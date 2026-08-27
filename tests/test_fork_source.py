"""The wizard's plan for installing the pinned Platterpus fork of cyanrip.

The commands cannot be executed here — there is no Distrobox, no container, and
no compiler for a foreign source tree in CI — so what is testable is the *plan*:
its order, its shape, the safety of how values reach the shell, and the fact that
the pin the code builds is the pin the handshake record says was verified.

That last one is the point of this file. A pin that lives only in a constant
drifts from the round that approved it, and "which commit is my ripper" then has
two answers. So the constant is checked against the committed handshake
document — reading the artifact, not remembering it.
"""

from __future__ import annotations

import importlib.util
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from platterpus.deps import fork_source
from platterpus.deps.host_setup import DEFAULT_CONTAINER


def _handshake() -> ModuleType:
    """Load `scripts/handshake.py`, which owns the handshake file ordering.

    Imported rather than re-implemented: `sort_key` is the single definition of "which
    handshake file is newer", and this file used to carry the third copy of it.
    """
    script = Path(__file__).resolve().parents[1] / "scripts" / "handshake.py"
    spec = importlib.util.spec_from_file_location("handshake_ordering", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER = DEFAULT_CONTAINER


# --- provenance: the pin matches the record ---------------------------------


def test_the_pin_is_the_one_the_newest_closed_handshake_round_verified() -> None:
    """Read the artifact, do not trust the memory of it.

    ``docs/handshake/verified/round-N.md`` is our own GO for a specific commit.
    If the constant and the document disagree, one of them is wrong and the
    disagreement IS the bug report — exactly the reasoning the fork and we agreed
    on for two independent expressions of one contract.

    **This test was passing for the wrong reason and lap 35 exposed it**
    (2026-08-06). Its name says *the newest CLOSED round*; its body used to take
    the last element of a sort keyed on ``int(round)`` alone. Every
    ``round-07-lap-NN.md`` file therefore shares one key, Python's sort is stable,
    and the tie was broken by **directory iteration order** — so "the newest
    verification" was whichever round-7 lap the filesystem happened to yield last.
    It named ``2f950c8`` by luck for eight laps, and adding a ninth changed the
    answer. `docs/testing.md` §5.aa: a gate whose subject is chosen by chance is
    not a gate.

    Two fixes, and the second is the substantive one:

    * order with the **shared** :func:`sort_key` — `(round, lap, stem)`, total by
      construction, the single definition of "newer" both projects agreed on;
    * ask the question the name asks. ``FORK_PIN`` is the *production* pin, which
      is approved by a **closed** round. The newest file overall is a lap of the
      round currently OPEN, and an open round's laps are not approvals — that is
      the whole point of the bilateral-GO rule. The test-pin half is a separate
      check (:func:`test_the_wizard_target_is_named_in_the_handshake_record`), and
      conflating them is what let an open round's file stand in for an approval.
    """
    handshake = _handshake()
    # **`outbound/` AS WELL AS `verified/`, because our closing GO does not always
    # live in the latter.** Round 14 closed with lap 18, an ordinary outbound lap
    # carrying `HANDSHAKE-VERDICT: GO` — and once SENT its bytes were frozen (the
    # fork's lap 19 digest covers them), so it could not be moved into `verified/`,
    # whose files must additionally open with a bolded `**GO on <pin>` line.
    # `handshake.py --status` already reads our verdict correctly from `outbound/`;
    # only this check looked at one directory, so two surfaces answered "is round
    # 14 verified by us?" differently. One question, one population.
    root = REPO_ROOT / "docs" / "handshake"
    verified = sorted(
        [
            path
            for directory in ("verified", "outbound")
            for path in (root / directory).glob("round-*.md")
        ],
        key=handshake.sort_key,
    )
    assert verified, "no verification files — cannot check the pin against the record"

    # Which rounds are CLOSED, read off the tooling rather than re-derived here.
    closed_rounds = {
        int(match.group(1))
        for line in handshake.round_status()
        if (match := re.match(r"round-(\d+):.*-> CLOSED", line))
    }
    assert closed_rounds, (
        "no closed handshake round — the production pin cannot have been approved"
    )
    newest_closed = max(closed_rounds)
    candidates = [
        path for path in verified if handshake.sort_key(path)[0] == newest_closed
    ]
    assert candidates, (
        f"round {newest_closed} reports CLOSED but has no verification file"
    )
    newest = candidates[-1]
    text = newest.read_text(encoding="utf-8")

    # **THE DECLARED FIELD, NOT A SUBSTRING**, and the difference is not academic.
    # This read `FORK_PIN in text` — a bare substring — so any mention anywhere in
    # a 19 KB prose file satisfied it. Round 14's verification discusses `ddf7ac3`
    # at length *precisely because it was the wrong value*: it had stood in our
    # `HANDSHAKE-OUR-PIN` for nine laps and §2 is the correction. So the check
    # passed on the strength of the defect it should have caught, while the round
    # actually approved `d9c058c`.
    #
    # Exactly `CLAUDE.md`'s *"can it be satisfied by the wrong thing?"* — the same
    # shape as the handshake gate whose §I was satisfied by the sentence *"I wrote,
    # of your continuation-line sweep:"*. Where a check matches on a label, make it
    # require the subject; only the pair is a check.
    declared = re.search(r"^HANDSHAKE-PIN:\s*([0-9a-f]{7,40})\b", text, re.M)
    assert declared is not None, (
        f"{newest.name} — the newest CLOSED round's verification — declares no "
        "HANDSHAKE-PIN, so there is nothing to hold the production pin to"
    )
    assert declared.group(1).startswith(fork_source.FORK_PIN) or (
        fork_source.FORK_PIN.startswith(declared.group(1))
    ), (
        f"{newest.name} declares HANDSHAKE-PIN: {declared.group(1)}, but "
        f"FORK_PIN is {fork_source.FORK_PIN!r}. A CLOSED round approves the pin it "
        "DECLARES — so either the production pin has not been rolled forward after "
        "the close, or the wizard builds a commit no closed round approved. "
        "Rolling it forward is the post-close step; do not relax this check."
    )


def _newest_closed_round_verification() -> tuple[int, Path]:
    """``(round number, verification file)`` for the newest CLOSED round, naming the pin.

    Shared by the pin check's siblings below. Picks the **last** lap of that round
    that mentions :data:`fork_source.FORK_PIN`, because a round can be re-declared
    across laps — round 7 named ``422d12a`` in lap 40 and corrected it to ``ddf7ac3``
    in lap 41, and the correction is the one that describes what we install.
    """
    handshake = _handshake()
    # **`outbound/` AS WELL AS `verified/`, because our closing GO does not always
    # live in the latter.** Round 14 closed with lap 18, an ordinary outbound lap
    # carrying `HANDSHAKE-VERDICT: GO` — and once SENT its bytes were frozen (the
    # fork's lap 19 digest covers them), so it could not be moved into `verified/`,
    # whose files must additionally open with a bolded `**GO on <pin>` line.
    # `handshake.py --status` already reads our verdict correctly from `outbound/`;
    # only this check looked at one directory, so two surfaces answered "is round
    # 14 verified by us?" differently. One question, one population.
    root = REPO_ROOT / "docs" / "handshake"
    verified = sorted(
        [
            path
            for directory in ("verified", "outbound")
            for path in (root / directory).glob("round-*.md")
        ],
        key=handshake.sort_key,
    )
    closed_rounds = {
        int(match.group(1))
        for line in handshake.round_status()
        if (match := re.match(r"round-(\d+):.*-> CLOSED", line))
    }
    assert closed_rounds, "no closed handshake round"

    # THE ROUND THAT APPROVED THE PIN WE INSTALL — not simply the newest closed one.
    #
    # **Those coincided until round 9 closed, and the difference has release
    # consequences.** Round 9 approved `b56f936`, which is **not a numbered fork
    # release**: the fork's round-9 lap 11 §F says its logs still read *"NOT a
    # released build"* and that the line *"moves when `release-manifest.json` names a
    # commit, and not before"*. `FORK_RELEASE_SEQ_BY_PIN` has no sequence for it, and
    # `fork_source` records at length why installing such a build is the worse error:
    # every archival log it writes would carry that sentence.
    #
    # So `FORK_PIN` legitimately stays at `ddf7ac3` — round **8**'s approved release —
    # while round 9 is the newest closed round. Keying on recency made the constants
    # demand a pin we must not install; keying on the pin asks the question that
    # actually matters: *which closed round approved the build we ship?*
    #
    # This is the same shape as round 7 vs `ddf7ac3` already documented in
    # `fork_source`: an approval and an installable release are different commits, and
    # the gap between them is normal rather than exceptional.
    # **BILATERAL, because "approved" means both sides declared it.** §5's whole point.
    #
    # Round 10 exposed why one side is not enough: our lap 2 declared
    # `HANDSHAKE-PIN: ddf7ac3` — the pin we *install* — while the fork's lap 1 used the
    # same field for `b809cfc`, the pin under *review*. **Two meanings of one field
    # across the seam inside one round.** Keying on our side alone made round 10 look
    # like the round that approved `ddf7ac3`, and it approved `56413d2`; a rip report
    # would have credited the wrong round for the build it installs, which is the exact
    # failure this test exists to catch.
    #
    # Requiring the pin in a lap of OURS *and* a lap of THEIRS is the property that
    # actually matters and cannot be satisfied by one side's bookkeeping. Round 8
    # qualifies (our lap 18 and their lap 17 both declare `ddf7ac3`); round 10 does not.
    inbound_dir = REPO_ROOT / "docs" / "handshake" / "inbound"
    theirs_by_round: dict[int, list[Path]] = {}
    for path in sorted(inbound_dir.glob("round-*.md")):
        if _declares_pin(path.read_text(encoding="utf-8"), fork_source.FORK_PIN):
            theirs_by_round.setdefault(handshake.sort_key(path)[0], []).append(path)

    by_round: dict[int, list[Path]] = {}
    for path in verified:
        number = handshake.sort_key(path)[0]
        if (
            number in closed_rounds
            and number in theirs_by_round
            and _declares_pin(path.read_text(encoding="utf-8"), fork_source.FORK_PIN)
        ):
            by_round.setdefault(number, []).append(path)
    assert by_round, (
        f"no CLOSED round has a verification file DECLARING pin "
        f"{fork_source.FORK_PIN!r} in HANDSHAKE-PIN or HANDSHAKE-RELEASE. Closed "
        f"rounds: {sorted(closed_rounds)}. Either the pin moved without a round "
        "approving it, or a round's verification does not name the pin it approved."
    )
    approving = max(by_round)
    # A floor, so this cannot silently pick an ancient round while a newer closed one
    # approved the same pin and was skipped for an unrelated reason.
    assert approving <= max(closed_rounds), (approving, sorted(closed_rounds))
    return approving, by_round[approving][-1]


#: Wire fields in which naming the pin is a **declaration about** it, rather than a
#: mention of it. `HANDSHAKE-RELEASE` counts because round 7 lap 41 used it for
#: exactly the case it exists for: the same approved C source at a new release
#: commit, with `HANDSHAKE-PIN` deliberately left where it was.
_PIN_DECLARING_FIELDS: tuple[str, ...] = ("HANDSHAKE-PIN", "HANDSHAKE-RELEASE")


def _declares_pin(text: str, pin: str) -> bool:
    """Does this lap **declare** ``pin``, or merely contain the string?

    **The old check was `pin in text`, and that is the "satisfied by the wrong
    thing" shape** this project keeps finding: a label matched without its subject.
    Round 7's lap 41 declares `HANDSHAKE-PIN: 104f6d4` and contains `ddf7ac3` four
    times — in a build tag (`platterpus-fork-gddf7ac3`), in `HANDSHAKE-RELEASE`, and
    twice in prose about a `git diff`. Three of those four are not declarations, and
    a bare substring test cannot tell them apart.

    It happened to select the right file, because lap 41's `HANDSHAKE-RELEASE` **is**
    a real declaration. But it would equally have selected a lap that merely argued
    *against* the pin, or one whose only occurrence was inside another build's tag —
    and then `APPROVED_BY_ROUND` and the app version would have been read out of a
    file that declares nothing about the pin we install. Every rip report and every
    EAC-compatible log carries those two values.

    So: the pin must be the **value of a pin-declaring field**, matched whole. A
    build tag like `platterpus-fork-gddf7ac3` is excluded because the value is not
    the pin, it merely ends with it.
    """
    stripped = re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)
    for field in _PIN_DECLARING_FIELDS:
        for match in re.finditer(
            rf"^{re.escape(field)}:[ \t]*(?P<value>.*)$", stripped, re.MULTILINE
        ):
            # First whitespace-delimited token, so `ddf7ac3 — supersedes ...` counts
            # and `cyanrip 0.9.4 (platterpus-fork-gddf7ac3)` does not.
            head = match.group("value").strip().split()
            if head and head[0].strip("`") == pin:
                return True
    return False


