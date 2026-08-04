#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compare rip logs against the EAC baseline by per-track Copy CRC.

EAC is the project's bit-perfect baseline (``output_reference/``,
``docs/test-plan.md``). A rip is byte-identical to EAC's when every track's Copy
CRC matches. This is the "proof it's working" tool: rip the baseline disc with a
backend, run this against EAC's log, and — if it passes — commit the backend's
log under ``output_reference/<backend>_<format>/``.

    python3 scripts/eac_parity.py \\
        output_reference/EAC_flac/eac_baseline_police_classics.log \\
        ~/Music/rips/whipper/Album/Album.log [more candidates ...]

The log format (EAC / whipper / cyanrip) is auto-detected per file. Prints a
per-track PASS/FAIL table for each candidate and exits non-zero if any candidate
isn't bit-perfect parity (so it's usable in CI / a release gate).

Run from a checkout with the package importable (``pip install -e .`` or
``PYTHONPATH=src``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from platterpus import rip_addendum
from platterpus.parity import ParityReport, compare_logs, decode_log_bytes


def _addendum_applies(candidate: Path) -> bool:
    """Whether an auto-fix addendum sits beside this log. Never raises."""
    try:
        return rip_addendum.addendum_path_for(candidate).is_file()
    except OSError:
        return False


def _candidate_text(candidate: Path) -> str:
    """A rip log's text **with its auto-fix addendum applied**.

    **REGRESSION, and it produced a wrong answer to the project's headline question.**
    This used to be a bare ``decode_log_bytes(candidate.read_bytes())``, which reads the
    ripper's log verbatim — and when Platterpus re-rips a track that missed AccurateRip
    and swaps the better read in, the ripper's log still records the **discarded** pass.
    The addendum is what says which CRC describes the file on disk.

    Measured on the 2026-08-04 rig rip of the EAC baseline disc: this script reported
    **13/14 — NOT parity**, naming track 5's candidate CRC as ``6902BCF0`` (the discarded
    read) against EAC's ``E0036697``. The file on disk *is* ``E0036697``; the rip was
    **14/14**. A false negative on the one number that answers "is Platterpus
    bit-perfect?", from Platterpus's own tool.

    `rip_addendum` already existed for exactly this, and `read_log_with_addendum` is
    documented as the only sanctioned way to read a rip log back — enforced by a sweep in
    `tests/test_rip_addendum.py`. **The sweep globs `src/platterpus/**.py` and this file
    is in `scripts/`**, so the rule was enforced everywhere it was learned and nowhere
    else. That gap is now closed at both ends: here, and in the sweep's scope.

    UTF-16 still has to work — the *baseline* is an EAC log — so the decode stays for a
    log with no addendum beside it.
    """
    return rip_addendum.read_any_log(candidate)


def _print_report(baseline: Path, candidate: Path, report: ParityReport) -> None:
    print(f"\n{candidate}  vs  {baseline}")
    if not report.tracks:
        print("  ! no per-track Copy CRCs in the baseline — nothing to compare")
        return
    for t in report.tracks:
        mark = "PASS" if t.ok else "FAIL"
        shown = t.candidate_crc or "(missing)"
        print(
            f"  Track {t.number:>2}: {mark}  "
            f"baseline {t.baseline_crc}  candidate {shown}"
        )
    for n in report.extra:
        print(f"  Track {n:>2}: EXTRA  (in candidate, not in the baseline)")
    verdict = "PARITY ✓" if report.ok else "NOT parity ✗"
    print(f"  → {report.matched}/{report.total} tracks match — {verdict}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare rip logs to an EAC baseline by per-track Copy CRC."
    )
    parser.add_argument(
        "baseline", type=Path, help="the EAC (or reference) baseline log"
    )
    parser.add_argument(
        "candidate", type=Path, nargs="+", help="candidate rip log(s) to check"
    )
    args = parser.parse_args(argv)

    try:
        # Read bytes + sniff the encoding: EAC logs are UTF-16, whipper/cyanrip
        # are UTF-8. Reading a real EAC log as UTF-8 would yield zero CRCs.
        baseline_text = decode_log_bytes(args.baseline.read_bytes())
    except OSError as exc:
        print(f"cannot read baseline {args.baseline}: {exc}", file=sys.stderr)
        return 2

    all_ok = True
    for candidate in args.candidate:
        # Same reason as the other two scripts: `read_any_log` never raises, so the
        # unreadable case has to be checked, not caught.
        if not candidate.is_file():
            print(f"cannot read {candidate}: not a readable file", file=sys.stderr)
            all_ok = False
            continue
        candidate_text = _candidate_text(candidate)
        if not candidate_text.strip():
            print(f"{candidate} is empty or unreadable", file=sys.stderr)
            all_ok = False
            continue
        report = compare_logs(baseline_text, candidate_text)
        all_ok = all_ok and report.ok
        _print_report(args.baseline, candidate, report)
        if _addendum_applies(candidate):
            print(
                f"  (an auto-fix addendum was applied: "
                f"{rip_addendum.addendum_path_for(candidate).name})"
            )

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
