"""`scripts/build_walkthrough_media.py`: a run folder in, the guide's pictures out.

KDD-42 W4. The script turns what the walkthrough script leaves behind into the
getting-started guide's final files: stills copied, frame bursts made into GIFs by
ffmpeg. These tests hold it to the three promises its docstring makes:

* **every shot is accounted for** as built, missing or failed, and the exit status
  is 0 only when all of them built;
* **all or nothing**: a run with any failure leaves the images folder exactly as it
  was;
* **ffmpeg is reported whole**: argv, exit code (``None`` for a call that never
  exited, never ``0``) and output, head and tail with the elision counted.

**What stands in for what, and how each stand-in differs from the real thing**
(CLAUDE.md: *what does my stand-in do that the real thing does not?*):

* **ffmpeg** is a small Python script written into ``tmp_path``. CI has no ffmpeg
  and the project adds no dependency for a test. It records its argv and writes a
  file that STARTS like the real output (``GIF89a``, the PNG signature) and is not
  a decodable picture. So these tests prove the argv, the bookkeeping and the
  refusals; whether real ffmpeg makes a good GIF from these flags is proved on the
  rig, on the shoot day (KDD-42 W7), and nowhere here.
* **the frames and stills** are 2x2 PNGs built with ``struct`` and ``zlib``, each
  with its own colour so a copied file can be traced to its source. No image file
  is committed (CLAUDE.md rule 8's spirit, and the guide's size budget).
* **the manifests** are written by the ``record`` verb's own
  ``burst_verbs._burst_manifest``, not by a copy of its format here, so a change
  to what the rig writes fails these tests instead of passing them.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import stat
import struct
import sys
import zlib
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from PySide6.QtCore import QTimer

from platterpus import getting_started
from platterpus.uiscript.burst_verbs import _Burst, _burst_manifest

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_SCRIPT: Final[Path] = _REPO_ROOT / "scripts" / "build_walkthrough_media.py"


def _load() -> ModuleType:
    """Load the script by path: ``scripts/`` is not a package (see
    ``test_harness_fidelity``), so it is never imported by name."""
    spec = importlib.util.spec_from_file_location("build_walkthrough_media", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_walkthrough_media"] = module  # dataclasses needs it
    spec.loader.exec_module(module)
    return module


bwm: Final[ModuleType] = _load()

#: Frames per synthesised burst, and the interval ``record 0.5 10`` would write.
_FRAMES: Final[int] = 5
_INTERVAL_MS: Final[int] = 100

#: The fake ffmpeg. Its behaviour is read from ``ffmpeg.json`` beside it, so one
#: test can switch it from working to failing without rewriting the program.
#: Everything it says goes to stderr, as real ffmpeg's log does, so the merged
#: output keeps its order and the fatal line is the last one.
_FAKE_FFMPEG: Final[str] = """
import json
import sys
import time
from pathlib import Path

config = json.loads(Path(__file__).with_name("ffmpeg.json").read_text())
with open(config["log"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv) + "\\n")
mode = config["mode"]
if mode == "fail":
    for number in range(config["noise"]):
        sys.stderr.write(f"frame={number:5d} fps=0.0 q=-0.0 size=N/A time=N/A\\n")
    sys.stderr.write(config["fatal"] + "\\n")
    sys.exit(3)
if mode == "hang":
    sys.stderr.write("fake ffmpeg: still working\\n")
    time.sleep(60)
target = Path(sys.argv[-1])
if mode == "not-a-gif":
    target.write_bytes(b"this is not a picture")
elif target.suffix == ".gif":
    target.write_bytes(b"GIF89a" + bytes(16))
else:
    target.write_bytes(b"\\x89PNG\\r\\n\\x1a\\n" + bytes(16))
