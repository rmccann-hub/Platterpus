"""No test walks the WHOLE repository with ``Path.rglob`` (TASKS R28).

**The defect this exists to prevent, measured rather than imagined.** Two flaky
failures came from the same shape. ``Path.rglob`` lists a directory, then descends
into each child it listed; if the child is gone by the time it gets there, it
raises ``FileNotFoundError``. Under ``pytest -n auto`` another xdist worker
creates and deletes tool caches at the repository root (``.hypothesis/tmp``,
``.pytest_cache``) while this one walks, so a whole-tree ``rglob`` fails at random
and green-on-retry. TASKS R18 was a Markdown sweep meeting ``.hypothesis/tmp``; a
second was the conflict-marker scan racing the same directory. Both were fixed by
moving to ``tests/conftest.py::repo_files``, which walks with ``os.walk`` (a
vanished directory is reported to ``onerror`` and skipped), prunes
``TOOL_CACHE_DIRS`` and nested checkouts, and returns the files sorted.

Fixing the two walks did not stop a third being written the same way, so this is
a sweep: it reads every test module's AST, finds each ``.rglob(...)`` call and each
``.glob("**...")`` call, works out what directory the receiver names, and refuses
any that names the repository root (or above it) or that it cannot place at all.

**What counts as whole-repository.** The resolver tracks a path as *how many
components below the repository root* it is: ``Path(__file__)`` in a top-level
test is 2 deep, ``.parent`` takes one off, ``.parents[k]`` takes ``k + 1`` off,
``/ "a/b"`` adds two, and a relative string is relative to the working directory
(the repository root, where pytest runs). Depth 0 or less is the whole tree.
A join with a value it cannot read (``REPO_ROOT / name``) counts as one
component, because a join names a subdirectory; a value it cannot place at all
(a parameter with no call site, an attribute of an object) is UNRESOLVED and is
refused like a whole-tree walk, because a sweep that passes whatever it cannot
read is a sweep that can be satisfied by the wrong thing (``CLAUDE.md``). A walk
of ``src/platterpus`` or ``docs/`` is fine: no tool writes a cache there mid-run.

**The allowlist may shrink, never grow.** :data:`_ALLOWED` exists for a walk that
genuinely cannot use ``repo_files`` — and the better fix is always to convert it.
A new entry needs an argued reason; a stale entry (one that no longer matches a
real site) fails :func:`test_the_allowlist_has_no_stale_entries`, so the list
cannot quietly describe a suite that has moved on.

**Can it pass by finding nothing?** No: :func:`test_the_sweep_examined_the_suite`
floors both the number of modules read and the number of walks found, and
:func:`test_a_planted_whole_repo_rglob_is_refused` runs the real scan over a
planted module to prove the detector refuses one.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

TESTS_DIR: Final[Path] = Path(__file__).resolve().parent
REPO_ROOT: Final[Path] = TESTS_DIR.parent

#: The shared walker lives here, so its own definition is not a "test" walk; and
#: this file names ``rglob`` in its planted fixture text, never in a call.
_EXEMPT_MODULES: Final[frozenset[str]] = frozenset({"conftest.py"})

#: Floor on the modules read. 322 test modules today; a bar well under that
#: catches a broken glob without tripping on ordinary consolidation.
_MIN_MODULES_EXAMINED: Final[int] = 250

#: Floor on the recursive walks FOUND (of any reach). About 90 today, nearly all
#: scoped to `src/platterpus`; a resolver that stopped recognising calls would
#: find none and refuse nothing, so this is the floor that keeps it honest.
_MIN_WALKS_FOUND: Final[int] = 50

#: Whole-repository (or unresolvable) walks that are allowed to stay, keyed by
#: (test module, "<enclosing qualname>:<receiver source>"), each with the reason
#: it cannot use ``repo_files``. **May shrink, never grow**: convert rather than
#: add. When this file landed (R28) every WHOLE-repository walk in the suite was
#: converted to ``repo_files``; what remains are walks the resolver cannot place
#: but a reader can, each argued below.
_STAGED_SESSION_DIR: Final[str] = (
    "walks the staging directory `_stage` built from a `plan_session(home="
    "tmp_path)` layout: under pytest's tmp_path, outside the repository, so no "
    "tool cache is created or deleted in it; the resolver cannot follow "
    "`staged.extra_dirs['session']`, a dict lookup on a returned object"
)
_ALLOWED: Final[dict[tuple[str, str], str]] = {
    (
        "test_test_session.py",
        "test_the_transcript_is_charged_before_any_log_rotation:base",
    ): _STAGED_SESSION_DIR,
    (
        "test_test_session.py",
        "test_the_current_log_is_still_staged_ahead_of_the_transcript:base",
    ): _STAGED_SESSION_DIR,
}


# --- the resolver -------------------------------------------------------------


@dataclass(frozen=True)
class _Rel:
    """A path that is ``depth`` components below the repository root."""

    depth: int


@dataclass(frozen=True)
class _Tmp:
    """A path under pytest's ``tmp_path``: outside the repository entirely."""


