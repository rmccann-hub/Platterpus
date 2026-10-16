# SPDX-License-Identifier: GPL-3.0-only
"""Which ISRC each track's files carry, and what the disc itself says (TASKS R20).

**Why this exists.** An ISRC is the recording's international code. Two sources
can give one: MusicBrainz, which the app looks up and hands cyanrip with ``-t``
(``adapters/cyanrip_backend.py``), and the disc, whose sub-channel can carry a
code per track. Since the fork's ``.23`` (round 32), cyanrip reads the disc's
own code for every audio track **even when we passed one**, keeps it apart from
the one the files carry, and writes both into its ``-j`` record. The log's
``ISRC:`` line and the tags show only the value we passed
(``cyanrip@891c79e:src/cyanrip_main.c:886-888``), so until this module the
disc's own reading reached nothing a user could see.

**What the record says, per track** (``cyanrip@891c79e:src/diagnostics.c:
359-371``, and the provider contract in our tree,
``docs/handshake/inbound/artifacts/round-34-lap-01-provider-contract-
g3f71347.md`` lines 1164-1177):

* ``number`` (int) and ``audio_ripped`` (bool): a pass limited to some tracks
  (``-l``, the securing pass, a cancel) lists every track; the rest say false.
* ``isrc_written``: the code the files carry; null with no files, or none passed.
* ``isrc_disc``: the disc's own code, or null, with ``isrc_disc_reason`` saying
  why (``"not read"``, ``"data track"``, ``"libcdio returned none"`` and others).

**The agreed direction** (round 34, the fork's answer relayed 2026-10-16): the
disc's value is the better source when it is well formed, MusicBrainz's is the
fallback, both are recorded, and a mismatch is information, not an error. This
module is the *recording* half, which needs nothing from the fork: it states
both values and whether they agree. The *preferring* half needs a cyanrip
option and log line, and is round 35's (TASKS R20).

**Tri-state throughout**: an absent or foreign record is *not determined*, and a
track with a field missing or mistyped compares as ``not_determined``. Pure
except :func:`read_isrcs`, which reads one file and never raises. Qt-free.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus import inbound_text
from platterpus.ripper_ending import (
    DESCRIBES,
    MAX_RECORD_BYTES,
    RECORD_SCHEMA_PREFIX,
    STATE_ABSENT,
    STATE_NOT_READ,
    STATE_NOT_REQUESTED,
    STATE_READ,
    STATE_UNREADABLE,
    STATE_UNRECOGNISED,
)

log = logging.getLogger(__name__)

#: ISO 3901: country (2 letters), registrant (3 letters or digits), year (2
#: digits), designation (5 digits). Hyphens are normalised away first.
ISRC_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}")

#: An audio CD has at most 99 tracks. A record listing more is not trusted to
#: be complete: the rows past this bound are dropped, and the drop is counted.
MAX_TRACKS: Final[int] = 99

#: A longer value is cut and the cut counted (an ISRC is 12, a reason under 50).
MAX_VALUE_CHARS: Final[int] = 64

#: How the two values compare, per track.
AGREE: Final[str] = "agree"
DIFFER: Final[str] = "differ"
DISC_ONLY: Final[str] = "disc_only"
WRITTEN_ONLY: Final[str] = "written_only"
NEITHER: Final[str] = "neither"
#: No files of this track were written this pass, so there is nothing to compare.
NOT_RIPPED: Final[str] = "not_ripped"
NOT_DETERMINED: Final[str] = "not_determined"


@dataclass(frozen=True)
class TrackIsrc:
    """One track's two ISRCs, as the record states them. ``None`` is null."""

    number: int
    written: str | None
    disc: str | None
    disc_reason: str | None
    #: ``audio_ripped`` as the record states it; ``None`` when absent.
    ripped: bool | None = None
    #: False when a field was missing or of the wrong type: the track then
    #: compares as ``not_determined`` rather than as whatever the gap implied.
    complete: bool = True


@dataclass(frozen=True)
class IsrcReading:
    """What the record says about every track's ISRC."""

    state: str
    detail: str = ""
    tracks: tuple[TrackIsrc, ...] = ()
    #: Rows dropped past :data:`MAX_TRACKS`, or skipped as not a track at all.
    dropped: int = 0


def normalise(code: str) -> str:
    """An ISRC as compared and checked: hyphens and spaces gone, upper case."""
    return code.replace("-", "").replace(" ", "").upper()


def well_formed(code: str | None) -> bool | None:
    """Whether ``code`` is an ISO 3901 ISRC. ``None`` when there is no code."""
    if code is None:
        return None
    return ISRC_PATTERN.fullmatch(normalise(code)) is not None


def agreement(track: TrackIsrc) -> str:
    """How the files' ISRC compares with the disc's. Pure.

    Compared after :func:`normalise`, so ``GB-AAA-99-00001`` and
    ``GBAAA9900001`` agree. A malformed disc value still compares: whether it
    is well formed is said beside it, not folded into this answer.
    """
    if not track.complete:
        return NOT_DETERMINED
    if track.ripped is False:
        return NOT_RIPPED
    if track.written is None and track.disc is None:
        return NEITHER
    if track.written is None:
        return DISC_ONLY
    if track.disc is None:
        return WRITTEN_ONLY
    return AGREE if normalise(track.written) == normalise(track.disc) else DIFFER


