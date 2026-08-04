"""Tests for the host-setup wizard dialog.

We drive the render slots (`_on_step`, `_on_finished`) directly with a fake
host (no QThread, no real commands), so the dialog's display logic is tested
without touching Distrobox/podman.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.ui.host_setup_dialog import HostSetupDialog


class _FakeHost:
    """Minimal stand-in for HostSetup (duck-typed)."""

    def __init__(self, ready: bool) -> None:
        self._ready = ready

    def is_ready(self) -> bool:
        return self._ready

    def run(self, progress=None, cancelled=None):  # pragma: no cover - unused here
        return []


def _dialog(qapp: QApplication, ready: bool = True) -> HostSetupDialog:
    return HostSetupDialog(host_setup=_FakeHost(ready))


def test_intro_mentions_cyanrip(qapp: QApplication) -> None:
    # cyanrip is the sole backend the wizard installs.
    assert "cyanrip" in _dialog(qapp)._intro.text()


def test_on_step_appends_formatted_line(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._on_step(
        StepResult("distrobox", "Distrobox", StepStatus.DONE, "already present")
    )
    text = dialog._results.toPlainText()
    assert "Distrobox" in text
    assert "already present" in text
    assert "✓" in text


def test_on_step_running_updates_status_not_log(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._on_step(
        StepResult(
            "tools",
            "flac + metaflac (in container)",
            StepStatus.RUNNING,
            "working… this can take a few minutes",
        )
    )
    # RUNNING shows what's happening in the status line, not the results log.
    assert "flac + metaflac" in dialog._status_label.text()
    assert "⏳" in dialog._status_label.text()
    assert dialog._results.toPlainText() == ""


def test_on_finished_all_already_present(qapp: QApplication) -> None:
    dialog = _dialog(qapp, ready=True)
    dialog._on_finished(
        [
            StepResult("distrobox", "Distrobox", StepStatus.DONE, "already present"),
            StepResult("export", "Export", StepStatus.DONE, "already present"),
        ]
    )
    assert "already set up" in dialog._status_label.text().lower()


def test_on_step_ignored_while_closing(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._closing = True
    dialog._on_step(StepResult("x", "X", StepStatus.RAN))
    assert dialog._results.toPlainText() == ""


def test_on_finished_ready_reports_success(qapp: QApplication) -> None:
    dialog = _dialog(qapp, ready=True)
    seen: list[bool] = []
    dialog.setup_finished.connect(seen.append)

    dialog._on_finished([StepResult("export", "Export", StepStatus.RAN)])

    assert "complete" in dialog._status_label.text().lower()
    assert dialog._setup_button.text() == "Re-run setup"
    assert seen == [True]


def test_a_failed_step_never_reads_as_setup_complete(qapp: QApplication) -> None:
    """REGRESSION (real-user report, 2026-08-04, v0.6.4b1).

    The wizard rendered "✓ Setup complete — the ripping tools are installed. You
    can rip now." and, two lines below it, "✗ Platterpus fork of cyanrip —
    installed cyanrip does not identify as the pinned fork build". Same run.

    Cause: the headline came from `is_ready()` alone, which asks *"is a ripper
    reachable on the host?"* (`cyanrip_exported() and flac_exported()`). The
    PREVIOUS fork build was still exported, so it answered True — correctly, to a
    different question — and the verdict never consulted `results`, so a FAILED
    step could not affect it.

    **This exact combination — ready=True WITH a failed step — was untested.** The
    pre-existing failure test uses ready=False, where `is_ready()` happens to agree
    with the results, so it could never catch this. A test that only exercises the
    case where two signals agree cannot detect that one of them is being read.
    """
    dialog = _dialog(qapp, ready=True)  # a working ripper IS exported

    dialog._on_finished(
        [
            StepResult("export", "Export tools to ~/.local/bin", StepStatus.DONE),
            StepResult(
                "fork",
                "Platterpus fork of cyanrip (build + export)",
                StepStatus.FAILED,
                "installed cyanrip does not identify as the pinned fork build "
                "(platterpus-fork-g9003e6f)",
            ),
        ]
    )

    text = dialog._status_label.text()
    assert "Setup complete" not in text, (
        f"a FAILED step still reads as success: {text!r}"
    )
    # The failure has to be named, not merely not-claimed-successful.
    assert "Platterpus fork of cyanrip" in text
    assert "9003e6f" in text, "the message drops the detail the user needs"
    # And the OTHER true half stays: they can still rip, with the older build.
    assert "can rip" in text, (
        "a user with a working ripper must not be told setup wholly failed — that "
        "is the opposite error, and just as wrong"
    )


def test_on_finished_failure_shows_failed_step(qapp: QApplication) -> None:
    dialog = _dialog(qapp, ready=False)
    seen: list[bool] = []
    dialog.setup_finished.connect(seen.append)

    dialog._on_finished(
        [
            StepResult("distrobox", "Distrobox", StepStatus.RAN),
            StepResult(
                "backend",
                "Container backend (podman)",
                StepStatus.FAILED,
                "install it manually and retry",
            ),
        ]
    )

    text = dialog._status_label.text()
    assert "Container backend" in text
    assert "manually" in text
    assert seen == [False]


def test_step_starts_and_finish_are_announced(qapp: QApplication, monkeypatch) -> None:
    """Setup runs for minutes with focus parked on a button — each step start
    and the final outcome must be audible without focus (a11y gap #4)."""
    heard: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.host_setup_dialog.announce",
        lambda _source, message: heard.append(message) or True,
    )
    dialog = _dialog(qapp)

    dialog._on_step(StepResult("container", "Create container", StepStatus.RUNNING))
    dialog._on_finished([StepResult("container", "Create container", StepStatus.DONE)])

    assert any("Create container" in m for m in heard)
    assert heard[-1] == dialog._status_label.text()
