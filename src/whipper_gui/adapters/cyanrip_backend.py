"""cyanrip backend — a second ripping backend behind the WhipperBackend ABC.

Why (KDD-18, docs/ecosystem-audit-2026-06.md): whipper is stalled (last release
2021) and its cd-paranoia has a real bug at read offsets > 587 — exactly the
range the tested Pioneer BDR-209D needs (+667), which fails tracks on hardware.
**cyanrip** is actively maintained (C/FFmpeg), applies the offset itself via
``-s`` with its own paranoia (no >587 bug), and does AccurateRip v1/v2 + EAC
CRC. We slot it behind the existing ABC so it's a config-selectable backend and
ripping still routes through a host-exported binary (Critical Rule #3).

**Phase 1 (this module): the testable core** — the rip argv builder, version,
find-offset, and a backend-independent drive scan. The parts that need
cyanrip-specific output parsing or a real cyanrip on hardware are stubbed with
clear messages and tracked in the ecosystem audit:
  * `disc_info` returns an empty DiscInfo for now (the GUI then uses its own
    host-side MusicBrainz lookup + unknown-mode, which already works);
  * whipper-only rip params (release_id, track/disc templates, cdr, keep_going,
    force_overread) don't map 1:1 to cyanrip and are documented, not forced.

cyanrip CLI (from its README): ``-d`` device, ``-s`` sample offset, ``-o``
codec list (flac default), ``-r`` retries, ``-N`` disable MusicBrainz,
``-G`` disable cover-art embed, ``-I`` info-only, ``-f`` find offset, ``-V``
version, ``-D``/``-F`` dir/file naming schemes.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from whipper_gui.adapters.whipper_backend import (
    RipHandle,
    WhipperBackend,
    WhipperError,
)
from whipper_gui.parsers.cd_info import DiscInfo
from whipper_gui.parsers.drive_list import DriveDescriptor

log = logging.getLogger(__name__)

_INFO_TIMEOUT_S: float = 120.0


class CyanripImpl(WhipperBackend):
    """Ripping backend that drives the `cyanrip` CLI."""

    def __init__(
        self,
        binary_path: Path | str = "cyanrip",
        working_dir: Path | None = None,
        dev_root: Path = Path("/dev"),
        sys_block: Path = Path("/sys/block"),
    ) -> None:
        self._binary: str = str(binary_path)
        self._working_dir: Path | None = working_dir
        # Injectable so list_drives() is testable without a real /dev or /sys.
        self._dev_root: Path = dev_root
        self._sys_block: Path = sys_block

    # --- Drive listing (backend-independent: scan /dev + /sys) ---

    def list_drives(self) -> list[DriveDescriptor]:
        """Enumerate optical drives by scanning ``/dev/sr*`` and reading the
        vendor/model/revision from sysfs. cyanrip has no list-drives command,
        and this is generic enough to not need one."""
        drives: list[DriveDescriptor] = []
        try:
            nodes = sorted(self._dev_root.glob("sr*"))
        except OSError:
            return drives
        for node in nodes:
            info = self._sys_block / node.name / "device"
            drives.append(
                DriveDescriptor(
                    device=str(node),
                    vendor=_read_sysfs(info / "vendor"),
                    model=_read_sysfs(info / "model"),
                    release=_read_sysfs(info / "rev"),
                )
            )
        return drives

    # --- Disc info (Phase 1: not yet parsed) ---

    def disc_info(self, drive: str) -> DiscInfo:
        """Return what we know about the inserted disc.

        Phase 1: cyanrip's ``-I`` output format isn't parsed yet, so we return
        an empty DiscInfo. The GUI already identifies the disc via its own
        host-side MusicBrainz lookup, so this is non-fatal — it just means the
        disc-info panel's IDs stay blank until the parser lands.
        """
        del drive  # unused until -I parsing is implemented
        log.info("CyanripImpl.disc_info: -I parsing not implemented yet (Phase 1)")
        return DiscInfo()

    # --- Rip ---

    def _build_rip_argv(
        self,
        drive: str,
        *,
        unknown: bool,
        cover_art: str,
        max_retries: int,
        read_offset_override: int | None,
    ) -> list[str]:
        """Build the cyanrip rip argv (pure — unit-tested).

        Maps the backend-neutral params to cyanrip flags. cyanrip needs the
        read offset every run (it has no whipper.conf), so we always pass
        ``-s`` when we have one — its own paranoia applies it without the
        >587 cd-paranoia bug.
        """
        argv: list[str] = [self._binary]
        if drive:
            argv += ["-d", drive]
        if read_offset_override is not None:
            argv += ["-s", str(read_offset_override)]
        argv += ["-o", "flac"]
        if max_retries:
            argv += ["-r", str(max_retries)]
        if unknown:
            argv.append("-N")  # disable MusicBrainz → rip without metadata
        if not cover_art:
            argv.append("-G")  # disable cover-art embedding
        return argv

    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
        cdr: bool = False,
        cover_art: str = "",
        force_overread: bool = False,
        max_retries: int = 5,
        keep_going: bool = False,
        read_offset_override: int | None = None,
    ) -> RipHandle:
        # release_id / track_template / disc_template / cdr / keep_going /
        # force_overread are whipper-isms with no 1:1 cyanrip flag; Phase 1
        # uses cyanrip's own MusicBrainz + default naming (see module docstring).
        del release_id, track_template, disc_template, cdr, force_overread, keep_going
        argv = self._build_rip_argv(
            drive,
            unknown=unknown,
            cover_art=cover_art,
            max_retries=max_retries,
            read_offset_override=read_offset_override,
        )
        # cyanrip writes under the current directory (its -D/-F schemes are
        # relative), so run it from the output dir.
        output_dir.mkdir(parents=True, exist_ok=True)
        log.info("cyanrip rip starting: %s (cwd=%s)", " ".join(argv), output_dir)
        process = subprocess.Popen(
            argv,
            cwd=str(output_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        return RipHandle(process=process)

    # --- Misc ---

    def version(self) -> str:
        return self._run(["-V"]).strip()

    def find_offset(self, device: str) -> int:
        """Run cyanrip's own offset finder (``-f``) and parse the result."""
        args = ["-f"]
        if device:
            args += ["-d", device]
        out = self._run(args)
        import re

        match = re.search(r"offset[^\-0-9]*(?P<offset>-?\d+)", out, re.IGNORECASE)
        if match:
            return int(match.group("offset"))
        raise WhipperError(
            "cyanrip could not detect the read offset. Insert a CD that's in "
            "the AccurateRip database and try again.",
            output=out,
        )

    def _run(self, args: list[str], timeout: float = _INFO_TIMEOUT_S) -> str:
        argv = [self._binary, *args]
        log.debug("cyanrip: %s", " ".join(argv))
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise WhipperError(f"cyanrip binary not found at {self._binary}") from exc
        except subprocess.TimeoutExpired as exc:
            raise WhipperError(f"cyanrip timed out after {timeout:.0f}s") from exc
        return (proc.stdout or "") + (proc.stderr or "")


def _read_sysfs(path: Path) -> str:
    """Read a one-line sysfs attribute, stripped; "" if unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
