"""The "button did nothing" class of bug: a thrown-away ``openUrl`` return.

``QDesktopServices.openUrl`` returns False when nothing on the system claims
the URL — no file manager, no application associated with ``.log``. On a fresh
KDE that is the ordinary state for a bare ``.log``, which is *why* the in-app
viewer exists. Three call sites ignored that bool, so on such a desktop the
button was simply inert: no error, no log line, nothing to report. The
maintainer's words were "trying to open the log link may or may not work"
(2026-08-01) — a coin flip decided by whether the machine happens to have an
association.

The window's Help → Open logs folder had always handled it, inline. That is the
recurring shape from ``docs/testing.md`` §5.o: a rule enforced at the one place
it was learned, and nowhere else. These tests hold all four call sites to it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMessageBox

from platterpus.ui.dialogs.file_viewer import FileViewerDialog
from platterpus.ui.external_open import open_path_externally
from platterpus.ui.rip_progress import RipProgress


@pytest.fixture()
def shown(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture the fallback dialog's body instead of showing it modally."""
    bodies: list[str] = []

    def fake_information(_parent: object, _title: str, text: str, *a: object) -> None:
        bodies.append(text)

    monkeypatch.setattr(QMessageBox, "information", fake_information)
    return bodies


def _refusing(url: QUrl) -> bool:
    """An `openUrl` that declines, exactly as a handler-less desktop does."""
    return False


def _accepting(url: QUrl) -> bool:
    return True


# --- the helper itself ------------------------------------------------------


def test_a_successful_open_says_nothing(shown: list[str], tmp_path: Path) -> None:
    assert open_path_externally(tmp_path, open_url=_accepting, what="rip folder")
    assert shown == [], "a working open must not nag"


def test_a_refused_open_shows_the_path_and_logs_it(
    shown: list[str], tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A path the user can paste beats a button that does nothing — and the
    refusal must reach the log file, because "the button does nothing" is
    otherwise an unreportable bug."""
    with caplog.at_level(logging.WARNING):
        ok = open_path_externally(tmp_path, open_url=_refusing, what="rip folder")
    assert ok is False
    assert len(shown) == 1
    assert str(tmp_path) in shown[0], "the user must be given the path"
    assert any("declined to open" in r.getMessage() for r in caplog.records), (
        "a silent refusal is an unreportable bug"
    )


# --- every call site, held to it --------------------------------------------


def test_open_rip_folder_is_not_a_dead_button(
    qapp: QApplication, shown: list[str], tmp_path: Path
) -> None:
    """Regression: the rip pane's Open-folder button dropped the bool.

    This is the same button as the "Open rip folder did nothing after I
    force-cancelled" report — fixed once for the *disabled/None* case, still
    silent for the *desktop-refused* case.
    """
    panel = RipProgress(open_url=_refusing, view_file=lambda _p, _t: None)
    panel.begin_rip(tmp_path, tmp_path / "app.log")
    assert panel._open_folder_button.isEnabled()
    panel._open_folder_button.click()
    assert len(shown) == 1
    assert str(tmp_path) in shown[0]


def test_view_externally_is_not_a_dead_button(
    qapp: QApplication, shown: list[str], tmp_path: Path
) -> None:
    """Regression: the viewer's own escape hatch dropped the bool.

    This is the worst of the three — the viewer exists *because* a .log has no
    handler, which is exactly when openUrl refuses. The escape hatch was dead on
    precisely the systems it was written for.
    """
    f = tmp_path / "Album.log"
    f.write_text("cyanrip log", encoding="utf-8")
    dialog = FileViewerDialog(f, open_url=_refusing, reader=lambda _p: "")
    dialog._open_external_button.click()
    assert len(shown) == 1
    assert str(f) in shown[0]


# --- View log: resolve which file at CLICK time, not at set time ------------


def test_view_log_falls_back_when_the_rip_log_never_appeared(
    qapp: QApplication, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """`set_log_path` deliberately doesn't gate on `.exists()` — the report is
    written moments later, so a set-time check would disable a button that is
    about to be valid. The cost was that `_log_path` could name a file that
    never appeared, and it was preferred unconditionally: the user got an errno
    inside the viewer while the real-time app log sat right there, readable.

    Click time is the one moment the answer is knowable, so that is where the
    choice is now made.
    """
    viewed: list[Path] = []
    live = tmp_path / "app.log"
    live.write_text("live app log", encoding="utf-8")
    panel = RipProgress(view_file=lambda p, _t: viewed.append(p))
    panel.begin_rip(tmp_path, live)
    panel.set_log_path(tmp_path / "Never Written.log")

    with caplog.at_level(logging.WARNING):
        panel._view_log_button.click()

    assert viewed == [live], "the readable log must win over the absent one"
    assert any("not readable" in r.getMessage() for r in caplog.records)


def test_view_log_still_prefers_the_backends_own_log_when_it_exists(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The other side: the fallback must not steal the normal case.

    Once cyanrip's per-track log is on disk it is strictly the better artifact,
    and a fix that quietly downgraded every finished rip to the app log would be
    worse than the bug.
    """
    viewed: list[Path] = []
    live = tmp_path / "app.log"
    live.write_text("live app log", encoding="utf-8")
    real = tmp_path / "Album.log"
    real.write_text("cyanrip 0.9.3", encoding="utf-8")
    panel = RipProgress(view_file=lambda p, _t: viewed.append(p))
    panel.begin_rip(tmp_path, live)
    panel.set_log_path(real)

    panel._view_log_button.click()
    assert viewed == [real]


def test_view_log_during_the_rip_opens_the_app_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """And the during-the-rip case, which is the whole reason the live log is
    wired in: no backend .log exists yet, so the button must still land
    somewhere useful rather than doing nothing."""
    viewed: list[Path] = []
    live = tmp_path / "app.log"
    live.write_text("live app log", encoding="utf-8")
    panel = RipProgress(view_file=lambda p, _t: viewed.append(p))
    panel.begin_rip(tmp_path, live)
    panel._view_log_button.click()
    assert viewed == [live]
