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
        ~/Music/rips/Album/Album.log [more candidates ...]

The log format (EAC / cyanrip / the legacy log format) is auto-detected per file.
Prints a per-track PASS/FAIL table for each candidate and exits non-zero if any
candidate isn't bit-perfect parity (so it's usable in CI / a release gate).

**The baseline must be a log somebody else wrote.** It names who wrote the
baseline, from the baseline's own first line, before any table. One of
Platterpus's OWN EAC-layout exports (``... (EAC-compatible).log``) is REFUSED as
the baseline, exit 2: it would compare our rip with our own rendering of it,
and pass. A baseline whose producer cannot be determined (a cyanrip log, say)
is compared, but the output says the match is parity with that log, not with
EAC. Our export is still welcome as a *candidate*.

Exit codes: ``0`` every candidate is at parity, ``1`` at least one is not, ``2``
an unreadable file or a refused baseline.

Run from a checkout with the package importable (``pip install -e .`` or
``PYTHONPATH=src``).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from platterpus import rip_addendum
from platterpus.parity import (
    BaselineProducer,
    ParityReport,
    compare_logs,
    decode_log_bytes,
    identify_baseline,
)

_LOG = logging.getLogger(__name__)

#: The baseline to pass instead, named in the refusal so the fix is in the message.
_EAC_BASELINE_HINT = "output_reference/EAC_flac/eac_baseline_police_classics.log"


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


def _refuse_our_own_export(baseline: Path, identity: BaselineProducer) -> int:
    """Refuse a baseline Platterpus wrote: visibly, to the log, and with exit 2.

    **REFUSE, not warn — decided by what each kind of error costs.** The thing
    being protected is the parity claim itself: a PASS here is what gets
    committed under ``output_reference/`` and ticked in ``TASKS.md`` as proof
    that a backend is bit-perfect against EAC.

    * A **false negative** (our export accepted as the baseline) prints "14/14
      PARITY ✓" and exits 0 for a comparison that cannot fail: every track of a
      rip matches our own export of that rip. A pass gets cited, not
      investigated, so a warning printed above a green verdict is the cheapest
      thing to scroll past and the costliest to miss.
    * A **false positive** (a real EAC log refused) needs its first line to begin
      with one of OUR banners, the exact strings ``eac_log_producer`` matches.
      EAC writes its own banner there, so this costs at most one re-run with
      the right file, and the message names the line that decided it.

    The costs are that lopsided, so the safe direction is the refusal. Exit 2
    is this tool's "the input is unusable" code, the same as an unreadable
    baseline, so a CI or rig step reading the status cannot take it for either
    verdict.
    """
    message = (
        f"refusing {baseline} as the baseline: it is {identity.describe()}. "
        "Comparing a rip with Platterpus's own export of it only checks our export "
        "against our own rip, so every track would match and the match would "
        "prove nothing about parity with Exact Audio Copy. Pass a log EAC wrote "
        f"as the baseline (for the reference disc, {_EAC_BASELINE_HINT}); our "
        "export is fine as a candidate."
    )
    print(message, file=sys.stderr)
    _LOG.error(
        "eac_parity: refused baseline %s: producer=platterpus, first line %r",
        baseline,
        identity.line,
    )
    return 2


def _print_baseline(baseline: Path, identity: BaselineProducer) -> None:
    """Say who wrote the baseline, once, before any table that relies on it.

    Tri-state on purpose. A baseline whose producer is not determined is still
    compared (two cyanrip rips can be checked against each other), but the
    reader is told, and the log records it, that a match against it is not
    parity with EAC.
    """
    print(f"baseline {baseline}: it is {identity.describe()}")
    if identity.producer is None:
        _LOG.warning(
            "eac_parity: baseline %s is not determined to be an EAC log "
            "(first line %r); a match is parity with that log, not with EAC",
            baseline,
            identity.line,
        )


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
    if report.ok and report.baseline.producer is None:
        # Never let an undetermined baseline read as EAC parity (tri-state).
        verdict += " with this baseline, which is NOT determined to be EAC's log"
    print(f"  → {report.matched}/{report.total} tracks match — {verdict}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare rip logs to an EAC baseline by per-track Copy CRC."
    )
    parser.add_argument(
        "baseline",
        type=Path,
        help="a log Exact Audio Copy wrote (or another rip's log, reported as not "
        "EAC's); one of Platterpus's own EAC-compatible exports is refused",
    )
    parser.add_argument(
        "candidate", type=Path, nargs="+", help="candidate rip log(s) to check"
    )
    args = parser.parse_args(argv)

    try:
        # Read bytes + sniff the encoding: EAC logs are UTF-16, cyanrip and
        # legacy-format logs are UTF-8. Reading a real EAC log as UTF-8 would
        # yield zero CRCs.
        baseline_text = decode_log_bytes(args.baseline.read_bytes())
    except OSError as exc:
        print(f"cannot read baseline {args.baseline}: {exc}", file=sys.stderr)
        return 2

    # Who wrote the baseline, asked of the one producer predicate before a single
    # candidate is compared, so a refused baseline produces no table to cite.
    identity = identify_baseline(baseline_text)
    if identity.is_ours:
        return _refuse_our_own_export(args.baseline, identity)
    _print_baseline(args.baseline, identity)

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
