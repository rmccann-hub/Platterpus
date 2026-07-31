"""Regression tests: a swapped-in re-rip must be what every surface describes.

Two real-hardware bugs, both from the same root cause — the album's whole-disc
`.log` records only the FIRST read pass, so anything the per-track auto-fix does
afterwards is invisible to it:

* **v0.5.9 run (2026-07-26):** a track whose `-Z N` re-reads *agreed* rendered a
  lone `Copy CRC`, dropping the Test & Copy proof we had earned (KDD-30); a track
  whose re-reads *disagreed* rendered indistinguishably from a clean one.
* **v0.5.10 run (same day, worse):** when the re-rip produced *different* audio
  and was swapped in, the EAC-compatible log and the JSON report still printed the
  **first pass's** CRC beside the shipped file's name — and v0.5.10's new
  convergence note decorated that wrong CRC with a proof. cyanrip's own log has a
  written addendum superseding the value; our renderings had no such mechanism.

So the merge rule under test is: measured fields come from the shipped read,
identity fields never move, an absent value never erases a real one, and the
convergence verdict is only ever the one we actually measured.
"""

from __future__ import annotations

from types import SimpleNamespace

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.ui.main_window_rip import RipMixin, _merge_shipped_track


def _window(
    retried: list[dict] | None, swapped: dict[int, object] | None = None
) -> SimpleNamespace:
    """A minimal stand-in exposing only the two attributes the enricher reads."""
    return SimpleNamespace(
        _last_retried_tracks=retried,
        _last_swapped_tracks=swapped or {},
    )


