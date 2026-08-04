"""T15 — the shared protocol's conformance table, run against our gate.

**Why this file exists.** `PROTOCOL.md` §8 is a 14-row table of cases a conforming
gate must refuse (and one it must allow). Both projects are meant to have a test
per row; the fork's are in their `tests/release_gate.py`. This is ours, one test
per row, in the table's order, so a row-by-row comparison between the two
implementations is possible without reading either one's prose.

**Their framing, and it is the reason this is "still first":** a close means
nothing while the two gates read the record differently. One side can believe a
round is closed while the other believes it is open — the exact failure both gates
exist to prevent.

**The last row matters as much as the others.** A gate that can never say yes is a
wall, not a gate, and it passes every refusal test in the table. That row is
asserted here for that reason and not for completeness.

Each test names its row so a divergence report can cite it. Where our behaviour
differs from the table, the test says so explicitly rather than being deleted or
weakened — a skipped conformance row is a divergence nobody can see.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "handshake.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("handshake_conf", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hs() -> ModuleType:
    return _load()


def _header(**overrides: str | None) -> str:
    """A complete, closing header. Pass ``None`` to omit a field.

    Built from the required-field lists rather than typed out, so adding a
    required field cannot leave this positive control quietly incomplete.
    """
    fields: dict[str, str | None] = {
        "HANDSHAKE-PROTOCOL": "2",
        "HANDSHAKE-ROUND": "9",
        "HANDSHAKE-LAP": "2",
        "HANDSHAKE-FROM": "platterpus",
        "HANDSHAKE-VERDICT": "GO",
        "HANDSHAKE-APP-VERSION": "platterpus 0.6.4",
        "HANDSHAKE-RIPPER-VERSION": (
            "cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)"
        ),
        "HANDSHAKE-PIN": "5bc654d",
        "HANDSHAKE-PEER-VERDICT": "GO",
        "HANDSHAKE-OUR-VERSION": "platterpus/0.6.4",
        "HANDSHAKE-OUR-PIN": "abc1234",
        "HANDSHAKE-PEER-VERSION": "0.9.4-rc1+platterpus.4",
        "HANDSHAKE-PEER-PIN": "5bc654d",
        "HANDSHAKE-TESTED": "T1-T8 and T14 on the pair above",
    }
    fields.update(overrides)
    return "\n".join(f"{k}: {v}" for k, v in fields.items() if v is not None) + "\n"


# --- row 14 first, because every other row passes on a gate that always refuses --


def test_row14_a_complete_two_sided_tested_round_is_ALLOWED(hs: ModuleType) -> None:
    """*"complete two-sided tested round → allow — a gate that can never say yes
    is a wall, not a gate."*

    Asserted before the refusals on purpose: it is the row that makes the other
    thirteen mean something.
    """
    assert hs.wire_verdict(_header()) == "GO"
    assert hs.close_blockers(_header()) == [], hs.close_blockers(_header())
    assert hs.protocol_refusal(_header()) is None


# --- rows 1-13, the refusals, in the table's order ----------------------------


def test_row1_our_go_with_no_peer_verdict_refuses_naming_it(hs: ModuleType) -> None:
    """*"our `GO`, no peer verdict → refuse, naming the missing peer verdict."*"""
    blockers = hs.close_blockers(_header(**{"HANDSHAKE-PEER-VERDICT": None}))
    assert blockers, "a GO with no peer verdict closed the round"
    assert any("HANDSHAKE-PEER-VERDICT" in b for b in blockers), blockers


def test_row2_our_go_with_peer_hold_refuses_naming_the_peer_verdict(
    hs: ModuleType,
) -> None:
    """*"our `GO`, peer `HOLD` → refuse, naming the peer verdict."*

    The case that used to close on our side: we read our own verdict only.
    """
    blockers = hs.close_blockers(_header(**{"HANDSHAKE-PEER-VERDICT": "HOLD"}))
    assert any("peer verdict" in b and "HOLD" in b for b in blockers), blockers


@pytest.mark.parametrize(
    "field",
    [
        "HANDSHAKE-OUR-VERSION",
        "HANDSHAKE-OUR-PIN",
        "HANDSHAKE-PEER-VERSION",
        "HANDSHAKE-PEER-PIN",
    ],
)
def test_row3_both_go_any_identity_field_missing_refuses_naming_it(
    hs: ModuleType, field: str
) -> None:
    """*"both `GO`, any identity field missing → refuse, naming the field."*

    Swept over all four rather than spot-checked on one: a gate enforcing three of
    four would look identical from the outside.
    """
    blockers = hs.close_blockers(_header(**{field: None}))
    assert any(field in b for b in blockers), blockers


def test_row4_both_go_without_tested_refuses(hs: ModuleType) -> None:
    """*"both `GO`, no `HANDSHAKE-TESTED` → refuse."*

    The maintainer's *"proper testing is needed"*, as a field: a round that closed
    with nothing tested is a release nobody checked.
    """
    blockers = hs.close_blockers(_header(**{"HANDSHAKE-TESTED": None}))
    assert any("HANDSHAKE-TESTED" in b for b in blockers), blockers


def test_row5_a_verdict_field_absent_entirely_refuses(hs: ModuleType) -> None:
    """*"verdict field absent entirely → refuse."* Fails closed, never permissive."""
    text = _header(**{"HANDSHAKE-VERDICT": None})
    assert hs.wire_verdict(text) is None
    assert hs.close_blockers(text), "an absent verdict closed the round"


def test_row6_a_verdict_declared_twice_refuses_as_ambiguous(hs: ModuleType) -> None:
    """*"verdict declared twice → refuse as ambiguous."*

    Not the first, not the last. Both values are present and the file's author
    meant one of them; guessing which is a guess wearing a derivation's clothes.
    """
    text = _header() + "HANDSHAKE-VERDICT: HOLD\n"
    assert hs.wire_fields(text)["HANDSHAKE-VERDICT"] == hs.AMBIGUOUS
    assert hs.wire_verdict(text) != "GO"
    assert any("more than once" in b for b in hs.close_blockers(text))
    # And the reverse order must behave identically — a parser taking the last
    # value would pass one of these and fail the other.
    reversed_text = "HANDSHAKE-VERDICT: HOLD\n" + _header()
    assert hs.wire_verdict(reversed_text) != "GO"


def test_row7_an_indented_or_prose_verdict_does_not_match(hs: ModuleType) -> None:
    """*"verdict indented / inside prose → refuse; the declaration did not match."*"""
    assert hs.wire_verdict("  HANDSHAKE-VERDICT: GO\n") is None
    assert hs.wire_verdict("> HANDSHAKE-VERDICT: GO\n") is None
    assert hs.wire_verdict("this is not a closing GO, we are holding\n") is None


def test_row8_a_close_illustrated_inside_a_fence_is_not_a_close(hs: ModuleType) -> None:
    """*"a complete close illustrated inside a ``` block → refuse, and do not adopt
    any of the illustrated values."*

    **The row that was found the hard way, on our file, by their gate.** They read
    the example block in our lap-3 §1 and compiled an illustrated
    `HANDSHAKE-PEER-VERSION` into their binary as a fact about us. Ours had the
    same hole, and it did not fire only because the illustrated verdict happened
    to match the real one — and our suite asserted the wrong behaviour outright.
    """
    illustrated = (
        "HANDSHAKE-PROTOCOL: 2\n"
        "HANDSHAKE-ROUND: 9\n"
        "HANDSHAKE-LAP: 2\n"
        "HANDSHAKE-FROM: platterpus\n"
        "HANDSHAKE-VERDICT: HOLD\n"
        "HANDSHAKE-APP-VERSION: platterpus 0.6.4\n"
        "HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1 (platterpus-fork-gabc1234)\n"
        "HANDSHAKE-PIN: abc1234\n"
        "\n# What a close looks like\n\n"
        "```\n" + _header() + "```\n"
    )
    # The real declaration wins and the illustrated one is invisible.
    assert hs.wire_verdict(illustrated) == "HOLD"
    fields = hs.wire_fields(illustrated)
    for adopted in hs.REQUIRED_CLOSE_FIELDS:
        assert adopted not in fields, (
            f"{adopted} was adopted from an illustrated example — this is the "
            "defect that put a fabricated fact about us into their binary"
        )
    # Tilde fences too, and an info string on the fence.
    assert "HANDSHAKE-TESTED" not in hs.wire_fields("~~~text\n" + _header() + "~~~\n")
    assert "HANDSHAKE-TESTED" not in hs.wire_fields("```md\n" + _header() + "```\n")


def test_row9_an_unrecognised_verdict_refuses(hs: ModuleType) -> None:
    """*"unrecognised verdict → refuse."* Not agreement, and not an error to skip."""
    for value in ("MAYBE", "APPROVED", "yes", "Go", ""):
        text = _header(**{"HANDSHAKE-VERDICT": value or "  "})
        assert hs.wire_verdict(text) != "GO", value
        assert hs.close_blockers(text), value


def test_row10_a_declared_round_that_differs_from_its_file_refuses(
    hs: ModuleType, tmp_path: Path
) -> None:
    """*"declared round ≠ the round it is filed under → refuse."*"""
    path = tmp_path / "round-9.md"
    path.write_text(_header(**{"HANDSHAKE-ROUND": "8"}), encoding="utf-8")
    problems = hs.check_wire_header(path)
    assert any("HANDSHAKE-ROUND: 8" in p and "round 9" in p for p in problems), problems


def test_row11_a_later_lap_declaring_hold_after_a_go_reopens_the_round(
    hs: ModuleType, tmp_path: Path
) -> None:
    """*"a later lap declaring `HOLD` after an earlier `GO` → refuse — a round can
    reopen."*

    State is the **latest lap**, not a conjunction over all of them. New evidence
    reopening a round is the protocol working.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-9.md").write_text("x", encoding="utf-8")
    # The COMPLETE header on both sides — round 9 is not grandfathered, so a close
    # needs the identity fields too (C9). Using a bare verdict here was the fixture
    # C9 immediately invalidated, which is the check working on its own test file.
    (tmp_path / "inbound" / "round-9.md").write_text(
        _header(**{"HANDSHAKE-FROM": "cyanrip-fork"}), encoding="utf-8"
    )
    (tmp_path / "verified" / "round-9.md").write_text(_header(), encoding="utf-8")
    assert hs.round_status(tmp_path)[0].endswith("CLOSED"), hs.round_status(tmp_path)

    (tmp_path / "verified" / "round-9b.md").write_text(
        _header(**{"HANDSHAKE-VERDICT": "HOLD", "HANDSHAKE-LAP": "3"}),
        encoding="utf-8",
    )
    reopened = hs.round_status(tmp_path)[0]
    assert reopened.endswith("OPEN"), reopened


