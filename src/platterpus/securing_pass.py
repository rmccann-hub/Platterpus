# SPDX-License-Identifier: GPL-3.0-only
"""The securing pass: whether it runs after the album pass, over which tracks, and why not.

**What the securing pass is.** After the album pass (the whole-disc read, or the
user's ``-l`` selection, with any read-speed-ladder retries of it) the rip worker
can re-read the tracks that need it, alone, with ``-Z``, into a temporary folder.
A re-read is kept only when it is the better read (``verdict.reread_supersedes``),
so the pass can never make a track worse. Two triggers, decided by mode, never both:

* **dynamic secure re-rip:** the album pass read fast with no ``-Z``, so the tracks
  AccurateRip did not confirm are re-read at the user's own ``-Z`` when the disc
  is in AccurateRip. When it is not, or the lookup failed, **every** track is
  re-read (``TRIGGER_SECOND_READ``, the owner's word of 2026-10-20: *"yes, read
  twice by default"*), because single reads go wrong without saying so and
  nothing outside the drive checked this one. Until that date such a disc kept
  its one read; Settings can still turn the second read off;
* **otherwise the auto ladder:** a ``-Z`` pass left a track whose reads never
  agreed, so that track is re-read harder, at the ``-Z`` ceiling.

Plain fixed mode with no dynamic secure re-rip has no securing pass.

**When it runs** (:func:`why_no_securing_pass`, the maintainer's ruling C1,
``PLANNING.md`` KDD-41). Until 2026-10-05 the pass was keyed on exit 0. cyanrip
exits 1 whenever its drive failed a read
(``cyanrip@910dd99:src/cyanrip_main.c:3124``), so after a ladder that ended on
such a pass, or in fixed mode, the tracks that most needed a second read never got
one. Now:

* **exit 0, not stopped by us:** it runs, as it always did. cyanrip's own clean
  exit is the evidence this path has always rested on, and nothing found since says
  it was wrong, so it is not re-litigated here (the coordinator's ruling on the
  brief, 2026-10-06);
* **exit 1:** it runs only when the pass can be SHOWN to have finished
  (:func:`~platterpus.ladder_trigger.why_pass_unfinished`, the gate the read-speed
  ladder's own judgement starts from): not stopped by us, the pass's own log, and
  every requested track in it. Exit 1 also covers an interrupted or aborted run, so
  on this path the log has to prove the difference;
* **anything else** (a cancel, a signal or crash exit, an exit status never
  collected) refuses.

A refusal is recorded (``SKIPPED_ALBUM_PASS_UNFINISHED``) with the sentence that
says which condition refused, so a report can answer "why was my track not
re-read?" instead of leaving it to look like an oversight.

Pure, no Qt, no I/O; never raises. The worker runs the plan this returns, and
keeps the album pass's exit status apart from the securing pass's (see
:attr:`~platterpus.workers.rip_worker.RipWorker.securing_pass_exit_code`).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from platterpus.accuraterip_standing import (
    AR_STANDING_IN_DATABASE,
    AR_STANDING_LOOKUP_FAILED,
    AR_STANDING_NOT_IN_DATABASE,
    accuraterip_standing,
)
from platterpus.ladder_trigger import why_pass_unfinished
from platterpus.read_speed_ladder import (
    recovery_secure_rerip_ceiling,
    tracks_failing_accuraterip,
)

log = logging.getLogger(__name__)

#: ``read_speed.secure_rerip.skipped_reason`` when the disc is not in AccurateRip
#: and the second read is turned off in Settings.
SKIPPED_DISC_NOT_IN_ACCURATERIP: Final[str] = "disc_not_in_accuraterip"

#: ``read_speed.secure_rerip.skipped_reason`` when the AccurateRip lookup failed
#: (or its answer cannot be read off the log) and the second read is turned off.
#: Its own reason since 2026-10-20: a failed lookup is not a disc the database
#: lacks, and a report that called it one would send the reader looking for a
#: pressing problem when the network was the problem.
SKIPPED_ACCURATERIP_LOOKUP_FAILED: Final[str] = "accuraterip_lookup_failed"

#: ``read_speed.secure_rerip.skipped_reason`` when the log does not say what
#: AccurateRip answered and the second read is turned off. Not folded into either
#: reason above: "not determined" is never reported as a negative.
SKIPPED_ACCURATERIP_NOT_DETERMINED: Final[str] = "accuraterip_not_determined"

#: The skip reason for each standing, when the second read is off.
_SKIP_FOR_STANDING: Final[dict[str, str]] = {
    AR_STANDING_NOT_IN_DATABASE: SKIPPED_DISC_NOT_IN_ACCURATERIP,
    AR_STANDING_LOOKUP_FAILED: SKIPPED_ACCURATERIP_LOOKUP_FAILED,
}

#: ``read_speed.secure_rerip.skipped_reason`` when the gate refused the album pass
#: (a cancel, a signal or crash exit, or an exit-1 pass that cannot be shown to
#: have finished). New on 2026-10-05 with ruling C1: before it, a pass that did
#: not exit 0 skipped the securing pass with no reason recorded at all.
SKIPPED_ALBUM_PASS_UNFINISHED: Final[str] = "album_pass_unfinished"

#: Why each track was re-read, as ``read_speed.retried_tracks[].trigger`` says it.
TRIGGER_ACCURATERIP: Final[str] = "accuraterip"
TRIGGER_INSTABILITY: Final[str] = "instability"
#: Every track re-read because AccurateRip could not vouch for the disc (the
#: owner's word of 2026-10-20, *"yes, read twice by default"*).
TRIGGER_SECOND_READ: Final[str] = "second_read"


@dataclass(frozen=True)
class SecuringPlan:
    """What the securing pass will do, or why it will not run.

    ``applies`` is whether this rip's settings have a securing pass at all; when it
    is False every other field is its default and there is nothing to say.
    ``refused`` is the sentence naming the condition that refused, ``""`` when the
    gate let the album pass be secured. ``disc_in_accuraterip`` is answered only in dynamic mode
    after a finished pass, and is ``None`` otherwise (not asked is not "no").
    """

    applies: bool = False
    tracks: tuple[int, ...] = ()
    trigger: str = ""
    rerip_z: int = 0
    refused: str = ""
    disc_in_accuraterip: bool | None = None
    skipped_reason: str | None = None
    #: :func:`~platterpus.accuraterip_standing.accuraterip_standing`'s answer, when it
    #: was asked (dynamic mode after a finished pass). "" = not asked.
    accuraterip_standing: str = ""


def why_no_securing_pass(
    rip_log: object,
    *,
    exit_code: int | None,
    stopped_by_us: bool,
    log_is_this_passes: bool,
    only_tracks: Sequence[int] = (),
    disc_track_total: int | None = None,
) -> str:
    """``""`` when the album pass may be secured; otherwise which condition refused.

    THE securing pass's gate (see the module docstring). A clean exit 0 that
    Platterpus did not stop passes on cyanrip's word, as before ruling C1. Every
    other case, exit 1 included, is :func:`~platterpus.ladder_trigger.
    why_pass_unfinished`'s to answer, so the two gates cannot word the same
    refusal two ways. Never raises (the delegate does not, and the rest is a
    comparison).
    """
    if exit_code == 0 and not stopped_by_us:
        return ""
    return why_pass_unfinished(
        rip_log,
        exit_code=exit_code,
        stopped_by_us=stopped_by_us,
        log_is_this_passes=log_is_this_passes,
        only_tracks=only_tracks,
        disc_track_total=disc_track_total,
    )


def plan_securing_pass(
    rip_log: object,
    *,
    refusal: str,
    dynamic: bool,
    auto_ladder: bool,
    secure_rerip_matches: int,
    max_retries: int,
    include_offset_variant: bool,
    unstable: Sequence[int],
    second_read_without_accuraterip: bool = True,
) -> SecuringPlan:
    """THE securing-pass decision, given the album pass's gate.

    ``refusal`` is :func:`why_no_securing_pass`'s answer for the album pass
    (``""`` when it may be secured). ``dynamic`` is whether
    dynamic secure re-rip is on with a real ``-Z``; ``unstable`` is the album
    pass's tracks whose ``-Z`` reads never agreed. Never raises: a plan that cannot
    be made refuses, which leaves the album exactly as the album pass wrote it.

    **A disc AccurateRip cannot vouch for is read twice** (the owner's word of
    2026-10-20). In dynamic mode the album pass carries no ``-Z``, so such a disc
    used to be left on that one read. Now, unless
    ``second_read_without_accuraterip`` is off, every track the album pass read
    is re-read with ``-Z``, whether the database has no entry for the disc or the
    lookup failed: in neither case did anything outside the drive check the
    read. A disc the database holds whose every track failed is not this case:
    a consensus exists, and the failing tracks are re-read toward it.
    """
    if not (dynamic or auto_ladder):
        return SecuringPlan()
    try:
        if refusal:
            return SecuringPlan(
                applies=True,
                refused=refusal,
                skipped_reason=SKIPPED_ALBUM_PASS_UNFINISHED,
            )
        if dynamic:
            # The user's number is the ceiling: a dynamic pass never invents a
            # harder -Z than the one they set.
            standing = accuraterip_standing(rip_log)
            if standing != AR_STANDING_IN_DATABASE:
                if not second_read_without_accuraterip:
                    return SecuringPlan(
                        applies=True,
                        trigger=TRIGGER_ACCURATERIP,
                        rerip_z=secure_rerip_matches,
                        disc_in_accuraterip=False,
                        skipped_reason=_SKIP_FOR_STANDING.get(
                            standing, SKIPPED_ACCURATERIP_NOT_DETERMINED
                        ),
                        accuraterip_standing=standing,
                    )
                return SecuringPlan(
                    applies=True,
                    tracks=tuple(tracks_read(rip_log)),
                    trigger=TRIGGER_SECOND_READ,
                    rerip_z=secure_rerip_matches,
                    disc_in_accuraterip=False,
                    accuraterip_standing=standing,
                )
            # With `rerip_offset_variant` on (the default), an offset-variant
            # ("partially accurate") match is not treated as proven and is re-read
            # too (real-hardware findings, 2026-07-23 and 2026-09-24).
            failing = tracks_failing_accuraterip(
                rip_log, include_offset_variant=include_offset_variant
            )
            return SecuringPlan(
                applies=True,
                tracks=tuple(failing),
                trigger=TRIGGER_ACCURATERIP,
                rerip_z=secure_rerip_matches,
                disc_in_accuraterip=True,
                accuraterip_standing=standing,
            )
        # Recovery: an unstable track needs a -Z to converge, so the user's
        # ceiling when they set one, else the internal bound, capped at what their
        # -r lets converge: the same answer the ladder gets.
        return SecuringPlan(
            applies=True,
            tracks=tuple(unstable),
            trigger=TRIGGER_INSTABILITY,
            rerip_z=recovery_secure_rerip_ceiling(
                secure_rerip_matches=secure_rerip_matches, max_retries=max_retries
            ),
        )
    except Exception:  # noqa: BLE001 — a plan must not crash the rip
        log.exception("plan_securing_pass failed; not running the securing pass")
        return SecuringPlan(
            applies=True,
            refused="the securing-pass plan failed (see the app log)",
            skipped_reason=SKIPPED_ALBUM_PASS_UNFINISHED,
        )


def tracks_read(rip_log: object) -> list[int]:
    """The track numbers the album pass read and wrote, sorted. Never raises.

    "Wrote" is a CRC on the track's record: a track listed but never ripped has
    no read to compare a second one against. A data track has a block in the log
    from the fork's ``.23`` but never a Copy CRC (its ``CRC32:`` is filed as
    ``data_crc32``), so it is never in this list.
    """
    crcs, _records = first_pass_records(rip_log)
    return sorted(crcs)


def first_pass_records(
    rip_log: object,
) -> tuple[dict[int, str], dict[int, object]]:
    """The album pass's CRC and whole parsed record per track. Never raises.

    The CRC is captured before any swap, so the addendum can say whether a re-read
    confirmed the original audio or replaced it (round 7: track 5 came back with
    the CRC the album log already held). The record lets the re-read decision ask
    whether the read it might replace was already verified.
    """
    crcs: dict[int, str] = {}
    records: dict[int, object] = {}
    try:
        for track in getattr(rip_log, "tracks", ()) or ():
            number = getattr(track, "number", None)
            if not isinstance(number, int):
                continue
            records[number] = track
            crc = str(
                getattr(track, "copy_crc", "") or getattr(track, "test_crc", "") or ""
            )
            if crc:
                crcs[number] = crc
    except Exception:  # noqa: BLE001 — a missing CRC costs a sentence, not the rip
        log.exception("could not read the album pass's per-track records")
    return crcs, records
