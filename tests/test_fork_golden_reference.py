"""The fork's golden reference log must parse with nothing left over.

`tests/fixtures/cyanrip_fork_golden_reference.log` is byte-exact output from the
cyanrip fork at its current pin, delivered in handshake round 4 (Appendix 1).
Verifying a handshake is not reading the other side's file — it is running their
artifact through our real parser and checking what comes out.

Doing exactly that on this round's log found three things a read-through did not:

* `Total time: 00:08.00` fell through as unrecognised, because our pattern
  demanded `HH:MM:SS` and the fork prints `MM:SS.ff` for a short disc. The
  disc's duration was silently absent.
* `Invoked as:` — a line **we asked them to add** (A3) — had no parser, so the
  argv the ripper actually received went straight into the unrecognised bucket.
* `Rip completed:  yes (3 of 3 tracks)` likewise. That footer is the ripper's
  own completion verdict *with its own denominator*, and the fork confirms
  (Q10) it is the only structural difference between a truncated log and a
  short one — the cue cannot tell you it was cut.

The file is deliberately **not** byte-compared. The fork flagged six fields that
vary by environment and run (`Invoked as:` path, `creation_time:`,
`Ripping finished at`, `Log FUN512:`, `Extraction speed:`, `Elapsed:`). Pinning
the whole file would fail on their machine and teach us to regenerate the
fixture until it passed. We pin the lines we parse.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.ripper_identity import identify_ripper

_GOLDEN = Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference.log"


@pytest.fixture(scope="module")
def parsed():  # type: ignore[no-untyped-def]  # a RipLog; annotating drags the import in
    return parse_cyanrip_log(_GOLDEN.read_text(encoding="utf-8"))


def test_the_fixture_is_the_whole_log() -> None:
    """A floor. Every assertion below is "the parse contains X", which a
    truncated or mis-extracted fixture could satisfy while hiding the rest."""
    text = _GOLDEN.read_text(encoding="utf-8")
    assert text.startswith("cyanrip 0.9.4-rc1 (platterpus-fork-")
    assert "Log FUN512:" in text, "the fixture is missing the log's footer"
    assert len(text.splitlines()) >= 200


def test_no_top_level_line_goes_unrecognised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The load-bearing test of the whole round.

    The parser logs a DEBUG line naming every top-level line it neither parsed
    nor has on its documented ignore list. An entry there is a fact the fork
    emitted and we dropped on the floor — which is how `Total time:`,
    `Invoked as:` and `Rip completed:` were found. Zero is the only acceptable
    number, and the message is asserted on so a rename cannot make this pass by
    finding nothing.
    """
    with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
        parse_cyanrip_log(_GOLDEN.read_text(encoding="utf-8"))
    unrecognised = [r for r in caplog.records if "unrecognised top-level" in r.message]
    assert not unrecognised, (
        "the fork emits lines we neither parse nor deliberately ignore: "
        + "; ".join(str(r.args) for r in unrecognised)
    )


def test_the_build_identifies_as_our_fork(parsed) -> None:  # type: ignore[no-untyped-def]
    identity = identify_ripper(parsed.log_creator, parsed.ripper_build)
    assert identity.kind == "fork"
    assert identity.is_fork is True
    assert "platterpus-fork" in parsed.ripper_build


def test_the_three_pregap_cases_survive_the_round_trip(parsed) -> None:  # type: ignore[no-untyped-def]
    """The cases the fork built this fixture to carry, and the ones our
    convention argument was about."""
    tracks = {t.number: t for t in parsed.tracks}
    assert len(tracks) == 3

    # Track 1: lead-in 150 + declared TOC 150. The EAC-comparable figure — see
    # tests/test_eac_pregap_convention.py for why the stated value wins here.
    assert tracks[1].pregap_length_frames == 300
    assert tracks[1].pregap_sectors == 300
    assert tracks[1].pregap_source == "TOC"

    # Track 2: TOC only, and the two derivations agree.
    assert tracks[2].pregap_sectors == 75
    assert tracks[2].start_sector - tracks[2].pregap_start_lsn == 75

    # Track 3: tried, could not tell. NOT zero, NOT absent.
    assert tracks[3].pregap_state == "unknown"
    assert tracks[3].pregap_unknown_reason == "sub-channel unreadable"
    assert tracks[3].pregap_sectors is None


def test_the_argv_the_ripper_received_is_captured(parsed) -> None:  # type: ignore[no-untyped-def]
    """`Invoked as:` — our A3 ask, delivered. The counterpart to the argv we
    record spawning it with; the gap between the two is where a wrapper or the
    Distrobox host-export mangles an argument, invisible from either end alone.
    """
    assert parsed.invoked_as
    assert "-N" in parsed.invoked_as, "the ripper reports being run without -N"
    assert parsed.invoked_as.startswith("/"), "expected an absolute program path"


