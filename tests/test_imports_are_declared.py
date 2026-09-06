"""Every third-party module the code imports is a dependency we declared.

**The break this exists to prevent, which it reproduces exactly.**
``tests/test_ci_jobs_are_bounded.py`` was written with ``import yaml``. PyYAML is
installed in some environments incidentally — it was in the one the test was written
in — and is in neither this project's runtime dependencies nor its ``dev`` extra, and
nothing else in the repo imports it. The full suite passed locally and **all four CI
matrix legs failed at once** with ``ModuleNotFoundError`` (2026-08-18).

The general shape is `docs/testing.md`'s *"what does my stand-in do that the real
thing does not?"*, asked of the **environment** rather than of a fixture. A working
interpreter accumulates packages nobody declared — transitive installs, leftovers from
another project, whatever the base image ships — so *"it passes here"* silently
includes them. A **test** file is where this bites hardest: an undeclared import there
looks harmless, is invisible to every runtime check, and takes the whole matrix down
at once rather than degrading.

Nothing else could see it. `pip-audit` reads the declared set, so an import that is
*not* in it is exactly what it cannot examine. `mypy` resolves against the installed
environment, which is the environment that has the package. Only a comparison of
*imports* against *declarations* closes it, and that comparison is what this file is.

**Both sides are derived, neither is a list.** The imports come from walking the AST
of every module under ``src/``, ``tests/`` and ``scripts/``; the declarations come from
``pyproject.toml``. A hand-maintained list of "allowed modules" would need updating
the day a real dependency is added, and would go stale silently — the failure mode
`CLAUDE.md` rule #7 describes for maps generally.

**Homes considered and rejected**, per the same rule's new-file burden of proof:
``test_dependency_build_notes.py`` and its ``test_deps_*`` siblings are about
*external tool* dependencies (cyanrip, flac, Picard) reached through the dependency
subsystem — a different subject that happens to share a word. ``test_build_harness.py``
is the AppImage recipe, and while it does compare pyproject pins against
``DEPENDENCIES.md``, the imports of the test suite are not part of a build harness.
``test_audit_regressions.py`` is the mypy opt-out ratchet. None fits; this is a
one-responsibility module rather than a concern bolted onto a file that promises
something else.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
PYPROJECT: Final[Path] = REPO_ROOT / "pyproject.toml"

#: Directories whose imports must be satisfiable from the declared set alone. These
#: are the trees CI installs and runs; anything importable only because a developer's
#: machine happens to have it belongs to none of them.
SOURCE_ROOTS: Final[tuple[str, ...]] = ("src", "tests", "scripts")

#: **There is no distribution → import-name alias table, and that is deliberate.**
#: The first draft had one, and both its rows (``pytest-cov`` → ``pytest_cov``,
#: ``tomli-w`` → ``tomli_w``) turned out to be nothing but the hyphen-to-underscore
#: normalisation :func:`_satisfiable_names` already applies — machinery that changed
#: no outcome. Its own guard test said so on the first run.
#:
#: The row it must *never* grow is ``pyyaml`` → ``yaml``: PyYAML is not a dependency
#: here, and aliasing it would make ``import yaml`` read as satisfiable and re-open
#: the exact hole this file exists to close.
#:
#: If a real dependency is ever added whose import name differs by more than that
#: rule (``beautifulsoup4`` → ``bs4`` is the classic), this sweep will fail with the
#: module named and the file that imports it. Map it *here*, beside this note, and
#: only for a distribution ``pyproject.toml`` actually declares.

#: First-party names that are never declared because they are ours. ``platterpus`` is
#: the package under test; ``conftest`` is pytest's own; test modules import each
#: other's helpers, and those are resolved from disk below rather than listed.
FIRST_PARTY: Final[frozenset[str]] = frozenset({"platterpus", "conftest"})

#: Floor. A sweep that examines nothing reports success — the failure mode this
#: project has hit repeatedly. Today's tree examines ~3,400 import statements; the
#: floor sits far below that so it asserts the population is real without becoming a
#: number to maintain.
MIN_IMPORTS_EXAMINED: Final[int] = 500


def _declared_distributions() -> set[str]:
    """Every distribution named in ``pyproject.toml``, runtime and every extra."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    # A requirement is `Name[extra]>=1.2,<2 ; marker` — the name ends at the first
    # separator. Deliberately a text split and not a full PEP 508 parse: pulling in a
    # parser to check dependencies would be its own joke.
    return {re.split(r"[<>=!~\[; ]", spec)[0].strip().lower() for spec in specs if spec}


def _satisfiable_names() -> set[str]:
    """Top-level import names that resolve without an undeclared install.

    A distribution's import name is its own name with hyphens turned into
    underscores — ``tomli-w`` is imported as ``tomli_w``. That covers every
    dependency this project has; see the note above for the case it does not cover
    and what to do about it.
    """
    names = {dist.replace("-", "_") for dist in _declared_distributions()}
    names |= {n.lower() for n in names}
    names |= FIRST_PARTY
    names |= set(sys.stdlib_module_names)
    # Sibling test modules and any package inside src/ are importable by name.
    names |= {p.stem for p in (REPO_ROOT / "tests").rglob("*.py")}
    names |= {p.name for p in (REPO_ROOT / "src").iterdir() if p.is_dir()}
    # ...and any module under `scripts/`, which a test may import directly after
    # putting that directory on `sys.path`. DERIVED from the filesystem, not
    # listed: this file's own docstring argues that a hand-maintained allowlist
    # needs updating and therefore rots, and adding one entry to prove the point
    # wrong would be the joke. `tests/test_mutation_sweep.py` importing
    # `mutation_sweep` is the first such case.
    names |= {p.stem for p in (REPO_ROOT / "scripts").rglob("*.py")}
    return names


