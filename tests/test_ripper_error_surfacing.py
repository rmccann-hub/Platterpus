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
