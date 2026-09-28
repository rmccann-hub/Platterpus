# SPDX-License-Identifier: GPL-3.0-only
"""A partial rip makes no CTDB claim about the whole disc — read off the filed runs.

**The defect** (the 2026-09-28 Full run, ``docs/handshake/artifactsround28/``): five
reports of 2-track rips said CTDB ``not_in_db``, *"this disc is not in CTDB"*,
``trustworthy: true``, ``gates.ctdb: "ran"``. The whole-disc rips of the same disc,
in the same run, found it with 102 entries. The CTDB TOC is built from the files
ripped (``ctdb/toc.py::disc_toc_from_files``), so two files made a two-track disc
that does not exist, and the 404 for it read as a real "not in the database".

**It is older than that run.** Every finished partial rip filed in rounds 26 and
27 — eleven of them — carries the same false verdict, and the three whole-disc
rips of the same disc there found 102 entries. So the subjects here are the
filed logs and reports themselves, derived from the filesystem with a floor, not a
fixture shaped like them: what is tested is the footer cyanrip actually wrote
(``Rip completed:  yes (2 of 14 tracks)``) and the verdict the app actually filed.

Nothing here touches the network or decodes audio: the CTDB client is a recorder,
and the FLACs are zero-byte stand-ins named by the real log (never audio, rule #8).
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

import pytest

from platterpus import album_loudness, rip_files, rip_report
from platterpus.adapters.ctdb_client import CTDBClient, CtdbLookupResult
from platterpus.ctdb import diagnose
from platterpus.ctdb.coverage import (
    MAX_CD_TRACKS,
    NOT_WHOLE_DISC_VERDICT,
    disc_track_count,
)
from platterpus.ctdb.toc import DiscToc
from platterpus.ctdb.verify import Verdict, not_whole_disc_result
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.workers.ctdb_worker import verify_rip_dir

_HANDSHAKE: Path = Path(__file__).resolve().parents[1] / "docs" / "handshake"

#: The rounds filed BEFORE the fix. Each of their finished partial rips reported
#: `not_in_db`; a round filed after it should not, so the "as filed" assertion is
#: scoped to these rather than to "every round" (which would turn red on the first
#: honest report). `artifactsround28` is the run that found it; it joins the
#: population as soon as its bundle is on the branch this runs on.
_FILED_BEFORE_THE_FIX: frozenset[str] = frozenset(
    {"artifactsround26", "artifactsround27", "artifactsround28"}
)

#: A named member the population must contain, so a glob that silently matches
#: the wrong files (or none) cannot pass: the label AND the subject.
_REQUIRED_PARTIAL: str = "artifactsround27/round27fullderivedmp3.log"
#: And the run that found the defect, 2026-09-28: its MP3 rip is one of the five
#: that were filed as "this disc is not in CTDB". Named on its own so the round
#: that motivated the fix cannot drop out of the population unnoticed.
_REQUIRED_PARTIAL_ROUND_28: str = "artifactsround28/round28fullderivedmp3.log"

#: Floors, measured 2026-09-28: rounds 26-27 hold 11 finished partial rips with a
#: report and 3 whole-disc ones; round 28 adds 5 and 2. Set below the count so a
#: new round only adds.
_MIN_PARTIAL: int = 5
_MIN_WHOLE: int = 1


@dataclass(frozen=True)
class _FiledRip:
    """One filed rip: its real log, what that log parses to, and its real report."""

    log: Path
    text: str
    parsed: RipLog
    names: tuple[str, ...]
    report: dict[str, object]

    @property
    def key(self) -> str:
        return self.log.relative_to(_HANDSHAKE).as_posix()

    @property
    def round_dir(self) -> str:
        return self.log.parent.name

    @property
    def disc_tracks(self) -> int | None:
        return disc_track_count(self.parsed)

    @property
    def partial(self) -> bool:
        total = self.disc_tracks
        return total is not None and len(self.names) < total

    def filed_ctdb(self) -> dict[str, object]:
        block = self.report.get("ctdb")
        return block if isinstance(block, dict) else {}


@functools.cache
def _filed_rips() -> tuple[_FiledRip, ...]:
    """Every filed cyanrip log whose sibling report records a FINISHED rip.

    The pairing is the bundles' own naming (``round27fullderivedmp3.log`` beside
    ``round27fullderivedmp3report.json``). A cancelled or failed rip is left out:
    no post-rip check runs on one, so it has no CTDB verdict to be right or wrong.
    """
    found: list[_FiledRip] = []
    for log in sorted(_HANDSHAKE.glob("artifactsround*/*.log")):
        report_path = log.with_name(log.name[: -len(".log")] + "report.json")
        if not report_path.is_file():
            continue
        text = log.read_text(encoding="utf-8")
        if not looks_like_cyanrip_log(text):
            continue  # the EAC-layout companion logs carry no footer
        report = json.loads(report_path.read_text(encoding="utf-8"))
        outcome = report.get("outcome")
        if not isinstance(outcome, dict) or outcome.get("status") != "success":
            continue
        parsed = parse_cyanrip_log(text)
        found.append(
            _FiledRip(log, text, parsed, rip_files.declared_names(parsed), report)
        )
    return tuple(found)


def _partial() -> list[_FiledRip]:
    return [rip for rip in _filed_rips() if rip.partial]


def _whole() -> list[_FiledRip]:
    return [
        rip
        for rip in _filed_rips()
        if rip.disc_tracks is not None and len(rip.names) == rip.disc_tracks
    ]


def _album_from(rip: _FiledRip, root: Path) -> Path:
    """The album folder the finish handler hands the worker, rebuilt from the
    filed log: the log byte-for-byte, and one zero-byte stand-in per file it names."""
    album = root / rip.log.stem
    album.mkdir()
    (album / rip.log.name).write_text(rip.text, encoding="utf-8")
    for name in rip.names:
        (album / name).write_bytes(b"")
    return album


class _RecordingClient(CTDBClient):
    """Answers "not in the database" and records every TOC it was asked about."""

    def __init__(self) -> None:
        self.tocs: list[DiscToc] = []

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        self.tocs.append(toc)
        return CtdbLookupResult(entries=())


def _refuse(path: Path) -> NoReturn:
    raise AssertionError(f"{path} was probed or decoded for a partial rip")


def _sectors(_path: Path) -> int:
    return 30_000


# --- the population, and its floors ----------------------------------------


def test_the_filed_population_is_what_this_file_claims() -> None:
    """Floors first, so every sweep below is known to have examined something."""
    partial = {rip.key for rip in _partial()}
    assert len(partial) >= _MIN_PARTIAL, sorted(partial)
    assert _REQUIRED_PARTIAL in partial, sorted(partial)
    assert len(_whole()) >= _MIN_WHOLE
    # The required member is the shape the defect report names: tracks 1,2 of 14,
    # read off the log's own lines rather than assumed.
    required = next(rip for rip in _partial() if rip.key == _REQUIRED_PARTIAL)
    assert "Tracks to rip:  1, 2" in required.text
    assert "Disc tracks:    14" in required.text
    assert (len(required.names), required.disc_tracks) == (2, 14)
    found = next(rip for rip in _partial() if rip.key == _REQUIRED_PARTIAL_ROUND_28)
    assert "Tracks to rip:  1, 2" in found.text
    assert (len(found.names), found.disc_tracks) == (2, 14)


# --- the verdict, from the real logs ---------------------------------------


def test_every_filed_partial_rip_is_answered_without_a_lookup(tmp_path: Path) -> None:
    examined = 0
    for rip in _partial():
        client = _RecordingClient()
        result = verify_rip_dir(
            client,
            _album_from(rip, tmp_path),
            samples_probe=_refuse,
            decoder=_refuse,
        )
        assert client.tocs == [], f"{rip.key}: CTDB was asked about a partial rip"
        assert result is not None
        assert result.verdict is Verdict.NOT_WHOLE_DISC, rip.key
        assert (
            f"{len(rip.names)} of the disc's {rip.disc_tracks} tracks" in result.message
        )
        assert result.trustworthy is None
        examined += 1
    assert examined >= _MIN_PARTIAL


def test_every_filed_whole_disc_rip_is_still_looked_up_with_every_track(
    tmp_path: Path,
) -> None:
    """Whole-disc behaviour unchanged: one lookup, with the disc's full TOC."""
    examined = 0
    for rip in _whole():
        client = _RecordingClient()
        verify_rip_dir(
            client,
            _album_from(rip, tmp_path),
            samples_probe=_sectors,
            decoder=lambda _p: b"\x00" * 16,
        )
        assert len(client.tocs) == 1, rip.key
        assert client.tocs[0].num_tracks == rip.disc_tracks == len(rip.names)
        examined += 1
    assert examined >= _MIN_WHOLE


