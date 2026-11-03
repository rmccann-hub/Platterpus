"""A rip report's ``diagnostics`` block, scoped to the rip it describes (TASKS R117).

**Why this exists (finding 9 of the 2026-11-03 Full run).** The diagnostics
collector is process-wide, on purpose: a setup failure an hour earlier can explain
a later rip (``diagnostics.DiagnosticLog.to_report_block`` says so in its
``scope``). But every report of that run then carried every diagnostic of the
session: the secure re-read's report opened with track 5's verdict from the rip
before it, and a twelve-section run repeats each early warning into the eleven
reports after it, so a reader of any one report cannot tell which items are its
own.

**What this does.** Given the block and the instant the rip started, it keeps in
``items`` (and in the counts, ``codes`` and ``worst_severity`` above them) only the
diagnostics recorded from that instant on, and says the earlier ones ONCE, as a
count with their codes in ``earlier_in_session``, so a reader still learns that
something happened before the rip and where to find it (the app log, and the
reports written then). ``scope`` states which of the two the block is.

**What it cannot do, said rather than implied.** The lower bound is the rip's
start; there is no upper bound, because a post-rip check (CTDB, the FLAC test)
records after the rip ends and belongs to it. So something another rip records
before this report's last write is still in it, as before.

Pure; never raises. A start instant that does not parse leaves the block as the
collector built it, session-wide, with its own ``scope``.
"""

from __future__ import annotations

from datetime import datetime

#: Severity order, worst first, as the collector ranks them.
_RANK: dict[str, int] = {"error": 0, "warning": 1, "info": 2}


def _instant(text: object) -> datetime | None:
    """An aware ``datetime`` from an ISO-8601 string with an offset, or None."""
    if not isinstance(text, str) or not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _field(item: object, key: str) -> object:
    """``item[key]`` for a dict item, else None, so no shape can raise."""
    return item.get(key) if isinstance(item, dict) else None


def scoped_to_rip(block: dict[str, object], started_at: object) -> dict[str, object]:
    """``block`` with ``items`` limited to the rip that began at ``started_at``.

    An item whose ``at`` does not parse is kept: dropping it would lose a
    diagnostic to a timestamp quibble, and keeping it can only over-report.
    """
    start = _instant(started_at)
    items = block.get("items")
    if start is None or not isinstance(items, list):
        return block
    mine: list[object] = []
    earlier: list[object] = []
    for item in items:
        at = _instant(_field(item, "at"))
        (earlier if at is not None and at < start else mine).append(item)

    def _codes(chosen: list[object]) -> list[str]:
        seen: dict[str, None] = {}
        for item in chosen:
            seen.setdefault(str(_field(item, "code") or ""), None)
        return list(seen)

    def _worst(chosen: list[object]) -> str | None:
        severities = [str(_field(item, "severity") or "") for item in chosen]
        return min(severities, key=lambda s: _RANK.get(s, 99)) if severities else None

    def _count(chosen: list[object], severity: str) -> int:
        return sum(1 for item in chosen if _field(item, "severity") == severity)

    scoped = dict(block)
    scoped.update(
        error_count=_count(mine, "error"),
        warning_count=_count(mine, "warning"),
        info_count=_count(mine, "info"),
        worst_severity=_worst(mine),
        codes=_codes(mine),
        scope=(
            f"this rip: diagnostics recorded from its start at {started_at}; "
            f"{len(earlier)} earlier diagnostic(s) of this process session are "
            "counted in earlier_in_session and not repeated (the app log and the "
            "reports written then have them)"
        ),
        earlier_in_session={
            "count": len(earlier),
            "codes": _codes(earlier),
            "worst_severity": _worst(earlier),
        },
        items=mine,
    )
    return scoped
