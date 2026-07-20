"""Per-drive profiles: a stable hardware fingerprint + provenance/confidence.

Why this exists (UX gap #6 / ux-design-principles principle 7)
--------------------------------------------------------------
A read offset that's right for one drive silently corrupts a rip on a
*different* drive. EAC hit exactly this in 2007: two identical-model drives,
one offset, the wrong one applied — a "silent wrong-offset rip". The fix the
research calls for is a per-drive profile keyed by a **stable hardware
identity**, with **provenance and confidence** on each learned fact, so the
user can *see* where an offset came from and how much to trust it, and so the
software can *warn* when state looks stale or ambiguous.

What this module is — and is NOT (the load-bearing boundary, KDD-23)
--------------------------------------------------------------------
This is a **record / display / guard ledger**. It remembers, per stable drive
identity, what offset was learned, from where, with what confidence, and when —
and it surfaces drift/collision warnings. It does **NOT** decide which offset a
rip actually uses: ``whipper.conf`` stays whipper's sole authority, and the
GUI's single global ``--offset`` override (``Config.read_offset`` /
``Config.override_read_offset``) stays the only other authority. Making this
ledger authoritative would mean either hand-authoring whipper.conf (forbidden,
KDD-15) or forcing ``--offset`` from a possibly-stale cache — i.e. re-creating
the very silent-wrong-offset bug the feature exists to prevent. Per-drive
offset *application* is a separate, hardware-gated change (it needs a real
two-drive rig to prove the right offset reaches the right drive).

Everything here is pure and **never raises** (parser-grade, per CLAUDE.md): a
malformed input degrades to a best-effort value, never an exception, so a
corrupt drive identity can never crash the GUI or block a rip. Persistence
lives in the sibling :mod:`platterpus.drive_profile_store`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from platterpus.adapters.accuraterip_offsets import (
    canonical_token,
    normalize_combined,
    normalize_drive_name,
)

log = logging.getLogger(__name__)


# --- Provenance + confidence vocabulary -------------------------------------


class OffsetSource(StrEnum):
    """Where a recorded read offset came from.

    A ``str``-valued Enum so it serializes to a plain JSON string and round-trips
    trivially. ``_missing_`` returns ``UNKNOWN`` for any unrecognized stored
    string, so deserializing a future/garbled value never raises.
    """

    # measured on THIS drive (a single offset-find reading)
    OFFSET_FIND = "offset_find"
    # read live from whipper.conf (whipper measured it)
    WHIPPER_CONF = "whipper_conf"
    # looked up by model in the AccurateRip list — reliable, but not probed here
    ACCURATERIP_LIST = "accuraterip_list"
    # the user typed it (the --offset override path)
    MANUAL = "manual"
    # the value two INDEPENDENT sources agree on — the only path to HIGH
    # confidence (see reconcile_offset). Not a raw source a caller records; it's
    # the *derived* provenance produced when e.g. the AccurateRip-list value and
    # a manual entry (or a real measurement) coincide.
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> OffsetSource:
        return cls.UNKNOWN


class Confidence(StrEnum):
    """How much to trust a recorded fact. ``str``-valued for human-readable JSON.

    Ordered via :data:`_CONFIDENCE_ORDER` (not an ``IntEnum``, so the stored
    values stay legible). ``_missing_`` → ``LOW`` so an unknown stored string is
    treated as least-trusted rather than raising.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def _missing_(cls, value: object) -> Confidence:
        return cls.LOW


# Trust ranking for the upgrade rule (an automatic source must never silently
# clobber a higher-confidence stored record — see drive_profile_store / the
# recorder in the main window).
_CONFIDENCE_ORDER: dict[Confidence, int] = {
    Confidence.LOW: 0,
    Confidence.MEDIUM: 1,
    Confidence.HIGH: 2,
}

# Base confidence for a SINGLE source, standing alone. The maintainer's model:
# HIGH is EARNED only when two *independent* sources agree on the value (see
# :func:`reconcile_offset`) — never granted to a lone reading. So no single
# source is HIGH here:
#   * OFFSET_FIND — one measurement on this unit (unconfirmed) → MEDIUM. (It was
#     wrongly HIGH; a fabricated cyanrip "-f" reading of 0 then outranked and
#     clobbered the correct AccurateRip-list value. cyanrip no longer produces
#     these at all — see cyanrip_backend.find_offset — but the demotion is the
#     durable fix for any future real detector.)
#   * WHIPPER_CONF — a value read from a leftover config, not verified here →
#     MEDIUM (whipper is no longer a backend, KDD-18).
#   * MANUAL — a deliberate but unverified user entry → MEDIUM.
#   * ACCURATERIP_LIST — reliable per *model*, never probed on this *unit* →
#     MEDIUM.
#   * UNKNOWN — least-trusted → LOW.
_SOURCE_CONFIDENCE: dict[OffsetSource, Confidence] = {
    OffsetSource.OFFSET_FIND: Confidence.MEDIUM,
    OffsetSource.WHIPPER_CONF: Confidence.MEDIUM,
    OffsetSource.MANUAL: Confidence.MEDIUM,
    OffsetSource.ACCURATERIP_LIST: Confidence.MEDIUM,
    OffsetSource.CONFIRMED: Confidence.HIGH,
    OffsetSource.UNKNOWN: Confidence.LOW,
}


