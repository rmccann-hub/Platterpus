"""Our LSL checker (`scripts/laplang/`) agrees with the fork's, and our amendments work.

The maintainer chose the fork's LSL as the lap language on 2026-09-26, with ours
sent as amendments to it. So this file tests three things, each for a reason
the record gives:

* **Agreement with the other implementation.** The fork's round 27 lap 6 is the
  first real LSL lap. Their checker calls it well formed with a census of 25
  statements, and so must ours, having been written from their spec rather than
  their code. Two implementations of one spec that agree are evidence; where
  they disagree, the disagreement is a finding (three were, all measured).
* **One broken lap per rule id.** Every rule id the checker can emit has a lap
  here that breaks that rule and nothing else, and a floor requires every id to
  have its case. A rule nobody has seen fire is a rule that may not work.
* **A real lap, re-expressed.** `tests/fixtures/lap_language_round27_lap05.md` is
  our round 27 lap 5 in LSL with the amendments. It is clean with every
  amendment on, and LSL 1 alone refuses exactly the parts it has no place for.

The spec and the checker are held to each other: every rule id the code emits is
named in `docs/handshake/outbound/artifacts/lsl-amendments-1.md`, and every id
that document defines is emitted by the code.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from laplang import refs  # noqa: E402 - needs the path line above
from laplang.cli import check_path, main, parse_amendments  # noqa: E402
from laplang.grammar import parse_lap  # noqa: E402
from laplang.model import Lap  # noqa: E402
from laplang.record import LAP_DIRS  # noqa: E402
from laplang.tables import AMENDMENTS  # noqa: E402

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "lap_language_round27_lap05.md"
THEIR_LAP_6 = REPO_ROOT / "docs" / "handshake" / "inbound" / "round-27-lap-06.md"
SPEC = (
    REPO_ROOT / "docs" / "handshake" / "outbound" / "artifacts" / "lsl-amendments-1.md"
)
PACKAGE = REPO_ROOT / "scripts" / "laplang"
ALL = frozenset(AMENDMENTS)

#: Their checker's census of their lap 6, from its own run (S22 of that lap) and
#: reproduced here on 2026-09-26 with `tools/lap-statements.py … --peer`.
THEIR_CENSUS = {
    "ACCEPT": 1,
    "ASK": 1,
    "CORRECT": 2,
    "DID": 2,
    "FACT": 14,
    "NOTE": 1,
    "UNKNOWN": 1,
    "VERDICT": 1,
    "WILL": 2,
}


def _header(
    *,
    author: str = "platterpus",
    round_number: int = 28,
    lap: int = 2,
    verdict: str = "GO",
) -> str:
    return (
        "HANDSHAKE-PROTOCOL: 6\n"
        f"HANDSHAKE-ROUND: {round_number}\n"
        f"HANDSHAKE-LAP: {lap}\n"
        f"HANDSHAKE-FROM: {author}\n"
        f"HANDSHAKE-VERDICT: {verdict}\n\n"
    )


#: A statement that satisfies LSL 1, for the LSL 1 cases to lean on. It carries
#: no amendment field, because LSL 1 alone refuses those (`LSL.field`).
PLAIN_FACT = (
    "S1 FACT measured: The suite passed.\n"
    "  evidence: run: python3 scripts/check.py => 4/4 gates passed\n"
)
#: The same statement, satisfying every amendment too.
GOOD_FACT = PLAIN_FACT + "  holds: platterpus 0.6.61\n  examined: 6021 tests, closed\n"


def _check(
    tmp_path: Path,
    text: str,
    *,
    amend: frozenset[str] = frozenset(),
    root: Path = REPO_ROOT,
    name: str = "lap.md",
) -> Lap:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return check_path(path, root=root, amendments=amend)


def _rules(lap: Lap, severity: str = "REFUSED") -> set[str]:
    return {p.rule for p in lap.problems if p.severity == severity}


def _census(lap: Lap) -> dict[str, int]:
    counts: dict[str, int] = {}
    for stmt in lap.statements:
        counts[stmt.kind] = counts.get(stmt.kind, 0) + 1
    return counts


# --- agreement with the fork's implementation ------------------------------


def test_their_lap_6_is_well_formed_with_the_census_their_checker_gave() -> None:
    lap = check_path(THEIR_LAP_6)
    assert lap.lsl, "their lap 6 declares LSL: 1"
    assert lap.refused() == [], [p.message for p in lap.refused()]
    assert _census(lap) == THEIR_CENSUS


def test_every_lsl_lap_we_hold_from_them_is_well_formed() -> None:
    """A sweep, with a floor: an empty inbox must not pass by finding nothing."""
    checked = 0
    for path in sorted(
        (REPO_ROOT / "docs" / "handshake" / "inbound").glob("round-*-lap-*.md")
    ):
        lap = check_path(path)
        if not lap.lsl:
            continue
        checked += 1
        assert lap.refused() == [], (path.name, [p.message for p in lap.refused()])
    assert checked >= 1, "no LSL lap from the fork was found to check"


@pytest.mark.skipif(
    not (Path("/home/user/cyanrip") / ".git").exists(),
    reason="no clone of the fork's tree here",
)
def test_with_their_tree_their_lap_6_has_no_warnings_either() -> None:
    lap = check_path(THEIR_LAP_6, peer=Path("/home/user/cyanrip"))
    assert lap.problems == [], [p.message for p in lap.problems]


def test_a_platterpus_lap_may_cite_its_own_commits_and_measurements(
    tmp_path: Path,
) -> None:
    """Finding F1: "us" is the lap's author.

    Their checker refuses both statements below, reading "our tree" as cyanrip
    whoever wrote the lap (measured 2026-09-26). The spec says a `DID` names "a
    SHA on our publishing branch", which for this lap is Platterpus's.
    """
    lap = _check(
        tmp_path,
        _header(verdict="OPEN") + "LSL: 1\n\n"
        "S1 DID: We merged the regex fix.\n"
        "  commit: da766ca\n"
        "S2 FACT measured: Our README's first line is its title.\n"
        "  evidence: platterpus@da766ca:README.md:1\n"
        "S3 VERDICT: OPEN\n"
        "  basis: S2\n",
    )
    # No problems at all, not merely no refusals: both statements resolve in our
    # own tree, so even a warning means one was looked for in the wrong tree.
    # (Asserting only "no refusals" let a checker that resolved our commit in the
    # fork's tree pass, because without that clone it warns rather than refuses.)
    assert lap.problems == [], [(p.rule, p.message) for p in lap.problems]


def test_a_commit_a_shallow_clone_cannot_see_is_unchecked_not_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding F3: a missing commit in a shallow clone is a fact about the clone.

    Their checker, run on their own lap 6 in a depth-1 clone of their own tree,
    refused it 15 times (measured 2026-09-26). The stand-in below answers the two
    questions a shallow clone answers: the commit is not here, and yes, shallow.
    """

    def shallow_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args[:1] == ("rev-parse",) and "--is-shallow-repository" in args:
            return subprocess.CompletedProcess(list(args), 0, "true\n", "")
        return subprocess.CompletedProcess(list(args), 1, "", "")

    monkeypatch.setattr(refs, "_git", shallow_git)
    lap = _check(
        tmp_path,
        _header(verdict="OPEN") + "LSL: 1\n\n"
        "S1 DID: Something old.\n  commit: 1234567\n"
        "S2 VERDICT: OPEN\n  basis: S1\n",
    )
    assert lap.refused() == []
    assert any("shallow" in p.message for p in lap.problems if p.severity == "WARN")


