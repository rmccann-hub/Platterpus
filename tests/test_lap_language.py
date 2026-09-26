"""The lap language checker (`scripts/laplang/`) does what its spec says.

Three kinds of test, and each exists for a reason the record gives:

* **One failing lap per rule.** Every rule id the checker can emit has a lap here
  that breaks exactly that rule, and the test requires that id. A rule with no
  failing example is a rule nobody has seen fire, and "can this check be
  satisfied by finding nothing?" is this project's standing question.
* **A real lap, re-expressed.** `tests/fixtures/lap_language_round27_lap05.md`
  is our round 27 lap 5 written in the language. It must pass with zero problems
  against the real round 27 record, with the real lap 5 taken out, because a
  language that only toy inputs satisfy has not met the thing it is for.
* **The parser never raises.** The fork's laps are external input, and parsers
  of external input here never raise (`CLAUDE.md`). A property test feeds it
  arbitrary text and arbitrary damage to the example.

And the spec and the checker are held to each other: every rule id the code
emits is defined in `docs/handshake/outbound/artifacts/lap-language-1.md`, and
every id the spec defines is emitted by the code.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from laplang.cli import round_files  # noqa: E402 - needs the path line above
from laplang.kinds import KINDS  # noqa: E402
from laplang.model import Lap  # noqa: E402
from laplang.parse import parse_lap  # noqa: E402
from laplang.rounds import check_round, ledger, turn  # noqa: E402

EXAMPLE = REPO_ROOT / "tests" / "fixtures" / "lap_language_round27_lap05.md"
SPEC = REPO_ROOT / "docs" / "handshake" / "outbound" / "artifacts" / "lap-language-1.md"
LAPLANG = REPO_ROOT / "scripts" / "laplang"

#: A valid header for a held mid-round lap, before any statement.
HEADER = """HANDSHAKE-PROTOCOL: 6
HANDSHAKE-LANGUAGE: 1
HANDSHAKE-ROUND: 30
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-READY-TO-READ: no
"""

#: One well-formed statement, to build variations on.
CLAIM = """#### C1 CLAIM measured
The run ripped two tracks, both verified.

- holds-for: platterpus 0.6.60 with cyanrip 0.9.4-rc2+platterpus.16
- method: read the rip report
- tool: none; the report, read directly
- result: two of two verified
- examined: 1 rip, closed
"""


def lap(body: str = CLAIM, header: str = HEADER) -> Lap:
    return parse_lap(header + "\n# A lap\n\n" + body)


def rules(parsed: Lap) -> set[str]:
    return {p.rule for p in parsed.problems}


def test_a_well_formed_lap_has_no_problems() -> None:
    """The floor under every negative test below: the base they vary is clean."""
    parsed = lap()
    assert parsed.uses_language
    assert parsed.problems == ()
    assert [s.sid for s in parsed.statements] == ["C1"]


def test_a_lap_that_does_not_opt_in_is_not_judged() -> None:
    """A v6 lap's body is prose by that protocol; the checker leaves it alone."""
    parsed = parse_lap(
        "HANDSHAKE-PROTOCOL: 6\nHANDSHAKE-ROUND: 30\n\nAny prose at all.\n"
    )
    assert not parsed.uses_language
    assert parsed.problems == ()


