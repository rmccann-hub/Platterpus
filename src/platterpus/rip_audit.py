"""Audit a whole library of finished rips, without a CD or a re-rip.

The v0.6.1 hardware test plan was a checklist of things to open and read by
hand, and the maintainer's response was the correct one: *"either have them done
by the application or give me a command to do all of it at once."* A checklist a
human executes is a checklist a human skips, and every question on it is
answerable from artifacts already sitting on disk.

So this walks a rips folder and answers them all:

* **Which cyanrip built each rip** — fork, upstream, or not determined. The
  version number cannot tell, because the fork tracks upstream versions.
* **Did the rip finish**, according to the ripper's own footer rather than our
  count of how many tracks its log happened to mention.
* **Pre-gap provenance actually observed** — including whether the fork's
  sub-channel path has *ever* successfully run on real media, which as of this
  release it has not, anywhere.
* **Which disc of a multi-disc release** the tags came from, and whether that
  was determined or guessed.
* **Do the audio files the log claims actually exist and have bytes** — the
  check the fork's Q9 measurement made necessary (see :func:`_audit_files`).
* **What failed, in the ripper's own words**, with its exit code and the exact
  command line.

Read-only. It opens files and prints; it never writes, moves, deletes or
re-rips. Safe to run against a live library.

Never raises on a bad artifact: a library will contain half-written JSON from an
interrupted rip, and an auditor that dies on the first one is useless precisely
when it is needed. Anything unreadable is *reported* as unreadable.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

#: A FLAC smaller than this is not plausibly a track. The fork measured that a
#: killed rip leaves **0-byte** files even for tracks its log reports complete
#: (handshake round 4, Q9) — encoding runs on a separate thread behind a queue,
#: so the log record and the audio have independent durability. A few hundred
#: bytes is header-only; a real track is megabytes.
MIN_PLAUSIBLE_TRACK_BYTES: int = 4096

#: Version of the embedded `self_check` block's shape. Bumped when its keys
#: change, so a consumer can tell an old report from a new one — separate from
#: the report's own schema version, because checks are added far more often
#: than the report is restructured.
SELF_CHECK_SCHEMA: int = 1

#: Marks a finding the user should act on, versus one that is merely reported.
LEVEL_OK = "ok"
LEVEL_NOTE = "note"
LEVEL_WARN = "warn"


@dataclass
class Finding:
    """One thing worth saying about one album."""

    level: str
    text: str


@dataclass
class AlbumAudit:
    """Everything the audit could determine about one ripped album."""

    folder: Path
    title: str = ""
    findings: list[Finding] = field(default_factory=list)
    #: Facts the summary aggregates across the whole library.
    ripper_kind: str = ""
    pregap_sources: set[str] = field(default_factory=set)
    completed: bool | None = None
    empty_files: int = 0

    def add(self, level: str, text: str) -> None:
        self.findings.append(Finding(level, text))

    @property
    def worst(self) -> str:
        if any(f.level == LEVEL_WARN for f in self.findings):
            return LEVEL_WARN
        if any(f.level == LEVEL_NOTE for f in self.findings):
            return LEVEL_NOTE
        return LEVEL_OK


def _load_json(path: Path) -> dict[str, Any] | None:
    """Parse a report, or None. Never raises — half-written JSON is normal."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as exc:
        log.warning("unreadable report %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


def _audit_ripper(report: dict[str, Any], album: AlbumAudit) -> None:
    """Which cyanrip binary produced this rip."""
    rip = report.get("rip") or {}
    kind = rip.get("ripper_identity") or ""
    album.ripper_kind = str(kind)
    build = rip.get("ripper_build") or "(no build tag)"
    if kind == "fork":
        album.add(LEVEL_OK, f"ripped by the Platterpus fork ({build})")
    elif kind == "stock":
        album.add(
            LEVEL_NOTE,
            f"ripped by unmodified upstream cyanrip ({build}) — no pre-gap, "
            f"sample-peak or per-track timing rows",
        )
    else:
        # NOT "stock". An unrecognised tag is an absence of evidence.
        album.add(LEVEL_NOTE, f"ripper build not determined ({build})")


def _audit_completion(report: dict[str, Any], album: AlbumAudit) -> None:
    """Did the ripper say it finished, and does our own count agree?"""
    rip = report.get("rip") or {}
    outcome = report.get("outcome") or {}
    completeness = report.get("completeness") or {}

    completed = rip.get("rip_completed")
    album.completed = completed if isinstance(completed, bool) else None
    done = rip.get("rip_completed_tracks")
    total = rip.get("rip_completed_total")
    reason = rip.get("rip_completed_reason") or ""

    if completed is True:
        album.add(LEVEL_OK, f"rip completed ({done} of {total} tracks)")
    elif completed is False:
        detail = f" — {reason}" if reason else ""
        album.add(LEVEL_WARN, f"rip did NOT complete: {done} of {total} tracks{detail}")
    else:
        # The footer is absent. Per the fork (Q10) that is what a killed rip
        # looks like, and the cue cannot tell you — so say so rather than
        # treating a missing footer as a failure verdict.
        expected = completeness.get("tracks_expected")
        album.add(
            LEVEL_NOTE,
            "the ripper's completion footer is absent — the log was cut off, or "
            f"predates the fork pin (disc has {expected or '?'} tracks)",
        )

    status = outcome.get("status")
    if status and status != "success":
        hint = outcome.get("failure_hint") or "no diagnosis captured"
        album.add(LEVEL_WARN, f"outcome {status}: {hint}")
        code = outcome.get("ripper_exit_code")
        # `null` is a real answer — a child never reaped — and reads
        # differently from exit 0.
        album.add(
            LEVEL_NOTE,
            f"ripper exit code: {'not reaped (null)' if code is None else code}",
        )
        argv = outcome.get("ripper_command_display")
        if argv:
            album.add(LEVEL_NOTE, f"command: {argv}")


def _audit_medium(report: dict[str, Any], album: AlbumAudit) -> None:
    """Which disc of a multi-disc release these tags came from."""
    disc = report.get("disc") or {}
    basis = disc.get("medium_basis")
    if not basis:
        return
    if disc.get("medium_undetermined"):
        album.add(
            LEVEL_WARN,
            "could not determine which disc of a multi-disc release this is — "
            "the track titles may belong to a different disc. "
            + str(disc.get("medium_detail") or ""),
        )
    else:
        album.add(LEVEL_OK, f"disc identified by {basis}")


def _audit_pregaps(report: dict[str, Any], album: AlbumAudit) -> None:
    """What pre-gap provenance this rip actually observed.

    The headline is whether ``sub-channel`` ever appears. The fork's
    Q-subchannel path (upstream PR #115) has only ever executed its *failure*
    branch, because disc images always fall into ``unknown``. The first real
    occurrence anywhere will show up here.
    """
    for track in report.get("tracks") or []:
        if not isinstance(track, dict):
            continue
        source = track.get("pregap_source")
        if source:
            album.pregap_sources.add(str(source))
        state = track.get("pregap_state")
        if state == "unknown":
            album.pregap_sources.add(
                "unknown: " + str(track.get("pregap_unknown_reason") or "?")
            )


def _audit_files_check(report: dict[str, Any], album: AlbumAudit) -> None:
    """Do the audio files the log claims actually exist, with bytes in them?

    **This is the check the fork's Q9 measurement made necessary**, and it is
    the reason a "successful" track cannot be trusted on a cancelled rip:
    cyanrip encodes on a separate thread behind a queue, so it writes a track's
    log record — CRC and all — before the encoder has flushed. Kill the process
    and you get a 0-byte FLAC for a track the log calls complete. The log record
    and the audio have independent durability.

    So a track's presence in the log is *not* evidence its file is playable, and
    an app that reports such a track as verified is making a claim it cannot
    support. Nothing here deletes anything; it reports.
    """
    folder = album.folder
    try:
        flacs = sorted(folder.glob("*.flac"))
    except OSError as exc:
        album.add(LEVEL_NOTE, f"could not list audio files: {exc}")
        return

    if not flacs:
        # Not necessarily wrong — a WAV/MP3-only rip, or the audio was moved to
        # a library folder. Reported, not judged.
        album.add(LEVEL_NOTE, "no .flac files in this folder")
        return

    empty = []
    for path in flacs:
        try:
            size = path.stat().st_size
        except OSError:
            empty.append((path.name, -1))
            continue
        if size < MIN_PLAUSIBLE_TRACK_BYTES:
            empty.append((path.name, size))

    album.empty_files = len(empty)
    if not empty:
        album.add(LEVEL_OK, f"{len(flacs)} audio files, all with content")
        return

    names = ", ".join(f"{n} ({s} B)" for n, s in empty[:5])
    more = f" and {len(empty) - 5} more" if len(empty) > 5 else ""
    if (
        album.completed is False
        or (report.get("outcome") or {}).get("status") != "success"
    ):
        album.add(
            LEVEL_WARN,
            f"{len(empty)} empty/truncated audio file(s) after an incomplete rip "
            f"— EXPECTED, not corruption; the ripper logs a track before its "
            f"encoder flushes. Re-rip this disc. {names}{more}",
        )
    else:
        album.add(
            LEVEL_WARN,
            f"{len(empty)} empty/truncated audio file(s) in a rip that reports "
            f"SUCCESS — this should not happen; please report it. {names}{more}",
        )


def _audit_argv_agreement(report: dict[str, Any], album: AlbumAudit) -> None:
    """Do the argv we SENT and the argv the ripper says it RECEIVED agree?

    Both halves were captured in v0.6.1 and nothing compared them, which made
    the pair decorative: we asked the fork for its ``Invoked as:`` line
    (handshake A3) precisely so that a wrapper, a shell, or the Distrobox
    host-export mangling an argument would become visible — and a difference
    that nothing looks at is not visible.

    Compared as **sets of tokens**, not as strings. The two are legitimately
    formatted differently: we record the vector as spawned, the ripper prints a
    shell-ish line with quoting, and its argv[0] is the resolved absolute path
    behind the export while ours is the wrapper we invoked. Comparing the
    strings would cry wolf on every rip. Comparing the *flags* catches the case
    that matters — an argument that changed, vanished or appeared in transit.
    """
    outcome = report.get("outcome") or {}
    sent = outcome.get("ripper_argv")
    received = (report.get("rip") or {}).get("invoked_as")
    if not sent or not received:
        # Not a finding. An older rip, an upstream cyanrip that does not print
        # the line, or a rip that never launched — all legitimately silent.
        return

    def flags(tokens: list[str]) -> set[str]:
        return {tok for tok in tokens if re.fullmatch(r"-[A-Za-z]", tok)}

    sent_flags = flags([str(x) for x in sent])
    received_flags = flags(received.split())

    missing = sorted(sent_flags - received_flags)
    extra = sorted(received_flags - sent_flags)
    if not missing and not extra:
        album.add(LEVEL_OK, f"the ripper received the {len(sent_flags)} flags we sent")
        return
    parts = []
    if missing:
        parts.append(f"we sent but it did not receive: {' '.join(missing)}")
    if extra:
        parts.append(f"it received but we did not send: {' '.join(extra)}")
    album.add(
        LEVEL_WARN,
        "the command line changed in transit between Platterpus and cyanrip — "
        + "; ".join(parts)
        + ". Something between us (the host export wrapper, a shell) altered it.",
    )


def _audit_log_integrity(report: dict[str, Any], album: AlbumAudit) -> None:
    """Does the EAC-style log still match its own SHA-256 footer?

    We publish that checksum as an openly-verifiable integrity claim (KDD-28) —
    anyone can re-run `sha256sum` over the body. Publishing a claim and never
    checking it ourselves is the weaker half of a promise, so the audit checks
    it on the copy embedded in the report.

    Tri-state, because the verifier is: ``True`` matches, ``False`` means the
    log was altered after rendering, ``None`` means there is no Platterpus
    footer at all (a real EAC log, or output from before the checksum shipped).
    ``None`` is reported as a note, never as a pass — "no checksum to check" is
    not "the checksum checked out".
    """
    from platterpus.eac_log_export import verify_eac_style_log_checksum

    entry = (report.get("artifacts") or {}).get("eac_log") or {}
    text = entry.get("text")
    if not text:
        return
    if entry.get("truncated"):
        # A truncated copy cannot verify, and reporting it as a mismatch would
        # be a false accusation against an intact file.
        album.add(
            LEVEL_NOTE,
            "the embedded EAC log is truncated, so its checksum cannot be "
            "re-checked from the report (the file on disk is unaffected)",
        )
        return
    verdict = verify_eac_style_log_checksum(str(text))
    if verdict is True:
        album.add(LEVEL_OK, "the EAC-style log matches its own SHA-256 footer")
    elif verdict is False:
        album.add(
            LEVEL_WARN,
            "the EAC-style log does NOT match its own SHA-256 footer — it was "
            "altered after it was written. Its contents can no longer be "
            "treated as an archival record of this rip.",
        )
    else:
        album.add(LEVEL_NOTE, "the EAC-style log carries no Platterpus checksum footer")


def _audit_disc_identity(report: dict[str, Any], album: AlbumAudit) -> None:
    """Record the TOC-derived disc identity, so two rips can be compared.

    The MusicBrainz Disc ID and CDDB ID are computed from the physical TOC, so
    they identify the same *pressing* across re-rips independently of any
    metadata edit. Without them in the audit, "is this the same disc as last
    time?" needs the JSON opened by hand — which is the thing this command
    exists to avoid.
    """
    rip = report.get("rip") or {}
    disc_id = rip.get("musicbrainz_disc_id")
    cddb = rip.get("cddb_id")
    if disc_id or cddb:
        album.add(
            LEVEL_NOTE,
            f"disc identity — MusicBrainz {disc_id or '(none)'} / CDDB {cddb or '(none)'}",
        )


@dataclass(frozen=True)
class Check:
    """One named question the audit asks of a rip.

    A **registry entry**, not a hard-coded call. Adding a future check is one
    function plus one row in :data:`CHECKS` — it then runs automatically in
    every rip's embedded ``self_check`` block *and* in ``--audit-rips``, with
    no third place to remember. Removing one is equally local.

    ``needs_files`` marks a check that touches the filesystem. Those are the
    ones that can be *unavailable* rather than merely negative — the album
    folder may have been moved, or the report may be read on another machine —
    and an unavailable check is recorded as **skipped**, never as passed.
    """

    name: str
    question: str
    needs_files: bool
    run: Callable[[dict[str, Any], AlbumAudit], None]


#: Every check, in report order. This tuple IS the audit — nothing else
#: enumerates the checks, so the JSON block, the CLI report and the tests
#: cannot disagree about which ones exist.
CHECKS: tuple[Check, ...] = (
    Check("ripper_build", "Which cyanrip built this rip?", False, _audit_ripper),
    Check("completion", "Did the ripper say it finished?", False, _audit_completion),
    Check("medium", "Which disc of a multi-disc release?", False, _audit_medium),
    Check("pregap", "What pre-gap provenance was observed?", False, _audit_pregaps),
    Check(
        "audio_files",
        "Do the claimed audio files have bytes?",
        True,
        _audit_files_check,
    ),
    Check(
        "argv_agreement",
        "Did the ripper receive the command line we sent?",
        False,
        _audit_argv_agreement,
    ),
    Check(
        "log_integrity",
        "Does the EAC log still match its own checksum?",
        False,
        _audit_log_integrity,
    ),
    Check(
        "disc_identity",
        "Which physical pressing was this?",
        False,
        _audit_disc_identity,
    ),
)


def run_checks(
    report: dict[str, Any],
    folder: Path | None,
    album: AlbumAudit,
) -> tuple[list[str], list[str]]:
    """Run every registered check. Returns ``(ran, skipped)`` check names.

    A check that cannot run is **skipped and named**, never silently omitted:
    a report whose findings list is short because a check did not execute reads
    identically to one that is short because nothing was wrong, and this
    codebase has shipped that confusion three times.

    Never raises. A check that throws is recorded as a finding against itself,
    because an auditor that dies halfway through a library is worse than one
    that reports a broken check.
    """
    ran: list[str] = []
    skipped: list[str] = []
    for check in CHECKS:
        if check.needs_files and folder is None:
            skipped.append(check.name)
            continue
        try:
            check.run(report, album)
        except Exception as exc:  # noqa: BLE001 — a broken check must not stop the audit
            log.exception("audit check %s raised", check.name)
            album.add(LEVEL_NOTE, f"check '{check.name}' could not run: {exc}")
            skipped.append(check.name)
            continue
        ran.append(check.name)
    return ran, skipped


def self_check_block(report: dict[str, Any], folder: Path | None) -> dict[str, Any]:
    """The audit, as a JSON block to embed in the rip report itself.

    So every rip carries its own verdict at the moment it was written, and the
    user never has to remember to run anything. ``--audit-rips`` runs the same
    registry over a whole library later — same checks, same wording, because
    both go through :data:`CHECKS`.

    ``checks_skipped`` is populated rather than implied. "This check found
    nothing" and "this check never ran" are different facts.
    """
    album = AlbumAudit(folder=folder or Path("."))
    ran, skipped = run_checks(report, folder, album)
    return {
        "schema": SELF_CHECK_SCHEMA,
        "checks_run": ran,
        "checks_skipped": skipped,
        "worst": album.worst,
        "findings": [{"level": f.level, "text": f.text} for f in album.findings],
    }


def audit_album(report_path: Path) -> AlbumAudit:
    """Audit one album from its ``.platterpus.json``. Never raises."""
    folder = report_path.parent
    album = AlbumAudit(folder=folder)
    report = _load_json(report_path)
    if report is None:
        album.add(LEVEL_WARN, f"report is unreadable or not JSON: {report_path.name}")
        return album

    disc = report.get("disc") or {}
    rip = report.get("rip") or {}
    album.title = str(
        report.get("album") or disc.get("album") or rip.get("album") or folder.name
    )

    run_checks(report, folder, album)

    verdict = (report.get("verdict") or {}).get("message")
    if verdict:
        album.add(LEVEL_OK, str(verdict))
    return album


def find_reports(root: Path) -> list[Path]:
    """Every ``*.platterpus.json`` under ``root``, sorted. Never raises."""
    try:
        return sorted(root.rglob("*.platterpus.json"))
    except OSError as exc:
        log.warning("could not walk %s: %s", root, exc)
        return []


_ICON = {LEVEL_OK: "  ok  ", LEVEL_NOTE: " note ", LEVEL_WARN: " WARN "}


def render(audits: list[AlbumAudit], root: Path) -> str:
    """The whole report as text. Pure — takes audits, returns a string."""
    out: list[str] = [
        f"Platterpus rip audit — {root}",
        "=" * 72,
        "",
    ]
    if not audits:
        out += [
            "No .platterpus.json reports found.",
            "",
            "Every rip writes one beside its audio. If this folder holds rips made",
            "before reports existed, there is nothing to audit — re-rip to get one.",
        ]
        return "\n".join(out) + "\n"

    for album in audits:
        out.append(f"{album.title}")
        out.append(f"  {album.folder}")
        for finding in album.findings:
            out.append(f"  [{_ICON[finding.level]}] {finding.text}")
        out.append("")

    # --- the aggregate answers, which are the point of doing this in bulk ----
    out += ["=" * 72, "SUMMARY", ""]
    total = len(audits)
    kinds: dict[str, int] = {}
    for album in audits:
        kinds[album.ripper_kind or "unknown"] = (
            kinds.get(album.ripper_kind or "unknown", 0) + 1
        )
    out.append(f"albums audited: {total}")
    out.append(
        "  ripper: "
        + ", ".join(
            f"{n}× {k}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])
        )
    )

    incomplete = [a for a in audits if a.completed is False]
    unknown_completion = [a for a in audits if a.completed is None]
    out.append(f"  completed: {sum(1 for a in audits if a.completed is True)}")
    if incomplete:
        out.append(f"  DID NOT complete: {len(incomplete)} — re-rip these:")
        out += [f"      {a.title}" for a in incomplete]
    if unknown_completion:
        out.append(
            f"  completion not stated (older rip or cut-off log): {len(unknown_completion)}"
        )

    empties = [a for a in audits if a.empty_files]
    if empties:
        out.append(f"  albums with empty/truncated audio: {len(empties)}")
        out += [f"      {a.title} ({a.empty_files} file(s))" for a in empties]

    sources: set[str] = set()
    for album in audits:
        sources |= album.pregap_sources
    out.append("")
    out.append("pre-gap provenance seen across the library:")
    if sources:
        out += [f"  - {s}" for s in sorted(sources)]
    else:
        out.append("  - none reported (stock cyanrip, or no disc had a pre-gap)")

    # The headline result nobody has ever had.
    if any(s.startswith("sub-channel") for s in sources):
        out += [
            "",
            "  *** A SUB-CHANNEL pre-gap read SUCCEEDED. ***",
            "  As of v0.6.1 this path had never executed successfully anywhere —",
            "  disc images always fail into 'unknown'. This is new information;",
            "  please send the log for that album.",
        ]

    warns = [a for a in audits if a.worst == LEVEL_WARN]
    out += ["", f"albums needing attention: {len(warns)}"]
    out += [f"  - {a.title}" for a in warns]
    return "\n".join(out) + "\n"


def run_audit(root: Path) -> int:
    """Audit every rip under ``root``, print the report, return an exit code.

    ``0`` when nothing needs attention, ``1`` when something does. Never ``2`` —
    a library with problems in it is a successful audit, not a failed one.
    """
    audits = [audit_album(p) for p in find_reports(root)]
    print(render(audits, root), end="")
    return 1 if any(a.worst == LEVEL_WARN for a in audits) else 0
