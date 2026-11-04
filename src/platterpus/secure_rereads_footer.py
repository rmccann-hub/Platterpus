# SPDX-License-Identifier: GPL-3.0-only
"""The footer's ``Secure re-reads:`` line, which the fork proposes for ``.29``.

**Why it exists.** Under ``-Z`` each track block says whether its re-reads agreed
(``  Secure re-read:  converged after N reads`` or ``did NOT converge after N
reads (repeat limit hit)``, ``cyanrip@3f288fb:src/cyanrip_log.c:744-751``), but
nothing at the end of the log said how many did not, so a reader of the footer
alone saw ``Ripping errors: 0`` beside a track whose reads never agreed. The
fork's round 38 lap 1 S5 (the review's A5, our round 37 lap 6 S12 (a)) proposes
one line, directly above ``Ripping errors:`` and only under ``-Z``::

    Secure re-reads: every track converged
    Secure re-reads: N track(s) did not converge (track(s) T)

naming the tracks whose re-reads hit the repeat limit or the time limit. **Not
built yet**: this module reads the wording as the lap spells it, before the
build exists, so a release of ours can read it first.

**It is not a read error, and must never become one.** ``Ripping errors:`` keeps
its count and suffix (their S5), and the read-speed ladder keys on the drive's
count inside it (``RipLog.drive_read_errors``), never on this line: a re-read
that did not converge is instability, handled per track by the securing pass
(``read_speed_ladder._instability_explains_arm``). Nothing here feeds the ladder.

**What the lap leaves open, read tolerantly.** ``track(s)`` is the lap's
notation, not necessarily the printed text, so ``track``, ``tracks`` and the
literal ``track(s)`` are all read; ``T`` is read as numbers separated by commas,
spaces or ``and``, and a trailing ``, list truncated`` (the shape the fork's
``Encoder errors:`` uses for a bounded list) is read as a cut list, never as a
whole one. Anything else is kept verbatim, bounded and screened, as
``unrecognised``, with no count invented.

**Tri-state.** No line is ``None`` on the log (an older build, or a rip without
``-Z``), never "every track converged". Pure, Qt-free, never raises; imports
nothing from the parser, so the parser can take the dataclass from here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, TypedDict

from platterpus import diagnostics, inbound_text
from platterpus.data_tracks import is_data_track
from platterpus.safe_int import int_or_none

#: The line, column 0, as the lap spells it. The value is everything after the
#: label; it is read by :func:`read_value`, so the pattern only recognises.
LINE: Final[re.Pattern[str]] = re.compile(
    r"^Secure re-reads:\s+(?P<value>\S(?:.{0,398}\S)?)\s*$"
)

#: The converged arm, word for word.
_ALL_CONVERGED: Final[str] = "every track converged"

#: The other arm. ``tracks?`` or the literal ``track(s)``, both places; the list
#: is digits and separators only, bounded, and may end ``, list truncated``.
_SOME: Final[re.Pattern[str]] = re.compile(
    r"(?P<count>\d{1,3}) track(?:s|\(s\))? did not converge "
    r"\(track(?:s|\(s\))? (?P<list>\d{1,3}(?:(?:,\s?|\s|\s?and\s)\d{1,3}){0,98})"
    r"(?P<truncated>, list truncated)?\)"
)

#: Splits the track list: a comma, ``and``, or whitespace.
_SEPARATOR: Final[re.Pattern[str]] = re.compile(r"\s*(?:,|\band\b)\s*|\s+")

#: The states of the line, and of the report's block.
ALL_CONVERGED: Final[str] = "all_converged"
SOME_DID_NOT_CONVERGE: Final[str] = "some_did_not_converge"
UNRECOGNISED: Final[str] = "unrecognised"
STATES: Final[frozenset[str]] = frozenset(
    {ALL_CONVERGED, SOME_DID_NOT_CONVERGE, UNRECOGNISED}
)

#: ``issues`` code: the footer names different tracks from the track blocks.
ISSUE_DISAGREES: Final[str] = "secure_rereads_footer_disagrees"

#: An unrecognised value is kept as its head and tail, the middle counted.
_KEEP_HEAD: Final[int] = 160
_KEEP_TAIL: Final[int] = 80


@dataclass(frozen=True)
class SecureRereads:
    """The ``Secure re-reads:`` line, read.

    ``count`` and ``tracks`` are the line's own numbers for the second arm (both
    empty for the first, both ``None``/empty for ``unrecognised``); ``truncated``
    is True when the ripper cut the list. ``text`` is the value as printed,
    screened and bounded, kept whatever the state.
    """

    state: str
    text: str
    count: int | None = None
    tracks: tuple[int, ...] = ()
    truncated: bool = False


class SecureRereadsBlock(TypedDict):
    """The report's ``rip.secure_rereads`` (schema 43); null when no line."""

    state: str
    did_not_converge_count: int | None
    did_not_converge_tracks: list[int]
    tracks_truncated: bool
    #: Does the line name the same tracks as the track blocks' ``Secure
    #: re-read:`` rows? Null when either side cannot say.
    agrees_with_track_blocks: bool | None
    text: str


