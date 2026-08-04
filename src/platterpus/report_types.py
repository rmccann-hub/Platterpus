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
    c2_pointers: bool | None
    paranoia_level: str | None
    overread_mode: str | None
    ripper_build: str | None
    creation_date: str | None
    musicbrainz_disc_id: str | None
    cddb_id: str | None
    # v14: the ripper's own completion footer, tri-state. `rip_completed` is
    # `None` when the log was cut off or predates the fork pin — which is a
    # different fact from `False`, and must not render as one.
    rip_completed: bool | None
    rip_completed_tracks: int | None
    rip_completed_total: int | None
    rip_completed_reason: str | None
    # v14: the ripper's own `Invoked as:` line — what it says it RECEIVED, as
    # against `outcome.ripper_argv`, which is what we SENT.
    invoked_as: str | None
    #: v17, both FORK-ONLY and both verbatim. `ripper_handshake_note` is the
    #: binary's own compiled-in statement of the round it was built from — a
    #: second, independent witness beside `ripper_handshake_approval`, which is
    #: *our* verdict on the banner. `ripper_consumer` is who it was told the
    #: caller was, which its own log says is unverified.
    ripper_handshake_note: str | None
    ripper_consumer: str | None
    # v13: which cyanrip binary produced this. Tri-state: `null` is "not
    # determined" and must never be read as `false`, because an unrecognised
    # build tag is absence of evidence, not evidence of a stock binary.
    ripper_is_platterpus_fork: bool | None
    ripper_identity: str | None
    ripper_identity_detail: str | None
    # v15: whether that binary is the build BOTH projects affirmatively verified
    # — a different question from `ripper_identity`, checked at rip time rather
    # than only by CI. `"not_determined"` is not a pass.
    ripper_handshake_approval: str | None
    ripper_handshake_approval_detail: str | None
    ripper_handshake_approved_build: str | None
    ripper_handshake_approved_for_platterpus: str | None
    ripper_handshake_approved_by_round: int | None


class TimingBlock(TypedDict):
    elapsed_seconds: int | None
    elapsed_human: str | None
    started_at: str | None
    finished_at: str | None
    # Only present when BOTH elapsed and a positive disc duration are known.
    disc_seconds: NotRequired[int]
    realtime_multiplier: NotRequired[float]
    #: WHICH duration the multiplier is measured against — "audio actually
    #: extracted" for a partial/cancelled rip, the whole disc otherwise. Written by
    #: `rip_report._enrich_timing` and undeclared here until 2026-08-04, so a
    #: consumer reading this type had no idea the ratio's denominator could change
    #: meaning between two reports. `NotRequired` because it only appears alongside
    #: `realtime_multiplier`.
    realtime_multiplier_basis: NotRequired[str]


class AutoUnknownRetryBlock(TypedDict):
    fired: bool
    reason: str | None


class OutcomeBlock(TypedDict):
    status: str
    failure_hint: str | None
    auto_unknown_retry: AutoUnknownRetryBlock
    # v13: the two facts that make a failure reproducible, and both were being
    # computed and discarded before it. `ripper_exit_code` is tri-state — `None`
    # means the child was never reaped (wedged in a drive ioctl where even
    # SIGKILL does not land) and must never be written as `0`.
    ripper_exit_code: int | None
    ripper_argv: list[str] | None
    # The FIRST invocation's argv when the rip took more than one pass, `None`
    # when it took one. The distinction is load-bearing: the archival log's
    # `Invoked as:` line comes from the first pass, so comparing it against
    # `ripper_argv` (the last) accused clean multi-pass rips of tampering.
    ripper_argv_first_pass: list[str] | None
    #: The argv rendered as a copy-pasteable command line, for a bug report.
    ripper_command_display: str | None


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
    #: WHICH disc of a multi-disc release these tags came from, and how we decided
    #: (`medium_select.py`). Written since v0.6.1 and undeclared here until
    #: 2026-08-04 — which matters more than most drift: a rip whose medium could not
    #: be resolved is still a rip, but its titles may belong to another disc, and
    #: `medium_undetermined` is the only field that says so. A consumer typed against
    #: this block could not see it existed.
    medium_basis: str | None
    medium_detail: str | None
    medium_undetermined: bool


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
    pregap_start_lsn: int | None
    #: The pre-gap's *provenance and state*, not just its number. Tri-state by
    #: design — `pregap_state` distinguishes a measured zero from "we could not
    #: determine it", which is the distinction the whole pre-gap investigation
    #: turned on — and all four shipped undeclared here.
    pregap_length_frames: int | None
    pregap_source: str | None
    pregap_state: str | None
    pregap_unknown_reason: str | None
    replaygain: dict[str, str] | None
    accuraterip_lookup: str | None
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


class DiagnosticItemBlock(TypedDict):
    """One entry in the report's `diagnostics.items` list.

    Mirrors :class:`platterpus.diagnostics.Diagnostic` exactly — one shape, not two.
    The dataclass is the producer and this is its consumed contract; a completeness
    test asserts the field sets match so they cannot drift.
    """

    severity: str
    code: str
    subsystem: str
    message: str
    detail: str | None
    tool: str | None
    argv: list[str] | None
    #: Tri-state: `null` means no child was reaped, which is NOT `0`.
    exit_code: int | None
    at: str | None
    where: str | None
    track: int | None


