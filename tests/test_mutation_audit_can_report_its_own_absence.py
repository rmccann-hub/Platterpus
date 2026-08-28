"""The mutation audit must be able to say when it did not happen.

**Why this file exists.** The weekly mutation job ran seven times between
2026-07-13 and 2026-08-24. Every one reported ``success``. Every one finished in
**under 90 seconds** — for a job whose test suite takes four minutes to run
*once*. Not one of them mutated anything.

The command line was ``mutmut run --paths-to-mutate "..."``, which is mutmut 2.x
syntax. mutmut 3.0 removed the flag; ``mutmut`` was installed **unpinned**; so an
upstream major release retired this project's test-efficacy audit, and the two
``|| true`` suffixes meant a hard ``exit 2`` and a completed audit produced the
same green tick.

Three separate rules of this repo were in play and none of them fired, because
each was written about something slightly different:

* ``CLAUDE.md`` Critical rule #11 — *a tool that gates CI must not float* — was
  read as being about **gating** tools. This one gates nothing, so it floated.
  A floating tool can silently retire a *signal* too, and a signal nobody can
  tell is off is worse than no signal: its silence reads as good news.
* ``docs/testing.md`` §5.au — *a passing check and an absent check have the same
  signature* — is the exact defect, written down, in a file this job exists to
  serve.
* ``scripts/check.py`` already refuses to call a timed-out gate a pass. The same
  reasoning had simply never been applied to a workflow.

**So the fix could not be "correct the flag".** A corrected flag rots the same
way the next time mutmut changes. What this file enforces is the property that
was missing: the job must be **structurally incapable of reporting success while
measuring nothing**.

The floor counts mutants that reached a *verdict*. That distinction is the whole
point and it is not pedantry — mutmut today generates 348 mutants for
``verdict.py``, runs **none** of them, and exits 0. A floor on mutants
*generated* would pass on that run. ``CLAUDE.md``: *can this check be satisfied
by finding nothing?* — asked of the check that was written to answer it.
"""

from __future__ import annotations

import glob
import re
import tomllib
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
WORKFLOW: Final[Path] = REPO_ROOT / ".github" / "workflows" / "mutation.yml"
PYPROJECT: Final[Path] = REPO_ROOT / "pyproject.toml"


def _mutmut_config() -> dict[str, object]:
    with PYPROJECT.open("rb") as handle:
        return dict(tomllib.load(handle)["tool"]["mutmut"])


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# The config names real things
# --------------------------------------------------------------------------


def test_the_mutation_config_exists_at_all() -> None:
    """The floor for every test below. If ``[tool.mutmut]`` is gone, mutmut
    guesses its own source paths and mutates the entire package — and each
    assertion below would pass on an empty dict."""
    config = _mutmut_config()
    assert config, "[tool.mutmut] is missing from pyproject.toml"
    assert "only_mutate" in config, "[tool.mutmut] does not scope what it mutates"


def test_every_mutated_path_pattern_matches_a_real_file() -> None:
    """A glob that matches nothing mutates nothing, silently.

    This is not hypothetical: the first draft of the ``[tool.mutmut]`` block
    written on 2026-08-28 listed ``tests/test_ctdb_crc.py`` in its test
    selection — a file that has never existed in this repository. mutmut takes a
    selection at face value, so the audit would have run with a test file
    missing and said nothing about it.
    """
    patterns = _mutmut_config()["only_mutate"]
    assert isinstance(patterns, list) and patterns, "only_mutate is empty"
    empty = [p for p in patterns if not glob.glob(str(REPO_ROOT / str(p)))]
    assert not empty, (
        "these only_mutate patterns match no file, so they mutate nothing:\n  "
        + "\n  ".join(empty)
    )


def test_every_selected_test_file_exists() -> None:
    """The regression test for the defect described above."""
    selection = _mutmut_config().get("pytest_add_cli_args_test_selection", [])
    assert isinstance(selection, list) and selection, (
        "no test selection — mutmut would run the whole 4,686-test suite per "
        "mutant, which does not finish inside the job's 90-minute bound"
    )
    missing = [t for t in selection if not (REPO_ROOT / str(t)).is_file()]
    assert not missing, (
        "the mutation test selection names files that do not exist:\n  "
        + "\n  ".join(str(m) for m in missing)
    )


# --------------------------------------------------------------------------
# The workflow cannot lie
# --------------------------------------------------------------------------


