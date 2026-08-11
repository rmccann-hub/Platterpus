"""Run a one-shot child process that another thread can actually kill.

**Why this exists.** `subprocess.run` is the obvious way to shell out and it is
the wrong one whenever a GUI needs to be able to stop the work: it constructs the
`Popen` internally and never hands it out, so there is no object to signal. Every
worker built on it therefore has, at best, a `cancel()` that sets a flag the
blocked call never reads — which `CLAUDE.md` rule 9 calls a false promise and
forbids shipping. The codebase had three of those (audit, 2026-07-29).

So the pattern is: `Popen`, register it where another thread can find it,
`communicate(timeout=…)`, deregister. That is fiddly enough to get subtly wrong —
and it *was* written a second time for the cache probe before this module
existed — so it lives here once and the callers share it.

Three things this gets right that a hand-rolled version tends not to:

* **`start_new_session=True` is load-bearing, not hygiene.** It makes the child a
  process-group leader, so one `killpg` reaches the whole tree — which matters
  because these commands are host wrappers that spawn podman which spawns the
  real tool. Signalling only the direct child leaves the actual reader running and
  the disc spinning. Worse, *without* it the child shares **our** group, and a
  `killpg` would signal the GUI itself.
* **The cancel/startup race is closed.** A cancel arriving between `Popen` and
  registration would otherwise find nothing registered and be silently dropped —
  the user presses Cancel and nothing happens. A sticky flag is re-checked right
  after registering.
* **A timeout kills the child.** `subprocess.run` does that for free; `Popen` does
  not, so migrating to `Popen` for cancellability silently *loses* it and leaves a
  timed-out probe running. That is the "what new state does this fix create"
  question from the pre-flight checklist, answered in code.

**SIGKILL, not SIGTERM.** Cancel is called from the GUI thread and must not wait
(the never-block rule), and a reliable SIGTERM needs a grace period plus an
escalation — i.e. waiting. Everything routed through here is a **read-only probe**
(a disc-info read, a `--version` call, a cache measurement) with nothing to flush,
so a hard kill costs nothing and is the only thing that reliably returns the drive.
A child that *does* have state to flush — the rip itself — deliberately does not
use this module; it uses `RipHandle`, which escalates properly on a worker thread.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading

log = logging.getLogger(__name__)

# How long to wait for a killed child to be reaped before giving up on it. Short
# on purpose: SIGKILL has already been sent, so anything still alive is stuck in an
# uninterruptible kernel call (a wedged drive ioctl) where waiting does not help.
REAP_TIMEOUT_S: float = 5.0


class KillableCommand:
    """One named slot holding at most one live child, killable from any thread.

    Not a pool: each instance models a single logical operation the GUI can have in
    flight (the disc-info probe, the cache probe, …), which is all the callers need
    and keeps `cancel()` unambiguous about what it stops. Create one per operation
    at module scope and reuse it.
    """

    def __init__(self, name: str) -> None:
        self._name: str = name
        self._lock: threading.Lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        # Sticky, so a cancel that lands in the window between `Popen` and
        # registration is honoured rather than dropped. Cleared when the run ends.
        self._cancel_requested: bool = False

    @property
    def name(self) -> str:
        return self._name

    def is_running(self) -> bool:
        """Whether a child is currently registered. For diagnostics and tests."""
        with self._lock:
            return self._proc is not None

    def cancel(self) -> None:
        """SIGKILL the running child's process group. Thread-safe, non-blocking.

        Safe to call when nothing is running, and safe to call twice. Sets the
        sticky flag either way so a child that is *about* to be registered is
        killed as soon as it appears.
        """
        with self._lock:
            self._cancel_requested = True
            proc = self._proc
        if proc is None:
            return
        log.info("%s: cancelling (SIGKILL to the process group)", self._name)
        self._kill_group(proc)

    def _kill_group(self, proc: subprocess.Popen[str]) -> None:
        """SIGKILL the child's whole group, falling back to the child alone."""
        if proc.poll() is not None:
            return  # already exited; nothing to signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            # The group may be gone, or getpgid may race with exit. Falling back to
            # the single process is strictly better than giving up: it at least
            # ends the wrapper, even if an in-container child outlives it briefly.
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass

    def run(
        self,
        argv: list[str],
        *,
        timeout: float,
        stdin_devnull: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run `argv` to completion, capturing text output. Cancellable.

        Returns a `CompletedProcess` so this is a drop-in for `subprocess.run` at
        the call sites. Raises `FileNotFoundError` (binary missing) and
        `subprocess.TimeoutExpired` (child killed first) exactly as `run` does, so
        existing error handling keeps working unchanged.

        `stdin_devnull` defaults True because every current caller must not inherit
        the parent's stdin — a tool that reads stdin would otherwise block forever
        on a GUI process with no terminal.
        """
        proc = subprocess.Popen(  # noqa: S603 — callers pass a resolved binary
            argv,
            stdin=subprocess.DEVNULL if stdin_devnull else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # see the module docstring — load-bearing
        )
        with self._lock:
            self._proc = proc
            cancelled_during_startup = self._cancel_requested
        if cancelled_during_startup:
            self._kill_group(proc)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as timed_out:
            # `subprocess.run` kills on timeout; do the same, group-wide, so a
            # timed-out probe does not keep the drive busy. Then re-raise so
            # callers' existing TimeoutExpired handling is unchanged.
            self._kill_group(proc)
            try:
                # **KEEP WHAT THE CHILD ALREADY SAID.** This second `communicate`
                # returns everything buffered before the timeout, and this code
                # used to discard it and re-raise — so a hung probe produced
                # `exit code: none` and *nothing captured*, which is what the
                # diagnostic record showed for the 120 s `cyanrip -I` hang on
                # 2026-08-10. The output existed. We threw it away.
                #
                # That is `CLAUDE.md`'s diagnostic-completeness rule, fourth
                # instance: "all three were facts we HAD and discarded, which is
                # worse than facts never obtained because the report looked
                # complete either way." A partial capture is often the whole
                # diagnosis — the last line before a drive wedges is the line that
                # says which sector it wedged on.
                #
                # `subprocess.run` does exactly this: it catches TimeoutExpired,
                # drains, and re-raises with the output attached. We were the only
                # path that did not, which is why swapping `run` for this class
                # silently lost the capture.
                late_stdout, late_stderr = proc.communicate(timeout=REAP_TIMEOUT_S)
                # typeshed types these `bytes | None` because it models only the
                # bytes-mode child; ours is `text=True`, so `communicate` really
                # returns `str` and CPython stores whatever it is given. Narrowed
                # here rather than weakened at the source: encoding the text back
                # to bytes to satisfy the annotation would make every reader of
                # the exception decode it again, and one of them would forget.
                timed_out.stdout = late_stdout  # type: ignore[assignment]  # text mode
                timed_out.stderr = late_stderr  # type: ignore[assignment]  # text mode
                if late_stdout or late_stderr:
                    log.warning(
                        "%s: timed out after %ss; keeping the %d character(s) it "
                        "had already written — see the diagnostic record",
                        self._name,
                        timeout,
                        len(late_stdout or "") + len(late_stderr or ""),
                    )
            except subprocess.TimeoutExpired:
                # Unreapable: the child never died, so there is nothing to drain
                # and `timed_out.stdout` stays as CPython left it. Absence here is
                # a real answer and must not be dressed up as an empty capture.
                log.error(
                    "%s: child unreapable after SIGKILL — leaked, probably stuck "
                    "in an uninterruptible drive ioctl; no output could be "
                    "recovered",
                    self._name,
                )
            raise
        finally:
            with self._lock:
                # Clear the slot ONLY if it still holds *our* child. Two runs can
                # overlap — the GUI supersedes an in-flight disc scan by starting a
                # second one — and the loser finishing later must not deregister the
                # winner. Without this identity check the second child becomes
                # unkillable and `cancel()` silently degrades to a no-op, which
                # defeats the entire point of the module. Found by audit immediately
                # after this module was written (2026-07-29): the fix's own new state
                # needed its own thinking, exactly as the pre-flight checklist asks.
                if self._proc is proc:
                    self._proc = None
                    self._cancel_requested = False
        return subprocess.CompletedProcess(
            args=argv, returncode=proc.returncode, stdout=stdout, stderr=stderr
        )
