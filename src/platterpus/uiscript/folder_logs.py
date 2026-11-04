"""Find the one cyanrip log a scripted ``cyanrip … -D <folder>`` rip wrote this run.

The ``cyanrip`` verb runs the ripper in the rips folder
(``runner._ripper_workdir``), so a step that passes ``-D <name>`` leaves its log
in ``<rips folder>/<name>``. Two verbs read such a log back: section P3's
``expect-deemphasis-pair`` (``deemphasis_verbs.py``) and ``record-accuracy
<label> <folder>`` (``accuracy_verbs.py``, the track-3 script). They share this
one reader so the rules for *which* log is read cannot drift between them:

* the folder name is one plain path segment (:func:`folder_problem`), so it
  cannot leave the rips folder;
* only a log written since this run started counts (``since``, the run's own
  ``RunReport.started_at``), so a log from an earlier run is never graded;
* exactly one such log: none, or more than one, is a problem, never a guess;
* the log is read with its sidecar addendum (``rip_addendum.with_addendum``),
  as every read-back must be.

Thread-safe and Qt-free: the callers run it on a helper thread, because the rips
folder may be on a slow share. Never raises: anything that stops the read is the
result's ``problem``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log
from platterpus.rip_addendum import with_addendum
from platterpus.uiscript.pregap_verbs import MAX_LOG_BYTES

#: A ``-D`` folder name a verb will read: one plain path segment. No separator and
#: no leading dot, so it cannot leave the rips folder.
_FOLDER_NAME: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def folder_problem(name: str) -> str:
    """Why ``name`` cannot name a rip's ``-D`` folder, or ``""`` when it can."""
    if _FOLDER_NAME.fullmatch(name) is None:
        return (
            f"{name!r} is not a plain folder name (letters, digits, '.', '_', "
            "'-'; no '/', up to 64 characters): it names the -D folder of one "
            "rip, inside the rips folder"
        )
    return ""


@dataclass(frozen=True)
class FolderLog:
    """The one log found, or why there is none. ``problem`` empty means found."""

    path: Path | None = None
    text: str = ""
    problem: str = ""


def read_one_log(root: Path, name: str, *, since: float) -> FolderLog:
    """The one cyanrip log in ``root/name`` written at or after ``since``."""
    folder = root / name
    try:
        candidates = sorted(
            path
            for path in folder.glob("*.log")
            if path.is_file() and path.stat().st_mtime >= since
        )
    except OSError as exc:
        return FolderLog(problem=f"{folder} could not be listed ({exc})")
    logs: list[tuple[Path, str]] = []
    for path in candidates:
        try:
            if path.stat().st_size > MAX_LOG_BYTES:
                return FolderLog(
                    problem=f"{path} is over {MAX_LOG_BYTES} bytes, so it was not read"
                )
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return FolderLog(problem=f"{path} could not be read ({exc})")
        if looks_like_cyanrip_log(text):
            logs.append((path, text))
    if len(logs) != 1:
        found = "none" if not logs else ", ".join(p.name for p, _ in logs)
        return FolderLog(
            problem=(
                f"{folder} holds {len(logs)} cyanrip log(s) written since this run "
                f"started ({found}); exactly one is read"
            )
        )
    path, text = logs[0]
    return FolderLog(path=path, text=with_addendum(text, path))
