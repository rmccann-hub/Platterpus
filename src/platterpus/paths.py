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
# decides which offset a rip uses — the config's read offset, passed to cyanrip
# as `-s`, stays the only authority (PLANNING.md KDD-23).
DRIVE_PROFILES_PATH: Path = CONFIG_DIR / "drive_profiles.json"

# Where our log file lives (rotated by logging_setup.py).
LOG_DIR: Path = _XDG_DATA_HOME / APP_NAME
LOG_PATH: Path = LOG_DIR / "log.txt"

# LEFTOVERS FROM OLDER VERSIONS, named for what they are rather than for the
# program that made them. Before cyanrip became the only ripper (KDD-18,
# 2026-06-30) Platterpus drove another one, which kept a config folder here and
# was exported to ~/.local/bin under its own name. Nothing reads or writes
# either any more; the uninstaller removes them if they are still on disk. The
# paths are the real names on disk, so they are spelled exactly.
LEGACY_RIPPER_CONFIG_DIR: Path = _XDG_CONFIG_HOME / "whipper"
LEGACY_RIPPER_WRAPPER_PATH: Path = Path.home() / ".local" / "bin" / "whipper"

# Default location of the host-exported cyanrip binary (the sole backend,
# KDD-18): the host-setup wizard runs `distrobox-export` inside the `ripping`
# container, which drops a wrapper here.
CYANRIP_BINARY_DEFAULT: Path = Path.home() / ".local" / "bin" / "cyanrip"

# Default location of the host-exported `flac` decoder. The setup wizard
# installs the `flac` package in the container (for metaflac too) and is
# supposed to export this so `flac --test` can verify rips that the backend
# didn't self-verify (cyanrip) and the CTDB audio cross-check can decode.
# Same `distrobox-export` route as cyanrip.
FLAC_BINARY_DEFAULT: Path = Path.home() / ".local" / "bin" / "flac"

# Default location of the host-exported `cd-paranoia` binary (libcdio's, NOT
# Xiph's cdparanoia — it shares the libcdio-paranoia engine cyanrip reads with,
# so its cache self-test speaks for cyanrip's own reads). Used only by the
# optional cache-defeat probe (`cd-paranoia -A`, KDD-25/KDD-29): it measures
# whether this drive returns cached audio on a re-read, so the EAC-layout log's
# "Defeat audio cache" line can carry a *measured* Yes/No instead of "(unknown)".
# Same `distrobox-export` route as cyanrip/flac — it touches the drive, so it
# runs inside the `ripping` container against the mapped device (Critical Rule #3).
CDPARANOIA_BINARY_DEFAULT: Path = Path.home() / ".local" / "bin" / "cd-paranoia"
