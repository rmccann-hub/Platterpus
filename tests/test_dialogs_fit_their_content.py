"""Every dialog fits its text and its screen — measured on real screen shapes.

**The defect this gates** (real-user report, 2026-09-23): the cyanrip build picker
opened 360 px tall with all five of its paragraphs cut off mid-sentence and nothing
to scroll. The maintainer's point was the general one — *"it does mean you have
not solved this globally or put in a fix/gate/rule that does."* They were right:
Settings already clamped itself to the screen and Drive Setup already refused to be
shorter than its prose, each fixed on its own, and no test anywhere measured a
label against the height its text needs.

**The mechanism, reproduced before it was fixed.** Qt sizes a new window from its
size hint and caps it at two-thirds of the screen, and a word-wrapped `QLabel` is
squeezed below its text rather than pushing the window taller. On a virtual
960 × 540 screen — a 1080p panel at 200% scaling, which is what a KDE laptop
reports — the picker came up at exactly 360 px and clipped 5 labels. At 1280 × 720
it clipped 1, at 800 × 800 it clipped 1. The fix lives on
`CenteredDialog._fit_content_to_screen`, and a body whose length is not ours to
fix scrolls in a `FitScrollArea` (`ui/dialogs/fit_scroll_area.py`).

**Why a subprocess.** The screen shape is a property of the Qt platform plugin,
fixed when `QApplication` starts, and this suite's application is shared. The
offscreen plugin takes a screen geometry from a JSON file, so each shape gets its
own interpreter. That is what makes this a measurement on a 540 px screen rather
than an assertion about arithmetic we believe describes one — the lesson of
`docs/testing.md` §5.v, where CI's 800 × 800 virtual screen made two different
window defaults measure identically.

**Scope, stated so it is not silently narrower than it reads.** Every
`CenteredDialog` subclass in `src/`, derived from the source rather than listed by
hand, so a new dialog without a factory here fails. NOT covered: `QMessageBox`
(Qt sizes those itself and their text is short), the main window (it has its own
scroll-area rules in `docs/architecture.md` §3.9), and the setup wizard pages.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
SRC: Path = REPO_ROOT / "src"

#: The screen shapes measured. 960 × 540 is the one that reproduced the report and
#: the one most likely to find the next overflow; 1920 × 1080 is the common
#: unscaled desktop, where a dialog must also not be SMALLER than its text.
SCREENS: tuple[tuple[int, int], ...] = ((960, 540), (1920, 1080))

#: A dialog class name must appear here to be measured — and every
#: `CenteredDialog` subclass in the source must appear here, or the completeness
#: test below fails. The factories themselves live in `_factories()`, which runs
#: inside the measuring subprocess.
MEASURED: frozenset[str] = frozenset(
    {
        "AboutDialog",
        "DiagnosticsDialog",
        "DriveSetupDialog",
        "FileViewerDialog",
        "HelpDialog",
        "HostSetupDialog",
        "ManualInstallDialog",
        "PendingInstallsDialog",
        "ReleasePickerDialog",
        "RipperPickerDialog",
        "ScriptConsoleDialog",
        "SettingsDialog",
        "SetupCenterDialog",
        "UninstallDialog",
        "UnknownAlbumDialog",
    }
)


def _factories() -> dict[str, object]:
    """One way to build each dialog with stand-in dependencies.

    Imported only inside the subprocess, because building a dialog needs a
    `QApplication` on the screen being measured. The stand-ins are the ones each
    dialog's own test file already uses, imported rather than copied, so a change
    to a constructor breaks one place.
    """
    from PySide6.QtWidgets import QWidget
    from test_ui_drive_setup_dialog import _StubBackend
    from test_ui_host_setup_dialog import _FakeHost
    from test_ui_manual_install_dialog import _absent_probe, _spec
    from test_ui_pending_installs_dialog import _item
    from test_ui_release_picker import _release

    from platterpus.config import Config
    from platterpus.ui.dialogs.diagnostics_dialog import DiagnosticsDialog
    from platterpus.ui.dialogs.file_viewer import FileViewerDialog
    from platterpus.ui.dialogs.manual_install import ManualInstallDialog
    from platterpus.ui.dialogs.pending_installs import PendingInstallsDialog
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.ui.dialogs.setup_center import SetupCenterDialog
    from platterpus.ui.drive_setup_dialog import DriveSetupDialog
    from platterpus.ui.help_dialogs import AboutDialog, HelpDialog
    from platterpus.ui.host_setup_dialog import HostSetupDialog
    from platterpus.ui.release_picker import ReleasePickerDialog
    from platterpus.ui.ripper_picker import RipperPickerDialog
    from platterpus.ui.settings_dialog import SettingsDialog
    from platterpus.ui.uninstall_dialog import UninstallDialog
    from platterpus.ui.unknown_album import UnknownAlbumDialog

    text_file = Path(tempfile.mkdtemp()) / "viewed.txt"
    text_file.write_text("a line\n", encoding="utf-8")
    holder = QWidget()
    return {
        "AboutDialog": lambda: AboutDialog(),
        "DiagnosticsDialog": lambda: DiagnosticsDialog(),
        "DriveSetupDialog": lambda: DriveSetupDialog(_StubBackend(), "/dev/sr0"),
        "FileViewerDialog": lambda: FileViewerDialog(
            text_file, reader=lambda _p: "a line"
        ),
        "HelpDialog": lambda: HelpDialog(),
        "HostSetupDialog": lambda: HostSetupDialog(host_setup=_FakeHost(True)),
        "ManualInstallDialog": lambda: ManualInstallDialog(_spec(), _absent_probe()),
        "PendingInstallsDialog": lambda: PendingInstallsDialog(
            [_item("picard"), _item("metaflac")]
        ),
        "ReleasePickerDialog": lambda: ReleasePickerDialog(
            [_release(), _release(mbid="second")]
        ),
        "RipperPickerDialog": lambda: RipperPickerDialog(),
        "ScriptConsoleDialog": lambda: ScriptConsoleDialog(holder),
        "SettingsDialog": lambda: SettingsDialog(Config()),
        "SetupCenterDialog": lambda: SetupCenterDialog(
            None,
            app_version="0.0.0",
            ripper_pin="0000000",
            ripper_version="0.0.0",
            approved_by_round=0,
            dependency_report=None,
            actions={},
        ),
        "UninstallDialog": lambda: UninstallDialog(build_teardown=lambda *a: None),
        "UnknownAlbumDialog": lambda: UnknownAlbumDialog(),
    }


def _measure_one(dialog: object) -> dict[str, object]:
    """Show one dialog and report every way it fails to fit.

    A label counts as clipped when its height is less than the height its own
    text needs at its own width — `heightForWidth`, the number Qt's layout is
    supposed to honour and, for a squeezed top-level window, does not.
    """
    from PySide6.QtWidgets import QApplication, QLabel

    from platterpus.ui.dialogs.centering import CenteredDialog
    from platterpus.ui.dialogs.fit_scroll_area import FitScrollArea

    app = QApplication.instance()
    assert app is not None
    dialog.show()  # type: ignore[attr-defined]  # every factory returns a QDialog
    for _ in range(5):
        app.processEvents()
    avail = dialog.screen().availableGeometry()  # type: ignore[attr-defined]  # a QDialog
    clipped: list[str] = []
    examined = 0
    for label in dialog.findChildren(QLabel):  # type: ignore[attr-defined]  # a QDialog
        if not (label.wordWrap() and label.isVisibleTo(dialog) and label.text()):
            continue
        examined += 1
        need = label.heightForWidth(label.width())
        if label.height() < need:
            clipped.append(
                f"{label.height()}px of {need}px needed: {label.text()[:60]!r}"
            )
    # A scroll body that scrolls although the window had room to grow is the
    # opposite failure: nothing is clipped, and the user still sees a third of the
    # dialog behind a scrollbar — the defect `SettingsDialog._opening_size` was
    # written for. The window is "capped" when the fit stopped it at the screen.
    cap = avail.height() - CenteredDialog.SCREEN_MARGIN_PX
    capped = dialog.height() >= cap - 1  # type: ignore[attr-defined]  # a QDialog
    scroll_ranges = [
        area.verticalScrollBar().maximum() - area.verticalScrollBar().minimum()
        for area in dialog.findChildren(FitScrollArea)  # type: ignore[attr-defined]  # a QDialog
    ]
    report: dict[str, object] = {
        "capped": capped,
        "scroll_ranges": scroll_ranges,
        "size": [dialog.width(), dialog.height()],  # type: ignore[attr-defined]  # a QDialog
        "avail": [avail.width(), avail.height()],
        "fits": dialog.width() <= avail.width()  # type: ignore[attr-defined]  # a QDialog
        and dialog.height() <= avail.height(),  # type: ignore[attr-defined]  # a QDialog
        "clipped": clipped,
        "examined": examined,
    }
    dialog.close()  # type: ignore[attr-defined]  # a QDialog
    return report


def _measure_all() -> dict[str, object]:
    """Subprocess entry: every dialog, plus the picker with a long list."""
    from unittest import mock

    from PySide6.QtWidgets import QApplication

    _app = QApplication([])
    results: dict[str, object] = {}
    for name, make in _factories().items():
        results[name] = _measure_one(make())  # type: ignore[operator]  # factories are callables

    # FUTURE-PROOFING, measured rather than promised. The picker lists whatever
    # builds the handshake record names; the maintainer asked that it keep
    # working "in case there are more options later". Eight rows is more than
    # any round has ever offered.
    from platterpus.deps import fork_source
    from platterpus.ui.ripper_picker import RipperPickerDialog

    real = fork_source.ripper_choices()
    many = [real[0]] * 8
    with mock.patch.object(fork_source, "ripper_choices", return_value=many):
        picker = RipperPickerDialog()
        report = _measure_one(picker)
        bar = picker._body_scroll.verticalScrollBar()
        report["scroll_range"] = bar.maximum() - bar.minimum()
        results["RipperPickerDialog[8 rows]"] = report
    return results


def _run_on_screen(width: int, height: int) -> dict[str, dict[str, object]]:
    config = Path(tempfile.mkdtemp()) / "screen.json"
    config.write_text(
        json.dumps(
            {
                "screens": [
                    {
                        "name": f"{width}x{height}",
                        "x": 0,
                        "y": 0,
                        "width": width,
                        "height": height,
                        "logicalDpi": 96,
                        "dpr": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = f"offscreen:configfile={config}"
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(REPO_ROOT / "tests")])
    proc = subprocess.run(
        [sys.executable, __file__, "--measure"],
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
        check=False,
    )
    assert proc.returncode == 0, (
        f"the measuring subprocess failed (exit {proc.returncode}):\n"
        f"{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )
    marker = "MEASUREMENTS:"
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith(marker)), None)
    assert line is not None, f"no measurements printed:\n{proc.stdout[-3000:]}"
    parsed: dict[str, dict[str, object]] = json.loads(line[len(marker) :])
    return parsed


@pytest.fixture(scope="module", params=SCREENS, ids=lambda s: f"{s[0]}x{s[1]}")
def measured(request: pytest.FixtureRequest) -> dict[str, dict[str, object]]:
    width, height = request.param
    return _run_on_screen(width, height)


def test_no_dialog_clips_its_own_text(measured: dict[str, dict[str, object]]) -> None:
    """The user's symptom, for every dialog: no paragraph is cut off."""
    offenders = {
        name: report["clipped"]
        for name, report in measured.items()
        if report["clipped"]
    }
    assert not offenders, (
        "dialogs whose wrapped text is shorter than it needs — put the body in a "
        f"`FitScrollArea` (buttons outside it):\n{json.dumps(offenders, indent=2)}"
    )


