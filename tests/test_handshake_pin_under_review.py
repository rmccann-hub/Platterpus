"""``PIN_UNDER_REVIEW`` must track the newest inbound handshake round.

**Why this file exists.** The constant it guards spent five rounds at a
round-7 value, with the comment above it still reading *"round 7 is open"*. The
consequence was not a crash: `handshake_approval._why_this_build_is_here`
returned an empty string for the build under review, so a rip against it reported
a bare *"NOT the build this Platterpus was verified against"* with no reason —
which is the *"every word accurate, and the user is left thinking something
broke"* shape that function was written to remove. The mechanism worked
throughout; its input had rotted.

`CLAUDE.md`: *a comment where a check belongs is not a fix*, and a value that
goes stale invisibly needs a sweep. The value has to be a constant rather than a
runtime read, because ``docs/`` is not shipped inside an AppImage — so the check
is a test that derives the expected value from the committed round files and
refuses a constant that lags them. Same pattern as
``tests/test_verify_log_support.py``, which derives its capability set from the
committed inbound flag tables rather than trusting a hand-kept list.

**It is deliberately one-directional about capabilities.** The pin an open round
*proposes* is not a build whose flags we have been handed a table for, so it must
NOT appear in either capability set — the tri-state exists to answer "we do not
know" rather than guess. That absence is asserted here too, because it is the
half a future reader is most likely to "fix" by adding a row.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

from platterpus.deps import fork_source

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_INBOUND: Final[Path] = _REPO_ROOT / "docs" / "handshake" / "inbound"

#: ``HANDSHAKE-PIN: <commit>`` at column 0 of a round file's wire header. Anchored
#: to a line start and to the exact key, because ``HANDSHAKE-PIN-POLICY:`` is a
#: different (prose) field that shares the prefix — a substring match would read
#: the policy paragraph and find whatever commit it mentions first.
_PIN_LINE: Final[re.Pattern[str]] = re.compile(
    r"^HANDSHAKE-PIN:[ \t]*([0-9a-f]{7,40})\b", re.MULTILINE
)

#: Rounds before the wire header existed. Their files carry no ``HANDSHAKE-PIN:``
#: and are not evidence about the current pin either way.
_PRE_HEADER: Final[frozenset[str]] = frozenset(
    {"round-2.md", "round-3.md", "round-4.md", "round-5.md"}
)


def _round_lap(path: Path) -> tuple[int, int]:
    """``(round, lap)`` from a filename, for ordering. Unparsed sorts first."""
    match = re.search(r"round-0*(\d+)(?:-lap-0*(\d+))?", path.name)
    if match is None:
        return (-1, -1)
    return (int(match.group(1)), int(match.group(2) or 0))


def _inbound_rounds() -> list[Path]:
    """Every inbound round file, oldest first. Excludes the superseded folder."""
    return sorted(
        (
            p
            for p in _INBOUND.glob("round-*.md")
            if p.is_file() and p.name not in _PRE_HEADER
        ),
        key=_round_lap,
    )


def test_there_are_inbound_rounds_with_wire_headers() -> None:
    """The floor. Without it a glob that matched nothing would pass every
    assertion below, and this file would be decoration — which is precisely the
    failure mode it was written to prevent, so it does not get to have it."""
    rounds = _inbound_rounds()
    assert len(rounds) >= 5, f"only found {[p.name for p in rounds]}"
    with_pins = [p for p in rounds if _PIN_LINE.search(p.read_text(encoding="utf-8"))]
    assert len(with_pins) >= 3, (
        f"only {len(with_pins)} inbound rounds declare a HANDSHAKE-PIN, so the "
        f"derivation below has almost nothing to derive from: "
        f"{[p.name for p in with_pins]}"
    )


def test_the_pin_under_review_matches_the_newest_inbound_round() -> None:
    """**The check that would have caught five rounds of staleness.**

    Reads the newest inbound round file's own ``HANDSHAKE-PIN:`` header and
    compares it to the constant. Derived from the artifact, not from anyone's
    memory of it — `CLAUDE.md`: *when a committed artifact can settle a question,
    the test should read the artifact.*
    """
    newest = next(
        (
            path
            for path in reversed(_inbound_rounds())
            if _PIN_LINE.search(path.read_text(encoding="utf-8"))
        ),
        None,
    )
    assert newest is not None, "no inbound round declares a HANDSHAKE-PIN"
    match = _PIN_LINE.search(newest.read_text(encoding="utf-8"))
    assert match is not None  # guarded by the generator above
    declared = match.group(1)

    assert fork_source.PIN_UNDER_REVIEW.casefold() == declared.casefold(), (
        f"PIN_UNDER_REVIEW is {fork_source.PIN_UNDER_REVIEW!r} but the newest "
        f"inbound round ({newest.name}) proposes {declared!r}.\n\n"
        f"Update the constant in src/platterpus/deps/fork_source.py. Do NOT also "
        f"add it to BUILD_TAGS_ACCEPTING_CONSUMER_FLAG or "
        f"BUILD_TAGS_ACCEPTING_VERIFY_LOG — see the next test for why.\n\n"
        f"When this is stale, `handshake_approval._why_this_build_is_here` returns "
        f"an empty string for the build under review, so a rip against it reports "
        f"'NOT the build this Platterpus was verified against' with no reason at "
        f"all."
    )


def test_a_capability_claim_for_the_build_under_review_is_backed_by_a_table() -> None:
    """A capability row needs a PUBLISHED FLAG TABLE behind it — checked, not assumed.

    **This replaces a test that asserted the pin under review claims no
    capability at all**, and the replacement is that test's own escape clause
    firing for the first time. Its docstring said the rows *"go in when it becomes
    a release or a declared test pin, at which point there is a published table to
    derive them from."* Round 14's pin is a release (`release_seq` 20, the `beta`
    channel resolves to it) and the fork ships a generated flag table with every
    lap, so both halves of that condition are met.

    Keeping the old assertion would have kept a real defect: the 2026-08-24 rig
    run produced **nine rips, every one logging** `Consumer: not identified (no
    --consumer given)` — in the round whose entire subject is provenance on a
    released pair — because `--consumer` is gated on a set the under-review build
    was forbidden from joining.

    So the property moves from *"make no claim"* to *"make no UNBACKED claim"*,
    and it is checked against the **artifact**: the newest provider contract filed
    under `docs/handshake/inbound/artifacts/` must actually list the flag. That is
    stronger than the rule it replaces — the old one could only ever say "not
    yet", and this one fails if we invent a capability the fork never published.

    Tri-state is untouched: a build absent from a set still answers
    ``not determined`` rather than ``False``.
    """
    contracts = sorted(
        (_REPO_ROOT / "docs" / "handshake" / "inbound" / "artifacts").glob(
            "*provider-contract*.md"
        )
    )
    assert contracts, "no provider contract is filed — this check measures nothing"
    published = contracts[-1].read_text(encoding="utf-8")

    tag = f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}"
    claims = {
        "--consumer": tag in fork_source.BUILD_TAGS_ACCEPTING_CONSUMER_FLAG,
        "--verify-log": tag in fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG,
    }
    assert any(claims.values()), (
        f"{tag} is the pin under review and claims NO capability at all. That was "
        f"correct while the fork had published no flag table for it; "
        f"{contracts[-1].name} is one. A build we install and rip with should "
        f"have its capabilities derived from it."
    )
    for flag, claimed in claims.items():
        if not claimed:
            continue  # not claiming it is always honest
        assert f"`{flag}`" in published, (
            f"{tag} claims {flag} support, but {contracts[-1].name} — the newest "
            f"provider contract we hold — does not list it. A capability row must "
            f"be derived from their published table, never from ours."
        )


def test_the_durable_release_constant_is_still_a_capability_member() -> None:
    """The other side of the split, so it cannot be lost in the shuffle.

    ``FORK_RELEASE_4_COMMIT`` and ``PIN_UNDER_REVIEW`` were one constant until
    2026-08-21. Release 4 has a published flag table listing both flags, which is
    a permanent fact about that build; it must stay in both sets. If a rename ever
    drops it, a non-zero exit from that build silently downgrades to
    ``not_determined`` and the log-integrity check goes quiet on it.
    """
    tag = f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_RELEASE_4_COMMIT}"
    assert tag in fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG, tag
    assert tag in fork_source.BUILD_TAGS_ACCEPTING_CONSUMER_FLAG, tag
    assert fork_source.accepts_verify_log(tag) is True, tag
    assert fork_source.FORK_RELEASE_4_COMMIT != fork_source.PIN_UNDER_REVIEW, (
        "the two constants hold the same value, so the split that separated a "
        "durable capability fact from a per-round transient has been undone"
    )


@pytest.mark.parametrize("attribute", ["PIN_UNDER_REVIEW", "FORK_RELEASE_4_COMMIT"])
def test_both_constants_look_like_commits(attribute: str) -> None:
    """Cheap, and it catches the paste that lands a whole banner in a pin field."""
    value = getattr(fork_source, attribute)
    assert re.fullmatch(r"[0-9a-f]{7,40}", value), (
        f"{attribute} is {value!r}, which is not a bare commit hash. The build "
        f"tags below are composed as f'{{FORK_BRANCH}}-g{{{attribute}}}', so "
        f"anything else silently produces a tag no build prints."
    )


def test_the_under_review_pin_and_version_are_one_pairing_from_one_lap() -> None:
    """**The relation, which no test of either constant alone can express.**

    `PIN_UNDER_REVIEW` had a checker (above). `UNDER_REVIEW_TARGET.version` had
    none, so on 2026-09-01 the pin rolled to `978f9b0` while the version beside it
    still read `0.9.4-rc2+platterpus.10` — round 14's. Every field was individually
    defensible and the pairing named a build that has never existed, which is the
    2026-08-18 mis-pairing shape exactly: *the channel head's version rendered
    against the installed commit, every field true, the sentence false.*

    It is not cosmetic. That version string is what `--install-ripper` and the
    setup wizard label the build they compile, and what the handshake skeleton
    puts in `HANDSHAKE-RIPPER-VERSION` beside `HANDSHAKE-PIN` — so the seam would
    have carried a banner-and-pin combination no binary prints.

    Both halves are derived from the SAME inbound lap here, because reading them
    from two places is how they came apart.
    """
    newest = next(
        (
            path
            for path in reversed(_inbound_rounds())
            if _PIN_LINE.search(path.read_text(encoding="utf-8"))
        ),
        None,
    )
    assert newest is not None, "no inbound round declares a HANDSHAKE-PIN"
    text = newest.read_text(encoding="utf-8")

    pin_match = _PIN_LINE.search(text)
    assert pin_match is not None
    declared_pin = pin_match.group(1)

    # `HANDSHAKE-RIPPER-VERSION: cyanrip <version> (<build tag>)` — the pairing as
    # THEY state it, which is the artifact this project treats as authoritative.
    banner = re.search(
        r"^HANDSHAKE-RIPPER-VERSION:[ \t]*cyanrip[ \t]+(?P<version>\S+)"
        r"[ \t]*\((?P<tag>[^)]+)\)",
        text,
        re.MULTILINE,
    )
    assert banner is not None, (
        f"{newest.name} declares no parseable HANDSHAKE-RIPPER-VERSION, so this "
        f"check has nothing to derive the pairing from"
    )

    target = fork_source.UNDER_REVIEW_TARGET
    assert target.pin.casefold() == declared_pin.casefold(), (
        f"UNDER_REVIEW_TARGET.pin is {target.pin!r} but {newest.name} declares "
        f"{declared_pin!r}"
    )
    assert target.version == banner.group("version"), (
        f"UNDER_REVIEW_TARGET.version is {target.version!r} but {newest.name} "
        f"declares {banner.group('version')!r} for that same pin. The two fields "
        f"name ONE build; a version rendered against a different commit is the "
        f"mis-pairing this test exists to refuse."
    )
    # And the tag they print must be the one we compose, or the acceptance run's
    # `expect-ripper-under-review` compares against a string no build emits.
    assert banner.group("tag").strip() == f"{fork_source.FORK_BRANCH}-g{target.pin}", (
        f"we would compose {fork_source.FORK_BRANCH}-g{target.pin!r} but they "
        f"print {banner.group('tag').strip()!r}"
    )
