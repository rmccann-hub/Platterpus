# SPDX-License-Identifier: GPL-3.0-only
"""The words for per-track CTDB results: one sentence and one table, shared.

The verdict's message, the results pane and ``--ctdb-calibrate`` all describe the
same :class:`~platterpus.ctdb.matching.CtdbTrackResult` rows, so they read them
through these two functions and cannot describe one track two ways. Split from
``matching.py`` (which decides the results) on 2026-10-21, because wording and
deciding are separate jobs and the pair crossed the module-size heuristic.
"""

from __future__ import annotations

from collections.abc import Sequence

from platterpus.ctdb.matching import CtdbTrackResult, TrackVerdict


def _track_list(numbers: Sequence[int]) -> str:
    """ "track 3", "tracks 3 and 7", "tracks 3, 5 and 7"."""
    if len(numbers) == 1:
        return f"track {numbers[0]}"
    head = ", ".join(str(n) for n in numbers[:-1])
    return f"tracks {head} and {numbers[-1]}"


def per_track_sentence(tracks: Sequence[CtdbTrackResult], total: int) -> str:
    """The one wording for the per-track results, shared by the verdict and the screen.

    Empty when no per-track result exists (the check did not get that far).
    ``total`` is every submission for the disc, the denominator EAC prints.
    """
    if not tracks:
        return ""
    count = len(tracks)
    undetermined = [t.track for t in tracks if t.verdict is TrackVerdict.NOT_DETERMINED]
    if len(undetermined) == count:
        return f"Per track: not determined ({tracks[0].reason})."
    agree = [t for t in tracks if t.verdict is TrackVerdict.MATCH and not t.outvoted]
    minority = [t for t in tracks if t.outvoted]
    differs = [t.track for t in tracks if t.verdict is TrackVerdict.DIFFERS]
    parts = [f"Per track: {len(agree)} of {count} agree with CTDB"]
    if differs:
        verb = "differs" if len(differs) == 1 else "differ"
        parts.append(f"{_track_list(differs)} {verb} from every entry")
    for track in minority:
        parts.append(
            f"track {track.track} agrees only with a minority "
            f"({track.confidence:,} of {total:,} submissions)"
        )
    if undetermined:
        parts.append(f"{_track_list(undetermined)} not determined")
    return "; ".join(parts) + "."


def per_track_lines(tracks: Sequence[CtdbTrackResult], total: int) -> list[str]:
    """One line per track for ``--ctdb-calibrate`` and the diagnostics, in our words.

    Laid out like EAC's ``Track | CTDB Status`` table so the two can be read side
    by side, but worded as ours: "agree" rather than EAC's "Accurately ripped",
    because this is not EAC's plugin and does not count what it counts (it has
    no repair-based localisation, see the module docstring).
    """
    lines: list[str] = []
    for track in tracks:
        if track.verdict is TrackVerdict.MATCH:
            text = f"({track.confidence:,}/{total:,}) agree"
            if track.offset:
                text += f" at offset {track.offset:+d}"
            if track.outvoted:
                text += f", a minority: {track.disagreeing_confidence:,} disagree"
        elif track.verdict is TrackVerdict.DIFFERS:
            text = (
                f"differs from every entry "
                f"({track.disagreeing_confidence:,}/{total:,} disagree)"
            )
        else:
            text = f"not determined ({track.reason})"
        lines.append(f" {track.track:2d}   | {text}")
    return lines
