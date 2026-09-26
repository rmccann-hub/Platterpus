#!/usr/bin/env python3
"""Check laps written in the lap language, and say whose turn it is.

    python3 scripts/lap_language.py check tests/fixtures/lap_language_round27_lap05.md
    python3 scripts/lap_language.py turn 27

The language, and why each rule exists, is in `scripts/laplang/__init__.py` and
the spec it implements, `docs/handshake/outbound/artifacts/lap-language-1.md`.
This file only puts `scripts/` on the import path and hands over, so the package
can be imported the same way by the tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from laplang.cli import main  # noqa: E402 - needs the path line above

if __name__ == "__main__":
    sys.exit(main())
