#!/usr/bin/env python3
"""Check a handshake lap written in LSL, the fork's lap statement language.

    python3 scripts/lap_language.py check docs/handshake/inbound/round-27-lap-06.md
    python3 scripts/lap_language.py check LAP --peer ../cyanrip --amend all

This is a second, independent implementation of LSL 1, written from the fork's
spec rather than their checker, with our proposed amendments behind `--amend`.
Why, and what each amendment is for, are in `scripts/laplang/__init__.py` and
`docs/handshake/outbound/artifacts/lsl-amendments-1.md`. This file only puts
`scripts/` on the import path and hands over, so the tests can import the
package the same way.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from laplang.cli import main  # noqa: E402 - needs the path line above

if __name__ == "__main__":
    sys.exit(main())
