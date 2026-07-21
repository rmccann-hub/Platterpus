"""In-app read-only viewer for a rip's ``.log`` / ``.platterpus.json`` (IMP-1).

Why this exists (real-user report): a ``.log`` or ``.platterpus.json`` usually
has no registered default application on a fresh KDE, so
``QDesktopServices.openUrl`` pops the "Open With" app-chooser — the "weird option
for picking an app" the maintainer hit, and a jarring break from the
zero-terminal bar. Showing the file in a self-contained, read-only pane avoids
the chooser entirely, while an "Open externally…" button still defers to the OS
for anyone who prefers their own editor.

Self-contained and testable: the file read is a pure, injectable function (no
network, no external process), and the external-open callable is injected the
same way the rest of the UI injects ``QDesktopServices.openUrl``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.ui.dialogs.centering import CenteredDialog

log = logging.getLogger(__name__)

# Cap the in-app read so a pathologically large file (a marathon debug log)
# can't hang the GUI laying it out. The full file is always one click away via
# "Open externally…". A few MiB comfortably holds any real rip log/report.
_MAX_VIEW_BYTES: int = 8 * 1024 * 1024

# A reader takes a path and returns its text (best-effort, never raises).
FileReader = Callable[[Path], str]
# The external opener, matching QDesktopServices.openUrl's shape.
OpenUrlFn = Callable[[QUrl], bool]


def read_text_bounded(path: Path) -> str:
    """Read ``path`` as text for display — bounded, UTF-8 with replacement,
    never raises. A read failure or an over-cap file degrades to a clear note
    rather than an exception (the viewer must always show *something*)."""
    try:
        data = path.read_bytes()[: _MAX_VIEW_BYTES + 1]
    except OSError as exc:
        log.warning("could not read %s for the in-app viewer: %s", path, exc)
        return f"(could not open {path.name}: {exc})"
    over_cap = len(data) > _MAX_VIEW_BYTES
    text = data[:_MAX_VIEW_BYTES].decode("utf-8", errors="replace")
    if over_cap:
        text += (
            "\n\n… (truncated for display — use “Open externally…” for the full file)"
        )
    return text


class FileViewerDialog(CenteredDialog):
    """A read-only, monospace view of a single text file (log or JSON report)."""

    def __init__(
        self,
        path: Path,
        *,
        title: str | None = None,
        parent: QWidget | None = None,
        reader: FileReader | None = None,
        open_url: OpenUrlFn | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = Path(path)
        # Injected so tests never launch a real external app.
        self._open_url: OpenUrlFn = open_url or QDesktopServices.openUrl

        self.setWindowTitle(title or self._path.name)
        self.resize(820, 620)

        layout = QVBoxLayout(self)
        self._view = QPlainTextEdit(self)
        self._view.setReadOnly(True)
        # A rip log / JSON is column-aligned; wrapping would scramble it.
        self._view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._view.setFont(mono)
        self._view.setAccessibleName(f"Contents of {self._path.name}")
        self._view.setPlainText((reader or read_text_bounded)(self._path))
        layout.addWidget(self._view)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        # "Open externally…" is the escape hatch to the OS for those who want it
        # — but it's no longer the ONLY way to read the file.
        self._open_external_button = QPushButton("Open &externally…", self)
        buttons.addButton(
            self._open_external_button, QDialogButtonBox.ButtonRole.ActionRole
        )
        self._open_external_button.clicked.connect(self._on_open_external)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_open_external(self) -> None:
        self._open_url(QUrl.fromLocalFile(str(self._path)))
