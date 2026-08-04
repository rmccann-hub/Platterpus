"""``PLANNING.md``'s module map must cover the modules that exist.

**Why this exists.** `CLAUDE.md` names `PLANNING.md` as *"architecture, module
map, and the numbered KDD decision log"* and gives it authority on implementation
choices. `PLANNING.md` itself opens §2 with *"One paragraph per module, no more"*
— a promise of completeness. It had drifted to **13 of 122 modules missing from
both the directory tree and the per-module list**, including `hard_exit.py` and
`ripper_identity.py`, which `CLAUDE.md`'s own Critical rules and Code conventions
name by name. A contributor sent to the module map to find out what
`ripper_identity` does would have found nothing there and concluded it does not
exist.

Nothing checked it, and nothing was going to: a map is only ever wrong by
omission, and omissions are invisible in a diff. This is the same class as the
docs-index gap (`tests/test_doc_index_completeness.py`) and the same fix — turn
the promise into a gate.

**What is deliberately not checked.** Not the *content* of an entry beyond
existence and a minimum length: judging whether a paragraph is a good description
is a review question, not a test. And not the reverse direction beyond a
sanity floor — `PLANNING.md` legitimately names files that are not source
modules (`scripts/…`, the generated `_build.py`, `setup.py` as a thing we do
*not* use), so "every name resolves" would fail on correct prose.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PLANNING = _REPO_ROOT / "PLANNING.md"
_SRC = _REPO_ROOT / "src" / "platterpus"

#: Modules a map entry would say nothing about. `__init__.py` files exist to make
#: packages; the map covers the packages instead.
_SKIP_NAMES: frozenset[str] = frozenset({"__init__.py"})

#: Minimum characters in a §2 bullet before it counts as a description. The real
#: bullets run to several sentences; this only catches a placeholder.
_MIN_BULLET_CHARS = 60


def _sections() -> tuple[str, str]:
    """``PLANNING.md``'s §1 directory tree and §2 per-module responsibility text.

    Sliced by heading rather than by line number so inserting a KDD does not
    silently move the window — which would make this test read the wrong region
    and pass for the wrong reason.
    """
    lines = _PLANNING.read_text(encoding="utf-8").splitlines()

    def index_of(prefix: str) -> int:
        for i, line in enumerate(lines):
            if line.startswith(prefix):
                return i
        raise AssertionError(f"PLANNING.md has no heading starting {prefix!r}")

    tree_start = index_of("## 1. Directory tree")
    resp_start = index_of("## 2. Per-module")
    resp_end = index_of("## 3. ")
    return (
        "\n".join(lines[tree_start:resp_start]),
        "\n".join(lines[resp_start:resp_end]),
    )


def _source_modules() -> list[Path]:
    return sorted(
        p
        for p in _SRC.rglob("*.py")
        if p.name not in _SKIP_NAMES and "__pycache__" not in p.parts
    )


def test_every_source_module_is_in_the_directory_tree() -> None:
    """§1 is the map a contributor scans first."""
    tree, _ = _sections()
    modules = _source_modules()
    missing = sorted(p.name for p in modules if p.name not in tree)
    assert not missing, (
        f"PLANNING.md §1 (Directory tree) omits {len(missing)} module(s): "
        + ", ".join(missing)
    )
    # Floor: the glob must have found a real codebase, or "nothing is missing" is
    # a statement about nothing.
    assert len(modules) >= 80, f"only {len(modules)} modules found — glob broken?"


def test_every_source_module_has_a_responsibility_bullet() -> None:
    """§2 promises "one paragraph per module". Held to it.

    A bullet, not a mention: a module named inside *another* module's paragraph is
    a cross-reference, which is how `rip_files.py` could have looked covered while
    having no entry of its own.
    """
    _, resp = _sections()
    bullets: dict[str, str] = {}
    for match in re.finditer(
        r"^- \*\*`(?P<name>[\w./]+\.py)`\*\*(?P<body>.*)$", resp, re.MULTILINE
    ):
        bullets[Path(match.group("name")).name] = match.group("body")

    modules = _source_modules()
    missing = sorted(p.name for p in modules if p.name not in bullets)
    assert not missing, (
        f"PLANNING.md §2 (Per-module responsibility) has no bullet for "
        f"{len(missing)} module(s): " + ", ".join(missing)
    )

    thin = sorted(
        f"{name} ({len(body)} chars)"
        for name, body in bullets.items()
        if len(body) < _MIN_BULLET_CHARS
    )
    assert not thin, (
        "these §2 bullets are too short to be the promised paragraph: "
        + ", ".join(thin)
    )
    # Floors, both directions: the bullet regex must be finding bullets, and the
    # module glob must be finding modules.
    assert len(bullets) >= 80, (
        f"only {len(bullets)} §2 bullets parsed — has the bullet format changed? "
        "A regex that stopped matching would make this test vacuous."
    )
    assert len(modules) >= 80, f"only {len(modules)} modules found — glob broken?"


def test_the_map_does_not_describe_source_modules_that_are_gone() -> None:
    """The converse, scoped to names that look like package modules.

    A deleted module keeps its paragraph, and the paragraph keeps reading as
    current — `whipper_backend.py` was removed in KDD-18 and its description
    would have been indistinguishable from a live one. Scoped to bare
    `foo.py` bullets: `PLANNING.md` legitimately names `scripts/…` files, the
    generated `_build.py`, and `setup.py` as something we deliberately do not
    use, so a blanket "every name resolves" would fail on correct prose.
    """
    _, resp = _sections()
    # Every `.py` that EXISTS — not `_source_modules()`, which skips `__init__.py`
    # for *coverage* purposes. Reusing that filter here made the test report the
    # `__init__.py` bullet as describing a deleted module, when `PLANNING.md`
    # rightly describes it as the version holder. A skip-list built for one
    # question is the wrong input to a different one.
    present = {p.name for p in _SRC.rglob("*.py") if "__pycache__" not in p.parts}
    named = {
        Path(m.group("name")).name
        for m in re.finditer(r"^- \*\*`(?P<name>[\w./]+\.py)`\*\*", resp, re.MULTILINE)
    }
    phantoms = sorted(named - present)
    assert not phantoms, (
        "PLANNING.md §2 has responsibility bullets for modules that no longer "
        "exist: " + ", ".join(phantoms)
    )
    assert len(named) >= 80, f"only {len(named)} bullets parsed"
