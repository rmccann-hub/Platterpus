"""Read what `scripts/pr_steward.py` judges from the GitHub API.

The reading half of the `pr-steward` skill (`.claude/skills/pr-steward/SKILL.md`),
split from the judging half in `pr_steward.py` because they are two jobs: what
the API says, and what it means. Everything here is read; nothing is written,
merged or re-run. A DRAFT, owned by this repository.

Only ``https://api.github.com`` is ever opened, and an answer that cannot be read
raises :class:`ApiError`, so the caller gives no verdict rather than a wrong one.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Final

API: Final[str] = "https://api.github.com"


@dataclass(frozen=True)
class CheckRun:
    """One check run, the fields the verdict needs."""

    name: str
    status: str  # queued, in_progress, completed
    conclusion: str  # "" until completed
    run_id: int  # GitHub's id; a later run of the same name has a larger one
    details_url: str = ""


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