def test_the_approval_round_and_app_version_match_the_record() -> None:
    """``handshake_approval``'s two constants, derived from the record like the pin.

    **This is a regression test for a defect that shipped in two releases**
    (2026-08-07). ``FORK_PIN`` moved to the round-7 release when round 7 closed, and
    the test above confirmed it against the record — while ``APPROVED_BY_ROUND`` and
    ``APPROVED_FOR_PLATTERPUS_VERSION``, one import away, stayed at ``6`` and
    ``"0.6.3"``. So v0.6.4 and v0.6.5 stamped *"handshake round 6 approved, for
    Platterpus 0.6.3"* into every rip report and every EAC-compatible log, about a
    pin that round **7** approved — round 6 approved a different commit entirely.

    **Why the existing tests could not see it.** They asserted
    ``str(APPROVED_BY_ROUND) in approval.detail`` — that the number we print is the
    number we hold. That passes for *every* value, including a wrong one: a list
    checked against itself is consistent, not verified (`CLAUDE.md`). The fix is to
    check against the artifact, which is what the pin beside it already did.

    Both values are read out of the newest closed round's own verification file, so
    the round number, the app version and the pin move together or this fails.
    """
    import platterpus.handshake_approval as ha

    newest_closed, verification = _newest_closed_round_verification()

    assert ha.APPROVED_BY_ROUND == newest_closed, (
        f"handshake_approval.APPROVED_BY_ROUND is {ha.APPROVED_BY_ROUND} but the "
        f"newest CLOSED round is {newest_closed} ({verification.name}). Every rip "
        f"report would credit the wrong round for approving pin {fork_source.FORK_PIN}."
    )

    # `HANDSHAKE-APP-VERSION: platterpus 0.6.5` → "0.6.5". Read off the file rather
    # than compared to `__version__`: the field names the version the pairing was
    # declared at, which deliberately stays put as the app version moves on.
    header = re.search(
        r"^HANDSHAKE-APP-VERSION:\s*platterpus\s+(?P<version>\S+)",
        verification.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert header is not None, (
        f"{verification.name} has no HANDSHAKE-APP-VERSION line — the protocol "
        f"requires one, so the app version this pin was approved for is not derivable"
    )
    declared = header.group("version")
    assert ha.APPROVED_FOR_PLATTERPUS_VERSION == declared, (
        f"handshake_approval.APPROVED_FOR_PLATTERPUS_VERSION is "
        f"{ha.APPROVED_FOR_PLATTERPUS_VERSION!r} but {verification.name} — the newest "
        f"closed round's verification naming pin {fork_source.FORK_PIN} — declares "
        f"{declared!r}"
    )


def test_the_approval_constants_check_is_not_vacuous() -> None:
    """The floor for the test above: it must be comparing to something real.

    A check that reads a file and finds nothing passes just as quietly as one that
    finds agreement. Assert the subject exists and is non-trivial — a closed round
    numbered at least 1, a file that actually names the pin, and a declared app
    version that looks like a version rather than an empty match.
    """
    newest_closed, verification = _newest_closed_round_verification()
    assert newest_closed >= 1
    text = verification.read_text(encoding="utf-8")
    assert fork_source.FORK_PIN in text
    header = re.search(
        r"^HANDSHAKE-APP-VERSION:\s*platterpus\s+(?P<version>\d+\.\d+\S*)",
        text,
        re.MULTILINE,
    )
    assert header is not None, (
        f"{verification.name} declares no parseable app version — the sibling test "
        f"would then be asserting against whatever the regex happened to catch"
    )


def test_the_pin_check_reads_a_closed_round_not_whatever_sorts_last() -> None:
    """The non-triviality floor for the test above.

    Without this, the check could quietly go back to "the newest file of any
    round" and still pass, because today the two happen to agree often enough.
    Assert the *subject* explicitly: the round it examines must be CLOSED, and it
    must not be the round that is currently open.
    """
    handshake = _handshake()
    statuses = handshake.round_status()
    closed = {
        int(m.group(1))
        for line in statuses
        if (m := re.match(r"round-(\d+):.*CLOSED", line))
    }
    open_rounds = {
        int(m.group(1))
        for line in statuses
        if (m := re.match(r"round-(\d+):.*-> OPEN", line))
    }
    assert closed, "expected at least one closed round"
    assert max(closed) not in open_rounds
    # And the constants are two different things, deliberately: the production pin
    # is what a release installs, the test pin is what an open round nominates.
    # If they were ever equal, a round could approve itself.
    assert fork_source.FORK_PIN != fork_source.FORK_TEST_PIN


def test_the_expected_build_tag_is_derived_not_typed() -> None:
    """cyanrip prints ``(<PROJECT_FORK_ID>-g<short sha>)``. Deriving the expected
    tag from the branch and pin means bumping the pin cannot leave a stale
    literal behind that silently accepts the wrong binary."""
    assert fork_source.FORK_EXPECTED_BUILD_TAG == (
        f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_PIN}"
    )


