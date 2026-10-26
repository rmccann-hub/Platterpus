"""The CTDB parity record: its URL, its syndrome attribute, and its fetch (TASKS R43).

Held against REAL data where the repository has it: the reference disc's lookup
(`tests/fixtures/ctdb_lookup_police_classics.xml`) and the row heads of the real
parity record behind its 1,416-submission entry
(`tests/fixtures/ctdb_parity_32115_rowheads.txt`). The fetch itself is tested with
an injected fetcher, so no test reaches the network.
"""

from __future__ import annotations

import urllib.error
from pathlib import Path
from urllib.parse import urlsplit

from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters import ctdb_client, ctdb_parity
from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbEntry,
    CtdbHttpImpl,
    CtdbLookupResult,
    parse_lookup_response,
)
from platterpus.adapters.ctdb_parity import (
    ParityFetch,
    fetch_parity,
    parity_url,
    parse_syndrome,
)

FIXTURES = Path(__file__).parent / "fixtures"
LOOKUP = FIXTURES / "ctdb_lookup_police_classics.xml"
ROW_HEADS = FIXTURES / "ctdb_parity_32115_rowheads.txt"
STRIDE_WORDS = 11760


def _entries() -> dict[str, CtdbEntry]:
    result = parse_lookup_response(LOOKUP.read_bytes())
    return {e.entry_id: e for e in result.entries}


def _row_heads() -> list[bytes]:
    rows: list[bytes] = []
    for line in ROW_HEADS.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            _index, hexed = line.split()
            rows.append(bytes.fromhex(hexed))
    return rows


# --- the lookup fields, from the real reference-disc answer -------------------


def test_the_dominant_entry_carries_its_parity_url_syndrome_and_stride() -> None:
    entry = _entries()["32115"]
    assert entry.confidence == 1416
    assert entry.parity_url == "http://p.cuetools.net/32115"
    assert entry.npar == 16
    assert entry.stride == 5880
    assert len(entry.syndrome) == 16
    assert entry.syndrome[0] == 0xAA13  # "E6po..." -> bytes 13 aa, little-endian


def test_an_entry_without_parity_has_no_url_and_an_npar8_entry_has_8_words() -> None:
    entries = _entries()
    assert entries["8456102"].parity_url == ""
    assert entries["8456102"].has_parity is False
    assert len(entries["3396214"].syndrome) == 8
    with_parity = [e for e in entries.values() if e.parity_url]
    assert len(with_parity) >= 2  # non-triviality: the fixture has real parity URLs


def test_the_real_record_lays_its_rows_out_as_the_lookup_says() -> None:
    """Row ``i`` of the real record starts with word ``i`` of the lookup's syndrome.

    Two artifacts the server published independently (the record behind
    ``hasparity`` and the ``syndrome`` attribute) agree under our reading of the
    layout: rows of 11,760 little-endian words, row ``i`` holding syndrome ``i``.
    """
    heads = _row_heads()
    assert len(heads) == 16
    syndrome = _entries()["32115"].syndrome
    assert [int.from_bytes(h[:2], "little") for h in heads] == list(syndrome)


# --- URL validation ------------------------------------------------------------


def test_parity_url_accepts_cuetools_hosts_and_resolves_a_relative_path() -> None:
    assert parity_url("http://p.cuetools.net/32115") == "http://p.cuetools.net/32115"
    assert parity_url("https://cuetools.net/x/1") == "https://cuetools.net/x/1"
    assert parity_url("/parity/7") == "http://db.cuetools.net/parity/7"


def test_parity_url_refuses_anything_else() -> None:
    for refused in (
        "",
        None,
        "ftp://p.cuetools.net/1",
        "http://p.cuetools.net.evil.example/1",
        "http://localhost/1",
        "http://127.0.0.1/1",
        "http://p.cuetools.net/1?x=y",
        "http://p.cuetools.net/" + "a" * 300,
        "http://notcuetools.net/1",
    ):
        assert parity_url(refused) == "", refused


@given(st.text(max_size=400))
def test_parity_url_never_raises(text: str) -> None:
    value = parity_url(text)
    if value == "":
        return
    # Parse the host, as the adapter does: a substring test would pass
    # `http://p.cuetools.net.evil.example/`, which the adapter refuses.
    host = urlsplit(value).hostname or ""
    assert host == "cuetools.net" or host.endswith(".cuetools.net"), value


# --- the syndrome attribute -------------------------------------------------------


def test_parse_syndrome_is_all_or_nothing() -> None:
    assert parse_syndrome("GfEkil6sFv4GQlAcVGvvUg==") != ()
    assert parse_syndrome("not base64!") == ()
    assert parse_syndrome("QQ==") == ()  # one byte: not a whole word
    assert parse_syndrome("") == ()
    assert parse_syndrome(None) == ()


