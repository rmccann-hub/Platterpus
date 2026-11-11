# SPDX-License-Identifier: GPL-3.0-only
"""What the user is told about an automatic CTDB repair, in plain words (TASKS R133).

The owner's word of 2026-11-05 (``PLANNING.md`` KDD-47, amended): *"Should
ripping to a good file need a button? Either we are confident it will happen or
not, if not we need to fix that or then leave for the user but let them know."*
So every outcome of the automatic repair is said, on the results pane and in the
log view:

* **repaired**: which track, how many samples, the CTDB entry and its
  submissions, how it was proved, what a fresh CTDB check of the repaired files
  says, what AccurateRip can and cannot say about it, and where the original is;
* **refused or failed**: that the rip differs from the strongest entry, why it
  was not repaired (the guard's own sentence), what the user can do, and where
  the full details are (``ui/failure_text.LOG_POINTER``, ``docs/architecture.md``
  §4 *Add a failure path*).

Status is never colour alone: every sentence starts with its marker (``✓``,
``⚠``, ``ⓘ``), and the level travels beside the text for the label's colour.

**AccurateRip after a repair is "not determined", and said so, per version.**
Platterpus has no AccurateRip lookup of its own (cyanrip does it during the rip,
and its log prints only our checksums, never the database's for a track that did
not match), so the repaired track's AccurateRip v1 and v2 checksums are stated
for a reader to compare, each with "not determined", and never called verified
(:func:`accuraterip_after_repair`, which the EAC-layout log's ``Record:`` row and
the report's per-track ``record`` share). Pure and Qt-free; never raises.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from platterpus.ctdb.repair_types import RepairStatus

#: The levels ``ui/status_colours.status_style`` colours. Named here, not
#: imported, because that module is Qt and this one must not be.
LEVEL_OK: Final[str] = "ok"
LEVEL_WARN: Final[str] = "warn"
LEVEL_INFO: Final[str] = "neutral"

#: Why the repair did not run, when Settings turned it off. One constant, so the
#: window that builds the record and any reader of it agree on the words.
OFF_IN_SETTINGS: Final[str] = (
    "automatic CTDB repair is off in Settings (Repair from CTDB after a rip)"
)
#: Why the repair did not run, when a newer rip had started before it could.
NEWER_RIP: Final[str] = (
    "a newer rip started before the repair could run, so this album was left as "
    "it was ripped"
)
#: Why the repair did not run, when another album's repair still held the worker.
ANOTHER_REPAIR: Final[str] = (
    "another album's CTDB repair was still running, so this one was not started"
)
#: The reason a repair the app stopped carries (closing, or a cancel).
CANCELLED: Final[str] = (
    "the repair was stopped before it finished (the app was closing); nothing "
    "was replaced"
)
#: The reason recorded when the app closed and the worker could not be waited for.
CLOSED_UNFINISHED: Final[str] = (
    "the app closed before the CTDB repair finished; if it had already replaced a "
    "file, the original is kept beside it as '<name>.flac.before-ctdb-repair'"
)

_REFUSED_ADVICE: Final[str] = (
    "What you can do: clean the disc and rip it again, or rip it in another "
    "drive. If AccurateRip verified the track, the read is right as it is and "
    "nothing needs doing."
)
_FAILED_ADVICE: Final[str] = (
    "What you can do: check that flac and metaflac (1.4 or later) are installed "
    "(Tools → Setup & Updates…), then rip the disc again; or clean the disc, or "
    "rip it in another drive."
)


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def after_repair_agrees(after: object | None) -> bool | None:
    """Does the fresh CTDB check of the repaired files agree? Tri-state.

    ``None`` when no fresh check ran; ``True`` for a match no stronger entry
    outvotes; ``False`` otherwise. The one predicate the results pane's sentence
    and each repaired track's record (``track_record.py``) read, so the two cannot
    describe one check two ways.
    """
    if after is None:
        return None
    verdict = getattr(getattr(after, "verdict", None), "value", None)
    outvoted = bool(getattr(after, "outvoted", False))
    return verdict == "match" and not outvoted


def _hex(value: object) -> str | None:
    """``BCF4E815`` for an int checksum, else None (a bool is not a checksum)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:08X}"
    return None


#: Why AccurateRip's answer about repaired audio is "not determined", said once.
ACCURATERIP_AFTER_REPAIR_WHY: Final[str] = (
    "Platterpus has no AccurateRip lookup of its own, and the rip's AccurateRip "
    "answer describes the read"
)


def accuraterip_after_repair(v1: object, v2: object) -> str:
    """``AccurateRip v1 134C0B9D: not determined; v2 BCF4E815: not determined (…)``.

    **Whether each version matched, stated per version, and the answer is "not
    determined"** (G3, 2026-11-11). Our own checksums of the repaired file are
    known (``accuraterip_crc.py``); AccurateRip's entries for the track are not,
    because cyanrip looks AccurateRip up during the rip and prints the database's
    value only for a read that MATCHED it, and a track the repair rewrote is one
    whose read did not (``ctdb/repair_plan.py`` refuses an AccurateRip-verified
    track). So neither "matched" nor "did not match" can be said, and the
    tri-state's third value is printed rather than either guess. Taking ints
    (``RepairedTrack``) or hex strings (the report's ``ctdb.repair.tracks``).
    """
    parts: list[str] = []
    for version, value in (("v1", v1), ("v2", v2)):
        crc = _hex(value) or (value.upper() if isinstance(value, str) else None)
        parts.append(
            f"{version} {crc}: not determined" if crc else f"{version}: no checksum"
        )
    return f"AccurateRip {'; '.join(parts)} ({ACCURATERIP_AFTER_REPAIR_WHY})"


