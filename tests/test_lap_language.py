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

import hashlib
import importlib.util
import os
import pprint
import re
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from laplang import refs, scratch  # noqa: E402 - needs the path line above
from laplang.cli import (  # noqa: E402
    check_path,
    main,
    parse_amendments,
    render,
    render_runs,
)
from laplang.grammar import parse_lap  # noqa: E402
from laplang.model import Lap, RunCoverage  # noqa: E402
from laplang.record import LAP_DIRS  # noqa: E402
from laplang.rerun import (  # noqa: E402
    MARKER_RE,
    appears,
    plan_command,
    quoted_parts,
    split_run,
    stated_exits,
)
from laplang.tables import (  # noqa: E402
    AMENDMENTS,
    LSL3_RULES,
    LSL_VERSIONS,
    carries_no_weight,
)

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


def _load_stale_clone_hint() -> str:
    """`scripts/check.py`'s STALE_CLONE_HINT, loaded by path under its own name so
    it cannot collide with anything else on `sys.path`."""
    spec = importlib.util.spec_from_file_location(
        "_check_for_lap_clone_hint", REPO_ROOT / "scripts" / "check.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    hint: str = module.STALE_CLONE_HINT
    return hint


STALE_CLONE_HINT: str = _load_stale_clone_hint()


def _why(detail: object) -> str:
    """The failure message for an assertion that reads this tree's origin/main.

    The stale-clone check comes first. A fresh cloud session starts shallow with
    an old origin/main, and there these tests failed on laps that were fine,
    showing only the checker's complaint about the lap (2026-09-29 configuration
    re-check, A21).

    **A string, never a tuple.** pytest shows a non-string assertion message
    through `saferepr`, which cuts it at about 240 characters. A tuple therefore
    showed the first line of the hint and lost its fix, and lost most of the
    checker's report (review finding B1, 2026-09-29). A string is shown whole.
    """
    shown = detail if isinstance(detail, str) else pprint.pformat(detail, width=100)
    return f"{STALE_CLONE_HINT}\n\n{shown}"


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
    assert lap.problems == [], _why([(p.rule, p.message) for p in lap.problems])


def test_a_held_back_origin_main_is_named_before_the_checkers_complaint(
    tmp_path: Path,
) -> None:
    """The case behind A21 (2026-09-29), built in a throwaway clone.

    The cited commit is on the remote's main. Only this clone's origin/main is
    behind it, as in a fresh cloud session. The checker still complains, since it
    cannot tell a stale clone from a stranded commit. The message our assertions
    show must then name the clone before the lap.
    """

    def git(root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "commit.gpgsign=false", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "-q", "-b", "main")
    git(upstream, "config", "user.email", "test@example.invalid")
    git(upstream, "config", "user.name", "test")
    for name in ("base", "cited"):
        (upstream / name).write_text(name, encoding="utf-8")
        git(upstream, "add", name)
        git(upstream, "commit", "-q", "-m", name)
    base, cited = (
        git(upstream, "rev-parse", "HEAD~1"),
        git(upstream, "rev-parse", "HEAD"),
    )
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(upstream), str(clone))
    text = (
        _header(verdict="OPEN") + "LSL: 1\n\n"
        f"S1 DID: We merged it.\n  commit: {cited[:7]}\n"
        "S2 VERDICT: OPEN\n  basis: S1\n"
    )
    fresh = _check(tmp_path, text, root=clone)
    assert fresh.problems == [], [(p.rule, p.message) for p in fresh.problems]

    git(clone, "update-ref", "refs/remotes/origin/main", base)
    stale = _check(tmp_path, text, root=clone)
    assert stale.problems, "a held-back origin/main must still be complained about"
    shown = _why([(p.rule, p.message) for p in stale.problems])
    # A string, so pytest prints all of it: the whole hint, fix included, then
    # every complaint the checker made (review finding B1).
    assert isinstance(shown, str)
    assert shown.startswith(STALE_CLONE_HINT)
    assert "git fetch --unshallow origin" in shown
    for problem in stale.problems:
        assert problem.message in shown


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
        _header() + "LSL: 9\n\n" + PLAIN_FACT + _BODY_END, severity="CANNOT"
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
    # LSL 3. No `--amend`: the version line alone switches B1-B3 on.
    "B1": Case(
        # A run: with no at: on a lap with no HANDSHAKE-FROM-COMMIT names no commit.
        _header(verdict="OPEN")
        + "LSL: 3\n\n"
        + GOOD_FACT
        + "S2 VERDICT: OPEN\n  basis: S1\n"
    ),
    "B2": Case(
        # A GO over a round whose held laps set no close condition.
        _header() + "LSL: 3\n\n" + GOOD_FACT + "  at: da766ca\n" + _BODY_END
    ),
    "B3": Case(
        # An answer written as a NOTE, which carries no weight.
        _header(verdict="OPEN")
        + "LSL: 3\n\n"
        + GOOD_FACT
        + "  at: da766ca\n"
        + "S2 NOTE: We will take this up next round.\n  answers: cyanrip:R28.L1.S2\n"
        + "S3 VERDICT: OPEN\n  basis: S1\n",
        record=(
            (
                f"{LAP_DIRS['cyanrip']}/round-28-lap-01.md",
                _header(author="cyanrip-fork", lap=1, verdict="OPEN")
                + "LSL: 1\n\n"
                + PLAIN_FACT
                + "S2 ASK: Will you take this?\n  target: NEXT-ROUND\n"
                + "S3 VERDICT: OPEN\n  basis: S1\n",
            ),
        ),
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
            re.findall(
                r'"(LSL\.[a-z0-9]+|A[1-8]|B[1-9])"', path.read_text(encoding="utf-8")
            )
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
    """Our amendments' spec names every LSL 1 and LSL 2 id the code emits.

    LSL 3's ids are the fork's proposal's, not our amendments', so they are held
    to that text by the test below, and here only to the table that switches
    them on.
    """
    named = set(
        re.findall(r"`(LSL\.[a-z0-9]+|A[1-8])`", SPEC.read_text(encoding="utf-8"))
    )
    emitted = _emitted_rule_ids() - set(LSL3_RULES)
    assert named == emitted, {
        "only in spec": named - emitted,
        "only in code": emitted - named,
    }
    assert _emitted_rule_ids() & {f"B{n}" for n in range(1, 10)} == set(LSL3_RULES)
    assert LSL_VERSIONS[3] - LSL_VERSIONS[2] == frozenset(LSL3_RULES)


def test_a_clean_lap_passes_every_amendment(tmp_path: Path) -> None:
    lap = _check(tmp_path, _header() + "LSL: 1\n\n" + GOOD_FACT + _BODY_END, amend=ALL)
    assert lap.problems == []


def test_lsl_2_is_lsl_1_with_every_amendment_on(tmp_path: Path) -> None:
    """`LSL: 2` switches A1-A8 on by itself (the fork's round 28 lap 3 S14, S18).

    The same statement is refused under `LSL: 2` for lacking A4's and A5's fields,
    and accepted once it carries them, with no `--amend` given either time: the
    version line, not the command line, decides what a lap is held to.
    """
    plain = _check(tmp_path, _header() + "LSL: 2\n\n" + PLAIN_FACT + _BODY_END)
    assert plain.lsl_version == 2
    assert _rules(plain) == {"A4", "A5"}, [(p.rule, p.message) for p in plain.problems]
    good = _check(tmp_path, _header() + "LSL: 2\n\n" + GOOD_FACT + _BODY_END)
    assert good.refused() == [], [p.message for p in good.refused()]
    # And LSL 1 is unchanged: the plain statement passes, the fields are refused.
    assert (
        _check(tmp_path, _header() + "LSL: 1\n\n" + PLAIN_FACT + _BODY_END).refused()
        == []
    )
    assert _rules(
        _check(tmp_path, _header() + "LSL: 1\n\n" + GOOD_FACT + _BODY_END)
    ) == {"LSL.field"}


def test_a_go_says_how_much_it_was_checked_against(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `GO` checked against no close condition passes A1 by finding nothing.

    The fork found that in their checker (round 28 lap 3 S19), and it holds in
    ours: this lap has no `TERM set` anywhere in its round and passes every
    amendment. In LSL 2 the count is printed, so the vacuous pass is on the page
    rather than hidden behind "well formed"; LSL 3's B2 refuses it (below).
    """
    path = tmp_path / "lap.md"
    path.write_text(_header() + "LSL: 2\n\n" + GOOD_FACT + _BODY_END, encoding="utf-8")
    lap = check_path(path)
    assert lap.refused() == []
    assert lap.go_checked_against == {"A1": 0, "A7": 0}
    assert main(["check", str(path)]) == 0
    out = capsys.readouterr().out
    assert "A1: this GO was checked against 0 close condition(s)" in out
    assert "nothing to wait for" in out
    assert "A7: this GO was checked against 0 blocking question(s)" in out
    # The same GO in LSL 3, its run: given the commit it ran at so that B1 has
    # nothing to say: B2 refuses it, and the count that printed 0 is the reason.
    path.write_text(
        _header() + "LSL: 3\n\n" + GOOD_FACT + "  at: da766ca\n" + _BODY_END,
        encoding="utf-8",
    )
    lap = check_path(path)
    assert _rules(lap) == {"B2"}, [(p.rule, p.message) for p in lap.problems]
    assert lap.go_checked_against["A1"] == 0


def test_the_worked_examples_go_names_what_it_waited_on() -> None:
    """Non-triviality for the count above: a GO with close conditions counts them."""
    lap = check_path(FIXTURE, amendments=ALL)
    assert lap.go_checked_against.get("A1", 0) >= 1, lap.go_checked_against


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
    # Since 2026-09-26 the session branch merges into main with a merge commit,
    # so on main these warnings are gone; on a pull request they remain until
    # the merge. A subset check covers both.
    branch_only = {"3d2566f", "9c44f5f", "a7b51a8", "caa04f0", "f7519d9", "fafa565"}
    for problem in lap.problems:
        if problem.rule == "LSL.offrecord":
            sha = problem.message.split()[1]
            assert sha in branch_only, _why(problem.message)


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


# --- LSL 3: B1, B2, B3 -------------------------------------------------------------
#
# The spec is the shared proposal's §"LSL 3", at
# `cyanrip@889a375:docs/handshake/PROPOSAL-lap-statement-language.md:204-252`.

#: Where a clone of the fork's tree may be, for the test that reads their text.
FORK_CLONE = Path("/home/user/cyanrip")
#: Their proposal, as an LSL citation into their tree.
PROPOSAL = "cyanrip@889a375:docs/handshake/PROPOSAL-lap-statement-language.md"


def _fork_proposal() -> str | None:
    """Their proposal at 889a375, when a clone of their tree holds that commit."""
    if not (FORK_CLONE / ".git").exists():
        return None
    shown = subprocess.run(
        ["git", "-C", str(FORK_CLONE), "show", PROPOSAL.split("@", 1)[1]],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return shown.stdout if shown.returncode == 0 else None


def test_lsl_3_is_lsl_2_plus_b1_to_b3_and_nothing_else() -> None:
    assert LSL_VERSIONS[3] == LSL_VERSIONS[2] | {"B1", "B2", "B3"}
    assert LSL_VERSIONS[2] == ALL, "LSL 2 must stay exactly A1-A8"
    # `--amend all` is what it always was: A1-A8, never B1-B3.
    assert parse_amendments("all") == ALL


@pytest.mark.skipif(
    _fork_proposal() is None, reason="no clone of the fork's tree holding 889a375"
)
def test_lsl_3_rule_ids_are_the_ones_their_proposal_defines() -> None:
    """The ids are theirs: read them from the table under their `## LSL 3`."""
    text = _fork_proposal() or ""
    section = text.split("## LSL 3", 1)[1].split("\n## ", 1)[0]
    rows = set(re.findall(r"^\| `(B\d+)` \|", section, re.M))
    assert rows == set(LSL3_RULES), rows
    assert "`LSL: 3`" in text.split("## Syntax", 1)[1].split("\n## ", 1)[0]


def test_the_version_line_names_every_implemented_version(tmp_path: Path) -> None:
    lap = _check(tmp_path, _header() + "LSL: 5\n\n" + PLAIN_FACT + _BODY_END)
    [problem] = [p for p in lap.problems if p.rule == "LSL.version"]
    assert "implements LSL 1, 2, 3 and 4" in problem.message
    opened = _check(tmp_path, _header(verdict="OPEN") + "LSL: 3\n\nS1 VERDICT: OPEN\n")
    assert opened.lsl_version == 3


@pytest.mark.parametrize(
    ("portable", "target", "refused"),
    [
        ("no", "NEXT-ROUND", True),
        ("no", "FIXED", True),
        ("no", "BLOCKING", False),
        ("yes", "NEXT-ROUND", False),
    ],
)
def test_a_finding_of_ours_that_neither_travels_nor_blocks_is_for_a_commit(
    tmp_path: Path, portable: str, target: str, refused: bool
) -> None:
    """The fork's A3 amendment, accepted in our round 28 lap 2 S11 and not built
    until their round 30 lap 7 S2 found our lap 6 S15 passing it."""
    extra = {
        "FIXED": "  landed: platterpus@da766ca:README.md\n",
        "BLOCKING": "  breaks: platterpus:R28.L1.S1\n",
    }.get(target, "")
    text = (
        _header(verdict="OPEN")
        + "LSL: 3\n\n"
        + GOOD_FACT
        + "S2 FINDING ours: A check of ours read a skip as a stop.\n"
        "  in: platterpus@da766ca:README.md\n  shape: a skip read as a stop\n"
        f"  target: {target}\n{extra}  evidence: platterpus@da766ca:README.md\n"
        f"  portable: {portable}\n"
        "S3 VERDICT: OPEN\n  basis: S1\n"
    )
    lap = _check(tmp_path, text, amend=ALL)
    hits = [p for p in lap.refused() if "for a commit, not a lap" in p.message]
    assert bool(hits) is refused, [p.message for p in lap.refused()]


def test_our_round_30_lap_6_S15_is_refused_as_the_forks_checker_refuses_it() -> None:
    """Our sent lap 6 broke the rule; it is frozen, so the record says so.

    Both checkers now read it the same way: one refusal, S15's, and nothing else.
    """
    path = REPO_ROOT / "docs/handshake/outbound/round-30-lap-06.md"
    lap = check_path(path)
    refusals = lap.refused()
    assert [(p.rule, "for a commit, not a lap" in p.message) for p in refusals] == [
        ("A3", True)
    ], [p.message for p in refusals]
    assert "S15" in refusals[0].message


def test_the_help_names_every_implemented_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--help` says what the checker implements, from the same table."""
    from laplang import cli

    with pytest.raises(SystemExit):
        cli.main(["--help"])
    assert "LSL 1, 2, 3 and 4" in " ".join(capsys.readouterr().out.split())


_PRE_COMMIT = (
    "S2 WILL: Our next lap is GO unless the run fails.\n"
    "  owner: us\n"
    "  when: {when}\n"
    "  verdict: GO\n"
    "  unless: the run fails\n"
)


@pytest.mark.parametrize(
    ("version", "when", "refused"),
    [
        (4, "our next lap", False),
        (4, "once the bundle is committed to our tree", True),
        (3, "once the bundle is committed to our tree", False),
    ],
)
def test_lsl_4_holds_a_pre_commit_to_the_one_literal(
    tmp_path: Path, version: int, when: str, refused: bool
) -> None:
    """LSL 4's C1 (round 30: their lap 3 S10, our lap 4 S36, their lap 5 S12):
    under `LSL: 4` a WILL carrying verdict: says exactly `when: our next lap`,
    refused under A2 otherwise; an LSL 3 lap keeps the rule it was written
    under, so the same prose is accepted there."""
    body = PLAIN_FACT + _PRE_COMMIT.format(when=when) + "S3 VERDICT: GO\n  basis: S1\n"
    lap = _check(tmp_path, _header() + f"LSL: {version}\n\n" + body)
    assert lap.lsl_version == version
    c1 = [p for p in lap.problems if p.rule == "A2" and "LSL 4" in p.message]
    assert bool(c1) is refused, [p.message for p in lap.problems]


#: Our checker's report on each committed round-28 lap: once as filed (`LSL: 1`)
#: and once with that line read as `LSL: 2`, as sha256/16 of `render()`'s text,
#: and the LSL 2 refusals by rule. Measured on 2026-09-28 with the checker as it
#: was BEFORE LSL 3 was written (`scripts/laplang` at b592567a), so this pins that
#: LSL 3 changed no LSL 1 or LSL 2 report. A deliberate change to an LSL 1 or 2
#: message moves these; the assertion prints the new report, to be read before
#: the number is updated.
_ROUND_28_REPORTS: dict[str, tuple[str, str, dict[str, int]]] = {
    "inbound/round-28-lap-01.md": (
        "72bc7a652c4c088a",
        "d4016340ff98dbf0",
        {"A4": 10, "A5": 4},
    ),
    "inbound/round-28-lap-03.md": (
        "255ac576861cf2db",
        "39dd191508fc9817",
        {"A4": 14, "A5": 5},
    ),
    "outbound/round-28-lap-02.md": (
        "e0c3dd06d9b9b6d1",
        "662b9b57e0748fd9",
        {"A4": 8, "A5": 3},
    ),
    "outbound/round-28-lap-04.md": (
        "e52218380b67e83f",
        "1091d1c55df9756e",
        {"A4": 15, "A5": 7},
    ),
    # Our held lap 5 was measured here too ("2165401650fe6fac", "fb67e28adfed5761",
    # A4 27, A5 10). It was rewritten and released as lap 7 on 2026-09-28, after the
    # fork's lap 5 took that number, so the measurement describes a file that no
    # longer exists, and it is dropped rather than re-measured: a report taken now
    # would be the LSL 3 checker's, which is what this pin exists to compare against.
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def test_the_round_28_pin_covers_every_lap_it_was_measured_on() -> None:
    """The floor for the pin below: the round-28 laps measured on 2026-09-28 that
    are still the files measured, laps 1 to 4.

    Every one of them is pinned and still on disk where the pin says, so the pin
    cannot pass by having nothing, or less, left to compare. (That each still
    declares `LSL: 1` is asserted by the pinned test itself.) Laps from 5 on were
    written after LSL 3, so there is no pre-LSL-3 report of them to hold.
    """
    held = {
        path.relative_to(REPO_ROOT / "docs" / "handshake").as_posix()
        for side in ("inbound", "outbound")
        for path in (REPO_ROOT / "docs" / "handshake" / side).glob(
            "round-28-lap-0[1-4].md"
        )
    }
    assert len(held) == 4, held
    assert set(_ROUND_28_REPORTS) == held


@pytest.mark.parametrize("name", sorted(_ROUND_28_REPORTS))
def test_lsl_1_and_2_reports_on_round_28_are_unchanged(
    tmp_path: Path, name: str
) -> None:
    as_filed, as_lsl_2, refusals = _ROUND_28_REPORTS[name]
    path = REPO_ROOT / "docs" / "handshake" / name
    text = path.read_text(encoding="utf-8")
    assert re.search(r"^LSL: 1$", text, re.M), f"{name} no longer declares LSL: 1"
    lap = check_path(path)
    report, code = render(lap)
    assert (code, _digest(report)) == (0, as_filed), _why(report)
    assert lap.runs is None and "B1:" not in report
    rewritten = tmp_path / path.name
    rewritten.write_text(
        re.sub(r"^LSL: 1$", "LSL: 2", text, count=1, flags=re.M), encoding="utf-8"
    )
    lap = check_path(rewritten)
    report, code = render(lap)
    by_rule: dict[str, int] = {}
    for problem in lap.refused():
        by_rule[problem.rule] = by_rule.get(problem.rule, 0) + 1
    assert by_rule == refusals, _why(report)
    assert (code, _digest(report)) == (1, as_lsl_2), _why(report)
    assert lap.runs is None and "B1:" not in report


# The relation between this checker and the handshake gate's R6: two surfaces
# answering "is this a pre-commit?", which must agree (review finding R15).


def _handshake_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "handshake_for_lsl_relation", REPO_ROOT / "scripts" / "handshake.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("version", "owner", "refused_by"),
    [
        # LSL 2: A2 is in force, and refuses only a promise the author cannot
        # make (`owner: them`). The rules are tuples, not sets, so the
        # population is literal (tests/test_dynamic_sweeps_declare_a_floor.py).
        (2, "us", ()),
        (2, "them", ("A2",)),
        # LSL 3 is LSL 2 plus B1-B3, so A2 is in force there too.
        (3, "us", ()),
        (3, "them", ("A2",)),
        # LSL 1: A2 is not in force, and `verdict:` and `unless:` are not LSL 1
        # fields, so the lap's own language refuses the WILL whoever owns it
        # (review finding Q6).
        (1, "us", ("LSL.field",)),
        (1, "them", ("LSL.field",)),
    ],
)
def test_r6_counts_exactly_the_pre_commits_a2_accepts(
    tmp_path: Path, version: int, owner: str, refused_by: tuple[str, ...]
) -> None:
    """A lap 5 of round 99 whose only pre-commit is A2's structured `WILL`. When
    the lap's own LSL accepts it, R6 must count it; when LSL refuses it, R6 must
    not. Before R15, R6 refused the LSL 2 lap A2 accepted, as "carries no
    pre-commit". Before Q6, R6 counted the LSL 1 one, which LSL 1 refuses because
    it defines neither field: the gate passed a statement the lap's own
    language calls malformed."""
    # LSL 1 refuses the amendment fields GOOD_FACT carries, so an LSL 1 lap
    # leans on PLAIN_FACT, and the WILL is the only thing that differs.
    fact = PLAIN_FACT if version == 1 else GOOD_FACT
    # LSL 3's B1 wants the commit a `run:` ran at; the lap header names it.
    commit = _FROM_COMMIT if version == 3 else ""
    text = (
        # **Round 99, not 29** (moved 2026-09-28). The checker reads the REAL laps
        # of the lap's round for A2's cross-lap promise, and this used to name
        # round 29, which had none. Once our real round 29 lap 2 pre-committed a
        # `GO`, this made-up lap 5 was bound by it and refused under A2 for
        # declaring HOLD: the case was testing the repository's state, not the
        # rule. A round no real lap will reach keeps it about the rule alone.
        _header(round_number=99, lap=5, verdict="HOLD").rstrip("\n")
        + "\n"
        + commit
        + f"\nLSL: {version}\n\n"
        + fact
        + f"S2 WILL: Declare GO in our next lap.\n  owner: {owner}\n"
        "  when: our next lap\n  verdict: GO\n  unless: the Full run fails\n"
        "S3 VERDICT: HOLD\n  basis: S1\n"
    )
    lap = _check(tmp_path, text)
    lsl_accepts = lap.refused() == []
    # The only thing wrong with each lap is the one the case names.
    assert {p.rule for p in lap.problems} == set(refused_by), [
        (p.rule, p.message) for p in lap.problems
    ]
    assert lsl_accepts == (not refused_by)
    if version == 1:
        # ... and it is the two fields LSL 1 does not define that it refuses.
        messages = [p.message for p in lap.refused()]
        assert len(messages) == 2, messages
        assert any("verdict: is not a field" in m for m in messages), messages
        assert any("unless: is not a field" in m for m in messages), messages
    # NON-TRIVIALITY: the sentence does not carry the prose form, so the
    # structured fields are the only thing R6 can count.
    assert "is `GO` unless" not in text and "is GO unless" not in text
    r6 = _handshake_module().pre_commit_problems(text, "round-99-lap-05.md")
    assert (r6 == []) == lsl_accepts, r6
    if not lsl_accepts:
        assert len(r6) == 1 and "carries no pre-commit" in r6[0], r6
    if version == 1 and owner == "us":
        # The refusal says why the WILL did not count, and where it would.
        assert "S2 WILL states verdict: GO and unless:" in r6[0], r6
        assert "this lap declares LSL 1" in r6[0], r6
        assert "in LSL 2, 3 or 4, as a WILL" in r6[0], r6


# B1 without --rerun: every run: names the commit it ran at.

_FROM_COMMIT = "HANDSHAKE-FROM-COMMIT: da766ca\n"


def _lsl3(body: str, *, verdict: str = "OPEN", extra_header: str = "") -> str:
    """An LSL 3 lap of ours: `body` is S1-S8, and S9 is the VERDICT."""
    return (
        _header(verdict=verdict).rstrip("\n")
        + "\n"
        + extra_header
        + "\nLSL: 3\n\n"
        + body
        + f"S9 VERDICT: {verdict}\n  basis: S1\n"
    )


def _measured(n: int, run: str, *, at: str | None = None) -> str:
    """A FACT measured that satisfies A4 and A5, with `run` as its evidence."""
    return (
        f"S{n} FACT measured: It printed what the lap says.\n"
        f"  evidence: run: {run}\n"
        + (f"  at: {at}\n" if at is not None else "")
        + "  holds: platterpus 0.6.61\n  examined: 1 run, closed\n"
    )


def _numbered(*statements: str) -> str:
    """`statements` as S1.., then NOTEs up to S8, so the VERDICT is S9."""
    filler = [f"S{n} NOTE: Nothing here.\n" for n in range(len(statements) + 1, 9)]
    return "".join(statements) + "".join(filler)


def test_b1_a_run_is_satisfied_by_an_at_or_by_the_lap_header(tmp_path: Path) -> None:
    by_at = _check(tmp_path, _lsl3(_numbered(_measured(1, "true => ok", at="da766ca"))))
    assert by_at.problems == [], _why([(p.rule, p.message) for p in by_at.problems])
    by_header = _check(
        tmp_path,
        _lsl3(_numbered(_measured(1, "true => ok")), extra_header=_FROM_COMMIT),
    )
    assert by_header.problems == [], _why(
        [(p.rule, p.message) for p in by_header.problems]
    )
    neither = _check(tmp_path, _lsl3(_numbered(_measured(1, "true => ok"))))
    assert _rules(neither) == {"B1"}
    [problem] = neither.refused()
    assert "has neither" in problem.message
    assert problem.line == neither.statements[0].fields[0].line


@pytest.mark.parametrize(
    ("at", "why"),
    [
        ("cyanrip@da766ca", "cyanrip's tree"),
        ("main", "not 'main'"),
        ("platterpus@da766ca:README.md", "not 'platterpus@da766ca:README.md'"),
        ("0000000", "does not resolve"),
    ],
)
def test_b1_refuses_an_at_that_is_not_a_commit_of_the_authors_tree(
    tmp_path: Path, at: str, why: str
) -> None:
    lap = _check(tmp_path, _lsl3(_numbered(_measured(1, "true => ok", at=at))))
    assert _rules(lap) == {"B1"}, _why([(p.rule, p.message) for p in lap.problems])
    assert any(why in p.message for p in lap.refused()), _why(
        [p.message for p in lap.refused()]
    )


@pytest.mark.parametrize("at", ["da766ca", "platterpus@da766ca"])
def test_b1_an_at_that_is_a_commit_alone_is_accepted(tmp_path: Path, at: str) -> None:
    """The two forms an `at:` has: a commit, bare or with its side."""
    lap = _check(tmp_path, _lsl3(_numbered(_measured(1, "true => ok", at=at))))
    assert lap.problems == [], _why([(p.rule, p.message) for p in lap.problems])


@pytest.mark.parametrize(
    ("at", "rest"),
    [
        ("da766ca (the release)", "'(the release)'"),
        # Continuation spacing and all: whatever follows the commit's word.
        ("platterpus@da766ca   the tip then", "'the tip then'"),
    ],
)
def test_b1_refuses_an_at_with_anything_after_its_commit(
    tmp_path: Path, at: str, rest: str
) -> None:
    """Round 29's reading (the fork's lap 1 S29, accepted): an `at:` is a commit
    and nothing else. We used to read its first word and drop the rest, so both
    of these were accepted as `da766ca`, a commit that resolves here: the commit
    is good, so only the prose after it can be what is refused."""
    lap = _check(tmp_path, _lsl3(_numbered(_measured(1, "true => ok", at=at))))
    assert _rules(lap) == {"B1"}, [(p.rule, p.message) for p in lap.problems]
    [problem] = lap.refused()
    assert "an at: names a commit and nothing else" in problem.message
    assert rest in problem.message, problem.message
    at_line = next(f.line for f in lap.statements[0].fields if f.name == "at")
    assert problem.line == at_line


_PROSE_HEADER = "HANDSHAKE-FROM-COMMIT: see §H, a lap cannot carry its own\n"


def test_b1_refuses_each_run_leaning_on_a_header_that_names_no_single_commit(
    tmp_path: Path,
) -> None:
    """Round 29's reading (the fork's lap 1 S29, accepted): a `run:` with no
    `at:` needs the lap's `HANDSHAKE-FROM-COMMIT` to name one commit, and is
    refused when it names none. We used to warn, reading B1's row as asking only
    whether the header is there. It is each `run:` that is refused, once each."""
    runs = _numbered(_measured(1, "true => ok"), _measured(2, "false => no"))
    lap = _check(tmp_path, _lsl3(runs, extra_header=_PROSE_HEADER))
    assert _rules(lap) == {"B1"}, [(p.rule, p.message) for p in lap.problems]
    assert [p.rule for p in lap.problems] == ["B1", "B1"], lap.problems
    assert sorted(p.line for p in lap.refused()) == [
        lap.statements[0].fields[0].line,
        lap.statements[1].fields[0].line,
    ]
    for problem in lap.refused():
        assert "names no single commit" in problem.message, problem.message
        assert "not a commit" in problem.message, problem.message
    # Declared twice, it names no single commit: the protocol does not let a
    # reader settle a doubly-declared field by taking the first.
    twice = _check(
        tmp_path,
        _lsl3(
            _numbered(_measured(1, "true => ok")),
            extra_header=_FROM_COMMIT + "HANDSHAKE-FROM-COMMIT: 785925a\n",
        ),
    )
    assert _rules(twice) == {"B1"}, [(p.rule, p.message) for p in twice.problems]
    [problem] = twice.refused()
    assert "declared 2 times" in problem.message


def test_b1_does_not_refuse_such_a_header_where_no_run_needs_it(
    tmp_path: Path,
) -> None:
    """The header is `PROTOCOL.md`'s, not LSL's: B1 refuses the `run:` that leans
    on it, so a lap whose every `run:` names its own commit by an `at:`, or that
    has no `run:` at all, is not refused for it."""
    by_at = _check(
        tmp_path,
        _lsl3(
            _numbered(_measured(1, "true => ok", at="da766ca")),
            extra_header=_PROSE_HEADER,
        ),
    )
    assert by_at.problems == [], _why([(p.rule, p.message) for p in by_at.problems])
    no_run = _check(
        tmp_path,
        _lsl3(
            _numbered(
                "S1 FACT read: Our README's first line is its title.\n"
                "  evidence: platterpus@da766ca:README.md:1\n"
                "  holds: platterpus@da766ca\n"
            ),
            extra_header=_PROSE_HEADER,
        ),
    )
    assert no_run.problems == [], _why([(p.rule, p.message) for p in no_run.problems])
    assert no_run.runs is not None and no_run.runs.total == 0


def test_rerun_on_an_lsl_2_lap_says_it_re_ran_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "lap.md"
    path.write_text(_header() + "LSL: 2\n\n" + GOOD_FACT + _BODY_END, encoding="utf-8")
    assert main(["check", str(path), "--rerun"]) == 0
    assert "B1 is LSL 3's, so nothing was re-run" in capsys.readouterr().out


# B1 with --rerun, against a real repository made for the test.


def _git_repo(
    tmp_path: Path, files: dict[str, str], *, executable: tuple[str, ...] = ()
) -> tuple[Path, str]:
    """A git repository of `files` on `main`, one commit: (its path, the commit)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for name, text in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if name in executable:
            target.chmod(0o755)
    _in(repo, "init", "-q", "-b", "main")
    _commit(repo, "the tree the laps ran at")
    return repo, _in(repo, "rev-parse", "--short=12", "HEAD").strip()


def _in(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout


def _commit(repo: Path, message: str) -> None:
    """Commit everything in `repo`, as a test identity, unsigned."""
    _in(repo, "add", "-A")
    _in(
        repo,
        "-c",
        "user.name=lap test",
        "-c",
        "user.email=lap-test@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-q",
        "-m",
        message,
    )


def test_a_final_line_without_a_newline_can_be_cited(tmp_path: Path) -> None:
    """Our round 29 lap 4 S33, accepted as their round 30 lap 1 S20: the last line
    counts whether or not it ends in a newline. Resolved through a real
    repository, since the count is taken from `git show`'s output."""
    assert refs.line_count("") == 0
    assert refs.line_count("banner") == 1
    assert refs.line_count("banner\n") == 1
    assert refs.line_count("a\nb") == 2
    repo, sha = _git_repo(
        tmp_path, {"one.txt": "cyanrip 0.9.4 banner", "two.txt": "a\nb\n"}
    )
    trees = refs.Trees({"platterpus": repo, "cyanrip": None}, {"platterpus": "main"})
    for token, outcome in (
        (f"platterpus@{sha}:one.txt:1", "ok"),
        (f"platterpus@{sha}:one.txt:2", "refused"),
        (f"platterpus@{sha}:two.txt:2", "ok"),
        (f"platterpus@{sha}:two.txt:3", "refused"),
    ):
        ref = refs.parse_artifact(token)
        assert ref is not None, token
        got = trees.artifact(ref, "cyanrip")
        assert got.outcome == outcome, (token, got)


def _worktrees(repo: Path) -> list[str]:
    listed = _in(repo, "worktree", "list", "--porcelain")
    return [line for line in listed.splitlines() if line.startswith("worktree ")]


_TOOLS: dict[str, str] = {
    "tools/marked.py": "#!/usr/bin/env python3\n# LSL-RERUN: commit-only\nprint('hello 42')\n",
    "tools/direct.py": (
        "#!/usr/bin/env python3\n# LSL-RERUN: commit-only\n"
        "import sys\nprint('direct', sys.argv[1])\n"
    ),
    "tools/unmarked.py": "print('hello 42')\n",
    "tools/mentions.py": "'''Says LSL-RERUN: commit-only in prose.'''\nprint('hello 42')\n",
    "data.txt": "alpha\nbeta\ngamma\n",
}


def test_b1_without_rerun_executes_nothing_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sentinel = tmp_path / "ran"
    repo, sha = _git_repo(
        tmp_path,
        {
            "tool.py": "# LSL-RERUN: commit-only\n"
            f"open({str(sentinel)!r}, 'w').close()\nprint('hi')\n"
        },
    )
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(_measured(1, 'python3 tool.py => "hi"', at=sha))),
        encoding="utf-8",
    )
    assert main(["check", str(path), "--root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "B1: 1 run: result(s); none re-run, because --rerun was not given" in out
    assert not sentinel.exists(), "a check without --rerun executed the lap's command"
    # With --rerun it does run: the sentinel is the proof the two differ.
    assert main(["check", str(path), "--root", str(repo), "--rerun"]) == 0
    assert "1 re-run and matched" in capsys.readouterr().out
    assert sentinel.exists()


def test_rerun_matches_refuses_and_reports_each_run(tmp_path: Path) -> None:
    repo, sha = _git_repo(tmp_path, _TOOLS, executable=("tools/direct.py",))
    data_hash = hashlib.sha256(b"alpha\nbeta\ngamma\n").hexdigest()
    matched = [
        'python3 tools/marked.py => "hello 42"',
        'tools/direct.py x => exit 0, "direct x"',
        'git show HEAD:data.txt => "alpha…gamma"',
        f'sha256sum data.txt => "{data_hash}"',
        "git log --format='%s' -1 => \"the tree the laps ran at\"",
        # The spaces around an ellipsis are the elision's: the output has
        # newlines there, and an honest lap is not refused for its typography.
        'git show HEAD:data.txt => "alpha … gamma"',
    ]
    refused = [
        'python3 tools/marked.py => "goodbye"',
        'git show HEAD:data.txt => "gamma…alpha"',
    ]
    unchecked = {
        'python3 tools/unmarked.py => "hello 42"': "does not declare the re-run marker",
        'python3 tools/mentions.py => "hello 42"': "does not declare the re-run marker",
        'git log | head => "x"': "needs a shell",
        "wc -l data.txt => 3 lines": "quotes nothing, so it is prose",
        'git log main -1 => "x"': "names the ref 'main'",
        'git log --since=yesterday => "x"': "reads the clock",
        'cat data.txt => "alpha"': "is not git, sha256sum, wc",
        'python3 tools/missing.py => "x"': "is not a file of the author's tree",
        'wc -l /etc/hostname => "1"': "is an absolute path",
    }
    runs = matched + refused + list(unchecked)
    body = "".join(_measured(n, run, at=sha) for n, run in enumerate(runs, start=1))
    text = (
        _header(verdict="OPEN")
        + "LSL: 3\n\n"
        + body
        + f"S{len(runs) + 1} VERDICT: OPEN\n  basis: S1\n"
    )
    path = tmp_path / "lap.md"
    path.write_text(text, encoding="utf-8")
    before = _worktrees(repo)
    lap = check_path(path, root=repo, rerun=True)
    problems = [(p.rule, p.message) for p in lap.problems]
    assert lap.runs is not None
    counts = (lap.runs.total, lap.runs.matched, lap.runs.mismatched, lap.runs.not_rerun)
    assert counts == (17, 6, 2, 9), problems
    assert _rules(lap) == {"B1"}
    evidence_line = {s.n: s.fields[0].line for s in lap.statements}
    first_refused = len(matched) + 1
    assert sorted(p.line for p in lap.refused()) == [
        evidence_line[first_refused],
        evidence_line[first_refused + 1],
    ]
    assert all("is not in the output" in p.message for p in lap.refused())
    warned = {p.line: p for p in lap.problems if p.severity == "WARN"}
    assert {p.rule for p in warned.values()} == {"LSL.unchecked"}
    first_unchecked = len(matched) + len(refused) + 1
    for n, (run, why) in enumerate(unchecked.items(), start=first_unchecked):
        assert why in warned[evidence_line[n]].message, (run, warned[evidence_line[n]])
    # The scratch checkouts are gone, from the clone's record and from the disk.
    assert _worktrees(repo) == before
    assert lap.runs.leftovers == []
    report, code = render(lap)
    assert code == 1
    assert (
        "B1: 17 run: result(s): 6 re-run and matched, 2 re-run and not matched, "
        "9 could not be re-run"
    ) in report


def test_a_quoted_oneline_hash_does_not_depend_on_the_rerunning_clone(
    tmp_path: Path,
) -> None:
    """Git sizes an abbreviation by the clone's object count; the re-run must not.

    The fork's round 29 lap 3 S23 quoted `git log --oneline` as `f8ebf48 src/…`,
    right for its blob-less clone; our full clone printed `f8ebf48f` and refused it.
    The clone here asks for twelve characters, as a bigger clone would get, and the
    lap quotes seven.
    """
    repo, sha = _git_repo(tmp_path, _TOOLS)
    subprocess.run(["git", "-C", str(repo), "config", "core.abbrev", "12"], check=True)
    short = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline", "-1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert len(short.split()[0]) == 12, "the floor: this clone abbreviates longer"
    subject = short.split(" ", 1)[1].strip()
    run = f'git log --oneline -1 => "{sha[:7]} {subject}"'
    text = (
        _header(verdict="OPEN")
        + "LSL: 3\n\n"
        + _measured(1, run, at=sha)
        + "S2 VERDICT: OPEN\n  basis: S1\n"
    )
    path = tmp_path / "lap.md"
    path.write_text(text, encoding="utf-8")
    lap = check_path(path, root=repo, rerun=True)
    assert lap.runs is not None
    assert (lap.runs.matched, lap.runs.mismatched) == (1, 0), [
        p.message for p in lap.problems
    ]


#: A marked tool that prints a count and FAILS, and one that prints the words
#: `exit 0` and fails, for the exit-status cases.
_FAILING_TOOLS: dict[str, str] = {
    **_TOOLS,
    "tools/fails.py": "# LSL-RERUN: commit-only\nimport sys\n"
    "print('round 27: 12 lap(s), 10 failed')\nsys.exit(1)\n",
    "tools/says_exit.py": "# LSL-RERUN: commit-only\nimport sys\n"
    "print('exit 0')\nsys.exit(1)\n",
}


def test_a_rerun_that_failed_is_matched_but_never_silently(tmp_path: Path) -> None:
    """Review finding R13, for a result that states NO exit code. B1 compares
    such a result's quoted strings, stdout and stderr together, and nothing
    else, so a failed command is not REFUSED for failing. But it was reported as
    a plain match: "0 failed" is in "10 failed", and sha256sum's error message
    repeats the file name it could not open. Each is a match with an UNCHECKED
    exit: warning, counted apart on the report line. Round 29 left this case
    exactly as it was (the fork's lap 1 S28: "a result that states none is
    UNCHECKED when the command exits non-zero"); a result that states `exit N`
    is held to it, below."""
    repo, sha = _git_repo(tmp_path, _FAILING_TOOLS)
    runs = [
        'python3 tools/fails.py => "0 failed"',
        'sha256sum "all 91 tests passed" => "all 91 tests passed"',
        'python3 tools/marked.py => "hello 42"',
    ]
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(*[_measured(n, r, at=sha) for n, r in enumerate(runs, 1)])),
        encoding="utf-8",
    )
    lap = check_path(path, root=repo, rerun=True)
    assert lap.refused() == [], "B1's text refuses only a quoted string not printed"
    assert lap.runs is not None
    assert (lap.runs.matched, lap.runs.matched_nonzero, lap.runs.not_rerun) == (
        3,
        2,
        0,
    ), [(p.rule, p.message) for p in lap.problems]
    evidence_line = {s.n: s.fields[0].line for s in lap.statements if s.fields}
    warned = {p.line: p.message for p in lap.problems if p.severity == "WARN"}
    assert set(warned) == {evidence_line[1], evidence_line[2]}, warned
    assert all(
        m.startswith("UNCHECKED exit:") and "it exited 1" in m for m in warned.values()
    ), warned
    # The exact argv, quoting kept, so the echoed argument is visible as one.
    assert "sha256sum 'all 91 tests passed'" in warned[evidence_line[2]]
    assert all("states no exit code" in m for m in warned.values()), warned
    report, code = render(lap)
    assert code == 0
    assert (
        "B1: 3 run: result(s): 3 re-run and matched (2 of them exited non-zero "
        "with no exit code stated, which B1 does not compare: each an UNCHECKED "
        "exit: above), 0 re-run and not matched, 0 could not be re-run"
    ) in report


