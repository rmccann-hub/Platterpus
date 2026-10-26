"""Tests for platterpus.drive_media — the media-change auto-detect (fakes only;
the ioctl path is hardware-gated and degrades to 'unavailable')."""

from __future__ import annotations

from evidence_paths import evidence
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import drive_media
from platterpus.drive_media import (
    DISC,
    EMPTY,
    INSERTED,
    NO_CHANGE,
    NOT_READY,
    OPEN,
    REMOVAL_CONFIRM_S,
    REMOVED,
    RETURNED,
    UNAVAILABLE,
    MediaWatcher,
    probe_disc_status,
)


def _stepping(step: float = 10.0) -> MediaWatcher:
    """A watcher whose clock moves ``step`` seconds per known reading.

    With a step past :data:`REMOVAL_CONFIRM_S`, an empty tray read twice in a row
    has lasted long enough to be believed: the second reading confirms it. The
    product's clock is the monotonic one; this replays readings at poll pace
    without sleeping.
    """
    now = [0.0]

    def clock() -> float:
        now[0] += step
        return now[0]

    return MediaWatcher(clock=clock)


def _replay(timed: list[tuple[float, str]]) -> tuple[list[str], MediaWatcher]:
    """Feed ``(seconds, reading)`` pairs at exactly those times."""
    at = [0.0]
    w = MediaWatcher(clock=lambda: at[0])
    events: list[str] = []
    for when, reading in timed:
        at[0] = when
        events.append(w.observe_event(reading))
    return events, w


def test_first_observation_never_fires() -> None:
    # A disc already in the drive at startup is handled by the normal startup
    # scan — the watcher must not also fire on its very first reading.
    w = MediaWatcher()
    assert w.observe(DISC) is False
    assert w.observe(DISC) is False  # steady state → still no fire


def test_fires_on_empty_to_disc() -> None:
    w = MediaWatcher()
    assert w.observe(EMPTY) is False  # baseline
    assert w.observe(DISC) is True  # a disc appeared → rescan


def test_fires_after_eject_then_reinsert() -> None:
    # The exact cancel→eject→new-disc sequence: disc present, then ejected
    # (tray open / empty), then a new disc inserted.
    w = _stepping()
    assert w.observe(DISC) is False  # baseline (disc was in during/just after rip)
    assert w.observe(OPEN) is False  # cancel ejected it (not believed yet)
    assert w.observe(EMPTY) is False  # still empty 10 s later: a removal
    assert w.observe(DISC) is True  # new disc → rescan


def test_unavailable_blip_never_triggers() -> None:
    # A busy drive mid-teardown reads 'unavailable'; that must not manufacture a
    # spurious rescan when it clears back to 'disc'. The drive HAD a disc before
    # the blip — which is the case the rule is about. (Until 2026-09-28 this test
    # started from EMPTY and asserted no fire, i.e. it pinned the lost insertion
    # below as correct: its fixture was a real insertion, not a blip.)
    w = MediaWatcher()
    assert w.observe(DISC) is False  # baseline: a disc is in
    assert w.observe(UNAVAILABLE) is False
    assert w.observe(DISC) is False  # the same disc, still there → nothing


def test_an_insertion_seen_through_an_unreadable_check_still_fires() -> None:
    """The rig bug (2026-09-28). empty → unavailable → disc is a disc arriving.

    An unknown reading used to overwrite the previous state, so ``disc`` was
    compared with ``unavailable`` and the insertion was never reported: the disc
    sat unread until the tray was cycled or the app restarted. Now the last
    KNOWN state is kept across the gap, however many unknown readings long.
    """
    for empty in (EMPTY, OPEN, NOT_READY):
        w = MediaWatcher()
        assert w.observe_event(empty) == NO_CHANGE  # baseline
        assert w.observe_event(UNAVAILABLE) == NO_CHANGE
        assert w.observe_event(UNAVAILABLE) == NO_CHANGE
        assert w.observe_event(DISC) == INSERTED, empty
        assert w.bridged_unknown_readings == 2
        assert w.bridge_note() == ", after 2 unreadable status checks"


def test_a_removal_seen_through_an_unreadable_check_still_fires() -> None:
    # The mirror: disc → unavailable → open is the disc leaving, and the view
    # must be cleared. It used to be swallowed the same way.
    w = _stepping()
    assert w.observe_event(DISC) == NO_CHANGE
    assert w.observe_event(UNAVAILABLE) == NO_CHANGE
    assert w.observe_event(OPEN) == NO_CHANGE  # not believed until it lasts
    assert w.observe_event(UNAVAILABLE) == NO_CHANGE
    assert w.observe_event(OPEN) == REMOVED
    assert w.bridge_note() == ", after 1 unreadable status check"


