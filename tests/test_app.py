"""Tests for platterpus.app.

`main()` constructs heavy components (QApplication, real subprocess
adapters); tests focus on the lightweight paths — argparse, the
`--version` short-circuit — and on importing the module without
crashes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from platterpus import __version__
from platterpus import app as app_module


def test_prefer_xwayland_sets_platform_on_wayland(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On a Wayland session, prefer XWayland (with a native-Wayland fallback) to
    dodge the Plasma 6 black-window repaint bug."""
    import os

    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    app_module._prefer_xwayland_on_wayland()
    assert os.environ["QT_QPA_PLATFORM"] == "xcb;wayland"


def test_prefer_xwayland_via_wayland_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """WAYLAND_DISPLAY alone (no XDG_SESSION_TYPE) still counts as Wayland."""
    import os

    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    app_module._prefer_xwayland_on_wayland()
    assert os.environ["QT_QPA_PLATFORM"] == "xcb;wayland"


def test_prefer_xwayland_respects_user_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit QT_QPA_PLATFORM is never overridden."""
    import os

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("QT_QPA_PLATFORM", "wayland")
    app_module._prefer_xwayland_on_wayland()
    assert os.environ["QT_QPA_PLATFORM"] == "wayland"


def test_prefer_xwayland_noop_off_wayland(monkeypatch: pytest.MonkeyPatch) -> None:
    """On X11 (or no display), the platform is left untouched."""
    import os

    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    app_module._prefer_xwayland_on_wayland()
    assert "QT_QPA_PLATFORM" not in os.environ


def test_main_version_flag_prints_and_exits(capsys: pytest.CaptureFixture) -> None:
    """--version exits via SystemExit before any heavy construction."""
    with pytest.raises(SystemExit) as excinfo:
        app_module.main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    # argparse may print to stdout or stderr depending on version.
    # Verify the version string appears at least once in either stream.
    assert "platterpus" in out


def test_main_version_text_matches_package_version(
    capsys: pytest.CaptureFixture,
) -> None:
    """The version string includes the package's __version__."""
    with pytest.raises(SystemExit):
        app_module.main(["--version"])
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert __version__ in combined


def test_main_version_includes_build_fingerprint(
    capsys: pytest.CaptureFixture,
) -> None:
    """`--version` also reports the build fingerprint (the exact git SHA in a
    built AppImage, the "source" sentinel in a checkout) so a bug report carries
    the precise build, not just the marketing version — the version audit gap."""
    from platterpus.build_info import build_fingerprint

    with pytest.raises(SystemExit):
        app_module.main(["--version"])
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert f"({build_fingerprint()})" in text


def test_installed_metadata_matches_canonical_version() -> None:
    """The build's dynamic version must equal the single source of truth.

    `__version__` in `platterpus/__init__.py` is canonical; `pyproject.toml`
    reads it via `[tool.setuptools.dynamic]`. If that wiring breaks, the
    installed package metadata would drift from `__version__` — catch it here.
    Skips when the package isn't installed (e.g. a raw source run).
    """
    import importlib.metadata as metadata

    try:
        installed = metadata.version("platterpus")
    except metadata.PackageNotFoundError:
        pytest.skip("platterpus not installed; nothing to compare against")
    assert installed == __version__


def test_main_unknown_flag_exits_non_zero(
    capsys: pytest.CaptureFixture,
) -> None:
    """argparse rejects unknown flags."""
    with pytest.raises(SystemExit) as excinfo:
        app_module.main(["--bogus-flag"])
    # argparse returns 2 for argument errors.
    assert excinfo.value.code != 0


def test_main_module_is_importable() -> None:
    """The bare import path used by `python -m platterpus` works."""
    # This re-imports a known package; sanity check that no module-level
    # side effects (Qt construction, subprocess calls) happen on import.
    import importlib

    module = importlib.reload(app_module)
    assert hasattr(module, "main")
    assert callable(module.main)


# --- Crash handler -------------------------------------------------------


