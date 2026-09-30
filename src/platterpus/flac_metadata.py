"""Read a FLAC file's tags and embedded pictures, without any external tool.

**Why this exists.** The acceptance run rips eight albums and, until this module,
never opened one of the files it made to ask whether the tags on it were the
ones the user chose. The report records what we *sent* the ripper and what our
tagging pass *attempted*; neither is the file. A title that lost its colon, or a
cover that was embedded into eleven files of fourteen, is only visible by reading
the FLAC itself — which is what a music library does, and what the user sees.

**Why not ``metaflac``.** It is the tool our own tagging pass uses to *write*, so
reading back through it would check the file with the same program that wrote it
(``CLAUDE.md``: *two implementations agreeing is not either one being correct*).
It would also be a subprocess, and the acceptance runner's verbs run on the GUI
thread (rule: never block it). The FLAC metadata layout is small and fixed, and
:func:`platterpus.checksums.flac_unencoded_md5` already reads its first block the
same way for the same reasons: it cannot fail because a tool is missing.

The layout, from the FLAC format specification (RFC 9639 §8):

* the four bytes ``fLaC``, then metadata blocks until one is flagged *last*;
* each block has a 4-byte header: bit 7 of the first byte is the *last* flag,
  bits 0-6 the block type, and the next three bytes the payload length;
* type 4, ``VORBIS_COMMENT``: a vendor string, then ``KEY=VALUE`` comments, every
  length a **little-endian** 32-bit number (Vorbis's own convention);
* type 6, ``PICTURE``: a picture type, MIME type, description, four image
  numbers and the image bytes, every number **big-endian** (FLAC's convention).

**It never raises.** The input is a file on disk that another program wrote and
that may be truncated, empty or not a FLAC at all (a killed rip leaves 0-byte
files — handshake round 4, Q9). Every way of not reading it cleanly is a
:attr:`FlacMetadata.problem` sentence, and a caller reads *that* rather than
catching anything. A "never raises" property test holds it to that.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final

log = logging.getLogger(__name__)

_FLAC_MAGIC: Final[bytes] = b"fLaC"
_ID3_MAGIC: Final[bytes] = b"ID3"
_BLOCK_VORBIS_COMMENT: Final[int] = 4
_BLOCK_PICTURE: Final[int] = 6
#: The only reserved "invalid" block type (RFC 9639 §8.1). Meeting it means the
#: bytes are not a metadata block, so reading stops rather than guessing.
_BLOCK_INVALID: Final[int] = 127

#: Bounds, so a corrupt length field cannot make us read a gigabyte or loop for
#: ever. Real files are far inside them: a tagged track has a handful of blocks
#: and a few dozen comments, and a cover image is well under 16 MiB.
MAX_BLOCKS: Final[int] = 256
MAX_COMMENTS: Final[int] = 4096
MAX_COMMENT_BYTES: Final[int] = 1 << 20
MAX_VORBIS_BLOCK_BYTES: Final[int] = 16 << 20

#: The picture type the FLAC spec gives a front cover (RFC 9639 §8.8, table 13),
#: which is what our tagging pass embeds.
PICTURE_FRONT_COVER: Final[int] = 3


@dataclass(frozen=True)
class FlacPicture:
    """One embedded picture: what it claims to be, and how many bytes it holds."""

    picture_type: int
    mime: str
    data_bytes: int


@dataclass(frozen=True)
class FlacMetadata:
    """What one FLAC file's metadata blocks say.

    ``problem`` is empty when every block was read to the *last* flag; otherwise
    it says why reading stopped, and the fields hold whatever was read before it.
    A non-empty ``problem`` is **not determined**, never a clean read with fewer
    tags — a caller grading tags must say so rather than compare a partial list.
    """

    is_flac: bool
    comments: tuple[tuple[str, str], ...] = ()
    pictures: tuple[FlacPicture, ...] = ()
    vendor: str = ""
    problem: str = ""

    def values(self, key: str) -> list[str]:
        """Every value stored under ``key``, in file order.

        Vorbis comment names are case-insensitive (the Vorbis I specification,
        §5.2.1), and writers disagree about case — the cyanrip fork capitalises
        every key from ``.19`` on, earlier builds did not. So the comparison is
        on :func:`normalise_key`, which also folds ``ALBUM_ARTIST`` into
        ``ALBUMARTIST``: ffmpeg writes the first spelling's metadata under the
        second name, and a reader that told them apart would miss the tag.
        """
        wanted = normalise_key(key)
        return [value for name, value in self.comments if normalise_key(name) == wanted]


def normalise_key(key: str) -> str:
    """A tag name as the comparison sees it: upper case, no ``_`` or spaces."""
    return key.upper().replace("_", "").replace(" ", "")


def _read_exact(handle: BinaryIO, count: int) -> bytes | None:
    """``count`` bytes, or ``None`` when the file ends first."""
    data = handle.read(count)
    return data if len(data) == count else None


def _skip_id3(handle: BinaryIO) -> str:
    """Step over an ID3v2 tag some writers put before ``fLaC``. Returns a problem."""
    header = _read_exact(handle, 10)
    if header is None:
        return "the file ends inside an ID3 header"
    # The size is four 7-bit bytes ("syncsafe"), excluding the 10-byte header.
    size = 0
    for byte in header[6:10]:
        size = (size << 7) | (byte & 0x7F)
    handle.seek(size, 1)
    return ""


def _parse_vorbis_comment(
    payload: bytes,
) -> tuple[str, list[tuple[str, str]], str]:
    """``(vendor, comments, problem)`` from a ``VORBIS_COMMENT`` payload."""
    comments: list[tuple[str, str]] = []
    if len(payload) < 4:
        return "", comments, "the tag block is too short to hold its vendor length"
    (vendor_length,) = struct.unpack_from("<I", payload, 0)
    offset = 4
    if vendor_length > len(payload) - offset:
        return "", comments, "the tag block's vendor string runs past the block"
    vendor = payload[offset : offset + vendor_length].decode("utf-8", "replace")
    offset += vendor_length
    if len(payload) - offset < 4:
        return vendor, comments, "the tag block ends before its comment count"
    (count,) = struct.unpack_from("<I", payload, offset)
    offset += 4
    if count > MAX_COMMENTS:
        return vendor, comments, f"the tag block claims {count} comments"
    for index in range(count):
        if len(payload) - offset < 4:
            return vendor, comments, f"the tag block ends inside comment {index + 1}"
        (length,) = struct.unpack_from("<I", payload, offset)
        offset += 4
        if length > MAX_COMMENT_BYTES or length > len(payload) - offset:
            return vendor, comments, f"comment {index + 1} runs past the tag block"
        text = payload[offset : offset + length].decode("utf-8", "replace")
        offset += length
        # A comment with no `=` is malformed by the spec; kept under an empty
        # name rather than dropped, so a count of comments stays honest.
        name, _, value = text.partition("=")
        comments.append((name if "=" in text else "", value if "=" in text else text))
    return vendor, comments, ""


def _read_picture(handle: BinaryIO, length: int) -> tuple[FlacPicture | None, str]:
    """Read a ``PICTURE`` block's fields, SKIPPING its image bytes."""
    start = handle.tell()
    head = _read_exact(handle, 8)
    if head is None:
        return None, "a picture block ends before its MIME type"
    picture_type, mime_length = struct.unpack(">II", head)
    if mime_length > length:
        return None, "a picture block's MIME type runs past the block"
    mime_raw = _read_exact(handle, mime_length)
    desc_len_raw = _read_exact(handle, 4)
    if mime_raw is None or desc_len_raw is None:
        return None, "a picture block ends inside its MIME type"
    (description_length,) = struct.unpack(">I", desc_len_raw)
    if description_length > length:
        return None, "a picture block's description runs past the block"
    handle.seek(description_length, 1)
    tail = _read_exact(handle, 20)
    if tail is None:
        return None, "a picture block ends before its image"
    (data_length,) = struct.unpack_from(">I", tail, 16)
    consumed = handle.tell() - start
    if data_length > length - consumed:
        return None, "a picture block's image runs past the block"
    handle.seek(start + length)
    mime = mime_raw.decode("ascii", "replace")
    return FlacPicture(picture_type, mime, data_length), ""


