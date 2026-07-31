"""Parse whipper's cd-info FORMAT into a DiscInfo record.

This parses the legacy `whipper cd info` output format; the current
cyanrip backend gathers disc info via `-I -N` instead, so this parser is
kept for old paths and test fixtures. Whipper emitted three lines for the
`Info` command (verified against whipper-team/whipper master,
command/cd.py):

    CDDB disc id: 940A6A0B
    MusicBrainz disc id wzr8h2ssXg4...
    MusicBrainz lookup URL https://musicbrainz.org/cdtoc/attach?id=...

Note the deliberate inconsistency: "CDDB disc id:" has a colon, but
"MusicBrainz disc id" and "MusicBrainz lookup URL" do not. That's
upstream's choice; the parser accepts both styles via named-group
regex alternation.

Missing fields are returned as empty strings rather than None — a CDDB
disc id is always derivable from a TOC, so a missing one would only
happen if this log format changed, which we'd notice immediately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from platterpus.safe_int import int_or_none

_CDDB_DISC_ID = re.compile(r"^CDDB disc id:\s*(?P<value>\S+)\s*$")
_MB_DISC_ID = re.compile(r"^MusicBrainz disc id\s+(?P<value>\S+)\s*$")
_MB_URL = re.compile(r"^MusicBrainz lookup URL\s+(?P<value>\S+)\s*$")
# "Disc duration: 01:02:08.026, 16 audio tracks". The track count lets
# the GUI show numbered (blank) rows for a disc MusicBrainz doesn't know,
# so the user still sees what's on the disc before an unknown-album rip.
# Bounded quantifier, deliberately. An unbounded `\d+` here is quadratic on a long
# run of digits, because every prefix of the run is a candidate the engine must
# reject before failing the whole match:
#
#     500 digits → 2.26 ms · 1000 → 8.82 ms · 2000 → 35.11 ms · 4000 → 141.36 ms
#
# `{1,4}` is linear (4000 digits → 0.295 ms) and loses nothing: a Red Book CD holds
# at most 99 tracks, so four digits is already two more than the format allows.
# Parsers of external output must be bounded in time as well as never-raising —
# this input is a subprocess's stdout, so its length is not ours to trust.
_NUM_TRACKS = re.compile(r"(?P<value>\d{1,4})\s+audio\s+tracks")


@dataclass(frozen=True)
class DiscInfo:
    """Output of `whipper cd info`."""

    cddb_disc_id: str = ""
    musicbrainz_disc_id: str = ""
    musicbrainz_submit_url: str = ""
    num_tracks: int = 0


def parse_cd_info(stdout: str) -> DiscInfo:
    """Parse `whipper cd info` stdout into a DiscInfo.

    Missing fields default to empty strings. The parser tolerates extra
    lines (whipper sometimes emits warnings or library noise) by
    matching on a per-line basis and ignoring anything that doesn't fit
    the known patterns.
    """
    cddb = ""
    mb_id = ""
    mb_url = ""
    num_tracks = 0

    for line in stdout.splitlines():
        match = _CDDB_DISC_ID.match(line)
        if match:
            cddb = match.group("value")
            continue

        match = _MB_DISC_ID.match(line)
        if match:
            mb_id = match.group("value")
            continue

        match = _MB_URL.match(line)
        if match:
            mb_url = match.group("value")
            continue

        # `search`, not `match`: the track count is embedded mid-line
        # ("Disc duration: ..., 16 audio tracks"), not anchored.
        match = _NUM_TRACKS.search(line)
        if match:
            # Keep the 0 default when the count is unusable — "we don't know how
            # many tracks" is what 0 already means to every caller here.
            num_tracks = (
                int_or_none(match.group("value"), field="cd-info track count") or 0
            )
            continue

    return DiscInfo(
        cddb_disc_id=cddb,
        musicbrainz_disc_id=mb_id,
        musicbrainz_submit_url=mb_url,
        num_tracks=num_tracks,
    )
