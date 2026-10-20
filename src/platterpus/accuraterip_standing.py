# SPDX-License-Identifier: GPL-3.0-only
"""What AccurateRip can say about a disc: in its database, not, or no answer.

**Why this is its own module.** :func:`~platterpus.read_speed_ladder.
disc_in_accuraterip` answers "did any track match?". The owner's word of
2026-10-20 (*"yes, read twice by default"*) needs a different question answered:
whether anything outside the drive could vouch for the disc at all. A disc the
database does not hold, a lookup that failed, and a disc the database holds whose
every track misread all give "no track matched", and they need three different
answers from the securing pass (``securing_pass.plan_securing_pass``).

Pure; no Qt, no I/O; never raises.
"""

from __future__ import annotations

import logging
from typing import Final

from platterpus import diagnostics
from platterpus.read_speed_ladder import disc_in_accuraterip

log = logging.getLogger(__name__)


#: What AccurateRip can say about a disc, as :func:`accuraterip_standing` reads it.
#: In the database: an entry exists for this disc, whether or not any track matched.
AR_STANDING_IN_DATABASE: Final[str] = "in_database"
#: The lookup ran and the database holds no entry for this disc (``not found``, or
#: ``mismatch``: entries came back, none of them for this disc's IDs).
AR_STANDING_NOT_IN_DATABASE: Final[str] = "not_in_database"
#: No answer: the lookup failed (``error``) or was not made (``disabled``).
AR_STANDING_LOOKUP_FAILED: Final[str] = "lookup_failed"
#: The log does not say: no disc-level line and no per-track row we recognise.
AR_STANDING_NOT_DETERMINED: Final[str] = "not_determined"

# The disc-level `AccurateRip:` words, as cyanrip prints them
# (`cyanrip@3861b266:src/cyanrip_log.c:1037-1041`), and what each means here.
# `mismatch` is a response that held entries but none for this disc's IDs
# (`cyanrip@3861b266:src/accurip.c:177-184`): there is no consensus for this
# disc either, so it reads as not in the database.
_DISC_STATUS_STANDING: Final[dict[str, str]] = {
    "found": AR_STANDING_IN_DATABASE,
    "not found": AR_STANDING_NOT_IN_DATABASE,
    "mismatch": AR_STANDING_NOT_IN_DATABASE,
    "error": AR_STANDING_LOOKUP_FAILED,
    "disabled": AR_STANDING_LOOKUP_FAILED,
}


def accuraterip_standing(rip_log: object) -> str:
    """What AccurateRip can say about this disc: one of the ``AR_STANDING_*`` values.

    **Why this exists** (the owner's word of 2026-10-20, *"yes, read twice by
    default"*). :func:`disc_in_accuraterip` answers "did any track match?", and
    returns False both for a disc the database does not hold and for a lookup
    that failed, and also for a disc the database holds whose every track
    misread. Those are three different situations with three different
    answers, so this reads the lookup's own reply:

    * a track matched, or cyanrip says ``found``: **in the database**, even when
      every track failed, because a consensus exists to re-read toward;
    * ``not found`` or ``mismatch``: **not in the database**;
    * ``error`` or ``disabled``: **lookup failed**, nothing vouched for the disc;
    * otherwise the per-track ``Accurip:`` rows decide where they can, and
      anything else is **not determined**, never a guess.

    The per-track row alone cannot separate the first two failures: cyanrip
    prints ``not found`` for both (``cyanrip@3861b266:src/cyanrip_log.c:669-671``).
    Pure, never raises.
    """
    try:
        if disc_in_accuraterip(rip_log):
            return AR_STANDING_IN_DATABASE
        status = str(getattr(rip_log, "accuraterip_disc_status", "") or "")
        standing = _DISC_STATUS_STANDING.get(status.strip().casefold())
        if standing is not None:
            return standing
        if status.strip():
            # A word we do not know is not evidence either way.
            log.warning(
                "unrecognised AccurateRip disc status %r",
                diagnostics.bounded_chars(status, head=40, tail=40),
            )
        lookups = [
            str(getattr(track, "accuraterip_lookup", "") or "").casefold()
            for track in getattr(rip_log, "tracks", ()) or ()
        ]
        if any("disc found in database" in text for text in lookups):
            return AR_STANDING_IN_DATABASE
        if lookups and all(text.strip() == "disabled" for text in lookups):
            return AR_STANDING_LOOKUP_FAILED
        return AR_STANDING_NOT_DETERMINED
    except Exception:  # noqa: BLE001 — a predicate must never crash a rip
        log.exception("accuraterip_standing failed; not determined")
        return AR_STANDING_NOT_DETERMINED


def unvouched_sentence(standing: str) -> str:
    """Why AccurateRip could not vouch for the disc, as a clause for a log line.

    One wording per standing, so the app log, the console and any later surface
    cannot describe one disc two ways. Never raises.
    """
    if standing == AR_STANDING_NOT_IN_DATABASE:
        return "AccurateRip has no entry for this disc"
    if standing == AR_STANDING_LOOKUP_FAILED:
        return "the AccurateRip lookup failed, so nothing checked this disc"
    if standing and standing != AR_STANDING_IN_DATABASE:
        return "the log does not say what AccurateRip answered for this disc"
    return "AccurateRip can't vouch for this disc"
