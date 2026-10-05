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
cannot run quadratically. **The calls whose pattern is not a literal** stay
outside it, because a sweep cannot read them; they are counted per file in
``_UNTIMED_CALLS``, with the reason each cannot stall, and a test holds that
ledger to the tree in both directions.

**And it read ``src/`` only until 2026-10-05.** ``scripts/`` and ``build/`` —
the handshake tooling, the generators, the gate runner — are swept too now, by
their own test over the population the size ratchet reads
(``conftest.maintained_tooling_modules``). Their 88 literal patterns were all
linear when they joined; thirteen computed ones went into the ledger.

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
from conftest import maintained_tooling_modules
from hypothesis import given, settings
from hypothesis import strategies as st

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src" / "platterpus"

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


def _pick_clock() -> Callable[[], float]:
    """The CPU time THIS THREAD has used, where the platform measures it finely.

    **Not wall-clock time, and that is the fix for every flake this file has had.**
    Wall-clock time counts the time the test spent descheduled, and on a runner
    running the suite on every core (`pytest -n auto`) that is most of the error.
    Measured here on 2026-09-27, four cores with eight busy-loop processes beside
    the test: a linear pattern (`uiscript.script._TOKEN` on spaces, idle growth
    3.8-4.2x per 4x of input) timed on the wall clock read 14.5x and 20.5x,
    because one size's whole measurement landed in someone else's timeslice (178
    us against its idle 47 us). The three rounds whose minimum was meant to drop
    such a hiccup run back to back, inside the same slice, so they shared it. On
    this clock the same experiment read 3.6-4.9x at double and quadruple
    oversubscription. Descheduled time is not the pattern's cost; CPU time is.

    Falls back to `perf_counter` where the thread clock is coarser than a
    microsecond (Windows reports 15.6 ms), because a coarse clock would put every
    fast pattern under the noise floor and this sweep would then time nothing.
    """
    if time.get_clock_info("thread_time").resolution <= 1e-6:
        return time.thread_time
    return time.perf_counter


_clock: Callable[[], float] = _pick_clock()
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


def _re_calls(paths: list[Path]) -> list[tuple[str, ast.Call, str]]:
    """Every ``re.<function>(...)`` call in ``paths``: (repo-relative file, call, how).

    One walk for both halves of the population — the literal patterns the sweep
    times, and the computed ones it cannot (``_untimed_calls``) — so the two can
    never disagree about what counts as a call to ``re``.
    """
    found: list[tuple[str, ast.Call, str]] = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (
            OSError,
            SyntaxError,
        ):  # pragma: no cover - a broken file fails elsewhere
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in _HOW_EACH_CALL_RUNS
                and isinstance(func.value, ast.Name)
                and func.value.id == "re"
                and node.args
            ):
                found.append((rel, node, _HOW_EACH_CALL_RUNS[func.attr]))
    return found


def _is_literal_pattern(call: ast.Call) -> bool:
    first = call.args[0]
    return isinstance(first, ast.Constant) and isinstance(first.value, str)


def _compiled_patterns(
    paths: list[Path] | None = None,
) -> list[tuple[str, str, str]]:
    """Every literal pattern handed to ``re``: (location, pattern, how).

    ``paths`` defaults to every module under ``src/platterpus``; the tooling sweep
    passes ``conftest.maintained_tooling_modules`` instead.

    ``how`` is the method a measurement must use to time it the way it runs (see
    ``_HOW_EACH_CALL_RUNS``). Read from the source with ``ast`` rather than by
    importing, so a pattern is checked even if its module has import side
    effects, and so the location in the failure message is a real file:line a
    reader can open.
    """
    if paths is None:
        paths = sorted(_SRC.rglob("*.py"))
    found: list[tuple[str, str, str]] = []
    for rel, call, how in _re_calls(paths):
        first = call.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.append((f"{rel}:{call.lineno}", first.value, how))
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
            start = _clock()
            for _ in range(repeats):
                run(text)
            elapsed = _clock() - start
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


