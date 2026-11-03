#!/usr/bin/env python3
"""Say whether a commit's checks are green, and if not, exactly why not.

The mechanical half of the `steward` skill (`.claude/skills/steward/SKILL.md`),
which carries the judgement. A DRAFT, owned by this repository.

**Why this exists (2026-11-02).** `main` went red twice after a merge with
nobody watching, and the waits written by hand read a CANCELLED run (a newer
push superseding it) as a failure, waited for a check count that went stale, and
never said that a REQUIRED check no workflow runs any more (`test (py3.11)`)
blocks a merge for good. The skill tells the whole story; this decides by rule.

**What it reads, all from the GitHub API, never from prose:** the checks the
branch's ruleset requires (`rules/branches/<branch>`), every check run on the
commit, and every workflow run for it. The verdict:

* ``GREEN``     every required check passed and nothing else on the commit failed;
* ``FAILED``    a check failed, or timed out (required or not: a red
                ``appimage.yml`` on ``main`` is a red ``main``);
* ``CANCELLED`` the newest run of a required check was cancelled, which is
                usually a newer push superseding it: follow the newest commit;
* ``BLOCKED``   a required check has not reported and every workflow run for the
                commit has finished, so it never will: the ruleset names a job
                that does not run, which only the owner can change;
* ``PENDING``   anything still running or queued, and nothing above.

The worst state wins, in that order: FAILED before BLOCKED before CANCELLED
before PENDING. A failure is never hidden behind something still running.

``--logs`` fetches each failed job's log and prints every line that names a
failure (each ``FAILED``/``ERROR`` test, pytest's summary, ``##[error]``),
never only the last one: reading a run through ``tail -1`` hid two failing tests
on 2026-11-02.

Exit status is the verdict's: 0 GREEN, 1 FAILED, 2 PENDING, 3 BLOCKED,
4 CANCELLED, and 5 when the API could not be read (nothing was checked, so no
verdict is given; an unreadable answer is never reported as green).

Usage::

    python3 scripts/pr_steward.py --sha <commit>            # any commit
    python3 scripts/pr_steward.py --pr 425                  # a PR's head commit
    python3 scripts/pr_steward.py --sha <merge sha> --logs  # main after a merge
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Final

# The reading half, beside this file (`scripts/` is on the path when this runs
# as a script, as `emit_bom.py`'s `bommap` is).
from pr_steward_github import (
    ApiError,
    CheckRun,
    check_runs,
    full_sha,
    job_log,
    pr_head,
    required_checks,
    workflows_finished,
)

DEFAULT_REPO: Final[str] = "rmccann-hub/Platterpus"

GREEN: Final[str] = "GREEN"
FAILED: Final[str] = "FAILED"
PENDING: Final[str] = "PENDING"
BLOCKED: Final[str] = "BLOCKED"
CANCELLED: Final[str] = "CANCELLED"

#: The verdicts, worst first: the first one that applies is the answer.
SEVERITY: Final[tuple[str, ...]] = (FAILED, BLOCKED, CANCELLED, PENDING, GREEN)

EXIT_CODES: Final[dict[str, int]] = {
    GREEN: 0,
    FAILED: 1,
    PENDING: 2,
    BLOCKED: 3,
    CANCELLED: 4,
}
#: The API could not be read; no verdict.
EXIT_UNREAD: Final[int] = 5

#: A completed check with one of these passed. `skipped` and `neutral` are
#: GitHub's own "did not need to run" and "reported, no opinion".
_PASSING: Final[frozenset[str]] = frozenset({"success", "skipped", "neutral"})
#: A completed check with one of these failed.
_FAILING: Final[frozenset[str]] = frozenset(
    {"failure", "timed_out", "action_required", "startup_failure", "stale"}
)


@dataclass(frozen=True)
class Report:
    """The verdict, and every reason for it."""

    verdict: str
    failed: tuple[CheckRun, ...] = ()
    cancelled: tuple[CheckRun, ...] = ()
    pending: tuple[str, ...] = ()
    never_reported: tuple[str, ...] = ()
    passed: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default=())


def newest_by_name(runs: list[CheckRun]) -> dict[str, CheckRun]:
    """The newest run of each check name: a re-run supersedes the run before it."""
    newest: dict[str, CheckRun] = {}
    for run in runs:
        held = newest.get(run.name)
        if held is None or run.run_id > held.run_id:
            newest[run.name] = run
    return newest


def classify(
    required: list[str],
    check_runs: list[CheckRun],
    workflows_finished: bool,
) -> Report:
    """The verdict for one commit. Pure: everything it reads is an argument.

    ``workflows_finished`` is True when every workflow run for the commit has
    completed; with a required check still unreported, that is what tells a
    check that is coming from one that never will.
    """
    newest = newest_by_name(check_runs)
    failed: list[CheckRun] = []
    cancelled: list[CheckRun] = []
    pending: list[str] = []
    never: list[str] = []
    passed: list[str] = []
    notes: list[str] = []

    for name in sorted(set(required)):
        run = newest.get(name)
        if run is None:
            (never if workflows_finished else pending).append(name)
        elif run.status != "completed":
            pending.append(name)
        elif run.conclusion in _PASSING:
            passed.append(name)
        elif run.conclusion == "cancelled":
            cancelled.append(run)
        else:
            failed.append(run)

    # A check nobody requires still counts when it FAILS: a red appimage.yml on
    # main is a red main. Its passing, pending or cancelled runs decide nothing.
    for name, run in sorted(newest.items()):
        if name in required:
            continue
        if run.status == "completed" and run.conclusion in _FAILING:
            failed.append(run)
        elif run.status == "completed" and run.conclusion not in _PASSING | {
            "cancelled"
        }:
            notes.append(f"{name}: unrecognised conclusion {run.conclusion!r}")

    if not required:
        notes.append("the branch's ruleset requires no checks; only failures count")

    states = {
        FAILED: bool(failed),
        BLOCKED: bool(never),
        CANCELLED: bool(cancelled),
        PENDING: bool(pending),
    }
    verdict = next((state for state in SEVERITY if states.get(state)), GREEN)
    return Report(
        verdict=verdict,
        failed=tuple(failed),
        cancelled=tuple(cancelled),
        pending=tuple(pending),
        never_reported=tuple(never),
        passed=tuple(passed),
        notes=tuple(notes),
    )


def failure_lines(log: str) -> list[str]:
    """Every line of a job log that names a failure, in order. Never raises.

    GitHub prefixes each line with a timestamp, which is dropped. Kept: a
    pytest ``FAILED``/``ERROR`` line, pytest's final summary (``N failed`` /
    ``N passed``), an ``E   AssertionError`` line, and a ``##[error]`` line.
    """
    kept: list[str] = []
    for raw in log.splitlines():
        line = raw
        # "2026-11-02T20:43:14.9378129Z FAILED tests/x.py::t" -> drop the stamp.
        head, sep, rest = raw.partition(" ")
        if sep and head.endswith("Z") and head[:4].isdigit():
            line = rest
        text = line.strip()
        summary = (
            text[:1].isdigit()
            and (" passed" in text or " failed" in text)
            and " in " in text
        )
        if summary or text.startswith(("FAILED ", "ERROR ", "##[error]", "E   ")):
            kept.append(text)
    return kept


# --- The command -----------------------------------------------------------


def render(report: Report, sha: str) -> str:
    """The report as text for a person."""
    lines = [f"{report.verdict}  {sha[:12]}"]
    for run in report.failed:
        lines.append(f"  failed     {run.name} ({run.conclusion})  {run.details_url}")
    for run in report.cancelled:
        lines.append(f"  cancelled  {run.name}  (follow the newest commit's run)")
    for name in report.never_reported:
        lines.append(
            f"  blocked    {name}: required, and no workflow left to report it; "
            "only the owner can change the ruleset"
        )
    for name in report.pending:
        lines.append(f"  pending    {name}")
    lines.append(f"  passed     {len(report.passed)} required check(s)")
    lines.extend(f"  note       {note}" for note in report.notes)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else ""
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sha", help="the commit to judge")
    target.add_argument("--pr", type=int, help="judge this pull request's head commit")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--branch",
        default="",
        help="whose ruleset applies (default: main, or the PR's base)",
    )
    parser.add_argument(
        "--logs", action="store_true", help="print each failed job's failure lines"
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    try:
        if args.pr is not None:
            sha, base = pr_head(args.repo, args.pr)
        else:
            sha, base = full_sha(args.repo, args.sha), "main"
        branch = args.branch or base
        report = classify(
            required_checks(args.repo, branch),
            check_runs(args.repo, sha),
            workflows_finished(args.repo, sha),
        )
    except ApiError as exc:
        print(
            f"pr_steward: could not read GitHub, so no verdict: {exc}", file=sys.stderr
        )
        return EXIT_UNREAD

    if args.json:
        print(
            json.dumps(
                {
                    "verdict": report.verdict,
                    "sha": sha,
                    "failed": [r.name for r in report.failed],
                    "cancelled": [r.name for r in report.cancelled],
                    "never_reported": list(report.never_reported),
                    "pending": list(report.pending),
                    "passed": list(report.passed),
                    "notes": list(report.notes),
                },
                indent=2,
            )
        )
    else:
        print(render(report, sha))

    if args.logs:
        for run in report.failed:
            try:
                lines = failure_lines(job_log(args.repo, run))
            except ApiError as exc:
                print(f"--- {run.name}: log unreadable: {exc}")
                continue
            print(f"--- {run.name}: {len(lines)} failure line(s)")
            print("\n".join(lines) if lines else "  (none matched; read the whole log)")
    return EXIT_CODES[report.verdict]


if __name__ == "__main__":
    sys.exit(main())
