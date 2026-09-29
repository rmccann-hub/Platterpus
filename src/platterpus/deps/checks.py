"""Probe functions: "is this dependency present, and at what version?"

One probe per dependency, returning a `ProbeResult`. Probes have no side
effects — they MUST NOT install, modify, or write anything; they may
shell out (via `VERSION_PROBE`, a killable command) to ask a tool for its
version.

Failures (tool missing, network gone, timeout, **a non-zero exit**) are
caught and reflected in the `ProbeResult`, never raised. The dependency
manager classifies a probe with `present=False` as missing; how to resolve
it is the registry's tier decision and the resolvers' job.

A tool that ran but *failed* counts as a failure, not as a version answer —
see `_SUCCESS_EXIT_CODES`. Reporting "installed, version 19.0" because a
linker error mentioned `libcdio.so.19.0` is worse than reporting the tool
missing: the user is told a broken tool is fine, and the wizard that would
have fixed it never offers.
"""

from __future__ import annotations

import importlib.metadata
import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from platterpus.cyanrip_cli import VERSION_FLAGS
from platterpus.deps.version import parse_version
from platterpus.killable import KillableCommand, was_cancelled

log = logging.getLogger(__name__)

# Version probes shell out, and the FIRST one of a session starts the Distrobox
# container — tens of seconds cold. `DependencyCheckWorker` blocks in there with no
# way for `QThread.quit()` to reach it, so closing the window mid-check used to wait
# out the shutdown budget and abandon the thread. Routing through a killable command
# makes that worker's `cancel()` real rather than a flag nothing reads.
VERSION_PROBE: KillableCommand = KillableCommand("dependency version probe")


def cancel_version_probes() -> None:
    """Stop an in-flight version probe. Thread-safe, non-blocking (GUI thread).

    Only the *current* probe is killed. `check_all` runs the specs in sequence, so
    the worker's own cancel flag stops the loop starting the next one — the kill and
    the flag are complementary, and neither alone is enough: the flag cannot
    interrupt a blocked call, and the kill cannot stop the next iteration.
    """
    VERSION_PROBE.cancel()


# Probes that shell out should never hang the GUI (they run off-thread, but a
# tight cap also forces a wrong answer). `cyanrip --version` returns in
# milliseconds once warm — but the FIRST probe of a session must start
# the Distrobox `ripping` container (podman cold-start), which routinely takes
# tens of seconds on first use after a boot. A 10s cap made a cold container
# look like a MISSING ripper at launch, AND left it cold for the disc scan that
# followed (real-user report, Bazzite + BDR-209D, 2026-06-27). Budget for the
# cold start: now the launch probe actually waits for the container to come up,
# which WARMS it as a side effect — so the disc scan that follows runs warm and
# fast. Native-binary probes (metaflac, flac on the host) return in ms regardless,
# so the larger ceiling only ever bites a container cold-start or a wedged binary.
_PROBE_TIMEOUT_S: float = 60.0


# --- A probe may not outlive the check it belongs to ------------------------
#
# `_PROBE_TIMEOUT_S` bounds ONE probe. The dependency check runs seven specs in a
# row, and cyanrip's probe tries two version flags, so a wedged container used to
# mean ~7 minutes before any answer — the "Check dependencies does nothing" report
# (2026-09-28). `DependencyManager.check_all` therefore sets an overall deadline
# for the pass, and every probe it runs reads it here, because the probe is where
# the waiting actually happens:
#
# * a probe's timeout is capped to what the check has left, so the in-flight child
#   is SIGKILLed (group-wide, by `KillableCommand`'s own timeout path) at the
#   deadline rather than up to 60 s after it;
# * once the deadline has passed, no further probe is started — which is what
#   stops cyanrip's second version flag spawning a fresh 60 s wait after the first
#   one was killed.
#
# **Why a capped timeout and not a timer calling `cancel_version_probes()`.**
# `VERSION_PROBE` is ONE slot shared by every caller in the process. A timer that
# cancelled it at the deadline would kill whichever child held the slot at that
# moment — which can be the cyanrip-update check's probe on another thread, not
# ours. The capped timeout can only ever end the child this thread started.
#
# **Thread-local on purpose.** The probes are zero-argument callables (see
# `registry.DependencySpec.probe`), so the deadline cannot be passed to them. The
# check runs every probe on the thread that called `check_all` (the GUI's worker,
# or the main thread under `--doctor`, which passes `CHECK_DEADLINE_S` too), so a
# per-thread value reaches exactly that check's probes. A probe run outside it on
# another thread (the ripper-update check) keeps the plain `_PROBE_TIMEOUT_S`.


