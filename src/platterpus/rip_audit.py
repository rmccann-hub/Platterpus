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


def _ar_matched(block: Any) -> bool:
    """True when an AccurateRip variant block records an actual match.

    A block's *presence* is not a match — cyanrip prints a line for "not found,
    either a new pressing, or bad rip" too, and counting the line was how a track
    that matched nothing once got reported as an offset-variant match. Keyed on the
    result text, which is what the ripper actually said.
    """
    if not isinstance(block, dict):
        return False
    result = str(block.get("result") or "").casefold()
    if not result or "not found" in result:
        return False
    return "accurately ripped" in result or "matches accurip" in result


def _audit_handshake_note(report: dict[str, Any], album: AlbumAudit) -> None:
    """Do the ripper's **own** statement and *our* verdict agree about the round?

    **Two independent witnesses to one fact, which is why this is its own check.**
    ``ripper_handshake_approval`` is *our* verdict, computed by comparing the banner
    against the pin our record says a closed round approved.
    ``ripper_handshake_note`` is the *binary's own compiled-in sentence* about the
    round it was built from. Neither is derived from the other, so a disagreement is
    information that no amount of re-reading either one alone can produce.

    **The transition this exists to catch** (cyanrip fork's release-test request,
    2026-08-07): every rip ever made until the round-7 release carried

        Handshake:  round 7 lap 33 OPEN, verdict HOLD -- NOT a released build

    and the released build is the first to carry the closed/GO shape. Everything
    downstream of that line has only ever seen the "NOT a released build" form, and
    **the transition has never been exercised by anything**. A check that only ever
    saw one of two states has not been tested.

    Tri-state throughout: a build that emits no note at all is *not determined* (stock
    upstream has no such line), never a failure.
    """
    rip = report.get("rip") or {}
    note = str(rip.get("ripper_handshake_note") or "").strip()
    verdict = str(rip.get("ripper_handshake_approval") or "").strip()

    if not note:
        # Fork-only line. Absent means stock upstream, or a build predating it.
        album.add(
            LEVEL_NOTE,
            "the ripper stated no handshake note — that is stock upstream or a "
            "build older than the note, not evidence of an unreleased build",
        )
        return

    # Read off the note's own words. `closed` and `OPEN` are the two shapes the fork
    # emits; anything else is a third state we decline to interpret.
    lowered = note.casefold()
    says_open = "open" in lowered or "not a released build" in lowered
    says_closed = "closed" in lowered

    if says_open and not says_closed:
        album.add(
            LEVEL_WARN,
            f"the ripper says it was built from an OPEN round: {note!r} — rips from "
            f"this build carry that sentence permanently in their log",
        )
    elif says_closed and not says_open:
        album.add(LEVEL_OK, f"ripper built from a closed round: {note!r}")
    else:
        album.add(LEVEL_NOTE, f"handshake note not in a shape we recognise: {note!r}")

    # The cross-check, which is the actual point. Our verdict and their sentence are
    # about the same binary; if they disagree, one of the two is wrong and the
    # disagreement IS the bug report.
    if verdict == "approved" and says_open and not says_closed:
        album.add(
            LEVEL_WARN,
            "DISAGREEMENT: we score this ripper 'approved' while the binary itself "
            "says it was built from an open round. Our pin and their compiled-in "
            "note describe the same build and cannot both be right",
        )
    elif verdict == "unapproved" and says_closed and not says_open:
        album.add(
            LEVEL_NOTE,
            "the binary says it was built from a closed round, but it is not the "
            "build OUR record approved — expected when their release is ahead of "
            "our verification, and the reason the two witnesses are kept separate",
        )


