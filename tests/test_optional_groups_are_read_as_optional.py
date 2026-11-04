"""An optional regex group is read with `present_int_or_none`, never `int_or_none`.

**Why (TASKS R116, then R128 (c)).** `safe_int.int_or_none` warns "unusable
integer" for anything it cannot convert, ``None`` included. An optional group
(one inside ``(?:...)?``, or in only some branches of an alternation) is ``None``
whenever the line does not carry it, which is not an unusable integer, it is an
absent one. On 2026-11-03 one such group put 1,942 warnings in one Full run, 96%
of the log's warnings (`pregap_search`), and R116 fixed that one caller. R128
asked for the rest: this sweep found `_take_rip_completed`'s ``done`` and
``total``, which warned on every ``Rip completed:`` line without its
``(N of M tracks)`` parenthetical.

**How it is mechanical, and where it stops.** For every call of either function
in `src/platterpus` whose argument is ``<m>.group("<name>")`` or ``<m>["<name>"]``,
the match ``<m>`` is resolved to the compiled pattern it came from:

* a binding in the same function, ``<m> = PATTERN.search|match|fullmatch(...)``,
  a walrus, or ``for <m> in PATTERN.finditer(...)``, nearest before the call;
* a parameter, through every call of that function in the same module, or the
  ``_LineRule(<name>, PATTERN, handler)`` table that dispatches it.

Then CPython's own regex parser (``re._parser``, present in 3.11 to 3.14) says
whether the group can be absent. A call the sweep cannot resolve fails it, unless
it is listed in ``_UNRESOLVED`` with its reason; a listing that no longer matches
a call fails too. A value that reached `int_or_none` through a variable is not
seen at all: that shape is read by hand, and the R128 report lists each one.
"""

from __future__ import annotations

import ast
import importlib
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

try:  # 3.11+: the private home of the parser `re.compile` itself uses
    from re import _constants as _sre_constants  # type: ignore[attr-defined]  # private, stable 3.11-3.14
    from re import _parser as _sre_parser  # type: ignore[attr-defined]  # private, stable 3.11-3.14
except ImportError:  # pragma: no cover — every supported Python has them
    pytest.skip("re._parser is not available", allow_module_level=True)

_SRC: Path = Path(__file__).resolve().parent.parent / "src"
_PACKAGE: Path = _SRC / "platterpus"
_READERS: frozenset[str] = frozenset({"int_or_none", "present_int_or_none"})
_MATCHERS: frozenset[str] = frozenset({"search", "match", "fullmatch", "finditer"})

#: Calls the sweep cannot resolve, by ``<file>:<function>:<group>``, each with the
#: reason it is safe. Empty today; an entry needs a reason a reviewer can check.
_UNRESOLVED: dict[str, str] = {}


# --- Which named groups can be absent ----------------------------------------


def _groups_in(items: object) -> set[int]:
    """Every group number anywhere under a parsed subpattern."""
    found: set[int] = set()
    for op, av in items:  # type: ignore[attr-defined]  # a parsed SubPattern
        if op is _sre_constants.SUBPATTERN:
            if av[0]:
                found.add(av[0])
            found |= _groups_in(av[3])
        elif op in _REPEATS:
            found |= _groups_in(av[2])
        elif op is _sre_constants.BRANCH:
            for alternative in av[1]:
                found |= _groups_in(alternative)
        elif op is _sre_constants.ATOMIC_GROUP:
            found |= _groups_in(av)
        elif op is _sre_constants.GROUPREF_EXISTS:
            found |= _groups_in(av[1])
            if av[2] is not None:
                found |= _groups_in(av[2])
        elif op in (_sre_constants.ASSERT, _sre_constants.ASSERT_NOT):
            found |= _groups_in(av[1])
    return found


_REPEATS: tuple[object, ...] = (
    _sre_constants.MAX_REPEAT,
    _sre_constants.MIN_REPEAT,
    _sre_constants.POSSESSIVE_REPEAT,
)


