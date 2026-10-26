"""Tests for the verified-read chase (TASKS R7): the decision and the reads.

`verified_read_chase.plan_chase` decides whether a track gets extra single
reads; `workers.verified_read_run.run_chase` takes them. Synthetic logs and
parsed records only, never audio. The fixtures are shaped on the 2026-10-12
hardware run's track 5 (read ``C96464AB`` once, the value AccurateRip verifies,
then ``4065BECC`` twice) and round 32's securing pass
(``round32fullwholediscsecuringpass.txt``: ``C96464AB`` once, ``E0036697`` three
times).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.parsers.cyanrip_log import (
    parse_cyanrip_log,
    secure_rerip_limit_kept_read,
    secure_rerip_read_checksum,
)
from platterpus.parsers.rip_log import AccurateRipResult, LimitKeptRead, TrackResult
from platterpus.rip_report import build_report
from platterpus.verified_read_chase import (
    CHASE_ATTEMPTS_CEILING,
    CHASE_KEPT_VERIFIED,
    CHASE_NONE_VERIFIED,
    CHASE_SKIPPED_NOT_DETERMINED,
    CHASE_SKIPPED_READS_AGREED,
    CHASE_STOPPED,
    KEPT_FIRST_READ,
    KEPT_SECURING_PASS,
    KEPT_VERIFIED_REREAD,
    ChaseDecision,
    chase_log_path_for,
    chase_log_section,
    copy_chase_block,
    kept_read,
    plan_chase,
    securing_pass_read_checksums,
)
from platterpus.workers.verified_read_run import SingleRead, chase_sentence, run_chase

# --- Fixtures ---------------------------------------------------------------


def _track(crc: str, *, confidence: int | None = None, number: int = 5) -> TrackResult:
    """A parsed track whose v2 result matched at ``confidence`` (None = no match)."""
    v2 = AccurateRipResult(
        version=2,
        result="accurately ripped" if confidence else "not found",
        confidence=confidence,
        local_crc="BCF4E815" if confidence else "9EEB8843",
    )
    return TrackResult(number=number, copy_crc=crc, accuraterip_v2=v2)


UNVERIFIED = _track("4065BECC")
VERIFIED = _track("C96464AB", confidence=200)

#: A securing pass's log, shaped on round 32's: track 3 hit the limit with four
#: printed values and no checksum on its `Done;` line; track 5 converged.
SECURING_LOG = """\
Tracks:

Repeating ripping (0 out of 2 matches for current checksum 2AC1F945)
Repeating ripping (0 out of 2 matches for current checksum 1AC787A1)
Repeating ripping (0 out of 2 matches for current checksum DDF455EF)
Repeating ripping (0 out of 2 matches for current checksum 660CECDF)
Done; (repeat limit of 5 reads reached; at most 1 read agreed)
Track 3 read with errors.
  EAC CRC32:     D27A4CE4 (after 5 rips)

Repeating ripping (0 out of 2 matches for current checksum C96464AB)
Repeating ripping (0 out of 2 matches for current checksum E0036697)
Repeating ripping (1 out of 2 matches for current checksum e0036697)
Done; (2 out of 2 matches for current checksum E0036697)
Track 5 read successfully!
  EAC CRC32:     E0036697 (after 4 rips)
"""


# --- Reading the securing pass's per-read values ----------------------------


def test_each_tracks_read_values_are_attributed_to_the_track_they_end_on() -> None:
    values = securing_pass_read_checksums(SECURING_LOG)
    assert values == {
        3: ("2AC1F945", "1AC787A1", "DDF455EF", "660CECDF"),
        5: ("C96464AB", "E0036697", "E0036697", "E0036697"),
    }


def test_a_read_checksum_is_read_only_off_a_loop_line() -> None:
    """The fragment is searched only in a line the loop's own patterns claim."""
    assert (
        secure_rerip_read_checksum(
            "Repeating ripping (0 out of 2 matches for current checksum c96464ab)"
        )
        == "C96464AB"
    )
    assert (
        secure_rerip_read_checksum(
            "Done; (2 out of 2 matches for current checksum E0036697)"
        )
        == "E0036697"
    )
    # The limit-hit line prints none, in either wording.
    assert (
        secure_rerip_read_checksum(
            "Done; (no matches found, but hit repeat limit of 3)"
        )
        is None
    )
    # The same words on a line that is not a loop line are not a read.
    assert secure_rerip_read_checksum("Comment: current checksum C96464AB") is None


def test_values_with_no_track_line_after_them_are_not_attributed() -> None:
    """A log cut short mid-loop: the reads are nobody's, so nothing is guessed."""
    text = "Repeating ripping (0 out of 2 matches for current checksum C96464AB)\n"
    assert securing_pass_read_checksums(text) == {}


