# SPDX-License-Identifier: GPL-3.0-only
"""Adapter for the AccurateRip database: one disc's ``dBAR`` file, fetched and read.

**Why Platterpus asks AccurateRip itself now** (TASKS R138, round 39's gate G2,
2026-11-11). Until this module, AccurateRip was asked only by cyanrip, during the
rip, and its log prints the database's value only for a read that matched. A CTDB
repair rewrites a track whose read did not, so AccurateRip v1 and v2 of the
repaired audio could only be called "not determined". The repair computes those
checksums from the repaired file (``accuraterip_crc.py``); this adapter fetches
the database's answer for the disc, so the two can be compared.

An external service, so it lives behind this adapter (``CLAUDE.md`` Critical rule
1): the ABC :class:`AccurateRipDbClient` is the seam, :class:`AccurateRipHttpImpl`
the one implementation, and the fetcher is injected so no test reaches the
network (``tests/conftest.py`` also replaces the real one for every test).

**The URL** (checked by hand against the live server on 2026-11-11). From the
disc's AccurateRip ID ``id1-id2-cddb`` (cyanrip's ``AccurateRip ID:`` line) and
its audio track count ``N``::

    http://www.accuraterip.com/accuraterip/a/b/c/dBAR-NNN-id1-id2-cddb.bin

where ``a``, ``b``, ``c`` are id1's LOWEST, second-lowest and third-lowest hex
digits (id1 ``001d420f`` gives ``f/0/2``) and every id is 8 lower-case hex
digits. A wrong digit gives a 404 HTML page, so a reply is accepted only when it
reads as dBAR responses naming the disc that was asked about. Plain HTTP, as the
drive-offset snapshot uses (``accuraterip_offsets_data.py``): trust comes from
comparing checksums, not from the transport.

**Never raises; every outcome is one of three** (:class:`LookupState`): FOUND
(with every response), NOT_IN_DATABASE (a 404: AccurateRip has no entry for this
disc), or FAILED with the reason (network, a page that is not dBAR, a reply about
another disc, a bad AccurateRip ID). Called only off the GUI thread (the CTDB
repair worker); a lookup is one GET bounded by :data:`HTTP_TIMEOUT_S` per try.
"""

from __future__ import annotations

import enum
import http.client
import logging
import re
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from platterpus import __version__, diagnostics
from platterpus.parsers.accuraterip_dbar import (
    DbarResponse,
    looks_like_markup,
    parse_dbar,
)

log = logging.getLogger(__name__)

ACCURATERIP_SCHEME: Final[str] = "http"
ACCURATERIP_HOST: Final[str] = "www.accuraterip.com"
#: Every dBAR file lives below this path.
DBAR_PATH: Final[str] = "/accuraterip/"
#: The community convention a database asks of a client: say who is asking.
USER_AGENT: Final[str] = (
    f"platterpus/{__version__} (https://github.com/rmccann-hub/Platterpus)"
)
#: Per-attempt socket timeout. The real file is under 2 KB.
HTTP_TIMEOUT_S: Final[float] = 15.0
#: Cap on a reply. A response is at most 13 + 99 x 9 = 904 bytes, and the
#: reference disc's file holds 13; a megabyte is over a thousand responses.
MAX_REPLY_BYTES: Final[int] = 1024 * 1024
#: A CD holds 1 to 99 tracks (Red Book); the file name has room for three digits.
MIN_TRACKS: Final[int] = 1
MAX_TRACKS: Final[int] = 99
#: Backoffs before each attempt: transient failures (timeouts, 5xx) are retried.
RETRY_BACKOFFS_S: Final[tuple[float, ...]] = (0.0, 1.5, 3.0)

# "001d420f-013bb370-e20dfe0e": cyanrip prints `%08x-%08x-%08x`. Bounded.
_DISC_ID: Final[re.Pattern[str]] = re.compile(
    r"(?P<id1>[0-9a-fA-F]{8})-(?P<id2>[0-9a-fA-F]{8})-(?P<cddb>[0-9a-fA-F]{8})"
)

