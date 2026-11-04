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
_ROW = re.compile(r"^\| (R\d+) \|", re.MULTILINE)


def test_every_r_row_number_appears_once() -> None:
    numbers = _ROW.findall(_TASKS.read_text(encoding="utf-8"))
    # Floor: the table holds well over a hundred R rows, so this cannot pass by
    # reading none.
    assert len(numbers) >= 100, len(numbers)
    repeated = sorted(n for n, count in Counter(numbers).items() if count > 1)
    assert not repeated, (
        f"TASKS.md has more than one row for {repeated}: keep the current one "
        "and delete the rest (a merge of two branches is the usual cause)"
    )