def test_build_and_verify_cannot_be_given_different_builds() -> None:
    """The property the ``ForkTarget`` seam exists for.

    Before it, the build step read ``FORK_PIN`` and the verify step read
    ``FORK_EXPECTED_BUILD_TAG`` — two module constants that agreed only because one
    derived from the other. With two installable builds (a production pin and a
    mid-round test pin) "build X, assert it printed Y" became two independent edits,
    and getting one wrong installs one binary while checking for another.

    Asserted over BOTH targets, not just the current default: a check that only
    exercises the value in force cannot fail when the *other* one is wrong.
    """
    for target in (fork_source.PRODUCTION_TARGET, fork_source.TEST_TARGET):
        commands = fork_source.fork_build_commands(CONTAINER, target)
        build_argv, verify_argv = commands[1], commands[-1]
        assert target.pin in build_argv, f"{target.pin} is not what gets built"
        assert target.build_tag in verify_argv, (
            f"the verify does not check for {target.build_tag} — the build and the "
            f"check are looking at different binaries"
        )
        # And the pair really is distinguishable, so this cannot pass vacuously by
        # both targets happening to be the same commit.
    assert fork_source.PRODUCTION_TARGET.pin != fork_source.TEST_TARGET.pin, (
        "the two targets are the same commit, so the test above proves nothing"
    )


def test_the_wizard_target_is_named_in_the_handshake_record() -> None:
    """Whatever the wizard installs must be a build the record actually names.

    The production pin is checked against the newest *verified* round (above). A
    **test** pin is nominated by the fork, so it is checked against the newest
    *inbound* round — and that check is the thing that catches a stale one. This
    round's test pin moved twice, each time retiring a build the previous lap told
    us to install; `f750890` in particular could hang an `-x` probe with no
    diagnostic at all, which is precisely the failure the hardware session exists
    to observe.
    """
    target = fork_source.WIZARD_TARGET
    if target == fork_source.PRODUCTION_TARGET:
        return  # covered by the verified-round check above
    # `handshake.sort_key`, not a local sort. This test had its own `(round, name)`
    # key and it was the THIRD copy of that ordering in the repo; all three broke when
    # the naming migration mixed `round-7.md` with `round-07-lap-16.md`, because
    # lexically `"round-07-lap-16" < "round-7"`. This one then read the fork's lap-1
    # file as the newest round and reported the test pin as unnamed.
    inbound = sorted(
        (REPO_ROOT / "docs" / "handshake" / "inbound").glob("round-*.md"),
        key=_handshake().sort_key,
    )
    assert inbound, "no inbound files — cannot check a test pin against the record"
    newest = inbound[-1]
    text = newest.read_text(encoding="utf-8")

    # OUR OWN NEWEST LAP COUNTS TOO, but only if it DECLARES the pin in the wire
    # header — not if the sha merely appears somewhere in its prose.
    #
    # **Why this arm exists** (round 7 lap 34). A test pin is the fork's to nominate,
    # which is why the check reads the *inbound* record and why that is the right
    # default. But `beta.8` / `92ceeed` reached us **out of band** — reported by the
    # maintainer, who is the one holding the rig — while both sides' newest laps still
    # named `4a35604`. The record and the machine disagreed, with hardware about to
    # run on the machine.
    #
    # Refusing outright would mean shipping an app that installs a build the rig does
    # not have. Accepting silently would defeat the whole guard. So: we may declare a
    # pin first, and the declaration has to be a `HANDSHAKE-TEST-PIN` line in a lap we
    # actually wrote and sent — which lap 34 is, and which asks them to confirm it in
    # as many words. A sha mentioned in passing still fails, because "the record names
    # it" has to mean *declared*, not *discussed*.
    if target.pin not in text:
        ours = sorted(
            (REPO_ROOT / "docs" / "handshake" / "verified").glob("round-*.md"),
            key=_handshake().sort_key,
        )
        declared = ""
        if ours:
            for line in ours[-1].read_text(encoding="utf-8").splitlines():
                if line.startswith("HANDSHAKE-TEST-PIN:"):
                    declared = line.split(":", 1)[1].strip()
                    break
        assert declared == target.pin, (
            f"{newest.name} does not name test pin {target.pin!r}, and our newest lap "
            f"({ours[-1].name if ours else 'none'}) does not DECLARE it either "
            f"(HANDSHAKE-TEST-PIN reads {declared!r}) — the wizard would build a commit "
            "no side put in the record, which is how a retired pin gets installed for a "
            "hardware session"
        )
    for retired in fork_source.SUPERSEDED_TEST_PINS:
        assert retired != target.pin, f"{retired} is both current and retired"


def test_the_pin_is_a_short_sha_not_a_branch_or_tag() -> None:
    """A branch name here would install whatever is newest, which is the thing
    the pin exists to prevent."""
    assert re.fullmatch(r"[0-9a-f]{7,40}", fork_source.FORK_PIN)


def test_the_clone_url_is_the_fork_over_https() -> None:
    """HTTPS, not SSH: the wizard runs unattended and must not need a key agent."""
    assert fork_source.FORK_REPO_URL.startswith("https://")
    assert "rmccann-hub/cyanrip" in fork_source.FORK_REPO_URL


# --- the plan ---------------------------------------------------------------


def test_the_step_runs_deps_build_install_export_verify_in_that_order() -> None:
    commands = fork_source.fork_build_commands(CONTAINER)
    joined = [" ".join(c) for c in commands]
    assert len(commands) == 5

    assert "dnf install -y" in joined[0]
    assert "ninja -C" in joined[1]
    assert "install -Dm0755" in joined[2]
    assert "distrobox-export --bin" in joined[3]
    assert "-V" in joined[4]


def test_verification_is_last_because_it_checks_what_was_just_installed() -> None:
    """A verify that ran first could only ever confirm the previous state — which
    on a re-run is the very thing being replaced."""
    commands = fork_source.fork_build_commands(CONTAINER)
    assert commands[-1] == fork_source.verify_command(CONTAINER)


def test_the_verify_fails_the_step_on_a_binary_that_is_not_the_pinned_fork() -> None:
    """The command must actually compare against the expected tag. A verify that
    only ran the binary and ignored its output would pass for stock cyanrip."""
    argv = fork_source.verify_command(CONTAINER)
    assert fork_source.WIZARD_TARGET.build_tag in argv
    assert fork_source.FORK_INSTALL_PATH in argv
    script = next(a for a in argv if "banner=" in a)
    assert "exit 1" in script, "the verify script must fail, not merely print"


def test_every_command_goes_through_distrobox_enter() -> None:
    """Critical rule #3: container work is driven only through Distrobox, and
    only in setup. Nothing here may shell out to podman directly."""
    for argv in fork_source.fork_build_commands(CONTAINER):
        assert argv[:4] == ["distrobox", "enter", CONTAINER, "--"]
        assert "podman" not in argv


def test_the_fork_is_installed_where_it_outranks_the_copr_package() -> None:
    """``/usr/local/bin`` precedes ``/usr/bin`` on Fedora's PATH, so the fork wins
    inside the container too — not only via the host export."""
    assert fork_source.FORK_INSTALL_PATH == "/usr/local/bin/cyanrip"