def test_the_rig_logs_two_removals_with_no_insertion_cannot_recur() -> None:
    """The committed evidence, replayed against the watcher.

    ``docs/handshake/artifactsround27/round27fullplatterpusapplog1.txt`` lines 34-35:
    *disc removed* at 20:30:07 and again at 23:25:32, with no *disc inserted*
    and no drive change between. For the second removal the watcher had to see
    a disc again; the only way it could see one without an INSERTED was through
    an unknown reading. This is the shortest sequence that produces that log, and
    it now reports the return of the disc.
    """
    w = _stepping()
    events = [
        w.observe_event(status)
        for status in (DISC, OPEN, OPEN, UNAVAILABLE, DISC, OPEN, OPEN)
    ]
    assert events == [
        NO_CHANGE,
        NO_CHANGE,
        REMOVED,
        NO_CHANGE,
        INSERTED,
        NO_CHANGE,
        REMOVED,
    ]


def test_the_rig_log_is_the_one_this_replays() -> None:
    """Pin the replay above to the artifact, not to my memory of it."""

    log = evidence("docs/handshake/artifactsround27/round27fullplatterpusapplog1.txt")
    lines = log.read_text(encoding="utf-8").splitlines()
    events = [
        (number, line)
        for number, line in enumerate(lines, start=1)
        if "disc removed from" in line
        or "disc inserted in" in line
        or "drive changed:" in line
    ]
    # Launch's drive change, then the two removals, then the script's drive change.
    assert [n for n, _ in events[:4]] == [11, 34, 35, 133], events[:4]
    assert "20:30:07" in events[1][1] and "23:25:32" in events[2][1]


def test_unknown_values_are_bridged_like_unavailable() -> None:
    # A value this module does not know is no information either, never a state.
    w = MediaWatcher()
    w.observe_event(EMPTY)
    assert w.observe_event("something-new") == NO_CHANGE
    assert w.observe_event(DISC) == INSERTED


def test_reset_forgets_a_pending_unknown_streak() -> None:
    w = MediaWatcher()
    w.observe_event(EMPTY)
    w.observe_event(UNAVAILABLE)
    w.reset()
    assert w.observe_event(DISC) == NO_CHANGE  # baseline after a reset, as before
    assert w.bridged_unknown_readings == 0
    assert w.last_status == DISC


def test_not_ready_to_disc_fires() -> None:
    w = MediaWatcher()
    assert w.observe(NOT_READY) is False
    assert w.observe(DISC) is True


def test_a_disc_the_app_read_is_not_an_insertion_when_the_drive_reports_it() -> None:
    """Code review 2026-09-28 (R0): a retry read the disc while the last reading
    was `not_ready`, and the drive's next `disc` fired INSERTED — a third read of
    a disc already on screen. The read is recorded silently instead."""
    for before in (NOT_READY, EMPTY, OPEN):
        w = _stepping()
        w.observe_event(DISC)
        w.observe_event(before)  # the last reading before the read
        w.note_disc_present()  # the app read the disc
        assert w.observe_event(DISC) == NO_CHANGE, before
        # The disc it read is what a later removal is measured against.
        assert w.observe_event(OPEN) == NO_CHANGE, before
        assert w.observe_event(OPEN) == REMOVED, before
        assert w.observe_event(DISC) == INSERTED, before


def test_noting_a_read_clears_the_unreadable_streak_and_keeps_the_readings() -> None:
    w = MediaWatcher()
    w.observe_event(NOT_READY)
    w.observe_event(UNAVAILABLE)
    w.note_disc_present()
    assert w.observe_event(DISC) == NO_CHANGE
    assert w.bridge_note() == "", "a read, not a reading, bridged the gap"
    assert w.last_status == DISC


def test_reset_forgets_baseline() -> None:
    # After a drive switch the caller resets; the next reading is a fresh
    # baseline (no fire even if it's a disc).
    w = MediaWatcher()
    w.observe(EMPTY)
    w.reset()
    assert w.observe(DISC) is False  # first obs after reset = baseline only


