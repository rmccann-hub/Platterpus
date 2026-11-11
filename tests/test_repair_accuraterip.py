# SPDX-License-Identifier: GPL-3.0-only
"""Gate G2: a CTDB-repaired track's audio, verified by AccurateRip (TASKS R138).

Round 39's plan (2026-11-11): *track 5's CTDB-repaired audio must be verified by
AccurateRip v2*. What is held here:

* **the worker asks once, after the commit**, with the disc's AccurateRip ID from
  the rip's log and the album's track count, and records per repaired track and
  per version what the database says (``ctdb/repair_accuraterip.py``). The fake
  database below reads the album's files AT the lookup, so a lookup made before
  the commit would find the read's checksums and fail the test;
* **every reason not to ask is said**: no client, no AccurateRip ID, a cancel, a
  client that raises, a repair that was refused;
* **the record names the match**: the owner's 2026-11-10 track 5 reads
  ``AccurateRip v1 134C0B9D matched (confidence 129); v2 BCF4E815 matched
  (confidence 200)`` in the EAC-layout log's ``Record:`` row, the report's
  ``record`` and the results pane, from one function;
* **expect-track-records grades G2**: v2 matched passes; v2 absent from a
  database that holds the disc fails; anything not determined is BLOCKED.

No audio from a disc (Critical rule 8): the worker's album is
``tests/test_ctdb_repair.py``'s seeded random PCM, and the dBAR bytes are
synthesised (``tests/test_accuraterip_db.py``).
"""

from __future__ import annotations

import dataclasses
import json
import struct
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from test_accuraterip_db import (
    DISC,
    DISC_ID_TEXT,
    TRACKS,
    reference_dbar,
)
from test_ctdb_repair import _Disc, _errors
from test_ctdb_repair_auto import _reverify_with, _test_repair, _track
from test_track_record import _album, _log, _repaired_result, _track5, _verified

from platterpus.accuraterip_crc import accuraterip_crcs
from platterpus.accuraterip_db_answer import (
    AR_MATCHED,
    AR_NOT_DETERMINED,
    AR_NOT_IN_DATABASE,
    ArDbAnswer,
)
from platterpus.adapters.accuraterip_db import (
    AccurateRipDbClient,
    AccurateRipDiscId,
    AccurateRipHttpImpl,
    DbarLookup,
    LookupState,
    read_reply,
)
from platterpus.ctdb.repair_accuraterip import lookup_for_repair, with_accuraterip
from platterpus.ctdb.repair_types import RepairRecord, RepairStatus
from platterpus.ctdb.repair_wording import repaired_text
from platterpus.eac_log_export import render_eac_style_log
from platterpus.rip_report import build_report
from platterpus.uiscript.track_record_grading import grade_track_records
from platterpus.workers.ctdb_repair_worker import CtdbRepairOutcome, CtdbRepairWorker

#: The line the owner's track 5 must carry once AccurateRip has been asked.
TRACK5_AR: str = (
    "AccurateRip v1 134C0B9D matched (confidence 129); "
    "v2 BCF4E815 matched (confidence 200)"
)


def _owners_lookup() -> DbarLookup:
    """The reference disc's database answer, from the synthesised file."""
    return AccurateRipHttpImpl(fetcher=lambda _u: reference_dbar()).lookup(DISC, TRACKS)


def _owners_result() -> Any:
    """2026-11-10's repaired result, with AccurateRip asked about track 5."""
    result = _repaired_result()
    record = with_accuraterip(result.repair, _owners_lookup())
    return dataclasses.replace(result, repair=record)


# --- the record's words ----------------------------------------------------------------


