"""A modal dialog must leave a trace: presented, and closed with what result.

**The bug this pins.** The maintainer closed Platterpus mid-session on
2026-08-05 because it *"looked hung"*. The app was in fact waiting on the
MusicBrainz release picker — four candidates, a modal dialog, and a **96-second
silence in the log** (19:36:41 → 19:38:17) with the main window still reading
``MusicBrainz match: 4 matches found — pick one``.

The mechanism first suspected (a modal swallowing the picker) is *impossible*:
the MB result arrives as a queued cross-thread signal and a nested Qt event loop
still delivers those. The real finding is smaller and worse — the picker's call
site logged **nothing on any branch**: not opened, not waiting, not accepted, not
cancelled. So a user reading the picker and an app genuinely wedged produced
byte-identical logs, and the artifact could not answer even the first question:
*was the dialog ever put on screen?*

That is why the show/close lines live on ``CenteredDialog`` — the shared base
every dialog in the app inherits — and not only at the call site that was found
wanting. ``docs/testing.md`` §5.o: enforce a rule across the codebase, not at the
place it was learned.
"""

from __future__ import annotations

import logging

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.adapters.musicbrainz_client import ReleaseSummary
from platterpus.ui.dialogs.centering import CenteredDialog
from platterpus.ui.release_picker import ReleasePickerDialog

# --- The shared base ------------------------------------------------------


def test_showing_a_dialog_logs_that_it_was_presented(
    qapp: QApplication, caplog: pytest.LogCaptureFixture
) -> None:
    """`showEvent` fires when Qt actually maps the window.

    That makes this line *evidence the dialog reached the screen* — a stronger
    claim than a log line before `exec()`, which only proves we asked.
    """
    dialog = CenteredDialog()
    dialog.setWindowTitle("Pick something")
    with caplog.at_level(logging.INFO):
        dialog.show()
        qapp.processEvents()
    presented = [r for r in caplog.records if "dialog presented" in r.getMessage()]
    assert presented, "showing a dialog logged nothing"
    message = presented[0].getMessage()
    assert "CenteredDialog" in message  # which dialog
    assert "Pick something" in message  # and which prompt
    assert presented[0].levelno >= logging.INFO, (
        "a DEBUG line does not reach the log of the user who cannot tell a "
        "prompt from a freeze"
    )
    dialog.close()


@pytest.mark.parametrize(
    ("closer", "expected"),
    [
        ("accept", "accepted"),
        # Qt maps Esc and the window-manager close button onto Rejected, so these
        # two are genuinely the same code and the wording says so rather than
        # picking one of them.
        ("reject", "rejected or closed"),
        ("close", "rejected or closed"),
    ],
)
def test_closing_a_dialog_logs_how_it_closed(
    qapp: QApplication,
    caplog: pytest.LogCaptureFixture,
    closer: str,
    expected: str,
) -> None:
    """Accept, reject and the window-manager close all funnel through `done`.

    Parametrised over all three because a pair of `accepted`/`rejected` signal
    connections — the obvious alternative — would miss the third.
    """
    dialog = CenteredDialog()
    dialog.setWindowTitle("Pick something")
    dialog.show()
    qapp.processEvents()
    with caplog.at_level(logging.INFO):
        getattr(dialog, closer)()
    closed = [r for r in caplog.records if "dialog closed" in r.getMessage()]
    assert closed, f"{closer}() logged nothing"
    assert expected in closed[0].getMessage()


def test_the_release_picker_inherits_the_lifecycle_lines(
    qapp: QApplication, caplog: pytest.LogCaptureFixture
) -> None:
    """The specific dialog the report was about, not just the base class."""
    releases = [
        ReleaseSummary(mbid=f"mbid-{i}", title=f"Album {i}", artist_credit="Artist")
        for i in range(4)
    ]
    dialog = ReleasePickerDialog(releases)
    with caplog.at_level(logging.INFO):
        dialog.show()
        qapp.processEvents()
        dialog.reject()
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "dialog presented" in text
    assert "ReleasePickerDialog" in text
    assert "dialog closed" in text


# The call-site half of this fix — the four branches of the picker's own logging —
# lives in `tests/test_ui_main_window.py`, next to the `teardown_threads` fixture
# that builds a real MainWindow with its threads stopped. Named here so the two
# halves are findable from each other: see
# `test_multiple_candidates_log_the_wait_before_it_starts` and its three siblings.


# --- The sweep: no dialog may opt out -------------------------------------


