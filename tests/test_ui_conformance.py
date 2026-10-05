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
  against the source), the main window, and — since the 2026-10-05 audit —
  every message box and inline Qt dialog the app can show, built with its real
  worst-case text (`tests/test_ui_message_box_conformance.py`, whose populations
  are derived from the source the same way).
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

**Scope, stated so it is not silently narrower than it reads.** This line used
to say `QMessageBox` was NOT covered — "built inside methods, sized by Qt, short
text". The texts were not short: measured on 2026-10-05, the cyanrip offers, the
dependency summary and the script reference were each taller than common
screens, and the beta update prompt opened with its buttons below the edge. They
are measured now. Still NOT covered: Qt's own file dialog (usually the
desktop's), and tooltips.

**Every window is measured as production shows it**: the app-wide
`DialogCenterFilter` that `app.main` installs is installed here too, because it
is what fits and places every dialog that is not a `CenteredDialog`
(`test_the_matrix_installs_the_filter_app_main_installs`).
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
    "window_on_screen",
    "scrolls_only_when_capped",
    "text_contrast",
    "button_floor",
    "cut_off_labels",
    "cut_off_cells",
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


def _menu_groups(window: object) -> list[tuple[str, list[str]]]:
    """Each menu a person can open in ``window``, with the labels in it.

    **Submenus and context menus included (2026-09-27).** This used to read the
    menu bar's menus one level deep, which was every menu there was until Tools
    gained an *Advanced* submenu and the disc panel an album menu; a clash inside
    either would have passed. The walk is `conftest.window_menus`, the one the
    shortcut rule in `tests/test_accessibility_standards.py` also uses, so the
    two rules cannot disagree about which menus exist.
    """
    from conftest import window_menus

    groups: list[tuple[str, list[str]]] = []
    for where, menu in window_menus(window):
        labels = [a.text() for a in menu.actions() if a.text()]  # type: ignore[attr-defined]  # a QMenu
        groups.append((where, labels))
        if where.startswith("album menu"):
            menu.deleteLater()  # type: ignore[attr-defined]  # built for us; ours to free
    return groups


def _duplicate_mnemonics(
    groups: list[tuple[str, list[str]]],
) -> tuple[list[str], int]:
    """``(violations, letters examined)``: each Alt-letter claimed twice in a group."""
    violations: list[str] = []
    examined = 0
    for where, texts in groups:
        claims: dict[str, list[str]] = {}
        for text in texts:
            for letter in _mnemonics(text):
                examined += 1
                claims.setdefault(letter, []).append(text)
        for letter, owners in sorted(claims.items()):
            if len(owners) > 1:
                violations.append(f"{where}: Alt+{letter.upper()}: {owners}")
    return violations, examined


