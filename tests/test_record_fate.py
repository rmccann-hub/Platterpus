"""What became of each ripper invocation's `--diagnostics` record (TASKS R9).

On the 2026-10-13 Full run two of the eleven ripper invocations, the two
securing passes (`-l 3,5` and `-l 3`), left no record: each ran in a temporary
folder deleted when it ended, and nothing said so. These tests pin both halves of
the fix: the worker-side copy (`keep_securing_record`) and the session-side
reading of the reports (`record_absences`), which is how the bundle's MANIFEST
names a missing record rather than omitting it.

**The real-artifact test reads the round-32 reports as filed** (schema v33, from
before this fix). Two of them ran a securing pass, and the line must say exactly
that two securing passes' records are not determined there: the absence the fork
and we failed to see, now visible even in the old reports.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from platterpus import record_fate
from platterpus.rip_report import build_outcome

_REPO = Path(__file__).resolve().parent.parent
_ROUND32 = _REPO / "docs/handshake/artifactsround32"
_REPORT_GLOB = "*.platterpus.json"


# --- Keeping the securing pass's record ---------------------------------------


def _told(tmp_path: Path, *, written: bool = True) -> Path:
    temp = tmp_path / "platterpus-refix-x"
    temp.mkdir()
    told = temp / "cyanrip-diagnostics-20261013T162022Z.json"
    if written:
        told.write_text('{"pass": "securing"}\n', encoding="utf-8")
    return told


def test_a_written_record_is_copied_beside_the_albums_with_its_pass_named(
    tmp_path: Path,
) -> None:
    rips = tmp_path / "rips"
    rips.mkdir()
    told = _told(tmp_path)
    fate = record_fate.keep_securing_record(told, rips, started=True, cancelled=False)
    kept = rips / "cyanrip-diagnostics-20261013T162022Z-securingpass.json"
    assert (fate.state, fate.path, fate.detail) == (record_fate.STATE_KEPT, kept, "")
    assert kept.read_text(encoding="utf-8") == '{"pass": "securing"}\n'
    # The session's record scan collects it with its one existing glob.
    from fnmatch import fnmatch

    from platterpus.test_session import DIAGNOSTICS_RECORD_GLOB

    assert fnmatch(kept.name, DIAGNOSTICS_RECORD_GLOB)


def test_a_taken_name_is_never_overwritten(tmp_path: Path) -> None:
    rips = tmp_path / "rips"
    rips.mkdir()
    taken = rips / "cyanrip-diagnostics-20261013T162022Z-securingpass.json"
    taken.write_text("someone else's\n", encoding="utf-8")
    fate = record_fate.keep_securing_record(
        _told(tmp_path), rips, started=True, cancelled=False
    )
    assert fate.path == rips / "cyanrip-diagnostics-20261013T162022Z-securingpass2.json"
    assert taken.read_text(encoding="utf-8") == "someone else's\n"


def test_a_pass_that_never_started_has_no_record_due(tmp_path: Path) -> None:
    fate = record_fate.keep_securing_record(
        _told(tmp_path, written=False), tmp_path, started=False, cancelled=False
    )
    assert fate == record_fate.RecordFate()
    assert fate.as_block() == {"state": "not_run", "path": None, "detail": None}


def test_a_missing_record_is_named_with_where_cyanrip_was_told_to_write_it(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    told = _told(tmp_path, written=False)
    fate = record_fate.keep_securing_record(
        told, tmp_path, started=True, cancelled=False
    )
    assert fate.state == record_fate.STATE_MISSING
    assert fate.path == told
    assert told.name in fate.detail and "securing pass ended" in fate.detail
    assert any("record is missing" in r.getMessage() for r in caplog.records)


def test_a_cancel_is_the_reason_when_the_rip_was_cancelled(tmp_path: Path) -> None:
    fate = record_fate.keep_securing_record(
        _told(tmp_path, written=False), tmp_path, started=True, cancelled=True
    )
    assert fate.state == record_fate.STATE_MISSING
    assert "the rip was cancelled" in fate.detail


def test_an_argv_that_named_no_record_says_so(tmp_path: Path) -> None:
    fate = record_fate.keep_securing_record(
        None, tmp_path, started=True, cancelled=False
    )
    assert fate.state == record_fate.STATE_MISSING
    assert "named no --diagnostics record" in fate.detail


def test_a_copy_that_fails_is_missing_with_the_error(tmp_path: Path) -> None:
    told = _told(tmp_path)
    fate = record_fate.keep_securing_record(
        told, tmp_path / "no-such-rips-folder", started=True, cancelled=False
    )
    assert fate.state == record_fate.STATE_MISSING
    assert "could not be copied" in fate.detail


@pytest.mark.parametrize(
    ("fate", "said"),
    [
        (None, "not determined"),
        (record_fate.RecordFate(), "none due"),
        (record_fate.RecordFate("kept", Path("/r/x-securingpass.json")), "kept as"),
        (record_fate.RecordFate("missing", None, "because"), "MISSING: because"),
    ],
)
def test_the_bundle_fact_names_each_state(fate: object, said: str) -> None:
    assert said in record_fate.describe_fate(fate)


# --- The report carries it ------------------------------------------------------


def test_the_outcome_block_carries_the_fate_and_a_missing_one_unaccounted_is_missing(
    tmp_path: Path,
) -> None:
    kept = record_fate.RecordFate("kept", tmp_path / "r-securingpass.json")
    block = build_outcome(
        status="success", securing_pass_started=True, securing_pass_record=kept
    )
    assert block["securing_pass_record"] == kept.as_block()
    # A securing pass that ran with nothing reporting its record is MISSING, never
    # `not_run`: a record nobody accounted for is not one that was kept.
    silent = build_outcome(status="success", securing_pass_started=True)
    assert silent["securing_pass_record"]["state"] == "missing"
    none_ran = build_outcome(status="success")
    assert none_ran["securing_pass_record"]["state"] == "not_run"


def test_a_missing_record_is_raised_in_the_reports_issues() -> None:
    from platterpus.parsers.rip_log import RipLog
    from platterpus.rip_report import build_report

    outcome = build_outcome(
        status="success",
        securing_pass_started=True,
        securing_pass_record=record_fate.RecordFate("missing", None, "the reason"),
    )
    report = build_report(RipLog(), outcome=outcome)
    raised = [
        i for i in report["issues"] if i["code"] == "securing_pass_record_missing"
    ]
    assert len(raised) == 1 and "the reason" in raised[0]["message"], raised
    clean = build_report(RipLog(), outcome=build_outcome(status="success"))
    assert not [
        i for i in clean["issues"] if i["code"] == "securing_pass_record_missing"
    ]


# --- The session bundle reads it back --------------------------------------------


def _album(root: Path, name: str, outcome: dict[str, object]) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / f"{name}.platterpus.json").write_text(
        json.dumps({"outcome": outcome}), encoding="utf-8"
    )
    return folder


def test_a_missing_securing_record_is_named_with_its_reason(tmp_path: Path) -> None:
    folder = _album(
        tmp_path,
        "secure reread",
        {
            "securing_pass_started": True,
            "securing_pass_record": {
                "state": "missing",
                "path": None,
                "detail": "the rip was cancelled",
            },
        },
    )
    line = record_fate.record_absences([folder], [], report_glob=_REPORT_GLOB)
    assert line.startswith("1 named by 1 rip report(s)"), line
    assert "secure reread: securing pass: the rip was cancelled" in line


def test_a_kept_record_the_scan_found_is_not_missing_and_one_it_did_not_is(
    tmp_path: Path,
) -> None:
    kept = tmp_path / "cyanrip-diagnostics-1-securingpass.json"
    folder = _album(
        tmp_path,
        "whole disc",
        {"securing_pass_record": {"state": "kept", "path": str(kept), "detail": None}},
    )
    found = record_fate.record_absences([folder], [kept], report_glob=_REPORT_GLOB)
    assert found == "none named by 1 rip report(s)"
    lost = record_fate.record_absences([folder], [], report_glob=_REPORT_GLOB)
    assert "did not find it" in lost


def test_an_album_record_written_after_the_report_is_not_called_missing(
    tmp_path: Path,
) -> None:
    late = tmp_path / "cyanrip-diagnostics-2.json"
    folder = _album(
        tmp_path,
        "cancel me",
        {"ripper_record": {"state": "absent", "detail": str(late)}},
    )
    assert record_fate.record_absences(
        [folder], [late], report_glob=_REPORT_GLOB
    ).startswith("none named")
    assert "album pass: cyanrip's record was absent" in record_fate.record_absences(
        [folder], [], report_glob=_REPORT_GLOB
    )


def test_what_the_reports_cannot_say_is_counted_never_read_as_nothing_missing(
    tmp_path: Path,
) -> None:
    no_report = tmp_path / "r16deemphon"
    no_report.mkdir()
    unreadable = tmp_path / "broken"
    unreadable.mkdir()
    (unreadable / "broken.platterpus.json").write_text("{not json", encoding="utf-8")
    line = record_fate.record_absences(
        [no_report, unreadable], [], report_glob=_REPORT_GLOB
    )
    assert "none named by 0 rip report(s)" in line
    assert "1 report(s) had no readable outcome block" in line
    assert "1 folder(s) have no rip report" in line


def test_the_filed_round_32_reports_name_exactly_two_undetermined_securing_passes(
    tmp_path: Path,
) -> None:
    """The run that found R9, read by the fix: schema v33 reports cannot say what
    became of a securing pass's record, and exactly two of them ran one."""
    # The rip reports, not the script run's own report beside them.
    reports = [
        path
        for path in sorted(_ROUND32.glob("round32full*report.json"))
        if path.name != "round32fullscriptreport.json"
    ]
    assert len(reports) >= 8, f"only {len(reports)} round-32 reports found"
    folders = []
    for index, report in enumerate(reports):
        folder = tmp_path / f"album{index:02d}"
        folder.mkdir()
        shutil.copyfile(report, folder / "rip.platterpus.json")
        folders.append(folder)
    records = sorted(_ROUND32.glob("round32fulljrecord*.json"))
    line = record_fate.record_absences(folders, records, report_glob=_REPORT_GLOB)
    assert line.startswith(f"none named by {len(reports)} rip report(s)"), line
    assert "had no readable outcome block" not in line, line
    assert "2 securing pass(es) ran under a report older than schema v34" in line, line
