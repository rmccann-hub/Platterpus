"""Can a title, or any value cyanrip echoes into its log, forge a verdict line?

Peer review 2.4 (the claude-code-skills session, 2026-10-26, from `main` at
`d745464d`). cyanrip prints metadata values verbatim, with ``"%s\\n"``, in the
per-track ``Metadata:`` block and in the ``CD-TEXT:`` blocks
(``cyanrip@eca33dc:src/cyanrip_log.c:58-62`` and ``:770-776``; the CD-TEXT block
is printed at ``:785-788``), so a value holding a line break puts the text after
it at column 0 of a line of its own. Our parser reads the log line by line, so
such a line is shaped exactly like one cyanrip printed itself.

Two routes reach that echo, and they are answered differently:

* **Values we send** (``-a`` / ``-t``). Refused or replaced at the argv
  chokepoint before cyanrip sees them (decision D14): the four path-bearing
  fields refuse a control character, the seven tag-only fields have it replaced
  with a space. :func:`test_OUR_values_cannot_carry_a_line_into_the_log` drives
  every one of the eleven through the real builder, then echoes what cyanrip
  would have stored into a real log and parses it: the verdict does not move.
* **Values we never send.** The disc's own CD-TEXT is echoed verbatim in a
  per-track ``CD-TEXT:`` block (and fills tags we leave empty,
  ``cyanrip@eca33dc:src/cdtext.c:110-131``). Nothing we send can stop that, so
  the parser defends itself: every per-track verdict row (``EAC CRC32``,
  ``Secure re-read``, ``Accurip:`` and its ``v1`` / ``v2`` / ``450`` rows) is
  printed BEFORE the block's ``Metadata:`` header in every cyanrip build
  (``cyanrip@eca33dc:src/cyanrip_log.c:648-744`` against ``:755``), so one that
  appears after it can only have come out of an echoed value, and is not read.

**What this does not close, written down rather than scoped away** (TASKS R86):
an echoed value can still forge a block OPENER (``Track N read successfully!``),
a ``Done;`` line, or a disc-level header row through the ``Album:`` line or the
disc ``CD-TEXT:`` block. Only the fork escaping what it echoes closes those; it
goes to them as a NEXT-ROUND item.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Final

import pytest

from platterpus.adapters.cyanrip_backend import _metadata_args
from platterpus.adapters.rip_backend import RipError, RipMetadata, TrackTag
from platterpus.cyanrip_cli import split_meta_blob
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.verdict import accuraterip_verdict

_FIXTURE: Final[Path] = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36l8.log"
)

#: Track 1's ``TITLE:`` row in the reference log: the echo we put values into.
_TITLE_ROW: Final[str] = "    TITLE:                         Unknown track\n"

#: Every character Python's ``str.splitlines`` ends a line at, which is what the
#: parser splits on, plus NUL and ESC (no line break, but no business in a log).
_BREAKS: Final[tuple[str, ...]] = (
    "\n",
    "\r",
    "\r\n",
    "\x0b",
    "\x0c",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x85",
    " ",
    " ",
)

#: Rows that, read as cyanrip's own, would change a track's verdict. Each one is
#: a shape the parser reads when it is genuine (proved by
#: :func:`test_each_forged_row_IS_read_when_it_stands_where_cyanrip_prints_it`).
_FORGED_ROWS: Final[dict[str, str]] = {
    "accurip_status": "  Accurip:       accurately ripped (confidence 200)",
    "accurip_v1": "    Accurip v1:  BAE96A9D (accurately ripped, confidence 200)",
    "accurip_v2": "    Accurip v2:  C0772401 (accurately ripped, confidence 200)",
    "accurip_450": "    Accurip 450: 00000000 (matches Accurip DB, confidence 200)",
    "eac_crc": "  EAC CRC32:     DEADBEEF (after 9 rips)",
    "secure_reread": "  Secure re-read:  did NOT converge after 9 reads (repeat limit hit)",
}


def _base() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def _verdict_facts(rip_log: RipLog) -> tuple[object, ...]:
    """Everything a track's verdict is computed from, plus the verdict itself."""
    per_track = tuple(
        (
            t.number,
            t.status,
            t.copy_crc,
            t.rip_count,
            t.accuraterip_lookup,
            t.accuraterip_v1,
            t.accuraterip_v2,
            t.accuraterip_offset,
            t.secure_rerip_converged,
        )
        for t in rip_log.tracks
    )
    return (
        per_track,
        rip_log.ripping_errors,
        accuraterip_verdict(rip_log, disc_track_total=3),
    )


