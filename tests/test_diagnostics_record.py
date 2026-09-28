"""cyanrip's `-j` record reaches each rip's report bundle, and stays out of the album.

**What went wrong.** The record is written in the rip's cwd, the rips ROOT, and
the album folder is below it. The evidence bundle reads the album folder, so it
never collected the record: 0 occurrences in the 2026-09-07 bundle's manifest,
"all 8 paths relative" (TASKS, the `-j` rows). For a rip cyanrip refuses before it
opens a logfile, that record is the only evidence there is.

**What these tests hold.** The record's location is read off the argv the ripper
was spawned with, never predicted, and the bundle collects it by name from there.
The record is NOT moved into the album folder: a rip leaves only its `.log`,
`.cue` and `.platterpus.json` there (the maintainer, 2026-09-27). The end-to-end
tests assert that too, so a later "tidy-up" that moves it fails here.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from platterpus import diagnostics_record as dr
from platterpus.adapters.cyanrip_backend import DIAGNOSTICS_RECORD_PREFIX, CyanripImpl
from platterpus.evidence_bundle import build_bundle

NAME = f"{DIAGNOSTICS_RECORD_PREFIX}-20260927T010203Z.json"
RECORD_GLOB = f"{DIAGNOSTICS_RECORD_PREFIX}-*.json"


# --- where the record is: read off the argv, never predicted -------------------


def test_the_record_path_is_read_off_the_argv_the_ripper_was_given(
    tmp_path: Path,
) -> None:
    argv = ["cyanrip", "-N", "-j", NAME, "-G"]
    assert dr.record_path_from_argv(argv, tmp_path) == tmp_path / NAME
    assert dr.record_path_from_argv(["cyanrip", "-j", "/abs/x.json"], tmp_path) == (
        Path("/abs/x.json")
    )
    # genopt: a repeated single-value option replaces the previous one.
    assert dr.record_path_from_argv(["c", "-j", "a", "-j", "b"], tmp_path) == (
        tmp_path / "b"
    )
    assert dr.record_path_from_argv(["cyanrip", "-N"], tmp_path) is None
    assert dr.record_path_from_argv(["cyanrip", "-j"], tmp_path) is None
    assert dr.record_path_from_argv([], tmp_path) is None


def test_the_reader_finds_the_record_the_real_argv_builder_names(
    tmp_path: Path,
) -> None:
    """The relation between the two places the flag is written.

    If the builder renamed its flag or moved the name, a reader keyed on its own
    copy of the flag would find nothing, and every record would silently stop
    reaching the bundle again.
    """
    argv = CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=3,
        read_offset_override=6,
    )

    found = dr.record_path_from_argv(argv, tmp_path)

    assert found is not None, f"no -j record found in the real argv: {argv}"
    assert found.parent == tmp_path, "the builder's name is not relative any more"
    assert found.name.startswith(DIAGNOSTICS_RECORD_PREFIX), found


# --- how the bundle names it ------------------------------------------------------


def test_bundle_members_names_each_record_once_and_keeps_its_file_name(
    tmp_path: Path,
) -> None:
    first = tmp_path / "a" / NAME
    second = tmp_path / "b" / NAME  # same name, another directory

    members = dr.bundle_members([first, second, first])

    assert members == {
        f"ripperdiagnostics/{NAME}": first,
        f"ripperdiagnostics2/{NAME}": second,
    }, "a repeated dict key would have dropped one record silently"
    assert all(name.endswith(NAME) for name in members), "the suffix must survive"
    assert dr.bundle_members([]) == {}


def test_a_record_in_the_rips_root_reaches_the_bundle_and_not_as_album_content(
    tmp_path: Path,
) -> None:
    root = tmp_path / "rips"
    album = root / "Artist" / "Album"
    album.mkdir(parents=True)
    (album / "Album.log").write_text("ripper log\n", encoding="utf-8")
    record = root / NAME
    record.write_text('{"exit_code": 0}\n', encoding="utf-8")

    result = build_bundle(
        dest_dir=tmp_path / "bundles",
        stamp="20260927T000000Z",
        app_version="0.6.61",
        outcome="test",
        album_dir=album,
        log_dir=tmp_path / "no-logs-here",
        files=dr.bundle_members([record]),
    )

    assert result.path is not None, result.error
    with tarfile.open(result.path, "r:gz") as tar:
        names = tar.getnames()
    assert [n for n in names if n.endswith(NAME)] == [f"ripperdiagnostics/{NAME}"]
    assert "album/Album.log" in names, "the album walk itself stopped working"


# --- end to end: the real argv builder, the real spawn, the real worker ----------
#
# A stand-in binary that does what cyanrip does with the two paths it is given:
# the log goes into the folder `-D` names (created relative to the cwd), and the
# `-j` record goes to the name it was handed, relative to the cwd, as it exits.
# Nothing here tells the worker where the record is; it has to read the argv.

_STAND_IN = """#!/bin/sh
case "$1" in --verify-log|--version|-V) exit 0 ;; esac
record=""; dir="."
while [ $# -gt 0 ]; do
  case "$1" in
    -j) record="$2"; shift 2 ;;
    -D) dir="$2"; shift 2 ;;
    *) shift ;;
  esac
