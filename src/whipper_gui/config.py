"""TOML config persistence for the GUI.

Reads `~/.config/whipper-gui/config.toml` via stdlib `tomllib`; writes
via the `tomli-w` package (stdlib is read-only). Uses a typed dataclass
so callers see attribute access (`cfg.output_dir`) instead of dict
lookups, and so the schema lives in one place.

- The first `load()` call creates the file with defaults if missing.
- `save()` writes atomically (temp file + rename) so a crash mid-save
  can't corrupt the user's settings.
- Unknown keys in an older binary loading a newer file are logged and
  dropped, not crashed on. This keeps forward compatibility cheap.
"""

from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

import tomli_w

from whipper_gui.paths import CONFIG_DIR, CONFIG_PATH, WHIPPER_BINARY_DEFAULT

# Bump this when the schema grows new keys. Migration logic lives in
# _migrate() below — currently a no-op because we're at v1.
SCHEMA_VERSION: int = 1

# Computed once at import time. If the user's HOME changes mid-process,
# the GUI needs a restart — same as every other XDG-aware application.
_DEFAULT_OUTPUT_DIR: Path = Path.home() / "Music" / "rips"
_DEFAULT_WORKING_DIR: Path = Path.home() / ".cache" / "whipper-gui"

# Whipper's own default templates (see `whipper cd rip --help`). Kept
# inline so future-you doesn't need to grep the codebase for the format
# specifiers.
_DEFAULT_TRACK_TEMPLATE: str = "%A - %d/%t. %a - %n"
_DEFAULT_DISC_TEMPLATE: str = "%A - %d/%A - %d"

log = logging.getLogger(__name__)


@dataclass
class Config:
    """The persisted user configuration. Attributes mirror TOML keys 1:1."""

    # --- Output locations ---
    output_dir: str = field(default_factory=lambda: str(_DEFAULT_OUTPUT_DIR))
    working_dir: str = field(default_factory=lambda: str(_DEFAULT_WORKING_DIR))

    # --- Whipper rip templates ---
    track_template: str = _DEFAULT_TRACK_TEMPLATE
    disc_template: str = _DEFAULT_DISC_TEMPLATE

    # --- Tool paths (overrides for the dependency subsystem) ---
    # User can re-point these in Settings if the defaults are wrong.
    whipper_path: str = field(default_factory=lambda: str(WHIPPER_BINARY_DEFAULT))
    metaflac_path: str = "metaflac"  # relies on PATH by default

    # --- Rip parameters ---
    # Informational only; whipper.conf is authoritative per the brief.
    # Surfaced here so Settings can display what the GUI thinks is in
    # effect. read_offset is in samples, signed.
    read_offset: int = 0

    # --- UI toggles ---
    auto_launch_picard: bool = False

    # --- Schema bookkeeping ---
    schema_version: int = SCHEMA_VERSION


def load() -> Config:
    """Return the current config, creating it with defaults if missing.

    On first run this writes the defaults file before returning so the
    user has something to edit in Settings.
    """
    if not CONFIG_PATH.exists():
        log.info("config file missing; creating defaults at %s", CONFIG_PATH)
        cfg = Config()
        save(cfg)
        return cfg

    with CONFIG_PATH.open("rb") as f:
        raw = tomllib.load(f)

    raw = _migrate(raw)

    # Drop unknown keys so an older binary reading a newer file doesn't
    # crash. Log so we know it happened — silent drops would be worse.
    known = {f.name for f in Config.__dataclass_fields__.values()}
    unknown = set(raw) - known
    if unknown:
        log.warning("unknown config keys ignored: %s", sorted(unknown))
    filtered = {k: v for k, v in raw.items() if k in known}

    return Config(**filtered)


def save(cfg: Config) -> None:
    """Atomically write `cfg` to CONFIG_PATH.

    Atomicity matters: a SIGKILL or power loss between `open` and
    `close` of the real file would otherwise leave a half-written TOML.
    We write to a sibling temp file and rename — `os.replace` is atomic
    on POSIX.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    tmp = CONFIG_PATH.with_suffix(".tmp")
    with tmp.open("wb") as f:
        tomli_w.dump(asdict(cfg), f)
    os.replace(tmp, CONFIG_PATH)
    log.debug("config saved to %s", CONFIG_PATH)


def _migrate(raw: dict) -> dict:
    """Apply schema migrations in-place. Currently a no-op (v1).

    When SCHEMA_VERSION bumps, chain per-version mutations here. Each
    migration reads `raw["schema_version"]`, transforms `raw`, and bumps
    the version. Keep individual steps small so they're easy to review.
    """
    version = int(raw.get("schema_version", 1))
    if version == 1:
        return raw
    # Future migrations slot in here. Unknown future versions get a
    # warning and v1 treatment — better than crashing the GUI.
    log.warning("unknown schema_version=%s; treating as v1", version)
    return raw
