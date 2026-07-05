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
import os
from pathlib import Path

from platterpus import __version__, build_info
from platterpus.parsers.rip_log import track_accuraterip_verified
from platterpus.verdict import accuraterip_verdict

log = logging.getLogger(__name__)


def _atomic_write_text(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` atomically (temp sibling + ``os.replace``).

    Crash-safety (it.12): a SIGKILL or power loss part-way through a plain
    ``write_text`` would leave a truncated ``.platterpus.json`` — and the report
    is re-written repeatedly as post-rip checks finish, widening that window.
    ``os.replace`` is atomic on POSIX, so a reader ever sees either
    the old complete file or the new complete file, never a torn one (the same
    guarantee ``config.save`` already gives). Raises ``OSError`` on failure; the
    callers below keep the best-effort/never-raise contract by catching it.
    """
    tmp = target.with_name(target.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        # Don't leave a stray temp behind on a failed write.
        try:
            tmp.unlink()
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
REPORT_SCHEMA_VERSION: int = 8

# Cap on how many session-log lines the report embeds. The JSON is now the SINGLE
# per-album debug artifact (no `.platterpus.log` sidecar), so it should hold
# *everything* for this album's rip — verbose enough to debug from alone. A
# single album's log is a few hundred lines at INFO, low thousands at DEBUG, so
# 10k comfortably captures a whole verbose rip while still bounding a pathological
# case (the write is atomic + debounced, off the critical path). Lines are scoped
# to THIS rip already; if the in-memory buffer's own bound ever truncated older
# lines, `truncated` is set and the full history is still in log.txt.
_MAX_EMBEDDED_LOG_LINES: int = 10000


def build_report(
    rip_log: object,
    *,
    ctdb_result: object | None = None,
    flac_verify_result: object | None = None,
    transcode_result: object | None = None,
    derived_verify_result: object | None = None,
    recompress_result: object | None = None,
    cover_art_result: object | None = None,
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
    environment: dict | None = None,
    gates: dict | None = None,
    log_parse: dict | None = None,
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
            secure_rerip=secure_rerip,
            outcome=outcome,
            settings=settings,
            disc=disc,
            environment=environment,
            gates=gates,
            log_parse=log_parse,
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
        embedded = embedded[-_MAX_EMBEDDED_LOG_LINES:]
    return {
        "scope": "this session since launch, excluding other albums' rips",
        # True if EITHER the in-memory buffer dropped lines OR we capped here;
        # in both cases log.txt has the complete record.
        "truncated": bool(truncated) or capped,
        "lines": embedded,
    }


def build_outcome(
    *,
    status: str,
    failure_hint: str | None = None,
    auto_unknown_retry_fired: bool = False,
    auto_unknown_retry_reason: str | None = None,
) -> dict:
    """Build the ``outcome`` block: the PROCESS result of the rip.

    This is the single most-requested support datum and was previously absent —
    ``verdict``/``health_status`` describe AccurateRip / the rip log, not whether
    the *run* succeeded. ``status`` is one of ``"success"`` / ``"cancelled"`` /
    ``"failed"``; ``failure_hint`` is an actionable one-liner when we have one;
    ``auto_unknown_retry`` records whether the self-heal (re-rip as unknown when
    the ripper couldn't reach MusicBrainz) fired. Pure; never raises.
    """
    return {
        "status": status,
        "failure_hint": failure_hint or None,
        "auto_unknown_retry": {
            "fired": bool(auto_unknown_retry_fired),
            "reason": auto_unknown_retry_reason or None,
        },
    }


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
        "rip_goal": getattr(config, "rip_goal", None),
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
            "a jump; 'at' is the PC wall-clock time. Compare against 'timing'."
        ),
        "samples": samples,
    }


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
    secure_rerip: dict | None = None,
    outcome: dict | None = None,
    settings: dict | None = None,
    disc: dict | None = None,
    environment: dict | None = None,
    gates: dict | None = None,
    log_parse: dict | None = None,
) -> dict:
    message, level = accuraterip_verdict(rip_log)
    info = getattr(rip_log, "ripping_info", None)
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
    read_speed_block = dict(read_speed) if read_speed else None
    if secure_rerip is not None:
        read_speed_block = read_speed_block or {}
        read_speed_block["secure_rerip"] = secure_rerip
    # The environment defaults to a live probe (Python/OS/PySide6/channel) when
    # the caller didn't supply one — so a report always carries it — but a test
    # can inject a fixed dict for determinism.
    if environment is None:
        environment = build_info.environment_report()
    issues = _issues(
        outcome=outcome,
        verdict_level=level,
        ctdb=ctdb,
        flac_integrity=flac_integrity,
        derived=derived,
        transcode=transcode,
        cover_art=cover_art,
        read_speed=read_speed_block,
    )
    return {
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
        "rip": {
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
            "creation_date": getattr(rip_log, "creation_date", "") or None,
        },
        "accuraterip_summary": getattr(rip_log, "accuraterip_summary", "") or None,
        "partially_accurate_summary": (
            getattr(rip_log, "partially_accurate_summary", "") or None
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
        "log_parse": _log_parse(rip_log, log_parse),
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
        # report a self-contained debug record (None when not captured).
        "debug": debug_log,
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
        # Per-track extraction diagnostics cyanrip logs (all None on whipper):
        # the drive speed this track read at (×), the extraction quality (%),
        # whether pre-emphasis was flagged, and the sample peak level. Surfaced
        # so a marginal track's read conditions are visible in the report.
        "extraction_speed": getattr(track, "extraction_speed", None),
        "extraction_quality": getattr(track, "extraction_quality", None),
        "pre_emphasis": getattr(track, "pre_emphasis", None),
        "peak_level": getattr(track, "peak_level", None),
        # ReplayGain / loudness tags cyanrip wrote into the FLAC (raw strings) —
        # the machine-readable record of what was tagged. None when absent.
        "replaygain": (dict(getattr(track, "replaygain", {})) or None),
        # The shared confidence>=1 rule — same as the banner and disc panel.
        "accuraterip_verified": track_accuraterip_verified(track),
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
    return {
        "ran": True,
        "ok": (not failures) and (error is None),
        "reencoded": getattr(result, "reencoded", 0),
        "failures": [str(p) for p in failures],
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
) -> list[dict]:
    """Derive the consolidated ``issues`` list from the already-assembled blocks.

    One severity-tagged list a triager opens first, instead of cross-reading five
    sub-blocks. Reads the SERIALIZED dicts (not the raw results) so it can never
    disagree with what the report shows. Empty on a clean rip. Pure; never raises.
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

    if verdict_level == "warn":
        add(
            "warning",
            "not_bit_perfect",
            "not every track verified exactly against AccurateRip — "
            "see verdict and the per-track table",
        )

    if read_speed and read_speed.get("unresolved"):
        unstable = read_speed.get("unstable_tracks") or []
        tail = f" (track(s) {', '.join(str(t) for t in unstable)})" if unstable else ""
        add(
            "warning",
            "read_unstable",
            f"read instability remained after the automatic re-rip{tail}",
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
    environment: dict | None = None,
    gates: dict | None = None,
    log_parse: dict | None = None,
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
        )
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
