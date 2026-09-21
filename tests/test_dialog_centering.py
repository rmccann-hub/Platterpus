# ---------------------------------------------------------------------------
# WORD-WRAPPED PROSE NEEDS A WIDTH TO WRAP TO.
#
# A QLabel with setWordWrap(True) has a height-for-width policy, so with no width
# set Qt takes one from whatever else is in the layout — usually a QRadioButton
# or QCheckBox, whose label does NOT wrap. The dialog ends up as wide as its
# longest unwrappable line and the paragraphs reflow to that.
#
# Real-user report, 2026-09-21, on the cyanrip build picker: "window sizing is
# wrong." Eight of this app's twelve prose-carrying dialogs already set a width;
# four never had, and one of those four was added the same day this was reported.
# ---------------------------------------------------------------------------


def test_a_dialog_that_sets_no_width_still_gets_one(qapp) -> None:
    """The floor applies on first show, when there is finally something to measure."""
    from PySide6.QtWidgets import QLabel, QVBoxLayout

    from platterpus.ui.dialogs.centering import CenteredDialog

    dialog = CenteredDialog(None)
    layout = QVBoxLayout(dialog)
    label = QLabel("word wrapped prose " * 40)
    label.setWordWrap(True)
    layout.addWidget(label)

    assert dialog.minimumWidth() < CenteredDialog.DEFAULT_MINIMUM_WIDTH
    dialog.show()
    try:
        assert dialog.minimumWidth() >= CenteredDialog.DEFAULT_MINIMUM_WIDTH
    finally:
        dialog.close()


def test_a_dialog_that_CHOSE_a_width_keeps_it(qapp) -> None:
    """A floor for the ones that never thought about it, not a value imposed on
    the ones that did — otherwise every deliberately-narrow dialog silently
    widens, which is a regression wearing a fix's clothes."""
    from platterpus.ui.dialogs.centering import CenteredDialog

    chosen = CenteredDialog.DEFAULT_MINIMUM_WIDTH + 240
    dialog = CenteredDialog(None)
    dialog.setMinimumWidth(chosen)
    dialog.show()
    try:
        assert dialog.minimumWidth() == chosen
    finally:
        dialog.close()


def test_every_prose_carrying_dialog_resolves_to_a_width() -> None:
    """The sweep, so the next one cannot slip through.

    Source-level, because instantiating every dialog needs each one's
    collaborators. A dialog either sets a width itself or inherits the floor from
    `CenteredDialog` — what is refused is a `QDialog` carrying wrapped prose that
    does neither.
    """
    import re
    from pathlib import Path

    ui = Path(__file__).resolve().parent.parent / "src" / "platterpus" / "ui"
    offenders: list[str] = []
    examined = 0
    for path in sorted(ui.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "setWordWrap(True)" not in text:
            continue
        if not re.search(r"class \w+\((CenteredDialog|QDialog)\)", text):
            continue
        examined += 1
        sizes_itself = re.search(
            r"self\.(resize|setMinimumWidth|setMinimumSize|setFixedWidth|setFixedSize)\(",
            text,
        )
        # **Per CLASS, not per file.** `"CenteredDialog" in text` was the first
        # version and it is satisfied by an import — so a class declared
        # `(QDialog)` in a file that merely mentions the base would have passed.
        # A check that can be satisfied by the wrong thing is the shape this repo
        # names; ask what each class actually inherits.
        bases = set(re.findall(r"class \w+\((CenteredDialog|QDialog)\)", text))
        inherits_the_floor = bases == {"CenteredDialog"}
        if not (sizes_itself or inherits_the_floor):
            offenders.append(f"{path.name} (bases: {sorted(bases)})")

    assert examined >= 8, (
        f"only {examined} prose-carrying dialog(s) examined — the pattern has "
        "stopped matching and this sweep is measuring nothing"
    )
    assert not offenders, (
        "these dialogs carry word-wrapped prose with no width, so Qt sizes them "
        f"from their longest unwrappable line: {offenders}"
    )
