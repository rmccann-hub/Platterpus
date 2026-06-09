"""Parse `cyanrip -I` (info-only) output into a DiscInfo record.

cyanrip prints a "start report" before doing anything (verified against
cyanreg/cyanrip master, `src/cyanrip_log.c::cyanrip_log_start_report`).
The lines we need, with their exact labels:

    Disc tracks:    16
    DiscID:         xA2hjkk0Jl0gKKtIdYuTje4JTXY-
    CDDB ID:        c50a780f

`DiscID` is the **MusicBrainz** disc ID — cyanrip computes it locally from
the disc TOC (SHA-1 per the MusicBrainz spec, `src/discid.c`), so it is
present even with MusicBrainz lookups disabled (`-N`). Same for `CDDB ID`.
That's why the adapter runs `-I -N`: disc identification needs no network.

In info-only mode cyanrip also prints the MusicBrainz *submission* URL on
the line AFTER its label (`src/cyanrip_main.c`):

    MusicBrainz URL:
    https://musicbrainz.org/cdtoc/attach?...

Optional metadata lines (`Release ID:`, `Album:`, …) are printed only when
known; we deliberately don't parse them — the GUI does its own MusicBrainz
lookup host-side (Critical Rule #5), so the IDs + track count are all the
backend needs to report.

The result reuses the backend-neutral :class:`DiscInfo` dataclass, so the
GUI handles whipper and cyanrip identically.
"""

from __future__ import annotations

import re

from whipper_gui.parsers.cd_info import DiscInfo

# Labels are anchored at line start; the value is the first non-space run.
# `\s+` between label and value: cyanrip pads with spaces for alignment.
_DISC_TRACKS = re.compile(r"^Disc tracks:\s+(?P<value>\d+)\s*$")
_DISCID = re.compile(r"^DiscID:\s+(?P<value>\S+)\s*$")
_CDDB_ID = re.compile(r"^CDDB ID:\s+(?P<value>\S+)\s*$")
# The submit URL follows its label on the NEXT line; accept only something
# URL-shaped there (printf of a NULL pointer would print "(null)").
_MB_URL_LABEL = re.compile(r"^MusicBrainz URL:\s*$")
_URL = re.compile(r"^(?P<value>https?://\S+)\s*$")


def parse_cyanrip_info(stdout: str) -> DiscInfo:
    """Parse `cyanrip -I` stdout into a DiscInfo.

    Missing fields default to empty strings / zero — including the case
    where cyanrip failed outright (no disc, bad device) and printed only
    an error message. The parser must never raise on arbitrary text.
    """
    cddb = ""
    mb_id = ""
    mb_url = ""
    num_tracks = 0
    # True while we're looking for the URL that follows "MusicBrainz URL:".
    expecting_url = False

    for line in stdout.splitlines():
        if expecting_url:
            # Tolerate a blank line between the label and the URL, but stop
            # looking once any other content appears (the report moved on).
            if not line.strip():
                continue
            match = _URL.match(line)
            if match:
                mb_url = match.group("value")
            expecting_url = False
            continue

        if _MB_URL_LABEL.match(line):
            expecting_url = True
            continue

        match = _DISC_TRACKS.match(line)
        if match:
            num_tracks = int(match.group("value"))
            continue

        match = _DISCID.match(line)
        if match:
            mb_id = match.group("value")
            continue

        match = _CDDB_ID.match(line)
        if match:
            cddb = match.group("value")
            continue

    return DiscInfo(
        cddb_disc_id=cddb,
        musicbrainz_disc_id=mb_id,
        musicbrainz_submit_url=mb_url,
        num_tracks=num_tracks,
    )