# --- shell safety -----------------------------------------------------------


def test_no_value_is_spliced_into_the_build_script() -> None:
    """Every value arrives as a positional argument, so nothing in a URL, a
    branch name or a path can be reinterpreted by the shell. The same discipline
    the COPR repo stanza uses.
    """
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    for value in (
        fork_source.FORK_REPO_URL,
        fork_source.FORK_BRANCH,
        fork_source.WIZARD_TARGET.pin,
        fork_source.FORK_SOURCE_SUBPATH,
    ):
        assert value not in script, f"{value!r} is spliced into the script body"
        assert value in argv, f"{value!r} must be passed as its own argument"


def test_the_build_script_has_a_label_argument_so_values_are_not_eaten_as_argv0() -> (
    None
):
    """``sh -c SCRIPT NAME ARG1 …`` binds NAME to ``$0``. Without a throwaway
    label the first real value would land in ``$0`` and every ``$1``… would be
    off by one — a silent, total misconfiguration."""
    argv = fork_source.build_command(CONTAINER)
    after_script = argv[argv.index("-c") + 2 :]
    assert after_script[0] == "build-cyanrip-fork"
    assert after_script[1:] == [
        fork_source.FORK_SOURCE_SUBPATH,
        fork_source.FORK_REPO_URL,
        fork_source.FORK_BRANCH,
        fork_source.WIZARD_TARGET.pin,
        # $5 — the build tag the pre-install guard compares against, so a wrong
        # build is refused before `sudo install` and `distrobox-export` make the
        # change irreversible.
        fork_source.WIZARD_TARGET.build_tag,
        # $6 — `meson setup` options for this pin, space-joined; empty for every
        # pin that predates `meson_options.txt` (round 11 §0), which is our
        # current one. Asserted through the target rather than as a literal ""
        # so this test keeps checking the *wiring* after the pin moves.
        " ".join(fork_source.WIZARD_TARGET.meson_options),
    ]


def test_the_build_script_aborts_on_the_first_failure() -> None:
    """Without ``set -e`` a failed clone falls through to "build whatever is
    already in that directory", which installs a stale binary while reporting
    success — the silent-wrong-answer class this project keeps hunting."""
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert script.startswith("set -eu")


def test_the_build_detaches_onto_the_pin_rather_than_trusting_the_branch() -> None:
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert "checkout --force --detach" in script
    # And it fetches before checking out, so a pin newer than a cached clone
    # still resolves.
    assert script.index("fetch") < script.index("checkout --force --detach")


# --- build dependencies -----------------------------------------------------


def test_build_deps_are_requested_as_pkgconfig_provides_not_package_names() -> None:
    """Fedora's ``ffmpeg-free-devel`` and RPM Fusion's ``ffmpeg-devel`` conflict
    and cannot both be named, so the library deps are requested by the
    pkg-config file they provide and dnf resolves whichever package ships it —
    the same trick the cd-paranoia step uses.
    """
    libs = [p for p in fork_source.FORK_BUILD_PACKAGES if p.startswith("pkgconfig(")]
    assert len(libs) >= 9, "floor: expected the fork's full pkg-config dependency set"
    toolchain = [
        p for p in fork_source.FORK_BUILD_PACKAGES if not p.startswith("pkgconfig(")
    ]
    assert set(toolchain) == {"git", "meson", "ninja-build", "gcc"}


@pytest.mark.parametrize(
    "module",
    [
        # Read off the fork's own src/meson.build at the pin — every
        # `dependency('x')` line it declares.
        "libavcodec",
        "libavformat",
        "libswresample",
        "libavfilter",
        "libavutil",
        "libcdio",
        "libcdio_paranoia",
        "libmusicbrainz5",
        "libcurl",
    ],
)
def test_every_meson_dependency_of_the_fork_is_installed(module: str) -> None:
    """A missing devel package makes ``meson setup`` fail with a message about a
    library rather than about a wizard, so this list is the difference between a
    one-click install and a support thread."""
    assert f"pkgconfig({module})" in fork_source.FORK_BUILD_PACKAGES


# --- The `$HOME` defect: paths, expansion, and the guard --------------------


def test_the_source_subpath_carries_no_shell_variable() -> None:
    """REGRESSION (real-user log, 2026-08-04, v0.6.4b2).

    This constant was the literal ``"$HOME/.cache/platterpus/cyanrip-fork"`` with a
    comment claiming the container's shell would expand it. **Parameter expansion
    does not recurse:** the script did ``src="$1"``, so ``$HOME`` stayed 5 literal
    characters and every path became relative to a directory *named* ``$HOME``. The
    user's own log said::

        Source dir: /home/rmccann/$HOME/.cache/platterpus/cyanrip-fork

    The build still succeeded — right commit, right version, 31/31 targets — because
    clone, configure, compile and install all used the same wrong string and agreed
    with each other. The only casualty was meson's ``vcs_tag``, which fell back to
    upstream's literal ``release``, so the binary reported
    ``platterpus-fork-grelease``: a build tag naming no commit.
    """
    assert "$" not in fork_source.FORK_SOURCE_SUBPATH
    assert not fork_source.FORK_SOURCE_SUBPATH.startswith("/"), (
        "the subpath is relative to $HOME by design — the script prefixes it"
    )
    assert not hasattr(fork_source, "FORK_SOURCE_DIR"), (
        "FORK_SOURCE_DIR was the `$HOME`-bearing constant; it must not come back"
    )


def test_no_command_ships_an_unexpanded_variable_to_the_container() -> None:
    """The sweep, not the single case. ANY argv with a `$` is the same defect.

    Checked across the whole plan rather than the two commands known to have had
    it, because the failure mode is invisible when every consumer is wrong the same
    way — which is exactly how it survived.
    """
    for argv in fork_source.fork_build_commands(CONTAINER):
        # The script BODIES legitimately contain `$1`/`$HOME` — that is the fix.
        # It is the *arguments* that must be literal.
        script_idx = argv.index("-c") + 1 if "-c" in argv else -1
        for i, arg in enumerate(argv):
            if i == script_idx:
                continue
            assert "$" not in arg, (
                f"argv element {arg!r} carries an unexpanded shell variable; it will "
                f"arrive at the container literally (full argv: {argv})"
            )


def test_the_build_and_install_scripts_expand_home_at_the_point_of_use() -> None:
    """Both must prefix `$HOME` themselves, and both must agree.

    Fixing only the build would leave the install copying from a path that no
    longer exists — the two were consistent in being wrong, so they have to stay
    consistent in being right.
    """
    build = fork_source.build_command(CONTAINER)
    install = fork_source.install_command(CONTAINER)
    for argv in (build, install):
        script = argv[argv.index("-c") + 1]
        assert 'src="$HOME/$1"' in script, (
            f"script does not expand $HOME at the point of use:\n{script[:200]}"
        )
        assert fork_source.FORK_SOURCE_SUBPATH in argv, (
            "the subpath must arrive as its own argument, never spliced into the body"
        )


@pytest.mark.parametrize(
    "bad",
    [
        "$HOME/.cache/platterpus/cyanrip-fork",  # the actual defect
        "/absolute/path",
        "../escape",
        "a/../../b",
        "has space; rm -rf /",
        "back`tick`",
        "quote'd",
        'double"quote',
        "pipe|it",
        "amp&it",
        "glob*star",
        "",
        "  padded  ",
    ],
)
def test_the_chokepoint_guard_rejects_what_a_shell_would_mangle(bad: str) -> None:
    """CLAUDE.md: validate outputs to dependencies **at the argv chokepoint**, in
    code — not merely stated in a doc. The `$` case is the one that shipped."""
    with pytest.raises(ValueError):
        fork_source.assert_shell_safe_subpath(bad)


def test_the_chokepoint_guard_accepts_the_real_subpath() -> None:
    """The converse — so the guard cannot pass by rejecting everything."""
    assert (
        fork_source.assert_shell_safe_subpath(fork_source.FORK_SOURCE_SUBPATH)
        == fork_source.FORK_SOURCE_SUBPATH
    )


def test_the_build_script_reports_the_paths_it_resolved() -> None:
    """The diagnostics that would have ended this in seconds instead of two rounds.

    The failure was *entirely* visible in a path, and nothing printed the path.
    """
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    for needed in (
        "HOME=$HOME",
        "cwd=$(pwd)",
        "source tree=$src",
        "rev-parse HEAD",
        "status --porcelain",
        "built banner=",
    ):
        assert needed in script, f"the build script never reports {needed!r}"


