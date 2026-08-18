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
import re
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
        # Long enough to clear the evidence floor. It read 'T1-T8 and T14 on the pair above' — 31 characters
        # naming nothing in particular — and the close/status tests leaned on that
        # passing. `evidence_blockers` (2026-08-18) refuses content-free evidence, so
        # this went red: the gate was correct and the STAND-IN WAS MORE PERMISSIVE THAN
        # THE PRODUCT. CLAUDE.md, "what does my stand-in do that the real thing does
        # not?" — the answer here was "accept a close with no evidence".
        "HANDSHAKE-TESTED": (
            "T1-T8 and T14 on the pair above — the full suite green under CI's import path, with "
            "PYTEST_EXIT read from pytest's own status. NOT tested: any drive."
        ),
    }
    fields.update(overrides)
    return "\n".join(f"{k}: {v}" for k, v in fields.items() if v is not None) + "\n"


# --- row 14 first, because every other row passes on a gate that always refuses --


def test_C16_a_complete_two_sided_tested_round_is_ALLOWED(hs: ModuleType) -> None:
    """*"complete two-sided tested round → allow — a gate that can never say yes
    is a wall, not a gate."*

    Asserted before the refusals on purpose: it is the row that makes the other
    thirteen mean something.
    """
    assert hs.wire_verdict(_header()) == "GO"
    assert hs.close_blockers(_header()) == [], hs.close_blockers(_header())
    assert hs.protocol_refusal(_header()) is None


# --- rows 1-13, the refusals, in the table's order ----------------------------


def test_C1_our_go_with_no_peer_verdict_refuses_naming_it(hs: ModuleType) -> None:
    """*"our `GO`, no peer verdict → refuse, naming the missing peer verdict."*"""
    blockers = hs.close_blockers(_header(**{"HANDSHAKE-PEER-VERDICT": None}))
    assert blockers, "a GO with no peer verdict closed the round"
    assert any("HANDSHAKE-PEER-VERDICT" in b for b in blockers), blockers


