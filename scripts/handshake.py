#!/usr/bin/env python3
"""Emit our outbound handshake file, and validate cyanrip's inbound one.

The handshake (``docs/cyanrip-handshake.md``) is bidirectional: two files per
round, two verifications, and no release from either side until both are in.
Until now that was **prose**, and this project's own rule is that *a rule
nothing executes is not a rule* (``docs/testing.md`` §5.m). Twice a round has
come back missing a required section, and both times it was noticed by luck.

So this script makes the protocol executable in both directions:

* ``--emit`` writes a skeleton **outbound** file with every section §3 of the
  protocol requires, so no round can be sent missing one. The skeleton includes
  the inbound spec inline, because the fork does not have this repo.
* ``--check FILE`` validates a received **inbound** file against §4's required
  sections and exits non-zero listing what is absent. It also flags the two
  failure modes that are *worse* than a missing section: a section present but
  empty, and §D ("log-format delta") left silent when silence is ambiguous.
* ``--status`` reports where the current round stands — what we sent, what came
  back, whether we verified it — read off ``docs/handshake/``.

Neither direction is optional and neither is the default: a round is open until
``--status`` says both files exist *and* our verification was sent.

Usage::

    python scripts/handshake.py --emit 5                 # start round 5 outbound
    python scripts/handshake.py --check docs/handshake/inbound/round-4.md
    python scripts/handshake.py --status
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
HANDSHAKE_DIR: Path = _REPO_ROOT / "docs" / "handshake"
OUTBOUND_DIR: Path = HANDSHAKE_DIR / "outbound"
INBOUND_DIR: Path = HANDSHAKE_DIR / "inbound"
VERIFIED_DIR: Path = HANDSHAKE_DIR / "verified"
PROTOCOL_DOC: Path = _REPO_ROOT / "docs" / "cyanrip-handshake.md"

# Minimum characters of real content under a heading before it counts as
# answered. A heading with "TODO" or a single word under it is the failure mode
# that motivated the checker — a section that is *present but empty* passes a
# naive "is the heading there" test while telling the reader nothing.
MIN_SECTION_CHARS: int = 40


@dataclass(frozen=True)
class Section:
    """One required section of a handshake file."""

    key: str
    title: str
    why: str
    #: True when silence in this section is ambiguous rather than simply
    #: absent — these get the strictest check, because "I didn't mention it"
    #: and "nothing changed" are different answers and only one is safe.
    must_be_explicit: bool = False
    #: Heading keywords that count as this section being present. Used for the
    #: OUTBOUND sections, whose headings are human prose rather than a letter.
    #: Empty for inbound sections, which match on their letter key.
    keywords: tuple[str, ...] = ()


# What cyanrip must send us (protocol §4). The letters are the section keys the
# fork writes as `## A`, `## §A`, `## A.` etc. — the matcher is lenient about
# the decoration and strict about the content.
INBOUND_SECTIONS: tuple[Section, ...] = (
    Section("A", "Pin", "repo, branch, commit SHA, exact --version output"),
    Section(
        "B",
        "Answers",
        "every question, each marked measured / read-from-source / unverified",
    ),
    Section("C", "Changes", "one row per commit, flagging any that alter log text"),
    Section(
        "D",
        "Log-format delta",
        '"no changes" must be written out — silence is ambiguous',
        must_be_explicit=True,
    ),
    Section("E", "Golden log", "regenerated + the command, if D changed"),
    Section(
        "F", "Verification", "proven (with how) vs not proven (with what it takes)"
    ),
    Section("G", "Revert-proof", "per behavioural fix; a 'no' is fine, a blank is not"),
    Section(
        "H",
        "Found in our output",
        '"nothing found" must be written out',
        must_be_explicit=True,
    ),
    Section("I", "Provider contract", "the mirror of our consumer contract"),
    Section("J", "Questions back", "their open questions to us"),
)

# What we must send them (protocol §3).
#
# Outbound headings are prose written by a human ("## §3 · What I fixed on my
# side — drop these from your list"), not single letters, so these are matched
# by KEYWORD rather than by the anchored letter pattern the inbound sections
# use. Each entry's `keywords` are the alternatives that count as that section
# being present; matching is case-insensitive and looks only at heading lines,
# so a passing mention in body prose cannot satisfy a section.
#
# The first version of this checker matched on the internal key and rejected our
# own skeleton *and* the real round-4 file — a validator can be wrong in the
# direction of over-strictness too, and that direction is worse, because the fix
# people reach for is switching it off.
OUTBOUND_SECTIONS: tuple[Section, ...] = (
    Section(
        "Corrections",
        "Corrections",
        "anything we sent that was wrong, stated early",
        keywords=("correction",),
    ),
    Section(
        "Confirmations",
        "Confirmations",
        "their claims we checked, and how",
        keywords=("confirmation", "confirmed"),
    ),
    Section(
        "Fixed",
        "What we fixed",
        "so they can drop it from their list",
        keywords=("what i fixed", "what we fixed", "fixed on"),
    ),
    Section(
        "Requirements",
        "Requirements",
        "binding terms for the pin",
        keywords=("requirement",),
    ),
    Section(
        "Asks",
        "Behaviour asks",
        "separated from questions",
        keywords=("ask",),
    ),
    Section(
        "Questions",
        "Questions",
        "numbered, so they can answer numbered",
        keywords=("question",),
    ),
    Section(
        "NotAsking",
        "Explicitly not asking",
        "so they do not spend effort",
        keywords=("not asking",),
    ),
    Section(
        "ReturnSpec",
        "The return-file spec",
        "inline — they do not have this repo",
        keywords=("return file", "return-file"),
    ),
    Section(
        "Rigour",
        "The shared rigour bar",
        "both sides hold to it",
        keywords=("rigour", "rigor"),
    ),
)


def _heading_pattern(key: str) -> re.Pattern[str]:
    """Match a markdown heading introducing section ``key``.

    Lenient about decoration — ``## A``, ``### §A —``, ``## A. Pin``, ``**A**``
    all count — because the fork is a different project with its own habits and
    rejecting a complete file over a heading style would be theatre. Bounded
    quantifiers throughout, per the project rule.
    """
    esc = re.escape(key)
    return re.compile(
        rf"^\s{{0,3}}(?:#{{1,6}}\s*)?(?:\*\*)?(?:§\s*)?{esc}\b[.):\s—-]{{0,4}}",
        re.MULTILINE | re.IGNORECASE,
    )


def _section_body(text: str, key: str, all_keys: tuple[str, ...]) -> str | None:
    """Text under section ``key``, up to the next section heading. None if absent."""
    match = _heading_pattern(key).search(text)
    if match is None:
        return None
    start = match.end()
    end = len(text)
    for other in all_keys:
        if other == key:
            continue
        nxt = _heading_pattern(other).search(text, start)
        if nxt is not None:
            end = min(end, nxt.start())
    return text[start:end].strip()


# Phrases that make a "nothing to report" section explicit rather than silent.
_EXPLICIT_NOTHING = (
    "no change",
    "no changes",
    "unchanged",
    "nothing found",
    "nothing to report",
    "none found",
    "no issues",
    "identical",
)


def check_inbound(path: Path) -> list[str]:
    """Return a list of problems with a received cyanrip handshake file.

    Empty list means it satisfies the protocol. Never raises on content — a
    malformed file must produce a *report*, not a traceback, or the checker
    becomes something people stop running.
    """
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]

    if not text.strip():
        return [f"{path} is empty"]

    keys = tuple(s.key for s in INBOUND_SECTIONS)
    for section in INBOUND_SECTIONS:
        body = _section_body(text, section.key, keys)
        if body is None:
            problems.append(
                f"§{section.key} ({section.title}) is MISSING — {section.why}"
            )
            continue
        if len(body) < MIN_SECTION_CHARS:
            problems.append(
                f"§{section.key} ({section.title}) is present but has "
                f"{len(body)} chars of content — {section.why}"
            )
            continue
        if section.must_be_explicit:
            lowered = body.casefold()
            # Either it reports something substantial, or it explicitly says
            # there is nothing. What it may not do is trail off.
            says_nothing_explicitly = any(p in lowered for p in _EXPLICIT_NOTHING)
            if len(body) < 200 and not says_nothing_explicitly:
                problems.append(
                    f"§{section.key} ({section.title}) is short and does not "
                    f"explicitly state the null case — {section.why}"
                )
    return problems


_HEADING_LINE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.{1,200})$", re.MULTILINE)


def _headings(text: str) -> list[str]:
    """Every markdown heading's text, lower-cased.

    Only headings — a section is "present" when it has a heading, not when the
    word appears somewhere in a paragraph. Otherwise an outbound file that
    merely *mentions* corrections would pass the corrections check.
    """
    return [m.group("text").casefold() for m in _HEADING_LINE.finditer(text)]


def check_outbound(text: str) -> list[str]:
    """Return a list of problems with an outbound file we are about to send.

    Matched by heading keyword, not by exact title: the real files carry
    numbered, em-dashed headings written for a reader, and a checker that
    demanded an exact string would reject every genuine round. Strictness is
    spent on *presence of the section*, not on its wording.
    """
    problems: list[str] = []
    headings = _headings(text)
    for section in OUTBOUND_SECTIONS:
        needles = section.keywords or (section.title.casefold(),)
        if not any(n in heading for heading in headings for n in needles):
            problems.append(f"outbound is missing '{section.title}' — {section.why}")
    return problems


def _inbound_spec_markdown() -> str:
    """The inbound spec as a table, for pasting into the outbound file.

    Generated from ``INBOUND_SECTIONS`` rather than retyped, so the spec we ask
    them to satisfy is by construction the same one our checker enforces. Asking
    for a section we do not check, or checking one we never asked for, is the
    exact asymmetry that makes a protocol rot.
    """
    rows = "\n".join(
        f"| **{s.key}** | {s.title} — {s.why}"
        + (
            " **Must be stated explicitly; silence is ambiguous.**"
            if s.must_be_explicit
            else ""
        )
        + " |"
        for s in INBOUND_SECTIONS
    )
    return "| § | Contents |\n|---|---|\n" + rows


def emit_outbound(round_number: int) -> str:
    """Build a skeleton outbound handshake file for ``round_number``."""
    sections = "\n\n".join(
        f"## {s.title}\n\n<!-- {s.why} -->\n\nTODO" for s in OUTBOUND_SECTIONS[:-2]
    )
    return f"""# Platterpus → cyanrip fork · Round {round_number}

