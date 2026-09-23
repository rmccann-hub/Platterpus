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

import ast
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
        # RELEASED, because this helper's contract is "a COMPLETE closing header"
        # and from round 19 a lap that does not declare its release state cannot
        # close (2026-09-14). Added when `test_C19_a_stable_release_is_allowed_...`
        # went red: its fixture is `round-99`, so the grandfather does not cover it
        # and the gate correctly refused a stand-in that declared nothing.
        #
        # **That is the floor working, not a false failure.** C19 is the half that
        # asserts the gate can still say YES — a gate that can only refuse is a wall
        # — so the one test guaranteed to catch an over-broad release rule is the one
        # that caught it. Teaching the stand-in to declare is the fix; exempting
        # fixtures from the rule would have made every other test here assert against
        # a world the product does not have (`CLAUDE.md`: *what does my stand-in do
        # that the real thing does not?*).
        "HANDSHAKE-READY-TO-READ": "yes — released by the operator on 2026-09-14",
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


def _record_with_a_complete_close_one_version_ahead(root: Path, hs: ModuleType) -> Path:
    """A round that CLOSES on every rule this gate implements — v5's included — one
    of whose laps declares a protocol one version above what the gate implements.

    **Complete under v5 on purpose.** The first version omitted
    ``HANDSHAKE-PEER-VERDICT-SOURCE``, so a file declaring 6 was refused by row C41
    (6 is "5 or more") and the C15 tests passed with the version refusal deleted —
    the revert probe reported them VACUOUS. The version must be the ONLY fault here.
    """
    for sub in ("outbound", "inbound", "verified"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "verified" / "round-99-lap-02.md").write_text(
        _header(
            **{
                "HANDSHAKE-ROUND": "99",
                "HANDSHAKE-LAP": "2",
                "HANDSHAKE-FROM": "platterpus",
            }
        )
        + "\n**GO on 5bc654d**\n",
        encoding="utf-8",
    )
    (root / "inbound" / "round-99-lap-03.md").write_text(
        _header(
            **{
                "HANDSHAKE-ROUND": "99",
                "HANDSHAKE-LAP": "3",
                "HANDSHAKE-FROM": "cyanrip-fork",
                "HANDSHAKE-PROTOCOL": str(hs.PROTOCOL_VERSION + 1),
                hs.PEER_VERDICT_SOURCE_FIELD: "round-99-lap-02.md at platterpus@abc1234",
            }
        )
        + "\n**GO on 5bc654d**\n",
        encoding="utf-8",
    )
    return root