def test_track_5s_record_names_both_matches() -> None:
    """The line R138 asks for, in the log's Record row and the report's record."""
    result = _owners_result()
    row = result.repair.tracks[0]
    assert row.accuraterip_v1_database == ArDbAnswer(AR_MATCHED, confidence=129)
    assert row.accuraterip_v2_database == ArDbAnswer(AR_MATCHED, confidence=200)
    rip_log = _log(_verified(4), _track5())
    text = render_eac_style_log(rip_log, ctdb_result=result)
    record = next(x.strip() for x in text.splitlines() if "Record: repaired" in x)
    assert record.endswith(f"; {TRACK5_AR}"), record
    assert "not determined" not in record and "accurately ripped" not in record.lower()
    report = build_report(rip_log, ctdb_result=result)
    five = next(t for t in report["tracks"] if t["number"] == 5)
    assert five["record"]["line"].endswith(f"; {TRACK5_AR}")
    assert f"Record: {five['record']['line']}" == record  # one line, two surfaces
    _level, pane = repaired_text(result)
    assert f"Track 5: {TRACK5_AR}." in pane


def test_the_report_carries_the_answers_and_the_lookup() -> None:
    report = build_report(_log(_track5()), ctdb_result=_owners_result())
    repair = report["ctdb"]["repair"]
    (row,) = repair["tracks"]
    assert row["accuraterip_v2_database"] == {
        "answer": AR_MATCHED,
        "confidence": 200,
        "reason": None,
    }
    assert row["accuraterip_v1_database"]["confidence"] == 129
    lookup = repair["accuraterip_lookup"]
    assert lookup["state"] == "found" and lookup["responses_read"] == 13
    assert lookup["complete"] is True and lookup["trailing_bytes"] == 0
    assert lookup["url"].endswith("/f/0/2/dBAR-014-001d420f-013bb370-e20dfe0e.bin")


def test_a_record_without_a_lookup_still_says_not_determined() -> None:
    """Before R138's lookup (or with none made) the line keeps the third value."""
    text = render_eac_style_log(_log(_track5()), ctdb_result=_repaired_result())
    record = next(x for x in text.splitlines() if "Record: repaired" in x)
    assert "v1 134C0B9D: not determined; v2 BCF4E815: not determined" in record
    assert "matched" not in record


def test_each_answer_has_its_words() -> None:
    gone = ArDbAnswer(AR_NOT_IN_DATABASE, reason="AccurateRip holds this disc")
    unknown = ArDbAnswer(AR_NOT_DETERMINED, reason="the lookup failed: offline")
    result = _repaired_result()
    row = dataclasses.replace(
        result.repair.tracks[0],
        accuraterip_v1_database=gone,
        accuraterip_v2_database=unknown,
    )
    record = dataclasses.replace(result.repair, tracks=(row,))
    text = render_eac_style_log(
        _log(_track5()), ctdb_result=dataclasses.replace(result, repair=record)
    )
    line = next(x for x in text.splitlines() if "Record: repaired" in x)
    assert (
        "AccurateRip v1 134C0B9D: not in the AccurateRip database; v2 BCF4E815: not "
        "determined (AccurateRip holds this disc; the lookup failed: offline)"
    ) in line


# --- asking, and every reason not to ---------------------------------------------------


class _Recording(AccurateRipDbClient):
    """A database that records what it was asked and answers with ``answer``."""

    def __init__(self, answer: Any) -> None:
        self.asked: list[tuple[AccurateRipDiscId, int]] = []
        self._answer = answer

    def lookup(self, disc: AccurateRipDiscId, track_count: int) -> DbarLookup:
        self.asked.append((disc, track_count))
        return self._answer(disc, track_count)  # type: ignore[no-any-return]  # a test's callable


def _log_with_id(*tracks: object, disc_id: str = DISC_ID_TEXT) -> object:
    return SimpleNamespace(tracks=list(tracks), accuraterip_disc_id=disc_id)


def test_no_id_no_client_a_cancel_or_a_raise_each_say_why() -> None:
    client = _Recording(lambda *_a: _owners_lookup())
    no_id = lookup_for_repair(client, _log_with_id(disc_id=""), TRACKS)
    assert no_id.state is LookupState.FAILED and "no AccurateRip ID" in no_id.reason
    stopped = lookup_for_repair(client, _log_with_id(), TRACKS, cancelled=True)
    assert stopped.state is LookupState.FAILED and "stopped" in stopped.reason
    assert client.asked == []  # neither asked anything
    none = lookup_for_repair(None, _log_with_id(), TRACKS)
    assert "no AccurateRip client" in none.reason

    def _raise(*_a: object) -> DbarLookup:
        raise RuntimeError("a client that breaks its contract")

    raised = lookup_for_repair(_Recording(_raise), _log_with_id(), TRACKS)
    assert raised.state is LookupState.FAILED and "RuntimeError" in raised.reason
    asked = lookup_for_repair(client, _log_with_id(), TRACKS)
    assert asked.state is LookupState.FOUND and client.asked == [(DISC, TRACKS)]