def _python_files() -> list[Path]:
    return [
        path
        for root in SOURCE_ROOTS
        for path in sorted((REPO_ROOT / root).rglob("*.py"))
        if path.is_file()
    ]


def _imported_top_level(path: Path) -> list[str]:
    """Top-level module name of every absolute import in one file.

    Relative imports (``from .x import y``) are skipped — they are first-party by
    construction. ``import a.b.c`` contributes ``a``, because that is the name that
    has to be installed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module.split(".")[0])
    return found


def _undeclared() -> tuple[dict[str, set[str]], int]:
    """``{module: {files}}`` for undeclared imports, plus the count examined."""
    satisfiable = _satisfiable_names()
    offenders: dict[str, set[str]] = {}
    examined = 0
    for path in _python_files():
        for name in _imported_top_level(path):
            examined += 1
            # PySide6 submodules (`PySide6.QtCore`) reduce to `PySide6`, which is
            # declared; the case-insensitive check covers how it is written.
            if name in satisfiable or name.lower() in satisfiable:
                continue
            offenders.setdefault(name, set()).add(
                path.relative_to(REPO_ROOT).as_posix()
            )
    return offenders, examined


def test_every_import_is_a_declared_dependency() -> None:
    """The sweep. An import nothing declares is a matrix-wide failure waiting to run."""
    offenders, examined = _undeclared()
    assert not offenders, (
        "these modules are imported but declared nowhere in pyproject.toml, so they "
        "resolve only in environments that happen to have them — CI installs the "
        "declared set and will fail on every Python version at once:\n  "
        + "\n  ".join(
            f"{name}  ({', '.join(sorted(files))})"
            for name, files in sorted(offenders.items())
        )
        + "\nEither declare it (CLAUDE.md → Deviation policy asks first for a "
        "dependency not in DEPENDENCIES.md) or do without it."
    )
    assert examined >= MIN_IMPORTS_EXAMINED, (
        f"only {examined} imports examined across {len(_python_files())} files — the "
        f"source roots have moved and this sweep is passing by finding nothing"
    )


def test_the_sweep_flags_an_undeclared_import(tmp_path: Path) -> None:
    """Non-triviality, against a constructed file rather than by reading the code.

    The assertion above passes on a clean tree, which is also what a sweep that
    matches nothing does. This proves the predicate separates the two.
    """
    module = tmp_path / "sample.py"
    module.write_text(
        "import os\nimport yaml\nfrom platterpus import config\n", encoding="utf-8"
    )
    imported = _imported_top_level(module)
    assert imported == ["os", "yaml", "platterpus"]

    satisfiable = _satisfiable_names()
    assert "os" in satisfiable, "stdlib must be satisfiable"
    assert "platterpus" in satisfiable, "first-party must be satisfiable"
    assert "yaml" not in satisfiable, (
        "PyYAML is not declared in pyproject.toml, so `import yaml` must read as "
        "undeclared — this is the exact import that broke all four matrix legs on "
        "2026-08-18. If PyYAML is ever declared deliberately, delete this assertion "
        "rather than weakening the sweep."
    )


def test_the_declared_set_is_read_from_pyproject_and_normalised() -> None:
    """Pin the *other* half: reading the declarations, and the hyphen rule.

    The sweep compares two derived sets, so it goes green either by both being right
    or by the declared side being wrong in a way that swallows everything. A
    `_declared_distributions` that returned every string it saw — say by failing to
    strip the version specifier — would make `"pytest>=8,<10"` a satisfiable name and
    nothing would ever be flagged again.

    So this asserts against named packages that really are declared, and checks the
    specifier is stripped rather than trusting the split.
    """
    declared = _declared_distributions()
    assert declared, "pyproject.toml declares no dependencies at all — parse failure?"
    for expected in ("pyside6", "musicbrainzngs", "pytest", "tomli-w"):
        assert expected in declared, (
            f"`{expected}` is declared in pyproject.toml but did not survive parsing "
            f"— the requirement split is wrong, and a broken declared set makes the "
            f"whole sweep vacuous"
        )
    # Specifiers must be gone: their presence would turn each entry into a name no
    # import can match, which fails safe, but their *partial* presence would not.
    assert not [d for d in declared if any(c in d for c in "<>=!~[ ;")], (
        f"version specifiers survived the split: {sorted(declared)}"
    )

    satisfiable = _satisfiable_names()
    assert "tomli_w" in satisfiable, (
        "`tomli-w` is imported as `tomli_w`; the hyphen-to-underscore normalisation "
        "is what makes a declared dependency match its import, and without it every "
        "hyphenated package would be reported as undeclared"
    )


@pytest.mark.parametrize("root", SOURCE_ROOTS)
def test_each_source_root_contributes_files(root: str) -> None:
    """Per-root floor, because one empty root hides inside a healthy total.

    The aggregate floor above is satisfied by `src/` alone. If `tests/` or `scripts/`
    stopped being walked — renamed, moved, excluded — the sweep would still report a
    large number and check none of their imports. That is the shape of gap this
    session kept finding: a population that quietly lost a member.
    """
    files = [p for p in _python_files() if p.is_relative_to(REPO_ROOT / root)]
    assert files, f"no Python files found under {root}/ — the sweep is not seeing it"
