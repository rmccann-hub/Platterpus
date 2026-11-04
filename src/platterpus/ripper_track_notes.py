# SPDX-License-Identifier: GPL-3.0-only
"""Three track-block lines the fork proposes for ``.29``, read before it is built.

The fork's round 38 lap 1 proposes each with its wording and asks that a release
of ours read it first (its S7, S8 and S9). None is built at the lap's pin
(``cyanrip@3f288fb``), so the wordings here are the lap's, and every reader is
tolerant where the lap leaves a detail open.

* **``Filtered:``** (their S7, the review's A6). When a filter changed the audio
  written, a line after the track's ``Accurip`` rows::

      Filtered:      hdcd; the checksums and AccurateRip verdicts above are of the read, before the filter

  with ``hdcd``, ``de-emphasis`` or both. The filters are libavfilter's
  ``hdcd`` and ``aemphasis``, chained in that order when both run
  (``cyanrip@3f288fb:src/cyanrip_encode.c:615-628``), so the checksums printed
  above are of samples the files no longer hold. **Our rips cannot print it**:
  we never send ``-H``, and we send ``-W``, which turns automatic de-emphasis
  off. It is read so that, should it ever appear, every place a track's verdict
  is shown says so, and never claimed otherwise. The lap does not say how the
  two names are joined when both ran; ``, ``, `` and `` and ``+`` are read, in
  any order, and anything else is kept as ``unrecognised``.
* **``Pregap length: A or B frames (undecided)``** (their S8, our round 37 lap 6
  S11). Where a sub-channel search narrowed the pre-gap to one sector without
  deciding it, A the shorter and B the longer, in the place the track block
  read ``unknown (sub-channel search bounds did not meet)``. **It is a range,
  never A**: the parser keeps the track's pre-gap *not determined*
  (``pregap_state`` ``unknown``) and carries the two bounds beside it, so no
  reader can take either bound for the length. The cue sheet will carry
  ``INDEX 00`` at the earlier bound, B frames before ``INDEX 01``; our cue
  audit judges a marker only against a pre-gap whose state is ``known``
  (``rip_audit``), so that marker is neither required nor called spurious.
* **``Embedded cover art: none (...)``** (their S9, the review's B6). A cover
  fetched during the rip that the output cannot hold prints
  ``  Embedded cover art: none (the output cannot hold a <codec> picture; saved
  as <file>)``, where ``.28`` logged it as embedded although the muxer dropped
  it. Our rips send ``-G`` (``adapters/cyanrip_backend.py``), which turns
  cyanrip's own embedding off, so neither this nor the old two-line form
  (``  Embedded cover art:`` then ``    Front: 500x500 JPEG``,
  ``cyanrip@3f288fb:src/cyanrip_log.c:914-937``) reaches our logs; our own
  embedding is the report's ``cover_art`` block, graded on the files themselves
  (``uiscript/tag_grading.grade_cover_art``). Read so that a log saying
  ``none`` is never read as a picture embedded.

Pure, Qt-free, never raises. Imports nothing from the parser, so the parser and
:mod:`platterpus.parsers.rip_log` take the dataclasses from here without a cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, TypedDict

from platterpus import diagnostics, inbound_text
from platterpus.safe_int import int_or_none

# --- S7: Filtered ---------------------------------------------------------------

#: The line, indented as the track block's other rows. Recognises only; the
#: value is read by :func:`read_filtered`.
FILTERED_LINE: Final[re.Pattern[str]] = re.compile(
    r"^\s{1,8}Filtered:\s+(?P<value>\S(?:.{0,398}\S)?)\s*$"
)

#: The fixed tail after the filter names, word for word from the lap.
FILTERED_TAIL: Final[str] = (
    "; the checksums and AccurateRip verdicts above are of the read, before the filter"
)

#: The two filter names the lap gives, in the order the chain runs them.
FILTER_NAMES: Final[tuple[str, ...]] = ("hdcd", "de-emphasis")

#: How the names may be joined: a comma, ``and`` or ``+``.
_JOIN: Final[re.Pattern[str]] = re.compile(r"\s{0,4}(?:,|\+|\band\b)\s{0,4}")

# --- S8: an undecided pre-gap ---------------------------------------------------

#: ``Pregap length: A or B frames (undecided)``. Bounded digits, both bounds
#: required, the whole value pinned so nothing else reads as a range.
PREGAP_LENGTH_UNDECIDED: Final[re.Pattern[str]] = re.compile(
    r"^\s{1,8}Pregap length:\s+(?P<shorter>\d{1,9})\s+or\s+(?P<longer>\d{1,9})"
    r"\s+frames\s+\(undecided\)\s*$"
)

# --- S9: Embedded cover art -------------------------------------------------------

#: The header line, alone (the two-line form) or with ``.29``'s value after it.
EMBEDDED_COVER_ART_LINE: Final[re.Pattern[str]] = re.compile(
    r"^\s{1,8}Embedded cover art:(?:\s+(?P<value>\S(?:.{0,598}\S)?))?\s*$"
)

_NONE_HEAD: Final[str] = "none (the output cannot hold a "
_NONE_MIDDLE: Final[str] = " picture; saved as "

# --- states -----------------------------------------------------------------------

#: A line read in the wording the lap gives.
READ: Final[str] = "read"
#: A line that is there, in a wording we do not read: kept, bounded and screened.
UNRECOGNISED: Final[str] = "unrecognised"
#: ``Embedded cover art:`` with nothing after it: the ripper says it embedded a
#: picture, named on the next line. Its claim, not a check of the file.
COVER_STATED_EMBEDDED: Final[str] = "stated_embedded"
#: ``Embedded cover art: none (...)``: the file holds no picture from the ripper.
COVER_NONE: Final[str] = "none"

#: An unrecognised value is kept as its head and tail, the middle counted.
_KEEP_HEAD: Final[int] = 200
_KEEP_TAIL: Final[int] = 100


def _kept(value: str) -> str:
    bounded = diagnostics.bounded_chars(value, head=_KEEP_HEAD, tail=_KEEP_TAIL)
    return inbound_text.screen_line(bounded).text


@dataclass(frozen=True)
class TrackFilter:
    """A track's ``Filtered:`` line: which filters changed the audio written."""

    state: str
    filters: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class RipperCoverArt:
    """A track's ``Embedded cover art:`` line, as the RIPPER states it.

    Never our own embedding (the report's ``cover_art``): what cyanrip's log
    said it did with a picture it was handed or fetched.
    """

    state: str
    text: str
    codec: str | None = None
    saved_as: str | None = None