def _rerun_lap(tmp_path: Path, runs: list[str]) -> Lap:
    """`runs` as S1.. of an LSL 3 lap, each at the one commit of a repository of
    `_FAILING_TOOLS`, checked with --rerun."""
    repo, sha = _git_repo(tmp_path, _FAILING_TOOLS)
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(*[_measured(n, r, at=sha) for n, r in enumerate(runs, 1)])),
        encoding="utf-8",
    )
    return check_path(path, root=repo, rerun=True)


def test_a_stated_exit_code_that_the_rerun_reproduces_is_a_plain_match(
    tmp_path: Path,
) -> None:
    """Round 29's reading (the fork's lap 1 S28, accepted): a result that states
    `exit N` outside its quotes is held to it. A re-run that exits N is a plain
    match, with no UNCHECKED exit: warning, even when N is not 0: the lap said
    the command fails, and it does. Before, the first two were `UNCHECKED exit:`
    and counted as failed matches, because `exit N` was read as prose."""
    runs = [
        'python3 tools/fails.py => exit 1, "10 failed"',
        'python3 tools/fails.py => "10 failed", exit 1',
        'python3 tools/marked.py => "hello 42", exit 0',
    ]
    lap = _rerun_lap(tmp_path, runs)
    assert lap.problems == [], [(p.rule, p.message) for p in lap.problems]
    assert lap.runs is not None
    assert (
        lap.runs.total,
        lap.runs.matched,
        lap.runs.matched_nonzero,
        lap.runs.mismatched,
        lap.runs.not_rerun,
    ) == (3, 3, 0, 0, 0)
    report, code = render(lap)
    assert code == 0
    assert "exited non-zero" not in report, report


