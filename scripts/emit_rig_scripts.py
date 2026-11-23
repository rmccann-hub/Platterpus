#!/usr/bin/env python3
"""Write ``fullacceptance.txt`` and ``quickcheck.txt`` from their blocks.

TASKS R188: the Full acceptance run and the Quick check are cut, at their section
headers, into blocks under ``src/platterpus/rig_scripts/blocks/``, so each test
exists once and every pre-built test is an ordered list of them
(``uiscript/prebuilt.py``). The two whole files still ship, because the owner,
``--run-script fullacceptance`` and many tests read them, and they are now
**generated**: the blocks named in ``uiscript/blocks.py``'s ``GENERATED_FILES``,
joined in order, byte for byte. Edit a block, then run this.

Usage::

    python3 scripts/emit_rig_scripts.py           # rewrite the two files
    python3 scripts/emit_rig_scripts.py --check   # exit 1 if either is stale

``tests/test_prebuilt_tests.py`` runs the check, so a hand edit to a generated
file (which the next run of this script would silently undo) fails CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from platterpus.uiscript import blocks  # noqa: E402 — after the path insert
from platterpus.uiscript.find_script import packaged_scripts_dir  # noqa: E402


def rendered() -> dict[Path, str]:
    """``{file: text}`` for each generated file, from its blocks.

    Raises ``ValueError`` naming the block when one cannot be read: a generator
    that wrote a partial file would be worse than one that stopped.
    """
    out: dict[Path, str] = {}
    for name, order in blocks.GENERATED_FILES.items():
        text, problem = blocks.joined_text(order)
        if problem:
            raise ValueError(problem)
        out[packaged_scripts_dir() / name] = text
    return out


def stale() -> list[Path]:
    """The generated files whose text on disk is not their blocks joined."""
    found: list[Path] = []
    for path, text in rendered().items():
        try:
            current = path.read_text(encoding="utf-8")
        except OSError:
            current = None
        if current != text:
            found.append(path)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if stale")
    args = parser.parse_args(argv)
    try:
        if args.check:
            out_of_date = stale()
            if out_of_date:
                names = ", ".join(p.name for p in out_of_date)
                sys.stderr.write(
                    f"stale: {names}. Edit the blocks, not the file, then "
                    "regenerate with: python3 scripts/emit_rig_scripts.py\n"
                )
                return 1
            return 0
        for path, text in rendered().items():
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
    except ValueError as exc:
        sys.stderr.write(f"emit_rig_scripts: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
