"""Every message box the app can show, built with its real worst-case text and
measured by the UI conformance matrix on every screen it knows.

**Why this file exists (audit, 2026-10-05).** The maintainer asked for window
sizes and readability to be double-checked, *"especially on obscure windows like
the beta or odd cyanrip upgrades"*. `tests/test_ui_conformance.py` measured every
`CenteredDialog` and said, in its own docstring, that `QMessageBox` was NOT
covered. Built with their real text and measured, the obscure ones were exactly
the broken ones: the cyanrip offer for an unapproved beta build was 500 × 903 on
a 1366 × 768 laptop at 150 % text, the *Script commands* reference was 480 × 1820
on a 1080p panel at 200 % (500 × 1764 even at 1920 × 1080), the dependency
summary after a failed install was 480 × 1260 at 150 % on 960 × 540, and the beta
update prompt — a size that fitted — opened with its Yes and No below the screen,
because the app centred each box before Qt had sized it. The fix is
`ui/dialogs/message_box_fit.py`, applied to every box by the app-wide
`DialogCenterFilter`; this file is the population that holds it to the matrix.

**Three populations, each derived from the source so a new box cannot be missed:**

* **ROUTED** — every ``message_boxes.<kind>(parent, title, text, …)`` call in
  `src/`, found by walking the AST. The text is evaluated from the call: literal
  parts as written, every runtime value replaced by a long, realistic one (a deep
  path under a long home directory), and a whole-variable text by a long
  paragraph. Floor: :data:`MIN_ROUTED_BOXES`.
* **DIRECT** — every function that constructs a ``QMessageBox`` itself, as
  `tests/test_message_boxes_are_plaintext.py` enumerates them. Each must have a
  scenario in :data:`SITE_SCENARIOS` that drives the REAL function with real,
  worst-case inputs; `test_every_direct_message_box_has_a_scenario` fails by
  name for one that does not.
* **INLINE QT DIALOGS** — every other Qt dialog class constructed directly
  (today, the update's ``QProgressDialog``), the same way.

**Plus the real long texts the routed sweep can only stand in for:** the cyanrip
offer for EVERY verdict `deps/ripper_offer.py` can produce (asserted, not hoped),
the app's own update and beta prompts, the dependency summary with every section
it has at once, and the crash dialog.

**Not covered, said rather than implied:** Qt's own file dialog (on a desktop it
is usually the desktop's, not ours to size), and tooltips.
"""

from __future__ import annotations

import ast
import os
import re
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Final
from unittest import mock

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SRC: Final[Path] = REPO_ROOT / "src" / "platterpus"

#: A home directory as long as real ones get, so every path in every box is too.
LONG_HOME: Final[str] = "/home/maximilian-schwarzenegger-lindqvist"
#: Where an AppImage user runs the app from — the token `self_invocation()` puts
#: into every command a box tells the user to type.
LONG_APPIMAGE: Final[str] = f"{LONG_HOME}/Applications/platterpus-x86_64.AppImage"
#: What every runtime value in a routed box's f-string is replaced with.
LONG_VALUE: Final[str] = (
    f"{LONG_HOME}/Music/Platterpus/Godspeed You! Black Emperor/"
    "Lift Your Skinny Fists Like Antennas to Heaven (2000)"
)
#: What a text that is ENTIRELY a runtime value (``detail``, ``message``) becomes.
LONG_PARAGRAPH: Final[str] = (
    "A dependency told us something long, and this box shows it as written: "
    f"{LONG_VALUE}. " * 4
).strip()

#: Floor on routed boxes: 40 call sites on 2026-10-05. Below this the AST walk is
#: broken and "every routed box fits" is a statement about nothing.
MIN_ROUTED_BOXES: Final[int] = 30

#: The routed functions, by the name a call site uses.
_ROUTED_KINDS: Final[frozenset[str]] = frozenset(
    {"warning", "information", "critical", "question"}
)

