"""Tests for the app-wide dialog-centering filter."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QRect
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget

from platterpus.ui.dialogs import auto_center
from platterpus.ui.dialogs.auto_center import (
    DialogCenterFilter,
    has_been_centered,
    mark_as_centered,
)
from platterpus.ui.dialogs.centering import CenteredDialog, _clamp_to


@pytest.fixture
def centered_ids(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Record which dialogs the filter actually placed, without holding them.

    The filter's real job (moving a window) is invisible to a headless test, so
    we spy on the one call that does it. We record `id()` rather than the widget
    itself **on purpose**: keeping a reference would keep the dialog alive, and
    the BUG-10 test below depends on each dialog really being freed.
    """
    seen: list[int] = []
    monkeypatch.setattr(auto_center, "center_on_anchor", lambda w: seen.append(id(w)))
    return seen


def test_filter_centres_a_plain_dialog_once_on_its_first_show(
    qapp: QApplication, centered_ids: list[int]
) -> None:
    # A plain QDialog (a QMessageBox is one) is centred on its first Show and
    # marked, so a second Show leaves it exactly where the user left it.
    f = DialogCenterFilter()
    box = QMessageBox()
    assert not has_been_centered(box)

    f.eventFilter(box, QEvent(QEvent.Type.Show))
    assert has_been_centered(box)
    assert centered_ids == [id(box)]

    f.eventFilter(box, QEvent(QEvent.Type.Show))
    assert centered_ids == [id(box)]  # still once — not re-centred


def test_filter_skips_centered_dialog(
    qapp: QApplication, centered_ids: list[int]
) -> None:
    # CenteredDialog self-centres, so the filter must not also handle it — and
    # must not mark it either (the mark means "*we* placed this one").
    f = DialogCenterFilter()
    dlg = CenteredDialog()
    f.eventFilter(dlg, QEvent(QEvent.Type.Show))
    assert not has_been_centered(dlg)
    assert centered_ids == []


def test_filter_ignores_non_show_events(
    qapp: QApplication, centered_ids: list[int]
) -> None:
    f = DialogCenterFilter()
    box = QMessageBox()
    f.eventFilter(box, QEvent(QEvent.Type.Hide))
    assert not has_been_centered(box)
    assert centered_ids == []


def test_a_new_dialog_is_centred_even_when_it_reuses_a_freed_id(
    qapp: QApplication, centered_ids: list[int]
) -> None:
    """BUG-10, asserted the way the bug actually happened.

    Dialogs are transient, and CPython hands a freed address straight to the next
    object: created and dropped in a loop, every one of these message boxes lands
    on the *same* `id()`. The original filter kept a `set` of ids, so it centred
    the first box and silently skipped the other 49 — the exact "prompt opened on
    the wrong monitor" bug this filter exists to prevent.

    The mark now lives on the dialog (a Qt dynamic property), so it dies with the
    dialog and a recycled address means nothing. No `gc.collect()` is needed —
    and none is wanted: forcing a collection here detonates every deferred cycle
    in the whole suite at one point, which is its own crash hazard under the
    headless `offscreen` platform (docs/testing.md).
    """
    f = DialogCenterFilter()
    ids: list[int] = []
    for _ in range(50):
        box = QMessageBox()
        ids.append(id(box))
        f.eventFilter(box, QEvent(QEvent.Type.Show))
        del box  # freed by refcount, right here — no collection required

    # Sanity: if ids were NOT recycled this test would prove nothing, so say so
    # rather than passing vacuously.
    assert len(set(ids)) < 50, "no id was reused — this can no longer detect BUG-10"
    assert len(centered_ids) == 50


def test_the_filter_keeps_no_registry_of_dialogs(qapp: QApplication) -> None:
    """The design property behind the BUG-10 fix, asserted directly.

    The filter is installed on the QApplication for the whole session. If it
    holds a container of dialogs (or of their ids), that container is both a
    staleness hazard and something that grows all session. It must stay empty of
    per-dialog state; the mark belongs on the dialog.
    """
    f = DialogCenterFilter()
    box = QMessageBox()
    f.eventFilter(box, QEvent(QEvent.Type.Show))
    # PySide pre-populates a couple of SignalInstance attributes; none of them —
    # nor anything a future change adds — may be a dialog or a collection.
    for name, value in vars(f).items():
        assert value is not box, name
        assert not isinstance(value, (set, frozenset, dict, list, tuple)), name


