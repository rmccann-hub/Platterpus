"""The mutation audit must be able to say when it did not happen.

**The property, restated for the harness that replaced mutmut (2026-09-05).**
This file used to guard `mutmut`'s wiring: that it was pinned, that its commands
were not wrapped in `|| true`, that a floor counted mutants which reached a
verdict. Those assertions were right about the property and specific to a tool
that has since been removed — mutmut generates mutants and executes none in this
repo, including when a single mutant is named, and the recorded diagnosis
(import paths) was disproven by measurement.

**A guard test moves with the thing it guards.** Leaving the mutmut assertions
here would have left the file green against a workflow that no longer exists —
a check passing for the wrong reason, which this project holds to be worse than
one that fails. So the property is preserved and re-pointed at
`scripts/mutation_sweep.py`:

* the audit's exit status is not discarded;
* it carries a floor on mutants that actually reached a verdict, so a sweep that
  measured nothing cannot read as a clean one;
* and the floor can actually fail — asserted by construction rather than by
  reading the source, which is the stronger form.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
WORKFLOW: Final[Path] = REPO_ROOT / ".github" / "workflows" / "mutation.yml"
SWEEP: Final[Path] = REPO_ROOT / "scripts" / "mutation_sweep.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import mutation_sweep as ms  # noqa: E402


def test_the_audit_script_exists_and_the_workflow_calls_it() -> None:
    """The wiring, checked in both directions: a script nothing runs and a
    workflow calling a script that does not exist fail identically at 6am on a
    Monday, and neither says so."""
    assert SWEEP.is_file(), "scripts/mutation_sweep.py is gone"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/mutation_sweep.py" in text, (
        "the weekly workflow does not invoke the sweep — the audit is wired to nothing"
    )


#: `target:` / `tests:` rows of the sweep matrix. **No YAML library**, matching
#: `tests/test_ci_jobs_are_bounded.py`, which chose the same and says why: PyYAML
#: is not a declared dependency of this project and `tests/test_imports_are_declared.py`
#: correctly refuses an import that resolves only where somebody happens to have it.
#: Adding a dependency to read a config file is the wrong trade — and the deviation
#: policy would require asking first.
_MATRIX_ROW: Final[re.Pattern[str]] = re.compile(
    r"^\s{10,14}(?P<key>target|tests|floor):\s*(?P<value>\S.*?)\s*$"
)

#: A trailing `# comment` on a matrix scalar. YAML strips it; the regex above
#: does not, so a `floor: 3  # the whole population` would otherwise parse as
#: the string ``"3  # the whole population"`` and `int()` would raise inside the
#: test rather than reporting the leg. Stripped explicitly so the failure a
#: reader sees is about the floor, not about this parser.
_TRAILING_COMMENT: Final[re.Pattern[str]] = re.compile(r"\s+#.*$")


def _declared_limit() -> int:
    """The `--limit N` the workflow actually passes.

    Read rather than hardcoded: the reachable ceiling for every leg is
    ``min(limit, generated)``, so a `40` written into this file would let the
    workflow lower its limit and quietly make floors unreachable again — the
    check would still be green while measuring a number nobody uses.
    """
    match = re.search(r"--limit\s+(\d+)", WORKFLOW.read_text(encoding="utf-8"))
    assert match is not None, (
        "the sweep invocation no longer passes --limit; this test cannot compute "
        "the reachable ceiling without it"
    )
    return int(match.group(1))


def _matrix_legs() -> tuple[list[str], list[str], list[int]]:
    """Read the sweep matrix out of the workflow: targets, test rows, floors.

    Returned as three parallel lists rather than a list of triples because the
    tests below assert on their *lengths* against each other — a leg that
    declares a target and no floor is a real finding, and zipping would hide it
    by silently truncating to the shortest.
    """
    targets: list[str] = []
    tests: list[str] = []
    floors: list[int] = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        match = _MATRIX_ROW.match(line)
        if match is None:
            continue
        value = _TRAILING_COMMENT.sub("", match.group("value"))
        key = match.group("key")
        if key == "target":
            targets.append(value)
        elif key == "tests":
            tests.append(value)
        else:
            floors.append(int(value))
    return targets, tests, floors


def test_every_matrix_target_and_test_file_actually_EXISTS() -> None:
    """A target that does not exist makes the sweep exit 2, and a test file that
    does not exist makes it measure a module nothing covers — a 0% score that is
    a fact about the SELECTION, not the suite. Checked here rather than
    discovered on a Monday."""
    targets, tests, _ = _matrix_legs()

    # FLOOR, because a regex that stops matching would otherwise make this pass
    # by finding nothing — the failure this file is named for.
    assert len(targets) >= 3, (
        f"only {len(targets)} sweep target(s) parsed from {WORKFLOW.name}; either "
        "the matrix shrank or the parser stopped matching, and those are "
        "different findings that look identical from here"
    )
    assert len(tests) == len(targets), (
        f"{len(targets)} target(s) but {len(tests)} test row(s) — every leg needs both"
    )

    for target in targets:
        assert (REPO_ROOT / target).is_file(), f"sweep target missing: {target}"
    for row in tests:
        for test in row.split():
            assert (REPO_ROOT / test).is_file(), f"sweep test missing: {test}"


def test_the_sweep_status_is_not_discarded() -> None:
    """No blanket `|| true`, and `pipefail` set before the `| tee`.

    The `tee` half is the one that bites: without `pipefail` the step reports
    TEE's exit code, so a sweep that failed its floor reads green. That is the
    defect `CLAUDE.md` records four times, and introducing it in the workflow
    about signals that lie would have been the joke.
    """
    # COMMENTS STRIPPED FIRST. The header of that workflow *discusses* `|| true`
    # at length — it is the defect the rewrite is about — so a naive substring
    # match fails on the file's own explanation of why the thing is absent. Same
    # rule the handshake protocol states for declarations: what a file STATES,
    # never what it QUOTES, and a format's own documentation is the likeliest
    # place to trip its parser.
    lines = [
        line
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    ]
    body = "\n".join(lines)
    assert "|| true" not in body, (
        "a blanket `|| true` makes a crash indistinguishable from a clean audit"
    )
    assert "set -o pipefail" in body, "the `| tee` would mask the sweep's exit code"


def test_the_workflow_passes_a_FLOOR_on_checked_mutants() -> None:
    """The anti-vacuity gate has to be armed at the call site, not merely
    available in the script."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--min-checked" in text, (
        "the sweep is invoked without a floor, so a run that checked nothing "
        "would exit 0 — the exact mutmut failure this audit was rebuilt to stop"
    )


