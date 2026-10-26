"""`.27`'s `Pregap search:` line, read into the parse, the report and the results.

The fork's round 36 lap 8 S21 says it is built: for every track a sub-channel
pre-gap search ran on, found or not, one track-block line below `Pregap source:`
(or below `Pregap LSN:` when no source is printed) saying what the search saw
(`cyanrip@b2ffd42:src/cyanrip_log.c:476-489`; their P2 row
`cyanrip@b2ffd42:PROVIDER-CONTRACT.md:300`). It exists because
`unknown (sub-channel CRC mismatches)` was printed whatever stopped the search,
frames that passed their CRC and answered for another sector included, and the
reference disc's track 9 read 95 or unknown on `.26` where `.25` and EAC read 94
(their S5). Only the counts tell the causes apart.

**Where the line comes from.** `cyanrip_fork_golden_reference_r36l8.log` is
`cyanrip@22af58e:docs/golden-reference.log` byte for byte (sha256 below), the
reference the fork regenerated for lap 8 from their build `platterpus-fork-gdbc49d9`.
It carries the line once, on track 3, whose image pre-gap the search could not
read. Every other shape is the source's format string, copied from their P2 row,
filled in by Python's `%`, which formats `%i`, `%+i` and `%s` as C's printf does.
`cyanrip_fork_golden_reference_r36l7.log` is the build before, which prints none.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import pregap_search
from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.pregap_search import PregapSearch, describe, read_search
from platterpus.rip_audit import LEVEL_NOTE, audit_album
from platterpus.rip_report import build_report

_FIXTURES = Path(__file__).parent / "fixtures"
#: `cyanrip@22af58e:docs/golden-reference.log`, verbatim.
_R36L8_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r36l8.log"
_R36L8_SHA256 = "13e1288cc4447c2ee2d134865b4fa30a1c998150766ddda62a8cef0b9d75c2d1"
#: The previous `.27` reference (lap 7), which prints no `Pregap search:` line.
_R36L7_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r36l7.log"

#: Their P2 row (`cyanrip@b2ffd42:PROVIDER-CONTRACT.md:300`), copied rather than
#: built from our pattern, with the source's four-space indent
#: (`cyanrip@b2ffd42:src/cyanrip_log.c:483`), which P2 records without it.
_P2_SEARCH = (
    "    Pregap search: %i sectors asked; %i reads failed the CRC; %i sectors gave "
    "no frame passing it; %i frames were another sector's; %i had no address; "
    "frames answer %+i sectors off%s%s"
)
#: The two optional clauses, as the source builds them (`:478-487`).
_HARDER = "; 200-retry pass ran"
_UNDECIDED = "; LSN %i to %i undecided"

#: Track 3's line in the golden reference, as printed.
_GOLDEN_LINE = (
    "    Pregap search: 1 sectors asked; 0 reads failed the CRC; 0 sectors gave no "
    "frame passing it; 0 frames were another sector's; 0 had no address; frames "
    "answer +0 sectors off; LSN 376 to 524 undecided"
)


def _golden() -> str:
    text = _R36L8_LOG.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == _R36L8_SHA256
    return text


def _line(
    *counts: int, harder: bool = False, undecided: tuple[int, int] | None = None
) -> str:
    tail = _UNDECIDED % undecided if undecided is not None else ""
    return _P2_SEARCH % (*counts, _HARDER if harder else "", tail)


def _with_line(line: str) -> str:
    """The golden reference with track 3's search line replaced by ``line``."""
    text = _golden()
    assert text.count(_GOLDEN_LINE + "\n") == 1  # floor: the anchor is there, once
    return text.replace(_GOLDEN_LINE + "\n", line + "\n")


# --- the reference as published ---------------------------------------------------


def test_the_line_sits_below_the_unknown_pregap_lsn_of_track_3() -> None:
    """Where the source prints it when no `Pregap source:` line is printed."""
    lines = _golden().splitlines()
    found = [i for i, line in enumerate(lines) if line.startswith("    Pregap search:")]
    assert len(found) == 1  # floor: the line is there, once
    assert lines[found[0]] == _GOLDEN_LINE
    assert lines[found[0] - 1] == "    Pregap LSN:  unknown (sub-channel unreadable)"


