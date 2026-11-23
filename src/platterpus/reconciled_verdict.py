"""One line that reconciles AccurateRip and CTDB: which source decides, and why.

**Why this module exists** (UX review of 0.7.127, findings V2 and A3; TASKS
R181). After a rip the window showed AccurateRip's verdict ("⚠ … AccurateRip
says track 5 is WRONG") in the banner and CTDB's ("CTDB: verified ✓") one tab
away, both in amber, and nothing on screen said which of them to believe. A
non-expert saw "verified" and "WRONG" for the same rip. The pieces of a
reconciliation already existed, each on its own surface: the CTDB per-track note
(``ctdb_disagreement``, "AccurateRip is the verdict"), the whole-disc
reconciliation (``verdict.reconcile_ar_ctdb``), and the repair's sentence
(``ctdb/repair_wording``). This module puts them in ONE sentence under the
banner, and that sentence always names the source that decides.

**The rules it applies are the project's, not new ones:**

* **AccurateRip is the one source of WRONG** (the owner's word for 0.7.119;
  ``verdict.track_accuraterip_contradiction``). A CTDB match, per track or for
  the whole disc, does not clear a track AccurateRip compared and rejected: the
  line says the two disagree, that AccurateRip decides, and what settles it.
  ``ui/rip_progress.ctdb_verdict_level`` already refuses green to such a match.
* **A proven CTDB repair changes the file, so it changes who decides.**
  AccurateRip's answer describes the READ; the repair replaced it with audio
  proved to equal a CTDB entry (``ctdb/repair_wording``). When a fresh CTDB
  check of the repaired files agrees, CTDB decides for those tracks. When it does
  not, nothing settles them yet, and the line says so.
* **CTDB decides where AccurateRip has nothing to say**: a disc AccurateRip has
  no entry for, or did not check, and that CTDB matches as a whole.
* **Neither source is promoted by absence.** No CTDB answer means no line at all
  (the banner is then the whole verdict), not "CTDB agrees".

Status is never colour alone: the line leads with ``✓``, ``⚠`` or ``ⓘ`` for its
level. Pure: no Qt, no I/O; reads results with ``getattr`` and never raises.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from platterpus.ctdb.repair_wording import after_repair_agrees
from platterpus.ctdb_disagreement import ctdb_disagreements, ctdb_note_sentence
from platterpus.finish_wording import tracks_phrase
from platterpus.verdict import (
    AR_CONTRADICTION_WRONG,
    accuraterip_contradictions,
    accuraterip_counts,
    reconcile_ar_ctdb,
)

log = logging.getLogger(__name__)

#: Which source the line says decides. Strings, like the verdict levels, so a
#: report or a log line can carry them as they are.
DECIDES_ACCURATERIP: Final[str] = "accuraterip"
DECIDES_CTDB: Final[str] = "ctdb"
DECIDES_BOTH: Final[str] = "both"
#: More than one source decides, each for different tracks (a repaired track is
#: CTDB's, a rejected one AccurateRip's).
DECIDES_SPLIT: Final[str] = "split"

#: The line's levels, the ones ``ui/status_colours`` colours.
LEVEL_OK: Final[str] = "ok"
LEVEL_NEUTRAL: Final[str] = "neutral"
LEVEL_WARN: Final[str] = "warn"

#: The marker each level leads with (WCAG: never colour alone).
_MARKER: Final[dict[str, str]] = {LEVEL_OK: "✓", LEVEL_NEUTRAL: "ⓘ", LEVEL_WARN: "⚠"}
#: Worst first, so the line takes the level of its most serious clause.
_SEVERITY: Final[tuple[str, ...]] = (LEVEL_WARN, LEVEL_NEUTRAL, LEVEL_OK)

#: The CTDB verdict values this module reads (``ctdb.verify.Verdict``'s values,
#: compared as strings so this module needs no enum import to stay duck-typed).
_MATCH: Final[str] = "match"
_NO_MATCH: Final[str] = "no_match"

#: Why AccurateRip decides when CTDB matches a track it rejects. Said in the
#: user's terms: the two checks disagree, AccurateRip's per-track answer is the
#: one this app treats as the verdict, and only a new read can settle it.
_WHY_AR_OVER_CTDB: Final[str] = (
    "AccurateRip is the per-track verdict, and a CTDB match does not clear a "
    "track AccurateRip compared and rejected"
)


@dataclass(frozen=True)
class ReconciledVerdict:
    """The line, its level (``ok`` / ``neutral`` / ``warn``) and who decides."""

    text: str
    level: str
    decides: str


def _verdict_value(result: object) -> str | None:
    """``"match"``, ``"no_match"`` … for a CTDB result, or None without one."""
    verdict = getattr(result, "verdict", None)
    value = getattr(verdict, "value", verdict)
    return value if isinstance(value, str) else None


def _ctdb_track_matches(ctdb_tracks: Sequence[object]) -> set[int]:
    """Tracks CTDB's per-track answer matches, and not only with a minority."""
    found: set[int] = set()
    for row in ctdb_tracks:
        number = getattr(row, "track", None)
        value = _verdict_value(row)
        outvoted = bool(getattr(row, "outvoted", False))
        if isinstance(number, int) and value == _MATCH and not outvoted:
            found.add(number)
    return found


