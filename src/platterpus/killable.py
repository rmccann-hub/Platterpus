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
* **The cancel/startup race is closed, and scoped to one run.** A cancel arriving
  between `Popen` and registration would otherwise find nothing registered and be
  silently dropped — the user presses Cancel and nothing happens. So each run takes
  a sequence number before it spawns, `cancel()` records the highest issued so far,
  and the check is re-run right after registering. The scoping is the half that was
  missing: a slot-wide flag let a cancel aimed at one probe kill the *replacement*
  the GUI started immediately afterwards, which is a rescan that never completes.
* **Every live child is tracked, not just the newest.** Two runs through one slot
  can overlap (a superseded disc probe still unwinding while its replacement
  starts), and a slot that remembered only the most recent child lost the older
  one the moment the newer one finished: ``cancel()`` then found nothing to kill
  while the older reader went on holding the drive (the owner's rig, 2026-11-05,
  two ``cyanrip -I`` on one drive until both timed out at 120 s). So the slot keeps
  each live child under its own sequence number, and a cancel reaches all of them.
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

The one writer routed through here is the CTDB repair (:class:`KillableJob`,
2026-11-05), and a hard kill is safe for it by construction: every ``flac`` and
``metaflac`` that writes, writes only to a hidden candidate file beside the
original (``ctdb/repair_commit.candidate_path``), which the repair deletes on
any failure. The original is touched only by the commit, a link and a rename in
Python, with no child process to kill.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from pathlib import Path

from platterpus.container_gate import FIRST_ENTRY

log = logging.getLogger(__name__)

# How long to wait for a killed child to be reaped before giving up on it. Short
# on purpose: SIGKILL has already been sent, so anything still alive is stuck in an
# uninterruptible kernel call (a wedged drive ioctl) where waiting does not help.
REAP_TIMEOUT_S: float = 5.0


class CancelledRun(subprocess.CompletedProcess[str]):
    """A run that ended because its own slot's :meth:`KillableCommand.cancel` killed it.

    Returned in place of a plain ``CompletedProcess``, with the same fields, so a
    caller that reads only ``returncode`` behaves as before. What it adds is who
    ended the run: its ``-9`` is the SIGKILL Platterpus sent, not the tool's answer,
    so no caller may report it as the tool failing (:func:`was_cancelled`).

    Why (the round-29 Full run, 2026-09-28): the operator pressed Rescan, the rescan
    superseded the disc probe in flight, and ``cyanrip exited -9`` was recorded as a
    dependency failure, a warning that every rip report of that session carried.
    """


class CancelledBytesRun(subprocess.CompletedProcess[bytes]):
    """:class:`CancelledRun` for a binary run (:meth:`KillableCommand.run_bytes`).

    A second class rather than a generic one because ``CompletedProcess`` is
    generic only to the type checker; at run time a binary run and a text run
    are the same class, and :func:`was_cancelled` must recognise both.
    """


def was_cancelled(proc: object) -> bool:
    """Whether ``proc`` is a run that its own slot's ``cancel()`` ended."""
    return isinstance(proc, CancelledRun | CancelledBytesRun)


