"""Machine-readable (JSON) rip report — the structured companion to the log.

Deep-research lesson (docs/ux-design-principles.md #2, "two outputs every
time"): a trustworthy tool should emit both a human-readable narrative *and* a
machine-readable structure, so the result can be re-verified, fed to QA/repair
tooling, or attached to a support thread later. Platterpus already has the human
log (the backend's `.log`); this adds the JSON.

`build_report` is pure and **never raises** (mirrors the parser/renderer
discipline): a malformed or partial ``RipLog`` yields a best-effort report with
a valid envelope rather than blowing up the post-rip path. The whole-disc
verdict reuses :func:`platterpus.verdict.accuraterip_verdict` and the per-track
flag reuses :func:`track_accuraterip_verified`, so the JSON can never disagree
with the on-screen banner about what "verified" means.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

from platterpus import __version__, build_info, diagnostics
from platterpus.atomic_write import atomic_write_text
from platterpus.handshake_approval import (
    RipperApproval,
    approve_rip_log,
    cross_check_note,
)
from platterpus.parsers.rip_log import (
    track_accuraterip_verified,
    tracks_needing_heavy_reread,
)
from platterpus.report_types import ArtifactsBlock, EnvironmentBlock
from platterpus.ripper_identity import RipperIdentity, identify_ripper
from platterpus.verdict import accuraterip_verdict

log = logging.getLogger(__name__)


def _atomic_write_text(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` atomically AND durably.

    Crash-safety (it.12): the report is re-written repeatedly as post-rip checks
    finish, so a torn/truncated ``.platterpus.json`` would be easy to hit on a
    crash or power loss. Delegates to ``atomic_write`` (temp → fsync →
    ``os.replace`` → parent-dir fsync), so a reader ever sees either the complete
    old file or the complete new file. Raises ``OSError`` on failure; the callers
    keep the best-effort/never-raise contract by catching it, and a stray temp
    from a failed write is cleaned up here.
    """
    try:
        atomic_write_text(target, text)
    except OSError:
        # Don't leave a stray temp behind on a failed write.
        try:
            target.with_name(target.name + ".tmp").unlink()
        except OSError:
            pass
        raise


# Bump when the JSON shape changes in a way a consumer must notice.
# v2 (0.4.5): added the `verification` block (FLAC-integrity + transcode outcomes
# beside CTDB) and per-file `checksums` — the maintainer's "one debug file" rule
# means everything extra lives here, not in extra sidecars.
# v3 (0.4.6): added `verification.derived` — the per-format proof of the derived
# MP3/WavPack/WAV files (bit-identity for lossless, decode-clean+complete for
# lossy MP3) alongside the FLAC-master checks; and `read_speed` — the adaptive
# read-speed ladder's per-pass history.
# v4 (0.4.7): added `eta_trace` (PC-clock-stamped samples of our ETA + cyanrip's,
# for future ETA modelling) and `read_speed.unstable_tracks` — the tracks whose
# secure re-read never converged (read instability, flagged not auto-re-ripped).
# v5 (0.4.8): added `read_speed.retried_tracks` — the per-track auto-fix history
# (each unstable track re-ripped alone with a harder -Z; whether it then converged
# and whether the improved FLAC replaced the original). `unstable_tracks` now
# lists only tracks the auto-fix could NOT rescue.
# v6 (0.4.9): richer diagnostics for the maintainer's hardware analysis — `rip`
# now carries `speed_changeable` (whether the drive can change read speed; the
# field behind the `-S`-abort fix), and each track carries the extraction metrics
# cyanrip logs: `extraction_speed` (×), `extraction_quality` (%), `pre_emphasis`,
# and `peak_level`. All were already parsed; v6 just surfaces them so a re-rip's
# JSON reports back everything the log reveals.
# v7 (0.4.10): "one file explains a rip" — the report now records the *process*
# result and everything a triager asks for, all additive keys:
#   * `outcome` — success/cancelled/failed + a failure hint + whether the
#     auto-heal (re-rip as unknown) fired (the actual process result; the older
#     `verdict`/`health_status` are AccurateRip/log-derived, not that).
#   * `settings` — what the GUI *asked for* (output format, cover-art mode, the
#     secure-re-rip config, and the read offset {configured, applied, effective}
#     — the log shows `0` whether the offset was truly 0 or configured-but-off).
#   * `disc` — provenance: unknown-mode + the MusicBrainz release id.
#   * `environment` — Python / OS / PySide6 / install channel (+ per-dependency
#     versions & paths, filled by the GUI from the launch-time dependency probe).
#   * `generator.build_fingerprint` — the build's git short-SHA (or "source"),
#     so a report is traceable to an exact build (debug only; NOT EAC parity).
#   * `verification.gates` — turns an ambiguous `null` sub-block into an explicit
#     "ran"/"disabled"/"backend self-verifies"/"flac-only" so a missing check is
#     never confused with a failed one.
#   * `cover_art` — the structured front-cover result (found / why-not / embedded).
#   * `read_speed.secure_rerip` — why the dynamic secure re-rip did or didn't run.
#   * `log_parse` — whether the human log parsed cleanly (flags a degraded read).
#   * `issues` — one consolidated, severity-tagged "what went wrong" list a
#     triager opens first (empty on a clean rip).
# v9 (0.4.24): re-rip trust support, all additive:
#   * `rip.musicbrainz_disc_id` / `rip.cddb_id` — the TOC-derived disc IDs, the
#     truest "same physical disc" key (stable across re-rips, independent of any
#     MusicBrainz *release* edit). The re-rip comparison (rip_compare) keys on
#     them, so a report is self-sufficient for that diff.
#   * each track now serializes `secure_rerip_converged` (was parsed but dropped)
#     beside `rip_count`, so the read-effort signal is in the machine record.
#   * `issues` can now carry a `heavy_reread` warning — tracks that needed
#     unusually heavy re-reading (or a -Z that never converged) even when they
#     ultimately matched AccurateRip: the earliest in-rip "this may not be
#     reproducible" hint (see parsers.rip_log.tracks_needing_heavy_reread).
#
# NOT a version bump: `issues` gained a `tagging_failed` code (2026-07-31). A new
# code inside an existing, already-declared list shape is additive in a way no
# consumer can trip over — every reader iterates `issues` — whereas a new
# top-level or `verification` key changes a key set that consumers and tests pin
# exactly. Bump the version for a shape change, not for a new value in one.
# v10 (0.5.20): five per-track facts the parser already read and this file
# dropped, so the JSON stops being less complete than the human-readable log it
# sits beside:
#   * `appended_silence_frames` — frames of *fabricated silence* the ripper
#     appended because it could not read that far. The important one: deployed
#     cyanrip 0.9.3 prints it (last track, overread off) and both committed
#     reference rips contain it, so this was a live omission, not fork
#     preparation. It reached the EAC-layout log and never the machine record.
#   * `start_sector` / `end_sector` / `pregap_sectors` — absolute disc geometry.
#     EAC's "TOC of the extracted CD" is derived from these exactly; without
#     them the JSON could not rebuild a table the `.log` already shows.
#   * `extraction_elapsed_seconds` — fork-only, None on 0.9.3. Serialized now so
#     the fork's output lands in the report the day the fork ships, rather than
#     being parsed into a field nothing writes down.
# v11 (0.5.21): two corrections to v10, both found by running the maintainer's
# cyanrip fork's real output through the parser:
#   * `pregap_start_lsn` added, and `pregap_sectors` now means what its name says.
#     v10 serialized cyanrip's "Pregap LSN:" row — an ABSOLUTE position — under
#     `pregap_sectors`, and every consumer rendered it as a length. On the
#     reference pressing that is an 89x over-claim in the EAC "Pre-gap length"
#     row. The length is now derived as `start_sector - pregap_start_lsn`, which
#     is exactly how cyanrip computes the duration it prints itself.
#   * the disc-level `c2_pointers`, `paranoia_level` and `overread_mode` — read
#     from the log and rendered into the EAC-layout artifact, but absent from the
#     machine record, so an automated consumer could not see what the rip did.
# v12 (0.5.22): make the JSON genuinely the only file worth uploading. The
# maintainer's instruction, after a hardware round in which every diagnosis
# began by asking for a second file: "just assume I can only upload the json
# file, put all [the tests] in there that you need" (2026-08-01).
#   * `artifacts` — the verbatim text of the three companion files written
#     beside the report (cyanrip's own `.log`, our EAC-layout render, the
#     `.cue`), each with its size and a SHA-256 of the bytes on disk. Text only,
#     enforced by an extension allowlist — never audio (critical rule #8). A
#     file that is absent says so rather than being omitted: "cyanrip wrote no
#     cue" and "we didn't look" are different findings, and a zero-byte cue
#     after a cancelled rip is invisible in a summary and obvious in a byte
#     count (both were real, 2026-08-01).
#   * `completeness` — `tracks_expected` / `tracks_in_report` / `complete`. The
#     disc's track count reached this builder already, but only to *feed* the
#     verdict; it was never written down, so the JSON's only track count was
#     `len(tracks)` — the log's own list, which a cancel shrinks. A reader had
#     to parse English out of `verdict.message` to learn that a 2-track report
#     described a 14-track disc. This is the same missing denominator that has
#     now been corrected on four surfaces; recording it as a number is what
#     stops a fifth.
# v20: `partially_accurate_reported` — the ripper's own offset-variant fraction,
#     verbatim, beside our own derived sentence about it. Added because the fraction's
#     DENOMINATOR changed meaning between fork builds (`1/1` up to `e61e75a`, `1/14`
#     from `f5e11ba`, same disc, same track) while our sentence asserted the old
#     meaning in prose. The sentence is now counted from the per-track results, and
#     this field preserves what the binary actually printed — two logs of one disc
#     from two builds are not comparable without it.
# v21: `eta_trace.samples[].state` and `.reread_pass`. Before this, only the branch
#     that made a FRESH rate measurement recorded a sample, so the trace went silent
#     on the hold and stall paths — the b8 rig trace has a 541-second and a
#     400-second hole, both landing exactly on the minutes the estimator was
#     misbehaving, which is how the peak reading became un-analysable from the
#     artifact. Every branch records now, and `state` is what keeps that honest: a
#     re-shown older estimate is labelled `held_*`, a pinned album bar during a
#     secure re-read is `rereading`, and only `computed` is a measurement.
# v15: `ripper_handshake_approval` / `_detail` / `_approved_build` /
# `_approved_for_platterpus` / `_approved_by_round` — whether the ripper that
# produced THIS rip is the build both projects affirmatively verified, checked at
# rip time rather than only by CI. Tri-state; `not_determined` is not a pass.
# v14: `rip_completed` / `_tracks` / `_total` / `_reason` and `invoked_as` —
#     the ripper's own completion verdict and the argv it reports receiving.
#     Both were being PARSED and then not serialized, which the embedded
#     self-check caught the first time it ran: it reported "footer absent" for
#     a log that plainly had one. Also adds the `self_check` block itself.
# v13: `ripper_is_platterpus_fork` / `ripper_identity` / `ripper_identity_detail`.
#     `ripper_build` was already recorded, but it is a raw tag — a consumer had
#     to know which strings mean "the Platterpus fork" to use it, and nothing
#     said so. The classified answer is tri-state (`true` / `false` / `null`)
#     because "we could not tell which binary" is a real and common outcome, and
#     collapsing it to `false` would assert an unmodified upstream build we have
#     no evidence for — the exact shape of bug this project has now shipped three
#     times (`Accurip: disabled`, the all-zero CRC, `Pregap LSN: unknown`).
# v23: `settings.rip_goal` becomes DERIVED from the six preset fields instead of
#     read back from `config.rip_goal`, and `settings.rip_goal_stored` appears only
#     when the stored label disagreed. `rip_goal` is a *label for a bundle of
#     fields* and nothing kept the two in step — a hand-edited config.toml, a field
#     changed outside `apply_preset`, or a config written before the field existed
#     all leave a stale label. The Settings dialog had always re-derived (so the
#     screen was right); the report wrote the stored string, so a rip's permanent
#     record could name a goal its own settings never matched. Both values are now
#     present when they differ, because the disagreement is itself the finding.
# v22: `rip.ripper_release_id` — the MusicBrainz release id the ripper RESOLVED AND
#     USED, off its own header, plus the `issues` comparison against the id we sent.
#     Previously in the ignored table with a recorded reason ("our own input reflected;
#     `Invoked as:` is a better witness for an argv disagreement"), which was true of
#     the argv question and did not cover a different one: we hand the whole tag set as
#     ONE colon-delimited `-a` blob, so what the ripper received and what it parsed are
#     separate claims and only the first was recorded. The comparison is what makes
#     either number more than a record — it also checks `-N` really suppressed the
#     ripper's own lookup (Critical rule #5) at the artifact instead of on trust.
REPORT_SCHEMA_VERSION: int = 23

