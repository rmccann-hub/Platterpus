"""A track's first-pass re-read verdict, kept when a securing pass replaces it.

**Why this exists (TASKS R114, finding 2 of the 2026-11-03 Full run).** Section N
ripped the reference disc with ``-Z 2 -r 5``. Track 3's first pass read four
different checksums and stopped at the repeat limit: ``Secure re-read:  did NOT
converge after 5 reads (repeat limit hit)``
(``docs/handshake/artifactsround37/round37full1103asecurereread.log:293``). The
securing pass re-ripped it alone and converged after 3 reads. The merge that makes
the album's record describe the file on disk
(``ui/main_window_rip._merge_shipped_track``) then replaced the track's read count
and re-read verdict with the securing pass's, which is right for the file, and kept
nothing of the first pass. So the report's ``heavy_reread`` named track 5 only and
the EAC-layout log said ``confirmed across 3 secure re-reads`` over a track whose
drive had disagreed with itself four ways a few minutes earlier. The addendum and
the diagnostics kept the fact; the two records a reader opens first did not.

**Two facts, two slots.** The securing pass's verdict stays where it was, because it
describes the shipped read. The first pass's verdict is a second fact about the
same track, so it gets its own slot, :class:`FirstPassReread` on
``TrackResult.first_pass_reread``, written by the merge from the track as the
album pass left it and never overwritten by a later merge.

Pure and Qt-free; every function reads with ``getattr`` and never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from platterpus.reread_limit import STOPPED_BY_REPEAT_LIMIT, STOPPED_BY_TIME_LIMIT

if TYPE_CHECKING:
    from platterpus.parsers.rip_log import LimitKeptRead, RereadAgreement
    from platterpus.reread_limit import RereadLimitStop


@dataclass(frozen=True)
class FirstPassReread:
    """The album pass's own ``-Z`` facts for a track a later read replaced.

    The same five fields ``TrackResult`` carries for the shipped read
    (``rip_count`` and the four ``secure_rerip_*``), as the album pass's log
    printed them. None in a field is "the log did not say", as there.
    """

    rip_count: int | None = None
    converged: bool | None = None
    agreement: RereadAgreement | None = None
    kept_read: LimitKeptRead | None = None
    limit_stop: RereadLimitStop | None = None


def snapshot(track: object) -> FirstPassReread | None:
    """What to keep of ``track``'s own re-read facts before a merge replaces them.

    A snapshot the track already carries wins: a second merge must not record the
    securing pass as the first. None when the track was never re-read and states
    no read count, since there is nothing to lose.
    """
    existing = getattr(track, "first_pass_reread", None)
    if isinstance(existing, FirstPassReread):
        return existing
    rip_count = getattr(track, "rip_count", None)
    converged = getattr(track, "secure_rerip_converged", None)
    if not isinstance(rip_count, int):
        rip_count = None
    if not isinstance(converged, bool):
        converged = None
    if rip_count is None and converged is None:
        return None
    return FirstPassReread(
        rip_count=rip_count,
        converged=converged,
        agreement=getattr(track, "secure_rerip_agreement", None),
        kept_read=getattr(track, "secure_rerip_kept_read", None),
        limit_stop=getattr(track, "secure_rerip_limit_stop", None),
    )


def did_not_converge(track: object) -> bool:
    """True when the track's first pass hit a limit before its reads agreed."""
    first = getattr(track, "first_pass_reread", None)
    return isinstance(first, FirstPassReread) and first.converged is False


def clause(track: object) -> str:
    """``the first pass did not converge after 5 reads (repeat limit hit; …)``, or "".

    "" unless :func:`did_not_converge`. Names the limit the log named, so a pass
    our own time limit stopped is never worded as reads that disagreed, and the
    agreement count only where two or more reads agreed (``at most`` when the log
    proves it, ``at least`` when it proves a floor, as the EAC-layout log's
    repeat-limit caveat words it).
    """
    if not did_not_converge(track):
        return ""
    first = getattr(track, "first_pass_reread", None)
    reads = getattr(first, "rip_count", None)
    after = f" after {reads} reads" if isinstance(reads, int) else ""
    details: list[str] = []
    stop = getattr(first, "limit_stop", None)
    kind = getattr(stop, "kind", None)
    if kind == STOPPED_BY_TIME_LIMIT:
        seconds = getattr(stop, "time_limit_seconds", None)
        limit = f" of {seconds} s" if isinstance(seconds, int) else ""
        details.append(f"stopped at our time limit{limit}")
    elif kind == STOPPED_BY_REPEAT_LIMIT:
        details.append("repeat limit hit")
    agreement = getattr(first, "agreement", None)
    agreed = getattr(agreement, "most_reads_agreed", None)
    if isinstance(agreed, int) and agreed >= 2:
        bound = "at most" if getattr(agreement, "exact", False) is True else "at least"
        of_reads = f" of {reads}" if isinstance(reads, int) and reads >= agreed else ""
        details.append(f"{bound} {agreed}{of_reads} reads agreed")
    detail = f" ({'; '.join(details)})" if details else ""
    return f"the first pass did not converge{after}{detail}"


def sentences(rip_log: object) -> list[str]:
    """One sentence per track whose first pass did not converge, for the report.

    Each says what replaced that pass, from the track's own (shipped) fields:
    ``track 3: the first pass did not converge after 5 reads (repeat limit hit;
    at most 2 of 5 reads agreed); the read that replaced it converged after 3
    reads``.
    """
    out: list[str] = []
    for track in getattr(rip_log, "tracks", ()) or ():
        said = clause(track)
        number = getattr(track, "number", None)
        if not said or not isinstance(number, int):
            continue
        converged = getattr(track, "secure_rerip_converged", None)
        reads = getattr(track, "rip_count", None)
        after = f" after {reads} reads" if isinstance(reads, int) else ""
        if converged is True:
            now = f"the read that replaced it converged{after}"
        elif converged is False:
            now = f"the read that replaced it did not converge either{after}"
        else:
            now = "the read that replaced it has no re-read verdict"
        out.append(f"track {number}: {said}; {now}")
    return out
