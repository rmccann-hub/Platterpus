"""An application-wide event filter that centres dialogs on the main window.

:class:`~platterpus.ui.dialogs.centering.CenteredDialog` only helps dialogs that
*subclass* it. The most common first-run prompts — the "add to menu" offer, the
shortcut prompt, update prompts — are plain ``QMessageBox`` static calls, which
can't subclass anything and so still popped up on whatever screen the compositor
chose (real-user report on a multi-monitor desktop, 0.4.4). Installing one
filter on the ``QApplication`` catches *every* dialog's first show — including
``QMessageBox`` and ``QFileDialog`` — and centres it over the window the user is
looking at.

Like all our centring, this is best-effort: under native Wayland clients can't
position themselves (the app prefers XWayland, where ``move()`` works), so there
it's a harmless no-op. ``CenteredDialog`` instances are skipped — they already
centre themselves, so we don't fight them.

**How "already centred" is remembered — and why it changed twice.** A dialog
must be placed on its FIRST show only; re-showing it shouldn't yank it back to
the middle after the user dragged it. So something has to remember which dialogs
we've handled. The mark now lives *on the dialog itself* (a Qt dynamic
property), not in a table on the filter — see :data:`CENTERED_PROPERTY` for the
full reasoning and the two earlier designs it replaces.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QDialog, QWidget

from platterpus.ui.dialogs.centering import CenteredDialog, center_on_anchor

#: Name of the Qt *dynamic property* we stamp on a dialog once we have placed it.
#:
#: This is the whole "have I seen this dialog?" mechanism, and it deliberately
#: keeps **no state on the filter at all**. Two earlier designs did, and both
#: were wrong in instructive ways:
#:
#: 1. ``set[int]`` of ``id(obj)`` — **BUG-10**. Dialogs are transient: a
#:    ``QMessageBox`` is built, shown, closed and freed, and CPython promptly
#:    hands the freed address to the *next* object. So a later, brand-new dialog
#:    inherited an earlier one's id, matched the stale entry, and was treated as
#:    "already centred" — i.e. it opened wherever the compositor felt like, which
#:    is the exact bug this filter exists to fix. (Measured, not theoretical: 50
#:    sequential ``QMessageBox`` objects created and dropped in a loop reuse the
#:    *same* id all 50 times, so the old filter centred exactly one of them.)
#:
#: 2. ``weakref.WeakSet`` of the dialogs — it fixed BUG-10, but it **measures the
#:    wrong lifetime**. A PySide QObject is really two objects: the Python
#:    wrapper and the C++ ``QObject``, and they die independently. A weakref is
#:    attached to the *wrapper*, so the WeakSet entry disappears when Python
#:    stops referencing the dialog — not when Qt destroys it. Whenever the C++
#:    side goes first (a parent being deleted, ``deleteLater()``,
#:    ``shiboken6.delete()``), the wrapper lives on as an invalidated husk, the
#:    weakref stays alive, and **the entry silently persists for a dialog that no
#:    longer exists**. That is BUG-10's failure mode arriving by a second route:
#:    stale bookkeeping that can shadow a later dialog. The old test only ever
#:    passed because ``del box`` happened to drop the last *Python* reference —
#:    it never exercised the case the filter actually meets at runtime, where Qt
#:    owns and destroys the dialog.
#:
#:    (For the record, so nobody "fixes" this back: holding a weakref to a PySide
#:    object is *supported* — shiboken gives ``SbkObject`` a ``weakreflist`` and
#:    clears it at a safe point during dealloc. The objection is semantic, not a
#:    crash. Separately, the only way to *prove* an entry had vanished was a
#:    forced ``gc.collect()`` in the test, and on CPython ≤ 3.11 a cyclic
#:    collection can begin inside any C-extension allocation — including partway
#:    through shiboken's multi-step teardown — which makes a suite-wide
#:    ``gc.collect()`` a detonator for unrelated latent damage. CPython 3.12
#:    moved collection to bytecode boundaries, which is why such crashes tend to
#:    show up on the 3.11 leg alone and *look* like they belong to whichever test
#:    called ``gc.collect()``.)
#:
#: A dynamic property has neither failure mode. Qt stores it inside the
#: ``QObject``, so the mark is *born and destroyed with the dialog*: there is no
#: table to go stale, nothing to invalidate, and no id to be recycled — a fresh
#: dialog is always unmarked no matter what address it landed on. It costs one
#: hash lookup, needs no weakrefs, and touches no other object's lifetime.
#:
#: (A plain Python attribute on the wrapper — ``obj._platterpus_centered = True``
#: — would be monkey-patching a foreign object, which the project style forbids,
#: and it can be *lost*: PySide may discard and rebuild a wrapper while the C++
#: object lives on. The Qt property is stored on the C++ side, which is the
#: lifetime we actually mean.)
#:
#: Qt reserves dynamic-property names beginning with ``_q_``; this one is
#: namespaced to the project so it cannot collide with Qt's or another library's.
CENTERED_PROPERTY: str = "_platterpus_centered"


def has_been_centered(dialog: QWidget) -> bool:
    """Return whether *this exact dialog object* has already been placed by us.

    Reads the mark back off the widget. An unmarked widget returns ``None`` from
    ``property()``, which is falsey — so a brand-new dialog is always "not yet
    centred" without us having to pre-register anything.
    """
    try:
        return bool(dialog.property(CENTERED_PROPERTY))
    except RuntimeError:
        # PySide raises RuntimeError("Internal C++ object already deleted") when a
        # Python wrapper outlives its C++ QObject. We can't place a widget that no
        # longer exists, so answer "already handled" and let the caller skip it.
        # Qt only delivers events to live objects, so this shouldn't be reachable
        # — but placement is cosmetic and must never take the application down.
        return True


def mark_as_centered(dialog: QWidget) -> None:
    """Stamp the "we placed this one" mark on *dialog*.

    Setting a dynamic property makes Qt send the widget a
    ``DynamicPropertyChange`` event, which comes straight back through this very
    filter. That is harmless and free: the filter's first test rejects anything
    that isn't a ``Show``.
    """
    try:
        dialog.setProperty(CENTERED_PROPERTY, True)
    except RuntimeError:
        # Same wrapper-outlived-its-C++-object case as above. Failing to record
        # the mark only costs a re-centre if the dialog is ever shown again, so
        # swallowing it is safe — and far better than an exception escaping into
        # Qt's event delivery.
        pass


class DialogCenterFilter(QObject):
    """Centres each top-level dialog over the active window on its first show.

    Deliberately **stateless**: everything it needs to know about a dialog is
    stored on that dialog (see :data:`CENTERED_PROPERTY`). One instance is
    installed on the ``QApplication`` for the whole session, so "no per-dialog
    bookkeeping" also means "nothing that grows for the life of the app".
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 — Qt API
        # Cheapest check first: only Show events are interesting. This is also
        # what makes marking free — the DynamicPropertyChange event that
        # mark_as_centered triggers is rejected right here.
        if event.type() == QEvent.Type.Show and isinstance(obj, QDialog):
            # CenteredDialog already self-centres; don't double-handle it — and
            # don't mark it either, since the mark means "*we* placed this".
            if not isinstance(obj, CenteredDialog) and not has_been_centered(obj):
                mark_as_centered(obj)
                center_on_anchor(obj)
        # Never consume the event — we only observe it.
        return False
