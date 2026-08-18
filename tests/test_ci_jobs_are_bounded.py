"""Every CI job declares a wall-clock bound, in every workflow.

**Why this is a sweep and not four edits.** ``ci.yml``'s ``test`` job already
carried ``timeout-minutes: 15`` — on the *step* that runs pytest, with the reasoning
written correctly beside it: *"a cheap backstop: if a future regression hangs the
suite, the job fails in minutes instead of burning the 6-hour default."* The rule was
right. Its **subject** was one step, because that is the step whose author was
thinking about hangs.

The step that actually wedges is the one nobody expected to. On 2026-08-18 the
``apt-get`` that installs the headless Qt libraries stalled on a GitHub runner four
separate times across three runs of one branch, each with no bound at all — while
sibling matrix legs cleared the same step in 13 and 32 seconds. A stalled job is
indistinguishable from a slow one from the outside, so the first suspicion fell on
the change under review rather than on the runner.

Sweeping for the rule found three more jobs with no bound anywhere: ``appimage.yml``
``build``, ``publish-pypi.yml`` ``publish``, and — worst of the three —
``release.yml`` ``build-and-release``, where a wedge holds a runner for six hours
while a maintainer waits for a release that is never coming.

That is this session's recurring shape, and the reason the fix is a derived sweep:
**enforce a rule across the surface it belongs on, not at the place it was learned.**
Same lesson as ``tests/test_qthread_ownership.py`` (the ``QThread`` teardown rule was
enforced for one class out of nine) and ``tests/test_gating_tools_are_pinned.py`` (the
pin rule was written in the file that does not gate).

The expected set is derived from the filesystem — every ``*.yml`` under
``.github/workflows/`` — so a workflow added later is covered the day it lands rather
than the day someone remembers this file exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import pytest
import yaml

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
WORKFLOW_DIR: Final[Path] = REPO_ROOT / ".github" / "workflows"

#: Floors, so this file cannot pass by finding nothing. A sweep that examines an empty
#: set is decoration: it stays green through a renamed directory, a glob that stops
#: matching, or a parser that silently returns ``{}`` — and it reports success while
#: doing so. Both numbers are below today's counts on purpose; they assert the
#: population is real, not that it has a particular size.
MIN_WORKFLOWS: Final[int] = 4
MIN_JOBS: Final[int] = 8

#: The 6-hour GitHub default. A bound at or above it is not a bound — it is the
#: default restated, and it would satisfy a naive "is the key present" check while
#: changing nothing about how long a wedged job holds a runner.
GITHUB_DEFAULT_MINUTES: Final[int] = 360


def _workflows() -> list[Path]:
    """Every workflow file, derived from disk rather than listed here."""
    return sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))


def _jobs(path: Path) -> dict[str, Any]:
    """The ``jobs:`` mapping of one workflow.

    Parsed as YAML rather than grepped: ``timeout-minutes`` appears at both job and
    step level, and a text search cannot tell the two apart — which is precisely the
    distinction this file exists to hold. A step-level bound is what was already
    there when every job was unbounded.
    """
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path.name} did not parse as a YAML mapping"
    jobs = loaded.get("jobs")
    assert isinstance(jobs, dict) and jobs, f"{path.name} declares no jobs"
    return jobs


def _all_jobs() -> list[tuple[str, str, dict[str, Any]]]:
    """``(workflow filename, job id, job body)`` for every job in the repo."""
    return [
        (path.name, job_id, body)
        for path in _workflows()
        for job_id, body in _jobs(path).items()
        if isinstance(body, dict)
    ]


def test_the_sweep_has_something_to_sweep() -> None:
    """The floor. Without it every assertion below is vacuously satisfiable."""
    workflows = _workflows()
    assert len(workflows) >= MIN_WORKFLOWS, (
        f"only {len(workflows)} workflow files found under {WORKFLOW_DIR} — the "
        f"sweep below would pass by examining almost nothing. If workflows really "
        f"were removed, lower MIN_WORKFLOWS deliberately and say why."
    )
    jobs = _all_jobs()
    assert len(jobs) >= MIN_JOBS, (
        f"only {len(jobs)} jobs found across {len(workflows)} workflows — too few "
        f"for this sweep to mean anything. Did the YAML parse produce empty bodies?"
    )


@pytest.mark.parametrize(
    ("workflow", "job_id", "body"),
    [pytest.param(w, j, b, id=f"{w}:{j}") for w, j, b in _all_jobs()],
)
def test_every_job_declares_a_bound(
    workflow: str, job_id: str, body: dict[str, Any]
) -> None:
    """A job with no ``timeout-minutes`` inherits GitHub's 6-hour default.

    Six hours is not a backstop. It is long enough that a wedged job looks like a
    queue delay, gets waited on, and is eventually cancelled by a human — which is
    how the 2026-08-18 stall consumed two runs before anyone read the step list.
    """
    bound = body.get("timeout-minutes")
    assert bound is not None, (
        f"job `{job_id}` in {workflow} declares no `timeout-minutes`, so it inherits "
        f"GitHub's {GITHUB_DEFAULT_MINUTES}-minute default. Add a job-level bound "
        f"sized to what the job actually does. A step-level bound does not count: "
        f"it only covers the step someone expected to hang."
    )


@pytest.mark.parametrize(
    ("workflow", "job_id", "body"),
    [pytest.param(w, j, b, id=f"{w}:{j}") for w, j, b in _all_jobs()],
)
def test_every_bound_is_actually_a_bound(
    workflow: str, job_id: str, body: dict[str, Any]
) -> None:
    """Present is not the same as meaningful — the wrong-thing question, asked here.

    ``timeout-minutes: 360`` would satisfy the test above while leaving behaviour
    exactly as it was. So the value is checked, not merely its presence: a positive
    integer, strictly under the default it exists to replace.
    """
    bound = body.get("timeout-minutes")
    if bound is None:
        pytest.skip("absence is the previous test's failure, not this one's")
    assert isinstance(bound, int) and not isinstance(bound, bool), (
        f"job `{job_id}` in {workflow} has a non-integer `timeout-minutes` "
        f"({bound!r}). GitHub accepts an expression here, but a computed bound is "
        f"one this sweep cannot check — keep it a literal."
    )
    assert 0 < bound < GITHUB_DEFAULT_MINUTES, (
        f"job `{job_id}` in {workflow} sets `timeout-minutes: {bound}`, which is not "
        f"a bound: {GITHUB_DEFAULT_MINUTES} minutes is GitHub's own default, so this "
        f"restates it rather than tightening it."
    )
