"""Which systemd unit owns the ``ripping`` container, and keeping it off ours.

**The defect this closes (measured on the rig, 2026-09-24).** On 2026-09-23 a
whole-disc rip was killed 95 seconds in, because the Distrobox container it ran
in died underneath it. The host journal showed that the container belonged to a
*different, already-closed* Platterpus window:

* that window started the container, four seconds after it opened;
* it later updated itself and relaunched inside the same systemd unit, and the
  relaunched window was closed;
* **the unit stayed alive after the window closed**, because the container's
  monitor process (``conmon``) was still inside it. KDE runs every app it
  launches as a systemd service that lives while any of its processes does;
* the acceptance run, in a new window, used that container, and when that old
  unit ended, the container went with it.

**Why the monitor was inside a window's unit.** podman leaves ``conmon`` in the
caller's cgroup, instead of giving it a scope of its own, whenever the
``INVOCATION_ID`` environment variable is set
(``containers/podman@5866b09:libpod/oci_conmon_linux.go:183-186``). systemd sets
that variable for every service it runs, so a KDE-launched app has it, and every
child we spawn inherited it: the ripper wrapper, ``flac``, ``metaflac``,
``cd-paranoia`` — each a Distrobox export, so each can start the container.

**What this module does about it** — two things, both about where the
container's monitor lives:

1. :func:`release_launcher_unit_hold` removes ``INVOCATION_ID`` from our own
   environment at startup, before anything spawns. podman then puts ``conmon``
   in its own ``libpod-conmon-…scope``, so a container we start survives any of
   our windows closing. Reproduced on the rig with a stand-in app launched the
   way KDE launches apps: with the variable, the container died when the app's
   unit ended; without it, the container kept running.
2. :func:`container_owner` is read-only: it finds the container's ``conmon`` in
   ``/proc`` and names the unit that owns it, for ``--doctor``. A container
   started from a terminal, or by an older Platterpus, still belongs to that
   terminal or window, and this is how a user finds out.

**Routing is unchanged** (Critical rule #3): we still only run
``~/.local/bin/cyanrip``. Nothing here calls into the container or starts,
stops or moves it; the first part changes the environment our children inherit,
the second only reads ``/proc``.
"""

from __future__ import annotations

import enum
import logging
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

#: The variable systemd sets for a service's processes, and the one podman reads.
INVOCATION_ID: Final[str] = "INVOCATION_ID"

#: The prefix podman gives the scope it creates for a container's monitor when it
#: is allowed to (``createUnitName("libpod-conmon", id)`` in the file cited above).
OWN_SCOPE_PREFIX: Final[str] = "libpod-conmon-"

#: What KDE (and systemd's XDG autostart) name the units of the apps they launch:
#: ``app-<desktop id>@<uuid>.service`` or ``app-<desktop id>-<pid>.scope``.
APP_UNIT_PREFIX: Final[str] = "app-"


def release_launcher_unit_hold(environ: MutableMapping[str, str]) -> bool:
    """Remove ``INVOCATION_ID`` from ``environ``; return whether it was there.

    Called with ``os.environ`` at the top of :func:`platterpus.app.main`, so every
    child process from then on inherits an environment without it. Idempotent:
    a second call finds nothing and returns ``False``.
    """
    if environ.pop(INVOCATION_ID, None) is None:
        return False
    log.info(
        "removed %s from our environment, so a container one of our tools starts "
        "gets its own scope instead of belonging to this window (podman keeps its "
        "monitor in the caller's unit while the variable is set)",
        INVOCATION_ID,
    )
    return True


class Ownership(enum.Enum):
    """Who the container's monitor belongs to."""

    OWN_SCOPE = "own_scope"  # its own libpod-conmon scope: survives any app closing
    APP = "app"  # inside an app's or terminal's unit: dies when that unit ends
    OTHER = "other"  # some other unit (a login session, a service): named as found
    NOT_RUNNING = "not_running"  # no monitor process for the container
    UNKNOWN = "unknown"  # a monitor was found but its cgroup could not be read


