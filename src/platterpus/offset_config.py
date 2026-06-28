"""Detect whether a usable optical-drive read offset is configured.

whipper refuses to rip until a read offset is known (it errors with
"drive offset unconfigured"). An offset can come from one of two places:

  * whipper's own `whipper.conf`, written by the drive-setup wizard's
    `whipper offset find` (whipper is authoritative for it), or
  * the GUI's `--offset` override (Config.override_read_offset), which lets
    a user set the value by hand when they can't run auto-detection (no
    AccurateRip disc) — we pass it as `--offset N` at rip time.

This module answers "is either present?" so the GUI can offer first-run
calibration only when it's actually needed. Pure stdlib + injectable path
so it's trivially testable; no whipper.conf authoring happens here (per
PLANNING.md KDD-15, the GUI never hand-writes that file).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from platterpus.paths import WHIPPER_CONFIG_PATH

log = logging.getLogger(__name__)

# A section header `[name]` and a `read_offset = N` key=value. whipper writes
# the offset under a `[drive:...]` section, keying each drive as
# `[drive:<vendor%20model%20…>]` (the id is URL-quoted), so we decode it for
# display. One scanner (`_iter_conf_offsets`) feeds both the "is any offset
# set?" check and the per-drive read-out below — see the note there.
_SECTION_RE = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
_OFFSET_KV = re.compile(r"^\s*read_offset\s*=\s*(?P<val>-?\d+)\s*$")
_DRIVE_PREFIX = "drive:"


def _read_conf_text(conf_path: Path) -> str | None:
    """Read whipper.conf as UTF-8, or None if it's missing/unreadable.

    The single read-or-give-up step both parses below share, so the
    "missing file vs unreadable file (logged)" handling lives in one place.
    A missing file is a normal first-run state (silent None); an unreadable
    one is worth a log line.
    """
    try:
        return conf_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:  # unreadable file — treat as "not configured"
        log.warning("could not read %s: %s", conf_path, exc)
        return None


def _iter_conf_offsets(text: str) -> Iterator[tuple[str | None, int]]:
    """Yield ``(section_name, offset_value)`` for every read_offset assignment.

    `section_name` is the most recent `[section]` header (None before any).
    This is the ONE place that walks whipper.conf for offsets; the two public
    functions differ only in how they *filter* what it yields — neither
    re-implements the scan, so they can't drift apart.
    """
    current_section: str | None = None
    for line in text.splitlines():
        section = _SECTION_RE.match(line)
        if section:
            current_section = section.group("name")
            continue
        kv = _OFFSET_KV.match(line)
        if kv:
            yield current_section, int(kv.group("val"))


def whipper_conf_has_offset(conf_path: Path = WHIPPER_CONFIG_PATH) -> bool:
    """True if whipper.conf exists and assigns a read_offset for some drive."""
    text = _read_conf_text(conf_path)
    if text is None:
        return False
    return any(True for _section, _value in _iter_conf_offsets(text))


def is_offset_configured(
    override_read_offset: bool,
    conf_path: Path = WHIPPER_CONFIG_PATH,
) -> bool:
    """True if a read offset will reach whipper from either source.

    `override_read_offset` is Config.override_read_offset — when set, the GUI
    passes `--offset` and whipper.conf is irrelevant.
    """
    return bool(override_read_offset) or whipper_conf_has_offset(conf_path)


@dataclass(frozen=True)
class WhipperConfOffset:
    """One per-drive read offset whipper has persisted, for display.

    `drive` is the human-readable drive id (whipper's URL-quoted section name,
    decoded); `offset` is the signed sample offset whipper will apply to that
    drive when the GUI does *not* pass `--offset`.
    """

    drive: str
    offset: int


def read_drive_offsets(
    conf_path: Path = WHIPPER_CONFIG_PATH,
) -> list[WhipperConfOffset]:
    """Parse whipper.conf's per-drive `read_offset` values — the offsets
    whipper will *actually* apply (authoritative when the GUI isn't overriding).

    This is the trust check the GUI's own stored `read_offset` can't give: the
    config file may have been written by the wizard or hand-edited and drifted
    from what the GUI thinks. **Never raises** — a missing/unreadable/malformed
    file just yields `[]`, like the other config probes here.
    """
    text = _read_conf_text(conf_path)
    if text is None:
        return []
    offsets: list[WhipperConfOffset] = []
    for section, value in _iter_conf_offsets(text):
        if section and section.startswith(_DRIVE_PREFIX):
            raw_id = section[len(_DRIVE_PREFIX) :]
            offsets.append(
                WhipperConfOffset(
                    drive=unquote(raw_id).strip() or raw_id,
                    offset=value,
                )
            )
    return offsets


def describe_conf_offsets(conf_path: Path = WHIPPER_CONFIG_PATH) -> str:
    """A one-line, human summary of whipper.conf's per-drive read offsets.

    Used by the Settings dialog and `--doctor` to show what whipper will apply,
    rather than the GUI's stored copy. Never raises.
    """
    offsets = read_drive_offsets(conf_path)
    if not offsets:
        return "none set"
    return "; ".join(f"{o.drive} → {o.offset:+d}" for o in offsets)
