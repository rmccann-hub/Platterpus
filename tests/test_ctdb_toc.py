# SPDX-License-Identifier: GPL-3.0-only
"""Tests for whipper_gui.ctdb.toc — deterministic TOC math/parsing.

(Whether the resulting toc-string actually matches CTDB's wire format is a
hardware-validation item, KDD-16 / docs/test-plan.md — these tests cover that
the transformations do what we intend.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from whipper_gui.ctdb.toc import (
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


def test_disctoc_toc_string() -> None:
    toc = DiscToc(track_offsets=(150, 18172), leadout=295716)
    assert toc.toc_string() == "150:18172:295716"
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
