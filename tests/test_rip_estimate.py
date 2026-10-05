"""The up-front rip time estimate (`rip_estimate`), held to the filed rips.

The model's constants come from the rig's filed reports, and these tests read
those reports rather than restating them: the overhead, the rig's reading
multiple, and whether the model's range contains what each filed rip took.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import pytest

from platterpus import rip_estimate
from platterpus.adapters.accuraterip_offsets import normalize_drive_name
from platterpus.rip_estimate import ReadRate

_ARTIFACTS = Path(__file__).resolve().parent.parent / "docs" / "handshake"


@dataclass(frozen=True)
class _Filed:
    name: str
    mode: str | None
    matches: int
    retried: tuple[int, ...]
    elapsed: float
    lengths: dict[int, float]  # track number -> audio seconds
    extraction: float


def _filed_rips() -> list[_Filed]:
    """Every filed rip report that finished and carries per-track timings."""
    rips: list[_Filed] = []
    for path in sorted(_ARTIFACTS.glob("artifactsround*/*report.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if (data.get("outcome") or {}).get("status") != "success":
            continue
        tracks = [t for t in data.get("tracks") or [] if isinstance(t, dict)]
        lengths: dict[int, float] = {}
        extraction = 0.0
        usable = bool(tracks)
        for track in tracks:
            start, end = track.get("start_sector"), track.get("end_sector")
            took = track.get("extraction_elapsed_seconds")
            number = track.get("number")
            if not (
                isinstance(start, int)
                and isinstance(end, int)
                and isinstance(took, int | float)
                and isinstance(number, int)
            ):
                usable = False
                break
            lengths[number] = (end - start + 1) / 75
            extraction += float(took)
        elapsed = (data.get("timing") or {}).get("elapsed_seconds")
        if not usable or not isinstance(elapsed, int | float):
            continue
        speed = data.get("read_speed") or {}
        rips.append(
            _Filed(
                name=path.name,
                mode=(speed.get("secure_rerip") or {}).get("mode"),
                matches=int(speed.get("final_secure_rerip_matches") or 0),
                retried=tuple(
                    r["track"]
                    for r in speed.get("retried_tracks") or []
                    if isinstance(r, dict) and isinstance(r.get("track"), int)
                ),
                elapsed=float(elapsed),
                lengths=lengths,
                extraction=extraction,
            )
        )
    return rips


def _first_passes() -> list[_Filed]:
    """Rips whose album pass read each track once (no `-Z` on the first pass)."""
    return [r for r in _filed_rips() if r.mode == "dynamic" and r.matches == 0]


# --- the constants, against the artifacts -----------------------------------


def test_the_rigs_seed_is_its_measured_first_pass_multiple() -> None:
    passes = _first_passes()
    assert len(passes) >= 20, f"only {len(passes)} filed first passes to measure"
    multiples = [r.extraction / sum(r.lengths.values()) for r in passes]
    seed = rip_estimate.MODEL_SEEDS[normalize_drive_name("PIONEER", "BD-RW BDR-209D")]
    assert min(multiples) <= seed <= max(multiples), (seed, min(multiples))
    median = statistics.median(multiples)
    assert abs(seed - median) / median < 0.1, (
        f"the seed {seed} is not the filed median {median:.3f}"
    )


def test_the_overhead_is_inside_what_the_filed_rips_show() -> None:
    """Elapsed minus reading, on rips with no re-read: the per-rip overhead."""
    plain = [r for r in _first_passes() if not r.retried]
    assert len(plain) >= 10, f"only {len(plain)} filed rips without a re-read"
    overheads = [r.elapsed - r.extraction for r in plain]
    assert min(overheads) <= rip_estimate.OVERHEAD_S <= max(overheads), overheads


def test_every_filed_uniform_rip_falls_inside_the_estimates_range() -> None:
    """Uniform `-Z 2`: at least N+1 reads, at most the retry ceiling."""
    seed = rip_estimate.seed_for("PIONEER BD-RW BDR-209D")
    uniform = [r for r in _filed_rips() if r.mode == "uniform" and r.matches > 0]
    assert len(uniform) >= 3, f"only {len(uniform)} filed uniform rips"
    for rip in uniform:
        estimate = rip_estimate.estimate_rip(
            sum(rip.lengths.values()),
            seed,
            secure_rerip_matches=rip.matches,
            dynamic=False,
            max_retries=5,
        )
        assert estimate is not None and estimate.seconds_high is not None
        # 10% below the minimum: the seed is a median, and a rip a little
        # faster than it is still the model working.
        assert estimate.seconds * 0.9 <= rip.elapsed <= estimate.seconds_high, (
            rip.name,
            rip.elapsed,
            estimate,
        )


def test_every_filed_dynamic_rip_with_re_reads_falls_inside_the_model() -> None:
    """The main pass plus, per re-read track, N+1 to `-r` times its length."""
    seed = rip_estimate.seed_for("PIONEER BD-RW BDR-209D")
    reread = [r for r in _first_passes() if r.retried]
    assert len(reread) >= 4, f"only {len(reread)} filed rips with a re-read"
    for rip in reread:
        estimate = rip_estimate.estimate_rip(
            sum(rip.lengths.values()),
            seed,
            secure_rerip_matches=2,
            dynamic=True,
            max_retries=5,
        )
        assert estimate is not None
        assert estimate.reread_low is not None and estimate.reread_high is not None
        extra = sum(rip.lengths[n] for n in rip.retried if n in rip.lengths)
        low = estimate.seconds * 0.9 + extra * estimate.reread_low * 0.9
        high = estimate.seconds * 1.1 + extra * estimate.reread_high
        assert low <= rip.elapsed <= high, (rip.name, rip.elapsed, low, high)


# --- the folding ------------------------------------------------------------


def test_a_seed_is_replaced_by_the_drives_first_rip_and_later_rips_are_weighted() -> (
    None
):
    seed = rip_estimate.seed_for("PIONEER BD-RW BDR-209D")
    assert seed is not None and seed.rips == 0
    first = rip_estimate.fold(seed, 600.0, 300.0)
    assert first == ReadRate(600.0, 300.0, 1), "a seed was averaged with a real rip"
    second = rip_estimate.fold(first, 600.0, 600.0)
    assert second.rips == 2
    assert second.multiple is not None
    # Recent rips count more: the new rip's 1.0 pulls past the midpoint of 0.75.
    assert 0.75 < second.multiple < 1.0


def test_an_unknown_model_has_no_seed() -> None:
    assert rip_estimate.seed_for("SOME OTHER DRIVE") is None
    assert (
        rip_estimate.estimate_rip(
            600, None, secure_rerip_matches=0, dynamic=False, max_retries=5
        )
        is None
    )


class _Track:
    def __init__(self, start: object, end: object, took: object) -> None:
        self.start_sector = start
        self.end_sector = end
        self.extraction_elapsed_seconds = took


def test_the_first_pass_sample_counts_only_complete_tracks() -> None:
    sample = rip_estimate.first_pass_sample(
        [
            _Track(0, 7499, 110.0),  # 100 s of audio in 110 s
            _Track(7500, 14999, None),  # no extraction time: left out
            _Track(None, None, 50.0),  # no span: left out
            _Track(20000, 10000, 5.0),  # backwards span: left out
            _Track(15000, 22499, float("nan")),  # not a number: left out
        ]
    )
    assert sample == (100.0, 110.0)
    assert rip_estimate.first_pass_sample([]) is None


# --- the sentences ----------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "said"),
    [(45, "45s"), (413, "7m"), (3762, "1h 5m"), (10996, "3h 5m"), (7200, "2h")],
)
def test_rough_durations(seconds: float, said: str) -> None:
    assert rip_estimate.rough(seconds) == said


def test_the_sentences_say_what_the_figure_rests_on() -> None:
    seed = rip_estimate.seed_for("PIONEER BD-RW BDR-209D")
    dynamic = rip_estimate.estimate_rip(
        3583, seed, secure_rerip_matches=2, dynamic=True, max_retries=5
    )
    said = rip_estimate.describe(dynamic)
    assert said.startswith("Time estimate: about 1h 5m"), said
    assert "test rig" in said and "3 to 5 times" in said
    own = rip_estimate.describe(
        rip_estimate.estimate_rip(
            600,
            ReadRate(1200, 300, 4),
            secure_rerip_matches=0,
            dynamic=False,
            max_retries=5,
        )
    )
    assert "own reading speed over its last 4 rips" in own and "4.0x" in own
    assert "finished no rip" in rip_estimate.describe(None)
    assert "not identified" in rip_estimate.describe(None, known=False)
