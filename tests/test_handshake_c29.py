"""Row C29 in our gate, and the emitter that cannot under-declare.

**Why this exists (2026-10-13).** Our round 32 lap 4 declared
``HANDSHAKE-PROTOCOL: 7`` after the fork's lap 3 of the same round had declared 8.
Row C29 refuses exactly that (a lap may not under-declare the rules it is read by),
and the fork's gate refused it. Ours did not, for two reasons fixed together:

* our gate had no C29 check at all, so ``--check`` passed the lap; and
* ``--emit`` wrote :data:`handshake.DECLARED_PROTOCOL` alone, which still said 7.

The fixes: :func:`handshake.c29_problem` in ``--check``, and
:func:`handshake.protocol_to_declare`, which never answers less than the highest
version any lap of the round already declares. Both are pinned here against a
record built in a temporary directory, and against the real record, where lap 4 is
the one file C29 refuses.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_SCRIPT: Final[Path] = _REPO_ROOT / "scripts" / "handshake.py"


@pytest.fixture(scope="module")
def hs() -> ModuleType:
    """The real gate, loaded by path the way the other handshake tests load it."""
    if "handshake" in sys.modules:
        return sys.modules["handshake"]
    spec = importlib.util.spec_from_file_location("handshake", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["handshake"] = module
    spec.loader.exec_module(module)
    return module


def _lap(round_number: int, lap: int, protocol: int) -> str:
    """The three wire fields C29 reads, at column 0."""
    return (
        f"HANDSHAKE-ROUND: {round_number}\n"
        f"HANDSHAKE-LAP: {lap}\n"
        f"HANDSHAKE-PROTOCOL: {protocol}\n"
    )


@pytest.fixture
def record(hs: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty record in three directories, standing in for ours."""
    for name, attr in (
        ("outbound", "OUTBOUND_DIR"),
        ("inbound", "INBOUND_DIR"),
        ("verified", "VERIFIED_DIR"),
    ):
        folder = tmp_path / name
        folder.mkdir()
        monkeypatch.setattr(hs, attr, folder)
    return tmp_path


def _write(record: Path, side: str, round_number: int, lap: int, protocol: int) -> Path:
    path = record / side / f"round-{round_number:02d}-lap-{lap:02d}.md"
    path.write_text(_lap(round_number, lap, protocol), encoding="utf-8")
    return path


def test_a_lap_declaring_less_than_an_earlier_lap_is_refused(
    hs: ModuleType, record: Path
) -> None:
    """Round 32 as it happened: their lap 3 at 8, our lap 4 at 7."""
    theirs = _write(record, "inbound", 32, 3, 8)
    ours = _write(record, "outbound", 32, 4, 7)
    problem = hs.c29_problem(ours, ours.read_text(encoding="utf-8"))
    assert problem is not None and "C29" in problem
    assert theirs.name in problem and ": 7" in problem
    assert hs.c29_problem(theirs, theirs.read_text(encoding="utf-8")) is None


def test_the_FILE_is_refused_and_a_later_lap_declaring_the_record_passes(
    hs: ModuleType, record: Path
) -> None:
    """The reading we proposed in round 32 lap 6: C29 refuses the lap that
    under-declares, not every later lap of its round. A lap 6 at 8 is clean even
    with the refused lap 4 still in the record."""
    _write(record, "inbound", 32, 3, 8)
    _write(record, "outbound", 32, 4, 7)
    later = _write(record, "outbound", 32, 6, 8)
    assert hs.c29_problem(later, later.read_text(encoding="utf-8")) is None


def test_an_earlier_lap_declaring_LESS_does_not_refuse_a_later_one(
    hs: ModuleType, record: Path
) -> None:
    """Declaring MORE than an earlier lap is how a round moves to a new protocol."""
    _write(record, "outbound", 32, 2, 7)
    later = _write(record, "inbound", 32, 3, 8)
    assert hs.c29_problem(later, later.read_text(encoding="utf-8")) is None


def test_rounds_before_C29_binds_are_not_judged(hs: ModuleType, record: Path) -> None:
    """Round 8 broke this rule wholesale before it was a rule; the fork's gate
    starts at the same round ours does."""
    before = hs.C29_FROM_ROUND - 1
    _write(record, "inbound", before, 3, 8)
    ours = _write(record, "outbound", before, 4, 7)
    assert hs.c29_problem(ours, ours.read_text(encoding="utf-8")) is None


def test_the_emitter_declares_at_least_the_records_highest_version(
    hs: ModuleType, record: Path
) -> None:
    """`--emit` must not be able to write lap 4's mistake again."""
    assert hs.protocol_to_declare(32) == hs.DECLARED_PROTOCOL, "an empty record"
    _write(record, "inbound", 32, 3, hs.DECLARED_PROTOCOL + 1)
    assert hs.protocol_to_declare(32) == hs.DECLARED_PROTOCOL + 1
    assert hs.protocol_to_declare(33) == hs.DECLARED_PROTOCOL, "another round"
    skeleton = hs.emit_outbound(32)
    assert f"HANDSHAKE-PROTOCOL: {hs.DECLARED_PROTOCOL + 1}\n" in skeleton


def test_check_reports_C29_and_the_real_record_refuses_only_our_lap_4(
    hs: ModuleType,
) -> None:
    """Against the committed record: lap 4 is refused for C29 by `--check`, and
    no other file of any round from 25 on is (a floor of files examined, so an
    empty glob cannot pass)."""
    examined = 0
    refused: list[str] = []
    for directory in (hs.OUTBOUND_DIR, hs.INBOUND_DIR, hs.VERIFIED_DIR):
        for path in sorted(directory.glob("round-*.md")):
            text = path.read_text(encoding="utf-8")
            number = hs.declared_round(text)
            if number is None or number < hs.C29_FROM_ROUND:
                continue
            examined += 1
            if hs.c29_problem(path, text) is not None:
                refused.append(f"{path.parent.name}/{path.name}")
    assert examined >= 40, f"only {examined} laps from round 25 on were examined"
    assert refused == ["outbound/round-32-lap-04.md"], refused
    lap4 = hs.OUTBOUND_DIR / "round-32-lap-04.md"
    problems = hs.check_wire_header(lap4)
    assert any("C29" in p for p in problems), problems
