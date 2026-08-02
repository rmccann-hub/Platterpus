"""`realtime_multiplier` must not report the disc *fraction* as a *rate*.

The real number, off the rig (2026-08-01): a rip cancelled after 2 of 14
tracks reported ``realtime_multiplier: 0.21``. That is 755 ÷ 3582 — elapsed
over the whole disc's length — which is only a rate if the whole disc was
ripped. Actual throughput was about 0.93x. A plausible wrong number is worse
than none, because nothing about it invites checking.
"""

from __future__ import annotations

from platterpus.rip_report import build_timing
from platterpus.ui.main_window_rip import _ripped_audio_seconds


class _Track:
    def __init__(self, start: int | None, end: int | None) -> None:
        self.start_sector = start
        self.end_sector = end


class _Log:
    def __init__(self, *tracks: _Track) -> None:
        self.tracks = tracks


# --- the number that shipped ------------------------------------------------


def test_a_cancelled_rip_does_not_report_the_disc_fraction_as_a_rate() -> None:
    """The exact rig numbers, with no audio figure available."""
    timing = build_timing(755, disc_seconds=3582, completed=False)
    assert timing["realtime_multiplier"] is None
    assert "not computed" in timing["realtime_multiplier_basis"]
    # The elapsed facts are still recorded — only the derived claim is withheld.
    assert timing["elapsed_seconds"] == 755
    assert timing["disc_seconds"] == 3582


def test_a_cancelled_rip_uses_the_audio_it_actually_extracted() -> None:
    """When we know how much audio came off the disc, that IS a real rate.

    Tracks 1–3 of the rig's disc are 49,920 sectors ≈ 666 s, plus part of track
    4 — about 700 s in 755 s of wall clock, so ~0.93x. That is a defensible
    number; 0.21 never was.
    """
    timing = build_timing(
        755, disc_seconds=3582, audio_seconds_ripped=700, completed=False
    )
    assert timing["realtime_multiplier"] == 0.93
    assert timing["realtime_multiplier_basis"] == "audio actually extracted"


def test_a_completed_rip_reports_the_true_rate() -> None:
    timing = build_timing(3600, disc_seconds=3582, completed=True)
    assert timing["realtime_multiplier"] == 1.01


def test_an_unknown_outcome_keeps_the_old_behaviour() -> None:
    """`completed=None` must not be read as "did not complete".

    Every existing caller omits the flag, and a caller that does not KNOW the
    rip was cancelled has not asserted that it was — silently withholding the
    multiplier from all of them would be its own dishonesty.
    """
    timing = build_timing(3600, disc_seconds=3582)
    assert timing["realtime_multiplier"] == 1.01
    assert "realtime_multiplier_basis" not in timing


def test_zero_elapsed_yields_no_rate_rather_than_a_division_error() -> None:
    assert (
        build_timing(0, disc_seconds=3582, completed=True).get("realtime_multiplier")
        is None
    )


# --- the helper that supplies the honest denominator ------------------------


def test_ripped_audio_is_summed_from_the_sector_spans() -> None:
    """Inclusive of both endpoints, at 75 sectors per second."""
    assert _ripped_audio_seconds(_Log(_Track(0, 74), _Track(75, 149))) == 2.0


def test_ripped_audio_is_none_when_the_log_has_no_geometry() -> None:
    """None means "cannot say", which build_timing turns into a null multiplier
    — not a zero, which would divide into a nonsense rate."""
    assert _ripped_audio_seconds(_Log(_Track(None, None))) is None
    assert _ripped_audio_seconds(_Log()) is None


def test_ripped_audio_ignores_a_track_whose_span_is_backwards() -> None:
    """Never raises, and never subtracts: a malformed span contributes nothing
    rather than corrupting the total."""
    assert _ripped_audio_seconds(_Log(_Track(500, 100), _Track(0, 74))) == 1.0


# --- the gap the rig found in the first version of this fix ------------------


def test_a_failed_rip_is_not_completed_either() -> None:
    """Gating on "was it cancelled" alone left the failure case open.

    Real artifact, 2026-08-02: the Roots Music rip died after 2 seconds on a bad
    argument, read nothing, and archived `realtime_multiplier: 0.0` — 2 s over a
    3467 s disc. `outcome.status` was "failed", not "cancelled", so a
    cancel-only gate would still have computed it.
    """
    timing = build_timing(2, disc_seconds=3467, completed=False)
    assert timing["realtime_multiplier"] is None
    assert "did not finish" in timing["realtime_multiplier_basis"]
