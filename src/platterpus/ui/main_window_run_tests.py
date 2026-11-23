"""The main window's half of Tools → Advanced → Run tests… (TASKS R188).

Extracted as a mixin, like the other ``main_window_*`` concerns (KDD-19), so the
provisioning mixin (`main_window_provision`, past 2,000 lines and on the size
ratchet) gains only the parameters its one session start takes. Its methods stay
reachable as ``window._x``. What it does:

* opens the Run tests screen (`open_run_tests_dialog`), keeping one, and raising
  it if it is already open;
* starts the chosen test's session (`run_chosen_test`), through the same
  `run_acceptance_session` the old menu item called, so the session folder, the
  sleep lock, the settings restore and the one bundle are unchanged;
* opens the chosen script in the test-script console (`edit_chosen_test`);
* estimates a choice against this window's disc and drive
  (`_estimate_chosen_test`), with the estimate the runner itself logs.

Nothing here blocks: each method builds a dialog, or hands values to methods
that already run their slow parts off the GUI thread.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from platterpus.ui.main_window_shared import MainWindowShared

if TYPE_CHECKING:
    from pathlib import Path

    from platterpus.ui.dialogs.run_tests_dialog import RunTestsDialog
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.uiscript.chosen_test import ChosenTest

log = logging.getLogger(__name__)


class RunTestsMixin(MainWindowShared):
    """Opens the Run tests screen and starts what it chose."""

    #: The Run tests screen while it is open, so a second menu click raises it
    #: and the window can refresh its start-up settings. ``None`` otherwise.
    _run_tests_dialog: RunTestsDialog | None = None

    if TYPE_CHECKING:

        def run_acceptance_session(
            self,
            size: str | None = None,
            *,
            script_name: str = "",
            script_path: Path | None = None,
            script_text: str = "",
            test_name: str = "",
            blocks: tuple[str, ...] = (),
        ) -> bool: ...

        def open_script_console(
            self, *, autorun: bool = False
        ) -> ScriptConsoleDialog: ...

    def open_run_tests_dialog(self) -> RunTestsDialog:
        """Tools → Advanced → Run tests…: show the screen (one at a time)."""
        from platterpus.ui.dialogs.run_tests_dialog import RunTestsDialog

        existing = self._run_tests_dialog
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return existing
        dialog = RunTestsDialog(
            self,
            config=self._config,
            start=self.run_chosen_test,
            edit=self.edit_chosen_test,
            estimate=self._estimate_chosen_test,
            save_setting=self._save_user_setting,
        )
        # Deleted when it closes: `open()` returns at once and the window is its
        # parent, so without this every visit would leave a hidden dialog behind.
        # The reference is dropped with it, so nothing reaches a deleted widget.
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.destroyed.connect(self._forget_run_tests_dialog)
        self._run_tests_dialog = dialog
        dialog.open()
        return dialog

    def _forget_run_tests_dialog(self) -> None:
        """The screen was deleted: drop the reference to it."""
        self._run_tests_dialog = None

    def run_chosen_test(self, choice: ChosenTest) -> bool:
        """Start ``choice``'s session. Returns whether it started.

        A file is loaded as itself; a test made of blocks is written into the
        session folder first. Either way the run carries the test's name and
        blocks into its report, and evidence is judged from them.
        """
        log.info(
            "run tests: %s chosen (%s, %s)", choice.name, choice.title, choice.size
        )
        return self.run_acceptance_session(
            size=choice.size,
            script_path=choice.path,
            script_text="" if choice.path is not None else choice.text,
            test_name=choice.name,
            blocks=choice.blocks,
        )

    def edit_chosen_test(self, choice: ChosenTest) -> None:
        """Open the test-script console holding ``choice``'s script."""
        console = self.open_script_console()
        console.set_script_text(choice.text)
        log.info("run tests: %s opened in the console", choice.name)

    def _estimate_chosen_test(self, choice: ChosenTest) -> str:
        """The runner's own estimate for ``choice`` on this window. Never raises."""
        from platterpus.uiscript.estimate_verbs import estimate_for_window
        from platterpus.uiscript.run_block import expand_run_blocks
        from platterpus.uiscript.runner import MAX_WAIT_S, TICK_MS
        from platterpus.uiscript.script import parse

        steps = expand_run_blocks(parse(choice.text)).steps
        return estimate_for_window(
            self,
            steps,
            run_size=choice.size,
            tick_s=TICK_MS / 1000,
            wait_cap_s=MAX_WAIT_S,
        )