@dataclass(frozen=True)
class ContainerOwner:
    """The answer :func:`container_owner` gives. Never raised, always returned."""

    ownership: Ownership
    unit: str = ""  # the unit's name, as the cgroup path ends
    app: str = ""  # the app's desktop id, for an APP unit
    pid: int = 0  # the monitor's process id, 0 when there is none


def unit_from_cgroup(text: str) -> str:
    """The unit a ``/proc/<pid>/cgroup`` file places a process in, or ``""``.

    Reads the cgroup-v2 line (``0::/path``) and returns its last path component.
    Best-effort and never raises, like every parser of external text here: an
    unexpected file gives ``""``, which the caller reports as unknown.
    """
    for line in text.splitlines():
        hierarchy, sep, path = line.partition("::")
        if sep and hierarchy == "0":
            return path.rstrip("/").rpartition("/")[2]
    return ""


def app_from_unit(unit: str) -> str:
    """``app-org.kde.konsole-22592.scope`` -> ``org.kde.konsole``; ``""`` if not an app."""
    if not unit.startswith(APP_UNIT_PREFIX):
        return ""
    name = unit[len(APP_UNIT_PREFIX) :]
    name = name.rsplit(".", 1)[0] if name.endswith((".service", ".scope")) else name
    if "@" in name:  # app-<id>@<uuid>.service
        return name.split("@", 1)[0]
    head, _, tail = name.rpartition("-")  # app-<id>-<pid>.scope
    return head if head and tail.isdigit() else name


def classify(unit: str) -> Ownership:
    """Which kind of owner a unit name is."""
    if not unit:
        return Ownership.UNKNOWN
    if unit.startswith(OWN_SCOPE_PREFIX):
        return Ownership.OWN_SCOPE
    if unit.startswith(APP_UNIT_PREFIX):
        return Ownership.APP
    return Ownership.OTHER


def _is_container_monitor(argv: list[str], container: str) -> bool:
    """Whether a ``conmon`` command line is the container's own monitor.

    ``-n``/``--name`` carries the container's name. An ``exec`` session has a
    monitor of its own (``-e``/``--exec``), which lives in whoever ran the exec
    and ends with it, so it is not the one that decides the container's life.
    """
    if "-e" in argv or "--exec" in argv:
        return False
    for flag in ("-n", "--name"):
        if flag in argv:
            index = argv.index(flag)
            if index + 1 < len(argv) and argv[index + 1] == container:
                return True
    return f"--name={container}" in argv


def container_owner(
    container: str = "ripping", proc: Path | None = None
) -> ContainerOwner:
    """Find the container's monitor in ``proc`` and name the unit that owns it.

    Read-only and never raises: a process that vanishes or cannot be read while
    we look is skipped, and the answer says ``NOT_RUNNING`` or ``UNKNOWN`` rather
    than guessing. ``proc`` is ``/proc`` in production and a fake tree in tests.
    """
    root = proc if proc is not None else Path("/proc")
    try:
        entries = [entry for entry in root.iterdir() if entry.name.isdigit()]
    except OSError as exc:
        log.warning("could not list %s to find the container's monitor: %s", root, exc)
        return ContainerOwner(Ownership.UNKNOWN)
    for entry in sorted(entries, key=lambda e: int(e.name)):
        try:
            if (entry / "comm").read_text(encoding="utf-8").strip() != "conmon":
                continue
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue  # gone, or not ours to read
        argv = [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
        if not _is_container_monitor(argv, container):
            continue
        try:
            unit = unit_from_cgroup((entry / "cgroup").read_text(encoding="utf-8"))
        except OSError as exc:
            log.warning("could not read the container monitor's cgroup: %s", exc)
            return ContainerOwner(Ownership.UNKNOWN, pid=int(entry.name))
        return ContainerOwner(
            classify(unit), unit=unit, app=app_from_unit(unit), pid=int(entry.name)
        )
    return ContainerOwner(Ownership.NOT_RUNNING)
