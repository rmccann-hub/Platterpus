#!/usr/bin/env python3
"""Pack the files an exchange needs into ONE file the operator sends.

**One file per exchange.** The operator's rule, 2026-08-15: *"there should only be
one file moving forward, unless the second is a script file to run."* The
correspondence is relayed by hand between two repositories, and every extra
attachment is another thing to lose — round 8 lost fifteen laps that way, in both
directions, while both projects' gates reported healthy.

**Not a merged file and not a lap.** Each part goes in as exact bytes between
column-0 delimiters with its own SHA-256, so the receiver splits it back into the
originals and can *prove* they are the originals. A merged round file would be a
falsified record; this is an envelope around files that stay intact.

**Why it exists again after being deleted.** We built one, it was counted as a lap
by our own round digest and read as a misfiled lap by our naming sweep, and we
deleted it — calling that the stronger fix. cyanrip disagreed in round 9 lap 3 §B1
and was right: *"deleting the instance removed your exposure; the rule removed
everyone's."* The rule is now protocol v4 §5a — a file declaring
`HANDSHAKE-ROUND`, `HANDSHAKE-LAP` or `HANDSHAKE-FROM` more than once is ambiguous
and therefore not a lap — so an envelope is excluded **by construction** on both
sides. :func:`assert_not_a_lap` checks that property on this file's own output
*before writing it*, so an envelope a conforming enumerator would misread is never
produced.

Built from cyanrip's published description rather than their `tools/make-envelope.py`,
and the two are mutually splittable: we split their round-9 envelope with the
reader they published and all ten parts verified.

Usage::

    python scripts/emit_envelope.py --check    # exit 1 if the envelope is stale
    python scripts/emit_envelope.py            # write it
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

#: What this exchange carries, in reading order. Listed explicitly rather than
#: globbed: sending is a deliberate act, and a glob would silently ship whatever
#: happened to land in the directory.
PARTS: tuple[Path, ...] = (
    HANDSHAKE_DIR / "verified" / "round-09-lap-06.md",
    # Their lap 5 §J2 asked for lap 2 hash-declared, so its bytes are verifiable
    # on receipt the way lap 3's never were. It is unchanged from when it was
    # sent — cyanrip publishes the same hash in their own digest lines.
    HANDSHAKE_DIR / "verified" / "round-09-lap-02.md",
)

#: **The name cannot match `round-*.md`**, which is the glob both projects' gates
#: use. The envelope carries wire headers in its body, so a matching name could be
#: resolved as a lap and displace the round's real latest one. `round09…` has no
#: hyphen after `round`, so it cannot match on any filesystem, case-sensitive or
#: not — and it satisfies CLAUDE.md → *Artifact filenames that cross machines*.
OUT: Path = HANDSHAKE_DIR / "outbound" / "round09lap06platterpus.md"

BEGIN: str = "<<<<<<<<<< BEGIN {name} sha256={sha} >>>>>>>>>>"
END: str = "<<<<<<<<<< END {name} >>>>>>>>>>"

#: The exact inverse, published inside the envelope so the receiver has code
#: rather than a description. Byte-compatible with cyanrip's reader — verified by
#: splitting their round-9 envelope with ours and theirs with the same pattern.
PART_RE: re.Pattern[str] = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)

#: Fences stripped before counting declarations, per v4 §2 rule 2.
_FENCE_RE: re.Pattern[str] = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

#: The three fields whose exactly-once presence defines a lap (v4 §5a).
_LAP_FIELDS: tuple[str, ...] = (
    "HANDSHAKE-ROUND",
    "HANDSHAKE-LAP",
    "HANDSHAKE-FROM",
)


@dataclass(frozen=True)
class Part:
    name: str
    size: int
    sha256: str
    text: str


def assert_not_a_lap(envelope: str) -> None:
    """Refuse to emit an envelope a conforming enumerator would read as a lap.

    **Checked on the output, before writing.** The property is structural — an
    envelope carrying N parts declares each field N times — but "structural" is
    what we assumed last time, and the one-part case is exactly where the
    assumption fails: an envelope around a single lap declares each field
    **once**, which is indistinguishable from a lap.

    So the guard is not decoration even though the rule makes it look like one,
    and the fix when it fires is a real one: the envelope's own preamble declares
    the fields too, with a value that says what the file is. That keeps the count
    at two for a one-part envelope and at N+1 for the rest.
    """
    stripped = _FENCE_RE.sub("", envelope)
    for field in _LAP_FIELDS:
        count = len(re.findall(rf"^{re.escape(field)}:", stripped, re.MULTILINE))
        if count == 1:
            raise SystemExit(
                f"refusing to write {OUT.name}: it declares {field} exactly once, "
                "so a conforming enumerator (v4 §5a) would read this envelope as a "
                "lap. Add the envelope's own declaration to the preamble."
            )


def read_parts() -> list[Part]:
    out: list[Part] = []
    for path in PARTS:
        data = path.read_bytes()
        out.append(
            Part(
                name=path.name,
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                text=data.decode("utf-8"),
            )
        )
    return out


def split(envelope: str) -> dict[str, bytes]:
    """Envelope text → ``{filename: exact original bytes}``. Never raises."""
    return {
        m["name"]: (m["body"] + "\n").encode("utf-8")
        for m in PART_RE.finditer(envelope)
    }


def render(parts: list[Part]) -> str:
    table = "\n".join(
        f"| `{p.name}` | {p.size:,} | `{p.sha256[:16]}…` |" for p in parts
    )
    header = f"""# Transport envelope — {len(parts)} file(s), Platterpus → cyanrip fork