# --- The decision -------------------------------------------------------------


def _plan(**overrides: object) -> ChaseDecision | None:
    args: dict[str, object] = {
        "disc_in_accuraterip": True,
        "kept": UNVERIFIED,
        "first_pass": UNVERIFIED,
        "securing": UNVERIFIED,
        "loop_values": ("C96464AB", "4065BECC", "4065BECC"),
        "max_retries": 5,
    }
    args.update(overrides)
    return plan_chase(**args)  # type: ignore[arg-type]  # a test's keyword bag


def test_the_2026_10_12_track_5_is_chased() -> None:
    """Two values among the reads, the kept one unverified, the disc in the DB."""
    decision = _plan()
    assert decision == ChaseDecision(True, 5, 2)


def test_a_disc_accuraterip_does_not_hold_is_never_chased() -> None:
    """No read of it can be verified, so extra reads only cost time."""
    assert _plan(disc_in_accuraterip=False) is None


def test_a_verified_kept_read_is_never_chased() -> None:
    assert _plan(kept=VERIFIED) is None


def test_a_drive_that_returned_one_value_every_time_is_not_chased() -> None:
    decision = _plan(loop_values=("E0036697", "E0036697", "E0036697"))
    assert decision == ChaseDecision(False, 5, 1, CHASE_SKIPPED_READS_AGREED)


def test_reads_that_cannot_be_compared_are_not_determined_never_agreed() -> None:
    """Tri-state: no value to compare is not evidence the reads agreed."""
    decision = _plan(loop_values=(), first_pass=None)
    assert decision == ChaseDecision(False, 5, None, CHASE_SKIPPED_NOT_DETERMINED)


def test_two_block_crcs_that_differ_count_as_two_values() -> None:
    """The album pass and the securing pass read different EAC CRC32s."""
    decision = _plan(
        loop_values=("E0036697",), first_pass=_track("1D0B4419"), securing=UNVERIFIED
    )
    assert decision is not None and decision.run
    assert decision.distinct_reads_seen == 2


def test_two_equal_block_crcs_with_no_loop_values_are_one_value() -> None:
    decision = _plan(loop_values=())
    assert decision == ChaseDecision(False, 5, 1, CHASE_SKIPPED_READS_AGREED)


@pytest.mark.parametrize(
    ("max_retries", "limit"), [(1, 1), (3, 3), (5, 5), (20, CHASE_ATTEMPTS_CEILING)]
)
def test_the_attempt_limit_is_the_users_r_capped(max_retries: int, limit: int) -> None:
    decision = _plan(max_retries=max_retries)
    assert decision is not None and decision.attempt_limit == limit


# --- The reads ----------------------------------------------------------------


class _Reads:
    """A stand-in for `RipWorker._read_once_for_chase`: one scripted read per call.

    Each read writes a log naming the track and, like the real pass, a file in
    the attempt's folder; `parse_log` reads that log with the real parser.
    """

    def __init__(
        self, crcs: list[tuple[str, int | None, int]], number: int = 5
    ) -> None:
        # (EAC CRC32, AccurateRip v2 confidence or None, exit code) per read.
        self.crcs = crcs
        self.number = number
        self.calls: list[Path] = []

    def __call__(self, number: int, folder: Path) -> SingleRead | None:
        crc, confidence, exit_code = self.crcs[len(self.calls)]
        self.calls.append(folder)
        ar = (
            f"accurately ripped, confidence {confidence}"
            if confidence
            else "not found, either a new pressing, or bad rip"
        )
        log = folder / "rip.log"
        log.write_text(
            "cyanrip 0.9.3 (release)\n"
            "AccurateRip:    found\n"
            f"Track {self.number} read successfully!\n"
            f"  EAC CRC32:     {crc}\n"
            f"    Accurip v2:  BCF4E815 ({ar})\n"
            "  File(s):\n"
            f"    {crc}.flac\n",
            encoding="utf-8",
        )
        (folder / f"{crc}.flac").write_bytes(crc.encode())
        return SingleRead(exit_code == 0, str(log), exit_code, ("cyanrip", "-l", "5"))


def _parse(path: str) -> object | None:
    return parse_cyanrip_log(Path(path).read_text(encoding="utf-8"))


