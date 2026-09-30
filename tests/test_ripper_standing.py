"""What the installed ripper build means, in words: About and the update offer.

The maintainer's report (2026-09-28): About said ``cyanrip: 0.9.4 ✓`` and the update
offer said *"release 28 — you have release 27 (e0471f4)"*. Both were accurate and
neither said what it meant. These tests pin the replacement:

* every state names the build by version, commit and fork release, and says what
  that state means for the rips;
* the status is the SAME fact the rip-time check records (`approve_ripper`), a
  relation neither surface can express alone;
* a version is never printed beside a commit it does not belong to;
* the text the ripper printed about itself cannot be read as Markdown in About.
"""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace as _NS

import pytest
from hypothesis import given
from hypothesis import strategies as st
from PySide6.QtWidgets import QApplication, QTextBrowser

from platterpus import handshake_approval, ripper_standing
from platterpus.deps import build_notes, fork_source
from platterpus.deps import manager as dep_manager
from platterpus.deps.build_notes import BuildNote
from platterpus.deps.manager import DependencyReport
from platterpus.deps.registry import SPECS
from platterpus.ui.help_dialogs import AboutDialog

_APPROVED = fork_source.FORK_EXPECTED_BANNER
_UNDER_REVIEW = fork_source.UNDER_REVIEW_TARGET.banner
_OTHER_FORK = "cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)"
_NO_TAG = "cyanrip 0.9.4"


@pytest.fixture
def a_round_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """Round 29 as it stood while it was open: `e0471f4` (`.17`) approved, `51cc789`
    (`.18`) under review.

    **Set here, not read off the live pins.** These tests were written while round 29
    was open and first read the state from the constants; when the round closed on
    2026-09-29 the two pins became one and each test was about a state that no longer
    existed. Both commits are rows of the fork's release table, so the state is a real
    one, not a made-up pair.
    """
    monkeypatch.setattr(fork_source, "FORK_PIN", "e0471f4")
    monkeypatch.setattr(fork_source, "FORK_EXPECTED_VERSION", "0.9.4-rc2+platterpus.17")
    monkeypatch.setattr(
        fork_source, "FORK_EXPECTED_BUILD_TAG", "platterpus-fork-ge0471f4"
    )
    monkeypatch.setattr(
        fork_source,
        "FORK_EXPECTED_BANNER",
        "cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)",
    )
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", "51cc789")
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW_ROUND", 29)
    monkeypatch.setattr(
        fork_source,
        "UNDER_REVIEW_TARGET",
        dataclasses.replace(
            fork_source.UNDER_REVIEW_TARGET,
            pin="51cc789",
            version="0.9.4-rc2+platterpus.18",
        ),
    )
    assert fork_source.a_round_is_reviewing_a_build(), "the fixture's own floor"
    assert fork_source.current_test_pin() is None, "round 29 named no test pin"


def test_the_approved_build_is_named_and_says_approved() -> None:
    standing = ripper_standing.describe_installed_ripper(_APPROVED)
    assert fork_source.FORK_EXPECTED_VERSION in standing.installed
    assert f"commit {fork_source.FORK_PIN}" in standing.installed
    assert "the Platterpus fork" in standing.installed
    assert standing.status.startswith("✓ Approved")
    assert f"round {handshake_approval.APPROVED_BY_ROUND}" in standing.status


def test_the_build_under_review_says_being_tested_and_keep_it(
    a_round_is_open: None,
) -> None:
    standing = ripper_standing.describe_installed_ripper(
        fork_source.UNDER_REVIEW_TARGET.banner
    )
    assert f"commit {fork_source.PIN_UNDER_REVIEW}" in standing.installed
    assert standing.status.startswith("ⓘ Being tested, not approved yet")
    assert f"round {fork_source.PIN_UNDER_REVIEW_ROUND}" in standing.status
    assert "unapproved" in standing.status and "bit-perfect" in standing.status