def test_show_fatal_dialog_noops_without_qapplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fatal-error dialog must be safe to call when no QApplication
    exists (the GUI itself failed to come up): it should quietly no-op
    rather than raise — and never block on a modal exec()."""
    from PySide6.QtWidgets import QApplication

    # Force the "no QApplication" branch regardless of whether another
    # test in this process already constructed one (which would otherwise
    # pop a blocking modal dialog).
    monkeypatch.setattr(QApplication, "instance", staticmethod(lambda: None))
    app_module._show_fatal_dialog("test", RuntimeError("boom"))  # must not raise


def test_install_excepthook_sets_and_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    """_install_excepthook installs a hook that routes normal exceptions to
    the dialog and passes KeyboardInterrupt through to the default hook."""
    import sys

    shown: list[tuple[str, BaseException]] = []
    monkeypatch.setattr(
        app_module, "_show_fatal_dialog", lambda title, exc: shown.append((title, exc))
    )

    original = sys.excepthook
    try:
        app_module._install_excepthook()
        assert sys.excepthook is not original

        err = ValueError("kaboom")
        sys.excepthook(ValueError, err, None)
        assert shown and shown[-1][1] is err

        shown.clear()
        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
        assert shown == []  # KeyboardInterrupt is not routed to the dialog
    finally:
        sys.excepthook = original


def test_main_ctdb_calibrate_flag_runs_diagnostics_and_exits(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """`platterpus --ctdb-calibrate <folder>` short-circuits into the CTDB
    diagnostics (calibrate mode) before QApplication and returns its exit code —
    so the maintainer can pin the CTDB CRC straight from the AppImage (KDD-16)."""
    import platterpus.ctdb.diagnose as diag

    calls: list[tuple[object, bool]] = []

    def _fake(folder, *, calibrate_crc):
        calls.append((folder, calibrate_crc))
        return 0

    monkeypatch.setattr(diag, "run_diagnostics", _fake)
    # A MainWindow being constructed would mean the flag was ignored.
    import platterpus.ui.main_window as mw

    monkeypatch.setattr(
        mw,
        "MainWindow",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("main window built")),
    )

    rc = app_module.main(["--ctdb-calibrate", str(tmp_path)])
    assert rc == 0
    assert calls == [(tmp_path, True)]


def test_main_uninstall_flag_opens_uninstaller_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`platterpus --uninstall` (the Uninstall menu entry) opens just the
    uninstaller dialog — no adapters, no main window."""
    import platterpus.ui.uninstall_dialog as ud
    from platterpus import app as app_module

    opened: list[bool] = []

    class _FakeDialog:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            opened.append(True)
            return 0

    monkeypatch.setattr(ud, "UninstallDialog", _FakeDialog)
    # A MainWindow being constructed would mean the flag was ignored.
    import platterpus.ui.main_window as mw

    monkeypatch.setattr(
        mw,
        "MainWindow",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("main window built")),
    )

    assert app_module.main(["--uninstall"]) == 0
    assert opened == [True]


# --- --compare / --assemble-best-of routing (0.4.24) ------------------------


def _stub_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize config load + logging so a CLI-diagnostic path can run without
    touching the real user config/log (these run before the diagnostic handler)."""
    monkeypatch.setattr("platterpus.logging_setup.configure_logging", lambda: None)
    monkeypatch.setattr("platterpus.logging_setup.set_debug_logging", lambda v: None)

    class _Cfg:
        debug_logging = False

    monkeypatch.setattr("platterpus.config.load", lambda: _Cfg())


def test_compare_flag_routes_to_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_startup(monkeypatch)
    seen: dict = {}

    def _fake(prev, later, **kw):  # type: ignore[no-untyped-def]
        seen["args"] = (prev, later)
        return 7

    monkeypatch.setattr("platterpus.cli_compare.run_compare", _fake)
    rc = app_module.main(["--compare", "prev.json", "later.json"])
    assert rc == 7
    assert [str(p) for p in seen["args"]] == ["prev.json", "later.json"]


def test_assemble_best_of_flag_routes_to_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_startup(monkeypatch)
    seen: dict = {}

    def _fake(dest, a, b):  # type: ignore[no-untyped-def]
        seen["args"] = (dest, a, b)
        return 0

    monkeypatch.setattr("platterpus.cli_compare.run_assemble_best_of", _fake)
    rc = app_module.main(["--assemble-best-of", "Best", "a.json", "b.json"])
    assert rc == 0
    assert [str(p) for p in seen["args"]] == ["Best", "a.json", "b.json"]


# --- Crash-handler safety (audit, 2026-07-29) --------------------------------


def test_thread_exceptions_are_logged_not_lost(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Regression: exceptions on a plain `threading.Thread` went NOWHERE.

    `sys.excepthook` does not cover `threading.Thread` — CPython routes those to
    `threading.excepthook`, whose default writes to stderr and returns. An AppImage
    launched from the applications menu has no attached stderr, so every failure in
    the fire-and-forget post-rip daemon threads was invisible: not the log, not the
    report, not the screen. The user saw a step silently never finish and filed a bug
    report containing no evidence it had ever run.
    """
    import threading

    from platterpus.app import _install_excepthook

    original_sys, original_thread = sys.excepthook, threading.excepthook
    try:
        _install_excepthook()

        def _boom() -> None:
            raise ValueError("post-rip step blew up")

        worker = threading.Thread(target=_boom, name="post-rip-probe")
        with caplog.at_level("ERROR"):
            worker.start()
            worker.join(10)
        assert not worker.is_alive()
    finally:
        sys.excepthook, threading.excepthook = original_sys, original_thread

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "post-rip-probe" in messages, (
        f"the thread's failure never reached the log. Records: {messages!r}"
    )
    assert any(r.exc_info for r in caplog.records), (
        "logged without exc_info, so the traceback — the only actionable part — is "
        "still lost."
    )


