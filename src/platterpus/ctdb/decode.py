# SPDX-License-Identifier: GPL-3.0-only
"""Decode ripped FLACs to raw PCM, and read FLAC sample counts.

CTDB's match CRC is computed over the disc's decoded audio, so we need PCM on
the host. Per the user's decision (2026-06-03) we use the host `flac` binary
**if present** and degrade with a clear message if it isn't — no required new
dependency. `metaflac` (already a project dependency) gives us per-file sample
counts for TOC/lead-out math.

Both tools are resolved to absolute paths (a desktop-launched GUI has a minimal
PATH) and invoked via argument lists (never a shell). Runners are injectable so
tests never shell out.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

# Decode timeout per file — a full track is seconds of work; the cap just stops
# a wedged decoder from hanging the caller.
_DECODE_TIMEOUT_S: float = 120.0
_PROBE_TIMEOUT_S: float = 15.0

# Injectable subprocess runner: argv -> CompletedProcess. Default runs for real.
Runner = Callable[[list[str]], "subprocess.CompletedProcess[bytes]"]


class DecoderUnavailable(RuntimeError):
    """Raised when no FLAC decoder is available on the host.

    The caller turns this into a "local CRC unavailable — install `flac`"
    verdict rather than a crash, so CTDB lookup still works without a decoder.
    """


def _which(name: str) -> str | None:
    """Resolve `name` on PATH, then common absolute locations (minimal PATH)."""
    found = shutil.which(name)
    if found:
        return found
    # ~/.local/bin FIRST: that is where distrobox-export puts the container's
    # flac/metaflac, and it was the one directory this list omitted (audit,
    # 2026-07-28) — so a desktop-launched AppImage decided they were missing.
    for candidate in (
        str(Path.home() / ".local" / "bin" / name),
        f"/usr/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/bin/{name}",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def _stderr_tail(stderr: str | bytes | None, lines: int = 3) -> str:
    """The last few lines of a tool's stderr, as one loggable string.

    WHY (CLAUDE.md, "validate every dependency output"): when `flac`/`metaflac`
    fails, its stderr is the ONLY thing that says why — a missing file, a corrupt
    stream, a permissions problem all look identical from the exit code alone. So
    it must reach both the log and the exception message; it used to be dropped
    outright for `metaflac`, which made a decode failure undiagnosable.

    Accepts str or bytes because the two runners here differ (`flac` is run in
    binary mode to keep the PCM on stdout intact; `metaflac` in text mode), and
    never raises — undecodable bytes are replaced, not fatal.
    """
    if not stderr:
        return ""
    text = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
    tail = text.strip().splitlines()[-lines:]
    return " / ".join(part.strip() for part in tail if part.strip())


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv, capture_output=True, timeout=_DECODE_TIMEOUT_S, check=False
    )


def flac_available() -> bool:
    """True if a host `flac` decoder can be found.

    Note (Critical Rule #6): the *user-facing* "is flac present + install it"
    logic lives in the dependency subsystem (`deps/registry.py` registers
    `flac` as optional, probed by `deps/checks.check_flac`). The `_which` here
    is the runner's path resolution — we need the actual binary path to invoke
    it — exactly the same split as `check_metaflac` (probe) vs the metaflac
    adapter (run). This isn't a scattered availability check.
    """
    return _which("flac") is not None


def decode_flac_to_pcm(path: Path, runner: Runner | None = None) -> bytes:
    """Decode one FLAC to headerless little-endian 16-bit stereo PCM.

    Uses `flac -d --force-raw-format --endian=little --sign=signed -c <file>`,
    which writes raw PCM to stdout. Raises `DecoderUnavailable` if `flac` is
    missing, or `RuntimeError` if the decode fails.
    """
    flac = _which("flac")
    if flac is None:
        raise DecoderUnavailable("the `flac` decoder is not installed on the host")
    run = runner or _default_runner
    argv = [
        flac,
        "-d",
        "-s",
        "--force-raw-format",
        "--endian=little",
        "--sign=signed",
        "-c",
        str(path),
    ]
    proc = run(argv)
    if proc.returncode != 0:
        detail = _stderr_tail(proc.stderr) or f"rc={proc.returncode}"
        # Log as well as raise: the caller turns the exception into a one-line
        # verdict, so without this the tool's own words never reach the log file.
        log.warning(
            "flac decode failed on %s (rc=%s): %s", path.name, proc.returncode, detail
        )
        raise RuntimeError(f"flac decode failed on {path.name}: {detail}")
    return proc.stdout or b""


# --- metaflac sample-count probe -------------------------------------------

ProbeRunner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _default_probe_runner(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=_PROBE_TIMEOUT_S, check=False
    )


def total_samples(path: Path, runner: ProbeRunner | None = None) -> int:
    """Per-channel sample count of a FLAC via `metaflac --show-total-samples`."""
    metaflac = _which("metaflac")
    if metaflac is None:
        raise DecoderUnavailable("`metaflac` is not installed on the host")
    run = runner or _default_probe_runner
    proc = run([metaflac, "--show-total-samples", str(path)])
    if proc.returncode != 0:
        # metaflac's stderr used to be thrown away here, so a failed sample-count
        # probe surfaced as the bare, unactionable "metaflac failed on 01.flac".
        # Carry the tool's own words into BOTH the log and the exception message —
        # the caller (ctdb/verify.py) puts that message in the user-visible
        # verdict, so this is the only route the reason has to the user.
        detail = _stderr_tail(proc.stderr) or "no stderr output"
        log.warning(
            "metaflac --show-total-samples failed on %s (rc=%s): %s",
            path.name,
            proc.returncode,
            detail,
        )
        raise RuntimeError(
            f"metaflac failed on {path.name} (rc={proc.returncode}): {detail}"
        )
    text = (proc.stdout or "").strip()
    try:
        return int(text)
    except ValueError as exc:
        # A zero exit with unusable stdout is just as undiagnosable — log what we
        # actually got (stdout AND any stderr) before turning it into a verdict.
        stderr_detail = _stderr_tail(proc.stderr)
        log.warning(
            "metaflac --show-total-samples gave unparseable output for %s: %r%s",
            path.name,
            text,
            f" (stderr: {stderr_detail})" if stderr_detail else "",
        )
        raise RuntimeError(f"unparseable metaflac output: {text!r}") from exc
