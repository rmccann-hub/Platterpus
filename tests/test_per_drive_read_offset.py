"""Each drive rips at its OWN read offset (the owner's rule of 2026-11-12).

*"Test the drive once, up front, save it per drive."* Until that day a rip
applied ONE global offset (``Config.read_offset``), and the per-drive profile only
recorded provenance. So a second drive the AccurateRip list does not carry ripped
at the FIRST drive's offset with no prompt — every sample shifted, silently. The
fix makes the selected drive's profile the offset a rip applies, decided in one
place (``offset_config.offset_for_drive``, asked through the window's
``_selected_drive_offset``).

These drive the REAL Start path (``_on_rip_requested``) on a real ``MainWindow``,
with only the worker start replaced by a recorder, so each assertion is about the
``-s`` value cyanrip would have been handed. The pure rule and the hand-over plan
are pinned on their own in ``tests/test_offset_config.py``.

**What the stand-ins do that the product does not.** The drive picker is
monkeypatched to answer for whichever drive the test "selects", and sysfs is
replaced so a drive's serial is what the test says; the window's own code reads
both through the same calls it uses on the rig.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import stop_window_threads
from PySide6.QtWidgets import QApplication, QMessageBox
from test_ui_main_window import _make_window

from platterpus.config import Config
from platterpus.drive_profiles import (
    Confidence,
    DriveProfile,
    OffsetRecord,
    OffsetSource,
)
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.ui import message_boxes
from platterpus.workers.rip_worker import RipParameters

#: The rig's drive: the bundled AccurateRip list says +667 for it.
_PIONEER = DriveDescriptor(
    device="/dev/sr0", vendor="PIONEER", model="BD-RW  BDR-209D", release="1.0"
)
#: A drive no list carries — the case that ripped silently at the other's offset.
_UNLISTED = DriveDescriptor(
    device="/dev/sr1", vendor="ACME", model="Frobnicator 9000", release="1"
)


@pytest.fixture()
def make_window(qapp: QApplication) -> Iterator[Any]:
    """A real MainWindow, its threads stopped afterwards (as `teardown_threads`)."""
    created: list[Any] = []

    def factory(**kwargs: Any) -> Any:
        window = _make_window(qapp, **kwargs)
        created.append(window)
        return window

    yield factory
    for window in created:
        stop_window_threads(window)
        window.deleteLater()


class _Rig:
    """Selects drives on a window and records what Start hands the worker."""

    def __init__(self, window: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        self.window = window
        self.selected: DriveDescriptor | None = None
        self.started: list[RipParameters] = []
        self.warnings: list[str] = []
        self.wizard_opened = 0
        drives = [_PIONEER, _UNLISTED]
        monkeypatch.setattr(
            window._drive_picker, "current_drive", lambda: self.selected
        )
        monkeypatch.setattr(window._drive_picker, "all_drives", lambda: drives)
        # A serial per device node, so two drives — even two of one model — have
        # two fingerprints, as two drives that expose a serial do.
        monkeypatch.setattr(
            "platterpus.ui.main_window_drive.read_drive_identity",
            lambda device: (f"SN{device[-1]}", ""),
        )
        monkeypatch.setattr(window, "_start_rip_worker", self.started.append)
        monkeypatch.setattr(message_boxes, "information", lambda *a, **k: None)

        def warning(_parent: object, title: str, *_a: object, **_k: object) -> Any:
            self.warnings.append(title)
            return QMessageBox.StandardButton.No

        monkeypatch.setattr(message_boxes, "warning", warning)
        monkeypatch.setattr(
            window,
            "_on_drive_setup",
            lambda: setattr(self, "wizard_opened", self.wizard_opened + 1),
        )

    def select(self, drive: DriveDescriptor) -> None:
        self.selected = drive

    def start(self) -> RipParameters | None:
        """Press Start on the selected drive; the params the worker got, or None."""
        assert self.selected is not None
        before = len(self.started)
        self.window._on_rip_requested(
            RipParameters(
                drive=self.selected.device,
                release_id="",
                output_dir=Path("/tmp/x"),
                track_template="t",
                disc_template="d",
                unknown=True,
            )
        )
        return self.started[-1] if len(self.started) > before else None


def test_two_drives_with_different_saved_offsets_each_rip_at_their_own(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect, the whole way: two drives set up in turn, each saving its own
    offset through the app's one writer. The config's single value is then the
    SECOND drive's, which is what the first drive used to rip at."""
    window = make_window(config=Config(drive_setup_prompted=True))
    rig = _Rig(window, monkeypatch)
    rig.select(_PIONEER)
    assert window._set_read_offset_override(691) is True  # measured on this unit
    rig.select(_UNLISTED)
    assert window._set_read_offset_override(102) is True
    assert window._config.read_offset == 102, "floor: the global holds drive 2's"

    rig.select(_PIONEER)
    first = rig.start()
    rig.select(_UNLISTED)
    second = rig.start()

    assert first is not None and second is not None, rig.warnings
    assert first.read_offset_override == 691
    assert second.read_offset_override == 102
    assert rig.warnings == [], "a deliberate (hand-entered) offset was questioned"


