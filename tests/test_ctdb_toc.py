# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.ctdb.toc — deterministic TOC math/parsing.

(Whether the resulting toc-string actually matches CTDB's wire format is a
hardware-validation item, KDD-16 / docs/test-plan.md — these tests cover that
the transformations do what we intend.)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.ctdb.toc import (
    LEAD_IN_SECTORS,
    SAMPLES_PER_SECTOR,
    DiscToc,
    disc_toc_from_files,
    msf_to_sectors,
    parse_cue_index01_sectors,
    samples_to_sectors,
)


def test_msf_to_sectors() -> None:
    assert msf_to_sectors(0, 0, 0) == 0
    assert msf_to_sectors(0, 2, 0) == 150  # 2 s = 150 frames
    assert msf_to_sectors(1, 0, 0) == 60 * 75


def test_samples_to_sectors_rounds_up() -> None:
    assert samples_to_sectors(SAMPLES_PER_SECTOR) == 1
    assert samples_to_sectors(SAMPLES_PER_SECTOR + 1) == 2  # partial last sector
    assert samples_to_sectors(0) == 0


def test_disctoc_toc_string_is_lead_in_relative() -> None:
    # lookup2.php wants offsets relative to the first track (lead-in removed) —
    # the list must start at 0, so every value is 150 less than the absolute
    # (AccurateRip-convention) offsets we store. Verified against the live
    # server: the old "150:…" form 404'd; "0:…" returns a real match.
    toc = DiscToc(track_offsets=(150, 18172), leadout=295716)
    assert toc.toc_string() == "0:18022:295566"
    assert toc.num_tracks == 2


def test_disctoc_validates() -> None:
    with pytest.raises(ValueError):
        DiscToc(track_offsets=(), leadout=10)
    with pytest.raises(ValueError):
        DiscToc(track_offsets=(150,), leadout=150)  # leadout not past last track


def test_parse_cue_index01_adds_lead_in() -> None:
    cue = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        'FILE "02.flac" WAVE\n'
        "  TRACK 02 AUDIO\n"
        "    INDEX 00 03:58:50\n"
        "    INDEX 01 04:00:00\n"
    )
    sectors = parse_cue_index01_sectors(cue)
    # First track at lead-in; second at 4:00 + lead-in. INDEX 00 ignored.
    assert sectors == [LEAD_IN_SECTORS, msf_to_sectors(4, 0, 0) + LEAD_IN_SECTORS]


def test_disc_toc_from_files_accumulates_lengths() -> None:
    # Two tracks: 1 sector and 2 sectors' worth of samples.
    sizes = {Path("a.flac"): SAMPLES_PER_SECTOR, Path("b.flac"): 2 * SAMPLES_PER_SECTOR}
    toc = disc_toc_from_files(list(sizes), samples_probe=lambda p: sizes[p])
    assert toc.track_offsets == (LEAD_IN_SECTORS, LEAD_IN_SECTORS + 1)
    assert toc.leadout == LEAD_IN_SECTORS + 1 + 2


def test_disc_toc_from_files_empty_raises() -> None:
    with pytest.raises(ValueError):
        disc_toc_from_files([], samples_probe=lambda p: 0)


# --- Property: the .cue INDEX reader, over the sheets a writer can produce ------
#
# Until 2026-09-25 this parser was pinned by one hand-written sheet and, in
# `tests/test_never_raises_contract.py`, at the 4300-digit integer boundary. The
# property below generates whole sheets — any number of tracks, INDEX 00/02 lines,
# TITLE and REM noise that quotes an INDEX line, either case, any indentation, any
# of the three line-ending conventions — and asserts the reader returns exactly
# the INDEX 01 starts, in order, as absolute sectors.

#: Characters a cue VALUE is drawn from. Every character `str.splitlines` treats
#: as a line boundary is excluded: this reader splits with `splitlines` (as does
#: `cue_validate`), so a TITLE carrying U+2028 is two lines to both of them. That
#: shared behaviour is outside what this property pins, in either direction.
_CUE_VALUE = st.text(
    st.characters(
        blacklist_characters='\n\r\x0b\x0c\x1c\x1d\x1e\x85  "',
        blacklist_categories=["Cs"],
    ),
    max_size=20,
)
_MSF = st.tuples(st.integers(0, 99), st.integers(0, 59), st.integers(0, 74))


def _stamp(msf: tuple[int, int, int], pad: bool) -> str:
    m, s, f = msf
    return f"{m:02}:{s:02}:{f:02}" if pad else f"{m}:{s:02}:{f:02}"