class _ProbeBudget(threading.local):
    """The current thread's check deadline, as a ``time.monotonic()`` instant."""

    deadline_at: float | None = None


_BUDGET: _ProbeBudget = _ProbeBudget()


@contextmanager
def probe_deadline(deadline_at: float | None) -> Iterator[None]:
    """Cap every probe this thread runs, until the block exits, at ``deadline_at``.

    ``None`` means "no overall deadline" (the plain per-probe timeout applies).
    The previous value is restored on exit, so a nested use cannot leak a
    deadline into code that runs after it.
    """
    previous = _BUDGET.deadline_at
    _BUDGET.deadline_at = deadline_at
    try:
        yield
    finally:
        _BUDGET.deadline_at = previous


def _probe_timeout() -> float | None:
    """How long the next probe may run, or None when the check's time is up."""
    deadline_at = _BUDGET.deadline_at
    if deadline_at is None:
        return _PROBE_TIMEOUT_S
    remaining = deadline_at - time.monotonic()
    if remaining <= 0:
        return None
    return min(_PROBE_TIMEOUT_S, remaining)


# Which exit codes mean "the tool answered us".
#
# **Why this constant exists.** A probe used to count as successful the moment the
# command *finished*, whatever it finished with. But a failing run still prints
# something, and that something routinely contains a version-like number that
# belongs to a completely different program: a Distrobox/podman start failure
# prints podman's own version, and a broken binary prints
# `libcdio.so.19.0: cannot open shared object file`. `parse_version` grabs the
# first `N.N` it sees, so those numbers were being reported as *the tool's*
# version — which also cleared the spec's minimum-version floor, and the
# dependency report then told the user a demonstrably broken tool was installed
# and current. The exit code is the one piece of evidence that distinguishes
# "answered" from "failed while saying a number", so we now require it.
#
# A negative return code (killed by a signal) lands here too, which is the
# behaviour we want: `cancel_version_probes()` SIGKILLs the child, and a probe
# we deliberately killed part-way must never be read as a version answer.
_SUCCESS_EXIT_CODES: frozenset[int] = frozenset({0})

