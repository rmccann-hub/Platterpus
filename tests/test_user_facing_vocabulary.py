# SPDX-License-Identifier: GPL-3.0-only
"""Internal vocabulary must not reach an end user's screen (UX review W2).

The UX review of 0.7.127 found the project's own working words on the surfaces a
first-time user reads: "handshake round 40" on Setup & Updates, "2 ok, 2
missing/needs-attention" and "numpy (Python package) 2.5.5" in the launch
summary, field names in Diagnostics (covered in `test_ui_diagnostics_dialog.py`),
"KDD-16" in a CTDB result line, and the container plumbing as the User Guide's
second section. (The CTDB line is pinned in `test_ui_rip_progress.py`.) Each
test here pins one of those surfaces to the plain words that
replaced it, and fails on the old wording.

The About dialog's *Ripper* section still explains handshake rounds — on purpose:
it is where the owner reads them, and where the tooltip below sends anyone who
asks.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.config import Config


def _setup_center(round_no: int) -> object:
    from platterpus.ui.dialogs.setup_center import SetupCenterDialog
    from platterpus.user_settings import SettingWrite

    return SetupCenterDialog(
        None,
        app_version="0.7.127",
        ripper_pin="edb73dd",
        ripper_version="0.9.4-rc3+platterpus.32",
        approved_by_round=round_no,
        dependency_report=None,
        actions={},
        config=Config(),
        save_setting=lambda _f, _v: SettingWrite(applied=True, message=""),
    )


def test_setup_center_says_tested_build_and_keeps_the_round_in_the_tooltip(
    qapp: QApplication,
) -> None:
    """REGRESSION (W2): "Approved build: … from handshake round 40"."""
    center = _setup_center(40)
    try:
        label = center._ripper_status_label  # type: ignore[attr-defined]
        text = label.text()
        assert "Tested build: edb73dd (0.9.4-rc3+platterpus.32)" in text, text
        assert "approved for this version of Platterpus" in text, text
        assert "handshake" not in text.lower(), text
        assert "round" not in text.lower(), text
        # The detail is kept, one hover away, for the owner and a bug report.
        assert "handshake round 40" in label.toolTip()
    finally:
        center.close()  # type: ignore[attr-defined]


def _dep_summary(monkeypatch: pytest.MonkeyPatch, report: object) -> str:
    """Render the launch summary without a window; return the text it showed."""
    from platterpus.ui.main_window_deps import DependencyMixin

    shown: list[str] = []
    for name in ("information", "warning"):
        monkeypatch.setattr(
            f"platterpus.ui.message_boxes.{name}",
            lambda _parent, _title, text: shown.append(text),
        )
    # `_show_dep_summary` reads nothing off the window but the parent it hands
    # the (stubbed) message box, so the mixin's function runs unbound.
    DependencyMixin._show_dep_summary(None, report)  # type: ignore[arg-type]
    assert len(shown) == 1
    return shown[0]


def _report(dep_ids: list[str], missing_ids: list[str] | None = None) -> object:
    from platterpus.deps.checks import ProbeResult
    from platterpus.deps.manager import DependencyReport
    from platterpus.deps.registry import SPECS
    from platterpus.deps.resolvers import MissingItem

    by_id = {s.dep_id: s for s in SPECS}
    report = DependencyReport()
    for dep_id in dep_ids:
        report.ok.append(by_id[dep_id])
        report.ok_versions[dep_id] = (2, 5, 5)
    for dep_id in missing_ids or []:
        absent = ProbeResult(present=False, version=None, location=None)
        report.missing.append(MissingItem(spec=by_id[dep_id], probe=absent))
    return report


def test_dep_summary_counts_in_plain_words(monkeypatch: pytest.MonkeyPatch) -> None:
    """REGRESSION (W2): "2 ok, 2 missing/needs-attention"."""
    text = _dep_summary(monkeypatch, _report(["metaflac"], ["cyanrip"]))
    assert text.startswith("1 installed, 1 needs attention."), text
    assert "missing/needs-attention" not in text
    text = _dep_summary(monkeypatch, _report(["metaflac", "flac"]))
    assert text.startswith("2 installed, 0 need attention."), text


def test_bundled_python_packages_are_grouped_under_their_own_heading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REGRESSION (W2): "numpy (Python package) 2.5.5" beside cyanrip.

    Kept (a bug report still needs the version) but under "Bundled components",
    by package name, and never in the "Installed:" list of things a user tends.
    """
    text = _dep_summary(monkeypatch, _report(["metaflac", "musicbrainzngs", "numpy"]))
    installed = next(
        line for line in text.splitlines() if line.startswith("Installed:")
    )
    bundled = next(line for line in text.splitlines() if line.startswith("Bundled"))
    assert "numpy" not in installed and "musicbrainzngs" not in installed, installed
    assert "metaflac" in installed, installed
    assert "numpy 2.5.5" in bundled and "musicbrainzngs 2.5.5" in bundled, bundled
    assert "nothing to install" in bundled, bundled
    assert "(Python package)" not in text, text


def test_only_python_packages_shipped_inside_are_marked_bundled() -> None:
    """The grouping keys on a registry field; a host tool must never carry it."""
    from platterpus.deps.registry import SPECS

    bundled = {s.dep_id for s in SPECS if s.bundled}
    assert bundled == {"musicbrainzngs", "numpy"}, bundled


def test_the_user_guide_puts_the_plumbing_last() -> None:
    """REGRESSION (W2): *How it's wired* was the guide's second section."""
    from platterpus.help_content import USER_GUIDE

    headings = [line for line in USER_GUIDE.splitlines() if line.startswith("## ")]
    assert len(headings) >= 10, headings  # the guide was read, not an empty string
    assert headings[-1] == "## How it's wired", headings[-3:]
    assert headings[0] == "## Ripping a CD — the basics", headings[:2]
