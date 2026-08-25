"""Tests for platterpus.app.

`main()` constructs heavy components (QApplication, real subprocess
adapters); tests focus on the lightweight paths — argparse, the
`--version` short-circuit — and on importing the module without
crashes.
"""

from __future__ import annotations

import logging
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


# --- --install-ripper: the no-GUI front end for the setup wizard -------------
#
# WHY THIS FLAG NEEDS TESTS OF ITS OWN. It exists because the wizard ships
# *inside* a release, so a user on an older build has no in-app route to a newer
# cyanrip pin — and the pin moves every handshake round (it moved twice in one
# day: round 6 asked for `ad65a24`, round 6b withdrew it hours later). The flag
# is the route, and the thing that can go quietly wrong is its *verdict*: report
# success when the ripper is unusable, or failure when only the optional
# cd-paranoia probe (KDD-29, deliberately last) did not resolve.


def _install_ripper_stub(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ready: bool,
    failures: tuple[str, ...] = (),
) -> list[str]:
    """Replace HostSetup with a stub whose readiness and failures are chosen.

    Returns the list the stub records its printed titles into, so a test can
    assert the progress callback was actually wired rather than ignored. The stub
    class also records its construction kwargs on ``_Stub.last_kwargs``, reachable
    via ``host_setup_module.HostSetup.last_kwargs``.
    """
    from platterpus import config as config_module
    from platterpus.deps import host_setup as host_setup_module
    from platterpus.deps import step_engine

    monkeypatch.setattr(config_module, "load", lambda: config_module.Config())
    seen: list[str] = []

    class _Stub:
        #: The kwargs the CLI constructed it with, so a test can assert WHICH fork
        #: target was threaded through. Without this the override could resolve
        #: correctly for the banner and still build the pinned commit — the print and
        #: the build are two different reads, and this repo has already shipped that
        #: exact divergence once.
        last_kwargs: dict[str, object] = {}

        def __init__(self, *a: object, **kw: object) -> None:
            _Stub.last_kwargs = dict(kw)

        def run(
            self,
            progress: object = None,
            dry_run: bool = False,
            cancelled: object = None,
        ) -> list[step_engine.StepResult]:
            results = [
                step_engine.StepResult(
                    "container",
                    "Container",
                    step_engine.StepStatus.DONE,
                    "already present",
                )
            ]
            for title in failures:
                results.append(
                    step_engine.StepResult(
                        title.lower(),
                        title,
                        step_engine.StepStatus.FAILED,
                        "no package",
                    )
                )
            for r in results:
                seen.append(r.title)
                if callable(progress):
                    progress(r)
            return results

        def is_ready(self) -> bool:
            return ready

    monkeypatch.setattr(host_setup_module, "HostSetup", _Stub)
    return seen


