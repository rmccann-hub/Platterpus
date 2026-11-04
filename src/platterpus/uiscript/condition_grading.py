"""One track ripped under several conditions on one build: the pure half (R123).

**Why it exists.** In the owner's Full runs, track 3 of the reference disc read
wrong whenever it was ripped straight after track 2 (section P5's four timed rips
of tracks 1 to 3, and the 0.7.119 run's secure re-read) and right when ripped
alone (section P6, 8 of 8, CRC32 ``59D352DD``). The fork's round 37 lap 7 S11
names what to vary, one thing at a time, with each rip's AccurateRip verdict:
tracks 2 and 3 together against track 3 alone, the read speed, the paranoia
level, and ``--cache-probe`` on every rip so each carries the cache model it read
under. ``rig_scripts/track3abba.txt`` makes those rips; this module counts them.

``compare-accuracy`` (``accuracy_grading.py``) cannot: it compares BUILDS over
the SAME tracks, and here the build is one and the track sets differ on purpose.

**The condition is the label without its trailing digits**: ``pair1`` to
``pair4`` are the condition ``pair``, ``alone1`` to ``alone4`` are ``alone``. The
script names the condition where it makes the rip, so the record cannot be filed
under the wrong one by a separate list.

**A measurement, never a pass or a fail** (``INFO``), like P6. What can be
refused, as not determined, is a comparison that would not mean anything: a log
naming no build, rips from more than one build (the build would then be a second
variable), a named rip without the track, fewer than two conditions, or a rip
AccurateRip gave no answer about, since counting an unknown as "not right" would
score it as a failure.

Pure and Qt-free; every function returns, none raises.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Final

from platterpus.uiscript.accuracy_grading import (
    ANSWERED_STATES,
    STATE_WORDS,
    AccuracyComparison,
    AccuracyRecord,
    TrackAccuracy,
)
from platterpus.verdict import AR_STATE_VERIFIED

#: The highest track number a Red Book CD can have.
MAX_TRACK: Final[int] = 99

#: The label ``cache probe:`` lines are read under, and how much of one is kept.
_CACHE_LABEL: Final[str] = "Cache probe:"
_CACHE_KEEP: Final[int] = 200


def cache_probe_value(text: str) -> str:
    """The value of the log's first ``Cache probe:`` line, or ``""``.

    Read verbatim, as ``rig_check`` surfaces it: the value is a range, a bound or
    an explicit unknown (the parser's reason for leaving it unparsed), so a
    reader gets the fork's own words. Bounded, and an elision is counted.
    """
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(_CACHE_LABEL):
            value = stripped[len(_CACHE_LABEL) :].strip()
            if len(value) > _CACHE_KEEP:
                cut = len(value) - _CACHE_KEEP
                return f"{value[:_CACHE_KEEP]}… ({cut} more characters)"
            return value
    return ""


def condition_of(label: str) -> str:
    """``pair3`` → ``pair``: the label with its trailing digits removed."""
    stem = label.rstrip("0123456789")
    return stem or label


def track_problem(text: str) -> tuple[int | None, str]:
    """The track number in ``text``, or why it is not one (1 to 99)."""
    if not text.isdigit() or not 1 <= int(text) <= MAX_TRACK:
        return None, f"{text!r} is not a track number (1 to {MAX_TRACK})"
    return int(text), ""


def _track(record: AccuracyRecord, number: int) -> TrackAccuracy | None:
    return next((t for t in record.tracks if t.number == number), None)


def _condition_lines(
    number: int, condition: str, rows: Sequence[tuple[AccuracyRecord, TrackAccuracy]]
) -> list[str]:
    """The tally of one condition: right in N of M, its CRC32s, fixups, cache."""
    right = sum(1 for _, t in rows if t.state == AR_STATE_VERIFIED)
    states = Counter(STATE_WORDS.get(t.state, t.state) for _, t in rows)
    labels = ", ".join(r.label for r, _ in rows)
    lines = [
        f"track {number}, {condition}: right in {right} of {len(rows)} rip(s) "
        f"({labels}); " + ", ".join(f"{w} {n}" for w, n in sorted(states.items()))
    ]
    crcs = Counter(t.crc32 or "(none)" for _, t in rows)
    lines.append(
        f"  {len(crcs)} distinct CRC32: "
        + "; ".join(f"{crc} x{n}" for crc, n in sorted(crcs.items()))
    )
    lines.append(
        "  per rip: "
        + "; ".join(
            f"{r.label} {STATE_WORDS.get(t.state, t.state)} {t.crc32 or '(none)'}"
            + ("" if t.fixups is None else f" FIXUP_ATOM {t.fixups}")
            for r, t in rows
        )
    )
    caches = Counter(r.cache or "(no Cache probe: line)" for r, _ in rows)
    lines.append(
        "  cache probe: " + "; ".join(f"{c} x{n}" for c, n in sorted(caches.items()))
    )
    return lines


def compare_conditions(
    number: int, labels: Sequence[str], records: Mapping[str, AccuracyRecord]
) -> AccuracyComparison:
    """Per condition, how many rips of track ``number`` AccurateRip verified."""

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
    unnamed = [r.label for r in chosen if not r.build]
    if unnamed:
        return refuse(f"the log of {', '.join(unnamed)} names no build")
    builds = sorted({r.build for r in chosen})
    if len(builds) > 1:
        return refuse(
            f"the rips came from {len(builds)} builds ({', '.join(builds)}), so the "
            "build would be a second variable; compare-accuracy compares builds"
        )
    missing = [r.label for r in chosen if _track(r, number) is None]
    if missing:
        return refuse(f"{', '.join(missing)} did not rip track {number}")
    groups: dict[str, list[tuple[AccuracyRecord, TrackAccuracy]]] = {}
    for record in chosen:
        track = _track(record, number)
        if track is not None:
            groups.setdefault(condition_of(record.label), []).append((record, track))
    if len(groups) < 2:
        return refuse(
            f"every label names one condition ({', '.join(groups)}); a comparison "
            "needs two"
        )
    lines = [f"build {builds[0]}; conditions in the order first named"]
    for condition, rows in groups.items():
        lines += _condition_lines(number, condition, rows)
    shared = sorted(
        crc
        for crc in {t.crc32 for rows in groups.values() for _, t in rows if t.crc32}
        if sum(any(t.crc32 == crc for _, t in rows) for rows in groups.values()) > 1
    )
    lines.append(
        f"track {number}: CRC32 read under more than one condition: "
        + (", ".join(shared) if shared else "none")
    )
    detail = "\n".join(lines)
    unanswered = [
        f"{r.label} ({STATE_WORDS.get(t.state, t.state)})"
        for rows in groups.values()
        for r, t in rows
        if t.state not in ANSWERED_STATES
    ]
    if unanswered:
        return refuse(
            f"AccurateRip gave no answer about track {number} in "
            + ", ".join(unanswered)
            + "; counting it as not right would score an unknown as a failure",
            detail,
        )
    return AccuracyComparison(True, detail)
