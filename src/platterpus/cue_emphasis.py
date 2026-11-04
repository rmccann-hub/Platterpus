"""Does the cue's ``FLAGS PRE`` agree with what the ripper did to the audio?

**What ``FLAGS PRE`` means.** Some CDs were mastered with pre-emphasis: a treble
boost the player is meant to undo on playback. A cue sheet's ``FLAGS PRE`` line
tells a player or burner *"the audio in this track's file is still
pre-emphasised; undo it"*. So the line is right exactly when the file still holds
the disc's own, boosted samples, and wrong in both other directions: missing on a
boosted file (the listener hears the treble boost) or present on a file that was
already de-emphasised (the treble is cut twice).

**Why the rule is decidable from the record.** Whether the file still holds the
disc's samples is decided by two facts we already have, and both come from
somewhere other than the cue:

1. **What cyanrip was told** (the argv in the report). cyanrip de-emphasises a
   pre-emphasised track by default; ``-W`` turns that off, and ``-E`` forces
   de-emphasis on every track and wins over ``-W``. The predicate is one
   function in the fork, used by both the encoder and the cue writer,
   ``crip_deemphasis_active`` (cyanrip@93c70cbc:src/cyanrip_main.h:708-712:
   ``(settings.deemphasis && t->preemphasis) || settings.force_deemphasis``), with
   ``settings.deemphasis = 1`` by default (cyanrip@93c70cbc:src/cyanrip_main.c:2909)
   and ``FLAGS PRE`` written as its exact negation
   (cyanrip@93c70cbc:src/cue_writer.c:266-267). Every Platterpus rip sends ``-W``
   (``adapters/cyanrip_backend.py``, from 0.7.102), as EAC does by never
   de-emphasising (``docs/eac-parity.md``, the pre-emphasis row).
2. **Which tracks the disc flags as pre-emphasised** (cyanrip's ``Preemphasis:``
   row, read by ``parsers/cyanrip_log.py`` into the report's per-track
   ``pre_emphasis``).

So the cue must carry ``FLAGS PRE`` on a track exactly when the track is
pre-emphasised **and** de-emphasis was not applied. **Tri-state**: when either fact
is unknown the answer is *not determined*, never a pass and never a failure.

Pure: argv and report values in, findings out. Never raises.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Final

from platterpus.cue_validate import (
    LEVEL_NOTE,
    LEVEL_OK,
    LEVEL_WARN,
    CueFinding,
    CueSheet,
)

log = logging.getLogger(__name__)

#: The file holds the disc's own samples: ``-W`` sent, ``-E`` not.
KEPT: Final[str] = "kept"
#: cyanrip de-emphasised any pre-emphasised track: ``-E`` sent, or ``-W`` absent.
REMOVED: Final[str] = "removed"
#: We cannot say which (no argv recorded, or two passes that disagree).
NOT_DETERMINED: Final[str] = "not_determined"

#: The spellings of the two flags. Short ones are what our argv builder sends;
#: the long ones are cyanrip's names for the same options
#: (cyanrip@93c70cbc:src/cyanrip_main.c:3010-3013, ``force_deemphasis`` and
#: ``no_deemphasis``, each ``_`` registered as ``-``,
#: cyanrip@93c70cbc:src/genopt.h:475-482), read too so a hand-built argv is not
#: misjudged.
_KEEP_FLAGS: Final[frozenset[str]] = frozenset({"-W", "--no-deemphasis"})
_FORCE_FLAGS: Final[frozenset[str]] = frozenset({"-E", "--force-deemphasis"})

#: The cue flag this module judges.
PRE_FLAG: Final[str] = "PRE"


def emphasis_handling(argv: Sequence[object]) -> str:
    """What one cyanrip argv did to a pre-emphasised track's samples.

    :data:`KEPT` for ``-W`` without ``-E``; :data:`REMOVED` for ``-E`` (it wins
    over ``-W`` in cyanrip's predicate) or for neither (cyanrip's default is to
    de-emphasise); :data:`NOT_DETERMINED` for an empty argv, since a rip with no
    recorded command line says nothing about either flag.

    Membership by whole token, as the other argv readers here do: a tag value
    reaches cyanrip as ``N=key=value``, so a token that is exactly ``-W`` is the
    flag.
    """
    tokens = {str(part) for part in argv}
    if not tokens:
        return NOT_DETERMINED
    if tokens & _FORCE_FLAGS:
        return REMOVED
    if tokens & _KEEP_FLAGS:
        return KEPT
    return REMOVED


def handling_of_passes(passes: Sequence[Sequence[object]]) -> str:
    """One answer for a rip of one or more passes, or not determined.

    Each pass writes the tracks it reads, so two passes told different things
    leave the album holding files of both kinds; no one rule then fits the cue,
    and claiming one would accuse a correct line. Empty passes are ignored.
    """
    answers = {emphasis_handling(argv) for argv in passes if argv}
    if len(answers) == 1:
        return next(iter(answers))
    if len(answers) > 1:
        log.warning("rip passes disagree on de-emphasis: %s", sorted(answers))
    return NOT_DETERMINED


def check_flags_pre(
    sheet: CueSheet, pre_emphasis: Mapping[int, bool | None], handling: str
) -> list[CueFinding]:
    """Judge every track of ``sheet`` for ``FLAGS PRE``. Always one finding at least.

    ``pre_emphasis`` maps track number to cyanrip's own reading (``None`` for a
    track whose ``Preemphasis:`` row we did not read). A track in the cue but not
    in the map, or with ``None``, is counted as not determined and named.
    """
    if handling not in (KEPT, REMOVED):
        return [
            CueFinding(
                LEVEL_NOTE,
                "flags_pre_undetermined",
                "cue FLAGS PRE — not determined: the report does not say whether "
                "de-emphasis was applied (no ripper command line recorded, or "
                "two passes told different things)",
            )
        ]
    wrong_missing: list[int] = []
    wrong_present: list[int] = []
    unknown: list[int] = []
    agreed = 0
    flagged = 0
    for track in sheet.tracks:
        number = track.number
        if number is None:
            continue
        emphasised = pre_emphasis.get(number)
        if emphasised is None:
            unknown.append(number)
            continue
        want = emphasised and handling == KEPT
        have = PRE_FLAG in track.flags
        if want and not have:
            wrong_missing.append(number)
        elif have and not want:
            wrong_present.append(number)
        else:
            agreed += 1
            flagged += int(have)
    return _findings(handling, agreed, flagged, wrong_missing, wrong_present, unknown)


def _tracks(numbers: Sequence[int]) -> str:
    """``track 3`` or ``tracks 3, 5``."""
    label = "track" if len(numbers) == 1 else "tracks"
    return f"{label} {', '.join(str(n) for n in sorted(numbers))}"


def _findings(
    handling: str,
    agreed: int,
    flagged: int,
    wrong_missing: Sequence[int],
    wrong_present: Sequence[int],
    unknown: Sequence[int],
) -> list[CueFinding]:
    """The sentences, one per kind of answer that occurred."""
    how = (
        "the disc's own samples were kept (-W)"
        if handling == KEPT
        else "de-emphasis was applied (-E, or no -W)"
    )
    findings: list[CueFinding] = []
    if wrong_missing:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "flags_pre_missing",
                f"cue FLAGS PRE missing on {_tracks(wrong_missing)}: cyanrip "
                f"reported pre-emphasis and {how}, so the file is still "
                "pre-emphasised and a player reading this cue will not undo it",
            )
        )
    if wrong_present:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "flags_pre_spurious",
                f"cue FLAGS PRE present on {_tracks(wrong_present)}, but {how} or "
                "cyanrip reported no pre-emphasis, so the file is not "
                "pre-emphasised and a player would cut its treble",
            )
        )
    if unknown:
        findings.append(
            CueFinding(
                LEVEL_NOTE,
                "flags_pre_track_undetermined",
                f"cue FLAGS PRE — not determined for {_tracks(unknown)}: the "
                "report has no pre-emphasis reading for it",
            )
        )
    if agreed:
        findings.append(
            CueFinding(
                LEVEL_OK,
                "flags_pre_agrees",
                f"cue FLAGS PRE agrees on {agreed} track(s) ({flagged} flagged): {how}",
            )
        )
    if not findings:
        findings.append(
            CueFinding(
                LEVEL_NOTE,
                "flags_pre_no_tracks",
                "cue FLAGS PRE — not determined: the cue names no numbered track",
            )
        )
    return findings
