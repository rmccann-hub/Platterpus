"""The one-file report bundle: what goes in, what must never, and what it says.

The feature exists because the maintainer had to assemble the upload by hand
(2026-08-19). The tests here are mostly about the two ways such a convenience
goes wrong: it quietly leaves something out, or it quietly puts something in.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from platterpus import evidence_bundle
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


# ==========================================================================
# SEVERAL album folders — the acceptance session's case
# ==========================================================================
#
# An ordinary rip has one album folder. An acceptance session rips the same disc
# several times under different settings, so its bundle has to carry several —
# and the tempting way to do that (pass them through `extra_dirs`) would widen
# their allowlist to admit `.png`, i.e. the record label's cover art, which
# Critical rule #8 forbids leaving the machine. So they get their own parameter
# on the STRICT route.
#
# The hazard these tests exist for is not an error. `tarfile` accepts a duplicate
# member name: it writes both and extraction keeps whichever landed last. Two rips
# of one disc both contain `rip.log`, so without distinct prefixes one album
# silently replaces another inside an archive that still opens and still lists —
# "a silent truncation reads as completeness", in the module whose docstring says
# that.


def _album(root: Path, name: str, *, log_text: str) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "rip.log").write_text(log_text, encoding="utf-8")
    return folder


def test_two_album_folders_do_not_collide_in_the_archive(tmp_path: Path) -> None:
    """The whole reason this parameter exists. Both files must survive."""
    first = _album(tmp_path / "a", "Album", log_text="FIRST RIP")
    second = _album(tmp_path / "b", "Album", log_text="SECOND RIP")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260828T000000Z",
        app_version="0.0.0",
        outcome="success",
        album_dirs=[first, second],
        log_dir=log_dir,
    )
    assert result.ok, result.error

    with tarfile.open(result.path) as tar:
        names = tar.getnames()
        bodies = {
            n: (tar.extractfile(n) or io.BytesIO()).read().decode()
            for n in names
            if n.endswith("rip.log")
        }

    logs = sorted(n for n in names if n.endswith("rip.log"))
    assert len(logs) == 2, f"one album folder overwrote the other: {names}"
    assert len(set(logs)) == 2, f"two members share one archive name: {logs}"
    assert sorted(bodies.values()) == ["FIRST RIP", "SECOND RIP"], (
        "both members exist but one file's CONTENT was lost — the archive names "
        "differ and the payloads do not, which a name-only check would miss"
    )


def test_a_single_album_folder_keeps_the_layout_it_has_always_had(
    tmp_path: Path,
) -> None:
    """No member moves one directory deeper because a different caller passes two.

    An ordinary rip's bundle is an artifact people already have. Changing its
    layout as a side effect of adding a feature is a breaking change nobody asked
    for, so the prefix appears only when there is something to disambiguate.
    """
    only = _album(tmp_path / "a", "Album", log_text="ONLY")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260828T000000Z",
        app_version="0.0.0",
        outcome="success",
        album_dirs=[only],
        log_dir=log_dir,
    )
    assert result.ok, result.error
    with tarfile.open(result.path) as tar:
        names = tar.getnames()
    assert "album/rip.log" in names, f"the single-folder layout changed: {names}"


def test_album_dirs_are_held_to_the_STRICT_allowlist(tmp_path: Path) -> None:
    """Critical rule #8, at the seam this change created.

    The point of a separate parameter is that more-than-one does not buy a
    caller the widened `extra_dirs` rule. Cover art and audio must both be
    refused from an album folder however many were passed.
    """
    first = _album(tmp_path / "a", "One", log_text="X")
    second = _album(tmp_path / "b", "Two", log_text="Y")
    (first / "cover.png").write_bytes(b"")
    (second / "01.flac").write_bytes(b"")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260828T000000Z",
        app_version="0.0.0",
        outcome="success",
        album_dirs=[first, second],
        log_dir=log_dir,
    )
    assert result.ok, result.error
    with tarfile.open(result.path) as tar:
        names = tar.getnames()

    assert not [n for n in names if n.endswith((".png", ".flac"))], (
        f"artwork or audio entered the archive from an album folder: {names}"
    )
    # And the exclusion is NAMED, not silent — the module's third property.
    skipped = " ".join(f"{e.name} {e.reason}" for e in result.skipped)
    assert "cover.png" in skipped and "01.flac" in skipped, (
        f"an exclusion happened without a manifest row saying so: {skipped}"
    )


def test_the_same_folder_passed_twice_is_archived_once(tmp_path: Path) -> None:
    """Otherwise it is read twice, archived under two names, and charged twice
    against the byte budget — pushing a later, real artifact out."""
    only = _album(tmp_path / "a", "Album", log_text="ONE")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260828T000000Z",
        app_version="0.0.0",
        outcome="success",
        album_dir=only,
        album_dirs=[only],
        log_dir=log_dir,
    )
    assert result.ok, result.error
    with tarfile.open(result.path) as tar:
        logs = [n for n in tar.getnames() if n.endswith("rip.log")]
    assert logs == ["album/rip.log"], f"the folder was archived twice: {logs}"


def test_the_manifest_names_every_album_folder_not_a_count(tmp_path: Path) -> None:
    """A manifest saying "3 album folders" is a claim the reader cannot check."""
    first = _album(tmp_path / "a", "First", log_text="X")
    second = _album(tmp_path / "b", "Second", log_text="Y")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260828T000000Z",
        app_version="0.0.0",
        outcome="success",
        album_dirs=[first, second],
        log_dir=log_dir,
    )
    assert result.ok, result.error
    with tarfile.open(result.path) as tar:
        member = tar.extractfile("MANIFEST.txt")
        manifest = (member or io.BytesIO()).read().decode()

    for folder in (first, second):
        assert str(folder) in manifest, (
            f"the manifest does not name {folder} — a reader cannot tell which "
            f"discs the bundle covers:\n{manifest}"
        )


# ==========================================================================
# THE ORDER IS THE BUDGET — rotations must not crowd out the rip evidence
# ==========================================================================
#
# `MAX_TOTAL_BYTES` is spent walking `_collect`'s list, so whatever sorts last is
# what gets refused when the archive fills. The app-log handler is
# `maxBytes=8 MiB, backupCount=10`, so `applog/` can present **88 MiB** against a
# **64 MiB** budget — and it used to be collected in one block ahead of
# everything. A long acceptance run could spend the whole archive on log
# rotations and refuse EVERY rip folder: no rip log, no cue, no report, no
# checksum. Each refusal writes a manifest line, so it was never silent — but a
# reader still receives a file that looks complete and answers nothing.
#
# Found 2026-08-29 by an audit lens asking what the bundle actually contains,
# while a real 6-hour acceptance run was in flight on the maintainer's rig.


def test_log_rotations_do_not_crowd_out_the_rip_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression test, written as the real failure rather than as an
    ordering assertion: fill the budget with rotations and demand the album
    survive. An ordering check alone would pass on a build that ordered
    correctly and still dropped the evidence for some other reason.
    """
    # THE SIZES ARE THE TEST, and the first draft of this got them wrong in a
    # way the revert probe caught: the budget check REFUSES an over-large file
    # and keeps walking, so a few tiny album files simply slipped into the
    # headroom the refused rotations left behind, and the test passed against
    # the broken order. Reproducing the symptom means the rotations must fill
    # the budget to within LESS than one album file — which is exactly the real
    # shape, where 8 MiB rotations exhaust 64 MiB and a 50 KB rip log then has
    # nowhere to go.
    monkeypatch.setattr(evidence_bundle, "MAX_TOTAL_BYTES", 8_000)

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "log.txt").write_text("C" * 12, encoding="utf-8")
    # 4 x 1900 = 7600; with the 12-byte current log that leaves 388 bytes.
    for n in range(1, 6):
        (log_dir / f"log.txt.{n}").write_text("R" * 1_900, encoding="utf-8")

    album = tmp_path / "out" / "Album"
    album.mkdir(parents=True)
    # 500 > 388, so under the old order these do not fit and are refused.
    (album / "disc.log").write_text("L" * 500, encoding="utf-8")
    (album / "disc.cue").write_text("Q" * 500, encoding="utf-8")

    result = build_bundle(
        dest_dir=tmp_path / "dest",
        stamp="20260829T000000Z",
        app_version="0.0.0",
        outcome="acceptance test session",
        album_dirs=[album],
        log_dir=log_dir,
    )
    assert result.ok, result.error

    with tarfile.open(result.path) as tar:
        names = tar.getnames()

    assert "album/disc.log" in names, (
        "the ripper's own log was crowded out of the bundle by app-log "
        f"rotations — this is the whole evidence the run exists to produce: {names}"
    )
    assert "album/disc.cue" in names, f"the cue sheet was crowded out: {names}"
    assert "applog/log.txt" in names, (
        "the CURRENT app log must still come first — it is the artifact that "
        f"exists for every outcome, including runs that produced no album: {names}"
    )
    # Non-triviality: the budget must actually have bitten, or this test proves
    # nothing about ordering — it would pass on a bundle that fitted everything.
    refused = [e for e in result.skipped if "budget" in e.reason]
    assert refused, (
        "nothing was refused for budget, so the pressure this test exists to "
        "create did not happen and the ordering was never exercised"
    )
    assert all(e.name.startswith("applog/log.txt.") for e in refused), (
        "something other than a log rotation was refused for budget; the "
        f"rotations must absorb the shortfall: {[e.name for e in refused]}"
    )