def test_a_stated_exit_code_the_rerun_does_not_reproduce_is_refused(
    tmp_path: Path,
) -> None:
    """Held to it both ways: a failure the lap called a success, and a success it
    called a failure. The refusal names both codes and quotes the output, as a
    missing quoted string's refusal does. Before, the first was matched with an
    UNCHECKED exit: warning and the second a plain match."""
    runs = [
        'python3 tools/fails.py => exit 0, "10 failed"',
        'python3 tools/marked.py => exit 3, "hello 42"',
        # Two codes stated: no single run can end with both, so B1 refuses it
        # rather than choosing one.
        'python3 tools/fails.py => exit 0 at first, then exit 1, "10 failed"',
    ]
    lap = _rerun_lap(tmp_path, runs)
    assert _rules(lap) == {"B1"}, [(p.rule, p.message) for p in lap.problems]
    assert lap.runs is not None
    assert (lap.runs.matched, lap.runs.mismatched, lap.runs.not_rerun) == (0, 3, 0)
    evidence_line = {s.n: s.fields[0].line for s in lap.statements if s.fields}
    refused = {p.line: p.message for p in lap.refused()}
    assert set(refused) == {evidence_line[n] for n in (1, 2, 3)}, refused
    assert [p for p in lap.problems if p.severity == "WARN"] == [], lap.problems
    first = refused[evidence_line[1]]
    assert "its result states exit 0, but it exited 1" in first, first
    assert "'round 27: 12 lap(s), 10 failed\\n'" in first, first
    second = refused[evidence_line[2]]
    assert "its result states exit 3, but it exited 0" in second, second
    assert "'hello 42\\n'" in second, second
    third = refused[evidence_line[3]]
    assert "states exit 0 and exit 1, and no run ends with two codes" in third, third


