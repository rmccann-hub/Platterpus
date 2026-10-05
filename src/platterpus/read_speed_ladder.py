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
    (:func:`read_errors_present`); it means the drive gave up on a read. From
    the fork's ``+platterpus.20`` the per-track arm also says "with errors" for
    paranoia skips and for a ``-Z`` track at the repeat limit, which are
    instability, so those two are left out of the trigger
    (:func:`_instability_explains_arm`).
  * *Read instability* — cyanrip's secure re-read (``-Z N``) hit its repeat limit
    before enough reads agreed (:func:`unstable_tracks`). A real disc proved
    the error COUNT stays 0 even then, so this is the reliable per-track quality
    tell — but per the maintainer's call it is **flagged, not auto-re-ripped**
    (a whole-disc re-rip to retry one track can cost hours with no guarantee).
  A converged read that merely matches an offset-variant pressing is NEITHER — a
  pressing difference, not a fault — and is never treated as either signal.

**Hardware-gated (see docs/cyanrip-fork.md Part A §8 — flagged for the
Bazzite + Pioneer BDR-209D validation before this is treated as authoritative):**
  (a) ~~whether cyanrip exposes a reliable per-track read-quality signal~~ —
      ANSWERED 2026-07-01: the whole-disc ripping-error count is NOT sufficient
      (a disc with an unstable track reported 0 errors), so we now also read the
      per-track ``-Z`` convergence (:func:`unstable_tracks`) and flag it;
  (b) whether cyanrip can re-rip a *subset* of tracks at a new speed, or the whole
      disc must re-run (today we re-run the whole disc — safe, if slower — which
      is exactly why (a)'s instability is flagged rather than auto-re-ripped);
  (c) RESOLVED on hardware (2026-07-01): the BDR-209D reports speed as
      "unchangeable" and cyanrip ABORTS on ``-S`` there — so once the banner
      reports speed_changeable=False the ladder degrades to plain re-reads and
      never sends a speed again.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from platterpus.cyanrip_cli import (
    highest_convergeable_repeat_rips,
    retries_flag_value,
)
from platterpus.parsers.rip_log import (
    accuraterip_is_match,
    track_accuraterip_verified,
)

# `report_types` is pure typing — no runtime imports of its own — so depending on
# it here costs nothing and buys the thing a bare `dict` cannot: the report block
# this module BUILDS and the report block `rip_report` WRITES are now provably the
# same shape, checked, rather than two descriptions that agree by habit.
from platterpus.report_types import (
    ReportReadSpeedBlock,
    RetriedTrackBlock,
    SpeedPassBlock,
)

log = logging.getLogger(__name__)

# The read-speed rungs, fastest → slowest. 0 means "let the drive pick" (its
# maximum) and is the first, fastest rung — cyanrip omits ``-S`` entirely there.
# The remaining rungs are the classic EAC-style step-down (8× → 4× → 2×); many
# drives read a marginal disc more accurately slower. 2× is the FLOOR (the last
# rung): below it there's little accuracy to gain and a lot of time to lose.
DEFAULT_LADDER: tuple[int, ...] = (0, 8, 4, 2)
FLOOR_SPEED: int = DEFAULT_LADDER[-1]

# At the floor speed, if a disc STILL won't read clean, escalate cyanrip's `-Z N`
# (re-read a track until one read matches N earlier ones: N+1 identical reads)
# instead of going slower. Start at 2 (three identical reads) and climb to this
# ceiling, then give up (and FLAG).
_Z_FLOOR: int = 2
MAX_SECURE_REREP: int = 3


def recovery_secure_rerip_ceiling(
    *, secure_rerip_matches: int, max_retries: int
) -> int:
    """The highest ``-Z`` a RECOVERY re-read may use on this rip.

    Two callers in the rip worker ask this: the ladder's ``-Z`` escalation after
    a pass with read errors, and the auto-fix that re-reads a track whose ``-Z``
    pass never converged. One answer, so the two cannot disagree.

    * **The user set a ``-Z``** (``secure_rerip_matches > 0``): their number is the
      ceiling and is returned as it is. It is never lowered here — quietly asking
      for fewer matching reads than they chose would weaken their verification
      without telling them. Whether it can converge under their ``-r`` is refused
      at the input boundary (``settings_validation``) and again at the argv
      chokepoint, which is where a caller that skipped Settings is caught.
    * **They left it Off** (0): the recovery still needs SOME ``-Z``, so it falls
      back to :data:`MAX_SECURE_REREP` — but **capped at what their ``-r`` lets
      converge**. That bound is ours, not theirs, so it is ours to keep inside
      their limit. Until 2026-09-28 it was not: with Max retries at 3 the ladder
      sent ``-Z 3 -r 3``, a pass that reads every track three times and can never
      converge (``cyanrip@faec4a8:src/cyanrip_main.c:997-1012``), then flagged
      every track unstable and re-read them all again the same way.

    Returns 0 when no ``-Z`` can converge at all (one read allowed); both callers
    already treat 0 as "no secure re-read", so nothing is attempted rather than
    something doomed. Never raises.
    """
    if secure_rerip_matches > 0:
        return secure_rerip_matches
    return min(
        MAX_SECURE_REREP,
        highest_convergeable_repeat_rips(retries_flag_value(max_retries)),
    )


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
    until N+1 passes are identical). Returns None when both are exhausted — the
    caller then stops and FLAGS the disc as still-failing. Never raises: an
    unknown current speed is treated as the top rung so escalation still makes
    progress.

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
            # `-Z N` is satisfied by N+1 identical passes, so that is the number
            # the reason names; it said "{N} passes agree" until 2026-09-28.
            reason = (
                "drive can't change speed — re-reading until "
                f"{next_z + 1} passes are identical (-Z {next_z})"
                if speed_locked
                else f"still failing at {_speed_label(floor)} — re-reading until "
                f"{next_z + 1} passes are identical (-Z {next_z})"
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
    also lands as an "error" in that track's status, unless instability put it
    there (:func:`_instability_explains_arm`). A disc simply *not in
    AccurateRip* is NOT an error (nothing to re-read for) — this returns False
    for it, so the ladder never spins on a clean-but-unknown disc.
    """
    try:
        health = getattr(rip_log, "health_status", "") or ""
        if health and "no error" not in health.lower():
            return True
        for track in getattr(rip_log, "tracks", ()) or ():
            if "error" not in (getattr(track, "status", "") or "").lower():
                continue
            if _instability_explains_arm(track):
                continue
            return True
        return False
    except Exception:  # noqa: BLE001 — an escalation predicate must not crash
        log.exception("read_errors_present failed; assuming no errors")
        return False


def _instability_explains_arm(track: object) -> bool:
    """True when a track's ``with errors`` arm reports instability, not a failed read.

    **Why this exists.** From ``+platterpus.20`` the fork moves a track to
    ``read with errors.`` in two cases that were ``read successfully!`` before:
    paranoia skipped on it, or its ``-Z`` re-read hit the repeat limit
    (``cyanrip@1770d3c:src/cyanrip_main.c:1276-1282``). Up to ``.19`` only a read
    the drive failed moved the arm, and every such read is also counted in
    ``Ripping errors:``, which the health check above reads first.

    Instability is handled per track (the securing pass and the auto-fix), never
    by re-reading the whole disc slower; see :func:`unstable_tracks`. Leaving
    these two cases out keeps the ladder keyed on what it was keyed on, whichever
    build wrote the log. Whether skips SHOULD step the speed down is a policy
    question for the maintainer; a ripper upgrade must not answer it for them.
    Never raises.
    """
    if getattr(track, "secure_rerip_converged", None) is False:
        return True
    counts = getattr(track, "paranoia_counts", None) or {}
    skips = counts.get("SKIP", 0) if isinstance(counts, dict) else 0
    return isinstance(skips, int) and skips > 0


def unstable_tracks(rip_log: object) -> list[int]:
    """Track numbers whose cyanrip secure re-read (``-Z``) never converged.

    cyanrip re-reads a track until N+1 reads are identical; when it instead hits
    the repeat limit first (two reads MAY have agreed: at `-Z 2` it takes three),
    that track's data is UNSTABLE (a
    scratch/dirt region) and may not be bit-perfect. This is the reliable
    per-track read-quality signal — distinct from cyanrip's whole-disc
    ripping-error count (which stays 0 even then; see :func:`read_errors_present`)
    and from a one-frame AccurateRip match (``Accurip 450``: one frame agreed and
    the rest of the track matched nothing; it says nothing about stability either
    way — see :mod:`platterpus.one_frame_match`). Per the maintainer's "flag it, don't auto
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


