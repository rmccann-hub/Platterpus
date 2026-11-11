# SPDX-License-Identifier: GPL-3.0-only
"""`.31`'s ``--reread-until-accuraterip``: an agreement AccurateRip overruled.

**What the option does** (the fork's ``.31``, built as their round 39 lap 1 S4
says, from our round 38 lap 16 S13 as their lap 17 S8 accepted it). Under ``-Z N``
a track ends when N + 1 reads agree. With ``--reread-until-accuraterip CONF``, an
agreement on a read AccurateRip does NOT match, on a track AccurateRip holds at
confidence CONF or more, does not end the track: it reads on until a read
AccurateRip matches at CONF or more, or a limit (``-r`` or the time limit).

**Why we read it, and why the fail-safe direction matters here.** The reference
disc's track 3 converged on ``3D8FCF0C`` on the owner's drive while AccurateRip
holds ``59D352DD``: reads that agree with each other on the wrong audio. This rule
is what lets the ripper itself refuse that agreement. Without a reader, the head
below matched none of the parser's ``Done;`` patterns, so the track had NO
verdict, and the EAC-layout log infers convergence for an unmeasured track read
two or more times. That is the one direction this project must never be wrong in.

**The lines, verbatim from their source at ``e531a33``** (P2 of
``round-39-lap-01-provider-contract-g6eacb8b.md``, lines 376 and 504 to 512):

* the early end, ``cyanrip@e531a33:src/cyanrip_main.c:2140``::

    Done; (read %i matches AccurateRip at confidence %i; agreement on %08X
    overruled by AccurateRip; kept %08X, read %i time%s)

  ``read %i`` is the read number that matched; ``kept %08X`` that read's EAC
  CRC32 (``vs->crc ^ UINT32_MAX``) and how many reads gave it. A read made BEFORE
  the overrule counts (their S6 second point), so the kept read may be older than
  the agreement it overrules.
* the clause ``agreement on %08X overruled by AccurateRip``, after ``agreed`` in
  each of the four repeat-limit and four time-limit lines
  (``cyanrip@e531a33:src/cyanrip_main.c:2183-2242``): the track reached a limit
  after its agreement was overruled. Those lines keep their limit verdict (not
  converged), and the parser's existing readers keep reading their kept clause.
* the track block's row, ``cyanrip@e531a33:src/cyanrip_log.c:852``::

      Secure re-read:  matched AccurateRip after %i reads (agreement on %08X overruled)

  printed only for a track the early end closed. At a limit after an overrule
  the row keeps its ``did NOT converge`` form, and only the ``Done;`` line names
  the overrule (their S6 fourth point).

**The verdict is "did not converge", and the fork says so** (their S6 fifth
point: such a track "did not converge, and it did not fail"). So the parser files
these as not converged, the fail-safe direction, and this module carries the
other half of the fact, that AccurateRip ended the reads, for the per-track
record (``track_record_sources.ar_guided_convergence``) and for the footer check
(``secure_rereads_footer``), which must not count such a track as one the
footer's ``did not converge`` list should name.

**The first agreement overruled is the one named** (their S6 first point).

Pure, Qt-free, never raises; every number bounded so each pattern is linear
(`tests/test_regex_bounded_time.py`). Imports nothing from the parser, so the
parser and :mod:`platterpus.parsers.rip_log` can take the dataclass from here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from platterpus.safe_int import int_or_none

#: The early end's head, at any indentation (it comes from the repeat loop before
#: the track opens, as every ``Done;`` line does). It stops at ``time``: the
#: ``%s`` after it is the ripper's plural, which states no fact.
EARLY_END: Final[re.Pattern[str]] = re.compile(
    r"^\s*Done;\s+\(read (?P<read>\d{1,6}) matches AccurateRip at confidence "
    r"(?P<confidence>\d{1,6}); agreement on (?P<overruled>[0-9A-Fa-f]{8}) "
    r"overruled by AccurateRip; kept (?P<kept>[0-9A-Fa-f]{8}), read "
    r"(?P<reads>\d{1,6}) time"
)
#: The clause inside a limit line. A FRAGMENT pattern: searched only in a line the
#: parser's ``_SECURE_DONE_FAIL`` already claimed.
OVERRULE_CLAUSE: Final[re.Pattern[str]] = re.compile(
    r"\bagreement on (?P<overruled>[0-9A-Fa-f]{8}) overruled by AccurateRip\b"
)
#: The track block row's text, after ``Secure re-read:``. A FRAGMENT pattern:
#: matched only against the text the parser's ``_TRACK_SECURE_VERDICT`` captured.
MATCHED_ROW: Final[re.Pattern[str]] = re.compile(
    r"^matched AccurateRip after (?P<reads>\d{1,6}) reads? \(agreement on "
    r"(?P<overruled>[0-9A-Fa-f]{8}) overruled\)"
)


@dataclass(frozen=True)
class AccurateRipOverrule:
    """An agreement AccurateRip overruled under ``.31``'s ``-Z`` rule.

    ``overruled_crc`` is the agreement's checksum, as the line prints it.
    ``ended_on_match`` is True when a read AccurateRip matches ended the track
    (the early end, or its row), False when the track went on to a limit.
    ``matched_read`` and ``confidence`` are the early end's read number and
    AccurateRip confidence; ``kept_crc`` and ``kept_reads`` the read it kept and
    how many reads gave it; ``reads`` the row's total read count. Each is ``None``
    where the line that was read does not state it.
    """

    overruled_crc: str
    ended_on_match: bool
    matched_read: int | None = None
    confidence: int | None = None
    kept_crc: str | None = None
    kept_reads: int | None = None
    reads: int | None = None


def early_end(line: str) -> AccurateRipOverrule | None:
    """The early end's facts, from a whole log line, or ``None``. Never raises.

    A zero read number, confidence or read count is not a match (the option takes
    a confidence from 1, and every read is counted from 1), so it gives ``None``
    rather than a claim AccurateRip vouched for a read.
    """
    if not isinstance(line, str):
        return None
    match = EARLY_END.match(line)
    if match is None:
        return None
    read = int_or_none(match.group("read"), field="cyanrip AccurateRip-matched read")
    confidence = int_or_none(
        match.group("confidence"), field="cyanrip AccurateRip-matched confidence"
    )
    reads = int_or_none(match.group("reads"), field="cyanrip AccurateRip-kept reads")
    if not read or not confidence or not reads:
        return None
    return AccurateRipOverrule(
        overruled_crc=match.group("overruled").upper(),
        ended_on_match=True,
        matched_read=read,
        confidence=confidence,
        kept_crc=match.group("kept").upper(),
        kept_reads=reads,
    )


def limit_overrule(claimed_limit_line: str) -> AccurateRipOverrule | None:
    """The overrule named in a limit line the parser claimed, or ``None``.

    ``None`` for every build before ``.31`` (no clause), so its absence is never
    read as "AccurateRip overruled nothing": it is a line that does not say.
    Never raises.
    """
    if not isinstance(claimed_limit_line, str):
        return None
    match = OVERRULE_CLAUSE.search(claimed_limit_line)
    if match is None:
        return None
    return AccurateRipOverrule(
        overruled_crc=match.group("overruled").upper(), ended_on_match=False
    )


def row_overrule(row_text: str) -> AccurateRipOverrule | None:
    """The ``Secure re-read:  matched AccurateRip …`` row's facts, or ``None``.

    ``row_text`` is the text after the label. Never raises.
    """
    if not isinstance(row_text, str):
        return None
    match = MATCHED_ROW.match(row_text.strip())
    if match is None:
        return None
    reads = int_or_none(match.group("reads"), field="cyanrip AccurateRip-matched reads")
    return AccurateRipOverrule(
        overruled_crc=match.group("overruled").upper(),
        ended_on_match=True,
        reads=reads or None,
    )


def combined(
    buffered: AccurateRipOverrule | None, row: AccurateRipOverrule
) -> AccurateRipOverrule:
    """The row's facts with what the early end added, when they agree.

    The two state halves of one fact: the early end names the matched read, its
    confidence and the kept read; the row names the total read count. Joined only
    when both name the same overruled checksum; otherwise the row stands alone, as
    the parser's verdict does (the row's track is not in question). Pure.
    """
    if buffered is None or buffered.overruled_crc != row.overruled_crc:
        return row
    return AccurateRipOverrule(
        overruled_crc=row.overruled_crc,
        ended_on_match=True,
        matched_read=buffered.matched_read,
        confidence=buffered.confidence,
        kept_crc=buffered.kept_crc,
        kept_reads=buffered.kept_reads,
        reads=row.reads if row.reads is not None else buffered.reads,
    )


def ended_on_accuraterip(track: object) -> bool:
    """True when ``track``'s ``-Z`` reads ended on an AccurateRip match (``.31``).

    Read with ``getattr``: False for any track without the fact, which is every
    build before ``.31``. Never raises.
    """
    overrule = getattr(track, "secure_rerip_ar_overrule", None)
    return getattr(overrule, "ended_on_match", None) is True


def record_phrase(overrule: AccurateRipOverrule) -> str:
    """The per-track record's words for an overrule. Pure; never raises.

    ``re-read: matched AccurateRip at confidence 200 after 4 reads, overruling an
    agreement on 3D8FCF0C`` for an early end, and for a limit after an overrule
    ``an agreement on 3D8FCF0C was overruled by AccurateRip``. A fact the log did
    not state is left out, never filled in.
    """
    if not overrule.ended_on_match:
        return f"an agreement on {overrule.overruled_crc} was overruled by AccurateRip"
    confidence = f" at confidence {overrule.confidence}" if overrule.confidence else ""
    reads = overrule.reads
    after = f" after {reads} read{'' if reads == 1 else 's'}" if reads else ""
    kept = ""
    if overrule.kept_crc and overrule.matched_read:
        kept = f" (kept {overrule.kept_crc}, from read {overrule.matched_read})"
    return (
        f"re-read: matched AccurateRip{confidence}{after}, overruling an agreement "
        f"on {overrule.overruled_crc}{kept}"
    )
