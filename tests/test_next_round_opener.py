"""§1a in our own laps: the next round is the provider's to open (TASKS R171).

Our round 40 lap 4 said *"Round 41 opens with whichever side writes its lap 1"*,
which `docs/handshake-protocol.md` §1a forbids (cyanrip, the provider, opens
every round unless the operator signs an E3 override), and ``handshake.py
--check`` passed it with no warning. These tests hold the refusal that now
catches it.

Sent laps are immutable: every test that needs a variant of a real lap copies
its text into ``tmp_path`` and edits the copy. Nothing here writes under
``docs/handshake/``.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import given
from hypothesis import strategies as st

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUTBOUND = _REPO_ROOT / "docs" / "handshake" / "outbound"
_LAP_40_4 = _OUTBOUND / "round-40-lap-04.md"

#: The two laps of ours that broke §1a, found by running the check over every
#: outbound lap on 2026-11-16. A closed set: a third would be a new defect, and a
#: lap dropping out of it would mean the check went blind.
_KNOWN_OFFENDERS = {"round-29-lap-04.md", "round-40-lap-04.md"}


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, _REPO_ROOT / "scripts" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hs() -> ModuleType:
    return _load("handshake")


#: Loaded once: the property test below runs many examples, and a function-scoped
#: fixture under ``@given`` is a hypothesis health-check failure.
_OPENER: ModuleType = _load("next_round_opener")


def _opener_refusals(problems: list[str]) -> list[str]:
    return [p for p in problems if "§1a" in p]


def _with_next_lap(text: str, value: str) -> str:
    """The lap's text with only its HANDSHAKE-NEXT-LAP value replaced."""
    edited, count = re.subn(
        r"^HANDSHAKE-NEXT-LAP: .*$",
        lambda _m: f"HANDSHAKE-NEXT-LAP: {value}",
        text,
        flags=re.M,
    )
    assert count == 1, "the fixture lap no longer has exactly one NEXT-LAP line"
    return edited


def _write_copy(tmp_path: Path, text: str) -> Path:
    folder = tmp_path / "outbound"
    folder.mkdir(exist_ok=True)
    path = folder / "round-40-lap-04.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_our_sent_round_40_lap_4_is_refused_by_check(hs: ModuleType) -> None:
    """The lap that started R171, read in place and never edited, fails --check."""
    text = _LAP_40_4.read_text(encoding="utf-8")
    assert "whichever side writes its lap 1" in text, "the fixture lap changed"
    problems = _opener_refusals(hs.check_outbound_paths(_LAP_40_4))
    assert len(problems) == 1, problems
    assert "whichever side" in problems[0] and "round 41" in problems[0]


def test_the_refused_set_over_every_sent_lap_is_exactly_the_two_offenders(
    hs: ModuleType,
) -> None:
    """Run over the whole record: the two laps that broke §1a are refused, and
    every lap that said it right (or said nothing about the next round) passes.
    The floor stops this passing by finding no laps to read."""
    examined = 0
    refused: set[str] = set()
    for path in sorted(_OUTBOUND.glob("round-*.md")):
        text = path.read_text(encoding="utf-8")
        if "HANDSHAKE-NEXT-LAP:" not in text:
            continue
        examined += 1
        if hs.next_round_opener_problems(text, path.name):
            refused.add(path.name)
    assert examined >= 90, f"only {examined} laps carry HANDSHAKE-NEXT-LAP"
    assert refused == _KNOWN_OFFENDERS


@pytest.mark.parametrize(
    "lap",
    [
        "round-15-lap-15.md",  # "Round 16 is yours to open"
        "round-28-lap-09.md",  # "round 29's lap 1 is yours"
        "round-30-lap-16.md",  # "round 31 then opens with your lap 1"
        "round-31-lap-05.md",  # "round 32 opens with your lap 1"
        "round-35-lap-18.md",  # "Round 36 is yours to open under §1a"
        "round-38-lap-06.md",  # "7 (ours): …", a lap of the CURRENT round
        "round-40-lap-02.md",  # "3 (yours): …"
    ],
)
def test_real_correct_next_lap_prose_passes(hs: ModuleType, lap: str) -> None:
    path = _OUTBOUND / lap
    assert hs.next_round_opener_problems(path.read_text("utf-8"), lap) == []


