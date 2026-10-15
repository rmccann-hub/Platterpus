"""`scripts/evidence_manifest.py`: the checks that keep HR-2's manifest a promise.

Each case builds a real repository in a temporary directory the way HR-2 §5 says
a move is made: a run folder on `main`, an orphan `evidence` commit holding the
whole folder byte for byte, then a removal commit on `main` that deletes the
folder (keeping its README) and adds `docs/evidence-manifest.tsv`. Every check is
shown holding on that, then failing on one specific breakage, so none of them
can pass by finding nothing.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evidence_manifest as em  # noqa: E402 - needs the path line above

FOLDER = "docs/handshake/artifactsround99"
FILES = {
    f"{FOLDER}/README.md": b"# round 99\n",
    f"{FOLDER}/full.log": b"track 1 ok\ntrack 2 ok\n",
    f"{FOLDER}/report.json": b'{"ok": true}\n',
}
HEADER = "path\tbytes\tsha256\tevidence_commit\tlast_default_commit"


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _rows(evidence: str, last: str, files: dict[str, bytes]) -> str:
    lines = [HEADER]
    for path in sorted(files):
        data = files[path]
        digest = hashlib.sha256(data).hexdigest()
        lines.append(f"{path}\t{len(data)}\t{digest}\t{evidence}\t{last}")
    return "\n".join(lines) + "\n"


def _moved(tmp_path: Path, files: dict[str, bytes] = FILES) -> dict[str, str | Path]:
    """A repository after a move: (root, evidence commit, last default, removal)."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    for path, data in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(data)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "a run filed on main")
    last = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-q", "--orphan", "evidence")
    _git(root, "rm", "-q", "-r", "--cached", ".")
    _git(root, "add", FOLDER)
    _git(root, "commit", "-q", "-m", "evidence: round 99")
    evidence = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-q", "-f", "main")
    for path in files:
        if not path.endswith("README.md"):
            _git(root, "rm", "-q", path)
    (root / "docs" / "evidence-manifest.tsv").write_text(_rows(evidence, last, files))
    _git(root, "add", "docs/evidence-manifest.tsv")
    _git(root, "commit", "-q", "-m", "the move")
    removal = _git(root, "rev-parse", "HEAD")
    return {"root": root, "evidence": evidence, "last": last, "removal": removal}