"""

_FATAL: Final[str] = "fake ffmpeg: Invalid data found when processing input"


def _png(seed: int) -> bytes:
    """A valid 2x2 RGB PNG whose colour comes from ``seed``."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    pixel = bytes(((seed * 37) % 256, (seed * 91) % 256, (seed * 13) % 256))
    rows = b"".join(b"\x00" + pixel * 2 for _ in range(2))  # filter byte, 2 pixels
    header = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)  # 2x2, 8-bit, RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _manifest(
    stem: str,
    *,
    taken: int = _FRAMES,
    asked: int = _FRAMES,
    lost: int = 0,
    failures: tuple[str, ...] = (),
    on_screen: bool = True,
) -> str:
    """What the ``record`` verb writes, from the verb's own writer."""
    burst = _Burst(
        name=stem,
        directory=Path("."),
        frames=asked,
        interval_ms=_INTERVAL_MS,
        timer=QTimer(),
        taken=taken,
        failed=lost,
        size=(1280, 800),
        failures=list(failures),
    )
    return _burst_manifest(burst, on_screen) + "\n"


class Rig:
    """One synthesised run: its folders, the fake ffmpeg and what ffmpeg was told."""

    def __init__(self, root: Path) -> None:
        self.run: Path = root / "run"
        self.desktop: Path = root / "desktop"
        self.out: Path = root / "images"
        self.bin: Path = root / "bin"
        self.ffmpeg: Path = self.bin / "ffmpeg"
        self.calls_log: Path = root / "ffmpeg-calls.jsonl"
        for folder in (self.run, self.desktop, self.bin):
            folder.mkdir()
        self.ffmpeg.write_text(f"#!{sys.executable}\n{_FAKE_FFMPEG}", encoding="utf-8")
        self.ffmpeg.chmod(self.ffmpeg.stat().st_mode | stat.S_IXUSR)
        self.set_ffmpeg("ok")
        self.sources: dict[str, bytes] = {}
        for seed, shot in enumerate(getting_started.SHOTS):
            if shot.kind == "loop":
                for index in range(1, _FRAMES + 1):
                    self.frame(shot.stem, index).write_bytes(_png(seed + index))
                # One burst rendered off screen: the note it appends is allowed.
                text = _manifest(shot.stem, on_screen=shot.stem != "06-rip-progress")
                self.manifest(shot.stem).write_text(text, encoding="utf-8")
            else:
                folder = self.desktop if shot.kind == "desktop" else self.run
                self.sources[shot.stem] = _png(seed)
                (folder / f"{shot.stem}.png").write_bytes(self.sources[shot.stem])
                # The screenshot verb's other windows, which are never the picture.
                (self.run / f"{shot.stem}-1-Settings.png").write_bytes(_png(99))

    def frame(self, stem: str, index: int) -> Path:
        return self.run / f"{stem}-{index:04d}.png"

    def manifest(self, stem: str) -> Path:
        return self.run / f"{stem}-frames.txt"

    def set_ffmpeg(self, mode: str, *, noise: int = 0) -> None:
        config = {"mode": mode, "log": str(self.calls_log), "noise": noise}
        config["fatal"] = _FATAL
        (self.bin / "ffmpeg.json").write_text(json.dumps(config), encoding="utf-8")

    def calls(self) -> list[list[str]]:
        """Every argv the fake ffmpeg was started with, in order."""
        if not self.calls_log.exists():
            return []
        lines = self.calls_log.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def build(self, **overrides: object):  # noqa: ANN201 - the script's MediaReport
        """``build_media`` over the real shot list, the desktop folder separate.

        Unannotated like ``tests/test_round_digest.py``'s helpers: the script is
        loaded by path, so its classes have no static type in this module."""
        kwargs: dict[str, object] = {
            "desktop_dir": self.desktop,
            "out_dir": self.out,
            "ffmpeg": str(self.ffmpeg),
        }
        kwargs.update(overrides)
        return bwm.build_media(self.run, **kwargs)


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    return Rig(tmp_path)


