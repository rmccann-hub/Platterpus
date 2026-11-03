"""A dialog opened without waiting for it is deleted when it closes.

**Why this exists (review of the 2026-11-03 Full run, B2).** Every screenshot
step of that run listed ``QMessageBox 'cyanrip update' visible=False
modal=True``: the cyanrip install offer (`_offer_ripper_install`) was built per
offer, opened with ``open()``, and never deleted. ``open()`` and ``show()``
return at once, and the parent window owns the dialog, so without
``WA_DeleteOnClose`` each one stays behind as a hidden child for the life of the
process: a modal one keeps answering *"is a dialog open?"* sweeps, and the
acceptance run's screenshots recorded it on every step. Its sibling in
`_on_ripper_update_result` already set the attribute, with a comment naming
this leak; the rule was written into one box and not the other.

**The sweep.** Every function in the package that builds a dialog (Qt's own and
every subclass, `test_dialogs_have_a_parent._dialog_classes`) and then opens it
with ``open()`` or ``show()`` must set ``WA_DeleteOnClose`` in that function, or
be listed below with the reason it does not. ``exec()`` is not swept: it
returns only when the dialog has closed, and the caller drops it there. The
allowlist may shrink, never grow.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from test_dialogs_have_a_parent import _dialog_classes

SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: ``(module, function)`` that open a dialog without waiting and do not delete
#: it on close, each with its reason. RATCHET: may shrink, never grow.
_KEPT_ON_PURPOSE: Final[dict[tuple[str, str], str]] = {
    ("ui/main_window.py", "_on_show_getting_started"): (
        "one guide per window, built once and raised again on every later open, "
        "so it is reused, not leaked"
    ),
    ("ui/main_window_provision.py", "open_setup_center"): (
        "held on `self._setup_center`, which a dozen methods read; a closed one "
        "is replaced on the next open and stays behind until the window goes. "
        "Deleting it on close needs every reader to forget it first (a known "
        "gap, reported with B2)"
    ),
    ("ui/main_window_provision.py", "open_script_console"): (
        "held on `self._script_console`, whose runner and timers outlive a "
        "close by design; replaced on the next open, as Setup & Updates is"
    ),
    ("ui/main_window_update.py", "_begin_update_install"): (
        "the update's progress window, held on `self._install_dialog`; the "
        "worker's queued progress slots read it until it is cleared, so a "
        "close by the window's own button must not delete it under them"
    ),
}


def _target(node: ast.expr) -> str | None:
    """``box`` or ``self.box`` as a name, else ``None``."""
    if isinstance(node, ast.Name):
        return node.id
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    ):
        return f"self.{node.attr}"
    return None


def _sets_delete_on_close(fn: ast.AST) -> bool:
    """A real ``setAttribute(... WA_DeleteOnClose ...)`` call, not a mention:
    a comment naming the attribute must not satisfy the sweep."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "setAttribute"
        and any(
            isinstance(arg, ast.Attribute) and arg.attr == "WA_DeleteOnClose"
            for arg in node.args
        )
        for node in ast.walk(fn)
    )


def _opened_without_waiting(
    root: Path = SRC,
) -> tuple[dict[tuple[str, str], bool], int]:
    """Each function that opens a dialog it built with ``open()``/``show()``,
    mapped to whether it sets ``WA_DeleteOnClose``; and how many dialog
    constructions were read."""
    dialogs = _dialog_classes(root) | {"plain_progress_dialog"}
    found: dict[tuple[str, str], bool] = {}
    built_total = 0
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        for fn in ast.walk(ast.parse(text)):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            built: set[str] = set()
            for node in ast.walk(fn):
                if not (
                    isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                ):
                    continue
                func = node.value.func
                name = (
                    func.id
                    if isinstance(func, ast.Name)
                    else func.attr
                    if isinstance(func, ast.Attribute)
                    else None
                )
                if name in dialogs:
                    built_total += 1
                    built |= {n for t in node.targets if (n := _target(t))}
            opens = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("open", "show")
                and _target(node.func.value) in built
                for node in ast.walk(fn)
            )
            if opens:
                found[(rel, fn.name)] = _sets_delete_on_close(fn)
    return found, built_total


def test_every_dialog_opened_without_waiting_is_deleted_when_it_closes() -> None:
    found, built = _opened_without_waiting()
    # Floors: the scan read the package's dialogs (29 assigned constructions on
    # 2026-11-03), and found the sites it
    # exists for, the two cyanrip boxes among them.
    assert built >= 25, f"only {built} dialog constructions read: the scan broke"
    assert len(found) >= 6, found
    assert ("ui/main_window_update.py", "_offer_ripper_install") in found, found
    assert ("ui/main_window_update.py", "_on_ripper_update_result") in found, found

    leaking = sorted(
        f"{module}::{function}"
        for (module, function), deletes in found.items()
        if not deletes and (module, function) not in _KEPT_ON_PURPOSE
    )
    assert leaking == [], (
        "opened with open()/show() and never deleted: each one stays behind as "
        f"a hidden child of its window. Set WA_DeleteOnClose: {leaking}"
    )


def test_the_allowlist_names_only_sites_that_still_exist_and_still_keep() -> None:
    """A fixed site leaves the list in the same change, so it cannot be
    regressed behind a stale exemption."""
    found, _ = _opened_without_waiting()
    stale = sorted(
        f"{m}::{f}" for (m, f) in _KEPT_ON_PURPOSE if found.get((m, f)) is not False
    )
    assert stale == [], f"remove from _KEPT_ON_PURPOSE: {stale}"


def test_a_declined_cyanrip_install_offer_leaves_no_box_behind(qapp: object) -> None:
    """B2 itself, on the real window: the offer is opened, declined, and once
    Qt runs its deferred deletes no `QMessageBox` is left under the window,
    so the next screenshot sweep cannot list a hidden, modal 'cyanrip update'."""
    from conftest import stop_window_threads
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QMessageBox
    from test_ui_main_window import _make_window

    window = _make_window(qapp)
    try:
        window._offer_ripper_install(object(), "a newer build", "abc1234")
        box = window._ripper_offer_box
        assert isinstance(box, QMessageBox), "floor: no offer was opened"
        decline = next(
            b
            for b in box.buttons()
            if box.buttonRole(b) == QMessageBox.ButtonRole.RejectRole
        )
        decline.click()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        left = [
            b.windowTitle()
            for b in window.findChildren(QMessageBox)
            if b.windowTitle() == "cyanrip update"
        ]
        assert left == [], f"the declined offer stayed behind: {left}"
        assert window._ripper_offer_box is None
    finally:
        window.hide()
        stop_window_threads(window)
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
