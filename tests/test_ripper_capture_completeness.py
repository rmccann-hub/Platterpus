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
4. **Every track's outcome line was left out** (found later, 2026-10-05, by the
   cyanrip fork: round 30 lap 9 S29). The test for "is this a redraw?" was "does
   this line move the bar?", and `Track N read successfully!` moves the bar.
   Redraws are now thinned per run, first and last kept and the rest counted,
   and the report's label says exactly that.

The through-line: each was a fact we *had* and threw away, which is worse than
one we never obtained, because the report looked complete either way.
"""

from __future__ import annotations

import re
import subprocess
import sys

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import inbound_text, report_artifacts
from platterpus.adapters.rip_backend import RipHandle
from platterpus.parsers.cyanrip_log import finished_track
from platterpus.redraw_run import REDRAW_ELISION_PHRASE, RedrawRun
from platterpus.rip_report import build_outcome
from platterpus.workers import rip_worker as rw


class _Sink:
    """The retention half of ``RipWorker`` with none of the Qt.

    The loop needs a live subprocess, a thread and a signal target, and a fixture
    that supplied all three would be testing the fixture, so this holds only the
    worker's retention STATE and borrows the worker's own retention METHODS. It
    used to re-implement the head/tail trim in ``feed``; since 2026-10-05 (round
    30 lap 9 S29, the redraw runs) it calls the product's method instead, so there
    is no mirrored body left to drift. The fields are still pinned by
    :func:`test_the_worker_still_uses_the_constants_this_mirrors` — the
    harness-fidelity rule (``docs/testing.md`` §5.t).
    """

    def __init__(self) -> None:
        self._stdout_lines: list[str] = []
        self._stdout_tail: list[str] = []
        self._stdout_elided: int = 0
        # The open run of progress redraws (`redraw_run`).
        self._redraw_run: RedrawRun = RedrawRun()
        # The worker's screening tally (`inbound_text`), which `captured_stdout`
        # reads to decide whether to add its note. Mirrored, like the fields
        # above, so the borrowed method runs against the worker's real state.
        self._inbound: inbound_text.Tally = inbound_text.Tally()

    _capture_line = rw.RipWorker._capture_line
    _retain_stdout_line = rw.RipWorker._retain_stdout_line
    _store_line = rw.RipWorker._store_line
    _flush_redraw_run = rw.RipWorker._flush_redraw_run
    captured_stdout = rw.RipWorker.captured_stdout

    def feed(self, line: str) -> bool:
        """One line, through the worker's own routing; True when it was a redraw."""
        return self._capture_line(line, line)


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
    """Harness fidelity. `_Sink` supplies the worker's retention fields to the
    worker's own methods (until 2026-10-05 it reimplemented the trim), so if the
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


# --- 4. a track's outcome line, and the redraws around it ---------------------
#
# Round 30 lap 9 S29 (the cyanrip fork, reading the 2026-10-05 Full run): the
# capture never carried `Track N read successfully!` or `read with errors.`. The
# worker asked `_progress_for(line) is not None` to decide what to leave out, and an
# outcome line moves the bar, so it was left out with the redraws, while the report
# called the capture "complete even when the ripper was killed".

_PHRASE = re.escape(REDRAW_ELISION_PHRASE)
_REDRAW_MARKER = re.compile(rf"^\[platterpus\] … (?P<count>\d+) {_PHRASE} …$")

#: Every shape `_progress_for` gives a bar value for, and what the capture does with
#: it: True for a redraw (thinned), False for a line kept as it is. The previous
#: backend's three shapes are redraws in the format they were written for.
_DECISIONS: tuple[tuple[str, bool], ...] = (
    ("Ripping track 5, progress - 42.37%, ETA - 3m, errors - 0", True),
    ("Ripping and encoding track 5, progress - 100.00%", True),
    ("Reading TOC  50 %", True),
    ("Reading track 3 of 16 (1 of 9) ...  42 %", True),
    ("Getting length of audio track (1 of 16) ... 100 %", True),
    ("Track 5 read successfully!", False),
    ("Track 5 read with errors.", False),
    ("Track 5 ripped and encoded successfully!", False),
    ("Track 5 ripped and encoded with errors.", False),
    # An outcome line that also contains a redraw's words is an outcome: the safe
    # direction, since calling a line a redraw can cost a verdict.
    ("Track 5 read with errors. Ripping track 5, progress - 1.00%", False),
    # Lines `_progress_for` gives no value for, which were always kept.
    ("Disc tracks:    14", False),
    ("Flushing encoders...", False),
    ("Done; (2 out of 2 matches for current checksum ABCD1234)", False),
    ("Repeating ripping (1 out of 3 matches for current checksum ABCD1234)", False),
    ("Trying to quit", False),
)


def test_each_shape_the_bar_reads_is_decided() -> None:
    """The enumeration the fix was asked for, as a table the predicate is held to."""
    for line, redraw in _DECISIONS:
        assert rw._is_progress_redraw(line) is redraw, line
    # Both sides populated, so the table cannot pass by finding nothing.
    assert sum(r for _, r in _DECISIONS) == 5
    assert sum(not r for _, r in _DECISIONS) >= 5


def test_a_run_keeps_its_first_and_last_and_counts_the_middle() -> None:
    """Five redraws: the first, a marker counting three, the last, then the outcome."""
    sink = _Sink()
    redraws = [f"Ripping track 2, progress - {p}.00%" for p in range(1, 6)]
    for line in redraws:
        sink.feed(line)
    sink.feed("Track 2 read with errors.")
    assert sink.captured_stdout.splitlines() == [
        redraws[0],
        f"[platterpus] … 3 {REDRAW_ELISION_PHRASE} …",
        redraws[-1],
        "Track 2 read with errors.",
    ]


def test_runs_of_one_and_two_carry_no_marker() -> None:
    """A marker counting zero would claim an elision that did not happen."""
    sink = _Sink()
    sink.feed("Ripping track 1, progress - 100.00%")
    sink.feed("Track 1 read successfully!")
    sink.feed("Ripping track 2, progress - 1.00%")
    sink.feed("Ripping track 2, progress - 100.00%")
    sink.feed("Track 2 read successfully!")
    text = sink.captured_stdout
    assert REDRAW_ELISION_PHRASE not in text
    assert len(text.splitlines()) == 5


def test_an_open_run_is_shown_and_reading_the_capture_does_not_close_it() -> None:
    """The ripper's last output can be redraws (killed mid-read). The capture shows
    them, and reading it twice, as the report's re-writes do, changes nothing."""
    sink = _Sink()
    sink.feed("Summary:")
    for p in (1, 2, 3, 4):
        sink.feed(f"Ripping track 7, progress - {p}.00%, errors - 2")
    first_read = sink.captured_stdout
    assert first_read == sink.captured_stdout
    assert first_read.splitlines() == [
        "Summary:",
        "Ripping track 7, progress - 1.00%, errors - 2",
        f"[platterpus] … 2 {REDRAW_ELISION_PHRASE} …",
        "Ripping track 7, progress - 4.00%, errors - 2",
    ]
    # The run is still open: one more redraw joins it rather than starting another.
    sink.feed("Ripping track 7, progress - 5.00%, errors - 3")
    assert f"… 3 {REDRAW_ELISION_PHRASE} …" in sink.captured_stdout
    assert sink.captured_stdout.splitlines()[-1].endswith("5.00%, errors - 3")


