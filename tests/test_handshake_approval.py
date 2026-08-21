"""Unit tests for the rip-time handshake verification (`handshake_approval`).

**Why this file exists.** The module was written to satisfy a direct maintainer
instruction — *"verify at the time of rip as well so we can confirm"* — and shipped
with **no test of its own**; the only thing touching it was
`test_report_types_completeness`, which asserts the report *carries* the keys, not
that the verdict in them is right. A check nobody checks is the shape of thing this
project keeps finding: it would have passed a release gate while answering every
question wrong.

The properties under test, in the order they matter:

1. **Tri-state, and `not_determined` is never a pass.** An absent banner and an
   unrecognised build tag are *absence of evidence*, and the whole point of the
   module is that they do not render as the negative.
2. **The approved build is the only `approved`.** Not "a fork build", not "the right
   version number" — the exact build tag a closed round named.
3. **A recognised-but-unapproved build says why it is here.** The test pin during a
   hardware session is *expected*; a verdict that cannot say so is the "accurate and
   useless" dependency-dialog failure again.
4. **Never raises.** It parses a dependency's output.
5. **The verdict off a *parsed* log matches the verdict off the banner** — added after
   the fork found (round 7 lap 10, H2) that it did not. See
   `test_the_real_fork_log_reads_unapproved_not_not_determined`, which reads the
   committed artifact rather than a fixture, because the fixture in this very file
   was what hid the bug: it fed `log_creator` a *whole* banner, a shape the parser
   never produces.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus import __version__
from platterpus import handshake_approval as ha
from platterpus.deps import fork_source
from platterpus.parsers.cyanrip_log import parse_cyanrip_log

APPROVED_BANNER = fork_source.FORK_EXPECTED_BANNER

_REPO = Path(__file__).resolve().parent.parent


def test_the_approved_build_tag_is_the_only_approval() -> None:
    """The exact build a closed round named, and nothing else, reads `approved`."""
    approval = ha.approve_ripper(APPROVED_BANNER)
    assert approval.verdict == ha.APPROVED
    assert approval.is_approved
    # The pair, both halves, in the sentence a support question would quote.
    assert fork_source.FORK_EXPECTED_BUILD_TAG in approval.detail
    assert ha.APPROVED_FOR_PLATTERPUS_VERSION in approval.detail
    assert str(ha.APPROVED_BY_ROUND) in approval.detail


@pytest.mark.parametrize(
    "banner",
    [
        None,
        "",
        "   ",
        # Recognisably cyanrip, but with no parenthetical build tag at all — which is
        # what stock upstream prints. NOT unapproved: we cannot tell.
        "cyanrip 0.9.3",
        "cyanrip 0.9.4-rc1",
    ],
)
def test_absent_or_untagged_banner_is_not_determined_and_not_a_pass(
    banner: str | None,
) -> None:
    """Absence of evidence is its own verdict, and it never counts as approval."""
    approval = ha.approve_ripper(banner)
    assert approval.verdict == ha.NOT_DETERMINED
    assert not approval.is_approved, "not_determined must never satisfy is_approved"
    assert not approval.verdict == ha.UNAPPROVED, (
        "an untagged build is absence of evidence, not evidence of an unapproved build"
    )
    assert approval.detail.strip(), "a verdict with no explanation is the useless kind"


def test_a_different_recognisable_build_is_unapproved() -> None:
    """The real negative: a build tag we can read that is not the approved one."""
    approval = ha.approve_ripper("cyanrip 0.9.4-rc1 (platterpus-fork-gdeadbee)")
    assert approval.verdict == ha.UNAPPROVED
    assert not approval.is_approved
    assert "deadbee" in approval.detail
    assert fork_source.FORK_EXPECTED_BUILD_TAG in approval.detail, (
        "the negative must name what WAS expected, or the user cannot act on it"
    )


def test_the_current_test_pin_is_unapproved_but_explains_itself() -> None:
    """The round-7 test pin is what the hardware session installs on purpose.

    It is still `unapproved` — no round has approved a test pin, and softening that
    would discard the check. What it must not do is read as a fault.
    """
    banner = (
        f"cyanrip {fork_source.FORK_TEST_VERSION} ({fork_source.FORK_TEST_BUILD_TAG})"
    )
    approval = ha.approve_ripper(banner)

    assert approval.verdict == ha.UNAPPROVED, "a test pin is not a release"
    assert not approval.is_approved
    detail = approval.detail
    assert "test pin" in detail.lower(), (
        "the message must say the build is a nominated test pin, or an expected "
        "state during a hardware session reads as a broken install"
    )
    assert fork_source.FORK_TEST_PIN in detail
    assert str(fork_source.FORK_TEST_PIN_ROUND) in detail


def test_a_retired_test_pin_says_it_is_retired_and_names_the_current_one() -> None:
    """Evidence from a withdrawn pin is not the evidence the round is waiting for.

    Both retired pins were withdrawn for cause — `f750890`'s `-x` could hang with no
    diagnostic at all — so a rig log that quietly accepted it would send back a
    session's worth of unusable evidence.
    """
    assert fork_source.SUPERSEDED_TEST_PINS, "the retired list must not be empty"
    for retired in fork_source.SUPERSEDED_TEST_PINS:
        approval = ha.approve_ripper(f"cyanrip 0.9.4-rc1 (platterpus-fork-g{retired})")
        assert approval.verdict == ha.UNAPPROVED
        assert "retired" in approval.detail.lower(), retired
        assert fork_source.FORK_TEST_PIN in approval.detail, (
            f"{retired} is retired but the message does not name the current pin"
        )


def test_the_pin_under_review_says_the_round_is_open() -> None:
    approval = ha.approve_ripper(
        f"cyanrip 0.9.4-rc1 (platterpus-fork-g{fork_source.PIN_UNDER_REVIEW})"
    )
    assert approval.verdict == ha.UNAPPROVED
    assert "open" in approval.detail.lower()
    assert fork_source.PIN_UNDER_REVIEW in approval.detail


def test_dirty_suffix_on_the_approved_commit_is_not_approved() -> None:
    """A `-dirty` build carries a tag for a tree that is not what was built.

    CLAUDE.md rule 12: *"a build tag names a commit; it does not name what was
    built."* Round 6 shipped two golden references whose banners named commits three
    behind the pin. So the approval must NOT tolerate `-dirty` — unlike
    `accepts_consumer_flag`, where tolerance is correct because a dirty build of a
    listed commit still has the flag.
    """
    dirty = f"cyanrip {fork_source.FORK_EXPECTED_VERSION} ({fork_source.FORK_EXPECTED_BUILD_TAG}-dirty)"
    approval = ha.approve_ripper(dirty)
    assert approval.verdict != ha.APPROVED, (
        "a -dirty banner does not describe the binary and cannot be an approval"
    )


@pytest.mark.parametrize(
    "junk",
    [
        "(",
        ")",
        "()",
        ")(",
        "cyanrip (",
        "cyanrip )",
        "\x00\x01",
        "(" * 500,
        "cyanrip 0.9.4 (" + "x" * 5000 + ")",
        "\n\n\n",
        "cyanrip (nested (parens) here)",
    ],
)
def test_never_raises_on_malformed_banners(junk: str) -> None:
    """It parses a dependency's output, so the never-raises rule applies."""
    approval = ha.approve_ripper(junk)
    assert approval.verdict in {ha.APPROVED, ha.UNAPPROVED, ha.NOT_DETERMINED}
    assert isinstance(approval.detail, str)


