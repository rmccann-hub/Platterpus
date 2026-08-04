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

    header = "\n".join(
        [
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


#: A handshake file name: ``round-6.md``, or ``round-6b.md`` for an amendment
#: sent after the round's main file. The suffix is deliberately allowed — round 6
#: needed one within hours — and is deliberately *not* a new round number.
_ROUND_NAME = re.compile(r"^round-(?P<number>\d{1,4})(?P<amendment>[a-z]{0,2})$")


def round_number(path: Path) -> int | None:
    """The round a handshake file belongs to, or None if the name is not one.

    ``round-6b.md`` returns 6. Returning None rather than raising matters: an
    unrelated file dropped in the directory must not take the status report
    down with it.
    """
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

#: The fields the format requires of every file, from either side (§8.2).
REQUIRED_WIRE_FIELDS: tuple[str, ...] = (
    "HANDSHAKE-ROUND",
    "HANDSHAKE-LAP",
    "HANDSHAKE-FROM",
    "HANDSHAKE-VERDICT",
    "HANDSHAKE-APP-VERSION",
    "HANDSHAKE-RIPPER-VERSION",
    "HANDSHAKE-PIN",
)

#: ``GO`` is the only affirmative. Everything else — including a value neither side
#: recognises — means *not closed*.
AFFIRMATIVE: str = "GO"

#: Rounds that closed before the fork emitted the header block. Their affirmative
#: GO for these is in the round record and in our verification prose; grandfathered
#: **by number**, never by "no header means fine", and pinned by a test. Same shape
#: and same reason as :data:`RETROSPECTIVE_ROUNDS` — the fallback is the defect.
THEIR_PRE_HEADER_ROUNDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 7})

#: Ours, likewise: every verification file through round 7 lap 1 predates the
#: format and states its verdict as bolded prose. May shrink, never grow.
OUR_PRE_HEADER_ROUNDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 7})


def wire_fields(text: str) -> dict[str, str]:
    """Every column-0 ``KEY: value`` field in a handshake file.

    Later occurrences win, except that :func:`wire_verdict` treats a *repeated
    verdict* as ambiguous rather than taking one — see there.
    """
    return {m.group("key"): m.group("value") for m in _WIRE_FIELD.finditer(text)}


def wire_verdict(text: str) -> str | None:
    """The declared verdict, or None if the file states none.

    ``GO`` is the only affirmative. ``HOLD``, ``OPEN`` and any unrecognised value
    all mean *not closed* — an unknown verdict is not consent, and mapping it to
    anything else would be a guess wearing a derivation's clothes (the fork's
    phrase for the same hazard on their side).

    **Two verdict lines are ambiguous, not "the first one"**, and resolve to
    ``HOLD``. Adopted from their gate; the reasoning is theirs and it is right.
    """
    found = {
        m.group("value").split()[0]
        for m in _WIRE_FIELD.finditer(text)
        if m.group("key") == "HANDSHAKE-VERDICT" and m.group("value").split()
    }
    if not found:
        return None
    return AFFIRMATIVE if found == {AFFIRMATIVE} else "HOLD"


def check_wire_header(path: Path, *, expect_from: str | None = None) -> list[str]:
    """Validate a handshake file's header block against §8.2. Returns problems.

    Reports rather than raises, like every other check here: a validator that
    crashes is a validator people stop running.
    """
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path.name}: unreadable ({exc})"]

    fields = wire_fields(text)
    for key in REQUIRED_WIRE_FIELDS:
        if key not in fields:
            problems.append(
                f"{path.name}: missing required field {key} (protocol §8.2)"
            )

    # The declared round must match the filename's. A file whose header and name
    # disagree is an error, not a reinterpretation (§8.3 rule 6) — this is the one
    # check the filename convention cannot make for itself.
    declared = fields.get("HANDSHAKE-ROUND", "")
    named = round_number(path)
    if declared and named is not None:
        try:
            if int(declared) != named:
                problems.append(
                    f"{path.name}: declares HANDSHAKE-ROUND: {declared} but its "
                    f"name says round {named} (protocol §8.3 rule 6)"
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
    return problems


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


def _round_files(directory: Path, number: int) -> list[Path]:
    """Every file in ``directory`` belonging to round ``number``, oldest first.

    Sorted by stem so ``round-6.md`` precedes ``round-6b.md`` — the reading order
    the fork sends them in, and the order in which later files supersede earlier
    ones.
    """
    if not directory.is_dir():
        return []
    return sorted(
        (p for p in directory.glob("round-*.md") if round_number(p) == number),
        key=lambda p: p.stem,
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
    if not rounds:
        return ["no handshake rounds recorded under docs/handshake/"]
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
        # The verdict comes from the NEWEST verification file for the round —
        # `_round_files` sorts by stem, so an amendment (`round-7b.md`) supersedes
        # the file it corrects. Reading the oldest would let a since-withdrawn GO
        # keep a round closed.
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
        both_go = verdict == "GO" and theirs == "GO"
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

    label = " + ".join(str(p) for p in args.check)
    problems = check_inbound(*args.check)
    if not problems:
        sys.stdout.write(f"{label}: satisfies the protocol (all sections present)\n")
        return 0
    sys.stderr.write(f"{label}: {len(problems)} problem(s)\n")
    for problem in problems:
        sys.stderr.write(f"  - {problem}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
