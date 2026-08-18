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

**No YAML library, deliberately.** The first version imported ``PyYAML``, which is
installed in some environments incidentally and is *not* in this project's ``dev``
extra — so it passed locally and broke all four matrix legs at once with
``ModuleNotFoundError``. Adding a dependency is a step this project asks you to stop
and check first (``CLAUDE.md`` → *Deviation policy*), and it is not needed: the only
question here is whether ``timeout-minutes`` appears at **job** level or **step**
level, and in YAML that is a question about indentation. :func:`_job_bounds` answers
exactly that and nothing else — see its docstring for why this is not the "grep cannot
tell them apart" failure the paragraph above warns about.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
WORKFLOW_DIR: Final[Path] = REPO_ROOT / ".github" / "workflows"

#: Floors, so this file cannot pass by finding nothing. A sweep that examines an empty
#: set is decoration: it stays green through a renamed directory, a glob that stops
#: matching, or a reader that silently returns ``{}`` — and it reports success while
#: doing so. Both numbers are below today's counts on purpose; they assert the
#: population is real, not that it has a particular size.
MIN_WORKFLOWS: Final[int] = 4
MIN_JOBS: Final[int] = 8

#: The 6-hour GitHub default. A bound at or above it is not a bound — it is the
#: default restated, and it would satisfy a naive "is the key present" check while
#: changing nothing about how long a wedged job holds a runner.
GITHUB_DEFAULT_MINUTES: Final[int] = 360

#: ``jobs:`` at column 0 — where the mapping this file cares about begins.
_JOBS_KEY: Final[re.Pattern[str]] = re.compile(r"^jobs:\s*(?:#.*)?$")
#: A job id: exactly two spaces of indent, then ``name:`` and nothing else.
_JOB_ID: Final[re.Pattern[str]] = re.compile(r"^ {2}(?P<id>[A-Za-z0-9_.-]{1,80}):\s*$")
#: A job-level property: exactly four spaces. A step's properties sit at eight (six
#: for the ``- `` item marker plus two), so this cannot match one.
_JOB_TIMEOUT: Final[re.Pattern[str]] = re.compile(
    r"^ {4}timeout-minutes:\s*(?P<value>\S+)"
)
#: Any line at column 0 that is not blank and not a comment — the end of ``jobs:``.
_TOP_LEVEL: Final[re.Pattern[str]] = re.compile(r"^[^\s#]")


def _job_bounds(text: str) -> dict[str, int | None]:
    """Map each job id to its **job-level** ``timeout-minutes``, or ``None``.

    **Indentation-aware, which is the whole point.** The docstring of this module
    says a text search cannot tell a job-level bound from a step-level one, and that
    is true of a search for the *word*. It is not true of a search anchored to
    depth: GitHub's schema fixes the layout, so ``jobs:`` sits at column 0, a job id
    at 2, a job's own properties at 4, and a step's properties at 8 (the ``- ``
    marker takes 6). Matching ``timeout-minutes`` at *exactly* four spaces therefore
    selects job-level bounds and cannot select a step's — which is the one
    discrimination this file needs.

    A ``None`` value means the job was found and declares no bound; a job missing
    from the mapping entirely means the reader did not see it at all, which the
    floors below turn into a failure rather than a pass.

    Values are returned as text-derived ``int`` where they parse and ``None`` where
    they do not, so a computed or quoted bound reads as "no literal bound" and gets
    reported rather than silently accepted.
    """
    bounds: dict[str, int | None] = {}
    in_jobs = False
    current: str | None = None
    for line in text.splitlines():
        if not in_jobs:
            in_jobs = bool(_JOBS_KEY.match(line))
            continue
        # A new top-level key ends the jobs mapping.
        if _TOP_LEVEL.match(line):
            break
        job = _JOB_ID.match(line)
        if job is not None:
            current = job.group("id")
            bounds.setdefault(current, None)
            continue
        if current is None:
            continue
        found = _JOB_TIMEOUT.match(line)
        if found is not None:
            raw = found.group("value")
            bounds[current] = int(raw) if raw.isdigit() else None
    return bounds


def _workflows() -> list[Path]:
    """Every workflow file, derived from disk rather than listed here."""
    return sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))


def _all_jobs() -> list[tuple[str, str, int | None]]:
    """``(workflow filename, job id, job-level bound)`` for every job in the repo."""
    return [
        (path.name, job_id, bound)
        for path in _workflows()
        for job_id, bound in _job_bounds(path.read_text(encoding="utf-8")).items()
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
        f"for this sweep to mean anything. Did the reader stop matching job ids?"
    )
    # Every workflow must contribute at least one job, or a file whose layout the
    # reader cannot follow would drop out of the population instead of failing —
    # the same "silently left the check's set" hole CLAUDE.md rule #7 describes.
    empty = [p.name for p in _workflows() if not _job_bounds(p.read_text("utf-8"))]
    assert not empty, (
        f"the reader found no jobs at all in {', '.join(empty)} — its indentation "
        f"assumptions no longer hold for that file, so those jobs are unchecked"
    )


