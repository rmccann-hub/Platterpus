"""The repair plan: where each correction lands, and every refusal with its reason.

Pure, so every branch is reached here with hand-built localisations; the
end-to-end proof that a plan repairs real (synthetic) audio is
``tests/test_ctdb_repair.py``. The disc is three tracks of 40 sectors: 70,560
frames, 141,120 words, so ten parity rows of 11,760 words between a front guard
band of 11,760 words and a back one of 11,760 (``crc.ctdb_trims``).
"""

from __future__ import annotations

import dataclasses

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.adapters.ctdb_client import CtdbEntry
from platterpus.ctdb.differences import (
    CtdbLocalisation,
    EntryLocalisation,
    LocalisationStatus,
)
from platterpus.ctdb.repair_plan import plan_repair
from platterpus.ctdb.repair_types import PlanRefusal, RepairPlan

_FRAMES = (40 * 588, 40 * 588, 40 * 588)
_STRIDE = 11760
_TOTAL_WORDS = 2 * sum(_FRAMES)
_STRONG = CtdbEntry(
    crc=0x11111111,
    confidence=1416,
    track_crcs=(1, 2, 3),
    npar=16,
    entry_id="32115",
    stride=5880,
)
_WEAK = CtdbEntry(crc=0x22222222, confidence=1, track_crcs=(4, 5, 6), entry_id="w")
_ENTRIES = (_STRONG, _WEAK)
_DISC = {0: 0x22222222}  # our disc matches the weak entry, as the reference disc does


def _localised(
    words: tuple[int, ...],
    values: tuple[int, ...] | None = None,
    *,
    offset: int = 0,
    entry_id: str = "32115",
    crcs: tuple[int, ...] = (10, 20, 30),
) -> CtdbLocalisation:
    row = EntryLocalisation(
        entry_id,
        1416,
        LocalisationStatus.LOCATED,
        offset,
        words,
        values=values if values is not None else tuple(0x1234 for _ in words),
    )
    return CtdbLocalisation(
        LocalisationStatus.LOCATED, entries=(row,), track_crc32s=crcs
    )


def _plan(localisation: CtdbLocalisation, **kwargs: object) -> RepairPlan | PlanRefusal:
    entries = kwargs.pop("entries", _ENTRIES)
    disc = kwargs.pop("disc", _DISC)
    frames = kwargs.pop("frames", _FRAMES)
    return plan_repair(localisation, entries, disc, frames, **kwargs)


def _refused(localisation: CtdbLocalisation, **kwargs: object) -> str:
    got = _plan(localisation, **kwargs)
    assert isinstance(got, PlanRefusal), got
    return got.reason


# --- where each correction lands ------------------------------------------------


def test_each_word_lands_on_its_track_frame_and_channel() -> None:
    start2 = 2 * _FRAMES[0]  # track 2's first word
    words = (2 * 6000 + 1, start2 + 2 * 100, start2 + 2 * 100 + 1)
    plan = _plan(_localised(words, (1, 2, 0xFFFF)))
    assert isinstance(plan, RepairPlan)
    placed = [(f.track, f.frame, f.channel, f.value) for f in plan.fixes]
    assert placed == [(1, 6000, 1, 1), (2, 100, 0, 2), (2, 100, 1, 0xFFFF)]
    assert plan.tracks == (1, 2)
    assert plan.fixes_for(2)[0].track_word == 200
    assert plan.expected_disc_crc == _STRONG.crc
    assert plan.expected_track_crcs == (1, 2, 3)
    assert plan.track_starts == (0, 23520, 47040) and plan.total_frames == 70560
    assert plan.track_crc32s == (10, 20, 30) and plan.npar == 16


@pytest.mark.parametrize("offset", [-1500, 667])
def test_the_window_moves_with_the_offset(offset: int) -> None:
    first = _STRIDE + 2 * offset  # the window's first word
    last = _TOTAL_WORDS - _STRIDE + 2 * offset - 1  # and its last
    assert isinstance(_plan(_localised((first, last), offset=offset)), RepairPlan)
    assert "first stride" in _refused(_localised((first - 1,), offset=offset))
    assert "last stride" in _refused(_localised((last + 1,), offset=offset))


# --- the refusals --------------------------------------------------------------


def test_a_word_in_either_guard_band_is_refused() -> None:
    assert "first stride" in _refused(_localised((_STRIDE - 1,)))
    assert "last stride" in _refused(_localised((_TOTAL_WORDS - _STRIDE,)))
    assert "outside the disc's audio" in _refused(_localised((_TOTAL_WORDS + 5,)))