# Cap on how many session-log lines the report embeds. The JSON is now the SINGLE
# per-album debug artifact (no `.platterpus.log` sidecar), so it should hold
# *everything* for this album's rip — verbose enough to debug from alone. A
# single album's log is a few hundred lines at INFO, low thousands at DEBUG, so
# 10k comfortably captures a whole verbose rip while still bounding a pathological
# case (the write is atomic + debounced, off the critical path). Lines are scoped
# to THIS rip already; if the in-memory buffer's own bound ever truncated older
# lines, `truncated` is set and the full history is still in log.txt.
# ALSO A BACKSTOP, for the same reason as the byte budget below — raised from 10,000
# after that number turned out to be the binding constraint on a real verbose rip
# (20k lines), which is not what a "cap a pathological case" limit should ever be.
# Bytes are the meaningful bound; this is the cheap sanity guard in front of them.
_MAX_EMBEDDED_LOG_LINES: int = 200_000

# Byte budget for the embedded log — the bound that actually matters, added after a
# real 14-track rip produced a **1.5 MB** report of which **1.23 MB (81%)** was this
# one block. The line cap above was set from an estimate ("a few hundred lines at
# INFO, low thousands at DEBUG") that was never measured against a rip, and a line
# cap cannot bound a file anyway because a line has no fixed length.
#
# **THIS IS A RUNAWAY BACKSTOP, NOT A ROUTINE CAP — DO NOT LOWER IT TO SAVE SPACE.**
# The first version of this constant was 256 KiB, chosen to bring that 1.5 MB report
# "back under control", and the maintainer corrected it on the spot: *"I did tell you
# to capture more error data than you think you need."* He is right, and the
# arithmetic says so — 1.5 MB of diagnostics sits beside ~400 MB of FLAC for the same
# album, so the report is 0.4% of what the rip already wrote. Trading a diagnosis for
# 0.4% is the wrong trade, and it is the exact trade CLAUDE.md's diagnostic-
# completeness rule forbids: a fact we had and discarded is worse than one we never
# obtained, because the artifact looks complete either way.
#
# 8 MiB therefore bounds only a pathological case (a log loop, a runaway retry) where
# the report would otherwise grow without limit and become unopenable. A normal
# verbose rip — measured at 1.23 MB for 14 tracks at DEBUG — is nowhere near it and
# is embedded whole.
_MAX_EMBEDDED_LOG_BYTES: int = 8 * 1024 * 1024


def build_report(
    rip_log: object,
    *,
    ctdb_result: object | None = None,
    flac_verify_result: object | None = None,
    transcode_result: object | None = None,
    derived_verify_result: object | None = None,
    recompress_result: object | None = None,
    cover_art_result: object | None = None,
    tagging_result: object | None = None,
    read_speed: dict | None = None,
    secure_rerip: dict | None = None,
    eta_trace: list | None = None,
    checksums: dict | None = None,
    generated_at: str = "",
    timing: dict | None = None,
    debug_log: dict | None = None,
    outcome: dict | None = None,
    settings: dict | None = None,
    disc: dict | None = None,
    environment: EnvironmentBlock | None = None,
    gates: dict | None = None,
    log_parse: dict | None = None,
    disc_track_total: int | None = None,
    artifacts: ArtifactsBlock | None = None,
    #: v18: the RIPPER's verdict on its own log, from `adapters.ripper_log_verify`
    #: — an independent witness, unlike our own SHA-256 footer check. Typed
    #: `object` because this pure builder must not import an adapter.
    ripper_log_verification: object | None = None,
) -> dict:
    """Return a structured, versioned summary of a rip as a plain dict.

    ``generated_at`` is supplied by the caller (an ISO-8601 timestamp) so this
    stays pure and deterministic. ``ctdb_result`` is an optional
    :class:`~platterpus.ctdb.verify.CtdbVerifyResult`. ``flac_verify_result`` is
    an optional :class:`~platterpus.adapters.flac_verify.FlacVerifyResult` and
    ``transcode_result`` an optional
    :class:`~platterpus.adapters.transcode.TranscodeResult` — together they form
    the report's ``verification`` block alongside CTDB. ``checksums`` is an
    optional ``{relpath: sha256}`` map (see :mod:`platterpus.checksums`).
    ``timing`` / ``debug_log`` are as in :func:`build_timing` /
    :func:`build_debug_log`.

    The v7 (0.4.10) blocks are assembled by the caller (they depend on live
    config / rip params / the launch-time dependency probe, which this pure
    builder can't reach) and passed in: ``outcome`` (see :func:`build_outcome`),
    ``settings`` (:func:`build_settings`), ``disc``, ``environment``
    (defaults to :func:`build_info.environment_report` when omitted), ``gates``
    (:func:`build_gates`), ``cover_art_result``, ``secure_rerip`` (folded into
    the ``read_speed`` block), ``recompress_result`` and ``log_parse``. The
    ``issues`` list is derived here from the assembled blocks. Never raises.
    """
    try:
        return _build(
            rip_log,
            ctdb_result,
            generated_at,
            timing,
            debug_log,
            flac_verify_result,
            transcode_result,
            checksums,
            derived_verify_result,
            read_speed,
            eta_trace,
            recompress_result=recompress_result,
            cover_art_result=cover_art_result,
            tagging_result=tagging_result,
            secure_rerip=secure_rerip,
            outcome=outcome,
            settings=settings,
            disc=disc,
            environment=environment,
            gates=gates,
            log_parse=log_parse,
            disc_track_total=disc_track_total,
            artifacts=artifacts,
            ripper_log_verification=ripper_log_verification,
        )
    except Exception:  # noqa: BLE001 — a report builder must never crash a rip
        log.exception("rip-report build failed; emitting minimal envelope")
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "generator": {
                "name": "platterpus",
                "version": __version__,
                "build_fingerprint": build_info.build_fingerprint(),
            },
            "error": "report could not be built",
        }


def build_timing(
    elapsed_seconds: float | None,
    *,
    disc_seconds: float | None = None,
    started_at: str = "",
    finished_at: str = "",
    audio_seconds_ripped: float | None = None,
    completed: bool | None = None,
) -> dict:
    """Build the ``timing`` section: actual elapsed + how it compares to the disc.

    Pure and never raises. ``elapsed_seconds`` is the GUI-measured wall-clock
    (cyanrip logs the disc's audio length and a finish timestamp, but never its
    own run time). ``disc_seconds`` is the disc's audio duration; when given, we
    record a **realtime multiplier** (elapsed ÷ audio length) — a meaningful,
    honest archival metric ("this rip took 2.6× the disc's runtime") that
    replaces cyanrip's first-tick ETA, which was wildly wrong (it logged "822h"
    at 0.01% on a real disc — see rip_worker).
    """
    from platterpus.rip_timing import format_duration

    timing: dict = {
        "elapsed_seconds": (
            round(elapsed_seconds) if isinstance(elapsed_seconds, int | float) else None
        ),
        "elapsed_human": format_duration(elapsed_seconds),
        "started_at": started_at or None,
        "finished_at": finished_at or None,
    }
    if (
        isinstance(elapsed_seconds, int | float)
        and isinstance(disc_seconds, int | float)
        and disc_seconds > 0
    ):
        timing["disc_seconds"] = round(disc_seconds)
    # `elapsed / disc_seconds` is only a RATE if the whole disc was ripped. On a
    # cancelled rip it silently reports the fraction of the disc covered, which
    # reads as an implausibly fast rip: the rig's 2-of-14 cancel logged
    # `realtime_multiplier: 0.21` (755 s of a 3582 s disc) when actual throughput
    # was about 0.93x. A plausible wrong number is worse than none, because
    # nothing about it invites checking.
    #
    # Three outcomes, in order of how much we know:
    #   * a completed rip           -> elapsed / disc audio, the real rate
    #   * a partial rip that told us how much audio it DID extract
    #                               -> elapsed / that, still a real rate
    #   * anything else             -> null, and null means "we cannot say"
    #
    # `completed=None` keeps every existing caller on the old behaviour: a caller
    # that does not know whether the rip finished has not asserted that it didn't.
    if not isinstance(elapsed_seconds, int | float) or elapsed_seconds <= 0:
        return timing
    if completed is False:
        if isinstance(audio_seconds_ripped, int | float) and audio_seconds_ripped > 0:
            timing["realtime_multiplier"] = round(
                audio_seconds_ripped / elapsed_seconds, 2
            )
            timing["realtime_multiplier_basis"] = "audio actually extracted"
        else:
            timing["realtime_multiplier"] = None
            timing["realtime_multiplier_basis"] = (
                "not computed — the rip did not finish, so elapsed over the "
                "disc's length would be the fraction covered, not a rate"
            )
        return timing
    if isinstance(disc_seconds, int | float) and disc_seconds > 0:
        timing["realtime_multiplier"] = round(elapsed_seconds / disc_seconds, 2)
    return timing


def build_debug_log(lines: list[str], *, truncated: bool = False) -> dict:
    """Wrap captured session log lines for the report's ``debug`` section.

    ``lines`` is this session's log (everything since launch) with other albums'
    rips already filtered out by the caller; ``truncated`` is True if the
    in-memory buffer already dropped its oldest lines. Embeds at most
    ``_MAX_EMBEDDED_LOG_LINES`` (keeping the most recent — closest to this rip),
    so the report stays small and fast to (re)serialize on the GUI thread no
    matter how long the session ran; the full history is always in log.txt.
    Pure; never raises.
    """
    embedded = list(lines)
    capped = len(embedded) > _MAX_EMBEDDED_LOG_LINES
    if capped:
        embedded = _head_and_tail(embedded, _MAX_EMBEDDED_LOG_LINES)
    # THEN the byte budget, which is the constraint that actually bit. The line cap
    # alone let a real 14-track rip's report reach 1.23 MB of `debug` — 81% of a
    # 1.5 MB file — because the comment above estimated "a few hundred lines at
    # INFO, low thousands at DEBUG" and never checked. Lines are a proxy; bytes are
    # the thing the user waits on and the disk holds.
    budget = _MAX_EMBEDDED_LOG_BYTES
    if sum(len(line) + 1 for line in embedded) > budget:
        capped = True
        embedded = _head_and_tail_by_bytes(embedded, budget)
    return {
        "scope": "this session since launch, excluding other albums' rips",
        # True if EITHER the in-memory buffer dropped lines OR we capped here;
        # in both cases log.txt has the complete record.
        "truncated": bool(truncated) or capped,
        "lines": embedded,
    }


def _elision(dropped: int) -> str:
    """The marker that makes a truncation VISIBLE and COUNTED.

    CLAUDE.md: *"A silent truncation reads as completeness."* A reader who sees a
    gap marked with its size knows to open log.txt; a reader who sees a seamless
    join believes they have the whole record.
    """
    return f"… [{dropped} line(s) elided by Platterpus — the full record is in log.txt]"