#: Qt dialog classes a call site can construct directly, besides `QMessageBox`
#: (its own population) and `CenteredDialog` subclasses (the matrix's own list).
_INLINE_DIALOG_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "QDialog",
        "QProgressDialog",
        "QInputDialog",
        "QErrorMessage",
        "QColorDialog",
        "QFontDialog",
        "QWizard",
        "QFileDialog",
    }
)

#: Every function that shows a box or a Qt dialog of its own, by `module::function`
#: (the key `tests/test_message_boxes_are_plaintext.py` uses), and the scenarios
#: that drive it. Completeness against the source is asserted below.
SITE_SCENARIOS: Final[dict[str, tuple[str, ...]]] = {
    "app.py::_show_fatal_dialog": ("crash dialog", "crash dialog[unattended]"),
    "ui/dialogs/script_console.py::_on_show_reference": ("Script commands",),
    "ui/dialogs/script_settings_box.py::use_builtin_acceptance_script": (
        "built-in acceptance script missing",
    ),
    "ui/main_window_drive.py::_present_drive_diagnosis": ("drive access[no group]",),
    "ui/main_window_provision.py::_acceptance_message": ("acceptance message",),
    "ui/main_window_provision.py::_ask_acceptance_run_size": ("acceptance run size",),
    "ui/main_window_rip.py::_confirm_known_overwrite": (
        "album already ripped",
        "album folder ambiguous",
    ),
    # The cyanrip offers: one scenario per offer case, built in the subprocess
    # from :func:`offer_cases`; listed here by prefix.
    "ui/main_window_update.py::_offer_ripper_install": ("cyanrip install offer[*]",),
    "ui/main_window_update.py::_on_ripper_update_result": (
        "cyanrip update check[*]",
        "cyanrip update check, held back[*]",
    ),
    # Inline Qt dialogs.
    "ui/main_window_update.py::_begin_update_install": (
        "update progress[downloading]",
        "update progress[installing]",
    ),
}

#: Routed boxes whose text is long AND dynamic, driven through the real method so
#: the measured text is the real one rather than the routed sweep's stand-in.
REAL_CONTENT_SCENARIOS: Final[tuple[str, ...]] = (
    "dependency summary[every section]",
    "dependency summary[all ok]",
    "app update[beta, AppImage]",
    "app update[beta, source install]",
    "app update[up to date, running a beta]",
    "app update[beta channel, up to date]",
    "app update[check failed]",
    "app update[install failed]",
    "app update[installed, relaunch failed]",
)

#: The offer cases, by name: every verdict `deps/ripper_offer.py` can produce.
OFFER_CASE_NAMES: Final[tuple[str, ...]] = (
    "no fork build found",
    "unrecognised build, manifest unreachable",
    "current test pin",
    "retired test pin",
    "manifest unreachable",
    "newer, approved",
    "newer beta, unapproved, round open",
    "newer, the build under review",
    "current",
    "ahead of the channel",
    "the build under review installed",
)

# ==========================================================================
# The routed population, from the AST
# ==========================================================================


@dataclass(frozen=True)
class RoutedBox:
    """One ``message_boxes.<kind>(…)`` call, with its text evaluated."""

    key: str
    kind: str
    title: str
    text: str


