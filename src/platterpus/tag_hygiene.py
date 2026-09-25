"""Replace control characters in tags that only ever become tags (decision D14).

**The problem.** Seven of the eleven values we hand cyanrip as tags come from
MusicBrainz and are not editable in the track table: genre, label, catalog number,
barcode, the year, each track's ISRC, and the release ID. A stray newline in a
MusicBrainz entry went straight into the ``-a``/``-t`` argument and the file's tags,
and the user had no way to fix it before ripping (``TASKS.md`` E12; the
``_metadata_args`` fuzz row).

**The ruling** (maintainer, 2026-09-25, D14 B): replace the character with a
space, and say so in the report. Refusing the rip would block a user who cannot
fix the value; changing it silently would make the tag differ from MusicBrainz
with nothing saying why.

**What this does not touch.** The other four values (album artist, album title,
and each track's title and artist) become folder and file names, so they still
**refuse** a control character, loudly, before the rip starts
(``settings_validation.path_segment_issue``). Both sides use
``settings_validation.is_control_char``, so they agree on which characters count.

Pure: no Qt, no I/O. The argv chokepoint (``adapters/cyanrip_backend._metadata_args``)
calls it so nothing reaches cyanrip unreplaced, and the rip-finish path calls it on
the same metadata to record what was changed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from platterpus.adapters.rip_backend import RipMetadata
from platterpus.report_types import TagFixEntry
from platterpus.settings_validation import is_control_char


@dataclass(frozen=True)
class TagFix:
    """One tag-only field that had control characters replaced."""

    field: str
    replaced: int


@dataclass(frozen=True)
class CleanedTags:
    """The metadata as it goes to cyanrip, and what was changed on the way."""

    metadata: RipMetadata
    release_id: str
    fixes: tuple[TagFix, ...]


def clean_value(value: str) -> tuple[str, int]:
    """``(value with each control character replaced by a space, how many)``.

    A value that is not a string is returned unchanged with a count of 0. The
    type says ``str``, but real callers pass ``None`` for an absent release id,
    and the argv chokepoint must not fail a rip over a field that is empty.
    """
    if not isinstance(value, str):
        return value, 0
    count = sum(1 for ch in value if is_control_char(ch))
    if not count:
        return value, 0
    return "".join(" " if is_control_char(ch) else ch for ch in value), count


def clean_tag_only_fields(
    metadata: RipMetadata | None, release_id: str = ""
) -> CleanedTags:
    """Replace control characters in every tag-only field.

    Never raises on a :class:`RipMetadata` of :class:`TrackTag` entries, whatever
    the values hold. The four path-bearing fields are returned exactly as given:
    refusing them is a different rule, applied by the caller before this runs.
    """
    meta = metadata or RipMetadata()
    fixes: list[TagFix] = []

    def fix(field: str, value: str) -> str:
        cleaned, count = clean_value(value)
        if count:
            fixes.append(TagFix(field, count))
        return cleaned

    # Album fields, then the release id, then tracks: the order a reader of the
    # report expects, and the order the arguments are built in.
    album = {
        "year": fix("year", meta.year),
        "genre": fix("genre", meta.genre),
        "catalog_number": fix("catalog number", meta.catalog_number),
        "barcode": fix("barcode", meta.barcode),
        "label": fix("label", meta.label),
    }
    cleaned_id = fix("release id", release_id)
    tracks = tuple(
        replace(track, isrc=fix(f"track {track.number} isrc", track.isrc))
        for track in meta.tracks
    )
    cleaned = replace(
        meta,
        year=album["year"],
        genre=album["genre"],
        catalog_number=album["catalog_number"],
        barcode=album["barcode"],
        label=album["label"],
        tracks=tracks,
    )
    return CleanedTags(cleaned, cleaned_id, tuple(fixes))


def fixes_block(fixes: tuple[TagFix, ...]) -> list[TagFixEntry]:
    """The report's ``disc.tag_control_characters_replaced`` list."""
    return [TagFixEntry(field=f.field, replaced=f.replaced) for f in fixes]
