"""A ``-dirty`` build is ordered as its release, and reported, kept and offered as unapproved.

The claude-code-skills review of 2026-10-26 (item 2.2) found ``-dirty`` stripped
before the release lookup. That is right for ORDERING (a dirty build of a release
still sits at that release and has its flags), and it is kept. The defect was
elsewhere: :func:`~platterpus.deps.fork_source.same_commit` is a prefix match, so
``5f1d036-dirty`` read as the approved pin in the update offer (*"your build is
the newest published"*, nothing offered) while every rip on it recorded
``unapproved``, and ``<pin under review>-dirty`` read as the build a round needs,
so the offer, the wizard and the ripper status all kept it.

One predicate answers *is this dirty* (``fork_source.is_dirty_build``); each
surface below is held to the rip-time verdict, ``handshake_approval``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from platterpus import handshake_approval as ha
from platterpus import ripper_standing
from platterpus.deps import fork_source
from platterpus.deps.ripper_manifest import (
    CHANNEL_STABLE,
    RipperManifest,
    parse_manifest,
)
from platterpus.deps.ripper_offer import (
    OFFER_MISMATCHED,
    OFFER_UP_TO_DATE,
    evaluate_offer,
)

#: The fork's manifest as published at `a3f7043` (stable `.23`, beta `.27`).
_MANIFEST_PATH: Path = (
    Path(__file__).parent / "fixtures" / "fork_release_manifest_a3f7043.json"
)


def _manifest() -> RipperManifest:
    parsed = parse_manifest(_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert parsed is not None, "the filed manifest must parse"
    return parsed


def _banner(commit: str) -> str:
    return f"cyanrip {fork_source.FORK_EXPECTED_VERSION} ({fork_source.FORK_BRANCH}-g{commit})"


# --- The verdict --------------------------------------------------------------


def test_a_dirty_tag_of_the_approved_pin_reads_as_UNAPPROVED() -> None:
    """Not merely "not approved": ``not_determined`` would pass that, and it is the
    wrong claim. A ``-dirty`` tag of a commit we know is recognised, so the honest
    verdict is the real negative; the clean tag beside it is the positive control."""
    clean = ha.approve_ripper(_banner(fork_source.FORK_PIN))
    dirty = ha.approve_ripper(_banner(f"{fork_source.FORK_PIN}-dirty"))
    assert clean.verdict == ha.APPROVED
    assert dirty.verdict == ha.UNAPPROVED
    assert "-dirty" in dirty.detail and "changes" in dirty.detail, dirty.detail


def test_a_dirty_tag_of_the_build_under_review_is_not_described_as_that_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "abc1234")
    approval = ha.approve_ripper(_banner("abc1234-dirty"))
    assert approval.verdict == ha.UNAPPROVED
    assert fork_source.pin_under_review_role() not in approval.detail
    assert "-dirty" in approval.detail


def test_the_tri_state_still_holds_for_a_banner_with_no_tag() -> None:
    """The narrowing is to KNOWN builds: an absent tag stays not determined."""
    assert ha.approve_ripper("cyanrip 0.9.4").verdict == ha.NOT_DETERMINED


# --- Ordering keeps it --------------------------------------------------------


def test_ordering_still_places_a_dirty_build_at_its_release() -> None:
    assert fork_source.release_seq_for_commit(f"{fork_source.FORK_PIN}-dirty") == (
        fork_source.FORK_PIN_RELEASE_SEQ
    )


@pytest.mark.parametrize(
    ("value", "dirty"),
    [
        ("5f1d036-dirty", True),
        ("platterpus-fork-g5f1d036-DIRTY", True),
        ("  5f1d036-dirty  ", True),
        ("5f1d036", False),
        ("", False),
        ("dirty", False),
    ],
)
def test_is_dirty_build(value: str, dirty: bool) -> None:
    assert fork_source.is_dirty_build(value) is dirty


# --- Keeping refuses it ---------------------------------------------------------


def test_a_dirty_build_under_review_is_not_the_build_under_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "abc1234")
    assert fork_source.a_round_is_reviewing_a_build()
    assert fork_source.is_the_build_under_review("abc1234")
    assert not fork_source.is_the_build_under_review("abc1234-dirty")


def test_the_ripper_status_does_not_call_a_dirty_build_under_review_being_tested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "abc1234")
    clean = ripper_standing.describe_installed_ripper(_banner("abc1234"))
    dirty = ripper_standing.describe_installed_ripper(_banner("abc1234-dirty"))
    assert "Being tested" in clean.status
    assert "Being tested" not in dirty.status
    assert dirty.verdict == ha.UNAPPROVED


# --- Offering refuses it --------------------------------------------------------


def test_a_dirty_approved_pin_is_offered_the_clean_pin_not_told_it_is_current() -> None:
    manifest = _manifest()
    clean = evaluate_offer(
        manifest,
        CHANNEL_STABLE,
        installed_commit=fork_source.FORK_PIN,
    )
    assert clean.verdict == OFFER_UP_TO_DATE  # the positive control
    assert not clean.install_commit

    dirty = evaluate_offer(
        manifest,
        CHANNEL_STABLE,
        installed_commit=f"{fork_source.FORK_PIN}-dirty",
    )
    assert dirty.verdict == OFFER_MISMATCHED, dirty.detail
    assert dirty.install_commit == fork_source.FORK_PIN
    # The relation: the offer's "costs nothing" is the rip verdict of the build on
    # offer, and the build on offer is clean.
    assert dirty.auto_installable == ha.approves_commit(dirty.install_commit)
    assert dirty.may_surface_unprompted
    assert "-dirty" in dirty.detail and "unapproved" in dirty.detail


def test_a_dirty_build_under_review_is_offered_the_clean_one_with_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "abc1234")
    offer = evaluate_offer(
        _manifest(),
        CHANNEL_STABLE,
        installed_commit="abc1234-dirty",
    )
    assert offer.install_commit == "abc1234"
    assert not offer.auto_installable  # not approved yet: consent, not one click
    assert offer.installable_with_consent
    assert offer.would_be_unapproved


@pytest.mark.parametrize(
    "installed",
    [
        f"{fork_source.FORK_PIN}-dirty",
        f"{fork_source.PIN_UNDER_REVIEW}-dirty",
        f"{fork_source.FORK_TEST_PIN}-dirty",
        "0badc0d-dirty",
    ],
)
def test_no_offer_ever_installs_a_dirty_build(installed: str) -> None:
    offer = evaluate_offer(
        _manifest(),
        CHANNEL_STABLE,
        installed_commit=installed,
    )
    assert offer.install_commit, "a dirty build was left with nothing to put back"
    assert not fork_source.is_dirty_build(offer.install_commit)


def test_the_manifest_cannot_name_a_dirty_commit() -> None:
    """The other route to offering one: their manifest. Its commit field is
    validated as hex at the boundary, so a `-dirty` row does not parse into an
    offer at all."""
    document = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    document["channels"]["stable"]["commit"] = "891c79e-dirty"
    parsed = parse_manifest(json.dumps(document))
    stable = parsed.channel(CHANNEL_STABLE) if parsed is not None else None
    assert stable is None or not fork_source.is_dirty_build(stable.commit)
