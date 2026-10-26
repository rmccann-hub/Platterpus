"""Timed rips compared across two cyanrip builds: the pure half (round 36 S15).

**What this measures, and what it does not.** The owner asked for a timed rip
comparing two fork builds, and the fork's round 36 lap 1 S15 proposed the method:
the same tracks of the reference disc, ripped with the same settings on each
build, alternating builds twice (A, B, A, B) so drive warm-up favours neither,
each track's ``Elapsed:`` line read from its log. The comparison is the ratio of
B's summed ``Elapsed:`` to A's over the same tracks, once per pair, and the two
pairs **agree** when their ratios are within :data:`AGREEMENT_TOLERANCE`.

It is a **measurement, never a pass or a fail**: a slower build is a finding for
the fork, not a defect in this rip, so every grade here is gathered (``INFO``).
What it can refuse is a comparison that would not mean anything — the track sets
differ, a track has no ``Elapsed:`` line, the two records came from one build or
from a build nobody could name, or one track was read more times in one record
than in the other. Those are "not determined", which is not an answer.

**No new parser.** The ``Elapsed:`` line is already read by the cyanrip log
parser into ``TrackResult.extraction_elapsed_seconds`` (``parsers/cyanrip_log.py``,
``_TRACK_ELAPSED_SECONDS``, with its never-raises property test). This module
reads that field off a parsed :class:`~platterpus.parsers.rip_log.RipLog`, so the
one parser of cyanrip's text stays the only one.

Pure and Qt-free; every function returns, none raises. The verbs that call it are
``uiscript/timing_verbs.py``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Final

from platterpus.parsers.rip_log import RipLog

#: How close the two pairs' ratios must be to call the comparison done. The
#: fork's S15 wording: *"the ratio … within 0.05 of each other"*.
AGREEMENT_TOLERANCE: Final[float] = 0.05

#: A label as a script may type it: short, and nothing a transcript or a JSON
#: key could misread. Validated at the boundary (``CLAUDE.md``: inputs are
#: validated for character set and length by a pure function).
_LABEL_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")


def label_problem(label: str, what: str = "a timing") -> str:
    """Why ``label`` cannot name ``what`` (a timing, by default), or ``""``.

    ``what`` lets the accuracy verbs (``accuracy_grading.py``) share the one rule
    for a script's labels rather than keep a second copy of it.
    """
    if _LABEL_RE.match(label or ""):
        return ""
    return f"{label!r} cannot name {what}: use 1 to 32 letters, digits, '_', '.' or '-'"


@dataclass(frozen=True)
class TimingRecord:
    """One rip's per-track ``Elapsed:`` seconds, and which build produced them.

    ``build`` is the log's own banner parenthetical (``RipLog.ripper_build``), so
    the record says which binary it measured from the artifact itself rather than
    from what the script believed it had installed.
    """

    label: str
    build: str
    #: ``{track number: elapsed seconds}`` for every track that printed one.
    seconds: dict[int, float] = field(default_factory=dict)
    #: Tracks the log holds with NO usable ``Elapsed:`` line, in order.
    missing: tuple[int, ...] = ()
    #: ``{track number: reads}`` where the log states how many times it read the
    #: track (``-Z`` re-reads). An ``Elapsed:`` covers every read of its track.
    reads: dict[int, int] = field(default_factory=dict)
    #: The log file it was read from, for the transcript.
    source: str = ""

    @property
    def complete(self) -> bool:
        """True when every track in the log has a timing, and there is one."""
        return bool(self.seconds) and not self.missing

    def total(self, tracks: tuple[int, ...]) -> float:
        """The summed seconds over ``tracks`` (every one must be present)."""
        return math.fsum(self.seconds[n] for n in tracks)

    def describe(self) -> str:
        """One transcript paragraph: the build, each track, the sum."""
        per_track = ", ".join(
            f"track {n} {self.seconds[n]:.2f} s" for n in sorted(self.seconds)
        )
        lines = [
            f"timing {self.label}: build {self.build or '(not determined)'}; "
            f"{len(self.seconds)} track(s) timed, summed "
            f"{math.fsum(self.seconds.values()):.2f} s",
            f"  {per_track}" if per_track else "  no track printed an Elapsed: line",
        ]
        if self.missing:
            lines.append(
                "  NOT DETERMINED for track(s) "
                + ", ".join(str(n) for n in self.missing)
                + ": the log holds no Elapsed: line for them"
            )
        reread = {n: r for n, r in self.reads.items() if r > 1}
        if reread:
            lines.append(
                "  read more than once (each Elapsed: covers every read): "
                + ", ".join(f"track {n} x{r}" for n, r in sorted(reread.items()))
            )
        if self.source:
            lines.append(f"  from {self.source}")
        return "\n".join(lines)


def timing_from_log(label: str, log: RipLog, source: str = "") -> TimingRecord:
    """A :class:`TimingRecord` from a parsed rip log. Never raises.

    A non-finite or negative ``Elapsed:`` is treated as missing rather than
    summed: the parser bounds the digits, but a value that cannot be a duration
    must not move a ratio.
    """
    seconds: dict[int, float] = {}
    missing: list[int] = []
    reads: dict[int, int] = {}
    for track in log.tracks:
        number = track.number
        value = track.extraction_elapsed_seconds
        if isinstance(value, float) and math.isfinite(value) and value >= 0:
            seconds[number] = value
        else:
            missing.append(number)
        if isinstance(track.rip_count, int) and track.rip_count > 0:
            reads[number] = track.rip_count
    return TimingRecord(
        label=label,
        build=(log.ripper_build or "").strip(),
        seconds=seconds,
        missing=tuple(missing),
        reads=reads,
        source=source,
    )


@dataclass(frozen=True)
class Ratio:
    """``candidate / base`` over the same tracks, or why it is not determined.

    ``value`` is ``None`` exactly when ``refusal`` is set. Tri-state as always: a
    comparison that could not be made says so and carries no number.
    """

    base: str
    candidate: str
    value: float | None
    detail: str
    refusal: str = ""


def ratio(base: TimingRecord | None, candidate: TimingRecord | None) -> Ratio:
    """The summed-``Elapsed:`` ratio of ``candidate`` to ``base``. Never raises.

    Refuses — no number, a reason — when either record is absent or incomplete,
    when the track sets differ, when the read counts differ on a common track,
    when either build is not determined, or when both name the same build (a
    build compared with itself measures the drive, not the build).
    """
    base_label = base.label if base is not None else "?"
    cand_label = candidate.label if candidate is not None else "?"

    def refuse(why: str) -> Ratio:
        return Ratio(base_label, cand_label, None, "", f"not determined: {why}")

    if base is None or candidate is None:
        absent = [
            label
            for label, record in ((base_label, base), (cand_label, candidate))
            if record is None
        ]
        return refuse(f"no timing has been recorded as {', '.join(absent)}")
    for record in (base, candidate):
        if not record.complete:
            return refuse(
                f"timing {record.label} is incomplete (track(s) "
                f"{', '.join(str(n) for n in record.missing) or 'none'} untimed, "
                f"{len(record.seconds)} timed)"
            )
        if not record.build:
            return refuse(
                f"timing {record.label}'s log names no build, so what it measured "
                "cannot be said"
            )
    if base.build == candidate.build:
        return refuse(
            f"both timings came from {base.build}; a build compared with itself "
            "measures the drive, not the build"
        )
    tracks = tuple(sorted(base.seconds))
    if tracks != tuple(sorted(candidate.seconds)):
        return refuse(
            f"the track sets differ ({base.label}: {list(tracks)}, "
            f"{candidate.label}: {sorted(candidate.seconds)}), so the sums are "
            "over different audio"
        )
    differing = [
        n
        for n in tracks
        if n in base.reads
        and n in candidate.reads
        and base.reads[n] != candidate.reads[n]
    ]
    if differing:
        return refuse(
            "track(s) "
            + ", ".join(
                f"{n} ({base.reads[n]} vs {candidate.reads[n]} reads)"
                for n in differing
            )
            + " were read a different number of times, so the work differs"
        )
    base_sum, cand_sum = base.total(tracks), candidate.total(tracks)
    if base_sum <= 0:
        return refuse(
            f"timing {base.label} sums to {base_sum:.2f} s; nothing to divide by"
        )
    value = cand_sum / base_sum
    return Ratio(
        base.label,
        candidate.label,
        value,
        f"{candidate.label}/{base.label} = {value:.3f} ({candidate.build} "
        f"{cand_sum:.2f} s / {base.build} {base_sum:.2f} s over track(s) "
        f"{', '.join(str(n) for n in tracks)})",
    )


@dataclass(frozen=True)
class Agreement:
    """Whether two pairs' ratios agree within the tolerance; tri-state.

    ``agree`` is ``None`` when either ratio is not determined.
    """

    agree: bool | None
    detail: str


def agreement(
    first: Ratio, second: Ratio, tolerance: float = AGREEMENT_TOLERANCE
) -> Agreement:
    """Do two ratios agree within ``tolerance``? Never raises."""
    if first.value is None or second.value is None:
        return Agreement(
            None,
            "agreement not determined: "
            + "; ".join(r.refusal for r in (first, second) if r.refusal),
        )
    gap = abs(first.value - second.value)
    # Inclusive, and the boundary is not decided by float error: 1.05 - 1.00 is
    # 0.050000000000000044 in binary, which is "within 0.05" as S15 means it.
    agree = gap < tolerance or math.isclose(gap, tolerance, rel_tol=1e-9)
    verdict = "AGREE" if agree else "DISAGREE"
    tail = (
        "the comparison is done"
        if agree
        else "the comparison is not settled; another A/B pair is needed"
    )
    return Agreement(
        agree,
        f"the two ratios {verdict}: {first.value:.3f} and {second.value:.3f} differ "
        f"by {gap:.3f} (tolerance {tolerance:.2f}); {tail}",
    )
