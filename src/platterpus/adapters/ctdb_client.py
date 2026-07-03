# SPDX-License-Identifier: GPL-3.0-only
"""Adapter for the CUETools Database (CTDB) lookup service.

Clean-room per PLANNING.md KDD-16: implemented from the LGPL `cuetools.net`
reference and the protocol spec in `docs/archive/upstream-modification-investigation.md`
— never from the GPL-2.0-only `python-cuetoolsdb`. As an unmaintained/external
service this lives behind a thin adapter (Critical Rule #1) so the transport or
provider can be swapped without touching the verify logic.

⚠️ HARDWARE-VALIDATION GATE (KDD-16): the endpoint, query parameters, and
response element/attribute names are reconstructed from the spec and confirmed
present in the LGPL `CUEToolsDB.cs`, but the exact wire behaviour (does our
`toc=` string produce a hit? are these the live attribute names?) must be
verified against the real server with a known disc — see `docs/test-plan.md`.
The XML parsing is unit-tested against fixtures for *what we expect*.
"""

from __future__ import annotations

import logging
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from platterpus import __version__
from platterpus.ctdb.toc import DiscToc

log = logging.getLogger(__name__)

# CTDB is queried over plain HTTP. The reference CUETools client uses
# `http://db.cuetools.net` (CUETools.CTDB/CUEToolsDB.cs: `urlbase = "http://" +
# server`), and the host serves no valid HTTPS certificate — `https://` fails
# with a hostname-mismatch (confirmed on real hardware, KDD-16). HTTP is correct
# here: this is a read-only public CRC lookup, and a rip's trust comes from
# comparing the returned CRC to our locally-computed one, not from the transport.
CTDB_SCHEME: str = "http"
CTDB_HOST: str = "db.cuetools.net"
LOOKUP_PATH: str = "/lookup2.php"
# A descriptive User-Agent is the MusicBrainz/CTDB community convention.
USER_AGENT: str = (
    f"platterpus/{__version__} (https://github.com/rmccann-hub/Platterpus)"
)
# Per-ATTEMPT socket timeout (a healthy lookup is ~0.1-0.4s; db.cuetools.net is
# a hobby server that occasionally stalls). We retry rather than wait out one
# long hang — three quick failures beat a single 20s freeze.
_HTTP_TIMEOUT_S: float = 15.0
# Hard cap on a CTDB lookup response (a few KB in practice) — bounds memory
# against a hostile/misbehaving server over the plain-HTTP transport.
_MAX_RESPONSE_BYTES: int = 8 * 1024 * 1024
# Transient failures (timeout / connection / 5xx) are retried with backoff;
# a clean 404 or a parsed empty response is deterministic and NOT retried.
_RETRY_BACKOFFS_S: tuple[float, ...] = (0.0, 1.5, 3.0)  # len = number of attempts


@dataclass(frozen=True)
class CtdbEntry:
    """One CTDB database entry for a queried TOC.

    `crc`/`confidence` drive the verify verdict; `trackcrcs` is per-track.
    `npar`/`has_parity`/`syndrome`/`entry_id` are Phase-2 (repair) parity
    fields — parsed but unused by verify.
    """

    crc: int | None
    confidence: int
    track_crcs: tuple[int, ...] = ()
    npar: int = 0
    has_parity: bool = False
    entry_id: str = ""


@dataclass(frozen=True)
class CtdbLookupResult:
    """Outcome of a TOC lookup. `entries` empty ⇒ disc not in the database."""

    entries: tuple[CtdbEntry, ...] = ()

    @property
    def in_database(self) -> bool:
        return bool(self.entries)


class CtdbLookupError(RuntimeError):
    """Network/parse failure during a lookup (distinct from 'not in DB')."""


# Injectable fetcher: given a URL, return the response bytes. Default uses
# urllib; tests pass a fake that returns canned XML without touching the net.
Fetcher = Callable[[str], bytes]


class CTDBClient(ABC):
    """What the verify layer needs from CTDB: look up a disc by its TOC."""

    @abstractmethod
    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        """Return the CTDB entries for `toc` (empty result if not in the DB)."""
        raise NotImplementedError


def _default_fetcher(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_S) as response:
        # Bound the read: the transport is plain HTTP (db.cuetools.net serves no
        # valid TLS cert — see CTDB_SCHEME), so a MITM or a misbehaving server
        # could otherwise return a multi-GB body and exhaust memory before the
        # XML parse. A CTDB lookup response is a few KB; 8 MiB is generous.
        data = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(data) > _MAX_RESPONSE_BYTES:
        raise CtdbLookupError(
            f"CTDB response exceeded {_MAX_RESPONSE_BYTES} bytes — refusing it"
        )
    return data


