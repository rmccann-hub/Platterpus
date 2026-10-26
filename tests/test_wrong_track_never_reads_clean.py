"""Row 8 of the owner's EAC-parity plan of record (2026-10-26): never clean words
over a track AccurateRip contradicts.

**The measured case.** The Police disc's secure re-read in the Full run of
2026-10-21 (bundle ``20261021t113505z``, ``album/secure reread …``) shipped track 3
as ``3D8FCF0C``: four reads, the last three agreeing, ``secure_rerip_converged``
True, and AccurateRip matching frame 450 (confidence 200) and no whole-track
checksum. Its EAC-layout log said::

    Copy CRC 3D8FCF0C  (Test and Copy CRC identical — confirmed across 4 secure re-reads)
    Only one frame matched AccurateRip (confidence 200); …  (AR frame 450)
    Copy OK
    …
    No errors occurred

The owner's yardstick (plan §2) calls that track WRONG: the frame match places
the pressing, so the whole-track miss means the audio differs. A wrong track
reported as fine is the worst outcome the plan names.

The bundle is not committed (it is run evidence, and this shape needs only its
values), so the track is rebuilt here from the committed reference rip of the
same disc, whose track 3 carries the same frame-450 row, with the N rip's
measured CRC, read count and convergence put on it.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.eac_log_export import (
    CONTRADICTED_VERDICT,
    DISC_HAD_ERRORS,
    render_eac_style_log,
)
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.rip_report import build_report
from platterpus.ui.rip_progress import RipProgress
from platterpus.verdict import (
    AR_CONTRADICTION_DIFFERS,
    AR_CONTRADICTION_WRONG,
    accuraterip_rejected_count,
    track_accuraterip_contradiction,
)

_REFERENCE = (
    Path(__file__).resolve().parent.parent
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)

pytestmark = pytest.mark.skipif(
    not _REFERENCE.exists(), reason="reference rip not present in this checkout"
)


def _run_a_n_rip() -> RipLog:
    """The reference rip with track 3 as the N rip shipped it (2026-10-21)."""
    log = parse_cyanrip_log(_REFERENCE.read_text(encoding="utf-8", errors="replace"))
    tracks = tuple(
        replace(t, copy_crc="3D8FCF0C", rip_count=4, secure_rerip_converged=True)
        if t.number == 3
        else t
        for t in log.tracks
    )
    return replace(log, tracks=tracks)


def _block(text: str, number: int) -> list[str]:
    """The EAC-layout per-track block for ``number``, up to the blank line."""
    lines = text.splitlines()
    start = lines.index(f"Track {number:>2}")
    end = lines.index("", start + 2)
    while lines[end + 1].startswith("     "):
        end = lines.index("", end + 1)
    return lines[start:end]


def _track(number: int, rip_log: RipLog) -> TrackResult:
    return next(t for t in rip_log.tracks if t.number == number)


# --- the one predicate --------------------------------------------------------


def test_the_measured_track_is_wrong_and_a_verified_one_is_not() -> None:
    rip_log = _run_a_n_rip()
    # Floors: the fixture holds the shape this test is about.
    track3 = _track(3, rip_log)
    assert track3.accuraterip_offset is not None
    assert track3.accuraterip_offset.confidence == 200
    assert track_accuraterip_contradiction(track3) == AR_CONTRADICTION_WRONG
    assert track_accuraterip_contradiction(_track(1, rip_log)) is None
    # The CTDB guard's count and this predicate are one rule: 3 and 5.
    assert accuraterip_rejected_count(rip_log) == 2


def test_a_compared_track_that_matched_nothing_differs() -> None:
    track = TrackResult(
        number=7,
        copy_crc="12345678",
        accuraterip_v1=AccurateRipResult(version=1, result="not found", local_crc="AA"),
        accuraterip_v2=AccurateRipResult(version=2, result="not found", local_crc="BB"),
        accuraterip_lookup="disc found in database (max confidence: 200)",
    )
    assert track_accuraterip_contradiction(track) == AR_CONTRADICTION_DIFFERS


@pytest.mark.parametrize(
    "lookup",
    ["disabled", "not found in database"],
    ids=["never-asked", "disc-not-in-database"],
)
def test_no_finding_is_no_contradiction(lookup: str) -> None:
    """AccurateRip said nothing about the track, so it contradicts nothing."""
    track = TrackResult(
        number=2,
        copy_crc="12345678",
        accuraterip_v1=AccurateRipResult(version=1, result="x", local_crc="AA"),
        accuraterip_lookup=lookup,
    )
    assert track_accuraterip_contradiction(track) is None


def test_the_predicate_never_raises_on_a_wrong_shape() -> None:
    assert track_accuraterip_contradiction(object()) is None
    assert track_accuraterip_contradiction(None) is None


# --- the EAC-layout log -------------------------------------------------------


def test_the_eac_layout_block_no_longer_calls_the_wrong_track_clean() -> None:
    text = render_eac_style_log(_run_a_n_rip(), disc_track_total=14)
    block = _block(text, 3)
    joined = "\n".join(block)
    assert "Copy OK" not in joined
    assert "confirmed across" not in joined
    assert block[-1] == f"     {CONTRADICTED_VERDICT}"
    assert (
        "     Copy CRC 3D8FCF0C  (Test and Copy CRC identical — the re-reads agreed "
        "on this value, and AccurateRip contradicts it)"
    ) in block
    assert (
        "     Proof: none — WRONG: frame 450 matches AccurateRip's entry for this "
        "pressing (confidence 200) and the whole track does not, so the audio "
        "differs from it"
    ) in block


def test_a_verified_track_keeps_eac_s_clean_lines() -> None:
    """The mirror defect: a right track must keep EAC's own words."""
    rip_log = _run_a_n_rip()
    rip_log = replace(
        rip_log,
        tracks=tuple(
            replace(t, rip_count=3, secure_rerip_converged=True) if t.number == 1 else t
            for t in rip_log.tracks
        ),
    )
    block = _block(render_eac_style_log(rip_log, disc_track_total=14), 1)
    assert block[-1] == "     Copy OK"
    assert any("confirmed across 3 secure re-reads" in line for line in block)
    assert not any("WRONG" in line for line in block)


