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
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_FLAC_BINARY: str = "flac"
# A decode-test is fast, but bound it so one wedged file can't hang the thread.
_TEST_TIMEOUT_S: float = 120.0

# Injectable for tests: takes the argv, returns the process exit code.
Runner = Callable[[list[str]], int]


@dataclass(frozen=True)
class FlacVerifyResult:
    """Outcome of verifying a set of FLAC files.

    ``checked`` is how many files were tested; ``failures`` lists the paths that
    failed the decode/MD5 test; ``error`` is set (and the rest empty) when the
    check could not run at all — e.g. the ``flac`` binary is missing. ``ok`` is
    True only when the check ran and every tested file passed.
    """

    checked: int = 0
    failures: tuple[Path, ...] = ()
    error: str = ""

    @property
    def ran(self) -> bool:
        return not self.error

    @property
    def ok(self) -> bool:
        return self.ran and not self.failures


def _default_runner(argv: list[str]) -> int:
    # Capture stderr and log its tail on failure (never swallow a dependency's
    # error — CLAUDE.md "validate every input and every dependency output"), so a
    # `flac --test` that reports corruption is diagnosable from the log file.
    proc = subprocess.run(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        timeout=_TEST_TIMEOUT_S,
        text=True,
    )
    if proc.returncode != 0 and proc.stderr:
        log.warning(
            "flac --test failed (rc=%s): %s",
            proc.returncode,
            proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "",
        )
    return proc.returncode


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
    specific file marks that file as a failure.
    """
    run = runner or _default_runner
    failures: list[Path] = []
    checked = 0
    for path in paths:
        try:
            rc = run([binary, "--test", "--silent", str(path)])
        except FileNotFoundError:
            return FlacVerifyResult(
                checked=checked,
                error=f"'{binary}' not found — cannot verify FLAC integrity",
            )
        except subprocess.TimeoutExpired:
            log.warning("flac --test timed out on %s", path)
            failures.append(path)
            checked += 1
            continue
        except OSError as exc:
            return FlacVerifyResult(
                checked=checked, error=f"could not run {binary}: {exc}"
            )
        checked += 1
        if rc != 0:
            failures.append(path)
    return FlacVerifyResult(checked=checked, failures=tuple(failures))
