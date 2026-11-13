# SPDX-License-Identifier: GPL-3.0-only
"""``expect-track-records``: every track's record is truthful, in both our records.

**Why this grader exists** (round 39's gate G3, "the record", the owner-approved
plan of 2026-11-11). Two wordings must never appear on a track:

* **``Accurately ripped`` on a track a CTDB repair rewrote.** EAC's phrase vouches
  for the audio, and the file is no longer the read the phrase describes;
* **``Copy OK`` (or any ``OK``) over reads that disagree.** EAC's own fault
  (``docs/eac-parity.md`` Part F row 8): it prints ``Copy OK`` when its Test and
  Copy CRCs differ, and a reader or a logchecker reads the ``OK``.

And every audio track must carry a record of how it was verified (the EAC-layout
log's ``Record:`` row, the report's per-track ``record``). **And gate G2** (TASKS
R138): every track a CTDB repair rewrote must be verified by AccurateRip v2,
graded by :mod:`platterpus.uiscript.repair_accuraterip_grading` from
``ctdb.repair``; not determined there is BLOCKED, never a pass.

**The subject comes from the facts, not from the label it grades.** Which tracks
were repaired is read from ``ctdb.repair`` (status ``repaired``, its ``tracks``);
which tracks' reads disagreed from each track's own fields (a Test CRC unlike the
Copy CRC, ``secure_rerip_converged`` false, a kept-at-limit read, ``.30``'s
``other_reads``, a first pass that did not converge) and the chase's
``verified_rereads``. The record's own flags are added to that set, never used in
place of it, so a record that under-reports its own track still meets the check
(``CLAUDE.md``: *where a check matches on a label, make it also require the
subject*).

**Severity: ARCHIVAL**, declared here before any run (``docs/testing.md`` →
*Acceptance severity*): the EAC-layout log and the report are the record of the
rip, and a track called accurate or OK that is neither is the *wrong and reported
as fine* outcome Part F1 names as the worst.

Pure; reads the folder's EAC-layout log (a small text file) and the report it is
handed; never raises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from platterpus.track_record import RECORD_KINDS, RECORD_REPAIRED
from platterpus.uiscript.artifact_grading import Grade
from platterpus.uiscript.repair_accuraterip_grading import grade_repaired_v2

#: The EAC-layout log's name ends with this (``ui/main_window_rip._write_eac_log``).
EAC_LOG_SUFFIX: Final[str] = " (EAC-compatible).log"
#: EAC's phrase, matched without case: a lower-case copy vouches just the same.
_ACCURATE: Final[re.Pattern[str]] = re.compile(r"accurately ripped", re.IGNORECASE)
#: Any ``OK`` as a word, in the block's status line (``Copy OK``, ``OK``).
_OK: Final[re.Pattern[str]] = re.compile(r"\bOK\b")
#: A track block's rows are indented five spaces (``eac_log_export._track_block``).
_ROW_INDENT: Final[str] = "    "
#: A track block opens ``Track  5`` / ``Track 14`` at column 0.
_TRACK_HEADER: Final[re.Pattern[str]] = re.compile(r"^Track\s{1,2}(?P<n>\d{1,3})\s*$")


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def repaired_subjects(report: Mapping[str, Any]) -> set[int]:
    """The tracks ``ctdb.repair`` says it rewrote: status ``repaired`` only."""
    ctdb = report.get("ctdb")
    repair = ctdb.get("repair") if isinstance(ctdb, Mapping) else None
    if not isinstance(repair, Mapping) or repair.get("status") != "repaired":
        return set()
    rows = repair.get("tracks")
    found: set[int] = set()
    for row in rows if isinstance(rows, list) else ():
        number = _int(row.get("track")) if isinstance(row, Mapping) else None
        if number is not None:
            found.add(number)
    return found


def _disagreed(track: Mapping[str, Any]) -> bool:
    """The track's own fields show reads that gave more than one value."""
    test_crc = str(track.get("test_crc") or "").upper()
    copy_crc = str(track.get("copy_crc") or "").upper()
    if test_crc and copy_crc and test_crc != copy_crc:
        return True
    if track.get("secure_rerip_converged") is False:
        return True
    if track.get("secure_rerip_kept_read") is not None:
        return True
    others = track.get("other_reads")
    if isinstance(others, Mapping) and (others.get("reads") or others.get("not_kept")):
        return True
    first = track.get("first_pass_reread")
    return isinstance(first, Mapping) and first.get("secure_rerip_converged") is False


def disagreeing_subjects(report: Mapping[str, Any]) -> set[int]:
    """The tracks whose reads disagreed, from their own fields and the chase."""
    found: set[int] = set()
    for track in report.get("tracks") or ():
        if not isinstance(track, Mapping):
            continue
        number = _int(track.get("number"))
        if number is not None and _disagreed(track):
            found.add(number)
    read_speed = report.get("read_speed")
    secure = read_speed.get("secure_rerip") if isinstance(read_speed, Mapping) else None
    chased = secure.get("verified_rereads") if isinstance(secure, Mapping) else None
    for number in chased if isinstance(chased, list) else ():
        if _int(number) is not None:
            found.add(number)
    return found


