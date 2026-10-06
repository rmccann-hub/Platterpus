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

import hashlib
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


#: Released peer laps our gate refuses for **one named rule alone**, pinned by the
#: sha256 of their exact bytes. **Not a pre-format exemption, and kept apart from**
#: :data:`_PRE_FORMAT_INBOUND` **for that reason**: these laps were written under
#: the format, our checker is right to refuse them, and a sent lap is never edited
#: (§4a), so the miss is recorded rather than repaired, as
#: ``handshake.INBOUND_HELD_EXEMPT_SHA256`` records one of ours. Each entry is
#: excused only while (1) its bytes are unchanged, (2) the named rule is the ONLY
#: problem ``--check`` finds in it, and (3) once we have sent a later lap in the
#: same round, the first such lap names the file and the rule: the finding goes to
#: the peer, which is what "answer the lap" means in the sweep's message.
#:
#: Each value is (sha256, rule). The rule is matched in every refusal by the exact
#: text ``--check`` writes for it (:data:`_RULE_TEXT`), so a second, different
#: problem in a pinned lap is never excused under the first one's name.
#:
#: * ``round-30-lap-09.md`` (R6) — the fork's round 30 lap 9
#:   (``cyanrip@f6d72c0``), released 2026-10-05: its S41 and S42 are WILLs with no
#:   ``verdict: GO`` and its prose has no pre-commit. Found by this sweep on
#:   filing; raised in our round 30 lap 10.
#: * ``round-30-lap-15.md`` (C44) — the fork's round 30 lap 15
#:   (``cyanrip@5e75eac``), released 2026-10-06: it declares ``GO`` at protocol 6
#:   without ``HANDSHAKE-AGREED-CHANGES``. Found by this sweep on filing; raised in
#:   our round 30 lap 16 (S11), which asks for their lap 17 with the field,
#:   because both gates read the round's close off it.
_MISSES_ANSWERED: Final[dict[str, tuple[str, str]]] = {
    "round-30-lap-09.md": (
        "be2f763b63ef77b6989bedcaebd2e70b0d08c9754af2f2408ebe0418293cce03",
        "R6",
    ),
    "round-30-lap-15.md": (
        "b3e9117263f1005ca066956899d4ddb0d73a54397fd2402e6f28fa51c0e15511",
        "C44",
    ),
}

#: The text ``--check`` writes in a refusal for each rule a miss may be pinned
#: under. Read from the checker's own messages, not paraphrased: R6's refusals
#: carry ``": R6: "`` and C44's carry ``"row C44"``.
_RULE_TEXT: Final[dict[str, str]] = {"R6": " R6: ", "C44": "row C44"}


def _is_answered_miss(name: str, problems: list[str]) -> bool:
    """Whether ``name``'s refusal is exactly a pinned, answered miss."""
    pinned = _MISSES_ANSWERED.get(name)
    if pinned is None:
        return False
    sha, rule = pinned
    actual = hashlib.sha256((_INBOUND / name).read_bytes()).hexdigest()
    return actual == sha and all(_RULE_TEXT[rule] in p for p in problems)


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
        if name not in _PRE_FORMAT_INBOUND and not _is_answered_miss(name, problems)
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


def test_every_pinned_miss_is_exact_and_answered(hs: ModuleType) -> None:
    """Each pinned miss still exists with its bytes, is still refused for its rule
    and nothing else, and is answered by name in our first later lap of its round,
    once one exists. A pin whose answer never went out is a finding we kept."""
    assert _MISSES_ANSWERED, "nothing pinned: delete this test with the dict"
    assert {rule for _sha, rule in _MISSES_ANSWERED.values()} <= set(_RULE_TEXT)
    refused = _refused(hs, _INBOUND)
    for name, (sha, rule) in _MISSES_ANSWERED.items():
        path = _INBOUND / name
        assert path.is_file(), f"pinned {rule} miss {name} no longer exists"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, (
            f"{name}'s bytes changed: a sent lap is never edited (§4a)"
        )
        problems = refused.get(name, [])
        assert problems, f"{name} now passes --check: remove its pin"
        assert all(_RULE_TEXT[rule] in p for p in problems), problems
        named = hs.name_round_and_lap(path)
        assert named is not None, name
        later = sorted(
            (lap, candidate)
            for sub in ("outbound", "verified")
            for candidate in (_REPO_ROOT / "docs" / "handshake" / sub).glob(
                f"round-{named[0]:02d}-lap-*.md"
            )
            if (got := hs.name_round_and_lap(candidate)) is not None
            and (lap := got[1]) > named[1]
        )
        if not later:
            continue  # our next lap of this round has not been written yet
        answer = later[0][1].read_text(encoding="utf-8")
        assert name in answer and rule in answer, (
            f"our first lap after {name}, {later[0][1].name}, does not raise its "
            f"{rule} miss by name"
        )


def test_a_pinned_miss_excuses_only_its_own_rule() -> None:
    """The excuse must not stretch: lap 15's C44 pin does not cover an R6 refusal,
    and a refusal that names neither rule is not excused at all."""
    c44 = (
        "round-30-lap-15.md: declares GO but a GO file declaring HANDSHAKE-PROTOCOL"
        ": 6 must declare HANDSHAKE-AGREED-CHANGES, and it is absent (§5e, row C44)"
    )
    r6 = "round-30-lap-15.md:1: R6: lap 15 carries no pre-commit"
    assert _is_answered_miss("round-30-lap-15.md", [c44])
    assert not _is_answered_miss("round-30-lap-15.md", [c44, r6])
    assert not _is_answered_miss("round-30-lap-15.md", ["some other problem"])
    assert not _is_answered_miss("round-30-lap-09.md", [c44])
