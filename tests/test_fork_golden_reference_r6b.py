"""The fork's round-6b golden reference — the artifact at the pin we build.

`tests/fixtures/cyanrip_fork_golden_reference_r6b.log` is byte-exact output from
the cyanrip fork at pin `25a2265`, delivered in round 6b (Appendix 1). The
round-4 reference (`cyanrip_fork_golden_reference.log`) is kept alongside it
rather than replaced: two references at different pins are the only way to see a
line *change*, and replacing the old one each round would make every rename
invisible in exactly the round it happened.

**Why this file exists as a test and not as a read-through.** Round 6 renamed two
lines we parse (`Peak level:` → `Sample peak level:`, `Cache defeat:` →
`Cache model:`) and its cover note asked us to verify them "before you ship".
A read-through of a rename table cannot tell you whether *your* regex matches;
running their artifact through the real parser can. That is the same discipline
`docs/testing.md` §5.u states the other way round: when a committed artifact can
settle a question, the test reads the artifact.

**Three findings are pinned here, each because it was invisible to a check that
looked reasonable.**

1. *Per-track paranoia counters are per-**pass**, not per-track.* Round 5 told us
   they "sum exactly to the disc totals" and we verified it — on an artifact
   ripped without `-Z`. Under `-Z` the disc total is every pass and the per-track
   figure is only the last one, so the sums differ by the re-read factor. Proven
   in their source: `start_paranoia` is snapshotted *inside* the
   `repeat_ripping:` loop (`cyanrip_main.c`), so each pass resets the baseline,
   while the process-global counter keeps accumulating. Asserted here so nobody
   "fixes" the discrepancy into a false invariant.

2. *The counters are also how we know the silence fix is in this binary.* The
   round-6 artifact (cachemodel 1) logged one READ per sector; this one logs
   `ceil(sectors / 16)`. That is the fix, visible in the artifact, and it is the
   only evidence of it the log carries — see (3) for why that matters.

3. *The build tag does not name the pin.* This artifact's banner reads
   `platterpus-fork-gd5d2fed`, four commits below `25a2265` — including the
   silence fix the reference exists to demonstrate. So the tag is asserted to be
   *a fork build*, which is all we can honestly conclude from it, and the pin
   agreement is checked against `fork_source` rather than against this log.
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path

import pytest

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.ripper_identity import identify_ripper

_GOLDEN = Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r6b.log"

#: The cachemodel the fork sets for disc-image drivers at this pin, read off
#: `src/cyanrip_main.c` (`cdio_paranoia_cachemodel_size(ctx->paranoia, 16)`).
#: It doubles as paranoia's `c_block` read-chunk size, which is why the READ
#: callback count divides by it.
_IMAGE_CACHEMODEL_SECTORS = 16


@pytest.fixture(scope="module")
def text() -> str:
    return _GOLDEN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parsed(text: str):  # type: ignore[no-untyped-def]  # a RipLog
    return parse_cyanrip_log(text)


def test_the_fixture_is_the_whole_log(text: str) -> None:
    """A floor. Every assertion below is "the parse contains X", which a
    truncated or mis-extracted fixture could satisfy while hiding the rest."""
    assert text.startswith("cyanrip 0.9.4-rc1 (platterpus-fork-")
    assert "Log FUN512:" in text, "the fixture is missing the log's footer"
    assert len(text.splitlines()) == 269, "round 6b states 269 lines"


def test_no_top_level_line_goes_unrecognised(text: str) -> None:
    """The load-bearing test of the round.

    The parser logs a DEBUG line naming every top-level line it neither parsed
    nor has on its documented ignore list. An entry there is a fact the fork
    emitted and we dropped on the floor.
    """
    logger = "platterpus.parsers.cyanrip_log"
    records: list[logging.LogRecord] = []

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Collect()
    log = logging.getLogger(logger)
    previous_level, previous_propagate = log.level, log.propagate
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)
    try:
        parse_cyanrip_log(text)
    finally:
        log.removeHandler(handler)
        log.setLevel(previous_level)
        log.propagate = previous_propagate

    missed = [r for r in records if "unrecognised top-level" in r.getMessage()]
    assert not missed, (
        "the fork emits lines we neither parse nor deliberately ignore: "
        + "; ".join(r.getMessage() for r in missed)
    )


# --- round 6 §D1: the two renames, measured rather than read -----------------


def test_the_renamed_sample_peak_row_parses(text: str, parsed) -> None:  # type: ignore[no-untyped-def]
    """`Peak level:` → `Sample peak level:  99.8% (-0.0 dBFS)`.

    Both halves matter: the artifact must actually carry the new spelling (so
    this cannot pass by finding nothing), and the parser must extract the
    percentage from it. Track 3's 27.3% is asserted too — a pattern that only
    handled `100.0%` would look correct on the first two tracks.
    """
    assert "Sample peak level:" in text, "the fixture predates the rename"
    assert "\n    Peak level:" not in text, "the old spelling is still present"
    peaks = {t.number: t.peak_level for t in parsed.tracks}
    assert peaks == {1: 1.0, 2: 1.0, 3: 0.273}


def test_the_renamed_cache_row_is_not_a_key_we_depend_on(text: str, parsed) -> None:  # type: ignore[no-untyped-def]
    """`Cache defeat:` → `Cache model:` costs us nothing, and the reason is worth
    writing down rather than rediscovering.

    Our own **Cache defeat** row is *our* measurement — `cd-paranoia -A`, stored
    per drive (KDD-29) — not a field scraped from cyanrip's log. cyanrip's line
    describes what libcdio-paranoia *models*, which is a different claim, and the
    fork renamed it for exactly that reason. So `defeat_audio_cache` stays unset
    by the parse, and the honest `(unknown)` in an unprobed export is preserved.
    """
    assert "Cache model:" in text
    assert "Cache defeat:" not in text
    assert parsed.ripping_info.defeat_audio_cache is None, (
        "the parser started inferring a cache verdict from cyanrip's model line — "
        "that is a modelled figure, not a measured one (KDD-25's never-forge rule)"
    )


# --- the -Z axis (A4), and both `Done;` forms -------------------------------


def test_the_secure_reread_axis_is_exercised_and_converges(text: str, parsed) -> None:  # type: ignore[no-untyped-def]
    """`-Z 2`: three reads, agreement on the last two, per track.

    The fork indents its `Done;` line, which once shifted every `-Z` verdict by
    one track (F1). Asserting the *verdict per track* rather than "a Done; line
    exists" is what makes this a regression test for that.
    """
    assert "Repeating ripping (" in text
    assert "(after 3 rips)" in text
    for track in parsed.tracks:
        assert track.rip_count == 3, f"track {track.number} rip count"
        assert track.secure_rerip_converged is True, f"track {track.number} verdict"


def test_over_full_scale_peaks_are_exercised(text: str, parsed) -> None:  # type: ignore[no-untyped-def]
    """Round 6 §C7 reported this coverage as missing and round 6b withdrew that:
    the fixture audio always had a true peak of +0.3 dBFS. The values were absent
    from round 5's reference because the paranoia defect had zeroed the audio, not
    because the material lacked them.

    Pinned here because a `REPLAYGAIN_TRACK_PEAK` above 1.0 is the one input that
    proves we never treat ReplayGain's peak as a percentage-of-full-scale — EAC's
    `Peak level` cannot exceed 100%, this can, and conflating them silently
    understates a clipped master.
    """
    assert "True peak level:   0.3 dBFS" in text
    peaks = {
        t.number: float(t.replaygain["REPLAYGAIN_TRACK_PEAK"]) for t in parsed.tracks
    }
    assert peaks[1] > 1.0 and peaks[2] > 1.0, peaks
    assert peaks[3] < 1.0, "the sub-unity control track is gone"
    # And the sample-peak field — which *is* a percentage — is not contaminated
    # by it. 1.033086 must never surface as a 103.3% sample peak.
    assert max(t.peak_level or 0.0 for t in parsed.tracks) <= 1.0


# --- the paranoia-counter semantics -----------------------------------------


def _per_track_read_counts(text: str) -> list[int]:
    """READ counts from the indented per-track blocks only.

    Indentation is the discriminator: the disc-level block starts at column 0
    and its counters are indented two spaces; a per-track block is itself
    indented, so its counters carry four. Keyed on that rather than on order,
    because "the last one is the disc total" breaks on a partial rip.
    """
    return [int(m.group(1)) for m in re.finditer(r"^ {4}READ: +(\d+)$", text, re.M)]


def test_per_track_paranoia_counters_are_per_pass_not_per_track(
    text: str,
    parsed,  # type: ignore[no-untyped-def]
) -> None:
    """The invariant round 5 gave us, and the condition under which it is false.

    Their claim — per-track counters sum to the disc totals — was verified on a
    `-Z`-off artifact where it is arithmetically guaranteed. Here the ratio is
    exactly the number of passes, because each pass resets the per-track
    baseline while the disc-level counter accumulates over all of them.

    The consequence for a consumer is the reason this is asserted rather than
    noted: a disc-level `SKIP: 300` on a `-Z 2` rip is three passes' worth of
    skips, so rendering it as "300 unreadable frames" over-reports by the
    re-read factor.
    """
    per_track = _per_track_read_counts(text)
    assert len(per_track) == len(parsed.tracks) >= 3, per_track
    disc_total = parsed.paranoia_counts["READ"]
    passes = {t.rip_count for t in parsed.tracks}
    assert passes == {3}, "this fixture is the -Z 2 one; the ratio below needs it"

    assert sum(per_track) != disc_total, (
        "per-track counters now sum to the disc total under -Z — if the fork "
        "changed the snapshot point, say so in the handshake before relying on it"
    )
    assert sum(per_track) * passes.pop() == disc_total, (
        f"per-track {per_track} (sum {sum(per_track)}) does not scale to the disc "
        f"total {disc_total} by the pass count"
    )


def test_the_read_chunk_size_shows_the_silence_fix_is_in_this_binary(
    text: str,
    parsed,  # type: ignore[no-untyped-def]
) -> None:
    """The only evidence in the artifact that it came from a fixed build.

    Round 6b's whole subject is that at `ad65a24` a disc-image rip above `-P 0`
    returned silence, because upstream set paranoia's cachemodel — which is also
    its `c_block` read-chunk size — to 1 sector for image drivers. The fix raises
    it to 16. paranoia's READ callback fires once per chunk, so the count per
    track is `ceil(frames / 16)` at this pin and was `frames` at the last one
    (225/150/75 → 15/10/5 on the same fixture).

    This matters because the artifact's own build tag names a commit *below* the
    fix (see the module docstring). The counters are the check that does not
    depend on the tag being right.
    """
    per_track = _per_track_read_counts(text)
    frames = [t.end_sector - t.start_sector + 1 for t in parsed.tracks]
    expected = [math.ceil(f / _IMAGE_CACHEMODEL_SECTORS) for f in frames]
    assert per_track == expected, (
        f"READ counts {per_track} do not match ceil(frames/{_IMAGE_CACHEMODEL_SECTORS}) "
        f"= {expected} for frame counts {frames} — either the cachemodel moved off "
        f"16 or this reference came from a build that still has the silence defect"
    )
    # A floor: with cachemodel 1 the counts would equal the frame counts, which
    # is precisely the broken build. Naming it makes the check non-vacuous.
    assert per_track != frames, "one READ per sector means cachemodel 1 — the defect"


# --- provenance --------------------------------------------------------------


def test_the_build_identifies_as_our_fork_whichever_commit_built_it(parsed) -> None:  # type: ignore[no-untyped-def]
    """Classification keys on the fork *id*, not on the commit.

    Deliberate, and this artifact is why: its tag is four commits behind the pin,
    so a classifier that required the pinned sha would report a genuine fork build
    as unrecognised. "Which fork" and "which commit of it" are separate questions
    and only the first can be answered from a banner we did not build.
    """
    identity = identify_ripper(parsed.log_creator, parsed.ripper_build)
    assert identity.kind == "fork"
    assert identity.is_fork is True
    assert parsed.ripper_build.startswith("platterpus-fork-g")


def test_the_reference_was_generated_with_the_paranoia_level_pinned(text: str) -> None:
    """`-P 0` in `Invoked as:`, which round 6b makes a standing requirement for
    every future reference: without it the audio is silence, and a reference whose
    audio is silence still parses perfectly."""
    invoked = next(line for line in text.splitlines() if line.startswith("Invoked as:"))
    assert " -P 0" in invoked, f"reference not pinned to -P 0: {invoked}"
    assert " -N" in invoked, "the ripper was run with its own metadata lookup live"
