"""The three test-script settings, in their one home: the script console.

Which script loads at start-up, whether it runs by itself when Platterpus
starts, and whether the unsafe verbs are allowed. Until 2026-09-24 they were
edited in Settings as well, and the console carried a second, per-run copy of
the unsafe-verbs box: two editors of one setting, where the one a user last
touched was not necessarily the one in force. `ui/setting_homes.py` records that
they live here now, and `tests/test_setting_homes.py` holds every window to it.

**Each change is saved as it is made**, through the window's single-setting
writer (`MainWindow._save_user_setting`), which validates with the same
predicate as the ``set`` script verb. The console has no OK button to wait for,
and a change that took effect only on some later click would be one the user
believed they had made and had not. A refused change is put back and the
validator's own sentence is shown, so a control never displays a value that is
not in force.

**Why a widget of its own.** The console's job is to run a batch and show its
transcript; this box's job is three settings. Kept apart so neither file has to
be read to understand the other (`CLAUDE.md`: one responsibility per module).

Nothing here blocks: validation is pure, and a save writes a small TOML file.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.test_session import builtin_acceptance_script
from platterpus.ui.accessibility import announce

if TYPE_CHECKING:
    from collections.abc import Callable

    from platterpus.config import Config
    from platterpus.user_settings import SettingWrite

log = logging.getLogger(__name__)


class ScriptSettingsBox(QGroupBox):
    """Startup script, autorun and the unsafe verbs, saved as they change."""

    #: A startup script was saved (``""`` when it was cleared). The console
    #: decides whether loading it now would discard anything.
    startup_script_saved = Signal(str)

    def __init__(
        self,
        parent: QWidget,
        *,
        script_path: str,
        autorun: bool,
        allow_unsafe: bool,
        save_setting: Callable[[str, object], SettingWrite] | None,
    ) -> None:
        super().__init__("Script settings (saved as you change them)", parent)
        #: Saves one setting through the window. ``None`` for a console built
        #: with no window to save to (a test): the controls then change this
        #: console only, and the log says so.
        self._save_setting: Callable[[str, object], SettingWrite] | None = save_setting
        box = QVBoxLayout(self)

        row = QHBoxLayout()
        label = QLabel("Startup script:", self)
        row.addWidget(label)
        self.startup_script_edit: QLineEdit = QLineEdit(script_path, self)
        # Read-only: a path is chosen with a button, never typed, so there is no
        # half-typed value for the validator to refuse on every keystroke.
        self.startup_script_edit.setReadOnly(True)
        self.startup_script_edit.setPlaceholderText("(none — the console starts blank)")
        self.startup_script_edit.setAccessibleName("Startup script")
        self.startup_script_edit.setToolTip(
            "The script this console loads when it opens, and the one Platterpus "
            "runs at start-up if the box below is ticked. Leave empty for none."
            "\n\nEach line is one step (open a dialog, check what is on screen, "
            "take a screenshot, run the ripper and assert its exit code). A "
            "failing step is recorded and the batch keeps going, so an unattended "
            "run always comes back with a complete transcript."
        )
        label.setBuddy(self.startup_script_edit)
        row.addWidget(self.startup_script_edit, stretch=1)
        choose = QPushButton("C&hoose…", self)
        choose.setAccessibleName("Choose the startup script")
        choose.clicked.connect(self._on_choose_startup_script)
        row.addWidget(choose)
        builtin = QPushButton("Use &built-in", self)
        builtin.setAccessibleName("Use the built-in acceptance test script")
        builtin.setToolTip(
            "Use the full acceptance test that ships inside Platterpus as the "
            "startup script. It does not start anything: press Run, or use "
            "Tools → Run acceptance test… for the whole session."
        )
        builtin.clicked.connect(self.use_builtin_acceptance_script)
        row.addWidget(builtin)
        clear = QPushButton("Cl&ear", self)
        clear.setAccessibleName("Clear the startup script")
        clear.clicked.connect(lambda: self.set_startup_script(""))
        row.addWidget(clear)
        box.addLayout(row)

        self.autorun_check: QCheckBox = QCheckBox(
            "Run it automatically when Platterpus starts", self
        )
        self.autorun_check.setChecked(autorun)
        self.autorun_check.setToolTip(
            "ON: launching Platterpus is the test run — the console opens and the "
            "startup script above starts, so a session needs nobody in front of "
            "it. OFF (default): the script only loads, and runs when you press "
            "Run.\n\nIt does nothing without a startup script: BOTH have to be set "
            "deliberately, because an app that runs a script at launch because a "
            "file said so is a surprising thing to ship."
        )
        self.autorun_check.toggled.connect(
            lambda on: self._save_box("test_script_autorun", self.autorun_check, on)
        )
        box.addWidget(self.autorun_check)

        # "not built yet" because they are not: `eval` and `call` carry
        # `implemented=False` and have no handler, so this box gates nothing
        # today. A control that advertises a capability it cannot deliver is the
        # same defect as the `expect-status` gap (2026-08-24).
        self.unsafe_check: QCheckBox = QCheckBox(
            "Allow the unsafe script verbs (eval, call — not built yet)", self
        )
        self.unsafe_check.setChecked(allow_unsafe)
        self.unsafe_check.setToolTip(
            "OFF (default), and turning it ON changes nothing yet: eval and call "
            "are reserved but not implemented, so a script using either is refused "
            "either way. The vocabulary is otherwise a closed list of named actions "
            "with nothing that can run arbitrary code. If the escape hatch is ever "
            "built, ON is its gate, and a run that used it would say so at the top "
            "of its own transcript."
        )
        self.unsafe_check.toggled.connect(
            lambda on: self._save_box("test_script_allow_unsafe", self.unsafe_check, on)
        )
        box.addWidget(self.unsafe_check)

        self._status: QLabel = QLabel("", self)
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setWordWrap(True)
        self._status.setAccessibleName("Script settings status")
        box.addWidget(self._status)

    def refresh_settings(self, config: Config) -> None:
        """Show ``config``'s three script settings. Changes nothing.

        Called by the window when one of them changed elsewhere (a script's
        ``set``), so the boxes never show a value no longer in force. Signals are
        blocked: re-rendering must not look like a click and save again.
        """
        for box, value in (
            (self.autorun_check, config.test_script_autorun),
            (self.unsafe_check, config.test_script_allow_unsafe),
        ):
            box.blockSignals(True)
            box.setChecked(bool(value))
            box.blockSignals(False)
        self.startup_script_edit.setText(config.test_script_path)

    # --- Saving -------------------------------------------------------------

    def say(self, text: str) -> None:
        """Show, and announce, what the last change did."""
        self._status.setText(text)
        announce(self._status, text)

    def status_text(self) -> str:
        return self._status.text()

    def _save(self, field: str, value: object) -> tuple[bool, str]:
        """Save one setting through the window; ``(applied, message)``."""
        if self._save_setting is None:
            log.info("script console: %s = %r for this console only", field, value)
            return True, ""
        result = self._save_setting(field, value)
        return result.applied, result.message

    def _save_box(self, field: str, box: QCheckBox, checked: bool) -> None:
        applied, message = self._save(field, checked)
        if not applied:
            # Refused: put the box back, so it never shows a value not in force.
            box.blockSignals(True)
            box.setChecked(not checked)
            box.blockSignals(False)
            self.say(f"⚠ Not changed: {message}")
            return
        self.say(f"✓ Saved.{' ' + message if message else ''}")

    def set_startup_script(self, path: str) -> bool:
        """Save ``path`` (``""`` for none) as the startup script."""
        applied, message = self._save("test_script_path", path)
        if not applied:
            self.say(f"⚠ Not changed: {message}")
            return False
        self.startup_script_edit.setText(path)
        if message:
            self.say(f"✓ Saved. {message}")
        self.startup_script_saved.emit(path)
        return True

    def _on_choose_startup_script(self) -> None:
        start = self.startup_script_edit.text() or str(Path.home())
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Choose the startup script",
            start,
            "Scripts (*.txt *.pscript);;All files (*)",
        )
        if chosen:
            self.set_startup_script(chosen)

    def use_builtin_acceptance_script(self) -> None:
        """Make the acceptance batch we ship the startup script.

        **Says why when it cannot.** `builtin_acceptance_script` returns a
        *reason* alongside the path precisely so a missing file produces a
        sentence rather than a field that silently stays empty — a build whose
        package data did not make it in is a real failure mode (it is one
        `pyproject.toml` line), and "nothing happened when I clicked" is the
        least diagnosable way to report it. PlainText, because the reason embeds
        a filesystem path and Qt's default `AutoText` would swallow a path
        containing `<` as markup (Critical rule #12, inbound half).
        """
        path, reason = builtin_acceptance_script()
        if path is None:
            log.error("the built-in acceptance script is unavailable: %s", reason)
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Built-in test script unavailable")
            box.setTextFormat(Qt.TextFormat.PlainText)
            box.setText(reason)
            box.exec()
            return
        log.info("startup script set to the built-in acceptance batch: %s", path)
        self.set_startup_script(str(path))
