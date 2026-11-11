# SPDX-License-Identifier: GPL-3.0-only
"""How each track's copy was verified, in the one wording every record prints.

**Why this module exists** (round 39's gate G3, "the record", the owner-approved
plan of 2026-11-11). :mod:`platterpus.track_proof` says *which proof* a copy has
(AccurateRip, CTDB, reads that agree, none). It does not say *how the copy came to
be the one kept*, and on the reference disc that is the question a reader has:
track 5 of the owner's 2026-11-10 Full run was read, not verified, and then
rewritten from CTDB entry 32115 (``E0036697`` to ``C96464AB``). Neither the
EAC-layout log nor the report's track row said so; the repair lived only in
``ctdb.repair``. So every track's record now names one of these, and only these:

* **first read** — the copy is the track's one read, and a database verifies it;
* **re-read, n agreeing of m** — a ``-Z`` secure re-read, ``n`` of its ``m`` reads
  agreeing (exactly, or as a bound the log proves);
* **kept at the -Z limit for AccurateRip's match** — the fork's
  ``--prefer-accuraterip-match`` kept a read AccurateRip matches at the limit;
* **the fork's ``.31`` -Z rule** — AccurateRip ended the reads after overruling
  an agreement it does not match (``--reread-until-accuraterip``), read from the
  log (:mod:`platterpus.reread_ar_overrule`) for the builds in
  :data:`platterpus.track_record_sources.AR_GUIDED_CONVERGENCE_BUILDS`; a later
  build we cannot read says *not determined*, never a guess;
* **chase attempt k** — our verified-read chase (TASKS R7) kept its ``k``-th read;
* **repaired from CTDB** — with the entry id, the Copy CRC before and after, a
  fresh CTDB check, and AccurateRip v1 and v2 each stated (not determined: see
  :func:`platterpus.ctdb.repair_wording.accuraterip_after_repair`), from
  :func:`platterpus.track_record_sources.repaired_tracks_by_number`;
* **not verified** — with the read path and the reason.

**And whether the reads disagreed**, tri-state (:func:`reads_disagree`), because
EAC prints ``Copy OK`` over reads that disagree (``docs/eac-parity.md`` Part F row
8) and our EAC-layout log must not: it decides the log's status line.

Reads the verdict's predicates through ``track_proof`` and computes nothing of its
own about AccurateRip. Pure; no Qt, no I/O; reads with ``getattr``; never raises.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from platterpus.ctdb.repair_wording import accuraterip_after_repair
from platterpus.data_tracks import is_data_track
from platterpus.report_types import TrackRecordBlock
from platterpus.track_proof import (
    PROOF_ACCURATERIP,
    PROOF_CTDB,
    PROOF_NONE,
    PROOF_READS_AGREE,
    PROOF_VERIFIED_REREAD,
    accuraterip_matches,
    track_proof,
)
from platterpus.track_record_reads import read_path, reads_disagree
from platterpus.track_record_sources import (
    RepairFacts,
    ar_guided_convergence,
    ar_overrule_words,
    int_or_none_strict,
    upper_hex,
)

#: The copy is the track's one read, and AccurateRip or CTDB verifies it.
RECORD_FIRST_READ: Final[str] = "first_read"
#: A ``-Z`` re-read, verified by AccurateRip, CTDB, or its reads agreeing.
RECORD_REREAD: Final[str] = "reread"
#: The fork's ``--prefer-accuraterip-match`` kept an AccurateRip-matched read.
RECORD_KEPT_AT_LIMIT: Final[str] = "kept_at_limit_for_accuraterip"
#: The fork's ``.31`` AccurateRip-guided ``-Z`` rule (a seam; see below).
RECORD_AR_GUIDED: Final[str] = "accuraterip_guided_convergence"
#: Our verified-read chase kept one of its single reads (TASKS R7).
RECORD_CHASE: Final[str] = "chase_attempt"
#: Rewritten from a CTDB entry after the read (TASKS R43, R133).
RECORD_REPAIRED: Final[str] = "repaired_from_ctdb"
#: Nothing verifies the copy.
RECORD_NOT_VERIFIED: Final[str] = "not_verified"

#: Every kind :func:`track_record` returns, for a sweep to enumerate.
RECORD_KINDS: Final[frozenset[str]] = frozenset(
    {
        RECORD_FIRST_READ,
        RECORD_REREAD,
        RECORD_KEPT_AT_LIMIT,
        RECORD_AR_GUIDED,
        RECORD_CHASE,
        RECORD_REPAIRED,
        RECORD_NOT_VERIFIED,
    }
)


@dataclass(frozen=True)
class TrackRecord:
    """One track's record: its kind (:data:`RECORD_KINDS`), its line, two flags.

    ``reads_disagree`` is :func:`reads_disagree` (tri-state); ``repaired`` is True
    when a CTDB repair rewrote the track's file after the read.
    """

    kind: str
    line: str
    reads_disagree: bool | None
    repaired: bool


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def _repaired_line(facts: RepairFacts, path: str) -> str:
    """``repaired from CTDB entry 32115 (…) after the read (…): Copy CRC …; …``."""
    samples = (
        f", {_plural(facts.samples_corrected, 'sample')} corrected"
        if facts.samples_corrected is not None
        else ""
    )
    crcs = (
        f"Copy CRC {facts.crc_before} before, {facts.crc_after} after"
        if facts.crc_before and facts.crc_after
        else "Copy CRC after the repair not recorded"
    )
    if facts.after_agrees is True:
        weight = (
            f" ({_plural(facts.after_confidence, 'submission')})"
            if facts.after_confidence
            else ""
        )
        fresh = f"a fresh CTDB check of the repaired files agrees{weight}"
    elif facts.after_agrees is False:
        fresh = "a fresh CTDB check of the repaired files does not agree"
    else:
        fresh = "a fresh CTDB check of the repaired files did not run"
    ar = accuraterip_after_repair(
        facts.accuraterip_v1_after, facts.accuraterip_v2_after
    )
    return (
        f"repaired from CTDB entry {facts.entry_id} "
        f"(confidence {facts.confidence:,}) after the read ({path}): "
        f"{crcs}{samples}; {fresh}; {ar}"
    )


def _verification(kind: str, proof_line: str, track: object) -> str:
    """The database's part of the line, from the proof ``track_proof`` found."""
    if kind in (PROOF_ACCURATERIP, PROOF_VERIFIED_REREAD):
        return f"verified by AccurateRip {accuraterip_matches(track)}"
    if kind == PROOF_CTDB:
        return f"verified by {proof_line}"
    if kind == PROOF_READS_AGREE:
        return f"verified only by the reads agreeing: {proof_line}"
    return proof_line.removeprefix("none — ")


