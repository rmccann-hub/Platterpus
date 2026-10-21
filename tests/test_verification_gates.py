"""The record says which checks ran, from what HAPPENED (the owner's list, item 5).

Two defects, one shape — *a completeness field derived from config describes what
was requested, and will be read as what happened* (`CLAUDE.md`):

* **TASKS.md P2 #4.** ``gates.flac_integrity`` read ``"ran"`` from the settings
  while the checker had aborted on a missing ``flac`` binary. It is now read from
  the result: ``"ran — passed"``, ``"ran — failed"``, or ``"not run — <reason>"``.
* **TASKS.md P2 #5.** The unattended quit gave up on post-rip work and left a
  ``.platterpus.json`` reading ``"No errors occurred"``,
  ``completeness.complete: true`` and ``cover_art: null``. The give-up now writes
  ``completeness.verification`` and a ``verification_cut_short`` issue first.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtWidgets import QApplication, QWidget
from test_ui_main_window import _make_window

from platterpus import rip_report, verification_gates
from platterpus.adapters.flac_verify import FlacVerifyResult, verify_flac_files
from platterpus.config import Config
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.parsers.rip_log import RipLog
from platterpus.verification_gates import (
    CUT_SHORT_GATE,
    GATE_RAN,
    GATE_RAN_FAILED,
    GATE_RAN_PASSED,
    ISSUE_VERIFICATION_CUT_SHORT,
    NOT_RUN_PREFIX,
)


def _gates(**overrides: bool) -> dict[str, Any]:
    """Every check requested, as the settings would build it."""
    inputs: dict[str, bool] = {
        "ctdb_enabled": True,
        "flac_verify_enabled": True,
        "backend_self_verifies": False,
        "transcode_requested": True,
    }
    inputs.update(overrides)
    return rip_report.build_gates(**inputs)


def _report(**kwargs: Any) -> dict[str, Any]:
    return rip_report.build_report(
        RipLog(tracks=()), generated_at="2026-10-21T00:00:00+00:00", **kwargs
    )


def _codes(report: dict[str, Any]) -> set[str]:
    return {issue["code"] for issue in report["issues"]}


# --- (a) gates read from the result ------------------------------------------


def test_a_missing_flac_binary_records_flac_integrity_as_not_run_with_the_reason(
    tmp_path: Path,
) -> None:
    """The measured case, through the REAL runner: the binary is not there.

    No stand-in for the failure itself — `verify_flac_files` execs a path that
    does not exist, exactly as a removed ``flac`` presents on a direct exec, and
    its own abort sentence is what must reach the gate.
    """
    master = tmp_path / "01.flac"
    master.write_bytes(b"not audio; never read")
    result = verify_flac_files([master], binary=str(tmp_path / "absent" / "flac"))
    assert not result.ran and "not found" in result.error  # the precondition

    report = _report(
        flac_verify_result=result,
        gates=_gates(ctdb_enabled=False, transcode_requested=False),
    )

    gate = report["verification"]["gates"]["flac_integrity"]
    assert gate != GATE_RAN, "the settings' claim survived a checker that never ran"
    assert gate.startswith(NOT_RUN_PREFIX), gate
    assert "not found" in gate, f"the reason did not reach the gate: {gate!r}"
    completeness = report["completeness"]["verification"]
    assert completeness["not_run"] == ["flac_integrity"]
    assert completeness["complete"] is False
    assert "verification_step_did_not_run" in _codes(report)


def test_a_flac_check_that_ran_says_whether_it_passed() -> None:
    passed = _report(
        flac_verify_result=FlacVerifyResult(checked=3),
        gates=_gates(ctdb_enabled=False, transcode_requested=False),
    )
    failed = _report(
        flac_verify_result=FlacVerifyResult(checked=3, failures=(Path("01.flac"),)),
        gates=_gates(ctdb_enabled=False, transcode_requested=False),
    )
    assert passed["verification"]["gates"]["flac_integrity"] == GATE_RAN_PASSED
    assert failed["verification"]["gates"]["flac_integrity"] == GATE_RAN_FAILED
    assert passed["completeness"]["verification"]["complete"] is True
    # A check that ran and failed is complete: it produced its verdict.
    assert failed["completeness"]["verification"]["complete"] is True


def test_the_derived_gate_is_read_from_its_result_the_same_way() -> None:
    gates = verification_gates.gates_from_results(
        {"ctdb": "disabled", "flac_integrity": "disabled", "derived": GATE_RAN},
        flac_integrity=None,
        derived={"ran": False, "ok": False, "error": "ffmpeg not found"},
        ctdb=None,
    )
    assert gates is not None
    assert gates["derived"] == f"{NOT_RUN_PREFIX}ffmpeg not found"


def test_a_ctdb_check_that_could_not_run_says_so_and_a_lookup_keeps_ran() -> None:
    for verdict in (Verdict.LOOKUP_ERROR, Verdict.DECODER_UNAVAILABLE):
        report = _report(
            ctdb_result=CtdbVerifyResult(verdict=verdict, message="network down"),
            gates=_gates(flac_verify_enabled=False, transcode_requested=False),
        )
        gate = report["verification"]["gates"]["ctdb"]
        assert gate == f"{NOT_RUN_PREFIX}network down", (verdict, gate)
    # A lookup that compared something keeps "ran": its verdict carries a weight
    # (schema v38), so the pass or fail is read from `ctdb.verdict`.
    matched = _report(
        ctdb_result=CtdbVerifyResult(verdict=Verdict.NO_MATCH),
        gates=_gates(flac_verify_enabled=False, transcode_requested=False),
    )
    assert matched["verification"]["gates"]["ctdb"] == GATE_RAN


def test_the_could_not_run_ctdb_verdicts_match_the_enum() -> None:
    """The builder spells these to stay adapter-free; the enum is the source."""
    assert verification_gates.CTDB_COULD_NOT_RUN_VERDICTS == {
        Verdict.LOOKUP_ERROR.value,
        Verdict.DECODER_UNAVAILABLE.value,
    }


def test_a_gate_with_no_result_keeps_ran_and_counts_against_completeness() -> None:
    report = _report(gates=_gates(ctdb_enabled=False, transcode_requested=False))
    assert report["verification"]["gates"]["flac_integrity"] == GATE_RAN
    assert report["completeness"]["verification"]["without_result"] == [
        "flac_integrity"
    ]
    assert report["completeness"]["verification"]["complete"] is False
    assert rip_report.ISSUE_VERIFICATION_RESULT_MISSING in _codes(report)


def test_a_long_reason_is_bounded_and_the_cut_is_counted() -> None:
    reason = verification_gates.bounded_reason("x" * 250)
    assert reason.endswith("… (50 more characters)"), reason
    assert verification_gates.bounded_reason("") == "no reason recorded"


def test_every_ran_state_counts_as_ran_and_nothing_else_does() -> None:
    for state in (GATE_RAN, GATE_RAN_PASSED, GATE_RAN_FAILED):
        assert verification_gates.gate_claims_ran(state), state
    for state in ("disabled", CUT_SHORT_GATE, f"{NOT_RUN_PREFIX}flac not found", None):
        assert not verification_gates.gate_claims_ran(state), state


# --- (b) the unattended give-up writes "not completed" before quitting ---------


def test_the_cut_short_block_and_issue_reach_the_report() -> None:
    report = _report(
        gates=rip_report.build_gates(
            ctdb_enabled=True,
            flac_verify_enabled=False,
            backend_self_verifies=False,
            transcode_requested=False,
            cut_short=("ctdb",),
        ),
        verification_cut_short=["CTDB verify"],
    )
    assert report["verification"]["gates"]["ctdb"] == CUT_SHORT_GATE
    block = report["completeness"]["verification"]
    assert block["cut_short"] is True
    assert block["cut_short_steps"] == ["CTDB verify"]
    assert block["complete"] is False
    codes = _codes(report)
    assert ISSUE_VERIFICATION_CUT_SHORT in codes
    # One event, one finding: not also "result missing" for the same gate.
    assert rip_report.ISSUE_VERIFICATION_RESULT_MISSING not in codes
    # An absent result is not a passed one, so a grader never reads it as settled.
    assert ISSUE_VERIFICATION_CUT_SHORT in rip_report.VERIFICATION_DROPPED_CODES


@pytest.fixture()
def window(qapp: QApplication):
    made = _make_window(qapp, config=Config(ctdb_verify_after_rip=True))
    yield made
    stop_window_threads(made)
    made.deleteLater()


def test_the_give_up_writes_the_not_completed_record_before_returning(
    window: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end through the window, the record and the real report writer.

    Two steps are alive when the give-up fires: the CTDB verify (which has a gate)
    and the tagging/cover-art thread (which has none) — the measured artifact's
    shape, whose `cover_art` was null. The report must say both did not finish,
    and it must be on disk when the method returns, because `app.quit()` is next.
    """
    log_file = tmp_path / "Album.log"
    log_file.write_text("log", encoding="utf-8")
    record = window._capture_post_rip_record(RipLog(tracks=()), log_file)
    record.gate_inputs = {
        "ctdb_enabled": True,
        "flac_verify_enabled": False,
        "backend_self_verifies": False,
        "transcode_requested": False,
    }
    record.outcome = {"status": "success"}
    record.pending = {"ctdb"}
    record.launched = {"ctdb"}
    monkeypatch.setattr(window, "_build_rip_debug_log", lambda rip_window=None: None)

    release = threading.Event()
    ctdb = threading.Thread(target=release.wait, args=(10,), daemon=True)
    tagging = threading.Thread(target=release.wait, args=(10,), daemon=True)
    ctdb.start()
    tagging.start()
    window._ctdb_thread = ctdb
    window._post_rip_thread = tagging
    try:
        still = window._record_post_rip_cut_short()
        report_path = rip_report.report_path_for(log_file)
        report = json.loads(report_path.read_text(encoding="utf-8"))
    finally:
        release.set()
        ctdb.join(timeout=10)
        tagging.join(timeout=10)

    assert "ctdb" in still and "post_rip" in still
    assert report["verification"]["gates"]["ctdb"] == CUT_SHORT_GATE
    block = report["completeness"]["verification"]
    assert block["cut_short"] is True
    assert block["complete"] is False
    assert "CTDB verify" in block["cut_short_steps"]
    assert "tagging, cover art and format conversion" in block["cut_short_steps"]
    issue = next(
        i for i in report["issues"] if i["code"] == ISSUE_VERIFICATION_CUT_SHORT
    )
    assert issue["severity"] == "warning"
    assert "cover art" in issue["message"]