def test_a_refused_repair_is_left_as_it_was() -> None:
    record = RepairRecord(RepairStatus.REFUSED, reason="a guard said no")
    assert with_accuraterip(record, _owners_lookup()) is record


def _database_of_the_files_on_disk(paths: list[Path]) -> Any:
    """A dBAR answer computed from the album's files AT the moment it is asked.

    Response 1 holds every track's v2, response 2 its v1, both of the files as
    they are when the lookup runs: so a lookup before the repair commits finds
    the read's checksums, and the repaired track's answers would not match.
    """

    def answer(disc: AccurateRipDiscId, count: int) -> DbarLookup:
        sums = [
            accuraterip_crcs(p.read_bytes(), n, count) for n, p in enumerate(paths, 1)
        ]
        raw = b""
        for confidence, pick in ((200, "v2"), (129, "v1")):
            raw += struct.pack("<BIII", count, disc.id1, disc.id2, disc.cddb)
            for crcs in sums:
                assert crcs is not None
                raw += struct.pack("<BII", confidence, getattr(crcs, pick), 0)
        return read_reply(raw, disc, count)

    return answer


def test_the_worker_asks_accuraterip_once_after_the_commit(
    tmp_path: Path, qapp: object
) -> None:
    disc = _Disc(tmp_path, 23, _errors())
    client = _Recording(_database_of_the_files_on_disk(disc.paths))
    worker = CtdbRepairWorker(
        disc.result,
        disc.paths[0].parent,
        client=disc.client,
        accuraterip=client,
        rip_log=_log_with_id(_track(1), _track(2), _track(3)),
        repair=_test_repair,
        reverify=_reverify_with(disc),
    )
    seen: list[CtdbRepairOutcome] = []
    worker.done.connect(seen.append)
    worker.run()
    record = seen[0].result.repair
    assert record is not None and record.status is RepairStatus.REPAIRED
    assert client.asked == [(DISC, 3)]  # once, for the disc, with its track count
    assert record.tracks, "the fixture's repair rewrote no track"
    for row in record.tracks:
        assert row.accuraterip_v2_database == ArDbAnswer(AR_MATCHED, confidence=200)
        assert row.accuraterip_v1_database == ArDbAnswer(AR_MATCHED, confidence=129)
    assert record.accuraterip_lookup is not None
    assert record.accuraterip_lookup.state == "found"


def test_a_worker_with_no_client_records_why(tmp_path: Path, qapp: object) -> None:
    disc = _Disc(tmp_path, 24, _errors())
    worker = CtdbRepairWorker(
        disc.result,
        disc.paths[0].parent,
        client=disc.client,
        rip_log=_log_with_id(_track(1), _track(2), _track(3)),
        repair=_test_repair,
        reverify=_reverify_with(disc),
    )
    seen: list[CtdbRepairOutcome] = []
    worker.done.connect(seen.append)
    worker.run()
    record = seen[0].result.repair
    assert record is not None and record.status is RepairStatus.REPAIRED
    for row in record.tracks:
        assert row.accuraterip_v2_database is not None
        assert row.accuraterip_v2_database.answer == AR_NOT_DETERMINED
        assert "no AccurateRip client" in row.accuraterip_v2_database.reason


# --- expect-track-records grades G2 ------------------------------------------------------


def _graded(tmp_path: Path, result: Any) -> Any:
    report, folder = _album(tmp_path, _log(_verified(4), _track5()), result)
    return grade_track_records(report, folder)