def _head_and_tail(lines: list[str], limit: int) -> list[str]:
    """Keep the FIRST and LAST portions, not just the last.

    **Tail-only was the bug here.** The old cap kept `lines[-N:]`, which for a rip
    drops exactly the opening: the argv we spawned, the drive and disc detection,
    the settings in force. A failure's explanation is usually last, but a rip's
    *context* is always first, and a bounded record needs both ends (CLAUDE.md,
    diagnostic completeness). Two-thirds to the tail, because that is where a
    fatal message lands.
    """
    if len(lines) <= limit:
        return lines
    tail_n = max(1, (limit * 2) // 3)
    head_n = max(1, limit - tail_n - 1)  # -1 leaves room for the marker itself
    dropped = len(lines) - head_n - tail_n
    return [*lines[:head_n], _elision(dropped), *lines[-tail_n:]]


def _head_and_tail_by_bytes(lines: list[str], budget: int) -> list[str]:
    """The same head+tail shape, bounded by BYTES rather than line count.

    A line can be any length, so a line cap does not bound a file. Fills the tail
    first (a fatal message is the last thing printed), then the head with whatever
    budget remains, and always emits the counted marker.
    """
    tail: list[str] = []
    used = 0
    tail_budget = (budget * 2) // 3
    for line in reversed(lines):
        cost = len(line) + 1
        if used + cost > tail_budget:
            break
        tail.append(line)
        used += cost
    tail.reverse()
    head: list[str] = []
    for line in lines[: len(lines) - len(tail)]:
        cost = len(line) + 1
        if used + cost > budget:
            break
        head.append(line)
        used += cost
    dropped = len(lines) - len(head) - len(tail)
    if dropped <= 0:
        return lines
    return [*head, _elision(dropped), *tail]


def build_outcome(
    *,
    status: str,
    failure_hint: str | None = None,
    auto_unknown_retry_fired: bool = False,
    auto_unknown_retry_reason: str | None = None,
    ripper_exit_code: int | None = None,
    ripper_argv: tuple[str, ...] | list[str] | None = None,
    ripper_argv_first_pass: tuple[str, ...] | list[str] | None = None,
) -> dict:
    """Build the ``outcome`` block: the PROCESS result of the rip.

    This is the single most-requested support datum and was previously absent —
    ``verdict``/``health_status`` describe AccurateRip / the rip log, not whether
    the *run* succeeded. ``status`` is one of ``"success"`` / ``"cancelled"`` /
    ``"failed"``; ``failure_hint`` is an actionable one-liner when we have one;
    ``auto_unknown_retry`` records whether the self-heal (re-rip as unknown when
    the ripper couldn't reach MusicBrainz) fired. Pure; never raises.

    ``ripper_exit_code`` and ``ripper_argv`` (v13) are the two facts that make a
    failure reproducible, and both were being computed and discarded:

    * The exit code separates outcomes that rendered identically. ``1`` is the
      ripper refusing an argument, ``0`` with a cancel is the user stopping a
      healthy run, and a negative value is a signal — ``-9`` meaning we had to
      SIGKILL the process group. ``None`` is its own answer: the child was never
      reaped, which happens when it is wedged in a drive ioctl where even
      SIGKILL does not land.
    * The argv is what lets someone re-run the exact failing command. The one
      argument defect that has killed a whole rip (``-t 17=`` on a 16-track
      disc) was diagnosed from files the maintainer uploaded, because our own
      report did not carry the command line.
    """
    argv = tuple(ripper_argv or ())
    # The FIRST invocation, when the rip took more than one.
    #
    # A rip can spawn the ripper twice: the whole-disc pass, then an auto-fix pass
    # (`-Z N -l <tracks>`) over only the tracks AccurateRip did not verify.
    # `ripper_argv` is the LAST one — right for "re-run what finished" — but the
    # archival log's `Invoked as:` line comes from the *first* pass (the auto-fix
    # addendum says so in as many words). Comparing those two is comparing
    # different commands, and the argv-agreement check did exactly that: on a real
    # 14-track rip where auto-fix re-ripped 2 tracks it reported *"the command line
    # changed in transit … Something between us altered it"*, naming `-Z` and `-l`
    # as injected. Nothing had altered anything. A cross-check that accuses the
    # user's system of tampering whenever the product's own self-heal fires is
    # worse than no cross-check, because the false alarm fires on precisely the
    # rips a user looks at closely.
    #
    # None when there was only one pass, so "single-pass" and "first of several"
    # stay distinguishable rather than both rendering as a bare argv.
    first = tuple(ripper_argv_first_pass or ())
    return {
        "status": status,
        "failure_hint": failure_hint or None,
        "auto_unknown_retry": {
            "fired": bool(auto_unknown_retry_fired),
            "reason": auto_unknown_retry_reason or None,
        },
        # Distinct keys rather than one nested object, because a support reader
        # greps this file and a flat key is findable.
        "ripper_exit_code": ripper_exit_code,
        # A list (JSON has no tuples) of the argv as spawned. Empty argv is
        # serialized as null, not [], so "we never launched it" and "we launched
        # it with no arguments" stay distinguishable.
        "ripper_argv": list(argv) or None,
        "ripper_argv_first_pass": list(first) or None,
        # Pre-joined for the human reading the JSON. Not shell-quoted: it is a
        # record of an `execve` argument vector, and quoting it would suggest it
        # is safe to paste, which for a vector containing user-entered metadata
        # it is not. `ripper_argv` above is the machine-readable form.
        "ripper_command_display": " ".join(argv) or None,
    }


def _derived_rip_goal(config: object) -> str | None:
    """The goal the config's *fields* describe, not the label stored beside them.

    ``goal_presets.detect_goal`` reads the six preset fields directly, so it
    needs a real :class:`~platterpus.config.Config`-shaped object; this module is
    handed duck-typed stand-ins by tests and by the minimal-failure path, and it
    must never raise. On anything it cannot classify we fall back to the stored
    label rather than to ``None``, because a possibly-stale label still carries
    more than a blank.

    Imported inside the function on purpose: :mod:`platterpus.goal_presets`
    imports :class:`Config`, and pulling it in at module scope here drags the
    settings-preset layer into the report writer's import graph for one lookup.
    """
    from platterpus import goal_presets

    try:
        return goal_presets.detect_goal(config)  # type: ignore[arg-type]  # duck-typed
    except (AttributeError, TypeError):
        stored = getattr(config, "rip_goal", None)
        return stored if isinstance(stored, str) else None


def _stale_rip_goal(config: object) -> dict[str, str]:
    """``{"rip_goal_stored": <label>}`` when the stored label disagrees, else ``{}``.

    A disagreement means the config file's label is wrong about its own settings.
    That is worth recording (and logging) rather than quietly overwriting: it is
    the only evidence that the user's ``config.toml`` says one thing and does
    another, and the report is where a support reader would look.
    """
    stored = getattr(config, "rip_goal", None)
    if not isinstance(stored, str) or not stored:
        return {}
    derived = _derived_rip_goal(config)
    if derived is None or derived == stored:
        return {}
    log.warning(
        "config.rip_goal is %r but the settings actually describe %r; "
        "recording the derived goal and keeping the stored one as "
        "settings.rip_goal_stored",
        stored,
        derived,
    )
    return {"rip_goal_stored": stored}


def build_settings(config: object, *, read_offset_effective: int | None = None) -> dict:
    """Build the ``settings`` block: what the GUI *asked the ripper for*.

    The rip log only ever shows what the drive *did*; this records the user's
    configured intent so a support reader can tell, e.g., a genuine 0 read offset
    from one that was configured but never applied. Reads a
    :class:`~platterpus.config.Config` via ``getattr`` so it's pure and tolerant
    of a partial/duck-typed object; ``read_offset_effective`` is the value
    actually handed to cyanrip for this rip (``-s``), passed by the caller from
    the rip params. Never raises.
    """
    fmt = getattr(config, "output_format", None)
    configured_offset = getattr(config, "read_offset", None)
    applied = bool(getattr(config, "override_read_offset", False))
    if read_offset_effective is None:
        read_offset_effective = (configured_offset or 0) if applied else 0
    settings: dict = {
        "output_format": fmt,
        "cover_art": getattr(config, "cover_art", "") or None,
        "read_speed_mode": getattr(config, "read_speed_mode", None),
        "read_speed": getattr(config, "read_speed", None),
        "secure_rerip_dynamic": getattr(config, "secure_rerip_dynamic", None),
        "secure_rerip_matches": getattr(config, "secure_rerip_matches", None),
        "max_retries": getattr(config, "max_retries", None),
        "ctdb_verify_after_rip": getattr(config, "ctdb_verify_after_rip", None),
        "verify_flac_after_rip": getattr(config, "verify_flac_after_rip", None),
        "recompress_flac_after_rip": getattr(config, "recompress_flac_after_rip", None),
        # DERIVED, not read back. `rip_goal` in the config file is a label for a
        # bundle of the six fields above it, and nothing keeps the two in step:
        # a hand-edited config.toml, a field changed by any path that does not go
        # through `apply_preset`, or a config written before the field existed all
        # leave a stale label behind. The Settings dialog already ignores it and
        # re-derives (which is why the maintainer's `Archival exact` display was
        # correct while `Debug logging` was on) — but the REPORT was writing the
        # stored string, so a rip's permanent record could name a goal the
        # settings it ran under never matched. Found while checking the rig
        # findings of 2026-08-05.
        #
        # The fields are authoritative; the label is a view of them. `detect_goal`
        # is the same function the dialog uses, so the record and the screen
        # cannot disagree.
        "rip_goal": _derived_rip_goal(config),
        # And we do not DISCARD the stored value: if it disagreed, that fact is
        # part of the diagnosis (CLAUDE.md — capture everything, never silently).
        # Absent when it agrees, so a normal report is not noisier for it.
        **_stale_rip_goal(config),
        "read_offset": {
            "configured": configured_offset,
            "applied": applied,
            "effective": read_offset_effective,
        },
    }
    # MP3's VBR quality is only meaningful when MP3 is the chosen output.
    if fmt == "mp3":
        settings["mp3_vbr_quality"] = getattr(config, "mp3_vbr_quality", None)
    return settings


def build_gates(
    *,
    ctdb_enabled: bool,
    flac_verify_enabled: bool,
    backend_self_verifies: bool,
    recompress_enabled: bool,
    backend_maxes_compression: bool,
    transcode_requested: bool,
) -> dict:
    """Build ``verification.gates``: WHY each verification sub-block is or isn't
    populated.

    A `null` result sub-block (``flac_integrity``, ``transcode``, ``derived``…)
    is ambiguous on its own — did the check fail to run, or was it never meant to?
    This turns each into an explicit state the report is self-describing about, so
    "didn't run" is never misread as "passed" (or "failed"). Pure; never raises.
    """
    if not flac_verify_enabled:
        flac_gate = "disabled"
    elif backend_self_verifies:
        flac_gate = "backend self-verifies"
    else:
        flac_gate = "ran"
    if not recompress_enabled:
        recompress_gate = "disabled"
    elif backend_maxes_compression:
        recompress_gate = "backend already maxes compression"
    else:
        recompress_gate = "ran"
    return {
        "ctdb": "ran" if ctdb_enabled else "disabled",
        "flac_integrity": flac_gate,
        "recompress": recompress_gate,
        "derived": "ran" if transcode_requested else "flac-only",
    }


def _eta_trace_block(eta_trace: list | None, timing: dict | None) -> dict | None:
    """Assemble the report's ``eta_trace`` block from the recorded samples.

    Backfills each sample with ``actual_remaining_seconds`` — the time that
    ACTUALLY remained at that moment, computed from the rip's real finish
    (``timing.finished_at``) minus the sample's ``at``. That turns the trace into
    a direct predicted-vs-actual record (our ``our_eta_seconds`` vs the truth) the
    maintainer can eyeball or mine for a better model later. Pure; never raises —
    a sample with an unparseable/absent timestamp simply omits the actual field.
    """
    if not eta_trace:
        return None
    from datetime import datetime

    finish_dt = None
    finished_at = (timing or {}).get("finished_at")
    if isinstance(finished_at, str) and finished_at:
        try:
            finish_dt = datetime.fromisoformat(finished_at)
        except ValueError:
            finish_dt = None

    samples: list[dict] = []
    for raw in eta_trace:
        sample = dict(raw)
        at = sample.get("at")
        if finish_dt is not None and isinstance(at, str) and at:
            try:
                remaining = (finish_dt - datetime.fromisoformat(at)).total_seconds()
                sample["actual_remaining_seconds"] = max(0, round(remaining))
            except (ValueError, TypeError):
                pass
        samples.append(sample)
    return {
        "note": (
            "Per-sample ETA record for analysis, not display. "
            "'our_eta_seconds' is Platterpus's smoothed album estimate; "
            "'actual_remaining_seconds' is what really remained (finish − 'at') "
            "so estimate-vs-actual is directly visible; 'cyanrip_eta' is cyanrip's "
            "own per-op estimate (untrusted); 'read_speed' is the -S value in "
            "effect (0 = drive max); 'track'/'activity' are the event context for "
            "a jump; 'at' is the PC wall-clock time. 'state' names the branch that "
            "produced the sample — computed (a fresh rate measurement), "
            "held_no_rate / held_over_ceiling (the previous estimate re-shown), "
            "rereading (a secure re-read has the album bar pinned) or stalled "
            "(neither liveness signal moved) — so a held value is never mistaken "
            "for a measurement; 'reread_pass' counts restarts of the current "
            "track's read (0 = first read). Compare against 'timing'."
        ),
        "samples": samples,
    }


def _ripper_log_verify_block(verification: object | None) -> dict | None:
    """Serialize the ripper's verdict on its own log. ``None`` when never attempted.

    Reads attributes defensively (``getattr``) for the same reason every serializer
    here does: this builder is pure and must never raise, and it is handed a value
    the GUI assembled from a worker.

    ``None`` is a THIRD state and is deliberately distinguishable from
    ``not_determined``: a rip that never reached the verification step (cancelled
    before a log existed, or a report written by an older build) is not a rip whose
    log could not be verified. Both are non-passes and neither is a failure.
    """
    if verification is None:
        return None
    argv = getattr(verification, "argv", ()) or ()
    return {
        # `verified` / `failed` / `not_determined`. Tri-state as always: an absent
        # verifier is not a failed verification.
        "verdict": str(getattr(verification, "verdict", "") or "") or None,
        "detail": str(getattr(verification, "detail", "") or "") or None,
        "log": str(getattr(verification, "log_path", "") or "") or None,
        # The full diagnostic set for an external call, so a `failed` verdict is an
        # accusation the user can check rather than one they must take on trust.
        # Tri-state exit code — `null` for a child never reaped, never written as 0.
        "exit_code": getattr(verification, "exit_code", None),
        "argv": [str(part) for part in argv],
        "output": str(getattr(verification, "output", "") or "") or None,
    }


def _ripper_approval(rip_log: object) -> RipperApproval:
    """Whether this rip's ripper is the build both projects verified. Never raises.

    Separate from :func:`_ripper_identity` on purpose: "is it our fork" and "is it
    the build a closed round approved" are different questions, and answering the
    second with the first is how an unapproved fork build would have read as fine.
    """
    return approve_rip_log(rip_log)


def _ripper_identity(rip_log: object) -> RipperIdentity:
    """Classify the ripper binary behind this rip.

    A thin pass-through to the shared classifier so the report, the EAC-style
    log and the live rip panel cannot describe the same binary differently.
    ``getattr`` because a caller may hand us a stand-in ``RipLog`` from an older
    parse that predates these fields.
    """
    return identify_ripper(
        getattr(rip_log, "log_creator", "") or "",
        getattr(rip_log, "ripper_build", "") or "",
    )


def _build(
    rip_log: object,
    ctdb_result: object | None,
    generated_at: str,
    timing: dict | None = None,
    debug_log: dict | None = None,
    flac_verify_result: object | None = None,
    transcode_result: object | None = None,
    checksums: dict | None = None,
    derived_verify_result: object | None = None,
    read_speed: dict | None = None,
    eta_trace: list | None = None,
    *,
    recompress_result: object | None = None,
    cover_art_result: object | None = None,
    tagging_result: object | None = None,
    secure_rerip: dict | None = None,
    outcome: dict | None = None,
    settings: dict | None = None,
    disc: dict | None = None,
    environment: EnvironmentBlock | None = None,
    gates: dict | None = None,
    log_parse: dict | None = None,
    disc_track_total: int | None = None,
    artifacts: ArtifactsBlock | None = None,
    #: v18: the RIPPER's verdict on its own log, from `adapters.ripper_log_verify`
    #: — an independent witness, unlike our own SHA-256 footer check. Typed
    #: `object` because this pure builder must not import an adapter.
    ripper_log_verification: object | None = None,
) -> dict:
    # The JSON's verdict must be the SAME claim the window makes, so it is given
    # the same two extra facts: the disc's own track count (the only denominator a
    # stopped rip cannot shrink) and the rip's outcome. Without them a cancelled
    # 2-of-14 rip serialised `{"level": "ok", "message": "Bit-perfect: all 2
    # tracks verified against AccurateRip"}` (found on the rig, 2026-07-30).
    message, level = accuraterip_verdict(
        rip_log,
        disc_track_total=disc_track_total,
        outcome_status=(
            str(outcome.get("status") or "") if isinstance(outcome, dict) else ""
        ),
    )
    info = getattr(rip_log, "ripping_info", None)
    # Serialized once, into a local, so the block the report shows and the `issues`
    # entry derived from it cannot describe the same verdict two ways — the same
    # reason `rip_block` and `log_parse_block` are hoisted below.
    verify_block = _ripper_log_verify_block(ripper_log_verification)
    # Serialize the verification sub-blocks once, into locals, so both the
    # `verification` block below and the derived `issues` list read the SAME
    # values (they can never disagree). The read-speed block carries the dynamic
    # secure-re-rip provenance (why the targeted re-rip did/didn't run) when the
    # GUI supplied it.
    flac_integrity = _flac_verify(flac_verify_result)
    transcode = _transcode(transcode_result)
    derived = _derived_verify(derived_verify_result)
    recompress = _recompress(recompress_result)
    ctdb = _ctdb(ctdb_result)
    cover_art = _cover_art(cover_art_result)
    # Tagging feeds `issues` ONLY — it deliberately gets no block of its own. The
    # severity-tagged `issues` list is already the report's declared home for
    # "what went wrong" (report_types.IssueBlock), and every `verification`
    # sub-block is part of a key set consumers and tests pin exactly, so a new one
    # would be a wire-format change for a fact that fits an existing field.
    tagging = _tagging(tagging_result)
    read_speed_block = dict(read_speed) if read_speed else None
    if secure_rerip is not None:
        read_speed_block = read_speed_block or {}
        read_speed_block["secure_rerip"] = secure_rerip
    # The environment defaults to a live probe (Python/OS/PySide6/channel) when
    # the caller didn't supply one — so a report always carries it — but a test
    # can inject a fixed dict for determinism.
    if environment is None:
        environment = build_info.environment_report()
    # How many tracks this rip was supposed to produce, recorded rather than
    # merely used. `disc_track_total` reached this builder only to feed the
    # verdict, so the JSON's ONLY track count was `len(tracks)` — the log's own
    # list, which a cancel shrinks. That is the same missing denominator that
    # has now been fixed on four surfaces, and a reader of the JSON alone had
    # to parse it out of the English in `verdict.message` to know a 2-track
    # report described a 14-track disc. State it as a number.
    tracks_in_report = len(getattr(rip_log, "tracks", ()) or ())
    completeness = {
        "tracks_expected": disc_track_total,
        "tracks_in_report": tracks_in_report,
        # `==`, not `>=`. With `>=`, a report carrying MORE tracks than the rip was
        # asked for read as "complete" — but a track count that exceeds the request
        # means the report and the request disagree, which is a fact to surface, not
        # to round up into success. `tracks_in_report` is right there for a reader
        # who wants to see which way it differs.
        "complete": (
            None if not disc_track_total else tracks_in_report == disc_track_total
        ),
        "note": (
            "tracks_expected is what the rip was ASKED for — the disc's track "
            "count, or fewer when the user ticked a subset in the Rip? column. "
            "null means it wasn't known to this writer (an in-progress write, "
            "or a log parsed offline); it is NOT a claim that the rip was whole."
        ),
    }
    # The `rip` and `log_parse` blocks are built HERE, into locals, for the same
    # reason the verification sub-blocks above are: `issues` derives from them, and
    # a second construction site would let the enumerated "what went wrong" list
    # and the block it claims to summarise disagree. They are serialised into the
    # returned dict below by name, never rebuilt.
    log_parse_block = _log_parse(rip_log, log_parse)
    rip_block = _rip_block(rip_log, info)
    issues = _issues(
        outcome=outcome,
        verdict_level=level,
        ctdb=ctdb,
        flac_integrity=flac_integrity,
        derived=derived,
        transcode=transcode,
        cover_art=cover_art,
        tagging=tagging,
        read_speed=read_speed_block,
        heavy_reread_tracks=tracks_needing_heavy_reread(rip_log),
        log_truncated=bool(getattr(rip_log, "log_truncated", False)),
        recompress=recompress,
        log_parse=log_parse_block,
        completeness=completeness,
        rip=rip_block,
        disc=disc,
        artifacts=artifacts,
        ripper_log_verification=verify_block,
        dependencies=(environment or {}).get("dependencies"),
    )
    built: dict = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generator": {
            "name": "platterpus",
            "version": __version__,
            # Ties this report to an exact build (git short-SHA, or "source" on a
            # checkout). Debug aid only — NOT part of any EAC-parity/bit-perfection
            # claim (maintainer's ask, 0.4.10).
            "build_fingerprint": build_info.build_fingerprint(),
        },
        "generated_at": generated_at or None,
        # EVERY PROBLEM THIS RIP NOTICED, IN ONE PLACE (schema v16).
        #
        # Placed third — before `outcome`, before the verdict, before the tracks —
        # because it is the first thing anyone debugging a rip should read, and
        # burying it would recreate the situation it was added to fix: diagnostics
        # spread across `outcome.failure_hint`, `log_parse.note`, `ctdb.error`, the
        # per-track `issues` and the verification blocks, none of them enumerated,
        # so answering "did anything go wrong?" required knowing where to look.
        #
        # Read from the process-wide collector, which also wrote every one of these
        # to the text log as it happened — one call site, two sinks, so the two
        # artifacts cannot describe the same event differently.
        "diagnostics": diagnostics.to_report_block(),
        # v18: THE RIPPER'S OWN VERDICT ON ITS OWN LOG.
        #
        # An independent witness. Everything else here is our measurement of our
        # work; this is the dependency checking its own artifact with its own
        # checksum and its own code. The cyanrip fork found why that matters (round
        # 7 lap 10, H1/J3): our `log_integrity` self-check reported *"the EAC-style
        # log matches its own SHA-256 footer"* on a rip that shipped a cyanrip log
        # cyanrip itself would reject, because we had appended the auto-fix addendum
        # past its `Log FUN512:` line. A closed loop agrees with itself.
        #
        # `null` means the verification never ran (a cancelled rip, an old report);
        # `not_determined` means it ran and could not answer. Neither is a pass.
        "ripper_log_verification": verify_block,
        # The PROCESS result (success/cancelled/failed + hint + auto-heal). The
        # single most-requested support datum; distinct from `verdict`/
        # `health_status`, which describe AccurateRip / the rip log, not the run.
        "outcome": outcome,
        "timing": timing,
        # What the host ran it on + which exact build (first bug-report question).
        "environment": environment,
        # What the GUI ASKED the ripper for (vs. what the log says the drive did).
        "settings": settings,
        # Provenance: unknown-mode + the MusicBrainz release id this rip used.
        "disc": disc,
        "log_creator": getattr(rip_log, "log_creator", "") or None,
        "verdict": {"level": level, "message": message or None},
        # Immediately after the verdict, because it is the verdict's denominator
        # — the number the sentence above is measured against, in machine-readable
        # form so no consumer has to re-derive it from `len(tracks)`.
        "completeness": completeness,
        "rip": rip_block,
        "accuraterip_summary": getattr(rip_log, "accuraterip_summary", "") or None,
        "partially_accurate_summary": (
            getattr(rip_log, "partially_accurate_summary", "") or None
        ),
        # v20: the ripper's own fraction, verbatim, beside our sentence about it.
        "partially_accurate_reported": (
            getattr(rip_log, "partially_accurate_reported", "") or None
        ),
        "disc_duration": getattr(rip_log, "disc_duration", "") or None,
        "paranoia_counts": dict(getattr(rip_log, "paranoia_counts", {}) or {}) or None,
        # Adaptive read-speed ladder history: the speed / -Z each pass used and
        # whether it read clean (see read_speed_ladder.attempts_to_report). None
        # on a normal single-pass rip. `retried_tracks` records the per-track
        # auto-fix (each unstable track re-ripped alone with a harder -Z; whether
        # it converged and whether the better FLAC replaced the original).
        # `unstable_tracks` lists tracks the auto-fix could NOT rescue, and
        # `unresolved: true` FLAGS the disc when any remain (or a pass never read
        # clean) — surfaced, never papered over. In dynamic mode this also carries
        # a `secure_rerip` sub-block explaining why the targeted secure re-rip did
        # or didn't run (e.g. skipped because the disc isn't in AccurateRip).
        "read_speed": read_speed_block,
        # ETA trace kept "for posterity": a throttled series of samples pairing
        # the PC wall-clock time with our smoothed estimate, cyanrip's own ETA, the
        # read speed, and the event context (track + phase). Each sample is
        # backfilled with the ACTUAL time that remained (from the real finish) so
        # predicted-vs-actual is directly visible. None on a rip too short to
        # sample. NOT the estimate shown live.
        "eta_trace": _eta_trace_block(eta_trace, timing),
        # Whole-disc loudness (integrated LUFS / LRA / true peak) from cyanrip's
        # "Album Loudness Summary"; per-track loudness lives in each track's
        # `replaygain`. None when absent (e.g. whipper logs).
        "album_loudness": dict(getattr(rip_log, "album_loudness", {}) or {}) or None,
        "health_status": getattr(rip_log, "health_status", "") or None,
        "sha256_hash": getattr(rip_log, "sha256_hash", "") or None,
        # cyanrip's own log signature ("Log FUN512:") — its analogue to EAC's
        # signed log checksum, the one archival-forensic field we were dropping.
        "log_checksum": getattr(rip_log, "log_checksum", "") or None,
        # Whether the human ``.log`` parsed cleanly. A degraded read (a stray
        # non-UTF-8 byte forced ``errors="replace"``, or nothing parsed) is flagged
        # here so a thin/empty report isn't mistaken for a clean rip.
        "log_parse": log_parse_block,
        "tracks": [_track(t) for t in (getattr(rip_log, "tracks", ()) or ())],
        "ctdb": ctdb,
        # The full post-rip verification suite in one place: AccurateRip lives in
        # `verdict`/`tracks`, CTDB stays at `ctdb` (back-compat), and this block
        # adds the FLAC-integrity decode + the transcode + re-compress outcomes so
        # a reader sees every check the master (and any derived files) passed.
        # `gates` says WHY each result is or isn't populated ("ran" / "disabled" /
        # "backend self-verifies" / "flac-only"), so a null is never ambiguous.
        "verification": {
            "gates": gates,
            "flac_integrity": flac_integrity,
            "transcode": transcode,
            "derived": derived,
            "recompress": recompress,
        },
        # The front-cover result — hits "good cover image" directly: found / why
        # not / how many files it was embedded in. None on a FLAC-only rip with no
        # art requested (see _cover_art).
        "cover_art": cover_art,
        # One consolidated, severity-tagged "what went wrong" list, derived from
        # the blocks above — the first thing a triager opens. Empty on a clean rip.
        "issues": issues,
        # Per-file SHA256 for long-term integrity checking (bit-rot). Embedded
        # here rather than a separate checksums.sha256 sidecar — one debug file.
        "checksums": (dict(checksums) if checksums else None),
        # Bulky, so it sits last: the embedded session log that makes this
        # report a self-contained debug record (None when not captured), and
        # the verbatim text of the companion files written beside it (None when
        # the caller supplied no paths — e.g. the `--compare` CLI).
        "debug": debug_log,
        "artifacts": artifacts,
    }
    return _ordered_for_reading(built)


