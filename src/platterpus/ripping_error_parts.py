# SPDX-License-Identifier: GPL-3.0-only
"""The parts of cyanrip's ``Ripping errors:`` count, each one named.

**Why it exists.** cyanrip's footer prints one number, ``Ripping errors: N``, and
that number adds things that are not alike: frame reads the drive failed, sectors
whose EDC check failed, stretches paranoia gave up verifying (its "skips"),
tracks that did not finish, and disc lookups that failed. From the fork's
``+platterpus.20`` it names one of them, ``Ripping errors: N (including M
paranoia skips)``, so our read-speed ladder could take the skips back out
(``RipLog.drive_read_errors``). Our round 38 lap 4 S12 asked for every part to be
named instead, "so no frame is counted twice by us either", and the fork's
round 41 lap 1 S16 proposes the wording, for a build after ``.33``::

    Ripping errors: 57 (28 frame reads failed, 28 paranoia skips, 1 track not finished)

The leading count and its prefix are unchanged. Each part that is not zero is
printed, in this order: ``frame reads failed``, ``sectors failing EDC``,
``paranoia skips``, ``tracks not finished``, ``disc lookups failed``. The fork
stops printing the old ``(including N paranoia skips)`` only after a release of
ours reads BOTH, so this module reads both, before any build prints the new one
(round 20's order: the reader ships first).

**What the lap leaves open, read tolerantly.** Its one example of a count of 1 is
``1 track not finished``, so a singular is printed for 1; it does not spell the
other four singulars, so each label is read singular or plural whatever the
number beside it says. We key on the LABEL, never on the position, so a part
printed out of the promised order is still read as itself.

**A part we do not know is kept, counted and logged, never dropped.** A future
build may add a sixth part, or reword one. Dropping it would make the parts we
did read look like the whole count (CLAUDE.md, *diagnostic completeness*: "a
silent truncation reads as completeness"). So it is kept verbatim (screened and
bounded) in :attr:`RippingErrorParts.unknown`, the number of entries we had to
leave out is counted in :attr:`RippingErrorParts.unknown_elided`, and the parser
logs a warning naming it.

**Which way is safe when a part is missing.** Under the new wording a part that
is not printed is zero, because only non-zero parts are printed. That holds only
while we recognise every part on the line: if one part is unknown, it might be a
part we know under a new name, so every known part that is absent reads as
``None`` ("not determined"), never 0. The read-speed ladder subtracts the skips
from the count to get the drive's own errors; reading an unknown skip count as 0
would hand the ladder skips as drive errors and step a disc down for paranoia's
work, while ``None`` only makes it say less (``ladder_trigger``). Same rule for
the old wording: a suffix we cannot read is not evidence that there were no
skips.

Pure, Qt-free, never raises. It imports nothing from the parser, so the parser
and ``RipLog`` can both take the dataclass from here without a cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from platterpus import diagnostics, inbound_text
from platterpus.safe_int import int_or_none

#: Above this, a count is not a count of anything on a CD (about 360,000
#: sectors), and is stored as "not determined". The parser's own bound for the
#: leading count is this same constant, so the two cannot drift apart.
MAX_PLAUSIBLE_COUNT: Final[int] = 10**9

# --- Which wording the line used --------------------------------------------
#: ``Ripping errors: N`` and nothing after it: every build before ``.20``, and a
#: later build on a rip with no skips (and, under the new wording, no parts).
FORM_COUNT_ONLY: Final[str] = "count_only"
#: ``.20``'s ``(including M paranoia skips)``.
FORM_INCLUDING: Final[str] = "including"
#: The round 41 lap 1 S16 wording, each part named.
FORM_NAMED: Final[str] = "named"
#: Something follows the count that is neither wording; kept in ``unknown``.
FORM_UNRECOGNISED: Final[str] = "unrecognised"

# --- The five parts the lap names, singular and plural ----------------------
#: Label as printed (whitespace collapsed) -> the field it fills. Both numbers
#: are listed for every label, because the lap spells only one singular.
_LABELS: Final[dict[str, str]] = {
    "frame reads failed": "frame_reads_failed",
    "frame read failed": "frame_reads_failed",
    "sectors failing EDC": "sectors_failing_edc",
    "sector failing EDC": "sectors_failing_edc",
    "paranoia skips": "paranoia_skips",
    "paranoia skip": "paranoia_skips",
    "tracks not finished": "tracks_not_finished",
    "track not finished": "tracks_not_finished",
    "disc lookups failed": "disc_lookups_failed",
    "disc lookup failed": "disc_lookups_failed",
}

#: The fields, in the order the lap promises to print them.
PART_FIELDS: Final[tuple[str, ...]] = (
    "frame_reads_failed",
    "sectors_failing_edc",
    "paranoia_skips",
    "tracks_not_finished",
    "disc_lookups_failed",
)

#: One part: a count of at most a uint64's twenty digits, then a label of
#: letters and single spaces. A part that does not fit is kept as unknown text.
_PART: Final[re.Pattern[str]] = re.compile(
    r"^(?P<count>\d{1,20})\s{1,4}(?P<label>[A-Za-z](?:[A-Za-z ]{0,78}[A-Za-z])?)$"
)

#: How many unknown parts are kept verbatim; the rest are counted, not kept.
MAX_UNKNOWN_KEPT: Final[int] = 8
#: Characters kept of one unknown part's text, head and tail.
_UNKNOWN_HEAD: Final[int] = 60
_UNKNOWN_TAIL: Final[int] = 20


@dataclass(frozen=True)
class UnknownPart:
    """A part of the line we did not recognise, kept as the ripper printed it.

    ``text`` is screened (control characters flagged) and bounded, head and
    tail, any elision counted. ``count`` is its number when it had the shape
    ``<digits> <words>``, else None: we never invent one.
    """

    text: str
    count: int | None


@dataclass(frozen=True)
class RippingErrorParts:
    """The ``Ripping errors:`` line's parts. Each part is tri-state.

    A part is an int when the line states it (0 under the named wording when
    the part is absent and every printed part was recognised); None when the
    line does not say, which is every part but the skips under the older two
    wordings, and every absent part when an unknown one is printed.
    """

    form: str
    frame_reads_failed: int | None = None
    sectors_failing_edc: int | None = None
    paranoia_skips: int | None = None
    tracks_not_finished: int | None = None
    disc_lookups_failed: int | None = None
    #: Parts we did not recognise, at most :data:`MAX_UNKNOWN_KEPT` of them.
    unknown: tuple[UnknownPart, ...] = ()
    #: Unknown parts left out of ``unknown`` because it was full; never silent.
    unknown_elided: int = 0

    @property
    def unknown_total(self) -> int:
        """Every unknown part the line carried, kept or not."""
        return len(self.unknown) + self.unknown_elided


def _plausible(value: int | None) -> int | None:
    """``value`` if it could be a count on a CD, else None ("not determined")."""
    if value is None or not 0 <= value <= MAX_PLAUSIBLE_COUNT:
        return None
    return value


def _unknown(text: str, count: int | None) -> UnknownPart:
    """An unknown part, screened and bounded, so nothing absurd reaches a log."""
    bounded = diagnostics.bounded_chars(text, head=_UNKNOWN_HEAD, tail=_UNKNOWN_TAIL)
    return UnknownPart(inbound_text.screen_line(bounded).text, count)


def _read_named(parts_text: str) -> RippingErrorParts:
    """Read the named wording's comma-separated parts. Never raises."""
    found: dict[str, int | None] = {}
    unknown: list[UnknownPart] = []
    elided = 0
    for piece in parts_text.split(","):
        text = " ".join(piece.split())  # collapse runs of spaces, strip the ends
        match = _PART.match(text)
        count = (
            _plausible(int_or_none(match.group("count"), field="ripping-error part"))
            if match
            else None
        )
        name = _LABELS.get(match.group("label")) if match else None
        # A known label printed twice is not a part we understand either: keep
        # the second as unknown rather than overwrite or add the first.
        if name is not None and name not in found:
            found[name] = count
            continue
        if len(unknown) < MAX_UNKNOWN_KEPT:
            unknown.append(_unknown(text, count))
        else:
            elided += 1
    # Absent means zero only while every part printed was recognised (see the
    # module docstring: an unknown part may be a known one renamed).
    absent: int | None = 0 if not unknown and not elided else None
    values = {name: found.get(name, absent) for name in PART_FIELDS}
    return RippingErrorParts(
        form=FORM_NAMED,
        frame_reads_failed=values["frame_reads_failed"],
        sectors_failing_edc=values["sectors_failing_edc"],
        paranoia_skips=values["paranoia_skips"],
        tracks_not_finished=values["tracks_not_finished"],
        disc_lookups_failed=values["disc_lookups_failed"],
        unknown=tuple(unknown),
        unknown_elided=elided,
    )