# One broken lap per lap-level rule. Each entry: (rule, body, header), where the
# header is HEADER unless the rule is about the header.
_BROKEN: list[tuple[str, str, str]] = [
    ("L1", CLAIM + "\nHANDSHAKE-PIN: 221a1df\n", HEADER),
    ("L2", CLAIM, HEADER.rstrip("\n") + "\nnot a field\n"),
    ("L3", "```\nquoted\n```\n\n" + CLAIM, HEADER),
    ("L4", CLAIM + "Text after the attributes.\n", HEADER),
    ("L5", "#### a heading that is not a statement\n\n" + CLAIM, HEADER),
    ("L6", "A sentence with no statement around it.\n\n" + CLAIM, HEADER),
    ("L7", CLAIM.replace("- tool:", "* tool:"), HEADER),
    ("L8", CLAIM, HEADER + "HANDSHAKE-LAP: 3\n"),
    ("L9", CLAIM, HEADER + "HANDSHAKE-X-TRY: " + "x" * 200 + "\n"),
    ("L10", CLAIM, HEADER + "HANDSHAKE-VERDICT-NOTE: why\n"),
    ("L11", CLAIM, HEADER + "HANDSHAKE-INVENTED: 1\n"),
    (
        "L12",
        CLAIM,
        HEADER + "HANDSHAKE-NEXT-LAP: 6 (yours), transcribing this verdict\n",
    ),
    ("L13", CLAIM + "\n" + CLAIM, HEADER),
    ("L14", CLAIM + "- re: #C9\n", HEADER),
    ("L15", CLAIM, HEADER + "HANDSHAKE-PIN-POLICY: r30l1#C1\n"),
    (
        "L16",
        CLAIM.replace("#### C1 CLAIM measured", "#### C1 CLAIM asserted").replace(
            "- method: read the rip report\n- tool: none; the report, read directly\n"
            "- result: two of two verified\n- examined: 1 rip, closed\n",
            "- unverified-because: not re-run\n",
        ),
        HEADER + "HANDSHAKE-TESTED: #C1\n",
    ),
    (
        "L17",
        "#### C1 CLAIM asserted\nA belief.\n\n- holds-for: x\n- unverified-because: not checked\n\n"
        "#### F1 FINDING yours\nA defect.\n\n- in: cyanrip@221a1df:src/cyanrip_log.c:625\n"
        "- shape: s\n- target: next-round\n- witness: #C1\n",
        HEADER,
    ),
    (
        "L18",
        "#### Q1 QUESTION next-round\nA question.\n\n- to: platterpus\n- wants: answer\n",
        HEADER,
    ),
    ("L19", "#### T1 TERM set\nA condition.\n\n- requires: something\n", HEADER),
    ("L20", CLAIM, HEADER.replace("HANDSHAKE-VERDICT: HOLD", "HANDSHAKE-VERDICT: GO")),
    ("L21", CLAIM.replace("CLAIM measured", "OPINION measured"), HEADER),
    ("L22", CLAIM.replace("#### C1 CLAIM", "#### Q1 CLAIM"), HEADER),
    ("L23", CLAIM.replace("CLAIM measured", "CLAIM guessed"), HEADER),
    ("L24", CLAIM.replace("The run ripped two tracks, both verified.\n", ""), HEADER),
    ("L25", CLAIM.replace("both verified.", "both verified." + " word" * 130), HEADER),
    ("L26", CLAIM + "- colour: blue\n", HEADER),
    ("L27", CLAIM + "- tool: again\n", HEADER),
    (
        "L28",
        CLAIM.replace("- examined: 1 rip, closed", "- examined: some rips"),
        HEADER,
    ),
    ("L29", CLAIM.replace("- tool: none; the report, read directly\n", ""), HEADER),
    (
        "L30",
        CLAIM + "\n#### F1 FINDING yours\nA defect.\n\n"
        "- in: cyanrip@221a1df:src/cyanrip_log.c:625\n- shape: s\n- target: blocking\n"
        "- witness: #C1\n",
        HEADER,
    ),
    (
        "L31",
        CLAIM + "\n#### F1 FINDING ours\nA defect.\n\n"
        "- in: platterpus@7071625:src/platterpus/rip_audit.py:137\n- shape: s\n"
        "- target: next-round\n- witness: #C1\n",
        HEADER,
    ),
    ("L32", CLAIM.replace("1 rip, closed", "3 rips, open"), HEADER),
    (
        "L33",
        CLAIM + "\n#### F1 FINDING ours\nA defect.\n\n"
        "- in: platterpus@7071625:src/platterpus/rip_audit.py:137\n- shape: s\n"
        "- target: fixed\n- witness: #C1\n- portable: no\n",
        HEADER,
    ),
]