def _echo_after_title(text: str, value: str) -> str:
    """The log with ``value`` echoed as track 1's title, as cyanrip prints it."""
    assert text.count(_TITLE_ROW) == 3, "the fixture changed under this test"
    first = text.index(_TITLE_ROW)
    row = f"    TITLE:                         {value}\n"
    return text[:first] + row + text[first + len(_TITLE_ROW) :]


def _with_cdtext_block(text: str, value: str) -> str:
    """Track 1 given a per-track ``CD-TEXT:`` block whose title is ``value``.

    Placed where cyanrip prints it: after the ``Metadata:`` block, before the
    paranoia counts (``cyanrip@eca33dc:src/cyanrip_log.c:785-811``).
    """
    anchor = "\n  Paranoia status counts:\n"
    first = text.index(anchor)
    block = f"\n  CD-TEXT:\n    title: {value}\n"
    return text[:first] + block + text[first:]


# --- route 1: the values we send ----------------------------------------------

#: The eleven values `_metadata_args` turns into argv, and the key each is sent
#: under. The four path-bearing ones are refused; the rest are replaced.
_PATH_BEARING: Final[tuple[str, ...]] = (
    "album_title",
    "album_artist",
    "track_title",
    "track_artist",
)
_FIELDS: Final[dict[str, str]] = {
    "album_title": "album",
    "album_artist": "album_artist",
    "track_title": "title",
    "track_artist": "artist",
    "year": "date",
    "genre": "genre",
    "catalog_number": "catalognumber",
    "barcode": "barcode",
    "label": "label",
    "isrc": "isrc",
    "release_id": "musicbrainz_albumid",
}


def test_the_forged_row_table_names_every_verdict_row() -> None:
    """The floor for the three tests parametrized over `_FORGED_ROWS`."""
    assert len(_FORGED_ROWS) == 6


def test_the_field_table_names_all_eleven_values_we_send() -> None:
    """The floor for the parametrized route-1 test: its population is computed."""
    assert len(_FIELDS) == 11 and set(_PATH_BEARING) <= set(_FIELDS)


def _metadata_with(field: str, value: str) -> tuple[RipMetadata, str]:
    track = TrackTag(
        1,
        title=value if field == "track_title" else "T",
        artist=value if field == "track_artist" else "A",
        isrc=value if field == "isrc" else "",
    )
    meta = RipMetadata(tracks=(track,))
    if hasattr(meta, field):
        meta = dataclasses.replace(meta, **{field: value})
    return meta, value if field == "release_id" else "mbid"


@pytest.mark.parametrize("brk", _BREAKS)
@pytest.mark.parametrize("field", sorted(_FIELDS))
def test_OUR_values_cannot_carry_a_line_into_the_log(field: str, brk: str) -> None:
    """The whole path: argv builder -> what cyanrip stores -> its echo -> parser."""
    payload = "X" + brk + _FORGED_ROWS["accurip_status"]
    meta, release_id = _metadata_with(field, payload)
    if field in _PATH_BEARING:
        with pytest.raises(RipError, match="control character"):
            _metadata_args(meta, release_id)
        return
    argv = _metadata_args(meta, release_id)
    blobs = [argv[i + 1] for i, token in enumerate(argv) if token in ("-a", "-t")]
    sent: dict[str, str] = {}
    for blob in blobs:
        # A `-t` blob is `N=key=value:…`; drop the track number the way cyanrip does.
        body = blob.split("=", 1)[1] if blob[:1].isdigit() else blob
        sent.update(split_meta_blob(body))
    stored = sent[_FIELDS[field]]
    assert stored.startswith("X") and not any(ch in stored for ch in brk)

    baseline = parse_cyanrip_log(_base())
    echoed = parse_cyanrip_log(_echo_after_title(_base(), stored))
    assert _verdict_facts(echoed) == _verdict_facts(baseline)


# --- route 2: a value we never send (the disc's CD-TEXT) -----------------------


@pytest.mark.parametrize("brk", ["\n", "\r", "\x85", " ", "\n\n"])
@pytest.mark.parametrize("row", sorted(_FORGED_ROWS))
def test_a_CDTEXT_echo_cannot_forge_a_track_verdict_row(row: str, brk: str) -> None:
    """``\\n\\n`` too: a blank line ends the block a reader might scope by."""
    baseline = parse_cyanrip_log(_base())
    forged = parse_cyanrip_log(
        _with_cdtext_block(_base(), "Song" + brk + _FORGED_ROWS[row])
    )
    assert _verdict_facts(forged) == _verdict_facts(baseline)