def test_the_unattended_quit_records_the_give_up_before_it_quits(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ORDER is the fix: record, then quit. Time injected, never slept."""
    from platterpus import app as app_module
    from platterpus.app import _arm_unattended_quit

    clock: list[float] = [1_000.0]
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock[0])
    events: list[str] = []

    class _Runner:
        running = False

    class _Console:
        runner = _Runner()

    class _App:
        def quit(self) -> None:
            events.append("quit")

    stand_in = QWidget()
    stand_in._pending_evidence_bundle = None  # type: ignore[attr-defined]
    stand_in._post_rip_work_settled = lambda: False  # type: ignore[attr-defined]
    stand_in._post_rip_still_running = lambda: "ctdb"  # type: ignore[attr-defined]

    def _record() -> str:
        events.append("record")
        return "ctdb"

    stand_in._record_post_rip_cut_short = _record  # type: ignore[attr-defined]
    timer = _arm_unattended_quit(_App(), stand_in, _Console(), budget_s=60.0)
    try:
        timer.timeout.emit()  # the batch is over: the grace clock starts
        assert events == []
        clock[0] += 61.0
        timer.timeout.emit()  # the budget is spent: give up
    finally:
        timer.stop()
        timer.timeout.disconnect()
        stand_in.deleteLater()
        qapp.processEvents()
    assert events == ["record", "quit"], events