class _NoAttrs:
    """Stands in for a rip log the parser gave up on part-way."""


def test_approve_rip_log_survives_a_log_object_with_no_banner() -> None:
    """Called from the report builder, which must never raise on a partial parse."""
    assert ha.approve_rip_log(_NoAttrs()).verdict == ha.NOT_DETERMINED
    assert ha.approve_rip_log(None).verdict == ha.NOT_DETERMINED

    class _Log:
        # The shape the parser ACTUALLY produces: banner without the parenthetical,
        # tag in its own field. This fixture used to set
        # `log_creator = APPROVED_BANNER` — the whole banner, parens included — which
        # no real parse ever yields, and that is precisely why it passed while the
        # product returned `not_determined` on every real fork rip (lap 10, H2).
        log_creator = f"cyanrip {fork_source.FORK_EXPECTED_VERSION}"
        ripper_build = fork_source.FORK_EXPECTED_BUILD_TAG

    assert ha.approve_rip_log(_Log()).verdict == ha.APPROVED


# --------------------------------------------------------------------------------
# The regression that reads the artifact, not our memory of it (CLAUDE.md: *"when a
# committed artifact can settle a question, the test should read the artifact"*).
# --------------------------------------------------------------------------------


def _real_fork_logs() -> list[Path]:
    """Committed real fork rip logs — the input shape the product actually sees."""
    return sorted(
        p
        for p in (_REPO / "output_reference").glob("cyanrip_fork_*/*.log")
        if "EACcompatible" not in p.name
    )


