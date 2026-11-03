"""An output folder Platterpus cannot write to is refused before the rip (0.7.119).

**The measured case.** A rip to a folder this user could not write to started the
worker and failed inside the backend's ``mkdir`` with "unexpected error: [Errno
13] Permission denied", naming neither the folder nor what to do. The check is
pure (``output_writable.decide``) over facts gathered once
(``check_output_writable``), so these tests can deny a write even though the
suite may run as root, whom ``os.access`` allows everywhere.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from platterpus.output_writable import (
    WriteCheck,
    check_output_writable,
    decide,
    nearest_existing,
)


def _deny(_path: Path, _mode: int) -> bool:
    return False


def _allow(_path: Path, _mode: int) -> bool:
    return True


def test_nearest_existing_walks_up_to_what_is_there(tmp_path: Path) -> None:
    assert nearest_existing(tmp_path) == tmp_path
    assert nearest_existing(tmp_path / "a" / "b" / "c") == tmp_path
    # A link to nothing is in mkdir's way, so it counts as existing.
    (tmp_path / "dangling").symlink_to(tmp_path / "nowhere")
    assert nearest_existing(tmp_path / "dangling" / "x") == tmp_path / "dangling"


def test_a_writable_folder_or_parent_is_not_refused(tmp_path: Path) -> None:
    for folder in (tmp_path, tmp_path / "Music" / "rips"):
        result = check_output_writable(folder, access=_allow)
        assert result.refuse is False, result
        assert str(tmp_path) in result.message


def test_a_folder_this_user_cannot_write_is_refused_by_name(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    asked: list[tuple[Path, int]] = []

    def deny(path: Path, mode: int) -> bool:
        asked.append((path, mode))
        return False

    with caplog.at_level(logging.WARNING, logger="platterpus.output_writable"):
        result = check_output_writable(tmp_path, access=deny)
    assert result.refuse is True
    assert result.message.startswith(f"Cannot rip into the output folder {tmp_path}:")
    assert "not allowed to write to it" in result.message
    assert "Choose another output folder in Settings" in result.message
    # It asked for what mkdir needs, of the folder itself.
    assert asked == [(tmp_path, os.W_OK | os.X_OK)]
    # Logged as a warning, in the same words.
    assert [r.getMessage() for r in caplog.records] == [result.message]


def test_a_missing_folder_under_an_unwritable_parent_names_the_parent(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "Music"
    result = check_output_writable(folder, access=_deny)
    assert result.refuse is True
    assert f"not allowed to create it in {tmp_path}" in result.message
    assert str(folder) in result.message


def test_a_file_where_the_folder_should_be_is_refused(tmp_path: Path) -> None:
    """No permission trick needed: this one refuses even for root."""
    blocker = tmp_path / "Music"
    blocker.write_text("not a folder", encoding="utf-8")
    result = check_output_writable(blocker)
    assert result.refuse is True
    assert f"{blocker} exists, but it is not a folder" in result.message
    inside = check_output_writable(blocker / "rips")
    assert inside.refuse is True
    assert f"{blocker} is not a folder, so {blocker / 'rips'} cannot be made" in (
        inside.message
    )


def test_a_filesystem_that_gives_no_answer_is_not_checked_and_not_refused(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(_path: Path, _mode: int) -> bool:
        raise OSError(5, "Input/output error")

    with caplog.at_level(logging.WARNING, logger="platterpus.output_writable"):
        result = check_output_writable(tmp_path, access=broken)
    assert result.refuse is None
    assert result.message.startswith("output folder not checked:")
    assert any("not checked" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    ("existing", "is_dir", "writable", "refuse"),
    [
        (None, False, False, None),
        ("folder", True, True, False),
        ("folder", True, False, True),
        ("folder", False, False, True),
        ("parent", True, True, False),
        ("parent", True, False, True),
        ("parent", False, False, True),
    ],
)
def test_decide_is_tri_state(
    existing: str | None, is_dir: bool, writable: bool, refuse: bool | None
) -> None:
    folder = Path("/media/music/rips")
    where = {None: None, "folder": folder, "parent": folder.parent}[existing]
    result = decide(folder, where, is_dir, writable)
    assert isinstance(result, WriteCheck)
    assert result.refuse is refuse
    if refuse:
        assert str(folder) in result.message
