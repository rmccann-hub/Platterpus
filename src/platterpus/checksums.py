"""Per-file SHA256 digests — a long-term integrity record for a rip.

The ``.log`` carries EAC-style CRC32s that prove *bit-perfection at rip time*.
SHA256 digests answer a different question: **has anything changed since?** —
bit-rot, a bad disk, or a careless re-tag years later. They complement (don't
replace) the AccurateRip/CTDB rip-time proof.

Per the maintainer's "one debug file" rule, these digests are **embedded in the
`.platterpus.json` report**, not written as a separate `checksums.sha256`
sidecar — the only files a rip leaves are the EAC-compliant ``.log``, the
``.cue``, and that one JSON. To verify later, a digest can be re-computed with
:func:`sha256_file` (or the value pasted into any SHA256 checker).

Pure and never-raises: a hashing/IO error on one file is recorded against that
file rather than aborting — a partial record still protects the files it could
read.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from platterpus import rip_files

# Audio extensions we fingerprint — the FLAC master plus every format the
# transcode adapter can derive. Lower-cased; matched case-insensitively.
_AUDIO_SUFFIXES: frozenset[str] = frozenset({".flac", ".mp3", ".wav", ".wv", ".m4a"})

# Read files in 1 MiB chunks so a long album never loads a whole track into RAM.
_CHUNK: int = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Return the hex SHA256 of `path`, streaming it in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def audio_files(rip_dir: Path) -> list[Path]:
    """Every audio file under `rip_dir`, sorted, for a stable digest order.

    The unscoped folder scan. :func:`compute_digests` no longer calls this
    directly — it asks :mod:`platterpus.rip_files` which files *this rip* wrote,
    and that module uses a scan like this one only as its logged fallback. Kept
    public because "everything audio under this folder" is still a useful,
    honestly-named question for callers that mean exactly that.
    """
    try:
        return sorted(
            p
            for p in rip_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in _AUDIO_SUFFIXES
        )
    except OSError:
        # A missing/unreadable directory yields no files rather than raising —
        # this backs a best-effort report section, never a gate.
        return []


def compute_digests(rip_dir: Path) -> dict[str, str]:
    """Map each audio file (relative POSIX path) to its SHA256, for the report.

    Scoped to the files THIS rip produced — its FLAC masters plus whatever was
    derived from them — via :mod:`platterpus.rip_files`, not to everything audio
    in the folder. The manifest is the report's own integrity record, so
    fingerprinting a leftover from an earlier cancelled rip would attest to a
    file this rip never wrote. When no rip log can scope it, rip_files falls back
    to the full folder scan and logs that it did.

    Never raises: a file that can't be read maps to ``"unreadable: <error>"``
    instead of aborting the whole set. Streams each file, so it's safe on large
    albums — but it still does real disk I/O, so callers must run it OFF the GUI
    thread (it's invoked from the post-rip worker, after any transcode, so the
    derived files are included too).
    """
    digests: dict[str, str] = {}
    for path in rip_files.rip_audio_files(rip_dir).files:
        rel = path.relative_to(rip_dir).as_posix()
        try:
            digests[rel] = sha256_file(path)
        except OSError as exc:
            digests[rel] = f"unreadable: {exc}"
    return digests


#: A FLAC ``STREAMINFO`` block is always the first metadata block, is exactly 34
#: bytes of payload, and its last 16 bytes are the MD5 of the **unencoded** audio.
#: An all-zero value is the spec's "not computed", which is a real answer and must
#: never be reported as a digest.
_FLAC_MAGIC: bytes = b"fLaC"
_STREAMINFO_PAYLOAD_BYTES: int = 34
_ZERO_MD5: str = "0" * 32


def flac_unencoded_md5(path: Path) -> str | None:
    """The MD5 of a FLAC's decoded audio, read from its own ``STREAMINFO``.

    **Why this exists alongside :func:`sha256_file`.** That function digests the
    *container*, which is the right tool for "has this file changed on disk" and
    the wrong one for "is this the same audio": writing a tag rewrites the
    container and invalidates the SHA256 while the audio is untouched. Every FLAC
    already carries an MD5 of its decoded samples, computed by the encoder — so a
    **retag-surviving audio identity** is available for free and we were not
    recording it. EAC records nothing comparable.

    Parsed here rather than shelled out to ``metaflac --show-md5sum`` on purpose:
    it is 20 lines of header reading, it cannot fail because a tool is missing,
    and it keeps this module dependency-free so the report can always carry the
    field.

    Returns ``None`` — never a guess — when the file is not a FLAC, is truncated,
    or records the all-zero "not computed" value. ``None`` means *not determined*,
    which is a different fact from a digest that failed to match.
    """
    try:
        with path.open("rb") as handle:
            if handle.read(4) != _FLAC_MAGIC:
                return None
            header = handle.read(4)
            if len(header) < 4:
                return None
            # Bits 1-7 of the first header byte are the block type; STREAMINFO is
            # 0 and the spec requires it first, so anything else means this is not
            # a FLAC stream we understand rather than a FLAC with an odd layout.
            if header[0] & 0x7F != 0:
                return None
            if int.from_bytes(header[1:4], "big") != _STREAMINFO_PAYLOAD_BYTES:
                return None
            payload = handle.read(_STREAMINFO_PAYLOAD_BYTES)
            if len(payload) < _STREAMINFO_PAYLOAD_BYTES:
                return None
    except OSError:
        # Same contract as the rest of this module: a best-effort report section
        # never raises, and an unreadable file is "not determined".
        return None
    digest = payload[18:34].hex()
    return None if digest == _ZERO_MD5 else digest


def unencoded_audio_digests(rip_dir: Path) -> dict[str, str]:
    """Map each FLAC this rip produced to its decoded-audio MD5.

    Same scoping as :func:`compute_digests` — the files THIS rip wrote — so the
    two maps can be read side by side. Non-FLAC outputs (MP3, WAV, WavPack) are
    absent rather than present-and-empty: a key whose value is a placeholder is
    the silent-truncation shape, and the caller can tell "no entry" from
    "entry we could not compute" because the latter never appears.

    Cheap by comparison with the SHA256 pass — it reads 42 bytes per file rather
    than streaming the whole thing — but it is still disk I/O and belongs off the
    GUI thread with its sibling.
    """
    digests: dict[str, str] = {}
    for path in audio_files(rip_dir):
        if path.suffix.lower() != ".flac":
            continue
        digest = flac_unencoded_md5(path)
        if digest is not None:
            try:
                key = path.relative_to(rip_dir).as_posix()
            except ValueError:
                key = path.name
            digests[key] = digest
    return digests
