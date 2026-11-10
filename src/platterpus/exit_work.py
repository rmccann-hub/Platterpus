"""Work that must finish before the process exits, after the window has gone.

**What it is for.** Quitting during a rip must stop the ripper, and stop it so
that its log keeps its footer: cyanrip is sent SIGTERM and given a grace to
finish the read in hand and write the end of its log, and only then, if it still
holds the drive, SIGKILL. cyanrip acts on SIGTERM only once that read returns,
and the rig's drive has been measured taking 54 seconds over one read of a
damaged disc (the 2026-10-04 run), so the grace is long. Waiting it out on the GUI
thread froze the window for up to half a minute at the moment the user asked it
to go away.

So the window closes at once, and the wait moves here: ``closeEvent`` hands the
stop to :func:`start`, which runs it on a helper thread, and ``app.main`` calls
:func:`wait` after ``app.exec()`` returns and before the process exits. The
window is already gone by then, so no slot can fire into it, and the process
lingers without a window only for as long as the reader takes to let go.

**Why the join, and why it is bounded.** The helper is a daemon thread, so an
interpreter exit that did not wait for it would kill it part-way through
stopping the reader, and leave cyanrip holding the drive after the app has gone
(the 2026-07-01 report). The join is what prevents that. It is bounded by each
job's own budget plus a margin, because the job's subprocesses are themselves
bounded and a wait past that would only hide a hang.

Plain ``threading``, not ``QThread``: the work touches no Qt object, and a
Python thread carries none of ``~QThread()``'s hazards (Critical rule #9).
Never raises.

**Freeing the drive after a cancelled ripper child** (:func:`free_drive_after_cancel`,
2026-11-05) is exit work too, though it is usually started mid-session. Killing a
ripper child kills OUR process group: the host wrapper and the ``podman exec``
client. The ``cyanrip`` inside the ``ripping`` container is not in that group and
podman does not forward the signal, so it reads on, holding the drive (the
owner's rig, 2026-11-05: a ui-script rip stopped from the console left two
``cyanrip`` reading ``/dev/sr0`` after the app had closed, until the disc was
ejected by hand). The app's own rip has always freed the drive after its cancel;
this is the same ``drive_control`` step for every other path that cancels a
ripper child. Started here so that, whenever it is started, the process does not
exit before it has finished, and the exit check (:func:`audit`) reports only what
is left after it.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from platterpus import drive_control

log = logging.getLogger(__name__)

#: How long :func:`wait` allows past a job's own budget. The budget bounds the
#: job's steps, but a subprocess started just before the budget ran out still
#: runs for its own timeout, so the join allows a few seconds more.
JOIN_MARGIN_S: Final[float] = 5.0


@dataclass
class _Job:
    """One piece of exit work: its thread, its name, and when it must be done."""

    thread: threading.Thread
    name: str
    deadline: float


_LOCK: Final[threading.Lock] = threading.Lock()
_JOBS: list[_Job] = []


def start(
    work: Callable[[], object],
    *,
    name: str,
    budget_s: float,
    clock: Callable[[], float] = time.monotonic,
) -> threading.Thread:
    """Run ``work`` on a helper thread that :func:`wait` joins before exit.

    ``work`` must be thread-safe: no Qt, no widgets, no dialogs. It is expected
    to bound itself to ``budget_s``; the join allows that plus
    :data:`JOIN_MARGIN_S`. A failure inside it is logged, never raised. Returns
    the thread, already started.
    """

    def run() -> None:
        try:
            work()
        except Exception:  # noqa: BLE001 — exit work must not die silently
            log.exception("exit work %r failed", name)

    thread = threading.Thread(target=run, name=f"exit-{name}", daemon=True)
    with _LOCK:
        _JOBS.append(_Job(thread, name, clock() + budget_s))
    log.info("exit work %r started, budget %.0fs", name, budget_s)
    thread.start()
    return thread


def pending() -> int:
    """How many exit jobs are still running."""
    with _LOCK:
        return sum(1 for job in _JOBS if job.thread.is_alive())


def wait(
    *,
    margin_s: float = JOIN_MARGIN_S,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Join every exit job, each up to its deadline plus ``margin_s``.

    Returns ``True`` when every job finished, ``False`` when one was still
    running at its deadline. That one is left to die with the process, and the
    log says which, because the work it was doing is then not known to be done.
    """
    with _LOCK:
        jobs = list(_JOBS)
    finished = True
    for job in jobs:
        remaining = job.deadline + margin_s - clock()
        if job.thread.is_alive():
            log.info(
                "waiting up to %.0fs for exit work %r before the process exits",
                max(remaining, 0.0),
                job.name,
            )
        job.thread.join(timeout=max(remaining, 0.0))
        if job.thread.is_alive():
            finished = False
            log.warning(
                "exit work %r did not finish within its budget; the process exits "
                "without it, so what it was doing is not known to be done",
                job.name,
            )
    with _LOCK:
        _JOBS[:] = [job for job in _JOBS if job.thread.is_alive()]
    return finished


