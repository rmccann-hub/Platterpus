# SPDX-License-Identifier: GPL-3.0-only
"""When a rip pass steps the read-speed ladder down: the one predicate.

**Why this module exists (round 30 lap 9 S27, the cyanrip fork's finding).** The
ladder's job is to re-read, slower, a disc the drive could not read cleanly. The
rip worker escalated only on ``success and had_read_errors``, where ``success``
was "cyanrip exited 0". But cyanrip exits 1 whenever its drive error count is not
zero (``cyanrip@910dd99:src/cyanrip_main.c:3124``, ``return (err_cnt ||
fatal_abort) ? 1 : 0;``; upstream ``return !!err_cnt;`` at
``cyanrip@f8ebf48:src/cyanrip_main.c:2128``). So the one pass the ladder exists
for ended it, at full speed, on every build, and our round 30 lap 8 S28 said the
opposite. The exit code says the run reported errors; it cannot say whether the
run *finished*, and finishing is what makes a slower re-read worth trying.

**So the decision reads the log, and the exit code only rules cases out.** A pass
steps the disc down when all of these hold, and :func:`judge_step_down` says which
one did not:

1. Platterpus did not stop it (a cancel or a stop we sent is not a disc fault);
2. cyanrip exited 0 or 1, the only codes its own ``main()`` returns; anything else
   is a signal, a crash or the container going away;
3. the log we read is this pass's own, not one an earlier pass left on disk (a
   pass that fails before cyanrip opens its log leaves the old one in place, and
   exit 1 never stepped the ladder before, so nothing had to tell them apart);
4. no encode failed, because slowing the drive cannot mend an encoder;
5. the pass finished every track it was asked for (:func:`why_pass_incomplete`);
6. and the drive failed at least one read
   (:func:`~platterpus.read_speed_ladder.read_errors_present`), which from the
   fork's ``.20`` takes paranoia's skips out of the count, because skips are read
   instability and instability is handled per track, never by re-reading the
   whole disc (the policy of 4790a16a; the fork's S12).

**A finished pass is four of those, 1, 2, 3 and 5** (:func:`why_pass_unfinished`).
The securing pass asks it of an album pass that exited 1 (the maintainer's ruling
C1, ``PLANNING.md`` KDD-41; the gate is ``securing_pass.why_no_securing_pass``).
It re-reads the tracks AccurateRip did not confirm, and it was keyed on exit 0, so
a pass the drive could not read cleanly, the one whose tracks most need it, never
got one. It does not ask for read errors (a clean exit-0 pass is where it always
ran) or refuse a failed encode (its re-read goes to a temporary folder and is kept
only when it is the better read, so it cannot make a track worse). Both questions
share :func:`_why_process_did_not_finish`, so they cannot disagree about what
"Platterpus stopped it" or "a signal ended it" means.

Pure, no Qt, no I/O, and never raises: an escalation decision made from a
best-effort parse must not crash the rip, and a refusal is the safe answer when
the evidence cannot be read (a wrong step costs a whole slower re-read; a missed
one leaves the disc where it was before this module existed).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from platterpus.read_speed_ladder import read_errors_present

log = logging.getLogger(__name__)

#: The exit codes cyanrip's own ``main()`` returns. The fork keeps every exit
#: "within {0, 1}" as a standing requirement of ours
#: (``cyanrip@910dd99:src/cyanrip_main.c:3123``), and upstream returns ``!!err_cnt``.
CYANRIP_OWN_EXITS: frozenset[int] = frozenset({0, 1})


@dataclass(frozen=True)
class StepDown:
    """Whether a pass steps the ladder down, and the sentence that says why."""

    warranted: bool
    reason: str


def judge_step_down(
    rip_log: object,
    *,
    exit_code: int | None,
    stopped_by_us: bool,
    log_is_this_passes: bool,
    only_tracks: Sequence[int] = (),
    disc_track_total: int | None = None,
) -> StepDown:
    """THE escalation decision for one finished pass. See the module docstring.

    ``only_tracks`` and ``disc_track_total`` are what the rip ASKED for
    (``RipParameters``): a ``-l`` selection, or the whole disc of that many tracks.
    Returns a refusal whose ``reason`` names the first condition that failed, so
    the rip's log can say why a pass with read errors did not step. Never raises.
    """
    try:
        process = _why_process_did_not_finish(
            exit_code=exit_code,
            stopped_by_us=stopped_by_us,
            log_is_this_passes=log_is_this_passes,
        )
        if process:
            return StepDown(False, process)
        if not read_errors_present(rip_log):
            return StepDown(False, "the drive reported no read errors")
        encoder = getattr(rip_log, "encoder_failed_tracks", None)
        if isinstance(encoder, int) and encoder > 0:
            return StepDown(
                False,
                f"{encoder} track(s) failed to encode, which a slower read cannot mend",
            )
        incomplete = why_pass_incomplete(
            rip_log, only_tracks=only_tracks, disc_track_total=disc_track_total
        )
        if incomplete:
            return StepDown(False, f"the pass did not finish: {incomplete}")
        drive = getattr(rip_log, "drive_read_errors", None)
        counted = (
            f"the drive failed {drive} read(s)"
            if isinstance(drive, int) and drive > 0
            else "its log shows read errors"
        )
        return StepDown(True, f"the pass finished and {counted}")
    except Exception:  # noqa: BLE001 — an escalation decision must not crash the rip
        log.exception("judge_step_down failed; not stepping the ladder down")
        return StepDown(False, "the step-down check failed (see the app log)")


def why_pass_unfinished(
    rip_log: object,
    *,
    exit_code: int | None,
    stopped_by_us: bool,
    log_is_this_passes: bool,
    only_tracks: Sequence[int] = (),
    disc_track_total: int | None = None,
) -> str:
    """``""`` when the pass FINISHED; otherwise which condition refused.

    Conditions 1 to 3 and 5 of the module docstring, in that order. Exit 0 and
    exit 1 are judged alike, because cyanrip exits 1 for a finished pass whose
    drive failed a read, as well as for one it did not finish. A cancel, a stop we
    sent, a signal or crash exit, an exit status never collected, a log an earlier
    pass left behind, and a pass that did not finish every requested track all
    refuse. The securing pass's gate delegates to this for every case but a clean
    exit 0 (``securing_pass.why_no_securing_pass``, ruling C1, KDD-41).

    Takes :func:`judge_step_down`'s arguments, for the same pass and the same
    evidence. Never raises; a check that fails refuses.
    """
    try:
        process = _why_process_did_not_finish(
            exit_code=exit_code,
            stopped_by_us=stopped_by_us,
            log_is_this_passes=log_is_this_passes,
        )
        if process:
            return process
        incomplete = why_pass_incomplete(
            rip_log, only_tracks=only_tracks, disc_track_total=disc_track_total
        )
        return f"the pass did not finish: {incomplete}" if incomplete else ""
    except Exception:  # noqa: BLE001 — a gate must not crash the rip
        log.exception("why_pass_unfinished failed; treating the pass as unfinished")
        return "the finished-pass check failed (see the app log)"


def _why_process_did_not_finish(
    *, exit_code: int | None, stopped_by_us: bool, log_is_this_passes: bool
) -> str:
    """Conditions 1 to 3: ``""`` when the PROCESS ended on its own with its own log.

    Shared by :func:`judge_step_down` and :func:`why_pass_unfinished`, so the two
    say the same sentence for the same case. Pure; cannot raise.
    """
    if stopped_by_us:
        return "Platterpus stopped this pass"
    if exit_code is None:
        return "cyanrip's exit status was never collected"
    if exit_code not in CYANRIP_OWN_EXITS:
        return (
            f"cyanrip exited {exit_code}, which its own main() never returns "
            "(a signal, a crash or the container), so the pass did not finish"
        )
    if not log_is_this_passes:
        return "this pass wrote no log of its own"
    return ""


def why_pass_incomplete(
    rip_log: object,
    *,
    only_tracks: Sequence[int] = (),
    disc_track_total: int | None = None,
) -> str:
    """``""`` when the log shows the pass finished every track it was asked for.

    Otherwise the reason it does not. Evidence, strongest first:

    * **The ripper's own footer**, ``Rip completed:  yes (N of M tracks)``. It is
      ``no (...)`` for an interrupted or aborted run, and from the fork's ``.20``
      a failed track aborts. Before ``.20`` a failed track in an all-tracks rip
      still printed ``yes`` (their round 30 lap 9 S22), so the footer is not trusted
      alone: the tracks must be there too.
    * **Our own per-track parse**: a block for every requested track (data tracks
      count, since cyanrip skips them by design), no ``Interrupted at:``, and a
      log that was not cut off. ``M`` in the footer is the disc's total
      including data tracks, so for a whole-disc rip the blocks must number at
      least ``M``; for a ``-l`` selection each requested number must have one.
    * **No footer at all** (stock cyanrip never prints one): the finish report's
      ``Ripping errors:`` line must be there, which upstream prints only when its
      rip loop falls through rather than jumping to ``end:``
      (``cyanrip@f8ebf48:src/cyanrip_main.c:2110-2112``), and the track check above
      still applies, with our own disc total.

    Never raises; a log it cannot read is incomplete ("not determined" is not a
    pass).
    """
    try:
        if rip_log is None:
            return "there is no log to read"
        completed = getattr(rip_log, "rip_completed", None)
        reason = str(getattr(rip_log, "rip_completed_reason", "") or "").strip()
        if completed is False:
            return f"the log says it did not complete ({reason or 'no reason given'})"
        if completed is None and getattr(rip_log, "ripping_errors", None) is None:
            return "the log has no completion footer and no finish report"
        where = getattr(rip_log, "interrupted_at", None)
        if where:
            return f"the log records an interruption at {where}"
        if getattr(rip_log, "log_truncated", False):
            return "the log was cut off"
        if getattr(rip_log, "last_track_incomplete", False):
            return "the last track's block is incomplete"
        numbers = {
            number
            for track in getattr(rip_log, "tracks", ()) or ()
            if isinstance(number := getattr(track, "number", None), int)
        }
        if not numbers:
            return "the log holds no track blocks"
        if only_tracks:
            missing = sorted(set(only_tracks) - numbers)
            if missing:
                listed = ", ".join(str(n) for n in missing)
                return f"track(s) {listed} were asked for and have no block in the log"
            return ""
        footer_total = getattr(rip_log, "rip_completed_total", None)
        total = footer_total if isinstance(footer_total, int) else disc_track_total
        if not isinstance(total, int) or total < 1:
            return "how many tracks the disc has is not known"
        if len(numbers) < total:
            return (
                f"the log holds {len(numbers)} track block(s) of a {total}-track disc"
            )
        return ""
    except Exception:  # noqa: BLE001 — a completeness check must not crash the rip
        log.exception("why_pass_incomplete failed; treating the pass as incomplete")
        return "the completeness check failed (see the app log)"