def optional_groups(pattern: re.Pattern[str]) -> tuple[frozenset[str], frozenset[str]]:
    """``(optional, mandatory)`` named groups of ``pattern``.

    Optional: under a repeat whose minimum is 0, in a branch that not every
    alternative of its alternation shares, in a conditional, or in a lookaround
    (whose groups a later step need not have set).
    """
    parsed = _sre_parser.parse(pattern.pattern, pattern.flags)
    names = {number: name for name, number in parsed.state.groupdict.items()}
    optional: set[str] = set()
    mandatory: set[str] = set()

    def walk(items: object, maybe: bool) -> None:
        for op, av in items:  # type: ignore[attr-defined]  # a parsed SubPattern
            if op is _sre_constants.SUBPATTERN:
                if av[0] in names:
                    (optional if maybe else mandatory).add(names[av[0]])
                walk(av[3], maybe)
            elif op in _REPEATS:
                walk(av[2], maybe or av[0] == 0)
            elif op is _sre_constants.BRANCH:
                shares = [_groups_in(alternative) for alternative in av[1]]
                for alternative, share in zip(av[1], shares, strict=True):
                    walk(alternative, maybe or any(share != s for s in shares))
            elif op is _sre_constants.ATOMIC_GROUP:
                walk(av, maybe)
            elif op is _sre_constants.GROUPREF_EXISTS:
                walk(av[1], True)
                if av[2] is not None:
                    walk(av[2], True)
            elif op in (_sre_constants.ASSERT, _sre_constants.ASSERT_NOT):
                walk(av[1], True)

    walk(parsed, False)
    return frozenset(optional), frozenset(mandatory)


@pytest.mark.parametrize(
    ("pattern", "optional", "mandatory"),
    [
        (r"(?P<a>\d+)", set(), {"a"}),
        (r"x(?:\s+(?P<a>\d+))?", {"a"}, set()),
        (r"(?P<a>\d)*", {"a"}, set()),
        (r"(?P<a>\d){1,3}", set(), {"a"}),
        (r"(?P<a>\d)|z", {"a"}, set()),
        (r"(?P<a>\d)|(?P<b>z)", {"a", "b"}, set()),
        (r"(?:(?P<a>\d)|x)(?P<b>y)", {"a"}, {"b"}),
        (r"(?:(?P<a>\d)y|(?P<a2>\d)z)?w", {"a", "a2"}, set()),
    ],
)
def test_the_analyser_tells_an_optional_group_from_a_mandatory_one(
    pattern: str, optional: set[str], mandatory: set[str]
) -> None:
    """The sweep below is only as good as this reading, so it is pinned first."""
    assert optional_groups(re.compile(pattern)) == (
        frozenset(optional),
        frozenset(mandatory),
    )


# --- Resolving each reader call to its pattern --------------------------------


@dataclass(frozen=True)
class _Site:
    """One `int_or_none` / `present_int_or_none` call on a named group."""

    where: str  # file:line
    key: str  # file:function:group, the `_UNRESOLVED` key
    reader: str
    group: str
    patterns: tuple[re.Pattern[str], ...]  # empty when unresolved