def test_the_build_script_refuses_a_relative_or_variable_bearing_source_tree() -> None:
    """Belt to the Python guard's braces — the shell checks its own `$src` too.

    Two independent expressions, deliberately: the Python guard protects the value
    we pass, and this protects against a `$HOME` that is itself unset or odd inside
    the container, which Python cannot see.
    """
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert "is not an absolute path" in script
    assert "unexpanded variable" in script


def test_the_verify_error_names_the_banner_it_ACTUALLY_saw() -> None:
    """The single missing string that cost two sessions.

    The old message said only "does not identify as the pinned fork build ($2)" —
    what we EXPECTED. The observed banner was printed one line earlier on stdout,
    and `HostSetup._run_commands` keeps only the LAST line for the UI, so the one
    fact that mattered was discarded exactly when it mattered. The answer was
    `platterpus-fork-grelease` — not a wrong commit, a tag naming *no* commit.
    """
    argv = fork_source.verify_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert "reports" in script and "$banner" in script, (
        f"the verify error does not quote the observed banner:\n{script}"
    )
    assert "grelease" in script, (
        "the vcs_tag-fallback case has a specific cause and deserves its own "
        "sentence — a user should not need to know meson internals to act on it"
    )


# --- the release gate's floor ------------------------------------------------


def test_an_in_flight_round_with_no_committed_files_is_still_OPEN(
    tmp_path: Path,
) -> None:
    """The state that let four releases out during round 8.

    Round 8 ran for seven laps with its files uncommitted. `round-*.md` found
    nothing for it, so the gate reported every *filed* round CLOSED and allowed
    a release — and it was not wrong about anything it could see. The
    empty-record branch did not fire either: it only triggers when there are **no**
    rounds at all, and rounds 1-7 were sitting right there.

    So the defect is the empty-record one arriving a level up — an in-flight round
    with no files is indistinguishable from no round — and `CURRENT_ROUND` is the
    floor that closes it. This test builds exactly that world: every round below
    the current one filed and CLOSED, the current one absent.
    """
    handshake = _handshake()
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
    for number in range(1, handshake.CURRENT_ROUND):
        for name in ("outbound", "inbound", "verified"):
            sender = "cyanrip" if name == "inbound" else "platterpus"
            (tmp_path / name / f"round-{number}.md").write_text(
                f"HANDSHAKE-ROUND: {number}\n"
                "HANDSHAKE-LAP: 1\n"
                f"HANDSHAKE-FROM: {sender}\n"
                "HANDSHAKE-VERDICT: GO\n\n**GO on ddf7ac3**\n",
                encoding="utf-8",
            )

    lines = handshake.round_status(tmp_path, floor=handshake.CURRENT_ROUND)
    current = [ln for ln in lines if ln.startswith(f"round-{handshake.CURRENT_ROUND}:")]
    assert current, (
        f"round {handshake.CURRENT_ROUND} vanished from the status report because "
        "it has no files — which is the entire bug"
    )
    assert "OPEN" in current[0], current[0]
    assert any("do not release" in ln for ln in lines), lines


def test_the_floor_does_not_make_every_round_open(tmp_path: Path) -> None:
    """The companion question: can this be satisfied by the wrong thing?

    A floor that reported OPEN unconditionally would pass the test above while
    making the gate useless — every round open forever, and the first person to
    need a release would delete the check. Rounds below the current one must
    still be able to close.
    """
    handshake = _handshake()
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        sender = "cyanrip" if name == "inbound" else "platterpus"
        (tmp_path / name / "round-1.md").write_text(
            "HANDSHAKE-ROUND: 1\nHANDSHAKE-LAP: 1\n"
            f"HANDSHAKE-FROM: {sender}\nHANDSHAKE-VERDICT: GO\n\n**GO on ddf7ac3**\n",
            encoding="utf-8",
        )
    lines = handshake.round_status(tmp_path)
    assert any(ln.startswith("round-1:") and "CLOSED" in ln for ln in lines), lines


def test_the_floor_tracks_the_newest_round_on_disk() -> None:
    """`CURRENT_ROUND` is maintained by hand, so it can go stale. Staleness in the
    safe direction (too low relative to reality) is the dangerous one — that is
    the invisible-round bug returning — so pin it against the record: the floor
    must be at least the highest round anyone has filed a file for."""
    handshake = _handshake()
    base = REPO_ROOT / "docs" / "handshake"
    filed = {
        number
        for name in ("outbound", "inbound", "verified")
        for path in (base / name).glob("round-*.md")
        if (number := handshake.round_number(path)) is not None
    }
    assert filed, "no handshake files at all — this test is measuring nothing"
    assert handshake.CURRENT_ROUND >= max(filed), (
        f"CURRENT_ROUND is {handshake.CURRENT_ROUND} but round {max(filed)} has "
        "files on disk; bump it or the newer round is invisible to the gate"
    )


class TestInstallingTheApprovedPinByName:
    """`--install-ripper <approved pin>` must not call it unapproved.

    **Measured on the rig, 2026-08-14.** The operator ran
    ``--install-ripper ddf7ac3`` — naming the pin a closed round approved — and
    the installer answered:

        cyanrip build: ddf7ac3 — ... NOT a pinned build, and no round has
        approved it. Every rip with this installed reports
        ripper_handshake_approval: unapproved, which is the correct answer

        NOTE: this is not the handshake-approved build (ddf7ac3).

    A sentence of the form *"this is not X (X)"*. Ninety seconds later
    ``--rig-check`` reported ``OK ripper/handshake approved`` for the very same
    binary, because approval is decided by the installed build tag and not by how
    the install was requested.

    Two surfaces disagreeing about one fact is the failure `CLAUDE.md` names by
    name. The cause was a whole-object comparison — ``target_for_commit`` builds a
    ForkTarget whose ``version`` and ``why`` differ by construction, so
    ``target != PRODUCTION_TARGET`` was true even when the pins matched. Only the
    commit may decide approval.
    """

    def test_the_approved_pin_is_not_described_as_unapproved(self) -> None:
        target = fork_source.target_for_commit(fork_source.PRODUCTION_TARGET.pin)
        assert "no round has approved it" not in target.why, (
            "installing the approved pin by name claims no round approved it — "
            f"this is the 2026-08-14 rig contradiction. why={target.why!r}"
        )
        assert "unapproved" not in target.why, (
            "the install predicts rips will report unapproved; --rig-check "
            f"reports approved for this exact build. why={target.why!r}"
        )
        assert "approved" in target.why

    def test_a_genuinely_different_commit_is_still_called_unapproved(self) -> None:
        """The non-triviality floor. A fix that called *everything* approved
        would pass the test above and destroy the warning that matters."""
        target = fork_source.target_for_commit("0badc0de")
        assert "NOT the approved pin" in target.why
        assert "unapproved" in target.why

    def test_same_commit_treats_a_short_sha_as_the_full_one(self) -> None:
        """Git abbreviations are prefixes, so both spellings are one commit."""
        short = fork_source.PRODUCTION_TARGET.pin
        assert fork_source.same_commit(short, short)
        assert fork_source.same_commit(short, short + "9f2c1ab4d5e6")
        assert fork_source.same_commit(short.upper(), short)

    def test_same_commit_refuses_the_cases_that_would_approve_by_accident(
        self,
    ) -> None:
        """An empty pin must never match: returning True there would silently
        approve a build nobody named."""
        assert not fork_source.same_commit("", fork_source.PRODUCTION_TARGET.pin)
        assert not fork_source.same_commit(fork_source.PRODUCTION_TARGET.pin, "")
        assert not fork_source.same_commit("", "")
        assert not fork_source.same_commit("0badc0de", "ddf7ac3")


