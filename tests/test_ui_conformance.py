"""The UI conformance matrix: every rule, on every window, in every condition.

**Why this file is shaped like a matrix.** On 2026-09-23 a real-user report found
four UI defects in one sitting — a dialog cutting its own text off, status colours
below the contrast bar, a main window taller than a small screen, and dead menu
paths — and every one had the same root: *a rule was written into ONE window and
never applied to the rest.* Settings clamped itself to the screen; Drive Setup
refused to be shorter than its prose; thirteen other dialogs did neither. The
maintainer's question was the right one: *"anything you can do to fix this
globally?"* This is that. A rule lives here once and is applied to every window
under every condition, so it cannot be learned in one place again; and the window
list is derived from the source, so a new window is measured the day it lands.

**The three axes.**

* WINDOWS — every `CenteredDialog` subclass in `src/` (completeness is asserted
  against the source) plus the main window.
* CONDITIONS — :data:`CONDITIONS`: 14 standard screen shapes as the LOGICAL size
  the desktop reports (scaling is what makes a big panel a small screen), a dark
  theme, and a 150% text size, each where it can bite.
* RULES — :data:`RULES`, each a measurement of the rendered window, never of the
  source. Static source checks live in `tests/test_accessibility_standards.py`;
  this file is the half that renders.

**Why subprocesses.** The screen, the palette and the application font are fixed
when `QApplication` starts, and this suite's application is shared. Each
condition gets its own interpreter, all started at once. The offscreen plugin will
not move a window between screens (a `setScreen` found its second screen already
deleted), which is why it is one process per condition rather than one per run.

**Scope, stated so it is not silently narrower than it reads.** NOT covered:
`QMessageBox` (built inside methods, sized by Qt, short text — the plain-text half
is swept by `tests/test_message_boxes_are_plaintext.py`), the setup wizard pages,
and tooltips.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
SRC: Path = REPO_ROOT / "src"

#: Every standard screen shape, as the LOGICAL size the desktop reports — scaling
#: is what makes a big panel a small screen, so a 1080p panel at 200% is 960 × 540
#: here. The maintainer's instruction, 2026-09-23: *"make sure rules for the
#: windows work across all standard window resolutions, I only gave you what I am
#: using."* The first version of this file measured two shapes; this is the set a
#: Linux desktop, a laptop and a handheld (Bazzite's other target) actually report.
#: All of them run in ONE interpreter — the offscreen plugin takes several screens
#: side by side — so the matrix costs one subprocess, not fourteen.
SCREENS: tuple[tuple[str, int, int], ...] = (
    ("steamdeck-150pct", 853, 533),  # 1280x800 at 150%
    ("1080p-200pct", 960, 540),  # the shape that reproduced the report
    ("netbook", 1024, 600),
    ("xga", 1024, 768),
    ("720p", 1280, 720),  # also 1080p at 150%, 1440p at 200%
    ("steamdeck", 1280, 800),  # also 2560x1600 at 200% (Legion Go)
    ("laptop-hd", 1366, 768),  # the most common laptop panel
    ("wxga-plus", 1440, 900),
    ("1080p-125pct", 1536, 864),
    ("hd-plus", 1600, 900),
    ("1080p", 1920, 1080),
    ("wuxga", 1920, 1200),
    ("1440p", 2560, 1440),
    ("4k", 3840, 2160),
)


#: The conditions each window is measured under: (id, screen, theme, text scale).
#: Every screen shape in the light theme at 100%; the dark theme where contrast is
#: decided (it does not depend on the screen, so two shapes suffice); and 150%
#: text — a common accessibility setting — on the six shortest screens, where a
#: bigger font is most likely to push text off or a window past the screen.
CONDITIONS: tuple[tuple[str, str, str, float], ...] = (
    *((name, name, "light", 1.0) for name, _w, _h in SCREENS),
    ("1080p-200pct-dark", "1080p-200pct", "dark", 1.0),
    ("1080p-dark", "1080p", "dark", 1.0),
    *(
        (f"{name}-text150", name, "light", 1.5)
        for name in (
            "steamdeck-150pct",
            "1080p-200pct",
            "netbook",
            "xga",
            "720p",
            "steamdeck",
        )
    ),
)

#: Every rule this matrix applies. A test below reads each by name, so a rule
#: added here without a test — or a test with no rule — fails the completeness
#: check rather than being silently skipped.
RULES: tuple[str, ...] = (
    "clipped_text",
    "window_fits_screen",
    "scrolls_only_when_capped",
    "text_contrast",
    "button_floor",
    "cut_off_labels",
    "duplicate_shortcuts",
    "unnamed_inputs",
)

#: Breeze (light) and Breeze Dark (Plasma 6) — the KDE defaults on Bazzite — as
#: the palettes the matrix renders in. `ui/status_colours.py` is held to wider
#: background ranges than these; this is what a user actually gets.
PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "Window": "#eff0f1",
        "WindowText": "#232629",
        "Base": "#fcfcfc",
        "AlternateBase": "#eff0f1",
        "Text": "#232629",
        "Button": "#fcfcfc",
        "ButtonText": "#232629",
        "Highlight": "#3daee9",
        "HighlightedText": "#fcfcfc",
        "Link": "#2980b9",
        "ToolTipBase": "#f7f7f7",
        "ToolTipText": "#232629",
    },
    "dark": {
        "Window": "#202326",
        "WindowText": "#fcfcfc",
        "Base": "#141618",
        "AlternateBase": "#1d1f22",
        "Text": "#fcfcfc",
        "Button": "#292c30",
        "ButtonText": "#fcfcfc",
        "Highlight": "#3daee9",
        "HighlightedText": "#fcfcfc",
        "Link": "#1d99f3",
        "ToolTipBase": "#292c30",
        "ToolTipText": "#fcfcfc",
    },
}

#: Qt's "no maximum" — a maximum below it is one somebody set.
_QWIDGETSIZE_MAX: int = 16777215

#: WCAG 2.2 AA, normal-size text.
AA_TEXT: float = 4.5
#: WCAG 2.5.8 target size, and the floor `CLAUDE.md` holds our own sizes to.
TARGET_FLOOR_PX: int = 24

#: A dialog class name must appear here to be measured — and every
#: `CenteredDialog` subclass in the source must appear here, or the completeness
#: test below fails. The factories themselves live in `_factories()`, which runs
#: inside the measuring subprocess.
MEASURED: frozenset[str] = frozenset(
    {
        "AboutDialog",
        "DiagnosticsDialog",
        "DriveSetupDialog",
        "FileViewerDialog",
        "HelpDialog",
        "HostSetupDialog",
        "ManualInstallDialog",
        "PendingInstallsDialog",
        "ReleasePickerDialog",
        "RipperPickerDialog",
        "ScriptConsoleDialog",
        "SettingsDialog",
        "SetupCenterDialog",
        "UninstallDialog",
        "UnknownAlbumDialog",
    }
)


def _factories() -> dict[str, object]:
    """One way to build each dialog with stand-in dependencies.

    Imported only inside the subprocess, because building a dialog needs a
    `QApplication` on the screen being measured. The stand-ins are the ones each
    dialog's own test file already uses, imported rather than copied, so a change
    to a constructor breaks one place.
    """
    from PySide6.QtWidgets import QWidget
    from test_ui_drive_setup_dialog import _StubBackend
    from test_ui_host_setup_dialog import _FakeHost
    from test_ui_manual_install_dialog import _absent_probe, _spec
    from test_ui_pending_installs_dialog import _item
    from test_ui_release_picker import _release

    from platterpus.config import Config
    from platterpus.ui.dialogs.diagnostics_dialog import DiagnosticsDialog
    from platterpus.ui.dialogs.file_viewer import FileViewerDialog
    from platterpus.ui.dialogs.manual_install import ManualInstallDialog
    from platterpus.ui.dialogs.pending_installs import PendingInstallsDialog
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.ui.dialogs.setup_center import SetupCenterDialog
    from platterpus.ui.drive_setup_dialog import DriveSetupDialog
    from platterpus.ui.help_dialogs import AboutDialog, HelpDialog
    from platterpus.ui.host_setup_dialog import HostSetupDialog
    from platterpus.ui.release_picker import ReleasePickerDialog
    from platterpus.ui.ripper_picker import RipperPickerDialog
    from platterpus.ui.settings_dialog import SettingsDialog
    from platterpus.ui.uninstall_dialog import UninstallDialog
    from platterpus.ui.unknown_album import UnknownAlbumDialog
    from platterpus.user_settings import SettingWrite

    text_file = Path(tempfile.mkdtemp()) / "viewed.txt"
    text_file.write_text("a line\n", encoding="utf-8")
    holder = QWidget()
    return {
        "AboutDialog": lambda: AboutDialog(),
        "DiagnosticsDialog": lambda: DiagnosticsDialog(),
        "DriveSetupDialog": lambda: DriveSetupDialog(_StubBackend(), "/dev/sr0"),
        "FileViewerDialog": lambda: FileViewerDialog(
            text_file, reader=lambda _p: "a line"
        ),
        "HelpDialog": lambda: HelpDialog(),
        "HostSetupDialog": lambda: HostSetupDialog(host_setup=_FakeHost(True)),
        "ManualInstallDialog": lambda: ManualInstallDialog(_spec(), _absent_probe()),
        "PendingInstallsDialog": lambda: PendingInstallsDialog(
            [_item("picard"), _item("metaflac")]
        ),
        "ReleasePickerDialog": lambda: ReleasePickerDialog(
            [_release(), _release(mbid="second")]
        ),
        "RipperPickerDialog": lambda: RipperPickerDialog(),
        "ScriptConsoleDialog": lambda: ScriptConsoleDialog(holder),
        "SettingsDialog": lambda: SettingsDialog(Config()),
        "SetupCenterDialog": lambda: SetupCenterDialog(
            None,
            app_version="0.0.0",
            ripper_pin="0000000",
            ripper_version="0.0.0",
            approved_by_round=0,
            dependency_report=None,
            actions={},
            config=Config(),
            save_setting=lambda _f, _v: SettingWrite(True),
        ),
        "UninstallDialog": lambda: UninstallDialog(build_teardown=lambda *a: None),
        "UnknownAlbumDialog": lambda: UnknownAlbumDialog(),
    }


def _apply_condition(app: object, theme: str, text_scale: float) -> None:
    """Style, palette and font for this process's condition."""
    from PySide6.QtGui import QColor, QPalette

    app.setStyle("Fusion")  # type: ignore[attr-defined]  # a QApplication
    palette = QPalette()
    for role, colour in PALETTES[theme].items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(colour))
    app.setPalette(palette)  # type: ignore[attr-defined]  # a QApplication
    if text_scale != 1.0:
        font = app.font()  # type: ignore[attr-defined]  # a QApplication
        if font.pointSizeF() > 0:
            font.setPointSizeF(font.pointSizeF() * text_scale)
        else:
            font.setPixelSize(round(font.pixelSize() * text_scale))
        app.setFont(font)  # type: ignore[attr-defined]  # a QApplication


