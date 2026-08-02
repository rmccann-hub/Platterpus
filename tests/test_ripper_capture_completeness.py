"""Everything the ripper told us has to survive into the report.

Prompted by the maintainer, 2026-08-02: *"is there any output or error the log
file does not capture? it needs them all, and all context to fix anything."* The
audit that question forced found three real holes, and this file is the floor
under all three.

1. **The retained stdout was head-only.** Past a 20 000-line cap the worker
   simply stopped appending, reasoned as "the head holds the header and the
   earliest tracks". True of a rip that succeeds and exactly wrong for one that
   fails: a ripper's fatal message is the *last* thing it prints, so the single
   line a runaway most needed to keep was the one guaranteed to be dropped —
   and dropped with nothing recording that a drop had occurred.
2. **The exit code was computed and discarded.** `1` (the ripper refused an
   argument), `0` plus a cancel (the user stopped a healthy run), and `-9` (we
   SIGKILLed a wedged process group) are three different failures that rendered
   identically in the report.
3. **The argv was never recorded.** The one argument defect that has killed a
   whole rip — `-t 17=` against a 16-track disc — was diagnosed from files the
   maintainer uploaded by hand, because our own report did not carry the
   command line.

The through-line: each was a fact we *had* and threw away, which is worse than
one we never obtained, because the report looked complete either way.
"""

from __future__ import annotations

import subprocess
import sys

from platterpus.adapters.rip_backend import RipHandle
from platterpus.rip_report import build_outcome
from platterpus.workers import rip_worker as rw


class _Sink:
    """The retention half of ``RipWorker`` with none of the Qt.

    Deliberately mirrors the worker's real loop body rather than calling it: the
    loop needs a live subprocess, a thread and a signal target, and a fixture
    that supplied all three would be testing the fixture. The mirrored lines are
    pinned by :func:`test_the_worker_still_uses_the_constants_this_mirrors`, so
    the stand-in cannot drift away from the product without failing — the
    harness-fidelity rule (``docs/testing.md`` §5.t).
    """

    def __init__(self) -> None:
        self._stdout_lines: list[str] = []
        self._stdout_tail: list[str] = []
        self._stdout_elided: int = 0

    def feed(self, line: str) -> None:
        if len(self._stdout_lines) < rw._MAX_STDOUT_LINES:
            self._stdout_lines.append(line)
        else:
            self._stdout_tail.append(line)
            if len(self._stdout_tail) > rw._STDOUT_TAIL_LINES:
                self._stdout_tail.pop(0)
                self._stdout_elided += 1

    captured_stdout = rw.RipWorker.captured_stdout


# --- 1. the tail, where the error is -----------------------------------------


def test_a_short_rip_is_captured_verbatim_with_no_marker() -> None:
    """Inertness: the overwhelmingly common case must be byte-identical to
    before, or this fix would have changed every normal report."""
    sink = _Sink()
    for i in range(500):
        sink.feed(f"line {i}")
    text = sink.captured_stdout
    assert text.splitlines() == [f"line {i}" for i in range(500)]
    assert "elided" not in text


def test_the_last_line_survives_a_runaway_ripper() -> None:
    """The bug. The fatal message is the final line, and it must be in there."""
    sink = _Sink()
    total = rw._MAX_STDOUT_LINES + rw._STDOUT_TAIL_LINES + 5_000
    for i in range(total - 1):
        sink.feed(f"noise {i}")
    sink.feed("Invalid track number 17, list has 16 tracks!")

    text = sink.captured_stdout
    assert text.splitlines()[-1] == "Invalid track number 17, list has 16 tracks!"
    # And the head is still there — this is head+tail, not a ring buffer that
    # discarded the version banner and the early per-track results.
    assert text.splitlines()[0] == "noise 0"


def test_the_discarded_middle_is_declared_and_counted() -> None:
    """An unmarked jump would read as a ripper that fell silent, which is a
    different and more alarming fact than "we truncated it"."""
    sink = _Sink()
    overflow = 5_000
    total = rw._MAX_STDOUT_LINES + rw._STDOUT_TAIL_LINES + overflow
    for i in range(total):
        sink.feed(f"line {i}")

    lines = sink.captured_stdout.splitlines()
    markers = [ln for ln in lines if "elided" in ln]
    assert len(markers) == 1, "exactly one elision marker"
    assert str(overflow) in markers[0], f"the count must be stated: {markers[0]}"
    # The marker is ours, not something the ripper could have printed, so a
    # reader (or a parser) can tell an elision from real output.
    assert markers[0].startswith("[platterpus]")


