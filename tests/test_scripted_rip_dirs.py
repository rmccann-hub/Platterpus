"""A script run's bundle carries each scripted rip's full log, never its audio.

Found 2026-11-04 preparing round 38's drive-mode test: a `cyanrip ... -D <folder>`
step wrote the rip's log into the rips folder, and the run's bundle carried only
the run folder, so the owner's upload had a one-line summary per rip and none of
the logs. ``uiscript/scripted_rip_dirs.py`` names the folders; these tests hold
that the bundle then carries every log, cue and record in them, and no audio.
"""

from __future__ import annotations

import ast
import tarfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus.evidence_bundle import build_bundle
from platterpus.uiscript.scripted_rip_dirs import (
    MAX_RIP_DIRS,
    RIP_DIR_PREFIX,
    bundle_extra_dirs,
    rip_output_dir,
)

RUNNER = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "platterpus"
    / "uiscript"
    / "runner.py"
)


def _names_in(archive: Path) -> set[str]:
    with tarfile.open(archive, "r:gz") as tar:
        return set(tar.getnames())


def _log_dir(tmp_path: Path) -> Path:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.txt").write_text("app log\n")
    return logs


def test_the_d_folder_is_resolved_against_the_step_s_folder(tmp_path: Path) -> None:
    args = ["-N", "-l", "5", "-D", "dmfiveearly1", "-o", "flac"]
    assert rip_output_dir(args, tmp_path) == tmp_path / "dmfiveearly1"


def test_the_last_d_wins_and_an_absolute_one_is_taken_as_given(tmp_path: Path) -> None:
    absolute = tmp_path / "elsewhere"
    assert rip_output_dir(["-D", "a", "-D", str(absolute)], tmp_path) == absolute


def test_no_d_and_unsafe_values_name_no_folder(tmp_path: Path) -> None:
    assert rip_output_dir(["-l", "3"], tmp_path) is None
    assert rip_output_dir(["-D"], tmp_path) is None
    assert rip_output_dir(["-D", ""], tmp_path) is None
    assert rip_output_dir(["-D", "../up"], tmp_path) is None
    assert rip_output_dir(["-D", "has space"], tmp_path) is None


def test_the_mapping_keeps_the_run_folder_and_is_bounded(tmp_path: Path) -> None:
    run = tmp_path / "run"
    dirs = [tmp_path / f"d{i}" for i in range(MAX_RIP_DIRS + 3)]
    extra, left_out = bundle_extra_dirs(run, [dirs[0], dirs[0], *dirs[1:]])
    assert extra["scriptrun"] == run
    assert len(extra) == 1 + MAX_RIP_DIRS
    assert left_out == dirs[MAX_RIP_DIRS:]
    assert extra[f"{RIP_DIR_PREFIX}/d0"] == dirs[0]


def test_a_bundle_carries_each_rip_s_log_and_record_and_no_audio(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "transcript.txt").write_text("transcript\n")
    rips = tmp_path / "rips"
    folder = rip_output_dir(["-D", "dmfiveearly1"], rips)
    assert folder is not None
    folder.mkdir(parents=True)
    (folder / "dmfiveearly1.log").write_text("cyanrip log\nRipping errors: 0\n")
    (folder / "dmfiveearly1.cue").write_text('FILE "05.flac" WAVE\n')
    (folder / "dmfiveearly1.diagnostics.json").write_text("{}\n")
    (folder / "05.flac").write_bytes(b"fLaC\x00audio")

    extra, left_out = bundle_extra_dirs(run, [folder])
    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20261104T000000Z",
        app_version="0.7.121",
        outcome="test script run",
        log_dir=_log_dir(tmp_path),
        extra_dirs=extra,
    )

    assert left_out == []
    assert result.path is not None, result.error
    names = _names_in(result.path)
    assert "scriptrun/transcript.txt" in names
    for kept in (
        "dmfiveearly1.log",
        "dmfiveearly1.cue",
        "dmfiveearly1.diagnostics.json",
    ):
        assert f"{RIP_DIR_PREFIX}/dmfiveearly1/{kept}" in names, names
    assert not any(name.endswith(".flac") for name in names), "audio entered a bundle"


def test_the_runner_hands_the_bundle_the_scripted_rip_folders() -> None:
    """The wiring, at the call site: the run's bundle is built from
    ``bundle_extra_dirs``, not from a literal holding the run folder alone."""
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", getattr(node.func, "id", "")) == "build_bundle"
    ]
    assert calls, "runner.py no longer builds a bundle; this test is measuring nothing"
    for call in calls:
        extra = next((kw.value for kw in call.keywords if kw.arg == "extra_dirs"), None)
        assert isinstance(extra, ast.Name), ast.unparse(call)
    assert "bundle_extra_dirs(" in RUNNER.read_text(encoding="utf-8")
    assert "rip_output_dir(" in RUNNER.read_text(encoding="utf-8")


@given(st.lists(st.text(max_size=40), max_size=12))
def test_rip_output_dir_never_raises(args: list[str]) -> None:
    rip_output_dir(args, Path("/tmp/rips"))
