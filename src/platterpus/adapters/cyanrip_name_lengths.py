"""Refuse, before Start, a rip whose folder or file name is too long to create.

**The defect this closes (TASKS R88).** Linux allows at most 255 BYTES in one
path component (``NAME_MAX``). cyanrip builds every folder and file name from our
``-D``/``-F`` naming schemes and the tags we hand it, and it does not shorten a
name that is too long (no ``NAME_MAX`` handling anywhere in
``cyanrip@eca33dc:src/naming.c``). So an identified disc whose track title runs to
90 Japanese characters (270 UTF-8 bytes) passed every check we had, read the
whole track, and then failed to create the file: the read time was wasted and
the track was lost.

**The owner's interim (2026-10-26): refuse before Start, naming the track and its
byte count.** The long-term fix is the fork shortening the FILE NAME only, so the
tag stays whole; that will be asked for in a handshake lap. Until then a person
shortens the title in the track table, which shortens the tag with it.

**How it predicts the names: it does not restate cyanrip's rules.** Every name is
rendered by the one renderer the overwrite guard already uses
(:func:`platterpus.naming.render_scheme`), from the very ``-D``/``-F`` schemes the
argv sends (:func:`cyanrip_backend._path_schemes`) and the tags it sends, cleaned
the way ``_metadata_args`` cleans them. Each name's byte count is
:func:`platterpus.naming.name_bytes_on_disk`, which counts what cyanrip writes for
a character, not the character we typed. Three things cyanrip adds that the
renderer does not hold are written here, each with the line it comes from:

* a track's file gets ``.flac`` (and a derived format gets its own extension
  beside it, ``adapters.transcode.extension_for``);
* ``{track}`` is zero-padded to the disc's width
  (``cyanrip@eca33dc:src/naming.c:239-250``);
* the rip LOG and CUE are written into the album folder under cyanrip's own
  ``{album}`` scheme (``cyanrip@eca33dc:src/cyanrip_main.c:2355-2356``,
  ``src/naming.c:497-505``), so an album title that fits as a folder can still be
  four bytes too long as ``<album>.log``.

**Two callers, one function** (CLAUDE.md: one predicate, many callers):

* ``ui.track_table.TrackTable.validate``: the visible, specific error before
  Start, at the point of entry;
* ``cyanrip_backend.CyanripBackend._build_rip_argv``: the argv chokepoint's
  backstop, which refuses like the other path checks there, so no route to the
  ripper (a script verb, a re-rip into a numbered folder) can skip it.

Pure: no Qt, no I/O, never raises.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from platterpus import naming, tag_hygiene
from platterpus.adapters import cyanrip_backend
from platterpus.adapters.rip_backend import RipError, RipMetadata, TrackTag

log = logging.getLogger(__name__)

#: The extension of the file every rip writes first: the FLAC master.
_MASTER_EXTENSION: Final[str] = "flac"

#: The extensions cyanrip gives the rip log and the cue sheet, both written into
#: the album folder under the same name scheme (``src/naming.c:497-505``). The
#: longer of the two is what has to fit; they are the same length today.
_SIDE_FILE_EXTENSIONS: Final[tuple[str, ...]] = ("log", "cue")

#: What a person can shorten to fix a name, by the cyanrip key that put it there.
#: A key missing from this map (``track``, a literal) is nothing the track table
#: can edit. The phrasing differs by kind so the message reads as a sentence:
#: a track's own title is "its title", the album's is "the album title".
_TRACK_FIELD_PHRASES: Final[dict[str, str]] = {
    "title": "its title",
    "artist": "its artist",
    "album": "the album title",
    "album_artist": "the album artist",
    "date": "the year",
}
_ALBUM_FIELD_PHRASES: Final[dict[str, str]] = {
    "album": "the album title",
    "album_artist": "the album artist",
    # In a FOLDER, `{artist}` is the album artist: we never send an album-level
    # `artist` and cyanrip fills it from `album_artist` (the note on
    # `cyanrip_backend._album_level_tags`).
    "artist": "the album artist",
    "date": "the year",
}

#: What the message says when no editable value made the name long, i.e. the
#: template's own literal text did.
_TEMPLATE_PHRASE: Final[str] = "the file naming scheme in Settings"


@dataclass(frozen=True)
class OverlongName:
    """One folder or file name a rip would need that no Linux filesystem can hold.

    ``kind`` is ``"folder"`` (one level of the album folder), ``"log"`` (the rip
    log and cue sheet) or ``"track"`` (a track's audio file). ``track`` is the
    track number for a ``"track"``, else ``None``. ``fields`` are the phrases for
    the values the person can shorten, in the order they appear in the name.
    ``name`` is the predicted name, kept for the log; the user-facing message
    deliberately leaves it out, because it is too long to read in a dialog.
    """

    kind: str
    track: int | None
    fields: tuple[str, ...]
    byte_count: int
    name: str

    def message(self) -> str:
        """The sentence a person reads: what, how long, the limit, what to fix."""
        if self.kind == "track":
            what = f"Track {self.track}’s file name"
        elif self.kind == "log":
            what = "The rip log’s file name"
        else:
            what = "The album folder’s name"
        fix = " or ".join(self.fields) if self.fields else _TEMPLATE_PHRASE
        return (
            f"{what} would be {self.byte_count} bytes; the limit is "
            f"{naming.NAME_MAX_BYTES} — shorten {fix}."
        )


@dataclass(frozen=True)
class RipNaming:
    """What the track table needs to predict a rip's names before Start.

    The same values the rip is built from, snapshotted by the main window
    (``_rip_metadata_for``, the snapshot the rip itself is handed), so the names
    the table checks are the names the argv will produce.
    """

    track_template: str
    metadata: RipMetadata
    disc_track_total: int | None = None
    #: The tracks ticked in the Rip? column; empty means the whole disc.
    only_tracks: tuple[int, ...] = ()
    #: The extension a selected derived format adds beside each FLAC, or "".
    derived_extension: str = ""


def describe(found: Sequence[OverlongName]) -> str:
    """One message for every over-long name: the first in full, the rest COUNTED.

    A dialog that named only the first would send a person round the loop once
    per track, and one that dropped the rest silently would read as complete
    (CLAUDE.md: any elision is counted and marked). Every one is in the log.
    """
    if not found:
        return ""
    text = found[0].message()
    others = len(found) - 1
    if others:
        noun = "name is" if others == 1 else "names are"
        text += f" {others} more {noun} too long as well; each is listed in the log."
    return text


def _track_number_text(number: int, disc_track_total: int) -> str:
    """``{track}`` as cyanrip renders it: padded to 2 digits when the disc has
    more than 9 tracks and to 3 when it has more than 99, otherwise as is
    (``cyanrip@eca33dc:src/naming.c:239-250``)."""
    width = 3 if disc_track_total > 99 else 2 if disc_track_total > 9 else 1
    return str(number).zfill(width)


def _phrases(
    scheme: str, tags: dict[str, str], phrases: dict[str, str]
) -> tuple[str, ...]:
    """The editable values in ``scheme`` that hold text, deduplicated, in order.

    A key with no value renders as its own short NAME (``render_scheme``), so it
    cannot be what made a name long, and naming it would send the person to a
    blank field.
    """
    found: list[str] = []
    for key in naming.scheme_keys(scheme):
        phrase = phrases.get(key)
        if phrase and tags.get(key) and phrase not in found:
            found.append(phrase)
    return tuple(found)


def _measure(
    kind: str,
    track: int | None,
    scheme: str,
    tags: dict[str, str],
    extensions: Sequence[str],
    phrases: dict[str, str],
) -> OverlongName | None:
    """Render one component of ``scheme`` and report it when it does not fit.

    With ``extensions``, the name is measured once per extension and the longest
    reported, because each one is a separate file cyanrip or the transcoder
    creates and every one of them has to fit.
    """
    rendered = naming.render_scheme(scheme, tags)
    names = [f"{rendered}.{ext}" for ext in extensions] if extensions else [rendered]
    longest = max(names, key=naming.name_bytes_on_disk)
    size = naming.name_bytes_on_disk(longest)
    if size <= naming.NAME_MAX_BYTES:
        return None
    return OverlongName(
        kind=kind,
        track=track,
        fields=_phrases(scheme, tags, phrases),
        byte_count=size,
        name=longest,
    )


def _default_track_scheme(position: tuple[int, int] | None) -> str:
    """cyanrip's own ``-F`` default, for a template with no file part.

    ``{if #totaldiscs# > #1#|disc|.}{track} - {title}``
    (``cyanrip@eca33dc:src/cyanrip_main.c:2354``), with its condition resolved the
    way ``_path_schemes`` resolves ``%N``: from the position ``-c`` sends.
    """
    if position is not None and position[1] > 1:
        return f"{position[0]}.{{track}} - {{title}}"
    return "{track} - {title}"


def _log_scheme(position: tuple[int, int] | None) -> str:
    """cyanrip's log and cue name scheme, ``{album}{if #totaldiscs# > #1# CD|disc|}``
    (``cyanrip@eca33dc:src/cyanrip_main.c:2355-2356``; we send no ``-L``/``-M``),
    its condition resolved from the position ``-c`` sends. With no ``-c`` cyanrip
    has no ``totaldiscs`` and the condition is false."""
    if position is not None and position[1] > 1:
        return f"{{album}} CD{position[0]}"
    return "{album}"


def _track_tags(
    album_tags: dict[str, str], track: TrackTag, disc_track_total: int
) -> dict[str, str]:
    """The tags cyanrip renders a track's file name from.

    A track's dictionary is its own tags with the album's copied in UNDER them
    (``AV_DICT_DONT_OVERWRITE``, ``cyanrip@eca33dc:src/cyanrip_main.c:613-616``),
    so a track artist wins over the album artist and an absent one falls back to
    it, and ``{album}``/``{date}`` are the album's.
    """
    tags = dict(album_tags)
    tags["track"] = _track_number_text(track.number, disc_track_total)
    if track.title:
        tags["title"] = track.title
    if track.artist:
        tags["artist"] = track.artist
    return tags


def overlong_names(
    track_template: str,
    metadata: RipMetadata | None,
    *,
    disc_track_total: int | None = None,
    only_tracks: Sequence[int] = (),
    derived_extension: str = "",
) -> tuple[OverlongName, ...]:
    """Every folder or file name this rip would need that is over 255 bytes.

    ``track_template``, ``metadata`` and ``disc_track_total`` are what the argv
    builder is handed, and the names are rendered from exactly what it sends.
    ``only_tracks`` limits the track files to the ones being ripped (empty means
    every track, as it does for ``-l``); a track the disc does not have is skipped,
    as ``_metadata_args`` skips its ``-t``. ``derived_extension`` is the
    extension a selected derived format will add beside each FLAC (``"mp3"``),
    or ``""`` for none.

    Empty when everything fits. Pure; never raises.
    """
    meta = tag_hygiene.clean_tag_only_fields(metadata or RipMetadata()).metadata
    position = cyanrip_backend._disc_position(meta)
    folder_scheme, file_scheme = cyanrip_backend._path_schemes(
        track_template if isinstance(track_template, str) else "", meta, position
    )
    album_tags = cyanrip_backend._album_level_tags(meta)
    found: list[OverlongName] = []

    # The album folder, one level at a time: NAME_MAX is per component, and a
    # folder scheme with three levels is three names. No `-D` means cyanrip's own
    # default folder, which `predicted_album_folder` renders the same way.
    folder = folder_scheme or cyanrip_backend.DEFAULT_FOLDER_FOR_OUR_RIP
    for segment in folder.split("/"):
        overlong = _measure(
            "folder", None, segment, album_tags, (), _ALBUM_FIELD_PHRASES
        )
        if overlong is not None:
            found.append(overlong)

    # The rip log and cue sheet, created at the start of the rip in that folder.
    overlong = _measure(
        "log",
        None,
        _log_scheme(position),
        album_tags,
        _SIDE_FILE_EXTENSIONS,
        _ALBUM_FIELD_PHRASES,
    )
    if overlong is not None:
        found.append(overlong)

    # Each track's file, created only AFTER that track has been read: the case
    # that wasted the read time, and the one the owner's interim exists for.
    extensions = (
        (_MASTER_EXTENSION, derived_extension)
        if derived_extension
        else (_MASTER_EXTENSION,)
    )
    track_scheme = file_scheme or _default_track_scheme(position)
    numbers = [t.number for t in meta.tracks if isinstance(t.number, int)]
    width_basis = disc_track_total or max(numbers, default=0)
    wanted = set(only_tracks)
    for track in meta.tracks:
        if not isinstance(track.number, int):
            continue
        if wanted and track.number not in wanted:
            continue
        if disc_track_total and track.number > disc_track_total:
            continue
        overlong = _measure(
            "track",
            track.number,
            track_scheme,
            _track_tags(album_tags, track, width_basis),
            extensions,
            _TRACK_FIELD_PHRASES,
        )
        if overlong is not None:
            found.append(overlong)
    return tuple(found)


def overlong_names_for(naming: RipNaming) -> tuple[OverlongName, ...]:
    """:func:`overlong_names` for a :class:`RipNaming` snapshot."""
    return overlong_names(
        naming.track_template,
        naming.metadata,
        disc_track_total=naming.disc_track_total,
        only_tracks=naming.only_tracks,
        derived_extension=naming.derived_extension,
    )


def log_overlong(found: Sequence[OverlongName], where: str) -> None:
    """Write every over-long name to the log, the predicted name included."""
    for item in found:
        log.warning(
            "%s: %s (predicted name %r, %d bytes)",
            where,
            item.message(),
            item.name,
            item.byte_count,
        )


def assert_names_fit(
    track_template: str,
    metadata: RipMetadata | None,
    *,
    disc_track_total: int | None = None,
    only_tracks: Sequence[int] = (),
) -> None:
    """The argv chokepoint's half: raise :class:`RipError` when a name will not fit.

    Checks the FLAC only: the argv builder does not know the derived format, and
    no derived extension is longer than ``flac`` (``tests/test_title_filenames.py``
    holds that, so a longer one turns a test red rather than this check blind).
    The track table's check, which does know it, measures both.
    """
    found = overlong_names(
        track_template,
        metadata,
        disc_track_total=disc_track_total,
        only_tracks=only_tracks,
    )
    if found:
        log_overlong(found, "refusing to start a rip")
        raise RipError(describe(found))
