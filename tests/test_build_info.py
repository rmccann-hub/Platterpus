"""Tests for platterpus.build_info (build fingerprint + install channel + env)."""

from __future__ import annotations

from pathlib import Path

from platterpus import build_info


def test_build_fingerprint_is_source_without_stamp() -> None:
    # A source checkout has no generated _build.py → the "source" sentinel.
    assert build_info.build_fingerprint() == "source"


def test_build_fingerprint_reads_generated_stamp(monkeypatch, tmp_path) -> None:
    # Simulate build_appimage.sh having written _build.py: a fake module on the
    # import path with BUILD_FINGERPRINT set is picked up.
    import sys
    import types

    fake = types.ModuleType("platterpus._build")
    fake.BUILD_FINGERPRINT = "abc1234"
    monkeypatch.setitem(sys.modules, "platterpus._build", fake)
    assert build_info.build_fingerprint() == "abc1234"


def test_build_fingerprint_never_raises_on_broken_stamp(monkeypatch) -> None:
    import sys
    import types

    fake = types.ModuleType("platterpus._build")
    # No BUILD_FINGERPRINT attribute at all → ImportError inside → sentinel.
    monkeypatch.setitem(sys.modules, "platterpus._build", fake)
    assert build_info.build_fingerprint() == "source"


def test_install_channel_appimage(monkeypatch) -> None:
    monkeypatch.setenv("APPIMAGE", "/home/user/platterpus-x86_64.AppImage")
    assert build_info.install_channel() == "appimage"


def test_install_channel_pipx(monkeypatch) -> None:
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setattr(
        build_info.sys, "prefix", str(Path.home() / ".local/pipx/venvs/platterpus")
    )
    assert build_info.install_channel() == "pipx"


def test_install_channel_source(monkeypatch) -> None:
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setattr(build_info.sys, "prefix", "/home/user/Platterpus/.venv")
    assert build_info.install_channel() == "source"


def test_environment_report_shape_and_never_raises() -> None:
    env = build_info.environment_report()
    assert set(env) == {"python", "platform", "pyside6", "install_channel"}
    # Python version is always determinable in-process.
    assert isinstance(env["python"], str) and env["python"]
    assert env["install_channel"] in {"appimage", "pipx", "source"}
