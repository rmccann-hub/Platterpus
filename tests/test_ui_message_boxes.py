"""`ui/message_boxes.py` answers exactly as Qt's static helpers do.

The module replaces `QMessageBox.warning/information/critical/question` at every
call site in the product (so the text can be pinned to PlainText, which a static
helper cannot do). Converting 38 call sites is only a routing change if each
function gives the caller the SAME answer the static helper did, for every way a
person can close the box. So these tests open both for real, side by side, and
compare them against Qt itself, the source artifact, rather than against a
description of what Qt does:

* the same buttons, the same default button, the same icon, title and text;
* the same answer for each button, for Esc, and for the window's close button;
* PlainText on ours, AutoText on theirs — the one intended difference.

A timer inspects the box once its modal loop is running and then acts, so no
person is needed; a test-owned watchdog closes anything left open, so a
regression fails a test instead of hanging the session. That holds for EVERY
test here that opens a real box, not only the comparison: each opens it inside
`_watchdog` and asserts the watchdog did not have to step in, and a sweep of this
file refuses a box opened outside one. Without it, `exec()` waits for a click
that never comes, and pytest's 300 s faulthandler ends the worker as a crash
rather than a failed test (review finding Q2, 2026-09-28: two tests had no
watchdog, and a regression in the code they test hung them).

**One difference is Qt's, not ours, and it is recorded here so nobody "fixes" it.**
PySide6 resolves a five-argument `QMessageBox.warning/critical/question(...)` to
Qt's deprecated int-returning overload, so the static helper hands back a bare
`int`. Ours returns `QMessageBox.StandardButton`. Every caller compares with
`==`, and an `IntFlag` equals its integer value, so the comparison each caller
makes is unchanged; the tests below compare VALUES.

Also here: a box whose parent is destroyed while it is open answers NoButton (a
missing answer never reads as a Yes) and says so in the log, and a box is handed
back to Qt once its answer is read, rather than staying behind as a hidden child
of the window for the rest of the session.
"""

from __future__ import annotations

import ast
import contextlib
import logging
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Final

import pytest
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QApplication, QMessageBox, QWidget

from platterpus.ui import message_boxes

SB = QMessageBox.StandardButton

#: The REAL functions on both sides, taken when this file is imported. The
#: autouse `_non_blocking_message_boxes` fixture in `tests/conftest.py` replaces
#: both Qt's statics and the module's functions for every test, so that no box
#: waits for a click; collection imports this file before any test runs, so
#: these references are Qt's own helpers and the product's own functions.
_QT_STATIC: Final[dict[str, Callable[..., int]]] = {
    "information": QMessageBox.information,
    "warning": QMessageBox.warning,
    "critical": QMessageBox.critical,
    "question": QMessageBox.question,
}
_OURS: Final[dict[str, Callable[..., int]]] = {
    "information": message_boxes.information,
    "warning": message_boxes.warning,
    "critical": message_boxes.critical,
    "question": message_boxes.question,
}

#: Text whose first line Qt's AutoText reads as HTML, so the format difference is
#: exercised where it matters and the title/text comparison is not trivially
#: equal on text both would show the same.
_TITLE: Final[str] = "Title <b>not bold</b>"
_TEXT: Final[str] = "<b>cyanrip</b> 0.9.3\nInstall failures:\n  • flac: <stdin>"

