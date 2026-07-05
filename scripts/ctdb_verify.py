#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Standalone CTDB verify — the hardware-validation vehicle for KDD-16.

Run this against a folder of freshly-ripped FLACs (a disc you believe is in
CTDB) to exercise the whole verify path WITHOUT the GUI:

    python3 scripts/ctdb_verify.py ~/Music/rips/Artist/Album/

It prints the disc TOC, the exact lookup URL, the database verdict, and (if
`flac` is installed) our computed CRC vs. the database CRCs. Use it to confirm
— or correct — the wire format and the CRC algorithm (see docs/test-plan.md,
Test 1).

The actual logic lives in :mod:`platterpus.ctdb.diagnose` so the shipped app can
expose the exact same thing as ``platterpus --ctdb-calibrate <folder>`` (runs
from the AppImage, no dev checkout needed). This script is the dev-checkout
front-end to it.

This script imports the project package, so run it from a checkout with the
package importable (e.g. `pip install -e .` or `PYTHONPATH=src`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from platterpus.ctdb.diagnose import run_diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a rip against CTDB.")
    parser.add_argument(
        "folder", type=Path, help="folder containing the ripped .flac files"
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help=(
            "if the disc is in CTDB, sweep candidate offset-guard trims over the "
            "decoded PCM and report which one reproduces the database CRC "
            "(pins the CTDB-CRC algorithm on real hardware — KDD-16)."
        ),
    )
    args = parser.parse_args(argv)
    return run_diagnostics(args.folder, calibrate_crc=args.calibrate)


if __name__ == "__main__":
    raise SystemExit(main())