def test_no_dialog_is_taller_or_wider_than_the_screen(
    measured: dict[str, dict[str, object]],
) -> None:
    """A window bigger than the screen has buttons the user cannot reach."""
    offenders = {
        name: (report["size"], report["avail"])
        for name, report in measured.items()
        if not report["fits"]
    }
    assert not offenders, f"dialogs larger than the screen: {offenders}"


def test_the_measurement_examined_real_text(
    measured: dict[str, dict[str, object]],
) -> None:
    """Non-triviality: a sweep that found no labels would pass by finding nothing.

    The floor is well under today's count, so it fails on a measurement that
    stopped seeing labels rather than on ordinary edits to a dialog.
    """
    examined = sum(int(report["examined"]) for report in measured.values())  # type: ignore[call-overload]  # JSON int
    assert examined >= 20, f"only {examined} wrapped labels examined"
    assert set(MEASURED) <= set(measured), (
        f"dialogs not measured: {sorted(set(MEASURED) - set(measured))}"
    )


def test_a_body_scrolls_only_when_the_screen_ran_out(
    measured: dict[str, dict[str, object]],
) -> None:
    """The inverse failure, which a clipping check alone cannot see.

    A scroll body with a small size hint opens small and scrolls: every label
    fits, the check above passes, and the user reads a third of the dialog behind
    a scrollbar on a screen with room to spare. Found by a revert probe of this
    very file, 2026-09-23 — replacing `FitScrollArea.sizeHint` with Qt's own left
    every other test here green.
    """
    offenders = {
        name: report
        for name, report in measured.items()
        if not report["capped"] and any(report["scroll_ranges"])  # type: ignore[arg-type]  # JSON list of ints
    }
    assert not offenders, (
        "dialogs whose body scrolls although the window had room to grow — the "
        f"scroll area is under-reporting its content:\n{json.dumps(offenders, indent=2)}"
    )