#: `(label, extra positional arguments, the buttons the box must show)` — the
#: button shapes our call sites use, plus Qt's own defaults and the one legacy
#: shape (a default button that is not among the buttons).
_CONFIGS: Final[list[tuple[str, tuple[SB, ...], dict[str, tuple[str, ...]]]]] = [
    (
        "defaults",
        (),
        {
            "information": ("Ok",),
            "warning": ("Ok",),
            "critical": ("Ok",),
            "question": ("No", "Yes"),
        },
    ),
    ("Yes|No,Yes", (SB.Yes | SB.No, SB.Yes), {"*": ("No", "Yes")}),
    ("Yes|No,No", (SB.Yes | SB.No, SB.No), {"*": ("No", "Yes")}),
    ("Yes|Cancel,Cancel", (SB.Yes | SB.Cancel, SB.Cancel), {"*": ("Cancel", "Yes")}),
    ("Ok|Cancel", (SB.Ok | SB.Cancel,), {"*": ("Cancel", "Ok")}),
    ("legacy Yes,No", (SB.Yes, SB.No), {"*": ("No", "Yes")}),
]

#: How long the watchdog lets a box stay open before closing it and failing the
#: case. A box here is acted on at the first turn of its event loop, so anything
#: near this long means the timer never found it.
_WATCHDOG_MS: Final[int] = 3000


def _cases() -> list[tuple[str, str, tuple[SB, ...], tuple[str, ...], str]]:
    """Every (kind, config, args, expected buttons, action) to compare."""
    cases = []
    for kind in _QT_STATIC:
        for label, args, buttons_by_kind in _CONFIGS:
            buttons = buttons_by_kind.get(kind, buttons_by_kind.get("*", ()))
            for action in (*buttons, "esc", "close"):
                cases.append((kind, label, args, buttons, action))
    return cases


@contextlib.contextmanager
def _watchdog(seen: dict[str, object]) -> Iterator[None]:
    """Close any box still open after `_WATCHDOG_MS`, and record that it had to.

    Every test here that opens a real box does so inside this, so a regression that
    leaves a box open (a timer that never found it, a box no longer parented to
    what deletes it, a button that is not there) fails that test within seconds.
    `seen["rescued"]` is the watchdog's own report, and each caller asserts it
    stayed False: a box the watchdog had to close was not closed by what the test
    is about.

    It closes EVERY visible box, parented or not, because a box a regression left
    unparented is a top-level window of its own and still has to go.
    """
    seen["rescued"] = False

    def _rescue() -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMessageBox) and widget.isVisible():
                seen["rescued"] = True
                widget.done(0)

    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(_WATCHDOG_MS)
    timer.timeout.connect(_rescue)
    timer.start()
    try:
        yield
    finally:
        timer.stop()


def _button_name(box: QMessageBox, button: QAbstractButton | None) -> str:
    if button is None:
        return "None"
    return box.standardButton(button).name or "?"


def _open_and_act(
    show: Callable[..., int],
    args: tuple[SB, ...],
    action: str,
    parent: QWidget | None = None,
) -> dict[str, object]:
    """Open a box for real with ``show``, then press ``action`` on it.

    Returns what the open box showed and the answer ``show`` returned (as its
    integer value, so Qt's bare-int overload and our enum compare by what they
    mean). ``rescued`` is set if the watchdog had to close it.
    """
    seen: dict[str, object] = {}

    def _act() -> None:
        box = QApplication.activeModalWidget()
        if not isinstance(box, QMessageBox):
            seen["error"] = f"no open message box to act on: {box!r}"
            return
        seen["icon"] = box.icon()
        seen["title"] = box.windowTitle()
        seen["text"] = box.text()
        seen["format"] = box.textFormat()
        seen["buttons"] = tuple(sorted(_button_name(box, b) for b in box.buttons()))
        seen["default"] = _button_name(box, box.defaultButton())
        if action == "esc":
            QTest.keyClick(box, Qt.Key.Key_Escape)
        elif action == "close":
            box.close()
        else:
            target = box.button(SB[action])
            if target is None:
                seen["error"] = f"the box has no {action} button"
                box.done(0)
                return
            target.click()

    QTimer.singleShot(0, _act)
    with _watchdog(seen):
        answer = show(parent, _TITLE, _TEXT, *args)
    seen["answer"] = int(answer)  # Qt's bare int and our IntFlag, by value
    return seen


