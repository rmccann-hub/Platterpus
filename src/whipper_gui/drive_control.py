"""Force-stop the optical drive when a cancelled rip won't let go.

Why this exists: a rip runs as `~/.local/bin/whipper` (host wrapper) → podman
→ whipper → **cdparanoia inside the `ripping` container**. Cancelling kills
the host-side process tree, but podman doesn't forward the signal into the
container, so cdparanoia keeps reading and the drive spins — sometimes for
minutes (real-user report, 2026-05-31). Two levers can stop it:

  1. **Eject the disc on the host** (`eject <device>`) — stays within the
     "GUI talks to the host, never the container" architecture. Often
     fails mid-rip with "device busy" because cdparanoia holds the device
     open; in that case lever 2 does the work.
  2. **Kill cdparanoia/whipper inside the container.**

Lever 2 runs a command *inside* the `ripping` container, which CLAUDE.md
Critical Rule #3 normally forbids ("the GUI never calls into the container
directly"). This is a **deliberate, user-approved exception (2026-05-31)**,
scoped strictly to *force-stopping a cancelled rip* — the only reliable way
to stop a runaway in-container reader from the host. It is NOT a general
licence to drive whipper inside the container; ripping itself still goes
through `~/.local/bin/whipper`.

Everything here is best-effort and synchronous; the caller runs it off the
GUI thread (it can block for the subprocess timeout). The `runner` is
injectable so tests never touch a real drive or container.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Callable

log = logging.getLogger(__name__)

# The Distrobox container whipper lives in (README/setup-host default).
DEFAULT_CONTAINER: str = "ripping"

# The optical reader's process names. We match against the process *name*
# (pkill default), NOT the full command line (`-f`), for two safety reasons:
#   * `-f` would match the GUI's own command line ("whipper-gui") and kill the
#     app, and match the `distrobox enter … whipper …` wrapper and kill that
#     session before reaching the reader (the bug that left the drive spinning).
#   * the reader binaries below uniquely identify what holds the drive.
# We deliberately do NOT include "whipper" here — killing the reader releases
# the device (the drive spins down in seconds); the orphaned whipper then errors
# out on its own, and matching "whipper" risks hitting "whipper-gui".
_READER_NAMES: str = "cdparanoia|cd-paranoia|cdrdao"

# A runner takes an argv list and returns something with a `.returncode`.
Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

# When the GUI is launched from a desktop icon (not a shell), PATH can be
# minimal and miss ~/.local/bin or even /usr/bin. Resolve these tools to an
# absolute path so the force-stop doesn't silently no-op.
_PKILL_FALLBACKS: tuple[str, ...] = ("/usr/bin/pkill", "/bin/pkill")
_EJECT_FALLBACKS: tuple[str, ...] = ("/usr/bin/eject", "/usr/sbin/eject", "/sbin/eject")
_DISTROBOX_FALLBACKS: tuple[str, ...] = (
    os.path.expanduser("~/.local/bin/distrobox"),
    "/usr/bin/distrobox",
    "/usr/local/bin/distrobox",
)


def _resolve(name: str, *fallbacks: str) -> str:
    """Find an executable even under a minimal PATH. Falls back to common
    absolute locations, then to the bare name (which FileNotFoundErrors if the
    tool is genuinely absent — caught and treated as best-effort)."""
    found = shutil.which(name)
    if found:
        return found
    for candidate in fallbacks:
        if os.path.exists(candidate):
            return candidate
    return name


def _default_runner(argv: list[str]) -> "subprocess.CompletedProcess[str]":
    """Run a command, swallowing its output; never inherit stdin (so a
    `distrobox enter` can't block waiting on a TTY). Bounded by a timeout so a
    wedged container can't hang the caller forever."""
    return subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    )


def _run_rc(argv: list[str], run: Runner) -> int | None:
    """Run argv, returning its exit code, or None if it couldn't run."""
    try:
        return run(argv).returncode
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("command %s failed: %s", argv[:1], exc)
        return None


def eject_drive(device: str = "", runner: Runner | None = None) -> bool:
    """Eject `device` on the host. Returns True if the eject succeeded.

    A non-zero exit is the normal "device busy" case if the reader still holds
    the drive — call this *after* the reader is killed so the device is free.
    (While a rip is reading, the drive also ignores the physical eject button,
    which is why pressing eject by hand doesn't stop the spin.)
    """
    run = runner or _default_runner
    argv = [_resolve("eject", *_EJECT_FALLBACKS), *([device] if device else [])]
    rc = _run_rc(argv, run)
    if rc == 0:
        log.info("ejected %s", device or "(default)")
        return True
    log.info("eject %s returned rc=%s", device or "(default)", rc)
    return False


def kill_reader_on_host(runner: Runner | None = None) -> int | None:
    """SIGKILL the optical reader as a host-visible process.

    On rootless podman/Distrobox (the Bazzite target) the in-container
    `cdparanoia` is a normal host process, so a host pkill reaches it — no
    `distrobox enter` needed. Matches reader names only (see `_READER_NAMES`),
    so it can never hit the GUI or pkill itself.

    Returns pkill's exit code (0 = killed something, 1 = nothing matched), or
    None if pkill couldn't run.
    """
    run = runner or _default_runner
    argv = [_resolve("pkill", *_PKILL_FALLBACKS), "-KILL", _READER_NAMES]
    rc = _run_rc(argv, run)
    log.info("host pkill -KILL '%s' rc=%s", _READER_NAMES, rc)
    return rc


def force_stop_in_container(
    container: str = DEFAULT_CONTAINER, runner: Runner | None = None
) -> int | None:
    """SIGKILL the reader from *inside* the container. USER-APPROVED Rule #3
    exception, used only as a fallback when the host pkill matched nothing
    (e.g. a setup where container processes aren't host-visible).

    Matches reader names only (no `-f`), so the `distrobox enter`/`pkill`
    command can't match and kill its own session.
    """
    run = runner or _default_runner
    argv = [_resolve("distrobox", *_DISTROBOX_FALLBACKS), "enter", container, "--",
            "pkill", "-KILL", _READER_NAMES]
    rc = _run_rc(argv, run)
    log.info("in-container pkill -KILL '%s' rc=%s", _READER_NAMES, rc)
    return rc


def force_stop_drive(
    device: str = "",
    container: str = DEFAULT_CONTAINER,
    runner: Runner | None = None,
) -> str:
    """Stop a runaway drive: kill the reader, then eject.

    Order matters — kill **first** so the reader lets go of the device (the
    drive spins down within seconds and the eject can then take effect; an
    eject while the reader holds the device just fails "busy"). The host pkill
    is the primary lever; the in-container kill is a fallback only if the host
    matched nothing. Synchronous and best-effort; run it off the GUI thread.
    """
    host_rc = kill_reader_on_host(runner=runner)
    killed = host_rc == 0
    if host_rc != 0:
        # Host pkill found no reader process — try inside the container.
        killed = force_stop_in_container(container, runner=runner) == 0
    ejected = eject_drive(device, runner=runner)
    log.info("force_stop_drive: killed=%s ejected=%s", killed, ejected)
    if killed:
        return "Stopped the reader — the drive should spin down."
    if ejected:
        return "Ejected the disc — the drive should stop."
    return "Tried to force-stop the drive (reader kill + eject)."