def test_install_ripper_reports_ready_and_names_the_pin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The pin is printed because it is the one fact the user cannot check any
    other way before a rip: two builds of this fork differ only by their build
    tag, and one of them (`ad65a24`) returns silence on disc images."""
    from platterpus.deps.fork_source import WIZARD_TARGET

    seen = _install_ripper_stub(monkeypatch, ready=True)
    rc = app_module.main(["--install-ripper"])
    out = capsys.readouterr().out
    assert rc == 0
    assert WIZARD_TARGET.pin in out, "the pin being built is not stated"
    assert WIZARD_TARGET.banner in out
    assert "ready" in out.casefold()
    assert seen, "the progress callback was never called — steps ran silently"
    assert "Container" in out, "step results were not printed as they landed"


def test_install_ripper_succeeds_when_only_an_optional_step_failed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """cd-paranoia is optional and runs LAST (KDD-29): the cache verdict goes
    unmeasured, the ripper is fully installed. Keying the exit code on "no step
    failed" would tell a user with a working ripper that setup failed."""
    _install_ripper_stub(monkeypatch, ready=True, failures=("Cache probe",))
    rc = app_module.main(["--install-ripper"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ready" in out.casefold()
    # And it does not hide the miss — an unmeasured cache verdict is a fact.
    assert "Cache probe" in out


def test_install_ripper_fails_and_points_at_the_log(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A failed install must name the step AND where the dependency's own output
    went. Every command's argv and combined output goes to the log via
    SubprocessRunner; a failure message without that pointer is a diagnosis the
    user cannot reach (the diagnostic-completeness rule)."""
    from platterpus.paths import LOG_PATH

    _install_ripper_stub(monkeypatch, ready=False, failures=("Build cyanrip fork",))
    rc = app_module.main(["--install-ripper"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Build cyanrip fork" in out
    assert str(LOG_PATH) in out


# --- --install-ripper <commit>: reaching a pin that moved without a release -------
#
# `CLAUDE.md` Critical rule #12 says a moving fork pin needs a route to it that does
# not ship inside a release, and names `--install-ripper` as that route. It was half
# true: the flag existed, but it built a module constant, so a new pin still needed a
# Platterpus release — the granularity the rule calls wrong. The fork's pin moved
# FIVE times inside round 7, twice in one day.


def test_install_ripper_builds_the_pinned_commit_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ALLOW case, and first: an override that broke the default would be worse
    than no override."""
    from platterpus.deps import host_setup as host_setup_module
    from platterpus.deps.fork_source import WIZARD_TARGET

    _install_ripper_stub(monkeypatch, ready=True)
    assert app_module.main(["--install-ripper"]) == 0
    target = host_setup_module.HostSetup.last_kwargs.get("fork_target")
    # On the PIN, not on `is None`. The CLI resolves the default to `WIZARD_TARGET`
    # explicitly, which is equivalent to passing nothing — asserting `is None` would be
    # testing the mechanism rather than the behaviour, and it failed for that reason.
    assert target is not None and target.pin == WIZARD_TARGET.pin, (
        f"a bare --install-ripper is no longer building the pinned build: {target!r}"
    )
    assert WIZARD_TARGET.banner in capsys.readouterr().out


def test_install_ripper_with_a_commit_builds_that_commit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from platterpus.deps import host_setup as host_setup_module

    _install_ripper_stub(monkeypatch, ready=True)
    assert app_module.main(["--install-ripper", "deadbee"]) == 0
    target = host_setup_module.HostSetup.last_kwargs.get("fork_target")
    # THE ASSERTION THAT MATTERS: the target reaches the thing that BUILDS, not just
    # the line that prints. Those are separate reads, and naming one while building
    # the other is a failure this repo has shipped before.
    assert target is not None and target.pin == "deadbee", (
        f"the supplied commit did not reach HostSetup: {target!r}"
    )
    out = capsys.readouterr().out
    assert "deadbee" in out
    assert "platterpus-fork-gdeadbee" in out, "the tag a correct build must print"
    # It is not the approved build, and the install must say so BEFORE the build, not
    # leave the rip report to be the first place it surfaces.
    assert "unapproved" in out


def test_an_operator_commit_does_not_invent_a_version_string(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """We cannot read an arbitrary commit's `meson.build`, so we must not print a
    version next to the word "expects" — that invites a comparison against a number
    nobody measured. The tag is verifiable; the version is declared unknown."""
    from platterpus.deps.fork_source import FORK_TEST_VERSION

    _install_ripper_stub(monkeypatch, ready=True)
    app_module.main(["--install-ripper", "deadbee"])
    out = capsys.readouterr().out
    assert FORK_TEST_VERSION not in out, (
        "the pinned build's version was printed for a different commit, which is a "
        "claim about a tree we never read"
    )
    assert "not predictable" in out


def test_install_ripper_with_the_approved_pin_does_not_call_it_unapproved(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Naming the approved pin explicitly must not produce "this is not X (X)".

    **Measured on the rig, 2026-08-14.** `--install-ripper ddf7ac3` — the pin a
    closed round approved — printed *"NOT a pinned build, and no round has
    approved it"* and *"NOTE: this is not the handshake-approved build
    (ddf7ac3)"*, then predicted every rip would report `unapproved`. Ninety
    seconds later `--rig-check` reported `OK ripper/handshake approved` for that
    same binary, because approval is decided by the installed build tag, not by
    how the install was requested.

    The cause was a whole-object comparison: `target_for_commit` returns a
    ForkTarget whose `version` and `why` differ by construction, so
    `target != PRODUCTION_TARGET` held even when the pins were identical. This
    covers the `app.py` half — the note itself — which the `fork_source` tests
    cannot reach.
    """
    from platterpus.deps.fork_source import PRODUCTION_TARGET

    _install_ripper_stub(monkeypatch, ready=True)
    assert app_module.main(["--install-ripper", PRODUCTION_TARGET.pin]) == 0
    out = capsys.readouterr().out
    assert "this is not the handshake-approved build" not in out, (
        "installing the approved pin by name announced it is not the approved "
        f"build — the 2026-08-14 rig contradiction. Output:\n{out}"
    )
    assert "unapproved" not in out, (
        "the install predicted rips would report unapproved; --rig-check reports "
        f"approved for this exact build. Output:\n{out}"
    )


def test_the_unapproved_note_still_fires_for_a_different_commit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-triviality floor for the test above.

    A "fix" that deleted the note entirely would satisfy the previous test and
    remove the warning that matters — a test pin really does report `unapproved`
    on every rip, and the install is the honest place to say so.
    """
    _install_ripper_stub(monkeypatch, ready=True)
    app_module.main(["--install-ripper", "0badc0de"])
    out = capsys.readouterr().out
    assert "this is not the handshake-approved build" in out
    assert "unapproved" in out


def test_startup_logs_the_argv_it_was_invoked_with(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The run's own argv must reach the log, not just its version.

    **Measured 2026-08-14.** The rig's installed ripper silently changed from
    the approved pin to a different build. `~/.local/share/platterpus/log.txt`
    showed a second `platterpus … starting` at the exact minute, followed by the
    full build/install/export sequence — but *not which pin it had been asked
    for*, so the question could only be answered from the operator's shell
    history. No bug report carries shell history.

    Critical rule #12 requires the exact argv of every dependency we spawn. The
    same reasoning applies to our own invocation, because this program's
    behaviour changes completely by flag: `--install-ripper` rebuilds and
    replaces the ripper; `--doctor` touches nothing.
    """
    _install_ripper_stub(monkeypatch, ready=True)
    with caplog.at_level("INFO", logger="platterpus.app"):
        app_module.main(["--install-ripper", "0badc0de"])
    startup = [r for r in caplog.records if "starting" in r.getMessage()]
    assert startup, "no startup line logged at all"
    message = startup[0].getMessage()
    assert "0badc0de" in message, (
        "the startup line does not record the argv, so a log cannot say which "
        f"pin an --install-ripper run was asked for. Logged: {message!r}"
    )


def test_the_startup_line_survives_a_flag_with_no_argument(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Non-triviality floor for the test above.

    The argv addition must not make the startup line conditional on there being
    an interesting argument to print — a run with a bare flag still needs its
    marker in the log, and it must still name the flag.

    (`--version` deliberately is not used here: argparse's version action exits
    inside `parse_args`, before `configure_logging()`, so it logs nothing at all
    by design. Asserting otherwise would pin a behaviour we do not have.)
    """
    _install_ripper_stub(monkeypatch, ready=True)
    with caplog.at_level("INFO", logger="platterpus.app"):
        app_module.main(["--install-ripper"])
    startup = [r for r in caplog.records if "starting" in r.getMessage()]
    assert startup, "a startup line must be logged for a bare flag too"
    assert "install-ripper" in startup[0].getMessage(), (
        f"the flag itself is missing from the startup line: {startup[0].getMessage()!r}"
    )


def test_install_ripper_list_shows_the_menu_and_installs_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--install-ripper list` is a query, not an action.

    The dangerous failure is not a wrong menu — it is a menu that *installs*.
    This asserts the step engine was never constructed, so listing cannot
    replace the ripper the operator is currently using.
    """
    from platterpus.deps import host_setup as host_setup_module
    from platterpus.deps.fork_source import PRODUCTION_TARGET

    seen = _install_ripper_stub(monkeypatch, ready=True)
    host_setup_module.HostSetup.last_kwargs = {}
    assert app_module.main(["--install-ripper", "list"]) == 0
    out = capsys.readouterr().out

    assert PRODUCTION_TARGET.build_tag in out, "the menu does not name the build tag"
    assert PRODUCTION_TARGET.pin in out
    assert not seen, f"listing ran install steps: {seen}"
    assert not host_setup_module.HostSetup.last_kwargs, (
        "listing constructed the installer — a query must not be able to "
        "replace the ripper the operator is currently ripping with"
    )


def test_install_ripper_list_is_case_and_space_tolerant(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Typed by a person at a terminal, so ' List ' must work too."""
    _install_ripper_stub(monkeypatch, ready=True)
    assert app_module.main(["--install-ripper", " List "]) == 0
    assert "install" in capsys.readouterr().out.lower()


def test_a_real_commit_still_installs_rather_than_listing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-triviality floor: a guard that swallowed every value would satisfy
    the tests above and break installing entirely."""
    from platterpus.deps import host_setup as host_setup_module

    _install_ripper_stub(monkeypatch, ready=True)
    assert app_module.main(["--install-ripper", "0badc0de"]) == 0
    target = host_setup_module.HostSetup.last_kwargs.get("fork_target")
    assert target is not None and target.pin == "0badc0de"


# --- The unattended run must end itself, but not early -----------------------


def test_the_unattended_quit_waits_for_post_rip_work_before_quitting(qapp) -> None:
    """`--run-script` now ends the process — but the BATCH ending is not the WORK
    ending, and quitting on the wrong one truncates the evidence.

    Maintainer, 2026-08-19: *"we shouldn't need to hard quit these consoles if
    they are done actually."* The run left the window open, so the launching
    terminal kept a live `python3.12` and Konsole asked "There is a process
    running in this window" on close; on the rig it sat idle five and a half
    minutes until a person clicked through.

    The trap is the obvious fix. On that same run the script finished at
    17:51:15.8 and the rip's own evidence bundle sealed at **17:51:18.4** — after
    CTDB, the FLAC verify and the checksums landed. Connecting to the runner's
    `finished` would have killed the process in that gap and truncated exactly
    the artifact this release exists to make trustworthy. So the quit is gated on
    the same settlement predicate the bundle waits on.

    Driven through the real helper with stand-ins for the three collaborators, so
    what is under test is the GATE rather than a description of it.
    """
    from platterpus.app import _arm_unattended_quit

    quits: list[int] = []
    state = {"running": True, "pending": object(), "settled": False}

    class _Runner:
        @property
        def running(self) -> bool:
            return bool(state["running"])

    class _Console:
        @property
        def runner(self):
            return _Runner()

    class _App:
        def quit(self) -> None:
            quits.append(1)

    from PySide6.QtWidgets import QWidget

    window = QWidget()
    window._pending_evidence_bundle = state["pending"]
    window._post_rip_work_settled = lambda: bool(state["settled"])
    window._post_rip_still_running = lambda: "ctdb"

    timer = _arm_unattended_quit(_App(), window, _Console())
    assert timer is not None, "the helper armed no timer"

    # 1. Batch still running — must not quit.
    timer.timeout.emit()
    assert not quits, "quit while the script batch was still running"

    # 2. Batch done, but the bundle is still queued — must STILL not quit. This is
    #    the 2.6-second window that would have truncated the rig's evidence.
    state["running"] = False
    timer.timeout.emit()
    assert not quits, (
        "quit with an evidence bundle still queued — the archive would have been "
        "cut off before its verification landed"
    )
    # 3. Bundle sealed but a post-rip check still alive — must still not quit.
    window._pending_evidence_bundle = None
    timer.timeout.emit()
    assert not quits, "quit while a post-rip check was still running"

    # 4. Everything settled — now it may quit.
    state["settled"] = True
    timer.timeout.emit()
    assert quits, (
        "everything had settled and the process still did not quit — this is the "
        "'process running in this window' prompt the fix exists to remove"
    )
    # TEAR IT DOWN HERE, NOT "LATER".
    #
    # Three things were wrong with `timer.stop(); window.deleteLater()`:
    #
    # 1. `deleteLater()` only POSTS the destruction. With no event-loop turn
    #    inside this test, the C++ QWidget — plus the QTimer parented to it and
    #    the closure its connection keeps alive — is destroyed at some arbitrary
    #    later point in the session, inside a test that has nothing to do with
    #    this one. That is the harness handing a stranger its cleanup, and a Qt
    #    object graph torn down inside an unrelated test is the exact shape of
    #    this suite's historical SIGSEGVs (`conftest.stop_window_threads`).
    # 2. The graph is a REFERENCE CYCLE — window owns the timer, the timer's
    #    connection holds `_tick`, and `_tick` closes over the window — so
    #    dropping the last Python name does not free it either; it waits for the
    #    cyclic collector, which `conftest._cyclic_gc_paused_during_each_test`
    #    runs *between* tests. Same problem, different scheduler.
    # 3. A stopped timer is not a disconnected one. Stopping ends the ticks;
    #    disconnecting is what actually breaks the cycle above.
    #
    # So: disconnect, then let Qt genuinely process the delete before returning.
    timer.stop()
    timer.timeout.disconnect()
    window.deleteLater()
    qapp.processEvents()  # runs the posted DeferredDelete, here, in this test


def test_a_long_batch_does_not_spend_the_post_rip_grace_period(
    qapp, monkeypatch, caplog
) -> None:
    """The grace clock starts when the BATCH ends, not when the timer is armed.

    Measured on the full-acceptance hardware run, 2026-08-23. The budget's own
    docstring says "after its batch ends"; the code armed it at process start.
    For any batch longer than the budget the two differ by the whole overrun, and
    a tick returns early while the batch runs — so nothing noticed until the
    batch was over, at which point the deadline was long gone. The app quit
    **3.0 s** into post-rip work, killing the cover-art fetch, the CTDB verify,
    the FLAC verify and the SHA-256 digests, and left an archival
    `.platterpus.json` with `cover_art: null` that still reported
    `health_status: "No errors occurred"`.

    Time is injected rather than slept, so this asserts the arithmetic instead of
    racing it. Reverting the fix makes step 2 fail: with the deadline armed at
    `t0 + budget`, a batch that ran past the budget quits on the very first tick
    after it ends.
    """
    from platterpus import app as app_module
    from platterpus.app import _arm_unattended_quit

    clock: list[float] = [1_000.0]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])

    quits: list[int] = []
    state = {"running": True}

    class _Runner:
        @property
        def running(self) -> bool:
            return bool(state["running"])

    class _Console:
        @property
        def runner(self):
            return _Runner()

    class _App:
        def quit(self) -> None:
            quits.append(1)

    from PySide6.QtWidgets import QWidget

    window = QWidget()
    window._pending_evidence_bundle = None
    window._post_rip_work_settled = lambda: False  # post-rip work still going
    window._post_rip_still_running = lambda: "post_rip, ctdb, flac_verify"

    budget = 60.0
    timer = _arm_unattended_quit(_App(), window, _Console(), budget_s=budget)

    # 1. The batch runs for two hours — far past the budget. No quit: a tick
    #    while the batch is live returns before any deadline is consulted.
    clock[0] += 2 * 60 * 60
    timer.timeout.emit()
    assert not quits, "quit while the script batch was still running"

    # 2. The batch ends. THIS is when the grace period starts. Before the fix the
    #    deadline was already 7140 s in the past and this tick quit immediately —
    #    on the rig, 3.0 s into a cover-art fetch.
    state["running"] = False
    timer.timeout.emit()
    assert not quits, (
        "quit on the first tick after a long batch — the batch's own runtime was "
        "charged against the post-rip grace period, so post-rip work got none"
    )

    # 3. Part-way through the grace period: still waiting.
    clock[0] += budget / 2
    timer.timeout.emit()
    assert not quits, "quit before the post-rip grace period was spent"

    # 4. Grace exhausted: quit, and say how long we ACTUALLY waited. The old
    #    message printed the constant, so a give-up 0.55 s in announced itself as
    #    "after 900s" — the one line that explains missing results, misreporting.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="platterpus.app"):
        clock[0] += budget
        timer.timeout.emit()
    assert quits, "never quit, even after the post-rip grace period was spent"
    give_up = "\n".join(r.getMessage() for r in caplog.records)
    assert "90.0s" in give_up, (
        "the give-up line must report the ELAPSED wait (90.0s here), not the "
        f"budget — got: {give_up!r}"
    )
    assert "post_rip, ctdb, flac_verify" in give_up, (
        "the give-up line must name what was still running"
    )


# --- The fatal-error dialog must not stack on itself -------------------------


def test_a_second_fatal_error_does_not_open_a_second_dialog(qapp) -> None:
    """A fatal error raised WHILE the fatal dialog is up must not nest.

    **This is the defect that hung CI for 45 minutes across two runs and printed
    nothing but progress dots.** `_show_fatal_dialog` ends in `box.exec()`, which
    runs a NESTED EVENT LOOP — so Qt keeps delivering events, and an exception
    escaping any callback during that window re-enters `sys.excepthook`, which
    calls this function again, which opens a second modal dialog *inside* the
    first one's loop. Nothing raises, so the function's `except Exception` never
    sees it; the recursion goes through Qt.

    The measured evidence is a faulthandler dump from the 2026-08-19 CI run, whose
    main-thread stack is literally::

        _show_fatal_dialog -> hook -> _show_fatal_dialog -> hook -> <a test>

    two dialogs deep and blocked in the inner `exec()`. Headless, nobody clicks
    OK, so the process parked there until the job timed out — and a real user gets
    a pile of dialogs where each must be dismissed before the one under it, with
    every one of them able to spawn another.

    Driven through the REAL function with only `QMessageBox.exec` replaced, and
    the stand-in re-enters exactly the way Qt's own loop did: it raises a second
    fatal error from inside the first `exec()`. Asserting on the count of dialogs
    rather than on the flag, because the flag is the mechanism and "only one
    dialog appears" is the property.
    """
    from PySide6.QtWidgets import QMessageBox

    from platterpus import app as app_module

    execs: list[int] = []

    def _fake_exec(self: QMessageBox) -> int:
        execs.append(1)
        # What Qt's nested event loop did: deliver something that blows up, whose
        # exception reaches the excepthook and asks for another fatal dialog.
        app_module._show_fatal_dialog("re-entry", RuntimeError("during exec"))
        return 0

    original = QMessageBox.exec
    try:
        QMessageBox.exec = _fake_exec  # type: ignore[method-assign]  # probe the real fn
        app_module._show_fatal_dialog("first", ValueError("the real crash"))
    finally:
        QMessageBox.exec = original  # type: ignore[method-assign]

    assert execs == [1], (
        f"{len(execs)} fatal dialogs were opened, not 1. A fatal error arriving "
        "while the dialog is up must be logged and dropped: a second modal opens "
        "inside the first one's event loop, and neither can be dismissed before "
        "the other. This is the CI hang of 2026-08-19."
    )
    # And the guard must not latch: a LATER, unrelated crash still gets its dialog.
    # A re-entrancy flag stuck ON would silence every future crash report, which is
    # a worse failure than the one it fixes.
    execs.clear()

    def _quiet_exec(self: QMessageBox) -> int:
        execs.append(1)
        return 0

    try:
        QMessageBox.exec = _quiet_exec  # type: ignore[method-assign]
        app_module._show_fatal_dialog("later", ValueError("a separate crash"))
    finally:
        QMessageBox.exec = original  # type: ignore[method-assign]

    assert execs == [1], (
        "the re-entrancy guard latched ON: a later, unrelated fatal error got no "
        "dialog at all. It must clear when the first dialog closes."
    )


def test_the_unattended_quit_never_fires_while_a_rip_is_reading_the_disc(
    qapp,
) -> None:
    """**Regression for the 2026-08-24 rig run, and the defect that killed a rip.**

    The batch ended while a whole-disc secure re-read was 1.48% into track 1. Both
    existing gates passed — there was no queued bundle and no post-rip work,
    *because the rip had not finished* — so the helper logged "post-rip work has
    settled — quitting", `closeEvent` reported `rip active=True` one millisecond
    later, and `fuser -k /dev/sr0` killed the reader. That rip's log has no FUN512
    footer and no report; it does not appear in the library audit at all.

    `_post_rip_work_settled()` is a true and complete answer to a different
    question. This is `CLAUDE.md`'s *did I check the preconditions where the thing
    HAPPENS?* — the guard was built for the deferral it knew about and never asked
    the prior one.

    **The budget must not rescue it either.** A live rip deliberately does not
    start the grace clock: the budget is 15 minutes and a full-disc uniform
    re-read is hours, so counting a rip against it would delay the kill rather
    than prevent it. Asserted with a budget of zero, which makes any
    budget-based expiry fire on the very first tick.
    """
    from platterpus.app import _arm_unattended_quit

    quits: list[int] = []
    state = {"rip": object()}

    class _Runner:
        running = False

    class _Console:
        @property
        def runner(self):
            return _Runner()

    class _App:
        def quit(self) -> None:
            quits.append(1)

    from PySide6.QtWidgets import QWidget

    window = QWidget()
    window._rip_worker = state["rip"]
    window._pending_evidence_bundle = None
    window._post_rip_work_settled = lambda: True
    window._post_rip_still_running = lambda: ""

    timer = _arm_unattended_quit(_App(), window, _Console(), budget_s=0.0)
    assert timer is not None

    # A rip is reading. Every other gate says "settled". It must not quit — and a
    # zero budget must not let it through the give-up path either.
    for _ in range(5):
        timer.timeout.emit()
    assert not quits, (
        "the app quit while a rip was still reading the disc — this is the defect "
        "that destroyed the whole-disc secure re-read on 2026-08-24"
    )

    # THE FLOOR: once the rip ends it must actually quit, or this test would pass
    # against a helper that never quits at all.
    window._rip_worker = None
    timer.timeout.emit()
    assert quits, (
        "the helper never quit once the rip ended — the guard has become a hang, "
        "which is the failure the whole unattended path exists to avoid"
    )
    timer.stop()
