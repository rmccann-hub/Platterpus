"""Force-stop the optical drive when a cancelled rip won't let go.

Why this exists: a rip runs as `~/.local/bin/cyanrip` (host wrapper) → podman
→ **cyanrip inside the `ripping` container**, which reads the disc directly.
Cancelling kills the host-side wrapper, but podman doesn't forward the signal
into the container, so the in-container reader keeps the drive spinning —
sometimes for minutes (real-user reports, 2026-05/06).

Hard-won facts (2026-06-01, real hardware; some date from before cyanrip but
the mechanics still apply):

  * **Kill the process that actually holds the drive.** cyanrip reads the disc
    itself (libcdio, no child process), so killing `cyanrip` by name stops it
    (real-user report, 2026-06-27). The ripper older versions drove was an
    *orchestrator* that respawned a separate reader, and its kill path stayed
    here as an inert seam until 2026-09-24, when it was removed: it matched a
    program Platterpus no longer launches, and a `pkill -f` pattern with nothing
    to kill is a risk with no benefit.
  * On rootless podman/Distrobox (the Bazzite target) the in-container
    processes are **host-visible**, so a host-side `pkill`/`fuser` reaches
    them — no `distrobox enter` needed in the normal case.
  * **Never use `pkill -f` with a bare tool name or with the reader names.**
    `-f` matches the full command line, so it also matches the GUI's own
    "platterpus" command line (killing the app) and the `distrobox enter …`
    wrapper / the pkill's own command line (self-kill). Match readers by
    process *name* (no `-f`).
  * The drive ignores the physical eject button while a read holds the device,
    which is why pressing eject by hand doesn't stop the spin — and why a
    software `eject` only works *after* the holder is killed.

The in-container `distrobox enter …` fallback (used only when the host can't
see the processes) calls *into* the `ripping` container, which CLAUDE.md
Critical Rule #3 normally forbids. This is a **deliberate, user-approved
exception (2026-05-31)**, scoped strictly to *force-stopping a cancelled rip*.
Ripping itself still goes through `~/.local/bin/cyanrip`.

Everything here is best-effort and synchronous; the caller runs it off the GUI
thread (it can block for the subprocess timeout). The `runner` is injectable so
tests never touch a real drive or container.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from collections.abc import Callable
from typing import Final

from platterpus import diagnostics
from platterpus.tool_paths import exported_tools_dir, resolve_tool

log = logging.getLogger(__name__)

# The Distrobox container the ripper lives in (README/setup-host default).
DEFAULT_CONTAINER: str = "ripping"

# How long the GUI waits after a cancel before force-stopping whatever still
# holds the drive.
#
# **It lives here rather than in the UI module that arms the timer**, because a
# second reader now depends on it: the rip worker waits for the ripper to finish
# writing its log, and that wait is only useful if it outlasts this countdown —
# the in-container reader typically writes its completion footer *because* this
# rescue fires (measured 2026-09-09: rescue at +4.9 s, footer at +6.6 s). Two
# expressions of one number is how those two silently stopped agreeing; raising
# this countdown now lengthens the wait that depends on it, in one edit.
FORCE_STOP_COUNTDOWN_S: float = 5.0

# The in-container ripper/reader process names, matched against the process
# *name* (pkill default, NOT `-f`; `-f` would self-match the wrapper/pkill
# command line). The cd-paranoia cache probe and cdrdao are separate readers;
# **cyanrip is its own reader** (libcdio, no child process), so it has to be
# killed by its own name — otherwise cancelling a cyanrip rip killed only the host wrapper and
# the in-container cyanrip kept ripping the disc (real-user report, 2026-06-27).
_READER_NAMES: str = "cdparanoia|cd-paranoia|cdrdao|cyanrip"

# A runner takes an argv list and returns something with a `.returncode`.
Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

# When the GUI is launched from a desktop icon (not a shell), PATH can be
# minimal and miss ~/.local/bin or even /usr/bin. Resolve these tools to an
# absolute path so the force-stop doesn't silently no-op.
#
# THE SEARCH IS `tool_paths.find_tool`'s, and the DIRECTORIES are this module's
# decision. The force-stop tools must be the HOST's: Critical rule #3's one
# exception kills the reader device-scoped on the host first, and `~/.local/bin`
# is where distrobox-export puts CONTAINER tools. So the host tools' lists leave it
# out on purpose, `_host_tool` excludes it from PATH as well (PATH is searched
# first, and a login session puts it there), and only `distrobox`, which is a host
# tool that lives there when installed per user, searches it.
# `tests/test_tool_paths.py` holds that split, by running the lookup.
_HOST_TOOL_DIRS_PKILL: tuple[str, ...] = ("/usr/bin", "/bin")
_HOST_TOOL_DIRS_FUSER: tuple[str, ...] = ("/usr/bin", "/bin", "/usr/sbin")
_HOST_TOOL_DIRS_EJECT: tuple[str, ...] = ("/usr/bin", "/usr/sbin", "/sbin")
_DISTROBOX_DIRS: tuple[str, ...] = (
    os.path.expanduser("~/.local/bin"),
    "/usr/bin",
    "/usr/local/bin",
)


def _host_tool(name: str, dirs: tuple[str, ...]) -> str:
    """``name`` as the HOST has it: PATH and ``dirs``, never the container exports.

    If the host has none, the answer is its path in ``dirs[0]``, so running it
    fails as "not found" and the force-stop moves on to the in-container step,
    which is the order rule #3's exception allows.
    """
    return resolve_tool(name, dirs, exclude_dirs=(exported_tools_dir(),))


# Per-command ceiling for the ordinary (off-GUI-thread) callers, where blocking
# is fine and we would rather wait than give up on a wedged drive.
_STEP_TIMEOUT_S: float = 20.0


def _run_bounded(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    """Run a command with an explicit per-command timeout, **capturing** its output.

    Never inherits stdin, so a `distrobox enter` can't block waiting on a TTY.
    Split out from :func:`_default_runner` purely so a caller that must bound the
    *whole sequence* can supply a shrinking timeout — see :func:`budgeted_runner`.

    **stderr used to be `DEVNULL`**, which destroyed the tool's message at the
    source: `eject`'s own explanation ("Device busy", "not a mountpoint") could not
    be recovered by any caller, however careful, and the rip pane went on reading
    *"Rip complete — ejecting the disc…"* while the tray never opened. Nothing was
    logged above INFO and nothing appeared on screen. Output is now captured and
    merged so callers can log and surface it; `eject` prints a line or two, so
    there is no volume concern.
    """
    return subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # merged — the interleaving is evidence
        timeout=timeout,
        check=False,
        text=True,
        errors="replace",  # a stray non-UTF-8 byte must not raise here
    )


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, swallowing its output; bounded by the per-step ceiling."""
    return _run_bounded(argv, _STEP_TIMEOUT_S)


