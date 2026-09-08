"""The GUI build picker — the caller `--install-ripper list` never had.

Every assertion here is about a *relation* between two surfaces, because the
defects this dialog closes were all of that shape: the terminal knew which build
an acceptance run needed and the GUI had no way to install it, and three
expressions independently decided *"which build?"* until two of them disagreed
in one day.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from platterpus.deps import fork_source
from platterpus.ui.ripper_picker import RipperPickerDialog


@pytest.fixture
def picker(qapp: QApplication) -> RipperPickerDialog:
    del qapp
    return RipperPickerDialog()


def test_the_picker_offers_exactly_what_the_cli_lists(
    picker: RipperPickerDialog,
) -> None:
    """**The relation, and the whole reason this file exists.**

    `--install-ripper list` and this dialog answer one question, so they read one
    function. A GUI list that drifted from the CLI's would send an operator to a
    build the acceptance script refuses — which is the abort that has ended an
    overnight run three times, arriving through a new door.
    """
    offered = [pin for _button, pin in picker._buttons]
    listed = [choice.pin for choice in fork_source.ripper_choices()]
    assert offered == listed, (
        f"the GUI picker and --install-ripper list disagree: {offered} vs {listed}"
    )
    assert len(offered) >= 2, (
        f"only {len(offered)} build(s) offered — a picker with one row cannot "
        "exercise the pre-selection below, so this file would assert nothing"
    )


def test_the_preselected_build_is_the_one_the_rig_needs(
    picker: RipperPickerDialog,
) -> None:
    """Pre-selection is `pin_the_rig_should_install()`, not a position.

    Round 16 is the first round to name a test pin DISTINCT from the pin under
    review, and both other surfaces that answer this got it wrong that week: the
    menu's own reason line called the reviewed pin mandatory, and the acceptance
    script's abort message told an operator to install it. One function decides
    it now, and this asserts the dialog uses that function rather than, say,
    defaulting to the last row.
    """
    checked = [pin for button, pin in picker._buttons if button.isChecked()]
    assert len(checked) == 1, f"expected exactly one pre-selected row, got {checked}"
    assert fork_source.same_commit(
        checked[0], fork_source.pin_the_rig_should_install()
    ), (
        f"the picker pre-selects {checked[0]} but the rig needs "
        f"{fork_source.pin_the_rig_should_install()}"
    )


def test_the_preselected_build_is_one_the_acceptance_script_ACCEPTS(
    picker: RipperPickerDialog,
) -> None:
    """The end-to-end relation: pick the default, and section A must pass.

    `expect-ripper-under-review` accepts the reviewed pin or the agreed test pin.
    A picker whose default is neither would hand an operator a four-second abort
    *after* they had done the clicking — the exact experience this dialog was
    written to remove, with the terminal step deleted and the failure kept.
    """
    checked = next(pin for button, pin in picker._buttons if button.isChecked())
    accepted = {fork_source.PIN_UNDER_REVIEW, fork_source.FORK_TEST_PIN}
    assert any(fork_source.same_commit(checked, pin) for pin in accepted), (
        f"the default {checked} is not one section A accepts ({sorted(accepted)})"
    )


def test_cancelling_installs_nothing(qapp: QApplication) -> None:
    """Empty is a real answer.

    Falling back to `WIZARD_TARGET` on cancel would install a build the user did
    not ask for — a worse outcome than the terminal command this replaces, which
    at least could not run without being typed.
    """
    del qapp
    assert RipperPickerDialog().chosen_pin() == ""


def test_choosing_a_row_returns_that_row(picker: RipperPickerDialog) -> None:
    """Non-triviality floor for the two tests above: the dialog must actually
    read the buttons, not return its default whatever is checked."""
    other = next(pin for button, pin in picker._buttons if not button.isChecked())
    for button, pin in picker._buttons:
        button.setChecked(pin == other)
    picker._accept_choice()
    assert picker.chosen_pin() == other


def test_every_label_carrying_a_reason_is_PlainText(
    picker: RipperPickerDialog,
) -> None:
    """The inbound-seam rule, applied so this file does not become a 14th
    unswept `QLabel` site.

    Qt's default `AutoText` auto-detects HTML, so a `<` in any of this text is
    swallowed as an unknown tag and the reader never learns text went missing.
    The strings are our own constants today; the rule is about the widget, and
    `TASKS.md` already tracks 13 sites that were left to be judged individually.
    """
    labels = picker.findChildren(QLabel)
    assert labels, "no labels found — this sweep would pass by finding nothing"
    for label in labels:
        assert label.textFormat() == Qt.TextFormat.PlainText, (
            f"a label is not PlainText: {label.text()[:60]!r}"
        )


def test_the_unapproved_expectation_is_stated_once(
    picker: RipperPickerDialog,
) -> None:
    """An operator who meets a column of `unapproved` verdicts unwarned stops a
    run that was working. The dialog says so before the install, which is the
    honest place — a surprise in a rip report reads as a defect."""
    text = " ".join(label.text() for label in picker.findChildren(QLabel))
    assert "unapproved" in text
    assert "not a fault" in text
