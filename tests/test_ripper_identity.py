"""Which cyanrip binary produced a rip — and refusing to guess when we cannot.

Platterpus runs a *fork* of cyanrip that emits rows stock cyanrip does not, so a
log from each is not interchangeable evidence about the same disc. Until this
existed, nothing in the rendered log, the report, or the UI said which binary a
rip came from; the version number alone cannot tell, because the fork tracks
upstream versions.

The assertion this file cares most about is the negative one: an unrecognised
build tag must classify as ``unknown``, **never** as ``stock``. "Not a tag we
know" is an absence of evidence, and reporting it as "unmodified upstream" would
be the fourth instance of this project's most persistent bug — ``Accurip:
disabled`` read as "in the database, no match", an all-zero CRC read as a
confidence-200 match, ``Pregap LSN: unknown`` read as ``none``.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.ripper_identity import (
    FORK_BUILD_TAGS,
    STOCK_BUILD_TAGS,
    _tag_matches,
    identify_from_banner,
    identify_ripper,
)

_MINIMAL_RIP = "Track 1 ripped and encoded successfully!\n"


def _rendered(banner: str) -> str:
    return render_eac_style_log(
        parse_cyanrip_log(f"{banner}\n{_MINIMAL_RIP}"),
        platterpus_version="0.0.0",
        build_fingerprint="test",
        encoder_versions={},
    )


def _identity_row(banner: str) -> str:
    rows = [
        ln.strip() for ln in _rendered(banner).splitlines() if "Ripper build:" in ln
    ]
    assert len(rows) == 1, f"expected exactly one provenance row, got {rows}"
    return rows[0]


# --- the three states ---------------------------------------------------------


@pytest.mark.parametrize("tag", sorted(FORK_BUILD_TAGS))
def test_every_accepted_fork_tag_identifies_as_the_fork(tag: str) -> None:
    """The accepted set is data, so it is swept rather than spot-checked — a tag
    added to it without working would otherwise ship unnoticed."""
    identity = identify_ripper("cyanrip 0.9.4-rc1", tag)
    assert identity.kind == "fork"
    assert identity.is_fork is True
    assert tag in identity.detail


def test_a_fork_tag_with_a_build_hash_appended_still_identifies() -> None:
    """`git describe` habitually appends `-g<sha>`; the tag must survive it, or
    identification breaks on the first build made from a non-tagged commit."""
    identity = identify_ripper("cyanrip 0.9.4-rc1", "platterpus-fork-g1a2b3c4")
    assert identity.kind == "fork"


def test_the_upstream_release_tag_identifies_as_stock() -> None:
    identity = identify_ripper("cyanrip 0.9.3.1", "release")
    assert identity.kind == "stock"
    assert identity.is_fork is False


@pytest.mark.parametrize(
    "tag",
    [
        "",  # no parenthetical at all
        "g1a2b3c4",  # a bare git describe
        "fedora",  # a distro's tag
        "0.9.3.1-1",  # a package revision
        "unknown",
        "   ",
    ],
)
def test_an_unrecognised_tag_is_unknown_and_never_stock(tag: str) -> None:
    """The load-bearing negative. `is_fork` must be None, not False."""
    identity = identify_ripper("cyanrip 0.9.3.1", tag)
    assert identity.kind == "unknown", f"{tag!r} must not be classified"
    assert identity.is_fork is None, "None means 'not determined' — never False"
    assert "unknown" in identity.detail.casefold()


def test_no_banner_at_all_is_unknown() -> None:
    identity = identify_ripper("", "")
    assert identity.kind == "unknown"
    assert identity.is_fork is None


@pytest.mark.parametrize(
    "hostile",
    [
        "\x00\x01\x02",
        "(" * 500,
        "platterpus" * 1000,
        "\n\nrelease\n\n",
        "PLATTERPUS-FORK",
    ],
)
def test_it_never_raises_on_hostile_input(hostile: str) -> None:
    """It is fed parsed external output, so it has to answer rather than throw.

    `PLATTERPUS-FORK` is in this list deliberately: case-insensitivity is the
    intended behaviour, and it being here means a change that made matching
    case-sensitive shows up as a *classification* change, not a crash.
    """
    identity = identify_ripper(hostile, hostile)
    assert identity.kind in {"fork", "stock", "unknown"}
    assert identity.detail


def test_matching_is_case_insensitive() -> None:
    assert identify_ripper("cyanrip 0.9.4", "Platterpus-Fork").kind == "fork"
    assert identify_ripper("cyanrip 0.9.3", "RELEASE").kind == "stock"


# --- classifying from a raw `-V` banner ---------------------------------------


def test_a_whole_version_line_can_be_classified_directly() -> None:
    """The preflight check and the progress panel hold a banner string, not a
    parsed log; they must not need a second private regex to read it."""
    identity = identify_from_banner("cyanrip 0.9.4-rc1 (platterpus-fork)")
    assert identity.kind == "fork"
    assert identity.version == "cyanrip 0.9.4-rc1"
    assert identity.build_tag == "platterpus-fork"


def test_a_banner_with_no_parenthetical_is_unknown_not_stock() -> None:
    assert identify_from_banner("cyanrip 0.9.3.1").kind == "unknown"


def test_an_empty_banner_is_unknown() -> None:
    assert identify_from_banner("").kind == "unknown"
    assert identify_from_banner("   \n  ").kind == "unknown"


# --- what the signed archival log says ----------------------------------------


def test_the_rendered_log_names_the_fork_when_the_fork_ripped() -> None:
    row = _identity_row("cyanrip 0.9.4-rc1 (platterpus-fork)")
    assert "platterpus-fork" in row
    assert "Platterpus fork" in row


def test_the_rendered_log_says_unmodified_when_upstream_ripped() -> None:
    row = _identity_row("cyanrip 0.9.3.1 (release)")
    assert "unmodified upstream" in row


def test_the_row_is_present_and_says_so_when_the_build_is_unknown() -> None:
    """Omitting the row would read as "nothing unusual", and this log is signed.

    Both unknown shapes are covered: a tag we do not recognise, and no tag.
    """
    unrecognised = _identity_row("cyanrip 0.9.3.1 (g1a2b3c4)")
    assert "not determined" in unrecognised
    assert "g1a2b3c4" in unrecognised

    absent = _identity_row("cyanrip 0.9.3.1")
    assert "not determined" in absent


# The two AFFIRMATIVE claims the row can make. Matched with their leading em
# dash so they cannot be confused with the undetermined row, which names both
# possibilities in prose ("...the Platterpus fork or an unmodified cyanrip...")
# precisely because it is declining to pick one.
_CLAIM_FORK = "— the Platterpus fork of cyanrip"
_CLAIM_STOCK = "— unmodified upstream cyanrip"


def test_the_rendered_log_never_claims_a_build_it_could_not_identify() -> None:
    """The negative, at the surface a reader actually sees."""
    for banner in ("cyanrip 0.9.3.1", "cyanrip 0.9.3.1 (g1a2b3c4)", "cyanrip 1.0"):
        row = _identity_row(banner)
        assert _CLAIM_FORK not in row, row
        assert _CLAIM_STOCK not in row, row
        assert "not determined" in row, row


def test_the_claim_strings_are_the_ones_the_renderer_actually_emits() -> None:
    """Guards the guard: if the row's wording is reworded, the two constants
    above would silently stop matching anything and the negative test would pass
    by finding nothing. So assert each claim DOES appear in its own case."""
    assert _CLAIM_FORK in _identity_row("cyanrip 0.9.4-rc1 (platterpus-fork)")
    assert _CLAIM_STOCK in _identity_row("cyanrip 0.9.3.1 (release)")


def test_the_committed_reference_log_still_renders_a_row() -> None:
    """Inertness check on the real 0.9.3 log we ship: the row appears, and it
    reports honestly rather than claiming a fork that did not rip it."""
    from pathlib import Path

    stock = Path(__file__).parents[1] / "output_reference" / "cyanrip_flac"
    text = render_eac_style_log(
        parse_cyanrip_log(
            (stock / "cyanrip_flac_police_classics.log").read_text(encoding="utf-8")
        ),
        platterpus_version="0.0.0",
        build_fingerprint="test",
        encoder_versions={},
    )
    rows = [ln.strip() for ln in text.splitlines() if "Ripper build:" in ln]
    assert len(rows) == 1
    assert "Platterpus fork" not in rows[0]


# --- the real tags this fork emits (handshake round 4, A / Q2 / H3) -----------


def test_the_real_pin_banner_identifies_as_the_fork() -> None:
    """Byte-for-byte the string the fork reports emitting at pin a835052.

    Pinned by SHAPE, not literally: the `g<sha>` component changes on every
    push, and the fork warned that asserting the whole string would break on
    their next commit. What must hold is the `platterpus-fork` token.
    """
    identity = identify_from_banner("cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)")
    assert identity.kind == "fork"
    assert identity.build_tag == "platterpus-fork-ga835052"


def test_a_different_commit_sha_still_identifies() -> None:
    """The shape-not-literal rule, exercised. If this ever fails, someone has
    pinned a SHA and the next fork push turns the suite red for no reason."""
    for sha in ("ga835052", "gdeadbee", "g0000000", "gabcdef1234567"):
        assert identify_from_banner(
            f"cyanrip 0.9.4-rc1 (platterpus-fork-{sha})"
        ).kind == ("fork"), sha


def test_a_tarball_build_of_the_fork_is_not_mistaken_for_upstream() -> None:
    """§H3 of the fork's round-4 file, and it is a genuine near-miss.

    Built from a source tarball with no git metadata, meson's `vcs_tag` falls
    back to the literal string `release`, so the tag becomes
    `platterpus-fork-grelease`. Because we tokenise on `-`/`_` this classifies
    as **fork**, correctly. Were we matching `release` as a substring anywhere,
    that build would flip to "unmodified upstream" — the exact tri-state
    collapse the classifier exists to prevent, on a binary that IS the fork.

    They flagged it as a case we had not enumerated. They were right; here it is.
    """
    identity = identify_from_banner("cyanrip 0.9.4-rc1 (platterpus-fork-grelease)")
    assert identity.kind == "fork", (
        "a tarball build of the fork must not read as unmodified upstream"
    )
    assert identity.is_fork is True


def test_the_older_comma_form_still_identifies() -> None:
    """The pre-round-4 banner shape, `(<sha>, platterpus-fork)`. The maintainer
    has archived rips from those builds; reclassifying them as unknown would
    rewrite the provenance of real library entries."""
    assert identify_from_banner(
        "cyanrip 0.9.4-rc1 (ec406ac, platterpus-fork)"
    ).kind == ("fork")


def test_a_dirty_build_is_indistinguishable_and_that_is_recorded() -> None:
    """Q2's caveat, pinned as a KNOWN LIMIT rather than left as folklore.

    A binary built from a modified working tree emits its base commit's tag with
    no marker, so it claims to be that commit. We cannot detect it from the
    banner and must not pretend otherwise: it classifies as fork, which is true,
    and the SHA it reports may be a lie. Adding `--dirty` is open as J2.
    """
    clean = identify_from_banner("cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)")
    # There is no third state to assert — the point is that a dirty build is
    # byte-identical to this, so this test exists to carry the sentence above.
    assert clean.kind == "fork"
    assert "ga835052" in clean.build_tag


# ==========================================================================
# The build tag is EXTERNAL INPUT, and matching it used to be cubic
# ==========================================================================
#
# `_tag_matches` generated every contiguous run of hyphen-separated parts —
# two nested loops with an O(n) join inside, so O(n³) in the number of
# separators. The tag is whatever the ripper's version banner said, and it is
# reached on every rip through `rip_report` and the EAC-compatible log emitter.
#
# Measured 2026-08-28 on the old implementation: 400 parts 0.11 s, 800 parts
# 0.87 s, 1600 parts 7.1 s, **3000 parts 45 s** — eight times the work for twice
# the input, which is the cubic signature. A garbled banner does not have to be
# malicious to be long, and nothing validated the tag's shape before this.
#
# Found by the 2026-08-28 lesson-to-gate audit while asking a different
# question — "which boundary functions have no property test?" — which is the
# argument for asking it of every boundary rather than the ones that have burned
# us. It is also `CLAUDE.md`'s *validate every input and every dependency
# output*, applied to a field nobody thought of as an input because it is "just
# a version string".


def _reference_tag_matches(tag: str, wanted: frozenset[str]) -> bool:
    """The ORIGINAL implementation, kept as the oracle for the rewrite.

    **This is an equivalence test, not a correctness test, and the difference
    matters** — `CLAUDE.md` warns that two implementations agreeing is not
    either one being correct, because they share an ancestor. Correctness is
    established by the example tests above, which assert real banners against
    real expectations. What this pins is that making the function fast did not
    make it answer differently, which is the one thing a rewrite can break and
    example tests spot-check.
    """
    import re

    if tag in wanted:
        return True
    tokens = {t for t in re.split(r"[\s,;+/]+", tag) if t}
    if tokens & wanted:
        return True
    for token in tokens:
        parts = re.split(r"[-_]", token)
        for width in range(len(parts), 0, -1):
            for start in range(len(parts) - width + 1):
                if "-".join(parts[start : start + width]) in wanted:
                    return True
    return False


@given(
    st.lists(
        st.sampled_from(
            ["platterpus", "fork", "cyanrip", "g1a2b3c4", "a", "", "dirty", "0.9.4"]
        ),
        max_size=7,
    ),
    st.sampled_from(["-", "_", " ", "+", ",", ";", "/"]),
)
@settings(max_examples=400, deadline=None)
def test_the_fast_tag_matcher_answers_exactly_as_the_original(
    words: list[str], separator: str
) -> None:
    """Equivalence over generated tags, both sets."""
    tag = separator.join(words)
    for wanted in (FORK_BUILD_TAGS, STOCK_BUILD_TAGS):
        assert _tag_matches(tag, wanted) == _reference_tag_matches(tag, wanted), (
            f"the rewrite changed the answer for {tag!r} against {sorted(wanted)}"
        )


def test_a_long_build_tag_does_not_hang_the_program() -> None:
    """The regression test for the cubic blow-up.

    The bound is deliberately loose — this is a *complexity* assertion, not a
    benchmark, and a slow CI runner must not turn it into a flake. The old
    implementation took 45 SECONDS on this input; anything under a second is
    unambiguously not cubic, and the measurement below is ~0.0001 s.
    """
    import time

    tag = "-".join(["a"] * 3000)
    started = time.perf_counter()
    assert _tag_matches(tag, FORK_BUILD_TAGS) is False
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0, (
        f"classifying a 3000-part build tag took {elapsed:.2f}s — the matcher has "
        f"gone superlinear again. This value comes off the ripper's version "
        f"banner on every rip; the original cost 45s here."
    )


def test_the_timing_guard_would_have_caught_the_original() -> None:
    """Non-triviality: prove the bound is meaningful by timing the ORACLE.

    Without this the assertion above is just "a fast thing is fast" — it would
    pass against any implementation, including one that never matched anything.
    A smaller input keeps this test quick while still showing the growth.
    """
    import time

    tag = "-".join(["a"] * 400)
    started = time.perf_counter()
    _reference_tag_matches(tag, FORK_BUILD_TAGS)
    old_cost = time.perf_counter() - started

    started = time.perf_counter()
    _tag_matches(tag, FORK_BUILD_TAGS)
    new_cost = time.perf_counter() - started

    assert old_cost > new_cost * 10, (
        f"the original ({old_cost:.4f}s) is no longer dramatically slower than "
        f"the rewrite ({new_cost:.4f}s) on 400 parts — either the oracle has "
        f"been changed, or this guard is measuring nothing"
    )
