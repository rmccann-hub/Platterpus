"""The drive-cache check runs in a folder of its own and leaves nothing behind.

TASKS R97 (the owner's report of 2026-10-28): `cd-paranoia -A` always writes
`cdparanoia.log` in the folder it starts in, and the probe was started with no
folder, so a Full run left a 325 KB log in the owner's home folder. These tests
run the REAL probe path (`probe_cache_defeat` with its default runner, through
`KillableCommand`) against a stand-in `cd-paranoia` that behaves like the real
one in the way that matters: it writes `cdparanoia.log` in its working folder.
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import pytest

from platterpus.adapters import cache_probe, cache_probe_folder

#: The real `cd-paranoia -A` output from the BDR-209D, committed as a fixture.
_REAL_OUTPUT: Path = Path(__file__).parent / "fixtures" / "cdparanoia_A_bdr209d.txt"

#: A stand-in for `cd-paranoia -A`: prints the real output, and writes its log to
#: `cdparanoia.log` in the folder it was started in, as the real tool does.
_STAND_IN = """#!/bin/sh
printf 'line %s of the timing sweep\\n' 1 2 3 > cdparanoia.log
echo 'Drive tests OK with Paranoia.' >> cdparanoia.log
cat "{fixture}"
"""


@pytest.fixture
def stand_in(tmp_path: Path) -> Path:
    if shutil.which("sh") is None:
        pytest.skip("no sh")
    tool = tmp_path / "bin" / "cd-paranoia"
    tool.parent.mkdir()
    tool.write_text(_STAND_IN.format(fixture=_REAL_OUTPUT), encoding="utf-8")
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    return tool


def test_the_probe_leaves_no_log_where_it_was_launched(
    tmp_path: Path, stand_in: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched = tmp_path / "home"
    launched.mkdir()
    monkeypatch.chdir(launched)
    work = tmp_path / "data"

    result = cache_probe.probe_cache_defeat("", binary=stand_in, work_dir=work)

    # Non-triviality: the stand-in ran, and its verdict was read.
    assert result.exit_code == 0, result
    assert result.cache_sectors == 140, result.raw_output
    # The defect: nothing written where Platterpus was launched.
    assert not (launched / "cdparanoia.log").exists()
    assert os.listdir(launched) == []
    # The log came back with the result, and its folder is gone.
    assert "Drive tests OK with Paranoia." in result.analysis_log
    assert list(work.iterdir()) == []


def test_without_a_folder_of_its_own_the_probe_does_not_run(
    tmp_path: Path, stand_in: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-safe against littering: a folder that cannot be made means no run."""
    launched = tmp_path / "home"
    launched.mkdir()
    monkeypatch.chdir(launched)
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x", encoding="utf-8")

    result = cache_probe.probe_cache_defeat("", binary=stand_in, work_dir=blocker)

    assert result.error and result.exit_code is None, result
    assert os.listdir(launched) == []


def test_a_long_log_keeps_its_end(tmp_path: Path) -> None:
    """The summary is at the end of the tool's log, so the bound keeps the tail."""
    (tmp_path / cache_probe_folder.ANALYSIS_LOG_NAME).write_text(
        "\n".join(f"timing {n}" for n in range(9000)) + "\nDrive tests OK.",
        encoding="utf-8",
    )
    kept = cache_probe_folder.take_analysis_log(tmp_path)
    assert kept.rstrip().endswith("Drive tests OK.")
    assert "timing 0" in kept
    assert len(kept.splitlines()) < 1000
