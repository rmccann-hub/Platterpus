# SPDX-License-Identifier: GPL-3.0-only
"""A derived MP3's ReplayGain is measured on the MP3, never copied from the FLAC.

The defect (TASKS.md, "A derived MP3 carries the FLAC's `REPLAYGAIN_*` tags"):
``-map_metadata 0`` copied cyanrip's figures, measured before the lossy encode, into
the MP3. These tests hold the fix: the encode drops them, the MP3 is measured, and
the tags written are the MP3's, in cyanrip's own format.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import rip_report
from platterpus.adapters import mp3_replaygain
from platterpus.adapters.mp3_replaygain import (
    DROPPED_TAGS,
    Loudness,
    album_tags,
    apply,
    parse_summary,
    track_tags,
)
from platterpus.adapters.tool_run import ToolRun
from platterpus.adapters.transcode import transcode_files

# The shape ffmpeg 6.1's ebur128 prints (measured 2026-10-21 on a 3 s sine MP3).
_SUMMARY = """\
[Parsed_ebur128_0 @ 0x55f5ce44c380] Summary:

  Integrated loudness:
    I:         -21.8 LUFS
    Threshold: -31.8 LUFS

  Loudness range:
    LRA:        20.0 LU
    Threshold: -41.8 LUFS
    LRA low:   -41.8 LUFS
    LRA high:  -21.8 LUFS

  True peak:
    Peak:      -21.1 dBFS
"""


def _summary(i: float, lra: float, peak: str) -> str:
    return (
        "Summary:\n\n  Integrated loudness:\n"
        f"    I:         {i:.1f} LUFS\n    Threshold: -31.8 LUFS\n\n"
        f"  Loudness range:\n    LRA:        {lra:.1f} LU\n\n"
        f"  True peak:\n    Peak:      {peak} dBFS\n"
    )


# --- parsing ------------------------------------------------------------------


def test_parses_ffmpegs_summary() -> None:
    assert parse_summary(_SUMMARY) == Loudness(-21.8, 20.0, -21.1)


def test_digital_silence_has_a_minus_infinite_peak() -> None:
    parsed = parse_summary(_summary(-70.0, 0.0, "-inf"))
    assert parsed is not None and parsed.true_peak_dbfs == -math.inf
    assert track_tags(parsed)["REPLAYGAIN_TRACK_PEAK"] == "0.000000"


def test_reads_the_last_summary_only() -> None:
    text = _summary(-10.0, 1.0, "-1.0") + "\n" + _summary(-20.0, 2.0, "-2.0")
    assert parse_summary(text) == Loudness(-20.0, 2.0, -2.0)


@pytest.mark.parametrize(
    "text",
    ["", "no summary here", "Summary:\n    I: -21.8 LUFS\n", "I: -1 LUFS\nLRA: 1 LU"],
)
def test_an_incomplete_summary_is_no_measurement(text: str) -> None:
    assert parse_summary(text) is None


@given(st.text())
def test_parse_summary_never_raises(text: str) -> None:
    parse_summary(text)


@given(st.text(alphabet="Summary:ILRAPeakUFSdB-0123456789.inf \n", max_size=400))
def test_parse_summary_never_raises_on_near_misses(text: str) -> None:
    parse_summary(text)


# --- the tags, in cyanrip's format ---------------------------------------------


def test_track_tags_follow_cyanrips_formulae() -> None:
    """``cyanrip@eca33dc:src/cyanrip_main.c:539-557``: gain = -18 - I, two decimals
    and " dB"; peak is the linear true peak to six decimals; reference -18 LUFS."""
    tags = track_tags(Loudness(-21.8, 20.0, -21.1))
    assert tags == {
        "REPLAYGAIN_TRACK_GAIN": "3.80 dB",
        "REPLAYGAIN_TRACK_RANGE": "20.00 dB",
        "REPLAYGAIN_TRACK_PEAK": f"{10 ** (-21.1 / 20):.6f}",
        "REPLAYGAIN_REFERENCE_LOUDNESS": "-18.00 LUFS",
    }
    assert not any(key.startswith("R128_") for key in tags)


def test_album_tags_follow_cyanrips_formulae() -> None:
    tags = album_tags(Loudness(-9.5, 6.9, 0.1))
    assert tags["REPLAYGAIN_ALBUM_GAIN"] == "-8.50 dB"
    assert tags["REPLAYGAIN_ALBUM_RANGE"] == "6.90 dB"
    assert tags["REPLAYGAIN_ALBUM_PEAK"] == f"{10 ** (0.1 / 20):.6f}"


def test_every_loudness_tag_cyanrip_writes_is_dropped() -> None:
    """The nine keys ``cyanrip_main.c:539-580`` sets. A tag left off this list would
    carry the FLAC's figure into the MP3 again."""
    assert set(DROPPED_TAGS) == {
        f"REPLAYGAIN_{scope}_{kind}"
        for scope in ("TRACK", "ALBUM")
        for kind in ("GAIN", "PEAK", "RANGE")
    } | {"REPLAYGAIN_REFERENCE_LOUDNESS", "R128_TRACK_GAIN", "R128_ALBUM_GAIN"}


