# SPDX-License-Identifier: GPL-3.0-only
"""Smoke test for `scripts/rig_session.sh`, the unattended half of a rig session.

**WHY THIS FILE EXISTS.** The v0.6.4b6 changelog said the script was *"smoke-tested
with every binary absent: exits 0, all ten artifacts present, six failures recorded
rather than hidden."* That was true — as a **manual run in one session**, with nothing
committed to keep it true. When the script grew a second half in b7 it regressed
immediately and in two ways, neither of which a human reading the diff would catch:

1. the completion banner ended up **before** the new steps, so `00-summary.txt` said
   `COMPLETE` with five steps still to run and the artifact listing omitted them;
2. `ls` on a glob matching nothing exits **2**, and with `set -e` that killed the
   whole script mid-step — in the script whose entire purpose is that *a failing step
   is data*.

Describing a manual verification in a changelog is not a check (CLAUDE.md: *a comment
where a check belongs is not a fix*). This is the check.

The script is a **deliverable the maintainer runs on the rig**, where a mid-way abort
costs a session with a disc in the drive — so the floors below matter more than usual.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO / "scripts" / "rig_session.sh"


def _run(tmp_path: Path) -> tuple[int, Path, str]:
    """Run the script with a fake HOME and a non-existent app, and return the result.

    Every external binary it wants is absent or bogus on purpose: that is the
    condition under which "never stop on a failure" is actually being tested.
    """
    home = tmp_path / "home"
    (home / "Music" / "Album").mkdir(parents=True)
    # One report with an ABSURD ETA peak (like the measured b6 one), one sane, and one
    # corrupt — so the sweep has to discriminate rather than merely print.
    album = home / "Music" / "Album"
    (album / "bad.platterpus.json").write_text(
        json.dumps({"eta_trace": {"samples": [{"our_eta_seconds": 222_900}]}})
    )
    (album / "good.platterpus.json").write_text(
        json.dumps({"eta_trace": {"samples": [{"our_eta_seconds": 600}]}})
    )
    (album / "broken.platterpus.json").write_text("{ not json")
    out = tmp_path / "out"
    env = {**os.environ, "HOME": str(home)}
    proc = subprocess.run(
        ["bash", str(_SCRIPT), str(out), "/nonexistent/appimage"],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=tmp_path,  # NOT the repo: exercises the "not in a checkout" branches
        env=env,
        check=False,
    )
    return proc.returncode, out, proc.stdout + proc.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_script_exits_zero_even_when_every_binary_is_missing(tmp_path: Path) -> None:
    """**The load-bearing property.** A failing step is data; the caller reads files.

    This is the assertion that catches an `errexit` abort. It failed for the exit-2
    bug and nothing else did — the artifacts up to the abort were all present, so a
    file-existence check alone reported success.
    """
    rc, _out, output = _run(tmp_path)
    assert rc == 0, f"the script aborted with {rc} instead of surviving:\n{output[-3000:]}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_every_step_writes_its_artifact_and_completion_comes_last(
    tmp_path: Path,
) -> None:
    """A step that produced no artifact must be distinguishable from one that passed."""
    _rc, out, _output = _run(tmp_path)
    summary = out / "00-summary.txt"
    assert summary.is_file(), "no summary was written at all"
    text = summary.read_text(encoding="utf-8", errors="replace")

    # FLOOR: a script that ran two steps and stopped would satisfy a laxer check.
    numbered = sorted(p.name for p in out.glob("[0-9][0-9]-*"))
    assert len(numbered) >= 15, f"expected >=15 numbered artifacts, got {numbered}"

    # ORDERING: `COMPLETE` must be the LAST banner, or the summary lies about how far
    # the run got. This is the bug that came from appending a second half to the file.
    banners = [ln for ln in text.splitlines() if ln.startswith("=== ")]
    assert banners, "no step banners in the summary"
    assert "COMPLETE" in banners[-1], (
        "COMPLETE is not the final banner, so the summary claims the run finished "
        f"before later steps ran. Last three: {banners[-3:]}"
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_failures_are_recorded_rather_than_hidden(tmp_path: Path) -> None:
    """With every binary absent, non-zero exits MUST appear in the record.

    The floor that caught the inverted-`!` bug, where every failure was written as
    `exit: 0` — the script reporting success for all of them while exiting 0 itself.
    """
    _rc, out, _output = _run(tmp_path)
    text = (out / "00-summary.txt").read_text(encoding="utf-8", errors="replace")
    nonzero = [ln for ln in text.splitlines() if "exit: " in ln and "exit: 0" not in ln]
    assert len(nonzero) >= 3, (
        "fewer than three non-zero exits were recorded even though no binary exists — "
        f"failures are being swallowed. Recorded: {nonzero}"
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_eta_sweep_flags_an_absurd_peak_and_reports_unreadable_files(
    tmp_path: Path,
) -> None:
    """Step 10 must DISCRIMINATE, not merely print, and must not skip a bad file."""
    _rc, out, _output = _run(tmp_path)
    sweep = out / "10-eta-sweep.txt"
    assert sweep.is_file(), "the ETA sweep wrote no artifact"
    text = sweep.read_text(encoding="utf-8", errors="replace")
    assert "ABSURD" in text, (
        "a 61.9-hour peak was not flagged, so the sweep cannot detect the very bug "
        f"it exists for:\n{text}"
    )
    assert "absurd (>24h) peaks: 1" in text, f"the absurd count is wrong:\n{text}"
    assert "UNREADABLE" in text, (
        "the corrupt report was skipped silently — an unreadable artifact is a "
        f"finding, not a no-op:\n{text}"
    )
    # And the sane report must NOT be flagged, or the check passes on everything.
    assert "good.platterpus.json" in text and "0.17h" in text, (
        f"the sane report was not measured, so the sweep may flag indiscriminately:\n{text}"
    )
