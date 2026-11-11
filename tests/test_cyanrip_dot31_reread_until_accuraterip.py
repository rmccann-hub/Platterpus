"""`.31`'s `--reread-until-accuraterip` lines, read (the fork's round 39 lap 1 S3 to S6).

**Every line below is rendered from `.31`'s own format strings**, P2 of
``docs/handshake/inbound/artifacts/round-39-lap-01-provider-contract-g6eacb8b.md``
(lines 376 and 504 to 512; source ``cyanrip@e531a33:src/cyanrip_main.c:2140``,
``:2183-2242`` and ``src/cyanrip_log.c:852``), and the first test reads those rows
out of the filed contract, so a reworded row in a later contract fails here rather
than leaving these tests to pin a wording no build prints. No `.31` log of a track
AccurateRip ended exists yet (their S5: no scenario reaches AccurateRip), so the
log around them is the hand-made `.29` shape of ``test_cyanrip_round38_wordings``.

What is held:

* the early end is a ``-Z`` verdict and NOT convergence (the fork's S6, fifth
  point: such a track "did not converge, and it did not fail"), so it is never
  left verdict-less, which the EAC-layout log would fill in as convergence, and
  never a failure sentence;
* its facts (the matched read, the confidence, the overruled agreement, the kept
  read) reach the track, joined to the row's read count;
* the clause in each of the eight limit lines is read, and each line keeps its
  limit verdict, its limit and its kept read;
* the footer is not contradicted by a track AccurateRip ended (S6, fifth point),
  and the third form S7 asks about is read;
* the per-track record says AccurateRip ended the reads, overruling the agreement.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import reread_ar_overrule as ar
from platterpus import secure_rereads_footer as footer
from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import (
    is_ripper_error_line,
    parse_cyanrip_log,
    secure_rerip_ar_overrule,
    secure_rerip_limit_kept_read,
    secure_rerip_limit_stop,
    secure_rerip_verdict_converged,
)
from platterpus.reread_limit import STOPPED_BY_REPEAT_LIMIT, STOPPED_BY_TIME_LIMIT
from platterpus.track_record import RECORD_AR_GUIDED, track_record

_CONTRACT: Final[Path] = (
    Path(__file__).resolve().parents[1]
    / "docs/handshake/inbound/artifacts/round-39-lap-01-provider-contract-g6eacb8b.md"
)

#: The early end, rendered from `cyanrip_main.c:2140`'s format: read 4 matches
#: AccurateRip at confidence 200, the agreement on 3D8FCF0C overruled, 59D352DD
#: kept, read once. Track 3 of the reference disc is the case the rule was asked
#: for (our round 38 lap 16 S13).
_EARLY_END: Final[str] = (
    "Done; (read 4 matches AccurateRip at confidence 200; agreement on 3D8FCF0C "
    "overruled by AccurateRip; kept 59D352DD, read 1 time)"
)
#: The row `cyanrip_log.c:852` prints for that track.
_ROW: Final[str] = (
    "  Secure re-read:  matched AccurateRip after 4 reads (agreement on 3D8FCF0C "
    "overruled)"
)

#: The eight limit lines with the clause, each with what it states, rendered from
#: `cyanrip_main.c:2183` to `:2242` in their order.
_LIMIT_LINES: Final[tuple[tuple[str, str, bool], ...]] = (
    (
        "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed; "
        "agreement on 3D8FCF0C overruled by AccurateRip; kept 59D352DD, read 1 time, "
        "which AccurateRip matches at confidence 200; last read 0A0B0C0D, not kept)",
        STOPPED_BY_TIME_LIMIT,
        True,
    ),
    (
        "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed; "
        "agreement on 3D8FCF0C overruled by AccurateRip; kept 59D352DD, read 1 time, "
        "which AccurateRip matches at confidence 200)",
        STOPPED_BY_TIME_LIMIT,
        True,
    ),
    (
        "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed; "
        "agreement on 3D8FCF0C overruled by AccurateRip; last read 0A0B0C0D, not kept)",
        STOPPED_BY_TIME_LIMIT,
        False,
    ),
    (
        "Done; (time limit of 600 s reached after 4 reads; at most 2 reads agreed; "
        "agreement on 3D8FCF0C overruled by AccurateRip)",
        STOPPED_BY_TIME_LIMIT,
        False,
    ),
    (
        "Done; (repeat limit of 5 reads reached; at most 2 reads agreed; agreement on "
        "3D8FCF0C overruled by AccurateRip; kept 59D352DD, read 1 time, which "
        "AccurateRip matches at confidence 200; last read 0A0B0C0D, not kept)",
        STOPPED_BY_REPEAT_LIMIT,
        True,
    ),
    (
        "Done; (repeat limit of 5 reads reached; at most 2 reads agreed; agreement on "
        "3D8FCF0C overruled by AccurateRip; kept 59D352DD, read 1 time, which "
        "AccurateRip matches at confidence 200)",
        STOPPED_BY_REPEAT_LIMIT,
        True,
    ),
    (
        "Done; (repeat limit of 5 reads reached; at most 2 reads agreed; agreement on "
        "3D8FCF0C overruled by AccurateRip; last read 0A0B0C0D, not kept)",
        STOPPED_BY_REPEAT_LIMIT,
        False,
    ),
    (
        "Done; (repeat limit of 5 reads reached; at most 2 reads agreed; agreement on "
        "3D8FCF0C overruled by AccurateRip)",
        STOPPED_BY_REPEAT_LIMIT,
        False,
    ),
)


def _format_of(line: str) -> str:
    """``line`` back to the format string it was rendered from, for the P2 check."""
    out = re.sub(r"\b[0-9A-F]{8}\b", "%08X", line)
    out = re.sub(
        r"(time limit of )\d+( s reached after )\d+( read)s", r"\1%i\2%u\3%s", out
    )
    out = re.sub(r"(repeat limit of )\d+( read)s", r"\1%i\2%s", out)
    out = re.sub(r"(at most )\d+( read)s", r"\1%i\2%s", out)
    out = re.sub(r"(read )\d+( time)(;|,|\))", r"\1%i\2%s\3", out)
    out = re.sub(r"(confidence )\d+", r"\1%i", out)
    out = re.sub(r"(read )\d+( matches)", r"\1%i\2", out)
    return re.sub(r"(after )\d+( reads)", r"\1%i\2", out)


def test_every_line_here_is_a_row_of_31s_own_contract() -> None:
    """The fixtures are `.31`'s P2 rows rendered, not our paraphrase of them."""
    contract = _CONTRACT.read_text(encoding="utf-8")
    lines = [_EARLY_END] + [line for line, _kind, _kept in _LIMIT_LINES]
    for line in lines:
        assert f"| `{_format_of(line)}` |" in contract, _format_of(line)
    assert (
        "| `Secure re-read:  matched AccurateRip after %i reads (agreement on %08X "
        "overruled)` |"
    ) in contract
    # And the option itself is in `.31`'s P1.
    assert "| none | `--reread-until-accuraterip` |" in contract