def test_the_disc_level_sentence_is_never_clean_over_a_wrong_track() -> None:
    text = render_eac_style_log(_run_a_n_rip(), disc_track_total=14)
    assert "No errors occurred" not in text
    assert "All tracks accurately ripped" not in text
    assert f"\n{DISC_HAD_ERRORS}\n" in text
    assert (
        "Ripper's own count  : Ripping errors: 0 — not counted: track(s) 3, 5, "
        "which AccurateRip contradicts"
    ) in text


def test_a_clean_disc_keeps_the_ripper_s_sentence() -> None:
    """With every track verified, nothing changes: EAC's clean sentence stays."""
    rip_log = _run_a_n_rip()
    verified = _track(1, rip_log)
    rip_log = replace(
        rip_log,
        tracks=tuple(
            replace(
                t,
                accuraterip_v1=verified.accuraterip_v1,
                accuraterip_v2=verified.accuraterip_v2,
                accuraterip_offset=None,
            )
            for t in rip_log.tracks
        ),
    )
    text = render_eac_style_log(rip_log, disc_track_total=14)
    assert "\nNo errors occurred\n" in text
    assert DISC_HAD_ERRORS not in text
    assert "Ripper's own count" not in text


# --- the report and the results table ----------------------------------------


def test_the_report_names_the_contradiction_per_track() -> None:
    report = build_report(_run_a_n_rip())
    by_number = {t["number"]: t for t in report["tracks"]}
    assert by_number[3]["accuraterip_contradiction"] == AR_CONTRADICTION_WRONG
    assert by_number[5]["accuraterip_contradiction"] == AR_CONTRADICTION_WRONG
    assert by_number[1]["accuraterip_contradiction"] is None
    # The ripper's own word is kept as it said it; this field is the verdict.
    assert by_number[3]["status"] == "ripped successfully"


def test_the_results_table_status_cell_is_not_clean_for_a_wrong_track(
    qapp: QApplication,
) -> None:
    widget = RipProgress()
    widget.set_rip_log(_run_a_n_rip(), disc_track_total=14)
    rows = {
        widget._ar_table.item(row, 0).text(): widget._ar_table.item(row, 2)
        for row in range(widget._ar_table.rowCount())
    }
    wrong = rows["3"]
    # Status is never colour alone: the cell carries a marker and words.
    assert wrong.text() == "⚠ Wrong (AccurateRip)"
    assert "ripped successfully" in wrong.toolTip()
    assert "frame 450" in wrong.toolTip()
    assert rows["1"].text() == "ripped successfully"
