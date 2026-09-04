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
import shlex
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

#: cyanrip's diagnostics-record flag, which this module is the **only** caller of.
#:
#: Named rather than inlined so `scripts/emit_dependency_contract.py` can *derive*
#: it. Our published half of the seam has a section headed "Flags we pass you",
#: generated from the rip argv builder plus the version and `--verify-log` probes —
#: and this flag was outside that population, so the contract we handed the fork
#: listed 18 flags and omitted one we really send. Found 2026-08-21, while checking
#: a round-12 claim that turned on which document a schema number belonged to;
#: nothing in the fork's contract describes the `-j` record either, so the surface
#: was undocumented from both ends.
#:
#: That generator's own comment says *"The rip is not the only thing we run. Every
#: invocation we make is part of the argv surface"* — this is the fourth invocation
#: shape, and the third time that exact blind spot has been recorded there. A rule
#: stated one screen above the population it does not cover is not enforcement.
DIAGNOSTICS_FLAG: Final[str] = "-j"


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


def _rip_was_cancelled(album_dir: Path) -> bool:
    """Whether this rip's own report says it was cancelled. Never raises.

    Read off the artifact rather than inferred from the log's shape, because
    "the log has no tracks" is the very thing we are trying to explain and
    explaining it with itself would be circular.

    **Two independent witnesses**, either of which is sufficient: the report's
    ``outcome.status`` and an issue coded ``rip_cancelled``. One field could be
    renamed by a schema change and quietly turn this check into "never
    cancelled", which would restore the false FAIL without anything failing to
    announce it. Both are written by the same code path today, so this is
    redundancy against future drift, not against present disagreement.

    Returns False when there is no report, it cannot be read, or it does not say
    cancelled — the caller treats False as "no excuse for an empty parse", which
    is the fail-closed direction.
    """
    import json

    for report in sorted(album_dir.glob("*.platterpus.json")):
        try:
            data = json.loads(report.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        outcome = data.get("outcome")
        if isinstance(outcome, dict) and outcome.get("status") == "cancelled":
            return True
        issues = data.get("issues")
        if isinstance(issues, list) and any(
            isinstance(issue, dict) and issue.get("code") == "rip_cancelled"
            for issue in issues
        ):
            return True
    return False


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
        # A PLATTERPUS template, not a cyanrip one. `_build_rip_argv` runs this
        # through `scheme_from_template`, which translates our `%`-tokens into
        # cyanrip's `{}` ones **and neutralises literal braces by turning them
        # into parens**. Handing it `"{track} - {title}"` — already in cyanrip's
        # language — therefore produced `-F "(track) - (title)"`, a naming scheme
        # no real rip has ever sent, in the function whose docstring promises
        # "the argv a real rip would send" (found 2026-08-24). `%t - %n` is the
        # default preset's file part (`naming.PRESETS[0]`), so this now composes
        # what the GUI actually holds.
        track_template="%t - %n",
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

    full = [binary, DIAGNOSTICS_FLAG, str(record), *argv]
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

    # EVERY flag, compared as a TOKEN. Both halves of that were wrong until
    # 2026-08-24, and the verdict text claimed neither.
    #
    #   * It checked FOUR flags — `-Z -l -N -s` — of the 15 the builder emits,
    #     and then reported "every flag we composed arrived intact". Unchecked
    #     were `-T` (the sanitisation mode whose absence cost a finished 14-track
    #     archival rip five days earlier), `-G`, `-a`, `-t`, `-c`, `-F`, `-o`,
    #     `-r`, `-d` and `--consumer`. A transport that dropped any of them
    #     reported OK.
    #   * `flag not in received` was a SUBSTRING test against the whole
    #     invocation string, so `-s` is satisfied by any path containing `-s` —
    #     and the invocation embeds an operator-supplied output directory. A rig
    #     session run into `~/rig-session/` passes the `-s` check with the real
    #     `-s 667` absent.
    #
    # That is `CLAUDE.md`'s "can it be satisfied by the wrong thing?", in the one
    # check whose stated purpose is settling an argv question for the fork
    # without spending a disc pass. A check that passes for the wrong reason is
    # worse than one that fails, because a failure gets investigated.
    try:
        received_tokens = shlex.split(received)
    except ValueError as exc:
        # Unbalanced quoting in their record. NOT a pass: we cannot compare, and
        # "could not compare" is a different answer from "they agree".
        manifest.add(
            Result(
                FAIL,
                "argv/integrity",
                f"the binary's own record of its invocation could not be split "
                f"into tokens ({exc}), so nothing could be compared against the "
                f"{len(argv)} args we composed. received: {received[:400]}",
                art,
            )
        )
        return
    # Flags only. Values may legitimately be re-quoted between our list and their
    # rendering of it; a flag may not change. `argv[0]` is excluded — it is the
    # path we spawned, and they record their own resolved binary path.
    composed_flags = [tok for tok in full[1:] if tok.startswith("-")]
    received_flags = [tok for tok in received_tokens if tok.startswith("-")]
    missing: list[str] = []
    remaining = list(received_flags)
    for flag in composed_flags:
        if flag in remaining:
            remaining.remove(flag)  # count repeats (`-t` appears once per track)
        else:
            missing.append(flag)
    if missing:
        manifest.add(
            Result(
                FAIL,
                "argv/integrity",
                f"composed {len(argv)} args carrying {len(composed_flags)} flag "
                f"token(s); the binary did NOT receive {missing}. "
                f"received: {received[:400]}",
                art,
            )
        )
        return
    manifest.add(
        Result(
            OK,
            "argv/integrity",
            f"all {len(composed_flags)} flag token(s) we composed arrived intact "
            f"({' '.join(sorted(set(composed_flags)))}) in the binary's own record "
            f"of the {len(argv)} args we sent. Flag tokens are compared, not "
            f"values: a value may be re-quoted in their rendering, a flag may not "
            f"change",
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
        # FAIL, not SKIP. `SKIP` is the honest answer when nothing was given to
        # look at (the branch above). "I was given a folder and it holds no
        # ripper log" is a FINDING — and it has to be graded, because
        # `Manifest.failed` is `any(status == FAIL)` and the exit code is the
        # ONLY grade section G gets. G is ARCHIVAL for one stated reason: "the
        # log *is* the provenance record". A missing log passing as 0 is that
        # section satisfied by finding nothing.
        manifest.add(
            Result(
                FAIL,
                "handshake/note",
                f"no ripper log under {album_dir} — the folder exists and holds "
                "no log, so there is no provenance record for this rip",
            )
        )
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
        # FAIL, not SKIP — same reasoning as `handshake/note` above, and this is
        # the row the acceptance script's section G actually leans on.
        manifest.add(
            Result(
                FAIL,
                "parser/log",
                f"no ripper log under {album_dir} — nothing to parse, so this "
                "check reports the state it found rather than skipping quietly",
            )
        )
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
    # BEFORE the zero-track branch, and that placement is the whole point.
    #
    # `_report_interruption` describes a rip that was STOPPED, and a rip stopped
    # early is precisely the rip whose log ends at its `Tracks:` header with
    # nothing under it — so a call placed after the early return below would be
    # unreachable for every log it exists to describe. Written here after putting
    # it there first: `CLAUDE.md`'s *did I check the preconditions where the thing
    # HAPPENS, or where it was scheduled?*, with an early return as the deferral.
    _report_paranoia_scope(manifest, parsed)
    _report_interruption(manifest, parsed)
    tracks = len(getattr(parsed, "tracks", ()) or ())
    if tracks == 0:
        # THE FLOOR IS RIGHT; ITS SUBJECT WAS NOT CHECKED.
        #
        # "A parse that finds nothing is not a parse that found nothing wrong" is
        # the correct instinct (CLAUDE.md: *can this check be satisfied by finding
        # nothing?*) and it stays. But a zero-track parse has two causes, and only
        # one of them is a defect:
        #
        #   * the parser broke, or their log format moved  -> FAIL, as before
        #   * the rip was CANCELLED before any track finished -> there is no track
        #     record to find, and saying "ZERO tracks" about it is a FAIL for the
        #     wrong reason
        #
        # Measured, 2026-08-20: a cancel landed 91s into track 1 of a paranoia-max
        # rip, so cyanrip's log legitimately ended at its `Tracks:` header with
        # nothing under it. `rig-check` called that a parser failure. It was one of
        # only two failures in a 60-step run, and it was noise — and noise in a
        # FAIL is expensive here, because a FAIL that turns out to be nothing
        # teaches the reader to discount the next one.
        #
        # THE SKIP REQUIRES POSITIVE EVIDENCE, never an assumption: we only excuse
        # the empty parse when the rip's own report says it was cancelled. Absent
        # that evidence this stays a FAIL, so a real parser regression on a real
        # rip can never hide behind "maybe it was cancelled" (tri-state, as
        # everywhere else: not-determined is not a pass).
        cancelled = _rip_was_cancelled(album_dir)
        if cancelled:
            manifest.add(
                Result(
                    SKIP,
                    "parser/log",
                    f"{logs[-1].name} parsed to zero tracks, and this rip's own "
                    f"report says it was CANCELLED — the ripper was stopped before "
                    f"any track record was written, so there is nothing for the "
                    f"parser to find and this log is not a subject for the check. "
                    f"Rip a disc to completion to exercise it.",
                )
            )
            return
        manifest.add(
            Result(
                FAIL,
                "parser/log",
                f"parsed {logs[-1].name} to ZERO tracks — a parse that finds "
                f"nothing is not a parse that found nothing wrong. This rip's "
                f"report does not say it was cancelled, so an empty parse is "
                f"unexplained.",
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
            cache
            or (
                "no Cache probe: line in this log, and there never will be one — "
                "`-x` is not in the rip argv builder at all, so no Platterpus rip "
                "probes the cache. The probe is a separate `cyanrip -N -x -I` "
                "invocation (round 14 T3), whose exact argv, exit code and complete "
                "output are recorded in the SCRIPT REPORT and transcript, not here. "
                "Look there, not for an absence in this manifest."
            ),
        )
    )


def _report_paranoia_scope(manifest: Manifest, parsed: object) -> None:
    """Surface the per-track/disc paranoia relationship, for round 14's T1.

    **Read off the already-parsed object; nothing here re-reads the log.** Both
    figures have been parsed since 0.6.24 and neither reached the manifest, which
    is `CLAUDE.md`'s *a diagnosis we captured but never showed the user is the same
    bug from their side* — and it bites hardest exactly here, because this manifest
    is what the acceptance run sends the fork as evidence.

    Why the two numbers and not one: under ``-Z`` a track's own counter is the
    **last** pass while the disc total sums **every** pass. The fork's round-14
    lap 1 §D added a ``Scope:`` line saying so after we broke a five-round-old
    claim that they summed — which had survived because every artifact it was
    checked against read each track exactly once, the one condition that forces the
    sum arithmetically. A disc that converges on the first read cannot distinguish
    the two readings, so this row says which case the run got rather than printing
    numbers the reader has to interpret.

    **The invariant is an INEQUALITY, and a ratio is not it.** ``sum(per-track) <=
    disc total``, with equality exactly when every track was read once. The
    tempting ``disc == passes x sum`` holds on the fork's synthetic fixture *by
    construction* — every pass there does identical work — and will not hold on
    media, because re-reads exist precisely when passes differ. Their round-14
    acceptance spec asks in as many words whether anything here encodes that
    ratio; it does not, and the first draft of this function did. The multiple is
    reported as an observation, never as the property, and only the ``<=`` is
    graded.
    """
    tracks = getattr(parsed, "tracks", ()) or ()
    per_track = 0
    scoped = 0
    for track in tracks:
        per_track += sum((getattr(track, "paranoia_counts", None) or {}).values())
        if getattr(track, "paranoia_scope", None):
            scoped += 1
    disc = sum((getattr(parsed, "paranoia_counts", None) or {}).values())
    if per_track == 0 and disc == 0:
        manifest.add(
            Result(
                INFO,
                "parser/paranoia",
                "this log carries no paranoia counters at all — not a finding on "
                "its own (a clean read of a clean disc reports none), but it means "
                "the per-track/disc relationship is untested by this rip",
            )
        )
        return
    exercised = "YES" if scoped else "no"
    common = (
        f"per-track counters sum to {per_track}; the disc block totals {disc}. "
        f"Scope: line present on {scoped} of {len(tracks)} track(s) — secure "
        f"re-read genuinely exercised: {exercised}"
    )
    if per_track > disc:
        # THE ONLY GRADED HALF. `sum <= disc` is the fork's published invariant and
        # it cannot be violated by any amount of re-reading, so a violation is a
        # contract break rather than a disc property — the one thing here worth
        # failing a run over.
        manifest.add(
            Result(
                FAIL,
                "parser/paranoia",
                f"{common}. The per-track sum EXCEEDS the disc total, which the "
                f"provider contract says is impossible: the disc block sums every "
                f"pass and the per-track figures are one pass each, so the sum can "
                f"only ever be less than or equal to it.",
            )
        )
        return
    # The multiple is an OBSERVATION and is worded as one. It equals the pass count
    # only on a fixture where every pass does identical work; on media it will not,
    # and a reader who takes it for the pass count will mis-read a correct rip.
    if per_track and disc % per_track == 0 and disc != per_track:
        note = f" (disc total is {disc // per_track}x the sum on this rip)"
    else:
        note = ""
    manifest.add(Result(INFO, "parser/paranoia", f"{common}{note}"))


def _report_interruption(manifest: Manifest, parsed: object) -> None:
    """Surface ``Interrupted at:``, for round 14's T4. Tri-state, never a pass.

    The fork added this line at our round-12 ask and we did not parse it for a
    round; we parse it now and it still reached no artifact anyone sends anywhere.
    A rip that completed has no such line and **that is the ordinary case**, so the
    absence is reported as an absence rather than graded — the check that matters
    is whether a rip we *interrupted on hardware* produced one, which only the
    operator's own cancel step can create.
    """
    where = getattr(parsed, "interrupted_at", None)
    completed = getattr(parsed, "rip_completed", None)
    if where:
        manifest.add(
            Result(
                INFO,
                "parser/interrupted",
                f"the ripper recorded where it stopped: {where!r} "
                f"(rip_completed={completed!r})",
            )
        )
        return
    manifest.add(
        Result(
            INFO,
            "parser/interrupted",
            f"no 'Interrupted at:' line in this log (rip_completed={completed!r}) "
            f"— expected for a rip that ran to the end; only a cancelled or killed "
            f"rip produces one",
        )
    )


def _discover_album_dir(manifest: Manifest) -> Path | None:
    """The folder holding the newest rip on this machine, or ``None``.

    Reuses :mod:`platterpus.rip_compare`'s discovery — the same "which rip did
    the operator just make" rule ``--compare`` uses — rather than re-deriving it
    here, so the two cannot disagree about which rip is current.

    Never raises: discovery is a convenience, and a rig session must not die
    because a configured output folder has gone missing. Every outcome is
    recorded, including the failures, because *"no album folder"* and *"I picked
    one for you"* are different facts about the run.
    """
    try:
        from platterpus import rip_compare

        report = rip_compare.newest_report(rip_compare.default_report_roots())
    except Exception as exc:  # noqa: BLE001 — discovery must never end the session
        manifest.add(Result(INFO, "album/discovery", f"could not look: {exc}"))
        return None
    if report is None:
        manifest.add(
            Result(
                INFO,
                "album/discovery",
                "no .platterpus.json found under the output/library folders; "
                "the log checks below will SKIP",
            )
        )
        return None
    found = report.parent
    manifest.add(Result(INFO, "album/discovery", f"newest rip found: {found}"))
    return found


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

    # NO ALBUM FOLDER? FIND IT. The rig script used to carry the line
    # "Replace the path with the folder the rip actually wrote" — a hand-edit in
    # a written procedure, which by the maintainer's 2026-08-11 directive is a
    # thing the software was supposed to do. The operator has just ripped a disc;
    # which folder that landed in is a question this program can answer and they
    # should not have to.
    #
    # Discovery is only a DEFAULT: an explicit path always wins, because a rig
    # session may deliberately point at an older rip. And it is announced in the
    # manifest either way — a check that silently chose its own subject would let
    # a reader attribute one rip's log to another.
    if album_dir is None:
        album_dir = _discover_album_dir(manifest)

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
