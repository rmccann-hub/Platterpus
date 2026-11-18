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
syntax."* The square-bracket qualifier and the Title-Case descriptor were his
example, kept literally from then until 2026-11-17.

**The convention changed on 2026-11-17** (the owner's word, fixing finding W1
of that day's end-user UX review): the Title Case descriptor and the square
brackets read as shouting inside a list, and KDE's style, which every checkbox
and button beside these combos already follows, writes list items in sentence
case. The *structure* he asked for is kept (one name, one em dash, one
descriptor, one optional qualifier from a closed set); only the case and the
brackets changed.

**The convention.**

    <Name> — <descriptor in sentence case>[ (qualifier)]

- ``Name`` is what the thing *is* — a format (``FLAC``), a mode
  (``Adaptive ladder``), or a shape (``Artist / Album / 01 - Title``). It starts
  with a capital, and after its first word only acronyms and proper names are
  capitalised. A *path shape* (a name containing ``/``) is exempt after its
  first word, because its words are tag fields (``Artist``, ``Album``), not
  prose.
- ``—`` is an **em dash with a space either side**, and it appears exactly once.
  One separator means a reader (and this checker) can always tell the name from
  the description, which a parenthetical cannot.
- ``descriptor`` says what picking it *does*, in sentence case: it continues the
  name's sentence, so it starts lowercase, and only acronyms (``VBR``,
  ``CTDB``), words with an inner capital (``AccurateRip``, ``WavPack``) and the
  proper names in :data:`PROPER_NAMES` are capitalised.
- ``(qualifier)`` is optional, lowercase, and comes from a closed set
  (:data:`QUALIFIERS`) so it stays a *label*, not a second free-text field.

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

#: The closed set of trailing ``(qualifier)`` annotations. Closed on purpose:
#: the moment this is free text it becomes a second descriptor, and two
#: descriptors is the inconsistency this module exists to remove. Add a member
#: here (deliberately) rather than inventing one at a call site.
QUALIFIERS: frozenset[str] = frozenset(
    {
        "recommended",
        "advanced",
        "default",
        "optional",
        "debugging",
    }
)

#: Proper names that are capitalised in sentence case and are neither acronyms
#: nor written with an inner capital, so the checker cannot recognise them by
#: shape. Kept short and deliberate, like :data:`QUALIFIERS`: a word added here
#: is a word every label may capitalise.
PROPER_NAMES: frozenset[str] = frozenset({"Plex", "Jellyfin", "Picard"})

#: Shared by the Goal combo and the naming-scheme combo, which both need a
#: "none of the above" row. It was a hardcoded literal in the dialog *and* a
#: constant in :mod:`platterpus.naming`, so the two could drift apart while
#: sitting four hundred lines from each other in the same dialog.
CUSTOM_LABEL: str = f"Custom{SEPARATOR}hand-tuned below"

#: Punctuation stripped from a word before the capitalisation check. Parentheses
#: are removed anywhere in the token (not only at the ends) so
#: ``"(Accurate"`` and ``"Rip)"`` are still checked as words — a blanket
#: "skip anything with a bracket" would let ``(Fully Verified)`` through,
#: which is a check satisfied by the wrong thing.
_STRIPPED = ".,;:!?\"'`"

#: A trailing ``(qualifier)`` — one lowercase word in parentheses — captured so
#: the descriptor check can look at the rest of the string and the qualifier can
#: be validated against QUALIFIERS. A parenthetical that is not one lowercase
#: word, like ``(AccurateRip + CTDB)``, is part of the descriptor.
#:
#: **Both quantifiers are bounded**, per the project's regex rule — and this one
#: was caught by `tests/test_regex_bounded_time.py` rather than by care: an
#: unbounded `\s*` before an anchored group backtracks super-linearly, measured at
#: 16× the time for 4× the input on a run of tabs. A qualifier is one word from a
#: five-member set, so 32 characters is generous and a longer "qualifier" is not
#: one.
_QUALIFIER_SUFFIX = re.compile(r"\s{0,4}\((?P<qualifier>[a-z]{1,32})\)$")

#: The old convention's ``[Qualifier]``, recognised only to name it as the
#: problem: a label still written the old way should be told what to change.
_OLD_QUALIFIER = re.compile(r"\[[^\[\]]{0,32}\]$")

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


def _word_is_sentence_case(word: str) -> bool:
    """True if one whitespace-separated word may stand inside a sentence-case label.

    Accepts: a lowercase word, an all-caps acronym (``VBR``, ``CTDB``), a word
    with a capital after its first letter (``AccurateRip``, ``WavPack``),
    anything with no letters (``+``) or containing a digit (``01``, ``MP3``,
    ``foobar2000``), and a name in :data:`PROPER_NAMES`. Refuses a word written
    with only its first letter capitalised (``Lossless``, ``Verified``), which
    is what Title Case looks like.

    Each half of a hyphenated compound is checked independently
    (``best-Quality``): looking only at the word's first letter would pass it,
    which is the hole a one-line implementation leaves.
    """
    for part in word.replace("(", "").replace(")", "").split("-"):
        token = part.strip(_STRIPPED)
        if not token or any(ch.isdigit() for ch in token):
            continue  # a number, a measurement, or a version like foobar2000
        if not any(ch.isalpha() for ch in token):
            continue  # punctuation standing alone, e.g. the "+" in "(A + B)"
        if not token[0].isupper():
            continue
        letters = [ch for ch in token if ch.isalpha()]
        if len(letters) > 1 and all(ch.isupper() for ch in letters):
            continue  # an acronym
        if any(ch.isupper() for ch in token[1:]):
            continue  # an inner capital: a product name like AccurateRip
        if token in PROPER_NAMES:
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
    if not name[0].isupper() and not name[0].isdigit():
        return f"name {name!r} does not start with a capital"
    if "/" not in name:
        bad_name = [w for w in name.split()[1:] if not _word_is_sentence_case(w)]
        if bad_name:
            return (
                f"name {name!r} is not sentence case — "
                f"capitalised word(s): {', '.join(bad_name)}"
            )

    if _OLD_QUALIFIER.search(descriptor):
        return (
            "ends with a [Bracketed] qualifier; the convention is a lowercase "
            "one in parentheses, e.g. (recommended)"
        )
    match = _QUALIFIER_SUFFIX.search(descriptor)
    if match is not None:
        qualifier = match.group("qualifier")
        if qualifier not in QUALIFIERS:
            allowed = ", ".join(sorted(QUALIFIERS))
            return f"has qualifier ({qualifier}); allowed qualifiers are: {allowed}"
        descriptor = descriptor[: match.start()]

    descriptor = descriptor.strip()
    if not descriptor:
        return "has no descriptor after the separator (only a qualifier)"

    # One list, one message: reporting the first bad word and stopping means a
    # label with three capitalised words takes three runs to fix.
    bad = [word for word in descriptor.split() if not _word_is_sentence_case(word)]
    if bad:
        return (
            f"descriptor {descriptor!r} is not sentence case — "
            f"capitalised word(s): {', '.join(bad)}"
        )
    return None
