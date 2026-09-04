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
#:
#: **This file is the OFFERED packaging of the current lap, not a record of what
#: was sent.** The record of what was sent is `tests/test_sent_laps_are_immutable.py`,
#: because a send is an act by the operator and this generator cannot observe it.
#: Keeping the two straight is not pedantry: round 9 lap 6 went out bare while this
#: envelope sat in `outbound/` packing lap 6 *and* lap 2, and the lap's own prose
#: then said both that it travelled in an envelope (§B) and that it travelled bare
#: (§E). One artifact implying a send that did not happen was half of that
#: contradiction — see lap 8 §A2.
#: `PARTS[0]` is the OPERATIVE lap — `lead_identity()` names the envelope after it.
#: Part 2 is `src/platterpus/rig_scripts/fullacceptance.txt`, the acceptance script
#: itself (it moved into the package on 2026-08-28 so the app can open it).
#: Round 14's only close condition is a hardware pass, the maintainer asked that the
#: fork be given *the plan and the script* to amend rather than a description of
#: them, and lap 2 quotes the file's sha256 — so the file has to travel or that
#: quote is unverifiable. It is NOT a lap and carries no wire headers, so it cannot
#: be miscounted; `assert_not_a_lap` checks that property on the envelope before
#: writing it.
PARTS: tuple[Path, ...] = (
    HANDSHAKE_DIR / "outbound" / "round-15-lap-07.md",
    HANDSHAKE_DIR / "outbound" / "round-15-lap-04.md",
    HANDSHAKE_DIR / "outbound" / "round-15-lap-05.md",
    HANDSHAKE_DIR / "outbound" / "round-15-lap-06.md",
    REPO_ROOT / "src" / "platterpus" / "rig_scripts" / "fullacceptance.txt",
)

# WHY THIS CARRIES FOUR LAPS, AND WHY THAT IS A FAILURE REPORT RATHER THAN A
# FEATURE (2026-09-04).
#
# Laps 4, 5 and 6 were written on 09-02, 09-03 and 09-04 and **none of them was
# ever handed over.** This constant stayed pointed at round 14 lap 16 through all
# three, and the envelope was regenerated FOUR separate times on 09-04 — because
# it also carries `fullacceptance.txt`, which was being edited — each time
# reporting success while packing a round the peer closed weeks ago.
#
# That is exactly the failure cyanrip's round-9 lap 3 §B1 named when they argued
# against deleting this generator: *"deleting the instance removed your exposure;
# the rule removed everyone's."* The rule they got us to write is that an envelope
# cannot be miscounted as a lap. It says nothing about an envelope that is
# faithfully, repeatedly, correctly built around the WRONG lap — and the docstring
# above already warned about the neighbouring case ("one artifact implying a send
# that did not happen"), which is how this one hid in plain sight.
#
# The laps travel UNMODIFIED. Protocol v4 §4a makes a correction a new lap rather
# than an edit, and there is a concrete reason beyond the principle: laps 5 and 6
# each declare a `HANDSHAKE-ROUND-DIGEST` computed over the laps before them, so
# editing 4 or 5 now would falsify a value already written down. `round-08-lap-18`
# is the precedent — written, never sent, sent unmodified two rounds later, on the
# reasoning that sending a file late does not make it a new file.
#
# PARTS[0] is lap 7 because `lead_identity()` names the envelope after the
# OPERATIVE lap, and 7 is the one that covers the other three. Its §A tells the
# reader to take 4, 5 and 6 first; the packing order and the reading order differ
# here for the first time, deliberately.
#
# `fullacceptance.txt` travels for the same reason it did in round 14: it CHANGED
# materially in this lap's subject — nine rips that asserted nothing about
# completion now do, and both `expect-status Done` sites are gone — and it is the
# artifact the round's only close condition is produced by. A lap that alters the
# script the other side is about to have run, sent without the script, is a
# description of an artifact instead of the artifact.
#
# `securereread.txt` stays OUT even though it changed this time (it carried both
# defects: the 10800 budget and `expect-status Done`). The fork's lap 11 §K
# retired it for this run because `fullacceptance.txt` contains T1 as section N,
# so it is not part of the close condition; lap 7 §C4 cites it as evidence that
# the fix was swept rather than applied where it was found, which is a claim about
# our process rather than an artifact they must review.

