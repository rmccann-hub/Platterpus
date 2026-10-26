"""Do the rips of one disc in one run agree about where its pregaps are? (R10)

**Why this exists.** On the 2026-10-13 Full run the secure re-read's log left
track 4's 158-frame pregap out of its ``Gaps:`` list (and its cue sheet had no
``INDEX 00`` for it), while the whole-disc rip of the SAME disc, an hour
earlier on the same drive, listed it (``docs/handshake/artifactsround32/``:
``round32fullsecurereread.log`` lines 42-50 against ``round32fullwholedisc.log``
line 44). The same run's logs also disagree about track 9: 95 frames in some,
94 in others. The fork caught it (their round 32 lap 9, S4); our reading of the
run did not, because **nothing compared two rips of one disc within one run**.
Every grader we had looked at one rip at a time, and a single log that omits a
pregap looks exactly like a disc without one.

**What it compares, and why that list.** cyanrip's ``Gaps:`` block is a
statement about the WHOLE disc, printed whatever ``-l`` selected: a two-track rip
still lists every pregap it found. The per-track ``Pregap length:`` rows exist
only for the tracks that rip read, so they could not compare a two-track rip
with a whole-disc one. One line per gap, in the shape every committed log has::

    158 frame pregap in track 4, merging into track 3

A track the block does not name has no pregap, and ``0 frame pregap in track 1,
unmerged`` says the same thing out loud, so both read as 0. Only the FRAME
COUNT is compared: whether a gap is merged into the previous track is a setting
(``-G``), not something read off the disc.

**A pregap the log calls unknown is a reading, and it disagrees with a number.**
From ``.22`` the block can say ``pregap of track 9 unknown (sub-channel CRC
mismatches)``. Until 2026-10-26 that line made the whole list unreadable, so the
log was set aside, and on the fork's round 36 runs of the reference disc the
check compared three logs, called them identical, and set aside the three that
said track 9 was unknown (their round 36 lap 8 S11). A log that cannot tell a
pregap disagrees with one that gives it a value; that is the disagreement this
check exists to report. Such a track reads as unknown, and the detail names the
log's reason and, where the log carries ``.27``'s ``Pregap search:`` line for
that track, what the search saw (:func:`platterpus.pregap_search.describe`).

**Who is "the same disc".** The MusicBrainz Disc ID on cyanrip's ``DiscID:``
line: computed from the disc's table of contents, so it names the physical disc
and not the release, which is the same key ``rip_compare.same_disc`` tries first.
A log without one cannot be grouped and is named, never guessed into a group.

**What the answer is, and what it is NOT.** Three states, never two:

* **agree** — every disc with two or more readable lists had identical ones;
* **differ** — at least one track's pregap differs between rips of one disc,
  and every such track is named, with which logs said what;
* **not determined** — no disc had two readable lists, so nothing was compared.
  This is the floor: a comparison of one log with nothing agrees with itself,
  and reporting that as "agree" would be a check satisfied by finding nothing.

Disagreement cannot say WHICH log is right: there is no third witness in a log,
only two readings of one sub-channel. Nor does it move a sample: cyanrip merges
a pregap into the end of the previous track, so the track files are cut at the
same boundaries either way, and on the filed run tracks 4, 8 and 9 carry the
same CRC and the same AccurateRip match in both rips (the logs above, their
track blocks). What differs is the cue sheet and the log's line. Those are why
the acceptance verb that calls this gathers rather than fails (``pregap_verbs``;
the severity argument is in ``docs/testing.md`` → *Acceptance severity*, row P4).

Pure and Qt-free, and **never raises**: every reading of an external log goes
through :func:`read_gap_list`, which answers "not determined, because …" for
anything it does not recognise.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.pregap_search import describe as describe_search
from platterpus.safe_int import int_or_none

#: The floor: how many readable lists of one disc a comparison needs.
MIN_LOGS_PER_DISC: Final[int] = 2

#: One line of cyanrip's ``Gaps:`` block, as every committed log spells it. The
#: tail after the comma (``merging into track 3`` / ``unmerged``) is a setting
#: and is not compared. Bounded digit counts: a 99-track disc and a pregap of a
#: few minutes both fit, and an absurd number is "not recognised", not a gap.
_GAP_LINE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<frames>\d{1,7}) frames? pregap in track (?P<track>\d{1,3})(?:,\s*\S.*)?$"
)

#: The fork's line for a pregap its sub-channel search could not tell
#: (``pregap of track 9 unknown (sub-channel CRC mismatches)``, ``.22`` onward).
#: The reason is optional and bounded; a reason we do not know is still a reason.
_UNKNOWN_LINE: Final[re.Pattern[str]] = re.compile(
    r"^pregap of track (?P<track>\d{1,3}) unknown(?: \((?P<reason>[^()]{1,120})\))?$"
)

#: Stock cyanrip 0.9.3's whole ``Gaps:`` block when there are none.
_NONE_SIGNALLED: Final[str] = "None signalled"

#: How the parser joins the block's lines into ``RippingInfo.gap_detection``
#: (``parsers.cyanrip_log``: ``"; ".join(gap_lines)``). A fragment that is not a
#: gap line makes the whole list "not determined", so a value that ever contains
#: this separator fails safe rather than being read as two gaps.
_JOINED_BY: Final[str] = "; "

#: How much of a Disc ID the transcript quotes. A real one is 28 characters; the
#: value comes from a file, so it is bounded rather than trusted.
_DISC_ID_SHOWN: Final[int] = 40


@dataclass(frozen=True)
class GapReading:
    """One log's pregap list, or why it has none we can use.

    ``pregaps`` maps track number to frames for every track with a non-zero
    pregap, and to ``None`` for a track the log says is UNKNOWN; ``pregaps``
    itself being ``None`` means NOT DETERMINED, never "no pregaps", and
    ``problem`` then says why. ``unknown_notes`` says, per unknown track, the
    log's reason and what its sub-channel search saw. ``disc_id`` is ``""`` when
    the log names no disc.
    """

    label: str
    disc_id: str
    pregaps: Mapping[int, int | None] | None
    problem: str = ""
    unknown_notes: Mapping[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TrackDifference:
    """One track whose pregap differs between rips of one disc.

    ``readings`` pairs each frame count that was read with the logs that read
    it, largest first, so "158 frames in ten logs, 0 in one" reads in that order;
    ``None`` is "the log says unknown", and comes last. ``notes`` pairs each log
    that read unknown with what it said about why.
    """

    disc_id: str
    track: int
    readings: tuple[tuple[int | None, tuple[str, ...]], ...]
    notes: tuple[tuple[str, str], ...] = ()


#: The three answers :func:`compare` gives.
AGREE: Final[str] = "agree"
DIFFER: Final[str] = "differ"
NOT_DETERMINED: Final[str] = "not determined"


@dataclass(frozen=True)
class PregapComparison:
    """The answer for a whole run: :data:`AGREE`, :data:`DIFFER` or
    :data:`NOT_DETERMINED`, the tracks that differ, and the sentence that says it.

    ``compared`` counts the logs that took part in a comparison (two or more of
    one disc); ``set_aside`` names every log that did not, with the reason, so
    the floor's arithmetic is visible rather than asserted.
    """

    state: str
    detail: str
    differences: tuple[TrackDifference, ...] = ()
    compared: int = 0
    set_aside: tuple[str, ...] = field(default_factory=tuple)

    @property
    def differing_tracks(self) -> tuple[int, ...]:
        """Every track named as differing, in order, each once."""
        return tuple(sorted({d.track for d in self.differences}))


def parse_gap_lines(joined: str) -> tuple[dict[int, int | None] | None, str]:
    """``(track -> frames, "")`` from the parser's joined ``Gaps:`` value, or
    ``(None, why not)``. Pure; never raises.

    Zero-frame entries are dropped, because the block's silence about a track
    already says 0. A track the block calls unknown maps to ``None``. A track
    named twice with two different answers is not recognised: the log
    contradicts itself, and picking one would be a guess.
    """
    pregaps, _reasons, problem = _read_gap_lines(joined)
    return pregaps, problem


def _read_gap_lines(
    joined: str,
) -> tuple[dict[int, int | None] | None, dict[int, str], str]:
    """:func:`parse_gap_lines`, with each unknown track's reason beside it."""
    text = (joined or "").strip()
    if not text:
        return None, {}, "the log has no Gaps: block"
    if text == _NONE_SIGNALLED:
        return {}, {}, ""
    pregaps: dict[int, int | None] = {}
    reasons: dict[int, str] = {}
    for fragment in text.split(_JOINED_BY):
        unknown = _UNKNOWN_LINE.match(fragment.strip())
        if unknown is not None:
            track_said = int_or_none(unknown.group("track"), field="Gaps: track")
            if track_said is None:
                return (
                    None,
                    {},
                    "its Gaps: block has a number this check could not read",
                )
            if track_said in pregaps and pregaps[track_said] is not None:
                return None, {}, f"its Gaps: block names track {track_said} twice"
            pregaps[track_said] = None
            reasons[track_said] = unknown.group("reason") or "no reason given"
            continue
        match = _GAP_LINE.match(fragment.strip())
        if match is None:
            shown = fragment.strip()[:80]
            return (
                None,
                {},
                f"its Gaps: block has a line this check does not read: {shown!r}",
            )
        # Through the shared guard, like every parser of external text (the
        # never-raises sweep in `tests/test_never_raises_contract.py`). The regex
        # already bounds both to a few digits; the guard is what keeps that true
        # if the regex is ever widened.
        track = int_or_none(match.group("track"), field="Gaps: track")
        frames = int_or_none(match.group("frames"), field="Gaps: frames")
        if track is None or frames is None:
            return None, {}, "its Gaps: block has a number this check could not read"
        if frames == 0:
            if pregaps.get(track, 0) != 0:
                return None, {}, f"its Gaps: block names track {track} twice"
            continue
        if track in pregaps and pregaps[track] != frames:
            return None, {}, f"its Gaps: block names track {track} twice"
        pregaps[track] = frames
    return pregaps, reasons, ""


