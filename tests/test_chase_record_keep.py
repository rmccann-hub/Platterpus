"""A chase read's ripper record is kept for the bundle (the fork's round 39 lap 1 S10).

``chase_record_keep`` copies each verified-read chase read's ``--diagnostics``
record out of the read's temporary folder into the rips root, where the session
bundle's scan finds it (``test_session.session_diagnostics_records``). The worker
half is ``tests/test_rip_worker.py::test_a_chase_reads_record_leaves_its_temp_folder_for_the_rips_root``.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path

import pytest

from platterpus import test_session
from platterpus.chase_record_keep import chase_record_destination, keep_chase_record


def test_the_kept_name_is_found_by_the_bundles_own_scan(tmp_path: Path) -> None:
    source = tmp_path / "attempt" / "cyanrip-diagnostics-20261111T101500Z.json"
    source.parent.mkdir()
    source.write_text('{"block_crcs": []}\n', encoding="utf-8")
    rips = tmp_path / "rips"
    rips.mkdir()
    kept = keep_chase_record(source, rips, 3)
    assert kept == rips / "cyanrip-diagnostics-20261111T101500Z-chase-t03.json"
    found, dropped = test_session.session_diagnostics_records([rips], since=0.0)
    assert found == [kept] and dropped == 0


def test_a_taken_name_is_numbered_never_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "cyanrip-diagnostics-S.json"
    assert chase_record_destination(source, tmp_path, 5) == (
        tmp_path / "cyanrip-diagnostics-S-chase-t05.json"
    )
    assert chase_record_destination(source, tmp_path, 5, 2) == (
        tmp_path / "cyanrip-diagnostics-S-chase-t05-2.json"
    )


def test_a_missing_record_is_logged_and_none_is_due_without_one(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert keep_chase_record(tmp_path / "gone.json", tmp_path, 3) is None
    assert "left no -j record" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert keep_chase_record(None, tmp_path, 3) is None
    assert caplog.text == ""  # no record was asked for, so none is lost


def test_a_failed_copy_is_logged_never_raised(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source = tmp_path / "cyanrip-diagnostics-S.json"
    source.write_text("{}", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        assert keep_chase_record(source, tmp_path / "no-such-folder", 3) is None
    assert "could not keep" in caplog.text


def test_the_session_scan_keeps_up_to_400_records() -> None:
    """Every chase read keeps one now (up to 16 a track, five section R rips), so
    the old cap of 80 could drop the earliest rips' records."""
    limit = inspect.signature(test_session.session_diagnostics_records).parameters[
        "limit"
    ]
    assert limit.default == 400
