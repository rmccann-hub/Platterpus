"""Errors in a read the album replaced, on every surface that states the rip's health.

TASKS R59 (b), run C of the four 0.7.112 Full runs (2026-10-22, *Roots Music*
disc 3, the secure re-read): the album pass counted 2 ripping errors, both
paranoia skips in track 16 (its ``-j`` record), and the verified-read chase
replaced track 16 with attempt 5, AccurateRip v1 confidence 11 and v2 24, which
printed READ, VERIFY and OVERLAP and no SKIP
(``round36full1022asecurerereadverifiedread.txt``, its last block). The
verdict said ``Bit-perfect: all 16 tracks``, and three surfaces still stated
the superseded read's tally: the report's ``health_status`` ("2 ripping
errors"), the EAC-layout log ("2 ripping errors" under "All tracks accurately
ripped") and the window's status line. R70 (``df181a84``) had fixed the audit's
grade only.

These tests drive each surface with run C's shape on a two-track disc, and pin
the RELATION: the report's sentence, the audit's grade, the EAC-layout line and
the window all come from one placement (``replaced_read_errors``), so they
cannot place one error two ways.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import rip_audit
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.replaced_read_errors import (
    errors_in_replaced_reads,
    errors_in_replaced_reads_of,
    place_counted_errors,
)
from platterpus.rip_health import effective_health_status, health_reads_clean
from platterpus.rip_report import build_report
from platterpus.ui.main_window_helpers import fidelity_summary

#: Run C's chase read 5's own counters: no READERR, no SKIP.
_CLEAN_CHASE_READ: dict[str, int] = {"READ": 1205, "VERIFY": 85, "OVERLAP": 17}


def _error_positions(skips_in_2: int = 2, skips_in_1: int = 0) -> dict[str, object]:
    """``disc.error_positions`` as the report records it: track 2 skipped."""
    return {
        "state": "read",
        "tracks": [
            {
                "number": n,
                "state": "read",
                "read_errors": 0,
                "skips": skips_in_2 if n == 2 else skips_in_1,
                "complete": True,
                "count_agrees_with_counters": True,
            }
            for n in (1, 2)
        ],
    }


def _verified(confidence: int) -> AccurateRipResult:
    return AccurateRipResult(
        version=2,
        result=f"accurately ripped, confidence {confidence}",
        confidence=confidence,
        local_crc="0A1B2C3D",
    )


def _rip_log(*, kept_counts: dict[str, int] | None = None, errors: int = 2) -> RipLog:
    """The log after the auto-fix merge: track 2 is the chase read, verified."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(
                number=1,
                filename="01 - One.flac",
                copy_crc="11111111",
                status="ripped successfully",
                accuraterip_v2=_verified(30),
                paranoia_counts={"READ": 900},
            ),
            TrackResult(
                number=2,
                filename="02 - Two.flac",
                copy_crc="0A1B2C3D",
                status="ripped successfully",
                accuraterip_v2=_verified(24),
                paranoia_counts=dict(
                    _CLEAN_CHASE_READ if kept_counts is None else kept_counts
                ),
            ),
        ),
        accuraterip_summary="2/2 tracks ripped accurately",
        health_status=f"{errors} ripping errors" if errors else "No errors occurred",
        ripping_errors=errors,
    )


def _retried(kept_attempt: int | None = 5) -> list[dict[str, object]]:
    """The worker's record: the chase kept attempt 5 on AccurateRip's word."""
    return [
        {
            "track": 2,
            "reripped_z": 0,
            "converged": False,
            "replaced": kept_attempt is not None,
            "replaced_because": "accuraterip" if kept_attempt is not None else None,
            "verified_read_chase": {
                "outcome": "kept_verified_read",
                "attempt_limit": 5,
                "distinct_reads_seen": 3,
                "attempts": [],
                "kept_attempt": kept_attempt,
            },
        }
    ]


def _placed(**over: object):  # type: ignore[no-untyped-def]  # test helper
    rip_log = over.pop("rip_log", None) or _rip_log()
    return errors_in_replaced_reads_of(
        rip_log,
        over.pop("error_positions", _error_positions()),
        over.pop("retried", _retried()),
    )


# --- the placement ------------------------------------------------------------


def test_run_c_places_both_errors_in_the_replaced_read_and_the_reads_kept_clean() -> (
    None
):
    placed = _placed()
    assert placed is not None
    assert (placed.counted, placed.in_replaced, placed.tracks) == (2, 2, (2,))
    assert placed.kept_read_errors == 0 and placed.reads_kept_are_clean


def test_a_replacement_with_errors_or_no_counters_is_not_clean() -> None:
    """The third input. The album's tally never counts the chase read, so its
    own counters are the only witness that the read kept had no errors; a read
    that printed none is not known to be clean."""
    skipped = _placed(rip_log=_rip_log(kept_counts={"READ": 10, "SKIP": 1}))
    silent = _placed(rip_log=_rip_log(kept_counts={}))
    assert skipped is not None and skipped.kept_read_errors == 1
    assert silent is not None and silent.kept_read_errors is None
    assert not skipped.reads_kept_are_clean and not silent.reads_kept_are_clean


def test_errors_in_a_kept_read_or_an_unclosed_count_are_not_clean() -> None:
    kept = _placed(retried=_retried(kept_attempt=None))
    assert kept is not None and kept.kept_tracks == (2,)
    assert not kept.reads_kept_are_clean
    # Track 1 also skipped, which the tally of 2 does not hold: not determined.
    assert _placed(error_positions=_error_positions(skips_in_1=1)) is None