def read_gap_list(text: str, label: str) -> GapReading:
    """One cyanrip log's Disc ID and pregap list. Pure; never raises.

    Reads through the product's own log parser, so this check and every other
    reader of a cyanrip log agree about what the ``Gaps:`` block and the
    ``DiscID:`` line say (``CLAUDE.md``: one predicate, many callers).
    """
    try:
        if not looks_like_cyanrip_log(text):
            return GapReading(label, "", None, "it is not a log cyanrip wrote")
        parsed = parse_cyanrip_log(text)
    except Exception as exc:  # noqa: BLE001 — a grader of external text never raises
        return GapReading(label, "", None, f"its log could not be parsed ({exc!r})")
    disc_id = (parsed.disc_id or "").strip()
    pregaps, reasons, problem = _read_gap_lines(parsed.ripping_info.gap_detection)
    # Each unknown track's reason, and what `.27`'s search saw on that track when
    # this rip read it (a track block exists only for a track the rip read).
    searches = {
        getattr(t, "number", None): getattr(t, "pregap_search", None)
        for t in parsed.tracks
    }
    notes = {
        track: "; ".join(
            part for part in (reason, describe_search(searches.get(track))) if part
        )
        for track, reason in reasons.items()
    }
    if not disc_id:
        return GapReading(
            label,
            "",
            pregaps,
            "it names no Disc ID, so its disc is unknown",
            unknown_notes=notes,
        )
    return GapReading(label, disc_id, pregaps, problem, unknown_notes=notes)