@dataclass(frozen=True)
class _Unresolved:
    """A value the resolver cannot place. Refused, never assumed scoped."""

    why: str


@dataclass(frozen=True)
class _Seq:
    """Several possible values: a tuple iterated, or a name bound twice."""

    items: tuple[_Value, ...]


_Value = _Rel | _Tmp | _Unresolved | _Seq

#: Pytest fixtures that hand a test a temporary directory.
_TMP_FIXTURES: Final[frozenset[str]] = frozenset({"tmp_path", "tmp_path_factory"})

#: Path methods that return the same location they were called on.
_SAME_PLACE_METHODS: Final[frozenset[str]] = frozenset(
    {"resolve", "absolute", "expanduser"}
)


def _flatten(value: _Value) -> list[_Value]:
    if isinstance(value, _Seq):
        return [leaf for item in value.items for leaf in _flatten(item)]
    return [value]


@dataclass(frozen=True)
class Walk:
    """One recursive walk found in a test module, and what it reaches."""

    module: str
    identifier: str
    line: int
    reach: str  # "whole" | "scoped" | "unresolved"
    detail: str


def _string_depth(text: str) -> _Value:
    """How deep a relative path string is; an absolute one cannot be placed."""
    if text.startswith("/"):
        return _Unresolved(f"absolute path {text!r}")
    depth = 0
    for part in text.split("/"):
        if part in ("", "."):
            continue
        depth += -1 if part == ".." else 1
    return _Rel(depth)


def _module_file_depth(dotted: str) -> _Value:
    """Depth of ``<module>.__file__`` for a module of this repository's ``src``."""
    parts = dotted.split(".")
    package = REPO_ROOT / "src" / Path(*parts) / "__init__.py"
    if package.is_file():
        return _Rel(len(parts) + 2)
    module = REPO_ROOT / "src" / Path(*parts[:-1]) / f"{parts[-1]}.py"
    if module.is_file():
        return _Rel(len(parts) + 1)
    return _Unresolved(f"{dotted}.__file__ is not a module of src/")


