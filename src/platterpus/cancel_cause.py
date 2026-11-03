# SPDX-License-Identifier: GPL-3.0-only
"""Who cancelled a rip, said the same way in the app log, the report and the log.

**Why this exists (TASKS R62; the plan of record, Appendix H §3).** Disc 1 of the
2026-10-21 Full run was cancelled by the acceptance runner, when its six-hour
`wait-for-rip` ran out. The app log said "rip cancel requested by the user" and
the EAC-layout log "the securing pass was INTERRUPTED (you cancelled the rip)"
(``round36full1021bwholedisceac.log:325``, evidence ``08de9851``). Nobody had
pressed anything. Every route that stops a rip goes through the window's one
Cancel (``RipMixin._on_rip_cancel``), so that one place assumed the user, and a
reader of either file was told something false about the run.

**The causes.** Each caller of the Cancel names itself:

* :data:`BY_USER` — the Cancel button, or Force stop pressed by hand;
* :data:`BY_TIME_LIMIT` — a script's ``wait-for-rip`` ran out with the rip still
  reading, so the run ended and cancelled the rip it had started (R49 is the
  per-track budget that would make this rarer);
* :data:`BY_RUN_ENDED` — a script run ended early another way (stopped from the
  console, ``abort``, ``abort-if-failed``) while its rip was reading;
* :data:`BY_SCRIPT_STEP` — a script's own step cancelled it: ``cancel-rip``, or a
  check that stops a rip it says should never have started.

A cancel no caller named is :data:`NOT_RECORDED`, never assumed to be the user:
tri-state, as everywhere else in this project.

Pure, Qt-free, never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypedDict

BY_USER: Final[str] = "user"
BY_TIME_LIMIT: Final[str] = "time_limit"
BY_RUN_ENDED: Final[str] = "run_ended"
BY_SCRIPT_STEP: Final[str] = "script_step"
NOT_RECORDED: Final[str] = "not_recorded"

#: Every value ``cancelled_by.by`` can hold.
CAUSES: Final[frozenset[str]] = frozenset(
    {BY_USER, BY_TIME_LIMIT, BY_RUN_ENDED, BY_SCRIPT_STEP, NOT_RECORDED}
)

#: Who, as the app log's "rip cancel requested by …" line names them.
_WHO: Final[dict[str, str]] = {
    BY_USER: "the user",
    BY_TIME_LIMIT: "the test run, whose time limit for the rip ran out",
    BY_RUN_ENDED: "the test run, which ended while the rip was reading",
    BY_SCRIPT_STEP: "a step of the test script",
    NOT_RECORDED: "a caller that did not say who it was",
}

#: How much of a caller's detail is kept. It is our own text (a step's source
#: line, a run's reason), bounded so a long reason cannot swamp a log line.
_MAX_DETAIL: Final[int] = 240


@dataclass(frozen=True)
class CancelCause:
    """Who cancelled (one of :data:`CAUSES`) and, for a script, which step."""

    by: str
    detail: str = ""


#: The Cancel button and a hand-pressed Force stop.
USER: Final[CancelCause] = CancelCause(BY_USER)


class CancelledByBlock(TypedDict):
    """The report's ``outcome.cancelled_by`` (schema v42)."""

    by: str
    detail: str | None
    sentence: str


def _clean(cause: object) -> CancelCause:
    """A cause we can word: an unknown or malformed one is :data:`NOT_RECORDED`."""
    if not isinstance(cause, CancelCause) or cause.by not in CAUSES:
        return CancelCause(NOT_RECORDED)
    detail = " ".join(str(cause.detail or "").split())
    if len(detail) > _MAX_DETAIL:
        detail = detail[:_MAX_DETAIL] + f"… [{len(detail) - _MAX_DETAIL} more]"
    return CancelCause(cause.by, detail)


def who(cause: object) -> str:
    """``the user``, or the script's role, for the app log's cancel line."""
    clean = _clean(cause)
    said = _WHO[clean.by]
    return f"{said} ({clean.detail})" if clean.detail else said


def sentence(cause: object) -> str:
    """``the user cancelled the rip``, or who else did. Never "you" unless it was."""
    clean = _clean(cause)
    if clean.by == BY_USER:
        return "you cancelled the rip"
    if clean.by == NOT_RECORDED:
        return "the rip was cancelled; who cancelled it was not recorded"
    return f"{who(clean)} cancelled the rip"


def outcome_block(cause: object, *, status: str) -> CancelledByBlock | None:
    """``outcome.cancelled_by``: ``None`` unless the rip's status is cancelled."""
    if status != "cancelled":
        return None
    clean = _clean(cause)
    return {
        "by": clean.by,
        "detail": clean.detail or None,
        "sentence": sentence(clean),
    }


def sentence_from_outcome(outcome: object) -> str:
    """The sentence a report's ``outcome`` carries, or ``""`` when it has none."""
    block = outcome.get("cancelled_by") if isinstance(outcome, dict) else None
    said = block.get("sentence") if isinstance(block, dict) else None
    return said if isinstance(said, str) else ""