def test_the_fatal_dialog_refuses_to_build_widgets_off_the_gui_thread(
    qapp: object, caplog: pytest.LogCaptureFixture
) -> None:
    """A crash handler that is unsafe exactly when it is needed is worse than none.

    An exception escaping a slot on a worker QThread invokes `sys.excepthook` **on
    that worker thread**, so `_show_fatal_dialog` would construct a QMessageBox and
    enter a nested event loop off the GUI thread — which Qt forbids for widgets. Two
    failure modes: undefined behaviour on a real platform, and `exec()` never
    returning, so the worker's `finished` never fires and its thread is abandoned.

    Runs the handler on a real worker thread and asserts it logs instead of drawing.
    """
    import threading

    from platterpus.app import _show_fatal_dialog

    def _call_off_thread() -> None:
        _show_fatal_dialog("test", RuntimeError("from a worker thread"))

    worker = threading.Thread(target=_call_off_thread, name="off-gui-probe")
    with caplog.at_level("ERROR"):
        worker.start()
        worker.join(10)

    assert not worker.is_alive(), (
        "the handler never returned — it most likely entered QMessageBox.exec() off "
        "the GUI thread, which is the hang this guard exists to prevent."
    )
    # `getMessage()` formats lazily, so this assertion doubles as a check that the
    # handler's own log call is safe to format LATER: an earlier version passed the
    # live QThread as a `%s` arg and this line raised
    # "libshiboken: Internal C++ object already deleted" once the worker had exited.
    # A crash handler whose log call can itself throw is not a crash handler.
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "non-GUI thread" in messages, (
        "the off-thread call was not recognised and logged; it either drew a widget "
        f"off the GUI thread or reported nothing. Records: {messages!r}"
    )
    assert "off-gui-probe" in messages, (
        "the log line does not name the thread, so a reader cannot tell which "
        f"background task failed. Records: {messages!r}"
    )


# --- termination signals (the 2026-07-01 bug through a third door) ----------


def test_termination_handlers_close_the_window_and_quit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIGTERM/SIGINT must go through the real `closeEvent`, not kill us dead.

    `closeEvent` was the ONLY thing that stopped the in-container reader. podman
    does not forward signals into the container, so a session logout or
    `kill <pid>` during a rip left cyanrip ripping and holding the drive — and the
    drive ignores its own eject button while a read holds the device, so there was
    no in-app *and* no hardware way out.

    The handler deliberately does almost nothing (it runs between arbitrary
    bytecodes); the QTimer slot does the work. So this test drives the timer's
    signal directly, which is exactly what the event loop would do.
    """
    import signal

    from PySide6.QtWidgets import QApplication

    closed: list[bool] = []
    quit_called: list[bool] = []

    class _FakeWindow:
        def close(self) -> None:
            closed.append(True)

    # The QTimer needs a real QObject parent, so the real application object is
    # used and its `quit` is intercepted — a fake app would not be a valid parent,
    # and asserting on a fake whose `quit` is never reached is how this test
    # passed while proving nothing the first time it was written.
    qapp = QApplication.instance() or QApplication([])
    monkeypatch.setattr(qapp, "quit", lambda: quit_called.append(True))

    # Save and restore the process-wide handlers. Leaking a SIGTERM handler into
    # the rest of the suite would be a real bug in this test, not a detail.
    saved = {sig: signal.getsignal(sig) for sig in app_module._TERMINATION_SIGNALS}
    try:
        timer = app_module._install_termination_handlers(
            qapp,
            _FakeWindow(),  # type: ignore[arg-type]  # only close() is used
        )
        assert timer is not None, "handlers must install on the main thread"
        try:
            # Nothing has arrived yet: a tick must NOT tear the app down.
            timer.timeout.emit()
            assert closed == [] and quit_called == [], (
                "the timer ticks constantly; it must be inert until a signal lands"
            )

            # Now deliver SIGTERM the way the OS would — through the installed
            # handler. Calling the handler directly (rather than os.kill) keeps the
            # test from depending on signal-delivery timing.
            handler = signal.getsignal(signal.SIGTERM)
            assert callable(handler), "SIGTERM must have a callable handler installed"
            handler(signal.SIGTERM, None)

            timer.timeout.emit()
            assert closed == [True], (
                "the window must be CLOSED, so the real closeEvent stops the rip "
                "and frees the drive — never a second copy of the teardown"
            )
            assert quit_called == [True], "and the app must actually exit"
        finally:
            timer.stop()
    finally:
        for sig, previous in saved.items():
            signal.signal(sig, previous)


def test_termination_handlers_degrade_when_signals_cannot_be_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`signal.signal` raises ValueError off the main thread — the normal case
    under a test runner or an embedded interpreter. That must not stop the app
    from starting; it just keeps the old behaviour for that signal."""
    import signal as signal_module

    def refuse(_sig: int, _handler: object) -> object:
        raise ValueError("signal only works in main thread")

    monkeypatch.setattr(app_module.signal, "signal", refuse)
    result = app_module._install_termination_handlers(
        object(),  # type: ignore[arg-type]  # never touched on this path
        object(),  # type: ignore[arg-type]
    )
    assert result is None, "no handlers installed → no timer to keep alive"
    # And the real handlers are untouched.
    assert signal_module.getsignal(signal_module.SIGTERM) is not refuse


