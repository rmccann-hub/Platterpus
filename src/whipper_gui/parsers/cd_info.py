"""Parse `whipper cd info` output into a DiscInfo record.

Whipper emits three lines for the `Info` command (verified against
whipper-team/whipper master, command/cd.py):

    CDDB disc id: 940A6A0B
    MusicBrainz disc id wzr8h2ssXg4...
    MusicBrainz lookup URL https://musicbrainz.org/cdtoc/attach?id=...

Note the deliberate inconsistency: "CDDB disc id:" has a colon, but
"MusicBrainz disc id" and "MusicBrainz lookup URL" do not. That's
upstream's choice; the parser accepts both styles via named-group
regex alternation.

Missing fields are returned as empty strings rather than None — a CDDB
disc id is always derivable from a TOC, so a missing one would only
happen if whipper changed its output, which we'd notice immediately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CDDB_DISC_ID = re.compile(r"^CDDB disc id:\s*(?P<value>\S+)\s*$")
_MB_DISC_ID = re.compile(r"^MusicBrainz disc id\s+(?P<value>\S+)\s*$")
_MB_URL = re.compile(r"^MusicBrainz lookup URL\s+(?P<value>\S+)\s*$")


@dataclass(frozen=True)
class DiscInfo:
    """Output of `whipper cd info`."""

    cddb_disc_id: str = ""
    musicbrainz_disc_id: str = ""
    musicbrainz_submit_url: str = ""


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

    return DiscInfo(
        cddb_disc_id=cddb,
        musicbrainz_disc_id=mb_id,
        musicbrainz_submit_url=mb_url,
    )