# --- Freeing the drive after a ripper child was cancelled ---------------------

#: A disc probe writes no log, so its reader is SIGKILLed: one bounded ``fuser``.
PROBE_FREE_BUDGET_S: Final[float] = 25.0

#: A rip writes a log whose footer comes from cyanrip's ``atexit``, so its reader
#: gets SIGTERM, the grace, and SIGKILL only after that: the app's own shutdown
#: stop's budget, for the same reason (``main_window_rip._SHUTDOWN_DRIVE_FREE_BUDGET_S``).
RIP_FREE_BUDGET_S: Final[float] = drive_control.READER_TERM_GRACE_S + 5.0


def _sigkill_probe_reader(device: str, runner: drive_control.Runner) -> object:
    """Device-scoped SIGKILL (``fuser -k``) of whatever holds ``device``.

    Device-scoped ONLY, never the broad host ``pkill`` that ``free_drive`` falls
    back to: a probe's reader is found by the device it holds, and a name match
    could kill a rip on another drive. The in-container reader is host-visible
    on rootless podman, which is why the host step reaches it (the rig's
    ``fuser -k ... free_drive: killed=True`` the same night); if the host sees
    nothing holding the device, nothing is reading it.
    """
    return drive_control.free_device_holders(device, runner=runner)


def _stop_rip_reader(device: str, runner: drive_control.Runner) -> object:
    """SIGTERM, grace, then SIGKILL: ``drive_control.stop_reader_gracefully``."""
    return drive_control.stop_reader_gracefully(device, runner=runner)


#: The ``drive_control`` steps the frees below run. Module attributes read at
#: call time, so the test suite puts recorders in their place
#: (``tests/conftest.py``): a test must never signal whatever holds a real drive
#: on the machine running it.
probe_reader_stop: Callable[[str, drive_control.Runner], object] = _sigkill_probe_reader
rip_reader_stop: Callable[[str, drive_control.Runner], object] = _stop_rip_reader

#: The device each free in flight is for, so a second cancel of the same drive
#: does not start a second, competing stop (a SIGKILL racing a graceful stop's
#: grace would cost the rip its log footer). Touched on the GUI thread only.
_FREEING: dict[str, threading.Thread] = {}


def freeing(device: str) -> bool:
    """Whether a free of ``device`` started here is still running."""
    with _LOCK:
        thread = _FREEING.get(device)
    return thread is not None and thread.is_alive()


def free_probe_drive_now(device: str, *, why: str) -> None:
    """SIGKILL whatever holds ``device`` now, on the CALLER's thread. Blocking.

    For a caller already off the GUI thread that must not go on until the drive
    is free: the disc probe that replaces a superseded one, which would
    otherwise read beside the superseded probe's in-container reader
    (``DiscInfoWorker``). Bounded by :data:`PROBE_FREE_BUDGET_S`. Never raises.
    """
    if not device:
        return
    log.info("freeing %s before reading it (%s)", device, why)
    try:
        probe_reader_stop(device, drive_control.budgeted_runner(PROBE_FREE_BUDGET_S))
    except Exception:  # noqa: BLE001 — a free must never stop the probe after it
        log.exception("freeing %s before reading it failed", device)


