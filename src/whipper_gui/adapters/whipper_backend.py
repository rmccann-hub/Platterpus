"""Adapter over the host-exported `whipper` CLI.

`WhipperBackend` is an abstract base class with the four operations the
GUI needs. `WhipperHostExportedImpl` is the v1 concrete implementation
that shells out to `~/.local/bin/whipper`. A future `CyanripImpl` could
implement the same ABC and be selected via config — see PLANNING.md §5.

The adapter is deliberately thin: it builds argv, runs subprocess, and
hands stdout to the parsers in `whipper_gui.parsers`. It does NOT parse
output inline.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from whipper_gui.parsers.cd_info import DiscInfo, parse_cd_info
from whipper_gui.parsers.drive_list import DriveDescriptor, parse_drive_list
from whipper_gui.paths import WHIPPER_CONFIG_PATH

log = logging.getLogger(__name__)

# Generous timeout for one-shot info commands. `whipper drive list` and
# `whipper cd info` return within seconds on a healthy system; the cap
# guards against a hung subprocess.
_INFO_TIMEOUT_S: float = 30.0

# Drive-calibration commands take much longer: `drive analyze` spins the
# disc, and `offset find` tries many candidate offsets against AccurateRip.
_SETUP_TIMEOUT_S: float = 300.0

# whipper's success/diagnostic lines, matched defensively (named-group
# regex per CLAUDE.md, not column splits). Sources:
#   offset find → "Read offset of device is: %d."  (whipper/command/offset.py)
#   drive analyze → "cdparanoia (can|cannot) defeat the audio cache …"
#                   "cannot analyze the drive: is there a CD in it?"
_OFFSET_RE: re.Pattern[str] = re.compile(
    r"[Rr]ead offset of device is:\s*(?P<offset>-?\d+)"
)
_CACHE_CAN: str = "can defeat the audio cache"
_CACHE_CANNOT: str = "cannot defeat the audio cache"
_NO_DISC_MARKER: str = "is there a CD in it"


def _last_line(text: str, rc: int) -> str:
    """The last non-empty line of `text`, or an rc= fallback for the GUI."""
    lines = text.strip().splitlines()
    return lines[-1] if lines else f"rc={rc}"


def back_up_whipper_config(conf_path: Path = WHIPPER_CONFIG_PATH) -> Path | None:
    """Copy `whipper.conf` to `whipper.conf.bak` before the drive-setup
    wizard lets whipper rewrite it, so the user can always revert.

    Returns the backup path, or None if there was no existing config to
    back up (a fresh system — whipper will create it on first write).
    """
    if not conf_path.exists():
        return None
    backup = conf_path.with_name(conf_path.name + ".bak")
    shutil.copy2(conf_path, backup)
    log.info("backed up %s -> %s", conf_path, backup)
    return backup


class WhipperError(Exception):
    """Raised when a whipper subprocess fails in an actionable way.

    The message holds the last stderr line whipper emitted (or its
    stdout fallback) so the GUI can surface something meaningful to
    the user. The full output is available on `.output` for logging.
    """

    def __init__(self, message: str, output: str = "") -> None:
        super().__init__(message)
        self.output: str = output


class RipHandle:
    """Handle to a running rip subprocess.

    Exposes line-streaming, blocking wait, and cancellation. Doesn't
    know where whipper writes the `.log` file — the rip worker locates
    that itself by scanning `output_dir` after the process exits.
    """

    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._process: subprocess.Popen[str] = process

    def log_lines(self) -> Iterator[str]:
        """Yield whipper's combined stdout/stderr lines as they come.

        Iteration ends when whipper closes its stream (i.e. exits).
        Call `.wait()` afterward to harvest the exit code.
        """
        assert self._process.stdout is not None
        for line in self._process.stdout:
            yield line.rstrip("\n")

    def wait(self, timeout: float | None = None) -> int:
        """Block until whipper exits; return its exit code."""
        return self._process.wait(timeout=timeout)

    def cancel(self, term_timeout: float = 5.0) -> int:
        """Cancel the rip. SIGTERM first, then SIGKILL after the timeout.

        Returns the eventual exit code. Safe to call multiple times.
        """
        if self._process.returncode is not None:
            return self._process.returncode

        self._process.terminate()
        try:
            return self._process.wait(timeout=term_timeout)
        except subprocess.TimeoutExpired:
            log.warning(
                "whipper did not exit %.1fs after SIGTERM — sending SIGKILL",
                term_timeout,
            )
            self._process.kill()
            return self._process.wait()

    @property
    def returncode(self) -> int | None:
        return self._process.returncode


# --- Abstract base ----------------------------------------------------------


class WhipperBackend(ABC):
    """Abstract base for any whipper-or-equivalent ripping backend.

    Implementations: WhipperHostExportedImpl (this module). Future:
    CyanripImpl could be slotted in by implementing this interface.
    """

    @abstractmethod
    def list_drives(self) -> list[DriveDescriptor]:
        """Return all drives the backend can see, parsed."""

    @abstractmethod
    def disc_info(self, drive: str) -> DiscInfo:
        """Return TOC/MB-disc-ID info for the disc currently in `drive`."""

    @abstractmethod
    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
        cdr: bool = False,
    ) -> RipHandle:
        """Begin a rip. `release_id` is an MBID, never an interactive prompt.

        `cdr=True` passes whipper's `--cdr` flag so it will rip a burned
        CD-R (it refuses by default). The returned handle streams
        whipper's stdout and supports cancel.
        """

    @abstractmethod
    def version(self) -> str:
        """Return whipper's reported version string (raw, untrimmed)."""

    # --- Optional drive-calibration capability ------------------------------
    # Deliberately NOT abstract: not every backend can auto-calibrate (a
    # future CyanripImpl might expect whipper.conf to be pre-populated).
    # The drive-setup wizard treats NotImplementedError as "this backend
    # can't do it" rather than crashing.

    def analyze_drive(self, device: str) -> bool | None:
        """Profile the drive's audio cache (for the setup wizard).

        Returns True/False when whipper determines the cache can / cannot
        be defeated, or None if it ran but couldn't classify. whipper
        persists the result to whipper.conf itself. Raises `WhipperError`
        if no disc is present (it needs one to test).
        """
        raise NotImplementedError

    def find_offset(self, device: str) -> int:
        """Auto-detect the drive read offset in samples, signed.

        Tests candidate offsets against AccurateRip; whipper persists the
        winner to whipper.conf itself. Raises `WhipperError` if none was
        found (most often: the inserted disc isn't in AccurateRip).
        """
        raise NotImplementedError


