# SPDX-License-Identifier: GPL-3.0-only
"""Whether a rip's health may read clean: the two checks behind "No errors occurred".

**Why this module exists** (the owner's known-fixes list of 2026-10-21, item 3).
cyanrip's ``Ripping errors: 0`` becomes the sentence "No errors occurred", and
two things could sit under that sentence unremarked:

* **An error line above the summary.** cyanrip can print one of its own
  diagnostics and still count zero: the fork's round-20 example printed
  ``Error writing trailer: File too large!`` six lines above
  ``Ripping errors: 0``. The parser now keeps every such line
  (``RipLog.ripper_error_lines``, by the same matcher the rip worker uses on the
  live stream), and :func:`error_lines_contradicting_summary` compares the two.
* **A track paranoia could not read cleanly.** A paranoia ``SKIP`` is a read it
  gave up verifying; cyanrip before ``.20`` counted none of them, so a track
  with 2,586 skips (track 18 of the 2026-10-04 rig run) sat under "No errors
  occurred". The rule for which such tracks count is
  :func:`platterpus.verdict.track_has_unverified_skips`; this module turns it into
  the report's ``issues`` entry.

**One function per question, N callers.** The report's ``health_status`` and the
window's status line both ask :func:`effective_health_status`, so the two cannot
call one rip clean and not clean. The EAC-layout log deliberately does NOT: its
disc-level sentence is a surface the cyanrip fork diffs against, so its wording
changes only through the handshake (the proposal is in ``TASKS.md``, for our
round 36 lap).

Pure; no Qt, no I/O; reads with ``getattr`` and never raises.
"""

from __future__ import annotations

from typing import Final

from platterpus.verdict import track_has_unverified_skips

#: The sentence the parser writes for ``Ripping errors: 0``; every reader of
#: health treats exactly this string as clean.
CLEAN_HEALTH: Final[str] = "No errors occurred"

#: ``issues`` code: the ripper printed a diagnostic its own zero count leaves out.
ISSUE_ERROR_LINES_UNDER_ZERO_SUMMARY: Final[str] = (
    "ripper_error_lines_under_zero_summary"
)
#: ``issues`` code: a track paranoia skipped on, that AccurateRip did not confirm.
ISSUE_UNVERIFIED_PARANOIA_SKIPS: Final[str] = "unverified_paranoia_skips"

#: How many of the error lines an ``issues`` message quotes; the rest are counted.
_QUOTED_LINES: Final[int] = 3


def _summary_count_is_zero(rip_log: object) -> bool:
    """True only when the log's ``Ripping errors:`` line was read as exactly 0.

    ``None`` (no summary, or a number we could not read) is not zero: with no
    summary there is nothing for the lines to contradict. ``bool`` is refused
    because ``False == 0`` in Python and a flag is not a count.
    """
    count = getattr(rip_log, "ripping_errors", None)
    return isinstance(count, int) and not isinstance(count, bool) and count == 0


def error_lines_contradicting_summary(rip_log: object) -> tuple[str, ...]:
    """The ripper's diagnostic lines when its own summary says ``Ripping errors: 0``.

    Empty when the summary is absent or non-zero (a non-zero count already reads
    as not clean, so the lines add detail, not a contradiction), and when the log
    held no such line. The tuple is the parser's bounded head-and-tail sample;
    :func:`error_line_count` is the full count. Never raises.
    """
    try:
        if not _summary_count_is_zero(rip_log):
            return ()
        lines = getattr(rip_log, "ripper_error_lines", ()) or ()
        return tuple(str(line) for line in lines if str(line).strip())
    except (TypeError, ValueError):
        return ()


def error_line_count(rip_log: object) -> int:
    """How many diagnostic lines the log held, including any the sample elided."""
    total = getattr(rip_log, "ripper_error_lines_total", 0)
    kept = len(getattr(rip_log, "ripper_error_lines", ()) or ())
    if isinstance(total, int) and not isinstance(total, bool) and total >= kept:
        return total
    return kept


def effective_health_status(rip_log: object) -> str:
    """The rip's health sentence, never "No errors occurred" over an error line.

    The parser's ``health_status`` unchanged, unless the ripper printed a
    diagnostic under a zero summary: then the sentence names the disagreement
    instead of reading clean. A ``health_status`` that is already not clean (an
    encoder failure, say) keeps its words and gains the note. Never raises.
    """
    health = str(getattr(rip_log, "health_status", "") or "")
    if not error_lines_contradicting_summary(rip_log):
        return health
    count = error_line_count(rip_log)
    note = (
        f"the ripper printed {count} error line{'s' if count != 1 else ''} "
        "although its summary reads Ripping errors: 0"
    )
    if health in ("", CLEAN_HEALTH):
        return note
    return f"{health}; {note}"


def unverified_skip_tracks(rip_log: object) -> list[int]:
    """Track numbers paranoia skipped on that AccurateRip did not confirm."""
    numbers: list[int] = []
    for track in getattr(rip_log, "tracks", ()) or ():
        number = getattr(track, "number", None)
        if isinstance(number, int) and track_has_unverified_skips(track):
            numbers.append(number)
    return numbers


def health_findings(rip_log: object) -> list[tuple[str, str, str]]:
    """The report's ``issues`` entries for this module's two checks.

    Each is ``(severity, code, message)``, the shape ``rip_report._issues`` adds.
    Both are warnings: neither proves the audio wrong, and each means the record
    may not call the rip clean. Never raises.
    """
    findings: list[tuple[str, str, str]] = []
    skipped = unverified_skip_tracks(rip_log)
    if skipped:
        listed = ", ".join(str(number) for number in skipped)
        findings.append(
            (
                "warning",
                ISSUE_UNVERIFIED_PARANOIA_SKIPS,
                f"track(s) {listed}: paranoia gave up verifying some reads and kept "
                "what it had, and AccurateRip did not confirm the audio, so the "
                'copy is not confirmed (the EAC-layout log reads "Copy NOT '
                "confirmed\"); the ripper's error count may not include these "
                "skips",
            )
        )
    lines = error_lines_contradicting_summary(rip_log)
    if lines:
        count = error_line_count(rip_log)
        quoted = "; ".join(f'"{line.strip()}"' for line in lines[:_QUOTED_LINES])
        more = count - min(len(lines), _QUOTED_LINES)
        tail = f" and {more} more (see the ripper's log)" if more > 0 else ""
        findings.append(
            (
                "warning",
                ISSUE_ERROR_LINES_UNDER_ZERO_SUMMARY,
                f"the ripper printed {quoted}{tail}, yet its own summary reads "
                "Ripping errors: 0. The two disagree, so this rip's health is not "
                "reported as clean",
            )
        )
    return findings
