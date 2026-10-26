# SPDX-License-Identifier: GPL-3.0-only
"""Every CTDB CRC a verify compares, from ONE streamed pass over the disc's PCM.

**What CTDB stores per entry** (`lookup2.php`): one whole-disc CRC (`crc32`) and
one CRC per track (`trackcrcs`). Both are the same kind of number, a plain zlib
CRC-32 over a WINDOW of the disc's little-endian 16-bit stereo PCM. They differ
only in which window:

* **the whole disc**: everything except the guard band, the front ``stride/2``
  frames and the back ``laststride/2`` frames (:func:`crc.ctdb_trims`, confirmed
  on hardware, KDD-16);
* **a track**: that track's samples, except that the FIRST track also loses the
  front guard band and the LAST track also loses the back one.

The track definition is CUETools' ``AccurateRipVerify.CTDBCRC(iTrack, oi,
prefixSamples, suffixSamples)`` (LGPL, ``CUETools.AccurateRip/AccurateRip.cs``),
which ``CDRepairEncode.TrackCRC(iTrack, oi)`` (``CDRepair.cs``) calls with
``prefixSamples = stride/2`` and ``suffixSamples = laststride/2``, the same two
trims as the whole-disc value. Track 1 starts at ``prefixSamples`` and the last
track ends ``suffixSamples`` before the lead-out; every other track is whole. So a
middle track's CTDB CRC is just the CRC-32 of the track, which is the number EAC
prints as "Copy CRC" when null samples are counted. That is how
``tests/test_ctdb_per_track.py`` checks this definition against MEASURED data (the
committed EAC logs of the reference disc beside the real CTDB response for it)
rather than against this description of it.

**An offset** ``o`` moves every window ``o`` frames later into our audio (``front
+= o``, ``back -= o`` in :func:`crc.ctdb_crc`). It asks: does our audio equal the
entry's if that entry's pressing sits ``o`` samples from ours? CTDB places a
pressing anywhere in ±5879 frames (:data:`crc.CTDB_OFFSET_RANGE`), so every
track is measured over that whole range; which of those offsets count for which
entry is :mod:`platterpus.ctdb.matching`'s question.

**How, without holding the disc in memory or re-CRCing it per offset.** Let
``C(x) = zlib.crc32(pcm[:x])``. The CRC of the slice ``pcm[a:b]`` is
``C(b) XOR Z(C(a))``, where ``Z`` is the GF(2) operator "append ``b - a`` zero
bytes" (zlib's ``crc32_combine`` algebra, :func:`calibrate.combine_operator`). A
window keeps its length as it slides, so each window needs ONE operator, and each
offset then costs two prefix values and four table lookups. The prefix values are
read off one running CRC as the tracks stream past, one track's PCM resident at a
time: the memory rule (#39) that ``verify.py`` already keeps.

Pure and total: no Qt, no I/O, never raises on any integers or bytes. Heavy
enough (one pass over ~600 MB of PCM) that it must run off the GUI thread, which
``workers/ctdb_worker.py`` already guarantees for the whole verify.
"""

from __future__ import annotations

import logging
import zlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from platterpus.ctdb.calibrate import combine_operator
from platterpus.ctdb.crc import BYTES_PER_SAMPLE_FRAME, CTDB_OFFSET_RANGE, ctdb_trims
from platterpus.ctdb.toc import LEAD_IN_SECTORS, SAMPLES_PER_SECTOR, DiscToc

log = logging.getLogger(__name__)

#: How far a pressing can sit from ours: CTDB's ±(stride/2 − 1) frames, the
#: range ``CDRepairEncode.FindOffset`` searches. Tracks are measured over all of
#: it, because an entry's own offset can be anywhere in it.
DISC_OFFSET_RANGE: int = CTDB_OFFSET_RANGE  # = 5879

#: A window in stereo frames, ``(start, end)``, end exclusive, at offset 0.
Window = tuple[int, int]

#: The four 256-entry byte tables of one GF(2) operator (see `_byte_tables`).
_Tables = tuple[list[int], list[int], list[int], list[int]]


