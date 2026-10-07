#!/usr/bin/env python3
"""Turn a walkthrough run folder into the getting-started guide's pictures (KDD-42 W4).

The walkthrough rig script (``getting_started.WALKTHROUGH_SCRIPT``) leaves a run
folder: a ``<stem>.png`` for each ``screenshot`` step, and for each ``record`` step
a burst of frames ``<stem>-0001.png`` onward with a manifest, ``<stem>-frames.txt``.
This reads the one shot list every part of the guide shares,
``getting_started.SHOTS``, and makes each picture's final file, ``Shot.file_name``:

* ``still``: the run's PNG, copied once it is shown to BE a PNG;
* ``desktop`` (taken by hand with Spectacle, outside the app): the same, read from
  ``--desktop``, which defaults to the run folder;
* ``loop``: a looping GIF made by ffmpeg, only after the manifest shows a complete
  burst: no frame lost, and the frames on disk numbered exactly 1 to N.

**All or nothing.** Every file is built in a temporary folder and moved into
``--out`` (the guide's ``images/`` folder by default) only when EVERY shot built and
the total fits the size budget. A failed run leaves the images folder exactly as it
was, so the guide can never show half of one shoot beside half of another.

**ffmpeg is reported whole**: each call's exact argv, its exit code (``None`` when it
never exited, because it timed out or could not start; never written as ``0``) and
its complete merged output, shown as head and tail with the elided count marked,
because ffmpeg's reason for failing is the last thing it prints.

    python3 scripts/build_walkthrough_media.py --run <run folder> --desktop <folder>
    python3 scripts/build_walkthrough_media.py --run <run folder> --dry-run

Exit status: 0 when every picture was built and moved in (with ``--dry-run``: when
every input is present); 1 when one was not, or the budget was exceeded; 2 when an
argument was refused before anything ran.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

# The shot list, the budget and the fps cap are read from where they are decided,
# never restated here, so a renamed picture cannot leave this script behind.
from platterpus import getting_started  # noqa: E402
from platterpus.diagnostics import bounded_chars  # noqa: E402
from platterpus.getting_started import Shot  # noqa: E402
from platterpus.uiscript.burst_verbs import RECORD_MAX_FPS  # noqa: E402

log = logging.getLogger("build_walkthrough_media")

#: ``missing``: an input is not there. ``failed``: it is, and is wrong, or ffmpeg failed.
ShotState = Literal["built", "missing", "failed"]

_PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
_GIF_SIGNATURES: Final[tuple[bytes, ...]] = (b"GIF89a", b"GIF87a")
#: One ffmpeg call's limit. A 300-frame burst takes seconds; this is for a hang.
FFMPEG_TIMEOUT_S: Final[float] = 300.0
#: How much of a failing ffmpeg's output the report shows, in characters. The
#: tail is the larger half: ffmpeg says why it failed last.
_OUTPUT_HEAD: Final[int] = 1500
_OUTPUT_TAIL: Final[int] = 3000
#: The manifest's first line, as ``burst_verbs._burst_manifest`` writes it. Matched
#: at the start only, so the " — RENDERED while…" note it may append is allowed.
_MANIFEST: Final[re.Pattern[str]] = re.compile(
    r"burst '(?P<name>[^']{1,200})': (?P<taken>[0-9]{1,6}) of (?P<asked>[0-9]{1,6}) "
    r"frame\(s\) taken, (?P<lost>[0-9]{1,6}) lost, one every "
    r"(?P<interval>[0-9]{1,6}) ms, [0-9]{1,6}x[0-9]{1,6}"
)


@dataclass(frozen=True)
class Manifest:
    """A burst's manifest, read. ``rest`` holds the lines after the first, each of
    which names a lost frame."""

    name: str
    taken: int
    asked: int
    lost: int
    interval_ms: int
    rest: tuple[str, ...]


@dataclass(frozen=True)
class FfmpegRun:
    """One ffmpeg call, kept whole. ``exit_code`` is ``None`` when it never exited,
    and ``note`` then says why (timed out, or could not start)."""

    argv: tuple[str, ...]
    exit_code: int | None
    output: str
    note: str = ""


@dataclass
class ShotResult:
    """What became of one shot. ``size`` is the built file's bytes."""

    shot: Shot
    state: ShotState
    detail: str
    size: int = 0
    runs: list[FfmpegRun] = field(default_factory=list)


