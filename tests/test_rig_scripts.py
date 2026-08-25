"""The committed rig scripts are checked by the real language, not by eye.

**Why this file exists.** `docs/rig-scripts/*.txt` are the tests this project
actually runs on hardware — `CLAUDE.md`'s *a new testing capability is a SCRIPT
VERB* means the script language is where the acceptance suite is written. They
are committed artifacts, they cross machines by hand, and until now **nothing
parsed them**. So a step naming a setting that does not exist looked identical to
one that works, right up until an unattended two-hour run recorded an ERROR for
it — and then the run's own summary line reported `error=3` without saying which
three, so the defect survived being measured.

Found the way it always is: `docs/rig-scripts/fullacceptance.txt` carried

    set paranoia_passes 3
    expect paranoia_passes 3

and `paranoia_passes` has never been a field of :class:`~platterpus.config.Config`
in this repository's history. Both steps errored on every run of that script.
They are two of the three errors in the 2026-08-23 full acceptance pass.

**A comment where a check belongs is not a fix** (`CLAUDE.md`), so the fix is this
sweep rather than the corrected line. The population is DERIVED from the
directory, not listed here: a typed list is the hand-maintained field that rots,
inside a test written about an artifact that rotted.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from platterpus.config import Config
from platterpus.uiscript import script as uiscript
from platterpus.uiscript import verbs

RIG_SCRIPTS: Path = Path(__file__).resolve().parents[1] / "docs" / "rig-scripts"

#: Verbs that only make sense as a `set`/`expect` subject if the name is a real
#: config field. Kept as a tuple rather than inlined so a new settings verb has
#: one place to join.
SETTING_VERBS: tuple[str, ...] = ("set", "expect", "expect-contains")


def _scripts() -> list[Path]:
    return sorted(RIG_SCRIPTS.glob("*.txt"))


def test_there_are_scripts_to_check() -> None:
    """The floor. Every test below iterates a glob, and a glob that matches
    nothing passes each of them silently — `CLAUDE.md`'s *can this check be
    satisfied by finding nothing?* applied to the population rather than to a
    single assertion."""
    found = _scripts()
    assert len(found) >= 3, f"only {len(found)} rig script(s) under {RIG_SCRIPTS}"


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: p.name)
def test_every_step_names_a_verb_that_exists_and_is_built(path: Path) -> None:
    """A verb with no handler is an ERROR at dispatch, hours into an unattended run.

    Both halves matter and they fail differently: an unknown verb is a typo, a
    known-but-unbuilt verb is a capability the generated reference advertises and
    the runner cannot serve. `expect-status` was the second kind and cost step 179
    of 288 on the 2026-08-23 run.
    """
    known = {v.name for v in verbs._VERB_LIST}
    built = {v.name for v in verbs._VERB_LIST if v.implemented}
    steps = uiscript.parse(path.read_text(encoding="utf-8"))
    assert steps, f"{path.name} parsed to no steps at all"
    problems = [
        f"line {step.line_no}: {step.verb!r} "
        + ("is not a verb" if step.verb not in known else "has no handler")
        for step in steps
        if step.verb not in built
    ]
    assert not problems, f"{path.name}\n" + "\n".join(problems)


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: p.name)
def test_every_setting_named_is_a_real_config_field(path: Path) -> None:
    """**The regression test for the defect that prompted this file.**

    `set`/`expect` take a *config.toml field name*, and the runner reports
    ``no setting called 'x'`` at run time — which is the right behaviour and the
    wrong moment. Checked here against the real dataclass, so the same mistake
    fails in CI in milliseconds instead of on a rig two hours in.
    """
    fields = {f.name for f in dataclasses.fields(Config())}
    assert fields, "Config has no fields — this check is measuring nothing"
    steps = uiscript.parse(path.read_text(encoding="utf-8"))
    problems = [
        f"line {step.line_no}: {step.verb} {step.args[0]!r} is not a Config field"
        for step in steps
        if step.verb in SETTING_VERBS and step.args and step.args[0] not in fields
    ]
    assert not problems, f"{path.name}\n" + "\n".join(problems)


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: p.name)
def test_every_scripted_cyanrip_invocation_survives_the_sanitiser(path: Path) -> None:
    """A committed script must not carry a step the argv guard will refuse.

    `sanitise_cyanrip_args` re-establishes the `-N` chokepoint for the one route
    to the ripper that bypasses it. A refused step is not a safety failure — the
    guard did its job — but it *is* a step that will never run, recorded in a file
    somebody will run unattended. Delegating to the real function rather than
    restating its rule is the point: a second copy of a safety check is a second
    thing to drift.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []
    for step in uiscript.parse(path.read_text(encoding="utf-8")):
        if step.verb != "cyanrip":
            continue
        refusal = uiscript.sanitise_cyanrip_args(list(step.args))
        marked = _refusal_is_declared(lines, step.line_no)
        argv = f"cyanrip {' '.join(step.args)}"
        if refusal is not None and not marked:
            problems.append(f"line {step.line_no}: {argv} -> {refusal}")
        # THE OTHER DIRECTION, and it is the half that rots. A marker left over a
        # step the guard now admits would read as "this is refused on purpose"
        # about an argv that runs — so the marker must be as falsifiable as the
        # refusal it documents.
        if refusal is None and marked:
            problems.append(
                f"line {step.line_no}: {argv} carries EXPECT-SANITISER-REFUSAL "
                f"but the sanitiser now allows it — remove the marker or the "
                f"comment is describing a guard that no longer fires"
            )
    assert not problems, f"{path.name}\n" + "\n".join(problems)


