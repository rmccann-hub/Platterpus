"""How long a rip should take, said before it starts, from what the drive has done.

**Why.** The live estimate (``RipWorker._album_eta_text``) needs eight seconds of
reading before it says anything, and it can only measure the pass in front of it,
so a rip began with no figure at all and the re-reads after the main pass came as
a surprise. Our operator asked for an overall estimate, in the log as well
(2026-10-05), on the reasoning that we hold a great deal of timing data. We do:
every filed rip report carries each track's extraction time and its length.

**The model, and the data it comes from.** On the rig's drive (the filed reports,
rounds 8 to 30, ``docs/handshake/artifactsround*/*report.json``):

* the first read of a track takes about its own running time: 0.88 to 1.09
  seconds of reading per second of audio, whole discs and two-track rips alike;
* a rip costs about 6 to 13 seconds beyond its reading (starting the ripper,
  the AccurateRip lookups);
* a secure re-read at ``-Z N`` reads a track N+1 times when the reads agree and
  up to the retry ceiling (``-r``) when they do not; uniform ``-Z 2`` rips took
  2.93 to 3.16 times the audio.

So: first pass = audio × the drive's reading multiple + overhead; uniform ``-Z N``
multiplies the reading by N+1 at least; dynamic mode adds, for each track that
AccurateRip does not confirm, N+1 to ``-r`` times that track's own length. Which
tracks will need it cannot be known before the main read, so that part is stated
as a per-track cost, never folded into a single number that would be wrong.

**Where the multiple comes from.** The drive's own finished rips, folded into
its profile (``drive_profiles.DriveProfile.read_rate``), recent rips weighted
more. Before a drive has finished a rip, the rig's measurement is used only for
the rig's drive model (:data:`MODEL_SEEDS`), and any other drive gets no
estimate rather than a guess: drives differ several-fold, and a confident wrong
figure is worse than none. Pure; never raises.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from platterpus.rip_timing import format_duration

#: Seconds a rip costs beyond its reading: the ripper starting, the TOC, the
#: AccurateRip lookups. The filed rig rips show 5.3 to 12.8 s (two-track rips,
#: elapsed minus the sum of extraction times); `tests/test_rip_estimate.py` reads
#: them and holds this inside that range.
OVERHEAD_S: Final[float] = 10.0

#: How much an earlier rip counts against a new one when they are folded
#: together. Recent rips count more, so a drive that is cleaned, or a disc
#: batch that reads differently, moves the estimate within a few rips.
HISTORY_WEIGHT: Final[float] = 0.7

#: The reading multiple measured on the project's rig, by drive model, used for
#: a drive of that model until it has finished a rip of its own. Keyed by
#: `drive_profiles.normalize_drive_name`. Derived from the filed reports' first
#: passes (median 1.05 seconds of reading per second of audio); the test
#: re-derives it from the artifacts.
MODEL_SEEDS: Final[dict[str, float]] = {"PIONEER BD-RW BDR-209D": 1.05}

#: The audio a seed stands for, so a seed and a first real rip fold sensibly.
_SEED_AUDIO_S: Final[float] = 3600.0


@dataclass(frozen=True)
class ReadRate:
    """A drive's measured first reads: audio read, seconds spent reading it.

    ``rips`` is how many of the drive's own rips are folded in; 0 marks a seed
    from :data:`MODEL_SEEDS`, which the drive's first real rip replaces.
    """

    audio_seconds: float
    read_seconds: float
    rips: int

    @property
    def multiple(self) -> float | None:
        """Seconds of reading per second of audio, or None when unmeasurable."""
        if self.audio_seconds <= 0 or self.read_seconds <= 0:
            return None
        return self.read_seconds / self.audio_seconds


def seed_for(model_key: str) -> ReadRate | None:
    """The rig's measurement for this drive model, if it is the rig's model."""
    multiple = MODEL_SEEDS.get(model_key)
    if multiple is None:
        return None
    return ReadRate(_SEED_AUDIO_S, _SEED_AUDIO_S * multiple, 0)


def fold(rate: ReadRate | None, audio_seconds: float, read_seconds: float) -> ReadRate:
    """Fold one rip's first reads into a drive's history.

    A seed (``rips == 0``) is replaced, not averaged: the drive's own rip is the
    better witness. Otherwise earlier rips are weighted by :data:`HISTORY_WEIGHT`.
    """
    if rate is None or rate.rips <= 0:
        return ReadRate(audio_seconds, read_seconds, 1)
    return ReadRate(
        rate.audio_seconds * HISTORY_WEIGHT + audio_seconds,
        rate.read_seconds * HISTORY_WEIGHT + read_seconds,
        rate.rips + 1,
    )


def first_pass_sample(tracks: Iterable[object]) -> tuple[float, float] | None:
    """(audio seconds, reading seconds) over a parsed log's tracks, or None.

    A track counts only when it carries both its sector span and its extraction
    time, so a log cut short contributes the tracks it finished. 75 sectors per
    second (Red Book).
    """
    audio = 0.0
    reading = 0.0
    for track in tracks:
        start = getattr(track, "start_sector", None)
        end = getattr(track, "end_sector", None)
        elapsed = getattr(track, "extraction_elapsed_seconds", None)
        if not (isinstance(start, int) and isinstance(end, int) and end >= start):
            continue
        if not isinstance(elapsed, int | float) or not math.isfinite(elapsed):
            continue
        if elapsed <= 0:
            continue
        audio += (end - start + 1) / 75
        reading += float(elapsed)
    if audio <= 0 or reading <= 0:
        return None
    return audio, reading


@dataclass(frozen=True)
class RipEstimate:
    """What a rip should take, before it starts."""

    #: The audio the rip will read, seconds.
    audio_seconds: float
    #: The reading multiple the figure rests on, and how many rips measured it.
    multiple: float
    rips: int
    #: The main pass, including overhead (uniform mode: every track's N+1 reads).
    seconds: float
    #: Uniform mode: the most, if every track needs the retry ceiling.
    seconds_high: float | None
    #: Dynamic mode: a re-read track costs this many times its own length, lo-hi.
    reread_low: float | None
    reread_high: float | None


def estimate_rip(
    audio_seconds: float,
    rate: ReadRate | None,
    *,
    secure_rerip_matches: int,
    dynamic: bool,
    max_retries: int,
) -> RipEstimate | None:
    """The estimate for a rip of ``audio_seconds``, or None when it cannot be made."""
    if rate is None or audio_seconds <= 0 or not math.isfinite(audio_seconds):
        return None
    multiple = rate.multiple
    if multiple is None or not math.isfinite(multiple):
        return None
    reading = audio_seconds * multiple
    reads_low = secure_rerip_matches + 1 if secure_rerip_matches > 0 else 1
    reads_high = max(reads_low, max_retries)
    if secure_rerip_matches > 0 and not dynamic:
        return RipEstimate(
            audio_seconds,
            multiple,
            rate.rips,
            reading * reads_low + OVERHEAD_S,
            reading * reads_high + OVERHEAD_S,
            None,
            None,
        )
    reread = secure_rerip_matches > 0 and dynamic
    return RipEstimate(
        audio_seconds,
        multiple,
        rate.rips,
        reading + OVERHEAD_S,
        None,
        multiple * reads_low if reread else None,
        multiple * reads_high if reread else None,
    )


def rough(seconds: float) -> str:
    """A duration as an estimate is said: to the minute, or five past an hour.

    "about 1h 5m", not "1h 4m 37s": the figure is a projection, and digits it
    cannot support read as a measurement. Under two minutes it keeps seconds.
    """
    if not math.isfinite(seconds) or seconds < 0:
        return "unknown"
    if seconds < 120:
        return format_duration(seconds)
    step = 300 if seconds >= 3600 else 60
    rounded = int(round(seconds / step) * step)
    hours, rem = divmod(rounded, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes}m"


def describe(estimate: RipEstimate | None, *, known: bool = True) -> str:
    """One sentence for the plan and the log.

    ``known`` False means the selected tracks' lengths are not all known (an
    unknown disc), which is a different reason for having no estimate.
    """
    if estimate is None:
        if not known:
            return (
                "Time estimate: none, because the length of every track to rip "
                "is not known (the disc is not identified)."
            )
        return (
            "Time estimate: none yet. This drive has finished no rip in "
            "Platterpus, so how fast it reads is not known; the live estimate "
            "appears once reading starts, and later rips get one up front."
        )
    if estimate.rips > 0:
        basis = (
            f"this drive's own reading speed over its last {estimate.rips} "
            f"rip{'s' if estimate.rips != 1 else ''}"
        )
    else:
        basis = "the speed measured on the project's test rig for this drive model"
    speed = 1 / estimate.multiple
    sentence = (
        f"Time estimate: about {rough(estimate.seconds)} for "
        f"{rough(estimate.audio_seconds)} of audio, at {speed:.1f}x "
        f"({basis})"
    )
    if estimate.seconds_high is not None:
        sentence += (
            f"; up to {rough(estimate.seconds_high)} if reads disagree "
            "and tracks need the retry ceiling"
        )
    sentence += "."
    if estimate.reread_low is not None and estimate.reread_high is not None:
        sentence += (
            " Any track AccurateRip does not confirm is then re-read, which "
            f"takes {estimate.reread_low:.0f} to {estimate.reread_high:.0f} times "
            "that track's own length."
        )
    return sentence