def test_the_retained_size_stays_bounded() -> None:
    """The cap still caps. A tail that grew without limit would reintroduce the
    unbounded-memory problem the original stop existed to prevent."""
    sink = _Sink()
    for i in range(rw._MAX_STDOUT_LINES * 3):
        sink.feed(f"line {i}")
    kept = len(sink.captured_stdout.splitlines())
    assert kept <= rw._MAX_STDOUT_LINES + rw._STDOUT_TAIL_LINES + 1  # +1 marker


def test_the_worker_still_uses_the_constants_this_mirrors() -> None:
    """Harness fidelity. `_Sink` reimplements the worker's retention, so if the
    worker stops using these names the stand-in is silently testing nothing."""
    source = rw.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    for name in ("_MAX_STDOUT_LINES", "_STDOUT_TAIL_LINES", "_stdout_tail"):
        assert text.count(name) >= 2, f"{name} is no longer used by the worker"
    assert "self._stdout_tail.pop(0)" in text, (
        "the worker's rolling-window trim changed shape; _Sink no longer mirrors it"
    )


# --- 2 and 3. exit code and argv ----------------------------------------------


def test_the_outcome_block_distinguishes_the_three_failure_shapes() -> None:
    """These three rendered identically before, and they need different fixes."""
    refused = build_outcome(status="failed", ripper_exit_code=1)
    cancelled = build_outcome(status="cancelled", ripper_exit_code=0)
    killed = build_outcome(status="cancelled", ripper_exit_code=-9)
    codes = {
        refused["ripper_exit_code"],
        cancelled["ripper_exit_code"],
        killed["ripper_exit_code"],
    }
    assert codes == {1, 0, -9}


def test_an_unreaped_child_records_none_not_zero() -> None:
    """A child wedged in a drive ioctl is never reaped, and `0` there would read
    as a clean exit — the same "did not happen vs happened and found nothing"
    error this codebase keeps making."""
    assert build_outcome(status="failed")["ripper_exit_code"] is None


def test_the_argv_is_recorded_and_a_missing_one_is_null_not_empty() -> None:
    """`[]` would mean "invoked with no arguments"; `null` means "never
    launched". Those are different, and the second is a bug report."""
    with_argv = build_outcome(
        status="failed", ripper_argv=("cyanrip", "-N", "-t", "17=")
    )
    assert with_argv["ripper_argv"] == ["cyanrip", "-N", "-t", "17="]
    assert with_argv["ripper_command_display"] == "cyanrip -N -t 17="

    without = build_outcome(status="failed", ripper_argv=())
    assert without["ripper_argv"] is None
    assert without["ripper_command_display"] is None


def test_the_report_carries_the_argument_that_killed_a_real_rip() -> None:
    """The concrete regression: this exact argv ended a rip in two seconds with
    nothing ripped, and the report of it could not say why."""
    argv = ("cyanrip", "-d", "/dev/sr0", "-N", "-t", "17=", "-t", "18=")
    outcome = build_outcome(
        status="failed",
        failure_hint="Invalid track number 17, list has 16 tracks!",
        ripper_exit_code=1,
        ripper_argv=argv,
    )
    assert "-t" in (outcome["ripper_argv"] or [])
    assert "17=" in (outcome["ripper_argv"] or [])
    assert outcome["ripper_exit_code"] == 1
    assert "16 tracks" in (outcome["failure_hint"] or "")


def test_the_handle_reports_the_argv_the_os_received() -> None:
    """Read off `Popen.args` rather than passed in beside it, so it cannot drift
    from what was actually spawned. Uses a real process — a stub `.args` would
    prove only that we can read an attribute we set ourselves."""
    argv = [sys.executable, "-c", "print('hi')"]
    process = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        assert RipHandle(process).argv == tuple(argv)
    finally:
        process.stdout.close() if process.stdout else None
        process.wait(timeout=30)


def test_the_handle_argv_survives_a_string_command() -> None:
    """`Popen` accepts a bare string with `shell=True`; the property must return
    a tuple either way rather than exploding the string into characters."""

    class _FakeProcess:
        args = "cyanrip -N"

    handle = RipHandle.__new__(RipHandle)
    handle._process = _FakeProcess()  # type: ignore[assignment]  # duck-typed args only
    assert handle.argv == ("cyanrip -N",)