def test_the_parser_splits_the_banner_so_log_creator_alone_cannot_be_classified() -> (
    None
):
    """The mechanism behind H2, pinned off the real artifact.

    This is the *floor* under the next test: it proves the premise (the parser drops
    the parenthetical from `log_creator`) rather than asserting it in a comment. If a
    future parser change ever put the tag back into `log_creator`, this fails loudly
    and tells the next reader why `approve_rip_log` bothers to reassemble.
    """
    logs = _real_fork_logs()
    assert logs, "no committed real fork log — this regression would test nothing"
    for path in logs:
        parsed = parse_cyanrip_log(path.read_text(encoding="utf-8", errors="replace"))
        assert parsed.ripper_build, f"{path.name}: no build tag parsed"
        assert "(" not in parsed.log_creator, (
            f"{path.name}: log_creator carries the parenthetical "
            f"({parsed.log_creator!r}) — H2's premise has changed"
        )
        # And the tag is not recoverable from log_creator by any means: the two fields
        # together are the banner, and only together.
        assert parsed.ripper_build not in parsed.log_creator, path.name


def test_the_real_fork_log_reads_unapproved_not_not_determined() -> None:
    """The H2 regression: every real fork rip must reach the *verdict*, not the shrug.

    Reverting `approve_rip_log` to read `log_creator` alone makes this fail — the
    check that a test earns its keep. The maintainer's own instruction predicted the
    right answer (*"expect ripper_handshake_approval: unapproved on every rip"*),
    which is what makes the shipped `not_determined` a wrong verdict rather than a
    terse one.
    """
    logs = _real_fork_logs()
    assert logs, "no committed real fork log — this regression would test nothing"
    for path in logs:
        parsed = parse_cyanrip_log(path.read_text(encoding="utf-8", errors="replace"))
        approval = ha.approve_rip_log(parsed)

        assert approval.verdict == ha.UNAPPROVED, (
            f"{path.name}: verdict {approval.verdict!r} — a build we extracted and "
            "can name must never report as 'not determined'"
        )
        # The observed banner must be the *whole* first line, reassembled, so a bug
        # report quotes what the binary printed rather than half of it.
        first_line = path.read_text(encoding="utf-8", errors="replace").split("\n", 1)[
            0
        ]
        assert approval.observed_banner == first_line.strip(), (
            f"{path.name}: observed_banner {approval.observed_banner!r} is not the "
            f"banner line {first_line.strip()!r}"
        )
        # And it explains itself: this build is the round-7 test pin, deliberately
        # installed for the hardware session.
        assert "test pin" in approval.detail.lower(), path.name
        assert parsed.ripper_build in approval.detail, path.name