def _result(report, stem: str):  # noqa: ANN001, ANN201 - the script's classes
    """The one result for ``stem``; asserted to exist, so a rename cannot skip it."""
    found = [r for r in report.results if r.shot.stem == stem]
    assert len(found) == 1, f"{stem}: {len(found)} results"
    return found[0]


def _files(folder: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in folder.iterdir()} if folder.exists() else {}


def _first(kind: getting_started.ShotKind) -> str:
    """The first planned shot of a kind, asserted to exist."""
    shots = getting_started.shots_of(kind)
    assert shots, f"the shot list has no {kind} shot"
    return shots[0].stem


# --- The whole run --------------------------------------------------------------


def test_a_complete_run_builds_every_planned_picture(rig: Rig) -> None:
    """Every shot in SHOTS, built and moved in, each from its own input.

    Floors: the shot list itself (so an emptied list cannot pass by building
    nothing), every file it names, and at least three GIFs (KDD-42 W1's loops).
    """
    shots = getting_started.SHOTS
    loops = getting_started.shots_of("loop")
    assert len(shots) >= getting_started.MIN_SHOTS
    assert len(loops) >= 3

    report = rig.build()

    assert report.ok, bwm.render(report)
    assert report.installed
    written = _files(rig.out)
    assert sorted(written) == sorted(s.file_name for s in shots)
    assert len(written) == len(shots)
    gifs = [name for name in written if name.endswith(".gif")]
    assert len(gifs) >= 3 and len(gifs) == len(loops)
    for shot in shots:
        data = written[shot.file_name]
        if shot.kind == "loop":
            assert data.startswith(b"GIF89a"), shot.stem
        else:
            assert data == rig.sources[shot.stem], f"{shot.stem} is not its own source"
    # The screenshot verb's other-window files were never taken for the picture.
    assert not any("-1-Settings" in name for name in written)
    assert report.total_bytes == sum(len(d) for d in written.values())
    assert sum(r.state == "built" for r in report.results) == len(shots)


def test_each_loop_is_two_ffmpeg_passes_with_the_documented_argv(rig: Rig) -> None:
    """``palettegen`` then ``paletteuse`` per loop, reading the burst's own frames
    at the burst's own rate, with ``-nostdin`` so ffmpeg never waits on a key."""
    report = rig.build()
    assert report.ok, bwm.render(report)
    calls = rig.calls()
    loops = getting_started.shots_of("loop")
    assert len(calls) == 2 * len(loops)
    for shot, palette_call, gif_call in zip(
        loops, calls[0::2], calls[1::2], strict=True
    ):
        frames = str(rig.run / f"{shot.stem}-%04d.png")
        head = [str(rig.ffmpeg), "-nostdin", "-y", "-framerate", "10", "-i", frames]
        assert palette_call[: len(head)] == head
        assert palette_call[len(head) :][:2] == ["-vf", "palettegen=stats_mode=diff"]
        palette = palette_call[-1]
        assert palette.endswith(f"{shot.stem}-palette.png")
        assert gif_call[: len(head)] == head
        tail = gif_call[len(head) :]
        assert tail[:-1] == ["-i", palette, "-lavfi", "paletteuse", "-loop", "0"]
        assert Path(tail[-1]).name == shot.file_name
        # Built in the temporary folder, never straight into the images folder.
        assert Path(tail[-1]).parent != rig.out


# --- The manifest ---------------------------------------------------------------


def test_the_manifest_the_record_verb_writes_is_read_back_exactly() -> None:
    """Round trip through the verb's own writer, on screen and off: the parser
    reads what the rig writes, not what this file believes it writes."""
    for on_screen in (True, False):
        text = _manifest(
            "06-rip-progress",
            taken=29,
            asked=30,
            lost=1,
            failures=("frame 7: not written",),
            on_screen=on_screen,
        )
        manifest = bwm.parse_manifest(text)
        assert manifest is not None, text
        assert (manifest.name, manifest.taken, manifest.asked) == (
            "06-rip-progress",
            29,
            30,
        )
        assert (manifest.lost, manifest.interval_ms) == (1, _INTERVAL_MS)
        assert manifest.rest == ("frame 7: not written",)


