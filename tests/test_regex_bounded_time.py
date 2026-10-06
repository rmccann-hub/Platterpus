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
import re._parser as _sre_parser  # the stdlib's pattern parser: see `_lead_ins`
import time
from collections.abc import Callable, Sequence
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

#: One timed input: a LEAD-IN, the FILL character repeated, and a TAIL. Only the
#: run of the fill grows between the two sizes; the lead-in and the tail are fixed.
#: The sweep's original inputs are the shapes with no lead-in and no tail.
Shape = tuple[str, str, str]

#: The original inputs: a run of one character, alone.
_FILL_ONLY: tuple[Shape, ...] = tuple(("", fill, "") for fill in _FILLS)


#: Two of them by name, for the tests that measure one.
_SPACES: Shape = ("", " ", "")
_ZEROS: Shape = ("", "0", "")


def _text(shape: Shape, length: int) -> str:
    """The input a shape describes, with its run ``length`` characters long."""
    lead, fill, tail = shape
    return lead + fill * length + tail


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
    rounds: int = _TIMING_ROUNDS,
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

    ``rounds`` is lowered to 1 only by the lead-in screen, which times about thirty
    times as many inputs as the original sweep. A screen may read high on noise;
    it can never read low, and every pattern it flags is re-measured at a larger
    size with the full rounds before anything fails (``_confirm_at_scale``).
    """
    run = getattr(compiled, how)
    best = float("inf")
    for _ in range(rounds):
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


#: (growth ratio, the shape that grew most, seconds at the larger size).
Growth = tuple[float, Shape, float]


def _worst_growth(
    pattern: str,
    *,
    stop_above: float | None = None,
    how: str = "search",
    shapes: Sequence[Shape] = _FILL_ONLY,
    rounds: int = _TIMING_ROUNDS,
) -> Growth:
    """Return the worst (growth_ratio, shape, large_seconds) over ``shapes``.

    ``stop_above`` returns as soon as one shape exceeds it. Only the tests that
    must show a known-quadratic pattern IS caught pass it: one shape over the
    threshold is the whole proof, and timing a quadratic pattern on all eight
    fills at full size cost 22 s of every suite run (2026-09-26). The sweeps
    never pass it, because there the worst shape is the answer.
    """
    compiled = re.compile(pattern)
    worst: Growth = (0.0, ("", "", ""), 0.0)
    enough_s = 0.25 if stop_above is not None else None
    for shape in shapes:
        small = _seconds_per_search(
            compiled, _text(shape, _SMALL), enough_s=enough_s, how=how, rounds=rounds
        )
        large = _seconds_per_search(
            compiled, _text(shape, _LARGE), enough_s=enough_s, how=how, rounds=rounds
        )
        ratio = large / max(small, 1e-12)
        if ratio > worst[0]:
            worst = (ratio, shape, large)
        if stop_above is not None and worst[0] > stop_above:
            break
    return worst


# --- Lead-ins: inputs that get PAST a pattern's literal prefix (2026-10-06) ----
#
# A run of one character never gets past `Read stalls:`, so a pattern that only
# backtracks once its label has matched looked linear to the shapes above. Eight
# such patterns in `parsers/cyanrip_log.py` were quadratic for that reason, and
# two in the tooling (TASKS, *Found while integrating*, item 4). So each pattern
# is also timed on runs that START INSIDE IT: for every repeat that can take a
# variable number of characters, a lead-in is the shortest text that reaches that
# repeat, alone and with one character the repeat accepts, and the run of the
# fill follows. `Read stalls: a` then 2,000 spaces then `x` is one such input.
#
# The lead-ins are derived from the pattern itself, by the standard library's own
# pattern parser (`re._parser`, the module `re.compile` uses), not from a list of
# labels kept by hand: a hand-kept list covers the patterns someone thought of,
# and the point of a sweep is the one nobody thought of. `re._parser` is private,
# so a Python that drops it fails this file's import loudly rather than quietly
# timing nothing; it has been there, under this name, since Python 3.11, the
# oldest version the project supports.

#: Where a run sits relative to the rest of the line. With no tail, a run that
#: ends the line; with `x`, a run followed by one more character, which is what
#: makes a trailing `\s*$` fail and retry. Each catches patterns the other cannot:
#: the lazy `\S.*?\s*$` needs the `x`, and `TITLE\s+(?P<value>.*\S)` needs none.
_TAILS: tuple[str, ...] = ("", "x")

#: The opcodes `re._parser` uses for a repeat (`*`, `+`, `?`, `{m,n}`, and their
#: lazy and possessive forms).
_REPEATS: frozenset[str] = frozenset({"MAX_REPEAT", "MIN_REPEAT", "POSSESSIVE_REPEAT"})

#: Characters tried, in order, when a lead-in needs one character of a class.
_CLASS_CANDIDATES: str = "a0 x-.:,A_/#=\t" + "".join(map(chr, range(33, 127)))

#: Each category a parsed character class can hold, as a pattern `re` can test.
_CATEGORY_TESTS: dict[str, str] = {
    "CATEGORY_DIGIT": r"\d",
    "CATEGORY_NOT_DIGIT": r"\D",
    "CATEGORY_SPACE": r"\s",
    "CATEGORY_NOT_SPACE": r"\S",
    "CATEGORY_WORD": r"\w",
    "CATEGORY_NOT_WORD": r"\W",
    "CATEGORY_LINEBREAK": r"\n",
    "CATEGORY_NOT_LINEBREAK": r"[^\n]",
}

#: One node of a parsed pattern: an opcode and its argument.
_Node = tuple[object, object]


def _op(node: _Node) -> str:
    """A node's opcode by name (``LITERAL``, ``MAX_REPEAT``, ...)."""
    return str(getattr(node[0], "name", node[0]))