@pytest.mark.parametrize(
    ("kind", "label", "args", "buttons", "action"),
    _cases(),
    ids=[f"{c[0]}-{c[1]}-{c[4]}" for c in _cases()],
)
def test_each_function_answers_as_qts_static_helper_does(
    qapp: QApplication,
    kind: str,
    label: str,
    args: tuple[SB, ...],
    buttons: tuple[str, ...],
    action: str,
) -> None:
    theirs = _open_and_act(_QT_STATIC[kind], args, action)
    ours = _open_and_act(_OURS[kind], args, action)

    # Both boxes were really open and really acted on — not rescued, not missed.
    for side, seen in (("Qt's static helper", theirs), ("ours", ours)):
        assert "error" not in seen, f"{side}: {seen.get('error')}"
        assert seen["rescued"] is False, f"{side}: the box was still open"
        # Non-triviality: the box showed the buttons this case is about, so an
        # answer that matches is a match over a real choice.
        assert seen["buttons"] == buttons, (side, seen["buttons"])

    # The one intended difference.
    assert theirs.pop("format") == Qt.TextFormat.AutoText
    assert ours.pop("format") == Qt.TextFormat.PlainText
    # Everything else, the answer included, is Qt's.
    assert ours == theirs


def test_the_comparison_covers_every_kind_and_every_way_to_close() -> None:
    """A floor under the parametrised comparison, so it cannot shrink unnoticed."""
    cases = _cases()
    assert (
        {c[0] for c in cases}
        == set(_OURS)
        == {
            "information",
            "warning",
            "critical",
            "question",
        }
    )
    assert {c[4] for c in cases} >= {"esc", "close", "Yes", "No", "Ok", "Cancel"}
    assert len(cases) >= 60


def test_a_box_destroyed_while_open_answers_nobutton_and_says_so(
    qapp: QApplication, caplog: pytest.LogCaptureFixture
) -> None:
    """Its parent goes away while it is open, taking the box with it.

    There is no answer to read. It must not read as a Yes — the Yes/No question
    below defaults to Yes, which is the answer a careless fallback would give —
    and it must not raise into the excepthook; it is logged instead.

    The parent's `deleteLater()` is posted from inside the box's own event loop,
    so that loop runs the deletion while the box is open (measured: the box's
    C++ side is gone by the time `exec()` returns).
    """
    parent = QWidget()
    seen: dict[str, object] = {}
    QTimer.singleShot(0, parent.deleteLater)
    with (
        caplog.at_level(logging.WARNING, logger="platterpus.ui.message_boxes"),
        _watchdog(seen),
    ):
        answer = _OURS["question"](parent, "t", "x", SB.Yes | SB.No, SB.Yes)
    # First: the box went away WITH its parent. Had the watchdog closed it, the
    # parent's deletion did not take it, which is the behaviour under test.
    assert seen["rescued"] is False, (
        "the box outlived its destroyed parent and the watchdog had to close it"
    )
    assert answer == SB.NoButton
    assert any(
        "destroyed while it was open" in record.getMessage()
        for record in caplog.records
    ), "a box that vanished without an answer must leave a line in the log"


def test_a_box_is_handed_back_to_qt_once_its_answer_is_read(
    qapp: QApplication,
) -> None:
    """Parented to a window that outlives it, a box is not freed by Python.

    Without the hand-back every box shown would stay behind as a hidden child of
    the main window for the rest of the session. Checked in two steps so the test
    shows which step removes it: still there until Qt's deferred deletions run,
    gone after.
    """
    parent = QWidget()
    seen: dict[str, object] = {}
    try:

        def _press_ok() -> None:
            # No `assert` in here: an exception raised in a timer slot is printed
            # and swallowed, and a box it failed to close stays open. Record what
            # went wrong, close the box, and assert once `exec()` has returned.
            box = QApplication.activeModalWidget()
            if not isinstance(box, QMessageBox):
                seen["error"] = f"no open message box to act on: {box!r}"
                return  # the watchdog closes whatever is open
            ok = box.button(SB.Ok)
            if ok is None:
                seen["error"] = "the box has no Ok button"
                box.done(0)
                return
            ok.click()

        QTimer.singleShot(0, _press_ok)
        with _watchdog(seen):
            answer = _OURS["information"](parent, "t", "x")
        assert "error" not in seen, seen.get("error")
        assert seen["rescued"] is False, "the box was still open"
        assert answer == SB.Ok
        assert len(parent.findChildren(QMessageBox)) == 1, "the box was never shown"
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert parent.findChildren(QMessageBox) == [], (
            "the box is still a child of its parent after its answer was read"
        )
    finally:
        parent.deleteLater()


