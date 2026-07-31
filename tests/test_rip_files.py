# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.rip_files — "which files did THIS rip write?".

The bug these exist for: every post-rip check used to glob the album folder, so
leftovers from an earlier *cancelled* rip were verified as if this rip had
written them. The reported sequence is reproduced verbatim in
``_album_with_leftovers``: cancel a rip (partial files, one truncated FLAC), fix
a track title, re-rip with *Replace* — the corrected titles produce new
filenames, so the new files land beside the old rather than over them.

The four consumers are exercised through their own public entry points (not just
the helper), because the point of the fix is that all four now agree.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from platterpus import checksums, rip_files
from platterpus.adapters.ctdb_client import CTDBClient, CtdbLookupResult
from platterpus.adapters.flac_verify import FlacVerifyResult
from platterpus.ctdb import diagnose
from platterpus.ctdb.toc import DiscToc
from platterpus.workers.ctdb_worker import verify_rip_dir as ctdb_verify_rip_dir
from platterpus.workers.derived_verify_worker import (
    verify_rip_dir as derived_verify_rip_dir,
)
from platterpus.workers.flac_verify_worker import verify_rip_dir as flac_verify_rip_dir

# --- fixtures: a real cyanrip log + a contaminated album folder -------------

# The files the *current* rip wrote (the titles the user corrected).
THIS_RIP: tuple[str, ...] = ("01 - Roxanne.flac", "02 - Message In A Bottle.flac")
# What the earlier, cancelled rip left behind: the old (misspelled) title, plus a
# truncated file it was mid-write on when it was killed. Both are `.flac` in the
# same folder, so the old glob returned all four.
LEFTOVERS: tuple[str, ...] = ("01 - Roxane.flac", "02 - Message In A Bottel.flac")
TRUNCATED: str = LEFTOVERS[1]


def _cyanrip_log(
    names: tuple[str, ...], *, folder: str = "The Police/Greatest Hits"
) -> str:
    """A minimal but real-shaped cyanrip log naming ``names``, one per track.

    Filenames are written the way cyanrip writes them — relative to the configured
    output *root*, not to the album folder — so the tests exercise the same
    basename mapping production does.
    """
    lines = ["cyanrip 0.9.3 (release)", "Device model:   PIONEER BD-RW BDR-209D", ""]
    for number, name in enumerate(names, start=1):
        lines += [
            f"Track {number} ripped and encoded successfully!",
            "  EAC CRC32:     A1B2C3D4",
            "  File(s):",
            f"    {folder}/{name}",
            "",
        ]
    lines += [f"Tracks ripped accurately: {len(names)}/{len(names)}", ""]
    return "\n".join(lines)


def _album_with_leftovers(tmp_path: Path, *, log: bool = True) -> Path:
    """The reported scenario: this rip's N files plus a cancelled rip's leftovers.

    ``log=False`` reproduces a folder with no usable rip record, which must
    degrade to the old folder scan rather than verifying nothing.
    """
    album = tmp_path / "The Police" / "Greatest Hits"
    album.mkdir(parents=True)
    for name in THIS_RIP:
        (album / name).write_bytes(b"FLAC-this-rip")
    for name in LEFTOVERS:
        # The truncated one is deliberately short/garbage — this is the file that
        # made `flac --test` fail and downgraded a clean rip's verdict.
        (album / name).write_bytes(b"\x00" if name == TRUNCATED else b"FLAC-old-rip")
    if log:
        (album / "Greatest Hits.log").write_text(
            _cyanrip_log(THIS_RIP), encoding="utf-8"
        )
    return album


# --- declared_names: reading the rip's own record ---------------------------