# The three blocks that dwarf everything else, biggest LAST. Measured on a real
# 14-track rip: `debug` 1.23 MB, `artifacts` 100 KB, `eta_trace` 103 KB — together
# 95% of a 1.5 MB report.
_BULK_KEYS_LAST: Final[tuple[str, ...]] = ("eta_trace", "artifacts", "debug")

# What a reader wants FIRST: is this report trustworthy, what happened, what went
# wrong. Anything not named here keeps its existing relative position in the middle.
_LEAD_KEYS_FIRST: Final[tuple[str, ...]] = (
    "schema_version",
    "generator",
    "generated_at",
    "self_check",
    "outcome",
    "verdict",
    "completeness",
    "diagnostics",
    "issues",
    "health_status",
    "accuraterip_summary",
    "partially_accurate_summary",
    "partially_accurate_reported",
    "ripper_log_verification",
)


def _ordered_for_reading(report: dict) -> dict:
    """Reorder the top-level keys so a PARTIAL read answers the useful questions.

    **THE ONLY CONSUMER OF THIS FILE IS AN ANALYST READING IT** (the maintainer's
    framing: *"You're the only one reading the JSON file; make it efficient for
    you."*). JSON objects are order-preserving on the wire, so key order decides
    what a `head -c 40000` can see — and the measured order was hostile:

    * `self_check`, which says whether the report itself is *trustworthy*, sat at
      byte **1,515,002 of 1,516,421** — dead last, behind 1.23 MB of `debug`;
    * `tracks`, `issues` and `checksums` all sat past byte 147,000, pushed there by
      a 103 KB `eta_trace` wedged in at 14 KB.

    So: the decisive small blocks first, the three bulk blocks last, everything else
    keeps its relative order. **No key is added or removed** — this is purely the
    order they serialize in, so every existing consumer and every key-set test is
    unaffected. Pure; never raises.
    """
    lead = [k for k in _LEAD_KEYS_FIRST if k in report]
    bulk = [k for k in _BULK_KEYS_LAST if k in report]
    spoken_for = {*lead, *bulk}
    middle = [k for k in report if k not in spoken_for]
    return {k: report[k] for k in (*lead, *middle, *bulk)}


