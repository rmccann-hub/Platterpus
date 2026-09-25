"""Tests for :mod:`platterpus.tag_hygiene` — maintainer decision D14 (2026-09-25).

A control character in a tag that comes only from MusicBrainz (genre, label,
catalog number, barcode, year, ISRC, release id) is replaced with a space and the
report says so. The four path-bearing fields still refuse one. Until this, the
seven went to cyanrip unchecked (`TASKS.md` E12 and the `_metadata_args` fuzz row).
"""

from __future__ import annotations

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import tag_hygiene
from platterpus.adapters.cyanrip_backend import RipError, _metadata_args
from platterpus.adapters.rip_backend import RipMetadata, TrackTag
from platterpus.settings_validation import is_control_char, path_segment_issue

_TAG_ONLY = ("year", "genre", "catalog_number", "barcode", "label")


def test_clean_metadata_passes_through_untouched() -> None:
    meta = RipMetadata(genre="Rock", label="Label", tracks=(TrackTag(1, isrc="GB1"),))
    cleaned = tag_hygiene.clean_tag_only_fields(meta, "mbid")
    assert cleaned.metadata == meta and cleaned.release_id == "mbid"
    assert cleaned.fixes == ()


@pytest.mark.parametrize("field", _TAG_ONLY)
def test_each_album_level_tag_only_field_is_cleaned(field: str) -> None:
    meta = RipMetadata(**{field: "a\nb\tc"})
    cleaned = tag_hygiene.clean_tag_only_fields(meta)
    assert getattr(cleaned.metadata, field) == "a b c"
    assert cleaned.fixes == (tag_hygiene.TagFix(field.replace("_", " "), 2),)


def test_track_isrc_and_release_id_are_cleaned_and_named() -> None:
    meta = RipMetadata(tracks=(TrackTag(3, isrc="GB\x00AAA"),))
    cleaned = tag_hygiene.clean_tag_only_fields(meta, "id\r")
    assert cleaned.metadata.tracks[0].isrc == "GB AAA"
    assert cleaned.release_id == "id "
    assert [f.field for f in cleaned.fixes] == ["release id", "track 3 isrc"]


def test_path_bearing_fields_are_left_for_the_refusal() -> None:
    """Replacing these would hide the refusal the path rule depends on."""
    meta = RipMetadata(
        album_title="A\nB",
        album_artist="C\nD",
        tracks=(TrackTag(1, title="E\nF", artist="G\nH"),),
    )
    cleaned = tag_hygiene.clean_tag_only_fields(meta)
    assert cleaned.metadata == meta and cleaned.fixes == ()


def test_the_report_block_names_each_field_and_count() -> None:
    fixes = (tag_hygiene.TagFix("genre", 2), tag_hygiene.TagFix("label", 1))
    assert tag_hygiene.fixes_block(fixes) == [
        {"field": "genre", "replaced": 2},
        {"field": "label", "replaced": 1},
    ]


def test_one_definition_of_a_control_character_for_both_rules() -> None:
    """The path fields refuse exactly what the tag-only fields replace."""
    for code in range(0x300):
        ch = chr(code)
        refused = "control character" in (path_segment_issue("Title", f"a{ch}b") or "")
        assert refused == is_control_char(ch), hex(code)


@given(st.text(), st.text(), st.text())
def test_no_control_character_survives_in_a_tag_only_field(
    genre: str, isrc: str, release_id: str
) -> None:
    meta = RipMetadata(genre=genre, tracks=(TrackTag(1, isrc=isrc),))
    cleaned = tag_hygiene.clean_tag_only_fields(meta, release_id)
    for value in (
        cleaned.metadata.genre,
        cleaned.metadata.tracks[0].isrc,
        cleaned.release_id,
    ):
        assert not any(is_control_char(ch) for ch in value)
    assert len(cleaned.metadata.genre) == len(genre)  # replaced, never removed
    assert sum(f.replaced for f in cleaned.fixes) == sum(
        is_control_char(ch) for ch in genre + isrc + release_id
    )


# --- at the argv chokepoint --------------------------------------------------


def test_the_argv_carries_the_replaced_value_and_the_log_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    args = _metadata_args(RipMetadata(album_title="X", genre="Rock\nPop"), "mbid")
    blob = args[args.index("-a") + 1]
    assert "genre=Rock Pop" in blob
    assert any("genre tag" in r.getMessage() for r in caplog.records)


_ANY = st.text(max_size=12)


@given(
    title=_ANY,
    artist=_ANY,
    year=_ANY,
    genre=_ANY,
    catalog=_ANY,
    barcode=_ANY,
    label=_ANY,
    track_title=_ANY,
    track_artist=_ANY,
    isrc=_ANY,
    release_id=_ANY,
)
def test_no_control_character_reaches_the_blob_from_any_field(
    title: str,
    artist: str,
    year: str,
    genre: str,
    catalog: str,
    barcode: str,
    label: str,
    track_title: str,
    track_artist: str,
    isrc: str,
    release_id: str,
) -> None:
    """The E12 invariant, over all eleven fields: refused, or not present."""
    meta = RipMetadata(
        album_title=title,
        album_artist=artist,
        year=year,
        genre=genre,
        catalog_number=catalog,
        barcode=barcode,
        label=label,
        tracks=(TrackTag(1, title=track_title, artist=track_artist, isrc=isrc),),
    )
    try:
        args = _metadata_args(meta, release_id)
    except RipError:
        return  # a path-bearing field was refused, loudly: the other half of D14
    for arg in args:
        assert not any(is_control_char(ch) for ch in arg), arg


def test_a_none_release_id_is_passed_through_not_raised_on() -> None:
    """Real callers pass `None` for an absent release id; the chokepoint must not
    fail a rip over an empty field (found by the argv-contract suite)."""
    cleaned = tag_hygiene.clean_tag_only_fields(RipMetadata(), None)  # type: ignore[arg-type]  # the shape real callers use
    assert cleaned.release_id is None and cleaned.fixes == ()
    assert _metadata_args(RipMetadata(album_title="X"), None) == ["-a", "album=X"]  # type: ignore[arg-type]  # same