# --- the steps, with a stand-in ffmpeg -----------------------------------------


class _FakeFfmpeg:
    """Answers a measurement with a summary and writes a retag's output file.

    Unlike real ffmpeg it measures nothing: ``loudness`` maps the joined input
    names to the summary to print, so a test states what each file "sounds" like."""

    def __init__(self, loudness: dict[str, str]) -> None:
        self.loudness = loudness
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> ToolRun:
        self.calls.append(argv)
        inputs = [argv[i + 1] for i, a in enumerate(argv) if a == "-i"]
        if "null" in argv:
            key = "+".join(Path(p).name for p in inputs)
            if key not in self.loudness:
                return ToolRun(exit_code=1, output="decode error", argv=tuple(argv))
            return ToolRun(exit_code=0, output=self.loudness[key], argv=tuple(argv))
        Path(argv[-1]).write_bytes(Path(inputs[0]).read_bytes() + b"+tags")
        return ToolRun(exit_code=0, output="", argv=tuple(argv))

    def retags(self) -> list[list[str]]:
        return [argv for argv in self.calls if "null" not in argv]


def _metadata(argv: list[str]) -> dict[str, str]:
    pairs = [argv[i + 1] for i, a in enumerate(argv) if a == "-metadata"]
    return dict(pair.split("=", 1) for pair in pairs)


def _mp3s(tmp_path: Path, n: int) -> list[Path]:
    paths = [tmp_path / f"{i:02d}.mp3" for i in range(1, n + 1)]
    for path in paths:
        path.write_bytes(b"mp3")
    return paths


def test_each_mp3_gets_its_own_track_figures_and_the_albums(tmp_path: Path) -> None:
    a, b = _mp3s(tmp_path, 2)
    fake = _FakeFfmpeg(
        {
            "01.mp3": _summary(-12.0, 5.0, "-0.5"),
            "02.mp3": _summary(-14.0, 7.0, "0.3"),
            "01.mp3+02.mp3": _summary(-13.0, 6.0, "0.3"),
        }
    )

    outcome = apply([a, b], whole_album=True, binary="ffmpeg", runner=fake)

    assert outcome.tracks_tagged == 2 and outcome.album_tagged
    assert outcome.reasons == ()
    first, second = (_metadata(argv) for argv in fake.retags())
    assert first["REPLAYGAIN_TRACK_GAIN"] == "-6.00 dB"
    assert second["REPLAYGAIN_TRACK_GAIN"] == "-4.00 dB"
    assert (
        first["REPLAYGAIN_ALBUM_GAIN"] == second["REPLAYGAIN_ALBUM_GAIN"] == "-5.00 dB"
    )
    # The retag is a stream copy into a temp, moved into place.
    assert all("copy" in argv for argv in fake.retags())
    assert a.read_bytes() == b"mp3+tags"
    assert not list(tmp_path.glob("*.tmp"))


def test_part_of_an_album_gets_no_album_figures(tmp_path: Path) -> None:
    (a,) = _mp3s(tmp_path, 1)
    fake = _FakeFfmpeg({"01.mp3": _summary(-12.0, 5.0, "-0.5")})

    outcome = apply([a], whole_album=False, binary="ffmpeg", runner=fake)

    assert outcome.tracks_tagged == 1 and not outcome.album_tagged
    assert "not every track" in outcome.reasons[0]
    assert not any(
        k.startswith("REPLAYGAIN_ALBUM") for k in _metadata(fake.retags()[0])
    )


def test_an_unmeasured_mp3_is_left_untagged_not_given_a_guess(tmp_path: Path) -> None:
    a, b = _mp3s(tmp_path, 2)
    fake = _FakeFfmpeg({"02.mp3": _summary(-14.0, 7.0, "0.3")})

    outcome = apply([a, b], whole_album=True, binary="ffmpeg", runner=fake)

    assert outcome.tracks_tagged == 1 and not outcome.album_tagged
    assert a.read_bytes() == b"mp3"  # untouched: no figures, not someone else's
    assert any(
        "01.mp3: not measured" in r and "decode error" in r for r in outcome.reasons
    )
    assert any("a track could not be measured" in r for r in outcome.reasons)


# --- through the transcode adapter --------------------------------------------


def test_the_mp3_encode_drops_the_flacs_loudness_tags(tmp_path: Path) -> None:
    flac = tmp_path / "01.flac"
    flac.write_bytes(b"FLAC")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> ToolRun:
        seen.append(argv)
        if "null" not in argv:
            Path(argv[-1]).write_bytes(b"mp3")
        return ToolRun(exit_code=0, output=_SUMMARY, argv=tuple(argv))

    result = transcode_files([flac], fmt="mp3", binary="ffmpeg", runner=runner)

    encode = seen[0]
    assert "libmp3lame" in encode
    dropped = {k for k, v in _metadata(encode).items() if v == ""}
    assert dropped == set(DROPPED_TAGS)
    assert result.replaygain is not None and result.replaygain.tracks_tagged == 1
    assert result.replaygain.album_tagged


