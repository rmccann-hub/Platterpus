# SPDX-License-Identifier: GPL-3.0-only
"""Optional post-rip FLAC re-compression to the maximum level.

whipper encodes FLAC at the tool default (`-5`); this re-encodes each output FLAC
at `-8` (flac's `--best`) to shrink the files. It is **lossless and `--verify`'d**,
so the audio is provably bit-identical to before, and `flac` **preserves all
metadata** (Vorbis tags, embedded cover art, cuesheet) when it re-encodes a FLAC
input — so the tags whipper wrote and any art the GUI embedded survive.

Opt-in (default off) and pointless for backends that already max compression
(cyanrip), which the GUI skips. Each file is re-encoded to a sibling temp file and
then **atomically swapped in**, so a failure (or a crash) leaves the original
untouched. Best-effort; **never raises**.
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_FLAC_BINARY: str = "flac"
_LEVEL: str = "-8"  # flac --best (lossless; only the file size changes)
# A full re-encode is heavier than `--test`; give each file a generous bound.
_TIMEOUT_S: float = 300.0

Runner = Callable[[list[str]], int]


@dataclass(frozen=True)
class RecompressResult:
    """Outcome of re-compressing a set of FLAC files.

    ``reencoded`` is how many were rewritten; ``failures`` lists paths that could
    not be re-encoded (left untouched); ``error`` is set (rest empty) when the
    step could not run at all (e.g. ``flac`` missing). ``ok`` is True only when it
    ran and every file was rewritten.
    """

    reencoded: int = 0
    failures: tuple[Path, ...] = ()
    error: str = ""

    @property
    def ran(self) -> bool:
        return not self.error

    @property
    def ok(self) -> bool:
        return self.ran and not self.failures


def _default_runner(argv: list[str]) -> int:
    proc = subprocess.run(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        timeout=_TIMEOUT_S,
    )
    return proc.returncode


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def recompress_flac_files(
    paths: Sequence[Path],
    *,
    binary: str = _FLAC_BINARY,
    runner: Runner | None = None,
) -> RecompressResult:
    """Re-encode each FLAC at ``-8`` with verify; return a :class:`RecompressResult`.

    Never raises. A missing ``flac`` binary (or any failure to run it) aborts with
    ``error`` set, leaving every file untouched. A per-file failure leaves that
    original in place (the temp is discarded, never swapped in). On success each
    file is replaced atomically (``os.replace`` of a sibling temp), so the rip is
    never left with a half-written FLAC.
    """
    run = runner or _default_runner
    failures: list[Path] = []
    reencoded = 0
    for path in paths:
        tmp = path.with_name(path.name + ".recompress.tmp")
        argv = [binary, _LEVEL, "--verify", "--silent", "-f", "-o", str(tmp), str(path)]
        try:
            rc = run(argv)
        except FileNotFoundError:
            return RecompressResult(
                reencoded=reencoded,
                error=f"'{binary}' not found — cannot re-compress FLACs",
            )
        except subprocess.TimeoutExpired:
            log.warning("flac re-encode timed out on %s", path)
            _safe_unlink(tmp)
            failures.append(path)
            continue
        except OSError as exc:
            return RecompressResult(
                reencoded=reencoded, error=f"could not run {binary}: {exc}"
            )
        if rc != 0 or not tmp.exists():
            _safe_unlink(tmp)
            failures.append(path)
            continue
        try:
            os.replace(tmp, path)  # atomic swap-in (same directory)
        except OSError as exc:
            log.warning("could not swap in re-compressed %s: %s", path, exc)
            _safe_unlink(tmp)
            failures.append(path)
            continue
        reencoded += 1
    return RecompressResult(reencoded=reencoded, failures=tuple(failures))