@pytest.mark.parametrize(
    ("rule", "body", "header"), _BROKEN, ids=[r for r, _b, _h in _BROKEN]
)
def test_each_lap_rule_fires_on_the_lap_that_breaks_it(
    rule: str, body: str, header: str
) -> None:
    found = rules(lap(body, header))
    assert rule in found, f"{rule} did not fire; the checker reported {sorted(found)}"


def test_every_lap_rule_the_checker_emits_has_a_broken_lap() -> None:
    """The floor under the parametrized test above: its table covers every rule.

    Derived from the checker's source, so a new `L` rule without a failing lap
    fails here by name, and an emptied table cannot pass by generating no cases.
    """
    emitted = set()
    for path in LAPLANG.glob("*.py"):
        emitted |= set(re.findall(r'"(L[0-9]+)"', path.read_text(encoding="utf-8")))
    emitted.discard("L0")
    covered = {rule for rule, _body, _header in _BROKEN}
    assert len(covered) >= 33
    assert emitted - covered == set(), (
        f"lap rules with no broken lap: {sorted(emitted - covered)}"
    )


def _round_lap(
    number: int, author: str, verdict: str, body: str, *, released: bool = True
) -> Lap:
    ready = "yes — operator (rmccann), 2026-09-26" if released else "no"
    header = (
        f"HANDSHAKE-PROTOCOL: 6\nHANDSHAKE-LANGUAGE: 1\nHANDSHAKE-ROUND: 30\n"
        f"HANDSHAKE-LAP: {number}\nHANDSHAKE-FROM: {author}\nHANDSHAKE-VERDICT: {verdict}\n"
        f"HANDSHAKE-READY-TO-READ: {ready}\n"
    )
    if verdict == "GO":
        header += "HANDSHAKE-VERDICT-SOURCE: #C1\nHANDSHAKE-TESTED: #C1\n"
    return lap(body, header)


def _round_rules(*laps: Lap) -> set[str]:
    return {p.rule for _owner, p in check_round(laps)}


_BLOCKING = (
    "#### Q1 QUESTION blocking\nDoes it hold?\n\n- to: platterpus\n- wants: answer\n"
    "- breaks: the pin's one-frame line\n"
)
_TERM = "#### T1 TERM set\nThe real test.\n\n- requires: the Full run\n"


def test_round_rules_fire_on_the_rounds_that_break_them() -> None:
    """R1–R10, each on the smallest round that breaks it."""
    opener = _round_lap(
        1, "cyanrip-fork", "OPEN", CLAIM + "\n" + _BLOCKING + "\n" + _TERM
    )
    assert opener.problems == ()

    assert "R1" in _round_rules(opener, _round_lap(1, "platterpus", "OPEN", CLAIM))
    assert "R2" in _round_rules(
        _round_lap(2, "platterpus", "HOLD", CLAIM + "- re: r30l9#C1\n")
    )
    assert "R3" in _round_rules(
        opener, _round_lap(2, "platterpus", "HOLD", CLAIM + "- re: r30l2#C1\n")
    )
    answer_a_claim = "#### A1 ANSWER yes\nYes.\n\n- answers: r30l1#C1\n"
    assert "R4" in _round_rules(
        opener, _round_lap(2, "platterpus", "HOLD", answer_a_claim)
    )
    own = _round_lap(
        2, "cyanrip-fork", "HOLD", "#### A1 ANSWER yes\nYes.\n\n- answers: r30l1#Q1\n"
    )
    assert "R5" in _round_rules(opener, own)
    wrong_kind = "#### A1 ANSWER accept\nAccepted.\n\n- answers: r30l1#Q1\n"
    assert "R6" in _round_rules(opener, _round_lap(2, "platterpus", "HOLD", wrong_kind))
    assert "R7" in _round_rules(opener, _round_lap(2, "platterpus", "GO", CLAIM))
    assert "R8" in _round_rules(opener, _round_lap(2, "platterpus", "GO", CLAIM))
    promise = (
        CLAIM
        + "\n#### P1 PROMISE verdict\nNext lap is GO.\n\n- due: lap 3\n- verdict: GO\n- unless: a regression\n"
    )
    kept = _round_lap(2, "platterpus", "HOLD", promise)
    assert "R9" in _round_rules(
        opener, kept, _round_lap(3, "platterpus", "HOLD", CLAIM)
    )
    bad_slot = CLAIM + "\n#### T2 TERM met\nMet.\n\n- term: r30l1#C1\n- witness: #C1\n"
    assert "R10" in _round_rules(opener, _round_lap(2, "platterpus", "HOLD", bad_slot))


