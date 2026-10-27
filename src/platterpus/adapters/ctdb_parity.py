# SPDX-License-Identifier: GPL-3.0-only
"""Fetch a CTDB entry's parity record: the data that locates where a rip differs.

Clean-room per PLANNING.md KDD-16: written from the published format, read in the
LGPL ``cuetools.net`` source (``CUETools.CTDB/CUEToolsDB.cs`` ``FetchDB`` and
``CUETools.Parity/Parity2Syndrome.cs`` ``Bytes2Syndrome``), and checked against the
live server on 2026-10-26 (below). No code was copied.

**What the record is.** Each CTDB entry that has one carries a ``hasparity`` URL
(``http://p.cuetools.net/32115`` for the reference disc's 1,416-submission entry).
Behind it is ``npar`` rows of ``stride`` little-endian 16-bit words: row ``i`` is
the entry's Reed-Solomon syndrome ``S_i`` for every one of the 11,760 interleaved
columns of the disc's audio (:mod:`platterpus.ctdb.syndromes` says what a
syndrome is). The lookup's own ``syndrome`` attribute is column 0 of those rows.
Because syndrome ``i`` does not depend on ``npar``, the first ``k`` rows are the
record for ``npar = k``; CUETools fetches 4, then 8, then 16 rows with HTTP
``Range`` requests, and so do we, up to 16 (CUETools' ``maxNpar``).

**Measured, not assumed (2026-10-26, curl 8.x through the session proxy):** entry
32115 (``npar="16" stride="5880"``) returned ``200``, ``content-length 376320`` =
16 × 11,760 × 2; a ``Range: bytes=0-15`` request returned ``206``; and the first
word of each of its 16 rows equals, in order, the 16 words of that entry's
``syndrome`` attribute in ``tests/fixtures/ctdb_lookup_police_classics.xml``.
Entry 3396214 (``npar="8"``) returned 188,160 bytes = 8 × 11,760 × 2.

**External input, validated at the boundary** (CLAUDE.md, *Validate every input*):
the URL comes from the lookup response, so it must be http(s) on ``cuetools.net``
or one of its subdomains, with a bounded path, or it is refused rather than
fetched. The body is read to at most the size the request asked for, plus one
byte to detect an over-long answer. Nothing here raises: every failure becomes a
:class:`ParityFetch` whose ``error`` says what went wrong, which the localisation
reports as "not determined".
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from platterpus import __version__

log = logging.getLogger(__name__)

#: The most parity rows we use: CUETools' ``AccurateRipVerify.maxNpar``. A row
#: count beyond it would correct more errors than CUETools itself ever claims.
MAX_NPAR: int = 16

#: Where a relative ``hasparity`` ("/32115") is resolved, as CUETools' ``urlbase``.
_RELATIVE_BASE: str = "http://db.cuetools.net"

#: A parity URL we will fetch: http(s), a host under cuetools.net, a short path of
#: URL-safe characters. Named groups and bounded repeats, so it runs in linear time.
_PARITY_URL = re.compile(
    r"(?P<scheme>https?)://(?P<host>[A-Za-z0-9.-]{1,253})(?P<path>/[A-Za-z0-9._~/-]{0,200})"
)

#: The base64 text of a ``syndrome`` attribute: at most 16 words = 32 bytes = 44
#: characters, with room for a server that sends up to 64 words.
_SYNDROME_TEXT = re.compile(r"(?P<b64>[A-Za-z0-9+/]{1,172}={0,2})")

_HTTP_TIMEOUT_S: float = 15.0

#: Given a URL, how many bytes to ask for and the most to read, return ``(HTTP
#: status, body)``. Injected in tests so no test reaches the network.
RangeFetcher = Callable[[str, int, int], tuple[int, bytes]]

#: The most rows a record may claim (64 × 11,760 × 2 bytes = 1.5 MB), so a
#: response cannot make us read more than that whatever its ``npar`` says.
MAX_RECORD_ROWS: int = 64

#: The lookup adapter's User-Agent (``ctdb_client.USER_AGENT``), spelled here so
#: this module needs nothing from that one; a test holds the two equal.
USER_AGENT: str = (
    f"platterpus/{__version__} (https://github.com/rmccann-hub/Platterpus)"
)


@dataclass(frozen=True)
class ParityFetch:
    """The first ``rows`` parity rows of an entry, or why they could not be had.

    ``data`` is exactly ``rows × stride_words × 2`` bytes when ``error`` is empty.
    """

    data: bytes = b""
    rows: int = 0
    error: str = ""


def parity_url(text: str | None) -> str:
    """The entry's validated parity URL, or ``""`` when it has none we will fetch.

    A relative path resolves against CTDB's own host, as CUETools does. Anything
    else (another host, another scheme, a long or odd path) is refused, because a
    URL a response hands us is not one we should visit on its say-so.
    """
    if not text:
        return ""
    candidate = text.strip()
    if candidate.startswith("/"):
        candidate = _RELATIVE_BASE + candidate
    match = _PARITY_URL.fullmatch(candidate)
    if match is None:
        return ""
    host = match.group("host").lower()
    if host != "cuetools.net" and not host.endswith(".cuetools.net"):
        return ""
    return candidate


def parse_syndrome(text: str | None) -> tuple[int, ...]:
    """The ``syndrome`` attribute as 16-bit words, or ``()`` when unreadable.

    Base64 of little-endian 16-bit words: column 0 of the entry's parity rows,
    which is what a fetched record is checked against. All or nothing, like the
    per-track CRC list: a partial read would compare the wrong words.
    """
    if not text or _SYNDROME_TEXT.fullmatch(text.strip()) is None:
        return ()
    try:
        raw = base64.b64decode(text.strip(), validate=True)
    except (binascii.Error, ValueError):
        return ()
    if not raw or len(raw) % 2:
        return ()
    return tuple(
        int.from_bytes(raw[i : i + 2], "little") for i in range(0, len(raw), 2)
    )


def _default_range_fetcher(url: str, nbytes: int, cap: int) -> tuple[int, bytes]:
    """GET the first ``nbytes`` of ``url`` with a ``Range`` header, reading at most ``cap + 1``."""
    request = urllib.request.Request(  # noqa: S310 — a request for a URL parity_url() already held to http(s) on cuetools.net
        url, headers={"Range": f"bytes=0-{nbytes - 1}", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_S) as response:  # noqa: S310 — parity_url() admits only http(s) on cuetools.net before a URL gets here
        status = int(response.status)
        # A server that ignores Range answers 200 with the whole record, so allow
        # that much (``cap``), and one byte more to see an over-long answer.
        body: bytes = response.read(cap + 1)
    return status, body


def fetch_parity(
    url: str,
    rows: int,
    stride_words: int,
    full_rows: int,
    fetcher: RangeFetcher = _default_range_fetcher,
) -> ParityFetch:
    """Fetch the first ``rows`` rows of an entry's parity record. Never raises.

    ``full_rows`` is the entry's own ``npar``: a server that ignores ``Range``
    sends all of them, and the first ``rows`` are kept, as CUETools does. Any other
    length is refused: a short record cannot be lined up with the columns.
    """
    if not url:
        return ParityFetch(error="the entry has no parity URL we will fetch")
    if (
        not 1 <= rows <= MAX_NPAR
        or not 0 < stride_words <= 65535
        or not rows <= full_rows <= MAX_RECORD_ROWS
    ):
        return ParityFetch(
            error=f"parity shape refused (rows {rows}, of {full_rows}, stride {stride_words})"
        )
    wanted = rows * stride_words * 2
    whole = full_rows * stride_words * 2
    try:
        status, body = fetcher(url, wanted, whole)
    except urllib.error.HTTPError as exc:
        return ParityFetch(error=f"parity fetch refused (HTTP {exc.code})")
    except (OSError, ValueError) as exc:
        log.warning("CTDB parity fetch failed for %s: %s", url, exc)
        return ParityFetch(error=f"parity fetch failed ({type(exc).__name__}: {exc})")
    if status == 206 and len(body) == wanted:
        return ParityFetch(data=body, rows=rows)
    if status == 200 and len(body) == whole:
        return ParityFetch(data=body[:wanted], rows=rows)
    return ParityFetch(
        error=(
            f"parity record has the wrong length (HTTP {status}, {len(body):,} bytes; "
            f"expected {wanted:,}, or {whole:,} for the whole record)"
        )
    )
