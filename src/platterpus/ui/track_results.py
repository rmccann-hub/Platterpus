"""What the track table shows about each track after a rip: one place decides it.

**Why this module exists** (UX review of 0.7.127, findings M2 and V3; TASKS R179
and R181). The window used to list a disc's tracks twice: the editable table
above (Rip?, #, Title, Artist, Length, Status) and a results table in the rip
pane's Tracks tab (#, Title, Status, AR v1, AR v2, EAC), with different status
words for the same track ("✓ Done" above, "ripped successfully" below) and the
databases' internals as column titles ("one frame only (200)", "B0D122E7 ~").
Now there is ONE track table, and after a rip it gains one **Verified** column
(``✓ 200 matching rips``, ``⚠ Mismatch``) and three detail columns hidden by
default (AccurateRip v1, AccurateRip v2 and the EAC CRC), whose words and
tooltips are the ones the results table had. This module renders every one of
those cells, so the track table only displays them.

**Where it came from.** The AccurateRip cell renderers (:func:`ar_cell`,
:func:`ar_tooltip`, :func:`eac_cell` and their tooltips) moved here unchanged
from ``ui/rip_progress.py``, whose table they rendered; rip_progress no longer
owns a table. The Status cell's rule (:func:`status_cell`) is the one the
results table had, with one change: a clean copy reads ``✓ Done``, the live
column's word, rather than the ripper's ``ripped successfully`` (which stays in
the tooltip), so a track has one status word before, during and after a rip.

**The honesty rules it keeps:**

* never a clean word over a track AccurateRip contradicts (the plan of record,
  2026-10-26, row 8; ``verdict.track_accuraterip_contradiction`` decides it);
* a CTDB-only disagreement is an ``ⓘ`` note, never WRONG (``ctdb_disagreement``);
* a CTDB repair is named, with whether a fresh CTDB check confirmed it
  (``reconciled_verdict.repaired_tracks``);
* status is never colour alone: every verdict cell carries ``✓``, ``⚠`` or ``ⓘ``.

Qt-free (the track table's model reads these cells as plain strings) and never
raises on a log, a CTDB result or a repair record of an unexpected shape.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from platterpus import one_frame_match
from platterpus.ctdb_disagreement import (
    CELL_NOTE,
    ctdb_disagreements,
    ctdb_note_sentence,
)
from platterpus.data_tracks import is_data_track
from platterpus.parsers.rip_log import accuraterip_is_match, track_accuraterip_verified
from platterpus.reconciled_verdict import repaired_tracks
from platterpus.track_proof import contradiction_sentence
from platterpus.verdict import (
    AR_CONTRADICTION_WRONG,
    AR_STATE_ABSENT,
    AR_STATE_NO_DATA,
    AR_STATE_NO_MATCH,
    AR_STATE_NOT_CHECKED,
    AR_STATE_OFFSET_VARIANT,
    AR_STATE_VERIFIED,
    accuraterip_compared,
    accuraterip_confidence_text,
    accuraterip_db_max_confidence,
    accuraterip_state,
    track_accuraterip_contradiction,
    track_accuraterip_state,
)

log = logging.getLogger(__name__)

#: The live Status column's word for a finished track (``track_table``'s
#: ``STATUS_DONE`` display). A clean copy reads the same after the rip.
DONE_TEXT: Final[str] = "✓ Done"

# Glyphs for the EAC column's at-a-glance archival mark (symbol + text, never
# colour alone — the trust-first UX rule).
_EAC_VERIFIED: Final[str] = "✓"
_EAC_PARTIAL: Final[str] = "~"

#: The Verified column's words. Short, because the column is narrow; the tooltip
#: carries the detail (the database, the checksums, what the numbers mean).
VERIFIED_MISMATCH: Final[str] = "⚠ Mismatch"
VERIFIED_NOT_IN_DATABASE: Final[str] = "ⓘ Not in database"
VERIFIED_NOT_CHECKED: Final[str] = "ⓘ Not checked"
#: The Status column's words for a track the automatic CTDB repair replaced:
#: confirmed by a fresh CTDB check of the repaired files, or not.
STATUS_REPAIRED: Final[str] = "✓ Repaired"
STATUS_REPAIR_UNCONFIRMED: Final[str] = "⚠ Repaired, unconfirmed"
VERIFIED_NONE: Final[str] = "—"


@dataclass(frozen=True)
class Cell:
    """One cell: the text it shows and its tooltip ("" for none)."""

    text: str
    tip: str = ""


@dataclass(frozen=True)
class TrackResultCells:
    """Everything the track table shows about one ripped track."""

    status: Cell
    verified: Cell
    ar_v1: Cell
    ar_v2: Cell
    crc: Cell


# Shared explanation of the "only one frame matched" state (cyanrip's `Accurip
# 450` line, "partially accurately ripped" up to +platterpus.16), used as the AR-cell tooltip and echoed in the
# User Guide glossary. It lives in `one_frame_match` so the table, the help and
# the banner read one wording. Until 2026-09-24 it said the audio "matches a
# known pressing … shifted by a fixed offset" and was "usually perfectly fine",
# which was wrong on the mechanism: see that module.
ONE_FRAME_TOOLTIP: str = one_frame_match.TOOLTIP

# The "we compared it and nothing matched" state. This is NOT "not in the
# database" — the disc IS there, our read just doesn't match any stored copy of
# it — and saying "not in DB" about such a track is a factually false claim. The
# durable EAC-compatible log already learned this (it writes "Cannot be verified
# as accurate", review finding 2026-07-28); the on-screen table did not, and
# collapsed the case into "not in DB" until 2026-07-31. The narrow column can
# only carry "in DB, no match", so the nuance lives here in the tooltip.
NO_MATCH_TOOLTIP: str = (
    "In the database, but no match: AccurateRip has this disc, and this track's "
    "checksum was compared against the copies other people submitted — none of "
    'them matched. That is NOT the same as "not in the database": the track '
    "simply cannot be verified as accurate. Innocent causes are common (an "
    "unlisted pressing, or a drive read offset that differs from ours), but a "
    "genuine read error looks exactly the same from here — re-rip the disc to "
    "tell them apart, and compare the two rips."
)

# The lookup never ran, so the database has said nothing either way. Kept
# separate from NO_MATCH_TOOLTIP because collapsing them is the exact conflation
# that made a never-queried disc read as a failed comparison (audit, 2026-07-31).
NOT_CHECKED_TOOLTIP: str = (
    "Not checked: no AccurateRip lookup was made for this rip, so the database "
    "has said nothing about this track either way. This is not a result — it is "
    "the absence of one. Re-rip with AccurateRip enabled (and a working network "
    "connection from the ripping container) to get a verdict."
)


def eac_cell(track: object) -> tuple[str, str]:
    """Render the EAC column for a track: the EAC CRC32 value + an archival mark.

    Returns ``(text, tooltip)``. The value is cyanrip's per-track EAC CRC32 (the
    same "Copy CRC" the companion log carries), so it can be diffed against a
    real EAC rip. The trailing glyph is an at-a-glance, HONEST archival mark —
    never a claim that our log equals an EAC-signed one (Platterpus never signs
    an EAC log):

    * ``✓`` — the track is AccurateRip-verified *and* its copy is OK. The rip as
      a whole is read-offset-corrected with no read errors, so a verified track
      meets the archival bar we can actually check.
    * ``~`` — only one frame (frame 450) matched AccurateRip; the rest of the
      track is unverified (never a false ✓).
    * (no glyph) — a real CRC we recorded but can't externally verify (not in
      the AccurateRip database).

    Never raises (duck-typed via ``getattr`` / the shared match helpers).
    """
    crc = (getattr(track, "copy_crc", "") or "").upper()
    if not crc:
        return "—", "No per-track EAC CRC32 was recorded for this track."
    status = getattr(track, "status", "") or ""
    if track_accuraterip_verified(track) and copy_is_ok(status):
        return (
            f"{crc}  {_EAC_VERIFIED}",
            "EAC-format CRC32. ✓ = AccurateRip-verified and copy OK; the rip is "
            "read-offset-corrected with no read errors, so this track meets the "
            "archival bar we can verify. NOT a claim of EAC-checksum equivalence "
            "— Platterpus never signs an EAC log.",
        )
    if accuraterip_is_match(getattr(track, "accuraterip_offset", None)):
        return (
            f"{crc}  {_EAC_PARTIAL}",
            "EAC-format CRC32. ~ = only one frame (frame 450) of this track "
            "matched AccurateRip; the rest of the track is unverified.",
        )
    return (
        crc,
        "EAC-format CRC32 (compare against a real EAC log). No ✓: this track "
        "didn't match the AccurateRip database — either it isn't present, or the "
        "read didn't match a stored copy — so it can't be independently verified.",
    )


# --- The AccurateRip states, decided in ONE place ---------------------------
#
# AccurateRip can put a track in exactly four states, and the project's dominant
# bug shape is each render surface re-deriving them with its own if-chain (four
# such disagreements shipped in one week — see tests/test_surface_consistency.py).
# Naming the states, and deciding them once in `_ar_state`, means the cell text
# and the cell tooltip cannot drift apart *within* this module; the fitness test
# then guards the harder seam — that this module and the durable EAC-compatible
# log (`eac_log_export._accuraterip_line`) put the same track in the same state.
#
# Values are plain strings, not an Enum, because they are only ever compared
# against these constants and a string keeps the debugger/log output readable.
# The state names and the classifier now live in `platterpus.verdict`, the module
# whose whole purpose is "one definition of verified" — because the EAC log
# renderer needs the identical classification and two copies is how the two
# surfaces came to disagree. Aliased to the old private names so this file's
# rendering code reads unchanged.
_AR_STATE_VERIFIED = AR_STATE_VERIFIED
_AR_STATE_OFFSET_VARIANT = AR_STATE_OFFSET_VARIANT
_AR_STATE_NO_MATCH = AR_STATE_NO_MATCH
_AR_STATE_ABSENT = AR_STATE_ABSENT
_AR_STATE_NO_DATA = AR_STATE_NO_DATA
_AR_STATE_NOT_CHECKED = AR_STATE_NOT_CHECKED
_ar_compared = accuraterip_compared
_ar_state = accuraterip_state


def ar_cell(
    result: object, *, offset_result: object = None, lookup: str | None = None
) -> str:
    """Render one AccurateRip cell (v1 or v2) for a track.

    ``offset_result`` is the track's frame-450 result (cyanrip's "Accurip 450:").
    When the whole-track checksum (``result``) did NOT match but frame 450 DID,
    we say "one frame only (N)": what matched, and nothing about why. The cell
    used to say "offset-variant match" and call the track "actually fine", which
    was a cause nothing measured (see :mod:`platterpus.one_frame_match`); the
    tooltip carries the rest.

    The cell text is short because the column is narrow; where short text cannot
    carry the nuance (``in DB, no match``), :func:`ar_tooltip` supplies it.
    Never raises (duck-typed via ``accuraterip_is_match`` / ``getattr``).
    """
    state = _ar_state(result, offset_result, lookup)
    if state == _AR_STATE_VERIFIED:
        # A genuine database match, format-agnostic across the legacy log
        # format's "Found, exact match" and cyanrip's "accurately ripped,
        # confidence N".
        #
        # "N of M", where M is the database's best confidence for this track.
        # The bare N was close to meaningless on its own: confidence 3 is
        # excellent on an obscure disc and a warning on a famous one. The pair is
        # the DIFFERENT-PRESSING signal — a low own-confidence against a high
        # maximum means most people's discs disagree with yours, which is a
        # pressing difference rather than a bad rip. cyanrip has printed the
        # maximum on every per-track `Accurip:` row all along and we read the row
        # only to answer "did a lookup happen" (2026-08-24). Rendered through the
        # shared `verdict` helper so the table, the report and any later surface
        # cannot describe one track's standing three different ways.
        return f"OK ({accuraterip_confidence_text(result, lookup)})"
    if state == _AR_STATE_OFFSET_VARIANT:
        conf = getattr(offset_result, "confidence", None)
        return (
            f"{one_frame_match.CELL} ({conf})"
            if conf is not None
            else one_frame_match.CELL
        )
    if state == _AR_STATE_NOT_CHECKED:
        # NOT "not in DB" — nobody looked, so the database has no opinion. Saying
        # "no match" here asserted both that the disc is present and that our read
        # disagreed with it, neither of which was established.
        return "not checked"
    if state == _AR_STATE_NO_MATCH:
        # THE FIX (2026-07-31): this used to say "not in DB" — a false claim
        # about a disc the database demonstrably has. Keep it short enough for
        # the column; NO_MATCH_TOOLTIP carries the rest.
        return "in DB, no match"
    if state == _AR_STATE_NO_DATA:
        return "—"
    # Absent: nothing was submitted for this disc, so there was nothing to
    # compare against. Say that plainly instead of cyanrip's alarmist "either a
    # new pressing, or bad rip" (a not-in-DB track is not necessarily a bad rip).
    result_text = getattr(result, "result", "") or ""
    lowered = result_text.lower()
    if not result_text or "not present" in lowered or "not found" in lowered:
        return "not in DB"
    # Unrecognized wording from a future backend: show it verbatim rather than
    # guessing, so an unexpected state is diagnosable instead of mislabelled.
    confidence = getattr(result, "confidence", None)
    return f"{result_text} ({confidence})" if confidence is not None else result_text


def ar_tooltip(
    result: object, *, offset_result: object = None, lookup: str | None = None
) -> str:
    """The tooltip for one AR cell — empty when the cell text needs no footnote.

    Derived from the same :func:`_ar_state` as the cell text, so a cell can never
    show one state's words with another state's explanation. (It previously was
    re-derived at the call site, which is the same one-fact-many-derivations
    shape this whole module keeps getting bitten by.) Never raises.
    """
    state = _ar_state(result, offset_result, lookup)
    if state == _AR_STATE_OFFSET_VARIANT:
        return ONE_FRAME_TOOLTIP
    if state == _AR_STATE_NOT_CHECKED:
        return NOT_CHECKED_TOOLTIP
    if state == _AR_STATE_NO_MATCH:
        return NO_MATCH_TOOLTIP
    if state == _AR_STATE_VERIFIED:
        # A verified track needs no footnote UNLESS its own confidence is far
        # below the database's best for the same track — which the cell now shows
        # as "N of M" but has no room to explain. The column is narrow; this is
        # where the nuance goes, exactly as it does for `in DB, no match`.
        return confidence_standing_tooltip(result, lookup)
    return ""


#: A verified track whose own confidence is at or below this FRACTION of the
#: database's best gets the different-pressing footnote. A ratio, not a fixed
#: number, because the meaning is relative: confidence 3 against a maximum of 3 is
#: an obscure disc everyone rips identically, and confidence 3 against 200 is a
#: pressing almost nobody else has. One quarter is a deliberately loose bar — the
#: footnote is an explanation, not a warning, and it says what the numbers mean
#: rather than passing judgement on the rip.
_DIFFERENT_PRESSING_RATIO: float = 0.25

#: The floor below which the ratio says nothing. With a database maximum in single
#: figures every rip is "far below" something, and a footnote on every track is a
#: footnote nobody reads.
_DIFFERENT_PRESSING_MIN_MAX: int = 10


def confidence_standing_tooltip(result: object, lookup: str | None) -> str:
    """Explain an "N of M" confidence pair when the gap is worth explaining.

    Empty for the ordinary case — a track that matched what most people have, or
    a disc whose database entry is too thin for the comparison to mean anything.
    Never raises.
    """
    own = getattr(result, "confidence", None)
    db_max = accuraterip_db_max_confidence(lookup)
    if own is None or db_max is None:
        return ""
    if db_max < _DIFFERENT_PRESSING_MIN_MAX:
        return ""
    if own > db_max * _DIFFERENT_PRESSING_RATIO:
        return ""
    return (
        f"This rip is bit-perfect — it matched {own} other submission(s) exactly.\n\n"
        f"The number after 'of' is the most any single version of this track has "
        f"({db_max}). Yours matched a much less common one, which usually means "
        f"you have a different PRESSING of the disc — a different factory or "
        f"release with slightly different audio. That is normal and is not a "
        f"problem with your rip or your drive."
    )


# --- The Status and Verified cells, and the whole table's cells --------------


def copy_is_ok(status: str) -> bool:
    """True when a track's status is a clean copy (EAC's 'Copy OK')."""
    return status.strip().lower() in ("copy ok", "ripped successfully")


def status_cell(
    track: object, ctdb_kind: str | None = None, repaired: bool | None = None
) -> Cell:
    """The Status column for a ripped track.

    * AccurateRip contradicts the copy (``verdict.track_accuraterip_contradiction``,
      the one predicate the EAC-layout log and the report ask): a ``⚠`` and the
      finding replace the ripper's word, because the plan of record (2026-10-26,
      row 8) forbids clean wording over such a track. The tooltip is the
      EAC-layout log's ``Proof:`` row, plus the ripper's word, so nothing hides.
    * A CTDB repair replaced that track and a fresh CTDB check confirmed it
      (``repaired`` True): ``✓ Repaired (CTDB)``, because the file is no longer
      the read AccurateRip rejected; the tooltip keeps AccurateRip's finding
      about the read. Unconfirmed, the ``⚠`` stays.
    * Otherwise a clean copy reads ``✓ Done`` (the live column's word, so a track
      keeps one status word; the ripper's own "ripped successfully" is in the
      tooltip) and any other word of the ripper's is shown as it said it.
    * ``ctdb_kind`` (``ctdb_disagreement``: CTDB differs, or agrees only with a
      minority, on a track AccurateRip does not contradict) adds an ``ⓘ`` note
      after the word, with the note's sentence as the tooltip: information, and
      AccurateRip is the verdict.

    Never raises.
    """
    status = str(getattr(track, "status", "") or "")
    said = f" The ripper reported: “{status}”." if status else ""
    contradiction = track_accuraterip_contradiction(track)
    if contradiction is not None:
        proof = f"Proof: {contradiction_sentence(track, contradiction)}.{said}"
        if repaired is not None:
            return Cell(
                STATUS_REPAIRED if repaired else STATUS_REPAIR_UNCONFIRMED,
                (
                    "Repaired from CTDB, and a fresh CTDB check of the repaired "
                    "file agrees."
                    if repaired
                    else "Repaired from CTDB, but no fresh CTDB check confirms the "
                    "repaired file."
                )
                + " AccurateRip's answer describes the read the repair replaced. "
                + proof,
            )
        text = (
            "⚠ Wrong (AccurateRip)"
            if contradiction == AR_CONTRADICTION_WRONG
            else "⚠ Differs from AccurateRip"
        )
        return Cell(text, proof)
    word = DONE_TEXT if copy_is_ok(status) else status
    if ctdb_kind is None:
        return Cell(word, said.strip())
    number = getattr(track, "number", "?")
    note = ctdb_note_sentence([(number, ctdb_kind)])
    return Cell(f"{word} · {CELL_NOTE}" if word else CELL_NOTE, f"{note}.{said}")


def _best_confidence(track: object) -> int | None:
    """The higher confidence of the track's matching AccurateRip versions."""
    found = [
        conf
        for name in ("accuraterip_v1", "accuraterip_v2")
        if accuraterip_is_match(result := getattr(track, name, None))
        and isinstance(conf := getattr(result, "confidence", None), int)
    ]
    return max(found) if found else None


