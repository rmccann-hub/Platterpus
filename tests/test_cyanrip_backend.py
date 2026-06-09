"""Tests for the cyanrip backend (Phase 1: argv builder + drive scan).

The actual cyanrip execution is hardware-gated; here we test the pure argv
construction and the sysfs-based drive scan with injected paths.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from whipper_gui.adapters.cyanrip_backend import CyanripImpl
from whipper_gui.adapters.whipper_backend import WhipperError


def _patch_run(monkeypatch, *, stdout: str = "", stderr: str = "", raises=None):
    """Stub cyanrip_backend.subprocess.run with a fixed result (or exception)."""
    import whipper_gui.adapters.cyanrip_backend as mod

    def fake_run(argv, **kwargs):
        if raises is not None:
            raise raises
        return SimpleNamespace(returncode=0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)


def _impl() -> CyanripImpl:
    return CyanripImpl(binary_path="cyanrip")


# --- rip argv builder -----------------------------------------------------


def test_rip_argv_known_disc_with_offset() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
    )
    assert argv[0] == "cyanrip"
    assert "-d" in argv and argv[argv.index("-d") + 1] == "/dev/sr0"
    # cyanrip applies the offset itself via -s (no whipper >587 bug).
    assert "-s" in argv and argv[argv.index("-s") + 1] == "667"
    assert "-o" in argv and argv[argv.index("-o") + 1] == "flac"
    assert "-r" in argv and argv[argv.index("-r") + 1] == "5"
    assert "-N" not in argv  # known disc → keep MusicBrainz on
    assert "-G" not in argv  # cover art wanted → keep embedding on


def test_rip_argv_unknown_disc_disables_musicbrainz() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=True,
        cover_art="",
        max_retries=5,
        read_offset_override=667,
    )
    assert "-N" in argv  # unknown → disable MusicBrainz (no network needed)
    assert "-G" in argv  # no cover art → disable embedding


def test_rip_argv_omits_offset_when_none() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=None,
    )
    assert "-s" not in argv


# --- drive scan -----------------------------------------------------------


def test_list_drives_scans_dev_and_sysfs(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "sr0").write_bytes(b"")
    (dev / "sda").write_bytes(b"")  # not optical — must be ignored
    sysblk = tmp_path / "sys-block"
    info = sysblk / "sr0" / "device"
    info.mkdir(parents=True)
    (info / "vendor").write_text("PIONEER\n")
    (info / "model").write_text("BD-RW   BDR-209D\n")
    (info / "rev").write_text("1.51\n")

    impl = CyanripImpl(dev_root=dev, sys_block=sysblk)
    drives = impl.list_drives()

    assert len(drives) == 1
    d = drives[0]
    assert d.device == str(dev / "sr0")
    assert d.vendor == "PIONEER"
    assert d.model == "BD-RW   BDR-209D"
    assert d.release == "1.51"


def test_list_drives_empty_when_no_optical(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    dev.mkdir()
    impl = CyanripImpl(dev_root=dev, sys_block=tmp_path / "sys")
    assert impl.list_drives() == []


def test_list_drives_tolerates_missing_sysfs(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "sr0").write_bytes(b"")
    impl = CyanripImpl(dev_root=dev, sys_block=tmp_path / "nope")
    drives = impl.list_drives()
    assert len(drives) == 1
    assert drives[0].vendor == ""  # sysfs absent → blank, no crash


# --- disc_info (runs `cyanrip -I -N` and parses the report) ---------------


def test_disc_info_runs_info_only_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """disc_info must use info-only mode (-I) with MusicBrainz disabled (-N)
    — identification is local; the GUI does its own MB lookup — and pass the
    selected device."""
    import whipper_gui.adapters.cyanrip_backend as mod

    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "Disc tracks:    16\n"
                "DiscID:         xA2hjkk0Jl0gKKtIdYuTje4JTXY-\n"
                "CDDB ID:        c50a780f\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    info = _impl().disc_info("/dev/sr0")

    argv = seen[0]
    assert "-I" in argv and "-N" in argv
    assert argv[argv.index("-d") + 1] == "/dev/sr0"
    assert info.musicbrainz_disc_id == "xA2hjkk0Jl0gKKtIdYuTje4JTXY-"
    assert info.cddb_disc_id == "c50a780f"
    assert info.num_tracks == 16


def test_disc_info_error_output_degrades_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from whipper_gui.parsers.cd_info import DiscInfo

    _patch_run(monkeypatch, stdout="Unable to read disc TOC!\n")
    assert _impl().disc_info("/dev/sr0") == DiscInfo()


def test_disc_info_raises_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_run(monkeypatch, raises=FileNotFoundError("cyanrip"))
    with pytest.raises(WhipperError, match="not found"):
        _impl().disc_info("/dev/sr0")


# --- version / find_offset (subprocess stubbed) ---------------------------


def test_version_returns_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_run(monkeypatch, stdout="cyanrip 0.9.3.1\n")
    assert _impl().version() == "cyanrip 0.9.3.1"


def test_find_offset_parses_value(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_run(monkeypatch, stdout="Detected drive offset: 667\n")
    assert _impl().find_offset("/dev/sr0") == 667


def test_find_offset_raises_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_run(monkeypatch, stdout="no offset here")
    with pytest.raises(WhipperError):
        _impl().find_offset("/dev/sr0")


def test_run_raises_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_run(monkeypatch, raises=FileNotFoundError("cyanrip"))
    with pytest.raises(WhipperError, match="not found"):
        _impl().version()
