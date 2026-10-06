"""Tests for platterpus.securing_pass — whether the securing pass runs, and over what.

The worker-level cases (the filed `.19` full run, a fake ripper that exits as
cyanrip does) are in `tests/test_rip_worker.py`, under *The securing pass after a
pass the drive could not read cleanly*. These pin the gate and the plan on their
own, so a regression names the rule that moved.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.ladder_trigger import why_pass_unfinished
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.securing_pass import (
    SKIPPED_ALBUM_PASS_UNFINISHED,
    SKIPPED_DISC_NOT_IN_ACCURATERIP,
    TRIGGER_ACCURATERIP,
    TRIGGER_INSTABILITY,
    SecuringPlan,
    first_pass_records,
    plan_securing_pass,
    why_no_securing_pass,
)

_FULL_RUN = (
    Path(__file__).resolve().parent.parent
    / "docs/handshake/artifactsround30/round30oct04full.log"
)


def _fork_log(*, footer: str = "yes (2 of 2 tracks)", errors: str = "3") -> object:
    """A finished two-track fork log whose drive failed a read on track 2."""
    return parse_cyanrip_log(
        "cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)\n"
        "Tracks to rip:  all\n"
        "Track 1 read successfully!\n"
        "  EAC CRC32:     00000001\n"
        "Track 2 read with errors.\n"
        "  EAC CRC32:     00000002\n"
        f"Ripping errors: {errors}\n"
        "Encoder errors: none; 2 tracks encoded\n" + f"Rip completed:  {footer}\n"
    )


def _stock_log_without_a_total() -> object:
    """Stock cyanrip's shape: no footer, so completeness needs our disc total."""
    return parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Speed:          default (changeable)\n"
        "Disc tracks:    1\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     329DC760\n"
        "  File(s):\n"
        "    Artist/Album/01 - One.flac\n"
        "Ripping errors: 0\n"
    )


def _gate(log: object, **overrides: object) -> str:
    kwargs: dict[str, object] = {
        "exit_code": 1,
        "stopped_by_us": False,
        "log_is_this_passes": True,
    }
    kwargs.update(overrides)
    return why_no_securing_pass(log, **kwargs)  # type: ignore[arg-type]  # test kwargs


# --- The gate -----------------------------------------------------------------


def test_a_finished_exit_1_pass_is_secured() -> None:
    """THE ruling (C1): exit 1 for drive errors over a finished pass."""
    assert _gate(_fork_log()) == ""


def test_the_filed_full_run_with_drive_errors_is_secured_on_exit_1() -> None:
    """The real `.19` log, rewritten as the pass the drive could not read."""
    text = _FULL_RUN.read_text(encoding="utf-8")
    assert text.count("Track 18 read successfully!\n") == 1
    rewritten = text.replace(
        "Track 18 read successfully!\n", "Track 18 read with errors.\n"
    ).replace("\nRipping errors: 0\n", "\nRipping errors: 3\n")
    assert _gate(parse_cyanrip_log(rewritten), disc_track_total=18) == ""


def test_each_exit_1_refusal_names_its_condition() -> None:
    """One refusal per condition, from an otherwise-secured exit-1 pass."""
    refusals = {
        "stopped": _gate(_fork_log(), stopped_by_us=True),
        "stale": _gate(_fork_log(), log_is_this_passes=False),
        "interrupted": _gate(
            _fork_log(footer="no (interrupted by SIGTERM, 1 of 2 tracks)")
        ),
        "aborted": _gate(_fork_log(footer="no (aborted, 1 of 2 tracks)")),
        "unprovable": _gate(_stock_log_without_a_total()),
    }
    assert "Platterpus stopped" in refusals["stopped"]
    assert "no log of its own" in refusals["stale"]
    assert "interrupted by SIGTERM" in refusals["interrupted"]
    assert "did not complete (aborted)" in refusals["aborted"]
    assert "how many tracks the disc has is not known" in refusals["unprovable"]
    # The floor: every refusal is its own sentence, so none is a catch-all.
    assert len(set(refusals.values())) == len(refusals)


def test_a_signal_a_crash_and_an_unreaped_exit_refuse() -> None:
    log = _fork_log()
    assert "137" in _gate(log, exit_code=137)
    assert "-15" in _gate(log, exit_code=-15)
    assert "never collected" in _gate(log, exit_code=None)


