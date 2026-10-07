"""Help → Getting started: the walkthrough guide, offline, in a window of its own.

KDD-42 W6 puts the getting-started guide *in the app by default*: a viewer pane
that works with no network, shows the still pictures, plays the short loops, gives
every picture its alt text, can be read with the keyboard alone, and is readable in
both themes. The text and the pictures come from ``getting_started`` (the package's
``guide/`` folder); this module only shows them.

**Non-modal on purpose.** The guide is something you read *while* doing what it
says, so it must not block the main window the way the User Guide's ``exec()`` does.
The main window keeps one instance and raises it when asked again.

**Why the loops are animated by hand.** ``QTextBrowser`` draws a GIF as its first
frame and stops. Each loop gets a ``QMovie``, and every new frame is put back into
the document as the image's resource, so the browser repaints the moving picture
in place. A **Pause animations** button stops them all, because WCAG 2.2.2 requires
a way to stop anything that moves for longer than five seconds, and these loop for
ever. It exists only when the guide has a loop to pause.

No I/O beyond reading the guide's own files, which ship inside the package.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QHideEvent, QMovie, QShowEvent, QTextDocument
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from platterpus import getting_started
from platterpus.ui.dialogs.centering import CenteredDialog

log = logging.getLogger(__name__)

#: The window's title, also what a screen reader announces when it opens.
TITLE: str = "Platterpus — Getting started"
#: The toggle's two labels. Alt+P either way; no single-key shortcut (WCAG 2.1.4).
PAUSE_LABEL: str = "&Pause animations"
PLAY_LABEL: str = "&Play animations"


class GettingStartedDialog(CenteredDialog):
    """The getting-started guide (KDD-42), on Help → Getting started."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        markdown: str | None = None,
        base_dir: Path | None = None,
    ) -> None:
        """Show ``markdown`` (default: the packaged guide) with pictures from ``base_dir``.

        Both parameters exist for tests, which give the viewer a guide of their own
        with generated pictures; the app passes neither.
        """
        super().__init__(parent)
        self.setWindowTitle(TITLE)
        self.setModal(False)
        self.resize(760, 640)
        self._base_dir: Path = (
            base_dir if base_dir is not None else getting_started.GUIDE_DIR
        )
        text = markdown if markdown is not None else getting_started.guide_markdown()

        layout = QVBoxLayout(self)
        self._view: QTextBrowser = QTextBrowser(self)
        # A screen reader otherwise announces an anonymous QTextBrowser as "text".
        self._view.setAccessibleName("Getting started guide")
        # Links in the guide (the Releases page) open in the browser; following
        # one inside this pane would replace the guide with a web page it cannot
        # render.
        self._view.setOpenExternalLinks(True)
        # `images/…` in the text resolves against the guide's own folder.
        self._view.setSearchPaths([str(self._base_dir)])
        self._view.setMarkdown(text)
        layout.addWidget(self._view)

        #: One running movie per loop the text shows, keyed by the image's URL.
        self._movies: dict[str, QMovie] = {}
        self._start_loops(text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        self._pause_button: QPushButton | None = None
        if self._movies:
            self._pause_button = QPushButton(PAUSE_LABEL, self)
            self._pause_button.setCheckable(True)
            self._pause_button.toggled.connect(self._on_pause_toggled)
            buttons.addButton(
                self._pause_button, QDialogButtonBox.ButtonRole.ActionRole
            )
        layout.addWidget(buttons)

    def _start_loops(self, text: str) -> None:
        """Give every ``.gif`` the text shows a movie that repaints it in place."""
        for ref in getting_started.image_references(text):
            if not ref.target.lower().endswith(".gif") or ref.target in self._movies:
                continue
            path = self._base_dir / ref.target
            if not path.is_file():
                # The browser shows the alt text for a picture it cannot load; the
                # log says which file was missing, for whoever packaged it.
                log.warning("getting-started loop not found: %s", path)
                continue
            movie = QMovie(str(path), parent=self)
            if not movie.isValid():
                log.warning("getting-started loop is not a readable GIF: %s", path)
                continue
            url = ref.target
            movie.frameChanged.connect(
                lambda _frame, url=url, movie=movie: self._show_frame(url, movie)
            )
            self._movies[url] = movie
            movie.start()

    def _show_frame(self, url: str, movie: QMovie) -> None:
        """Put the movie's current frame into the document, and repaint."""
        self._view.document().addResource(
            QTextDocument.ResourceType.ImageResource, QUrl(url), movie.currentPixmap()
        )
        self._view.viewport().update()

    def _on_pause_toggled(self, paused: bool) -> None:
        """Pause or resume every loop, and say on the button what a press will do."""
        for movie in self._movies.values():
            movie.setPaused(paused)
        if self._pause_button is not None:
            self._pause_button.setText(PLAY_LABEL if paused else PAUSE_LABEL)

    def _user_paused(self) -> bool:
        """Whether the reader pressed Pause, which a hide and a show must not undo."""
        return self._pause_button is not None and self._pause_button.isChecked()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802 — Qt's name
        """Stop the loops while the window is closed: the main window keeps it."""
        for movie in self._movies.values():
            movie.setPaused(True)
        super().hideEvent(event)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt's name
        """Resume the loops on reopening, unless the reader had paused them."""
        super().showEvent(event)
        if not self._user_paused():
            for movie in self._movies.values():
                movie.setPaused(False)

    def movies(self) -> dict[str, QMovie]:
        """The running loops, by image URL. Read by tests."""
        return dict(self._movies)
