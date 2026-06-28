# SPDX-License-Identifier: GPL-3.0-only
"""Composition root helpers — build the real adapters from config.

Two entry points need the *same* concrete adapters wired from ``Config``: the
running GUI (``app.py``) and the ``--doctor`` diagnostic (``preflight.py``).
Both pick the ripping backend from ``cfg.ripper_backend`` and build the
MusicBrainz client with the project's user-agent. Doing that in ONE place keeps
the two from drifting — before this existed, the backend-selection block
(including the host-exported-path fallback) was copied in both, and a fix to one
could silently miss the other. It also gives the architecture rule "nothing
constructs adapters except the composition root" (docs/architecture.md §2) a
literal home.

Construction does **no I/O** (no network, no subprocess), so these are safe to
call before any check or window exists. The functions are deliberately granular
rather than one "build everything": ``app.py`` additionally needs a
``MetaflacAdapter`` and injects into ``MainWindow``, while ``preflight`` wraps
the pieces in a ``PreflightContext`` with the backend name — so the genuinely
*shared* part is the backend choice and the MB client, and that is what lives
here. The trivial zero-argument adapters (``CtdbHttpImpl``, ``DependencyManager``)
stay inline at each call site; wrapping them would add indirection without
removing duplication.
"""

from __future__ import annotations

import logging
from pathlib import Path

from platterpus import __version__
from platterpus.adapters.musicbrainz_client import (
    MusicBrainzClient,
    MusicBrainzNgsImpl,
)
from platterpus.adapters.whipper_backend import (
    WhipperBackend,
    WhipperHostExportedImpl,
)
from platterpus.config import Config
from platterpus.paths import CYANRIP_BINARY_DEFAULT

log = logging.getLogger(__name__)

# MusicBrainz policy wants a reachable contact (URL or email) in the user-agent
# so they can reach a human about a misbehaving client; also the CTDB default.
CONTACT_URL = "https://github.com/rmccann-hub/Platterpus"


def build_backend(cfg: Config) -> tuple[WhipperBackend, str]:
    """Construct the ripping backend that ``cfg.ripper_backend`` selects.

    Returns ``(backend, backend_name)``. cyanrip (KDD-18) is imported lazily so
    a whipper-only run never pays for it. Both prefer the host-exported absolute
    path: a desktop-launched GUI inherits a minimal PATH that may omit
    ``~/.local/bin`` (the same lesson as ``drive_control``'s absolute-path
    resolution), falling back to a PATH lookup for a native install.
    """
    working_dir = Path(cfg.working_dir) if cfg.working_dir else None
    if cfg.ripper_backend == "cyanrip":
        from platterpus.adapters.cyanrip_backend import CyanripImpl

        cyanrip_binary: Path | str = (
            CYANRIP_BINARY_DEFAULT if CYANRIP_BINARY_DEFAULT.exists() else "cyanrip"
        )
        log.info("using cyanrip backend (%s)", cyanrip_binary)
        backend: WhipperBackend = CyanripImpl(
            binary_path=cyanrip_binary, working_dir=working_dir
        )
        return backend, "cyanrip"
    return (
        WhipperHostExportedImpl(
            binary_path=Path(cfg.whipper_path), working_dir=working_dir
        ),
        "whipper",
    )


def build_musicbrainz_client() -> MusicBrainzClient:
    """Construct the v1 MusicBrainz client with the project's user-agent."""
    return MusicBrainzNgsImpl(
        app="platterpus", version=__version__, contact=CONTACT_URL
    )
