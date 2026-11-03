"""`expect-derived-files`: the MP3, WavPack and WAV files a K section rips.

Review C4 of the owner's 2026-11-03 Full run: K1 to K3 graded the FLAC masters
and never opened a derived file. Each case below is an album folder as a derived
rip leaves it (masters stating their length, derived files built from each
format's layout by `test_derived_metadata`'s builders, and the report's
`encoder_argv`), and each failing case is one planted fault in it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_derived_metadata import build_master, build_mp3, build_wav, build_wavpack

from platterpus.uiscript.derived_grading import grade_derived_files
from platterpus.uiscript.tag_grading import ExpectedTags

SAMPLES = 132300
EXPECTED = ExpectedTags(
    album="B: c",
    album_artist="A",
    tracks={1: ("Roxanne", "A"), 2: ("Can’t Stand", "A")},
)
_ARGV = {
    "mp3": ["ffmpeg", "-c:a", "libmp3lame", "-q:a", "2", "-f", "mp3", "x"],
    "wavpack": ["ffmpeg", "-c:a", "wavpack", "-f", "wv", "x"],
    "wav": ["ffmpeg", "-c:a", "pcm_s16le", "-f", "wav", "x"],
}


def _tags(number: int) -> dict[str, str]:
    title, artist = EXPECTED.tracks[number]
    return {
        "TITLE": title,
        "ARTIST": artist,
        "ALBUM": EXPECTED.album,
        "ALBUMARTIST": EXPECTED.album_artist,
        "TRACKNUMBER": f"{number}/2",
    }


def derived_album(
    folder: Path, fmt: str, *, pictures: int = 1, release: str = "rel-1"
) -> dict[str, Any]:
    """Two masters and their derived files, and the report that names them."""
    folder.mkdir(parents=True, exist_ok=True)
    tracks = []
    for number in (1, 2):
        stem = f"{number:02d} - Track"
        build_master(folder / f"{stem}.flac", SAMPLES)
        if fmt == "mp3":
            build_mp3(folder / f"{stem}.mp3", _tags(number), SAMPLES, pictures=pictures)
        elif fmt == "wavpack":
            build_wavpack(folder / f"{stem}.wv", _tags(number), SAMPLES)
        else:
            build_wav(
                folder / f"{stem}.wav", SAMPLES, {b"INAM": _tags(number)["TITLE"]}
            )
        tracks.append({"number": number, "filename": f"{stem}.flac"})
    return {
        "tracks": tracks,
        "disc": {"musicbrainz_release_id": release},
        "verification": {"transcode": {"encoder_argv": list(_ARGV[fmt])}},
    }


def _grade(report: dict[str, Any], folder: Path, fmt: str, **kw: Any) -> Any:
    quality = 2 if fmt == "mp3" else None
    return grade_derived_files(report, folder, fmt, EXPECTED, "embed", quality, **kw)


@pytest.mark.parametrize("fmt", ["mp3", "wavpack", "wav"])
def test_a_derived_album_passes(tmp_path: Path, fmt: str) -> None:
    report = derived_album(tmp_path, fmt, pictures=1)
    grade = _grade(report, tmp_path, fmt)
    assert grade.passed, grade.detail
    if fmt == "mp3":
        assert "-q:a 2" in grade.detail and "cover embedded" in grade.detail


def test_an_mp3_encoded_at_another_quality_fails(tmp_path: Path) -> None:
    """`mp3_vbr_quality 2` reaching the encoder, proven from what ran."""
    report = derived_album(tmp_path, "mp3")
    report["verification"]["transcode"]["encoder_argv"][4] = "0"
    grade = _grade(report, tmp_path, "mp3")
    assert not grade.passed and "-q:a '0'" in grade.detail


def test_an_mp3_without_the_cover_the_setting_embeds_fails(tmp_path: Path) -> None:
    grade = _grade(derived_album(tmp_path, "mp3", pictures=0), tmp_path, "mp3")
    assert not grade.passed and "a cover owed" in grade.detail


@pytest.mark.parametrize("fmt", ["mp3", "wavpack"])
def test_a_stripped_tag_fails(tmp_path: Path, fmt: str) -> None:
    report = derived_album(tmp_path, fmt)
    stem = tmp_path / "02 - Track"
    tags = {k: v for k, v in _tags(2).items() if k != "ALBUMARTIST"}
    if fmt == "mp3":
        build_mp3(stem.with_suffix(".mp3"), tags, SAMPLES, pictures=1)
    else:
        build_wavpack(stem.with_suffix(".wv"), tags, SAMPLES)
    grade = _grade(report, tmp_path, fmt)
    assert not grade.passed and "track 2: ALBUMARTIST" in grade.detail


@pytest.mark.parametrize(
    ("fmt", "ext"), [("mp3", "mp3"), ("wavpack", "wv"), ("wav", "wav")]
)
def test_a_truncated_file_fails(tmp_path: Path, fmt: str, ext: str) -> None:
    report = derived_album(tmp_path, fmt)
    path = tmp_path / f"01 - Track.{ext}"
    data = path.read_bytes()
    path.write_bytes(data[: len(data) * 2 // 3])
    grade = _grade(report, tmp_path, fmt)
    assert not grade.passed and "track 1" in grade.detail


def test_the_wrong_codec_and_a_missing_file_fail(tmp_path: Path) -> None:
    report = derived_album(tmp_path, "wavpack")
    report["verification"]["transcode"]["encoder_argv"][2] = "pcm_s16le"
    (tmp_path / "02 - Track.wv").unlink()
    grade = _grade(report, tmp_path, "wavpack")
    assert not grade.passed
    assert "-c:a 'pcm_s16le'" in grade.detail and "missing" in grade.detail


def test_what_the_record_cannot_settle_is_not_determined(tmp_path: Path) -> None:
    """No encoder argv (a report before v42): never a pass."""
    report = derived_album(tmp_path, "mp3")
    del report["verification"]["transcode"]["encoder_argv"]
    grade = _grade(report, tmp_path, "mp3")
    assert not grade.passed and grade.blocked
    assert grade.detail.startswith("not determined")


def test_a_format_that_is_not_derived_is_refused(tmp_path: Path) -> None:
    assert not _grade(derived_album(tmp_path, "wav"), tmp_path, "flac").passed


# --- through the real runner ----------------------------------------------------


def _window_over(folder: Path, report: dict[str, Any]) -> Any:
    """A window whose last rip wrote `folder`, its report settled, its tags kept."""
    from test_uiscript_rip_verbs import _window_after_a_rip_into

    from platterpus.adapters.rip_backend import RipMetadata, TrackTag
    from platterpus.config import Config
    from platterpus.ui.post_rip_record import PostRipRecord

    report.update(
        outcome={"status": "success"},
        verification={**report["verification"], "gates": {"derived": "ran — passed"}},
        issues=[],
    )
    (folder / "rip.platterpus.json").write_text(json.dumps(report), "utf-8")
    log_file = folder / "rip.log"
    log_file.write_text("log", "utf-8")
    win = _window_after_a_rip_into(log_file)
    win._config = Config(cover_art="embed")
    record = PostRipRecord(generation=1, log_file=log_file)
    record.metadata = RipMetadata(
        album_artist=EXPECTED.album_artist,
        album_title=EXPECTED.album,
        tracks=tuple(
            TrackTag(number=n, title=t, artist=a)
            for n, (t, a) in EXPECTED.tracks.items()
        ),
    )
    win._post_rip_records = {1: record}
    return win


def test_the_verb_grades_the_derived_files_and_names_its_quality(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    from test_uiscript_rip_verbs import _step_outcome

    from platterpus.uiscript.report import Outcome
    from platterpus.uiscript.runner import ScriptRunner

    win = _window_over(tmp_path, derived_album(tmp_path, "mp3"))
    ok = _step_outcome(
        ScriptRunner(win), qapp, process_until, "expect-derived-files mp3 2"
    )
    assert ok.outcome is Outcome.PASS, ok.detail
    wrong = _step_outcome(
        ScriptRunner(win), qapp, process_until, "expect-derived-files mp3 5"
    )
    assert wrong.outcome is Outcome.FAIL and "-q:a" in wrong.detail
    unnamed = _step_outcome(
        ScriptRunner(win), qapp, process_until, "expect-derived-files mp3"
    )
    assert unnamed.outcome is Outcome.ERROR
