# SPDX-License-Identifier: GPL-3.0-only
"""The adaptive read-speed ladder — the pure decision logic behind the rip.

The goal (the maintainer's north star): behave like a careful EAC user with zero
terminal. **Start fast, and only slow down / re-read harder when a disc actually
needs it — quality can only go UP, never down.** A clean disc rips at full speed;
a marginal one is re-read at progressively slower speeds (which many drives read
more accurately) and, at the floor, with cyanrip's `-Z` re-rip-until-match.

This module is the *brain* only — pure, no Qt, no subprocess, **never raises**.
The rip worker calls :func:`next_step` after each pass to decide the next attempt,
and :func:`attempts_to_report` to record what each pass needed (honest reporting:
a disc that still can't read clean at the floor is FLAGGED, never papered over).

**Two signals, deliberately kept apart (real-hardware finding, 2026-07-01):**
  * *Unrecoverable read errors* — cyanrip's finish-report ripping-error count /
    a per-track "with errors" status. This is what TRIGGERS the step-down
    (:func:`read_errors_present`); it means the drive gave up on a read.
  * *Read instability* — cyanrip's secure re-read (``-Z N``) hit its repeat limit
    without any two reads agreeing (:func:`unstable_tracks`). A real disc proved
    the error COUNT stays 0 even then, so this is the reliable per-track quality
    tell — but per the maintainer's call it is **flagged, not auto-re-ripped**
    (a whole-disc re-rip to retry one track can cost hours with no guarantee).
  A converged read that merely matches an offset-variant pressing is NEITHER — a
  pressing difference, not a fault — and is never treated as either signal.

**Hardware-gated (see docs/ripper-engine-strategy.md §8 — flagged for the
Bazzite + Pioneer BDR-209D validation before this is treated as authoritative):**
  (a) ~~whether cyanrip exposes a reliable per-track read-quality signal~~ —
      ANSWERED 2026-07-01: the whole-disc ripping-error count is NOT sufficient
      (a disc with an unstable track reported 0 errors), so we now also read the
      per-track ``-Z`` convergence (:func:`unstable_tracks`) and flag it;
  (b) whether cyanrip can re-rip a *subset* of tracks at a new speed, or the whole
      disc must re-run (today we re-run the whole disc — safe, if slower — which
      is exactly why (a)'s instability is flagged rather than auto-re-ripped);
  (c) whether the BDR-209D honours ``-S`` through the Linux/libcdio-paranoia
      stack at all (if not, the ladder degrades to plain re-reads — no regression).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# The read-speed rungs, fastest → slowest. 0 means "let the drive pick" (its
# maximum) and is the first, fastest rung — cyanrip omits ``-S`` entirely there.
# The remaining rungs are the classic EAC-style step-down (8× → 4× → 2×); many
# drives read a marginal disc more accurately slower. 2× is the FLOOR (the last
# rung): below it there's little accuracy to gain and a lot of time to lose.
DEFAULT_LADDER: tuple[int, ...] = (0, 8, 4, 2)
FLOOR_SPEED: int = DEFAULT_LADDER[-1]

# At the floor speed, if a disc STILL won't read clean, escalate cyanrip's `-Z N`
# (re-rip a track until N reads' checksums agree) instead of going slower. Start
# at 2 (two agreeing reads) and climb to this ceiling, then give up (and FLAG).
_Z_FLOOR: int = 2
MAX_SECURE_REREP: int = 3

# A hard backstop on total passes, independent of the ladder maths, so a bug can
# never spin a disc forever: ladder rungs + the -Z escalations, plus slack.
MAX_ATTEMPTS: int = 6


@dataclass(frozen=True)
class LadderStep:
    """The next rip attempt the ladder recommends after a pass with read errors."""

    speed: int  # 0 = drive default/max; else the ``-S`` value
    secure_rerip_matches: int  # cyanrip's ``-Z`` for this attempt (0 = off)
    reason: str  # human-readable why, for the log/report


@dataclass(frozen=True)
class SpeedAttempt:
    """A record of one completed rip pass — what it used and how it went.

    ``clean`` is True when the pass completed, read without unrecoverable errors,
    AND every secure re-read converged (no unstable track). The escalation history
    is a list of these, so the report can show exactly which speed / ``-Z`` a disc
    needed — or that it never read clean. NOTE only unrecoverable errors trigger a
    step-down; instability marks a pass not-clean (honest reporting) but is
    flagged, not re-ripped (maintainer's policy).
    """

    attempt: int  # 1-based
    speed: int  # 0 = drive default/max
    secure_rerip_matches: int
    clean: bool


def next_step(
    *,
    current_speed: int,
    current_secure_rerip: int,
    ladder: tuple[int, ...] = DEFAULT_LADDER,
    max_secure_rerip: int = MAX_SECURE_REREP,
    speed_locked: bool = False,
) -> LadderStep | None:
    """Given the pass that just failed, return the next attempt — or None to stop.

    Escalation order: step DOWN the speed ladder first (slower reads are often
    more accurate), and only once at the floor speed, escalate ``-Z`` (re-read
    until N passes agree). Returns None when both are exhausted — the caller then
    stops and FLAGS the disc as still-failing. Never raises: an unknown current
    speed is treated as the top rung so escalation still makes progress.

    ``speed_locked`` (real-hardware finding, 2026-07-01): when the drive can't
    change read speed, cyanrip **aborts** the rip if handed ``-S`` — so the speed
    rungs are not just ineffective, they're dangerous. When set, we skip the speed
    ladder entirely and escalate ONLY ``-Z`` at the current (max) speed, so ``-S``
    is never sent. This keeps the sole working lever on such a drive.
    """
    try:
        if not ladder:
            return None
        floor = ladder[-1]
        # Still room to slow down? Step to the next-slower rung, keeping -Z —
        # UNLESS the drive can't change speed (then -S would abort the rip).
        if not speed_locked and current_speed != floor:
            try:
                idx = ladder.index(current_speed)
            except ValueError:
                # Unknown speed → treat as the top rung so we still step toward
                # the floor rather than stalling.
                idx = 0
            if idx < len(ladder) - 1:
                nxt = ladder[idx + 1]
                return LadderStep(
                    speed=nxt,
                    secure_rerip_matches=current_secure_rerip,
                    reason=(
                        f"read errors — retrying at {_speed_label(nxt)} "
                        "(slower reads are often more accurate)"
                    ),
                )
        # At the floor speed (or a speed-locked drive): escalate -Z instead of
        # going slower. Stay at the current speed — for a locked drive that's max
        # (0), since we must never emit an -S value cyanrip would reject.
        step_speed = current_speed if speed_locked else floor
        next_z = max(current_secure_rerip + 1, _Z_FLOOR)
        if next_z <= max_secure_rerip:
            reason = (
                "drive can't change speed — re-reading until "
                f"{next_z} passes agree (-Z {next_z})"
                if speed_locked
                else f"still failing at {_speed_label(floor)} — re-reading until "
                f"{next_z} passes agree (-Z {next_z})"
            )
            return LadderStep(
                speed=step_speed,
                secure_rerip_matches=next_z,
                reason=reason,
            )
        return None
    except Exception:  # noqa: BLE001 — a policy helper must never crash the rip
        log.exception("read-speed ladder next_step failed; stopping escalation")
        return None


def _speed_label(speed: int) -> str:
    """Human label for a rung: 0 → 'max speed', else 'N×'."""
    return "max speed" if speed <= 0 else f"{speed}×"


def read_errors_present(rip_log: object) -> bool:
    """True if a parsed rip log shows unrecoverable read errors — the signal
    that a slower re-read might help.

    Pure and never raises (it drives an escalation decision from a best-effort
    parse). cyanrip normalises its finish line to ``health_status`` of
    "No errors occurred" (0 errors) or "N ripping errors"; a per-track failure
    also lands as an "error" in that track's status. A disc simply *not in
    AccurateRip* is NOT an error (nothing to re-read for) — this returns False
    for it, so the ladder never spins on a clean-but-unknown disc.
    """
    try:
        health = getattr(rip_log, "health_status", "") or ""
        if health and "no error" not in health.lower():
            return True
        for track in getattr(rip_log, "tracks", ()) or ():
            if "error" in (getattr(track, "status", "") or "").lower():
                return True
        return False
    except Exception:  # noqa: BLE001 — an escalation predicate must not crash
        log.exception("read_errors_present failed; assuming no errors")
        return False


def unstable_tracks(rip_log: object) -> list[int]:
    """Track numbers whose cyanrip secure re-read (``-Z``) never converged.

    cyanrip re-reads a track until N reads' checksums agree; when it instead hits
    the repeat limit with no two reads agreeing, that track's data is UNSTABLE (a
    scratch/dirt region) and may not be bit-perfect. This is the reliable
    per-track read-quality signal — distinct from cyanrip's whole-disc
    ripping-error count (which stays 0 even then; see :func:`read_errors_present`)
    and from an offset-variant AccurateRip match (a stable read of a different
    pressing — NOT instability). Per the maintainer's "flag it, don't auto
    re-rip" policy (2026-07-01) these are surfaced honestly but do NOT trigger a
    re-rip. Pure, sorted, deduped, and — like every helper here — never raises.
    """
    try:
        numbers: list[int] = []
        for track in getattr(rip_log, "tracks", ()) or ():
            if getattr(track, "secure_rerip_converged", None) is False:
                number = getattr(track, "number", None)
                if isinstance(number, int):
                    numbers.append(number)
        return sorted(set(numbers))
    except Exception:  # noqa: BLE001 — a report helper must never crash a rip
        log.exception("unstable_tracks failed; assuming none")
        return []


def attempts_to_report(
    attempts: list[SpeedAttempt],
    unstable: list[int] | None = None,
    retried: list[dict] | None = None,
) -> dict | None:
    """Summarize the escalation history for the JSON report. None if no attempts.

    Records every pass (speed + ``-Z`` + whether it read clean), the final
    settings, whether the ladder had to escalate at all, and — the honest bits —
    whether the disc was left ``unresolved``, which tracks are still ``unstable``,
    and what the per-track auto-fix ``retried``.

    ``unstable`` is the track numbers whose secure re-read never converged AND
    that a per-track auto-fix couldn't rescue (from :func:`unstable_tracks` after
    the fix). ``retried`` is the auto-fix history (one dict per re-ripped track:
    ``{track, reripped_z, converged, replaced}``). ``unresolved`` is True whenever
    the last pass wasn't clean OR any track is still unstable — surfaced, never
    papered over. Never raises.
    """
    try:
        if not attempts:
            return None
        last = attempts[-1]
        unstable_list = sorted(set(unstable or []))
        return {
            "attempts": [
                {
                    "attempt": a.attempt,
                    "speed": a.speed,
                    "speed_label": _speed_label(a.speed),
                    "secure_rerip_matches": a.secure_rerip_matches,
                    "clean": a.clean,
                }
                for a in attempts
            ],
            "final_speed": last.speed,
            "final_speed_label": _speed_label(last.speed),
            "final_secure_rerip_matches": last.secure_rerip_matches,
            # Did we ever have to step down / re-read harder than the first pass?
            "escalated": len(attempts) > 1,
            # The honest flag: the disc never read clean at the floor, OR a track
            # is still unstable after the auto-fix (see below).
            "unresolved": (not last.clean) or bool(unstable_list),
            # Tracks whose secure re-read never converged and that the per-track
            # auto-fix could NOT rescue — still a "may not be bit-perfect" caveat.
            "unstable_tracks": unstable_list,
            # Per-track auto-fix history: each unstable track re-ripped alone with
            # a harder -Z, whether it then converged, and whether the improved FLAC
            # replaced the original. Empty when nothing was re-ripped.
            "retried_tracks": [dict(r) for r in (retried or [])],
        }
    except Exception:  # noqa: BLE001 — report helpers never crash a rip
        log.exception("read-speed ladder attempts_to_report failed")
        return None