# --- the early end -----------------------------------------------------------------


def test_the_early_end_is_a_verdict_and_not_convergence() -> None:
    assert secure_rerip_verdict_converged(_EARLY_END) is False
    assert secure_rerip_verdict_converged("    " + _EARLY_END) is False
    # Never a failure sentence: the worker and the parser ask the predicate first.
    assert not is_ripper_error_line(_EARLY_END)
    # Not a limit line: none of the limit readers claims it.
    assert secure_rerip_limit_stop(_EARLY_END) is None
    assert secure_rerip_limit_kept_read(_EARLY_END) is None


def test_the_early_end_states_its_facts() -> None:
    found = secure_rerip_ar_overrule(_EARLY_END)
    assert found == ar.AccurateRipOverrule(
        overruled_crc="3D8FCF0C",
        ended_on_match=True,
        matched_read=4,
        confidence=200,
        kept_crc="59D352DD",
        kept_reads=1,
    )
    # A zero confidence or read number is not AccurateRip vouching for a read.
    assert ar.early_end(_EARLY_END.replace("confidence 200", "confidence 0")) is None
    assert ar.early_end(_EARLY_END.replace("read 4 matches", "read 0 matches")) is None


def test_the_row_joins_the_early_end_and_adds_the_read_count() -> None:
    row = ar.row_overrule(_ROW.split("Secure re-read:", 1)[1])
    assert row is not None and row.reads == 4 and row.ended_on_match
    joined = ar.combined(ar.early_end(_EARLY_END), row)
    assert (joined.matched_read, joined.confidence, joined.reads) == (4, 200, 4)
    assert joined.kept_crc == "59D352DD"
    # A row naming a different agreement stands alone, never joined.
    other = ar.row_overrule(
        "matched AccurateRip after 4 reads (agreement on 11111111 overruled)"
    )
    assert other is not None
    assert ar.combined(ar.early_end(_EARLY_END), other) == other


