#!/usr/bin/env python3
"""`HANDSHAKE-ROUND-DIGEST` — protocol v3 §5a, implemented from the spec text.

**Written independently of cyanrip's `tools/round-digest.py`, deliberately.** The
spec fixes the construction precisely so two implementations can be *compared*;
copying theirs would produce agreement that proves nothing, which is the
"my two witnesses are related" failure both projects keep writing rules against.
If the two numbers differ over the same set of laps, one of us has misread the
spec and that is worth more than a matching number.

The construction, §5a verbatim:

1. ``sha256`` of each lap file's **exact bytes**
2. one line per lap: ``<lap number>\\t<HANDSHAKE-FROM>\\t<sha256 hex>``
3. sort those lines **byte-wise ascending**
4. join with ``\\n``, append a trailing ``\\n``, encode UTF-8
5. the digest is the **first 16 hex characters** of the ``sha256`` of that, and
   the count of laps included

Keyed on lap number and ``FROM`` rather than the filename, because filenames are
local layout and the two projects already differ.

**What counts as a lap is the part the spec leaves to the reader, and it bit on
the first run.** See :func:`is_a_lap`.

Usage::

    python scripts/round_digest.py 8          # the digest for round 8
    python scripts/round_digest.py 8 --list   # and show every lap it included
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
HANDSHAKE_DIR: Path = REPO_ROOT / "docs" / "handshake"

#: Directories under the handshake tree that hold evidence, not correspondence.
#: Rig artifacts are not laps and must never enter a digest.
NON_LAP_DIRS: frozenset[str] = frozenset(
    {"artifactsround08", "superseded", "artifacts"}
)

#: §2 rule 2 — fenced blocks are stripped before any field is read. A declaration
#: is a statement the file MAKES, never one it QUOTES.
_FENCE_RE: re.Pattern[str] = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def _declarations(text: str, key: str) -> list[str]:
    """Every column-0 declaration of ``key``. Plural on purpose — see :func:`is_a_lap`."""
    stripped = _FENCE_RE.sub("", text)
    return [
        m.group(1).strip()
        for m in re.finditer(rf"^{re.escape(key)}:[ \t]*(.*)$", stripped, re.MULTILINE)
    ]


@dataclass(frozen=True)
class LapFile:
    """One lap, as the digest sees it."""

    path: Path
    lap: str
    sender: str
    sha256: str

    @property
    def line(self) -> str:
        """Step 2 of the construction."""
        return f"{self.lap}\t{self.sender}\t{self.sha256}"


def is_a_lap(text: str) -> bool:
    """Is this file **one lap**, for digest purposes?

    **The spec says "every lap of this round the writer holds" and leaves the
    enumeration to each implementation. That gap is real, and it fired on the very
    first run of this tool**, which is the best possible time.

    Our repository contains `round08platterpusbundle.md` — a *transport envelope*
    carrying three laps verbatim so the operator can send one attachment instead
    of three. It is not a lap: it declares no verdict of its own and closes
    nothing. But it contains three wire headers in its body, so a sweep that reads
    the *first* `HANDSHAKE-LAP` it finds counted it as a fourth lap 2 and produced
    a digest over five entries for a round with four. **A digest that silently
    includes a container is worse than none**: it is stable, reproducible, and
    describes a record neither side has.

    The rule is derived from the spec rather than from a local allowlist, which
    matters because an allowlist only ever excludes the container you already know
    about:

    * **§2 rule 3** — a field declared twice is *ambiguous*, and ambiguity is
      never resolved by taking the first or the last. A file with two
      `HANDSHAKE-LAP` lines is not a lap; it is a file containing laps.
    * A lap must declare a round, a lap number and a sender — exactly once each.

    A quoted-lap appendix, a merged summary, and any future envelope are all
    excluded by the same test, without either project maintaining a list.
    """
    for key in ("HANDSHAKE-ROUND", "HANDSHAKE-LAP", "HANDSHAKE-FROM"):
        if len(_declarations(text, key)) != 1:
            return False
    return True


def laps_for_round(number: int, root: Path = HANDSHAKE_DIR) -> list[LapFile]:
    """Every lap of ``number`` this repository holds — ours and inbound alike."""
    found: list[LapFile] = []
    for path in sorted(root.rglob("*.md")):
        if NON_LAP_DIRS & set(path.parts):
            continue
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        if not is_a_lap(text):
            continue
        if _declarations(text, "HANDSHAKE-ROUND")[0] != str(number):
            continue
        found.append(
            LapFile(
                path=path,
                lap=_declarations(text, "HANDSHAKE-LAP")[0],
                sender=_declarations(text, "HANDSHAKE-FROM")[0],
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )
    return found


def round_digest(laps: list[LapFile]) -> tuple[str, int]:
    """Steps 2–5. Returns ``(16 hex chars, lap count)``.

    An empty round hashes the empty-but-for-a-newline blob rather than raising or
    returning a sentinel: *"we hold nothing"* is a real state with a real value,
    and both sides computing the same number for it is the point.
    """
    blob = ("\n".join(sorted(lap.line for lap in laps)) + "\n").encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16], len(laps)


def declaration(number: int, root: Path = HANDSHAKE_DIR) -> str:
    """The header line, formatted exactly as §5a shows it."""
    digest, count = round_digest(laps_for_round(number, root))
    return f"HANDSHAKE-ROUND-DIGEST: sha256/16 = {digest} over {count} lap(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round", type=int, help="round number")
    parser.add_argument("--list", action="store_true", help="show every lap included")
    args = parser.parse_args(argv)

    laps = laps_for_round(args.round)
    if args.list:
        for lap in sorted(laps, key=lambda item: (int(item.lap or 0), item.sender)):
            print(f"  lap {lap.lap:>2}  {lap.sender:<14} {lap.sha256[:16]}  {lap.path}")
        if not laps:
            print("  (no laps held for this round)", file=sys.stderr)
    print(declaration(args.round))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
