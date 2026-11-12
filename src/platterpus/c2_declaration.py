# SPDX-License-Identifier: GPL-3.0-only
"""cyanrip's ``C2 errors:`` header line: what the drive DECLARES, and whether C2 was used.

**What the line is.** Every cyanrip build prints one disc-header line about C2
error pointers. Its value comes from libcdio's drive capabilities, which are read
off the drive's capabilities page (MODE SENSE page 2Ah): a DECLARATION, never a
measurement. The wordings, each from the source that prints it:

* upstream: ``supported by drive`` / ``unsupported by drive``
  (``cyanrip@648b1ddd:src/cyanrip_log.c:275-276``, the fork repository's
  ``master``, which carries upstream's history);
* the fork today: ``supported by drive, not used`` / ``unsupported by drive``, and
  ``unknown (capabilities query failed)`` when the query itself failed
  (``cyanrip@54d66666:src/drive_caps.c:117-122``);
* the fork's PROPOSAL for a later build (their round 39 lap 3 S14,
  ``docs/handshake/inbound/round-39-lap-03.md``; NOT BUILT, read here before any
  build prints it): ``not declared by drive (capabilities page, not measured)``
  and ``declared supported by drive (capabilities page), not used``, worded as the
  ``Accurate stream:`` line words its own declaration, the failed-query form
  unchanged.

**Why the proposal exists, and why this module reads the old words the new way.**
The fork's C2 probe of 2026-11-11 found that the Pioneer BDR-209D, whose page
2Ah does not declare C2 (so cyanrip prints ``unsupported by drive``), returns C2
error pointers anyway: three bits at LBA 83430, in track 5's error, in all four
reads (their lap 3 S11, filed at ``cyanrip@74b6f0a``; our probe's own
``summary.txt`` there reads ``t5-c2-1.bin: frame 14 (3 bits)`` for each read).
So ``unsupported by drive`` was never a fact about the drive. It is what the
page says. This module therefore reads BOTH spellings of each branch into ONE
state, worded as a statement about the page:

* ``declared_supported``: the page declares C2;
* ``not_declared``: the page does not declare C2. **Never "the drive cannot"**: a
  drive whose page is silent may still return C2 pointers, as this one does;
* ``unknown``: the capabilities query failed, so nothing was declared either way;
* ``unrecognised``: the line is there in a wording this build does not know, the
  value kept (bounded) as the reason and a warning logged;
* ``not_present``: no ``C2 errors:`` line at all (another ripper's log).

A relabelling of the same branch must not change our answer
(``CLAUDE.md``: *if they relabelled this without changing the artifact, would my
answer change?*), so ``unsupported by drive`` and the proposed ``not declared by
drive (…)`` give the same state, and the same EAC answer below.

**Whether the rip USED C2** is a second question, the one EAC's ``Make use of C2
pointers`` row asks, and it is answered separately by :func:`c2_used`. In the
fork's source neither branch reads with C2: the declared branch says so in its
own words (``supported by drive, not used``, ``drive_caps.c:121``), and the one
READ CD the fork builds itself asks for no C2 (``c2_error_information = 0``,
``cyanrip@54d66666:src/pregap.c:206``). So a not-declared line is a truthful
"No", for the reason that the ripper did not ask for C2 — never because the drive
could not give it.

Pure, Qt-free, never raises. Imports nothing from the parser, so the parser can
take it without a cycle (``tests/test_c2_declaration.py`` holds every wording and
the never-raises property).
"""

from __future__ import annotations

import logging
import re
from typing import Final

from platterpus import diagnostics

log = logging.getLogger(__name__)

#: The capabilities page declares C2 error pointers.
C2_DECLARED_SUPPORTED: Final[str] = "declared_supported"
#: The capabilities page does not declare them. A statement about the page: the
#: BDR-209D's page is silent and the drive returns them (round 39 lap 3 S11).
C2_NOT_DECLARED: Final[str] = "not_declared"
#: The capabilities query failed, so the page said nothing either way.
C2_UNKNOWN: Final[str] = "unknown"
#: The line is there, in a wording this build does not recognise. Spelled as
#: ``parsers.rip_log.DRIVE_FACT_UNRECOGNISED`` so one word means one thing in the
#: report's ``rip`` block (the test module holds the two equal).
C2_UNRECOGNISED: Final[str] = "unrecognised"
#: No ``C2 errors:`` line was printed. Spelled as ``DRIVE_FACT_NOT_PRESENT``.
C2_NOT_PRESENT: Final[str] = "not_present"
#: Every state ``RippingInfo.c2_declared`` can hold.
C2_DECLARED_STATES: Final[frozenset[str]] = frozenset(
    {
        C2_DECLARED_SUPPORTED,
        C2_NOT_DECLARED,
        C2_UNKNOWN,
        C2_UNRECOGNISED,
        C2_NOT_PRESENT,
    }
)

