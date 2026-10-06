"""Running git, and reading what a cited file says, for the lap checker.

Split out of :mod:`laplang.refs` (2026-10-06) when reading a citation learned to
decode files that are not UTF-8: resolving a reference (refs) and talking to git
and decoding its output (here) are two jobs. Every call is bounded by
:data:`GIT_TIMEOUT_S` and answers ``None`` rather than raising when git cannot be
asked, which the resolver reports as *unchecked*.
"""

from __future__ import annotations

import codecs
import subprocess
from pathlib import Path
from typing import Final

#: How long one `git` call may take. A checker that hangs is not evidence.
GIT_TIMEOUT_S: Final[float] = 30.0

#: Byte-order marks and the codec each names, longest first: UTF-32 LE's mark
#: begins with UTF-16 LE's, so the shorter one must not be tried first.
_BOMS: Final[tuple[tuple[bytes, str], ...]] = (
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


def decode_cited(data: bytes) -> str:
    """A cited file's text, whatever it was written in. Never raises.

    A citation names LINES, so what matters is that the line count is the one
    a reader of the file would see. A file with a byte-order mark is decoded by
    the codec the mark names (EAC's logs are UTF-16 LE with a mark, so their
    lines count as an editor shows them). Anything else is read as UTF-8 with
    undecodable bytes replaced: a stray byte must cost a character, never the
    check.
    """
    for mark, codec in _BOMS:
        if data.startswith(mark):
            return data.decode(codec, errors="replace")
    return data.decode("utf-8", errors="replace")


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run git in `root`. None means git could not be asked, which is unchecked.

    ``errors="replace"``: git's own output (a ref name, a path) is not promised
    to be UTF-8, and an answer we cannot decode is still an answer.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    """:func:`run_git`, with stdout left as bytes for :func:`decode_cited`."""
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
