# SPDX-License-Identifier: GPL-3.0-only
"""How many tracks the DISC has, for deciding whether a CTDB lookup is sound.

**Why this is a question at all.** CTDB identifies a disc by its whole table of
contents, and the only TOC the verify can build is from the FLAC files the rip
wrote (:func:`platterpus.ctdb.toc.disc_toc_from_files`). So the TOC is the
disc's TOC only when the files are *every* track. A partial rip — a ``-l 1,2``
selection in the Rip? column — sends CTDB a two-track disc that does not exist,
gets a 404, and used to be reported as *"this disc is not in CTDB"* about a disc
CTDB holds 102 entries for. The 2026-09-28 Full run filed five such reports (its
bundle is round 28's artifacts folder under ``docs/handshake/``).

**Where the number comes from, in order.** "Count the files" cannot answer this:
it is the thing being checked. The witnesses are:

1. **The ripper's own footer**, ``Rip completed: yes (2 of 14 tracks)``. Its
   second number is the disc's total, printed by the binary that wrote the
   files, off the physical TOC (``RipLog.rip_completed_total``). It is the same
   number :mod:`platterpus.album_loudness` reads to decide whether the album
   loudness figures cover the disc, so the two surfaces answer "was this the
   whole disc?" from one key. Fork builds print it on every rip.
2. **The caller's fallback**, for a build with no such footer: in the GUI, the
   ``Disc tracks:`` count cyanrip printed when the disc was probed
   (``DiscInfo.num_tracks``) — the same binary's count, read earlier.

The footer wins when both exist, because it was written by the rip being
verified. Neither present means ``None``: *not known*, which is never read as
"whole disc" or as "partial" — the verify then does what it always did.

Pure; never raises; Qt-free.
"""

from __future__ import annotations

from typing import Final

#: The wire value of ``ctdb.verify.Verdict.NOT_WHOLE_DISC``, spelled ONCE, here.
#: The enum takes its value from this, and ``rip_report`` compares the report's
#: ``ctdb.verdict`` against it — importing the enum instead would drag the CTDB
#: HTTP adapter into a builder that is kept adapter-free, and spelling the string
#: twice is the join that let ``"error"`` stand in for ``"lookup_error"`` from
#: v0.5.12 to 2026-08-18 with nothing to notice.
NOT_WHOLE_DISC_VERDICT: Final[str] = "not_whole_disc"

#: The Red Book limit: a CD holds at most 99 tracks. A "disc track count" outside
#: 1..99 is not a count a file list can be compared against — it is a parse not
#: to trust — so it reads as "not known" rather than as a number.
MAX_CD_TRACKS: Final[int] = 99


def plausible_track_count(value: object) -> int | None:
    """``value`` if it is a whole number of CD tracks (1..99), else ``None``."""
    # `bool` is an `int` subclass, and `True` is not "one track".
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 1 <= value <= MAX_CD_TRACKS else None


def disc_track_count(rip_log: object | None, *, fallback: object = None) -> int | None:
    """How many tracks the disc has — not the rip — or ``None`` if nothing says.

    ``rip_log`` is a parsed ripper log (or ``None``); it is read via ``getattr``,
    like every consumer of one, so a log-shaped object of any kind degrades to
    ``None`` instead of raising. ``fallback`` is the caller's second witness
    (see the module docstring); it is range-checked exactly like the footer,
    because it is just as much external input.
    """
    stated = plausible_track_count(getattr(rip_log, "rip_completed_total", None))
    if stated is not None:
        return stated
    return plausible_track_count(fallback)
