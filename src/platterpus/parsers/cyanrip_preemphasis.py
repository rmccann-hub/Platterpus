"""Reading the per-track `Preemphasis:` row of a cyanrip log, without a regex.

The row says whether the drive reported pre-emphasis on the track, which bears on
whether the audio on disk is what was mastered. `cyanrip_log` reads it here and
nowhere else. It is its own module because `cyanrip_log.py` is far past the size
the code conventions ask for, and the test that holds oversize modules to their
size refuses growth there.
"""

from __future__ import annotations

import re
from typing import Final

# The per-track `Preemphasis:` row (`cyanrip@597dee8:src/cyanrip_log.c:573`,
# `"  Preemphasis:   "`, two spaces of indent). Its VALUE is read by
# `preemphasis_text` below with string operations, not a regex (2026-10-28, on the
# owner's instruction): tests/test_regex_bounded_time.py failed a CI leg on the old
# value regex over noise at about 0.05 ms, and the owner had the regex replaced so
# it cannot flake that way again. This pattern stays only to RECOGNISE the row, for
# `cyanrip_log`'s tables that publish our consumer contract and classify real-log lines;
# it captures nothing and ends right after the label.
PREEMPHASIS_LABEL: Final[re.Pattern[str]] = re.compile(r"^\s+Preemphasis:\s")

#: The label `preemphasis_text` looks for once the indent is stripped.
_PREEMPHASIS_WORD: Final[str] = "Preemphasis:"


def preemphasis_text(line: str) -> str | None:
    r"""The value of a `Preemphasis:` row, or None when ``line`` is not one.

    Reads exactly what the regex it replaced read on any single line (no
    newline in it), `^\s+Preemphasis:\s+(?P<text>\S(?:.*\S)?|[^\S\n])\s*$`;
    tests/test_preemphasis_reads_as_the_regex_did.py keeps that regex and holds
    this function to it. In words:

    - the line must be indented (at least one blank before the label), and the
      label must be followed by at least one blank;
    - the value is what follows, with surrounding blanks removed;
    - when only blanks follow the label, the old regex took the LAST of them as
      the value (a single space, for a line of spaces), provided there were at
      least two; with one, it did not match, so this returns None.

    `str.strip`, `str.lstrip` and `str.isspace` use the same notion of a blank as
    a `str` regex's `\s`, so the two agree on tabs and non-ASCII blanks too.
    """
    if not line[:1].isspace():
        return None
    body = line.lstrip()
    if not body.startswith(_PREEMPHASIS_WORD):
        return None
    rest = body[len(_PREEMPHASIS_WORD) :]
    if not rest[:1].isspace():
        return None
    value = rest.strip()
    if value:
        return value
    # Only blanks follow the label: the old regex's `[^\S\n]` took the last one,
    # and needed one more before it for its `\s+`.
    return rest[-1] if len(rest) >= 2 else None
