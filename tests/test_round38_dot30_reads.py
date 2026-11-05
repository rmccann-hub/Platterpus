"""`.30`'s additions, read before a release of ours names it (our round 38 lap 9 S10).

The fork's round 38 lap 8 S16 and S17 built three things a release of ours promised
to read first: the track block's ``  Other read:`` line, the ``-j`` record's
per-track ``reads`` at ``cyanrip-diagnostics/13``, and its top-level
``drive_declared``. **Every form here is taken from their tree at ``40dc64d7``,
not from the lap's prose:**

* the ``Other read:`` lines are the ones their source can print
  (``cyanrip@40dc64d7:src/cyanrip_log.c:856-896``), the second arm word for word
  as their own test builds it (``cyanrip@40dc64d7:tests/rip_images.py:8970-8972``)
  and the line their lap 8 S16 quotes;
* the ``/13`` record is their golden reference, byte for byte
  (``tests/fixtures/cyanrip_fork_diagnostics13_golden.json``);
* the ``reads`` and ``drive_declared`` shapes no image can reach are rebuilt from
  the strings their unit test expects (``cyanrip@40dc64d7:tests/diagrecord.c:
  390-480``), since only a drive answers and none has run it yet.

And the other direction: a ``.29``-shaped log and a ``/12`` record read exactly as
before, every new field "not present", never a negative.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from hypothesis import given, settings
from hypothesis import strategies as st
from test_cyanrip_round38_wordings import _log as _dot29_log

from platterpus import other_reads as other
from platterpus import record_drive_declared as declared
from platterpus import record_reads as reads
from platterpus.error_positions import report_block as error_positions_block
from platterpus.isrc_provenance import parse_isrcs
from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report
from platterpus.ripper_ending import STATE_READ

_FIXTURES: Final[Path] = Path(__file__).parent / "fixtures"
_GOLDEN_13: Final[Path] = _FIXTURES / "cyanrip_fork_diagnostics13_golden.json"
_RECORD_10: Final[Path] = _FIXTURES / "cyanrip_fork_diagnostics10_interrupted.json"
_LOG_26: Final[Path] = _FIXTURES / "cyanrip_fork_golden_reference_r36l8.log"

#: Their lap 8 S16's line, word for word.
_LAP_LINE: Final[str] = (
    "  Other read:      2FFECF45, read 1 time, differs from the kept read in "
    "second 1 (00:01); saved as reads/01-2FFECF45.wav"
)
#: Their first arm (`cyanrip@40dc64d7:src/cyanrip_log.c:876`), read twice.
_NOT_KNOWN_LINE: Final[str] = (
    "  Other read:      0BADF00D, read 2 times, differs from the kept read; which "
    "seconds is not known (per-second CRCs not kept)"
)


def _rip_images_line(crc: str, n: int, path: str | None) -> str:
    """The line `cyanrip@40dc64d7:tests/rip_images.py:8970-8972` builds."""
    return (
        f"  Other read:      {crc}, read {n} time{'' if n == 1 else 's'}, "
        f"differs from the kept read in second 1 (00:01)"
        + (f"; saved as {path}" if path else "")
    )


def _with_lines(lines: list[str], *, after_echo: bool = False) -> str:
    """The `.26` golden log with `lines` put where `.30` prints them in track 1.

    After `Secure re-read:` and before `Accurip:` (their source), or, with
    `after_echo`, inside the `Metadata:` echo, where cyanrip never prints one.
    """
    text = _LOG_26.read_text(encoding="utf-8")
    anchor = (
        "  Metadata:\n"
        if after_echo
        else "  Secure re-read:  converged after 3 reads\n"
    )
    at = text.index(anchor) + len(anchor)
    return text[:at] + "".join(line + "\n" for line in lines) + text[at:]


# --- the log line -----------------------------------------------------------------


def test_the_lap_s_line_is_read_whole() -> None:
    read = other.read_other_read(_LAP_LINE.split("Other read:", 1)[1].strip())
    assert read.state == other.READ
    assert (read.crc, read.count, read.where) == ("2FFECF45", 1, other.WHERE_SECONDS)
    assert read.seconds == (1,) and read.seconds_not_named == 0
    assert read.seconds_differing == 1
    assert read.file == "reads/01-2FFECF45.wav"


def test_every_arm_the_source_can_print() -> None:
    not_known = other.read_other_read(_NOT_KNOWN_LINE.split("Other read:", 1)[1])
    assert (not_known.state, not_known.where, not_known.count) == (
        other.READ,
        other.WHERE_NOT_KNOWN,
        2,
    )
    assert not_known.seconds_differing is None and not_known.file is None
    # Nine differ: eight named, the ninth counted (`:882`, `:888-889`).
    named = ", ".join(
        f"{j} ({j // 60:02d}:{j % 60:02d})" for j in (0, 1, 2, 59, 60, 61, 119, 3599)
    )
    many = other.read_other_read(
        f"12345678, read 3 times, differs from the kept read in seconds {named}, and 1 more"
    )
    assert many.where == other.WHERE_SECONDS
    assert many.seconds == (0, 1, 2, 59, 60, 61, 119, 3599)
    assert many.seconds_differing == 9
    # Their print buffer incomplete: `where` is empty, the rest still read.
    empty = other.read_other_read(
        "12345678, read 1 time, ; saved as /x/01-12345678.wav"
    )
    assert (empty.where, empty.file) == (other.WHERE_NOT_STATED, "/x/01-12345678.wav")


def test_a_line_that_breaks_its_own_grammar_is_unrecognised_never_half_read() -> None:
    # `time` is singular exactly when read once.
    assert other.read_other_read("12345678, read 1 times, ").state == other.UNRECOGNISED
    assert other.read_other_read("12345678, read 2 time, ").state == other.UNRECOGNISED
    assert other.read_other_read("1234567, read 1 time, ").state == other.UNRECOGNISED
    for where in (
        "differs from the kept read in second 1 (00:02)",  # mm:ss not its own
        "differs from the kept read in seconds 2 (00:02), 1 (00:01)",  # order
        "differs from the kept read in seconds 1 (00:01), and 3 more",  # < 8 named
        "differs from the kept read in seconds 1 (00:01)",  # plural for one
        "differs from the kept read somewhere",
    ):
        read = other.read_other_read(f"12345678, read 1 time, {where}")
        assert (read.state, read.where) == (other.READ, other.UNRECOGNISED), where
        assert read.seconds == () and read.seconds_differing is None


def test_the_lines_reach_the_track_and_the_report_beside_the_kept_read() -> None:
    log = parse_cyanrip_log(
        _with_lines([_NOT_KNOWN_LINE, _rip_images_line("2FFECF45", 1, None), _LAP_LINE])
    )
    assert len(log.tracks) == 3  # floor: the whole log was read
    first = log.tracks[0]
    assert [r.crc for r in first.other_reads] == ["0BADF00D", "2FFECF45", "2FFECF45"]
    assert first.copy_crc == "D36D9296"  # the kept read is untouched
    assert first.secure_rerip_converged is True
    assert [t.other_reads for t in log.tracks[1:]] == [(), ()]
    rows = build_report(log)["tracks"]
    block = rows[0]["other_reads"]
    assert block is not None and block["not_kept"] == 0
    assert [e["differs"] for e in block["reads"]] == ["not_known", "seconds", "seconds"]
    assert block["reads"][2] == {
        "state": "read",
        "crc": "2FFECF45",
        "count": 1,
        "differs": "seconds",
        "differing_seconds": [1],
        "differing_seconds_not_named": 0,
        "differing_seconds_total": 1,
        "file": "reads/01-2FFECF45.wav",
        "text": _LAP_LINE.split("Other read:", 1)[1].strip(),
    }
    assert rows[1]["other_reads"] is None and rows[2]["other_reads"] is None


def test_an_other_read_line_inside_the_echo_is_refused() -> None:
    """Printed before `Metadata:` in every build, so after it it is an echoed value."""
    log = parse_cyanrip_log(_with_lines([_LAP_LINE], after_echo=True))
    assert len(log.tracks) == 3
    assert log.tracks[0].other_reads == ()


def test_many_lines_keep_their_head_and_tail_and_count_the_middle() -> None:
    lines = [_rip_images_line(f"{n:08X}", 1, None) for n in range(100)]
    log = parse_cyanrip_log(_with_lines(lines))
    kept = log.tracks[0].other_reads
    assert len(kept) == other.KEEP_HEAD + other.KEEP_TAIL
    assert log.tracks[0].other_reads_not_kept == 100 - len(kept)
    assert kept[0].crc == "00000000" and kept[-1].crc == f"{99:08X}"
    assert kept[other.KEEP_HEAD].crc == f"{100 - other.KEEP_TAIL:08X}"


def test_the_line_is_claimed_by_its_listed_pattern_and_no_other() -> None:
    """The enumeration the generated consumer contract publishes lists it."""
    patterns = dict(cyanrip_log._INDENTED_LINE_PATTERNS)
    assert patterns["track_other_read"].match(_LAP_LINE)
    others = [
        name
        for name, pattern in cyanrip_log._INDENTED_LINE_PATTERNS
        if name not in {"track_other_read", "gaps_value"} and pattern.match(_LAP_LINE)
    ]
    assert others == []


def test_a_dot29_log_reads_as_before() -> None:
    for text in (_dot29_log(), _LOG_26.read_text(encoding="utf-8")):
        log = parse_cyanrip_log(text)
        assert len(log.tracks) >= 2  # floor
        assert all(
            t.other_reads == () and t.other_reads_not_kept == 0 for t in log.tracks
        )
        assert all(row["other_reads"] is None for row in build_report(log)["tracks"])


@settings(max_examples=300, deadline=None)
@given(st.text(max_size=300))
def test_the_line_reader_never_raises(text: str) -> None:
    read = other.read_other_read(text)
    assert read.state in other.STATES and read.where in other.WHERE_STATES
    other.block((read,), 0)


@settings(max_examples=100, deadline=None)
@given(st.text(max_size=200))
def test_the_parser_never_raises_on_a_mangled_other_read_line(text: str) -> None:
    clean = text.replace("\n", " ").replace("\r", " ")
    parse_cyanrip_log(_with_lines([f"  Other read:      {clean}"]))


# --- the record's `reads` ---------------------------------------------------------


def _golden() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(_GOLDEN_13.read_text(encoding="utf-8"))
    return data


def test_the_fork_s_v13_record_is_read() -> None:
    data = _golden()
    assert data["schema"] == "cyanrip-diagnostics/13"
    reading = parse_isrcs(_GOLDEN_13.read_text(encoding="utf-8"))
    assert reading.state == STATE_READ and len(reading.tracks) == 3  # floor
    for track, row in zip(reading.tracks, data["rip"]["track_state"], strict=True):
        found = track.distinct_reads
        assert found.state == reads.READ and len(found.reads) == 1
        kept = found.kept()
        assert kept is not None and kept.complete
        assert (kept.count, kept.last_read, kept.file) == (3, 3, None)
        # Derived against the row itself: the one read is the track's own.
        assert kept.eac_crc == row["eac_crc"]
        assert list(kept.block_crcs.crcs) == row["block_crcs"]
    rows = error_positions_block(reading)["tracks"]
    assert [r["distinct_reads_state"] for r in rows] == ["read"] * 3
    entry = rows[0]["distinct_reads"]
    assert entry is not None and entry[0]["kept"] is True
    assert entry[0]["differs_from_kept_in_seconds"] is None
    assert reading.drive_declared.state == declared.NOT_STATED  # a disc image


def test_diagrecord_s_two_reads_and_a_comparison_of_seconds() -> None:
    """The entries `cyanrip@40dc64d7:tests/diagrecord.c:391-397` expects."""
    data = _golden()
    data["rip"]["track_state"][0]["reads"] = [
        {"eac_crc": "0BADF00D", "count": 2, "last_read": 3, "kept": False,
         "accurip_v1": "00000001", "accurip_v2": "FFFFFFFF",
         "block_crcs": ["0000ABCD", "12345678"], "file": 'dir/"q".wav'},
        {"eac_crc": "CAFEF00D", "count": 1, "last_read": 4, "kept": True,
         "accurip_v1": "0000000A", "accurip_v2": "0000000B",
         "block_crcs": None, "file": None},
    ]  # fmt: skip
    data["rip"]["track_state"][1]["reads"] = None  # never read
    reading = parse_isrcs(json.dumps(data))
    first = reading.tracks[0].distinct_reads
    assert [r.complete for r in first.reads] == [True, True]
    assert first.reads[0].file == 'dir/"q".wav'
    assert reading.tracks[1].distinct_reads.state == reads.NOT_STATED
    rows = error_positions_block(reading)["tracks"]
    # The kept read's CRCs are null, so no second can be compared.
    assert rows[0]["distinct_reads"] is not None
    assert rows[0]["distinct_reads"][0]["differs_from_kept_in_seconds"] is None
    assert rows[1]["distinct_reads"] is None
    # With the kept read's CRCs present, the differing seconds are derived.
    data["rip"]["track_state"][0]["reads"][1]["block_crcs"] = ["0000ABCD", "00000000"]
    rows = error_positions_block(parse_isrcs(json.dumps(data)))["tracks"]
    assert rows[0]["distinct_reads"] is not None
    assert rows[0]["distinct_reads"][0]["differs_from_kept_in_seconds"] == [1]


def test_states_bounds_and_a_v12_record() -> None:
    assert reads.parse_distinct_reads({"reads": "x"}).state == reads.UNRECOGNISED
    odd = reads.parse_distinct_reads({"reads": [1, {"eac_crc": "zz", "kept": 1}]})
    assert odd.not_read == 1 and odd.reads[0].complete is False
    assert odd.reads[0].eac_crc is None and odd.reads[0].kept is None
    assert odd.kept() is None
    long = reads.parse_distinct_reads({"reads": [{}] * 70})
    assert len(long.reads) == reads.KEEP_HEAD + reads.KEEP_TAIL and long.not_kept == 6
    v12: dict[str, Any] = json.loads(_RECORD_10.read_text(encoding="utf-8"))
    v12["schema"] = "cyanrip-diagnostics/12"
    reading = parse_isrcs(json.dumps(v12))
    assert reading.state == STATE_READ and reading.tracks  # floor
    assert {t.distinct_reads.state for t in reading.tracks} == {reads.NOT_PRESENT}
    assert reading.drive_declared.state == declared.NOT_PRESENT
    rows = error_positions_block(reading)["tracks"]
    assert {r["distinct_reads_state"] for r in rows} == {"not_present"}
    assert {str(r["distinct_reads"]) for r in rows} == {"None"}


_JSON: Final[Any] = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=12),
    lambda children: (
        st.lists(children, max_size=5)
        | st.dictionaries(st.text(max_size=12), children, max_size=5)
    ),
    max_leaves=25,
)


@settings(max_examples=300, deadline=None)
@given(_JSON)
def test_the_reads_reader_never_raises(value: object) -> None:
    found = reads.parse_distinct_reads({"reads": value})
    assert found.state in reads.STATES
    reads.report_entries(found)


# --- the record's `drive_declared` ------------------------------------------------

#: The replies `cyanrip@40dc64d7:tests/diagrecord.c:445-480` expects, as JSON.
_DECLARED: Final[str] = """{
  "inquiry": {"answered":true,"length":8,"truncated":false,"bytes":"058000320350494F"},
  "configuration": {"answered":true,"length":24,"truncated":false,
    "bytes":"00000014000000080000030400080100001E090482000000"},
  "cd_read_feature": {"found":true,"bytes":"001E090482000000","current":true,
    "dap":true,"c2_flags":true,"cd_text":false},
  "mode_sense_all_pages": [
    {"page_control":"current","answered":true,"length":16,"truncated":false,
     "bytes":"000E0000000000000106240500000000"},
    {"page_control":"changeable","answered":true,"length":40,"truncated":true,
     "bytes":"000E0000000000000106240500000000"},
    {"page_control":"default","answered":true,"length":16,"truncated":false,
     "bytes":"000E0000000000000106000500000000"},
    {"page_control":"saved","answered":false,"length":null,"truncated":null,"bytes":null}
  ]
}"""


def _declared(value: object) -> declared.DriveDeclared:
    return declared.parse_drive_declared({"drive_declared": value})


def test_every_reply_diagrecord_expects_is_read_and_checked() -> None:
    found = _declared(json.loads(_DECLARED))
    assert found.state == declared.READ
    assert found.inquiry is not None and found.inquiry["bytes"] == "058000320350494F"
    assert found.inquiry["agrees"] is True and found.inquiry["state"] == "read"
    feature = found.cd_read_feature
    assert feature is not None and feature["state"] == "read"
    assert (feature["current"], feature["dap"], feature["c2_flags"], feature["cd_text"]) == (
        True, True, True, False,
    )  # fmt: skip
    assert feature["bits_agree_with_bytes"] is True
    assert [p["page_control"] for p in found.mode_sense] == list(declared.PAGE_CONTROLS)
    changeable, saved = found.mode_sense[1]["reply"], found.mode_sense[3]["reply"]
    assert (changeable["truncated"], changeable["agrees"]) == (True, True)
    assert (saved["state"], saved["answered"], saved["agrees"]) == ("read", False, None)


def test_a_record_contradicting_its_own_bytes_says_so() -> None:
    value = json.loads(_DECLARED)
    value["inquiry"]["truncated"] = True  # 8 bytes kept of 8 declared
    value["cd_read_feature"]["cd_text"] = True  # byte 4 is 0x82
    found = _declared(value)
    assert found.inquiry is not None and found.inquiry["agrees"] is False
    feature = found.cd_read_feature
    assert feature is not None and feature["bits_agree_with_bytes"] is False
    assert feature["state"] == declared.UNRECOGNISED


def test_no_feature_is_null_bits_never_false() -> None:
    value = json.loads(_DECLARED)
    value["cd_read_feature"] = {"found": False, "bytes": None, "current": None,
                                "dap": None, "c2_flags": None, "cd_text": None}  # fmt: skip
    feature = _declared(value).cd_read_feature
    assert feature is not None and feature["state"] == "read"
    assert feature["dap"] is None and feature["bits_agree_with_bytes"] is None


def test_the_report_block_carries_it_and_says_what_it_is() -> None:
    data = _golden()
    data["drive_declared"] = json.loads(_DECLARED)
    block = declared.report_block(parse_isrcs(json.dumps(data)))
    assert block["state"] == STATE_READ and block["declared_state"] == "read"
    assert block["mode_sense_all_pages"] is not None
    assert len(block["mode_sense_all_pages"]) == 4
    assert "not a measurement" in block["note"]
    image = declared.report_block(parse_isrcs(_GOLDEN_13.read_text(encoding="utf-8")))
    assert image["declared_state"] == "not_stated" and image["inquiry"] is None
    unread = declared.report_block(None)
    assert (unread["state"], unread["declared_state"]) == ("not_read", None)
    assert _declared("x").state == declared.UNRECOGNISED
    # Through the report as the window hands it its `disc` block, and to JSON.
    report = build_report(None, disc={"drive_declared": block})
    carried = json.loads(json.dumps(report))["disc"]["drive_declared"]
    assert carried["inquiry"]["bytes"] == "058000320350494F"
    assert carried["cd_read_feature"]["bits_agree_with_bytes"] is True


@settings(max_examples=300, deadline=None)
@given(_JSON)
def test_the_declared_reader_never_raises(value: object) -> None:
    found = _declared(value)
    assert found.state in declared.STATES