def track_record(
    track: object,
    *,
    chased: bool = False,
    chase_attempt: int | None = None,
    repair: RepairFacts | None = None,
    ctdb_track: object | None = None,
    ripper_version: str = "",
) -> TrackRecord:
    """The record of how ``track``'s copy was verified. Never raises.

    ``chased`` is True when the file is a verified-read chase read
    (``secure_rerip.verified_rereads``), ``chase_attempt`` which attempt it was
    when the report says; ``repair`` is :func:`repaired_tracks_by_number`'s entry;
    ``ctdb_track`` this track's CTDB row (the read's), as ``track_proof`` takes it;
    ``ripper_version`` the log's ``log_creator``, for the ``.31`` seam.
    """
    try:
        disagree = reads_disagree(track, chased=chased)
        if is_data_track(track):
            return TrackRecord(
                RECORD_NOT_VERIFIED,
                "not verified — a data track, which AccurateRip and CTDB do not cover",
                disagree,
                False,
            )
        path = read_path(track)
        if repair is not None:
            return TrackRecord(
                RECORD_REPAIRED, _repaired_line(repair, path), disagree, True
            )
        proof = track_proof(track, verified_reread=chased, ctdb_track=ctdb_track)
        verified = _verification(proof.kind, proof.line, track)
        if chased:
            which = (
                f"chase attempt {chase_attempt}" if chase_attempt else "a chase attempt"
            )
            return TrackRecord(
                RECORD_CHASE,
                f"{which} (TASKS R7), a single read kept in place of a read AccurateRip "
                f"did not verify; {verified}",
                disagree,
                False,
            )
        kept = getattr(track, "secure_rerip_kept_read", None)
        if kept is not None:
            crc = upper_hex(getattr(kept, "crc", None)) or "?"
            reads = int_or_none_strict(getattr(kept, "reads", None))
            times = f", read {_plural(reads, 'time')}" if reads else ""
            confidence = getattr(kept, "accuraterip_confidence", None)
            return TrackRecord(
                RECORD_KEPT_AT_LIMIT,
                f"kept at the -Z limit for AccurateRip's match (the ripper's "
                f"--prefer-accuraterip-match): {crc}{times}, AccurateRip confidence "
                f"{confidence} ({path})"
                + (f"; {words}" if (words := ar_overrule_words(track)) else ""),
                disagree,
                False,
            )
        guided = ar_guided_convergence(track, ripper_version)
        if guided is True:  # `.31` and later: AccurateRip ended the reads
            return TrackRecord(
                RECORD_AR_GUIDED,
                f"{ar_overrule_words(track)}; {verified}",
                disagree,
                False,
            )
        caveat = ""
        if guided is None and path != "first read":
            caveat = (
                "; whether the fork's .31 AccurateRip-guided -Z rule chose this read "
                "is not determined (this release does not read that build's log)"
            )
        if (words := ar_overrule_words(track)) is not None:  # `.31`: a limit after
            caveat += f"; {words}"  # an overrule, which the limit line names
        if proof.kind == PROOF_NONE:
            return TrackRecord(
                RECORD_NOT_VERIFIED,
                f"not verified — {path}; {verified}{caveat}",
                disagree,
                False,
            )
        kind = RECORD_FIRST_READ if path == "first read" else RECORD_REREAD
        return TrackRecord(kind, f"{path}; {verified}{caveat}", disagree, False)
    except (AttributeError, TypeError, ValueError):
        return TrackRecord(
            RECORD_NOT_VERIFIED,
            "not verified — the record could not be determined",
            None,
            False,
        )


def track_record_among(
    track: object,
    *,
    chased: frozenset[int],
    chase_attempts: Mapping[int, int],
    repairs: Mapping[int, RepairFacts],
    ctdb_rows: Mapping[int, object],
    ripper_version: str,
) -> TrackRecord:
    """:func:`track_record` for one track of a rip, given the rip-wide facts.

    Each mapping is keyed by track number, which a malformed track may not have,
    in which case none applies.
    """
    number = int_or_none_strict(getattr(track, "number", None))
    if number is None:
        return track_record(track, ripper_version=ripper_version)
    return track_record(
        track,
        chased=number in chased,
        chase_attempt=chase_attempts.get(number),
        repair=repairs.get(number),
        ctdb_track=ctdb_rows.get(number),
        ripper_version=ripper_version,
    )


def record_block(record: TrackRecord) -> TrackRecordBlock:
    """The report's per-track ``record`` (schema 45): the four fields, as JSON."""
    return {
        "kind": record.kind,
        "line": record.line,
        "reads_disagree": record.reads_disagree,
        "repaired": record.repaired,
    }