def test_C2_our_go_with_peer_hold_refuses_naming_the_peer_verdict(
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
def test_C3_both_go_any_close_field_missing_refuses_naming_it(
    hs: ModuleType, field: str
) -> None:
    """*"both `GO`, any identity field missing → refuse, naming the field."*

    Swept over all four rather than spot-checked on one: a gate enforcing three of
    four would look identical from the outside.
    """
    blockers = hs.close_blockers(_header(**{field: None}))
    assert any(field in b for b in blockers), blockers


def test_C4_both_go_without_tested_refuses(hs: ModuleType) -> None:
    """*"both `GO`, no `HANDSHAKE-TESTED` → refuse."*

    The maintainer's *"proper testing is needed"*, as a field: a round that closed
    with nothing tested is a release nobody checked.
    """
    blockers = hs.close_blockers(_header(**{"HANDSHAKE-TESTED": None}))
    assert any("HANDSHAKE-TESTED" in b for b in blockers), blockers


def test_C5_a_verdict_field_absent_entirely_refuses(hs: ModuleType) -> None:
    """*"verdict field absent entirely → refuse."* Fails closed, never permissive."""
    text = _header(**{"HANDSHAKE-VERDICT": None})
    assert hs.wire_verdict(text) is None
    assert hs.close_blockers(text), "an absent verdict closed the round"


def test_C6_a_verdict_declared_twice_refuses_as_ambiguous(hs: ModuleType) -> None:
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


def test_C7_an_indented_or_prose_verdict_does_not_match(hs: ModuleType) -> None:
    """*"verdict indented / inside prose → refuse; the declaration did not match."*"""
    assert hs.wire_verdict("  HANDSHAKE-VERDICT: GO\n") is None
    assert hs.wire_verdict("> HANDSHAKE-VERDICT: GO\n") is None
    assert hs.wire_verdict("this is not a closing GO, we are holding\n") is None


def test_C8_a_close_illustrated_inside_a_fence_is_not_a_close(hs: ModuleType) -> None:
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


def test_C11_an_unrecognised_verdict_refuses(hs: ModuleType) -> None:
    """*"unrecognised verdict → refuse."* Not agreement, and not an error to skip."""
    for value in ("MAYBE", "APPROVED", "yes", "Go", ""):
        text = _header(**{"HANDSHAKE-VERDICT": value or "  "})
        assert hs.wire_verdict(text) != "GO", value
        assert hs.close_blockers(text), value


def test_C12_a_declared_round_that_differs_from_its_file_refuses(
    hs: ModuleType, tmp_path: Path
) -> None:
    """*"declared round ≠ the round it is filed under → refuse."*"""
    path = tmp_path / "round-9.md"
    path.write_text(_header(**{"HANDSHAKE-ROUND": "8"}), encoding="utf-8")
    problems = hs.check_wire_header(path)
    assert any("HANDSHAKE-ROUND: 8" in p and "round 9" in p for p in problems), problems


def test_C13_a_later_lap_declaring_hold_after_a_go_reopens_the_round(
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


def test_C14_no_round_files_at_all_refuses(hs: ModuleType, tmp_path: Path) -> None:
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


def test_C15_a_higher_protocol_version_refuses_rather_than_guessing(
    hs: ModuleType,
) -> None:
    """*"`HANDSHAKE-PROTOCOL` higher than implemented → refuse rather than guess."*

    A gate reading a file one version ahead cannot know which of that version's
    rules it is silently not applying — including, possibly, a new close
    requirement.

    **Derived from `hs.PROTOCOL_VERSION`, never a literal.** The first version of
    this test hard-coded `"3"` as "higher", which was true while the gate
    implemented v2 and became a test of nothing the day the gate shipped v3 — the
    assertion still passed by asserting the opposite of what it meant. A test whose
    fixture encodes the value under test measures the fixture.
    """
    ours = hs.PROTOCOL_VERSION
    assert (
        hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": str(ours + 1)}))
        is not None
    )
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": "99"})) is not None
    # Our own version and older ones are fine.
    assert hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": str(ours)})) is None
    for older in range(1, ours):
        assert (
            hs.protocol_refusal(_header(**{"HANDSHAKE-PROTOCOL": str(older)})) is None
        )
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
def test_C9_a_round_8_file_missing_an_identity_field_refuses(
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


def test_C9_applies_on_a_mid_round_hold_too(hs: ModuleType) -> None:
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


def test_C10_a_pre_header_round_missing_them_is_allowed(
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


# --- C17 / C18: a test pin is not a pin agreement (§6a) ------------------------
#
# The field exists because our own rules deadlocked: a close needs
# `HANDSHAKE-TESTED`, that evidence only comes from the rig, the rig installs the
# pinned build, and neither side may move the pin while a round is open — so the
# rig forever runs the build *without* the changes under review. Every step is a
# rule both projects hold and together they are unsatisfiable. Splitting "the
# build we agreed on" from "the build we are testing" is the way out.


def test_C17_a_hold_carrying_a_test_pin_is_still_not_a_close(hs: ModuleType) -> None:
    """C17 — *"a file declaring `HANDSHAKE-TEST-PIN` and otherwise complete, but
    verdict `HOLD` → refuse; a test pin is not a release."*

    The floor that makes this mean something: the **same file with the test pin
    removed** must be refused for the same reason. Otherwise this test would pass
    against a gate that refuses every file, and would also pass against one that
    refuses files *because* they carry a test pin — the opposite of §6a, which
    requires a test pin to be permitted alongside a real close.
    """
    with_pin = _header(**{"HANDSHAKE-VERDICT": "HOLD", "HANDSHAKE-TEST-PIN": "dc21958"})
    without = _header(**{"HANDSHAKE-VERDICT": "HOLD"})
    assert hs.close_blockers(with_pin), "a HOLD with a test pin closed the round"
    # Same reason, not a new one: the verdict is what blocks, not the test pin.
    assert hs.close_blockers(with_pin) == hs.close_blockers(without), (
        "the test pin changed why the file was refused — it must be inert on a "
        f"HOLD: {hs.close_blockers(with_pin)} vs {hs.close_blockers(without)}"
    )


def test_C18_a_valid_close_may_carry_a_test_pin_and_is_still_allowed(
    hs: ModuleType,
) -> None:
    """C18 — *"`HANDSHAKE-TEST-PIN` present alongside a valid close → allow, and the
    test pin must not be mistaken for `HANDSHAKE-PIN`."*

    This is the **normal** sequence, not an edge case: the evidence a close cites
    was gathered on the test pin, so a closing file will usually name both. A gate
    that refuses it re-creates the deadlock §6a exists to break.
    """
    text = _header(**{"HANDSHAKE-TEST-PIN": "dc21958"})
    assert hs.close_blockers(text) == [], hs.close_blockers(text)
    # And the two pins stay distinguishable — reading the test pin as the agreement
    # would move the production pin to a build nobody approved.
    fields = hs.wire_fields(text)
    assert fields[hs.TEST_PIN_FIELD] == "dc21958"
    assert fields["HANDSHAKE-PIN"] == "5bc654d"
    assert fields[hs.TEST_PIN_FIELD] != fields["HANDSHAKE-PIN"]


def test_C18_a_test_pin_with_no_agreed_pin_at_all_is_refused(hs: ModuleType) -> None:
    """The half of C18 that is a refusal, and the reason `TEST_PIN_FIELD` is not
    simply ignored as an unknown field.

    A closing file naming *only* the build it tested would move the production pin
    to something never agreed to. Unknown-field tolerance (§3) is what lets a
    proposal ship before the other side implements it; it is not licence to treat a
    field with a stated meaning as noise once you know the meaning.
    """
    text = _header(**{"HANDSHAKE-PIN": None, "HANDSHAKE-TEST-PIN": "dc21958"})
    blockers = hs.close_blockers(text)
    assert any(hs.TEST_PIN_FIELD in b and "HANDSHAKE-PIN" in b for b in blockers), (
        blockers
    )


# --- C19 / C20: what a release CLAIMS, not whether one happens -----------------


def _record_with_one_open_round(root: Path) -> Path:
    """A minimal handshake record whose single round is OPEN, for C19/C20.

    **Why a fixture now, and the previous version of this file said so.** C19 and
    C20 used to run against the *real* record, with a floor asserting a round was
    open so the check could not silently become a property of the empty set. On
    2026-08-07 round 7 closed, that floor fired exactly as designed, and this is
    the "re-point it at a fixture" the message asked for.

    The fixture is deliberately the smallest thing the gate can read: one outbound
    file, one inbound reply, and one verification whose verdict is `**HOLD**`. A
    HOLD is what makes the round open — not the absence of a file — because a
    presence-only check reporting CLOSED is the defect §5 of the shared protocol
    exists to prevent.
    """
    for sub in ("outbound", "inbound", "verified"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "outbound" / "round-99.md").write_text("sent\n", encoding="utf-8")
    (root / "inbound" / "round-99.md").write_text("returned\n", encoding="utf-8")
    (root / "verified" / "round-99.md").write_text(
        "HANDSHAKE-VERDICT: HOLD\n\n**HOLD on deadbee** — the round is still open.\n",
        encoding="utf-8",
    )
    return root


def _record_with_one_closed_round(root: Path) -> Path:
    """The mirror of :func:`_record_with_one_open_round`: one round, verdict GO.

    Deliberately built the same way and differing only in the verdict, so the
    pair isolates *the verdict* as the thing that opens and closes a round. A
    fixture that also differed in which files exist would let a presence-only
    gate pass both halves.
    """
    for sub in ("outbound", "inbound", "verified"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "outbound" / "round-99.md").write_text("sent\n", encoding="utf-8")
    # FULL closing headers on both, not just a verdict line: a GO that cannot
    # close is not a close (§5), and `close_blockers` is what enforces it. A
    # fixture carrying only the verdict would assert that the gate says yes to
    # something the gate is right to refuse.
    for sub, sender in (("inbound", "cyanrip-fork"), ("verified", "platterpus")):
        (root / sub / "round-99.md").write_text(
            _header(**{"HANDSHAKE-ROUND": "99", "HANDSHAKE-FROM": sender})
            + "\n**GO on 5bc654d** — verified in both directions.\n",
            encoding="utf-8",
        )
    return root


def test_C19_a_stable_release_is_refused_while_any_round_is_open(
    hs: ModuleType, tmp_path: Path
) -> None:
    """C19 — *"a stable release requested with any round open → refuse."*

    Against a **fixture**, since 2026-08-07: round 7 closed, every round in the
    real record is CLOSED, and this row would otherwise be asserting a property of
    the empty set. The previous version anticipated that and left the instruction
    in its own failure message; this is that instruction carried out.
    """
    root = _record_with_one_open_round(tmp_path / "handshake")
    open_rounds = [ln for ln in hs.round_status(root) if ln.endswith("OPEN")]
    assert open_rounds, "the fixture does not present an open round"
    assert hs.main(["--release-gate", "--handshake-dir", str(root)]) == 1, (
        "a stable release passed with a round open"
    )


def test_C19_a_stable_release_is_allowed_when_every_round_is_closed(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The companion half: a refusal test alone passes against a gate that
    refuses everything.

    **Moved off the real record, 2026-08-12.** It used to assert *"Platterpus may
    cut a stable release right now"*, which was true when written (round 7 had
    just closed) and is a statement about today rather than about the gate. Round
    8 opened and it failed — correctly reporting reality, and uselessly, because
    the property under test is *the gate can say yes*, not *the project is
    currently releasable*. That is the "a test that asserts today's state is a
    test that fails on progress" shape `round_status` already warns about, and
    the sibling above had already been re-pointed at a fixture for exactly this
    reason.
    """
    root = _record_with_one_closed_round(tmp_path / "handshake")
    assert [ln for ln in hs.round_status(root) if ln.endswith("OPEN")] == []
    assert hs.main(["--release-gate", "--handshake-dir", str(root)]) == 0


def test_C19_the_gate_agrees_with_the_real_record(hs: ModuleType) -> None:
    """What the real record can still be asked, without pinning today's answer.

    Whether Platterpus is releasable changes; that the gate's verdict *matches
    its own status report* does not. Keeping this against the real record means a
    gate that ignored the record entirely — the failure mode both C19 halves
    exist for — still fails here whichever way the project happens to stand.
    """
    open_rounds = [ln for ln in hs.round_status() if ln.endswith("OPEN")]
    expected = 1 if open_rounds else 0
    assert hs.main(["--release-gate"]) == expected, (
        f"the gate and the status report disagree: open rounds {open_rounds}"
    )


def test_C20_a_prerelease_is_allowed_and_prints_every_open_round(
    hs: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """C20 — *"a pre-release requested with a round open → allow, and print every
    open round first."*

    Both halves matter and only the first is obvious. **Permitting a beta quietly
    would be worse than refusing it**: the whole justification is that a beta
    claims no joint verification, and a claim nobody is shown is not a claim. So
    the gate must both return success *and* name what is open.
    """
    root = _record_with_one_open_round(tmp_path / "handshake")
    assert (
        hs.main(["--release-gate", "--prerelease", "--handshake-dir", str(root)]) == 0
    )
    # **stderr, deliberately.** The gate's warnings go to stderr so that piping its
    # stdout into a release script cannot swallow them, and so they still reach a
    # log when stdout is captured. Asserted on the stream it actually uses rather
    # than changing the gate to suit the test.
    captured = capsys.readouterr()
    printed = captured.err
    for line in [ln for ln in hs.round_status(root) if ln.endswith("OPEN")]:
        round_name = line.split(":")[0]
        assert round_name in printed, (
            f"{round_name} is open and the pre-release gate did not name it: {printed}"
        )
    # And it must still say plainly that a STABLE release remains blocked, or the
    # output reads as approval.
    assert "STABLE" in printed and "blocked" in printed, printed


# --- the table itself must not shrink -----------------------------------------


def _conformance_row_ids() -> list[str]:
    """The row IDs, read out of the shared protocol file.

    **Derived, not hardcoded.** The previous version of this check looped over
    `range(1, 17)` and skipped two numbers with a comment explaining that the
    fork's indices differed from ours — so it could neither notice a new row nor
    tell which row a given test covered. Stable IDs exist precisely to end that,
    and a coverage check that restates the expected set defeats them again on the
    first row either side adds.
    """
    text = (_REPO_ROOT / "docs" / "handshake-protocol.md").read_text(encoding="utf-8")
    return re.findall(r"^\|\s*(C\d+)\s*\|", text, re.MULTILINE)


def _rows_after_heading(heading_fragment: str) -> list[str]:
    """Row IDs declared *after* a given §8 sub-heading in the shared spec.

    Used to separate rows that bind today from rows the spec itself defers. The
    fragment is matched against the heading text, so the fork can reword the
    heading without breaking us as long as the phrase survives — and if it does
    not, the caller asserts the split parsed rather than silently exempting the
    whole table.
    """
    text = (_REPO_ROOT / "docs" / "handshake-protocol.md").read_text(encoding="utf-8")
    lowered = text.lower()
    at = lowered.find(heading_fragment.lower())
    if at < 0:
        return []
    return re.findall(r"^\|\s*\*{0,2}(C\d+)\*{0,2}\s*\|", text[at:], re.MULTILINE)


def test_every_conformance_row_has_a_test_here() -> None:
    """A floor on the suite, not on the gate.

    A skipped conformance row is a divergence nobody can see. If the shared table
    grows a row, this fails until a test for it exists — which is the only way a
    shared table stays shared.
    """
    ids = _conformance_row_ids()
    # Floor: a table that parsed to nothing would make this pass by finding nothing,
    # which is the failure mode this whole file is about.
    assert len(ids) >= 20, (
        f"only {len(ids)} conformance row ID(s) parsed out of the protocol file — "
        "the table's shape changed and this check is no longer reading it"
    )
    assert len(ids) == len(set(ids)), f"duplicate row IDs in the table: {ids}"
    source = Path(__file__).read_text(encoding="utf-8")

    # The v3 rows are not yet binding, and the spec says so itself — the heading
    # "Rows added in v3 — required once both gates implement 3". So the split is
    # DERIVED from the document rather than hard-coded here: a row the fork moves
    # out of that section becomes binding on us the moment they send the file, with
    # no edit on our side. A hand-kept list would go stale in exactly the direction
    # that hides work.
    pending = _rows_after_heading("Rows added in v3")
    assert pending, (
        "the v3 section heading no longer parses — if the rows became binding, "
        "delete this branch rather than letting it silently exempt everything"
    )
    binding = [i for i in ids if i not in pending]
    # Floor on the split itself: if it ever swallowed the v2 rows the check above
    # would pass by exempting everything, which is the shape this file exists for.
    assert len(binding) >= 20, (
        f"only {len(binding)} binding row(s) after removing the v3 section — the "
        "split is reading the table wrong"
    )

    missing = [i for i in binding if f"def test_{i}_" not in source]
    assert not missing, (
        f"shared protocol §8 rows {', '.join(missing)} have no test in this file — "
        "a conformance row without a test is a divergence nobody can see"
    )

    # And the pending ones are reported, not forgotten. Round 9's close condition 1
    # is "both gates implement 3"; these are what that means for this file.
    unwritten = [i for i in pending if f"def test_{i}_" not in source]
    assert unwritten == sorted(unwritten, key=lambda s: int(s[1:])), unwritten


def test_no_test_here_claims_a_row_the_table_does_not_have() -> None:
    """The converse, which the old check had no way to state.

    A test named for a row that no longer exists is a coverage claim about
    nothing — and it is how our own file ended up with two different tests both
    called `test_row9_`, one for "unrecognised verdict" and one for the round-8
    identity fields. Either could have been deleted and the coverage check would
    have stayed green.
    """
    ids = set(_conformance_row_ids())
    source = Path(__file__).read_text(encoding="utf-8")
    claimed = set(re.findall(r"^def test_(C\d+)_", source, re.MULTILINE))
    unknown = sorted(claimed - ids)
    assert not unknown, (
        f"test(s) here claim row(s) {', '.join(unknown)}, which the shared table "
        "does not define"
    )