@pytest.mark.parametrize(
    ("workflow", "job_id", "bound"),
    [pytest.param(w, j, b, id=f"{w}:{j}") for w, j, b in _all_jobs()],
)
def test_every_job_declares_a_bound(
    workflow: str, job_id: str, bound: int | None
) -> None:
    """A job with no ``timeout-minutes`` inherits GitHub's 6-hour default.

    Six hours is not a backstop. It is long enough that a wedged job looks like a
    queue delay, gets waited on, and is eventually cancelled by a human — which is
    how the 2026-08-18 stall consumed two runs before anyone read the step list.
    """
    assert bound is not None, (
        f"job `{job_id}` in {workflow} declares no literal job-level "
        f"`timeout-minutes`, so it inherits GitHub's {GITHUB_DEFAULT_MINUTES}-minute "
        f"default. Add one sized to what the job actually does. A step-level bound "
        f"does not count: it only covers the step someone expected to hang."
    )


@pytest.mark.parametrize(
    ("workflow", "job_id", "bound"),
    [pytest.param(w, j, b, id=f"{w}:{j}") for w, j, b in _all_jobs()],
)
def test_every_bound_is_actually_a_bound(
    workflow: str, job_id: str, bound: int | None
) -> None:
    """Present is not the same as meaningful — the wrong-thing question, asked here.

    ``timeout-minutes: 360`` would satisfy the test above while leaving behaviour
    exactly as it was. So the value is checked, not merely its presence.
    """
    if bound is None:
        pytest.skip("absence is the previous test's failure, not this one's")
    assert 0 < bound < GITHUB_DEFAULT_MINUTES, (
        f"job `{job_id}` in {workflow} sets `timeout-minutes: {bound}`, which is not "
        f"a bound: {GITHUB_DEFAULT_MINUTES} minutes is GitHub's own default, so this "
        f"restates it rather than tightening it."
    )


def test_the_reader_tells_a_job_bound_from_a_step_bound() -> None:
    """The one property the whole file rests on, pinned against constructed text.

    This is the assertion that makes :func:`_job_bounds` trustworthy without a YAML
    library. ``bounded`` has its bound at job level; ``only_a_step`` has the *same
    key with the same value* at step level and must read as unbounded. A search for
    the word alone would call both bounded — which is exactly the confusion that let
    every job in this repo go unbounded while a `timeout-minutes` sat in the file.
    """
    sample = (
        "name: Example\n"
        "on:\n"
        "  push:\n"
        "jobs:\n"
        "  bounded:\n"
        "    runs-on: ubuntu-22.04\n"
        "    timeout-minutes: 15\n"
        "    steps:\n"
        "      - name: something\n"
        "        run: true\n"
        "  only_a_step:\n"
        "    runs-on: ubuntu-22.04\n"
        "    steps:\n"
        "      - name: slow thing\n"
        "        timeout-minutes: 15\n"
        "        run: true\n"
        "  computed:\n"
        "    runs-on: ubuntu-22.04\n"
        "    timeout-minutes: ${{ inputs.limit }}\n"
    )
    assert _job_bounds(sample) == {
        "bounded": 15,
        "only_a_step": None,
        "computed": None,
    }


def test_the_reader_stops_at_the_end_of_the_jobs_mapping() -> None:
    """A key after ``jobs:`` must not be swallowed as a job.

    Without the top-level guard a trailing block would contribute phantom entries,
    and a phantom job with no bound would fail the sweep for a reason that does not
    exist — a false alarm being just as corrosive as a miss.
    """
    sample = (
        "jobs:\n"
        "  real:\n"
        "    timeout-minutes: 5\n"
        "concurrency:\n"
        "  group: ci\n"
        "  cancel-in-progress: true\n"
    )
    assert _job_bounds(sample) == {"real": 5}


def test_the_sweep_would_fail_on_an_unbounded_job() -> None:
    """Revert-proof at the unit level, so the detector is known to be able to fail.

    The parametrized tests above prove the *current* tree is clean, which is exactly
    what a vacuous detector also reports. This constructs the defect instead.
    """
    unbounded = _job_bounds("jobs:\n  build:\n    runs-on: ubuntu-22.04\n")
    assert unbounded == {"build": None}
    with pytest.raises(AssertionError, match="declares no literal job-level"):
        test_every_job_declares_a_bound("fake.yml", "build", unbounded["build"])
    with pytest.raises(AssertionError, match="is not a bound"):
        test_every_bound_is_actually_a_bound("fake.yml", "build", 360)
