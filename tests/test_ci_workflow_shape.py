"""Shape rules for `.github/workflows/ci.yml` that no other sweep holds.

Each test here pins one item of the 2026-10-27 external review that changed
`ci.yml`, so a later edit cannot quietly undo it. Parsed as text rather than
YAML: PyYAML is not a declared dependency of the suite (the same choice
`tests/test_workflow_permissions.py` makes), and each shape checked is a line or
two at a known indentation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

CI_YML: Final[Path] = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
)


def _ci_lines() -> list[str]:
    return CI_YML.read_text(encoding="utf-8").splitlines()


def _step_block(lines: list[str], index: int) -> list[str]:
    """The lines of the step starting at `index`, up to the next step or job."""
    indent = len(lines[index]) - len(lines[index].lstrip(" "))
    block = [lines[index]]
    for line in lines[index + 1 :]:
        stripped = line.strip()
        here = len(line) - len(line.lstrip(" "))
        if stripped and here <= indent and not stripped.startswith("#"):
            break
        block.append(line)
    return block


def test_every_checkout_drops_its_token() -> None:
    """Item 1.4: no checkout in ci.yml leaves the token in the clone.

    No job here pushes, so none needs the credential persisted. A NEW checkout
    added without the setting turns this red, which a per-step fix could not do.
    """
    lines = _ci_lines()
    checkouts = [
        i
        for i, ln in enumerate(lines)
        if re.match(r"^\s*- uses: actions/checkout@", ln)
    ]
    # NON-TRIVIALITY: ci.yml has nine jobs, each with one checkout. A pattern that
    # matched nothing would pass the loop below.
    assert len(checkouts) >= 9, checkouts
    missing = [
        f"ci.yml:{i + 1}"
        for i in checkouts
        if not any(
            ln.strip() == "persist-credentials: false" for ln in _step_block(lines, i)
        )
    ]
    assert not missing, f"checkouts that keep their token: {missing}"


def test_every_qt_job_installs_the_font_the_conformance_gate_measures() -> None:
    """Item 3.1: the gate's fixture selects DejaVu Sans, so CI must install it.

    Read from the apt install calls themselves, not from a mention in a comment:
    the package must be an argument of `apt-get ... install`. EVERY such call,
    since 2026-11-02: the matrix moved to the `ui-conformance` job, and a check
    that read only the first call would have passed with the font missing from
    the job that measures with it.
    """
    text = CI_YML.read_text(encoding="utf-8")
    installs = re.findall(r"apt-get \"\$\{opts\[@\]\}\" install -y([^;]*);", text)
    # NON-TRIVIALITY: both Qt jobs, `test` and `ui-conformance`, were found.
    assert len(installs) >= 2, f"found {len(installs)} apt install call(s)"
    for args in installs:
        packages = args.replace("\\", " ").split()
        assert "libfontconfig1" in packages, packages
        assert "fonts-dejavu-core" in packages, packages


#: The file the `ui-conformance` job runs and the `test` legs leave out.
_CONFORMANCE: Final[str] = "tests/test_ui_conformance.py"


def _job_block(lines: list[str], job: str) -> list[str]:
    """The lines of one job under `jobs:`, up to the next job."""
    start = lines.index(f"  {job}:")
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if re.match(r"^  [a-z][a-z0-9-]*:$", line) or re.match(r"^\S", line):
            break
        block.append(line)
    return block


def _pytest_calls(block: list[str]) -> list[str]:
    """Each `pytest ...` command in a job: a line that runs it (``run: pytest``
    or a folded line opening with ``pytest``), joined with the lines below it
    at the same indentation, which are the rest of a folded command."""
    calls: list[str] = []
    for i, line in enumerate(block):
        body = line.strip().removeprefix("run: ")
        if not body.startswith("pytest "):
            continue
        indent = len(line) - len(line.lstrip(" "))
        parts = [body]
        for more in block[i + 1 :]:
            if not more.strip() or len(more) - len(more.lstrip(" ")) != indent:
                break
            parts.append(more.strip())
        calls.append(" ".join(parts))
    return calls


def test_the_conformance_matrix_runs_in_exactly_one_job() -> None:
    """2026-11-02: the matrix left the `test` legs for a job of its own. The two
    halves are one claim: the legs `--ignore` the file AND `ui-conformance` runs
    it. Either half alone would lose it (ignored and run nowhere) or pay for it
    five times (run everywhere), so the relation is what is held."""
    lines = _ci_lines()
    legs = _pytest_calls(_job_block(lines, "test"))
    own = _pytest_calls(_job_block(lines, "ui-conformance"))
    assert len(legs) == 1 and len(own) == 1, (legs, own)
    assert f"--ignore={_CONFORMANCE}" in legs[0].split(), legs[0]
    assert own[0].split()[1:] == [_CONFORMANCE], own[0]
    # NON-TRIVIALITY: the file is real and holds the matrix.
    root = CI_YML.parents[2]
    assert "def test_every_window_passes_every_rule_in_every_condition" in (
        root / _CONFORMANCE
    ).read_text(encoding="utf-8")


def _top_level_block(lines: list[str], key: str) -> dict[str, str]:
    """A column-0 mapping's two-space children, as `{child: value}`."""
    start = next(i for i, ln in enumerate(lines) if ln == f"{key}:")
    block: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith("  ") or line.startswith("   "):
            break
        name, _, value = line.strip().partition(":")
        block[name] = value.strip()
    return block


