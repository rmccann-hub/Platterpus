"""The verified-read chase, end to end in the rip worker (TASKS R7).

Drives ``RipWorker`` synchronously with the fake backend from
``test_rip_worker``: an album pass, a securing pass whose reads disagree and
whose kept read AccurateRip rejects, then single reads of that track. The logs
are synthetic, shaped on the 2026-10-12 hardware run's track 5 (``C96464AB``
once, the value AccurateRip verifies, ``4065BECC`` twice, the majority kept at
the repeat limit). No audio: each "FLAC" is a few marker bytes.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication
from test_rip_worker import _FakeBackend, _FakeHandle, _params

from platterpus.verified_read_chase import (
    CHASE_KEPT_VERIFIED,
    CHASE_SKIPPED_READS_AGREED,
)
from platterpus.workers.rip_worker import RipWorker

_ALBUM_PASS = (
    "cyanrip 0.9.3 (release)\n"
    "Disc tracks:    1\n"
    "AccurateRip:    found\n"
    "Track 1 ripped and encoded successfully!\n"
    "  EAC CRC32:     E0036697\n"
    "  Accurip:       disc found in database (max confidence: 200)\n"
    "    Accurip v2:  9EEB8843 (not found, either a new pressing, or bad rip)\n"
    "  File(s):\n"
    "    Artist/Album/01 - A.flac\n"
    "Ripping errors: 0\n"
)


def _securing_pass(values: tuple[str, ...], kept: str) -> str:
    """A -Z 2 pass that hit the repeat limit; ``values`` are its printed reads."""
    loop = "".join(
        f"Repeating ripping (0 out of 2 matches for current checksum {v})\n"
        for v in values
    )
    return (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    1\n"
        "AccurateRip:    found\n"
        f"{loop}"
        "Done; (repeat limit of 3 reads reached; at most 2 reads agreed)\n"
        "Track 1 read with errors.\n"
        f"  EAC CRC32:     {kept} (after 3 rips)\n"
        "  Accurip:       disc found in database (max confidence: 200)\n"
        "    Accurip v2:  11111111 (not found, either a new pressing, or bad rip)\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )


def _single_read(crc: str, confidence: int | None) -> str:
    ar = (
        f"accurately ripped, confidence {confidence}"
        if confidence
        else "not found, either a new pressing, or bad rip"
    )
    return (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    1\n"
        "AccurateRip:    found\n"
        "Track 1 read successfully!\n"
        f"  EAC CRC32:     {crc}\n"
        "  Accurip:       disc found in database (max confidence: 200)\n"
        f"    Accurip v2:  BCF4E815 ({ar})\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )


def _run(
    tmp_path: Path,
    securing: str,
    singles: list[tuple[str, int | None, int]],
) -> tuple[RipWorker, _FakeBackend]:
    """Album pass, securing pass, then one scripted single read per later call.

    ``singles`` holds (EAC CRC32, AccurateRip v2 confidence or None, exit code).
    Each call gets its own handle, so a single read's exit code can differ from
    the securing pass's.
    """
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))

    def side_effect(call: dict) -> None:  # type: ignore[type-arg]  # the fake's own record
        index = len(backend.rip_calls) - 1
        rel = call["output_dir"] / "Artist" / "Album"
        rel.mkdir(parents=True, exist_ok=True)
        if index == 0:
            (rel / "rip.log").write_text(_ALBUM_PASS, encoding="utf-8")
            (rel / "01 - A.flac").write_bytes(b"ALBUM-E0036697")
            return
        if index == 1:
            (rel / "rerip.log").write_text(securing, encoding="utf-8")
            (rel / "01 - A.flac").write_bytes(b"SECURING")
            return
        crc, confidence, exit_code = singles[index - 2]
        backend.set_handle(_FakeHandle(lines=["ripping"], exit_code=exit_code))
        (rel / "single.log").write_text(_single_read(crc, confidence), encoding="utf-8")
        (rel / "01 - A.flac").write_bytes(f"SINGLE-{crc}".encode())

    backend.rip_side_effect = side_effect
    worker = RipWorker(
        backend,
        _params(
            tmp_path,
            read_speed_mode="auto_ladder",
            secure_rerip_matches=2,
            secure_rerip_dynamic=True,
            max_retries=5,
        ),
    )
    worker.start_rip()
    return worker, backend


def test_a_read_accuraterip_verifies_replaces_the_majority_read_it_rejects(
    qapp: QApplication, tmp_path: Path
) -> None:
    """THE incident: the securing pass saw C96464AB once and kept 4065BECC. The
    chase reads the track singly, the second read is verified, and the album
    keeps that read, with the record saying which read and why."""
    worker, backend = _run(
        tmp_path,
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        [("4065BECC", None, 0), ("C96464AB", 200, 0)],
    )

    assert len(backend.rip_calls) == 4, "floor: the chase took two single reads"
    for call in backend.rip_calls[2:]:
        assert call["secure_rerip_matches"] == 0, "a chase read sent -Z"
        assert call["only_tracks"] == (1,)
        assert call["read_speed"] == 0
    album = tmp_path / "Artist" / "Album"
    assert (album / "01 - A.flac").read_bytes() == b"SINGLE-C96464AB"
    (entry,) = worker.retried_tracks
    assert entry["replaced"] is True
    assert entry["replaced_because"] == "accuraterip"
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["outcome"] == CHASE_KEPT_VERIFIED
    assert chase["kept_attempt"] == 2
    assert [a["eac_crc"] for a in chase["attempts"]] == ["4065BECC", "C96464AB"]
    assert worker.unstable_tracks == []
    report = worker.secure_rerip_report
    assert report is not None and report.get("verified_rereads") == [1]
    # The shipped record is the kept read's, for the report and the EAC log.
    assert getattr(worker.swapped_track_records[1], "copy_crc", "") == "C96464AB"
    # Both reads' own logs are kept, with argv and exit status; the addendum
    # describes the file on disk.
    kept_logs = (album / "rip.platterpus-verified-read.txt").read_text()
    assert kept_logs.count("=== Platterpus verified-read chase") == 2
    addendum = (album / "rip.platterpus-addendum.txt").read_text()
    assert "CRC C96464AB" in addendum
    assert "a single read with no -Z" in addendum


def test_a_chase_read_never_takes_the_securing_passs_exit_status(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Each pass has its own exit field (ruling C1); a chase read that exits 1
    must not be reported as the securing pass exiting 1, and is not kept."""
    worker, backend = _run(
        tmp_path,
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        # Every read exits 1, the last included: the securing pass's field would
        # end on 1 if a chase read wrote it (a last read exiting 0 hides that).
        [("C96464AB", 200, 1)] + [("4065BECC", None, 1)] * 4,
    )
    assert len(backend.rip_calls) == 2 + 5, "floor: the chase ran to its limit"
    assert worker.securing_pass_exit_code == 0
    assert worker.ripper_exit_code == 0
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["kept_attempt"] is None
    assert chase["attempts"][0]["exit_code"] == 1
    assert entry["replaced"] is False
    album = tmp_path / "Artist" / "Album"
    assert (album / "01 - A.flac").read_bytes() == b"ALBUM-E0036697"


def test_a_drive_that_returned_one_value_every_time_gets_no_extra_reads(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Every printed read and both block CRCs equal: the record says the chase
    was skipped and why, and no single read is spawned."""
    worker, backend = _run(
        tmp_path,
        _securing_pass(("E0036697", "E0036697"), "E0036697"),
        [],
    )
    assert len(backend.rip_calls) == 2
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["outcome"] == CHASE_SKIPPED_READS_AGREED
    assert chase["attempts"] == []
