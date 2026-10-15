"""Evidence citations in the lap checker (HR-2 §6, protocol v9).

After the move, run evidence lives on an orphan `evidence` branch and a lap cites
it as `<repo>@<evidence commit>:<path>` with its SHA-256. These drive
`laplang.refs.Trees` against real repositories built in a temporary directory:
a "GitHub" repository with `main` and `evidence`, and a session's clone that
fetched `main` only, which is what §7's refspec leaves a session with.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from laplang.evidence import (  # noqa: E402 - needs the path line above
    HEADER,
    STRICT_ENV,
    parse_manifest,
)
from laplang.refs import Trees, parse_artifact  # noqa: E402

RUN = "docs/handshake/artifactsround99/round99full.log"
LOG = b"line one\nline two\nline three\n"


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _manifest(rows: list[tuple[str, bytes, str]]) -> str:
    lines = [HEADER]
    for path, data, commit in sorted(rows):
        sha = hashlib.sha256(data).hexdigest()
        lines.append(f"{path}\t{len(data)}\t{sha}\t{commit}\t{'b' * 40}")
    return "\n".join(lines) + "\n"


def _world(tmp_path: Path, *, row_data: bytes | None = LOG) -> dict[str, object]:
    """A remote with `main` and an orphan `evidence`, and a clone of `main` only."""
    remote = tmp_path / "remote"
    remote.mkdir()
    _git(remote, "init", "-q", "-b", "main")
    _git(remote, "config", "uploadpack.allowFilter", "true")
    _git(remote, "config", "uploadpack.allowAnySHA1InWant", "true")
    (remote / "README.md").write_text("main\n")
    _git(remote, "add", "README.md")
    _git(remote, "commit", "-q", "-m", "main one")
    # The evidence branch: an orphan commit holding the run file.
    _git(remote, "checkout", "-q", "--orphan", "evidence")
    _git(remote, "rm", "-q", "-r", "--cached", ".")
    (remote / "README.md").unlink()
    run = remote / RUN
    run.parent.mkdir(parents=True)
    run.write_bytes(LOG)
    _git(remote, "add", RUN)
    _git(remote, "commit", "-q", "-m", "evidence: one run")
    evidence_commit = _git(remote, "rev-parse", "HEAD")
    _git(remote, "checkout", "-q", "-f", "main")
    # The manifest row lands on main afterwards (HR-2 §10).
    if row_data is not None:
        (remote / "docs").mkdir(exist_ok=True)
        (remote / "docs" / "evidence-manifest.tsv").write_text(
            _manifest([(RUN, row_data, evidence_commit)])
        )
        _git(remote, "add", "docs/evidence-manifest.tsv")
        _git(remote, "commit", "-q", "-m", "manifest")
    clone = tmp_path / "clone"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--single-branch",
            "--branch",
            "main",
            f"file://{remote}",
            str(clone),
        ],
        check=True,
        capture_output=True,
    )
    return {"remote": remote, "clone": clone, "evidence": evidence_commit}


def _resolve(root: Path, token: str) -> tuple[str, str]:
    ref = parse_artifact(token)
    assert ref is not None, token
    got = Trees({"platterpus": root, "cyanrip": None}, {"platterpus": "HEAD"}).artifact(
        ref, "platterpus"
    )
    return got.outcome, got.message


def test_a_filed_citation_is_fetched_by_hash_and_resolves(tmp_path: Path) -> None:
    """The session never fetched `evidence`: the checker fetches the one commit
    into a temporary repository and checks the file against its row."""
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    assert "evidence" not in _git(clone, "branch", "-a")
    outcome, message = _resolve(clone, f"platterpus@{world['evidence']}:{RUN}:2-3")
    assert outcome == "ok", message
    # The working clone was not made shallow or given the branch (§7).
    assert _git(clone, "rev-parse", "--is-shallow-repository") == "false"
    assert "evidence" not in _git(clone, "branch", "-a")


def test_a_line_range_past_the_file_is_still_refused(tmp_path: Path) -> None:
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    outcome, _ = _resolve(clone, f"platterpus@{world['evidence']}:{RUN}:2-9")
    assert outcome == "refused"


def test_a_file_that_does_not_hash_to_its_row_is_refused(tmp_path: Path) -> None:
    world = _world(tmp_path, row_data=b"not the bytes that were filed\n")
    clone = world["clone"]
    assert isinstance(clone, Path)
    outcome, message = _resolve(clone, f"platterpus@{world['evidence']}:{RUN}")
    assert outcome == "refused" and "manifest row says" in message


def test_an_evidence_commit_with_no_manifest_row_is_refused(tmp_path: Path) -> None:
    """HR-2 §6b: the row comes first. The clone here holds the evidence branch, so
    the commit is visibly on it, and the missing row is the refusal."""
    world = _world(tmp_path, row_data=None)
    clone = world["clone"]
    assert isinstance(clone, Path)
    _git(
        clone,
        "fetch",
        "-q",
        "origin",
        "+refs/heads/evidence:refs/remotes/origin/evidence",
    )
    outcome, message = _resolve(clone, f"platterpus@{world['evidence']}:{RUN}")
    assert outcome == "refused" and "no row" in message


def test_a_citation_made_before_the_move_keeps_the_old_rules(tmp_path: Path) -> None:
    """§6d: a commit on the ref of record resolves as it always did, even though
    its path now has a manifest row (the row's commit is on `evidence`)."""
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    head = _git(clone, "rev-parse", "HEAD")
    outcome, message = _resolve(clone, f"platterpus@{head}:README.md")
    assert outcome == "ok", message


def test_a_commit_that_cannot_be_fetched_is_unchecked_and_strict_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    _git(clone, "remote", "set-url", "origin", f"file://{tmp_path}/nowhere")
    token = f"platterpus@{world['evidence']}:{RUN}"
    monkeypatch.delenv(STRICT_ENV, raising=False)
    outcome, message = _resolve(clone, token)
    assert outcome == "unchecked" and message.startswith("UNCHECKED")
    monkeypatch.setenv(STRICT_ENV, "1")
    outcome, message = _resolve(clone, token)
    assert outcome == "refused" and "evidence job" in message


def test_a_commit_off_the_evidence_branch_is_refused(tmp_path: Path) -> None:
    """A manifest row naming a commit that `evidence` does not reach: the file is
    right, the branch is wrong (§6a)."""
    world = _world(tmp_path)
    remote = world["remote"]
    clone = world["clone"]
    assert isinstance(remote, Path) and isinstance(clone, Path)
    _git(remote, "checkout", "-q", "-b", "elsewhere", str(world["evidence"]))
    (remote / "extra.txt").write_text("x\n")
    _git(remote, "add", "extra.txt")
    _git(remote, "commit", "-q", "-m", "not evidence")
    stray = _git(remote, "rev-parse", "HEAD")
    _git(remote, "checkout", "-q", "main")
    (remote / "docs" / "evidence-manifest.tsv").write_text(
        _manifest([(RUN, LOG, stray)])
    )
    _git(remote, "commit", "-q", "-am", "row naming a stray commit")
    _git(clone, "pull", "-q", "--ff-only")
    outcome, message = _resolve(clone, f"platterpus@{stray}:{RUN}")
    assert outcome == "refused" and "not reachable" in message


def test_the_manifest_parser_names_every_way_a_row_breaks_hr2_section_4() -> None:
    good = f"{RUN}\t3\t{'a' * 64}\t{'c' * 40}\t"
    rows, problems = parse_manifest(f"{HEADER}\n{good}\n")
    assert problems == [] and RUN in rows and rows[RUN].last_default_commit == ""
    broken = "\n".join(
        [
            HEADER,
            f"z\t3\t{'a' * 64}\t{'c' * 40}\t",
            f"a\tx\t{'A' * 64}\tabc\tdef",
            f"/abs\t1\t{'a' * 64}\t{'c' * 40}\t",
            f"z\t3\t{'a' * 64}\t{'c' * 40}\t",
            "too\tfew",
        ]
    )
    _, problems = parse_manifest(broken)
    text = " | ".join(problems)
    for expected in (
        "does not end with a newline",
        "bytes is not a whole number",
        "sha256 is not 64",
        "evidence_commit is not a full",
        "last_default_commit is neither",
        "not a plain repository path",
        "has a second row",
        "cells, not 5",
    ):
        assert expected in text, (expected, problems)
    _, problems = parse_manifest(
        f"{HEADER}\nb\t1\t{'a' * 64}\t{'c' * 40}\t\na\t1\t{'a' * 64}\t{'c' * 40}\t\n"
    )
    assert any("out of order" in p for p in problems)
    assert parse_manifest("wrong header\n")[1]


def test_an_old_citation_of_a_moved_file_still_resolves_at_its_default_commit(
    tmp_path: Path,
) -> None:
    """§6d, the case that matters: a lap written before the move cites a run file
    at a default-branch commit; after the move that path HAS a manifest row. The
    citation keeps the old rules (the commit is on the ref of record), rather than
    being refused for naming a commit that `evidence` does not reach."""
    world = _world(tmp_path, row_data=None)
    remote = world["remote"]
    assert isinstance(remote, Path)
    (remote / RUN).parent.mkdir(parents=True, exist_ok=True)
    (remote / RUN).write_bytes(LOG)
    _git(remote, "add", RUN)
    _git(remote, "commit", "-q", "-m", "a run filed on main, before the move")
    before_move = _git(remote, "rev-parse", "HEAD")
    _git(remote, "rm", "-q", RUN)
    (remote / "docs").mkdir(exist_ok=True)  # `git rm` took the emptied folders
    (remote / "docs" / "evidence-manifest.tsv").write_text(
        HEADER
        + "\n"
        + f"{RUN}\t{len(LOG)}\t{hashlib.sha256(LOG).hexdigest()}\t"
        + f"{world['evidence']}\t{before_move}\n"
    )
    _git(remote, "add", "docs/evidence-manifest.tsv")
    _git(remote, "commit", "-q", "-m", "the move: removal and manifest")
    clone = world["clone"]
    assert isinstance(clone, Path)
    _git(clone, "pull", "-q", "--ff-only")
    outcome, message = _resolve(clone, f"platterpus@{before_move[:12]}:{RUN}:1-3")
    assert outcome == "ok", message


def test_the_fetcher_fetches_a_commit_once_and_reads_trees_it_lacks(
    tmp_path: Path,
) -> None:
    """A second file of one commit costs a `git show`, not a second fetch; and
    §5d's tree comparison works on a commit only the remote holds."""
    from laplang.evidence import Fetcher

    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    sha = str(world["evidence"])
    fetcher = Fetcher()
    assert fetcher.read(clone, sha, RUN) == LOG
    remote_url = _git(clone, "remote", "get-url", "origin")
    assert fetcher._fetched == {(remote_url, sha)}
    # With the remote gone, the cached commit still answers; a new one cannot.
    _git(clone, "remote", "set-url", "origin", f"file://{tmp_path}/nowhere")
    fetcher._temps[f"file://{tmp_path}/nowhere"] = fetcher._temps[remote_url]
    fetcher._fetched.add((f"file://{tmp_path}/nowhere", sha))
    assert fetcher.read(clone, sha, RUN) == LOG
    folder = RUN.rsplit("/", 1)[0]
    remote = world["remote"]
    assert isinstance(remote, Path)
    assert fetcher.object_id(clone, sha, folder) == _git(
        remote, "rev-parse", f"{sha}:{folder}"
    )
    assert fetcher.object_id(clone, "f" * 40, folder) is None


def _lap_citing(tmp_path: Path, clone: Path, citation: str) -> list[str]:
    """Check a one-statement lap whose evidence is `citation`; the LSL.4 refusals."""
    from laplang.cli import check_path

    lap = tmp_path / "round-99-lap-02.md"
    lap.write_text(
        "HANDSHAKE-PROTOCOL: 9\nHANDSHAKE-ROUND: 99\nHANDSHAKE-LAP: 2\n"
        "HANDSHAKE-FROM: platterpus\nHANDSHAKE-VERDICT: OPEN\n\nLSL: 1\n\n"
        "S1 FACT measured: The run is filed.\n"
        f"  evidence: {citation}\n",
        encoding="utf-8",
    )
    checked = check_path(lap, root=clone, amendments=frozenset())
    return [
        p.message
        for p in checked.problems
        if p.severity == "REFUSED" and p.rule == "LSL.4"
    ]


def test_the_sha256_a_lap_writes_beside_a_citation_is_checked(tmp_path: Path) -> None:
    """HR-2 §6a cites evidence "with its SHA-256". Until 2026-10-15 the checker
    compared the file with its manifest row and never read the hash the lap
    wrote, so one wrong hex digit passed (round 33 lap 6 D2)."""
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    good = hashlib.sha256(LOG).hexdigest()
    bad = good[:-1] + ("0" if good[-1] != "0" else "1")
    cite = f"platterpus@{world['evidence']}:{RUN}"
    assert _lap_citing(tmp_path, clone, f"{cite} sha256 {good}") == []
    refused = _lap_citing(tmp_path, clone, f"{cite} sha256 {bad}")
    assert len(refused) == 1, refused
    assert f"the lap quotes {bad}" in refused[0], refused
    assert f"the file hashes {good}" in refused[0], refused


def test_a_quoted_value_that_is_not_a_sha256_is_refused(tmp_path: Path) -> None:
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    refused = _lap_citing(
        tmp_path, clone, f"platterpus@{world['evidence']}:{RUN} sha256 e8e1d9c7"
    )
    assert any("is not a SHA-256" in m for m in refused), refused


def test_a_quoted_sha256_on_an_ordinary_citation_is_checked_too(tmp_path: Path) -> None:
    """Not only evidence: a file on the default branch, cited with a hash, must
    hash to it as well."""
    world = _world(tmp_path)
    clone = world["clone"]
    assert isinstance(clone, Path)
    head = _git(clone, "rev-parse", "HEAD")
    right = hashlib.sha256(b"main\n").hexdigest()
    cite = f"platterpus@{head}:README.md"
    assert _lap_citing(tmp_path, clone, f"{cite} sha256 {right}") == []
    wrong = "0" * 64
    refused = _lap_citing(tmp_path, clone, f"{cite} sha256 {wrong}")
    assert any(f"the lap quotes {wrong}" in m for m in refused), refused