class TrackFilterBlock(TypedDict):
    """The report's per-track ``filtered`` (schema 43); null when no line."""

    state: str
    filters: list[str]
    #: Why it matters, in a sentence, or the value as printed when unrecognised.
    text: str


class RipperCoverArtBlock(TypedDict):
    """The report's per-track ``ripper_cover_art`` (schema 43); null when no line."""

    state: str
    codec: str | None
    saved_as: str | None
    text: str


def read_filtered(value: object) -> TrackFilter:
    """The ``Filtered:`` line's value as a :class:`TrackFilter`. Never raises.

    Read only when it ends in the lap's tail and every name before it is one of
    :data:`FILTER_NAMES`, each once; anything else is :data:`UNRECOGNISED`, kept.
    """
    if not isinstance(value, str):
        return TrackFilter(UNRECOGNISED, (), _kept(repr(value)))
    text = value.strip()
    kept = _kept(text)
    if not text.endswith(FILTERED_TAIL):
        return TrackFilter(UNRECOGNISED, (), kept)
    names = [n for n in _JOIN.split(text[: -len(FILTERED_TAIL)].strip()) if n]
    if not names or len(set(names)) != len(names):
        return TrackFilter(UNRECOGNISED, (), kept)
    if any(name not in FILTER_NAMES for name in names):
        return TrackFilter(UNRECOGNISED, (), kept)
    ordered = tuple(name for name in FILTER_NAMES if name in names)
    return TrackFilter(READ, ordered, kept)