#: How far above a step the marker may sit. A window rather than "the line
#: directly above" because these scripts are heavily commented and the reason
#: belongs in prose with the step, not crammed onto one line.
_MARKER_WINDOW: int = 14
_MARKER: str = "EXPECT-SANITISER-REFUSAL:"


def _refusal_is_declared(lines: list[str], line_no: int) -> bool:
    """Does a comment shortly above ``line_no`` declare the refusal deliberate?

    The declaration lives in the SCRIPT, not in an allowlist here, for the reason
    `CLAUDE.md` gives about names that cross machines: a list in a test file is a
    second description of a fact the artifact can state itself, and the two drift.
    It also travels — the fork runs these scripts too.
    """
    start = max(0, line_no - 1 - _MARKER_WINDOW)
    return any(_MARKER in line for line in lines[start : line_no - 1])


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: p.name)
def test_no_step_failed_to_parse(path: Path) -> None:
    """The parser records a per-step `error` instead of raising; read it.

    Without this the checks above skip a malformed line rather than failing on it,
    which is the quiet-truncation shape: a script with a broken step would pass
    every assertion in this file.
    """
    steps = uiscript.parse(path.read_text(encoding="utf-8"))
    broken = [f"line {s.line_no}: {s.source!r} -> {s.error}" for s in steps if s.error]
    assert not broken, f"{path.name}\n" + "\n".join(broken)


# --- The acceptance script and the pin under review are ONE key ---------------

ACCEPTANCE: Path = RIG_SCRIPTS / "fullacceptance.txt"

#: `expect-cyanrip platterpus-fork-g<sha>` — the build the acceptance run asserts
#: it is grading. Matched on the whole tail so a prefix cannot satisfy it.
_ASSERTED_BUILD = re.compile(
    r"^expect-cyanrip\s+platterpus-fork-g(?P<sha>[0-9a-f]{7,40})\s*$",
    re.MULTILINE,
)


