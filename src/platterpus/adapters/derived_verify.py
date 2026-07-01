# SPDX-License-Identifier: GPL-3.0-only
"""Post-transcode verification of the DERIVED files (MP3 / WavPack / WAV).

The FLAC master is already proven bit-perfect off the disc (AccurateRip + CTDB)
and proven to decode cleanly (``flac --test`` via ``flac_verify``). This adapter
closes the last gap: proving the files we *derived* from that master are good
too — **honestly per format**, respecting Critical Rule #4's lossless/lossy line:

  * **WavPack** (``.wv``) and **WAV** are LOSSLESS, so we prove *bit-identity*:
    decode both the derived file and its FLAC master to raw PCM and compare. If
    the PCM matches, the derived file carries exactly the disc's audio — the
    strongest guarantee there is. A mismatch is a real defect (flagged, never
    papered over).
  * **MP3** is LOSSY by design ("not for that use"), so bit-identity is
    *impossible* and comparing it to the master would be dishonest. Instead we
    prove it **decodes cleanly end-to-end** (a full decode with no error) and is
    **complete** (one MP3 per master track). The report says exactly that: MP3
    verification proves decodability + completeness, NOT bit-identity.

**One tool, no new dependency (Critical Rule #6).** Everything routes through
``ffmpeg``, which is *already* the transcode encoder — so it is guaranteed
present whenever a derived file exists (if it were missing, the transcode would
have failed and there'd be nothing to verify). We decode each file to canonical
16-bit little-endian PCM (the CD format) and SHA-256 the stream; lossless
formats compare that digest against the master's, lossy formats only require it
to exist (a successful full decode). No ``wavpack``/``wvunpack`` decoder is
added — PCM byte-compare via the tool we already have is both the definitive
lossless proof and the fewest moving parts.

Best-effort and **never raises** — the rip already succeeded, so a missing tool
or an odd file is reported as a result, never an exception into the GUI.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_FFMPEG_BINARY: str = "ffmpeg"
# A full-album decode is slower than a single track; bound it so one wedged file
# can't hang the verify thread forever.
_DECODE_TIMEOUT_S: float = 600.0
# Read the decoded PCM off ffmpeg's stdout in chunks so a whole album's PCM
# (hundreds of MB) is hashed with bounded memory, never buffered whole.
_PCM_CHUNK: int = 1 << 20  # 1 MiB

# The lossless transcode targets — the ones we can (and must) prove bit-identical
# to the FLAC master. MP3 is deliberately absent (lossy; can't and shouldn't
# match). WAV isn't tagged/arted but its PCM payload is still lossless.
_LOSSLESS_FORMATS: frozenset[str] = frozenset({"wav", "wavpack"})

# Decode a file to a PCM digest, or None if it couldn't be decoded. Injectable
# so tests never invoke a real ffmpeg.
PcmHasher = Callable[[Path], "str | None"]


@dataclass(frozen=True)
class DerivedVerifyResult:
    """Outcome of verifying a set of derived files against the FLAC masters.

    ``fmt`` is the derived format; ``lossless`` says which proof was applied
    (bit-identity vs decode-clean). ``checked`` is how many derived files were
    verified and ``expected`` how many there should have been (one per master),
    so ``checked < expected`` means the transcode was incomplete. ``failures``
    are files that could not be decoded at all (or whose master wouldn't decode,
    so no comparison was possible); ``mismatches`` are LOSSLESS files whose PCM
    differs from the master — a genuine defect. ``error`` is set (and the rest
    empty) when the check couldn't run at all (e.g. ``ffmpeg`` missing, or no
    derived files found).
    """

    fmt: str = ""
    lossless: bool = False
    checked: int = 0
    expected: int = 0
    failures: tuple[Path, ...] = ()
    mismatches: tuple[Path, ...] = ()
    error: str = ""

    @property
    def ran(self) -> bool:
        return not self.error

    @property
    def complete(self) -> bool:
        """Every master got a derived file that we verified."""
        return self.checked == self.expected and self.expected > 0

    @property
    def ok(self) -> bool:
        """Ran, verified at least one file, and nothing failed/mismatched/missing.

        For a lossless format this means every derived file is bit-identical to
        its master; for MP3 it means every one decoded cleanly and the set is
        complete. It never means "MP3 is bit-identical" — that's not claimed."""
        return self.ran and not self.failures and not self.mismatches and self.complete