def test_observe_event_reports_insert_removal_and_none() -> None:
    # The richer form reports both transitions; insert/removal are opposites.
    w = _stepping()
    assert w.observe_event(EMPTY) == NO_CHANGE  # baseline
    assert w.observe_event(DISC) == INSERTED  # empty → disc
    assert w.observe_event(DISC) == NO_CHANGE  # steady state
    assert w.observe_event(OPEN) == NO_CHANGE  # tray open: not believed yet
    assert w.observe_event(OPEN) == REMOVED  # still open 10 s on: ejected
    assert w.observe_event(EMPTY) == NO_CHANGE  # open → empty is not a new event


def test_observe_event_removal_fires_for_each_empty_state() -> None:
    # A disc → any known-empty state (empty / open / not-ready) is a removal.
    for empty in (EMPTY, OPEN, NOT_READY):
        w = _stepping()
        assert w.observe_event(DISC) == NO_CHANGE  # baseline (disc present)
        assert w.observe_event(empty) == NO_CHANGE  # pending
        assert w.observe_event(empty) == REMOVED


def test_observe_event_removal_ignores_unavailable_blip() -> None:
    # disc → 'unavailable' (a busy drive mid-teardown) is NOT a removal, so a
    # transient probe failure can't wrongly clear a still-loaded disc view.
    w = MediaWatcher()
    assert w.observe_event(DISC) == NO_CHANGE  # baseline
    assert w.observe_event(UNAVAILABLE) == NO_CHANGE  # blip, not a removal
    assert w.observe_event(DISC) == NO_CHANGE  # back to disc from unknown → nothing


def test_observe_event_first_observation_never_fires_removal() -> None:
    # The very first reading only establishes the baseline, even if it's empty.
    w = MediaWatcher()
    assert w.observe_event(EMPTY) == NO_CHANGE


def test_probe_disc_status_never_raises_on_bad_device() -> None:
    # Best-effort contract: a missing/blank device degrades to 'unavailable',
    # never an exception (the caller just doesn't auto-rescan).
    assert probe_disc_status("") == UNAVAILABLE
    assert probe_disc_status("/dev/does-not-exist-platterpus") == UNAVAILABLE


def test_status_from_code_maps_cdrom_codes() -> None:
    # The CDROM_DRIVE_STATUS return codes map to our statuses; unknown → unavailable.
    assert drive_media.status_from_code(4) == DISC  # CDS_DISC_OK
    assert drive_media.status_from_code(1) == EMPTY  # CDS_NO_DISC
    assert drive_media.status_from_code(2) == OPEN  # CDS_TRAY_OPEN
    assert drive_media.status_from_code(3) == NOT_READY  # CDS_DRIVE_NOT_READY
    assert drive_media.status_from_code(0) == UNAVAILABLE  # CDS_NO_INFO / unknown
    assert drive_media.status_from_code(999) == UNAVAILABLE


# --- The invariant the rig log broke -----------------------------------------

_ANY_READING = st.sampled_from(
    [DISC, EMPTY, OPEN, NOT_READY, UNAVAILABLE, "garbage-status"]
)


#: Seconds between readings: all at once, at poll pace, and slower than the bound.
_STEPS = st.sampled_from([0.0, 2.5, 10.0])


@settings(max_examples=300)
@given(st.lists(_ANY_READING, max_size=40), _STEPS)
def test_events_strictly_alternate_whatever_the_drive_reports(
    readings: list[str], step: float
) -> None:
    """Between two removals there is always an insertion, and vice versa.

    That is what "the watcher tracks whether a disc is in" means, and it is the
    property the rig log contradicts (two removals, nothing between). The old
    watcher broke it on ``[disc, open, unavailable, disc, open]``. RETURNED is
    neither: the disc was never believed gone.
    """
    w = _stepping(step)
    fired = [
        e for e in (w.observe_event(r) for r in readings) if e in (INSERTED, REMOVED)
    ]
    for earlier, later in zip(fired, fired[1:], strict=False):
        assert earlier != later, (readings, fired)


@settings(max_examples=300)
@given(st.lists(_ANY_READING, max_size=40), _STEPS)
def test_every_known_empty_to_disc_transition_is_reported(
    readings: list[str], step: float
) -> None:
    """Counted against the readings themselves, with unknown ones dropped: every
    disc that appears after an empty reading is reported, as an insertion or (the
    empty part too short to believe) a return the caller re-reads."""
    known = [r for r in readings if r in (DISC, EMPTY, OPEN, NOT_READY)]
    expected = sum(
        1
        for before, after in zip(known, known[1:], strict=False)
        if before != DISC and after == DISC
    )
    w = _stepping(step)
    reported = sum(1 for r in readings if w.observe_event(r) in (INSERTED, RETURNED))
    assert reported == expected, readings