_COLOUR_IN_STYLE: re.Pattern[str] = re.compile(r"(?<![-\w])color:\s*(#[0-9a-fA-F]{6})")
_MNEMONIC: re.Pattern[str] = re.compile(r"&([^&\s])")


def _mnemonics(text: str) -> list[str]:
    """The Alt-letter a label claims — `&&` is a literal ampersand, not one."""
    return [m.group(1).casefold() for m in _MNEMONIC.finditer(text.replace("&&", ""))]


def _measure_one(window: object) -> dict[str, object]:
    """Show one window and apply every rule to what was rendered."""
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import (
        QAbstractButton,
        QAbstractItemView,
        QAbstractSpinBox,
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QTextEdit,
        QToolButton,
    )

    from platterpus.ui.dialogs.centering import CenteredDialog
    from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea
    from platterpus.ui.status_colours import contrast_ratio

    app = QApplication.instance()
    assert app is not None
    window.show()  # type: ignore[attr-defined]  # every factory returns a window
    for _ in range(5):
        app.processEvents()
    w = window  # a QWidget; the ignores below are for this `object` parameter
    avail = w.screen().availableGeometry()  # type: ignore[attr-defined]  # a QWidget
    violations: dict[str, list[str]] = {rule: [] for rule in RULES}
    examined: dict[str, int] = {rule: 0 for rule in RULES}

    def shown(widget: object) -> bool:
        return bool(widget.isVisibleTo(w))  # type: ignore[attr-defined]  # a QWidget

    # clipped_text — a wrapped label shorter than its own text needs at its width.
    for label in w.findChildren(QLabel):  # type: ignore[attr-defined]  # a QWidget
        if not (label.wordWrap() and shown(label) and label.text()):
            continue
        examined["clipped_text"] += 1
        need = label.heightForWidth(label.width())
        if label.height() < need:
            violations["clipped_text"].append(
                f"{label.height()}px of {need}px: {label.text()[:60]!r}"
            )

    # window_fits_screen — a window larger than the screen hides its buttons.
    examined["window_fits_screen"] += 1
    if w.width() > avail.width() or w.height() > avail.height():  # type: ignore[attr-defined]  # a QWidget
        violations["window_fits_screen"].append(
            f"{w.width()}x{w.height()} on {avail.width()}x{avail.height()}"  # type: ignore[attr-defined]  # a QWidget
        )

    # scrolls_only_when_capped — a body that scrolls although the window had room.
    cap = avail.height() - CenteredDialog.SCREEN_MARGIN_PX
    capped = w.height() >= cap - 1  # type: ignore[attr-defined]  # a QWidget
    for area in w.findChildren(FitScrollArea):  # type: ignore[attr-defined]  # a QWidget
        examined["scrolls_only_when_capped"] += 1
        bar = area.verticalScrollBar()
        if bar.maximum() > bar.minimum() and not capped:
            violations["scrolls_only_when_capped"].append(
                f"{area.accessibleName()!r} scrolls {bar.maximum() - bar.minimum()}px "
                f"in a {w.height()}px window that could grow to {cap}px"  # type: ignore[attr-defined]  # a QWidget
            )

    # text_contrast — measured from the colours actually applied, not the source.
    for widget in [*w.findChildren(QLabel), *w.findChildren(QAbstractButton)]:  # type: ignore[attr-defined]  # a QWidget
        text = widget.text()
        if not (text and shown(widget) and widget.isEnabled()):
            continue
        if isinstance(widget, QLabel) and ("<" in text and ">" in text):
            continue  # rich text carries its own colours; not measurable here
        own = _COLOUR_IN_STYLE.search(widget.styleSheet())
        palette = widget.palette()
        fg = (
            own.group(1)
            if own
            else palette.color(
                QPalette.ColorGroup.Active, widget.foregroundRole()
            ).name()
        )
        bg = palette.color(QPalette.ColorGroup.Active, widget.backgroundRole()).name()
        examined["text_contrast"] += 1
        ratio = contrast_ratio(fg, bg)
        if ratio < AA_TEXT:
            violations["text_contrast"].append(
                f"{ratio:.2f}:1 {fg} on {bg}: {type(widget).__name__} {text[:40]!r}"
            )

    # button_floor — a button smaller than it should be. Two ways to get there,
    # and neither is WCAG's user-agent exception (2.5.8: a size "determined by
    # the user agent and not modified by the author" is exempt — the platform
    # style's own button height is not ours to police): a size WE set below the
    # 24 px floor, or a layout that squeezed a button below the height its own
    # style asked for.
    for button in [*w.findChildren(QPushButton), *w.findChildren(QToolButton)]:  # type: ignore[attr-defined]  # a QWidget
        if not shown(button):
            continue
        examined["button_floor"] += 1
        authored = (
            button.maximumHeight() < _QWIDGETSIZE_MAX or button.minimumHeight() > 0
        )
        if authored and button.height() < TARGET_FLOOR_PX:
            violations["button_floor"].append(
                f"{button.height()}px, a size we set: {button.text()!r}"
            )
        elif button.height() < button.sizeHint().height():
            violations["button_floor"].append(
                f"squeezed to {button.height()}px of the style's "
                f"{button.sizeHint().height()}px: {button.text()!r}"
            )

    # cut_off_labels — a one-line label or a button whose text does not fit.
    for widget in [*w.findChildren(QAbstractButton), *w.findChildren(QLabel)]:  # type: ignore[attr-defined]  # a QWidget
        text = widget.text()
        if not (text and shown(widget)):
            continue
        if isinstance(widget, QLabel) and (widget.wordWrap() or "<" in text):
            continue
        examined["cut_off_labels"] += 1
        if widget.width() + 1 < widget.sizeHint().width():
            violations["cut_off_labels"].append(
                f"{widget.width()}px of {widget.sizeHint().width()}px: "
                f"{type(widget).__name__} {text[:50]!r}"
            )

    # duplicate_shortcuts — two controls in one window claiming the same Alt-key.
    sources: list[str] = [
        b.text()
        for b in w.findChildren(QAbstractButton)
        if shown(b) and b.isEnabled()  # type: ignore[attr-defined]  # a QWidget
    ]
    sources += [
        lab.text()
        for lab in w.findChildren(QLabel)
        if shown(lab) and lab.buddy() is not None  # type: ignore[attr-defined]  # a QWidget
    ]
    groups: list[tuple[str, list[str]]] = [("window", sources)]
    if isinstance(w, QMainWindow):
        # The menu bar's titles share the window's Alt-keys; each menu's items
        # are their own group, because a letter only has to be unique among the
        # items of the menu that is open.
        bar = w.menuBar().actions()
        sources += [a.text() for a in bar]
        groups += [
            (f"menu {a.text()!r}", [i.text() for i in a.menu().actions() if i.text()])
            for a in bar
            if a.menu() is not None
        ]
    for where, texts in groups:
        claims: dict[str, list[str]] = {}
        for text in texts:
            for letter in _mnemonics(text):
                examined["duplicate_shortcuts"] += 1
                claims.setdefault(letter, []).append(text)
        for letter, owners in sorted(claims.items()):
            if len(owners) > 1:
                violations["duplicate_shortcuts"].append(
                    f"{where}: Alt+{letter.upper()}: {owners}"
                )

    # unnamed_inputs — a field a screen reader would announce as nothing.
    buddies = {
        id(lab.buddy())
        for lab in w.findChildren(QLabel)
        if lab.buddy() is not None  # type: ignore[attr-defined]  # a QWidget
    }
    for kind in (
        QLineEdit,
        QAbstractSpinBox,
        QComboBox,
        QPlainTextEdit,
        QTextEdit,
        QAbstractItemView,
    ):
        for field in w.findChildren(kind):  # type: ignore[attr-defined]  # a QWidget
            if not shown(field):
                continue
            parent = field.parentWidget()
            if isinstance(parent, (QComboBox, QAbstractSpinBox, QAbstractItemView)):
                # Part of a named control: the editor inside a combo or spin box,
                # or a table's header, which assistive tech reads as the table's
                # own column headings.
                continue
            examined["unnamed_inputs"] += 1
            if not field.accessibleName() and id(field) not in buddies:
                violations["unnamed_inputs"].append(
                    f"{type(field).__name__} {field.objectName()!r} has no accessible "
                    "name and no labelling buddy"
                )

    report: dict[str, object] = {
        "size": [w.width(), w.height()],  # type: ignore[attr-defined]  # a QWidget
        "avail": [avail.width(), avail.height()],
        "violations": violations,
        "examined": examined,
    }
    w.close()  # type: ignore[attr-defined]  # a QWidget
    return report