# WHY THIS MOVED FROM LAP 6 TO LAP 13, and why `securereread.txt` came out.
#
# Lap 13 leads because it CORRECTS lap 12's own header — `0.6.26` was unpublished
# when lap 12 declared the operator was running it — so the two must travel
# together or the peer reads the correction after the thing it corrects. The lap-12
# envelope was superseded before it was sent and is not kept: an envelope on disk
# that nobody sent is a record of nothing.
#
# Laps 8 and 10 were sent BARE and PARTS deliberately stayed on lap 6 through
# both: an envelope exists to carry a lap *plus artifacts*, and a lap that only
# answers a lap would produce a one-part envelope — pointless, and the case
# `assert_not_a_lap` is tightest against. The fork sends theirs bare for the same
# reason.
#
# Lap 12 is different: it CHANGES `fullacceptance.txt` — a new `abort-if-failed`
# guard after the identity section, and the fork's C1 detector as section P2 — and
# that file is the round's only close condition. A lap that alters the script the
# other side is about to have run, sent without the script, is a description of an
# artifact instead of the artifact. So the envelope moves with it.
#
# **`securereread.txt` is out because it did not change.** The fork's lap 11 §K
# retires it for this run (`fullacceptance.txt` contains T1 as section N) and it
# is unchanged since lap 6, so re-sending it is the noise both sides keep
# declining to send. It stays in the tree for a night when only the close matters.
#
# The consequence to keep in view: the published `round14lap06platterpus.md` on
# disk is now HISTORY, not the current envelope. That is correct — it is the record
# of what lap 6 sent, and lap 6 sent the file as it then stood. Regenerating it
# against today's script would falsify what we sent.

#: The envelope's name, as a template. **Two properties, and both are checked by
#: `tests/test_handshake_file_naming.py` rather than asserted in this comment.**
#:
#: 1. **It cannot match `round-*.md`**, the glob both projects' gates use. The
#:    envelope carries wire headers in its body, so a matching name could be
#:    resolved as a lap and displace the round's real latest one. `round09…` has no
#:    hyphen after `round`, so it cannot match on any filesystem, case-sensitive or
#:    not.
#: 2. **It is safe to cross machines** — CLAUDE.md → *Artifact filenames that cross
#:    machines*: lowercase ASCII letters and digits only, numbers zero-padded. This
#:    file is relayed by hand through a chat client and a file manager, which is the
#:    exact path that lost a rig run to `round08joint.txt` vs `round-08-joint.txt`.
#:
#: **Why a template and not a literal.** The literal drifted three times in one
#: session — `round08platterpusbundle.md` → `round09platterpusenvelope.md` →
#: `round09lap06platterpus.md` — because nothing stated the pattern and nothing
#: checked it, so each send re-invented the name. The operator noticed before any
#: gate did. The name is now *generated from the lap it carries*, the same rule
#: `handshake_filename` follows and for the same reason: a hand-typed name is a
#: second description of a fact the file already declares.
NAME_TEMPLATE: str = "round{round:02d}lap{lap:02d}platterpus.md"


def envelope_filename(round_: int, lap: int) -> str:
    """The cross-machine name for the envelope carrying ``round``/``lap``.

    Zero-padded to two digits to match the lap-file convention's pad width, so the
    two names state the same numbers the same way.
    """
    return NAME_TEMPLATE.format(round=round_, lap=lap)


def lead_identity() -> tuple[int, int]:
    """``(round, lap)`` of the lap this envelope is *for* — read from its header.

    ``PARTS[0]`` is the lap being sent; anything after it is context the peer asked
    for. Reading the header rather than taking arguments is what makes the name
    unable to drift from the contents: change the parts and the name follows.
    """
    text = _FENCE_RE.sub("", PARTS[0].read_text(encoding="utf-8"))
    found: list[int] = []
    for field in ("HANDSHAKE-ROUND", "HANDSHAKE-LAP"):
        values = re.findall(rf"^{field}:[ \t]*(\d+)[ \t]*$", text, re.MULTILINE)
        if len(values) != 1:
            raise SystemExit(
                f"cannot name the envelope: {PARTS[0].name} declares {field} "
                f"{len(values)} time(s), and the name states that number. "
                "A lead part must be exactly one lap."
            )
        found.append(int(values[0]))
    return found[0], found[1]


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