<!-- Skeleton from scripts/handshake.py. Every section below is required by
     docs/cyanrip-handshake.md §3; the checker will not let a round go out with
     one missing. Replace each TODO. -->

**What I need back:** one markdown file matching *The return-file spec* below.
I will verify every claim in it against the real parser and the committed
fixtures, then send a short verification file. **Neither project releases until
both directions are done.**

{sections}

## The return-file spec

One markdown file, these sections, in this order.

{_inbound_spec_markdown()}

**Then I owe you a verification file.** If I go quiet after your return file,
that is a bug in me — chase it. Silence leaves you unable to distinguish
"verified" from "not looked at yet".

## The shared rigour bar

<!-- both sides hold to it; see docs/cyanrip-handshake.md §5 -->

TODO
"""


def round_status(root: Path | None = None) -> list[str]:
    """Describe the state of every round found under ``docs/handshake/``.

    ``root`` overrides that directory so the OPEN and CLOSED branches can be
    exercised against a constructed state. Without it a test could only assert
    whatever the repo happens to contain today — which is exactly how the first
    version of this test broke: it pinned "round 4 is OPEN", and round 4 closed.
    A test that asserts today's state is a test that fails on progress.
    """
    base = root if root is not None else HANDSHAKE_DIR
    outbound, inbound, verified = (
        base / "outbound",
        base / "inbound",
        base / "verified",
    )
    lines: list[str] = []
    rounds: set[str] = set()
    for directory in (outbound, inbound, verified):
        if directory.is_dir():
            rounds.update(p.stem for p in directory.glob("round-*.md"))
    if not rounds:
        return ["no handshake rounds recorded under docs/handshake/"]
    for name in sorted(rounds):
        sent = (outbound / f"{name}.md").exists()
        back = (inbound / f"{name}.md").exists()
        was_verified = (verified / f"{name}.md").exists()
        state = "CLOSED" if (sent and back and was_verified) else "OPEN"
        lines.append(
            f"{name}: sent={'yes' if sent else 'NO'} "
            f"returned={'yes' if back else 'NO'} "
            f"verified={'yes' if was_verified else 'NO'}  -> {state}"
        )
    if any(line.endswith("OPEN") for line in lines):
        lines.append("")
        lines.append("A round is OPEN: do not release, and do not switch the pin.")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--emit", type=int, metavar="ROUND", help="print an outbound skeleton"
    )
    group.add_argument(
        "--check", type=Path, metavar="FILE", help="validate an inbound file"
    )
    group.add_argument("--status", action="store_true", help="report the round state")
    group.add_argument(
        "--release-gate",
        action="store_true",
        help="exit non-zero if any round is open (for the release workflow)",
    )
    args = parser.parse_args(argv)

    if args.emit is not None:
        sys.stdout.write(emit_outbound(args.emit))
        return 0
    if args.status:
        for line in round_status():
            sys.stdout.write(line + "\n")
        return 1 if any(ln.endswith("OPEN") for ln in round_status()) else 0
    if args.release_gate:
        # THE release gate. `--status` reports and also exits non-zero, which
        # made it look like this already existed — but nothing on the release
        # path ran it, and the only thing enforcing "no release while a round is
        # open" was a unit test that reddened *every* commit the moment a round
        # was opened. That is the wrong place twice over: it blocked ordinary
        # work, and it did not block a release, because `release.yml` never
        # called it. This subcommand exists so the workflow can.
        lines = round_status()
        open_rounds = [ln for ln in lines if ln.endswith("OPEN")]
        if not open_rounds:
            sys.stdout.write("handshake: every round is closed — release allowed\n")
            return 0
        sys.stderr.write(
            "handshake: a round is OPEN, so this release is blocked "
            "(docs/cyanrip-handshake.md §7 — both directions must be verified "
            "before either project releases):\n"
        )
        for line in open_rounds:
            sys.stderr.write(f"  - {line}\n")
        return 1

    problems = check_inbound(args.check)
    if not problems:
        sys.stdout.write(
            f"{args.check}: satisfies the protocol (all sections present)\n"
        )
        return 0
    sys.stderr.write(f"{args.check}: {len(problems)} problem(s)\n")
    for problem in problems:
        sys.stderr.write(f"  - {problem}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
