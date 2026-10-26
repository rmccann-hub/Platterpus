"""Which proof each track's copy has, in the one wording every surface prints.

**Why this module exists** (the owner's EAC-parity plan of record, 2026-10-26,
rows 8 and 9). The worst outcome the owner names is *a wrong track reported as
fine*. On the Police disc's secure re-read of 2026-10-21, track 3 read
``3D8FCF0C``, matched AccurateRip on frame 450 only, and the EAC-layout log said
"confirmed across 4 secure re-reads … Copy OK" over it. The facts were all in the
parsed log; no surface turned them into a sentence about the track.

Row 9 asks for the other half: one line per track naming the proof it has. EAC's
log has one kind, Test and Copy CRCs that agree. Ours has several, and the
strongest differs from track to track, so the log has to say which:

* **AccurateRip**, v1 and/or v2, at a confidence;
* **a verified re-read**: a single re-read AccurateRip verifies, kept by the
  verified-read chase in place of a read it did not verify (TASKS R7);
* **CTDB per track**, where AccurateRip has no entry and CTDB's per-track entry
  agrees and is not outvoted (TASKS R34, R43);
* **reads agreed**, with no database behind them: the drive read the track the
  same way each time, which cannot show that the audio is right;
* **none**, with the reason, including a track AccurateRip contradicts.

This module reads the verdict's predicates (:mod:`platterpus.verdict` is the
single source) and words what they found. It computes nothing of its own about
AccurateRip. The EAC-layout log's ``Proof:`` row and the report's per-track
``proof`` both come from :func:`track_proof`, so the two cannot describe one
track two ways.

Pure; no Qt, no I/O; reads with ``getattr`` and never raises.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from platterpus.data_tracks import is_data_track
from platterpus.parsers.rip_log import accuraterip_is_match
from platterpus.verdict import (
    AR_CONTRADICTION_WRONG,
    accuraterip_db_max_confidence,
    accuraterip_lookup_happened,
    track_accuraterip_contradiction,
)

#: An exact AccurateRip match, v1 and/or v2.
PROOF_ACCURATERIP: Final[str] = "accuraterip"
#: A single re-read AccurateRip verifies, kept by the verified-read chase.
PROOF_VERIFIED_REREAD: Final[str] = "verified_reread"
#: CTDB's per-track entry agrees and is not outvoted; AccurateRip has none.
PROOF_CTDB: Final[str] = "ctdb"
#: Repeated reads agreed, and no database confirms them.
PROOF_READS_AGREE: Final[str] = "reads_agree"
#: Nothing proves this copy; the line says why.
PROOF_NONE: Final[str] = "none"

#: Every kind :func:`track_proof` returns, for a sweep to enumerate.
PROOF_KINDS: Final[frozenset[str]] = frozenset(
    {
        PROOF_ACCURATERIP,
        PROOF_VERIFIED_REREAD,
        PROOF_CTDB,
        PROOF_READS_AGREE,
        PROOF_NONE,
    }
)


@dataclass(frozen=True)
class TrackProof:
    """One track's proof: its kind (one of :data:`PROOF_KINDS`) and its line."""

    kind: str
    line: str


def contradiction_sentence(track: object, contradiction: str) -> str:
    """``none — WRONG: …`` or ``none — this copy differs …`` for a contradicted track.

    ``contradiction`` is what :func:`platterpus.verdict.track_accuraterip_contradiction`
    returned for ``track``. "none" comes first because that is the proof this
    copy has; the rest says which finding took it away.

    * **WRONG** is the owner's word for the one-frame case (plan of record §2):
      frame 450 matching places the pressing, so a whole-track miss means the
      audio differs from it. The confidence is the matched frame's entry.
    * **differs** borrows the headline's phrase
      (:func:`platterpus.verdict.differing_tracks_phrase`), with the database's
      best confidence for the track where its ``Accurip:`` row gives one.
    """
    if contradiction == AR_CONTRADICTION_WRONG:
        offset = getattr(track, "accuraterip_offset", None)
        confidence = getattr(offset, "confidence", None)
        conf = f" (confidence {confidence})" if confidence else ""
        return (
            f"none — WRONG: frame 450 matches AccurateRip's entry for this "
            f"pressing{conf} and the whole track does not, so the audio differs "
            "from it"
        )
    confidence = accuraterip_db_max_confidence(
        getattr(track, "accuraterip_lookup", None)
    )
    conf = f" (confidence {confidence})" if confidence else ""
    return (
        f"none — this copy differs from AccurateRip's entry{conf}: most likely a "
        "misread"
    )


def ctdb_tracks_by_number(ctdb_result: object) -> dict[int, object]:
    """``{track number: CtdbTrackResult}`` from a CTDB result, or ``{}``.

    Duck-typed (``ctdb_result.tracks``, each with ``.track``), so the report
    builder can pass what it holds without importing the adapter's types.
    """
    rows = getattr(ctdb_result, "tracks", None)
    if not isinstance(rows, (list, tuple)):
        return {}
    by_number: dict[int, object] = {}
    for row in rows:
        number = getattr(row, "track", None)
        if isinstance(number, int) and not isinstance(number, bool):
            by_number[number] = row
    return by_number


def _ctdb_verdict(row: object | None) -> str:
    """The row's verdict value (``match``, ``differs``, ``not_determined``) or ``""``."""
    value = getattr(getattr(row, "verdict", None), "value", None)
    return value if isinstance(value, str) else ""


def _ctdb_agrees(row: object | None) -> bool:
    """CTDB's per-track entry agrees and no stronger entry disagrees (R34)."""
    return _ctdb_verdict(row) == "match" and getattr(row, "outvoted", None) is False