@dataclass
class MediaReport:
    """Every shot's result, the total, and whether the files were moved in."""

    results: list[ShotResult]
    out_dir: Path
    budget_bytes: int | None
    total_bytes: int = 0
    #: Why the files were not moved in, when every shot built: the budget, or the
    #: move itself failing part way.
    problem: str = ""
    #: Set only after every file was moved in. Nothing else sets it.
    installed: bool = False

    @property
    def ok(self) -> bool:
        """The one success claim: every shot built, nothing refused, all moved in."""
        built = all(r.state == "built" for r in self.results)
        return built and not self.problem and self.installed


def parse_manifest(text: str) -> Manifest | None:
    """The manifest read, or ``None`` when its first line is not one. Never raises."""
    lines = text.splitlines()
    match = _MANIFEST.match(lines[0]) if lines else None
    if match is None:
        return None
    return Manifest(
        name=match["name"],
        taken=int(match["taken"]),
        asked=int(match["asked"]),
        lost=int(match["lost"]),
        interval_ms=int(match["interval"]),
        rest=tuple(line.strip() for line in lines[1:] if line.strip()),
    )


def _starts_with(path: Path, signatures: tuple[bytes, ...]) -> bool:
    """Whether the file opens with one of ``signatures``; False if it cannot be read."""
    try:
        with path.open("rb") as handle:
            head = handle.read(8)
    except OSError:
        return False
    return any(head.startswith(sig) for sig in signatures)


def _frame_problem(run_dir: Path, stem: str, count: int) -> str:
    """'' when the frames on disk are exactly ``<stem>-0001.png`` to ``count``.

    ffmpeg reads ``<stem>-%04d.png`` and stops at the first gap, so a missing frame
    would make a shorter GIF that nothing reports. Only ``<stem>-<digits>.png`` is a
    frame, so ``07-verdict-1-<slug>.png`` is never read as ``07-verdict-appears``'s.
    """
    prefix = f"{stem}-"
    try:
        names = [p.name for p in run_dir.iterdir()]
    except OSError as exc:
        return f"the run folder could not be listed: {exc}"
    numbers = [
        n[len(prefix) : -len(".png")]
        for n in names
        if n.startswith(prefix) and n.endswith(".png")
    ]
    found = {n for n in numbers if n.isascii() and n.isdigit()}
    expected = {f"{i:04d}" for i in range(1, count + 1)}
    if found == expected:
        return ""
    missing = ", ".join(sorted(expected - found)) or "none"
    extra = ", ".join(sorted(found - expected)) or "none"
    return bounded_chars(
        f"the frames on disk are not {stem}-0001 to -{count:04d}: missing {missing}; "
        f"unexpected {extra}",
        head=300,
        tail=200,
    )


