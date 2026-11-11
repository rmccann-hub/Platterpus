"""The automatic CTDB repair after a rip: no button (TASKS R133, KDD-47 amended).

The owner's word of 2026-11-05: *"Should ripping to a good file need a button?
Either we are confident it will happen or not, if not we need to fix that or then
leave for the user but let them know."* What is held here:

* **the trigger**: a rip that differs from CTDB's strongest entry starts a repair,
  and nothing else does (``repair_run.differs_from_strongest``);
* **the switch**: with the Settings switch off nothing is repaired, and the user
  is told so;
* **a refusal changes nothing and is told**: the files are byte-identical, and the
  sentence says why and what to do, with the log's path;
* **cancel kills the child**: a ``flac`` the repair is blocked in is SIGKILLed,
  the run returns at once, and the files are unchanged;
* **the read's verdict is preserved**: the report's ``ctdb`` fields stay what the
  rip's own audio measured, the verify after the repair sits beside them in
  ``after_repair``, and ``expect-ctdb`` grades the read, naming the repair as
  information only;
* **the move waits**: the CTDB check's own daemon holds the library move before
  it emits, and the hold is released when the repair has landed.

No copyrighted audio (CLAUDE.md rule 8): the discs are ``random.Random`` PCM from
``tests/test_ctdb_repair.py``'s synthetic-disc fixture, which stores raw PCM under
a ``.flac`` name and decodes by reading it back. **What that stand-in does that
the real thing does not**: no FLAC codec runs here; ``tests/test_flac_rewrite.py``
runs the real ``flac``/``metaflac`` where they are installed. The cancel test runs
a real child process (a shell script standing in for ``flac``), because the claim
is that a real process group is killed.
"""

from __future__ import annotations

import dataclasses
import os
import stat
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import stop_window_threads
from test_ctdb_repair import _Disc, _errors, _FakeRewriter

from platterpus.adapters.accuraterip_db import AccurateRipHttpImpl
from platterpus.adapters.flac_rewrite import CANCELLED as TOOL_CANCELLED
from platterpus.adapters.flac_rewrite import FlacRewriter, run_bytes
from platterpus.config import Config
from platterpus.ctdb import decode
from platterpus.ctdb.repair import PcmDecoder
from platterpus.ctdb.repair_run import (
    accuraterip_answers,
    differs_from_strongest,
    repair_verified_rip,
)
from platterpus.ctdb.repair_types import RepairStatus
from platterpus.ctdb.repair_wording import (
    CANCELLED,
    CLOSED_UNFINISHED,
    NEWER_RIP,
    OFF_IN_SETTINGS,
    repair_text,
)
from platterpus.ctdb.toc import SamplesProbe
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict, verify_rip
from platterpus.killable import KillableJob, was_cancelled
from platterpus.parsers.rip_log import AccurateRipResult
from platterpus.rip_report import _ctdb
from platterpus.ui import main_window_ctdb_repair as repair_mixin
from platterpus.ui.failure_text import LOG_POINTER
from platterpus.ui.main_window_ctdb_repair import CtdbRepairContext
from platterpus.uiscript import record_grading
from platterpus.workers.ctdb_repair_worker import CtdbRepairOutcome, CtdbRepairWorker


def _read(path: Path) -> bytes:
    return Path(path).read_bytes()


def _frames(path: Path) -> int:
    return Path(path).stat().st_size // 4


def _track(
    number: int, *, verified: bool = False, differs: bool = False, named: bool = True
) -> object:
    """A parsed track as ``accuraterip_answers`` reads it (cyanrip's shape).

    Neither ``verified`` nor ``differs``: AccurateRip was never asked, so it said
    nothing (no lookup line), which is the third answer, not a "no".
    """
    v1 = None
    if verified:
        v1 = AccurateRipResult(version=1, result="accurately ripped", confidence=3)
    elif differs:
        v1 = AccurateRipResult(
            version=1, result="not found, either a new pressing, or bad rip"
        )
    asked = verified or differs
    return SimpleNamespace(
        number=number,
        status="",
        filename=f"{number:02d}.flac" if named else "",
        copy_crc="ABCDEF01",
        accuraterip_v1=v1,
        accuraterip_v2=None,
        accuraterip_offset=None,
        accuraterip_lookup="found in database (max confidence: 3)" if asked else None,
    )


