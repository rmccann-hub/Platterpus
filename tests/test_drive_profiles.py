"""Tests for the per-drive profile ledger (drive_profiles + drive_profile_store).

Covers the five tiers (easy/medium/hard/edge/unexpected per docs/testing.md):
the stable fingerprint priority/normalization/collision logic, a never-raises
property test on the fingerprint, sysfs identity reading with fake roots, the
store's never-raises load + atomic round-trip + migration, and the mismatch
guard's truth table. All of this is pure/off-hardware — no real drive needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.drive_profile_store import DriveProfileStore
from platterpus.drive_profiles import (
    SEVERITY_INFO,
    SEVERITY_WARN,
    WARNING_COLLISION,
    WARNING_DISAGREEMENT,
    WARNING_FIRMWARE_CHANGED,
    WARNING_LOW_CONFIDENCE,
    Confidence,
    DriveProfile,
    OffsetRecord,
    OffsetSource,
    compute_fingerprint,
    confidence_for,
    confidence_rank,
    evaluate_drive_state,
    find_fingerprint_collisions,
    read_drive_identity,
)


# A tiny stand-in for offset_config.WhipperConfOffset (the guard is duck-typed).
@dataclass(frozen=True)
class _ConfOffset:
    drive: str
    offset: int


# --- Fingerprint priority + tiers -------------------------------------------


def test_fingerprint_prefers_wwn_then_serial_then_model() -> None:
    # WWN wins outright.
    assert compute_fingerprint("PIONEER", "BD-RW BDR-209D", serial="S1", wwn="W1") == (
        "wwn:W1"
    )
    # No WWN → serial (scoped by normalized vendor/model).
    sn = compute_fingerprint("PIONEER", "BD-RW BDR-209D", serial="S1")
    assert sn == "sn:PIONEER BD-RW BDR-209D:S1"
    # Neither → vendor/model only.
    vm = compute_fingerprint("PIONEER", "BD-RW BDR-209D")
    assert vm == "vm:PIONEER BD-RW BDR-209D"


def test_fingerprint_tiers_never_cross_collide() -> None:
    # The same vendor/model on three tiers must produce three distinct keys.
    base = ("PIONEER", "BD-RW BDR-209D")
    keys = {
        compute_fingerprint(*base),
        compute_fingerprint(*base, serial="ABC"),
        compute_fingerprint(*base, wwn="WWN"),
    }
    assert len(keys) == 3


def test_fingerprint_normalizes_whipper_double_space() -> None:
    # whipper emits the double-spaced model; the vm: key matches the
    # single-spaced AccurateRip form (shared canonicalization).
    a = compute_fingerprint("PIONEER", "BD-RW  BDR-209D")
    b = compute_fingerprint("pioneer", "BD-RW BDR-209D")
    assert a == b == "vm:PIONEER BD-RW BDR-209D"


def test_fingerprint_firmware_not_in_key() -> None:
    # release is intentionally absent from compute_fingerprint's signature: a
    # firmware change must NOT orphan a profile. Same inputs → same key.
    assert compute_fingerprint("LG", "BH16NS40") == compute_fingerprint(
        "LG", "BH16NS40"
    )


def test_fingerprint_gaining_a_serial_changes_the_key() -> None:
    # A drive that starts reporting a serial becomes a new (fail-safe) identity.
    assert compute_fingerprint("LG", "BH16NS40") != compute_fingerprint(
        "LG", "BH16NS40", serial="X"
    )


@settings(max_examples=300, deadline=None)
@given(
    vendor=st.text(),
    model=st.text(),
    serial=st.text(),
    wwn=st.text(),
)
def test_fingerprint_never_raises_and_is_nonempty(
    vendor: str, model: str, serial: str, wwn: str
) -> None:
    fp = compute_fingerprint(vendor, model, serial=serial, wwn=wwn)
    assert isinstance(fp, str)
    assert fp  # always a non-empty, stable key, even for empty inputs


# --- Collision detection ----------------------------------------------------


def test_collisions_flags_shared_fingerprint() -> None:
    fps = ["vm:A", "vm:A", "vm:B"]
    assert find_fingerprint_collisions(fps) == {"vm:A"}


def test_collisions_empty_when_all_distinct() -> None:
    assert find_fingerprint_collisions(["wwn:1", "sn:x:2", "vm:B"]) == set()


# --- sysfs identity reading -------------------------------------------------


def test_read_drive_identity_reads_serial_and_wwn(tmp_path: Path) -> None:
    dev = tmp_path / "sr0" / "device"
    dev.mkdir(parents=True)
    (dev / "serial").write_text("SER123\n")
    (dev / "wwn").write_text("0x5001\n")
    assert read_drive_identity("/dev/sr0", sys_block=tmp_path) == ("SER123", "0x5001")


def test_read_drive_identity_absent_returns_empty(tmp_path: Path) -> None:
    # No sysfs node at all (the common optical-drive case) → ("", "").
    assert read_drive_identity("/dev/sr9", sys_block=tmp_path) == ("", "")


# --- Confidence helpers -----------------------------------------------------


def test_confidence_for_maps_sources() -> None:
    assert confidence_for(OffsetSource.OFFSET_FIND) is Confidence.HIGH
    assert confidence_for(OffsetSource.ACCURATERIP_LIST) is Confidence.MEDIUM
    assert confidence_for(OffsetSource.MANUAL) is Confidence.MEDIUM
    assert confidence_for(OffsetSource.UNKNOWN) is Confidence.LOW


def test_confidence_rank_orders() -> None:
    assert confidence_rank(Confidence.HIGH) > confidence_rank(Confidence.MEDIUM)
    assert confidence_rank(Confidence.MEDIUM) > confidence_rank(Confidence.LOW)


def test_unknown_enum_strings_decode_to_safe_defaults() -> None:
    # The never-raises contract: a future/garbled stored value never blows up.
    assert OffsetSource("not-a-real-source") is OffsetSource.UNKNOWN
    assert Confidence("???") is Confidence.LOW


# --- Store round-trip + never-raises ---------------------------------------


def _sample_profile() -> DriveProfile:
    return DriveProfile(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW  BDR-209D",
        release="1.51",
        offset=OffsetRecord(
            value=667,
            source=OffsetSource.ACCURATERIP_LIST,
            confidence=Confidence.MEDIUM,
            detected_at="2026-06-29T00:00:00Z",
        ),
        cache_defeat=True,
        cache_defeat_source=OffsetSource.WHIPPER_CONF,
        last_seen_device="/dev/sr0",
        last_seen_at="2026-06-29T00:00:00Z",
    )


def test_store_round_trips_through_disk(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    store = DriveProfileStore()
    profile = _sample_profile()
    store.upsert(profile)
    store.save(path)

    loaded = DriveProfileStore.load(path)
    got = loaded.get(profile.fingerprint)
    assert got == profile  # enums + nested OffsetRecord survive byte-for-byte


def test_store_missing_file_is_empty(tmp_path: Path) -> None:
    store = DriveProfileStore.load(tmp_path / "nope.json")
    assert store.all() == []


def test_store_corrupt_json_is_empty_and_leaves_file(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text("{not valid json")
    store = DriveProfileStore.load(path)
    assert store.all() == []
    assert path.exists()  # the bad file is preserved for inspection, not clobbered


def test_store_drops_unusable_profile_keeps_good(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text(
        '{"schema_version": 1, "profiles": {'
        '"vm:GOOD": {"vendor": "V", "model": "M"}, '
        '"vm:BAD": "this should be an object"}}'
    )
    store = DriveProfileStore.load(path)
    assert store.get("vm:GOOD") is not None
    assert store.get("vm:BAD") is None


def test_store_future_schema_version_does_not_crash(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text('{"schema_version": 999, "profiles": {}}')
    assert DriveProfileStore.load(path).all() == []


def test_store_unknown_enum_string_loads_as_safe_default(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text(
        '{"schema_version": 1, "profiles": {"vm:X": {"vendor": "V", "model": "M", '
        '"offset": {"value": 12, "source": "wat", "confidence": "huge"}}}}'
    )
    profile = DriveProfileStore.load(path).get("vm:X")
    assert profile is not None
    assert profile.offset is not None
    assert profile.offset.source is OffsetSource.UNKNOWN
    assert profile.offset.confidence is Confidence.LOW


def test_store_top_level_not_object_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text("[1, 2, 3]")  # valid JSON, but not the object we expect
    assert DriveProfileStore.load(path).all() == []


def test_store_profiles_not_a_dict_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text('{"schema_version": 1, "profiles": "oops"}')
    assert DriveProfileStore.load(path).all() == []


def test_store_unreadable_path_is_empty(tmp_path: Path) -> None:
    # Point at a directory: read_text raises IsADirectoryError (an OSError),
    # which load() must swallow into an empty store rather than propagate.
    a_dir = tmp_path / "is_a_dir"
    a_dir.mkdir()
    assert DriveProfileStore.load(a_dir).all() == []


def test_store_offset_with_non_int_value_is_dropped(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    path.write_text(
        '{"schema_version": 1, "profiles": {"vm:X": {"vendor": "V", "model": "M", '
        '"offset": {"value": "not-an-int", "source": "manual", "confidence": "medium"}}}}'
    )
    profile = DriveProfileStore.load(path).get("vm:X")
    assert profile is not None
    assert profile.offset is None  # the unusable offset is dropped, the profile kept


def test_store_atomic_save_leaves_no_tmp(tmp_path: Path) -> None:
    path = tmp_path / "drive_profiles.json"
    store = DriveProfileStore()
    store.upsert(_sample_profile())
    store.save(path)
    assert path.exists()
    assert not path.with_suffix(".tmp").exists()


# --- Mismatch guard truth table ---------------------------------------------


def _stored(offset: OffsetRecord | None, release: str = "1.51") -> DriveProfile:
    return DriveProfile(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release=release,
        offset=offset,
    )


def test_guard_consistent_state_is_quiet() -> None:
    stored = _stored(
        OffsetRecord(667, OffsetSource.OFFSET_FIND, Confidence.HIGH),
    )
    warnings = evaluate_drive_state(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=stored,
        conf_offsets=[_ConfOffset("PIONEER BD-RW BDR-209D", 667)],
        collisions=set(),
    )
    assert warnings == []


def test_guard_flags_identical_drive_collision() -> None:
    fp = "vm:PIONEER BD-RW BDR-209D"
    warnings = evaluate_drive_state(
        fingerprint=fp,
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=None,
        conf_offsets=[],
        collisions={fp},
    )
    kinds = {w.kind for w in warnings}
    assert WARNING_COLLISION in kinds
    assert all(
        w.severity == SEVERITY_WARN for w in warnings if w.kind == WARNING_COLLISION
    )


def test_guard_collision_only_for_vm_tier() -> None:
    # A shared serial/WWN is the same physical unit, not the EAC-2007 case.
    fp = "sn:PIONEER BD-RW BDR-209D:ABC"
    warnings = evaluate_drive_state(
        fingerprint=fp,
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=None,
        conf_offsets=[],
        collisions={fp},
    )
    assert all(w.kind != WARNING_COLLISION for w in warnings)


def test_guard_flags_firmware_change() -> None:
    stored = _stored(
        OffsetRecord(667, OffsetSource.OFFSET_FIND, Confidence.HIGH), release="1.50"
    )
    warnings = evaluate_drive_state(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=stored,
        conf_offsets=[_ConfOffset("PIONEER BD-RW BDR-209D", 667)],
        collisions=set(),
    )
    assert WARNING_FIRMWARE_CHANGED in {w.kind for w in warnings}


def test_guard_flags_offset_disagreement() -> None:
    stored = _stored(OffsetRecord(12, OffsetSource.MANUAL, Confidence.MEDIUM))
    warnings = evaluate_drive_state(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=stored,
        conf_offsets=[_ConfOffset("PIONEER BD-RW BDR-209D", 667)],
        collisions=set(),
    )
    disagreements = [w for w in warnings if w.kind == WARNING_DISAGREEMENT]
    assert len(disagreements) == 1
    # The message names both values so the user sees which one whipper uses.
    assert "+667" in disagreements[0].message
    assert "+12" in disagreements[0].message


def test_guard_skips_malformed_conf_entries() -> None:
    # A conf-offset object missing .drive/.offset must be skipped, not crash.
    class _Bad:
        pass

    stored = _stored(OffsetRecord(667, OffsetSource.OFFSET_FIND, Confidence.HIGH))
    warnings = evaluate_drive_state(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=stored,
        conf_offsets=[_Bad(), _ConfOffset("PIONEER BD-RW BDR-209D", 667)],
        collisions=set(),
    )
    assert warnings == []  # the good entry matches; the bad one is ignored


def test_guard_nudges_low_confidence_unmeasured_offset() -> None:
    stored = _stored(
        OffsetRecord(667, OffsetSource.ACCURATERIP_LIST, Confidence.MEDIUM)
    )
    warnings = evaluate_drive_state(
        fingerprint="vm:PIONEER BD-RW BDR-209D",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.51",
        stored=stored,
        conf_offsets=[],  # whipper.conf hasn't confirmed it
        collisions=set(),
    )
    nudges = [w for w in warnings if w.kind == WARNING_LOW_CONFIDENCE]
    assert len(nudges) == 1
    assert nudges[0].severity == SEVERITY_INFO