def _kept(value: str) -> str:
    bounded = diagnostics.bounded_chars(value, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text


def read_value(value: object) -> SecureRereads:
    """The line's value as a :class:`SecureRereads`. Never raises."""
    if not isinstance(value, str):
        return SecureRereads(UNRECOGNISED, _kept(repr(value)))
    text = value.strip()
    kept = _kept(text)
    if text == _ALL_CONVERGED:
        return SecureRereads(ALL_CONVERGED, kept, count=0)
    match = _SOME.fullmatch(text) if len(text) <= 400 else None
    if match is None:
        return SecureRereads(UNRECOGNISED, kept)
    count = int_or_none(match.group("count"), field="Secure re-reads count")
    numbers: list[int] = []
    for piece in _SEPARATOR.split(match.group("list")):
        number = int_or_none(piece, field="Secure re-reads track") if piece else None
        if piece and number is None:
            return SecureRereads(UNRECOGNISED, kept)
        if number is not None:
            numbers.append(number)
    truncated = match.group("truncated") is not None
    # A count the list contradicts (more tracks named than counted, or fewer
    # with no cut said) is the line disagreeing with itself: not read.
    if (
        count is None
        or len(numbers) > count
        or (len(numbers) < count and not truncated)
    ):
        return SecureRereads(UNRECOGNISED, kept)
    return SecureRereads(
        SOME_DID_NOT_CONVERGE,
        kept,
        count=count,
        tracks=tuple(numbers),
        truncated=truncated,
    )


def _blocks_not_converged(tracks: Sequence[object]) -> set[int] | None:
    """The tracks whose block says their re-reads did not converge, or None.

    None when a track block cannot say (no ``Secure re-read:`` row), because a
    footer cannot be checked against a block that is silent.
    """
    named: set[int] = set()
    for track in tracks:
        number = getattr(track, "number", None)
        converged = getattr(track, "secure_rerip_converged", None)
        if not isinstance(number, int) or is_data_track(track):
            continue
        if converged is None:
            return None
        if converged is False:
            named.add(number)
    return named


def report_block(
    footer: SecureRereads | None, tracks: Sequence[object] = ()
) -> SecureRereadsBlock | None:
    """``rip.secure_rereads``, or None when the log printed no line. Never raises."""
    if not isinstance(footer, SecureRereads):
        return None
    agrees: bool | None = None
    blocks = _blocks_not_converged(tracks)
    if blocks is not None and footer.state != UNRECOGNISED and not footer.truncated:
        agrees = set(footer.tracks) == blocks
    return {
        "state": footer.state,
        "did_not_converge_count": footer.count,
        "did_not_converge_tracks": list(footer.tracks),
        "tracks_truncated": footer.truncated,
        "agrees_with_track_blocks": agrees,
        "text": footer.text,
    }


def findings(block: object) -> list[tuple[str, str]]:
    """``(issue code, sentence)`` for a block that disagrees with its tracks.

    Information, not a verdict: the per-track rows decide each track, and a
    footer that names other tracks is the log contradicting itself, said so a
    reader looks. Never raises.
    """
    if (
        not isinstance(block, Mapping)
        or block.get("agrees_with_track_blocks") is not False
    ):
        return []
    return [
        (
            ISSUE_DISAGREES,
            f"the ripper's footer says {block.get('text')!r}, which does not name "
            "the same tracks as the track blocks' own 'Secure re-read:' rows; "
            "each track's row is what this report reads",
        )
    ]