def _after_sentence(after: object | None) -> tuple[str, bool]:
    """What the fresh CTDB check of the repaired files said; True when it agrees."""
    if after is None:
        return ("A fresh CTDB check of the repaired files did not run.", False)
    verdict = getattr(getattr(after, "verdict", None), "value", None)
    if after_repair_agrees(after):
        confidence = int(getattr(after, "confidence", 0) or 0)
        return (
            "A fresh CTDB check of the repaired files agrees: they match "
            f"{_plural(confidence, 'submission')}.",
            True,
        )
    message = str(getattr(after, "message", "") or verdict or "no verdict")
    return (f"A fresh CTDB check of the repaired files says: {message}.", False)


def _accuraterip_sentence(tracks: tuple[object, ...]) -> str:
    """AccurateRip about the repaired tracks, per track and per version.

    Through :func:`accuraterip_after_repair`, the words each repaired track's
    ``Record:`` row in the EAC-layout log and the report's ``record`` use too, so
    the results pane cannot say one thing about a version and the log another.
    """
    parts = [
        f"Track {getattr(row, 'track', '?')}: "
        + accuraterip_after_repair(
            getattr(row, "accuraterip_v1_after", None),
            getattr(row, "accuraterip_v2_after", None),
        )
        + "."
        for row in tracks
    ]
    return " ".join(parts) or (
        f"AccurateRip: not determined for the repaired audio "
        f"({ACCURATERIP_AFTER_REPAIR_WHY})."
    )


def repaired_text(result: object) -> tuple[str, str]:
    """``(level, text)`` for a REPAIRED record. The level is OK only when CTDB agrees."""
    record = getattr(result, "repair", None)
    tracks = tuple(getattr(record, "tracks", ()) or ())
    described = "; ".join(
        f"track {getattr(row, 'track', '?')} "
        f"({_plural(int(getattr(row, 'samples_corrected', 0) or 0), 'sample')} "
        "corrected)"
        for row in tracks
    )
    confidence = int(getattr(record, "confidence", 0) or 0)
    entry = getattr(record, "entry_id", "") or "?"
    offset = getattr(record, "offset", None)
    where = f", offset {offset:+d}" if isinstance(offset, int) and offset else ""
    kept = ", ".join(
        f"'{Path(str(getattr(row, 'original_kept_as', '') or '')).name}'"
        for row in tracks
    )
    after, agrees = _after_sentence(getattr(result, "after_repair", None))
    marker = "✓" if agrees else "⚠"
    text = (
        f"{marker} Repaired from CTDB: {described or 'no track named'}, toward the "
        f"CTDB entry with {_plural(confidence, 'submission')} (entry {entry}{where}). "
        "Proved before anything was replaced: the new file decodes to the original "
        "audio plus exactly those corrections, and the whole disc's CTDB checksum "
        f"now equals that entry's. {after} {_accuraterip_sentence(tracks)} The "
        f"original file is kept beside it as {kept or 'its .before-ctdb-repair copy'}"
        ". The rip's logs still record the read as it was: the ripper's own log "
        "is never changed, and the EAC-layout log keeps the read's rows and names "
        "this repair beside them in each repaired track's Record row."
    )
    return (LEVEL_OK if agrees else LEVEL_WARN), text


def not_repaired_text(result: object, *, log_pointer: str) -> tuple[str, str]:
    """``(level, text)`` for a REFUSED or FAILED record: what, why, what to do, where.

    ``log_pointer`` is ``ui/failure_text.LOG_POINTER``, passed in so this module
    stays free of the UI package; the sweep in ``tests/test_failure_surfaces.py``
    holds the UI to appending that one sentence rather than its own.
    """
    record = getattr(result, "repair", None)
    status = getattr(record, "status", None)
    reason = str(getattr(record, "reason", "") or "no reason was recorded").rstrip(".")
    best = int(getattr(result, "best_confidence", 0) or 0)
    strongest = (
        f"the strongest CTDB entry ({_plural(best, 'submission')})"
        if best
        else "the strongest CTDB entry"
    )
    if reason == OFF_IN_SETTINGS:
        return LEVEL_INFO, (
            f"ⓘ This rip differs from {strongest}, and was not repaired because "
            f"{reason}. Turn it on and rip the disc again to have Platterpus repair "
            "it when it can prove the result."
        )
    verb = (
        "could not finish repairing it"
        if status is RepairStatus.FAILED
        else ("did not repair it")
    )
    advice = _FAILED_ADVICE if status is RepairStatus.FAILED else _REFUSED_ADVICE
    return LEVEL_WARN, (
        f"⚠ This rip differs from {strongest}, and Platterpus {verb}: {reason}. "
        f"Nothing was changed. {advice}\n\n{log_pointer}"
    )


def repair_text(result: object, *, log_pointer: str) -> tuple[str, str] | None:
    """The sentence for any repair outcome on ``result``, or None when there was none."""
    record = getattr(result, "repair", None)
    if record is None:
        return None
    if getattr(record, "status", None) is RepairStatus.REPAIRED:
        return repaired_text(result)
    return not_repaired_text(result, log_pointer=log_pointer)


#: Shown while the repair works, so a long decode never looks like a hang.
IN_PROGRESS: Final[str] = (
    "ⓘ This rip differs from the strongest CTDB entry. Repairing it from that "
    "entry's parity, and proving the result before anything is replaced…"
)