def _ctdb_row_sentence(row: object | None) -> str:
    """What CTDB's per-track answer said, for the Verified tooltip; "" for none."""
    if row is None:
        return ""
    verdict = getattr(getattr(row, "verdict", None), "value", None)
    confidence = int(getattr(row, "confidence", 0) or 0)
    if verdict == "match" and not bool(getattr(row, "outvoted", False)):
        return f"CTDB: this track matches ({confidence:,} submissions)."
    if verdict == "match":
        return (
            f"CTDB: this track matches only a minority ({confidence:,} "
            "submissions), so it corroborates nothing."
        )
    if verdict == "differs":
        return "CTDB: this track differs from every entry CTDB holds for it."
    return ""


def _ctdb_row_matches(row: object | None) -> bool:
    verdict = getattr(getattr(row, "verdict", None), "value", None)
    return verdict == "match" and not bool(getattr(row, "outvoted", False))


def verified_cell(
    track: object,
    ctdb_row: object | None = None,
    repaired: bool | None = None,
    repaired_confidence: int = 0,
) -> Cell:
    """The Verified column: one short answer, the detail in its tooltip.

    The answer is AccurateRip's for every track it has an answer for, because
    AccurateRip is the per-track verdict (``reconciled_verdict`` says why on the
    screen). CTDB answers for a track AccurateRip has nothing to say about (not
    in the database, or not checked) when its per-track answer is a match no
    stronger entry outvotes. A repaired track says so. The tooltip lists both
    AccurateRip versions and the EAC CRC (the detail columns' words), what the
    state means, and CTDB's per-track answer. Never raises.
    """
    if is_data_track(track):
        return Cell(VERIFIED_NONE, "A data track: neither database covers it.")
    offset = getattr(track, "accuraterip_offset", None)
    lookup = getattr(track, "accuraterip_lookup", None)
    v1 = getattr(track, "accuraterip_v1", None)
    v2 = getattr(track, "accuraterip_v2", None)
    crc_text, _crc_tip = eac_cell(track)
    detail = (
        f"AccurateRip v1: {ar_cell(v1, offset_result=offset, lookup=lookup)}\n"
        f"AccurateRip v2: {ar_cell(v2, offset_result=offset, lookup=lookup)}\n"
        f"EAC CRC32: {crc_text}"
    )
    ctdb_said = _ctdb_row_sentence(ctdb_row)
    state = track_accuraterip_state(track)

    def tip(*parts: str) -> str:
        return "\n\n".join(p for p in (detail, *parts, ctdb_said) if p)

    if repaired is not None:
        if repaired:
            return Cell(
                f"✓ CTDB ({repaired_confidence:,})",
                tip(
                    "Repaired from CTDB: the file now equals a CTDB entry, proved "
                    "before anything was replaced, and a fresh CTDB check of the "
                    "repaired file agrees. The AccurateRip answers above describe "
                    "the read the repair replaced."
                ),
            )
        return Cell(
            VERIFIED_MISMATCH,
            tip(
                "Repaired from CTDB, but no fresh CTDB check confirms the "
                "repaired file. Re-rip the track and compare."
            ),
        )
    if state == AR_STATE_VERIFIED:
        confidence = _best_confidence(track)
        text = (
            f"✓ {confidence:,} matching rip{'' if confidence == 1 else 's'}"
            if confidence is not None
            else "✓ AccurateRip"
        )
        standing = confidence_standing_tooltip(
            v1 if accuraterip_is_match(v1) else v2, lookup
        )
        return Cell(
            text,
            tip(
                "AccurateRip verified this track: its checksum equals the one "
                "other people's rips of this disc submitted, so the audio is "
                "bit-perfect.",
                standing,
            ),
        )
    if state in (AR_STATE_OFFSET_VARIANT, AR_STATE_NO_MATCH):
        why = (
            ONE_FRAME_TOOLTIP if state == AR_STATE_OFFSET_VARIANT else NO_MATCH_TOOLTIP
        )
        return Cell(VERIFIED_MISMATCH, tip(why))
    if _ctdb_row_matches(ctdb_row):
        confidence = int(getattr(ctdb_row, "confidence", 0) or 0)
        return Cell(
            f"✓ CTDB ({confidence:,})",
            tip(
                "AccurateRip has no answer for this track, and CTDB's does: it "
                "matches the entries CTDB holds for it."
            ),
        )
    if state == AR_STATE_NOT_CHECKED:
        return Cell(VERIFIED_NOT_CHECKED, tip(NOT_CHECKED_TOOLTIP))
    if state == AR_STATE_ABSENT:
        return Cell(
            VERIFIED_NOT_IN_DATABASE,
            tip(
                "AccurateRip has no entry for this track, so it cannot verify it "
                "either way. That says nothing against the rip."
            ),
        )
    return Cell(VERIFIED_NONE, tip())


