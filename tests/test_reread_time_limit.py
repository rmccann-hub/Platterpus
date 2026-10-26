"""The fork's PROPOSED `-Z` time limit, read before any build prints it.

Their round 36 lap 10 S11 (`cyanrip@52501ed:docs/handshake/round-36-lap-10.md`)
proposes `--reread-time-limit SECONDS`: after each whole-track read of a `-Z`
track that has not converged, once its reads have taken SECONDS or more, no
further read starts. Round 20's order: our reader takes every shape before any
build of theirs prints it. The shapes below are S11's text, verbatim, and the
log they sit in is the fork's own regenerated reference
(`cyanrip_fork_golden_reference_r36l7.log`, `cyanrip@ed540ff:docs/golden-reference.log`
byte for byte, hashed below) with S11's lines put where S11 says they go.

**The claim these tests protect is the fail-safe direction.** A time-limit line
that fell through as unrecognised would leave the track with NO verdict, and the
EAC-layout log infers convergence for an unmeasured track read twice or more. So
the line must read as NOT converged. And the second claim: a track our clock
stopped is never described as one whose reads disagreed, because the limit is
ours, not the disc's.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from pathlib import Path

import pytest

from platterpus import reread_limit
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import (
    is_ripper_error_line,
    is_secure_rerip_verdict,
    parse_cyanrip_log,
    secure_rerip_limit_agreement,
    secure_rerip_limit_kept_read,
    secure_rerip_limit_stop,
    secure_rerip_verdict_converged,
)
from platterpus.parsers.rip_log import LimitKeptRead, RereadAgreement, TrackResult
from platterpus.reread_limit import RereadLimitStop
from platterpus.rip_report import build_report
from platterpus.ui.main_window_rip import _merge_shipped_track

_FIXTURES = Path(__file__).parent / "fixtures"
_R36L7_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r36l7.log"
_R36L7_SHA256 = "bc9b98c426e9a7bc688a357fdabe5dc062d45347a824848bbc958909c50c75e3"

# --- S11's shapes, verbatim ------------------------------------------------------

#: The disc header line, below `Retry limit:`, only when the option is given.
_S11_HEADER = "Re-read limit:  600 s a track, checked between whole-track reads"
#: The `-Z` loop's end line.
_S11_DONE = "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed)"
#: The same, carrying the repeat limit's two clauses as they are (S11: "taking the
#: repeat limit's two clauses as they are"; their wording at the repeat limit is
#: `cyanrip@52501ed:src/cyanrip_main.c:1833` and `:1858`).
_S11_DONE_NOT_KEPT = (
    "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed; "
    "last read 0A0B0C0D, not kept)"
)
_S11_DONE_AR = (
    "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed; "
    "kept 1FFC9968, read 2 times, which AccurateRip matches at confidence 200; "
    "last read 0A0B0C0D, not kept)"
)
#: The track block's row, beside the repeat limit's `(repeat limit hit)`.
_S11_ROW = (
    "  Secure re-read:  did NOT converge after 4 reads (time limit of 600 s reached)"
)
#: The repeat limit's own forms, which every build since `.19` prints
#: (`cyanrip@52501ed:src/cyanrip_main.c:1864`, `src/cyanrip_log.c:736`).
_REPEAT_DONE = "Done; (repeat limit of 3 reads reached; at most 2 reads agreed)"
_REPEAT_ROW = "  Secure re-read:  did NOT converge after 3 reads (repeat limit hit)"

_TIME_STOP = RereadLimitStop(
    kind=reread_limit.STOPPED_BY_TIME_LIMIT, time_limit_seconds=600, reads=4
)


def _golden() -> str:
    text = _R36L7_LOG.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == _R36L7_SHA256
    return text


def _once(text: str, old: str, new: str, *, start: int = 0) -> str:
    """``text`` with the first ``old`` at or after ``start`` replaced; it must exist."""
    at = text.index(old, start)  # raises if the anchor is gone: a floor
    return text[:at] + new + text[at + len(old) :]


def _with_s11() -> str:
    """The reference with S11's lines put where S11 says they go.

    Track 1 stays as published (converged). Track 2 is stopped by the time limit
    after 4 reads. Track 3 is stopped by the repeat limit, so the two limits sit
    side by side in one log, and a reading that confused them would show.
    """
    text = _golden()
    retry = "Retry limit:    10 (per frame, and per whole-track re-read)\n"
    assert text.count(retry) == 1
    text = text.replace(retry, retry + _S11_HEADER + "\n")
    text = _once(
        text,
        "Done; (2 out of 2 matches for current checksum 07B89F6F)\n"
        "Track 2 read successfully!\n",
        f"{_S11_DONE}\nTrack 2 read with errors.\n",
    )
    two = text.index("Track 2 read with errors.")
    text = _once(text, "(after 3 rips)", "(after 4 rips)", start=two)
    text = _once(
        text, "  Secure re-read:  converged after 3 reads", _S11_ROW, start=two
    )
    text = _once(
        text,
        "Done; (2 out of 2 matches for current checksum CC206A3D)\n"
        "Track 3 read successfully!\n",
        f"{_REPEAT_DONE}\nTrack 3 read with errors.\n",
    )
    three = text.index("Track 3 read with errors.")
    text = _once(
        text, "  Secure re-read:  converged after 3 reads", _REPEAT_ROW, start=three
    )
    return text


# --- the verdict: never convergence ------------------------------------------------


@pytest.mark.parametrize("line", [_S11_DONE, _S11_DONE_NOT_KEPT, _S11_DONE_AR])
def test_the_time_limit_line_is_a_verdict_and_never_convergence(line: str) -> None:
    for shown in (line, "  " + line, "\t" + line):
        assert secure_rerip_verdict_converged(shown) is False, shown
        assert is_secure_rerip_verdict(shown), shown
        # The pair is the check: the limit arm claims it AND the convergence
        # arm does not.
        assert cyanrip_log._SECURE_DONE_FAIL.match(shown), shown
        assert cyanrip_log._SECURE_DONE_MATCH.match(shown) is None, shown
        # A verdict is a fact about the read, never a ripper failure line.
        assert not is_ripper_error_line(shown), shown


def test_near_misses_of_the_time_limit_arm_stay_unread() -> None:
    for line in (
        "Done; (time limitless reads)",
        "Repeating ripping (time limit of 600 s reached after 4 reads)",
        "Done; the time limit of 600 s was reached",
    ):
        assert secure_rerip_verdict_converged(line) is None, line


def test_the_track_row_reads_as_not_converged() -> None:
    assert cyanrip_log._parse_secure_verdict(_S11_ROW.split(":", 1)[1]) is False


# --- the reference, with S11's lines in it -----------------------------------------


def test_the_reference_with_s11_reads_each_track_by_its_own_limit() -> None:
    log = parse_cyanrip_log(_with_s11())
    tracks = {t.number: t for t in log.tracks}
    assert sorted(tracks) == [1, 2, 3]  # floor: the whole log was read

    info = log.ripping_info
    assert (info.reread_time_limit_seconds, info.reread_time_limit_state) == (
        600,
        reread_limit.TIME_LIMIT_READ,
    )

    assert tracks[1].secure_rerip_converged is True
    assert tracks[1].secure_rerip_limit_stop is None

    two = tracks[2]
    assert two.secure_rerip_converged is False
    assert two.status == "ripped with errors"  # `Track N read with errors.`
    assert two.secure_rerip_limit_stop == _TIME_STOP
    assert two.secure_rerip_agreement == RereadAgreement(
        most_reads_agreed=2, exact=True
    )

    three = tracks[3]
    assert three.secure_rerip_converged is False
    # The row's `(repeat limit hit)` names no count; the `Done;` line's is kept.
    assert three.secure_rerip_limit_stop == RereadLimitStop(
        kind=reread_limit.STOPPED_BY_REPEAT_LIMIT, repeat_limit_reads=3, reads=3
    )


def test_no_s11_line_is_left_unrecognised(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parse_cyanrip_log(_with_s11())
    unread = [
        r.getMessage()
        for r in caplog.records
        if "unrecognised" in r.getMessage() and "line" in r.getMessage()
    ]
    assert not unread, unread
    # And the header line is claimed by a rule, not by the ignored list.
    claimed = [
        rule.name
        for rule in cyanrip_log._ALL_LINE_RULES
        if rule.pattern.match(_S11_HEADER)
    ]
    assert claimed == ["reread_time_limit"], claimed


def test_without_the_option_nothing_changes() -> None:
    """The published reference, untouched: no header, every limit field empty."""
    log = parse_cyanrip_log(_golden())
    assert len(log.tracks) == 3
    assert log.ripping_info.reread_time_limit_state == (
        reread_limit.TIME_LIMIT_NOT_PRESENT
    )
    assert log.ripping_info.reread_time_limit_seconds is None
    assert {t.secure_rerip_limit_stop for t in log.tracks} == {None}


# --- the clauses the time-limit line carries ---------------------------------------


def test_the_kept_read_clauses_are_read_on_the_time_limit_line() -> None:
    assert secure_rerip_limit_kept_read(_S11_DONE_AR) == LimitKeptRead(
        crc="1FFC9968",
        reads=2,
        accuraterip_confidence=200,
        last_read_crc="0A0B0C0D",
    )
    for line in (_S11_DONE, _S11_DONE_NOT_KEPT, _S11_DONE_AR):
        agreement = secure_rerip_limit_agreement(line, [])
        assert agreement == RereadAgreement(most_reads_agreed=2, exact=True), line
        assert secure_rerip_limit_stop(line) == _TIME_STOP, line


def test_which_limit_each_shape_names() -> None:
    repeat = reread_limit.STOPPED_BY_REPEAT_LIMIT
    cases = {
        _REPEAT_DONE: RereadLimitStop(kind=repeat, repeat_limit_reads=3),
        "Done; (no matches found, but hit repeat limit of 5)": RereadLimitStop(
            kind=repeat, repeat_limit_reads=5
        ),
        _REPEAT_ROW: RereadLimitStop(kind=repeat, reads=3),
        _S11_ROW: _TIME_STOP,
        # Not verdicts that stopped at a limit: converged, or not a verdict.
        "  Secure re-read:  converged after 3 reads": None,
        "Done; (2 out of 2 matches for current checksum 1FFC9968)": None,
        "Repeating ripping (1 out of 2 matches for current checksum 1FFC9968)": None,
        "Re-read limit:  600 s a track, checked between whole-track reads": None,
    }
    for line, expected in cases.items():
        assert secure_rerip_limit_stop(line) == expected, line


def test_a_line_naming_both_limits_names_neither() -> None:
    both = "Done; (time limit of 600 s reached after 4 reads; repeat limit of 5 reads)"
    assert secure_rerip_verdict_converged(both) is False  # still not converged
    assert secure_rerip_limit_stop(both) is None


def test_the_row_wins_over_the_buffered_line_and_a_converged_row_clears_it() -> None:
    def track(done: str, row: str) -> TrackResult:
        return parse_cyanrip_log(
            "cyanrip 0.9.4-rc3+platterpus.28 (platterpus-fork-g0000000)\n"
            f"{done}\nTrack 1 read with errors.\n"
            "  EAC CRC32:     AAAA1111 (after 4 rips)\n"
            f"{row}\n"
        ).tracks[0]

    # A different limit in the row: the row's, alone.
    assert track(_REPEAT_DONE, _S11_ROW).secure_rerip_limit_stop == _TIME_STOP
    # A converged row: no limit stopped anything.
    converged = track(_S11_DONE, "  Secure re-read:  converged after 4 reads")
    assert converged.secure_rerip_converged is True
    assert converged.secure_rerip_limit_stop is None
    # A row that names no limit leaves the line's alone.
    unnamed = track(_S11_DONE, "  Secure re-read:  did NOT converge after 4 reads")
    assert unnamed.secure_rerip_limit_stop == _TIME_STOP


# --- the header line ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("600 s a track, checked between whole-track reads", ("read", 600, "")),
        ("1 s a track, checked between whole-track reads", ("read", 1, "")),
        # A reworded trailer keeps the seconds.
        ("900 s a track, checked after each read", ("read", 900, "")),
        # The option takes a whole number from 1: a zero is not a limit.
        ("0 s a track, checked between whole-track reads", ("unrecognised", None)),
        ("ten minutes a track", ("unrecognised", None)),
        ("600 seconds", ("unrecognised", None)),
    ],
)
def test_the_header_value_is_read_or_kept(
    value: str, expected: tuple[object, ...], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="platterpus.reread_limit"):
        state, seconds, text = reread_limit.time_limit_state(value)
    assert (state, seconds) == expected[:2]
    if state == reread_limit.TIME_LIMIT_READ:
        assert text == ""
        assert not caplog.records
    else:
        # Kept, and said in the log: never dropped, never guessed.
        assert text == value
        assert any("Re-read limit:" in r.getMessage() for r in caplog.records)


# --- the report --------------------------------------------------------------------


def test_the_report_names_the_limit_per_track_and_the_header() -> None:
    report = build_report(parse_cyanrip_log(_with_s11()))
    rip = report["rip"]
    assert (
        rip["reread_time_limit_seconds"],
        rip["reread_time_limit_state"],
        rip["reread_time_limit_text"],
    ) == (600, "read", None)
    stops = [row["secure_rerip_limit_stop"] for row in report["tracks"]]
    assert stops == [
        None,
        {
            "stopped_by": "time_limit",
            "time_limit_seconds": 600,
            "repeat_limit_reads": None,
            "reads": 4,
        },
        {
            "stopped_by": "repeat_limit",
            "time_limit_seconds": None,
            "repeat_limit_reads": 3,
            "reads": 3,
        },
    ]


def test_the_report_without_the_option_says_not_present() -> None:
    report = build_report(parse_cyanrip_log(_golden()))
    assert report["rip"]["reread_time_limit_state"] == "not_present"
    assert report["rip"]["reread_time_limit_seconds"] is None
    assert [row["secure_rerip_limit_stop"] for row in report["tracks"]] == [None] * 3


# --- the EAC-layout log: our limit, never the disc ----------------------------------


def _block(text: str, number: int) -> str:
    start = text.index(f"Track {number:>2}\n")
    end = text.find("\nTrack ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_the_eac_layout_log_says_our_time_limit_stopped_the_track() -> None:
    text = render_eac_style_log(parse_cyanrip_log(_with_s11()))
    two = _block(text, 2)
    assert (
        "Copy CRC 07B89F6F  (re-reads stopped at our time limit of 600 s before "
        "they converged; at most 2 of 4 reads agreed — this read is not confirmed "
        "reproducible)"
    ) in two, two
    assert (
        "Copy NOT confirmed — re-reads stopped at our time limit before they "
        "converged, so this track is not verified reproducible"
    ) in two, two
    # Never the disc: no sentence that says the reads disagreed.
    for blame in ("did NOT agree", "did not converge,", "Copy OK", "Test CRC"):
        assert blame not in two, (blame, two)

    stability = [line for line in text.splitlines() if line.startswith("Read stab")]
    assert stability == [
        "Read stability      : track(s) 2 stopped re-reading at our time limit "
        "before the reads converged — not confirmed reproducible (a limit we set, "
        "not a finding about the disc)",
        "Read stability      : track(s) 3 did not read identically across re-reads "
        "— not confirmed reproducible",
    ], stability

    # The repeat limit's track reads exactly as it always has.
    three = _block(text, 3)
    assert "re-reads did not converge; at most 2 of 3 reads agreed" in three, three
    assert "Copy NOT confirmed — re-reads did not converge" in three, three


def test_a_track_stopped_after_one_read_says_no_count() -> None:
    """The first read always runs, and the clock can stop the track after it:
    "at most 1 read agreed" is then true and says nothing, and "did NOT agree"
    would blame the disc for our limit."""
    parsed = parse_cyanrip_log(_with_s11())
    one_read = replace(
        parsed.tracks[1],
        rip_count=1,
        secure_rerip_agreement=RereadAgreement(most_reads_agreed=1, exact=True),
    )
    text = render_eac_style_log(replace(parsed, tracks=(one_read,)))
    assert (
        "(re-reads stopped at our time limit of 600 s before they converged — "
        "this read is not confirmed reproducible)"
    ) in text, text
    assert "did NOT agree" not in text


# --- a re-rip's verdict takes its own limit with it --------------------------------


def test_a_reripped_verdict_never_keeps_the_first_pass_limit() -> None:
    first_pass = TrackResult(
        number=2,
        copy_crc="07B89F6F",
        rip_count=4,
        secure_rerip_converged=False,
        secure_rerip_limit_stop=_TIME_STOP,
    )
    # Re-read and not swapped in: the first pass's limit does not describe it.
    assert (
        _merge_shipped_track(first_pass, None, {2: True}).secure_rerip_limit_stop
        is None
    )
    # Swapped in: the shipped read's own.
    shipped = replace(
        first_pass,
        secure_rerip_limit_stop=RereadLimitStop(
            kind=reread_limit.STOPPED_BY_REPEAT_LIMIT, repeat_limit_reads=5
        ),
    )
    merged = _merge_shipped_track(first_pass, shipped, {2: False})
    assert merged.secure_rerip_limit_stop == shipped.secure_rerip_limit_stop