def test_a_long_picker_scrolls_instead_of_clipping(
    measured: dict[str, dict[str, object]],
) -> None:
    """Future-proofing, asserted: eight rows scroll, fit, and clip nothing.

    On the small screen the scroll range must be positive — that is the proof
    the body really is the thing that yields. On the large one it may be zero;
    the assertion there is only that nothing clipped and the window fit.
    """
    report = measured["RipperPickerDialog[8 rows]"]
    assert not report["clipped"], report["clipped"]
    assert report["fits"], report
    width, height = report["avail"]  # type: ignore[misc]  # JSON list of two ints
    if height < 700:
        assert int(report["scroll_range"]) > 0, (  # type: ignore[call-overload]  # JSON int
            "eight rows on a short screen did not scroll — the body is not the "
            f"widget that yields: {report}"
        )


def test_every_centered_dialog_in_the_source_is_measured() -> None:
    """Completeness, derived from the source rather than trusted.

    A new dialog without a factory here would never be measured, and a list of
    dialogs is only ever wrong by omission — the decay `CLAUDE.md` names under
    *"Does this document promise completeness?"*.
    """
    pattern = re.compile(r"^class (\w+)\(CenteredDialog\):", re.MULTILINE)
    found = {
        match.group(1)
        for path in (SRC / "platterpus").rglob("*.py")
        for match in pattern.finditer(path.read_text(encoding="utf-8"))
    }
    assert len(found) >= 10, f"only {len(found)} dialogs found — the pattern broke"
    assert found == MEASURED, (
        f"not measured: {sorted(found - MEASURED)}; "
        f"measured but gone: {sorted(MEASURED - found)}"
    )


if __name__ == "__main__" and "--measure" in sys.argv:
    print("MEASUREMENTS:" + json.dumps(_measure_all()))
