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
"""

from __future__ import annotations

import pytest

from platterpus import __version__
from platterpus import handshake_approval as ha
from platterpus.deps import fork_source

APPROVED_BANNER = fork_source.FORK_EXPECTED_BANNER


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
        f"cyanrip 0.9.4-rc1 (platterpus-fork-g{fork_source.NEXT_PIN_UNDER_REVIEW})"
    )
    assert approval.verdict == ha.UNAPPROVED
    assert "open" in approval.detail.lower()
    assert fork_source.NEXT_PIN_UNDER_REVIEW in approval.detail


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
        log_creator = APPROVED_BANNER

    assert ha.approve_rip_log(_Log()).verdict == ha.APPROVED


def test_version_pair_line_names_both_versions() -> None:
    """The maintainer's ask, literally: *include what versions you both are.*"""
    line = ha.version_pair_line()
    assert __version__ in line, "our version is missing from the pair line"
    assert fork_source.FORK_EXPECTED_BANNER in line, "the ripper's build is missing"
    assert str(ha.APPROVED_BY_ROUND) in line


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
