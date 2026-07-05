"""Tests for platterpus.drive_media — the media-change auto-detect (fakes only;
the ioctl path is hardware-gated and degrades to 'unavailable')."""

from __future__ import annotations

from platterpus import drive_media
from platterpus.drive_media import (
    DISC,
    EMPTY,
    NOT_READY,
    OPEN,
    UNAVAILABLE,
    MediaWatcher,
    probe_disc_status,
)


def test_first_observation_never_fires() -> None:
    # A disc already in the drive at startup is handled by the normal startup
    # scan — the watcher must not also fire on its very first reading.
    w = MediaWatcher()
    assert w.observe(DISC) is False
    assert w.observe(DISC) is False  # steady state → still no fire


def test_fires_on_empty_to_disc() -> None:
    w = MediaWatcher()
    assert w.observe(EMPTY) is False  # baseline
    assert w.observe(DISC) is True  # a disc appeared → rescan


def test_fires_after_eject_then_reinsert() -> None:
    # The exact cancel→eject→new-disc sequence: disc present, then ejected
    # (tray open / empty), then a new disc inserted.
    w = MediaWatcher()
    assert w.observe(DISC) is False  # baseline (disc was in during/just after rip)
    assert w.observe(OPEN) is False  # cancel ejected it
    assert w.observe(EMPTY) is False  # tray closed empty (or still empty)
    assert w.observe(DISC) is True  # new disc → rescan


def test_unavailable_blip_never_triggers() -> None:
    # A busy drive mid-teardown reads 'unavailable'; that must not manufacture a
    # spurious rescan when it clears back to 'disc'.
    w = MediaWatcher()
    assert w.observe(EMPTY) is False
    assert w.observe(UNAVAILABLE) is False
    assert w.observe(DISC) is False  # came from 'unavailable', not a known-empty


def test_not_ready_to_disc_fires() -> None:
    w = MediaWatcher()
    assert w.observe(NOT_READY) is False
    assert w.observe(DISC) is True


def test_reset_forgets_baseline() -> None:
    # After a drive switch the caller resets; the next reading is a fresh
    # baseline (no fire even if it's a disc).
    w = MediaWatcher()
    w.observe(EMPTY)
    w.reset()
    assert w.observe(DISC) is False  # first obs after reset = baseline only


def test_probe_disc_status_never_raises_on_bad_device() -> None:
    # Best-effort contract: a missing/blank device degrades to 'unavailable',
    # never an exception (the caller just doesn't auto-rescan).
    assert probe_disc_status("") == UNAVAILABLE
    assert probe_disc_status("/dev/does-not-exist-platterpus") == UNAVAILABLE


def test_status_from_code_maps_cdrom_codes() -> None:
    # The CDROM_DRIVE_STATUS return codes map to our statuses; unknown → unavailable.
    assert drive_media.status_from_code(4) == DISC  # CDS_DISC_OK
    assert drive_media.status_from_code(1) == EMPTY  # CDS_NO_DISC
    assert drive_media.status_from_code(2) == OPEN  # CDS_TRAY_OPEN
    assert drive_media.status_from_code(3) == NOT_READY  # CDS_DRIVE_NOT_READY
    assert drive_media.status_from_code(0) == UNAVAILABLE  # CDS_NO_INFO / unknown
    assert drive_media.status_from_code(999) == UNAVAILABLE
