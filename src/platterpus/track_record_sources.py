# SPDX-License-Identifier: GPL-3.0-only
"""The facts a track's record needs that the parsed log does not hold.

Split from :mod:`platterpus.track_record` (which words the record) because these
READ other records, each defensively: the CTDB repair's outcome
(``ctdb_result.repair``), the chase's kept attempt (the report's
``read_speed.retried_tracks``), and the ripper build, for the seam where the
fork's ``.31`` AccurateRip-guided ``-Z`` rule will be recognised. Reading and
wording are separate jobs, and the pair crossed the module-size heuristic.

Pure; no Qt, no I/O; reads with ``getattr``; never raises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from platterpus.ctdb.repair_wording import after_repair_agrees
from platterpus.reread_ar_overrule import AccurateRipOverrule, record_phrase

#: **The ``.31`` seam: fork build numbers whose log we can read for the
#: AccurateRip-guided ``-Z`` rule.** Empty until ``.31`` was published
#: (2026-11-11, ``e531a33``, their round 39 lap 1 S2); its log text is P2 of
#: ``round-39-lap-01-provider-contract-g6eacb8b.md`` (lines 376 and 504 to 512),
#: read by :mod:`platterpus.reread_ar_overrule` into the track's
#: ``secure_rerip_ar_overrule``, which :func:`_ar_guided_read` reads. A later
#: build joins when its own contract is filed and still prints the lines.
AR_GUIDED_CONVERGENCE_BUILDS: Final[frozenset[int]] = frozenset({31})
#: The first fork build that may apply the rule. A re-read from it or later that
#: this release cannot read says "not determined" rather than calling the read a
#: plain re-read, which it might not be.
AR_GUIDED_FIRST_BUILD: Final[int] = 31

#: **Fork builds whose log prints an ``Other read:`` line for EVERY ``-Z`` read
#: that was not kept** (:mod:`platterpus.other_reads`), so a converged track that
#: prints none had all its reads agree, and the record's count is exact (TASKS
#: R140, our round 39 lap 2 S16). Read in their source, not assumed: each distinct
#: checksum of a ``-Z`` track is filed as its own spool, a repeat adding a count
#: (``cyanrip@e531a33:src/cyanrip_main.c:2034-2079``; ``cyanrip@5cc1c6b`` the same
#: at ``:2011``), every spool is copied onto the track when the track is decided
#: (``crip_keep_reads``, ``cyanrip@e531a33:src/cyanrip_main.c:1442-1460``, called
#: at ``:2480``; ``cyanrip@5cc1c6b:src/cyanrip_main.c:1422``, ``:2351``), and the
#: log prints one line per read not kept (``cyanrip@e531a33:src/cyanrip_log.c:
#: 874-896``, ``cyanrip@5cc1c6b:src/cyanrip_log.c:869-891``). The one gap in
#: that chain is ``crip_keep_reads``'s allocation failing, which prints no lines
#: at all; a converged ``-Z`` track has at most ``-r`` spools, so it is an
#: out-of-memory case only. ``.30`` (``5cc1c6b``) and ``.31`` (``e531a33``),
#: whose meson.build line 21 names each. Enumerated, never ``>= 30``: a later
#: build joins when its own source is read, and until then its record keeps the
#: floor, which is true and only weaker.
OTHER_READS_COMPLETE_BUILDS: Final[frozenset[int]] = frozenset({30, 31})

# "cyanrip 0.9.4-rc3+platterpus.31": the fork's own build number. Bounded.
_FORK_BUILD: Final[re.Pattern[str]] = re.compile(r"\+platterpus\.(?P<n>\d{1,4})\b")


@dataclass(frozen=True)
class RepairFacts:
    """What the CTDB repair did to one track, from ``ctdb_result.repair``."""

    entry_id: str
    confidence: int
    samples_corrected: int | None
    crc_before: str | None
    crc_after: str | None
    accuraterip_v1_after: object
    accuraterip_v2_after: object
    # AccurateRip's database about each (TASKS R138): an `ArDbAnswer`, or None
    # when the repair recorded no lookup.
    accuraterip_v1_database: object
    accuraterip_v2_database: object
    after_agrees: bool | None
    after_confidence: int | None


def int_or_none_strict(value: object) -> int | None:
    """``value`` when it is an int and not a bool, else None."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def upper_hex(value: object) -> str | None:
    """``C96464AB`` from an int or a hex string; None otherwise."""
    number = int_or_none_strict(value)
    if number is not None:
        return f"{number:08X}"
    return value.upper() if isinstance(value, str) and value else None


