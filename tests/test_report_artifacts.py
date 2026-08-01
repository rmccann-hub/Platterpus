"""The JSON report has to be the ONLY file worth uploading (schema v12).

The maintainer's instruction after a hardware round in which every diagnosis
began by asking for a second file: *"just assume I can only upload the json
file, put all [the tests] in there that you need"* (2026-08-01). That is a
testable property, and these tests are it.

Two things had to change for it to be true:

* the three companion files beside the report — cyanrip's ``.log``, our
  EAC-layout render, the ``.cue`` — are embedded verbatim; and
* the report finally *states* how many tracks the disc had, instead of leaving
  ``len(tracks)`` as its only count.

Both gaps were found the same way: by trying to diagnose a real rip from the
real upload and running out of information.
"""

from __future__ import annotations

import json
from pathlib import Path

from platterpus.parsers.rip_log import RipLog, TrackResult
from platterpus.report_artifacts import (
    EMBEDDABLE_SUFFIXES,
    MAX_ARTIFACT_BYTES,
    build_artifact,
    build_artifacts,
)
from platterpus.rip_report import build_report, report_to_json

# --- one artifact -----------------------------------------------------------


def test_an_embedded_artifact_carries_its_text_size_and_digest(tmp_path: Path) -> None:
    f = tmp_path / "Album.log"
    f.write_text("cyanrip 0.9.3\nTrack 1 ripped and encoded successfully!\n")
    entry = build_artifact(f)
    assert entry["exists"] is True
    assert "Track 1 ripped" in entry["text"]
    assert entry["bytes"] == f.stat().st_size
    assert entry["truncated"] is False
    assert len(entry["sha256"]) == 64


def test_the_digest_is_of_the_bytes_on_disk_not_the_truncated_text(
    tmp_path: Path,
) -> None:
    """A digest of the shortened text would be a digest of something no file
    ever contained — worse than no digest, because it looks checkable."""
    import hashlib

    f = tmp_path / "huge.log"
    data = b"x" * (MAX_ARTIFACT_BYTES + 5000)
    f.write_bytes(data)
    entry = build_artifact(f)
    assert entry["truncated"] is True
    assert len(entry["text"]) == MAX_ARTIFACT_BYTES, "text is capped"
    assert entry["bytes"] == len(data), "size is the REAL size, not the capped one"
    assert entry["sha256"] == hashlib.sha256(data).hexdigest()


def test_truncation_keeps_the_head_because_that_is_where_the_facts_are(
    tmp_path: Path,
) -> None:
    """A rip log's header carries the drive, offset, paranoia level and disc
    identity. Losing those costs more than losing the last few tracks."""
    f = tmp_path / "huge.log"
    f.write_bytes(b"HEADER: offset +667\n" + b"y" * (MAX_ARTIFACT_BYTES + 100))
    assert build_artifact(f)["text"].startswith("HEADER: offset +667")


def test_an_absent_file_says_so_rather_than_vanishing(tmp_path: Path) -> None:
    """ "cyanrip wrote no cue" and "we didn't look for one" are different
    findings, and an omitted key cannot tell them apart."""
    entry = build_artifact(tmp_path / "nope.cue")
    assert entry["exists"] is False
    assert entry["path"] == str(tmp_path / "nope.cue"), "where we looked is the point"
    assert "error" in entry


def test_an_empty_file_is_present_and_zero_not_absent(tmp_path: Path) -> None:
    """The real one: a cancelled rip left a 0-byte .cue on the rig (2026-08-01).
    That is invisible in a summary and obvious in a byte count — but only if an
    empty file is reported as *present and empty*, not folded in with missing.
    """
    f = tmp_path / "Album.cue"
    f.write_bytes(b"")
    entry = build_artifact(f)
    assert entry["exists"] is True
    assert entry["bytes"] == 0
    assert entry["text"] == ""
    assert "error" not in entry


def test_a_bad_byte_costs_one_character_not_the_whole_artifact(tmp_path: Path) -> None:
    f = tmp_path / "Album.log"
    f.write_bytes(b"cyanrip \xff\x80 0.9.3")
    assert "cyanrip" in build_artifact(f)["text"]


def test_no_path_at_all_is_still_a_well_formed_entry() -> None:
    entry = build_artifact(None)
    assert entry == {"path": None, "exists": False}


# --- critical rule #8: never, under any circumstances, audio ----------------


