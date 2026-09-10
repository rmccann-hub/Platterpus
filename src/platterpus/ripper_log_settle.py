"""Wait for the ripper to finish WRITING its log, before anything reads it.

## The defect this exists to remove (2026-09-09 hardware run, §I)

Cancelling a rip destroyed the archival record of that rip — not by damaging it,
but by **reading it 6.1 seconds too early**. The measured sequence:

    22:02:08.392  rip cancel requested; arming the 5s force-stop rescue
    22:02:08.902  ripper.log_verify_failed: cyanrip exit 3: No FUN512 checksum found
    22:02:08.903  rip finished: success=False    <- report + EAC export rendered here
    22:02:13.293  post-cancel rescue: device-scoped SIGTERM to whatever holds /dev/sr0
    22:02:15      Ripping finished at 2026-09-09T22:02:15-04:00   <- log actually done

The log on disk is a **complete, signed record of an interrupted rip** — it
carries ``Rip completed: no (interrupted by SIGTERM, 0 of 14 tracks)``,
``Interrupted at: track 1, mid-read`` and a valid ``Log FUN512:``. Every one of
those lines landed *after* we had already read the file and published our
findings about it. So one race produced three false archival statements:

* ``ripper_log_verification: verdict "failed"`` was written into the report,
  permanently, about a log the ripper would have accepted;
* ``health_status: null`` in the same report, though ``Ripping errors: 1`` is in
  the file;
* ``Conclusive status report : absent — this log carries no end-of-rip summary``
  in the **EAC-compatible log**, over a rip whose end-of-rip summary is six lines
  long.

Not three defects. One, with three faces — which is why the fix is here, upstream
of all three readers, rather than three corrections downstream.

## Why the ripper's exit is not evidence the log is finished

``~/.local/bin/cyanrip`` is the host-exported Distrobox wrapper (Critical rule
#3). Signalling it reaches the wrapper's process group on the **host**; the
process that actually reads the disc and writes the log lives inside the
``ripping`` container, in a tree podman does not forward our signal into — the
same fact ``drive_control`` exists for. So on a cancel, the wrapper exits at once
and its exit says **nothing** about whether the writer has stopped.

The discriminator is therefore not "did the process exit" but:

    **Did we read the ripper's output to EOF?**

EOF on that pipe means the writing process closed its stdout, which it does at
exit. A read loop that ran to EOF has proof the writer is gone. A read loop that
``break``\\ s on a cancel flag has no such proof — and that is the *only* path
where this wait does any work.

This is the ABSENCE rule from ``CLAUDE.md`` in a new place: *an absence in a log
is a fact about the logger before it is a fact about the subject.* A missing
``Log FUN512:`` line is a fact about the file **at the instant we looked**. Before
inferring anything from it, establish that the writer had finished putting things
there.

## No quiet-window heuristic, deliberately

The obvious implementation waits for the file to stop growing for N seconds and
then declares the writer finished. It is wrong here, and measurably so: on the
run above the log went quiet at the cancel and stayed quiet for 6.6 seconds
before the footer appeared, because the footer is written from cyanrip's
``atexit`` and nothing kills the in-container reader until the GUI's force-stop
rescue fires at +5 s. Any quiet window shorter than that concludes "the writer
has stopped" while the writer is merely waiting to be told to stop.

So there are exactly two outcomes, and **no inference between them**: either the
footer appeared (the writer finished; whatever the log says is now a fact about
the artifact), or the deadline expired (we still do not know). The second is
:data:`NOT_SETTLED` and its consumers must report ``not_determined`` — never the
negative.

Which failure the safe direction avoids, said explicitly per ``CLAUDE.md``: a
false *"the writer finished"* stamps ``failed`` into an archival record about a
good log, and that record is what the user keeps. A false *"still writing"* costs
one ``not_determined`` line in a report. The asymmetry is not close.

## Threading

Blocking, and bounded. Called on the rip worker's thread, never the GUI thread.
``should_abandon`` is the interrupt: at window close the reader is about to be
killed synchronously anyway, so waiting for it to finish writing is pointless and
the wait must not hold up teardown. It is a real interrupt rather than a flag the
blocked call never checks — the wait is a poll loop that reads it every tick,
which is what makes it honest under ``CLAUDE.md``'s cancel rule.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

log: Final[logging.Logger] = logging.getLogger(__name__)

#: How often to re-read the log while waiting. Short enough that abandoning the
#: wait at shutdown is not perceptible, long enough that a 20-second wait is
#: eighty stats of one small file rather than thousands.
POLL_S: Final[float] = 0.25

SETTLED: Final[str] = "settled"
NOT_SETTLED: Final[str] = "not_settled"


@dataclass(frozen=True)
class LogSettle:
    """Whether the ripper has finished writing a log, and how we know.

    ``state`` is deliberately two-valued rather than three: "the footer is here"
    and "we still do not know" are the only things this can establish, and adding
    a third that *inferred* completion from silence is the heuristic the module
    docstring rejects. The tri-state lives one layer up, where a not-settled
    result becomes ``not_determined``.
    """

    state: str
    #: One sentence naming what we observed, for the rip log and the report. A
    #: not-settled result that says nothing is the capture-without-surfacing bug.
    reason: str
    #: How long we actually waited. ``0.0`` on the overwhelmingly common path —
    #: a rip read to EOF already has its footer, so this costs one file read.
    waited_s: float = 0.0

    @property
    def is_settled(self) -> bool:
        """True only when the ripper's own footer is on disk."""
        return self.state == SETTLED