def result_cells(
    rip_log: object,
    ctdb_tracks: Sequence[object] = (),
    repair_result: object = None,
) -> dict[int, TrackResultCells]:
    """Every ripped track's cells, keyed by track number.

    ``ctdb_tracks`` is the CTDB result's per-track rows (empty before CTDB
    answers); ``repair_result`` the automatic repair's result, or None. The
    CTDB note comes from the one predicate (``ctdb_disagreements``) and the
    repaired tracks from ``reconciled_verdict.repaired_tracks``, the ones the
    reconciled verdict line reads, so the table and the line name the same
    tracks. Never raises: an unreadable input gives fewer cells, not an error.
    """
    try:
        tracks = tuple(getattr(rip_log, "tracks", ()) or ())
        kinds = dict(ctdb_disagreements(list(ctdb_tracks), rip_log))
        rows: Mapping[object, object] = {
            getattr(row, "track", None): row for row in ctdb_tracks
        }
        repaired = repaired_tracks(repair_result)
        after = getattr(repair_result, "after_repair", None)
        repaired_confidence = int(getattr(after, "confidence", 0) or 0)
        cells: dict[int, TrackResultCells] = {}
        for track in tracks:
            number = getattr(track, "number", None)
            if not isinstance(number, int) or isinstance(number, bool):
                continue
            offset = getattr(track, "accuraterip_offset", None)
            lookup = getattr(track, "accuraterip_lookup", None)
            v1 = getattr(track, "accuraterip_v1", None)
            v2 = getattr(track, "accuraterip_v2", None)
            crc_text, crc_tip = eac_cell(track)
            cells[number] = TrackResultCells(
                status=status_cell(track, kinds.get(number), repaired.get(number)),
                verified=verified_cell(
                    track,
                    rows.get(number),
                    repaired.get(number),
                    repaired_confidence,
                ),
                ar_v1=Cell(
                    ar_cell(v1, offset_result=offset, lookup=lookup),
                    ar_tooltip(v1, offset_result=offset, lookup=lookup),
                ),
                ar_v2=Cell(
                    ar_cell(v2, offset_result=offset, lookup=lookup),
                    ar_tooltip(v2, offset_result=offset, lookup=lookup),
                ),
                crc=Cell(crc_text, crc_tip),
            )
        return cells
    except (AttributeError, TypeError, ValueError):
        log.warning("could not render the track results", exc_info=True)
        return {}
