"""Every compiled regex in ``src/`` must run in roughly linear time.

Why this exists as a *sweep* rather than as a test per pattern: a profiling pass
(2026-07-30) timed all 80 compiled patterns across 14 modules at two input sizes
and found **four** that were super-linear. They had nothing in common except the
shapes that cause backtracking, and nobody had noticed any of them — so the
durable output of that investigation is this check, not the four fixes.

The one that mattered was ``adapters/accuraterip_offsets._CSV_LINE``:

    ^\\s*(?P<name>.+?)\\s*,\\s*(?P<offset>-?\\d+)\\s*$

quadratic in the line length (3000 chars → 13 ms; before a ``.strip()``
accidentally defused the all-whitespace case, **13.8 seconds**) — and it parses a
**user-edited CSV** that ``MainWindow.__init__`` loads **on the GUI thread before
the window is shown**. That is this project's never-block-the-GUI-thread rule
broken by a regex instead of by a subprocess, which is exactly the kind of thing a
per-pattern test would never have been written for.

The others: ``parsers/cd_info._NUM_TRACKS`` (unbounded ``\\d+``, 4000 digits →
141 ms), ``rip_timing._ETA_PIECE``, and ``deps.version.DEFAULT_VERSION_PATTERN``.

**What this test is not.** It is not a benchmark and must not fail because CI was
busy. It compares each pattern against *itself* at two input sizes and only
objects to super-linear **growth**, with a generous factor — so a uniformly slow
machine passes. It also never fails on a single reading: a flagged pattern is
re-measured, because a scheduler hiccup on one timing run is far more likely than
a genuine regression.
"""

from __future__ import annotations

import ast
import re
import time
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "platterpus"

# The two input sizes. A 4x jump in length should cost ~4x for a linear pattern;
# a quadratic one costs ~16x, and the four real offenders were all far worse than
# that (the CSV row grew 35x for a 4x input).
_SMALL = 500
_LARGE = 2000

# How much growth is allowed for that 4x input. 8x leaves generous headroom over
# the 4x a linear pattern costs, while every real offender exceeded it — the
# closest was 17.9 ms vs 1.1 ms, a factor of 16.
_MAX_GROWTH = 8.0

# Timings below this are dominated by measurement noise rather than by the
# pattern, so a ratio computed from them means nothing. 200 us is comfortably
# above the ~1 us floor of a `re.search` on a short string.
_NOISE_FLOOR_S = 200e-6

# How many times a single search may be repeated to lift its total above the
# noise floor. Repetition is what makes this sweep actually examine anything: a
# single `.search` on a fast pattern costs ~1 us, which is *under* the floor, so
# the first version of this test skipped it — and skipped 88 of the 90 patterns
# for the same reason while still reporting itself as a full sweep. Timing a
# batch instead gives every pattern a real per-search figure. The cap bounds the
# cost for the fastest patterns; a slow pattern clears the floor on the first
# repeat and never escalates, so the expensive case is cheap and vice versa.
#: Timing rounds per measurement; the MINIMUM is reported. Three is enough to
#: drop a single scheduler hiccup and cheap enough not to slow the sweep.
_TIMING_ROUNDS = 3
_MAX_REPEATS = 4096
_REPEAT_STEP = 8

# Filler characters, chosen to exercise the shapes that actually backtrack:
# digit runs (unbounded `\d+`), whitespace runs (`\s*` chains), word runs
# (lazy `.+?`), and a couple of structural characters that appear in the log and
# CSV formats these patterns parse.
_FILLS: tuple[str, ...] = ("0", " ", "a", "\t", ",", ":", "-", ".")


