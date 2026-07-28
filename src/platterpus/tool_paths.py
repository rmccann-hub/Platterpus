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

import shutil
from pathlib import Path
from typing import Final

# Searched in order, after PATH. `~/.local/bin` leads because it is where
# `distrobox-export` puts the container's tools — the whole point of the module.
_FALLBACK_DIRS: Final[tuple[str, ...]] = (
    str(Path.home() / ".local" / "bin"),
    "/usr/bin",
    "/usr/local/bin",
    "/bin",
)


def resolve_tool(name: str) -> str:
    """Absolute path to ``name``, or the bare name if it cannot be found.

    Returning the bare name on failure is deliberate: the caller then gets the
    same ``FileNotFoundError`` it would have had anyway, at the same place, so
    this can be dropped in without changing any error path. It can only ever
    improve resolution, never break it.
    """
    found = shutil.which(name)
    if found:
        return found
    for directory in _FALLBACK_DIRS:
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
    return name