# --- CLI path arguments (audit, 2026-07-31) ----------------------------------
#
# `argparse`'s `type=Path` constructs a Path; it validates nothing. So a folder
# argument reached the code unchecked: a missing folder was reported as "No .flac
# files found in …" (the wrong subsystem, preceded by an unrelated warning about a
# missing rip log), and a relative folder named "-x" ("./-x" normalises to "-x")
# produced "-x/track.flac" argv entries that `flac`/`metaflac` parse as OPTIONS.


def test_ctdb_calibrate_rejects_a_missing_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture
) -> None:
    """A specific error naming the folder — never the misleading "no FLACs"."""
    import platterpus.ctdb.diagnose as diag

    monkeypatch.setattr(
        diag,
        "run_diagnostics",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("diagnostics ran")),
    )
    rc = app_module.main(["--ctdb-calibrate", str(tmp_path / "not-there")])
    assert rc == 2
    out = capsys.readouterr().out
    assert "does not exist" in out
    assert "not-there" in out


def test_ctdb_calibrate_rejects_a_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture
) -> None:
    import platterpus.ctdb.diagnose as diag

    monkeypatch.setattr(
        diag,
        "run_diagnostics",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("diagnostics ran")),
    )
    target = tmp_path / "album.flac.json"
    target.write_text("{}", encoding="utf-8")
    rc = app_module.main(["--ctdb-calibrate", str(target)])
    assert rc == 2
    assert "not a folder" in capsys.readouterr().out


def test_ctdb_calibrate_hands_diagnostics_an_absolute_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """The dependency-argument half of the rule: an absolute path can never be
    mistaken for an option by `flac`/`metaflac`, because it starts with "/"."""
    import platterpus.ctdb.diagnose as diag

    seen: list[object] = []
    monkeypatch.setattr(
        diag, "run_diagnostics", lambda folder, **k: (seen.append(folder), 0)[1]
    )
    dashed = tmp_path / "-x"
    dashed.mkdir()
    monkeypatch.chdir(tmp_path)

    rc = app_module.main(["--ctdb-calibrate", "./-x"])
    assert rc == 0
    assert len(seen) == 1
    folder = seen[0]
    assert isinstance(folder, Path)
    assert folder.is_absolute()
    assert str(folder).startswith("/")


def test_doctor_prints_the_config_reset_notice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """`--doctor` is the no-GUI front end, so a reset that only reached the log
    file would be the same silent reset the GUI notice exists to prevent (a reset
    `read_offset` rips the next disc at the wrong offset)."""
    from platterpus import config as config_module
    from platterpus import preflight
    from platterpus import settings_validation as sv

    monkeypatch.setattr(config_module, "load", lambda: config_module.Config())
    monkeypatch.setattr(
        config_module,
        "take_load_resets",
        lambda: [
            sv.ResetRecord(
                field="read_offset",
                message="Read offset must be between -5000 and 5000.",
                old_value="99999",
                new_value="0",
            )
        ],
    )
    monkeypatch.setattr(preflight, "run_preflight", lambda ctx, **k: [])
    monkeypatch.setattr(preflight, "format_details", lambda results: "")
    monkeypatch.setattr(preflight, "format_summary", lambda results, **k: "ok")
    monkeypatch.setattr(preflight, "exit_code", lambda results: 0)

    rc = app_module.main(["--doctor"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Read offset must be between -5000 and 5000." in out
    assert "99999" in out
