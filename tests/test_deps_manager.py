"""Tests for platterpus.deps.manager.

The manager is constructed with a custom spec list so each test isolates the
check_all probe/classify path. (Resolution routing lives in the GUI —
``main_window_deps._resolve_missing_unified`` — not the manager; the old
``resolve_missing`` cascade was removed as the unused second implementation.)
"""

from __future__ import annotations

from collections.abc import Callable

from platterpus.deps.checks import ProbeResult
from platterpus.deps.manager import DependencyManager, DependencyReport
from platterpus.deps.registry import DependencySpec, Tier

# --- Spec/probe factories -------------------------------------------------


def _spec(
    dep_id: str,
    probe: Callable[[], ProbeResult],
    tier: Tier = Tier.AUTO,
    min_version: tuple[int, ...] = (0, 0, 0),
    install_command: list[str] | None = None,
    fallback_tiers: tuple[Tier, ...] = (),
) -> DependencySpec:
    return DependencySpec(
        dep_id=dep_id,
        display_name=dep_id,
        probe=probe,
        min_version=min_version,
        tier=tier,
        install_command=install_command,
        search_string=f"install {dep_id}",
        fallback_tiers=fallback_tiers,
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
