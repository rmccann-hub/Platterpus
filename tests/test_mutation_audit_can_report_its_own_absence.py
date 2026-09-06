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
    r"^\s{10,14}(?P<key>target|tests):\s*(?P<value>\S.*?)\s*$"
)


def test_every_matrix_target_and_test_file_actually_EXISTS() -> None:
    """A target that does not exist makes the sweep exit 2, and a test file that
    does not exist makes it measure a module nothing covers — a 0% score that is
    a fact about the SELECTION, not the suite. Checked here rather than
    discovered on a Monday."""
    targets: list[str] = []
    tests: list[str] = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        match = _MATRIX_ROW.match(line)
        if match is None:
            continue
        (targets if match.group("key") == "target" else tests).append(
            match.group("value")
        )

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
