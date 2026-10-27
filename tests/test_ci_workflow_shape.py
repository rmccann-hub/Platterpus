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
