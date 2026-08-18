"""Critical rule #11, mechanically: **a tool that gates CI must not float.**

The rule is a paragraph in ``CLAUDE.md``:

    ``ruff format`` and ``mypy --strict`` change what they accept between minor
    releases, so a wide version range means a routine upstream release turns CI red
    with zero change to our code — and it reads as a code problem. ``ruff`` and
    ``mypy`` are pinned to the minor they were measured against.

**It was written in the file that does not gate, and absent from the one that
does.** ``pyproject.toml``'s ``dev`` extra pinned ``ruff>=0.15.22,<0.16``; the
``lint`` job in ``.github/workflows/ci.yml`` — the job that actually decides whether
a PR merges — installed ``ruff>=0.15,<1``, the entire 0.x line. Only ``typecheck``
used the pin, because it installs the dev extra. So the gate this rule exists to
protect was the one place the rule did not reach, and the first ruff 0.16 release
would have reddened CI on somebody's unrelated pull request. Found 2026-08-18 by an
enforcement audit that asked, of every "enforced by" claim in ``CLAUDE.md``, *what
actually enforces this?*

The general lesson, which is why this file exists rather than a one-line workflow
fix: **a rule about a gate has to be checked at the gate.** Writing the constraint
where it is convenient to read is how it ends up describing a file nobody runs.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Final

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
PYPROJECT: Path = REPO_ROOT / "pyproject.toml"
CI_WORKFLOW: Path = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: The tools CLAUDE.md rule #11 names as gating. Not derived from the workflow: the
#: rule is about *these two specifically*, because their output changes between minor
#: releases in ways that fail a check rather than merely warn.
GATING_TOOLS: Final[tuple[str, ...]] = ("ruff", "mypy")

#: A pin whose upper bound is a MINOR, e.g. ``<0.16`` or ``<2.4``. ``<1`` is not one:
#: it admits every minor release in a major series, which is what floating means.
_MINOR_UPPER_BOUND: Final[re.Pattern[str]] = re.compile(r"<\s*(\d+)\.(\d+)")

#: A pip install of one of the gating tools carrying a literal version constraint.
#: Matches the shape the defect had — ``pip install "ruff>=0.15,<1"`` — including a
#: bare ``pip install ruff==0.15.0``. Deliberately does NOT match the fixed form,
#: which installs ``"$spec"`` read out of ``pyproject.toml`` at run time.
_LITERAL_PIN: Final[re.Pattern[str]] = re.compile(
    r"pip\s+install[^\n]*[\"']?\b(?P<tool>ruff|mypy)\s*[<>=!~]"
)


def _dev_extra() -> list[str]:
    document = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = document["project"]["optional-dependencies"]["dev"]
    assert isinstance(dev, list)
    return [str(entry) for entry in dev]


def _spec_for(tool: str) -> str:
    """The ``dev`` extra's requirement string for ``tool``."""
    for entry in _dev_extra():
        # Normalise the PEP 503 way, so `ruff` matches however it is spelled.
        if entry.replace("-", "_").lower().startswith(tool):
            return entry
    raise AssertionError(
        f"{tool!r} is not in pyproject's `dev` extra at all — CLAUDE.md rule #11 "
        f"names it as a gating tool, so its pin has to live somewhere"
    )


def test_every_gating_tool_is_pinned_to_a_minor() -> None:
    """The pin itself: an upper bound of ``<1`` is not a pin, it is a major range."""
    for tool in GATING_TOOLS:
        spec = _spec_for(tool)
        match = _MINOR_UPPER_BOUND.search(spec)
        assert match is not None, (
            f"{spec!r} has no minor-level upper bound. CLAUDE.md rule #11: a gating "
            f"tool is pinned to the minor it was measured against, because a routine "
            f"upstream release otherwise turns CI red with no change to our code."
        )


def test_the_ci_gate_installs_the_pin_rather_than_repeating_it() -> None:
    """**The half that was missing**, and the reason the pin did not bind.

    A literal version in the workflow is a *second* copy of the pin, free to disagree
    with the first — and it did, for the whole life of the ``lint`` job. So the
    workflow must derive the spec instead of restating it.
    """
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    offenders = sorted({m.group("tool") for m in _LITERAL_PIN.finditer(workflow)})
    assert not offenders, (
        f"{CI_WORKFLOW.name} installs {offenders} with a literal version constraint. "
        f"That is a second copy of the pin in the file that actually gates, and the "
        f"two drifted: pyproject said `<0.16` while the lint job said `<1`. Read the "
        f"spec out of pyproject.toml at run time so there is one source of truth."
    )


def test_the_ci_gate_still_installs_the_gating_tools_at_all() -> None:
    """The floor. Without it, deleting the install steps makes the test above pass.

    "Can this check be satisfied by finding nothing?" — it can, and this is the
    answer: the workflow must still name every gating tool and must still read the
    pin out of ``pyproject.toml``.
    """
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    for tool in GATING_TOOLS:
        assert tool in workflow, (
            f"{CI_WORKFLOW.name} does not mention {tool!r} at all — the gate it is "
            f"supposed to run has gone missing, and the pin check above would pass "
            f"quietly for exactly that reason"
        )
    assert "pyproject.toml" in workflow, (
        "no job reads pyproject.toml, so nothing derives a pin — the literal-pin "
        "check above is satisfied by a workflow that installs nothing"
    )


def test_the_literal_pin_detector_actually_matches_the_shipped_defect() -> None:
    """Non-triviality, measured against the real line rather than argued.

    The exact text that shipped is asserted to match, and the exact text that
    replaced it is asserted not to. A detector verified only against the current
    (clean) file cannot be told apart from one that matches nothing.
    """
    shipped = '        run: python -m pip install "ruff>=0.15,<1"'
    assert _LITERAL_PIN.search(shipped), (
        "the detector does not match the line that actually shipped — it would have "
        "reported the tree clean while the defect was in it"
    )

    fixed = '          python -m pip install "$spec"'
    assert not _LITERAL_PIN.search(fixed), (
        "the detector matches the derived form too, so it can never be satisfied"
    )

    # And the other spelling a future edit is most likely to reach for.
    assert _LITERAL_PIN.search("run: pip install mypy==2.3.0")