def test_the_not_in_db_those_reports_filed_was_false() -> None:
    """The artifact half: the reports as filed said "not in CTDB", and a whole-disc
    rip of the SAME disc (same MusicBrainz disc ID, which is computed from the full
    TOC) in the same run found it. So the verdict was a claim about the wrong disc,
    not a finding about this one — which is what the new verdict stops us making."""
    found_in_ctdb: dict[tuple[str, str], int] = {}
    for rip in _whole():
        entries = rip.filed_ctdb().get("entry_count")
        if isinstance(entries, int) and entries > 0 and rip.parsed.disc_id:
            found_in_ctdb[(rip.round_dir, rip.parsed.disc_id)] = entries

    contradicted = 0
    for rip in _partial():
        if rip.round_dir not in _FILED_BEFORE_THE_FIX:
            continue
        filed = rip.filed_ctdb()
        assert filed.get("verdict") == "not_in_db", rip.key
        assert filed.get("entry_count") == 0, rip.key
        assert rip.parsed.disc_id, f"{rip.key}: floor — the log names its disc"
        assert (rip.round_dir, rip.parsed.disc_id) in found_in_ctdb, (
            f"{rip.key}: no whole-disc rip of the same disc in the same run found "
            "it in CTDB — the contradiction this file rests on is not in the data"
        )
        contradicted += 1
    assert contradicted >= _MIN_PARTIAL


