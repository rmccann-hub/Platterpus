"""When a disc read fails: may the app try again on its own, and what does it say?

**Why this exists (2026-09-28).** The maintainer reported, from the rig: *"sometimes
it asks immediately about what the artist is, sometimes I have to open the drive and
close it again and restart the app."* Every failed disc read (`cyanrip -I`) ended the
same way: an error line in the disc panel, and nothing else, ever. Nothing retried
it, and the drive-status watcher could not rescue it either, because its first
reading after a drive change is only a baseline — so a disc that became ready while
its first read was failing was never looked at again. The failures that end that way
are the ordinary ones:

* the first read of a session starting a cold `ripping` container
  (`friendly_disc_scan_error` has said *"it's much faster the second time"* since
  2026-06-27 — and left the second time to the user);
* a disc still spinning up when it was read (the tray had just closed);
* the container briefly refusing to start (`exit 125`, *"unable to start
  container"*, measured on the rig: `round26platterpusapplog1.txt` line 812).

So a failed read is now retried automatically, a bounded number of times, and the
panel says so while it waits. When the retries are used up — or a retry would be
pointless — the message ends with what to do, so an error is never the end of it.

**Pure and Qt-free on purpose.** The window gathers the facts
(:class:`RetryConditions`) and applies the answer (:class:`RetryDecision`); the
state and every branch live here, where they are tested without a window. The
decision is a named function that returns *which* condition refused, asked twice —
when a retry is scheduled and again when its timer fires, because anything can
happen in between (CLAUDE.md: *check the preconditions where the thing HAPPENS*).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Final

from platterpus.drive_media import EMPTY, OPEN

#: Automatic retries after a failed disc read, per request (a drive change, a
#: Rescan, an insertion). Two: each failure mode above clears on the first retry
#: when it clears at all, and a disc that fails three reads needs a person.
AUTO_RETRY_LIMIT: Final[int] = 2

#: The wait before each automatic retry. Long enough for a disc to finish
#: spinning up and a container start to settle; short enough that the disc shows
#: up about when the user would have thought to click Rescan.
AUTO_RETRY_DELAY_MS: Final[int] = 4_000

#: How many times a due retry may wait for a drive-freeing kill to finish. A
#: timed-out read starts one (the in-container reader can still hold the drive),
#: and a read started under it would be killed by it. The kill is bounded at three
#: 20 s steps (`drive_control._STEP_TIMEOUT_S`); 15 waits of the delay cover that,
#: and then the retry gives up rather than waiting on.
FREE_WAIT_CHECKS: Final[int] = 15

# Why an automatic retry did not start: each is a sentence the log line and the
# panel carry as-is. "" (no blocker) means go.
BLOCKED_BY_RIP: Final[str] = "a rip is running"
BLOCKED_BY_SCAN: Final[str] = "another disc read is already running"
BLOCKED_BY_NEWER_REQUEST: Final[str] = "a newer disc read replaced this one"
BLOCKED_BY_OTHER_DRIVE: Final[str] = "the drive it was for is no longer selected"
#: Not a refusal: wait and ask again (bounded by FREE_WAIT_CHECKS).
BLOCKED_BY_FREEING: Final[str] = "the drive is still being freed"
BLOCKED_BY_NO_DISC: Final[str] = "the drive reports no disc"
BLOCKED_BY_BUDGET: Final[str] = "the automatic retries are used up"
BLOCKED_BY_FAILURE_KIND: Final[str] = "trying again cannot change this failure"

#: Blockers meaning a NEWER read owns the disc panel, so a cancelled retry leaves
#: it alone. Any other blocker leaves the panel saying "trying again…", which is
#: then false, so the retry replaces it with the given-up text.
PANEL_OWNED_ELSEWHERE: Final[frozenset[str]] = frozenset(
    {BLOCKED_BY_SCAN, BLOCKED_BY_NEWER_REQUEST, BLOCKED_BY_OTHER_DRIVE}
)

#: The one failure no retry can change: the ripper binary is not there. Its
#: remedy is the dependency subsystem's (Critical rule #6), not a re-read.
_PERMANENT_FAILURE_MARKERS: Final[tuple[str, ...]] = ("binary not found",)

# What the window does with a decision.
RETRY_LATER: Final[str] = "retry later"  # (re)arm the timer
READ_NOW: Final[str] = "read now"  # start the automatic re-read
GIVE_UP: Final[str] = "give up"  # show `error_text`; no retry
STAND_DOWN: Final[str] = "stand down"  # a newer read owns the panel; do nothing


@dataclass(frozen=True)
class RetryConditions:
    """The facts an automatic retry depends on, read by the window at the moment
    it asks — never cached from when the retry was scheduled."""

    rip_running: bool
    scan_running: bool
    #: The retry is for the newest read that was asked for (see `request`).
    newest_request: bool
    #: The drive the retry is for is still the selected one.
    same_drive: bool
    #: A drive-freeing kill (after a timed-out read) is still running.
    drive_being_freed: bool
    #: `drive_media.probe_disc_status` for the drive, read now.
    media_status: str


@dataclass(frozen=True)
class PendingRetry:
    """A scheduled automatic retry: what it is for, and how it came to be."""

    device: str
    #: The request counter's value when it was scheduled.
    request: int
    #: The failure it retries, for the message if it is cancelled.
    failure: str
    #: How many times it has already waited for the drive to be freed.
    free_waits: int = 0


@dataclass(frozen=True)
class RetryDecision:
    """What the window should do now. Texts are "" when the panel is left alone."""

    action: str
    log_line: str
    device: str = ""
    retrying_text: str = ""
    error_text: str = ""


def failure_is_retryable(message: str) -> bool:
    """False only for a failure no retry can change (the ripper is missing)."""
    return not any(marker in message for marker in _PERMANENT_FAILURE_MARKERS)


def retry_blocker(conditions: RetryConditions) -> str:
    """The first reason an automatic re-read may not start now, or ``""`` to go.

    Ordered by who owns the drive (a rip, another read), then whether this retry
    is still wanted, then whether the drive can be read. A tray reported empty or
    open refuses because the read would fail for certain — and the drive-status
    watcher reads a disc the moment one arrives, so a retry adds nothing.
    """
    if conditions.rip_running:
        return BLOCKED_BY_RIP
    if conditions.scan_running:
        return BLOCKED_BY_SCAN
    if not conditions.newest_request:
        return BLOCKED_BY_NEWER_REQUEST
    if not conditions.same_drive:
        return BLOCKED_BY_OTHER_DRIVE
    if conditions.drive_being_freed:
        return BLOCKED_BY_FREEING
    if conditions.media_status in (EMPTY, OPEN):
        return BLOCKED_BY_NO_DISC
    return ""


def retrying_text(message: str, retry_number: int) -> str:
    """The panel's line while a retry is pending: what the app is doing, then the
    failure in the ripper's own words (Critical rule #12)."""
    seconds = AUTO_RETRY_DELAY_MS // 1000
    return (
        f"couldn't read the disc yet — trying again automatically in {seconds} s "
        f"(retry {retry_number} of {AUTO_RETRY_LIMIT}).\n"
        f"What happened: {message}"
    )


