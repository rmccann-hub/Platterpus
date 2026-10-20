"""The second read of a disc AccurateRip can't vouch for (the owner's word of
2026-10-20, *"yes, read twice by default"*).

The plan and the worker are held in `tests/test_securing_pass.py` and
`tests/test_rip_worker.py`. These hold what a user sees and keeps: the setting
and its default, the named "reads agree" verdict, the report's record of it,
the time estimate and the plan line.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from platterpus import rip_estimate
from platterpus.config import Config
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_estimate import ReadRate
from platterpus.rip_plan import describe_rip_plan
from platterpus.rip_report import build_report
from platterpus.ui.settings_dialog import SettingsDialog
from platterpus.verdict import (
    VERDICT_BASIS_READS_AGREE,
    accuraterip_verdict,
    reads_agree_without_accuraterip,
)

#: cyanrip's line for a re-read whose reads agreed, and for one that hit the
#: repeat limit first (`parsers/cyanrip_log.py`, `_RERIP_DONE`).
_AGREED = "Done; (2 out of 2 matches for current checksum {crc})\n"
_GAVE_UP = "Done; (no matches found, but hit repeat limit of 5)\n"


def _log(*, track2: str = _AGREED, header: str = "not found") -> object:
    """Two tracks, nothing in AccurateRip, each read again with -Z."""
    return parse_cyanrip_log(
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    2\n"
        f"AccurateRip:    {header}\n"
        + _AGREED.format(crc="11111111")
        + "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     11111111\n"
        "    Accurip v1:  AAAAAAAA (not found, either a new pressing, or bad rip)\n"
        + track2.format(crc="22222222")
        + "Track 2 ripped and encoded successfully!\n"
        "  EAC CRC32:     22222222\n"
        "    Accurip v1:  BBBBBBBB (not found, either a new pressing, or bad rip)\n"
        "Ripping errors: 0\n"
    )


def test_the_second_read_is_on_by_default() -> None:
    assert Config().second_read_without_accuraterip is True


def test_the_setting_round_trips_through_settings(qapp: QApplication) -> None:
    dialog = SettingsDialog(Config())
    assert dialog._second_read_unvouched_check.isChecked() is True
    assert dialog.to_config().second_read_without_accuraterip is True
    dialog._second_read_unvouched_check.setChecked(False)
    assert dialog.to_config().second_read_without_accuraterip is False
    off = SettingsDialog(Config(second_read_without_accuraterip=False))
    assert off._second_read_unvouched_check.isChecked() is False
    # The opt-out says what turning it off gives up.
    assert "can pass without any warning" in (
        dialog._second_read_unvouched_check.toolTip()
    )


def test_reads_that_agree_get_their_own_verdict_and_never_verified() -> None:
    log = _log()
    assert reads_agree_without_accuraterip(log, disc_track_total=2) is True
    message, level = accuraterip_verdict(log, disc_track_total=2)
    assert message.startswith("ⓘ Reads agree")
    assert "not verified by AccurateRip" in message
    assert "verified against" not in message
    assert level == "neutral"


def test_a_track_whose_reads_disagree_is_amber_and_named() -> None:
    log = _log(track2=_GAVE_UP)
    assert reads_agree_without_accuraterip(log, disc_track_total=2) is False
    message, level = accuraterip_verdict(log, disc_track_total=2)
    assert level == "warn"
    assert "track 2" in message
    assert not message.startswith("ⓘ Reads agree")


def test_a_stopped_rip_cannot_claim_its_reads_agree() -> None:
    """Two of a three-track disc: the third was never read at all."""
    assert reads_agree_without_accuraterip(_log(), disc_track_total=3) is False


def test_the_report_names_the_basis() -> None:
    agreed = build_report(_log(), outcome={"status": "success"}, disc_track_total=2)
    assert agreed["verdict"]["basis"] == VERDICT_BASIS_READS_AGREE
    gave_up = build_report(
        _log(track2=_GAVE_UP), outcome={"status": "success"}, disc_track_total=2
    )
    assert gave_up["verdict"]["basis"] is None


def test_the_estimate_says_an_unknown_disc_reads_twice() -> None:
    rate = ReadRate(audio_seconds=3600.0, read_seconds=3600.0, rips=3)
    kwargs = {"secure_rerip_matches": 2, "dynamic": True, "max_retries": 5}
    on = rip_estimate.estimate_rip(
        1800.0, rate, second_read_without_accuraterip=True, **kwargs
    )
    off = rip_estimate.estimate_rip(
        1800.0, rate, second_read_without_accuraterip=False, **kwargs
    )
    assert on is not None and off is not None
    assert on.unvouched_seconds is not None and off.unvouched_seconds is None
    # The main pass, then every track again at three agreeing reads: at least
    # four times the audio.
    assert on.unvouched_seconds >= 4 * 1800.0
    assert "read twice" in rip_estimate.describe(on)
    assert "read twice" not in rip_estimate.describe(off)


def test_the_plan_says_what_happens_to_an_unknown_disc() -> None:
    def plan(second: bool) -> str:
        return "\n".join(
            describe_rip_plan(
                secure_rerip_matches=2,
                secure_rerip_dynamic=True,
                second_read_without_accuraterip=second,
            )
        )

    assert "EVERY track is read again with -Z 2" in plan(True)
    assert "kept on the one fast read" in plan(False)