def confidence_for(source: OffsetSource) -> Confidence:
    """The default confidence for `source` (LOW for anything unexpected)."""
    return _SOURCE_CONFIDENCE.get(source, Confidence.LOW)


def confidence_rank(confidence: Confidence) -> int:
    """Numeric rank for ordering/upgrade comparisons (higher = more trusted)."""
    return _CONFIDENCE_ORDER.get(confidence, 0)


# Friendly, effect-first labels for each provenance source (UI display).
_SOURCE_LABEL: dict[OffsetSource, str] = {
    OffsetSource.OFFSET_FIND: "measured once on this drive",
    OffsetSource.WHIPPER_CONF: "from whipper.conf",
    OffsetSource.ACCURATERIP_LIST: "from the AccurateRip list",
    OffsetSource.MANUAL: "entered by hand",
    OffsetSource.CONFIRMED: "confirmed — two independent sources agree",
    OffsetSource.UNKNOWN: "from an unknown source",
}


def describe_source(source: OffsetSource) -> str:
    """A short human label for `source` (for the provenance display line)."""
    return _SOURCE_LABEL.get(source, "from an unknown source")


# --- The records ------------------------------------------------------------


@dataclass(frozen=True)
class OffsetRecord:
    """One learned read offset and where it came from."""

    value: int  # signed samples
    source: OffsetSource
    confidence: Confidence
    # ISO-8601 UTC; provenance/staleness display only, never a rip input
    detected_at: str = ""


def reconcile_offset(
    existing: OffsetRecord | None, candidate: OffsetRecord
) -> OffsetRecord:
    """Merge a newly-learned offset fact with the stored one — the maintainer's
    **agreement-based confidence** model. Pure; never raises.

    The record's confidence reflects how many *independent* sources corroborate
    its value, never the source type alone:

    - **Nothing stored** → take the candidate at its base (single-source)
      confidence.
    - **Same source** → refresh (value/date may change), but never downgrade a
      value already CONFIRMED by agreement.
    - **Two independent sources AGREE on the value** → promote to a CONFIRMED,
      HIGH-confidence record. This is the *only* way to reach HIGH.
    - **They DISAGREE** → do NOT silently clobber; keep the more-trustworthy
      record and let :func:`evaluate_drive_state` surface the conflict:
        * a deliberate MANUAL entry always wins (user authority);
        * a MANUAL or already-CONFIRMED stored value is never overwritten by an
          automatic source;
        * otherwise keep the strictly-higher-confidence record, and on a tie keep
          the incumbent (so an equal-confidence newcomer — e.g. a bogus reading —
          can't flip-flop or overwrite the AccurateRip-list value).

    This replaced the old confidence-rank-only rule, under which a lone
    HIGH-confidence "measurement" (a fabricated cyanrip 0) clobbered the correct
    AccurateRip-list value and could never be corrected.
    """
    if existing is None:
        return candidate
    if candidate.source == existing.source:
        # A refresh of the same source. Don't let it downgrade an
        # agreement-confirmed value that still matches.
        if existing.confidence is Confidence.HIGH and candidate.value == existing.value:
            return existing
        return candidate
    if candidate.value == existing.value:
        # Independent corroboration → CONFIRMED / HIGH.
        return OffsetRecord(
            value=candidate.value,
            source=OffsetSource.CONFIRMED,
            confidence=Confidence.HIGH,
            detected_at=candidate.detected_at,
        )
    # Disagreement on the value.
    if candidate.source is OffsetSource.MANUAL:
        return candidate  # a deliberate user override always wins
    if existing.source is OffsetSource.MANUAL or existing.confidence is Confidence.HIGH:
        return existing  # never clobber a manual or already-confirmed value
    if confidence_rank(candidate.confidence) > confidence_rank(existing.confidence):
        return candidate
    return existing


