"""The rip report is written off the GUI thread, and stays correct doing it.

`rip_report.write_report` was called directly from the GUI thread on the strength
of its own docstring — *"writing a small JSON file is cheap, so this is safe to
call on the GUI thread"*. Measured against a real artifact it is a **5.2 MB**
document: ~46 ms to serialise, 15-40 ms for the atomic write and its two
``fsync``s on local SSD, **206 ms** into a directory holding fresh FLAC
writeback. Six to eight times per rip. Two docstrings asserted the safety on size
grounds and both were measuring an assumption.

Moving it off-thread creates its own new state, which is what these tests are
mostly about (`CLAUDE.md`: *what new state does this fix create, and what tests
that?*):

* two writers on one file would tear the artifact — hence one worker;
* a stale write landing after a fresher one would silently regress the report to
  an earlier state, and it would still parse — hence newest-wins with a single
  consumer;
* a write dropped at window close would lose the final report — hence a bounded
  `flush`, which **reports** when it times out instead of returning silently.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from platterpus import report_writer
from platterpus.report_writer import ReportWriter


def _slow_job(record: list[int], number: int, delay: float = 0.0):
    def run() -> Path | None:
        if delay:
            time.sleep(delay)
        record.append(number)
        return Path(f"/tmp/report-{number}.json")

    return run


class TestNewestWins:
    def test_the_newest_job_always_runs(self) -> None:
        """The one non-negotiable property. Superseding is only lossless because
        every report carries ALL accumulated results, so the newest strictly
        contains every earlier one — but that argument collapses if the newest
        is itself the one dropped."""
        writer = ReportWriter()
        ran: list[int] = []
        for n in range(8):
            writer.submit(_slow_job(ran, n))
        assert writer.flush(5.0), "flush timed out"
        writer.stop()
        assert ran, "nothing ran at all"
        assert max(ran) == 7, f"the newest job did not run: {ran}"

    def test_superseded_jobs_are_actually_skipped(self) -> None:
        """The floor. Without it this class would pass on an implementation that
        simply ran everything, and the memory bound would be a fiction."""
        writer = ReportWriter()
        ran: list[int] = []
        # A slow first job holds the worker while the rest pile into the slot.
        writer.submit(_slow_job(ran, 0, delay=0.30))
        time.sleep(0.05)  # let it start
        for n in range(1, 20):
            writer.submit(_slow_job(ran, n))
        assert writer.flush(5.0)
        writer.stop()
        assert len(ran) < 20, f"nothing was coalesced: {ran}"
        assert 19 in ran, f"the newest was dropped: {ran}"

    def test_a_stale_write_never_lands_after_a_fresher_one(self) -> None:
        """The failure this ordering exists to prevent: the report on disk
        silently regressing to an earlier revision. It would still be valid JSON
        and still parse, which is why nothing downstream would notice."""
        writer = ReportWriter()
        order: list[int] = []
        for n in range(6):
            writer.submit(_slow_job(order, n, delay=0.02))
        assert writer.flush(5.0)
        writer.stop()
        assert order == sorted(order), f"writes completed out of order: {order}"


class TestFlushIsHonest:
    def test_flush_waits_for_an_in_flight_write(self) -> None:
        writer = ReportWriter()
        ran: list[int] = []
        writer.submit(_slow_job(ran, 1, delay=0.25))
        assert writer.flush(5.0), "flush returned before the write finished"
        assert ran == [1], "flush returned while the job was still running"
        writer.stop()

    def test_flush_reports_false_when_it_times_out(self) -> None:
        """It must not return silently. A caller that cannot tell a completed
        write from an abandoned one will report the report as complete, which is
        the silent-truncation-reads-as-completeness shape."""
        writer = ReportWriter()
        release = threading.Event()

        def blocked() -> Path | None:
            release.wait(timeout=5.0)
            return None

        writer.submit(blocked)
        time.sleep(0.05)
        try:
            assert writer.flush(0.2) is False
        finally:
            release.set()
            writer.stop()

    def test_flush_on_a_writer_that_never_ran_is_true(self) -> None:
        """Nothing pending is a complete state, not a timeout."""
        assert ReportWriter().flush(0.1) is True


class TestTheWorkerSurvives:
    def test_a_raising_job_does_not_kill_the_writer(self) -> None:
        """The next post-rip check will submit again. A dead writer would stop
        producing the one artifact a user uploads, silently."""
        writer = ReportWriter()
        ran: list[int] = []

        def boom() -> Path | None:
            raise RuntimeError("write blew up")

        writer.submit(boom)
        assert writer.flush(5.0)
        writer.submit(_slow_job(ran, 42))
        assert writer.flush(5.0)
        writer.stop()
        assert ran == [42], "the writer died on the first exception"

    def test_submitting_after_stop_restarts_rather_than_dropping(self) -> None:
        """`stop()` ends the thread, not the writer.

        The first implementation latched a `_stopping` flag and refused later
        work with a warning. Wrong trade, and the tests found it: this is a
        process-wide singleton, so a single close would have disarmed report
        writing for everything afterwards — including a late queued signal
        arriving during teardown, which is precisely when the report matters.
        Writing one late beats dropping it.
        """
        writer = ReportWriter()
        writer.stop()
        ran: list[int] = []
        writer.submit(_slow_job(ran, 1))
        assert writer.flush(5.0), "the writer did not restart"
        assert ran == [1], "a report submitted after stop() was dropped"
        writer.stop()


class TestWiredIntoTheWindow:
    """The revert-proof. These fail if the write goes back on the GUI thread."""

    def test_the_window_submits_instead_of_calling_write_report(self) -> None:
        """Read the source: `_write_rip_report` must hand the call to the writer,
        not perform it. Asserted structurally because the alternative — trusting
        a comment that says it is off-thread — is the shape that produced the bug
        in the first place (two docstrings asserted safety on size grounds)."""
        import inspect

        from platterpus.ui.main_window_rip import RipMixin

        src = inspect.getsource(RipMixin._write_rip_report)
        assert "report_writer.writer().submit(" in src, (
            "the report write is no longer routed through the writer thread"
        )
        # The give-away for a regression: a direct call would appear as
        # `rip_report.write_report(` rather than as a partial handed to submit().
        assert "rip_report.write_report(\n" not in src, (
            "write_report is being called directly again — that is the 5 MB "
            "serialize + fsync back on the GUI thread"
        )
        assert "partial(" in src, "the payload must be snapshotted eagerly"

    def test_close_waits_for_the_pending_write(self) -> None:
        """`closeEvent` must pass wait=True, or the last report dies with the
        process now that the write is asynchronous."""
        import inspect

        from platterpus.ui.main_window import MainWindow

        src = inspect.getsource(MainWindow.closeEvent)
        assert "_flush_rip_report(wait=True)" in src, (
            "close no longer waits for the report; the final revision is lost"
        )

    def test_flush_without_wait_does_not_block(self) -> None:
        """The debounce-timer slot runs on the GUI thread and must stay
        non-blocking — waiting there would put the freeze straight back."""
        import inspect

        from platterpus.ui.main_window_rip import RipMixin

        src = inspect.getsource(RipMixin._flush_rip_report)
        head = src.split("if wait:", 1)[0]
        # `writer().stop()`, not a bare "stop()" — the debounce timer's own
        # `_rip_report_timer.stop()` lives in this half and is correct there.
        # The first draft of this assertion matched that and failed on working
        # code: a substring check that hits the wrong subject is the same class
        # of mistake as a check that passes for the wrong reason.
        assert "writer().stop()" not in head, "the non-wait path blocks on the writer"
        assert "flush(" not in head, "the non-wait path waits on the writer"


class TestTheSharedWriter:
    def test_writer_is_a_singleton(self) -> None:
        """Two instances would be two threads on one file — the tear this
        design removes by construction."""
        assert report_writer.writer() is report_writer.writer()


class TestTheDocstringsNoLongerLie:
    """The false claims are load-bearing history, not decoration: they are the
    reason nobody measured this for six releases."""

    @pytest.mark.parametrize(
        ("module", "banned"),
        [
            ("platterpus.rip_report", "safe to call on the GUI thread"),
            ("platterpus.atomic_write", "these are tiny files"),
        ],
    )
    def test_no_module_still_claims_the_write_is_cheap(
        self, module: str, banned: str
    ) -> None:
        import importlib
        import inspect

        source = inspect.getsource(importlib.import_module(module))
        # The phrase may survive INSIDE a correction that quotes it; what must
        # not survive is an unqualified assertion. Require the correction nearby.
        if banned in source:
            assert "false" in source.lower() or "used to say" in source.lower(), (
                f"{module} still asserts {banned!r} without the correction"
            )
