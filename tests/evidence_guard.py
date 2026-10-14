"""Fail any test that opens run evidence at its original path (HR-2 §2).

**Why at run time.** HR-2 moves the run folders off the default branch, and from
the move on "a check refuses any new test, tool or check that opens an evidence
path". A test names an evidence file by its original path on purpose -- that is
its provenance -- and reads the fixture at ``tests/fixtures/evidence/<that path>``.
A sweep over names cannot tell that apart from a test that opens the original,
so for tests the check is on what actually happens: a Python audit hook records
every ``open`` of a path inside a moving folder
or file, and the autouse fixture in ``conftest.py`` fails the test that did it.

Before the move the originals still exist, which is exactly when this matters: a
test that read one would pass today and fail the day the folder leaves. After
the move, such a test fails anyway; this makes it fail now, with the path named.

Tools, CI and ``src/`` are covered by the static sweep in
``tests/test_no_new_evidence_readers.py``. Audit hooks cannot be removed, so this
one is installed once per process and does nothing but compare a string.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import evidence_manifest  # noqa: E402 - needs the path line above

#: Absolute originals: each moving folder, with a trailing separator.
FOLDERS: Final[tuple[str, ...]] = tuple(
    str(REPO_ROOT / f) + os.sep for f in evidence_manifest.MOVING_FOLDERS
)
#: Only `open`: a read of a file's bytes is the dependency HR-2 §2 is about. A
#: listing that walks past a moving folder (a sweep that then reads each file
#: from its fixture) is not, and one that depends on a folder's contents still
#: fails in the simulated move, which is what §2 says finds every reader.
_EVENTS: Final[frozenset[str]] = frozenset({"open"})

#: What the hook saw since the fixture last cleared it.
seen: list[str] = []


def evidence_path(raw: object) -> str | None:
    """The absolute path if `raw` names something that moves, else None."""
    if not isinstance(raw, (str, bytes, os.PathLike)):
        return None
    try:
        path = os.path.abspath(os.fsdecode(raw))  # type: ignore[arg-type]  # PathLike[str] | str | bytes
    except (TypeError, ValueError):
        return None
    folder = path + os.sep
    for moving in FOLDERS:
        if folder == moving or path.startswith(moving):
            # A README, or a specification such as lsl-amendments-1.md, stays on
            # the default branch too (HR-2 §5a, HR-2.1 a): reading it is fine.
            rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
            return None if evidence_manifest.stays_on_default(rel) else path
    return None


def _hook(event: str, args: tuple[object, ...]) -> None:
    if event in _EVENTS and args:
        hit = evidence_path(args[0])
        if hit is not None:
            seen.append(hit)


_installed: list[bool] = []


def install() -> None:
    """Install the hook once per process."""
    if not _installed:
        sys.addaudithook(_hook)
        _installed.append(True)