def _audit_checksum_inventory(report: dict[str, Any], album: AlbumAudit) -> None:
    """**Count the checksum lines before comparing them.**

    The fork's own lesson, sent to us after we caught it (release-test request §2.1):
    their comparison used a pattern that returned **4** where the real inventory was
    **12**, because the per-track lines are spelled ``Accurip``, not ``AccurateRip``.
    Every one of the four it found matched, so the comparison passed — truthfully,
    about a third of the evidence. *A pattern returning a plausible number is worse
    than one returning nothing*, because a plausible number gets cited.

    So this check counts, states the denominator, and **has a floor**: it asserts an
    expected count derived from the track count rather than reporting whatever it
    happened to find. A check that can be satisfied by finding nothing is decoration
    (`CLAUDE.md`), and "all the CRCs I found agreed" is exactly that check.
    """
    tracks = report.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        album.add(
            LEVEL_NOTE,
            "no track list in the report — checksum inventory not determined",
        )
        return

    ripped = [t for t in tracks if isinstance(t, dict)]
    expected = len(ripped)
    if expected == 0:
        album.add(LEVEL_NOTE, "no track entries — checksum inventory not determined")
        return

    with_copy = sum(1 for t in ripped if str(t.get("copy_crc") or "").strip())
    accurip_kinds = ("v1", "v2", "offset_450")
    accurip_present = 0
    for track in ripped:
        ar = track.get("accuraterip")
        if not isinstance(ar, dict):
            continue
        accurip_present += sum(
            1 for kind in accurip_kinds if isinstance(ar.get(kind), dict)
        )

    # The copy CRC is the one every ripped track must have; a gap here is a real
    # hole in the evidence rather than a database miss.
    if with_copy == expected:
        album.add(
            LEVEL_OK,
            f"checksum inventory: {with_copy}/{expected} tracks carry a copy CRC",
        )
    else:
        album.add(
            LEVEL_WARN,
            f"checksum inventory INCOMPLETE: only {with_copy} of {expected} tracks "
            f"carry a copy CRC — {expected - with_copy} track(s) have no checksum, "
            f"so any 'all CRCs matched' claim covers less than the whole disc",
        )

    # **The denominator is NOT 3 × tracks, and getting that wrong is the same class
    # of error this check was written to catch** (cyanrip fork, seam packet
    # 2026-08-10 §2.3). `Accurip 450:` prints *only where v1 and v2 both missed*, so
    # a disc where everything matches can never produce more than 2 × tracks. The
    # first version of this check reported "29 of a possible 42" on a 14-track disc,
    # implying 13 absent results where exactly **one** track could have had a 450
    # line at all. A ceiling that cannot be reached is as misleading as a subset
    # reported as the whole — we published this check as a fix for under-counting and
    # it shipped over-stating instead.
    #
    # Their rule, which we adopt: `2 × tracks + (tracks where v1 AND v2 both missed)`.
    both_missed = 0
    for track in ripped:
        ar = track.get("accuraterip")
        if not isinstance(ar, dict):
            continue
        if not _ar_matched(ar.get("v1")) and not _ar_matched(ar.get("v2")):
            both_missed += 1
    possible = expected * 2 + both_missed
    variants = "v1, v2, and 450 only where both of those missed"

    # GRADED, not hard-coded to `note`. A full inventory is a clean result and must
    # say so: an informational check pinned at note level makes an otherwise perfect
    # rip un-gradeable, which is the defect
    # `test_a_complete_rip_with_real_files_is_clean` was written for after it shipped
    # once already. A grade that can never be clean tells the user nothing.
    if accurip_present >= possible:
        album.add(
            LEVEL_OK,
            f"AccurateRip inventory complete: {accurip_present}/{possible} "
            f"({expected} tracks × 2, plus {both_missed} where both v1 and v2 "
            f"missed and a 450 line could appear)",
        )
    else:
        album.add(
            LEVEL_NOTE,
            f"AccurateRip results present: {accurip_present} of a possible "
            f"{possible} — {variants}. A shortfall means the disc or those "
            f"variants are absent from the database, not that the rip is worse; "
            f"the denominator is what makes the number readable",
        )


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
        # Speak rather than return. No basis recorded is the pre-v0.6.1 report
        # shape, or a rip with no MusicBrainz release at all — both legitimate,
        # and both meaning "we cannot tell you which disc of a set this is".
        # Returning silently made that indistinguishable from "disc confirmed".
        album.add(
            LEVEL_NOTE,
            "which disc of a multi-disc release this is was not recorded — "
            "either an unknown-disc rip with no MusicBrainz release, or a "
            "report written before Platterpus recorded medium selection",
        )
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
    tracks = [t for t in (report.get("tracks") or []) if isinstance(t, dict)]
    for track in tracks:
        source = track.get("pregap_source")
        if source:
            album.pregap_sources.add(str(source))
        state = track.get("pregap_state")
        if state == "unknown":
            album.pregap_sources.add(
                "unknown: " + str(track.get("pregap_unknown_reason") or "?")
            )

    # Say something either way. This check used to feed only the library-wide
    # summary set, so an album whose tracks carried no pre-gap rows produced no
    # album finding at all — which on the first real-hardware run of the
    # embedded self-check meant a check listed as "run" that had said nothing.
    # The floor in `run_checks` would catch that now; speaking here says *why*,
    # which is the part the user can act on.
    observed = sorted(album.pregap_sources)
    if observed:
        album.add(
            LEVEL_OK if len(tracks) else LEVEL_NOTE,
            f"pre-gap provenance across {len(tracks)} track(s): " + ", ".join(observed),
        )
    else:
        album.add(
            LEVEL_NOTE,
            f"no pre-gap provenance recorded for any of {len(tracks)} track(s) — "
            "pre-gap length and source are fork-only rows, so a rip made with "
            "unmodified upstream cyanrip cannot report them",
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
    # Compare against the FIRST pass when the rip had more than one.
    #
    # `invoked_as` is read out of the whole-disc log, which is always the first
    # pass — the auto-fix addendum states that outright. `ripper_argv` is the
    # *last* invocation, so on any rip where auto-fix fired the two describe
    # different commands and the extra `-Z`/`-l` looked like injected arguments.
    # Real-hardware false alarm, 2026-08-03: a clean 14-track rip whose self-heal
    # re-ripped 2 tracks was told its command line had been altered in transit.
    #
    # Like-for-like, or not at all: a check comparing two different commands is
    # not a weaker check, it is a wrong one.
    multi_pass = bool(outcome.get("ripper_argv_first_pass"))
    sent = outcome.get("ripper_argv_first_pass") or outcome.get("ripper_argv")
    received = (report.get("rip") or {}).get("invoked_as")
    if not sent or not received:
        # NOT silent. This used to `return` with a comment calling the silence
        # legitimate — an older rip, a stock cyanrip that does not print the
        # line, a rip that never launched. Those are legitimate *reasons*, and
        # they are exactly what the user needs told: one of their integrity
        # cross-checks is unavailable for this rip. Reported as "not determined"
        # rather than passing by omission.
        if not sent and not received:
            album.add(
                LEVEL_NOTE,
                "command-line agreement not determined — neither the argv we "
                "sent nor the ripper's own 'Invoked as:' line was recorded",
            )
        elif not received:
            album.add(
                LEVEL_NOTE,
                "command-line agreement not determined — the ripper did not "
                "print an 'Invoked as:' line, so what it actually received "
                "cannot be cross-checked (stock cyanrip does not print one; the "
                "Platterpus fork does)",
            )
        else:
            album.add(
                LEVEL_NOTE,
                "command-line agreement not determined — the ripper reported "
                "the command line it received, but the argv we sent was not "
                "recorded in this report",
            )
        return

    def flags(tokens: list[str]) -> set[str]:
        """The option tokens, short and long.

        Short options only, originally — which made the check blind to a **long**
        option appearing in transit, the exact class of injection it exists to
        catch. Found by T14's own tamper case
        (`tests/test_multi_pass_rip_end_to_end.py`), which injected
        `--injected-by-a-wrapper` and was not noticed.

        Still options only, never *values*: `-s 667`'s `667` and argv[0]'s
        resolved path legitimately differ between what we spawn and what the
        ripper prints, so comparing those would cry wolf on every rip.
        """
        return {
            tok
            for tok in tokens
            if re.fullmatch(r"-[A-Za-z]", tok) or re.fullmatch(r"--[A-Za-z][\w-]*", tok)
        }

    sent_flags = flags([str(x) for x in sent])
    received_flags = flags(received.split())

    # Name WHICH pass was compared. A reader who sees "the 9 flags we sent" on a
    # rip that ran the ripper twice is entitled to know the check covered the
    # whole-disc pass and not the auto-fix one — whose `Invoked as:` line the
    # addendum consumed, so there is nothing to compare it against.
    which = " on the whole-disc pass" if multi_pass else ""
    missing = sorted(sent_flags - received_flags)
    extra = sorted(received_flags - sent_flags)
    if not missing and not extra:
        album.add(
            LEVEL_OK,
            f"the ripper received the {len(sent_flags)} flags we sent{which}",
        )
        return
    parts = []
    if missing:
        parts.append(f"we sent but it did not receive: {' '.join(missing)}")
    if extra:
        parts.append(f"it received but we did not send: {' '.join(extra)}")
    album.add(
        LEVEL_WARN,
        f"the command line changed in transit between Platterpus and cyanrip{which}"
        " — "
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
        album.add(
            LEVEL_NOTE,
            "no EAC-style log is embedded in this report, so its published "
            "SHA-256 footer could not be re-checked from the report alone",
        )
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


def _audit_ripper_log_integrity(report: dict[str, Any], album: AlbumAudit) -> None:
    """Did the RIPPER accept its own log? The independent half of log integrity.

    **Why this exists as a second check rather than an extension of the first**
    (round 7 lap 10, J3). :func:`_audit_log_integrity` verifies *the file we wrote*
    against *the checksum we computed* — a closed loop that agrees with itself no
    matter what. On the rig it reported *"the EAC-style log matches its own SHA-256
    footer"* on a rip that shipped a cyanrip log cyanrip itself would reject,
    because we had appended the auto-fix addendum past its `Log FUN512:` line. The
    fork's words: *"asserting against the thing you wrote rather than against an
    independent artifact."*

    So the two checks stay separate and both run: one says our rendering is intact,
    the other says the ripper's own record is. Neither substitutes for the other,
    and merging them would let a pass on the easy one imply the hard one.

    Reads the RECORDED verdict rather than probing. The probe lives in the rip
    worker (`adapters/ripper_log_verify`) because it spawns a container exec, and
    this registry runs inside `write_report`, which runs in a GUI slot — a
    subprocess here would freeze the window (CLAUDE.md, never block the GUI
    thread). `needs_files=False` for exactly that reason: there is nothing to open.

    Four states, all reported, none silently dropped — a check that says nothing is
    the confusion `run_checks`'s floor exists to prevent.
    """
    block = report.get("ripper_log_verification")
    if not isinstance(block, dict) or not block:
        album.add(
            LEVEL_NOTE,
            "this rip did not record whether the ripper accepts its own log "
            "(the report predates that check, or the rip ended before a log "
            "existed) — that is not a failed verification",
        )
        return
    verdict = str(block.get("verdict") or "")
    detail = str(block.get("detail") or "").strip()
    if verdict == "verified":
        album.add(
            LEVEL_OK,
            detail or "the ripper verified its own log against its own checksum",
        )
        return
    if verdict == "failed":
        # WARN, and it names the evidence: exit code and argv, so the user can
        # re-run the same command themselves. An accusation against an archival
        # artifact has to be checkable.
        exit_code = block.get("exit_code")
        argv = " ".join(str(part) for part in (block.get("argv") or []))
        shown = detail or "the ripper REJECTED its own log's checksum"
        album.add(
            LEVEL_WARN,
            f"{shown} — verified with `{argv}`"
            + (
                f", which exited {exit_code}"
                if isinstance(exit_code, int)
                else ", which never returned an exit status"
            ),
        )
        return
    album.add(
        LEVEL_NOTE,
        detail
        or "the ripper could not be asked to verify its own log, so its integrity "
        "is not determined — an absent verifier is not a failed verification",
    )


def _audit_cue_integrity(report: dict[str, Any], album: AlbumAudit) -> None:
    """Is the ``.cue`` we shipped actually right? It is external input.

    **Why this check exists.** The cue is written by cyanrip, copied into the
    album folder by us, and handed to the user as part of the archival record —
    and until v0.6.4 nothing in Platterpus had read a line of it. The rig rip of
    2026-08-05 proved two separate things wrong in one cue and neither was
    noticed: 9 of 14 ``ISRC`` lines missing (exactly the tracks carrying an
    ``INDEX 00`` marker), and the album ``TITLE`` still carrying the U+2236
    escaping artefact we already undo in the FLAC tags and the EAC-style log.
    Both were detectable from facts already in this report.

    The judging is in :mod:`platterpus.cue_validate` — pure, no I/O — so it can
    be tested against real committed cues and cannot freeze a GUI slot. This
    function's whole job is to assemble what we know **independently of the
    cue**: the ISRCs and titles out of the argv we sent, the pre-gap lengths out
    of the ripper's own log rows. Checking the cue against itself would be
    consistent rather than verified.

    Tri-state throughout: an absent, empty or truncated cue is *not determined*,
    never a pass.
    """
    from platterpus.cue_validate import (
        COLON_SUBSTITUTE,
        ExpectedCue,
        sent_album_metadata,
        sent_track_metadata,
        sent_track_selection,
        validate_cue,
    )

    entry = (report.get("artifacts") or {}).get("cue") or {}
    text = entry.get("text")
    if not text:
        album.add(
            LEVEL_NOTE,
            "cue sheet — not determined: no .cue is embedded in this report, so "
            "its contents could not be checked (a rip that ended before the "
            "ripper wrote one, or a report from before cues were embedded)",
        )
        return
    if entry.get("truncated"):
        # A truncated copy is missing its tail, and every check here reports
        # *absence* — a missing ISRC, a missing INDEX 00. Judging a cut-off copy
        # would manufacture findings against a file that is intact on disk.
        album.add(
            LEVEL_NOTE,
            "cue sheet — not determined: the embedded copy is truncated, so a "
            "missing line cannot be told from a cut-off one (the file on disk is "
            "unaffected)",
        )
        return

    # What we SENT. The first pass, for the same reason `_audit_argv_agreement`
    # uses it: on a rip where the auto-fix fired, the last argv describes a
    # two-track re-rip and would claim the cue is missing twelve tracks' ISRCs.
    outcome = report.get("outcome") or {}
    argv = outcome.get("ripper_argv_first_pass") or outcome.get("ripper_argv") or []
    sent_tracks = sent_track_metadata([str(part) for part in argv])
    sent_album = sent_album_metadata([str(part) for part in argv])

    def real_colons(value: str) -> str:
        """The true text, with our U+2236 workaround undone."""
        return value.replace(COLON_SUBSTITUTE, ":")

    isrcs = {
        number: pairs["isrc"]
        for number, pairs in sent_tracks.items()
        if pairs.get("isrc")
    }
    titles = {
        number: real_colons(pairs["title"])
        for number, pairs in sent_tracks.items()
        if pairs.get("title")
    }

    # What the RIPPER measured. Only pre-gaps whose state is "known": an unknown
    # pre-gap must not become an accusation in either direction (a missing marker
    # we cannot justify, or a spurious one we cannot rule out).
    tracks = [t for t in (report.get("tracks") or []) if isinstance(t, dict)]
    pregaps: dict[int, int] = {}
    for track in tracks:
        number = track.get("number")
        frames = track.get("pregap_length_frames")
        if (
            isinstance(number, int)
            and isinstance(frames, int)
            and track.get("pregap_state") == "known"
        ):
            pregaps[number] = frames

    # Only claim a track count when the rip actually finished. A cancelled rip
    # legitimately leaves a shorter cue, and accusing it of one would train the
    # reader to ignore this check.
    completed = (report.get("rip") or {}).get("rip_completed")
    track_count = len(tracks) if completed is True and tracks else None

    # Which tracks the ripper was told to rip. Read from the SAME (first-pass)
    # argv as the ISRCs above, which is what makes the pair like-for-like: the
    # user's per-track selection lives in the first pass's `-l`, while the
    # auto-fix re-rip's `-l` is in the *last* pass and must not be mistaken for
    # it. `-t` tag arguments are built from the metadata and ignore the
    # selection, so without this a two-track rip expects fourteen ISRCs in a
    # two-track cue and warns about twelve of them.
    expected = ExpectedCue(
        isrcs=isrcs,
        pregap_frames=pregaps,
        track_titles=titles,
        album_title=real_colons(sent_album["album"])
        if sent_album.get("album")
        else None,
        track_count=track_count,
        ripped_tracks=sent_track_selection([str(part) for part in argv]),
    )
    for finding in validate_cue(str(text), expected=expected):
        album.add(finding.level, finding.text)


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
        # LEVEL_OK, not LEVEL_NOTE. Recording the pressing's identity is a check
        # that SUCCEEDED, and levelling it as a note made `worst` read "note" for
        # a flawless rip — which is what the first real-hardware self_check block
        # said. A level that is always at least "note" is not a verdict.
        album.add(
            LEVEL_OK,
            f"disc identity — MusicBrainz {disc_id or '(none)'} / CDDB {cddb or '(none)'}",
        )
    else:
        album.add(
            LEVEL_NOTE,
            "no TOC-derived disc identity recorded, so this rip cannot be "
            "matched to the same physical pressing later",
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
    Check(
        # Added 2026-08-07 for the first rip on the round-7 RELEASE. The binary's
        # own compiled-in handshake sentence changes shape for the first time with
        # that build, and nothing had ever seen the second shape.
        "handshake_note",
        "Do the ripper's own handshake note and our verdict agree?",
        False,
        _audit_handshake_note,
    ),
    Check(
        # Added 2026-08-07. Counts the evidence and states the denominator, because
        # a checksum comparison over a silently-partial inventory passes.
        "checksum_inventory",
        "How many of the disc's checksums do we actually hold?",
        False,
        _audit_checksum_inventory,
    ),
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
        # Renamed from "log_integrity" in v0.6.4. The old name read as "is the log
        # intact", which is the claim the fork correctly said it was not making: it
        # checks OUR rendering against OUR footer. The name now says whose.
        "our_log_integrity",
        "Does the EAC-style log WE wrote match the checksum WE published?",
        False,
        _audit_log_integrity,
    ),
    Check(
        # The independent half. Kept as its own row rather than folded into the one
        # above so a pass on ours can never imply a pass on theirs.
        "ripper_log_integrity",
        "Does the RIPPER accept the log it wrote?",
        False,
        _audit_ripper_log_integrity,
    ),
    Check(
        # Added v0.6.4b12. The cue is the one artifact we ship that nothing had
        # ever read — see `_audit_cue_integrity`. `needs_files=False`: the cue's
        # text is embedded in the report, so this runs on a report read anywhere.
        "cue_integrity",
        "Is the .cue we shipped consistent with what we sent and measured?",
        False,
        _audit_cue_integrity,
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
        before = len(album.findings)
        try:
            check.run(report, album)
        except Exception as exc:  # noqa: BLE001 — a broken check must not stop the audit
            log.exception("audit check %s raised", check.name)
            album.add(LEVEL_NOTE, f"check '{check.name}' could not run: {exc}")
            skipped.append(check.name)
            continue
        ran.append(check.name)
        if len(album.findings) == before:
            # THE FLOOR. A check that ran and said nothing is the third state
            # this function originally missed: `checks_run` listed it, no finding
            # mentioned it, and the report was indistinguishable from one where
            # the check had found everything in order. The first real-hardware
            # run of the embedded self-check hit it immediately — `pregap` and
            # `argv_agreement` both ran silently on a stock-cyanrip rip, because
            # stock does not emit the rows they read.
            #
            # "A silent truncation reads as completeness" (CLAUDE.md), and the
            # same is true of a silent check. Individual checks are written to
            # say why they have nothing; this is the backstop that makes a future
            # silent check impossible rather than merely discouraged, and
            # tests/test_rip_audit.py asserts every registered check speaks.
            album.add(
                LEVEL_NOTE,
                f"check '{check.name}' ({check.question}) ran but had nothing to "
                f"report for this rip — treat this as 'not determined', not 'ok'",
            )
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
            # Name the FILE. "send the log for that album" is ambiguous between the
            # ripper's `.log`, the EAC-style log and the app log — and the one that
            # actually carries this evidence is the JSON report.
            "  please send that album's `.platterpus.json` report.",
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
