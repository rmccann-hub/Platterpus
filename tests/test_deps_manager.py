"""Tests for platterpus.deps.manager.

The manager is constructed with a custom spec list so each test isolates the
check_all probe/classify path. (Resolution routing lives in the GUI —
``main_window_deps._resolve_missing_unified`` — not the manager; the old
``resolve_missing`` cascade was removed as the unused second implementation.)
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from platterpus.deps.checks import ProbeResult, check_cyanrip
from platterpus.deps.manager import DependencyManager, DependencyReport
from platterpus.deps.registry import DependencySpec, Tier

# --- Spec/probe factories -------------------------------------------------


def _spec(
    dep_id: str,
    probe: Callable[[], ProbeResult],
    tier: Tier = Tier.AUTO,
    min_version: tuple[int, ...] = (0, 0, 0),
    install_command: list[str] | None = None,
) -> DependencySpec:
    return DependencySpec(
        dep_id=dep_id,
        display_name=dep_id,
        probe=probe,
        min_version=min_version,
        tier=tier,
        install_command=install_command,
        search_string=f"install {dep_id}",
    )


def _present(version: tuple[int, ...] = (1, 0, 0)) -> Callable[[], ProbeResult]:
    return lambda: ProbeResult(present=True, version=version, location="/x")


def _absent() -> Callable[[], ProbeResult]:
    return lambda: ProbeResult(present=False, version=None, location=None)


# --- check_all ------------------------------------------------------------


def test_check_all_classifies_present_and_missing() -> None:
    specs = [
        _spec("present", _present()),
        _spec("missing", _absent()),
    ]
    mgr = DependencyManager(specs=specs)

    report = mgr.check_all()

    assert [s.dep_id for s in report.ok] == ["present"]
    assert [m.spec.dep_id for m in report.missing] == ["missing"]


def test_check_all_records_ok_versions() -> None:
    specs = [
        _spec("present", _present(version=(0, 10, 0))),
        _spec("missing", _absent()),
    ]
    mgr = DependencyManager(specs=specs)

    report = mgr.check_all()

    # The OK dep's detected version is stamped; the missing one is absent.
    assert report.ok_versions == {"present": (0, 10, 0)}


def test_check_all_treats_too_old_as_missing() -> None:
    specs = [
        _spec(
            "old",
            probe=lambda: ProbeResult(present=True, version=(0, 9, 0), location="/x"),
            min_version=(1, 0, 0),
        ),
    ]
    mgr = DependencyManager(specs=specs)

    report = mgr.check_all()

    assert report.ok == []
    assert len(report.missing) == 1
    assert report.missing[0].spec.dep_id == "old"


def test_check_all_is_idempotent() -> None:
    specs = [_spec("x", _present()), _spec("y", _absent())]
    mgr = DependencyManager(specs=specs)

    r1 = mgr.check_all()
    r2 = mgr.check_all()

    assert [s.dep_id for s in r1.ok] == [s.dep_id for s in r2.ok]
    assert [m.spec.dep_id for m in r1.missing] == [m.spec.dep_id for m in r2.missing]


def test_all_resolved_true_when_everything_probes_ok() -> None:
    specs = [_spec("a", _present()), _spec("b", _present())]
    mgr = DependencyManager(specs=specs)

    report = mgr.check_all()

    assert report.all_resolved is True


def test_all_resolved_false_when_missing_and_no_resolve_attempt() -> None:
    specs = [_spec("a", _absent())]
    mgr = DependencyManager(specs=specs)

    report = mgr.check_all()

    assert report.all_resolved is False


# --- Manager constructs cleanly with no args (production path) ------------


def test_manager_constructs_with_default_registry() -> None:
    """The no-args constructor must work — it's what app.py uses."""
    mgr = DependencyManager()
    # Real probes shell out and may take a moment, but they shouldn't
    # crash. We don't assert on the result; we just confirm the call
    # path doesn't blow up.
    report = mgr.check_all()
    assert isinstance(report, DependencyReport)


# --- An overall deadline, and a report honest about what it did not reach ----
#
# The maintainer's report (2026-09-28): Setup & Updates -> Check dependencies
# "seems to freeze, not respond, or give no error". The probe runs off the GUI
# thread, so the window never froze -- but seven probes at up to 60 s each (120 s
# for cyanrip, which tries two version flags) meant a wedged container gave NO
# answer for minutes. And a check that stopped early returned a PARTIAL report
# with no marker, which every surface then read as the whole picture: "a
# completeness field derived from config describes what was requested".


def _sleeping_tool(tmp_path: Path, name: str = "cyanrip") -> Path:
    """A real executable that never answers -- the wedged-container stand-in.

    Real, not a patched `VERSION_PROBE.run`: the thing under test is that the
    child is KILLED at the deadline, and only a real child can show that.
    """
    tool = tmp_path / name
    tool.write_text("#!/bin/sh\nexec sleep 20\n", encoding="utf-8")
    tool.chmod(0o755)
    return tool


