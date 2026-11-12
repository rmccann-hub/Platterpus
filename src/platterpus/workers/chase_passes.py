# SPDX-License-Identifier: GPL-3.0-only
"""The verified-read chase over a whole pass's tracks, and where its logs are kept.

:mod:`platterpus.workers.verified_read_run` reads ONE track until AccurateRip
agrees; this runs it over the tracks a pass left unverified, and keeps every
attempt's log beside the album's. Split out in round 39 (gate G1), when the
chase learned to follow Archival Exact's ``-Z`` album pass as well as the
securing pass (``CHASE_AFTER_ALBUM_PASS``, TASKS R7's open item) and one rip
could therefore chase twice, so the loop over a pass's tracks and the loop over
one track's reads each stay a focused module.

**Composes with the ripper's own reads.** The chase runs only for a track whose
kept read AccurateRip did not verify, so it is always the FALLBACK after the
ripper's reads: today after ``-Z`` (and ``--prefer-accuraterip-match`` on
``.27`` on), and after ``.31``'s ``--reread-until-accuraterip CONF``, which
every ``-Z`` pass sends to a build that lists it (their round 38 lap 16 S13;
their round 39 lap 3 S15 for the album pass), whose reads would already have
kept a verified read where the drive gave one. A track that option left
verified is not chased; one it could not verify is, under the same budget.

Plain functions with their collaborators handed in, run on the rip worker's
thread, never the GUI's. Never raises.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from platterpus.accuraterip_standing import (
    AR_STANDING_IN_DATABASE,
    accuraterip_standing,
)
from platterpus.chase_record import (
    CHASE_AFTER_ALBUM_PASS,
    CHASE_AFTER_SECURING_PASS,
    skipped_block,
)
from platterpus.read_speed_ladder import tracks_failing_accuraterip
from platterpus.report_types import RetriedTrackBlock
from platterpus.securing_pass import TRIGGER_ACCURATERIP
from platterpus.verdict import REREAD_KEPT_FOR_ACCURATERIP
from platterpus.verified_read_chase import (
    chase_log_path_for,
    plan_chase,
    securing_pass_read_checksums,
)
from platterpus.workers.verified_read_run import (
    SingleRead,
    chase_sentence,
    run_chase,
)

log = logging.getLogger(__name__)


def chase_tracks(
    entries: list[RetriedTrackBlock],
    *,
    rerip_log: object,
    rerip_log_text: str,
    first_pass_tracks: dict[int, object],
    shipped: dict[int, object],
    max_retries: int,
    read_once: Callable[[int, Path], SingleRead | None],
    parse_log: Callable[[str], object | None],
    swap_in: Callable[[object, Path], bool],
    cancelled: Callable[[], bool],
    say: Callable[[str], None],
    status: Callable[[str], None],
    clock: Callable[[], float] = time.monotonic,
    after: str = CHASE_AFTER_SECURING_PASS,
) -> tuple[dict[int, object], list[str]]:
    """Chase each track the securing pass (or the album pass) just recorded.

    ``entries`` are ``retried_tracks`` records; each one the chase applied to
    gets a ``verified_read_chase`` block, and a kept read sets ``replaced`` and
    ``replaced_because``. ``shipped`` is the worker's records of reads already
    swapped in, so the read the album keeps now is known. Returns the kept
    reads' parsed records by track, and every attempt's log section. Never
    raises.

    ``after`` says which pass ``rerip_log`` is. After a securing pass it is that
    pass, and ``first_pass_tracks`` the album pass. After Archival Exact's
    ``-Z`` album pass (:data:`CHASE_AFTER_ALBUM_PASS`, round 39) it is the album
    pass itself, and so is ``first_pass_tracks``: the album's read is the one
    kept, its ``-Z`` loop gives the values compared, and its block CRC is not
    compared with itself, which would read one read as two that agreed.
    """
    kept_reads: dict[int, object] = {}
    sections: list[str] = []
    try:
        # The securing pass's own lookup: the newest answer for this disc.
        in_db = accuraterip_standing(rerip_log) == AR_STANDING_IN_DATABASE
        loop = securing_pass_read_checksums(rerip_log_text)
        securing = {
            getattr(t, "number", None): t
            for t in getattr(rerip_log, "tracks", ()) or ()
        }
        for entry in entries:
            if cancelled():
                break
            number = entry["track"]
            album = first_pass_tracks.get(number)
            kept = shipped.get(number) if entry["replaced"] else None
            kept = kept if kept is not None else album
            decision = plan_chase(
                disc_in_accuraterip=in_db,
                kept=kept,
                first_pass=None if after == CHASE_AFTER_ALBUM_PASS else album,
                securing=securing.get(number),
                loop_values=loop.get(number, ()),
                max_retries=max_retries,
                album_pass=album,
            )
            if decision is None:
                continue
            if not decision.run:
                entry["verified_read_chase"] = skipped_block(decision, after)
                continue
            status(
                f"Reading track {number} again, singly, for a read AccurateRip "
                "verifies…"
            )
            run = run_chase(
                number,
                decision,
                kept=kept,
                read_once=read_once,
                parse_log=parse_log,
                swap_in=swap_in,
                cancelled=cancelled,
                after=after,
                clock=clock,
            )
            entry["verified_read_chase"] = run.block
            sections.extend(run.sections)
            say(chase_sentence(number, run.block))
            if run.kept_track is not None:
                entry["replaced"] = True
                entry["replaced_because"] = REREAD_KEPT_FOR_ACCURATERIP
                kept_reads[number] = run.kept_track
    except Exception:  # noqa: BLE001 — the chase must never crash the rip
        log.exception("verified-read chase failed; album unchanged from here")
    return kept_reads, sections


def album_pass_entries(album_log: object, handled: set[int]) -> list[RetriedTrackBlock]:
    """Records for the chase after Archival Exact's ``-Z`` album pass (round 39).

    One per track AccurateRip did not verify (``tracks_failing_accuraterip``,
    the predicate the dynamic securing pass picks its tracks by, data tracks
    and one-frame matches handled alike) that no securing pass has recorded:
    ``handled`` holds those, which the chase after that pass already
    considered. ``reripped_z`` is 0 and ``converged`` False because no ``-Z``
    re-read ran for these tracks; the chase's own block says what did. Never
    raises.
    """
    try:
        failing = tracks_failing_accuraterip(album_log, include_offset_variant=True)
    except Exception:  # noqa: BLE001 — no list means no chase, never a crash
        log.exception("could not list the album pass's unverified tracks")
        return []
    return [
        {
            "track": number,
            "trigger": TRIGGER_ACCURATERIP,
            "reripped_z": 0,
            "converged": False,
            "replaced": False,
            "replaced_because": None,
        }
        for number in failing
        if number not in handled
    ]


def keep_chase_logs(
    album_log_path: str, sections: list[str], *, append: bool = False
) -> Path | None:
    """Write every attempt's log beside the album's; the path, or None. Never raises.

    ``append`` adds to what this rip already wrote there: Archival Exact can
    chase twice in one rip (after its securing pass, then after its album pass),
    and the second must not erase the first's logs.
    """
    if not sections or not album_log_path:
        return None
    target = chase_log_path_for(album_log_path)
    try:
        with target.open("a" if append else "w", encoding="utf-8") as handle:
            handle.write("".join(sections))
    except OSError:
        log.exception("could not keep the verified-read chase's logs")
        return None
    return target
