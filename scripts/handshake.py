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
  back, and **what our verification decided** — read off ``docs/handshake/``.

Neither direction is optional and neither is the default: a round is open until
both files exist *and* our verification file **declares GO**. The verdict, not
the file's existence, is what closes a round — round 7's verification is a
deliberate mid-round ``**HOLD**`` and a presence-only check reported it CLOSED,
which would have let a release through with the round open.

Usage::

    python scripts/handshake.py --emit 5                 # start round 5 outbound
    python scripts/handshake.py --check docs/handshake/inbound/round-4.md
    python scripts/handshake.py --status
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_REPO_ROOT: Path = Path(__file__).resolve().parents[1]
HANDSHAKE_DIR: Path = _REPO_ROOT / "docs" / "handshake"
OUTBOUND_DIR: Path = HANDSHAKE_DIR / "outbound"
INBOUND_DIR: Path = HANDSHAKE_DIR / "inbound"
VERIFIED_DIR: Path = HANDSHAKE_DIR / "verified"
PROTOCOL_DOC: Path = _REPO_ROOT / "docs" / "cyanrip-handshake.md"
#: The SHARED wire-format specification — the same document in both repositories,
#: adopted verbatim from the fork in round 7 lap 4. Neither project owns it, and a
#: change to it is a protocol version bump both sides must ship before the next
#: close. Our gate is measured against *this* file, not against our own paraphrase
#: of it: checking a copy against a copy is how two vocabularies happen.
PROTOCOL_SPEC: Path = _REPO_ROOT / "docs" / "handshake-protocol.md"

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
#
# EVERY INBOUND SECTION CARRIES `keywords`, AND THAT IS NOT DECORATION. A
# single-letter key matched positionally validates the *label*, not the subject,
# and it failed in both directions on round 6:
#
#   * §I ("Provider contract") passed because a line of their prose began
#     "I wrote, of your continuation-line sweep:". The provider contract was in
#     that file — as Appendix 2 — so the check reported the right answer for the
#     wrong reason and would have passed with the appendix deleted.
#   * §G ("Revert-proof") passed because they lettered an unrelated section
#     "## G. Asks back". The word "revert" appears **zero** times in the whole
#     file. The checker reported 1 problem; there were 2.
#
# So the letter now has to be a real heading, and the section's *subject* has to
# appear somewhere in the document. The letter answers "did they label it", the
# keywords answer "did they write it", and only the pair is a check. This is the
# "can it be satisfied by finding nothing?" question applied to our own gate —
# which is the one place it had never been asked.
INBOUND_SECTIONS: tuple[Section, ...] = (
    Section(
        "A",
        "Pin",
        "repo, branch, commit SHA, exact --version output",
        keywords=("pin", "commit"),
    ),
    Section(
        "B",
        "Answers",
        "every question, each marked measured / read-from-source / unverified",
        keywords=("measured", "read from source", "read-from-source"),
    ),
    Section(
        "C",
        "Changes",
        "one row per commit, flagging any that alter log text",
        keywords=("commit", "release contains", "changes"),
    ),
    Section(
        "D",
        "Log-format delta",
        '"no changes" must be written out — silence is ambiguous',
        must_be_explicit=True,
        keywords=("log-format", "log format"),
    ),
    Section(
        "E",
        "Golden log",
        "regenerated + the command, if D changed",
        keywords=("golden",),
    ),
    Section(
        "F",
        "Verification",
        "proven (with how) vs not proven (with what it takes)",
        keywords=("verif",),
    ),
    Section(
        "G",
        "Revert-proof",
        "per behavioural fix; a 'no' is fine, a blank is not",
        keywords=("revert",),
    ),
    Section(
        "H",
        "Found in our output",
        '"nothing found" must be written out',
        must_be_explicit=True,
        keywords=("found in", "nothing found", "your output", "our output"),
    ),
    Section(
        "I",
        "Provider contract",
        "the mirror of our consumer contract",
        keywords=("provider contract",),
    ),
    Section(
        "J",
        "Questions back",
        "their open questions to us",
        keywords=("question", "ask"),
    ),
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

    **A heading marker is now REQUIRED** (``#``, ``**`` or ``§``). The first
    version accepted a bare letter at the start of a line, which meant an
    ordinary English sentence satisfied a required section: their round-6 file's
    §I was credited to the line *"I wrote, of your continuation-line sweep:"*.
    Prose beginning with "A ", "I " or "We " is normal writing, and a validator
    that reads it as structure launders a missing section as a present one.
    """
    esc = re.escape(key)
    return re.compile(
        rf"^\s{{0,3}}(?:#{{1,6}}\s*(?:§\s*)?|\*\*\s*(?:§\s*)?|§\s*)"
        rf"{esc}\b[.):\s—-]{{0,4}}",
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


def _safe_read(path: Path) -> str:
    """File text, or ``""``. Used by probes that run *before* the real read, whose
    job is to report an unreadable file properly."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def check_inbound(*paths: Path) -> list[str]:
    """Return a list of problems with a received cyanrip handshake round.

    Empty list means it satisfies the protocol. Never raises on content — a
    malformed file must produce a *report*, not a traceback, or the checker
    becomes something people stop running.

    Several paths are treated as **one round delivered in parts**, which round 6
    was: the return file, then an amendment hours later that moved the pin
    because the first pin returned silence on disc images. Requiring the
    amendment to restate all ten sections would make the honest thing (send the
    correction immediately) score worse than the dangerous thing (fold it into
    the next round). Sections are satisfied by any file in the set; the *newest*
    file wins where both speak, which is what "supersedes" means.
    """
    problems: list[str] = []
    if not paths:
        return ["no inbound file given"]
    # The shared wire header (protocol §8.2), required from round 7 on. Checked
    # per-file rather than across the set: a header is per-document metadata, not
    # a section a later amendment can supply on an earlier file's behalf.
    for path in paths:
        num = round_number(path)
        if num is not None and num not in THEIR_PRE_HEADER_ROUNDS:
            problems.extend(check_wire_header(path, expect_from="cyanrip-fork"))
    # A MID-ROUND LAP IS NOT A FULL ROUND FILE, and demanding all ten sections of
    # one is the over-strictness this checker's own notes warn about — the failure
    # whose fix people reach for is switching the checker off. A round opens with a
    # complete file (lap 1) and then both sides exchange *replies*, each scoped to
    # what it answers; round 7 lap 2 legitimately has no golden log and no §C
    # commit table because nothing about those changed in that exchange.
    #
    # `HANDSHAKE-LAP` is what makes this decidable rather than a judgement, which
    # is the field earning its place: if every file in the set declares a lap above
    # 1, the section sweep does not apply. A set containing a lap-1 file is a full
    # round and is swept as before.
    laps = [wire_fields(_safe_read(path)).get("HANDSHAKE-LAP") for path in paths]
    if laps and all(lap and lap.strip().isdigit() and int(lap) > 1 for lap in laps):
        if not problems:
            return []
        return problems
    texts: list[str] = []
    for path in paths:
        try:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            return [f"cannot read {path}: {exc}"]
        if not texts[-1].strip():
            return [f"{path} is empty"]
    text = "\n\n".join(texts)

    keys = tuple(s.key for s in INBOUND_SECTIONS)
    lowered_all = text.casefold()
    for section in INBOUND_SECTIONS:
        body = _section_body(text, section.key, keys)
        # The SUBJECT floor, checked against the whole document rather than the
        # section body. A round may reletter its sections — the fork's round 6
        # ran A–H with the provider contract as an appendix — and rejecting a
        # complete file over its numbering would be theatre. What may not happen
        # is a required subject going unwritten while a same-lettered section
        # covers something else. "revert" appearing zero times in a file whose
        # §G is headed "Asks back" is a missing section, not a naming quibble.
        subject_written = not section.keywords or any(
            k in lowered_all for k in section.keywords
        )
        if not subject_written:
            problems.append(
                f"§{section.key} ({section.title}) is ABSENT — none of "
                f"{list(section.keywords)} appears anywhere in the file"
                + (
                    f", though a section is lettered {section.key}"
                    if body is not None
                    else ""
                )
                + f" — {section.why}"
            )
            continue
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


#: Which checker a file belongs to, decided by the directory it lives in.
#: Direction is a property of *where the file is*, not of what it says, because
#: the wire header is exactly the thing a malformed file gets wrong — routing on
#: `HANDSHAKE-FROM` would send a file with a mistyped header to the checker that
#: cannot see the mistake. The header is still checked, just not trusted to route.
_DIRECTION_BY_DIR: Final[dict[str, str]] = {
    "outbound": "outbound",
    "inbound": "inbound",
    "verified": "verified",
}


def direction_of(path: Path) -> str:
    """Whether ``path`` is a file we sent, one we received, or a verification.

    Falls back to ``HANDSHAKE-FROM`` only when the file is not in one of the three
    known directories — someone checking a draft in a scratch folder should still
    get the right spec rather than a confusing wall of inbound-only complaints.
    """
    by_dir = _DIRECTION_BY_DIR.get(path.parent.name)
    if by_dir is not None:
        return by_dir
    sender = wire_fields(_safe_read(path)).get("HANDSHAKE-FROM", "").strip()
    return "inbound" if sender == "cyanrip-fork" else "outbound"


def check_outbound_paths(*paths: Path) -> list[str]:
    """Validate files **we** are about to send, against the outbound spec.

    This exists because :func:`check_outbound` had no caller. It was written,
    tested as a function, and never wired to the command line, so ``--check`` ran
    the *inbound* spec against everything — and an outbound file checked that way
    reports six sections "missing" that the outbound spec never asks for, plus a
    wrong-sender complaint. A reviewer seeing seven problems on a correct file
    learns to distrust the checker, which is worse than having no checker.

    The same shape as the ``RipHandle.cancel`` that was fully implemented and
    called from nowhere: grep for a call site before believing a capability is
    reachable.
    """
    problems: list[str] = []
    if not paths:
        return ["no outbound file given"]
    for path in paths:
        num = round_number(path)
        # Rounds 1-6 predate the shared wire header; requiring it of them would
        # fail files that were correct when sent.
        if num is not None and num not in OUR_PRE_HEADER_ROUNDS:
            problems.extend(check_wire_header(path, expect_from="platterpus"))
        text = _safe_read(path)
        if not text.strip():
            problems.append(f"{path} is empty")
            continue
        problems.extend(check_outbound(text))
    return problems


def check_verification_paths(*paths: Path) -> list[str]:
    """Validate a verification file — the one that actually closes a round.

    A verification's job is narrower than a round file's: declare a verdict, and
    declare it in the bolded form the gate reads. The failure this catches is the
    one the protocol calls out as worse than a missing section — a file that reads
    like a close to a human and carries no verdict a gate can find.
    """
    problems: list[str] = []
    if not paths:
        return ["no verification file given"]
    for path in paths:
        num = round_number(path)
        if num is not None and num not in OUR_PRE_HEADER_ROUNDS:
            problems.extend(check_wire_header(path, expect_from="platterpus"))
        text = _safe_read(path)
        if not text.strip():
            problems.append(f"{path} is empty")
            continue
        if verification_verdict(text) is None:
            problems.append(
                f"{path.name}: no verdict — a verification file must state a "
                "bolded '**GO on <pin>' or '**HOLD on <pin>' at a line start. "
                "A missing verdict fails closed and leaves the round OPEN."
            )
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


def _fork_pin() -> str:
    """The pinned fork commit, read from the product rather than retyped here.

    A skeleton that names a pin the code does not build is the drift this whole
    protocol exists to prevent, so the value comes from `deps/fork_source.py`.
    """
    from platterpus.deps import fork_source  # noqa: PLC0415

    return fork_source.FORK_PIN


def _fork_banner() -> str:
    """The exact banner the pinned build prints. Same reason as :func:`_fork_pin`."""
    from platterpus.deps import fork_source  # noqa: PLC0415

    return fork_source.FORK_EXPECTED_BANNER


def emit_outbound(round_number: int) -> str:
    """Build a skeleton outbound handshake file for ``round_number``."""
    sections = "\n\n".join(
        f"## {s.title}\n\n<!-- {s.why} -->\n\nTODO" for s in OUTBOUND_SECTIONS[:-2]
    )
    from platterpus import __version__ as _app_version  # noqa: PLC0415

    # THE GENERATOR MUST EMIT A FILE THE CHECKER ACCEPTS, and it did not: this line
    # was absent, so `--emit N | --check` reported "missing required field
    # HANDSHAKE-PROTOCOL (§3)" against our own skeleton. `handshake_filename` exists
    # because a hand-typed name is a third description of a fact — and the header the
    # same instruction points at was hand-maintained here and had drifted from
    # `REQUIRED_WIRE_FIELDS` in the same file. Found in lap 21 by running the emitter
    # through the checker; `test_the_emitted_skeleton_satisfies_our_own_checker` is
    # the standing version of that, derived from the required-field tuple rather than
    # from this list, so the next added field cannot go missing here quietly.
    header = "\n".join(
        [
            f"HANDSHAKE-PROTOCOL: {PROTOCOL_VERSION}",
            f"HANDSHAKE-ROUND: {round_number}",
            "HANDSHAKE-LAP: 1",
            "HANDSHAKE-FROM: platterpus",
            "HANDSHAKE-VERDICT: OPEN",
            f"HANDSHAKE-APP-VERSION: platterpus {_app_version}",
            f"HANDSHAKE-RIPPER-VERSION: {_fork_banner()}",
            f"HANDSHAKE-PIN: {_fork_pin()}",
            "CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ <commit>",
        ]
    )
    return f"""{header}

# Platterpus → cyanrip fork · Round {round_number}

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


# --- The file naming convention -----------------------------------------------
#
# **Why this needed fixing (maintainer directive, 2026-08-04: "agree on a naming
# convention for the handshake files and both use it").**
#
# The old scheme was `round-N` plus the next free letter, and the letter encoded
# nothing. What that produced:
#
#   * `inbound/round-7f.md` is **lap 12** while `verified/round-7f.md` is **lap 10** —
#     the same suffix means different laps depending on the directory;
#   * `inbound/round-7d.md` and `verified/round-7d.md` are *both* lap 7, by coincidence;
#   * filing a received file means finding "the next free letter", and doing that
#     wrong **overwrites a previous lap**. It happened in this session: lap 12 was
#     copied over `round-7c.md`, which was lap 4, and had to be restored from git.
#
# The fix is that the name states the two facts the wire header already declares, so
# the filename and the header are two descriptions of one thing — and a test asserts
# they agree, which is the only reason a second description is safe to have.
#
# ``round-07-lap-16.md``
#
#   * zero-padded to two digits so a lexical sort is chronological. At round or lap
#     100 the width goes to three **everywhere**, as one deliberate migration; the
#     conformance test fails on mixed widths rather than letting the sort rot;
#   * direction comes from the directory (``inbound`` / ``outbound`` / ``verified``),
#     not the name, and ``HANDSHAKE-FROM`` must agree with it;
#   * **no amendment letters.** An amendment is a new lap. Both projects already
#     work that way — the fork has issued sixteen laps in one round — and a lap
#     number is a fact both sides can state, where "the next letter" is a fact only
#     the filer knows.
#
# Files that predate the lap header keep their old names and are grandfathered by
# the same round-number rule as ``OUR_PRE_HEADER_ROUNDS``: the convention binds a
# file **that declares a lap**, which is derivable rather than a list to maintain.

#: The canonical form: ``round-07-lap-16``.
_LAP_NAME = re.compile(r"^round-(?P<round>\d{2,4})-lap-(?P<lap>\d{2,4})$")

#: The grandfathered form: ``round-6``, or ``round-6b`` for an amendment sent after
#: the round's main file. Retained for the pre-lap-header files only — see above.
_ROUND_NAME = re.compile(r"^round-(?P<number>\d{1,4})(?P<amendment>[a-z]{0,2})$")

#: Zero-pad width. Bump to 3 only as a whole-directory migration.
NAME_PAD: int = 2


def handshake_filename(round_number_: int, lap: int) -> str:
    """The canonical file name for a round and lap. **Generate, never hand-type.**

    A name typed by hand is a third description of a fact the header already states
    twice, and the whole point of the convention is that there are two and they are
    checked against each other.
    """
    return f"round-{round_number_:0{NAME_PAD}d}-lap-{lap:0{NAME_PAD}d}.md"


def name_round_and_lap(path: Path) -> tuple[int, int] | None:
    """``(round, lap)`` from a canonical name, or None if it is not one.

    None covers both "a grandfathered name" and "not a handshake file at all"; the
    caller decides which matters. Never raises — an unrelated file dropped in the
    directory must not take the status report down with it.
    """
    match = _LAP_NAME.match(path.stem)
    if match is None:
        return None
    return int(match.group("round")), int(match.group("lap"))


def round_number(path: Path) -> int | None:
    """The round a handshake file belongs to, or None if the name is not one.

    Accepts the canonical ``round-07-lap-16`` form and the grandfathered
    ``round-6`` / ``round-6b``. Returning None rather than raising matters: an
    unrelated file dropped in the directory must not take the status report down
    with it.
    """
    canonical = name_round_and_lap(path)
    if canonical is not None:
        return canonical[0]
    match = _ROUND_NAME.match(path.stem)
    return int(match.group("number")) if match else None


#: The verdict a verification file declares, as a bolded marker at the start of
#: a line: ``**GO on pin `abc1234`.**`` or ``**HOLD on `abc1234`.``. Anchored to
#: the line start (with the optional ``**``) on purpose — a `GO`/`HOLD` appearing
#: mid-sentence is *prose about* the verdict, not the verdict. Round 7's file
#: says "not a closing GO" in its second paragraph and declares **HOLD** on line
#: 7; a pattern that scanned anywhere in the text would read that file as GO.
_VERDICT_LINE = re.compile(r"^[ \t]*(?:\*\*)?(?P<verdict>GO|HOLD)\b", re.MULTILINE)

#: Rounds whose verification file predates the ``**GO``/``**HOLD`` convention.
#: Rounds 1–3 were *reconstructed retrospectively* in one sitting (2026-08-02)
#: while backfilling the correspondence record — they were closed long before
#: there was a marker to write. Grandfathered by number, explicitly, rather than
#: by "treat a missing verdict as GO", because that fallback is the whole defect
#: this constant exists to avoid: it would silently close any future round whose
#: verification forgot to state a verdict. This set may shrink, never grow — a
#: test asserts exactly that.
RETROSPECTIVE_ROUNDS: frozenset[int] = frozenset({1, 2, 3})


#: The round currently in flight. **The release gate's floor** — it is counted as
#: a round whether or not any file for it has been committed yet.
#:
#: **Why a constant and not "whatever files exist".** Round 8 ran for seven laps
#: with its files uncommitted, so ``round-*.md`` found nothing for it and the
#: gate reported every *filed* round CLOSED — release allowed. Four releases went
#: out during an open round, and the gate was not wrong about anything it could
#: see. The empty-record branch above did not fire either: it only triggers when
#: there are **no** rounds at all, and rounds 1-7 were sitting right there.
#:
#: So this is the same defect the empty-record branch already exists to prevent,
#: arriving one level up: *an in-flight round with no files is indistinguishable
#: from no round*. A committed number cannot be forgotten the way a commit can,
#: and ``--emit`` refuses a round above it so opening one forces the bump.
#:
#: Staleness fails in the SAFE direction: a value left behind reports a closed
#: round as open and blocks a release, which is a conversation. The other
#: direction ships.
CURRENT_ROUND: Final[int] = 8


# --- The shared wire format (protocol §8) -----------------------------------
#
# ONE language, both repos. The fork introduced a machine-readable header block in
# round 7 lap 2 alongside their own release gate; we had bolded prose. Two gates,
# two vocabularies, one protocol — each able to read only its own files, which is
# exactly what `CLAUDE.md` rule 12's "this rule lives in both repos" exists to
# prevent, arriving in the tooling instead of the prose. Their form wins on the
# merits (machine-readable, survives rewording, a round number *in* the file
# cannot silently disagree with the filename) and is adopted here.
#
# Specified in `docs/cyanrip-handshake.md` §8 and reproduced verbatim in every
# round file from round 7 lap 3 on, so a reader of either repo has the spec.

#: Any ``KEY: value`` field at column 0. Deliberately generic: unknown fields are
#: *ignored* by both parsers, so either side can add one without breaking the
#: other. Column-0 anchored because a round file legitimately quotes ``GO`` in
#: prose and block-quotes example headers — their lap-2 file does both, on purpose,
#: as its own first test.
_WIRE_FIELD = re.compile(
    r"^(?P<key>[A-Z][A-Z0-9-]*):[ \t]*(?P<value>\S.*?)[ \t]*$", re.MULTILINE
)

#: A fenced code block (``` or ~~~), stripped BEFORE any field matching.
_FENCE_BLOCK = re.compile(
    r"^(?P<fence>```+|~~~+)[^\n]*\n.*?^(?P=fence)[ \t]*$\n?",
    re.MULTILINE | re.DOTALL,
)

#: The protocol version this gate implements (`PROTOCOL.md`). A file declaring a
#: **higher** number is refused rather than guessed at: we cannot know which of
#: that version's rules we are silently not applying.
PROTOCOL_VERSION: int = 2

#: Sentinel for a field declared more than once with conflicting values. A real
#: value can never equal it, and every consumer treats it as "not closed".
#: PROTOCOL.md §2 rule 3 — do not take the first, do not take the last, refuse.
AMBIGUOUS: str = "<ambiguous: declared more than once>"

#: `GO` is the only closing value, and on its own it is still not a close.
AFFIRMATIVE: str = "GO"

#: The closed verdict vocabulary (§4). Anything outside it is "not closed" — an
#: unrecognised value is not agreement and not an error to skip past.
VERDICT_VOCABULARY: frozenset[str] = frozenset({"OPEN", "HOLD", "GO"})

#: The fields every file must declare, either side (§3).
REQUIRED_WIRE_FIELDS: tuple[str, ...] = (
    "HANDSHAKE-PROTOCOL",
    "HANDSHAKE-ROUND",
    "HANDSHAKE-LAP",
    "HANDSHAKE-FROM",
    "HANDSHAKE-VERDICT",
    "HANDSHAKE-APP-VERSION",
    "HANDSHAKE-RIPPER-VERSION",
    "HANDSHAKE-PIN",
)

#: The additional fields a **closing** file must carry (§5). A `GO` without these
#: is not a close: an agreement that does not name its parties cannot be quoted
#: later, and a round that closed with nothing tested is a release nobody checked.
REQUIRED_CLOSE_FIELDS: tuple[str, ...] = (
    "HANDSHAKE-PEER-VERDICT",
    "HANDSHAKE-OUR-VERSION",
    "HANDSHAKE-OUR-PIN",
    "HANDSHAKE-PEER-VERSION",
    "HANDSHAKE-PEER-PIN",
    "HANDSHAKE-TESTED",
)

#: The optional field that names a build designated to *gather* the evidence a
#: close needs (§6a). It is **not** a pin agreement and must never be read as one.
#:
#: Why the protocol needed it: our own rules deadlocked. A close requires
#: `HANDSHAKE-TESTED`; hardware evidence only comes from the rig; the rig installs
#: the pinned build; neither side may move the pin while a round is open — so the
#: rig always runs the build *without* the changes under review, and the round can
#: never close. Every step is a rule both projects hold and together they are
#: unsatisfiable. The fix is to stop conflating "the build we agreed on" with "the
#: build we are testing".
#:
#: Consequence for this gate, and the whole reason the constant exists here rather
#: than being ignored as an unknown field: a file carrying a test pin must be no
#: closer to closing a round than the same file without one (rows C17/C18).
TEST_PIN_FIELD: str = "HANDSHAKE-TEST-PIN"

#: Rounds recorded before the header existed, exempted **by number** — never by a
#: rule like "a missing verdict is fine for old rounds", which is the fallback that
#: lets any new round close by omission. Both sets may shrink, never grow.
THEIR_PRE_HEADER_ROUNDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 7})
OUR_PRE_HEADER_ROUNDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 7})


def _strip_fences(text: str) -> str:
    """Remove fenced code blocks, so an *illustrated* field is not a declaration.

    **The third bait shape, and neither project had it.** A declaration is a
    statement the file *makes*, not one it *quotes* — and examples, templates and
    conformance tables legitimately carry field lines at column 0. The fork's gate
    read the example block in our own lap-3 §1 and compiled an illustrated
    ``HANDSHAKE-PEER-VERSION`` into their binary as a fact about us.

    **Ours had the same hole and it did not fire only by luck:** our lap-3 file
    illustrates ``HANDSHAKE-VERDICT: HOLD`` inside a fence *and* declares ``HOLD``
    for real, so the duplicate resolved to the right answer for no good reason. Our
    suite even asserted the **wrong** behaviour — that a fenced field should match
    — with a confident comment about not parsing markdown. It was wrong.

    Newlines are preserved so nothing that depends on line numbers shifts.
    """

    def blank(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return _FENCE_BLOCK.sub(blank, text)


def wire_fields(text: str) -> dict[str, str]:
    """Every column-0 ``KEY: value`` declaration, fenced examples excluded.

    A key declared twice with *different* values maps to :data:`AMBIGUOUS`.
    """
    seen: dict[str, str] = {}
    for match in _WIRE_FIELD.finditer(_strip_fences(text)):
        key, value = match.group("key"), match.group("value")
        if key in seen and seen[key] != value:
            seen[key] = AMBIGUOUS
        elif key not in seen:
            seen[key] = value
    return seen


def wire_verdict(text: str) -> str | None:
    """The declared verdict, or None if the file states none.

    ``GO`` is the only affirmative. ``OPEN``, ``HOLD``, an unrecognised value and
    an ambiguous double declaration all mean *not closed*.
    """
    value = wire_fields(text).get("HANDSHAKE-VERDICT")
    if value is None:
        return None
    if value == AMBIGUOUS:
        return "HOLD"
    token = value.split()[0] if value.split() else ""
    if token == AFFIRMATIVE:
        return AFFIRMATIVE
    return token if token in VERDICT_VOCABULARY else "HOLD"


def declared_round(text: str) -> int | None:
    """The round a file *declares*, or None. Independent of its filename.

    `round_number()` reads the name; this reads the header. Both exist because §3
    requires them to agree and a check needs each separately to say so.
    """
    value = wire_fields(text).get("HANDSHAKE-ROUND")
    if value is None or value == AMBIGUOUS:
        return None
    try:
        return int(value.split()[0])
    except (ValueError, IndexError):
        return None


def close_blockers(text: str, round_hint: int | None = None) -> list[str]:
    """Why this file does not close a round. Empty list means it does.

    Separate from :func:`wire_verdict` because "did they say GO" and "is that GO
    sufficient" are different questions, and §5 makes the second the operative
    test. The gate must name **which** field is absent rather than refusing
    without a reason.
    """
    fields = wire_fields(text)
    verdict = fields.get("HANDSHAKE-VERDICT")
    if verdict is None:
        return ["no HANDSHAKE-VERDICT declared (§2 rule 4)"]
    if verdict == AMBIGUOUS:
        return ["HANDSHAKE-VERDICT declared more than once (§2 rule 3)"]
    token = verdict.split()[0] if verdict.split() else ""
    if token != AFFIRMATIVE:
        if token not in VERDICT_VOCABULARY:
            return [f"unrecognised verdict {token!r} (§4)"]
        return [f"verdict is {token}, not GO"]

    blockers: list[str] = []
    # THE IDENTITY FIELDS ARE PART OF A CLOSE, and this is where they were missing.
    #
    # `check_inbound` validated them; the *gate* never did. So a round-8 file
    # declaring GO with every §5 close field and **none** of `HANDSHAKE-FROM` /
    # `-APP-VERSION` / `-RIPPER-VERSION` / `-PIN` closed the round. Our lap-5 reply
    # told the fork "all four of our v1 additions required — yes", which was true of
    # one function and false of the one that decides releases: one half of a
    # two-half check, again.
    #
    # Found because the fork had the identical gap — *"our gate parsed all four and
    # enforced none"* — reported it in their lap 4, and in lap 6 said plainly that
    # our claim was a code-reading claim with no conformance row behind it. It was.
    # Rows C9/C10 now exercise it (`tests/test_handshake_conformance.py`).
    #
    # Round-gated: rounds in the grandfather set predate the header entirely, and
    # demanding fields of a file written before the spec would refuse history.
    # `round_hint` is the round the CALLER knows this file belongs to — from its
    # directory and filename. It matters because the pre-header rounds have no
    # header at all, so reading the round out of the text returns None for exactly
    # the files the exemption exists for. Without the hint this over-fired and
    # reported rounds 1-6 as OPEN: a grandfather clause keyed on a field the
    # grandfathered files do not have. An unknown round is treated as exempt —
    # a file we cannot place is not a file we can hold to a later spec.
    num = round_hint if round_hint is not None else declared_round(text)
    grandfathered = num is None or num in (
        OUR_PRE_HEADER_ROUNDS | THEIR_PRE_HEADER_ROUNDS
    )
    if not grandfathered:
        for key in REQUIRED_WIRE_FIELDS:
            value = fields.get(key)
            if value is None:
                blockers.append(
                    f"a closing file must declare {key} (§3) — an agreement that "
                    "does not name its parties cannot be quoted later"
                )
            elif value == AMBIGUOUS:
                blockers.append(f"{key} declared more than once (§2 rule 3)")
    for key in REQUIRED_CLOSE_FIELDS:
        value = fields.get(key)
        if value is None:
            blockers.append(f"a closing file must declare {key} (§5)")
        elif value == AMBIGUOUS:
            blockers.append(f"{key} declared more than once (§2 rule 3)")
    peer = fields.get("HANDSHAKE-PEER-VERDICT")
    if peer is not None and peer != AMBIGUOUS and peer.split()[:1] != [AFFIRMATIVE]:
        # "They did not object" is never "they agreed" — and the peer verdict is
        # TRANSCRIBED, not judged, so a peer HOLD written down honestly must block.
        blockers.append(f"peer verdict is {peer!r}, not GO (§5)")
    # A TEST PIN IS NOT A PIN AGREEMENT (§6a, row C18). A test pin may accompany a
    # valid close — that is the normal sequence, since the evidence a close cites
    # was gathered on it — but it must never *substitute* for `HANDSHAKE-PIN`. The
    # failure this refuses is a file that names only the build it tested and closes
    # the round on it, moving the production pin to something never agreed.
    #
    # Deliberately checked here rather than left to the required-field sweep above:
    # that sweep is round-gated by the grandfather clause, and a test pin is a v2
    # addition that can only appear on files written after it existed.
    test_pin = fields.get(TEST_PIN_FIELD)
    if test_pin is not None and test_pin != AMBIGUOUS:
        agreed = fields.get("HANDSHAKE-PIN")
        if agreed is None or agreed == AMBIGUOUS:
            blockers.append(
                f"{TEST_PIN_FIELD} is declared but HANDSHAKE-PIN is not (§6a) — a "
                "test pin names the build that gathered the evidence, never the "
                "build being agreed to, and it must not be read as one"
            )
    return blockers


def protocol_refusal(text: str) -> str | None:
    """A reason to refuse the file on protocol-version grounds, or None."""
    declared = wire_fields(text).get("HANDSHAKE-PROTOCOL")
    if declared is None:
        return None
    if declared == AMBIGUOUS:
        return "HANDSHAKE-PROTOCOL declared more than once"
    try:
        version = int(declared.split()[0])
    except (ValueError, IndexError):
        return f"HANDSHAKE-PROTOCOL: {declared!r} is not an integer"
    if version > PROTOCOL_VERSION:
        return (
            f"file declares protocol v{version}; this gate implements "
            f"v{PROTOCOL_VERSION} — refusing rather than guessing which rules it "
            "is not applying (§3)"
        )
    return None


def check_wire_header(path: Path, *, expect_from: str | None = None) -> list[str]:
    """Validate a handshake file's header against §2/§3. Returns problems.

    Reports rather than raises: a validator that crashes is one people stop
    running.
    """
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path.name}: unreadable ({exc})"]

    # A version we do not implement is refused first and alone: reporting field
    # problems against rules we may be applying wrongly would be noise.
    refusal = protocol_refusal(text)
    if refusal:
        return [f"{path.name}: {refusal}"]

    fields = wire_fields(text)
    for key in REQUIRED_WIRE_FIELDS:
        value = fields.get(key)
        if value is None:
            problems.append(f"{path.name}: missing required field {key} (§3)")
        elif value == AMBIGUOUS:
            problems.append(f"{path.name}: {key} declared more than once (§2 rule 3)")

    verdict = fields.get("HANDSHAKE-VERDICT")
    if verdict is not None and verdict != AMBIGUOUS:
        token = verdict.split()[0] if verdict.split() else ""
        if token not in VERDICT_VOCABULARY:
            problems.append(
                f"{path.name}: verdict {token!r} is outside the vocabulary "
                f"{sorted(VERDICT_VOCABULARY)} (§4) — an unrecognised value is "
                "not agreement"
            )

    # The declared round must match the filename's: a bookkeeping error, not a
    # reinterpretation (§3). The one check a filename convention cannot self-make.
    declared = fields.get("HANDSHAKE-ROUND", "")
    named = round_number(path)
    if declared and declared != AMBIGUOUS and named is not None:
        try:
            if int(declared) != named:
                problems.append(
                    f"{path.name}: declares HANDSHAKE-ROUND: {declared} but its "
                    f"name says round {named} (§3)"
                )
        except ValueError:
            problems.append(
                f"{path.name}: HANDSHAKE-ROUND: {declared!r} is not an integer"
            )

    if expect_from and fields.get("HANDSHAKE-FROM") not in (None, expect_from):
        problems.append(
            f"{path.name}: HANDSHAKE-FROM is {fields['HANDSHAKE-FROM']!r}, expected "
            f"{expect_from!r} for a file in this directory"
        )

    # A `GO` that cannot close is worth saying at check time, not only at gate
    # time: the author of a closing file should learn what is missing while they
    # are still writing it.
    if verdict is not None and verdict != AMBIGUOUS:
        if verdict.split()[:1] == [AFFIRMATIVE]:
            problems.extend(
                f"{path.name}: declares GO but {b}"
                for b in close_blockers(text)
                if not _is_peer_verdict_blocker(b)
            )
    return problems


#: The one close-blocker that is NOT the author's to fix, and folding it into
#: `check_wire_header`'s problems made a first GO unexpressible.
#:
#: **THE GO-FIRST DEADLOCK, and it was ours.** Lap 23 was written with
#: ``HANDSHAKE-VERDICT: GO`` and `test_our_own_committed_files_satisfy_the_format_we_publish`
#: refused it: *"declares GO but peer verdict is 'HOLD', not GO (§5)"*. We reported that as a
#: hole in the shared spec. The fork tested **their** loader against the same case in their
#: lap 24 §B1 — accepted as well-formed, correctly refused as a close — and they were right:
#: our *gate* was never wrong (`round_status` requires both verdicts and `--release-gate`
#: exits 1), only this checker was, because it conflated **well-formed** with **closable**.
#:
#: Both sides need a closable GO; a GO is closable only once the peer has GO'd; so under the
#: strict reading neither side can go first and **a round that reaches agreement has no way to
#: record it.** Round 6 closed before the wire header existed, so round 7 was the first to
#: reach a close attempt under v2 and the first to hit this.
#:
#: The fix is narrow on purpose. **Every other blocker stays a problem**, because every other
#: blocker is the author's own gap — a missing identity field, no ``HANDSHAKE-TESTED``. The
#: peer's verdict is the one thing the author cannot fix by editing their own file, so
#: reporting it as a defect in that file is a category error. §5's intent survives intact:
#: `close_blockers` still names it, `--status` still shows it, and the round still does not
#: close.
#:
#: Agreed for the round-8 spec bump in preference to a new ``READY`` token (their §B2): a new
#: verdict word would meet gates that have not shipped the new spec, which correctly treat an
#: unrecognised verdict as *not agreement* — so a ``READY`` file would silently fail to close
#: against an older peer. This wording changes only whether a **checker** errors, and leaves
#: both gates' closing behaviour byte-identical.
_PEER_VERDICT_BLOCKER: Final[str] = "peer verdict is "


def _is_peer_verdict_blocker(blocker: str) -> bool:
    """Whether this close-blocker is the peer's verdict rather than the author's gap."""
    return blocker.startswith(_PEER_VERDICT_BLOCKER)


def verification_verdict(text: str) -> str | None:
    """The verdict our verification file declares: ``"GO"``, ``"HOLD"``, or None.

    None means *no verdict was stated*, which callers must treat as **not
    closed** — a verification that does not say whether the pin may move has not
    answered the question the protocol asks.

    Conflicting markers also return ``"HOLD"``. A file that says both is a file
    whose author changed their mind mid-draft, and the safe reading of "GO and
    HOLD" is HOLD: a release wrongly blocked is a delay, a release wrongly
    allowed is a shipped unverified pin.
    """
    found = {m.group("verdict") for m in _VERDICT_LINE.finditer(text)}
    if not found:
        return None
    return "GO" if found == {"GO"} else "HOLD"


#: The lap of a file that declares none. **1, not 0** — the fork's rule, adopted in
#: lap 19 after their lap 18 revealed we had picked different numbers for the same
#: convention.
#:
#: Theirs is the more correct one and the reason is semantic rather than aesthetic: a
#: round's pre-lap-header file **is** that round's first lap. Round 7's `round-7.md` is
#: lap 1; calling it lap 0 invents a lap that never existed. Both choices order our
#: tree identically today, which is exactly why it needed catching by comparison rather
#: than by a failing test.
DEFAULT_LAP: int = 1

#: The lap of a file whose ``HANDSHAKE-LAP`` is declared more than once with different
#: values. **It sorts LAST, on purpose** — also the fork's rule, and it closes a real
#: hole on our side rather than merely aligning us.
#:
#: We used to fall back to the *filename* for an ambiguous declaration. So a file named
#: `lap-09` declaring both 9 and 20 sorted at 9, a later valid file was read as the
#: newest, and **the ambiguity was never examined by the gate at all** — the protocol's
#: own "present-but-ambiguous is worse than absent" principle broken in the direction
#: that hides it. Sorting it last makes it the file the verdict is read from, at which
#: point ``check_wire_header`` refuses it by name.
#:
#: A sentinel rather than ``None`` because the sort key is typed ``int``; the value only
#: has to exceed any real lap, and a lap count that reaches nine figures is a different
#: problem.
AMBIGUOUS_LAP: int = 1_000_000_000


def _lap_of(path: Path) -> int:
    """The lap a file belongs to, for ordering. **From the header, never the name.**

    Three answers, and each is a rule in the shared spec rather than a local choice:
    the declared integer; :data:`DEFAULT_LAP` when nothing is declared (§3 — *"absent
    means lap 1"*); :data:`AMBIGUOUS_LAP` when two different laps are declared, so the
    ambiguity sorts to where it must be examined.

    **There used to be a filename fallback between the second and third, and removing
    it is the round-7-lap-21 fix.** Reading the name when the header is silent is the
    thing §3 forbids in the same sentence that sets the default — *"by declared number,
    never by filename or mtime"* — and it made the two implementations of one agreed
    convention differ invisibly for the whole life of the convention: on today's trees
    the name and the default agree everywhere (our only no-lap files are named
    ``round-07-lap-01`` and the grandfathered ``round-N``, which has no lap to read), so
    no test on either side could see it.

    **What the fallback was accidentally protecting, and what protects it now.** A file
    that carries a v2 wire header but omits its required ``HANDSHAKE-LAP`` sorts at lap
    1 under the rule, i.e. *oldest* — so a later ``GO`` could be read as a round's
    newest word while this file's ``HOLD`` sorted underneath it. That is fail-open, and
    the name fallback happened to cover it. The fix is not the fallback (which would
    re-break §3) but §2 rule 4: **an absent required field fails closed.** A header-
    bearing file with no lap is refused outright by :func:`ordering_blockers`, so it
    never reaches the question of where it sorts.
    """
    try:
        declared = wire_fields(path.read_text(encoding="utf-8", errors="replace")).get(
            "HANDSHAKE-LAP", ""
        )
    except OSError:
        declared = ""
    if declared == AMBIGUOUS:
        return AMBIGUOUS_LAP
    if declared and declared.strip().isdigit():
        return int(declared.strip())
    return DEFAULT_LAP


def _round_of(path: Path) -> int:
    """The round a file belongs to, for ordering. **Header first, name second.**

    The mirror of :func:`_lap_of`, and it exists because ours did not have one: the
    round half of the sort key read :func:`round_number`, which is name-only, while the
    lap half already read the header. One key, two different notions of where the fact
    lives — the second divergence lap 21's diff found, and the spec had already ruled on
    it (§3: *"never by filename or mtime"*).

    **The name fallback here is required, not a lapse**, and this is the qualification
    the rule as worded needs: the v2 wire header begins at round 7 lap 2, so 27 of the
    41 committed correspondence files declare no ``HANDSHAKE-ROUND`` at all. For those
    the name is the only fact in existence. "Never the filename" has to mean *never in
    preference to the header* — a spec that meant it literally would be unimplementable
    against its own record.

    :func:`round_number` stays name-only on purpose: §3 requires the two to agree, and
    a check needs each separately in order to say so.
    """
    try:
        declared = declared_round(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        declared = None
    if declared is not None:
        return declared
    return round_number(path) or 0


#: The files our half of the seam is actually made of — the argv we send and the
#: text we parse back. `HANDSHAKE-SOURCE-ANCHOR` is a hash over exactly these, so
#: a `file:line` citation in a lap stays checkable against a named tree.
#:
#: **Mirrors the fork's definition rather than inventing one.** Theirs covers
#: `src/*.c` and `src/*.h` — *their* source. Ours covers ours.
SOURCE_ANCHOR_FILES: tuple[str, ...] = (
    "src/platterpus/adapters/cyanrip_backend.py",
    "src/platterpus/cyanrip_cli.py",
    "src/platterpus/cue_validate.py",
    "src/platterpus/parsers/cyanrip_info.py",
    "src/platterpus/parsers/cyanrip_log.py",
    "src/platterpus/parsers/rip_log.py",
    "src/platterpus/ripper_messages.py",
)


def source_anchor(root: Path | None = None) -> str:
    """The 16-hex `HANDSHAKE-SOURCE-ANCHOR` for our seam source.

    **This exists because the field was hand-typed and was wrong.** Round 7's
    laps carried `sha256/16 = 7dc313815850eb60`, which is character-for-character
    the first 16 hex of the `seam-commands` hash declared two lines below it in
    the same header. The anchor was a copy of a *shared file's* hash — a file
    neither project owns — so it pinned nothing about our source, in every lap
    that declared it. The fork found it; we confirmed it by recomputing.

    The lesson is the mechanism, not the typo: **a field whose value is typed by
    hand beside a similar-looking value will eventually be the other one.** It is
    computed now, and `tests/test_handshake_source_anchor.py` refuses a lap whose
    declared anchor is any shared file's prefix.

    Hashes `path\0content\0` per file in sorted order, so a rename is a change
    and two files cannot swap contents unnoticed. A missing file hashes as absent
    rather than raising — this is called while rendering a document, and a
    traceback there is worse than a value that visibly differs.
    """
    base = root or _REPO_ROOT
    digest = hashlib.sha256()
    for rel in sorted(SOURCE_ANCHOR_FILES):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        path = base / rel
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"<absent>")
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def sort_key(path: Path) -> tuple[int, int, str]:
    """**The** ordering for handshake files: ``(round, lap, stem)``.

    Public and single because "which file is newer" was answered by a plain stem sort
    in **three** independent places, and all three were wrong the moment the naming
    migration mixed `round-7.md` with `round-07-lap-16.md` — lexically
    ``"round-07-lap-16" < "round-7"``. One of the three decides `--status`, and it
    reported an OPEN round as closed.

    Three copies of an ordering is three chances to get it wrong; a sort key is exactly
    the kind of thing that looks too small to share until it decides a release gate.
    Callers pass this to ``sorted(key=...)`` and no longer spell it themselves.

    ``stem`` is a third component the fork's three ordering rules do not mention. It is
    only a tiebreak for two files at the same ``(round, lap)`` — a state the naming
    convention forbids and ``--check`` refuses — kept so the sort is *total*, because a
    non-total key makes "the newest file" depend on directory iteration order, which is
    the class of thing that decides a release gate differently on two machines. Named
    here so it is agreed rather than merely present on one side.

    Never raises: an unreadable or oddly-named file sorts first rather than exploding
    the caller.
    """
    return (_round_of(path), _lap_of(path), path.stem)


#: Filename marker for a lap file the SENDER later revised and re-sent. Protocol §2
#: says *"Each lap is a new file. Never edit a file already sent."* — but it happened
#: (cyanrip fork, round 7 lap 25, 2026-08-05: a second, larger lap-25 with substantive
#: corrections). Deleting the first would destroy the record of what was actually sent
#: and quoted; keeping it unmarked creates a duplicate `(round, lap)` that the gate
#: resolves by FILENAME — and measured, it resolved BACKWARDS, treating the superseded
#: file as newest. So a marked file is archival: preserved, and out of the sequence.
SUPERSEDED_MARKER: Final[str] = "-as-first-sent"


def is_superseded_archive(path: Path) -> bool:
    """True for a preserved earlier copy of a lap the sender revised and re-sent.

    Deliberately keyed on the FILENAME rather than on content: the whole point is that
    the file's content is what was sent and must not be edited to add a marker.
    """
    return SUPERSEDED_MARKER in path.stem


def ordering_blockers(paths: Iterable[Path]) -> list[str]:
    """Why the files of a round cannot be *ordered* — which is a refusal, not a warning.

    Two states, both of which ordering alone can only hide, and both already normative
    in the shared spec. They are checked at the **gate** rather than only in ``--check``
    because ``--check`` validates one inbound delivery while the gate is what decides
    whether a round is closed, and it was reading these files without ever asking
    whether they were coherent.

    * **A v2 file with no ``HANDSHAKE-LAP``** — §2 rule 4, an absent required field
      fails closed. Under §3's "absent means lap 1" such a file sorts *oldest*, so a
      later ``GO`` would be read as the round's newest word while this file's verdict
      sorted underneath it. Fail-open, so it is refused instead.
    * **A file whose declared round is not its named round** — §3, and §8's tenth
      conformance row. ``check_wire_header`` has always reported it; the gate never
      asked, so a file declaring round 8 could sit in round 7's set, sort last on the
      strength of its declaration, and have its verdict read as round 7's.

    Grandfathering is derived, not listed: a file with no ``HANDSHAKE-PROTOCOL`` line
    predates the header and neither rule applies to it. That is the same
    already-in-the-file test the section sweep uses, and it cannot go stale the way a
    frozenset of round numbers does.
    """
    problems: list[str] = []
    for path in paths:
        fields = wire_fields(_safe_read(path))
        if "HANDSHAKE-PROTOCOL" not in fields:
            continue  # predates the wire header; §9 grandfathers it wholesale
        lap = fields.get("HANDSHAKE-LAP")
        if lap is None:
            problems.append(
                f"{path.name}: carries a wire header but declares no HANDSHAKE-LAP "
                "(§2 rule 4) — an absent required field fails closed, and under §3 "
                "it would otherwise sort as lap 1 and be superseded by anything later"
            )
        named = round_number(path)
        declared = fields.get("HANDSHAKE-ROUND")
        if (
            named is not None
            and declared is not None
            and declared != AMBIGUOUS
            and declared.strip().isdigit()
            and int(declared) != named
        ):
            problems.append(
                f"{path.name}: declares HANDSHAKE-ROUND: {declared} but is filed as "
                f"round {named} (§3, §8 row 10) — it cannot be ordered within either "
                "round without the gate choosing which declaration to believe"
            )
    # A DUPLICATE (round, lap, sender) IS UNORDERABLE, AND IT FAILED OPEN.
    #
    # `sort_key` is `(round, lap, stem)`, so two files at the same round and lap fall
    # through to the filename — which is arbitrary with respect to which was sent
    # later. MEASURED on the real case: `round-07-lap-25.md` (the revision) sorted
    # BEFORE `round-07-lap-25-as-first-sent.md`, so the gate would have read the
    # SUPERSEDED file's verdict as the round's newest word. Both happened to declare
    # HOLD, so nothing broke — which is exactly how this class of bug survives.
    #
    # This is the third fail-open ordering hole in this function's own subject matter,
    # and the first two are the two blockers above it. The lesson is the same each
    # time: whenever "the newest file" is not a well-defined question, the permissive
    # answer is the wrong one.
    # SCOPED PER DIRECTORY, which is the correct scope and not a loosening.
    # `_round_files` sorts within ONE directory and the verdict is read from that
    # directory's last file (`done[-1]` ours, `back[-1]` theirs) — so two files only
    # ever compete for "newest" inside the same directory. An outbound round file and
    # our verification of it can legitimately share a lap: different roles, neither
    # superseding the other.
    seen: dict[tuple[str, int | None, int, str], str] = {}
    for path in paths:
        if is_superseded_archive(path):
            continue  # archival by name: preserved, deliberately out of the sequence
        fields = wire_fields(_safe_read(path))
        if "HANDSHAKE-PROTOCOL" not in fields:
            continue  # predates the wire header; §9 grandfathers it wholesale
        key = (
            path.parent.name,
            _round_of(path),
            _lap_of(path),
            (fields.get("HANDSHAKE-FROM") or "").strip(),
        )
        if key in seen:
            problems.append(
                f"{path.name}: declares the same round/lap/sender as {seen[key]} "
                f"(round {key[1]}, lap {key[2]}, from {key[3] or '?'}) — §2 says each "
                "lap is a new file and a sent file is never edited, so two of them "
                "cannot be ordered: the gate would pick by filename, which is "
                f"arbitrary. Rename the earlier copy with '{SUPERSEDED_MARKER}' to "
                "archive it out of the sequence, or give the revision its own lap."
            )
        else:
            seen[key] = path.name
    return problems


def _round_files(directory: Path, number: int) -> list[Path]:
    """Every file in ``directory`` belonging to round ``number``, oldest first.

    **Ordered by (lap, stem), NOT by stem alone**, and that distinction was a live bug
    for the length of one commit. The 2026-08-04 rename to ``round-07-lap-LL.md`` left
    the pre-lap-header ``round-7.md`` in place beside it, and lexically
    ``"round-07-lap-16" < "round-7"`` — ``'0' < '7'`` at the seventh character. So the
    fork's **lap 1** file sorted last and was read as the newest, which flipped
    ``--status`` for round 7 from ``they-verified=HOLD`` to ``GO``.

    That is the worst class of regression this file can have: a **release gate** whose
    answer changed because of a filename. Ordering by the declared lap makes the sort
    a function of the facts rather than of the string, so mixing naming schemes cannot
    reorder anything. ``stem`` stays as the tiebreak for two files at the same lap.
    """
    if not directory.is_dir():
        return []
    return sorted(
        (p for p in directory.glob("round-*.md") if round_number(p) == number),
        key=sort_key,
    )


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
    rounds: set[int] = set()
    for directory in (outbound, inbound, verified):
        if directory.is_dir():
            for path in directory.glob("round-*.md"):
                num = round_number(path)
                if num is not None:
                    rounds.add(num)
    # The floor, added unconditionally: see CURRENT_ROUND for why a round with no
    # committed files must still count as a round.
    rounds.add(CURRENT_ROUND)
    if not rounds:
        # AN EMPTY RECORD IS A REFUSAL, NOT AGREEMENT (PROTOCOL.md §8 row 12).
        #
        # This used to return a bare "no handshake rounds" line, which does not end
        # in "OPEN" — so `--release-gate` read it as "nothing is open" and printed
        # *"every round is closed — release allowed"*. A gate satisfied by finding
        # nothing, in the gate whose whole job is not being satisfied by nothing.
        # Found by running the fork's own conformance table against ours (T15),
        # which is the entire argument for having a shared table.
        return [
            "no handshake rounds recorded under docs/handshake/ -> OPEN",
            "",
            "An empty record is not agreement: do not release, and do not switch "
            "the pin.",
        ]
    for num in sorted(rounds):
        name = f"round-{num}"
        # An AMENDMENT (`round-6b.md`) belongs to its round, it is not a round of
        # its own. Round 6 was amended hours after it was sent because the pin it
        # asked for returned silence on disc images; counting that as "round 6b,
        # OPEN" would report two open rounds where one was corrected, and would
        # make sending a correction immediately look worse in the record than
        # sitting on it.
        sent = _round_files(outbound, num)
        back = _round_files(inbound, num)
        done = _round_files(verified, num)
        # A ROUND WHOSE FILES CANNOT BE ORDERED IS OPEN, and the reason is named.
        #
        # Both blockers are states in which "the newest file" is not a well-defined
        # question (`ordering_blockers`), and in both the wrong answer is the
        # permissive one — a file that sorts oldest by omission, or one that sorts
        # last on the strength of a round it does not belong to. Reported before the
        # verdicts are read, because the verdicts are read *off the ordering*.
        unorderable = ordering_blockers([*sent, *back, *done])
        # The verdict comes from the NEWEST verification file for the round —
        # `_round_files` sorts by `sort_key`, so a later lap supersedes the file it
        # corrects. Reading the oldest would let a since-withdrawn GO keep a round
        # closed.
        verdict: str | None = None
        if done:
            our_text = done[-1].read_text(encoding="utf-8")
            # The shared header is authoritative (protocol §8). Our own bolded
            # prose form is the fallback, and only for rounds that predate the
            # format — otherwise the two representations could disagree and the
            # older, looser one would win.
            verdict = wire_verdict(our_text)
            if verdict is None and num in OUR_PRE_HEADER_ROUNDS:
                verdict = verification_verdict(our_text)
            if verdict is None and num in RETROSPECTIVE_ROUNDS:
                verdict = "GO"
        # THEIR verdict, read from the newest inbound file for the round.
        #
        # **The handshake is affirmative and BILATERAL** (maintainer directive,
        # 2026-08-04): *"Both of you should not make a new release until you are
        # both happy with the handshake files."* Reading only our own verdict made
        # their HOLD unable to block our release — which is the same
        # one-half-of-a-two-half-contract error §7 of the protocol already records
        # twice, arriving a third time. Their lap-2 file declares
        # `HANDSHAKE-VERDICT: HOLD` at column 0; nothing here was reading it.
        theirs: str | None = None
        if back:
            theirs = wire_verdict(back[-1].read_text(encoding="utf-8"))
            if theirs is None and num in THEIR_PRE_HEADER_ROUNDS:
                theirs = "GO"
        # A round closes on BOTH VERDICTS, not on the files existing. Round 7 is
        # the case that proved the first half matters: its verification is a
        # deliberate mid-round HOLD ("your §15 asked us to hold"), and a
        # presence-only check reported it CLOSED and let `--release-gate` pass —
        # while the deviation policy forbids releasing or moving the pin with a
        # round open. A gate that a HOLD satisfies is not a gate (CLAUDE.md: *can
        # this check be satisfied by the wrong thing?*).
        # A GO that cannot close is not a close (§5). Reading only the verdict is
        # what let a round-8 file with no identity fields close — see
        # `close_blockers`. Checked on BOTH sides' newest file.
        # `close_blockers` is a check on a §5 *header*, so it only applies to rounds
        # that have one. The pre-header rounds state their verdict in prose, and
        # running the header check over them reported "no HANDSHAKE-VERDICT
        # declared" for every closed round in the record — the grandfather clause
        # defeated by the very absence it exists to permit. Second time in one
        # change: the first was keying the exemption on a field those files lack.
        pre_header = num in (OUR_PRE_HEADER_ROUNDS | THEIR_PRE_HEADER_ROUNDS)
        our_blockers: list[str] = []
        their_blockers: list[str] = []
        if not pre_header:
            if done:
                our_blockers = close_blockers(
                    done[-1].read_text(encoding="utf-8"), round_hint=num
                )
            if back:
                their_blockers = close_blockers(
                    back[-1].read_text(encoding="utf-8"), round_hint=num
                )
        both_go = (
            verdict == "GO"
            and theirs == "GO"
            and not our_blockers
            and not their_blockers
            and not unorderable
        )
        state = "CLOSED" if (sent and back and both_go) else "OPEN"

        def shown_verdict(value: str | None) -> str:
            if value is None:
                return "NO"
            return "yes (GO)" if value == "GO" else f"yes ({value} — not closed)"

        lines.append(
            f"{name}: sent={'yes' if sent else 'NO'} "
            f"returned={'yes' if back else 'NO'} "
            f"we-verified={shown_verdict(verdict)} "
            f"they-verified={shown_verdict(theirs)}  -> {state}"
        )
        # Named, not merely counted: a gate that refuses without saying which file
        # and which rule is a gate people route around.
        lines.extend(f"  cannot order {problem}" for problem in unorderable)
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
        "--check",
        type=Path,
        nargs="+",
        metavar="FILE",
        help="validate an inbound file. Pass several to validate a round "
        "delivered as a file plus an amendment (round 6 + round 6b) — the "
        "sections are looked for across the set, because an amendment that "
        "only changes the pin should not be required to restate all ten",
    )
    group.add_argument("--status", action="store_true", help="report the round state")
    parser.add_argument(
        "--handshake-dir",
        metavar="DIR",
        default=None,
        help="read the round record from DIR instead of docs/handshake. Exposes "
        "what `round_status()` already accepted: the gate's own conformance rows "
        "(C19/C20) need a record with an OPEN round, and once every real round is "
        "closed the only honest way to assert a refusal is against a fixture "
        "rather than against the empty set",
    )
    parser.add_argument(
        "--prerelease",
        action="store_true",
        help="with --release-gate: permit a PRE-RELEASE while a round is open. A "
        "pre-release is a test artifact, not a claim that the pair was verified "
        "(handshake round 7 lap 6 §1 — the close-needs-hardware deadlock). A "
        "stable release is still refused.",
    )
    group.add_argument(
        "--release-gate",
        action="store_true",
        help="exit non-zero if any round is open (for the release workflow)",
    )
    args = parser.parse_args(argv)

    if args.emit is not None:
        sys.stdout.write(emit_outbound(args.emit))
        return 0
    record_root = Path(args.handshake_dir) if args.handshake_dir else None
    if args.status:
        status_lines = round_status(record_root)
        for line in status_lines:
            sys.stdout.write(line + "\n")
        return 1 if any(ln.endswith("OPEN") for ln in status_lines) else 0
    if args.release_gate:
        # A PRE-RELEASE is permitted while a round is open. A stable release is not.
        #
        # The fork found the deadlock and named it (round 7 lap 6 §1): a round cannot
        # close without `HANDSHAKE-TESTED` naming what ran; that evidence needs the
        # reviewed build on the rig; installing it is forbidden while the round is
        # open. Every step is a rule both projects hold and together they are
        # unsatisfiable. Their fix is `HANDSHAKE-TEST-PIN` — a build designated to
        # gather evidence, which never closes a round and never moves the production
        # pin. This is the same fix on our side of the seam.
        #
        # **What the gate protects is the claim a stable release makes**: that the
        # pair was jointly verified. A beta makes no such claim — it ships as a
        # GitHub pre-release, its own report says `ripper_handshake_approval:
        # not_determined` or `unapproved`, and its whole purpose is to *produce* the
        # evidence the close requires. Refusing it does not protect a user; it
        # guarantees the round can never close.
        #
        # Loud, not silent: the open rounds are printed either way, so a pre-release
        # never looks like a clean record.
        if args.prerelease:
            lines = round_status(record_root)
            open_rounds = [ln for ln in lines if ln.endswith("OPEN")]
            if open_rounds:
                sys.stderr.write(
                    "handshake: PRE-RELEASE permitted with a round OPEN — this build "
                    "is a test artifact, not a verified pair. It must ship as a "
                    "GitHub pre-release and must not move the production pin:\n"
                )
                for line in open_rounds:
                    sys.stderr.write(f"  - {line}\n")
                sys.stderr.write(
                    "handshake: a STABLE release is still blocked until both sides "
                    "declare GO with both versions, both pins and HANDSHAKE-TESTED.\n"
                )
            else:
                sys.stdout.write(
                    "handshake: every round is closed — pre-release allowed\n"
                )
            return 0
        # THE release gate. `--status` reports and also exits non-zero, which
        # made it look like this already existed — but nothing on the release
        # path ran it, and the only thing enforcing "no release while a round is
        # open" was a unit test that reddened *every* commit the moment a round
        # was opened. That is the wrong place twice over: it blocked ordinary
        # work, and it did not block a release, because `release.yml` never
        # called it. This subcommand exists so the workflow can.
        lines = round_status(record_root)
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

    label = " + ".join(str(p) for p in args.check)
    # ROUTE BY DIRECTION. Before this, `--check` ran the *inbound* spec against
    # every file it was given, so checking one of our own outbound files reported
    # six sections "missing" that the outbound spec never asks for. Seven bogus
    # problems on a correct file is how a checker gets switched off.
    #
    # Files are grouped rather than checked one at a time because `check_inbound`
    # deliberately treats several inbound paths as ONE round delivered in parts
    # (round 6 was exactly that), and splitting them would reintroduce the
    # over-strictness its docstring warns about.
    grouped: dict[str, list[Path]] = {"outbound": [], "inbound": [], "verified": []}
    for path in args.check:
        grouped[direction_of(path)].append(path)
    problems = []
    if grouped["inbound"]:
        problems.extend(check_inbound(*grouped["inbound"]))
    if grouped["outbound"]:
        problems.extend(check_outbound_paths(*grouped["outbound"]))
    if grouped["verified"]:
        problems.extend(check_verification_paths(*grouped["verified"]))
    if not problems:
        sys.stdout.write(f"{label}: satisfies the protocol (all sections present)\n")
        return 0
    sys.stderr.write(f"{label}: {len(problems)} problem(s)\n")
    for problem in problems:
        sys.stderr.write(f"  - {problem}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
