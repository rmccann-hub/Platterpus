# SPDX-License-Identifier: GPL-3.0-only
"""How far the verified-read chase may go for one track: reads, time, and the cache.

:mod:`platterpus.verified_read_chase` decides WHETHER a track is chased; this
module decides HOW FAR: how many single reads it may take, how long they may take
in all, and whether one read can be served from the drive's cache left by the
read before it. Round 39's gate G1 (the owner's plan of 2026-11-11): track 3 of
the reference disc must end AccurateRip-verified from a drive read on five
default whole-disc rips in a row.

**Rule 1, the attempt limit: 16 for a track AccurateRip knows at high
confidence, the user's ``-r`` (at most 5) otherwise.** Track 3 reads right about
one read in three on the owner's BDR-209D: 7 of 22 on 2026-11-09, 12 of 37 over
every filed read. If reads were independent, the chance that N single reads all
miss is (2/3)^N, and G1 needs five rips in a row to hit, (1 - (2/3)^N)^5:

    N =  5 -> 0.49   (the old limit: G1 fails one time in two)
    N = 12 -> 0.96
    N = 16 -> 0.992  (the smallest N at which the model gives G1 at 99%)

Reads are NOT independent: 0 of 7 on 2026-11-03b and 0 of 8 in 2026-11-04's
paired rips, which the independent model gives 6% and 4%. In such a session no
count reaches 99%, and more reads only cost time. That is why the TIME budget
(rule 2), not the count, is what bounds the chase in practice, and why the count
stays bounded at all instead of reading "until verified".

**"High confidence" means AccurateRip's top entry for the track has confidence
>= 10** (:data:`CHASE_HIGH_CONFIDENCE_MIN`; the ``max confidence:`` figure of
cyanrip's ``Accurip:`` row, read by ``verdict.accuraterip_db_max_confidence``).
Extra reads pay only when the entry is a value this disc can give: when our
disagreement with it is a misread, not a different pressing. That is a
judgement, and the data constrain it only from one side: every track the chase
or a re-read has verified on hardware must qualify (the reference disc's tracks
3 and 5 at 200; disc 3's track 16 on 2026-10-22, the chase's one hardware keep,
at v2 confidence 24). The costs are asymmetric. A false positive raises the
limit where it cannot pay and costs time the budget already bounds; a false
negative loses a verified read, the thing the archival master is protected
for. So the threshold sits low, and below it, where a handful of submitters or a
shared misread can be the top entry, the ordinary limit still runs.

**The high limit needs a time budget.** It is granted only when rule 2's budget
could be computed. Without one, 16 whole-track reads of a damaged track can be
days (disc 1's track 18 read once in 8,548 s on 2026-10-21, TASKS R49), so a
track whose length is not stated keeps the ordinary limit: a fail-safe defined
against the drive time a person is waiting through, since the read kept is the
same either way.

**Rule 2, the time budget (TASKS R49): the larger of 5 x the track's length and
2 x its album-pass read time.** The precedent is EAC's extraction option "Skip
track extraction after duration longer than n times realtime" (named by the
owner's round 39 plan; we have not read EAC's source, which is closed). A
multiple of the track's length is what EAC bounds by; a multiple of what the
drive actually took on the album pass keeps a slow drive or a slow disc from
being stopped after one read. Checked BETWEEN reads, the way the fork checks its
``--reread-time-limit`` (``cyanrip@5cc1c6b:src/cyanrip_main.c:2068-2075``): a
read in progress is never stopped, so the first read always runs and the last
can run past the budget. The fork's option cannot carry it here: a chase read is
a single read with no ``-Z``, and cyanrip refuses ``--reread-time-limit``
without ``-Z`` (exit 64, ``cyanrip@5cc1c6b:src/cyanrip_main.c:3414-3417``), so
the chase measures its own time. Where ``.31``'s ``--reread-until-accuraterip``
has already read a ``-Z`` track toward a verified read, the chase is only the
fallback for a track it left unverified (``workers/chase_passes.py``).

**Rule 3, the drive cache between chase reads.** Each chase read is a separate
cyanrip run. Inside one run, paranoia's cache model defeats the drive's cache on
every backseek (``cd-paranoia -A`` reports this drive's 137 to 144 sectors as
defeated); between two runs nothing does, and the run before left its last
sectors, the END of this same track, in the cache. The drive's cache holds 128
to 255 sectors (``.30``'s ``Cache probe:``, the fork's round 38 lap 8 S12).
A chase read starts at the track's FIRST sector, so it reads ``length - 255``
sectors the cache cannot hold before it reaches any it might; the fork's own
figure for a read that flushes this cache is 312 sectors (their round 38 lap 8
S12). So a track of at least 255 + 312 = 567 sectors (7.56 s) has its cache
defeated by the read itself, every time, with nothing added. A shorter track is
recorded ``not_assured``: no mechanism we have defeats the cache between two
runs, and inventing one would mean a route to the drive that is not the ripper.
A cached read cannot make a wrong read pass, since AccurateRip is the judge and
the cache only repeats what the drive already returned, so the cost of
``not_assured`` is attempts that may repeat, never a false verification.

Pure: no Qt, no I/O, never raises.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Final

log = logging.getLogger(__name__)

#: Rule 1: the most single reads a track AccurateRip knows weakly, or not at
#: all, gets, whatever ``-r`` says (the chase's limit before round 39).
CHASE_ATTEMPTS_CEILING: Final[int] = 5
#: Rule 1: the AccurateRip top-entry confidence from which a track is "known at
#: high confidence" (the module docstring says why 10).
CHASE_HIGH_CONFIDENCE_MIN: Final[int] = 10
#: Rule 1: the most single reads such a track gets (the module docstring says
#: why 16: G1 at 99% under independent reads at the measured one in three).
CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING: Final[int] = 16

#: ``verified_read_chase.attempt_limit_reason``: the user's ``-r``, at most 5.
LIMIT_FROM_REPEAT_LIMIT: Final[str] = "repeat_limit"
#: ``verified_read_chase.attempt_limit_reason``: rule 1's high limit.
LIMIT_FROM_HIGH_CONFIDENCE: Final[str] = "high_confidence"

#: Rule 2: the budget is at least this many times the track's length (EAC's
#: "n times realtime").
CHASE_BUDGET_REALTIME_MULTIPLE: Final[int] = 5
#: Rule 2: and at least this many times what the album pass took to read it.
CHASE_BUDGET_READ_TIME_MULTIPLE: Final[int] = 2

#: A CD plays 75 sectors a second (Red Book), so a length in sectors divided by
#: this is the track's length in seconds.
SECTORS_PER_SECOND: Final[int] = 75

#: Rule 3: the largest cache this drive was measured to have, in sectors
#: (``.30``'s ``Cache probe:`` bracket, 128 to 255).
DRIVE_CACHE_CEILING_SECTORS: Final[int] = 255
#: Rule 3: sectors a read must take from elsewhere to flush that cache (the
#: fork's round 38 lap 8 S12: twelve reads of 26 sectors between every pass).
CACHE_FLUSH_SECTORS: Final[int] = 312
#: Rule 3: the shortest track whose own read flushes the cache before it reaches
#: anything the previous read can have left there.
CACHE_SELF_DEFEATING_SECTORS: Final[int] = (
    DRIVE_CACHE_CEILING_SECTORS + CACHE_FLUSH_SECTORS
)

#: ``verified_read_chase.cache_defeat``: the read flushes the cache itself.
CACHE_DEFEATED_BY_WHOLE_TRACK_READ: Final[str] = "whole_track_read"
#: The track is too short for that; nothing we have defeats it between runs.
CACHE_DEFEAT_NOT_ASSURED: Final[str] = "not_assured"
#: The track's length is not stated, so it cannot be said (never "assured").
CACHE_DEFEAT_NOT_DETERMINED: Final[str] = "not_determined"


@dataclass(frozen=True)
class ChaseBudget:
    """How far one track's chase may go, and every input that decided it.

    ``attempt_limit`` is rule 1's count and ``limit_reason`` which arm gave it
    (``LIMIT_FROM_*``). ``time_budget_seconds`` is rule 2's budget, ``None`` when
    the track's length is not stated (then only the count bounds the chase).
    ``cache_defeat`` is rule 3's answer (``CACHE_*``). The inputs are kept so the
    report can show the arithmetic, not only its result.
    """

    attempt_limit: int = 1
    limit_reason: str = LIMIT_FROM_REPEAT_LIMIT
    accuraterip_top_confidence: int | None = None
    track_seconds: float | None = None
    album_read_seconds: float | None = None
    time_budget_seconds: float | None = None
    cache_defeat: str = CACHE_DEFEAT_NOT_DETERMINED


def track_sectors(track: object | None) -> int | None:
    """A parsed track's length in sectors, from its own Start/End LSN, or None.

    Both ends are inclusive in cyanrip's block (``Start LSN: 28067 ... End LSN:
    49919`` is track 3's 21,853 frames, which its ``Frames:`` row also says).
    Anything not a positive length is not stated. Never raises.
    """
    start = _whole(getattr(track, "start_sector", None))
    end = _whole(getattr(track, "end_sector", None))
    if start is None or end is None:
        return None
    length = end - start + 1
    return length if length > 0 else None


def track_seconds(track: object | None) -> float | None:
    """A parsed track's length in seconds (sectors / 75), or None. Never raises."""
    sectors = track_sectors(track)
    return None if sectors is None else sectors / SECTORS_PER_SECOND


