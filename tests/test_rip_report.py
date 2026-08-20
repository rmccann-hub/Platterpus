"""Tests for platterpus.rip_report (the machine-readable JSON rip report)."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.deps import fork_source
from platterpus.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    RippingInfo,
    TrackResult,
)
from platterpus.rip_report import (
    REPORT_SCHEMA_VERSION,
    build_debug_log,
    build_gates,
    build_outcome,
    build_report,
    build_settings,
    build_timing,
    report_path_for,
    report_to_json,
    write_report,
)


class _FakeConfig:
    """A minimal Config-shaped object for build_settings tests (pure, no I/O)."""

    output_format = "flac"
    mp3_vbr_quality = 0
    cover_art = "embed"
    read_speed_mode = "auto_ladder"
    read_speed = 0
    secure_rerip_dynamic = True
    secure_rerip_matches = 2
    max_retries = 5
    ctdb_verify_after_rip = True
    verify_flac_after_rip = True
    recompress_flac_after_rip = False
    rip_goal = "fast_verified"
    read_offset = 667
    override_read_offset = True


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CYANRIP_REFERENCE = (
    _REPO_ROOT
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)


def _sample_log() -> RipLog:
    return RipLog(
        log_creator="cyanrip 0.9.3",
        creation_date="2026-06-28",
        ripping_info=RippingInfo(
            drive="PIONEER BD-RW BDR-209D",
            defeat_audio_cache=True,
            read_offset_correction=667,
        ),
        tracks=(
            TrackResult(
                number=1,
                filename="01 - Roxanne.flac",
                test_crc="B0D122E7",
                copy_crc="B0D122E7",
                status="ripped successfully",
                accuraterip_v2=AccurateRipResult(
                    version=2,
                    result="accurately ripped",
                    confidence=200,
                    local_crc="22B9924D",
                ),
            ),
            TrackResult(number=2, copy_crc="DEADBEEF", status="ripped successfully"),
        ),
        accuraterip_summary="1/2 tracks ripped accurately (AccurateRip)",
        health_status="No errors occurred",
    )


def test_report_envelope_and_verdict() -> None:
    report = build_report(_sample_log(), generated_at="2026-06-28T12:00:00")
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["generator"]["name"] == "platterpus"
    assert report["generated_at"] == "2026-06-28T12:00:00"
    # Verdict reuses the shared rule: 1 of 2 verified → "warn".
    assert report["verdict"]["level"] == "warn"
    assert "1 of 2" in report["verdict"]["message"]
    assert report["rip"]["read_offset_correction"] == 667


def test_per_track_fields_use_shared_verified_rule() -> None:
    report = build_report(_sample_log())
    t1, t2 = report["tracks"]
    assert t1["number"] == 1
    assert t1["copy_crc"] == "B0D122E7"
    assert t1["accuraterip_verified"] is True  # confidence 200
    assert t1["accuraterip"]["v2"]["confidence"] == 200
    # Track 2 has a Copy CRC but no AccurateRip match → not verified.
    assert t2["accuraterip_verified"] is False
    assert t2["accuraterip"]["v1"] is None


def test_timing_section_absent_by_default() -> None:
    # No timing passed → the key is present but null (a consumer can rely on
    # the key always existing).
    report = build_report(_sample_log())
    assert report["timing"] is None


def test_timing_records_actual_and_realtime_multiplier() -> None:
    timing = build_timing(
        9493,  # the real 2h38m13s rip
        disc_seconds=3582,  # the disc's 59m42s audio length
        started_at="2026-06-30T17:52:14",
        finished_at="2026-06-30T20:30:27",
    )
    report = build_report(_sample_log(), timing=timing)
    t = report["timing"]
    assert t["elapsed_seconds"] == 9493
    assert t["elapsed_human"] == "2h 38m 13s"
    # elapsed ÷ disc length — the honest metric that replaces cyanrip's ETA.
    assert t["disc_seconds"] == 3582
    assert t["realtime_multiplier"] == round(9493 / 3582, 2)
    assert t["started_at"] == "2026-06-30T17:52:14"
    # cyanrip's bogus ETA is gone.
    assert "estimated_seconds" not in t
    assert "estimate_source" not in t


def test_timing_omits_multiplier_when_disc_unknown() -> None:
    # A rip with no disc duration (e.g. cancelled early) still records the
    # actual elapsed, but carries no multiplier keys.
    timing = build_timing(120, disc_seconds=None)
    assert timing["elapsed_seconds"] == 120
    assert timing["elapsed_human"] == "2m 0s"
    assert "realtime_multiplier" not in timing
    assert "disc_seconds" not in timing


def test_timing_handles_missing_elapsed() -> None:
    # Defensive: a None elapsed degrades to "unknown" rather than raising.
    timing = build_timing(None)
    assert timing["elapsed_seconds"] is None
    assert timing["elapsed_human"] == "unknown"


def test_debug_section_absent_by_default() -> None:
    report = build_report(_sample_log())
    assert report["debug"] is None


def test_debug_section_embeds_session_log() -> None:
    debug = build_debug_log(["line one", "line two"], truncated=False)
    report = build_report(_sample_log(), debug_log=debug)
    assert report["debug"]["lines"] == ["line one", "line two"]
    assert report["debug"]["truncated"] is False
    assert "excluding other albums" in report["debug"]["scope"]


def test_debug_section_notes_truncation() -> None:
    debug = build_debug_log(["kept"], truncated=True)
    assert build_report(_sample_log(), debug_log=debug)["debug"]["truncated"] is True


# --- Verification block + checksums (0.4.5, schema v2) -------------------


def test_verification_block_present_but_empty_by_default() -> None:
    report = build_report(_sample_log())
    assert report["verification"] == {
        "gates": None,
        "flac_integrity": None,
        "transcode": None,
        "derived": None,
        "recompress": None,
    }
    assert report["checksums"] is None


def test_flac_integrity_result_serialized() -> None:
    from platterpus.adapters.flac_verify import FlacVerifyResult

    report = build_report(
        _sample_log(), flac_verify_result=FlacVerifyResult(checked=14)
    )
    fi = report["verification"]["flac_integrity"]
    assert fi["ran"] is True and fi["ok"] is True and fi["checked"] == 14
    assert fi["failures"] == [] and fi["error"] is None


def test_flac_integrity_failure_serialized() -> None:
    from platterpus.adapters.flac_verify import FlacVerifyResult

    result = FlacVerifyResult(checked=14, failures=(Path("bad.flac"),))
    fi = build_report(_sample_log(), flac_verify_result=result)["verification"][
        "flac_integrity"
    ]
    assert fi["ok"] is False and fi["failures"] == ["bad.flac"]


def test_transcode_result_serialized() -> None:
    from platterpus.adapters.transcode import TranscodeResult

    report = build_report(
        _sample_log(), transcode_result=TranscodeResult(transcoded=14)
    )
    tc = report["verification"]["transcode"]
    assert tc["ran"] is True and tc["ok"] is True and tc["transcoded"] == 14


def test_derived_verify_lossless_result_serialized() -> None:
    from platterpus.adapters.derived_verify import DerivedVerifyResult

    report = build_report(
        _sample_log(),
        derived_verify_result=DerivedVerifyResult(
            fmt="wavpack", lossless=True, checked=14, expected=14
        ),
    )
    dv = report["verification"]["derived"]
    assert dv["format"] == "wavpack"
    assert dv["lossless"] is True
    assert dv["ok"] is True and dv["complete"] is True and dv["checked"] == 14
    assert dv["proof"] == "bit-identical PCM vs FLAC master"
    assert dv["mismatches"] == [] and dv["error"] is None


def test_derived_verify_lossy_mp3_states_it_is_not_bit_identity() -> None:
    from platterpus.adapters.derived_verify import DerivedVerifyResult

    dv = build_report(
        _sample_log(),
        derived_verify_result=DerivedVerifyResult(
            fmt="mp3", lossless=False, checked=14, expected=14
        ),
    )["verification"]["derived"]
    assert dv["lossless"] is False
    # The report must NOT claim MP3 bit-identity.
    assert "NOT bit-identical" in dv["proof"]
    assert dv["ok"] is True  # ok here means decode-clean + complete


def test_read_speed_block_serialized() -> None:
    from platterpus.read_speed_ladder import SpeedAttempt, attempts_to_report

    attempts = [SpeedAttempt(1, 0, 0, clean=False), SpeedAttempt(2, 8, 0, clean=True)]
    report = build_report(_sample_log(), read_speed=attempts_to_report(attempts))
    rs = report["read_speed"]
    assert rs is not None
    assert rs["escalated"] is True and rs["unresolved"] is False
    assert rs["final_speed"] == 8


def test_read_speed_block_absent_on_single_pass() -> None:
    # A normal single-pass rip passes no read_speed → the key is None (omitted).
    assert build_report(_sample_log())["read_speed"] is None


def test_read_speed_block_carries_flagged_unstable_tracks() -> None:
    # The "flag it, don't auto re-rip" case: one pass, no escalation, but a track
    # left unstable must reach the JSON as unresolved + a listed unstable track.
    from platterpus.read_speed_ladder import SpeedAttempt, attempts_to_report

    report = build_report(
        _sample_log(),
        read_speed=attempts_to_report(
            [SpeedAttempt(1, 0, 2, clean=False)], unstable=[3]
        ),
    )
    rs = report["read_speed"]
    assert rs["escalated"] is False  # we did NOT re-rip
    assert rs["unresolved"] is True  # …but it's flagged
    assert rs["unstable_tracks"] == [3]


def test_read_speed_block_records_auto_fix_retries() -> None:
    # The auto-fix re-ripped an unstable track; when it converged and replaced the
    # original, the track drops off unstable_tracks and is recorded in retried.
    from platterpus.read_speed_ladder import SpeedAttempt, attempts_to_report

    report = build_report(
        _sample_log(),
        read_speed=attempts_to_report(
            # No hard errors on the pass → clean; the instability was handled by
            # the auto-fix, so nothing is left unstable.
            [SpeedAttempt(1, 0, 2, clean=True)],
            unstable=[],  # nothing left unstable after the fix
            retried=[
                {"track": 3, "reripped_z": 3, "converged": True, "replaced": True}
            ],
        ),
    )
    rs = report["read_speed"]
    assert rs["unstable_tracks"] == []  # rescued
    assert rs["retried_tracks"] == [
        {"track": 3, "reripped_z": 3, "converged": True, "replaced": True}
    ]
    # An auto-fixed-and-clean rip is not "unresolved".
    assert rs["unresolved"] is False


def test_eta_trace_block_serialized_and_labeled() -> None:
    samples = [
        {
            "at": "2026-07-01T04:20:00-05:00",
            "elapsed_seconds": 100,
            "overall_percent": 50.0,
            "read_speed": 8,
            "our_eta_seconds": 100,
            "cyanrip_eta": "49m",
        }
    ]
    report = build_report(_sample_log(), eta_trace=samples)
    et = report["eta_trace"]
    assert et is not None
    assert et["samples"] == samples
    # The block is self-describing (labeled) — both estimates + the clock.
    assert "our_eta_seconds" in et["note"] and "cyanrip_eta" in et["note"]


def test_eta_trace_absent_when_not_recorded() -> None:
    assert build_report(_sample_log())["eta_trace"] is None


def test_eta_trace_backfills_actual_remaining_and_event_context() -> None:
    # Each sample gains actual_remaining_seconds (finish − at), so the estimate
    # can be read directly against the truth; the event context is preserved.
    samples = [
        {
            "at": "2026-07-01T04:00:00-05:00",
            "our_eta_seconds": 1200,
            "track": 1,
            "activity": "Reading track 1… 50%",
        },
        {
            "at": "2026-07-01T04:30:00-05:00",
            "our_eta_seconds": 3600,
            "track": 2,
            "activity": "Reading track 2… 10%",
        },
    ]
    report = build_report(
        _sample_log(),
        eta_trace=samples,
        timing={"finished_at": "2026-07-01T05:00:00-05:00"},
    )
    got = report["eta_trace"]["samples"]
    # 60 min remained at the first sample, 30 min at the second.
    assert got[0]["actual_remaining_seconds"] == 3600
    assert got[1]["actual_remaining_seconds"] == 1800
    # Event context (why a jump happened) is carried through.
    assert got[1]["track"] == 2 and "track 2" in got[1]["activity"]
    assert "actual_remaining_seconds" in report["eta_trace"]["note"]


def test_eta_trace_without_finish_omits_actual_remaining() -> None:
    # No finish time (e.g. a rip that never completed) → no actual field, no crash.
    samples = [{"at": "2026-07-01T04:00:00-05:00", "our_eta_seconds": 1200}]
    report = build_report(_sample_log(), eta_trace=samples)  # no timing
    assert "actual_remaining_seconds" not in report["eta_trace"]["samples"][0]


def test_derived_verify_mismatch_serialized() -> None:
    from platterpus.adapters.derived_verify import DerivedVerifyResult

    result = DerivedVerifyResult(
        fmt="wav", lossless=True, checked=14, expected=14, mismatches=(Path("bad.wav"),)
    )
    dv = build_report(_sample_log(), derived_verify_result=result)["verification"][
        "derived"
    ]
    assert dv["ok"] is False and dv["mismatches"] == ["bad.wav"]


def test_checksums_embedded_in_report() -> None:
    sums = {"01 - A.flac": "abc123", "01 - A.mp3": "def456"}
    report = build_report(_sample_log(), checksums=sums)
    assert report["checksums"] == sums


def test_schema_version_matches_constant() -> None:
    assert build_report(_sample_log())["schema_version"] == REPORT_SCHEMA_VERSION


def test_report_surfaces_v6_drive_and_track_diagnostics() -> None:
    """v6: speed_changeable (rip block) + per-track extraction metrics."""
    rip_log = RipLog(
        ripping_info=RippingInfo(
            drive="PIONEER BD-RW BDR-209D", speed_changeable=False
        ),
        tracks=(
            TrackResult(
                number=1,
                filename="01 - Roxanne.flac",
                extraction_speed=8.0,
                extraction_quality=99.9,
                pre_emphasis=False,
                peak_level=0.87,
            ),
        ),
    )
    report = build_report(rip_log)
    assert report["rip"]["speed_changeable"] is False
    track = report["tracks"][0]
    assert track["extraction_speed"] == 8.0
    assert track["extraction_quality"] == 99.9
    assert track["pre_emphasis"] is False
    assert track["peak_level"] == 0.87


def test_v6_diagnostics_absent_are_none() -> None:
    """A log without the diagnostics (e.g. whipper) leaves the fields None,
    never crashes."""
    report = build_report(_sample_log())
    assert report["rip"]["speed_changeable"] is None
    assert report["tracks"][0]["extraction_speed"] is None


def test_report_includes_loudness_checksum_and_replaygain() -> None:
    from platterpus.parsers.rip_log import RipLog, TrackResult

    log = RipLog(
        tracks=(TrackResult(1, replaygain={"REPLAYGAIN_TRACK_GAIN": "-4.10 dB"}),),
        album_loudness={"integrated_lufs": "-13.9", "true_peak_dbfs": "0.8"},
        log_checksum="SMUmY2sg",
    )
    report = build_report(log)
    assert report["album_loudness"] == {
        "integrated_lufs": "-13.9",
        "true_peak_dbfs": "0.8",
    }
    assert report["log_checksum"] == "SMUmY2sg"
    assert report["tracks"][0]["replaygain"] == {"REPLAYGAIN_TRACK_GAIN": "-4.10 dB"}


def test_report_loudness_and_checksum_absent_when_empty() -> None:
    report = build_report(_sample_log())
    assert report["album_loudness"] is None
    assert report["log_checksum"] is None


def test_session_log_is_embedded_in_the_json_not_a_sidecar(tmp_path: Path) -> None:
    # The per-album session log lives INSIDE the JSON (debug.lines), and there is
    # NO standalone .platterpus.log sidecar (maintainer's call, 2026-07-01).
    log_file = tmp_path / "Album.log"
    log_file.write_text("(human log)")
    debug = build_debug_log(["line one", "line two"], truncated=False)
    out = write_report(_sample_log(), log_file, debug_log=debug)
    report = json.loads(out.read_text())
    assert report["debug"]["lines"] == ["line one", "line two"]
    # No sidecar written.
    assert not (tmp_path / "Album.platterpus.log").exists()


def test_debug_section_keeps_BOTH_ENDS_when_it_has_to_truncate() -> None:
    """A truncated embedded log keeps the HEAD **and** the TAIL, counted.

    **THIS TEST'S EXPECTATION CHANGED DELIBERATELY.** It used to assert tail-only
    ("keeps most recent"), matching the old `lines[-N:]`. That drops exactly the
    opening of a rip — the argv we spawned, the drive and disc detection, the
    settings in force — and CLAUDE.md's diagnostic-completeness rule requires both
    ends with a counted elision, because "a silent truncation reads as
    completeness". A failure's explanation is usually last; a rip's *context* is
    always first.

    Note the cap itself is now a runaway backstop, not a routine limit (the
    maintainer: *"I did tell you to capture more error data than you think you
    need"*), so reaching it takes a deliberately pathological input.
    """
    from platterpus.rip_report import _MAX_EMBEDDED_LOG_LINES

    lines = [f"line {i}" for i in range(_MAX_EMBEDDED_LOG_LINES + 500)]
    debug = build_debug_log(lines)
    assert debug["truncated"] is True
    # BOTH ends survive.
    assert debug["lines"][0] == lines[0], "the head was dropped"
    assert debug["lines"][-1] == lines[-1], "the tail was dropped"
    # And the gap is MARKED and COUNTED, not silently joined.
    markers = [line for line in debug["lines"] if "elided" in line]
    assert len(markers) == 1, f"expected exactly one elision marker, got {markers}"
    assert "500" in markers[0] or "50" in markers[0], (
        f"the elision marker does not state how many lines went missing: {markers[0]!r}"
    )


def test_ctdb_section_serialized_when_present() -> None:
    result = CtdbVerifyResult(
        Verdict.MATCH,
        confidence=8,
        our_crc=0x22B9924D,
        matched_crc=0x22B9924D,
        message="verified against CTDB (confidence 8)",
        crc_validated=False,
    )
    report = build_report(_sample_log(), ctdb_result=result)
    assert report["ctdb"]["verdict"] == "match"
    assert report["ctdb"]["confidence"] == 8
    # An unvalidated match is honestly NOT trustworthy yet (KDD-16).
    assert report["ctdb"]["trustworthy"] is False
    # CRCs are auditable (hex, matching the per-track AccurateRip CRC style).
    assert report["ctdb"]["our_crc"] == "22B9924D"
    assert report["ctdb"]["matched_crc"] == "22B9924D"
    assert "confidence 8" in report["ctdb"]["message"]
    # Absent CTDB → null section.
    assert build_report(_sample_log())["ctdb"] is None


def test_ctdb_section_carries_db_crcs_for_offline_diagnosis() -> None:
    # v8: a no_match report is self-diagnosing — it carries the DB's expected
    # CRC(s) + entry_count alongside our_crc, so a reader (or the KDD-16
    # calibration) sees exactly what we computed vs what CTDB expected without a
    # second live lookup. Mirrors the real-disc Police no_match.
    result = CtdbVerifyResult(
        Verdict.NO_MATCH,
        confidence=1347,
        our_crc=0x9C4045CE,
        db_crcs=(0xDEADBEEF, 0x12345678),
    )
    ctdb = build_report(_sample_log(), ctdb_result=result)["ctdb"]
    assert ctdb["our_crc"] == "9C4045CE"
    assert ctdb["matched_crc"] is None
    assert ctdb["entry_count"] == 2
    assert ctdb["db_crcs"] == ["DEADBEEF", "12345678"]


def test_rewrite_adds_ctdb_section_to_same_file(tmp_path: Path) -> None:
    # Mirrors the GUI: write the report at rip-finish (no CTDB), then re-write
    # the SAME file once the async CTDB verify lands. The final file carries it.
    log_file = tmp_path / "Album.log"
    log_file.write_text("(human log)")
    out = write_report(_sample_log(), log_file)
    assert json.loads(out.read_text())["ctdb"] is None

    result = CtdbVerifyResult(Verdict.MATCH, confidence=8)
    again = write_report(_sample_log(), log_file, ctdb_result=result)
    assert again == out  # same path, overwritten
    assert json.loads(out.read_text())["ctdb"]["verdict"] == "match"


def test_report_is_valid_json_roundtrip() -> None:
    text = report_to_json(build_report(_sample_log()))
    parsed = json.loads(text)
    assert parsed["tracks"][0]["copy_crc"] == "B0D122E7"
    assert text.endswith("\n")


def test_build_never_raises_on_empty_or_garbage() -> None:
    assert build_report(RipLog())["schema_version"] == REPORT_SCHEMA_VERSION
    assert (
        build_report(object())["schema_version"] == REPORT_SCHEMA_VERSION
    )  # any shape


def test_build_returns_minimal_envelope_if_internals_raise(monkeypatch) -> None:
    # Force the inner build to blow up; the report must still come back as a
    # valid minimal envelope, never propagate the error into the rip path.
    import platterpus.rip_report as mod

    def boom(*_a, **_k):
        raise RuntimeError("simulated")

    monkeypatch.setattr(mod, "_build", boom)
    report = build_report(_sample_log())
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["error"] == "report could not be built"


def test_write_report_returns_none_on_oserror(tmp_path: Path) -> None:
    # Parent dir doesn't exist → OSError → returns None (best-effort, no raise).
    missing = tmp_path / "nope" / "Album.log"
    assert write_report(_sample_log(), missing) is None


def test_write_report_vanished_folder_logs_quietly_no_traceback(
    tmp_path: Path, caplog
) -> None:
    """A cancelled/cleaned rip whose album folder is gone must NOT dump a
    FileNotFoundError traceback at WARNING (that reads like a crash — a real
    user's log showed exactly this). It's a benign, expected case: log a concise
    INFO and move on. Regression for the uploaded Roots cancel log."""
    import logging

    missing = tmp_path / "gone" / "Album.log"  # parent "gone/" never created
    with caplog.at_level(logging.INFO, logger="platterpus.rip_report"):
        assert write_report(_sample_log(), missing) is None
    # No WARNING and no traceback for the benign vanished-folder case…
    assert not any(r.levelno >= logging.WARNING for r in caplog.records)
    assert not any(r.exc_info for r in caplog.records)
    # …but it IS noted (so the skip is visible), naming the missing folder.
    assert any(
        "no longer exists" in r.getMessage() and "gone" in r.getMessage()
        for r in caplog.records
    )


def test_write_report_writes_beside_the_log(tmp_path: Path) -> None:
    log_file = tmp_path / "Album.log"
    log_file.write_text("(human log)")
    out = write_report(_sample_log(), log_file)
    assert out == report_path_for(log_file) == tmp_path / "Album.platterpus.json"
    assert out.is_file()
    assert json.loads(out.read_text())["generator"]["name"] == "platterpus"


def test_write_report_is_atomic_no_temp_left_behind(tmp_path: Path) -> None:
    # Crash-safety (it.12): the atomic temp+rename must not leave a .tmp sibling
    # behind, and the written JSON must be complete (parseable).
    log_file = tmp_path / "Album.log"
    log_file.write_text("(human log)")
    out = write_report(_sample_log(), log_file)
    assert out is not None
    assert not out.with_name(out.name + ".tmp").exists()
    json.loads(out.read_text())  # complete, parseable — never a torn write


def test_write_report_overwrite_stays_atomic(tmp_path: Path) -> None:
    # The report is re-written as each async check finishes; each overwrite is
    # atomic and leaves no temp.
    log_file = tmp_path / "Album.log"
    log_file.write_text("(human log)")
    write_report(_sample_log(), log_file)
    out = write_report(
        _sample_log(), log_file, ctdb_result=CtdbVerifyResult(Verdict.NO_MATCH)
    )
    assert out is not None and out.is_file()
    assert not out.with_name(out.name + ".tmp").exists()


# --- v7 (0.4.10): outcome / settings / disc / environment / issues -------


def test_schema_and_generator_fingerprint() -> None:
    report = build_report(_sample_log())
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    # A source checkout has no _build.py stamp → the "source" sentinel, always
    # present so a consumer never has to handle a missing fingerprint.
    assert report["generator"]["build_fingerprint"] == "source"


def test_outcome_block_default_absent_but_present_when_supplied() -> None:
    # No outcome passed → the key exists (present-or-null contract) but is null.
    assert build_report(_sample_log())["outcome"] is None
    outcome = build_outcome(
        status="failed",
        failure_hint="Track 5 couldn't be read.",
        auto_unknown_retry_fired=True,
        auto_unknown_retry_reason="ripper could not reach MusicBrainz",
    )
    report = build_report(_sample_log(), outcome=outcome)
    assert report["outcome"]["status"] == "failed"
    assert report["outcome"]["failure_hint"] == "Track 5 couldn't be read."
    assert report["outcome"]["auto_unknown_retry"] == {
        "fired": True,
        "reason": "ripper could not reach MusicBrainz",
    }


def test_settings_block_records_effective_read_offset() -> None:
    settings = build_settings(_FakeConfig())
    report = build_report(_sample_log(), settings=settings)
    s = report["settings"]
    assert s["output_format"] == "flac"
    assert s["secure_rerip_dynamic"] is True and s["secure_rerip_matches"] == 2
    # The offset triple disambiguates "0 configured" from "configured but off".
    assert s["read_offset"] == {"configured": 667, "applied": True, "effective": 667}
    # MP3-only field omitted when the format isn't MP3.
    assert "mp3_vbr_quality" not in s


def test_settings_offset_effective_zero_when_not_applied() -> None:
    class Cfg(_FakeConfig):
        override_read_offset = False

    s = build_settings(Cfg())
    # Configured 667 but NOT applied → effective 0 (the case the log hides).
    assert s["read_offset"] == {"configured": 667, "applied": False, "effective": 0}


def test_settings_includes_mp3_quality_only_for_mp3() -> None:
    class Cfg(_FakeConfig):
        output_format = "mp3"
        mp3_vbr_quality = 2

    s = build_settings(Cfg())
    assert s["output_format"] == "mp3" and s["mp3_vbr_quality"] == 2


def test_disc_block_carries_provenance() -> None:
    report = build_report(
        _sample_log(),
        disc={"unknown": False, "musicbrainz_release_id": "release-123"},
    )
    assert report["disc"] == {
        "unknown": False,
        "musicbrainz_release_id": "release-123",
    }


def test_environment_block_defaults_to_live_probe() -> None:
    # Omitted → build_report fills it from build_info (always populated).
    report = build_report(_sample_log())
    env = report["environment"]
    assert env["install_channel"] in {"appimage", "pipx", "source"}
    assert set(env) == {"python", "platform", "pyside6", "install_channel"}


def test_environment_block_accepts_injected_dict() -> None:
    injected = {"python": "3.11.0", "platform": "Linux", "pyside6": "6.9"}
    report = build_report(_sample_log(), environment=injected)
    assert report["environment"] == injected


def test_verification_gates_explain_null_subblocks() -> None:
    gates = build_gates(
        ctdb_enabled=True,
        flac_verify_enabled=True,
        backend_self_verifies=True,  # → not "ran"
        recompress_enabled=False,
        backend_maxes_compression=True,
        transcode_requested=False,
    )
    v = build_report(_sample_log(), gates=gates)["verification"]
    assert v["gates"] == {
        "ctdb": "ran",
        "flac_integrity": "backend self-verifies",
        "recompress": "disabled",
        "derived": "flac-only",
    }


def test_recompress_result_serialized() -> None:
    from platterpus.adapters.flac_recompress import RecompressResult

    report = build_report(
        _sample_log(), recompress_result=RecompressResult(reencoded=14)
    )
    rc = report["verification"]["recompress"]
    assert rc == {
        "ran": True,
        "ok": True,
        "reencoded": 14,
        "failures": [],
        # `None`, not `[]`: this writer had no per-file details to report because
        # nothing failed. `[]` would also be truthful here but indistinguishable
        # from a result that predates the field, which is a different claim.
        "failure_details": None,
        "error": None,
    }


def test_secure_rerip_block_folded_into_read_speed() -> None:
    sr = {
        "mode": "dynamic",
        "engaged": False,
        "disc_in_accuraterip": False,
        "skipped_reason": "disc_not_in_accuraterip",
    }
    report = build_report(_sample_log(), secure_rerip=sr)
    assert report["read_speed"]["secure_rerip"] == sr


def test_cover_art_block_serialized() -> None:
    from dataclasses import dataclass, field

    @dataclass
    class _CoverArtResult:
        mode: str = "embed"
        found: bool = True
        reason: str = "ok"
        embedded_count: int = 14
        saved_as: str = ""
        release_id: str = "rel-1"
        bytes: int = 20345
        format: str = "jpg"
        error: str = ""
        additional_saved: list = field(default_factory=lambda: ["back.jpg"])

    ca = build_report(_sample_log(), cover_art_result=_CoverArtResult())["cover_art"]
    assert ca["found"] is True and ca["reason"] == "ok"
    assert ca["embedded_count"] == 14 and ca["format"] == "jpg"
    # The back/booklet package is recorded too (None when there was none).
    assert ca["additional_saved"] == ["back.jpg"]


def test_log_parse_block_flags_thin_parse() -> None:
    # A real log → ok True.
    assert build_report(_sample_log())["log_parse"]["ok"] is True
    # An empty log (nothing parsed) → ok False, so a thin report is explained.
    assert build_report(RipLog())["log_parse"]["ok"] is False
    # An explicit override is honoured verbatim.
    report = build_report(_sample_log(), log_parse={"ok": False, "note": "degraded"})
    assert report["log_parse"] == {"ok": False, "note": "degraded"}


def _clean_log() -> RipLog:
    """A rip with nothing to flag: verified, and its ripper build identified.

    The **approved banner** is part of "clean" on purpose, read from the product
    constant rather than a literal. A log whose banner carries no build tag cannot
    say which binary produced it, and the report now says so at ``info`` — so a
    fixture with a bare ``"cyanrip 0.9.3"`` is not a clean rip, it is an
    unidentifiable one, and asserting an empty ``issues`` against it would have
    pinned the *absence* of that signal.
    """
    return RipLog(
        log_creator=fork_source.FORK_EXPECTED_BANNER,
        tracks=(
            TrackResult(
                number=1,
                copy_crc="AA",
                accuraterip_v2=AccurateRipResult(
                    version=2, result="accurately ripped", confidence=200
                ),
            ),
        ),
    )


def test_issues_empty_on_a_clean_rip() -> None:
    # All-verified sample would still be "warn" (1 of 2); use a fully-verified one.
    report = build_report(
        _clean_log(),
        outcome=build_outcome(status="success", ripper_exit_code=0),
    )
    assert report["issues"] == []


# --- the eight checks added because each could be true while `issues` was empty ---
#
# Every one of these is a regression test for a real hole: the fact was in the
# report, and the ONE list a triager opens first said "nothing to flag" about it.


def test_issues_flags_a_ripper_build_that_cannot_be_identified() -> None:
    """No build tag → ``not_determined`` at info, never silence and never a pass."""
    log = replace(_clean_log(), log_creator="cyanrip 0.9.3")
    report = build_report(
        log, outcome=build_outcome(status="success", ripper_exit_code=0)
    )
    codes = {i["code"]: i["severity"] for i in report["issues"]}
    assert codes["ripper_handshake_not_determined"] == "info"


def test_issues_flags_an_unapproved_ripper_build() -> None:
    """A build tag we recognise as NOT the approved pin is a warning, not silence."""
    log = replace(
        _clean_log(), log_creator="cyanrip 0.9.4-rc1 (platterpus-fork-gdeadbee)"
    )
    report = build_report(
        log, outcome=build_outcome(status="success", ripper_exit_code=0)
    )
    codes = {i["code"]: i["severity"] for i in report["issues"]}
    assert codes["ripper_handshake_unapproved"] == "warning"


def test_issues_flags_a_success_whose_ripper_was_never_reaped() -> None:
    """`None` exit code on a success: 'success' rests on the log alone. Say so."""
    report = build_report(_clean_log(), outcome=build_outcome(status="success"))
    codes = {i["code"]: i["severity"] for i in report["issues"]}
    assert codes["ripper_exit_unknown"] == "warning"


def test_issues_flags_a_success_with_a_nonzero_ripper_exit() -> None:
    report = build_report(
        _clean_log(), outcome=build_outcome(status="success", ripper_exit_code=3)
    )
    issue = next(
        i for i in report["issues"] if i["code"] == "ripper_nonzero_exit_on_success"
    )
    assert issue["severity"] == "warning"
    assert "3" in issue["message"]


def test_issues_flags_a_recompress_failure() -> None:
    """The step that REWRITES archival masters was not even a parameter before."""
    from platterpus.adapters.flac_recompress import RecompressResult

    report = build_report(
        _clean_log(),
        outcome=build_outcome(status="success", ripper_exit_code=0),
        recompress_result=RecompressResult(reencoded=1, failures=(Path("bad.flac"),)),
    )
    codes = {i["code"]: i["severity"] for i in report["issues"]}
    # `error`, not `warning`: re-compression REWRITES the archival master in place,
    # so a failure means a file we were asked to improve may be in an unknown state.
    assert codes["recompress_failed"] == "error"


def test_issues_flags_a_degraded_log_parse() -> None:
    report = build_report(
        _clean_log(),
        outcome=build_outcome(status="success", ripper_exit_code=0),
        log_parse={"ok": False, "note": "non-UTF-8 byte forced errors=replace"},
    )
    issue = next(i for i in report["issues"] if i["code"] == "ripper_log_unparsed")
    assert "non-UTF-8" in issue["message"]


def test_issues_flags_a_track_count_that_disagrees_with_the_disc() -> None:
    report = build_report(
        _clean_log(),
        outcome=build_outcome(status="success", ripper_exit_code=0),
        disc_track_total=14,
    )
    issue = next(i for i in report["issues"] if i["code"] == "track_count_mismatch")
    assert "14" in issue["message"] and "1" in issue["message"]


def test_issues_flags_an_artifact_that_could_not_be_embedded() -> None:
    report = build_report(
        _clean_log(),
        outcome=build_outcome(status="success", ripper_exit_code=0),
        artifacts={
            "note": "n/a",
            "rip_log": {"path": "/x/a.log", "error": "Permission denied"},
        },
    )
    issue = next(i for i in report["issues"] if i["code"] == "artifact_unavailable")
    assert "Permission denied" in issue["message"]


def test_issues_flags_a_dependency_below_its_minimum() -> None:
    report = build_report(
        _clean_log(),
        outcome=build_outcome(status="success", ripper_exit_code=0),
        environment={
            "dependencies": {
                "flac": {"present": True, "version": "1.2.1", "min_version_met": False}
            }
        },
    )
    issue = next(i for i in report["issues"] if i["code"] == "dependency_below_minimum")
    assert "1.2.1" in issue["message"]


def test_issues_consolidates_failures_with_severity() -> None:
    from platterpus.adapters.derived_verify import DerivedVerifyResult
    from platterpus.adapters.flac_verify import FlacVerifyResult

    report = build_report(
        _sample_log(),  # 1 of 2 verified → not_bit_perfect (warning)
        outcome=build_outcome(status="failed", failure_hint="disc unreadable"),
        flac_verify_result=FlacVerifyResult(checked=2, failures=(Path("bad.flac"),)),
        derived_verify_result=DerivedVerifyResult(
            fmt="wav", lossless=True, mismatches=(Path("bad.wav"),)
        ),
    )
    codes = {i["code"]: i["severity"] for i in report["issues"]}
    assert codes["rip_failed"] == "error"
    assert codes["flac_integrity_failed"] == "error"
    assert codes["derived_mismatch"] == "error"
    assert codes["not_bit_perfect"] == "warning"
    # The failure hint is surfaced in the consolidated list.
    assert any(i["message"] == "disc unreadable" for i in report["issues"])


def test_issues_flags_read_instability_and_cover_art_and_transcode() -> None:
    from dataclasses import dataclass

    from platterpus.adapters.transcode import TranscodeResult

    @dataclass
    class _CoverArtResult:
        mode: str = "embed"
        found: bool = False
        reason: str = "404"

    report = build_report(
        _sample_log(),
        read_speed={"unresolved": True, "unstable_tracks": [5]},
        transcode_result=TranscodeResult(error="ffmpeg missing"),
        cover_art_result=_CoverArtResult(),
    )
    codes = {i["code"] for i in report["issues"]}
    assert {"read_unstable", "transcode_failed", "cover_art_missing"} <= codes


# --- CLI: scripts/rip_report.py -------------------------------------------


def _load_cli():
    spec = importlib.util.spec_from_file_location(
        "rip_report_cli", _REPO_ROOT / "scripts" / "rip_report.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cli_emits_json_for_committed_cyanrip_log(capsys) -> None:
    cli = _load_cli()
    rc = cli.main([str(_CYANRIP_REFERENCE)])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert parsed["generator"]["name"] == "platterpus"
    assert len(parsed["tracks"]) == 14  # the Police disc


def test_cli_missing_file_returns_2(tmp_path: Path) -> None:
    cli = _load_cli()
    assert cli.main([str(tmp_path / "nope.log")]) == 2


def test_cli_refuses_an_eac_log(tmp_path: Path, capsys) -> None:
    # An EAC log fed here would otherwise parse to an empty whipper RipLog and
    # silently emit a 0-track report with exit 0 — refuse with a clear message.
    cli = _load_cli()
    eac = tmp_path / "eac.log"
    eac.write_text(
        "Exact Audio Copy V1.8\n\nTrack  1\n\n     Copy CRC B0D122E7\n",
        encoding="utf-8",
    )
    rc = cli.main([str(eac)])
    assert rc == 2
    assert "EAC log" in capsys.readouterr().err


# --- v9 (0.4.24): disc IDs, secure_rerip_converged, heavy_reread issue -------


def test_schema_version_is_24() -> None:
    # v23 made `settings.rip_goal` DERIVED from the six preset fields instead of read
    # back from `config.rip_goal`, and added `settings.rip_goal_stored`, present only
    # when the stored label disagreed. `rip_goal` is a label for a bundle of fields and
    # nothing kept the two in step: a hand-edited config.toml, a field changed outside
    # `apply_preset`, or a config written before the field existed all leave a stale
    # label behind. The Settings dialog had always re-derived, so the SCREEN was right
    # while the permanent record could name a goal the settings never matched. Both
    # values are kept when they differ, because the disagreement is itself the finding.
    #
    # v22 added `rip.ripper_release_id` — the release id the ripper RESOLVED AND USED,
    # off its own header — plus the `issues` comparison against the id we sent. It had
    # been in the ignored table with a recorded reason: "our own input reflected;
    # `Invoked as:` is a better witness for an argv disagreement." True of the argv
    # question, and it did not cover a different one: the whole tag set goes as ONE
    # colon-delimited `-a` blob, so what the ripper RECEIVED and what it PARSED are
    # separate claims and only the first was recorded. The comparison is what makes
    # either number more than a record, and it checks `-N` really suppressed the
    # ripper's own lookup (Critical rule #5) at the artifact rather than on trust.
    #
    # v21 added `eta_trace.samples[].state` and `.reread_pass`. Only the branch that
    # made a FRESH rate measurement used to record a sample, so the trace went silent
    # on the hold and stall paths: the b8 rig trace has a 541-second and a 400-second
    # hole, both landing exactly on the minutes the estimator was misbehaving, which is
    # how its peak reading became un-analysable from the artifact that was supposed to
    # explain it. Every branch records now, and `state` is what keeps that honest — a
    # re-shown older estimate is labelled `held_*`, a pinned album bar during a secure
    # re-read is `rereading`, and only `computed` is a measurement.
    #
    # v19 added `rip.read_stalls` — the fork's stall-watchdog verdict, verbatim. They
    # added that line at their own initiative FOR us, and we were not reading it while
    # answering a design question about whether we wanted it per-track (round 7 lap 9
    # J3 versus lap 13). `null` on stock cyanrip, which never prints it: a third state,
    # because "no stalls measured" and "stalls not measured" are different claims.
    #
    # v18 added `ripper_log_verification` — the RIPPER's verdict on its OWN log, run
    # with its own `--verify-log` and its own checksum. The one block here whose
    # verdict is not ours, which is the entire reason it exists: the cyanrip fork
    # found that our `self_check`'s log-integrity row verified a file we wrote
    # against a checksum we computed, and reported it fine on a rip that shipped a
    # cyanrip log cyanrip itself would reject (round 7 lap 10, H1/J3).
    #
    # v17 added the two FORK-ONLY provenance rows the ripper prints about ITSELF:
    # `rip.ripper_handshake_note` (its compiled-in statement of which handshake round
    # it was built from — a build from an open-round tree says so permanently) and
    # `rip.ripper_consumer` (who it was told the caller was, which its own log calls
    # unverified). The first is a second, INDEPENDENT witness beside
    # `ripper_handshake_approval`, which is *our* verdict on the banner: when the two
    # disagree, the disagreement is the finding.
    #
    # v16 added the `diagnostics` block: every problem the rip noticed, in ONE place,
    # so "did anything go wrong and what?" has a single answer instead of requiring a
    # reader to already know about `outcome.failure_hint`, `log_parse.note`,
    # `ctdb.error`, the per-track `issues` and the verification blocks. (v15 added the
    # rip-time handshake-approval block.)
    #
    # v20 added `partially_accurate_reported`: the ripper's own offset-variant fraction,
    # verbatim, beside our sentence about it. The fraction's DENOMINATOR changed meaning
    # between fork builds (`1/1` up to `e61e75a`, `1/14` from `f5e11ba`, same disc, same
    # track), so our sentence is derived from the per-track results and this field keeps
    # what the binary actually printed — two logs of one disc from two builds are not
    # comparable without it.
    #
    # v24 added `audio_md5`: relpath -> MD5 of the DECODED audio, read from each
    # FLAC's own STREAMINFO. Distinct from `checksums`, which digests the
    # container and is therefore invalidated by a legitimate retag — so a
    # retagged album used to look as suspect as a corrupted one. Its own key
    # rather than folded into `checksums`, because a SHA256 mismatch after a
    # retag is expected while an audio-MD5 mismatch never is, and a reader must
    # not be able to confuse the two.
    assert REPORT_SCHEMA_VERSION == 24


def _issue_codes(report: dict) -> set[str]:
    return {str(i.get("code")) for i in report.get("issues") or []}


def test_the_two_provenance_witnesses_are_actually_compared() -> None:
    """We published the claim; nothing in the code was making it.

    Round 7 lap 10 §C told the fork *"when the two disagree, the disagreement is the
    finding"* about `ripper_handshake_approval` (our verdict on the banner) versus
    `ripper_handshake_note` (their build system's compiled-in statement). The note
    was parsed at v17, stored, and read by nothing — the same defect the approval
    block itself had until the fork found it.

    Driven through `_issues` at the seam it actually runs at, with the note taken
    from the committed rig log rather than invented.
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log
    from platterpus.rip_report import _issues

    log = (
        Path(__file__).resolve().parent.parent
        / "output_reference"
        / "cyanrip_fork_flac"
        / "cyanrip_fork_police_classics.log"
    )
    assert log.is_file(), "no committed fork log — this test would prove nothing"
    note = parse_cyanrip_log(
        log.read_text(encoding="utf-8", errors="replace")
    ).handshake_note
    assert note, "the committed log carries no Handshake: line"

    # Approved + a build that says it is NOT a release: an ERROR, because one of two
    # independent witnesses must be wrong.
    conflicting = _issues(
        outcome=None,
        verdict_level="ok",
        ctdb=None,
        flac_integrity=None,
        derived=None,
        transcode=None,
        cover_art=None,
        read_speed=None,
        rip={
            "ripper_handshake_approval": "approved",
            "ripper_handshake_note": note,
        },
    )
    disagreements = [
        i for i in conflicting if i["code"] == "ripper_provenance_witnesses_disagree"
    ]
    assert disagreements, f"no disagreement raised; got {_codes(conflicting)}"
    assert disagreements[0]["severity"] == "error"
    assert note in disagreements[0]["message"]

    # The REAL artifact's state — unapproved, note agreeing — must be silent, or
    # every deliberate test-pin rip carries a finding and the entry gets ignored.
    agreeing = _issues(
        outcome=None,
        verdict_level="ok",
        ctdb=None,
        flac_integrity=None,
        derived=None,
        transcode=None,
        cover_art=None,
        read_speed=None,
        rip={
            "ripper_handshake_approval": "unapproved",
            "ripper_handshake_note": note,
        },
    )
    assert "ripper_provenance_witnesses_disagree" not in _codes(agreeing)


def _codes(issues: list[dict]) -> set[str]:
    return {str(i.get("code")) for i in issues}


def test_the_forks_own_handshake_and_consumer_lines_reach_the_json() -> None:
    """Read off the REAL committed fork log, not a hand-written fixture.

    The parser ignored both lines until a real rig artifact was read (2026-08-04) and
    the top-level-line sweep reported 12 unrecognised rows — two of which were these.
    They had been on the TASKS list as "currently unrecognised"; the artifact is what
    made them implementable, because a fixture would have been my guess at their
    wording.
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    fork_log = (
        Path(__file__).resolve().parents[1]
        / "output_reference"
        / "cyanrip_fork_flac"
        / "cyanrip_fork_police_classics.log"
    )
    report = build_report(parse_cyanrip_log(fork_log.read_text(encoding="utf-8")))
    rip = report["rip"]

    # VERBATIM. The clause that matters most is a whole phrase, not a field.
    assert rip["ripper_handshake_note"] == (
        "round 7 lap 7 OPEN, verdict HOLD -- NOT a released build"
    )
    assert "NOT a released build" in rip["ripper_handshake_note"]
    assert rip["ripper_consumer"] == "not identified (no --consumer given)"


def test_a_stock_log_leaves_both_new_fork_rows_null() -> None:
    """Absent means absent. AppImage users run stock cyanrip, which never prints
    these, and one build has to be correct against both."""
    report = build_report(_sample_log())
    assert report["rip"]["ripper_handshake_note"] is None
    assert report["rip"]["ripper_consumer"] is None


def test_the_rippers_own_completion_verdict_reaches_the_json() -> None:
    """Parsed since v0.6.1 and, until the embedded self-check ran, never
    serialized — so the report said "completion footer absent" about a log that
    plainly had one. Caught by a *consumer* of the field, which is the argument
    for having one."""
    report = build_report(
        RipLog(
            rip_completed=False,
            rip_completed_tracks=2,
            rip_completed_total=14,
            rip_completed_reason="interrupted by user",
            invoked_as="/usr/bin/cyanrip -d /dev/sr0 -N",
        )
    )
    assert report["rip"]["rip_completed"] is False
    assert report["rip"]["rip_completed_tracks"] == 2
    assert report["rip"]["rip_completed_total"] == 14
    assert report["rip"]["rip_completed_reason"] == "interrupted by user"
    assert report["rip"]["invoked_as"] == "/usr/bin/cyanrip -d /dev/sr0 -N"


def test_an_absent_footer_serializes_as_null_not_false() -> None:
    """Tri-state at the serialization boundary, where it is easiest to lose."""
    report = build_report(RipLog())
    assert report["rip"]["rip_completed"] is None


# --- v13: which ripper binary, and how the process actually ended ------------


def test_the_report_says_which_cyanrip_binary_ripped_the_disc() -> None:
    """The fork emits rows stock cyanrip does not, so two logs of one disc are
    not interchangeable evidence — and the version number cannot tell them apart
    because the fork tracks upstream versions."""
    fork = build_report(
        RipLog(log_creator="cyanrip 0.9.4-rc1", ripper_build="platterpus-fork")
    )
    assert fork["rip"]["ripper_is_platterpus_fork"] is True
    assert fork["rip"]["ripper_identity"] == "fork"

    stock = build_report(RipLog(log_creator="cyanrip 0.9.3.1", ripper_build="release"))
    assert stock["rip"]["ripper_is_platterpus_fork"] is False
    assert stock["rip"]["ripper_identity"] == "stock"


def test_an_unidentifiable_build_is_null_not_false() -> None:
    """`false` would assert an unmodified upstream binary we have no evidence
    for. `null` is "not determined" — the same distinction this codebase has now
    got wrong three times elsewhere."""
    for build in ("", "g1a2b3c4", "fedora"):
        report = build_report(RipLog(log_creator="cyanrip 0.9.3.1", ripper_build=build))
        assert report["rip"]["ripper_is_platterpus_fork"] is None, build
        assert report["rip"]["ripper_identity"] == "unknown", build
        assert report["rip"]["ripper_identity_detail"]


def test_rip_block_carries_disc_ids() -> None:
    log = RipLog(disc_id="MBDISC", cddb_id="CDDB01", tracks=(TrackResult(1),))
    report = build_report(log)
    assert report["rip"]["musicbrainz_disc_id"] == "MBDISC"
    assert report["rip"]["cddb_id"] == "CDDB01"


def test_rip_block_disc_ids_null_when_absent() -> None:
    report = build_report(RipLog(tracks=(TrackResult(1),)))
    assert report["rip"]["musicbrainz_disc_id"] is None
    assert report["rip"]["cddb_id"] is None


def test_track_serializes_secure_rerip_converged() -> None:
    log = RipLog(
        tracks=(
            TrackResult(1, copy_crc="AA", secure_rerip_converged=True),
            TrackResult(2, copy_crc="BB", secure_rerip_converged=False),
            TrackResult(3, copy_crc="CC"),
        )
    )
    report = build_report(log)
    assert report["tracks"][0]["secure_rerip_converged"] is True
    assert report["tracks"][1]["secure_rerip_converged"] is False
    assert report["tracks"][2]["secure_rerip_converged"] is None


def test_heavy_reread_issue_fires_on_non_convergence() -> None:
    # track 2 never converged; track 3 needed 4 passes → both flagged.
    log = RipLog(
        tracks=(
            TrackResult(1, copy_crc="AA", rip_count=1),
            TrackResult(2, copy_crc="BB", secure_rerip_converged=False),
            TrackResult(3, copy_crc="CC", rip_count=4),
        )
    )
    report = build_report(log)
    codes = [i["code"] for i in report["issues"]]
    assert "heavy_reread" in codes
    msg = next(i for i in report["issues"] if i["code"] == "heavy_reread")["message"]
    assert "2" in msg and "3" in msg


def test_no_heavy_reread_issue_on_clean_rip() -> None:
    log = RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=1),))
    report = build_report(log)
    assert "heavy_reread" not in [i["code"] for i in report["issues"]]


def test_heavy_reread_threshold_boundary() -> None:
    # Boundary of HEAVY_REREAD_THRESHOLD (3): 2 passes is benign (no flag),
    # 3 passes flags. A one-character off-by-one here would slip the whole suite.
    from platterpus.parsers.rip_log import tracks_needing_heavy_reread

    two = RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=2),))
    three = RipLog(tracks=(TrackResult(1, copy_crc="AA", rip_count=3),))
    assert tracks_needing_heavy_reread(two) == []
    assert tracks_needing_heavy_reread(three) == [1]
    # And it surfaces in the report issue only at the threshold.
    assert "heavy_reread" not in [i["code"] for i in build_report(two)["issues"]]
    assert "heavy_reread" in [i["code"] for i in build_report(three)["issues"]]


# --- v10 (0.5.20): per-track facts the parser read and the report dropped ----


def test_schema_version_is_10_and_the_v10_keys_are_present() -> None:
    """The keys exist even on a log that reports none of them.

    A consumer distinguishes "the ripper didn't say" from "this build doesn't
    record it" only if the key is always present and `null` when unmeasured. The
    whole point of adding these is that a reader can *ask*.
    """
    track = build_report(_sample_log())["tracks"][0]
    for key in (
        "extraction_elapsed_seconds",
        "appended_silence_frames",
        "start_sector",
        "end_sector",
        "pregap_sectors",
    ):
        assert key in track, f"v10 key {key!r} missing from the track block"
        assert track[key] is None, f"{key!r} should be null when unreported"


def test_the_committed_cyanrip_log_puts_its_real_geometry_in_the_report() -> None:
    """Asserted against the real reference rip, not a fixture I wrote.

    This is the check that would have caught the omission. `appended_silence_frames`
    is the one that matters: cyanrip 0.9.3 prints `Appended: 2 frames of silence`
    on track 14 of this very disc, meaning that track's final two frames are
    **fabricated silence rather than disc audio** — the most archival-relevant
    per-track fact in the log. It reached the EAC-layout log and never the JSON,
    so the machine record of an archival rip was quietly less complete than the
    human-readable one beside it. A fabricated fixture could not have exposed
    that, because I would have written the fixture from the same wrong belief.

    The sector geometry is asserted on track 1, whose absolute numbers are in the
    committed log and are what EAC's "TOC of the extracted CD" is derived from.
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    rip_log = parse_cyanrip_log(_CYANRIP_REFERENCE.read_text(encoding="utf-8"))
    report = build_report(rip_log)
    tracks = report["tracks"]
    assert len(tracks) == 14

    # Track 14 is the one with appended silence — the last track, overread off.
    last = tracks[13]
    assert last["appended_silence_frames"] == 2, (
        "cyanrip logged 'Appended: 2 frames of silence' for track 14 of this "
        "disc; the report must say so, because those frames are not disc audio"
    )
    # And it is genuinely per-track: no other track on this disc has any.
    assert [t["appended_silence_frames"] for t in tracks[:13]] == [None] * 13

    first = tracks[0]
    assert first["start_sector"] == 0
    assert first["end_sector"] == 14486
    assert first["pregap_sectors"] == 0, "'Pregap LSN: none' is measured-zero"

    # Fork-only: 0.9.3 prints no elapsed, so every track must report null rather
    # than a zero that would read as "instant".
    assert [t["extraction_elapsed_seconds"] for t in tracks] == [None] * 14


# --- v11 (0.5.21): the pre-gap length/position split -------------------------


def test_pregap_length_and_position_are_separate_keys() -> None:
    """v10 shipped cyanrip's absolute `Pregap LSN` under the name `pregap_sectors`.

    They are different quantities and the report now says so. The length is
    derived; the position is what the ripper printed.
    """
    track = build_report(_sample_log())["tracks"][0]
    assert "pregap_sectors" in track and "pregap_start_lsn" in track
    assert track["pregap_sectors"] is None
    assert track["pregap_start_lsn"] is None


# --- multi-pass rips: two facts a single-pass report cannot express ------------


def test_outcome_records_the_first_pass_argv_separately() -> None:
    """`ripper_argv` is the LAST invocation — right for "re-run what finished".
    But the archival log's `Invoked as:` line is written by the FIRST pass, so a
    cross-check between them needs the first pass recorded too. Without it, a
    dynamic secure-rerip's `-Z`/`-l` read as arguments injected in transit."""
    first = ["cyanrip", "-d", "/dev/sr0", "-N"]
    last = [*first, "-Z", "2", "-l", "3,5"]
    out = build_outcome(
        status="success", ripper_argv=last, ripper_argv_first_pass=first
    )
    assert out["ripper_argv"] == last
    assert out["ripper_argv_first_pass"] == first
    # The display string stays the one you can re-run — the last invocation.
    assert out["ripper_command_display"].endswith("-l 3,5")


def test_a_single_pass_rip_leaves_the_first_pass_field_null() -> None:
    """Null, not a copy of `ripper_argv`: "one pass" and "the first of several"
    are different facts, and a consumer must be able to tell them apart."""
    out = build_outcome(status="success", ripper_argv=["cyanrip", "-N"])
    assert out["ripper_argv"] == ["cyanrip", "-N"]
    assert out["ripper_argv_first_pass"] is None


def test_failure_hint_is_none_on_a_successful_rip() -> None:
    """A field named `failure_hint` populated on a rip whose status is "success"
    and whose exit code is 0 tells every consumer — and `--audit-rips` — that
    this is why the rip failed. It did not fail.

    The real case: a dynamic secure-rerip that did not converge on one track makes
    the ripper print `Done; (no matches found, but hit repeat limit of 5)`, which
    was scraped into `failure_hint` on an otherwise clean 14-track rip. The fact
    belongs in the read-stability line, not here.
    """
    out = build_outcome(status="success", failure_hint=None, ripper_exit_code=0)
    assert out["failure_hint"] is None
    # And the field still works where it means something.
    failed = build_outcome(status="failed", failure_hint="Offset is unset!")
    assert failed["failure_hint"] == "Offset is unset!"


def test_the_finish_handler_gates_the_hint_on_a_non_success_status() -> None:
    """The gate lives in the caller, so assert it there.

    `build_outcome` cannot decide this — it stores what it is handed. The bug was
    the finish handler handing it the worker's scraped hint unconditionally, so a
    successful rip carried a failure diagnosis. Read from the source because the
    handler needs a live MainWindow and a rip to exercise; refactoring an event
    handler to suit a test is the wrong trade (the harness adapts to the product).
    """
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "platterpus"
        / "ui"
        / "main_window_rip.py"
    ).read_text(encoding="utf-8")
    start = source.index("failure_hint=(")
    window = source[start : start + 600]
    assert 'if _status != "success"' in window, (
        "the finish handler no longer gates failure_hint on a non-success status — "
        "a successful rip will carry a failure diagnosis again"
    )


# --- v22: the release id the ripper RESOLVED, and the comparison ------------------
#
# This line sat in the parser's ignored table with a recorded reason — "our own input
# reflected; `Invoked as:` is a better witness for an argv disagreement" — which was
# true of the argv question and quietly answered a different one. We hand the whole
# tag set as ONE colon-delimited `-a` blob, so what the ripper RECEIVED and what it
# PARSED OUT are separate claims, and only the first was recorded. The album title on
# the reference disc carries `∶` (U+2236) precisely because a real colon breaks that
# syntax, so the failure mode is live, not theoretical.


def _log_with_ripper_release_id(value: str) -> RipLog:
    log = _sample_log()
    return replace(log, release_id=value)


def test_the_ripper_resolved_release_id_is_recorded() -> None:
    report = build_report(_log_with_ripper_release_id("d14a7546-815b-43c6"))
    assert report["rip"]["ripper_release_id"] == "d14a7546-815b-43c6"


def test_an_absent_ripper_release_id_is_null_not_a_finding() -> None:
    """An unknown-disc rip sends no release id, a whipper log has no such line, and
    neither does a build older than this row. All three are "no claim" — the report
    must not manufacture a disagreement out of a field nobody filled."""
    report = build_report(
        _sample_log(), disc={"unknown": True, "musicbrainz_release_id": None}
    )
    assert report["rip"]["ripper_release_id"] is None
    assert not {
        "ripper_release_id_mismatch",
        "ripper_release_id_unexpected",
    } & _issue_codes(report)


def test_matching_release_ids_raise_nothing() -> None:
    """The ALLOW case first: a check that can only ever complain is a wall, and it
    would pass every negative case below."""
    report = build_report(
        _log_with_ripper_release_id("release-123"),
        disc={"unknown": False, "musicbrainz_release_id": "release-123"},
    )
    assert report["rip"]["ripper_release_id"] == "release-123"
    assert not {
        "ripper_release_id_mismatch",
        "ripper_release_id_unexpected",
    } & _issue_codes(report)


def test_a_release_id_the_ripper_did_not_get_from_us_is_flagged() -> None:
    """`-N` is supposed to stop cyanrip doing its own MusicBrainz lookup (Critical
    rule #5). If it reports a release id on a rip that sent none, it looked one up —
    and that is checked against the artifact instead of trusted."""
    report = build_report(
        _log_with_ripper_release_id("looked-this-up-itself"),
        disc={"unknown": True, "musicbrainz_release_id": None},
    )
    assert "ripper_release_id_unexpected" in _issue_codes(report)
    hit = next(
        i for i in report["issues"] if i["code"] == "ripper_release_id_unexpected"
    )
    assert hit["severity"] == "warning"
    assert "looked-this-up-itself" in hit["message"]


def test_a_release_id_disagreement_is_an_error_naming_both() -> None:
    """The case the field exists for: the tags, filenames and cue on disk were
    written from what the RIPPER parsed, so a disagreement means the folder may
    describe a different release than the report does. Both ids are named, because a
    message saying only "mismatch" leaves the reader to go find them."""
    report = build_report(
        _log_with_ripper_release_id("what-the-ripper-used"),
        disc={"unknown": False, "musicbrainz_release_id": "what-we-resolved"},
    )
    assert "ripper_release_id_mismatch" in _issue_codes(report)
    hit = next(i for i in report["issues"] if i["code"] == "ripper_release_id_mismatch")
    assert hit["severity"] == "error"
    assert "what-the-ripper-used" in hit["message"]
    assert "what-we-resolved" in hit["message"]


# --- v23: settings.rip_goal is derived, not the stored label ----------------


def test_settings_rip_goal_is_derived_from_the_fields_not_the_stored_label() -> None:
    """The rig finding of 2026-08-05, pinned.

    `Config()`'s defaults ARE the `fast_verified` preset, so a config carrying
    `rip_goal="custom"` is incoherent: it claims a hand-tuned setup while every
    field matches a shipped preset. The Settings dialog already showed the
    truthful answer (it re-derives); the report was writing the stored string, so
    the rip's permanent record could name a goal its settings never matched.
    """
    from platterpus.config import Config

    settings = build_settings(replace(Config(), rip_goal="custom"))
    assert settings["rip_goal"] == "fast_verified"
    # And the stale label is kept rather than overwritten in silence.
    assert settings["rip_goal_stored"] == "custom"


def test_a_truthful_stored_label_adds_no_extra_field() -> None:
    """No noise in the normal case — absence of the key is the "they agree" signal."""
    from platterpus.config import Config

    settings = build_settings(Config())
    assert settings["rip_goal"] == "fast_verified"
    assert "rip_goal_stored" not in settings


def test_a_hand_tuned_config_derives_custom_and_keeps_the_stale_preset_label() -> None:
    """The other direction, and the one a real config file hits.

    `read_speed_mode="fixed"` is one field away from every shipped preset, so the
    settings ARE custom — while `rip_goal` still holds the default
    `"fast_verified"`, because nothing rewrote it. (The dialog would have: it
    derives on OK. This is the shape of a config written by anything else.) The
    report must name the truthful goal and keep the stale label beside it.
    """
    from platterpus.config import Config

    settings = build_settings(replace(Config(), read_speed_mode="fixed"))
    assert settings["rip_goal"] == "custom"
    assert settings["rip_goal_stored"] == "fast_verified"


def test_a_config_that_cannot_be_classified_falls_back_to_the_stored_label() -> None:
    """`build_settings` takes duck-typed objects and must never raise.

    A stand-in without the six preset fields cannot be classified, and a blank is
    worse than a possibly-stale label, so the stored value is reported and no
    disagreement is claimed.
    """

    class _Partial:
        rip_goal = "portable"

    settings = build_settings(_Partial())
    assert settings["rip_goal"] == "portable"
    assert "rip_goal_stored" not in settings


def test_a_config_with_no_goal_at_all_reports_none() -> None:
    class _Empty:
        pass

    settings = build_settings(_Empty())
    assert settings["rip_goal"] is None
    assert "rip_goal_stored" not in settings


# --- A parameter that is accepted and ignored -------------------------------


def test_write_report_forwards_audio_md5_to_the_document(tmp_path) -> None:
    """The 2026-08-19 rig defect: accepted, then dropped on the floor.

    `write_report` took an `audio_md5` argument and never passed it to
    `build_report`, so EVERY report ever written carried `audio_md5: null` — while
    the caller had the value and the GUI logged reading it. The rig's app log said
    *"1 FLAC audio MD5(s) read"* two seconds before the report that says it has
    none.

    That shape is the worst one available: the call site looks correct, the type
    checker is satisfied, and the only symptom is a null in an archival record
    where null reads as *"not computed"* rather than *"we lost it"*. It survived
    because every existing test drove `build_report` — the pure builder, which
    always handled the field correctly — and nothing drove the wrapper the app
    actually calls.
    """
    from platterpus import rip_report

    target = tmp_path / "album.log"
    target.write_text("stand-in\n", encoding="utf-8")

    rip_report.write_report(
        None,
        target,
        checksums={"01.flac": "sha-aaa"},
        audio_md5={"01.flac": "md5-bbb"},
    )

    written = list(tmp_path.glob("*.platterpus.json"))
    assert written, "write_report produced no document"
    doc = json.loads(written[0].read_text(encoding="utf-8"))
    assert doc["checksums"] == {"01.flac": "sha-aaa"}, "precondition"
    assert doc["audio_md5"] == {"01.flac": "md5-bbb"}, (
        "write_report accepted audio_md5 and did not forward it — the archival "
        "record claims the audio identity was never computed"
    )


def test_no_write_report_parameter_is_silently_dropped() -> None:
    """The sweep, because one dropped parameter means the shape is reachable.

    `write_report` is a wrapper whose whole job is forwarding; a name it accepts
    and never mentions again is, by construction, a value the caller believes was
    recorded and was not. Rather than fix the one instance and trust the next
    reader, every parameter is checked for at least one mention in the body.

    Deliberately a *mention* check, not a data-flow analysis: cheap, and it
    catches the failure mode that actually happened — a name absent from the body
    entirely.

    **Its limit, measured rather than assumed.** Reverting the fix above did NOT
    make this test fail, because the revert left behind a comment that mentions
    `audio_md5`, and a mention is all this looks for. So this is a *net for the
    next one*, not the regression test for this one:
    `test_write_report_forwards_audio_md5_to_the_document` is the authority, and
    it does fail on that revert. Stated plainly because a sweep believed to be
    stronger than it is, is worse than no sweep — it is the "check that passes for
    the wrong reason" this project keeps finding.

    Matched on the bare NAME, not on `name=`. The first version looked for the
    kwarg spelling and flagged `log_file`, which is used positionally
    (`target = report_path_for(log_file)`) — a false positive that would have been
    silenced with an exclusion, and exclusions are where the next real instance
    hides.
    """
    import inspect
    import re as _re

    from platterpus import rip_report

    src = inspect.getsource(rip_report.write_report)
    body = src.partition('"""')[2].partition('"""')[2] or src  # skip the docstring
    params = list(inspect.signature(rip_report.write_report).parameters)
    dropped = [
        name for name in params if not _re.search(rf"\b{_re.escape(name)}\b", body)
    ]
    assert not dropped, (
        "write_report accepts these parameters and never uses them, so a caller "
        f"that supplies one gets silence instead of a record: {dropped}"
    )
