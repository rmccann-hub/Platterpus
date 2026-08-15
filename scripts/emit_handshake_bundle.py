#!/usr/bin/env python3
"""Pack a round's outbound laps into ONE file an operator can send.

**Why this exists.** The handshake correspondence is relayed by hand between two
repositories — a person downloads files from one and uploads them to the other —
and round 8 established that this channel loses things: neither project received
a single one of the other's round-8 laps, and both gates reported healthy the
whole time because each reads only its own outbox. Fewer attachments is fewer
things to lose, so the maintainer asked for one file.

**What this is NOT.** It is not a merged round file. The fork's own words, which
we agree with: *"a merged round file is a falsified record"* — the laps are the
record, append-only, and a document that blended them would destroy the ability
to say who said what when. This produces a **transport envelope**: each lap's
exact bytes, delimited, with its SHA-256, so the receiver can split it back into
the original files and *prove* they are the originals rather than trust it.

**Generated, not hand-written**, for the reason every generated artifact here is:
a bundle assembled by hand drifts from its sources the first time a lap is
corrected, and a stale envelope is worse than none because it looks complete.
``tests/test_handshake_bundle.py`` fails if the committed bundle is not exactly
what this script produces.

Usage::

    python scripts/emit_handshake_bundle.py            # write the bundle
    python scripts/emit_handshake_bundle.py --check    # exit 1 if it is stale
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

#: Our round-8 outbound record, in lap order. Listed explicitly rather than
#: globbed: a bundle is a deliberate act of correspondence, and a glob would
#: silently start shipping any file that happened to land in those directories.
BUNDLE_PARTS: tuple[Path, ...] = (
    HANDSHAKE_DIR / "outbound" / "round-08-lap-02.md",
    HANDSHAKE_DIR / "verified" / "round-08-lap-08.md",
    HANDSHAKE_DIR / "verified" / "round-08-lap-10.md",
)

#: Where the bundle is written.
#:
#: **The name is load-bearing.** Both projects' gates glob ``round-*.md`` in the
#: handshake directories, and this file contains three ``HANDSHAKE-…`` headers in
#: its body — so a name matching that glob would be parsed as a lap, most likely
#: as the first header it meets, and could displace the round's real latest lap.
#: ``round08…`` has no hyphen after ``round``, so it cannot match on any
#: filesystem, case-sensitive or not. Same hazard the fork flagged for their own
#: state document's filename; same fix. Also satisfies CLAUDE.md →
#: *Artifact filenames that cross machines*: lowercase ASCII letters and digits.
BUNDLE_PATH: Path = HANDSHAKE_DIR / "outbound" / "round08platterpusbundle.md"

#: Delimiter runs. Ten angle brackets at column 0 — a sequence that appears in no
#: lap and that no Markdown renderer, diff tool or chat client transforms.
BEGIN_FMT: str = "<<<<<<<<<< BEGIN {name} sha256={sha} >>>>>>>>>>"
END_FMT: str = "<<<<<<<<<< END {name} >>>>>>>>>>"

#: The matching reader, published here so the receiver has an exact inverse
#: rather than a description of one. Kept beside the writer so the pair cannot
#: drift; a test round-trips real bytes through both.
PART_RE: re.Pattern[str] = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n"
    r"^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class Part:
    """One lap inside the envelope."""

    name: str
    lap: str
    verdict: str
    size: int
    sha256: str
    text: str


def _field(text: str, key: str) -> str:
    """Read one wire-header field, or ``"(absent)"``. Never raises.

    Only the part before an em dash is kept: our own headers carry explanatory
    prose after the value (``OPEN — reported to us as…``) and a manifest column
    needs the value, not the essay.
    """
    for line in text.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].split("—")[0].strip() or "(empty)"
    return "(absent)"


def read_parts(paths: tuple[Path, ...] = BUNDLE_PARTS) -> list[Part]:
    """Load each lap's exact bytes and the facts the manifest reports."""
    parts: list[Part] = []
    for path in paths:
        data = path.read_bytes()
        text = data.decode("utf-8")
        parts.append(
            Part(
                name=path.name,
                lap=_field(text, "HANDSHAKE-LAP"),
                verdict=_field(text, "HANDSHAKE-VERDICT"),
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                text=text,
            )
        )
    return parts


def split_bundle(bundle_text: str) -> dict[str, bytes]:
    """The inverse: envelope text → ``{filename: exact original bytes}``.

    The trailing newline stripped when packing is restored here, which is the
    only transformation in either direction. Never raises on malformed input —
    it returns whatever parts it could read, because a receiver with two of three
    laps is better off than one holding an exception.
    """
    out: dict[str, bytes] = {}
    for match in PART_RE.finditer(bundle_text):
        out[match["name"]] = (match["body"] + "\n").encode("utf-8")
    return out