def _evaluate(node: ast.expr) -> str:
    """The text a call site would show, with every runtime value made long."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.JoinedStr):
        return "".join(
            str(part.value) if isinstance(part, ast.Constant) else LONG_VALUE
            for part in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _evaluate(node.left) + _evaluate(node.right)
    return LONG_PARAGRAPH


def routed_boxes() -> list[RoutedBox]:
    """Every routed message box in `src/`, keyed ``routed:<module>:<line>``."""
    found: list[RoutedBox] = []
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(SRC).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _ROUTED_KINDS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "message_boxes"
                and len(node.args) >= 3
            ):
                continue
            found.append(
                RoutedBox(
                    key=f"routed:{rel}:{node.lineno}",
                    kind=node.func.attr,
                    title=_evaluate(node.args[1]),
                    text=_evaluate(node.args[2]),
                )
            )
    return found


def inline_dialog_sites() -> set[str]:
    """``module::function`` for every direct construction of a Qt dialog class."""
    sites: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(SRC).as_posix()
        for func in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(func, ast.FunctionDef):
                continue
            for call in ast.walk(func):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id in _INLINE_DIALOG_CLASSES
                ):
                    sites.add(f"{rel}::{func.name}")
    return sites


def expected_keys() -> set[str]:
    """Every key :func:`measure_message_boxes` must produce, before any suffix."""
    keys = {box.key for box in routed_boxes()}
    keys |= set(REAL_CONTENT_SCENARIOS)
    for names in SITE_SCENARIOS.values():
        for name in names:
            if name.endswith("[*]"):
                keys |= {name.replace("*", case) for case in OFFER_CASE_NAMES}
            else:
                keys.add(name)
    return keys


# ==========================================================================
# Real content
# ==========================================================================


def offer_cases() -> dict[str, object]:
    """One `RipperOffer` per case, each built by the real code with real pins."""
    from platterpus.deps import fork_source, ripper_offer
    from platterpus.deps.ripper_manifest import RipperManifest, RipperRelease

    def manifest(
        channel: str, commit: str, seq: int, round_no: int, closed: bool, version: str
    ) -> RipperManifest:
        row = RipperRelease(
            channel=channel,
            version=version,
            commit=commit,
            release_seq=seq,
            handshake_round=round_no,
            round_closed=closed,
            install_url="https://github.com/rmccann-hub/cyanrip/archive/x.tar.gz",
        )
        return RipperManifest(
            schema=2,
            project="cyanrip-fork",
            default_channel="stable",
            channels={channel: row},
        )

    pin = fork_source.FORK_PIN
    pin_seq = fork_source.FORK_PIN_RELEASE_SEQ or 1
    # A release our own record places before the pin: the user an approved
    # upgrade is offered to.
    older = next(
        (
            commit
            for commit, seq in sorted(
                fork_source.FORK_RELEASE_SEQ_BY_PIN.items(), key=lambda item: item[1]
            )
            if seq < pin_seq
        ),
        pin,
    )
    head = manifest("stable", pin, pin_seq, 29, True, fork_source.FORK_EXPECTED_VERSION)
    review = fork_source.PIN_UNDER_REVIEW
    beta_version = "0.9.4-rc2+platterpus.25-beta.3"
    evaluate = ripper_offer.evaluate_offer
    cases: dict[str, object] = {
        "no fork build found": evaluate(None, "stable", installed_commit=None),
        "unrecognised build, manifest unreachable": evaluate(
            None, "beta", installed_commit="deadbee"
        ),
        "current test pin": ripper_offer._test_pin_offer(
            "beta", fork_source.FORK_TEST_PIN, retired=False
        ),
        "retired test pin": ripper_offer._test_pin_offer(
            "beta", fork_source.FORK_TEST_PIN, retired=True
        ),
        "manifest unreachable": evaluate(None, "stable", installed_commit=pin),
        "newer, approved": evaluate(head, "stable", installed_commit=older),
        "newer beta, unapproved, round open": evaluate(
            manifest("beta", "abcdef1", pin_seq + 7, 31, False, beta_version),
            "beta",
            installed_commit=pin,
        ),
        "newer, the build under review": evaluate(
            manifest(
                "beta",
                review,
                pin_seq + 7,
                fork_source.PIN_UNDER_REVIEW_ROUND,
                False,
                beta_version,
            ),
            "beta",
            installed_commit=pin,
        ),
        "current": evaluate(head, "stable", installed_commit=pin),
        "ahead of the channel": ripper_offer._up_to_date_offer(
            "stable",
            RipperRelease(
                "stable", fork_source.FORK_EXPECTED_VERSION, pin, pin_seq, 29, True, "u"
            ),
            "abcdef1",
            pin_seq + 3,
        ),
        "the build under review installed": ripper_offer._up_to_date_offer(
            "beta",
            RipperRelease("beta", beta_version, review, pin_seq + 1, 30, False, "u"),
            review,
            pin_seq + 1,
        ),
    }
    assert tuple(cases) == OFFER_CASE_NAMES, "offer cases and their names drifted"
    return cases


def _dependency_report_with_every_section() -> object:
    """A report with every section the summary can print, all at once.

    An upper bound rather than a state one machine reaches — a tool is not both
    installed and failed — but each section is bounded by the number of specs, so
    all of them together is the longest summary the code can produce.
    """
    from platterpus.deps.build_notes import cyanrip_build_note
    from platterpus.deps.checks import ProbeResult
    from platterpus.deps.manager import DependencyReport
    from platterpus.deps.registry import SPECS
    from platterpus.deps.resolvers import InstallResult

    report = DependencyReport()
    report.ok = list(SPECS)
    report.ok_versions = {spec.dep_id: (1, 4, 3) for spec in SPECS}
    report.build_notes = {
        "cyanrip": cyanrip_build_note(
            ProbeResult(
                True,
                (0, 9, 3),
                f"{LONG_HOME}/.local/bin/cyanrip",
                "cyanrip 0.9.3 (stock)\n",
            )
        )
    }
    report.install_results = [
        InstallResult(
            spec=spec,
            success=False,
            message=(
                "install failed: error: Packages not found: "
                f"{spec.dep_id}-tools (rpm-ostree install --apply-live, exit 1)"
            ),
        )
        for spec in SPECS
    ]
    report.unchecked = list(SPECS)
    report.unchecked_reason = (
        "the container 'ripping' did not answer within 45 s (distrobox enter timed out)"
    )
    return report


# ==========================================================================
# The measuring run (inside the matrix's subprocess)
# ==========================================================================


@contextmanager
def _measured_modals(
    measure: Callable[[object], dict[str, object]],
    results: dict[str, object],
    current: list[str],
) -> Iterator[None]:
    """Every box or dialog opened inside this block is measured instead of waited on.

    `exec()` on the headless platform waits forever for a click, so each one is
    replaced with "measure what is on screen, then answer as if closed" — the box
    is the one production built, with production's text and buttons.
    """
    from PySide6.QtWidgets import QDialog, QMessageBox

    def record(widget: object) -> None:
        base = current[0]
        key = base
        number = 2
        while key in results:
            key = f"{base}#{number}"
            number += 1
        results[key] = measure(widget)

    def fake_exec(self: object) -> int:
        record(self)
        return 0

    def fake_open(self: object) -> None:
        record(self)

    with (
        mock.patch.object(QMessageBox, "exec", fake_exec),
        mock.patch.object(QMessageBox, "open", fake_open),
        mock.patch.object(QDialog, "exec", fake_exec),
        mock.patch.dict(os.environ, {"APPIMAGE": LONG_APPIMAGE}),
    ):
        yield


def _scenarios(window: object, tmp: Path) -> dict[str, Callable[[], object]]:
    """Each scenario by name: the real code path, driven with worst-case inputs."""
    from PySide6.QtWidgets import QMessageBox

    from platterpus import app as app_module
    from platterpus.drive_access import diagnose_drive_access
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.workers.rip_worker import RipParameters

    w: object = window  # a MainWindow; attribute access below is on the real one
    scenarios: dict[str, Callable[[], object]] = {}

    def crash(unattended: bool) -> None:
        exc = OSError(
            28,
            "No space left on device",
            f"{LONG_VALUE}/01 - Storm (Lift Yr. Skinny Fists, Like Antennas to Heaven…).flac",
        )
        app_module._show_fatal_dialog("Platterpus error", exc, unattended=unattended)

    scenarios["crash dialog"] = lambda: crash(False)
    scenarios["crash dialog[unattended]"] = lambda: crash(True)

    def script_commands() -> None:
        console = ScriptConsoleDialog(w)  # type: ignore[arg-type]  # a QWidget
        console._on_show_reference()
        console.deleteLater()

    scenarios["Script commands"] = script_commands

    def builtin_missing() -> None:
        console = ScriptConsoleDialog(w)  # type: ignore[arg-type]  # a QWidget
        from platterpus import test_session

        # Where a pipx install would have put it, from the module's own names.
        missing = (
            Path(LONG_HOME)
            / ".local/share/pipx/venvs/platterpus/lib/python3.14/site-packages"
            / "platterpus"
            / test_session.BUILTIN_SCRIPT_DIR_NAME
            / test_session.ACCEPTANCE_SCRIPT_NAME
        )
        with mock.patch(
            "platterpus.test_session.builtin_acceptance_script_path",
            return_value=missing,
        ):
            console._script_settings.use_builtin_acceptance_script()
        console.deleteLater()

    scenarios["built-in acceptance script missing"] = builtin_missing

    scenarios["drive access[no group]"] = lambda: w._present_drive_diagnosis(  # type: ignore[attr-defined]  # a MainWindow
        diagnose_drive_access(
            list_nodes=lambda: ["/dev/sr0", "/dev/sr1"],
            is_readable=lambda _p: False,
            group_of=lambda _p: "optical",
            in_group=lambda _g: False,
        )
    )
    scenarios["acceptance run size"] = lambda: w._ask_acceptance_run_size()  # type: ignore[attr-defined]  # a MainWindow
    scenarios["acceptance message"] = lambda: w._acceptance_message(  # type: ignore[attr-defined]  # a MainWindow
        QMessageBox.Icon.Warning,
        "Acceptance test could not start",
        "systemd-inhibit refused: Failed to inhibit: Access denied "
        "(org.freedesktop.login1.inhibit-block-sleep)\n\nThe session folder is "
        f"{LONG_HOME}/Downloads/platterpus-acceptance-20261005T231500Z-full-run",
        open_path=tmp,
    )

    # The overwrite prompts, on real folders (empty stand-in files, never audio).
    # A `12"` in a title is the character cyanrip swaps for a look-alike, which is
    # what makes two folders able to claim one album.
    artist = "Godspeed You! Black Emperor"
    library = tmp / "Music Library on the NAS (FLAC masters — do not edit)"

    def overwrite(ambiguous: bool) -> None:
        root = library / ("ambiguous" if ambiguous else "single")
        if ambiguous:
            title = 'Lift Your Skinny Fists Like Antennas to Heaven (2000 12" Remaster)'
            names = (title.replace('"', "“"), title.replace('"', "”"))
        else:
            title = "Lift Your Skinny Fists Like Antennas to Heaven (2000 Remaster)"
            names = (title,)
        for name in names:
            folder = root / artist / name
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "01 - Storm.flac").write_bytes(b"not really audio")
        table = w._track_table  # type: ignore[attr-defined]  # a MainWindow
        table._album_artist_edit.setText(artist)
        table._album_title_edit.setText(title)
        w._confirm_known_overwrite(  # type: ignore[attr-defined]  # a MainWindow
            RipParameters(
                drive="/dev/sr0",
                release_id="mbid",
                output_dir=root,
                track_template="%A/%d/%t - %n",
                disc_template="%A/%d/%d",
                unknown=False,
            )
        )

    scenarios["album already ripped"] = lambda: overwrite(False)
    scenarios["album folder ambiguous"] = lambda: overwrite(True)

    for case, offer in offer_cases().items():
        scenarios[f"cyanrip update check[{case}]"] = _offer_check(w, offer, held=False)
        scenarios[f"cyanrip update check, held back[{case}]"] = _offer_check(
            w, offer, held=True
        )
        scenarios[f"cyanrip install offer[{case}]"] = _offer_install(w, offer)

    scenarios["update progress[downloading]"] = lambda: _update_progress(w, False)
    scenarios["update progress[installing]"] = lambda: _update_progress(w, True)

    scenarios["dependency summary[every section]"] = lambda: w._show_dep_summary(  # type: ignore[attr-defined]  # a MainWindow
        _dependency_report_with_every_section(), _every_spec_missing()
    )
    scenarios["dependency summary[all ok]"] = lambda: _all_ok_summary(w)
    scenarios.update(_app_update_scenarios(w))
    return scenarios


def _offer_check(window: object, offer: object, *, held: bool) -> Callable[[], None]:
    """The menu's *Check for cyanrip updates* answer for ``offer``.

    ``held`` is the same answer while something stops the install being offered
    (an acceptance session): the slot appends why, which makes it longer.
    """

    def run() -> None:
        w: object = window
        w._ripper_offer_box = None  # type: ignore[attr-defined]  # a MainWindow
        w._ripper_check_is_automatic = False  # type: ignore[attr-defined]  # a MainWindow
        if held:
            with mock.patch.object(
                type(w),
                "_interruption_blocker",
                lambda _self: "an acceptance test session is running",
            ):
                w._on_ripper_update_result(offer)  # type: ignore[attr-defined]  # a MainWindow
        else:
            w._on_ripper_update_result(offer)  # type: ignore[attr-defined]  # a MainWindow
        w._ripper_offer_box = None  # type: ignore[attr-defined]  # a MainWindow

    return run


def _offer_install(window: object, offer: object) -> Callable[[], None]:
    """The one-click install offer for ``offer``, in its consent form."""

    def run() -> None:
        w: object = window
        w._offer_ripper_install(  # type: ignore[attr-defined]  # a MainWindow
            offer, str(getattr(offer, "detail", "")), "abcdef1", needs_consent=True
        )
        w._ripper_offer_box = None  # type: ignore[attr-defined]  # a MainWindow

    return run


def _update_progress(window: object, installing: bool) -> None:
    """The app update's progress dialog, built by the real method, no download."""
    from PySide6.QtCore import QObject, Signal

    class _NoDownload(QObject):
        progress = Signal(float)
        status = Signal(str)
        finished = Signal(bool, str)

        def __init__(self, _version: str) -> None:
            super().__init__()

        def run(self) -> None:  # pragma: no cover — never started
            pass

        def cancel(self) -> None:
            pass

    w: object = window
    with (
        mock.patch("platterpus.workers.start_worker_thread", lambda *a, **k: None),
        mock.patch("platterpus.workers.update_worker.UpdateInstallWorker", _NoDownload),
    ):
        w._begin_update_install("0.7.100b12")  # type: ignore[attr-defined]  # a MainWindow
    dialog = w._install_dialog  # type: ignore[attr-defined]  # a MainWindow
    if installing:
        w._on_install_status("Installing — almost done, please don't close…")  # type: ignore[attr-defined]  # a MainWindow
    # Measured by the caller's `current` key through `_measured_modals`' recorder,
    # which only sees `exec`/`open`; a progress dialog is `show()`n, so it is
    # handed over explicitly.
    _MEASURE_SHOWN[0](dialog)
    w._install_dialog = None  # type: ignore[attr-defined]  # a MainWindow
    w._install_worker = None  # type: ignore[attr-defined]  # a MainWindow
    w._install_thread = None  # type: ignore[attr-defined]  # a MainWindow (never started)
    dialog.deleteLater()