# --- the eight limit lines -----------------------------------------------------------


@pytest.mark.parametrize(("line", "kind", "kept"), _LIMIT_LINES)
def test_each_limit_line_keeps_its_verdict_and_names_the_overrule(
    line: str, kind: str, kept: bool
) -> None:
    assert secure_rerip_verdict_converged(line) is False
    stop = secure_rerip_limit_stop(line)
    assert stop is not None and stop.kind == kind
    kept_read = secure_rerip_limit_kept_read(line)
    assert (kept_read is not None) is kept
    if kept_read is not None:
        assert (kept_read.crc, kept_read.accuraterip_confidence) == ("59D352DD", 200)
    found = secure_rerip_ar_overrule(line)
    assert found == ar.AccurateRipOverrule(
        overruled_crc="3D8FCF0C", ended_on_match=False
    )


def test_a_limit_line_without_the_clause_names_no_overrule() -> None:
    """Every build before `.31`: an absence, never "AccurateRip overruled nothing"."""
    assert (
        secure_rerip_ar_overrule(
            "Done; (repeat limit of 5 reads reached; at most 2 reads agreed)"
        )
        is None
    )
    assert (
        secure_rerip_ar_overrule(
            "Done; (2 out of 2 matches for current checksum 07B89F6F)"
        )
        is None
    )


# --- a whole log -------------------------------------------------------------------


def _log(*, done: str = _EARLY_END, row: str = _ROW, secure: str = "") -> str:
    """A hand-made `.31` log of track 3 of a 3-track disc, under `-Z 2`."""
    return f"""cyanrip 0.9.4-rc3+platterpus.31 (platterpus-fork-ge531a33)
Invoked as:     cyanrip -d /dev/sr0 -N -Z 2 -G -U -W -l 3 --reread-until-accuraterip 2
Disc tracks:    3
Tracks to rip:  3
DiscID:         oMp2k.ixH0QqrdaZzsARoRS.p6c-

Tracks:

Repeating ripping (0 out of 2 matches for current checksum 3D8FCF0C)
Repeating ripping (1 out of 2 matches for current checksum 3D8FCF0C)
Repeating ripping (2 out of 2 matches for current checksum 3D8FCF0C)
{done}
Track 3 read with no error reported.
Summary:

  Properties:
    Start LSN:   525
    End LSN:     599

  EAC CRC32:     59D352DD (after 4 rips)
{row}
  Accurip:       disc found in database (max confidence: 200)
    Accurip v1:  CEDEB120 (accurately ripped, confidence 200)
    Accurip v2:  E856170A (accurately ripped, confidence 200)

  Metadata:
    TRACK:                         3

  File(s):
    o/3.flac

Tracks ripped accurately: 1/1

{secure}
Ripping errors: 0
Rip completed:  yes (1 of 3 tracks)
"""