def _in_class(char: str, items: list[_Node]) -> bool:
    """Whether ``char`` is in a parsed character class (an ``IN`` node's items)."""
    negated = False
    hit = False
    for node in items:
        op, arg = _op(node), node[1]
        if op == "NEGATE":
            negated = True
        elif op == "LITERAL" and isinstance(arg, int):
            hit = hit or ord(char) == arg
        elif op == "RANGE" and isinstance(arg, tuple):
            hit = hit or arg[0] <= ord(char) <= arg[1]
        elif op == "CATEGORY":
            test = _CATEGORY_TESTS.get(str(getattr(arg, "name", arg)), "(?!)")
            hit = hit or re.fullmatch(test, char) is not None
    return hit != negated


def _witness(nodes: list[_Node]) -> str:
    """The shortest text the nodes match, as near as one pass can tell.

    Every repeat at its minimum count, the first branch of an alternation nested
    in a repeat (`_flattenings` lays out the others), and nothing for an anchor
    or a lookaround. Best effort by design: a lead-in that
    does not quite match only means one input that does not reach its repeat,
    and the sweep still times every other input it has.
    """
    out: list[str] = []
    for node in nodes:
        op, arg = _op(node), node[1]
        if op == "LITERAL" and isinstance(arg, int):
            out.append(chr(arg))
        elif op == "NOT_LITERAL":
            out.append("b" if arg == ord("a") else "a")
        elif op == "ANY":
            out.append("a")
        elif op == "IN" and isinstance(arg, list):
            out.append(next((c for c in _CLASS_CANDIDATES if _in_class(c, arg)), ""))
        elif op == "BRANCH" and isinstance(arg, tuple):
            out.append(_witness(list(arg[1][0])))
        elif op == "SUBPATTERN" and isinstance(arg, tuple):
            out.append(_witness(list(arg[3])))
        elif op == "ATOMIC_GROUP":
            out.append(_witness(list(arg)))  # type: ignore[call-overload]  # a SubPattern
        elif op in _REPEATS and isinstance(arg, tuple):
            out.append(_witness(list(arg[2])) * int(arg[0]))
    return "".join(out)


#: The most ways through one pattern's alternations that `_flattenings` keeps.
#: Every pattern in the tree has far fewer; the cap only stops a pathological
#: nest of alternations from multiplying the sweep's cost.
_MAX_FLATTENINGS = 16