@st.composite
def _cue_sheet(draw: st.DrawFn) -> tuple[str, list[int]]:
    """A cue sheet and, computed independently of the parser, its INDEX 01 sectors."""
    starts = draw(st.lists(_MSF, min_size=1, max_size=12))
    lines: list[str] = []
    for number, start in enumerate(starts, 1):
        lines.append(f'FILE "{draw(_CUE_VALUE)}.flac" WAVE')
        lines.append(f"  TRACK {number:02} AUDIO")
        # Noise that QUOTES an INDEX 01 line — the reader must key on a line that
        # IS one, never on a line that mentions one.
        decoy = f"INDEX 01 {_stamp(draw(_MSF), True)}"
        lines.append(
            f'    TITLE "{draw(st.sampled_from([decoy, "x"]))}{draw(_CUE_VALUE)}"'
        )
        lines.append(f"    REM COMMENT {draw(st.sampled_from([decoy, 'ok']))}")
        if draw(st.booleans()):
            lines.append(f"    INDEX 00 {_stamp(draw(_MSF), True)}")
        keyword = draw(st.sampled_from(["INDEX", "index", "Index"]))
        indent = draw(st.sampled_from(["", " ", "    ", "\t"]))
        gap = draw(st.sampled_from([" ", "  ", "\t"]))
        lines.append(
            f"{indent}{keyword}{gap}01{gap}{_stamp(start, draw(st.booleans()))}"
        )
        if draw(st.booleans()):
            lines.append(f"    INDEX 02 {_stamp(draw(_MSF), True)}")
    eol = draw(st.sampled_from(["\n", "\r\n", "\r"]))
    text = eol.join(lines) + draw(st.sampled_from(["", eol]))
    # CD-DA addressing, stated from the Red Book rather than read back from
    # `msf_to_sectors`: 60 s a minute, 75 sectors a second, plus the 150-sector
    # (2 s) lead-in the AccurateRip/CTDB convention includes.
    expected = [(m * 60 + s) * 75 + f + 150 for m, s, f in starts]
    return text, expected


@given(_cue_sheet())
def test_the_cue_reader_returns_exactly_the_index_01_starts_in_order(
    sheet: tuple[str, list[int]],
) -> None:
    text, expected = sheet
    assert expected, "the sheet has at least one track, so the reader has work to do"
    assert parse_cue_index01_sectors(text) == expected


#: A garbled timestamp: missing fields, letters, stray colons, a non-ASCII digit
#: (`\d` matches `٣`), or nothing.
_GARBLE = st.text(st.sampled_from("0123456789:x ٣"), max_size=14)


def _index01(stamp: st.SearchStrategy[str]) -> st.SearchStrategy[str]:
    return st.builds(
        "{}INDEX{}01 {}".format,
        st.sampled_from(["", "  ", "\t"]),
        st.sampled_from([" ", "\t"]),
        stamp,
    )


#: An INDEX 01 line the reader CAN convert — a real MSF with trailing junk, which
#: the reader tolerates — so the property below is guaranteed to reach the
#: conversion rather than hoping a random timestamp happens to parse.
_CONVERTIBLE = _index01(
    st.builds(lambda msf, junk: _stamp(msf, True) + junk, _MSF, _GARBLE)
)


@given(
    lines=st.lists(st.one_of(st.text(max_size=40), _index01(_GARBLE)), max_size=12),
    convertible=_CONVERTIBLE,
    at=st.integers(0, 12),
)
def test_the_cue_reader_never_raises_and_never_conjures_a_start(
    lines: list[str], convertible: str, at: int
) -> None:
    """On arbitrary text salted with garbled and convertible INDEX 01 lines: never
    raises, and every sector returned is accounted for by a line that mentions
    INDEX — the reader may skip a line it cannot convert, never produce one.

    The salt is what makes this reach the conversion: plain `st.text()` almost never
    draws an INDEX line, and a first version that relied on random timestamps
    parsing was revert-probed VACUOUS. So one convertible line is always present,
    and the floor asserts the reader converted it."""
    lines.insert(min(at, len(lines)), convertible)
    text = "\n".join(lines)
    sectors = parse_cue_index01_sectors(text)
    assert sectors, "the convertible INDEX 01 line was not converted"
    mentions = [ln for ln in text.splitlines() if re.search("index", ln, re.IGNORECASE)]
    assert len(sectors) <= len(mentions)
    assert all(s >= LEAD_IN_SECTORS for s in sectors)
