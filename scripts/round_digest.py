#!/usr/bin/env python3
"""Compute `HANDSHAKE-ROUND-DIGEST` — the cyanrip fork's method, adopted whole.

**Why theirs and not ours.** Our round-15 lap 2 declared a digest computed by
hand: `sha256` over the concatenated bytes of `docs/handshake/inbound/round-NN-lap-*.md`.
Their lap 3 §3 reproduced that number exactly — so the *construction* was
understood on both sides — and then named the part that actually matters:

    "A digest over only our own outbox would agree with itself forever, which is
    the defect this replaces."

Ours had the mirror of that property. **An inbox-only digest can never disagree
about anything we sent**, so it cannot detect the case the field exists for. That
is a defect of population, not of algorithm, and it survives any amount of care
about hashing. Their offer was "adopt ours or tell us to adopt yours; we are not
attached" — and theirs is strictly better, so this is theirs.

**The construction, from their lap 3 §3(a), implemented rather than paraphrased:**

1. one row per lap: ``<lap number>\\t<HANDSHAKE-FROM value>\\t<sha256 hex of the
   file's bytes>``
2. sort the rows **as strings**
3. join with ``\\n``, then append a trailing ``\\n``
4. ``sha256`` the UTF-8 bytes, truncate to 16 hex

The empty record therefore hashes ``"\\n"`` and gives ``01ba4719c80b6fe9`` — which
is what their lap 1 declared over zero laps, and is the first fixture in
`tests/test_round_digest.py`.

**Population: the whole record.** Every lap of the round, ours *and* theirs.

**The two `--exclude` refusals are not polish.** Both cost a real defect, one on
each side:

* an `--exclude` matching **nothing** must refuse rather than silently exclude
  nothing — we found that in round 9, they had it too;
* an `--exclude` matching **more than one** file must also refuse. That is the
  mirror and neither side had asked it. It became reachable the moment two laps
  crossed at one number — round 14 crossed four times — and
  ``--exclude round-14-lap-18.md`` then dropped *both* sides' laps, producing a
  confident digest over a population nobody asked for, **at the same count**.

**And a THIRD refusal, found 2026-09-07 while re-deriving a peer's older digest.**
`--exclude` was a single-value option, so ``--exclude A.md --exclude B.md``
silently kept A: argparse takes the last value and nothing complained. The
command printed a digest, an exit code of 0, and a lap count — over a population
that still contained a lap the caller had explicitly named. Exactly the failure
the two refusals above exist to prevent, arriving through the *interface* rather
than through the matching, and it is reachable whenever a peer's digest predates
laps that now exist: reproducing their lap-4 number needs both lap 4 and lap 5
left out. `--exclude` now accumulates, and every name is still held to matching
exactly one file.

A digest that is wrong is recoverable. A digest that is wrong *and reports the
expected number of laps* is the one that gets believed.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_HANDSHAKE: Final[Path] = _REPO_ROOT / "docs" / "handshake"

#: Where a round's laps live. Both directions, which is the point.
_DIRECTIONS: Final[tuple[str, ...]] = ("inbound", "outbound")

#: `HANDSHAKE-FROM: <value>` at column 0. Anchored to the exact key so
#: `HANDSHAKE-FROM-COMMIT:` and `HANDSHAKE-FROM-REPO:` cannot satisfy it — they
#: share the prefix and mean something else entirely.
_FROM: Final[re.Pattern[str]] = re.compile(
    r"^HANDSHAKE-FROM:[ \t]*(?P<value>\S+)", re.MULTILINE
)

#: `round-NN-lap-LL.md`, the committed lap spelling (`CLAUDE.md` → *Artifact
#: filenames*: the hand-carried envelope uses a different convention on purpose).
_LAP_NAME: Final[re.Pattern[str]] = re.compile(
    r"^round-0*(?P<round>\d+)-lap-0*(?P<lap>\d+)\.md$"
)


class DigestError(RuntimeError):
    """A refusal. Raised rather than returned so no caller can ignore it."""


@dataclass(frozen=True)
class Row:
    """One lap's contribution, before it becomes a line of text."""

    lap: int
    sender: str
    sha256: str
    path: Path

    def render(self) -> str:
        """Their exact row format. Tabs, not spaces — a separator that cannot
        occur inside any of the three fields."""
        return f"{self.lap}\t{self.sender}\t{self.sha256}"


def _laps_for_round(round_number: int) -> list[Path]:
    """Every committed lap of ``round_number``, both directions, sorted by name."""
    found: list[Path] = []
    for direction in _DIRECTIONS:
        directory = _HANDSHAKE / direction
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("round-*-lap-*.md")):
            match = _LAP_NAME.match(path.name)
            if match and int(match.group("round")) == round_number:
                found.append(path)
    return sorted(found, key=lambda p: (p.name, p.parent.name))