def eac_log_blocks(text: str) -> dict[int, list[str]]:
    """``{track: its block's lines}`` from an EAC-layout log's text.

    A block opens at ``Track NN`` and holds every following line that is blank or
    indented as a track's rows are (five spaces; four is enough); it ends at the
    first other line (the next track, or the status report, whose count lines are
    indented by one or two), so `` 14 track(s) accurately ripped`` below the
    blocks is never read as a track's.
    """
    blocks: dict[int, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        header = _TRACK_HEADER.match(line)
        if header:
            current = blocks.setdefault(int(header.group("n")), [])
            continue
        if current is None:
            continue
        if line and not line.startswith(_ROW_INDENT):
            current = None
            continue
        current.append(line)
    return blocks


def _eac_log_path(folder: Path) -> Path | None:
    try:
        found = sorted(folder.glob(f"*{EAC_LOG_SUFFIX}"))
    except OSError:
        return None
    return found[0] if found else None


def _status_line(block: list[str]) -> str:
    """The block's last non-blank line: the track's verdict in EAC's layout."""
    for line in reversed(block):
        if line.strip():
            return line.strip()
    return ""


def _grade_eac_log(
    blocks: dict[int, list[str]],
    repaired: set[int],
    disagree: set[int],
    data_tracks: set[int],
) -> list[str]:
    """Every problem the EAC-layout log's blocks show, one sentence each."""
    problems: list[str] = []
    for number, block in sorted(blocks.items()):
        records = [line.strip() for line in block if line.strip().startswith("Record:")]
        if number not in data_tracks and not records:
            problems.append(f"track {number} has no Record: row in the EAC-layout log")
        if number in repaired:
            if any(_ACCURATE.search(line) for line in block):
                problems.append(
                    f"track {number} was repaired from CTDB and its EAC-layout block "
                    "says Accurately ripped"
                )
            if not any("repaired from CTDB" in line for line in records):
                problems.append(
                    f"track {number} was repaired from CTDB and its Record: row does "
                    "not say so"
                )
        status = _status_line(block)
        if (number in repaired or number in disagree) and _OK.search(status):
            why = (
                "was repaired from CTDB"
                if number in repaired
                else "had reads that disagree"
            )
            problems.append(f"track {number} {why} and its status line says {status!r}")
    return problems


def _grade_report(
    report: Mapping[str, Any], repaired: set[int], disagree: set[int]
) -> tuple[list[str], int]:
    """The report's per-track ``record`` problems, and how many records were read."""
    problems: list[str] = []
    read = 0
    for track in report.get("tracks") or ():
        if not isinstance(track, Mapping):
            continue
        number = _int(track.get("number"))
        record = track.get("record")
        if not isinstance(record, Mapping):
            problems.append(f"track {number} has no record in the report")
            continue
        read += 1
        kind, line = record.get("kind"), str(record.get("line") or "")
        if kind not in RECORD_KINDS or not line:
            problems.append(f"track {number}'s record is not one we know: {kind!r}")
        if number in repaired and (kind != RECORD_REPAIRED or _ACCURATE.search(line)):
            problems.append(
                f"track {number} was repaired from CTDB and its report record reads "
                f"{kind!r}: {line!r}"
            )
        if number in disagree and _OK.search(line):
            problems.append(
                f"track {number} had reads that disagree and its record says OK"
            )
    return problems, read


def grade_track_records(report: Mapping[str, Any], folder: Path) -> Grade:
    """PASS when no track carries a banned wording and every track has a record.

    FAIL on any ``Accurately ripped`` for a repaired track, any ``OK`` over reads
    that disagree, or a missing record, in the EAC-layout log or the report, or
    a repaired track AccurateRip v2 does not hold (G2). BLOCKED when the report
    predates per-track records (schema 45), holds no track to examine (a check
    satisfied by finding nothing is decoration), or a repaired track's
    AccurateRip v2 is not determined.
    """
    tracks = [t for t in (report.get("tracks") or ()) if isinstance(t, Mapping)]
    if not tracks:
        return Grade(
            False, "the report lists no track, so no record was examined", blocked=True
        )
    if not any(isinstance(t.get("record"), Mapping) for t in tracks):
        return Grade(
            False,
            "the report carries no per-track record (schema 45 or later writes one), "
            "so how each track was verified is not determined",
            blocked=True,
        )
    repaired = repaired_subjects(report)
    disagree = disagreeing_subjects(report)
    for track in tracks:
        record = track.get("record")
        number = _int(track.get("number"))
        if isinstance(record, Mapping) and number is not None:
            if record.get("repaired") is True:
                repaired.add(number)
            if record.get("reads_disagree") is True:
                disagree.add(number)
    data_tracks = {
        n
        for t in tracks
        if t.get("data_crc32") and (n := _int(t.get("number"))) is not None
    }
    problems, read = _grade_report(report, repaired, disagree)
    path = _eac_log_path(folder)
    # Said, not silent: with `write_eac_log_after_rip` off (the default until
    # 2026-11-12, and still a user's choice) there is no EAC-layout log to read,
    # and the step grades the report's records alone.
    where = "the report (no EAC-layout log in the folder, so the report alone)"
    if path is not None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return Grade(False, f"could not read {path.name}: {exc}")
        blocks = eac_log_blocks(text)
        if not blocks:
            problems.append(f"{path.name} has no track block to read")
        problems += _grade_eac_log(blocks, repaired, disagree, data_tracks)
        where = f"the report and {path.name} ({len(blocks)} track blocks)"
    # G2 (TASKS R138): each repaired track's AccurateRip v2, from `ctdb.repair`.
    v2 = grade_repaired_v2(report)
    problems += v2.problems
    subjects = (
        f"repaired from CTDB: {sorted(repaired) or 'none'}; reads disagreed: "
        f"{sorted(disagree) or 'none'}"
    )
    if problems:
        return Grade(False, "; ".join(problems) + f" ({subjects})")
    held = (
        f"{read} track records read in {where}; no Accurately ripped on a repaired "
        f"track and no OK over reads that disagree ({subjects}); {v2.summary}"
    )
    if v2.undetermined:  # not determined is never a pass
        return Grade(False, held, blocked=True)
    return Grade(True, held)