def _flattenings(nodes: list[_Node]) -> list[list[_Node]]:
    """The pattern as flat sequences: groups opened up, one per alternative.

    A repeat inside a group, or inside the second branch of an alternation, can
    only be reached by a lead-in if the sequence in front of it is laid out flat,
    so every group is opened and every alternation becomes one sequence per
    branch (`(?:Over|Under)read` is two sequences).
    """
    ways: list[list[_Node]] = [[]]
    for node in nodes:
        op, arg = _op(node), node[1]
        if op == "SUBPATTERN" and isinstance(arg, tuple):
            options = _flattenings(list(arg[3]))
        elif op == "ATOMIC_GROUP":
            options = _flattenings(list(arg))  # type: ignore[call-overload]  # a SubPattern
        elif op == "BRANCH" and isinstance(arg, tuple):
            options = [way for branch in arg[1] for way in _flattenings(list(branch))]
        else:
            options = [[node]]
        ways = [way + option for way in ways for option in options][:_MAX_FLATTENINGS]
    return ways


def _accepts(nodes: list[_Node], char: str) -> bool:
    """Whether a repeat's body can start with ``char``, so a run of it goes in.

    Answers True for anything it cannot read (an anchor, a lookaround): a fill
    timed needlessly costs a little time, and a fill skipped wrongly is a blind
    spot.
    """
    if not nodes:
        return True
    op, arg = _op(nodes[0]), nodes[0][1]
    if op == "LITERAL":
        return arg == ord(char)
    if op == "NOT_LITERAL":
        return arg != ord(char)
    if op == "ANY":
        return char != "\n"
    if op == "IN" and isinstance(arg, list):
        return _in_class(char, arg)
    if op == "SUBPATTERN" and isinstance(arg, tuple):
        return _accepts(list(arg[3]), char)
    if op == "BRANCH" and isinstance(arg, tuple):
        return any(_accepts(list(branch), char) for branch in arg[1])
    if op in _REPEATS and isinstance(arg, tuple):
        return _accepts(list(arg[2]), char)
    return True


def _lead_in_shapes(pattern: str) -> list[Shape]:
    """Every input that starts a run INSIDE the pattern, at one of its repeats.

    For each repeat that can hold a run (its count varies, and its maximum is at
    least ``_SMALL``, the shorter run timed), two lead-ins: the shortest text in
    front of the repeat, which puts the run where the repeat starts, and the same
    plus one character the repeat accepts, which puts it inside, where a lazy
    `.+?` behind a greedy `\\s+` is (``Album: a``). Each is timed with every fill
    the repeat accepts (a run of a character it refuses never goes in) and each
    tail. A bounded repeat too short to hold a run is skipped: the run passes it
    and is timed at the next repeat, by that repeat's own lead-in. Empty lead-ins
    are left out, because the fill-only shapes already time them.
    """
    try:
        ways = _flattenings(list(_sre_parser.parse(pattern)))
    except re.error:  # pragma: no cover - an invalid pattern fails where it compiles
        return []
    shapes: list[Shape] = []
    for nodes in ways:
        for index, node in enumerate(nodes):
            op, arg = _op(node), node[1]
            if not (op in _REPEATS and isinstance(arg, tuple)):
                continue
            low, high, body = int(arg[0]), int(arg[1]), list(arg[2])
            if low == high or high < _SMALL:
                continue
            before = _witness(nodes[:index])
            fills = [fill for fill in _FILLS if _accepts(body, fill)]
            for lead in (before, before + _witness(body)):
                for fill in fills:
                    for tail in _TAILS:
                        shape = (lead, fill, tail)
                        if lead and shape not in shapes:
                            shapes.append(shape)
    return shapes


def _lead_ins(pattern: str) -> list[str]:
    """The distinct lead-ins of a pattern's shapes, in order."""
    return list(dict.fromkeys(lead for lead, _fill, _tail in _lead_in_shapes(pattern)))


#: How many times the detector proof below may measure one side before it
#: concludes. The sweep calls a pattern super-linear only when it is slow twice;
#: the proof holds its own two answers to the same standard. Noise can only make a
#: timing LONGER, so a broken clock or a wrong threshold still fails every attempt,
#: and only a spike on one attempt is forgiven. Added 2026-09-27 after the proof
#: failed once in about six parallel runs and passed 8 of 8 when re-run under load.
_PROOF_ATTEMPTS = 3


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
    pattern: str, shape: Shape, how: str, first_large_s: float
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
    base = _seconds_per_search(compiled, _text(shape, _LARGE), how=how)
    bigger = _seconds_per_search(
        compiled, _text(shape, _LARGE * 4), enough_s=0.25, how=how
    )
    ratio = bigger / max(base, 1e-12)
    return ratio > _MAX_GROWTH, ratio, bigger


