"""Where CTDB disagrees about a track AccurateRip does not contradict: a note, never WRONG.

**The decision** (the owner's word for 0.7.119, "do 1 - 4 as recommended"):
AccurateRip stays the ONE source of "WRONG". ``verdict.track_accuraterip_contradiction``
decides it, and the status line, the notification, the disc panel, the results
table, the addendum, the report's ``health_status``, the self-check and the
EAC-layout log all ask that predicate (``tests/test_wrong_track_on_every_surface.py``).
None of that changes here.

**What this adds.** CTDB answers per track too (``ctdb/matching.py``): a track
can *differ* from every CTDB entry that carries it, or *agree only with a
minority* (``outvoted``: the entries that agree hold fewer submissions than one
entry that disagrees). Until now that answer reached only the Details tab's CTDB
sentence and the report's ``ctdb.tracks[]``; the results table showed the
ripper's clean word over such a track with nothing beside it. So a reader of the
table could not see that a second database questions the track. The track is
not WRONG (AccurateRip did not say so), and it is not silently clean either: it
carries a visible ``ⓘ`` note naming the track, and saying that AccurateRip is
the verdict.

**One predicate, every surface delegates.** :func:`ctdb_disagreements` is the
only place that decides which tracks get the note; the results table's Status
cell and tooltip and the note line under the status line both read it, and
:func:`ctdb_note_sentence` is their one wording. A track AccurateRip already
contradicts (``wrong`` or ``differs``) gets no CTDB note: its ``⚠`` is already
there, and the note's "AccurateRip is the verdict" would point at a verdict that
already says it.

**Tri-state.** CTDB's ``not_determined`` (no per-track CRCs, nothing of ours to
compare) is not a disagreement and gets no note; nor does a row this module
cannot read. Status is never colour alone: the note always carries ``ⓘ``.

Pure: reads duck-typed rows (an in-memory ``CtdbTrackResult`` or a report's
``ctdb.tracks[]`` dict) and a parsed rip log. Never raises.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Final

from platterpus.verdict import track_accuraterip_contradiction

log = logging.getLogger(__name__)

#: CTDB's per-track verdict is ``differs``: entries carry this track's CRC and
#: none agrees with ours.
CTDB_DISAGREES_DIFFERS: Final[str] = "differs"
#: CTDB's per-track verdict is ``match``, but only with a minority: the agreeing
#: submissions are fewer than one disagreeing entry's (``outvoted``).
CTDB_DISAGREES_OUTVOTED: Final[str] = "outvoted"

#: The marker every surface shows with the note, so the status is never colour
#: alone (WCAG 2.2 AA, ``docs/ux-design-principles.md``). Information, not a
#: warning: the ``⚠`` stays AccurateRip's.
NOTE_MARKER: Final[str] = "ⓘ"

#: The short form for a table cell, after the ripper's own word.
CELL_NOTE: Final[str] = f"{NOTE_MARKER} CTDB disagrees"

#: How each kind is worded inside the note's parentheses.
_KIND_WORDS: Final[dict[str, str]] = {
    CTDB_DISAGREES_DIFFERS: "differs",
    CTDB_DISAGREES_OUTVOTED: "outvoted",
}


def _field(row: object, name: str) -> object:
    """``row[name]`` for a report dict, ``row.name`` for a result object."""
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


def track_ctdb_disagreement(row: object) -> str | None:
    """How CTDB's answer for one track disagrees with our read, or None.

    :data:`CTDB_DISAGREES_DIFFERS` for a ``differs`` verdict,
    :data:`CTDB_DISAGREES_OUTVOTED` for a ``match`` that is ``outvoted``, None for
    an agreeing match, ``not_determined`` and anything unreadable. ``row`` is a
    ``CtdbTrackResult`` (whose ``verdict`` is an enum) or a report row (a plain
    string). Never raises.
    """
    try:
        verdict = _field(row, "verdict")
        value = getattr(verdict, "value", verdict)
        if value == "differs":
            return CTDB_DISAGREES_DIFFERS
        if value == "match" and _field(row, "outvoted") is True:
            return CTDB_DISAGREES_OUTVOTED
        return None
    except (AttributeError, TypeError, ValueError):
        return None


def ctdb_disagreements(
    ctdb_tracks: object, rip_log: object | None
) -> list[tuple[int, str]]:
    """``(track number, kind)`` for each track that gets the CTDB note, in CTDB order.

    A track is listed when CTDB disagrees (:func:`track_ctdb_disagreement`) AND
    AccurateRip does not contradict it (``verdict.track_accuraterip_contradiction``
    is None for that track in ``rip_log``). A track CTDB names that the log does
    not hold is listed: AccurateRip said nothing against it. ``ctdb_tracks`` is a
    result's ``tracks`` or a report's ``ctdb.tracks``; anything else is no rows.
    Never raises.
    """
    try:
        rows: Sequence[object] = (
            ctdb_tracks if isinstance(ctdb_tracks, (list, tuple)) else ()
        )
        log_tracks = getattr(rip_log, "tracks", ()) or ()
        contradicted = {
            getattr(t, "number", None)
            for t in log_tracks
            if track_accuraterip_contradiction(t) is not None
        }
        found: list[tuple[int, str]] = []
        for row in rows:
            number = _field(row, "track")
            if not isinstance(number, int) or isinstance(number, bool):
                continue
            kind = track_ctdb_disagreement(row)
            if kind is not None and number not in contradicted:
                found.append((number, kind))
        return found
    except (AttributeError, TypeError, ValueError):
        log.warning("could not read CTDB's per-track answer", exc_info=True)
        return []


def ctdb_note_sentence(found: Iterable[tuple[object, str]]) -> str:
    """The one wording of the note, or "" when no track gets it.

    ``ⓘ CTDB disagrees on track 3 (differs); AccurateRip is the verdict`` and,
    for more, ``ⓘ CTDB disagrees on tracks 1, 4 (differs) and track 7
    (outvoted); AccurateRip is the verdict``. Never says WRONG: that word is
    AccurateRip's. Never raises.
    """
    pairs = [(n, k) for n, k in found if k in _KIND_WORDS]
    parts: list[str] = []
    for kind in (CTDB_DISAGREES_DIFFERS, CTDB_DISAGREES_OUTVOTED):
        numbers = [str(n) for n, k in pairs if k == kind]
        if numbers:
            noun = "tracks" if len(numbers) > 1 else "track"
            parts.append(f"{noun} {', '.join(numbers)} ({_KIND_WORDS[kind]})")
    if not parts:
        return ""
    return (
        f"{NOTE_MARKER} CTDB disagrees on {' and '.join(parts)}; "
        "AccurateRip is the verdict"
    )