def _main_window() -> object:
    """The main window, built with the same stand-ins its own tests use."""
    from test_ui_main_window import _FakeBackend, _FakeMb

    from platterpus.adapters.metaflac import MetaflacAdapter
    from platterpus.config import Config
    from platterpus.deps.manager import DependencyManager
    from platterpus.ui.main_window import MainWindow

    # Built as an install that has ALREADY answered its first-run questions. The
    # first version built a fresh `Config()`, so showing the window fired the
    # one-time "Set up Platterpus?" question — a static `QMessageBox.question`,
    # which waits forever for a click on an offscreen screen, and hung the whole
    # measurement past its 240 s budget. The layout under test is the everyday
    # window, not the first-run prompt.
    answered = Config(
        host_setup_prompted=True,
        drive_setup_prompted=True,
        appimage_integration_prompted=True,
    )
    return MainWindow(
        config=answered,
        backend=_FakeBackend(),
        mb_client=_FakeMb(),
        metaflac=MetaflacAdapter(),
        dependency_manager=DependencyManager(specs=[]),
        save_config=lambda _cfg: None,
    )


def _measure_all() -> dict[str, object]:
    """Subprocess entry: every window, in this process's one condition."""
    from conftest import stop_window_threads
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    _apply_condition(
        app,
        os.environ.get("PLATTERPUS_UI_THEME", "light"),
        float(os.environ.get("PLATTERPUS_UI_TEXT_SCALE", "1.0")),
    )
    results: dict[str, object] = {}
    for name, make in _factories().items():
        results[name] = _measure_one(make())  # type: ignore[operator]  # factories are callables
    window = _main_window()
    results["MainWindow"] = _measure_one(window)
    stop_window_threads(window)
    results.update(_measure_long_picker())
    results.update(_measure_states())
    return results


