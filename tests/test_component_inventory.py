"""One inventory of every component, with when its versions were measured.

Help → About, Diagnostics, the rip report and the acceptance bundle all read
`build_info.component_inventory`, so they cannot describe one machine four ways.
A version is a fact about the moment it was measured, so every surface shows
when, and About can measure again without freezing the window.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as _NS

from PySide6.QtWidgets import QApplication

from platterpus import build_info
from platterpus.deps import manager as dep_manager
from platterpus.deps.manager import DependencyManager, DependencyReport
from platterpus.ui.help_dialogs import AboutDialog


def _report(measured_at: str = "2026-09-24T17:00:00+00:00") -> DependencyReport:
    return DependencyReport(
        ok=[_NS(dep_id="cyanrip")],
        ok_versions={"cyanrip": (0, 9, 4)},
        ok_probes={"cyanrip": _NS(location="/home/u/.local/bin/cyanrip")},
        measured_at=measured_at,
    )


class _Spec:
    def __init__(self, dep_id: str) -> None:
        self.dep_id = dep_id
        self.min_version = (0,)
        self.build_note = None

    def probe(self) -> object:
        return _NS(present=True, version=(1, 0), location=f"/usr/bin/{self.dep_id}")


def test_a_check_records_when_it_measured() -> None:
    before = datetime.now(UTC).replace(microsecond=0)
    report = DependencyManager(specs=[_Spec("flac")]).check_all()  # type: ignore[list-item]  # a stand-in spec
    measured = datetime.fromisoformat(report.measured_at)
    assert measured.tzinfo is not None
    assert before <= measured <= datetime.now(UTC)


def test_the_inventory_before_any_check_says_not_measured_not_none() -> None:
    inventory = build_info.component_inventory(None)
    assert inventory["dependencies"] is None
    assert inventory["dependencies_measured_at"] is None
    assert inventory["app"] and inventory["build"]


def test_the_inventory_carries_versions_and_their_time() -> None:
    inventory = build_info.component_inventory(_report())
    assert inventory["dependencies"] == {
        "cyanrip": {
            "present": True,
            "version": "0.9.4",
            "location": "/home/u/.local/bin/cyanrip",
            "min_version_met": True,
        }
    }
    assert inventory["dependencies_measured_at"] == "2026-09-24T17:00:00+00:00"


def test_the_age_is_worded_for_a_person() -> None:
    now = datetime(2026, 9, 24, 17, 0, tzinfo=UTC)
    at = lambda delta: (now - delta).isoformat()  # noqa: E731
    describe = build_info.describe_measured_at
    assert describe(None) == "not measured yet this session"
    assert describe(at(timedelta(seconds=5)), now).startswith("measured just now")
    assert describe(at(timedelta(minutes=4)), now).startswith("measured 4 minutes ago")
    assert describe(at(timedelta(hours=2)), now) == "measured 2 hours ago (15:00 UTC)"
    assert describe("garbage", now) == "measured at garbage"


def test_about_lists_each_dependency_with_a_marker_and_the_age() -> None:
    markdown = AboutDialog._build_markdown(build_info.component_inventory(_report()))
    assert "### Dependencies (measured" in markdown
    assert "- cyanrip: 0.9.4 ✓" in markdown
    # Before a check: says so, and names the way to run one.
    before = AboutDialog._build_markdown(build_info.component_inventory(None))
    assert "not measured yet this session" in before and "Check again" in before


def test_check_again_waits_for_the_check_and_refreshes(qapp: QApplication) -> None:
    calls: list[object] = []
    forgotten: list[bool] = []

    def recheck(on_done: object) -> object:
        calls.append(on_done)
        return lambda: forgotten.append(True)

    dep_manager.remember_report(None)
    try:
        dialog = AboutDialog(recheck=recheck)  # type: ignore[arg-type]  # a stand-in hook
        button = dialog._recheck_button
        assert button is not None
        assert "not measured yet" in dialog._viewer.toPlainText()

        button.click()
        assert len(calls) == 1
        assert not button.isEnabled() and button.text() == "Checking…"

        # The check lands: the store now holds a report, and the view shows it.
        dep_manager.remember_report(_report())
        calls[0]()  # type: ignore[operator]  # the callback the dialog handed over
        assert button.isEnabled()
        assert "cyanrip: 0.9.4" in dialog._viewer.toPlainText()

        # A second click, then the dialog closes before that check lands.
        button.click()
        dialog.reject()
        assert forgotten == [True], "closing did not stop the dialog being told"
    finally:
        dep_manager.remember_report(None)


def test_about_without_a_window_has_no_check_again(qapp: QApplication) -> None:
    assert AboutDialog()._recheck_button is None