def _chase(reads: _Reads, *, cancelled: list[bool] | None = None, limit: int = 5):  # type: ignore[no-untyped-def]  # a test helper returning run_chase's own type
    swapped: list[str] = []

    def swap_in(track: object, folder: Path) -> bool:
        swapped.append((folder / str(getattr(track, "filename", ""))).read_text())
        return True

    flags = cancelled if cancelled is not None else [False]
    run = run_chase(
        5,
        ChaseDecision(True, limit, 2),
        kept=UNVERIFIED,
        read_once=reads,
        parse_log=_parse,
        swap_in=swap_in,
        cancelled=lambda: flags[0],
    )
    return run, swapped


def test_the_first_read_accuraterip_verifies_is_kept_and_the_chase_ends() -> None:
    reads = _Reads([("4065BECC", None, 0), ("C96464AB", 200, 0), ("C96464AB", 200, 0)])
    run, swapped = _chase(reads)
    assert len(reads.calls) == 2, "the chase did not stop at the verified read"
    assert swapped == ["C96464AB"]
    assert run.block["outcome"] == CHASE_KEPT_VERIFIED
    assert run.block["kept_attempt"] == 2
    assert [a["eac_crc"] for a in run.block["attempts"]] == ["4065BECC", "C96464AB"]
    assert [a["kept"] for a in run.block["attempts"]] == [False, True]
    assert run.block["attempts"][1]["accuraterip_v2_confidence"] == 200
    assert getattr(run.kept_track, "copy_crc", "") == "C96464AB"
    # Every attempt's folder is gone afterwards, kept read or not.
    assert not any(folder.exists() for folder in reads.calls)
    assert len(run.sections) == 2 and "attempt 2" in run.sections[1]


def test_when_no_read_is_verified_nothing_is_kept_and_the_record_says_so() -> None:
    reads = _Reads([("4065BECC", None, 0)] * 3)
    run, swapped = _chase(reads, limit=3)
    assert len(reads.calls) == 3
    assert swapped == []
    assert run.kept_track is None
    assert run.block["outcome"] == CHASE_NONE_VERIFIED
    assert run.block["kept_attempt"] is None
    assert "none of 3 single read(s)" in chase_sentence(5, run.block)


def test_a_verified_read_that_did_not_exit_cleanly_is_not_kept() -> None:
    """Nothing is swapped in from a read that did not finish (exit 1 here)."""
    reads = _Reads([("C96464AB", 200, 1), ("C96464AB", 200, 0)])
    run, swapped = _chase(reads)
    assert run.block["attempts"][0]["kept"] is False
    assert run.block["attempts"][0]["exit_code"] == 1
    assert run.block["kept_attempt"] == 2


def test_a_read_whose_log_names_another_track_is_not_kept() -> None:
    reads = _Reads([("C96464AB", 200, 0)], number=6)
    run, swapped = _chase(reads, limit=1)
    assert swapped == []
    assert run.block["outcome"] == CHASE_NONE_VERIFIED
    assert run.block["attempts"][0]["eac_crc"] is None


def test_a_cancel_stops_the_chase_before_the_next_read() -> None:
    flags = [False]
    reads = _Reads([("4065BECC", None, 0)] * 5)

    def read_then_cancel(number: int, folder: Path) -> SingleRead | None:
        flags[0] = True
        return reads(number, folder)

    run = run_chase(
        5,
        ChaseDecision(True, 5, 2),
        kept=UNVERIFIED,
        read_once=read_then_cancel,
        parse_log=_parse,
        swap_in=lambda track, folder: True,
        cancelled=lambda: flags[0],
    )
    assert len(reads.calls) == 1
    assert run.block["outcome"] == CHASE_STOPPED


def test_a_read_that_cannot_start_stops_the_chase() -> None:
    run = run_chase(
        5,
        ChaseDecision(True, 5, 2),
        kept=UNVERIFIED,
        read_once=lambda number, folder: None,
        parse_log=_parse,
        swap_in=lambda track, folder: True,
        cancelled=lambda: False,
    )
    assert run.block["outcome"] == CHASE_STOPPED
    assert run.block["attempts"] == []


# --- The record ----------------------------------------------------------------


def test_kept_read_names_which_read_the_album_keeps() -> None:
    base = {
        "track": 5,
        "trigger": "accuraterip",
        "reripped_z": 2,
        "converged": False,
        "replaced": False,
        "replaced_because": None,
    }
    assert kept_read(base) == KEPT_FIRST_READ  # type: ignore[arg-type]  # a literal record
    assert kept_read({**base, "replaced": True}) == KEPT_SECURING_PASS  # type: ignore[arg-type]  # a literal record
    chased = {
        **base,
        "replaced": True,
        "verified_read_chase": {"kept_attempt": 2},
    }
    assert kept_read(chased) == KEPT_VERIFIED_REREAD  # type: ignore[arg-type]  # a literal record