def disc_in_accuraterip(rip_log: object) -> bool:
    """True if the disc appears to be in the AccurateRip database.

    Signalled by *at least one* track getting a real AR match — v1/v2
    (:func:`track_accuraterip_verified`) or an offset-variant match
    (``accuraterip_offset``). This is the discriminator the dynamic secure
    re-rip needs: it separates "in the DB, but some tracks didn't match" (worth
    a targeted re-rip of the failing tracks — a DB consensus exists to converge
    toward) from "not in the DB at all" (a CD-R or obscure pressing — no
    consensus exists, so a re-rip can't produce a match and would only waste a
    whole second pass on every track, the exact slowdown dynamic mode avoids).
    Pure, never raises.
    """
    try:
        for track in getattr(rip_log, "tracks", ()) or ():
            if track_accuraterip_verified(track):
                return True
            if accuraterip_is_match(getattr(track, "accuraterip_offset", None)):
                return True
        return False
    except Exception:  # noqa: BLE001 — a predicate must never crash a rip
        log.exception("disc_in_accuraterip failed; assuming not in DB")
        return False


def tracks_failing_accuraterip(
    rip_log: object, *, include_offset_variant: bool = False
) -> list[int]:
    """Track numbers NOT proven by AccurateRip after a pass.

    A track is "proven" if AccurateRip v1/v2 matched. With the function's default
    a one-frame match (``Accurip 450``, called "offset-variant" in this code) also
    counts as proven and is skipped — the fast first read is kept. The rip worker
    passes the user's setting, which is on by default since the release after
    0.6.56, because one frame matching verifies one frame. In *dynamic* secure-rerip mode these are the
    tracks worth a targeted `-Z` re-rip: a track that matched the database on the
    fast first read is treated as proven, so re-reading it is normally wasted time.

    When ``include_offset_variant`` is True, an offset-variant-only match is NOT
    treated as proven and IS returned for re-read. This is the opt-in
    "re-read offset-variant tracks until they stabilize" behaviour: an
    offset-variant match confirms *a* pressing but does NOT prove the read is
    reproducible — real hardware showed a track offset-variant-matching two rips
    with *different* full-track audio each time (2026-07-23). Re-reading until
    ``-Z`` reads agree yields a stable, reproducible read for such a track.

    Everything that didn't match the DB at all is always returned. Data tracks are
    skipped. Pure, sorted, deduped, never raises.
    """
    try:
        numbers: list[int] = []
        for track in getattr(rip_log, "tracks", ()) or ():
            if track_accuraterip_verified(track):
                continue
            if not include_offset_variant and accuraterip_is_match(
                getattr(track, "accuraterip_offset", None)
            ):
                continue
            if "data track" in (getattr(track, "status", "") or "").lower():
                continue
            number = getattr(track, "number", None)
            if isinstance(number, int):
                numbers.append(number)
        return sorted(set(numbers))
    except Exception:  # noqa: BLE001 — a report/predicate helper must not crash
        log.exception("tracks_failing_accuraterip failed; assuming none")
        return []


