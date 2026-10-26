# SPDX-License-Identifier: GPL-3.0-only
"""The two per-track keys the fork's ``-j`` record gains at ``cyanrip-diagnostics/11``.

**What they are, and where they were agreed.**

* ``kept_read_began``: when the read a track's files carry began, the record's
  copy of ``.27``'s ``Kept read began:`` log line (:mod:`platterpus.kept_read`).
  The fork built the line in ``.27`` and held the key back (their round 36 lap 7
  S15), because a new key moves the record to ``/11``, which our reader had to
  accept first (our round 36 lap 3 S5).
* ``isrc_disc_read``: which read found the disc's own ISRC for this track, one of
  ``read sub-channel``, ``q frames`` or ``read sub-channel, again`` (their round
  36 lap 4 S12). ``.26`` asks libcdio first; when it returns none, it reads 200
  of the track's own Q frames, and when those carry none it asks libcdio again
  with the drive's head inside the track (their lap 4 S6). The log's ``Disc
  ISRC:`` line prints the code and not which of the three found it, which their
  lap 4 S8 called their gap; this key closes it.

**Neither key is built yet** (their lap 7 S15: both wait for the release of ours
that reads ``/11``). So this module reads the shapes the fork proposed, and is
tolerant where the shape is not settled: the instant is read by the record's form
in :func:`platterpus.kept_read.began_instant` (an explicit offset allowed), and a
read word outside the three is kept as the record states it, screened and
bounded, with the state ``unrecognised``, never dropped and never guessed into one
of the three.

**How ``/11`` is accepted.** Every reader of the record recognises it by the
schema PREFIX (``ripper_ending.RECORD_SCHEMA_PREFIX``), never by its number, so a
``/11`` record was never refused. Accepting it means reading what it adds; a
``/10`` record, which lacks both keys, reads exactly as it did, with both new
states ``not_present``.

**Tri-state.** ``not_present``: the key is absent (``/10`` and earlier).
``not_stated``: the key is there and ``null`` (a data track, a track not read, no
disc ISRC found). ``read``: a value we can read. ``unrecognised``: a value of the
wrong type or form. Never a negative for something we could not read.

**Read once, with the rest of the row.** This module opens nothing:
:func:`platterpus.isrc_provenance.parse_isrcs`, the one reader of
``rip.track_state``, hands each row here. Pure, Qt-free, never raises.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from platterpus import inbound_text, kept_read

#: The record's keys, spelled once.
KEPT_READ_BEGAN_KEY: Final[str] = "kept_read_began"
ISRC_DISC_READ_KEY: Final[str] = "isrc_disc_read"

#: The three reads that can find a disc ISRC, as the fork proposed them (their
#: round 36 lap 4 S12), in the order ``.26`` tries them (their lap 4 S6).
ISRC_DISC_READS: Final[tuple[str, ...]] = (
    "read sub-channel",
    "q frames",
    "read sub-channel, again",
)

#: The four states of each key. ``READ`` and ``NOT_PRESENT`` are
#: :mod:`platterpus.kept_read`'s own words, so the log's state and the record's
#: read the same for the same fact.
READ: Final[str] = kept_read.READ
NOT_PRESENT: Final[str] = kept_read.NOT_PRESENT
NOT_STATED: Final[str] = "not_stated"
UNRECOGNISED: Final[str] = kept_read.UNRECOGNISED
STATES: Final[frozenset[str]] = frozenset({READ, NOT_PRESENT, NOT_STATED, UNRECOGNISED})

#: An unrecognised read word is kept, cut past this many characters and the cut
#: counted (the three proposed words are under 25).
MAX_VALUE_CHARS: Final[int] = 64


@dataclass(frozen=True)
class TrackRecordV11:
    """One ``track_state`` row's two ``/11`` keys, as the record states them."""

    #: The instant in UTC (``YYYY-MM-DDTHH:MM:SSZ``) when the state is ``read``.
    kept_read_began: str | None = None
    kept_read_began_state: str = NOT_PRESENT
    #: The record's word: one of :data:`ISRC_DISC_READS` when ``read``; for
    #: ``unrecognised``, the value as stated (screened and bounded); else None.
    isrc_disc_read: str | None = None
    isrc_disc_read_state: str = NOT_PRESENT


def parse_row(row: Mapping[str, object]) -> TrackRecordV11:
    """The two ``/11`` keys of one ``track_state`` row. Pure; never raises."""
    began, began_state = _kept_read_began(row)
    word, word_state = _isrc_disc_read(row)
    return TrackRecordV11(
        kept_read_began=began,
        kept_read_began_state=began_state,
        isrc_disc_read=word,
        isrc_disc_read_state=word_state,
    )


def _kept_read_began(row: Mapping[str, object]) -> tuple[str | None, str]:
    if KEPT_READ_BEGAN_KEY not in row:
        return None, NOT_PRESENT
    value = row.get(KEPT_READ_BEGAN_KEY)
    if value is None:
        return None, NOT_STATED
    state, instant = kept_read.instant_state(value, offset_allowed=True)
    return (instant or None), state


def _isrc_disc_read(row: Mapping[str, object]) -> tuple[str | None, str]:
    if ISRC_DISC_READ_KEY not in row:
        return None, NOT_PRESENT
    value = row.get(ISRC_DISC_READ_KEY)
    if value is None:
        return None, NOT_STATED
    if not isinstance(value, str):
        # A number or an object where a word belongs: said, and unreadable.
        return None, UNRECOGNISED
    if value in ISRC_DISC_READS:
        return value, READ
    return _bounded(value), UNRECOGNISED


def _bounded(value: str) -> str:
    """A value as a reader may see it: control characters escaped, cut counted."""
    text = inbound_text.screen_line(value).text
    if len(text) <= MAX_VALUE_CHARS:
        return text
    cut = len(text) - MAX_VALUE_CHARS
    return f"{text[:MAX_VALUE_CHARS]}… [{cut} more characters]"