def _fill_only_shapes(_pattern: str) -> Sequence[Shape]:
    """The original inputs, the same for every pattern."""
    return _FILL_ONLY


def _assert_every_pattern_is_roughly_linear(
    patterns: list[tuple[str, str, str]],
    *,
    floor: int,
    where: tuple[str, ...],
    shapes_for: Callable[[str], Sequence[Shape]] = _fill_only_shapes,
    timed_floor: int | None = None,
    rounds: int = _TIMING_ROUNDS,
) -> None:
    """Time every pattern; re-measure anything that looks super-linear.

    The re-measurement is not politeness, it is what makes this usable in CI: a
    single timing can be wrecked by the scheduler, and a check that cries wolf
    gets deleted — which would be worse than not having it.

    ``where`` is the repo-relative prefixes the patterns must come from. The floor
    counts only patterns found there, and a pattern from anywhere else fails:
    with two sweeps sharing this helper, a tooling sweep handed the package's
    patterns would otherwise clear its floor on the wrong population and pass.

    ``shapes_for`` gives each pattern's inputs: the fill-only runs by default, or
    its lead-ins. A pattern with no lead-in (no repeat whose count can vary) has
    nothing to time behind one, so for the lead-in sweeps ``timed_floor`` is the
    floor on how many patterns DID have inputs, and every one of those must have
    been timed.
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

    suspects: list[tuple[str, str, str, float, Shape, float]] = []
    measured = 0
    with_inputs = 0
    for location, pattern, how in patterns:
        shapes = shapes_for(pattern)
        if not shapes:
            continue
        with_inputs += 1
        ratio, shape, large_s = _worst_growth(
            pattern, how=how, shapes=shapes, rounds=rounds
        )
        if ratio > 0.0:
            measured += 1
        if ratio > _MAX_GROWTH:
            suspects.append((location, pattern, how, ratio, shape, large_s))

    # The floor that matters. Counting *collected* patterns above only proves the
    # `ast` walk still works; it says nothing about whether any of them were
    # timed, and the first version of this sweep collected 90 and timed 2 — every
    # other pattern fell under the noise floor and was silently skipped, so the
    # check reported a clean sweep after examining 2% of it. Repetition (see
    # `_seconds_per_search`) is what closed that, and this is the assertion that
    # keeps it closed: a skip is now a failure, not a shrug.
    needed = len(patterns) if timed_floor is None else timed_floor
    assert with_inputs >= needed, (
        f"only {with_inputs} of {len(patterns)} patterns had any input to time "
        f"(floor {needed}), so this sweep is passing by not looking"
    )
    assert measured == with_inputs, (
        f"timed only {measured} of {with_inputs} patterns — the rest produced no "
        "usable measurement, so this sweep is passing by not looking"
    )

    # Confirm each suspect at a larger input pair. Only a pattern that is also
    # super-linear there is a finding (see `_confirm_at_scale` for why the same
    # sizes twice was not a second witness).
    confirmed: list[str] = []
    for location, pattern, how, first_ratio, shape, first_large_s in suspects:
        is_real, second_ratio, second_s = _confirm_at_scale(
            pattern, shape, how, first_large_s
        )
        if is_real:
            lead, fill, tail = shape
            confirmed.append(
                f"{location}\n"
                f"    pattern: {pattern!r}, timed by .{how}\n"
                f"    on {lead!r} + a run of {fill!r} + {tail!r}, a 4x longer run "
                f"cost {first_ratio:.1f}x more at {_SMALL}->{_LARGE} chars, then "
                f"{second_ratio:.1f}x at {_LARGE}->{_LARGE * 4} "
                f"({second_s * 1000:.2f} ms)"
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


#: DEBT LEDGER — patterns the lead-in sweeps below find super-linear and that are
#: not fixed yet: (file, the pattern's exact text) -> why it can wait and where
#: it is tracked. **May shrink, never grow.** Keyed by the text rather than a line
#: number, so a fix (which changes the text) leaves the entry matching nothing,
#: and `test_every_lead_in_debt_entry_still_names_a_real_pattern` then asks for it
#: to be removed. Ledgered patterns are not timed: they are known slow, and one of
#: them takes seconds per input.
_LEAD_IN_DEBT: dict[tuple[str, str], str] = {
    (
        "src/platterpus/parsers/drive_list.py",
        r"^drive:\s*(?P<device>\S+),\s*"
        r"vendor:\s*(?P<vendor>.+?),\s*"
        r"model:\s*(?P<model>.+?),\s*"
        r"release:\s*(?P<release>\S+)\s*$",
    ): (
        "the legacy ripper's drive-list format, and `parse_drive_list` has no "
        "caller outside tests (the cyanrip backend enumerates /dev/sr* itself). "
        "320 ms on `drive:a,vendor:` and 2,000 spaces (2026-10-06). The lazy "
        "vendor and model cells may contain commas, so a greedy rewrite is not "
        "the one-line change the others were. TASKS: the lead-in debt row."
    ),
    (
        "scripts/emit_ripper_inventory.py",
        r"^\|\s*`(?P<site>[^`]+)`\s*\|\s*`(?P<text>.*)`\s*\|"
        r"\s*(?P<evidence>[^|]+?)\s*\|\s*(?P<logfile>[^|]+?)\s*\|\s*$",
    ): (
        "a maintainer tool, run by hand when a round ships a provider contract, "
        "over the rows of the fork's committed table. Cubic, not quadratic: "
        "3.7 s on one 2,000-character row of blanks (2026-10-06). Two lazy cells "
        "and a greedy one between pipes need their own equivalence proof. "
        "TASKS: the lead-in debt row."
    ),
    (
        "scripts/round_digest.py",
        r"^round-0*(?P<round>\d+)-lap-0*(?P<lap>\d+)\.md$",
    ): (
        "matched against file names only (`path.name`), which NAME_MAX bounds "
        "at 255 bytes: 0.3 ms at 255 characters, 19 ms at 2,000 (2026-10-06). "
        "TASKS: the lead-in debt row."
    ),
}


def _not_ledgered(patterns: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """The patterns minus the lead-in debt ledger's entries."""
    return [
        (location, pattern, how)
        for location, pattern, how in patterns
        if (location.rsplit(":", 1)[0], pattern) not in _LEAD_IN_DEBT
    ]