# --- The drive that flickers (the owner's Full runs on 0.7.112) --------------
#
# Timings copied from the app log in bundle `platterpusbundle20261021t113505z`
# (lines 649, 653, 665) and the same log grown in `platterpusbundle20261022t114515z`
# (lines 5735-5768, 14575-14608, and the real swap at 14616-14619). The bundles
# are the owner's and are not committed; the readings and times are copied exactly.

#: (seconds into the minute, reading): disc → open → unavailable → disc, nobody
#: touching the drive, 41 s after a rip. The `disc` before is one 2.5 s poll
#: earlier than the `open`; the log records changes only, so it is not logged.
_RUN_A_FLICKER: list[tuple[float, str]] = [
    (36.742, DISC),
    (39.242, OPEN),
    (39.301, UNAVAILABLE),
    (41.720, DISC),
]


def test_the_run_a_flicker_is_not_a_removal() -> None:
    """The reading that cost run A 57 of its 60 failures is a return, not an eject."""
    events, w = _replay(_RUN_A_FLICKER)
    assert events == [NO_CHANGE, NO_CHANGE, NO_CHANGE, RETURNED]
    assert abs(w.last_gap_seconds - 2.478) < 1e-6


def test_every_logged_flicker_is_shorter_than_the_bound_and_the_swap_longer() -> None:
    """The bound against the measurements it was chosen from, so moving it past
    either side of the data fails here rather than on the rig."""
    flickers = [  # open → disc, from the logged times
        41.720 - 39.242,  # 08:02 (run A)
        9.079 - 6.442,  # 11:09
        31.643 - 29.066,  # 12:12
        21.661 - 19.274,  # 15:30
        19.164 - 16.778,  # 16:44
        30.433 - 28.036,  # 02:50
        52.882 - 50.244,  # 04:08, the longest
        52.934 - 50.308,  # 05:06
        55.433 - 52.804,  # 06:16
    ]
    real_swap_open_s = (32 * 60 + 10.497) - (31 * 60 + 45.460)  # 07:31:45 → 07:32:10
    assert max(flickers) < REMOVAL_CONFIRM_S / 2, max(flickers)
    assert real_swap_open_s > REMOVAL_CONFIRM_S * 4, real_swap_open_s
    for gap in flickers:
        events, _w = _replay([(0.0, DISC), (2.5, OPEN), (2.5 + gap, DISC)])
        assert events[-1] == RETURNED, gap


def test_the_real_swap_in_the_same_log_is_still_a_removal_and_an_insertion() -> None:
    """07:31:45 open, read at each 2.5 s poll; 07:32:10 not_ready; 07:32:19 disc."""
    timed = [(0.0, DISC)] + [(2.5 + 2.5 * n, OPEN) for n in range(10)]
    timed += [(27.5 + 2.5 * n, NOT_READY) for n in range(4)] + [(36.2, DISC)]
    events, _w = _replay(timed)
    assert events.count(REMOVED) == 1 and events.count(INSERTED) == 1
    assert events.index(REMOVED) == 4, "believed at the first poll 6 s past the open"
    assert events[-1] == INSERTED and RETURNED not in events


def test_a_removal_is_measured_from_the_empty_reading_not_the_last_disc() -> None:
    """The poll is skipped for a whole rip, so the last `disc` reading can be an
    hour old when a flicker arrives (run A: 41 s after a 30-minute rip). A bound
    measured from it would believe the flicker at once."""
    events, _w = _replay([(0.0, DISC), (3600.0, OPEN), (3602.5, DISC)])
    assert events == [NO_CHANGE, NO_CHANGE, RETURNED]


def test_the_alternation_property_can_fail() -> None:
    """Non-triviality: the alternation check rejects the pre-2026-09-28 rule.

    The old rule is reconstructed here in four lines (remember every reading,
    unknown ones included) and fed the rig sequence. It produces the rig log's
    shape, two removals with nothing between, so a watcher that regressed to it
    would fail the property above rather than pass it by accident.
    """
    empty_states = {EMPTY, OPEN, NOT_READY}
    prev: str | None = None
    fired: list[str] = []
    for status in (DISC, OPEN, UNAVAILABLE, DISC, OPEN):
        if prev in empty_states and status == DISC:
            fired.append(INSERTED)
        elif prev == DISC and status in empty_states:
            fired.append(REMOVED)
        prev = status
    assert fired == [REMOVED, REMOVED]
    assert any(a == b for a, b in zip(fired, fired[1:], strict=False))
