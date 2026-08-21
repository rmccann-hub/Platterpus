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


def test_the_build_under_review_makes_no_capability_claim() -> None:
    """The one-directional half, asserted so it is not "fixed" by a future reader.

    A build the fork has proposed but not published a flag table for has
    capabilities we do not know. `accepts_verify_log` is tri-state precisely so it
    can answer ``None`` instead of guessing, and round 12's pin is additionally
    one the fork's own policy says is not a release and must not be installed —
    so a capability row for it would describe a build nobody runs.

    The rows go in when it becomes a release or a declared test pin, at which
    point there is a published table to derive them from.
    """
    tag = f"{fork_source.FORK_BRANCH}-g{fork_source.PIN_UNDER_REVIEW}"
    assert tag not in fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG, (
        f"{tag} claims --verify-log support with no published flag table behind "
        f"it. Derive the row from the fork's P1 table when the pin becomes a "
        f"release; until then 'we do not know' is the honest answer and "
        f"accepts_verify_log() returning None is how it is said."
    )
    assert tag not in fork_source.BUILD_TAGS_ACCEPTING_CONSUMER_FLAG, (
        f"{tag} claims --consumer support with no published flag table behind it"
    )
    assert fork_source.accepts_verify_log(tag) is None, (
        f"accepts_verify_log({tag!r}) is "
        f"{fork_source.accepts_verify_log(tag)!r}, not None — an unknown build "
        f"must be not-determined, never False (which would invent evidence of "
        f"absence) and never True"
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