# How much of a failed probe's output goes into the log line. Long enough to
# carry a linker error or a podman message, short enough that a tool spewing
# megabytes can't bloat the user's log file.
_MAX_LOGGED_OUTPUT_CHARS: int = 500


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single dependency probe.

    - `present`: True if the dep is installed and we got a usable answer.
    - `version`: parsed version tuple, or None if we couldn't determine it.
    - `location`: where we found it (path, "(python package)", etc.) or None.
    - `raw_output`: stdout/stderr we captured, useful for debugging. Kept
      short — we log it but don't store gigabytes if a probe goes weird.
    """

    present: bool
    version: tuple[int, ...] | None
    location: str | None
    raw_output: str = ""


def _run_version_command(
    argv: list[str],
    *,
    accept_exit_codes: frozenset[int] = _SUCCESS_EXIT_CODES,
    log_failure: bool = True,
) -> tuple[bool, str, str | None]:
    """Shell out and capture stdout+stderr. Returns (ran_ok, output, location).

    `ran_ok` means **"this tool answered our version question"** — not merely
    "a process started and stopped". So it is False when the binary is missing,
    when the probe times out, *and* when the command exits with a code we don't
    accept (see `_SUCCESS_EXIT_CODES` for why that last one matters). A caller
    that sees `ran_ok=False` must report the dependency as absent rather than
    parse a version out of the output — an error message's numbers are not a
    version.

    Both streams are captured together because a version banner is not reliably
    on stdout: `cd-paranoia --version` prints its banner to **stderr** and still
    exits 0.

    A failed probe is logged with the exit code and the captured output, so a
    user's bug report carries *why* the tool was called absent (CLAUDE.md: when
    a dependency fails, capture its stderr/stdout and log it). It is a warning,
    not an error, because plenty of these are expected — an optional tool that
    isn't installed is normal.

    `location` is `argv[0]` resolved through `shutil.which` when possible so the
    user sees the actual path the GUI is using, not the unresolved name.

    **`accept_exit_codes` — the allow-list seam, deliberately unused today.**
    A non-zero exit for a version flag is a rare-but-real upstream convention:
    libcdio's shared `print_version()` ends in `exit(EXIT_INFO)` and `EXIT_INFO`
    is **100** (`libcdio/src/util.h`), so e.g. `cd-info --version` prints a
    perfectly good banner and "fails" with rc=100. Every tool *Platterpus*
    probes was checked against its own upstream source and exits 0 on its
    version flag (evidence recorded in `docs/dependency-contracts.md` →
    *Version probes*), so no caller passes this parameter. It exists so that the
    day one of them changes, the fix is an explicit per-tool allow-list with the
    evidence written down beside it — never a return to "any exit code counts",
    which is the bug this function was fixed for.

    **`log_failure=False` — for a caller that tries several flags.** cyanrip
    renamed its version flag between the build users have and the build we want
    (`platterpus.cyanrip_cli`), so `check_cyanrip` tries `-V` then `-v`. On a
    0.9.4 build the first attempt is *expected* to fail, and logging
    "treating the tool as unavailable" for it would put a line in every user's
    log file that is both alarming and untrue. The caller suppresses the
    per-attempt line and logs once, itself, only if every flag failed. Absence is
    still logged — just at the point where it is actually known.
    """
    resolved = shutil.which(argv[0]) or argv[0]
    # The overall check's deadline, if one is running on this thread (see
    # `probe_deadline`). Past it, nothing is spawned: "not asked" is reported as
    # a non-answer, and the check that owns the deadline records the tool as NOT
    # CHECKED rather than missing, because an absence we caused is not a fact.
    timeout = _probe_timeout()
    if timeout is None:
        log.warning(
            "probe: %s not started — the dependency check's overall deadline has "
            "passed",
            " ".join(argv),
        )
        return False, "", resolved
    try:
        proc = VERSION_PROBE.run(argv, timeout=timeout, stdin_devnull=True)
    except FileNotFoundError:
        log.debug("probe: %s not found on PATH", argv[0])
        return False, "", None
    except subprocess.TimeoutExpired:
        # The number logged is the timeout this probe actually had, which is the
        # check's remaining budget when that was shorter than `_PROBE_TIMEOUT_S`.
        log.warning("probe: %s timed out after %.1fs", argv[0], timeout)
        return False, "", resolved

    combined = (proc.stdout or "") + (proc.stderr or "")
    if was_cancelled(proc):
        # We killed it (`cancel_version_probes`), so its -9 says nothing about the
        # tool; the result is unchanged, and the line no longer calls it unavailable.
        log.info("probe: %s stopped by Platterpus before it answered", argv[0])
        return False, combined, resolved
    if proc.returncode not in accept_exit_codes:
        # `debug` rather than `warning` when the caller has more flags to try:
        # the evidence is kept (a bug report still carries it) without asserting
        # a conclusion the caller has not reached yet.
        (log.warning if log_failure else log.debug)(
            "probe: %s exited %d — %s, NOT parsing a version out of its error "
            "output. Captured output: %s",
            " ".join(argv),
            proc.returncode,
            "treating the tool as unavailable"
            if log_failure
            else "the caller has further flags to try",
            _summarize_output(combined),
        )
        return False, combined, resolved
    return True, combined, resolved


def _summarize_output(text: str) -> str:
    """Squash captured tool output into one truncated line fit for a log record.

    Multi-line output in a single log line makes the log file hard to read (and
    hard to grep), so newlines become ` | `. An empty capture is spelled out
    rather than logged as nothing at all — "the tool failed and said nothing" is
    itself a useful clue, and a blank tail would look like a truncated log line.
    """
    flattened = " | ".join(line.strip() for line in text.strip().splitlines() if line)
    if not flattened:
        return "(none)"
    if len(flattened) > _MAX_LOGGED_OUTPUT_CHARS:
        return flattened[:_MAX_LOGGED_OUTPUT_CHARS] + "… (truncated)"
    return flattened


def check_cyanrip(binary_path: Path) -> ProbeResult:
    """Probe the host-exported cyanrip binary.

    Ripping routes through `~/.local/bin/cyanrip` (Critical Rule #3), so we
    accept the path explicitly rather than relying on PATH alone. cyanrip
    reports its version with `-V` (not `--version`), and exits 0 doing so.

    The highest-stakes case for the exit-code check: the host export is a small
    shell script that enters the Distrobox container, so when the container is
    gone or podman errors out, *the export still runs and still prints* — the
    error text carries podman's version, which used to be reported as cyanrip's.
    A non-zero exit now means absent, which is what routes the user to the setup
    wizard that actually fixes it.
    """
    if not binary_path.exists():
        return ProbeResult(present=False, version=None, location=str(binary_path))

    # Try every flag cyanrip has ever used to print its version, in order —
    # `-V` on 0.9.3.x, `-v` from 0.9.4-rc1 onward (the generic genopt parser
    # replaced the hand-rolled `case 'V':`). See `platterpus.cyanrip_cli`.
    #
    # This must not report the FIRST failure as the reason the tool is absent:
    # on a 0.9.4 build the `-V` attempt is expected to fail, and logging that as
    # "treating the tool as unavailable" would put a misleading line in every
    # user's log file. Only an all-flags-failed outcome is a real absence.
    output = ""
    for flag in VERSION_FLAGS:
        ran, output, _ = _run_version_command(
            [str(binary_path), flag], log_failure=False
        )
        if ran:
            version = parse_version(output)
            return ProbeResult(
                present=True,
                version=version,
                location=str(binary_path),
                raw_output=output.strip()[:200],
            )
    log.warning(
        "probe: %s answered none of %s — treating cyanrip as unavailable. "
        "Last captured output: %s",
        binary_path,
        " / ".join(VERSION_FLAGS),
        _summarize_output(output),
    )
    return ProbeResult(present=False, version=None, location=str(binary_path))


def check_cdparanoia(binary_path: Path) -> ProbeResult:
    """Probe the host-exported ``cd-paranoia`` binary (libcdio's, KDD-29).

    Optional — used only by the cache-defeat probe. Routes through the same
    ``~/.local/bin`` host-export as cyanrip (Critical Rule #3), so we accept the
    path explicitly rather than relying on PATH. cd-paranoia prints its version
    banner on ``--version`` — to **stderr**, and exits 0 (upstream
    libcdio-paranoia ``src/cd-paranoia.c``: ``case 'V': fprintf(stderr, …);
    exit(0);``) — so we read both streams and require a zero exit. A missing
    binary or a non-zero run is reported as absent (which the wizard resolves by
    re-running host setup). Beware the family resemblance: libcdio's *other*
    tools exit 100 on ``--version``; cd-paranoia has its own ``main`` and does
    not (see ``_run_version_command``'s allow-list note).
    """
    if not binary_path.exists():
        return ProbeResult(present=False, version=None, location=str(binary_path))

    ran, output, _ = _run_version_command([str(binary_path), "--version"])
    if not ran:
        return ProbeResult(present=False, version=None, location=str(binary_path))

    version = parse_version(output)
    return ProbeResult(
        present=True,
        version=version,
        location=str(binary_path),
        raw_output=output.strip()[:200],
    )


def check_metaflac(binary_name: str = "metaflac") -> ProbeResult:
    """Probe `metaflac`, expected on PATH (via the same Distrobox export route
    as the ripper)."""
    ran, output, location = _run_version_command([binary_name, "--version"])
    if not ran or location is None:
        return ProbeResult(present=False, version=None, location=None)

    version = parse_version(output)
    return ProbeResult(
        present=True,
        version=version,
        location=location,
        raw_output=output.strip()[:200],
    )


def check_flac(binary_name: str = "flac") -> ProbeResult:
    """Probe the host `flac` decoder, expected on PATH.

    Used by the optional CTDB verify (KDD-14): the audio CRC is computed
    over the ripped FLACs decoded back to PCM with host `flac`. Optional —
    its absence just means the CTDB audio check can't run (the CTDB lookup
    half still works). Same shape as `check_metaflac`.
    """
    ran, output, location = _run_version_command([binary_name, "--version"])
    if not ran or location is None:
        return ProbeResult(present=False, version=None, location=None)

    version = parse_version(output)
    return ProbeResult(
        present=True,
        version=version,
        location=location,
        raw_output=output.strip()[:200],
    )


def check_ffmpeg(binary_name: str = "ffmpeg") -> ProbeResult:
    """Probe `ffmpeg`, expected on PATH.

    The encoder for the Output-format feature (KDD-22): every rip produces FLAC
    (the master), and a non-FLAC choice is a post-rip ffmpeg transcode of that
    FLAC — WavPack (`-c:a wavpack`), MP3 (libmp3lame), or WAV (pcm_s16le).
    Optional: its absence just disables non-FLAC output (FLAC ripping is
    unaffected, and the FLAC master is always kept). ffmpeg prints its version
    to `-version` (single dash, unlike the GNU `--version` the other probes use).
    """
    ran, output, location = _run_version_command([binary_name, "-version"])
    if not ran or location is None:
        return ProbeResult(present=False, version=None, location=None)

    version = parse_version(output)
    return ProbeResult(
        present=True,
        version=version,
        location=location,
        raw_output=output.strip()[:200],
    )


def check_libdiscid() -> ProbeResult:
    """Probe libdiscid by attempting to load it via ctypes.

    We try the common SONAME variants the library ships with. If any
    load succeeds, we call `discid_get_version_string()` for the version.
    Returns `present=False` if no variant loads.

    Note (PLANNING.md KDD-06): libdiscid may not actually be required on
    the host because cyanrip computes the disc ID inside its Distrobox
    container. The probe exists so the dependency subsystem has the
    capability when the answer turns out to be "yes, we need it."
    """
    import ctypes
    import ctypes.util

    # ctypes.util.find_library is the portable way; fall back to common
    # SONAMEs if it doesn't resolve (some systems set it up oddly).
    candidates: list[str] = []
    found = ctypes.util.find_library("discid")
    if found:
        candidates.append(found)
    candidates.extend(["libdiscid.so.0", "libdiscid.so"])

    for name in candidates:
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            continue

        try:
            lib.discid_get_version_string.restype = ctypes.c_char_p
            version_str = lib.discid_get_version_string().decode("utf-8")
        except (AttributeError, OSError, UnicodeDecodeError):
            version_str = ""

        version = parse_version(version_str)
        return ProbeResult(
            present=True,
            version=version,
            location=name,
            raw_output=version_str,
        )

    return ProbeResult(present=False, version=None, location=None)


def check_picard_flatpak() -> ProbeResult:
    """Probe MusicBrainz Picard via Flathub.

    Uses `flatpak info --user org.musicbrainz.Picard`. If flatpak itself
    isn't installed, returns `present=False` (which the registry can
    treat as a tier-(a) install opportunity for the Flatpak system).
    """
    ran, output, _ = _run_version_command(
        ["flatpak", "info", "--user", "org.musicbrainz.Picard"]
    )
    if not ran:
        return ProbeResult(present=False, version=None, location=None)

    # `flatpak info` returns non-zero when the app isn't installed (that case is
    # now caught by the exit-code check above, which is where it belongs). This
    # stays as the belt for the opposite shape: a zero exit whose output isn't
    # the record we expected. A real "app is installed" answer always contains a
    # "Version:" line, and without one there is nothing trustworthy to parse.
    if "Version:" not in output:
        return ProbeResult(
            present=False, version=None, location=None, raw_output=output[:200]
        )

    version = parse_version(output)
    return ProbeResult(
        present=True,
        version=version,
        location="flatpak: org.musicbrainz.Picard",
        raw_output=output.strip()[:200],
    )


def check_python_pkg(distribution: str) -> ProbeResult:
    """Probe a Python distribution that's expected to be importable.

    We ask `importlib.metadata` instead of importing the module so we
    can read the version even if importing would have side effects.
    """
    try:
        version_str = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return ProbeResult(present=False, version=None, location=None)

    version = parse_version(version_str)
    return ProbeResult(
        present=True,
        version=version,
        location=f"python: {distribution}",
        raw_output=version_str,
    )