def test_a_track_accuraterip_ended_says_so_and_does_not_converge() -> None:
    parsed = parse_cyanrip_log(_log())
    (three,) = [t for t in parsed.tracks if t.number == 3]
    assert three.secure_rerip_converged is False
    assert three.secure_rerip_limit_stop is None
    assert three.secure_rerip_ar_overrule == ar.AccurateRipOverrule(
        overruled_crc="3D8FCF0C",
        ended_on_match=True,
        matched_read=4,
        confidence=200,
        kept_crc="59D352DD",
        kept_reads=1,
        reads=4,
    )
    assert ar.ended_on_accuraterip(three)


def test_the_record_says_accuraterip_ended_the_reads() -> None:
    parsed = parse_cyanrip_log(_log())
    (three,) = [t for t in parsed.tracks if t.number == 3]
    record = track_record(three, ripper_version=parsed.log_creator)
    assert record.kind == RECORD_AR_GUIDED
    assert record.line.startswith(
        "re-read: matched AccurateRip at confidence 200 after 4 reads, overruling an "
        "agreement on 3D8FCF0C (kept 59D352DD, from read 4); verified by AccurateRip"
    ), record.line
    # The reads did disagree: an agreement on one value, a kept read of another.
    assert record.reads_disagree is True
    assert "not determined" not in record.line


def test_a_31_track_the_rule_did_not_end_carries_no_caveat() -> None:
    """`.31` is a build we read, so its silence is a statement, not a gap."""
    converged = _log(
        done="Done; (2 out of 2 matches for current checksum 59D352DD)",
        row="  Secure re-read:  converged after 3 reads",
    )
    parsed = parse_cyanrip_log(converged)
    (three,) = [t for t in parsed.tracks if t.number == 3]
    record = track_record(three, ripper_version=parsed.log_creator)
    assert record.kind != RECORD_AR_GUIDED
    assert "not determined" not in record.line
    # A build after `.31` we have not read keeps the caveat.
    later = track_record(three, ripper_version="cyanrip 0.9.4-rc3+platterpus.32")
    assert "not determined" in later.line


def test_a_limit_after_an_overrule_is_named_in_the_record() -> None:
    line, _kind, _kept = _LIMIT_LINES[5]  # repeat limit, kept for AccurateRip
    parsed = parse_cyanrip_log(
        _log(
            done=line,
            row="  Secure re-read:  did NOT converge after 5 reads (repeat limit hit)",
        )
    )
    (three,) = [t for t in parsed.tracks if t.number == 3]
    assert three.secure_rerip_ar_overrule is not None
    assert not three.secure_rerip_ar_overrule.ended_on_match
    record = track_record(three, ripper_version=parsed.log_creator)
    assert record.line.endswith(
        "an agreement on 3D8FCF0C was overruled by AccurateRip"
    ), record.line


# --- the footer --------------------------------------------------------------------


def test_the_footer_does_not_count_a_track_accuraterip_ended() -> None:
    """S6, fifth point: `.31` prints neither form; a footer naming the OTHER tracks
    is not contradicted by one AccurateRip ended."""
    parsed = parse_cyanrip_log(_log(secure="Secure re-reads: every track converged"))
    (three,) = [t for t in parsed.tracks if t.number == 3]
    assert footer._blocks_not_converged([three]) == set()
    # Non-triviality: the same track read as a plain limit IS counted.
    plain = parse_cyanrip_log(
        _log(
            done="Done; (repeat limit of 5 reads reached; at most 2 reads agreed)",
            row="  Secure re-read:  did NOT converge after 5 reads (repeat limit hit)",
        )
    )
    (limited,) = [t for t in plain.tracks if t.number == 3]
    assert footer._blocks_not_converged([limited]) == {3}