@dataclass(frozen=True)
class DriveProfile:
    """Everything we've learned about one physical drive, keyed by fingerprint."""

    fingerprint: str  # the stable key (see compute_fingerprint)
    vendor: str
    model: str
    # firmware revision; for display + swap detection, NOT part of the key
    release: str = ""
    serial: str = ""  # sysfs serial if exposed ("" otherwise)
    wwn: str = ""  # sysfs WWN if exposed ("" otherwise)
    offset: OffsetRecord | None = None
    # learned cache fact; DISPLAY only (whipper.conf stays authoritative)
    cache_defeat: bool | None = None
    cache_defeat_source: OffsetSource | None = None
    # e.g. "/dev/sr0" — advisory display only, NEVER part of the key
    last_seen_device: str = ""
    last_seen_at: str = ""  # ISO-8601 UTC


# --- Stable fingerprint -----------------------------------------------------


def compute_fingerprint(
    vendor: str, model: str, serial: str = "", wwn: str = ""
) -> str:
    """A stable identity key for a drive. Pure, deterministic, never raises.

    Priority (first non-empty tier wins; the tier prefix is part of the string
    so two tiers can never collide, and a drive that *gains* a serial later
    produces a new fingerprint → a fail-safe fresh confirm, never silent reuse
    of a stale offset under a changed identity):

    1. ``wwn:<wwn>`` — a World-Wide Name is globally unique; strongest.
    2. ``sn:<normalized vendor+model>:<serial>`` — serial scoped by model, so a
       short serial reused across different models can't collide.
    3. ``vm:<normalized vendor+model>`` — the common case (whipper's ``drive
       list`` and most optical drives in sysfs expose no serial/WWN). This is
       the *same* key AccurateRip lookup and whipper.conf's ``[drive:...]``
       section use, via the shared canonicalization, so they always agree.

    Firmware (``release``) is deliberately NOT in any tier: a firmware update
    must not orphan a learned profile. Firmware change is surfaced by the swap
    guard (:func:`evaluate_drive_state`) instead.
    """
    wwn_c = canonical_token(wwn)
    if wwn_c:
        return f"wwn:{wwn_c}"
    serial_c = canonical_token(serial)
    if serial_c:
        return f"sn:{normalize_drive_name(vendor, model)}:{serial_c}"
    return f"vm:{normalize_drive_name(vendor, model)}"


def _read_sysfs_attr(path: Path) -> str:
    """Read a one-line sysfs attribute, stripped; "" if unreadable. Never raises."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def read_drive_identity(
    device: str, sys_block: Path = Path("/sys/block")
) -> tuple[str, str]:
    """Return ``(serial, wwn)`` for `device` from sysfs; ``("", "")`` if absent.

    Reads ``/sys/block/<dev>/device/{serial,wwn}``. Optical drives frequently
    expose neither (and whipper reports no serial at all), so empty strings are
    the normal case, not an error. The `sys_block` root is injectable for tests
    — the same seam the cyanrip backend's drive scan uses. Never raises; these
    are sub-millisecond local reads.
    """
    name = Path(device).name  # "/dev/sr0" -> "sr0"
    base = sys_block / name / "device"
    return (_read_sysfs_attr(base / "serial"), _read_sysfs_attr(base / "wwn"))


def find_fingerprint_collisions(fingerprints: list[str]) -> set[str]:
    """Return the set of fingerprints shared by more than one enumerated drive.

    Pure counting over the currently-connected drives' fingerprints. A shared
    ``vm:`` fingerprint is the EAC-2007 identical-drive case (two same-model
    drives with no serial to tell them apart); the guard below treats those as a
    warning. Never raises.
    """
    counts: dict[str, int] = {}
    for fp in fingerprints:
        counts[fp] = counts.get(fp, 0) + 1
    return {fp for fp, n in counts.items() if n > 1}


# --- Mismatch guard ---------------------------------------------------------
#
# Three checks, all WARN/INFO, never BLOCK. Blocking a rip over a record-layer
# heuristic would be worse than the disease — and the offset whipper actually
# uses is unchanged by this module anyway. The point is to make a situation that
# is silent today *visible* so the user can act.

WARNING_COLLISION = "collision"
WARNING_FIRMWARE_CHANGED = "firmware_changed"
WARNING_DISAGREEMENT = "disagreement"
WARNING_LOW_CONFIDENCE = "low_confidence"

SEVERITY_WARN = "warn"
SEVERITY_INFO = "info"


@dataclass(frozen=True)
class DriveWarning:
    """One non-blocking trust note about the selected drive's offset state."""

    kind: str  # one of the WARNING_* constants
    message: str  # ready-to-show, effect-first text
    severity: str  # SEVERITY_WARN | SEVERITY_INFO


