"""One window for setup, dependencies and both update checks.

**Why this exists.** A real user, after an update (2026-09-21): *"when i went to
check for updates it kept asking me, repeatedy or this that or the other, and
other dependanciessn, other applications, other whatever, this was too much…
Why the need for 2 menu items for updating, and a separate for set up and
dependcies, can't this all be shown on one window?"*

They were describing two separate things that felt like one, and both were real:

* **Six menu items for four questions.** *Check for updates*, *Check for cyanrip
  updates* and *Install a cyanrip build* sat in **Help**, which is for
  documentation; *Set up Platterpus*, *Add app shortcut* and *Set up drive* sat
  in **Tools**; and the dependency check had no menu item at all — it was a
  button inside Settings. Somebody asking "is my install healthy?" had to know
  which of three menus held which half of the answer.
* **A chain of modals at launch.** Up to five, in sequence, each its own
  decision. That half is fixed at its cause (`run_setup_wizard` and the
  dependency check's floor check); this window is the other half — the place the
  answers live when the user goes looking for them instead of being asked.

**It owns no logic, and that is deliberate.** Every button here delegates to the
method that already does the job — `_on_check_updates`, `_on_check_ripper_updates`,
`_on_pick_ripper_build`, `_on_check_dependencies`, `open_host_setup_dialog`,
`_on_drive_setup`, `_on_add_app_shortcut`. A consolidated window that
re-implemented any of them would be a second answer to a question that already
has one, free to disagree with the report a rip writes (`CLAUDE.md`: one
predicate, N callers). What this file contributes is *placement*, not behaviour.

**It holds three settings, and only these three** (2026-09-24). A setting lives
beside what it steers (`ui/setting_homes.py`), so the two update channels sit
above the checks they decide, and the read offset — edited in *Set up drive…* —
is shown in the Drive section. Each tick-box saves the moment it is clicked,
through the window's one single-setting writer (`_save_user_setting`), because
this window has no OK to wait for and a change that took effect only on some
later button would be one the user believed they had made and had not.

**It never probes.** Everything it displays is either a module constant or a
value the window already cached — nothing here shells out, and in particular
nothing asks the container what ripper is installed, because that enters
Distrobox and would freeze the GUI thread for the length of a cold start. The
live answers arrive the way they always did: through the checks the buttons
start, which run on workers.

**Modeless, and held by the window.** Its buttons open modal dialogs on top of
it, so it must not be modal itself — an `exec()` here would put every one of them
inside this window's nested event loop, which is the stacking this whole change
exists to stop. `show()` alone would let Qt garbage-collect it the moment the
opening call returns, so the window keeps the reference and re-opening raises the
existing one, exactly as `open_script_console` does.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus import offset_config
from platterpus.ui.accessibility import announce

# The dependency line is the same verdict the status bar shows when a check lands,
# so it lives with the other dependency-check sentences and is imported here — one
# function, two surfaces, so they cannot describe one report two ways. Re-exported
# under this module's name because tests and callers already import it from here.
from platterpus.ui.dependency_check_status import (
    INFO_MARK,
    OK_MARK,
    WARN_MARK,
    dependency_summary_line,
)
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea
from platterpus.ui.plain_text import plain_tooltip
from platterpus.update_check import CHANNEL_BETA, CHANNEL_STABLE

if TYPE_CHECKING:
    from collections.abc import Callable

    from platterpus.config import Config
    from platterpus.user_settings import SettingWrite

log = logging.getLogger(__name__)

#: Minimum height for a control that commits an action, and the floor for one
#: that does not — the accessibility convention in `CLAUDE.md`. An explicit size
#: is a size you own: Qt's platform default is the user-agent exception, and
#: setting one forfeits it.
_COMMIT_HEIGHT: int = 44
_TARGET_FLOOR: int = 24

#: The buttons that change something the moment they are pressed, by key, and so
#: are held to `_COMMIT_HEIGHT`. Only *Add app shortcut* does: it writes the menu
#: entry at once. Every other button runs a check or opens a window (its "…"),
#: where the commit is a later button of that window's own.
#:
#: **Why every button was 44 px until 2026-11-17, and why not now.** The seven
#: full-width 44 px buttons stacked under their status lines read as a wall with
#: nothing primary, and the body needed 814 px, so the window scrolled on an
#: 800 px screen (UX review of 0.7.127, L2: 560 × 736 with a 67 px scroll).
_COMMITS: frozenset[str] = frozenset({"shortcut"})

#: The status marker vocabulary, from the one place it is defined. **Never colour
#: alone** — every level carries a glyph (`dependency_check_status`).
_OK: str = OK_MARK
_WARN: str = WARN_MARK
_INFO: str = INFO_MARK

#: The dependency button's label while a check the user asked for runs. No
#: mnemonic: a disabled button cannot be activated. Its label at rest stays the
#: literal in the section list below, because `tests/test_help_documents_the_menu`
#: reads the section buttons out of this source to resolve every menu path the
#: product names — a label held in a constant would vanish from that model.
_DEP_CHECK_BUSY_LABEL: str = "Checking dependencies…"


class SetupCenterDialog(CenteredDialog):
    """Setup, dependencies and updates, in one place.

    The parent window is the only collaborator: this dialog reads a few cached
    values off it and calls its existing slots. It is constructed with explicit
    callables rather than reaching into the window itself, so the wiring is
    visible at the call site and the dialog is testable without a MainWindow.
    """

    def __init__(
        self,
        parent: QWidget | None,
        *,
        app_version: str,
        ripper_pin: str,
        ripper_version: str,
        approved_by_round: int,
        dependency_report: object | None,
        actions: dict[str, Callable[[], object]],
        config: Config,
        save_setting: Callable[[str, object], SettingWrite],
        drive_offset: Callable[[], offset_config.DriveOffset] | None = None,
        drive_standing: Callable[[], str] | None = None,
        setup_standing: Callable[[object | None], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Setup & Updates")
        # Reads what the next rip on the SELECTED drive applies (the window's
        # `_selected_drive_offset`). A reader, not a value: the offset is per
        # drive, so it changes when the drive does, and every refresh asks again.
        self._drive_offset: Callable[[], offset_config.DriveOffset] | None = (
            drive_offset
        )
        # Whether drive setup and setup have anything left to do, checked against
        # the drive and the tools there now (the owner, 2026-11-25, TASKS R248:
        # "let users know if the hardware is the same as the last setup not need
        # to run (and check if it is)"). Readers, asked on every refresh.
        self._drive_standing: Callable[[], str] | None = drive_standing
        self._setup_standing: Callable[[object | None], str] | None = setup_standing
        self._setup_label: QLabel = QLabel("")
        self._setup_label.setTextFormat(Qt.TextFormat.PlainText)
        self._setup_label.setWordWrap(True)
        # NOT modal — see the module docstring. Its buttons open modal dialogs,
        # and a modal parent would nest every one of them inside this window's
        # event loop.
        self.setModal(False)

        self._actions: dict[str, Callable[[], object]] = actions
        self._save_setting: Callable[[str, object], SettingWrite] = save_setting
        self._dependency_label: QLabel | None = None
        #: Every action button, so a rip can lock them all (`set_locked`).
        self._buttons: dict[str, QPushButton] = {}
        #: Each button's label as built, so one relabelled while busy can be put
        #: back exactly — mnemonic included — rather than from a second copy.
        self._button_labels: dict[str, str] = {}
        #: Two independent reasons the dependency button can be greyed, kept apart
        #: so ending one cannot re-enable a button the other still needs off: a
        #: rip ending must not re-arm "Check dependencies" mid-check.
        self._locked: bool = False
        self._dep_check_busy: bool = False

        root = QVBoxLayout(self)

        # The sections scroll; Close does not. Four sections of buttons plus their
        # status lines need ~710 px, which a 1080p panel at 200% scaling (540
        # logical px) cannot give — measured, and it is the screen shape that cut
        # the cyanrip build picker off mid-sentence on 2026-09-23. `FitScrollArea`
        # is invisible whenever the content fits.
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        self._body_scroll: FitScrollArea = FitScrollArea(self)
        self._body_scroll.setWidget(body)
        self._body_scroll.setAccessibleName("Setup and update actions")
        root.addWidget(self._body_scroll, stretch=1)

        intro = QLabel(
            "Everything about keeping Platterpus and its ripper healthy, in one "
            "place. Each check runs in the background and reports back here or "
            "in its own window."
        )
        # PlainText everywhere text can carry a version string, a commit or a
        # dependency's own output: Qt's default AutoText auto-detects HTML, so a
        # line that merely looks like markup is interpreted rather than shown,
        # and the user never learns text went missing.
        intro.setTextFormat(Qt.TextFormat.PlainText)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # The one tick-box vocabulary on this window: each is the two-value view
        # of a channel STRING (a third channel needs no config migration).
        self._app_beta_check: QCheckBox = QCheckBox(
            "Offer beta (&pre-release) updates", self
        )
        self._app_beta_check.setToolTip(
            "ON: Check for updates also offers pre-release builds (0.6.4b1, "
            "0.6.5rc1…). OFF (default): only finished releases are offered, so "
            "'up to date' means up to date on the stable channel.\n\nBetas are "
            "published for testing: they may contain bugs, and a beta's rip "
            "reports can name a ripper build no handshake round has approved yet. "
            "Every beta offer says so before it installs, and you can go back to a "
            "stable release at any time.\n\nSaved as soon as you click it. Leave "
            "this off unless you are testing."
        )
        self._ripper_beta_check: QCheckBox = QCheckBox(
            "Offer beta (pre-re&lease) cyanrip builds", self
        )
        self._ripper_beta_check.setToolTip(
            "ON: Check for cyanrip updates also tells you about beta builds the "
            "fork has published for testing. OFF (default): only stable builds, "
            "from a closed handshake round.\n\nThis tick-box installs nothing: it "
            "only reports what the fork has published, and says what taking a "
            "build would cost. A ripper no handshake round has verified makes every "
            "rip afterwards report its ripper as 'unapproved': the audio is "
            "unaffected, but the record can no longer say the ripper was jointly "
            "verified.\n\nSaved as soon as you click it. Leave this off unless you "
            "are testing."
        )
        self._offset_label: QLabel = QLabel("")
        self._offset_label.setTextFormat(Qt.TextFormat.PlainText)
        self._offset_label.setWordWrap(True)
        self._render_setup_standing(dependency_report)
        self.refresh_settings(config)
        self._app_beta_check.toggled.connect(
            lambda on: self._on_channel_toggled(
                "update_channel", self._app_beta_check, on
            )
        )
        self._ripper_beta_check.toggled.connect(
            lambda on: self._on_channel_toggled(
                "ripper_channel", self._ripper_beta_check, on
            )
        )

        grid = QGridLayout()
        # The status column takes the width; the buttons keep their own.
        grid.setColumnStretch(0, 1)
        layout.addLayout(grid)
        row = 0

        row = self._add_section(
            grid,
            row,
            title="Platterpus",
            status=f"{_OK} Version {app_version}",
            checkbox=self._app_beta_check,
            buttons=[("Check for &updates", "app_update")],
        )
        # The APPROVED build, which is a constant, not a probe. What is actually
        # installed is only knowable by entering the container, so the check
        # button is what answers that — stating the approved build here and the
        # installed one there keeps the two claims apart.
        #
        # In a user's words on the visible line: it read "Approved build: … from
        # handshake round 40", and a user has never been told what a handshake
        # round is (UX review of 0.7.127, W2). The round is kept, in the tooltip,
        # for the owner and for a bug report; the About dialog explains rounds.
        self._ripper_status_label: QLabel = QLabel(
            f"{_INFO} Tested build: {ripper_pin} ({ripper_version}), approved "
            "for this version of Platterpus"
        )
        self._ripper_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self._ripper_status_label.setWordWrap(True)
        self._ripper_status_label.setToolTip(
            plain_tooltip(
                f"Approved in handshake round {approved_by_round}: the joint test "
                "this version of Platterpus and the cyanrip fork both passed "
                "before release."
            )
        )
        row = self._add_section(
            grid,
            row,
            title="Ripper (cyanrip)",
            status_widget=self._ripper_status_label,
            checkbox=self._ripper_beta_check,
            buttons=[
                # Alt+C: Alt+U is the app's own update check, one section up.
                ("Check for &cyanrip updates", "ripper_update"),
                ("Choose a &build…", "ripper_pick"),
            ],
        )
        self._dependency_label = QLabel(dependency_summary_line(dependency_report))
        self._dependency_label.setTextFormat(Qt.TextFormat.PlainText)
        self._dependency_label.setWordWrap(True)
        row = self._add_section(
            grid,
            row,
            title="Dependencies",
            status_widget=self._dependency_label,
            buttons=[("Check &dependencies", "dep_check")],
        )
        row = self._add_section(
            grid,
            row,
            title="Drive",
            # What the next rip does with the offset: a value already in the
            # config, so reading it is free. The drive wizard edits it.
            status_widget=self._offset_label,
            buttons=[
                ("Set up d&rive…", "drive_setup"),
                # Moved here from the Tools menu (2026-09-24): one place for the
                # drive, instead of one item in each of two menus.
                ("Dia&gnose drive access…", "drive_diagnose"),
            ],
        )
        row = self._add_section(
            grid,
            row,
            title="Setup",
            status_widget=self._setup_label,
            buttons=[
                ("Run &setup…", "host_setup"),
                # Alt+T: Alt+S is "Run setup" beside it.
                ("Add app shor&tcut", "shortcut"),
            ],
        )

        # What the last tick-box click did, so a save (or a refusal) is seen and
        # heard rather than assumed.
        self._settings_status: QLabel = QLabel("")
        self._settings_status.setTextFormat(Qt.TextFormat.PlainText)
        self._settings_status.setWordWrap(True)
        self._settings_status.setAccessibleName("Setup and updates status")
        layout.addWidget(self._settings_status)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.rejected.connect(self.reject)
        root.addWidget(box)

    def _add_section(
        self,
        grid: QGridLayout,
        row: int,
        *,
        title: str,
        buttons: list[tuple[str, str]],
        status: str | None = None,
        status_widget: QLabel | None = None,
        checkbox: QCheckBox | None = None,
    ) -> int:
        """Lay out one section and return the next free row.

        Sections are uniform on purpose: a user scanning for "where do I check X"
        should not have to read four different layouts.
        """
        if row:
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            grid.addWidget(line, row, 0, 1, 2)
            row += 1

        heading = QLabel(title)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        font = heading.font()
        font.setBold(True)
        heading.setFont(font)
        grid.addWidget(heading, row, 0, 1, 2)
        row += 1

        if status_widget is None:
            status_widget = QLabel(status or "")
            status_widget.setTextFormat(Qt.TextFormat.PlainText)
            status_widget.setWordWrap(True)
        # ONE ROW PER ITEM: what it says on the left, what you can do about it on
        # the right (UX review L2). The status spans the rows of its section's
        # buttons, so a section with two buttons is still one item.
        grid.addWidget(
            status_widget, row, 0, max(1, len(buttons)), 1, Qt.AlignmentFlag.AlignTop
        )
        for offset, (label, key) in enumerate(buttons):
            button = QPushButton(label)
            # Qt's own height, which is the platform's, held to the floor; the
            # one button that commits gets the commit size (`_COMMITS`).
            button.setMinimumHeight(
                _COMMIT_HEIGHT if key in _COMMITS else _TARGET_FLOOR
            )
            button.clicked.connect(lambda _checked=False, k=key: self._run(k))
            self._buttons[key] = button
            self._button_labels[key] = label
            grid.addWidget(button, row + offset, 1, Qt.AlignmentFlag.AlignTop)
        row += max(1, len(buttons))

        if checkbox is not None:
            grid.addWidget(checkbox, row, 0, 1, 2)
            row += 1
        return row

    def _run(self, key: str) -> None:
        """Invoke the delegated action, never swallowing what it raises.

        A button that silently does nothing is the dead-menu-item shape this
        project forbids, and the likeliest cause here is a wiring mistake — a key
        with no action behind it — which must be loud rather than invisible.
        """
        action = self._actions.get(key)
        if action is None:
            log.error("Setup & Updates: no action wired for %r", key)
            return
        log.info("Setup & Updates: running %s", key)
        action()

    def set_locked(self, locked: bool) -> None:
        """Grey every action while a rip runs, and say why.

        The window's rip lock greys the menu item that OPENS this window; this is
        the half that reaches one already open. Every action is locked, as the
        menu item was, because each one either uses the drive, installs
        something, or replaces the app. The channel tick-boxes stay usable: they
        only decide what a later check offers.
        """
        self._locked = locked
        for key, button in self._buttons.items():
            button.setEnabled(
                not locked and not (key == "dep_check" and self._dep_check_busy)
            )
        if locked:
            self._settings_status.setText(
                f"{_INFO} Locked while a rip runs. The actions come back when it ends."
            )
        elif self._settings_status.text().startswith(f"{_INFO} Locked"):
            self._settings_status.setText("")
        self._grow_to_fit()

    def refresh_settings(self, config: Config) -> None:
        """Show ``config``'s channels and the selected drive's read offset.

        Called at construction and by the window whenever a setting this window
        displays changes elsewhere (a script's ``set``, a drive-wizard save), so
        the boxes never describe a channel the config no longer holds. Signals
        are blocked: re-rendering must not look like a click and save again.
        """
        for box, channel in (
            (self._app_beta_check, config.update_channel),
            (self._ripper_beta_check, config.ripper_channel),
        ):
            box.blockSignals(True)
            box.setChecked(channel == CHANNEL_BETA)
            box.blockSignals(False)
        decision = (
            self._drive_offset()
            if self._drive_offset is not None
            else offset_config.offset_for_drive(
                None,
                apply_offsets=config.override_read_offset,
                drive_selected=False,
            )
        )
        applied = offset_config.describe_applied_offset(decision)
        marker = _INFO if offset_config.is_offset_configured(decision) else _WARN
        offset_line = f"{marker} Read offset: {applied}"
        standing = self._drive_standing() if self._drive_standing is not None else ""
        self._offset_label.setText(
            f"{standing}\n{offset_line}" if standing else offset_line
        )
        self._grow_to_fit()

    def _render_setup_standing(self, report: object | None) -> None:
        """The Setup row: what setup does, or whether it has anything left to do."""
        what = (
            f"{_INFO} Installs the ripping tools in their container, adds the "
            "menu entry, and calibrates the drive."
        )
        if self._setup_standing is None:
            self._setup_label.setText(what)
            return
        self._setup_label.setText(self._setup_standing(report))

    def _on_channel_toggled(self, field: str, box: QCheckBox, beta: bool) -> None:
        """Save a channel tick-box through the window, and say what happened."""
        result = self._save_setting(field, CHANNEL_BETA if beta else CHANNEL_STABLE)
        what = "Platterpus" if field == "update_channel" else "cyanrip"
        if not result.applied:
            # Refused: put the box back, so it never shows a value not in force.
            box.blockSignals(True)
            box.setChecked(not beta)
            box.blockSignals(False)
            text = f"{_WARN} Not changed: {result.message}"
        elif beta:
            text = f"{_OK} Saved: beta {what} builds will be offered."
        else:
            text = f"{_OK} Saved: only stable {what} releases will be offered."
        if result.applied and result.message:
            text += f" {result.message}"
        self._settings_status.setText(text)
        announce(self._settings_status, text)
        self._grow_to_fit()

    def refresh_dependencies(self, report: object | None) -> None:
        """Re-render the dependency line after a check has reported.

        Called by the window when a probe lands, so the window this user opened
        to answer a question actually shows the answer rather than making them
        close and reopen it. (It was defined and never called until 2026-09-28:
        the line kept its opening text for as long as the window stayed open.)
        """
        if self._dependency_label is not None:
            text = dependency_summary_line(report)
            self._dependency_label.setText(text)
            announce(self._dependency_label, text)
        # Setup's line reads the same check, so it moves with it.
        self._render_setup_standing(report)
        self._grow_to_fit()

    def show_dependency_check_running(self, message: str, *, busy: bool) -> None:
        """A check is in flight: say so, and grey the button if the user asked.

        ``busy`` is True for a check the user started (or upgraded by a second
        click). A check nobody asked for — the launch check — leaves the button
        usable, because clicking it is how the user asks to see that check's
        result (`run_dependency_check_async` upgrades it rather than starting a
        second probe).
        """
        self._dep_check_busy = busy
        if self._dependency_label is not None:
            self._dependency_label.setText(f"{_INFO} {message}")
        self._apply_dep_check_button()
        self._grow_to_fit()

    def show_dependency_check_finished(
        self, report: object | None, *, failure: str = ""
    ) -> None:
        """The check landed: show its result and give the button back.

        ``failure`` is the sentence to show instead when the check itself crashed
        (``report`` is None then). Rendering None as the usual line would say
        "Not checked yet", which is untrue of a check that ran and failed.
        """
        self._dep_check_busy = False
        self._apply_dep_check_button()
        if failure and self._dependency_label is not None:
            self._dependency_label.setText(failure)
            announce(self._dependency_label, failure)
            self._grow_to_fit()
            return
        self.refresh_dependencies(report)

    def _grow_to_fit(self) -> None:
        """A status line changed: give the window the height its text now needs.

        **Why this window refits after it opens.** It is sized to its content on
        first show (`CenteredDialog`), and its lines change while it is open: a
        dependency check that lands can turn "Not checked yet" into a paragraph
        naming eight tools. With the status beside its buttons (UX review L2) that
        paragraph wraps in the narrower status column, and the body scrolled 60 px
        in a window that had the whole screen to grow into
        (`tests/test_ui_conformance.py`, *scrolls_only_when_capped*). The fit only
        ever GROWS the window and stops at the screen, so calling it again never
        shrinks a window the user made bigger; it is not called before the first
        show, which does the first fit itself.

        The body's layout is activated first. It is the top layout of a widget
        inside the scroll area, so the fit's own ``activate()`` (the dialog's
        layout) does not reach it, and until Qt's next event-loop turn it still
        answers with the height of the OLD text: measured on the conformance
        path, the fit then found nothing to grow and the body scrolled 60 px.
        """
        if not self.isVisible() or self.isMaximized():
            return
        body = self._body_scroll.widget()
        body_layout = body.layout() if body is not None else None
        if body_layout is not None:
            body_layout.activate()
        self._fit_content_to_screen()

    def _apply_dep_check_button(self) -> None:
        """Label and enable the dependency button from BOTH of its conditions."""
        button = self._buttons.get("dep_check")
        if button is None:
            return
        button.setText(
            _DEP_CHECK_BUSY_LABEL
            if self._dep_check_busy
            else self._button_labels["dep_check"]
        )
        button.setEnabled(not self._locked and not self._dep_check_busy)