#: Set by :func:`measure_message_boxes` to its recorder, for dialogs that are
#: shown rather than `exec`ed.
_MEASURE_SHOWN: list[Callable[[object], None]] = [lambda _w: None]


def _every_spec_missing() -> list[object]:
    from platterpus.deps.checks import ProbeResult
    from platterpus.deps.registry import SPECS
    from platterpus.deps.resolvers import MissingItem

    return [MissingItem(spec=s, probe=ProbeResult(False, None, None)) for s in SPECS]


def _all_ok_summary(window: object) -> None:
    from platterpus.deps.manager import DependencyReport
    from platterpus.deps.registry import SPECS

    report = DependencyReport()
    report.ok = list(SPECS)
    report.ok_versions = {spec.dep_id: (1, 4, 3) for spec in SPECS}
    window._show_dep_summary(report, [])  # type: ignore[attr-defined]  # a MainWindow


def _app_update_scenarios(window: object) -> dict[str, Callable[[], object]]:
    """The app's own update answers, beta wording included, through the real slot."""
    import platterpus

    w: object = window
    beta = SimpleNamespace(
        version="0.7.100b12",
        url="https://github.com/rmccann-hub/Platterpus/releases/tag/v0.7.100b12",
        is_prerelease=True,
    )
    older = SimpleNamespace(version="0.6.1", url="https://example.invalid/")

    def result(info: object, *, appimage: bool = True, running: str = "") -> None:
        env = {"APPIMAGE": LONG_APPIMAGE} if appimage else {}
        with (
            mock.patch.dict(os.environ, env),
            mock.patch.object(
                platterpus, "__version__", running or platterpus.__version__
            ),
        ):
            if not appimage:
                os.environ.pop("APPIMAGE", None)
            w._on_update_result(info)  # type: ignore[attr-defined]  # a MainWindow

    def beta_channel_up_to_date() -> None:
        config = w._config  # type: ignore[attr-defined]  # a MainWindow
        before = config.update_channel
        config.update_channel = "beta"
        try:
            result(older)
        finally:
            config.update_channel = before

    def relaunch_failed() -> None:
        with (
            mock.patch(
                "subprocess.Popen",
                side_effect=OSError(13, "Permission denied", LONG_APPIMAGE),
            ),
            mock.patch("platterpus.appimage_integration.integrate", lambda _p: None),
        ):
            w._on_update_install_finished(True, LONG_APPIMAGE)  # type: ignore[attr-defined]  # a MainWindow

    return {
        "app update[beta, AppImage]": lambda: result(beta),
        "app update[beta, source install]": lambda: result(beta, appimage=False),
        "app update[up to date, running a beta]": lambda: result(
            older, running="0.6.65b3"
        ),
        "app update[beta channel, up to date]": beta_channel_up_to_date,
        "app update[check failed]": lambda: result(None),
        "app update[install failed]": lambda: w._on_update_install_finished(  # type: ignore[attr-defined]  # a MainWindow
            False,
            "the build attestation did not verify: the bundle was signed by "
            "https://github.com/someone-else/Platterpus/.github/workflows/"
            "release.yml@refs/tags/v0.7.100b12, not by this project's release workflow",
        ),
        "app update[installed, relaunch failed]": relaunch_failed,
    }


