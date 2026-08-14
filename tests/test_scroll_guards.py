"""The two scrolling rules, and proof each one is doing something.

Both were reported by the maintainer on 2026-08-13 after using the app:

    "the scroll bars on the run test script window are all off and reset, i
    think they should either keep scrolling if at the bottom, or stay where
    there they are if manually put there"

    "the scrolling on the settings page i have accidentially scrolled down on
    options i did not mean to"

**The wheel one is not cosmetic.** Qt's default is that a spin box under the
pointer swallows the wheel and increments *itself*, so scrolling the Settings
page past a control edits it. Most of those controls are calibration that
reaches cyanrip's argv — a nudged `read_offset` rips the **next disc at the
wrong offset**, with no error, no warning, and a clean-looking log. That is the
same class as every other silent-wrong-answer defect this project keeps finding,
which is why it is tested like one rather than eyeballed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QComboBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from platterpus.ui.scroll_guards import (  # noqa: E402
    append_keeping_position,
    protect_value_widgets,
)


def _wheel(widget: QWidget, *, down: bool = True) -> QWheelEvent:
    """A wheel event of the shape Qt delivers from a real mouse."""
    delta = -120 if down else 120
    return QWheelEvent(
        QPointF(widget.rect().center()),
        QPointF(widget.mapToGlobal(widget.rect().center())),
        QPoint(0, delta),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


class TestAScrollGestureNeverChangesAValue:
    def test_an_unfocused_spin_box_ignores_the_wheel(self, qapp) -> None:
        """The reported bug, inverted."""
        host = QWidget()
        spin = QSpinBox(host)
        spin.setRange(-2000, 2000)
        spin.setValue(667)  # the read offset, which is the case that matters
        guard = protect_value_widgets(host)
        assert guard is not None

        QApplication.sendEvent(spin, _wheel(spin))
        assert spin.value() == 667, (
            "scrolling past the read offset changed it — the next disc would be "
            "ripped at the wrong offset and the log would look perfectly normal"
        )
        host.deleteLater()

    def test_a_focused_spin_box_still_adjusts(self, qapp) -> None:
        """The non-triviality floor. A guard that blocked the wheel *always*
        would pass the test above and break deliberate editing — so this asserts
        the value DOES move once the user has chosen the widget."""
        host = QWidget()
        host.show()
        spin = QSpinBox(host)
        spin.setRange(0, 100)
        spin.setValue(50)
        protect_value_widgets(host)
        spin.setFocus()
        qapp.processEvents()
        if not spin.hasFocus():
            pytest.skip("no focus in this headless session; the branch is untestable")

        QApplication.sendEvent(spin, _wheel(spin))
        assert spin.value() != 50, "a focused spin box must still be adjustable"
        host.close()
        host.deleteLater()

    def test_a_combo_box_is_covered_too(self, qapp) -> None:
        """Settings has ten of these between spin boxes and combos; the guard is
        applied by type, not by naming each one."""
        host = QWidget()
        combo = QComboBox(host)
        combo.addItems(["flac", "wavpack", "mp3", "wav"])
        combo.setCurrentIndex(0)
        protect_value_widgets(host)

        QApplication.sendEvent(combo, _wheel(combo))
        assert combo.currentIndex() == 0, "scrolling past changed the output format"
        host.deleteLater()

    def test_without_the_guard_the_value_does_move(self, qapp) -> None:
        """**The revert-proof, and the reason this file exists.**

        If Qt did not actually steal the wheel, every test above would pass on a
        no-op guard. This one drives the same event at an *unguarded* spin box
        and requires the value to change — so the guard is measured against the
        real behaviour rather than against an assumption about it.
        """
        host = QWidget()
        spin = QSpinBox(host)
        spin.setRange(0, 100)
        spin.setValue(50)
        # deliberately NOT guarded
        QApplication.sendEvent(spin, _wheel(spin))
        assert spin.value() != 50, (
            "Qt did not steal the wheel here, so the guard's tests prove nothing "
            "— re-check the event shape before trusting them"
        )
        host.deleteLater()

    def test_the_guard_reaches_widgets_nested_in_layouts(self, qapp) -> None:
        """Settings puts its controls inside a form inside a scroll area, so a
        sweep that only looked at direct children would protect nothing."""
        root = QWidget()
        outer = QVBoxLayout(root)
        middle = QWidget(root)
        outer.addWidget(middle)
        inner = QVBoxLayout(middle)
        spin = QSpinBox(middle)
        spin.setRange(0, 100)
        spin.setValue(7)
        inner.addWidget(spin)

        protect_value_widgets(root)
        QApplication.sendEvent(spin, _wheel(spin))
        assert spin.value() == 7, "the sweep did not reach a nested control"
        root.deleteLater()


class TestALogPaneDoesNotYankYouBack:
    def _filled(self, qapp) -> QPlainTextEdit:
        view = QPlainTextEdit()
        view.resize(300, 80)
        view.setPlainText("\n".join(f"line {n}" for n in range(200)))
        qapp.processEvents()
        return view

    def test_scrolled_up_stays_put(self, qapp) -> None:
        view = self._filled(qapp)
        bar = view.verticalScrollBar()
        bar.setValue(bar.maximum() // 3)
        parked = bar.value()
        assert parked < bar.maximum(), "the fixture is already at the bottom"

        append_keeping_position(view, "a new step arrived")

        assert bar.value() == parked, (
            "appending dragged the view away from where the reader parked it"
        )
        view.deleteLater()

    def test_at_the_bottom_it_follows(self, qapp) -> None:
        """The other half — a run you are watching live must keep streaming."""
        view = self._filled(qapp)
        bar = view.verticalScrollBar()
        bar.setValue(bar.maximum())

        append_keeping_position(view, "a new step arrived")

        assert bar.value() == bar.maximum(), (
            "the view stopped following the tail while parked at the bottom"
        )
        view.deleteLater()

    def test_the_text_actually_arrives_either_way(self, qapp) -> None:
        """Non-triviality: a helper that scrolled correctly and appended nothing
        would satisfy both tests above."""
        view = self._filled(qapp)
        bar = view.verticalScrollBar()
        bar.setValue(0)
        append_keeping_position(view, "MARKER-ONE")
        bar.setValue(bar.maximum())
        append_keeping_position(view, "MARKER-TWO")
        text = view.toPlainText()
        assert "MARKER-ONE" in text and "MARKER-TWO" in text
        view.deleteLater()


class TestItIsActuallyWiredIn:
    """A guard nothing installs is the defect this project has shipped three
    times (`CLAUDE.md`). Both call sites are checked, not assumed."""

    def test_the_settings_dialog_installs_the_wheel_guard(self, qapp) -> None:
        import inspect

        from platterpus.ui.settings_dialog import SettingsDialog

        src = inspect.getsource(SettingsDialog.__init__)
        assert "protect_value_widgets" in src, (
            "Settings does not install the wheel guard — the reported bug is back"
        )
        assert "self._wheel_guard" in src, (
            "the guard is not retained; an event filter whose last Python "
            "reference is dropped stops filtering, silently"
        )

    def test_the_script_console_appends_stickily(self, qapp) -> None:
        import inspect

        from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

        src = inspect.getsource(ScriptConsoleDialog._append)
        assert "append_keeping_position" in src
        assert "appendPlainText" not in src, (
            "the console still appends directly, which always scrolls to the end"
        )
