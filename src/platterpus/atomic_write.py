"""Durable atomic file writes (temp → fsync → replace → fsync-dir).

Why this exists
---------------
Three places persist small state files (``config.py``, ``drive_profile_store.py``,
``rip_report.py``) and each claimed a plain temp-file + ``os.replace`` made the
write "crash- *and power-loss*-safe". That is only *half* true: ``os.replace`` is
atomic against a **process** crash (the kernel's page cache still holds the
data), but on a **power loss** the rename can reach disk while the temp file's
DATA has not — leaving a zero-length or torn file after reboot. The honest
guarantee needs ``fsync`` of the file *before* the rename and ``fsync`` of the
directory *after* it. This module is the one place that does it right, so the
durability claim in those callers' docstrings is actually true.

Never used on the GUI thread for large data — these are tiny files (< a few KB);
the ``fsync`` cost is negligible and worth the correctness.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def _fsync_dir(directory: Path) -> None:
    """Best-effort ``fsync`` of a directory so a rename into it is durable.

    Opening a directory for fsync is POSIX-specific and can fail on some
    filesystems / platforms; a failure here only weakens durability of the
    *rename* (the file data is already fsync'd), so we log and move on rather
    than fail the whole write.
    """
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        log.debug(
            "directory fsync unsupported for %s; rename durability weakened", directory
        )
    finally:
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically and durably write ``data`` to ``path``.

    Writes a sibling ``<name>.tmp``, ``flush``+``fsync``s it so the bytes are on
    disk, ``os.replace``s it over the target (atomic on POSIX), then ``fsync``s
    the parent directory so the rename itself survives a power loss. A reader (or
    a crash) ever sees either the complete old file or the complete new file —
    never a torn or empty one. Raises ``OSError`` on failure (callers that want a
    best-effort contract catch it); the ``.tmp`` may be left behind on failure,
    which the next successful write overwrites.
    """
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """``atomic_write_bytes`` for text — encode then write durably."""
    atomic_write_bytes(path, text.encode(encoding))
