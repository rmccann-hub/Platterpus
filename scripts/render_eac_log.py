#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Render a cyanrip/whipper rip log into an EAC-*layout* comparison log.

This produces an honest, conspicuously-attributed log that mirrors EAC's
section/per-track layout so you can ``diff``/``meld`` it against a real EAC log
and eyeball the per-track Copy CRCs — the readable companion to
``scripts/eac_parity.py``'s pass/fail table.

**It is NOT a genuine EAC log and is never signed** (see
``docs/eac-log-and-repair-feasibility.md``: signing our output as EAC is
provenance forgery). The first line and the footer say so.

    python3 scripts/render_eac_log.py ~/Music/rips/Album/Album.log
    python3 scripts/render_eac_log.py Album.log -o Album.eac-style.log

Run from a checkout with the package importable (``pip install -e .`` or
``PYTHONPATH=src``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from whipper_gui.eac_log_export import render_eac_style_log
from whipper_gui.parity import decode_log_bytes
from whipper_gui.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from whipper_gui.parsers.eac_log import looks_like_eac_log
from whipper_gui.parsers.rip_log import RipLog, parse_rip_log


def _parse_to_rip_log(text: str) -> RipLog:
    """Parse a cyanrip or whipper log into a RipLog (auto-detected)."""
    if looks_like_cyanrip_log(text):
        return parse_cyanrip_log(text)
    return parse_rip_log(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a cyanrip/whipper rip log into an EAC-layout "
        "comparison log (unsigned, clearly attributed — NOT a real EAC log)."
    )
    parser.add_argument("rip_log", type=Path, help="a cyanrip or whipper rip log")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="write here instead of stdout (UTF-8)",
    )
    args = parser.parse_args(argv)

    try:
        text = decode_log_bytes(args.rip_log.read_bytes())
    except OSError as exc:
        print(f"cannot read {args.rip_log}: {exc}", file=sys.stderr)
        return 2

    if looks_like_eac_log(text):
        print(
            f"{args.rip_log} already looks like an EAC log — nothing to render.",
            file=sys.stderr,
        )
        return 2

    rendered = render_eac_style_log(_parse_to_rip_log(text))

    if args.output is not None:
        try:
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"cannot write {args.output}: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