def budgeted_runner(budget_s: float) -> Runner:
    """A Runner that bounds the WHOLE kill sequence, not each command in it.

    Why this exists: the kill sequence is *up to seven* subprocesses (a `fuser`,
    a few host `pkill`s, then a `distrobox enter` and its `pkill`s), and each was
    independently capped at 20 s. That is fine off the GUI thread — but the
    shutdown path runs it **on** the GUI thread deliberately (a daemon thread
    would be killed mid-`pkill` as the interpreter exits), so the worst case was a
    window that appeared frozen for well over a minute while closing. Capping each
    command doesn't help; only capping the total does.

    Implemented as a runner wrapper rather than a parameter threaded through the
    three step functions, because the ``runner`` seam already exists and this way
    the steps stay unaware of it — nothing about *what* to kill changes, only how
    long we are willing to spend trying.

    Once the budget is spent, remaining commands are **skipped, and logged as
    skipped** — a truncated shutdown must be visible in the log rather than
    looking like a sequence that ran and found nothing (the "no silent caps"
    rule). A skipped command reports a non-zero code, which the callers already
    read as "this step killed nothing", so the sequence degrades exactly as it
    would if the command had run and matched nothing.
    """
    deadline = time.monotonic() + max(0.0, budget_s)

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            log.warning(
                "drive-free budget of %.1fs is spent — SKIPPING %s "
                "(the drive may still be held; this is a bounded shutdown, "
                "not a completed kill sequence)",
                budget_s,
                argv[:1],
            )
            return subprocess.CompletedProcess(
                argv, returncode=124, stdout="", stderr=""
            )
        # Never hand a command more than the per-step ceiling even if the budget
        # is generous: the ceiling is what keeps one wedged call from eating a
        # whole budget that later steps still need.
        return _run_bounded(argv, min(remaining, _STEP_TIMEOUT_S))

    return run


