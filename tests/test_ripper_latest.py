"""``--install-ripper latest`` / ``latest-beta``: a channel's head, resolved to a commit.

The resolver lives in `deps/ripper_latest.py`; the CLI half (that the resolved
target is the one the step engine BUILDS, and that a refusal installs nothing) is
in `tests/test_app.py` beside the other `--install-ripper` tests.

The manifest these tests read is the fork's published schema-2 document
(`test_ripper_manifest.PUBLISHED_V2`), with the beta row moved ahead so the two
channels are distinguishable — a test in which both keywords resolve to the same
commit cannot tell which row either one read.
"""

from __future__ import annotations

import json
from typing import Any

from test_ripper_manifest import PUBLISHED_V2

from platterpus.deps import fork_source
from platterpus.deps.ripper_latest import (
    LATEST_KEYWORDS,
    channel_for,
    resolve_keyword,
    resolve_latest,
)
from platterpus.deps.ripper_manifest import (
    CHANNEL_BETA,
    CHANNEL_STABLE,
    RipperManifest,
    parse_manifest,
)
from platterpus.deps.ripper_offer import OFFER_AVAILABLE, evaluate_offer

#: A beta head distinct from the stable one, and ahead of every release our own
#: record lists, so the offer below sees it as a genuine forward step.
#:
#: **It must never be a pin a closed round approved.** It was `e0471f4` while round
#: 28 reviewed that build, and when round 28 closed and `FORK_PIN` rolled to it
#: (2026-09-28) the fixture's "unapproved beta head" became the approved build, and
#: `--install-ripper latest-beta` correctly stopped printing its "not the
#: handshake-approved build" note. So the head is now the fork's branch tip after
#: `.17`, `a71176d`, a commit no round has reviewed, and the assertion in
#: `_document` fails first, with this reason, if a later roll catches up with it.
_BETA_COMMIT = "a71176d"

#: The build a closed round approved — what a bare `--install-ripper` builds.
PRODUCTION_TARGET_PIN: str = fork_source.PRODUCTION_TARGET.pin


def _document(**beta: Any) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(json.dumps(PUBLISHED_V2))
    ours = fork_source.release_seq_for_commit(fork_source.PRODUCTION_TARGET.pin)
    assert ours is not None, "the premise: our approved pin has a release number"
    assert _BETA_COMMIT != fork_source.FORK_PIN, (
        "the premise: the fixture's beta head is a build no closed round approved. "
        "FORK_PIN has caught up with it; move _BETA_COMMIT past the new pin."
    )
    document["channels"]["beta"].update(
        {
            "commit": _BETA_COMMIT,
            "release_seq": ours + 5,
            "handshake_round": 29,
            "round_closed": False,
            "version": "0.9.4-rc2+platterpus.18",
            "install": f"https://github.com/rmccann-hub/cyanrip/archive/{_BETA_COMMIT}.tar.gz",
            **beta,
        }
    )
    return document


def _manifest(**beta: Any) -> RipperManifest:
    parsed = parse_manifest(json.dumps(_document(**beta)))
    assert parsed is not None, "the fixture must parse"
    return parsed


def test_each_keyword_reads_its_own_channels_head() -> None:
    manifest = _manifest()
    stable = manifest.channel(CHANNEL_STABLE)
    beta = manifest.channel(CHANNEL_BETA)
    assert stable is not None and beta is not None
    assert stable.commit != beta.commit, "the premise: the two heads differ"

    latest = resolve_latest("latest", manifest)
    assert latest.target is not None, latest.detail
    assert latest.target.pin == stable.commit
    assert latest.release is stable

    latest_beta = resolve_latest("latest-beta", manifest)
    assert latest_beta.target is not None, latest_beta.detail
    assert latest_beta.target.pin == beta.commit == _BETA_COMMIT
    assert "beta" in latest_beta.detail and "OPEN" in latest_beta.detail


def test_the_target_carries_what_the_manifest_states_for_that_commit() -> None:
    """Version and meson options come from the row describing THIS commit.

    Schema 2 names `-Ddeclare_released=true`; meson fails the whole configure on
    an option a commit does not know, so the options must be the row's, not a
    constant. The build tag is derived from the commit, so the verify step is as
    strict as for any `--install-ripper <commit>`.
    """
    manifest = _manifest()
    row = manifest.channel(CHANNEL_STABLE)
    assert row is not None and row.meson_options, "the premise: schema-2 options"

    target = resolve_latest("latest", manifest).target
    assert target is not None
    assert target.version == row.version
    assert target.meson_options == row.meson_options
    assert target.build_tag == f"platterpus-fork-g{row.commit}"


def test_an_unreadable_manifest_is_a_refusal_never_the_approved_build() -> None:
    """The TASKS row's closing warning, as a test.

    Falling back to the approved pin would look helpful and would make a script
    that asked for the channel head record the wrong build as the one it tested.
    """
    for keyword in LATEST_KEYWORDS:
        resolution = resolve_latest(keyword, None)
        assert resolution.target is None, f"{keyword} installed something anyway"
        assert "Nothing was installed" in resolution.detail
        assert "could not be read" in resolution.detail


def test_a_channel_the_manifest_does_not_carry_is_a_refusal_naming_it() -> None:
    manifest = _manifest(commit="NOT-A-SHA")  # the parser drops the beta row
    assert manifest.channel(CHANNEL_BETA) is None, "the premise: no usable beta row"

    resolution = resolve_latest("latest-beta", manifest)
    assert resolution.target is None
    assert "no usable beta entry" in resolution.detail
    # And the stable keyword is unaffected: one bad row hides only itself.
    assert resolve_latest("latest", manifest).target is not None


def test_a_commit_is_never_mistaken_for_a_keyword_and_never_fetches() -> None:
    """Adding keywords must not change what any existing argument means."""
    for commit in ("deadbee", PRODUCTION_TARGET_PIN, "", "list"):
        assert channel_for(commit) is None, commit

    fetched: list[str] = []

    def fetch(url: str) -> str:
        fetched.append(url)
        return json.dumps(_document())

    assert resolve_keyword("deadbee", fetch=fetch) is None
    assert fetched == [], "a commit argument read the network"

    resolution = resolve_keyword(" LATEST-Beta ", fetch=fetch)
    assert fetched, "a keyword did not read the manifest"
    assert resolution is not None and resolution.target is not None
    assert resolution.target.pin == _BETA_COMMIT


def test_the_keyword_and_the_gui_offer_name_the_same_build() -> None:
    """Two surfaces ask the manifest "what is the beta build?"; one answer.

    `evaluate_offer` is what the GUI's update check shows. If `latest-beta` read
    the channel some other way — "whichever row has the higher sequence", say —
    the offer and the command a script runs could install different builds while
    both claimed to be the beta channel's.
    """
    manifest = _manifest()
    offer = evaluate_offer(
        manifest, CHANNEL_BETA, installed_commit=fork_source.PRODUCTION_TARGET.pin
    )
    assert offer.verdict == OFFER_AVAILABLE, offer.detail
    resolution = resolve_latest("latest-beta", manifest)
    assert resolution.target is not None
    assert resolution.release == offer.release
    assert resolution.target.pin == offer.install_commit
