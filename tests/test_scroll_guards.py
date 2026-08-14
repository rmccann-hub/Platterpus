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

import re
from pathlib import Path

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


class TestTheRuleIsAppliedEverywhere:
    """The sweep, modelled on `test_qthread_ownership.py`.

    The first pass of this fix guarded Settings and the script console, because
    those were the two the maintainer happened to be looking at. That is exactly
    the failure `CLAUDE.md` names — *enforce a rule across the codebase, not at
    the place it was learned* — and it left the **read-offset spin box** in the
    drive-setup dialog unguarded, which is the single control the rule was
    written for.

    So: derive the population from the source, and require the guard. Both
    allowlists below are ratchets with a written reason per entry; they may
    shrink, never grow.
    """

    #: Modules that build a value widget but deliberately do not install the
    #: wheel guard. Empty, and it should stay that way — an entry here needs a
    #: reason good enough to accept that scrolling can edit the value.
    WHEEL_GUARD_EXEMPT: dict[str, str] = {}

    #: Modules allowed to append to a text view directly. One entry, and it is
    #: an exception because its own mechanism is *stronger* — see the note in
    #: `ui/scroll_guards.py`.
    STICKY_APPEND_EXEMPT: dict[str, str] = {
        "rip_progress.py": (
            "tracks follow-state across appends and re-pins on tab-show; its "
            "pane sits in a non-current tab where Qt leaves maximum() stale, "
            "so the per-append question this helper asks cannot be answered "
            "there. Unifying would restore the 2026-08-06 stale-pane bug."
        ),
    }

    def _ui_modules(self) -> list[Path]:
        from platterpus import ui

        return sorted(Path(ui.__file__).parent.rglob("*.py"))

    def test_every_module_with_a_value_widget_installs_the_guard(self) -> None:
        constructs = re.compile(
            r"\bQ(?:Spin|DoubleSpin|Combo|Slider|Dial|DateTime|Date|Time)"
            r"(?:Box|Edit)?\s*\("
        )
        offenders: list[str] = []
        examined = 0
        for path in self._ui_modules():
            if path.name == "scroll_guards.py":
                continue
            text = path.read_text(encoding="utf-8")
            if not constructs.search(text):
                continue
            examined += 1
            if path.name in self.WHEEL_GUARD_EXEMPT:
                continue
            if "protect_value_widgets" not in text:
                offenders.append(str(path.name))
        assert examined >= 3, (
            f"only {examined} module(s) with a value widget were found — the "
            "sweep is not reaching the UI package, so a clean result is "
            "meaningless (there are at least Settings, the drive picker and "
            "the drive-setup dialog)"
        )
        assert not offenders, (
            "these build a QSpinBox/QComboBox/QSlider but never call "
            "`protect_value_widgets`, so scrolling past one silently edits it "
            "— for anything reaching cyanrip's argv that rips the next disc "
            f"wrong with a clean-looking log:\n  {chr(10).join(offenders)}"
        )

    def test_no_module_appends_to_a_text_view_directly(self) -> None:
        offenders: list[str] = []
        examined = 0
        for path in self._ui_modules():
            if path.name == "scroll_guards.py":
                continue
            examined += 1
            if path.name in self.STICKY_APPEND_EXEMPT:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if line.lstrip().startswith("#"):
                    continue
                if re.search(r"\.appendPlainText\s*\(", line):
                    offenders.append(f"{path.name}:{lineno}")
        assert examined >= 20, f"sweep reached only {examined} modules"
        assert not offenders, (
            "these append directly, which always yanks the view to the bottom "
            "and drags a reader away from the line they stopped on. Use "
            "`append_keeping_position`, or add a reasoned allowlist entry:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_allowlisted_exception_really_is_stronger(self) -> None:
        """A ratchet entry that stops being true is worse than no entry.

        `rip_progress` is exempt *because* it has tab-aware follow state. If
        someone deletes that mechanism and leaves the exemption, the module
        keeps its pass while losing the property the exemption was granted for
        — the "satisfied by the wrong thing" failure. So the claim is checked.
        """
        from platterpus import ui

        source = (Path(ui.__file__).parent / "rip_progress.py").read_text(
            encoding="utf-8"
        )
        assert "_log_follow" in source and "valueChanged" in source, (
            "rip_progress.py is allowlisted out of the sticky-append rule "
            "because it tracks follow state itself — that mechanism is gone, "
            "so either restore it or drop the allowlist entry and use "
            "`append_keeping_position`"
        )


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
