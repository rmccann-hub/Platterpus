"""The two test-script settings, in their one home: Run this at start-up.

Which script runs at start-up, and whether it runs by itself when Platterpus
starts. Until 2026-09-24 they were edited in Settings as well: two editors of one
setting, where the one a user last touched was not necessarily the one in force.
From 2026-11-23 (TASKS R188) their home is the **Run tests…** screen, under *Run
this at start-up*, where tests are chosen: the script console lost its Choose…
and Use built-in buttons with its Load…, because one screen now chooses every
test. `ui/setting_homes.py` records the home, and `tests/test_setting_homes.py`
holds every window to it.

**Use this test** makes the test chosen above the start-up script. A test that
is a file (a packaged script, one of yours, a file you chose) is saved as that
file's path; a test made of blocks is first written to your scripts folder
(`~/.config/platterpus/scripts/`), where the screen lists it as yours next time.
The screen supplies that path through a callable, so this box needs to know
nothing about tests.

**Each change is saved as it is made**, through the window's single-setting
writer (`MainWindow._save_user_setting`), which validates with the same
predicate as the ``set`` script verb. A refused change is put back and the
validator's own sentence is shown, so a control never displays a value that is
not in force.

Nothing here blocks: validation is pure, and a save writes a small TOML file.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.ui.accessibility import announce

if TYPE_CHECKING:
    from collections.abc import Callable

    from platterpus.config import Config
    from platterpus.user_settings import SettingWrite

log = logging.getLogger(__name__)


class ScriptSettingsBox(QGroupBox):
    """Startup script and autorun, saved as they change."""

    #: A startup script was saved (``""`` when it was cleared).
    startup_script_saved = Signal(str)

    def __init__(
        self,
        parent: QWidget,
        *,
        script_path: str,
        autorun: bool,
        save_setting: Callable[[str, object], SettingWrite] | None,
        chosen_path: Callable[[], tuple[str, str]] | None = None,
    ) -> None:
        super().__init__("Run this at start-up (saved as you change it)", parent)
        #: Saves one setting through the window. ``None`` for a screen built
        #: with no window to save to (a test): the controls then change this
        #: screen only, and the log says so.
        self._save_setting: Callable[[str, object], SettingWrite] | None = save_setting
        #: ``(path, note)`` for the test chosen above, or ``("", why not)``.
        self._chosen_path: Callable[[], tuple[str, str]] | None = chosen_path
        box = QVBoxLayout(self)

        row = QHBoxLayout()
        label = QLabel("Start-up script:", self)
        row.addWidget(label)
        self.startup_script_edit: QLineEdit = QLineEdit(script_path, self)
        # Read-only: a path is chosen with a button, never typed, so there is no
        # half-typed value for the validator to refuse on every keystroke.
        self.startup_script_edit.setReadOnly(True)
        self.startup_script_edit.setPlaceholderText("(none)")
        self.startup_script_edit.setAccessibleName("Start-up script")
        self.startup_script_edit.setToolTip(
            "The script the console loads when it opens, and the one Platterpus "
            "runs at start-up if the box below is ticked. Leave empty for none."
        )
        label.setBuddy(self.startup_script_edit)
        row.addWidget(self.startup_script_edit, stretch=1)
        self.use_button: QPushButton = QPushButton("Use &this test", self)
        self.use_button.setAccessibleName("Use the chosen test as the start-up script")
        self.use_button.setToolTip(
            "Make the test chosen above the start-up script. It does not start "
            "anything: press Run for that."
        )
        self.use_button.clicked.connect(self.use_chosen_test)
        row.addWidget(self.use_button)
        clear = QPushButton("C&lear", self)
        clear.setAccessibleName("Clear the start-up script")
        clear.clicked.connect(lambda: self.set_startup_script(""))
        row.addWidget(clear)
        box.addLayout(row)

        self.autorun_check: QCheckBox = QCheckBox(
            "Run it &automatically when Platterpus starts", self
        )
        self.autorun_check.setChecked(autorun)
        self.autorun_check.setToolTip(
            "ON: launching Platterpus is the test run — the console opens and the "
            "start-up script above starts, so a session needs nobody in front of "
            "it. OFF (default): the script only loads, and runs when you press "
            "Run.\n\nIt does nothing without a start-up script: BOTH have to be "
            "set deliberately, because an app that runs a script at launch because "
            "a file said so is a surprising thing to ship."
        )
        self.autorun_check.toggled.connect(
            lambda on: self._save_box("test_script_autorun", self.autorun_check, on)
        )
        box.addWidget(self.autorun_check)

        self._status: QLabel = QLabel("", self)
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setWordWrap(True)
        self._status.setAccessibleName("Start-up settings status")
        box.addWidget(self._status)

    def refresh_settings(self, config: Config) -> None:
        """Show ``config``'s two script settings. Changes nothing.

        Called by the window when one of them changed elsewhere (a script's
        ``set``), so the boxes never show a value no longer in force. Signals are
        blocked: re-rendering must not look like a click and save again.
        """
        self.autorun_check.blockSignals(True)
        self.autorun_check.setChecked(bool(config.test_script_autorun))
        self.autorun_check.blockSignals(False)
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
            log.info("run tests: %s = %r for this screen only", field, value)
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
        if path:
            self.say(f"✓ Saved: {path}" + (f" {message}" if message else ""))
        else:
            self.say("✓ Saved: no start-up script.")
        self.startup_script_saved.emit(path)
        return True

    def use_chosen_test(self) -> bool:
        """Save the test chosen above as the start-up script. Says why when not."""
        if self._chosen_path is None:
            self.say("⚠ Not changed: no test is chosen.")
            return False
        path, note = self._chosen_path()
        if not path:
            self.say(f"⚠ Not changed: {note}")
            return False
        if not self.set_startup_script(path):
            return False
        if note:
            self.say(f"{self.status_text()} {note}")
        return True
