# SPDX-License-Identifier: GPL-3.0-only
"""Post-rip FLAC integrity verification — the encode-verify cyanrip doesn't do itself.

The historical whipper backend passed ``flac --verify`` while it ripped, so each
FLAC was proven to decode back to exactly the PCM that was read off the disc.
cyanrip encodes via FFmpeg with no such self-check, so a cyanrip rip lacks that
guarantee. This adapter runs
an independent post-rip check: ``flac --test`` decodes each FLAC and verifies its
embedded STREAMINFO MD5 against the decoded audio, catching encode-time or disk
corruption.

It is best-effort and **never raises** — the rip itself already succeeded, so a
missing ``flac`` binary or an odd file is reported as a result, never an
exception into the GUI.

**Every failure carries what ``flac`` said about it.** The result used to record
only *which paths* failed, because the injected runner returned an ``int`` and the
tool's own output was logged-and-dropped inside it. A report reading "FLAC verify
FAILED for 3 file(s)" named the files and could not name the reason — see
:mod:`platterpus.adapters.tool_run` for why that was a missing channel rather than
a missing call.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from platterpus.adapters.tool_run import ToolRun, ToolRunner, make_runner
from platterpus.tool_paths import resolve_tool

log = logging.getLogger(__name__)

_FLAC_BINARY: str = resolve_tool("flac")
# A decode-test is fast, but bound it so one wedged file can't hang the thread.
_TEST_TIMEOUT_S: float = 120.0

# Injectable for tests: takes the argv, returns everything the tool said.
Runner = ToolRunner

_default_runner: ToolRunner = make_runner(
    timeout_s=_TEST_TIMEOUT_S,
    tool="flac --test",
    code="flac.verify_failed",
    where="adapters.flac_verify.verify_flac_files",
)


@dataclass(frozen=True)
class FlacVerifyFailure:
    """One file that failed the decode test, **and why**.

    The ``why`` is the point. Without it the archival claim "these FLACs decode to
    the PCM their MD5 says they should" fails with no evidence attached, and a
    reader cannot tell an unreadable file from a corrupt one from a tool that timed
    out — three very different problems that used to render identically.
    """

    path: Path
    #: The tool's exit code, argv and complete output for *this* file.
    run: ToolRun

    @property
    def reason(self) -> str:
        """One line a person can read. Never empty."""
        return self.run.summary

    def to_json(self) -> dict[str, object]:
        return {"path": str(self.path), **self.run.to_json()}


@dataclass(frozen=True)
class FlacVerifyResult:
    """Outcome of verifying a set of FLAC files.

    ``checked`` is how many files were tested; ``failures`` lists the paths that
    failed the decode/MD5 test; ``error`` is set (and the rest empty) when the
    check could not run at all — e.g. the ``flac`` binary is missing. ``ok`` is
    True only when the check ran and every tested file passed.

    ``failure_details`` is ``failures`` with the tool's own words attached, one
    entry per failed path and in the same order. ``failures`` is kept as the plain
    tuple of paths because several consumers (the UI list, the checksum pass) only
    ever wanted the paths, and widening them all to reach a nested field would have
    been a change with no reader.
    """

    checked: int = 0
    failures: tuple[Path, ...] = ()
    error: str = ""
    failure_details: tuple[FlacVerifyFailure, ...] = field(default=())

    @property
    def ran(self) -> bool:
        return not self.error

    @property
    def ok(self) -> bool:
        return self.ran and not self.failures

    def reasons(self) -> tuple[str, ...]:
        """``"01.flac: exit 1: ERROR ..."`` per failure. For a UI line or a log."""
        return tuple(f"{d.path.name}: {d.reason}" for d in self.failure_details)


def verify_flac_files(
    paths: Sequence[Path],
    *,
    binary: str = _FLAC_BINARY,
    runner: Runner | None = None,
) -> FlacVerifyResult:
    """Run ``flac --test`` on each path; return a :class:`FlacVerifyResult`.

    Never raises. A missing ``flac`` binary (or any other failure to even run
    it) aborts with ``error`` set rather than marking files failed — "couldn't
    check" is not the same as "corrupt". A non-zero exit or a timeout on a
    specific file marks that file as a failure, **with the tool's output kept**.
    """
    run_cmd = runner or _default_runner
    failures: list[Path] = []
    details: list[FlacVerifyFailure] = []
    checked = 0
    for path in paths:
        # `--silent` is deliberately NOT passed: it suppresses the very message that
        # explains a failure, and the whole point of this pass is to be able to
        # quote it. `flac --test` is quiet on success anyway, so the cost is nil.
        run = run_cmd([binary, "--test", str(path)])
        if not run.started:
            # The binary is not there. Abort the whole pass rather than blame the
            # file — `run.started`, not `run.ran`, because a *timeout* means the tool
            # works and wedged on this input, which is the file's problem and is
            # handled below. Collapsing the two is how a missing binary came to be
            # reported as a corrupt FLAC.
            log.error(
                "flac --test could not run (%s) — aborting the verify pass after "
                "%d file(s)",
                run.error,
                checked,
            )
            return FlacVerifyResult(
                checked=checked,
                error=f"{run.error} — cannot verify FLAC integrity",
                failures=tuple(failures),
                failure_details=tuple(details),
            )
        checked += 1
        if not run.ok:
            failures.append(path)
            details.append(FlacVerifyFailure(path=path, run=run))
    return FlacVerifyResult(
        checked=checked,
        failures=tuple(failures),
        failure_details=tuple(details),
    )
