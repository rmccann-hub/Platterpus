# SPDX-License-Identifier: GPL-3.0-only
"""``int()`` that cannot raise — the one guard behind every "never raises" parser.

**Why this module exists at all.** CPython 3.11+ refuses to convert a decimal
string longer than 4300 digits: ``int("9" * 4301)`` raises ``ValueError``
(``sys.set_int_max_str_digits``, added as a CVE-2020-10735 denial-of-service
mitigation). A ``\\d+`` regex group is unbounded, so *every* ``int(match.group(…))``
in a parser of external text is a live ``ValueError`` — no matter how carefully
the regex proves the characters are digits. The character class rules out
``int("abc")``; it does nothing about length.

That makes it precisely the shape CLAUDE.md forbids: a parser documented "never
raises" that does. It is also not hypothetical — it was found and fixed once, in
:mod:`platterpus.parsers.cyanrip_log`, whose seven numeric fields were all
demonstrated raising (review finding, 2026-07-28). The fix was applied *only
there*, and the pinned regression test in ``tests/test_parsers_property.py``
covered *only* that parser, so six identical holes in five other modules
survived — the EAC-log, cd-info, cyanrip-info and whipper-log parsers, the
``whipper.conf`` offset scanner and the CTDB ``.cue`` reader.

That is the failure ``docs/testing.md`` §5.o names: **enforce a rule across the
codebase, not at the place it was learned.** So the guard now lives in one shared
module every caller routes through, and
``tests/test_never_raises_contract.py`` sweeps for unguarded ``int()`` calls
rather than trusting the next author to remember.

Callers treat ``None`` as "this field is unknown", which is what a best-effort
parser is supposed to return for text it cannot use.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# How much of an unusable value to put in the log record. A 4301-digit run is
# the case this module exists for, and pasting it whole into log.txt would bury
# every other line around it — the first few characters plus the length is
# everything a reader needs to recognise "a corrupt numeric field".
_LOGGED_CHARS: int = 32


def int_or_none(raw: object, *, field: str = "") -> int | None:
    """``int(raw)`` when that is possible, otherwise ``None``. Never raises.

    Use this at **every** point where a parser turns external text into a number.
    It is deliberately total: ``ValueError`` (non-numeric text, or a digit run
    over CPython's 4300-digit conversion limit) and ``TypeError`` (a duck-typed
    object that isn't number-like at all) both degrade to ``None``.

    ``field`` names the thing being parsed so the log line says *which* value was
    unusable — "unusable integer for Copy CRC track number" is diagnosable, a
    bare "unusable integer" is not (CLAUDE.md: a dependency's bad output must be
    captured and logged, never swallowed). It is a keyword argument, and optional,
    so adding the guard to a call site is never blocked by not having a good name
    for it.
    """
    try:
        # Annotated rather than returned directly: `int()`'s overload for a bare
        # `object` yields `Any`, and returning that would silently un-type every
        # caller. Naming the local asserts the type instead of suppressing the
        # warning — one `ignore` for the deliberately-total call, none for the
        # return.
        value: int = int(raw)  # type: ignore[call-overload]  # total by design
    except (TypeError, ValueError):
        text = repr(raw)
        log.warning(
            "unusable integer%s: %s%s — recording as unknown",
            f" for {field}" if field else "",
            text[:_LOGGED_CHARS],
            f"… ({len(text)} chars)" if len(text) > _LOGGED_CHARS else "",
        )
        return None
    return value
