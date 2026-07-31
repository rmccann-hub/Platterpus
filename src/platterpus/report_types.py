"""The `.platterpus.json` rip-report shape, as TypedDicts.

Single source of truth for the structure `rip_report` WRITES and `rip_compare`
READS. Derived from what the code actually emits (schema v9).
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class GeneratorBlock(TypedDict):
    name: str
    version: str
    build_fingerprint: str


class VerdictBlock(TypedDict):
    level: str
    message: str | None


class RipBlock(TypedDict):
    drive: str | None
    extraction_engine: str | None
    read_offset_correction: int | None
    defeat_audio_cache: bool | None
    overread_lead_out: bool | None
    gap_detection: str | None
    cd_r_detected: bool | None
    speed_changeable: bool | None
    creation_date: str | None
    musicbrainz_disc_id: str | None
    cddb_id: str | None


class TimingBlock(TypedDict):
    elapsed_seconds: int | None
    elapsed_human: str | None
    started_at: str | None
    finished_at: str | None
    # Only present when BOTH elapsed and a positive disc duration are known.
    disc_seconds: NotRequired[int]
    realtime_multiplier: NotRequired[float]


class AutoUnknownRetryBlock(TypedDict):
    fired: bool
    reason: str | None


class OutcomeBlock(TypedDict):
    status: str
    failure_hint: str | None
    auto_unknown_retry: AutoUnknownRetryBlock


class ReadOffsetBlock(TypedDict):
    configured: int | None
    applied: bool
    effective: int | None


class SettingsBlock(TypedDict):
    output_format: str | None
    cover_art: str | None
    read_speed_mode: str | None
    read_speed: int | None
    secure_rerip_dynamic: bool | None
    secure_rerip_matches: int | None
    max_retries: int | None
    ctdb_verify_after_rip: bool | None
    verify_flac_after_rip: bool | None
    recompress_flac_after_rip: bool | None
    rip_goal: str | None
    read_offset: ReadOffsetBlock
    # Written only when output_format == "mp3".
    mp3_vbr_quality: NotRequired[int | None]


class DiscBlock(TypedDict):
    unknown: bool | None
    musicbrainz_release_id: str | None
    catalog_number: str | None
    barcode: str | None
    label: str | None


class DependencyEntry(TypedDict):
    present: bool
    version: str | None
    location: str | None
    min_version_met: bool


class EnvironmentBlock(TypedDict):
    python: str | None
    platform: str | None
    pyside6: str | None
    install_channel: str
    # Filled by the GUI from the launch-time dependency probe; absent when the
    # pure builder produced the block itself (build_info.environment_report) — and
    # NULLABLE because the GUI emits a literal `null` when the probe produced no
    # report. Typing it non-optional would silently change the wire format that
    # `rip_compare` and any external consumer already read.
    dependencies: NotRequired[dict[str, DependencyEntry] | None]


class GatesBlock(TypedDict):
    ctdb: str
    flac_integrity: str
    recompress: str
    derived: str


class FlacIntegrityBlock(TypedDict):
    ran: bool
    ok: bool
    checked: int
    failures: list[str]
    error: str | None


class TranscodeBlock(TypedDict):
    ran: bool
    ok: bool
    transcoded: int
    failures: list[str]
    error: str | None


class DerivedBlock(TypedDict):
    format: str | None
    lossless: bool
    proof: str
    ran: bool
    ok: bool
    complete: bool
    checked: int
    expected: int
    failures: list[str]
    mismatches: list[str]
    error: str | None


class RecompressBlock(TypedDict):
    ran: bool
    ok: bool
    reencoded: int
    failures: list[str]
    error: str | None


class VerificationBlock(TypedDict):
    gates: GatesBlock | None
    flac_integrity: FlacIntegrityBlock | None
    transcode: TranscodeBlock | None
    derived: DerivedBlock | None
    recompress: RecompressBlock | None


class CtdbBlock(TypedDict):
    verdict: str | None
    confidence: int | None
    trustworthy: bool | None
    crc_validated: bool | None
    our_crc: str | None
    matched_crc: str | None
    entry_count: int
    db_crcs: list[str | None]
    message: str | None


class CoverArtBlock(TypedDict):
    mode: str | None
    found: bool | None
    reason: str | None
    embedded_count: int | None
    saved_as: str | None
    release_id: str | None
    bytes: int | None
    format: str | None
    error: str | None
    additional_saved: list[str] | None


class LogParseBlock(TypedDict):
    ok: bool
    note: str | None


class IssueBlock(TypedDict):
    severity: str
    code: str
    message: str


class ArResultBlock(TypedDict):
    result: str | None
    confidence: int | None
    local_crc: str | None
    remote_crc: str | None


class TrackAccurateRipBlock(TypedDict):
    v1: ArResultBlock | None
    v2: ArResultBlock | None
    offset_450: ArResultBlock | None


class TrackBlock(TypedDict):
    number: int | None
    filename: str | None
    test_crc: str | None
    copy_crc: str | None
    status: str | None
    rip_count: int | None
    secure_rerip_converged: bool | None
    extraction_speed: float | None
    extraction_quality: float | None
    pre_emphasis: bool | None
    peak_level: float | None
    extraction_elapsed_seconds: float | None
    appended_silence_frames: int | None
    start_sector: int | None
    end_sector: int | None
    pregap_sectors: int | None
    replaygain: dict[str, str] | None
    accuraterip_verified: bool
    accuraterip: TrackAccurateRipBlock


class SpeedPassBlock(TypedDict):
    attempt: int
    speed: int
    speed_label: str
    secure_rerip_matches: int
    clean: bool


class RetriedTrackBlock(TypedDict):
    track: int
    reripped_z: int
    converged: bool
    replaced: bool


class SecureReripBlock(TypedDict):
    mode: str
    engaged: bool
    disc_in_accuraterip: bool | None
    skipped_reason: str | None
    interrupted: bool


class ReportReadSpeedBlock(TypedDict, total=False):
    """The report's `read_speed` field.

    This is also what `read_speed_ladder.attempts_to_report` returns — ONE shape,
    not two. An earlier draft had a `total=True` ladder block plus this one, but the
    two are the same field at different moments of being filled in, and keeping both
    meant every producer had to pick.

    EVERY key is optional, which is not laziness: `rip_report._build` folds
    `secure_rerip` into this block, so when the ladder never ran but the
    secure-re-rip provenance exists the value is legitimately
    `{"secure_rerip": {...}}` with no ladder keys at all.
    """

    attempts: list[SpeedPassBlock]
    final_speed: int
    final_speed_label: str
    final_secure_rerip_matches: int
    escalated: bool
    unresolved: bool
    unstable_tracks: list[int]
    retried_tracks: list[RetriedTrackBlock]
    secure_rerip: SecureReripBlock


class EtaSampleBlock(TypedDict):
    at: str
    elapsed_seconds: int
    overall_percent: float
    read_speed: int
    our_eta_seconds: int | None
    cyanrip_eta: str | None
    track: int | None
    activity: str | None
    # Backfilled by `_eta_trace_block`; omitted when `at`/finish is unparseable.
    actual_remaining_seconds: NotRequired[int]


class EtaTraceBlock(TypedDict):
    note: str
    samples: list[EtaSampleBlock]


class DebugBlock(TypedDict):
    scope: str
    truncated: bool
    lines: list[str]


class RipReport(TypedDict):
    """A complete `.platterpus.json`, schema v9.

    Every key is required: `rip_report._build` returns one fixed dict literal,
    so a successfully-built report always carries all of them (many as None).
    """

    schema_version: int
    generator: GeneratorBlock
    generated_at: str | None
    outcome: OutcomeBlock | None
    timing: TimingBlock | None
    environment: EnvironmentBlock | None
    settings: SettingsBlock | None
    disc: DiscBlock | None
    log_creator: str | None
    verdict: VerdictBlock
    rip: RipBlock
    accuraterip_summary: str | None
    partially_accurate_summary: str | None
    disc_duration: str | None
    paranoia_counts: dict[str, int] | None
    read_speed: ReportReadSpeedBlock | None
    eta_trace: EtaTraceBlock | None
    album_loudness: dict[str, str] | None
    health_status: str | None
    sha256_hash: str | None
    log_checksum: str | None
    log_parse: LogParseBlock
    tracks: list[TrackBlock]
    ctdb: CtdbBlock | None
    verification: VerificationBlock
    cover_art: CoverArtBlock | None
    issues: list[IssueBlock]
    checksums: dict[str, str] | None
    debug: DebugBlock | None


class MinimalRipReport(TypedDict):
    """The never-raises fallback envelope `build_report` emits if `_build` throws.

    A DIFFERENT shape from `RipReport` — only three keys — so `build_report`
    returns `RipReport | MinimalRipReport` rather than making 26 keys optional.
    """

    schema_version: int
    generator: GeneratorBlock
    error: str
