"""`drivetest.sh probe` reads every whole second the wrong samples sit in (round 39's G4).

The first C2 probe (2026-11-11, filed by the fork at `cyanrip@74b6f0a`) read five
26-frame windows chosen as points: they held 20 sectors of track 3's second 244,
26 of its second 251, none of its second 252, and part of track 5's second 144
(the fork's round 39 lap 3 S12). The test burn's records place track 3's wrong
reads in whole seconds 244, 251 and 252 and track 5's in second 144, so the probe
now reads each of those seconds whole: three windows from the second's first frame.

These run the script's OWN functions (`c2_windows`, `c2_summary`), cut out of it
by name, and check them against the reference disc's committed log, not against
numbers copied here: the track starts and the read offset come from
`output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.log`. No drive,
no disc and no audio: the summary's reads are zeros we write ourselves.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

from platterpus.parsers.cyanrip_log import parse_cyanrip_log

_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_SCRIPT: Final[Path] = _ROOT / "docs/rig-scripts/drivetest.sh"
_REFERENCE_LOG: Final[Path] = (
    _ROOT / "output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.log"
)
#: The seconds the test burn's records place a wrong read in (our round 39 lap 2),
#: as (track, second). The probe must cover these; it may cover more.
_WRONG_SECONDS: Final[frozenset[tuple[int, int]]] = frozenset(
    {(3, 244), (3, 251), (3, 252), (5, 144)}
)
#: Where the fork's probe found C2 bits: LBA 83430, in track 5 (their lap 3 S11).
_C2_BITS_LBA: Final[int] = 83430
_FRAME_SAMPLES: Final[int] = 588
_WINDOW_FRAMES: Final[int] = 26
_C2_FRAME: Final[int] = 2646

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _function(name: str) -> str:
    """The text of one shell function of the script, from `name() {` to its `}`."""
    text = _SCRIPT.read_text(encoding="utf-8")
    match = re.search(rf"^{name}\(\) {{\n.*?^}}\n", text, re.MULTILINE | re.DOTALL)
    assert match is not None, f"{name}() is not in {_SCRIPT.name}"
    return match.group(0)


def _windows() -> list[tuple[str, int]]:
    """`c2_windows` as the script computes it, run in bash."""
    text = _SCRIPT.read_text(encoding="utf-8")
    seconds = re.search(r"^C2_SECONDS=.*$", text, re.MULTILINE)
    assert seconds is not None
    out = subprocess.run(
        [
            "bash",
            "-c",
            seconds.group(0) + "\n" + _function("c2_windows") + "c2_windows",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout
    pairs = [line.split(":") for line in out.split()]
    return [(label, int(lba)) for label, lba in pairs]


def _reference() -> tuple[dict[int, int], int]:
    """Each track's start sector and the read offset, from the committed log."""
    log = parse_cyanrip_log(_REFERENCE_LOG.read_text(encoding="utf-8"))
    starts = {
        t.number: t.start_sector for t in log.tracks if t.start_sector is not None
    }
    offset = log.ripping_info.read_offset_correction
    assert offset == 667 and len(starts) >= 5  # floors: the log is the one we mean
    return starts, offset


def test_the_probe_reads_each_wrong_second_whole() -> None:
    """Every disc frame that holds a sample of each second, after the read offset
    moves the file's second +667 samples into the disc, is inside a window read
    under that second's label."""
    starts, offset = _reference()
    windows = _windows()
    assert windows[0] == ("control", 5000)
    labels = {label for label, _ in windows} - {"control"}
    covered_seconds = set()
    for label in labels:
        m = re.fullmatch(r"t(\d+)s(\d+)", label)
        assert m is not None, label
        track, second = int(m[1]), int(m[2])
        covered_seconds.add((track, second))
        first_sample = (starts[track] + 75 * second) * _FRAME_SAMPLES + offset
        last_sample = first_sample + 75 * _FRAME_SAMPLES - 1
        needed = set(
            range(first_sample // _FRAME_SAMPLES, last_sample // _FRAME_SAMPLES + 1)
        )
        read = {
            lba + i
            for name, lba in windows
            if name == label
            for i in range(_WINDOW_FRAMES)
        }
        assert needed <= read, (label, sorted(needed - read))
        assert len(needed) == 76  # the offset makes a second straddle 76 frames
    assert covered_seconds >= _WRONG_SECONDS, sorted(_WRONG_SECONDS - covered_seconds)


def test_the_second_with_the_c2_bits_holds_the_lba_they_were_found_at() -> None:
    windows = [(label, lba) for label, lba in _windows() if label == "t5s144"]
    assert any(lba <= _C2_BITS_LBA < lba + _WINDOW_FRAMES for _, lba in windows)


def _read(c2_bits_at: dict[int, int]) -> bytes:
    """26 frames of zero audio, with N C2 bits set in the given frames."""
    frames = []
    for i in range(_WINDOW_FRAMES):
        pointers = bytearray(294)
        for bit in range(c2_bits_at.get(i, 0)):
            pointers[bit] = 0x01
        frames.append(bytes(2352) + bytes(pointers))
    return b"".join(frames)


def test_the_summary_names_each_flagged_frame_by_its_disc_lba(tmp_path: Path) -> None:
    for n in (1, 2, 3):
        (tmp_path / f"t5s144-83422-c2-{n}.bin").write_bytes(_read({8: 3}))
        (tmp_path / f"control-5000-c2-{n}.bin").write_bytes(_read({}))
    (tmp_path / "t3s252-46967-c2-1.bin").write_bytes(b"\x00" * 100)
    (tmp_path / "stray-c2-1.bin").write_bytes(b"")
    out = subprocess.run(
        ["bash", "-c", _function("c2_summary") + 'c2_summary "$1"', "x", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout.splitlines()
    assert "control, LBA 5000 to 5025: C2 bits none in 3 read(s)" in out
    assert (
        "track 5 second 144, LBA 83422 to 83447: C2 bits read 1: LBA 83430 (3 bits); "
        "read 2: LBA 83430 (3 bits); read 3: LBA 83430 (3 bits)"
    ) in out
    assert (
        "track 3 second 252, LBA 46967 to 46992: C2 bits read 1: 100 bytes, "
        f"not 26 frames of {_C2_FRAME}"
    ) in out
    assert "stray-c2-1.bin: not a probe read's name; left out of this summary" in out
    # Windows in disc order, so the summary reads along the disc.
    lbas = [int(m[1]) for line in out if (m := re.search(r"LBA (\d+) to", line))]
    assert lbas == sorted(lbas) and len(lbas) == 3
