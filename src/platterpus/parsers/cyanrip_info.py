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

`Disc MCN:` (the disc's catalogue number) is read too, by the rip-log parser's
own reader (`disc_mcn.py`), so `-I` and a rip cannot read one line two ways:
today cyanrip prints it only when the disc has an MCN, and the fork proposes
printing it always, with `none (…)` or `unknown (…)` (their round 38 lap 3 S17).
Its line comes between `CDDB ID:` and `Album:`, where an echoed CD-TEXT value
with a line break can forge one, so a second copy makes it not determined
(`not_present`, logged) rather than the last copy winning, as the rip-log
parser's echo guard does.

Other optional metadata lines (`Release ID:`, `Album:`, …) are printed only when
known; we deliberately don't parse them — the GUI does its own MusicBrainz
lookup host-side (Critical Rule #5), so the IDs + track count are all the
backend needs to report.

The result reuses the backend-neutral :class:`DiscInfo` dataclass (shared
with the legacy disc-info parser, ``parsers/cd_info.py``), so the GUI's
disc-info handling does not depend on which parser produced it.
"""

from __future__ import annotations

import logging
import re

from platterpus import disc_mcn
from platterpus.parsers.cd_info import DiscInfo
from platterpus.safe_int import int_or_none

# Labels are anchored at line start; the value is the first non-space run.
# `\s+` between label and value: cyanrip pads with spaces for alignment.
_DISC_TRACKS = re.compile(r"^Disc tracks:\s+(?P<value>\d+)\s*$")
_DISCID = re.compile(r"^DiscID:\s+(?P<value>\S+)\s*$")
_CDDB_ID = re.compile(r"^CDDB ID:\s+(?P<value>\S+)\s*$")
# The submit URL follows its label on the NEXT line; accept only something
# URL-shaped there (printf of a NULL pointer would print "(null)").
_MB_URL_LABEL = re.compile(r"^MusicBrainz URL:\s*$")
_URL = re.compile(r"^(?P<value>https?://\S+)\s*$")

log = logging.getLogger(__name__)


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
    mcn = disc_mcn.DiscMcn()
    mcn_lines = 0
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
            # 0 already means "unknown track count" to every caller, so an
            # unusable value keeps the default rather than inventing a number.
            num_tracks = (
                int_or_none(match.group("value"), field="cyanrip disc track count") or 0
            )
            continue

        match = _DISCID.match(line)
        if match:
            mb_id = match.group("value")
            continue

        match = _CDDB_ID.match(line)
        if match:
            cddb = match.group("value")
            continue

        match = disc_mcn.LINE.match(line)
        if match:
            mcn_lines += 1
            if mcn_lines == 1:
                mcn = disc_mcn.read_value(match.group("value"))
            continue

    if mcn_lines > 1:
        # cyanrip prints the row once; a second copy is an echoed value that
        # broke a line, and neither copy can be preferred (see the docstring).
        log.warning(
            "cyanrip -I printed %d Disc MCN: lines; the MCN is not determined",
            mcn_lines,
        )
        mcn = disc_mcn.DiscMcn()

    return DiscInfo(
        cddb_disc_id=cddb,
        musicbrainz_disc_id=mb_id,
        musicbrainz_submit_url=mb_url,
        num_tracks=num_tracks,
        disc_mcn=mcn,
    )