def _measure_long_picker() -> dict[str, object]:
    """The picker with more rows than any round has offered."""
    from unittest import mock

    # FUTURE-PROOFING, measured rather than promised. The picker lists whatever
    # builds the handshake record names; the maintainer asked that it keep
    # working "in case there are more options later". Eight rows is more than
    # any round has ever offered.
    from platterpus.deps import fork_source
    from platterpus.ui.ripper_picker import RipperPickerDialog

    real = fork_source.ripper_choices()
    many = [real[0]] * 8
    with mock.patch.object(fork_source, "ripper_choices", return_value=many):
        picker = RipperPickerDialog()
        report = _measure_one(picker)
        bar = picker._body_scroll.verticalScrollBar()
        report["scroll_range"] = bar.maximum() - bar.minimum()
    return {"RipperPickerDialog[8 rows]": report}


#: Windows measured in a STATE rather than as they open. A window that has just
#: opened shows none of its coloured status lines — they appear when a rip
#: finishes or an input is wrong — so without these the contrast rule examined
#: every label except the ones whose colour we chose. A revert probe proved it:
#: forcing the light-theme colours onto a dark window passed every rule.
STATES: tuple[str, ...] = (
    "MainWindow[status ok]",
    "MainWindow[status warn]",
    "MainWindow[status neutral]",
    "SettingsDialog[errors]",
    "SettingsDialog[warnings]",
)