def test_every_dialog_in_the_app_inherits_the_logging_base() -> None:
    """A straight `QDialog` subclass silently opts out of the lifecycle lines.

    Derived from the source rather than from a list of the dialogs we know about,
    because this rule's whole failure mode is *the one that was missed*. It found
    one on the day it was written: `DiagnosticsDialog` — a **diagnostics** window
    that left no trace of having been opened, which is the joke telling itself.

    Matches on the base classes of each `class` statement, read from the AST,
    rather than by importing every UI module, so it needs no QApplication and
    cannot be defeated by an import that happens to fail in a headless container.

    **Why the AST and not a regex (2026-09-25).** The first version matched
    ``^class X(QDialog):`` literally, so its candidate set was *provably* empty
    once every dialog had been migrated: the only line of that shape left in the
    tree was `CenteredDialog` itself, which it skipped. And the shapes it could
    not see were the ordinary ones — ``class X(QtWidgets.QDialog)``,
    ``class X(QDialog, SomeMixin)``, a base list wrapped across lines. Each of
    those opts a dialog out exactly as well, and each passed. (Revert-probed:
    rebasing `FileViewerDialog` onto either of the first two passed the old test.)

    So the population is now **every class statement in the package** and the
    question is "does any base name QDialog, bare or dotted", and the check owes
    two floors, because a sweep that finds nothing to object to must also prove
    it found the things it is about:

    * it must see `CenteredDialog` itself as a direct `QDialog` subclass — the
      one legitimate match, and the proof the matcher can match at all;
    * it must see the dialogs that DO comply. 15 classes named `CenteredDialog`
      as a base when measured (2026-09-25); the floor sits a little below so a
      deleted dialog does not trip it, while a matcher that stopped seeing
      class bases does.

    Scope, stated rather than implied: `QDialog` only. Subclassing a *concrete*
    Qt dialog (`QMessageBox`, `QFileDialog`) is not policed here — none exists
    today, and such a class cannot also inherit `CenteredDialog`, so it would
    need its own rule rather than this one.
    """
    import ast
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[1] / "src" / "platterpus"

    def _base_name(node: ast.expr) -> str:
        """`QDialog` for both `QDialog` and `QtWidgets.QDialog`; "" otherwise."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    offenders: list[str] = []
    roots: list[str] = []
    compliant: list[str] = []
    scanned = 0
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        scanned += 1
        rel = path.relative_to(src_root.parents[1])
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [_base_name(b) for b in node.bases]
            if "CenteredDialog" in bases:
                compliant.append(node.name)
            if "QDialog" not in bases:
                continue
            # `CenteredDialog` IS the base; it is the one legitimate subclass.
            if node.name == "CenteredDialog":
                roots.append(f"{rel}")
                continue
            offenders.append(f"{rel}:{node.lineno}: class {node.name}(...QDialog...)")
    # Floor: a rglob that stopped matching would report "no offenders" forever.
    # 173 modules in the package when measured (2026-09-25).
    assert scanned >= 150, f"only scanned {scanned} modules — the glob is broken"
    assert len(roots) == 1, (
        f"expected exactly one direct QDialog subclass named CenteredDialog, found "
        f"{roots or 'none'} — either the base moved, or the matcher can no longer "
        "see a QDialog base at all, and the offender check below is measuring nothing"
    )
    assert len(compliant) >= 12, (
        f"only {len(compliant)} classes inherit CenteredDialog (15 when measured, "
        "2026-09-25) — the sweep is not seeing the population it polices"
    )
    assert not offenders, (
        "these dialogs subclass QDialog directly, so they inherit neither the "
        "centring nor the presented/closed log lines:\n  " + "\n  ".join(offenders)
    )


def test_the_runner_names_the_release_picker_by_its_real_title(qapp: object) -> None:
    """Two descriptions of one string, tied so they cannot drift.

    `uiscript.runner._RELEASE_PICKER_TITLE` exists so a blocked `rip` can point the
    operator at `pick-release` instead of the generic `ok` / `cancel` — which is
    *wrong* for this dialog, because `answer-dialog` presses a button and the picker
    needs a row selected. Reported from the rig on 2026-08-26, where the generic
    message sent someone to the wrong verb: a diagnosis accurate about the problem
    and wrong about the remedy.

    The constant is a literal rather than an import, so `rip`'s guard does not pull
    a widget module in on every step. That is only safe with this test: if the
    dialog is ever retitled, the guard would silently fall back to the generic
    advice and nobody would notice, because the fallback still *reads* correctly.
    """
    from platterpus.uiscript.runner import _RELEASE_PICKER_TITLE  # noqa: PLC0415

    dialog = ReleasePickerDialog([])
    try:
        assert dialog.windowTitle() == _RELEASE_PICKER_TITLE, (
            f"the picker's title is {dialog.windowTitle()!r} but the runner "
            f"compares against {_RELEASE_PICKER_TITLE!r}, so a blocked rip would "
            "give the generic ok/cancel advice — which cannot answer this dialog"
        )
    finally:
        dialog.deleteLater()


def test_both_blocked_step_messages_send_the_operator_to_pick_release(
    qapp: object,
) -> None:
    """Two sites gave the same wrong remedy; fix both, and assert both.

    `rip`'s guard and `wait-for-rip`'s no-worker branch each name a verb for the
    dialog they found blocking. Both said `answer-dialog` unconditionally, which
    cannot answer the release picker: it presses a button, and the picker needs a
    row selected. Reported from the rig 2026-08-26.

    Asserted by reading the source of both handlers rather than by driving a modal,
    because the point is that **neither** site is left behind — `docs/testing.md`
    §5.o, a rule enforced where it was learned is not enforced. A behavioural test
    of one handler would have passed while the other stayed wrong, which is exactly
    the state this replaces.
    """
    import inspect  # noqa: PLC0415

    from platterpus.uiscript import runner as runner_mod  # noqa: PLC0415

    handlers = {
        "rip": runner_mod.ScriptRunner._do_rip,
        "wait-for-rip": runner_mod.ScriptRunner._do_wait_for_rip,
    }
    for name, fn in handlers.items():
        src = inspect.getsource(fn)
        assert "_RELEASE_PICKER_TITLE" in src, (
            f"`{name}` does not special-case the release picker, so a blocked run "
            "there still tells the operator to use `answer-dialog` — which cannot "
            "resolve a dialog that needs a row selected"
        )
        assert "pick-release" in src, (
            f"`{name}` names the picker but never names `pick-release`, so its "
            "advice still points at the wrong verb"
        )