def test_the_deadline_kills_the_in_flight_probe_and_marks_the_rest_unchecked(
    tmp_path: Path,
) -> None:
    """A wedged probe is killed at the deadline, and nothing after it is probed.

    cyanrip's probe tries two version flags. Killing the first child is not
    enough on its own: the probe would go on to start the second and block for
    another 60 s. So this asserts the WHOLE check ends near the deadline.
    """
    tool = _sleeping_tool(tmp_path)
    reached: list[str] = []

    def after() -> ProbeResult:
        reached.append("after")
        return ProbeResult(present=True, version=(1, 0, 0), location="/x")

    mgr = DependencyManager(
        specs=[
            _spec("first", _present()),
            _spec("cyanrip", lambda: check_cyanrip(tool)),
            _spec("after", after),
        ]
    )
    started = time.monotonic()
    report = mgr.check_all(deadline_s=0.5)
    elapsed = time.monotonic() - started

    assert elapsed < 8.0, (
        f"the check took {elapsed:.1f} s with a 0.5 s deadline: the in-flight "
        "probe was not killed, or the second version flag was started after it"
    )
    assert [s.dep_id for s in report.ok] == ["first"]
    # The killed probe is NOT missing: absence we caused is not an answer.
    assert report.missing == [], (
        "a probe WE killed was reported as a missing tool -- that routes the user "
        "to the setup wizard for a tool that may be installed"
    )
    assert [s.dep_id for s in report.unchecked] == ["cyanrip", "after"]
    assert reached == [], "a spec after the deadline was still probed"
    assert "stopped after 0.5 s" in report.unchecked_reason
    assert not report.complete
    assert report.all_resolved is False, "an incomplete check cannot be all resolved"
    assert report.measured_at, "an incomplete check still says when it measured"


def test_no_probe_is_started_once_the_deadline_has_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The half that stops the second version flag: refuse, do not spawn."""
    from platterpus.deps import checks

    spawned: list[list[str]] = []
    monkeypatch.setattr(
        checks.VERSION_PROBE, "run", lambda argv, **_kw: spawned.append(argv)
    )
    with checks.probe_deadline(time.monotonic() - 1.0):
        ran, output, _where = checks._run_version_command(["metaflac", "--version"])
    assert (ran, output) == (False, "")
    assert spawned == [], "a probe was spawned after the check's deadline"


def test_a_probe_timeout_never_outlives_the_checks_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The kill is the probe's own timeout, capped to what the check has left.

    Capping the timeout kills OUR child at the deadline (KillableCommand SIGKILLs
    the group on timeout). The alternative, calling `cancel_version_probes()` from
    a timer, kills whatever child holds the shared slot -- which can belong to a
    concurrent caller such as the cyanrip-update check.
    """
    from platterpus.deps import checks

    timeouts: list[float] = []

    def fake_run(argv: list[str], *, timeout: float, **_kw: object) -> object:
        timeouts.append(timeout)
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    monkeypatch.setattr(checks.VERSION_PROBE, "run", fake_run)
    with checks.probe_deadline(time.monotonic() + 5.0):
        checks._run_version_command(["metaflac", "--version"])
    checks._run_version_command(["metaflac", "--version"])  # outside a check
    assert 0 < timeouts[0] <= 5.0, timeouts
    assert timeouts[1] == checks._PROBE_TIMEOUT_S, "the cap leaked out of the check"


def test_a_cancelled_check_marks_what_it_did_not_reach() -> None:
    """Shutdown cancel is an early stop too, and must not read as complete."""
    calls: list[str] = []

    def probe(dep_id: str) -> Callable[[], ProbeResult]:
        def run() -> ProbeResult:
            calls.append(dep_id)
            return ProbeResult(present=True, version=(1, 0, 0), location="/x")

        return run

    mgr = DependencyManager(specs=[_spec(n, probe(n)) for n in ("a", "b", "c")])
    report = mgr.check_all(cancelled=lambda: bool(calls))

    assert calls == ["a"]
    assert [s.dep_id for s in report.unchecked] == ["b", "c"]
    assert "cancelled" in report.unchecked_reason
    assert not report.complete


def test_a_complete_check_says_nothing_about_unchecked_tools() -> None:
    """Non-triviality: the marker is absent when there is nothing to mark."""
    from platterpus.deps.manager import describe_unchecked

    report = DependencyManager(specs=[_spec("a", _present())]).check_all(
        deadline_s=30.0
    )
    assert report.unchecked == [] and report.unchecked_reason == ""
    assert report.complete
    assert describe_unchecked(report) == ""
    assert describe_unchecked(None) == ""


def test_describe_unchecked_names_every_tool_and_the_reason() -> None:
    from platterpus.deps.manager import describe_unchecked, unchecked_names

    spec_a = _spec("a", _present())
    report = DependencyReport(
        unchecked=[spec_a, _spec("b", _present())],
        unchecked_reason="stopped after 120 s: the check took too long",
    )
    assert unchecked_names(report) == ["a", "b"]
    sentence = describe_unchecked(report)
    assert "not checked: a, b" in sentence
    assert "stopped after 120 s" in sentence