# --- one broken lap per rule ---------------------------------------------------


@dataclass(frozen=True)
class Case:
    text: str
    severity: str = "REFUSED"
    amend: frozenset[str] = frozenset()
    #: Extra laps to hold in a scratch record, as {relative path: text}.
    record: tuple[tuple[str, str], ...] = ()
    #: Answer git from a stand-in, for a case whose rule is about the state of a
    #: tree (which branches hold a commit) that no fixed repository can promise.
    branch_only_git: bool = False


def _branch_only_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """A tree where every commit exists, only on `origin/claude/x`, never on main."""
    if args[:2] == ("merge-base", "--is-ancestor"):
        return subprocess.CompletedProcess(list(args), 1, "", "")
    if args[:3] == ("branch", "-r", "--contains"):
        return subprocess.CompletedProcess(list(args), 0, "  origin/claude/x\n", "")
    return subprocess.CompletedProcess(list(args), 0, "line\n" * 50, "")


_BODY_END = "S2 VERDICT: GO\n  basis: S1\n"

_BROKEN: dict[str, Case] = {
    "LSL.1": Case(
        _header() + "LSL: 1\n\nS1 CLAIM: A kind LSL does not have.\n" + _BODY_END
    ),
    "LSL.2": Case(_header() + "LSL: 1\n\nS1 FACT measured: No evidence.\n" + _BODY_END),
    "LSL.3": Case(
        _header() + "LSL: 1\n\n" + PLAIN_FACT + "S3 VERDICT: GO\n  basis: S1\n"
    ),
    "LSL.4": Case(
        _header()
        + "LSL: 1\n\n"
        + PLAIN_FACT
        + "S2 ACCEPT: Their proposal.\n  re: platterpus-fork\n"
        "S3 VERDICT: GO\n  basis: S1\n"
    ),
    "LSL.5": Case(_header(verdict="HOLD") + "LSL: 1\n\n" + PLAIN_FACT + _BODY_END),
    "LSL.6": Case(
        _header()
        + "LSL: 1\n\n"
        + PLAIN_FACT
        + "S2 ASK: Must this hold the pin?\n  target: BLOCKING\n"
        "S3 VERDICT: GO\n  basis: S1\n"
    ),
    "LSL.syntax": Case(
        _header()
        + "LSL: 1\n\n"
        + PLAIN_FACT
        + "A sentence nobody can cite.\n"
        + _BODY_END
    ),
    "LSL.field": Case(
        _header() + "LSL: 1\n\n" + PLAIN_FACT + "  colour: blue\n" + _BODY_END
    ),
    "LSL.value": Case(
        _header()
        + "LSL: 1\n\n"
        + PLAIN_FACT
        + "S2 WILL: Cut the release.\n  owner: someone\n"
        "  when: the round closes\nS3 VERDICT: GO\n  basis: S1\n"
    ),
    "LSL.header": Case(
        _header(author="nobody") + "LSL: 1\n\n" + PLAIN_FACT + _BODY_END
    ),
    "LSL.version": Case(
        _header() + "LSL: 2\n\n" + PLAIN_FACT + _BODY_END, severity="CANNOT"
    ),
    "LSL.file": Case("", severity="CANNOT"),
    "LSL.offrecord": Case(
        _header(verdict="OPEN")
        + "LSL: 1\n\n"
        + "S1 DID: A commit that lives only on a session branch.\n"
        + "  commit: 1234567\n"
        + "S2 VERDICT: OPEN\n  basis: S1\n",
        severity="WARN",
        branch_only_git=True,
    ),
    "LSL.relayed": Case(
        _header()
        + "LSL: 1\n\nS1 FACT relayed: The operator said so.\n  source: the operator\n"
        + _BODY_END,
        severity="WARN",
    ),
    "LSL.unchecked": Case(
        _header() + "LSL: 1\n\nS1 FACT read: Their lap 6 declares GO.\n"
        "  evidence: cyanrip@9e3b76f:meson.build:1\n" + _BODY_END,
        severity="WARN",
    ),
    "A1": Case(
        _header(lap=1)
        + "LSL: 1\n\n"
        + GOOD_FACT
        + "S2 TERM set: The Full run passes.\n  requires: a Full run on the pair\n"
        "S3 VERDICT: GO\n  basis: S1\n",
        amend=ALL,
    ),
    "A2": Case(
        _header(lap=3, verdict="HOLD")
        + "LSL: 1\n\n"
        + GOOD_FACT
        + "S2 VERDICT: HOLD\n  basis: S1\n",
        amend=ALL,
        record=(
            (
                f"{LAP_DIRS['platterpus']}/round-28-lap-01.md",
                _header(lap=1, verdict="OPEN")
                + "LSL: 1\n\n"
                + GOOD_FACT
                + "S2 WILL: Declare GO in our next lap.\n  owner: us\n  when: our next lap\n"
                "  verdict: GO\n  unless: the Full run fails\n"
                "S3 VERDICT: OPEN\n  basis: S1\n",
            ),
        ),
    ),
    "A3": Case(
        _header()
        + "LSL: 1\n\n"
        + GOOD_FACT
        + "S2 FINDING ours: A check of ours read a skip as a stop.\n"
        "  in: platterpus@da766ca:README.md\n  shape: a skip read as a stop\n"
        "  target: NEXT-ROUND\n  evidence: run: pytest => 1 failed\n"
        "S3 VERDICT: GO\n  basis: S1\n",
        amend=ALL,
    ),
    "A4": Case(
        _header()
        + "LSL: 1\n\n"
        + GOOD_FACT.replace("  holds: platterpus 0.6.61\n", "")
        + _BODY_END,
        amend=ALL,
    ),
    "A5": Case(
        _header()
        + "LSL: 1\n\n"
        + GOOD_FACT.replace("6021 tests, closed", "0 tests, closed")
        + _BODY_END,
        amend=ALL,
    ),
    "A6": Case(
        _header(verdict="HOLD")
        + "LSL: 1\n\n"
        + GOOD_FACT
        + "S2 NOTE: We like this less.\n"
        "S3 REFUSE: Their proposal.\n  re: S1\n  because: S2\nS4 VERDICT: HOLD\n  basis: S1\n",
        amend=ALL,
    ),
    "A7": Case(
        _header() + "LSL: 1\n\n" + GOOD_FACT + _BODY_END,
        amend=ALL,
        record=(
            (
                f"{LAP_DIRS['cyanrip']}/round-28-lap-01.md",
                _header(author="cyanrip-fork", lap=1, verdict="OPEN")
                + "LSL: 1\n\n"
                + GOOD_FACT
                + "S2 ASK: Does the pin misread track 3?\n  target: BLOCKING\n"
                "  breaks: every rip of track 3\nS3 VERDICT: OPEN\n  basis: S1\n",
            ),
        ),
    ),
    "A8": Case(
        _header()
        + "LSL: 1\n\n"
        + GOOD_FACT
        + "S2 CORRECT: Our lap 1 named the wrong lap.\n"
        "  re: S1\n  was: round 24\n  now: round 21\n"
        + "S3 VERDICT: GO\n  basis: S1\n",
        amend=ALL,
    ),
}