def _measure_states() -> dict[str, object]:
    """Each coloured status line, shown through its real renderer."""
    from types import SimpleNamespace

    from conftest import stop_window_threads

    from platterpus import settings_validation as sv

    results: dict[str, object] = {}
    for level in ("ok", "warn", "neutral"):
        window = _main_window()
        progress = window._rip_progress
        progress.set_comparison(
            SimpleNamespace(
                summary="all 14 tracks identical",
                headline_level=level,
                differing_count=0,
            )
        )
        progress.set_stall_notice("⚠ No progress from the drive for 2 minutes.")
        results[f"MainWindow[status {level}]"] = _measure_one(window)
        stop_window_threads(window)
    for label, severity in (
        ("errors", sv.SEVERITY_ERROR),
        ("warnings", sv.SEVERITY_WARNING),
    ):
        dialog = _factories()["SettingsDialog"]()  # type: ignore[operator]  # a factory
        dialog._render_validation(  # type: ignore[attr-defined]  # a SettingsDialog
            [
                sv.ValidationIssue(
                    "output_dir", "Output folder must be absolute.", severity
                )
            ]
        )
        results[f"SettingsDialog[{label}]"] = _measure_one(dialog)
    return results


def _run_all_conditions() -> dict[str, dict[str, dict[str, object]]]:
    """Every window in every condition — one process each, all at once."""
    shapes = {name: (width, height) for name, width, height in SCREENS}
    tmp = Path(tempfile.mkdtemp())
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(REPO_ROOT / "tests")])
    procs: dict[str, subprocess.Popen[str]] = {}
    for cond_id, screen, theme, scale in CONDITIONS:
        width, height = shapes[screen]
        config = tmp / f"{cond_id}.json"
        spec = {
            "name": screen,
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "logicalDpi": 96,
            "dpr": 1,
        }
        config.write_text(json.dumps({"screens": [spec]}), encoding="utf-8")
        procs[cond_id] = subprocess.Popen(
            [sys.executable, __file__, "--measure"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **env,
                "QT_QPA_PLATFORM": f"offscreen:configfile={config}",
                "PLATTERPUS_UI_THEME": theme,
                "PLATTERPUS_UI_TEXT_SCALE": str(scale),
            },
        )
    measured: dict[str, dict[str, dict[str, object]]] = {}
    marker = "MEASUREMENTS:"
    for cond_id, proc in procs.items():
        try:
            out, err = proc.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            raise AssertionError(
                f"{cond_id}: the measurement hung\n{err[-3000:]}"
            ) from None
        assert proc.returncode == 0, (
            f"{cond_id}: the measuring subprocess failed (exit {proc.returncode}):\n"
            f"{out[-3000:]}\n{err[-3000:]}"
        )
        line = next((ln for ln in out.splitlines() if ln.startswith(marker)), None)
        assert line is not None, f"{cond_id}: no measurements printed:\n{out[-3000:]}"
        measured[cond_id] = json.loads(line[len(marker) :])
    return measured


