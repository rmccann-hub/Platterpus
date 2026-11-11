# SPDX-License-Identifier: GPL-3.0-only
"""Gate G2: a CTDB-repaired track's audio is verified by AccurateRip v2.

**Why** (round 39's gate G2, TASKS R138, the owner-approved plan of 2026-11-11).
A repair is proved against CTDB, whose parity drove it; AccurateRip is the
witness CTDB is not. Since 2026-11-11 the repair asks AccurateRip's database
about each repaired track's own v1 and v2 (``ctdb/repair_accuraterip.py``) and
the report records the answer per track (``ctdb.repair.tracks[].
accuraterip_v2_database``, schema 45). ``expect-track-records`` grades G3 (the
record) and, through :func:`grade_repaired_v2`, this.

**The subject is ``ctdb.repair``**, never the record's line: the tracks a
``repaired`` repair names are the ones graded, so a report whose record hides a
repair cannot skip the check. For each, one of three:

* **passes**: AccurateRip v2 matched the repaired audio, at a confidence;
* **fails**: AccurateRip holds the disc and not this checksum (the database was
  read whole) — the repair produced audio AccurateRip does not recognise;
* **not determined** (the step is BLOCKED, never passed): no lookup recorded (a
  report from before R138), the lookup failed, the reply was cut short, or
  AccurateRip has no entry for the disc at all, so it cannot verify anything.

A report with no repaired track has nothing for G2 to grade, and says so.
**Severity: ARCHIVAL**, as ``track_record_grading`` declares for the verb. Pure;
reads the report it is handed; never raises.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from platterpus.accuraterip_db_answer import AR_MATCHED, AR_NOT_IN_DATABASE


@dataclass(frozen=True)
class V2Grade:
    """G2's findings, one sentence each: what failed, what is not known, what held."""

    problems: list[str] = field(default_factory=list)
    undetermined: list[str] = field(default_factory=list)
    verified: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """One clause for the step's detail: what G2 found, or that it had nothing."""
        if not (self.problems or self.undetermined or self.verified):
            return "G2: no track was repaired from CTDB, so AccurateRip v2 had none"
        return "G2: " + "; ".join(self.problems + self.undetermined + self.verified)


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _repair(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
    ctdb = report.get("ctdb")
    repair = ctdb.get("repair") if isinstance(ctdb, Mapping) else None
    if isinstance(repair, Mapping) and repair.get("status") == "repaired":
        return repair
    return None


def grade_repaired_v2(report: Mapping[str, Any]) -> V2Grade:
    """G2 over every track ``ctdb.repair`` rewrote. Never raises."""
    grade = V2Grade()
    repair = _repair(report)
    if repair is None:
        return grade
    lookup = repair.get("accuraterip_lookup")
    disc_state = lookup.get("state") if isinstance(lookup, Mapping) else None
    rows = repair.get("tracks")
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, Mapping) or _int(row.get("track")) is None:
            continue
        number = row["track"]
        crc = str(row.get("accuraterip_v2_after") or "no checksum")
        v2 = row.get("accuraterip_v2_database")
        if not isinstance(v2, Mapping):
            grade.undetermined.append(
                f"track {number}'s AccurateRip v2 ({crc}) is not determined: the "
                "report records no AccurateRip lookup of the repaired audio"
            )
            continue
        answer, reason = v2.get("answer"), str(v2.get("reason") or "no reason given")
        confidence = _int(v2.get("confidence"))
        if answer == AR_MATCHED and confidence is not None and confidence > 0:
            grade.verified.append(
                f"track {number}'s repaired audio is verified by AccurateRip v2 "
                f"{crc} (confidence {confidence:,})"
            )
        elif answer == AR_NOT_IN_DATABASE and disc_state == "found":
            grade.problems.append(
                f"track {number} was repaired from CTDB and AccurateRip v2 does not "
                f"verify it: {crc} is not in the database ({reason})"
            )
        else:
            grade.undetermined.append(
                f"track {number}'s AccurateRip v2 ({crc}) is not determined: {reason}"
            )
    return grade