def test_declared_names_are_basenames_in_track_order() -> None:
    """The log's path is relative to the output root; callers hold the album
    folder. And order must follow the log's track numbers, not the filenames —
    an unpadded naming template sorts "10" before "2" lexically."""
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    parsed = parse_cyanrip_log(
        _cyanrip_log(("1 - A.flac", "2 - B.flac", "10 - J.flac"))
    )
    assert rip_files.declared_names(parsed) == (
        "1 - A.flac",
        "2 - B.flac",
        "10 - J.flac",
    )


def test_declared_names_never_escapes_the_album_folder() -> None:
    """Log text is external input: a name with a traversal component must be
    reduced to a basename, never used to point outside the folder asked about."""

    class _Track:
        number = 1
        filename = "../../../etc/passwd"

    class _Log:
        tracks = (_Track(),)

    assert rip_files.declared_names(_Log()) == ("passwd",)


def test_declared_names_never_raises_on_junk() -> None:
    class _Log:
        tracks = "not a track list"

    assert rip_files.declared_names(_Log()) == ()
    assert rip_files.declared_names(None) == ()
    assert rip_files.declared_names(object()) == ()


# --- the core regression: leftovers are excluded ---------------------------


def test_master_files_exclude_a_cancelled_rips_leftovers(tmp_path: Path) -> None:
    """The bug, at the source: 4 FLACs on disk, 2 written by this rip."""
    album = _album_with_leftovers(tmp_path)

    result = rip_files.rip_master_files(album)

    assert result.authoritative
    assert [p.name for p in result.files] == list(THIS_RIP)
    assert len(result.files) == 2  # not 4
    # The specific file that caused the false ⚠ FAILED must be out.
    assert TRUNCATED not in [p.name for p in result.files]
    assert sorted(p.name for p in result.excluded) == sorted(LEFTOVERS)