def _run_rc(argv: list[str], run: Runner) -> int | None:
    """Run argv, returning its exit code, or None if it couldn't run."""
    return _run_capture(argv, run)[0]


def _run_capture(argv: list[str], run: Runner) -> tuple[int | None, str]:
    """Run argv, returning ``(exit code, captured output)``.

    The exit code is **tri-state**: ``None`` means no status was collected (the
    command could not start, or a timeout killed it), which is a real answer and
    never to be read as ``0``. The output is what the tool actually said — the
    thing `_run_bounded` used to send to `DEVNULL`, so no caller could report it.
    """
    try:
        proc = run(argv)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("command %s failed: %s", argv[:1], exc)
        # The reason IS output as far as a reader is concerned; pass it along rather
        # than returning an empty string and losing why nothing ran.
        return None, f"{type(exc).__name__}: {exc}"
    output = getattr(proc, "stdout", "") or ""
    stderr = getattr(proc, "stderr", "") or ""
    return proc.returncode, diagnostics.bounded_output(output + stderr)


def _pkill_arglists() -> list[list[str]]:
    """The pkill argument lists (after the `pkill` token) that stop a rip: the
    reader processes by NAME, which is what actually stops a cyanrip rip
    (`cyanrip` is in `_READER_NAMES`). Never `-f`: a full-command-line match can
    hit the GUI's own command line or this pkill's.

    A list of lists, so a second pattern can be added without reshaping the
    callers; the first entry used to be an inert pattern for the ripper older
    versions drove (removed 2026-09-24)."""
    return [
        ["-KILL", _READER_NAMES],  # cyanrip / cdrdao / cd-paranoia, by process name
    ]


def _run_pkills(prefix: list[str], run: Runner) -> bool:
    """Run the pkill arg-lists with a prefix (`[pkill_path]` on the host, or
    `[distrobox, enter, c, --, pkill]` for the container). True if any killed."""
    killed = False
    for args in _pkill_arglists():
        rc = _run_rc(prefix + args, run)
        log.info("pkill %s rc=%s", args, rc)
        if rc == 0:
            killed = True
    return killed


def eject_drive(device: str = "", runner: Runner | None = None) -> bool:
    """Eject `device` on the host (call *after* the holder is killed, so the
    device is free). Returns True if the eject succeeded.

    A failure is recorded with ``eject``'s **own words** at WARNING, not INFO. It
    used to log ``"eject … returned rc=N"`` at INFO with the message discarded, and
    the caller (`_eject_async`) threw the bool away — so a tray that never opened
    produced nothing at all above INFO, nothing on screen, and a status line still
    claiming the disc was being ejected.
    """
    run = runner or _default_runner
    argv = [_host_tool("eject", _HOST_TOOL_DIRS_EJECT), *([device] if device else [])]
    rc, output = _run_capture(argv, run)
    if rc == 0:
        log.info("ejected %s", device or "(default)")
        return True
    diagnostics.record_command_failure(
        "drive.control_failed",
        "eject",
        argv,
        rc,
        output,
        message=(
            f"could not eject {device or 'the default drive'}: "
            f"{'no exit status (never reaped)' if rc is None else f'exit {rc}'}"
            + (
                f" — {output.strip().splitlines()[-1].strip()}"
                if output.strip()
                else ""
            )
        ),
        severity=diagnostics.WARNING,
        where="drive_control.eject_drive",
    )
    return False