@settings(max_examples=300, deadline=None)
@given(st.text())
def test_reading_a_manifest_never_raises(text: str) -> None:
    """A parser of what another program wrote never raises (CLAUDE.md)."""
    result = bwm.parse_manifest(text)
    assert result is None or isinstance(result, bwm.Manifest)


def test_a_burst_that_lost_a_frame_is_refused_and_says_which(rig: Rig) -> None:
    """The rig's real shape: frame 3 failed, so the files are 1, 2, 4, 5, 6 and
    the manifest says ``5 of 6, 1 lost`` with the lost frame on the next line.
    Refused with that line quoted, and ffmpeg never started for it."""
    stem = _first("loop")
    rig.frame(stem, 3).unlink()
    rig.frame(stem, 6).write_bytes(_png(6))
    text = _manifest(stem, taken=5, asked=6, lost=1, failures=("frame 3: not written",))
    rig.manifest(stem).write_text(text, encoding="utf-8")

    report = rig.build()

    result = _result(report, stem)
    assert result.state == "failed"
    assert "the burst lost 1 frame(s)" in result.detail
    assert "5 of 6 frame(s) taken, 1 lost" in result.detail
    assert "frame 3: not written" in result.detail
    assert not any(stem in " ".join(call) for call in rig.calls())
    assert not report.ok and not rig.out.exists()


def test_a_gap_in_the_frame_numbers_is_refused(rig: Rig) -> None:
    """The manifest says five frames and none lost, but frame 3 is gone from disk.
    ffmpeg would stop at the gap and make a two-frame GIF; refused instead."""
    stem = _first("loop")
    rig.frame(stem, 3).unlink()

    report = rig.build()

    result = _result(report, stem)
    assert result.state == "failed"
    assert "missing 0003" in result.detail
    assert not any(stem in " ".join(call) for call in rig.calls())
    assert not report.ok and not rig.out.exists()


def test_a_frame_beyond_the_manifest_is_refused(rig: Rig) -> None:
    """A sixth frame the manifest does not count (a leftover of an earlier take)."""
    stem = _first("loop")
    rig.frame(stem, 6).write_bytes(_png(6))
    result = _result(rig.build(), stem)
    assert result.state == "failed"
    assert "unexpected 0006" in result.detail


def test_an_unreadable_manifest_is_refused_with_its_line(rig: Rig) -> None:
    stem = _first("loop")
    rig.manifest(stem).write_text("burst of something else\n", encoding="utf-8")
    result = _result(rig.build(), stem)
    assert result.state == "failed"
    assert "burst of something else" in result.detail


def test_a_missing_manifest_is_missing(rig: Rig) -> None:
    stem = _first("loop")
    rig.manifest(stem).unlink()
    result = _result(rig.build(), stem)
    assert result.state == "missing"
    assert str(rig.manifest(stem)) in result.detail


# --- Stills and desktop shots ---------------------------------------------------


def test_a_missing_still_is_named_and_nothing_is_moved(rig: Rig) -> None:
    stem = _first("still")
    (rig.run / f"{stem}.png").unlink()

    report = rig.build()

    result = _result(report, stem)
    assert result.state == "missing"
    assert str(rig.run / f"{stem}.png") in result.detail
    # Every other shot still built: the report covers all of them.
    others = [r for r in report.results if r.shot.stem != stem]
    assert others and all(r.state == "built" for r in others)
    assert not report.ok and not report.installed
    assert not rig.out.exists()
    assert "NOTHING was written to" in bwm.render(report)


