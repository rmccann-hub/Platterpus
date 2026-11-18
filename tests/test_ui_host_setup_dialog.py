"""Tests for the host-setup wizard dialog.

We drive the render slots (`_on_step`, `_on_finished`) directly with a fake
host (no QThread, no real commands), so the dialog's display logic is tested
without touching Distrobox/podman.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from test_labels_state_their_text_format import _shown

from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.ui.host_setup_dialog import HostSetupDialog, ripper_update_copy


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
    # The step's own words live in the details line since the F3 rewording (UX
    # review of 0.7.127): a plain sentence leads, the raw text follows. Still on
    # screen, word for word, which is what this assertion protects.
    details = dialog._details_label.text()
    assert not dialog._details_label.isHidden()
    assert "9003e6f" in details, "the message drops the detail the user needs"
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
    # The mapped sentence leads (F3): a failed "backend" step means no Podman,
    # and the action says what to install. The raw text follows in the details.
    assert "Install Podman" in text
    assert "manually" in dialog._details_label.text()
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


def test_the_intro_shows_its_list_as_a_list(qapp: QApplication) -> None:
    """The intro is markup (its `<b>cyanrip</b>`), and markup reads `\\n` as a space.

    Until 2026-10-05 its line breaks were `\\n`, so the three-item list showed as
    one run-on paragraph (found 2026-09-28, recorded on the TASKS row for labels
    given text by `setText`). What the user sees is read the way QLabel renders
    it (`_shown`), so the test is about the rendering, not the source.
    """
    dialog = _dialog(qapp)
    shown = _shown(dialog._intro)
    assert dialog._intro.textFormat() == Qt.TextFormat.RichText
    assert "<b>" not in shown and "<br>" not in shown, shown
    assert (
        "no terminal needed:\n\n"
        "• installs Distrobox + a container runtime (if missing)\n"
        "• creates the 'ripping' container and installs cyanrip + flac into it\n"
        "• makes the ripping tools available to this app\n\n"
        "It takes a few minutes"
    ) in shown, shown


def test_the_ripper_update_intro_keeps_its_paragraphs_and_its_pin(
    qapp: QApplication,
) -> None:
    """The other `SetupCopy` intro: three paragraphs, and the pin shown as written.

    The pin names a build the user picked, so `ripper_update_copy` escapes it into
    the markup; a pin shaped like a tag must come out exactly as typed.
    """
    pin = "abc<1234>&co"
    dialog = HostSetupDialog(host_setup=_FakeHost(False), copy=ripper_update_copy(pin))
    shown = _shown(dialog._intro)
    assert shown.startswith(
        f"Installing cyanrip build {pin}.\n\nPlatterpus builds the ripper"
    ), shown
    assert "rows below say which.\n\nThe build is verified" in shown, shown
    assert dialog.windowTitle() == "Updating cyanrip"


# --- F3 (UX review of 0.7.127): failure wording, Open log, timing -----------
#
# The review's screenshot showed `Setup stopped at "Distrobox": command not found:
# pkexec ([Errno 2] …)` as the headline, the log path as plain text, and an intro
# promising "usually instant" for a run that builds the ripper from source.


def test_a_missing_pkexec_leads_with_a_plain_sentence_and_keeps_the_raw_text(
    qapp: QApplication,
) -> None:
    """REGRESSION (F3): the headline is the mapped sentence, not the errno."""
    dialog = _dialog(qapp, ready=False)
    raw = "command not found: pkexec ([Errno 2] No such file or directory: 'pkexec')"
    dialog._on_finished([StepResult("distrobox", "Distrobox", StepStatus.FAILED, raw)])

    status = dialog._status_label.text()
    # The plain sentence and the action lead…
    assert "couldn't ask for your password" in status, status
    assert "Install Distrobox" in status, status
    assert "Re-run setup" in status, status
    # …and the raw errno text is NOT the headline any more.
    assert "Errno" not in status, status
    # It is kept, word for word, in the details line — never dropped.
    assert not dialog._details_label.isHidden()
    assert raw in dialog._details_label.text()
    assert dialog._details_label.textFormat() == Qt.TextFormat.PlainText


def test_the_retry_label_in_the_action_is_the_button_on_screen(
    qapp: QApplication,
) -> None:
    """The ripper-update copy's retry button says "Try again", so must the action."""
    dialog = HostSetupDialog(host_setup=_FakeHost(False), copy=ripper_update_copy("x"))
    dialog._on_finished(
        [
            StepResult(
                "cyanrip_fork",
                "Platterpus fork of cyanrip",
                StepStatus.FAILED,
                "ninja: build stopped: subcommand failed.",
            )
        ]
    )
    status = dialog._status_label.text()
    assert "Try again" in status, status
    assert "Re-run setup" not in status, status


