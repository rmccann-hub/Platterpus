"""Resolve an external tool to a real path under a hostile PATH.

**Why this module exists.** The host-setup wizard installs `flac`, `metaflac`
and friends inside the `ripping` container and `distrobox-export`s them into
`~/.local/bin` (Critical rule #3 — the GUI calls the host-exported binary, never
the container). A GUI launched from a *desktop icon* does not inherit a login
shell's PATH, and `~/.local/bin` is exactly the entry that goes missing.

The failure that produces is nasty precisely because it looks like the opposite
of itself: the wizard checks `~/.local/bin/flac` directly and reports success,
while the launch-time dependency probe resolves a bare `"flac"` through PATH,
finds nothing, and tells the user to install a tool that is already installed
and exported. Tagging, FLAC verification and CTDB decode then degrade for no
reason the user can see. (Architecture audit, 2026-07-28; same class as the
cold-start timeout bug — an environment assumption that only breaks off the
developer's own machine.)

`drive_control` already solved this for its own tools; this module is that
solution generalised, so every caller shares one search order instead of each
adapter inventing its own.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Final


def exported_tools_dir() -> str:
    """``~/.local/bin``: where `distrobox-export` puts the CONTAINER's tools.

    Read at call time, from the home directory as it is now, so a test that points
    ``HOME`` somewhere else reaches every caller.
    """
    return str(Path.home() / ".local" / "bin")


# Searched in order, after PATH. `~/.local/bin` leads because it is where
# `distrobox-export` puts the container's tools — the whole point of the module.
_FALLBACK_DIRS: Final[tuple[str, ...]] = (
    exported_tools_dir(),
    "/usr/bin",
    "/usr/local/bin",
    "/bin",
)


def _same_dir(a: str, b: str) -> bool:
    """True when two spellings name one directory (`/home` → `/var/home` on
    Fedora Atomic, a trailing slash, a relative entry in PATH)."""
    return os.path.realpath(a) == os.path.realpath(b)


def find_tool(
    name: str,
    search_dirs: Sequence[str] | None = None,
    *,
    exclude_dirs: Sequence[str] = (),
) -> str | None:
    """Absolute path to ``name``, or ``None`` if it cannot be found.

    **The one implementation of the search.** PATH first, then ``search_dirs`` in
    order, or :data:`_FALLBACK_DIRS` when the caller names none. There were three
    copies of this loop (here, `ctdb/decode._which` and `drive_control._resolve`),
    in a module whose own docstring says it exists so there would be one (TASKS row
    "Three copies of one tool-search order"). A caller that needs a DIFFERENT
    order passes it, so the order is a named decision at the call site rather than
    a fourth copy of the loop.

    ``exclude_dirs`` are skipped in BOTH halves, PATH included. `drive_control`
    passes :func:`exported_tools_dir`, because its force-stop tools must be the
    host's, never a container export. Leaving that directory out of its own list
    was not enough, and the code said otherwise (review R6, 2026-09-28): PATH is
    searched first, and a login or Plasma session puts `~/.local/bin` on it, so an
    exported `pkill` there won and "device-scoped on the host first" ran inside
    the container.

    ``_FALLBACK_DIRS`` is read at call time, not bound as a default, so a test that
    replaces it reaches every caller.
    """
    if exclude_dirs:
        path = os.environ.get("PATH", os.defpath)
        kept = [
            entry
            for entry in path.split(os.pathsep)
            if not any(_same_dir(entry, skip) for skip in exclude_dirs)
        ]
        found = shutil.which(name, path=os.pathsep.join(kept))
    else:
        found = shutil.which(name)
    if found:
        return found
    for directory in _FALLBACK_DIRS if search_dirs is None else search_dirs:
        if any(_same_dir(directory, skip) for skip in exclude_dirs):
            continue
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
    return None


def resolve_tool(
    name: str,
    search_dirs: Sequence[str] | None = None,
    *,
    exclude_dirs: Sequence[str] = (),
) -> str:
    """Absolute path to ``name``, or a name that fails cleanly if it cannot be found.

    Returning the bare name on failure is deliberate: the caller then gets the
    same ``FileNotFoundError`` it would have had anyway, at the same place, so
    this can be dropped in without changing any error path. It can only ever
    improve resolution, never break it.

    **Except when a directory is excluded.** A bare name is searched on PATH again
    when it runs, which would find the very directory excluded. So the answer is
    then the tool's path in the first directory the caller allows: if it is not
    there, running it fails with ``FileNotFoundError`` naming that path, and the
    excluded copy is never run.
    """
    found = find_tool(name, search_dirs, exclude_dirs=exclude_dirs)
    if found:
        return found
    if exclude_dirs:
        allowed = [
            directory
            for directory in (_FALLBACK_DIRS if search_dirs is None else search_dirs)
            if not any(_same_dir(directory, skip) for skip in exclude_dirs)
        ]
        if allowed:
            return str(Path(allowed[0]) / name)
    return name