def test_the_ctdb_guard_and_the_album_loudness_label_agree_on_every_filed_log() -> None:
    """Two surfaces answer "was this the whole disc?" off the same footer; test the
    RELATION, which neither module's own tests can express."""
    sides: set[bool] = set()
    for rip in _filed_rips():
        covers = album_loudness.coverage(rip.parsed)
        if covers is None or rip.disc_tracks is None:
            continue
        loudness_says_part = covers["state"] == album_loudness.PART_OF_DISC
        assert loudness_says_part == rip.partial, rip.key
        sides.add(rip.partial)
    assert sides == {True, False}, "floor: both a partial and a whole rip compared"


# --- every surface that renders the verdict ---------------------------------


def _gates(*, ctdb_enabled: bool = True) -> dict[str, object]:
    # Only CTDB is switched on: every other gate reading "ran" with no result
    # passed in would (rightly) file `verification_result_missing` about ITSELF,
    # which is noise in a test about the CTDB gate.
    return rip_report.build_gates(
        ctdb_enabled=ctdb_enabled,
        flac_verify_enabled=False,
        backend_self_verifies=False,
        recompress_enabled=False,
        backend_maxes_compression=False,
        transcode_requested=False,
        rip_status="success",
    )


def _report_for(result: object) -> dict[str, object]:
    rip = next(rip for rip in _partial() if rip.key == _REQUIRED_PARTIAL)
    return rip_report.build_report(
        rip.parsed,
        ctdb_result=result,
        gates=_gates(),
        outcome={"status": "success"},
        disc_track_total=2,
        generated_at="2026-09-28T00:00:00+00:00",
    )


def test_the_report_says_not_run_and_never_that_the_check_ran() -> None:
    report = _report_for(not_whole_disc_result(2, 14))
    ctdb = report["ctdb"]
    assert isinstance(ctdb, dict)
    assert ctdb["verdict"] == NOT_WHOLE_DISC_VERDICT == Verdict.NOT_WHOLE_DISC.value
    assert ctdb["trustworthy"] is None
    verification = report["verification"]
    assert isinstance(verification, dict)
    assert verification["gates"]["ctdb"] == rip_report.NOT_WHOLE_DISC_GATE
    issues = report["issues"]
    assert isinstance(issues, list)
    codes = {issue["code"] for issue in issues}
    assert not codes & rip_report.VERIFICATION_DROPPED_CODES
    # Not run is not a problem to report: the user chose the tracks.
    assert not [i for i in issues if "CTDB" in str(i.get("message"))], issues
    assert "not in CTDB" not in json.dumps(report)


