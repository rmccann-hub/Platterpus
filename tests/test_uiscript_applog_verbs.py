"""`app-log` and `sigterm-world`: this launch's own log, read by the run (A4).

TASKS *"Fold the hardware-only checks into the closing run"* (2026-10-05). Two
open rows are settled only by what the app logged during a drive run: whether a
probe waited for the first container command (*"Cold-container start"*), and
whether a cancel's SIGTERM reaches the ripper inside the container (*"If a podman
ever forwards the wrapper's SIGTERM"*).

**Tested against the filed run, not only against lines written here.** The
2026-10-05 Full run's app log and its cancelled rip's log are committed
(``docs/handshake/artifactsround30/round30oct05full*``); the predicate is run on
them, and the log lines it keys on are tied to the product code that writes them.
"""

from __future__ import annotations

import inspect
import logging
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from test_uiscript_rip_verbs import _run_one, _window

from platterpus import container_gate, drive_control, log_buffer
from platterpus.logging_setup import _LOG_FORMAT
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.ui.main_window_rip import RipMixin
from platterpus.uiscript import applog_verbs as av
from platterpus.uiscript.report import Outcome

_FILED = Path(__file__).resolve().parent.parent / "docs/handshake/artifactsround30"
_APPLOG = _FILED / "round30oct05fullplatterpusapplog1.txt"
_CANCELLED = _FILED / "round30oct05fullcancelme.log"


@pytest.fixture
def session_buffer() -> Iterator[log_buffer.SessionLogBuffer]:
    """A real session buffer on the root logger, formatted as the product's."""
    buffer = log_buffer.SessionLogBuffer()
    buffer.setFormatter(logging.Formatter(_LOG_FORMAT))
    buffer.setLevel(logging.DEBUG)
    root = logging.getLogger()
    before = (log_buffer.get_session_buffer(), root.level)
    root.addHandler(buffer)
    root.setLevel(logging.DEBUG)
    log_buffer.set_session_buffer(buffer)
    try:
        yield buffer
    finally:
        root.removeHandler(buffer)
        log_buffer.set_session_buffer(before[0])
        root.setLevel(before[1])


# --- The keys are the product's own words --------------------------------------


def test_the_marks_are_the_lines_the_product_writes() -> None:
    cancel = inspect.getsource(RipMixin._on_rip_cancel)
    rescue = inspect.getsource(RipMixin._auto_force_stop)
    assert av.CANCEL_MARK in cancel
    assert av.RESCUE_MARK in rescue
    gate = inspect.getsource(container_gate.FirstEntryGate)
    # The needle section A uses, in both of the gate's lines (waited / gave up).
    assert gate.count("for the first container command") == 2


def test_every_rescue_outcome_logs_a_line_the_reader_knows(
    session_buffer: log_buffer.SessionLogBuffer,
) -> None:
    """Driven through the real `term_unsignalled_holders`, each arm's own line."""

    def fuser(rc: int) -> Any:
        def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(argv, rc, "", "")

        return run

    assert (
        drive_control.term_unsignalled_holders("/dev/sr0", None, fuser(0))
        == "signalled"
    )
    signalled = session_buffer.snapshot_excluding([]).lines
    assert av.rescue_outcome([f"x {av.RESCUE_MARK}", *signalled]) == av.SIGNALLED
    before = len(session_buffer.snapshot_excluding([]).lines)
    assert drive_control.term_unsignalled_holders("/dev/sr0", None, fuser(1)) == (
        "nothing held it"
    )
    free = session_buffer.snapshot_excluding([]).lines[before:]
    assert av.rescue_outcome([f"x {av.RESCUE_MARK}", *free]) == av.NOTHING_HELD


