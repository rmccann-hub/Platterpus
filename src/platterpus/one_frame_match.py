"""What cyanrip's ``Accurip 450`` line establishes, in the words every surface uses.

**What the line is.** cyanrip prints

    Accurip 450: 57722DDE (matches Accurip DB, confidence 200, track is partially accurately ripped)

only when BOTH whole-track checksums (v1 and v2) matched no AccurateRip
submission (``cyanrip@df91ae7:src/cyanrip_log.c:594``). The checksum on that line
is ``acu_sum_1_450``, which adds up the 588 stereo samples of **frame 450 and no
other** (``cyanrip@df91ae7:src/checksums.h:74-78``): one frame, 1/75 of a second,
six seconds into the track. It "matches" when that one frame equals the stored
frame-450 checksum of a submission whose confidence is above three quarters of
the track's best (``src/cyanrip_log.c:598,616``). AccurateRip stores that frame so
that offset-finding tools can calibrate a drive; it was never meant to verify a
track.

**What this project called it, and why that was wrong on the mechanism.** For two
months every surface here said *"matched an offset-variant pressing"* and that
such a track was *"usually just a different pressing and perfectly fine"*. Both are
false:

* a pressing shifted by an offset moves frame 450 too, so it would not match here;
* a pressing someone submitted has its own whole-track entry, and
  ``crip_find_ar`` walks every entry (``cyanrip@df91ae7:src/accurip.c:304-317``),
  so it would have matched exactly, on v1 or v2.

So what the line establishes is: **six seconds into the track, one frame agrees
with a well-confirmed submission, and the track as a whole matches none.** Nothing
in the check says why. The measured cases say it is not one cause. Section J's
track 1 on 2026-09-24 read ``0E91CD1A`` while five other reads gave ``B0D122E7``,
an exact match, so its bytes were wrong elsewhere; the same wrong read happened on
2026-09-11. A read interrupted after frame 450 passes the check too (the fork's
round 26 lap 4). And the Police disc's track 5 shows why agreeing ``450``
checksums prove nothing about the rest: across six filed rips its frame 450 read
``4CCBCF89`` every time, while its whole-track checksum was ``E0036697`` four times
and ``6902BCF0`` twice. (Our round 24 lap 4 cited the matching ``4CCBCF89`` as
proof that track 5 is a pressing difference rather than a bad read. It was a
frame-450 checksum, so it proved neither; corrected in round 27.)

**So these words say what matched and name no cause.** They are the one wording;
``tests/test_one_frame_match.py`` sweeps the user-facing surfaces for the old
claim. The internal names (``accuraterip_offset``, the ``"offset-variant"`` state
value in reports) are unchanged: they are keys other code and old reports carry,
and renaming a key is a schema change this wording does not need.

**NOT changed here: the EAC-compatible log.** Its lines are what the cyanrip fork
diffs against, and in round 7 (lap 11, H4) both sides agreed that neither rewords
that log unilaterally. The new wording for it is proposed in handshake round 27.
"""

from __future__ import annotations

from typing import Final

#: The table cell for a track in this state, beside the matched entry's
#: confidence: ``one frame only (200)``. Narrow column, so the tooltip carries the
#: rest.
CELL: Final[str] = "one frame only"

#: The results-table tooltip and the explanation the help and the banner echo.
TOOLTIP: Final[str] = (
    "One frame matched: this track's whole-track AccurateRip checksums matched no "
    "submission, but one frame of it (frame 450, 1/75 of a second, six seconds "
    "in) matched one. cyanrip calls this “partially accurately ripped”. It "
    "verifies that one frame and nothing else: the rest of the track may hold a "
    "read error, or audio that differs from every submission, and this check "
    "cannot tell which. Platterpus re-reads such tracks until two reads agree "
    "(on by default in Settings). If a re-rip gives a different checksum here, "
    "the track has a read problem."
)

#: The same fact as a clause, for sentences that already name the track(s).
CLAUSE: Final[str] = (
    "only one frame matched AccurateRip, so the rest of the track is unverified"
)


def count_sentence(matched: int, population: int) -> str:
    """``1 of 14 tracks matched AccurateRip on one frame only (the rest unverified)``.

    The noun agrees with the POPULATION, not the count: "1 of 14 tracks". Pure and
    never raises; negative or odd numbers are rendered as given, since the caller
    counted them and this only words them.
    """
    noun = "track" if population == 1 else "tracks"
    return (
        f"{matched} of {population} {noun} matched AccurateRip on one frame only "
        "(the rest unverified)"
    )
