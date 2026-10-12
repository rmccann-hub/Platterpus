"""`scripts/laplang/commit_map.py`: reading the map a history rewrite leaves.

**Why this exists (2026-10-12).** The owner rewrote this repository's commit
metadata to remove personal information, which gave every commit a new ID.
Citations keep their old IDs (a sent lap is never edited), and three readers
resolve them through the map: the lap checker, the reachability test and the
`HANDSHAKE-OUR-PIN` check. They share this one module, so its own behaviour is
pinned here: what it refuses, and the three ways a lookup can go wrong (an
ambiguous abbreviation, an ID rewritten twice, and a cycle).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
MODULE_PATH: Final[Path] = REPO_ROOT / "scripts" / "laplang" / "commit_map.py"

A: Final[str] = "a" * 40
B: Final[str] = "b" * 40
C: Final[str] = "c" * 40


@pytest.fixture(scope="module")
def cm() -> ModuleType:
    """Loaded by path, the way the tests that depend on it load it."""
    name = "platterpus_commit_map"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: One case per refusal `parse_map` and `load` can make: (file name, content,
#: words the problem must contain).
MALFORMED: Final[list[tuple[str, str, str]]] = [
    ("commit-map-2026-10-12.txt", f"{A} {B}\n", "first line"),
    ("commit-map-2026-10-12.txt", f"old new\n{A} {A}\n", "mapped to itself"),
    ("commit-map-2026-10-12.txt", f"old new\n{A} {B}\n{A} {C}\n", "listed twice"),
    ("commit-map-2026-10-12.txt", f"old new\n{A} {B}\n{B} {C}\n", "both an old"),
    ("commit-map-2026-10-12.txt", f"old new\n{A[:39]} {B}\n", "not '<old"),
    ("commit-map-2026-10-12.txt", f"old new\n{A.upper()} {B}\n", "not '<old"),
    ("commit-map-today.txt", f"old new\n{A} {B}\n", "must be named"),
]


def _write(root: Path, name: str, text: str) -> None:
    folder = root / "docs" / "handshake"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="ascii")


def test_a_repository_with_no_map_answers_nothing(
    cm: ModuleType, tmp_path: Path
) -> None:
    found, problems = cm.load(tmp_path)
    assert problems == [] and found.pairs == {} and found.current("abc1234") is None


def test_an_old_id_maps_to_its_replacement_by_any_abbreviation(
    cm: ModuleType, tmp_path: Path
) -> None:
    _write(tmp_path, "commit-map-2026-10-12.txt", f"old new\n{A} {B}\n")
    found, problems = cm.load(tmp_path)
    assert problems == []
    assert found.current(A) == B
    assert found.current(A[:7]) == B
    assert found.current(B) is None, "a new ID is not an old one"
    assert found.current("a" * 6) is None, "shorter than a citation can be"
    assert found.current("not-hex") is None


def test_an_ambiguous_abbreviation_names_no_commit(
    cm: ModuleType, tmp_path: Path
) -> None:
    first = "1234567" + "0" * 33
    second = "1234567" + "f" * 33
    _write(
        tmp_path, "commit-map-2026-10-12.txt", f"old new\n{first} {A}\n{second} {B}\n"
    )
    found, problems = cm.load(tmp_path)
    assert problems == []
    assert found.current("1234567") is None
    assert found.current("12345670") == A


def test_an_id_rewritten_twice_reaches_todays_id(
    cm: ModuleType, tmp_path: Path
) -> None:
    _write(tmp_path, "commit-map-2026-10-12.txt", f"old new\n{A} {B}\n")
    _write(tmp_path, "commit-map-2031-01-01.txt", f"old new\n{B} {C}\n")
    found, problems = cm.load(tmp_path)
    assert problems == []
    assert found.sources == ["commit-map-2026-10-12.txt", "commit-map-2031-01-01.txt"]
    assert found.current(A[:9]) == C


def test_a_cycle_across_files_answers_nothing(cm: ModuleType, tmp_path: Path) -> None:
    _write(tmp_path, "commit-map-2026-10-12.txt", f"old new\n{A} {B}\n")
    _write(tmp_path, "commit-map-2031-01-01.txt", f"old new\n{B} {A}\n")
    found, _ = cm.load(tmp_path)
    assert found.current(A) is None


def test_every_refusal_has_a_malformed_case() -> None:
    """Floor for the sweep below: it parametrizes over `MALFORMED`, so an
    emptied table would pass having checked nothing."""
    assert len(MALFORMED) >= 7
    said = {case[2] for case in MALFORMED}
    assert {"first line", "mapped to itself", "listed twice", "both an old"} <= said


@pytest.mark.parametrize(("name", "text", "said"), MALFORMED)
def test_a_malformed_map_is_reported_and_never_raises(
    cm: ModuleType, tmp_path: Path, name: str, text: str, said: str
) -> None:
    _write(tmp_path, name, text)
    _, problems = cm.load(tmp_path)
    assert any(said in p for p in problems), problems


def test_a_second_file_cannot_remap_an_old_id(cm: ModuleType, tmp_path: Path) -> None:
    _write(tmp_path, "commit-map-2026-10-12.txt", f"old new\n{A} {B}\n")
    _write(tmp_path, "commit-map-2031-01-01.txt", f"old new\n{A} {C}\n")
    found, problems = cm.load(tmp_path)
    assert found.current(A) == B
    assert any("already mapped" in p for p in problems), problems


def test_the_header_is_the_one_filter_repo_writes(cm: ModuleType) -> None:
    """The map is committed as `git filter-repo` wrote it (filtered to the
    commits that were pushed), so the header must be filter-repo's own:
    `old` and `new`, padded with spaces to the width of an ID."""
    pairs, problems = cm.parse_map(f"old{' ' * 38}new\n{A} {B}\n", "x")
    assert problems == [] and pairs == [(A, B)]


def test_a_rerun_at_an_old_id_checks_out_the_commit_that_replaced_it(
    tmp_path: Path,
) -> None:
    """LSL's `--rerun` checks out the commit a lap names. A lap sent before the
    rewrite names an old ID, which no longer exists; the re-run must happen at
    the commit the map says replaced it, and must fail without the map."""
    import subprocess

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from laplang.scratch import Scratch  # noqa: PLC0415 - needs the path line above

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(clone), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout.strip()

    clone = tmp_path / "clone"
    clone.mkdir()
    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    (clone / "f").write_text("f\n", encoding="utf-8")
    git("add", "f")
    git("commit", "-q", "-m", "f")
    current = git("rev-parse", "HEAD")
    gone = "0123456789abcdef0123456789abcdef01234567"

    without = Scratch(clone)
    try:
        assert isinstance(without.tree(gone[:9]), str), "an unknown ID has no checkout"
    finally:
        without.close()

    _write(clone, "commit-map-2026-10-12.txt", f"old new\n{gone} {current}\n")
    with_map = Scratch(clone)
    try:
        tree = with_map.tree(gone[:9])
        assert isinstance(tree, Path), tree
        assert (tree / "f").read_text(encoding="utf-8") == "f\n"
    finally:
        with_map.close()