def test_the_empty_holder_arm_now_logs_its_outcome(
    session_buffer: log_buffer.SessionLogBuffer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one arm that returned without a line; `sigterm-world` would read its
    silence as no outcome at all."""
    monkeypatch.setattr(drive_control, "device_holders", lambda *_a, **_k: [])
    reached = drive_control.SignalledRipper(pid=99999, pgid=99999, sent_at=0.0)
    assert drive_control.term_unsignalled_holders("/dev/sr0", reached) == (
        "nothing held it"
    )
    lines = session_buffer.snapshot_excluding([]).lines
    assert av.rescue_outcome([f"x {av.RESCUE_MARK}", *lines]) == av.NOTHING_HELD


# --- The pure answers ------------------------------------------------------------


def test_matching_lines_keeps_head_and_tail_and_counts_the_gap() -> None:
    lines = [f"line {n} First Container Command" for n in range(30)]
    shown = av.matching_lines(lines, "first container command")
    assert len(shown) == av.APP_LOG_LINES_SHOWN + 1
    assert shown[0] == lines[0] and shown[-1] == lines[-1]
    assert "18 more line(s)" in shown[av.APP_LOG_LINES_SHOWN // 2]
    assert av.matching_lines(lines[:3], "FIRST") == lines[:3]


@pytest.mark.parametrize(
    ("rescue", "footer", "says"),
    [
        (av.SIGNALLED, True, "ONE SIGNAL"),
        (av.SIGNALLED, False, "SECOND SIGNAL"),
        (av.NOTHING_HELD, True, "FORWARDED"),
        (av.REFUSED, True, "NOT THE CONTAINER PATH"),
        (av.NOT_LOGGED, True, "NOT DETERMINED"),
        (av.NO_RESCUE, True, "NOT DETERMINED"),
        (av.SIGNALLED, None, "NOT DETERMINED"),
    ],
)
def test_each_world_is_named_and_unknown_is_never_an_answer(
    rescue: str, footer: bool | None, says: str
) -> None:
    assert av.sigterm_world(rescue, footer).startswith(says)


def test_the_filed_2026_10_05_cancel_reads_one_signal() -> None:
    """The committed run: the rescue fired 4.75 s after Cancel, `fuser` exit 0,
    and the log was signed one second later. One signal, read from the artifacts."""
    lines = _APPLOG.read_text(encoding="utf-8", errors="replace").splitlines()
    after = av.lines_after_last(lines, av.CANCEL_MARK)
    assert after is not None, "the filed app log holds no cancel"
    rescue = av.rescue_outcome(after)
    assert rescue == av.SIGNALLED
    signed = parse_cyanrip_log(_CANCELLED.read_text(encoding="utf-8")).rip_completed
    assert signed is not None, "the filed cancelled log has no footer"
    assert av.sigterm_world(rescue, signed is not None).startswith("ONE SIGNAL")


# --- The handlers ----------------------------------------------------------------


def test_app_log_copies_matching_lines_and_says_what_it_could_see(
    qapp: Any, session_buffer: log_buffer.SessionLogBuffer
) -> None:
    logging.getLogger("platterpus.container_gate").info(
        "cyanrip --version waits for the first container command of this session "
        "to finish, so the container is not started twice at once"
    )
    record, _runner = _run_one(_window(), "app-log for the first container command")
    assert record.outcome is Outcome.INFO
    assert "waits for the first container command" in record.detail
    assert "logged since launch" in record.detail

    record, _runner = _run_one(_window(), "app-log nothing logs this sentence")
    assert record.outcome is Outcome.INFO and record.detail.startswith("no line")


def test_app_log_without_a_buffer_is_not_determined(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(log_buffer, "get_session_buffer", lambda: None)
    record, _runner = _run_one(_window(), "app-log anything")
    assert record.outcome is Outcome.INFO and "not determined" in record.detail


def test_sigterm_world_reads_a_cancel_and_the_logs_footer(
    qapp: Any, session_buffer: log_buffer.SessionLogBuffer
) -> None:
    log = logging.getLogger("platterpus.ui.main_window_rip")
    log.info("%s; arming the 5s force-stop rescue", av.CANCEL_MARK)
    log.info("%s to whatever holds /dev/sr0", av.RESCUE_MARK)
    logging.getLogger("platterpus.drive_control").info("fuser -k TERM /dev/sr0 rc=0")
    parsed = parse_cyanrip_log(_CANCELLED.read_text(encoding="utf-8"))
    win = _window(last_rip_log=parsed, last_rip_log_file=_CANCELLED)
    record, _runner = _run_one(win, "sigterm-world")
    assert record.outcome is Outcome.INFO
    assert record.detail.startswith("ONE SIGNAL"), record.detail
    assert "fuser -k TERM /dev/sr0 rc=0" in record.detail


def test_sigterm_world_with_no_cancel_is_not_determined(
    qapp: Any, session_buffer: log_buffer.SessionLogBuffer
) -> None:
    record, _runner = _run_one(_window(), "sigterm-world")
    assert record.outcome is Outcome.INFO and record.detail.startswith("NOT DETERMINED")


# --- The closing run carries each check, naming its row ---------------------------

_ACCEPTANCE = Path(__file__).resolve().parent.parent / (
    "src/platterpus/rig_scripts/fullacceptance.txt"
)


def _sections() -> dict[str, list[str]]:
    """``{section letter: its step lines}`` of the full acceptance script."""
    out: dict[str, list[str]] = {}
    current = ""
    for raw in _ACCEPTANCE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("log --- "):
            current = line[len("log --- ") :].split(".", 1)[0]
        if current and line and not line.startswith("#"):
            out.setdefault(current, []).append(line)
    return out


def test_each_folded_check_is_a_step_that_names_its_tasks_row() -> None:
    """A4: the bundle closes the rows, so each step's neighbour names its row."""
    sections = _sections()
    assert len(sections) >= 20, "floor: the script's sections were not read"
    a, i = sections["A"], sections["I"]
    assert "app-log for the first container command" in a
    assert any('TASKS "Cold-container start"' in ln for ln in a)
    assert i.index("cancel-rip") < i.index("sigterm-world")
    assert any("forwards the wrapper's SIGTERM" in ln for ln in i)
    assert any('TASKS "S25 on hardware"' in ln for ln in i)
    # The screenshot row: named beside each screenshot that follows a long or
    # post-cancel rip, where the 2026-09-30 run's screenshots failed.
    for section, shot in (
        ("F", "screenshot afterfullrip"),
        ("H", "screenshot afteroverwrite"),
        ("J", "screenshot afterrecovery"),
        ("K3", "screenshot afterwav"),
        ("N", "screenshot aftersecurereread"),
    ):
        lines = sections[section]
        named = lines[lines.index(shot) - 1]
        assert "Three screenshot steps found no window on screen" in named, section