def test_a_result_that_states_only_an_exit_code_is_still_prose(
    tmp_path: Path,
) -> None:
    """Unchanged by round 29: a result that quotes nothing is prose and is not
    re-run (the proposal, "What B1 re-runs", item 4), whatever it states. S28
    adds a rule for the exit code of a result B1 compares, and does not amend
    item 4. So a false `=> exit 0` is reported, not refused."""
    lap = _rerun_lap(tmp_path, ["python3 tools/fails.py => exit 0"])
    assert lap.refused() == [], [(p.rule, p.message) for p in lap.problems]
    assert lap.runs is not None
    assert (lap.runs.matched, lap.runs.mismatched, lap.runs.not_rerun) == (0, 0, 1)
    [warning] = lap.problems
    assert "its result quotes nothing, so it is prose" in warning.message


def test_an_exit_inside_the_quotes_is_output_not_a_stated_code(
    tmp_path: Path,
) -> None:
    """`"exit 0"` quotes what the command printed; it states nothing about how it
    ended. So this failing tool, which prints `exit 0`, is the no-code-stated
    case: matched, and warned about as UNCHECKED exit:, exactly as before."""
    lap = _rerun_lap(tmp_path, ['python3 tools/says_exit.py => "exit 0"'])
    assert lap.refused() == [], [(p.rule, p.message) for p in lap.problems]
    assert lap.runs is not None
    assert (lap.runs.matched, lap.runs.matched_nonzero) == (1, 1)
    [warning] = lap.problems
    assert warning.message.startswith("UNCHECKED exit:"), warning.message
    assert "it exited 1" in warning.message


