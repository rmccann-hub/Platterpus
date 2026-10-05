"""One inventory of every component, with when its versions were measured.

Help → About and the acceptance bundle's ``COMPONENTS.json`` both read
`build_info.component_inventory`, so they cannot describe one machine two ways;
Diagnostics and the rip report read the summariser underneath it. A version is a
fact about the moment it was measured, so every surface shows when, and About can
measure again without freezing the window.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as _NS

import pytest
from PySide6.QtWidgets import QApplication

from platterpus import build_info
from platterpus.deps import manager as dep_manager
from platterpus.deps.build_notes import cyanrip_build_note, own_versions
from platterpus.deps.checks import ProbeResult
from platterpus.deps.manager import DependencyManager, DependencyReport
from platterpus.deps.registry import DependencySpec, Tier
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
            # No build note in this report, so the tool's own text is NOT
            # DETERMINED, and says so, rather than being left out.
            "version_text": None,
            "location": "/home/u/.local/bin/cyanrip",
            "min_version_met": True,
        }
    }
    assert inventory["dependencies_measured_at"] == "2026-09-24T17:00:00+00:00"


# --- each tool's own version text (TASKS.md: "COMPONENTS.json names the ripper
# as 0.9.4"; declared to the fork in round 30 lap 4, S43) ----------------------

#: The ripper's banner as the `.18` and `.17` fork builds print it, and as an
#: upstream release prints it. All three parse to `0.9.4`, which is the defect.
_FORK_18 = "cyanrip 0.9.4-rc2+platterpus.18 (platterpus-fork-g51cc789)"
_FORK_17 = "cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-g0981c69)"
_UPSTREAM = "cyanrip 0.9.4 (release)"


def _real_spec(dep_id: str, raw: str, *, noted: bool) -> DependencySpec:
    """A real spec, checked by the real manager, so the build note is the real one.

    A stand-in report with a hand-made `build_notes` would bypass the code that
    fills that map in production; this goes through `DependencyManager.check_all`
    and the registry's own `cyanrip_build_note`.
    """
    return DependencySpec(
        dep_id=dep_id,
        display_name=dep_id,
        probe=lambda: ProbeResult(
            present=True,
            version=(0, 9, 4),
            location=f"/home/u/.local/bin/{dep_id}",
            raw_output=raw,
        ),
        min_version=(0, 0, 0),
        tier=Tier.MANUAL,
        install_command=None,
        search_string="x",
        build_note=cyanrip_build_note if noted else None,
    )


def _checked(cyanrip_banner: str) -> DependencyReport:
    return DependencyManager(
        [
            _real_spec("cyanrip", cyanrip_banner, noted=True),
            _real_spec("flac", "flac 1.5.0", noted=False),
        ]
    ).check_all()


def test_the_bundle_names_the_rippers_own_version_text() -> None:
    """``COMPONENTS.json`` said ``"cyanrip": {"version": "0.9.4"}`` for every build.

    The new key carries what the binary said about itself, beside ``version``,
    which is unchanged for every reader that already compares it.
    """
    entries = build_info.component_inventory(_checked(_FORK_18))["dependencies"]
    assert entries is not None
    assert entries["cyanrip"]["version"] == "0.9.4"  # unchanged, for compatibility
    assert entries["cyanrip"]["version_text"] == "0.9.4-rc2+platterpus.18"
    # The fork from upstream, and one fork release from the next: the version
    # alone cannot, and the three must not collapse to one value.
    named: dict[str, str | None] = {}
    versions: set[str | None] = set()
    for banner in (_FORK_17, _FORK_18, _UPSTREAM):
        rows = build_info.component_inventory(_checked(banner))["dependencies"]
        assert rows is not None
        named[banner] = rows["cyanrip"]["version_text"]
        versions.add(rows["cyanrip"]["version"])
    assert named == {
        _FORK_17: "0.9.4-rc2+platterpus.17",
        _FORK_18: "0.9.4-rc2+platterpus.18",
        _UPSTREAM: "0.9.4",
    }
    assert versions == {"0.9.4"}


def test_an_undetermined_version_text_is_stated_never_omitted_or_empty() -> None:
    """Tri-state: a string, or ``null`` for *not determined*. Never absent, never ``""``.

    Two ways to reach it: a tool whose check has no build note (flac), and the
    ripper when its check captured no banner. A tool that is not there at all is
    ``present: false`` beside the same ``null``.
    """
    entries = build_info.component_inventory(_checked(""))["dependencies"]
    assert entries is not None
    assert set(entries) == {"cyanrip", "flac"}  # floor: both rows examined
    for dep_id in ("cyanrip", "flac"):
        assert "version_text" in entries[dep_id], dep_id
        assert entries[dep_id]["version_text"] is None, dep_id
    missing = DependencyReport(
        missing=[
            _NS(  # type: ignore[list-item]  # a stand-in missing item
                spec=_NS(dep_id="picard"),
                probe=_NS(present=False, version=None, location=None),
            )
        ]
    )
    absent = build_info.component_inventory(missing)["dependencies"]
    assert absent is not None
    assert absent["picard"]["present"] is False
    assert absent["picard"]["version_text"] is None


def test_the_components_file_carries_the_key_as_json() -> None:
    """The bundle writes the inventory with `json.dumps(..., indent=2)`; read it
    back from text, as the fork's reader would, and find the key beside
    ``version``."""
    text = json.dumps(build_info.component_inventory(_checked(_FORK_18)), indent=2)
    read = json.loads(text)["dependencies"]
    assert read["cyanrip"]["version_text"] == "0.9.4-rc2+platterpus.18"
    assert read["flac"]["version_text"] is None
    assert '"version_text": null' in text
    keys = list(read["cyanrip"])
    assert keys.index("version_text") == keys.index("version") + 1


def test_about_and_the_bundle_read_the_same_key() -> None:
    """The relation, not either side: About shows the inventory's own text.

    Before, About read `own_versions` beside an inventory that did not carry it,
    so a caller handing About an inventory got the parsed ``0.9.4``.
    """
    report = _checked(_FORK_18)
    inventory = build_info.component_inventory(report)
    entries = inventory["dependencies"]
    assert entries is not None
    # The inventory delegates to the reader About used: one text, two surfaces.
    assert entries["cyanrip"]["version_text"] == own_versions(report)["cyanrip"]
    markdown = AboutDialog._build_markdown(inventory)
    assert "- cyanrip: `0.9.4-rc2+platterpus.18` ✓" in markdown
    assert "- cyanrip: 0.9.4 ✓" not in markdown
    # A tool with no text of its own still shows its parsed version.
    assert "- flac: 0.9.4 ✓" in markdown


def test_the_inventory_survives_a_reader_that_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never raises: a failure reading the notes reads as *not determined*."""
    import platterpus.deps.build_notes as notes

    def boom(_report: object) -> dict[str, str]:
        raise RuntimeError("nope")

    monkeypatch.setattr(notes, "own_versions", boom)
    entries = build_info.component_inventory(_checked(_FORK_18))["dependencies"]
    assert entries is not None
    assert entries["cyanrip"]["version_text"] is None
    assert entries["cyanrip"]["version"] == "0.9.4"


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


def test_about_names_the_tools_an_incomplete_check_did_not_reach() -> None:
    """The rows are what was measured; the note is what was not.

    Passed beside the inventory rather than inside it: the inventory is also the
    acceptance bundle's components file, which crosses the handshake seam.
    """
    from platterpus.deps.manager import describe_unchecked

    report = _report()
    report.unchecked = [_NS(dep_id="metaflac", display_name="metaflac")]  # type: ignore[list-item]  # a stand-in spec
    report.unchecked_reason = "the check stopped after 120 s"
    dep_manager.remember_report(report)
    try:
        markdown = AboutDialog._build_markdown()  # production path: reads the store
        assert "- cyanrip: 0.9.4 ✓" in markdown
        assert "⚠ Check incomplete — 1 not checked: metaflac" in markdown
        assert "stopped after 120 s" in markdown
        # The note travels with the report, never with the inventory.
        inventory = build_info.component_inventory(report)
        assert "unchecked" not in str(sorted(inventory))
        assert describe_unchecked(report) in markdown
    finally:
        dep_manager.remember_report(None)