def _rip_block(rip_log: object, info: object) -> dict:
    """The ``rip`` block: what the drive and the ripper binary actually did.

    Built by its own function rather than inline in :func:`_build`'s dict literal
    because ``issues`` derives from it — a second construction site would let the
    enumerated "what went wrong" list and the block it summarises disagree.
    """
    identity = _ripper_identity(rip_log)
    approval = _ripper_approval(rip_log)
    return {
        "drive": getattr(info, "drive", "") or None,
        "extraction_engine": getattr(info, "extraction_engine", "") or None,
        "read_offset_correction": getattr(info, "read_offset_correction", None),
        "defeat_audio_cache": getattr(info, "defeat_audio_cache", None),
        "overread_lead_out": getattr(info, "overread_lead_out", None),
        "gap_detection": getattr(info, "gap_detection", "") or None,
        "cd_r_detected": getattr(info, "cd_r_detected", None),
        # Whether the drive reports it can change read speed. False means
        # cyanrip's `-S` aborts the rip, so the ladder escalates via `-Z`
        # only (the BDR-209D is speed-locked — real-hardware finding). None
        # when the log didn't say (older cyanrip / whipper).
        "speed_changeable": getattr(info, "speed_changeable", None),
        # v11: three facts that reach the human-readable EAC-layout log and were
        # absent from the machine record, so an automated consumer could not see
        # what the rip actually did. `c2_pointers` is the field the fork's §2.5
        # change exists to fill: None = capability only / nothing stated, False =
        # explicitly not used, which is EAC's "No".
        "c2_pointers": getattr(info, "c2_pointers", None),
        "paranoia_level": getattr(info, "paranoia_level", "") or None,
        "overread_mode": getattr(info, "overread_mode", "") or None,
        # Which cyanrip BINARY produced this rip ("release", "fork", a git
        # describe). The only provenance separating an official build from a local
        # one, and they can differ in pre-gap metadata and peak values.
        "ripper_build": getattr(rip_log, "ripper_build", "") or None,
        # v14: the ripper's OWN completion verdict, counts and reason —
        # not our count of how many tracks its log happened to mention.
        # Tri-state: `null` means the footer was absent, which is what a
        # killed rip looks like, and must never be read as `false`
        # ("finished, and reported failure"). Per the fork (handshake
        # round 4, Q10) this footer is the only structural difference
        # between a truncated log and a short one — the cue cannot tell.
        "rip_completed": getattr(rip_log, "rip_completed", None),
        "rip_completed_tracks": getattr(rip_log, "rip_completed_tracks", None),
        "rip_completed_total": getattr(rip_log, "rip_completed_total", None),
        "rip_completed_reason": getattr(rip_log, "rip_completed_reason", "") or None,
        # The argv the ripper reports RECEIVING (fork-only). We separately
        # record the argv we spawned it with in `outcome.ripper_argv`; when
        # those two disagree, something between us mangled an argument, and
        # that gap is invisible from either end alone.
        "invoked_as": getattr(rip_log, "invoked_as", "") or None,
        # v17: the ripper's OWN statement of what it was built from, and who it was
        # told the caller was. Both fork-only, both verbatim, both `null` on stock.
        #
        # `ripper_handshake_note` is a second, INDEPENDENT witness to provenance:
        # `ripper_handshake_approval` (v15) is *our* verdict on the banner, while this
        # is what the fork's build system compiled into the binary. When the two
        # disagree, the disagreement is the finding — and a build from an open round
        # says so here permanently, which no banner can.
        # v19: the fork's stall watchdog verdict, verbatim. `null` on stock, which
        # never prints the line — a THIRD state beside "none" and a count, because
        # "no stalls measured" and "stalls not measured" are different claims.
        "read_stalls": getattr(rip_log, "read_stalls", "") or None,
        # The count inside it, tri-state: 0 = measured none, N = that many stalled,
        # null = not measured / not reported / a shape we did not recognise. Never
        # replaces the verbatim text above — an unrecognised shape must leave the
        # ripper's own sentence intact rather than reduce it to a wrong number.
        "read_stalls_count": getattr(rip_log, "read_stalls_count", None),
        "ripper_handshake_note": getattr(rip_log, "handshake_note", "") or None,
        "ripper_consumer": getattr(rip_log, "consumer", "") or None,
        # v13: the *classified* answer, so a consumer does not have to know
        # which tags mean "our fork". Tri-state on purpose — `null` is "not
        # determined", and must never be read as `false`. An unrecognised
        # tag is an absence of evidence, not evidence of a stock binary.
        "ripper_is_platterpus_fork": identity.is_fork,
        "ripper_identity": identity.kind,
        "ripper_identity_detail": identity.detail,
        # v15: is this the build BOTH projects affirmatively verified?
        #
        # A different question from `ripper_identity`, which answers "fork,
        # stock, or undetermined". This answers "the build a closed handshake
        # round approved" — and it is checked HERE, at rip time, because a
        # release gate runs once on a machine that never rips a disc. Tri-state
        # like everything else about provenance: `not_determined` for an absent
        # or unreadable build tag is a real answer, and never a pass.
        "ripper_handshake_approval": approval.verdict,
        "ripper_handshake_approval_detail": approval.detail,
        "ripper_handshake_approved_build": approval.approved_banner,
        "ripper_handshake_approved_for_platterpus": approval.approved_for_platterpus,
        "ripper_handshake_approved_by_round": approval.approved_by_round,
        "creation_date": getattr(rip_log, "creation_date", "") or None,
        # TOC-derived disc identity (cyanrip's "DiscID:"/"CDDB ID:" lines).
        # The truest "same physical disc" key — stable across re-rips and
        # independent of any MusicBrainz release edit — so the re-rip
        # comparison (rip_compare) keys on the MB Disc ID first. None on a
        # whipper log / when cyanrip didn't print them.
        "musicbrainz_disc_id": getattr(rip_log, "disc_id", "") or None,
        "cddb_id": getattr(rip_log, "cddb_id", "") or None,
        # The release id the RIPPER resolved and used, off its own header — the
        # witness that its parse of our single colon-delimited `-a` blob put our
        # release id where we meant it to. `outcome.ripper_argv` shows what it
        # received; only this shows what it used. `issues` compares the two.
        "ripper_release_id": getattr(rip_log, "release_id", "") or None,
    }


