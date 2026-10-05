"""Readers over the repository: file text, pyproject, string literals in the
code (docstrings excluded), requirement strings, and the AST scans that find
which programs and packages the code actually uses.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Final

from bommap.model import _REPO_ROOT, GeneratorError


def _rel(path: Path) -> str:
    """A repo-relative POSIX path: what every ``used_in`` cell names."""
    return path.relative_to(_REPO_ROOT).as_posix()


@cache
def _text(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


@cache
def _pyproject() -> dict[str, object]:
    return tomllib.loads(_text("pyproject.toml"))


def _project() -> dict[str, object]:
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    return project


@cache
def _code_strings(rel: str) -> frozenset[str]:
    """Every string literal in a Python file, docstrings EXCLUDED.

    A witness found only in a docstring proves the code *talks about* a tool,
    not that it runs it — the same "mention is not a call" trap the threading
    sweep once fell into — so docstrings do not count.
    """
    tree = ast.parse(_text(rel))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return frozenset(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    )


def _witnessed(rel: str, literal: str, *, as_word: bool = False) -> bool:
    """True when ``literal`` is a string in ``rel``'s code.

    ``as_word=False`` demands an exact string (an argv element). ``as_word=True``
    accepts the literal as a whole word inside a longer string (a command inside
    an ``sh -c`` script), because a two-letter name such as ``sh`` matched as a
    bare substring would match almost anything.
    """
    pattern = re.compile(rf"(?<![\w-]){re.escape(literal)}(?![\w-])")
    if not rel.endswith(".py"):
        # A shell script or a workflow: comment lines do not count, for the same
        # reason docstrings do not.
        return any(pattern.search(line) for line in _logical_lines(_text(rel)))
    strings = _code_strings(rel)
    if not as_word:
        return literal in strings
    return any(pattern.search(s) for s in strings)


def _require(rel: str, literal: str, *, as_word: bool = False, why: str) -> str:
    """Return ``rel`` if the witness holds; stop the run naming it if not."""
    if not (_REPO_ROOT / rel).is_file():
        raise GeneratorError(f"{why}: {rel} does not exist")
    if not _witnessed(rel, literal, as_word=as_word):
        raise GeneratorError(
            f"{why}: {literal!r} is no longer a string in {rel}. If the code "
            "stopped using it, remove it from scripts/emit_bom.py; if it moved, "
            "point the witness at the new file."
        )
    return rel


def _normalise(name: str) -> str:
    """PEP 503 normalisation, which is also what a ``pkg:pypi`` purl uses."""
    return re.sub(r"[-_.]+", "-", name).lower()


_REQUIREMENT: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<extras>\[[^\]]*\])?\s*(?P<spec>.*?)\s*$"
)


def _requirement(text: str) -> tuple[str, str]:
    """``"PySide6>=6.11.1,<6.12"`` → ``("PySide6", ">=6.11.1,<6.12")``."""
    match = _REQUIREMENT.match(text)
    if match is None:
        raise GeneratorError(f"cannot read requirement {text!r}")
    return match.group("name"), match.group("spec").replace(" ", "")


def _exact(constraint: str) -> str:
    """The version an ``==X`` constraint pins, or ``""`` for anything wider."""
    if constraint.startswith("==") and "," not in constraint and "*" not in constraint:
        return constraint[2:]
    return ""


def _vers(scheme: str, constraint: str) -> str:
    """A PEP 440-style constraint in CycloneDX ``vers`` syntax (``|``-joined)."""
    if not constraint:
        return ""
    return f"vers:{scheme}/" + "|".join(part for part in constraint.split(",") if part)


def _home_relative(path: Path) -> str:
    """``/home/x/.local/bin/cyanrip`` → ``~/.local/bin/cyanrip``.

    The registry's binary paths are computed from the CURRENT user's home, so
    writing them verbatim would make the BOM differ between two machines.
    """
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return path.as_posix()


def _join(items: Iterable[str]) -> str:
    return ", ".join(items)


def _strings(value: object) -> list[str]:
    """A TOML array as a list of strings; anything else is a shape we refuse."""
    if not isinstance(value, list):
        raise GeneratorError(f"expected a TOML array, got {type(value).__name__}")
    return [str(item) for item in value]


@cache
def _src_files() -> tuple[str, ...]:
    return tuple(
        sorted(_rel(p) for p in (_REPO_ROOT / "src" / "platterpus").rglob("*.py"))
    )


#: The shared lookup helpers every caller is meant to resolve a tool through
#: (``tool_paths`` exists so there is one search order; ``ctdb/decode._which``
#: delegates to it). A literal first argument to one of them is the most
#: reliable "this program is run" signal the code offers.
_LOOKUP_HELPERS: Final[frozenset[str]] = frozenset(
    {"resolve_tool", "find_tool", "which", "_which", "_host_tool"}
)


@cache
def _binary_constants() -> dict[str, str]:
    """``platterpus.paths``'s ``*_BINARY_DEFAULT`` names → the program they name."""
    from platterpus import paths

    return {
        name: Path(str(getattr(paths, name))).name
        for name in sorted(dir(paths))
        if name.endswith("_BINARY_DEFAULT")
    }


