# SPDX-License-Identifier: GPL-3.0-only
"""Help → Copy diagnostics: the copyable surface the UI did not have.

An audit (2026-08-04) found **no** export, bundle or copy-diagnostics action anywhere
in the UI — the only clipboard call in the whole tree copied a *package search
string* — and the one place a cyanrip fatal is ever displayed could not be selected
with a mouse.

Most of these test :func:`build_diagnostics_text`, which is pure: the rendering is
what a user pastes into a bug report, and it should be assertable without a widget.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from platterpus import __version__, diagnostics
from platterpus.paths import LOG_PATH
from platterpus.ui.dialogs.diagnostics_dialog import (
    DiagnosticsDialog,
    build_diagnostics_text,
)


@pytest.fixture(autouse=True)
def _clean_collector() -> None:
    diagnostics.clear()
    yield
    diagnostics.clear()


def test_the_report_names_both_versions_and_the_log_path() -> None:
    """A support question is about the *pair*, and the reader needs somewhere to go.

    CLAUDE.md rule 12: a round approves a pin for a named app version, so a report
    naming only one half is not answering the question that was asked.
    """
    text = build_diagnostics_text()
    assert __version__ in text
    assert "cyanrip" in text
    assert str(LOG_PATH) in text
    # The environment is the first question of every bug report.
    assert "--- Environment ---" in text
    assert "python" in text


def test_recorded_diagnostics_appear_with_argv_exit_code_and_detail() -> None:
    """The four facts CLAUDE.md's completeness rule names must all be renderable."""
    diagnostics.record_command_failure(
        "flac.verify_failed",
        "flac --test",
        ["flac", "--test", "/x/01.flac"],
        1,
        "01.flac: ERROR while decoding data\n",
        where="test",
    )
    text = build_diagnostics_text()

    assert "flac.verify_failed" in text
    assert "exit code: 1" in text
    assert "flac --test /x/01.flac" in text
    assert "ERROR while decoding data" in text
    assert "errors: 1" in text


def test_an_unreaped_child_reads_as_no_exit_code_never_as_zero() -> None:
    """Tri-state, in the *rendered* text as well as in the JSON.

    This is the third surface that has to get it right (log line, report block, this)
    and the reason they all read from one collector: `exit code: 0` for a child that
    was never reaped is a confident wrong answer.
    """
    diagnostics.error(
        "ripper.unreapable_child",
        "the ripper could not be reaped",
        tool="cyanrip",
        argv=["cyanrip", "-d", "/dev/sr0"],
        exit_code=None,
    )
    text = build_diagnostics_text()
    assert "exit code: none (no child was reaped)" in text
    assert "exit code: 0" not in text


def test_an_empty_collector_does_not_read_as_a_clean_bill_of_health() -> None:
    """ "Nothing recorded" and "everything verified" are different claims.

    The same distinction the report's `issues: []` needed, on the surface a user
    actually pastes. An empty section with no sentence would be read as the second.
    """
    text = build_diagnostics_text()
    assert "nothing recorded this session" in text
    assert "not that everything was verified" in text


def test_the_report_says_when_dependencies_were_never_probed() -> None:
    """A missing dependency section is "the launch check has not run", which is a
    real answer and reads nothing like "no dependencies"."""
    text = build_diagnostics_text()
    assert "--- Dependencies ---" in text
    assert "not probed yet this session" in text


def test_rendering_never_raises_on_a_hostile_diagnostic() -> None:
    """A diagnostics view that cannot open is worse than none: it fails exactly when
    the user is already trying to report a failure."""

    class _Hostile:
        def __str__(self) -> str:
            raise RuntimeError("boom")

    diagnostics.error("internal.unexpected_exception", "odd", detail=_Hostile())
    text = build_diagnostics_text()  # must not raise
    assert "=== Platterpus diagnostics ===" in text


def test_the_dialog_is_readonly_selectable_and_copies(qapp: QApplication) -> None:
    diagnostics.warning("ctdb.query_failed", "CTDB was unreachable")
    dialog = DiagnosticsDialog()
    try:
        assert dialog._text.isReadOnly()
        assert "ctdb.query_failed" in dialog.text()

        dialog._on_copy()
        clipboard = QApplication.clipboard()
        if clipboard is not None:  # headless CI may have none
            assert "ctdb.query_failed" in clipboard.text()
            assert dialog._copied_label.text() == "Copied."
    finally:
        dialog.deleteLater()


def test_a_missing_clipboard_says_so_rather_than_appearing_to_work(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A copy button that silently does nothing makes the user click it again — the
    same ambiguity this whole subsystem exists to remove, in miniature."""
    dialog = DiagnosticsDialog()
    try:
        monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: None))
        dialog._on_copy()
        assert "No clipboard" in dialog._copied_label.text()
    finally:
        dialog.deleteLater()