def _kill_and_reap(proc: subprocess.Popen) -> None:
    """Kill a decode subprocess AND wait for it, so we never leave a zombie.

    ``kill()`` alone only sends the signal; without a ``wait()`` the child stays
    a zombie (defunct) until GC eventually reaps it — and across an album's worth
    of timeouts those would accumulate (review-confirmed leak). Bounded + guarded
    so reaping can't itself hang or raise.
    """
    try:
        proc.kill()
    except OSError:
        pass
    try:
        proc.wait(timeout=5.0)
    except Exception:  # noqa: BLE001 — reaping is best-effort; never raise
        pass


def _default_hasher(path: Path, *, binary: str = _FFMPEG_BINARY) -> str | None:
    """Decode ``path`` to canonical 16-bit LE PCM via ffmpeg and SHA-256 it.

    Returns the hex digest, or None if the file could not be decoded (missing
    binary, non-zero exit, timeout, or read error). Streams the PCM in chunks so
    a full album is hashed with bounded memory. Never raises.
    """
    argv = [
        binary,
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:a",  # audio only — ignore any embedded cover
        "-f",
        "s16le",  # canonical CD PCM: 16-bit little-endian
        "-",  # write the raw PCM to stdout
    ]
    digest = hashlib.sha256()
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError) as exc:
        log.warning("derived-verify: could not launch %s: %s", binary, exc)
        return None
    assert proc.stdout is not None
    try:
        while True:
            chunk = proc.stdout.read(_PCM_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
        rc = proc.wait(timeout=_DECODE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        log.warning("derived-verify: decode timed out on %s", path)
        _kill_and_reap(proc)
        return None
    except OSError as exc:
        log.warning("derived-verify: decode read failed on %s: %s", path, exc)
        _kill_and_reap(proc)
        return None
    finally:
        proc.stdout.close()
    if rc != 0:
        return None
    return digest.hexdigest()


def verify_derived_files(
    pairs: Sequence[tuple[Path, Path]],
    *,
    fmt: str,
    expected: int | None = None,
    hasher: PcmHasher | None = None,
) -> DerivedVerifyResult:
    """Verify each ``(derived, master)`` pair per ``fmt``; return a result.

    ``pairs`` maps each derived file to the FLAC master it was made from.
    ``expected`` is how many masters there are (defaults to ``len(pairs)``); a
    smaller ``len(pairs)`` means some masters had no derived file (incomplete
    transcode). ``hasher`` is injected in tests; production decodes via ffmpeg.

    Lossless formats (WAV/WavPack) require the derived PCM to equal the master's
    (proof of bit-identity); MP3 only requires the derived file to decode
    cleanly (proof of decodability, since a lossy file can't match the master).
    Never raises — a decode that can't run marks the file, never throws.
    """
    lossless = fmt in _LOSSLESS_FORMATS
    total_expected = expected if expected is not None else len(pairs)
    hash_fn = hasher or _default_hasher
    if not pairs:
        return DerivedVerifyResult(
            fmt=fmt,
            lossless=lossless,
            expected=total_expected,
            error=f"no {fmt} files found to verify",
        )

    failures: list[Path] = []
    mismatches: list[Path] = []
    checked = 0
    for derived, master in pairs:
        try:
            derived_hash = hash_fn(derived)
        except Exception:  # noqa: BLE001 — a verifier must never crash the GUI
            log.exception("derived-verify: hashing %s crashed", derived)
            derived_hash = None
        if derived_hash is None:
            # Couldn't decode the derived file at all → failed verification.
            failures.append(derived)
            continue
        if not lossless:
            # MP3 (lossy): a clean full decode is all we can honestly assert.
            checked += 1
            continue
        # Lossless: prove bit-identity against the master's PCM.
        try:
            master_hash = hash_fn(master)
        except Exception:  # noqa: BLE001 — never crash the GUI
            log.exception("derived-verify: hashing master %s crashed", master)
            master_hash = None
        if master_hash is None:
            # Can't compare if the master won't decode — report as a failure to
            # verify (not a mismatch: we don't know the derived is wrong).
            failures.append(derived)
            continue
        checked += 1
        if derived_hash != master_hash:
            mismatches.append(derived)
    return DerivedVerifyResult(
        fmt=fmt,
        lossless=lossless,
        checked=checked,
        expected=total_expected,
        failures=tuple(failures),
        mismatches=tuple(mismatches),
    )
