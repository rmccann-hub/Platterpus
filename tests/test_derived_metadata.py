"""`derived_metadata`: an MP3's, WavPack's or WAV's tags, pictures and length.

The files here are built byte by byte from each format's layout, never encoded:
no audio enters the repository or a test (Critical rule #8), and the suite does
not need ffmpeg. One test checks the reader against ffmpeg's real output when
ffmpeg is on the machine, so the hand-built layouts are not only our belief
about the formats. The builders are imported by the grader tests.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.checksums import flac_total_samples
from platterpus.derived_metadata import read_derived_metadata

RATE = 44100


def _id3_frame(frame_id: str, text: str) -> bytes:
    payload = b"\x03" + text.encode("utf-8") + b"\x00"
    return frame_id.encode() + struct.pack(">I", len(payload)) + b"\x00\x00" + payload


def build_mp3(
    path: Path, tags: dict[str, str], samples: int, *, pictures: int = 0
) -> Path:
    """An ID3v2.3 tag, then one MPEG-1 layer III frame carrying ffmpeg's
    `Info` header (frames, bytes, TOC, quality, then the encoder string with
    its delay and padding 21 bytes in), then filler standing for the frames."""
    names = {
        "TITLE": "TIT2",
        "ARTIST": "TPE1",
        "ALBUM": "TALB",
        "ALBUMARTIST": "TPE2",
        "TRACKNUMBER": "TRCK",
    }
    frames = b"".join(_id3_frame(names[k], v) for k, v in tags.items())
    for _ in range(pictures):
        apic = b"\x00image/jpeg\x00\x03\x00\xff\xd8jpeg"
        frames += b"APIC" + struct.pack(">I", len(apic)) + b"\x00\x00" + apic
    size = len(frames)
    syncsafe = bytes([(size >> s) & 0x7F for s in (21, 14, 7, 0)])
    tag = b"ID3\x03\x00\x00" + syncsafe + frames
    delay, padding = 576, (-(samples + 576)) % 1152
    count = (samples + delay + padding) // 1152
    stream = 417 * (count + 1)
    info = b"Info" + struct.pack(">III", 0x0F, count, stream) + bytes(100) + bytes(4)
    lame = b"Lavc60.31" + bytes(12) + ((delay << 12) | padding).to_bytes(3, "big")
    first = b"\xff\xfb\x50\x00" + bytes(32) + info + lame
    path.write_bytes(tag + first + bytes(stream - len(first)))
    return path


def build_wav(path: Path, samples: int, tags: dict[bytes, str] | None = None) -> Path:
    """RIFF/WAVE: 16-bit stereo `fmt `, an optional LIST/INFO, then `data`."""
    fmt = struct.pack("<HHIIHH", 1, 2, RATE, RATE * 4, 4, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if tags:
        info = b"INFO"
        for key, value in tags.items():
            raw = value.encode() + b"\x00"
            info += key + struct.pack("<I", len(raw)) + raw + b"\x00" * (len(raw) & 1)
        chunks += b"LIST" + struct.pack("<I", len(info)) + info
    chunks += b"data" + struct.pack("<I", samples * 4) + bytes(samples * 4)
    path.write_bytes(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)
    return path


def _wv_block(total: int, index: int, count: int) -> bytes:
    flags = 0x800 | 0x1000 | (9 << 23) | 1  # initial, final, 44.1 kHz, 16-bit
    body = bytes(64)
    head = b"wvpk" + struct.pack("<IHBB", 24 + len(body), 0x410, 0, 0)
    return head + struct.pack("<IIIII", total, index, count, flags, 0) + body


def build_wavpack(
    path: Path, tags: dict[str, str], samples: int, *, blocks: int = 3
) -> Path:
    """WavPack blocks (each header's total, index and count), then APEv2."""
    per = -(-samples // blocks)
    data = b"".join(
        _wv_block(samples, i * per, min(per, samples - i * per)) for i in range(blocks)
    )
    items = b""
    for key, value in tags.items():
        raw = value.encode()
        items += struct.pack("<II", len(raw), 0) + key.encode() + b"\x00" + raw
    footer = (
        b"APETAGEX"
        + struct.pack("<IIII", 2000, len(items) + 32, len(tags), 0)
        + bytes(8)
    )
    path.write_bytes(data + items + footer)
    return path


def build_master(path: Path, samples: int) -> Path:
    """A header-only FLAC whose STREAMINFO states ``samples`` at 44.1 kHz."""
    packed = (RATE << 44) | (1 << 41) | (15 << 36) | samples
    info = struct.pack(">HH", 4096, 4096) + bytes(6) + packed.to_bytes(8, "big")
    info += bytes(16)
    path.write_bytes(b"fLaC" + bytes([0x80]) + len(info).to_bytes(3, "big") + info)
    return path


_TAGS = {"TITLE": "Roxanne", "ARTIST": "A", "ALBUM": "B: c", "ALBUMARTIST": "A"}


def test_an_mp3s_tags_cover_and_exact_length_are_read(tmp_path: Path) -> None:
    meta = read_derived_metadata(
        build_mp3(tmp_path / "a.mp3", {**_TAGS, "TRACKNUMBER": "1"}, 132300, pictures=1)
    )
    assert meta.kind == "mp3" and not meta.problem
    assert meta.values("title") == ["Roxanne"] and meta.values("ALBUM") == ["B: c"]
    assert meta.pictures == 1 and meta.samples == 132300 and meta.exact


def test_a_wavpacks_tags_and_held_samples_are_read(tmp_path: Path) -> None:
    tags = {"Title": "Roxanne", "album_artist": "A", "Track": "2"}
    meta = read_derived_metadata(build_wavpack(tmp_path / "a.wv", tags, 132300))
    assert meta.kind == "wavpack" and not meta.problem
    assert meta.values("ALBUMARTIST") == ["A"] and meta.values("TRACKNUMBER") == ["2"]
    assert meta.samples == 132300 and meta.sample_rate == RATE and meta.bits == 16


def test_a_wavs_length_and_info_tags_are_read(tmp_path: Path) -> None:
    meta = read_derived_metadata(
        build_wav(tmp_path / "a.wav", 1000, {b"INAM": "Roxanne"})
    )
    assert meta.kind == "wav" and meta.samples == 1000 and meta.bits == 16
    assert meta.values("TITLE") == ["Roxanne"]


@pytest.mark.parametrize("name", ["a.mp3", "a.wv", "a.wav"])
def test_a_file_cut_short_reads_shorter_than_its_header_claims(
    tmp_path: Path, name: str
) -> None:
    """A header is written whole before the audio; the length read is what is HELD."""
    path = tmp_path / name
    if name.endswith("mp3"):
        build_mp3(path, _TAGS, 132300)
    elif name.endswith("wv"):
        build_wavpack(path, _TAGS, 132300)
    else:
        build_wav(path, 132300)
    whole = read_derived_metadata(path).samples
    data = path.read_bytes()
    path.write_bytes(data[: len(data) // 2])
    cut = read_derived_metadata(path).samples
    assert whole == 132300 and cut is not None and cut < whole * 0.9


def test_the_master_builder_states_its_length(tmp_path: Path) -> None:
    assert flac_total_samples(build_master(tmp_path / "m.flac", 132300)) == 132300


@settings(max_examples=300, deadline=None)
@given(
    prefix=st.sampled_from([b"", b"ID3\x03\x00", b"\xff\xfb", b"wvpk", b"RIFF"]),
    body=st.binary(max_size=600),
)
def test_the_reader_never_raises(
    tmp_path_factory: pytest.TempPathFactory, prefix: bytes, body: bytes
) -> None:
    path = tmp_path_factory.mktemp("d") / "x"
    path.write_bytes(
        prefix + (b"\x00\x00\x00\x00WAVE" if prefix == b"RIFF" else b"") + body
    )
    meta = read_derived_metadata(path)
    assert isinstance(meta.problem, str)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
@pytest.mark.parametrize(
    ("fmt", "args"),
    [
        ("mp3", ["-id3v2_version", "3", "-c:a", "libmp3lame", "-q:a", "2"]),
        ("wv", ["-map", "0:a", "-c:a", "wavpack"]),
        ("wav", ["-map", "0:a", "-c:a", "pcm_s16le"]),
    ],
)
def test_the_reader_agrees_with_ffmpegs_own_output(
    tmp_path: Path, fmt: str, args: list[str]
) -> None:
    """A generated tone (no recording, Critical rule #8), transcoded as we do."""
    master = tmp_path / "m.flac"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
         "sine=frequency=440:duration=3", "-ac", "2", "-ar", "44100",
         "-metadata", "TITLE=Hello", "-metadata", "ALBUMARTIST=AA", str(master)],
        check=True, timeout=60,
    )  # fmt: skip
    out = tmp_path / f"m.{fmt}"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-nostdin", "-y", "-i", str(master),
         "-map_metadata", "0", *args, "-f", "wv" if fmt == "wv" else fmt, str(out)],
        check=True, timeout=60,
    )  # fmt: skip
    meta = read_derived_metadata(out)
    assert not meta.problem and meta.samples == flac_total_samples(master)
    assert meta.values("TITLE") == ["Hello"]
    if fmt != "wav":
        assert meta.values("ALBUMARTIST") == ["AA"]