def test_an_unlisted_second_drive_with_no_offset_is_refused_not_given_the_firsts(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The silent wrong-offset rip: drive 1 is set up (+667 from the list), then
    drive 2 — not in the list, never set up — is selected and Start pressed. It
    must stop and offer the wizard; before the fix it ripped at +667."""
    window = make_window(config=Config(drive_setup_prompted=True))
    rig = _Rig(window, monkeypatch)
    rig.select(_PIONEER)
    assert rig.start() is not None  # auto-applies the list's +667 for drive 1
    assert window._config.override_read_offset is True
    assert window._config.read_offset == 667, "floor: drive 1's offset is the global"

    rig.select(_UNLISTED)
    monkeypatch.setattr(
        message_boxes,
        "warning",
        lambda _p, title, *_a, **_k: (
            rig.warnings.append(title) or QMessageBox.StandardButton.Yes
        ),
    )
    params = rig.start()

    assert params is None, f"drive 2 ripped at {params.read_offset_override!r}"
    assert rig.warnings == ["Set up your drive first"]
    assert rig.wizard_opened == 1, "answering Yes did not offer the drive wizard"
    assert window._selected_drive_offset().value is None


def test_an_existing_users_global_offset_moves_to_the_drive_it_was_used_on(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Migration: a user of an earlier version, offset +48 applied to every rip,
    on a drive the list does not carry. The first drive seen inherits it, so that
    user is not suddenly blocked — and a second drive does NOT inherit it."""
    window = make_window(
        config=Config(
            drive_setup_prompted=True, override_read_offset=True, read_offset=48
        )
    )
    rig = _Rig(window, monkeypatch)
    assert window._drive_profiles.global_offset_moved is False

    rig.select(_UNLISTED)
    params = rig.start()

    assert params is not None and params.read_offset_override == 48, rig.warnings
    decision = window._selected_drive_offset()
    assert decision.record is not None
    assert decision.record.source is OffsetSource.GLOBAL_CONFIG
    assert window._drive_profiles.global_offset_moved is True

    rig.select(_PIONEER)  # a drive with nothing saved: the list's value, not +48
    second = rig.start()
    assert second is not None and second.read_offset_override == 667


def test_the_drive_already_holding_the_global_value_keeps_it_and_no_other_inherits(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Migration, the other branch: the profile ledger already records the
    global +48 for drive 1, so that is the drive it was set up on. Drive 2,
    selected first under the new code, is asked to be set up, not handed +48."""
    window = make_window(
        config=Config(
            drive_setup_prompted=True, override_read_offset=True, read_offset=48
        )
    )
    rig = _Rig(window, monkeypatch)
    pioneer_fp = window._fingerprint_for(_PIONEER)[0]
    window._drive_profiles.upsert(
        DriveProfile(
            fingerprint=pioneer_fp,
            vendor=_PIONEER.vendor,
            model=_PIONEER.model,
            offset=OffsetRecord(48, OffsetSource.MANUAL, Confidence.MEDIUM),
        )
    )

    rig.select(_UNLISTED)
    assert rig.start() is None
    assert rig.warnings == ["Set up your drive first"]

    rig.select(_PIONEER)
    rig.warnings.clear()
    held = rig.start()
    assert held is not None and held.read_offset_override == 48
    assert rig.warnings == [], "drive 1's deliberate +48 was questioned"


def test_the_disagreement_prompt_is_per_drive_and_respects_a_manual_offset(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two units of the listed model (two serials): one measured by hand at +691,
    one carrying the bogus 0 an old detection left. Only the second is offered
    the list's +667; the hand-entered +691 is never questioned."""
    window = make_window(config=Config(drive_setup_prompted=True))
    rig = _Rig(window, monkeypatch)
    second_unit = DriveDescriptor(
        device="/dev/sr2", vendor="PIONEER", model="BD-RW  BDR-209D", release="1.0"
    )
    rig.select(second_unit)
    assert window._set_read_offset_override(0, OffsetSource.OFFSET_FIND) is True
    rig.select(_PIONEER)
    assert window._set_read_offset_override(691, OffsetSource.MANUAL) is True

    manual = rig.start()
    assert manual is not None and manual.read_offset_override == 691
    assert rig.warnings == []

    rig.select(second_unit)
    healed = rig.start()  # the prompt is answered No: the drive's own 0 is kept
    assert rig.warnings == ["Read offset disagreement"]
    assert healed is not None and healed.read_offset_override == 0

    rig.select(_PIONEER)
    rig.warnings.clear()
    again = rig.start()
    assert again is not None and again.read_offset_override == 691
    assert rig.warnings == []


def test_a_rip_for_a_device_other_than_the_selected_drive_is_refused(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The offset is looked up for the selected drive and the rip reads
    ``params.drive``; if the two ever differ, one drive's offset would be paired
    with the other's audio, so Start refuses and says why."""
    window = make_window(config=Config(drive_setup_prompted=True))
    rig = _Rig(window, monkeypatch)
    rig.select(_PIONEER)
    window._set_read_offset_override(667, OffsetSource.ACCURATERIP_LIST)
    window._on_rip_requested(
        RipParameters(
            drive=_UNLISTED.device,
            release_id="",
            output_dir=Path("/tmp/x"),
            track_template="t",
            disc_template="d",
            unknown=True,
        )
    )
    assert rig.started == []
    assert rig.warnings == ["Drive changed"]


def test_a_read_offset_written_as_a_setting_is_saved_for_the_selected_drive(
    make_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`set read_offset N` (and any single-setting write of the field) used to
    change only the config, which no rip reads any more: a silent no-op. It goes
    to the one offset writer now, so the drive selected gets it, as a hand entry."""
    window = make_window(config=Config(drive_setup_prompted=True))
    rig = _Rig(window, monkeypatch)
    rig.select(_UNLISTED)

    assert window._save_user_setting("read_offset", 6).applied is True

    decision = window._selected_drive_offset()
    assert decision.value == 6
    assert decision.record is not None
    assert decision.record.source is OffsetSource.MANUAL
    params = rig.start()
    assert params is not None and params.read_offset_override == 6