def free_device_holders(
    device: str, runner: Runner | None = None, signal: str = ""
) -> bool:
    """`fuser -k <device>`: signal whatever holds the device, matched by the
    *device* rather than a process name — so it catches the holder no matter
    what it's called, and never the GUI (which doesn't open the device). No-op
    without a device path. Returns True if something was using/signalled.

    ``signal`` names the signal to send (e.g. ``"TERM"``); the default keeps
    fuser's own default, SIGKILL.

    **WHICH SIGNAL IS AN ARCHIVAL DECISION, NOT A TASTE.** SIGKILL cannot be
    caught, so cyanrip runs no ``atexit`` — and ``atexit`` is where it writes the
    log's completion footer and its ``Log FUN512:`` signature. Killing the reader
    therefore turns an archival record into an unverifiable fragment, which is
    exactly the loss §I of the acceptance run exists to detect. A cancel that
    stops the drive by destroying the log has traded one failure for a worse one.

    So the post-cancel rescue passes ``signal="TERM"``: cyanrip handles SIGTERM
    (``cyanrip_main.c``, ``quit_signals[] = { SIGINT, SIGTERM }``), so its handler
    runs, the rip unwinds, and the footer is written. The shutdown path does the
    same through :func:`stop_reader_gracefully` (SIGTERM, a grace, then SIGKILL
    only if the device is still held): it runs only when a rip is in flight, so a
    log IS being protected there. It went straight to SIGKILL until 2026-09-30, on
    the premise that the reader was wedged, and a rip in the round-29 Full run was
    left without its footer that way. Only the stuck-scan path keeps the default,
    because a scan writes no log.

    ONE SIGTERM, AND THIS IS NATURALLY THE FIRST. cyanrip's second-signal branch
    force-exits without the footer, so a duplicate is as destructive as a kill.
    ``fuser`` only signals a process that is STILL holding the device, so a reader
    that already received our SIGTERM has exited and is not signalled again —
    the conditionality is what makes this safe rather than a second guess.
    """
    if not device:
        return False
    run = runner or _default_runner
    argv = [_host_tool("fuser", _HOST_TOOL_DIRS_FUSER), "-s", "-k"]
    if signal:
        argv.append(f"-{signal}")
    argv.append(device)
    rc = _run_rc(argv, run)
    log.info("fuser -k %s %s rc=%s", signal or "(SIGKILL)", device, rc)
    return rc == 0


def kill_reader_on_host(runner: Runner | None = None) -> bool:
    """SIGKILL the reader (cyanrip, and the other reader names) as
    host-visible processes. On
    rootless podman/Distrobox the in-container processes are host-visible, so
    this is the primary lever. Returns True if something was killed."""
    run = runner or _default_runner
    pkill = _host_tool("pkill", _HOST_TOOL_DIRS_PKILL)
    return _run_pkills([pkill], run)


def force_stop_in_container(
    container: str = DEFAULT_CONTAINER, runner: Runner | None = None
) -> bool:
    """SIGKILL the rip from *inside* the container (USER-APPROVED Rule #3
    exception), used only as a fallback when the host pkill matched nothing.
    Returns True if something was killed."""
    run = runner or _default_runner
    distrobox = resolve_tool("distrobox", _DISTROBOX_DIRS)
    return _run_pkills([distrobox, "enter", container, "--", "pkill"], run)


