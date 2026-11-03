# SPDX-License-Identifier: GPL-3.0-only
"""The C9 verbs: ``expect-config-saved``, ``expect-no-rip`` and ``wait-for-status``.

**Why they exist** (the review of the 2026-11-03 Full run, C9). A user reaches
Settings' OK, the overwrite prompt's Cancel and Replace, and Cancel during the
securing pass on one drive, and no acceptance step pressed any of them. Pressing
was already possible (``open``/``ok``, ``answer-dialog click=``, ``cancel-rip``);
what a script could not do was ASSERT the result, or act at the phase of a rip
the case is about. Each verb is tested here for the failure it exists to catch,
and the sections that use them are pinned against the committed scripts.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from conftest import stop_window_threads
from test_uiscript_rip_verbs import _step_outcome, _window

from platterpus import config as config_module
from platterpus import paths
from platterpus.config import Config
from platterpus.uiscript import control_verbs
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse

_RIG_SCRIPTS = (
    Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"
)


@pytest.fixture
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where `config.save` writes and the verb reads, inside this test's folder."""
    path = tmp_path / "config" / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", path.parent)
    monkeypatch.setattr(config_module, "CONFIG_PATH", path)
    monkeypatch.setattr(paths, "CONFIG_PATH", path)
    return path


# --- expect-config-saved --------------------------------------------------------


def test_the_file_holding_the_running_settings_passes(
    qapp: Any, process_until: Any, config_path: Path
) -> None:
    running = Config(max_retries=7)
    config_module.save(running)
    step = _step_outcome(
        ScriptRunner(_window(config=running)),
        qapp,
        process_until,
        "expect-config-saved",
    )
    assert step.outcome is Outcome.PASS, step.detail


def test_a_setting_the_file_does_not_hold_fails_and_is_named(
    qapp: Any, process_until: Any, config_path: Path
) -> None:
    config_module.save(Config(max_retries=7))
    step = _step_outcome(
        ScriptRunner(_window(config=Config(max_retries=3))),
        qapp,
        process_until,
        "expect-config-saved",
    )
    assert step.outcome is Outcome.FAIL
    assert "max_retries: the file holds 7, running 3" in step.detail


def test_no_settings_file_fails(
    qapp: Any, process_until: Any, config_path: Path
) -> None:
    step = _step_outcome(
        ScriptRunner(_window()), qapp, process_until, "expect-config-saved"
    )
    assert step.outcome is Outcome.FAIL
    assert not config_path.exists(), "the check must not write a defaults file"


def test_a_file_saved_too_long_ago_fails_the_timed_form(
    qapp: Any, process_until: Any, config_path: Path
) -> None:
    """The half that makes Settings OK falsifiable: `set` saved earlier, OK did not."""
    running = Config()
    config_module.save(running)
    past = time.time() - 30.0
    os.utime(config_path, (past, past))
    step = _step_outcome(
        ScriptRunner(_window(config=running)),
        qapp,
        process_until,
        "expect-config-saved 2",
    )
    assert step.outcome is Outcome.FAIL
    assert "not within the last 2 s" in step.detail


def test_a_file_saved_just_now_passes_the_timed_form(
    qapp: Any, process_until: Any, config_path: Path
) -> None:
    running = Config()
    config_module.save(running)
    step = _step_outcome(
        ScriptRunner(_window(config=running)),
        qapp,
        process_until,
        "expect-config-saved 5",
    )
    assert step.outcome is Outcome.PASS, step.detail


@pytest.mark.parametrize("arg", ["0", "-1", "601", "soon"])
def test_a_window_outside_its_range_is_refused(
    qapp: Any, process_until: Any, config_path: Path, arg: str
) -> None:
    step = _step_outcome(
        ScriptRunner(_window()), qapp, process_until, f"expect-config-saved {arg}"
    )
    assert step.outcome is Outcome.ERROR


def test_a_newer_versions_extra_key_is_not_a_difference() -> None:
    assert control_verbs.config_differences({"a": 1}, {"a": 1, "future": 2}) == []


def test_settings_ok_on_the_real_window_saves_what_is_running(
    qapp: Any, process_until: Any, config_path: Path
) -> None:
    """Section D2's sequence, on a real `MainWindow` and its real Settings dialog.

    The stand-in above sets the file directly; this one asks the product's OK to
    write it, so a window whose OK stopped saving fails here (`CLAUDE.md`: what
    does my stand-in do that the real thing does not?).
    """
    from test_ui_main_window import _make_window

    # The first-run offers already answered, as on any rig that has run before:
    # a fresh window's host-setup offer saves the config too, and found by
    # revert-probing this test, it made OK's own save unnecessary to pass.
    seasoned = Config(
        host_setup_prompted=True,
        drive_setup_prompted=True,
        appimage_integration_prompted=True,
    )
    window = _make_window(qapp, config=seasoned, save_cfg=config_module.save)
    try:
        config_module.save(window._config)
        past = time.time() - 30.0
        os.utime(config_path, (past, past))
        step = _step_outcome(
            ScriptRunner(window),
            qapp,
            process_until,
            "open settings\nok\nwait 0.3\nexpect-config-saved 5",
        )
        assert step.outcome is Outcome.PASS, step.detail
    finally:
        stop_window_threads(window)
        window.deleteLater()