def test_C15_the_GATE_refuses_a_higher_protocol_not_only_the_helper(
    hs: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """C15 is a statement about the GATE — *"refuse rather than guess"* — and the
    test above only proves the helper returns a reason.

    That gap was real. Until 2026-09-22 ``protocol_refusal`` had one caller,
    ``--check``; ``round_status`` and ``--release-gate`` read a verdict out of a
    file one version ahead and closed the round on it. Measured in the round-24
    rehearsal: our v4 GO plus a peer v5 GO read CLOSED and the release gate exited
    0, while ``--check`` refused the same lap. The row passed throughout, because
    its test asserted the helper — a *requested* thing standing in for a
    *happened* one (``CLAUDE.md``).
    """
    root = _record_with_a_complete_close_one_version_ahead(tmp_path / "hs", hs)
    lines = hs.round_status(root)
    assert any(ln.startswith("round-99:") and ln.endswith("OPEN") for ln in lines), (
        lines
    )
    assert any(ln.startswith("  refused inbound/round-99-lap-03.md") for ln in lines), (
        lines
    )
    assert hs.main(["--release-gate", "--handshake-dir", str(root)]) == 1
    capsys.readouterr()


def test_C15_the_gate_and_the_checker_give_ONE_answer(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The relation, not either surface: no round containing a file ``--check``
    refuses on version grounds may read CLOSED. Tested at both a higher version
    and our own, so the property cannot pass by refusing everything."""
    ahead = _record_with_a_complete_close_one_version_ahead(tmp_path / "a", hs)
    ahead_file = ahead / "inbound" / "round-99-lap-03.md"
    assert hs.protocol_refusal(ahead_file.read_text(encoding="utf-8")) is not None
    assert not any(ln.endswith("CLOSED") for ln in hs.round_status(ahead))

    level = _record_with_one_closed_round(tmp_path / "b")
    for path in (level / "inbound").glob("*.md"):
        assert hs.protocol_refusal(path.read_text(encoding="utf-8")) is None
    assert any(ln.endswith("CLOSED") for ln in hs.round_status(level)), (
        "the positive control failed — a gate that refuses at every version passes "
        "the half above for the wrong reason"
    )


# --- C37-C42: protocol v5 (§5b / §5c) ------------------------------------------


def _v5_lap(hs: ModuleType, sender: str, lap: int, **overrides: str | None) -> str:
    """A complete closing header declaring v5, for round 99."""
    fields: dict[str, str | None] = {
        "HANDSHAKE-PROTOCOL": str(hs.PEER_VERDICT_SOURCE_FROM_PROTOCOL),
        "HANDSHAKE-ROUND": "99",
        "HANDSHAKE-LAP": str(lap),
        "HANDSHAKE-FROM": sender,
        hs.PEER_VERDICT_SOURCE_FIELD: "none — no lap of the peer's exists yet",
    }
    fields.update(overrides)
    return _header(**fields) + f"\nlap {lap} body\n"


def _v5_world(
    hs: ModuleType, root: Path, laps: list[tuple[str, int, dict[str, str | None]]]
) -> Path:
    """Write ``(direction, lap, overrides)`` laps as ``round-99-lap-LL.md``."""
    for sub in ("outbound", "inbound", "verified"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for direction, lap, overrides in laps:
        sender = "cyanrip-fork" if direction == "inbound" else "platterpus"
        (root / direction / f"round-99-lap-{lap:02d}.md").write_text(
            _v5_lap(hs, sender, lap, **overrides), encoding="utf-8"
        )
    return root


def _we_spoke_first_and_they_closed(
    hs: ModuleType, root: Path, **their_close: str | None
) -> Path:
    """The case §5b exists for: their lap 1 OPEN, our lap 2 GO (transcribing their
    OPEN, because their answer did not exist yet), their lap 3 GO."""
    return _v5_world(
        hs,
        root,
        [
            (
                "inbound",
                1,
                {"HANDSHAKE-VERDICT": "OPEN", "HANDSHAKE-PEER-VERDICT": "OPEN"},
            ),
            (
                "outbound",
                2,
                {
                    "HANDSHAKE-PEER-VERDICT": "OPEN",
                    hs.PEER_VERDICT_SOURCE_FIELD: "round-99-lap-01.md at cyanrip@abc1234",
                },
            ),
            (
                "inbound",
                3,
                {
                    hs.PEER_VERDICT_SOURCE_FIELD: "round-99-lap-02.md at platterpus@def5678",
                    **their_close,
                },
            ),
        ],
    )


def _state(lines: list[str]) -> str:
    rows = [ln for ln in lines if ln.startswith("round-99:")]
    assert len(rows) == 1, lines
    return "CLOSED" if rows[0].endswith("CLOSED") else "OPEN"


def test_C40_a_newer_peer_lap_closes_the_round_and_both_are_printed(
    hs: ModuleType, tmp_path: Path
) -> None:
    """C40 — *"the §5b lap is newer than the one the source names → allow, resolved
    on the peer lap's own declaration, and print both."* This is the whole of v5's
    saving: under v4 this round needs one more lap of ours whose only content is a
    copy of their GO."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    lines = hs.round_status(root)
    assert _state(lines) == "CLOSED", lines
    superseded = [ln for ln in lines if "superseded by the newer" in ln]
    assert superseded and "round-99-lap-03.md" in superseded[0], lines
    assert "OPEN from lap 1" in superseded[0], superseded


def test_C40_the_same_files_declaring_4_do_NOT_close(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The contrast that makes C40 mean something: v4 semantics are unchanged for a
    file that declares 4. If this closed, v5 would have been applied to files that
    did not ask for it — the C29 reasoning, from the other side."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    for path in [*root.glob("*/round-99-lap-*.md")]:
        text = path.read_text(encoding="utf-8").replace(
            f"HANDSHAKE-PROTOCOL: {hs.PEER_VERDICT_SOURCE_FROM_PROTOCOL}\n",
            "HANDSHAKE-PROTOCOL: 4\n",
        )
        path.write_text(text, encoding="utf-8")
    assert _state(hs.round_status(root)) == "OPEN"


def _they_opened_and_we_closed(hs: ModuleType, root: Path) -> Path:
    """Round 24's exact shape: their lap 1 GO transcribing ``none`` (nothing of ours
    existed), our lap 2 GO transcribing their lap 1. Closes on OUR gate at lap 2."""
    return _v5_world(
        hs,
        root,
        [
            ("inbound", 1, {"HANDSHAKE-PEER-VERDICT": "none"}),
            (
                "outbound",
                2,
                {hs.PEER_VERDICT_SOURCE_FIELD: "round-99-lap-01.md at cyanrip@abc1234"},
            ),
        ],
    )


def test_a_close_one_lap_before_a_literal_peer_gate_SAYS_so(
    hs: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Round 24 closed on our gate at lap 2 and on the fork's at lap 3, and our
    output said a bare CLOSED — so a lap of ours promised one close and our code
    acted on the other. The round still closes (both declared GO); the line says
    which close it is, on `--status` and on an allowed release."""
    root = _they_opened_and_we_closed(hs, tmp_path / "hs")
    lines = hs.round_status(root)
    assert _state(lines) == "CLOSED", lines
    early = [ln for ln in lines if "one lap before" in ln]
    assert len(early) == 1, lines
    assert (
        "inbound/round-99-lap-01.md does not list outbound/round-99-lap-02.md"
        in (early[0])
    )
    assert early[0].startswith(hs.SOURCE_LINE_PREFIX)
    assert not early[0].endswith("OPEN")
    capsys.readouterr()
    assert hs.main(["--release-gate", "--handshake-dir", str(root)]) == 0
    assert "one lap before" in capsys.readouterr().out


def test_a_close_both_gates_agree_on_prints_no_early_note(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The contrast: when the peer's closing lap LISTS ours (their lap 3 naming our
    lap 2), a literal gate sees what ours sees and there is nothing to say. Without
    this the note could fire on every v5 close and would mean nothing."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    lines = hs.round_status(root)
    assert _state(lines) == "CLOSED", lines
    assert not [ln for ln in lines if "one lap before" in ln], lines


def test_C42_a_v5_close_prints_which_lap_each_peer_verdict_came_from(
    hs: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """C42 — a close resting on a file in the peer's tree must name it, on
    ``--status`` AND on an allowed release, or it cannot be audited later."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    lines = hs.round_status(root)
    sources = [ln for ln in lines if ln.startswith(hs.SOURCE_LINE_PREFIX)]
    assert any(
        "resolved from inbound/round-99-lap-03.md (GO)" in ln for ln in sources
    ), lines
    assert any(
        "resolved from outbound/round-99-lap-02.md (GO)" in ln for ln in sources
    ), lines
    capsys.readouterr()
    assert hs.main(["--release-gate", "--handshake-dir", str(root)]) == 0
    out = capsys.readouterr().out
    assert "resolved from inbound/round-99-lap-03.md" in out, out
    assert "release allowed" in out, out
    # And no source line may be counted as an open round by the gate.
    assert not any(ln.endswith("OPEN") for ln in sources), sources


def test_C42_holds_on_the_PRERELEASE_path_too_because_every_v0_release_takes_it(
    hs: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`release.yml` runs `--release-gate --prerelease` for every `v0.*` tag, so the
    strict path the C42 test above drives is one no release of ours has taken. The
    source lines — and the one-lap-early note — must print on this path as well."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    capsys.readouterr()
    assert (
        hs.main(["--release-gate", "--prerelease", "--handshake-dir", str(root)]) == 0
    )
    out = capsys.readouterr().out
    assert "resolved from inbound/round-99-lap-03.md" in out, out
    assert "pre-release allowed" in out, out

    early = _they_opened_and_we_closed(hs, tmp_path / "early")
    capsys.readouterr()
    assert (
        hs.main(["--release-gate", "--prerelease", "--handshake-dir", str(early)]) == 0
    )
    assert "one lap before" in capsys.readouterr().out


def test_C39_a_transcription_that_disagrees_with_its_source_refuses_naming_both(
    hs: ModuleType, tmp_path: Path
) -> None:
    """C39 — the named source and the transcription must agree; refuse naming both
    values and both files."""
    root = _v5_world(
        hs,
        tmp_path / "hs",
        [
            ("inbound", 1, {"HANDSHAKE-VERDICT": "HOLD"}),
            ("outbound", 2, {hs.PEER_VERDICT_SOURCE_FIELD: "round-99-lap-01.md"}),
        ],
    )
    lines = hs.round_status(root)
    assert _state(lines) == "OPEN"
    c39 = [ln for ln in lines if "row C39" in ln]
    assert c39, lines
    assert (
        "HANDSHAKE-PEER-VERDICT: GO" in c39[0] and "HANDSHAKE-VERDICT: HOLD" in c39[0]
    )
    assert (
        "outbound/round-99-lap-02.md" in c39[0]
        and "inbound/round-99-lap-01.md" in c39[0]
    )


@pytest.mark.parametrize("ready", ["no — held by the operator", None])
def test_C38_an_unreleased_candidate_refuses_NAMING_the_lap_and_the_value(
    hs: ModuleType, tmp_path: Path, ready: str | None
) -> None:
    """C38 — the §5b candidate must declare READY-TO-READ: yes; refuse naming the lap
    and the value read, and treat an absent field as no (§5c)."""
    root = _we_spoke_first_and_they_closed(
        hs, tmp_path / "hs", **{"HANDSHAKE-READY-TO-READ": ready}
    )
    lines = hs.round_status(root)
    assert _state(lines) == "OPEN"
    c38 = [ln for ln in lines if "row C38" in ln]
    assert c38 and "round-99-lap-03.md" in c38[0], lines
    shown = "absent" if ready is None else repr(ready)
    assert shown in c38[0], c38[0]


def test_C37_a_peer_file_that_is_not_an_enumerated_lap_is_never_read(
    hs: ModuleType, tmp_path: Path
) -> None:
    """C37 — §5b reads a lap this gate enumerates, never any file it happens to
    hold. A file declaring ``HANDSHAKE-FROM`` twice is not a lap (§5a), so it must
    not supply a verdict even when it is the newest file and says GO."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    lap3 = root / "inbound" / "round-99-lap-03.md"
    lap3.write_text(
        lap3.read_text(encoding="utf-8") + "HANDSHAKE-FROM: cyanrip-fork\n",
        encoding="utf-8",
    )
    assert not hs.counts_as_one_lap(lap3.read_text(encoding="utf-8"))
    lines = hs.round_status(root)
    assert _state(lines) == "OPEN", lines
    assert not any("resolved from inbound/round-99-lap-03.md" in ln for ln in lines), (
        lines
    )


def test_C37_with_no_enumerated_peer_lap_the_refusal_says_so(
    hs: ModuleType, tmp_path: Path
) -> None:
    """Step 4: holding no enumerated lap refuses AND names which condition failed."""
    root = _v5_world(hs, tmp_path / "hs", [("outbound", 2, {})])
    (root / "inbound" / "round-99-lap-01.md").write_text(
        _v5_lap(hs, "cyanrip-fork", 1) + "HANDSHAKE-LAP: 1\n", encoding="utf-8"
    )
    lines = hs.round_status(root)
    assert _state(lines) == "OPEN"
    assert any("none is an enumerated lap" in ln and "C37" in ln for ln in lines), lines


@pytest.mark.parametrize(
    "missing", ["HANDSHAKE-PEER-VERDICT", "HANDSHAKE-PEER-VERDICT-SOURCE"]
)
def test_C41_a_v5_file_missing_either_peer_verdict_field_is_refused(
    hs: ModuleType, tmp_path: Path, missing: str
) -> None:
    """C41 — at ``--check`` (any verdict) and at the gate."""
    root = _we_spoke_first_and_they_closed(hs, tmp_path / "hs")
    ours = root / "outbound" / "round-99-lap-02.md"
    kept = [
        ln
        for ln in ours.read_text(encoding="utf-8").splitlines()
        if not ln.startswith(f"{missing}:")
    ]
    ours.write_text("\n".join(kept) + "\n", encoding="utf-8")
    problems = hs.check_wire_header(ours)
    assert any("row C41" in p and missing in p for p in problems), problems
    assert _state(hs.round_status(root)) == "OPEN"
    # And a v4 file without the source field is NOT refused for it: C41 binds a
    # file that declares 5, and v4 never had the field.
    v4 = tmp_path / "v4.md"
    v4.write_text(_header(**{"HANDSHAKE-PROTOCOL": "4"}), encoding="utf-8")
    assert not any("C41" in p for p in hs.check_wire_header(v4))


def test_the_source_parser_never_raises_and_reads_the_committed_spellings(
    hs: ModuleType,
) -> None:
    """``HANDSHAKE-PEER-VERDICT-SOURCE`` is free text written by two projects."""
    assert hs.parse_source("round-24-lap-03.md at cyanrip@e5008c9").lap == 3
    assert hs.parse_source("their lap 3, read at cyanrip@e5008c9").lap == 3
    assert hs.parse_source("none — no lap of yours exists").none_declared
    assert hs.parse_source("**none**").none_declared
    unplaceable = hs.parse_source("their closing file")
    assert unplaceable.lap is None and not unplaceable.none_declared
    for junk in ("", "   ", "lap", "round-x-lap-y", "\x00", "lap -1"):
        hs.parse_source(junk)


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
    return re.findall(r"^\|\s*(C\d+[a-z]?)\s*\|", text, re.MULTILINE)


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
    return re.findall(r"^\|\s*\*{0,2}(C\d+[a-z]?)\*{0,2}\s*\|", text[at:], re.MULTILINE)


def test_every_conformance_row_has_a_test_here(hs: ModuleType) -> None:
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

    # WHICH ROWS BIND IS DERIVED FROM THE SPEC'S HEADINGS AND OUR VERSION — the
    # spec's own instruction: *"The split is by heading rather than by a list a test
    # hardcodes, so bumping PROTOCOL_VERSION turns them on with no second edit."*
    #
    # **This test broke that instruction for thirteen rounds.** It exempted every row
    # after the v3 heading as "pending" unconditionally, so when both gates reached 4
    # in round 9, the sixteen v3/v4 rows (C21-C36) stayed exempt — and none of them
    # has a row-named test here to this day. Found 2026-09-22 while bumping to 5, when
    # the same unconditional exemption would have swallowed C37-C42 as well. Now:
    # rows under "required once both gates implement N" bind when PROTOCOL_VERSION
    # reaches N, and the v3/v4 rows that bind without a named test are COUNTED in a
    # ratchet below instead of being invisible.
    after_v3 = _rows_after_heading("Rows added in v3")
    after_v5 = _rows_after_heading("Rows added in v5")
    assert after_v3 and after_v5, (
        "a versioned §8 heading no longer parses — if its rows became unconditional, "
        "delete this branch rather than letting it silently exempt them"
    )
    v34_rows = [i for i in after_v3 if i not in after_v5]
    tiers: list[tuple[int, list[str]]] = [(4, v34_rows), (5, after_v5)]
    pending = [
        i for version, rows in tiers if hs.PROTOCOL_VERSION < version for i in rows
    ]
    binding = [i for i in ids if i not in pending]
    # Floor on the split itself: if it ever swallowed the v2 rows the check above
    # would pass by exempting everything, which is the shape this file exists for.
    assert len(binding) >= 20, (
        f"only {len(binding)} binding row(s) after the version split — the split is "
        "reading the table wrong"
    )

    missing = [
        i
        for i in binding
        if f"def test_{i}_" not in source
        and i not in _KNOWN_DIVERGENCES
        and i not in _BINDING_ROWS_WITHOUT_A_NAMED_TEST
    ]
    assert not missing, (
        f"shared protocol §8 rows {', '.join(missing)} have no test in this file — "
        "a conformance row without a test is a divergence nobody can see"
    )


#: Binding rows with **no row-named test in this file** — a ratchet that may shrink
#: and never grow, and deliberately separate from ``_KNOWN_DIVERGENCES`` below, which
#: records rows our gate does NOT implement. These are rows it is supposed to
#: implement and this file has never *run*.
#:
#: **Why sixteen, all at once.** Rows C21-C36 are v3/v4 rows, binding since both gates
#: reached protocol 4 in round 9. The coverage check above treated them as pending
#: unconditionally — against the spec's own instruction that bumping the version turns
#: them on — so no named test was ever demanded. Some behaviours are exercised under
#: other names (the digest in ``tests/test_round_digest.py``, overrides and the lap
#: limit in ``tests/test_handshake_tooling.py``), but *"one test per row, in the
#: table's order"* is what makes a divergence report citable, and that was never true
#: for any of them. Recorded 2026-09-22 so the gap is a number, not a silence.
#: Retire an entry by writing ``test_C<nn>_…`` — the check below refuses a stale entry.
_BINDING_ROWS_WITHOUT_A_NAMED_TEST: frozenset[str] = frozenset(
    {f"C{n}" for n in range(21, 37)}
)


def test_the_untested_binding_rows_ratchet_is_exact() -> None:
    """Every entry must still lack its test and still be a row in the table."""
    source = Path(__file__).read_text(encoding="utf-8")
    ids = set(_conformance_row_ids())
    stale = sorted(
        i for i in _BINDING_ROWS_WITHOUT_A_NAMED_TEST if f"def test_{i}_" in source
    )
    assert not stale, (
        f"{stale} now have tests — remove them from _BINDING_ROWS_WITHOUT_A_NAMED_TEST"
    )
    unknown = sorted(_BINDING_ROWS_WITHOUT_A_NAMED_TEST - ids)
    assert not unknown, f"{unknown} are not rows in the shared §8 table"
    assert len(_BINDING_ROWS_WITHOUT_A_NAMED_TEST) <= 16, "this ratchet may only shrink"


#: Binding conformance rows our gate does NOT implement — **recorded, not hidden.**
#:
#: **A ratchet that may shrink and never grow**, and every entry carries what the
#: divergence is and which direction it fails in. The point is that a row here is
#: *counted*: the alternative is what actually happened to ``C13a``, which was
#: invisible for as long as the row-id pattern was ``C\d+`` — not exempted, not
#: deferred, simply unable to appear in any denominator.
#:
#: ``C13a`` — *"a later lap of any verdict after the round reached a terminal state
#: → refuse the FILE as an illegal transition; the round stays closed. v3 changed
#: this: under v2 it reopened the round."* Our ``round_status`` reads the newest
#: file on each side, so a later lap still reopens a closed round — the v2
#: behaviour. **It fails CLOSED**: every later-lap shape (``HOLD``, or no verdict
#: at all) turns the round ``OPEN`` and ``--release-gate`` refuses, so the
#: divergence over-blocks a release rather than permitting one. That is the right
#: direction to be wrong in and it is still wrong, and it is why this is queued
#: rather than hot-fixed at the end of a long change.
_KNOWN_DIVERGENCES: frozenset[str] = frozenset({"C13a"})


def test_every_known_divergence_is_still_real() -> None:
    """A ratchet's exemptions have to expire, or the list becomes folklore.

    If someone implements ``C13a`` and writes ``test_C13a_…``, the row above stops
    being a divergence — and an exemption left behind would go on excusing a test
    that now exists, which is how an allowlist outlives the thing it allowed.

    Same shape as the ``_WORKERS_WITHOUT_CANCEL`` ratchet: the list may shrink,
    never grow, and something has to notice when it should have shrunk.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    stale = sorted(i for i in _KNOWN_DIVERGENCES if f"def test_{i}_" in source)
    assert not stale, (
        f"{stale} are listed as known divergences but now have tests. Remove them "
        "from _KNOWN_DIVERGENCES — an exemption that outlives its subject silently "
        "excuses the next one."
    )
    # FLOOR, so the test cannot pass by the constant having been emptied out from
    # under it without anyone deciding to.
    ids = set(_conformance_row_ids())
    unknown = sorted(_KNOWN_DIVERGENCES - ids)
    assert not unknown, (
        f"{unknown} are listed as divergences from rows the shared table does not "
        "have. Either the table changed or this constant is naming nothing."
    )


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
    claimed = set(re.findall(r"^def test_(C\d+[a-z]?)_", source, re.MULTILINE))
    unknown = sorted(claimed - ids)
    assert not unknown, (
        f"test(s) here claim row(s) {', '.join(unknown)}, which the shared table "
        "does not define"
    )


# --- the table GREW and this file did not notice -----------------------------------

#: Conformance rows this file names today. **A ratchet: it may only grow.**
#:
#: **Found 2026-09-13, and the fork found the symptom first.** Their round-18
#: status ran their own self-found checks against our public tree and reported
#: that `HANDSHAKE-OVERRIDE` appears in `docs/handshake-protocol.md` and in **zero**
#: `.py` files here — so C31 (refuse an override missing `-BY`/`-WHY`) and C32
#: (honour it, and print it whenever the round's state is printed) are unimplemented
#: and untested. Verified here rather than accepted: 0 references in any `.py`.
#:
#: **The disease is larger than that row.** This file's docstring says
#: *"`PROTOCOL.md` §8 is a 14-row table… one test per row"*. The shared table now
#: has **36** rows. It grew and the promise did not, which is `CLAUDE.md`'s
#: *does this document promise completeness? then it needs a sweep, not a comment*
#: — decaying invisibly, because a map is only ever wrong by omission.
#:
#: This constant is not the fix. It is the **counter** that makes the gap visible
#: and stops it widening silently while the real work is queued in `TASKS.md`.
#: A conformance row id. **`[a-z]?` is load-bearing and was missing.**
#:
#: The table has one suffixed row, `C13a`, and `C\d+` cannot match it. The fork
#: found this in their round-18 lap 3 §4a, in the ratchet below, one day after it
#: was written — and their own coverage counter has the identical blind spot
#: (`\bC[0-9]+\b`). Same defect, both projects, independently.
#:
#: **Why invisible beats uncovered.** A row the DENOMINATOR cannot include can
#: never be reported as missing: the check would print full coverage while one row
#: had no test at all. That is `CLAUDE.md`'s *can this check be satisfied by
#: finding nothing?* applied to a set rather than a count.
_ROW_ID: str = r"^\| (C\d+[a-z]?) "

#: The same widening on the other side of the comparison. A test that NAMES `C13a`
#: must be counted as covering it; with `\bC\d+\b` the mention would be read as
#: `C13` and the real row would stay uncounted — a false positive and a false
#: negative from one pattern.
_NAMED_ID: str = r"(?<![A-Za-z0-9])C\d+[a-z]?(?![A-Za-z0-9])"

_ROWS_NAMED_HERE: frozenset[str] = frozenset(
    {f"C{n}" for n in range(1, 21)} | {"C13a", "C31", "C32"}
)

#: **What this counts, stated because the first two numbers here were both wrong.**
#: A row counts when a ``test_`` function NAMES it — in its name, docstring or body.
#: That is an UPPER BOUND on behavioural coverage: C13a, C31 and C32 appear only
#: inside assertion messages, so **20 rows have a dedicated ``def test_C<N>_``
#: function and three more are references**.
#:
#: **The honest reading: 23 of 37 named, 14 uncovered — and the 14 are contiguous.**
#: They are C21–C30 and C33–C36, every one of them a row added in v3/v4. That is a
#: far more actionable statement than a bare count, and it only became visible once
#: the pattern could see the tests.
#:
#: **Two wrong numbers preceded it, both published, both from a regex that could not
#: see its subject.** ``C\d+`` reported 36 rows and 6 named (it cannot match
#: ``C13a``); widening it to ``\bC\d+[a-z]?\b`` reported 37 and 9 — still wrong,
#: because ``\b`` does not fire between ``C1`` and the underscore in
#: ``test_C1_the_wire_header``: **``_`` is a word character**, so every one of the
#: twenty rows with a dedicated test was invisible to the check counting them. The
#: fix for a blind spot was written with a different blind spot, and its own comment
#: claimed *"the blind spot cannot return."*
#:
#: Hence ``_NAMED_ID``'s explicit alphanumeric boundaries rather than ``\b``, and
#: hence ``test_no_narrow_row_id_pattern_survives_anywhere_in_this_file``: the sweep
#: is the fix, because this file had **four** places that derive a row id and the
#: first repair reached one of them.


def _rows_named_by_tests() -> set[str]:
    """Row ids named inside a TEST, never in surrounding prose.

    **A scan over the whole file counts comments, which makes the ratchet
    satisfiable by writing ABOUT a row instead of testing it.** Measured
    immediately: widening the id pattern to catch `C13a` took apparent coverage
    from 6 to 10, and all four new ids were ones mentioned in the comment
    explaining the widening. The number went up because prose was added.

    That is `CLAUDE.md`'s *where a check matches on a label, make it also require
    the subject* — the label answers *did they name it*, the body answers *did they
    write it*, and only the pair is a check. So this walks the AST and reads only
    functions whose name starts with `test_`: their names, docstrings and bodies,
    and no module-level comment.
    """
    source = (_REPO_ROOT / "tests" / "test_handshake_conformance.py").read_text(
        encoding="utf-8"
    )
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            found |= set(re.findall(_NAMED_ID, node.name))
            found |= set(
                re.findall(_NAMED_ID, ast.get_source_segment(source, node) or "")
            )
    return found


def test_the_conformance_table_has_not_outgrown_this_file_any_further() -> None:
    """The sweep this file's own completeness claim always needed.

    Derives the row set from the shared protocol rather than from a list here, so
    a row added by either project is counted the round it lands. Asserts two
    things and neither can be satisfied by finding nothing:

    1. the protocol still parses to a substantial table (floor), and
    2. every row this file claims to name is still in the protocol, and
    3. the covered set has not SHRUNK.

    It deliberately does **not** assert full coverage, because that would fail
    today and a red suite is not a record — the shortfall is itemised in
    `TASKS.md` instead, with this counter stopping it growing.
    """
    proto = (_REPO_ROOT / "docs" / "handshake-protocol.md").read_text(encoding="utf-8")
    rows = set(re.findall(_ROW_ID, proto, re.M))
    assert len(rows) >= 30, (
        f"the protocol parses to {len(rows)} conformance row(s); it had 37 on "
        "2026-09-13, so either the table shrank or this parser stopped matching — "
        "and a coverage check over an empty table passes by not looking"
    )
    # THE ROW THE FIRST VERSION OF THIS TEST COULD NOT SEE. Pinned by id, because
    # a suffixed row is invisible to `C\d+` and invisible is worse than uncovered:
    # a denominator that cannot include it reports FULL coverage while it has none.
    assert "C13a" in rows, (
        "the row-id pattern no longer matches C13a. It is the only suffixed row in "
        "the table and the one both projects' counters missed — ours counted 36 "
        "where there are 37, and the fork's own `\\bC[0-9]+\\b` cannot match it "
        "either. If the suffix convention changed, widen _ROW_ID rather than "
        "dropping this assertion."
    )
    named = _rows_named_by_tests()
    stale = _ROWS_NAMED_HERE - rows
    assert not stale, (
        f"this file names conformance row(s) {sorted(stale)} that the protocol no "
        "longer defines — the shared table changed under us"
    )
    covered = rows & named
    assert len(covered) >= len(_ROWS_NAMED_HERE), (
        f"conformance coverage SHRANK: {len(covered)} of {len(rows)} rows NAMED "
        "by a test (an upper bound on real coverage), "
        f"was {len(_ROWS_NAMED_HERE)}. This ratchet may only grow. The "
        f"{len(rows) - len(covered)} uncovered rows are itemised in TASKS.md; "
        "C31/C32 (operator override) are the two the fork found for us."
    )


def test_no_narrow_row_id_pattern_survives_anywhere_in_this_file() -> None:
    """A sweep, because fixing this one site at a time is how it got to four.

    **The incident.** The shared table has one suffixed row, ``C13a``. This file
    derived a row id in **four** places; the fork found the first one, it was
    widened, and its comment said *"so the blind spot cannot return."* The other
    three were still ``C\\d+`` the next day — including
    ``_conformance_row_ids()``, which is what most of the tests here actually call,
    so the repair had reached the ratchet and not the checks.

    That is this repo's own rule twice over: *enforce a rule across the codebase,
    not at the place it was learned*, and *a comment where a check belongs is not a
    fix.* So this greps the file for the narrow form rather than trusting that
    every site was found — the next one gets caught the moment it is written.

    **Scoped to row-id extraction, not to the characters.** A bare ``C\\d+`` inside
    a prose comment ABOUT the defect is not a defect, so the sweep looks only at
    lines that also carry a regex delimiter and a capture, which is what an
    extraction site looks like.
    """
    source = (_REPO_ROOT / "tests" / "test_handshake_conformance.py").read_text(
        encoding="utf-8"
    )
    offenders: list[str] = []
    for number, line in enumerate(source.splitlines(), start=1):
        if (
            "re.findall" not in line
            and "re.compile" not in line
            and "re.match" not in line
        ):
            continue
        # `C\d+` NOT followed by the `[a-z]?` that admits a suffixed row.
        if re.search(r"C\\d\+(?!\[a-z\]\?)", line):
            offenders.append(f"  line {number}: {line.strip()}")

    assert not offenders, (
        "a row-id pattern here is still `C\\d+`, which cannot match `C13a` — the "
        "one suffixed row in the shared table:\n"
        + "\n".join(offenders)
        + "\n\nUse `C\\d+[a-z]?`. A row the denominator cannot include can never be "
        "reported as uncovered, so a narrow pattern prints FULL coverage while a "
        "row has none. This sweep exists because the first repair reached one of "
        "four extraction sites and its comment said the blind spot could not return."
    )

    # FLOOR. The sweep above passes trivially if it is scanning nothing, which is
    # the failure `CLAUDE.md` names as *can this check be satisfied by finding
    # nothing?* — asked, here, of a check written to fix a check.
    widened = len(re.findall(r"C\\d\+\[a-z\]\?", source))
    assert widened >= 3, (
        f"only {widened} widened row-id pattern(s) found in this file; there were "
        "4 extraction sites plus their comments on 2026-09-13. Either they were "
        "removed or this sweep has stopped matching — and a sweep that matches "
        "nothing reports a clean file."
    )