def _frames(value: int | None) -> str:
    if value is None:
        return "unknown"
    return "none" if value == 0 else f"{value} frame{'s' if value != 1 else ''}"


def _largest_first(item: tuple[int | None, list[str]]) -> tuple[bool, int]:
    """Sort key: frame counts largest first, then "unknown" last."""
    value = item[0]
    return (value is None, -(value or 0))


def _quoted(labels: Sequence[str]) -> str:
    return ", ".join(f"'{label}'" for label in labels)


def _short(disc_id: str) -> str:
    return disc_id if len(disc_id) <= _DISC_ID_SHOWN else disc_id[:_DISC_ID_SHOWN] + "…"


def compare(readings: Sequence[GapReading]) -> PregapComparison:
    """Compare every disc's pregap lists across the run. Pure; never raises.

    A disc is compared only when :data:`MIN_LOGS_PER_DISC` of its logs have a
    determined list; a disc with fewer is named as not compared. When no disc
    reaches the floor the answer is :data:`NOT_DETERMINED`, never :data:`AGREE`.
    """
    set_aside: list[str] = []
    by_disc: dict[str, list[GapReading]] = {}
    for reading in readings:
        if reading.pregaps is None or not reading.disc_id:
            set_aside.append(f"'{reading.label}': {reading.problem or 'no reading'}")
            continue
        by_disc.setdefault(reading.disc_id, []).append(reading)

    differences: list[TrackDifference] = []
    compared = 0
    disc_lines: list[str] = []
    for disc_id, group in by_disc.items():
        if len(group) < MIN_LOGS_PER_DISC:
            set_aside.append(
                f"'{group[0].label}': the only readable log of disc "
                f"{_short(disc_id)}, so there is nothing to compare it with"
            )
            continue
        compared += len(group)
        tracks = sorted({t for r in group for t in (r.pregaps or {})})
        found_here = 0
        for track in tracks:
            seen: dict[int | None, list[str]] = {}
            notes: list[tuple[str, str]] = []
            for reading in group:
                value = (reading.pregaps or {}).get(track, 0)
                seen.setdefault(value, []).append(reading.label)
                if value is None:
                    notes.append(
                        (
                            reading.label,
                            reading.unknown_notes.get(track, "") or "no reason given",
                        )
                    )
            if len(seen) < 2:
                continue
            found_here += 1
            differences.append(
                TrackDifference(
                    disc_id,
                    track,
                    tuple(
                        (frames, tuple(labels))
                        for frames, labels in sorted(seen.items(), key=_largest_first)
                    ),
                    tuple(notes),
                )
            )
        verdict = f"{found_here} track(s) differ" if found_here else "identical"
        disc_lines.append(
            f"disc {_short(disc_id)}: {len(group)} logs compared, {verdict}"
        )

    aside = (
        [f"set aside ({len(set_aside)}): " + "; ".join(set_aside)] if set_aside else []
    )
    if not compared:
        return PregapComparison(
            NOT_DETERMINED,
            "\n".join(
                [
                    f"not determined: {len(readings)} cyanrip log(s) from this run "
                    f"were read, and no disc had {MIN_LOGS_PER_DISC} or more with a "
                    "readable Gaps: list, so no two rips were compared. A list "
                    "compared with nothing agrees with itself, so this is not a pass.",
                    *aside,
                ]
            ),
            compared=0,
            set_aside=tuple(set_aside),
        )

    if not differences:
        return PregapComparison(
            AGREE,
            "\n".join(
                [
                    f"✓ the pregap lists agree: {compared} log(s) compared",
                    *disc_lines,
                    *aside,
                ]
            ),
            compared=compared,
            set_aside=tuple(set_aside),
        )

    track_lines = []
    for diff in differences:
        said = "; ".join(
            f"{_frames(frames)} in {_quoted(labels)}"
            for frames, labels in diff.readings
        )
        track_lines.append(f"track {diff.track} (disc {_short(diff.disc_id)}): {said}")
        # Why each log could not tell: its reason, and what the search saw, so
        # a run can tell reads that failed the CRC from misplaced frames.
        track_lines.extend(
            f"  '{label}' says unknown: {note}" for label, note in diff.notes
        )
    named = ", ".join(str(t) for t in sorted({d.track for d in differences}))
    return PregapComparison(
        DIFFER,
        "\n".join(
            [
                f"⚠ the pregap lists DIFFER between rips of one disc, at track(s) "
                f"{named}: {compared} log(s) compared",
                *track_lines,
                *disc_lines,
                *aside,
                "Gathered, not graded: cyanrip's sub-channel pregap reading varied "
                "between reads of one disc (the fork's `subchannel-pregap-varies`). "
                "The track files are cut at the same boundaries either way, because "
                "a merged pregap stays at the end of the previous track; what "
                "differs is the cue sheet's INDEX 00 and the log's Gaps: line, and "
                "nothing here can say which reading is right.",
            ]
        ),
        differences=tuple(differences),
        compared=compared,
        set_aside=tuple(set_aside),
    )
