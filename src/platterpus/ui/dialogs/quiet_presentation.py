"""Windows that appear without taking focus or jumping to the front.

A scripted run opens and closes dozens of dialogs over hours. Before this, each
one was raised and given the keyboard (``centering.center_on_anchor``), taking it
from whatever the person was doing in another program. The owner's word,
2026-11-24 (TASKS R195): *"they should run on their own ... and also not
interrupt a user with bringing windows and things to the front."*

One process-wide switch, :func:`present_quietly`: on for a ``--run-script``
launch from its first window (``app.py``), and for any scripted run while it
runs (``uiscript/unanswered_dialog_guard.py``). While it is on, every window is
shown without activating (the app-wide filter in ``auto_center.py`` calls
:func:`mark_show_without_activating`), and :func:`bring_to_front`, the one place
the app asks for the front, does nothing.

Split out of ``centering.py`` to keep that module about placing dialogs.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

log = logging.getLogger(__name__)

#: True while windows must appear WITHOUT taking focus or jumping to the front:
#: a `--run-script` launch, and any scripted run while it runs (the owner,
#: 2026-11-24: *"they should run on their own ... and also not interrupt a user
#: with bringing windows and things to the front"*). A scripted run opens and
#: closes dozens of dialogs; with this off, each one took the keyboard from
#: whatever the person was doing in another program. A plain module flag, read
#: and written on the GUI thread only. Set through :func:`present_quietly`.
_present_quietly: bool = False

#: The window property Qt's X11 (xcb) plugin reads at the moment it maps a
#: window: true sends `_NET_WM_USER_TIME` 0, which tells the window manager
#: "this window was not asked for by a click; do not give it focus". It is how
#: `Qt.WA_ShowWithoutActivating` reaches the window manager, set here directly
#: as well because the attribute alone is copied to the window only when the
#: native window is created, and a dialog shown a second time already has one.
SHOW_WITHOUT_ACTIVATING_PROPERTY: str = "_q_showWithoutActivating"


def present_quietly(enabled: bool) -> None:
    """Turn quiet presentation on or off for every window shown from now on."""
    global _present_quietly  # one process-wide switch, GUI thread only
    if enabled != _present_quietly:
        log.info(
            "windows now %s",
            "open without taking focus or coming to the front (a scripted run)"
            if enabled
            else "open normally, in front and focused",
        )
    _present_quietly = enabled


def presenting_quietly() -> bool:
    """Whether windows are being shown without taking focus (see the flag)."""
    return _present_quietly


def mark_show_without_activating(widget: QWidget) -> None:
    """In quiet mode, make ``widget`` appear without taking focus. Never raises.

    Called from the window's Show event, which Qt delivers before it maps the
    window, so the window manager hears it in time (`stacking.py` relies on the
    same ordering). Does nothing outside quiet mode.
    """
    if not _present_quietly:
        return
    try:
        widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        handle = widget.windowHandle()
        if handle is not None:
            handle.setProperty(SHOW_WITHOUT_ACTIVATING_PROPERTY, True)
    except RuntimeError:
        # A wrapper whose C++ object is already gone: nothing left to show.
        log.debug("could not mark a window whose C++ side is already gone")


def bring_to_front(widget: QWidget) -> None:
    """Raise ``widget`` and give it focus, except in quiet mode. Never raises.

    The one place the app asks for the front. In quiet mode it does nothing:
    the window is already shown (and stacked above the window it blocks, by
    `stacking.py`), and taking the keyboard from another program is exactly
    what a scripted run must not do.
    """
    if _present_quietly:
        return
    try:
        widget.raise_()
        widget.activateWindow()
    except RuntimeError:
        log.debug("could not raise a window whose C++ side is already gone")