@settings(max_examples=200, deadline=None)
@given(
    tally=st.one_of(st.none(), st.text(max_size=30), st.integers()),
    block=st.recursive(
        st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=8)),
        lambda inner: st.one_of(
            st.lists(inner, max_size=4),
            st.dictionaries(st.text(max_size=8), inner, max_size=4),
        ),
        max_leaves=12,
    ),
    replacing=st.dictionaries(
        st.integers(-2, 20),
        st.one_of(
            st.none(),
            st.dictionaries(
                st.sampled_from(["READ", "SKIP", "READERR"]), st.integers()
            ),
        ),
        max_size=3,
    ),
)
def test_the_placement_never_raises(
    tally: object, block: object, replacing: dict[int, object]
) -> None:
    """It reads a report another process wrote: never an exception."""
    place_counted_errors(tally, block, replacing)


# --- the surfaces ---------------------------------------------------------------


def test_health_status_is_about_the_reads_kept_and_names_the_replaced_read() -> None:
    rip_log = _rip_log()
    placed = _placed(rip_log=rip_log)
    said = effective_health_status(rip_log, placed)
    assert said == (
        "No errors occurred in the reads kept; the ripper's 2 ripping error(s) "
        "were all in the first read of track(s) 2, replaced by a read AccurateRip "
        "verified"
    )
    assert health_reads_clean(rip_log, placed)
    # Without the placement, or with one that is not clean, the ripper's words.
    assert effective_health_status(rip_log) == "2 ripping errors"
    unclean = _placed(rip_log=_rip_log(kept_counts={}))
    assert effective_health_status(rip_log, unclean) == "2 ripping errors"
    assert not health_reads_clean(rip_log, unclean)


def test_a_placement_of_another_count_is_not_applied() -> None:
    """The sentence and the parsed count must be the same tally."""
    placed = _placed()
    other = _rip_log(errors=3)
    assert effective_health_status(other, placed) == "3 ripping errors"


def _report(rip_log: RipLog) -> dict:
    return build_report(
        rip_log,
        disc={"error_positions": _error_positions()},
        read_speed={"retried_tracks": _retried()},  # type: ignore[arg-type]  # only the key read here
        generated_at="2026-11-03T00:00:00+00:00",
    )


def test_the_report_states_the_reads_kept_and_keeps_the_ripper_tally() -> None:
    rip_log = _rip_log()
    report = _report(rip_log)
    assert report["health_status"].startswith("No errors occurred in the reads kept")
    assert report["ripper_health_status"] == "2 ripping errors"


def test_the_report_the_audit_and_the_window_place_errors_alike() -> None:
    """The relation, which no test of one side can express: the audit re-reads
    the written report and reaches the placement the builder used."""
    rip_log = _rip_log()
    report = _report(rip_log)
    assert errors_in_replaced_reads(report) == _placed(rip_log=rip_log)
    album = rip_audit.AlbumAudit(folder=Path("x"))
    rip_audit._grade_a_reported_completion(report, album, 2, 2)
    oks = [f.text for f in album.findings if f.level == rip_audit.LEVEL_OK]
    assert oks and "no errors in the reads it keeps" in oks[0], album.findings
    summary = fidelity_summary(
        rip_log, expected_track_total=2, replaced_reads=_placed(rip_log=rip_log)
    )
    assert "all 2 tracks ripped cleanly, no read errors" in summary, summary


def test_an_older_report_still_reads_its_tally_from_health_status() -> None:
    """Schema 41 and before carried the tally in `health_status` alone."""
    report = _report(_rip_log())
    del report["ripper_health_status"]
    report["health_status"] = "2 ripping errors"
    assert errors_in_replaced_reads(report) == _placed()


def _status_report(text: str) -> list[str]:
    body = text.split("End of status report")[0]
    return body.splitlines()[-12:]


def test_the_eac_layout_line_agrees_with_the_read_that_was_kept() -> None:
    rip_log = _rip_log()
    text = render_eac_style_log(rip_log, replaced_reads=_placed(rip_log=rip_log))
    status = _status_report(text)
    assert "No errors occurred" in status
    assert (
        "Ripper's own count  : Ripping errors: 2 — all in the first read of "
        "track(s) 2, replaced by a read AccurateRip verified"
    ) in status
    assert "2 ripping errors" not in status
    # And without the placement the ripper's sentence stands, as before.
    assert "2 ripping errors" in _status_report(render_eac_style_log(rip_log))


def test_a_contradicted_track_still_keeps_no_errors_occurred_off_the_log() -> None:
    """Row 8 of the plan of record holds beside this: a track AccurateRip
    contradicts keeps EAC's "There were errors", and both facts are named."""
    rip_log = _rip_log()
    wrong = TrackResult(
        number=1,
        filename="01 - One.flac",
        copy_crc="22222222",
        status="ripped successfully",
        accuraterip_v1=AccurateRipResult(version=1, result="no match", confidence=0),
        accuraterip_offset=AccurateRipResult(
            version=1,
            result="accurately ripped, confidence 9",
            confidence=9,
            local_crc="33333333",
        ),
        paranoia_counts={"READ": 900},
    )
    from dataclasses import replace

    rip_log = replace(rip_log, tracks=(wrong, rip_log.tracks[1]))
    status = _status_report(
        render_eac_style_log(rip_log, replaced_reads=_placed(rip_log=rip_log))
    )
    assert "No errors occurred" not in status
    assert "There were errors" in status
    (line,) = [s for s in status if s.startswith("Ripper's own count")]
    assert "track(s) 2, replaced by" in line and "not counted: track(s) 1" in line