# --- v1 concrete implementation --------------------------------------------


class WhipperHostExportedImpl(WhipperBackend):
    """Calls the whipper binary exported by Distrobox to ~/.local/bin/whipper.

    Per CLAUDE.md Critical Rule #3, the GUI never enters the Distrobox
    container directly — it invokes the host-exported entry point
    whipper itself manages.
    """

    def __init__(
        self,
        binary_path: Path,
        working_dir: Path | None = None,
    ) -> None:
        """`binary_path` defaults via config to ~/.local/bin/whipper.

        `working_dir`, when set, is passed as `--working-directory`. None
        means whipper uses its own default.
        """
        self._binary: Path = binary_path
        self._working_dir: Path | None = working_dir

    # --- Info commands ---

    def list_drives(self) -> list[DriveDescriptor]:
        output = self._run_info(["drive", "list"])
        return parse_drive_list(output)

    def disc_info(self, drive: str) -> DiscInfo:
        # Note: whipper has no -d/--device flag — it auto-detects the
        # single drive on the system. The `drive` parameter is accepted
        # for ABC compatibility and for future multi-drive support
        # (P1 backlog); on single-drive systems (the common case) it's
        # ignored at the subprocess layer. If a multi-drive selection
        # mechanism is later added to whipper, plumb it here.
        del drive  # explicit: parameter intentionally unused for v1
        try:
            output = self._run_info(["cd", "info"])
        except WhipperError as exc:
            # Upstream whipper bug: `whipper cd info` exits -1 with
            # CRITICAL "unable to retrieve disc metadata, --unknown
            # argument not passed" when the inserted disc isn't in
            # MusicBrainz/FreeDB — but the Info subcommand doesn't
            # accept --unknown (only Rip does), so there's no way to
            # pass it. Treat that specific failure as "this disc isn't
            # in any database" and return an empty DiscInfo so the GUI
            # can render a clean "not in MusicBrainz" state and offer
            # the File → Rip as Unknown Album flow.
            if "unable to retrieve disc metadata" in (exc.output or ""):
                # Whipper still prints the disc IDs and "N audio tracks"
                # to stdout before it bails on the missing metadata, so
                # parse what it gave us rather than discarding everything.
                # That salvages the track count (for showing numbered
                # blank rows) and the disc IDs (for the info panel). If
                # the output had none of those, parse_cd_info returns an
                # empty DiscInfo and the unknown-album flow still works.
                log.info(
                    "whipper cd info: disc not in MusicBrainz/FreeDB; "
                    "parsing partial output for the unknown-album flow"
                )
                return parse_cd_info(exc.output)
            raise
        return parse_cd_info(output)

    def version(self) -> str:
        return self._run_info(["--version"]).strip()

    # --- Drive calibration (setup wizard) ---

    def analyze_drive(self, device: str) -> bool | None:
        args = ["drive", "analyze"]
        if device:
            # Unlike `cd rip`/`cd info`, the drive subcommands DO accept
            # -d/--device (whipper/command/drive.py), so pass the selected
            # drive explicitly — matters once multi-drive support lands.
            args += ["-d", device]
        rc, out = self._run_capture(args, _SETUP_TIMEOUT_S)
        if _NO_DISC_MARKER in out:
            raise WhipperError(
                "Insert a CD so the drive can be analyzed.", output=out
            )
        if _CACHE_CAN in out:
            return True
        if _CACHE_CANNOT in out:
            return False
        if rc != 0:
            raise WhipperError(
                f"whipper drive analyze failed: {_last_line(out, rc)}",
                output=out,
            )
        return None  # ran cleanly but produced no recognizable verdict

    def find_offset(self, device: str) -> int:
        args = ["offset", "find"]
        if device:
            args += ["-d", device]
        _rc, out = self._run_capture(args, _SETUP_TIMEOUT_S)
        match = _OFFSET_RE.search(out)
        if match:
            return int(match.group("offset"))
        # The usual cause is a disc that isn't in AccurateRip; whipper's
        # own detection is also documented as "primitive". Give the user
        # an actionable message rather than the raw failure.
        raise WhipperError(
            "Could not detect the read offset. Insert a popular commercial "
            "CD (one likely to be in the AccurateRip database) and try again.",
            output=out,
        )

    # --- Streaming rip ---

    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
        cdr: bool = False,
    ) -> RipHandle:
        # Note: whipper has no -d/--device flag for `cd rip` — it
        # auto-detects the single drive. Multi-drive selection is P1
        # (see TASKS.md). `drive` is accepted for ABC compatibility.
        del drive  # explicit: parameter intentionally unused for v1
        argv: list[str] = [
            str(self._binary),
            "cd", "rip",
            "--release-id", release_id,
            "--output-directory", str(output_dir),
            "--track-template", track_template,
            "--disc-template", disc_template,
        ]
        if self._working_dir is not None:
            argv.extend(["--working-directory", str(self._working_dir)])
        if unknown:
            argv.append("--unknown")
        if cdr:
            # Burned discs: whipper aborts with "inserted disc seems to be
            # a CD-R, --cdr not passed" unless we explicitly allow it.
            argv.append("--cdr")

        # Whipper chdir's into --working-directory without creating it
        # (crashes with FileNotFoundError otherwise — hit on T32 with a
        # fresh ~/.cache/whipper-gui). Create both dirs up front so a
        # first-ever rip on a clean system just works. exist_ok keeps
        # this idempotent for every subsequent rip.
        output_dir.mkdir(parents=True, exist_ok=True)
        if self._working_dir is not None:
            self._working_dir.mkdir(parents=True, exist_ok=True)

        log.info("rip starting: %s", " ".join(argv))
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge so a single stream is observable
            text=True,
            bufsize=1,  # line-buffered for responsive UI updates
        )
        return RipHandle(process=process)

    # --- Internals ---

    def _run_capture(
        self, args: list[str], timeout: float = _INFO_TIMEOUT_S
    ) -> tuple[int, str]:
        """Run a one-shot whipper invocation; return (returncode, combined).

        Raises `WhipperError` only for binary-missing or timeout — NOT for
        a non-zero exit, because some callers (drive analyze, offset find)
        need to classify the output themselves before deciding it's an
        error.
        """
        argv: list[str] = [str(self._binary), *args]
        log.debug("whipper: %s", " ".join(argv))
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise WhipperError(
                f"whipper binary not found at {self._binary}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise WhipperError(
                f"whipper timed out after {timeout:.0f}s"
            ) from exc
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def _run_info(self, args: list[str]) -> str:
        """Run a one-shot info command; return combined output, raising
        `WhipperError` on non-zero exit (last error line preserved)."""
        rc, combined = self._run_capture(args)
        if rc != 0:
            raise WhipperError(
                f"whipper failed: {_last_line(combined, rc)}", output=combined
            )
        return combined
