# SPDX-License-Identifier: GPL-3.0-only
"""Put a proved repair on disk without ever losing the original (TASKS R43).

The last step of ``ctdb/repair.py``, and the only one that changes the user's
files. Split out because it is a different job from the arithmetic before it:
file names, links, renames and their undo, which a test drives on a real
temporary directory (``tests/test_ctdb_repair.py``).

**The order, and why.**

1. Every original is KEPT first, as ``<name>.flac.before-ctdb-repair``: a hard
   link (the same bytes under a second name, instant and atomic), or where the
   filesystem has no links (FAT and exFAT, which removable drives use) a copy
   that is compared with the original before it counts as kept. An earlier
   repair's kept original is never overwritten: the repair is refused instead.
2. Then each new file is renamed over the original's name with ``os.replace``,
   which is atomic on POSIX: a reader sees the old file or the new one, never
   half of either. The directory is synced after each rename.
3. If anything fails part-way, every rename already made is undone (the kept
   original is renamed back) and every kept copy is removed, so a failed commit
   leaves the album exactly as it was.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from pathlib import Path

from platterpus.atomic_write import fsync_directory

#: The suffix the original keeps, beside the repaired file.
BACKUP_SUFFIX: str = ".before-ctdb-repair"


class CommitRefused(Exception):
    """The commit did not happen; ``reason`` says why and ``failure`` whether a
    tool or the disk failed (True) or a guard said no (False)."""

    def __init__(self, reason: str, *, failure: bool = False) -> None:
        super().__init__(reason)
        self.reason: str = reason
        self.failure: bool = failure


def candidate_path(path: Path) -> Path:
    """The hidden temporary the new file is written to, beside the original."""
    return path.with_name(f".{path.name}.ctdb-repair.flac")


def backup_path(path: Path) -> Path:
    """Where the original is kept once a repair replaces it."""
    return path.with_name(path.name + BACKUP_SUFFIX)


def _copy_kept(path: Path, backup: Path) -> None:
    """Copy ``path`` to ``backup`` and confirm the bytes; remove the copy on any doubt."""
    try:
        shutil.copy2(path, backup)
        same = path.read_bytes() == backup.read_bytes()
    except OSError as exc:
        backup.unlink(missing_ok=True)
        raise CommitRefused(f"could not keep {path.name}: {exc}", failure=True) from exc
    if not same:
        backup.unlink(missing_ok=True)
        raise CommitRefused(f"the copy of {path.name} did not match it", failure=True)


def keep_original(path: Path) -> Path:
    """Keep the original under the backup name; refuse to overwrite an earlier one."""
    backup = backup_path(path)
    if backup.exists():
        raise CommitRefused(
            f"{backup.name} is already there from an earlier repair; it is not "
            "overwritten, so nothing is repaired"
        )
    try:
        os.link(path, backup)
    except OSError:
        _copy_kept(path, backup)
    return backup


def commit(pairs: Sequence[tuple[Path, Path]]) -> dict[Path, Path]:
    """Keep every original, then rename each ``(original, new)`` in; all or nothing.

    Returns ``{original path: where it was kept}``. Raises :class:`CommitRefused`
    with the album left as it was.
    """
    kept: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, _new in pairs:
            kept[path] = keep_original(path)
        for path, new in pairs:
            os.replace(new, path)
            replaced.append(path)
            fsync_directory(path.parent)
    except (OSError, CommitRefused) as exc:
        for path in replaced:  # put each original back under its own name
            os.replace(kept.pop(path), path)
        for backup in kept.values():
            backup.unlink(missing_ok=True)
        if isinstance(exc, CommitRefused):
            raise
        raise CommitRefused(f"could not replace the file: {exc}", failure=True) from exc
    return kept
