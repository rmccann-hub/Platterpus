"""When to run a drive's audio-cache check by itself, and what to say about it.

**Why this exists (TASKS R53, EAC parity).** The cache-defeat verdict is what fills
"Defeat audio cache: Yes/No" in the EAC-compatible log, and log checkers take
points off when that line is missing. The verdict comes from ``cd-paranoia -A``
(KDD-29), a probe that reads the disc for minutes. Until 2026-11-12 it ran only
when the user remembered to press *Analyze cache* in Set up drive, so most drives
never had one. The owner's rule of 2026-11-12 is that drive properties are tested
**once, up front, at drive setup, and saved per drive** — so the check now starts
by itself the first time Set up drive opens for a drive with an audio CD in it.

This module is the *decision*, kept pure so every branch is testable without a
drive, a dialog or a thread:

* :func:`verdict_state` — does this drive's saved profile already hold a verdict
  that still applies? (A firmware update since the measurement means it may not.)
* :func:`decide_auto_check` — given that, the disc, and whether the drive is free,
  should the dialog start the check now, wait for something, or do nothing?
* :func:`rip_start_note` — the one-line, non-blocking note shown when a rip
  starts on a drive that still has no verdict.

What it deliberately does NOT do: run anything, or block a rip. A rip with no
verdict is still a good rip (AccurateRip and CTDB prove the audio); the log just
says "(unknown)" for that one line. So the rip path only *mentions* the check —
it never starts a multi-minute probe on its own before a rip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from platterpus.drive_profiles import DriveProfile

# --- Verdict state ---------------------------------------------------------
#
# Plain strings, like the drive-profile warning kinds, so a log line or a test
# failure reads as words.

#: The profile holds a measured Yes/No that still applies.
MEASURED: Final[str] = "measured"
#: No verdict was ever recorded for this drive (or there is no profile at all).
NOT_MEASURED: Final[str] = "not_measured"
#: A verdict exists, but it was measured under different firmware than the
#: drive now reports, so it may no longer describe the drive.
FIRMWARE_CHANGED: Final[str] = "firmware_changed"


def verdict_state(profile: DriveProfile | None, current_release: str) -> str:
    """Whether ``profile`` holds a cache verdict that still applies. Never raises.

    ``current_release`` is the firmware revision the drive reports right now.

    The firmware the verdict was measured under is its own field
    (``cache_defeat_release``), NOT the profile's ``release``: every drive
    sighting rewrites ``release`` to the current firmware
    (``_record_drive_fact``), so comparing against it would never see a change.

    A verdict recorded before that field existed has no firmware beside it
    (``""``). It is treated as still applying: we cannot tell, and re-measuring
    every such drive would start a several-minute disc read the user did not ask
    for on the strength of a missing field rather than of anything we know.
    """
    if profile is None or profile.cache_defeat is None:
        return NOT_MEASURED
    measured_under = profile.cache_defeat_release.strip()
    now = current_release.strip()
    if measured_under and now and measured_under != now:
        return FIRMWARE_CHANGED
    return MEASURED


# --- What the setup dialog should do ---------------------------------------

#: Start the check now.
START: Final[str] = "start"
#: The check is needed, but there is no audio CD in the drive.
WAIT_FOR_DISC: Final[str] = "wait_for_disc"
#: The check is needed and a disc is in, but the drive is busy (a disc read or
#: a rip has it). Reading it from two programs at once is how a drive wedges.
WAIT_FOR_DRIVE: Final[str] = "wait_for_drive"
#: Nothing to do: the verdict is saved, the backend cannot measure it, or the
#: check already ran once in this dialog (a second automatic run would loop on a
#: drive that answers "inconclusive" every time).
NOTHING: Final[str] = "nothing"


@dataclass(frozen=True)
class AutoCheckDecision:
    """What the dialog should do, and the sentence that says so.

    ``message`` is empty when there is nothing worth telling the user. Every
    non-empty message starts with a status marker (``ⓘ``), so its meaning is
    never carried by colour alone (WCAG 1.4.1).
    """

    action: str
    message: str


def decide_auto_check(
    *,
    can_analyze: bool,
    verdict: str | None,
    audio_disc_present: bool,
    drive_busy: bool,
    already_attempted: bool,
) -> AutoCheckDecision:
    """Decide whether the setup dialog starts the cache check by itself.

    ``verdict`` is a :func:`verdict_state` value, or ``None`` when the caller did
    not say — the dialog's default, so a caller that does not opt in (a test, a
    future second opener) keeps the old button-only behaviour rather than
    starting a disc read nobody asked for.

    The order of the checks is the order that decides the outcome: a backend that
    cannot measure, or a verdict already saved, means nothing to do whatever the
    disc; only then does the disc, and then the drive, matter.
    """
    if not can_analyze or verdict is None or verdict == MEASURED:
        return AutoCheckDecision(NOTHING, "")
    if already_attempted:
        return AutoCheckDecision(NOTHING, "")
    why = (
        "This drive's firmware changed since its audio-cache check, so the check "
        "needs to run again."
        if verdict == FIRMWARE_CHANGED
        else "This drive's audio-cache check has not run yet."
    )
    if not audio_disc_present:
        return AutoCheckDecision(
            WAIT_FOR_DISC,
            f"ⓘ {why} Insert any audio CD and it starts by itself while this "
            "window is open. You can still save the read offset without a disc.",
        )
    if drive_busy:
        return AutoCheckDecision(
            WAIT_FOR_DRIVE,
            f"ⓘ {why} It starts by itself as soon as the drive has finished "
            "reading the disc.",
        )
    return AutoCheckDecision(
        START,
        f"ⓘ {why} It is running now: it reads the CD for a few minutes, and the "
        "result is saved for this drive. Press Skip check to stop it.",
    )


# --- The note at rip start --------------------------------------------------


def rip_start_note(*, can_analyze: bool, verdict: str) -> str | None:
    """The note to show when a rip starts on this drive, or ``None`` for none.

    Never a gate: the rip goes ahead either way. The note says what the missing
    verdict costs (one line of the log) and how to get it, so the user can do it
    after this rip instead of discovering the "(unknown)" in a log checker.
    A backend that cannot measure the cache gets no note: there would be nothing
    the user could do about it.
    """
    if not can_analyze or verdict == MEASURED:
        return None
    why = (
        "This drive's firmware changed since its audio-cache check"
        if verdict == FIRMWARE_CHANGED
        else "This drive's audio-cache check has not run"
    )
    # Short enough for a status bar at an ordinary window width: one or two
    # lines. The rip itself is unaffected, and the note says so first.
    return (
        f"ⓘ {why}, so this rip's log will show the audio cache as unknown (the "
        "rip itself is unaffected). To run it, open Set up drive with an audio CD "
        "in when no rip is running; it starts by itself."
    )
