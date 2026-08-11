"""Platterpus's half of the seam check — the interface the cyanrip fork asked for.

Their seam packet (2026-08-10 §4b) asked for
``platterpus-rig-check.py [--out DIR] [--album-dir DIR] [--device DEV]`` so the
two projects' checks compose into **one upload** rather than two piles. This is
that, shipped inside the package so an AppImage user needs no checkout, and
driven by ``--rig-session`` so an operator still runs one command.

**The contract, theirs, followed exactly:**

* every raw output under ``--out``, shared with their script;
* append to ``MANIFEST.txt``, never overwrite, as ``STATUS  name  detail``;
* four statuses and the distinction is the point — ``OK`` / ``FAIL`` / ``SKIP`` /
  ``INFO``. **SKIP means did not run**; a check that ran and found nothing is
  ``OK``; a measurement this script cannot judge is ``INFO``, never ``OK``. A
  reader who greps the status is entitled to believe it;
* exit non-zero **only** on ``FAIL``;
* read-only — nothing re-rips, re-encodes or writes into the library.

**The check that matters most is check 1**, and it is theirs: compose exactly the
argv a real rip would send, run it against a device that cannot open, and read
``invocation`` back out of cyanrip's own ``-j`` record. That compares what the
binary *received* against what we *composed* — which is the comparison
``argv_agreement`` does not make, and the one that settles an argv question
without spending a disc.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.rip_addendum import read_log_with_addendum

log = logging.getLogger(__name__)

#: The four statuses, and they are not interchangeable.
OK: Final[str] = "OK"
FAIL: Final[str] = "FAIL"
SKIP: Final[str] = "SKIP"
INFO: Final[str] = "INFO"

#: Bound on any single probe. A seam check must not become the thing that hangs.
PROBE_TIMEOUT_S: Final[float] = 120.0


@dataclass
class Result:
    """One line of the manifest."""

    status: str
    name: str
    detail: str
    artifact: str = ""

    def render(self) -> str:
        tail = f"  [{self.artifact}]" if self.artifact else ""
        return f"{self.status:<5} {self.name}  {self.detail}{tail}"


class Manifest:
    """Appends to ``MANIFEST.txt`` and remembers whether anything FAILed."""

    def __init__(self, out: Path, sink: Callable[[str], None] = print) -> None:
        self.out: Path = out
        self.path: Path = out / "MANIFEST.txt"
        self.results: list[Result] = []
        # Where the rendered lines go as they are produced. Defaults to the
        # terminal because that is where `--rig-check` runs; the script verb
        # passes a collector instead, so the same check can report into a script
        # transcript without a second implementation rendering it differently.
        self.sink: Callable[[str], None] = sink
        out.mkdir(parents=True, exist_ok=True)

    def add(self, result: Result) -> None:
        self.results.append(result)
        line = result.render()
        self.sink(line)
        # APPEND, never overwrite — their script writes into the same file, and a
        # truncating open would silently delete the other project's evidence.
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def write_artifact(self, name: str, text: str) -> str:
        """Drop raw output beside the manifest; return the filename for the row."""
        target = self.out / name
        try:
            target.write_text(text, encoding="utf-8", errors="replace")
        except OSError as exc:
            log.warning("could not write %s: %s", target, exc)
            return ""
        return name

    @property
    def failed(self) -> bool:
        return any(r.status == FAIL for r in self.results)


def _ripper_logs(album_dir: Path) -> list[Path]:
    """The cyanrip logs in a rip folder, oldest first.

    The EAC-compatible companion sits beside the real one and is a **different
    format**; parsing it as a cyanrip log finds nothing, and "found nothing" is
    indistinguishable from "the parser broke". Excluded by name rather than by
    hoping the sort order puts the right one last.
    """
    return [
        path
        for path in sorted(album_dir.glob("*.log"))
        if "EACcompatible" not in path.name
    ]


def _compose_reference_argv(binary: str, device: str, build_tag: str) -> list[str]:
    """The argv a real rip would send, built by the REAL builder.

    Not a hand-written approximation: it calls the same method the rip path
    calls, on the same class, so a flag that stops being emitted disappears from
    this check on the next run without anyone remembering to edit it. An
    approximation here would be a second description of the command line, which
    is the exact class of thing this check exists to catch.

    ``build_tag`` is passed through because ``--consumer`` is capability-gated on
    it: composing with an empty tag would silently drop a flag the real rip sends
    to this very binary, and the check would then be measuring a command line
    nobody runs.

    Returns the argv **without** ``argv[0]`` — the caller puts the binary back at
    the front along with the ``-j`` record path.
    """
    from platterpus.adapters.cyanrip_backend import CyanripImpl
    from platterpus.adapters.rip_backend import RipMetadata, TrackTag

    backend = CyanripImpl(binary_path=binary)
    metadata = RipMetadata(
        album_artist="Platterpus",
        album_title="Rig Check",
        year="2026",
        tracks=(TrackTag(number=1, title="One"), TrackTag(number=2, title="Two")),
    )
    argv = backend._build_rip_argv(  # noqa: SLF001 — deliberately the real builder
        device,
        unknown=False,
        cover_art="",
        max_retries=3,
        read_offset_override=667,
        track_template="{track} - {title}",
        metadata=metadata,
        secure_rerip_matches=3,
        only_tracks=(1, 2),
        disc_track_total=2,
        ripper_build_tag=build_tag,
    )
    return argv[1:]


def check_argv_reaches_the_binary(
    manifest: Manifest, binary: str, build_tag: str = ""
) -> None:
    """**Check 1 — theirs, and the one that needed no disc.**

    Compose a real rip's argv, run it against a device that cannot open, and read
    ``invocation`` back out of cyanrip's ``-j`` record. `Invoked as:` is built
    from raw ``argv``, so it reports what *arrived* rather than a reconstruction.

    A mismatch here means something between our composition and the binary is
    altering the command line — the question their §2.1 raised. An agreement means
    the transport is clean and any missing flag is a composition decision, which
    is a different conversation.
    """
    record = manifest.out / "argv-probe.json"
    try:
        argv = _compose_reference_argv(
            binary, "/nonexistent-platterpus-rig-check.cue", build_tag
        )
    except Exception as exc:  # noqa: BLE001 — a check must not crash the run
        manifest.add(
            Result(FAIL, "argv/compose", f"could not build a reference argv: {exc!r}")
        )
        return

    full = [binary, "-j", str(record), *argv]
    try:
        proc = subprocess.run(  # noqa: S603 — our own binary, no shell
            full,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        manifest.add(Result(FAIL, "argv/run", f"could not run the ripper: {exc!r}"))
        return

    art = manifest.write_artifact(
        "argv-probe-output.txt",
        f"argv: {' '.join(full)}\nexit: {proc.returncode}\n\n"
        + (proc.stdout or "")
        + (proc.stderr or ""),
    )

    if not record.is_file():
        # The run is EXPECTED to fail (the device cannot open); what must survive
        # is the -j record, which cyanrip writes from atexit.
        manifest.add(
            Result(
                FAIL,
                "argv/record",
                "cyanrip wrote no -j diagnostics record, so what it received "
                "cannot be read back — the check could not be performed",
                art,
            )
        )
        return

    try:
        received = str(json.loads(record.read_text(encoding="utf-8")).get("invocation"))
    except (OSError, ValueError, AttributeError) as exc:
        manifest.add(Result(FAIL, "argv/parse", f"unreadable -j record: {exc!r}", art))
        return

    missing = [flag for flag in ("-Z", "-l", "-N", "-s") if flag not in received]
    if missing:
        manifest.add(
            Result(
                FAIL,
                "argv/integrity",
                f"composed {len(argv)} args; the binary did NOT receive {missing}. "
                f"received: {received[:400]}",
                art,
            )
        )
        return
    manifest.add(
        Result(
            OK,
            "argv/integrity",
            f"every flag we composed arrived intact (-Z, -l, -N, -s present in the "
            f"binary's own record of {len(argv)} composed args)",
            art,
        )
    )


def check_ripper_identity(manifest: Manifest, binary: str) -> str:
    """Which build is installed, and is it one a channel publishes?

    Returns the installed build tag (``""`` when it could not be read), because
    the argv check needs it: ``--consumer`` is gated on the build, so composing a
    reference argv without it would measure a command line no rip ever sends.
    """
    from platterpus.deps import fork_source

    try:
        proc = subprocess.run(  # noqa: S603 — our own binary, no shell
            [binary, "-v"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        manifest.add(Result(FAIL, "ripper/version", f"could not run: {exc!r}"))
        return ""
    banner = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
    first = banner[0] if banner else ""
    art = manifest.write_artifact("ripper-version.txt", "\n".join(banner))
    if not first:
        manifest.add(Result(FAIL, "ripper/version", "no version banner", art))
        return ""
    manifest.add(Result(INFO, "ripper/version", first, art))

    # Tri-state: an unrecognised tag is NOT "unapproved", it is undetermined.
    from platterpus.handshake_approval import approve_ripper

    verdict = approve_ripper(first)
    status = OK if verdict.is_approved else INFO
    manifest.add(
        Result(status, "ripper/handshake", f"{verdict.verdict} — {verdict.detail}")
    )

    pinned = fork_source.FORK_PIN
    manifest.add(
        Result(
            INFO,
            "ripper/pin",
            f"this Platterpus pins {pinned}; the installed banner is above. A test "
            f"pin is expected to differ during an open round.",
        )
    )

    from platterpus.ripper_identity import identify_from_banner

    return identify_from_banner(first).build_tag


def check_handshake_note_transition(manifest: Manifest, album_dir: Path | None) -> None:
    """Does the newest rip's `Handshake:` line read as a closed round or an open one?

    Their §4b check 2. The beta emits ``round 8 lap 1 OPEN … NOT a released
    build``; every rip before this said ``round 7 lap NN``. Both shapes must be
    read correctly rather than one being the only one ever seen.
    """
    if album_dir is None or not album_dir.is_dir():
        manifest.add(
            Result(SKIP, "handshake/note", "no --album-dir given, so no log to read")
        )
        return
    logs = _ripper_logs(album_dir)
    if not logs:
        manifest.add(Result(SKIP, "handshake/note", f"no ripper log under {album_dir}"))
        return
    text = read_log_with_addendum(logs[-1])
    line = next(
        (ln.strip() for ln in text.splitlines() if ln.startswith("Handshake:")), ""
    )
    if not line:
        manifest.add(
            Result(
                INFO,
                "handshake/note",
                "the log carries no Handshake: line — stock upstream, or a build "
                "older than the note. Not a failure.",
            )
        )
        return
    lowered = line.casefold()
    shape = (
        "closed"
        if "closed" in lowered and "open" not in lowered
        else "OPEN"
        if "open" in lowered
        else "unrecognised"
    )
    manifest.add(Result(INFO, "handshake/note", f"{shape}: {line}"))


def check_parsers_against_the_log(manifest: Manifest, album_dir: Path | None) -> None:
    """Our parsers against whatever log is there — their §4b check 3.

    The golden reference moved (new `Cache probe:` wording, ten more fatal
    messages), so the parser must be run against real text rather than trusted.
    """
    if album_dir is None or not album_dir.is_dir():
        manifest.add(Result(SKIP, "parser/log", "no --album-dir given"))
        return
    logs = _ripper_logs(album_dir)
    if not logs:
        manifest.add(Result(SKIP, "parser/log", f"no ripper log under {album_dir}"))
        return
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    text = read_log_with_addendum(logs[-1])
    try:
        parsed = parse_cyanrip_log(text)
    except Exception as exc:  # noqa: BLE001 — parsers must never raise; prove it
        manifest.add(
            Result(
                FAIL, "parser/log", f"the parser RAISED, which it must never: {exc!r}"
            )
        )
        return
    tracks = len(getattr(parsed, "tracks", ()) or ())
    if tracks == 0:
        manifest.add(
            Result(
                FAIL,
                "parser/log",
                f"parsed {logs[-1].name} to ZERO tracks — a parse that finds "
                f"nothing is not a parse that found nothing wrong",
            )
        )
        return
    cache = next(
        (ln.strip() for ln in text.splitlines() if ln.startswith("Cache probe:")), ""
    )
    manifest.add(
        Result(OK, "parser/log", f"parsed {tracks} track(s) from {logs[-1].name}")
    )
    manifest.add(
        Result(
            INFO,
            "parser/cache-probe",
            cache or "no Cache probe: line in this log (the rip did not pass -x)",
        )
    )


def run_rig_check(
    out: Path,
    album_dir: Path | None = None,
    device: str | None = None,
    sink: Callable[[str], None] = print,
) -> int:
    """Run every check; return 0 unless something FAILed.

    ``sink`` receives each rendered manifest line as it is produced. It exists so
    the GUI script verb can collect the lines into its transcript while the
    terminal flag prints them, without a second copy of this function — the
    checks, their wording and their statuses stay in exactly one place.
    """
    from platterpus.paths import CYANRIP_BINARY_DEFAULT

    manifest = Manifest(out, sink=sink)
    binary = str(CYANRIP_BINARY_DEFAULT)

    from platterpus import __version__
    from platterpus.build_info import build_fingerprint

    manifest.add(
        Result(
            INFO, "platterpus/version", f"{__version__} (build {build_fingerprint()})"
        )
    )

    build_tag = check_ripper_identity(manifest, binary)
    check_argv_reaches_the_binary(manifest, binary, build_tag)
    check_handshake_note_transition(manifest, album_dir)
    check_parsers_against_the_log(manifest, album_dir)

    if device:
        manifest.add(
            Result(
                INFO,
                "device",
                f"{device} — the -x / -f / cd-paranoia passes are cyanrip's script's "
                f"job, deliberately not duplicated here",
            )
        )
    else:
        manifest.add(Result(SKIP, "device", "no --device given"))

    sink(f"manifest: {manifest.path}")
    return 1 if manifest.failed else 0
