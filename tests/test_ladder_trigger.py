"""Tests for platterpus.ladder_trigger — when a pass steps the read-speed ladder.

The worker-level cases (a real filed log, a fake ripper that exits as cyanrip
does) are in `tests/test_rip_worker.py`. These pin each refusal on its own, so a
regression names the condition that moved.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.ladder_trigger import (
    judge_step_down,
    why_pass_incomplete,
    why_pass_unfinished,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log

_FULL_RUN = (
    Path(__file__).resolve().parent.parent
    / "docs/handshake/artifactsround30/round30oct04full.log"
)


def _fork_log(
    *,
    tracks: tuple[int, ...] = (1, 2),
    failed: tuple[int, ...] = (),
    footer: str = "yes (2 of 2 tracks)",
    ripping_errors: str = "0",
    tracks_to_rip: str = "all",
) -> str:
    """A small log in the fork's shape: blocks, finish report, footer."""
    blocks = "".join(
        f"Track {n} read {'with errors.' if n in failed else 'successfully!'}\n"
        f"  EAC CRC32:     0000000{n}\n"
        "  File(s):\n"
        f"    Artist/Album/0{n} - T.flac\n"
        for n in tracks
    )
    return (
        "cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)\n"
        f"Tracks to rip:  {tracks_to_rip}\n"
        + blocks
        + f"Ripping errors: {ripping_errors}\n"
        "Encoder errors: none; 2 tracks encoded\n"
        + (f"Rip completed:  {footer}\n" if footer else "")
    )


def _judge(
    text: str,
    *,
    exit_code: int | None = 1,
    stopped_by_us: bool = False,
    log_is_this_passes: bool = True,
    only_tracks: tuple[int, ...] = (),
    disc_track_total: int | None = None,
) -> tuple[bool, str]:
    """Judge a log as cyanrip's exit-1 pass, unless told otherwise."""
    verdict = judge_step_down(
        parse_cyanrip_log(text),
        exit_code=exit_code,
        stopped_by_us=stopped_by_us,
        log_is_this_passes=log_is_this_passes,
        only_tracks=only_tracks,
        disc_track_total=disc_track_total,
    )
    return verdict.warranted, verdict.reason


def test_a_finished_pass_with_drive_errors_steps_down_on_exit_1() -> None:
    warranted, reason = _judge(_fork_log(failed=(2,), ripping_errors="3"))
    assert warranted is True
    assert "the drive failed 3 read(s)" in reason


def test_exit_0_and_exit_1_are_judged_alike() -> None:
    """Whatever the exit code: the log decides, the code only rules cases out."""
    text = _fork_log(failed=(2,), ripping_errors="3")
    assert _judge(text, exit_code=0)[0] is _judge(text, exit_code=1)[0] is True


def test_each_condition_refuses_on_its_own() -> None:
    """One refusal per condition, named, from an otherwise-stepping pass."""
    text = _fork_log(failed=(2,), ripping_errors="3")
    refusals = {
        "stopped": _judge(text, stopped_by_us=True),
        "unreaped": _judge(text, exit_code=None),
        "killed": _judge(text, exit_code=137),
        "stale": _judge(text, log_is_this_passes=False),
        "no errors": _judge(_fork_log()),
        "encoder": _judge(
            text.replace(
                "Encoder errors: none; 2 tracks encoded",
                "Encoder errors: 1 track failed (1); 1 track encoded",
            ).replace("Ripping errors: 3", "Ripping errors: 4")
        ),
        "interrupted": _judge(
            _fork_log(
                failed=(2,),
                ripping_errors="3",
                footer="no (interrupted by SIGTERM, 1 of 2 tracks)",
            )
        ),
        "aborted": _judge(
            _fork_log(
                failed=(2,), ripping_errors="3", footer="no (aborted, 1 of 2 tracks)"
            )
        ),
    }
    for name, (warranted, reason) in refusals.items():
        assert warranted is False, name
        assert reason, name
    assert "Platterpus stopped" in refusals["stopped"][1]
    assert "137" in refusals["killed"][1]
    assert "no log of its own" in refusals["stale"][1]
    assert "encode" in refusals["encoder"][1]
    assert "did not complete (interrupted by SIGTERM)" in refusals["interrupted"][1]
    assert "did not complete (aborted)" in refusals["aborted"][1]
    # The floor: every refusal is a different sentence, so none is a catch-all.
    assert len({reason for _w, reason in refusals.values()}) == len(refusals)


def test_19s_yes_over_a_failed_track_is_not_taken_at_its_word() -> None:
    """Before `.20` a failed track in an all-tracks rip still printed `yes`.

    The fork's round 30 lap 9 S22: `Rip completed:  yes (0 of 2 tracks)` over a
    run that exited 1. Here track 2 never got a block, so the pass did not finish.
    """
    text = _fork_log(tracks=(1,), ripping_errors="1", footer="yes (1 of 2 tracks)")
    warranted, reason = _judge(text)
    assert warranted is False
    assert "1 track block(s) of a 2-track disc" in reason


