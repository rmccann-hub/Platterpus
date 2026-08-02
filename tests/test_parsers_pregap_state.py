"""`unknown` is not `none` — the third instance of one class of bug.

The cyanrip fork prints three different answers about a track's pre-gap:

    Pregap LSN:  150 (duration: 00:02.00)             <- found
    Pregap LSN:  none                                 <- measured, none
    Pregap LSN:  unknown (sub-channel unreadable)     <- tried, could not tell

Our pattern was ``(\\d+|none)``, so the third matched *nothing* and fell through
to ``pregap_start_lsn=None, pregap_sectors=None`` — byte-identical to the
second. "We could not determine whether this track has a pre-gap" and "this
track has no pre-gap" are different archival claims, and this log is signed.

Same shape as ``Accurip: disabled`` rendering as "in DB, no match", and as the
all-zero CRC counting as a confidence-200 match. Third time, hence a dedicated
file: the fix is a *state*, not another special case.

Fixtures are the fork's own golden reference, kept byte-exact.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log

_FORK_GOLDEN = Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference.log"
_STOCK = (
    Path(__file__).parents[1]
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)


def _fork_tracks() -> dict[int, object]:
    log = parse_cyanrip_log(_FORK_GOLDEN.read_text(encoding="utf-8"))
    return {t.number: t for t in log.tracks}


# --- the three states must be three states ----------------------------------


def test_unknown_is_its_own_state_not_a_silent_none() -> None:
    """The bug, pinned. Track 3 of the fork's golden log is the `unknown` case."""
    t3 = _fork_tracks()[3]
    assert t3.pregap_state == "unknown"
    assert t3.pregap_unknown_reason == "sub-channel unreadable"
    # Emphatically NOT 0. A 0 here reads downstream as "measured, no gap".
    assert t3.pregap_sectors is None
    assert t3.pregap_start_lsn is None


def test_a_measured_none_stays_a_measured_none() -> None:
    """The other side: stock cyanrip's `none` must not become `unknown`.

    Every track of the committed 14-track reference reports `none`, so this also
    proves the change is inert on the ripper actually in production.
    """
    stock = parse_cyanrip_log(_STOCK.read_text(encoding="utf-8"))
    assert len(stock.tracks) == 14
    assert {t.pregap_state for t in stock.tracks} == {"none"}
    assert {t.pregap_sectors for t in stock.tracks} == {0}


def test_a_found_pregap_is_state_known_with_its_source() -> None:
    tracks = _fork_tracks()
    assert tracks[1].pregap_state == "known"
    assert tracks[2].pregap_state == "known"
    # Provenance we previously had to infer. "sub-channel" here would mean a gap
    # the TOC does not declare — the whole point of upstream PR #115.
    assert tracks[1].pregap_source == "TOC"
    assert tracks[2].pregap_source == "TOC"


# --- the stated length beats our derivation ---------------------------------


def test_track_one_uses_the_stated_length_not_the_subtraction() -> None:
    """Track 1 is exactly where deriving `start - lsn` gets the wrong answer.

    The golden log reads `Pregap LSN: 0` / `Start LSN: 150` / `Pregap length:
    300`, and its `Gaps:` block declares a 150-frame TOC pre-gap. 150 (lead-in) +
    150 (declared) = 300. Subtracting gives 150 — half the real gap — because
    LSN 0 cannot express a lead-in that physically occupies −150..−1.
    """
    t1 = _fork_tracks()[1]
    assert t1.pregap_start_lsn == 0
    assert t1.start_sector == 150
    assert t1.pregap_length_frames == 300, "the ripper states it outright"
    assert t1.pregap_sectors == 300, "and the stated value wins over 150-0=150"


def test_a_stated_length_agrees_with_the_subtraction_elsewhere() -> None:
    """Track 2 is the case where both methods agree, so preferring the stated
    one cannot be hiding a disagreement — 375 − 300 = 75, and it says 75."""
    t2 = _fork_tracks()[2]
    assert t2.start_sector - t2.pregap_start_lsn == 75
    assert t2.pregap_length_frames == 75
    assert t2.pregap_sectors == 75


# --- what the signed log says -----------------------------------------------


def test_the_eac_row_says_not_determined_rather_than_going_silent() -> None:
    """Omitting the row would be indistinguishable from "no pre-gap", and this
    log carries a SHA-256. The file's standing rule is that rows the ripper does
    not report say so instead of guessing."""
    text = render_eac_style_log(
        parse_cyanrip_log(_FORK_GOLDEN.read_text(encoding="utf-8"))
    )
    # Anchored to the row label, not a substring search for "Pre-gap": the
    # header's ripper-provenance line legitimately mentions pre-gap in prose,
    # and a loose filter counted it as a fourth track row.
    rows = [line for line in text.splitlines() if line.strip().startswith("Pre-gap ")]
    assert len(rows) == 3, "one row per track, including the undetermined one"
    assert "not determined by the ripper" in rows[2]
    assert "sub-channel unreadable" in rows[2]
    assert "0:00:00.00" not in text, "an undetermined gap must never render as zero"


def test_the_rendered_lengths_match_the_rippers_own_duration_suffix() -> None:
    """Independent cross-check: cyanrip prints `(duration: 00:04.00)` and
    `(duration: 00:01.00)` beside the LSNs it reports. Our converted rows must
    agree with the ripper's own arithmetic, or one of us is wrong about the unit.

    (The fraction is hundredths of a second, not CD frames — proven by the real
    EAC value `0:00:01.96`, impossible for a 0–74 counter.)
    """
    text = render_eac_style_log(
        parse_cyanrip_log(_FORK_GOLDEN.read_text(encoding="utf-8"))
    )
    assert "Pre-gap length  0:00:04.00" in text
    assert "Pre-gap length  0:00:01.00" in text


def test_stock_cyanrip_renders_no_pregap_rows_at_all() -> None:
    """Inertness on the production ripper: every track measured `none`, so EAC's
    row is correctly absent throughout — unchanged from before this fix."""
    text = render_eac_style_log(parse_cyanrip_log(_STOCK.read_text(encoding="utf-8")))
    assert "Pre-gap" not in text