def read_elapsed_seconds(track: object | None) -> float | None:
    """What a read of the track took, by its own ``Elapsed:`` row, or None.

    The fork prints it per track; stock cyanrip does not, and a missing value is
    "not stated", never zero. Never raises.
    """
    value = getattr(track, "extraction_elapsed_seconds", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def time_budget_seconds(
    length_seconds: float | None, read_seconds: float | None
) -> float | None:
    """Rule 2: max(5 x length, 2 x album-pass read time); None without a length.

    The length is required: it is the EAC precedent's own measure and the floor
    of the budget, while the read time is the fork's alone and only ever raises
    it. Never raises.
    """
    if length_seconds is None or length_seconds <= 0:
        return None
    budget = CHASE_BUDGET_REALTIME_MULTIPLE * length_seconds
    if read_seconds is not None and read_seconds > 0:
        budget = max(budget, CHASE_BUDGET_READ_TIME_MULTIPLE * read_seconds)
    return budget


def attempt_limit(
    max_retries: int, top_confidence: int | None, *, budget_known: bool
) -> tuple[int, str]:
    """Rule 1: ``(limit, LIMIT_FROM_*)``. Never raises.

    The high limit needs both a top entry at :data:`CHASE_HIGH_CONFIDENCE_MIN` or
    more AND a time budget (the module docstring says why each).
    """
    ordinary = max(1, min(_whole(max_retries) or 1, CHASE_ATTEMPTS_CEILING))
    if (
        budget_known
        and top_confidence is not None
        and top_confidence >= CHASE_HIGH_CONFIDENCE_MIN
    ):
        return CHASE_HIGH_CONFIDENCE_ATTEMPTS_CEILING, LIMIT_FROM_HIGH_CONFIDENCE
    return ordinary, LIMIT_FROM_REPEAT_LIMIT


def cache_defeat(sectors: int | None) -> str:
    """Rule 3 for a track of ``sectors``: one of the ``CACHE_*`` words. Never raises."""
    if sectors is None:
        return CACHE_DEFEAT_NOT_DETERMINED
    if sectors >= CACHE_SELF_DEFEATING_SECTORS:
        return CACHE_DEFEATED_BY_WHOLE_TRACK_READ
    return CACHE_DEFEAT_NOT_ASSURED


def top_confidence(*tracks: object | None) -> int | None:
    """AccurateRip's top-entry confidence for the track, from the first record
    whose ``Accurip:`` row states it (the kept read's, then the album pass's).

    The same entry is printed on every read of one track, since it is the
    database's and not the read's; the first stated one is taken. Never raises.
    """
    # Imported here, not at the top: `verdict` imports `read_speed_ladder`
    # (through `accuraterip_standing`), which imports the chase, which imports
    # this module, so a top-level import is a cycle. The one reader of the
    # figure is reused rather than a second pattern written here.
    from platterpus.verdict import accuraterip_db_max_confidence

    for track in tracks:
        value = accuraterip_db_max_confidence(
            getattr(track, "accuraterip_lookup", None)
        )
        if value is not None:
            return value
    return None


def plan_budget(
    *, kept: object | None, album_pass: object | None, max_retries: int
) -> ChaseBudget:
    """All three rules for one track. Never raises; a failure gives rule 1's
    ordinary limit with nothing else known, the behaviour before round 39.

    ``kept`` is the read the album holds now; ``album_pass`` the album pass's
    record of the track (its read time is rule 2's second term). The length is
    taken from whichever states it, the album pass first: the LSNs are the
    disc's, so every read of one track states the same pair.
    """
    try:
        sectors = track_sectors(album_pass)
        if sectors is None:
            sectors = track_sectors(kept)
        length = None if sectors is None else sectors / SECTORS_PER_SECOND
        read = read_elapsed_seconds(album_pass)
        budget = time_budget_seconds(length, read)
        confidence = top_confidence(kept, album_pass)
        limit, reason = attempt_limit(
            max_retries, confidence, budget_known=budget is not None
        )
        return ChaseBudget(
            attempt_limit=limit,
            limit_reason=reason,
            accuraterip_top_confidence=confidence,
            track_seconds=length,
            album_read_seconds=read,
            time_budget_seconds=budget,
            cache_defeat=cache_defeat(sectors),
        )
    except Exception:  # noqa: BLE001 — a budget that cannot be made is the old limit
        log.exception("chase budget failed; keeping the ordinary attempt limit")
        limit, reason = attempt_limit(max_retries, None, budget_known=False)
        return ChaseBudget(attempt_limit=limit, limit_reason=reason)


def _whole(value: object) -> int | None:
    """``value`` when it is a whole number (a bool is not one), else None."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None