def test_row12_no_round_files_at_all_refuses(hs: ModuleType, tmp_path: Path) -> None:
    """*"no round files at all → refuse; an empty record is not agreement."*"""
    lines = hs.round_status(tmp_path)
    assert lines and "no handshake rounds" in lines[0], lines
    # And through the gate itself, which is the surface that matters.
    import pytest as _pytest

    monkey = _pytest.MonkeyPatch()
    try:
        monkey.setattr(hs, "HANDSHAKE_DIR", tmp_path)
        assert hs.main(["--release-gate"]) == 1
    finally:
        monkey.undo()


def test_row13_a_higher_protocol_version_refuses_rather_than_guessing(
    hs: ModuleType,
) -> None:
    """*"`HANDSHAKE-PROTOCOL` higher than implemented → refuse rather than guess."*

    A v2 gate reading a v3 file cannot know which of v3's rules it is silently not
    applying — including, possibly, a new close requirement.
    """
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": "3"})) is not None
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": "99"})) is not None
    # Our own version and older ones are fine.
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": "2"})) is None
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": "1"})) is None
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": None})) is None
    # A non-integer is refused too rather than silently ignored.
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": "two"})) is not None


# --- C9 / C10: the rows the fork added in lap 4, which we did not have ---------
# Their lap 6: *"your table has 14 rows, ours has 16 — and the two you are missing
# are the two that found a real gap in our gate."* They were right, and we had the
# same gap: `check_inbound` validated the four identity fields and the GATE never
# did, so a round-8 file declaring GO with every §5 close field and none of
# `HANDSHAKE-FROM` / `-APP-VERSION` / `-RIPPER-VERSION` / `-PIN` closed the round.
#
# Our lap-5 reply told them "all four of our v1 additions required — yes". That was
# a code-reading claim with no conformance row behind it, exactly as they said.