class DiagnosticsBlock(TypedDict):
    """The report's `diagnostics` block (schema v16) — *"did anything go wrong?"*

    Added on a maintainer directive: *"I want full error and reporting to the output
    log file (JSON) as possible for future debugging… make finding errors easy."*
    Before it, diagnostics were scattered across `outcome.failure_hint`,
    `log_parse.note`, `ctdb.error`, per-track `issues` and the verification blocks —
    each a different shape, none enumerated, so answering the first question a
    support thread asks required knowing where to look.

    The counts and `codes` come FIRST on purpose: a reader who checks only
    `error_count` still learns the thing that matters.
    """

    error_count: int
    warning_count: int
    info_count: int
    #: The most severe severity recorded, or `null` when nothing was.
    worst_severity: str | None
    #: Every distinct code, first-seen order — what *kinds* of thing went wrong.
    codes: list[str]
    #: What period the items cover. The collector is process-wide, so a setup
    #: failure earlier in the same session appears here — useful (it explains an
    #: unapproved ripper) but only if the reader is told, hence this field.
    scope: str
    #: Stated, never implied. A capped list that does not say so reads as complete.
    truncated: bool
    dropped_count: int
    #: The one command that finds every diagnostic in the text log.
    log_grep_hint: str
    items: list[DiagnosticItemBlock]


class RipReport(TypedDict):
    """A complete `.platterpus.json`, schema v17.

    Every key is required: `rip_report._build` returns one fixed dict literal,
    so a successfully-built report always carries all of them (many as None).
    """

    schema_version: int
    generator: GeneratorBlock
    generated_at: str | None
    #: Every problem this rip noticed, in one place (schema v16). Deliberately
    #: near the top of the report: it is the first thing a debugger should read.
    diagnostics: DiagnosticsBlock
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
    #: The verdict's DENOMINATOR as a number (schema v12) and the verbatim text of
    #: the companion files written beside the report. Both shipped four schema
    #: versions before they were declared here, which is the same defect this
    #: module's own docstring calls out: a `TypedDict` that under-describes a dict
    #: literal is not a type error, because the emit site is not annotated as the
    #: `TypedDict`, so there is nothing for mypy to compare.
    completeness: CompletenessBlock
    artifacts: ArtifactsBlock | None
    #: Added by `write_report` after `_build`, so it is absent from an in-memory
    #: report and present in every written one. See :class:`SelfCheckBlock`.
    self_check: NotRequired[SelfCheckBlock]


class MinimalRipReport(TypedDict):
    """The never-raises fallback envelope `build_report` emits if `_build` throws.

    A DIFFERENT shape from `RipReport` — only three keys — so `build_report`
    returns `RipReport | MinimalRipReport` rather than making 26 keys optional.
    """

    schema_version: int
    generator: GeneratorBlock
    error: str


class ArtifactEntry(TypedDict):
    """One companion text file, embedded verbatim in the report (schema v12).

    Always answers the same questions in the same shape so a reader never has
    to distinguish "key missing" from "file missing". ``sha256`` digests the
    BYTES ON DISK, not the possibly-truncated ``text`` — a digest of something
    no file ever contained would be worse than none. ``error`` appears only on
    a failure (unreadable, or a suffix the embedder refuses).
    """

    path: str | None
    exists: bool
    source: NotRequired[str]
    bytes: NotRequired[int]
    sha256: NotRequired[str]
    truncated: NotRequired[bool]
    text: NotRequired[str]
    error: NotRequired[str]


class ArtifactsBlock(TypedDict):
    """The three files written beside the report, so one upload is enough."""

    note: str
    rip_log: ArtifactEntry
    ripper_stdout: ArtifactEntry
    eac_log: ArtifactEntry
    cue: ArtifactEntry


class SelfCheckFindingBlock(TypedDict):
    """One finding from the post-rip self-audit (`rip_audit.CHECKS`)."""

    check: str
    level: str
    message: str


class SelfCheckBlock(TypedDict):
    """The app auditing its own work at the moment the rip finishes.

    **Added by `write_report`, not by `_build`** — one of its checks stats the audio
    files, and `_build` is pure by contract. That is a legitimate split and it is also
    why this block went undeclared: the completeness sweep in
    `tests/test_report_types_completeness.py` built a report through `build_report` and
    compared *that* against :class:`RipReport`, so a key the **writer** adds was
    invisible to it. Found by reading a real rig artifact (2026-08-04), which had 32
    top-level keys where the builder produces 31 — *"am I verifying the behaviour, or
    my stand-in's behaviour?"*, answered by the artifact. The sweep now reads a written
    file.
    """

    schema: int
    checks_run: list[str]
    checks_skipped: list[str]
    worst: str
    findings: list[SelfCheckFindingBlock]


class CompletenessBlock(TypedDict):
    """The verdict's denominator, as a number rather than English prose.

    ``tracks_expected`` is what the rip was ASKED for — the disc's track count,
    or fewer when the user ticked a subset. ``None`` means it was not known to
    the writer; that is explicitly NOT a claim that the rip was whole, which is
    why ``complete`` is tri-state rather than defaulting to True.
    """

    tracks_expected: int | None
    tracks_in_report: int
    complete: bool | None
    note: str