def test_a_still_that_is_not_a_png_is_refused(rig: Rig) -> None:
    stem = _first("still")
    (rig.run / f"{stem}.png").write_bytes(b"GIF89a, not a PNG")
    result = _result(rig.build(), stem)
    assert result.state == "failed"
    assert "is not a PNG" in result.detail


def test_desktop_shots_are_read_from_the_desktop_folder(rig: Rig) -> None:
    """The Spectacle shots live in their own folder here, and only there."""
    desktop = getting_started.shots_of("desktop")
    assert desktop, "the shot list has no desktop shot"
    assert all(not (rig.run / f"{s.stem}.png").exists() for s in desktop)

    assert rig.build().ok

    # Without --desktop they are looked for in the run folder, and are missing.
    report = rig.build(desktop_dir=None, out_dir=rig.out.parent / "other")
    missing = {r.shot.stem for r in report.results if r.state == "missing"}
    assert missing == {s.stem for s in desktop}


# --- ffmpeg failing -------------------------------------------------------------


def test_a_failing_ffmpeg_is_reported_whole_and_nothing_moves(rig: Rig) -> None:
    """Exit code, exact argv and complete output kept; the report shows head and
    tail with the elision counted, so the fatal line, printed last, survives.
    The images folder keeps its older picture untouched."""
    rig.out.mkdir()
    old_still = rig.out / f"{_first('still')}.png"
    old_still.write_bytes(b"the previous shoot")
    rig.set_ffmpeg("fail", noise=300)

    report = rig.build()

    assert not report.ok and not report.installed
    assert _files(rig.out) == {old_still.name: b"the previous shoot"}
    loops = [r for r in report.results if r.shot.kind == "loop"]
    assert len(loops) >= 3
    for result in loops:
        assert result.state == "failed"
        assert result.detail == "ffmpeg (palette pass) exited 3"
        (run,) = result.runs  # the second pass never started
        assert run.exit_code == 3
        assert run.argv[:3] == (str(rig.ffmpeg), "-nostdin", "-y")
        assert run.argv[-1].endswith("-palette.png")
        assert run.output.count("\n") == 301  # all 300 noise lines and the fatal one
        assert run.output.rstrip().endswith(_FATAL)
    text = bwm.render(report)
    assert "exit 3: " + shlex.join(loops[0].runs[0].argv) in text
    assert _FATAL in text
    assert "character(s) omitted" in text
    assert "frame=    0" in text  # the head is kept too, not just the tail


def test_a_hung_ffmpeg_is_killed_and_has_no_exit_code(rig: Rig) -> None:
    """A call that never exited reports ``None``, never ``0``, and keeps what it
    printed before it was killed."""
    rig.set_ffmpeg("hang")
    stem = _first("loop")

    # 3 s: long enough that a busy parallel run cannot make Python's own start-up
    # look like the hang, short enough to keep the suite quick.
    report = rig.build(timeout_s=3.0, shots=(getting_started.shot(stem),))

    result = _result(report, stem)
    assert result.state == "failed"
    (run,) = result.runs
    assert run.exit_code is None
    assert "timed out after 3 s" in run.note
    assert "still working" in run.output
    text = bwm.render(report)
    assert "never exited" in text and "exit 0" not in text


def test_an_ffmpeg_that_exits_0_without_a_gif_is_refused(rig: Rig) -> None:
    rig.set_ffmpeg("not-a-gif")
    stem = _first("loop")
    result = _result(rig.build(shots=(getting_started.shot(stem),)), stem)
    assert result.state == "failed"
    assert "is not a GIF" in result.detail


# --- The size budget ------------------------------------------------------------


def test_an_exceeded_budget_fails_naming_the_total_and_the_budget(rig: Rig) -> None:
    report = rig.build(budget_bytes=10)
    assert all(r.state == "built" for r in report.results)
    assert not report.ok and not report.installed
    assert f"{report.total_bytes:,} bytes" in report.problem
    assert "budget of 10 bytes" in report.problem
    assert not rig.out.exists()
    assert "OVER the budget of 10 bytes" in bwm.render(report)


