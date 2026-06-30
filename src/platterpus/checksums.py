"""Per-file SHA256 manifest — a long-term integrity record for a rip.

The ``.log`` already carries EAC-style CRC32s that prove *bit-perfection at rip
time*. A SHA256 manifest answers a different question: **has anything changed
since?** Years later, bit-rot, a bad disk, or a careless re-tag can corrupt a
file; comparing the files against this manifest (``sha256sum -c
checksums.sha256``) catches that. It's standard archival practice and complements
— doesn't replace — the AccurateRip/CTDB rip-time verification.

The manifest lists every audio file beside the FLACs (the FLAC masters *and* any
derived MP3/WavPack/WAV), in the standard ``<hex>␠␠<relpath>`` format
``sha256sum`` reads. Pure and never-raises: a hashing/IO error on one file is
recorded as a comment line rather than aborting the manifest (it backs an
archival guarantee, not a gate — a partial manifest still protects the files it
could read).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

# Audio extensions we fingerprint — the FLAC master plus every format the
# transcode adapter can derive. Lower-cased; matched case-insensitively.
_AUDIO_SUFFIXES: frozenset[str] = frozenset(
    {".flac", ".mp3", ".wav", ".wv", ".m4a"}
)

# The sidecar filename, in the album folder beside the audio.
MANIFEST_NAME: str = "checksums.sha256"

# Read files in 1 MiB chunks so a long album never loads a whole track into RAM.
_CHUNK: int = 1024 * 1024


@dataclass(frozen=True)
class ManifestResult:
    """Outcome of writing a manifest. `error` is set only on a fatal failure
    (e.g. the directory couldn't be written); per-file read errors are counted
    in `failed` and noted as comments in the file, not raised."""

    path: Path | None = None
    hashed: int = 0
    failed: int = 0
    error: str = ""
    failures: tuple[str, ...] = field(default_factory=tuple)


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
    """Every audio file under `rip_dir`, sorted, for a stable manifest order."""
    return sorted(
        p
        for p in rip_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _AUDIO_SUFFIXES
    )


def write_manifest(rip_dir: Path) -> ManifestResult:
    """Write ``checksums.sha256`` for every audio file under `rip_dir`.

    Never raises: a per-file read error becomes a ``# <name>: <error>`` comment
    and increments `failed`; only an inability to enumerate or write the
    manifest itself yields a result with `error` set. Paths are written relative
    to `rip_dir` so the manifest is portable (matches ``sha256sum``'s default).
    """
    try:
        files = audio_files(rip_dir)
    except OSError as exc:
        return ManifestResult(error=f"could not list {rip_dir}: {exc}")

    lines: list[str] = []
    hashed = 0
    failures: list[str] = []
    for path in files:
        rel = path.relative_to(rip_dir).as_posix()
        try:
            digest = sha256_file(path)
        except OSError as exc:
            failures.append(rel)
            lines.append(f"# {rel}: unreadable ({exc})")
            continue
        # Two spaces + filename is the exact format `sha256sum -c` expects.
        lines.append(f"{digest}  {rel}")
        hashed += 1

    manifest_path = rip_dir / MANIFEST_NAME
    try:
        manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        return ManifestResult(
            error=f"could not write {manifest_path}: {exc}",
            hashed=hashed,
            failed=len(failures),
            failures=tuple(failures),
        )
    return ManifestResult(
        path=manifest_path,
        hashed=hashed,
        failed=len(failures),
        failures=tuple(failures),
    )