def _compiled_patterns() -> list[tuple[str, str]]:
    """Every module-level ``re.compile`` in ``src/``, as (location, pattern).

    Read from the source with ``ast`` rather than by importing, so a pattern is
    checked even if its module has import side effects, and so the location in the
    failure message is a real file:line a reader can open.
    """
    found: list[tuple[str, str]] = []
    for path in sorted(_SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (
            OSError,
            SyntaxError,
        ):  # pragma: no cover - a broken file fails elsewhere
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_compile = (
                isinstance(func, ast.Attribute)
                and func.attr == "compile"
                and isinstance(func.value, ast.Name)
                and func.value.id == "re"
            )
            if not is_compile or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                rel = path.relative_to(_SRC.parent.parent)
                found.append((f"{rel}:{node.lineno}", first.value))
    return found


def _seconds_per_search(compiled: re.Pattern[str], text: str) -> float:
    """Cost of one ``.search``, averaged over enough repeats to beat clock noise.

    Timed with ``.search`` because that is how these patterns are used on
    subprocess output and file rows — ``.match`` would anchor away the backtracking
    that ``.search`` has to do at every start position.

    **Reported as the MINIMUM over several timing rounds, not a single sample.**
    Scheduler noise, a GC pass, a CPU-frequency step and a co-tenant on the runner
    can only ever make a measurement *longer* — never shorter — so the minimum is
    the best available estimate of the pattern's real cost, and it is the standard
    way to time short operations (`timeit` documents exactly this reasoning).

    Written after this file's own detector-proof test flaked: a *linear* pattern
    measured 10.9x growth against an 8.0x ceiling, on one run out of three, in a
    container. A single noisy sample in the denominator inflates the ratio without
    bound, so the test reported a quadratic pattern where there was none — and a
    timing gate that reddens CI at random is a gate people switch off, which is
    worse than not having it.
    """
    best = float("inf")
    for _ in range(_TIMING_ROUNDS):
        repeats = 1
        while True:
            start = time.perf_counter()
            for _ in range(repeats):
                compiled.search(text)
            elapsed = time.perf_counter() - start
            if elapsed >= _NOISE_FLOOR_S or repeats >= _MAX_REPEATS:
                best = min(best, elapsed / repeats)
                break
            repeats *= _REPEAT_STEP
    return best


def _worst_growth(pattern: str) -> tuple[float, str, float]:
    """Return the worst (growth_ratio, fill, large_seconds) over the fills."""
    compiled = re.compile(pattern)
    worst = (0.0, "", 0.0)
    for fill in _FILLS:
        small = _seconds_per_search(compiled, fill * _SMALL)
        large = _seconds_per_search(compiled, fill * _LARGE)
        ratio = large / max(small, 1e-12)
        if ratio > worst[0]:
            worst = (ratio, fill, large)
    return worst


def test_every_compiled_regex_in_src_is_roughly_linear() -> None:
    """Sweep every pattern; re-measure anything that looks super-linear.

    The re-measurement is not politeness, it is what makes this usable in CI: a
    single timing can be wrecked by the scheduler, and a check that cries wolf
    gets deleted — which would be worse than not having it.
    """
    patterns = _compiled_patterns()
    # Floor: a sweep that finds nothing to examine is decoration. The codebase had
    # 80 compiled patterns when this was written; 40 allows real deletion without
    # letting the check quietly stop looking.
    assert len(patterns) >= 40, (
        f"only found {len(patterns)} compiled patterns in src/ — this sweep has "
        "stopped finding them, which would make it pass by examining nothing"
    )

    suspects: list[tuple[str, str, float, str]] = []
    measured = 0
    for location, pattern in patterns:
        ratio, fill, _ = _worst_growth(pattern)
        if ratio > 0.0:
            measured += 1
        if ratio > _MAX_GROWTH:
            suspects.append((location, pattern, ratio, fill))

    # The floor that matters. Counting *collected* patterns above only proves the
    # `ast` walk still works; it says nothing about whether any of them were
    # timed, and the first version of this sweep collected 90 and timed 2 — every
    # other pattern fell under the noise floor and was silently skipped, so the
    # check reported a clean sweep after examining 2% of it. Repetition (see
    # `_seconds_per_search`) is what closed that, and this is the assertion that
    # keeps it closed: a skip is now a failure, not a shrug.
    assert measured == len(patterns), (
        f"timed only {measured} of {len(patterns)} patterns — the rest produced no "
        "usable measurement, so this sweep is passing by not looking"
    )

    # Re-measure the suspects. Only a pattern that is slow twice is a finding.
    confirmed: list[str] = []
    for location, pattern, first_ratio, fill in suspects:
        second_ratio, _, large_s = _worst_growth(pattern)
        if second_ratio > _MAX_GROWTH:
            confirmed.append(
                f"{location}\n"
                f"    pattern: {pattern!r}\n"
                f"    a 4x longer input of {fill!r} cost {first_ratio:.1f}x then "
                f"{second_ratio:.1f}x more time ({large_s * 1000:.2f} ms at "
                f"{_LARGE} chars)"
            )

    assert not confirmed, (
        "these patterns grow super-linearly with input length, so a long line of "
        "external output or user-edited text can stall whatever thread they run "
        "on:\n\n" + "\n\n".join(confirmed) + "\n\n"
        "Fix by bounding a quantifier (`\\d{1,4}` rather than `\\d+`) or by "
        "replacing the pattern with string operations — `rpartition` did it for "
        "the CSV row that prompted this test."
    )


def test_the_sweep_can_still_tell_a_quadratic_pattern_from_a_linear_one() -> None:
    """Prove the detector detects — on both sides.

    The sweep above reports "no super-linear patterns", and that sentence reads
    the same whether the codebase is clean or the measurement broke. Everything it
    depends on is fragile in the quiet direction: a clock that returns the same
    value twice, a repeat loop the optimiser hoists, a growth threshold set too
    high. So this test hands ``_worst_growth`` two patterns whose answers are known
    and requires it to separate them.

    The quadratic one is the pattern that prompted this whole file —
    ``adapters/accuraterip_offsets._CSV_LINE`` as it was before the fix, whose
    ``.+?`` followed by ``\\s*,`` backtracks over every start position. The linear
    one is a bounded literal search, which must **not** trip the threshold: a
    detector that flags everything is as useless as one that flags nothing, and
    only the pair rules out both.
    """
    quadratic = r"^\s*(?P<name>.+?)\s*,\s*(?P<offset>-?\d+)\s*$"
    quad_ratio, _, quad_large_s = _worst_growth(quadratic)
    assert quad_ratio > _MAX_GROWTH, (
        f"the known-quadratic CSV row measured only {quad_ratio:.1f}x growth "
        f"({quad_large_s * 1000:.3f} ms at {_LARGE} chars) — under the "
        f"{_MAX_GROWTH}x threshold, so the sweep above would have passed it. The "
        "timing machinery is broken, and every 'clean' result it gives is worthless."
    )

    linear = r"Ripping track (?P<track>\d{1,3}) of (?P<total>\d{1,3})"
    lin_ratio, lin_fill, _ = _worst_growth(linear)
    assert lin_ratio <= _MAX_GROWTH, (
        f"a bounded linear pattern measured {lin_ratio:.1f}x growth on "
        f"{lin_fill!r} — the threshold is too tight and the sweep will cry wolf"
    )


@pytest.mark.parametrize(
    ("module", "attribute"),
    [
        ("platterpus.parsers.cd_info", "_NUM_TRACKS"),
        ("platterpus.deps.version", "DEFAULT_VERSION_PATTERN"),
    ],
)
def test_the_known_offenders_stay_bounded(module: str, attribute: str) -> None:
    """Pin the two fixed patterns by name, so a revert names itself.

    The sweep above would also catch these, but its failure message has to be
    generic. These two say which pattern and why, and they are cheap.
    """
    import importlib

    pattern = getattr(importlib.import_module(module), attribute)
    text = "9" * 4000
    start = time.perf_counter()
    pattern.search(text)
    elapsed = time.perf_counter() - start
    # 141 ms was the unbounded `\d+` measurement on this exact input; 20 ms is far
    # above what the bounded form needs (0.3 ms) and far below the bug.
    assert elapsed < 0.020, (
        f"{module}.{attribute} took {elapsed * 1000:.1f} ms on 4000 digits — an "
        "unbounded quantifier has come back"
    )