def test_the_exit_codes_a_result_states_outside_its_quotes() -> None:
    assert stated_exits('"IN SYNC", exit 0') == [0]
    assert stated_exits('exit 1, "refused"') == [1]
    assert stated_exits("**exit 0**, and `exit 0` again") == [0]
    assert stated_exits("exit 0 … exit 2") == [0, 2]
    assert stated_exits('"a" exit\t2 "b"') == [2]
    # Inside its quotes, the words are output, not a stated code.
    assert stated_exits('"exit 0"') == []
    assert stated_exits('"IN SYNC, exit 0"') == []
    # A quotation is replaced by a space, so its two sides cannot join into one.
    assert stated_exits('ex"x"it 0') == []
    # Literal, as the fork's S28 writes it: these are prose, not `exit N`.
    for prose in ("exited 1", "pre-exit 1", "exit code 1", "Exit 1", "exit 0x1"):
        assert stated_exits(prose) == [], prose
    # A code no process can exit with is still a stated code, held and refused.
    assert stated_exits("exit 1234") == [1234]
    assert stated_exits("exit 1234567890") == [], "ten digits: past the bound"
    assert stated_exits("no exit stated") == []


def test_rerun_runs_at_the_commit_named_not_at_the_clones_tip(tmp_path: Path) -> None:
    """The commit is the statement's at:, else the header's; never the clone's tip."""
    repo, first = _git_repo(tmp_path, {"v.txt": "one\n"})
    (repo / "v.txt").write_text("two\n", encoding="utf-8")
    _commit(repo, "second")
    tip = _in(repo, "rev-parse", "--short=12", "HEAD").strip()
    path = tmp_path / "lap.md"
    # The header names the first commit. S1's at: names the tip and wins over the
    # header; S2 has no at: and runs at the header's commit, not at the tip.
    body = _numbered(
        _measured(1, 'git show HEAD:v.txt => "two"', at=tip),
        _measured(2, 'git show HEAD:v.txt => "one"'),
    )
    path.write_text(
        _lsl3(body, extra_header=f"HANDSHAKE-FROM-COMMIT: {first}\n"), encoding="utf-8"
    )
    lap = check_path(path, root=repo, rerun=True)
    assert lap.runs is not None and lap.runs.matched == 2, [
        (p.rule, p.message) for p in lap.problems
    ]
    assert lap.problems == []
    # And the non-triviality: at the other commit, the same claim does not hold.
    path.write_text(
        _lsl3(_numbered(_measured(1, 'git show HEAD:v.txt => "one"', at=tip))),
        encoding="utf-8",
    )
    assert _rules(check_path(path, root=repo, rerun=True)) == {"B1"}


