"""The acceptance run's installation checks (`install_health`, `expect-installed`).

The owner, 2026-11-25: the Full run *"should include everything, not just how the
rip runs"*. That day's reinstall left the menu entry and the Desktop icon
pointing at a file that had moved, and logged a traceback on close; these tests
hold the checks that now catch both, and the verb that reports them.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from platterpus import install_health
from platterpus.install_health import Finding
from platterpus.uiscript import health_verbs
from platterpus.uiscript.report import Outcome

_ID = "io.example.App"
_UNINSTALL = "app-uninstall"


def _app(folder: Path, executable: bool = True) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    app = folder / "platterpus-x86_64.AppImage"
    app.write_bytes(b"ELF")
    app.chmod(0o700 if executable else 0o600)
    return app


def _entry(folder: Path, name: str, target: Path, extra: str = "") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.desktop"
    path.write_text(
        f'[Desktop Entry]\nType=Application\nExec="{target}"{extra} %U\n',
        encoding="utf-8",
    )
    return path


def _shortcuts(
    tmp_path: Path, installed: Path | None, *, desktop: bool = True
) -> list[Finding]:
    folder = tmp_path / "Desktop"
    if desktop:
        folder.mkdir(parents=True, exist_ok=True)
    return install_health.check_shortcuts(
        installed,
        desktop_dir=tmp_path / "applications",
        desktop_folder=folder,
        desktop_id=_ID,
        uninstall_name=_UNINSTALL,
    )


def test_exec_target_reads_the_quoted_first_word() -> None:
    text = '[Desktop Entry]\nExec="/home/u/My \\"Apps\\"/x.AppImage" --uninstall\n'
    assert install_health.exec_target(text) == Path('/home/u/My "Apps"/x.AppImage')
    assert install_health.exec_target("[Desktop Entry]\nName=x\n") is None
    assert install_health.exec_target('Exec="unterminated\n') is None


def test_shortcuts_that_launch_the_installed_app_pass(tmp_path: Path) -> None:
    app = _app(tmp_path / "Applications")
    _entry(tmp_path / "applications", _ID, app)
    _entry(tmp_path / "applications", _UNINSTALL, app, " --uninstall")
    _entry(tmp_path / "Desktop", _ID, app)

    found = _shortcuts(tmp_path, app)

    assert [f.ok for f in found] == [True, True, True]


def test_a_shortcut_to_a_file_that_has_moved_fails(tmp_path: Path) -> None:
    """REGRESSION (the owner's log, 2026-11-25): both shortcuts were rewritten to
    the Downloads copy after the app had moved to ~/Applications."""
    app = _app(tmp_path / "Applications")
    gone = tmp_path / "Downloads" / "platterpus-x86_64.AppImage"
    _entry(tmp_path / "applications", _ID, gone)
    _entry(tmp_path / "applications", _UNINSTALL, app, " --uninstall")
    _entry(tmp_path / "Desktop", _ID, gone)

    found = _shortcuts(tmp_path, app)

    failed = [f.text for f in found if f.ok is False]
    assert len(failed) == 2
    assert all("not there" in text for text in failed)


def test_a_missing_entry_another_app_or_a_non_executable_file_fails(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path / "Applications", executable=False)
    other = _app(tmp_path / "Elsewhere")
    _entry(tmp_path / "applications", _ID, app)
    _entry(tmp_path / "applications", _UNINSTALL, other, " --uninstall")
    # No Desktop icon written at all.

    found = _shortcuts(tmp_path, app)

    texts = [f.text for f in found if f.ok is False]
    assert any("not executable" in t for t in texts)
    assert any("not the installed app" in t for t in texts)
    assert any("missing" in t for t in texts)


def test_no_appimage_or_no_desktop_folder_is_reported_not_failed(
    tmp_path: Path,
) -> None:
    assert [f.ok for f in _shortcuts(tmp_path / "a", None)] == [None]
    home = tmp_path / "b"
    app = _app(home / "Applications")
    _entry(home / "applications", _ID, app)
    _entry(home / "applications", _UNINSTALL, app)
    found = _shortcuts(home, app, desktop=False)
    assert [f.ok for f in found] == [True, True, None]


def test_tools_required_fail_and_optional_are_reported(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("cyanrip", "flac"):
        (bin_dir / name).write_text("#!/bin/sh\n")
        os.chmod(bin_dir / name, 0o700)

    found = install_health.check_tools(bin_dir)

    by_text = {f.text.split()[0]: f.ok for f in found}
    assert by_text == {
        "cyanrip": True,
        "flac": True,
        "metaflac": False,
        "cd-paranoia": None,
    }


def test_drive_facts() -> None:
    held = install_health.check_drive_facts("PIONEER BDR", "measured", "measured", True)
    assert [f.ok for f in held] == [True, True]
    missing = install_health.check_drive_facts(
        "PIONEER BDR", "not_measured", "measured", False
    )
    assert [f.ok for f in missing] == [False, False]
    assert [
        f.ok for f in install_health.check_drive_facts("", None, "measured", True)
    ] == [False]


def test_tracebacks_are_found_and_counted() -> None:
    lines = [
        "INFO all fine",
        "ERROR platterpus.workers: stop_thread failed; ignored\nTraceback (most recent call last):\n  ...",
        "ERROR deliberate refusal, no traceback",
        "ERROR other\nTraceback (most recent call last):\n  x",
    ]
    assert install_health.count_tracebacks(lines) == 2
    shown = install_health.find_tracebacks(lines, limit=1)
    assert len(shown) == 1 and "stop_thread failed" in shown[0]
    assert install_health.find_tracebacks(["INFO ok"]) == []


# --- The verb ------------------------------------------------------------------


class _Runner(health_verbs.HealthVerbsMixin):
    """The mixin with the two runner methods it calls, recording what it records."""

    def __init__(self, lines: list[str] | None) -> None:
        self._window: Any = object()
        self.records: list[tuple[Outcome, str]] = []
        self._lines = lines

    def _record(self, step: Any, outcome: Outcome, detail: str = "", **_: Any) -> None:
        self.records.append((outcome, detail))

    def _session_log(self) -> tuple[list[str] | None, str]:
        return self._lines, "3 line(s) logged since launch"


class _Step:
    def __init__(self, *args: str) -> None:
        self.args = list(args)


def test_the_log_aspect_fails_on_a_traceback_and_passes_without() -> None:
    bad = _Runner(["INFO x", "ERROR y\nTraceback (most recent call last):\n z"])
    bad._do_expect_installed(_Step("log"))  # type: ignore[arg-type]  # a minimal step
    assert bad.records[0][0] is Outcome.FAIL
    assert "1 traceback" in bad.records[0][1]

    good = _Runner(["INFO x"])
    good._do_expect_installed(_Step("log"))  # type: ignore[arg-type]  # a minimal step
    assert good.records[0][0] is Outcome.PASS

    unread = _Runner(None)
    unread._do_expect_installed(_Step("log"))  # type: ignore[arg-type]  # a minimal step
    assert unread.records[0][0] is Outcome.INFO


def test_an_unknown_aspect_is_an_error_and_diagnostics_is_info() -> None:
    runner = _Runner([])
    runner._do_expect_installed(_Step("everything"))  # type: ignore[arg-type]  # a minimal step
    runner._do_expect_installed(_Step("diagnostics"))  # type: ignore[arg-type]  # a minimal step
    assert [r[0] for r in runner.records] == [Outcome.ERROR, Outcome.INFO]


def test_the_shortcuts_aspect_follows_a_moved_appimage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`$APPIMAGE` still names Downloads after the first-run move; the check reads
    the shortcuts against where the file went."""
    from platterpus import appimage_integration as ai

    app = _app(tmp_path / "Applications")
    monkeypatch.setenv("APPIMAGE", str(tmp_path / "Downloads" / app.name))
    monkeypatch.setattr(ai, "APPLICATIONS_DIR", tmp_path / "Applications")
    assert health_verbs.installed_appimage() == app

    monkeypatch.delenv("APPIMAGE")
    assert health_verbs.installed_appimage() is None
