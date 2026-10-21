# SPDX-License-Identifier: GPL-3.0-only
"""Run the verified-read chase for one track: single reads until AccurateRip agrees.

:mod:`platterpus.verified_read_chase` decides WHETHER a track is chased; this
runs the reads (TASKS R7). Plain functions with their collaborators handed in, so
the loop is tested without Qt or a drive and ``RipWorker`` keeps only the wiring.

**Every read goes through the worker's own pass runner** (``read_once`` is
``RipWorker._read_once_for_chase``, which calls ``_rip_once``). That is what
keeps the rules this project paid for: the argv is built and checked by the
backend's chokepoint (``-N``, ranges, ``assert_metadata_lookup_disabled``), the
child is a ``Popen`` in its own session, and ``RipWorker.cancel()`` kills it
(CLAUDE.md rule 9). It runs on the rip worker's thread, never the GUI's.

**What is kept, and when.** A read is kept only when all of these hold, and the
first such read ends the chase:

* it finished cleanly (exit 0) and was not cancelled: nothing is swapped in from
  a read that did not finish, the securing pass's rule;
* its log describes exactly the track we asked for, the securing pass's
  attribution guard;
* ``verdict.reread_supersedes`` keeps it over the album's current read for
  AccurateRip's reason, the one rule for "which read is better";
* the file copies into the album atomically (``swap_in``).

Otherwise the album keeps the file it had and the record says why. Never raises.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from platterpus.accuraterip_standing import (
    AR_STANDING_IN_DATABASE,
    accuraterip_standing,
)
from platterpus.report_types import (
    ChaseAttemptBlock,
    RetriedTrackBlock,
    VerifiedReadChaseBlock,
)
from platterpus.verdict import REREAD_KEPT_FOR_ACCURATERIP, reread_supersedes
from platterpus.verified_read_chase import (
    CHASE_KEPT_VERIFIED,
    CHASE_NONE_VERIFIED,
    CHASE_STOPPED,
    ChaseDecision,
    attempt_block,
    chase_log_path_for,
    chase_log_section,
    plan_chase,
    securing_pass_read_checksums,
    skipped_block,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SingleRead:
    """What one single read returned: as ``_rip_once`` says it, plus its exit and argv."""

    success: bool
    log_path: str
    exit_code: int | None
    argv: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChaseRun:
    """The chase of one track: its report block, the kept read, and its log sections."""

    block: VerifiedReadChaseBlock
    #: The kept read's parsed track record, or None when nothing was kept.
    kept_track: object | None = None
    #: One section per attempt for the kept chase log (`chase_log_section`).
    sections: list[str] = field(default_factory=list)


def _only_track(parsed: object | None, number: int) -> object | None:
    """The parsed record for ``number``, when the log describes that track alone.

    The securing pass's guard, for the same reason: a verdict attributed to the
    wrong track would copy a read over a file it does not describe.
    """
    tracks: list[object] = list(getattr(parsed, "tracks", ()) or ())
    numbers = {getattr(t, "number", None) for t in tracks}
    if numbers != {number}:
        if tracks:
            log.warning(
                "verified-read chase: a read of track %s returned a log describing "
                "track(s) %s; not keeping it",
                number,
                sorted(str(n) for n in numbers),
            )
        return None
    return tracks[0]


def _log_text(path: str) -> str:
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        log.warning("verified-read chase: could not read %s", path, exc_info=True)
        return ""


def run_chase(
    number: int,
    decision: ChaseDecision,
    *,
    kept: object | None,
    read_once: Callable[[int, Path], SingleRead | None],
    parse_log: Callable[[str], object | None],
    swap_in: Callable[[object, Path], bool],
    cancelled: Callable[[], bool],
) -> ChaseRun:
    """Read ``number`` alone, up to ``decision.attempt_limit`` times. Never raises.

    ``kept`` is the parsed record of the read the album holds now (unverified, or
    the chase would not run). ``read_once(number, folder)`` runs one read into
    ``folder`` and returns None when it could not start. Each attempt's folder is
    deleted afterwards, kept read or not: a kept read has been copied out.
    """
    attempts: list[ChaseAttemptBlock] = []
    sections: list[str] = []
    outcome = CHASE_NONE_VERIFIED
    kept_track: object | None = None
    kept_attempt: int | None = None
    try:
        for attempt in range(1, decision.attempt_limit + 1):
            if cancelled():
                outcome = CHASE_STOPPED
                break
            folder = Path(tempfile.mkdtemp(prefix="platterpus-verified-read-"))
            try:
                run = read_once(number, folder)
                if run is None:  # it could not start; the worker said why
                    outcome = CHASE_STOPPED
                    break
                sections.append(
                    chase_log_section(
                        number,
                        attempt,
                        run.argv,
                        run.exit_code,
                        _log_text(run.log_path),
                    )
                )
                track = _only_track(parse_log(run.log_path), number)
                keep = (
                    run.success
                    and not cancelled()
                    and track is not None
                    and reread_supersedes(kept, track) == REREAD_KEPT_FOR_ACCURATERIP
                    and swap_in(track, folder)
                )
                attempts.append(attempt_block(attempt, track, run.exit_code, kept=keep))
                if keep:
                    outcome, kept_track, kept_attempt = (
                        CHASE_KEPT_VERIFIED,
                        track,
                        attempt,
                    )
                    break
                if cancelled():
                    outcome = CHASE_STOPPED
                    break
            finally:
                shutil.rmtree(folder, ignore_errors=True)
    except Exception:  # noqa: BLE001 — a chase must never crash the rip
        log.exception("verified-read chase of track %s failed; album unchanged", number)
        outcome = CHASE_STOPPED if kept_track is None else outcome
    block: VerifiedReadChaseBlock = {
        "outcome": outcome,
        "attempt_limit": decision.attempt_limit,
        "distinct_reads_seen": decision.distinct_reads_seen,
        "attempts": attempts,
        "kept_attempt": kept_attempt,
    }
    return ChaseRun(block=block, kept_track=kept_track, sections=sections)


def chase_sentence(number: int, block: VerifiedReadChaseBlock) -> str:
    """The log pane's one line about a track's chase. Never raises."""
    tried = len(block.get("attempts") or [])
    limit = block.get("attempt_limit", 0)
    outcome = block.get("outcome", "")
    if outcome == CHASE_KEPT_VERIFIED:
        return (
            f"[verified read] track {number}: single read {block.get('kept_attempt')} "
            f"of up to {limit} matches AccurateRip; kept it in place of a read "
            "AccurateRip did not verify."
        )
    said = {
        CHASE_NONE_VERIFIED: f"none of {tried} single read(s) matched AccurateRip",
        CHASE_STOPPED: f"stopped after {tried} single read(s)",
    }.get(outcome, f"not re-read singly ({outcome})")
    return f"[verified read] track {number}: {said}; the album keeps the read it had."


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
) -> tuple[dict[int, object], list[str]]:
    """Chase each track the securing pass just recorded. Never raises.

    ``entries`` are the securing pass's ``retried_tracks`` records; each one the
    chase applied to gets a ``verified_read_chase`` block, and a kept read sets
    ``replaced`` and ``replaced_because``. ``shipped`` is the worker's records of
    reads already swapped in, so the read the album keeps now is known. Returns
    the kept reads' parsed records by track, and every attempt's log section.
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
            kept = shipped.get(number) if entry["replaced"] else None
            kept = kept if kept is not None else first_pass_tracks.get(number)
            decision = plan_chase(
                disc_in_accuraterip=in_db,
                kept=kept,
                first_pass=first_pass_tracks.get(number),
                securing=securing.get(number),
                loop_values=loop.get(number, ()),
                max_retries=max_retries,
            )
            if decision is None:
                continue
            if not decision.run:
                entry["verified_read_chase"] = skipped_block(decision)
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


def keep_chase_logs(album_log_path: str, sections: list[str]) -> Path | None:
    """Write every attempt's log beside the album's; the path, or None. Never raises."""
    if not sections or not album_log_path:
        return None
    target = chase_log_path_for(album_log_path)
    try:
        target.write_text("".join(sections), encoding="utf-8")
    except OSError:
        log.exception("could not keep the verified-read chase's logs")
        return None
    return target