@cache
def tool_lookups() -> dict[str, tuple[str, ...]]:
    """Program name → the src files that reach it. Three signals, all from the AST:

    * a literal first argument to one of :data:`_LOOKUP_HELPERS`;
    * a literal default for a parameter whose name says it is the binary
      (``binary_name: str = "metaflac"``) — how the adapters name their tool;
    * a use of a ``platterpus.paths.*_BINARY_DEFAULT`` constant (the host-export
      paths such as ``~/.local/bin/cd-paranoia``).
    """
    constants = _binary_constants()
    found: dict[str, set[str]] = {}
    for rel in _src_files():
        tree = ast.parse(_text(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args:
                func = node.func
                name = (
                    func.attr
                    if isinstance(func, ast.Attribute)
                    else func.id
                    if isinstance(func, ast.Name)
                    else ""
                )
                first = node.args[0]
                if (
                    name in _LOOKUP_HELPERS
                    and isinstance(first, ast.Constant)
                    and isinstance(first.value, str)
                ):
                    found.setdefault(first.value, set()).add(rel)
            elif isinstance(node, ast.arguments):
                positional = [*node.posonlyargs, *node.args]
                pairs = list(
                    zip(
                        positional[len(positional) - len(node.defaults) :],
                        node.defaults,
                        strict=True,
                    )
                )
                pairs += [
                    (a, d)
                    for a, d in zip(node.kwonlyargs, node.kw_defaults, strict=True)
                    if d is not None
                ]
                for arg, default in pairs:
                    if (
                        "binary" in arg.arg
                        and isinstance(default, ast.Constant)
                        and isinstance(default.value, str)
                    ):
                        found.setdefault(default.value, set()).add(rel)
            elif (
                isinstance(node, ast.Name)
                and node.id in constants
                and not rel.endswith("/paths.py")
            ):
                found.setdefault(constants[node.id], set()).add(rel)
    return {tool: tuple(sorted(files)) for tool, files in sorted(found.items())}


@cache
def _imports(roots: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Top-level imported module (lower-cased) → files importing it."""
    found: dict[str, set[str]] = {}
    for root in roots:
        for path in sorted((_REPO_ROOT / root).rglob("*.py")):
            rel = _rel(path)
            try:
                tree = ast.parse(_text(rel))
            except SyntaxError as exc:
                # A test fixture can be deliberately unparseable. It imports
                # nothing we could count, so it is skipped, but loudly.
                sys.stderr.write(f"emit_bom: skipped unparseable {rel}: {exc.msg}\n")
                continue
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif (
                    isinstance(node, ast.ImportFrom) and node.module and not node.level
                ):
                    names = [node.module]
                for module in names:
                    found.setdefault(module.split(".")[0].lower(), set()).add(rel)
    return {module: tuple(sorted(files)) for module, files in found.items()}


def _imported_by(distribution: str, roots: tuple[str, ...]) -> str:
    """Where a distribution is imported, summarised without losing anything.

    Up to eight files are named outright. Beyond that, every DIRECTORY holding
    an importer is named instead, marked "(every importer is in these
    directories)", so the cell still accounts for all of them — a silent "and
    others" would read as completeness.

    **No per-directory counts, deliberately.** A count moves every time anyone
    adds a test file (nearly all of them import pytest), which would make the
    committed BOM stale on almost every commit — and a check that is red for no
    reason is the check somebody deletes. A directory list moves only when a
    package starts being used somewhere new, which is worth a regeneration.
    """
    files = _imports(roots).get(_normalise(distribution).replace("-", "_"), ())
    if not files:
        return "not imported directly"
    if len(files) <= 8:
        return _join(files)
    dirs = sorted({rel.rsplit("/", 1)[0] + "/" for rel in files})
    return _join(dirs) + " (every importer is in these directories)"


def _project_repository() -> str:
    """``[project.urls].Repository`` from pyproject: this repository's home."""
    urls = _project().get("urls", {})
    if not isinstance(urls, dict) or "Repository" not in urls:
        raise GeneratorError("pyproject.toml [project.urls] has no Repository")
    return str(urls["Repository"])


def _logical_lines(text: str) -> list[str]:
    """Lines with ``\\`` continuations joined, comment lines dropped."""
    out: list[str] = []
    buffer = ""
    for raw in text.splitlines():
        if raw.lstrip().startswith("#"):
            continue
        if raw.rstrip().endswith("\\"):
            buffer += raw.rstrip()[:-1] + " "
            continue
        out.append(buffer + raw)
        buffer = ""
    if buffer:
        out.append(buffer)
    return out