def test_once_the_round_closes_the_same_build_says_approved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other side of the test above, which a close reaches without any code
    changing: the reviewed build and the approved one are one commit, so the same
    banner reads as approved and nothing calls it "being tested"."""
    monkeypatch.setattr(fork_source, "PIN_UNDER_REVIEW", fork_source.FORK_PIN)
    assert not fork_source.a_round_is_reviewing_a_build(), "the floor"
    standing = ripper_standing.describe_installed_ripper(
        fork_source.FORK_EXPECTED_BANNER
    )
    assert standing.status.startswith("✓ Approved"), standing.status
    assert "Being tested" not in standing.status


def test_another_fork_build_says_not_approved_and_names_the_way_back() -> None:
    standing = ripper_standing.describe_installed_ripper(_OTHER_FORK)
    assert standing.status.startswith("⚠ Not approved")
    assert "Tools → Setup & Updates…" in standing.status
    assert fork_source.FORK_PIN in standing.status


def test_no_tag_and_no_banner_are_not_determined_never_negative() -> None:
    for banner in (_NO_TAG, None, ""):
        standing = ripper_standing.describe_installed_ripper(banner)
        assert standing.status.startswith("ⓘ Not determined"), banner
        assert "upstream" not in standing.installed, banner


def test_the_status_is_the_verdict_every_rip_records() -> None:
    """Two surfaces, one question, one key: the relation, not either side."""
    for banner in (_APPROVED, _UNDER_REVIEW, _OTHER_FORK, _NO_TAG, None):
        standing = ripper_standing.describe_installed_ripper(banner)
        assert standing.verdict == handshake_approval.approve_ripper(banner).verdict
    marker = {
        handshake_approval.APPROVED: "✓",
        handshake_approval.NOT_DETERMINED: "ⓘ",
    }
    seen = set()
    for banner in (_APPROVED, _UNDER_REVIEW, _OTHER_FORK, _NO_TAG):
        standing = ripper_standing.describe_installed_ripper(banner)
        seen.add(standing.verdict)
        if standing.verdict in marker:
            assert standing.status.startswith(marker[standing.verdict])
        else:
            assert standing.status[0] in "ⓘ⚠", "every status carries a text marker"
    assert len(seen) == 3, "the four banners must reach all three verdicts"


def test_a_version_is_never_paired_with_a_commit_it_does_not_belong_to() -> None:
    assert ripper_standing.name_build(None, "abc1234", 17) == (
        "the build from commit abc1234 (fork release 17)"
    )
    assert ripper_standing.known_version_for_commit("abc1234") is None
    assert ripper_standing.name_known_build(fork_source.FORK_PIN).startswith(
        f"cyanrip {fork_source.FORK_EXPECTED_VERSION} (commit {fork_source.FORK_PIN}"
    )


@given(st.text(max_size=300))
def test_describing_any_banner_never_raises(banner: str) -> None:
    standing = ripper_standing.describe_installed_ripper(banner)
    assert standing.installed and standing.status


def test_the_ripper_banner_comes_from_the_check_not_a_probe() -> None:
    assert build_notes.RIPPER_DEP_ID in {spec.dep_id for spec in SPECS}
    report = DependencyReport(
        ok_probes={build_notes.RIPPER_DEP_ID: _NS(raw_output=f"{_APPROVED}\nmore")}
    )
    assert build_notes.ripper_banner(report) == _APPROVED
    assert build_notes.ripper_banner(None) is None
    assert build_notes.ripper_banner(DependencyReport()) is None


def _report(banner: str, version_text: str, tag: str) -> DependencyReport:
    return DependencyReport(
        ok=[_NS(dep_id="cyanrip")],  # type: ignore[list-item]  # a stand-in spec
        ok_versions={"cyanrip": (0, 9, 4)},
        ok_probes={
            "cyanrip": _NS(location="/home/u/.local/bin/cyanrip", raw_output=banner)
        },
        measured_at="2026-09-28T21:50:00+00:00",
        build_notes={
            "cyanrip": BuildNote(
                ok=True,
                summary="the Platterpus fork",
                detail="",
                version_text=version_text,
                build_tag=tag,
            )
        },
    )


def _about_text(report: DependencyReport) -> str:
    dep_manager.remember_report(report)
    try:
        view = QTextBrowser()
        view.setMarkdown(AboutDialog._build_markdown())
        return view.toPlainText()
    finally:
        dep_manager.remember_report(None)


def test_about_names_the_full_build_and_what_it_means(qapp: QApplication) -> None:
    text = _about_text(
        _report(
            _APPROVED,
            fork_source.FORK_EXPECTED_VERSION,
            fork_source.FORK_EXPECTED_BUILD_TAG,
        )
    )
    # The row the maintainer quoted, now with the tool's own version.
    assert f"cyanrip: {fork_source.FORK_EXPECTED_VERSION} ✓" in text
    assert "cyanrip: 0.9.4 ✓" not in text
    for row in ("Installed:", "Status: ✓ Approved", "Default build:", "How to read"):
        assert row in text, row


def test_about_shows_the_rippers_own_text_literally(qapp: QApplication) -> None:
    """Dependency output is not Markdown: a crafted banner renders as written.

    The tag holds no ``)``, because the first ``)`` ends a banner's tag.
    """
    tag = "evil*tag_[x]<b>bold</b>`x`<a href=http://e.x>y"
    report = _report(f"cyanrip 0.9.4 ({tag})", "0.9.4", tag)
    assert f'build tag "{tag}"' in _about_text(report)
    dep_manager.remember_report(report)
    try:
        view = QTextBrowser()
        view.setMarkdown(AboutDialog._build_markdown())
        html = view.toHtml()
    finally:
        dep_manager.remember_report(None)
    assert "http://e.x" in view.toPlainText()
    assert 'href="http://e.x"' not in html, "a banner made a link"
    assert "<b>bold" not in html.replace("&lt;b&gt;", ""), "a banner made bold text"


def test_the_update_offer_names_both_builds_and_explains_the_numbers(
    a_round_is_open: None,
) -> None:
    """The maintainer's quote: 'release 28 — you have release 27 (e0471f4)'."""
    from test_ripper_manifest import PUBLISHED_V2

    from platterpus.deps.ripper_manifest import parse_manifest
    from platterpus.deps.ripper_offer import evaluate_offer

    document = json.loads(json.dumps(PUBLISHED_V2))
    beta = document["channels"]["beta"]
    beta.update(
        commit=fork_source.PIN_UNDER_REVIEW,
        release_seq=fork_source.release_seq_for_commit(fork_source.PIN_UNDER_REVIEW),
        version=fork_source.UNDER_REVIEW_TARGET.version,
        install=f"https://github.com/rmccann-hub/cyanrip/archive/{fork_source.PIN_UNDER_REVIEW}.tar.gz",
    )
    manifest = parse_manifest(json.dumps(document))
    assert manifest is not None
    offer = evaluate_offer(manifest, "beta", installed_commit=fork_source.FORK_PIN)
    assert offer.release is not None, offer.detail
    assert (
        ripper_standing.name_known_build(fork_source.PIN_UNDER_REVIEW) in offer.detail
    )
    assert (
        f"You have {ripper_standing.name_known_build(fork_source.FORK_PIN)}"
        in offer.detail
    )
    assert ripper_standing.SHORT_HOW_TO_READ in offer.detail
    assert "you have release" not in offer.detail
    assert "in *this* repository" not in offer.detail
    assert f"round {fork_source.PIN_UNDER_REVIEW_ROUND} is testing" in offer.detail


