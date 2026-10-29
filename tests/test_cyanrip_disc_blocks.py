"""`.28`'s new log wordings, read before the build ships (the fork's round 37 lap 1).

The fork proposed four wordings for `.28` and asked that a release of ours read
them first, since our parser reports an unrecognised top-level line and `.28` is
not released before we read them (`docs/handshake/inbound/round-37-lap-01.md`):

* S5, the `Pregap searches:` block; S7, the `Names shortened:` block
  (`parsers/cyanrip_disc_blocks.py`);
* S6, the unknown pregap's new reason, `sub-channel search bounds did not meet`,
  which every reader of the reason already takes as text;
* S8, `Speed:` when `-S` could not be applied (`tests/test_rip_worker.py` holds
  what the ladder does with it).

The block lines below are the fork's own: S5's golden-reference line
(`cyanrip@2ccaf88:docs/golden-reference.log:44-45`), and S6 to S8 as the lap
spells them.
"""

from __future__ import annotations

from typing import Final

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.parsers import cyanrip_disc_blocks as blocks
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.uiscript import pregap_grading

#: S5's line, word for word from the fork's golden reference.
_SEARCH_RECORD: Final[str] = (
    "1 sectors asked; 0 reads failed the CRC; 0 sectors gave no frame passing it; "
    "0 frames were another sector's; 0 had no address; frames answer +0 sectors "
    "off; LSN 376 to 524 undecided"
)

#: A disc-level stretch of a `.28` log: `Gaps:`, then both new blocks, then a
#: disc row that must still be read after them.
_LOG: Final[str] = f"""cyanrip 0.9.4-rc3+platterpus.28 (platterpus-fork-g0000000)
Speed:          default (setting 8x failed)
Gaps:
    0 frame pregap in track 1, unmerged
    pregap of track 9 unknown (sub-channel search bounds did not meet)

Pregap searches:
    track 3: {_SEARCH_RECORD}
    track 9: 267 sectors asked; 131 reads failed the CRC

Names shortened:
    folder: Artist: A (Live) {"x" * 200} (301 bytes as rendered)
    track 3, flac: 03 - Song (Remix: 2) (290 bytes as rendered)
    cue sheet: Album.cue (270 bytes as rendered)
    log: Album.log (270 bytes as rendered)

Album:          After The Blocks
"""


def test_the_pregap_searches_block_is_read_per_track() -> None:
    info = parse_cyanrip_log(_LOG).ripping_info
    assert info.pregap_searches == (
        (3, _SEARCH_RECORD),
        (9, "267 sectors asked; 131 reads failed the CRC"),
    )


def test_the_names_shortened_block_is_read_from_the_right() -> None:
    """A name may hold `": "` and parentheses; only the fixed tail ends it."""
    names = parse_cyanrip_log(_LOG).ripping_info.names_shortened
    assert [(n.what, n.rendered_bytes) for n in names] == [
        ("folder", 301),
        ("track 3, flac", 290),
        ("cue sheet", 270),
        ("log", 270),
    ]
    assert names[0].name == "Artist: A (Live) " + "x" * 200
    assert names[1].name == "03 - Song (Remix: 2)"


def test_the_blocks_end_and_the_next_row_is_still_read() -> None:
    parsed = parse_cyanrip_log(_LOG)
    assert parsed.ripping_info.album == "After The Blocks"
    # The `Gaps:` block ended at its blank line; the searches did not join it.
    assert "track 3:" not in parsed.ripping_info.gap_detection


def test_the_new_unknown_reason_is_read_where_the_old_one_was() -> None:
    """S6: both wordings, in `Gaps:` and in a track block's `Pregap LSN:`."""
    for reason in (
        "sub-channel CRC mismatches",
        "sub-channel search bounds did not meet",
    ):
        line = f"pregap of track 9 unknown ({reason})"
        match = pregap_grading._UNKNOWN_LINE.match(line)
        assert match is not None and match.group("reason") == reason
        log = (
            "cyanrip 0.9.4\nTrack 9 ripped and encoded successfully!\n"
            f"    Pregap LSN:  unknown ({reason})\n"
        )
        track = parse_cyanrip_log(log).tracks[0]
        assert track.pregap_state == "unknown"
        assert track.pregap_unknown_reason == reason


def test_the_speed_value_when_a_speed_was_not_applied() -> None:
    """S8: a drive that took no speed is unchangeable; an image names no drive."""

    def speed(value: str) -> bool | None:
        return parse_cyanrip_log(
            f"cyanrip 0.9.4\nSpeed:          {value}\n"
        ).ripping_info.speed_changeable

    assert speed("default (setting 8x failed)") is False
    assert speed("default (disc image, 8x not applied)") is None


def test_lines_that_are_not_the_shape_are_refused() -> None:
    assert blocks.parse_pregap_search_line("    track x: y") is None
    assert blocks.parse_pregap_search_line("track 3: y") is None
    assert blocks.parse_shortened_name_line("    folder: A (12 bytes)") is None
    assert (
        blocks.parse_shortened_name_line("    folder: A (²³ bytes as rendered)") is None
    )
    assert (
        blocks.parse_shortened_name_line("    folder: (12 bytes as rendered)") is None
    )
    assert (
        blocks.parse_shortened_name_line("    disc: A (12 bytes as rendered)") is None
    )


@settings(max_examples=500, deadline=None)
@given(st.text(max_size=120))
def test_the_two_readers_never_raise(text: str) -> None:
    for prefix in ("", "    ", "    track 3: ", "    folder: ", "    track 1, flac: "):
        blocks.parse_pregap_search_line(prefix + text)
        blocks.parse_shortened_name_line(prefix + text)