def repaired_tracks_by_number(ctdb_result: object) -> dict[int, RepairFacts]:
    """``{track: RepairFacts}`` for each track a REPAIRED record rewrote, else ``{}``.

    Only a ``repaired`` status counts: a refused or failed repair replaced
    nothing, and its track keeps the read's record (``ctdb/repair_types.py``).
    """
    record = getattr(ctdb_result, "repair", None)
    status = getattr(getattr(record, "status", None), "value", None)
    if status != "repaired":
        return {}
    after = getattr(ctdb_result, "after_repair", None)
    agrees = after_repair_agrees(after)
    after_confidence = int_or_none_strict(getattr(after, "confidence", None))
    facts: dict[int, RepairFacts] = {}
    for row in getattr(record, "tracks", ()) or ():
        number = int_or_none_strict(getattr(row, "track", None))
        if number is None:
            continue
        facts[number] = RepairFacts(
            entry_id=str(getattr(record, "entry_id", "") or "?"),
            confidence=int_or_none_strict(getattr(record, "confidence", None)) or 0,
            samples_corrected=int_or_none_strict(
                getattr(row, "samples_corrected", None)
            ),
            crc_before=upper_hex(getattr(row, "pcm_crc32_before", None)),
            crc_after=upper_hex(getattr(row, "pcm_crc32_after", None)),
            accuraterip_v1_after=getattr(row, "accuraterip_v1_after", None),
            accuraterip_v2_after=getattr(row, "accuraterip_v2_after", None),
            accuraterip_v1_database=getattr(row, "accuraterip_v1_database", None),
            accuraterip_v2_database=getattr(row, "accuraterip_v2_database", None),
            after_agrees=agrees,
            after_confidence=after_confidence,
        )
    return facts


def chase_attempts_by_track(retried_tracks: object) -> dict[int, int]:
    """``{track: k}`` for each track whose file is the chase's ``k``-th read.

    From the report's ``read_speed.retried_tracks`` (``RetriedTrackBlock``), read
    defensively: a wrong shape costs the attempt number, never the record.
    """
    found: dict[int, int] = {}
    if not isinstance(retried_tracks, (list, tuple)):
        return found
    for block in retried_tracks:
        if not isinstance(block, Mapping):
            continue
        chase = block.get("verified_read_chase")
        number = int_or_none_strict(block.get("track"))
        kept = (
            int_or_none_strict(chase.get("kept_attempt"))
            if isinstance(chase, Mapping)
            else None
        )
        if number is not None and kept is not None:
            found[number] = kept
    return found


def fork_build_number(ripper_version: str) -> int | None:
    """``31`` from ``cyanrip 0.9.4-rc3+platterpus.31``; None when it names none."""
    match = _FORK_BUILD.search(ripper_version or "")
    return int(match.group("n")) if match else None


def prints_every_other_read(ripper_version: str) -> bool:
    """Does this build print an ``Other read:`` line for every ``-Z`` read not kept?

    True only for :data:`OTHER_READS_COMPLETE_BUILDS`. False for stock cyanrip,
    an older fork build, a later one not yet read, or no version at all: those
    keep the floor wording, the safe direction for a record that claims what the
    log proves. Never raises.
    """
    return fork_build_number(ripper_version) in OTHER_READS_COMPLETE_BUILDS


def ar_guided_convergence(track: object, ripper_version: str) -> bool | None:
    """Did the fork's ``.31`` AccurateRip-guided ``-Z`` rule keep this read?

    Tri-state. ``False`` for a build before :data:`AR_GUIDED_FIRST_BUILD` (or no
    fork number at all: stock cyanrip has no such rule). ``None`` for a ``.31`` or
    later build this release cannot read (not in
    :data:`AR_GUIDED_CONVERGENCE_BUILDS`): it may have applied the rule, and we do
    not know its words. For a listed build, ``True`` when AccurateRip ended the
    track's reads (``.31``'s early end), ``False`` when the log says it did not.
    """
    build = fork_build_number(ripper_version)
    if build is None or build < AR_GUIDED_FIRST_BUILD:
        return False
    if build not in AR_GUIDED_CONVERGENCE_BUILDS:
        return None
    return _ar_guided_read(track)


def _ar_guided_read(track: object) -> bool:
    """The ``.31`` log's own statement for this track: did AccurateRip end it?

    ``True`` for a track whose ``-Z`` reads ended on a read AccurateRip matches
    after an agreement it overruled (``cyanrip@e531a33:src/cyanrip_main.c:2140``
    and its row at ``src/cyanrip_log.c:852``); ``False`` otherwise, since a
    ``.31`` log that names no such end is a statement that none happened.
    """
    overrule = getattr(track, "secure_rerip_ar_overrule", None)
    return isinstance(overrule, AccurateRipOverrule) and overrule.ended_on_match


def ar_overrule_words(track: object) -> str | None:
    """The record's words for ``.31``'s overrule of this track, or ``None``.

    :func:`platterpus.reread_ar_overrule.record_phrase`: an early end reads
    ``re-read: matched AccurateRip at confidence N after k reads, overruling an
    agreement on X``; a limit after an overrule reads ``an agreement on X was
    overruled by AccurateRip``. Never raises.
    """
    overrule = getattr(track, "secure_rerip_ar_overrule", None)
    if not isinstance(overrule, AccurateRipOverrule):
        return None
    return record_phrase(overrule)
