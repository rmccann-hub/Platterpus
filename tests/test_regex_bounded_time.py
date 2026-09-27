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

**Its population was not closed, and the gap was found by a stopwatch
(2026-09-26).** It swept module-level ``re.compile`` calls only, and reported a
clean sweep over them while an inline ``re.sub(r"\\s+-\\s+", ...)`` in the
drive-name normaliser went quadratic on a long run of spaces: 0.54 s on the
drive-offset CSV test's 20,000-space row, which parses on the GUI thread before
the window is shown. It surfaced only when the suite went parallel and that test's
wall-clock bound tipped over. Now every ``re.<function>(<literal>, ...)`` call is
in the population, and each inline one is timed the way its call site uses it:
``re.match``/``re.fullmatch`` anchored, everything else by ``.search``. Timing a
``fullmatch`` on a filename by ``.search`` would report a quadratic pattern that
cannot run quadratically. **Two calls remain outside it**, because their pattern
is not a literal a sweep can read: ``adapters/cache_probe.py`` (a pattern passed
in) and ``ripper_messages.py`` (built from the ripper's published format
strings, bounded by ``_TAIL_LIMIT``).

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
from collections.abc import Callable
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


#: The `re` functions whose first argument is a pattern, and how each one runs
#: it. `compile` does not say how the pattern will be used, so it is timed by
#: the worst case, `.search`, which retries at every start position.
_HOW_EACH_CALL_RUNS: dict[str, str] = {
    "compile": "search",
    "search": "search",
    "sub": "search",
    "subn": "search",
    "split": "search",
    "findall": "search",
    "finditer": "search",
    "match": "match",
    "fullmatch": "fullmatch",
}


def _compiled_patterns() -> list[tuple[str, str, str]]:
    """Every literal pattern handed to ``re`` in ``src/``: (location, pattern, how).

    ``how`` is the method a measurement must use to time it the way it runs (see
    ``_HOW_EACH_CALL_RUNS``). Read from the source with ``ast`` rather than by
    importing, so a pattern is checked even if its module has import side
    effects, and so the location in the failure message is a real file:line a
    reader can open.
    """
    found: list[tuple[str, str, str]] = []
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
            is_re_call = (
                isinstance(func, ast.Attribute)
                and func.attr in _HOW_EACH_CALL_RUNS
                and isinstance(func.value, ast.Name)
                and func.value.id == "re"
            )
            if not is_re_call or not node.args:
                continue
            assert isinstance(func, ast.Attribute)  # narrowed by is_re_call
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                rel = path.relative_to(_SRC.parent.parent)
                how = _HOW_EACH_CALL_RUNS[func.attr]
                found.append((f"{rel}:{node.lineno}", first.value, how))
    return found