def test_g2_passes_when_v2_matches(tmp_path: Path) -> None:
    grade = _graded(tmp_path, _owners_result())
    assert grade.passed and not grade.blocked, grade.detail
    assert (
        "track 5's repaired audio is verified by AccurateRip v2 BCF4E815 "
        "(confidence 200)" in grade.detail
    )


def _with_v2(answer: ArDbAnswer, lookup: DbarLookup | None = None) -> Any:
    result = _owners_result()
    row = dataclasses.replace(result.repair.tracks[0], accuraterip_v2_database=answer)
    record = dataclasses.replace(result.repair, tracks=(row,))
    if lookup is not None:
        record = with_accuraterip(record, lookup)
        row = dataclasses.replace(record.tracks[0], accuraterip_v2_database=answer)
        record = dataclasses.replace(record, tracks=(row,))
    return dataclasses.replace(result, repair=record)


def test_g2_fails_when_the_database_holds_the_disc_and_not_the_checksum(
    tmp_path: Path,
) -> None:
    gone = ArDbAnswer(AR_NOT_IN_DATABASE, reason="AccurateRip holds this disc")
    grade = _graded(tmp_path, _with_v2(gone))
    assert not grade.passed and not grade.blocked
    assert (
        "track 5 was repaired from CTDB and AccurateRip v2 does not verify it: "
        "BCF4E815 is not in the database" in grade.detail
    )


def test_g2_is_blocked_when_not_determined(tmp_path: Path) -> None:
    """A loop over a literal list, not a parametrize over computed values
    (`tests/test_dynamic_sweeps_declare_a_floor.py`), with its own floor."""
    answers = [
        ArDbAnswer(AR_NOT_DETERMINED, reason="the AccurateRip lookup failed: offline"),
        ArDbAnswer(AR_MATCHED, confidence=0),  # a match nobody submitted
    ]
    assert len(answers) == 2
    for place, answer in enumerate(answers):
        folder = tmp_path / str(place)
        folder.mkdir()
        grade = _graded(folder, _with_v2(answer))
        assert not grade.passed and grade.blocked, grade.detail
        assert "track 5's AccurateRip v2 (BCF4E815) is not determined" in grade.detail


def test_g2_is_blocked_for_a_disc_accuraterip_does_not_have(tmp_path: Path) -> None:
    """A 404 says nothing about the track: AccurateRip cannot verify the repair."""
    gone = DbarLookup(LookupState.NOT_IN_DATABASE, reason="no entry (HTTP 404)")
    result = _repaired_result()
    record = with_accuraterip(result.repair, gone)
    assert record.tracks[0].accuraterip_v2_database is not None
    assert record.tracks[0].accuraterip_v2_database.answer == AR_NOT_IN_DATABASE
    grade = _graded(tmp_path, dataclasses.replace(result, repair=record))
    assert not grade.passed and grade.blocked, grade.detail


def test_g2_is_blocked_on_a_report_from_before_the_lookup(tmp_path: Path) -> None:
    grade = _graded(tmp_path, _repaired_result())
    assert not grade.passed and grade.blocked, grade.detail
    assert "the report records no AccurateRip lookup of the repaired audio" in (
        grade.detail
    )


def test_g2_has_nothing_to_grade_without_a_repair(tmp_path: Path) -> None:
    report = json.loads(json.dumps(build_report(_log(_verified(1))), default=str))
    grade = grade_track_records(report, tmp_path)
    assert grade.passed, grade.detail
    assert "no track was repaired from CTDB" in grade.detail


def test_g2_reads_ctdb_repair_not_the_record(tmp_path: Path) -> None:
    """The subject is ctdb.repair: a record rewritten to look matched is no pass."""
    report, folder = _album(tmp_path, _log(_verified(4), _track5()), _repaired_result())
    for track in report["tracks"]:
        if track["number"] == 5:
            track["record"]["line"] = track["record"]["line"].replace(
                "not determined", "matched (confidence 200)"
            )
    (folder / "rip (EAC-compatible).log").unlink()
    grade = grade_track_records(report, folder)
    assert grade.blocked and not grade.passed, grade.detail