def test_the_rippers_own_completion_verdict_is_captured(parsed) -> None:  # type: ignore[no-untyped-def]
    """With its own denominator — the number our verdict should be measured
    against, recorded rather than recomputed from `len(tracks)`
    (docs/testing.md §5.n)."""
    assert parsed.rip_completed is True
    assert parsed.rip_completed_tracks == 3
    assert parsed.rip_completed_total == 3
    assert not parsed.log_truncated


def test_a_log_without_the_footer_reports_unknown_not_false(parsed) -> None:  # type: ignore[no-untyped-def]
    """Tri-state, at the field that most invites collapsing.

    A killed rip's log simply lacks the footer. `None` says "the ripper never
    got to tell us"; `False` would say "it finished and reported failure".
    Those need different messages to the user, and conflating them is the bug
    shape this project has now shipped three times.
    """
    text = _GOLDEN.read_text(encoding="utf-8")
    killed = text[: text.index("Rip completed:")]
    assert parse_cyanrip_log(killed).rip_completed is None


def test_the_disc_duration_parses_in_the_short_form(parsed) -> None:  # type: ignore[no-untyped-def]
    """`MM:SS.ff`, which the original `HH:MM:SS` pattern missed entirely."""
    assert parsed.disc_duration == "00:08.00"


# --- the cancelled form, which their golden reference cannot show -------------


def test_the_cancelled_rip_footer_keeps_its_counts() -> None:
    """The case the whole cancelled-rip effort is about.

    Their golden reference is a *successful* rip, so it carries only
    `Rip completed:  yes (3 of 3 tracks)`. The fork's generated **P2 table**
    (`cyanrip_log.c:420`) revealed a second shape:

        Rip completed:  no (interrupted by user, 2 of 3 tracks)

    My first pattern handled only the `yes` shape, so a cancelled rip parsed as
    `verdict='no'` and **silently dropped "2 of 3"** — the ripper's own count,
    for the exact scenario where our own count is least trustworthy. No fixture
    could have caught this; only their contract could. That is what a provider
    contract is for.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)\n"
        "Rip completed:  no (interrupted by user, 2 of 3 tracks)\n"
    )
    assert log.rip_completed is False
    assert log.rip_completed_tracks == 2
    assert log.rip_completed_total == 3
    assert log.rip_completed_reason == "interrupted by user"


def test_a_bare_no_without_counts_still_parses() -> None:
    """Defensive: the verdict survives even if the parenthetical is absent,
    and the counts stay None rather than becoming 0."""
    log = parse_cyanrip_log("cyanrip 0.9.4 (platterpus-fork-g1)\nRip completed:  no\n")
    assert log.rip_completed is False
    assert log.rip_completed_tracks is None


@pytest.mark.parametrize(
    ("line", "state", "reason"),
    [
        (
            "    Pregap LSN:  unknown (sub-channel unreadable)",
            "unknown",
            "sub-channel unreadable",
        ),
        (
            "    Pregap LSN:  unknown (sub-channel CRC mismatches)",
            "unknown",
            "sub-channel CRC mismatches",
        ),
        ("    Pregap LSN:  none", "none", ""),
        ("    Pregap LSN:  150 (duration: 00:02.00)", "known", ""),
    ],
)
def test_every_pregap_outcome_in_their_contract_is_distinguished(
    line: str, state: str, reason: str
) -> None:
    """All four outcomes their P2 table lists, including the CRC-mismatch
    variant that no fixture we hold has ever contained.

    The three `unknown`/`none` rows are the ones that must not collapse into
    each other: "tried and the sub-channel was unreadable", "tried and the CRCs
    disagreed", and "measured, there is no gap" are three different archival
    claims and this log is signed.
    """
    log = parse_cyanrip_log(
        "cyanrip 0.9.4 (platterpus-fork-g1)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  Properties:\n"
        f"{line}\n"
        "    Start LSN:   150\n"
    )
    track = log.tracks[0]
    assert track.pregap_state == state
    assert track.pregap_unknown_reason == reason


@pytest.mark.parametrize(
    "source", ["TOC", "lead-in", "sub-channel (not signalled by TOC)"]
)
def test_every_pregap_source_in_their_contract_parses(source: str) -> None:
    """`lead-in` and the sub-channel form are in their P2 table and in no
    fixture we hold. A source we fail to parse becomes an empty string, which
    the report would render as "provenance unknown" for a gap whose provenance
    the ripper stated plainly."""
    log = parse_cyanrip_log(
        "cyanrip 0.9.4 (platterpus-fork-g1)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  Properties:\n"
        "    Pregap LSN:  150 (duration: 00:02.00)\n"
        f"    Pregap source: {source}\n"
        "    Start LSN:   300\n"
    )
    assert log.tracks[0].pregap_source == source
