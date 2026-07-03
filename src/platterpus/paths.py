"""Filesystem paths used across the GUI.

Single source of truth for user config, user log, and the paths the
Distrobox container shares with the GUI. Honors `XDG_CONFIG_HOME` and
`XDG_DATA_HOME` when set, falling back to `~/.config` and
`~/.local/share` per the freedesktop.org Base Directory spec.

No I/O happens here — every constant is just a `pathlib.Path`. The
modules that consume these constants (`config.py`, `logging_setup.py`)
are responsible for creating parent directories on first write.
"""

from __future__ import annotations

import os
from pathlib import Path

# XDG base dirs with conventional fallbacks. We resolve once at import
# time; if the user's HOME or XDG_* changes mid-process, restart.
_XDG_CONFIG_HOME: Path = Path(
    os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
)
_XDG_DATA_HOME: Path = Path(
    os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
)

# Application slot under each XDG base dir (config/cache/log dir name + the
# CLI/console-script name). Lower-case, hyphen-free slug.
APP_NAME: str = "platterpus"

# Reverse-DNS freedesktop application id — used for the .desktop filename, the
# AppStream metainfo <id>, and the bundled icon name. The hyphen in the GitHub
# handle (rmccann-hub) becomes an underscore because app-id components can't
# contain hyphens. Distinct from APP_NAME (which is the CLI/config slug).
APP_ID: str = "io.github.rmccann_hub.Platterpus"

# Where our own settings live.
CONFIG_DIR: Path = _XDG_CONFIG_HOME / APP_NAME
CONFIG_PATH: Path = CONFIG_DIR / "config.toml"

# Per-drive profile ledger (drive_profiles.py): a machine-managed record of the
# stable hardware fingerprint + the provenance/confidence of each drive's
# learned read offset and cache behaviour. Deliberately a SEPARATE file from
# config.toml — it's a keyed collection of hardware facts with a different
# lifecycle than the user's flat preferences, and it is never hand-edited (so
# JSON, not the hand-editable TOML config). It is a TRUST LEDGER only: it never
# decides which offset a rip uses — whipper.conf and the --offset override stay
# authoritative (PLANNING.md KDD-23).
DRIVE_PROFILES_PATH: Path = CONFIG_DIR / "drive_profiles.json"

# Where our log file lives (rotated by logging_setup.py).
LOG_DIR: Path = _XDG_DATA_HOME / APP_NAME
LOG_PATH: Path = LOG_DIR / "log.txt"

# The legacy whipper.conf in the Distrobox `ripping` container's shared config.
# It historically held per-drive `read_offset` / `defeats_cache`. Platterpus
# still READS it as a reference for the offset trust display (offset_config.py),
# but nothing writes it any more: the drive-setup wizard saves the detected
# offset to Platterpus's OWN config, applied to cyanrip as `-s` (cyanrip does
# not read whipper.conf). Kept read-only for users upgrading from the whipper
# era. See PLANNING.md KDD-15/18.
WHIPPER_CONFIG_PATH: Path = _XDG_CONFIG_HOME / "whipper" / "whipper.conf"

# Default location of the host-exported whipper binary. The Settings
# dialog lets the user override this at runtime, but this is the value
# we assume on first launch (matches the brief's documented setup).
WHIPPER_BINARY_DEFAULT: Path = Path.home() / ".local" / "bin" / "whipper"

# Default location of the host-exported cyanrip binary (the optional
# KDD-18 backend). Same export route as whipper: the host-setup wizard
# runs `distrobox-export` inside the `ripping` container, which drops a
# wrapper here.
CYANRIP_BINARY_DEFAULT: Path = Path.home() / ".local" / "bin" / "cyanrip"

# Default location of the host-exported `flac` decoder. The setup wizard
# installs the `flac` package in the container (for metaflac too) and is
# supposed to export this so `flac --test` can verify rips that the backend
# didn't self-verify (cyanrip) and the CTDB audio cross-check can decode.
# Same `distrobox-export` route as whipper/cyanrip.
FLAC_BINARY_DEFAULT: Path = Path.home() / ".local" / "bin" / "flac"
