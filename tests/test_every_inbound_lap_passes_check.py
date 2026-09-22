"""Every inbound lap in the record must pass our own ``handshake.py --check``.

**Why this exists (2026-09-22).** Rehearsing the round-opener runbook for round 24
filed a realistic lap 1 into a scratch copy of the tree: eight tests fired on
arrival, each naming a bookkeeping action. With the lap's header changed to
protocol 5 — which our gate did not yet implement — ``--check`` refused it, and the
**same eight tests fired and no ninth.** Once the bookkeeping was done the suite
would have gone green over a lap our own checker rejected. A checker that only runs
when someone remembers to run it is a comment where a check belongs.

**The eleven exemptions are history, pinned by name.** They are laps from rounds
1–8, written before the formats ``--check`` now enforces existed (the lettered
return-file sections, the round-8 identity fields, the v3 ``WITHDRAWN`` verdict).
Rounds 9 onward pass completely. The set may shrink and never grow: a new failure
is a new lap our checker refuses, which is exactly what this file exists to catch.
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
_INBOUND: Final[Path] = _REPO_ROOT / "docs" / "handshake" / "inbound"

#: Inbound laps that predate the formats ``--check`` enforces. Measured 2026-09-22:
#: 100 inbound files, 89 pass, and these 11 fail — every one from round 8 or earlier.
_PRE_FORMAT_INBOUND: Final[frozenset[str]] = frozenset(
    {
        "round-1.md",
        "round-2.md",
        "round-3.md",
        "round-6.md",
        "round-6b.md",
        "round-6c.md",
        "round-07-lap-01.md",
        "round-07-note-ripper-commit-correction.md",
        "round-08-lap-01.md",
        "round-08-lap-03.md",
        "round-08-lap-05.md",
    }
)


@pytest.fixture(scope="module")
def hs() -> ModuleType:
    spec = importlib.util.spec_from_file_location("handshake_inbound_sweep", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["handshake_inbound_sweep"] = module
    spec.loader.exec_module(module)
    return module


def _refused(hs: ModuleType, directory: Path) -> dict[str, list[str]]:
    """Every inbound lap in ``directory`` that ``--check`` refuses, with why."""
    return {
        path.name: problems
        for path in sorted(directory.glob("round-*.md"))
        if (problems := hs.check_inbound(path))
    }


def test_every_inbound_lap_passes_our_own_check(hs: ModuleType) -> None:
    files = sorted(_INBOUND.glob("round-*.md"))
    # Floor: a moved directory or a broken glob must not pass by finding nothing.
    assert len(files) >= 90, f"only {len(files)} inbound files found under {_INBOUND}"
    refused = {
        name: problems
        for name, problems in _refused(hs, _INBOUND).items()
        if name not in _PRE_FORMAT_INBOUND
    }
    assert not refused, (
        "inbound lap(s) in the record that our own `handshake.py --check` refuses — "
        "fix the checker or answer the lap, never add it to _PRE_FORMAT_INBOUND:\n  "
        + "\n  ".join(f"{name}: {problems[0]}" for name, problems in refused.items())
    )


def test_the_pre_format_exemptions_are_exact(hs: ModuleType) -> None:
    """Each exemption must still exist and still fail — an exemption that outlives
    its subject silently widens to cover whatever takes the name next."""
    refused = _refused(hs, _INBOUND)
    missing = sorted(n for n in _PRE_FORMAT_INBOUND if not (_INBOUND / n).is_file())
    assert not missing, f"exempted files no longer exist: {missing}"
    now_passing = sorted(n for n in _PRE_FORMAT_INBOUND if n not in refused)
    assert not now_passing, (
        f"{now_passing} now pass --check — remove them from _PRE_FORMAT_INBOUND"
    )
    assert len(_PRE_FORMAT_INBOUND) <= 11, "this set may only shrink"


def test_the_sweep_catches_the_lap_that_prompted_it(
    hs: ModuleType, tmp_path: Path
) -> None:
    """Non-vacuity, against the real shape: a copy of a lap the checker accepts,
    re-declared one protocol version ahead of what the gate implements."""
    source = _INBOUND / "round-23-lap-01.md"
    text = source.read_text(encoding="utf-8")
    assert not hs.check_inbound(source), "the positive control no longer passes"
    ahead = text.replace(
        "HANDSHAKE-PROTOCOL: 4\n",
        f"HANDSHAKE-PROTOCOL: {hs.PROTOCOL_VERSION + 1}\n",
        1,
    )
    assert ahead != text, "the fixture's protocol line was not rewritten"
    (tmp_path / "round-23-lap-01.md").write_text(ahead, encoding="utf-8")
    assert "round-23-lap-01.md" in _refused(hs, tmp_path)