@pytest.mark.parametrize("rule", sorted(_BROKEN))
def test_each_lap_rule_fires_on_the_lap_that_breaks_it(
    tmp_path: Path, rule: str
) -> None:
    case = _BROKEN[rule]
    root = REPO_ROOT
    if case.record:
        root = tmp_path / "tree"
        for relative, text in case.record:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    if rule == "LSL.file":
        lap = check_path(
            tmp_path, root=root, amendments=case.amend
        )  # a directory cannot be read
    elif case.branch_only_git:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(refs, "_git", _branch_only_git)
            lap = _check(tmp_path, case.text, amend=case.amend, root=root)
    else:
        lap = _check(tmp_path, case.text, amend=case.amend, root=root)
    assert rule in _rules(lap, case.severity), [
        (p.rule, p.message) for p in lap.problems
    ]
    if case.severity == "REFUSED":
        assert _rules(lap) == {rule}, (
            f"the case for {rule} breaks other rules too: {_rules(lap)}"
        )


def _emitted_rule_ids() -> set[str]:
    ids: set[str] = set()
    for path in PACKAGE.glob("*.py"):
        ids |= set(
            re.findall(r'"(LSL\.[a-z0-9]+|A[1-8])"', path.read_text(encoding="utf-8"))
        )
    return ids