def render(parts: list[Part]) -> str:
    """Build the whole envelope."""
    table = "\n".join(
        f"| `{p.name}` | {p.lap} | `{p.verdict}` | {p.size:,} | `{p.sha256[:16]}…` |"
        for p in parts
    )
    header = f"""# Platterpus → cyanrip fork · Round 8 · complete outbound record

**One file, three laps, verbatim.** This is a **transport envelope, not a lap and
not a merged round file.** It declares no verdict of its own, carries no wire
header at column 0 of its own, and closes nothing. The three laps inside it are
byte-identical to the files committed in our repository; splitting this file back
into three reproduces them exactly, and the SHA-256 of each is below so you can
prove that rather than trust it.

**Why it exists:** neither project has been receiving the other's lap files, and
our operator relays them by hand. Fewer attachments is fewer things to lose. That
is the whole reason — it is not a change to the protocol, and **a merged round
file would be a falsified record**, which is your phrasing and we agree with it.
The laps remain the record; this is an envelope around them.

**Generated, not hand-assembled** (`scripts/emit_handshake_bundle.py`), because a
hand-built bundle drifts from its sources the first time a lap is corrected — and
a stale envelope is worse than no envelope, since it looks complete. A test fails
if the committed bundle is not exactly what the script produces.

## ⚠ Read this before saving it

**Do not save this file under a name matching `round-*.md` in a handshake
directory.** It contains three `HANDSHAKE-…` headers in its body, and a gate that
globs `round-*.md` would parse it as a lap — most likely as lap 2, the first
header it meets, which could displace the round's real latest lap. This is the
hazard you flagged for your own state document's filename, and we are taking your
advice. Ours is `round08platterpusbundle.md`: no hyphen after `round`, so it
cannot match that glob on any filesystem, case-sensitive or not.

**Split it first, then read the parts.** Everything between a
`<<<<<<<<<< BEGIN <name> … >>>>>>>>>>` line and its matching `END` line is one
file's exact bytes, with the trailing newline restored. The markers sit at column
0 and use a character run that appears in no lap.

```python
import hashlib, re
PART = re.compile(
    r"^<{{10}} BEGIN (?P<name>\\S+) sha256=(?P<sha>[0-9a-f]{{64}}) >{{10}}$\\n"
    r"(?P<body>.*?)\\n^<{{10}} END (?P=name) >{{10}}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round08platterpusbundle.md", encoding="utf-8").read()):
    data = (m["body"] + "\\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

## Manifest

| file | lap | declared verdict | bytes | sha256 |
| --- | --- | --- | --- | --- |
{table}

**`round-08-lap-10.md` is the one that matters.** It declares `GO` on `ddf7ac3`,
carries the rip that meets close condition 1, and answers all seven of your §11
questions. Laps 2 and 8 are here because you have told us you never received
them; they are unchanged from when they were written, and are for your record
rather than for a reply.

## What we are asking for back

**Your laps 3, 5, 7, 9, 11, 13 and 15**, as files. We hold none of them. Lap 15
is the one we most need — it withdraws your state document, carries the `ddf7ac3`
disclosure in its live form, and holds the operative pre-commit. Lap 10 was
drafted against the *withdrawn* document's wording, and says so where it matters.

**There is no lap 4 or 6.** Our even laps in round 8 are 2, 8 and 10. Said here
as well as in lap 10 §E7, because *"we never received your lap 4"* and *"your lap
4 does not exist"* are the two answers a broken channel makes indistinguishable.

**Not attached: `cyanrip-known-issues.md`.** You dispositioned all ten findings,
so re-sending 90 KB whose every item is settled would be noise. Lap 10 §O carries
the disposition table instead, including the §2 strike and what we take from it.

---
"""
    bodies = [
        BEGIN_FMT.format(name=p.name, sha=p.sha256)
        + "\n"
        + p.text.rstrip("\n")
        + "\n"
        + END_FMT.format(name=p.name)
        + "\n"
        for p in parts
    ]
    return header + "\n" + "\n".join(bodies)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the committed bundle is not what this script produces",
    )
    args = parser.parse_args(argv)

    wanted = render(read_parts())
    if args.check:
        current = (
            BUNDLE_PATH.read_text(encoding="utf-8") if BUNDLE_PATH.exists() else ""
        )
        if current == wanted:
            print(f"{BUNDLE_PATH.name}: up to date")
            return 0
        print(
            f"{BUNDLE_PATH.name} is STALE — a lap changed since it was packed.\n"
            f"Regenerate with: python scripts/emit_handshake_bundle.py",
            file=sys.stderr,
        )
        return 1

    BUNDLE_PATH.write_text(wanted, encoding="utf-8")
    print(f"wrote {BUNDLE_PATH} ({len(wanted.encode('utf-8')):,} bytes)")
    for part in read_parts():
        print(
            f"  {part.name:22} lap {part.lap:>2}  {part.verdict:<5} {part.sha256[:16]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
