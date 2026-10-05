"""Manual-install dialog — tier (c) of the dependency subsystem.

Shown when a dependency can't be auto-installed and requires user
judgment or root privileges (the brief's classic example: `libdiscid`
via `rpm-ostree install + reboot` on Bazzite). The dialog presents:

  - The missing dependency's name and required minimum version
  - A one-line explanation of why we can't auto-install
  - A copyable read-only QLineEdit with a Google-search-ready query
  - Primary action: Copy. Secondary action: Close.

For dependencies the **setup wizard** provides (``spec.from_setup_wizard`` —
cyanrip/metaflac/flac/cd-paranoia, installed into the container and exported),
the user should NOT have to copy a search string: those get a primary **"Set
it up automatically…"** button that opens the wizard (one click, no terminal).
The copyable search string stays as a last-resort fallback.

No installation happens here for the search-string path — the user follows it
to resolve manually and re-runs the dependency check.
"""

from __future__ import annotations

import html
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.deps.checks import ProbeResult
from platterpus.deps.registry import DependencySpec
from platterpus.ui.accessibility import announce
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea


class ManualInstallDialog(CenteredDialog):
    """Tier (c) dialog. Modal; shown once per unresolvable dependency."""

    def __init__(
        self,
        spec: DependencySpec,
        probe: ProbeResult,
        parent: QWidget | None = None,
        on_setup_wizard: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._spec: DependencySpec = spec
        self._probe: ProbeResult = probe
        # When the dep comes from the setup wizard and the caller wired a
        # callback, offer the one-click wizard instead of making the user
        # copy a search string.
        self._on_setup_wizard: Callable[[], None] | None = (
            on_setup_wizard if getattr(spec, "from_setup_wizard", False) else None
        )

        self.setWindowTitle(f"Install required: {spec.display_name}")
        self.setModal(True)

        # Top-level layout: vertical with the form first, then the
        # copyable search-string row, then the button box.
        root = QVBoxLayout(self)

        # **The prose scrolls; the search string and the buttons do not.** The
        # intro and the spec's description are paragraphs, and on a short screen
        # at a large font (853 x 533 at 150 % text) there is not room for all of
        # it: the description was squeezed 4 px short of its last line, with
        # nothing to scroll (audit, 2026-10-05). `FitScrollArea` asks for the
        # whole body, so on any ordinary screen it is invisible.
        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_scroll = FitScrollArea(self)
        body_scroll.setWidget(body)
        body_scroll.setAccessibleName(f"Why {spec.display_name} needs installing")
        root.addWidget(body_scroll, stretch=1)

        # Every label built from a value STATES its text format. Qt's default,
        # AutoText, guesses: it treats the text as HTML when its first line
        # happens to contain a known tag, and then drops what it cannot render —
        # so the same label renders two ways depending on the value inside it
        # (CLAUDE.md Critical rule #12; tests/test_labels_state_their_text_format.py).
        #
        # RichText here, on purpose: the sentence and the <b>…</b> around the
        # button's name are ours. The dependency's display name is escaped. It is
        # ours today (deps/registry.py), but a DependencySpec is data, and this
        # label's markup must not depend on what a spec happens to contain.
        intro = QLabel(self._intro_markup(escaped_name=html.escape(spec.display_name)))
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setWordWrap(True)
        body_layout.addWidget(intro)

        # PlainText: versions and a description, none of it markup — and the
        # "Currently" version is read off the installed tool.
        required = QLabel(self._required_text())
        required.setTextFormat(Qt.TextFormat.PlainText)
        current = QLabel(self._current_text())
        current.setTextFormat(Qt.TextFormat.PlainText)
        why = QLabel(self._why_text())
        why.setTextFormat(Qt.TextFormat.PlainText)
        # Wrapped: the reason is the spec's DESCRIPTION, a paragraph (ffmpeg's is
        # 2,600 px of one line at the default font). Unwrapped, it pushed the
        # dialog to the full screen width and was still cut off mid-sentence at
        # the right edge, with its "Why manual:" caption squeezed to "Why manu"
        # (audit, 2026-10-05). The conformance matrix measures every real spec.
        why.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Required:", required)
        form.addRow("Currently:", current)
        form.addRow("Why manual:", why)
        body_layout.addLayout(form)

        # The copyable field. ReadOnly so the user can select but not
        # accidentally edit; selectByMouse + selectAll on focus keeps
        # the keyboard workflow ergonomic. For a wizard-provided dep this is
        # the *fallback*, labelled as such.
        self._search_field: QLineEdit = QLineEdit(spec.search_string, self)
        self._search_field.setReadOnly(True)
        self._search_field.setCursorPosition(0)
        field_label = (
            "Or, if you'd rather install it yourself — copyable search string:"
            if self._on_setup_wizard is not None
            else "Copyable search string:"
        )
        # The label is the field's BUDDY so a screen reader announces the field
        # by it; without that the field was a nameless text box.
        field_caption = QLabel(field_label)
        field_caption.setTextFormat(Qt.TextFormat.PlainText)
        field_caption.setBuddy(self._search_field)
        root.addWidget(field_caption)
        root.addWidget(self._search_field)

        # Button box. For wizard-provided deps, the primary action is
        # "Set it up automatically…" (opens the wizard); Copy/Close follow.
        # Otherwise Copy is primary (the brief's tier-(c) intent).
        button_box = QDialogButtonBox(self)
        self._setup_button: QPushButton | None = None
        if self._on_setup_wizard is not None:
            self._setup_button = button_box.addButton(
                "Set it &up automatically…", QDialogButtonBox.ButtonRole.AcceptRole
            )
            self._setup_button.clicked.connect(self._run_setup_wizard)
        self._copy_button: QPushButton = button_box.addButton(
            "&Copy", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._close_button: QPushButton = button_box.addButton(
            "Close", QDialogButtonBox.ButtonRole.RejectRole
        )
        # The most helpful action is the default: the wizard when available,
        # otherwise Copy.
        (self._setup_button or self._copy_button).setDefault(True)
        # Copy button doesn't close the dialog — user can copy multiple
        # times if they want. Close button does.
        self._copy_button.clicked.connect(self.copy_search_string)
        self._close_button.clicked.connect(self.reject)
        root.addWidget(button_box)

    # --- Setup-wizard action (wizard-provided deps only) -------------------

    def _run_setup_wizard(self) -> None:
        """Open the host-setup wizard, then close this dialog (accepted)."""
        if self._on_setup_wizard is not None:
            self._on_setup_wizard()
        self.accept()

    # --- Public surface -----------------------------------------------------

    def search_string(self) -> str:
        """Return what the Copy button would copy. Useful for tests."""
        return self._search_field.text()

    def copy_search_string(self) -> None:
        """Copy the search string to the system clipboard.

        Also briefly updates the Copy button label so the user sees
        feedback that the action took effect. We restore it shortly
        after via QTimer so the dialog can be used again.
        """
        QGuiApplication.clipboard().setText(self._search_field.text())
        self._copy_button.setText("Copied!")
        # The button-label flip is visual-only feedback — say it too (gap #4).
        announce(self._copy_button, "Search string copied to the clipboard.")
        # Reset the label after a short delay. Using Qt's single-shot
        # timer keeps the GUI thread non-blocking.
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1500, lambda: self._copy_button.setText("&Copy"))

    # --- Display string builders -------------------------------------------

    def _intro_markup(self, *, escaped_name: str) -> str:
        """The intro sentence, as MARKUP — the label shows it as RichText.

        `escaped_name` must already be HTML-escaped (the caller does it with
        `html.escape`), because it is interpolated into markup as it stands.
        """
        if self._on_setup_wizard is not None:
            return (
                f"{escaped_name} isn't set up yet. You don't need a "
                "terminal — click <b>Set it up automatically…</b> to run the "
                "one-time setup, which installs it for you. (If it's already "
                "running, it may just need a minute to finish.)"
            )
        return (
            f"{escaped_name} needs to be installed manually. "
            "Copy the search string below and use your distro's package "
            "tooling to resolve it, then re-run the dependency check "
            "from Settings."
        )

    def _required_text(self) -> str:
        version = ".".join(str(part) for part in self._spec.min_version)
        if version == "0.0.0":
            return "any installed version"
        return f">= {version}"

    def _current_text(self) -> str:
        if not self._probe.present:
            return "not installed"
        if self._probe.version is None:
            return "installed (version unknown)"
        version = ".".join(str(part) for part in self._probe.version)
        return f"installed: {version}"

    def _why_text(self) -> str:
        # Specs that need root, a reboot, or a distro-specific install
        # path are the typical tier-(c) inhabitants. Description gives
        # the human context.
        return self._spec.description or "Requires user action."
