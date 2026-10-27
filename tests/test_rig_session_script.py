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
import tarfile
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


def _run(tmp_path: Path, extra_path: Path | None = None) -> tuple[int, Path, str]:
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
    # NO NETWORK, deliberately, like the absent binaries. Step 12 clones the fork
    # from GitHub, and on 2026-09-29 a CI runner that could not reach GitHub showed
    # the clone had escaped `run()` and aborted the whole script with git's 128.
    # Rewriting the URL to a path that does not exist makes that failure happen
    # here every time, in milliseconds, instead of only on a runner that is offline.
    env = {
        **os.environ,
        "HOME": str(home),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "url.file:///nonexistent/platterpus-test/.insteadOf",
        "GIT_CONFIG_VALUE_0": "https://github.com/",
    }
    if extra_path is not None:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
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
    # timeouts duly arrived (the former `platterpusmorning.sh`, the
    # morning-after collector, since retired). Scoping a sweep is fine;
    # scoping it silently
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


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_harness_emits_no_shell_arithmetic_errors(tmp_path: Path) -> None:
    """A `[: 0\\n0: integer expected` on a rig session is a bug, not noise.

    `grep -c` PRINTS "0" and EXITS 1 when it matches nothing, so the idiom
    `x=$(grep -c ... || echo 0)` yields the two-line string "0\\n0" — and the
    numeric test that follows rejects it. Seen on the 2026-08-25 session. It was
    harmless *by luck*: the failed comparison fell through to the same branch the
    correct value would have taken, so the conclusion printed was right and the
    bug was visible only as a stderr line in the middle of an operator's console.

    Scoped to shell *arithmetic and test* errors, which are always defects, rather
    than to "any stderr". This fixture deliberately runs with no binaries present,
    so `command not found` is expected output here and must not fail the test —
    matching on it would make this a false-failure machine.
    """
    _rc, _out, output = _run(tmp_path)
    # MATCHED AS A PAIR, NOT AS A FIXED STRING, and that is the whole lesson of
    # this test's first version. It looked for the literal "integer expected" —
    # which is what bash prints on the rig — while the bash in CI prints "integer
    # *expression* expected". The substring never matched, so the test passed
    # against the very bug it was written for, and only `revert_probe` caught it.
    # A stand-in that words its errors differently from the real thing is the
    # harness-fidelity trap (`CLAUDE.md`), arriving through a locale string.
    subjects = ("integer", "unary operator", "binary operator")
    offenders = [
        line
        for line in output.splitlines()
        if "expected" in line and any(s in line for s in subjects)
    ]
    assert not offenders, (
        "the harness emitted shell test/arithmetic errors, which means a variable "
        "held something other than the number it was assumed to hold:\n"
        + "\n".join(offenders[:10])
    )


