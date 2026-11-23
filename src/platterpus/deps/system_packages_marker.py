"""The install note: which system packages Platterpus itself installed.

**Why a note.** The setup wizard (``deps/host_setup.py``) and ``setup-host.sh``
install Distrobox and podman with the system package manager when they are
missing. Those are general-purpose tools: on Bazzite they ship with the system,
and other containers may depend on them. So the uninstaller offers to remove
them ONLY when this note says Platterpus put them there — never on a guess,
because a wrong guess removes the user's own tools (TASKS R190).

**Format.** One package name per line in ``installed-system-packages.txt``
inside Platterpus's data folder; ``#`` lines are comments. Plain text on
purpose: ``setup-host.sh`` writes the same file with one ``echo``.

Reading never raises: a missing or unreadable note means "we installed
nothing", which is the answer that keeps the user's tools.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Final

from platterpus.paths import LOG_DIR

log = logging.getLogger(__name__)

#: The note's file name. ``setup-host.sh`` spells the same name.
MARKER_NAME: Final[str] = "installed-system-packages.txt"

#: Where the note lives by default: the app's data folder.
MARKER_PATH: Final[Path] = LOG_DIR / MARKER_NAME

#: A package name as the distributions spell one. Anything else in the file is
#: ignored rather than passed to a package manager.
_PACKAGE_NAME: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9+._-]{0,63}$")


def read_installed(path: Path = MARKER_PATH) -> tuple[str, ...]:
    """The packages the note names, in the order written, without repeats."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ()
    except OSError as exc:
        log.warning("could not read the install note %s: %s", path, exc)
        return ()
    names: list[str] = []
    for line in text.splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        if not _PACKAGE_NAME.fullmatch(name):
            log.warning("install note %s: ignoring %r (not a package name)", path, name)
            continue
        if name not in names:
            names.append(name)
    return tuple(names)


def record_installed(package: str, path: Path = MARKER_PATH) -> bool:
    """Add ``package`` to the note. True when the note now names it.

    Called right after a successful install. A failure to write is logged and
    returned, never raised: the install itself succeeded, and the cost of a
    missing note is only that the uninstaller will not offer the package.
    """
    if not _PACKAGE_NAME.fullmatch(package):
        log.error("not recording %r in the install note: not a package name", package)
        return False
    if package in read_installed(path):
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{package}\n")
    except OSError as exc:
        log.warning(
            "could not record %s in the install note %s: %s", package, path, exc
        )
        return False
    log.info("install note: recorded that Platterpus installed %s", package)
    return True


def forget_installed(packages: tuple[str, ...], path: Path = MARKER_PATH) -> None:
    """Drop ``packages`` from the note, after the uninstaller removed them."""
    remaining = [name for name in read_installed(path) if name not in packages]
    try:
        if remaining:
            path.write_text(
                "".join(f"{name}\n" for name in remaining), encoding="utf-8"
            )
        else:
            path.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("could not update the install note %s: %s", path, exc)