def test_only_a_pull_request_run_can_be_cancelled() -> None:
    """Item 2.7: superseded pull-request runs are cancelled, and nothing else.

    `release.yml` gates on `main`'s own run for the merge SHA, so a push run must
    never be cancelled, neither in progress nor while pending. GitHub cancels an
    older PENDING run in the same group whatever `cancel-in-progress` says, so a
    push's group must be unique to its run, not shared by every push to `main`.
    """
    concurrency = _top_level_block(_ci_lines(), "concurrency")
    assert concurrency.get("cancel-in-progress") == (
        "${{ github.event_name == 'pull_request' }}"
    ), concurrency
    group = concurrency.get("group", "")
    assert "github.event.pull_request.number" in group, group
    # The fallback for every other event (push, workflow_dispatch) is the run's
    # own id, which no later run shares, so nothing can supersede it.
    assert "github.run_id" in group, group
    assert "github.ref" not in group and "github.sha" not in group, (
        "a push group keyed on the ref or the sha is shared by later runs, and "
        f"GitHub cancels the older pending one: {group}"
    )


def _release_required_checks() -> list[str]:
    """The check names `release.yml`'s CI gate requires, from its NAMES block."""
    text = (CI_YML.parent / "release.yml").read_text(encoding="utf-8")
    block = text.split("required=$(cat <<'NAMES'\n", 1)[1].split(
        "\n          NAMES\n", 1
    )[0]
    return [line.strip() for line in block.splitlines() if line.strip()]


def test_the_release_requires_every_test_leg_and_the_conformance_job() -> None:
    """2026-11-02: `release.yml` names the checks a release needs green, apart
    from ci.yml, and it had drifted twice. It never gained `ui-conformance`
    when #422 moved the matrix there, so a release could go out without the
    layout check; and it named `test (py3.11)`, which TASKS R99 removes. The
    legs are read from ci.yml's matrix, so the two cannot disagree again."""
    lines = _ci_lines()
    matrix = next(ln for ln in lines if ln.strip().startswith("python-version: ["))
    versions = re.findall(r'"(\d+\.\d+)"', matrix)
    # NON-TRIVIALITY: a real matrix was read.
    assert len(versions) >= 3, matrix
    legs = {f"test (py{v})" for v in versions}
    required = _release_required_checks()
    assert legs <= set(required), sorted(legs - set(required))
    stale = {n for n in required if n.startswith("test (py")} - legs
    assert not stale, (
        f"release.yml requires legs ci.yml no longer runs: {sorted(stale)}"
    )
    assert "ui-conformance" in required, required