def _member_bytes(archive: Path) -> dict[str, bytes]:
    """Every member's actual payload, for assertions about CONTENT not names."""
    with tarfile.open(archive, "r:gz") as tar:
        return {
            name: (tar.extractfile(name) or io.BytesIO()).read()
            for name in tar.getnames()
        }


# ==========================================================================
# A folder the manifest CLAIMS was archived, and was not
# ==========================================================================
#
# `_collect` skipped an album folder that was not a directory with a bare
# `continue`, while `_album_folder_lines` rendered every path in `album_dirs`
# under a heading saying they were archived. A folder that vanished between
# discovery and archiving — moved by the library-filing step, deleted, unmounted
# — was therefore NAMED as present and ABSENT from the tar, with nothing
# connecting the two. That is this module's own third property ("every omission
# is named") broken by the code that renders the completeness claim.


def test_an_album_folder_that_vanished_is_refused_not_silently_skipped(
    tmp_path: Path,
) -> None:
    """The regression test, written as the real sequence: discovered, then gone.

    The folder is created (so it is a legitimate thing to have been named) and
    then removed before the bundle is built, which is exactly what the
    library-filing step does to a rip folder while a session is still running.
    """
    survivor = _album(tmp_path / "a", "Survivor", log_text="STILL HERE")
    vanished = _album(tmp_path / "b", "Vanished", log_text="MOVED AWAY")
    (vanished / "rip.log").unlink()
    vanished.rmdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260901T000000Z",
        app_version="0.0.0",
        outcome="acceptance test session",
        album_dirs=[survivor, vanished],
        log_dir=log_dir,
    )
    assert result.ok, result.error
    assert result.path is not None

    # FLOOR FIRST. The surviving folder really was archived, so what follows is
    # about the missing one and not about a bundle that collected nothing.
    names = _names_in(result.path)
    assert [n for n in names if n.endswith("rip.log")], (
        f"nothing was archived at all, so this proves nothing: {names}"
    )

    refusals = [e for e in result.skipped if e.source == str(vanished)]
    assert len(refusals) == 1, (
        "the vanished album folder produced no NOT-INCLUDED row — it was skipped "
        f"silently: {[(e.name, e.source) for e in result.skipped]}"
    )
    assert "not there" in refusals[0].reason, refusals[0].reason

    manifest = _read_from(result.path, "MANIFEST.txt")
    assert str(vanished) in manifest, "the folder is not named in the manifest at all"
    # The claim itself, which is the actual defect: the album block must not say
    # this folder was archived. The path is listed AND marked.
    album_block = manifest.split("Raw facts")[0]
    marked = [line for line in album_block.splitlines() if str(vanished) in line]
    assert marked and "NOT ARCHIVED" in marked[0], (
        "the manifest still lists the vanished folder under a heading saying it "
        f"was archived:\n{album_block}"
    )
    # And the folder that WAS archived carries no such mark — otherwise the mark
    # is decoration that says nothing about either folder.
    kept = [line for line in album_block.splitlines() if str(survivor) in line]
    assert kept and "NOT ARCHIVED" not in kept[0], kept