def from_match(match: re.Match[str]) -> RippingErrorParts:
    """The parts of a line the parser's ``Ripping errors:`` pattern matched.

    Reads the pattern's optional ``skips`` group (``.20``'s wording) and its
    optional ``parts`` group (the round 41 lap 1 S16 wording); when neither
    matched, whatever follows the count decides between "nothing" and
    "unrecognised". Never raises.
    """
    groups = match.groupdict()
    skips = groups.get("skips")
    if skips is not None:
        return RippingErrorParts(
            form=FORM_INCLUDING,
            paranoia_skips=_plausible(
                int_or_none(skips, field="cyanrip paranoia skips in Ripping errors")
            ),
        )
    parts = groups.get("parts")
    if parts is not None:
        return _read_named(parts)
    rest = match.string[match.end() :].strip()
    if not rest:
        # No earlier build counted skips (their round 30 lap 9 S11), and a build
        # that names parts prints none when all are zero: 0 skips either way.
        return RippingErrorParts(form=FORM_COUNT_ONLY, paranoia_skips=0)
    return RippingErrorParts(form=FORM_UNRECOGNISED, unknown=(_unknown(rest, None),))


def unknown_summary(parts: RippingErrorParts) -> str:
    """One bounded line naming the unknown parts, for the parser's warning."""
    kept = "; ".join(repr(part.text) for part in parts.unknown)
    if parts.unknown_elided:
        kept += f"; and {parts.unknown_elided} more not kept"
    return kept