def _log() -> RipLog:
    """Two tracks shaped like the real run: 3 and 5 are the re-read candidates."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(number=3, filename="03.flac", copy_crc="52DFDF7D"),
            TrackResult(number=5, filename="05.flac", copy_crc="6902BCF0"),
        ),
    )


def _by_number(rip_log: RipLog, number: int) -> TrackResult:
    return next(t for t in rip_log.tracks if t.number == number)


# --- the shipped read replaces the discarded one -----------------------------


def test_swapped_track_reports_the_shipped_crc() -> None:
    # THE v0.5.10 hardware bug: track 3's first pass read 52DFDF7D, the re-rip
    # that was swapped in read 3D8FCF0C — the CRC must name the file on disk.
    window = _window(
        [{"track": 3, "reripped_z": 2, "converged": True, "replaced": True}],
        {3: TrackResult(number=3, filename="tmp/03.flac", copy_crc="3D8FCF0C")},
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 3).copy_crc == "3D8FCF0C"


def test_identity_fields_are_never_taken_from_the_rerip() -> None:
    # The re-rip ran in a throwaway directory, so its filename is not the album's.
    window = _window(
        [{"track": 3, "reripped_z": 2, "converged": True, "replaced": True}],
        {3: TrackResult(number=3, filename="tmp/03.flac", copy_crc="3D8FCF0C")},
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 3).filename == "03.flac"


def test_shipped_accuraterip_results_replace_the_first_pass() -> None:
    # The AccurateRip verdict is a statement about specific bytes. After a swap it
    # must be the swapped-in read's, or we'd attribute a match to discarded audio.
    shipped = TrackResult(
        number=3,
        copy_crc="3D8FCF0C",
        accuraterip_v2=AccurateRipResult(
            version=2, result="accurately ripped", confidence=200, local_crc="ABCD1234"
        ),
    )
    window = _window(
        [{"track": 3, "reripped_z": 2, "converged": True, "replaced": True}],
        {3: shipped},
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 3).accuraterip_v2 is shipped.accuraterip_v2


def test_an_absent_rerip_value_never_erases_a_real_one() -> None:
    # A re-rip log that didn't report a CRC must not blank the one we have.
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": True}],
        {5: TrackResult(number=5, copy_crc="")},
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 5).copy_crc == "6902BCF0"


def test_tracks_the_auto_fix_never_touched_are_untouched() -> None:
    window = _window(
        [{"track": 3, "reripped_z": 2, "converged": True, "replaced": True}],
        {3: TrackResult(number=3, copy_crc="3D8FCF0C")},
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 5).copy_crc == "6902BCF0"
    assert _by_number(out, 5).secure_rerip_converged is None


def test_merge_helper_is_pure_and_returns_the_input_when_nothing_applies() -> None:
    # The merge rule is a module-level pure function, so it can be asserted on
    # directly: no shipped record and no verdict must be a no-op, not a copy.
    track = TrackResult(number=7, filename="07.flac", copy_crc="CCBFF669")
    assert _merge_shipped_track(track, None, {}) is track


# --- the convergence verdict -------------------------------------------------


def test_converged_and_swapped_track_is_marked() -> None:
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": True}]
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 5).secure_rerip_converged is True


def test_a_track_that_never_converged_is_recorded_as_such() -> None:
    # A MEASURED negative: it was re-read and no two reads agreed. Recorded, so the
    # log can't let it pass as clean — cyanrip's health line says "no errors" here.
    window = _window(
        [{"track": 3, "reripped_z": 2, "converged": False, "replaced": False}]
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 3).secure_rerip_converged is False


def test_converged_but_not_swapped_is_not_marked() -> None:
    # The re-read agreed but never replaced the album's file, so the shipped audio
    # is still the single-read first pass. Claiming convergence would attribute the
    # proof to bytes it wasn't earned on.
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": False}]
    )
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 5).secure_rerip_converged is None


def test_no_auto_fix_history_returns_the_log_unchanged() -> None:
    rip_log = _log()
    assert RipMixin._apply_auto_fix_results(_window([]), rip_log) is rip_log
    assert RipMixin._apply_auto_fix_results(_window(None), rip_log) is rip_log


def test_never_raises_on_a_malformed_history() -> None:
    # Worker-supplied data: a bad shape must degrade to "no enrichment", never
    # abort the post-rip chain.
    window = _window(["not-a-dict"])  # type: ignore[list-item]
    out = RipMixin._apply_auto_fix_results(window, _log())
    assert _by_number(out, 5).secure_rerip_converged is None


# --- end-to-end through the renderer ----------------------------------------


def test_rendered_log_pairs_the_shipped_crc_not_the_discarded_one() -> None:
    # The exact v0.5.10 regression: track 3 converged and was swapped in, so the
    # Test/Copy pair must carry 3D8FCF0C — the first pass's 52DFDF7D must be gone.
    window = _window(
        [{"track": 3, "reripped_z": 2, "converged": True, "replaced": True}],
        {3: TrackResult(number=3, copy_crc="3D8FCF0C")},
    )
    text = render_eac_style_log(RipMixin._apply_auto_fix_results(window, _log()))
    assert "Test CRC 3D8FCF0C" in text
    assert "Copy CRC 3D8FCF0C" in text
    assert "52DFDF7D" not in text


def test_rendered_log_flags_only_the_track_whose_rereads_disagreed() -> None:
    window = _window(
        [
            {"track": 3, "reripped_z": 2, "converged": False, "replaced": False},
            {"track": 5, "reripped_z": 2, "converged": True, "replaced": True},
        ],
        {5: TrackResult(number=5, copy_crc="E0036697")},
    )
    text = render_eac_style_log(RipMixin._apply_auto_fix_results(window, _log()))
    assert "Test CRC E0036697" in text
    assert "Test CRC 52DFDF7D" not in text
    assert "not confirmed reproducible" in text
    assert "Read stability      : track(s) 3" in text


def test_a_clean_rip_gains_no_read_stability_line() -> None:
    # Nothing measured → nothing said. A clean rip's conclusive report is unchanged.
    text = render_eac_style_log(_log())
    assert "Read stability" not in text
    assert "not confirmed reproducible" not in text


# --- an interrupted securing pass must be recorded (real-hardware, 2026-07-28) --


def test_secure_rerip_report_marks_an_interrupted_pass() -> None:
    """Closing the app mid-securing produced a report that implied a clean pass.

    Run 4 on the reference rig: the auto-fix launched `cyanrip -Z 2 -l 3,5`, the
    window was closed 26 minutes in, the drive was killed — and the JSON recorded
    `secure_rerip.engaged: true` with an EMPTY `retried_tracks` and nothing
    anywhere saying the pass was cut short. The audio was fine (the re-rip works
    in a temp directory and only swaps on success), but the record implied a
    securing pass that never finished.
    """
    from platterpus.workers.rip_worker import RipWorker

    worker = RipWorker.__new__(RipWorker)  # no Qt, no thread — state only
    worker._secure_rerip_mode = "dynamic"
    worker._secure_rerip_engaged = True
    worker._disc_in_accuraterip = True
    worker._secure_rerip_skipped_reason = None

    # Mid-pass: the flag is up.
    worker._secure_rerip_interrupted = True
    assert worker.secure_rerip_report["interrupted"] is True

    # Completed: the pass recorded its per-track outcomes and lowered the flag.
    worker._secure_rerip_interrupted = False
    assert worker.secure_rerip_report["interrupted"] is False


def test_a_saved_log_reparses_to_the_shipped_crcs_not_the_discarded_ones() -> None:
    """The swap addendum must survive a round-trip through the file.

    The GUI patches the CRCs from live worker state, so it never hit this — but
    anything re-reading the saved `.log` from disk (parity.track_copy_crcs, the
    `--compare` path, a third-party tool) got the FIRST pass's CRCs, describing
    bytes that are not on disk. Our own addendum says in words that its values
    supersede; the parser now honours that (review finding, 2026-07-28).
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    log_text = "\n".join(
        [
            "cyanrip 0.9.3",
            "Track 3 ripped and encoded successfully!",
            "  EAC CRC32:     52DFDF7D",
            "Track 5 ripped and encoded successfully!",
            "  EAC CRC32:     6902BCF0",
            "Ripping errors: 0",
            "",
            "=" * 72,
            "[Platterpus auto-fix addendum]",
            "Each CRC below is the SHIPPED file's and supersedes the",
            "value recorded for that track above.",
            "  Track 3 (The Police/03 - Message in a Bottle.flac): CRC 3D8FCF0C",
            "  Track 5 (The Police/05 - Don't Stand So Close to Me.flac): CRC E0036697",
            "=" * 72,
            "",
        ]
    )
    by_number = {t.number: t.copy_crc for t in parse_cyanrip_log(log_text).tracks}
    assert by_number[3] == "3D8FCF0C"
    assert by_number[5] == "E0036697"


