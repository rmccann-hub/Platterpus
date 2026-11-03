"""An acceptance session's ``SOURCES.txt``, written from what the bundle archived.

**Why this module exists.** ``test_session`` names every path a session asks
for and writes, into the archive, what became of each (``SOURCES.txt``), and the
bundler writes its own account of every member (``MANIFEST.txt``). On the
2026-11-03 Full run the two disagreed: ``SOURCES.txt`` said app-log rotations
``.6`` to ``.10`` were "archived as" a member, and ``MANIFEST.txt`` said each was
excluded because the 64 MiB budget was spent. ``SOURCES.txt`` was rendered when
the files were *staged*, before the bundle decided anything, so it described a
plan as a result. It is now rendered after the bundle has judged every file
(``evidence_bundle.build_bundle(late_text=...)``) and reads each staged file's
fate from the bundle's own entries: one source for both lists.

**And why a rotation can be left out on purpose.** The same run spent 42 MB of
that budget on app-log rotations last written days earlier, which hold none of
the run's lines. A rotation whose last write predates the session's start is now
left on disk and named here (:func:`written_before_session`), so the budget goes
to this run's own logs. Unknown is never a reason to leave one out: a rotation
whose time cannot be read is collected.

Pure except :func:`written_before_session`, which reads one file's mtime. Never
raises. Qt-free.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from platterpus.evidence_bundle import BundleEntry

log = logging.getLogger(__name__)

#: The session stamp's format (``test_session.STAMP_FORMAT``; tied by a test).
_STAMP_FORMAT: Final[str] = "%Y%m%dT%H%M%SZ"

#: What a staged file's line says when the bundle refused it.
NOT_ARCHIVED: Final[str] = "NOT ARCHIVED"

#: What a rotation's line says when it predates the session.
OLDER_THAN_SESSION: Final[str] = "NOT COLLECTED — older than this session"


def session_start(stamp: str) -> datetime | None:
    """The session's start as a UTC moment, or None when the stamp is unreadable."""
    try:
        return datetime.strptime(stamp, _STAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def written_before_session(path: Path, stamp: str) -> datetime | None:
    """When ``path`` was last written, if that was BEFORE the session began.

    ``None`` means collect it: written during the session, or either time is
    unknown (an unreadable stamp, a stat that failed). Never raises.
    """
    start = session_start(stamp)
    if start is None:
        return None
    try:
        written = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except (OSError, OverflowError, ValueError) as exc:
        log.warning("could not read when %s was last written: %r", path, exc)
        return None
    return written if written < start else None


def older_than_session_line(source: Path, written: datetime, stamp: str) -> str:
    """The ``SOURCES.txt`` line for a rotation left out as older than the session."""
    return (
        f"  {source}\n      {OLDER_THAN_SESSION}: last written "
        f"{written.strftime(_STAMP_FORMAT)}, before the session began ({stamp}), "
        "so it holds none of this run's lines; left on disk, not archived"
    )


def render_sources_record(
    *,
    stamp: str,
    root: Path,
    bundle: Path,
    lines: Sequence[str],
    members: Mapping[str, int],
    counts: Mapping[str, int],
    entries: Sequence[BundleEntry],
) -> str:
    """The record, with each staged file's line read from the bundle's verdict.

    ``members`` maps an archive member name to the index of its line in
    ``lines``; ``counts`` holds ``present``, ``absent``, ``failed`` and
    ``older``. A member the bundle refused gets the bundle's own reason, the
    sentence ``MANIFEST.txt`` prints for it, so the two cannot disagree.
    """
    refused = {e.name: e.reason for e in entries if not e.included}
    shown = list(lines)
    not_archived = 0
    for member, index in members.items():
        reason = refused.get(member)
        if reason is None or not 0 <= index < len(shown):
            continue
        not_archived += 1
        source = shown[index].split("\n", 1)[0]
        shown[index] = (
            f"{source}\n      {NOT_ARCHIVED} — staged as {member}, then refused "
            f"by the bundle: {reason}"
        )
    present = counts.get("present", 0)
    absent = counts.get("absent", 0)
    failed = counts.get("failed", 0)
    older = counts.get("older", 0)
    total = present + absent + failed + older
    return "\n".join(
        [
            "PLATTERPUS ACCEPTANCE SESSION — SOURCES",
            "=======================================",
            "",
            f"session stamp      {stamp}",
            f"session folder     {root}",
            f"deliverable        {bundle}",
            "",
            "Every path this session asked for is listed below, INCLUDING the ones",
            "that were not there. An absence somebody can read is a finding; an",
            "absence nobody can see reads as a complete bundle. Each file's line",
            "says what the bundle did with it, as MANIFEST.txt does.",
            "",
            f"asked for {total}: {present - not_archived} collected, "
            f"{not_archived} not archived, {absent} absent, {failed} failed, "
            f"{older} older than this session",
            "",
        ]
        + (shown or ["  (nothing was named — this is itself a finding)"])
        + [
            "",
            "No audio can be in this archive: everything above passed the",
            "allowlist in evidence_bundle (see MANIFEST.txt, which names every",
            "file it refused and why).",
            "",
        ]
    )
