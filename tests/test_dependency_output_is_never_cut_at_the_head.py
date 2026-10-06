"""No captured tool output, and no value quoted into a log record, is cut at the head alone.

**The defect, measured.** Round 30's closing run (2026-10-06) saved
``cd-paranoia -A``'s output to the run folder so the 137-sector figure in the
transcript could be checked. The file was exactly 2,000 bytes. The adapter kept
``text.strip()[:2000]``, cd-paranoia prints its seek timings first and its cache
verdict last, so the saved text stopped inside the timings and never reached
the figure it was the evidence for. Nothing said so: the file looked complete.

The rule it broke is CLAUDE.md's *diagnostic completeness* convention: where
output must be bounded, keep the head AND the tail and mark any elision with a
count, because *a silent truncation reads as completeness*. The fix was one
line. The rule is enforced here across the codebase rather than at the place it
was learned (``docs/testing.md`` §5.o), and fourteen more head-only cuts were
fixed with it, every one of them now bounded by
:func:`platterpus.diagnostics.bounded_chars` or ``bounded_output``.

**The population, and what it is NOT.** A head-only slice ``x[:N]`` is refused
in two places, where it is a cut of something a dependency said:

* the value of a ``raw_output=`` keyword (the field every probe result uses for
  what the tool printed), and
* anywhere inside the arguments of a ``log.<level>(...)`` call.

A slice elsewhere is not judged: ``raw[:256]`` sniffing a byte-order mark, or a
label cut to fit a table cell, is not a truncated capture. That boundary is a
SCOPE, stated here rather than left silent, and the floor below keeps the
population it does cover from going quietly empty.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
from typing import Final

SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"

_LOG_METHODS: Final[frozenset[str]] = frozenset(
    {"debug", "info", "warning", "error", "exception", "critical"}
)
_LOGGER_NAMES: Final[frozenset[str]] = frozenset(
    {"log", "logger", "logging", "_log", "_logger", "LOG"}
)

#: Floors on the population, measured 2026-10-06: 10 ``raw_output=`` keywords and
#: 725 logging calls. Well under both, so ordinary refactoring does not trip
#: them, and far above zero, so a broken walk cannot pass by finding nothing.
_MIN_RAW_OUTPUT_SITES: Final[int] = 8
_MIN_LOG_CALLS: Final[int] = 500

#: Head-only slices that are allowed to stay, each with the reason. Keyed by
#: (module, the slice's source text) with a count, not a line number, so an
#: unrelated edit does not churn it. A TWO-WAY ratchet: a new site fails, and an
#: entry that no longer matches fails too, so the list can only shrink.
_ALLOWED: Final[dict[tuple[str, str], tuple[int, str]]] = {
    ("drive_control.py", "argv[:1]"): (
        2,
        "a LIST head: the program name of the command being skipped, not a "
        "cut of anything the program printed.",
    ),
    ("rip_files.py", "excluded[:10]"): (
        1,
        "a list of file NAMES, already marked ', …' and counted by the "
        "`len(excluded)` argument beside it.",
    ),
    ("rip_files.py", "missing[:10]"): (
        1,
        "a list of file NAMES, already marked ', …' and counted by the "
        "`len(missing)` argument beside it.",
    ),
}


def _is_head_only_slice(node: ast.AST) -> bool:
    """``x[:N]``: an upper bound and nothing else."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Slice)
        and node.slice.lower is None
        and node.slice.upper is not None
        and node.slice.step is None
    )


def _is_log_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in _LOG_METHODS
        and isinstance(func.value, ast.Name)
        and func.value.id in _LOGGER_NAMES
    )


def _scan(tree: ast.AST) -> tuple[int, int, list[tuple[int, str]]]:
    """(raw_output sites, log calls, head-only cuts found) for one module."""
    raw_sites = 0
    log_calls = 0
    cuts: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "raw_output":
                raw_sites += 1
                if _is_head_only_slice(keyword.value):
                    cuts.append((node.lineno, ast.unparse(keyword.value)))
        if _is_log_call(node):
            log_calls += 1
            for argument in node.args:
                for inner in ast.walk(argument):
                    if _is_head_only_slice(inner):
                        cuts.append((node.lineno, ast.unparse(inner)))
    return raw_sites, log_calls, cuts


def _sweep() -> tuple[int, int, dict[tuple[str, str], list[int]]]:
    raw_total = 0
    log_total = 0
    found: dict[tuple[str, str], list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        raw_sites, log_calls, cuts = _scan(ast.parse(path.read_text("utf-8")))
        raw_total += raw_sites
        log_total += log_calls
        for line, text in cuts:
            found.setdefault((rel, text), []).append(line)
    return raw_total, log_total, found


def test_the_sweep_examines_a_real_population() -> None:
    """Can this check be satisfied by finding nothing? Not with a floor."""
    raw_total, log_total, _found = _sweep()
    assert raw_total >= _MIN_RAW_OUTPUT_SITES, raw_total
    assert log_total >= _MIN_LOG_CALLS, log_total


def test_no_captured_output_is_cut_at_the_head_alone() -> None:
    _raw, _log, found = _sweep()
    refused = [
        f"{rel}:{lines[0]}: `{text}` x{len(lines)}"
        for (rel, text), lines in sorted(found.items())
        if len(lines) > _ALLOWED.get((rel, text), (0, ""))[0]
    ]
    assert not refused, (
        "a head-only cut of dependency output drops the END, which is where a "
        "tool says what went wrong (and where cd-paranoia prints its verdict). "
        "Use `diagnostics.bounded_chars(text, head=, tail=)` for one line or "
        "`diagnostics.bounded_output(text)` for many:\n  " + "\n  ".join(refused)
    )


def test_every_allowance_still_matches_what_it_excuses() -> None:
    """The other half of the ratchet: a fixed site must leave the list."""
    _raw, _log, found = _sweep()
    counts = Counter({key: len(lines) for key, lines in found.items()})
    stale = [
        f"{rel}: `{text}` allows {allowed}, found {counts.get((rel, text), 0)}"
        for (rel, text), (allowed, _why) in _ALLOWED.items()
        if counts.get((rel, text), 0) != allowed
    ]
    assert not stale, "shrink the allowance to what is there:\n  " + "\n  ".join(stale)


def test_the_detector_sees_both_shapes_it_refuses() -> None:
    """The detector itself, on planted code: a pass must mean it looked."""
    planted = ast.parse(
        "def f(output, text):\n"
        "    log.warning('x %r', text[:80])\n"
        "    log.info('y %r', bounded(text))\n"
        "    return Result(raw_output=output[:2000])\n"
    )
    raw_sites, log_calls, cuts = _scan(planted)
    assert (raw_sites, log_calls) == (1, 2)
    assert [text for _line, text in cuts] == ["text[:80]", "output[:2000]"]
