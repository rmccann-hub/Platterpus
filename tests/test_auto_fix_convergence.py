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