def test_rerun_that_runs_too_long_is_killed_and_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, sha = _git_repo(
        tmp_path,
        {
            "slow.py": "# LSL-RERUN: commit-only\nimport time\ntime.sleep(60)\nprint('late')\n"
        },
    )
    monkeypatch.setattr(scratch, "RERUN_TIMEOUT_S", 0.5)
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(_measured(1, 'python3 slow.py => "late"', at=sha))),
        encoding="utf-8",
    )
    lap = check_path(path, root=repo, rerun=True)
    assert lap.refused() == [], "a run that could not finish is unchecked, not refused"
    assert lap.runs is not None and lap.runs.not_rerun == 1
    assert any("was killed" in p.message for p in lap.problems)
    assert len(_worktrees(repo)) == 1, "the scratch checkout was left behind"


def test_a_header_naming_a_tag_is_unchecked_and_checks_nothing_out(
    tmp_path: Path,
) -> None:
    """Review finding R16's route in: an annotated tag's sha has the shape of a
    commit, and `git worktree add` peeled it to the commit it tags, whose HEAD
    then failed the check, and that worktree was never removed. The tag is now
    refused as a commit before anything is checked out."""
    repo, _ = _git_repo(tmp_path, {"data.txt": "alpha\n"})
    _in(
        repo,
        "-c",
        "user.name=lap test",
        "-c",
        "user.email=lap-test@example.invalid",
        "tag",
        "-a",
        "-m",
        "a tag",
        "v1",
    )
    tag = _in(repo, "rev-parse", "v1").strip()[:12]
    assert _in(repo, "cat-file", "-t", tag).strip() == "tag"
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(
            _numbered(_measured(1, 'git show HEAD:data.txt => "alpha"')),
            extra_header=f"HANDSHAKE-FROM-COMMIT: {tag}\n",
        ),
        encoding="utf-8",
    )
    before = _worktrees(repo)
    lap = check_path(path, root=repo, rerun=True)
    assert lap.refused() == []
    assert lap.runs is not None and lap.runs.not_rerun == 1
    [warning] = [p for p in lap.problems if p.rule == "LSL.unchecked"]
    assert f"{tag} is a tag object, not a commit" in warning.message
    assert _worktrees(repo) == before
    assert lap.runs.leftovers == []


def test_a_checkout_that_fails_its_check_is_still_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding R16: `worktree add` succeeded, the follow-up check that
    HEAD is the commit failed (here, git does not answer it, as on a timeout),
    and `_add` returned only the reason, so `close` never removed the worktree
    the clone still listed."""
    repo, sha = _git_repo(tmp_path, {"data.txt": "alpha\n"})
    real_git = scratch._git

    def head_unanswered(
        root: Path, *args: str, timeout: float = scratch.GIT_TIMEOUT_S
    ) -> subprocess.CompletedProcess[str] | None:
        if args == ("rev-parse", "HEAD") and root != repo:
            return None
        return real_git(root, *args, timeout=timeout)

    monkeypatch.setattr(scratch, "_git", head_unanswered)
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(_measured(1, 'git show HEAD:data.txt => "alpha"', at=sha))),
        encoding="utf-8",
    )
    before = _worktrees(repo)
    lap = check_path(path, root=repo, rerun=True)
    assert any("is not at" in p.message for p in lap.problems), lap.problems
    assert lap.runs is not None and lap.runs.not_rerun == 1
    assert _worktrees(repo) == before, "the checkout that failed its check was left"
    assert lap.runs.leftovers == []


def test_a_leftover_is_named_as_what_it_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding R16's message: when a checkout would not go, the report
    told a person to `git worktree remove` the scratch DIRECTORY, which is not
    one. It now names the checkout, and names the directory as a directory."""
    repo, sha = _git_repo(tmp_path, {"data.txt": "alpha\n"})
    real_git = scratch._git

    def remove_refused(
        root: Path, *args: str, timeout: float = scratch.GIT_TIMEOUT_S
    ) -> subprocess.CompletedProcess[str] | None:
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(list(args), 1, "", "refused")
        return real_git(root, *args, timeout=timeout)

    monkeypatch.setattr(scratch, "_git", remove_refused)
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(_measured(1, 'git show HEAD:data.txt => "alpha"', at=sha))),
        encoding="utf-8",
    )
    before = _worktrees(repo)
    lap = check_path(path, root=repo, rerun=True)
    assert lap.runs is not None
    left = lap.runs.leftovers
    try:
        assert lap.runs.matched == 1, lap.problems
        [checkout] = [x for x in left if x.checkout]
        [directory] = [x for x in left if not x.checkout]
        assert Path(checkout.path).parent == Path(directory.path)
        assert f"worktree {checkout.path}" in _worktrees(repo)
        report = render(lap)[0]
        # `--force` twice, the command `close` tries (Q8): git refuses one
        # `--force` for a worktree still locked by a `worktree add`.
        assert f"`git worktree remove --force --force {checkout.path}`" in report
        [directory_line] = [ln for ln in report.splitlines() if "directory" in ln]
        assert f"scratch directory {directory.path}, which is not a checkout" in (
            directory_line
        )
        assert "git worktree remove" not in directory_line
    finally:
        for item in left:
            if item.checkout:
                _in(repo, "worktree", "remove", "--force", item.path)
        for item in left:
            if not item.checkout:
                Path(item.path).rmdir()
    assert _worktrees(repo) == before


def _lock_as_initializing(tree: Path) -> Path:
    """Lock `tree` as an interrupted `git worktree add` leaves it; its admin dir.

    git writes `locked`, reading "initializing", into the new worktree's admin
    directory before it checks anything out, and deletes it last. `_git`'s
    timeout SIGKILLs git, which cannot catch that, so a timed-out add leaves the
    lock on (review finding Q8, reproduced with a real kill by the reviewer).
    """
    admin = Path(_in(tree, "rev-parse", "--absolute-git-dir").strip())
    (admin / "locked").write_text("initializing\n", encoding="utf-8")
    return admin


def _remove_locked(repo: Path, trees: list[Path]) -> None:
    """Clean-up for the two tests below, whatever they got to: never `rm`."""
    listed = _worktrees(repo)
    for tree in trees:
        if f"worktree {tree}" in listed:
            _in(repo, "worktree", "remove", "--force", "--force", str(tree))
        if tree.parent.is_dir() and not any(tree.parent.iterdir()):
            tree.parent.rmdir()