def test_only_the_strongest_entry_is_a_target() -> None:
    minority = _localised((20000,), entry_id="w")
    reason = _refused(minority)
    assert "strongest CTDB entry (1,416 submissions) was not located" in reason
    assert "weaker entry is never made" in reason
    tie = dataclasses.replace(_WEAK, confidence=1416)
    assert "tie as the strongest" in _refused(
        _localised((20000,)), entries=(_STRONG, tie)
    )
    assert "no entry" in _refused(_localised((20000,)), entries=())


def test_a_rip_that_already_matches_the_strongest_entry_is_left_alone() -> None:
    reason = _refused(_localised((20000,)), disc={0: 0x22222222, 3: _STRONG.crc})
    assert "already matches the strongest" in reason


def test_accuraterip_verified_tracks_are_never_rewritten() -> None:
    located = _localised((20000, 2 * _FRAMES[0] + 8))
    reason = _refused(located, accuraterip_verified={2: True})
    assert "AccurateRip verified track 2" in reason
    # Compared and not verified, or not said: AccurateRip does not contradict.
    for said in (False, None):
        assert isinstance(_plan(located, accuraterip_verified={2: said}), RepairPlan)


def test_npar_8_carries_four_corrections_a_column_and_npar_16_eight() -> None:
    five = tuple(_STRIDE + 7 + r * _STRIDE for r in range(5))  # five rows, one column
    eight = dataclasses.replace(_STRONG, npar=8)
    reason = _refused(_localised(five), entries=(eight, _WEAK))
    assert "5 corrections in one parity column" in reason and "the 4 an entry" in reason
    assert isinstance(_plan(_localised(five)), RepairPlan)
    nine = tuple(_STRIDE + 7 + r * _STRIDE for r in range(9))
    assert "the 8 an entry with 16" in _refused(_localised(nine))
    assert "too short" in _refused(
        _localised((20000,)), entries=(dataclasses.replace(_STRONG, npar=1), _WEAK)
    )


def test_a_layout_it_cannot_place_is_refused() -> None:
    located = _localised((20000,))
    assert "before track 1" in _refused(located, pregap_frames=588)
    assert "whole number of CD sectors" in _refused(
        located, frames=(23520, 23521, 23520)
    )
    assert "no tracks" in _refused(_localised((20000,), crcs=()), frames=())


def test_malformed_rows_are_refused() -> None:
    assert "not distinct" in _refused(_localised((20000, 20000)))
    assert "not distinct" in _refused(_localised((20002, 20000)))
    assert "16-bit" in _refused(_localised((20000,), (0,)))
    assert "16-bit" in _refused(_localised((20000,), (0x10000,)))
    assert "value for some" in _refused(_localised((20000, 20002), (1,)))
    assert "outside CTDB" in _refused(_localised((20000,), offset=5880))
    assert "every track's audio" in _refused(_localised((20000,), crcs=(1, 2)))
    bare = dataclasses.replace(_STRONG, track_crcs=())
    assert "per-track CRCs" in _refused(_localised((20000,)), entries=(bare, _WEAK))
    assert "located no difference" in _refused(
        CtdbLocalisation(LocalisationStatus.NOT_DETERMINED, "x")
    )


# --- never raises ----------------------------------------------------------------


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    words=st.lists(st.integers(-5, 200_000), max_size=12),
    values=st.lists(st.integers(-2, 0x10002), max_size=12),
    offset=st.one_of(st.none(), st.integers(-7000, 7000)),
    frames=st.lists(st.integers(-600, 60_000), max_size=4),
    crcs=st.lists(st.integers(0, 2**32 - 1), max_size=4),
    pregap=st.integers(-10, 600),
    npar=st.integers(-1, 40),
    confidences=st.lists(st.integers(-3, 3000), min_size=0, max_size=3),
)
def test_plan_repair_never_raises(
    words: list[int],
    values: list[int],
    offset: int | None,
    frames: list[int],
    crcs: list[int],
    pregap: int,
    npar: int,
    confidences: list[int],
) -> None:
    entries = tuple(
        dataclasses.replace(_STRONG, entry_id=str(i), confidence=c, npar=npar)
        for i, c in enumerate(confidences)
    )
    row = EntryLocalisation(
        "0", 1, LocalisationStatus.LOCATED, offset, tuple(words), values=tuple(values)
    )
    located = CtdbLocalisation(
        LocalisationStatus.LOCATED, entries=(row,), track_crc32s=tuple(crcs)
    )
    got = plan_repair(located, entries, {}, frames, pregap_frames=pregap)
    assert isinstance(got, RepairPlan | PlanRefusal)
    if isinstance(got, RepairPlan):
        assert all(0 < f.value <= 0xFFFF for f in got.fixes)
        assert all(0 <= f.frame < got.track_frames[f.track - 1] for f in got.fixes)