def test_an_audio_path_is_refused_and_the_refusal_is_recorded(tmp_path: Path) -> None:
    """Rule #8 is "no copyrighted media, ever, not even temporarily", and a JSON
    report is something the user is explicitly asked to upload. "The caller
    passes the right path" is not a guarantee, so the embedder itself refuses —
    loudly, in the artifact, rather than by raising inside a rip's finish path.
    """
    f = tmp_path / "01 - Roxanne.flac"
    f.write_bytes(b"fLaC\x00\x00\x00\x22")
    entry = build_artifact(f)
    assert entry["exists"] is False, "an audio file must never read as embedded"
    assert "text" not in entry, "not one byte of it"
    assert "refusing to embed" in entry["error"]


def test_the_allowlist_admits_no_audio_extension() -> None:
    """A floor with teeth: the guard is an allowlist, so this checks the list
    itself rather than re-testing one rejection. Every extension rule #8 names
    must be absent — if someone widens the list, this is what stops them.
    """
    forbidden = {
        ".flac",
        ".wav",
        ".mp3",
        ".m4a",
        ".aac",
        ".ogg",
        ".opus",
        ".wv",
        ".ape",
        ".aiff",
        ".dsf",
    }
    assert not (EMBEDDABLE_SUFFIXES & forbidden)
    assert len(EMBEDDABLE_SUFFIXES) >= 3, "an empty allowlist would pass vacuously"


# --- the block, and the report it lands in ----------------------------------


def test_the_block_names_all_three_companions_even_when_none_exist(
    tmp_path: Path,
) -> None:
    block = build_artifacts(
        rip_log=tmp_path / "a.log", eac_log=tmp_path / "b.log", cue=tmp_path / "a.cue"
    )
    assert set(block) == {"note", "rip_log", "eac_log", "cue"}
    assert all(block[k]["exists"] is False for k in ("rip_log", "eac_log", "cue"))


def test_one_upload_carries_the_eac_log_that_contradicted_it(tmp_path: Path) -> None:
    """The end-to-end property. The clean-sweep bug (an EAC log claiming "All
    tracks accurately ripped" above its own "2 of 14" banner) was found by
    reading a file that the JSON did not contain. Now it does, so the same find
    is possible from the single upload.
    """
    rip = tmp_path / "Album.log"
    rip.write_text("cyanrip 0.9.3\n")
    eac = tmp_path / "Album (EAC-compatible).log"
    eac.write_text("*** INCOMPLETE RIP (cancelled) — 2 of 14 disc tracks. ***\n")
    cue = tmp_path / "Album.cue"
    cue.write_text('FILE "01.flac" WAVE\n')

    report = build_report(
        RipLog(tracks=(TrackResult(number=1), TrackResult(number=2))),
        disc_track_total=14,
        artifacts=build_artifacts(rip_log=rip, eac_log=eac, cue=cue),
    )
    round_tripped = json.loads(report_to_json(report))

    assert "INCOMPLETE RIP" in round_tripped["artifacts"]["eac_log"]["text"]
    assert "cyanrip 0.9.3" in round_tripped["artifacts"]["rip_log"]["text"]
    assert "01.flac" in round_tripped["artifacts"]["cue"]["text"]


# --- the denominator, recorded rather than merely used ----------------------


def test_the_report_states_the_disc_track_count_as_a_number() -> None:
    """`disc_track_total` reached the builder only to feed the verdict, so the
    JSON's only track count was `len(tracks)` — the log's own list, which a
    cancel shrinks. A reader had to parse English out of `verdict.message` to
    learn that a 2-track report described a 14-track disc.
    """
    report = build_report(
        RipLog(tracks=(TrackResult(number=1), TrackResult(number=2))),
        disc_track_total=14,
        outcome={"status": "cancelled"},
    )
    assert report["completeness"]["tracks_expected"] == 14
    assert report["completeness"]["tracks_in_report"] == 2
    assert report["completeness"]["complete"] is False


def test_a_complete_rip_records_itself_complete() -> None:
    report = build_report(
        RipLog(tracks=tuple(TrackResult(number=n) for n in range(1, 15))),
        disc_track_total=14,
        outcome={"status": "success"},
    )
    assert report["completeness"]["complete"] is True


def test_an_unknown_denominator_is_null_not_a_claim_of_completeness() -> None:
    """Tri-state on purpose. An in-progress write, or a log parsed offline by
    the `--compare` CLI, genuinely does not know the disc's count — and
    defaulting that to True is precisely the bug this block exists to prevent.
    """
    report = build_report(RipLog(tracks=(TrackResult(number=1),)))
    assert report["completeness"]["tracks_expected"] is None
    assert report["completeness"]["complete"] is None
    assert report["completeness"]["tracks_in_report"] == 1
