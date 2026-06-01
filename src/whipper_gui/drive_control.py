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

# Process names the in-container reader/ripper runs under. Matched as an
# extended-regex alternation by `pkill -f` (searched anywhere in the command
# line, so a full path like /usr/bin/cd-paranoia still matches).
_KILL_PATTERN: str = "cdparanoia|cd-paranoia|whipper|cdrdao"

# A runner takes an argv list and returns something with a `.returncode`.
Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

# When the GUI is launched from a desktop icon (not a shell), PATH can be
# minimal and miss ~/.local/bin or even /usr/bin. Resolve these tools to an
# absolute path so the force-stop doesn't silently no-op.
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


def eject_drive(device: str = "", runner: Runner | None = None) -> bool:
    """Eject `device` on the host. Returns True if the eject succeeded.

    A non-zero exit is the normal "device busy" case if the reader still holds
    the drive — not an error worth surfacing. (Call this *after* the reader is
    killed so the device is free.)
    """
    run = runner or _default_runner
    argv = [_resolve("eject", *_EJECT_FALLBACKS), *([device] if device else [])]
    try:
        rc = run(argv).returncode
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("eject %s failed: %s", device or "(default)", exc)
        return False
    if rc == 0:
        log.info("ejected %s", device or "(default)")
        return True
    log.info("eject %s returned rc=%s (likely busy)", device or "(default)", rc)
    return False


def force_stop_in_container(
    container: str = DEFAULT_CONTAINER, runner: Runner | None = None
) -> bool:
    """SIGKILL the in-container reader/ripper. USER-APPROVED Rule #3 exception.

    This is the lever that actually stops a runaway rip: the host can't signal
    the in-container `cdparanoia` (podman doesn't forward it), so we kill it
    inside the container. SIGKILL (not TERM) because force-stop is drastic and
    cdparanoia may otherwise sit in its read loop. Once killed, the device is
    released and the drive spins down within a few seconds.

    Returns True if pkill ran (exit 1 just means "nothing matched", which is
    fine).
    """
    run = runner or _default_runner
    argv = [_resolve("distrobox", *_DISTROBOX_FALLBACKS), "enter", container, "--",
            "pkill", "-KILL", "-f", _KILL_PATTERN]
    try:
        rc = run(argv).returncode
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("in-container force-stop failed: %s", exc)
        return False
    log.info("in-container pkill -KILL '%s' rc=%s", _KILL_PATTERN, rc)
    return rc in (0, 1)  # 0 killed something, 1 matched nothing


def force_stop_drive(
    device: str = "",
    container: str = DEFAULT_CONTAINER,
    runner: Runner | None = None,
) -> str:
    """Stop a runaway drive: kill the in-container reader, then eject.

    Order matters — we kill **first** so the reader lets go of the device, then
    eject (an eject while the reader holds the device just fails "busy", which
    is why the old eject-first order left the drive spinning). Synchronous and
    best-effort; run it off the GUI thread.
    """
    killed = force_stop_in_container(container, runner=runner)
    ejected = eject_drive(device, runner=runner)
    log.info("force_stop_drive: killed=%s ejected=%s", killed, ejected)
    if killed and ejected:
        return "Stopped the reader and ejected — the drive is stopped."
    if killed:
        return "Stopped the in-container reader — the drive should spin down."
    if ejected:
        return "Ejected the disc — the drive should stop."
    return "Tried to force-stop the drive (reader kill + eject)."
