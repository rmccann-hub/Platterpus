"""The one naming convention every Settings *option* follows, plus its checker.

**Why this module exists.** Every dropdown in Settings offered its options in
whatever phrasing the person adding it happened to like, so five combos in one
dialog read five different ways::

    FLAC — lossless archival master (recommended)     # em dash, lowercase
    Don't fetch                                       # no descriptor at all
    Adaptive ladder — fast, slower only if a disc needs it
    Fixed speed (advanced)                            # parenthetical, no dash
    Artist / Album / 01 - Title  (recommended)        # two spaces, parenthetical

The maintainer read that dialog on real hardware and asked for one syntax:
*"These settings should be called something like Flack - Lossless Archival
Master [Debugging] or similar, and other settings should reflect similar naming
syntax."* The square-bracket qualifier and the Title-Case descriptor below are
his example, kept literally rather than reinterpreted.

**The convention.**

    <Name> — <Descriptor In Title Case>[ [Qualifier]]

- ``Name`` is what the thing *is* — a format (``FLAC``), a mode
  (``Adaptive Ladder``), or a shape (``Artist / Album / 01 - Title``). It is
  deliberately free-form, because a path template and a file extension both
  belong here and neither is a sentence.
- ``—`` is an **em dash with a space either side**, and it appears exactly once.
  One separator means a reader (and this checker) can always tell the name from
  the description, which a parenthetical cannot: ``WavPack (.wv)`` and
  ``Fixed speed (advanced)`` use the same bracket for two different jobs.
- ``Descriptor`` says what picking it *does*, in Title Case.
- ``[Qualifier]`` is optional and comes from a closed set (:data:`QUALIFIERS`)
  so it stays a *label*, not a second free-text field.

**Why a checker rather than a note in a review guide.** ``CLAUDE.md`` records
this project's own lesson twice over — *a comment where a check belongs is not a
fix*, and *enforce a rule across the codebase, not at the place it was learned*.
A convention that lives only in prose is satisfied by whoever last read the
prose. :func:`check_option_label` is a pure function, so the test suite can
sweep **every item of every combo in the real dialog** and a combo added next
year is covered without anyone remembering this file exists.

**What it deliberately does not cover.** Labels that identify *hardware or
state* rather than offer a choice: the drive picker's
``Pioneer BD-RW BDR-209D (/dev/sr0)`` is a device, and its ``(no drives found)``
is a placeholder standing in for an empty list. Those are named exemptions here
(:func:`is_placeholder`) rather than silent omissions, because an exemption
nobody wrote down is indistinguishable from a rule nobody applied.
"""

from __future__ import annotations

import re

#: The separator between a name and its descriptor: an em dash with spaces.
#: Spelled as a constant so no caller can accidentally use a hyphen or an en
#: dash, which look near-identical in a terminal diff and would split wrong.
SEPARATOR: str = " — "

#: The closed set of trailing ``[Qualifier]`` annotations. Closed on purpose:
#: the moment this is free text it becomes a second descriptor, and two
#: descriptors is the inconsistency this module exists to remove. Add a member
#: here (deliberately) rather than inventing one at a call site.
QUALIFIERS: frozenset[str] = frozenset(
    {
        "Recommended",
        "Advanced",
        "Default",
        "Optional",
        "Debugging",
    }
)

#: Shared by the Goal combo and the naming-scheme combo, which both need a
#: "none of the above" row. It was a hardcoded literal in the dialog *and* a
#: constant in :mod:`platterpus.naming`, so the two could drift apart while
#: sitting four hundred lines from each other in the same dialog.
CUSTOM_LABEL: str = f"Custom{SEPARATOR}Hand-Tuned Below"

#: Words Title Case leaves lowercase (articles, conjunctions, short
#: prepositions). Capitalising them is *also* accepted — the checker's rule is
#: "capitalised, or one of these" — so this list can never make a correct label
#: fail; it only stops the checker rejecting `of`, `the`, `and` and friends.
_SMALL_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "if",
        "in",
        "into",
        "nor",
        "of",
        "off",
        "on",
        "onto",
        "or",
        "over",
        "per",
        "so",
        "than",
        "that",
        "the",
        "to",
        "up",
        "via",
        "vs",
        "with",
        "yet",
    }
)

#: Punctuation stripped from a word before the capitalisation check. Parentheses
#: are removed anywhere in the token (not only at the ends) so
#: ``"(AccurateRip"`` and ``"CTDB)"`` are still checked as words — a blanket
#: "skip anything with a bracket" would let ``(accuraterip + ctdb)`` through,
#: which is a check satisfied by the wrong thing.
_STRIPPED = ".,;:!?\"'`"

