# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.adapters.ctdb_client — URL build + XML parse + lookup."""

from __future__ import annotations

import pytest

from platterpus.adapters.ctdb_client import (
    CtdbHttpImpl,
    CtdbLookupError,
    CtdbLookupResult,
    parse_lookup_response,
)
from platterpus.ctdb.toc import DiscToc

_TOC = DiscToc(track_offsets=(150, 18172), leadout=295716)


def test_build_url_has_expected_params() -> None:
    url = CtdbHttpImpl().build_url(_TOC)
    # HTTP, not HTTPS: the host has no valid TLS cert and the reference client
    # uses http:// (see CTDB_SCHEME note in ctdb_client). KDD-16 / hardware.
    assert url.startswith("http://db.cuetools.net/lookup2.php?")
    assert "version=3" in url
    assert "ctdb=1" in url
    # Lead-in-relative offsets (start at 0): each is 150 less than the absolute
    # values in _TOC. ':' is URL-encoded.
    assert "toc=0%3A18022%3A295566" in url


def test_parse_empty_response_means_not_in_db() -> None:
    result = parse_lookup_response(b"<ctdb></ctdb>")
    assert isinstance(result, CtdbLookupResult)
    assert result.in_database is False
    assert result.entries == ()


def test_parse_entry_hex_crc_and_fields() -> None:
    xml = (
        b'<ctdb><entry crc="a1b2c3d4" confidence="7" npar="8" id="abc" '
        b'hasParity="1" trackcrcs="0011 22ff"/></ctdb>'
    )
    result = parse_lookup_response(xml)
    assert result.in_database is True
    (entry,) = result.entries
    assert entry.crc == 0xA1B2C3D4
    assert entry.confidence == 7
    assert entry.npar == 8
    assert entry.has_parity is True
    assert entry.entry_id == "abc"
    assert entry.track_crcs == (0x0011, 0x22FF)


def test_parse_tolerates_missing_attributes() -> None:
    result = parse_lookup_response(b"<ctdb><entry/></ctdb>")
    (entry,) = result.entries
    assert entry.crc is None
    assert entry.confidence == 0
    assert entry.has_parity is False


def test_parse_bad_xml_raises_lookup_error() -> None:
    with pytest.raises(CtdbLookupError):
        parse_lookup_response(b"<not closed")


def test_lookup_uses_injected_fetcher() -> None:
    canned = b'<ctdb><entry crc="00000001" confidence="2"/></ctdb>'
    seen: list[str] = []

    def fake_fetch(url: str) -> bytes:
        seen.append(url)
        return canned

    client = CtdbHttpImpl(fetcher=fake_fetch)
    result = client.lookup(_TOC)
    assert seen and seen[0].startswith("http://db.cuetools.net/")
    assert result.entries[0].crc == 1
    assert result.entries[0].confidence == 2


def test_parse_real_namespaced_wire_format() -> None:
    # The LIVE server returns a namespaced doc with crc32/hasparity (lowercase);
    # the old parser read `crc`/`hasParity` on a non-namespaced `entry` and so
    # matched nothing — CTDB "never worked". Verified against the real wire.
    xml = (
        b'<ctdb xmlns="http://db.cuetools.net/ns/mmd-1.0#">'
        b'<entry crc32="a1b2c3d4" confidence="12" npar="8" id="xyz" '
        b'hasparity="parity/xyz.bin" trackcrcs="0011 22ff"/></ctdb>'
    )
    result = parse_lookup_response(xml)
    assert result.in_database is True
    (entry,) = result.entries
    assert entry.crc == 0xA1B2C3D4
    assert entry.confidence == 12
    assert entry.has_parity is True  # a non-empty URL means parity is available
    assert entry.entry_id == "xyz"
    assert entry.track_crcs == (0x0011, 0x22FF)


def test_lookup_wraps_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch out the backoff so the retry loop doesn't sleep in the test.
    monkeypatch.setattr("platterpus.adapters.ctdb_client._RETRY_BACKOFFS_S", (0.0,))

    def boom(url: str) -> bytes:
        raise OSError("network down")

    with pytest.raises(CtdbLookupError):
        CtdbHttpImpl(fetcher=boom).lookup(_TOC)


def test_lookup_retries_transient_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A transient failure is retried; a later success is returned. No real sleep.
    monkeypatch.setattr(
        "platterpus.adapters.ctdb_client._RETRY_BACKOFFS_S", (0.0, 0.0, 0.0)
    )
    calls: list[int] = []

    def flaky(url: str) -> bytes:
        calls.append(1)
        if len(calls) < 2:
            raise TimeoutError("slow server")
        return b'<ctdb><entry crc32="00000009" confidence="3"/></ctdb>'

    result = CtdbHttpImpl(fetcher=flaky).lookup(_TOC)
    assert len(calls) == 2  # failed once, succeeded on the retry
    assert result.entries[0].crc == 9


def test_lookup_does_not_retry_http_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    monkeypatch.setattr(
        "platterpus.adapters.ctdb_client._RETRY_BACKOFFS_S", (0.0, 0.0, 0.0)
    )
    calls: list[int] = []

    def not_found(url: str) -> bytes:
        calls.append(1)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]

    with pytest.raises(CtdbLookupError, match="HTTP 404"):
        CtdbHttpImpl(fetcher=not_found).lookup(_TOC)
    assert len(calls) == 1  # 4xx is deterministic — not retried