def test_a_budget_that_holds_passes(rig: Rig) -> None:
    report = rig.build(budget_bytes=10_000_000)
    assert report.ok
    assert "within the budget of 10,000,000 bytes" in bwm.render(report)


def test_an_undecided_budget_reports_the_total_and_is_not_a_failure(
    rig: Rig,
) -> None:
    report = rig.build(budget_bytes=None)
    assert report.ok
    text = bwm.render(report)
    assert f"total: {report.total_bytes:,} bytes" in text
    assert "undecided (KDD-42 W7)" in text


# --- The command line -----------------------------------------------------------


def _argv(rig: Rig, *extra: str) -> list[str]:
    return [
        "--run",
        str(rig.run),
        "--desktop",
        str(rig.desktop),
        "--out",
        str(rig.out),
        "--ffmpeg",
        str(rig.ffmpeg),
        *extra,
    ]


def test_the_cli_builds_everything_and_exits_0(
    rig: Rig, capsys: pytest.CaptureFixture[str]
) -> None:
    assert bwm.main(_argv(rig)) == 0
    assert len(_files(rig.out)) == len(getting_started.SHOTS)
    out = capsys.readouterr().out
    assert f"{len(getting_started.SHOTS)} of {len(getting_started.SHOTS)} built" in out


def test_the_cli_exits_1_when_a_picture_is_not_built(rig: Rig) -> None:
    (rig.desktop / f"{_first('desktop')}.png").unlink()
    assert bwm.main(_argv(rig)) == 1
    assert not rig.out.exists()


def test_dry_run_lists_every_picture_and_writes_nothing(
    rig: Rig, capsys: pytest.CaptureFixture[str]
) -> None:
    before = sorted(p.name for p in rig.run.iterdir())

    assert bwm.main(_argv(rig, "--dry-run")) == 0

    out = capsys.readouterr().out
    for shot in getting_started.SHOTS:
        assert f"{shot.file_name} <- " in out
    assert "MISSING" not in out
    assert not rig.out.exists()
    assert rig.calls() == []
    assert sorted(p.name for p in rig.run.iterdir()) == before


def test_dry_run_names_a_missing_input_and_exits_1(
    rig: Rig, capsys: pytest.CaptureFixture[str]
) -> None:
    stem = _first("loop")
    rig.manifest(stem).unlink()
    assert bwm.main(_argv(rig, "--dry-run")) == 1
    assert f"{stem}-frames.txt (MISSING)" in capsys.readouterr().out
    assert not rig.out.exists()


@pytest.mark.parametrize(
    "case", ["no-run-folder", "percent-in-run", "ffmpeg-not-runnable", "out-is-a-file"]
)
def test_bad_arguments_are_refused_before_anything_runs(
    rig: Rig, case: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Exit 2, the refusal logged and named, ffmpeg never started, nothing made."""
    argv = _argv(rig)
    if case == "no-run-folder":
        argv[1] = str(rig.run.parent / "no-such-run")
    elif case == "percent-in-run":
        renamed = rig.run.parent / "run-%d"
        rig.run.rename(renamed)
        argv[1] = str(renamed)
    elif case == "ffmpeg-not-runnable":
        rig.ffmpeg.chmod(0o644)
    else:
        rig.out.write_bytes(b"a file where the folder should be")

    assert bwm.main(argv) == 2

    refusals = [r.getMessage() for r in caplog.records if "refused" in r.getMessage()]
    assert len(refusals) == 1, refusals
    flag = {
        "no-run-folder": "--run",
        "percent-in-run": "--run",
        "ffmpeg-not-runnable": "--ffmpeg",
        "out-is-a-file": "--out",
    }[case]
    assert flag in refusals[0]
    assert rig.calls() == []
    assert rig.out.is_file() if case == "out-is-a-file" else not rig.out.exists()