#: Floors on how many patterns had at least one lead-in when these sweeps were
#: written (2026-10-06): 133 of 174 in the package, 67 of 89 in the tooling.
#: About half, as for the floors above.
_MIN_SRC_LEAD_IN_PATTERNS = 66
_MIN_TOOLING_LEAD_IN_PATTERNS = 33


def test_every_compiled_regex_in_src_is_roughly_linear_behind_its_lead_ins() -> None:
    """The package's patterns again, on runs that start INSIDE each pattern.

    The sweep above feeds runs of one character, which never get past a literal
    label such as ``Read stalls:``; eight `parsers/cyanrip_log.py` patterns were
    quadratic behind theirs and passed it (2026-10-05). These inputs are derived
    from each pattern by `_lead_ins`. One timing round per size (``rounds=1``)
    keeps the cost near the original sweep's; a flagged pattern is re-measured
    with all three before anything fails. A separate test, so ``-n auto`` runs it
    beside the others.
    """
    _assert_every_pattern_is_roughly_linear(
        _not_ledgered(_compiled_patterns()),
        floor=40,
        where=("src/platterpus/",),
        shapes_for=_lead_in_shapes,
        timed_floor=_MIN_SRC_LEAD_IN_PATTERNS,
        rounds=1,
    )


def test_every_compiled_regex_in_the_tooling_is_roughly_linear_behind_its_lead_ins() -> (
    None
):
    """``scripts/`` and ``build/`` on the same lead-in inputs."""
    _assert_every_pattern_is_roughly_linear(
        _not_ledgered(_compiled_patterns(maintained_tooling_modules(_REPO_ROOT))),
        floor=_MIN_TOOLING_PATTERNS,
        where=("scripts/", "build/"),
        shapes_for=_lead_in_shapes,
        timed_floor=_MIN_TOOLING_LEAD_IN_PATTERNS,
        rounds=1,
    )