#: Each fixed wording, exactly as printed, with the state it means and the
#: reason (the ripper's own parenthetical, "" when it has none). A table rather
#: than a pattern, so a wording no build prints is ``unrecognised`` instead of
#: being squeezed into a state.
_FIXED_WORDINGS: Final[dict[str, tuple[str, str]]] = {
    # upstream `cyanrip@648b1ddd:src/cyanrip_log.c:275-276`
    "supported by drive": (C2_DECLARED_SUPPORTED, ""),
    # upstream, and the fork today (`cyanrip@54d66666:src/drive_caps.c:121`)
    "unsupported by drive": (C2_NOT_DECLARED, ""),
    # the fork today (`drive_caps.c:121`)
    "supported by drive, not used": (C2_DECLARED_SUPPORTED, ""),
    # PROPOSED, round 39 lap 3 S14 (not built)
    "not declared by drive (capabilities page, not measured)": (
        C2_NOT_DECLARED,
        "capabilities page, not measured",
    ),
    # PROPOSED, round 39 lap 3 S14 (not built)
    "declared supported by drive (capabilities page), not used": (
        C2_DECLARED_SUPPORTED,
        "capabilities page",
    ),
}

#: ``unknown`` with an optional parenthetical: the fork's failed-query form,
#: ``unknown (capabilities query failed)`` (``drive_caps.c:120``), unchanged by
#: the proposal. Any reason is taken, bounded: a reworded reason is still the
#: ripper saying it does not know, which is never a "no".
_UNKNOWN_VALUE: Final[re.Pattern[str]] = re.compile(
    r"^unknown(?:\s\((?P<reason>[^()\n]{1,120})\))?$"
)

#: How much of an unrecognised value is kept as its reason: head and tail, the
#: gap counted, as the `.26` drive facts keep theirs.
_UNRECOGNISED_HEAD: Final[int] = 100
_UNRECOGNISED_TAIL: Final[int] = 60


def c2_declaration_state(value: str) -> tuple[str, str]:
    """Read a ``C2 errors:`` value as ``(state, reason)``.

    ``state`` is one of :data:`C2_DECLARED_STATES` except ``not_present`` (the
    absence of the line is the caller's to decide), and ``reason`` is the
    ripper's parenthetical verbatim, "" when there is none:

    * ``supported by drive``, ``supported by drive, not used`` and the proposed
      ``declared supported by drive (capabilities page), not used`` →
      ``declared_supported``;
    * ``unsupported by drive`` and the proposed ``not declared by drive
      (capabilities page, not measured)`` → ``not_declared``. The page's
      silence, never "the drive cannot";
    * ``unknown (capabilities query failed)`` → ``unknown`` with that reason;
    * anything else → ``unrecognised``, the value kept (bounded) as the reason,
      and a warning in the log file naming the line.

    Pure and never raises (a parser of external output).
    """
    text = value.strip()
    fixed = _FIXED_WORDINGS.get(text)
    if fixed is not None:
        return fixed
    unknown = _UNKNOWN_VALUE.match(text)
    if unknown is not None:
        return C2_UNKNOWN, unknown.group("reason") or ""
    bounded = diagnostics.bounded_chars(
        text, head=_UNRECOGNISED_HEAD, tail=_UNRECOGNISED_TAIL
    )
    log.warning(
        "cyanrip's C2 errors: line reads %r, a wording this build does not "
        "recognise; recorded as unrecognised with the value kept",
        bounded,
    )
    return C2_UNRECOGNISED, bounded


def c2_used(value: str) -> bool | None:
    """EAC's ``Make use of C2 pointers``: ``False`` = not used, ``None`` = not stated.

    Never ``True``: no build we read uses C2, and ``not used`` contains the
    substring ``used``, so an affirmative branch would be a way to fabricate
    EAC's "Yes" (the reason the parser has never had one).

    * a ``not_declared`` line (either spelling) → ``False``: the ripper did not
      ask the drive for C2, on the page's word (see the module docstring for the
      fork's source). Not "the drive cannot": that is the claim S14 retires;
    * a line that says ``not used`` → ``False``, a statement about the rip;
    * upstream's bare ``supported by drive`` and the failed-query ``unknown``
      → ``None``: a declaration, or none, says nothing about use;
    * an unrecognised wording keeps the substring reading the parser had before
      this module (``unsupported`` / ``not supported`` / ``disabled`` / ``off`` /
      ``not used`` / ``unused`` / ``never used`` → ``False``, else ``None``), so a
      reword never turns an earned "No" into a guess, nor a guess into a "No".

    Pure and never raises. Logs nothing: :func:`c2_declaration_state` reports an
    unrecognised wording once.
    """
    text = value.strip()
    fixed = _FIXED_WORDINGS.get(text)
    if fixed is not None:
        state = fixed[0]
        if state == C2_NOT_DECLARED or text.endswith(", not used"):
            return False
        return None
    if _UNKNOWN_VALUE.match(text) is not None:
        return None
    folded = text.casefold()
    negatives = (
        "unsupported",
        "not supported",
        "disabled",
        "off",
        "not used",
        "unused",
        "never used",
    )
    if any(word in folded for word in negatives):
        return False
    return None
