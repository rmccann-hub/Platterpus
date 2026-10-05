"""The first entry into the ripping container of a session happens alone.

**What happened (the 2026-10-04 rig run).** At launch, two of our probes entered
the stopped ``ripping`` container in the same second: the dependency check's
``cyanrip --version`` and the startup disc scan's ``cyanrip -I``. The version
probe printed its banner and then did not exit until our 60 s timeout; the disc
scan never returned, and was abandoned 84 s later when the run rescanned
(``docs/handshake/artifactsround30/round30oct04platterpusapplog2.txt:59910``,
``:59918``, ``:60032``). The same scan on the now-running container returned in
13.5 s. ``cyanrip --version`` alone, measured by the fork on the same build,
returns in about 0.05 s before it touches the drive, so the wait was in the
container wrapper starting the container, twice at once.

**What this does.** While no container command has finished yet in this
process, a container command waits for the one already in flight to finish
before it starts. Once any one has finished, whatever its outcome, the gate is
open for good and commands run side by side as they always have. The wait is
bounded (:data:`FIRST_ENTRY_WAIT_S`) and interruptible by the caller's own
cancel, so a first entry that hangs costs the others a bounded delay and never
holds them for ever.

**What it is not.** It is a mitigation for a race we inferred and have not
reproduced: the mechanism inside the wrapper is not established. If the first
entry hangs on its own, the second still waits for it, then runs on a
container that is up. Routing is unchanged (Critical rule #3): this only orders
our own spawns of ``~/.local/bin`` exports; it never starts, stops or enters the
container itself.

Plain ``threading``: the callers are worker threads, never the GUI thread.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

from platterpus.tool_paths import exported_tools_dir

log = logging.getLogger(__name__)

#: The longest a container command waits for the first one to finish. Longer than
#: the dependency probe's own 60 s timeout, so a first entry that hangs until it is
#: killed has finished (and opened the gate) before anyone gives up on it.
FIRST_ENTRY_WAIT_S: Final[float] = 75.0

#: How often a waiting caller re-checks its own cancel and the gate.
_POLL_S: Final[float] = 0.25


def is_container_export(binary: str) -> bool:
    """Whether ``binary`` is a ``distrobox-export`` shim, which enters the container.

    Host tools (``fuser``, ``pgrep``) never do and never wait here.
    """
    if not binary:
        return False
    return str(Path(binary).parent) == exported_tools_dir()


class FirstEntryGate:
    """Orders container commands until the first one of the session has finished."""

    def __init__(self, wait_s: float = FIRST_ENTRY_WAIT_S) -> None:
        self._wait_s: float = wait_s
        self._lock: threading.Lock = threading.Lock()
        self._open: threading.Event = threading.Event()

    def is_open(self) -> bool:
        """True once a container command has finished in this process."""
        return self._open.is_set()

    def claim(
        self,
        binary: str,
        *,
        name: str = "",
        should_stop: Callable[[], bool] = lambda: False,
        clock: Callable[[], float] = time.monotonic,
    ) -> bool:
        """Wait, if this is a container command before the gate opens.

        Returns True when the caller is the first entry and must call
        :meth:`release` once its command has finished; False when it may simply
        run. Never raises, and never waits past :data:`FIRST_ENTRY_WAIT_S` or past
        ``should_stop()`` turning true.
        """
        if self._open.is_set() or not is_container_export(binary):
            return False
        started = clock()
        announced = False
        while True:
            if self._lock.acquire(timeout=_POLL_S):
                if self._open.is_set():
                    self._lock.release()
                    return False
                return True
            if self._open.is_set():
                return False
            if not announced:
                announced = True
                log.info(
                    "%s waits for the first container command of this session to "
                    "finish, so the container is not started twice at once",
                    name or binary,
                )
            if should_stop():
                return False
            if clock() - started >= self._wait_s:
                log.warning(
                    "%s waited %.0fs for the first container command, which has "
                    "not finished; running anyway",
                    name or binary,
                    self._wait_s,
                )
                return False

    def release(self) -> None:
        """The first entry has finished: open the gate for good."""
        self._open.set()
        self._lock.release()


#: The process's one gate. Module level because every container command in the
#: process shares the one container.
FIRST_ENTRY: Final[FirstEntryGate] = FirstEntryGate()