def read_flac_metadata(path: Path) -> FlacMetadata:
    """Every tag and embedded picture in ``path``. Never raises.

    Reads headers and tag text only; image bytes are skipped by seeking, so a
    large cover costs no memory.
    """
    try:
        with path.open("rb") as handle:
            return _read(handle)
    except (OSError, struct.error, ValueError) as exc:
        log.warning("could not read FLAC metadata from %s: %s", path, exc)
        return FlacMetadata(
            is_flac=False, problem=f"the file could not be read ({exc})"
        )


def _read(handle: BinaryIO) -> FlacMetadata:
    magic = handle.read(4)
    if magic[:3] == _ID3_MAGIC:
        handle.seek(0)
        skipped = _skip_id3(handle)
        if skipped:
            return FlacMetadata(is_flac=False, problem=skipped)
        magic = handle.read(4)
    if magic != _FLAC_MAGIC:
        return FlacMetadata(
            is_flac=False,
            problem="the file does not start with fLaC, so it is not a FLAC stream",
        )
    comments: list[tuple[str, str]] = []
    pictures: list[FlacPicture] = []
    vendor = ""
    problem = ""
    for _ in range(MAX_BLOCKS):
        header = _read_exact(handle, 4)
        if header is None:
            problem = "the file ends before its last metadata block"
            break
        is_last = bool(header[0] & 0x80)
        block_type = header[0] & 0x7F
        length = int.from_bytes(header[1:4], "big")
        if block_type == _BLOCK_INVALID:
            problem = "a metadata block has the reserved invalid type"
            break
        if block_type == _BLOCK_VORBIS_COMMENT:
            if length > MAX_VORBIS_BLOCK_BYTES:
                problem = f"the tag block claims {length} bytes"
                break
            payload = _read_exact(handle, length)
            if payload is None:
                problem = "the file ends inside the tag block"
                break
            vendor, found, problem = _parse_vorbis_comment(payload)
            comments.extend(found)
            if problem:
                break
        elif block_type == _BLOCK_PICTURE:
            picture, problem = _read_picture(handle, length)
            if picture is None:
                break
            pictures.append(picture)
        else:
            handle.seek(length, 1)
        if is_last:
            problem = ""
            break
    else:
        problem = f"more than {MAX_BLOCKS} metadata blocks without a last one"
    return FlacMetadata(
        is_flac=True,
        comments=tuple(comments),
        pictures=tuple(pictures),
        vendor=vendor,
        problem=problem,
    )
