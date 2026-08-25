# SPDX-License-Identifier: GPL-3.0-only
"""Smoke test for the shipped `rig_session.sh`, the unattended half of a rig session.

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
# Inside the package, not `scripts/`: the harness ships in the wheel so
# `--rig-session` reaches it from an AppImage, where a hardware session
# actually happens. Resolved through the app's own accessor rather than a
# second copy of the path, so a move breaks one place instead of two.
_SCRIPT = _REPO / "src" / "platterpus" / "rig_session.sh"


def _shell_harnesses() -> list[Path]:
    """Every shell harness in this project whose steps drive a drive or a network.

    Derived from the filesystem, not enumerated: a listed population is the
    hand-maintained field that rots, and this file's own sweep already promised to
    catch "the next one added" while looking at exactly one file.
    """
    found = [_SCRIPT, *sorted((_REPO / "docs" / "rig-scripts").glob("*.sh"))]
    return [p for p in found if p.is_file()]


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
def test_the_script_exits_zero_even_when_every_binary_is_missing(
    tmp_path: Path,
) -> None:
    """**The load-bearing property.** A failing step is data; the caller reads files.

    This is the assertion that catches an `errexit` abort. It failed for the exit-2
    bug and nothing else did — the artifacts up to the abort were all present, so a
    file-existence check alone reported success.
    """
    rc, _out, output = _run(tmp_path)
    assert rc == 0, (
        f"the script aborted with {rc} instead of surviving:\n{output[-3000:]}"
    )


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


def test_every_timeout_in_the_harness_escalates_to_sigkill() -> None:
    """A `timeout` without `-k` is the hang it was written to prevent.

    Plain `timeout N cmd` sends SIGTERM at the deadline and then waits — with no
    further bound — for a process that may never take it. This harness drives an
    optical drive, so a child can sit in an ioctl in uninterruptible sleep, which
    is exactly the case `CLAUDE.md` names: *"bound the post-SIGKILL wait too."*

    MEASURED, 2026-08-23: step 5b (`timeout 600 cyanrip -j … -l 1`) left a 0-byte
    artifact, no `exit:` line and no `MANIFEST.txt`, because the session never got
    past it — an unattended run whose whole purpose is that a failing step is data
    produced no data at all for that step and everything after it.

    A **sweep**, not a pin on the two that were wrong, so the next one added is
    caught too (`docs/testing.md` §5.o). Asserts the population is non-empty first:
    a regex that matches nothing would make this pass by finding nothing.

    **What this does NOT catch, stated rather than implied:** a step added with no
    `timeout` at all. Deleting the bound entirely makes this test pass — verified,
    `scripts/revert_probe.py` with `expect: "unaffected"`. Requiring a timeout on
    every command would be noise (most are instant local ones), so the gap is real
    and deliberate; the reviewer's question for a new step that touches the drive
    or the network is still "what bounds this?"
    """
    import re

    # COMMENTS STRIPPED FIRST. Without this the sweep matched the prose in the
    # comment that documents the very rule it enforces ("the timeout that exists
    # to stop a hang IS the hang") and failed on it — a check tripped by its own
    # explanation, the same shape as the handshake parser matching its own fenced
    # examples. A shell comment runs to end of line, and this file has no `#`
    # inside a string that could be eaten wrongly.
    naked: list[str] = []
    total = 0
    # EVERY shell harness, DERIVED from the filesystem rather than listed. The
    # docstring above promised "the next one added is caught too" while the
    # population was one hardcoded file — and a second harness with its own
    # timeouts duly arrived (`docs/rig-scripts/platterpusmorning.sh`, the
    # morning-after collector). Scoping a sweep is fine; scoping it silently
    # while its own docstring claims otherwise is the defect `CLAUDE.md` names.
    for script in _shell_harnesses():
        lines = [
            ln.split("#", 1)[0]
            for ln in script.read_text(encoding="utf-8").splitlines()
        ]
        text = "\n".join(lines)
        # Command position only: `timeout` starting a command, not a substring —
        # and `(` IS a command position, which this regex used to omit.
        #
        # **Measured, and it is why the widening above was vacuous on its first
        # try.** A bare `timeout` planted inside `APP="$(timeout 60 find …)"` did
        # not fail this test: the character before `timeout` is `(`, which was not
        # in the boundary set, so every command substitution was invisible. Six of
        # the morning collector's twelve bounds sat inside `$(…)` or `<(…)`, so the
        # sweep was reading half the file and reporting on all of it. Caught by
        # `scripts/revert_probe.py`'s discipline — assert the edit LANDED (the hash
        # moved) before believing a pass.
        calls = re.findall(
            r"(?:^|\|\||&&|;|\(|\s)(timeout\s+[^\n]*)", text, re.MULTILINE
        )
        total += len(calls)
        naked += [
            f"{script.name}: {c.strip()}"
            for c in calls
            if not re.match(r"timeout\s+-k\s+\d", c.strip())
        ]
    assert total, (
        "no `timeout` calls found in ANY shell harness — either they stopped "
        "bounding their steps or this regex has rotted; both need a human"
    )
    assert not naked, (
        "these `timeout` calls send SIGTERM and then wait forever if it does not "
        "land — add `-k <grace>` so the deadline is actually reachable:\n  "
        + "\n  ".join(naked)
    )


def test_the_diagnostics_probe_allows_for_a_full_length_first_track() -> None:
    """The 600 s bound sat inside the healthy range, so it would have killed a
    working step and called it a finding.

    Step 5b passes `-l 1`, which rips track 1 *in full*. The measured rate on this
    rig is 0.5x: track 1 of the reference disc (3:13) took **405.74 s** elapsed. A
    10-minute opener is therefore ~20 minutes before drive spin-up, TOC read and
    the AccurateRip lookup — so 600 s was a bound derived from one disc's short
    first track (`docs/testing.md` §5.ao, "is the population I measured closed?").

    Asserts the floor rather than the exact number, so raising it further does not
    need a test edit but dropping it back under does.
    """
    import re

    text = _SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"timeout\s+-k\s+(\d+)\s+(\d+)\s+\"\$RIPPER\"\s+-j", text)
    assert match, "could not find the bounded `-j` probe invocation"
    grace, deadline = int(match.group(1)), int(match.group(2))
    assert deadline >= 1200, (
        f"the -j probe's deadline is {deadline}s. It rips track 1 in full at a "
        "measured 0.5x, so a 10-minute opener needs ~1200s before any drive "
        "overhead — below that the timeout kills working rips"
    )
    assert grace >= 10, (
        f"a {grace}s SIGKILL grace is too tight to distinguish 'slow to exit' "
        "from 'wedged'"
    )


# --- The diagnosis file: the short answers, so nobody reads scrollback -------


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_diagnosis_file_is_written_and_names_its_verdict(tmp_path: Path) -> None:
    """The operator must not have to find four numbers in a 5 KB chronological log.

    Written after they reported exactly that: *"the questions you asked me i cannot
    see easily… they might be in there, but not visible to me readily."* Asking a
    person to eyeball terminal scrollback for an exit code and a duration is work
    handed back, which `CLAUDE.md` names as a symptom rather than a deliverable.

    Asserts the file exists, carries every heading the answers live under, and
    reaches a NAMED verdict rather than leaving the reader to infer one — even in
    this fixture, where no binary exists and the honest verdict is
    "NOT DETERMINED".
    """
    _rc, out, _output = _run(tmp_path)
    diag = out / "00-diagnosis.txt"
    assert diag.is_file(), "no diagnosis file was written"
    text = diag.read_text(encoding="utf-8", errors="replace")

    for heading in ("versions", "C1", "capture integrity", "what to send"):
        assert heading in text, f"the diagnosis has no {heading!r} section:\n{text}"

    # A verdict, always. Silence is the failure mode this file exists to remove.
    verdicts = ("NOT DETERMINED", "DID NOT REPRODUCE", "REPRODUCED")
    assert any(v in text for v in verdicts), (
        f"the diagnosis reaches no named verdict, so the reader must infer one:\n{text}"
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_every_step_records_a_duration_not_just_an_exit_code() -> None:
    """`elapsed:` is the number the C1 question turns on, and it was not recorded.

    Fifteen seconds means "the hang did not reproduce"; thirty-one minutes means it
    did. For three rig sessions this harness logged the exit code and not the
    duration, so the single datum the investigation needed had to be read out of a
    terminal by a person and relayed by hand.

    Asserted against the SOURCE rather than a run, so it holds for steps this
    fixture cannot reach.
    """
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "elapsed: ${secs}s" in text, (
        "run() does not record elapsed time; the C1 measurement is unanswerable"
    )
    # And the pair that makes the measurement a CONTROLLED one rather than an
    # observation: the bare refusal must run too, or there is nothing to compare.
    assert "04-bare-refusal.txt" in text, (
        "the bare offset refusal control step is gone, so a slow -j run cannot be "
        "distinguished from a slow refusal path — the whole point of the pair"
    )