def repaired_tracks(repair_result: object) -> dict[int, bool | None]:
    """``{track: does a fresh CTDB check agree?}`` for a REPAIRED record, else {}.

    The agreement is :func:`ctdb.repair_wording.after_repair_agrees`, tri-state
    (None when no fresh check ran), the predicate the repair's own sentence and
    each repaired track's record read. One whole-disc check, so every repaired
    track carries the same answer. Never raises.
    """
    try:
        record = getattr(repair_result, "repair", None)
        status = getattr(getattr(record, "status", None), "value", None)
        if status != "repaired":
            return {}
        agrees = after_repair_agrees(getattr(repair_result, "after_repair", None))
        return {
            number: agrees
            for row in tuple(getattr(record, "tracks", ()) or ())
            if isinstance(number := getattr(row, "track", None), int)
        }
    except (AttributeError, TypeError, ValueError):
        return {}


def _repair_failed(repair_result: object) -> bool:
    """True when a repair was attempted and refused or failed."""
    record = getattr(repair_result, "repair", None)
    status = getattr(getattr(record, "status", None), "value", None)
    return status in ("refused", "failed")


def _numbers(found: Sequence[tuple[object, str]]) -> list[object]:
    return [number for number, _kind in found]


def _ar_said(found: Sequence[tuple[object, str]]) -> str:
    """What AccurateRip said of ``found``, after "AccurateRip decides <tracks>: ".

    ``it says it is wrong`` / ``it says they are wrong`` /
    ``it says it differs from every copy it holds``, naming the tracks only when
    the two kinds are mixed (the clause's lead already names them otherwise).
    The banner and the table carry the detail ("only frame 450 matched"); this
    line only has to name the finding it reconciles.
    """
    wrong = [n for n, kind in found if kind == AR_CONTRADICTION_WRONG]
    differs = [n for n, kind in found if kind != AR_CONTRADICTION_WRONG]
    if wrong and differs:
        are = "are" if len(wrong) > 1 else "is"
        differ = "differ" if len(differs) > 1 else "differs"
        return (
            f"it says {tracks_phrase(wrong)} {are} wrong and "
            f"{tracks_phrase(differs)} {differ} from every copy it holds"
        )
    many = len(found) > 1
    if wrong:
        return f"it says {'they are' if many else 'it is'} wrong"
    return f"it says {'they differ' if many else 'it differs'} from every copy it holds"


