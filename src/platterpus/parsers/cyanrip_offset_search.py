"""Reading ``cyanrip -f``, cyanrip's own drive-offset finder, and deciding what to save.

Two callers read one output through one function (`docs/testing.md` §5.al): the
acceptance run's section O grades the search against the drive's known offset
(`uiscript/probe_grading.py`), and Set up drive measures the offset of a drive
that has none (TASKS R150, PLANNING KDD-50). The reader moved here from
`probe_grading` on 2026-11-25 for that second caller.

**What is saved (KDD-50, the owner's word of 2026-11-25).** Only a FINISHED search
(its own summary line, ``Drive offset of N found (confidence: C)!``), not one cut
short by a stop, in which at least :data:`MIN_AGREEING_TRACKS` tracks agreed, and
whose value Settings would accept. cyanrip's confidence is the count of the disc's
tracks that agreed on one offset; a later track that disagrees resets it to 1
(`cyanrip@52bde2d:src/cyanrip_main.c:1169-1186`). Two tracks agreeing on an exact
sample offset by chance is very unlikely, and the risk more tracks would not
remove (a disc whose AccurateRip entries come from a different pressing) is the
reason the window says the value came from one disc.

The three lines it reads are re-read at the pin the owner rips with, `.35`'s
source as on the fork's branch (`cyanrip@52bde2d:src/cyanrip_main.c:1215`, `:1220`,
`:1231`).

Pure; never raises.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from platterpus.settings_validation import OFFSET_MAX, OFFSET_MIN

#: cyanrip's offset finder's own lines, read in its source
#: (`cyanrip@174a134:src/cyanrip_main.c:594-692`, ``search_for_drive_offset``).
#: Named groups, never columns, so a reworded tail does not move the number read.
#:
#: **The summary is the answer.** The per-track lines (found, confirmed, a new
#: candidate replacing the old) are its working; the search ends by printing
#: ``Drive offset of ±N found (confidence: C)!`` once it has one (line 689), and
#: ``C`` is its own count of the tracks that agreed, so 1 means found once and
#: never confirmed. A run with working and no summary did not finish.
_SUMMARY: Final[re.Pattern[str]] = re.compile(
    r"^Drive offset of (?P<offset>[+-]\d{1,6}) found \(confidence: "
    r"(?P<confidence>\d{1,4})\)!",
    re.M,
)
_CANDIDATE: Final[re.Pattern[str]] = re.compile(
    r"^(?:New offset|Offset) of (?P<offset>[+-]\d{1,6}) (?:found|confirmed)", re.M
)
#: The three ways it ends without an answer (lines 634, 679, 681). NOT
#: ``Was not able to find drive offset with a radius of N frames``: that one is
#: followed by a retry at twice the radius (line 685), so it is working too.
#: ``Stopping, offset finding incomplete!`` is a stop signal cutting the search
#: short, and cyanrip still prints a summary after it if it had a candidate, so
#: a summary beside it is an incomplete search, never a finished one.
_GAVE_UP: Final[re.Pattern[str]] = re.compile(
    r"^(?P<why>No track had AccuRip entry, cannot find offset!"
    r"|No track was long enough, unable to find drive offset!"
    r"|Stopping, offset finding incomplete!)",
    re.M,
)
STOPPED: Final[str] = "Stopping, offset finding incomplete!"


@dataclass(frozen=True)
class FoundOffset:
    """What ``cyanrip -f`` printed about the drive's offset.

    ``offset`` and ``confidence`` are the summary line's when there is one
    (``summarised``); otherwise ``offset`` is the last candidate the working
    named, or ``None``, and ``confidence`` is 0. ``gave_up`` is cyanrip's own
    sentence when it printed one of the three ending lines.
    """

    offset: int | None
    confidence: int
    summarised: bool
    gave_up: str


def parse_found_offset(output: str) -> FoundOffset:
    """Read ``cyanrip -f``'s output. **Never raises**: any input gives an answer."""
    try:
        # A carriage return starts a line as far as a terminal is concerned, and
        # a progress line ending in one must not hide the line written after it.
        text = output.replace("\r", "\n") if isinstance(output, str) else ""
        endings = [m.group("why") for m in _GAVE_UP.finditer(text)]
        why = endings[-1] if endings else ""
        summaries = list(_SUMMARY.finditer(text))
        if summaries:
            last = summaries[-1]
            return FoundOffset(
                int(last.group("offset")), int(last.group("confidence")), True, why
            )
        candidates = list(_CANDIDATE.finditer(text))
        offset = int(candidates[-1].group("offset")) if candidates else None
        return FoundOffset(offset, 0, False, why)
    except (ValueError, TypeError, AttributeError):
        return FoundOffset(None, 0, False, "")


#: The fewest of the disc's tracks that must agree before a found offset is saved
#: (KDD-50). 1 is "found once, never confirmed"; to change the rule, change this
#: and the sentence in :func:`accept`, and the KDD.
MIN_AGREEING_TRACKS: Final[int] = 2


@dataclass(frozen=True)
class OffsetDecision:
    """Whether a search's answer is saved: ``offset`` when it is, else ``None``
    with ``reason``, a sentence for the user that says why and what to do."""

    offset: int | None
    agreeing_tracks: int
    reason: str


def accept(found: FoundOffset) -> OffsetDecision:
    """Decide whether ``found`` is an offset to save (KDD-50). Never raises."""
    if found.gave_up == STOPPED:
        return OffsetDecision(
            None, 0, "the search was stopped before it finished, so nothing is saved"
        )
    if not found.summarised:
        if found.gave_up.startswith("No track had AccuRip entry"):
            return OffsetDecision(
                None,
                0,
                "this disc is not in AccurateRip, so the offset cannot be measured "
                "from it. Try a well-known commercial CD, or enter the offset by "
                "hand",
            )
        if found.gave_up:
            return OffsetDecision(
                None, 0, f"cyanrip could not find it: {found.gave_up}"
            )
        return OffsetDecision(
            None, 0, "cyanrip's search did not finish, so nothing is saved"
        )
    offset = found.offset
    if offset is None or not OFFSET_MIN <= offset <= OFFSET_MAX:
        return OffsetDecision(
            None,
            found.confidence,
            f"cyanrip reported {offset}, outside the range a read offset can be "
            f"({OFFSET_MIN} to {OFFSET_MAX}), so it is not saved",
        )
    if found.confidence < MIN_AGREEING_TRACKS:
        return OffsetDecision(
            None,
            found.confidence,
            f"cyanrip found {offset:+d} on only one track of this disc, which is not "
            "enough to trust it. Try another well-known CD, or enter it by hand if "
            "you know it",
        )
    return OffsetDecision(offset, found.confidence, "")
