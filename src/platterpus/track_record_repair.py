# SPDX-License-Identifier: GPL-3.0-only
"""A CTDB repair's record line, and the read it names as the one repaired.

Split from :mod:`platterpus.track_record` (which words every kind of record)
because the repair's line is the one kind with its own question: WHICH read the
repair started from. A repair rewrites the file as it stood, and after a
securing pass whose read was not kept, the track's re-read fields describe that
pass's reads while the file holds the album pass's (TASKS R156, the fork's
round 40 lap 3 S14). :func:`repair_source` answers it from the merge's own
statement of which read the file holds; :func:`repaired_line` words the line.

Pure; no Qt, no I/O; reads with ``getattr``; never raises.
"""

from __future__ import annotations

from platterpus.ctdb.repair_wording import accuraterip_after_repair
from platterpus.track_record_reads import album_pass_read_path
from platterpus.track_record_sources import RepairFacts, upper_hex
from platterpus.verified_read_chase import KEPT_FIRST_READ


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def repaired_line(facts: RepairFacts, source: str) -> str:
    """``repaired from CTDB entry 32115 (…) after the read (…): Copy CRC …; …``.

    ``source`` is the parenthetical, :func:`repair_source`'s answer.
    """
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
        facts.accuraterip_v1_after,
        facts.accuraterip_v2_after,
        facts.accuraterip_v1_database,
        facts.accuraterip_v2_database,
    )
    return (
        f"repaired from CTDB entry {facts.entry_id} "
        f"(confidence {facts.confidence:,}) after the read ({source}): "
        f"{crcs}{samples}; {fresh}; {ar}"
    )


def repair_source(
    track: object,
    facts: RepairFacts,
    *,
    path: str,
    chased: bool,
    chase_attempt: int | None,
    every_other_read_printed: bool,
) -> str:
    """The read a CTDB repair started from, for its line's parenthetical (R156).

    A repair rewrites the file as it stood, so it starts from the read the file
    held, the one whose Copy CRC is the repair's ``crc_before``. Which read that
    was is the merge's statement (``TrackResult.kept_read_pass``), not
    :func:`read_path`'s: after a securing pass whose read was not kept, the
    track's re-read fields describe THAT pass's reads while the file holds the
    album pass's. Rip 1 of the owner's 2026-11-14 run printed ``after the read
    (re-read, at most 5 agreeing): Copy CRC 6902BCF0 before`` where ``6902BCF0``
    was the album pass's single read and the five agreeing reads were the
    securing pass's ``E0036697`` (the fork's round 40 lap 3 S14).

    When the record's own Copy CRC is not the repair's starting CRC, the two
    describe different reads and we cannot say which one the repair started
    from, so the line says so rather than naming one.
    """
    copy_crc = upper_hex(getattr(track, "copy_crc", None))
    if facts.crc_before and copy_crc and copy_crc != facts.crc_before:
        return f"which read is not determined: the record's Copy CRC is {copy_crc}"
    if chased:
        return (
            f"chase attempt {chase_attempt}, a single read"
            if chase_attempt
            else "a chase attempt, a single read"
        )
    if getattr(track, "kept_read_pass", "") == KEPT_FIRST_READ:
        return album_pass_read_path(
            track, every_other_read_printed=every_other_read_printed
        )
    return path
