#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Standalone preflight ("doctor") — first-pass rip-environment test, no CD.

Runs every check the rip pipeline needs except the disc read itself, so you can
sanity-check a machine *before* inserting a disc: the Distrobox→cyanrip routing,
drive detection + access, the dependency tools, and host network to MusicBrainz
/ Cover Art Archive / CTDB.

    python scripts/preflight.py                  # full run
    python scripts/preflight.py --no-network     # skip the network checks
    platterpus --doctor                          # same thing, via the app

Exit code: 0 = no hard blockers (warnings may exist), 1 = a blocker was found.
The actual logic lives in ``platterpus.preflight`` (unit-tested); this is just
the CLI wrapper.
"""

from __future__ import annotations

import argparse
import sys

from platterpus import config as config_module
from platterpus import preflight


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="preflight",
        description="First-pass test of the Platterpus rip environment (no CD).",
    )
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="skip the MusicBrainz / Cover Art Archive / CTDB reachability checks",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="disable ANSI colour output"
    )
    args = parser.parse_args(argv)

    # cyanrip is the sole backend (KDD-18), so there's nothing to override — the
    # old `--backend whipper|cyanrip` flag set a Config attribute that no longer
    # exists and was never read; it was removed.
    cfg = config_module.load()
    ctx = preflight.default_context(cfg)
    color = sys.stdout.isatty() and not args.no_color

    print(f"Platterpus preflight — backend: {ctx.backend_name}\n")
    results = preflight.run_preflight(
        ctx,
        network=not args.no_network,
        on_result=lambda r: print(preflight.format_line(r, color=color)),
    )

    details = preflight.format_details(results)
    if details:
        print("\n" + details)
    print("\n" + preflight.format_summary(results, color=color))
    return preflight.exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