def test_the_third_form_s7_asks_about_is_read() -> None:
    read = footer.read_value("every track converged or matched AccurateRip")
    assert read.state == footer.ALL_CONVERGED_OR_MATCHED
    assert read.count == 0 and read.tracks == ()
    parsed = parse_cyanrip_log(
        _log(secure="Secure re-reads: every track converged or matched AccurateRip")
    )
    assert parsed.secure_rereads is not None
    assert parsed.secure_rereads.state == footer.ALL_CONVERGED_OR_MATCHED
    block = footer.report_block(parsed.secure_rereads, parsed.tracks)
    assert block is not None and block["agrees_with_track_blocks"] is True


# --- never raises --------------------------------------------------------------------


_TEXT = st.text(
    alphabet=st.sampled_from(
        list("Done;(readmatchesAccurateRipconfidence0123456789ABCDEF ,)")
    ),
    max_size=200,
)


@settings(max_examples=300, deadline=None)
@given(st.one_of(_TEXT, st.text(max_size=300)))
def test_the_readers_never_raise(text: str) -> None:
    ar.early_end(text)
    ar.limit_overrule(text)
    ar.row_overrule(text)
    secure_rerip_ar_overrule(text)
    secure_rerip_verdict_converged(text)


@settings(max_examples=200, deadline=None)
@given(
    st.integers(min_value=-5, max_value=10**7),
    st.integers(min_value=-5, max_value=10**7),
    st.integers(min_value=-5, max_value=10**7),
)
def test_the_early_end_never_raises_on_any_number(
    read: int, conf: int, reads: int
) -> None:
    line = (
        f"Done; (read {read} matches AccurateRip at confidence {conf}; agreement on "
        f"3D8FCF0C overruled by AccurateRip; kept 59D352DD, read {reads} times)"
    )
    found = ar.early_end(line)
    if found is not None:
        assert found.matched_read and found.confidence and found.kept_reads


def test_the_readers_take_only_strings_without_raising() -> None:
    for value in (None, 3, b"Done;", object()):
        assert ar.early_end(value) is None  # type: ignore[arg-type]  # deliberately wrong type
        assert ar.limit_overrule(value) is None  # type: ignore[arg-type]  # deliberately wrong type
        assert ar.row_overrule(value) is None  # type: ignore[arg-type]  # deliberately wrong type


def test_the_early_end_is_listed_where_the_consumer_contract_reads_it() -> None:
    names = {name for name, _pattern in cyanrip_log._SECTION_LINE_PATTERNS}
    assert "secure_rerip_accuraterip_matched" in names


def test_the_merge_carries_the_overrule_with_the_shipped_read() -> None:
    """A securing read swapped in brings its own overrule; nothing else keeps one."""
    from dataclasses import replace

    from platterpus.ui.main_window_rip import _merge_shipped_track

    parsed = parse_cyanrip_log(_log())
    (shipped,) = [t for t in parsed.tracks if t.number == 3]
    first_pass = replace(
        shipped, secure_rerip_ar_overrule=None, secure_rerip_converged=None
    )
    merged = _merge_shipped_track(first_pass, shipped, {3: False})
    assert merged.secure_rerip_ar_overrule == shipped.secure_rerip_ar_overrule
    # Re-read and not swapped in: the first pass had none, and gets none.
    assert (
        _merge_shipped_track(first_pass, None, {3: False}).secure_rerip_ar_overrule
        is None
    )
    # A chase read (one read, no -Z) carries no -Z fact at all.
    single = _merge_shipped_track(first_pass, shipped, {}, single_read=True)
    assert single.secure_rerip_ar_overrule is None


def test_the_row_alone_is_never_read_as_convergence() -> None:
    """The row decides on its own: a log whose early end went unread (a reworded
    head, a cut log) still files the track as not converged, never converged."""
    text = _ROW.split("Secure re-read:", 1)[1]
    assert cyanrip_log._parse_secure_verdict(text) is False
    parsed = parse_cyanrip_log(_log(done="Done; (a head this build does not print)"))
    (three,) = [t for t in parsed.tracks if t.number == 3]
    assert three.secure_rerip_converged is False
    assert three.secure_rerip_ar_overrule is not None
    assert three.secure_rerip_ar_overrule.reads == 4
