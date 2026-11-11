# SPDX-License-Identifier: GPL-3.0-only
"""What a track's reads were, for its record: the path, and whether they disagreed.

Split from :mod:`platterpus.track_record` (which words the whole record) because
these two answers stand alone and have their own callers: the EAC-layout log's
status line asks :func:`reads_disagree` (never ``Copy OK`` over reads that
disagree, G3), and the record's line opens with :func:`read_path`. Both read only
the parsed track's own fields, plus whether the chase kept its read.

Pure; no Qt, no I/O; reads with ``getattr``; never raises.
"""

from __future__ import annotations

from platterpus.first_pass_reread import did_not_converge
from platterpus.track_record_sources import int_or_none_strict


def reads_disagree(track: object, *, chased: bool = False) -> bool | None:
    """Did this track's reads give more than one value? Tri-state, from the record.

    ``True`` on any recorded disagreement: a Test CRC unlike the Copy CRC; a
    ``-Z`` re-read that did not converge, or one kept at the limit for
    AccurateRip; ``.30``'s ``Other read:`` lines (reads not kept, each unlike the
    kept one); a first pass that did not converge before a securing read replaced
    it (TASKS R114); or a verified-read chase, which runs only when the drive
    returned more than one value (``verified_read_chase.plan_chase``). ``False``
    when two or more reads are recorded agreeing and nothing says otherwise.
    ``None`` for one read: nothing to compare.
    """
    test_crc = str(getattr(track, "test_crc", "") or "").upper()
    copy_crc = str(getattr(track, "copy_crc", "") or "").upper()
    if test_crc and copy_crc and test_crc != copy_crc:
        return True
    converged = getattr(track, "secure_rerip_converged", None)
    # Any `Other read:` line, even one kept as `unrecognised`, is a read whose
    # value was not the kept one's: the fork prints none when every read agreed.
    others: object = getattr(track, "other_reads", ())
    if (
        converged is False
        or getattr(track, "secure_rerip_kept_read", None) is not None
        or (isinstance(others, (tuple, list)) and len(others) > 0)
        or did_not_converge(track)
        or chased
    ):
        return True
    if converged is True or (test_crc and test_crc == copy_crc):
        return False
    return None


def _plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def _converged_agreement(track: object, reads: int | None) -> str:
    """``3 agreeing of 3``, ``at least 2 agreeing of 4``, for reads that converged.

    Exact when ``.30``'s ``Other read:`` lines account for every read not kept
    (the kept value's count is the rest), or when only two reads were made;
    otherwise the floor convergence proves, two.
    """
    if not isinstance(reads, int) or reads < 2:
        return "converged (the read count is not stated)"
    others = tuple(getattr(track, "other_reads", ()) or ())
    counts = [int_or_none_strict(getattr(o, "count", None)) for o in others]
    if others and not getattr(track, "other_reads_not_kept", 0) and None not in counts:
        agreeing = reads - sum(c for c in counts if c is not None)
        if 2 <= agreeing <= reads:
            return f"{agreeing} agreeing of {reads}"
    if reads == 2:
        return "2 agreeing of 2"
    return f"at least 2 agreeing of {reads}"


def _limit_agreement(track: object, reads: int | None) -> str:
    """``at most 2 agreeing of 3`` for reads a limit stopped, as the log proves."""
    of = f" of {reads}" if isinstance(reads, int) else ""
    agreement = getattr(track, "secure_rerip_agreement", None)
    agreed = int_or_none_strict(getattr(agreement, "most_reads_agreed", None))
    exact = getattr(agreement, "exact", False) is True
    if agreed is None:
        return f"did not converge{f' after {reads} reads' if of else ''}"
    if agreed < 2:
        return f"no two agreeing{of}" if exact else f"did not converge{of}"
    bound = "at most" if exact else "at least"
    return f"{bound} {agreed} agreeing{of}"


def read_path(track: object) -> str:
    """How the kept read was made, without the database: ``first read`` or a re-read."""
    test_crc = str(getattr(track, "test_crc", "") or "").upper()
    copy_crc = str(getattr(track, "copy_crc", "") or "").upper()
    if test_crc:
        if test_crc == copy_crc:
            return "re-read, 2 agreeing of 2 (the Test and Copy reads)"
        return "re-read, the Test and Copy reads disagree"
    reads = int_or_none_strict(getattr(track, "rip_count", None))
    converged = getattr(track, "secure_rerip_converged", None)
    if converged is True:
        return f"re-read, {_converged_agreement(track, reads)}"
    if converged is False:
        return f"re-read, {_limit_agreement(track, reads)}"
    if reads is not None and reads >= 2:
        return f"re-read, {_plural(reads, 'read')} (agreement not stated)"
    return "first read"