def test_a_requested_extra_directory_that_is_absent_is_named(tmp_path: Path) -> None:
    """The same rule at the other silent `continue` (§5.o — enforce it across the
    codebase, not only where it was learned).

    A caller naming a screenshot folder that never got created has evidence
    missing from the bundle, and used to have no way to tell.
    """
    present = tmp_path / "run"
    present.mkdir()
    (present / "run.log").write_text("ran", encoding="utf-8")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260901T000000Z",
        app_version="0.0.0",
        outcome="test script run",
        log_dir=_log_dir(tmp_path),
        extra_dirs={"scriptrun": present, "screenshots": tmp_path / "never-made"},
    )
    assert result.ok, result.error
    assert result.path is not None
    assert "scriptrun/run.log" in _names_in(result.path), "the floor is missing"

    missing = [e for e in result.skipped if e.source == str(tmp_path / "never-made")]
    assert len(missing) == 1, (
        f"an absent named directory left no trace: {[e.name for e in result.skipped]}"
    )
    assert "never-made" in _read_from(result.path, "MANIFEST.txt")


# ==========================================================================
# Critical rule #8 vs. a NAME test — the symlink, and the bytes
# ==========================================================================
#
# `_is_allowed` was a pure name test (`path.suffix.lower() in permitted`) while
# `_read_bounded` opened the file and read it by CONTENT. So a symlink called
# `notes.log` pointing at `track01.flac` was admitted on the strength of the
# link's own name and its AUDIO BYTES were written into the archive.
#
# An album folder is written by cyanrip and is unlikely to contain a hostile
# symlink, so the reach is small — but Critical rule #8 is absolute about what
# may leave the machine, and a guard that is a name test standing in for a
# content guarantee will be wrong for some reason nobody predicted. The fix is
# two layers: a link is judged by its target's name as well as its own, and every
# file's first bytes are checked against the audio signatures.
#
# Every "audio" file below is a few bytes generated inside `tmp_path`. No real
# track is ever written, and nothing goes anywhere near the repository.