def test_diagnostics_names_the_installed_ripper_beside_the_approved_pair(
    a_round_is_open: None,
) -> None:
    """The maintainer pasted a diagnostics file on 2026-09-28 that said only
    ``cyanrip: … version=0.9.4``, so it could not show whether `.18` was installed."""
    from platterpus.ui.dialogs.diagnostics_dialog import build_diagnostics_text

    dep_manager.remember_report(
        _report(
            fork_source.UNDER_REVIEW_TARGET.banner,
            fork_source.UNDER_REVIEW_TARGET.version,
            fork_source.UNDER_REVIEW_TARGET.build_tag,
        )
    )
    try:
        text = build_diagnostics_text()
    finally:
        dep_manager.remember_report(None)
    lines = text.splitlines()
    pair = next(i for i, line in enumerate(lines) if line.startswith("Approved pair:"))
    installed = lines[pair + 1]
    assert installed.startswith("Installed ripper: "), installed
    assert f"commit {fork_source.PIN_UNDER_REVIEW}" in installed
    assert "Being tested, not approved yet" in installed
    row = next(line for line in lines if line.startswith("cyanrip: "))
    assert f"build={fork_source.UNDER_REVIEW_TARGET.version}" in row


def test_diagnostics_before_any_check_says_not_checked() -> None:
    from platterpus.ui.dialogs.diagnostics_dialog import build_diagnostics_text

    dep_manager.remember_report(None)
    assert "Installed ripper: Not checked yet." in build_diagnostics_text()
