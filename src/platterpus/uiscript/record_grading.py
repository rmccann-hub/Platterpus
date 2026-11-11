"""Pure graders that read what a rip's REPORT already computed: CTDB, gates, offset.

**Why this module exists** (the review of the owner's 2026-11-03 Full run, on
0.7.117 with cyanrip ``.28``). Three steps passed without checking their subject,
and each time the answer was already in the report:

* ``expect-ctdb whole`` passed a CTDB "match" at confidence 1 against 1,524
  disagreeing submissions, while the report's own ``ctdb.outvoted`` was true and
  its ``ctdb.message`` said the match "does not corroborate the rip" (A3).
* ``expect-verification`` passed a check that RAN and FAILED: a gate reading
  ``"ran — failed"`` satisfied its floor, so a FLAC failing ``flac --test``, or a
  WavPack that is not its master, went green (C1).
* nothing graded the read offset a rip used, though the report computes
  ``rip.read_offset_check`` (C3).

**Every grader reads the report's own verdict rather than recomputing it**
(``CLAUDE.md``: one predicate, N callers). The weight behind a CTDB match is
``ctdb.verify.CtdbVerifyResult.outvoted``, serialised as ``ctdb.outvoted``; the
gate states are :mod:`platterpus.verification_gates`'s; the offset decision is
:mod:`platterpus.read_offset_check`'s. **Tri-state throughout**: a report too old
to carry the field is *not determined* (a BLOCKED grade), never a pass.

Split from :mod:`platterpus.uiscript.artifact_grading` (whose ``grade_ctdb`` moved
here) by what each grader is asked: these three read a VERDICT the report already
holds; that module re-runs the audit and compares the report with the log. Pure,
Qt-free, never raises.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from platterpus.safe_int import int_or_none
from platterpus.uiscript.artifact_grading import Grade, derived_verification_refusal

# --- expect-ctdb (moved from artifact_grading, A3) ------------------------------

#: The CTDB verdicts in which the lookup happened and was compared (`ctdb.verify
#: .Verdict`). A disc CTDB does not hold is a determined answer about the disc.
_CTDB_DETERMINED: Final[frozenset[str]] = frozenset({"match", "no_match", "not_in_db"})


def _ctdb_outvoted(block: Mapping[str, Any]) -> bool | None:
    """Is this MATCH outvoted by a stronger entry? Tri-state, from the report.

    The report's own ``outvoted`` first (schema v38). Where a report predates it
    but still carries both confidences, the same comparison
    :attr:`~platterpus.ctdb.verify.CtdbVerifyResult.outvoted` makes. ``None``
    when neither is there: the match's weight is not determined.
    """
    outvoted = block.get("outvoted")
    if isinstance(outvoted, bool):
        return outvoted
    matched, best = block.get("confidence"), block.get("best_confidence")
    # `bool` is an `int` in Python; a True here is not a confidence of 1.
    if isinstance(matched, bool) or isinstance(best, bool):
        return None
    if isinstance(matched, int) and isinstance(best, int):
        return matched < best
    return None


def _ctdb_repair_note(block: Mapping[str, Any]) -> str:
    """The automatic CTDB repair, as INFORMATION beside the grade of the read.

    **The grade is of the READ, and never of the repair** (TASKS R133, 2026-11-05).
    ``ctdb.verdict``, ``outvoted`` and ``trustworthy`` stay what the rip's own
    audio measured; the repair and the verify after it sit beside them, in
    ``ctdb.repair`` and ``ctdb.after_repair``. A step whose severity is archival
    asks whether the drive read the disc right, and a repair that made the files
    right afterwards does not answer that: grading it would let a repair satisfy
    an archival grade the read failed. So it is named here, after the verdict,
    and changes nothing. "" when the report holds no repair. Never raises.
    """
    repair = block.get("repair")
    if not isinstance(repair, dict):
        return ""
    status = str(repair.get("status") or "unrecorded")
    reason = str(repair.get("reason") or "").strip()
    after = block.get("after_repair")
    after_verdict = after.get("verdict") if isinstance(after, dict) else None
    detail = f": {reason}" if reason else ""
    then = f"; CTDB after it: {after_verdict}" if after_verdict else ""
    what = {"repaired": "repaired the files"}.get(status, f"ended as {status}")
    return (
        f" ⓘ After the read, the app's CTDB repair {what}{detail}{then}. "
        "This step grades the read, not the repair."
    )


def grade_ctdb(report: Mapping[str, Any], scope: str) -> Grade:
    """The CTDB check reached the verdict this rip's SCOPE calls for (the READ's).

    Graded on ``ctdb``'s own fields, which are the read's verdict; an automatic
    repair after it is reported as information only (:func:`_ctdb_repair_note`).
    """
    graded = _grade_ctdb_read(report, scope)
    block = report.get("ctdb")
    note = _ctdb_repair_note(block) if isinstance(block, dict) else ""
    if not note:
        return graded
    return Grade(graded.passed, graded.detail + note, blocked=graded.blocked)


def _grade_ctdb_read(report: Mapping[str, Any], scope: str) -> Grade:
    """The CTDB check reached the verdict this rip's SCOPE calls for.

    ``scope`` is what the script knows about its own rip and the report is not
    trusted to say: ``whole`` (every track was ripped, so CTDB must have been
    looked up and compared) or ``partial`` (a subset, so the lookup must have
    been DECLINED — a 2-of-14 rip sends CTDB a two-track disc that does not
    exist, and the 2026-09-28 Full run's five partial rips reported "not in
    CTDB" about a disc it holds 102 entries for).

    **A match its own database outvotes is not a pass** (A3, 2026-11-03): a
    match at confidence 1 beside 1,524 disagreeing submissions is as consistent
    with a shared misread as with a correct read, and the report says so
    (``ctdb.outvoted``, ``ctdb.message``). Nor is a match the report marks
    untrustworthy (``ctdb.trustworthy`` false: the CRC algorithm unconfirmed),
    nor one whose weight the report does not carry (not determined).
    """
    from platterpus.ctdb.coverage import NOT_WHOLE_DISC_VERDICT

    if scope not in ("whole", "partial"):
        return Grade(False, f"{scope!r} is not a scope — say `whole` or `partial`")
    block = report.get("ctdb")
    if not isinstance(block, dict):
        return Grade(
            False,
            "the report holds no CTDB result — the check was off, or it did not run",
        )
    verdict = str(block.get("verdict") or "")
    message = str(block.get("message") or "").strip()
    if scope == "partial":
        if verdict == NOT_WHOLE_DISC_VERDICT:
            return Grade(True, "CTDB declined a partial rip, as it must")
        return Grade(
            False,
            f"CTDB answered {verdict!r} for a partial rip, which it cannot look up "
            f"honestly ({message})",
        )
    if verdict not in _CTDB_DETERMINED:
        return Grade(
            False,
            f"CTDB reached no verdict for the whole disc: {verdict!r} ({message})",
        )
    weight = (
        f"confidence {block.get('confidence')} of {block.get('total_confidence')} "
        f"submission(s), strongest entry {block.get('best_confidence')}, "
        f"{block.get('entry_count')} entr(ies)"
    )
    if verdict == "match":
        outvoted = _ctdb_outvoted(block)
        if outvoted:
            return Grade(
                False,
                f"CTDB matched an entry its own database outvotes ({weight}), so the "
                f"match does not corroborate the rip: {message}",
            )
        if block.get("trustworthy") is False:
            return Grade(
                False,
                f"the report marks this CTDB match untrustworthy ({weight}): {message}",
            )
        if outvoted is None:
            return Grade(
                False,
                f"not determined: CTDB matched ({weight}), but the report does not "
                "say whether a stronger entry disagrees, so the match's weight is "
                "unknown",
                blocked=True,
            )
    return Grade(True, f"CTDB was looked up and compared: {verdict}, {weight}")


# --- expect-verification: a gate that ran and FAILED (C1) ---------------------


def _failed_files(block: object) -> str:
    """The files a result block names as failed or mismatched, bounded."""
    if not isinstance(block, dict):
        return "its result block is missing"
    names: list[str] = []
    for key in ("failures", "mismatches"):
        values = block.get(key)
        if isinstance(values, list):
            names.extend(str(v).rsplit("/", 1)[-1] for v in values)
    if not names:
        return "its result block names no file"
    shown = ", ".join(names[:6])
    return shown + (f" (+{len(names) - 6} more)" if len(names) > 6 else "")


def verification_refusal(report: Mapping[str, Any] | None) -> str | None:
    """Why a settled report's post-rip verification is NOT a pass, or None.

    Two refusals, each the report's own words: **any gate reads** ``"ran —
    failed"``, naming the files its result block names, or the derived
    verification did not run
    (:func:`~platterpus.uiscript.artifact_grading.derived_verification_refusal`,
    run C of 2026-10-22). A failed gate reads
    :data:`~platterpus.verification_gates.GATE_RAN_FAILED`. Before C1 the
    floor only needed *some* gate to have run, and ``gate_claims_ran`` counts
    "ran — failed" as ran, so a check that ran and failed was a pass. Every gate
    is read, not a list of names, so a gate added later is held too. Never raises.
    """
    from platterpus.verification_gates import GATE_RAN_FAILED

    verification = report.get("verification") if report is not None else None
    block = verification if isinstance(verification, dict) else {}
    gates = block.get("gates")
    failed = [
        f"{key} ({_failed_files(block.get(key))})"
        for key, state in (gates.items() if isinstance(gates, dict) else ())
        if state == GATE_RAN_FAILED
    ]
    if not failed:
        return derived_verification_refusal(report)
    return (
        f"a post-rip check ran and FAILED: {'; '.join(failed)}. A check that ran "
        "and failed is a finding about the files, never a pass."
    )


# --- expect-read-offset (C3) -----------------------------------------------------


def sent_read_offset(argv: Sequence[object]) -> int | None:
    """The ``-s`` value in an argv as spawned, or None when it holds none."""
    parts = [str(part) for part in argv]
    for index, part in enumerate(parts[:-1]):
        if part == "-s":
            return int_or_none(parts[index + 1], field="ripper argv -s")
    return None


def grade_read_offset(report: Mapping[str, Any]) -> Grade:
    """The read offset this rip applied is the right one for this drive.

    Reads ``rip.read_offset_check`` (:mod:`platterpus.read_offset_check`), which
    compares the offset the ripper's LOG says it applied with the AccurateRip
    drive list, and records whether this rip's AccurateRip matches re-confirm it
    (KDD-31). And the offset we SENT must be the one the log says was applied,
    in EVERY pass the report records (the first pass's argv and the last's, which
    differ when the auto-fix re-ripped), so a changed ``-s`` cannot hide behind a
    log that reads back what it was given. Reading only the first pass let a
    changed ``-s`` in the re-rip through (found by the planted-fault test, E1).

    PASS when the list agrees (``matches``), or when the list cannot judge the
    drive but AccurateRip confirmed the offset on this disc (``confirmed``).
    FAIL on a contradiction: the list gives another offset (``differs``), or the
    argv and the log disagree. Anything else is *not determined* (BLOCKED),
    which is never a pass.
    """
    rip = report.get("rip")
    block = rip.get("read_offset_check") if isinstance(rip, dict) else None
    if not isinstance(block, dict):
        return Grade(
            False,
            "not determined: the report holds no rip.read_offset_check (written "
            "from schema v39), so the offset was never checked",
            blocked=True,
        )
    from platterpus.read_offset_check import (
        AR_CONFIRMED,
        OFFSET_DIFFERS,
        OFFSET_MATCHES,
    )

    state = str(block.get("state") or "")
    applied = block.get("applied")
    detail = str(block.get("detail") or "").strip()
    ar = str(block.get("accuraterip_detail") or "").strip()
    outcome = report.get("outcome")
    passes = (
        [outcome.get("ripper_argv_first_pass"), outcome.get("ripper_argv")]
        if isinstance(outcome, dict)
        else []
    )
    sent = [sent_read_offset(argv) for argv in passes if isinstance(argv, list)]
    said = f"read offset {detail}; {ar}" if ar else f"read offset {detail}"
    for value in sent:
        if value is not None and isinstance(applied, int) and value != applied:
            return Grade(
                False,
                f"we sent -s {value:+d} and the ripper's log says it applied "
                f"{applied:+d}; the two must be one number ({said})",
            )
    if state == OFFSET_DIFFERS:
        return Grade(False, f"{said}. A wrong read offset shifts every sample.")
    if state == OFFSET_MATCHES:
        return Grade(True, said)
    if block.get("accuraterip_reconfirms") == AR_CONFIRMED:
        return Grade(True, f"{said} (the drive list could not judge it: {state})")
    return Grade(
        False,
        f"not determined ({state or 'no state'}): {said}",
        blocked=True,
    )