def test_the_archived_report_is_the_evidence_the_bug_shipped() -> None:
    """The bug is provable from the artifact, not only from the fork's report of it.

    The committed `.platterpus.json` was written on the rig by the shipped code, so it
    still carries the pre-fix answer — and its *detail* sentence is the confession:
    it says the ripper reported a banner **"with no build tag"** while the log's own
    first line ends in `(platterpus-fork-g9003e6f)`. Two artifacts from the same rip,
    disagreeing, both committed.

    Kept rather than regenerated because a regenerated artifact would erase the only
    hardware evidence that the wrong verdict reached a real report. What this test
    pins is that the *fixed* classifier no longer agrees with it — so if someone ever
    "fixes" the discrepancy by reverting the code instead, this fails.
    """
    import json

    reports = sorted((_REPO / "output_reference").glob("cyanrip_fork_*/*.json"))
    assert reports, "no committed fork report — nothing to cross-check"
    checked = 0
    for path in reports:
        report = json.loads(path.read_text(encoding="utf-8"))
        rip = report.get("rip") or {}
        archived = str(rip.get("ripper_handshake_approval") or "")
        if not archived:
            continue
        checked += 1
        assert archived == ha.NOT_DETERMINED, (
            f"{path.name}: archived verdict is {archived!r}. If this artifact was "
            "regenerated with the fixed code, update this test to read the new value "
            "rather than deleting it — the H2 evidence is what it is for."
        )
        assert "no build tag" in str(
            rip.get("ripper_handshake_approval_detail") or ""
        ), f"{path.name}: the archived detail no longer shows the H2 symptom"
        # The live classifier, over the log beside it, must now disagree with the
        # archive. Same rip, same bytes, different answer — that IS the fix.
        log = path.with_suffix("").with_suffix(".log")
        if not log.exists():
            continue
        parsed = parse_cyanrip_log(log.read_text(encoding="utf-8", errors="replace"))
        assert ha.approve_rip_log(parsed).verdict != archived, (
            f"{log.name}: the fixed classifier still returns the archived verdict — "
            "the H2 fix is not in effect"
        )
    assert checked, "no archived approval block found — this check examined nothing"


# --- the two independent witnesses, compared ---------------------------------
#
# `approve_ripper` reads the build tag against OUR record. The `Handshake:` line is
# what the fork's build system compiled into the BINARY. Neither is derived from the
# other — the only reason comparing them is worth anything, and the reason a build
# from an open-round tree says so permanently in a way no banner can.
#
# Our own round-7 lap-10 file told the fork "when the two disagree, the disagreement
# is the finding". Nothing compared them until this existed.

_OPEN_ROUND_NOTE = "round 7 lap 7 OPEN, verdict HOLD -- NOT a released build"


def test_the_real_forks_note_is_the_one_under_test() -> None:
    """Floor: the note used below is the artifact's, not one we invented.

    A fixture of our guess at their wording is what the H1/H5 lessons were about.
    """
    logs = _real_fork_logs()
    assert logs, "no committed fork log"
    notes = {
        parse_cyanrip_log(
            p.read_text(encoding="utf-8", errors="replace")
        ).handshake_note
        for p in logs
    }
    assert _OPEN_ROUND_NOTE in notes, (
        f"the committed logs carry {notes}, not the note these tests use"
    )


def test_approved_against_a_not_a_release_note_is_a_disagreement() -> None:
    """The dangerous direction, and the reason this is an ERROR downstream.

    We approved a build whose own compiled-in text says it came from a tree whose
    round had not closed. One of the two witnesses is wrong, and both possibilities
    are serious: the approved pin is not what we think, or the binary carries a build
    tag for a different tree (CLAUDE.md rule 12 — a build tag names a commit, not
    what was built).
    """
    message = ha.cross_check_note(ha.APPROVED, _OPEN_ROUND_NOTE)
    assert message, "an approved build claiming to be unreleased raised nothing"
    assert "disagree" in message
    assert _OPEN_ROUND_NOTE in message, "the finding does not quote the note"


def test_unapproved_against_the_same_note_is_agreement_not_a_finding() -> None:
    """The real artifact's state. It must NOT fire, or every test-pin rip cries wolf.

    This is the false-positive half, and it is the half that decides whether the
    check survives contact with a hardware session: a finding on every deliberate
    test-pin rip trains people to ignore the entry.
    """
    assert ha.cross_check_note(ha.UNAPPROVED, _OPEN_ROUND_NOTE) == ""