@pytest.mark.parametrize(
    "value",
    [
        "3 (yours): your reading of this lap; nothing closes on it.",
        "none in round 40: this lap closes it; round 41 is yours to open.",
        "none — round 40 closes here. Round 41 opens with your lap 1, as §1a says.",
        "none — round 41 is yours to open, not ours.",
        "7 (ours): the reading of the run on `0.6.63`; then yours.",
    ],
)
def test_correct_values_pass(hs: ModuleType, tmp_path: Path, value: str) -> None:
    text = _with_next_lap(_LAP_40_4.read_text(encoding="utf-8"), value)
    assert _opener_refusals(hs.check_outbound_paths(_write_copy(tmp_path, text))) == []


@pytest.mark.parametrize(
    "value",
    [
        "none — Round 41 opens with whichever side writes its lap 1.",
        "none in round 40. Round 41 opens with a lap 1 from either side.",
        "none — round 41 is ours to open.",
        "none — round 41 opens with our lap 1.",
        "none; we will open round 41 with the fixes.",
        "none — the next round opens with any side's lap 1.",
    ],
)
def test_wrong_openers_are_refused(hs: ModuleType, tmp_path: Path, value: str) -> None:
    text = _with_next_lap(_LAP_40_4.read_text(encoding="utf-8"), value)
    problems = _opener_refusals(hs.check_outbound_paths(_write_copy(tmp_path, text)))
    assert len(problems) == 1, (value, problems)


_E3 = (
    "HANDSHAKE-OVERRIDE: 1a — Platterpus opens round 41\n"
    "HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-11-16\n"
    "HANDSHAKE-OVERRIDE-WHY: the fork is away and our fix needs a round now\n"
)


def _with_override(text: str, override: str) -> str:
    """Insert the override lines just after the lap's NEXT-LAP line."""
    return re.sub(
        r"^(HANDSHAKE-NEXT-LAP: .*\n)",
        lambda m: m.group(1) + override,
        text,
        count=1,
        flags=re.M,
    )


def test_a_signed_e3_override_lets_us_open(hs: ModuleType, tmp_path: Path) -> None:
    text = _with_override(
        _with_next_lap(
            _LAP_40_4.read_text(encoding="utf-8"),
            "none — round 41 opens with our lap 1, under the E3 override below.",
        ),
        _E3,
    )
    assert _opener_refusals(hs.check_outbound_paths(_write_copy(tmp_path, text))) == []


@pytest.mark.parametrize(
    "override",
    [
        # No WHY: §6a-ter says "Rule id, who, and why. All three."
        "HANDSHAKE-OVERRIDE: 1a — Platterpus opens round 41\n"
        "HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-11-16\n",
        # No BY.
        "HANDSHAKE-OVERRIDE: 1a — Platterpus opens round 41\n"
        "HANDSHAKE-OVERRIDE-WHY: the fork is away and our fix needs a round now\n",
        # Signed, but for another round: an old override cannot be carried over.
        "HANDSHAKE-OVERRIDE: 1a — Platterpus opens round 40\n"
        "HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-11-16\n"
        "HANDSHAKE-OVERRIDE-WHY: the fork is away and our fix needs a round now\n",
        # Signed, but overriding a different rule.
        "HANDSHAKE-OVERRIDE: R4 — pin moved in round 41\n"
        "HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-11-16\n"
        "HANDSHAKE-OVERRIDE-WHY: the fork is away and our fix needs a round now\n",
    ],
)
def test_an_incomplete_or_misdirected_override_does_not(
    hs: ModuleType, tmp_path: Path, override: str
) -> None:
    text = _with_override(
        _with_next_lap(
            _LAP_40_4.read_text(encoding="utf-8"),
            "none — round 41 opens with our lap 1.",
        ),
        override,
    )
    assert len(_opener_refusals(hs.check_outbound_paths(_write_copy(tmp_path, text))))


def test_an_unreadable_round_number_defers_to_the_header_check() -> None:
    declared = [
        ("HANDSHAKE-ROUND", "forty"),
        ("HANDSHAKE-NEXT-LAP", "none — round 41 opens with whichever side."),
    ]
    assert _OPENER.opener_problems(declared, "x") == []


@given(
    st.lists(
        st.tuples(
            st.sampled_from(
                ["HANDSHAKE-ROUND", "HANDSHAKE-NEXT-LAP", "HANDSHAKE-OVERRIDE", "X"]
            ),
            st.text(max_size=200),
        ),
        max_size=6,
    )
)
def test_opener_problems_never_raises(declared: list[tuple[str, str]]) -> None:
    assert isinstance(_OPENER.opener_problems(declared, "x"), list)