def free_drive_after_cancel(device: str, *, writes_log: bool, why: str) -> bool:
    """Stop the in-container reader a cancelled ripper child left on ``device``.

    Non-blocking: the stop runs as exit work (:func:`start`), so the GUI thread
    never waits on it and the process never exits before it. ``writes_log``
    picks the stop: a rip's reader gets SIGTERM and the grace so its log keeps
    its footer (:data:`RIP_FREE_BUDGET_S`); a probe's is SIGKILLed
    (:data:`PROBE_FREE_BUDGET_S`). Returns True when a stop was started; False
    with no device (said in the log as not determined) or when one is already
    running for ``device``. Call on the GUI thread.
    """
    if not device:
        log.warning(
            "%s: no device to scope the stop to, so whether the in-container "
            "reader still holds a drive is NOT DETERMINED",
            why,
        )
        return False
    if freeing(device):
        log.info(
            "%s: %s is already being freed; not starting a second stop", why, device
        )
        return False
    budget = RIP_FREE_BUDGET_S if writes_log else PROBE_FREE_BUDGET_S
    stop = rip_reader_stop if writes_log else probe_reader_stop
    log.info(
        "%s: the host side was killed, but the reader inside the container is not "
        "in that process group; freeing %s (%s)",
        why,
        device,
        "SIGTERM, grace, then SIGKILL" if writes_log else "device-scoped SIGKILL",
    )

    def work() -> None:
        stop(device, drive_control.budgeted_runner(budget))

    thread = start(work, name=f"free-{device}", budget_s=budget)
    with _LOCK:
        _FREEING[device] = thread
    return True


#: The exit audit's whole budget: two quick host probes, run when the window has
#: gone and nothing waits on the process but its own exit.
AUDIT_BUDGET_S: Final[float] = 4.0


@dataclass(frozen=True)
class ExitAudit:
    """What the host saw of the drive and the ripper as Platterpus left.

    Both fields are tri-state: ``None`` is "no answer", never "all clear".
    """

    device: str
    #: Whether anything still holds ``device`` (``fuser``).
    device_held: bool | None
    #: The reader processes still running, as ``"<pid> <name>"`` (``pgrep``).
    readers: tuple[str, ...] | None

    @property
    def clean(self) -> bool | None:
        """True when the drive is free and no reader runs; None when unknown."""
        if self.device_held is True or self.readers:
            return False
        if self.device_held is False and self.readers == ():
            return True
        return None

    def sentence(self) -> str:
        """One line for the log, naming what was seen and what could not be."""
        drive = self.device or "the drive"
        if self.device_held is True:
            held = f"{drive} is STILL HELD"
        elif self.device_held is False:
            held = f"nothing holds {drive}"
        elif self.device:
            held = f"whether {drive} is held is not known (fuser gave no answer)"
        else:
            held = "no drive was in use, so none was checked"
        if self.readers:
            procs = "a ripper is STILL RUNNING (" + ", ".join(self.readers) + ")"
        elif self.readers == ():
            procs = "no ripper process is running"
        else:
            procs = "whether a ripper is running is not known (pgrep gave no answer)"
        verdict = {
            True: "Platterpus left nothing behind",
            False: "Platterpus has closed but left this behind",
            None: "so it is not known whether Platterpus left anything behind",
        }[self.clean]
        return f"exit check: {held}; {procs}, as the host sees them — {verdict}"


def audit(device: str, *, runner: drive_control.Runner | None = None) -> ExitAudit:
    """Check, once the exit work is done, that the drive and the ripper are free.

    Asked for by our operator (2026-10-05): a bundle is written while Platterpus
    runs, so nothing in it can show that a close let go of the drive. This line
    goes to the log at the moment of exit, where the next session's log, and its
    bundle, carry it. It reports; it does not kill: stopping the ripper is the
    exit work above (the app's own rip's stop, and every
    :func:`free_drive_after_cancel`), which :func:`wait` has joined before this
    runs, so what it shows is what was left AFTER the drive was freed. A
    straggler it shows is a fact to read, not to act on silently. Bounded by :data:`AUDIT_BUDGET_S`. Never raises.

    "As the host sees them": a reader in the ripping container is normally
    visible on the host, which is why the force-stop asks the host first. If a
    host ever cannot see it, this reads "nothing", and the sentence says whose
    view it is so that reading is not taken for more than it is.
    """
    run = runner or drive_control.budgeted_runner(AUDIT_BUDGET_S)
    try:
        held = drive_control.device_is_held(device, run) if device else None
        readers = drive_control.running_readers(run)
    except Exception:  # noqa: BLE001 — an audit must never stop the exit
        log.exception("exit check could not run")
        held, readers = None, None
    result = ExitAudit(device=device, device_held=held, readers=readers)
    if result.clean is True:
        log.info(result.sentence())
    else:
        log.warning(result.sentence())
    return result