def measure_message_boxes(
    measure: Callable[[object], dict[str, object]],
    make_window: Callable[[], object],
) -> dict[str, object]:
    """Subprocess entry: every box in this file's three populations, measured.

    ``measure`` is the matrix's `_measure_one`; every rule it applies to a dialog
    is applied to each box. Raises if a scenario opens nothing, because a scenario
    that stopped reaching its box would otherwise pass by measuring nothing.
    """
    from conftest import stop_window_threads
    from PySide6.QtWidgets import QApplication, QMessageBox

    from platterpus.ui import message_boxes

    results: dict[str, object] = {}
    current = ["?"]

    def record_shown(widget: object) -> None:
        results[current[0]] = measure(widget)

    _MEASURE_SHOWN[0] = record_shown
    icons = {
        "warning": QMessageBox.Icon.Warning,
        "information": QMessageBox.Icon.Information,
        "critical": QMessageBox.Icon.Critical,
        "question": QMessageBox.Icon.Question,
    }
    window = make_window()
    window.show()  # type: ignore[attr-defined]  # a MainWindow
    app = QApplication.instance()
    assert app is not None
    for _ in range(5):
        app.processEvents()
    try:
        for box in routed_boxes():
            built = message_boxes.build(
                icons[box.kind],
                window,
                box.title,
                box.text,  # type: ignore[arg-type]  # a QWidget
            )
            results[box.key] = measure(built)
            built.deleteLater()
        with tempfile.TemporaryDirectory() as tmp:
            scenarios = _scenarios(window, Path(tmp))
            missing = expected_keys() - {b.key for b in routed_boxes()} - set(scenarios)
            assert not missing, f"scenarios named but not built: {sorted(missing)}"
            with _measured_modals(measure, results, current):
                for name, run in scenarios.items():
                    current[0] = name
                    run()
                    if name not in results:
                        raise AssertionError(f"scenario {name!r} opened no dialog")
    finally:
        _MEASURE_SHOWN[0] = lambda _w: None
        stop_window_threads(window)
    return results