def force_stop_drive(
    device: str = "",
    container: str = DEFAULT_CONTAINER,
    runner: Runner | None = None,
) -> str:
    """Stop a runaway drive, then eject.

    Sequence (all best-effort, most-precise first):
      1. `fuser -k <device>` — device-scoped: kills exactly what holds THIS
         drive, so it can never hit an unrelated rip on another drive (#23);
      2. only if that caught nothing (no device given, or nothing held it), the
         broad name-matched host pkill (the reader names);
      3. only if the host saw nothing at all, kill inside the container;
      4. eject (now that the device is free).

    Device-scoped first (rather than the old name-matched pkill first) means a
    force-stop of one drive won't SIGKILL a cyanrip/cdparanoia ripping a
    *different* disc elsewhere. cyanrip is its own reader (it holds the device
    directly), so `fuser -k` stops it outright — nothing to respawn. The broad
    pkill is kept only as the deviceless/last-resort fallback.

    Synchronous and best-effort; run it off the GUI thread.
    """
    run = runner or _default_runner
    killed = free_device_holders(device, runner=run)
    if not killed:
        killed = kill_reader_on_host(runner=run)
    if not killed:
        killed = force_stop_in_container(container, runner=run)
    ejected = eject_drive(device, runner=run)
    log.info("force_stop_drive: killed=%s ejected=%s", killed, ejected)
    if killed:
        return "Stopped the rip — the drive should spin down."
    if ejected:
        return "Ejected the disc — the drive should stop."
    return "Tried to force-stop the drive (kill + eject)."


#: How long a reader signalled with SIGTERM gets to unwind and write its log's
#: footer before the shutdown path escalates to SIGKILL. **Measured need, not
#: taste:** the round-29 Full run's rip (2026-09-30) went 5.5 s without a line of
#: output in the middle of a slow read, and cyanrip acts on SIGTERM only once the
#: read in hand returns. The old shutdown path allowed 191 ms, then SIGKILLed, and
#: the log was left without its footer or `Log FUN512:` (the fork's round 30 S25).
#:
#: **8 s was shorter than one read, so it is 108 s** (2026-09-30, the fork's round
#: 30 lap 5 S17 and lap 7 S16; then the 2026-10-04 rig run). A SIGTERM that arrives
#: during a read is acted on only when the read returns. The fork first cited reads
#: of 11 s; our filed logs from this rig's drive hold one of 20 s, the fork's one of
#: 21 s (`docs/handshake/inbound/artifacts/round-30-lap-07-accurip-gddc1e8c.log:282`),
#: and a damaged disc one of **54 s**
#: (`docs/handshake/artifactsround30/round30oct04full.log:1501`).
#: The grace is TWICE the longest read filed in this tree, and
#: `tests/test_drive_control.py` derives that floor from the filed logs rather than
#: from this comment. It costs nothing in the ordinary case, where the wait ends
#: the moment the reader lets go, and it could only become this long because the
#: window no longer waits: it closes, and the wait runs as exit work (`exit_work`).
READER_TERM_GRACE_S: Final[float] = 108.0

#: How often the grace loop asks whether the device is still held.
_HELD_POLL_S: Final[float] = 0.25


def device_is_held(device: str, runner: Runner | None = None) -> bool | None:
    """`fuser -s <device>` with no signal: does anything still hold the device?

    **Tri-state.** ``True`` (exit 0: something holds it), ``False`` (exit 1: nothing
    does), ``None`` (no answer: fuser could not run, timed out, or a spent budget
    skipped it). A caller must not read ``None`` as "released".
    """
    if not device:
        return None
    rc = _run_rc(
        [_host_tool("fuser", _HOST_TOOL_DIRS_FUSER), "-s", device],
        runner or _default_runner,
    )
    if rc == 0:
        return True
    if rc == 1:
        return False
    return None


def running_readers(runner: Runner | None = None) -> tuple[str, ...] | None:
    """`pgrep -l` for the reader names: which readers does the HOST see running?

    Each entry is pgrep's own ``"<pid> <name>"`` line. ``()`` means pgrep looked
    and found none; ``None`` means it gave no answer (could not run, timed out),
    which a caller must not read as "none". The names are the ones the kill path
    uses (`_READER_NAMES`), so the two cannot disagree about what a reader is.
    """
    rc, out = _run_capture(
        [_host_tool("pgrep", _HOST_TOOL_DIRS_PKILL), "-l", _READER_NAMES],
        runner or _default_runner,
    )
    if rc == 0:
        return tuple(line.strip() for line in out.splitlines() if line.strip())
    if rc == 1:
        return ()
    return None