#: Given a URL, the reply's bytes; raises ``urllib.error.HTTPError`` / ``OSError``.
Fetcher = Callable[[str], bytes]


@dataclass(frozen=True)
class AccurateRipDiscId:
    """A disc's AccurateRip ID: the three words its dBAR file is named by."""

    id1: int
    id2: int
    cddb: int

    @property
    def text(self) -> str:
        """``001d420f-013bb370-e20dfe0e``, as cyanrip prints it."""
        return f"{self.id1:08x}-{self.id2:08x}-{self.cddb:08x}"


def parse_disc_id(text: object) -> AccurateRipDiscId | None:
    """The ID from cyanrip's ``AccurateRip ID:`` value, or None when it is not one.

    The input check at the boundary (``CLAUDE.md``: validate every input): exactly
    three words of eight hex digits, nothing around them but blanks.
    """
    if not isinstance(text, str):
        return None
    match = _DISC_ID.fullmatch(text.strip())
    if match is None:
        return None
    try:  # eight hex digits always convert; the guard is the never-raises sweep's
        return AccurateRipDiscId(
            int(match.group("id1"), 16),
            int(match.group("id2"), 16),
            int(match.group("cddb"), 16),
        )
    except ValueError:
        return None


def dbar_url(disc: AccurateRipDiscId, track_count: int) -> str:
    """The dBAR file's URL for ``disc`` with ``track_count`` audio tracks.

    Raises ``ValueError`` for a track count outside 1..99: a value the URL cannot
    carry is refused before it becomes a request, never sent and read as "not in
    the database" (the argv-chokepoint rule, applied to a URL).
    """
    if (
        not isinstance(track_count, int)
        or isinstance(track_count, bool)
        or not MIN_TRACKS <= track_count <= MAX_TRACKS
    ):
        raise ValueError(f"an AccurateRip track count must be 1 to 99: {track_count!r}")
    hex1 = f"{disc.id1:08x}"
    return (
        f"{ACCURATERIP_SCHEME}://{ACCURATERIP_HOST}{DBAR_PATH}"
        f"{hex1[-1]}/{hex1[-2]}/{hex1[-3]}/"
        f"dBAR-{track_count:03d}-{disc.text}.bin"
    )


class LookupState(enum.Enum):
    """The three outcomes. Only FOUND carries responses."""

    FOUND = "found"
    NOT_IN_DATABASE = "not_in_database"
    FAILED = "failed"


@dataclass(frozen=True)
class DbarLookup:
    """What the database said about one disc.

    ``complete`` is False when the reply was cut short after at least one whole
    response (``trailing_bytes`` counts the rest): a checksum found is still
    found, and one not found is then not determined.
    """

    state: LookupState
    url: str = ""
    responses: tuple[DbarResponse, ...] = ()
    complete: bool = False
    trailing_bytes: int = 0
    reason: str = ""


class AccurateRipDbClient(ABC):
    """What the repair needs from AccurateRip: one disc's database answer."""

    @abstractmethod
    def lookup(self, disc: AccurateRipDiscId, track_count: int) -> DbarLookup:
        """The database's answer for ``disc``. Never raises."""
        raise NotImplementedError


