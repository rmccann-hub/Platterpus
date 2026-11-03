"""Is there clearly too little room for this rip? Asked before it starts (C10).

**Why.** Nothing checked free space anywhere: a rip to a nearly full disk read
the whole disc and then failed writing, or wrote a truncated file, with the
drive time spent and the cause left for the reader of a log to find. The
question is asked once, before the ripper is spawned, by the rip worker on its
own thread (``RipWorker._space_refusal``), so a stalled network mount behind
the output folder can never freeze the window.

**The estimate is a floor, so a refusal means "clearly too little".** Audio CD
is 44,100 samples a second, two channels of two bytes: 176,400 bytes a second
of PCM. The FLAC master is counted at :data:`FLAC_FLOOR` of that, below what
FLAC makes of ordinary music (about half to two thirds), and each derived
format at its own floor (:data:`DERIVED_FLOOR`). A rip refused here would not
have fit even at those floors; a rip that passes can still run out of room on
an unusually incompressible disc, which the ripper then reports in its own
words. Nothing else is counted (the securing pass's temporary re-reads, the
logs), so the floor stays a floor.

**Tri-state, and unknown never refuses.** No track lengths (an unknown disc),
or a filesystem that cannot be asked, gives "not determined": the rip goes ahead
and the log says why nothing was checked. A check that refused on unknown would
stop rips it knows nothing about.

Pure except :func:`free_bytes`, which asks the filesystem once. Never raises.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

#: Bytes of PCM per second of CD audio: 44,100 Hz x 2 channels x 2 bytes.
PCM_BYTES_PER_SECOND: Final[int] = 44_100 * 2 * 2

#: The FLAC master's floor, as a fraction of PCM. FLAC makes ordinary CD music
#: about 50 to 70 % of PCM; 0.3 is below that for anything but near-silence.
FLAC_FLOOR: Final[float] = 0.3

#: Each derived format's floor, as a fraction of PCM, kept beside the FLAC
#: master (Critical rule #4). WAV is PCM itself; WavPack is lossless like FLAC;
#: MP3 VBR's smallest setting (``-V 9``) averages about 65 kbit/s, 4.6 % of PCM.
DERIVED_FLOOR: Final[dict[str, float]] = {
    "flac": 0.0,
    "wavpack": 0.3,
    "mp3": 0.04,
    "wav": 1.0,
}


@dataclass(frozen=True)
class SpaceCheck:
    """The answer: ``refuse`` True, False, or None (not determined), and why."""

    refuse: bool | None
    message: str


def audio_seconds(tracks: Iterable[object], wanted: Iterable[int] = ()) -> float | None:
    """Seconds of audio in the selected tracks, or None when any length is unknown.

    ``tracks`` are the rip's MusicBrainz tracks (``number``, ``length_ms``);
    ``wanted`` the selection, empty for all. The same rule as the rip's time
    estimate (``RipWorker._make_estimate``): every selected track needs a length.
    """
    chosen = set(wanted)
    lengths = [
        getattr(t, "length_ms", None)
        for t in tracks
        if not chosen or getattr(t, "number", None) in chosen
    ]
    if not lengths or any(not isinstance(ms, int) or ms <= 0 for ms in lengths):
        return None
    return sum(ms for ms in lengths if isinstance(ms, int)) / 1000


def bytes_needed(seconds: float | None, output_format: str) -> int | None:
    """The floor of what the rip writes: the FLAC master plus the derived format.

    None when the audio's length is unknown. A format not in
    :data:`DERIVED_FLOOR` adds nothing, so the figure stays a floor.
    """
    if seconds is None or seconds <= 0:
        return None
    ratio = FLAC_FLOOR + DERIVED_FLOOR.get(output_format, 0.0)
    return int(seconds * PCM_BYTES_PER_SECOND * ratio)


def free_bytes(folder: Path) -> int | None:
    """Free bytes on the filesystem ``folder`` will be on, or None if unknown.

    The output folder may not exist yet (the album folder is made by the rip),
    so the nearest existing parent is asked. Never raises.
    """
    candidate = folder
    try:
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        return shutil.disk_usage(candidate).free
    except (OSError, ValueError) as exc:
        log.warning("could not read the free space under %s: %r", folder, exc)
        return None


def _size(count: int) -> str:
    """Bytes as a person reads them: ``"412 MB"``, ``"1.6 GB"``."""
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f} GB"
    return f"{max(count, 0) / 1_000_000:.0f} MB"


def check(
    needed: int | None, free: int | None, folder: Path, output_format: str
) -> SpaceCheck:
    """Refuse only when ``free`` is below the floor ``needed``. Pure."""
    if needed is None:
        return SpaceCheck(
            None,
            "free space not checked: the length of the audio is not known "
            "(the disc is not identified, or a track has no length)",
        )
    if free is None:
        return SpaceCheck(
            None,
            f"free space not checked: the filesystem under {folder} gave no answer",
        )
    formats = "FLAC" if output_format in ("flac", "") else f"FLAC + {output_format}"
    if free < needed:
        return SpaceCheck(
            True,
            f"Not enough free space to rip: the output folder {folder} is on a "
            f"drive with {_size(free)} free, and this rip needs at least "
            f"{_size(needed)} ({formats}). Free some space, or choose another "
            "output folder in Settings.",
        )
    return SpaceCheck(
        False,
        f"free space: {_size(free)} under {folder}, this rip needs at least "
        f"{_size(needed)} ({formats})",
    )


def check_output_space(
    folder: Path,
    tracks: Iterable[object],
    wanted: Iterable[int],
    output_format: str,
) -> SpaceCheck:
    """:func:`check` for a rip, asking the filesystem once, and logged. Never raises."""
    try:
        needed = bytes_needed(audio_seconds(tracks, wanted), output_format)
        result = check(
            needed, free_bytes(folder) if needed else None, folder, output_format
        )
    except Exception as exc:  # noqa: BLE001 — a check must never stop a rip by crashing
        log.exception("the free-space check failed")
        return SpaceCheck(None, f"free space not checked: the check failed ({exc!r})")
    if result.refuse:
        log.error("%s", result.message)
    else:
        log.info("%s", result.message)
    return result