def _run(root: Path, *args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = em.main(["--root", str(root), *args])
    return code, out.getvalue()


@pytest.fixture
def moved(tmp_path: Path) -> dict[str, str | Path]:
    return _moved(tmp_path)


def _root(moved: dict[str, str | Path]) -> Path:
    root = moved["root"]
    assert isinstance(root, Path)
    return root


def test_a_correct_move_passes_every_check(moved: dict[str, str | Path]) -> None:
    root = _root(moved)
    assert _run(root, "format", "--base", "HEAD^") == (
        0,
        "evidence format: 0 problem(s)\n",
    )
    code, out = _run(root, "rows")
    assert code == 0 and "3 examined" in out, out
    code, out = _run(root, "branch")
    assert code == 0 and "1 examined" in out, out
    assert _run(root, "tags")[0] == 0
    code, out = _run(root, "move", "--removal", str(moved["removal"]), FOLDER)
    assert code == 0, out


def test_rows_since_the_base_examine_only_what_was_added(
    moved: dict[str, str | Path],
) -> None:
    code, out = _run(_root(moved), "rows", "--since", "HEAD")
    assert code == 0 and "0 examined" in out, out


def test_a_row_that_does_not_match_its_file_fails(moved: dict[str, str | Path]) -> None:
    root = _root(moved)
    wrong = dict(FILES)
    wrong[f"{FOLDER}/full.log"] = b"not what was filed\n"
    manifest = root / "docs" / "evidence-manifest.tsv"
    manifest.write_text(_rows(str(moved["evidence"]), str(moved["last"]), wrong))
    code, out = _run(root, "rows")
    assert code == 1 and "full.log: " in out and "its row says" in out, out


def test_a_changed_or_removed_row_breaks_append_only(
    moved: dict[str, str | Path],
) -> None:
    root = _root(moved)
    manifest = root / "docs" / "evidence-manifest.tsv"
    lines = manifest.read_text().splitlines(keepends=True)
    manifest.write_text("".join(lines[:-1]))
    code, out = _run(root, "format", "--base", "HEAD")
    assert code == 1 and "has been removed" in out, out
    manifest.write_text("".join(lines).replace("\t22\t", "\t23\t"))
    code, out = _run(root, "format", "--base", "HEAD")
    assert code == 1 and "has been changed" in out, out


def test_an_evidence_commit_that_changes_a_file_breaks_the_branch(
    moved: dict[str, str | Path],
) -> None:
    root = _root(moved)
    _git(root, "checkout", "-q", "evidence")
    (root / FOLDER / "full.log").write_bytes(b"rewritten\n")
    _git(root, "commit", "-q", "-am", "an edit, which evidence never takes")
    _git(root, "checkout", "-q", "-f", "main")
    code, out = _run(root, "branch")
    assert code == 1 and "changes or removes a file" in out, out


def test_a_merge_on_evidence_breaks_the_branch(moved: dict[str, str | Path]) -> None:
    root = _root(moved)
    _git(root, "checkout", "-q", "evidence")
    _git(
        root,
        "merge",
        "-q",
        "--allow-unrelated-histories",
        "-s",
        "ours",
        "main",
        "-m",
        "a merge, which evidence never takes",
    )
    _git(root, "checkout", "-q", "-f", "main")
    code, out = _run(root, "branch")
    assert code == 1 and "parents" in out, out


def test_a_tag_on_evidence_fails(moved: dict[str, str | Path]) -> None:
    root = _root(moved)
    _git(root, "tag", "v9.9.9", str(moved["evidence"]))
    code, out = _run(root, "tags")
    assert code == 1 and "refs/tags/v9.9.9" in out, out


def test_a_deleted_path_without_a_row_fails_the_move(
    moved: dict[str, str | Path],
) -> None:
    root = _root(moved)
    partial = {p: d for p, d in FILES.items() if not p.endswith("report.json")}
    _git(root, "checkout", "-q", "HEAD^")
    for path in FILES:
        if not path.endswith("README.md"):
            _git(root, "rm", "-q", path)
    (root / "docs" / "evidence-manifest.tsv").write_text(
        _rows(str(moved["evidence"]), str(moved["last"]), partial)
    )
    _git(root, "add", "docs/evidence-manifest.tsv")
    _git(root, "commit", "-q", "-m", "a move that forgot a row")
    code, out = _run(root, "move", "--removal", "HEAD", FOLDER)
    assert code == 1 and "report.json: deleted by" in out, out


def test_a_folder_whose_trees_differ_fails_the_move(
    moved: dict[str, str | Path],
) -> None:
    root = _root(moved)
    _git(root, "checkout", "-q", "evidence")
    (root / FOLDER / "extra.txt").write_text("not on main\n")
    _git(root, "add", FOLDER)
    _git(root, "commit", "-q", "-m", "evidence with one more file")
    other = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-q", "-f", str(moved["last"]))
    for path in FILES:
        if not path.endswith("README.md"):
            _git(root, "rm", "-q", path)
    (root / "docs" / "evidence-manifest.tsv").write_text(
        _rows(other, str(moved["last"]), FILES)
    )
    _git(root, "add", "docs/evidence-manifest.tsv")
    _git(root, "commit", "-q", "-m", "a move whose evidence tree differs")
    code, out = _run(root, "move", "--removal", "HEAD", FOLDER)
    assert code == 1 and "tree" in out and FOLDER in out, out


def test_a_move_check_of_no_folders_is_refused(moved: dict[str, str | Path]) -> None:
    code, out = _run(_root(moved), "move", "--removal", str(moved["removal"]))
    assert code == 1 and "not a check" in out, out


def test_before_the_move_there_is_nothing_to_check_and_it_says_so(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "one")
    for mode in ("format", "rows", "branch", "tags"):
        code, out = _run(root, mode)
        assert code == 0, (mode, out)
    assert "0 examined" in _run(root, "rows")[1]


def test_laps_reports_citation_failures_and_nothing_else(
    moved: dict[str, str | Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`laps` re-checks citations (LSL.4). An old lap's other findings were its
    own round's business, so a REFUSED A3 must not fail the evidence job, and a
    REFUSED LSL.4 must."""
    from dataclasses import dataclass

    from laplang import cli

    root = _root(moved)
    lap = root / "docs" / "handshake" / "outbound" / "round-99-lap-01.md"
    lap.parent.mkdir(parents=True, exist_ok=True)
    lap.write_text(
        f"evidence: platterpus@{str(moved['evidence'])[:12]}:{FOLDER}/full.log\n"
    )

    @dataclass
    class P:
        rule: str
        severity: str
        line: int
        message: str

    @dataclass
    class L:
        problems: list[P]

    found = [P("A3", "REFUSED", 3, "not about evidence")]
    monkeypatch.setattr(cli, "check_path", lambda path, root: L(found))
    assert em.check_laps(root) == ([], 1)
    found.append(P("LSL.4", "REFUSED", 1, "hashes differently"))
    problems, examined = em.check_laps(root)
    assert examined == 1 and len(problems) == 1 and "hashes differently" in problems[0]


def test_unchanged_holds_before_the_removal_and_says_when_a_file_drifted(
    moved: dict[str, str | Path],
) -> None:
    """HR-2.1 b: before the removal merges, each moved folder on the default
    branch must equal its tree at the evidence commit. Run against the commit
    the evidence was built from (`last`), then against one that changed a file."""
    root = _root(moved)
    code, out = _run(root, "unchanged", "--ref", str(moved["last"]))
    assert code == 0 and "1 examined" in out, out
    _git(root, "checkout", "-q", "-b", "drift", str(moved["last"]))
    (root / FOLDER / "full.log").write_bytes(b"edited after the build\n")
    _git(root, "commit", "-q", "-am", "a file changed after the build")
    _git(root, "checkout", "-q", "-f", str(moved["removal"]))
    code, out = _run(root, "unchanged", "--ref", "drift")
    assert code == 1 and "changed after the build" in out, out


def test_unchanged_skips_a_folder_already_removed(moved: dict[str, str | Path]) -> None:
    """After the removal merges only the README is left, and the check is over:
    it examines nothing rather than failing every later push."""
    code, out = _run(_root(moved), "unchanged", "--ref", str(moved["removal"]))
    assert code == 0 and "0 examined" in out, out


def test_a_removal_that_deletes_a_file_that_stays_fails_the_move(
    moved: dict[str, str | Path],
) -> None:
    root = _root(moved)
    _git(root, "rm", "-q", f"{FOLDER}/README.md")
    _git(root, "commit", "-q", "-m", "the README went too")
    code, out = _run(root, "move", "--removal", "HEAD", FOLDER)
    assert code == 1 and "stays on the default branch" in out, out


def test_what_stays_on_the_default_branch() -> None:
    assert em.stays_on_default("docs/handshake/artifactsround32/README.md")
    assert em.stays_on_default("docs/handshake/outbound/artifacts/lsl-amendments-1.md")
    assert not em.stays_on_default(
        "docs/handshake/outbound/artifacts/round-15-lap-13-run-report.json"
    )
    assert "docs/handshake/outbound/artifacts" in em.MOVING_FOLDERS


#: A run file named the way the fork's 2026-10-13 run names its album folders,
#: with a ratio colon and a single angle quote. git quotes such a path unless asked
#: for `-z`, and the quoted form matches no manifest row.
NON_ASCII: dict[str, bytes] = {
    **FILES,
    f"{FOLDER}/full acceptance\u2236 angle\u2039bracket.log": b"track 3 ok\n",
}


def test_a_moved_path_with_non_ascii_bytes_matches_its_row(tmp_path: Path) -> None:
    """Found verifying the fork's move (round 33): 29 of its 997 deleted paths hold
    non-ASCII bytes, and the move check read each one in git's quoted form, so it
    reported a missing manifest row the manifest has."""
    moved = _moved(tmp_path, NON_ASCII)
    root = _root(moved)
    code, out = _run(root, "move", "--removal", str(moved["removal"]), FOLDER)
    assert code == 0, out
    code, out = _run(root, "rows")
    assert code == 0 and "4 examined" in out, out