def test_every_lead_in_debt_entry_still_names_a_real_pattern() -> None:
    """The ledger in both directions: no entry outlives its pattern.

    A fixed pattern no longer has its old text, so its entry matches nothing and
    fails here; that is how the ledger shrinks. The other direction, a new slow
    pattern, is the sweeps' own job: anything not ledgered is timed.
    """
    population = sorted(_SRC.rglob("*.py")) + maintained_tooling_modules(_REPO_ROOT)
    present = {
        (location.rsplit(":", 1)[0], pattern)
        for location, pattern, _how in _compiled_patterns(population)
    }
    stale = sorted(
        f"{rel}: {pattern!r}"
        for rel, pattern in _LEAD_IN_DEBT
        if (rel, pattern) not in present
    )
    assert not stale, (
        "these _LEAD_IN_DEBT entries match no pattern in the tree; if the pattern "
        "was fixed, remove its entry:\n  " + "\n  ".join(stale)
    )


#: `parsers/cyanrip_log._READ_STALLS` as it was until 2026-10-06, the pattern that
#: found the blind spot: quadratic behind its label, linear on runs alone.
_OLD_READ_STALLS = r"^Read stalls:\s+(?P<value>\S.*?)\s*$"


def test_the_lead_ins_reach_inside_a_label_and_every_alternative() -> None:
    """What `_lead_ins` derives, pinned on shapes whose answers are known.

    The label's value (`Read stalls: a`), the second branch of an alternation
    (`Underread mode: a`, reachable only because each branch is laid out), and
    nothing at all for a pattern with no repeat that can hold a run, including a
    bounded one too short to (`\\d{1,4}`).
    """
    assert "Read stalls: a" in _lead_ins(_OLD_READ_STALLS)
    alternation = _lead_ins(r"^(?:Over|Under)read mode:\s+(?P<mode>.+?)\s*$")
    assert {"Overread mode: a", "Underread mode: a"} <= set(alternation), alternation
    assert _lead_ins(r"^abc$") == []
    assert _lead_ins(r"^Track (?P<n>\d{1,4})$") == []
    # A run is only timed where the repeat accepts it: `\s+` takes the blank
    # fills and refuses the digit.
    fills = {fill for _lead, fill, _tail in _lead_in_shapes(r"^Key:\s+x$")}
    assert fills == {" ", "\t"}, fills


def test_the_lead_in_shapes_catch_what_runs_of_one_character_cannot() -> None:
    """The extension detects, on both sides, and the old shapes do not.

    The old `_READ_STALLS` must read as linear to the fill-only shapes (the blind
    spot this closed, stated so a later change to them cannot silently make this
    test redundant) and as super-linear behind its lead-ins; the greedy form
    that replaced it must read as linear behind the same lead-ins. Each side
    settles over up to three attempts, as the detector proof above does.
    """
    blind = _settled(
        lambda: _worst_growth(_OLD_READ_STALLS),
        lambda ratio: ratio <= _MAX_GROWTH,
    )
    assert blind[-1][0] <= _MAX_GROWTH, (
        f"the fill-only shapes measured the old _READ_STALLS at {_series(blind)}; "
        "they were blind to it, so this proof no longer shows what the lead-ins add"
    )
    caught = _settled(
        lambda: _worst_growth(
            _OLD_READ_STALLS,
            stop_above=_MAX_GROWTH,
            shapes=_lead_in_shapes(_OLD_READ_STALLS),
        ),
        lambda ratio: ratio > _MAX_GROWTH,
    )
    assert caught[-1][0] > _MAX_GROWTH, (
        f"behind its lead-ins the old _READ_STALLS measured only {_series(caught)}, "
        "so the lead-in sweeps would pass the pattern they were written for"
    )
    greedy = r"^Read stalls:\s+(?P<value>\S(?:.*\S)?)\s*$"
    fixed = _settled(
        lambda: _worst_growth(greedy, shapes=_lead_in_shapes(greedy)),
        lambda ratio: ratio <= _MAX_GROWTH,
    )
    assert fixed[-1][0] <= _MAX_GROWTH, (
        f"the greedy _READ_STALLS measured {_series(fixed)} behind its lead-ins, "
        "so the lead-in sweeps would cry wolf on the fix"
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
            pattern, _SPACES, "search", first_large_s
        )
        verdicts.append(is_real)
        return ratio, _SPACES, seconds

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
    is_real, _, seconds = _confirm_at_scale("(", _SPACES, "search", _STALL_S)
    assert is_real and seconds == _STALL_S