def _track(track: object) -> dict:
    return {
        "number": getattr(track, "number", None),
        "filename": getattr(track, "filename", "") or None,
        "test_crc": getattr(track, "test_crc", "") or None,
        "copy_crc": getattr(track, "copy_crc", "") or None,
        "status": getattr(track, "status", "") or None,
        # How many read passes cyanrip needed (its "(after N rips)"); None for
        # whipper logs / a clean single-pass cyanrip track.
        "rip_count": getattr(track, "rip_count", None),
        # cyanrip's -Z secure re-read verdict: True = N reads' checksums agreed;
        # False = it hit the repeat limit without any two agreeing (the reliable
        # per-track read-instability flag); None = -Z off / older log. Was parsed
        # but not serialized before v9 — the read-effort signal in machine form.
        "secure_rerip_converged": getattr(track, "secure_rerip_converged", None),
        # Per-track extraction diagnostics cyanrip logs (all None on whipper):
        # the drive speed this track read at (×), the extraction quality (%),
        # whether pre-emphasis was flagged, and the sample peak level. Surfaced
        # so a marginal track's read conditions are visible in the report.
        "extraction_speed": getattr(track, "extraction_speed", None),
        "extraction_quality": getattr(track, "extraction_quality", None),
        "pre_emphasis": getattr(track, "pre_emphasis", None),
        "peak_level": getattr(track, "peak_level", None),
        # v10. Five facts the parser has been reading and the machine record
        # dropped — the JSON is meant to be the one file that explains a rip, so
        # a field that reaches the human-readable EAC log and not this file is a
        # hole in that promise.
        #
        # How long extraction took (seconds). Fork-only — deployed cyanrip 0.9.3
        # does not print it, so it stays None there. Deliberately NOT converted
        # into `extraction_speed`: what the fork's interval covers is unknown,
        # and a derived multiple would be a guess wearing EAC's label.
        "extraction_elapsed_seconds": getattr(
            track, "extraction_elapsed_seconds", None
        ),
        # Frames of SILENCE the ripper appended because it could not read the
        # disc that far. This one is NOT fork-only — 0.9.3 prints it, on the last
        # track, whenever overread is off, and both committed reference rips
        # contain it. It says the track's final frames are fabricated rather than
        # disc audio, which is the most archival-relevant per-track fact we hold,
        # and it reached the EAC-layout log but never the JSON.
        "appended_silence_frames": getattr(track, "appended_silence_frames", None),
        # Absolute disc geometry (sectors). EAC's "TOC of the extracted CD" is
        # derived from these exactly, so without them the JSON could not
        # reconstruct a table the .log already shows.
        "start_sector": getattr(track, "start_sector", None),
        "end_sector": getattr(track, "end_sector", None),
        # The pre-gap's LENGTH (0 = the ripper measured none; None = it reported
        # nothing usable) and, separately, the absolute position its INDEX 00
        # begins at. Both, because they are different quantities and v10 shipped
        # the position under the length's name — an 89x over-claim in the EAC row
        # on a real disc (see parsers.rip_log.TrackResult for the numbers).
        "pregap_sectors": getattr(track, "pregap_sectors", None),
        "pregap_start_lsn": getattr(track, "pregap_start_lsn", None),
        # Three states, never two. "unknown" (the ripper tried and could not
        # tell) must not serialize as a 0-length gap — see TrackResult.
        "pregap_state": getattr(track, "pregap_state", "") or None,
        "pregap_unknown_reason": getattr(track, "pregap_unknown_reason", "") or None,
        "pregap_length_frames": getattr(track, "pregap_length_frames", None),
        "pregap_source": getattr(track, "pregap_source", "") or None,
        # ReplayGain / loudness tags cyanrip wrote into the FLAC (raw strings) —
        # the machine-readable record of what was tagged. None when absent.
        "replaygain": (dict(getattr(track, "replaygain", {})) or None),
        # The shared confidence>=1 rule — same as the banner and disc panel.
        "accuraterip_verified": track_accuraterip_verified(track),
        # cyanrip's per-track "Accurip:" status text — the only thing that says
        # whether a lookup happened. Without it a consumer cannot tell "compared
        # and disagreed" from "never asked", which is the distinction the on-screen
        # cell and the EAC row were both getting wrong.
        "accuraterip_lookup": getattr(track, "accuraterip_lookup", None),
        "accuraterip": {
            "v1": _ar(getattr(track, "accuraterip_v1", None)),
            "v2": _ar(getattr(track, "accuraterip_v2", None)),
            # The +450-frame offset-pressing variant ("partially accurately
            # ripped"). Surfaced as data; NOT counted as a plain verified match.
            "offset_450": _ar(getattr(track, "accuraterip_offset", None)),
        },
    }


def _ar(ar: object) -> dict | None:
    if ar is None:
        return None
    return {
        "result": getattr(ar, "result", "") or None,
        "confidence": getattr(ar, "confidence", None),
        "local_crc": getattr(ar, "local_crc", None),
        "remote_crc": getattr(ar, "remote_crc", None),
    }


def _hex_crc(value: object) -> str | None:
    """Render a CTDB integer CRC as 8-digit uppercase hex (matches the
    AccurateRip CRC style elsewhere in the report); None passes through."""
    if isinstance(value, int):
        return f"{value:08X}"
    return None


def _failure_details(result: object | None) -> list[dict] | None:
    """Serialize a result's ``failure_details`` — the tool's own words per file.

    Every post-rip adapter that runs an external tool now carries, per failed file,
    that tool's exit code, exact argv and complete output. This lifts them into the
    JSON so a report says *why* a file failed rather than only *that* it did.

    ``None`` (not ``[]``) when the adapter predates the field, so a reader can tell
    "no failures" from "this writer could not say". Never raises: reads defensively
    and skips anything that will not serialize.
    """
    details = getattr(result, "failure_details", None)
    if not details:
        return None
    out: list[dict] = []
    for detail in details:
        to_json = getattr(detail, "to_json", None)
        if callable(to_json):
            try:
                block = to_json()
            except Exception:  # noqa: BLE001 — a report must never fail to build
                log.exception("rip_report: could not serialize a failure detail")
                continue
            if isinstance(block, dict):
                out.append(block)
    return out or None


def _flac_verify(result: object | None) -> dict | None:
    """Serialize a FlacVerifyResult (decode==stored-MD5 test of the masters).

    ``ran`` distinguishes "verified and passed/failed" from "couldn't run"
    (e.g. the ``flac`` binary is absent); ``failures`` lists any files that
    failed the decode test. None when no verify was attempted.
    """
    if result is None:
        return None
    failures = getattr(result, "failures", ()) or ()
    return {
        "ran": bool(getattr(result, "ran", False)),
        "ok": bool(getattr(result, "ok", False)),
        "checked": getattr(result, "checked", 0),
        "failures": [str(p) for p in failures],
        # What `flac --test` ACTUALLY SAID about each failed file. Before this the
        # report named the files and could not name the reason, so "3 file(s) failed"
        # was the whole diagnosis — see `adapters.tool_run`.
        "failure_details": _failure_details(result),
        "error": getattr(result, "error", "") or None,
    }


def _transcode(result: object | None) -> dict | None:
    """Serialize a TranscodeResult (deriving MP3/WavPack/WAV from the master).

    None when the rip was FLAC-only (no transcode happened)."""
    if result is None:
        return None
    failures = getattr(result, "failures", ()) or ()
    return {
        "ran": bool(getattr(result, "ran", False)),
        "ok": bool(getattr(result, "ok", False)),
        "transcoded": getattr(result, "transcoded", 0),
        "failures": [str(p) for p in failures],
        # ffmpeg's own exit code, argv and output per failed file.
        "failure_details": _failure_details(result),
        "error": getattr(result, "error", "") or None,
    }


def _derived_verify(result: object | None) -> dict | None:
    """Serialize a DerivedVerifyResult (proof of the MP3/WavPack/WAV outputs).

    ``lossless`` records which proof was applied so a reader is never misled:
    for WAV/WavPack ``ok`` means bit-identical to the FLAC master; for MP3 it
    means every file decoded cleanly and the set is complete — explicitly NOT
    bit-identity (a lossy file can't match). ``mismatches`` (lossless only) are
    derived files whose PCM differs from the master — a real defect. None when
    the rip was FLAC-only (nothing derived)."""
    if result is None:
        return None
    failures = getattr(result, "failures", ()) or ()
    mismatches = getattr(result, "mismatches", ()) or ()
    lossless = bool(getattr(result, "lossless", False))
    return {
        "format": getattr(result, "fmt", "") or None,
        "lossless": lossless,
        # What "ok" attests, spelled out so the JSON is self-describing.
        "proof": (
            "bit-identical PCM vs FLAC master"
            if lossless
            else "decodes cleanly + complete (lossy; NOT bit-identical)"
        ),
        "ran": bool(getattr(result, "ran", False)),
        "ok": bool(getattr(result, "ok", False)),
        "complete": bool(getattr(result, "complete", False)),
        "checked": getattr(result, "checked", 0),
        "expected": getattr(result, "expected", 0),
        "failures": [str(p) for p in failures],
        "mismatches": [str(p) for p in mismatches],
        "error": getattr(result, "error", "") or None,
    }


def _ctdb(result: object | None) -> dict | None:
    if result is None:
        return None
    verdict = getattr(getattr(result, "verdict", None), "value", None)
    db_crcs = getattr(result, "db_crcs", ()) or ()
    return {
        "verdict": verdict,
        "confidence": getattr(result, "confidence", None),
        "trustworthy": getattr(result, "trustworthy", None),
        "crc_validated": getattr(result, "crc_validated", None),
        # Include the CRCs + message so a consumer can audit a match, not just
        # see the verdict (hex to match the per-track AccurateRip CRC style).
        "our_crc": _hex_crc(getattr(result, "our_crc", None)),
        "matched_crc": _hex_crc(getattr(result, "matched_crc", None)),
        # The database's CRC(s) for this TOC + how many entries it had. With
        # `our_crc` this makes a no_match self-diagnosing: a reader (or the
        # KDD-16 calibration) sees exactly what we computed vs what the DB
        # expected, without a second live lookup.
        "entry_count": len(db_crcs),
        "db_crcs": [_hex_crc(c) for c in db_crcs],
        "message": getattr(result, "message", "") or None,
    }


def _recompress(result: object | None) -> dict | None:
    """Serialize a RecompressResult (opt-in ``flac -8`` re-encode of the masters).

    It mutates the archival masters, so its outcome belongs in the report. ``ok``
    is true only when every file re-encoded (or none needed to) with no error.
    None when re-compress wasn't run (the common case). Never raises."""
    if result is None:
        return None
    failures = getattr(result, "failures", ()) or ()
    error = getattr(result, "error", "") or None
    # `ran` READ OFF THE RESULT, never hardcoded.
    #
    # This was `"ran": True`, which is a wrong answer in a real case: when `flac`
    # is missing the step cannot run at all, `RecompressResult.error` is set, and
    # `.ran` is False — but the report said `ran: true, ok: false`, i.e. "we
    # re-encoded your archival masters and it went badly" instead of "we never
    # touched them". For the one step that MUTATES the masters, that is the worst
    # possible direction to be wrong in. Every sibling serializer here already
    # read `.ran`; this one alone asserted it.
    ran = bool(getattr(result, "ran", True))
    return {
        "ran": ran,
        "ok": ran and (not failures) and (error is None),
        "reencoded": getattr(result, "reencoded", 0),
        "failures": [str(p) for p in failures],
        # This step REWRITES the archival master, so a bare "it failed" is least
        # acceptable here of anywhere: each entry says whether flac refused, flac
        # claimed success and wrote nothing, or the atomic swap-in failed.
        "failure_details": _failure_details(result),
        "error": error,
    }


def _cover_art(result: object | None) -> dict | None:
    """Serialize a CoverArtResult (the front-cover fetch/embed outcome).

    Duck-typed via ``getattr`` (like every other serializer here) so it tolerates
    a partial/None object and never raises — the biggest previously-unstructured
    field, and the one that answers "did I get a good cover image?". ``found`` is
    True/False once art was attempted, None when it wasn't; ``reason`` is a short
    machine code (``"ok"``/``"404"``/``"oversize"``/``"not-image"``/
    ``"network"``…). None on a rip that neither embedded nor saved art."""
    if result is None:
        return None
    saved_as = getattr(result, "saved_as", None)
    return {
        "mode": getattr(result, "mode", "") or None,
        "found": getattr(result, "found", None),
        "reason": getattr(result, "reason", "") or None,
        "embedded_count": getattr(result, "embedded_count", None),
        "saved_as": str(saved_as) if saved_as else None,
        "release_id": getattr(result, "release_id", "") or None,
        "bytes": getattr(result, "bytes", None),
        "format": getattr(result, "format", "") or None,
        "error": getattr(result, "error", "") or None,
        "additional_saved": list(getattr(result, "additional_saved", []) or []) or None,
    }


def _tagging(result: object | None) -> dict | None:
    """Serialize the post-rip tagging outcome for the ``issues`` derivation.

    Unlike its siblings this does NOT become a report block: a tagging failure is
    recorded as an ``issues`` entry (``tagging_failed``), because that list is the
    report's declared home for "what went wrong" and it can grow a new code
    without changing any key set a consumer pins. This helper exists so the issue
    text is derived from ONE duck-typed read of the result (the house pattern),
    not from getattr calls scattered through :func:`_issues`.

    Duck-typed via ``getattr`` like every serializer here, so a partial object
    never raises. None when tagging didn't run (an identified disc is tagged by
    the ripper itself, so this is the common case). Never raises.
    """
    if result is None or not getattr(result, "ran", False):
        return None
    failures = [str(name) for name in (getattr(result, "failures", ()) or ())]
    error = getattr(result, "error", "") or None
    return {
        "ran": True,
        "ok": (not failures) and (error is None),
        "attempted": getattr(result, "attempted", 0),
        "tagged": getattr(result, "tagged", 0),
        "failures": failures,
        "error": error,
    }