# --- expect-no-rip -----------------------------------------------------------------


def test_no_rip_worker_passes(qapp: Any, process_until: Any) -> None:
    step = _step_outcome(ScriptRunner(_window()), qapp, process_until, "expect-no-rip")
    assert step.outcome is Outcome.PASS


def test_a_running_rip_fails(qapp: Any, process_until: Any) -> None:
    step = _step_outcome(
        ScriptRunner(_window(rip_worker=object())), qapp, process_until, "expect-no-rip"
    )
    assert step.outcome is Outcome.FAIL


# --- wait-for-status ---------------------------------------------------------------


class _Status:
    """A rip-progress pane whose status line a test can change."""

    def __init__(self, text: str = "") -> None:
        self.text = text

    def current_status(self) -> str:
        return self.text


def test_it_passes_once_the_status_reads_the_text(
    qapp: Any, process_until: Any
) -> None:
    status = _Status("Re-ripping track 1 to secure it… 12%")
    win = _window(rip_progress=status, rip_worker=object())
    step = _step_outcome(
        ScriptRunner(win), qapp, process_until, "wait-for-status 5 TO SECURE IT"
    )
    assert step.outcome is Outcome.PASS, step.detail


def test_it_fails_when_the_rip_it_watched_ends_first(
    qapp: Any, process_until: Any
) -> None:
    """Waiting on would only run the clock out on a question already answered."""
    status = _Status("Ripping track 1 of 2… 50%")
    win = _window(rip_progress=status, rip_worker=object())
    runner = ScriptRunner(win)
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    runner.start(parse("wait-for-status 60 to secure it"), source="t")
    assert process_until(lambda: runner._deadline is not None)
    win._rip_worker = None
    status.text = "Rip complete"
    assert process_until(lambda: bool(emitted), timeout=10.0)
    step = emitted[0].steps[-1]
    assert step.outcome is Outcome.FAIL
    assert "the rip ended" in step.detail


def test_it_times_out_naming_what_the_status_did_say(
    qapp: Any, process_until: Any
) -> None:
    win = _window(rip_progress=_Status("Ripping track 1… 3%"), rip_worker=object())
    step = _step_outcome(
        ScriptRunner(win), qapp, process_until, "wait-for-status 0.3 to secure it"
    )
    assert step.outcome is Outcome.FAIL
    assert "Ripping track 1" in step.detail


@pytest.mark.parametrize("seconds", ["0", "-5", "10801", "later"])
def test_a_wait_outside_its_range_is_refused(
    qapp: Any, process_until: Any, seconds: str
) -> None:
    step = _step_outcome(
        ScriptRunner(_window(rip_progress=_Status())),
        qapp,
        process_until,
        f"wait-for-status {seconds} to secure it",
    )
    assert step.outcome is Outcome.ERROR


# --- The committed scripts use them where the review said ----------------------------


def _verbs_of_section(script: str, header: str) -> list[str]:
    text = (_RIG_SCRIPTS / script).read_text(encoding="utf-8")
    assert text.count(f"log --- {header}. ") == 1, f"section {header} is not there"
    body = text.split(f"log --- {header}. ", 1)[1].split("\nlog --- ", 1)[0]
    return [step.source for step in parse("log --- x\n" + body) if step.verb][1:]


def test_d2_presses_settings_ok_and_proves_ok_wrote_the_file() -> None:
    lines = _verbs_of_section("fullacceptance.txt", "D2")
    order = [
        next(i for i, ln in enumerate(lines) if ln.startswith(prefix))
        for prefix in ("set ", "wait 3", "open settings", "ok", "expect-config-saved 2")
    ]
    assert order == sorted(order), lines
    assert any(ln.startswith("expect-drive-offset") for ln in lines)


def test_h2_presses_cancel_then_replace_on_its_own_album() -> None:
    lines = _verbs_of_section("fullacceptance.txt", "H2")
    cancel = lines.index("answer-dialog click=cancel 120 Album already ripped")
    replace = lines.index("answer-dialog click=replace 120 Album already ripped")
    assert lines[cancel + 1] == "expect-no-rip"
    assert cancel < replace
    assert "expect-rip-complete" in lines[replace:]
    album = next(ln for ln in lines if ln.startswith("album "))
    assert "angle<bracket" not in album, "H2 must not Replace section F's album"


def test_the_unknown_disc_run_cancels_in_its_securing_pass() -> None:
    lines = _verbs_of_section("unknowndiscacceptance.txt", "G")
    wait = next(i for i, ln in enumerate(lines) if ln.startswith("wait-for-status"))
    assert "to secure it" in lines[wait]
    cancel = lines.index("cancel-rip")
    assert wait < cancel
    assert "expect-log-well-formed" in lines[cancel:]