@pytest.mark.parametrize("row", sorted(_FORGED_ROWS))
def test_an_echoed_TITLE_cannot_forge_a_track_verdict_row(row: str) -> None:
    """The same, through the Metadata block: a tag CD-TEXT filled in for us."""
    baseline = parse_cyanrip_log(_base())
    forged = parse_cyanrip_log(_echo_after_title(_base(), "S\n" + _FORGED_ROWS[row]))
    assert _verdict_facts(forged) == _verdict_facts(baseline)


def test_the_echo_does_not_cost_the_rows_that_LIVE_in_it() -> None:
    """The ReplayGain rows sit inside the Metadata block and are still read."""
    baseline = parse_cyanrip_log(_base())
    forged = parse_cyanrip_log(
        _echo_after_title(_base(), "S\n" + _FORGED_ROWS["eac_crc"])
    )
    assert forged.tracks[0].replaygain == baseline.tracks[0].replaygain
    assert baseline.tracks[0].replaygain, "floor: the fixture has ReplayGain rows"


# --- the floors: the forged rows are real shapes ------------------------------


@pytest.mark.parametrize("row", sorted(_FORGED_ROWS))
def test_each_forged_row_IS_read_when_it_stands_where_cyanrip_prints_it(
    row: str,
) -> None:
    """Without this, every test above passes against rows nothing would read.

    Each row is put just before track 1's ``Metadata:`` header, where cyanrip
    prints the genuine one, and must change the parse there.
    """
    text = _base()
    anchor = "\n  Metadata:\n"
    first = text.index(anchor)
    moved = text[:first] + "\n" + _FORGED_ROWS[row] + text[first:]
    assert _verdict_facts(parse_cyanrip_log(moved)) != _verdict_facts(
        parse_cyanrip_log(text)
    )


def test_every_verdict_row_precedes_the_echo_in_every_committed_log() -> None:
    """The fact the parser's latch rests on, read from the artifacts, with a floor.

    If a build ever printed a verdict row after ``Metadata:`` / ``CD-TEXT:``, the
    latch would drop a genuine row; this would fail first.
    """
    import re

    root = Path(__file__).resolve().parents[1]
    opener = re.compile(r"^Track \d{1,4} ")
    echo = re.compile(r"^\s+(?:Metadata|CD-TEXT):\s*$")
    verdict = re.compile(r"^\s+(?:EAC CRC32|Accurip(?: v[12]| 450)?|Secure re-?read)\b")
    blocks_with_echo = 0
    files = 0
    for path in sorted(
        {*root.glob("tests/fixtures/**/*.log"), *root.glob("output_reference/**/*.log")}
    ):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "cyanrip" not in text[:400]:
            continue
        files += 1
        seen_echo = False
        for number, line in enumerate(text.splitlines(), 1):
            if opener.match(line):
                seen_echo = False
            elif echo.match(line):
                blocks_with_echo += not seen_echo
                seen_echo = True
            elif seen_echo and verdict.match(line):
                pytest.fail(f"{path.name}:{number}: a verdict row after the echo")
    assert files >= 20 and blocks_with_echo >= 100, (files, blocks_with_echo)


# --- the residual, pinned so it cannot be forgotten (TASKS R86) ----------------


def test_RESIDUAL_a_forged_block_opener_still_changes_the_parse() -> None:
    """Not closed here, and pinned so the narrowing is visible.

    A value carrying ``\\nTrack 2 read successfully!`` opens a block cyanrip never
    printed. The parser cannot tell it from a genuine opener, because the genuine
    one is at column 0 with no structure around it. Closed only by the fork
    escaping echoed values (NEXT-ROUND, TASKS R86). When that lands, a log from
    such a build cannot carry this shape, and this test may be retired with the
    row; until then it says exactly what is still open.
    """
    baseline = parse_cyanrip_log(_base())
    forged = parse_cyanrip_log(
        _with_cdtext_block(_base(), "Song\n\nTrack 2 read successfully!")
    )
    assert [t.number for t in forged.tracks] != [t.number for t in baseline.tracks] or (
        dataclasses.astuple(forged.tracks[0]) != dataclasses.astuple(baseline.tracks[0])
    )