def test_a_go_stands_over_the_peers_pending_half_but_never_its_own() -> None:
    """Round 27 lap 5 needed this: our GO came before the fork could name `.17`."""
    opener = _round_lap(1, "cyanrip-fork", "OPEN", CLAIM + "\n" + _TERM)
    theirs = (
        CLAIM
        + "\n#### T2 TERM pending\nTheirs remains.\n\n- term: r30l1#T1\n- on: cyanrip-fork\n- remains: their release\n"
    )
    ours = theirs.replace("- on: cyanrip-fork", "- on: platterpus")
    assert "R8" not in _round_rules(opener, _round_lap(2, "platterpus", "GO", theirs))
    assert "R8" in _round_rules(opener, _round_lap(2, "platterpus", "GO", ours))


def test_a_promise_is_kept_or_its_condition_is_claimed() -> None:
    opener = _round_lap(1, "cyanrip-fork", "OPEN", CLAIM)
    promise = (
        CLAIM
        + "\n#### P1 PROMISE verdict\nNext lap is GO.\n\n- due: lap 3\n- verdict: GO\n- unless: a regression\n"
    )
    made = _round_lap(2, "platterpus", "HOLD", promise)
    triggered = CLAIM.replace(
        "- examined: 1 rip, closed\n",
        "- examined: 1 rip, closed\n- triggers: r30l2#P1\n",
    )
    assert "R9" not in _round_rules(
        opener, made, _round_lap(3, "platterpus", "HOLD", triggered)
    )


def test_whose_turn_is_read_from_the_newest_released_lap() -> None:
    body = CLAIM
    first = _round_lap(1, "cyanrip-fork", "OPEN", body)
    header_next = "HANDSHAKE-NEXT-LAP: 3 cyanrip-fork\n"
    second = lap(
        body,
        HEADER.replace("HANDSHAKE-ROUND: 30", "HANDSHAKE-ROUND: 30").replace(
            "HANDSHAKE-READY-TO-READ: no",
            "HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-26",
        )
        + header_next,
    )
    t = turn([first, second])
    assert (t.party, t.lap) == ("cyanrip-fork", 3)
    held = lap(
        body,
        HEADER.replace("HANDSHAKE-LAP: 2", "HANDSHAKE-LAP: 3")
        + "HANDSHAKE-NEXT-LAP: 4 platterpus\n",
    )
    assert turn([first, second, held]).party == "cyanrip-fork", (
        "a held lap does not move the turn"
    )


def test_a_prose_lap_leaves_the_turn_not_determined() -> None:
    """Tri-state: a v6 lap's NEXT-LAP is a sentence, and the answer is 'not determined'."""
    laps = [_load(p) for p in round_files(27)]
    t = turn(laps)
    assert t.party is None
    assert t.detail.startswith("not determined")


def _load(path: Path) -> Lap:
    return parse_lap(path.read_text(encoding="utf-8"), name=path.name)