# ==========================================================================
# Static checks — no rendering, run in the pytest process
# ==========================================================================


def test_every_direct_message_box_has_a_scenario() -> None:
    """Completeness, from the source: a new box-building function fails by name."""
    from test_message_boxes_are_plaintext import _message_box_functions

    direct = set(_message_box_functions()) - {"ui/message_boxes.py::build"}
    sites = direct | inline_dialog_sites()
    assert len(direct) >= 8, f"only {len(direct)} direct sites — the sweep broke"
    assert "ui/main_window_update.py::_begin_update_install" in sites, (
        "the inline-dialog sweep no longer sees the update's progress dialog"
    )
    assert sites == set(SITE_SCENARIOS), (
        f"no scenario: {sorted(sites - set(SITE_SCENARIOS))}; "
        f"scenario for a site that is gone: {sorted(set(SITE_SCENARIOS) - sites)}"
    )


def test_the_routed_sweep_finds_every_routed_box() -> None:
    """Floor, and the subjects that matter most, by name."""
    boxes = routed_boxes()
    assert len(boxes) >= MIN_ROUTED_BOXES, f"only {len(boxes)} routed boxes found"
    keys = " ".join(box.key for box in boxes)
    for subject in (
        "main_window_update.py",
        "main_window_deps.py",
        "uninstall_dialog.py",
    ):
        assert subject in keys, f"no routed box found in {subject}"
    assert all(box.text for box in boxes), "a routed box evaluated to no text"


