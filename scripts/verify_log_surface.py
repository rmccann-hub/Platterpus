#!/usr/bin/env python3
"""Grade round 16's clause 3 the only way it can honestly be graded: with OUR parser.

## Why this exists

Round 16's close condition, fixed at lap 1 §0 under S-13, has three clauses. The
third is::

    no line you parse has moved except the ones §D names

**"You" is us.** The fork's `tools/round16-accept.py` grades all three clauses and
its exit code is the observable both sides' S-18 pre-commits now hang on — which
is right for clauses 1 and 2, because those are facts about their ripper that
their harness can measure. Clause 3 is not that kind of fact. It is a claim about
*our* reader, and a checker in their repository cannot run our reader.

Their `clause3()` does what it honestly can: it checks the `-j` record's schema
and its two instants, that every log's banner names the fork, and that two log
lines are present — `^\\s+Secure re-read:` and `^Consumer:`. That is **two of the
sixty log lines our generated consumer contract says we parse.** Not a defect on
their side; a proxy is the best a stranger to our parser can build. But a `GO`
resting on it would be a `GO` resting on a 2-of-60 sample of one third of the
condition, and neither project would want that written down.

So this closes the gap from the side that owns it. It runs the **real**
enumeration tables — the same ones `scripts/emit_dependency_contract.py` generates
the published contract from — over the logs a run actually produced, and reports
every line that is neither parsed nor knowingly ignored.

## What it will and will not tell you

It answers exactly one question: **is there a line in these logs that our parser
does not account for?** A line it cannot place is a clause-3 finding; whether that
finding blocks anything is S-14's question and a person's, not this script's.

It does **not** check that a parsed line's *value* is right, that the rip was good,
or that any line we expect is present — an absent line is a fact about the disc or
the invocation far more often than about the format, and grading absence here would
manufacture failures. `--expect` exists for the cases where a caller genuinely
knows a line must appear.

## The floors, and why a checker needs them

A sweep that examines nothing passes trivially, which is how *"0 issues"* comes to
mean *"0 files read"*. So: it refuses to report success unless it examined at least
one log and at least ``--min-lines`` lines, and it prints both counts next to the
verdict rather than only the verdict. `UNPROBED` is not a pass here either — that
rule is the fork's, from their own checker's first draft, and it is right.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:  # pragma: no cover - import plumbing
    sys.path.insert(0, str(_REPO_ROOT / "src"))

#: Default floor on lines examined. A cyanrip log for a single track is already
#: well past this; the number exists to catch an empty or truncated directory,
#: not to express an opinion about run size.
DEFAULT_MIN_LINES: Final[int] = 50

#: Lines that carry no format claim at all. Blank lines and the rule-off banners
#: cyanrip draws are not "lines we parse" in any sense, and counting them as
#: unrecognised would bury a real finding under decoration.
_STRUCTURAL: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^\s*$"),
    re.compile(r"^[=_\-]{4,}\s*$"),
)

#: OUR auto-fix addendum, when it appears INLINE in a ripper log.
#:
#: Modern rips put it in a `.platterpus-addendum.txt` sidecar — appending past
#: cyanrip's `Log FUN512:` line makes `--verify-log` reject the file, which is
#: the round-7 lap-10 H1 defect. But logs from before that change carry the block
#: inline, and `output_reference/` holds one. It is **our** text in their file, so
#: reporting it as a line "their format moved" would be this script accusing the
#: ripper of something Platterpus wrote. Recognised and counted separately rather
#: than silently dropped: a category that disappears is a category nobody audits.
_OURS_INLINE: Final[re.Pattern[str]] = re.compile(
    r"^(?:\[Platterpus auto-fix addendum\]"
    r"|The whole-disc log above records"
    r"|below didn't match AccurateRip"
    r"|swapped in\. Each CRC below"
    r"|value recorded for that track above"
    r"|\s+Track \d+ \(.*\): CRC [0-9A-Fa-f]{8})"
)

#: Filenames that are OURS, however they are spelled.
#:
#: The corpus writes `..._EACcompatible.log` and the evidence bundle writes
#: `... (EAC-compatible).log` — two spellings of one artifact, which is exactly
#: the hazard `CLAUDE.md` records under *legislate the name AND stop depending on
#: it*. So the match is on the name with separators and case removed, the same
#: move `uiscript/find_script.py` makes, rather than on either literal. Found by
#: running this script against the committed corpus on its first execution: the
#: literal `"EAC-compatible"` missed the corpus file and reported 43 lines of our
#: own EAC export as evidence that cyanrip's format had moved.
_OURS_IN_NAME: Final[tuple[str, ...]] = ("eaccompatible", "platterpusaddendum")


def _is_ours(path: Path) -> bool:
    """True for a log Platterpus wrote. Separator- and case-insensitive."""
    flat = re.sub(r"[^a-z0-9]", "", path.name.lower())
    return any(marker in flat for marker in _OURS_IN_NAME)


@dataclass
class SurfaceReport:
    """What the sweep saw. Every field is a count a reader can re-derive."""

    logs_examined: list[str] = field(default_factory=list)
    lines_examined: int = 0
    lines_parsed: int = 0
    lines_ignored: int = 0
    lines_structural: int = 0
    #: Lines Platterpus itself wrote into a ripper log (the historical inline
    #: addendum). Counted, never silently dropped.
    lines_ours: int = 0
    #: (file, line number, the line itself) for everything unaccounted for.
    unrecognised: list[tuple[str, int, str]] = field(default_factory=list)
    #: Patterns the caller said must appear and which did not.
    missing_expected: list[str] = field(default_factory=list)

    @property
    def examined_enough(self) -> bool:
        return bool(self.logs_examined) and self.lines_examined > 0


def _tables() -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    """(recognised, knowingly-ignored) patterns, read from the parser itself.

    **Not from the published markdown.** The contract page is *generated* from
    these same tables, so reading the page instead would add a copy that can go
    stale between regenerations — and the whole point of this script is to be the
    thing that cannot disagree with the parser.
    """
    from platterpus.parsers import cyanrip_log as parser

    recognised: list[re.Pattern[str]] = [
        rule.pattern for rule in parser._ALL_LINE_RULES
    ]
    recognised += [pattern for _name, pattern in parser._SECTION_LINE_PATTERNS]
    recognised += [pattern for _name, pattern in parser._INDENTED_LINE_PATTERNS]
    ignored: list[re.Pattern[str]] = [
        pattern for pattern, _reason in parser._IGNORED_DISC_LINES
    ]
    return recognised, ignored


def sweep(
    logs: Sequence[Path],
    *,
    expect: Iterable[str] = (),
) -> SurfaceReport:
    """Classify every line of every log. Never raises."""
    recognised, ignored = _tables()
    report = SurfaceReport()
    expect_patterns = [(spec, re.compile(spec, re.MULTILINE)) for spec in expect]
    seen_expected: set[str] = set()

    for path in logs:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            # An unreadable log is a fact about this machine, and it must not be
            # silently skipped — a sweep that quietly drops a file reports a
            # smaller population as a complete one.
            report.unrecognised.append((str(path), 0, f"<could not read: {exc!r}>"))
            continue
        report.logs_examined.append(str(path))
        for spec, pattern in expect_patterns:
            if pattern.search(text):
                seen_expected.add(spec)
        for number, line in enumerate(text.splitlines(), start=1):
            report.lines_examined += 1
            if any(p.match(line) for p in _STRUCTURAL):
                report.lines_structural += 1
            elif any(p.match(line) for p in recognised):
                report.lines_parsed += 1
            elif any(p.match(line) for p in ignored):
                report.lines_ignored += 1
            elif _OURS_INLINE.match(line):
                report.lines_ours += 1
            else:
                report.unrecognised.append((str(path), number, line.rstrip()))

    report.missing_expected = [s for s, _ in expect_patterns if s not in seen_expected]
    return report


def _collect(targets: Sequence[Path]) -> list[Path]:
    """Every ``.log`` under the given files/directories, sorted and de-duplicated.

    Excludes our own EAC-compatible companion, which we write: grading a file we
    author against our own parser is the closed loop the fork taught us to
    distrust (round 7 lap 10, J3), and it says nothing about whether *their*
    format moved.
    """
    found: set[Path] = set()
    for target in targets:
        if target.is_dir():
            found.update(p for p in target.rglob("*.log") if p.is_file())
        elif target.is_file():
            found.add(target)
    return sorted(p for p in found if not _is_ours(p))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Report every cyanrip log line our parser neither parses nor "
            "knowingly ignores. This is round 16 clause 3, graded by the reader "
            "the clause is about."
        )
    )
    ap.add_argument(
        "targets",
        nargs="+",
        type=Path,
        help="log files, or directories to search recursively for *.log",
    )
    ap.add_argument(
        "--min-lines",
        type=int,
        default=DEFAULT_MIN_LINES,
        help=(
            f"refuse to report success on fewer than this many lines "
            f"(default {DEFAULT_MIN_LINES}); a sweep that examined nothing is "
            f"not a sweep that found nothing"
        ),
    )
    ap.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="REGEX",
        help=(
            "a line that MUST appear somewhere in the logs; repeatable. Absence "
            "is normally a fact about the disc, so this is opt-in"
        ),
    )
    args = ap.parse_args(argv)

    logs = _collect(args.targets)
    report = sweep(logs, expect=args.expect)

    print(f"logs examined : {len(report.logs_examined)}")
    for name in report.logs_examined:
        print(f"                {name}")
    print(f"lines examined: {report.lines_examined}")
    print(
        f"  parsed {report.lines_parsed} / knowingly ignored {report.lines_ignored} "
        f"/ blank-or-rule {report.lines_structural} / ours {report.lines_ours} "
        f"/ UNACCOUNTED {len(report.unrecognised)}"
    )

    if not report.examined_enough:
        print(
            "\nUNPROBED: no log was read, so nothing was checked. This is not a "
            "pass — a clause whose evidence is absent is not a clause that "
            "passed.",
            file=sys.stderr,
        )
        return 2
    if report.lines_examined < args.min_lines:
        print(
            f"\nUNPROBED: only {report.lines_examined} line(s) examined, below the "
            f"floor of {args.min_lines}. Too small a population to report a "
            f"clean sweep from.",
            file=sys.stderr,
        )
        return 2

    if report.missing_expected:
        print("\nEXPECTED BUT ABSENT:", file=sys.stderr)
        for spec in report.missing_expected:
            print(f"  {spec}", file=sys.stderr)

    if report.unrecognised:
        print(
            f"\nCLAUSE 3 FINDING: {len(report.unrecognised)} line(s) our parser "
            f"does not account for. Each is either a format change or a line we "
            f"should be ignoring on purpose — both are ours to resolve, and "
            f"neither is decided here.",
            file=sys.stderr,
        )
        for name, number, line in report.unrecognised:
            print(f"  {name}:{number}: {line}", file=sys.stderr)

    if report.unrecognised or report.missing_expected:
        return 1
    print(
        f"\nCLAUSE 3 HOLDS on this reader: every one of {report.lines_examined} "
        f"line(s) across {len(report.logs_examined)} log(s) is either parsed or "
        f"on the knowingly-ignored list."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
