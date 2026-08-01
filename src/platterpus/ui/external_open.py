"""Hand a path to the desktop — and say so when the desktop won't take it.

``QDesktopServices.openUrl`` **returns a bool**, and that bool is the only
warning you get. It is False when nothing on the system claims the URL: no file
manager wired up, no application associated with ``.log``/``.cue``/``.json``, a
portal that declined. On a fresh KDE that is the *normal* state for a bare
``.log``, not an exotic one.

Throwing that bool away turns the button into a coin flip: it works on a
machine with the association and does nothing at all on one without — the user
clicks, the window sits there, and there is no error, no log line, nothing to
report. That is the "may or may not work" the maintainer hit, and it is the
same failure the "Open rip folder did nothing after I force-cancelled" report
was (see :meth:`RipProgress.begin_rip`).

The window's Help → Open logs folder already did the right thing: check the
bool, and if the desktop declined, show the path so the user can paste it into
Dolphin. It did it *inline*, so the two buttons in the rip pane and the
viewer's own "Open externally…" never got it. This module is that one
behaviour, in one place, for every caller — the same "enforce a rule across the
codebase, not at the place it was learned" lesson as the QThread sweep
(``docs/testing.md`` §5.o).

Pure UI glue: no I/O of its own, no blocking work. ``openUrl`` spawns the
handler and returns immediately, so it is safe on the GUI thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget

log = logging.getLogger(__name__)

# Matches QDesktopServices.openUrl's shape. Injected everywhere so tests never
# launch a real file manager.
OpenUrlFn = Callable[[QUrl], bool]


def open_path_externally(
    path: Path,
    *,
    parent: QWidget | None = None,
    open_url: OpenUrlFn | None = None,
    what: str = "item",
) -> bool:
    """Ask the desktop to open ``path``; report it honestly if it won't.

    Returns True when the desktop accepted the URL. On False the user gets a
    dialog naming ``what`` and showing the full path to copy — a path they can
    act on beats a button that does nothing — and the refusal is written to the
    log so a bug report carries it.

    ``parent`` may be None (the dialog is then unparented, which is fine; it is
    still modal to the app). ``what`` is the human noun for the thing being
    opened, e.g. "rip folder", "log file" — it is used in the dialog title and
    body, so keep it lower-case and short.
    """
    opener: OpenUrlFn = open_url or QDesktopServices.openUrl
    url = QUrl.fromLocalFile(str(path))
    if opener(url):
        return True
    # Not an exception — the desktop declining is an ordinary, recoverable
    # state, and the recovery is "here is the path". Logged at warning because
    # a user reporting "the button does nothing" needs this line to exist.
    log.warning("desktop declined to open %s: %s", what, path)
    QMessageBox.information(
        parent,
        f"Open {what}",
        f"Your {what} is here:\n{path}\n\n"
        "(Nothing on this system is set up to open it automatically — copy "
        "the path above into Files/Dolphin.)",
    )
    return False
