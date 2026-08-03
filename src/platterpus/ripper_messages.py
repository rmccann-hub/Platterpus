"""Recognising a cyanrip diagnostic in a stream of live output.

**Why this module replaced a prefix list.** Surfacing used to work off a
hand-maintained tuple of opening words — ``Invalid``, ``Unable``, ``Failed``, … —
and a line matched if it started with one. That mechanism has now failed twice,
once on each side of the seam, in exactly the same way:

* The cyanrip fork's contract generator filtered its fatal inventory through its
  own 21-word ``FATAL_PREFIXES`` allowlist. Handshake round 5 replaced it with a
  control-flow derivation and the inventory went **88 → 104**: the allowlist had
  been hiding 16 real strings.
* We then imported their 88 into a fixture and built a standing "we surface
  everything the ripper can say" test on it. That test was green — **because our
  fixture had inherited their allowlist's blind spot.** Re-deriving found that our
  own pattern missed *all* 13 matchable strings the allowlist had hidden,
  including two ordinary hardware failures: ``Offset is unset! To continue with an
  offset of 0, run with -s 0!`` and ``Device does not support changing speeds!``.
  Each of those rendered to the user as a bare "Rip failed."

That is CLAUDE.md's *"verify the behaviour, not the other side's description of
the behaviour"* biting one level deeper than where it was written: the fixture was
a description of their **filter**, so a test against it measured the filter and
not the ripper. Two independent guesses at "what does a diagnostic look like" is
one guess too many.

**What this does instead.** cyanrip's messages are ``printf`` format strings, and
the provider contract publishes them verbatim. So we compile each published format
into a regex — literals escaped, ``%`` conversions replaced by a bounded wildcard —
and match live output against the resulting set. Nothing is guessed: a line is a
diagnostic because the ripper's own inventory says that text exists, not because it
starts with a word we thought sounded bad.

The word-prefix pattern is **kept as a union member**, deliberately. The inventory
describes one pin, and a build newer than our contract will say things the
inventory does not list; the prefixes catch the common shapes of those. So:
inventory-derived for completeness, prefixes for forward tolerance, union for
both. Neither alone was enough — that is the whole lesson.

**Formats that cannot become patterns are excluded with a reason, never dropped
silently.** A format that is nothing but conversions (``"%s"``, ``"%s%s"``) would
compile to a pattern matching *every* line, so it is refused: it would turn every
progress redraw into a fatal-error report. Those are named in
:data:`UNMATCHABLE_FORMATS` and counted, because "we cannot pattern this" and "this
does not exist" are different facts and the second is the one that hides bugs.
"""

from __future__ import annotations

import re
from typing import Final

#: How much of a line past the recognised text we allow. Bounded, per the
#: project's never-unbounded-quantifier rule: a pathological line must not be
#: handed to the regex engine, nor to a QMessageBox.
_TAIL_LIMIT: Final[int] = 400

#: Longest a single ``%`` conversion's substituted value may be. Generous enough
#: for a path or an ffmpeg error string, bounded for the same reason as above.
_CONVERSION_LIMIT: Final[int] = 200

#: A C ``printf`` conversion: ``%s``, ``%08X``, ``%.2f``, ``%li``, ``%%``.
_CONVERSION = re.compile(r"%%|%[-+ #0-9.*]*(?:hh|h|ll|l|j|z|t|L)?[diuoxXeEfgGaAcspn]")

#: The minimum number of literal (non-conversion) characters a format must carry
#: for a pattern built from it to mean anything. ``"%s"`` has zero and would match
#: the world; ``"cdio: \"%s\""`` has seven and is a real fingerprint.
_MIN_LITERAL_CHARS: Final[int] = 6


def format_to_pattern(fmt: str) -> str | None:
    """Turn one published ``printf`` format into a regex, or ``None``.

    ``None`` means the format carries too little literal text to be a fingerprint
    — see :data:`_MIN_LITERAL_CHARS`. Returning ``None`` rather than a
    permissive pattern is the point: a bad pattern here would classify ordinary
    progress output as a fatal error, which is worse than missing the message.
    """
    text = fmt.strip()
    if not text:
        return None

    parts: list[str] = []
    literal_chars = 0
    position = 0
    for match in _CONVERSION.finditer(text):
        literal = text[position : match.start()]
        literal_chars += len(literal.strip())
        parts.append(re.escape(literal))
        if match.group(0) == "%%":
            parts.append(re.escape("%"))
            literal_chars += 1
        else:
            # `[^\n]` not `.` so a pattern can never span lines even if the
            # caller ever hands us a multi-line blob.
            parts.append(f"[^\\n]{{0,{_CONVERSION_LIMIT}}}?")
        position = match.end()
    trailing = text[position:]
    literal_chars += len(trailing.strip())
    parts.append(re.escape(trailing))

    if literal_chars < _MIN_LITERAL_CHARS:
        return None
    return "".join(parts)


def build_matcher(
    formats: list[str], *, extra_prefixes: tuple[str, ...] = ()
) -> tuple[re.Pattern[str], list[str]]:
    """Compile a matcher for ``formats``. Returns ``(pattern, unmatchable)``.

    ``unmatchable`` lists the formats that produced no pattern, so a caller can
    report the count rather than let it vanish. ``extra_prefixes`` are opening
    words matched in addition to the inventory — forward tolerance for a build
    newer than the contract.
    """
    alternatives: list[str] = []
    unmatchable: list[str] = []
    for fmt in formats:
        pattern = format_to_pattern(fmt)
        if pattern is None:
            unmatchable.append(fmt)
        else:
            alternatives.append(pattern)

    for prefix in extra_prefixes:
        # The boundary is what stops `Invalid` matching `Invalidated`. It admits
        # punctuation as well as whitespace because cyanrip's fatals habitually
        # end in `!` and some are the whole line — `Out of memory!` has no space
        # after the prefix at all, and a whitespace-only boundary missed it.
        alternatives.append(re.escape(prefix) + r"(?:[\s!.,:;?]|$)")

    if not alternatives:
        # Never compile an empty alternation: `(?:)` matches everything, which
        # would report every line of output as a ripper error.
        raise ValueError("build_matcher produced no alternatives")

    body = "|".join(alternatives)
    return (
        re.compile(f"^(?:{body})[^\\n]{{0,{_TAIL_LIMIT}}}$"),
        unmatchable,
    )