def test_a_dialog_whose_c_object_is_gone_is_treated_as_handled(
    qapp: QApplication,
) -> None:
    """A PySide wrapper can outlive its C++ object, and touching one raises
    RuntimeError. Centring is cosmetic and runs inside Qt's event delivery, so
    the mark helpers must swallow that — and a widget that no longer exists is
    "nothing left to place", i.e. already handled.

    The half-dead widget is made the way it happens for real: Qt deletes a
    parented child's C++ object along with its parent, while Python still holds
    the child's wrapper.
    """
    parent = QWidget()
    dlg = QDialog(parent)
    del parent  # Python owned the parent → Qt deletes the child's C++ side

    assert has_been_centered(dlg) is True
    mark_as_centered(dlg)  # must not raise either


def test_filter_never_consumes_event(qapp: QApplication) -> None:
    # The filter only observes; it must always return False so the dialog still
    # processes its own Show.
    f = DialogCenterFilter()
    assert f.eventFilter(QDialog(), QEvent(QEvent.Type.Show)) is False


# --- _clamp_to: the "never leave a dialog off-screen" guard (pure, no display) --

_AVAIL = QRect(0, 0, 1920, 1080)


def test_clamp_leaves_a_fully_visible_rect_untouched() -> None:
    frame = QRect(600, 400, 400, 300)  # comfortably inside
    assert _clamp_to(frame, _AVAIL) == frame


def test_clamp_pulls_back_a_rect_off_the_top_left() -> None:
    # Centred on a window near the top-left corner → negative top-left.
    clamped = _clamp_to(QRect(-120, -80, 400, 300), _AVAIL)
    assert clamped.topLeft().x() == 0 and clamped.topLeft().y() == 0
    assert clamped.size() == QRect(-120, -80, 400, 300).size()  # not resized


def test_clamp_pulls_back_a_rect_off_the_bottom_right() -> None:
    clamped = _clamp_to(QRect(1800, 1000, 400, 300), _AVAIL)
    # Slid just inside: right/bottom edges land on the available boundary.
    assert clamped.right() == _AVAIL.right()
    assert clamped.bottom() == _AVAIL.bottom()


def test_clamp_respects_a_nonzero_screen_origin() -> None:
    # A second monitor to the right: available area starts at x=1920.
    avail = QRect(1920, 0, 1920, 1080)
    # A dialog that landed to the LEFT of that screen is pulled onto it.
    clamped = _clamp_to(QRect(100, 50, 400, 300), avail)
    assert clamped.left() == 1920 and clamped.top() == 50


def test_clamp_pins_an_oversized_rect_to_the_top_left() -> None:
    # Bigger than the screen → pin top-left so the title bar/buttons stay reachable.
    clamped = _clamp_to(QRect(-50, -50, 3000, 2000), _AVAIL)
    assert clamped.topLeft().x() == 0 and clamped.topLeft().y() == 0


def test_center_on_anchor_raises_and_activates(qapp: QApplication) -> None:
    """Centring must also bring the dialog to the FRONT and focus it — the fix for
    a (correctly parented) prompt opening behind other windows on a 2-monitor
    desktop. We spy on raise_()/activateWindow() to confirm both are called."""
    from platterpus.ui.dialogs.centering import center_on_anchor

    class _SpyDialog(QDialog):
        def __init__(self) -> None:
            super().__init__()
            self.raised = False
            self.activated = False

        def raise_(self) -> None:  # noqa: N802 — Qt override
            self.raised = True
            super().raise_()

        def activateWindow(self) -> None:  # noqa: N802 — Qt override
            self.activated = True
            super().activateWindow()

    dlg = _SpyDialog()
    center_on_anchor(dlg)
    assert dlg.raised and dlg.activated
