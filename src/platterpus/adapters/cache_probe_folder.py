"""A folder of its own for the drive-cache check, so it leaves nothing in the user's.

**Why this exists (TASKS R97, the owner's report of 2026-10-28).** The cache check
runs ``cd-paranoia -A``, and ``-A`` always writes its detailed timing log to a
file named ``cdparanoia.log`` in the folder it was started in. We started it with
no folder of its own, so the log landed wherever Platterpus had been launched:
the owner's home folder, 325 KB after one Full run, while the run's bundle kept
only the summary the tool printed. `killable.KillableCommand.run` already says a
child that writes to a relative path must be given a folder; this module is that
folder for the cache check.

**Where the folder lives.** Under Platterpus's own data folder
(`paths.LOG_DIR`, ``~/.local/share/platterpus``), not under ``/tmp``. The tool
runs inside the Distrobox container through the host-exported wrapper, and the
container shares the home folder but is not promised to share ``/tmp``; a folder
the container cannot enter would send the log back to wherever it falls back to.

**What happens to the log.** It is read back, bounded head and tail with the gap
counted (`diagnostics.bounded_output`), and returned so the caller can keep it
with the run; then the folder and everything in it are removed. A folder that
cannot be made is reported as None, and the caller does not run the tool rather
than run it somewhere it would litter.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from platterpus import diagnostics
from platterpus.paths import LOG_DIR

log = logging.getLogger(__name__)

#: The file `cd-paranoia -A` writes in its working folder.
ANALYSIS_LOG_NAME: Final[str] = "cdparanoia.log"

#: How much of that log to keep: its summary is at the end, so the tail is the
#: larger part. One Full run's log was 8,034 lines, nearly all seek timings.
_HEAD_LINES: Final[int] = 200
_TAIL_LINES: Final[int] = 400


@contextmanager
def probe_folder(base: Path | None = None) -> Iterator[Path | None]:
    """A fresh folder under ``base`` (default `paths.LOG_DIR`), removed afterwards.

    Yields None when the folder cannot be made, so the caller can decline to run
    the tool rather than run it in the user's folder.
    """
    parent = base if base is not None else LOG_DIR
    try:
        parent.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix="cacheprobe", dir=parent))
    except OSError as exc:
        log.warning(
            "cache probe: could not make a folder of its own in %s: %s", parent, exc
        )
        yield None
        return
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def take_analysis_log(folder: Path) -> str:
    """The `cdparanoia.log` the tool wrote in ``folder``, bounded, or "" if none."""
    path = folder / ANALYSIS_LOG_NAME
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        log.warning("cache probe: could not read %s: %s", path, exc)
        return ""
    return diagnostics.bounded_output(text.strip(), head=_HEAD_LINES, tail=_TAIL_LINES)