def given_up_text(friendly: str, blocker: str, attempts: int) -> str:
    """The panel's line once no automatic retry will run. ``friendly`` is
    `friendly_disc_scan_error`'s text, which keeps an unrecognised failure in
    the ripper's own words; an action is added unless it already has one."""
    lines = [friendly]
    if blocker == BLOCKED_BY_NO_DISC:
        lines.append(
            "The drive reports no disc. Insert one and it is read automatically, "
            "or click “Rescan disc”."
        )
    elif blocker == BLOCKED_BY_FAILURE_KIND:
        # A missing ripper: re-reading cannot help, so no Rescan advice. The
        # dependency check is what reports it and offers the install.
        pass
    elif "Rescan disc" not in friendly:
        lines.append(
            "Click “Rescan disc” to try again, or eject and re-insert the disc."
        )
    # Why it stopped, whenever that is not already said above: a user who saw
    # "trying again…" and then this deserves to know which one it was.
    if attempts > 1:
        lines.append(f"(Read {attempts} times; {blocker}.)")
    elif blocker not in (BLOCKED_BY_NO_DISC, BLOCKED_BY_FAILURE_KIND):
        lines.append(f"(Not retried automatically: {blocker}.)")
    return "\n".join(lines)


class DiscReadRetries:
    """The retry state behind the window's disc reads. One per window."""

    def __init__(self) -> None:
        #: Counts the reads that were ASKED for; an automatic retry is not one.
        self.request: int = 0
        #: Automatic retries spent on the current request.
        self.retries_used: int = 0
        self.pending: PendingRetry | None = None

    def new_request(self) -> None:
        """A drive change, Rescan or insertion: a fresh budget, and any retry
        pending for an older read is dropped."""
        self.request += 1
        self.retries_used = 0
        self.pending = None

    def after_failure(
        self, device: str, message: str, friendly: str, conditions: RetryConditions
    ) -> RetryDecision:
        """A read of ``device`` failed with ``message``: retry later, or give up.

        The drive being freed does not refuse here — this very failure started
        the free, and the fire-time check waits for it.
        """
        if not failure_is_retryable(message):
            blocker = BLOCKED_BY_FAILURE_KIND
        else:
            blocker = retry_blocker(conditions)
            if blocker == BLOCKED_BY_FREEING:
                blocker = ""
            # After the conditions, so "the drive reports no disc" (which tells
            # the user what to do) wins over "the retries are used up".
            if not blocker and self.retries_used >= AUTO_RETRY_LIMIT:
                blocker = BLOCKED_BY_BUDGET
        if blocker:
            return RetryDecision(
                GIVE_UP,
                f"disc read of {device} failed; not retrying: {blocker}",
                device=device,
                error_text=given_up_text(friendly, blocker, self.retries_used + 1),
            )
        self.retries_used += 1
        self.pending = PendingRetry(device, self.request, message)
        return RetryDecision(
            RETRY_LATER,
            f"disc read of {device} failed; retrying automatically in "
            f"{AUTO_RETRY_DELAY_MS} ms (retry {self.retries_used} of "
            f"{AUTO_RETRY_LIMIT})",
            device=device,
            retrying_text=retrying_text(message, self.retries_used),
        )

    def when_due(
        self, conditions: RetryConditions, friendly: Callable[[str], str]
    ) -> RetryDecision:
        """The retry timer fired: read now, wait for the drive, or stand down.

        ``conditions`` must be read for the pending retry's own device and
        request. ``friendly`` turns its failure into the panel's text if the
        retry is given up.
        """
        pending, self.pending = self.pending, None
        if pending is None:
            return RetryDecision(STAND_DOWN, "no disc re-read is pending")
        blocker = retry_blocker(conditions)
        if blocker == BLOCKED_BY_FREEING and pending.free_waits < FREE_WAIT_CHECKS:
            self.pending = replace(pending, free_waits=pending.free_waits + 1)
            return RetryDecision(
                RETRY_LATER,
                f"automatic re-read of {pending.device} waits: {blocker}",
                device=pending.device,
            )
        if blocker in PANEL_OWNED_ELSEWHERE:
            return RetryDecision(
                STAND_DOWN,
                f"automatic re-read of {pending.device} not started: {blocker}",
                device=pending.device,
            )
        if blocker:
            return RetryDecision(
                GIVE_UP,
                f"automatic re-read of {pending.device} not started: {blocker}",
                device=pending.device,
                error_text=given_up_text(
                    friendly(pending.failure), blocker, self.retries_used
                ),
            )
        return RetryDecision(
            READ_NOW,
            f"automatic re-read {self.retries_used} of {AUTO_RETRY_LIMIT} of "
            f"{pending.device}",
            device=pending.device,
        )