def _has_footer(path: Path) -> bool:
    """Whether the log on disk carries cyanrip's ``Log FUN512:`` footer.

    Reads through the parser's own :func:`~platterpus.parsers.cyanrip_log.
    has_log_checksum` rather than re-spelling the pattern, so this and
    :mod:`platterpus.adapters.ripper_log_verify` cannot disagree about what the
    footer looks like — one definition, many callers.

    Never raises: a log we cannot read yet (still being created, a transient
    ``EIO``) is simply "no footer yet", which keeps waiting. That is the correct
    reading while the writer is presumed live, and the deadline bounds it.
    """
    from platterpus.parsers.cyanrip_log import has_log_checksum

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        # Logged, never swallowed (diagnostic-completeness rule). At DEBUG
        # because during a wait this is an expected transient, and one line per
        # 0.25 s tick at WARNING would bury the rip's own output.
        log.debug("could not read %s while waiting for its footer: %r", path, exc)
        return False
    return has_log_checksum(text)


def await_ripper_log_settled(
    log_path: str | Path,
    *,
    deadline_s: float,
    should_abandon: Callable[[], bool] | None = None,
    poll_s: float = POLL_S,
    now: Callable[[], float] = time.monotonic,
    wait: Callable[[float], bool] | None = None,
) -> LogSettle:
    """Wait, bounded, until the ripper's log carries its own completion footer.

    Returns immediately when the footer is already there, which is every rip that
    ran to EOF — so this is free on the normal path and only does work where the
    writer's exit was never observed.

    ``now``/``wait`` are the injected clock seam so tests drive every branch
    without real time. ``wait`` returns True when the caller should stop waiting
    (the shape of :meth:`threading.Event.wait`), so the default sleeps and the
    abandon path short-circuits; per the stand-in rule the fake must not be more
    capable than the real thing, and an ``Event`` is exactly what production uses.

    Never raises.
    """
    path = Path(log_path)
    sleeper = wait if wait is not None else _sleeping_wait
    abandon = should_abandon if should_abandon is not None else _never

    if _has_footer(path):
        return LogSettle(
            SETTLED,
            f"{path.name} already carries the ripper's own completion footer, so "
            "the ripper had finished writing it before we looked",
        )

    started = now()
    # A floor on the deadline rather than trusting the caller: a non-positive
    # budget would make this a single read dressed up as a wait, which reads as
    # having checked. Negative values are the `QThread.wait(-1)` trap in another
    # costume — say what happened instead.
    if deadline_s <= 0:
        return LogSettle(
            NOT_SETTLED,
            f"{path.name} has no completion footer and no time was budgeted to "
            f"wait for one (deadline {deadline_s:.1f}s), so whether the ripper "
            "had finished writing it is NOT DETERMINED",
        )

    log.info(
        "%s has no completion footer yet — waiting up to %.0fs for the ripper to "
        "finish writing it. Reading it now would record a complete log as "
        "unsigned.",
        path.name,
        deadline_s,
    )
    while True:
        if abandon():
            waited = now() - started
            return LogSettle(
                NOT_SETTLED,
                f"the wait for {path.name}'s completion footer was abandoned "
                f"after {waited:.1f}s because the app is closing and the "
                "in-container reader is being stopped, so whether the ripper "
                "finished writing this log is NOT DETERMINED",
                waited,
            )
        waited = now() - started
        if waited >= deadline_s:
            return LogSettle(
                NOT_SETTLED,
                f"{path.name} still carried no completion footer {waited:.1f}s "
                f"after the ripper's host-side wrapper exited, so whether the "
                "ripper finished writing it is NOT DETERMINED — the wrapper's "
                "exit is not the in-container reader's exit, and only that "
                "reader writes the footer",
                waited,
            )
        # Sleep the smaller of one tick and the time left, so the deadline is the
        # deadline rather than the deadline rounded up to a tick.
        #
        # AND THE RETURN VALUE IS HONOURED. It is the `threading.Event.wait`
        # shape — True means "stop waiting" — and the first version of this loop
        # documented that and then dropped it on the floor, which is
        # `CLAUDE.md`'s *a documented capability is not a capability*: a caller
        # passing `event.wait` would have been told it interrupts and got up to
        # one tick of latency and no early exit. Two routes to the same stop,
        # deliberately, because they answer different questions — `should_abandon`
        # is polled, `wait` returns.
        if sleeper(min(poll_s, deadline_s - waited)):
            waited = now() - started
            return LogSettle(
                NOT_SETTLED,
                f"the wait for {path.name}'s completion footer was interrupted "
                f"after {waited:.1f}s, so whether the ripper finished writing "
                "this log is NOT DETERMINED",
                waited,
            )
        if _has_footer(path):
            waited = now() - started
            log.info(
                "%s gained its completion footer %.1fs after the wrapper exited; "
                "the log is now the ripper's finished record and safe to read",
                path.name,
                waited,
            )
            return LogSettle(
                SETTLED,
                f"{path.name} gained the ripper's completion footer {waited:.1f}s "
                "after its host-side wrapper exited — the record on disk is the "
                "ripper's finished one",
                waited,
            )


def _sleeping_wait(seconds: float) -> bool:
    """The default ``wait``: plain sleep, no early return. Never negative."""
    time.sleep(max(0.0, seconds))
    return False


def _never() -> bool:
    """The default ``should_abandon``: nothing interrupts the wait."""
    return False


def event_abandoner(event: threading.Event) -> Callable[[], bool]:
    """A ``should_abandon`` backed by an :class:`threading.Event`.

    A named function rather than a lambda at the call site so the interrupt is
    greppable: ``tests/test_qthread_ownership.py`` and any human auditing whether
    a blocking wait can actually be interrupted are both looking for a call, not
    for a closure buried in an argument list.
    """
    return event.is_set