@dataclass(frozen=True)
class SweepResult:
    """What one pass measured. Offsets map to CRCs; an absent offset was not measured.

    ``disc`` holds the whole-disc CTDB CRC by offset; ``disc[0]`` is the value
    the database stores for an aligned pressing. ``tracks`` holds, per track in
    disc order, that track's CTDB CRC by offset. ``bytes_seen`` is how much PCM
    actually arrived: a window that reaches past it has no CRC, rather than a
    CRC of audio that was never read.
    """

    disc: Mapping[int, int]
    tracks: tuple[Mapping[int, int], ...]
    bytes_seen: int


def disc_window(total_frames: int) -> Window | None:
    """The whole-disc window at offset 0, or ``None`` when the guard band eats it."""
    front, back = ctdb_trims(total_frames)
    start, end = front, total_frames - back
    return (start, end) if end > start else None


def track_windows(
    track_starts: Sequence[int], total_frames: int
) -> tuple[Window | None, ...]:
    """Each track's CTDB window at offset 0, in disc order (``None``: no window).

    ``track_starts`` are frame positions from the start of the disc's audio
    (track 1 at 0). Track ``i`` runs to the next start, the last to
    ``total_frames``; then the first loses the front guard band and the last the
    back one. A one-track disc gets exactly the whole-disc window, as CUETools'
    code gives it. A track the trims swallow (a first track shorter than 5880
    frames) has no window rather than a negative one.
    """
    front, back = ctdb_trims(total_frames)
    count = len(track_starts)
    windows: list[Window | None] = []
    for index, raw_start in enumerate(track_starts):
        start = raw_start + (front if index == 0 else 0)
        end = track_starts[index + 1] if index + 1 < count else total_frames
        if index == count - 1:
            end -= back
        windows.append((start, end) if end > start else None)
    return tuple(windows)


def _offsets(window: Window | None, spread: int, total_frames: int) -> list[int]:
    """The offsets in ``±spread`` that keep ``window`` inside the disc."""
    if window is None or spread < 0:
        return []
    start, end = window
    return [
        o
        for o in range(-spread, spread + 1)
        if start + o >= 0 and end + o <= total_frames
    ]


def _prefix_crcs(
    chunks: Iterable[bytes], positions: Sequence[int]
) -> tuple[dict[int, int], int]:
    """``{p: zlib.crc32(pcm[:p])}`` for each sorted byte position, streamed.

    One running CRC is carried across the chunks; at each wanted position the
    bytes up to it are folded in and the value is recorded. Positions past the
    end of the data get no value. Returns the values and the bytes consumed.
    """
    values: dict[int, int] = {}
    wanted = len(positions)
    index = 0
    running = 0
    consumed = 0
    while index < wanted and positions[index] <= 0:
        values[positions[index]] = 0  # the CRC of nothing
        index += 1
    for chunk in chunks:
        view = memoryview(chunk)
        chunk_start = consumed
        chunk_end = consumed + len(view)
        folded = 0  # bytes of this chunk already in `running`
        while index < wanted and positions[index] <= chunk_end:
            relative = positions[index] - chunk_start
            if relative > folded:
                running = zlib.crc32(view[folded:relative], running)
                folded = relative
            values[positions[index]] = running
            index += 1
        if folded < len(view):
            running = zlib.crc32(view[folded:], running)
        consumed = chunk_end
    return values, consumed


def _byte_tables(operator: list[int]) -> _Tables:
    """Four 256-entry tables that apply a GF(2) operator one byte at a time.

    The operator is linear, so its image of a 32-bit value is the XOR of the
    images of its four bytes, and each byte's 256 images can be listed up front.
    Applying it then costs four lookups instead of a 32-step loop, which matters
    when it runs once per offset per window (about 94,000 times on a 14-track disc).
    """
    tables: list[list[int]] = []
    for lane in range(4):
        columns = operator[lane * 8 : lane * 8 + 8]
        table = [0] * 256
        for value in range(1, 256):
            low_bit = value & -value
            table[value] = table[value ^ low_bit] ^ columns[low_bit.bit_length() - 1]
        tables.append(table)
    return tables[0], tables[1], tables[2], tables[3]