def filter_sentence(track_filter: TrackFilter | None) -> str:
    """What a reader is told beside the track's verdict, or ``""``. Never raises.

    For :data:`READ`, the filters and what follows from them; for an unrecognised
    line, that one was printed and could not be read, which is still a reason not
    to take the checksums as the file's.
    """
    if not isinstance(track_filter, TrackFilter):
        return ""
    if track_filter.state != READ:
        return (
            "the ripper printed a 'Filtered:' line this version does not read "
            f"({track_filter.text!r}); the checksums above may not be of the file"
        )
    names = " and ".join(track_filter.filters)
    return (
        f"{names} changed the audio written; the CRCs and AccurateRip results "
        "above are of the read, before the filter, not of the file"
    )


def filter_block(track_filter: TrackFilter | None) -> TrackFilterBlock | None:
    """The report's per-track ``filtered``, or None for no line. Never raises."""
    if not isinstance(track_filter, TrackFilter):
        return None
    return {
        "state": track_filter.state,
        "filters": list(track_filter.filters),
        "text": filter_sentence(track_filter),
    }


#: ``issues`` code: a track's audio was changed by a filter after its checksums.
ISSUE_FILTERED: Final[str] = "track_audio_filtered"


def filter_findings(tracks: object) -> list[tuple[str, str]]:
    """``(issue code, sentence)`` per serialized track row with a ``filtered`` block.

    Empty for every rip of ours, which sends no filter. Never raises.
    """
    found: list[tuple[str, str]] = []
    for row in tracks if isinstance(tracks, list) else ():
        block = row.get("filtered") if isinstance(row, dict) else None
        if isinstance(block, dict):
            found.append(
                (ISSUE_FILTERED, f"track {row.get('number')}: {block.get('text')}")
            )
    return found


def read_undecided(match: re.Match[str]) -> tuple[int, int] | None:
    """``(shorter, longer)`` from a :data:`PREGAP_LENGTH_UNDECIDED` match.

    Ordered whatever the order printed. ``None`` when the two are equal, which is
    not a range: the line then decides nothing and the pre-gap stays as the
    track's other rows left it. Never raises.
    """
    first = int_or_none(match.group("shorter"), field="Pregap length undecided A")
    second = int_or_none(match.group("longer"), field="Pregap length undecided B")
    if first is None or second is None or first == second:
        return None
    return (min(first, second), max(first, second))


def undecided_text(pair: tuple[int, int] | None) -> str:
    """``"94 or 95 frames, undecided"``, or ``""``. Never raises."""
    if not pair:
        return ""
    return f"{pair[0]} or {pair[1]} frames, undecided"


def read_cover_art(value: str | None) -> RipperCoverArt:
    """The ``Embedded cover art:`` line as a :class:`RipperCoverArt`. Never raises.

    ``None`` or empty is the two-line form's header: :data:`COVER_STATED_EMBEDDED`.
    A value starting ``none`` is :data:`COVER_NONE` whatever follows, the codec
    and the saved file read when the parenthetical is the lap's: a ``none`` is
    never read as a picture embedded. Anything else is :data:`UNRECOGNISED`.
    """
    if value is None or not isinstance(value, str) or not value.strip():
        return RipperCoverArt(COVER_STATED_EMBEDDED, "")
    text = value.strip()
    kept = _kept(text)
    if text != "none" and not text.startswith("none "):
        return RipperCoverArt(UNRECOGNISED, kept)
    codec: str | None = None
    saved_as: str | None = None
    if text.startswith(_NONE_HEAD) and text.endswith(")"):
        inner = text[len(_NONE_HEAD) : -1]
        said_codec, middle, said_file = inner.partition(_NONE_MIDDLE)
        if middle and said_codec and said_file:
            codec, saved_as = _kept(said_codec), _kept(said_file)
    return RipperCoverArt(COVER_NONE, kept, codec=codec, saved_as=saved_as)


def cover_art_block(art: RipperCoverArt | None) -> RipperCoverArtBlock | None:
    """The report's per-track ``ripper_cover_art``, or None for no line."""
    if not isinstance(art, RipperCoverArt):
        return None
    return {
        "state": art.state,
        "codec": art.codec,
        "saved_as": art.saved_as,
        "text": art.text,
    }