def test_the_golden_line_is_the_p2_format_filled_in() -> None:
    """Our copy of their format string reproduces their own artifact's line."""
    assert _line(1, 0, 0, 0, 0, 0, undecided=(376, 524)) == _GOLDEN_LINE


def test_the_reference_parses_to_the_search_on_track_3_alone() -> None:
    log = parse_cyanrip_log(_golden())
    assert [t.number for t in log.tracks] == [1, 2, 3]  # floor: the whole log
    assert [t.pregap_search for t in log.tracks[:2]] == [None, None]
    assert log.tracks[2].pregap_state == "unknown"
    assert log.tracks[2].pregap_search == PregapSearch(
        asked=1,
        crc_failed=0,
        no_frame=0,
        elsewhere=0,
        no_address=0,
        shift=0,
        harder_pass_ran=False,
        undecided_from=376,
        undecided_to=524,
    )


def test_the_report_carries_the_search_per_track_and_null_without_a_line() -> None:
    rows = build_report(parse_cyanrip_log(_golden()))["tracks"]
    assert len(rows) == 3
    assert [r["pregap_search"] for r in rows[:2]] == [None, None]
    block = rows[2]["pregap_search"]
    assert block is not None
    assert block["state"] == pregap_search.READ
    assert (block["asked"], block["crc_failed"], block["elsewhere"]) == (1, 0, 0)
    assert (block["undecided_from"], block["undecided_to"]) == (376, 524)
    assert block["unrecognised"] is None
    assert "LSN 376 to 524 undecided" in block["summary"]


def test_a_build_without_the_line_reports_null_never_a_clean_search() -> None:
    log = parse_cyanrip_log(_R36L7_LOG.read_text(encoding="utf-8"))
    assert len(log.tracks) == 3
    assert [t.pregap_search for t in log.tracks] == [None, None, None]
    rows = build_report(log)["tracks"]
    assert [r["pregap_search"] for r in rows] == [None, None, None]


# --- every line of the reference is accounted for --------------------------------

#: Indented rows of the reference no pattern claims, each a decision: the loudness
#: summary and the `Properties:` rows the report does not carry, the tag dump's
#: rows, and the `Consumer:` line's continuation. A label not in this set fails
#: the test below, so a new line in a regenerated reference is seen, not skimmed.
_SKIMMED_LABELS: frozenset[str] = frozenset(
    {
        "Integrated loudness",
        "Threshold",
        "Loudness range",
        "LRA low",
        "LRA high",
        "Properties",
        "Duration",
        "Samples",
        "Frames",
        "True peak level",
        "Integrated loudness (R128)",
        "Loudness range (R128)",
        "Metadata",
        "MUSICBRAINZ_DISCID",
        "MEDIA",
        "COMMENT",
        "ALBUM",
        "TITLE",
        "ISRC",
        "CREATION_TIME",
        "(reported by the caller, not verified by cyanrip)",
    }
)


def test_every_top_level_line_of_the_reference_is_accounted_for(
    caplog: pytest.LogCaptureFixture,
) -> None:
    lines = _golden().splitlines()
    top_level = [line for line in lines if line and not line[0].isspace()]
    assert len(top_level) >= 40  # floor
    unaccounted = [
        line
        for line in top_level
        if not any(rule.pattern.match(line) for rule in cyanrip_log._ALL_LINE_RULES)
        and not any(p.match(line) for _, p in cyanrip_log._SECTION_LINE_PATTERNS)
        and not cyanrip_log._is_ignored_disc_line(line)
    ]
    assert unaccounted == []
    # And the parser itself, which logs every top-level line it neither parses
    # nor ignores on purpose, logs none.
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parse_cyanrip_log("\n".join(lines))
    assert not [r for r in caplog.records if "unrecognised top-level" in r.message]


