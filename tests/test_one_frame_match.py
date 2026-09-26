"""Every surface says what an `Accurip 450` match is, and none names a pressing.

cyanrip's `Accurip 450` checksum covers ONE frame of a track, and it is printed
only after both whole-track checksums matched nothing
(`platterpus.one_frame_match` has the derivation, from the fork's source). For two
months this project called that "an offset-variant pressing" and "usually
perfectly fine". On 2026-09-24 such a track held wrong audio.

The subject is the real log of that rip (section J, tracks 1-2), not a fixture:
its track 1 is the wrong read, and track 2 is an exact match, so every surface
below renders a disc that has both states on it.

Two kinds of assertion, and both are needed. A FLOOR that each surface says "one
frame", because a surface that rendered nothing would pass the ban. And the BAN on
the old cause, because a surface that added the new words beside the old ones
would pass the floor.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from platterpus import one_frame_match
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.eac_log_export import _accuraterip_line
from platterpus.help_content import USER_GUIDE
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog, TrackResult
from platterpus.rip_compare import STATUS_OFFSET_VARIANT, _describe_status
from platterpus.rip_plan import describe_rip_plan
from platterpus.ui.main_window_helpers import _partial_accurate_clause
from platterpus.ui.rip_progress import _ar_cell, _ar_tooltip, _eac_cell
from platterpus.verdict import accuraterip_verdict, reconcile_ar_ctdb

_SECTION_J_LOG: Path = (
    Path(__file__).resolve().parents[1]
    / "docs/handshake/artifactsround26/round26aftercancel.log"
)

#: The old claims. Each is a CAUSE (a pressing, an offset) or a VERDICT ("fine")
#: that a one-frame match cannot support.
_BANNED: tuple[str, ...] = (
    "offset-variant pressing",
    "offset-variant match",
    "different pressing",
    "shifted by a fixed offset",
    "perfectly fine",
    "almost certainly correct",
    "common pressing",
)


def _section_j() -> tuple[RipLog, TrackResult]:
    parsed = parse_cyanrip_log(_SECTION_J_LOG.read_text(encoding="utf-8"))
    # Floors: the log must still be the case this file is about.
    assert [t.number for t in parsed.tracks] == [1, 2], parsed.tracks
    track1 = parsed.tracks[0]
    assert track1.copy_crc == "0E91CD1A", "section J's wrong read of track 1"
    assert track1.accuraterip_offset is not None
    assert track1.accuraterip_offset.local_crc == "57722DDE"
    assert track1.accuraterip_offset.confidence == 200
    return parsed, track1


def _check(surface: str, text: str) -> None:
    assert "one frame" in text.lower(), f"{surface} does not say what matched: {text!r}"
    for phrase in _BANNED:
        assert phrase not in text.lower(), f"{surface} still says {phrase!r}: {text!r}"


def test_the_verdict_banner_says_one_frame_and_names_no_cause() -> None:
    parsed, _ = _section_j()
    message, level = accuraterip_verdict(parsed)
    assert level == "warn"
    _check("verdict banner", message)


def test_the_ctdb_reconciliation_says_one_frame_and_names_no_cause() -> None:
    parsed, _ = _section_j()
    line = reconcile_ar_ctdb(
        parsed,
        CtdbVerifyResult(verdict=Verdict.NO_MATCH, confidence=100, crc_validated=True),
    )
    assert line is not None
    _check("CTDB reconciliation", line)


def test_the_results_table_cell_and_tooltips_say_one_frame() -> None:
    _, track1 = _section_j()
    lookup = getattr(track1, "accuraterip_lookup", None)
    cell = _ar_cell(
        track1.accuraterip_v1, offset_result=track1.accuraterip_offset, lookup=lookup
    )
    assert cell == f"{one_frame_match.CELL} (200)"
    _check("AR cell", cell)
    _check(
        "AR cell tooltip",
        _ar_tooltip(
            track1.accuraterip_v1,
            offset_result=track1.accuraterip_offset,
            lookup=lookup,
        ),
    )
    text, tip = _eac_cell(track1)
    assert text.endswith("~"), text
    _check("EAC CRC cell tooltip", tip)


def test_the_status_line_and_the_report_sentence_say_one_frame() -> None:
    parsed, _ = _section_j()
    _check("status-line clause", _partial_accurate_clause(parsed))
    _check("report partially_accurate_summary", parsed.partially_accurate_summary)


def test_the_help_the_plan_and_the_compare_tool_say_one_frame() -> None:
    _check("User Guide", USER_GUIDE)
    plan = "\n".join(
        describe_rip_plan(
            secure_rerip_matches=2,
            secure_rerip_dynamic=True,
            rerip_offset_variant=True,
        )
    )
    _check("rip plan", plan)
    _check("compare tool", _describe_status(STATUS_OFFSET_VARIANT))


def test_the_settings_option_says_one_frame(qapp: QApplication) -> None:
    from platterpus.config import Config
    from platterpus.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(Config())
    box = dialog._rerip_offset_variant_check
    _check("Settings option", box.text())
    _check("Settings option tooltip", box.toolTip())


def test_the_EAC_compatible_log_is_NOT_reworded_until_round_27() -> None:
    """The one surface deliberately left alone, pinned so that a change is a decision.

    In round 7 (lap 11, H4) both projects agreed that neither rewords this log
    unilaterally, because it is what the cyanrip fork diffs against. So its line
    keeps the old words until round 27 settles new ones, where we answer first.
    When that lands, this test is the one to change, and the round is its reason.
    """
    _, track1 = _section_j()
    line = _accuraterip_line(track1)
    assert line.startswith("Matched an offset-variant pressing — partially accurate"), (
        line
    )


@pytest.mark.parametrize("population", [1, 14])
def test_the_count_sentence_agrees_its_noun_with_the_population(
    population: int,
) -> None:
    sentence = one_frame_match.count_sentence(1, population)
    noun = "track" if population == 1 else "tracks"
    assert sentence.startswith(f"1 of {population} {noun} matched"), sentence
    _check("count sentence", sentence)
