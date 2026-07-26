"""Regression tests: the auto-fix's convergence must reach the rendered log.

Real-hardware finding, 2026-07-26 (v0.5.9 run, track 5 of the Police disc). The
album's whole-disc `.log` records the FIRST read pass, so a track that the
per-track auto-fix afterwards re-read with `-Z N` — and whose re-reads *agreed*
— still parsed as `secure_rerip_converged=None`. Consequences, both fixed here:

* the EAC-compatible log printed a lone `Copy CRC` for a track whose CRC two
  independent reads provably agreed on (that agreement IS the Test & Copy
  evidence — KDD-30), so the log under-reported the read effort we performed;
* the JSON report's per-track record contradicted its own
  `read_speed.retried_tracks` entry, which said `converged: true`.

The honesty rules under test are the interesting part: only a track that both
converged AND was swapped in may be marked (otherwise the shipped bytes are
still the single-read first-pass ones), and a value the log itself carried is
never overwritten.
"""

from __future__ import annotations

from types import SimpleNamespace

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.rip_log import RipLog, TrackResult
from platterpus.ui.main_window_rip import RipMixin


def _window(retried: list[dict] | None) -> SimpleNamespace:
    """A minimal stand-in exposing only the attribute the enricher reads."""
    return SimpleNamespace(_last_retried_tracks=retried)


def _log() -> RipLog:
    """Two tracks shaped like the real run: 3 never converged, 5 was fixed."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(number=3, filename="03.flac", copy_crc="3D8FCF0C"),
            TrackResult(number=5, filename="05.flac", copy_crc="E0036697"),
        ),
    )


def _by_number(rip_log: RipLog, number: int) -> TrackResult:
    return next(t for t in rip_log.tracks if t.number == number)


def test_converged_and_swapped_track_is_marked() -> None:
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": True}]
    )
    out = RipMixin._apply_auto_fix_convergence(window, _log())
    assert _by_number(out, 5).secure_rerip_converged is True


def test_a_track_that_never_converged_is_recorded_as_such() -> None:
    # Track 3 was re-read and no two reads agreed. That's a MEASURED negative, so
    # it's recorded — the log must not let it pass as a clean single-read track.
    window = _window(
        [
            {"track": 3, "reripped_z": 2, "converged": False, "replaced": False},
            {"track": 5, "reripped_z": 2, "converged": True, "replaced": True},
        ]
    )
    out = RipMixin._apply_auto_fix_convergence(window, _log())
    assert _by_number(out, 3).secure_rerip_converged is False


def test_tracks_the_auto_fix_never_touched_stay_unknown() -> None:
    # Only re-read tracks get a verdict; a track nobody re-read is neither proven
    # nor doubted.
    rip_log = RipLog(
        tracks=(
            TrackResult(number=1, copy_crc="B0D122E7"),
            TrackResult(number=5, copy_crc="E0036697"),
        )
    )
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": True}]
    )
    out = RipMixin._apply_auto_fix_convergence(window, rip_log)
    assert _by_number(out, 1).secure_rerip_converged is None


def test_converged_but_not_swapped_is_not_marked() -> None:
    # The re-read agreed but the improved file never made it into the album, so
    # the shipped audio is still the single-read first pass. Claiming convergence
    # would attribute the proof to bytes it wasn't earned on.
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": False}]
    )
    out = RipMixin._apply_auto_fix_convergence(window, _log())
    assert _by_number(out, 5).secure_rerip_converged is None


def test_never_overwrites_a_value_the_log_carried() -> None:
    # Fill-only: a log that explicitly recorded non-convergence keeps that fact.
    rip_log = RipLog(
        tracks=(
            TrackResult(
                number=5,
                copy_crc="E0036697",
                secure_rerip_converged=False,
            ),
        )
    )
    window = _window(
        [{"track": 5, "reripped_z": 2, "converged": True, "replaced": True}]
    )
    out = RipMixin._apply_auto_fix_convergence(window, rip_log)
    assert _by_number(out, 5).secure_rerip_converged is False


def test_no_auto_fix_history_returns_the_log_unchanged() -> None:
    rip_log = _log()
    assert RipMixin._apply_auto_fix_convergence(_window([]), rip_log) is rip_log
    assert RipMixin._apply_auto_fix_convergence(_window(None), rip_log) is rip_log


def test_never_raises_on_a_malformed_history() -> None:
    # The history is worker-supplied data; a bad shape must degrade to "no
    # enrichment", never abort the post-rip chain.
    window = _window(["not-a-dict"])  # type: ignore[list-item]
    out = RipMixin._apply_auto_fix_convergence(window, _log())
    assert _by_number(out, 5).secure_rerip_converged is None


def test_rendered_log_shows_test_and_copy_only_for_the_fixed_track() -> None:
    # The end-to-end shape of the real regression: the rescued track earns the
    # EAC Test/Copy pair; the still-unstable one keeps its lone Copy CRC.
    window = _window(
        [
            {"track": 3, "reripped_z": 2, "converged": False, "replaced": False},
            {"track": 5, "reripped_z": 2, "converged": True, "replaced": True},
        ]
    )
    text = render_eac_style_log(RipMixin._apply_auto_fix_convergence(window, _log()))
    assert "Test CRC E0036697" in text
    assert "Copy CRC E0036697" in text
    assert "Test CRC 3D8FCF0C" not in text
    assert "Copy CRC 3D8FCF0C" in text
    # …and the track whose re-reads disagreed is called out, per-track and in the
    # conclusive report — cyanrip's own health line says "no errors" for it.
    assert "not confirmed reproducible" in text
    assert "Read stability      : track(s) 3" in text


def test_a_clean_rip_gains_no_read_stability_line() -> None:
    # Nothing measured → nothing said. A clean rip's conclusive report is unchanged.
    text = render_eac_style_log(_log())
    assert "Read stability" not in text
    assert "not confirmed reproducible" not in text