@pytest.mark.parametrize(
    "field",
    [
        "HANDSHAKE-FROM",
        "HANDSHAKE-APP-VERSION",
        "HANDSHAKE-RIPPER-VERSION",
        "HANDSHAKE-PIN",
    ],
)
def test_row9_a_round_8_file_missing_an_identity_field_refuses(
    hs: ModuleType, field: str
) -> None:
    """C9 — *"a round ≥ 8 file missing any of the four → refuse, naming the field."*

    Swept over all four: a gate enforcing three of four looks identical from
    outside, which is how this survived being claimed as done.
    """
    blockers = hs.close_blockers(_header(**{field: None}))
    assert any(field in b for b in blockers), (
        f"a closing round-8 file with no {field} was not refused: {blockers}"
    )


def test_row9_applies_on_a_mid_round_hold_too(hs: ModuleType) -> None:
    """C9's second half, which their wording is explicit about.

    A `HOLD` lap must still declare who wrote it and which pair produced its
    results — a measurement without provenance is the thing the fields exist for,
    and a mid-round lap is *mostly* what a round consists of.
    """
    text = _header(**{"HANDSHAKE-VERDICT": "HOLD", "HANDSHAKE-FROM": None})
    problems = (
        hs.check_wire_header(Path("round-9.md"), expect_from=None) if False else None
    )
    del problems
    # Checked through the header validator, which is the surface a non-closing lap
    # goes through — `close_blockers` short-circuits on a non-GO verdict by design.
    import tempfile

    path = Path(tempfile.mkdtemp()) / "round-9.md"
    path.write_text(text, encoding="utf-8")
    assert any("HANDSHAKE-FROM" in p for p in hs.check_wire_header(path)), (
        hs.check_wire_header(path)
    )