def _row_for(path: Path) -> Row:
    """Build one row, refusing a lap that declares no sender.

    A lap with no `HANDSHAKE-FROM` cannot be placed in the record — and guessing
    from the directory it sits in would make the digest depend on our filing
    rather than on the document, which is the same class of error as reading a
    pin from a covering message instead of the artifact.
    """
    raw = path.read_bytes()
    match = _FROM.search(raw.decode("utf-8", errors="replace"))
    if match is None:
        raise DigestError(
            f"{path.name} declares no `HANDSHAKE-FROM:`, so it cannot be placed "
            f"in the record. A row keyed on the directory would describe our "
            f"filing rather than the document."
        )
    name_match = _LAP_NAME.match(path.name)
    if name_match is None:  # pragma: no cover — the glob already constrains this
        raise DigestError(f"{path.name} is not a lap filename")
    return Row(
        lap=int(name_match.group("lap")),
        sender=match.group("value"),
        sha256=hashlib.sha256(raw).hexdigest(),
        path=path,
    )


def digest_of(rows: list[Row]) -> str:
    """Steps 2–4 of their construction. Pure, so the fixtures can drive it."""
    lines = sorted(row.render() for row in rows)
    joined = "\n".join(lines) + "\n"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _exclusion_names(exclude: str | Sequence[str] | None) -> tuple[str, ...]:
    """Normalise ``exclude`` to a tuple of names, refusing to iterate a string.

    A bare `str` IS a `Sequence[str]`, so ``exclude="round-16-lap-05.md"`` would
    otherwise iterate 22 single characters, none of which matches a lap — and the
    first one raises the "matched NO lap" refusal, which is a confusing message
    for a correct call. One name is the common case and must keep working; this is
    the only place that decides which shape it got.
    """
    if exclude is None:
        return ()
    if isinstance(exclude, str):
        return (exclude,)
    return tuple(exclude)


def laps_after_exclusions(
    round_number: int, exclude: str | Sequence[str] | None = None
) -> list[Path]:
    """The population a digest is computed over, after honouring ``exclude``.

    **Extracted so `--show-rows` and the digest cannot disagree about it.** They
    did: `--show-rows` filtered the list inline with a bare name comparison and no
    refusals, so a typo'd or ambiguous exclude printed a full set of rows and only
    then hit the error — rows that describe a population the digest refused to
    compute. Two implementations of one filter, which is the defect this project
    keeps finding in other shapes.

    Every name in ``exclude`` must match **exactly one** file. See the module
    docstring for what each of the three refusals cost.
    """
    laps = _laps_for_round(round_number)
    for name in _exclusion_names(exclude):
        matches = [p for p in laps if p.name == name]
        if not matches:
            raise DigestError(
                f"--exclude {name!r} matched NO lap of round {round_number}. "
                f"Refusing rather than excluding nothing: a typo would otherwise "
                f"produce a confident digest over the wrong population. "
                f"Laps present: {[p.name for p in laps]}"
            )
        if len(matches) > 1:
            raise DigestError(
                f"--exclude {name!r} matched {len(matches)} laps "
                f"({[str(p.relative_to(_HANDSHAKE)) for p in matches]}). Refusing: "
                f"two laps crossing at one number is exactly when this fires, and "
                f"dropping both produces a digest over a population nobody asked "
                f"for AT THE SAME COUNT — which is the version that gets believed."
            )
        laps = [p for p in laps if p.name != name]
    return laps


def round_digest(
    round_number: int, *, exclude: str | Sequence[str] | None = None
) -> tuple[str, int]:
    """``(digest, lap count)`` for ``round_number``.

    ``exclude`` names laps to leave out — usually *this* lap, which does not exist
    yet when its own header is written, and sometimes two, when reproducing a
    peer's digest that predates a lap now in the tree.
    """
    rows = [_row_for(p) for p in laps_after_exclusions(round_number, exclude)]
    return digest_of(rows), len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round", type=int, help="round number")
    parser.add_argument(
        "--exclude",
        metavar="LAP.md",
        action="append",
        help="a lap filename to leave out (usually the lap being written). Repeat "
        "to exclude more than one — it ACCUMULATES rather than overwriting, "
        "because the single-value form silently kept the first name",
    )
    parser.add_argument(
        "--show-rows",
        action="store_true",
        help="print the rows the digest is computed over, so a disagreement is "
        "diagnosable rather than just visible",
    )
    args = parser.parse_args(argv)
    try:
        if args.show_rows:
            laps = laps_after_exclusions(args.round, args.exclude)
            for row in sorted((_row_for(p) for p in laps), key=lambda r: r.render()):
                print(row.render())
        value, count = round_digest(args.round, exclude=args.exclude)
    except DigestError as exc:
        print(f"round-digest: {exc}", file=sys.stderr)
        return 2
    print(f"sha256/16 = {value} over {count} lap(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