def test_every_track_block_line_of_the_reference_is_accounted_for() -> None:
    """Every indented line is claimed by a listed pattern, or is a path under
    `File(s):`, a line of the `Gaps:` block, or a label skimmed on purpose."""
    classifiers = [
        pattern
        for name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS
        if name != "gaps_value"  # "any indented line": it would claim everything
    ] + [rule.pattern for rule in cyanrip_log._ALL_LINE_RULES]
    residue: list[str] = []
    examined = 0
    block = ""
    for line in _golden().splitlines():
        if line and not line[0].isspace():
            block = line.rstrip(":") if line.endswith(":") else ""
            continue
        if not line.strip():
            continue
        examined += 1
        stripped = line.strip()
        if (
            stripped.endswith(":")
            and line.startswith("  ")
            and not line.startswith("    ")
        ):
            block = stripped[:-1]
        if any(pattern.match(line) for pattern in classifiers):
            continue
        if block in {"Gaps", "File(s)"}:
            continue  # read by the `Gaps:` block reader and the `File(s):` lookahead
        label = stripped.split(":")[0] if ":" in stripped else stripped
        if label not in _SKIMMED_LABELS:
            residue.append(line)
    assert examined >= 150, examined  # floor: three track blocks and the header
    assert residue == []
    # The new line is claimed, and by its own pattern alone.
    claimed = [
        name
        for name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS
        if name != "gaps_value" and pattern.match(_GOLDEN_LINE)
    ]
    assert claimed == ["track_pregap_search"]


# --- every shape the source can print ------------------------------------------


#: Each shape the source can print, filled from their P2 format string by `_line`.
#: Built at import, so `test_the_case_tables_are_populated` floors it.
_SHAPES: list[tuple[str, PregapSearch]] = [
    # Their lap 8 S21's example: a found pre-gap, misplaced frames counted.
    (
        _line(37, 2, 0, 3, 0, 0),
        PregapSearch(37, 2, 0, 3, 0, 0, False, None, None),
    ),
    (
        _line(37, 2, 1, 3, 4, -2, harder=True),
        PregapSearch(37, 2, 1, 3, 4, -2, True, None, None),
    ),
    (
        _line(200, 0, 0, 12, 0, 1, harder=True, undecided=(16_800, 16_906)),
        PregapSearch(200, 0, 0, 12, 0, 1, True, 16_800, 16_906),
    ),
    (
        _line(5, 5, 5, 0, 0, 0, undecided=(-150, -1)),
        PregapSearch(5, 5, 5, 0, 0, 0, False, -150, -1),
    ),
]


@pytest.mark.parametrize(
    ("line", "expected"),
    _SHAPES,
    ids=["found", "harder-pass", "both-clauses", "negative-lsn"],
)
def test_each_shape_of_the_line_is_read(line: str, expected: PregapSearch) -> None:
    track = parse_cyanrip_log(_with_line(line)).tracks[2]
    assert track.pregap_search == expected


@settings(max_examples=150, deadline=None)
@given(
    st.lists(st.integers(0, 999_999_999), min_size=5, max_size=5),
    st.integers(-999_999_999, 999_999_999),
    st.booleans(),
    st.none()
    | st.tuples(st.integers(-999_999, 999_999), st.integers(-999_999, 999_999)),
)
def test_any_line_the_source_can_print_is_read_exactly(
    counts: list[int], shift: int, harder: bool, undecided: tuple[int, int] | None
) -> None:
    line = _line(*counts, shift, harder=harder, undecided=undecided)
    search = read_search(line.split("Pregap search:", 1)[1])
    assert search.state == pregap_search.READ, line
    assert [
        search.asked,
        search.crc_failed,
        search.no_frame,
        search.elsewhere,
        search.no_address,
    ] == counts
    assert (search.shift, search.harder_pass_ran) == (shift, harder)
    assert (search.undecided_from, search.undecided_to) == (undecided or (None, None))


# --- a wording we do not read -------------------------------------------------


#: Values in wordings this version does not read, one per way a reword can look.
_VARIANTS: list[str] = [
    # One word changed: a future build's reword.
    "37 sectors asked; 2 reads failed the checksum; 0 sectors gave no frame "
    "passing it; 3 frames were another sector's; 0 had no address; frames "
    "answer +0 sectors off",
    # A clause we have never seen appended.
    _line(1, 0, 0, 0, 0, 0).split("Pregap search: ", 1)[1] + "; 3 drives agreed",
    # The shift without its sign, which `%+i` always prints.
    "1 sectors asked; 0 reads failed the CRC; 0 sectors gave no frame passing "
    "it; 0 frames were another sector's; 0 had no address; frames answer 0 "
    "sectors off",
    "a sentence about something else",
]


def test_the_case_tables_are_populated() -> None:
    """The floor for the two parametrized tables above and below (they are built
    by calls, so an empty table would generate no cases and pass)."""
    assert len(_SHAPES) >= 4
    assert len(_VARIANTS) >= 4
    assert len({line for line, _ in _SHAPES}) == len(_SHAPES)