**Not a merged file and not a lap.** Each part below is byte-identical to its
original, between column-0 delimiters, with its own SHA-256. Split it before
reading; the reader is published here as code so you have an exact inverse rather
than a description of one.

**It cannot be counted as a lap.** Its own preamble declares the wire fields
below, so together with the parts it carries it declares each of them more than
once — failing v4 §5a's exactly-once test, which every conforming enumerator
uses. `scripts/emit_envelope.py` asserts that on this file before writing it,
because a **single-part** envelope would otherwise declare each field exactly
once and be indistinguishable from a lap.

HANDSHAKE-ROUND: not-a-lap (transport envelope)
HANDSHAKE-LAP: not-a-lap (transport envelope)
HANDSHAKE-FROM: not-a-lap (transport envelope)

## Manifest

| file | bytes | sha256 |
| --- | --- | --- |
{table}

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{{10}} BEGIN (?P<name>\\S+) sha256=(?P<sha>[0-9a-f]{{64}}) >{{10}}$\\n"
    r"(?P<body>.*?)\\n^<{{10}} END (?P=name) >{{10}}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("{OUT.name}", encoding="utf-8").read()):
    data = (m["body"] + "\\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---
"""
    bodies = [
        BEGIN.format(name=p.name, sha=p.sha256)
        + "\n"
        + p.text.rstrip("\n")
        + "\n"
        + END.format(name=p.name)
        + "\n"
        for p in parts
    ]
    return header + "\n" + "\n".join(bodies)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if stale")
    args = parser.parse_args(argv)

    wanted = render(read_parts())
    assert_not_a_lap(wanted)

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current == wanted:
            print(f"{OUT.name}: up to date")
            return 0
        print(
            f"{OUT.name} is STALE — a part changed since it was packed.\n"
            "Regenerate with: python scripts/emit_envelope.py",
            file=sys.stderr,
        )
        return 1

    OUT.write_text(wanted, encoding="utf-8")
    print(f"wrote {OUT} ({len(wanted.encode('utf-8')):,} bytes)")
    for part in read_parts():
        print(f"  {part.name:28} {part.size:>8,}  {part.sha256[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