def stop_reader_gracefully(
    device: str,
    container: str = DEFAULT_CONTAINER,
    runner: Runner | None = None,
    already_signalled: bool = False,
    grace_s: float = READER_TERM_GRACE_S,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Stop the reader holding ``device`` so that its log keeps its footer.

    SIGTERM first (device-scoped, `fuser -k -TERM`), then wait up to ``grace_s``
    for the device to be let go, and only if it is still held — or whether it is
    held cannot be told — escalate to :func:`free_drive`, whose SIGKILL leaves the
    log without its footer. That order is the archival decision
    :func:`free_device_holders` explains, applied to the shutdown path, which used
    to go straight to SIGKILL.

    ``already_signalled`` skips the SIGTERM: cyanrip's second signal force-exits
    without the footer, so a reader the post-cancel rescue already signalled is
    only waited for, never signalled again.

    **Fail-safe direction.** An undeterminable answer escalates. The failure the
    kill protects against is a reader left ripping after the app has gone (the
    2026-07-01 report); the one the grace protects against is a record without
    its footer. Escalating on "not determined" keeps the first impossible and
    costs the second only when fuser itself cannot answer.

    Blocks for up to ``grace_s`` plus the escalation; the shutdown path's own
    budget bounds it. Never raises.
    """
    if not device:
        log.warning(
            "no device to scope a SIGTERM to, so the reader is stopped with "
            "SIGKILL and its log may have no footer"
        )
        return free_drive(device=device, container=container, runner=runner)
    run = runner or _default_runner
    if not already_signalled:
        if not free_device_holders(device, runner=run, signal="TERM"):
            log.info(
                "nothing on the host held %s to SIGTERM; falling back to the "
                "broader stop",
                device,
            )
            return free_drive(device=device, container=container, runner=run)
    started = clock()
    while True:
        held = device_is_held(device, runner=run)
        waited = clock() - started
        if held is False:
            log.info(
                "the reader let go of %s %.1fs after SIGTERM; no SIGKILL was needed, "
                "so its log was allowed to finish",
                device,
                waited,
            )
            return "Stopped the rip; its log was allowed to finish."
        if held is None or waited >= grace_s:
            break
        sleep(_HELD_POLL_S)
    log.warning(
        "the reader still held %s after %.1fs of grace (or fuser could not say: "
        "%s); escalating to SIGKILL, so its log may have no footer",
        device,
        waited,
        "held" if held else "not determined",
    )
    return free_drive(device=device, container=container, runner=run)


def free_drive(
    device: str = "",
    container: str = DEFAULT_CONTAINER,
    runner: Runner | None = None,
) -> str:
    """Free a drive wedged by a runaway reader, WITHOUT ejecting the disc.

    Same kill sequence as :func:`force_stop_drive` (device-scoped `fuser -k`
    first, then the broad host pkill, then the in-container fallback) but it
    deliberately does NOT eject. Used when a *disc scan* gets stuck: the reader
    stalls holding the device open — even after the host-side subprocess times
    out, because podman doesn't forward the kill signal into the container.
    Device-scoped first so freeing one wedged drive can't kill a rip on another
    (#23). Killing the reader releases the device; leaving the disc in place lets
    the user immediately Rescan (or switch backends) without re-inserting it.

    Synchronous and best-effort; always run OFF the GUI thread. The shutdown
    path (`_stop_rip_on_shutdown` in `closeEvent`) ran it on the GUI thread by
    design until 2026-09-30, and was this rule's one sanctioned exception; it now
    reaches it through `stop_reader_gracefully` as exit work (`exit_work`), on a
    helper thread `app.main` joins before the process exits, so the exception is
    gone (see that method's docstring).
    """
    run = runner or _default_runner
    killed = free_device_holders(device, runner=run)
    if not killed:
        killed = kill_reader_on_host(runner=run)
    if not killed:
        killed = force_stop_in_container(container, runner=run)
    log.info("free_drive: killed=%s", killed)
    if killed:
        return "Freed the drive — it should spin down. Click Rescan disc to try again."
    return "Tried to free the drive (stopped the reader)."
