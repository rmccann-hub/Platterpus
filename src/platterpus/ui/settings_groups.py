"""Settings in four headed groups, and the mark on the rows a Goal sets.

**Why this module exists** (TASKS R180; the end-user UX review of 0.7.127,
findings S1, S2 and L3). Settings was one form of 33 rows: the Goal, the naming
templates, the read offset, the ``metaflac`` path, the output format, Picard, the
read speed and the CTDB boxes all sat in a single column, so a user looking for
one option read past every other one. The review asked for groups, and for the
rows a Goal preset changes to be marked, because picking a Goal changed seven
rows and nothing on screen said which.

So the dialog's rows now sit under four headings, each with one sentence saying
what the group is for:

* **Output**: where finished rips go, what they are called, what each holds.
* **Accuracy**: how the disc is read and checked.
* **After a rip**: what happens once the disc is read.
* **Advanced**: the raw templates, tool paths and the options for unusual
  drives, which most people never change.

**Headed sections, not tabs.** A tab hides the rows it does not show, and the
Goal changes rows in two groups at once (the output format in *Output*, the
re-reads in *Accuracy*): with tabs, a user would pick a Goal and see none of
what it changed. One scrolling page with headings keeps every changed row
findable by scrolling, and keeps every control a child of the same page, so
the dialog's tests and script verbs reach them exactly as before.

This module only lays the groups out and answers questions about them; the
dialog still builds every row itself, with the same ``form.addRow`` calls the
User Guide and tooltip sweeps read from its source. Pure layout on the GUI
thread: nothing here blocks.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from platterpus import goal_presets
from platterpus.config import Config
from platterpus.ui.status_colours import SECONDARY_STYLE

log: logging.Logger = logging.getLogger(__name__)

#: Group keys, in the order they appear on the page.
OUTPUT: Final[str] = "output"
ACCURACY: Final[str] = "accuracy"
AFTER_RIP: Final[str] = "after_rip"
ADVANCED: Final[str] = "advanced"

#: ``(key, heading, sentence)`` for each group, top to bottom. The sentence says
#: what the group is FOR, so a user can skip a group without reading its rows.
GROUPS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        OUTPUT,
        "Output",
        "Where finished rips go, what they are called, and what each one holds.",
    ),
    (
        ACCURACY,
        "Accuracy",
        "How the disc is read and checked. These decide whether a rip is "
        "bit-perfect, and whether you can prove it.",
    ),
    (
        AFTER_RIP,
        "After a rip",
        "What happens once the disc has been read: where the album is moved, "
        "and how you hear that it finished.",
    ),
    (
        ADVANCED,
        "Advanced",
        "The raw naming templates, tool paths and options for unusual drives "
        "or bug reports. Most people never need to change these.",
    ),
)

#: The mark before the label of every row a Goal sets. A shape, not a colour
#: (CLAUDE.md, accessibility rule 1), and one that no other line in the app uses,
#: so it cannot be read as a status.
GOAL_MARK: Final[str] = "◆"

#: The line under the Goal while it names a preset, and the end of the line once
#: it says Custom. It explains the mark where the mark is first seen.
GOAL_KEY_TEXT: Final[str] = (
    f"{GOAL_MARK} marks the options a goal sets. "
    "Change one and the goal becomes Custom."
)

#: The name the Custom line gives each field a Goal sets: the row's own label
#: where it has one, and a short form of its checkbox where it has none.
#: ``tests/test_goal_presets.py`` holds the keys to ``GoalPreset``'s fields, so a
#: field added to the presets cannot reach this line unnamed.
GOAL_FIELD_NAMES: Final[dict[str, str]] = {
    "output_format": "Output format",
    "ctdb_verify_after_rip": "CTDB",
    "verify_flac_after_rip": "Verify FLACs",
    "secure_rerip_matches": "Extra matching reads to trust a track",
    "secure_rerip_dynamic": "Verify every track",
    "rerip_offset_variant": "Re-read one-frame matches",
    "read_speed_mode": "Read speed",
}


def preset_name(goal: str) -> str:
    """The short name of a goal, the part of its combo label before the dash."""
    for key, label in goal_presets.GOAL_LABELS:
        if key == goal:
            return label.split(" — ", 1)[0]
    return goal


def _joined(names: list[str]) -> str:
    """``a``, ``a and b``, ``a, b and c``: a list as a sentence says it."""
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def goal_status_text(goal: str, config: Config) -> str:
    """The line under the Goal: the key to the mark, and why a goal is Custom.

    ``config`` is what the dialog's controls hold now. A Custom goal names the
    preset the controls are nearest to and each option that differs from it,
    so the user can see what to change back, or that nothing needs to.
    """
    if goal != goal_presets.GOAL_CUSTOM:
        return GOAL_KEY_TEXT
    nearest = goal_presets.nearest_preset(config)
    differing = [
        GOAL_FIELD_NAMES.get(field, field)
        for field in goal_presets.fields_differing(config, nearest)
    ]
    name = preset_name(nearest)
    if not differing:
        return (
            f"ⓘ Custom: every option a goal sets still matches {name}. {GOAL_KEY_TEXT}"
        )
    verb = "differs" if len(differing) == 1 else "differ"
    return f"ⓘ Custom: {_joined(differing)} {verb} from {name}. {GOAL_KEY_TEXT}"


def form_row(form: QFormLayout, widget: QWidget) -> int | None:
    """The row ``widget`` sits in on ``form``, or None when it is not there.

    PySide6's stub types ``QFormLayout.getWidgetPosition`` as returning
    ``object`` (PySide6 6.11.1), where Qt returns ``(row, role)`` with row -1
    for a widget the form does not hold. The answer is checked here, once,
    rather than cast: a cast would be a weaker type claimed to satisfy the
    checker (CLAUDE.md rule #10), and a shape we did not expect would then
    become a wrong row instead of no row.
    """
    position: object = form.getWidgetPosition(widget)
    if not isinstance(position, tuple) or len(position) != 2:
        log.warning("settings: unexpected form position %r", position)
        return None
    row = position[0]
    if not isinstance(row, int) or row < 0:
        return None
    return row


class SettingsGroups:
    """The four headed groups on the Settings page, and questions about them.

    Built into ``host``, the layout of the page inside the dialog's scroll
    area. Each group is a bold heading, its sentence in italics, and a
    ``QFormLayout`` the dialog adds its rows to through :meth:`form`.
    """

    def __init__(self, host: QVBoxLayout, parent: QWidget) -> None:
        self._forms: dict[str, QFormLayout] = {}
        self._headings: dict[str, QLabel] = {}
        for index, (key, heading, sentence) in enumerate(GROUPS):
            if index:
                # Space above each heading after the first, so a group reads as
                # starting there rather than as one more row of the last one.
                host.addSpacing(parent.fontMetrics().height())
            title = QLabel(heading, parent)
            title.setTextFormat(Qt.TextFormat.PlainText)
            font = title.font()
            font.setBold(True)
            title.setFont(font)
            title.setAccessibleName(f"{heading} settings")
            note = QLabel(sentence, parent)
            note.setTextFormat(Qt.TextFormat.PlainText)
            note.setWordWrap(True)
            note.setStyleSheet(SECONDARY_STYLE)
            form = new_form()
            host.addWidget(title)
            host.addWidget(note)
            host.addLayout(form)
            self._forms[key] = form
            self._headings[key] = title

    def form(self, key: str) -> QFormLayout:
        """The form the group ``key`` adds its rows to."""
        return self._forms[key]

    def heading(self, key: str) -> QLabel:
        """The group's heading label (screenshots and tests scroll to it)."""
        return self._headings[key]

    def section_of(self, widget: QWidget) -> str | None:
        """Which group a control is in, or None when it is in none.

        Walks up from ``widget``, because a control in a composite row (a path
        box beside its Browse button) is a child of the row the form holds, not
        a row itself.
        """
        current: QWidget | None = widget
        while current is not None:
            for key, form in self._forms.items():
                if form_row(form, current) is not None:
                    return key
            current = current.parentWidget()
        return None

    def mark_goal_rows(self, widgets: Iterable[QWidget]) -> list[QWidget]:
        """Put :data:`GOAL_MARK` before the label of each of ``widgets``' rows.

        A row with a label gets the mark at the start of it. A checkbox row has
        no label (its text is on the box), so the mark goes at the start of the
        box's own text: a mark alone in the label column sat on a line of its
        own above the box once a narrow window wrapped the rows (the owner's
        screenshots of 2026-11-23). Each marked control's accessible
        description says so too, since a screen reader reads the control rather
        than the column beside it. Returns the widgets carrying the mark. Safe
        to call twice: a marked label or box is not marked again.
        """
        marked: list[QWidget] = []
        for widget in widgets:
            key = self.section_of(widget)
            if key is None:
                log.warning("settings: %s is in no group", widget.objectName())
                continue
            form = self._forms[key]
            row = _row_holding(form, widget)
            if row is None:
                continue
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            old = item.widget() if item is not None else None
            if old is None and isinstance(widget, QCheckBox):
                # No label column to mark: the mark leads the box's own text.
                _lead_with_goal_mark(widget)
                widget.setAccessibleDescription("A goal sets this option.")
                marked.append(widget)
                continue
            text = old.text() if isinstance(old, QLabel) else ""
            if isinstance(old, QLabel) and text.startswith(GOAL_MARK):
                marked.append(old)
                continue
            # A new label rather than `setText` on the one `addRow` made: that
            # one was built by Qt with Qt's own format guess, and every label
            # here states its format where it is built (PlainText: the text is
            # ours, but a `<` in a future label must show as a `<`).
            if old is not None:
                form.removeWidget(old)
                old.hide()
                old.deleteLater()
            mark = QLabel(f"{GOAL_MARK} {text}".strip(), form.parentWidget())
            mark.setTextFormat(Qt.TextFormat.PlainText)
            # The label `addRow` made was the field's buddy; keep that, so the
            # label still names the control it sits beside.
            mark.setBuddy(widget)
            form.setWidget(row, QFormLayout.ItemRole.LabelRole, mark)
            widget.setAccessibleDescription("A goal sets this option.")
            marked.append(mark)
        return marked


def _lead_with_goal_mark(box: QCheckBox) -> None:
    """Put :data:`GOAL_MARK` at the start of a checkbox's own text, once.

    A checkbox shows its text as written (it is not a label, so no format is
    guessed), and its parameter is annotated so the label-format sweep can see
    that. Safe to call twice: a box already marked is left as it is.
    """
    if not box.text().startswith(GOAL_MARK):
        box.setText(f"{GOAL_MARK} {box.text()}")


def _row_holding(form: QFormLayout, widget: QWidget) -> int | None:
    """The form row holding ``widget`` itself or the composite row around it."""
    current: QWidget | None = widget
    while current is not None:
        row = form_row(form, current)
        if row is not None:
            return row
        current = current.parentWidget()
    return None


def new_form() -> QFormLayout:
    """A form that wraps a long row under its label instead of scrolling sideways.

    The review's L3: at a narrow width the page scrolled horizontally, because
    a form's minimum width is its widest label plus its widest field side by
    side. ``WrapLongRows`` puts the field under its label when the two do not
    fit together, and fields grow to the width they are given.
    """
    form = QFormLayout()
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    return form
