"""The one-file report bundle: what goes in, what must never, and what it says.

The feature exists because the maintainer had to assemble the upload by hand
(2026-08-19). The tests here are mostly about the two ways such a convenience
goes wrong: it quietly leaves something out, or it quietly puts something in.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

from platterpus.evidence_bundle import (
    ALLOWED_SUFFIXES,
    MAX_BUNDLES_KEPT,
    MAX_FILE_BYTES,
    MAX_TOTAL_BYTES,
    build_bundle,
    bundle_filename,
    prune_bundles,
    sha256_of,
)


def _names_in(archive: Path) -> set[str]:
    with tarfile.open(archive, "r:gz") as tar:
        return set(tar.getnames())


def _read_from(archive: Path, name: str) -> str:
    with tarfile.open(archive, "r:gz") as tar:
        handle = tar.extractfile(name)
        assert handle is not None, f"{name} is in the listing but has no content"
        return handle.read().decode("utf-8", errors="replace")


def _log_dir(tmp_path: Path) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    (d / "log.txt").write_text("app log line\n")
    return d


# --- Critical rule #8: no audio, ever ---------------------------------------


def test_no_audio_file_can_enter_a_bundle(tmp_path: Path) -> None:
    """**The rule this feature could most easily break.**

    The bundle walks a *rip folder*, which is by definition full of FLACs, and it
    produces a file whose entire purpose is to be uploaded somewhere. Critical
    rule #8 is absolute: no copyrighted media leaves in something we generate.

    Every extension here is checked, not just `.flac`, because the filter is an
    allowlist and the point of an allowlist is that it is right about formats
    nobody enumerated. `.foo` is in the list for exactly that reason.
    """
    album = tmp_path / "album"
    album.mkdir()
    (album / "rip.log").write_text("ripper log")
    for name in (
        "01.flac",
        "02.wav",
        "03.mp3",
        "04.m4a",
        "05.ogg",
        "06.opus",
        "07.wv",
        "08.ape",
        "09.aiff",
        "10.dsf",
        "11.aac",
        "cover.jpg",
        "mystery.foo",
    ):
        (album / name).write_bytes(b"NOT REALLY AUDIO BUT MUST NOT BE ARCHIVED")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        album_dir=album,
        log_dir=_log_dir(tmp_path),
    )

    assert result.ok, result.error
    assert result.path is not None
    names = _names_in(result.path)
    for name in names:
        suffix = Path(name).suffix.lower()
        assert suffix in ALLOWED_SUFFIXES or name.endswith("MANIFEST.txt"), (
            f"{name!r} entered the bundle with suffix {suffix!r}, which is not on "
            "the allowlist — Critical rule #8"
        )
    # Non-triviality: the archive is not empty, so "nothing forbidden is in it"
    # is not satisfied by "nothing is in it". A check that can pass by finding
    # nothing is decoration (`CLAUDE.md`).
    assert "album/rip.log" in names, f"the bundle archived nothing useful: {names}"


def test_every_exclusion_is_named_in_the_manifest(tmp_path: Path) -> None:
    """A missing artifact must be legible as excluded, not merely absent.

    A bundle that quietly holds eight of eleven artifacts looks exactly like a
    complete one, and the person reading it draws conclusions from the gap.
    """
    album = tmp_path / "album"
    album.mkdir()
    (album / "01.flac").write_bytes(b"audio")
    (album / "rip.log").write_text("ripper log")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        album_dir=album,
        log_dir=_log_dir(tmp_path),
    )

    assert result.path is not None
    manifest = _read_from(result.path, "MANIFEST.txt")
    assert "NOT INCLUDED" in manifest
    assert "01.flac" in manifest, "an excluded file left no trace in the manifest"
    assert "allowlist" in manifest
    assert [e.name for e in result.skipped] == ["album/01.flac"]


# --- The manifest tells the truth about the outcome -------------------------


def test_the_manifest_carries_the_facts_the_label_came_from(tmp_path: Path) -> None:
    """A label can be wrong; the fields it was computed from are re-derivable.

    Same reasoning as the rip report keeping raw counts beside its verdict — the
    reader must be able to disagree with our word for what happened.
    """
    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="cancelled",
        facts={"cancel requested": "True", "tracks in log": "3"},
        album_dir=None,
        log_dir=_log_dir(tmp_path),
    )

    assert result.path is not None
    manifest = _read_from(result.path, "MANIFEST.txt")
    assert "rip outcome        cancelled" in manifest
    assert "cancel requested" in manifest and "True" in manifest
    assert "tracks in log" in manifest and "3" in manifest


def test_a_rip_with_no_album_folder_still_produces_a_bundle(tmp_path: Path) -> None:
    """The failure that never got far enough to make a folder is the one that
    most needs sending. A bundle keyed on the album folder existing would skip
    exactly those."""
    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="failed",
        album_dir=None,
        log_dir=_log_dir(tmp_path),
    )

    assert result.ok, result.error
    assert result.path is not None
    assert "applog/log.txt" in _names_in(result.path)


def test_rotated_app_logs_are_included(tmp_path: Path) -> None:
    """`log.txt.1` has suffix `.1`, which is not on the allowlist. The rotations
    hold the *earlier* half of a session, and a bug reported after a long run is
    frequently explained there."""
    logs = _log_dir(tmp_path)
    (logs / "log.txt.1").write_text("older")
    (logs / "log.txt.12").write_text("older still")
    (logs / "log.txt.notanumber").write_text("must not be admitted")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        log_dir=logs,
    )

    assert result.path is not None
    names = _names_in(result.path)
    assert "applog/log.txt.1" in names
    assert "applog/log.txt.12" in names
    assert "applog/log.txt.notanumber" not in names, (
        "the rotation rule admitted a non-numeric suffix — it must key on digits"
    )


# --- Bounding, and saying so ------------------------------------------------


def test_an_oversized_file_keeps_head_and_tail_and_marks_the_gap(
    tmp_path: Path,
) -> None:
    """**Head AND tail.** A tool's fatal message is the last thing it prints, so
    a head-only cap drops precisely the line that explains the failure. And the
    elision is marked with its byte count, because a silent truncation reads as
    completeness (`CLAUDE.md`)."""
    logs = tmp_path / "logs"
    logs.mkdir()
    head = b"FIRST-LINE-MARKER\n"
    tail = b"\nLAST-LINE-MARKER-THE-FATAL-ONE"
    filler = b"x" * (MAX_FILE_BYTES + 1024)
    (logs / "log.txt").write_bytes(head + filler + tail)

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        log_dir=logs,
    )

    assert result.path is not None
    body = _read_from(result.path, "applog/log.txt")
    assert body.startswith("FIRST-LINE-MARKER")
    assert body.endswith("LAST-LINE-MARKER-THE-FATAL-ONE")
    assert "elided from the middle" in body
    entry = next(e for e in result.included if e.name == "applog/log.txt")
    assert "bounded" in entry.reason, entry.reason


# --- Never raises -----------------------------------------------------------


def test_an_unwritable_destination_reports_rather_than_raises(tmp_path: Path) -> None:
    """A convenience wrapped around a finished rip must never surface as a crash
    after a successful one."""
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file, not a directory")

    result = build_bundle(
        dest_dir=blocker / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        log_dir=_log_dir(tmp_path),
    )

    assert not result.ok
    assert result.error, "a failure produced no explanation"
    assert result.path is None


def test_an_unreadable_source_is_recorded_not_dropped(tmp_path: Path) -> None:
    """A file we could not read is a different finding from a file that was not
    there, and the bundle must not flatten the two into one silence."""
    logs = _log_dir(tmp_path)
    secret = logs / "unreadable.log"
    secret.write_text("mine")
    secret.chmod(0o000)
    try:
        result = build_bundle(
            dest_dir=tmp_path / "out",
            stamp="20260819T000000Z",
            app_version="0.6.17",
            outcome="success",
            log_dir=logs,
        )
        assert result.path is not None
        skipped = {e.name: e.reason for e in result.skipped}
        # Running as root defeats the chmod; only assert when it actually bit.
        if "applog/unreadable.log" in skipped:
            assert "unreadable" in skipped["applog/unreadable.log"]
            assert "unreadable" in _read_from(result.path, "MANIFEST.txt")
    finally:
        secret.chmod(0o600)


# --- Naming: the rule a lost rig run paid for -------------------------------


def test_the_archive_name_is_machine_readable_everywhere(tmp_path: Path) -> None:
    """Lowercase ASCII letters and digits only — no hyphens, underscores or case
    (`CLAUDE.md` → *Artifact filenames that cross machines*). A rig run was lost
    because one side spelled an artifact `round08joint.txt` and the other
    `round-08-joint.txt`."""
    name = bundle_filename("2026-08-19T00:08:08+0000")
    stem = name[: -len(".tar.gz")]
    assert stem.isalnum() and stem.islower(), name
    assert name.endswith(".tar.gz")
    assert name == "platterpusbundle20260819t0008080000.tar.gz"


def test_extra_text_is_embedded_verbatim(tmp_path: Path) -> None:
    """The diagnostics blob lives in memory, not on disk. Keeping it a parameter
    is what lets this module stay Qt-free and unit-testable."""
    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        log_dir=_log_dir(tmp_path),
        extra_text={"diagnostics.txt": "session diagnostics — 3 warnings"},
    )

    assert result.path is not None
    assert _read_from(result.path, "diagnostics.txt") == (
        "session diagnostics — 3 warnings"
    )


def test_two_bundles_of_the_same_inputs_are_byte_identical(tmp_path: Path) -> None:
    """The archive is evidence. Two bundles of one input set should differ only
    where the inputs differ — which also keeps the operator's username and the
    build hour off an artifact that gets posted in public."""
    logs = _log_dir(tmp_path)
    kwargs = dict(
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        log_dir=logs,
    )
    first = build_bundle(dest_dir=tmp_path / "a", **kwargs)  # type: ignore[arg-type]
    second = build_bundle(dest_dir=tmp_path / "b", **kwargs)  # type: ignore[arg-type]

    assert first.path is not None and second.path is not None
    assert sha256_of(first.path) == sha256_of(second.path)
    assert sha256_of(first.path), "the hash helper returned nothing to compare"


def test_the_manifest_derives_its_allowlist_rather_than_restating_it(
    tmp_path: Path,
) -> None:
    """The manifest's closing paragraph must come from the constants.

    The first version typed the extensions out as prose and was wrong within the
    hour: it named the strict set while the archive also carried this program's own
    screenshots under the widened one, so the manifest denied the presence of files
    it had itself listed two paragraphs above. A document that restates a rule in
    its own words is a second copy of that rule, and the copy is what goes stale.
    """
    runfolder = tmp_path / "run"
    runfolder.mkdir()
    (runfolder / "shot.png").write_bytes(b"screenshot")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="test script run",
        log_dir=_log_dir(tmp_path),
        extra_dirs={"scriptrun": runfolder},
    )

    assert result.path is not None
    manifest = _read_from(result.path, "MANIFEST.txt")
    for suffix in ALLOWED_SUFFIXES:
        assert suffix in manifest, f"{suffix} is allowed but the manifest omits it"
    assert ".png" in manifest, (
        "the archive carries a .png and the manifest's allowlist paragraph does not "
        "mention it — the manifest is describing a rule the bundle did not follow"
    )
    assert "scriptrun/shot.png" in _names_in(result.path)


def test_an_album_folder_image_is_excluded_while_a_run_folder_image_is_not(
    tmp_path: Path,
) -> None:
    """The scoped widening, asserted as a *relation* rather than one side at a time.

    Both halves in one bundle, because that is the only claim that matters: an
    album's `folder.png` is record-label artwork and must stay out, while the run
    folder's screenshot is a picture of our own window and goes in. Testing either
    alone would pass against a global allowlist, which is the bug.
    """
    album = tmp_path / "album"
    album.mkdir()
    (album / "folder.png").write_bytes(b"record label art")
    (album / "rip.log").write_text("ripper log")
    runfolder = tmp_path / "run"
    runfolder.mkdir()
    (runfolder / "dialogdrive.png").write_bytes(b"our own screenshot")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T000000Z",
        app_version="0.6.17",
        outcome="success",
        album_dir=album,
        log_dir=_log_dir(tmp_path),
        extra_dirs={"scriptrun": runfolder},
    )

    assert result.path is not None
    names = _names_in(result.path)
    assert "scriptrun/dialogdrive.png" in names, (
        "our own screenshot was refused — the widening is not reaching extra_dirs"
    )
    assert "album/folder.png" not in names, (
        "an album folder's image entered the bundle — the widened rule has leaked "
        "off the run folder and onto record-label artwork (Critical rule #8)"
    )


# --- The caps and the pruning (0.6.18) --------------------------------------
#
# The per-file cap alone bounds nothing useful: the app log rotates, so a busy
# machine presents `log.txt` plus five `log.txt.N` — six files each permitted
# 16 MiB, all of which the first version held in memory at once, on a machine that
# has just finished a rip. And nothing ever removed an old bundle.


def _big_log_dir(tmp_path: Path, count: int, each_bytes: int) -> Path:
    """A log directory with rotations, each `each_bytes` long."""
    d = tmp_path / "logs"
    d.mkdir()
    (d / "log.txt").write_bytes(b"a" * each_bytes)
    for n in range(1, count):
        (d / f"log.txt.{n}").write_bytes(bytes([0x61 + n]) * each_bytes)
    return d


def test_the_total_budget_is_enforced_and_says_so(tmp_path: Path) -> None:
    """Over-budget files are refused WITH A REASON, never dropped silently.

    A bundle quietly missing the rotation that contains the failure reads exactly
    like a complete one — the failure mode the whole manifest exists against.
    """
    each = MAX_TOTAL_BYTES // 4 + 1024  # four of these overflow the budget
    log_dir = _big_log_dir(tmp_path, count=6, each_bytes=each)

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T010000Z",
        app_version="0.6.18",
        outcome="success",
        log_dir=log_dir,
    )

    assert result.path is not None and not result.error, result.error
    total_in = sum(e.bytes_written for e in result.included)
    assert total_in <= MAX_TOTAL_BYTES, (
        f"{total_in} bytes of payload went in against a {MAX_TOTAL_BYTES} budget"
    )
    budget_refusals = [e for e in result.skipped if "budget" in e.reason]
    assert budget_refusals, (
        "six oversized rotations fitted inside the budget — either the fixture is "
        "not oversized or the cap is not enforced"
    )
    manifest = _read_from(result.path, "MANIFEST.txt")
    for entry in budget_refusals:
        assert entry.name in manifest, (
            f"{entry.name} was dropped but the manifest does not name it"
        )
    assert str(MAX_TOTAL_BYTES) in manifest, (
        "the manifest does not state the cap that changed what it contains"
    )


def test_a_normal_bundle_is_not_touched_by_the_total_budget(tmp_path: Path) -> None:
    """Non-triviality floor: the cap must not be refusing ordinary files.

    Without this, a budget of zero would satisfy the test above perfectly.
    """
    log_dir = _big_log_dir(tmp_path, count=6, each_bytes=4096)

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T020000Z",
        app_version="0.6.18",
        outcome="success",
        log_dir=log_dir,
    )

    assert result.path is not None
    assert len(result.included) == 6, (
        f"an ordinary log directory lost files: {[e.reason for e in result.skipped]}"
    )
    assert not [e for e in result.skipped if "budget" in e.reason]


def test_the_manifest_is_present_even_though_it_is_written_last(
    tmp_path: Path,
) -> None:
    """Streaming moved MANIFEST.txt from the first member to the last.

    Member order does not affect extraction, but "the manifest is in there" is the
    kind of thing a refactor breaks quietly, so it is asserted rather than assumed.
    """
    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260819T030000Z",
        app_version="0.6.18",
        outcome="cancelled",
        log_dir=_log_dir(tmp_path),
    )

    assert result.path is not None
    assert "MANIFEST.txt" in _names_in(result.path)
    assert "cancelled" in _read_from(result.path, "MANIFEST.txt")


def test_building_a_bundle_prunes_the_oldest_ones(tmp_path: Path) -> None:
    """The bundles folder is bounded, and the new bundle survives its own prune."""
    dest = tmp_path / "out"
    dest.mkdir()
    # Older than anything build_bundle will write, and more of them than the cap.
    stale = []
    for n in range(MAX_BUNDLES_KEPT + 5):
        p = dest / f"platterpusbundle2026010{n:04d}z.tar.gz"
        p.write_bytes(b"old")
        import os

        os.utime(p, (1_000_000 + n, 1_000_000 + n))
        stale.append(p)

    result = build_bundle(
        dest_dir=dest,
        stamp="20260819T040000Z",
        app_version="0.6.18",
        outcome="success",
        log_dir=_log_dir(tmp_path),
    )

    assert result.path is not None and result.path.exists(), (
        "the bundle just written was pruned — the one file the user is about to send"
    )
    remaining = sorted(p.name for p in dest.glob("platterpusbundle*.tar.gz"))
    assert len(remaining) == MAX_BUNDLES_KEPT, remaining
    assert result.path.name in remaining
    # Oldest-first: the very oldest must be gone and the newest stale one kept.
    assert not stale[0].exists(), "pruning removed the wrong end of the list"
    assert stale[-1].exists(), "pruning removed a recent bundle"


def test_pruning_never_touches_a_file_it_did_not_write(tmp_path: Path) -> None:
    """The narrowing that matters, because this function deletes files.

    A `*.tar.gz` glob would have been shorter and would delete a user's own
    archives, their renamed keepsake copy of a bundle, and any note beside it.
    """
    dest = tmp_path / "out"
    dest.mkdir()
    bystanders = [
        dest / "my-important-backup.tar.gz",
        dest / "platterpusbundle-with-hyphens.tar.gz",
        dest / "PLATTERPUSBUNDLE20260101Z.tar.gz",
        dest / "notes.txt",
        dest / "platterpusbundle20260101z.tar.gz.bak",
    ]
    for p in bystanders:
        p.write_bytes(b"not ours to delete")
    ours = []
    for n in range(MAX_BUNDLES_KEPT + 3):
        p = dest / f"platterpusbundle2026020{n:04d}z.tar.gz"
        p.write_bytes(b"ours")
        ours.append(p)

    removed = prune_bundles(dest, keep=MAX_BUNDLES_KEPT)

    assert removed, "nothing was pruned, so this proves nothing about what is safe"
    for p in bystanders:
        assert p.exists(), f"pruning deleted {p.name}, which this module never wrote"
    assert all(r in ours for r in removed), removed


def test_pruning_survives_a_missing_directory(tmp_path: Path) -> None:
    """Housekeeping must never be the thing that takes down a rip."""
    assert prune_bundles(tmp_path / "does-not-exist") == []
    assert prune_bundles(tmp_path, keep=0) == []
