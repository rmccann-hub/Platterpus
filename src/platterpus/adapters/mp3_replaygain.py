# SPDX-License-Identifier: GPL-3.0-only
"""ReplayGain for a derived MP3, measured on the MP3 itself.

**Why this exists.** cyanrip writes ``REPLAYGAIN_*`` tags into each FLAC from its
own EBU R128 measurement of the audio it read (``cyanrip@eca33dc:src/
cyanrip_main.c:537-580``). The transcode to MP3 copies every tag with
``-map_metadata 0``, so until 0.7.111 an MP3 carried the FLAC's figures: a gain
and, worse, a *peak* measured before the lossy encode. An MP3's decoded peak can
sit above the FLAC's, so a player trusting the copied peak for clipping
prevention trusts a number about a different file (TASKS.md, "A derived MP3
carries the FLAC's `REPLAYGAIN_*` tags").

**What we do instead.** The encode drops those tags (:data:`DROPPED_TAGS`, via an
empty ``-metadata KEY=``, which ffmpeg treats as "delete"). Then we decode each
finished MP3 through ffmpeg's ``ebur128`` filter, the same R128 measurement, and
write the figures in cyanrip's own format (:func:`track_tags`), so the MP3's tags
read like the FLAC's and describe the MP3. Album figures come from one measurement
over every MP3 of the rip played end to end, which is how cyanrip measures the
album: over the whole read, not as an average of tracks.

**Not copied: ``R128_*``.** Those are Opus header-gain tags; an MP3 player does
not read them, so the MP3 carries the ``REPLAYGAIN_*`` set only.

**Resolution.** ``ebur128`` prints its summary to 0.1 LU and 0.1 dB, so the MP3's
figures are written to that resolution (``-7.20 dB``) where cyanrip's carry two
measured decimals. A 0.1 dB step is below what a listener can hear.

**Honest failure.** If a measurement fails, that MP3 gets **no** ReplayGain tags,
never the FLAC's: an absent tag makes a player use its default, a wrong one makes
it act on a number about another file. Album tags are written only when every
track of the rip has an MP3, because an album figure over part of the album is a
claim about a different album. Each reason is recorded with ffmpeg's own words.

Parsing never raises (property-tested); the steps never raise either.
"""

from __future__ import annotations

import logging
import math
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.adapters.tool_run import ToolRunner, make_runner

log = logging.getLogger(__name__)

#: cyanrip's ReplayGain reference loudness (``REPLAYGAIN_REF_LOUDNESS``,
#: ``cyanrip@eca33dc:src/cyanrip_main.c:537``). Gain is this minus the measured
#: integrated loudness.
REFERENCE_LUFS: Final[float] = -18.0

#: Every loudness tag cyanrip writes into a FLAC (``cyanrip_main.c:539-580``). The
#: MP3 encode deletes all of them, so none of the FLAC's figures can survive into
#: the MP3 by accident; the measured ``REPLAYGAIN_*`` set is written back after.
DROPPED_TAGS: Final[tuple[str, ...]] = (
    "REPLAYGAIN_TRACK_GAIN",
    "REPLAYGAIN_TRACK_PEAK",
    "REPLAYGAIN_TRACK_RANGE",
    "REPLAYGAIN_ALBUM_GAIN",
    "REPLAYGAIN_ALBUM_PEAK",
    "REPLAYGAIN_ALBUM_RANGE",
    "REPLAYGAIN_REFERENCE_LOUDNESS",
    "R128_TRACK_GAIN",
    "R128_ALBUM_GAIN",
)

# ffmpeg's ebur128 summary (the block after "Summary:"), e.g.
#     I:         -21.8 LUFS
#     LRA:        20.0 LU
#     Peak:      -21.1 dBFS      (or "-inf dBFS" for digital silence)
# Named groups so a reordered or re-spaced summary still parses.
_SUMMARY: Final[re.Pattern[str]] = re.compile(r"Summary:")
_INTEGRATED: Final[re.Pattern[str]] = re.compile(
    r"^\s*I:\s+(?P<value>-?\d{1,3}(?:\.\d{1,3})?)\s+LUFS\s*$", re.M
)
_RANGE: Final[re.Pattern[str]] = re.compile(
    r"^\s*LRA:\s+(?P<value>\d{1,3}(?:\.\d{1,3})?)\s+LU\s*$", re.M
)
_TRUE_PEAK: Final[re.Pattern[str]] = re.compile(
    r"^\s*Peak:\s+(?P<value>-?(?:\d{1,3}(?:\.\d{1,3})?|inf))\s+dBFS\s*$", re.M
)

