"""Waiting for the ripper to finish WRITING its log, before anything reads it.

The defect: on 2026-09-09 a cancelled rip's log was read 6.1 seconds before the
ripper finished writing it, and three archival surfaces published the absence as
a finding — ``ripper_log_verification: "failed"``, ``health_status: null``, and an
EAC-compatible log reading *"Conclusive status report : absent — this log carries
no end-of-rip summary"* over a rip whose end-of-rip summary is six lines long. The
log on disk was complete and correctly signed the whole time.

What these tests hold, and why each one is here rather than implied:

* **Free on the normal path.** A log that already carries its footer settles with
  no wait at all — otherwise every successful rip would pay for a cancel's bug.
* **Two outcomes only, and silence is never one of them.** The tempting
  implementation waits for the file to stop growing and calls that "finished".
  It is wrong *here*, measured: the log went quiet at the cancel and stayed quiet
  for 6.6 s because nothing kills the in-container reader until the GUI's
  force-stop rescue reaches it. So a file that never changes and never gains a
  footer must come back NOT settled, forever. That is the assertion that stops
  the heuristic being reintroduced as an optimisation.
* **The deadline is the deadline.** A poll tick may not push the wait past it.
* **It never raises**, including on a file that does not exist or cannot be read —
  those are "no footer yet", which is the correct reading while the writer is
  presumed live, and the deadline bounds it.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.parsers.cyanrip_log import has_log_checksum
from platterpus.ripper_log_settle import (
    NOT_SETTLED,
    SETTLED,
    LogSettle,
    await_ripper_log_settled,
    event_abandoner,
)

#: A real cyanrip footer line, taken from the corpus rather than invented, so
#: these tests cannot pass against a footer shape the parser does not accept.
_REPO = Path(__file__).resolve().parent.parent
_CORPUS = (
    _REPO
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)


def _footer_line() -> str:
    """The `Log FUN512:` line out of a committed real log.

    Read from the artifact rather than hand-typed: `CLAUDE.md`'s *when a committed
    artifact can settle a question, the test should read the artifact*. A typed
    footer would pin my belief about the shape, and the shape is the whole subject.
    """
    for line in _CORPUS.read_text(errors="replace").splitlines():
        if line.startswith("Log FUN512:"):
            return line
    raise AssertionError(f"no Log FUN512: line in the corpus log {_CORPUS}")


def test_the_corpus_carries_a_real_footer_so_these_tests_are_not_vacuous() -> None:
    """Floor. Every "settled" case below depends on this line being recognised."""
    assert _CORPUS.is_file(), f"missing corpus log {_CORPUS}"
    assert has_log_checksum(_footer_line())


class _Clock:
    """A fake monotonic clock advanced only by the waits the code performs.

    Deliberately not richer than `time.monotonic` + `time.sleep`: it answers the
    same two questions and nothing else, so a test cannot rely on a capability
    production does not have.
    """

    def __init__(self) -> None:
        self.t: float = 0.0
        self.waits: list[float] = []

    def now(self) -> float:
        return self.t

    def wait(self, seconds: float) -> bool:
        self.waits.append(seconds)
        self.t += seconds
        return False


def test_a_log_that_already_has_its_footer_settles_with_no_wait(
    tmp_path: Path,
) -> None:
    """The normal path — a rip read to EOF. This must cost nothing."""
    log = tmp_path / "album.log"
    log.write_text(f"Ripping finished at 2026-09-09\n{_footer_line()}\n")
    clock = _Clock()
    settle = await_ripper_log_settled(
        log, deadline_s=20.0, now=clock.now, wait=clock.wait
    )
    assert settle.state == SETTLED
    assert settle.is_settled
    assert settle.waited_s == 0.0
    assert clock.waits == [], "a log with a footer must not be waited for at all"
    assert "already carries" in settle.reason


def test_a_footer_that_arrives_mid_wait_is_settled_and_the_delay_is_reported(
    tmp_path: Path,
) -> None:
    """The 2026-09-09 case, replayed: the footer landed 6.6 s after the cancel."""
    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    clock = _Clock()
    footer = _footer_line()

    def wait(seconds: float) -> bool:
        clock.wait(seconds)
        # Land the footer once the fake clock has passed the measured 6.6 s, i.e.
        # after the force-stop rescue would have reached the in-container reader.
        if clock.t >= 6.6 and not has_log_checksum(log.read_text()):
            log.write_text(f"Rip completed:  no (interrupted by SIGTERM)\n{footer}\n")
        return False

    settle = await_ripper_log_settled(log, deadline_s=20.0, now=clock.now, wait=wait)
    assert settle.state == SETTLED
    assert 6.6 <= settle.waited_s < 7.0
    # The number is IN the sentence: a reason that says "eventually" tells a
    # reader nothing they can compare against the next run.
    assert "6.6s" in settle.reason or "6.8s" in settle.reason, settle.reason


def test_silence_is_NEVER_read_as_the_writer_having_finished(tmp_path: Path) -> None:
    """The anti-heuristic assertion, and the reason this module has no quiet window.

    A file that never changes and never gains a footer is exactly what the
    measured cancel looked like for its first 6.6 seconds. Any implementation that
    concluded "settled" from silence would have graded that rip's log as unsigned —
    which is the bug. So: not settled, for the whole deadline, no matter how long
    the file has been still.
    """
    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    clock = _Clock()
    settle = await_ripper_log_settled(
        log, deadline_s=20.0, now=clock.now, wait=clock.wait
    )
    assert settle.state == NOT_SETTLED
    assert not settle.is_settled
    assert "NOT DETERMINED" in settle.reason
    # And it says WHY the wrapper's exit was not evidence, because that is the
    # fact a reader of the report needs in order to not re-derive it.
    assert "wrapper" in settle.reason


def test_the_wait_never_runs_past_its_deadline(tmp_path: Path) -> None:
    """A poll tick may not push the total past the budget.

    With a 0.25 s tick and a 1.1 s deadline, a naive loop sleeps 5 × 0.25 = 1.25 s.
    The last tick is trimmed instead, so the deadline means what it says — the
    same discipline the shutdown rules put on `QThread.wait`.
    """
    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    clock = _Clock()
    settle = await_ripper_log_settled(
        log, deadline_s=1.1, poll_s=0.25, now=clock.now, wait=clock.wait
    )
    assert settle.state == NOT_SETTLED
    assert sum(clock.waits) <= 1.1 + 1e-9, clock.waits
    assert clock.waits[-1] < 0.25, "the final tick was not trimmed to the deadline"


def test_abandoning_the_wait_returns_at_once_and_says_so(tmp_path: Path) -> None:
    """Window close must not be held up by a footer that is not coming.

    A real interrupt, not a flag the blocked call never reads: `CLAUDE.md` names a
    `cancel()` that only sets a flag as a false promise, and this loop reads the
    predicate every tick.
    """
    import threading

    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    event = threading.Event()
    event.set()
    clock = _Clock()
    settle = await_ripper_log_settled(
        log,
        deadline_s=20.0,
        should_abandon=event_abandoner(event),
        now=clock.now,
        wait=clock.wait,
    )
    assert settle.state == NOT_SETTLED
    assert clock.waits == [], "an abandoned wait must not sleep even once"
    assert "closing" in settle.reason
    assert "NOT DETERMINED" in settle.reason


def test_an_abandon_that_arrives_MID_wait_is_honoured(tmp_path: Path) -> None:
    """Not only the already-set case: the event is read on every tick."""
    import threading

    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    event = threading.Event()
    clock = _Clock()

    def wait(seconds: float) -> bool:
        clock.wait(seconds)
        if clock.t >= 1.0:
            event.set()
        return False

    settle = await_ripper_log_settled(
        log,
        deadline_s=20.0,
        should_abandon=event_abandoner(event),
        now=clock.now,
        wait=wait,
    )
    assert settle.state == NOT_SETTLED
    assert 1.0 <= settle.waited_s < 2.0, settle.waited_s
    assert "closing" in settle.reason


def test_a_zero_or_negative_budget_does_not_pretend_to_have_waited(
    tmp_path: Path,
) -> None:
    """A non-positive deadline is reported, not silently run as a single read.

    A check that can be satisfied by finding nothing is decoration; a wait with no
    budget is the same shape. And a negative value is the `QThread.wait(-1)` trap
    in another costume — say what happened rather than waiting forever.
    """
    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    for deadline in (0.0, -5.0):
        clock = _Clock()
        settle = await_ripper_log_settled(
            log, deadline_s=deadline, now=clock.now, wait=clock.wait
        )
        assert settle.state == NOT_SETTLED, deadline
        assert clock.waits == []
        assert "no time was budgeted" in settle.reason


def test_a_missing_or_unreadable_log_is_no_footer_yet_and_never_raises(
    tmp_path: Path,
) -> None:
    """A file that is not there yet keeps the wait going rather than exploding.

    That is the right reading while the writer is presumed live — the ripper
    creates the log as it starts — and the deadline is what stops it being
    unbounded.
    """
    clock = _Clock()
    settle = await_ripper_log_settled(
        tmp_path / "never-created.log",
        deadline_s=1.0,
        now=clock.now,
        wait=clock.wait,
    )
    assert settle.state == NOT_SETTLED
    assert clock.waits, "a missing log should have been waited for, not refused"


def test_a_zero_budget_on_a_log_that_HAS_a_footer_still_settles(
    tmp_path: Path,
) -> None:
    """The footer check runs BEFORE the budget check, and that ordering matters.

    The worker passes a zero budget on every rip it read to EOF — the normal path.
    If the budget were checked first, every successful rip would come back
    `not_determined` and the fix would have broken the case it was not about.
    """
    log = tmp_path / "album.log"
    log.write_text(f"{_footer_line()}\n")
    settle = await_ripper_log_settled(log, deadline_s=0.0)
    assert settle.state == SETTLED
    assert settle.waited_s == 0.0


def test_the_default_wait_really_sleeps_so_the_seam_is_not_the_only_path(
    tmp_path: Path,
) -> None:
    """Exercise the PRODUCTION clock, not just the injected one.

    Every test above injects `now`/`wait`, which means none of them runs the code
    the app actually runs. One case with the real defaults, kept to a tenth of a
    second, so the default path is not shipped untested — the harness-fidelity
    rule applied to a clock seam.
    """
    log = tmp_path / "album.log"
    log.write_text("Ripping...\n")
    settle = await_ripper_log_settled(log, deadline_s=0.1, poll_s=0.02)
    assert settle.state == NOT_SETTLED
    assert settle.waited_s >= 0.1


def test_the_dataclass_is_frozen_and_is_settled_needs_the_footer() -> None:
    """`is_settled` is the only thing callers should branch on."""
    import dataclasses

    assert dataclasses.is_dataclass(LogSettle)
    assert LogSettle(SETTLED, "x").is_settled
    assert not LogSettle(NOT_SETTLED, "x").is_settled
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        LogSettle(SETTLED, "x").state = NOT_SETTLED  # type: ignore[misc]
