# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.adapters.ctdb_client — URL build + XML parse + lookup."""

from __future__ import annotations

import pytest

from platterpus.adapters import ctdb_client as cc
from platterpus.adapters.ctdb_client import (
    CtdbHttpImpl,
    CtdbLookupError,
    CtdbLookupResult,
    parse_lookup_response,
)
from platterpus.ctdb.toc import DiscToc

_TOC = DiscToc(track_offsets=(150, 18172), leadout=295716)


def test_default_fetcher_rejects_an_oversized_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: the plain-HTTP CTDB fetch bounds the response so a hostile or
    misbehaving server can't exhaust memory before the XML parse."""

    class _Resp:
        def read(self, n: int) -> bytes:
            return b"x" * n  # always returns the full requested size → over cap

        def __enter__(self):
            return self

        def __exit__(self, *a: object) -> None:
            return None

    monkeypatch.setattr(cc.urllib.request, "urlopen", lambda *a, **k: _Resp())
    with pytest.raises(CtdbLookupError, match="exceeded"):
        cc._default_fetcher("http://db.cuetools.net/lookup2.php?x=1")


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
    """A deterministic REJECTION is not retried and does raise.

    **This test used to use 404 and so pinned the defect it was meant to guard.**
    404 is not a rejection — it is CTDB's way of saying "no entry for this TOC"
    (see the 404 test below for the measurement). 403 is a real deterministic
    refusal, which is what this case was always about.
    """
    import urllib.error

    monkeypatch.setattr(
        "platterpus.adapters.ctdb_client._RETRY_BACKOFFS_S", (0.0, 0.0, 0.0)
    )
    calls: list[int] = []

    def forbidden(url: str) -> bytes:
        calls.append(1)
        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]

    with pytest.raises(CtdbLookupError, match="HTTP 403"):
        CtdbHttpImpl(fetcher=forbidden).lookup(_TOC)
    assert len(calls) == 1  # 4xx is deterministic — not retried


def test_lookup_reads_http_404_as_not_in_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """404 is an ANSWER: the disc is not in CTDB. It must not raise.

    **Measured against the live server on 2026-08-18**, with the control that
    settles it: a real disc's TOC (Nirvana *Nevermind*) returns 200 + 35 KB of
    XML; the same TOC with +1 frame on every offset — structurally identical,
    non-existent — returns 404. Same URL, same parameters, same track count. The
    404 is keyed on the disc, not on the request. CTDB signals a genuinely bad
    request with **200** and the body ``Invalid arguments``.

    Routing 404 into ``CtdbLookupError`` made ``Verdict.NOT_IN_DATABASE``
    unreachable in production — the only other route to it is a 200 with zero
    entries, which the live server never produces for an unknown TOC. Every rip
    of a disc CTDB does not know wrote ``"verdict": "lookup_error"`` and
    ``"message": "CTDB rejected the request (HTTP 404)"`` into the archival JSON.
    Both false.
    """
    import urllib.error

    monkeypatch.setattr(
        "platterpus.adapters.ctdb_client._RETRY_BACKOFFS_S", (0.0, 0.0, 0.0)
    )
    calls: list[int] = []

    def not_found(url: str) -> bytes:
        calls.append(1)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]

    result = CtdbHttpImpl(fetcher=not_found).lookup(_TOC)

    assert result.in_database is False
    assert result.entries == ()
    # Answered on the first try: a 404 is deterministic, so retrying it would be
    # three requests to be told the same thing.
    assert len(calls) == 1