# The measurement. ``peak=true`` adds the true peak cyanrip also measures;
# ``framelog=quiet`` stops the per-100-ms lines, which for a whole disc are about
# 44,000 lines of output in front of the one summary we read (measured 2026-10-21:
# 68 lines for a 3-second file without it, the summary alone with it).
_FILTER: Final[str] = "ebur128=peak=true:framelog=quiet"

# Decoding a track for R128 with true peak is fast, but the album measurement
# decodes the whole disc (about 90 s for 74 minutes on a modest machine), so its
# bound is generous. Retagging is a stream copy: seconds.
_TRACK_TIMEOUT_S: Final[float] = 300.0
_ALBUM_TIMEOUT_S: Final[float] = 1800.0


@dataclass(frozen=True)
class Loudness:
    """One R128 measurement: integrated loudness, loudness range, true peak."""

    integrated_lufs: float
    range_lu: float
    #: ``-inf`` for digital silence, which ebur128 prints as ``-inf dBFS``.
    true_peak_dbfs: float


@dataclass(frozen=True)
class Mp3ReplayGain:
    """What happened to the derived MP3s' ReplayGain tags. Goes into the report."""

    #: MP3s that now carry track figures measured on themselves.
    tracks_tagged: int
    #: MP3s this step was given.
    tracks_total: int
    #: Whether album figures were written (every track had an MP3 and the album
    #: measurement succeeded).
    album_tagged: bool
    #: Why anything was left untagged, one line each, with ffmpeg's own words.
    reasons: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        return {
            "measured_on": "the MP3 itself (ffmpeg ebur128, true peak)",
            "tracks_tagged": self.tracks_tagged,
            "tracks_total": self.tracks_total,
            "album_tagged": self.album_tagged,
            "reasons": list(self.reasons),
        }


def drop_args() -> list[str]:
    """``-metadata KEY=`` for every tag in :data:`DROPPED_TAGS`, for the encode argv.

    ffmpeg deletes a key given an empty value, and matches keys without regard to
    case, so a lower-case ``replaygain_track_gain`` goes too."""
    args: list[str] = []
    for key in DROPPED_TAGS:
        args += ["-metadata", f"{key}="]
    return args


def parse_summary(text: str) -> Loudness | None:
    """The figures from ffmpeg's ``ebur128`` summary in ``text``, or ``None``.

    Reads only after the LAST ``Summary:`` (the filter also prints per-frame lines
    when asked, which carry the same labels). Never raises."""
    try:
        if not isinstance(text, str):
            return None
        starts = [m.end() for m in _SUMMARY.finditer(text)]
        if not starts:
            return None
        block = text[starts[-1] :]
        integrated = _INTEGRATED.search(block)
        lra = _RANGE.search(block)
        peak = _TRUE_PEAK.search(block)
        if integrated is None or lra is None or peak is None:
            return None
        peak_text = peak.group("value")
        peak_db = -math.inf if peak_text == "-inf" else float(peak_text)
        if peak_text == "inf":
            return None  # a positive infinite peak is not a measurement
        return Loudness(
            integrated_lufs=float(integrated.group("value")),
            range_lu=float(lra.group("value")),
            true_peak_dbfs=peak_db,
        )
    except (ValueError, TypeError, AttributeError):
        return None


def _gain(measured: Loudness) -> str:
    return f"{REFERENCE_LUFS - measured.integrated_lufs:.2f} dB"


def _peak(measured: Loudness) -> str:
    # cyanrip writes the true peak as a linear amplitude (``powf(10, dB / 20)``);
    # digital silence is 0.
    return f"{10 ** (measured.true_peak_dbfs / 20.0):.6f}"


def track_tags(measured: Loudness) -> dict[str, str]:
    """The track tags in cyanrip's format (``cyanrip_main.c:539-557``), minus R128."""
    return {
        "REPLAYGAIN_TRACK_GAIN": _gain(measured),
        "REPLAYGAIN_TRACK_RANGE": f"{measured.range_lu:.2f} dB",
        "REPLAYGAIN_TRACK_PEAK": _peak(measured),
        "REPLAYGAIN_REFERENCE_LOUDNESS": f"{REFERENCE_LUFS:.2f} LUFS",
    }


def album_tags(measured: Loudness) -> dict[str, str]:
    """The album tags in cyanrip's format (``cyanrip_main.c:559-580``), minus R128."""
    return {
        "REPLAYGAIN_ALBUM_GAIN": _gain(measured),
        "REPLAYGAIN_ALBUM_RANGE": f"{measured.range_lu:.2f} dB",
        "REPLAYGAIN_ALBUM_PEAK": _peak(measured),
    }


