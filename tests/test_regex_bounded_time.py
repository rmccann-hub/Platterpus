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
        except (OSError, SyntaxError):  # pragma: no cover - a broken file fails elsewhere
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


def _worst_growth(pattern: str) -> tuple[float, str, float]:
    """Return the worst (growth_ratio, fill, large_seconds) over the fills.

    Timed with ``.search`` because that is how these patterns are used on
    subprocess output and file rows — ``.match`` would anchor away the backtracking
    that ``.search`` has to do at every start position.
    """
    compiled = re.compile(pattern)
    worst = (0.0, "", 0.0)
    for fill in _FILLS:
        small_text = fill * _SMALL
        large_text = fill * _LARGE

        start = time.perf_counter()
        compiled.search(small_text)
        small = time.perf_counter() - start

        start = time.perf_counter()
        compiled.search(large_text)
        large = time.perf_counter() - start

        if large < _NOISE_FLOOR_S:
            continue  # too fast to say anything about
        ratio = large / max(small, 1e-9)
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
    for location, pattern in patterns:
        ratio, fill, _ = _worst_growth(pattern)
        if ratio > _MAX_GROWTH:
            suspects.append((location, pattern, ratio, fill))

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