done
echo "ripping"
if [ "{refuse}" = "yes" ]; then
  echo "Invalid argument: the rip was refused before any logfile was opened"
  printf '{{"exit_code": 1}}\\n' > "$record"
  exit 1
fi
mkdir -p "$dir"
printf 'cyanrip 0.9.3 (release)\\nRipping errors: 0\\n' > "$dir/rip.log"
printf '{{"exit_code": 0}}\\n' > "$record"
exit 0
"""


def _worker_rip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, refuse: bool
) -> tuple[Path, object, list[tuple[bool, str]]]:
    from platterpus.workers.rip_worker import RipParameters, RipWorker

    binary = tmp_path / "cyanrip"
    binary.write_text(_STAND_IN.format(refuse="yes" if refuse else "no"))
    binary.chmod(0o755)
    impl = CyanripImpl(binary_path=str(binary))
    monkeypatch.setattr(impl, "version", lambda: "cyanrip 0.9.3 (release)")
    root = tmp_path / "rips"
    worker = RipWorker(
        impl,
        RipParameters(
            drive="/dev/sr0",
            release_id="",
            output_dir=root,
            track_template="%A/%d/%t - %n",
            disc_template="%A/%d/%d",
        ),
    )
    finished: list[tuple[bool, str]] = []
    worker.finished.connect(lambda ok, path: finished.append((ok, path)))
    worker.start_rip()
    return root, worker, finished


def test_a_real_rips_record_stays_in_the_rips_root_and_is_named_for_the_bundle(
    qapp: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, worker, finished = _worker_rip(tmp_path, monkeypatch, refuse=False)

    assert finished and finished[0][1], f"the rip wrote no log: {finished}"
    album = Path(finished[0][1]).parent
    assert album != root, "the stand-in did not create the -D folder"
    in_root = sorted(root.glob(RECORD_GLOB))
    assert len(in_root) == 1, f"the record is not in the rips root: {in_root}"
    assert not list(album.glob(RECORD_GLOB)), (
        "a diagnostics record is in the album folder; a rip leaves only its .log, "
        ".cue and .platterpus.json there (the maintainer, 2026-09-27)"
    )
    records = worker.diagnostics_records  # type: ignore[attr-defined]
    assert records == (in_root[0],), records
    assert list(dr.bundle_members(records).values()) == in_root


def test_a_refused_rip_names_its_only_evidence_for_the_bundle(
    qapp: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P4: a run refused during argument validation opens no logfile at all."""
    root, worker, finished = _worker_rip(tmp_path, monkeypatch, refuse=True)

    assert finished == [(False, "")], finished
    in_root = sorted(root.glob(RECORD_GLOB))
    assert len(in_root) == 1, f"the stand-in wrote no record: {in_root}"
    assert worker.diagnostics_records == (in_root[0],)  # type: ignore[attr-defined]
