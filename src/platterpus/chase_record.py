# SPDX-License-Identifier: GPL-3.0-only
"""The verified-read chase's report record: one attempt, one track's chase.

Split from :mod:`platterpus.verified_read_chase` in round 39 (gate G1), when the
record grew the time budget, the limit's reason, the pass it followed and each
attempt's times (report schema 45), so the decision and the record each stay a
focused module. :mod:`platterpus.verified_read_chase` decides whether a track is
chased; :mod:`platterpus.chase_budget` how far; this writes down what happened,
in the words another surface prints ("chase attempt k", the time, why it
stopped). ``verified_read_chase.copy_chase_block`` copies it into the report.

**The words, and what each means** (schema 45, ``report_types.
VerifiedReadChaseBlock``): ``stopped_reason`` is what ended a chase that kept no
read, and ``after`` which pass's kept read the chase tried to better. The
outcome words stay :mod:`platterpus.verified_read_chase`'s, where they were.

Pure: no Qt, no I/O, never raises.
"""

from __future__ import annotations

from typing import Final, Protocol

from platterpus.chase_budget import ChaseBudget, read_elapsed_seconds
from platterpus.parsers.rip_log import track_accuraterip_verified
from platterpus.report_types import ChaseAttemptBlock, VerifiedReadChaseBlock


class ChasePlan(Protocol):
    """What a record needs of ``verified_read_chase.ChaseDecision``.

    A protocol, not the class, so this module needs nothing from the decision's
    module, which imports :func:`track_crc` from here.
    """

    @property
    def attempt_limit(self) -> int: ...
    @property
    def distinct_reads_seen(self) -> int | None: ...
    @property
    def outcome(self) -> str: ...
    @property
    def budget(self) -> ChaseBudget | None: ...


#: ``verified_read_chase.stopped_reason`` (schema 45): what ended a chase that
#: kept no read. None when a read was kept, and for a skipped chase.
STOPPED_ATTEMPT_LIMIT: Final[str] = "attempt_limit"
#: Rule 2's budget was spent before the next read could start (TASKS R49).
STOPPED_TIME_BUDGET: Final[str] = "time_budget"
#: The rip was cancelled between or during reads.
STOPPED_CANCELLED: Final[str] = "cancelled"
#: A read could not start (the worker said why), or the loop itself failed.
STOPPED_READ_DID_NOT_START: Final[str] = "read_did_not_start"

#: ``verified_read_chase.after`` (schema 45): the pass whose kept read the chase
#: tried to better. ``securing_pass``: the dynamic or recovery securing pass.
CHASE_AFTER_SECURING_PASS: Final[str] = "securing_pass"
#: ``album_pass``: Archival Exact's ``-Z`` album pass, which no securing pass
#: followed for this track (TASKS R7's open item, round 39).
CHASE_AFTER_ALBUM_PASS: Final[str] = "album_pass"


def track_crc(track: object | None) -> str:
    """A parsed track's EAC CRC32 (its block's), uppercase, or ``""``."""
    if track is None:
        return ""
    return str(getattr(track, "copy_crc", "") or "").strip().upper()


def attempt_block(
    attempt: int,
    track: object | None,
    exit_code: int | None,
    *,
    kept: bool,
    seconds: float | None = None,
    chase_elapsed: float | None = None,
) -> ChaseAttemptBlock:
    """One attempt's record, from the read's own parsed track. Never raises.

    ``seconds`` and ``chase_elapsed`` are the attempt's own wall-clock time and
    the chase's total when it ended, as the loop measured them (schema 45).
    """

    def confidence(name: str) -> int | None:
        value = getattr(getattr(track, name, None), "confidence", None)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    return {
        "attempt": attempt,
        "eac_crc": track_crc(track) or None,
        "accuraterip_verified": bool(track is not None)
        and track_accuraterip_verified(track),
        "accuraterip_v1_confidence": confidence("accuraterip_v1"),
        "accuraterip_v2_confidence": confidence("accuraterip_v2"),
        "exit_code": exit_code,
        "kept": kept,
        "seconds": _rounded(seconds),
        "chase_elapsed_seconds": _rounded(chase_elapsed),
        "read_seconds": _rounded(read_elapsed_seconds(track)),
    }


def chase_block(
    decision: ChasePlan,
    *,
    outcome: str,
    attempts: list[ChaseAttemptBlock],
    kept_attempt: int | None,
    after: str,
    elapsed: float | None,
    stopped_reason: str | None,
) -> VerifiedReadChaseBlock:
    """One track's chase record, run or skipped, with schema 45's budget fields.

    The one builder, so a run chase and a skipped one carry the same keys and
    the budget's inputs sit beside its result. Never raises.
    """
    budget = decision.budget or ChaseBudget(attempt_limit=decision.attempt_limit)
    return {
        "outcome": outcome,
        "attempt_limit": decision.attempt_limit,
        "distinct_reads_seen": decision.distinct_reads_seen,
        "attempts": attempts,
        "kept_attempt": kept_attempt,
        "after": after,
        "attempt_limit_reason": budget.limit_reason,
        "accuraterip_top_confidence": budget.accuraterip_top_confidence,
        "track_seconds": _rounded(budget.track_seconds),
        "album_read_seconds": _rounded(budget.album_read_seconds),
        "time_budget_seconds": _rounded(budget.time_budget_seconds),
        "elapsed_seconds": _rounded(elapsed),
        "stopped_reason": stopped_reason,
        "cache_defeat": budget.cache_defeat,
    }


def skipped_block(
    decision: ChasePlan, after: str = CHASE_AFTER_SECURING_PASS
) -> VerifiedReadChaseBlock:
    """The record of a chase that was considered and not attempted."""
    return chase_block(
        decision,
        outcome=decision.outcome,
        attempts=[],
        kept_attempt=None,
        after=after,
        elapsed=None,
        stopped_reason=None,
    )


def _rounded(value: float | None) -> float | None:
    """Seconds to the hundredth, as cyanrip prints ``Elapsed:``; None stays None."""
    return None if value is None else round(float(value), 2)
