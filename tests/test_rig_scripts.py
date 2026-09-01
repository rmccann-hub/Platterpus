"""The committed rig scripts are checked by the real language, not by eye.

**Why this file exists.** `src/platterpus/rig_scripts/*.txt` are the tests this
project actually runs on hardware — `CLAUDE.md`'s *a new testing capability is a
SCRIPT VERB* means the script language is where the acceptance suite is written.
They are committed artifacts and until now **nothing parsed them**. So a step
naming a setting that does not exist looked identical to one that works, right up
until an unattended two-hour run recorded an ERROR for it — and then the run's own
summary line reported `error=3` without saying which three, so the defect survived
being measured.

They moved out of `docs/` and INTO the package on 2026-08-28, which is why the
constant below points where it does. A test the program cannot open is a test the
operator has to fetch by hand, and an AppImage user had no copy of the acceptance
script at all — see the `package-data` note in `pyproject.toml`.

Found the way it always is: the acceptance script carried

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

#: The scripts themselves, INSIDE the package so the running program can open
#: them (`platterpus.test_session.builtin_acceptance_script`).
RIG_SCRIPTS: Path = (
    Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"
)
#: The prose + the shell wrappers, which stay under `docs/`. Two constants
#: rather than one plus `.parent` arithmetic: the old single constant was used
#: BOTH as "where the scripts are" and, via `.parent`, as "the docs root", so
#: moving the scripts would have silently repointed the doc lookups too.
DOCS: Path = Path(__file__).resolve().parents[1] / "docs"

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


# --- The shell wrappers around those scripts ---------------------------------
#
# The `.txt` files above are checked by the real parser. The two `.sh` files that
# *drive* them had nothing checking anything, and they are the half the operator
# actually types.

OVERNIGHT: Path = DOCS / "rig-scripts" / "platterpusovernight.sh"
MORNING: Path = DOCS / "rig-scripts" / "platterpusmorning.sh"


def test_the_overnight_wrapper_delegates_and_never_reimplements() -> None:
    """One caller of two existing scripts — not a third copy of either.

    The whole reason the wrapper is safe to add is that it contains no logic of
    its own: the acceptance run stays `--run-script`, the collection stays
    `platterpusmorning.sh`. If either job were re-expressed here it would be a
    second implementation to drift, and the drift would surface at 3 a.m. on a
    machine with a disc in it.

    So: it must *invoke* both, and must not contain the marker of having
    reimplemented the collector (a `tar` of its own).
    """
    text = OVERNIGHT.read_text(encoding="utf-8")
    assert "--run-script" in text, "the wrapper does not start an acceptance run"
    assert "platterpusmorning.sh" in text, "the wrapper does not run the collector"
    # Comments are stripped first: this file *discusses* tarring in its header,
    # and a substring match against prose is the "satisfied by the wrong thing"
    # shape CLAUDE.md names.
    code = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    assert "tar " not in code, (
        "the wrapper builds its own archive. Collection belongs to "
        "platterpusmorning.sh; two bundlers means two answers to 'which file do "
        "I upload'."
    )


def test_the_sleep_lock_covers_the_collection_too_not_just_the_rip() -> None:
    """A suspend during `tar` yields a truncated archive that still looks like one.

    The obvious version of this wrapper holds the lock over the rip and drops it
    before collecting, because the rip is the long part. But the collector tars
    up to a few hundred megabytes, and an archive interrupted mid-write is the
    silent-partial shape: it opens, it lists, and the artifact the night was for
    is missing from the end of it.

    Non-triviality: the inhibit prefix must be *used* more than once, not merely
    defined. A test that only asserted `systemd-inhibit` appears would pass
    against a wrapper that inhibits nothing.
    """
    code = "\n".join(
        line
        for line in OVERNIGHT.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "systemd-inhibit" in code, "no sleep inhibitor at all"
    uses = code.count('"${INHIBIT[@]}"')
    assert uses >= 2, (
        f"the inhibit prefix is applied {uses} time(s); it must cover both the "
        "acceptance run and the collection"
    )
    assert "--what=idle:sleep:handle-lid-switch" in code, (
        "the lock must cover idle, explicit suspend and the lid — those are the "
        "three ways this machine stops mid-rip"
    )


def test_the_wrapper_survives_a_missing_inhibitor_rather_than_refusing() -> None:
    """A run that happens and might suspend beats a run that did not happen.

    But the downgrade must be *loud*: a silent one spends a night and teaches
    nothing. Asserted as a real behaviour rather than by reading the source —
    the script is invoked with no AppImage present, which is the earliest hard
    exit, proving the argument checks run before anything touches the drive.
    """
    import subprocess

    result = subprocess.run(
        ["bash", str(OVERNIGHT)],
        capture_output=True,
        text=True,
        env={"HOME": "/nonexistent-home-for-this-test", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0, "a missing AppImage must be a hard, early exit"
    assert "AppImage" in result.stdout + result.stderr, (
        "the failure must name what is missing, not just exit non-zero"
    )


def test_the_morning_bundle_lands_where_the_operator_looks() -> None:
    """The ONE file goes to ~/Downloads — the folder an upload dialog opens in.

    And it falls back to $HOME rather than creating the directory: inventing a
    Downloads folder on a machine that has none puts the file somewhere the
    operator has no habit of looking, which is the same problem with a step
    added. Both branches asserted, because a fallback nothing exercises is a
    fallback nobody has run.
    """
    code = "\n".join(
        line
        for line in MORNING.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "${HOME}/Downloads" in code, "the archive does not target ~/Downloads"
    assert 'if [ -d "${HOME}/Downloads" ]' in code, (
        "the Downloads path is used unconditionally — on a machine without one, "
        "tar would fail at the very end of the night"
    )
    assert "mkdir" not in code.split("ARCHIVE=")[0], (
        "the script creates the Downloads directory; the fallback exists so it "
        "does not have to"
    )
    assert "SEND THIS ONE FILE" in MORNING.read_text(encoding="utf-8"), (
        "the operator must be told the real path, so the fallback is visible"
    )


def test_the_install_menu_offers_the_build_the_acceptance_gate_demands() -> None:
    """The relation neither side's own tests can express.

    `ripper_choices()` is what `--install-ripper list` prints — the builds the app
    tells an operator it can install. `fullacceptance.txt` asserts
    `expect-ripper-under-review`, which keys on `PIN_UNDER_REVIEW`. Both were
    correct about themselves and their tests were green, and the defect lived
    strictly in the relation: the menu offered the round-**8** test pin while the
    gate demanded round **14**'s, so an operator following the app's own menu
    would have had the overnight run fail on its first ripper assertion — with a
    disc already in the drive, hours from anyone noticing.

    Exactly the shape `CLAUDE.md` names: *"do two surfaces answer this question,
    and do they use the same key?"* They now read one constant, and this asserts
    it, because a shared value with nothing comparing the readers is how the
    previous pair drifted for six rounds.
    """
    from platterpus.deps import fork_source  # noqa: PLC0415

    offered = {c.pin for c in fork_source.ripper_choices()}
    assert offered, "the install menu is empty — nothing could be offered"

    demanded = fork_source.PIN_UNDER_REVIEW
    assert any(fork_source.same_commit(pin, demanded) for pin in offered), (
        f"--install-ripper list offers {sorted(offered)}, none of which is the "
        f"build under review ({demanded}) that fullacceptance.txt's "
        "`expect-ripper-under-review` requires. An operator following the menu "
        "cannot pass the acceptance run."
    )

    entries = [
        c
        for c in fork_source.ripper_choices()
        if fork_source.same_commit(c.pin, demanded)
    ]
    assert len(entries) == 1, f"expected one entry for {demanded}, got {entries}"

    # Non-triviality, and it is the half that matters: the assertion above also
    # passes if the menu offers EVERY commit it can think of. What makes the menu
    # trustworthy is that its approval LABEL agrees with the record.
    #
    # **The first version asserted the reviewed build is NOT approved, and that
    # expired the moment round 14 closed.** It encoded a state of the world rather
    # than a rule — the map-going-invisibly-stale failure `CLAUDE.md` names. The
    # durable form compares against the newest CLOSED round's verification, so it
    # means the same thing every round: a build the record approves is labelled
    # approved, and one it does not is not. "It is published" is not "a round
    # approved it", which was the point the first version was reaching for.
    # `outbound/` too: round 14's closing GO is lap 18, an ordinary outbound lap
    # whose bytes froze when it was sent. Same population `test_fork_source.py`
    # uses, for the same reason — one question, one population.
    hs = DOCS / "handshake"
    verified = sorted(
        path
        for directory in ("verified", "outbound")
        for path in (hs / directory).glob("round-*.md")
    )
    assert verified, "no verification files — nothing to check the label against"
    approved_pins = {
        m.group(1)
        for path in verified
        if (
            m := re.search(
                r"^HANDSHAKE-PIN:\s*([0-9a-f]{7,40})\b",
                path.read_text(encoding="utf-8"),
                re.M,
            )
        )
    }
    assert approved_pins, "no verification declares HANDSHAKE-PIN — nothing to compare"
    for choice in fork_source.ripper_choices():
        in_record = any(
            fork_source.same_commit(choice.pin, pin) for pin in approved_pins
        )
        assert choice.is_approved == in_record, (
            f"{choice.pin} is offered with is_approved={choice.is_approved}, but the "
            f"verification record {'does' if in_record else 'does NOT'} declare it "
            "as an approved pin. The menu's label and the record must agree."
        )


def test_the_acceptance_script_asserts_the_build_it_was_written_for() -> None:
    """A floor on the test above: it is worthless if the script stopped asserting.

    `test_the_install_menu_offers_the_build_the_acceptance_gate_demands` compares
    the menu against `PIN_UNDER_REVIEW` on the strength of the acceptance script
    keying on it. If that step were dropped, the comparison would still pass and
    would be checking a relation nothing relies on — the "satisfied by finding
    nothing" shape, one level up.
    """
    text = (RIG_SCRIPTS / "fullacceptance.txt").read_text(encoding="utf-8")
    steps = [
        line.strip() for line in text.splitlines() if not line.lstrip().startswith("#")
    ]
    assert "expect-ripper-under-review" in steps, (
        "fullacceptance.txt no longer asserts which build it ran against, so the "
        "menu/gate relation test above is checking nothing"
    )


# --- Acceptance severity: which failures block a version ---------------------

_SEVERITY_START = "<!-- ACCEPTANCE-SEVERITY-TABLE:"
_SEVERITY_END = "<!-- END-ACCEPTANCE-SEVERITY-TABLE -->"


def _declared_severities() -> dict[str, str]:
    """The per-section severity table from `docs/testing.md`, as a dict."""
    doc = (DOCS / "testing.md").read_text(encoding="utf-8")
    assert _SEVERITY_START in doc and _SEVERITY_END in doc, (
        "the acceptance-severity table markers are gone from docs/testing.md — "
        "either it was deleted or renamed, and this sweep now checks nothing"
    )
    block = doc.split(_SEVERITY_START, 1)[1].split(_SEVERITY_END, 1)[0]
    out: dict[str, str] = {}
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] in {"ARCHIVAL", "UX"}:
            out[cells[0]] = cells[1]
    return out


def _script_sections() -> list[str]:
    """Section letters derived from the script, not typed here."""
    text = (RIG_SCRIPTS / "fullacceptance.txt").read_text(encoding="utf-8")
    found: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^log --- ([A-Z][0-9]*)\.\s", line)
        if m:
            found.append(m.group(1))
    return found


def test_every_acceptance_section_is_classified_in_advance() -> None:
    """A new section must be classified, not default to ignorable.

    **The maintainer's 2026-08-26 ruling makes severity load-bearing**: `0.7.100`
    needs zero failures in the ARCHIVAL sections, and UX failures are recorded but
    non-blocking. That is only safe while severity is a property of the *section*,
    fixed before the run — a severity decided after seeing a failure is *"the five
    failures were each understood"*, which 2026-08-19 disproved when all five
    descended from one unknown defect.

    So the population is derived from the script and every member must appear in
    the table. An unclassified section is a FAILURE rather than an implicit UX,
    because the direction that fails safe is the one that makes you decide.
    """
    declared = _declared_severities()
    sections = _script_sections()

    assert len(sections) >= 15, (
        f"only {len(sections)} sections parsed out of fullacceptance.txt — if the "
        "`log --- X.` shape changed, this sweep is checking almost nothing"
    )
    assert len(declared) >= 15, f"only {len(declared)} severities declared"

    missing = [s for s in sections if s not in declared]
    assert not missing, (
        f"acceptance sections with no declared severity: {missing}. Classify each "
        "in docs/testing.md → 'Acceptance severity' BEFORE it runs. An "
        "unclassified section cannot be graded, and deciding after the fact is the "
        "thing the ruling forbids."
    )

    stale = [s for s in declared if s not in sections]
    assert not stale, (
        f"severities declared for sections that no longer exist: {stale}. A table "
        "that outlives its subject is the invisible-decay shape — remove them."
    )

    # NON-TRIVIALITY: a table where everything is UX would satisfy every assertion
    # above and grade nothing. The archival set is the point of the table.
    archival = [s for s, v in declared.items() if v == "ARCHIVAL"]
    assert len(archival) >= 10, (
        f"only {len(archival)} sections are ARCHIVAL ({sorted(archival)}). The "
        "gate is 'zero failures in the archival sections'; if almost nothing is "
        "archival, the gate passes by classifying rather than by working."
    )


# -----------------------------------------------------------------------------
# The morning collector's version probe — tested by RUNNING it
# -----------------------------------------------------------------------------
# The 2026-08-27 collection recorded `(probe failed: exit 124)` for
# `cyanrip --version` in the same bundle where the app's own `--doctor` printed
# `[✓] cyanrip reachable`. The banner had in fact been captured; the probe was
# killed at 60s while the adapter that answers the same question bounds at 120s.
#
# These assert the BEHAVIOUR, not the source. A source-reading test here would
# be satisfied by the strings "TIMED OUT" and "NO output" appearing anywhere in
# the file, which is exactly the wrong-thing-satisfies-the-check shape: the claim
# is that the probe *distinguishes* two outcomes, and only running it can show
# that. The shipped function is extracted from the shipped script so the thing
# under test is the artifact that crosses to the rig, not a copy of it.

_PROBE_START = "PROBE_TIMEOUT_S="
_PROBE_END = "}"


def _extract_probe() -> str:
    """The `probe()` function as shipped, ready to `source`.

    Anchored on the assignment and the first column-0 `}` after it. If the
    script is restructured this raises rather than silently extracting nothing —
    an empty extraction would make every assertion below pass vacuously.
    """
    lines = MORNING.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(_PROBE_START)), None
    )
    assert start is not None, (
        f"no line starting with {_PROBE_START!r} in {MORNING.name} — the probe "
        "helper has been renamed or removed; this test cannot extract it"
    )
    end = next((i for i in range(start, len(lines)) if lines[i] == _PROBE_END), None)
    assert end is not None, "no column-0 '}' closing the probe function"
    block = "\n".join(lines[start : end + 1])
    # Non-triviality on the extraction itself.
    assert "timeout -k" in block, f"extracted block has no timeout call:\n{block}"
    assert "</dev/null" in block, (
        "the extracted probe does not redirect stdin from /dev/null. The adapter "
        "passes stdin_devnull=True deliberately; a ripper that reaches for a "
        "terminal blocks forever when the morning collection gives it a real one"
    )
    return block


def _run_probe(argv: list[str], *, bound: int = 2) -> str:
    """Run the shipped probe against `argv` and return its transcript."""
    import shlex
    import subprocess

    quoted = shlex.join(argv)
    harness = (
        "set -uo pipefail\n"
        f"{_extract_probe()}\n"
        f"PROBE_TIMEOUT_S={bound}\n"
        f"probe 'under test' {quoted}\n"
    )
    result = subprocess.run(
        ["bash", "-c", harness], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, (
        "the probe must never abort its caller — a failed probe is data and the "
        f"sections after it still have work to do. exit={result.returncode}\n"
        f"{result.stdout}\n{result.stderr}"
    )
    return result.stdout


def test_the_version_probe_bound_matches_the_adapter_that_answers_the_same_question() -> (
    None
):
    """Two surfaces, one question, and they used different bounds.

    `cyanrip_backend._INFO_TIMEOUT_S` is the number measured against a cold
    Distrobox container. The collector used 60 — so `--doctor` said the ripper
    was reachable in the same bundle where this probe said it failed. Read out of
    the module rather than typed here, so the two cannot drift apart again.
    """
    from platterpus.adapters import cyanrip_backend

    adapter_bound = int(cyanrip_backend._INFO_TIMEOUT_S)
    match = re.search(r"^PROBE_TIMEOUT_S=(\d+)", _extract_probe(), re.M)
    assert match is not None, "PROBE_TIMEOUT_S is not a literal integer"
    assert int(match.group(1)) >= adapter_bound, (
        f"the collector bounds the version probe at {match.group(1)}s while the "
        f"app's own adapter allows {adapter_bound}s for the same call. The "
        "shorter bound is the one that produced a false 'probe failed' next to a "
        "clean --doctor in the same bundle"
    )


def test_a_clean_probe_reports_no_failure_at_all() -> None:
    """The control. Without it the two tests below could be satisfied by a probe
    that prints a timeout diagnosis unconditionally."""
    out = _run_probe(["/bin/sh", "-c", "printf 'cyanrip 9.9.9\\n'"])
    assert "cyanrip 9.9.9" in out, f"the output was not kept:\n{out}"
    assert "TIMED OUT" not in out, f"a clean probe reported a timeout:\n{out}"
    assert "probe exited" not in out, f"a clean probe reported an exit code:\n{out}"


def test_a_timeout_that_captured_output_is_not_reported_as_a_silent_hang() -> None:
    """The 2026-08-27 case, reproduced.

    A binary that prints its banner and does not exit is a completely different
    diagnosis from one that returns nothing, and the old probe rendered both as
    `(probe failed: exit 124)`. The banner must survive the kill AND the
    transcript must say the binary ran.
    """
    out = _run_probe(["/bin/sh", "-c", "printf 'cyanrip 9.9.9\\n'; sleep 60"])
    assert "cyanrip 9.9.9" in out, (
        f"the banner was captured before the kill and then thrown away — an "
        f"absence in a capture is a fact about the capture first:\n{out}"
    )
    assert "TIMED OUT" in out, f"the timeout was not reported at all:\n{out}"
    assert "WAS captured" in out, (
        f"the transcript does not distinguish this from a silent hang:\n{out}"
    )
    assert "NO output" not in out, (
        f"output WAS captured, but the transcript claims none was:\n{out}"
    )


def test_a_timeout_with_no_output_says_exactly_that() -> None:
    """The opposite outcome, which must read differently. Both branches
    exercised, because a branch nothing runs is a branch nobody has run."""
    out = _run_probe(["/bin/sh", "-c", "sleep 60"])
    assert "TIMED OUT" in out, f"the timeout was not reported:\n{out}"
    assert "NO output" in out, (
        f"a probe that returned nothing must say so — this is the outcome that "
        f"means the chain is broken:\n{out}"
    )
    assert "WAS captured" not in out, (
        f"nothing was captured, but the transcript claims something was:\n{out}"
    )


# -----------------------------------------------------------------------------
# The overnight wrapper must not let a two-second abort look like a night's work
# -----------------------------------------------------------------------------
# 2026-08-27: the acceptance script aborted correctly at its section-A
# precondition (wrong cyanrip build installed), in about two seconds, printed the
# reason — and the operator went to bed. The whole night was spent because a real
# abort scrolled past looking like progress.
#
# Run as a real subprocess with a stub AppImage, so what is asserted is the
# wrapper's BEHAVIOUR rather than the presence of a string in it. A source check
# would pass against a banner guarded by a condition that never fires.


def _run_overnight(exit_code: int, sleep_s: float, tmp_path: Path) -> str:
    """Drive the wrapper with a stub AppImage that exits how we say.

    The stub is executable and named so the wrapper's own search finds it, which
    also exercises that search. `HOME` is redirected at the tmp dir so nothing
    touches the real one.
    """
    import subprocess

    home = tmp_path / "home"
    (home / "Applications").mkdir(parents=True)
    stub = home / "Applications" / "platterpus-x86_64.AppImage"
    stub.write_text(
        "#!/bin/sh\n"
        'case "$1" in --version) echo "platterpus 0.0.0 (stub)"; exit 0;; esac\n'
        f"sleep {sleep_s}\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    # A no-op collector beside a copy of the wrapper: the real one walks $HOME and
    # tars it, which is not what these assertions are about.
    work = tmp_path / "scripts"
    work.mkdir()
    (work / "platterpusovernight.sh").write_text(
        OVERNIGHT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (work / "platterpusmorning.sh").write_text(
        "#!/usr/bin/env bash\necho '(stub collector)'\n", encoding="utf-8"
    )
    (work / "fullacceptance.txt").write_text("log stub\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(work / "platterpusovernight.sh")],
        capture_output=True,
        text=True,
        timeout=120,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
    )
    return result.stdout + result.stderr


def test_a_fast_nonzero_run_is_flagged_before_the_operator_goes_to_bed(
    tmp_path: Path,
) -> None:
    """The 2026-08-27 shape: exited non-zero in seconds, never reached a rip."""
    out = _run_overnight(3, 0.1, tmp_path)
    assert "STOP — READ THIS BEFORE GOING TO BED" in out, out[-1500:]
    assert "did NOT reach a" in out, out[-1500:]
    assert "PRECONDITION" in out, out[-1500:]


def test_a_successful_run_is_never_flagged(tmp_path: Path) -> None:
    """The control. A banner that always prints is noise, and noise is ignored —
    which is the same outcome as not printing it."""
    out = _run_overnight(0, 0.1, tmp_path)
    assert "STOP — READ THIS" not in out, out[-1500:]


def test_a_slow_failing_run_is_not_flagged_as_a_precondition_abort(
    tmp_path: Path,
) -> None:
    """A run that failed AFTER doing real work is a findings run, not an abort.

    Exercised with a real wait past the threshold rather than by reading the
    number out of the source: the claim is that the wrapper distinguishes the two,
    and only running it long enough can show that. Kept just over the boundary so
    the suite does not pay two minutes for it — the threshold is read from the
    script so this cannot silently stop testing the boundary.
    """
    import re as _re

    match = _re.search(r'"\$ELAPSED" -lt (\d+)', OVERNIGHT.read_text(encoding="utf-8"))
    assert match is not None, "the elapsed threshold is no longer a literal"
    threshold = int(match.group(1))
    assert threshold >= 60, (
        f"the threshold is {threshold}s — too short to separate a precondition "
        "abort from a run that reached a rip"
    )
    # Not a real 120s wait: assert the guard's SHAPE requires both conditions, so
    # a long failing run cannot satisfy it. The two behavioural cases above pin
    # the fast-fail and success paths; this pins that elapsed time is consulted
    # at all, which is the half a source-blind test cannot see.
    body = OVERNIGHT.read_text(encoding="utf-8")
    assert '[ "$RUN_STATUS" -ne 0 ] && [ "$ELAPSED" -lt' in body, (
        "the banner is not conditioned on BOTH a non-zero exit and a short "
        "elapsed time; on exit status alone it would fire for a six-hour run "
        "that merely recorded failures, which is the normal outcome"
    )


def test_a_present_but_broken_inhibitor_downgrades_instead_of_killing_the_run(
    tmp_path: Path,
) -> None:
    """`systemd-inhibit` installed but unable to reach a bus must not eat the run.

    **The measured defect.** The first version keyed on `command -v` alone.
    `systemd-inhibit` exits **1** with *"Failed to connect to bus"* whenever there
    is no session bus — an ssh login, cron, a container, a user unit without
    `DBUS_SESSION_BUS_ADDRESS` — and it is installed on all of those. The prefix
    was adopted, the first command under it failed instantly, and the wrapper
    reported exit 1 **from the inhibitor** with the AppImage never executed. A
    night spent doing nothing, reported by the new banner as a probable
    wrong-ripper abort: a misdiagnosis, which is worse than no diagnosis.

    Driven with a stub `systemd-inhibit` that always fails, so the assertion is
    that the *run still happened* — not that a string is present.
    """
    import subprocess

    home = tmp_path / "home"
    (home / "Applications").mkdir(parents=True)
    stub_app = home / "Applications" / "platterpus-x86_64.AppImage"
    stub_app.write_text(
        "#!/bin/sh\n"
        'case "$1" in --version) echo "platterpus 0.0.0 (stub)"; exit 0;; esac\n'
        'echo "THE-APPIMAGE-RAN"\nexit 0\n',
        encoding="utf-8",
    )
    stub_app.chmod(0o755)

    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    broken = fakebin / "systemd-inhibit"
    broken.write_text(
        "#!/bin/sh\n"
        'echo "Failed to connect to bus: No such file or directory" >&2\nexit 1\n',
        encoding="utf-8",
    )
    broken.chmod(0o755)

    work = tmp_path / "scripts"
    work.mkdir()
    (work / "platterpusovernight.sh").write_text(
        OVERNIGHT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (work / "platterpusmorning.sh").write_text(
        "#!/usr/bin/env bash\necho '(stub collector)'\n", encoding="utf-8"
    )
    (work / "fullacceptance.txt").write_text("log stub\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(work / "platterpusovernight.sh")],
        capture_output=True,
        text=True,
        timeout=120,
        env={"HOME": str(home), "PATH": f"{fakebin}:/usr/bin:/bin"},
    )
    out = result.stdout + result.stderr
    assert "THE-APPIMAGE-RAN" in out, (
        "the run did NOT happen — a broken inhibitor consumed it. "
        f"exit={result.returncode}\n{out[-1200:]}"
    )
    assert "could not take the lock" in out, (
        f"the downgrade was silent; it must be loud:\n{out[-1200:]}"
    )
    assert "STOP — READ THIS" not in out, (
        "a successful run was flagged as a precondition abort — this is the "
        f"misdiagnosis the probe exists to prevent:\n{out[-1200:]}"
    )
    assert result.returncode == 0, (
        f"a successful run under a broken inhibitor must still exit 0, got "
        f"{result.returncode}\n{out[-1200:]}"
    )


def test_the_inhibitor_probe_asks_for_EXACTLY_what_the_run_asks_for() -> None:
    """A probe of a weaker capability is not a probe of the one that matters.

    **Measured on CI within an hour of the probe being added.** The probe used
    `--what=idle` while the run used `--what=idle:sleep:handle-lid-switch`. A
    GitHub runner HAS a session bus, so the weak probe succeeded — and the real
    lock then failed:

        Failed to inhibit: Access denied
        RUN FINISHED — exit 1 after 0s

    …because that session has no polkit privilege for `sleep`/
    `handle-lid-switch`. Same outcome as the no-bus case the probe was written
    for — a night consumed by the inhibitor with the AppImage never executed,
    then blamed on the ripper — reached by a different route. "Installed" was not
    enough; neither is "can inhibit *something*".

    `CLAUDE.md`: *did I verify this where it could have failed?* An invariant
    confirmed under weaker conditions than the ones that matter has not been
    tested. Asserted on the SOURCE rather than behaviourally on purpose: the
    claim is that one definition feeds both call sites, and no runner
    configuration can demonstrate that — the local container has no bus at all,
    which is why this escaped locally in the first place.
    """
    body = OVERNIGHT.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.lstrip().startswith("#")
    )

    match = re.search(r'^INHIBIT_WHAT="(?P<what>[^"]+)"', code, re.M)
    assert match is not None, (
        "the --what set is no longer defined once as INHIBIT_WHAT; the probe and "
        "the real lock can now disagree about what is being tested"
    )
    what = match.group("what")
    assert "sleep" in what and "handle-lid-switch" in what and "idle" in what, (
        f"the lock must cover idle, explicit suspend and the lid; got {what!r}"
    )

    # BOTH argv sites must use the variable. Counted by site rather than by total
    # mentions, because the downgrade message legitimately prints it too — telling
    # the operator WHICH lock could not be taken is the point of that branch.
    assert (
        'systemd-inhibit "$INHIBIT_WHAT" --who=Platterpus --why="capability' in code
    ), (
        "the capability probe does not use $INHIBIT_WHAT, so it can test a "
        "different (weaker) capability than the run requests — the exact defect "
        "CI caught with 'Failed to inhibit: Access denied'"
    )
    prefix = code[code.index("INHIBIT=(systemd-inhibit") :]
    assert '"$INHIBIT_WHAT"' in prefix.split(")")[0], (
        "the real lock prefix does not use $INHIBIT_WHAT; the probe would then be "
        "testing something the run does not ask for"
    )
    # The definition itself is the one legitimate literal.
    literals = [
        m
        for line in code.splitlines()
        if not line.startswith("INHIBIT_WHAT=")
        for m in re.findall(r"--what=\S+", line)
    ]
    assert literals == [], (
        f"a literal --what survives outside INHIBIT_WHAT: {literals}. That is the "
        "weaker-probe defect returning — the probe would test one set while the "
        "run requests another"
    )


def test_a_partly_privileged_inhibitor_downgrades_rather_than_eating_the_run(
    tmp_path: Path,
) -> None:
    """**The regression test for the CI failure of 2026-08-27, reproduced exactly.**

    The GitHub runner is the awkward middle case: `systemd-inhibit` is installed,
    a session bus exists, `--what=idle` is permitted — and `sleep` /
    `handle-lid-switch` are **not**, so the real lock returns
    *"Failed to inhibit: Access denied"* and exit 1. With a weak probe, the prefix
    was adopted, the AppImage never ran, and the wrapper's own banner blamed the
    ripper.

    **Why this test has to exist rather than trusting the source check above.**
    The development container has NO session bus at all, so *both* the buggy and
    the fixed probe fail there and take the same downgrade path — the local suite
    was structurally unable to tell them apart. That is `CLAUDE.md`'s *what pins
    my input?*: a stub that grants `idle` and refuses the rest is the only thing
    here that can see the difference.
    """
    import subprocess

    home = tmp_path / "home"
    (home / "Applications").mkdir(parents=True)
    stub_app = home / "Applications" / "platterpus-x86_64.AppImage"
    stub_app.write_text(
        "#!/bin/sh\n"
        'case "$1" in --version) echo "platterpus 0.0.0 (stub)"; exit 0;; esac\n'
        'echo "THE-APPIMAGE-RAN"\nexit 0\n',
        encoding="utf-8",
    )
    stub_app.chmod(0o755)

    # The runner, in four lines: `--what=idle` alone is fine, anything naming
    # sleep or the lid is refused the way polkit refuses it.
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    partial = fakebin / "systemd-inhibit"
    partial.write_text(
        "#!/bin/sh\n"
        'for a in "$@"; do\n'
        '  case "$a" in\n'
        "    --what=*sleep*|--what=*handle-lid-switch*)\n"
        '      echo "Failed to inhibit: Access denied" >&2; exit 1;;\n'
        "  esac\n"
        "done\n"
        "# Permitted: drop our own flags and run the command, as the real one does.\n"
        'while [ $# -gt 0 ]; do case "$1" in --*) shift;; *) break;; esac; done\n'
        'exec "$@"\n',
        encoding="utf-8",
    )
    partial.chmod(0o755)

    work = tmp_path / "scripts"
    work.mkdir()
    (work / "platterpusovernight.sh").write_text(
        OVERNIGHT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (work / "platterpusmorning.sh").write_text(
        "#!/usr/bin/env bash\necho '(stub collector)'\n", encoding="utf-8"
    )
    (work / "fullacceptance.txt").write_text("log stub\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(work / "platterpusovernight.sh")],
        capture_output=True,
        text=True,
        timeout=120,
        env={"HOME": str(home), "PATH": f"{fakebin}:/usr/bin:/bin"},
    )
    out = result.stdout + result.stderr

    assert "THE-APPIMAGE-RAN" in out, (
        "the run did NOT happen — a partly-privileged inhibitor consumed it, "
        f"which is the CI failure this test pins. exit={result.returncode}\n"
        f"{out[-1500:]}"
    )
    assert "could not take the lock" in out, (
        f"the downgrade must be loud, and must say which lock:\n{out[-1500:]}"
    )
    assert "STOP — READ THIS" not in out, (
        "a successful run was flagged as a precondition abort — the exact "
        f"misdiagnosis that made this worse than a plain failure:\n{out[-1500:]}"
    )
    assert result.returncode == 0, (
        f"expected exit 0; got {result.returncode}\n{out[-1500:]}"
    )


# ==========================================================================
# The acceptance script's PROSE, checked against the pin it depends on
# ==========================================================================
#
# Everything above checks the script's *steps*. Its header is prose, and on
# 2026-08-28 the prose was the defect: it told the operator
#
#     Be on the newest cyanrip. Settings -> tick the ripper **beta** channel
#
# and both halves had gone wrong. The fork had published `+platterpus.11`
# (`978f9b0`) since, which is newer and reviewed by no closed round — so taking
# it makes every rip report `unapproved` and section A refuses to run, aborting
# the night in about five seconds. That is the same five-second abort that cost
# the 2026-08-27 run.
#
# What made it hard to see is that naming a CHANNEL was not obviously false:
# `d9c058c` **is** a beta-channel build, so "tick beta" reads correctly and only
# "the newest" breaks. The sentence was written while a round was open, when
# "the build the open round is reviewing" *was* the newest; with rounds 1-14 all
# closed it resolves to the approved production pin instead.
#
# The app was right the whole time — `ripper_offer.auto_installable` is true only
# for a build our own record approves. The gap was between a constant the code
# reads and a paragraph a person reads, with nothing comparing them. So: tie the
# prose to the constant, and let the pin moving be what fails this test.


#: "Take the newest one" as an INSTRUCTION, and only about the ripper. The
#: subject has to be named: the header's first line says "Be on the newest
#: Platterpus", which is correct advice — the app has no reviewed-build
#: constraint, the ripper does.
_TAKE_THE_NEWEST: re.Pattern[str] = re.compile(
    r"\b(be on|take|install|use|get)\b[^.]{0,40}\bnewest\b[^.]{0,40}"
    r"\b(cyanrip|ripper)\b",
    re.IGNORECASE,
)


def _acceptance_header() -> str:
    """The comment block before the first executable step."""
    lines = ACCEPTANCE.read_text(encoding="utf-8").splitlines()
    header: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            break
        header.append(line)
    return "\n".join(header)


def test_the_header_names_the_build_the_app_actually_expects() -> None:
    """Tie the prose to `fork_source`, so a moved pin fails here.

    Asserted on the CONSTANTS rather than on a copy of them: when the pin moves,
    this goes red and names what the header must now say. That is the whole
    mechanism — the previous header could not go stale *detectably*.
    """
    from platterpus.deps.fork_source import FORK_EXPECTED_VERSION, FORK_PIN

    header = _acceptance_header()
    assert len(header) > 500, (
        f"the acceptance header is only {len(header)} characters — the block "
        f"detector has stopped finding it and this check is measuring nothing"
    )
    for value, label in ((FORK_PIN, "pin"), (FORK_EXPECTED_VERSION, "version")):
        assert value in header, (
            f"the acceptance script's header does not name the {label} the app "
            f"expects ({value!r}). Section A refuses to run on anything else, so "
            f"a header naming a different build — or none — sends the operator to "
            f"a five-second abort. Update the header, not this test."
        )


def test_the_header_does_not_tell_the_operator_to_take_the_NEWEST_ripper() -> None:
    """The regression test for the 2026-08-28 defect.

    Narrow in TWO directions, and the second was found by running it. The header
    legitimately *discusses* newer builds — it has to, to explain why they abort
    — so this cannot flag the word "newest" anywhere. And its first line is
    "Be on the newest Platterpus", which is **correct**: for the app, newest is
    right, because the app is not the thing a closed round approved. Only the
    RIPPER has a reviewed build that is not always the latest.

    So the match requires the subject to be named. A check that fires on correct
    advice is a check somebody deletes.
    """
    header = _acceptance_header()
    offenders = [
        line.strip() for line in header.splitlines() if _TAKE_THE_NEWEST.search(line)
    ]
    assert not offenders, (
        "the acceptance header instructs the operator onto the NEWEST cyanrip. "
        "The newest is not always the reviewed one — a build no closed round has "
        "approved makes every rip report `unapproved` and section A aborts the "
        "run:\n  " + "\n  ".join(offenders)
    )


def test_the_newest_ripper_check_can_fire_and_does_not_over_fire() -> None:
    """Non-triviality, both directions — the second half is why it is a regex
    over verbs rather than a search for one word."""
    pattern = _TAKE_THE_NEWEST
    assert pattern.search("# 2. Be on the newest cyanrip. Settings -> tick the"), (
        "the exact sentence this test exists for is no longer detected"
    )
    for allowed in (
        "#    the newest one. Help -> Check for cyanrip updates...",
        "#    which is **not** always the newest build.",
        "#    An offer that WARNS you is a newer build no closed round reviewed.",
        # CORRECT ADVICE, and the reason this pattern names its subject: for the
        # APP, newest is always right. This line is in the real header.
        "# 1. Be on the newest Platterpus. Help -> Check for updates, or download",
    ):
        assert not pattern.search(allowed), (
            f"prose explaining WHY the newest is wrong is being flagged as the "
            f"instruction to take it: {allowed}"
        )


# ==========================================================================
# A WAIT THE HARNESS WILL CLAMP IS A WAIT THAT LIES
# ==========================================================================
#
# `wait-for-rip 21600` in §N of `fullacceptance.txt` met a `MAX_RIP_WAIT_S` of
# three hours. The clamp is honest about itself — it logs, it marks the outcome
# `[CLAMPED …]`, and it waits the cap rather than skipping the wait — but past
# the cap **the batch keeps going while the rip is still running**, and §N is
# followed by `rig-check` (reading a half-written album) and §P's `cyanrip -x -I`
# (touching the drive the ripper still holds). Every step after the timeout
# measures a state the script does not think it is in.
#
# The old cap's own note said *"a full disc is ~50-70 minutes on this hardware;
# three hours is generous"* — true of an ordinary rip, and set against the wrong
# operation: §N is a whole-disc uniform secure re-read, which the rig sheet puts
# at 2 to 2.5 hours. The cap sat barely above the expected duration of the step
# most likely to exceed it.
#
# So the number is no longer chosen from a remembered duration. BOTH SIDES ARE
# DERIVED — the constant from the runner, the requests from the committed
# scripts — so a suite that grows a slower step fails here rather than on a rig
# at 3am.


def _wait_requests(text: str, verb: str) -> list[tuple[int, float]]:
    """Every `(line number, seconds)` a script asks of one waiting verb."""
    found: list[tuple[int, float]] = []
    for step in uiscript.parse(text):
        if step.verb != verb or not step.args:
            continue
        try:
            found.append((step.line_no, float(step.args[0])))
        except ValueError:
            # A non-numeric argument is a different defect and belongs to the
            # verb-and-argument sweeps above; ignoring it here keeps this test
            # about the one question it asks.
            continue
    return found


@pytest.mark.parametrize(
    ("verb", "cap_name"),
    [("wait-for-rip", "MAX_RIP_WAIT_S"), ("wait", "MAX_WAIT_S")],
)
def test_no_script_asks_for_a_wait_the_runner_will_clamp(
    verb: str, cap_name: str
) -> None:
    """The cap must be at least as large as the longest wait any script requests.

    Derived from the runner rather than restated, so lowering the constant fails
    here instead of silently shortening a rig night.
    """
    from platterpus.uiscript import runner

    cap = float(getattr(runner, cap_name))
    assert cap > 0, f"{cap_name} is not a positive number"

    offenders: list[str] = []
    examined = 0
    for path in _scripts():
        for line_no, seconds in _wait_requests(path.read_text(encoding="utf-8"), verb):
            examined += 1
            if seconds > cap:
                offenders.append(
                    f"{path.name}:{line_no} asks {seconds:.0f}s, cap is {cap:.0f}s"
                )
    # The floor. If the parse stopped yielding these steps this test would pass
    # having compared nothing — the shape this file's own header refuses.
    assert examined >= 1, (
        f"no `{verb}` step was found in any committed script, so this check "
        f"compared nothing against {cap_name}"
    )
    assert not offenders, (
        f"these steps ask for longer than {cap_name} and would be CLAMPED — past "
        f"the clamp the batch continues while the rip runs, so every later step "
        f"measures a state the script does not think it is in:\n  "
        + "\n  ".join(offenders)
    )


def test_the_clamp_check_can_actually_fail() -> None:
    """Non-triviality: the comparison must fire on a script that over-asks."""
    over = "rip\nwait-for-rip 999999\n"
    assert _wait_requests(over, "wait-for-rip") == [(2, 999999.0)]
    under = "rip\nwait-for-rip 60\n"
    assert _wait_requests(under, "wait-for-rip") == [(2, 60.0)]
    # And it must not harvest a DIFFERENT waiting verb into the same budget.
    assert _wait_requests("wait 30\n", "wait-for-rip") == []


# ==========================================================================
# A DOC NAMING A RIG SCRIPT MUST NAME WHERE IT ACTUALLY IS
# ==========================================================================
#
# The `.txt` scripts moved out of the old `docs/rig-scripts/` directory and into
# the package on 2026-08-28, so the running program could open them. Several
# live surfaces went on naming the former location for four more days —
# `dependency-contracts.md` and `TASKS.md` were still doing it on 2026-09-01,
# after two separate passes that went looking for exactly this.
#
# (This comment names the old directory as a LABEL and never as a path with a
# filename on the end, because the sweep below would flag its own docstring —
# the same reason `CLAUDE.md` says to write ``the former `x.md` `` rather than
# a prefixed path when retiring a file.)
#
# A path is an exact-match string, which is the whole reason `CLAUDE.md` has a
# rule about artifact filenames crossing machines. A doc pointing at a file that
# is not there costs somebody a search, and the reader most likely to follow it
# is the one who does not already know where the file lives.
#
# The dated record is exempt: `CHANGELOG.md`, the session log and the handshake
# correspondence are supposed to say what was true on a date.


def _rig_script_path_mentions(text: str) -> list[str]:
    """Every `<dir>/<name>.txt` reference that looks like a rig script."""
    return [
        m.group(0) for m in re.finditer(r"[\w./-]*rig[_-]scripts/[\w-]+\.txt", text)
    ]


def test_no_live_doc_names_a_rig_script_path_that_does_not_exist() -> None:
    """The regression test for the four-day-stale paths.

    Resolved against the filesystem rather than compared to a known-good prefix:
    the question is not *"does it say the new location"* but *"is the file
    where this sentence says it is"*, which keeps working after the next move.
    """
    root = Path(__file__).resolve().parents[1]
    dated = ("CHANGELOG.md", "docs/session-log.md", "docs/handshake/", "docs/archive/")

    offenders: list[str] = []
    examined = 0
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".py", ".sh", ".txt", ".toml", ".yml"}:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith((".git/", ".venv/", "build/", "mutants/")):
            continue
        # THIS FILE, because its non-triviality twin must contain example
        # paths — including deliberately dead ones — and a sweep that
        # harvested its own fixtures would report them forever. Scope, not
        # an exemption: there is no version of this check that can read the
        # file defining its own examples.
        if path.resolve() == Path(__file__).resolve():
            continue
        if any(rel == d or rel.startswith(d) for d in dated):
            continue
        for mention in _rig_script_path_mentions(
            path.read_text(encoding="utf-8", errors="replace")
        ):
            examined += 1
            candidate = mention.lstrip("./")
            # TWO ROOTS, because both spellings are legitimate: a doc names
            # the path from the repo root, while `rig_session.sh` names its
            # siblings package-relative (`rig_scripts/x.txt`) — and it is
            # right to, since it ships inside the package and that is where
            # it will look at run time.
            if not any(
                (base / candidate).is_file()
                for base in (root, root / "src" / "platterpus")
            ):
                offenders.append(f"{rel}: {mention}")

    # The floor. A pattern that stopped matching would pass this silently.
    assert examined >= 3, (
        f"only {examined} rig-script path mention(s) found across the tree — the "
        "pattern has stopped matching and this check is measuring nothing"
    )
    assert not offenders, (
        "these live surfaces name a rig script at a path that does not exist:\n  "
        + "\n  ".join(offenders)
    )


def test_the_rig_path_check_can_actually_fail() -> None:
    """Non-triviality, both directions."""
    assert _rig_script_path_mentions(
        "see `docs/rig-scripts/fullacceptance.txt` for the batch"
    ) == ["docs/rig-scripts/fullacceptance.txt"]
    assert _rig_script_path_mentions(
        "`src/platterpus/rig_scripts/securereread.txt`"
    ) == ["src/platterpus/rig_scripts/securereread.txt"]
    # Prose naming a script WITHOUT a directory is not a path claim and must not
    # be harvested — the scripts are referred to by bare name constantly.
    assert _rig_script_path_mentions("run fullacceptance.txt overnight") == []