def conf_offset_for(
    vendor: str, model: str, conf_offsets: Sequence[object]
) -> int | None:
    """The live whipper.conf offset for this drive, matched by canonical name.

    `conf_offsets` is a list of objects with ``.drive`` (whipper's decoded
    ``[drive:...]`` id) and ``.offset`` — i.e. ``offset_config.WhipperConfOffset``
    (taken as ``object`` to avoid importing the Qt-free offset_config here and to
    stay duck-typed). Returns None when whipper.conf has nothing for this drive.
    """
    target = normalize_drive_name(vendor, model)
    for entry in conf_offsets:
        drive = getattr(entry, "drive", None)
        offset = getattr(entry, "offset", None)
        if drive is None or offset is None:
            continue
        if normalize_combined(str(drive)) == target:
            # Duck-typed input (list[object]); a non-int offset must not break
            # the never-raises contract — skip it rather than raise.
            try:
                return int(offset)
            except (TypeError, ValueError):
                continue
    return None


def evaluate_drive_state(
    *,
    fingerprint: str,
    vendor: str,
    model: str,
    release: str,
    stored: DriveProfile | None,
    conf_offsets: Sequence[object],
    collisions: set[str],
    accuraterip_value: int | None = None,
) -> list[DriveWarning]:
    """Return the trust warnings for the currently-selected drive. Never raises.

    Empty list means "nothing to flag". All warnings are advisory — the caller
    surfaces them as text, never as a gate on ripping.

    `accuraterip_value` is the offset the bundled AccurateRip drive-model list
    gives for this drive (``offset_db.lookup``), or None if the model isn't
    listed. When it disagrees with the stored/applied offset, that's the exact
    silent-wrong-offset case this guard exists to catch — so it's surfaced.
    """
    warnings: list[DriveWarning] = []

    # 1. Identical-drive collision (the EAC-2007 bug). Only meaningful for the
    #    vm: tier — a shared serial/WWN would be the same physical unit (or a
    #    USB-bridge quirk), not two drives we must tell apart.
    if fingerprint in collisions and fingerprint.startswith("vm:"):
        warnings.append(
            DriveWarning(
                WARNING_COLLISION,
                "Two drives report the same model and neither exposes a serial "
                "number, so Platterpus can't tell them apart — a read offset "
                "learned on one may be applied to the other. Confirm the offset "
                "before trusting a rip.",
                SEVERITY_WARN,
            )
        )

    # 2. Firmware changed since we last saw this fingerprint — the offset may no
    #    longer apply. (Firmware isn't in the key, so the profile is still found.)
    if stored is not None and stored.release and release and stored.release != release:
        warnings.append(
            DriveWarning(
                WARNING_FIRMWARE_CHANGED,
                f"This drive's firmware changed ({stored.release} → {release}) "
                "since its offset was recorded. Re-run Set up drive to confirm "
                "the offset still applies.",
                SEVERITY_WARN,
            )
        )

    # 3 & 4. Offset provenance checks (only when we have a recorded offset).
    if stored is not None and stored.offset is not None:
        stored_value = stored.offset.value
        conf_value = conf_offset_for(vendor, model, conf_offsets)
        disagreement = False

        # (a) whipper.conf disagrees with the stored/applied value.
        if conf_value is not None and conf_value != stored_value:
            disagreement = True
            warnings.append(
                DriveWarning(
                    WARNING_DISAGREEMENT,
                    f"whipper.conf has {conf_value:+d}, but Platterpus recorded "
                    f"{stored_value:+d} ({describe_source(stored.offset.source)}). "
                    "These disagree — re-open Set up drive to reconcile them.",
                    SEVERITY_WARN,
                )
            )

        # (b) The AccurateRip drive list disagrees — the classic silent
        #     wrong-offset case. Name both values and which the rip will use.
        if accuraterip_value is not None and accuraterip_value != stored_value:
            disagreement = True
            warnings.append(
                DriveWarning(
                    WARNING_DISAGREEMENT,
                    f"The AccurateRip drive list says {accuraterip_value:+d} for "
                    f"this model, but the offset in use is {stored_value:+d} "
                    f"({describe_source(stored.offset.source)}). These disagree — "
                    f"the rip will use {stored_value:+d}. Re-open Set up drive and "
                    "save the AccurateRip value unless you measured otherwise.",
                    SEVERITY_WARN,
                )
            )

        # (c) Gentle nudge: the value isn't confirmed by agreement, and nothing
        #     above either corroborated or contradicted it. Honest about cyanrip
        #     having no on-disc measurement — a rip that verifies against
        #     AccurateRip is what actually confirms the offset on your unit.
        if (
            not disagreement
            and stored.offset.confidence is not Confidence.HIGH
            and conf_value is None
            and accuraterip_value is None
        ):
            warnings.append(
                DriveWarning(
                    WARNING_LOW_CONFIDENCE,
                    "This drive's offset isn't yet confirmed on your specific unit "
                    f"(source: {describe_source(stored.offset.source)}, "
                    f"{stored.offset.confidence.value} confidence). A rip that "
                    "matches AccurateRip will confirm it.",
                    SEVERITY_INFO,
                )
            )

    return warnings