def _assert_every_pattern_is_roughly_linear(
    patterns: list[tuple[str, str, str]], *, floor: int, where: tuple[str, ...]
) -> None:
    """Time every pattern; re-measure anything that looks super-linear.

    The re-measurement is not politeness, it is what makes this usable in CI: a
    single timing can be wrecked by the scheduler, and a check that cries wolf
    gets deleted — which would be worse than not having it.

    ``where`` is the repo-relative prefixes the patterns must come from. The floor
    counts only patterns found there, and a pattern from anywhere else fails:
    with two sweeps sharing this helper, a tooling sweep handed the package's
    patterns would otherwise clear its floor on the wrong population and pass.
    """
    elsewhere = sorted(
        loc for loc, _pattern, _how in patterns if not loc.startswith(where)
    )
    assert not elsewhere, (
        f"this sweep is for {where} and was handed patterns from elsewhere: "
        f"{elsewhere[:5]}"
    )
    # Floor: a sweep that finds nothing to examine is decoration.
    assert len(patterns) >= floor, (
        f"only found {len(patterns)} compiled patterns in {where} (floor {floor}) "
        "— this sweep has stopped finding them, which would make it pass by "
        "examining nothing"
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


def test_every_compiled_regex_in_src_is_roughly_linear() -> None:
    """The package: every literal pattern handed to ``re`` under ``src/platterpus``.

    The codebase had 80 compiled patterns when this was written; a floor of 40
    allows real deletion without letting the check quietly stop looking.
    """
    _assert_every_pattern_is_roughly_linear(
        _compiled_patterns(), floor=40, where=("src/platterpus/",)
    )


#: Floor on the tooling's literal patterns: 88 on 2026-10-05, when the sweep was
#: extended to them (TASKS `scripts-outside-gates`). Half, as for the package.
_MIN_TOOLING_PATTERNS = 44


def test_every_compiled_regex_in_the_tooling_is_roughly_linear() -> None:
    """``scripts/`` and ``build/``: the same sweep over the maintainer tooling.

    These parse handshake laps, workflow files and generated documents, some of
    them written by the peer project, so a pattern that stalls on a long line
    there stalls a release gate (`handshake.py --release-gate`) or a CI check.
    The sweep read ``src/`` only until 2026-10-05; the population is the one the
    size ratchet reads, ``conftest.maintained_tooling_modules``. A separate test
    from the package sweep so ``pytest -n auto`` can run the two at once, and so
    a failure says which half it is in.
    """
    _assert_every_pattern_is_roughly_linear(
        _compiled_patterns(maintained_tooling_modules(_REPO_ROOT)),
        floor=_MIN_TOOLING_PATTERNS,
        where=("scripts/", "build/"),
    )


#: DEBT LEDGER — calls to ``re`` whose pattern is NOT a literal, so the sweep
#: above cannot read it and does not time it, per file with the count and why.
#: The sweep's docstring named the package's two in prose until 2026-10-05; prose
#: is not a population check, and the tooling added thirteen more. **May shrink,
#: never grow**: a new computed pattern must be entered here with its reason, so
#: the sweep's blind spot is a number a reviewer sees rather than a silence.
_UNTIMED_CALLS: dict[str, tuple[int, str]] = {
    "src/platterpus/adapters/cache_probe.py": (
        1,
        "the pattern is a parameter; its callers pass module-level patterns "
        "the sweep times where they are compiled",
    ),
    "src/platterpus/ripper_messages.py": (
        1,
        "built from the ripper's published format strings; each line is "
        "bounded by `_TAIL_LIMIT`",
    ),
    "scripts/bommap/reading.py": (
        1,
        "an escaped literal between two fixed lookarounds; no quantifier",
    ),
    "scripts/emit_envelope.py": (
        2,
        "a header field name from a fixed table, escaped or a plain word, in "
        "a fixed anchored shape",
    ),
    "scripts/handshake.py": (
        6,
        "escaped field names and version strings in fixed shapes, and the "
        "GO-claim and heading patterns, whose repeats are bounded "
        "(`{0,200}?`, `{0,3}`)",
    ),
    "scripts/laplang/context.py": (
        2,
        "an escaped section name in a fixed anchored heading shape",
    ),
    "scripts/round_digest.py": (
        1,
        "a header field name from a fixed table, anchored, with no quantifier",
    ),
    "scripts/verify_log_surface.py": (
        1,
        "the operator's own `--expect` patterns, which the tool exists to run",
    ),
}


def _untimed_calls(paths: list[Path]) -> dict[str, int]:
    """Per file, how many ``re`` calls carry a pattern that is not a literal."""
    counts: dict[str, int] = {}
    for rel, call, _how in _re_calls(paths):
        if not _is_literal_pattern(call):
            counts[rel] = counts.get(rel, 0) + 1
    return counts


def test_every_pattern_the_sweep_cannot_read_is_ledgered() -> None:
    """The sweep's blind spot, measured both ways against ``_UNTIMED_CALLS``.

    A new computed pattern (a file not in the ledger, or a count above its entry)
    fails, because the sweep would report clean while never having timed it. A
    count below its entry fails too, so the ledger cannot keep room that a new
    untimed call could quietly fill.
    """
    population = sorted(_SRC.rglob("*.py")) + maintained_tooling_modules(_REPO_ROOT)
    measured = _untimed_calls(population)
    # Floor, in the shape of the stale check below: an empty ledger, or a walk
    # that found nothing, must not compare equal and pass.
    assert _UNTIMED_CALLS, "the ledger is empty, so this check cannot fail"
    recorded = {name: count for name, (count, _why) in _UNTIMED_CALLS.items()}
    grown = sorted(
        f"{name}: {count} untimed call(s), ledger says {recorded.get(name, 0)}"
        for name, count in measured.items()
        if count > recorded.get(name, 0)
    )
    assert not grown, (
        "these files hand `re` a pattern the sweep cannot read, so it is never "
        "timed:\n  " + "\n  ".join(grown) + "\nPrefer a module-level literal the "
        "sweep can time. If the pattern must be computed, bound every repeat and "
        "enter the file in _UNTIMED_CALLS with the reason it cannot stall."
    )
    stale = sorted(
        f"{name}: ledger says {count}, found {measured.get(name, 0)}"
        for name, count in recorded.items()
        if measured.get(name, 0) < count
    )
    assert not stale, (
        "lower or remove these _UNTIMED_CALLS entries, so the room cannot be "
        "refilled silently:\n  " + "\n  ".join(stale)
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


def _confirmation(
    pattern: str, first_large_s: float, verdicts: list[bool]
) -> Callable[[], Growth]:
    """One `_confirm_at_scale` on a run of spaces, in the shape `_settled` takes.

    Each attempt's verdict is appended to ``verdicts``, and the tests below settle
    on and assert the VERDICT, not only the ratio beside it: the verdict is what
    the sweep acts on, and a confirmation that answered ``True`` with an honest
    ratio would pass a test that read the ratio alone.

    The two tests were single measurements until 2026-09-28, when the first of
    them read 8.9x on CI's Python 3.12 leg for a pattern that measures 3.9x here
    (median of 300, max 4.8x with the whole suite on every core beside it; the
    runner's noise was not reproduced). The sweep calls a pattern super-linear only
    when two measurements agree, so a test of its confirmation that fails on one
    was holding it to a stricter standard than the sweep keeps, and failing at the
    rate of a single noisy sample. Both now settle as the detector proof does: one
    wrong answer is forgiven, and a wrong answer on every attempt still fails.
    """

    def measure() -> Growth:
        is_real, ratio, seconds = _confirm_at_scale(
            pattern, " ", "search", first_large_s
        )
        verdicts.append(is_real)
        return ratio, " ", seconds

    return measure


def test_the_confirmation_clears_the_pattern_ci_flagged_on_noise() -> None:
    """The pattern flagged on 2026-09-27 at 8.4x then 8.5x is linear at scale."""
    flagged = (
        r"^\s+(?:Elapsed(?: time)?|Rip time|Extraction time|Time taken):\s+"
        r"(?P<s>\d{1,7}(?:\.\d{1,6})?)\s*(?:s|sec|secs|seconds)\b"
    )
    verdicts: list[bool] = []
    attempts = _settled(
        _confirmation(flagged, 0.00005, verdicts), lambda _ratio: not verdicts[-1]
    )
    assert not verdicts[-1], (
        f"a linear pattern confirmed at {_series(attempts)} over {len(attempts)} "
        "attempts, so the sweep would report it as a finding"
    )


def test_the_confirmation_still_catches_a_real_offender() -> None:
    """The drive-name normaliser before its 2026-09-26 fix, which is quadratic on a
    run of spaces with no hyphen, is confirmed at the larger pair too."""
    verdicts: list[bool] = []
    attempts = _settled(
        _confirmation(r"\s+-\s+", 0.005, verdicts), lambda _ratio: verdicts[-1]
    )
    assert verdicts[-1], (
        f"a quadratic pattern measured only {_series(attempts)} at scale over "
        f"{len(attempts)} attempts"
    )


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
    start = _clock()
    pattern.search(text)
    elapsed = _clock() - start
    # 141 ms was the unbounded `\d+` measurement on this exact input; 20 ms is far
    # above what the bounded form needs (0.3 ms) and far below the bug.
    assert elapsed < 0.020, (
        f"{module}.{attribute} took {elapsed * 1000:.1f} ms on 4000 digits — an "
        "unbounded quantifier has come back"
    )


# --- Offenders behind a literal prefix (2026-10-05) ----------------------------
#
# The sweep feeds each pattern runs of ONE character. A pattern that only
# backtracks once a literal prefix has matched (`Read stalls: x`, `KEY: x`) never
# reaches its slow region on such input, so the sweep reports it linear. That is
# how `_REQUIREMENT` and `_WIRE_FIELD` passed it when it was extended to the
# tooling, though each took about a third of a second on one 8,000-character line.
# Both had the same shape: a lazy capture followed by trailing whitespace before
# `$`, which retries the whitespace run at every step of the lazy capture. They
# are fixed and pinned by name below; the sweep's blind spot, and the same shape
# in `src/` (`parsers/cyanrip_log.py`), are recorded in TASKS.


def _pattern_assigned_to(rel: str, name: str) -> re.Pattern[str]:
    """The pattern a module assigns to ``name``, read from source, flags included.

    Read with ``ast`` rather than by importing, as the sweep reads, so the pin
    holds the text in the file and needs none of the script's import-time path
    setup. Flags are evaluated from ``re.<FLAG>`` names joined by ``|``.
    """
    tree = ast.parse((_REPO_ROOT / rel).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if not (isinstance(value, ast.Call) and value.args):
            continue
        pattern = value.args[0]
        assert isinstance(pattern, ast.Constant) and isinstance(pattern.value, str)
        flags = 0
        for flag_node in [*value.args[1:], *(k.value for k in value.keywords)]:
            for part in ast.walk(flag_node):
                if isinstance(part, ast.Attribute):
                    flags |= int(getattr(re, part.attr))
        return re.compile(pattern.value, flags)
    raise AssertionError(f"{rel} assigns no pattern to {name}")


#: (module, name, a line that drives the old pattern into its quadratic region).
_PREFIXED_OFFENDERS: list[tuple[str, str, str]] = [
    ("scripts/bommap/reading.py", "_REQUIREMENT", "a b" + " " * 20_000 + "c"),
]


@pytest.mark.parametrize(
    ("rel", "name", "line"),
    _PREFIXED_OFFENDERS,
    ids=[f"{rel}:{name}" for rel, name, _line in _PREFIXED_OFFENDERS],
)
def test_the_prefixed_offenders_stay_fast_on_the_line_that_found_them(
    rel: str, name: str, line: str
) -> None:
    """Each fixed pattern, on the line that showed it quadratic, by name.

    20,000 spaces cost the old patterns about 2 s (0.36 s at 8,000, growing 4x
    per doubling); the greedy forms take microseconds. 50 ms is far from both.
    """
    pattern = _pattern_assigned_to(rel, name)
    start = _clock()
    pattern.search(line)
    elapsed = _clock() - start
    assert elapsed < 0.050, (
        f"{rel}:{name} took {elapsed * 1000:.1f} ms on a {len(line)}-character "
        "line: a lazy capture before trailing whitespace has come back"
    )


#: The pattern `_REQUIREMENT` replaced, kept as the reference its rewrite must
#: agree with on every input.
_OLD_REQUIREMENT = (
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<extras>\[[^\]]*\])?\s*"
    r"(?P<spec>.*?)\s*$"
)


def _match_shape(match: re.Match[str] | None) -> tuple[object, ...] | None:
    return None if match is None else (match.span(), match.groupdict())


@settings(max_examples=400)
@given(st.text(alphabet="aZ0._-[]= <,\t\n\r", max_size=40))
def test_the_rewritten_requirement_pattern_reads_what_the_old_one_read(
    text: str,
) -> None:
    """Same match, same span, same groups, on every input — or it is not a fix.

    The rewrite exists to change the TIME and nothing else. The alphabet is the
    characters each part of the pattern branches on: name characters, the extras
    brackets, the separators of a version spec, and every kind of whitespace,
    including the newline that `.` refuses and whitespace classes accept.
    """
    old = re.compile(_OLD_REQUIREMENT)
    new = _pattern_assigned_to("scripts/bommap/reading.py", "_REQUIREMENT")
    assert _match_shape(new.match(text)) == _match_shape(old.match(text))


def test_the_requirement_rewrite_agrees_on_the_lines_the_tool_reads() -> None:
    """The equivalence above, on real shapes, with a floor on matches compared."""
    old = re.compile(_OLD_REQUIREMENT)
    new = _pattern_assigned_to("scripts/bommap/reading.py", "_REQUIREMENT")
    lines = [
        "PySide6>=6.11.1,<6.12",
        "  ruff >=0.15.22,<0.16  ",
        "sigstore[extra]>=4.5.0,<4.6",
        "pkg",
        "pkg   ",
        "a b" + " " * 50 + "c",
        "name x\n",
        "name x\n y",
    ]
    shapes = [(_match_shape(old.match(s)), _match_shape(new.match(s))) for s in lines]
    assert all(o == n for o, n in shapes), shapes
    assert sum(o is not None for o, _ in shapes) >= 6, "too few lines matched"


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


def test_the_timings_do_not_count_time_spent_off_the_cpu() -> None:
    """The sweep's clock must not count time the test was not running (2026-09-27).

    Sleeping is the plainest form of being descheduled. On the wall clock this
    reads 50 ms; on the thread's CPU clock it reads almost nothing, and that
    difference is what stopped a busy runner reading a linear pattern as 20x.
    """
    if time.get_clock_info("thread_time").resolution > 1e-6:
        pytest.skip("this platform's thread clock is coarse; the sweep uses wall time")
    start = _clock()
    time.sleep(0.05)
    asleep = _clock() - start
    assert asleep < 0.01, (
        f"the sweep's clock counted {asleep * 1000:.1f} ms of sleep, so it measures "
        "time spent descheduled, which is the noise that made linear patterns fail"
    )
    # Non-triviality: the same clock does advance while this thread computes.
    start = _clock()
    total = 0
    while _clock() - start < 0.02:
        total += 1
    assert total > 0