def test_a_lossless_target_is_not_remeasured(tmp_path: Path) -> None:
    flac = tmp_path / "01.flac"
    flac.write_bytes(b"FLAC")
    seen: list[list[str]] = []

    def runner(argv: list[str]) -> ToolRun:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"wv")
        return ToolRun(exit_code=0, argv=tuple(argv))

    result = transcode_files([flac], fmt="wavpack", binary="ffmpeg", runner=runner)

    assert result.replaygain is None
    assert len(seen) == 1  # the encode only: WavPack's copy of the tags is exact


def test_a_failed_track_withholds_the_album_figures(tmp_path: Path) -> None:
    good = tmp_path / "01.flac"
    bad = tmp_path / "02.flac"
    good.write_bytes(b"FLAC")
    bad.write_bytes(b"FLAC")

    def runner(argv: list[str]) -> ToolRun:
        if "null" in argv:
            return ToolRun(exit_code=0, output=_SUMMARY, argv=tuple(argv))
        if str(bad) in argv:
            return ToolRun(exit_code=1, output="boom", argv=tuple(argv))
        Path(argv[-1]).write_bytes(b"mp3")
        return ToolRun(exit_code=0, argv=tuple(argv))

    result = transcode_files([good, bad], fmt="mp3", binary="ffmpeg", runner=runner)

    assert result.replaygain is not None
    assert result.replaygain.tracks_tagged == 1
    assert not result.replaygain.album_tagged


def test_the_report_carries_the_replaygain_block(tmp_path: Path) -> None:
    flac = tmp_path / "01.flac"
    flac.write_bytes(b"FLAC")

    def runner(argv: list[str]) -> ToolRun:
        if "null" not in argv:
            Path(argv[-1]).write_bytes(b"mp3")
        return ToolRun(exit_code=0, output=_SUMMARY, argv=tuple(argv))

    block = rip_report._transcode(
        transcode_files([flac], fmt="mp3", binary="ffmpeg", runner=runner)
    )

    assert block is not None
    assert block["replaygain"] == {
        "measured_on": "the MP3 itself (ffmpeg ebur128, true peak)",
        "tracks_tagged": 1,
        "tracks_total": 1,
        "album_tagged": True,
        "reasons": [],
    }


# --- with the real ffmpeg ------------------------------------------------------

_FFMPEG = shutil.which("ffmpeg")


@pytest.mark.skipif(_FFMPEG is None, reason="needs a real ffmpeg")
def test_real_mp3_carries_its_own_figures_not_the_flacs(tmp_path: Path) -> None:
    """End to end through the shipped adapter and a real ffmpeg: a FLAC tagged with
    deliberately wrong figures (+9.99 dB, peak 0.123456, an R128 gain) gives an MP3
    whose figures are its own measurement and carries no R128 tag."""
    assert _FFMPEG is not None
    flacs = []
    for n, freq in ((1, 440), (2, 880)):
        flac = tmp_path / f"0{n}.flac"
        subprocess.run(
            [_FFMPEG, "-v", "error", "-f", "lavfi", "-i",
             f"sine=frequency={freq}:duration=2", "-ac", "2", "-ar", "44100",
             "-metadata", "TITLE=Song", "-metadata", "REPLAYGAIN_TRACK_GAIN=9.99 dB",
             "-metadata", "REPLAYGAIN_TRACK_PEAK=0.123456",
             "-metadata", "R128_TRACK_GAIN=1234", str(flac)],
            check=True,
        )  # fmt: skip
        flacs.append(flac)

    result = transcode_files(flacs, fmt="mp3", binary=_FFMPEG)

    assert result.ok and result.replaygain is not None
    assert result.replaygain.tracks_tagged == 2 and result.replaygain.album_tagged
    probe = subprocess.run(
        [_FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error", "-show_entries",
         "format_tags", "-of", "default=nw=1", str(tmp_path / "01.mp3")],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    tags = dict(line.removeprefix("TAG:").split("=", 1) for line in probe.splitlines())
    tags = {k.upper(): v for k, v in tags.items()}
    assert tags["TITLE"] == "Song"  # the other tags still carry over
    assert tags["REPLAYGAIN_TRACK_GAIN"] != "9.99 dB"
    assert tags["REPLAYGAIN_TRACK_PEAK"] != "0.123456"
    assert "R128_TRACK_GAIN" not in tags
    assert "REPLAYGAIN_ALBUM_GAIN" in tags
    # The figure is the MP3's own measurement, written the way the module writes it.
    run = subprocess.run(
        mp3_replaygain.measure_argv(_FFMPEG, [tmp_path / "01.mp3"]),
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    measured = parse_summary(run.stderr)
    assert measured is not None
    assert (
        tags["REPLAYGAIN_TRACK_GAIN"] == track_tags(measured)["REPLAYGAIN_TRACK_GAIN"]
    )