def test_a_selection_must_have_every_requested_track() -> None:
    """`-l 1,2,3` whose log holds 1 and 2: the third was never read."""
    text = _fork_log(
        tracks=(1, 2),
        failed=(2,),
        ripping_errors="3",
        footer="yes (2 of 14 tracks)",
        tracks_to_rip="1, 2, 3",
    )
    assert _judge(text, only_tracks=(1, 2))[0] is True
    warranted, reason = _judge(text, only_tracks=(1, 2, 3))
    assert warranted is False
    assert "track(s) 3 were asked for" in reason


def test_stock_cyanrip_with_no_footer_is_judged_by_its_finish_report() -> None:
    """Upstream prints no footer; its `Ripping errors:` only on a fall-through."""
    stock = _fork_log(failed=(2,), ripping_errors="3", footer="").replace(
        "cyanrip 0.9.4-rc2+platterpus.19 (platterpus-fork-g174a134)", "cyanrip 0.9.3"
    )
    assert _judge(stock, disc_track_total=2)[0] is True
    # Without a disc total to check against, the tracks cannot be counted.
    warranted, reason = _judge(stock)
    assert warranted is False and "not known" in reason
    # And with no finish report either, nothing says the pass finished.
    cut = stock.replace("Ripping errors: 3\n", "")
    assert "no completion footer and no finish report" in _judge(cut)[1]


def test_the_filed_full_run_is_complete_and_clean() -> None:
    """The real 18-track log: finished, so only its error count can step it."""
    parsed = parse_cyanrip_log(_FULL_RUN.read_text(encoding="utf-8"))
    assert why_pass_incomplete(parsed) == ""
    verdict = judge_step_down(
        parsed, exit_code=0, stopped_by_us=False, log_is_this_passes=True
    )
    assert verdict.warranted is False
    assert verdict.reason == "the drive reported no read errors"


def test_no_log_is_incomplete() -> None:
    assert why_pass_incomplete(None) == "there is no log to read"


@settings(max_examples=200, deadline=None)
@given(
    text=st.text(max_size=400),
    exit_code=st.one_of(st.none(), st.integers()),
    stopped=st.booleans(),
    own=st.booleans(),
    only=st.lists(st.integers(), max_size=4),
    total=st.one_of(st.none(), st.integers()),
)
def test_judge_step_down_never_raises(
    text: str,
    exit_code: int | None,
    stopped: bool,
    own: bool,
    only: list[int],
    total: int | None,
) -> None:
    """It decides from a best-effort parse, so any parse yields an answer."""
    verdict = judge_step_down(
        parse_cyanrip_log(text),
        exit_code=exit_code,
        stopped_by_us=stopped,
        log_is_this_passes=own,
        only_tracks=only,
        disc_track_total=total,
    )
    assert isinstance(verdict.warranted, bool) and verdict.reason
    # Any object at all, too: the worker hands it whatever the parse returned.
    assert (
        judge_step_down(
            object(), exit_code=1, stopped_by_us=False, log_is_this_passes=True
        ).warranted
        is False
    )


# --- The finished-pass check the securing pass asks of an exit-1 pass ---------


def _unfinished(text: str, **overrides: object) -> str:
    kwargs: dict[str, object] = {
        "exit_code": 1,
        "stopped_by_us": False,
        "log_is_this_passes": True,
    }
    kwargs.update(overrides)
    log = parse_cyanrip_log(text)
    return why_pass_unfinished(log, **kwargs)  # type: ignore[arg-type]  # test kwargs


def test_a_finished_pass_is_finished_whatever_its_exit_and_its_errors() -> None:
    """Exit 0 and exit 1 alike, read errors or none: finishing is the question."""
    for text in (_fork_log(), _fork_log(failed=(2,), ripping_errors="3")):
        assert _unfinished(text, exit_code=0) == ""
        assert _unfinished(text, exit_code=1) == ""


def test_an_encoder_failure_does_not_make_a_pass_unfinished() -> None:
    """Unlike the ladder: a securing re-read can mend a failed encode, never harm it."""
    text = _fork_log(failed=(2,), ripping_errors="4").replace(
        "Encoder errors: none; 2 tracks encoded",
        "Encoder errors: 1 track failed (1); 1 track encoded",
    )
    assert _unfinished(text) == ""


def test_the_two_questions_word_a_shared_refusal_the_same_way() -> None:
    """The relation: both callers share one helper, so a refusal for the same
    case is the same sentence in the ladder's log and the securing pass's."""
    text = _fork_log(failed=(2,), ripping_errors="3")
    cases: list[dict[str, object]] = [
        {"stopped_by_us": True},
        {"exit_code": None},
        {"exit_code": 137},
        {"log_is_this_passes": False},
    ]
    for case in cases:
        warranted, reason = _judge(text, **case)  # type: ignore[arg-type]  # test kwargs
        assert warranted is False, case
        assert _unfinished(text, **case) == reason, case
    # And the floor: four cases, four different sentences.
    assert len({_unfinished(text, **case) for case in cases}) == len(cases)


def test_an_interrupted_pass_is_unfinished_and_says_where() -> None:
    reason = _unfinished(_fork_log(footer="no (interrupted by SIGTERM, 1 of 2 tracks)"))
    assert reason.startswith("the pass did not finish: ")
    assert "interrupted by SIGTERM" in reason