def measure_argv(binary: str, paths: Sequence[Path]) -> list[str]:
    """The ffmpeg argv that measures ``paths`` played end to end.

    One path is a track; several are the album, joined with the ``concat`` filter
    so no list file (and no quoting of file names inside one) is needed. The
    output goes to ``/dev/null`` through the ``null`` muxer: nothing is written."""
    argv = [binary, "-nostdin", "-hide_banner"]
    for path in paths:
        argv += ["-i", str(path)]
    if len(paths) == 1:
        argv += ["-map", "0:a", "-af", _FILTER]
    else:
        joined = "".join(f"[{i}:a]" for i in range(len(paths)))
        argv += [
            "-filter_complex",
            f"{joined}concat=n={len(paths)}:v=0:a=1,{_FILTER}",
        ]
    return argv + ["-f", "null", os.devnull]


def retag_argv(binary: str, src: Path, tmp: Path, tags: dict[str, str]) -> list[str]:
    """Stream-copy ``src`` to ``tmp`` with ``tags`` set: no re-encode.

    Measured 2026-10-21 on ffmpeg 6.1 (Lavf60.16.100): the copy decodes to the same
    PCM, sample count included, so the LAME gapless header survives."""
    argv = [binary, "-nostdin", "-y", "-i", str(src)]
    argv += ["-map", "0", "-c", "copy", "-map_metadata", "0", "-id3v2_version", "3"]
    for key, value in tags.items():
        argv += ["-metadata", f"{key}={value}"]
    return argv + ["-f", "mp3", str(tmp)]


def _measure(
    binary: str, paths: Sequence[Path], run: ToolRunner
) -> tuple[Loudness | None, str]:
    result = run(measure_argv(binary, paths))
    if not result.ok:
        return None, result.summary
    measured = parse_summary(result.output)
    if measured is None:
        return None, "ffmpeg's ebur128 summary was not in its output"
    return measured, ""


def _retag(binary: str, path: Path, tags: dict[str, str], run: ToolRunner) -> str:
    """Write ``tags`` into ``path`` atomically; return ``""`` or why it failed."""
    tmp = path.with_name(path.name + ".replaygain.tmp")
    result = run(retag_argv(binary, path, tmp, tags))
    if not result.ok or not tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass
        return result.summary if not result.ok else "ffmpeg wrote no retagged file"
    try:
        os.replace(tmp, path)
    except OSError as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        return f"could not move the retagged file into place: {exc}"
    return ""


def apply(
    mp3s: Sequence[Path],
    *,
    whole_album: bool,
    binary: str,
    runner: ToolRunner | None = None,
) -> Mp3ReplayGain:
    """Measure each MP3, and the album when ``whole_album``, and write the tags.

    ``whole_album`` is the caller's statement that ``mp3s`` is every track of the
    rip; without it no album figures are written. ``runner`` is injectable for
    tests; by default each step gets a runner bounded for its own size. Never
    raises."""
    track_run = runner or make_runner(
        timeout_s=_TRACK_TIMEOUT_S,
        tool="ffmpeg",
        code="replaygain.measure_failed",
        where="adapters.mp3_replaygain.apply",
    )
    album_run = runner or make_runner(
        timeout_s=_ALBUM_TIMEOUT_S,
        tool="ffmpeg",
        code="replaygain.measure_failed",
        where="adapters.mp3_replaygain.apply",
    )
    reasons: list[str] = []
    try:
        per_track: dict[Path, dict[str, str]] = {}
        for path in mp3s:
            measured, why = _measure(binary, [path], track_run)
            if measured is None:
                reasons.append(f"{path.name}: not measured, left untagged: {why}")
            else:
                per_track[path] = track_tags(measured)

        album: dict[str, str] = {}
        if not mp3s:
            pass
        elif not whole_album:
            reasons.append(
                "album figures not written: not every track of the rip has an MP3"
            )
        elif len(per_track) != len(mp3s):
            reasons.append("album figures not written: a track could not be measured")
        else:
            measured, why = _measure(binary, list(mp3s), album_run)
            if measured is None:
                reasons.append(f"album figures not written: {why}")
            else:
                album = album_tags(measured)

        tagged = 0
        album_written = bool(album)
        for path, tags in per_track.items():
            why = _retag(binary, path, {**tags, **album}, track_run)
            if why:
                reasons.append(f"{path.name}: measured but not tagged: {why}")
                album_written = False
            else:
                tagged += 1
        for line in reasons:
            log.warning("MP3 ReplayGain: %s", line)
        return Mp3ReplayGain(
            tracks_tagged=tagged,
            tracks_total=len(mp3s),
            album_tagged=album_written and tagged == len(mp3s),
            reasons=tuple(reasons),
        )
    except Exception as exc:  # noqa: BLE001 — a tagging extra must never sink a rip
        log.exception("MP3 ReplayGain step failed unexpectedly")
        return Mp3ReplayGain(
            tracks_tagged=0,
            tracks_total=len(mp3s),
            album_tagged=False,
            reasons=(*reasons, f"failed unexpectedly: {exc}"),
        )
