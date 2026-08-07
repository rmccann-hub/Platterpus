# SPDX-License-Identifier: GPL-3.0-only
"""The Live log pane must show the newest line, including from a hidden tab.

**The report, verbatim (2026-08-06, real hardware):** *"its odd it says its
re-ripping track 5, but log says track 12."* The status line read
`Re-ripping track 5 to secure it… 97%`; the Live log pane's visible lines read
`Ripping and encoding track 12, progress - 7.22%`.

**Settled from the artifact, and the two lines are timestamped** (`CLAUDE.md` —
answer it from the artifact, and name which one). The rip's `.platterpus.json`
carries the session's debug stream, so both halves of the screenshot can be
located in it to the second:

* the status line, `Re-ripping track 5 … 97%`, matches
  `19:21:20,084  cyanrip │ Ripping track 5, progress - 96.39%`;
* the pane's visible tail, `track 12, progress - 7.22% … 7.44%`, was emitted at
  `18:59:35,904 … 18:59:36,434`.

**The pane was 21 minutes 44 seconds stale.** The status was current. Both
surfaces read the same `log_line` signal and the pane's copy is if anything
*fresher* relative to its own throttle, so the discrepancy could not come from
the stream — which is what pointed at the viewport.

(The screenshot's stamp reads `21:20` because it is cropped on the left — the
same crop that renders "Overall" as "erall". The status format is `%H:%M:%S`, so
the full stamp is `19:21:20`. Worth recording: a first pass at this treated the
apparent `21:20` as a *different, later* rip and nearly discarded the maintainer's
report as unmatchable to the artifacts. He said he took the screenshots during
the rip; he was right, and the disagreement was in the crop.)

**The cause was measured before it was fixed.** `QPlainTextEdit.appendPlainText`
auto-scrolls only a widget Qt is laying out. In a **non-current tab** — where
this view sits for most of a rip, because the user is watching the track grid —
3000 appends leave `verticalScrollBar().value() == 0` against `maximum() == 2999`.
That is the whole bug, and `test_a_hidden_tab_does_not_auto_scroll_without_help`
below pins the Qt behaviour itself, so if a future Qt fixes it we find out rather
than carrying a workaround forever.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.ui.rip_progress import _TAB_LOG, _TAB_TRACKS, RipProgress

# Enough lines to make the difference unmistakable and to exceed any viewport.
_LINES = 400


def _pane(qapp: QApplication) -> RipProgress:
    del qapp
    pane = RipProgress()
    pane.resize(700, 400)
    return pane


def _bar(pane: RipProgress):  # noqa: ANN202 — Qt scrollbar, typed at the call sites
    return pane._log_view.verticalScrollBar()


def test_a_hidden_tab_does_not_auto_scroll_without_help(qapp: QApplication) -> None:
    """Pin the Qt behaviour the fix exists for, on a bare widget.

    Deliberately NOT using the pane: this asserts the platform fact, so the fix's
    premise is checkable independently of our code. If this ever starts failing,
    Qt changed and the workaround can be reconsidered — which is a better outcome
    than a workaround nobody revisits.
    """
    from PySide6.QtWidgets import QPlainTextEdit, QTabWidget, QWidget

    tabs = QTabWidget()
    view = QPlainTextEdit()
    view.setReadOnly(True)
    tabs.addTab(QWidget(), "first")
    tabs.addTab(view, "log")
    tabs.resize(600, 300)
    tabs.show()
    qapp.processEvents()
    for i in range(_LINES):
        view.appendPlainText(f"line {i}")
    qapp.processEvents()
    bar = view.verticalScrollBar()
    assert bar.maximum() > 0, "the fixture appended too little to scroll at all"
    assert bar.value() == 0, (
        "Qt now auto-scrolls a hidden tab; the follow-the-tail workaround in "
        "rip_progress can be revisited"
    )


def test_the_pane_tracks_the_tail_while_its_tab_is_hidden(
    qapp: QApplication,
) -> None:
    """The regression, asserted where the difference is unambiguous.

    **This assertion was rewritten after failing its own revert check**, which is
    worth recording because the first version looked right. It asserted the state
    *after* switching to the tab — and Qt, once it finally lays the document out,
    lands at or one line short of the bottom depending on how the lines wrap. With
    the fix reverted it landed at exactly `382/382` for these lines and `381/382`
    for shorter ones, so the test passed against the broken code for a reason that
    had nothing to do with the code. A check that can be satisfied by the wrong
    thing is worse than one that fails (`CLAUDE.md`).

    The state that actually distinguishes the two implementations is the one
    *while the tab is hidden*: reverted, the scrollbar sits at `0` against a
    maximum of `_LINES - 1`; fixed, it tracks the tail continuously. That is also
    the state that matters, because it is the one the pane is in for most of a
    rip.
    """
    pane = _pane(qapp)
    pane.show()
    pane._tabs.setCurrentIndex(_TAB_TRACKS)  # the user is watching the track grid
    qapp.processEvents()

    for i in range(_LINES):
        pane.append_log_line(f"Ripping and encoding track {i // 30 + 1}, progress - 1%")
    qapp.processEvents()

    bar = _bar(pane)
    assert bar.maximum() > 0, "nothing to scroll — the fixture proved nothing"
    assert bar.value() == bar.maximum(), (
        f"the hidden Live log is parked at {bar.value()} of {bar.maximum()}: it is "
        "not tracking the newest line, so whatever is on screen when the user "
        "opens the tab is whatever Qt's deferred layout decides"
    )
    # And the newest line is genuinely the last one appended, not merely *a* late
    # one — a position check alone would pass on the wrong content.
    assert (
        pane._log_view.toPlainText()
        .rstrip()
        .endswith(f"Ripping and encoding track {(_LINES - 1) // 30 + 1}, progress - 1%")
    )


def test_switching_to_the_tab_lands_on_the_newest_line(qapp: QApplication) -> None:
    """The second half of the fix: re-pin when the tab becomes current.

    Weaker than the test above by design — Qt's own post-switch position is
    already close to the bottom, so this cannot distinguish the implementations on
    its own. It is here to pin the *user-visible* promise (open the tab, see the
    newest line) rather than the mechanism.
    """
    pane = _pane(qapp)
    pane.show()
    pane._tabs.setCurrentIndex(_TAB_TRACKS)
    qapp.processEvents()
    for i in range(_LINES):
        pane.append_log_line(f"line {i}")
    qapp.processEvents()
    pane._tabs.setCurrentIndex(_TAB_LOG)
    qapp.processEvents()
    bar = _bar(pane)
    assert bar.value() == bar.maximum()


def test_it_follows_while_the_tab_is_visible_too(qapp: QApplication) -> None:
    """The ordinary case must not regress in the course of fixing the odd one."""
    pane = _pane(qapp)
    pane.show()
    pane._tabs.setCurrentIndex(_TAB_LOG)
    qapp.processEvents()
    for i in range(_LINES):
        pane.append_log_line(f"line {i}")
    qapp.processEvents()
    bar = _bar(pane)
    assert bar.maximum() > 0
    assert bar.value() == bar.maximum()


def test_scrolling_up_pauses_the_follow(qapp: QApplication) -> None:
    """A console you cannot read back in is not a console.

    The new state the fix creates (`CLAUDE.md` — *what new state does this fix
    create, and what tests that?*): a follow flag. Its failure mode is yanking a
    reader back to the bottom mid-sentence, so that is what this pins.
    """
    pane = _pane(qapp)
    pane.show()
    pane._tabs.setCurrentIndex(_TAB_LOG)
    qapp.processEvents()
    for i in range(_LINES):
        pane.append_log_line(f"line {i}")
    qapp.processEvents()

    bar = _bar(pane)
    parked = bar.maximum() // 2
    bar.setValue(parked)  # the user drags up to read something
    qapp.processEvents()
    assert pane._log_follow is False

    for i in range(50):
        pane.append_log_line(f"more {i}")
    qapp.processEvents()
    assert bar.value() == parked, "the pane yanked the reader back to the bottom"


def test_scrolling_back_to_the_bottom_resumes_the_follow(
    qapp: QApplication,
) -> None:
    pane = _pane(qapp)
    pane.show()
    pane._tabs.setCurrentIndex(_TAB_LOG)
    qapp.processEvents()
    for i in range(_LINES):
        pane.append_log_line(f"line {i}")
    qapp.processEvents()
    bar = _bar(pane)
    bar.setValue(0)
    qapp.processEvents()
    assert pane._log_follow is False
    bar.setValue(bar.maximum())
    qapp.processEvents()
    assert pane._log_follow is True
    pane.append_log_line("the newest line")
    qapp.processEvents()
    assert bar.value() == bar.maximum()


@pytest.mark.parametrize("tab", [_TAB_TRACKS, _TAB_LOG])
def test_appending_never_raises_whatever_tab_is_current(
    qapp: QApplication, tab: int
) -> None:
    """`append_log_line` runs on the GUI thread for every ripper line.

    A raise here would escape a queued slot during a rip, so the floor is that it
    survives both tab states and an empty line.
    """
    pane = _pane(qapp)
    pane.show()
    pane._tabs.setCurrentIndex(tab)
    qapp.processEvents()
    pane.append_log_line("")
    pane.append_log_line("x" * 5000)
    qapp.processEvents()
