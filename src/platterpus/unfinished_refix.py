# SPDX-License-Identifier: GPL-3.0-only
"""What a securing pass that was stopped may still give the album, per track.

**The defect this exists for** (run B of the four Full runs on 0.7.112, the
damaged 18-track disc, 2026-10-21). The securing pass re-read tracks 11 to 18
in one ripper run (``-Z 2 -l 11,…,18``) and was stopped during track 18 by the
script's six-hour wait. Its own log shows track 11's re-read matching
AccurateRip (v1 confidence 12, v2 confidence 29) where the album pass's read
matched nothing. The worker swapped nothing from a pass that did not finish, so
the album kept the unverified first read and threw away a verified one.

**What a stopped pass can and cannot prove.** The pass stopping says nothing
about tracks it had already finished: each track is re-read, encoded and
written on its own, and a later track's interruption cannot reach back into an
earlier track's file. So the question is per track, and it has three parts,
each a fact we can read rather than predict:

1. **Its block is complete.** The track's verdict line was attributed (the
   parser does that only when the track's own line followed it whole) and its
   block reached ``File(s):``, the last row a track block prints. A block cut
   short has no file name and is refused.
2. **AccurateRip verified it, by the one rule.** :func:`verdict.reread_supersedes`
   is asked, as for a pass that finished, and only its AccurateRip answer swaps
   here. A read that merely converged is our drive agreeing with itself; from a
   pass that was stopped we take only the independent witness.
3. **Its file was written whole.** ``File(s):`` is printed before the encoder is
   joined (the fork's round 22 lap 1, "built from the request"), so the row is
   not proof that the file was closed. The FLAC's own ``STREAMINFO`` is: an
   encoder writes it with 0 samples and an all-zero MD5 and rewrites both when
   it closes the file (:func:`checksums.flac_total_samples`). The count must
   equal the read's, ``(End LSN - Start LSN + 1) * 588``, and the MD5 must be
   set.

A track that fails any part keeps its first read, and the report says which
part (``not_replaced_because``). Pure, and never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.checksums import flac_total_samples, flac_unencoded_md5
from platterpus.verdict import REREAD_KEPT_FOR_ACCURATERIP, reread_supersedes

#: Samples per channel in one CD sector (2352 bytes of 16-bit stereo).
SAMPLES_PER_SECTOR: Final[int] = 588

# ``retried_tracks[].not_replaced_because`` values for a track a stopped pass
# had finished re-reading. Report schema 40.
#: The re-read's block never reached its ``File(s):`` row, so it is not whole.
NOT_REPLACED_BLOCK_INCOMPLETE: Final[str] = "block_incomplete"
#: The one rule did not keep the re-read on AccurateRip's word.
NOT_REPLACED_NOT_VERIFIED: Final[str] = "accuraterip_did_not_verify"
#: The re-read's FLAC is missing, unclosed, or holds a different sample count.
NOT_REPLACED_FILE_NOT_WHOLE: Final[str] = "file_not_whole"
#: Everything held, and the copy into the album failed; the first read stayed.
NOT_REPLACED_COPY_FAILED: Final[str] = "copy_failed"


@dataclass(frozen=True)
class SalvageDecision:
    """Whether to swap one track's re-read in from a stopped pass, and why."""

    #: True when the re-read should replace the album's file.
    swap: bool
    #: ``verdict.REREAD_KEPT_FOR_ACCURATERIP`` when ``swap``; else None.
    replaced_because: str | None
    #: One of the ``NOT_REPLACED_*`` values when not ``swap``; else None.
    not_replaced_because: str | None
    #: One line a person can read, for the app log.
    detail: str


def expected_samples(track: object) -> int | None:
    """The samples per channel the ripper read for ``track``, from its LSNs.

    cyanrip prints ``Start LSN`` and ``End LSN`` for the sectors it read and
    ``Samples:`` equal to ``(end - start + 1) * 588`` (run B's track 11:
    ``135147`` to ``149259``, 14113 sectors, 8298444 samples). None when either
    is missing or the range is empty. Never raises.
    """
    start = getattr(track, "start_sector", None)
    end = getattr(track, "end_sector", None)
    if not isinstance(start, int) or not isinstance(end, int) or end < start:
        return None
    return (end - start + 1) * SAMPLES_PER_SECTOR


def file_written_whole(path: Path, track: object) -> tuple[bool, str]:
    """Is ``path`` a FLAC its encoder closed, holding all of ``track``'s read?

    Returns ``(whole, why)``. Not determined counts as not whole: the file
    protected here is the album's archival master, and swapping an unproven file
    over it is the failure a refusal avoids, at the cost of keeping a read
    AccurateRip did not verify. Never raises.
    """
    want = expected_samples(track)
    if want is None:
        return False, "the log gives no sector range to check the file against"
    got = flac_total_samples(path)
    if got is None:
        return False, f"{path.name} has no sample count (missing, or never closed)"
    if got != want:
        return False, f"{path.name} holds {got} samples where the read was {want}"
    if flac_unencoded_md5(path) is None:
        return False, f"{path.name} has no audio MD5 (its encoder never closed it)"
    return True, f"{path.name} holds all {want} samples and its audio MD5"


def salvage_decision(
    first_pass: object | None, reread: object, candidate: Path | None
) -> SalvageDecision:
    """Decide one track a stopped securing pass had finished. Never raises.

    ``candidate`` is the re-read's FLAC in the pass's temporary folder (None when
    the block names no file). The three parts are in the module docstring.
    """
    if candidate is None or not getattr(reread, "filename", ""):
        return SalvageDecision(
            False,
            None,
            NOT_REPLACED_BLOCK_INCOMPLETE,
            "its block never reached its File(s): row",
        )
    if reread_supersedes(first_pass, reread) != REREAD_KEPT_FOR_ACCURATERIP:
        return SalvageDecision(
            False,
            None,
            NOT_REPLACED_NOT_VERIFIED,
            "AccurateRip did not verify the re-read over the first read",
        )
    whole, why = file_written_whole(candidate, reread)
    if not whole:
        return SalvageDecision(False, None, NOT_REPLACED_FILE_NOT_WHOLE, why)
    return SalvageDecision(
        True,
        REREAD_KEPT_FOR_ACCURATERIP,
        None,
        f"AccurateRip verified the re-read and {why}",
    )


def _listed(numbers: list[int]) -> str:
    return ", ".join(str(n) for n in numbers)


def stopped_pass_sentence(recorded: list[int], kept: list[int], settled: bool) -> str:
    """The app-log and run-log line for a stopped pass's verdicts. Never raises.

    Names which re-reads replaced their first reads and which first reads stayed,
    so a reader of the log alone can tell the two apart (run B's log said every
    first read stayed, which after this change would be false for track 11).
    """
    stayed = [n for n in recorded if n not in kept]
    parts = [
        f"[auto-fix] the securing pass stopped before it finished; track(s) "
        f"{_listed(recorded)} had been re-read and their verdicts are kept."
    ]
    if kept:
        parts.append(
            f"AccurateRip verified the re-read of track(s) {_listed(kept)}, each "
            "written whole, so those re-reads replace the first reads."
        )
    if stayed:
        parts.append(
            f"The first reads of track(s) {_listed(stayed)} stay in the album."
        )
    if not settled:
        parts.append(
            "Its log never reached its footer, so they were read from the lines "
            "it had written; each verdict line was followed whole by its track's "
            "line."
        )
    return " ".join(parts)
