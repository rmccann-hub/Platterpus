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

    Matches on the base class named in the `class X(...)` line rather than by
    importing every UI module, so it needs no QApplication and cannot be defeated
    by an import that happens to fail in a headless container.
    """
    import re
    from pathlib import Path

    ui_root = Path(__file__).resolve().parents[1] / "src" / "platterpus" / "ui"
    pattern = re.compile(r"^class (?P<name>\w+)\(QDialog\):", re.MULTILINE)
    offenders: list[str] = []
    scanned = 0
    for path in sorted(ui_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        scanned += 1
        for match in pattern.finditer(text):
            name = match.group("name")
            # `CenteredDialog` IS the base; it is the one legitimate subclass.
            if name == "CenteredDialog":
                continue
            rel = path.relative_to(ui_root.parents[2])
            offenders.append(f"{rel}: class {name}(QDialog)")
    # Floor: a rglob that stopped matching would report "no offenders" forever.
    assert scanned >= 15, f"only scanned {scanned} UI modules — the glob is broken"
    assert not offenders, (
        "these dialogs subclass QDialog directly, so they inherit neither the "
        "centring nor the presented/closed log lines:\n  " + "\n  ".join(offenders)
    )
