"""The free-space floor a rip is checked against before it starts (review C10)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from platterpus import disk_space
from platterpus.disk_space import (
    FLAC_FLOOR,
    PCM_BYTES_PER_SECOND,
    audio_seconds,
    bytes_needed,
    check,
    free_bytes,
)


def _track(number: int, length_ms: int | None) -> SimpleNamespace:
    return SimpleNamespace(number=number, length_ms=length_ms)


def test_audio_seconds_needs_every_selected_length() -> None:
    tracks = [_track(1, 60_000), _track(2, 120_000), _track(3, None)]
    assert audio_seconds(tracks, (1, 2)) == 180.0
    assert audio_seconds(tracks) is None, "a track with no length was guessed"
    assert audio_seconds([]) is None


def test_the_floor_is_the_flac_master_plus_the_derived_format() -> None:
    hour = 3600.0
    flac = bytes_needed(hour, "flac")
    assert flac == int(hour * PCM_BYTES_PER_SECOND * FLAC_FLOOR)
    # Every derived format adds to the master (Critical rule #4: FLAC is kept).
    for fmt in ("wavpack", "mp3", "wav"):
        derived = bytes_needed(hour, fmt)
        assert derived is not None and flac is not None and derived > flac, fmt
    wav = bytes_needed(hour, "wav")
    assert wav is not None and wav >= int(hour * PCM_BYTES_PER_SECOND), "WAV is PCM"
    assert bytes_needed(hour, "nonsense") == flac, "an unknown format is not a floor"
    assert bytes_needed(None, "flac") is None and bytes_needed(0, "flac") is None


def test_check_is_tri_state_and_never_refuses_on_unknown(tmp_path: Path) -> None:
    assert check(None, 0, tmp_path, "flac").refuse is None
    assert check(10**9, None, tmp_path, "flac").refuse is None
    refused = check(10**9, 10**6, tmp_path, "mp3")
    assert refused.refuse is True
    assert str(tmp_path) in refused.message and "FLAC + mp3" in refused.message
    assert "1 MB free" in refused.message and "1.0 GB" in refused.message
    assert check(10**6, 10**9, tmp_path, "flac").refuse is False


def test_free_bytes_asks_the_nearest_folder_that_exists(tmp_path: Path) -> None:
    """The album folder does not exist before the rip makes it."""
    free = free_bytes(tmp_path / "not" / "yet" / "made")
    assert free is not None and free > 0


def test_the_check_never_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_folder: Path) -> int:
        raise RuntimeError("statvfs went away")

    monkeypatch.setattr(disk_space, "free_bytes", boom)
    result = disk_space.check_output_space(tmp_path, [_track(1, 60_000)], (), "flac")
    assert result.refuse is None and "check failed" in result.message
