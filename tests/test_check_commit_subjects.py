"""`scripts/check_commit_subjects.py`: the commit-subject grammar check.

The 2026-10-27 external review, item 2.9: `CLAUDE.md` records a lowercase
conventional `type(scope): summary` grammar and nothing checked it. A check
written from a generic template would refuse this repository's own form (the
review notes that claude-code-skills' example workflow refuses `type(scope):`),
so the accepting half is held here as firmly as the refusing half, and against
the repository's real history, not only against made-up subjects.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest
from hypothesis import given
from hypothesis import strategies as st

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def _load():  # a module object
    """Import the script by path (scripts/ is deliberately not a package)."""
    path = REPO_ROOT / "scripts" / "check_commit_subjects.py"
    spec = importlib.util.spec_from_file_location("_check_commit_subjects", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


subjects = _load()


@pytest.mark.parametrize(
    "subject",
    [
        # This repository's own form, with and without a scope.
        "fix(ci): match media-guard names NUL-separated so a non-ASCII name cannot pass",
        "feat(rip-worker): read the securing pass's limit line",
        "docs(handshake): file the fork's round 36 lap 12 and hold our lap 13",
        "docs(docs,ui): a scope joined with a comma, as one history entry has",
        "test: pin the argv surface",
        "release: 0.7.113",
        "refactor(ui)!: a breaking change marked with a bang",
        # An acronym or identifier first is not sentence case.
        "docs: README names the new minor",
        "fix(handshake): FORK_PIN moves only on a close",
        "fix(ui): PySide6 6.11.2 removed two menu shortcuts",
        # ci and build: in the history, and Dependabot's prefix.
        "ci(evidence): fetch only what each job reads; gitleaks fetches evidence",
        "build(deps): bump actions/checkout from 7.0.0 to 7.0.1 (#90)",
        "build(deps-dev): update mypy requirement from <2,>=1.13 to >=1.13,<3 (#70)",
        # Subjects git and Dependabot write on an ordinary commit.
        'Revert "fix(ci): match media-guard names NUL-separated"',
        "Bump actions/checkout from 7.0.0 to 7.0.1",
        "Bump the pip group across 1 directory with 2 updates",
    ],
)
def test_the_repository_grammar_is_accepted(subject: str) -> None:
    assert subjects.check_subject(subject) is None, subjects.check_subject(subject)


@pytest.mark.parametrize(
    "subject",
    [
        "Merge pull request #392 from rmccann-hub/claude/session-omka9f",
        "Merge branch 'main' into claude/session-omka9f",
        "Merge remote-tracking branch 'origin/main' into claude/x",
        "Merge commit '46314e2e' into claude/session-omka9f",
        "Merge claude/session-omka9f into paired-track3",
        # An author's `git merge -m` prose, as the history holds.
        "Merge the taken-over EAC audit branch (Part E, P3 and P5 to P8)",
        # A merge commit may carry a conventional subject too.
        "docs(eac-parity): merge main into the EAC audit branch",
    ],
)
def test_a_merge_commit_takes_a_merge_subject(subject: str) -> None:
    assert subjects.check_subject(subject, is_merge=True) is None


def test_a_merge_subject_on_an_ordinary_commit_is_refused() -> None:
    """Only a commit with two parents may say `Merge …` instead of `type: …`."""
    subject = "Merge pull request #392 from rmccann-hub/claude/session-omka9f"
    assert subjects.check_subject(subject, is_merge=False) is not None


@pytest.mark.parametrize(
    ("subject", "why"),
    [
        ("Fix the media guard", "not `type"),
        ("fix: Add a media guard", "capitalised"),
        ("feat(guide): Help → Getting started", "capitalised"),
        ("fix(ci): match names with -z.", "period"),
        ("fixed(ci): match names", "is not one of"),
        ("perf: faster parse", "is not one of"),
        ("Feat(ci): match names", "not `type"),
        ("fix(CI): match names", "not `type"),
        ("fix(ci):match names", "not `type"),
        ("fix(ci):  ", "not `type"),
        ("", "not `type"),
        ("Round 31 closes: lap 5 released (#309)", "not `type"),
        ("Merge stuff", "not `type"),
    ],
)
def test_a_subject_off_the_grammar_is_refused_with_its_reason(
    subject: str, why: str
) -> None:
    reason = subjects.check_subject(subject)
    assert reason is not None, f"{subject!r} was accepted"
    assert why in reason, reason


@given(st.text(max_size=200), st.booleans())
def test_check_subject_never_raises(text: str, is_merge: bool) -> None:
    result = subjects.check_subject(text, is_merge=is_merge)
    assert result is None or isinstance(result, str)


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(  # fixed argv, no shell
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


#: The two subjects in the 400 up to 27755380 that are off the grammar, both
#: written before any check existed: a squash-merge PR title (squash merging is
#: off since 2026-10-12) and one sentence-case summary.
_KNOWN_OFF_GRAMMAR: Final[frozenset[str]] = frozenset(
    {
        "Round 31 closes: lap 5 released, FORK_PIN to ca3f3ea (.21), every lap "
        "reader on one fence rule (#309)",
        "feat(guide): Help → Getting started, the README section and the "
        "walkthrough script",
    }
)


def test_the_check_accepts_the_history_it_was_written_for() -> None:
    """Measured against real subjects, so it cannot fail the repo's own practice.

    The 400 commits up to 27755380 (the audited commit), merges included and
    known as merges by their parents. The first draft of this check accepted
    only GitHub's and git's merge forms and this test refused 13 hand-written
    `git merge -m` subjects, which is why a merge commit now takes any `Merge …`.
    Skips when that commit is not in the clone (a shallow checkout).
    """
    log = _git("log", "--format=%P%x00%s", "-400", "27755380")
    if log is None:
        pytest.skip("27755380 is not in this clone (shallow?)")
    history = [line.split("\x00", 1) for line in log.splitlines()]
    # NON-TRIVIALITY: a log that came back nearly empty would pass the loop,
    # and a history with no merges would not exercise the merge rule.
    assert len(history) == 400, len(history)
    merges = sum(len(parents.split()) > 1 for parents, _ in history)
    assert merges >= 50, merges
    refused = [
        subject
        for parents, subject in history
        if subjects.check_subject(subject, is_merge=len(parents.split()) > 1)
        is not None
    ]
    assert set(refused) <= _KNOWN_OFF_GRAMMAR, refused


def test_main_reads_merges_off_the_range() -> None:
    """The range mode must know a merge by its parents, or `main` turns red.

    c01f085b..27755380 holds one ordinary commit and the merge of PR #392.
    """
    if _git("cat-file", "-e", "27755380^{commit}") is None:
        pytest.skip("27755380 is not in this clone (shallow?)")
    assert subjects.main(["--range", "c01f085b..27755380"]) == 0


def test_main_refuses_a_range_that_cannot_be_listed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert subjects.main(["--range", "no-such-ref..also-not-a-ref"]) == 1
    assert "could not be listed" in capsys.readouterr().out


def test_main_refuses_an_empty_range(tmp_path: Path) -> None:
    """A range with no commits read nothing, and a check that read nothing fails."""
    head = _git("rev-parse", "HEAD")
    if head is None:
        pytest.skip("not a git checkout")
    assert subjects.main(["--range", f"{head.strip()}..{head.strip()}"]) == 1


def test_main_passes_and_fails_by_the_subjects(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert subjects.main(["--subject", "fix(ci): ok"]) == 0
    assert subjects.main(["--subject", "fix(ci): ok", "--subject", "Bad one"]) == 1
    out = capsys.readouterr().out
    assert "examined: 2; failing: 1" in out
