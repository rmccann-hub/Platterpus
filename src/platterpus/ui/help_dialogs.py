"""Help-menu dialogs: About (version + environment) and User Guide.

Both are thin read-only viewers built on `QTextBrowser` so links are clickable
and the (Markdown) content renders nicely. They construct off whatever is
available without doing any I/O that could block the UI — the About box reports
*configured* paths and interpreter/Qt versions, and deliberately does NOT shell
out to the ripper (which would mean entering the container and could stall).
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Callable

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from platterpus import __version__, build_info, help_content
from platterpus.build_info import build_fingerprint
from platterpus.deps import manager as dep_manager
from platterpus.paths import (
    CONFIG_PATH,
    CYANRIP_BINARY_DEFAULT,
    LOG_PATH,
)
from platterpus.report_types import ComponentInventory
from platterpus.ui.dialogs.centering import CenteredDialog


def _markdown_viewer(
    parent: QWidget | None, markdown: str, accessible_name: str
) -> QTextBrowser:
    """A read-only, link-clickable Markdown view.

    `accessible_name` names the document for screen readers (an anonymous
    QTextBrowser reads as just "text"). Links are keyboard-followable out of
    the box — QTextBrowser's default interaction flags include
    LinksAccessibleByKeyboard (Tab cycles the links, Enter opens).
    """
    view = QTextBrowser(parent)
    view.setOpenExternalLinks(True)  # open repo/issue links in the browser
    view.setAccessibleName(accessible_name)
    view.setMarkdown(markdown)
    return view


class AboutDialog(CenteredDialog):
    """Version number, every component's version, and support info (Help → About).

    **Every component, with when it was measured.** The versions are the same
    inventory Diagnostics, the rip report and the acceptance bundle carry
    (`build_info.component_inventory`), read from the newest dependency probe and
    never probed here: a probe enters the ripper's container. So the dependency
    versions are shown with their age, and **Check again** runs the app's own
    off-thread dependency check and refreshes this view when it lands.

    ``recheck`` is the window's hook for that: it starts the check and returns a
    function that stops this dialog being told, called when the dialog closes, so
    a check that finishes after the dialog is gone never reaches a deleted widget.
    Without it (a test, or no window) there is no button.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        recheck: Callable[[Callable[[], None]], Callable[[], None]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Platterpus")
        self.resize(560, 460)

        layout = QVBoxLayout(self)
        # Put the logo forward: a centered header image above the version text.
        # Best-effort — if the logo can't be loaded we just skip the image.
        from platterpus.app_icon import logo_pixmap

        pixmap = logo_pixmap(96)
        if pixmap is not None:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QLabel

            logo = QLabel(self)
            logo.setPixmap(pixmap)  # type: ignore[arg-type]
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo)
        self._viewer: QTextBrowser = _markdown_viewer(
            self, self._build_markdown(), "About Platterpus details"
        )
        layout.addWidget(self._viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        self._recheck = recheck
        self._stop_listening: Callable[[], None] | None = None
        self._recheck_button: QPushButton | None = None
        if recheck is not None:
            self._recheck_button = buttons.addButton(
                "Check &again", QDialogButtonBox.ButtonRole.ActionRole
            )
            self._recheck_button.setToolTip(
                "Measure every dependency's version again, in the background, and "
                "update this list when it finishes."
            )
            self._recheck_button.clicked.connect(self._on_recheck)
            self.finished.connect(self._forget_recheck)
        layout.addWidget(buttons)

    def _on_recheck(self) -> None:
        """Start the app's dependency check; the list refreshes when it lands."""
        if self._recheck is None or self._recheck_button is None:
            return
        self._recheck_button.setEnabled(False)
        self._recheck_button.setText("Checking…")
        self._forget_recheck()
        self._stop_listening = self._recheck(self._on_recheck_done)

    def _on_recheck_done(self) -> None:
        """The check landed: show the new versions and their new age."""
        self._stop_listening = None
        self._viewer.setMarkdown(self._build_markdown())
        if self._recheck_button is not None:
            self._recheck_button.setText("Check &again")
            self._recheck_button.setEnabled(True)

    def _forget_recheck(self) -> None:
        if self._stop_listening is not None:
            self._stop_listening()
            self._stop_listening = None

    @staticmethod
    def _components_markdown(inventory: ComponentInventory) -> str:
        """The dependency rows, each with a text marker, never colour alone."""
        deps = inventory["dependencies"]
        age = build_info.describe_measured_at(inventory["dependencies_measured_at"])
        if deps is None:
            return (
                f"### Dependencies\n- {age}. The check runs at launch; "
                "**Check again** runs it now.\n\n"
            )
        rows = []
        for name in sorted(deps):
            entry = deps[name]
            if entry["present"] and entry["min_version_met"]:
                mark = "✓"
            elif entry["present"]:
                mark = "⚠ below the minimum version"
            else:
                mark = "⚠ missing"
            version = entry["version"] or "version not reported"
            where = f" — `{entry['location']}`" if entry["location"] else ""
            rows.append(f"- {name}: {version} {mark}{where}")
        return f"### Dependencies ({age})\n" + "\n".join(rows) + "\n\n"

    @staticmethod
    def _build_markdown(inventory: ComponentInventory | None = None) -> str:
        if inventory is None:
            inventory = build_info.component_inventory(dep_manager.latest_report())
        py = inventory["python"] or "{}.{}.{}".format(*sys.version_info[:3])
        return (
            f"# Platterpus\n\n"
            f"**Version {inventory['app']}**\n\n"
            f"{help_content.TAGLINE}\n\n"
            f"### Environment\n"
            f"- Build: {inventory['build']}\n"
            f"- Python: {py}\n"
            f"- Qt: {inventory['qt'] or qVersion()}\n"
            f"- PySide6: {inventory['pyside6'] or PYSIDE_VERSION}\n"
            f"- Platform: {inventory['platform'] or platform.platform()}\n\n"
            + AboutDialog._components_markdown(inventory)
            + f"### Paths\n"
            f"- Config: `{CONFIG_PATH}`\n"
            f"- Log: `{LOG_PATH}`\n"
            f"- cyanrip binary: `{CYANRIP_BINARY_DEFAULT}`\n\n"
            f"### Project\n"
            f"- [Source & releases]({help_content.REPO_URL})\n"
            f"- [Report an issue]({help_content.ISSUES_URL})\n"
            f"- License: {help_content.LICENSE_NAME}\n"
        )


class HelpDialog(CenteredDialog):
    """The user guide, on Help → User Guide."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Platterpus — User Guide")
        self.resize(720, 580)

        layout = QVBoxLayout(self)
        layout.addWidget(
            _markdown_viewer(self, self._guide_markdown(), "User Guide content")
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _guide_markdown() -> str:
        """The user guide with a version footer stamped in at render time.

        The version is read live from ``__version__`` (not a hardcoded string in
        the guide text) so it always matches the app you're running and can never
        go stale — the same reason the About dialog shows the version dynamically.
        This is the user-facing counterpart to the docs' "Last updated for vX.Y.Z"
        stamps: the in-app guide is read where git history isn't visible, so a
        visible version is a real currency signal.

        ``user_guide()``, never the raw ``USER_GUIDE`` constant: the same
        render-time reasoning applies to the guide's command examples, which name
        *this* install rather than a program name that exists on one channel only.
        """
        return (
            f"{help_content.user_guide()}\n\n---\n\n"
            f"*User Guide for **Platterpus v{__version__}** "
            f"(build {build_fingerprint()}).*\n"
        )
