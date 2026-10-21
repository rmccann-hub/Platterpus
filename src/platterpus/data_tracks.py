"""Which tracks are DATA tracks, and how many AUDIO tracks a rip is measured against.

**Why this module exists** (TASKS R13, 2026-10-21). An Enhanced CD (a "mixed" or
"CD-Extra" disc) carries a data track beside its audio. cyanrip's ``Disc tracks:``
count is ``cdio_cddap_tracks()``, which counts that data track
(``cyanrip@eca33dc7:src/cyanrip_main.c:405``, printed at
``src/cyanrip_log.c:1015``), and from the fork's ``.23`` the log holds a block for
it as well. A data track has no samples, no EAC CRC and no AccurateRip result:
``cyanrip_log_track_end()`` returns before the ``Accurip`` rows for one
(``cyanrip@eca33dc7:src/cyanrip_log.c:560-590``). So every surface that compared
its audio tally against the disc total counted the data track as an audio track
that "produced no result": a mixed disc whose every audio track verified read
"⚠ 2 of 3 tracks verified … 1 track produced no result", and the EAC-layout log
closed with "Some tracks could not be verified as accurate".

**One predicate, one key, many callers.** :func:`is_data_track` is the only test
of "is this a data track"; :func:`audio_track_totals` is the only place the disc
total becomes an audio total. The verdict banner, the JSON verdict, the
EAC-layout log, the status line, the disc-info panel, the read-speed ladder, the
artifact grading and the CTDB refusal all ask here, so they cannot count two
different populations (``CLAUDE.md``: *do two surfaces answer this question, and
do they use the same key?*). Kept apart from ``verdict`` because it is not about
AccurateRip; it is about which tracks AccurateRip could ever speak to.

Pure, Qt-free, and imports nothing from the package, so the parser can take
:data:`DATA_TRACK_MARKER` from here without a cycle. Every function reads via
``getattr`` and never raises.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

#: The substring every data track's ``TrackResult.status`` carries.
#: ``parsers.cyanrip_log.DATA_TRACK_STATUSES`` is built from it, so the parser that
#: writes a data status and :func:`is_data_track`, which reads one, cannot drift.
DATA_TRACK_MARKER: Final[str] = "data track"


def is_data_track(track: object) -> bool:
    """True when ``track`` is a DATA track, not an audio one.

    THE predicate for "leave this track out of anything about audio". Before this
    existed, two modules restated the substring test beside the verdict, which
    did not test at all. A status that is not a string is not a data status.
    """
    status = getattr(track, "status", "")
    return isinstance(status, str) and DATA_TRACK_MARKER in status.casefold()


def data_track_numbers(rip_log: object) -> list[int]:
    """The numbers of the data tracks the log holds a block for, in log order.

    Separate from the count so a surface can NAME them (the verdict's closing
    sentence, the CTDB refusal) as well as leave them out. A non-int number is
    skipped, since there is nothing to name.
    """
    tracks = getattr(rip_log, "tracks", ()) or ()
    return [
        n
        for t in tracks
        if is_data_track(t) and isinstance(n := getattr(t, "number", None), int)
    ]


def audio_track_totals(
    rip_log: object, disc_track_total: int | None
) -> tuple[int, int]:
    """``(expected, logged)``: how many AUDIO tracks there should be, and are logged.

    ``disc_track_total`` is what every caller already has: cyanrip's ``Disc
    tracks:``, or a ``-l`` selection's size (``verdict.expected_track_total``),
    either of which counts a data track. Each data track the LOG holds is taken
    out of both numbers. ``expected`` falls back to ``logged`` when the disc total
    is unknown.

    **The residue, stated:** a data track the log never reached (a rip stopped
    before it) cannot be told to be one, because the log is the only record of
    which tracks are data; the disc probe (``cyanrip -I``) prints only the count.
    It stays in ``expected`` and reads as never ripped, which for a stopped rip is
    true of it.
    """
    try:
        tracks = getattr(rip_log, "tracks", ()) or ()
        data = sum(1 for t in tracks if is_data_track(t))
        logged = len(tracks) - data
        if disc_track_total and disc_track_total > 0:
            return max(0, disc_track_total - data), logged
        return logged, logged
    except (TypeError, ValueError):
        return 0, 0


def data_track_sentence(numbers: Sequence[int]) -> str:
    """``" Track 1 is a data track, which AccurateRip does not cover."``, or ``""``.

    The verdict ends with it, so a reader who sees "all 2 tracks" beside a 3-track
    TOC is told why, rather than left to wonder which track was dropped. Leads
    with a space, because it is appended to a sentence.
    """
    if not numbers:
        return ""
    if len(numbers) == 1:
        return f" Track {numbers[0]} is a data track, which AccurateRip does not cover."
    named = ", ".join(str(n) for n in numbers[:-1]) + f" and {numbers[-1]}"
    return f" Tracks {named} are data tracks, which AccurateRip does not cover."
