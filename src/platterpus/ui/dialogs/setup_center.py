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
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea
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

#: The status marker vocabulary. **Never colour alone** — around 8% of men have
#: red/green colour-vision deficiency, and a greyscale screenshot or a
#: forced-colors theme drops hue entirely, so every level carries a glyph.
_OK: str = "✓"
_WARN: str = "⚠"
_INFO: str = "ⓘ"


def dependency_summary_line(report: object | None) -> str:
    """One line describing the last dependency probe, for a person.

    Pure, and separated from the widget so it can be tested without a display —
    the same split the rest of this project makes between what a value *is* and
    how it is drawn.

    **Tri-state, like every other verdict here.** "We have not looked yet" is a
    real answer and must not render as "nothing is wrong": a window that says
    `✓ All present` before any probe has run would be asserting something it
    cannot know, which is the failure mode this project keeps a marker
    vocabulary for.
    """
    if report is None:
        return f"{_INFO} Not checked yet in this session."
    missing = list(getattr(report, "missing", []) or [])
    required = [
        m for m in missing if not getattr(getattr(m, "spec", None), "optional", False)
    ]
    optional = [
        m for m in missing if getattr(getattr(m, "spec", None), "optional", False)
    ]
    if required:
        names = ", ".join(str(getattr(m, "name", "?")) for m in required)
        return f"{_WARN} {len(required)} required missing: {names}"
    if optional:
        names = ", ".join(str(getattr(m, "name", "?")) for m in optional)
        return f"{_OK} All required tools present. Optional not installed: {names}"
    return f"{_OK} All required tools present."


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
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Setup & Updates")
        # NOT modal — see the module docstring. Its buttons open modal dialogs,
        # and a modal parent would nest every one of them inside this window's
        # event loop.
        self.setModal(False)

        self._actions: dict[str, Callable[[], object]] = actions
        self._save_setting: Callable[[str, object], SettingWrite] = save_setting
        self._dependency_label: QLabel | None = None
        #: Every action button, so a rip can lock them all (`set_locked`).
        self._buttons: dict[str, QPushButton] = {}

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
            "from a closed handshake round.\n\nThis never installs anything: it "
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
        row = self._add_section(
            grid,
            row,
            title="Ripper (cyanrip)",
            # The APPROVED build, which is a constant, not a probe. What is
            # actually installed is only knowable by entering the container, so
            # the check button is what answers that — stating the approved build
            # here and the installed one there keeps the two claims apart.
            status=(
                f"{_INFO} Approved build: {ripper_pin} ({ripper_version}), "
                f"from handshake round {approved_by_round}"
            ),
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
            status=(
                f"{_INFO} Installs the ripping tools in their container, adds the "
                "menu entry, and calibrates the drive."
            ),
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
        grid.addWidget(status_widget, row, 0, 1, 2)
        row += 1

        if checkbox is not None:
            grid.addWidget(checkbox, row, 0, 1, 2)
            row += 1

        for label, key in buttons:
            button = QPushButton(label)
            button.setMinimumHeight(_COMMIT_HEIGHT)
            button.clicked.connect(lambda _checked=False, k=key: self._run(k))
            self._buttons[key] = button
            grid.addWidget(button, row, 0, 1, 2)
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
        for button in self._buttons.values():
            button.setEnabled(not locked)
        if locked:
            self._settings_status.setText(
                f"{_INFO} Locked while a rip runs. The actions come back when it ends."
            )
        elif self._settings_status.text().startswith(f"{_INFO} Locked"):
            self._settings_status.setText("")

    def refresh_settings(self, config: Config) -> None:
        """Show ``config``'s channels and read offset. Changes nothing.

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
        applied = offset_config.describe_applied_offset(
            config.read_offset, config.override_read_offset
        )
        marker = _INFO if config.override_read_offset else _WARN
        self._offset_label.setText(f"{marker} Read offset: {applied}")

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

    def refresh_dependencies(self, report: object | None) -> None:
        """Re-render the dependency line after a check has reported.

        Called by the window when a probe lands, so the window this user opened
        to answer a question actually shows the answer rather than making them
        close and reopen it.
        """
        if self._dependency_label is not None:
            self._dependency_label.setText(dependency_summary_line(report))