#: A trailing ``[Qualifier]``, captured so the descriptor check can look at the
#: rest of the string and the qualifier can be validated against QUALIFIERS.
#:
#: **Both quantifiers are bounded**, per the project's regex rule — and this one
#: was caught by `tests/test_regex_bounded_time.py` rather than by care: an
#: unbounded `\s*` before an anchored group backtracks super-linearly, measured at
#: 16× the time for 4× the input on a run of tabs. A qualifier is one word from a
#: five-member set, so 32 characters is generous and a longer "qualifier" is not
#: one.
_QUALIFIER_SUFFIX = re.compile(r"\s{0,4}\[(?P<qualifier>[^\[\]]{0,32})\]$")

#: A whole-string parenthesised placeholder, e.g. ``(no drives found)``. Matched
#: as an exemption, not as a conforming label.
_PLACEHOLDER = re.compile(r"^\([^()]*\)$")


def is_placeholder(label: str) -> bool:
    """True for a whole-string parenthesised stand-in like ``(no drives found)``.

    A placeholder is not an option — nothing happens if you "pick" it, and
    several are built from an error message whose wording is not ours. They are
    exempt from the convention, and this predicate is how a caller says so
    out loud.
    """
    return bool(_PLACEHOLDER.match(label.strip()))


def _word_is_titled(word: str, *, allow_small: bool) -> bool:
    """True if one whitespace-separated word satisfies the Title Case rule.

    Accepts: a capitalised word, an all-caps acronym (``VBR``, ``CTDB``),
    anything with no letters to capitalise (``+``) or containing a digit
    (``01``, ``24×``, ``foobar2000``), and — when ``allow_small`` — a small word
    left lowercase.

    ``allow_small`` is False for the descriptor's **first** word, because Title
    Case capitalises the opening word even when it is `the` or `a`.

    Each half of a hyphenated compound is checked independently
    (``Best-Quality``): looking only at the word's first letter would pass
    ``Best-quality``, which is the hole a one-line implementation leaves.
    """
    for part in word.replace("(", "").replace(")", "").split("-"):
        token = part.strip(_STRIPPED)
        if not token or any(ch.isdigit() for ch in token):
            continue  # a number, a measurement, or a version like foobar2000
        if not any(ch.isalpha() for ch in token):
            continue  # punctuation standing alone, e.g. the "+" in "(A + B)"
        if token[0].isupper():
            continue
        if allow_small and token.lower() in _SMALL_WORDS:
            continue
        return False
    return True


def check_option_label(label: str) -> str | None:
    """Return a human-readable problem with ``label``, or ``None`` if it conforms.

    Returns the *reason* rather than a bool so a failing sweep names what is
    wrong with which label — a boolean assertion over thirty labels tells you
    only that one of them is bad.

    Never raises: it is a text checker, and the callers are tests and (in
    principle) a lint script, both of which are more useful when they report
    than when they traceback.
    """
    if label != label.strip():
        return "has leading or trailing whitespace"
    if not label:
        return "is empty"
    if "  " in label:
        return "contains a double space (use the em-dash separator instead)"

    count = label.count(SEPARATOR)
    if count == 0:
        # Give the two near-misses their own message: they are what the old
        # labels actually did, so the report should name the fix, not the rule.
        if " - " in label or " – " in label:
            return (
                "separates with a hyphen or en dash; the convention is an "
                f"em dash ({SEPARATOR!r})"
            )
        return f"has no {SEPARATOR!r} separator between the name and what it does"
    if count > 1:
        return f"has {count} {SEPARATOR!r} separators; exactly one is allowed"

    name, descriptor = label.split(SEPARATOR)
    if not name.strip():
        return "has an empty name before the separator"

    match = _QUALIFIER_SUFFIX.search(descriptor)
    if match is not None:
        qualifier = match.group("qualifier")
        if qualifier not in QUALIFIERS:
            allowed = ", ".join(sorted(QUALIFIERS))
            return f"has qualifier [{qualifier}]; allowed qualifiers are: {allowed}"
        descriptor = descriptor[: match.start()]

    descriptor = descriptor.strip()
    if not descriptor:
        return "has no descriptor after the separator (only a qualifier)"

    words = descriptor.split()
    # One list, one message: reporting the first bad word and stopping means a
    # label with three lowercase words takes three runs to fix.
    bad = [
        word
        for index, word in enumerate(words)
        if not _word_is_titled(word, allow_small=index > 0)
    ]
    if bad:
        return (
            f"descriptor {descriptor!r} is not Title Case — "
            f"lowercase word(s): {', '.join(bad)}"
        )
    return None