# --- Every box this file opens is watched ------------------------------------

#: The tables whose functions open a real, modal box when called. `show` is
#: `_open_and_act`'s parameter, always one of them; `exec` is the box's own loop.
_OPENERS: Final[frozenset[str]] = frozenset({"_OURS", "_QT_STATIC"})

#: Nodes a `with` does not reach into: a function defined inside the block runs
#: whenever it is called, which may be after the watchdog has stopped.
_BOUNDARIES: Final[tuple[type[ast.AST], ...]] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
)


def _unwatched_openers(source: str) -> tuple[int, list[int]]:
    """How many calls in `source` open a real box, and the lines of those unwatched.

    A call is watched when a `with _watchdog(...)` encloses it in the same
    function.
    """
    tree = ast.parse(source)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    found = 0
    unwatched: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        opens = (
            (
                isinstance(func, ast.Subscript)
                and isinstance(func.value, ast.Name)
                and func.value.id in _OPENERS
            )
            or (isinstance(func, ast.Name) and func.id == "show")
            or (isinstance(func, ast.Attribute) and func.attr == "exec")
        )
        if not opens:
            continue
        found += 1
        ancestor = parents.get(node)
        watched = False
        while ancestor is not None and not isinstance(ancestor, _BOUNDARIES):
            if isinstance(ancestor, ast.With) and any(
                isinstance(item.context_expr, ast.Call)
                and isinstance(item.context_expr.func, ast.Name)
                and item.context_expr.func.id == "_watchdog"
                for item in ancestor.items
            ):
                watched = True
                break
            ancestor = parents.get(ancestor)
        if not watched:
            unwatched.append(node.lineno)
    return found, sorted(unwatched)


def test_every_box_this_file_opens_is_watched() -> None:
    """The module docstring's promise, held by a sweep of this file, not a comment."""
    found, unwatched = _unwatched_openers(Path(__file__).read_text(encoding="utf-8"))
    # Floor: three today (the comparison's `show`, the destroyed-parent question
    # and the hand-back information box). None found would mean the sweep is not
    # reading the calls, not that every call is watched.
    assert found >= 3, f"only {found} box-opening call(s) found in this file"
    assert not unwatched, (
        f"these lines of {Path(__file__).name} open a real message box outside "
        "`with _watchdog(seen):`, so a regression that leaves the box open hangs "
        f"the worker for 300 s instead of failing the test: {unwatched}"
    )
    # Non-triviality: it can say no, it can say yes, and a `with` does not
    # vouch for a function merely defined inside it.
    bare = "def t():\n    answer = _OURS['question'](None, 't', 'x')\n"
    watched = (
        "def t(seen):\n"
        "    with _watchdog(seen):\n"
        "        answer = _OURS['question'](None, 't', 'x')\n"
    )
    deferred = (
        "def t(seen):\n"
        "    with _watchdog(seen):\n"
        "        def later():\n"
        "            return _OURS['question'](None, 't', 'x')\n"
        "    later()\n"
    )
    assert _unwatched_openers(bare) == (1, [2])
    assert _unwatched_openers(watched) == (1, [])
    assert _unwatched_openers(deferred) == (1, [4])