def parse_isrcs(text: str) -> IsrcReading:
    """Read every track's ISRC fields out of a record's text. Pure; never raises."""
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        return IsrcReading(STATE_UNREADABLE, f"not valid JSON: {exc}")
    if not isinstance(data, Mapping):
        return IsrcReading(STATE_UNRECOGNISED, "the record is not a JSON object")
    schema = data.get("schema")
    if not isinstance(schema, str) or not schema.startswith(RECORD_SCHEMA_PREFIX):
        return IsrcReading(
            STATE_UNRECOGNISED,
            f"its schema is {_value(schema)!r}, not {RECORD_SCHEMA_PREFIX}…",
        )
    rip = data.get("rip")
    rows = rip.get("track_state") if isinstance(rip, Mapping) else None
    if not isinstance(rows, list):
        # A run refused before it ripped has `rip: null`; an older build has no
        # `track_state`. Read, and nothing to say: not the same as unreadable.
        return IsrcReading(STATE_READ, "the record lists no tracks")
    tracks: list[TrackIsrc] = []
    dropped = 0
    for row in rows:
        track = _track(row)
        if track is None or len(tracks) >= MAX_TRACKS:
            dropped += 1
            continue
        tracks.append(track)
    return IsrcReading(STATE_READ, tracks=tuple(tracks), dropped=dropped)


def read_isrcs(path: Path | None) -> IsrcReading:
    """Read the record at ``path``. Never raises.

    The same file :func:`platterpus.ripper_ending.read_ending` reads, read on
    the rip worker's thread at the same two moments. ``None`` is a rip that
    named no record.
    """
    if path is None:
        return IsrcReading(STATE_NOT_REQUESTED)
    try:
        size = path.stat().st_size
        if size > MAX_RECORD_BYTES:
            return IsrcReading(
                STATE_UNREADABLE,
                f"{path.name} is {size} bytes, over the {MAX_RECORD_BYTES}-byte bound",
            )
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return IsrcReading(STATE_ABSENT, str(path))
    except OSError as exc:
        log.warning("could not read cyanrip's -j record %s for ISRCs: %r", path, exc)
        return IsrcReading(STATE_UNREADABLE, f"{path.name}: {exc}")
    reading = parse_isrcs(text)
    if reading.dropped:
        log.warning(
            "-j record %s: %d track_state row(s) not read for ISRCs",
            path,
            reading.dropped,
        )
    return reading


def report_block(reading: IsrcReading | None) -> dict[str, object]:
    """The report's ``disc.isrc_provenance`` block (schema v35). Pure."""
    found = reading if reading is not None else IsrcReading(STATE_NOT_READ)
    rows: list[dict[str, object]] = [
        {
            "number": track.number,
            "audio_ripped": track.ripped,
            "written": track.written,
            "disc": track.disc,
            "disc_reason": track.disc_reason,
            "disc_well_formed": well_formed(track.disc),
            "agreement": agreement(track),
        }
        for track in found.tracks
    ]
    return {
        "describes": DESCRIBES,
        "state": found.state,
        "detail": found.detail or None,
        "tracks": rows,
        "rows_not_read": found.dropped,
    }


def findings(block: object) -> list[tuple[str, str]]:
    """The report's ``(issue code, sentence)`` pairs for a block. Pure.

    Information only (the round-34 agreement): a disc whose code differs from
    MusicBrainz's is worth knowing, not a failed rip. Each sentence names both
    values, never one quietly preferred.
    """
    if not isinstance(block, Mapping):
        return []
    rows = block.get("tracks")
    found: list[tuple[str, str]] = []
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, Mapping):
            continue
        number = row.get("number")
        disc = row.get("disc")
        if row.get("agreement") == DIFFER:
            found.append(
                (
                    "isrc_disc_differs",
                    f"track {number}: the disc's own ISRC is {disc}, the files "
                    f"carry {row.get('written')} (from MusicBrainz)",
                )
            )
        if isinstance(disc, str) and row.get("disc_well_formed") is False:
            found.append(
                (
                    "isrc_disc_malformed",
                    f"track {number}: the disc's own ISRC {disc!r} is not a "
                    "well-formed ISO 3901 code",
                )
            )
    return found


def _track(row: object) -> TrackIsrc | None:
    """One ``track_state`` row, or ``None`` when it is not a track at all."""
    if not isinstance(row, Mapping):
        return None
    number = row.get("number")
    if not isinstance(number, int) or isinstance(number, bool):
        return None
    complete = all(key in row for key in ("isrc_written", "isrc_disc"))
    written = _optional(row.get("isrc_written"))
    disc = _optional(row.get("isrc_disc"))
    reason = _optional(row.get("isrc_disc_reason"))
    for key, parsed in (("isrc_written", written), ("isrc_disc", disc)):
        if row.get(key) is not None and parsed is None:
            complete = False  # present, but not a string
    ripped = row.get("audio_ripped")
    return TrackIsrc(
        number,
        written,
        disc,
        reason,
        ripped=ripped if isinstance(ripped, bool) else None,
        complete=complete,
    )


def _optional(value: object) -> str | None:
    return _value(value) if isinstance(value, str) else None


def _value(value: object) -> str:
    """A screened value: control characters escaped, length bounded, cut counted."""
    text = inbound_text.screen_line(str(value)).text
    if len(text) <= MAX_VALUE_CHARS:
        return text
    cut = len(text) - MAX_VALUE_CHARS
    return f"{text[:MAX_VALUE_CHARS]}… [{cut} more characters]"