@pytest.mark.parametrize(
    "value",
    _VARIANTS,
    ids=["reworded", "new-clause", "unsigned-shift", "other"],
)
def test_a_variant_wording_is_kept_verbatim_never_dropped(
    value: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="platterpus.parsers.cyanrip_log"):
        log = parse_cyanrip_log(_with_line("    Pregap search: " + value))
    search = log.tracks[2].pregap_search
    assert search is not None
    assert search.state == pregap_search.UNRECOGNISED
    assert search.unrecognised == value
    assert search.asked is None and search.elsewhere is None
    assert any("unrecognised Pregap search" in r.getMessage() for r in caplog.records)
    block = build_report(log)["tracks"][2]["pregap_search"]
    assert block is not None
    assert (block["state"], block["unrecognised"], block["asked"]) == (
        pregap_search.UNRECOGNISED,
        value,
        None,
    )
    assert value in block["summary"]


def test_an_absurd_value_is_bounded_with_its_cut_counted() -> None:
    value = "9" * 5000 + " sectors asked END"
    search = read_search(value)
    assert search.state == pregap_search.UNRECOGNISED
    assert search.unrecognised.endswith("END")
    assert "character(s) omitted" in search.unrecognised
    assert len(search.unrecognised) < 400


def test_control_characters_in_a_variant_are_screened_visible() -> None:
    search = read_search("1 sectors asked\x1b[2J; \x00")
    assert search.state == pregap_search.UNRECOGNISED
    assert "\x1b" not in search.unrecognised and "\x00" not in search.unrecognised
    assert "\\x1b" in search.unrecognised and "\\x00" in search.unrecognised


# --- what a person reads --------------------------------------------------------


def test_the_summary_names_the_counts_that_tell_the_causes_apart() -> None:
    misplaced = describe(PregapSearch(37, 0, 0, 3, 0, 0, True, 16_800, 16_906))
    assert misplaced == (
        "37 sectors asked; 0 reads failed the CRC; 3 frames answered for another "
        "sector; the 200-retry pass ran; LSN 16800 to 16906 undecided"
    )
    failing = describe(PregapSearch(37, 2, 1, 0, 4, -1, False, None, None))
    assert failing == (
        "37 sectors asked; 2 reads failed the CRC; 0 frames answered for another "
        "sector; 1 sector gave no frame passing the CRC; 4 frames had no address; "
        "frames answered -1 sectors off"
    )
    assert describe(None) == ""


def _audit_report(tmp_path: Path, report: dict[str, Any]) -> Path:
    """``report`` written as an album's ``.platterpus.json``, as `audit_album`
    reads one (the same name `tests/test_rip_audit.py` writes)."""
    import json

    folder = tmp_path / "album"
    folder.mkdir()
    path = folder / "Album.platterpus.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_the_audit_names_the_counts_beside_an_unknown_pregap(tmp_path: Path) -> None:
    """The results say why a pre-gap is unknown, not only that it is."""
    report = build_report(
        parse_cyanrip_log(_with_line(_line(37, 0, 0, 3, 0, 0, undecided=(10, 20))))
    )
    album = audit_album(_audit_report(tmp_path, report))
    notes = [
        f.text for f in album.findings if f.level == LEVEL_NOTE and "track 3" in f.text
    ]
    assert notes == [
        "track 3: pre-gap unknown (sub-channel unreadable); the sub-channel search: "
        "37 sectors asked; 0 reads failed the CRC; 3 frames answered for another "
        "sector; LSN 10 to 20 undecided"
    ]


# --- never raises ---------------------------------------------------------------


@given(st.text(max_size=300))
def test_the_parser_never_raises_on_any_value(value: str) -> None:
    parse_cyanrip_log(
        _with_line("    Pregap search: " + value.replace("\n", " ").replace("\r", " "))
    )


@given(st.one_of(st.text(max_size=500), st.integers(), st.none(), st.floats()))
def test_the_reader_never_raises_and_never_invents_a_count(value: object) -> None:
    search = read_search(value)
    assert search.state in {pregap_search.READ, pregap_search.UNRECOGNISED}
    if search.state == pregap_search.UNRECOGNISED:
        assert (
            search.asked is None and search.elsewhere is None and search.shift is None
        )
    describe(search)
    pregap_search.report_block(search)