def test_the_worked_example_is_clean_on_its_own_and_in_its_real_round() -> None:
    example = _load(EXAMPLE)
    assert example.uses_language
    assert example.problems == (), "\n".join(
        p.render(EXAMPLE.name) for p in example.problems
    )
    kinds = {s.kind for s in example.statements}
    assert {"CLAIM", "TERM", "FINDING", "ANSWER", "NOTICE", "PROMISE"} <= kinds
    others = [
        _load(p)
        for p in round_files(27)
        if p.name != "round-27-lap-05.md" or p.parent.name != "outbound"
    ]
    assert len(others) == 4, (
        "round 27 held four other laps when the example was written"
    )
    found = [p for owner, p in check_round([*others, example]) if owner is example]
    assert found == [], "\n".join(p.render(EXAMPLE.name) for p in found)
    t = turn([*others, example])
    assert (t.party, t.lap) == ("cyanrip-fork", 6)
    open_terms = [
        ref
        for ref, _s, state, _st in ledger([*others, example]).terms
        if state not in {"met", "waived"}
    ]
    assert open_terms == ["r27l5#T4"], "only §0.3 remains, and it is theirs"


def test_every_citation_in_the_example_names_a_real_commit_and_line() -> None:
    """The example is evidence, so each `from:` must resolve in the tree it names.

    Only our own citations can be checked here without the fork's tree; theirs are
    checked when the clone is present and skipped, named, when it is not.
    """
    import subprocess

    text = EXAMPLE.read_text(encoding="utf-8")
    cites = re.findall(
        r"^- from: (platterpus|cyanrip)@([0-9a-f]+):([^:\s]+):(\d+)", text, re.M
    )
    assert len(cites) >= 10
    fork = REPO_ROOT.parent / "cyanrip"
    checked = 0
    for repo, sha, path, line in cites:
        root = REPO_ROOT if repo == "platterpus" else fork
        if repo == "cyanrip" and not (fork / ".git").exists():
            continue
        shown = subprocess.run(
            ["git", "-C", str(root), "show", f"{sha}:{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if repo == "cyanrip" and shown.returncode != 0:
            continue  # a shallow clone may not hold the commit; not a finding
        assert shown.returncode == 0, f"{repo}@{sha}:{path} does not exist"
        assert len(shown.stdout.splitlines()) >= int(line), (
            f"{repo}@{sha}:{path} has no line {line}"
        )
        checked += 1
    assert checked >= 8, f"only {checked} citations could be checked"


def test_the_spec_and_the_checker_define_the_same_rules() -> None:
    emitted = set()
    for path in LAPLANG.glob("*.py"):
        emitted |= set(re.findall(r'"([LR][0-9]+)"', path.read_text(encoding="utf-8")))
    emitted.discard("L0")  # an unreadable file, not a rule of the language
    spec = SPEC.read_text(encoding="utf-8")
    defined = set(re.findall(r"^\| `([LR][0-9]+)` \|", spec, re.M))
    assert defined, "the spec's rule table was not found"
    assert emitted - defined == set(), (
        f"rules the checker emits and the spec does not define: {sorted(emitted - defined)}"
    )
    assert defined - emitted == set(), (
        f"rules the spec defines and the checker never emits: {sorted(defined - emitted)}"
    )


def test_the_spec_names_every_kind_and_qualifier() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for kind, (_letter, qualifiers) in KINDS.items():
        assert f"`{kind}`" in spec, kind
        for qualifier in qualifiers:
            assert f"`{qualifier}`" in spec, f"{kind} {qualifier}"


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text())
def test_the_parser_never_raises_on_arbitrary_text(text: str) -> None:
    parse_lap(text)
    parse_lap(HEADER + text)


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.integers(min_value=0, max_value=14000),
    st.integers(min_value=0, max_value=400),
    st.text(max_size=40),
)
def test_the_parser_never_raises_on_a_damaged_real_lap(
    at: int, cut: int, insert: str
) -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    damaged = text[:at] + insert + text[at + cut :]
    parsed = parse_lap(damaged)
    check_round([parsed])
    turn([parsed])