def test_not_determined_says_the_note_is_the_only_witness() -> None:
    """Not a disagreement — a statement about what the provenance claim rests on."""
    message = ha.cross_check_note(ha.NOT_DETERMINED, _OPEN_ROUND_NOTE)
    assert "only statement" in message
    assert _OPEN_ROUND_NOTE in message


@pytest.mark.parametrize("note", [None, "", "   "])
def test_no_note_is_no_finding(note: str | None) -> None:
    """Stock cyanrip prints no `Handshake:` line. Absence is not evidence."""
    for verdict in (ha.APPROVED, ha.UNAPPROVED, ha.NOT_DETERMINED):
        assert ha.cross_check_note(verdict, note) == ""


def test_an_approved_build_with_a_released_note_is_silent() -> None:
    """The state a closed round should produce. It must be quiet, or the check is
    a permanent finding rather than a detector."""
    assert ha.cross_check_note(ha.APPROVED, "round 8 CLOSED, released build") == ""


@pytest.mark.parametrize(
    "junk", ["(", "\x00", "OPEN" * 5000, "\n\n", "hold", "HOLD", "Not A Released Build"]
)
def test_cross_check_never_raises(junk: str) -> None:
    """It reads a dependency's prose, so the never-raises rule applies."""
    for verdict in (ha.APPROVED, ha.UNAPPROVED, ha.NOT_DETERMINED, "", "weird"):
        assert isinstance(ha.cross_check_note(verdict, junk), str)


def test_version_pair_line_names_both_versions() -> None:
    """The maintainer's ask, literally: *include what versions you both are.*"""
    line = ha.version_pair_line()
    assert __version__ in line, "our version is missing from the pair line"
    assert fork_source.FORK_EXPECTED_BANNER in line, "the ripper's build is missing"
    assert str(ha.APPROVED_BY_ROUND) in line


def test_neither_pair_line_says_cyanrip_twice() -> None:
    """**REGRESSION, in the one line whose job is to be quotable.**

    Both renderers wrote ``f"… + cyanrip {banner}"`` while every banner they are handed
    already begins ``cyanrip ``, so the maintainer-requested pair line rendered
    *"Platterpus 0.6.4b3 + cyanrip cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)"* — in the
    Copy-diagnostics bundle, the place it is most likely to be pasted into a bug report.

    **The two tests above were green throughout, and could not have failed**: both assert
    *containment* of the banner, and `"cyanrip cyanrip 0.9.4…"` contains `"cyanrip
    0.9.4…"`. A containment assertion is structurally blind to a duplicated prefix — *can
    this check be satisfied by the wrong thing?*

    Asserted by **counting**, which is the observation that separates them, and over both
    renderers plus the shapes a banner can arrive in: a full banner, a bare build tag, and
    nothing at all.
    """
    lines = {
        "version_pair_line": ha.version_pair_line(),
        "observed/full banner": ha.observed_version_pair_line(
            "cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)"
        ),
        "observed/bare tag": ha.observed_version_pair_line("platterpus-fork-gc5fb909"),
        "observed/none": ha.observed_version_pair_line(None),
    }
    for label, line in lines.items():
        assert line.count("cyanrip") == 1, (
            f"{label} names the tool {line.count('cyanrip')} times: {line!r}"
        )
        # And it names it AT ALL — the fix must not be "drop the word".
        assert "cyanrip" in line, f"{label} no longer says which ripper: {line!r}"
    # Floor: all four shapes were actually exercised, so this cannot pass on an empty
    # dict if the helper is ever refactored into something that returns nothing.
    assert len(lines) == 4


def test_observed_pair_line_reports_what_ran_not_what_should_have() -> None:
    """An archival log naming the approved pair while another binary produced it is
    the stale-build-tag failure with the roles swapped."""
    other = "cyanrip 0.9.4-rc1 (platterpus-fork-gdeadbee)"
    line = ha.observed_version_pair_line(other)
    assert "deadbee" in line
    assert fork_source.FORK_EXPECTED_BUILD_TAG not in line, (
        "the observed line must not quote the approved build it did not run"
    )
    assert ha.UNAPPROVED in line

    missing = ha.observed_version_pair_line(None)
    assert ha.NOT_DETERMINED in missing
    assert "no banner" in missing


