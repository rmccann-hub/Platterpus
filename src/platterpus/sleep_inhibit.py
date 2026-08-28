"""Hold idle/sleep/lid suspend off for the lifetime of a long unattended run.

**Why this is Python and not shell any more.** The overnight acceptance run used
to be `docs/rig-scripts/platterpusovernight.sh`, which took this lock itself. The
maintainer's ruling was that the harness belongs *in* the program — *"this was
supposed to be a no cli program, not give me commands to use"*, *"make it all
verify and do it itself"* — so the lock moves here with it. The reasoning below is
inherited verbatim from that script; none of it was re-derived, and none of it
should be re-litigated without re-reading it.

**Why `systemd-inhibit` and not a settings change.** Changing the desktop's power
settings (a) persists after the run, silently leaving the machine awake forever,
and (b) needs somebody to remember to change it back — the handed-back step again.
`systemd-inhibit` holds the lock for the **lifetime of a child process** and drops
it the instant that child exits, including on a crash or a kill. Nothing to undo,
nothing to remember, and no state left behind if the run dies at 3 a.m.

**`idle:sleep:handle-lid-switch` is the exact set the run needs** — the idle timer,
an explicit suspend, and the lid. `handle-lid-switch` is included even on a desktop
because it costs nothing and the rig has been a laptop before. It deliberately does
**not** inhibit the screensaver: a blanked screen is harmless (the session keeps
running) and holding the display on all night for nobody is worse.

**PRESENT IS NOT THE SAME AS WORKING.** `systemd-inhibit` is installed on machines
where it cannot work, and it fails two different ways:

* *"Failed to connect to bus: No such file or directory"* — no session bus at all
  (an ssh login, a cron job, a container, a user unit without
  `DBUS_SESSION_BUS_ADDRESS`).
* *"Failed to inhibit: Access denied"* — a session bus exists but has no polkit
  privilege for `sleep`/`handle-lid-switch`. This is what a GitHub runner looks
  like, and it is the awkward middle case.

Either way, adopting the tool because the binary exists means the very first thing
run under it fails instantly — a night consumed with the real work never executed,
and (worse) reported as whatever the caller guesses a non-zero exit means. So the
capability is **PROBED**: run the real thing over `true` and adopt it only if that
actually worked.

**AND THE PROBE MUST ASK FOR EXACTLY WHAT THE RUN ASKS FOR.** The first probe in
the shell version asked for `--what=idle` while the run asked for all three, so it
tested a *weaker* capability than the one that matters; CI caught it on a runner
whose session could inhibit `idle` and not `sleep`. That is `CLAUDE.md`'s *"did I
verify this where it could have failed?"* — an invariant confirmed under conditions
weaker than the ones that matter has not been tested. Hence
:data:`INHIBIT_WHAT` is defined **once** and :meth:`SleepInhibitor._what_arg`
is the single place it becomes an argument, so the probe cannot drift from its
subject. `tests/test_sleep_inhibit.py` pins that by comparing the two *recorded*
argvs, not by reading the constant twice.

**A silent downgrade is unacceptable.** :meth:`SleepInhibitor.acquire` returns a
**tri-state** outcome — never a bool — because "not installed" and "installed but
refused" need different advice, and both need a sentence the caller can show a
person. A run that proceeds unprotected is fine; a run that proceeds unprotected
*without saying so* is how you spend a night and learn nothing.

**Threading.** :meth:`acquire` blocks for up to :data:`PROBE_TIMEOUT_S` on the
probe, so it must not be called on the Qt main thread (`CLAUDE.md`: never block the
GUI thread). :meth:`release` is bounded by construction and safe to call from a
teardown hook.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from dataclasses import dataclass
from typing import Final, Protocol

log = logging.getLogger(__name__)

#: The tool. Named once so a caller cannot spell it differently in a message than
#: we spell it in an argv.
INHIBIT_BINARY: Final[str] = "systemd-inhibit"

#: **THE ONE DEFINITION.** Read the module docstring before changing it, and note
#: that changing it here changes the probe and the real lock together — which is
#: the entire point. A second literal anywhere in this file is the bug this
#: constant exists to prevent.
INHIBIT_WHAT: Final[str] = "idle:sleep:handle-lid-switch"

#: `--who`, shown in `systemd-inhibit --list`. A person looking at that list at
#: 3 a.m. needs to know which program is holding their machine awake.
INHIBIT_WHO: Final[str] = "Platterpus"

#: `--why` for the throwaway probe, kept distinct from the real lock's so the two
#: are told apart in `--list` if a probe ever outlives its instant.
PROBE_WHY: Final[str] = "capability probe"

#: `--why` for the real lock. Overridable per caller; this is the harness default.
DEFAULT_WHY: Final[str] = "overnight acceptance run"

#: What the probe runs *under* the inhibitor. `true` exits 0 immediately, so a
#: non-zero exit is unambiguously the inhibitor's own refusal and never the
#: payload's.
PROBE_TRAILER: Final[tuple[str, ...]] = ("true",)

#: How long the held lock's child is asked to live. **Finite on purpose.** If we
#: ever leak this child (a hard `os._exit` on an abandoned-thread shutdown, say —
#: `platterpus.hard_exit` bypasses teardown by design) a `sleep infinity` would
#: keep the machine awake until reboot with nothing left to explain why. A week is
#: a huge margin over any overnight run and a bounded blast radius if we lose it.
LOCK_HOLD_SECONDS: Final[int] = 7 * 24 * 60 * 60

#: Probe budget. Generous: the failure modes above answer in milliseconds, but a
#: sick D-Bus can hang, and a hang here must not be mistaken for a refusal.
PROBE_TIMEOUT_S: Final[float] = 10.0

#: Grace between SIGTERM and the group SIGKILL in :meth:`SleepInhibitor.release`.
TERMINATE_GRACE_S: Final[float] = 5.0

#: How long to wait for a SIGKILLed child to be reaped before declaring it
#: unreapable. Short on purpose: SIGKILL has already been sent, so anything still
#: alive is in an uninterruptible kernel call where waiting does not help.
REAP_TIMEOUT_S: Final[float] = 5.0

#: Bounds on how much of the tool's own output reaches a user-visible sentence.
#: Head **and** tail, because a tool's fatal message is the *last* thing it prints
#: and a head-only cap drops exactly the line that explains the failure — while
#: still looking like a complete capture.
OUTPUT_HEAD_CHARS: Final[int] = 400
OUTPUT_TAIL_CHARS: Final[int] = 200

#: The three states. **Tri-state, never a bool** (`CLAUDE.md`'s `not_determined`
#: honesty): "the tool is missing" and "the tool refused" are different facts and
#: the user needs different advice for each.
STATE_HELD: Final[str] = "held"
STATE_UNAVAILABLE: Final[str] = "unavailable"
STATE_NOT_INSTALLED: Final[str] = "not_installed"
INHIBIT_STATES: Final[tuple[str, ...]] = (
    STATE_HELD,
    STATE_UNAVAILABLE,
    STATE_NOT_INSTALLED,
)

#: C0 controls (plus DEL) that must never reach a widget verbatim. Newline and tab
#: are kept: they are the only two that render as themselves.
_CONTROL_CHARS: Final[frozenset[str]] = frozenset(
    chr(code) for code in [*range(0x20), 0x7F] if chr(code) not in "\n\t"
)
_REPLACEMENT: Final[str] = "�"


def _bounded(text: str) -> str:
    """External text capped for display, with **every** elision counted and marked.

    Two obligations from `CLAUDE.md`'s inbound-seam rules, both of which have been
    got wrong here before:

    * *A silent truncation reads as completeness.* An unmarked cut is
      indistinguishable from a tool that fell silent, which is a different and more
      alarming fact. So the gap is stated **with a count**.
    * *Control characters and NULs are flagged.* This is the tool's own bytes going
      into a message a person reads; a NUL or a stray escape sequence in a widget
      is at best unreadable and at worst a terminal-control payload. They are
      replaced with U+FFFD and the substitution is counted too — replacing without
      saying so is the same silent-drop defect in a different coat.

    Bounding happens first so the per-character pass is over a bounded string.
    """
    stripped = text.strip()
    if len(stripped) > OUTPUT_HEAD_CHARS + OUTPUT_TAIL_CHARS:
        omitted = len(stripped) - OUTPUT_HEAD_CHARS - OUTPUT_TAIL_CHARS
        stripped = (
            stripped[:OUTPUT_HEAD_CHARS]
            + f" … [{omitted} character(s) omitted] … "
            + stripped[-OUTPUT_TAIL_CHARS:]
        )
    replaced = sum(1 for char in stripped if char in _CONTROL_CHARS)
    if replaced:
        stripped = "".join(
            _REPLACEMENT if char in _CONTROL_CHARS else char for char in stripped
        )
        stripped += f" [{replaced} control character(s) replaced]"
    return stripped


@dataclass(frozen=True)
class ProbeResult:
    """What one throwaway run of the inhibitor told us.

    ``output`` is the child's **complete** output with stderr merged in, because
    `CLAUDE.md`'s diagnostic-completeness rule wants everything the dependency said
    and `systemd-inhibit` puts its refusals on stderr. Merging rather than keeping
    two fields means no call site can capture one and drop the other.
    """

    returncode: int
    output: str


class InhibitedProcess(Protocol):
    """The part of :class:`subprocess.Popen` a held lock needs.

    Narrow on purpose: it is exactly what :meth:`SleepInhibitor.release` calls, so
    a test double is a handful of lines and cannot silently gain powers the real
    thing lacks. ``subprocess.Popen`` satisfies it structurally.
    """

    @property
    def pid(self) -> int: ...

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


class InhibitRunner(Protocol):
    """Every OS interaction this module performs, in one injectable seam.

    All three of these are here so a test never spawns a real process **and never
    signals a real process group** — a fake pid handed to a real ``os.killpg`` is a
    live grenade in a test suite, which is why the group kill is a seam method
    rather than a direct call from :meth:`SleepInhibitor.release`.
    """

    def probe(self, argv: list[str], *, timeout: float) -> ProbeResult:
        """Run `argv` to completion; return its exit code and merged output.

        May raise ``FileNotFoundError`` (binary absent), ``OSError`` or
        ``subprocess.SubprocessError`` (including a timeout); the caller handles
        all of them and never lets one escape.
        """
        ...

    def spawn(self, argv: list[str], *, start_new_session: bool) -> InhibitedProcess:
        """Start `argv` as a long-lived child and return the handle."""
        ...

    def kill_group(self, process: InhibitedProcess) -> None:
        """SIGKILL the child's whole process group, falling back to the child."""
        ...