def _window_crcs(
    window: Window,
    offsets: Sequence[int],
    prefix: Mapping[int, int],
    operators: dict[int, _Tables],
) -> dict[int, int]:
    """The CRC of ``window`` moved by each offset, from the prefix values."""
    start, end = window
    length = (end - start) * BYTES_PER_SAMPLE_FRAME
    tables = operators.get(length)
    if tables is None:
        tables = _byte_tables(combine_operator(length))
        operators[length] = tables
    t0, t1, t2, t3 = tables
    crcs: dict[int, int] = {}
    for offset in offsets:
        head = prefix.get((start + offset) * BYTES_PER_SAMPLE_FRAME)
        tail = prefix.get((end + offset) * BYTES_PER_SAMPLE_FRAME)
        if head is None or tail is None:
            continue  # part of the window never arrived
        shifted = (
            t0[head & 0xFF]
            ^ t1[(head >> 8) & 0xFF]
            ^ t2[(head >> 16) & 0xFF]
            ^ t3[head >> 24]
        )
        crcs[offset] = (tail ^ shifted) & 0xFFFFFFFF
    return crcs


def sweep(
    chunks: Iterable[bytes],
    track_starts: Sequence[int],
    total_frames: int,
    *,
    disc_range: int = 0,
    track_range: int = DISC_OFFSET_RANGE,
) -> SweepResult:
    """Measure the whole-disc CRC over ``±disc_range`` and every track's over ``±track_range``.

    ``chunks`` is the disc's PCM in order (a generator decoding one track at a
    time keeps one track resident); ``track_starts`` and ``total_frames`` come
    from the disc's TOC, so the windows are the ones CTDB keyed, not ones read
    off however much audio the decoder produced. A decoder error raised by the
    generator propagates to the caller, which turns it into a verdict.
    """
    disc_win = disc_window(total_frames)
    track_wins = track_windows(track_starts, total_frames)
    disc_offsets = _offsets(disc_win, disc_range, total_frames)
    track_offsets = [_offsets(w, track_range, total_frames) for w in track_wins]

    wanted: set[int] = set()
    plans: list[tuple[Window | None, list[int]]] = [(disc_win, disc_offsets)]
    plans.extend(zip(track_wins, track_offsets, strict=True))
    for window, offsets in plans:
        if window is None:
            continue
        for offset in offsets:
            wanted.add((window[0] + offset) * BYTES_PER_SAMPLE_FRAME)
            wanted.add((window[1] + offset) * BYTES_PER_SAMPLE_FRAME)

    prefix, consumed = _prefix_crcs(chunks, sorted(wanted))
    operators: dict[int, _Tables] = {}
    disc = _window_crcs(disc_win, disc_offsets, prefix, operators) if disc_win else {}
    tracks = tuple(
        _window_crcs(window, offsets, prefix, operators) if window else {}
        for window, offsets in zip(track_wins, track_offsets, strict=True)
    )
    return SweepResult(disc=disc, tracks=tracks, bytes_seen=consumed)


def disc_frames(toc: DiscToc) -> tuple[list[int], int]:
    """``(track starts, total frames)`` from the TOC: frames from track 1's start."""
    starts = [
        (sector - LEAD_IN_SECTORS) * SAMPLES_PER_SECTOR for sector in toc.track_offsets
    ]
    return starts, (toc.leadout - LEAD_IN_SECTORS) * SAMPLES_PER_SECTOR


def sweep_disc(
    chunks: Iterable[bytes], toc: DiscToc, *, disc_range: int = 0
) -> SweepResult:
    """:func:`sweep` with the windows read from the disc's TOC, as a verify needs.

    ``disc[0]`` equals ``crc.ctdb_crc(whole_disc_pcm, 0)``, the value confirmed
    on hardware (KDD-16); ``tests/test_ctdb_per_track.py`` holds the two equal.
    """
    starts, total_frames = disc_frames(toc)
    measured = sweep(chunks, starts, total_frames, disc_range=disc_range)
    expected = total_frames * BYTES_PER_SAMPLE_FRAME
    if measured.bytes_seen != expected:
        # The TOC comes from metaflac's sample counts and the PCM from flac's
        # decode, so the two agree for any sound FLAC. When they do not, the
        # windows past the audio have no CRC and their tracks read "not
        # determined" rather than being compared against audio never read.
        log.warning(
            "CTDB sweep: decoded %d bytes of PCM where the TOC says %d",
            measured.bytes_seen,
            expected,
        )
    return measured
