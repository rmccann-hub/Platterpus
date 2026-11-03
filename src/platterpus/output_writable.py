"""Can Platterpus write the rip into its output folder? Asked before the rip starts.

**Why.** Nothing asked. A rip to a folder this user cannot write to (a mount
owned by root, a folder whose permissions were changed, a path where a FILE
sits where the folder should be) started the worker, then failed inside the
backend's ``mkdir`` with "unexpected error: [Errno 13] Permission denied", a
sentence that names neither the folder nor what to do. Now the rip worker asks
first, on its own thread, beside the free-space check (``disk_space``,
``RipWorker._write_refusal``), and refuses with a sentence that names the folder
and what is wrong with it.

**What is checked.** The output folder may not exist yet: the rip makes it, and
the album folder under it. So the question is asked of the NEAREST EXISTING
part of the path: it must be a folder (not a file, not a link to nothing), and
this user must be able to create entries in it (``os.access`` with ``W_OK`` and
``X_OK``, which also answers "no" on a read-only filesystem).

**Tri-state, and unknown never refuses.** When the filesystem cannot be asked
(an ``OSError`` from a stalled mount, a path no part of which exists), the
answer is "not checked": the rip goes ahead, the log says why, and the backend's
own error is still there if the write does fail. A check that refused on unknown
would stop rips it knows nothing about.

:func:`decide` is pure (it takes the facts, so a test can give it a folder this
process could write to as root); :func:`check_output_writable` gathers the facts
once and logs the answer. Never raises.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

#: What to do, said once for every refusal.
_REMEDY: str = (
    "Choose another output folder in Settings, or fix the folder's permissions."
)


@dataclass(frozen=True)
class WriteCheck:
    """The answer: ``refuse`` True, False, or None (not checked), and why."""

    refuse: bool | None
    message: str


def nearest_existing(folder: Path) -> Path | None:
    """``folder``, or its nearest parent that exists (a link counts), or None.

    ``os.path.lexists`` rather than ``Path.exists``: a link to nothing is
    something in the way of ``mkdir``, not an absent folder. May raise
    ``OSError``; :func:`check_output_writable` catches it.
    """
    candidate = folder
    while not os.path.lexists(candidate):
        if candidate == candidate.parent:
            return None
        candidate = candidate.parent
    return candidate


def decide(
    folder: Path, existing: Path | None, is_dir: bool, writable: bool
) -> WriteCheck:
    """Refuse when the nearest existing part of ``folder`` cannot take the rip. Pure.

    ``existing`` is :func:`nearest_existing`'s answer; ``is_dir`` whether it is a
    folder (following links); ``writable`` whether this user may create entries
    in it.
    """
    if existing is None:
        return WriteCheck(
            None,
            f"output folder not checked: no part of {folder} exists to ask",
        )
    if not is_dir:
        where = (
            f"{folder} exists, but it is not a folder"
            if existing == folder
            else f"{existing} is not a folder, so {folder} cannot be made inside it"
        )
        return WriteCheck(
            True, f"Cannot rip into the output folder {folder}: {where}. {_REMEDY}"
        )
    if not writable:
        where = (
            "Platterpus is not allowed to write to it"
            if existing == folder
            else f"it does not exist yet, and Platterpus is not allowed to create "
            f"it in {existing}"
        )
        return WriteCheck(
            True,
            f"Cannot rip into the output folder {folder}: {where} (permission "
            f"denied, or a read-only drive). {_REMEDY}",
        )
    return WriteCheck(
        False, f"output folder: {existing} is a folder this user can write"
    )


def check_output_writable(
    folder: Path, access: Callable[[Path, int], bool] = os.access
) -> WriteCheck:
    """:func:`decide` for a rip's output folder, asking the filesystem once, logged.

    ``access`` is ``os.access``, injectable because a test running as root is
    allowed to write everywhere. Never raises.
    """
    try:
        existing = nearest_existing(folder)
        is_dir = existing is not None and existing.is_dir()
        writable = (
            is_dir and existing is not None and access(existing, os.W_OK | os.X_OK)
        )
        result = decide(folder, existing, is_dir, writable)
    except (OSError, ValueError, TypeError) as exc:
        result = WriteCheck(
            None,
            f"output folder not checked: the filesystem under {folder} gave no "
            f"answer ({exc!r})",
        )
    if result.refuse is False:
        log.info("%s", result.message)
    else:
        log.warning("%s", result.message)
    return result