def test_the_evaluator_makes_runtime_values_long() -> None:
    """Non-triviality: a stand-in that kept values short would measure nothing."""
    call = ast.parse('f"Couldn\'t read {path}: {exc}"', mode="eval").body
    text = _evaluate(call)
    assert text.count(LONG_VALUE) == 2, text
    assert text.startswith("Couldn't read ")
    assert _evaluate(ast.parse("message", mode="eval").body) == LONG_PARAGRAPH
    assert _evaluate(ast.parse('"a" + "b"', mode="eval").body) == "ab"


def test_the_offer_cases_reach_every_verdict() -> None:
    """Every verdict the offer module defines is measured — derived, not listed."""
    from platterpus.deps import ripper_offer

    verdicts = {
        value
        for name, value in vars(ripper_offer).items()
        if re.fullmatch(r"OFFER_[A-Z_]+", name) and isinstance(value, str)
    }
    assert len(verdicts) >= 4, verdicts
    reached = {getattr(offer, "verdict", None) for offer in offer_cases().values()}
    assert verdicts <= reached, f"verdicts no case reaches: {verdicts - reached}"
    # And the long ones are long: the consequence and the install hint are in.
    details = [str(getattr(o, "detail", "")) for o in offer_cases().values()]
    assert max(len(d) for d in details) > 1000, "the longest offer text shrank"
    assert any("--install-ripper" in d for d in details), "no install hint reached"
