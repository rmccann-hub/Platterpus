"""A sweep over committed files that keeps its population when evidence moves (HR-2).

Several tests sweep "every committed cyanrip log" (or every log under ``docs/``)
rather than naming one file. HR-2 moves the run folders off ``main``; each moved
file a test opens is copied byte for byte to ``tests/fixtures/evidence/<original
path>`` by ``scripts/evidence_fixtures.py``. A sweep that only globbed the live
tree would quietly shrink by every moved file and still pass on what was left,
which is the defect HR-2 §2 names. A sweep that globbed both would count each
moved file twice for as long as the original is still in the checkout.

:func:`with_moved_evidence` takes what the sweep found in the live tree and adds
the fixtures under the same original paths, so each file is counted once, read
from its fixture, and the population is the same size before the move and after.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Final

from evidence_paths import FIXTURE_ROOT

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def with_moved_evidence(live: Iterable[Path], pattern: str) -> list[Path]:
    """``live`` plus every evidence fixture matching ``pattern``, once per file.

    ``live`` is what the sweep globbed in the working tree; any of it that lies
    under the fixture root is dropped and re-added below by its original path.
    ``pattern`` is a glob relative to the repository root (``docs/**/*.log``),
    matched against the fixtures' ORIGINAL paths, so it is the same pattern the
    sweep used on the live tree. Where a moved file is still in this checkout,
    the fixture stands in for it rather than beside it. Sorted by original path.
    """
    by_original: dict[str, Path] = {}
    for path in live:
        resolved = path.resolve()
        if resolved.is_relative_to(FIXTURE_ROOT):
            continue
        by_original[resolved.relative_to(REPO_ROOT).as_posix()] = path
    for fixture in FIXTURE_ROOT.glob(pattern):
        if fixture.is_file():
            by_original[fixture.relative_to(FIXTURE_ROOT).as_posix()] = fixture
    return [by_original[key] for key in sorted(by_original)]
