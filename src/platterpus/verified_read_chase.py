# SPDX-License-Identifier: GPL-3.0-only
"""The verified-read chase: whether a track gets extra single reads, and the record.

**What it is for** (TASKS R7). On the 2026-10-12 hardware run the securing pass
read track 5 of the reference disc as ``C96464AB`` once, the one value AccurateRip
verifies (v2 confidence 200), and then twice as ``4065BECC``. At the repeat limit
cyanrip keeps the majority read, so the verified read was thrown away. Over 26
committed rips of that disc, tracks 3 and 5 often settle on values AccurateRip
rejects (``docs/eac-parity.md`` Part E §E2). Majority of reads is our drive
agreeing with itself; an AccurateRip match is other people's discs agreeing with
ours. When the two disagree, AccurateRip is the stronger evidence
(``verdict.reread_supersedes`` already says so for the securing pass's read).

**What the chase does.** After the securing pass, a track whose kept read
AccurateRip did not verify is read again ALONE, one read at a time with no
``-Z``, up to a bounded number of attempts, and the first read AccurateRip
verifies is kept. If none does, nothing changes and the record says so. We do
not control cyanrip's ``-Z`` and do not change the fork; every read is an
ordinary ``-l N`` rip through the same backend and argv chokepoint as any other.

**Why each read is judged by its own AccurateRip result, not by its CRC.** The
first idea was "re-read until the CRC equals the verified one". Within one
securing pass we cannot know which read was the verified one: cyanrip computes
the AccurateRip checksums only for the read it keeps, and the per-read values it
prints are the complement of the EAC CRC32 on builds before ``9669d84``. A single
read, on the other hand, is the read cyanrip keeps, so its own log carries its own
AccurateRip v1/v2 result. Each kept file then carries its own proof, in its own
log, and nothing depends on a CRC remembered from another read.

**When it runs** (:func:`plan_chase`), all three must hold:

* **the disc is in AccurateRip**, by the securing pass's own lookup. Otherwise no
  read can be verified, so extra reads only cost time;
* **the read the album keeps is not verified** (:func:`~platterpus.parsers.
  rip_log.track_accuraterip_verified`, confidence >= 1). See *the threshold*;
* **the drive returned more than one value for the track**: two different values
  among the securing pass's printed reads, or a securing-pass CRC unlike the album
  pass's. A drive that returned one value every time is reading a pressing
  AccurateRip does not hold, or a fault it reproduces; another read of that is not
  likely to differ, and on a disc whose every track fails that way a chase would
  cost several whole-disc reads for nothing. The 2026-10-12 track 5 (``C96464AB``
  once, ``4065BECC`` twice) and round 32's (``C96464AB`` once, ``E0036697`` three
  times, ``round32fullwholediscsecuringpass.txt``) both pass this test.

**The threshold: confidence >= 1, the program's one definition of verified.**
The brief offered ``>= 2``. We keep ``>= 1`` because three surfaces must agree:
``reread_supersedes`` already keeps a securing-pass read over a converged one at
``>= 1``, the verdict and the report call a track verified at ``>= 1``, and the
chase keeps a read only when ``reread_supersedes`` says so. A stricter bar here
alone would refuse reads the report then calls verified (two keys for one
question). Confidence counts how many other submitters share the checksum; it is
not a measure of how exact the match is, and a chance 32-bit match is about one in
four billion. The confidence of every attempt is recorded, so a reader can apply
a stricter bar to the record.

**The bound: the user's ``-r``, at most** :data:`CHASE_ATTEMPTS_CEILING`. cyanrip
describes ``-r`` as the limit "per frame, and per whole-track re-read", so it is
already the user's answer to how many whole-track reads of one track they accept.

Pure: no Qt, no I/O, never raises. The attempts themselves are run by
:mod:`platterpus.workers.verified_read_run`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.parsers.cyanrip_log import (
    finished_track,
    secure_rerip_read_checksum,
)
from platterpus.parsers.rip_log import track_accuraterip_verified
from platterpus.report_types import (
    ChaseAttemptBlock,
    RetriedTrackBlock,
    VerifiedReadChaseBlock,
)

log = logging.getLogger(__name__)

#: The most single reads one track gets, whatever ``-r`` says.
CHASE_ATTEMPTS_CEILING: Final[int] = 5

#: ``verified_read_chase.outcome``: a read AccurateRip verifies was kept.
CHASE_KEPT_VERIFIED: Final[str] = "kept_verified_read"
#: Every attempt ran and none was verified; the album keeps what it had.
CHASE_NONE_VERIFIED: Final[str] = "no_read_verified"
#: Cancelled, or a read failed to start; the album keeps what it had.
CHASE_STOPPED: Final[str] = "stopped"
#: Not attempted: the drive returned one value every time.
CHASE_SKIPPED_READS_AGREED: Final[str] = "skipped_reads_agreed"
#: Not attempted: no two values could be compared (tri-state: not "agreed").
CHASE_SKIPPED_NOT_DETERMINED: Final[str] = "skipped_reads_not_determined"

#: ``retried_tracks[].kept_read``: which read the album keeps.
KEPT_FIRST_READ: Final[str] = "first_read"
KEPT_SECURING_PASS: Final[str] = "securing_pass"
KEPT_VERIFIED_REREAD: Final[str] = "verified_reread"

#: Each chase read's own ripper log, kept beside the album's. ``.txt``, never
#: ``.log``, for the reason the securing pass's log is (`rip_addendum.
#: SECURING_PASS_LOG_SUFFIX`): the album's log is found by its suffix.
CHASE_LOG_SUFFIX: Final[str] = ".platterpus-verified-read.txt"

#: The most read values kept per track; a ``-Z`` loop is bounded by ``-r``, so
#: this is never reached on a real log, and only stops a malformed one growing.
_MAX_READS_PER_TRACK: Final[int] = 64


@dataclass(frozen=True)
class ChaseDecision:
    """Whether to chase one track. ``run`` False with an ``outcome`` is a skip."""

    run: bool
    attempt_limit: int
    distinct_reads_seen: int | None
    outcome: str = ""


def securing_pass_read_checksums(log_text: str) -> dict[int, tuple[str, ...]]:
    """Each track's ``-Z`` read values, in order, from the securing pass's log.

    The loop's lines come before the ``Track N read …`` line that ends the
    track's reads (``cyanrip_log.finished_track``, the parser's own pattern), so
    the values seen since the last such line belong to the track it names.
    Compare these only with each other (see
    :func:`~platterpus.parsers.cyanrip_log.secure_rerip_read_checksum`). Never
    raises: a log it cannot read gives ``{}``.
    """
    found: dict[int, tuple[str, ...]] = {}
    try:
        pending: list[str] = []
        for line in (log_text or "").splitlines():
            value = secure_rerip_read_checksum(line)
            if value is not None:
                if len(pending) < _MAX_READS_PER_TRACK:
                    pending.append(value)
                continue
            done = finished_track(line)
            if done is not None:
                if pending:
                    found[done[0]] = tuple(pending)
                pending = []
    except Exception:  # noqa: BLE001 — a missing hint costs a chase, never the rip
        log.exception("could not read the securing pass's per-read values")
    return found


def _crc(track: object | None) -> str:
    """A parsed track's EAC CRC32 (its block's), uppercase, or ``""``."""
    if track is None:
        return ""
    return str(getattr(track, "copy_crc", "") or "").strip().upper()


def plan_chase(
    *,
    disc_in_accuraterip: bool,
    kept: object | None,
    first_pass: object | None,
    securing: object | None,
    loop_values: tuple[str, ...],
    max_retries: int,
) -> ChaseDecision | None:
    """Whether to chase one track; ``None`` when the chase does not apply.

    ``kept`` is the parsed record of the read the album now keeps (the securing
    pass's when it was swapped in, else the album pass's); ``first_pass`` and
    ``securing`` are the album pass's and the securing pass's records for the
    track; ``loop_values`` is :func:`securing_pass_read_checksums`'s entry.
    ``None`` means not applicable (no read can be verified, or the kept one
    already is); a decision with ``run`` False is a skip worth recording. Never
    raises.
    """
    try:
        if not disc_in_accuraterip or kept is None:
            return None
        if track_accuraterip_verified(kept):
            return None
        limit = max(1, min(int(max_retries), CHASE_ATTEMPTS_CEILING))
        # Two kinds of evidence, never mixed: loop values only with each other,
        # block CRCs only with each other (both are EAC CRC32 on every build).
        first, second = _crc(first_pass), _crc(securing)
        distinct = len(set(loop_values)) if loop_values else None
        if first and second:
            if first != second:
                # Two values at least; the two sets cannot be merged into one count.
                distinct = max(distinct or 0, 2)
            elif distinct is None:
                distinct = 1  # two reads, one value
        if distinct is None:
            return ChaseDecision(False, limit, None, CHASE_SKIPPED_NOT_DETERMINED)
        if distinct < 2:
            return ChaseDecision(False, limit, distinct, CHASE_SKIPPED_READS_AGREED)
        return ChaseDecision(True, limit, distinct)
    except Exception:  # noqa: BLE001 — a plan that cannot be made changes nothing
        log.exception("plan_chase failed; not chasing this track")
        return None


def attempt_block(
    attempt: int, track: object | None, exit_code: int | None, *, kept: bool
) -> ChaseAttemptBlock:
    """One attempt's record, from the read's own parsed track. Never raises."""

    def confidence(name: str) -> int | None:
        value = getattr(getattr(track, name, None), "confidence", None)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    return {
        "attempt": attempt,
        "eac_crc": _crc(track) or None,
        "accuraterip_verified": bool(track is not None)
        and track_accuraterip_verified(track),
        "accuraterip_v1_confidence": confidence("accuraterip_v1"),
        "accuraterip_v2_confidence": confidence("accuraterip_v2"),
        "exit_code": exit_code,
        "kept": kept,
    }


def skipped_block(decision: ChaseDecision) -> VerifiedReadChaseBlock:
    """The record of a chase that was considered and not attempted."""
    return {
        "outcome": decision.outcome,
        "attempt_limit": decision.attempt_limit,
        "distinct_reads_seen": decision.distinct_reads_seen,
        "attempts": [],
        "kept_attempt": None,
    }


def kept_read(entry: RetriedTrackBlock) -> str:
    """Which read the album keeps for one retried track (``KEPT_*``). Never raises.

    Derived, not stored, so the worker's record and the report cannot disagree:
    a chase that kept an attempt wins, then a swapped-in securing-pass read, and
    otherwise the album pass's read stayed.
    """
    chase = entry.get("verified_read_chase")
    if isinstance(chase, dict) and chase.get("kept_attempt") is not None:
        return KEPT_VERIFIED_REREAD
    if entry.get("replaced"):
        return KEPT_SECURING_PASS
    return KEPT_FIRST_READ


def copy_chase_block(
    block: VerifiedReadChaseBlock | None,
) -> VerifiedReadChaseBlock | None:
    """A copy of a chase block for the report, so it never aliases the worker's."""
    if not isinstance(block, dict):
        return None
    return {
        "outcome": block["outcome"],
        "attempt_limit": block["attempt_limit"],
        "distinct_reads_seen": block["distinct_reads_seen"],
        "attempts": [ChaseAttemptBlock(**attempt) for attempt in block["attempts"]],
        "kept_attempt": block["kept_attempt"],
    }


def chase_log_path_for(log_path: str | Path) -> Path:
    """``…/Album.log`` → ``…/Album.platterpus-verified-read.txt``."""
    path = Path(log_path)
    return path.with_name(path.stem + CHASE_LOG_SUFFIX)


def chase_log_section(
    number: int, attempt: int, argv: tuple[str, ...], exit_code: int | None, text: str
) -> str:
    """One attempt's section of the kept chase log: what ran, how it ended, its log.

    The argv as spawned and the exit status head the ripper's own log, so the
    sidecar alone carries all three things the diagnostics rule asks for. The log
    is copied whole: it is a single track's, bounded by the ripper.
    """
    status = "never reaped" if exit_code is None else str(exit_code)
    head = [
        f"=== Platterpus verified-read chase: track {number}, attempt {attempt} ===",
        "argv: " + " ".join(argv) if argv else "argv: (not recorded)",
        f"exit status: {status}",
        "",
    ]
    return "\n".join(head) + (text or "(the read wrote no log)\n").rstrip("\n") + "\n\n"