class CtdbHttpImpl(CTDBClient):
    """HTTP implementation against `db.cuetools.net`."""

    def __init__(self, fetcher: Fetcher = _default_fetcher) -> None:
        self._fetch = fetcher

    def build_url(self, toc: DiscToc) -> str:
        """Compose the lookup2.php GET URL for `toc`.

        Params per the spec: version=3, ctdb=1, fuzzy=0, metadata=none, toc=…
        """
        query = urllib.parse.urlencode(
            {
                "version": "3",
                "ctdb": "1",
                "fuzzy": "0",
                "metadata": "none",
                "toc": toc.toc_string(),
            }
        )
        return f"{CTDB_SCHEME}://{CTDB_HOST}{LOOKUP_PATH}?{query}"

    def lookup(self, toc: DiscToc) -> CtdbLookupResult:
        url = self.build_url(toc)
        log.info("CTDB lookup: %s", url)
        last_error: Exception | None = None
        for attempt, backoff in enumerate(_RETRY_BACKOFFS_S):
            if backoff:
                time.sleep(backoff)  # off the GUI thread (CTDB worker); safe
            try:
                raw = self._fetch(url)
            except urllib.error.HTTPError as exc:
                # 4xx is a deterministic server answer (bad request / not found)
                # — don't retry; 5xx is transient — do.
                if exc.code < 500:
                    raise CtdbLookupError(
                        f"CTDB rejected the request (HTTP {exc.code})"
                    ) from exc
                last_error = exc
                log.warning("CTDB attempt %d: HTTP %d", attempt + 1, exc.code)
                continue
            except OSError as exc:
                # URLError / DNS (gaierror) / connection / timeout are all
                # OSError subclasses — transient; retry.
                last_error = exc
                log.warning("CTDB attempt %d failed: %s", attempt + 1, exc)
                continue
            return parse_lookup_response(raw)
        # All attempts exhausted — craft a message that tells the user WHICH
        # failure it was (so "no network" reads differently from "server slow").
        raise CtdbLookupError(_describe_lookup_failure(last_error))


def _describe_lookup_failure(exc: Exception | None) -> str:
    """A user-facing reason for an exhausted CTDB lookup, by failure kind.

    Distinguishes "no network / can't resolve" from "server slow" from "server
    error" so the verdict note tells the user what actually broke — CTDB failing
    is never fatal (AccurateRip is the primary proof), but a clear reason helps.
    """
    attempts = len(_RETRY_BACKOFFS_S)
    if isinstance(exc, urllib.error.HTTPError):
        return f"CTDB server error (HTTP {exc.code}) after {attempts} tries"
    reason = getattr(exc, "reason", None)
    if isinstance(exc, socket.gaierror) or isinstance(reason, socket.gaierror):
        return "couldn't resolve db.cuetools.net — check your internet connection"
    if isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(
        reason, (TimeoutError, socket.timeout)
    ):
        return f"CTDB server too slow to respond (timed out after {attempts} tries)"
    return f"couldn't reach the CTDB server ({exc})"


# --- Response parsing (pure; unit-tested against fixtures) ------------------


def _to_int(value: str | None, *, base: int = 10) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value, base)
    except ValueError:
        return None


def parse_lookup_response(raw: bytes) -> CtdbLookupResult:
    """Parse a CTDB `lookup2.php` XML body into a `CtdbLookupResult`.

    The live server returns a namespaced document
    (``<ctdb xmlns="http://db.cuetools.net/ns/mmd-1.0#"><entry …/></ctdb>``)
    whose entries carry ``crc32`` (hex), ``confidence``, ``npar``, ``id``,
    ``hasparity`` (a URL when present), and ``trackcrcs`` — confirmed against
    the real wire (2026-07-01). We match the ``entry`` tag ignoring its XML
    namespace and read those attribute names, with the older ``crc``/
    ``hasParity`` spellings as fallbacks. Robust to missing/extra attributes —
    unknown shapes yield no entries rather than raising.
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise CtdbLookupError(f"unparseable CTDB response: {exc}") from exc

    def _attr(el: ET.Element, *names: str) -> str | None:
        """First present, non-empty attribute among `names` (order matters)."""
        for name in names:
            value = el.get(name)
            if value:
                return value
        return None

    entries: list[CtdbEntry] = []
    # Match <entry> at any depth AND regardless of XML namespace: ET tags come
    # through as "{namespace}entry", so compare the local name. (The old
    # root.iter("entry") silently matched nothing on the namespaced real doc.)
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] != "entry":
            continue
        crc = _to_int(_attr(el, "crc32", "crc"), base=16)
        if crc is None:
            crc = _to_int(_attr(el, "crc32", "crc"))
        confidence = _to_int(el.get("confidence")) or 0
        npar = _to_int(el.get("npar")) or 0
        # `hasparity` is a URL (to the parity blob) when present — treat any
        # non-empty value as True; also accept the old boolean spelling.
        has_parity_raw = _attr(el, "hasparity", "hasParity") or ""
        has_parity = bool(has_parity_raw) and has_parity_raw.strip().lower() not in {
            "0",
            "false",
            "no",
        }
        track_crcs = tuple(
            v
            for v in (
                _to_int(tok, base=16) for tok in (el.get("trackcrcs") or "").split()
            )
            if v is not None
        )
        entries.append(
            CtdbEntry(
                crc=crc,
                confidence=confidence,
                track_crcs=track_crcs,
                npar=npar,
                has_parity=has_parity,
                entry_id=el.get("id") or "",
            )
        )
    return CtdbLookupResult(entries=tuple(entries))