def test_every_lap_rule_the_checker_emits_has_a_broken_lap() -> None:
    """The floor for the parametrized test above: no rule id without its case."""
    emitted = _emitted_rule_ids()
    assert len(emitted) >= 20, f"found only {len(emitted)} rule ids; the sweep is wrong"
    assert emitted == set(_BROKEN), {
        "no case": emitted - set(_BROKEN),
        "no rule": set(_BROKEN) - emitted,
    }


def test_the_spec_and_the_checker_define_the_same_rule_ids() -> None:
    named = set(
        re.findall(r"`(LSL\.[a-z0-9]+|A[1-8])`", SPEC.read_text(encoding="utf-8"))
    )
    assert named == _emitted_rule_ids(), {
        "only in spec": named - _emitted_rule_ids(),
        "only in code": _emitted_rule_ids() - named,
    }


def test_a_clean_lap_passes_every_amendment(tmp_path: Path) -> None:
    lap = _check(tmp_path, _header() + "LSL: 1\n\n" + GOOD_FACT + _BODY_END, amend=ALL)
    assert lap.problems == []


# --- the worked example ------------------------------------------------------------


def test_the_worked_example_is_clean_with_every_amendment() -> None:
    lap = check_path(FIXTURE, amendments=ALL)
    assert lap.refused() == [], [p.message for p in lap.refused()]
    assert len(lap.statements) == 31
    warned = {p.rule for p in lap.problems if p.severity == "WARN"}
    assert warned <= {"LSL.unchecked", "LSL.offrecord"}, (
        "the only warnings allowed are the fork's tree (absent here) and our "
        "session-branch commits"
    )
    # Lap 5 cites commits squash merging never put on main (finding F4). The
    # example keeps them, because they are what the real lap cited, and each is
    # named here so that a new off-record citation cannot slip in unremarked.
    branch_only = {"3d2566f", "9c44f5f", "a7b51a8", "caa04f0", "f7519d9", "fafa565"}
    for problem in lap.problems:
        if problem.rule == "LSL.offrecord":
            sha = problem.message.split()[1]
            assert sha in branch_only, problem.message


