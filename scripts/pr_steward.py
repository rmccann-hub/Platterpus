#!/usr/bin/env python3
"""Say whether a commit's checks are green, and if not, exactly why not.

The mechanical half of the `pr-steward` skill (`.claude/skills/pr-steward/SKILL.md`),
which carries the judgement. A DRAFT, owned by this repository.

**Why this exists (2026-11-02).** That day `main` went red twice after a merge
and nobody saw it until much later: the CI run on #420's merge commit, where a
test had left a window on screen for a later test to read, and `appimage.yml`
on every merge from #420 to #422, where appimagetool's floating build refused
the AppDir. Both were found by chance. The waits written by hand in between got
three things wrong, each of which this script now decides by rule:

* a test job CANCELLED because a newer push superseded its run was read as a
  FAILURE, so a branch looked broken that was only busy;
* the number of checks to wait for was a constant copied into the loop, and it
  went stale the moment a job was added (`ui-conformance`) or removed;
* a check the ruleset REQUIRES but no workflow runs any more (`test (py3.11)`,
  after the 3.11 leg left the matrix) blocks a merge forever, and nothing said
  so. GitHub shows it as "expected", which reads like "still running".

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
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Final

DEFAULT_REPO: Final[str] = "rmccann-hub/Platterpus"
API: Final[str] = "https://api.github.com"

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
class CheckRun:
    """One check run, the fields the verdict needs."""

    name: str
    status: str  # queued, in_progress, completed
    conclusion: str  # "" until completed
    run_id: int  # GitHub's id; a later run of the same name has a larger one
    details_url: str = ""


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


# --- Reading the API -------------------------------------------------------


class ApiError(Exception):
    """The GitHub API could not be read; no verdict can be given."""


def _get(url: str) -> bytes:
    # Every URL is built here from `API`, an https:// constant; refuse anything
    # else rather than open a `file:` or other scheme by accident.
    if not url.startswith(API + "/"):
        raise ApiError(f"refusing a URL outside {API}: {url}")
    request = urllib.request.Request(  # noqa: S310 — https, checked above
        url, headers={"Accept": "application/vnd.github+json"}
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        # The scheme and host were checked above.
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body: bytes = response.read()
            return body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ApiError(f"{url}: {exc}") from exc


def _json(url: str) -> object:
    try:
        return json.loads(_get(url))
    except ValueError as exc:
        raise ApiError(f"{url}: not JSON: {exc}") from exc


def required_checks(repo: str, branch: str) -> list[str]:
    """The status checks the branch's rules require, read from the API."""
    rules = _json(f"{API}/repos/{repo}/rules/branches/{branch}")
    if not isinstance(rules, list):
        raise ApiError(
            f"rules for {branch}: expected a list, got {type(rules).__name__}"
        )
    names: list[str] = []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
            params = rule.get("parameters") or {}
            for check in params.get("required_status_checks") or []:
                if isinstance(check, dict) and isinstance(check.get("context"), str):
                    names.append(check["context"])
    return names


def check_runs(repo: str, sha: str) -> list[CheckRun]:
    """Every check run on the commit, across pages."""
    runs: list[CheckRun] = []
    page = 1
    while True:
        data = _json(
            f"{API}/repos/{repo}/commits/{sha}/check-runs?per_page=100&page={page}"
        )
        batch = data.get("check_runs") if isinstance(data, dict) else None
        if not isinstance(batch, list):
            raise ApiError(f"check runs for {sha}: no check_runs list")
        for item in batch:
            if isinstance(item, dict):
                runs.append(
                    CheckRun(
                        name=str(item.get("name", "")),
                        status=str(item.get("status", "")),
                        conclusion=str(item.get("conclusion") or ""),
                        run_id=int(item.get("id") or 0),
                        details_url=str(item.get("details_url") or ""),
                    )
                )
        if len(batch) < 100:
            return runs
        page += 1


def workflows_finished(repo: str, sha: str) -> bool:
    """True when every workflow run for the commit has completed (and one exists)."""
    data = _json(f"{API}/repos/{repo}/actions/runs?head_sha={sha}&per_page=100")
    runs = data.get("workflow_runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        raise ApiError(f"workflow runs for {sha}: no workflow_runs list")
    return bool(runs) and all(
        isinstance(run, dict) and run.get("status") == "completed" for run in runs
    )


def full_sha(repo: str, ref: str) -> str:
    """The full 40-character SHA of ``ref``.

    Needed because the workflow-runs filter (``?head_sha=``) matches only a full
    SHA: given a short one it returns an empty list, which read as "no workflow
    has finished", so a required check that will never report was called
    PENDING instead of BLOCKED (found running this on 2026-11-02).
    """
    data = _json(f"{API}/repos/{repo}/commits/{ref}")
    sha = data.get("sha") if isinstance(data, dict) else None
    if not isinstance(sha, str) or len(sha) != 40:
        raise ApiError(f"commit {ref}: no full sha in the answer")
    return sha


def pr_head(repo: str, number: int) -> tuple[str, str]:
    """A pull request's head commit and its base branch."""
    data = _json(f"{API}/repos/{repo}/pulls/{number}")
    if not isinstance(data, dict):
        raise ApiError(f"PR #{number}: not an object")
    head = data.get("head") or {}
    base = data.get("base") or {}
    return str(head.get("sha", "")), str(base.get("ref", "main"))


def job_log(repo: str, run: CheckRun) -> str:
    """The log of the job behind a check run (check run ids are job ids)."""
    return _get(f"{API}/repos/{repo}/actions/jobs/{run.run_id}/logs").decode(
        "utf-8", errors="replace"
    )


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