def test_excluded_leftovers_are_logged_by_name(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A verify covering 2 of the 4 files in a folder must be explainable from
    the app log — otherwise the fix just moves the confusion."""
    album = _album_with_leftovers(tmp_path)
    with caplog.at_level(logging.INFO, logger="platterpus.rip_files"):
        rip_files.rip_master_files(album)
    assert "this rip did not write" in caplog.text
    assert TRUNCATED in caplog.text


def test_falls_back_to_the_folder_scan_and_logs_when_no_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Degrade, don't refuse: with no rip record, verifying the folder beats
    verifying nothing — but the reduced confidence must be in the log."""
    album = _album_with_leftovers(tmp_path, log=False)
    with caplog.at_level(logging.WARNING, logger="platterpus.rip_files"):
        result = rip_files.rip_master_files(album)

    assert not result.authoritative
    assert result.source == rip_files.SOURCE_GLOB
    assert len(result.files) == 4  # the old behaviour, unchanged
    assert "falling back to a folder scan" in caplog.text


def test_falls_back_when_the_declared_files_are_all_gone(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A log describing files that aren't there (moved album, manual tidy-up)
    can't scope anything — fall back loudly rather than verify an empty set."""
    album = tmp_path / "Album"
    album.mkdir()
    (album / "Album.log").write_text(
        _cyanrip_log(("01 - Gone.flac",)), encoding="utf-8"
    )
    (album / "01 - Something Else.flac").write_bytes(b"x")

    with caplog.at_level(logging.WARNING, logger="platterpus.rip_files"):
        result = rip_files.rip_master_files(album)

    assert not result.authoritative
    assert [p.name for p in result.files] == ["01 - Something Else.flac"]
    assert "none of which are on disk" in caplog.text


def test_eac_companion_log_does_not_defeat_the_scoping(tmp_path: Path) -> None:
    """The optional "(EAC-compatible).log" is written AFTER the ripper's log, so
    "newest .log" alone would pick it — and neither parser reads its filename
    lines, which would silently drop us back to the glob."""
    album = _album_with_leftovers(tmp_path)
    (album / "Greatest Hits (EAC-compatible).log").write_text(
        "Exact Audio Copy V1.6 from 23. October 2020\n\nFilename C:\\x\\01.wav\n",
        encoding="utf-8",
    )

    result = rip_files.rip_master_files(album)

    assert result.authoritative
    assert [p.name for p in result.files] == list(THIS_RIP)


def test_a_stale_rip_log_loses_to_the_current_one(tmp_path: Path) -> None:
    """Two rip logs in one folder: the newest that names files wins."""
    import os

    album = _album_with_leftovers(tmp_path)
    stale = album / "Greatest Hits (old).log"
    stale.write_text(_cyanrip_log(LEFTOVERS), encoding="utf-8")
    # Make the stale log unambiguously older than the current one.
    os.utime(stale, (1_000_000, 1_000_000))

    assert [p.name for p in rip_files.rip_master_files(album).files] == list(THIS_RIP)


def test_master_files_on_a_missing_folder_returns_empty_not_raise(
    tmp_path: Path,
) -> None:
    result = rip_files.rip_master_files(tmp_path / "nope")
    assert result.files == ()


def test_a_declared_file_that_vanished_is_reported_not_fatal(tmp_path: Path) -> None:
    """One of this rip's files deleted between rip and verify: verify the rest,
    and record the missing one so the gap is visible rather than invented."""
    album = _album_with_leftovers(tmp_path)
    (album / THIS_RIP[1]).unlink()

    result = rip_files.rip_master_files(album)

    assert result.authoritative  # a partial list still beats the folder listing
    assert [p.name for p in result.files] == [THIS_RIP[0]]
    assert result.missing == (THIS_RIP[1],)


def test_an_oversized_log_is_skipped_not_slurped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A "log" far bigger than any real one isn't ours; reading it would stall a
    post-rip worker. Skipping it degrades to the folder scan."""
    album = _album_with_leftovers(tmp_path)
    monkeypatch.setattr(rip_files, "_MAX_LOG_BYTES", 8)  # every log is now oversized

    result = rip_files.rip_master_files(album)

    assert not result.authoritative
    assert len(result.files) == 4


def test_an_unreadable_log_is_skipped_not_raised(tmp_path: Path) -> None:
    """A `.log` that can't be read (here: a directory wearing the name) must not
    turn "which files are mine?" into an exception on a worker thread."""
    album = _album_with_leftovers(tmp_path, log=False)
    (album / "Greatest Hits.log").mkdir()

    result = rip_files.rip_master_files(album)

    assert not result.authoritative  # fell back, did not raise
    assert len(result.files) == 4


def test_rip_log_can_be_passed_in_instead_of_re_read(tmp_path: Path) -> None:
    """The finish handler already parses the log; the seam lets it hand the
    parsed object over instead of paying for a second read."""
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    album = _album_with_leftovers(tmp_path, log=False)  # nothing on disk to read
    parsed = parse_cyanrip_log(_cyanrip_log(THIS_RIP))

    result = rip_files.rip_master_files(album, rip_log=parsed)

    assert result.authoritative
    assert [p.name for p in result.files] == list(THIS_RIP)


# --- consumer 1: CTDB verify (the TOC must hold N tracks, not 2N) ----------


class _RecordingClient(CTDBClient):
    """Records the TOC it was queried with; always answers "not in database"."""

    def __init__(self) -> None:
        self.queried_toc: DiscToc | None = None

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        self.queried_toc = toc
        return CtdbLookupResult()


def test_ctdb_toc_is_built_from_this_rips_files_only(tmp_path: Path) -> None:
    album = _album_with_leftovers(tmp_path)
    probed: list[Path] = []

    def probe(path: Path) -> int:
        probed.append(path)  # one call per file that enters the TOC
        return 1000

    client = _RecordingClient()
    ctdb_verify_rip_dir(client, album, samples_probe=probe, decoder=lambda _p: b"x")

    assert len(probed) == 2  # 2 tracks, not the 4 files in the folder
    assert [p.name for p in probed] == list(THIS_RIP)
    assert TRUNCATED not in [p.name for p in probed]
    assert client.queried_toc is not None
    assert len(client.queried_toc.track_offsets) == 2


# --- consumer 2: FLAC integrity verify (the false ⚠ FAILED) ---------------


def test_flac_verify_never_sees_the_truncated_leftover(tmp_path: Path) -> None:
    album = _album_with_leftovers(tmp_path)
    seen: list[list[Path]] = []

    def verifier(paths: list[Path]) -> FlacVerifyResult:
        seen.append(paths)
        # Faithful stand-in for `flac --test`: the truncated leftover is the one
        # file that would fail, so if it reaches here the verdict is downgraded.
        bad = tuple(p for p in paths if p.name == TRUNCATED)
        return FlacVerifyResult(checked=len(paths), failures=bad)

    result = flac_verify_rip_dir(album, verifier=verifier)

    assert result.checked == 2
    assert result.failures == ()  # a clean rip stays clean
    assert [p.name for p in seen[0]] == list(THIS_RIP)


# --- consumer 3: derived-file verify (expected count doubled) --------------


def test_derived_verify_expected_count_is_this_rips_track_count(
    tmp_path: Path,
) -> None:
    album = _album_with_leftovers(tmp_path)
    # A COMPLETE transcode of this rip: one .mp3 per master this rip wrote.
    for name in THIS_RIP:
        (album / name).with_suffix(".mp3").write_bytes(b"mp3")

    result = derived_verify_rip_dir(album, "mp3", hasher=lambda _p: "SAME")

    assert result.expected == 2  # not 4 — the leftovers are not masters
    assert result.checked == 2
    assert result.ok  # a complete transcode reads as complete


# --- consumer 4: the SHA256 manifest --------------------------------------


def test_manifest_records_only_files_this_rip_wrote(tmp_path: Path) -> None:
    album = _album_with_leftovers(tmp_path)
    for name in THIS_RIP:
        (album / name).with_suffix(".mp3").write_bytes(b"mp3-derived")
    # A leftover derived file from the cancelled rip, and a stale one of ours.
    (album / LEFTOVERS[0]).with_suffix(".mp3").write_bytes(b"old-mp3")

    digests = checksums.compute_digests(album)

    assert set(digests) == {
        "01 - Roxanne.flac",
        "01 - Roxanne.mp3",
        "02 - Message In A Bottle.flac",
        "02 - Message In A Bottle.mp3",
    }
    assert TRUNCATED not in digests
    assert "01 - Roxane.mp3" not in digests


def test_manifest_falls_back_to_the_recursive_scan_without_a_log(
    tmp_path: Path,
) -> None:
    """The fallback must reproduce the OLD scope exactly — including nested
    files — or the fix quietly changes what the report attests to."""
    album = _album_with_leftovers(tmp_path, log=False)
    nested = album / "bonus"
    nested.mkdir()
    (nested / "03 - Extra.flac").write_bytes(b"x")

    digests = checksums.compute_digests(album)

    assert "bonus/03 - Extra.flac" in digests
    assert len(digests) == 5  # 4 in the folder + the nested one


# --- consumer 5: the --ctdb-calibrate diagnostic --------------------------


def test_diagnose_find_flacs_is_scoped_to_this_rip(tmp_path: Path) -> None:
    album = _album_with_leftovers(tmp_path)
    assert [p.name for p in diagnose.find_flacs(album)] == list(THIS_RIP)


def test_diagnose_find_flacs_still_answers_for_a_bare_folder(tmp_path: Path) -> None:
    """The calibrate CLI is pointed at arbitrary folders, which usually have no
    parseable log — it must keep working there."""
    album = tmp_path / "Album"
    album.mkdir()
    for stem in ("02", "01"):
        (album / f"{stem}.flac").write_bytes(b"x")
    assert [p.name for p in diagnose.find_flacs(album)] == ["01.flac", "02.flac"]