class TestTheBuildRefusesBeforeInstalling:
    """The build step must reject a wrong binary BEFORE anything irreversible.

    The step order is build → install → export → verify. `sudo install` writes
    `/usr/local/bin/cyanrip` and `distrobox-export` rewrites the host wrapper;
    both are irreversible and both used to run *before* the only build-tag
    check. A failing verify therefore reported the problem accurately and left
    the wrong ripper on the ripping path with no rollback — the guard meant to
    be the last word running after the point of no return.

    These tests EXECUTE the shipped shell rather than pattern-match it. A shell
    guard that merely looks correct is a known failure mode here: the fork's own
    `sed` once produced non-compiling C while build output was suppressed, so a
    stale binary ran the test and passed.
    """

    #: The guard, lifted verbatim out of the shipped script so the test cannot
    #: drift from what we actually run.
    MARKER = "# --- REFUSE HERE, BEFORE ANYTHING IS INSTALLED"

    def _guard_fragment(self) -> str:
        script = fork_source._BUILD_SCRIPT
        assert self.MARKER in script, (
            "the pre-install guard is gone from the build script — the binary "
            "would be installed before its build tag is ever checked"
        )
        return script[script.index(self.MARKER) :]

    def _run(self, banner: str, expected_tag: str) -> subprocess.CompletedProcess[str]:
        """Run the real guard with a given banner, as `sh` would."""
        fragment = f"_banner={shlex.quote(banner)}\n" + self._guard_fragment()
        return subprocess.run(
            ["sh", "-c", fragment, "guard-test", "", "", "", "somepin", expected_tag],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_a_matching_banner_is_accepted(self) -> None:
        done = self._run(
            "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)",
            "platterpus-fork-gddf7ac3",
        )
        assert done.returncode == 0, f"correct build refused: {done.stderr}"
        assert "safe to install" in done.stdout

    def test_a_wrong_banner_is_refused_and_says_nothing_changed(self) -> None:
        done = self._run(
            "cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)",
            "platterpus-fork-gddf7ac3",
        )
        assert done.returncode != 0, "a mismatched build tag was allowed through"
        # NAME WHAT WE GOT, not only what we wanted.
        assert "g2ce8993" in done.stderr, "the refusal does not quote the actual banner"
        assert "gddf7ac3" in done.stderr, "the refusal does not name what was expected"
        assert "UNCHANGED" in done.stderr, (
            "the refusal does not tell the operator the previous ripper is still "
            "in place — which is the whole point of refusing early"
        )

    def test_a_binary_that_answers_no_version_flag_is_refused(self) -> None:
        done = self._run("", "platterpus-fork-gddf7ac3")
        assert done.returncode != 0
        assert "none of: -V --version" in done.stderr

    def test_the_release_fallback_tag_is_named_specifically(self) -> None:
        """`vcs_tag` falling back to its literal default is the v0.6.4b2 symptom
        and deserves its own sentence, not a generic mismatch."""
        # The fork's build tag is `platterpus-fork-g<vcs_tag>`, so when meson's
        # vcs_tag falls back to its literal default the tag reads
        # `platterpus-fork-grelease` — which is why the pattern keys on `-grelease`
        # rather than on the bare word.
        done = self._run(
            "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-grelease)",
            "platterpus-fork-gddf7ac3",
        )
        assert done.returncode != 0
        assert "names no commit at all" in done.stderr

    def test_the_guard_runs_before_the_install_script_exists(self) -> None:
        """Structural: the check lives in the BUILD script, and the install and
        export scripts are separate later steps. If the guard ever moves into
        the verify script, this fails — which is the regression."""
        assert self.MARKER in fork_source._BUILD_SCRIPT

        def _code_only(script: str) -> str:
            # Comments mention `sudo install` to explain WHY the guard is here,
            # so match on executable lines only. (The first version of this test
            # matched its own explanatory comment and failed — a check satisfied
            # by the wrong thing, caught immediately because it was run.)
            return "\n".join(
                line
                for line in script.splitlines()
                if not line.lstrip().startswith("#")
            )

        assert "sudo install" not in _code_only(fork_source._BUILD_SCRIPT), (
            "the build script now installs, so 'refuse before installing' is "
            "no longer a meaningful ordering claim"
        )
        assert "sudo install" in _code_only(fork_source._INSTALL_SCRIPT)

    def test_the_expected_tag_is_passed_from_the_target_not_rebuilt_in_shell(
        self,
    ) -> None:
        """One object owns the pin→tag relationship. A shell reconstruction from
        $3 and $4 would be a second spelling, free to drift."""
        target = fork_source.PRODUCTION_TARGET
        cmd = fork_source.build_command("ripping", target)
        # $6 (the per-pin meson options) now trails the tag, so index off the end
        # by name rather than assuming the tag is last — the reason this test
        # broke when the argument was added, and the reason it says so here.
        assert cmd[-1] == " ".join(target.meson_options)
        assert cmd[-2] == target.build_tag, (
            f"the build tag is not where it should be: {cmd[-4:]}"
        )
        assert cmd[-3] == target.pin

    def test_every_shipped_script_is_valid_shell(self) -> None:
        """`sh -n` parses without executing. Cheap, and it catches the case this
        project keeps hitting: shell that reads correctly and does not run."""
        for name in ("_BUILD_SCRIPT", "_INSTALL_SCRIPT", "_VERIFY_SCRIPT"):
            script = getattr(fork_source, name)
            done = subprocess.run(
                ["sh", "-n"], input=script, capture_output=True, text=True, timeout=30
            )
            assert done.returncode == 0, f"{name} is not valid shell: {done.stderr}"


class TestTheRipperBuildMenu:
    """`--install-ripper list` must name the build TAG, not only a role.

    A menu offering "the newest beta" without naming
    `platterpus-fork-g<sha>` asks an operator to choose a build they cannot
    later identify in a log. That is the confusion that cost a rig session's
    evidence on 2026-08-13, when a rip turned out to be on `g2ce8993` while the
    round under review was `ddf7ac3` — every artifact looked fine and answered a
    question nobody had asked.
    """

    def test_every_choice_carries_its_build_tag(self) -> None:
        choices = fork_source.ripper_choices()
        assert choices, "the menu is empty"
        for choice in choices:
            assert choice.build_tag.startswith(fork_source.FORK_BRANCH + "-g"), (
                f"{choice.pin} has no usable build tag: {choice.build_tag!r}"
            )
            assert choice.pin in choice.build_tag
            assert choice.build_tag in choice.label, (
                f"the menu line hides the tag: {choice.label!r}"
            )

    def test_the_approved_build_leads_and_is_marked_approved(self) -> None:
        """Ordering is by trust, not by date. For the ripper the newest build is
        the *least* checked one, which inverts the app's own 'newest wins'."""
        choices = fork_source.ripper_choices()
        assert choices[0].is_approved, "the approved build is not first"
        assert choices[0].pin == fork_source.PRODUCTION_TARGET.pin
        assert choices[0].kind == "approved"

    def test_an_unapproved_choice_is_visibly_marked(self) -> None:
        """Non-triviality floor: a menu that marked everything approved would
        pass the test above and destroy the distinction it exists for."""
        unapproved = [c for c in fork_source.ripper_choices() if not c.is_approved]
        assert unapproved, (
            "no unapproved build in the menu — either the test pin has been "
            "promoted (fine, drop this assertion then) or the flag is stuck True"
        )
        for choice in unapproved:
            assert "⚠" in choice.label and "✓" not in choice.label

    def test_a_duplicate_pin_is_listed_once(self) -> None:
        """When a round closes, the test pin is promoted and the two constants
        coincide. One build shown twice under two names reads as two options."""
        pins = [c.pin for c in fork_source.ripper_choices()]
        assert len(pins) == len(set(pins)), f"a build is listed twice: {pins}"

    def test_the_word_list_cannot_collide_with_a_commit(self) -> None:
        """`list` is a literal in the same slot as a COMMIT. Git requires at
        least 4 hex characters for an abbreviation, and 'list' is not hex, so
        the two can never be confused."""
        assert not all(ch in "0123456789abcdef" for ch in "list")


# --- Round 11 §0: the build flag is per-pin, and the default under-claims ---


def test_our_production_pin_gets_no_meson_options() -> None:
    """The measured trap, pinned as a test.

    Round 11 §0: `meson_options.txt` is **absent** at `ddf7ac3`, and meson fails the
    *entire* configure on an unknown `-D` — not just the option:

        meson.build:1:0: ERROR: Unknown options: "declare_released"

    Verified independently against the fork's tree rather than taken from their lap:
    `git ls-tree ddf7ac3 -- meson_options.txt` is empty, and the same file at
    `c4d1a00` declares `option('declare_released', ... value: false)`.

    So a constant `-Ddeclare_released=true` in our build step would make our *own
    current pin* unbuildable, and would kill the downgrade path to the one build with
    rig evidence behind it. This asserts the default is the safe one.
    """
    # **THE TRIPWIRE FIRED WHEN THE PIN ROLLED TO `d9c058c`, AND THE ANSWER
    # CHANGED — which is exactly what it is for.** Re-checked against the fork's
    # tree rather than assumed: `meson_options.txt` at `d9c058c` is **present**,
    # 973 bytes, and declares `declare_released`. So the old reason for the empty
    # default — *"the pin cannot accept the option and meson fails the entire
    # configure on an unknown -D"* — no longer holds.
    #
    # The default stays empty for a BETTER reason, and it is a provenance one.
    # Their own comment on that option says it is *"a CLAIM, not a measurement"*
    # that the build is a published release. **We build from source, in a
    # container, on the operator's machine — our binary is not their published
    # release artifact even when it is built from the released commit.** Passing
    # `-Ddeclare_released=true` would stamp a claim we are not entitled to make
    # into an archival log. Declining is the honest default.
    #
    # Keyed on the CURRENT production pin so the next roll asks the question again.
    assert fork_source.PRODUCTION_TARGET.pin == fork_source.FORK_PIN
    assert fork_source.PRODUCTION_TARGET.pin == "d9c058c", (
        "the pin moved — re-check meson_options.txt at the new pin, and re-ask "
        "whether we are entitled to any option it declares. Presence is not "
        "permission: `declare_released` is a claim about provenance, and a build "
        "we compiled is not the fork's published artifact."
    )
    assert fork_source.PRODUCTION_TARGET.meson_options == ()


def test_the_build_argv_carries_the_pins_options_and_nothing_else() -> None:
    """The options reach the container as one positional argument, or as empty."""
    argv = fork_source.build_command("ripping")
    assert argv[-1] == "", "our current pin must configure with no -D options"

    with_option = fork_source.ForkTarget(
        pin="c4d1a00",
        version="0.9.4-rc1+platterpus.6",
        why="round 11's published release",
        meson_options=("-Ddeclare_released=true",),
    )
    assert fork_source.build_command("ripping", with_option)[-1] == (
        "-Ddeclare_released=true"
    )


def test_the_build_script_never_interpolates_a_command_string() -> None:
    """The security boundary, asserted on the script text itself.

    Round 11 §J1 asked us to take the build command from their manifest. We take the
    *options* and keep our own command, because executing a string from a remote JSON
    document — on a path whose later steps run `sudo install` — hands the machine to
    whoever can write that file.

    So the script must reference `$6` only as `meson setup`'s options, and must never
    `eval` it or run it as a command in its own right.
    """
    script = fork_source._BUILD_SCRIPT
    assert "meson_opts" in script, "the options parameter vanished from the script"
    for forbidden in (
        "eval ",
        '$meson_opts "$@"',
        'sh -c "$meson_opts',
        "`$meson_opts`",
    ):
        assert forbidden not in script, (
            f"the build script may execute the manifest's text ({forbidden!r})"
        )
    # It is used exactly where it should be: as arguments to `meson setup`.
    assert script.count("$meson_opts") == 2, (
        "expected the options in both the --wipe and the fresh-configure branch"
    )


# -----------------------------------------------------------------------------
# "Is a handshake round open?" — ONE predicate, and every surface delegates
# -----------------------------------------------------------------------------
# Three surfaces answered this question with three implementations, and two of
# them were wrong inside the same hour on 2026-08-27, hours after round 14 closed:
#
#   * `uiscript.runner._pin_role_phrase()` — computed it itself. Correct, and it
#     was the third implementation, added because the second was wrong.
#   * `fork_source.UNDER_REVIEW_TARGET.why` — a hard-coded sentence reading
#     "round 14 is the round that would [approve], and it is open". Stale.
#   * the acceptance script's wrong-ripper FAIL — a hard-coded sentence saying
#     the installed build was not "the build the open handshake round is
#     reviewing". Stale, and it is the one an operator reads at 2am.
#
# The last one is why this matters rather than being a wording nit: it told an
# operator who had installed the fork's *newer* release that they had the wrong
# build for a round that was not running. Every word deliberate, the sentence
# false, and false in the direction that says you are behind when you are ahead.
#
# These test the RELATION, which is a property no test of a single surface can
# express (`CLAUDE.md`: *"do two surfaces answer this question, and do they use
# the same key?"*).


class TestTheRoundStatePredicate:
    def test_the_predicate_is_derived_from_the_pins_not_from_a_remembered_flag(
        self,
    ) -> None:
        """A flag someone must clear when a round closes is a flag that stays set.

        The two pins already carry the fact: a round is reviewing something
        exactly when `PIN_UNDER_REVIEW` names a build other than the approved
        one, because closing a round *is* the act of making them the same.
        """
        expected = not fork_source.same_commit(
            fork_source.PIN_UNDER_REVIEW, fork_source.FORK_PIN
        )
        assert fork_source.a_round_is_reviewing_a_build() is expected

    def test_the_phrase_and_the_predicate_cannot_disagree(self) -> None:
        """Both directions, so neither branch can rot unnoticed.

        Asserted as an if-and-only-if rather than one implication: a phrase that
        says "open" while the predicate says closed and one that says "closed"
        while the predicate says open are both this defect.
        """
        phrase = fork_source.pin_under_review_role()
        says_open = "open handshake round is reviewing" in phrase
        says_closed = "no handshake round is open" in phrase
        assert says_open != says_closed, (
            f"the phrase must say exactly one of the two things: {phrase!r}"
        )
        assert says_open is fork_source.a_round_is_reviewing_a_build(), (
            f"the phrase and the predicate disagree: predicate="
            f"{fork_source.a_round_is_reviewing_a_build()}, phrase={phrase!r}"
        )

    def test_the_phrase_always_names_the_pin_it_is_about(self) -> None:
        """A standing claim with no subject is the shape that misled twice.

        "the build the open handshake round is reviewing" does not say *which*
        build, so a reader cannot check it against what they installed.
        """
        assert fork_source.PIN_UNDER_REVIEW in fork_source.pin_under_review_role()

    def test_the_install_menus_reason_delegates_rather_than_restating(self) -> None:
        """`UNDER_REVIEW_TARGET.why` is text an operator reads at install time.

        Asserted as a substring relation, not by reading the source: the claim is
        that the two cannot diverge, and a source check would pass against a
        second copy that happened to match today.
        """
        assert (
            fork_source._pin_under_review_role_clause()
            in fork_source.UNDER_REVIEW_TARGET.why
        ), (
            "UNDER_REVIEW_TARGET.why no longer contains the derived clause, so it "
            f"is carrying its own sentence again: {fork_source.UNDER_REVIEW_TARGET.why!r}"
        )
        assert "round 14" not in fork_source.UNDER_REVIEW_TARGET.why, (
            "a hard-coded round NUMBER is the stale-sentence defect returning: it "
            "is correct only until the next round opens"
        )

    def test_the_script_runners_phrase_is_the_same_function_not_a_copy(self) -> None:
        """The surface that produced the 2am message.

        Byte-identical output is the assertion, because "equivalent logic" is
        what the three implementations each believed they had.
        """
        from platterpus.uiscript import runner

        assert runner._pin_role_phrase() == fork_source.pin_under_review_role()

    def test_the_predicate_reports_OPEN_for_a_pin_that_is_not_the_approved_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both branches exercised, because today only one of them is reachable.

        With round 14 closed the pins coincide, so every assertion above runs
        against the "closed" branch only — and a branch nothing runs is a branch
        nobody has run. This drives the other one.
        """
        monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "0000000")
        assert fork_source.a_round_is_reviewing_a_build() is True
        phrase = fork_source.pin_under_review_role()
        assert "open handshake round is reviewing" in phrase, phrase
        assert "0000000" in phrase, phrase
        assert "no handshake round is open" not in phrase, phrase


#: Declarative assertions that a round IS OPEN. A CONDITIONAL phrasing —
#: "during an open round", "while a round is open" — states when something holds
#: and is correct; `rig_check.py` has one. So the lookbehinds are load-bearing:
#: without them the sweep would demand a rewrite of a right string, and a false
#: positive is how a sweep acquires an allowlist and stops meaning anything.
_ROUND_IS_OPEN_CLAIM: re.Pattern[str] = re.compile(
    # Shape 1: "the round is open" / "the open handshake round is reviewing".
    r"(?<!\bduring an )(?<!\bwhile )"
    r"the (open )?(handshake )?round is (open|reviewing)"
    r"|the open handshake round is reviewing"
    r"|round is open and no round has approved"
    # Shape 2: a literal round NUMBER with a present-tense claim about its
    # state. This is the one `UNDER_REVIEW_TARGET.why` used — "round 14 is the
    # round that would [approve], and it is open" — and it needs its own branch
    # because it never contains the phrase from shape 1.
    #
    # Scoped to PRESENT TENSE on purpose. `round 14 approved`, `round 7 lap 10
    # H1`, `round 12 §D5` are historical PROVENANCE citations: they name a past
    # round as the source of a fact, they are correct, and there are 14 of them
    # in the package. A blanket ban on a literal round number would flag every
    # one, and a sweep that needs a 14-entry allowlist enforces nothing.
    r"|round \d+ is (the round|open|reviewing|currently|still)"
)


def _logical_text(source: str) -> str:
    """`source` with comments dropped and split string literals rejoined.

    **Why rejoining matters, measured.** The first version of this sweep matched
    line by line and MISSED the very string it was written for, because
    `ruff format` had split it:

        f"the installed cyanrip is NOT {expected}, the build the open "
        f"handshake round is reviewing. Every later section would be ..."

    Neither line contains the phrase; the string does. That is the same
    formatter-reflow hazard `CLAUDE.md` records for revert anchors, arriving in a
    detector instead of a patch — and a sweep defeated by an automatic reformat is
    a sweep that goes quiet without anyone touching the string.

    Comments are dropped because a comment is not what a user reads, and because
    the comments explaining this very defect would otherwise trip it. That has
    already happened once in this session.
    """
    kept: list[str] = []
    for line in source.splitlines():
        kept.append("" if line.strip().startswith("#") else line)
    text = "\n".join(kept)
    # Collapse implicit concatenation: a closing quote, whitespace (possibly a
    # newline and an `f` prefix), then an opening quote. Repeat to catch chains.
    joiner = re.compile(r"""(['"])\s*(?:[frbu]{0,2})(['"])""")
    for _ in range(8):
        collapsed = joiner.sub("", text)
        if collapsed == text:
            break
        text = collapsed
    return text


def test_no_module_asserts_a_handshake_round_IS_OPEN_in_a_user_facing_string() -> None:
    """The sweep, because fixing this at three sites is not fixing it.

    Round 14 closed on 2026-08-27 and **three** separate user-facing strings said
    a round was open. Two were wrong within the hour:

    * the acceptance script's wrong-ripper FAIL — the one an operator reads at 2am;
    * `fork_source.UNDER_REVIEW_TARGET.why` — install-time text with a hard-coded
      round *number* in it;
    * `app.py`'s `--install-ripper` note — *"the round is open and no round has
      approved a test pin"*, printed unconditionally for any non-approved build,
      and **between rounds is exactly when an operator installs one by hand**.

    `docs/testing.md` §5.o: enforce a rule across the codebase, not at the place it
    was learned. This is that enforcement.

    Every string that legitimately needs to say a round is open must route
    through :func:`fork_source.pin_under_review_role`, which decides it from the
    pins rather than from what somebody typed.
    """
    src_root = Path(fork_source.__file__).resolve().parents[1]
    modules = sorted(src_root.rglob("*.py"))
    assert len(modules) >= 120, (
        f"only {len(modules)} modules under {src_root} — the sweep is not reaching "
        "the package, so a clean result means nothing"
    )

    offenders: list[str] = []
    for path in modules:
        # The predicate's own definition is the one place the sentence belongs.
        if path.name == "fork_source.py":
            continue
        text = _logical_text(path.read_text(encoding="utf-8"))
        for match in _ROUND_IS_OPEN_CLAIM.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            offenders.append(
                f"{path.relative_to(src_root.parent)}:~{line_no}: "
                f"...{text[max(0, match.start() - 40) : match.end() + 40]}..."
            )

    assert not offenders, (
        "these assert that a handshake round IS OPEN, which is false between "
        "rounds — and between rounds is when an operator most often reads them:\n  "
        + "\n  ".join(offenders)
        + "\n\nCall fork_source.pin_under_review_role() (or "
        "a_round_is_reviewing_a_build()) instead of writing the sentence. A "
        "CONDITIONAL phrasing — 'during an open round', 'while a round is open' — "
        "is fine and is not matched."
    )


def test_the_round_claim_sweep_would_catch_all_three_strings_that_shipped() -> None:
    """Non-triviality, against the exact text of each of the three sites.

    A sweep that caught only one spelling would report one problem where there
    were three, which `CLAUDE.md` calls worse than failing. Case 1 is given in the
    **reflowed** form it actually had in the file, which is the form the first
    version of this sweep could not see — so this also pins `_logical_text`.

    The last two cases must NOT match: without them the sweep would demand a
    rewrite of correct strings.
    """
    shipped_and_wrong = [
        # Case 1, exactly as `ruff format` had left it: split mid-phrase.
        'f"the installed cyanrip is NOT {expected}, the build the open "\n'
        '            f"handshake round is reviewing. Every later section would be "',
        # Case 2: UNDER_REVIEW_TARGET.why.
        '"pin, but no round has approved it: round 14 is the round that would, "\n'
        '        "and it is open. A rip with this installed reports `unapproved`"',
        # Case 3: app.py's install note.
        'f"      round is open and no round has approved a test pin.\\n"',
    ]
    for i, text in enumerate(shipped_and_wrong, 1):
        assert _ROUND_IS_OPEN_CLAIM.search(_logical_text(text)), (
            f"the sweep would MISS shipped case {i}: {text!r}"
        )

    correct_and_conditional = [
        'f"pin is expected to differ during an open round.",',
        '"no release, no pin switch while a round is open"',
        # Historical PROVENANCE citations — past tense, naming a past round as
        # the source of a fact. There are 14 of these in the package and every
        # one is correct; flagging them would force an allowlist, and a sweep
        # with a list of excuses enforces nothing.
        '"the build round 14 approved, GO on both sides"',
        '"root-caused by the cyanrip fork in round 14 lap 7 B2"',
        '"a bound, or an explicit unknown (round 14 T3)"',
    ]
    for text in correct_and_conditional:
        assert not _ROUND_IS_OPEN_CLAIM.search(_logical_text(text)), (
            f"the sweep FALSELY flags a correct conditional: {text!r}"
        )


def test_installing_the_approved_pin_by_name_names_its_KNOWN_banner() -> None:
    """`--install-ripper d9c058c` printed a false sentence about our own pin.

    The preamble reads `target.expectation`, and for a hand-supplied commit that
    used to be *"the version string is not predictable for a commit we do not
    pin"* — printed for the commit we DO pin, in the preamble of the exact command
    an operator is told to run.

    The pairing is measured, not inferred: `FORK_EXPECTED_VERSION` with `FORK_PIN`
    is what both projects declared at column 0 in round 14 laps 17, 18 and 19. So
    the assertion is against `FORK_EXPECTED_BANNER` rather than a typed string —
    one source, and it cannot drift when the pin next moves.
    """
    target = fork_source.target_for_commit(fork_source.FORK_PIN)
    assert target.version_known is True, (
        "the approved pin's version is a fact this repository holds; reporting it "
        "as unknown makes `expectation` claim we do not pin our own pin"
    )
    assert target.expectation == fork_source.FORK_EXPECTED_BANNER, (
        f"expectation is {target.expectation!r}, not the banner our record pairs "
        f"with the pin ({fork_source.FORK_EXPECTED_BANNER!r})"
    )
    assert "we do not pin" not in target.expectation, target.expectation


def test_an_arbitrary_commit_still_declares_its_version_unknown() -> None:
    """The other half, and the half that must NOT be relaxed.

    An operator-supplied commit's `meson.build` is genuinely unknown to us, and
    inventing a number would put an unmeasured value into a banner comparison.
    Both branches asserted, because a fix that made the first one honest by making
    the second one dishonest would pass the test above.
    """
    target = fork_source.target_for_commit("0123abc")
    assert target.version_known is False
    assert "not predictable" in target.expectation, target.expectation
    assert "platterpus-fork-g0123abc" in target.expectation, (
        "the build TAG is still verified for an arbitrary commit — that is what "
        "makes the honest 'version unknown' safe rather than a hole"
    )
