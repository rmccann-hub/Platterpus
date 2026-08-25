"""Which builds accept `--verify-log`, derived from their published tables.

## The finding this answers (round 7 lap 12, J4)

Our first log-verification classifier decided *"the flag was rejected"* versus
*"the log was rejected"* by matching cyanrip's error text. The fork's reply:

> *"please confirm that is the string your classifier keys on, or **better, that it
> keys on the exit code plus the flag's absence from our published table rather than
> on our wording**. Our wording there is genopt's, not ours, and it is one upstream
> sync from changing."*

They are right, and it is a mistake we have watched from the other side: a matcher
built on a dependency's prose is a hand-maintained list of shapes, which is what hid
16 of their fatal strings in round 5 and what put `merged` in our gap matcher for two
rounds. So `failed` now requires **positive evidence the build accepts the flag**,
and the evidence is their published flag table.

## Why the constant is checked against the documents

`fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG` is a literal set, because it is read at
runtime and `docs/` is not on the AppImage. A literal set is a hand-maintained list —
the exact thing the finding is about — so this file derives the expected membership
from the committed inbound tables and asserts agreement. The list may be hand-written;
it may not be hand-*maintained*.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.adapters import ripper_log_verify as rlv
from platterpus.adapters.tool_run import ToolRun
from platterpus.cyanrip_cli import VERIFY_LOG_FLAG
from platterpus.deps import fork_source

_REPO = Path(__file__).resolve().parent.parent
_INBOUND = _REPO / "docs" / "handshake" / "inbound"
_REAL_LOG = (
    _REPO
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)

#: A P1 flag row: ``| `-Y` | `--verify-log` | Verify a rip log's FUN512 checksum |``
_FLAG_ROW = re.compile(r"^\|\s*`(-[A-Za-z])`\s*\|\s*`(--[a-z-]+)`\s*\|", re.M)


def _rounds_publishing_the_flag() -> list[Path]:
    """Inbound files whose flag table lists ``--verify-log``."""
    found: list[Path] = []
    for path in sorted(_INBOUND.glob("round-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(long == VERIFY_LOG_FLAG for _short, long in _FLAG_ROW.findall(text)):
            found.append(path)
    return found


def test_the_flag_is_actually_published_by_them() -> None:
    """Floor, and the premise of the whole design.

    If no inbound round listed the flag we would have no basis for *any* build
    returning `True`, and every non-zero exit would be `not_determined` forever —
    which would pass every test below by making them vacuous.
    """
    rounds = _rounds_publishing_the_flag()
    assert len(rounds) >= 2, (
        f"only {[p.name for p in rounds]} publish {VERIFY_LOG_FLAG}; the support set "
        "has no documentary basis"
    )


def test_the_support_set_is_not_empty_and_holds_only_fork_tags() -> None:
    tags = fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG
    assert tags, "no build is recorded as accepting --verify-log"
    for tag in tags:
        assert tag.startswith(fork_source.FORK_BRANCH), (
            f"{tag!r} is not a fork build tag. Only builds a published table "
            "describes belong here; stock upstream is 'unknown', not 'yes'."
        )


def test_no_published_table_has_ever_withdrawn_the_flag() -> None:
    """The documentary basis, stated as continuity rather than as one citation.

    The support set's justification is not *"round 4 listed it"* — it is that **every
    flag table either side has published since then still lists it, and none has
    withdrawn it.** That is the claim that makes covering later pins legitimate, and
    it is fully derivable from the committed files.

    This is the shape the `-V` finding taught: a contract line is true *for a range
    of builds*, and citing one snapshot is how *"`-v` is version; there is no `-V`"*
    came to be quoted long after it stopped being the whole truth.
    """
    tables = [
        p
        for p in sorted(_INBOUND.glob("round-*.md"))
        if len(_FLAG_ROW.findall(p.read_text(encoding="utf-8", errors="replace"))) >= 20
    ]
    assert len(tables) >= 3, (
        f"only {[p.name for p in tables]} carry a real flag table (>=20 rows); with "
        "fewer than three there is no continuity to check"
    )
    missing = [
        p.name
        for p in tables
        if VERIFY_LOG_FLAG
        not in {
            long
            for _short, long in _FLAG_ROW.findall(
                p.read_text(encoding="utf-8", errors="replace")
            )
        }
    ]
    assert not missing, (
        f"{missing} publish a flag table that does NOT list {VERIFY_LOG_FLAG}. The "
        "support set assumes the flag has never been withdrawn; that assumption is "
        "now false and every listed build needs re-checking."
    )


def test_every_fork_pin_we_know_about_is_in_the_support_set() -> None:
    """Coverage, one-directional, with the reason for the direction.

    A MISSING tag silently downgrades a real `failed` to `not_determined` and the
    check goes quiet — the failure mode that matters. An extra tag cannot cause a
    false accusation on its own, because reaching `failed` still needs a non-zero
    exit from that build.

    Every pin here post-dates round 4, and the test above establishes that no
    published table has withdrawn the flag since — so "every fork pin" is the correct
    scope rather than an over-reach.
    """
    pins = {
        "FORK_PIN": fork_source.FORK_PIN,
        "FORK_RELEASE_4_COMMIT": fork_source.FORK_RELEASE_4_COMMIT,
        "FORK_TEST_PIN": fork_source.FORK_TEST_PIN,
        # **The pin under review is the build the rig is actually running**, and it
        # was missing from this population until 2026-08-25 — so the one build being
        # exercised on hardware was the one build this coverage check could not see.
        # It is not a hypothetical: the 2026-08-24 cancelled rip's audit reported
        # *"we cannot establish that this build accepts --verify-log"*, which is the
        # silent downgrade this test's docstring names as the failure mode that
        # matters. A floor of ">= 4" passed the whole time, over four pins that were
        # not the one in use — a population, not a logic, defect.
        "PIN_UNDER_REVIEW": fork_source.PIN_UNDER_REVIEW,
        **{
            f"SUPERSEDED_TEST_PINS[{i}]": pin
            for i, pin in enumerate(fork_source.SUPERSEDED_TEST_PINS)
        },
    }
    named = {name: pin for name, pin in pins.items() if pin}
    assert len(named) >= 4, f"only {len(named)} pins to check: {named}"
    assert "PIN_UNDER_REVIEW" in named or not fork_source.PIN_UNDER_REVIEW, (
        "PIN_UNDER_REVIEW is set but dropped out of the checked population — the "
        "build on the rig must never be the one this check cannot see"
    )

    tags = {t.casefold() for t in fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG}
    for name, pin in named.items():
        tag = f"{fork_source.FORK_BRANCH}-g{pin}".casefold()
        assert tag in tags, (
            f"{name} ({pin}) is absent from BUILD_TAGS_ACCEPTING_VERIFY_LOG. A "
            "non-zero exit from that build would be downgraded to 'not determined', "
            "so the log-integrity check would go silent on it."
        )
        assert fork_source.accepts_verify_log(tag) is True, name


def test_the_support_lookup_and_the_set_cannot_disagree() -> None:
    """The function is the only sanctioned reader of the set.

    A second membership test spelled differently at a call site is how two
    descriptions of one fact start to drift.
    """
    for tag in fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG:
        assert fork_source.accepts_verify_log(tag) is True, tag
        assert fork_source.accepts_verify_log(tag.upper()) is True, (
            f"{tag}: the lookup is case-sensitive, so a banner that differs only in "
            "case would be treated as an unknown build"
        )


# --- the tri-state itself -----------------------------------------------------


def test_a_listed_build_is_true_and_tolerates_dirty() -> None:
    tag = fork_source.FORK_TEST_BUILD_TAG
    assert fork_source.accepts_verify_log(tag) is True
    assert fork_source.accepts_verify_log(f"{tag}-dirty") is True, (
        "a dirty build of a listed commit still has the flag"
    )


@pytest.mark.parametrize("tag", ["", "   ", "release", "platterpus-fork-gdeadbee"])
def test_an_unrecognised_build_is_none_never_false(tag: str) -> None:
    """`None`, not `False`. No document says any cyanrip LACKS the flag.

    Claiming absence would be inventing evidence — the same discipline as
    `not_determined` versus `unapproved` in the handshake approval.
    """
    assert fork_source.accepts_verify_log(tag) is None


# --- the classifier, keyed on the build rather than on their prose -------------


def _runner(exit_code: int | None, output: str = "", started: bool = True):
    def _call(argv: list[str]) -> ToolRun:
        return ToolRun(
            exit_code=exit_code, output=output, argv=tuple(argv), started=started
        )

    return _call


def test_failed_requires_a_build_we_know_accepts_the_flag() -> None:
    """The J4 fix. A non-zero exit alone is no longer enough to accuse the log."""
    known = fork_source.FORK_TEST_BUILD_TAG
    hit = rlv.verify_rip_log(
        _REAL_LOG, build_tag=known, runner=_runner(1, "Log checksum mismatch!")
    )
    assert hit.verdict == rlv.FAILED

    for unknown in ("", "release", "platterpus-fork-gdeadbee"):
        shrug = rlv.verify_rip_log(
            _REAL_LOG, build_tag=unknown, runner=_runner(1, "Log checksum mismatch!")
        )
        assert shrug.verdict == rlv.NOT_DETERMINED, unknown
        assert "cannot establish" in shrug.detail, unknown


def test_their_wording_is_no_longer_what_decides_it() -> None:
    """The property they asked us to confirm, asserted as behaviour.

    Their error string is genopt's and may change. So: with a KNOWN build, the
    verdict must be `failed` for a non-zero exit whatever the text says — including
    text we have never seen — and with an UNKNOWN build it must be `not_determined`
    whatever the text says. The output must not be able to flip either answer.
    """
    known = fork_source.FORK_TEST_BUILD_TAG
    novel_wordings = (
        "",
        "some future genopt phrasing nobody has written yet",
        "Log checksum mismatch!",
        "error: bad checksum",
    )
    for text in novel_wordings:
        assert (
            rlv.verify_rip_log(
                _REAL_LOG, build_tag=known, runner=_runner(1, text)
            ).verdict
            == rlv.FAILED
        ), f"known build flipped on output {text!r}"
        assert (
            rlv.verify_rip_log(
                _REAL_LOG, build_tag="release", runner=_runner(1, text)
            ).verdict
            == rlv.NOT_DETERMINED
        ), f"unknown build flipped on output {text!r}"


def test_the_wording_belt_can_still_only_soften_never_accuse() -> None:
    """The kept substring match may reach `not_determined`, never `failed`.

    A build we believe supports the flag but which says it does not is telling us our
    table is wrong; the safe reading of that disagreement is still "not determined",
    and the message says the table needs re-checking rather than blaming the log.
    """
    result = rlv.verify_rip_log(
        _REAL_LOG,
        build_tag=fork_source.FORK_TEST_BUILD_TAG,
        runner=_runner(1, "Unable to parse command line argument: --verify-log"),
    )
    assert result.verdict == rlv.NOT_DETERMINED
    assert "re-check" in result.detail or "needs re-checking" in result.detail


def test_exit_zero_needs_no_table_entry() -> None:
    """A build that answered 0 demonstrably has the flag.

    Requiring the table here would refuse a *successful* verification from stock
    cyanrip, which is the fail-safe rule applied in the wrong direction: it would
    discard evidence rather than avoid inventing it.
    """
    for tag in ("", "release", fork_source.FORK_TEST_BUILD_TAG):
        assert (
            rlv.verify_rip_log(_REAL_LOG, build_tag=tag, runner=_runner(0)).verdict
            == rlv.VERIFIED
        ), tag


def test_the_cyanrip_backend_supplies_a_build_tag() -> None:
    """A `build_tag` parameter nothing passes is the ABC-no-op defect again.

    `verify_log` must read the tag off the ripper's own banner — provenance derivable
    from the artifact — or every real rip lands on the unknown branch and `failed`
    becomes unreachable in production while every test here still passes.
    """
    import inspect

    from platterpus.adapters import cyanrip_backend

    source = inspect.getsource(cyanrip_backend.CyanripImpl.verify_log)
    assert "build_tag" in source, (
        "CyanripImpl.verify_log does not pass a build_tag, so no real rip can ever "
        "reach the 'failed' verdict"
    )
    assert hasattr(cyanrip_backend.CyanripImpl, "_observed_build_tag")