def test_a_whole_disc_not_in_db_still_reads_as_a_check_that_ran() -> None:
    """The gate correction keys on the verdict, not on the result being present."""
    from platterpus.ctdb.verify import CtdbVerifyResult

    report = _report_for(
        CtdbVerifyResult(Verdict.NOT_IN_DATABASE, message="this disc is not in CTDB")
    )
    verification = report["verification"]
    assert isinstance(verification, dict)
    assert verification["gates"]["ctdb"] == "ran"


def test_the_details_tab_line_is_the_verdicts_own_sentence() -> None:
    from platterpus.ui.rip_progress import ctdb_verdict_level, ctdb_verdict_line

    result = not_whole_disc_result(2, 14)
    line = ctdb_verdict_line(result)
    assert line == (
        "CTDB: not run — CTDB verifies whole discs, and this rip has 2 of the "
        "disc's 14 tracks"
    )
    assert "database" not in line  # it must never fall through to "not in the DB"
    assert ctdb_verdict_level(result) == "neutral"  # not a pass, not a failure


def test_ctdb_calibrate_on_a_partial_folder_asks_nothing(tmp_path: Path) -> None:
    """`--ctdb-calibrate` on a partial rip's folder: the verdict, and no sweep —
    calibration's own lookup would ask about the same nonexistent disc."""
    rip = next(rip for rip in _partial() if rip.key == _REQUIRED_PARTIAL)
    client = _RecordingClient()
    lines: list[str] = []
    code = diagnose.run_diagnostics(
        _album_from(rip, tmp_path),
        calibrate_crc=True,
        out=lines.append,
        client=client,
        decoder=_refuse,
        samples_probe=_sectors,
    )
    text = "\n".join(lines)
    assert code == 0
    assert client.tocs == []
    assert f"Verdict:    {NOT_WHOLE_DISC_VERDICT}" in text
    assert "not the disc's TOC" in text
    assert "Calibration skipped" in text
    assert "isn't in CTDB" not in text


# --- the count itself --------------------------------------------------------


class _Log:
    def __init__(self, total: object) -> None:
        self.rip_completed_total = total


#: "No log object at all", as opposed to a log whose footer is absent (`None`).
_NO_LOG: str = "<no log at all>"


@pytest.mark.parametrize(
    ("footer_total", "fallback", "expected"),
    [
        (14, None, 14),  # the footer alone
        (14, 2, 14),  # the footer wins over a disagreeing probe count
        (None, 14, 14),  # no footer: the probe count
        (_NO_LOG, 14, 14),  # no log at all: the probe count
        (_NO_LOG, None, None),  # nothing says: not known, never "whole"
        (0, None, None),  # not a CD track count
        (MAX_CD_TRACKS + 1, None, None),
        (True, None, None),  # a bool is not "one track"
        ("14", None, None),  # a string is not a parsed count
        (None, 0, None),  # the GUI's "unknown" probe count
        (None, -3, None),
    ],
)
def test_disc_track_count_reads_the_footer_first_and_range_checks_both(
    footer_total: object, fallback: object, expected: int | None
) -> None:
    log = None if footer_total == _NO_LOG else _Log(footer_total)
    assert disc_track_count(log, fallback=fallback) == expected


def test_the_rebuilt_album_is_read_the_way_the_filed_one_was(tmp_path: Path) -> None:
    """Stand-in check: `_album_from` must give rip_files the SAME answer the filed
    log gives — same names, from the log, with the log's footer — or the sweeps
    above would be testing the fixture rather than the product."""
    rip = next(rip for rip in _partial() if rip.key == _REQUIRED_PARTIAL)
    file_set = rip_files.rip_master_files(_album_from(rip, tmp_path))
    assert file_set.authoritative  # scoped by the log, not a folder scan
    assert tuple(p.name for p in file_set.files) == rip.names
    assert disc_track_count(file_set.rip_log) == rip.disc_tracks == 14
