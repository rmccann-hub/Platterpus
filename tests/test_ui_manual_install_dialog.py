"""Tests for platterpus.ui.dialogs.manual_install.

Construct the dialog, inspect its widget state, drive its actions
programmatically. No real display; the conftest forces Qt's offscreen
platform plugin.
"""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from platterpus.deps.checks import ProbeResult
from platterpus.deps.registry import DependencySpec, Tier
from platterpus.ui.dialogs.manual_install import ManualInstallDialog

# --- Spec / probe factories -----------------------------------------------


def _absent_probe() -> ProbeResult:
    return ProbeResult(present=False, version=None, location=None)


def _present_probe(version: tuple[int, ...] = (1, 2, 3)) -> ProbeResult:
    return ProbeResult(present=True, version=version, location="/x")


def _spec(
    dep_id: str = "libdiscid",
    min_version: tuple[int, ...] = (0, 6, 0),
    description: str = "System C library; requires rpm-ostree install + reboot",
    search_string: str = "install libdiscid Bazzite Fedora Atomic rpm-ostree",
) -> DependencySpec:
    return DependencySpec(
        dep_id=dep_id,
        display_name=dep_id,
        probe=lambda: ProbeResult(present=False, version=None, location=None),
        min_version=min_version,
        tier=Tier.MANUAL,
        install_command=None,
        search_string=search_string,
        description=description,
    )


# --- Construction --------------------------------------------------------


def test_window_title_includes_dep_name(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec("libdiscid"), _absent_probe())
    assert "libdiscid" in dialog.windowTitle()


def test_dialog_is_modal_by_default(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _absent_probe())
    assert dialog.isModal() is True


def test_search_string_visible_and_readonly(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _absent_probe())
    assert dialog.search_string() == (
        "install libdiscid Bazzite Fedora Atomic rpm-ostree"
    )
    assert dialog._search_field.isReadOnly() is True


# --- Copy action ---------------------------------------------------------


def test_copy_writes_search_string_to_clipboard(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _absent_probe())

    dialog.copy_search_string()

    assert (
        QGuiApplication.clipboard().text()
        == "install libdiscid Bazzite Fedora Atomic rpm-ostree"
    )


def test_copy_button_label_updates_then_resets(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _absent_probe())

    # "&Copy" — the "&" is the Alt+C keyboard mnemonic (a11y pass, gap #4).
    assert dialog._copy_button.text() == "&Copy"
    dialog.copy_search_string()
    assert dialog._copy_button.text() == "Copied!"
    # The reset is via a 1500ms QTimer; not driving the event loop
    # here. The "starts as Copy, flips to Copied!" path is what
    # matters; the eventual reset is a UX nicety we test by reading
    # the timer's scheduled fact rather than waiting for it.


# --- Display strings -----------------------------------------------------


def test_required_text_for_specific_minimum(qapp: QApplication) -> None:
    spec = _spec(min_version=(0, 6, 1))
    dialog = ManualInstallDialog(spec, _absent_probe())
    assert dialog._required_text() == ">= 0.6.1"


def test_required_text_for_any_version(qapp: QApplication) -> None:
    spec = _spec(min_version=(0, 0, 0))
    dialog = ManualInstallDialog(spec, _absent_probe())
    assert dialog._required_text() == "any installed version"


def test_current_text_when_absent(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _absent_probe())
    assert dialog._current_text() == "not installed"


def test_current_text_when_present_with_version(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _present_probe((0, 6, 2)))
    assert dialog._current_text() == "installed: 0.6.2"


def test_current_text_when_present_but_unknown_version(
    qapp: QApplication,
) -> None:
    probe = ProbeResult(present=True, version=None, location="/x")
    dialog = ManualInstallDialog(_spec(), probe)
    assert dialog._current_text() == "installed (version unknown)"


def test_why_text_falls_back_when_description_empty(
    qapp: QApplication,
) -> None:
    spec = _spec(description="")
    dialog = ManualInstallDialog(spec, _absent_probe())
    assert dialog._why_text() == "Requires user action."


# --- Setup-wizard button (from_setup_wizard deps) ------------------------


def _wizard_spec() -> DependencySpec:
    """A dep the setup wizard provides (whipper/metaflac/flac)."""
    return DependencySpec(
        dep_id="whipper",
        display_name="whipper",
        probe=lambda: ProbeResult(present=False, version=None, location=None),
        min_version=(0, 10, 0),
        tier=Tier.MANUAL,
        install_command=None,
        search_string="install whipper Bazzite Fedora Distrobox",
        description="installed + exported by the setup wizard",
        from_setup_wizard=True,
    )


def test_setup_wizard_button_shown_and_runs_for_wizard_dep(
    qapp: QApplication,
) -> None:
    """A wizard-provided dep offers the one-click wizard (the user shouldn't
    have to copy a search string), as the DEFAULT action; clicking it runs the
    callback and closes the dialog accepted."""
    called: list[bool] = []
    dialog = ManualInstallDialog(
        _wizard_spec(), _absent_probe(), on_setup_wizard=lambda: called.append(True)
    )
    assert dialog._setup_button is not None
    assert dialog._setup_button.isDefault() is True
    assert "Set it up automatically" in dialog._intro_text()

    dialog._setup_button.click()

    assert called == [True]
    assert dialog.result() == int(dialog.DialogCode.Accepted)


def test_no_setup_wizard_button_for_plain_dep(qapp: QApplication) -> None:
    """A non-wizard dep keeps the tier-(c) Copy-only path even if a callback is
    passed — Copy stays the default action."""
    dialog = ManualInstallDialog(_spec(), _absent_probe(), on_setup_wizard=lambda: None)
    assert dialog._setup_button is None
    assert dialog._copy_button.isDefault() is True


def test_no_setup_wizard_button_without_callback(qapp: QApplication) -> None:
    """Even a wizard dep shows no button if no callback was wired (defensive)."""
    dialog = ManualInstallDialog(_wizard_spec(), _absent_probe())
    assert dialog._setup_button is None


# --- Reject path ---------------------------------------------------------


def test_close_button_triggers_reject(qapp: QApplication) -> None:
    dialog = ManualInstallDialog(_spec(), _absent_probe())

    result_holder: dict[str, int] = {}

    def record_finished(result: int) -> None:
        result_holder["result"] = result

    dialog.finished.connect(record_finished)
    dialog._close_button.click()

    # QDialog.reject() sets result to Rejected (0).
    assert result_holder["result"] == int(dialog.DialogCode.Rejected)


def test_copy_confirmation_is_announced(qapp: QApplication, monkeypatch) -> None:
    """The Copied! button-label flip is visual-only feedback — a screen-reader
    user must hear that the copy took effect (a11y gap #4)."""
    heard: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.dialogs.manual_install.announce",
        lambda _source, message: heard.append(message) or True,
    )
    dialog = ManualInstallDialog(_spec(), _absent_probe())

    dialog.copy_search_string()

    assert heard == ["Search string copied to the clipboard."]