def _matched_pattern(node: ast.expr) -> ast.expr | None:
    """``PATTERN`` out of ``PATTERN.search(...)`` and its siblings."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _MATCHERS
    ):
        return node.func.value
    return None


def _read_group(arg: ast.expr) -> tuple[str, str] | None:
    """``(match_name, group)`` for ``m.group("g")`` or ``m["g"]``, else None."""
    if (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Attribute)
        and arg.func.attr == "group"
        and isinstance(arg.func.value, ast.Name)
        and len(arg.args) == 1
        and isinstance(arg.args[0], ast.Constant)
        and isinstance(arg.args[0].value, str)
    ):
        return arg.func.value.id, arg.args[0].value
    if (
        isinstance(arg, ast.Subscript)
        and isinstance(arg.value, ast.Name)
        and isinstance(arg.slice, ast.Constant)
        and isinstance(arg.slice.value, str)
    ):
        return arg.value.id, arg.slice.value
    return None


class _Module:
    """One source file: its functions, bindings and dispatch tables."""

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.rel: str = path.relative_to(_SRC).as_posix()
        self.tree: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
        self.functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self._module: object | None = None

    def scope_of(self, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        """The innermost function holding ``line``."""
        best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for function in self.functions:
            end = function.end_lineno or function.lineno
            if function.lineno <= line <= end and (
                best is None or function.lineno > best.lineno
            ):
                best = function
        return best

    def pattern(self, expr: ast.expr) -> re.Pattern[str] | None:
        """The compiled pattern a module-level name refers to, imported for real."""
        if not isinstance(expr, ast.Name):
            return None
        if self._module is None:
            name = ".".join(self.path.with_suffix("").relative_to(_SRC).parts)
            self._module = importlib.import_module(name)
        value = getattr(self._module, expr.id, None)
        return value if isinstance(value, re.Pattern) else None

    def bindings(
        self, name: str, scope: ast.AST | None, before: int
    ) -> list[re.Pattern[str]]:
        """The pattern ``name`` was last matched from in ``scope``, before ``before``."""
        found: list[tuple[int, re.Pattern[str]]] = []
        for node in ast.walk(scope if scope is not None else self.tree):
            target: ast.expr | None = None
            source: ast.expr | None = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, source = node.targets[0], _matched_pattern(node.value)
            elif isinstance(node, ast.NamedExpr):
                target, source = node.target, _matched_pattern(node.value)
            elif isinstance(node, ast.For):
                target, source = node.target, _matched_pattern(node.iter)
            if not (isinstance(target, ast.Name) and target.id == name):
                continue
            if source is None or node.lineno > before:
                continue
            if self.scope_of(node.lineno) is not scope:
                continue
            compiled = self.pattern(source)
            if compiled is not None:
                found.append((node.lineno, compiled))
        if not found:
            return []
        newest = max(line for line, _ in found)
        return [compiled for line, compiled in found if line == newest]

    def through_parameter(
        self, function: ast.FunctionDef | ast.AsyncFunctionDef, name: str
    ) -> list[re.Pattern[str]]:
        """The patterns a parameter ``name`` of ``function`` is called with."""
        params = [a.arg for a in function.args.args]
        if name not in params:
            return []
        index = params.index(name)
        found: list[re.Pattern[str]] = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            # `_LineRule("label", PATTERN, handler)`: the table hands the match in.
            if node.func.id == "_LineRule" and len(node.args) >= 3:
                handler = node.args[2]
                if isinstance(handler, ast.Name) and handler.id == function.name:
                    compiled = self.pattern(node.args[1])
                    if compiled is not None:
                        found.append(compiled)
                continue
            if node.func.id != function.name or len(node.args) <= index:
                continue
            arg = node.args[index]
            if isinstance(arg, ast.Name):
                found.extend(
                    self.bindings(arg.id, self.scope_of(node.lineno), node.lineno)
                )
        return found


def _sites() -> list[_Site]:
    sites: list[_Site] = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if path.name == "safe_int.py":
            continue
        module = _Module(path)
        for node in ast.walk(module.tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in _READERS
                and node.args
            ):
                continue
            read = _read_group(node.args[0])
            if read is None:
                continue
            match_name, group = read
            scope = module.scope_of(node.lineno)
            patterns = module.bindings(match_name, scope, node.lineno)
            if not patterns and scope is not None:
                patterns = module.through_parameter(scope, match_name)
            function = scope.name if scope is not None else "<module>"
            sites.append(
                _Site(
                    where=f"{module.rel}:{node.lineno}",
                    key=f"{module.rel}:{function}:{group}",
                    reader=node.func.id,
                    group=group,
                    patterns=tuple(patterns),
                )
            )
    return sites


_SITES: list[_Site] = _sites()

#: Measured 2026-11-04: 56 calls on a named group, every one resolved (the six
#: `pregap_search` reads by a computed name are not this shape). A floor, so a
#: resolver that stopped finding calls fails instead of passing on nothing.
_MIN_SITES: int = 50


def test_the_sweep_examines_the_calls_it_claims_to() -> None:
    """A sweep that found nothing would pass; this one must find the population,
    and among it the optional groups it was written for."""
    assert len(_SITES) >= _MIN_SITES, (len(_SITES), [s.where for s in _SITES])
    optional_sites = [
        site
        for site in _SITES
        if site.patterns
        and any(site.group in optional_groups(p)[0] for p in site.patterns)
    ]
    keys = {site.key for site in optional_sites}
    # The two known cases: R116's and the one this sweep found (R128 (c)).
    assert {
        "platterpus/pregap_search.py:read_search:undecided_from",
        "platterpus/pregap_search.py:read_search:undecided_to",
        "platterpus/parsers/cyanrip_log.py:_take_rip_completed:done",
        "platterpus/parsers/cyanrip_log.py:_take_rip_completed:total",
    } <= keys, sorted(keys)


def test_every_reader_call_on_a_named_group_is_resolved() -> None:
    unresolved = sorted(
        site.key for site in _SITES if not site.patterns and site.key not in _UNRESOLVED
    )
    assert not unresolved, (
        "these int_or_none calls read a regex group the sweep cannot trace to its "
        "pattern; teach the resolver, or list each in _UNRESOLVED with why its "
        f"group is always present: {unresolved}"
    )
    stale = sorted(set(_UNRESOLVED) - {site.key for site in _SITES})
    assert not stale, f"_UNRESOLVED names calls that no longer exist: {stale}"


def test_an_optional_group_is_never_read_with_int_or_none() -> None:
    """Absent is not unusable: an optional group goes to `present_int_or_none`."""
    wrong = [
        f"{site.where} ({site.key})"
        for site in _SITES
        if site.reader == "int_or_none"
        and any(site.group in optional_groups(p)[0] for p in site.patterns)
    ]
    assert not wrong, (
        "int_or_none reads an OPTIONAL regex group here, so every line without "
        "the group logs 'unusable integer' (TASKS R116: 1,942 warnings in one "
        f"run). Use safe_int.present_int_or_none: {wrong}"
    )