def _run_ffmpeg(argv: list[str], timeout_s: float) -> FfmpegRun:
    """Run one ffmpeg call to the end and keep everything it said.

    A command-line tool, not GUI code, so a blocking ``subprocess.run`` is right
    here; the timeout is what stops a hung ffmpeg holding the run forever. stderr
    is merged into stdout so the output keeps ffmpeg's own order. The argv kept is
    the one the child was given (``args``), not the one we meant to give it.
    """
    try:
        done = subprocess.run(  # noqa: S603 - a list argv, no shell
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        # `run` has killed it; what it printed before that is on the exception.
        partial = exc.output.decode("utf-8", "replace") if exc.output else ""
        note = f"timed out after {timeout_s:g} s and was killed"
        return FfmpegRun(tuple(str(a) for a in exc.cmd), None, partial, note)
    except OSError as exc:
        return FfmpegRun(tuple(argv), None, "", f"could not start: {exc}")
    output = done.stdout.decode("utf-8", "replace") if done.stdout else ""
    return FfmpegRun(tuple(str(a) for a in done.args), done.returncode, output)


def _copy_png(shot: Shot, source: Path, staging: Path) -> ShotResult:
    """A still or desktop shot: the source checked to be a PNG, then copied."""
    if not source.is_file():
        return ShotResult(shot, "missing", f"no file at {source}")
    if not _starts_with(source, (_PNG_SIGNATURE,)):
        return ShotResult(shot, "failed", f"{source} is not a PNG")
    target = staging / shot.file_name
    try:
        shutil.copyfile(source, target)
        size = target.stat().st_size
    except OSError as exc:
        return ShotResult(shot, "failed", f"{source} could not be copied: {exc}")
    return ShotResult(shot, "built", f"from {source}", size)


def _check_burst(shot: Shot, run_dir: Path) -> ShotResult | tuple[int, int]:
    """``(frames, fps)`` when the manifest and the frames are complete, else why not.

    Each refusal quotes the manifest's line, so the reader sees what the rig wrote.
    """
    path = run_dir / f"{shot.stem}-frames.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ShotResult(shot, "missing", f"no manifest at {path}")
    except (OSError, UnicodeDecodeError) as exc:
        return ShotResult(shot, "failed", f"{path} could not be read: {exc}")
    manifest = parse_manifest(text)
    first = bounded_chars(
        text.splitlines()[0] if text.strip() else "(empty)", head=300, tail=100
    )
    if manifest is None or manifest.name != shot.stem:
        return ShotResult(shot, "failed", f"not a manifest of {shot.stem}: {first}")
    # A lost frame is a jump in the loop. Refused, never papered over: re-record.
    if manifest.lost:
        named = "; ".join(manifest.rest) or "no frame named"
        why = f"the burst lost {manifest.lost} frame(s): {first} ({named})"
        return ShotResult(shot, "failed", why)
    if manifest.taken < 1 or manifest.taken != manifest.asked:
        return ShotResult(shot, "failed", f"an incomplete burst: {first}")
    # The manifest gives the interval; `record` made it round(1000 / fps).
    fps = round(1000 / manifest.interval_ms) if manifest.interval_ms else 0
    if not 1 <= fps <= RECORD_MAX_FPS:
        why = f"{fps} fps is outside 1 to {RECORD_MAX_FPS}: {first}"
        return ShotResult(shot, "failed", why)
    gap = _frame_problem(run_dir, shot.stem, manifest.taken)
    return ShotResult(shot, "failed", gap) if gap else (manifest.taken, fps)


def _build_loop(
    shot: Shot, run_dir: Path, work: Path, ffmpeg: str, timeout_s: float
) -> ShotResult:
    """A loop: the burst checked, then made into a GIF in ``work/out`` by ffmpeg.

    Two passes, because a GIF holds at most 256 colours: the first builds a palette
    from the frames themselves (``stats_mode=diff`` favours the pixels that change,
    which is the motion the loop is there to show), the second draws every frame
    with it. ``-nostdin`` stops ffmpeg waiting on the terminal for a key; ``-y``
    overwrites in the temporary folder; ``-loop 0`` loops the GIF forever.
    """
    checked = _check_burst(shot, run_dir)
    if isinstance(checked, ShotResult):
        return checked
    count, fps = checked
    frames = str(run_dir / f"{shot.stem}-%04d.png")
    palette = str(work / "scratch" / f"{shot.stem}-palette.png")
    gif = work / "out" / shot.file_name
    head = [ffmpeg, "-nostdin", "-y", "-framerate", str(fps), "-i", frames]
    passes = (
        ("palette", [*head, "-vf", "palettegen=stats_mode=diff", palette]),
        ("gif", [*head, "-i", palette, "-lavfi", "paletteuse", "-loop", "0", str(gif)]),
    )
    runs: list[FfmpegRun] = []
    for label, argv in passes:
        runs.append(run := _run_ffmpeg(argv, timeout_s))
        if run.exit_code != 0:
            said = run.note if run.exit_code is None else f"exited {run.exit_code}"
            return ShotResult(shot, "failed", f"ffmpeg ({label} pass) {said}", 0, runs)
    # An exit of 0 is ffmpeg's word; the file's first bytes are the evidence.
    if not _starts_with(gif, _GIF_SIGNATURES):
        why = f"ffmpeg exited 0 but {gif.name} is not a GIF"
        return ShotResult(shot, "failed", why, 0, runs)
    detail = f"{count} frames at {fps} fps, from {frames}"
    return ShotResult(shot, "built", detail, gif.stat().st_size, runs)


def build_media(
    run_dir: Path,
    *,
    desktop_dir: Path | None,
    out_dir: Path,
    ffmpeg: str,
    timeout_s: float = FFMPEG_TIMEOUT_S,
    shots: tuple[Shot, ...] = getting_started.SHOTS,
    budget_bytes: int | None = getting_started.IMAGE_BUDGET_BYTES,
) -> MediaReport:
    """Build every shot in a temporary folder, then move them all into ``out_dir``,
    or none of them. ``desktop_dir=None`` reads the desktop shots from the run."""
    desktop = run_dir if desktop_dir is None else desktop_dir
    report = MediaReport([], out_dir, budget_bytes)
    with tempfile.TemporaryDirectory(prefix="walkthrough-media-") as temporary:
        work = Path(temporary)
        (work / "out").mkdir()
        (work / "scratch").mkdir()
        for shot in shots:
            if shot.kind == "loop":
                result = _build_loop(shot, run_dir, work, ffmpeg, timeout_s)
            else:
                folder = desktop if shot.kind == "desktop" else run_dir
                result = _copy_png(shot, folder / f"{shot.stem}.png", work / "out")
            if result.state != "built":
                log.warning("%s %s: %s", shot.file_name, result.state, result.detail)
            report.results.append(result)
        report.total_bytes = sum(r.size for r in report.results)
        if budget_bytes is not None and report.total_bytes > budget_bytes:
            report.problem = (
                f"{report.total_bytes:,} bytes is over the budget of "
                f"{budget_bytes:,} bytes"
            )
            log.warning("%s", report.problem)
        if all(r.state == "built" for r in report.results) and not report.problem:
            _install(report, work / "out")
    return report


def _install(report: MediaReport, staging: Path) -> None:
    """Move every built file into the out folder, over any older copy.

    The decision is all or nothing (nothing moves unless everything built); the
    move is one file at a time, so a disk failing part way is reported with how far
    it got, and never as a success.
    """
    moved = 0
    try:
        report.out_dir.mkdir(parents=True, exist_ok=True)
        for result in report.results:
            name = result.shot.file_name
            shutil.move(staging / name, report.out_dir / name)
            moved += 1
    except OSError as exc:
        report.problem = (
            f"the move stopped after {moved} of {len(report.results)}: {exc}"
        )
        log.error("%s", report.problem)
        return
    report.installed = True


def render(report: MediaReport) -> str:
    """The report as text: one line per shot, and each failure's ffmpeg calls whole."""
    lines: list[str] = []
    for r in report.results:
        lines.append(f"{r.state:<8}{r.shot.file_name}: {r.detail}")
        for run in r.runs if r.state != "built" else []:
            code = "never exited" if run.exit_code is None else f"exit {run.exit_code}"
            lines.append(f"    {code}: {shlex.join(run.argv)}")
            if run.note:
                lines.append(f"    {run.note}")
            lines.append(f"    its output, {len(run.output)} character(s):")
            shown = bounded_chars(run.output, head=_OUTPUT_HEAD, tail=_OUTPUT_TAIL)
            lines.extend(f"      {line}" for line in shown.splitlines() or ["(none)"])
    if report.budget_bytes is None:
        budget = "the budget is undecided (KDD-42 W7), so it was not checked"
    elif report.total_bytes > report.budget_bytes:
        budget = f"OVER the budget of {report.budget_bytes:,} bytes"
    else:
        budget = f"within the budget of {report.budget_bytes:,} bytes"
    lines.append(f"total: {report.total_bytes:,} bytes; {budget}")
    built = sum(r.state == "built" for r in report.results)
    where = "moved into" if report.installed else "NOTHING was written to"
    lines.append(f"{built} of {len(report.results)} built; {where} {report.out_dir}")
    if report.problem:
        lines.append(f"not moved in: {report.problem}")
    return "\n".join(lines) + "\n"


def check_inputs(
    run_dir: Path, desktop_dir: Path | None, out_dir: Path, ffmpeg: str | None
) -> tuple[str, list[str]]:
    """The resolved ffmpeg, and every argument refused, before anything runs."""
    problems: list[str] = []
    for label, folder in (("--run", run_dir), ("--desktop", desktop_dir)):
        if folder is not None and not folder.is_dir():
            problems.append(f"{label} {folder} is not a folder")
    # ffmpeg reads a `%` in an input path as the start of a frame-number pattern.
    if "%" in str(run_dir):
        problems.append(f"--run {run_dir} contains '%', which ffmpeg would misread")
    resolved = shutil.which(ffmpeg) if ffmpeg else None
    if resolved is None:
        problems.append(f"--ffmpeg {ffmpeg or '(none on PATH)'} is not an executable")
    # The out folder must be one, or creatable inside the nearest folder that exists.
    existing = next((p for p in (out_dir, *out_dir.parents) if p.exists()), None)
    if existing is None or not existing.is_dir() or not os.access(existing, os.W_OK):
        problems.append(f"--out {out_dir} is not a folder that can be written")
    return resolved or "", problems


def _dry_run(run_dir: Path, desktop_dir: Path | None) -> tuple[str, bool]:
    """Each file that would be built and its input, and whether every input is
    there. Reads only: it writes nothing and runs nothing."""
    lines: list[str] = []
    complete = True
    for shot in getting_started.SHOTS:
        folder = desktop_dir if shot.kind == "desktop" and desktop_dir else run_dir
        name = f"{shot.stem}-frames.txt" if shot.kind == "loop" else f"{shot.stem}.png"
        present = (folder / name).is_file()
        complete = complete and present
        state = "present" if present else "MISSING"
        lines.append(f"{shot.file_name} <- {folder / name} ({state})")
    return "\n".join(lines) + "\n", complete


def main(argv: list[str] | None = None) -> int:
    """The command line: check the arguments, then list, or build and report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="the run folder")
    parser.add_argument(
        "--desktop", type=Path, help="the folder of Spectacle shots (default: --run)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=getting_started.IMAGES_DIR,
        help="where the pictures go (default: the guide's images folder)",
    )
    parser.add_argument(
        "--ffmpeg", default=shutil.which("ffmpeg"), help="default: ffmpeg on PATH"
    )
    parser.add_argument("--dry-run", action="store_true", help="list; write nothing")
    args = parser.parse_args(argv)
    # Refusals and failures go to stderr through `logging`; the report to stdout.
    logging.basicConfig(format="%(levelname)s: %(message)s")
    ffmpeg, problems = check_inputs(args.run, args.desktop, args.out, args.ffmpeg)
    for problem in problems:
        log.error("refused: %s", problem)
    if problems:
        return 2
    if args.dry_run:
        text, complete = _dry_run(args.run, args.desktop)
        sys.stdout.write(text)
        return 0 if complete else 1
    report = build_media(
        args.run, desktop_dir=args.desktop, out_dir=args.out, ffmpeg=ffmpeg
    )
    sys.stdout.write(render(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
