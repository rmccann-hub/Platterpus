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


def _securing_pass(
    values: tuple[str, ...],
    kept: str,
    limit_line: str = "Done; (repeat limit of 3 reads reached; at most 2 reads agreed)",
) -> str:
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
        f"{limit_line}\n"
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


#: The lines a fork log states for track 3 of the reference disc (LSNs and the
#: album pass's read time, `output_reference/cyanrip_fork_flac/…police_classics.log`),
#: which give the chase a time budget and so, with the 200 top entry, 16 reads.
_FORK_GEOMETRY = (
    "    Elapsed:            303.06 s\n"
    "    Start LSN:   28067 (with offset: 28068)\n"
    "    End LSN:     49919 (with offset: 49921)\n"
)


def _run(
    tmp_path: Path,
    securing: str,
    singles: list[tuple[str, int | None, int]],
    album: str = _ALBUM_PASS,
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
            (rel / "rip.log").write_text(album, encoding="utf-8")
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


def test_two_agreeing_printed_reads_under_a_proven_limit_still_get_the_chase(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The newer limit wording proves a read count: three reads, at most two
    agreed, and two printed reads that agree, so the third differed. That is two
    values, not one, and the chase reads the track singly (R66, `plan_chase`)."""
    worker, backend = _run(
        tmp_path,
        _securing_pass(("E0036697", "E0036697"), "E0036697"),
        [("E0036697", 200, 0)],
    )
    assert len(backend.rip_calls) > 2, "a proven second value was not chased"
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["outcome"] != CHASE_SKIPPED_READS_AGREED


def test_a_drive_that_returned_one_value_every_time_gets_no_extra_reads(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Every printed read and both block CRCs equal: the record says the chase
    was skipped and why, and no single read is spawned.

    In the OLDER limit wording, which proves no read count. The fork's newer
    "repeat limit of 3 reads reached; at most 2 reads agreed" beside two
    agreeing printed reads proves the third, unprinted read differed (R66,
    `plan_chase`), so that log is not "one value every time", and the chase
    rightly runs on it (the test below)."""
    worker, backend = _run(
        tmp_path,
        _securing_pass(
            ("E0036697", "E0036697"),
            "E0036697",
            "Done; (no matches found, but hit repeat limit of 3)",
        ),
        [],
    )
    assert len(backend.rip_calls) == 2
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["outcome"] == CHASE_SKIPPED_READS_AGREED
    assert chase["attempts"] == []


def test_a_track_accuraterip_knows_well_is_read_past_the_old_five(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Round 39, G1: track 3 reads right about one read in three, so five single
    reads miss it on half of all five-rip runs. With the LSNs and read time a fork
    log states and a top entry of 200, the chase may read 16 times inside its
    time budget, and keeps the seventh read here, which the old limit never took."""
    album = _ALBUM_PASS.replace(
        "Track 1 ripped and encoded successfully!\n",
        "Track 1 ripped and encoded successfully!\n" + _FORK_GEOMETRY,
    )
    worker, backend = _run(
        tmp_path,
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        [("4065BECC", None, 0)] * 6 + [("C96464AB", 200, 0)],
        album=album,
    )
    assert len(backend.rip_calls) == 2 + 7
    album_dir = tmp_path / "Artist" / "Album"
    assert (album_dir / "01 - A.flac").read_bytes() == b"SINGLE-C96464AB"
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["kept_attempt"] == 7
    assert chase["attempt_limit"] == 16
    assert chase.get("attempt_limit_reason") == "high_confidence"
    assert chase.get("after") == "securing_pass"
    assert chase.get("time_budget_seconds") == round(5 * 21853 / 75, 2)
    assert chase.get("cache_defeat") == "whole_track_read"
    # Every attempt carries its own time, for a surface printing "attempt k".
    assert all(isinstance(a.get("seconds"), float) for a in chase["attempts"]), chase[
        "attempts"
    ]


# --- Round 39: the chase on Archival Exact's album pass (TASKS R7's open item) ---


def _archival_album(values: tuple[str, ...], kept: str, done: str) -> str:
    """Archival Exact's album pass: every track read with -Z, here one track whose
    reads ended on ``kept``, which AccurateRip rejects, with ``values`` printed."""
    loop = "".join(
        f"Repeating ripping (0 out of 2 matches for current checksum {v})\n"
        for v in values
    )
    return (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    1\n"
        "AccurateRip:    found\n"
        f"{loop}{done}\n"
        "Track 1 ripped and encoded successfully!\n"
        f"{_FORK_GEOMETRY}"
        f"  EAC CRC32:     {kept} (after 3 rips)\n"
        "  Accurip:       disc found in database (max confidence: 200)\n"
        "    Accurip v2:  9EEB8843 (not found, either a new pressing, or bad rip)\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )


def _run_archival(
    tmp_path: Path, album: str, singles: list[tuple[str, int | None, int]]
) -> tuple[RipWorker, _FakeBackend]:
    """An Archival Exact rip (-Z 2 on every track from the first read), then one
    scripted single read per later call."""
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))

    def side_effect(call: dict) -> None:  # type: ignore[type-arg]  # the fake's own record
        index = len(backend.rip_calls) - 1
        rel = call["output_dir"] / "Artist" / "Album"
        rel.mkdir(parents=True, exist_ok=True)
        if index == 0:
            (rel / "rip.log").write_text(album, encoding="utf-8")
            (rel / "01 - A.flac").write_bytes(b"ALBUM")
            return
        crc, confidence, exit_code = singles[index - 1]
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
            secure_rerip_dynamic=False,
            max_retries=5,
        ),
    )
    worker.start_rip()
    return worker, backend


def test_archival_exact_chases_a_converged_read_accuraterip_rejects(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The 2026-10-21 shape (`round36full1021asecurereread.log:225-231`): the -Z
    album pass read the verified 59D352DD first, then converged on 3D8FCF0C,
    which it kept. No securing pass looks at a converged track, so until round 39
    the album shipped it. Now the chase reads it singly and keeps the read
    AccurateRip verifies, recorded as following the album pass."""
    album = _archival_album(
        ("59D352DD", "3D8FCF0C", "3D8FCF0C"),
        "3D8FCF0C",
        "Done; (2 out of 2 matches for current checksum 3D8FCF0C)",
    )
    worker, backend = _run_archival(
        tmp_path, album, [("3D8FCF0C", None, 0), ("59D352DD", 200, 0)]
    )
    assert len(backend.rip_calls) == 1 + 2, "floor: the chase took two single reads"
    assert backend.rip_calls[0]["secure_rerip_matches"] == 2, "not an archival rip"
    for call in backend.rip_calls[1:]:
        assert call["secure_rerip_matches"] == 0 and call["only_tracks"] == (1,)
    album_dir = tmp_path / "Artist" / "Album"
    assert (album_dir / "01 - A.flac").read_bytes() == b"SINGLE-59D352DD"
    (entry,) = worker.retried_tracks
    assert entry["trigger"] == "accuraterip" and entry["reripped_z"] == 0
    assert entry["replaced"] is True and entry["replaced_because"] == "accuraterip"
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase.get("after") == "album_pass"
    assert chase["kept_attempt"] == 2
    assert chase["attempt_limit"] == 16, "the album pass's LSNs gave no budget"
    report = worker.secure_rerip_report
    assert report is not None and report.get("verified_rereads") == [1]
    assert "CRC 59D352DD" in (album_dir / "rip.platterpus-addendum.txt").read_text()
    assert (album_dir / "rip.platterpus-verified-read.txt").exists()


def test_archival_exact_does_not_chase_a_track_whose_every_read_agreed(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Three -Z reads, one value: the same skip as after a securing pass, recorded,
    and no single read spawned."""
    album = _archival_album(
        ("3D8FCF0C", "3D8FCF0C"),
        "3D8FCF0C",
        "Done; (2 out of 2 matches for current checksum 3D8FCF0C)",
    )
    worker, backend = _run_archival(tmp_path, album, [])
    assert len(backend.rip_calls) == 1
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["outcome"] == CHASE_SKIPPED_READS_AGREED
    assert chase.get("after") == "album_pass"
    assert entry["replaced"] is False


def test_fast_verified_never_runs_the_album_pass_chase(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The album-pass chase is Archival Exact's alone: in dynamic mode the securing
    pass, and the chase after it, already cover every unverified track."""
    worker, backend = _run(
        tmp_path,
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        [("C96464AB", 200, 0)],
    )
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase.get("after") == "securing_pass"
    assert len(backend.rip_calls) == 3


def test_the_workers_second_addendum_write_in_one_rip_keeps_the_first(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The worker's sidecar writer accumulates (`rip_addendum.merged_rows`), so
    the album-pass chase's write cannot erase the securing pass's rows."""
    from platterpus.rip_addendum import SupersededTrack

    worker = RipWorker(_FakeBackend(handle=_FakeHandle()), _params(tmp_path))
    log_path = tmp_path / "Album.log"
    log_path.write_text("cyanrip\n", encoding="utf-8")
    worker._append_swap_addendum(
        str(log_path), "instability", [SupersededTrack(number=4, crc="AAAAAAAA")]
    )
    worker._append_swap_addendum(
        str(log_path), "accuraterip", [SupersededTrack(number=3, crc="59D352DD")]
    )
    text = (tmp_path / "Album.platterpus-addendum.txt").read_text(encoding="utf-8")
    assert "CRC AAAAAAAA" in text and "CRC 59D352DD" in text


def test_the_securing_pass_asks_for_its_time_limit_and_a_chase_read_never_does(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Round 39 (TASKS R49): the securing pass hands the backend rule 2's seconds
    (track 3's ceil(5 x 291.37) = 1457, from the album pass's LSNs), which the
    backend sends as --reread-time-limit to a build that lists it; the chase's
    single reads carry no -Z, so they never ask for it."""
    album = _ALBUM_PASS.replace(
        "Track 1 ripped and encoded successfully!\n",
        "Track 1 ripped and encoded successfully!\n" + _FORK_GEOMETRY,
    )
    worker, backend = _run(
        tmp_path,
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        [("C96464AB", 200, 0)],
        album=album,
    )
    assert len(backend.rip_calls) == 3, "floor: album pass, securing pass, a read"
    assert backend.rip_calls[0]["reread_time_limit_s"] is None, "album pass"
    assert backend.rip_calls[1]["reread_time_limit_s"] == 1457, "securing pass"
    assert backend.rip_calls[2]["reread_time_limit_s"] is None, "a chase read"


def test_archival_exact_reads_without_printed_values_are_not_determined_not_agreed(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Tri-state on the archival path: the album pass is both the kept read and the
    reads compared, so its block CRC must not be compared with itself. With no
    printed -Z values and no limit line, nothing shows how many values the drive
    returned: "not determined", never "the reads agreed"."""
    from platterpus.verified_read_chase import CHASE_SKIPPED_NOT_DETERMINED

    album = _archival_album((), "3D8FCF0C", "")
    worker, backend = _run_archival(tmp_path, album, [])
    assert len(backend.rip_calls) == 1
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None and chase["outcome"] == CHASE_SKIPPED_NOT_DETERMINED
    assert chase["distinct_reads_seen"] is None


def test_the_per_track_record_reads_the_chase_attempt_from_the_chase_block(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Round 39 G3's record says "chase attempt k" from the chase block's
    `kept_attempt` (`track_record_sources.chase_attempts_by_track`), the one
    field, not a parallel one; it must read the archival path's chase too, and
    the attempt's own time sits beside it in the same block."""
    from platterpus.track_record_sources import chase_attempts_by_track

    album = _archival_album(
        ("59D352DD", "3D8FCF0C", "3D8FCF0C"),
        "3D8FCF0C",
        "Done; (2 out of 2 matches for current checksum 3D8FCF0C)",
    )
    worker, _backend = _run_archival(
        tmp_path, album, [("3D8FCF0C", None, 0), ("59D352DD", 200, 0)]
    )
    assert chase_attempts_by_track(worker.retried_tracks) == {1: 2}
    (entry,) = worker.retried_tracks
    chase = entry.get("verified_read_chase")
    assert chase is not None
    kept = chase["attempts"][chase["kept_attempt"] - 1]
    assert kept["attempt"] == 2 and kept["kept"] is True
    assert isinstance(kept.get("seconds"), float)
