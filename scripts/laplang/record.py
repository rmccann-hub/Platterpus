"""The laps we hold, as this tree files them.

A statement reference into another lap resolves against the lap *we hold*: the
spec refuses a reference into a lap we do not hold, because a cited document
must be one the reader can open. In this repository our laps are under
`docs/handshake/outbound/` and the fork's, filed byte-exact, under
`docs/handshake/inbound/`, both named `round-RR-lap-NN.md`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from .grammar import read_lap
from .model import Lap, Side

LAP_DIRS: Final[dict[Side, str]] = {
    "platterpus": "docs/handshake/outbound",
    "cyanrip": "docs/handshake/inbound",
}


def lap_filename(round_number: int, lap_number: int) -> str:
    return f"round-{round_number:02d}-lap-{lap_number:02d}.md"


class Record:
    """The held laps under `root`.

    `checking` is the lap being checked, as (side, round, lap). The file at that
    position is left out of the record, because the lap under check stands in
    for it. That is how a worked example is checked against the real round with
    the real lap taken out.
    """

    def __init__(
        self, root: Path, checking: tuple[Side, int, int] | None = None
    ) -> None:
        self.root = root
        self.checking = checking
        self._cache: dict[tuple[Side, int, int], Lap | None] = {}

    def path(self, side: Side, round_number: int, lap_number: int) -> Path:
        return self.root / LAP_DIRS[side] / lap_filename(round_number, lap_number)

    def lap(self, side: Side, round_number: int, lap_number: int) -> Lap | None:
        """The held lap, parsed; None when we do not hold it."""
        key = (side, round_number, lap_number)
        if key == self.checking:
            return None
        if key not in self._cache:
            path = self.path(side, round_number, lap_number)
            self._cache[key] = read_lap(path) if path.is_file() else None
        return self._cache[key]

    def round_laps(self, round_number: int) -> list[Lap]:
        """Every held lap of the round in either direction, by lap number."""
        found: list[tuple[int, Lap]] = []
        for side, directory in LAP_DIRS.items():
            base = self.root / directory
            if not base.is_dir():
                continue
            for path in sorted(base.glob(f"round-{round_number:02d}-lap-*.md")):
                stem = path.stem.rsplit("-", 1)[-1]
                if not stem.isdigit():
                    continue
                lap = self.lap(side, round_number, int(stem))
                if lap is not None:
                    found.append((int(stem), lap))
        return [lap for _, lap in sorted(found, key=lambda pair: pair[0])]