def test_lsl_1_alone_refuses_only_what_the_amendments_add() -> None:
    """Without the amendments, the example has 12 statements of kinds LSL 1 lacks
    (8 TERM, 4 FINDING) and 14 fields it lacks, and nothing else wrong. Their
    checker gives the same 26, plus 4 that are finding F1 (measured 2026-09-26)."""
    lap = check_path(FIXTURE)
    by_rule: dict[str, int] = {}
    for problem in lap.refused():
        by_rule[problem.rule] = by_rule.get(problem.rule, 0) + 1
    assert by_rule == {"LSL.1": 12, "LSL.field": 14}


def _without_statement(text: str, head: str) -> str:
    """The example with one statement (head line and its fields) removed."""
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith(head))
    end = start + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    return "".join(lines[:start] + lines[end:])


def test_the_examples_go_rests_on_the_forks_pending_half(tmp_path: Path) -> None:
    """Lap 5's GO rested on the fork's half of §0.3, still to come. The prose lap
    never said so; S10 does, and without it A1 refuses the GO."""
    text = FIXTURE.read_text(encoding="utf-8")
    removed = _without_statement(text, "S10 TERM pending")
    renumbered = re.sub(
        r"^S(\d+) ",
        lambda m: f"S{int(m[1]) - 1 if int(m[1]) > 10 else int(m[1])} ",
        removed,
        flags=re.M,
    )
    lap = _check(tmp_path, renumbered, amend=ALL, name="round-27-lap-05.md")
    assert any(p.rule == "A1" and "no status" in p.message for p in lap.refused()), [
        p.message for p in lap.refused()
    ]


def test_a_side_cannot_say_go_over_its_own_pending_half(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8").replace("  on: them\n", "  on: us\n", 1)
    lap = _check(tmp_path, text, amend=ALL)
    assert any(
        p.rule == "A1" and "own pending half" in p.message for p in lap.refused()
    )


def test_a_finding_of_yours_cannot_sit_in_our_own_tree(tmp_path: Path) -> None:
    """A3 says whose a defect is first, and holds the citation to it."""
    text = FIXTURE.read_text(encoding="utf-8").replace(
        "S15 FINDING ours:", "S15 FINDING yours:", 1
    )
    lap = _check(tmp_path, text, amend=ALL)
    assert any(p.rule == "A3" and "our own tree" in p.message for p in lap.refused())


# --- the command line, and never raising ----------------------------------------


def test_exit_codes_are_well_formed_refused_and_cannot_check(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["check", str(FIXTURE), "--amend", "all"]) == 0
    assert main(["check", str(FIXTURE)]) == 1
    prose = REPO_ROOT / "docs" / "handshake" / "outbound" / "round-27-lap-05.md"
    assert main(["check", str(prose)]) == 2
    capsys.readouterr()


def test_amendment_lists_are_validated() -> None:
    assert parse_amendments("all") == ALL
    assert parse_amendments("A1, A3") == frozenset({"A1", "A3"})
    with pytest.raises(Exception, match="unknown amendment"):
        parse_amendments("A9")


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text())
def test_parsing_arbitrary_text_never_raises(text: str) -> None:
    parse_lap("LSL: 1\n" + text, Path("x.md"))
    parse_lap(text, Path("x.md"))


_FIXTURE_LINES = FIXTURE.read_text(encoding="utf-8").splitlines(keepends=True)


@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    st.lists(st.integers(min_value=0, max_value=len(_FIXTURE_LINES) - 1), max_size=12)
)
def test_checking_a_damaged_example_never_raises(
    tmp_path: Path, dropped: list[int]
) -> None:
    """Damage the real example and check it with every amendment on.

    What is under test is that the checker never raises, not git, so git is a
    stand-in that answers at once: with real git each example spawned dozens of
    processes and the test took 29 s (measured by the `--durations` this file's
    session now prints).
    """

    def instant_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(args), 0, "line\n" * 2000, "")

    text = "".join(
        line for i, line in enumerate(_FIXTURE_LINES) if i not in set(dropped)
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(refs, "_git", instant_git)
        _check(tmp_path, text, amend=ALL)
