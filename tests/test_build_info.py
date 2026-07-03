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


def test_dependency_summary_from_report() -> None:
    from types import SimpleNamespace as NS

    report = NS(
        ok=[NS(dep_id="cyanrip"), NS(dep_id="flac")],
        ok_versions={"cyanrip": (0, 9, 3), "flac": (1, 4, 0)},
        ok_probes={
            "cyanrip": NS(location="/home/u/.local/bin/cyanrip"),
            "flac": NS(location="/usr/bin/flac"),
        },
        missing=[
            NS(
                spec=NS(dep_id="picard"),
                probe=NS(present=False, version=None, location=None),
            )
        ],
    )
    summary = build_info.dependency_summary(report)
    assert summary["cyanrip"] == {
        "present": True,
        "version": "0.9.3",
        "location": "/home/u/.local/bin/cyanrip",
        "min_version_met": True,
    }
    assert summary["flac"]["version"] == "1.4.0"
    assert summary["picard"] == {
        "present": False,
        "version": None,
        "location": None,
        "min_version_met": False,
    }


def test_dependency_summary_never_raises_on_junk() -> None:
    # A non-report object degrades to an empty summary, never an exception.
    assert build_info.dependency_summary(object()) == {}
