"""Tests for platterpus.offset_config.

Since 2026-11-12 it holds the one rule for which read offset a rip applies: the
SELECTED drive's own, from its profile (`offset_for_drive`), and the one-time plan
that hands the single global offset of older versions to the drive it was set up
on (`plan_global_offset_move`). The window-level proof that each drive rips at
its own is `tests/test_per_drive_read_offset.py`.

Since 2026-09-24 the module reads no file at all. The leftover config folder of
the ripper older versions drove is still REMOVED by the uninstaller, and the sweep
at the bottom holds everything else to not reading it.
"""

from __future__ import annotations

import ast
from pathlib import Path

from platterpus.drive_profile_store import DriveProfileStore
from platterpus.drive_profiles import (
    Confidence,
    DriveProfile,
    OffsetRecord,
    OffsetSource,
)
from platterpus.offset_config import (
    MOVE_ALREADY_HELD,
    MOVE_INHERIT,
    MOVE_NOTHING,
    MOVE_WAIT,
    REASON_APPLIED,
    REASON_NO_DRIVE,
    REASON_NOT_SET_FOR_DRIVE,
    REASON_OUT_OF_RANGE,
    REASON_SWITCHED_OFF,
    describe_applied_offset,
    is_offset_configured,
    move_global_offset,
    offset_for_drive,
    plan_global_offset_move,
)
from platterpus.settings_validation import OFFSET_MAX

_SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"


def _record(value: int, source: OffsetSource = OffsetSource.MANUAL) -> OffsetRecord:
    return OffsetRecord(value=value, source=source, confidence=Confidence.MEDIUM)


def _profile(fingerprint: str, value: int | None) -> DriveProfile:
    return DriveProfile(
        fingerprint=fingerprint,
        vendor="V",
        model=fingerprint,
        offset=_record(value) if value is not None else None,
    )


# --- offset_for_drive: the one rule a rip's -s comes from --------------------


def test_a_drive_uses_its_own_saved_offset() -> None:
    decision = offset_for_drive(_record(691), apply_offsets=True)
    assert (decision.value, decision.reason) == (691, REASON_APPLIED)
    assert is_offset_configured(decision) is True


def test_a_drive_with_nothing_saved_gets_no_offset_never_another_drives() -> None:
    """Regression (2026-11-12): the second drive used to rip at the first one's
    global offset. With no record of its own, the answer is None."""
    decision = offset_for_drive(None, apply_offsets=True)
    assert (decision.value, decision.reason) == (None, REASON_NOT_SET_FOR_DRIVE)
    assert is_offset_configured(decision) is False


def test_the_master_switch_off_applies_nothing_but_keeps_the_record() -> None:
    record = _record(667)
    decision = offset_for_drive(record, apply_offsets=False)
    assert (decision.value, decision.reason) == (None, REASON_SWITCHED_OFF)
    assert decision.record == record  # the display can still say what is saved


def test_no_drive_selected_is_its_own_reason() -> None:
    decision = offset_for_drive(None, apply_offsets=True, drive_selected=False)
    assert (decision.value, decision.reason) == (None, REASON_NO_DRIVE)


def test_an_out_of_range_saved_offset_never_reaches_the_ripper() -> None:
    """The profile file is an input: its loader takes any whole number."""
    decision = offset_for_drive(_record(OFFSET_MAX + 1), apply_offsets=True)
    assert (decision.value, decision.reason) == (None, REASON_OUT_OF_RANGE)
    assert offset_for_drive(_record(OFFSET_MAX), apply_offsets=True).value == OFFSET_MAX


def test_describe_applied_offset_says_what_the_next_rip_does() -> None:
    on = describe_applied_offset(offset_for_drive(_record(667), apply_offsets=True))
    assert on.startswith("+667 samples, applied to every rip on this drive")
    assert "entered by hand" in on  # the provenance travels with the value
    negative = offset_for_drive(_record(-6), apply_offsets=True)
    assert describe_applied_offset(negative).startswith("-6 samples")
    off = describe_applied_offset(offset_for_drive(_record(667), apply_offsets=False))
    assert "not applied" in off and "+667" not in off
    unset = describe_applied_offset(offset_for_drive(None, apply_offsets=True))
    assert "not set for this drive" in unset
    none = offset_for_drive(None, apply_offsets=True, drive_selected=False)
    assert "no drive selected" in describe_applied_offset(none)