def test_a_spike_on_one_attempt_is_forgiven_and_a_real_failure_is_not() -> None:
    """The re-measure forgives noise and nothing else, shown with stand-ins.

    Noise only lengthens a timing, so one bad attempt followed by a good one is
    noise. A measurement that is bad every time is a real finding, and it must
    still fail after every attempt has been spent.
    """
    noisy = iter([(10.9, _ZEROS, 0.001), (3.8, _ZEROS, 0.001)])
    attempts = _settled(lambda: next(noisy), lambda ratio: ratio <= _MAX_GROWTH)
    assert [a[0] for a in attempts] == [10.9, 3.8]

    always_bad = _settled(
        lambda: (10.9, _ZEROS, 0.001), lambda ratio: ratio <= _MAX_GROWTH
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
# are fixed and pinned by name below. The sweep's blind spot was closed on
# 2026-10-06 by the lead-in shapes above, and what they found is pinned here too
# (the twenty-one in `parsers/cyanrip_log.py` are pinned in their own file,
# `tests/test_cyanrip_log_reads_values_greedily.py`).


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
#: Each line is long enough that its old form took at least 0.7 s on it (measured
#: 2026-10-06; `_CYANRIP_ETA_VALUE` 1.6 s on its 8,000 spaces), so a revert fails
#: the 50 ms bound below by a wide margin.
_PREFIXED_OFFENDERS: list[tuple[str, str, str]] = [
    ("scripts/bommap/reading.py", "_REQUIREMENT", "a b" + " " * 20_000 + "c"),
    ("scripts/handshake.py", "_WIRE_FIELD", "KEY: x" + " " * 20_000 + "y"),
    ("src/platterpus/cue_validate.py", "_RE_REM", "REM a" + " " * 12_000),
    ("src/platterpus/cue_validate.py", "_RE_TITLE", "TITLE" + " " * 12_000),
    ("src/platterpus/cue_validate.py", "_RE_PERFORMER", "PERFORMER" + " " * 12_000),
    ("src/platterpus/parsers/rip_log.py", "_FIELD", " a:a" + " " * 16_000 + "x"),
    (
        "src/platterpus/workers/rip_worker.py",
        "_CYANRIP_ETA_VALUE",
        "0h" + " " * 8_000 + "x",
    ),
    ("scripts/handshake.py", "_SOURCE_NAMED_LAP", "round-" + "0" * 30_000 + "x"),
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

    20,000 spaces cost the first two old patterns about 2 s (0.36 s at 8,000,
    growing 4x per doubling), and every line in the table costs its old form at
    least 0.7 s; the fixed forms take microseconds. 50 ms is far from both.
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


#: Requirement-shaped lines, built from the parts the pattern branches on, mixed
#: with free text over the same characters. Free text alone almost never forms a
#: name, a spec and a trailing blank in one line, so a strategy of only that
#: compared two misses most of the time and proved little.
_REQUIREMENT_LINES = st.one_of(
    st.builds(
        lambda lead, name, extras, gap, spec, tail: (
            f"{lead}{name}{extras}{gap}{spec}{tail}"
        ),
        st.text(alphabet=" \t", max_size=2),
        st.from_regex(r"[A-Za-z0-9][A-Za-z0-9._-]{0,5}", fullmatch=True),
        st.sampled_from(["", "[x]", "[a,b]", "[", "]"]),
        st.text(alphabet=" \t", max_size=3),
        st.text(alphabet="=<>,.0 \t\r\x0ca", max_size=12),
        st.text(alphabet=" \t\r\n\x0c", max_size=3),
    ),
    st.text(alphabet="aZ0._-[]= <,\t\n\r", max_size=40),
)


@settings(max_examples=400)
@given(_REQUIREMENT_LINES)
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


#: The pattern `handshake._WIRE_FIELD` replaced: the wire-header parser every
#: lap, ours and the fork's, goes through. Kept as the reference its rewrite must
#: agree with on every input, because a parser of the shared protocol may change
#: its speed and nothing else.
_OLD_WIRE_FIELD = r"^(?P<key>[A-Z][A-Z0-9-]*):[ \t]*(?P<value>\S.*?)[ \t]*$"


def _finditer_shape(pattern: re.Pattern[str], text: str) -> list[tuple[object, ...]]:
    return [(m.span(), m.groupdict()) for m in pattern.finditer(text)]


#: Lap-shaped text: header-field lines built from the parts the pattern branches
#: on (a key, blanks, a value with blanks and kept whitespace inside and after
#: it), mixed with free lines, joined by newlines. Free text alone rarely puts a
#: key, a colon and a value at the start of a line, so it cannot carry the proof.
_WIRE_LINES = st.lists(
    st.one_of(
        st.builds(
            lambda key, gap, value, tail: f"{key}:{gap}{value}{tail}",
            st.from_regex(r"[A-Z][A-Z0-9-]{0,6}", fullmatch=True),
            st.text(alphabet=" \t", max_size=3),
            st.text(alphabet="x \t\r\x0c`*:-", max_size=12),
            st.text(alphabet=" \t\r\x0c", max_size=3),
        ),
        st.text(alphabet="KEY-0:x \t\r\x0c`*", max_size=20),
    ),
    max_size=6,
).map("\n".join)


@settings(max_examples=400)
@given(_WIRE_LINES)
def test_the_rewritten_wire_field_pattern_reads_what_the_old_one_read(
    text: str,
) -> None:
    """Every match, span and group identical, as `_parse_wire_fields` iterates them.

    The alphabet holds a key's characters, the colon, a value character, every
    blank the two patterns treat differently (space and tab are stripped; carriage
    return and form feed are kept as part of the value), the newline that ends a
    field, and two markdown characters a lap puts around a value.
    """
    old = re.compile(_OLD_WIRE_FIELD, re.MULTILINE)
    new = _pattern_assigned_to("scripts/handshake.py", "_WIRE_FIELD")
    assert _finditer_shape(new, text) == _finditer_shape(old, text)


def test_the_wire_field_rewrite_agrees_on_the_lines_laps_carry() -> None:
    """The equivalence above, on real header shapes, with a floor on fields read."""
    old = re.compile(_OLD_WIRE_FIELD, re.MULTILINE)
    new = _pattern_assigned_to("scripts/handshake.py", "_WIRE_FIELD")
    text = (
        "HANDSHAKE-PROTOCOL: 6\n"
        "HANDSHAKE-VERDICT:   GO  \n"
        "HANDSHAKE-FROM: platterpus@abc123\t\n"
        "HANDSHAKE-READY-TO-READ: no\r\n"
        "NOTE: two  spaces inside   stay\n"
        "EMPTY:   \n"
        "lowercase: not a field\n"
        "> QUOTED: not at column 0\n"
        "KEY: x" + " " * 50 + "y\n"
    )
    old_fields = _finditer_shape(old, text)
    assert _finditer_shape(new, text) == old_fields
    assert len(old_fields) >= 6, f"too few fields read: {old_fields}"

    # And on the whole committed record: every lap either side has filed. 330
    # files and 7,720 fields on 2026-10-05, every one identical; the floors are
    # well under that so the record can be reorganised without failing this.
    files = sorted((_REPO_ROOT / "docs" / "handshake").rglob("*.md"))
    differing: list[str] = []
    fields = 0
    for path in files:
        lap = path.read_text(encoding="utf-8")
        before = _finditer_shape(old, lap)
        fields += len(before)
        if _finditer_shape(new, lap) != before:
            differing.append(path.relative_to(_REPO_ROOT).as_posix())
    assert len(files) >= 100 and fields >= 2000, (len(files), fields)
    assert not differing, f"the rewrite reads these laps differently: {differing}"


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