# --- The RELATION between the offer and the rip verdict -------------------------
#
# docs/testing.md §5.al: two surfaces answering one question by different keys will
# disagree, and the defect lives strictly in the relation — no test of either side
# alone can express it. This is that test.


APPROVAL_RELATION_INPUTS: list[tuple[str, str]] = [
    ("the pin exactly", fork_source.FORK_PIN),
    ("the pin upper-cased", fork_source.FORK_PIN.upper()),
    ("the pin with surrounding whitespace", f"  {fork_source.FORK_PIN}  "),
    ("the pin with a -dirty suffix", f"{fork_source.FORK_PIN}-dirty"),
    # THE CASE THAT MADE THE PREDICATE EXACT rather than prefix-tolerant: a full sha
    # beginning with the pin passes `same_commit` and prints a DIFFERENT build tag.
    (
        "a full 40-char sha beginning with the pin",
        fork_source.FORK_PIN + "a" * (40 - len(fork_source.FORK_PIN)),
    ),
    ("a short prefix of the pin", fork_source.FORK_PIN[:6]),
    ("the round-8 test pin", "cb440bd"),
    ("the build the fork withdrew", "422d12a"),
    ("the empty string", ""),
    ("whitespace only", "   "),
    ("not a sha at all", "not-a-sha"),
]


@pytest.mark.parametrize(
    ("label", "commit"),
    APPROVAL_RELATION_INPUTS,
    ids=[c[0] for c in APPROVAL_RELATION_INPUTS],
)
def test_the_offer_and_the_rip_never_disagree_about_approval(
    label: str, commit: str
) -> None:
    """``approves_commit(c)`` must equal *"a rip with that build reports approved"*.

    **The property the 2026-08-18 defect violated.** The install offer decided approval
    from the manifest's round label while :func:`approve_ripper` decided it from the
    build tag, so a build could be offered as *"one our record approves"* with nothing
    to weigh and then stamp ``unapproved`` into every report, log and EAC export. Both
    modules' own tests passed the whole time; only this relation could see it.

    Parameterised over hostile inputs rather than the happy path, because the
    interesting rows are the ones where a *plausible* implementation diverges — a
    ``-dirty`` tag, and above all a full 40-character sha beginning with the pin, which
    the prefix-tolerant :func:`~platterpus.deps.fork_source.same_commit` calls the same
    commit while the binary prints a different tag.
    """
    from platterpus.handshake_approval import (
        APPROVED,
        approve_ripper,
        approved_build_tag_for,
        approves_commit,
    )

    offered = approves_commit(commit)
    banner = (
        f"cyanrip {fork_source.FORK_EXPECTED_VERSION} ({approved_build_tag_for(commit)})"
        if commit.strip()
        else f"cyanrip {fork_source.FORK_EXPECTED_VERSION}"
    )
    reported = approve_ripper(banner).verdict
    assert offered is (reported == APPROVED), (
        f"{label}: the offer says approves_commit={offered} while a rip with that build "
        f"reports {reported!r}. One of these lands in an archival record; they must be "
        f"one computation, not two agreeing opinions (docs/testing.md §5.al)."
    )


def test_the_approval_relation_is_not_vacuously_true() -> None:
    """Floor: the parameter set must contain both answers, or the relation proves nothing.

    A table of only-rejected inputs would satisfy the test above for an
    ``approves_commit`` that returns ``False`` unconditionally.
    """
    from platterpus.handshake_approval import approves_commit

    answers = {approves_commit(commit) for _, commit in APPROVAL_RELATION_INPUTS}
    assert answers == {True, False}, (
        f"the relation table produces only {answers} — it cannot distinguish a working "
        "predicate from one that always answers the same way"
    )
