"""Terminal glue for the re-rip comparison + best-of assembler.

Thin CLIs over the pure :mod:`platterpus.rip_compare` core, mirroring how
``--doctor`` wraps :mod:`platterpus.preflight` and ``--ctdb-calibrate`` wraps
:mod:`platterpus.ctdb.diagnose`: this module does the *printing* and returns a
process exit code; all the logic (and all the tests of that logic) live in
``rip_compare``. Kept out of ``app.py`` so the entry point stays thin.

Exit codes (script-friendly):

* ``--compare``: ``0`` = identical / nothing to compare, ``1`` = differences
  found, ``2`` = an argument/read error.
* ``--assemble-best-of``: ``0`` = every planned file copied, ``1`` = some files
  failed to copy, ``2`` = an argument/read/setup error.
"""

from __future__ import annotations

from pathlib import Path

from platterpus import rip_compare


def run_compare(path_a: Path, path_b: Path, *, show_plan: bool = True) -> int:
    """Print a track-by-track comparison of two ``.platterpus.json`` reports.

    ``path_a`` is treated as the earlier/"previous" rip and ``path_b`` as the
    later one, but the comparison is symmetric — the labels just say which is
    which. Returns an exit code (see module docstring)."""
    report_a = rip_compare.load_report(path_a)
    report_b = rip_compare.load_report(path_b)
    if report_a is None or report_b is None:
        missing = [
            str(p) for p, r in ((path_a, report_a), (path_b, report_b)) if r is None
        ]
        print(
            "error: could not read a rip report (missing or not valid JSON):\n  "
            + "\n  ".join(missing)
        )
        return 2

    comparison = rip_compare.compare_reports(
        report_a,
        report_b,
        label_a=f"{rip_compare.report_label(report_a, fallback='A')}  [{path_a}]",
        label_b=f"{rip_compare.report_label(report_b, fallback='B')}  [{path_b}]",
    )
    print(rip_compare.render_comparison(comparison))

    # Only offer the best-of plan/assembly when the two are the same disc —
    # `--assemble-best-of` refuses across different discs, so advertising it (and
    # printing a confident per-track "better master" plan) there would mislead.
    if show_plan and comparison.differing_count and comparison.same_disc is not False:
        print()
        plan = rip_compare.best_of_plan(comparison, report_a, report_b)
        print(rip_compare.render_best_of_plan(plan))
        print(
            "\nTo assemble the best of both into a new folder, run:\n"
            f"  --assemble-best-of <DEST> {path_a} {path_b}"
        )

    return 1 if comparison.differing_count else 0


def run_assemble_best_of(dest: Path, path_a: Path, path_b: Path) -> int:
    """Assemble a best-of-both master folder from two rips of the same disc.

    Reads both reports, plans the per-track best master, and COPIES the chosen
    files into ``dest`` (non-destructive — the two source folders are untouched).
    The source FLACs are read from beside each report. Returns an exit code."""
    report_a = rip_compare.load_report(path_a)
    report_b = rip_compare.load_report(path_b)
    if report_a is None or report_b is None:
        print("error: could not read one or both rip reports (missing / not JSON)")
        return 2

    comparison = rip_compare.compare_reports(report_a, report_b)
    if comparison.same_disc is False:
        print(
            "error: these reports are for different discs (disc IDs differ) — "
            "refusing to assemble a best-of across different discs.\n"
            f"  A disc id: {comparison.disc_key_a}\n"
            f"  B disc id: {comparison.disc_key_b}"
        )
        return 2

    plan = rip_compare.best_of_plan(comparison, report_a, report_b)
    print(rip_compare.render_best_of_plan(plan))
    print()

    result = rip_compare.assemble_best_of(
        plan,
        folder_a=Path(path_a).parent,
        folder_b=Path(path_b).parent,
        dest=dest,
    )
    if result.error is not None:
        print(f"error: {result.error}")
        return 2
    print(f"Copied {result.copied} track(s) into {result.dest}")
    if result.failures:
        print("Some files could not be copied:")
        for failure in result.failures:
            print(f"  {failure}")
        return 1
    return 0
