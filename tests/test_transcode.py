# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the post-rip FLAC→MP3/WavPack/WAV transcode adapter.

The `ffmpeg` subprocess is injected (a fake runner), so these run with no real
binary. Contract (mirrors flac_recompress): never raise; distinguish "couldn't
run at all" (error) from "a file failed" (failures); the source FLAC is always
kept; the output is written atomically (sibling temp → os.replace).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from platterpus.adapters import transcode
from platterpus.adapters.transcode import (
    SUPPORTED_FORMATS,
    TranscodeResult,
    transcode_files,
)


def _make_flac(path: Path, content: bytes = b"FLACdata") -> Path:
    path.write_bytes(content)
    return path


def test_mp3_transcode_writes_sibling_and_keeps_flac(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01 - A.flac")
    b = _make_flac(tmp_path / "02 - B.flac")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"mp3data")  # argv[-1] is the temp output
        return 0

    result = transcode_files(
        [a, b], fmt="mp3", mp3_vbr_quality=0, binary="ffmpeg", runner=runner
    )

    assert result.ok and result.ran
    assert result.transcoded == 2
    assert result.failures == ()
    # Sibling .mp3 written; the FLAC master is untouched; no temp left behind.
    assert (tmp_path / "01 - A.mp3").read_bytes() == b"mp3data"
    assert (tmp_path / "02 - B.mp3").read_bytes() == b"mp3data"
    assert a.read_bytes() == b"FLACdata"  # FLAC kept
    assert not (tmp_path / "01 - A.mp3.transcode.tmp").exists()
    # The MP3 argv uses libmp3lame VBR and carries metadata + cover art.
    argv = seen[0]
    assert "libmp3lame" in argv
    assert argv[argv.index("-q:a") + 1] == "0"  # VBR quality passthrough
    assert "-map_metadata" in argv and "-c:v" in argv  # tags + cover
    assert argv[-1].endswith(".transcode.tmp")  # writes temp, not final name
    assert argv[argv.index("-i") + 1] == str(a)  # input is the FLAC


def test_mp3_vbr_quality_is_passed_through(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"x")
        return 0

    transcode_files([a], fmt="mp3", mp3_vbr_quality=2, runner=runner)
    assert seen[0][seen[0].index("-q:a") + 1] == "2"


def test_wav_transcode_uses_pcm_and_no_metadata(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"RIFF....WAVE")
        return 0

    result = transcode_files([a], fmt="wav", runner=runner)

    assert result.ok
    assert (tmp_path / "01.wav").read_bytes() == b"RIFF....WAVE"
    argv = seen[0]
    assert "pcm_s16le" in argv  # CD-format PCM
    # Audio-only: explicitly excludes any embedded cover (RIFF can't hold it),
    # so a FLAC with art still transcodes cleanly.
    assert argv[argv.index("-map") + 1] == "0:a"
    assert "-map_metadata" not in argv  # WAV/RIFF can't carry the tags
    assert "libmp3lame" not in argv