#: Where the envelope is written. Defined here rather than beside `NAME_TEMPLATE`
#: only because it calls `lead_identity()`, which needs `_FENCE_RE` to exist.
OUT: Path = HANDSHAKE_DIR / "outbound" / envelope_filename(*lead_identity())


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
    """Envelope text → ``{filename: exact original bytes}``. Never raises.

    **Parses the hash and does not check it** — deliberately, so this stays a pure
    inverse of :func:`render`. :func:`verify_split` is the checking form, and it
    is what the CLI calls. Nothing should use this one to decide whether an
    envelope arrived intact.
    """
    return {
        m["name"]: (m["body"] + "\n").encode("utf-8")
        for m in PART_RE.finditer(envelope)
    }


def verify_split(envelope: str) -> list[tuple[str, bytes, str, str]]:
    """Split and check every part. ``[(name, body, declared, computed)]``.

    A part is intact when ``declared == computed``. Returns both rather than a
    bool per part, because the caller has to be able to *print* the mismatch — a
    corrupted transfer that reports only "failed" leaves the two projects with no
    way to tell a truncation from a re-encoding.

    **Why this exists as a checking function at all.** :func:`split` parses the
    ``sha256=`` out of the delimiter and then ignores it, and until now that was
    the only splitter — reachable from no CLI, so every actual split was done by
    hand-writing the regex again (three times on 2026-08-21 alone). A per-part
    hash that nothing compares is decoration, and the delimiter carries it
    precisely so an envelope that lost bytes in a chat client cannot be read as
    complete. Same shape as the rule about a `cancel()` with no call site: the
    capability was implemented and unreachable.
    """
    out: list[tuple[str, bytes, str, str]] = []
    for match in PART_RE.finditer(envelope):
        body = (match["body"] + "\n").encode("utf-8")
        out.append(
            (match["name"], body, match["sha"], hashlib.sha256(body).hexdigest())
        )
    return out


def _do_split(envelope_path: Path, into: Path) -> int:
    """Write every part of `envelope_path` into `into`, verifying each hash.

    Refuses to write anything if any part fails, rather than leaving a directory
    of files where some are trustworthy and some are not — a half-written split
    is worse than none, because the next step reads whatever is on disk.
    """
    try:
        text = envelope_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {envelope_path}: {exc}", file=sys.stderr)
        return 1

    parts = verify_split(text)
    if not parts:
        print(
            f"{envelope_path}: no envelope parts found. Expected column-0 "
            f"delimiters of the form '<<<<<<<<<< BEGIN <name> sha256=<64 hex> "
            f">>>>>>>>>>'. A file with none is not an envelope — check whether a "
            f"chat client reflowed it.",
            file=sys.stderr,
        )
        return 1

    bad = [(n, d, c) for n, _b, d, c in parts if d != c]
    for name, _body, declared, computed in parts:
        mark = "OK  " if declared == computed else "BAD "
        print(
            f"{mark} {name:44} {declared[:16]} {'==' if declared == computed else '!='} {computed[:16]}"
        )
    if bad:
        print(
            f"\n{len(bad)} of {len(parts)} parts do not match their declared "
            f"hash. NOTHING was written. Ask the sender to resend — and say which "
            f"parts, because a mismatch on one part and on all of them are "
            f"different problems.",
            file=sys.stderr,
        )
        return 1

    into.mkdir(parents=True, exist_ok=True)
    for name, body, _declared, _computed in parts:
        # `Path(name).name` so a part called "../../etc/passwd" cannot escape the
        # target directory. The envelope is external input from another project;
        # nothing crosses that seam unchecked (Critical rule #12).
        target = into / Path(name).name
        target.write_bytes(body)
    print(f"\n{len(parts)} parts verified and written to {into}")
    return 0


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
    parser.add_argument(
        "--split",
        metavar="ENVELOPE",
        type=Path,
        help=(
            "UNPACK a received envelope instead of building ours: verify every "
            "part against its declared sha256 and write them out. Refuses to "
            "write anything if any part mismatches."
        ),
    )
    parser.add_argument(
        "--into",
        metavar="DIR",
        type=Path,
        default=Path("."),
        help="where --split writes the parts (default: the current directory)",
    )
    args = parser.parse_args(argv)

    # --split is the INBOUND direction and shares nothing with building ours, so
    # it returns before any of the outbound machinery runs. In particular it must
    # not require our own PARTS to exist: unpacking what the fork sent has to work
    # in a tree where we have no outbound lap staged.
    if args.split is not None:
        return _do_split(args.split, args.into)

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