def reconcile_verdict(
    rip_log: object, ctdb_result: object, repair_result: object = None
) -> ReconciledVerdict | None:
    """The one reconciled line for a finished rip, or None when there is none.

    ``rip_log`` is the parsed log (AccurateRip's per-track answers);
    ``ctdb_result`` the CTDB verify result (None before CTDB answers, or when
    the check did not run, which hides the line); ``repair_result`` the result
    the automatic repair returned (its ``repair`` record and ``after_repair``
    check), or None when no repair ran. Never raises: a results-pane line must
    never take the pane down, so an unexpected shape logs and returns None.
    """
    if ctdb_result is None or rip_log is None:
        return None
    try:
        return _reconcile(rip_log, ctdb_result, repair_result)
    except Exception:  # noqa: BLE001 — a results-pane line must never crash the pane
        log.exception("could not reconcile AccurateRip and CTDB; hiding the line")
        return None


def _reconcile(
    rip_log: object, ctdb_result: object, repair_result: object
) -> ReconciledVerdict | None:
    clauses: list[tuple[str, str, str]] = []  # (level, decides, sentence)
    # Audio tracks only: the predicate never contradicts a data track.
    contradicted = accuraterip_contradictions(rip_log)
    repaired = repaired_tracks(repair_result)
    verdict = _verdict_value(ctdb_result)
    trustworthy = getattr(ctdb_result, "trustworthy", None) is True
    whole_disc_match = verdict == _MATCH and trustworthy
    confidence = int(getattr(ctdb_result, "confidence", 0) or 0)
    ctdb_tracks = tuple(getattr(ctdb_result, "tracks", ()) or ())
    ctdb_matches = _ctdb_track_matches(ctdb_tracks)

    # --- Tracks the repair replaced: the file is no longer the read ----------
    proved = [n for n, agrees in sorted(repaired.items()) if agrees is True]
    unproved = [n for n, agrees in sorted(repaired.items()) if agrees is not True]
    if proved:
        many = len(proved) > 1
        clauses.append(
            (
                LEVEL_OK,
                DECIDES_CTDB,
                f"CTDB decides {tracks_phrase(proved)}: "
                f"{'they were' if many else 'it was'} repaired from CTDB and a "
                f"fresh CTDB check verifies the repaired file{'s' if many else ''}, "
                "while AccurateRip's answer describes the read the repair replaced.",
            )
        )
    if unproved:
        clauses.append(
            (
                LEVEL_WARN,
                DECIDES_ACCURATERIP,
                f"{tracks_phrase(unproved).capitalize()} "
                f"{'were' if len(unproved) > 1 else 'was'} repaired from CTDB, but "
                "no fresh CTDB check confirms the repaired audio, so nothing "
                "settles it yet: re-rip and compare.",
            )
        )

    # --- Tracks AccurateRip rejects and no repair replaced -------------------
    open_tracks = [(n, k) for n, k in contradicted if n not in repaired]
    if open_tracks:
        ctdb_agrees = [
            (n, k) for n, k in open_tracks if n in ctdb_matches or whole_disc_match
        ]
        rest = [(n, k) for n, k in open_tracks if (n, k) not in ctdb_agrees]
        if ctdb_agrees:
            numbers = _numbers(ctdb_agrees)
            them = "it" if len(numbers) == 1 else "them"
            how = (
                "CTDB matches the whole disc"
                if whole_disc_match
                else f"CTDB matches {them}"
            )
            clauses.append(
                (
                    LEVEL_WARN,
                    DECIDES_ACCURATERIP,
                    f"AccurateRip decides {tracks_phrase(numbers)}: "
                    f"{_ar_said(ctdb_agrees)}, while {how}. {_WHY_AR_OVER_CTDB}; "
                    f"re-rip {them} to settle the disagreement.",
                )
            )
        if rest:
            numbers = _numbers(rest)
            extra = ""
            if _repair_failed(repair_result):
                extra = " CTDB could not repair it (see the Details tab)."
            elif verdict == _NO_MATCH and (
                why := reconcile_ar_ctdb(rip_log, ctdb_result)
            ):
                # The reconciliation the Details tab used to carry, verbatim:
                # CTDB's whole-disc no-match is the same finding.
                extra = f" {why}"
            clauses.append(
                (
                    LEVEL_WARN,
                    DECIDES_ACCURATERIP,
                    f"AccurateRip decides {tracks_phrase(numbers)}: "
                    f"{_ar_said(rest)}.{extra}",
                )
            )

    # --- CTDB questions a track AccurateRip does not contradict --------------
    # The 0.7.119 note, word for word, with its reason; beside a rejected track
    # too, since the note's predicate already leaves a rejected track out.
    noted = ctdb_note_sentence(ctdb_disagreements(ctdb_tracks, rip_log))
    if noted:
        clauses.append(
            (
                LEVEL_NEUTRAL,
                DECIDES_ACCURATERIP,
                noted.removeprefix("ⓘ ").strip()
                + ", because AccurateRip, the per-track check, found nothing "
                "wrong with "
                + ("these tracks." if "tracks " in noted else "this track."),
            )
        )

    # --- Where AccurateRip rejects nothing ------------------------------------
    if not contradicted and not noted:
        clauses.extend(_agreeing_clauses(rip_log, ctdb_result, verdict, confidence))

    if not clauses:
        return None
    level = next(lv for lv in _SEVERITY if any(c[0] == lv for c in clauses))
    sources = {c[1] for c in clauses}
    decides = sources.pop() if len(sources) == 1 else DECIDES_SPLIT
    # The line leads with its level's marker. A later clause at another level
    # keeps its own (a CTDB note beside a rejected track reads "… ⓘ CTDB
    # disagrees on track 2 …"), so no clause's status is said by colour alone.
    body = " ".join(
        c[2] if i == 0 or c[0] == level else f"{_MARKER[c[0]]} {c[2]}"
        for i, c in enumerate(clauses)
    )
    return ReconciledVerdict(f"{_MARKER[level]} {body}", level, decides)