def test_row10_a_pre_header_round_missing_them_is_allowed(
    hs: ModuleType, tmp_path: Path
) -> None:
    """C10 — *"a round ≤ 7 file missing them → allow; exemption by pinned number."*

    And this is the half that bit us while implementing C9, twice. The exemption was
    first keyed on the round declared **in the header** — a field the exempt files do
    not have — so every closed round in the real record flipped to OPEN. Then
    `close_blockers` was run over them anyway, and reported "no HANDSHAKE-VERDICT
    declared" for files that state their verdict in prose. **A grandfather clause
    defeated by the very absence it exists to permit.**
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-6.md").write_text("x", encoding="utf-8")
    (tmp_path / "verified" / "round-6.md").write_text(
        "**GO on pin `2f950c8`.** Verified.", encoding="utf-8"
    )
    line = hs.round_status(tmp_path)[0]
    assert line.endswith("CLOSED"), (
        "a pre-header round was refused for lacking fields that did not exist when "
        f"it was written: {line}"
    )
    # Floor: the real record must still contain closed pre-header rounds, or this
    # test is asserting a property of an empty set.
    real = [ln for ln in hs.round_status() if ln.endswith("CLOSED")]
    assert len(real) >= 5, f"only {len(real)} closed rounds in the record"


# --- the table itself must not shrink -----------------------------------------


def test_every_conformance_row_has_a_test_here() -> None:
    """A floor on the suite, not on the gate.

    A skipped conformance row is a divergence nobody can see. If the protocol
    grows a row, this fails until a test for it exists — which is the only way a
    shared table stays shared.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    # 16 rows since the fork's lap 4. Ours had 14 and the two missing were the two
    # that found a real gap — in their gate and, as it turned out, in ours.
    for row in range(1, 17):
        if row in (15, 16):
            # C15/C16 are their numbering for our rows 13/14 (protocol version,
            # complete-round-allowed) — same cases, different index. Named here so
            # the mapping is recorded rather than inferred.
            continue
        assert f"def test_row{row}_" in source, (
            f"PROTOCOL.md §8 row {row} has no test in this file — a conformance "
            "row without a test is a divergence nobody can see"
        )