class _Module:
    """One test module's AST, its scopes and its bindings, ready to resolve."""

    def __init__(self, path: Path, tree: ast.Module) -> None:
        self.path: Path = path
        # The repository a module belongs to is its tests/ directory's parent, so
        # a planted module under `tmp_path/tests/` resolves against `tmp_path`.
        self.root: Path = path.resolve().parent.parent
        self.tree: ast.Module = tree
        self.parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node
        self.functions: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                self.functions.setdefault(node.name, []).append(node)
        # Depth of this file below the repository root: `tests/x.py` is 2.
        self.file_depth: int = len(path.resolve().relative_to(self.root).parts)
        self._in_progress: set[tuple[int, str]] = set()

    # Scope helpers ---------------------------------------------------------

    def enclosing_function(
        self, node: ast.AST
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | None:
        current = self.parents.get(node)
        while current is not None:
            if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                return current
            current = self.parents.get(current)
        return None

    def qualname(self, node: ast.AST) -> str:
        names: list[str] = []
        current = self.parents.get(node)
        while current is not None:
            if isinstance(
                current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ):
                names.append(current.name)
            current = self.parents.get(current)
        return ".".join(reversed(names)) or "<module>"

    @staticmethod
    def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
        """Every node of ``scope`` that is not inside a nested function or class."""
        stack: list[ast.AST] = list(ast.iter_child_nodes(scope))
        while stack:
            node = stack.pop()
            yield node
            if isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda
            ):
                continue
            stack.extend(ast.iter_child_nodes(node))

    # Name resolution -------------------------------------------------------

    def _bindings(self, scope: ast.AST, name: str) -> list[_Value] | None:
        """Every value ``name`` is given in ``scope``, or None if it is not bound."""
        values: list[_Value] = []
        bound = False
        if isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            param = self._parameter(scope, name)
            if param is not None:
                return [param]
        for node in self._scope_nodes(scope):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        bound = True
                        values.append(self.evaluate(node.value, scope))
            elif isinstance(node, ast.AnnAssign | ast.AugAssign):
                target = node.target
                if isinstance(target, ast.Name) and target.id == name:
                    bound = True
                    if isinstance(node, ast.AugAssign) or node.value is None:
                        values.append(_Unresolved(f"{name} is augmented"))
                    else:
                        values.append(self.evaluate(node.value, scope))
            elif isinstance(node, ast.For | ast.comprehension):
                target = node.target
                if isinstance(target, ast.Name) and target.id == name:
                    bound = True
                    iterable = self.evaluate(node.iter, scope)
                    values.append(
                        iterable
                        if isinstance(iterable, _Seq)
                        else _Unresolved(f"{name} iterates something unreadable")
                    )
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if (alias.asname or alias.name) == name:
                        bound = True
                        values.append(self._imported(node.module or "", alias.name))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (alias.asname or alias.name.split(".")[0]) == name:
                        bound = True
                        values.append(_Unresolved(f"{name} is a module"))
            elif isinstance(node, ast.withitem):
                var = node.optional_vars
                if isinstance(var, ast.Name) and var.id == name:
                    bound = True
                    values.append(_Unresolved(f"{name} is a context manager"))
            elif isinstance(node, ast.NamedExpr) and node.target.id == name:
                bound = True
                values.append(self.evaluate(node.value, scope))
        return values if bound else None

    def _imported(self, module: str, name: str) -> _Value:
        """A name imported from a helper module in tests/ is resolved there."""
        source = self.path.parent / f"{module}.py"
        if not source.is_file():
            return _Unresolved(f"{name} is imported from {module}")
        helper = _Module(source, ast.parse(source.read_text(encoding="utf-8")))
        return helper.resolve_name(name, None, helper.tree)

    def _parameter(
        self, function: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, name: str
    ) -> _Value | None:
        """A parameter is everything its default and its call sites pass it."""
        args = function.args
        positional = [*args.posonlyargs, *args.args]
        every = [*positional, *args.kwonlyargs]
        if args.vararg is not None:
            every.append(args.vararg)
        if args.kwarg is not None:
            every.append(args.kwarg)
        if name not in {a.arg for a in every}:
            return None
        if name in _TMP_FIXTURES:
            return _Tmp()
        values: list[_Value] = []
        # Defaults line up with the LAST positional parameters.
        defaults = dict(
            zip(
                [a.arg for a in positional][len(positional) - len(args.defaults) :],
                args.defaults,
                strict=True,
            )
        )
        for kwarg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            if default is not None:
                defaults[kwarg.arg] = default
        enclosing = self.enclosing_function(function) or self.tree
        if name in defaults:
            values.append(self.evaluate(defaults[name], enclosing))
        index = next((i for i, a in enumerate(positional) if a.arg == name), None)
        if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            for call in ast.walk(self.tree):
                if not (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == function.name
                ):
                    continue
                scope = self.enclosing_function(call) or self.tree
                passed: ast.expr | None = None
                if index is not None and index < len(call.args):
                    passed = call.args[index]
                for keyword in call.keywords:
                    if keyword.arg == name:
                        passed = keyword.value
                if passed is not None:
                    values.append(self.evaluate(passed, scope))
        if not values:
            values.extend(self._fixture(name))
        if not values:
            return _Unresolved(f"parameter {name} has no default and no call site")
        return _Seq(tuple(values))

    def _fixture(self, name: str) -> list[_Value]:
        """What a pytest fixture of this module named ``name`` returns or yields.

        A test's parameter is filled by the fixture of the same name, so the
        fixture's own ``return``/``yield`` is the parameter's value. A fixture
        from ``conftest.py`` is not read: the parameter stays unresolved."""
        values: list[_Value] = []
        for function in self.functions.get(name, []):
            if not any(
                "fixture" in ast.unparse(decorator)
                for decorator in function.decorator_list
            ):
                continue
            for inner in self._scope_nodes(function):
                if (
                    isinstance(inner, ast.Return | ast.Yield)
                    and inner.value is not None
                ):
                    values.append(self.evaluate(inner.value, function))
        return values

    def resolve_name(self, name: str, scope: ast.AST | None, start: ast.AST) -> _Value:
        if name == "__file__":
            return _Rel(self.file_depth)
        key = (id(start), name)
        if key in self._in_progress:
            return _Unresolved(f"{name} is defined in terms of itself")
        self._in_progress.add(key)
        try:
            current: ast.AST | None = start
            while current is not None:
                if isinstance(
                    current,
                    ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.Module,
                ):
                    found = self._bindings(current, name)
                    if found is not None:
                        return found[0] if len(found) == 1 else _Seq(tuple(found))
                current = self.parents.get(current)
            return _Unresolved(f"{name} is not bound in this module")
        finally:
            self._in_progress.discard(key)

    # Expression evaluation -------------------------------------------------

    def evaluate(self, node: ast.expr, scope: ast.AST) -> _Value:
        """What location ``node`` names, as far as the module's text says."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return _string_depth(node.value)
        if isinstance(node, ast.Name):
            return self.resolve_name(node.id, scope, scope)
        if isinstance(node, ast.Tuple | ast.List | ast.Set):
            return _Seq(tuple(self.evaluate(item, scope) for item in node.elts))
        if isinstance(node, ast.ListComp | ast.SetComp | ast.GeneratorExp):
            # A comprehension's loop variables are bound in the enclosing scope's
            # walk (see `_bindings`), so its element reads like any expression.
            return _Seq((self.evaluate(node.elt, scope),))
        if isinstance(node, ast.IfExp):
            return _Seq(
                (self.evaluate(node.body, scope), self.evaluate(node.orelse, scope))
            )
        if isinstance(node, ast.BoolOp):
            return _Seq(tuple(self.evaluate(v, scope) for v in node.values))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._join(
                self.evaluate(node.left, scope), self.evaluate(node.right, scope)
            )
        if isinstance(node, ast.Attribute):
            return self._attribute(node, scope)
        if isinstance(node, ast.Subscript):
            return self._subscript(node, scope)
        if isinstance(node, ast.Call):
            return self._call(node, scope)
        return _Unresolved(f"cannot read {ast.unparse(node)!r}")

    def _join(self, left: _Value, right: _Value) -> _Value:
        if isinstance(left, _Seq):
            return _Seq(tuple(self._join(item, right) for item in left.items))
        if not isinstance(left, _Rel):
            return left
        if isinstance(right, _Seq):
            return _Seq(tuple(self._join(left, item) for item in right.items))
        if isinstance(right, _Rel):
            return _Rel(left.depth + right.depth)
        # A join with something unreadable still names a subdirectory.
        return _Rel(left.depth + 1)

    @staticmethod
    def _up(value: _Value, levels: int) -> _Value:
        if isinstance(value, _Seq):
            return _Seq(tuple(_Module._up(item, levels) for item in value.items))
        if isinstance(value, _Rel):
            return _Rel(value.depth - levels)
        return value

    def _attribute(self, node: ast.Attribute, scope: ast.AST) -> _Value:
        if node.attr == "parent":
            return self._up(self.evaluate(node.value, scope), 1)
        if node.attr == "__file__":
            if isinstance(node.value, ast.Name):
                return _module_file_depth(self._dotted(node.value.id, scope))
            return _Unresolved(f"cannot read {ast.unparse(node)!r}")
        return _Unresolved(f"cannot read attribute {ast.unparse(node)!r}")

    def _dotted(self, name: str, scope: ast.AST) -> str:
        """The dotted module a local name was imported as (``ui`` →
        ``platterpus.ui``); the name itself when no import says otherwise."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if (alias.asname or alias.name) == name:
                        return f"{node.module}.{alias.name}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname == name:
                        return alias.name
        return name

    def _subscript(self, node: ast.Subscript, scope: ast.AST) -> _Value:
        base = node.value
        if (
            isinstance(base, ast.Attribute)
            and base.attr == "parents"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, int)
        ):
            return self._up(self.evaluate(base.value, scope), node.slice.value + 1)
        return _Unresolved(f"cannot read {ast.unparse(node)!r}")

    def _call(self, node: ast.Call, scope: ast.AST) -> _Value:
        func = node.func
        if isinstance(func, ast.Name) and func.id in {"Path", "PurePath"}:
            return self.evaluate(node.args[0], scope) if node.args else _Rel(0)
        if isinstance(func, ast.Attribute):
            if func.attr == "cwd":
                return _Rel(0)
            if func.attr == "mktemp":
                return _Tmp()
            if func.attr in _SAME_PLACE_METHODS:
                return self.evaluate(func.value, scope)
            if func.attr == "Path" and node.args:  # pathlib.Path(...)
                return self.evaluate(node.args[0], scope)
        if isinstance(func, ast.Name) and func.id in self.functions:
            # A module-local helper: what it returns is what it names.
            returned: list[_Value] = []
            for function in self.functions[func.id]:
                for inner in self._scope_nodes(function):
                    if isinstance(inner, ast.Return) and inner.value is not None:
                        returned.append(self.evaluate(inner.value, function))
            if returned:
                return returned[0] if len(returned) == 1 else _Seq(tuple(returned))
        return _Unresolved(f"cannot read call {ast.unparse(node)!r}")


