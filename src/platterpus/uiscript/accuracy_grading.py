"""Paired rips of one track on two cyanrip builds: the pure half (section P6).

**Why it exists.** On the 2026-10-21 Full run, track 3 of the reference disc
verified with AccurateRip in both of P5's timed rips on ``.25`` and in neither on
``.26``, though P5 already alternated the builds. The fork's round 36 lap 8 S8:
*"Two rips a side cannot separate the build from the disc."* The owner's word
(2026-10-26): *"add paired .25/.26 rips of track 3 to the Full run."* Section P6
rips the one track several times on each build, and this module says, per build
and per track, how many of those rips AccurateRip verified and which CRCs they
read.

**A measurement, never a pass or a fail** (``docs/testing.md``, Acceptance
severity, P6). A build that misreads a track is a finding for the fork, not a
defect of this rip. What can be refused is a comparison that would not mean
anything: a record whose log names no build, records over different tracks, only
one build among them, or a rip AccurateRip gave no answer about, since counting
an unknown as "not right" would score it as a failure. Those are "not
determined", which is not an answer.

**Nothing here decides what "verified" means.** Each track's state is
:func:`platterpus.verdict.track_accuraterip_state`, the one summary of the
verdict's per-column classifier, and the confidence text is
:func:`platterpus.verdict.accuraterip_confidence_text`. The log is read through
the cyanrip parser (``RipLog``), whose never-raises property test covers the text.

Pure and Qt-free; every function returns, none raises. The verbs that call it are
``uiscript/accuracy_verbs.py``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from platterpus.data_tracks import is_data_track
from platterpus.parsers.rip_log import RipLog, accuraterip_is_match
from platterpus.uiscript.timing_grading import label_problem as _label_problem
from platterpus.verdict import (
    AR_STATE_ABSENT,
    AR_STATE_NO_DATA,
    AR_STATE_NO_MATCH,
    AR_STATE_NOT_CHECKED,
    AR_STATE_OFFSET_VARIANT,
    AR_STATE_VERIFIED,
    accuraterip_confidence_text,
    track_accuraterip_state,
)

#: How each AccurateRip state reads in the transcript. Every state the verdict
#: can return has a distinct phrase, so no two collapse into one in a tally.
STATE_WORDS: Final[dict[str, str]] = {
    AR_STATE_VERIFIED: "verified",
    AR_STATE_OFFSET_VARIANT: "frame 450 only",
    AR_STATE_NO_MATCH: "mismatch",
    AR_STATE_ABSENT: "not in database",
    AR_STATE_NOT_CHECKED: "no lookup",
    AR_STATE_NO_DATA: "no result",
}

#: The states in which AccurateRip answered about THIS read of THIS track. Only
#: these can be counted as right or not right; the other three say nothing about
#: the read (the disc is not in the database, no lookup ran, or it left nothing).
ANSWERED_STATES: Final[frozenset[str]] = frozenset(
    {AR_STATE_VERIFIED, AR_STATE_OFFSET_VARIANT, AR_STATE_NO_MATCH}
)


def label_problem(label: str) -> str:
    """Why ``label`` cannot name an accuracy record, or ``""`` when it can."""
    return _label_problem(label, "an accuracy record")


@dataclass(frozen=True)
class TrackAccuracy:
    """One track of one rip: its AccurateRip state, CRC32 and read speed."""

    number: int
    #: One of the verdict's ``AR_STATES``.
    state: str
    #: ``"128 of 200"`` for a match (whole-track or frame 450); ``""`` otherwise.
    confidence: str = ""
    #: The ripper's EAC CRC32 of the track, upper-case hex; ``""`` when absent.
    crc32: str = ""
    #: ``Extraction speed:`` in X; ``None`` when the log printed none.
    speed: float | None = None

    def describe(self) -> str:
        """``track 3: verified (128 of 200), CRC32 59D352DD, 0.96x``."""
        words = STATE_WORDS.get(self.state, self.state)
        if self.confidence:
            words += f" ({self.confidence})"
        crc = self.crc32 or "(none)"
        speed = f"{self.speed:.2f}x" if self.speed is not None else "speed (none)"
        return f"track {self.number}: {words}, CRC32 {crc}, {speed}"


@dataclass(frozen=True)
class AccuracyRecord:
    """One rip's per-track AccurateRip outcome, and the build its log names.

    ``build`` is the log's own banner parenthetical (``RipLog.ripper_build``), so
    the record names the binary from the artifact rather than from what the
    script believed it had installed.
    """

    label: str
    build: str
    tracks: tuple[TrackAccuracy, ...] = ()
    source: str = ""

    @property
    def track_numbers(self) -> tuple[int, ...]:
        """The tracks this rip read, in order."""
        return tuple(sorted(t.number for t in self.tracks))

    def describe(self) -> str:
        """One transcript paragraph: the build, then one line per track."""
        lines = [
            f"accuracy {self.label}: build {self.build or '(not determined)'}; "
            f"{len(self.tracks)} audio track(s)"
        ]
        lines += [f"  {t.describe()}" for t in self.tracks]
        if not self.tracks:
            lines.append("  the log holds no audio track")
        if self.source:
            lines.append(f"  from {self.source}")
        return "\n".join(lines)


def _confidence(track: object, state: str) -> str:
    """The confidence text of whichever result made ``state`` a match."""
    lookup = getattr(track, "accuraterip_lookup", None)
    if state == AR_STATE_VERIFIED:
        matches = [
            r
            for r in (
                getattr(track, "accuraterip_v1", None),
                getattr(track, "accuraterip_v2", None),
            )
            if accuraterip_is_match(r)
        ]
        best = max(matches, key=lambda r: getattr(r, "confidence", 0) or 0)
        return accuraterip_confidence_text(best, lookup)
    if state == AR_STATE_OFFSET_VARIANT:
        offset = getattr(track, "accuraterip_offset", None)
        return accuraterip_confidence_text(offset, lookup)
    return ""


def accuracy_from_log(label: str, log: RipLog, source: str = "") -> AccuracyRecord:
    """An :class:`AccuracyRecord` from a parsed rip log. Never raises.

    Data tracks are left out: AccurateRip has nothing to say about them, and a
    comparison of audio must not count one.
    """
    tracks: list[TrackAccuracy] = []
    for track in log.tracks:
        if is_data_track(track):
            continue
        state = track_accuraterip_state(track)
        tracks.append(
            TrackAccuracy(
                number=track.number,
                state=state,
                confidence=_confidence(track, state),
                crc32=(track.copy_crc or "").strip().upper(),
                speed=track.extraction_speed,
            )
        )
    return AccuracyRecord(
        label=label,
        build=(log.ripper_build or "").strip(),
        tracks=tuple(tracks),
        source=source,
    )


@dataclass(frozen=True)
class AccuracyComparison:
    """Per build, per track: right in N of M rips. Tri-state.

    ``determined`` is False when the comparison could not be made; ``refusal``
    then says why, and ``detail`` still carries every tally that could be
    counted, so the transcript keeps the data even when the grade is red.
    """

    determined: bool
    detail: str
    refusal: str = ""


def _tally_lines(builds: Sequence[str], records: Sequence[AccuracyRecord]) -> list[str]:
    """One line per build per track, then the CRCs more than one build read."""
    lines: list[str] = []
    numbers = records[0].track_numbers
    for number in numbers:
        crc_builds: dict[str, set[str]] = {}
        for build in builds:
            rows = [
                (r.label, t)
                for r in records
                if r.build == build
                for t in r.tracks
                if t.number == number
            ]
            right = sum(1 for _, t in rows if t.state == AR_STATE_VERIFIED)
            states = Counter(STATE_WORDS.get(t.state, t.state) for _, t in rows)
            crcs: dict[str, Counter[str]] = {}
            for _, t in rows:
                crc = t.crc32 or "(none)"
                crcs.setdefault(crc, Counter())[STATE_WORDS.get(t.state, t.state)] += 1
                crc_builds.setdefault(crc, set()).add(build)
            lines.append(
                f"track {number}, {build}: right in {right} of {len(rows)} rip(s) "
                f"({', '.join(label for label, _ in rows)}); "
                + ", ".join(f"{word} {n}" for word, n in sorted(states.items()))
            )
            lines.append(
                f"  {len(crcs)} distinct CRC32: "
                + "; ".join(
                    f"{crc} x{sum(c.values())} ("
                    + ", ".join(f"{w} {n}" for w, n in sorted(c.items()))
                    + ")"
                    for crc, c in sorted(crcs.items())
                )
            )
        shared = sorted(crc for crc, seen in crc_builds.items() if len(seen) > 1)
        lines.append(
            f"track {number}: CRC32 read under more than one build: "
            + (", ".join(shared) if shared else "none")
        )
    return lines


def compare_accuracy(
    labels: Sequence[str], records: Mapping[str, AccuracyRecord]
) -> AccuracyComparison:
    """Per build and per track, how many rips AccurateRip verified. Never raises.

    Refuses (not determined) when fewer than two labels are named or one is named
    twice, a label has no record, a record names no build or holds no audio
    track, the records cover different tracks, they name fewer than two builds,
    or any named rip has a track AccurateRip gave no answer about.
    """

    def refuse(why: str, detail: str = "") -> AccuracyComparison:
        return AccuracyComparison(False, detail, f"not determined: {why}")

    if len(labels) < 2:
        return refuse(f"a comparison needs two labels or more, got {len(labels)}")
    repeated = sorted(label for label, n in Counter(labels).items() if n > 1)
    if repeated:
        return refuse(f"{', '.join(repeated)} named more than once")
    absent = [label for label in labels if label not in records]
    if absent:
        return refuse(f"no accuracy has been recorded as {', '.join(absent)}")
    chosen = [records[label] for label in labels]
    for record in chosen:
        if not record.build:
            return refuse(
                f"accuracy {record.label}'s log names no build, so what it "
                "measured cannot be said"
            )
        if not record.tracks:
            return refuse(f"accuracy {record.label}'s log holds no audio track")
    first = chosen[0]
    for record in chosen[1:]:
        if record.track_numbers != first.track_numbers:
            return refuse(
                f"the track sets differ ({first.label}: {list(first.track_numbers)}, "
                f"{record.label}: {list(record.track_numbers)}), so the rips read "
                "different audio"
            )
    builds = list(dict.fromkeys(r.build for r in chosen))
    if len(builds) < 2:
        return refuse(
            f"every rip named came from {builds[0]}; a comparison between builds "
            "needs two"
        )
    detail = "\n".join(_tally_lines(builds, chosen))
    unanswered = [
        f"{r.label} track {t.number} ({STATE_WORDS.get(t.state, t.state)})"
        for r in chosen
        for t in r.tracks
        if t.state not in ANSWERED_STATES
    ]
    if unanswered:
        return refuse(
            "AccurateRip gave no answer about "
            + ", ".join(unanswered)
            + "; counting it as not right would score an unknown as a failure",
            detail,
        )
    return AccuracyComparison(True, detail)