def test_close_removes_a_checkout_left_locked_by_a_timed_out_add(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding Q8: `worktree add` timed out, so git was killed before it
    unlocked the new worktree, and `_add` recorded the checkout for `close`
    (R16). git refuses a single-`--force` remove of a locked worktree, so `close`
    reported it as left behind. Here the add is done as git leaves it: made,
    still locked "initializing", and no answer, as `_git` gives on a timeout."""
    repo, sha = _git_repo(tmp_path, {"data.txt": "alpha\n"})
    real_git = scratch._git
    admins: list[Path] = []

    def add_times_out(
        root: Path, *args: str, timeout: float = scratch.GIT_TIMEOUT_S
    ) -> subprocess.CompletedProcess[str] | None:
        answer = real_git(root, *args, timeout=timeout)
        if args[2:4] == ("worktree", "add"):
            assert answer is not None and answer.returncode == 0, answer
            admins.append(_lock_as_initializing(Path(args[-2])))
            return None
        return answer

    monkeypatch.setattr(scratch, "_git", add_times_out)
    before = _worktrees(repo)
    made = scratch.Scratch(repo)
    assert made.tree(sha) == f"git did not answer when asked to check out {sha}"
    [admin] = admins
    trees = list(made._made)
    try:
        [tree] = trees
        # NON-TRIVIALITY: the checkout is there, git lists it as locked
        # "initializing", and git refuses the single `--force` close used to try.
        listed = _in(repo, "worktree", "list", "--porcelain")
        assert f"worktree {tree}" in listed and "locked initializing" in listed
        single = subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(tree)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert single.returncode != 0 and "locked" in single.stderr, single
        monkeypatch.setattr(scratch, "_git", real_git)
        assert made.close() == []
        assert not tree.exists() and not admin.exists()
    finally:
        monkeypatch.setattr(scratch, "_git", real_git)
        _remove_locked(repo, trees)
    assert _worktrees(repo) == before


def test_the_advice_for_a_leftover_checkout_is_a_command_git_takes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q8's other half: the report told a person to run `git worktree remove
    --force <path>`, which git refuses for a locked worktree, the likeliest
    leftover. Here `close`'s own remove gets no answer (a remove that timed
    out), and the command the report prints is run as a person would run it,
    in the author's clone, against a checkout still locked "initializing"."""
    repo, sha = _git_repo(tmp_path, {"data.txt": "alpha\n"})
    before = _worktrees(repo)
    made = scratch.Scratch(repo)
    tree = made.tree(sha)
    assert isinstance(tree, Path), tree
    trees = [tree]
    real_git = scratch._git

    def remove_unanswered(
        root: Path, *args: str, timeout: float = scratch.GIT_TIMEOUT_S
    ) -> subprocess.CompletedProcess[str] | None:
        if args[:2] == ("worktree", "remove"):
            return None
        return real_git(root, *args, timeout=timeout)

    try:
        _lock_as_initializing(tree)
        monkeypatch.setattr(scratch, "_git", remove_unanswered)
        left = made.close()
        monkeypatch.setattr(scratch, "_git", real_git)
        assert [x.path for x in left if x.checkout] == [str(tree)], left
        runs = RunCoverage(leftovers=left)
        [line] = [ln for ln in render_runs(runs) if "scratch checkout" in ln]
        [command] = re.findall(r"`([^`]+)`", line)
        ran = subprocess.run(
            shlex.split(command),
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert ran.returncode == 0, (command, ran.stderr)
        assert f"worktree {tree}" not in _worktrees(repo)
    finally:
        monkeypatch.setattr(scratch, "_git", real_git)
        _remove_locked(repo, trees)
    assert _worktrees(repo) == before


def _running(pid: int) -> bool:
    """Whether `pid` is a live process: present, and neither a zombie nor dead."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return False
    return stat.rsplit(")", 1)[-1].split()[0] not in ("Z", "X")


def test_an_interrupted_rerun_kills_its_group_before_the_checkout_goes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding R14. Ctrl-C while a re-run was in `child.wait()` left the
    child running: it leads its own session, so the terminal's SIGINT never
    reached it, and only a timeout killed the group. It then ran on, unbounded,
    while `close` force-removed the checkout it was running in. Now the group is
    killed and reaped before the interrupt goes on, and before the checkout goes.

    The interrupt is raised from inside the wait, once the child has started a
    grandchild in its group, so the group kill (not just the child's) is what
    the grandchild's death proves.
    """
    pidfile = tmp_path / "grandchild.pid"
    repo, sha = _git_repo(
        tmp_path,
        {
            "tools/group.py": "# LSL-RERUN: commit-only\n"
            "import os, subprocess, sys, time\n"
            "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "open(os.environ['LSL_TEST_PIDFILE'], 'w').write(str(g.pid))\n"
            "time.sleep(60)\nprint('done')\n"
        },
    )
    monkeypatch.setenv("LSL_TEST_PIDFILE", str(pidfile))
    real_popen = subprocess.Popen
    reruns: list[subprocess.Popen[bytes]] = []

    class InterruptedWait(subprocess.Popen[bytes]):  # the real one, patched below
        def wait(self, timeout: float | None = None) -> int:
            # Only the lap's command, only its first wait: the checker's own git
            # calls, and the reap `_kill` does, pass straight through.
            if not reruns and self.args[0] != "git":
                reruns.append(self)
                deadline = time.monotonic() + 30
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                raise KeyboardInterrupt
            return int(super().wait(timeout))

    at_close: list[int | None] = []
    real_close = scratch.Scratch.close

    def close_spy(self: scratch.Scratch) -> list[str]:
        at_close.append(reruns[0].poll() if reruns else -1000)
        return real_close(self)

    monkeypatch.setattr(scratch.subprocess, "Popen", InterruptedWait)
    monkeypatch.setattr(scratch.Scratch, "close", close_spy)
    path = tmp_path / "lap.md"
    path.write_text(
        _lsl3(_numbered(_measured(1, 'python3 tools/group.py => "done"', at=sha))),
        encoding="utf-8",
    )
    before = _worktrees(repo)
    try:
        with pytest.raises(KeyboardInterrupt):
            check_path(path, root=repo, rerun=True)
        assert pidfile.exists(), "the re-run never started its grandchild"
        grandchild = int(pidfile.read_text(encoding="utf-8"))
        [child] = reruns
        # Killed with its group and reaped BEFORE the checkout was removed.
        assert at_close == [-signal.SIGKILL], at_close
        assert child.returncode == -signal.SIGKILL
        deadline = time.monotonic() + 5
        while _running(grandchild) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not _running(grandchild), "the group kill missed the grandchild"
        assert _worktrees(repo) == before, "the scratch checkout was left behind"
    finally:
        # With the fix reverted the group is still alive: never leak it.
        for child in reruns:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            real_popen.wait(child, timeout=5)


def test_a_rerun_reads_no_stdin_and_survives_output_that_is_not_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its output must depend on the commit alone, so the re-run gets no stdin:
    `wc -l` with no file reads stdin, and the checker's own stdin is not the
    author's. And a tool's bytes are external input, so bytes that are not
    UTF-8 are replaced, never raised on (a raise would exit 1, which reads as
    "refused"; the fork's checker at 889a375 does that, their tools/
    lap-statements.py:883-887)."""
    repo, sha = _git_repo(
        tmp_path,
        {
            "bin.py": "# LSL-RERUN: commit-only\nimport sys\n"
            "sys.stdout.buffer.write(b'ok \\xff\\xfe bytes\\n')\n"
        },
    )
    spawned: list[dict[str, object]] = []
    real_popen = subprocess.Popen

    def spy(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
        # Every git call of the checker's own goes through Popen too; record
        # only the re-runs, the commands the lap named.
        argv = args[0] if args else kwargs.get("args")
        if isinstance(argv, list) and argv and argv[0] != "git":
            spawned.append(kwargs)
        return real_popen(*args, **kwargs)  # type: ignore[call-overload, no-any-return]  # a pass-through spy

    monkeypatch.setattr(scratch.subprocess, "Popen", spy)
    path = tmp_path / "lap.md"
    body = _numbered(
        _measured(1, 'python3 bin.py => "ok … bytes"', at=sha),
        _measured(2, 'wc -l => "0"', at=sha),
    )
    path.write_text(_lsl3(body), encoding="utf-8")
    lap = check_path(path, root=repo, rerun=True)
    assert lap.problems == [], [(p.rule, p.message) for p in lap.problems]
    assert lap.runs is not None and lap.runs.matched == 2
    assert len(spawned) == 2
    assert all(k.get("stdin") == subprocess.DEVNULL for k in spawned), spawned
    assert all(k.get("start_new_session") is True for k in spawned), spawned


def test_rerun_without_the_authors_clone_is_unchecked(tmp_path: Path) -> None:
    """A fork lap checked with no --peer: nothing to check out, so nothing refused."""
    text = _lsl3(
        _numbered(_measured(1, 'git show HEAD:README => "x"', at="da766ca")),
    ).replace("HANDSHAKE-FROM: platterpus", "HANDSHAKE-FROM: cyanrip-fork")
    path = tmp_path / "lap.md"
    path.write_text(text, encoding="utf-8")
    lap = check_path(path, rerun=True)
    assert lap.refused() == []
    assert lap.runs is not None and lap.runs.not_rerun == 1
    assert any("no clone of the author's tree" in p.message for p in lap.problems)


# The pure half of B1: planning a re-run, and comparing.


def test_a_command_is_planned_only_from_the_three_kinds() -> None:
    names = frozenset({"main", "origin/main"})
    planned = plan_command("git log --oneline -1 abc1234", names)
    assert not isinstance(planned, str) and planned.tree_file is None
    assert not isinstance(plan_command("wc -l a.txt", names), str)
    tool = plan_command("python3 ./tools/x.py 28", names)
    assert not isinstance(tool, str) and tool.tree_file == "tools/x.py"
    for command, why in (
        ("git status", "read-only query"),
        ("git -C x log", "read-only query"),
        ("git diff --output=x", "--output"),
        ("git show ../x", "climbs out"),
        ("git show HEAD:../x", "climbs out"),
        ("git log origin/main~2", "names the ref"),
        ("git log main..abc1234", "names the ref"),
        ("git log --format=%ar", "reads the clock"),
        ("git rev-parse --show-toplevel", "prints where the checkout is"),
        ("git log --all", "reads the clone's refs"),
        ("make check", "is not git"),
        ("python3 -m pytest", "python3 PATH"),
        ("wc -l x #comment", "comment"),
        ("wc -l 'unclosed", "does not split"),
        ("wc -l ~/x", "absolute path"),
        ("", "names no command"),
    ):
        reason = plan_command(command, names)
        assert isinstance(reason, str) and why in reason, (command, reason)
    for ch in "|;&<>$()*?[]{}\\`\n…":
        reason = plan_command(f"wc -l a{ch}b", names)
        assert isinstance(reason, str) and "needs a shell" in reason, repr(ch)


def test_quoted_strings_and_their_ordered_parts() -> None:
    assert quoted_parts('exit 0, "a…b" and "c"') == [["a", "b"], ["c"]]
    assert quoted_parts('"" and "…"') == [], "an empty quotation compares nothing"
    assert quoted_parts("no quotes here") == []
    # The spaces around an ellipsis are the elision's; the outer ones are quoted.
    assert quoted_parts('"Ok 91 … Fail 0"') == [["Ok 91", "Fail 0"]]
    assert quoted_parts('" 3 data.txt"') == [[" 3 data.txt"]]
    assert appears(["a", "b"], "xaxbx")
    assert not appears(["b", "a"], "xaxbx")
    assert split_run("run: git log => x => y").result == "x => y"
    assert split_run("run: git log").result is None


def test_only_the_tools_we_reviewed_declare_the_rerun_marker() -> None:
    """Each side marks its own tools, and a tool that reads the network, a drive,
    the clock or a moving ref must not carry the marker. This is the list of ours
    that do, each reviewed; a new one joins it only after the same review.

    `scripts/round_digest.py` reads only `docs/handshake/{inbound,outbound}` under
    the checkout it runs from (its `_REPO_ROOT` is its own file's grandparent) and
    hashes those bytes; it asks git nothing and reads no clock. `lap_language.py`
    must never carry it: it reads `origin/main`, a moving ref.
    """
    marked: set[str] = set()
    examined = 0
    for path in sorted(REPO_ROOT.glob("scripts/**/*.py")) + sorted(
        REPO_ROOT.glob("scripts/**/*.sh")
    ):
        examined += 1
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]
        if any(MARKER_RE.match(line) for line in head):
            marked.add(path.relative_to(REPO_ROOT).as_posix())
    assert examined >= 20, f"examined only {examined} scripts; the sweep is wrong"
    assert marked == {"scripts/round_digest.py"}


def test_a_line_that_mentions_the_marker_does_not_declare_it() -> None:
    assert MARKER_RE.match("# LSL-RERUN: commit-only")
    assert MARKER_RE.match("LSL-RERUN: commit-only")
    assert MARKER_RE.match('"""LSL-RERUN: commit-only')
    assert not MARKER_RE.match("Says `LSL-RERUN: commit-only` in prose.")
    assert not MARKER_RE.match("# A tool marked LSL-RERUN: commit-only is re-run.")
    assert not MARKER_RE.match("# LSL-RERUN: commit-onlyish")


# B3, and the relation to A6 that defines it.


def test_b3_an_answer_that_carries_no_weight_answers_nothing_for_a7(
    tmp_path: Path,
) -> None:
    """The fork's case (their round 28 lap 3 S20): a GO whose only answer to the
    other side's blocking question is a NOTE. LSL 2 counts it; LSL 3 does not."""
    root = tmp_path / "tree"
    ours = root / LAP_DIRS["platterpus"] / "round-28-lap-01.md"
    ours.parent.mkdir(parents=True)
    ours.write_text(
        _header(lap=1, verdict="OPEN")
        + "LSL: 1\n\n"
        + PLAIN_FACT
        + "S2 ASK: Does the pin misread track 3?\n  target: BLOCKING\n"
        "  breaks: every rip of track 3\n"
        "S3 VERDICT: OPEN\n  basis: S1\n",
        encoding="utf-8",
    )
    earlier = root / LAP_DIRS["cyanrip"] / "round-28-lap-02.md"
    earlier.parent.mkdir(parents=True)
    earlier.write_text(
        _header(author="cyanrip-fork", lap=2, verdict="OPEN")
        + "LSL: 2\n\n"
        + GOOD_FACT
        + "S2 NOTE: It does not.\n  answers: platterpus:R28.L1.S2\n"
        "S3 TERM set: The Full run passes.\n  requires: a Full run\n"
        "  regression: none\n"
        "S4 VERDICT: OPEN\n  basis: S1\n",
        encoding="utf-8",
    )

    def go(version: int) -> str:
        # `at:` is LSL 3's field (B1), so only the LSL 3 lap carries it.
        at = "  at: 1234567\n" if version == 3 else ""
        return (
            _header(author="cyanrip-fork", lap=3)
            + f"LSL: {version}\n\n"
            + GOOD_FACT
            + at
            + "S2 TERM met: The Full run passed.\n  term: cyanrip:R28.L2.S3\n"
            "  evidence: run: true => ok\n" + at + "S3 VERDICT: GO\n  basis: S1\n"
        )

    as_lsl_2 = _check(tmp_path, go(2), root=root)
    assert as_lsl_2.refused() == [], [p.message for p in as_lsl_2.refused()]
    assert as_lsl_2.go_checked_against == {"A1": 1, "A7": 1}
    as_lsl_3 = _check(tmp_path, go(3), root=root)
    assert _rules(as_lsl_3) == {"A7"}, [(p.rule, p.message) for p in as_lsl_3.problems]
    assert as_lsl_3.go_checked_against == {"A1": 1, "A7": 1}


_WEIGHTS: dict[str, str] = {
    "NOTE": "S2 NOTE: A remark.\n",
    "ASK": "S2 ASK: A question?\n  target: NEXT-ROUND\n",
    "WILL": "S2 WILL: Do it.\n  owner: us\n  when: the round closes\n",
    "UNKNOWN": "S2 UNKNOWN: Not known.\n  reason: no clone\n",
    "FACT relayed": "S2 FACT relayed: Heard it.\n  source: the operator\n",
    "FACT measured": _measured(2, "true => ok", at="da766ca"),
    "DID": "S2 DID: Merged it.\n  commit: da766ca\n",
    "ACCEPT": "S2 ACCEPT: Yes.\n  re: S1\n",
}


def _kind(label: str) -> tuple[str, str | None]:
    kind, _, grade = label.partition(" ")
    return kind, grade or None


@pytest.mark.parametrize("kind", sorted(_WEIGHTS))
def test_b3_refuses_an_answers_exactly_where_a6_refuses_weight(
    tmp_path: Path, kind: str
) -> None:
    """One predicate, two rules: B3's list is "the statements A6 lets carry no
    weight", so the RELATION is tested, not either list alone."""
    text = _lsl3(
        _measured(1, "true => ok", at="da766ca")
        + _WEIGHTS[kind]
        + "  answers: cyanrip:R28.L1.S30\n"
        + "S3 REFUSE: Not that.\n  re: S1\n  because: S2\n"
        + "".join(f"S{n} NOTE: Nothing.\n" for n in range(4, 9))
    )
    lap = _check(tmp_path, text)
    rules = _rules(lap)
    assert rules <= {"A6", "B3"}, [(p.rule, p.message) for p in lap.problems]
    assert ("B3" in rules) == ("A6" in rules) == carries_no_weight(*_kind(kind))


def test_the_weight_relation_is_not_trivial() -> None:
    weightless = [k for k in _WEIGHTS if carries_no_weight(*_kind(k))]
    assert len(weightless) >= 5 and len(_WEIGHTS) - len(weightless) >= 3


# Never raising, on LSL 3's new inputs.


@settings(max_examples=300, deadline=None)
@given(st.text(), st.frozensets(st.text(max_size=8), max_size=4))
def test_planning_and_matching_arbitrary_text_never_raises(
    text: str, names: frozenset[str]
) -> None:
    plan_command(text, names)
    claim = split_run("run: " + text)
    for parts in quoted_parts(claim.result or text):
        appears(parts, text)
    assert all(0 <= code <= 999_999_999 for code in stated_exits(text))


@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(st.text(max_size=400))
def test_checking_an_arbitrary_lsl_3_body_never_raises(
    tmp_path: Path, body: str
) -> None:
    def instant_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(args), 0, "line\n" * 50, "")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(refs, "_git", instant_git)
        _check(tmp_path, _header() + "LSL: 3\n\n" + GOOD_FACT + body + _BODY_END)