@pytest.fixture(scope="module")
def matrix() -> dict[str, dict[str, dict[str, object]]]:
    return _run_all_conditions()


def _violations(
    matrix: dict[str, dict[str, dict[str, object]]], rule: str
) -> dict[str, list[str]]:
    """``{"condition / window": [violation, ...]}`` for one rule, over everything."""
    found: dict[str, list[str]] = {}
    for cond_id, windows in matrix.items():
        for window, report in windows.items():
            hits = report["violations"][rule]  # type: ignore[index]  # JSON dict
            if hits:
                found[f"{cond_id} / {window}"] = hits  # type: ignore[assignment]  # JSON list
    return found


@pytest.mark.parametrize("rule", RULES)
def test_every_window_passes_every_rule_in_every_condition(
    matrix: dict[str, dict[str, dict[str, object]]], rule: str
) -> None:
    """The matrix itself: one assertion per rule, over all windows × conditions."""
    found = _violations(matrix, rule)
    assert not found, f"{rule}:\n" + json.dumps(found, indent=2)


#: The least each rule must examine across the whole matrix. A rule that stopped
#: finding its subject would otherwise pass by finding nothing. Set well under
#: today's counts so ordinary edits to a window do not trip them.
FLOORS: dict[str, int] = {
    "clipped_text": 300,
    "window_fits_screen": 300,
    "scrolls_only_when_capped": 40,
    "text_contrast": 1000,
    "button_floor": 500,
    "cut_off_labels": 1000,
    "duplicate_shortcuts": 200,
    "unnamed_inputs": 200,
}