def test_the_exit_0_path_keeps_its_rule() -> None:
    """A clean exit 0 Platterpus did not stop is secured on cyanrip's word, as
    before C1, even where the log alone could not prove the pass finished.

    The twin of the "unprovable" refusal above: the same log, refused on exit 1,
    secured on exit 0. Without the pair, a gate that secured nothing on exit 1, or
    refused everything on exit 0, would pass one of the two.
    """
    stock = _stock_log_without_a_total()
    assert _gate(stock, exit_code=0) == ""
    assert _gate(stock, exit_code=0, log_is_this_passes=False) == ""
    assert _gate(stock, exit_code=1) != ""
    # But a stop we sent refuses on exit 0 too.
    assert "Platterpus stopped" in _gate(stock, exit_code=0, stopped_by_us=True)


@settings(max_examples=200, deadline=None)
@given(
    exit_code=st.none() | st.integers(min_value=-64, max_value=300),
    stopped_by_us=st.booleans(),
    log_is_this_passes=st.booleans(),
    disc_track_total=st.none() | st.integers(min_value=0, max_value=99),
)
def test_every_case_but_a_clean_exit_0_is_the_finished_checks_answer(
    exit_code: int | None,
    stopped_by_us: bool,
    log_is_this_passes: bool,
    disc_track_total: int | None,
) -> None:
    """The relation: the gate DELEGATES to `why_pass_unfinished` rather than
    restating it, so the two cannot word one refusal two ways."""
    log = _fork_log()
    kwargs = {
        "exit_code": exit_code,
        "stopped_by_us": stopped_by_us,
        "log_is_this_passes": log_is_this_passes,
        "disc_track_total": disc_track_total,
    }
    gate = why_no_securing_pass(log, **kwargs)  # type: ignore[arg-type]  # hypothesis kwargs
    if exit_code == 0 and not stopped_by_us:
        assert gate == ""
    else:
        assert gate == why_pass_unfinished(log, **kwargs)  # type: ignore[arg-type]  # same


# --- The plan -----------------------------------------------------------------


def _plan(log: object, **overrides: object) -> SecuringPlan:
    kwargs: dict[str, object] = {
        "refusal": "",
        "dynamic": True,
        "auto_ladder": False,
        "secure_rerip_matches": 2,
        "max_retries": 5,
        "include_offset_variant": True,
        "unstable": (),
    }
    kwargs.update(overrides)
    return plan_securing_pass(log, **kwargs)  # type: ignore[arg-type]  # test kwargs


def test_plain_fixed_mode_has_no_securing_pass() -> None:
    plan = _plan(_fork_log(), dynamic=False, auto_ladder=False, refusal="anything")
    assert plan == SecuringPlan()
    assert plan.applies is False


def test_a_refusal_is_recorded_with_its_reason() -> None:
    plan = _plan(_fork_log(), refusal="Platterpus stopped this pass")
    assert plan.applies is True
    assert plan.tracks == ()
    assert plan.refused == "Platterpus stopped this pass"
    assert plan.skipped_reason == SKIPPED_ALBUM_PASS_UNFINISHED
    # Not asked is not "no": a refused plan never looked the disc up.
    assert plan.disc_in_accuraterip is None


def test_dynamic_mode_secures_the_tracks_accuraterip_did_not_confirm() -> None:
    log = parse_cyanrip_log(_FULL_RUN.read_text(encoding="utf-8"))
    plan = _plan(log)
    assert plan.tracks == (12, 13, 14, 15, 17, 18)
    assert (plan.trigger, plan.rerip_z) == (TRIGGER_ACCURATERIP, 2)
    assert plan.disc_in_accuraterip is True and plan.skipped_reason is None


def test_dynamic_mode_skips_a_disc_accuraterip_does_not_know() -> None:
    plan = _plan(_fork_log())  # no AccurateRip lines at all
    assert plan.tracks == ()
    assert plan.disc_in_accuraterip is False
    assert plan.skipped_reason == SKIPPED_DISC_NOT_IN_ACCURATERIP


def test_the_ladder_re_reads_its_unstable_tracks_inside_the_retry_ceiling() -> None:
    plan = _plan(_fork_log(), dynamic=False, auto_ladder=True, unstable=(2,))
    assert (plan.tracks, plan.trigger) == ((2,), TRIGGER_INSTABILITY)
    # -r 3 lets -Z 2 converge (three identical reads) and no harder.
    assert (
        _plan(
            _fork_log(), dynamic=False, auto_ladder=True, unstable=(2,), max_retries=3
        ).rerip_z
        == 2
    )


def test_first_pass_records_carry_each_tracks_crc_and_record() -> None:
    crcs, records = first_pass_records(_fork_log())
    assert crcs == {1: "00000001", 2: "00000002"}
    assert sorted(records) == [1, 2]
    assert first_pass_records(None) == ({}, {})