class KillableCommand:
    """One named slot for one logical operation, killable from any thread.

    Each instance models a single logical operation the GUI can have in flight (the
    disc-info probe, the ripper version probe, the cache probe, …), which keeps
    `cancel()` unambiguous about WHAT it stops: create one per operation at module
    scope and reuse it, and never share one slot between two operations, because a
    cancel aimed at one would reach the other.

    **One operation can still have more than one child alive at once**, and the
    slot must not pretend otherwise. The GUI supersedes an in-flight disc probe by
    starting a new one, and the old child takes a moment to die. So the slot keeps
    every live child it spawned, keyed by its run's sequence number, and
    :meth:`cancel` SIGKILLs every one its watermark covers. It used to keep only
    the newest, and an older child it had forgotten could not be killed at all.
    """

    def __init__(self, name: str) -> None:
        self._name: str = name
        self._lock: threading.Lock = threading.Lock()
        # EVERY live child this slot spawned, keyed by its run's sequence number
        # (below). Text-mode children (`run`) and binary ones (`run_bytes`, the
        # CTDB repair's `flac` pipes) share it.
        #
        # **A dict, not a single `_proc`, and the single one was a defect.** Two
        # runs through one slot can overlap: the GUI supersedes a disc probe by
        # starting another, and the module-level `rip_backend.INFO_PROBE` served
        # the disc probe and the version probe both. With one field, the later
        # run's registration overwrote the earlier child, the later run's
        # deregistration then emptied the field, and the earlier child was left
        # running where no `cancel()` could find it: no log line, no kill, though
        # the watermark covered its run. Reproduced 2026-11-05 with two `sleep`s
        # (the earlier one ran its full 8 s after a cancel), and seen on the
        # owner's rig the same day as two `cyanrip -I` on one drive until both
        # timed out. Keyed by sequence number, each run adds and removes only its
        # own entry, so no run can hide or evict another.
        self._live: dict[int, subprocess.Popen[str] | subprocess.Popen[bytes]] = {}
        # **A cancel is scoped to a RUN, not to this slot.**
        #
        # `_issued` counts runs; each `run()` takes its own sequence number
        # BEFORE it spawns. `cancel()` records the highest sequence issued so far,
        # so it cancels the run that is in flight (or the one whose `Popen` has
        # not finished registering yet) and has NO authority over any run started
        # afterwards.
        #
        # Both halves are load-bearing and the first version had only one. A
        # single sticky boolean honoured a cancel that landed between `Popen` and
        # registration — necessary, and pinned by
        # `test_a_cancel_that_lands_during_startup_is_not_lost` — but it was a
        # property of the *slot*, and the only thing that cleared it was the
        # cancelled run's own `finally`, which unwinds on another thread after a
        # SIGKILL. "Rescan disc" cancels the in-flight probe and starts the
        # replacement immediately (`stop_thread(..., wait_ms=0)`), so the
        # replacement could register while the flag was still set for its
        # predecessor and **kill itself at birth** — measured `returncode -9`
        # with empty output, which is exactly the signature the 2026-08-19 rig run
        # recorded for a dead rescan.
        #
        # A watermark keeps the startup-race guarantee (a run issued before the
        # cancel is still cancelled, however late it registers) while making the
        # scoping explicit rather than temporal.
        self._issued: int = 0
        self._cancel_through: int = 0

    @property
    def name(self) -> str:
        return self._name

    def is_running(self) -> bool:
        """Whether any child is currently registered. For diagnostics and tests."""
        with self._lock:
            return bool(self._live)

    def live_count(self) -> int:
        """How many children are registered right now. For diagnostics and tests."""
        with self._lock:
            return len(self._live)

    def cancel(self) -> None:
        """SIGKILL the process group of every covered live child. Thread-safe.

        Non-blocking, safe to call when nothing is running, and safe to call
        twice. Raises the watermark either way, so a child that was *issued*
        before this call is killed as soon as it appears, and a run issued
        afterwards is untouched.

        **Every** live child the watermark covers is killed, not only the newest:
        an operation the GUI superseded can still have its older child alive
        beside the replacement's, and the older one is the one holding the drive.
        """
        with self._lock:
            self._cancel_through = self._issued
            # Snapshot under the lock, signal outside it: `_kill_group` makes
            # system calls, and a run registering or deregistering on another
            # thread must not wait behind them.
            victims = [
                proc for seq, proc in self._live.items() if self._covered_locked(seq)
            ]
            through = self._cancel_through
        if not victims:
            # SAID, not silent. An absence in the log is a fact about the logger
            # first (CLAUDE.md), and the 2026-11-05 rig log had no line here at
            # all, so nobody could tell "nothing was running" from "something was
            # running and we lost it". A run issued but not yet registered is
            # still covered, and is killed as it registers (`_register`).
            log.info(
                "%s: cancel requested with no child registered; any run issued "
                "through #%d is killed as it starts",
                self._name,
                through,
            )
            return
        log.info(
            "%s: cancelling %d live child(ren) (SIGKILL to each process group)",
            self._name,
            len(victims),
        )
        for proc in victims:
            self._kill_group(proc)

    def _kill_group(
        self, proc: subprocess.Popen[str] | subprocess.Popen[bytes]
    ) -> None:
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
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run `argv` to completion, capturing text output. Cancellable.

        Returns a `CompletedProcess` so this is a drop-in for `subprocess.run` at
        the call sites. Raises `FileNotFoundError` (binary missing) and
        `subprocess.TimeoutExpired` (child killed first) exactly as `run` does, so
        existing error handling keeps working unchanged.

        `stdin_devnull` defaults True because every current caller must not inherit
        the parent's stdin — a tool that reads stdin would otherwise block forever
        on a GUI process with no terminal.

        `cwd` is the folder the child starts in; ``None`` keeps ours, which is what
        every probe that writes no file wants. A caller whose child writes to a
        RELATIVE path must pass one — without it, where the files land is decided
        by whichever folder the app happened to be launched from (the ui-script
        `cyanrip` verb's `-D`, 2026-09-28). A `cwd` that cannot be entered raises
        from `Popen` with the folder as ``exc.filename``, which is how a caller
        tells it apart from a missing binary.
        """
        # Claim a sequence number BEFORE spawning, so a cancel racing this call
        # can tell "the run that is starting" from "a run that starts later".
        with self._lock:
            self._issued += 1
            seq = self._issued
        # The first container command of the session runs alone
        # (`container_gate`); the wait ends early on this run's own cancel.
        first = FIRST_ENTRY.claim(
            argv[0] if argv else "",
            name=self._name,
            should_stop=lambda: self._covered_by_cancel(seq),
        )
        try:
            return self._spawn_and_wait(
                argv, seq, timeout=timeout, stdin_devnull=stdin_devnull, cwd=cwd
            )
        finally:
            if first:
                FIRST_ENTRY.release()

    def _covered_by_cancel(self, seq: int) -> bool:
        """Whether a cancel has been issued that covers run ``seq``."""
        with self._lock:
            return self._covered_locked(seq)

    def _covered_locked(self, seq: int) -> bool:
        """:meth:`_covered_by_cancel` for a caller already holding ``_lock``.

        The one place the coverage rule is written, so a subclass that widens it
        (:class:`KillableJob`: a cancel covers every later run too) changes the
        startup check, the registration check and the "ended by our cancel"
        check together rather than one of the three.
        """
        return seq <= self._cancel_through

    def _register(
        self, proc: subprocess.Popen[str] | subprocess.Popen[bytes], seq: int
    ) -> bool:
        """Add run ``seq``'s child to the slot; True when a cancel already covers it.

        Adds, never replaces: another run's child stays registered beside this
        one, so a cancel can still reach it (see ``_live`` in ``__init__``).
        """
        with self._lock:
            self._live[seq] = proc
            covered = self._covered_locked(seq)
        if covered:
            # The cancel landed before this child existed (between the sequence
            # number and `Popen`, or while the run waited at the container gate).
            # Logged because the kill that follows is otherwise the one kill this
            # module makes without a line saying so.
            log.info(
                "%s: run #%d was cancelled before it started; killing it at birth",
                self._name,
                seq,
            )
        return covered

    def _deregister(
        self, proc: subprocess.Popen[str] | subprocess.Popen[bytes], seq: int
    ) -> bool:
        """Remove run ``seq``'s own entry; True when our cancel ended that run.

        **Only its own entry.** Two runs can overlap, and the one finishing first
        must not take the other's child out of the slot: that would leave a live
        child no `cancel()` can reach, which defeats the whole module. Keyed by
        sequence number, the run removes exactly what it added. (The first
        version cleared the slot unconditionally and stranded the NEWER child,
        audit 2026-07-29; the second kept one field with an identity check and
        stranded the OLDER one, rig 2026-11-05. A dict has neither failure.)

        The cancel watermark is NOT reset here. It is a high-water mark over
        issued sequence numbers, so it excludes every later run by construction:
        there is nothing to clear, and clearing it was what made the flag's
        lifetime depend on which thread unwound first (see ``__init__``).

        "Ended by our cancel" needs BOTH a covering cancel and a SIGKILL exit
        status. A child that exited on its own just before the kill landed keeps
        its own exit status, and so does a -9 nobody here sent (the kernel's OOM
        killer), because no cancel covered it.
        """
        with self._lock:
            if self._live.get(seq) is proc:
                del self._live[seq]
            return self._covered_locked(seq) and proc.returncode == -signal.SIGKILL

    def run_bytes(
        self, argv: list[str], *, stdin: bytes | None, timeout: float
    ) -> subprocess.CompletedProcess[bytes]:
        """:meth:`run` for a binary child: bytes in on stdin, bytes out. Cancellable.

        **Why a second entry point and not a flag on** :meth:`run`: the CTDB
        repair pipes raw PCM through ``flac`` in both directions (its decode
        writes the audio to stdout, its encode reads it from stdin), which a
        text-mode child would corrupt. Everything else is the same contract,
        through the same helpers: a sequence number claimed before the spawn,
        the startup-race check, the process group (``start_new_session=True``),
        a kill on timeout that keeps what the child had already written, and a
        :class:`CancelledBytesRun` when this slot's own cancel ended the run.

        ``stdin`` is the child's whole input, or ``None`` for ``/dev/null``.
        Raises ``FileNotFoundError`` and ``subprocess.TimeoutExpired`` exactly as
        ``subprocess.run`` does.
        """
        with self._lock:
            self._issued += 1
            seq = self._issued
        first = FIRST_ENTRY.claim(
            argv[0] if argv else "",
            name=self._name,
            should_stop=lambda: self._covered_by_cancel(seq),
        )
        try:
            return self._spawn_and_wait_bytes(argv, seq, stdin=stdin, timeout=timeout)
        finally:
            if first:
                FIRST_ENTRY.release()

    def _spawn_and_wait_bytes(
        self, argv: list[str], seq: int, *, stdin: bytes | None, timeout: float
    ) -> subprocess.CompletedProcess[bytes]:
        """The body of :meth:`run_bytes`; the binary twin of :meth:`_spawn_and_wait`."""
        proc = subprocess.Popen(  # noqa: S603 — callers pass a resolved binary
            argv,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # see the module docstring — load-bearing
        )
        if self._register(proc, seq):
            self._kill_group(proc)
        try:
            # A child killed during startup closes its stdin; `communicate` swallows
            # the broken pipe that writing to it would raise (CPython's
            # `_stdin_write`), so a cancelled encode ends here, not in an exception.
            stdout, stderr = proc.communicate(input=stdin, timeout=timeout)
        except subprocess.TimeoutExpired as timed_out:
            self._kill_group(proc)
            try:
                # Keep what it already said, as `_spawn_and_wait` does and why.
                late_stdout, late_stderr = proc.communicate(timeout=REAP_TIMEOUT_S)
                timed_out.stdout = late_stdout
                timed_out.stderr = late_stderr
            except subprocess.TimeoutExpired:
                log.error(
                    "%s: child unreapable after SIGKILL — leaked; no output could "
                    "be recovered",
                    self._name,
                )
            raise
        finally:
            ended_by_our_cancel = self._deregister(proc, seq)
        if ended_by_our_cancel:
            return CancelledBytesRun(
                args=argv, returncode=proc.returncode, stdout=stdout, stderr=stderr
            )
        return subprocess.CompletedProcess(
            args=argv, returncode=proc.returncode, stdout=stdout, stderr=stderr
        )

    def _spawn_and_wait(
        self,
        argv: list[str],
        seq: int,
        *,
        timeout: float,
        stdin_devnull: bool,
        cwd: Path | None,
    ) -> subprocess.CompletedProcess[str]:
        """Spawn run ``seq`` and wait for it; the body of :meth:`run`."""
        proc = subprocess.Popen(  # noqa: S603 — callers pass a resolved binary
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL if stdin_devnull else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,  # see the module docstring — load-bearing
        )
        if self._register(proc, seq):
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
            # Remove ONLY this run's own child, and decide whether our cancel
            # ended it: the one implementation of both, shared with the binary
            # twin (`_deregister` says why each half is the way it is).
            ended_by_our_cancel = self._deregister(proc, seq)
        if ended_by_our_cancel:
            return CancelledRun(
                args=argv, returncode=proc.returncode, stdout=stdout, stderr=stderr
            )
        return subprocess.CompletedProcess(
            args=argv, returncode=proc.returncode, stdout=stdout, stderr=stderr
        )


def _tool(argv: list[str]) -> str:
    """The program an argv runs, for a log line: its first element, whole."""
    return argv[0] if argv else "(no program)"


class KillableJob(KillableCommand):
    """A :class:`KillableCommand` for ONE job of several runs: a cancel ends the job.

    **Why a second shape.** A :class:`KillableCommand` slot is shared by
    operations the GUI restarts (a rescan cancels the probe in flight and starts
    another at once), so its cancel deliberately has no authority over a run
    issued afterwards. The CTDB repair is the opposite case: one job that runs
    ``flac`` and ``metaflac`` a dozen times in a row, decoding, encoding and
    decoding again. A cancel that landed between two of those runs would find
    nothing to kill, and the job would carry on with the next one: a ``cancel()``
    that does not stop the work, which ``CLAUDE.md`` rule 9 forbids shipping.

    So here a cancel covers the run in flight AND every run after it: a later
    :meth:`run` or :meth:`run_bytes` returns a cancelled result at once, without
    spawning anything. Create one per job; never reuse one after it is cancelled.
    The coverage rule is widened in :meth:`_covered_locked`, the one place it is
    written, so the startup race stays closed for the widened rule too (the flag
    is set BEFORE the lock is taken, so either the registering run sees it, or
    ``cancel()`` sees the registered child).
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._job_cancelled: threading.Event = threading.Event()

    @property
    def cancelled(self) -> bool:
        """Whether :meth:`cancel` has been called on this job."""
        return self._job_cancelled.is_set()

    def cancel(self) -> None:
        """Kill the run in flight and refuse every later one. Thread-safe."""
        self._job_cancelled.set()
        super().cancel()

    def _covered_locked(self, seq: int) -> bool:
        return self._job_cancelled.is_set() or super()._covered_locked(seq)

    def run(
        self,
        argv: list[str],
        *,
        timeout: float,
        stdin_devnull: bool = True,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """:meth:`KillableCommand.run`, or a cancelled result once the job is cancelled."""
        if self._job_cancelled.is_set():
            log.info("%s: cancelled, so %s is not started", self._name, _tool(argv))
            return CancelledRun(
                args=argv, returncode=-signal.SIGKILL, stdout="", stderr=""
            )
        return super().run(argv, timeout=timeout, stdin_devnull=stdin_devnull, cwd=cwd)

    def run_bytes(
        self, argv: list[str], *, stdin: bytes | None, timeout: float
    ) -> subprocess.CompletedProcess[bytes]:
        """:meth:`KillableCommand.run_bytes`, or a cancelled result once cancelled."""
        if self._job_cancelled.is_set():
            log.info("%s: cancelled, so %s is not started", self._name, _tool(argv))
            return CancelledBytesRun(
                args=argv, returncode=-signal.SIGKILL, stdout=b"", stderr=b""
            )
        return super().run_bytes(argv, stdin=stdin, timeout=timeout)