def _log(*tracks: object) -> object:
    return SimpleNamespace(tracks=list(tracks))


def _plain_log() -> object:
    return _log(_track(1), _track(2), _track(3))


def _test_repair(
    paths: Sequence[Path],
    result: CtdbVerifyResult,
    accuraterip: Mapping[int, bool | None],
    _probe: SamplesProbe,
    _decoder: PcmDecoder,
    _rewriter: FlacRewriter,
) -> CtdbVerifyResult:
    """The real thin caller, with the synthetic disc's decoder and encoder."""
    return repair_verified_rip(
        paths,
        result,
        accuraterip_verified=accuraterip,
        samples_probe=_frames,
        decoder=_read,
        rewriter=_FakeRewriter(),
    )


def _reverify_with(disc: _Disc) -> Any:
    def reverify(
        _rip_dir: Path, _decoder: PcmDecoder, _probe: SamplesProbe
    ) -> CtdbVerifyResult:
        return verify_rip(disc.paths, disc.client, decoder=_read, samples_probe=_frames)

    return reverify


# --- the trigger, pure ---------------------------------------------------------------


def test_an_outvoted_match_differs_from_the_strongest_entry(tmp_path: Path) -> None:
    """The reference disc's shape: our audio equals a confidence-1 entry only."""
    disc = _Disc(tmp_path, 3, _errors())
    assert disc.result.verdict is Verdict.MATCH and disc.result.outvoted
    assert differs_from_strongest(disc.result)


def test_a_rip_that_matches_the_strongest_entry_is_left_alone(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 4, {})
    assert disc.result.verdict is Verdict.MATCH and not disc.result.outvoted
    assert not differs_from_strongest(disc.result)


@pytest.mark.parametrize(
    "verdict", [Verdict.NOT_IN_DATABASE, Verdict.LOOKUP_ERROR, Verdict.NOT_WHOLE_DISC]
)
def test_a_check_that_compared_nothing_starts_no_repair(
    tmp_path: Path, verdict: Verdict
) -> None:
    disc = _Disc(tmp_path, 5, _errors())
    assert not differs_from_strongest(dataclasses.replace(disc.result, verdict=verdict))


def test_no_measured_crcs_start_no_repair(tmp_path: Path) -> None:
    disc = _Disc(tmp_path, 6, _errors())
    assert not differs_from_strongest(dataclasses.replace(disc.result, disc_crcs={}))
    assert not differs_from_strongest(object())


def test_accuraterip_answers_are_per_file_and_refuse_a_mismatch() -> None:
    answers = accuraterip_answers(
        _log(_track(1, verified=True), _track(2, differs=True), _track(3)), 3
    )
    assert answers == {1: True, 2: False, 3: None}
    # A data track is not a file: left out of the numbering.
    data = SimpleNamespace(number=4, status="Data track, skipped")
    assert accuraterip_answers(_log(_track(1), _track(2), _track(3), data), 3) == {
        1: None,
        2: None,
        3: None,
    }
    # Cannot be lined up: the whole answer is unknown, never a partial guess.
    assert accuraterip_answers(_log(_track(1)), 3) is None
    assert accuraterip_answers(None, 3) is None


# --- killable: binary runs, and a job's cancel ---------------------------------------


def test_run_bytes_passes_binary_both_ways() -> None:
    data = bytes(range(256)) * 64
    done = KillableJob("test cat").run_bytes(["cat"], stdin=data, timeout=30)
    assert done.returncode == 0 and done.stdout == data


