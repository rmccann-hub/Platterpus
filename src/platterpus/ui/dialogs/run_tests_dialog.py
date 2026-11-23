"""Tools → Advanced → Run tests… — choose a test, see what it will do, run it.

**The owner's design** (TASKS R188, 2026-11-17; screenshots approved
2026-11-23). One screen in place of *Run acceptance test…*, *Run acceptance test
with an unknown disc…* and the script console's Load…, Choose… and Use built-in
buttons. Those pickers could reach only the full acceptance test among the
scripts packed inside the AppImage, so a script we named to the owner (the
over-read probe) was one they could not pick.

Three tabs choose the test, each producing one
:class:`~platterpus.uiscript.chosen_test.ChosenTest`:

* **Pre-built and yours**: the pre-built tests (``uiscript/prebuilt.py``), then
  every file in ``~/.config/platterpus/scripts/``, scanned when the screen opens
  and marked "(yours)".
* **Combination**: tick built-in blocks, each saying what it needs. They run in
  the catalogue's fixed order, and the setup they need is added once and named.
* **Script file**: any file, checked by content before Run is enabled.

Under the choice a box says what will run (by title), how long it takes and
whether it counts as evidence. **Run** starts the same session the old menu item
did (session folder, sleep lock, settings restored, one bundle), through the
window's callable; **Edit script…** opens the chosen script in the console; *Run
this at start-up* holds the two start-up settings, homed here
(``ui/setting_homes.py``).

**Nothing here blocks.** The work on a selection is reading a small packaged
file and parsing it (the Full run, 2,073 lines, parses in milliseconds) and the
estimate, which walks the steps in memory; the folder scan lists one small
folder once. The session's own slow parts (the sleep lock, the bundle) run on
the window's daemon threads, as they always have.

Every label that can carry a file name is PlainText (CLAUDE.md, inbound seam).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from platterpus.config import Config
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea
from platterpus.ui.dialogs.script_settings_box import ScriptSettingsBox
from platterpus.ui.plain_text import plain_tooltip
from platterpus.uiscript import blocks, chosen_test, prebuilt, script_files
from platterpus.uiscript.chosen_test import ChosenTest
from platterpus.user_settings import SettingWrite

log = logging.getLogger(__name__)

#: The line at the top of the screen, the owner's words.
INTRO: Final[str] = (
    "Choose a test and press Run. Each run gets its own session folder, puts "
    "your settings back when it ends, and packs one file to send."
)

#: The one line pointing at the C2 probe (the owner, 2026-11-23: it stays a rig
#: script run by hand, because it reads raw sectors inside the container).
C2_NOTE: Final[str] = (
    "The C2 probe is a rig script you run by hand: docs/rig-scripts/drivetest.sh"
)

#: The tab indexes.
TAB_PREBUILT: Final[int] = 0
TAB_COMBINATION: Final[int] = 1
TAB_FILE: Final[int] = 2

#: The height of the button that commits (WCAG 2.2 AA, the project's 44 px).
COMMIT_HEIGHT_PX: Final[int] = 44


class RunTestsDialog(CenteredDialog):
    """Choose a test; Run starts a session, Edit script… opens the console."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        config: Config,
        start: Callable[[ChosenTest], bool],
        edit: Callable[[ChosenTest], None],
        estimate: Callable[[ChosenTest], str] | None = None,
        save_setting: Callable[[str, object], SettingWrite] | None = None,
        scripts_dir: Path = script_files.USER_SCRIPTS_DIR,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run tests")
        self.resize(760, 760)
        self._start: Callable[[ChosenTest], bool] = start
        self._edit: Callable[[ChosenTest], None] = edit
        self._estimate: Callable[[ChosenTest], str] | None = estimate
        self._scripts_dir: Path = scripts_dir
        self._chosen_file: Path | None = None

        outer = QVBoxLayout(self)
        # THE BODY SCROLLS, THE BUTTONS DO NOT. Everything above Run sits in one
        # `FitScrollArea`, invisible while the screen has room (it asks for its
        # content's whole height) and scrolling on a small one (a Steam Deck at
        # 150% text), so Run and Close stay reachable. It is the ONLY scroll
        # surface: the test list shows every row and the Combination tab's boxes
        # are a plain column, because an inner surface with nothing left to
        # scroll swallows the wheel (`fit_scroll_area`'s docstring).
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        intro = QLabel(INTRO, body)
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(intro)

        self._tabs: QTabWidget = QTabWidget(body)
        self._tabs.addTab(self._build_prebuilt_tab(), "&Pre-built and yours")
        self._tabs.addTab(self._build_combination_tab(), "Com&bination")
        self._tabs.addTab(self._build_file_tab(), "Script &file")
        self._tabs.currentChanged.connect(lambda _index: self._refresh())
        layout.addWidget(self._tabs)

        what = QGroupBox("What will run", self)
        what_layout = QVBoxLayout(what)
        self._summary: QLabel = QLabel("", what)
        self._summary.setWordWrap(True)
        self._summary.setTextFormat(Qt.TextFormat.PlainText)
        self._summary.setAccessibleName("What will run")
        self._summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        what_layout.addWidget(self._summary)
        layout.addWidget(what)

        #: Run this at start-up: the two start-up settings, in their home.
        self._startup: ScriptSettingsBox = ScriptSettingsBox(
            self,
            script_path=config.test_script_path,
            autorun=config.test_script_autorun,
            save_setting=save_setting,
            chosen_path=self.startup_path_for_choice,
        )
        #: The controls the home table names (`ui/setting_homes.py`).
        self._startup_script_edit: QLineEdit = self._startup.startup_script_edit
        self._autorun_check: QCheckBox = self._startup.autorun_check
        layout.addWidget(self._startup)
        self._scroll: FitScrollArea = FitScrollArea(self)
        self._scroll.setAccessibleName("Choose a test")
        self._scroll.setWidget(body)
        outer.addWidget(self._scroll, stretch=1)

        buttons = QHBoxLayout()
        self._run_button: QPushButton = QPushButton("&Run", self)
        self._run_button.setDefault(True)
        self._run_button.setMinimumHeight(COMMIT_HEIGHT_PX)
        self._run_button.setAccessibleName("Run the chosen test")
        self._run_button.clicked.connect(self._on_run)
        buttons.addWidget(self._run_button)
        self._edit_button: QPushButton = QPushButton("&Edit script…", self)
        self._edit_button.setToolTip(
            "Open the chosen test's script in the test-script console, to read it "
            "or change it before running it from there."
        )
        self._edit_button.clicked.connect(self._on_edit)
        buttons.addWidget(self._edit_button)
        buttons.addStretch(1)
        close = QPushButton("&Close", self)
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        outer.addLayout(buttons)

        if self._prebuilt_list.count():
            self._prebuilt_list.setCurrentRow(0)
        self._refresh()

    # --- The three tabs -------------------------------------------------------

    def _build_prebuilt_tab(self) -> QWidget:
        page = QWidget(self)
        box = QVBoxLayout(page)
        self._prebuilt_list: QListWidget = QListWidget(page)
        self._prebuilt_list.setAccessibleName("Pre-built tests and your scripts")
        for test in prebuilt.PREBUILT:
            item = QListWidgetItem(f"{test.title} — {test.duration}")
            item.setData(Qt.ItemDataRole.UserRole, ("prebuilt", test.name))
            item.setToolTip(plain_tooltip(test.about))
            self._prebuilt_list.addItem(item)
        #: The owner's scripts, as found when the screen opened.
        self._user_scripts: tuple[Path, ...] = script_files.user_scripts(
            self._scripts_dir
        )
        for path in self._user_scripts:
            item = QListWidgetItem(f"{path.name} (yours)")
            item.setData(Qt.ItemDataRole.UserRole, ("yours", str(path)))
            item.setToolTip(plain_tooltip(str(path)))
            self._prebuilt_list.addItem(item)
        self._prebuilt_list.currentRowChanged.connect(lambda _row: self._refresh())
        # Every row shown, no scroll bar of its own (see the body's comment).
        self._prebuilt_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        rows = max(1, self._prebuilt_list.count())
        row_height = max(24, self._prebuilt_list.sizeHintForRow(0))
        self._prebuilt_list.setFixedHeight(
            rows * row_height + 2 * self._prebuilt_list.frameWidth() + 4
        )
        box.addWidget(self._prebuilt_list)
        where = QLabel(
            f"Your own scripts are read from {self._scripts_dir} when this screen "
            "opens; each is marked (yours).",
            page,
        )
        where.setWordWrap(True)
        where.setTextFormat(Qt.TextFormat.PlainText)
        box.addWidget(where)
        return page

    def _build_combination_tab(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        note = QLabel(
            "Tick the tests to run. They run in a fixed order, and the setup they "
            "need is added once and named below: ripper (the installed ripper "
            "answers), offset (the drive's read offset is set), disc (the disc "
            "is read and identified).",
            page,
        )
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(note)
        #: Each combinable block's tick-box, by block name.
        self._block_checks: dict[str, QCheckBox] = {}
        for block in blocks.combinable_blocks():
            text = f"{block.title} {block.needs_text()}".strip()
            check = QCheckBox(text, page)
            check.toggled.connect(lambda _on: self._refresh())
            outer.addWidget(check)
            self._block_checks[block.name] = check
        c2 = QLabel(C2_NOTE, page)
        c2.setWordWrap(True)
        c2.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(c2)
        return page

    def _build_file_tab(self) -> QWidget:
        page = QWidget(self)
        box = QVBoxLayout(page)
        row = QHBoxLayout()
        label = QLabel("Script file:", page)
        row.addWidget(label)
        self._file_edit: QLineEdit = QLineEdit(page)
        self._file_edit.setReadOnly(True)
        self._file_edit.setPlaceholderText("(none chosen)")
        self._file_edit.setAccessibleName("Script file")
        label.setBuddy(self._file_edit)
        row.addWidget(self._file_edit, stretch=1)
        choose = QPushButton("C&hoose a file…", page)
        choose.clicked.connect(self._on_choose_file)
        row.addWidget(choose)
        box.addLayout(row)
        explain = QLabel(
            "Any file name. It is checked before Run is enabled: plain UTF-8 text, "
            f"at most {script_files.MAX_SCRIPT_BYTES // 1024} KB, and every line a "
            "step the script language knows.",
            page,
        )
        explain.setWordWrap(True)
        explain.setTextFormat(Qt.TextFormat.PlainText)
        box.addWidget(explain)
        #: The check's verdict, with its mark (status is never colour alone).
        self._file_status: QLabel = QLabel("", page)
        self._file_status.setWordWrap(True)
        self._file_status.setTextFormat(Qt.TextFormat.PlainText)
        self._file_status.setAccessibleName("Script file check")
        box.addWidget(self._file_status)
        box.addStretch(1)
        return page

    # --- The choice -----------------------------------------------------------

    def current_choice(self) -> ChosenTest:
        """The test the screen would run now, on whichever tab is showing."""
        tab = self._tabs.currentIndex()
        if tab == TAB_COMBINATION:
            ticked = [n for n, c in self._block_checks.items() if c.isChecked()]
            return chosen_test.from_combination(ticked)
        if tab == TAB_FILE:
            if self._chosen_file is None:
                return ChosenTest(
                    "", "A script file", "full", "", None, problem="Choose a file."
                )
            return chosen_test.from_file(
                script_files.check_script_file(self._chosen_file)
            )
        item = self._prebuilt_list.currentItem()
        data = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if isinstance(data, tuple) and data[0] == "prebuilt":
            return chosen_test.from_prebuilt(prebuilt.PREBUILT_BY_NAME[data[1]])
        if isinstance(data, tuple) and data[0] == "yours":
            check = script_files.check_script_file(Path(data[1]))
            return chosen_test.from_file(check, yours=True)
        return ChosenTest("", "Nothing", "full", "", None, problem="Choose a test.")

    def select_prebuilt(self, name: str) -> bool:
        """Show the Pre-built tab with test ``name`` selected (also a test seam)."""
        for row in range(self._prebuilt_list.count()):
            item = self._prebuilt_list.item(row)
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, tuple) and data[1] == name:
                self._tabs.setCurrentIndex(TAB_PREBUILT)
                self._prebuilt_list.setCurrentRow(row)
                return True
        return False

    def choose_file(self, path: Path) -> None:
        """Show the Script file tab with ``path`` chosen (the picker's result)."""
        self._chosen_file = path
        self._file_edit.setText(str(path))
        self._tabs.setCurrentIndex(TAB_FILE)
        self._refresh()

    def summary_text(self) -> str:
        return self._summary.text()

    def _refresh(self) -> None:
        """Re-describe the choice, and enable Run and Edit only for a runnable one."""
        choice = self.current_choice()
        estimate = ""
        if choice.runnable and self._estimate is not None:
            estimate = self._estimate(choice)
        self._summary.setText(chosen_test.summary(choice, estimate))
        if self._chosen_file is not None and self._tabs.currentIndex() == TAB_FILE:
            self._file_status.setText(
                "✓ Checked: plain UTF-8 text, and every line a valid step."
                if choice.runnable
                else "⚠ Run stays off until this is fixed:\n" + choice.problem
            )
        self._run_button.setEnabled(choice.runnable)
        self._edit_button.setEnabled(bool(choice.text.strip()))
        self._startup.use_button.setEnabled(choice.runnable)

    # --- Buttons --------------------------------------------------------------

    def _on_choose_file(self) -> None:
        start = str(self._chosen_file or Path.home())
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Choose a test script", start, "All files (*)"
        )
        if chosen:
            self.choose_file(Path(chosen))

    def _on_run(self) -> bool:
        """Start the chosen test's session; close when it started."""
        choice = self.current_choice()
        if not choice.runnable:
            return False
        log.info("run tests: starting %s (%s)", choice.name, choice.title)
        if self._start(choice):
            self.accept()
            return True
        return False

    def _on_edit(self) -> None:
        choice = self.current_choice()
        if choice.text.strip():
            self._edit(choice)
            self.accept()

    def startup_path_for_choice(self) -> tuple[str, str]:
        """``(path, note)`` to save as the start-up script, or ``("", why not)``.

        A test that is a file is that file. A test made of blocks is written to
        the scripts folder first, under its name, so the start-up run has a file
        to read; the note says where, and that the screen lists it as yours.
        """
        choice = self.current_choice()
        if not choice.runnable:
            return "", choice.problem or "the chosen test cannot run"
        note = ""
        if choice.size != "full":
            note = "At start-up the whole script runs, at Full size."
        if choice.path is not None:
            return str(choice.path), note
        target = self._scripts_dir / f"{choice.name}.txt"
        try:
            self._scripts_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(choice.text, encoding="utf-8")
        except OSError as exc:
            log.warning("run tests: could not write %s: %s", target, exc)
            return "", f"could not write {target}: {exc}"
        return str(target), (note + f" Written to {target}; it is listed as yours.")

    def refresh_settings(self, config: Config) -> None:
        """Show ``config``'s start-up settings; the window calls it on a change."""
        self._startup.refresh_settings(config)