def test_the_acceptance_script_hardcodes_no_cyanrip_build_tag() -> None:
    """**The regression test for a defect that recurred three times in two days.**

    Two surfaces answered *"which cyanrip build is this run about?"* with
    different keys: the script carried a literal `platterpus-fork-g796df32`, while
    the in-app install route resolves the fork's `release-manifest.json` `beta`
    channel. They then published `f2c0506` and `d9c058c` on that channel. Each
    time, an operator following our own instructions installed the build we sent
    them to and **failed section A in the first four seconds**, told they were on
    the wrong one.

    Changing the literal three times was not the fix. The fork named the shape in
    their round-14 lap 4 §C: *"a hardcoded build tag in a committed script is a
    second copy of a fact that lives in release-manifest.json. Two places holding
    one fact, and only one of them has a checker."*

    So the script now says `expect-ripper-under-review`, which reads
    `PIN_UNDER_REVIEW` — itself derived from the newest inbound handshake lap by
    `tests/test_handshake_pin_under_review.py`. One key, three surfaces. **This
    test asserts the ABSENCE of the second copy**, because a test that merely
    checked the literal was current would have passed on all three wrong days.
    """
    text = ACCEPTANCE.read_text(encoding="utf-8")
    steps = uiscript.parse(text)
    literals = [
        f"line {s.line_no}: {s.source.strip()}"
        for s in steps
        if s.verb == "expect-cyanrip"
        and s.args
        and re.fullmatch(r"platterpus-fork-g[0-9a-f]{7,40}", s.args[0] or "")
    ]
    assert not literals, (
        "fullacceptance.txt asserts a LITERAL cyanrip build tag:\n  "
        + "\n  ".join(literals)
        + "\nUse `expect-ripper-under-review`, which reads the constant the "
        "handshake record derives. A literal here is a second copy of a fact "
        "the fork publishes, and it went stale three times in two days."
    )
    assert any(s.verb == "expect-ripper-under-review" for s in steps), (
        "the acceptance script no longer asserts WHICH cyanrip build it is "
        "grading. That assertion is what stops a multi-hour pass running against "
        "the wrong ripper, which is the one mistake that invalidates the run."
    )


def test_the_under_review_verb_matches_the_build_the_record_names() -> None:
    """The verb's expectation is the record's, not a copy of it.

    Asserted through the same construction the handler uses, so a change to
    either the branch name or the constant fails here rather than producing an
    assertion that can never match any real banner.
    """
    from platterpus.deps import fork_source

    expected = f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}"
    assert re.fullmatch(r"platterpus-fork-g[0-9a-f]{7,40}", expected), expected


def test_the_pin_under_review_has_a_release_sequence() -> None:
    """A build the acceptance run installs must be placeable in the fork's order.

    Without a row, `release_seq_for_commit` returns `None` and the ripper offer
    tells an operator sitting on a **published release** that they are on *"a
    mid-round test pin, or a commit installed by hand"* — every clause of it wrong.
    That was reported by the maintainer on 2026-08-17, fixed by adding one row, and
    the fork quoted our own prediction back a day later when it recurred: *"it
    returns every time you publish and we do not."* This is the check that stops it
    returning a third time.
    """
    from platterpus.deps import fork_source

    seq = fork_source.release_seq_for_commit(fork_source.PIN_UNDER_REVIEW)
    assert seq is not None, (
        f"{fork_source.PIN_UNDER_REVIEW} is the pin under review — the build the "
        f"acceptance run installs — and it has no row in FORK_RELEASE_SEQ_BY_PIN, "
        f"so the ripper offer cannot place it in the fork's release order."
    )


def test_the_pin_under_review_is_resolved_in_the_consumer_flag_set() -> None:
    """**Regression for all nine rips of the 2026-08-24 run logging no consumer.**

    `--consumer` is gated on `BUILD_TAGS_ACCEPTING_CONSUMER_FLAG`, a hand-kept set
    of build tags. None of round 14's three betas were in it, so every rip logged
    `Consumer: not identified (no --consumer given)` — the tag that records which
    program drove the rip, missing throughout the round whose entire subject is
    provenance on a released pair.

    That is the third instance in two days of the same shape the fork named: *a
    second copy of a fact, and only one copy has a checker.* This is the checker.
    It does not assert the answer is "yes" — a build genuinely lacking the flag is
    a real state and must stay expressible. It asserts the question has been
    **asked** of the build we are about to install, so the next pin move cannot
    re-open the gap in silence.
    """
    from platterpus.deps import fork_source

    tag = f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}"
    known = {t.casefold() for t in fork_source.BUILD_TAGS_ACCEPTING_CONSUMER_FLAG}
    assert known, "the consumer-flag set is empty — this check measures nothing"
    assert tag.casefold() in known, (
        f"{tag} is the pin under review — the build the acceptance run installs — "
        f"and it is not in BUILD_TAGS_ACCEPTING_CONSUMER_FLAG, so every rip on it "
        f"will log 'Consumer: not identified (no --consumer given)'. Add it if the "
        f"fork's published flag table lists -u/--consumer for that build; if it "
        f"genuinely does not accept the flag, say so here in a comment and change "
        f"this test to expect that."
    )