@given(st.text(max_size=300))
def test_parse_syndrome_never_raises(text: str) -> None:
    words = parse_syndrome(text)
    assert all(0 <= w <= 0xFFFF for w in words)


# --- the fetch ----------------------------------------------------------------------


def _fake(status: int, body: bytes, seen: list[tuple[str, int, int]] | None = None):
    def fetcher(url: str, nbytes: int, cap: int) -> tuple[int, bytes]:
        if seen is not None:
            seen.append((url, nbytes, cap))
        return status, body

    return fetcher


def test_a_ranged_answer_of_the_right_length_is_kept() -> None:
    seen: list[tuple[str, int, int]] = []
    body = bytes(i % 251 for i in range(4 * STRIDE_WORDS * 2))
    got = fetch_parity(
        "http://p.cuetools.net/1", 4, STRIDE_WORDS, 16, _fake(206, body, seen)
    )
    assert got.error == "" and got.rows == 4 and got.data == body
    assert seen == [
        ("http://p.cuetools.net/1", 4 * STRIDE_WORDS * 2, 16 * STRIDE_WORDS * 2)
    ]


def test_a_whole_record_answer_is_cut_to_the_rows_asked_for() -> None:
    whole = bytes(16 * STRIDE_WORDS * 2)
    got = fetch_parity(
        "http://p.cuetools.net/1", 8, STRIDE_WORDS, 16, _fake(200, whole)
    )
    assert got.error == "" and len(got.data) == 8 * STRIDE_WORDS * 2


def test_a_record_of_any_other_length_is_refused() -> None:
    got = fetch_parity(
        "http://p.cuetools.net/1", 8, STRIDE_WORDS, 16, _fake(206, b"\0" * 10)
    )
    assert got.data == b"" and "wrong length" in got.error


def test_network_failures_become_reasons() -> None:
    def refused(url: str, nbytes: int, cap: int) -> tuple[int, bytes]:
        raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)  # type: ignore[arg-type]  # headers unused

    def broken(url: str, nbytes: int, cap: int) -> tuple[int, bytes]:
        raise TimeoutError("timed out")

    assert (
        "HTTP 403"
        in fetch_parity("http://p.cuetools.net/1", 4, STRIDE_WORDS, 16, refused).error
    )
    assert (
        "TimeoutError"
        in fetch_parity("http://p.cuetools.net/1", 4, STRIDE_WORDS, 16, broken).error
    )


def test_a_shape_outside_the_bounds_is_refused_without_a_request() -> None:
    seen: list[tuple[str, int, int]] = []
    for rows, stride, full in (
        (0, STRIDE_WORDS, 16),
        (17, STRIDE_WORDS, 32),
        (4, 0, 16),
        (8, STRIDE_WORDS, 4),
        (4, STRIDE_WORDS, 65),
    ):
        got = fetch_parity(
            "http://p.cuetools.net/1", rows, stride, full, _fake(206, b"", seen)
        )
        assert "refused" in got.error
    assert seen == []
    assert "no parity URL" in fetch_parity("", 4, STRIDE_WORDS, 16).error


@given(
    st.integers(min_value=0, max_value=600),
    st.binary(max_size=2048),
    st.integers(1, 16),
)
def test_fetch_parity_never_raises(status: int, body: bytes, rows: int) -> None:
    got = fetch_parity("http://p.cuetools.net/1", rows, 64, 16, _fake(status, body))
    assert isinstance(got, ParityFetch)
    assert (got.error == "") == (len(got.data) == rows * 64 * 2)


# --- the client seam ----------------------------------------------------------------


def test_a_client_that_cannot_fetch_parity_says_so() -> None:
    class Lookup(CTDBClient):
        def lookup(self, toc: object) -> CtdbLookupResult:  # type: ignore[override]  # test double
            return CtdbLookupResult()

    entry = _entries()["32115"]
    assert "does not fetch" in Lookup().fetch_parity(entry, 4).error


def test_the_http_client_fetches_through_the_parity_adapter() -> None:
    seen: list[tuple[str, int, int]] = []
    client = CtdbHttpImpl(range_fetcher=_fake(206, bytes(4 * STRIDE_WORDS * 2), seen))
    got = client.fetch_parity(_entries()["32115"], 4)
    assert got.error == ""
    assert seen[0][0] == "http://p.cuetools.net/32115"


def test_both_adapters_send_the_same_user_agent() -> None:
    assert ctdb_parity.USER_AGENT == ctdb_client.USER_AGENT