def _measure_one(window: object) -> dict[str, object]:
    """Show one window and apply every rule to what was rendered."""
    from PySide6.QtCore import QPoint, QRect, Qt
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import (
        QAbstractButton,
        QAbstractItemView,
        QAbstractScrollArea,
        QAbstractSpinBox,
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QStyle,
        QTableView,
        QTextEdit,
        QToolButton,
    )

    from platterpus.ui.dialogs.centering import CenteredDialog
    from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea
    from platterpus.ui.dialogs.message_box_fit import SCROLL_AREA_NAME
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

    # window_on_screen — a window that FITS but is PLACED partly off the screen
    # hides its buttons just the same. Found 2026-10-05: message boxes were
    # centred while still Qt's 640-wide placeholder and then grew downward, so a
    # 480 x 420 beta prompt on a 540-px screen opened with Yes and No below the
    # edge. Measured on the window's own rectangle (its content and buttons).
    #
    # Sideways only, the frame's side border is tolerated. A window exactly as
    # wide as the screen — which `fit_dialog_to_screen` allows on purpose, and
    # which Qt itself makes a message box carrying a long path on a screen up to
    # 1024 px wide — cannot have its frame on the screen as well, so the clamp
    # puts the frame's left edge at the screen's and the content's last few
    # pixels (the border's width, 2 px offscreen; layout margin, not text) past
    # the right one. Vertically nothing is tolerated: that is the axis the
    # defect above was on, and a title bar is tens of pixels, not a border.
    examined["window_on_screen"] += 1
    g = w.geometry()  # type: ignore[attr-defined]  # a QWidget
    frame = w.frameGeometry()  # type: ignore[attr-defined]  # a QWidget
    border = max(g.left() - frame.left(), frame.right() - g.right(), 0)
    if not avail.adjusted(-border, 0, border, 0).contains(g):
        violations["window_on_screen"].append(
            f"{g.width()}x{g.height()} at ({g.x()},{g.y()}) on "
            f"{avail.width()}x{avail.height()}"
        )

    # scrolls_only_when_capped — a body that scrolls although the window had room.
    # The message-box text area (`message_box_fit`) is held to the same rule: it
    # exists only when no width could fit the text, so it must sit in a box that
    # is already as tall as the screen allows.
    cap = avail.height() - CenteredDialog.SCREEN_MARGIN_PX
    capped = w.height() >= cap - 1  # type: ignore[attr-defined]  # a QWidget
    message_areas = w.findChildren(QScrollArea, SCROLL_AREA_NAME)  # type: ignore[attr-defined]  # a QWidget
    for area in [*w.findChildren(FitScrollArea), *message_areas]:  # type: ignore[attr-defined]  # a QWidget
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

    # cut_off_labels — a one-line label or a button whose text does not fit;
    # and any label or button running past the right edge of a scroll area that
    # cannot scroll sideways. That second half was added 2026-10-05, when a
    # revert probe showed the first could not see it: an unwrapped paragraph
    # inside a `FitScrollArea` widens the body, so the label has its full width
    # and the VIEWPORT cuts the text off instead — the install dialog's tool
    # description, ending mid-sentence, passed every rule.
    def sideways_clip(widget: object) -> object | None:
        """The viewport of the nearest scroll area with no horizontal bar."""
        parent = widget.parentWidget()  # type: ignore[attr-defined]  # a QWidget
        while parent is not None and parent is not w:
            if isinstance(parent, QAbstractScrollArea):
                off = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                return (
                    parent.viewport()
                    if parent.horizontalScrollBarPolicy() == off
                    else None
                )
            parent = parent.parentWidget()
        return None

    for widget in [*w.findChildren(QAbstractButton), *w.findChildren(QLabel)]:  # type: ignore[attr-defined]  # a QWidget
        text = widget.text()
        if not (text and shown(widget)):
            continue
        viewport = sideways_clip(widget)
        if viewport is not None:
            examined["cut_off_labels"] += 1
            right = widget.mapTo(viewport, QPoint(widget.width(), 0)).x()
            if right > viewport.width() + 1:  # type: ignore[attr-defined]  # a QWidget
                violations["cut_off_labels"].append(
                    f"runs {right - viewport.width()}px past its scroll area: "  # type: ignore[attr-defined]  # a QWidget
                    f"{type(widget).__name__} {text[:50]!r}"
                )
        if isinstance(widget, QLabel) and (widget.wordWrap() or "<" in text):
            continue
        examined["cut_off_labels"] += 1
        if widget.width() + 1 < widget.sizeHint().width():
            violations["cut_off_labels"].append(
                f"{widget.width()}px of {widget.sizeHint().width()}px: "
                f"{type(widget).__name__} {text[:50]!r}"
            )

    # cut_off_cells — a table cell, in view, whose text does not fit it. Added
    # 2026-10-05: with real releases the MusicBrainz picker squeezed Title and
    # Artist to three characters ("Lift Y…"), and no rule looked inside a table.
    # Measured with the view's own font and wrap setting against the cell's
    # rectangle less the style's text margin; a cell with a check box or an icon
    # is skipped, because part of its width is not text.
    for view in w.findChildren(QTableView):  # type: ignore[attr-defined]  # a QWidget
        model = view.model()
        if not shown(view) or model is None:
            continue
        metrics = view.fontMetrics()
        margin = 2 * (
            view.style().pixelMetric(
                QStyle.PixelMetric.PM_FocusFrameHMargin, None, view
            )
            + 1
        )
        wrap = Qt.TextFlag.TextWordWrap if view.wordWrap() else Qt.TextFlag(0)
        in_view = view.viewport().rect()
        for row in range(model.rowCount()):
            for column in range(model.columnCount()):
                index = model.index(row, column)
                text = model.data(index, Qt.ItemDataRole.DisplayRole)
                rect = view.visualRect(index)
                if (
                    not text
                    or not rect.intersects(in_view)
                    or model.data(index, Qt.ItemDataRole.CheckStateRole) is not None
                    or model.data(index, Qt.ItemDataRole.DecorationRole) is not None
                ):
                    continue
                examined["cut_off_cells"] += 1
                room = rect.width() - margin
                need = metrics.boundingRect(
                    QRect(0, 0, max(room, 1), 100_000), int(wrap), str(text)
                )
                if need.width() > room + 1 or need.height() > rect.height():
                    violations["cut_off_cells"].append(
                        f"{room}x{rect.height()}px cell needs "
                        f"{need.width()}x{need.height()}px: {str(text)[:40]!r}"
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
    if isinstance(w, QMainWindow):
        # The menu bar's titles share the window's Alt-keys.
        sources += [a.text() for a in w.menuBar().actions()]
    # Each menu is its own group — every submenu at any depth, and the album's
    # right-click menu — because a letter only has to be unique among the items
    # of the menu that is open.
    groups: list[tuple[str, list[str]]] = [("window", sources), *_menu_groups(w)]
    found, letters = _duplicate_mnemonics(groups)
    examined["duplicate_shortcuts"] += letters
    violations["duplicate_shortcuts"] += found

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
    """Subprocess entry: every window, in this process's one condition.

    **The cyclic collector is off for the whole run**, for the reason
    `tests/conftest.py::_cyclic_gc_paused_during_each_test` gives: a collection
    that starts while the main windows' worker threads are churning Qt objects
    under the offscreen platform is a hard crash. Every pytest test has that
    guard; this subprocess, which builds five main windows and hundreds of
    dialogs, never did. It surfaced on 2026-10-05 as a deterministic SIGSEGV
    after a change that only added Python wrappers for scroll-area viewports —
    an allocation pattern, not a bug, moved a collection onto the bad moment.
    The process exits as soon as it has printed, so nothing needs collecting.
    """
    import gc

    gc.disable()
    from conftest import stop_window_threads
    from PySide6.QtWidgets import QApplication
    from test_ui_message_box_conformance import measure_message_boxes

    from platterpus.ui.dialogs.auto_center import DialogCenterFilter

    app = QApplication([])
    _apply_condition(
        app,
        os.environ.get("PLATTERPUS_UI_THEME", "light"),
        float(os.environ.get("PLATTERPUS_UI_TEXT_SCALE", "1.0")),
    )
    # As `app.main` does: every dialog that is not a `CenteredDialog` is fitted
    # and placed by this filter, so a matrix without it measures a different app.
    centring = DialogCenterFilter(app)
    app.installEventFilter(centring)
    results: dict[str, object] = {}
    for name, make in _factories().items():
        results[name] = _measure_one(make())  # type: ignore[operator]  # factories are callables
    window = _main_window()
    results["MainWindow"] = _measure_one(window)
    stop_window_threads(window)
    results.update(_measure_long_picker())
    results.update(_measure_states())
    results.update(_measure_every_real_spec())
    results.update(_measure_real_cyanrip_windows())
    results.update(_measure_real_releases())
    results.update(measure_message_boxes(_measure_one, _main_window))
    return results


def _measure_real_releases() -> dict[str, object]:
    """The release picker with releases as long as MusicBrainz's real ones.

    Its factory uses `_release()` stand-ins — "Album" by "Artist", no label, no
    notes — and with those it always fitted. With a two-label credit and a
    disambiguation note, the columns sized to their content took the width and
    Title and Artist were squeezed to three characters (audit, 2026-10-05).
    """
    from test_ui_release_picker import _release

    from platterpus.ui.release_picker import ReleasePickerDialog

    skinny = "Lift Your Skinny Fists Like Antennas to Heaven"
    gybe = "Godspeed You! Black Emperor"
    releases = [
        _release("a", skinny, gybe, "2000-10-09", "CA", 4, "Constellation", "CST012"),
        _release(
            "b",
            skinny,
            gybe,
            "2000-10-09",
            "XE",
            4,
            "Kranky",
            "KRANK043",
            disambiguation="European edition with alternate artwork",
        ),
        _release(
            "c",
            skinny,
            gybe,
            "2021",
            "JP",
            4,
            "Constellation / Daymare Recordings",
            "DYMC-1234",
            medium="SHM-CD",
            disambiguation="Japanese reissue, remastered, with obi",
        ),
        _release(
            "d",
            "The Rise and Fall of Ziggy Stardust and the Spiders From Mars "
            "(2012 Remastered Version)",
            "David Bowie",
            "2012-06-04",
            "GB",
            11,
            "EMI",
            "5099946362622",
            disambiguation="40th anniversary edition",
        ),
    ]
    return {
        "ReleasePickerDialog[real-length releases]": _measure_one(
            ReleasePickerDialog(releases)
        )
    }


#: Two cyanrip windows measured with what they really say, by key.
REAL_CYANRIP_WINDOWS: tuple[str, ...] = (
    "HostSetupDialog[Updating cyanrip]",
    "SetupCenterDialog[real pins, every check section]",
)


def _measure_real_cyanrip_windows() -> dict[str, object]:
    """The cyanrip upgrade wizard and Setup & Updates, built by the real code.

    The factories build both from stand-ins — the setup wizard's own first-run
    copy, and Setup & Updates with pin `0000000`, version `0.0.0`, round 0 — so
    neither was ever measured saying what a user reads when a cyanrip build is
    installed or offered (audit, 2026-10-05, on the maintainer's *"odd cyanrip
    upgrades"*). The wizard is opened through `_begin_ripper_install`, the path
    the update offer and the build picker use, with its installer replaced by a
    stand-in that does nothing, so nothing is built; Setup & Updates through
    `open_setup_center`, with the real pins and a dependency report carrying
    every section the check can report.
    """
    from unittest import mock

    from conftest import stop_window_threads
    from test_ui_host_setup_dialog import _FakeHost
    from test_ui_message_box_conformance import _dependency_report_with_every_section

    import platterpus.deps.host_setup as host_setup
    from platterpus.deps import fork_source

    measured: dict[str, object] = {}
    window = _main_window()

    def measure_the_wizard(_self: object, build: object) -> None:
        measured[REAL_CYANRIP_WINDOWS[0]] = _measure_one(build())  # type: ignore[operator]  # the wizard factory

    with (
        mock.patch.object(host_setup, "HostSetup", lambda **_kw: _FakeHost(False)),
        mock.patch.object(type(window), "run_setup_wizard", measure_the_wizard),
    ):
        window._begin_ripper_install(None, fork_source.FORK_PIN)  # type: ignore[attr-defined]  # a MainWindow
    center = window.open_setup_center()  # type: ignore[attr-defined]  # a MainWindow
    center.show_dependency_check_finished(_dependency_report_with_every_section())
    measured[REAL_CYANRIP_WINDOWS[1]] = _measure_one(center)
    window._setup_center = None  # type: ignore[attr-defined]  # a MainWindow
    stop_window_threads(window)
    return measured


def _real_spec_keys() -> set[str]:
    """The windows :func:`_measure_every_real_spec` measures, by key."""
    from platterpus.deps.registry import SPECS

    return {f"ManualInstallDialog[{spec.dep_id}]" for spec in SPECS} | {
        "PendingInstallsDialog[every spec]"
    }


def _measure_every_real_spec() -> dict[str, object]:
    """The install dialogs with the REAL dependency specs, not the stand-ins.

    The factories above build `ManualInstallDialog` from a test spec with a
    one-line description, so the matrix passed it for months while the real
    `ffmpeg` and `cd-paranoia` descriptions — 2,656 and 2,403 px of unwrapped
    text — ran off its right edge on every screen, the "Why manual:" caption
    squeezed to "Why manu" (audit, 2026-10-05). Stand-in content measures the
    stand-in. Every spec in the registry, so a new one is measured the day it
    lands.
    """
    from platterpus.deps.checks import ProbeResult
    from platterpus.deps.registry import SPECS
    from platterpus.deps.resolvers import MissingItem
    from platterpus.ui.dialogs.manual_install import ManualInstallDialog
    from platterpus.ui.dialogs.pending_installs import PendingInstallsDialog

    absent = ProbeResult(present=False, version=None, location=None)
    measured: dict[str, object] = {}
    for spec in SPECS:
        measured[f"ManualInstallDialog[{spec.dep_id}]"] = _measure_one(
            ManualInstallDialog(spec, absent, on_setup_wizard=lambda: None)
        )
    measured["PendingInstallsDialog[every spec]"] = _measure_one(
        PendingInstallsDialog([MissingItem(spec=s, probe=absent) for s in SPECS])
    )
    return measured


def _measure_long_picker() -> dict[str, object]:
    """The picker with one, two and eight rows, whatever the round state is."""
    from unittest import mock

    # FUTURE-PROOFING, measured rather than promised. The picker lists whatever
    # builds the handshake record names; the maintainer asked that it keep
    # working "in case there are more options later". Eight rows is more than
    # any round has ever offered.
    #
    # **AND ONE ROW AND TWO, because the row count follows the round state and a
    # shape the matrix only sees in one state is a shape it stops seeing.** One
    # row is what the picker shows between rounds (production pin only); two is
    # what it shows while a round reviews a build. On 2026-09-28 round 28 closed,
    # the picker dropped to one row, and at 150% text on 1024x768 its body
    # scrolled 21 px in a window that could still grow: `fit_dialog_to_screen`
    # grew the window once, and the scrollbar that then appeared re-wrapped the
    # text a line taller. The un-suffixed `RipperPickerDialog` measures whichever
    # state the tree is in; these pin every state regardless of it.
    from platterpus.deps import fork_source
    from platterpus.ui.ripper_picker import RipperPickerDialog

    real = fork_source.ripper_choices()
    measured: dict[str, object] = {}
    for rows, key in ((1, "1 row"), (2, "2 rows"), (8, "8 rows")):
        with mock.patch.object(
            fork_source, "ripper_choices", return_value=[real[0]] * rows
        ):
            picker = RipperPickerDialog()
            report = _measure_one(picker)
            bar = picker._body_scroll.verticalScrollBar()
            report["scroll_range"] = bar.maximum() - bar.minimum()
        measured[f"RipperPickerDialog[{key}]"] = report
    return measured


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


def _concurrent_measurements() -> int:
    """How many measuring processes this pytest process runs at once.

    Each one builds five main windows and a few hundred dialogs, about 200 MB at
    its peak (measured 2026-10-05; 144 MB before the message boxes joined the
    matrix). All 22 used to start together, and under `pytest -n auto` every
    xdist worker that runs a matrix test builds its own matrix: four workers
    times 22 processes on a 4-CPU, 16 GB machine. That ran out of memory. The
    kernel killed workers, xdist replaced them, each replacement started 22
    more, and the run did not end (153 orphaned processes, load average 166,
    measured). So the CPUs are shared out instead, one process per CPU per
    worker. Starting more than that never finished sooner; it only held more
    memory at once.
    """
    workers = int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", "1") or "1")
    return max(1, (os.cpu_count() or 2) // max(workers, 1))


def _collect(cond_id: str, proc: subprocess.Popen[str]) -> dict[str, dict[str, object]]:
    """One condition's measurements, read off its finished process."""
    marker = "MEASUREMENTS:"
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
    result: dict[str, dict[str, object]] = json.loads(line[len(marker) :])
    return result


def _run_all_conditions() -> dict[str, dict[str, dict[str, object]]]:
    """Every window in every condition — one process each, a CPU's worth at a time.

    A failure stops the others: a process left running after its test has
    failed, or after pytest is killed mid-run, keeps its memory and its CPU
    until it finishes on its own (`_concurrent_measurements` has the case).
    """
    shapes = {name: (width, height) for name, width, height in SCREENS}
    tmp = Path(tempfile.mkdtemp())
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(REPO_ROOT / "tests")])
    pending: list[tuple[str, dict[str, str]]] = []
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
        pending.append(
            (
                cond_id,
                {
                    **env,
                    "QT_QPA_PLATFORM": f"offscreen:configfile={config}",
                    "PLATTERPUS_UI_THEME": theme,
                    "PLATTERPUS_UI_TEXT_SCALE": str(scale),
                },
            )
        )
    limit = _concurrent_measurements()
    measured: dict[str, dict[str, dict[str, object]]] = {}
    running: dict[str, subprocess.Popen[str]] = {}
    try:
        while pending or running:
            while pending and len(running) < limit:
                cond_id, cond_env = pending.pop(0)
                running[cond_id] = subprocess.Popen(
                    [sys.executable, __file__, "--measure"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=cond_env,
                )
            oldest = next(iter(running))
            measured[oldest] = _collect(oldest, running.pop(oldest))
    finally:
        for proc in running.values():
            proc.kill()
            proc.communicate()
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
    # Every window in every condition: 22 conditions x well over 150 windows once
    # the message boxes joined (2026-10-05). Set far under that, so it trips only
    # when a population stops being measured, not when one box is removed.
    "window_on_screen": 2000,
    "scrolls_only_when_capped": 40,
    "text_contrast": 1000,
    "button_floor": 500,
    "cut_off_labels": 1000,
    "duplicate_shortcuts": 200,
    "unnamed_inputs": 200,
    # The release picker's cells: 18 stand-in and 36 real-length cells per
    # condition when this was written (2026-10-05).
    "cut_off_cells": 500,
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
    from test_ui_message_box_conformance import expected_keys

    expected = (
        MEASURED
        | {"MainWindow", *STATES, *REAL_CYANRIP_WINDOWS}
        | {"ReleasePickerDialog[real-length releases]"}
        | _real_spec_keys()
        | expected_keys()
    )
    for cond_id, windows in matrix.items():
        missing = expected - set(windows)
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


def test_the_shortcut_rule_descends_into_submenus_and_context_menus(
    qapp: object,
) -> None:
    """Non-triviality for the recursion, in-process and against constructed menus.

    Three clashes the one-level rule could not see — in a submenu, in a
    submenu's submenu, and in the disc panel's album menu — must each be found;
    and a letter a submenu shares with its PARENT must not be, because only the
    open menu's items compete for it.
    """
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QMainWindow

    from platterpus.ui.disc_info_panel import DiscInfoPanel

    window = QMainWindow()
    tools = window.menuBar().addMenu("&Tools")
    tools.addAction("&Settings…")
    advanced = tools.addMenu("&Advanced")
    advanced.addAction("Run &test script…")
    advanced.addAction("&Tidy up…")  # Alt+T twice, inside the submenu
    advanced.addAction("&Save a copy…")  # Alt+S, which Tools also has: allowed
    deeper = advanced.addMenu("&Deeper")
    deeper.addAction("&One")
    deeper.addAction("&Other")  # Alt+O twice, two levels down
    panel = DiscInfoPanel(window)
    window.setCentralWidget(panel)
    panel.set_album_actions([QAction("&Cover…", panel)])  # clashes with &Copy

    groups = _menu_groups(window)
    violations, letters = _duplicate_mnemonics(groups)

    assert any("'&Advanced'" in v and "Alt+T" in v for v in violations), violations
    assert any("'&Deeper'" in v and "Alt+O" in v for v in violations), violations
    assert any(v.startswith("album menu") and "Alt+C" in v for v in violations)
    assert not any("Alt+S" in v for v in violations), violations
    # Every value label's menu was examined, plus the panel's own.
    assert sum(1 for where, _ in groups if where.startswith("album menu")) >= 8
    assert letters >= 10
    window.deleteLater()


def test_the_matrix_installs_the_filter_app_main_installs() -> None:
    """The matrix measures message boxes fitted by `DialogCenterFilter`; that is
    only evidence about the product if the product installs the same filter.

    Read from `app.py`'s AST: a name bound to `DialogCenterFilter(...)` inside
    `main`, handed to an `installEventFilter(...)` call there. Both halves,
    because a filter built and never installed fits nothing.
    """
    import ast

    tree = ast.parse((SRC / "platterpus" / "app.py").read_text(encoding="utf-8"))
    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    bound = {
        target.id
        for node in ast.walk(main)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "DialogCenterFilter"
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    installed = {
        arg.id
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "installEventFilter"
        for arg in node.args
        if isinstance(arg, ast.Name)
    }
    assert bound, "app.main no longer builds a DialogCenterFilter"
    assert bound & installed, (
        f"app.main builds {sorted(bound)} but installs only {sorted(installed)}"
    )
    # And the matrix's own subprocess installs it (this file's `_measure_all`).
    source = Path(__file__).read_text(encoding="utf-8")
    assert "app.installEventFilter(centring)" in source


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