def test_the_reports_label_says_what_the_worker_keeps() -> None:
    """Two surfaces, one fact. The label quotes the marker the worker writes, and no
    longer claims a completeness the capture never had."""
    label = report_artifacts.RIPPER_STDOUT_LABEL
    assert REDRAW_ELISION_PHRASE in label
    assert "complete" not in label.lower()
    assert "every line in order" in label
    block = report_artifacts.build_artifacts(ripper_stdout="Summary:\n")
    assert block["ripper_stdout"]["source"] == label


# Lines that cannot match a redraw shape (no `%`, no `(`) and are not outcomes.
_plain = st.text(
    alphabet=st.characters(blacklist_characters="%(\n\r", blacklist_categories=("Cs",)),
    max_size=40,
).filter(lambda s: finished_track(s) is None)
_redraw = st.builds(
    "Ripping{} track {}, progress - {:.2f}%{}".format,
    st.sampled_from(["", " and encoding"]),
    st.integers(min_value=1, max_value=99),
    st.floats(min_value=0, max_value=100),
    st.sampled_from(["", ", ETA - 3m", ", ETA - 0s, errors - 7"]),
)
_outcome = st.builds(
    "Track {} {}".format,
    st.integers(min_value=1, max_value=99),
    st.sampled_from(["read successfully!", "read with errors."]),
)


@settings(max_examples=200, deadline=None)
@given(
    st.lists(
        st.one_of(
            st.tuples(st.just(True), _redraw),
            st.tuples(st.just(False), _plain),
            st.tuples(st.just(False), _outcome),
        ),
        max_size=120,
    )
)
def test_the_capture_is_the_stream_with_each_run_thinned(
    stream: list[tuple[bool, str]],
) -> None:
    """The completeness claim as a property, against an oracle that knows each line's
    kind from how it was MADE, not from the predicate.

    Every non-redraw line is kept, in order; each run of redraws is its first line,
    a marker counting the middle when there is one, and its last; and every redraw
    fed is either shown or counted.
    """
    sink = _Sink()
    expected: list[str] = []
    run: list[str] = []

    def close() -> None:
        if run:
            middle = len(run) - 2
            expected.append(run[0])
            if middle > 0:
                expected.append(f"[platterpus] … {middle} {REDRAW_ELISION_PHRASE} …")
            if len(run) > 1:
                expected.append(run[-1])
            run.clear()

    for is_redraw, line in stream:
        assert sink.feed(line) is is_redraw, line
        if is_redraw:
            run.append(line)
        else:
            close()
            expected.append(line)
    close()

    kept = sink.captured_stdout.split("\n")
    assert kept == (expected or [""])
    # Read off the CAPTURE: every redraw fed is a kept line or in a marker's count.
    counted = sum(
        int(m.group("count"))
        for m in (_REDRAW_MARKER.match(ln) for ln in kept)
        if m is not None
    )
    shown = sum(rw._is_progress_redraw(ln) for ln in kept)
    assert shown + counted == sum(r for r, _ in stream)


@settings(max_examples=300, deadline=None)
@given(
    st.one_of(
        st.text(max_size=2000),
        st.builds(
            "Ripping{} track {}, progress - {}%{}".format,
            st.sampled_from(["", " and encoding"]),
            st.text(alphabet="0123456789", max_size=5000),
            st.text(alphabet="0123456789.", max_size=5000),
            st.text(max_size=200),
        ),
        st.builds("Track {} {}".format, st.text(max_size=5000), st.text(max_size=50)),
    )
)
def test_the_redraw_predicate_never_raises(line: str) -> None:
    """It reads every line the ripper prints, live; a raise ends the read loop."""
    assert isinstance(rw._is_progress_redraw(line), bool)
