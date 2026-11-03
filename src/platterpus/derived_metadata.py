"""Read a derived MP3, WavPack or WAV file's tags, pictures and length, no tool needed.

**Why this exists** (review C4 of the owner's 2026-11-03 Full run). Sections K1
to K3 of the acceptance run graded the FLAC masters a rip keeps, never the MP3,
WavPack or WAV files a user who picked that format actually plays. A tag that
did not carry over, a cover that never reached the MP3, or a file cut short is
only visible in the derived file itself. This is
:mod:`platterpus.flac_metadata`'s counterpart for those three containers, and
for the same reasons it reads the bytes itself: ``ffprobe`` would be a
subprocess on the GUI thread the acceptance verbs run on, and the program that
wrote a file is the wrong one to check it with.

The layouts, each small and fixed:

* **MP3**: an ID3v2 tag (``ID3``, version, flags, a 28-bit syncsafe size, then
  frames: a 4-byte id, a size, 2 flag bytes); then the first MPEG frame, whose
  ``Xing``/``Info`` header counts the frames, and whose LAME extension (21 bytes
  after the encoder string's start) holds the encoder delay and padding, 12 bits
  each. ffmpeg writes both, so the sample count is exact.
* **WavPack**: the first block header (``wvpk``; the total sample count at bytes
  12-15 with its high byte at 11; the sample-rate index in bits 23-26 of the
  flags at 24-27), and the APEv2 tag at the file's end (``APETAGEX`` footer,
  items of value length, flags, key, value; a binary item is a picture).
* **WAV**: RIFF chunks; ``fmt `` gives channels, rate and bits, ``data`` its
  byte length, and a ``LIST``/``INFO`` chunk any tags ffmpeg copied.

**It never raises**, like its sibling: the file is another program's output and
may be truncated or not that format at all. Every way of not reading it is a
:attr:`DerivedMetadata.problem` sentence. A "never raises" property test holds it.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final

from platterpus.flac_metadata import normalise_key

log = logging.getLogger(__name__)

#: Bounds, so a corrupt length cannot make us read a gigabyte: a tag with a
#: cover is well under this, and a WAV has a handful of chunks.
MAX_TAG_BYTES: Final[int] = 32 << 20
MAX_CHUNKS: Final[int] = 64
_MP3_SYNC_SEARCH: Final[int] = 64 << 10

#: ID3v2, APEv2 and RIFF INFO names, as the Vorbis comment names the masters use.
_ID3_NAMES: Final[dict[str, str]] = {
    "TIT2": "TITLE",
    "TPE1": "ARTIST",
    "TALB": "ALBUM",
    "TPE2": "ALBUMARTIST",
    "TRCK": "TRACKNUMBER",
}
_INFO_NAMES: Final[dict[bytes, str]] = {
    b"INAM": "TITLE",
    b"IART": "ARTIST",
    b"IPRD": "ALBUM",
    b"IPRT": "TRACKNUMBER",
    b"ITRK": "TRACKNUMBER",
}
_APE_ALIASES: Final[dict[str, str]] = {"TRACK": "TRACKNUMBER"}
_ID3_TEXT_CODECS: Final[dict[int, str]] = {
    0: "latin-1",
    1: "utf-16",
    2: "utf-16-be",
    3: "utf-8",
}
#: WavPack's sample-rate table (the format's ``sample_rates``), index 15 custom.
_WV_RATES: Final[tuple[int, ...]] = (
    6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000,
    32000, 44100, 48000, 64000, 88200, 96000, 192000,
)  # fmt: skip
#: MPEG audio sample rates by version bits (index 3 is reserved).
_MPEG_RATES: Final[dict[int, tuple[int, int, int]]] = {
    3: (44100, 48000, 32000),  # MPEG 1
    2: (22050, 24000, 16000),  # MPEG 2
    0: (11025, 12000, 8000),  # MPEG 2.5
}


@dataclass(frozen=True)
class DerivedMetadata:
    """What one derived file says about itself.

    ``samples`` is per channel; ``exact`` says it is the true count (always for
    WavPack and WAV, and for an MP3 whose header gave delay and padding) rather
    than whole frames. A non-empty ``problem`` is *not determined*.
    """

    kind: str
    tags: tuple[tuple[str, str], ...] = ()
    pictures: int = 0
    samples: int | None = None
    sample_rate: int | None = None
    bits: int | None = None
    exact: bool = False
    problem: str = ""

    def values(self, key: str) -> list[str]:
        """Every value under ``key``, compared as :func:`normalise_key` does."""
        wanted = normalise_key(key)
        return [value for name, value in self.tags if normalise_key(name) == wanted]


def read_derived_metadata(path: Path) -> DerivedMetadata:
    """The tags, pictures and length of the MP3, WavPack or WAV at ``path``."""
    try:
        with path.open("rb") as handle:
            head = handle.read(12)
            if head[:4] == b"wvpk":
                return _read_wavpack(handle, head)
            if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
                return _read_wav(handle)
            if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3"):
                return _read_mp3(handle)
            return DerivedMetadata("", problem="not an MP3, WavPack or WAV file")
    except (OSError, struct.error, ValueError, IndexError) as exc:
        log.warning("could not read derived file %s: %s", path, exc)
        return DerivedMetadata("", problem=f"the file could not be read ({exc})")


def _text(raw: bytes, codec: str) -> list[str]:
    """Null-separated text values, trailing nulls and empties dropped."""
    text = raw.decode(codec, errors="replace")
    return [part for part in text.split("\x00") if part]


def _syncsafe(raw: bytes) -> int:
    return (raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]


def _read_mp3(handle: BinaryIO) -> DerivedMetadata:
    handle.seek(0)
    tags: list[tuple[str, str]] = []
    pictures = 0
    header = handle.read(10)
    audio_start = 0
    if header[:3] == b"ID3" and len(header) == 10:
        major, flags, size = header[3], header[5], _syncsafe(header[6:10])
        if size > MAX_TAG_BYTES:
            return DerivedMetadata("mp3", problem=f"the ID3 tag claims {size} bytes")
        body = handle.read(size)
        if len(body) < size:
            return DerivedMetadata("mp3", problem="the file ends inside its ID3 tag")
        if flags & 0x80:
            body = body.replace(b"\xff\x00", b"\xff")  # unsynchronisation
        position = 0
        if flags & 0x40 and len(body) >= 4:  # extended header
            extended = int.from_bytes(body[:4], "big")
            position = _syncsafe(body[:4]) if major >= 4 else extended + 4
        while position + 10 <= len(body) and body[position] != 0:
            frame_id = body[position : position + 4].decode("latin-1")
            raw = body[position + 4 : position + 8]
            length = _syncsafe(raw) if major >= 4 else int.from_bytes(raw, "big")
            payload = body[position + 10 : position + 10 + length]
            position += 10 + length
            if frame_id == "APIC":
                pictures += 1
            elif payload and (frame_id in _ID3_NAMES or frame_id == "TXXX"):
                codec = _ID3_TEXT_CODECS.get(payload[0], "latin-1")
                values = _text(payload[1:], codec)
                if frame_id == "TXXX" and values:
                    tags.extend((values[0], value) for value in values[1:])
                elif frame_id != "TXXX":
                    tags.extend((_ID3_NAMES[frame_id], value) for value in values)
        audio_start = 10 + size + (10 if flags & 0x10 else 0)
    handle.seek(audio_start)
    window = handle.read(_MP3_SYNC_SEARCH)
    sync = next(
        (
            i
            for i in range(len(window) - 4)
            if window[i] == 0xFF and window[i + 1] >= 0xE0
        ),
        -1,
    )
    if sync < 0:
        return DerivedMetadata(
            "mp3", tuple(tags), pictures, problem="no MPEG audio frame found"
        )
    version, rate_index = (window[sync + 1] >> 3) & 3, (window[sync + 2] >> 2) & 3
    mono = (window[sync + 3] >> 6) == 3
    if version not in _MPEG_RATES or rate_index == 3:
        return DerivedMetadata(
            "mp3", tuple(tags), pictures, problem="a bad MPEG header"
        )
    rate = _MPEG_RATES[version][rate_index]
    side = (17 if mono else 32) if version == 3 else (9 if mono else 17)
    per_frame = 1152 if version == 3 else 576
    xing = sync + 4 + side
    if window[xing : xing + 4] not in (b"Xing", b"Info"):
        return DerivedMetadata(
            "mp3", tuple(tags), pictures, sample_rate=rate,
            problem="no Xing/Info header, so the length is not determined",
        )  # fmt: skip
    xing_flags = int.from_bytes(window[xing + 4 : xing + 8], "big")
    if not xing_flags & 1:
        return DerivedMetadata(
            "mp3", tuple(tags), pictures, sample_rate=rate,
            problem="the Xing header carries no frame count",
        )  # fmt: skip
    frames = int.from_bytes(window[xing + 8 : xing + 12], "big")
    lame = xing + 8 + 4 * bool(xing_flags & 1) + 4 * bool(xing_flags & 2)
    lame += 100 * bool(xing_flags & 4) + 4 * bool(xing_flags & 8)
    gaps = window[lame + 21 : lame + 24]
    samples = frames * per_frame
    exact = len(gaps) == 3 and window[lame : lame + 4].isalpha()
    if exact:
        joined = int.from_bytes(gaps, "big")
        samples = max(0, samples - (joined >> 12) - (joined & 0xFFF))
    if xing_flags & 2:  # the stream's byte count: a file cut short holds less
        claimed = int.from_bytes(window[xing + 12 : xing + 16], "big")
        held = handle.seek(0, 2) - audio_start - sync
        if 0 < held < claimed:
            samples, exact = samples * held // claimed, False
    return DerivedMetadata("mp3", tuple(tags), pictures, samples, rate, exact=exact)


def _read_wavpack(handle: BinaryIO, head: bytes) -> DerivedMetadata:
    block = head + handle.read(20)
    if len(block) < 32:
        return DerivedMetadata("wavpack", problem="the file ends inside its header")
    total = int.from_bytes(block[12:16], "little")
    samples = None if total == 0xFFFFFFFF else (block[11] << 32) | total
    held = _wavpack_samples_held(handle)
    if samples is not None and held < samples:
        samples = held  # the header was written whole; the blocks were not
    flags = int.from_bytes(block[24:28], "little")
    index = (flags >> 23) & 0xF
    rate = _WV_RATES[index] if index < len(_WV_RATES) else None
    tags, pictures, problem = _read_ape(handle)
    return DerivedMetadata(
        "wavpack", tags, pictures, samples, rate, ((flags & 3) + 1) * 8,
        exact=samples is not None, problem=problem,
    )  # fmt: skip


def _wavpack_samples_held(handle: BinaryIO) -> int:
    """The samples the file's blocks actually hold, walking block headers.

    Only an initial block (flag 0x800) starts a new stretch of samples; a
    multichannel file's later blocks share its ``block_index``. The walk stops
    at the first header that is not ``wvpk`` (the APE tag) or that runs past
    the end of the file, so a truncated last block is not counted.
    """
    end = handle.seek(0, 2)
    position = held = 0
    for _ in range(1 << 20):
        handle.seek(position)
        block = handle.read(32)
        if len(block) < 32 or block[:4] != b"wvpk":
            break
        size = int.from_bytes(block[4:8], "little") + 8
        if size <= 8 or position + size > end:
            break
        if int.from_bytes(block[24:28], "little") & 0x800:
            held += int.from_bytes(block[20:24], "little")
        position += size
    return held


def _read_ape(handle: BinaryIO) -> tuple[tuple[tuple[str, str], ...], int, str]:
    """The APEv2 tag at the end of a file: (tags, pictures, problem)."""
    end = handle.seek(0, 2)
    handle.seek(max(0, end - 128))
    if handle.read(3) == b"TAG":  # an ID3v1 tag after the APE one
        end -= 128
    handle.seek(max(0, end - 32))
    footer = handle.read(32)
    if footer[:8] != b"APETAGEX":
        return (), 0, ""  # no tag: an accurate empty read, not a problem
    size, count = struct.unpack("<II", footer[12:20])
    if size > MAX_TAG_BYTES or size < 32 or size > end:
        return (), 0, f"the APE tag claims {size} bytes"
    handle.seek(end - size)
    body = handle.read(size - 32)
    tags: list[tuple[str, str]] = []
    pictures = 0
    position = 0
    for _ in range(min(count, 4096)):
        if position + 8 > len(body):
            return tuple(tags), pictures, "the APE tag ends inside an item"
        length, item_flags = struct.unpack("<II", body[position : position + 8])
        key_end = body.find(b"\x00", position + 8)
        if key_end < 0:
            return tuple(tags), pictures, "an APE item has no key terminator"
        key = body[position + 8 : key_end].decode("latin-1")
        value = body[key_end + 1 : key_end + 1 + length]
        position = key_end + 1 + length
        if (item_flags >> 1) & 3:
            pictures += 1  # binary (a picture) or an external reference
            continue
        name = _APE_ALIASES.get(normalise_key(key), key)
        tags.extend((name, text) for text in _text(value, "utf-8"))
    return tuple(tags), pictures, ""


def _read_wav(handle: BinaryIO) -> DerivedMetadata:
    tags: list[tuple[str, str]] = []
    rate = bits = align = None
    data_bytes = None
    for _ in range(MAX_CHUNKS):
        header = handle.read(8)
        if len(header) < 8:
            break
        chunk, size = header[:4], int.from_bytes(header[4:8], "little")
        if chunk == b"fmt ":
            fmt = handle.read(size)
            _channels, rate, _rate_bytes, align, bits = struct.unpack(
                "<HIIHH", fmt[2:16]
            )
        elif chunk == b"LIST" and size <= MAX_TAG_BYTES:
            body = handle.read(size)
            position = 4 if body[:4] == b"INFO" else len(body)
            while position + 8 <= len(body):
                sub, length = (
                    body[position : position + 4],
                    int.from_bytes(body[position + 4 : position + 8], "little"),
                )
                value = body[position + 8 : position + 8 + length]
                position += 8 + length + (length & 1)
                if sub in _INFO_NAMES:
                    tags.extend((_INFO_NAMES[sub], t) for t in _text(value, "utf-8"))
        else:
            if chunk == b"data":
                # What the file HOLDS, not what its header claims: a WAV cut
                # short keeps the header ffmpeg wrote before the audio.
                here = handle.tell()
                data_bytes = min(size, max(0, handle.seek(0, 2) - here))
                handle.seek(here)
            handle.seek(size, 1)
        if size & 1:
            handle.seek(1, 1)
    if data_bytes is None or not align or rate is None:
        return DerivedMetadata(
            "wav", tuple(tags), problem="no fmt or data chunk, so the length is unknown"
        )
    return DerivedMetadata(
        "wav", tuple(tags), 0, data_bytes // align, rate, bits, exact=True
    )