def attempts_to_report(
    attempts: list[SpeedAttempt],
    unstable: list[int] | None = None,
    retried: list[RetriedTrackBlock] | None = None,
) -> ReportReadSpeedBlock | None:
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
                SpeedPassBlock(
                    attempt=a.attempt,
                    speed=a.speed,
                    speed_label=_speed_label(a.speed),
                    secure_rerip_matches=a.secure_rerip_matches,
                    clean=a.clean,
                )
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
            # Copied field-by-field rather than `dict(r)`. The copy is the point —
            # the report must not alias a caller's live dict — but `dict(r)` throws
            # the shape away in the process, so the one place that knows what a
            # retried-track record contains stopped saying it. Naming the fields
            # keeps the copy AND makes a producer that forgets one fail here.
            "retried_tracks": [
                RetriedTrackBlock(
                    track=r["track"],
                    reripped_z=r["reripped_z"],
                    converged=r["converged"],
                    replaced=r["replaced"],
                    # `.get`, not `[]`: a record written before schema v30
                    # has no reason, and "not recorded" is what None says.
                    replaced_because=r.get("replaced_because"),
                )
                for r in (retried or [])
            ],
        }
    except Exception:  # noqa: BLE001 — report helpers never crash a rip
        log.exception("read-speed ladder attempts_to_report failed")
        return None