def test_a_cancelled_job_starts_nothing_more(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cancel between two runs would otherwise find nothing to kill."""
    job = KillableJob("test job")
    job.cancel()

    def _no_spawn(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("a cancelled job spawned a child")

    monkeypatch.setattr("platterpus.killable.subprocess.Popen", _no_spawn)
    assert was_cancelled(job.run_bytes(["cat"], stdin=b"x", timeout=5))
    assert was_cancelled(job.run(["true"], timeout=5))


def test_a_cancelled_tool_run_is_not_recorded_as_the_tool_failing() -> None:
    job = KillableJob("test rewrite")
    job.cancel()
    got = run_bytes(
        ["cat"], b"x", timeout_s=5, tool="flac", code="ctdb_repair.flac", command=job
    )
    assert not got.run.ok and got.run.error == TOOL_CANCELLED


# --- the worker ----------------------------------------------------------------------


def _worker(
    disc: _Disc, rip_log: object, **kwargs: Any
) -> tuple[CtdbRepairWorker, list[CtdbRepairOutcome]]:
    worker = CtdbRepairWorker(
        disc.result,
        disc.paths[0].parent,
        client=disc.client,
        rip_log=rip_log,
        **kwargs,
    )
    seen: list[CtdbRepairOutcome] = []
    worker.done.connect(seen.append)
    return worker, seen


def test_the_worker_repairs_and_keeps_the_reads_verdict(
    tmp_path: Path, qapp: object
) -> None:
    disc = _Disc(tmp_path, 7, _errors())
    worker, seen = _worker(
        disc, _plain_log(), repair=_test_repair, reverify=_reverify_with(disc)
    )
    worker.run()
    assert seen and worker.outcome is seen[0]
    result = seen[0].result
    assert result.repair is not None
    assert result.repair.status is RepairStatus.REPAIRED, result.repair.reason
    # The read's verdict, as measured: an outvoted match, not the repaired files'.
    assert result.verdict is Verdict.MATCH and result.outvoted
    assert result.our_crc == disc.result.our_crc
    # The repaired files' verdict, beside it.
    after = result.after_repair
    assert after is not None and after.verdict is Verdict.MATCH and not after.outvoted
    for number in (1, 2, 3):
        assert disc.paths[number - 1].read_bytes() == disc.clean_track(number)


def test_a_refused_repair_changes_nothing_and_is_told(
    tmp_path: Path, qapp: object
) -> None:
    """AccurateRip verified track 1, which the repair would rewrite: refused."""
    disc = _Disc(tmp_path, 8, _errors())
    before = disc.snapshot()
    log = _log(_track(1, verified=True), _track(2), _track(3))
    worker, seen = _worker(
        disc, log, repair=_test_repair, reverify=_reverify_with(disc)
    )
    worker.run()
    result = seen[0].result
    assert result.repair is not None and result.repair.status is RepairStatus.REFUSED
    assert "AccurateRip verified track 1" in result.repair.reason
    assert result.after_repair is None
    assert disc.snapshot() == before, "a refused repair changed the album folder"
    told = repair_text(result, log_pointer=LOG_POINTER)
    assert told is not None
    level, text = told
    assert level == "warn" and text.startswith("⚠")
    assert "AccurateRip verified track 1" in text and "What you can do" in text
    assert text.endswith(LOG_POINTER)


def test_a_log_that_cannot_be_lined_up_refuses_before_any_work(
    tmp_path: Path, qapp: object
) -> None:
    disc = _Disc(tmp_path, 9, _errors())
    calls: list[object] = []

    def _never(*args: object) -> CtdbVerifyResult:
        calls.append(args)
        raise AssertionError("the repair ran without AccurateRip's answer")

    # One track in the log, three files on disk (the log names none, so the
    # files come from the folder): AccurateRip's answers cannot be lined up.
    worker, seen = _worker(disc, _log(_track(1, named=False)), repair=_never)
    worker.run()
    assert not calls
    record = seen[0].result.repair
    assert record is not None and record.status is RepairStatus.REFUSED
    assert "AccurateRip" in record.reason


def _sleeping_flac(tmp_path: Path) -> tuple[Path, Path]:
    """A stand-in `flac` that records its pid and sleeps: a decode that never ends."""
    pidfile = tmp_path / "flac.pid"
    script = tmp_path / "fakeflac"
    script.write_text(f'#!/bin/sh\necho $$ > "{pidfile}"\nexec sleep 30\n')
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script, pidfile


def test_cancel_kills_the_child_the_repair_is_blocked_in(
    tmp_path: Path, qapp: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE.md rule 9: a cancel() that does not reach the child is a false promise.

    The real core, the worker's own killable decoder, and a real child process
    that would sleep 30 s. The cancel must end the run in seconds, the child must
    be gone, and the files must be as they were.
    """
    rip = tmp_path / "rip"
    rip.mkdir()
    disc = _Disc(rip, 10, _errors())
    before = disc.snapshot()
    script, pidfile = _sleeping_flac(tmp_path)
    monkeypatch.setattr(decode, "_which", lambda _name: str(script))

    def _real_core_killable_decoder(
        paths: Sequence[Path],
        result: CtdbVerifyResult,
        accuraterip: Mapping[int, bool | None],
        _probe: SamplesProbe,
        decoder: PcmDecoder,
        _rewriter: FlacRewriter,
    ) -> CtdbVerifyResult:
        return repair_verified_rip(
            paths,
            result,
            accuraterip_verified=accuraterip,
            samples_probe=_frames,
            decoder=decoder,  # the worker's: through its KillableJob
            rewriter=_FakeRewriter(),
        )

    worker, seen = _worker(disc, _plain_log(), repair=_real_core_killable_decoder)
    runner = threading.Thread(target=worker.run, daemon=True)
    runner.start()
    deadline = time.monotonic() + 15
    while not pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert pidfile.exists(), "the stand-in flac never started"
    pid = int(pidfile.read_text().strip())
    started = time.monotonic()
    worker.cancel()
    runner.join(10)
    assert not runner.is_alive(), "the cancel did not end the repair"
    assert time.monotonic() - started < 10
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # killed and reaped: no such process
    # Read off the worker: `done` was emitted on this plain thread, and its queued
    # delivery needs the GUI loop; the worker keeps the outcome for exactly the
    # case where the signal cannot be delivered (a closing window).
    outcome = worker.outcome
    assert outcome is not None and outcome.cancelled
    assert outcome.result.repair is not None
    assert outcome.result.repair.status is RepairStatus.FAILED
    assert outcome.result.repair.reason == CANCELLED
    assert disc.snapshot() == before


def test_a_cancel_before_the_start_does_not_repair(
    tmp_path: Path, qapp: object
) -> None:
    disc = _Disc(tmp_path, 11, _errors())
    before = disc.snapshot()
    release = threading.Event()
    reader = threading.Thread(target=release.wait, args=(30,), daemon=True)
    reader.start()  # an "other check" still reading the album
    worker, _seen = _worker(disc, _plain_log(), wait_for=[reader], repair=_test_repair)
    runner = threading.Thread(target=worker.run, daemon=True)
    try:
        runner.start()
        time.sleep(0.3)
        worker.cancel()
        runner.join(10)
        assert not runner.is_alive()
    finally:
        release.set()
        reader.join(5)
    outcome = worker.outcome
    assert outcome is not None and outcome.cancelled
    assert outcome.result.repair is not None
    assert outcome.result.repair.reason == CANCELLED
    assert disc.snapshot() == before


# --- the wording ---------------------------------------------------------------------


def test_a_repair_says_what_and_how_it_was_proved(tmp_path: Path, qapp: object) -> None:
    disc = _Disc(tmp_path, 12, _errors())
    worker, seen = _worker(
        disc, _plain_log(), repair=_test_repair, reverify=_reverify_with(disc)
    )
    worker.run()
    told = repair_text(seen[0].result, log_pointer=LOG_POINTER)
    assert told is not None
    level, text = told
    assert level == "ok" and text.startswith("✓ Repaired from CTDB: track 1 (")
    assert "1,416 submissions" in text and "entry 32115" in text
    assert "Proved before anything was replaced" in text
    # Per version, and never "verified" (G3, 2026-11-11): the database's entry
    # for a track the repair rewrote is not known, so each version says so.
    assert "Track 1: AccurateRip v1 " in text and "; v2 " in text
    assert (
        text.count(": not determined") >= 2
        and "verified" not in text.split("Track 1: AccurateRip", 1)[1].split(".", 1)[0]
    )
    assert ".before-ctdb-repair" in text and "logs still record the read" in text


def test_the_switch_off_is_said_plainly(tmp_path: Path) -> None:
    from platterpus.ctdb.repair_types import refused

    disc = _Disc(tmp_path, 13, _errors())
    told = repair_text(
        dataclasses.replace(disc.result, repair=refused(OFF_IN_SETTINGS)),
        log_pointer=LOG_POINTER,
    )
    assert told is not None and told[0] == "neutral"
    assert told[1].startswith("ⓘ") and OFF_IN_SETTINGS in told[1]


# --- the read is graded, the repair is information ---------------------------------


def test_expect_ctdb_grades_the_read_not_the_repair(
    tmp_path: Path, qapp: object
) -> None:
    """An archival grade the read failed cannot be satisfied by a repair."""
    disc = _Disc(tmp_path, 14, _errors())
    worker, seen = _worker(
        disc, _plain_log(), repair=_test_repair, reverify=_reverify_with(disc)
    )
    worker.run()
    block = _ctdb(seen[0].result)
    assert block is not None
    assert block["verdict"] == "match" and block["outvoted"] is True  # the read
    assert block["repair"]["status"] == "repaired"
    after = block["after_repair"]
    assert after is not None and after["verdict"] == "match"
    assert after["outvoted"] is False
    grade = record_grading.grade_ctdb({"ctdb": block}, "whole")
    assert not grade.passed and not grade.blocked
    assert "outvotes" in grade.detail
    assert "CTDB repair repaired the files; CTDB after it: match." in grade.detail
    assert "repair was repaired" not in grade.detail  # the 2026-11-10 wording
    assert "This step grades the read, not the repair." in grade.detail
    # And a passing read keeps passing, with no note when there was no repair.
    (tmp_path / "clean").mkdir()
    clean = _ctdb(_Disc(tmp_path / "clean", 15, {}).result)
    assert clean is not None and clean["after_repair"] is None
    plain = record_grading.grade_ctdb({"ctdb": clean}, "whole")
    assert plain.passed and "repair" not in plain.detail


# --- the window ----------------------------------------------------------------------


@pytest.fixture()
def repair_window(qapp: object):  # type: ignore[no-untyped-def]
    from test_ui_main_window import _make_window

    built: list[Any] = []

    def factory(config: Config | None = None) -> Any:
        window = _make_window(qapp, config=config or Config())  # type: ignore[arg-type]
        built.append(window)
        return window

    yield factory
    for window in built:
        stop_window_threads(window)
        window.deleteLater()


def _context(disc: _Disc, *, flac_verify: bool = True) -> CtdbRepairContext:
    return CtdbRepairContext(
        rip_dir=disc.paths[0].parent,
        rip_log=_plain_log(),
        disc_tracks_hint=3,
        transcode_fmt="",
        mp3_vbr_quality=0,
        flac_verify=flac_verify,
    )


def _pump_until(qapp: Any, done: Any, seconds: float = 20.0) -> None:
    deadline = time.monotonic() + seconds
    while not done() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert done(), "the repair did not land"


def test_with_the_switch_off_nothing_is_repaired_and_the_user_is_told(
    tmp_path: Path, repair_window: Any
) -> None:
    window = repair_window(Config(ctdb_repair_after_rip=False))
    window._open_post_rip_record()
    disc = _Disc(tmp_path, 16, _errors())
    before = disc.snapshot()
    generation = window._rip_generation
    window._note_ctdb_repair_context(_context(disc))
    window._arm_ctdb_repair(generation, disc.result)
    assert not window._ctdb_repair_busy, "the switch is off; nothing may hold the move"
    window._on_ctdb_verified(generation, disc.result)
    assert window._ctdb_repair_thread is None
    record = window._post_rip_record(generation)
    assert record.ctdb.repair.reason == OFF_IN_SETTINGS
    assert window._rip_progress._ctdb_repair_label.text().startswith("ⓘ")
    assert disc.snapshot() == before


def test_the_window_repairs_records_the_read_and_reruns_the_checks(
    tmp_path: Path, repair_window: Any, qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    disc = _Disc(tmp_path, 17, _errors())
    given: list[object] = []

    class _Worker(CtdbRepairWorker):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            given.append(kwargs.get("accuraterip"))
            super().__init__(
                *args, repair=_test_repair, reverify=_reverify_with(disc), **kwargs
            )

    monkeypatch.setattr(repair_mixin, "CtdbRepairWorker", _Worker)
    window = repair_window()
    window._open_post_rip_record()
    generation = window._rip_generation
    reruns: list[str] = []
    monkeypatch.setattr(
        window, "_start_checksums", lambda *a, **k: reruns.append("checksums")
    )
    monkeypatch.setattr(
        window, "_start_flac_verify", lambda *a, **k: reruns.append("flac_verify")
    )
    window._note_ctdb_repair_context(_context(disc))
    # The CTDB daemon holds the move before it emits.
    window._arm_ctdb_repair(generation, disc.result)
    assert window._ctdb_repair_busy and not window._post_rip_work_settled()
    window._on_ctdb_verified(generation, disc.result)
    record = window._post_rip_record(generation)
    assert record.ctdb is None and "ctdb" in record.pending, (
        "the CTDB gate must stay pending while the files may still change"
    )
    assert "ctdb_repair" in window._post_rip_steps_running()
    _pump_until(qapp, lambda: not window._ctdb_repair_busy)
    result = record.ctdb
    assert result.verdict is Verdict.MATCH and result.outvoted, "the read, kept"
    assert result.repair.status is RepairStatus.REPAIRED
    assert result.after_repair.verdict is Verdict.MATCH
    assert "ctdb" not in record.pending
    assert reruns == ["checksums", "flac_verify"]
    assert window._rip_progress._ctdb_repair_label.text().startswith("✓")
    assert disc.paths[0].read_bytes() == disc.clean_track(1)
    assert Path(f"{disc.paths[0]}.before-ctdb-repair").exists()
    # G2 (TASKS R138): the window hands the worker the real AccurateRip client
    # (the suite's guard keeps it off the network); without one, nothing is asked.
    assert len(given) == 1 and isinstance(given[0], AccurateRipHttpImpl)
    assert result.repair.accuraterip_lookup is not None


def test_a_landed_repair_names_itself_in_the_eac_layout_log_before_the_report(
    tmp_path: Path, repair_window: Any, qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G3 (2026-11-11): the EAC-layout log is rendered again when the repair lands.

    The log was written at the rip's end and when CTDB answered, both before the
    repair, so the repaired track's block described only the read. Once the repair
    lands, the track's ``Record:`` row says it was repaired, the read's own rows
    stay, and this happens BEFORE the report write, which embeds the log's text.
    """
    from platterpus.parsers.rip_log import RipLog, TrackResult
    from platterpus.ui.post_rip_record import EacLogRender

    disc = _Disc(tmp_path, 19, _errors())

    class _Worker(CtdbRepairWorker):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(
                *args, repair=_test_repair, reverify=_reverify_with(disc), **kwargs
            )

    monkeypatch.setattr(repair_mixin, "CtdbRepairWorker", _Worker)
    window = repair_window()
    record = window._open_post_rip_record()
    generation = window._rip_generation
    monkeypatch.setattr(window, "_start_checksums", lambda *a, **k: None)
    monkeypatch.setattr(window, "_start_flac_verify", lambda *a, **k: None)
    read = RipLog(
        log_creator="cyanrip 0.9.4-rc3+platterpus.30",
        tracks=tuple(
            TrackResult(number=n, copy_crc="ABCDEF01", status="ripped successfully")
            for n in (1, 2, 3)
        ),
    )
    render = EacLogRender(read, "0.7.121", "", {}, "success", 3, None, None)
    folder = disc.paths[0].parent
    record.log_file = folder / "rip.log"
    eac_log = folder / "rip (EAC-compatible).log"
    eac_log.write_text(render.render()[0], encoding="utf-8")
    record.eac_log = render
    seen_at_report: list[str] = []
    original = window._record_post_rip_result

    def _recording(gen: int, attribute: str, value: object) -> None:
        if attribute == "ctdb" and getattr(value, "repair", None) is not None:
            seen_at_report.append(eac_log.read_text(encoding="utf-8"))
        original(gen, attribute, value)

    monkeypatch.setattr(window, "_record_post_rip_result", _recording)
    window._note_ctdb_repair_context(_context(disc))
    window._arm_ctdb_repair(generation, disc.result)
    window._on_ctdb_verified(generation, disc.result)
    _pump_until(qapp, lambda: not window._ctdb_repair_busy)
    assert record.ctdb.repair.status is RepairStatus.REPAIRED
    text = eac_log.read_text(encoding="utf-8")
    assert "Record: repaired from CTDB entry 32115" in text
    assert "Copy CRC ABCDEF01" in text, "the read's own rows stay"
    assert (
        "accurately ripped"
        not in text.split("Track  1", 1)[1].split("Track  2")[0].lower()
    )
    assert seen_at_report and "Record: repaired from CTDB" in seen_at_report[0], (
        "the report must embed the log that names the repair"
    )


def test_a_window_closing_mid_repair_records_the_read(
    tmp_path: Path, repair_window: Any
) -> None:
    """The read's verdict reaches the report, with a record saying the app closed."""
    window = repair_window()
    window._open_post_rip_record()
    disc = _Disc(tmp_path, 18, _errors())
    generation = window._rip_generation
    record = window._post_rip_record(generation)
    record.pending.add("ctdb")
    window._ctdb_repair_busy = True
    window._ctdb_repair_generation = generation
    window._ctdb_repair_pending = disc.result
    window._land_ctdb_repair_on_close()
    assert not window._ctdb_repair_busy
    assert record.ctdb.verdict is Verdict.MATCH
    assert record.ctdb.repair.status is RepairStatus.FAILED
    assert record.ctdb.repair.reason == CLOSED_UNFINISHED
    assert "ctdb" not in record.pending


def test_the_after_repair_block_is_declared_as_written() -> None:
    """``ctdb.after_repair`` is a selection of ``ctdb``'s own fields; its type says which."""
    from platterpus.report_types import CtdbAfterRepairBlock
    from platterpus.rip_report import AFTER_REPAIR_KEYS

    assert set(AFTER_REPAIR_KEYS) == set(CtdbAfterRepairBlock.__annotations__)
    assert len(AFTER_REPAIR_KEYS) == len(set(AFTER_REPAIR_KEYS)) >= 10


def test_a_newer_rip_declines_the_repair_and_says_so_in_the_record(
    tmp_path: Path, repair_window: Any
) -> None:
    """A repair only starts for the album on screen: the launchers it re-runs
    afterwards register against the current rip, so another album's would land
    on the wrong record."""
    window = repair_window()
    window._open_post_rip_record()
    disc = _Disc(tmp_path, 19, _errors())
    generation = window._rip_generation
    window._note_ctdb_repair_context(_context(disc))
    window._rip_generation += 1
    window._open_post_rip_record()
    window._arm_ctdb_repair(generation, disc.result)
    window._on_ctdb_verified(generation, disc.result)
    assert window._ctdb_repair_thread is None
    assert not window._ctdb_repair_busy
    record = window._post_rip_record(generation)
    assert record.ctdb.repair.status is RepairStatus.REFUSED
    assert record.ctdb.repair.reason == NEWER_RIP
    # Not shown: the window describes the newer rip now.
    assert not window._rip_progress._ctdb_repair_label.text()


def test_the_derived_copies_are_made_again_from_the_repaired_flac(
    tmp_path: Path, repair_window: Any, qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a repair: stale results cleared, the transcode re-run on the masters,
    and the derived verify and checksums wait for it."""
    from platterpus.adapters.transcode import TranscodeResult

    window = repair_window()
    window._open_post_rip_record()
    disc = _Disc(tmp_path, 20, _errors())
    generation = window._rip_generation
    context = dataclasses.replace(_context(disc), transcode_fmt="mp3")
    window._note_ctdb_repair_context(context)
    record = window._post_rip_record(generation)
    record.transcode = record.derived_verify = object()
    record.checksums, record.audio_md5, record.flac_verify = {}, {}, object()
    transcoded: list[tuple[list[Path], str]] = []

    def _fake_transcode(
        paths: Sequence[Path], *, fmt: str, mp3_vbr_quality: int
    ) -> TranscodeResult:
        transcoded.append((list(paths), fmt))
        return TranscodeResult(transcoded=len(paths))

    monkeypatch.setattr(repair_mixin, "transcode_files", _fake_transcode)
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        window,
        "_start_derived_verify",
        lambda rip_dir, fmt, wait_for: calls.append(("derived", wait_for)),
    )
    monkeypatch.setattr(
        window,
        "_start_checksums",
        lambda rip_dir, wait_for: calls.append(("checksums", wait_for)),
    )
    monkeypatch.setattr(
        window,
        "_start_flac_verify",
        lambda rip_dir, wait_for: calls.append(("flac_verify", wait_for)),
    )
    window._rerun_after_ctdb_repair(generation)
    assert record.transcode is None and record.derived_verify is None
    assert record.checksums is None and record.audio_md5 is None
    assert record.flac_verify is None
    rederive = window._post_rip_thread
    assert isinstance(rederive, threading.Thread)
    assert calls == [
        ("derived", rederive),
        ("checksums", rederive),
        ("flac_verify", None),
    ]
    rederive.join(10)
    assert transcoded == [(disc.paths, "mp3")]
    _pump_until(qapp, lambda: record.transcode is not None)
    assert record.transcode.transcoded == 3
