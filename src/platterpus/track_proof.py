"""Which proof each track's copy has, in the one wording every surface prints.

**Why this module exists** (the owner's EAC-parity plan of record, 2026-10-26,
rows 8 and 9). The worst outcome the owner names is *a wrong track reported as
fine*. On the Police disc's secure re-read of 2026-10-21, track 3 read
``3D8FCF0C``, matched AccurateRip on frame 450 only, and the EAC-layout log said
"confirmed across 4 secure re-reads … Copy OK" over it. The facts were all in the
parsed log; no surface turned them into a sentence about the track.

So this is that sentence. It reads the verdict's predicates
(:mod:`platterpus.verdict` is the single source) and words what they found:
it computes nothing of its own about AccurateRip. The EAC-layout log's
``Proof:`` row and the report's per-track record both come from here, so the
two cannot describe one track two ways.

Pure; no Qt, no I/O; reads with ``getattr`` and never raises.
"""

from __future__ import annotations

from platterpus.verdict import (
    AR_CONTRADICTION_WRONG,
    accuraterip_db_max_confidence,
)


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