def _default_fetcher(url: str) -> bytes:
    """GET ``url`` with our User-Agent and a timeout, reading at most the cap + 1."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 — the URL is built by dbar_url from constants and a validated ID
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:  # noqa: S310 — the URL is built by dbar_url from constants and a validated ID
        data: bytes = response.read(MAX_REPLY_BYTES + 1)
    return data


def read_reply(raw: bytes, disc: AccurateRipDiscId, track_count: int) -> DbarLookup:
    """Check that ``raw`` is dBAR about ``disc``, and read it. Never raises.

    Accepted only when at least one whole response was read and every response
    names this disc's ids and track count: a reply about another disc, or a page
    that is not dBAR at all, is FAILED, never "not in the database".
    """
    if len(raw) > MAX_REPLY_BYTES:
        return DbarLookup(
            LookupState.FAILED,
            reason=f"the reply exceeded {MAX_REPLY_BYTES:,} bytes and was refused",
        )
    parsed = parse_dbar(raw)
    if not parsed.responses:
        why = (
            "the reply was a web page, not an AccurateRip dBAR file"
            if looks_like_markup(raw)
            else parsed.problem or "the reply held no response"
        )
        return DbarLookup(LookupState.FAILED, reason=why)
    for place, response in enumerate(parsed.responses, start=1):
        named = AccurateRipDiscId(response.id1, response.id2, response.cddb)
        if named != disc or response.track_count != track_count:
            return DbarLookup(
                LookupState.FAILED,
                reason=(
                    f"response {place} names disc {named.text} with "
                    f"{response.track_count} tracks, not the {disc.text} with "
                    f"{track_count} tracks that was asked about"
                ),
            )
    return DbarLookup(
        LookupState.FOUND,
        responses=parsed.responses,
        complete=parsed.complete,
        trailing_bytes=parsed.trailing_bytes,
        reason=parsed.problem,
    )


class AccurateRipHttpImpl(AccurateRipDbClient):
    """HTTP implementation against ``www.accuraterip.com``.

    ``fetcher`` None means the module's :func:`_default_fetcher`, looked up at
    CALL time, so the test suite's guard (``tests/conftest.py``) reaches a client
    built before it ran. ``sleep`` is the retry backoff's, injectable for tests.
    """

    def __init__(
        self,
        fetcher: Fetcher | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._fetcher: Fetcher | None = fetcher
        self._sleep: Callable[[float], None] = sleep

    def lookup(self, disc: AccurateRipDiscId, track_count: int) -> DbarLookup:
        try:
            url = dbar_url(disc, track_count)
        except ValueError as exc:
            return DbarLookup(LookupState.FAILED, reason=str(exc))
        log.info("AccurateRip lookup: %s", url)
        fetch = self._fetcher or _default_fetcher
        last = "no attempt was made"
        for attempt, backoff in enumerate(RETRY_BACKOFFS_S, start=1):
            if backoff:
                self._sleep(backoff)  # off the GUI thread (the repair worker)
            try:
                raw = fetch(url)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    log.info("AccurateRip has no entry for this disc (HTTP 404)")
                    return DbarLookup(
                        LookupState.NOT_IN_DATABASE,
                        url=url,
                        complete=True,
                        reason="AccurateRip has no entry for this disc (HTTP 404)",
                    )
                last = f"HTTP {exc.code} {exc.reason}"
                if exc.code < 500:
                    break  # a deterministic answer: retrying asks the same question
                log.warning("AccurateRip attempt %d: %s", attempt, last)
                continue
            except (OSError, ValueError, http.client.HTTPException) as exc:
                last = f"{type(exc).__name__}: {exc}"
                log.warning("AccurateRip attempt %d failed: %s", attempt, last)
                continue
            found = read_reply(raw, disc, track_count)
            if found.state is LookupState.FAILED:
                _record_failure(url, found.reason)
            return DbarLookup(
                found.state,
                url=url,
                responses=found.responses,
                complete=found.complete,
                trailing_bytes=found.trailing_bytes,
                reason=found.reason,
            )
        reason = f"the AccurateRip lookup failed: {last}"
        _record_failure(url, reason)
        return DbarLookup(LookupState.FAILED, url=url, reason=reason)


def _record_failure(url: str, reason: str) -> None:
    """Log and record a failed lookup, so it reaches the log file and the report."""
    log.warning("AccurateRip lookup failed (%s): %s", url, reason)
    diagnostics.warning(
        "accuraterip.query_failed",
        f"the AccurateRip lookup of the repaired audio failed: {reason}. Whether "
        "AccurateRip holds the repaired checksums is not determined.",
        tool="AccurateRip (HTTP)",
        detail=f"{url}\n{reason}",
        where="adapters.accuraterip_db.AccurateRipHttpImpl.lookup",
    )