def test_a_symlink_cannot_smuggle_audio_past_the_name_test(tmp_path: Path) -> None:
    """The reproduction, asserted on the archive's BYTES rather than its names.

    Checking that `notes.log` is absent from the listing would pass against a
    build that archived the audio under some other member name. What must be true
    is that the track's payload is in no member at all.
    """
    album = tmp_path / "album"
    album.mkdir()
    payload = b"fLaC\x00\x00\x00\x22PAYLOAD-THAT-MUST-NEVER-LEAVE"
    (album / "track01.flac").write_bytes(payload)
    (album / "rip.log").write_text("track 1 CRC ABCD1234", encoding="utf-8")
    (album / "notes.log").symlink_to(album / "track01.flac")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260901T010000Z",
        app_version="0.0.0",
        outcome="success",
        album_dir=album,
        log_dir=_log_dir(tmp_path),
    )
    assert result.ok, result.error
    assert result.path is not None

    bodies = _member_bytes(result.path)
    # FLOOR: the genuine ripper log did get in, so the absence below is the
    # filter working rather than an empty walk.
    assert any(name.endswith("rip.log") for name in bodies), sorted(bodies)
    assert b"PAYLOAD-THAT-MUST-NEVER-LEAVE" not in b"".join(bodies.values()), (
        "a symlink with an allowed NAME carried audio bytes into the archive — "
        "Critical rule #8"
    )
    refused = [e for e in result.skipped if e.name.endswith("notes.log")]
    assert refused, f"the symlink was dropped without a manifest row: {sorted(bodies)}"
    assert "symbolic link" in refused[0].reason, refused[0].reason
    assert "track01.flac" in refused[0].reason, (
        "the refusal does not name what the link pointed at, so a reader cannot "
        f"tell why it was refused: {refused[0].reason}"
    )


