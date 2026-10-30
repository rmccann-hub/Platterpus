"""Hold a question the user did not ask for until the main window is the one in use.

**Why this exists (TASKS R96, the owner's reports of 2026-10-28 and 29).** On
0.7.114 the album picker, which opens by itself when a disc's lookup returns more
than one release, appeared while the owner was in Tools → Setup & Updates…,
asking them to choose or cancel there. Their rule, in their words: *"if they need
to pop up, sure, but if they can hold, then hold them."* So dialogs come in two
kinds:

* **can hold** — nothing is waiting on the answer and nothing is lost by a delay
  (the album picker for a disc just inserted is the first). Those wait here until
  the main window is the one in use, then open;
* **must show now** — something is stopped on the answer or lost without it (a
  failed rip, a question a running rip is blocked on). Those do not come here;
  they open at once, and `CenteredDialog` raises them to the front.

**"In use" is read from Qt, not tracked.** Busy means: a modal dialog is open
(`QApplication.activeModalWidget()`), or the active window is one of ours other
than the main window. Setup & Updates is NOT modal (the 2026-10-28 run's
screenshot list reads `modal=False`), so a modal-only test would not have held the
picker the owner saw. The script console is exempt: during an acceptance run it is
the active window by design, and the script answers the picker itself.

**The precondition is checked where the dialog opens, not where it was queued**
(`CLAUDE.md`): every retry asks the caller's ``still_wanted`` first, so a held
picker for a disc that has since changed is dropped, not shown.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Final

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget

log = logging.getLogger(__name__)

#: How often a held dialog asks again. Half a second: short enough that the
#: dialog appears as the user comes back to the main window, long enough to cost
#: nothing while they work elsewhere.
RETRY_MS: Final[int] = 500


def busy_reason(main_window: QWidget) -> str:
    """Why a dialog that can hold should not open now, or ``""`` if it may."""
    modal = QApplication.activeModalWidget()
    if modal is not None:
        return f"a dialog is open ({modal.windowTitle()!r})"
    active = QApplication.activeWindow()
    if active is None or active is main_window or not active.isVisible():
        # Our app is not focused at all, or the main window is: either way no
        # other window of ours is being used, so the question may open. A hidden
        # window is not in use either: Qt can go on naming a dialog that just
        # closed as the active window until another one is activated.
        return ""
    # Imported here: the script console imports half the UI, and this module is
    # imported by the main window.
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

    if isinstance(active, ScriptConsoleDialog):
        return ""
    return f"another window is in use ({active.windowTitle()!r})"


def hold_until_free(
    main_window: QWidget,
    show: Callable[[], None],
    *,
    still_wanted: Callable[[], bool],
    what: str,
    on_drop: Callable[[], None] | None = None,
) -> None:
    """Call ``show`` now if the main window is free, else once it is.

    ``still_wanted`` is asked before every attempt, the first included; when it
    says no, the held dialog is dropped, the drop is logged, and ``on_drop`` runs
    so the caller can forget it was holding one. The retry timer is parented to
    ``main_window``, so it dies with the window.
    """
    logged_hold = False

    def attempt() -> None:
        nonlocal logged_hold
        if not still_wanted():
            log.info("%s: no longer wanted, not opened", what)
            if on_drop is not None:
                on_drop()
            return
        reason = busy_reason(main_window)
        if not reason:
            if logged_hold:
                log.info("%s: the main window is free again, opening it now", what)
            show()
            return
        if not logged_hold:
            logged_hold = True
            log.info(
                "%s: held until the main window is in use, because %s", what, reason
            )
        QTimer.singleShot(RETRY_MS, main_window, attempt)

    attempt()