def test_the_reports_copy_of_a_chase_block_is_not_the_workers() -> None:
    reads = _Reads([("C96464AB", 200, 0)])
    run, _swapped = _chase(reads, limit=1)
    copied = copy_chase_block(run.block)
    assert copied == run.block
    assert copied is not run.block
    assert copied is not None and copied["attempts"][0] is not run.block["attempts"][0]
    assert copy_chase_block(None) is None


def test_the_kept_chase_log_carries_argv_exit_status_and_the_log() -> None:
    section = chase_log_section(5, 2, ("cyanrip", "-l", "5"), None, "EAC CRC32: X\n")
    assert "track 5, attempt 2" in section
    assert "argv: cyanrip -l 5" in section
    assert "exit status: never reaped" in section
    assert "EAC CRC32: X" in section
    assert chase_log_path_for("/a/Album.log").name == (
        "Album.platterpus-verified-read.txt"
    )


def test_the_chase_records_argv_names_the_home_folder_as_a_tilde() -> None:
    """Run C, 2026-10-22: each attempt's argv line carried the rig's absolute home
    folder, and only the export's redaction kept it out of the bundle. The line
    is now written with ``~``, by the export's own function, at creation; the
    embedded cyanrip log, which is signed, is left exactly as the ripper wrote."""
    home = "/home/someone"
    log_text = f"cyanrip 0.9.4 (x)\nOutputs: {home}/Music\nLog FUN512: abc\n"
    section = chase_log_section(
        16,
        5,
        (f"{home}/.local/bin/cyanrip", "-l", "16", "-D", f"{home}/Music"),
        0,
        log_text,
        homes=[home],
    )
    argv_line = next(line for line in section.splitlines() if line.startswith("argv:"))
    assert argv_line == "argv: ~/.local/bin/cyanrip -l 16 -D ~/Music", argv_line
    assert log_text in section, "the signed log was altered"


# --- The fork's proposed kept-read clause (round 36 lap 4 S11) ----------------

_KEPT_LINE = (
    "Done; (repeat limit of 3 reads reached; at most 1 read agreed; kept C96464AB, "
    "read 1 time, which AccurateRip matches at confidence 200; last read 4065BECC, "
    "not kept)"
)


def test_the_proposed_kept_read_clause_is_read_with_its_last_read() -> None:
    assert secure_rerip_limit_kept_read(_KEPT_LINE) == LimitKeptRead(
        crc="C96464AB", reads=1, accuraterip_confidence=200, last_read_crc="4065BECC"
    )


def test_the_clause_without_a_last_read_means_the_last_read_was_kept() -> None:
    line = (
        "Done; (repeat limit of 3 reads reached; at most 2 reads agreed; kept "
        "c96464ab, read 2 times, which AccurateRip matches at confidence 7)"
    )
    assert secure_rerip_limit_kept_read(line) == LimitKeptRead("C96464AB", 2, 7, "")


@pytest.mark.parametrize(
    "line",
    [
        # Every released build: no clause, so nothing is claimed either way.
        "Done; (repeat limit of 3 reads reached; at most 2 reads agreed)",
        "Done; (no matches found, but hit repeat limit of 3)",
        # A converged line is not a limit verdict, whatever it carries.
        "Done; (2 out of 2 matches for current checksum C96464AB)",
        # A zero confidence or read count is not a match.
        "Done; (repeat limit of 3 reads reached; at most 1 read agreed; kept "
        "C96464AB, read 1 time, which AccurateRip matches at confidence 0)",
        "Done; (repeat limit of 3 reads reached; at most 1 read agreed; kept "
        "C96464AB, read 0 times, which AccurateRip matches at confidence 200)",
    ],
)
def test_no_clause_and_no_match_read_as_none(line: str) -> None:
    assert secure_rerip_limit_kept_read(line) is None


def test_the_clause_reaches_the_track_and_the_report() -> None:
    log = (
        "cyanrip 0.9.4 (release)\n"
        "Disc tracks:    1\n"
        f"{_KEPT_LINE}\n"
        "Track 1 read with errors.\n"
        "  EAC CRC32:     C96464AB (after 3 rips)\n"
        "Ripping errors: 0\n"
    )
    parsed = parse_cyanrip_log(log)
    (track,) = parsed.tracks
    assert track.secure_rerip_converged is False
    assert track.secure_rerip_kept_read == LimitKeptRead("C96464AB", 1, 200, "4065BECC")
    (block,) = build_report(parsed)["tracks"]
    assert block["secure_rerip_kept_read"] == {
        "crc": "C96464AB",
        "reads": 1,
        "accuraterip_confidence": 200,
        "last_read_crc": "4065BECC",
    }
