"""What cyanrip's album loudness rows were measured over, and the label they get.

**The rows.** After the last track cyanrip prints four rows we parse
(``parsers/cyanrip_log.py``, the ``_ALBUM_*`` patterns):

    Album integrated loudness (R128): -14.4 LUFS
    Album loudness range (R128):      6.9 LU (-18.6 to -11.7 LUFS)
    Album sample peak level:          -0.5 dBFS
    Album true peak level:            0.1 dBFS

and, as a fallback when those are absent, the same four figures from FFmpeg's
``Album Loudness Summary:`` block. They fill ``RipLog.album_loudness`` — four keys,
``integrated_lufs``, ``lra_lu``, ``sample_peak_dbfs``, ``true_peak_dbfs`` — which
reaches exactly two places: the report's ``album_loudness`` and one results-pane
line. We write no tags from them, and the EAC-compatible log carries none.

**What they cover.** Whatever audio the rip read, which is the album only when the
rip read the whole disc. The fork found it (round 26 lap 4, ``cancel-me.log:75``):
a rip interrupted early in track 1 printed "Album integrated loudness" of
-14.4 LUFS for about 40% of one track. A ``-l`` rip of two tracks prints an album
figure for those two. Both surfaces called it "Album loudness" regardless.

**The fix is ours, and it needs nothing from the fork.** The same log already says
how much was read: ``Rip completed: yes (2 of 14 tracks)`` or
``no (interrupted by SIGTERM, 0 of 14 tracks)``, and ``Interrupted at:``. So the
coverage is derived here from those, tri-state, and a part-of-disc figure is
labelled as what it is. ``not_determined`` (a log with no such footer) keeps the
ripper's own name for the rows, because calling it partial would be a claim too.

Pure; never raises.
"""

from __future__ import annotations

import logging
from typing import Final

from platterpus.report_types import AlbumLoudnessCoverage

log = logging.getLogger(__name__)

#: The rip read every track on the disc: the rows are the album's.
WHOLE_DISC: Final[str] = "whole_disc"
#: The rip read less than the disc (a ``-l`` selection, or an interrupted rip).
PART_OF_DISC: Final[str] = "part_of_disc"
#: The log does not say how much was read. Not a pass, and not a failure.
NOT_DETERMINED: Final[str] = "not_determined"

#: The ripper's own name for the rows, used when they ARE the album's or when we
#: cannot tell.
ALBUM_LABEL: Final[str] = "Album loudness"


def coverage(rip_log: object) -> AlbumLoudnessCoverage | None:
    """What ``rip_log.album_loudness`` was measured over, or ``None`` if there is none."""
    try:
        if not getattr(rip_log, "album_loudness", None):
            return None
        completed = getattr(rip_log, "rip_completed", None)
        finished = getattr(rip_log, "rip_completed_tracks", None)
        total = getattr(rip_log, "rip_completed_total", None)
        finished = finished if isinstance(finished, int) else None
        total = total if isinstance(total, int) else None
        where = getattr(rip_log, "interrupted_at", "") or None
        whole = finished is not None and total is not None and finished == total
        short = finished is not None and total is not None and finished < total
        if completed is True and whole:
            state = WHOLE_DISC
        elif completed is False or short:
            state = PART_OF_DISC
        else:
            state = NOT_DETERMINED
        return {
            "state": state,
            "tracks_finished": finished,
            "disc_tracks": total,
            "interrupted_at": where if isinstance(where, str) else None,
        }
    except Exception:  # noqa: BLE001 — a label helper must never block a report
        log.exception("could not derive what the album loudness covers")
        return None


def label(covers: AlbumLoudnessCoverage | None) -> str:
    """``Album loudness``, or what a part-of-disc figure actually measured.

    ``Loudness of what was read (0 of 14 tracks finished, then stopped at track 1,
    mid-read), not the whole album``.
    """
    if covers is None or covers.get("state") != PART_OF_DISC:
        return ALBUM_LABEL
    finished = covers.get("tracks_finished")
    total = covers.get("disc_tracks")
    detail = (
        f"{finished} of {total} tracks finished"
        if finished is not None and total is not None
        else "not every track"
    )
    where = covers.get("interrupted_at")
    if where:
        detail += f", then stopped at {where}"
    return f"Loudness of what was read ({detail}), not the whole album"