def test_no_shell_script_continues_a_line_into_a_comment() -> None:
    """A comment line after a trailing backslash ends the command, silently.

    `rig_session.sh` had a comment between `run "clone the fork" … \\` and its
    command, so `run` got no command and the clone ran outside it, under `set -e`:
    on 2026-09-29 a CI runner that could not reach GitHub aborted the whole session
    with git's 128. Swept over every tracked shell script, not only the one where
    it was found. Floor: at least three scripts are read.
    """
    tracked = subprocess.run(
        ["git", "ls-files", "*.sh"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert len(tracked) >= 3, f"the floor: only {tracked} were found"
    offenders: list[str] = []
    for name in tracked:
        lines = (_REPO / name).read_text(encoding="utf-8").splitlines()
        for number, (line, following) in enumerate(
            zip(lines, lines[1:], strict=False), 1
        ):
            if line.rstrip().endswith("\\") and following.lstrip().startswith("#"):
                offenders.append(f"{name}:{number}")
    assert not offenders, (
        "a line continues into a comment, which ends the command there: "
        + ", ".join(offenders)
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_clone_step_runs_inside_run_and_records_its_failure(
    tmp_path: Path,
) -> None:
    """With no network, step 12 records the clone's argv and its non-zero exit."""
    rc, out, output = _run(tmp_path)
    summary = (out / "00-summary.txt").read_text(encoding="utf-8", errors="replace")
    block = summary[summary.index("clone the fork") :]
    assert "argv: timeout -k 30 300 git clone" in block, block[:400]
    assert "exit: 128" in block, block[:400]
    assert "clone failed" in block, block[:400]
    assert "13  our own gates" in summary, "the session stopped after the clone"
    assert rc == 0, output[-2000:]


def _failing_shim(folder: Path, tool: str, when_arg: str) -> Path:
    """A `tool` that fails (exit 2) when any argument equals `when_arg`, else is real."""
    real = shutil.which(tool)
    assert real is not None, f"{tool} is not on PATH"
    folder.mkdir(exist_ok=True)
    shim = folder / tool
    shim.write_text(
        "#!/bin/bash\n"
        'for a in "$@"; do\n'
        f'  if [ "$a" = "{when_arg}" ]; then echo "{tool}: simulated failure" >&2; exit 2; fi\n'
        "done\n"
        f'exec {real} "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return folder


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_a_grep_that_could_not_count_is_not_reported_as_a_real_result(
    tmp_path: Path,
) -> None:
    """Regression (2026-10-12): `grep -c ... 2>/dev/null || true` read "could not look" as none.

    grep exits 1 for "no match" and 2 for "could not look". Both used to become
    TOC_HITS=0 and the line "no TOC-sourced pre-gap ... a REAL RESULT", the
    one conclusion a grep that never read the file has no evidence for.
    """
    shims = _failing_shim(tmp_path / "shims", "grep", "Pregap source: TOC")
    _rc, _out, output = _run(tmp_path, extra_path=shims)
    assert "COULD NOT COUNT the TOC-sourced pre-gaps (grep exit 2)" in output, output
    assert "a REAL RESULT, not a gap" not in output


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_an_empty_count_is_still_a_real_result(tmp_path: Path) -> None:
    """Control for the test above: with a working grep, finding none IS a result."""
    _rc, _out, output = _run(tmp_path)
    assert "a REAL RESULT, not a gap" in output, output
    assert "COULD NOT COUNT" not in output


def _run_collect(
    tmp_path: Path, extra_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the rig collector under a throwaway HOME holding one rip folder."""
    home = tmp_path / "home"
    rip = home / "Music" / "rips" / "Artist" / "Album"
    rip.mkdir(parents=True)
    (rip / "album.log").write_text("Track 1 | CRC32 A1B2C3D4\n", encoding="utf-8")
    env = dict(os.environ, HOME=str(home))
    if extra_path is not None:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", str(_REPO / "docs" / "rig-scripts" / "platterpuscollect.sh")],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=tmp_path,
        env=env,
        check=False,
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_collector_refuses_to_pack_a_bundle_it_could_not_check_for_audio(
    tmp_path: Path,
) -> None:
    """Regression (2026-10-12): a failing audio check printed "clean" (Critical rule #8).

    `AUDIO=$(find ... || true)` read a failed `find` as "no audio found", printed
    "clean - no audio files in the bundle", and packed the tarball the operator
    is told to upload. Now nothing is packed, and the reason is printed.
    """
    shims = _failing_shim(tmp_path / "shims", "find", "*.flac")
    result = _run_collect(tmp_path, extra_path=shims)
    assert result.returncode != 0, result.stdout
    assert "COULD NOT CHECK the bundle for audio" in result.stderr, result.stderr
    assert "clean - no audio files" not in result.stdout
    assert not (tmp_path / "home" / "platterpusbundle.tar.gz").exists()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_collector_says_when_it_could_not_list_the_rips(tmp_path: Path) -> None:
    """A failed listing of ~/Music/rips is not "no rip folder found"."""
    shims = _failing_shim(tmp_path / "shims", "find", "-printf")
    result = _run_collect(tmp_path, extra_path=shims)
    assert "COULD NOT LIST ~/Music/rips" in result.stdout, result.stdout
    assert "no rip folder found" not in result.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_collector_packs_a_clean_bundle_with_a_working_find(tmp_path: Path) -> None:
    """Control for both: the shims, not the collector, are what made them fail."""
    result = _run_collect(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "clean - no audio files in the bundle" in result.stdout
    assert (
        "album.log" in result.stdout
        or (tmp_path / "home" / "platterpusbundle.tar.gz").exists()
    )
    assert (tmp_path / "home" / "platterpusbundle.tar.gz").exists()


def _plant_in_transcripts(tmp_path: Path, names: list[str]) -> None:
    """Put text files with the given names where the collector copies wholesale.

    `~/.local/share/platterpus/uiscript` is copied with `cp -r`, so anything in it
    reaches the bundle and only the audio sweep stands between it and the upload.
    The files hold text: no audio is created (Critical rule #8 binds tests too).
    """
    folder = tmp_path / "home" / ".local" / "share" / "platterpus" / "uiscript"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "transcript.txt").write_text("step 1 ok\n", encoding="utf-8")
    for name in names:
        (folder / name).write_text("not audio\n", encoding="utf-8")


def _bundle_members(tmp_path: Path) -> list[str]:
    """The file names inside the packed bundle."""
    with tarfile.open(tmp_path / "home" / "platterpusbundle.tar.gz") as tar:
        return [Path(m.name).name for m in tar.getmembers() if m.isfile()]


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_collector_removes_every_audio_type_the_guards_know(tmp_path: Path) -> None:
    """Regression (review 2026-10-27, item 1.6): no audio type is packed.

    The sweep checked 7 of the guards' 18 extensions, so a `.ogg`, `.opus` or
    `.pcm` went into the tarball under the line "clean - no audio files in the
    bundle". One file per shared extension, alternately in upper case, plus a
    name with spaces in it.

    Not a test of item 3.7 (`IFS= read -r` in the delete loop): every line the
    sweep reads starts with the bundle's absolute path, so the blanks a bare
    `read` strips cannot occur there. `scripts/revert_probe.py` confirmed that
    reverting only `IFS=` leaves this test passing; the change is hygiene.
    """
    shared = (_REPO / ".githooks" / "audio-extensions.txt").read_text(encoding="utf-8")
    extensions = shared.split()
    assert len(extensions) >= 18, "the shared extension list is not being read"
    names = [
        f"t{i:02d}.{ext.upper() if i % 2 else ext}" for i, ext in enumerate(extensions)
    ]
    names.append(" with spaces .ogg")
    _plant_in_transcripts(tmp_path, names)

    result = _run_collect(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "REMOVING audio that must not be here" in result.stdout, result.stdout
    assert "removed; the bundle is now clean" in result.stdout, result.stdout
    members = _bundle_members(tmp_path)
    # Non-triviality: the bundle was packed and does carry the planted text file,
    # so an empty or missing tarball cannot pass the audio check below.
    assert "transcript.txt" in members, members
    packed_audio = [n for n in members if n in names]
    assert not packed_audio, f"audio reached the upload bundle: {packed_audio}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_the_collector_refuses_to_pack_audio_it_could_not_remove(
    tmp_path: Path,
) -> None:
    """A removal is checked, not assumed: audio left behind stops the packing.

    A name holding a newline cannot survive the sweep's one-name-per-line list,
    so `rm` is handed two halves that do not exist. The collector must look
    again, see the file is still there, and refuse to pack.
    """
    _plant_in_transcripts(tmp_path, ["two\nlines.flac"])

    result = _run_collect(tmp_path)

    assert result.returncode != 0, result.stdout
    assert "AUDIO IS STILL IN THE BUNDLE" in result.stderr, result.stderr
    assert not (tmp_path / "home" / "platterpusbundle.tar.gz").exists()
