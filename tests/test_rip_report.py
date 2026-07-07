"""Tests for platterpus.rip_report (the machine-readable JSON rip report)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
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


def test_schema_version_is_v8() -> None:
    assert REPORT_SCHEMA_VERSION == 8
    assert build_report(_sample_log())["schema_version"] == 8


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


def test_debug_section_caps_embedded_lines_and_keeps_most_recent() -> None:
    """A marathon session must not bloat the report (or its on-GUI-thread
    re-serialization): the embedded log is capped to the most-recent lines and
    marked truncated; log.txt keeps the full history."""
    from platterpus.rip_report import _MAX_EMBEDDED_LOG_LINES

    lines = [f"line {i}" for i in range(_MAX_EMBEDDED_LOG_LINES + 500)]
    debug = build_debug_log(lines)
    assert len(debug["lines"]) == _MAX_EMBEDDED_LOG_LINES
    assert debug["truncated"] is True
    # The most RECENT lines are kept (closest to the just-finished rip).
    assert debug["lines"][-1] == lines[-1]
    assert debug["lines"][0] == lines[500]


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


def test_v8_schema_and_generator_fingerprint() -> None:
    report = build_report(_sample_log())
    assert report["schema_version"] == 8
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
    from dataclasses import dataclass

    from dataclasses import field

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


def test_issues_empty_on_a_clean_rip() -> None:
    # All-verified sample would still be "warn" (1 of 2); use a fully-verified one.
    log = RipLog(
        log_creator="cyanrip 0.9.3",
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
    report = build_report(log, outcome=build_outcome(status="success"))
    assert report["issues"] == []


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