# --- plan_global_offset_move: who inherits an existing user's offset --------


def test_the_move_hands_the_global_offset_to_the_selected_drive() -> None:
    plan = plan_global_offset_move(
        override_read_offset=True,
        read_offset=667,
        selected_fingerprint="vm:a",
        profiles=[_profile("vm:a", None)],
    )
    assert plan == MOVE_INHERIT


def test_a_drive_already_holding_the_value_keeps_it_and_nobody_inherits() -> None:
    """It was set up on that drive; a second drive must not inherit it."""
    plan = plan_global_offset_move(
        override_read_offset=True,
        read_offset=667,
        selected_fingerprint="vm:b",
        profiles=[_profile("vm:a", 667), _profile("vm:b", None)],
    )
    assert plan == MOVE_ALREADY_HELD


def test_the_move_waits_for_a_drive_and_skips_a_value_nothing_applied() -> None:
    assert (
        plan_global_offset_move(
            override_read_offset=True,
            read_offset=667,
            selected_fingerprint=None,
            profiles=[],
        )
        == MOVE_WAIT
    )
    assert (
        plan_global_offset_move(
            override_read_offset=False,
            read_offset=667,
            selected_fingerprint="vm:a",
            profiles=[],
        )
        == MOVE_NOTHING
    )
    assert (
        plan_global_offset_move(
            override_read_offset=True,
            read_offset=OFFSET_MAX + 1,
            selected_fingerprint="vm:a",
            profiles=[],
        )
        == MOVE_NOTHING
    )


def test_the_move_replaces_the_selected_drives_record_and_marks_itself_done(
    tmp_path: Path,
) -> None:
    """The selected drive's own (different) record gives way to the value every
    rip on it used, with GLOBAL_CONFIG provenance; another drive is untouched;
    and the store is marked moved but NOT saved (the caller saves, once)."""
    path = tmp_path / "profiles.json"
    store = DriveProfileStore(
        {"vm:a": _profile("vm:a", 0), "vm:b": _profile("vm:b", 12)}, path=path
    )
    plan = move_global_offset(
        store,
        "vm:a",
        override_read_offset=True,
        read_offset=48,
        now_iso="2026-11-13T00:00:00+00:00",
    )
    assert plan == MOVE_INHERIT
    held = store.get("vm:a")
    assert held is not None and held.offset is not None
    assert (held.offset.value, held.offset.source) == (48, OffsetSource.GLOBAL_CONFIG)
    other = store.get("vm:b")
    assert other is not None and other.offset is not None
    assert other.offset.value == 12
    assert store.global_offset_moved is True
    assert not path.exists(), "the move saved the store itself"


def test_a_waiting_move_changes_nothing() -> None:
    store = DriveProfileStore(
        {"vm:a": _profile("vm:a", 3)}, path=Path("/nonexistent/p.json")
    )
    plan = move_global_offset(
        store, "", override_read_offset=True, read_offset=48, now_iso=""
    )
    assert plan == MOVE_WAIT
    assert store.global_offset_moved is False
    held = store.get("vm:a")
    assert held is not None and held.offset is not None and held.offset.value == 3


def test_the_module_does_no_io() -> None:
    """It used to read a file; nothing here may open one again."""
    tree = ast.parse((_SRC / "offset_config.py").read_text(encoding="utf-8"))
    names = {
        node.attr if isinstance(node, ast.Attribute) else node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute | ast.Name)
    }
    assert not names & {"open", "read_text", "read_bytes", "Path", "save"}, names


def test_only_the_uninstaller_refers_to_the_leftover_config_folder() -> None:
    """Nothing reads the old ripper's config folder; the uninstaller removes it.

    Derived from the tree, so a new reader anywhere in the package fails here by
    name. `paths.py` defines the constant; `deps/host_teardown.py` removes it.
    """
    users = sorted(
        str(path.relative_to(_SRC))
        for path in _SRC.rglob("*.py")
        if "LEGACY_RIPPER_CONFIG_DIR" in path.read_text(encoding="utf-8")
    )
    assert users == ["deps/host_teardown.py", "paths.py"], users