class SubprocessInhibitRunner:
    """The production :class:`InhibitRunner`, backed by ``subprocess``."""

    def probe(self, argv: list[str], *, timeout: float) -> ProbeResult:
        # `subprocess.run` is correct *here* and forbidden for the lock below: the
        # probe is a one-shot with a timeout (which `run` enforces by killing the
        # child), and nothing needs to signal it from another thread. The lock is
        # the opposite on both counts.
        completed = subprocess.run(  # noqa: S603 — argv is built from our constants
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merged: see ProbeResult
            text=True,
            timeout=timeout,
            check=False,
        )
        return ProbeResult(
            returncode=completed.returncode, output=completed.stdout or ""
        )

    def spawn(self, argv: list[str], *, start_new_session: bool) -> InhibitedProcess:
        # **`start_new_session` is load-bearing, not hygiene** (`CLAUDE.md` rule 9):
        # it makes the child a process-group leader so one `killpg` reaches the
        # whole tree — and, crucially, so that a `killpg` does not signal *our own*
        # process group, i.e. the app.
        #
        # Output goes to DEVNULL rather than PIPE. We never read this child, and a
        # pipe nobody drains holds ~64 KiB before the writer blocks forever — the
        # exact deadlock `CLAUDE.md` warns about. The diagnostic value is not lost:
        # the probe that ran a moment earlier captured what the tool has to say.
        return subprocess.Popen(  # noqa: S603 — argv is built from our constants
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=start_new_session,
        )

    def kill_group(self, process: InhibitedProcess) -> None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except OSError:
            # The group may already be gone, or `getpgid` may race with exit.
            # Falling back to the single process is strictly better than giving up.
            try:
                process.kill()
            except OSError:
                pass


