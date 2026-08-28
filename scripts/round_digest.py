#!/usr/bin/env python3
"""`HANDSHAKE-ROUND-DIGEST` — protocol v4 §5a, implemented from the spec text.

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

**v4 adds the asymmetric exclusion, and getting it backwards is the failure
mode**, so it is stated here as well as in `--exclude`'s help:

> The digest declared in lap N covers every lap the writer holds, excluding lap
> N. **A verifier checks it by computing over its own holdings, excluding that
> same lap N** — not its own newest lap.

The writer excludes *itself*; the reader excludes *the file it just received*.
Equality then means exactly *"we hold the same record apart from the lap in
flight"*. If a verifier excluded its own newest lap instead, the two sides would
exclude different files and disagree permanently — the failure §5a exists to
prevent, reintroduced by the fix for a different one. That half is the fork's,
added in round 9 lap 3 §B2, and it is the reason this takes a lap name rather
than a boolean.

Usage::

    python scripts/round_digest.py 8                              # round 8
    python scripts/round_digest.py 8 --list                       # show the laps
    python scripts/round_digest.py 9 --exclude round-09-lap-04.md # writer side
    python scripts/round_digest.py 9 --exclude round-09-lap-03.md # reader side
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

    Our repository carries a *transport envelope* — one file wrapping several laps
        verbatim so the operator moves one attachment instead of nine. It is not a lap:
        it declares no verdict and closes nothing. But it carries a wire header per
        part, so a sweep that reads the *first* `HANDSHAKE-LAP` it finds counted the
        envelope as an extra lap and produced a digest over one entry too many.
        **A digest that silently includes a container is worse than none**: it is
        stable, reproducible, and describes a record neither side has.

        The rule is derived from the spec rather than from a local allowlist, which
        matters because an allowlist only ever excludes the container you already know
        about:

        **Adopted into the shared spec as v4 §5a "What counts as one lap"**, with the
        reasoning and the defect recorded — cyanrip measured it against their own tree
        before agreeing (no file of theirs declares any of the three fields more than
        once; round 8's digest was unchanged), which is the right way to accept a rule.

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


class UnmatchedExclusion(Exception):
    """``--exclude`` named a file this round does not contain.

    **Raised rather than ignored, and that is the whole point of the class.** The
    first version matched on basename and silently dropped nothing when the name
    did not match — so passing a *path* instead of a basename printed a confident
    digest over the full set, including the very lap it had been told to remove.
    A caller comparing that number against a peer's would have read a manufactured
    mismatch as a real one.

    That is this project's own *"can this check be satisfied by finding nothing?"*
    failure, sitting inside the tool that implements the one §5a rule neither side
    may override. Found by an adversarial review of the diagnosis it was being used
    to produce, 2026-08-15 — not by the tool's own tests, which only ever passed it
    names that matched.
    """


def laps_for_round(
    number: int, root: Path = HANDSHAKE_DIR, *, exclude: tuple[str, ...] = ()
) -> list[LapFile]:
    """Every lap of ``number`` this repository holds — ours and inbound alike.

    ``exclude`` names lap files **by basename** and drops them (§5a, v4). Names
    rather than a flag because writer and reader exclude *different* files and must
    both be able to say which: the writer excludes the lap it is composing, the
    verifier excludes the lap it just received. A boolean "exclude the newest" would
    read correctly on the writing side and be silently wrong on the reading side,
    which is the whole reason the spec spells it out.

    **A name that matches nothing raises** :exc:`UnmatchedExclusion`. Plural because
    a verifier reproducing an older declaration has to drop every lap filed since,
    and the single-valued form could not express it — which meant the natural
    command for re-checking a past number quietly returned a different one.
    """
    # **AN EXCLUSION THAT MATCHES MORE THAN ONE FILE IS A REFUSAL, NOT A DROP OF
    # BOTH.** This is the exact mirror of the defect we found in round 9 and they
    # shipped our fix for: there, `--exclude` matching *nothing* silently dropped
    # nothing and printed a confident digest over the full set. **Neither project
    # then asked it the other way round** — matching *more than one* dropped all of
    # them, just as silently — and it stayed unreachable until two laps shared a
    # number, which is why it survived nine rounds.
    #
    # Found by the cyanrip fork, round 14 lap 19 §5, and confirmed here against our
    # own record before believing it: `--exclude round-14-lap-16.md` matched the
    # inbound and outbound lap 16, removed both, and returned `710ed2493fccd59c
    # over 19` — a confident answer over a population nobody asked for, exit 0.
    #
    # They sent the SPECIFICATION rather than their code, deliberately: a test does
    # not travel, its specification does. Two implementations that share an ancestor
    # share its bugs, which is what the round-9 half already proved.
    #
    # A repo-relative path now disambiguates, so a caller who genuinely wants one of
    # two same-numbered laps can say which. That reverses the old message's advice
    # ("Basenames only… not a path"), which was written when a basename could not be
    # ambiguous.
    repo_root = root.parent.parent
    wanted_out = set(exclude)
    hits: dict[str, list[Path]] = {name: [] for name in wanted_out}
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
        # Three spellings accepted, because the caller's frame of reference varies:
        # the bare basename (the common case), the path relative to the handshake
        # ROOT (`inbound/round-14-lap-16.md` — what a test with its own tree can
        # express), and the path relative to the REPO (`docs/handshake/inbound/…` —
        # what a person copies out of an error message). All three name one file
        # unambiguously; only the basename can collide.
        spellings = {path.name, path.relative_to(root).as_posix()}
        try:
            spellings.add(path.relative_to(repo_root).as_posix())
        except ValueError:  # pragma: no cover - root outside the repo
            pass
        keys = spellings & wanted_out
        if keys:
            for k in keys:
                hits[k].append(path)
            continue
        found.append(
            LapFile(
                path=path,
                lap=_declarations(text, "HANDSHAKE-LAP")[0],
                sender=_declarations(text, "HANDSHAKE-FROM")[0],
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )

    ambiguous = {k: v for k, v in hits.items() if len(v) > 1}
    if ambiguous:
        detail = "; ".join(
            f"{k!r} matches "
            + ", ".join(p.relative_to(repo_root).as_posix() for p in sorted(paths))
            for k, paths in sorted(ambiguous.items())
        )
        raise UnmatchedExclusion(
            f"--exclude is AMBIGUOUS: {detail}. Two laps share that number — one "
            "from each sender — so dropping both would answer over a population "
            "you did not ask for. Name the one you mean by its repo-relative "
            "path, or pass both paths if you really want both."
        )

    missing = sorted(k for k, v in hits.items() if not v)
    if missing:
        raise UnmatchedExclusion(
            f"--exclude named {missing}, which round {number} does not "
            "contain. Use a basename (round-09-lap-04.md) or, when two senders "
            "share a lap number, the repo-relative path. Refusing rather than "
            "printing a digest over a set you did not ask for."
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


def declaration(
    number: int, root: Path = HANDSHAKE_DIR, *, exclude: tuple[str, ...] = ()
) -> str:
    """The header line, formatted exactly as §5a shows it."""
    digest, count = round_digest(laps_for_round(number, root, exclude=exclude))
    return f"HANDSHAKE-ROUND-DIGEST: sha256/16 = {digest} over {count} lap(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round", type=int, help="round number")
    parser.add_argument("--list", action="store_true", help="show every lap included")
    parser.add_argument(
        "--exclude",
        metavar="LAP-FILE",
        action="append",
        default=[],
        help=(
            "drop one lap by basename (v4 section 5a). ASYMMETRIC, and getting it "
            "backwards is the failure mode. Repeatable. As the WRITER of lap N, exclude lap N "
            "-- your own file, which the reader cannot hash because you have not "
            "sent it. As the READER verifying lap N, exclude THAT SAME lap N, not "
            "your own newest. Excluding your own newest makes the two sides drop "
            "different files and disagree forever."
        ),
    )
    args = parser.parse_args(argv)

    exclude = tuple(args.exclude)
    try:
        laps = laps_for_round(args.round, exclude=exclude)
    except UnmatchedExclusion as exc:
        print(f"round_digest: {exc}", file=sys.stderr)
        return 2
    if args.list:
        for lap in sorted(laps, key=lambda item: (int(item.lap or 0), item.sender)):
            print(f"  lap {lap.lap:>2}  {lap.sender:<14} {lap.sha256[:16]}  {lap.path}")
        if not laps:
            print("  (no laps held for this round)", file=sys.stderr)
    print(declaration(args.round, exclude=exclude))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