def _reach(value: _Value) -> tuple[str, str]:
    """Collapse a resolved value to whole / unresolved / scoped, worst first."""
    leaves = _flatten(value)
    for leaf in leaves:
        if isinstance(leaf, _Rel) and leaf.depth <= 0:
            return "whole", "names the repository root or above"
    for leaf in leaves:
        if isinstance(leaf, _Unresolved):
            return "unresolved", leaf.why
    return "scoped", "a subdirectory or a temporary directory"


def _is_recursive_walk(node: ast.AST) -> bool:
    """``x.rglob(...)``, or ``x.glob("**...")`` — the same walk spelled out."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return False
    if node.func.attr == "rglob":
        return True
    if node.func.attr == "glob" and node.args:
        first = node.args[0]
        return (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and first.value.startswith("**")
        )
    return False


def scan_module(path: Path) -> list[Walk]:
    """Every recursive walk in one module, each with the directory it reaches."""
    module = _Module(path, ast.parse(path.read_text(encoding="utf-8")))
    walks: list[Walk] = []
    for node in ast.walk(module.tree):
        if not _is_recursive_walk(node):
            continue
        assert isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        receiver = node.func.value
        scope = module.enclosing_function(node) or module.tree
        reach, detail = _reach(module.evaluate(receiver, scope))
        walks.append(
            Walk(
                module=path.name,
                identifier=f"{module.qualname(node)}:{ast.unparse(receiver)}",
                line=node.lineno,
                reach=reach,
                detail=detail,
            )
        )
    return walks


def swept_modules(tests_dir: Path = TESTS_DIR) -> list[Path]:
    """The test modules this sweep reads: every ``*.py`` directly in tests/."""
    return sorted(p for p in tests_dir.glob("*.py") if p.name not in _EXEMPT_MODULES)


def scan(tests_dir: Path = TESTS_DIR) -> list[Walk]:
    return [walk for path in swept_modules(tests_dir) for walk in scan_module(path)]


def _refused(walks: list[Walk]) -> list[Walk]:
    return [
        w
        for w in walks
        if w.reach != "scoped" and (w.module, w.identifier) not in _ALLOWED
    ]


# --- the tests ----------------------------------------------------------------


def test_no_test_walks_the_whole_repository_with_rglob() -> None:
    refused = _refused(scan())
    assert not refused, (
        "These tests walk the whole repository (or a directory this sweep cannot "
        "place) with rglob, which raises FileNotFoundError when a parallel worker "
        "deletes a tool cache mid-walk (TASKS R18/R28). Use "
        "`conftest.repo_files(root)` and filter its result instead:\n"
        + "\n".join(
            f"  {w.module}:{w.line} {w.identifier} ({w.reach}: {w.detail})"
            for w in refused
        )
    )


def test_the_sweep_examined_the_suite() -> None:
    """Floors: a broken glob or a resolver that stopped seeing calls fails here."""
    modules = swept_modules()
    walks = scan()
    assert len(modules) >= _MIN_MODULES_EXAMINED, len(modules)
    assert len(walks) >= _MIN_WALKS_FOUND, len(walks)
    # Non-triviality: the resolver must place most walks, not shrug at them. If it
    # called everything "unresolved" it would still refuse, but for no reason.
    assert sum(w.reach == "scoped" for w in walks) >= _MIN_WALKS_FOUND, walks


def test_the_allowlist_has_no_stale_entries() -> None:
    """Every allowlisted key still names a real whole-repository site."""
    live = {(w.module, w.identifier) for w in scan() if w.reach != "scoped"}
    stale = sorted(set(_ALLOWED) - live)
    assert not stale, f"allowlist entries that match no site any more: {stale}"
    for key, reason in _ALLOWED.items():
        assert reason.strip(), f"{key} has no reason"


_PLANTED: Final[str] = """\
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"


