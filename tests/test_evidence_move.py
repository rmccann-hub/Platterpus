"""`scripts/evidence_move.py`: HR-2 §5's evidence commit, built the agreed way.

Driven against a real repository in a temporary directory: the builder clones
it at depth 1, as §5b says, and builds the orphan commit from an enumerated list.
The properties §5 asks for are each asserted: a rebuild gives the same ID (§5c's
"either side can rebuild the other's commit"), the identity and both dates are
the agreed ones, the rows parse as §4's manifest and match the commit (§5d), and
a listed entry with nothing behind it is refused rather than skipped (§5b).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evidence_move as em  # noqa: E402 - needs the path line above
from laplang.evidence import parse_manifest  # noqa: E402

DATE = "2026-10-15T12:00:00Z"
LISTED = ["ev/runs/round99", "ev/out/one.log"]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def source(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    files = {
        "ev/runs/round99/README.md": "# round 99\n",
        "ev/runs/round99/full.log": "track 1 ok\n",
        "ev/runs/round99/sub/report.json": '{"ok": true}\n',
        "ev/out/one.log": "one\n",
        "ev/out/spec.md": "stays\n",
        "src/app.py": "print('not evidence')\n",
    }
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(text)
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "main")
    return repo, _git(repo, "rev-parse", "HEAD")


def _build(
    tmp_path: Path, repo: Path, base: str, name: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, str, list[em.Entry]]:
    monkeypatch.setattr(em, "moving_list", lambda: list(LISTED))
    clone = tmp_path / name
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--depth",
            "1",
            "--single-branch",
            "--no-checkout",
            f"file://{repo}",
            str(clone),
        ],
        check=True,
        capture_output=True,
    )
    commit, entries = em.build(base, DATE, clone, None)
    return clone, commit, entries


def test_a_rebuild_gives_the_same_commit_with_the_agreed_identity(
    tmp_path: Path, source: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = source
    clone, first, entries = _build(tmp_path, repo, base, "a", monkeypatch)
    _, second, _ = _build(tmp_path, repo, base, "b", monkeypatch)
    assert first == second
    header = _git(clone, "cat-file", "-p", first)
    assert "\nauthor evidence <evidence@invalid> 1792065600 +0000\n" in header
    assert "\ncommitter evidence <evidence@invalid> 1792065600 +0000\n" in header
    assert "\nparent " not in header  # the first evidence commit is an orphan
    held = _git(clone, "ls-tree", "-r", "--name-only", first).split("\n")
    assert held == [
        "ev/out/one.log",
        "ev/runs/round99/README.md",
        "ev/runs/round99/full.log",
        "ev/runs/round99/sub/report.json",
    ]
    assert [e.path for e in entries] == held
    assert em.check_built(clone, first, entries) == []
    # §5d: the folder's tree is the same object on both branches.
    assert _git(clone, "rev-parse", f"{first}:ev/runs/round99") == _git(
        repo, "rev-parse", f"{base}:ev/runs/round99"
    )


def test_the_rows_parse_as_the_manifest_and_name_the_commit_and_base(
    tmp_path: Path, source: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = source
    clone, commit, entries = _build(tmp_path, repo, base, "a", monkeypatch)
    rows, problems = parse_manifest(em.rows(clone, commit, base, entries))
    assert problems == []
    assert sorted(rows) == [e.path for e in entries]
    row = rows["ev/runs/round99/full.log"]
    assert (row.size, row.evidence_commit, row.last_default_commit) == (
        11,
        commit,
        base,
    )


def test_a_listed_entry_with_nothing_behind_it_is_refused(
    tmp_path: Path, source: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = source
    monkeypatch.setattr(em, "moving_list", lambda: [*LISTED, "ev/runs/round98"])
    clone = tmp_path / "c"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(clone)],
        check=True,
        capture_output=True,
    )
    with pytest.raises(SystemExit, match="round98: nothing at"):
        em.build(base, DATE, clone, None)


def test_a_commit_missing_a_file_fails_the_pre_push_check(
    tmp_path: Path, source: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base = source
    clone, commit, entries = _build(tmp_path, repo, base, "a", monkeypatch)
    extra = em.Entry("ev/runs/round99/missing.log", "100644", "0" * 40, 5)
    assert any(
        "missing.log" in p for p in em.check_built(clone, commit, [*entries, extra])
    )


def test_the_removal_keeps_what_stays_and_deletes_the_rest(
    source: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """HR-2 §5a, HR-2.1 a: the removal deletes every file of a moving folder but
    the README and the files `STAYS` names, by the same predicate as the check."""
    repo, base = source
    monkeypatch.setattr(em, "moving_list", lambda: list(LISTED))
    monkeypatch.setattr(em.evidence_manifest, "STAYS", frozenset({"ev/out/one.log"}))
    gone = em.removal(repo, base)
    assert gone == ["ev/runs/round99/full.log", "ev/runs/round99/sub/report.json"]
