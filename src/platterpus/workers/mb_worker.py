"""MusicBrainzWorker — drives MusicBrainz lookups off the GUI thread.

MusicBrainz HTTP requests can take several seconds (especially on a
cold cache) and MUST NOT block input. The main thread constructs a
MusicBrainzWorker, moves it to a QThread, and drives its slots by
**emitting a signal connected to them** — a queued, cross-thread call
that runs on the worker's thread. (Calling a slot as a plain method
would run it on the *caller's* thread regardless of moveToThread, which
is exactly the freeze this worker exists to avoid.)

Every result signal echoes a **context** string back to the caller as its
first argument — the disc-id the query belongs to. Queries are async, so a
lookup started for disc A can land *after* the user swapped to disc B; the
GUI compares the echoed context against the current disc and drops a
mismatch (else disc A's release would tag disc B — wrong-album metadata).
This mirrors how DiscInfoWorker echoes the device it probed. For
`lookup_disc_id` the disc-id *is* the query, so it's echoed automatically;
`fetch_release`/`lookup_toc` take the context explicitly (the mbid/TOC alone
doesn't identify which disc scan asked for it).

Signals:
  releases_returned(str, list)  — (context, list[ReleaseSummary]) from disc-id / TOC
  release_returned(str, object) — (context, single ReleaseDetail) from MBID fetch
  error(str, str)               — (context, query-failure message)

Slots:
  lookup_disc_id(disc_id)          — context is the disc_id itself
  lookup_toc(toc, context)
  fetch_release(mbid, context)

One worker handles all three query types. Because a single worker on a
single thread processes slots serially, queries don't interleave —
which is what we want (each user action triggers exactly one query at
a time).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.adapters.musicbrainz_client import (
    MusicBrainzClient,
    MusicBrainzQueryError,
    TocSignature,
)

log = logging.getLogger(__name__)


class MusicBrainzWorker(QObject):
    """QObject worker for MusicBrainz queries via MusicBrainzClient."""

    # Each result carries a leading `context` (str) — the disc-id the query
    # belongs to — so the GUI can drop a late result from a disc the user
    # already ejected (wrong-album guard).
    releases_returned = Signal(str, list)  # (context, list[ReleaseSummary])
    release_returned = Signal(str, object)  # (context, ReleaseDetail) — object so
    # PySide needs no explicit type
    # registration for the dataclass
    error = Signal(str, str)  # (context, message)

    def __init__(
        self,
        client: MusicBrainzClient,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._client: MusicBrainzClient = client

    @Slot(str)
    def lookup_disc_id(self, disc_id: str) -> None:
        """Lookup release candidates by MB disc ID. Empty list when no match.

        The disc-id is echoed as the result context — it *is* what identifies
        which disc this lookup belongs to.
        """
        log.debug("MB disc-id lookup: %s", disc_id)
        try:
            results = self._client.releases_by_disc_id(disc_id)
        except MusicBrainzQueryError as exc:
            log.warning("MB disc-id lookup failed: %s", exc)
            self.error.emit(disc_id, str(exc))
            return
        self.releases_returned.emit(disc_id, results)

    @Slot(object, str)
    def lookup_toc(self, toc: TocSignature, context: str = "") -> None:
        """Lookup release candidates by TOC fingerprint.

        `context` (the disc-id the scan belongs to) is echoed back so a stale
        result can be dropped; the TOC alone doesn't identify the disc scan.
        """
        log.debug("MB TOC lookup: %s", toc.to_query())
        try:
            results = self._client.releases_by_toc(toc)
        except MusicBrainzQueryError as exc:
            log.warning("MB TOC lookup failed: %s", exc)
            self.error.emit(context, str(exc))
            return
        self.releases_returned.emit(context, results)

    @Slot(str, str)
    def fetch_release(self, mbid: str, context: str = "") -> None:
        """Fetch full release details for one MBID.

        `context` (the disc-id the fetch belongs to) is echoed back so a late
        fetch for an already-ejected disc can be dropped by the GUI.
        """
        log.debug("MB release fetch: %s", mbid)
        try:
            detail = self._client.release_by_mbid(mbid)
        except MusicBrainzQueryError as exc:
            log.warning("MB release fetch failed: %s", exc)
            self.error.emit(context, str(exc))
            return
        self.release_returned.emit(context, detail)
