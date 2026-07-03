"""Tests for the app-wide dialog-centering filter."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from platterpus.ui.dialogs.auto_center import DialogCenterFilter
from platterpus.ui.dialogs.centering import CenteredDialog, _clamp_to


def test_filter_marks_plain_dialog_seen_on_show(qapp: QApplication) -> None:
    # A plain QDialog (e.g. QMessageBox is one) gets centred — and recorded — on
    # its first Show, and only once. BUG-10: _seen now tracks the objects (a
    # WeakSet), not id() ints, so a reused id can't cause a false "already seen".
    f = DialogCenterFilter()
    box = QMessageBox()
    f.eventFilter(box, QEvent(QEvent.Type.Show))
    assert box in f._seen
    # A second show is a no-op (already seen) — must not raise.
    f.eventFilter(box, QEvent(QEvent.Type.Show))


def test_filter_skips_centered_dialog(qapp: QApplication) -> None:
    # CenteredDialog self-centres, so the filter must not also handle it.
    f = DialogCenterFilter()
    dlg = CenteredDialog()
    f.eventFilter(dlg, QEvent(QEvent.Type.Show))
    assert dlg not in f._seen


def test_filter_ignores_non_show_events(qapp: QApplication) -> None:
    f = DialogCenterFilter()
    box = QMessageBox()
    f.eventFilter(box, QEvent(QEvent.Type.Hide))
    assert box not in f._seen


def test_filter_forgets_a_destroyed_dialog(qapp: QApplication) -> None:
    """BUG-10: the WeakSet drops an entry once the dialog is gone, so a later
    dialog that happens to reuse the freed id() is NOT wrongly skipped (the old
    id()-in-a-plain-set could match a stale id and leave a dialog un-centred)."""
    import gc

    f = DialogCenterFilter()
    box = QMessageBox()
    f.eventFilter(box, QEvent(QEvent.Type.Show))
    assert len(f._seen) == 1
    del box
    gc.collect()
    # The weakref entry is gone, so nothing stale lingers to shadow a new dialog.
    assert len(f._seen) == 0


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