def test_wavpack_writes_wv_sibling_lossless_with_tags(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01 - A.flac")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"wvpk....")
        return 0

    result = transcode_files([a], fmt="wavpack", runner=runner)

    assert result.ok
    # The extension is ".wv", NOT ".wavpack" — derived from the format→ext map.
    assert (tmp_path / "01 - A.wv").read_bytes() == b"wvpk...."
    assert not (tmp_path / "01 - A.wavpack").exists()
    assert a.read_bytes() == b"FLACdata"  # FLAC master kept
    argv = seen[0]
    assert argv[argv.index("-c:a") + 1] == "wavpack"  # the lossless encoder
    assert "libmp3lame" not in argv and "pcm_s16le" not in argv
    # The MUXER is `wv`, not `wavpack` (that's the encoder). Passing the wrong
    # `-f` makes the real ffmpeg abort and write nothing — a bug the stubbed
    # runner can't catch, so pin the exact format string here.
    assert argv[argv.index("-f") + 1] == "wv"
    # Text tags carry over (APEv2), but the cover stream is dropped: ffmpeg's
    # WavPack muxer only accepts a single stream, so we map audio only.
    assert "-map_metadata" in argv
    assert argv[argv.index("-map") + 1] == "0:a"
    assert "-c:v" not in argv  # no attached-picture copy (muxer rejects it)


def test_supported_formats_are_the_transcode_targets() -> None:
    # FLAC is the native rip format (no transcode); these are the derived ones.
    assert SUPPORTED_FORMATS == {"mp3", "wavpack", "wav"}
    assert "flac" not in SUPPORTED_FORMATS


def test_custom_binary_path_is_used(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"x")
        return 0

    transcode_files([a], fmt="mp3", binary="/opt/ffmpeg/bin/ffmpeg", runner=runner)
    assert seen[0][0] == "/opt/ffmpeg/bin/ffmpeg"


def test_unsupported_format_is_a_clean_noop(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")
    calls: list[list[str]] = []

    # "flac" (and anything we don't transcode) → nothing run, no error.
    result = transcode_files(
        [a], fmt="flac", runner=lambda argv: calls.append(argv) or 0
    )
    assert result.ran and result.ok
    assert result.transcoded == 0
    assert calls == []  # runner never invoked


def test_nonzero_rc_leaves_no_output_and_marks_failure(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")

    def runner(argv: list[str]) -> int:
        Path(argv[-1]).write_bytes(b"partial")  # ffmpeg wrote then failed
        return 1

    result = transcode_files([a], fmt="mp3", runner=runner)

    assert result.ran and not result.ok
    assert result.transcoded == 0
    assert result.failures == (a,)
    assert not (tmp_path / "01.mp3").exists()  # no half-written output
    assert not (tmp_path / "01.mp3.transcode.tmp").exists()  # temp cleaned
    assert a.read_bytes() == b"FLACdata"  # FLAC untouched


def test_missing_temp_output_is_a_failure(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")
    # Runner claims success but never wrote the temp.
    result = transcode_files([a], fmt="mp3", runner=lambda argv: 0)
    assert result.failures == (a,)
    assert not (tmp_path / "01.mp3").exists()


def test_missing_binary_is_an_error_not_a_failure(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")

    def runner(argv: list[str]) -> int:
        raise FileNotFoundError("ffmpeg")

    result = transcode_files([a], fmt="mp3", runner=runner)
    assert not result.ran
    assert not result.ok
    assert result.failures == ()
    assert "not found" in result.error


def test_timeout_marks_file_failed_and_continues(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")
    b = _make_flac(tmp_path / "02.flac")

    def runner(argv: list[str]) -> int:
        if argv[argv.index("-i") + 1].endswith("01.flac"):
            Path(argv[-1]).write_bytes(b"partial")
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=300)
        Path(argv[-1]).write_bytes(b"ok")
        return 0

    result = transcode_files([a, b], fmt="mp3", runner=runner)

    assert result.ran  # a timeout is a per-file failure, not a hard abort
    assert result.transcoded == 1  # the second file still succeeded
    assert result.failures == (a,)
    assert not (tmp_path / "01.mp3.transcode.tmp").exists()  # partial cleaned


def test_oserror_aborts_with_error(tmp_path: Path) -> None:
    a = _make_flac(tmp_path / "01.flac")

    def runner(argv: list[str]) -> int:
        raise OSError("permission denied")

    result = transcode_files([a], fmt="mp3", runner=runner)
    assert not result.ran
    assert "could not run" in result.error


def test_failed_atomic_move_marks_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = _make_flac(tmp_path / "01.flac")

    def runner(argv: list[str]) -> int:
        Path(argv[-1]).write_bytes(b"ok")
        return 0

    def boom(_src: object, _dst: object) -> None:
        raise OSError("EXDEV")

    monkeypatch.setattr(transcode.os, "replace", boom)

    result = transcode_files([a], fmt="mp3", runner=runner)
    assert result.ran and not result.ok
    assert result.failures == (a,)
    assert not (tmp_path / "01.mp3.transcode.tmp").exists()  # temp cleaned up


def test_empty_input_is_a_clean_noop() -> None:
    result = transcode_files([], fmt="mp3", runner=lambda argv: 0)
    assert result.ran and result.ok
    assert result.transcoded == 0


def test_result_properties() -> None:
    assert TranscodeResult().ran and TranscodeResult().ok
    assert TranscodeResult(transcoded=3).ok
    assert not TranscodeResult(failures=(Path("x"),)).ok
    assert TranscodeResult(failures=(Path("x"),)).ran  # ran, just had a failure
    assert not TranscodeResult(error="boom").ran
    assert not TranscodeResult(error="boom").ok


# --- Real-binary integration (the stubbed runner can't catch a bad ffmpeg
# argv — e.g. the wrong `-f` muxer name). Skipped when ffmpeg/flac are absent;
# runs locally and on any CI image that has them. Self-generated audio only
# (CLAUDE.md Rule #8). Regression for the `-f wavpack` (should be `-f wv`) bug.

import hashlib  # noqa: E402
import shutil  # noqa: E402

_HAVE_FFMPEG = shutil.which("ffmpeg") is not None
_HAVE_FLAC = shutil.which("flac") is not None
_real_only = pytest.mark.skipif(
    not (_HAVE_FFMPEG and _HAVE_FLAC), reason="needs real ffmpeg + flac"
)


def _pcm_md5(path: Path) -> str:
    """MD5 of the decoded 16-bit PCM (format-independent lossless fingerprint)."""
    out = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a",
            "-f",
            "s16le",
            "-c:a",
            "pcm_s16le",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.md5(out).hexdigest()


def _make_real_flac(dir_: Path) -> Path:
    """A real, tagged FLAC with an embedded cover, generated from a sine wave."""
    wav = dir_ / "s.wav"
    png = dir_ / "c.png"
    flac = dir_ / "01 - Song.flac"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(wav),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x32:d=1",
            "-frames:v",
            "1",
            str(png),
        ],
        check=True,
    )
    subprocess.run(
        [
            "flac",
            "--silent",
            "-f",
            "-o",
            str(flac),
            "-T",
            "TITLE=Song",
            "-T",
            "ARTIST=Artist",
            "-T",
            "ALBUM=Album",
            f"--picture=3||||{png}",
            str(wav),
        ],
        check=True,
    )
    return flac


@_real_only
@pytest.mark.parametrize("fmt,ext", [("wavpack", "wv"), ("wav", "wav")])
def test_real_lossless_transcode_is_bit_identical(
    tmp_path: Path, fmt: str, ext: str
) -> None:
    """The lossless targets really decode back to the FLAC's exact PCM, through
    the SHIPPED adapter + real ffmpeg (no stub). Catches a wrong codec/muxer."""
    flac = _make_real_flac(tmp_path)
    src_md5 = _pcm_md5(flac)

    result = transcode_files([flac], fmt=fmt)

    out = tmp_path / f"01 - Song.{ext}"
    assert result.ok, f"{fmt} transcode failed: {result}"
    assert out.exists(), f"{fmt} wrote no output"
    assert flac.exists()  # FLAC master kept
    assert _pcm_md5(out) == src_md5  # provably lossless


@_real_only
def test_real_mp3_transcode_carries_tags_and_cover(tmp_path: Path) -> None:
    """MP3 (lossy) really carries tags + an embedded cover, through the shipped
    adapter + real ffmpeg."""
    flac = _make_real_flac(tmp_path)

    result = transcode_files([flac], fmt="mp3")

    out = tmp_path / "01 - Song.mp3"
    assert result.ok and out.exists()
    tags = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags=title,artist,album",
            "-of",
            "default=nw=1",
            str(out),
        ],
        capture_output=True,
        text=True,
    ).stdout
    assert "Song" in tags and "Artist" in tags
    cover = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "default=nw=1",
            str(out),
        ],
        capture_output=True,
        text=True,
    ).stdout
    assert "video" in cover  # the embedded cover (APIC) is present