@dataclass(frozen=True)
class InhibitOutcome:
    """The tri-state answer to "is suspend held off?", with its reason.

    ``what`` carries the exact `--what` value that was asked for, so a report can
    **prove** the probe and the lock agreed rather than asserting it — the drift
    described in the module docstring was invisible precisely because nothing
    recorded which capability had been tested.
    """

    state: str
    detail: str
    what: str

    def __post_init__(self) -> None:
        # A tripwire, not input validation: every outcome in this module is built
        # from static text, so an empty detail or an unknown state means a future
        # edit broke the promise that a caller always has something to show. Better
        # to fail loudly in a test than to hand the user a blank explanation.
        if self.state not in INHIBIT_STATES:
            raise ValueError(f"unknown inhibit state: {self.state!r}")
        if not self.detail.strip():
            raise ValueError("InhibitOutcome.detail must never be empty")

    @property
    def is_held(self) -> bool:
        """Convenience for callers that only branch. The three states remain the
        record — this is deliberately *not* the type of :attr:`state`."""
        return self.state == STATE_HELD


class SleepInhibitor:
    """Takes, holds and releases the idle/sleep/lid inhibitor for one run.

    One instance per logical run. Reusable: a released inhibitor can be acquired
    again, and a failed :meth:`acquire` can be retried (a session bus may have
    appeared since).
    """

    def __init__(
        self,
        *,
        runner: InhibitRunner | None = None,
        what: str = INHIBIT_WHAT,
        why: str = DEFAULT_WHY,
    ) -> None:
        self._runner: InhibitRunner = runner or SubprocessInhibitRunner()
        self._what: str = what
        self._why: str = why
        self._process: InhibitedProcess | None = None
        self._outcome: InhibitOutcome | None = None
        self._lock: threading.Lock = threading.Lock()
        # A release that lands *during* an acquire must not be lost. The child is
        # spawned outside the lock (the probe before it can take seconds, and a
        # teardown must not queue behind that), so `release()` can run when there
        # is nothing registered yet and would otherwise silently leave the machine
        # awake. Same watermark shape as `killable.KillableCommand`: each acquire
        # takes a sequence number before it spawns, `release()` records the highest
        # issued so far, and the just-spawned child re-checks it at registration.
        self._issued: int = 0
        self._released_through: int = 0

    # -- introspection ----------------------------------------------------

    @property
    def held(self) -> bool:
        """Whether a lock child is **actually alive** right now.

        Deliberately not a stored flag. `poll()` is free and a bookkeeping bool
        would keep claiming the machine is protected after the child died — which
        is the silent downgrade this module exists to prevent, arriving by the one
        route the tri-state outcome cannot see.
        """
        with self._lock:
            process = self._process
        if process is None:
            return False
        try:
            return process.poll() is None
        except OSError:  # a handle that has become unusable is not a held lock
            return False

    @property
    def outcome(self) -> InhibitOutcome | None:
        """The last :meth:`acquire` result, for a report. ``None`` before the first."""
        return self._outcome

    @property
    def what(self) -> str:
        """The `--what` capability set this instance asks for, probe and lock alike."""
        return self._what

    # -- argv builders ----------------------------------------------------

    def _what_arg(self) -> str:
        """The `--what=` argument. **The single place it is spelled.**

        Both :meth:`_probe_argv` and :meth:`_lock_argv` call this, which is what
        makes "the probe asks for exactly what the run asks for" a property of the
        code rather than of whoever last edited it.
        """
        return f"--what={self._what}"

    def _probe_argv(self) -> list[str]:
        return [
            INHIBIT_BINARY,
            self._what_arg(),
            f"--who={INHIBIT_WHO}",
            f"--why={PROBE_WHY}",
            "--mode=block",
            *PROBE_TRAILER,
        ]

    def _lock_argv(self) -> list[str]:
        return [
            INHIBIT_BINARY,
            self._what_arg(),
            f"--who={INHIBIT_WHO}",
            f"--why={self._why}",
            "--mode=block",
            "sleep",
            str(LOCK_HOLD_SECONDS),
        ]

    # -- acquire ----------------------------------------------------------

    def acquire(self) -> InhibitOutcome:
        """Probe the capability and, only if that worked, take the real lock.

        **Never raises.** Every failure becomes an outcome with a sentence the
        caller can show, because the one thing worse than an unprotected run is an
        unprotected run nobody was told about.
        """
        if self.held and self._outcome is not None:
            return self._outcome

        probe = self._run_probe()
        if probe is not None:
            return probe
        return self._take_lock()

    def _run_probe(self) -> InhibitOutcome | None:
        """Run the capability probe. Returns the refusal outcome, or ``None`` if it
        passed and the caller should go on to take the real lock."""
        argv = self._probe_argv()
        try:
            result = self._runner.probe(argv, timeout=PROBE_TIMEOUT_S)
        except FileNotFoundError:
            # The one signal that means *absent* rather than *refused*. Everything
            # else the tool can do to us is a refusal of some kind.
            return self._settle(
                STATE_NOT_INSTALLED,
                f"`{INHIBIT_BINARY}` is not installed, so idle, sleep and lid "
                f"suspend could NOT be held off ({self._what}). This machine may "
                f"suspend part-way through the run — disable sleep by hand if you "
                f"can.",
            )
        except (OSError, subprocess.SubprocessError) as exc:
            # A timeout lands here too, and it is a refusal we must not dress up as
            # anything else: a hung D-Bus is not a working lock.
            return self._settle(
                STATE_UNAVAILABLE,
                f"`{INHIBIT_BINARY}` could not be run to test the lock this run "
                f"needs ({self._what}): {_bounded(f'{type(exc).__name__}: {exc}')}. "
                f"The run will proceed WITHOUT the lock, so this machine may "
                f"suspend part-way through.",
            )

        if result.returncode != 0:
            said = _bounded(result.output)
            # Mark the silence rather than trailing off. "It printed nothing" is a
            # fact about the tool; an empty quotation is a fact about nothing.
            quoted = f"It said: {said}" if said else "It printed nothing."
            return self._settle(
                STATE_UNAVAILABLE,
                f"`{INHIBIT_BINARY}` is installed but could not take the lock this "
                f"run needs ({self._what}) — the probe exited {result.returncode}. "
                f"Usually there is no session bus (an ssh or cron invocation), or "
                f"this session has no polkit privilege for sleep/lid. {quoted} The "
                f"run will proceed WITHOUT the lock, so this machine may suspend "
                f"part-way through.",
            )
        return None

    def _take_lock(self) -> InhibitOutcome:
        """Spawn the long-lived child that actually holds the lock."""
        with self._lock:
            self._issued += 1
            sequence = self._issued
        argv = self._lock_argv()
        try:
            # `Popen`, never `subprocess.run`: `run` constructs the child
            # internally and never hands it out, so there would be nothing for
            # `release()` to signal (`CLAUDE.md` rule 9).
            process = self._runner.spawn(argv, start_new_session=True)
        except FileNotFoundError:
            # Vanished between the probe and now. Rare, but reporting it as a
            # refusal would send the user looking for a permission problem.
            return self._settle(
                STATE_NOT_INSTALLED,
                f"`{INHIBIT_BINARY}` passed the capability probe and then could not "
                f"be found ({self._what}). The run will proceed WITHOUT the lock, "
                f"so this machine may suspend part-way through.",
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return self._settle(
                STATE_UNAVAILABLE,
                f"`{INHIBIT_BINARY}` passed the capability probe but the lock "
                f"itself could not be started ({self._what}): "
                f"{_bounded(f'{type(exc).__name__}: {exc}')}. The run will proceed "
                f"WITHOUT the lock, so this machine may suspend part-way through.",
            )

        with self._lock:
            released_during_startup = sequence <= self._released_through
            if not released_during_startup:
                self._process = process
        if released_during_startup:
            # A release ran while we were spawning. Kill what we just started, or
            # the lock outlives the run that asked for it.
            log.info("sleep inhibitor: released during acquire; killing the child")
            self._runner.kill_group(process)
            return self._settle(
                STATE_UNAVAILABLE,
                f"The sleep lock ({self._what}) was released while it was being "
                f"taken, so it is NOT held. This machine may suspend.",
            )

        return self._settle(
            STATE_HELD,
            f"Idle, sleep and lid suspend are held off for this run ({self._what}). "
            f"The lock is released automatically when the run ends — there is "
            f"nothing to undo.",
        )

    def _settle(self, state: str, detail: str) -> InhibitOutcome:
        """Record and log an outcome. One place, so nothing is reported unlogged."""
        outcome = InhibitOutcome(state=state, detail=detail, what=self._what)
        self._outcome = outcome
        if state == STATE_HELD:
            log.info("sleep inhibitor: %s — %s", state, detail)
        else:
            # A downgrade is a warning even though the run continues: it is the
            # thing a morning post-mortem needs to find in the log file.
            log.warning("sleep inhibitor: %s — %s", state, detail)
        return outcome

    # -- release ----------------------------------------------------------

    def release(self) -> None:
        """Drop the lock. Bounded, never raises, and safe to call twice or never.

        SIGTERM, a grace period, then a **group** SIGKILL, then a bounded wait —
        and if the child is still not reapable, say so and return rather than
        blocking a shutdown forever (`CLAUDE.md`: a reader wedged in a drive ioctl
        is in uninterruptible sleep where even SIGKILL does not land).
        """
        with self._lock:
            # Raise the watermark whether or not anything is registered, so a
            # release racing an in-flight acquire is honoured when the child lands.
            self._released_through = self._issued
            process = self._process
            self._process = None
        if process is None:
            return

        try:
            if process.poll() is not None:
                log.info("sleep inhibitor: lock child had already exited")
                return
            process.terminate()
            if self._wait_bounded(process, TERMINATE_GRACE_S):
                log.info("sleep inhibitor: lock released (child terminated)")
                return
            log.warning(
                "sleep inhibitor: lock child ignored SIGTERM for %ss; "
                "escalating to a group SIGKILL",
                TERMINATE_GRACE_S,
            )
            self._runner.kill_group(process)
            if self._wait_bounded(process, REAP_TIMEOUT_S):
                log.info("sleep inhibitor: lock released (child killed)")
                return
            # Tri-state honesty again: an unreapable child is a real answer and
            # must be reported as one, not silently treated as released.
            log.error(
                "sleep inhibitor: lock child is UNREAPABLE after a group SIGKILL — "
                "abandoned; the inhibitor may still be held until it dies or the "
                "machine reboots",
            )
        except OSError as exc:
            # The handle can become unusable under us; that is not a reason to
            # break a caller's teardown.
            log.warning("sleep inhibitor: releasing the lock failed: %s", exc)

    def _wait_bounded(self, process: InhibitedProcess, timeout: float) -> bool:
        """Wait at most `timeout` seconds for `process`. True if it was reaped.

        Every wait in this module goes through here so none of them can be
        unbounded — ``wait(None)`` means *forever*, which on a teardown path is a
        frozen window with no upper bound.
        """
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return False
        return True