def test_every_rule_examined_real_subjects(
    matrix: dict[str, dict[str, dict[str, object]]],
) -> None:
    assert set(FLOORS) == set(RULES), "a rule has no floor, or a floor no rule"
    counts = {
        rule: sum(
            int(report["examined"][rule])  # type: ignore[index]  # JSON dict
            for windows in matrix.values()
            for report in windows.values()
        )
        for rule in RULES
    }
    short = {rule: n for rule, n in counts.items() if n < FLOORS[rule]}
    assert not short, f"rules that examined too little: {short} (all: {counts})"
    assert set(matrix) == {c[0] for c in CONDITIONS}, "a condition was not measured"
    for cond_id, windows in matrix.items():
        missing = (MEASURED | {"MainWindow", *STATES}) - set(windows)
        assert not missing, f"{cond_id}: windows not measured: {sorted(missing)}"


def test_a_long_picker_scrolls_instead_of_clipping(
    matrix: dict[str, dict[str, dict[str, object]]],
) -> None:
    """Future-proofing, asserted: eight rows scroll on a short screen."""
    for cond_id, windows in matrix.items():
        report = windows["RipperPickerDialog[8 rows]"]
        _w, height = report["avail"]  # type: ignore[misc]  # JSON list of two ints
        if height < 700:
            assert int(report["scroll_range"]) > 0, (  # type: ignore[call-overload]  # JSON int
                f"{cond_id}: eight rows on a short screen did not scroll"
            )


def test_the_contrast_rule_would_catch_the_colours_that_shipped() -> None:
    """Non-triviality for the rule that matters most, without a display."""
    from platterpus.ui.status_colours import contrast_ratio

    dark = PALETTES["dark"]["Window"]
    assert contrast_ratio("#1a7f37", dark) < AA_TEXT  # the shipped verdict green
    assert contrast_ratio(PALETTES["dark"]["WindowText"], dark) >= AA_TEXT


def test_the_shortcut_rule_reads_ampersands_the_way_qt_does() -> None:
    assert _mnemonics("Setup && &Updates…") == ["u"]
    assert _mnemonics("&Refresh") == ["r"]
    assert _mnemonics("Rock && Roll") == []


def test_every_centered_dialog_in_the_source_is_measured() -> None:
    """Completeness, derived from the source rather than trusted."""
    pattern = re.compile(r"^class (\w+)\(CenteredDialog\):", re.MULTILINE)
    found = {
        match.group(1)
        for path in (SRC / "platterpus").rglob("*.py")
        for match in pattern.finditer(path.read_text(encoding="utf-8"))
    }
    assert len(found) >= 10, f"only {len(found)} dialogs found — the pattern broke"
    assert found == MEASURED, (
        f"not measured: {sorted(found - MEASURED)}; "
        f"measured but gone: {sorted(MEASURED - found)}"
    )


if __name__ == "__main__" and "--measure" in sys.argv:
    print("MEASUREMENTS:" + json.dumps(_measure_all()))
