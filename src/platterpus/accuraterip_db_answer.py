# SPDX-License-Identifier: GPL-3.0-only
"""Does AccurateRip's database hold one checksum for one track? Tri-state.

**Why this module exists** (TASKS R138, round 39's gate G2, 2026-11-11). A CTDB
repair rewrites a track, and the repaired file's AccurateRip v1 and v2 are
computed from it (``accuraterip_crc.py``). The database's answer for the disc is
fetched by ``adapters/accuraterip_db.py``. This module puts the two together, one
version of one track at a time, into one of three answers and only these:

* **matched** at confidence N: some response's CRC for the track equals ours
  (the strongest such response's confidence, if more than one does);
* **not in the database**: AccurateRip has no entry for the disc (a 404), or it
  has the disc, the reply was read whole, and no response holds this CRC;
* **not determined**, with the reason: no checksum was computed, no lookup ran,
  the lookup failed, or the reply was cut short and the CRC was not in the part
  that was read.

The record and its wording read these (``ctdb/repair_types.RepairedTrack``,
``ctdb/repair_wording.accuraterip_after_repair``). The types are here and not in
the adapter, so the repair's pure data modules do not import a network module.
Pure; reads the lookup with ``getattr``; never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from platterpus.parsers.accuraterip_dbar import entries_for_track

#: The three answers (:class:`ArDbAnswer.answer`).
AR_MATCHED: Final[str] = "matched"
AR_NOT_IN_DATABASE: Final[str] = "not_in_database"
AR_NOT_DETERMINED: Final[str] = "not_determined"
AR_ANSWERS: Final[frozenset[str]] = frozenset(
    {AR_MATCHED, AR_NOT_IN_DATABASE, AR_NOT_DETERMINED}
)

#: Why the answer is not determined when no lookup was made at all.
NO_LOOKUP: Final[str] = "no AccurateRip lookup of the repaired audio was made"


@dataclass(frozen=True)
class ArDbAnswer:
    """One version of one track against the database: :data:`AR_ANSWERS`.

    ``confidence`` is set only for :data:`AR_MATCHED`; ``reason`` says why for
    the other two.
    """

    answer: str
    confidence: int | None = None
    reason: str = ""


@dataclass(frozen=True)
class ArLookupSummary:
    """The disc's lookup, in brief, for the record: its state, URL and size.

    ``state`` is ``adapters.accuraterip_db.LookupState``'s value (``found``,
    ``not_in_database``, ``failed``), or ``not_made`` when no lookup ran.
    """

    state: str
    url: str = ""
    responses: int = 0
    complete: bool = False
    trailing_bytes: int = 0
    reason: str = ""


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def summarize(lookup: object | None, *, why_not: str = NO_LOOKUP) -> ArLookupSummary:
    """:class:`ArLookupSummary` of a ``DbarLookup``; ``not_made`` for None."""
    if lookup is None:
        return ArLookupSummary("not_made", reason=why_not)
    state = getattr(getattr(lookup, "state", None), "value", None)
    responses = getattr(lookup, "responses", ()) or ()
    return ArLookupSummary(
        state=state if isinstance(state, str) else "failed",
        url=str(getattr(lookup, "url", "") or ""),
        responses=len(responses) if isinstance(responses, tuple) else 0,
        complete=getattr(lookup, "complete", False) is True,
        trailing_bytes=_int(getattr(lookup, "trailing_bytes", 0)) or 0,
        reason=str(getattr(lookup, "reason", "") or ""),
    )


def answer_for(lookup: object | None, track: int, crc: object) -> ArDbAnswer:
    """Whether the database holds ``crc`` for ``track`` (1-based). Never raises.

    ``lookup`` is an ``adapters.accuraterip_db.DbarLookup`` (or None when none
    was made); ``crc`` our checksum of the repaired audio, an int.
    """
    ours = _int(crc)
    if ours is None:
        return ArDbAnswer(
            AR_NOT_DETERMINED, reason="no AccurateRip checksum of it was computed"
        )
    summary = summarize(lookup)
    if summary.state == "not_in_database":
        return ArDbAnswer(
            AR_NOT_IN_DATABASE, reason=summary.reason or "AccurateRip has no entry"
        )
    if summary.state != "found":
        return ArDbAnswer(AR_NOT_DETERMINED, reason=summary.reason or NO_LOOKUP)
    responses = getattr(lookup, "responses", ()) or ()
    if not isinstance(responses, tuple):
        return ArDbAnswer(AR_NOT_DETERMINED, reason="the lookup held no responses")
    entries = entries_for_track(responses, track)
    matched = [confidence for value, confidence in entries if value == ours]
    if matched:
        return ArDbAnswer(AR_MATCHED, confidence=max(matched))
    if not summary.complete:
        return ArDbAnswer(
            AR_NOT_DETERMINED,
            reason=(
                "not in the part of AccurateRip's reply that was read, and the "
                f"reply was cut short ({summary.reason or 'incomplete'})"
            ),
        )
    return ArDbAnswer(
        AR_NOT_IN_DATABASE,
        reason=(
            f"AccurateRip holds this disc ({summary.responses} responses, "
            f"{len(entries)} entries for track {track}) and not this checksum"
        ),
    )