def _log_parse(rip_log: object, override: dict | None) -> dict:
    """The ``log_parse`` block: did the human ``.log`` parse into real content?

    The GUI can pass an explicit ``{ok, note}`` (e.g. it caught a decode that
    needed ``errors="replace"``); otherwise we infer ``ok`` from whether the
    parse produced any tracks or a creator line. A False here explains a thin
    report without implying the *rip* failed. Pure; never raises."""
    if isinstance(override, dict):
        return override
    tracks = getattr(rip_log, "tracks", ()) or ()
    ok = bool(tracks) or bool(getattr(rip_log, "log_creator", ""))
    # A truncated log parses "fine" — that was the whole problem. cyanrip's
    # logfile is block-buffered, so killing it loses the tail of a 4 KiB block;
    # on the rig a track that had completed and matched AccurateRip at
    # confidence 200 was simply absent, and nothing said so. `ok` stays True
    # (the parse really did succeed on what was there); the note is what stops a
    # reader treating the shortfall as fact.
    if getattr(rip_log, "log_truncated", False):
        return {
            "ok": ok,
            "note": (
                "the ripper's log was cut off mid-write (it was killed before "
                "flushing), so tracks it does not mention may still have been "
                "ripped and verified — this report's track list is a floor, not "
                "a complete account"
            ),
        }
    return {"ok": ok, "note": None}


def _issues(
    *,
    outcome: dict | None,
    verdict_level: str,
    ctdb: dict | None,
    flac_integrity: dict | None,
    derived: dict | None,
    transcode: dict | None,
    cover_art: dict | None,
    read_speed: dict | None,
    tagging: dict | None = None,
    heavy_reread_tracks: list[int] | None = None,
    log_truncated: bool = False,
    # ADDED after an audit found each of these could be true while `issues` stayed
    # empty — i.e. the one list a triager opens first said "nothing to flag" about a
    # rip that had demonstrably gone wrong. Each is a separate `if` below.
    recompress: dict | None = None,
    log_parse: dict | None = None,
    completeness: dict | None = None,
    rip: dict | None = None,
    # The disc as WE resolved it, so the ripper's echoed release id can be compared
    # against the one we sent. Two blocks, one question, and the comparison is the
    # only thing that makes either number more than a record.
    disc: dict | None = None,
    # The real type, not a widened one: this is the SAME block the report
    # serializes, and typing it `dict` here would let a future rename of an
    # artifact key pass the checker while silently matching nothing.
    artifacts: ArtifactsBlock | None = None,
    dependencies: dict | None = None,
    # The already-serialized v18 block, so this list and the block it summarises
    # read the same verdict.
    ripper_log_verification: dict | None = None,
) -> list[dict]:
    """Derive the consolidated ``issues`` list from the already-assembled blocks.

    One severity-tagged list a triager opens first, instead of cross-reading five
    sub-blocks. Reads the SERIALIZED dicts (not the raw results) so it can never
    disagree with what the report shows. Pure; never raises.

    Empty means "nothing to flag" — which is **not** the same as "verified". A
    rip nothing could be checked against (no AccurateRip match at all) now says
    so explicitly at ``info`` severity, because an empty list read as a clean
    bill of health for a rip that had never been corroborated.
    """
    issues: list[dict] = []

    def add(severity: str, code: str, message: str) -> None:
        issues.append({"severity": severity, "code": code, "message": message})

    status = (outcome or {}).get("status")
    if status == "failed":
        add(
            "error",
            "rip_failed",
            (outcome or {}).get("failure_hint")
            or "the rip did not complete successfully",
        )
    elif status == "cancelled":
        add("warning", "rip_cancelled", "the rip was cancelled before it finished")

    # Ranked as an ERROR, above the cancel it usually accompanies, because it
    # invalidates the other entries rather than adding to them: a truncated log
    # makes "N tracks were never ripped" unfalsifiable, and the rig's own case
    # had a track that WAS ripped and verified reported as never ripped.
    if log_truncated:
        add(
            "error",
            "ripper_log_truncated",
            "the ripper's log was cut off mid-write, so this report's track "
            "list is a floor — tracks it omits may have been ripped and "
            "verified",
        )

    # The RIPPER's own verdict on its own log (v18). Ranked ERROR alongside the
    # truncation check and for the same reason: it does not add to the other
    # entries, it undermines them. Every archival claim in this report is read out
    # of that log, so a log the ripper rejects makes the rest unfalsifiable.
    #
    # This is the entry the fork asked for in round 7 lap 10 J3 — *"it would have
    # caught this on the first rip"* — and it is the check our own `log_integrity`
    # could not be, because that one verifies a file we wrote against a checksum we
    # computed. Only `failed` fires: `not_determined` and a `null` block are
    # non-passes, not faults, and raising an issue for them would train a reader to
    # ignore the entry on every stock-cyanrip rip.
    # A DRIVE THAT STALLED. The fork's watchdog is the only thing that can tell us a
    # read took minutes rather than milliseconds, and a rip that needed that is one the
    # user should know about even when every checksum came out right — a stalling drive
    # is how a disc goes from readable to unreadable.
    #
    # Only a POSITIVE count fires. `0` is a clean measurement and `null` is no
    # measurement; raising an entry for either would put a line in every stock rip's
    # report and train a reader to skip the entry.
    stall_count = (rip or {}).get("read_stalls_count")
    if isinstance(stall_count, int) and stall_count > 0:
        add(
            "warning",
            "ripper_read_stalls",
            f"{stall_count} read(s) took long enough for the ripper's watchdog to "
            f"report a stall: {(rip or {}).get('read_stalls') or 'no detail'}. The "
            "audio may still be bit-perfect, but a drive or disc that stalls is worth "
            "knowing about before the next rip.",
        )

    # DID THE RIPPER USE THE RELEASE WE SENT IT? Tags, filenames and the .cue are all
    # written from the metadata WE resolved, but the ripper writes them from what it
    # parsed out of a single colon-delimited `-a` blob. A value that split wrong lands
    # in the wrong field silently, and the album title on the reference disc carries a
    # U+2236 lookalike precisely because a real colon breaks that syntax.
    #
    # Tri-state, and each state is a different claim:
    #   * ripper echoed nothing -> no claim (an unknown-disc rip sends no release id,
    #     and neither does a whipper log or a build older than this row). NOT a finding.
    #   * we sent nothing, ripper reports one -> it ran its OWN lookup, so `-N` did not
    #     take. That is Critical rule #5, checked at the artifact rather than trusted.
    #   * both present and different -> the tags on disk may describe another release.
    theirs = (rip or {}).get("ripper_release_id")
    ours = (disc or {}).get("musicbrainz_release_id")
    if theirs and not ours:
        add(
            "warning",
            "ripper_release_id_unexpected",
            f"the ripper reported release id {theirs} although this rip sent it none "
            "— it appears to have run its own MusicBrainz lookup, which -N is supposed "
            "to prevent.",
        )
    elif theirs and ours and theirs != ours:
        add(
            "error",
            "ripper_release_id_mismatch",
            f"the ripper used release id {theirs} but this rip resolved {ours} — the "
            "tags, filenames and cue sheet on disk may describe a different release "
            "than the one shown here. Check the -a argument in outcome.ripper_argv.",
        )

    verify_verdict = (ripper_log_verification or {}).get("verdict")
    if verify_verdict == "failed":
        add(
            "error",
            "ripper_log_verification_failed",
            (ripper_log_verification or {}).get("detail")
            or (
                "the ripper rejected its own log's checksum, so this report's "
                "archival claims cannot be traced to a faithful record of the rip"
            ),
        )

    if verdict_level == "warn":
        add(
            "warning",
            "not_bit_perfect",
            "not every track verified exactly against AccurateRip — "
            "see verdict and the per-track table",
        )
    elif verdict_level == "neutral":
        # "neutral" means NOTHING matched AccurateRip — a CD-R, an obscure
        # pressing, an unreachable database, or a wrong read offset. The rip may
        # be perfect, but it is not independently verified, and an empty issues
        # list beside a docstring reading "empty on a clean rip" told a triager
        # the opposite (audit finding, 2026-07-28). Informational, not a warning:
        # we are recording an absence of evidence, not evidence of a fault.
        add(
            "info",
            "unverified",
            "no track matched AccurateRip — this rip is not independently "
            "verified (an unsubmitted pressing, an unreachable database, or a "
            "wrong read offset all look like this)",
        )

    # CTDB is the whole-disc cross-check. Every other verification sub-block
    # contributes an issue; this one was passed in and then never read, so a
    # validated no-match — which CTDB's own wording calls "this rip differs from
    # the database" — reached the report and left `issues` empty.
    if ctdb:
        ctdb_verdict = ctdb.get("verdict")
        if ctdb_verdict == "no_match" and ctdb.get("crc_validated"):
            add(
                "warning",
                "ctdb_no_match",
                "the whole-disc CTDB checksum matched no database entry at the "
                "standard alignment — AccurateRip is the per-track authority, "
                "and an offset-shifted pressing looks like this too",
            )
        elif ctdb_verdict == "error":
            add(
                "info",
                "ctdb_unavailable",
                ctdb.get("message") or "the CTDB check could not be completed",
            )

    if read_speed and read_speed.get("unresolved"):
        unstable = read_speed.get("unstable_tracks") or []
        tail = f" (track(s) {', '.join(str(t) for t in unstable)})" if unstable else ""
        add(
            "warning",
            "read_unstable",
            f"read instability remained after the automatic re-rip{tail}",
        )

    # Read-effort early warning: tracks that needed unusually heavy re-reading
    # (or a -Z secure re-read that never converged) even if they ultimately
    # matched AccurateRip. The earliest in-rip hint that a track's audio may not
    # be reproducible — worth a look before trusting it as an archival master.
    # Distinct from `read_unstable` above (which is the ladder's post-auto-fix
    # verdict); this reads straight from the per-track log signals so it fires
    # even when the ladder never ran.
    if heavy_reread_tracks:
        listed = ", ".join(str(t) for t in heavy_reread_tracks)
        add(
            "warning",
            "heavy_reread",
            f"track(s) {listed} needed unusually heavy re-reading — a sign the "
            "read may not be reproducible; consider re-ripping to confirm",
        )

    if flac_integrity and flac_integrity.get("ran") and not flac_integrity.get("ok"):
        add(
            "error",
            "flac_integrity_failed",
            "one or more FLAC masters failed the decode/MD5 integrity test",
        )

    if derived:
        if derived.get("mismatches"):
            add(
                "error",
                "derived_mismatch",
                "a lossless derived file is NOT bit-identical to the FLAC master",
            )
        elif derived.get("failures"):
            add(
                "warning",
                "derived_verify_failed",
                "a derived file could not be decoded/verified",
            )

    if transcode and (transcode.get("error") or transcode.get("failures")):
        add(
            "warning",
            "transcode_failed",
            "one or more derived files could not be produced "
            "(the FLAC master was kept)",
        )

    if cover_art and cover_art.get("mode") and cover_art.get("found") is False:
        add(
            "warning",
            "cover_art_missing",
            cover_art.get("reason")
            or "the front cover could not be fetched or embedded",
        )

    # Tagging. `apply_track_tags` logged each per-file failure and returned the
    # successes, and its caller discarded them — so an album that shipped with no
    # tags at all produced a report that mentioned tagging nowhere and a window
    # that said "Done." The audio is untouched either way, hence `warning` and the
    # explicit "the audio is unaffected": this is a metadata problem, not a rip
    # problem, and conflating the two is how a triager wastes an hour.
    if tagging and tagging.get("ran") and not tagging.get("ok"):
        whole_pass_error = tagging.get("error")
        if whole_pass_error:
            detail = f"the tagging pass failed outright ({whole_pass_error})"
        else:
            failed = tagging.get("failures") or []
            attempted = tagging.get("attempted") or 0
            detail = (
                f"tags could not be written to {len(failed)} of {attempted} "
                f"file(s): {', '.join(str(name) for name in failed[:10])}"
                + (", …" if len(failed) > 10 else "")
            )
        add(
            "warning",
            "tagging_failed",
            f"{detail} — the audio is unaffected; the files can be tagged with Picard",
        )

    # --- Gaps closed after the 2026-08-04 error-reporting audit ---------------
    #
    # Every block below could be a plain statement of failure in the report while
    # `issues` stayed EMPTY. An empty issues list is read as "nothing to flag", so
    # each of these was a silent failure with its evidence sitting two blocks away.

    # RE-COMPRESS was not even a parameter of this function. It is the one step that
    # MUTATES the archival masters, so a failure here is the most consequential kind
    # there is — and it produced no issue at all.
    if recompress and recompress.get("ran") and not recompress.get("ok"):
        whole = recompress.get("error")
        failed = recompress.get("failures") or []
        detail = (
            f"the re-compress pass failed outright ({whole})"
            if whole
            else f"{len(failed)} file(s) failed to re-encode: "
            + ", ".join(str(f) for f in failed[:10])
            + (", …" if len(failed) > 10 else "")
        )
        add(
            "error",
            "recompress_failed",
            f"{detail} — this step re-encodes the archival masters in place, so "
            f"verify those files before trusting them",
        )

    # A VERIFICATION STEP THAT COULD NOT RUN was silent: `ran: false` skipped every
    # check above, while `verification.gates` still said "ran" (the gate is derived
    # from config, not from the result). "We did not check" is not "it passed".
    for label, block in (
        ("FLAC integrity", flac_integrity),
        ("derived-format verification", derived),
        ("re-compress", recompress),
    ):
        if block is not None and not block.get("ran") and block.get("error"):
            add(
                "warning",
                "verification_step_did_not_run",
                f"{label} was requested but could not run ({block['error']}) — "
                f"this rip carries no {label} result either way",
            )

    # DERIVED INCOMPLETE with no per-file failure: fewer derived files than masters
    # slipped past the mismatch/failure checks entirely.
    if derived and derived.get("ran") and derived.get("complete") is False:
        checked = derived.get("checked")
        expected = derived.get("expected")
        if not (derived.get("mismatches") or derived.get("failures")):
            add(
                "warning",
                "derived_incomplete",
                f"only {checked} of {expected} derived file(s) were verified — the "
                f"rest were neither confirmed nor reported as failures",
            )

    # THE RIPPER'S LOG DID NOT PARSE. Every track fact in this report comes from
    # that log, so a parse failure undermines the whole document — and said nothing.
    if log_parse is not None and log_parse.get("ok") is False:
        note = log_parse.get("note") or "no reason recorded"
        add(
            "warning",
            "ripper_log_unparsed",
            f"the ripper's log could not be parsed ({note}) — track-level facts in "
            f"this report may be incomplete",
        )

    # FEWER (OR MORE) TRACKS THAN ASKED FOR. Only ever appeared as prose inside
    # `verdict.message`, which nothing aggregates.
    if completeness is not None and completeness.get("complete") is False:
        got = completeness.get("tracks_in_report")
        want = completeness.get("tracks_expected")
        add(
            "warning",
            "track_count_mismatch",
            f"this report describes {got} track(s) but the rip was asked for "
            f"{want} — it is not a complete account of the request",
        )

    if rip:
        # AN UNAPPROVED RIPPER BUILD. The entire v15 handshake block was read by
        # nothing: a rip produced by a binary no closed round verified looked
        # identical, in `issues`, to one produced by the approved build.
        approval = rip.get("ripper_handshake_approval")
        if approval and approval != "approved":
            detail = rip.get("ripper_handshake_approval_detail") or ""
            severity = "warning" if approval == "unapproved" else "info"
            add(
                severity,
                f"ripper_handshake_{approval}",
                f"the ripper that produced this rip is {approval}: {detail}".strip(),
            )

        # THE TWO WITNESSES, COMPARED. `ripper_handshake_approval` is OUR verdict on
        # the build tag; `ripper_handshake_note` is what the fork's build system
        # compiled into the binary about the round it came from. Neither is derived
        # from the other, which is the only reason the comparison means anything.
        #
        # Our own round-7 lap-10 file told the fork *"when the two disagree, the
        # disagreement is the finding"* — and nothing compared them. That is
        # capture-without-surfacing one layer up: we parsed the note at v17, stored
        # it, published the claim, and did nothing with it. Exactly the defect the
        # approval block itself had until the fork found it was read by nothing.
        #
        # ERROR when we approved a build that says it is not a release: one of the
        # two must be wrong, and both possibilities are serious (a wrong pin, or a
        # build tag naming a tree that is not what was built — rule 12).
        conflict = cross_check_note(
            str(approval or ""), rip.get("ripper_handshake_note")
        )
        if conflict:
            add(
                "error" if approval == "approved" else "info",
                "ripper_provenance_witnesses_disagree"
                if approval == "approved"
                else "ripper_provenance_self_reported_only",
                conflict,
            )

    # A NON-ZERO EXIT ON A "SUCCESS". These two facts disagree, and only one of
    # them was flagged. Tri-state: `None` (never reaped) is its own case.
    if outcome and outcome.get("status") == "success":
        code = outcome.get("ripper_exit_code")
        if code is None:
            add(
                "warning",
                "ripper_exit_unknown",
                "the rip is recorded as successful but the ripper's exit status was "
                "never collected — the child was not reaped, so 'success' here rests "
                "on the log alone",
            )
        elif code != 0:
            add(
                "warning",
                "ripper_nonzero_exit_on_success",
                f"the rip is recorded as successful but the ripper exited {code} — "
                f"those two facts disagree and the exit code is the harder evidence",
            )

    # AN ARTIFACT WE COULD NOT EMBED. The report's own attachments failing is
    # exactly the case where a reader most needs to be told.
    for name, entry in (artifacts or {}).items():
        if isinstance(entry, dict) and entry.get("error"):
            add(
                "warning",
                "artifact_unavailable",
                f"the {name} artifact could not be embedded in this report "
                f"({entry['error']}) — it may still exist on disk",
            )

    # A DEPENDENCY BELOW ITS MINIMUM. `min_version_met: false` was the only
    # per-tool failure signal in the whole report and nothing surfaced it.
    for tool, info in (dependencies or {}).items():
        if not isinstance(info, dict):
            continue
        if info.get("present") and info.get("min_version_met") is False:
            add(
                "warning",
                "dependency_below_minimum",
                f"{tool} {info.get('version') or '(unknown version)'} is older than "
                f"this Platterpus requires — its results in this rip are suspect",
            )

    return issues