def _agreeing_clauses(
    rip_log: object, ctdb_result: object, verdict: str | None, confidence: int
) -> list[tuple[str, str, str]]:
    """The clauses for a rip AccurateRip contradicts on no track, and CTDB
    questions on none."""
    total, verified, _partial = accuraterip_counts(rip_log)
    trustworthy = getattr(ctdb_result, "trustworthy", None) is True
    rips = f"{confidence:,} submission{'' if confidence == 1 else 's'}"
    if verdict == _MATCH and trustworthy:
        if total and verified == total:
            return [
                (
                    LEVEL_OK,
                    DECIDES_BOTH,
                    "AccurateRip and CTDB agree: AccurateRip verified every track, "
                    f"and the whole disc matches CTDB ({rips}).",
                )
            ]
        if verified == 0:
            return [
                (
                    LEVEL_OK,
                    DECIDES_CTDB,
                    "CTDB decides: AccurateRip has no answer for these tracks, and "
                    f"the whole disc matches CTDB ({rips}).",
                )
            ]
        return [
            (
                LEVEL_OK,
                DECIDES_BOTH,
                f"AccurateRip verified {verified} of {total} tracks and has no "
                "answer for the rest; CTDB covers them, because the whole disc "
                f"matches CTDB ({rips}).",
            )
        ]
    if verdict == _MATCH:
        return [
            (
                LEVEL_NEUTRAL,
                DECIDES_ACCURATERIP,
                "AccurateRip decides: CTDB's match is with a minority of its "
                "submissions (or is not yet a confirmed check), so it corroborates "
                "nothing.",
            )
        ]
    if verdict == _NO_MATCH:
        why = reconcile_ar_ctdb(rip_log, ctdb_result)
        return [
            (
                LEVEL_NEUTRAL,
                DECIDES_ACCURATERIP,
                f"AccurateRip decides: CTDB has no matching entry for the whole "
                f"disc. {why}"
                if why
                else "AccurateRip decides: CTDB has no matching entry for the whole "
                "disc.",
            )
        ]
    return [
        (
            LEVEL_NEUTRAL,
            DECIDES_ACCURATERIP,
            "AccurateRip decides alone: CTDB gave no answer about this rip "
            "(see the Details tab).",
        )
    ]
