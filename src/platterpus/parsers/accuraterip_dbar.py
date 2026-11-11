# SPDX-License-Identifier: GPL-3.0-only
"""Reading an AccurateRip ``dBAR`` file: the database's answer for one disc.

**Why we read it ourselves** (TASKS R138, round 39's gate G2). AccurateRip is
asked during the rip by cyanrip, and its log prints the database's value only for
a read that MATCHED. A CTDB repair rewrites a track whose read did NOT match, so
the repaired audio's AccurateRip checksums (``accuraterip_crc.py``) have nothing
in the ripper's log to be compared with. The database's whole answer for the
disc is one small binary file (``adapters/accuraterip_db.py`` fetches it); this
module turns its bytes into values, and nothing else.

**The layout** (public; the same in every AccurateRip client, and checked by
hand against the real file for the reference disc on 2026-11-11: 1,807 bytes, 13
responses of 14 tracks). The file is a sequence of RESPONSES, one after another.
Each response is

* a 13-byte header: the track count (1 byte), then the disc's AccurateRip id1,
  id2 and CDDB id, each a little-endian unsigned 32-bit integer;
* then, per track in disc order, 9 bytes: the confidence (1 byte, how many
  submissions agree), the track's CRC (uint32 LE), and the frame-450 CRC (uint32
  LE, used by offset finding; kept, never compared here).

Which version (v1 or v2) a response's CRCs are is NOT stated in the file, so a
reader compares a track's v1 AND its v2 against every response's CRC for that
track; that is what every client does.

**External input, so it never raises** (``CLAUDE.md``: parsers of external output
never raise). Empty bytes, an HTML error page, a truncated tail, a track count of
zero: each returns what could be read, with ``problem`` saying why the rest could
not, and any bytes after the last whole response COUNTED in ``trailing_bytes``,
never dropped silently (a silent truncation reads as completeness). The id check
against the disc that was asked about is the adapter's, which knows the ids.
Pure; no I/O.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Final

#: Bytes in a response header: the track count, then id1, id2 and the CDDB id.
HEADER_BYTES: Final[int] = 13
#: Bytes per track in a response: confidence, CRC, frame-450 CRC.
TRACK_BYTES: Final[int] = 9
#: The header after its first byte, and one track: little-endian, no padding.
_IDS: Final[struct.Struct] = struct.Struct("<III")
_TRACK: Final[struct.Struct] = struct.Struct("<BII")


@dataclass(frozen=True)
class DbarTrack:
    """One track's entry in one response: how many agree, and on what."""

    confidence: int
    crc: int
    frame450_crc: int


@dataclass(frozen=True)
class DbarResponse:
    """One response: the disc it names (its header), and an entry per track."""

    track_count: int
    id1: int
    id2: int
    cddb: int
    tracks: tuple[DbarTrack, ...]


@dataclass(frozen=True)
class DbarParse:
    """Every whole response the bytes held, and why reading stopped, if early.

    ``problem`` is "" when every byte was read as whole responses. Otherwise it
    is one sentence a log or a report can carry; ``trailing_bytes`` counts the
    bytes after the last whole response, which are not read and never dropped
    without being counted.
    """

    responses: tuple[DbarResponse, ...] = ()
    trailing_bytes: int = 0
    problem: str = ""

    @property
    def complete(self) -> bool:
        """True when the bytes were whole responses, at least one, and nothing else.

        The answer a "not in the database" claim needs: a CRC missing from a
        file that was cut short may have been in the part that is missing.
        """
        return bool(self.responses) and not self.problem


def looks_like_markup(raw: bytes) -> bool:
    """True when ``raw`` opens like an HTML or XML page rather than a dBAR file.

    AccurateRip answers a path it does not have with a 404 HTML page (seen
    2026-11-11 with the wrong third path digit). A binary file can open with
    ``<`` too (a track count of 60), so the adapter's id check is the real test;
    this is only the reason given when it fails on a page.
    """
    return raw.lstrip()[:1] == b"<"


def parse_dbar(raw: bytes) -> DbarParse:
    """Every whole response in ``raw``, read in order. Never raises.

    Stops at the first response that cannot be read whole (a short header, a
    track count of zero, too few bytes for its tracks) and says why, counting
    the bytes it did not read.
    """
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        return DbarParse(problem="the reply was not bytes")
    data = bytes(raw)
    if not data:
        return DbarParse(problem="the reply was empty")
    if looks_like_markup(data):
        return DbarParse(
            trailing_bytes=len(data),
            problem="the reply was an HTML or XML page, not an AccurateRip dBAR file",
        )
    responses: list[DbarResponse] = []
    at = 0
    while at < len(data):
        left = len(data) - at
        if left < HEADER_BYTES:
            return _stopped(responses, left, f"{left} bytes after the last response")
        count = data[at]
        if count == 0:
            return _stopped(
                responses, left, f"response {len(responses) + 1} declares 0 tracks"
            )
        needed = HEADER_BYTES + count * TRACK_BYTES
        if left < needed:
            return _stopped(
                responses,
                left,
                f"response {len(responses) + 1} declares {count} tracks "
                f"({needed} bytes) and only {left} bytes remain",
            )
        id1, id2, cddb = _IDS.unpack_from(data, at + 1)
        tracks = tuple(
            DbarTrack(*_TRACK.unpack_from(data, at + HEADER_BYTES + i * TRACK_BYTES))
            for i in range(count)
        )
        responses.append(DbarResponse(count, id1, id2, cddb, tracks))
        at += needed
    return DbarParse(responses=tuple(responses))


def _stopped(responses: list[DbarResponse], left: int, why: str) -> DbarParse:
    return DbarParse(
        responses=tuple(responses),
        trailing_bytes=left,
        problem=f"the reply was cut short or malformed: {why}",
    )


def entries_for_track(
    responses: tuple[DbarResponse, ...], track: int
) -> tuple[tuple[int, int], ...]:
    """``(crc, confidence)`` for ``track`` (1-based) in every response, in order.

    A response with fewer tracks than ``track`` holds no entry for it and adds
    nothing. Never raises.
    """
    if not isinstance(track, int) or isinstance(track, bool) or track < 1:
        return ()
    found: list[tuple[int, int]] = []
    for response in responses:
        if track <= len(response.tracks):
            entry = response.tracks[track - 1]
            found.append((entry.crc, entry.confidence))
    return tuple(found)