def test_the_floor_CAN_fail_and_is_not_decoration(tmp_path: Path) -> None:
    """**Asserted by construction, not by reading the source.**

    A test that greps for `--min-checked` proves the flag is written down. This
    one proves it bites: a module with no mutable sites must make the CLI exit
    non-zero rather than report a clean sweep over nothing.
    """
    module = tmp_path / "nothing_to_mutate.py"
    module.write_text('def f():\n    return "no mutable sites"\n', encoding="utf-8")
    test = tmp_path / "test_nothing.py"
    test.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    assert (
        ms.main(["--target", str(module), "--tests", str(test), "--min-checked", "1"])
        != 0
    )


def test_a_sweep_that_DID_check_mutants_passes_the_same_floor(tmp_path: Path) -> None:
    """The other half. A floor that fails everything is as useless as one that
    fails nothing, and only the pair shows it discriminates."""
    module = tmp_path / "subject.py"
    module.write_text("def f(a, b):\n    return a < b\n", encoding="utf-8")
    test = tmp_path / "test_subject.py"
    test.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    assert (
        ms.main(["--target", str(module), "--tests", str(test), "--min-checked", "1"])
        == 0
    )


def test_every_leg_DECLARES_a_floor() -> None:
    """No default to fall back on, so a new leg cannot inherit somebody else's.

    The floor was one constant across every leg until 2026-09-06, and a single
    number cannot be right for populations that run from 3 mutants to 193. A leg
    added without one would silently be measured against a number chosen for a
    different module — which is how the `eac-log` leg came to carry a floor it
    could never reach.
    """
    targets, _, floors = _matrix_legs()
    assert len(floors) == len(targets), (
        f"{len(targets)} sweep leg(s) but {len(floors)} floor(s) — every leg "
        "declares its own, chosen against that module's mutant population"
    )
    for target, floor in zip(targets, floors, strict=True):
        assert floor >= 1, f"{target}: a floor of {floor} is satisfied by nothing"


def test_no_declared_floor_is_UNREACHABLE() -> None:
    """A floor above the module's mutant population can never pass.

    **This is the defect the file is named for, arriving through the
    configuration instead of the code.** The `eac-log` leg pointed at a 69-line
    parser that offers **3** mutants in total, under a floor of 8 — so it would
    have reported NO RESULT every week, for a reason that has nothing to do with
    whether its tests are any good. A permanently-red non-gating signal is worse
    than a missing one, because it teaches the reader to skip the whole
    workflow. Measured 2026-09-06, before the rewritten workflow's first
    scheduled run: `mutation.yml` had last run 2026-08-31 under mutmut.

    The floor is compared against ``min(--limit, generated)`` because the sweep
    samples down to ``--limit`` before executing, so the reachable ceiling is the
    smaller of the two — a floor of 60 on a 193-mutant module is unreachable just
    the same when only 40 are ever run.

    Generation only: no test process is spawned, so this costs an AST walk per
    leg rather than a sweep.
    """
    targets, _, floors = _matrix_legs()
    limit = _declared_limit()
    for target, floor in zip(targets, floors, strict=True):
        generated = len(ms._mutants_for(REPO_ROOT / target))
        reachable = min(limit, generated)
        assert floor <= reachable, (
            f"{target}: floor {floor} but only {reachable} mutant(s) can ever "
            f"reach a verdict ({generated} generated, --limit {limit}). This leg "
            "would report NO RESULT every run regardless of its tests — lower the "
            "floor to the module's real population, or point the leg at the "
            "module whose correctness you meant to measure."
        )
        # AND NOT SATISFIED BY FINDING NOTHING. A generator that stopped
        # producing mutants would make every floor "reachable" by making the
        # ceiling zero, which is the mutmut shape this whole file exists to
        # refuse.
        assert generated >= 1, (
            f"{target}: the generator produced no mutants at all, so this leg "
            "measures nothing — a broken generator and a perfect module look "
            "identical from a score"
        )


def test_the_archival_EAC_WRITER_is_swept_and_not_only_the_reader() -> None:
    """The artifact whose trustworthiness is the point is the one we EMIT.

    `parsers/eac_log.py` reads a third party's log; `eac_log_export.py` writes
    ours, and that file is the EAC-compatible record a tracker's logchecker and a
    future reader will judge this project by (KDD-24, `docs/eac-parity.md`). The
    matrix swept the 69-line reader and not the 1490-line writer — the smaller
    half of the pair, measured on the wrong side of the seam.

    Named explicitly rather than left to the length check above, because "the
    matrix has six legs" would stay true if this one were re-pointed at anything.
    """
    targets, _, _ = _matrix_legs()
    assert "src/platterpus/eac_log_export.py" in targets, (
        "the EAC log writer is not in the mutation matrix; sweeping only the "
        "reader measures our ability to consume somebody else's log, not our "
        "ability to produce a correct one"
    )
