"""Each TASKS.md row number names one row (2026-11-04).

Merging parallel branches by cherry-pick left R117, R119 and R120 twice: an
open copy beside the done one, so the open-task audit read three finished rows
as still to do (and R119 had two done copies). A row number is how laps, the
CHANGELOG and commits cite a task; two rows under one number make every such
citation ambiguous. This holds the table to one row per number.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_TASKS = Path(__file__).resolve().parents[1] / "TASKS.md"
#: Closed rows move here (2026-11-16, and the R table's on 2026-11-25, TASKS
#: R233); a number used there is used, so it is never handed out again.
_ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "archive"
    / "tasks-closed-to-2026-11-16.md"
)
_ROW = re.compile(r"^\| (R\d+) \|", re.MULTILINE)


def test_every_r_row_number_appears_once() -> None:
    live = _ROW.findall(_TASKS.read_text(encoding="utf-8"))
    archived = _ROW.findall(_ARCHIVE.read_text(encoding="utf-8"))
    numbers = live + archived
    # Floors: both files hold rows, so this cannot pass by reading none.
    assert len(live) >= 50, len(live)
    assert len(numbers) >= 200, len(numbers)
    repeated = sorted(n for n, count in Counter(numbers).items() if count > 1)
    assert not repeated, (
        f"TASKS.md and its archive hold more than one row for {repeated}: keep "
        "the current one, delete the rest, and never reuse a retired number"
    )
