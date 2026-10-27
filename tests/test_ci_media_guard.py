"""Behavioural tests for `ci.yml`'s `media-guard` job, the server half of rule #8.

**Why this file exists (the 2026-10-27 review, item 1.1).** The job listed the
change's file names one per LINE and matched each line against `\\.flac$` and its
siblings. git prints a name outside ASCII quoted and octal-escaped while
`core.quotePath` is on, which is git's default: `Björk.flac` comes out as
`"Bj\\303\\266rk.flac"`, closing quote included, so the pattern never matched it
and a required status check on the one rule here with legal consequences reported
a clean scan. The job now lists names with `-z` and matches NUL-terminated records.

These tests run the step's OWN script, extracted from `ci.yml`, against a real
temporary repository, the way `tests/test_changelog_dependabot_exemption.py` does
for the changelog gate: the defect was in behaviour on a real `git` listing, and
reading the YAML would not have shown it passing.

No real audio is created anywhere here (rule #8 applies to the tests too). The
fixtures are ordinary text files with audio EXTENSIONS, under `tmp_path`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CI_YML: Final[Path] = REPO_ROOT / ".github" / "workflows" / "ci.yml"
EXTENSIONS: Final[Path] = REPO_ROOT / ".githooks" / "audio-extensions.txt"
STEP_NAME: Final[str] = "Reject audio/copyrighted media (Critical Rule #8)"
#: A name git quotes under `core.quotePath`, which is what slipped past.
NON_ASCII_AUDIO: Final[str] = "Björk.flac"

_GIT: Final[str | None] = shutil.which("git")

pytestmark = pytest.mark.skipif(_GIT is None, reason="needs git on PATH")


def _step_script() -> str:
    """The `run: |` block of the media-guard step, dedented, read from `ci.yml`.

    Extracted by indentation rather than a YAML parser, because PyYAML is not one
    of this project's dependencies. The block ends at the first line indented
    less than its own first line.
    """
    lines = CI_YML.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, ln in enumerate(lines) if ln.strip() == f"- name: {STEP_NAME}"
    )
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body: list[str] = []
    indent: int | None = None
    for line in lines[run_at + 1 :]:
        if line.strip() == "":
            body.append("")
            continue
        here = len(line) - len(line.lstrip(" "))
        if indent is None:
            indent = here
        if here < indent:
            break
        body.append(line[indent:])
    script = "\n".join(body)
    # Floor: an extraction that found nothing would make every refusal below pass
    # for a reason that has nothing to do with audio.
    assert "audio-extensions.txt" in script and "ls-files" in script, script[:400]
    return script


def _git(repo: Path, *args: str) -> str:
    assert _GIT is not None
    return subprocess.run(
        [_GIT, "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository holding the real extension list and one commit."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    (work / ".githooks").mkdir()
    shutil.copyfile(EXTENSIONS, work / ".githooks" / "audio-extensions.txt")
    (work / "README.md").write_text("# base\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "base")
    return work


def _add_and_commit(repo: Path, name: str) -> tuple[str, str]:
    """Commit one text file called `name`; return the (before, after) push range."""
    before = _git(repo, "rev-parse", "HEAD")
    (repo / name).write_text("not audio, just a name\n", encoding="utf-8")
    _git(repo, "add", "-f", "--", name)
    _git(repo, "commit", "-q", "-m", f"add {name!r}")
    return before, _git(repo, "rev-parse", "HEAD")


def _run(repo: Path, **env: str) -> subprocess.CompletedProcess[str]:
    full = {
        **os.environ,
        "EVENT": "push",
        "PUSH_BEFORE": "",
        "PR_BASE": "",
        "PR_HEAD": "",
        "GITHUB_SHA": "",
        **env,
    }
    return subprocess.run(
        ["bash", "-c", _step_script()],
        cwd=repo,
        capture_output=True,
        text=True,
        env=full,
        timeout=60,
    )


def _push(repo: Path, before: str, after: str) -> subprocess.CompletedProcess[str]:
    return _run(repo, EVENT="push", PUSH_BEFORE=before, GITHUB_SHA=after)


def test_the_name_really_is_quoted_by_a_line_listing(repo: Path) -> None:
    """Non-triviality: the fixture must reproduce the condition that hid the file.

    If this git printed the name raw, the tests below would pass whether or not
    the job used `-z`, and would prove nothing about item 1.1.
    """
    before, after = _add_and_commit(repo, NON_ASCII_AUDIO)
    listed = _git(repo, "diff", "--name-only", before, after)
    assert listed.startswith('"') and "\\303\\266" in listed, listed


def test_a_non_ascii_audio_name_in_a_push_range_fails(repo: Path) -> None:
    """THE regression test for item 1.1: the quoted name must not slip past."""
    before, after = _add_and_commit(repo, NON_ASCII_AUDIO)
    result = _push(repo, before, after)
    assert result.returncode == 1, (
        f"media-guard passed {NON_ASCII_AUDIO!r}. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert NON_ASCII_AUDIO in result.stderr, (
        "the refusal did not name the file as it is spelled, so the operator "
        f"cannot find it: {result.stderr!r}"
    )


def test_a_non_ascii_audio_name_on_a_pull_request_fails(repo: Path) -> None:
    before, after = _add_and_commit(repo, "Motörhead – Ace.FLAC")
    result = _run(repo, EVENT="pull_request", PR_BASE=before, PR_HEAD=after)
    assert result.returncode == 1, result.stdout + result.stderr


def test_a_non_ascii_audio_name_in_a_whole_tree_scan_fails(repo: Path) -> None:
    """The `git ls-files` branch (a manual run, or a new ref) quotes names too."""
    _add_and_commit(repo, NON_ASCII_AUDIO)
    result = _run(repo, EVENT="workflow_dispatch")
    assert result.returncode == 1, result.stdout + result.stderr
    assert NON_ASCII_AUDIO in result.stderr


def test_a_name_with_a_newline_in_it_fails(repo: Path) -> None:
    """A line-based listing splits this name in two; a NUL-based one cannot."""
    before, after = _add_and_commit(repo, "liner notes\ntrack01.wav")
    result = _push(repo, before, after)
    assert result.returncode == 1, result.stdout + result.stderr


def test_an_ordinary_text_change_passes(repo: Path) -> None:
    """The floor: a job that refused everything would pass every test above."""
    before, after = _add_and_commit(repo, "Björk notes.md")
    result = _push(repo, before, after)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No audio/media files" in result.stdout
    assert "names examined: 1" in result.stdout, result.stdout


def test_a_missing_extension_list_refuses(repo: Path) -> None:
    before, after = _add_and_commit(repo, "notes.md")
    (repo / ".githooks" / "audio-extensions.txt").unlink()
    result = _push(repo, before, after)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "missing or empty" in result.stdout


def test_an_empty_extension_list_refuses(repo: Path) -> None:
    before, after = _add_and_commit(repo, "notes.md")
    (repo / ".githooks" / "audio-extensions.txt").write_text("", encoding="utf-8")
    result = _push(repo, before, after)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "missing or empty" in result.stdout


def test_a_malformed_extension_list_refuses(repo: Path) -> None:
    """A dotted or uppercase entry would build a pattern that matches nothing."""
    before, after = _add_and_commit(repo, "notes.md")
    (repo / ".githooks" / "audio-extensions.txt").write_text(
        ".flac\nwav\n", encoding="utf-8"
    )
    result = _push(repo, before, after)
    assert result.returncode == 1, result.stdout + result.stderr


def test_a_failing_git_diff_refuses(repo: Path) -> None:
    """The 2026-08-20 fail-open: a vanished base must refuse, not pass clean."""
    _, after = _add_and_commit(repo, "notes.md")
    result = _push(repo, "deadbeef" * 5, after)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "could not enumerate" in result.stdout, result.stdout


def test_the_extension_list_has_the_shape_the_job_requires() -> None:
    """One lowercase extension per line, a trailing newline, and nothing else.

    The pre-commit hook reads the same file, so its shape is a contract between
    two readers, and `flac` (the archival master) must be in it.
    """
    text = EXTENSIONS.read_text(encoding="utf-8")
    assert text.endswith("\n") and not text.endswith("\n\n"), repr(text[-20:])
    entries = text.splitlines()
    assert len(entries) >= 10, entries
    assert all(e.isascii() and e.isalnum() and e == e.lower() for e in entries), entries
    assert len(set(entries)) == len(entries), entries
    assert "flac" in entries and "wav" in entries and "mp3" in entries