def _seconds_per_search(
    compiled: re.Pattern[str],
    text: str,
    *,
    enough_s: float | None = None,
    how: str = "search",
) -> float:
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

    ``enough_s`` stops after the first round whose single search took at least
    that long. Only the known-quadratic proof passes it (2026-09-26): its search
    on 2,000 spaces takes about 3.6 s, three rounds of that cost 11 s, and
    scheduler noise cannot move a measurement that size by the 8x the threshold
    asks. It is never used where a false alarm is the risk: there a single long
    sample is exactly the noise the minimum exists to discard.

    ``how`` names the method to time (``search``, ``match`` or ``fullmatch``), so
    an inline call is measured the way its call site runs it.
    """
    run = getattr(compiled, how)
    best = float("inf")
    for _ in range(_TIMING_ROUNDS):
        repeats = 1
        while True:
            start = time.perf_counter()
            for _ in range(repeats):
                run(text)
            elapsed = time.perf_counter() - start
            if elapsed >= _NOISE_FLOOR_S or repeats >= _MAX_REPEATS:
                best = min(best, elapsed / repeats)
                break
            repeats *= _REPEAT_STEP
        if enough_s is not None and best >= enough_s:
            break
    return best


def _worst_growth(
    pattern: str, *, stop_above: float | None = None, how: str = "search"
) -> tuple[float, str, float]:
    """Return the worst (growth_ratio, fill, large_seconds) over the fills.

    ``stop_above`` returns as soon as one fill exceeds it. Only the test that
    must show a known-quadratic pattern IS caught passes it: one fill over the
    threshold is the whole proof, and timing a quadratic pattern on all eight
    fills at full size cost 22 s of every suite run (2026-09-26). The sweep of
    ``src/`` never passes it, because there the worst fill is the answer.
    """
    compiled = re.compile(pattern)
    worst = (0.0, "", 0.0)
    enough_s = 0.25 if stop_above is not None else None
    for fill in _FILLS:
        small = _seconds_per_search(compiled, fill * _SMALL, enough_s=enough_s, how=how)
        large = _seconds_per_search(compiled, fill * _LARGE, enough_s=enough_s, how=how)
        ratio = large / max(small, 1e-12)
        if ratio > worst[0]:
            worst = (ratio, fill, large)
        if stop_above is not None and worst[0] > stop_above:
            break
    return worst


#: How many times the detector proof below may measure one side before it
#: concludes. The sweep calls a pattern super-linear only when it is slow twice;
#: the proof holds its own two answers to the same standard. Noise can only make a
#: timing LONGER, so a broken clock or a wrong threshold still fails every attempt,
#: and only a spike on one attempt is forgiven. Added 2026-09-27 after the proof
#: failed once in about six parallel runs and passed 8 of 8 when re-run under load.
_PROOF_ATTEMPTS = 3

Growth = tuple[float, str, float]


def _settled(
    measure: Callable[[], Growth], holds: Callable[[float], bool]
) -> list[Growth]:
    """Measure until ``holds(ratio)`` or the attempts run out; return every attempt.

    Every attempt is returned, not only the last, so a failure message can show
    the whole series. The one unreproduced failure of this proof left no record of
    which side tripped, and that is the reason this function reports all of them.
    """
    attempts: list[Growth] = []
    for _ in range(_PROOF_ATTEMPTS):
        attempts.append(measure())
        if holds(attempts[-1][0]):
            break
    return attempts


def _series(attempts: list[Growth]) -> str:
    return ", ".join(f"{ratio:.1f}x" for ratio, _, _ in attempts)


#: One search this slow on a ``_LARGE``-character line is a stall whatever its
#: growth, so a suspect that slow is confirmed without timing a longer line. For the
#: CSV row that started this file, the longer line would take about a minute.
_STALL_S = 0.1


def _confirm_at_scale(
    pattern: str, fill: str, how: str, first_large_s: float
) -> tuple[bool, float, float]:
    """Does a suspect grow super-linearly at a LARGER input pair too?

    Returns ``(confirmed, ratio, seconds)``. The first measurement compares
    ``_SMALL`` to ``_LARGE`` characters, where a fast pattern's whole search is
    tens of microseconds and fixed per-call costs are a large share of it.
    Re-measuring at the same sizes, as this sweep first did, repeats that
    weakness inside the same noisy window: on 2026-09-27 CI flagged
    ``cyanrip_log._TRACK_ELAPSED_SECONDS`` at 8.4x and then 8.5x, while measured
    here it grew 3.8-4.3x per 4x of input on Python 3.11, 3.12 and 3.13 all the
    way to 32,000 characters. A genuinely super-linear pattern grows at least as
    fast at the larger pair, so this is a stronger second witness, not a weaker
    threshold.
    """
    if first_large_s >= _STALL_S:
        return True, first_large_s / _STALL_S, first_large_s
    compiled = re.compile(pattern)
    base = _seconds_per_search(compiled, fill * _LARGE, how=how)
    bigger = _seconds_per_search(compiled, fill * (_LARGE * 4), enough_s=0.25, how=how)
    ratio = bigger / max(base, 1e-12)
    return ratio > _MAX_GROWTH, ratio, bigger


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

    suspects: list[tuple[str, str, str, float, str, float]] = []
    measured = 0
    for location, pattern, how in patterns:
        ratio, fill, large_s = _worst_growth(pattern, how=how)
        if ratio > 0.0:
            measured += 1
        if ratio > _MAX_GROWTH:
            suspects.append((location, pattern, how, ratio, fill, large_s))

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

    # Confirm each suspect at a larger input pair. Only a pattern that is also
    # super-linear there is a finding (see `_confirm_at_scale` for why the same
    # sizes twice was not a second witness).
    confirmed: list[str] = []
    for location, pattern, how, first_ratio, fill, first_large_s in suspects:
        is_real, second_ratio, second_s = _confirm_at_scale(
            pattern, fill, how, first_large_s
        )
        if is_real:
            confirmed.append(
                f"{location}\n"
                f"    pattern: {pattern!r}, timed by .{how}\n"
                f"    a 4x longer input of {fill!r} cost {first_ratio:.1f}x more at "
                f"{_SMALL}->{_LARGE} chars, then {second_ratio:.1f}x at "
                f"{_LARGE}->{_LARGE * 4} ({second_s * 1000:.2f} ms)"
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
    quad = _settled(
        lambda: _worst_growth(quadratic, stop_above=_MAX_GROWTH),
        lambda ratio: ratio > _MAX_GROWTH,
    )
    quad_ratio, _, quad_large_s = quad[-1]
    assert quad_ratio > _MAX_GROWTH, (
        f"the known-quadratic CSV row measured only {_series(quad)} growth over "
        f"{len(quad)} attempts ({quad_large_s * 1000:.3f} ms at {_LARGE} chars on "
        f"the last) — under the {_MAX_GROWTH}x threshold every time, so the sweep "
        "above would have passed it. The timing machinery is broken, and every "
        "'clean' result it gives is worthless."
    )

    linear = r"Ripping track (?P<track>\d{1,3}) of (?P<total>\d{1,3})"
    lin = _settled(lambda: _worst_growth(linear), lambda ratio: ratio <= _MAX_GROWTH)
    lin_ratio, lin_fill, _ = lin[-1]
    assert lin_ratio <= _MAX_GROWTH, (
        f"a bounded linear pattern measured {_series(lin)} growth over {len(lin)} "
        f"attempts ({lin_fill!r} on the last) — over the {_MAX_GROWTH}x threshold "
        "every time, so the threshold is too tight and the sweep will cry wolf"
    )


def test_the_confirmation_clears_the_pattern_ci_flagged_on_noise() -> None:
    """The pattern flagged on 2026-09-27 at 8.4x then 8.5x is linear at scale."""
    flagged = (
        r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):\s+"
        r"(?P<s>\d{1,7}(?:\.\d{1,6})?)\s*(?:s|sec|secs|seconds)\b"
    )
    is_real, ratio, _ = _confirm_at_scale(flagged, " ", "search", 0.00005)
    assert not is_real, f"a linear pattern confirmed at {ratio:.1f}x"


def test_the_confirmation_still_catches_a_real_offender() -> None:
    """The drive-name normaliser before its 2026-09-26 fix, which is quadratic on a
    run of spaces with no hyphen, is confirmed at the larger pair too."""
    is_real, ratio, _ = _confirm_at_scale(r"\s+-\s+", " ", "search", 0.005)
    assert is_real, f"a quadratic pattern measured only {ratio:.1f}x at scale"


def test_a_stall_is_confirmed_without_timing_a_longer_line() -> None:
    """Passed a pattern that is not even valid, so a version that times anything
    raises instead of passing."""
    is_real, _, seconds = _confirm_at_scale("(", " ", "search", _STALL_S)
    assert is_real and seconds == _STALL_S


def test_a_spike_on_one_attempt_is_forgiven_and_a_real_failure_is_not() -> None:
    """The re-measure forgives noise and nothing else, shown with stand-ins.

    Noise only lengthens a timing, so one bad attempt followed by a good one is
    noise. A measurement that is bad every time is a real finding, and it must
    still fail after every attempt has been spent.
    """
    noisy = iter([(10.9, "0", 0.001), (3.8, "0", 0.001)])
    attempts = _settled(lambda: next(noisy), lambda ratio: ratio <= _MAX_GROWTH)
    assert [a[0] for a in attempts] == [10.9, 3.8]

    always_bad = _settled(
        lambda: (10.9, "0", 0.001), lambda ratio: ratio <= _MAX_GROWTH
    )
    assert len(always_bad) == _PROOF_ATTEMPTS
    assert not always_bad[-1][0] <= _MAX_GROWTH
    assert _series(always_bad) == ", ".join(["10.9x"] * _PROOF_ATTEMPTS)


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


def test_the_sweep_reads_inline_calls_and_times_each_as_it_runs() -> None:
    """The population is every literal pattern handed to `re`, not only compiles.

    Pinned by the pattern that was missing: the drive-name normaliser's inline
    `re.sub`, quadratic until 2026-09-26 and invisible to a sweep of
    `re.compile` alone. And an anchored call must be timed anchored, or a
    `fullmatch` on a filename reads as quadratic when it cannot run that way.
    """
    patterns = _compiled_patterns()
    normaliser = [
        pattern
        for location, pattern, how in patterns
        if location.startswith("src/platterpus/adapters/accuraterip_offsets.py")
        and "-" in pattern
        and how == "search"
    ]
    assert normaliser, (
        "the drive-name normaliser's inline re.sub is not in the sweep's "
        "population; the sweep is back to reading re.compile calls only"
    )
    assert any(how == "fullmatch" for _location, _pattern, how in patterns), (
        "no anchored call was found, so nothing is being timed as it runs"
    )
