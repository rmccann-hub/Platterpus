"""Pick which cyanrip build to install — the GUI half of ``--install-ripper``.

**Why this file exists, and why it is only a picker.** `--install-ripper list`
has printed the installable builds since the flag was written, and the acceptance
script's own header sends an operator to that terminal command when a handshake
round is open on a build the fork never published — the case where the in-app
update check can only answer *"your build is current"*, because it reads the
fork's **release manifest** and an unreleased commit is not in it. That header
carried a parenthetical admitting the gap: *"the menu has no GUI caller yet. That
is a real gap of ours, filed in TASKS.md, and it is the reason this paragraph
exists instead of a second click."* We wrote the excuse into the operator
instructions and left it there for a round.

The maintainer's standard is zero-terminal for anything the software can do
(KDD-17), and the directive of 2026-08-11 is sharper: *"i should never get an
instruction file again"* — a manual step is work handed back, and a symptom
rather than a deliverable. On 2026-09-08 the answer to *"what is the procedure?"*
still opened with a command to paste, so this closes that half of it.

**It installs nothing itself.** `MainWindowUpdateMixin._begin_ripper_install`
already builds any commit through `HostSetupDialog`, which runs the whole
pipeline on `HostSetupWorker`'s thread — git, meson, ninja, `sudo install`,
`distrobox-export`, minutes of it. That is the dialog `CLAUDE.md` names as *"the
one that already avoids"* the modal-does-its-own-blocking-work trap, and rule #6
puts every dependency install in one subsystem. So this dialog's whole job is to
return a commit, and a caller hands it to the path that already exists. A second
install route would drift the first time a build dependency changed, and would
drift **silently**, because both would still produce a working binary most of the
time.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from platterpus.deps import fork_source
from platterpus.ui.dialogs.centering import CenteredDialog

#: Minimum height for anything that commits an action, per the accessibility
#: convention in `CLAUDE.md` (44 px for a control that commits, 24 px floor
#: otherwise). An explicit size is a size you own: Qt's platform default is the
#: user-agent exception, and setting one forfeits it.
_COMMIT_HEIGHT: int = 44


class RipperPickerDialog(CenteredDialog):
    """Choose one of the builds this Platterpus knows how to install.

    The rows come from :func:`~platterpus.deps.fork_source.ripper_choices`, which
    is the same function ``--install-ripper list`` prints — not a second list.
    The pre-selected row is :func:`fork_source.pin_the_rig_should_install`, which
    is the same predicate the acceptance script's abort message uses, for the
    same reason: three surfaces answering *"which build?"* from three expressions
    is how two of them came to disagree in one day.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Install a cyanrip build")
        self._chosen: str = ""
        self._buttons: list[tuple[QRadioButton, str]] = []

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Platterpus builds cyanrip from source inside its container. Pick the "
            "build you want; the install is verified before anything is replaced, "
            "so if the binary does not identify as the build you asked for, your "
            "current ripper keeps working."
        )
        intro.setWordWrap(True)
        # PlainText, always. The inbound-seam rule in `CLAUDE.md`: Qt's default
        # `AutoText` auto-detects HTML, so a `<` anywhere in this text would be
        # swallowed as an unknown tag and the reader would never learn text went
        # missing. These strings are ours today; the rule is about the widget.
        intro.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(intro)

        wanted = fork_source.pin_the_rig_should_install()
        for choice in fork_source.ripper_choices():
            button = QRadioButton(choice.label)
            button.setMinimumHeight(_COMMIT_HEIGHT)
            # The accessible name carries the REASON as well as the label,
            # because a screen-reader user hearing only
            # "approved: 978f9b0 (platterpus-fork-g978f9b0)" has the identity and
            # none of the standing, and the standing is the whole decision.
            button.setAccessibleName(f"{choice.label} — {choice.why}")
            if fork_source.same_commit(choice.pin, wanted):
                button.setChecked(True)
            layout.addWidget(button)

            why = QLabel(choice.why)
            why.setWordWrap(True)
            why.setTextFormat(Qt.TextFormat.PlainText)
            # Indented under its own radio button so the reason reads as
            # belonging to that choice rather than to the next one.
            why.setContentsMargins(28, 0, 0, 8)
            layout.addWidget(why)
            self._buttons.append((button, choice.pin))

        # Said once, here, rather than repeated per row: every non-approved build
        # reports `unapproved` on every rip, and that is the record being honest
        # about an open round rather than a fault. An operator who meets a column
        # of those in a report and was not told to expect them stops the run.
        note = QLabel(
            "A build no handshake round has approved reports "
            "'ripper handshake approval: unapproved' on every rip. That is "
            "correct, not a fault — it is what a test session exists to change."
        )
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(note)

        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        install = box.button(QDialogButtonBox.StandardButton.Ok)
        install.setText("&Install")
        install.setMinimumHeight(_COMMIT_HEIGHT)
        install.setAccessibleName("Install the selected cyanrip build")
        box.accepted.connect(self._accept_choice)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def _accept_choice(self) -> None:
        """Record the checked pin, then accept.

        Reads the buttons rather than tracking a "current" field on every toggle:
        one source of truth at the moment it is needed, and no state to get out
        of step with the widgets.
        """
        for button, pin in self._buttons:
            if button.isChecked():
                self._chosen = pin
                break
        self.accept()

    def chosen_pin(self) -> str:
        """The commit the user chose, or ``""`` if they cancelled.

        Empty is a real answer and callers must treat it as one — installing
        `WIZARD_TARGET` because the picker returned nothing would install a build
        the user did not ask for, which is the failure mode the whole dialog
        exists to remove.
        """
        return self._chosen