def report_to_json(report: dict) -> str:
    """Serialize a report dict to pretty UTF-8 JSON (trailing newline).

    ``default=str`` is a belt for the never-raises contract: any stray
    non-JSON-native value (a Path/enum a future field might carry) degrades to
    its string form instead of raising ``TypeError`` mid-rip.
    """
    return (
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False, default=str)
        + "\n"
    )


def report_path_for(log_file: Path) -> Path:
    """The JSON report path that sits beside a rip log (`X.log` → `X.platterpus.json`)."""
    return log_file.parent / f"{log_file.stem}.platterpus.json"


# NOTE: there is deliberately NO separate ``.platterpus.log`` sidecar. The
# session log for a rip is EMBEDDED in the JSON report under ``debug.lines``
# (see build_debug_log), making the ``.platterpus.json`` the single, complete,
# self-contained per-album debug artifact (maintainer's call, 2026-07-01). Humans
# read cyanrip's own ``.log``/``.cue``; the global ``~/.local/share/platterpus/
# log.txt`` remains the cross-session catch-all for program-level failures.


def write_report(
    rip_log: object,
    log_file: Path,
    *,
    ctdb_result: object | None = None,
    flac_verify_result: object | None = None,
    transcode_result: object | None = None,
    derived_verify_result: object | None = None,
    recompress_result: object | None = None,
    cover_art_result: object | None = None,
    tagging_result: object | None = None,
    read_speed: dict | None = None,
    secure_rerip: dict | None = None,
    eta_trace: list | None = None,
    checksums: dict | None = None,
    generated_at: str = "",
    timing: dict | None = None,
    debug_log: dict | None = None,
    outcome: dict | None = None,
    settings: dict | None = None,
    disc: dict | None = None,
    environment: EnvironmentBlock | None = None,
    gates: dict | None = None,
    log_parse: dict | None = None,
    disc_track_total: int | None = None,
    artifacts: ArtifactsBlock | None = None,
    #: v18: the RIPPER's verdict on its own log, from `adapters.ripper_log_verify`
    #: — an independent witness, unlike our own SHA-256 footer check. Typed
    #: `object` because this pure builder must not import an adapter.
    ripper_log_verification: object | None = None,
) -> Path | None:
    """Build and write the JSON report beside ``log_file``. Best-effort.

    Returns the path written, or None on any failure (the report is a nice-to-
    have; it must never break the post-rip flow). Writing a small JSON file is
    cheap, so this is safe to call on the GUI thread. (Computing ``checksums``
    is NOT — that's done off-thread by the caller and passed in here.)
    """
    target = report_path_for(log_file)
    try:
        report = build_report(
            rip_log,
            ctdb_result=ctdb_result,
            flac_verify_result=flac_verify_result,
            transcode_result=transcode_result,
            derived_verify_result=derived_verify_result,
            recompress_result=recompress_result,
            cover_art_result=cover_art_result,
            tagging_result=tagging_result,
            read_speed=read_speed,
            secure_rerip=secure_rerip,
            eta_trace=eta_trace,
            checksums=checksums,
            generated_at=generated_at,
            timing=timing,
            debug_log=debug_log,
            outcome=outcome,
            settings=settings,
            disc=disc,
            environment=environment,
            gates=gates,
            log_parse=log_parse,
            disc_track_total=disc_track_total,
            artifacts=artifacts,
            ripper_log_verification=ripper_log_verification,
        )
        # Run the audit over the report we just built and embed the result, so
        # EVERY rip carries its own verdict and nobody has to remember to run
        # anything. `--audit-rips` runs the same registry over a whole library
        # later; both go through `rip_audit.CHECKS`, so the per-rip block and
        # the bulk report cannot word the same finding two different ways.
        #
        # Done HERE rather than in `build_report` because one of the checks
        # stats the audio files, and `build_report` is pure by contract. This
        # function already writes to disk, so the folder is legitimately in
        # scope — and it is `target.parent`, the album folder.
        #
        # Best-effort like the rest of the report: a broken self-check must
        # never cost the user their report.
        try:
            from platterpus import rip_audit

            report["self_check"] = rip_audit.self_check_block(report, target.parent)
            # RE-ORDER AFTER THE LATE ASSIGNMENT. `self_check` is set here, after
            # `_build` returned, so plain insertion appends it — which is precisely
            # how the block that says whether the report is TRUSTWORTHY ended up at
            # byte 1,515,002 of a 1,516,421-byte file, behind 1.23 MB of `debug`.
            # Re-running the ordering puts it back at the front where a partial read
            # finds it.
            report = _ordered_for_reading(report)
        except Exception:  # noqa: BLE001 — diagnostics must not break the artifact
            log.exception("self-check failed; report written without it")
        # Catch serialization errors (TypeError/ValueError from json.dumps on an
        # exotic future value) as well as write errors (OSError) — the report is
        # best-effort and must never break the post-rip flow. report_to_json
        # also uses default=str as a second line of defence. The write is atomic
        # (temp + os.replace) so a crash mid-write can't leave a torn JSON — it's
        # re-written repeatedly as post-rip checks finish, so that window matters.
        _atomic_write_text(target, report_to_json(report))
        return target
    except (OSError, TypeError, ValueError):
        # A vanished album folder is benign and expected — the rip was
        # cancelled/cleaned and its directory removed before this best-effort
        # (and debounced/incremental) write ran. Real-hardware log: a cancelled
        # rip's folder was gone 8 minutes later, and this logged a full
        # FileNotFoundError traceback at WARNING, which reads like a crash. Note
        # that case concisely without a traceback; keep the full diagnostics for
        # any genuine write failure (a real permissions/disk error).
        if not target.parent.exists():
            log.info(
                "skipped rip report; album folder no longer exists: %s",
                target.parent,
            )
        else:
            log.warning("could not write rip report to %s", target, exc_info=True)
        return None
