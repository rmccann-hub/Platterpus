"""Tests for whipper_gui.drive_access.

The public diagnose function takes injectable probes, so we simulate
every system state without real hardware or root.
"""

from __future__ import annotations

from whipper_gui.drive_access import (
    SEVERITY_NO_DEVICE,
    SEVERITY_OK,
    SEVERITY_PERMISSION,
    diagnose_drive_access,
)


def test_no_device_node() -> None:
    d = diagnose_drive_access(list_nodes=lambda: [])
    assert d.severity == SEVERITY_NO_DEVICE
    assert d.actionable is False
    assert d.fix_command is None
    assert "No optical drive" in d.summary


def test_readable_node_reports_ok() -> None:
    d = diagnose_drive_access(
        list_nodes=lambda: ["/dev/sr0"],
        is_readable=lambda p: True,
    )
    assert d.severity == SEVERITY_OK
    assert d.actionable is False
    assert "/dev/sr0" in d.detail
    assert d.devices == ("/dev/sr0",)


def test_unreadable_node_not_in_group_is_actionable() -> None:
    d = diagnose_drive_access(
        list_nodes=lambda: ["/dev/sr0"],
        is_readable=lambda p: False,
        group_of=lambda p: "cdrom",
        in_group=lambda g: False,
    )
    assert d.severity == SEVERITY_PERMISSION
    assert d.actionable is True
    assert d.fix_command == "sudo usermod -aG cdrom $USER"
    assert "isn't a member" in d.detail


def test_unreadable_node_already_in_group_suggests_relogin() -> None:
    d = diagnose_drive_access(
        list_nodes=lambda: ["/dev/sr0"],
        is_readable=lambda p: False,
        group_of=lambda p: "optical",
        in_group=lambda g: True,
    )
    assert d.severity == SEVERITY_PERMISSION
    assert d.fix_command == "sudo usermod -aG optical $USER"
    assert "Log out" in d.detail or "log out" in d.detail


def test_unknown_group_falls_back_to_cdrom() -> None:
    d = diagnose_drive_access(
        list_nodes=lambda: ["/dev/sr0"],
        is_readable=lambda p: False,
        group_of=lambda p: None,
        in_group=lambda g: False,
    )
    assert d.fix_command == "sudo usermod -aG cdrom $USER"