def test_a_failure_offers_open_log_and_it_opens_the_app_log(
    qapp: QApplication,
) -> None:
    """The log path was plain text; now an Open log button hands it to the desktop."""
    from platterpus.paths import LOG_PATH

    opened: list[str] = []

    def _fake_open(url: object) -> bool:
        opened.append(url.toLocalFile())  # type: ignore[attr-defined]
        return True

    dialog = HostSetupDialog(host_setup=_FakeHost(False), open_url=_fake_open)
    assert dialog._open_log_button.isHidden(), "Open log must wait for a failure"
    dialog._on_finished(
        [StepResult("backend", "Container backend (podman)", StepStatus.FAILED, "x")]
    )
    assert not dialog._open_log_button.isHidden()
    dialog._open_log_button.click()
    assert opened == [str(LOG_PATH)]
    # The path is named on the button itself (and, on a desktop that will not
    # open it, in the dialog `open_path_externally` shows instead).
    assert str(LOG_PATH) in dialog._open_log_button.toolTip()


def test_open_log_refused_by_the_desktop_names_the_path(
    qapp: QApplication, monkeypatch
) -> None:
    """A desktop with nothing to open a .txt with: the user still gets the path."""
    from platterpus.paths import LOG_PATH

    told: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.external_open.message_boxes.information",
        lambda _parent, _title, text: told.append(text),
    )
    dialog = HostSetupDialog(host_setup=_FakeHost(False), open_url=lambda _u: False)
    dialog._on_finished(
        [StepResult("backend", "Container backend (podman)", StepStatus.FAILED, "x")]
    )
    dialog._open_log_button.click()
    assert told and str(LOG_PATH) in told[0]


def test_a_success_shows_no_failure_details(qapp: QApplication) -> None:
    dialog = _dialog(qapp, ready=True)
    dialog._on_finished([StepResult("export", "Export", StepStatus.RAN)])
    assert dialog._details_label.isHidden()
    assert dialog._open_log_button.isHidden()


def test_the_intro_gives_one_honest_estimate(qapp: QApplication) -> None:
    """REGRESSION (F3): "usually instant" contradicted the README's few minutes.

    The README (*Easiest*, step 3) says "It takes a few minutes: it creates the
    container and builds the ripper". The dialog says the same, and no longer
    promises "instant" on any system: the container and the build are needed on
    Bazzite too.
    """
    dialog = _dialog(qapp)  # bound: a temporary is collected before _shown reads it
    shown = _shown(dialog._intro)
    assert "instant" not in shown, shown
    assert "takes a few minutes: it creates the container and builds the ripper" in (
        shown
    ), shown


def test_the_elapsed_time_shows_while_running_and_hides_after(
    qapp: QApplication, monkeypatch
) -> None:
    """Setup's bar is indeterminate; a moving clock shows the window is alive.

    Driven without the worker thread: the start slot's bookkeeping is called
    directly with `start_worker_thread` stubbed out, and the clock is faked
    (on the module's own `time` name, so nothing else's clock moves).
    """
    from types import SimpleNamespace

    import platterpus.ui.host_setup_dialog as hsd

    monkeypatch.setattr(hsd, "start_worker_thread", lambda *_a, **_k: None)
    now = [1000.0]
    monkeypatch.setattr(hsd, "time", SimpleNamespace(monotonic=lambda: now[0]))
    dialog = _dialog(qapp, ready=True)
    assert dialog._elapsed_label.isHidden()

    dialog._on_setup_clicked()
    assert not dialog._elapsed_label.isHidden()
    assert dialog._elapsed_timer.isActive()
    assert dialog._elapsed_label.text() == "Elapsed: 0:00"

    now[0] += 125.0
    dialog._tick_elapsed()
    assert dialog._elapsed_label.text() == "Elapsed: 2:05"

    # Stop the real QThread object the slot created but never started.
    dialog._thread = None
    dialog._worker = None
    now[0] += 10.0
    dialog._on_finished([StepResult("export", "Export", StepStatus.RAN)])
    assert not dialog._elapsed_timer.isActive()
    assert dialog._elapsed_label.isHidden()


def test_format_elapsed() -> None:
    from platterpus.ui.host_setup_dialog import format_elapsed

    assert format_elapsed(0) == "0:00"
    assert format_elapsed(59.9) == "0:59"
    assert format_elapsed(61) == "1:01"
    assert format_elapsed(3725) == "1:02:05"
    assert format_elapsed(-5) == "0:00"
    assert format_elapsed(float("nan")) == "0:00"
    assert format_elapsed(float("inf")) == "0:00"