def test_a_log_with_no_addendum_is_unchanged_by_the_addendum_pass() -> None:
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    text = "cyanrip 0.9.3\nTrack 1 ripped and encoded successfully!\n  EAC CRC32:     B0D122E7\n"
    assert parse_cyanrip_log(text).tracks[0].copy_crc == "B0D122E7"


# --- the stale AccurateRip verdict (TASKS #55, the worst of the three) -------


def test_a_replaced_track_never_inherits_the_first_passs_accuraterip_verdict() -> None:
    """The single worst thing this program could say, and it was saying it.

    When the auto-fix re-rips a track and swaps the better read into the album,
    every measured field is supposed to come from the *shipped* read. But the merge
    used a fallback helper: if the re-rip's log didn't print an AccurateRip line,
    the FIRST pass's result was kept — and the first pass's result confirmed the
    bytes that were thrown away.

    The consequence is not cosmetic. `track_accuraterip_verified` reads exactly
    these fields, so the trust banner, the JSON report, the per-track table and the
    EAC log would all assert **"AccurateRip verified"** for audio that was never
    checked against AccurateRip at all. That is the precise failure KDD-30 exists
    to prevent.

    Unknown is the honest answer, and the UI already renders it.
    """
    verified = AccurateRipResult(
        version=2, result="accurately ripped, confidence 200", confidence=200
    )
    first_pass = TrackResult(
        number=3,
        filename="03.flac",
        copy_crc="52DFDF7D",
        test_crc="52DFDF7D",
        accuraterip_v2=verified,
    )
    # The re-rip printed a new CRC but NO AccurateRip line — the case that bit us.
    shipped = TrackResult(number=3, copy_crc="3D8FCF0C")

    merged = _merge_shipped_track(first_pass, shipped, {3: True})

    assert merged.copy_crc == "3D8FCF0C", "the shipped read's CRC still wins"
    assert merged.accuraterip_v2 is None, (
        "an unreported verification must become UNKNOWN, never inherit the "
        "verdict that belonged to the discarded read"
    )
    # `test_crc` is typed `str` and defaults to "", so "unreported" is falsy here
    # rather than None. What matters is that it is NOT the first pass's value:
    # pairing that with the replacement's Copy CRC would render a two-reads-agree
    # convergence that never happened.
    assert not merged.test_crc, "an unreported Test CRC must stay unreported"
    assert merged.test_crc != "52DFDF7D", (
        "and it must specifically not be the discarded read's Test CRC"
    )


def test_a_replaced_track_keeps_a_verdict_the_rerip_actually_earned() -> None:
    """The other direction, so the fix cannot be 'always discard'.

    A re-rip whose log DOES carry an AccurateRip result must keep it — otherwise
    the fix would throw away real verification and under-report every auto-fixed
    track, which is a different bug wearing the same clothes.
    """
    stale = AccurateRipResult(version=2, result="not found", confidence=None)
    earned = AccurateRipResult(
        version=2, result="accurately ripped, confidence 12", confidence=12
    )
    first_pass = TrackResult(
        number=5, filename="05.flac", copy_crc="AAAA1111", accuraterip_v2=stale
    )
    shipped = TrackResult(number=5, copy_crc="E0036697", accuraterip_v2=earned)

    merged = _merge_shipped_track(first_pass, shipped, {5: True})

    assert merged.accuraterip_v2 is earned
    assert merged.accuraterip_v2 is not stale
    assert merged.copy_crc == "E0036697"


def test_an_untouched_track_keeps_everything_it_had() -> None:
    """The guard must only apply where a swap happened.

    A track the auto-fix never touched still has its first-pass verdict describing
    its own bytes, so nothing about it may change. Without this, "don't inherit"
    would wipe the verdict off every clean track on the disc.
    """
    verified = AccurateRipResult(
        version=1, result="accurately ripped, confidence 129", confidence=129
    )
    track = TrackResult(
        number=1, filename="01.flac", copy_crc="B0D122E7", accuraterip_v1=verified
    )
    merged = _merge_shipped_track(track, None, {})
    assert merged is track
    assert merged.accuraterip_v1 is verified