def test_a_symlinked_log_pointing_at_a_text_file_is_still_archived(
    tmp_path: Path,
) -> None:
    """The legitimate case the guard must not break.

    An operator may point `~/.local/share/platterpus/log.txt` at storage
    elsewhere. That link resolves to a `.txt` and must still be collected — a
    guard that refused every symlink would silently empty the log directory of
    the one artifact that exists for every outcome.
    """
    elsewhere = tmp_path / "storage"
    elsewhere.mkdir()
    (elsewhere / "stored.txt").write_text("REAL APP LOG LINE\n", encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.txt").symlink_to(elsewhere / "stored.txt")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260901T020000Z",
        app_version="0.0.0",
        outcome="failed",
        log_dir=logs,
    )
    assert result.ok, result.error
    assert result.path is not None
    assert "applog/log.txt" in _names_in(result.path), (
        "a symlinked app log was refused — the whole log directory would be empty "
        f"on that machine: {[(e.name, e.reason) for e in result.skipped]}"
    )
    assert "REAL APP LOG LINE" in _read_from(result.path, "applog/log.txt")


def test_a_file_whose_bytes_are_audio_is_refused_however_it_is_named(
    tmp_path: Path,
) -> None:
    """The layer that makes "no audio" a claim about CONTENT.

    Resolving a symlink and re-reading its target's name is still a name test.
    This is the check that does not depend on anyone having named the file
    honestly — and it is a denylist deliberately used as the *second* layer, so
    the allowlist above it still fails closed on a format nobody enumerated.
    """
    album = tmp_path / "album"
    album.mkdir()
    (album / "rip.log").write_text("genuine ripper log\n", encoding="utf-8")
    (album / "sneaky.log").write_bytes(b"fLaC\x00\x00\x00\x22SMUGGLED-BYTES")
    (album / "report.json").write_bytes(b"OggS\x00SMUGGLED-BYTES")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20260901T030000Z",
        app_version="0.0.0",
        outcome="success",
        album_dir=album,
        log_dir=_log_dir(tmp_path),
    )
    assert result.ok, result.error
    assert result.path is not None

    bodies = _member_bytes(result.path)
    # FLOOR: ordinary text with an allowed name still goes in. Without this, a
    # sniff that refused everything would pass.
    assert "album/rip.log" in bodies, sorted(bodies)
    assert b"genuine ripper log" in bodies["album/rip.log"]
    assert b"SMUGGLED-BYTES" not in b"".join(bodies.values()), (
        "a file named as text but holding audio bytes entered the archive"
    )
    refused = {e.name: e.reason for e in result.skipped}
    assert "album/sneaky.log" in refused and "FLAC" in refused["album/sneaky.log"]
    assert "album/report.json" in refused and "Ogg" in refused["album/report.json"]
    assert "first bytes" in _read_from(result.path, "MANIFEST.txt")


def test_the_current_log_still_outranks_the_album_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction, and it is not symmetric.

    A run that produced NO album folder is exactly the failure worth sending, so
    the current log keeps its place at the front. Moving the whole `applog/`
    block to the back would have fixed the crowding and broken this.
    """
    monkeypatch.setattr(evidence_bundle, "MAX_TOTAL_BYTES", 200)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "log.txt").write_text("W" * 150, encoding="utf-8")
    album = tmp_path / "out" / "Album"
    album.mkdir(parents=True)
    (album / "disc.log").write_text("Z" * 150, encoding="utf-8")

    result = build_bundle(
        dest_dir=tmp_path / "dest",
        stamp="20260829T000000Z",
        app_version="0.0.0",
        outcome="failed",
        album_dirs=[album],
        log_dir=log_dir,
    )
    assert result.ok, result.error
    with tarfile.open(result.path) as tar:
        names = tar.getnames()
    assert "applog/log.txt" in names, (
        f"the current app log lost its priority — a no-rip failure would now "
        f"send an archive with no log in it: {names}"
    )
