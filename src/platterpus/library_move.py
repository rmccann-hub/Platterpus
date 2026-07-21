"""Move a finished rip's album folder into the user's library folder.

The "auto-move completed rips to a library folder" feature (Settings →
*Move finished rips to*, empty = off): after a successful rip **and after every
post-rip check has settled** (tagging, cover art, transcode, CTDB/FLAC/derived
verification, checksums, the report's debounced re-write — the caller owns that
gate, see ``main_window_rip``), the whole album folder is relocated from the
working output directory into the library.

Pure and Qt-free by design (same shape as ``rip_compare``/``checksums``): a
single entry point that **never raises** — it returns a :class:`MoveResult`
either way, because it runs on a best-effort post-rip daemon thread where an
exception would just vanish. The move itself is ``shutil.move``: an atomic
rename on the same filesystem, a copy+delete across filesystems (a library on
another disk).

Safety rules, all tested:

* never overwrite — a name collision in the library lands in a fresh
  ``<name> (2)`` / ``(3)`` … sibling instead (same "keep both" convention as
  the known-disc overwrite dialog);
* refuse to move a folder into itself/its own subtree (a library configured
  *inside* the album folder), and refuse a source that is the library itself;
* a folder already sitting in the library is a clean no-op success.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# How many "<name> (N)" siblings to try before giving up. Two rips of one album
# in a day is plausible; ninety-nine means something is looping — stop and say so.
_MAX_SUFFIX: int = 99


@dataclass(frozen=True)
class MoveResult:
    """Outcome of a library move. ``destination`` is the album's final folder
    (set on success — including the already-in-the-library no-op); ``message``
    is a short human line for the rip log view either way."""

    ok: bool
    destination: Path | None
    message: str


def free_destination(library_dir: Path, folder_name: str) -> Path | None:
    """The first non-existing ``library_dir/<folder_name>``-style path.

    Tries the plain name, then ``<name> (2)`` … ``<name> (99)``. Returns None
    when every candidate exists (pathological — the caller reports it rather
    than overwriting anything). Pure: no filesystem writes, only existence
    probes.
    """
    plain = library_dir / folder_name
    if not plain.exists():
        return plain
    for n in range(2, _MAX_SUFFIX + 1):
        candidate = library_dir / f"{folder_name} ({n})"
        if not candidate.exists():
            return candidate
    return None


def move_album_folder(rip_dir: Path, library_dir: Path) -> MoveResult:
    """Move ``rip_dir`` (one album's folder) into ``library_dir``. Never raises.

    Every guard degrades to a ``MoveResult(ok=False, …)`` with a specific
    message — the rip itself already succeeded, so a failed move must never
    look like a failed rip, just tell the user the folder stayed put.
    """
    try:
        source = Path(rip_dir).resolve()
        library = Path(library_dir).resolve()

        if not source.is_dir():
            return MoveResult(False, None, f"rip folder not found: {rip_dir}")
        if source == library:
            # The "album folder" IS the library root — moving it into itself is
            # meaningless and a sign the caller mis-derived the folder. Refuse.
            return MoveResult(False, None, "rip folder and library folder are the same")
        if library.is_relative_to(source):
            return MoveResult(
                False,
                None,
                "library folder is inside the rip folder — refusing to move "
                "a folder into itself",
            )
        if source.parent == library:
            # Already home (e.g. output dir == library dir): clean no-op.
            return MoveResult(True, source, "rip is already in the library")

        library.mkdir(parents=True, exist_ok=True)
        destination = free_destination(library, source.name)
        if destination is None:
            return MoveResult(
                False,
                None,
                f"no free name for “{source.name}” in the library "
                f"(tried up to “{source.name} ({_MAX_SUFFIX})”)",
            )
        shutil.move(str(source), str(destination))
        log.info("moved rip %s → %s", source, destination)
        return MoveResult(True, destination, f"moved to {destination}")
    except OSError as exc:
        log.warning("library move of %s failed: %s", rip_dir, exc)
        return MoveResult(False, None, f"move failed: {exc}")
    except Exception:  # noqa: BLE001 — daemon-thread boundary: a surprise here
        # must degrade to a reported failure, never a vanished thread.
        log.exception("library move of %s failed unexpectedly", rip_dir)
        return MoveResult(False, None, "move failed unexpectedly (see log)")
