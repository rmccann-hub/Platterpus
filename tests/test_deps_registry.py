"""Tests for the real dependency registry (platterpus.deps.registry.SPECS).

The manager tests build synthetic specs; this pins properties of the actual
shipped registry that the rest of the app relies on — notably that new deps
(here, the P1 ffmpeg transcoder) are declared correctly and route through the
single subsystem (Critical Rule #6).
"""

from __future__ import annotations

from platterpus.deps.checks import ProbeResult
from platterpus.deps.registry import SPECS, Tier


def _spec(dep_id: str):
    return next((s for s in SPECS if s.dep_id == dep_id), None)


def test_dep_ids_are_unique() -> None:
    ids = [s.dep_id for s in SPECS]
    assert len(ids) == len(set(ids))


def test_ffmpeg_spec_is_registered_and_optional() -> None:
    spec = _spec("ffmpeg")
    assert spec is not None, "ffmpeg must be in the single dependency registry"
    # Optional: its absence only disables the MP3/WAV transcode, never blocks a
    # FLAC rip — so the launch check must not nag.
    assert spec.optional is True
    # Not auto-installable (host/container-routed like flac/metaflac).
    assert spec.tier is Tier.MANUAL
    assert spec.install_command is None
    # A copyable search string is required for the manual tier.
    assert spec.search_string


def test_ffmpeg_probe_is_a_zero_arg_callable_returning_a_proberesult(
    monkeypatch,
) -> None:
    spec = _spec("ffmpeg")
    assert spec is not None
    # The manager calls every probe with no args; stub the underlying check so
    # this doesn't depend on a real ffmpeg being installed.
    monkeypatch.setattr(
        "platterpus.deps.registry.check_ffmpeg",
        lambda: ProbeResult(
            present=True, version=(6, 1, 1), location="/usr/bin/ffmpeg"
        ),
    )
    result = spec.probe()
    assert isinstance(result, ProbeResult)
    assert result.present is True
