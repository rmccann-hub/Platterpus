"""Persistence for the per-drive profile ledger (:mod:`drive_profiles`).

A thin store over a single JSON file keyed by drive fingerprint. It mirrors
``config.py``'s proven discipline — best-effort, never-raising load and an
atomic temp-file + ``os.replace`` save — because a corrupt *cache* of hardware
facts must never block a rip or crash the GUI.

JSON (not the project's usual TOML) because this is a machine-managed, nested
``dict[fingerprint, profile]`` that is never hand-edited; stdlib ``json`` reads
*and* writes it, so the write path needs no extra dependency.

This is the only writer of ``drive_profiles.json``. The single recorder in the
main window funnels every learned fact through it (no scattered writes), the
same "one subsystem" discipline Critical Rule #6 applies to dependency checks.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from platterpus import paths
from platterpus.drive_profiles import (
    Confidence,
    DriveProfile,
    OffsetRecord,
    OffsetSource,
)

log = logging.getLogger(__name__)


def _default_path() -> Path:
    """The drive-profiles path, read live so tests can redirect it.

    Resolved through the ``paths`` module (not a bound import) so an autouse
    test fixture monkeypatching ``platterpus.paths.DRIVE_PROFILES_PATH`` keeps
    the suite from touching the real user config dir.
    """
    return paths.DRIVE_PROFILES_PATH


# Bumped when the on-disk shape changes; _migrate() upgrades older files. A
# file from a *newer* version is treated as current (with a warning) rather
# than crashing an older build — same tolerance as config.py.
SCHEMA_VERSION: int = 1


# --- (de)serialization helpers (never raise) --------------------------------


def _offset_to_dict(record: OffsetRecord) -> dict[str, object]:
    return {
        "value": record.value,
        "source": record.source.value,
        "confidence": record.confidence.value,
        "detected_at": record.detected_at,
    }


def _offset_from_dict(raw: object) -> OffsetRecord | None:
    """Rebuild an OffsetRecord from a JSON object; None if it isn't usable.

    Unknown enum strings decode to UNKNOWN/LOW (the enums' ``_missing_``), and a
    non-int value drops the record rather than raising — the never-raises
    contract reaches into deserialization.
    """
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    if not isinstance(value, int):
        return None
    return OffsetRecord(
        value=value,
        source=OffsetSource(raw.get("source", "unknown")),
        confidence=Confidence(raw.get("confidence", "low")),
        detected_at=str(raw.get("detected_at", "")),
    )


def _profile_to_dict(profile: DriveProfile) -> dict[str, object]:
    """Serialize a profile WITHOUT its fingerprint (that's the map key)."""
    cache_source = profile.cache_defeat_source
    return {
        "vendor": profile.vendor,
        "model": profile.model,
        "release": profile.release,
        "serial": profile.serial,
        "wwn": profile.wwn,
        "offset": _offset_to_dict(profile.offset) if profile.offset else None,
        "cache_defeat": profile.cache_defeat,
        "cache_defeat_source": cache_source.value if cache_source else None,
        "last_seen_device": profile.last_seen_device,
        "last_seen_at": profile.last_seen_at,
    }


def _profile_from_dict(fingerprint: str, raw: object) -> DriveProfile | None:
    """Rebuild a profile from its map key + JSON object; None if unusable."""
    if not isinstance(raw, dict):
        return None
    cache_source_raw = raw.get("cache_defeat_source")
    cache_defeat = raw.get("cache_defeat")
    return DriveProfile(
        fingerprint=fingerprint,
        vendor=str(raw.get("vendor", "")),
        model=str(raw.get("model", "")),
        release=str(raw.get("release", "")),
        serial=str(raw.get("serial", "")),
        wwn=str(raw.get("wwn", "")),
        offset=_offset_from_dict(raw.get("offset")),
        cache_defeat=cache_defeat if isinstance(cache_defeat, bool) else None,
        cache_defeat_source=(
            OffsetSource(cache_source_raw) if cache_source_raw is not None else None
        ),
        last_seen_device=str(raw.get("last_seen_device", "")),
        last_seen_at=str(raw.get("last_seen_at", "")),
    )


class DriveProfileStore:
    """In-memory map of fingerprint → DriveProfile, with JSON load/save."""

    def __init__(
        self,
        profiles: dict[str, DriveProfile] | None = None,
        path: Path | None = None,
    ) -> None:
        self._profiles: dict[str, DriveProfile] = dict(profiles or {})
        # Remember where we were loaded from so save() round-trips to the same
        # file without the caller having to thread the path back through.
        self._path: Path = path if path is not None else _default_path()

    # --- queries / mutators (in-memory; caller decides when to save) --------

    def get(self, fingerprint: str) -> DriveProfile | None:
        return self._profiles.get(fingerprint)

    def upsert(self, profile: DriveProfile) -> None:
        """Insert or replace the profile for ``profile.fingerprint``."""
        self._profiles[profile.fingerprint] = profile

    def all(self) -> list[DriveProfile]:
        return list(self._profiles.values())

    # --- persistence --------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> DriveProfileStore:
        """Load the store. NEVER raises.

        A missing file is the normal first-run state (empty store). A
        corrupt/unreadable file is logged and treated as empty — and is left on
        disk, not clobbered, so it can be inspected. Unusable individual
        profiles are skipped with a log line rather than failing the whole load.
        """
        if path is None:
            path = _default_path()
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return cls(path=path)
        except OSError as exc:
            log.warning("could not read %s: %s", path, exc)
            return cls(path=path)

        try:
            raw = json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("could not parse %s (%s); starting with no profiles", path, exc)
            return cls(path=path)

        if not isinstance(raw, dict):
            log.warning("%s is not a JSON object; starting with no profiles", path)
            return cls(path=path)

        raw = _migrate(raw)

        profiles: dict[str, DriveProfile] = {}
        raw_profiles = raw.get("profiles")
        if isinstance(raw_profiles, dict):
            for fingerprint, entry in raw_profiles.items():
                profile = _profile_from_dict(str(fingerprint), entry)
                if profile is not None:
                    profiles[profile.fingerprint] = profile
                else:
                    log.warning("dropped unusable drive profile %r", fingerprint)
        return cls(profiles, path=path)

    def save(self, path: Path | None = None) -> None:
        """Atomically write the store (temp file + os.replace).

        Writes to `path`, or the path this store was loaded from. Atomicity
        matters: a crash between open and close would otherwise leave a
        half-written file that the next load would (safely) discard. Same
        pattern config.save uses.
        """
        if path is None:
            path = self._path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "profiles": {
                fp: _profile_to_dict(profile) for fp, profile in self._profiles.items()
            },
        }
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp, path)
        log.debug("drive profiles saved to %s", path)


def _migrate(raw: dict) -> dict:
    """Upgrade an older on-disk shape to the current one. Returns `raw`.

    A stub today (there is only v1), but the seam exists from day one — schema
    migrations are cheap to add now and impossible to retrofit. A file claiming
    a *newer* version is treated as current with a warning, never a crash.
    """
    version = int(raw.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION)
    if version == SCHEMA_VERSION:
        return raw
    if version > SCHEMA_VERSION:
        log.warning(
            "drive_profiles.json schema_version=%s newer than v%s; treating as current",
            version,
            SCHEMA_VERSION,
        )
    return raw
