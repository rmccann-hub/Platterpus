"""`flac_metadata` reads tags and pictures from a FLAC's own blocks, and never raises.

The files here are SYNTHETIC and header-only: a ``fLaC`` marker, a STREAMINFO
block and whatever tag or picture blocks a test needs, built by
:func:`build_flac` in the test's own temporary directory. There is no audio in
them and nothing is committed (Critical rule #8); what is being tested is the
metadata layout, which is the part a music library reads.
"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.flac_metadata import (
    PICTURE_FRONT_COVER,
    normalise_key,
    read_flac_metadata,
)


def _block(block_type: int, payload: bytes, *, last: bool) -> bytes:
    return (
        bytes([(0x80 if last else 0) | block_type])
        + len(payload).to_bytes(3, "big")
        + payload
    )


def vorbis_payload(comments: list[str], vendor: str = "test vendor") -> bytes:
    """A VORBIS_COMMENT payload: little-endian lengths, per the Vorbis spec."""
    out = struct.pack("<I", len(vendor.encode())) + vendor.encode()
    out += struct.pack("<I", len(comments))
    for comment in comments:
        raw = comment.encode("utf-8")
        out += struct.pack("<I", len(raw)) + raw
    return out


def picture_payload(
    picture_type: int = PICTURE_FRONT_COVER, data: bytes = b"\xff\xd8jpeg"
) -> bytes:
    """A PICTURE payload: big-endian numbers, per the FLAC spec."""
    mime = b"image/jpeg"
    description = b""
    return (
        struct.pack(">II", picture_type, len(mime))
        + mime
        + struct.pack(">I", len(description))
        + description
        + struct.pack(">IIIII", 1, 1, 24, 0, len(data))
        + data
    )


def build_flac(
    path: Path,
    comments: list[str] | None = None,
    pictures: list[bytes] | None = None,
    *,
    id3: bool = False,
) -> Path:
    """Write a header-only FLAC with the given tags and pictures."""
    blocks: list[tuple[int, bytes]] = [(0, bytes(34))]  # STREAMINFO first, as required
    if comments is not None:
        blocks.append((4, vorbis_payload(comments)))
    for picture in pictures or []:
        blocks.append((6, picture))
    body = b"fLaC" + b"".join(
        _block(kind, payload, last=index == len(blocks) - 1)
        for index, (kind, payload) in enumerate(blocks)
    )
    if id3:
        tag = b"ID3\x03\x00\x00" + bytes([0, 0, 0, 5]) + b"xxxxx"
        body = tag + body
    path.write_bytes(body)
    return path


def test_tags_and_a_front_cover_are_read(tmp_path: Path) -> None:
    path = build_flac(
        tmp_path / "t.flac",
        ["ALBUM=full acceptance: angle<bracket", "TITLE=E=MC2: Rock 'n' Roll \\ 2"],
        [picture_payload()],
    )
    meta = read_flac_metadata(path)
    assert meta.is_flac and meta.problem == ""
    assert meta.values("album") == ["full acceptance: angle<bracket"]
    # The value keeps every `=` after the first: only the NAME ends at `=`.
    assert meta.values("TITLE") == ["E=MC2: Rock 'n' Roll \\ 2"]
    assert [(p.picture_type, p.mime, p.data_bytes) for p in meta.pictures] == [
        (PICTURE_FRONT_COVER, "image/jpeg", 6)
    ]


def test_key_spelling_is_folded_the_way_writers_disagree(tmp_path: Path) -> None:
    """ffmpeg writes `album_artist` as ALBUMARTIST; the fork capitalises from .19."""
    path = build_flac(tmp_path / "t.flac", ["album_artist=A", "AlbumArtist=B"])
    assert read_flac_metadata(path).values("ALBUMARTIST") == ["A", "B"]
    assert (
        normalise_key("Album Artist") == normalise_key("ALBUM_ARTIST") == "ALBUMARTIST"
    )


def test_an_id3_prefix_is_stepped_over(tmp_path: Path) -> None:
    path = build_flac(tmp_path / "t.flac", ["TITLE=x"], id3=True)
    assert read_flac_metadata(path).values("TITLE") == ["x"]


def test_a_file_that_is_not_flac_says_so(tmp_path: Path) -> None:
    path = tmp_path / "t.flac"
    path.write_bytes(b"")  # the 0-byte file a killed rip leaves (round 4, Q9)
    meta = read_flac_metadata(path)
    assert not meta.is_flac and "fLaC" in meta.problem


def test_a_missing_file_is_a_problem_not_an_exception(tmp_path: Path) -> None:
    meta = read_flac_metadata(tmp_path / "absent.flac")
    assert not meta.is_flac and "could not be read" in meta.problem


def test_a_truncated_tag_block_is_not_a_clean_read(tmp_path: Path) -> None:
    """A partial list of tags must never read as the whole list."""
    path = build_flac(tmp_path / "t.flac", ["TITLE=x", "ARTIST=y"])
    path.write_bytes(path.read_bytes()[:-5])
    meta = read_flac_metadata(path)
    assert meta.problem, "a truncated file was read as clean"


def test_a_file_that_never_flags_its_last_block_is_a_problem(tmp_path: Path) -> None:
    path = tmp_path / "t.flac"
    path.write_bytes(b"fLaC" + _block(0, bytes(34), last=False))
    assert "ends before its last metadata block" in read_flac_metadata(path).problem


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(st.binary(max_size=600), st.booleans())
def test_it_never_raises_on_any_bytes(data: bytes, with_magic: bool) -> None:
    """The input is a file another program wrote: every shape must be an answer."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "x.flac"
        path.write_bytes((b"fLaC" if with_magic else b"") + data)
        meta = read_flac_metadata(path)
    assert isinstance(meta.problem, str)
    assert meta.is_flac or meta.problem