def _helper(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def test_scoped_is_fine() -> None:
    assert list(DOCS.rglob("*.md")) is not None


def test_whole_repo_is_refused() -> None:
    assert list(REPO_ROOT.rglob("*.md")) is not None


def test_spelled_out_is_refused() -> None:
    assert list(Path(__file__).parent.parent.glob("**/*.py")) is not None


def test_through_a_parameter_is_refused() -> None:
    assert _helper(REPO_ROOT) is not None


def test_tmp_path_is_fine(tmp_path: Path) -> None:
    assert list(tmp_path.rglob("*")) == []
"""


def test_a_planted_whole_repo_rglob_is_refused(tmp_path: Path) -> None:
    """The real scan, over a planted tests/ directory, refuses exactly the
    whole-repository walks and passes the scoped ones."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_planted.py").write_text(_PLANTED, encoding="utf-8")
    walks = scan(tests)
    by_function = {w.identifier.split(":")[0]: w.reach for w in walks}
    assert by_function == {
        "_helper": "whole",
        "test_scoped_is_fine": "scoped",
        "test_whole_repo_is_refused": "whole",
        "test_spelled_out_is_refused": "whole",
        "test_tmp_path_is_fine": "scoped",
    }, walks
    assert {w.identifier for w in _refused(walks)} == {
        "_helper:root",
        "test_whole_repo_is_refused:REPO_ROOT",
        "test_spelled_out_is_refused:Path(__file__).parent.parent",
    }


def test_an_unplaceable_receiver_is_refused_not_assumed_scoped(tmp_path: Path) -> None:
    """Fail closed: a walk whose root the resolver cannot read is refused."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_opaque.py").write_text(
        "def test_opaque(somewhere: object) -> None:\n"
        "    list(somewhere.rglob('*'))  # type: ignore[attr-defined]\n",
        encoding="utf-8",
    )
    (walk,) = scan(tests)
    assert walk.reach == "unresolved", walk
    assert _refused([walk]) == [walk]
