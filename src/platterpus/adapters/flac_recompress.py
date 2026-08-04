# SPDX-License-Identifier: GPL-3.0-only
"""Optional post-rip FLAC re-compression to the maximum level.

This is only relevant historically: the old whipper backend encoded FLAC at the
tool default (`-5`), and this re-encodes each output FLAC at `-8 -e -p` (flac's
`--best` plus exhaustive model + coefficient search) to shrink the files as far as
flac can. It is **lossless and `--verify`'d**, so the audio is provably
bit-identical to before, and `flac` **preserves all metadata** (Vorbis tags,
embedded cover art, cuesheet) when it re-encodes a FLAC input — so the tags the
ripper wrote and any art the GUI embedded survive.

Opt-in (default off) and pointless for backends that already max compression —
which is exactly what the sole current backend (cyanrip) does, so the GUI skips
this entirely. Each file is re-encoded to a sibling temp file and
then **atomically swapped in**, so a failure (or a crash) leaves the original
untouched. Best-effort; **never raises**.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from platterpus.adapters.tool_run import ToolRun, ToolRunner, make_runner
from platterpus.tool_paths import resolve_tool

log = logging.getLogger(__name__)

_FLAC_BINARY: str = resolve_tool("flac")

# `-8` is flac's maximum compression *preset* (a.k.a. `--best` /
# `--compression-level-8`); per the xiph spec it expands to
# `-l 12 -b 4096 -m -r 6 -A "subdivide_tukey(3)"` (flags verified current
# against xiph.org/flac/documentation_tools_flac.html, 2026-06-23). Compression
# level is purely a file-size knob — every level is lossless, and `--verify`
# proves the decoded audio is bit-identical regardless of level, so the priority
# (bit-perfect) holds no matter what and the smaller file is the bonus.
#
# WHY THIS IS OPT-IN / OFF BY DEFAULT (the real reason, not just "modest gain"):
# higher compression raises the LPC prediction order — the `-l` setting, which
# the decoder must apply per sample. The classic encoder default is `-5` (`-l 8`)
# — what the historical whipper backend produced; `-8` is `-l 12`. A higher
# order = more multiply-accumulates per sample to DECODE, so a `-8` file costs a
# little more CPU/battery to play back. Historically (the ~2015 logic) this
# mattered on low-power portable players; on modern phones/desktops it's largely
# negligible, but it's a real reason a library aimed at mobile playback might
# prefer to leave files at the `-5` default. Both `-5` and `-8` stay inside the
# FLAC "Subset" (max LPC order 12 at <=48kHz), so this is a decode-*effort*
# difference, never a hardware-compatibility one. Net: the smaller file trades a
# touch of playback cost — hence opt-in, with `-5` the safe, mobile-friendly
# baseline.
#
# We DO add the two further-but-still-lossless options the docs list —
# `-e/--exhaustive-model-search` and `-p/--qlp-coeff-precision-search`, both
# flagged "(expensive!)". The maintainer is fine trading encode time for size
# (2026-06-23), and crucially these keep `-l` at 12, so they squeeze a bit more
# out at the cost of (much) slower *encoding* only — they add **no decode cost**,
# which is the dimension that matters for playback. The gain over plain `-8` is
# small (typically well under 1%), but it's free in every dimension we care about
# (still lossless, still `--verify`'d, no extra playback cost), so when a user has
# opted in to re-compressing at all, we go all the way. To drop back to the plain
# `-8` preset, set `_EXTRA_FLAGS = ()` — nothing else changes.
_LEVEL: str = "-8"
_EXTRA_FLAGS: tuple[str, ...] = ("-e", "-p")
# A full re-encode is heavier than `--test`, and `-e -p` make it heavier still;
# give each file a generous bound (a long track on slow hardware can take a while
# under exhaustive search). The maintainer accepts the encode time.
_TIMEOUT_S: float = 600.0

Runner = ToolRunner

_default_runner: ToolRunner = make_runner(
    timeout_s=_TIMEOUT_S,
    tool="flac (re-compress)",
    code="flac.recompress_failed",
    where="adapters.flac_recompress.recompress_flac_files",
)


@dataclass(frozen=True)
class RecompressFailure:
    """One FLAC that could not be re-compressed, **and why**.

    This step rewrites an *archival master* in place, so "it failed" without a
    reason is the least acceptable place in the program for a bare verdict: the
    reader needs to know whether the encode was refused, the swap-in was refused,
    or the tool wedged — three different recoveries.
    """

    path: Path
    #: The tool's exit code, argv and complete output for this file. ``None`` when
    #: the encode itself succeeded and the *swap-in* is what failed — in which case
    #: ``reason`` carries the OS error and there is no tool output to quote.
    run: ToolRun | None = None
    #: Set when the failure was ours rather than the tool's (an ``os.replace`` that
    #: could not complete). Never both this and a failing ``run``.
    stage_error: str = ""

    @property
    def reason(self) -> str:
        """One line a person can read. Never empty."""
        if self.stage_error:
            return self.stage_error
        return self.run.summary if self.run else "no reason recorded"

    def to_json(self) -> dict[str, object]:
        block: dict[str, object] = {"path": str(self.path), "reason": self.reason}
        if self.run is not None:
            block.update(self.run.to_json())
        return block


@dataclass(frozen=True)
class RecompressResult:
    """Outcome of re-compressing a set of FLAC files.

    ``reencoded`` is how many were rewritten; ``failures`` lists paths that could
    not be re-encoded (left untouched); ``error`` is set (rest empty) when the
    step could not run at all (e.g. ``flac`` missing). ``ok`` is True only when it
    ran and every file was rewritten.

    ``failure_details`` is ``failures`` with the tool's own words attached — one
    entry per failed path, same order.
    """

    reencoded: int = 0
    failures: tuple[Path, ...] = ()
    error: str = ""
    failure_details: tuple[RecompressFailure, ...] = field(default=())

    @property
    def ran(self) -> bool:
        return not self.error

    @property
    def ok(self) -> bool:
        return self.ran and not self.failures

    def reasons(self) -> tuple[str, ...]:
        return tuple(f"{d.path.name}: {d.reason}" for d in self.failure_details)


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
    run_cmd = runner or _default_runner
    failures: list[Path] = []
    details: list[RecompressFailure] = []
    reencoded = 0
    for path in paths:
        tmp = path.with_name(path.name + ".recompress.tmp")
        argv = [
            binary,
            _LEVEL,
            *_EXTRA_FLAGS,
            "--verify",
            "--silent",
            "-f",
            "-o",
            str(tmp),
            str(path),
        ]
        run = run_cmd(argv)
        if not run.started:
            # The binary is missing: a problem with the *pass*, not with this file.
            # `started`, not `ran` — a timeout means the tool works and wedged on
            # this input, which is handled below as a per-file failure.
            log.error(
                "flac re-compress could not run (%s) — aborting after %d file(s)",
                run.error,
                reencoded,
            )
            _safe_unlink(tmp)
            return RecompressResult(
                reencoded=reencoded,
                error=f"{run.error} — cannot re-compress FLACs",
                failures=tuple(failures),
                failure_details=tuple(details),
            )
        if not run.ok:
            _safe_unlink(tmp)
            failures.append(path)
            details.append(RecompressFailure(path=path, run=run))
            continue
        if not tmp.exists():
            # Exit 0 and NO OUTPUT FILE. Say so explicitly: it used to fall into the
            # same branch as a non-zero exit, so the report could not distinguish
            # "flac refused" from "flac claimed success and produced nothing" — and
            # the second is the more alarming of the two.
            reason = "flac exited 0 but wrote no output file — nothing was swapped in"
            log.error("%s (%s)", reason, path)
            failures.append(path)
            details.append(RecompressFailure(path=path, run=run, stage_error=reason))
            continue
        try:
            os.replace(tmp, path)  # atomic swap-in (same directory)
        except OSError as exc:
            reason = f"re-encode succeeded but the atomic swap-in failed: {exc}"
            log.error("could not swap in re-compressed %s: %s", path, exc)
            _safe_unlink(tmp)
            failures.append(path)
            details.append(RecompressFailure(path=path, stage_error=reason))
            continue
        reencoded += 1
    return RecompressResult(
        reencoded=reencoded,
        failures=tuple(failures),
        failure_details=tuple(details),
    )