def _ctdb_clause(row: object | None) -> str:
    """``; CTDB …`` for a track the proof line does not rest on CTDB for, or ``""``."""
    confidence = getattr(row, "confidence", None)
    if _ctdb_agrees(row):
        return f"; CTDB's per-track entry agrees (confidence {confidence})"
    if _ctdb_verdict(row) == "match":
        return f"; CTDB agrees only with a minority entry (confidence {confidence})"
    if _ctdb_verdict(row) == "differs":
        return "; CTDB's per-track entries differ from it too"
    return ""


def _accuraterip_matches(track: object) -> str:
    """``v1 at confidence 128 and v2 at confidence 200``: the exact matches, v1 first."""
    found = [
        f"v{getattr(ar, 'version', '?')} at confidence {getattr(ar, 'confidence', '?')}"
        for ar in (
            getattr(track, "accuraterip_v1", None),
            getattr(track, "accuraterip_v2", None),
        )
        if accuraterip_is_match(ar)
    ]
    return " and ".join(found)


def _no_entry_phrase(track: object) -> str:
    """Why AccurateRip proves nothing here, for a track it did not contradict."""
    if accuraterip_lookup_happened(getattr(track, "accuraterip_lookup", None)) is False:
        return "AccurateRip was not checked"
    return "AccurateRip has no entry for this track"


def _reads_agreed(track: object) -> str:
    """How the reads agreed, or ``""`` when nothing shows they did."""
    test_crc = str(getattr(track, "test_crc", "") or "").upper()
    copy_crc = str(getattr(track, "copy_crc", "") or "").upper()
    if test_crc and test_crc == copy_crc:
        return "the Test and Copy reads agreed"
    if getattr(track, "secure_rerip_converged", None) is True:
        reads = getattr(track, "rip_count", None)
        after = f" after {reads} reads" if isinstance(reads, int) and reads > 1 else ""
        return f"the secure re-reads agreed (converged{after})"
    return ""


def track_proof(
    track: object, *, verified_reread: bool = False, ctdb_track: object | None = None
) -> TrackProof:
    """The proof ``track``'s copy has, strongest first. Never raises.

    ``verified_reread`` is True when the track's file is a verified-read chase
    read (the report's ``read_speed.secure_rerip.verified_rereads``).
    ``ctdb_track`` is this track's CTDB per-track result, or None when CTDB was
    not consulted, as in the EAC-layout log, which is written before CTDB
    answers.

    A contradiction outranks everything but an exact match, which it cannot
    co-exist with: a copy AccurateRip calls wrong has no proof, whatever CTDB or
    the reads say, and the CTDB clause then names the disagreement.
    """
    try:
        if is_data_track(track):
            return TrackProof(
                PROOF_NONE,
                "none — a data track, which AccurateRip and CTDB do not cover",
            )
        contradiction = track_accuraterip_contradiction(track)
        if contradiction is not None:
            return TrackProof(
                PROOF_NONE,
                contradiction_sentence(track, contradiction) + _ctdb_clause(ctdb_track),
            )
        matches = _accuraterip_matches(track)
        if matches and verified_reread:
            return TrackProof(
                PROOF_VERIFIED_REREAD,
                f"a single re-read that AccurateRip verifies ({matches}), kept in "
                "place of a read it did not verify",
            )
        if matches:
            return TrackProof(PROOF_ACCURATERIP, f"AccurateRip {matches}")
        no_entry = _no_entry_phrase(track)
        if _ctdb_agrees(ctdb_track):
            confidence = getattr(ctdb_track, "confidence", None)
            return TrackProof(
                PROOF_CTDB,
                f"CTDB per track at confidence {confidence}; {no_entry}",
            )
        agreed = _reads_agreed(track)
        if agreed:
            return TrackProof(
                PROOF_READS_AGREE,
                f"{agreed}, and {no_entry}, so this shows the drive read it the same "
                "way each time, not that the audio is right" + _ctdb_clause(ctdb_track),
            )
        reads = (
            "its re-reads did not converge"
            if getattr(track, "secure_rerip_converged", None) is False
            else "no second read confirms it"
        )
        return TrackProof(
            PROOF_NONE, f"none — {no_entry}, and {reads}" + _ctdb_clause(ctdb_track)
        )
    except (AttributeError, TypeError, ValueError):
        return TrackProof(PROOF_NONE, "none — the proof could not be determined")


def verified_reread_numbers(secure_rerip: object) -> frozenset[int]:
    """The tracks whose file is a verified-read chase read, from the secure re-read block.

    Reads ``verified_rereads`` defensively, as ``eac_log_export`` does: the block
    comes from worker state, and a wrong shape must cost a clause, not the log.
    """
    if not isinstance(secure_rerip, dict):
        return frozenset()
    listed: Iterable[object] = secure_rerip.get("verified_rereads") or ()
    return frozenset(
        n for n in listed if isinstance(n, int) and not isinstance(n, bool)
    )


def track_proof_among(
    track: object, *, chased: frozenset[int], ctdb_rows: dict[int, object]
) -> TrackProof:
    """:func:`track_proof` for a track of a rip, given the rip-wide facts.

    ``chased`` is :func:`verified_reread_numbers` and ``ctdb_rows`` is
    :func:`ctdb_tracks_by_number`; both are keyed by track number, which a
    malformed track may not have, in which case neither applies.
    """
    number = getattr(track, "number", None)
    if not isinstance(number, int) or isinstance(number, bool):
        return track_proof(track)
    return track_proof(
        track, verified_reread=number in chased, ctdb_track=ctdb_rows.get(number)
    )
