"""A ripper that diagnosed the failure precisely, and a user shown "Rip failed."

The rig hit this for real (2026-08-02): a 16-track disc, a MusicBrainz medium
listing 18, `-t 17=` handed to cyanrip. It answered

    Invalid track number 17, list has 16 tracks!

and exited 1 in two seconds with nothing ripped. The sentence was in our
captured output the whole time. The report's ``failure_hint`` was ``null`` and
the window said "Rip failed."

That one *was* matched by the original pattern. The cyanrip fork session then
enumerated the ripper's fatal log call sites and measured that the six prefixes
we had covered **24 of 45** — so the same silent-failure shape was live for the
other 21, waiting on whichever one a user hit first.

The judgement recorded here, because the original narrowness was a considered
choice and it was the wrong one: a **miss** costs a user staring at "Rip failed"
with the answer in a buffer we already captured; a **false positive** costs one
extra sentence of the ripper's own words, on a rip that has already failed.
Those are not comparable, so the pattern is broad on purpose.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.workers.rip_worker import _RIPPER_ERROR_PREFIXES, _RIPPER_ERROR_RE

# Real cyanrip fatal lines. Every one of these ends a rip before or during
# audio extraction, so surfacing it verbatim is strictly better than "Rip
# failed." Sourced from the fork session's enumeration of cyanrip's fatal
# `cyanrip_log` call sites plus the strings the rig has actually produced.
_FATAL_LINES: tuple[str, ...] = (
    "Invalid track number 17, list has 16 tracks!",
    "Invalid offset value!",
    "Unable to open device /dev/sr0!",
    "Unable to read disc TOC!",
    "Unable to init cover art!",
    "Missing track number in -t!",
    "Missing argument for -o!",
    "No device specified and none found!",
    "No disc inserted?",
    "No cover art file specified!",
    "No tracks selected!",
    "Error reading sector 12345!",
    "Error initializing encoder!",
    "Errors were encountered, stopping!",
    "Failed to allocate output context!",
    "Failed to open output file!",
    "Couldn't open file for writing!",
    "Could not set drive speed!",
    "Cannot use -l with -I!",
    "Unsupported output format!",
    "Unknown option -q!",
    "Unrecognized sample format!",
    "Stopping, disc read error!",
    "Stopping after 3 errors!",
    "Aborting rip!",
    "Drive media changed, stopping!",
    "Insufficient memory for track buffer!",
    "Out of memory!",
    "Fatal error, cannot continue!",
)

# Lines that must NOT be treated as fatal. Some are near-misses on purpose: a
# pattern that swallowed these would turn a healthy rip's ordinary chatter into
# a scary hint.
_BENIGN_LINES: tuple[str, ...] = (
    "Track 1 ripped and encoded successfully!",
    "No errors were encountered.",  # begins with "No", not "No device"/"No disc"
    "Errorless read confirmed",  # "Error" without the boundary
    "Invalidated cache entry",  # "Invalid" without the boundary
    "Missingno is a great track title",  # "Missing" without the boundary
    "Disc tracks:    16",
    "Accurip: disabled",
    "  Error reading sector 5",  # indented: not a top-level fatal line
    "progress - 41.65%",
    "",
)


@pytest.mark.parametrize("line", _FATAL_LINES)
def test_every_known_fatal_line_is_recognised(line: str) -> None:
    assert _RIPPER_ERROR_RE.match(line), (
        f"would be shown as a bare 'Rip failed': {line}"
    )


@pytest.mark.parametrize("line", _BENIGN_LINES)
def test_ordinary_output_is_not_mistaken_for_a_fatal_error(line: str) -> None:
    assert not _RIPPER_ERROR_RE.match(line), f"benign line flagged as fatal: {line}"


def test_the_boundary_is_a_real_boundary() -> None:
    """`Invalid` must not match `Invalidated`. Without the `(?:\\s|$)` this is a
    bare prefix match and every near-miss above starts firing."""
    assert _RIPPER_ERROR_RE.match("Invalid offset")
    assert not _RIPPER_ERROR_RE.match("Invalidated")
    assert _RIPPER_ERROR_RE.match("Invalid")  # a bare word IS the whole line


def test_the_sample_is_large_and_varied_enough_to_conclude_from() -> None:
    """Floors. "every line in the list matches" is satisfied by an empty list,
    and "the prefixes are covered" is satisfied by one prefix used 29 times."""
    assert len(_FATAL_LINES) >= 25
    assert len(_BENIGN_LINES) >= 8
    exercised = {
        prefix
        for prefix in _RIPPER_ERROR_PREFIXES
        if any(line.startswith(prefix) for line in _FATAL_LINES)
    }
    assert len(exercised) >= 18, (
        f"only {len(exercised)} of {len(_RIPPER_ERROR_PREFIXES)} prefixes have a "
        "sample line; an unexercised prefix is an untested claim"
    )


def test_a_pathological_line_is_bounded() -> None:
    """The hint reaches a QMessageBox, and the pattern reaches a regex engine.
    Neither should be handed a megabyte because a ripper went haywire."""
    assert not _RIPPER_ERROR_RE.match("Invalid " + "x" * 100_000)
    # ...while a realistically long diagnosis still matches.
    assert _RIPPER_ERROR_RE.match("Invalid " + "x" * 150)


def test_the_widening_actually_widened() -> None:
    """Revert-proof in code: the six original prefixes covered a minority of the
    sample. If someone narrows this back, the count check fails loudly rather
    than the coverage silently regressing.
    """
    original = (
        "Invalid ",
        "Unable to ",
        "Missing ",
        "No device ",
        "Error reading ",
        "Stopping, ",
    )
    covered_before = sum(1 for line in _FATAL_LINES if line.startswith(original))
    covered_now = sum(1 for line in _FATAL_LINES if _RIPPER_ERROR_RE.match(line))
    assert covered_now == len(_FATAL_LINES)
    assert covered_before < covered_now, (
        "this sample no longer demonstrates the gap the widening closed"
    )


# --- the fork's OWN generated inventory, all 88 --------------------------------


_INVENTORY = Path(__file__).parent / "fixtures" / "cyanrip_fatal_messages.tsv"


def _inventory() -> list[tuple[str, str]]:
    """(source location, message) for every fatal string the fork can print.

    Read from the committed fixture, which is the fork's own mechanically
    generated list (handshake round 4, Appendix 2) — not a list we imagined.
    A description derived from their behaviour cannot describe behaviour they
    do not have, which is the whole reason the contract is exchanged.
    """
    rows: list[tuple[str, str]] = []
    for line in _INVENTORY.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or "\t" not in line:
            continue
        where, message = line.split("\t", 1)
        rows.append((where, message))
    return rows


def test_every_string_the_ripper_can_print_is_surfaced() -> None:
    """All 88. The fork predicted 87/88 and named the miss; we re-measured
    rather than taking their word, got the same one, and closed it."""
    rows = _inventory()
    assert len(rows) >= 80, f"inventory collapsed to {len(rows)} strings"
    missed = [(w, m) for w, m in rows if not _RIPPER_ERROR_RE.match(m)]
    assert not missed, "would render as a bare 'Rip failed': " + "; ".join(
        f"{w} {m}" for w, m in missed
    )


def test_the_hyphen_prefixed_string_is_the_one_that_needed_a_special_case() -> None:
    """Pins WHY `-J` is in the prefix list, so a tidy-up does not remove it.

    It begins with a hyphen, so no word prefix can reach it. It is also the
    reason the entry is `-J` and not `-J ` — with the trailing space the
    boundary would have to match the `(` that follows, and does not. The
    fixture caught that; reading the list would not have.
    """
    line = "-J (only generate a CUE sheet) cannot be used with -I (only print info)!"
    assert line in [m for _, m in _inventory()]
    assert _RIPPER_ERROR_RE.match(line)


def test_the_argument_parse_errors_are_covered() -> None:
    """These reach **stdout only** — argument validation runs before the
    logfile is opened, so there is no file to write them to (fork round 4, Q5).
    Our stdout capture is load-bearing for the whole class, and the pattern has
    to recognise them or the user gets "Rip failed" for a typo in a flag."""
    for message in (
        "Unable to parse command line argument: --bogus-flag",
        'Missing value for argument "--paranoia"',
        'Missing value for argument "--offset"',
    ):
        assert _RIPPER_ERROR_RE.match(message), message
