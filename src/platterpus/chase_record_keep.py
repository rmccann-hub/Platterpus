# SPDX-License-Identifier: GPL-3.0-only
"""Keep each verified-read chase read's ``--diagnostics`` record (round 39 lap 1 S10).

**Why this exists.** The fork's round 39 lap 1 S10 is BLOCKING: *"Put each rip's
``--diagnostics`` record in the bundle, in the five-rip run and from now on."* Their
gate G4 compares the per-second CRCs (``block_crcs``) of a track's wrong reads
with its right ones, and on the reference disc the reads that differ are track 3's
and track 5's: exactly the tracks the verified-read chase reads again and again
(TASKS R7; up to 16 single reads of a track AccurateRip knows well, round 39 G1).

Every other pass's record already reached the bundle: an album pass's stays where
cyanrip wrote it, in the rips root, and the securing pass's is copied there before
its temporary folder goes (``record_fate.keep_securing_record``, TASKS R9). **A
chase read's was the one left out**: each read runs in its own temporary folder
(``workers/verified_read_run.chase_track``), deleted after the read, so its
record went with it, unsaid, and with it the one comparison G4 asks for.

So each chase read's record is copied into the rips root as
``cyanrip-diagnostics-<stamp>-chase-t03.json``, beside the album passes'. The name
keeps the ``cyanrip-diagnostics-`` prefix and the ``.json`` suffix, so the session
bundle's scan (``test_session.DIAGNOSTICS_RECORD_GLOB``) and the drive test's
upload (``drivetest.sh``'s ``copy_records``) find it with no change, and the
track number says which read it was without opening it.

JSON text written by cyanrip, never audio; a copy never overwrites (a taken name
gets a number), and a missing record is logged, never raised. Qt-free and
thread-safe: it runs on the rip worker's thread.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

#: What marks a chase read's record in the rips root, before the track number.
CHASE_RECORD_MARK: Final[str] = "-chase-t"


def chase_record_destination(
    source: Path, rips_root: Path, track: int, attempt: int = 1
) -> Path:
    """Where chase read ``source`` of ``track`` is kept in ``rips_root``. Pure.

    ``cyanrip-diagnostics-<stamp>.json`` becomes
    ``<rips_root>/cyanrip-diagnostics-<stamp>-chase-t03.json``; ``attempt`` numbers
    a second name when the first is taken (``-chase-t03-2``).
    """
    count = "" if attempt <= 1 else f"-{attempt}"
    return (
        rips_root / f"{source.stem}{CHASE_RECORD_MARK}{track:02d}{count}{source.suffix}"
    )


def keep_chase_record(source: Path | None, rips_root: Path, track: int) -> Path | None:
    """Copy one chase read's record into ``rips_root``; the copy, or None. Never raises.

    ``source`` is where the read's argv told cyanrip to write it, inside the read's
    temporary folder (``None``: the argv named none, so no record was due, which is
    not logged as a loss). A record that is not there, or a copy that fails, is
    logged with the reason and gives None.
    """
    if source is None:
        return None
    try:
        if not source.is_file():
            log.warning(
                "the verified-read chase's read of track %s left no -j record at %s "
                "(cyanrip writes it as it exits; a read stopped before then has none)",
                track,
                source,
            )
            return None
        attempt = 1
        target = chase_record_destination(source, rips_root, track)
        while target.exists():
            attempt += 1
            target = chase_record_destination(source, rips_root, track, attempt)
        shutil.copyfile(source, target)
        return target
    except OSError as exc:
        log.warning(
            "could not keep the verified-read chase's -j record of track %s (%s): %r",
            track,
            source,
            exc,
        )
        return None