def test_mutmut_is_pinned_so_its_cli_cannot_vanish_under_us() -> None:
    """An unpinned install is what let mutmut 3.0 retire this audit.

    The bound is asserted on the *install line*, not on a comment about it: a
    comment saying "pinned" is exactly the shape ``CLAUDE.md`` refuses.
    """
    text = _workflow_text()
    installs = [
        line for line in text.splitlines() if "pip install" in line and "mutmut" in line
    ]
    assert installs, "mutation.yml no longer installs mutmut"
    unbounded = [
        line
        for line in installs
        # A bound is any of `==`, `>=`, `<`, `~=` applied to mutmut itself.
        if not re.search(r"mutmut[^\"']*[<>=~]=?\s*\d", line)
    ]
    assert not unbounded, (
        "mutmut is installed without a version bound. An unpinned major bump "
        "removed `--paths-to-mutate` and silently disabled this audit for seven "
        "weekly runs:\n  " + "\n  ".join(line.strip() for line in unbounded)
    )


def test_the_mutmut_commands_are_not_wrapped_in_a_blanket_true() -> None:
    """`mutmut run || true` is what made a crash indistinguishable from a pass.

    Scoped deliberately to the *tool* invocations. ``grep ... || true`` is
    correct and stays — grep exits 1 on no-match, which is the normal case, and
    `.github/workflows/ci.yml` already documents that reasoning. The defect was
    never `|| true`; it was `|| true` on the command whose failure was the
    entire news.
    """
    offenders = [
        line.strip()
        for line in _workflow_text().splitlines()
        if re.search(r"^\s*mutmut\s+(run|results)\b.*\|\|\s*true", line)
    ]
    assert not offenders, (
        "a mutmut invocation swallows its own exit status:\n  " + "\n  ".join(offenders)
    )


def test_the_job_asserts_a_floor_on_mutants_that_reached_a_VERDICT() -> None:
    """The gate that makes the job unable to pass while measuring nothing.

    Two halves, and only the pair is a check:

    1. a floor exists and is a positive number;
    2. what it counts is **killed + survived**, not mutants generated.

    The second half is the one that matters. mutmut currently generates hundreds
    of mutants and checks none of them; a floor on the generated count would
    pass on precisely the broken run this file exists to catch.
    """
    text = _workflow_text()

    match = re.search(r"MIN_CHECKED:\s*\"?(\d+)\"?", text)
    assert match, "mutation.yml declares no MIN_CHECKED floor"
    assert int(match.group(1)) > 0, "the MIN_CHECKED floor is zero, so it is decoration"

    assert re.search(r"checked=\$\(\(\s*killed \+ survived\s*\)\)", text), (
        "the floor must count mutants that reached a verdict (killed + "
        "survived). Counting generated mutants passes on a run that executed "
        "none of them, which is the exact failure this gate is for."
    )
    assert re.search(r'\[\s*"\$checked"\s*-lt\s*"\$MIN_CHECKED"\s*\]', text), (
        "MIN_CHECKED is declared but never compared against the checked count"
    )
    assert "exit 1" in text, "the floor check never fails the job"


def test_the_run_status_is_captured_rather_than_discarded() -> None:
    """`| tee` makes the pipeline's status `tee`'s, so the real one must be read
    out of `PIPESTATUS` — the same trap `CLAUDE.md` records for
    `pytest ... | tail` reporting 0 on a failing run."""
    text = _workflow_text()
    assert "PIPESTATUS[0]" in text, (
        "mutmut's exit status is read from a pipeline without PIPESTATUS, so a "
        "failing run reports the status of `tee`"
    )


# --------------------------------------------------------------------------
# Non-triviality: every check above must be able to fire
# --------------------------------------------------------------------------


def test_the_pin_check_can_actually_fail() -> None:
    """Against constructed text, because a detector that cannot fire is
    decoration — and this one is a regex over prose that could easily match
    everything or nothing."""
    unpinned = 'python -m pip install -e ".[dev]" mutmut'
    pinned = 'python -m pip install -e ".[dev]" "mutmut>=3.7,<3.8"'
    pattern = re.compile(r"mutmut[^\"']*[<>=~]=?\s*\d")
    assert not pattern.search(unpinned), "the pin check would pass an unpinned install"
    assert pattern.search(pinned), "the pin check would fail a correctly pinned install"


def test_the_blanket_true_check_can_actually_fail() -> None:
    """Both directions: it must catch the real defect and must NOT catch the
    legitimate `grep ... || true`."""
    pattern = re.compile(r"^\s*mutmut\s+(run|results)\b.*\|\|\s*true")
    assert pattern.search("          mutmut run --max-children 4 || true"), (
        "the check would have passed the exact line that broke seven runs"
    )
    assert not pattern.search(
        "          killed=$(grep -c ': killed$' out.txt || true)"
    ), (
        "the check flags grep's expected no-match exit, which would make it a "
        "false-failure machine and get it deleted"
    )
