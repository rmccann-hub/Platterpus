# SPDX-License-Identifier: GPL-3.0-only
"""AccurateRip's database, asked by Platterpus itself (TASKS R138, round 39's G2).

The adapter (``adapters/accuraterip_db.py``), the dBAR parser
(``parsers/accuraterip_dbar.py``) and the tri-state answer
(``accuraterip_db_answer.py``). **No byte here came from AccurateRip**: the dBAR
file is synthesised from the facts of the reference disc as recorded by hand on
2026-11-11 (AccurateRip ID ``001d420f-013bb370-e20dfe0e``, 14 tracks, 1,807
bytes, 13 responses; track 5's entries include ``BCF4E815`` at confidence 200 in
response 1 and ``134C0B9D`` at 129 in response 3; the pre-repair ``F5426D5F`` and
``9EEB8843`` in none). Every other entry is filler we chose. No test reaches the
network: the fetcher is injected, and ``tests/conftest.py`` replaces the default.
"""

from __future__ import annotations

import struct
import urllib.error
from email.message import Message
from typing import Any, Final

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus import diagnostics
from platterpus.accuraterip_db_answer import (
    AR_MATCHED,
    AR_NOT_DETERMINED,
    AR_NOT_IN_DATABASE,
    NO_LOOKUP,
    answer_for,
    summarize,
)
from platterpus.adapters import accuraterip_db
from platterpus.adapters.accuraterip_db import (
    AccurateRipDiscId,
    AccurateRipHttpImpl,
    DbarLookup,
    LookupState,
    dbar_url,
    parse_disc_id,
    read_reply,
)
from platterpus.parsers.accuraterip_dbar import (
    DbarParse,
    entries_for_track,
    parse_dbar,
)

#: The reference disc's AccurateRip ID, as cyanrip's log printed it.
DISC_ID_TEXT: Final[str] = "001d420f-013bb370-e20dfe0e"
DISC: Final[AccurateRipDiscId] = AccurateRipDiscId(0x001D420F, 0x013BB370, 0xE20DFE0E)
TRACKS: Final[int] = 14
#: Track 5 after the CTDB repair: our own v1 and v2 of the repaired file.
V1_AFTER: Final[int] = 0x134C0B9D
V2_AFTER: Final[int] = 0xBCF4E815
#: Track 5 as read, before the repair: in no response.
V1_BEFORE: Final[int] = 0xF5426D5F
V2_BEFORE: Final[int] = 0x9EEB8843


def response(
    disc: AccurateRipDiscId = DISC,
    tracks: list[tuple[int, int]] | None = None,
    count: int | None = None,
) -> bytes:
    """One synthesised dBAR response: the header, then (confidence, crc) per track."""
    rows = tracks if tracks is not None else [(3, 0x1000 + i) for i in range(TRACKS)]
    head = struct.pack(
        "<BIII", len(rows) if count is None else count, disc.id1, disc.id2, disc.cddb
    )
    return head + b"".join(
        struct.pack("<BII", c, crc, 0xAAAA0000 + crc & 0xFFFFFFFF) for c, crc in rows
    )


def reference_dbar() -> bytes:
    """The reference disc's file, from the facts: 13 responses, 1,807 bytes."""
    responses = []
    for place in range(1, 14):
        rows = [(place, 0x10000 * place + i) for i in range(TRACKS)]
        if place == 1:
            rows[4] = (200, V2_AFTER)
        if place == 3:
            rows[4] = (129, V1_AFTER)
        responses.append(response(tracks=rows))
    return b"".join(responses)


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", code, "status", Message(), None)


# --- the URL --------------------------------------------------------------------------


def test_the_url_takes_id1s_lowest_three_hex_digits_in_that_order() -> None:
    """Checked by hand 2026-11-11: id1 001d420f is f/0/2; another order is a 404."""
    assert dbar_url(DISC, TRACKS) == (
        "http://www.accuraterip.com/accuraterip/f/0/2/"
        "dBAR-014-001d420f-013bb370-e20dfe0e.bin"
    )
    assert dbar_url(AccurateRipDiscId(0xABC, 0, 0), 1).endswith(
        "/c/b/a/dBAR-001-00000abc-00000000-00000000.bin"
    )


@pytest.mark.parametrize("count", [0, 100, -1, True])
def test_a_track_count_the_url_cannot_carry_is_refused(count: Any) -> None:
    with pytest.raises(ValueError, match="1 to 99"):
        dbar_url(DISC, count)
    looked = AccurateRipHttpImpl(fetcher=_never).lookup(DISC, count)
    assert looked.state is LookupState.FAILED and "1 to 99" in looked.reason


def _never(url: str) -> bytes:
    raise AssertionError(f"a refused lookup reached the network: {url}")


def test_the_disc_id_is_read_strictly() -> None:
    assert parse_disc_id(DISC_ID_TEXT) == DISC
    assert parse_disc_id(f"  {DISC_ID_TEXT.upper()}\n") == DISC
    assert parse_disc_id(DISC) is None  # not text
    for bad in ("", "001d420f-013bb370", "001d420f-013bb370-e20dfe0e-0", "zz" * 12):
        assert parse_disc_id(bad) is None, bad
    assert DISC.text == DISC_ID_TEXT


# --- the parser -------------------------------------------------------------------------


def test_the_reference_file_reads_as_13_responses_of_14_tracks() -> None:
    raw = reference_dbar()
    assert len(raw) == 1807
    parsed = parse_dbar(raw)
    assert parsed.complete and parsed.trailing_bytes == 0
    assert len(parsed.responses) == 13
    assert {r.track_count for r in parsed.responses} == {TRACKS}
    five = entries_for_track(parsed.responses, 5)
    assert (V2_AFTER, 200) == five[0] and (V1_AFTER, 129) == five[2]
    crcs = {crc for crc, _ in five}
    assert V1_BEFORE not in crcs and V2_BEFORE not in crcs
    assert entries_for_track(parsed.responses, 15) == ()
    assert entries_for_track(parsed.responses, 0) == ()


def test_a_truncated_tail_is_counted_never_dropped() -> None:
    raw = reference_dbar()[:-5]
    parsed = parse_dbar(raw)
    assert len(parsed.responses) == 12 and not parsed.complete
    assert parsed.trailing_bytes == 139 - 5
    assert "cut short" in parsed.problem


@pytest.mark.parametrize(
    ("raw", "words"),
    [
        (b"", "empty"),
        (b"<!DOCTYPE html><html>404 Not Found</html>", "HTML"),
        (b"\x00" + b"\x01" * 20, "0 tracks"),
        (b"\x0e" + b"\x00" * 5, "6 bytes"),
    ],
)
def test_what_is_not_dbar_reads_as_nothing_and_says_why(raw: bytes, words: str) -> None:
    parsed = parse_dbar(raw)
    assert parsed.responses == () and not parsed.complete
    assert words in parsed.problem


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(st.binary(max_size=4096))
def test_parse_dbar_never_raises(raw: bytes) -> None:
    """CLAUDE.md: a parser of external output never raises, on any bytes."""
    parsed = parse_dbar(raw)
    assert isinstance(parsed, DbarParse)
    read = sum(13 + 9 * r.track_count for r in parsed.responses)
    if not parsed.problem.startswith("the reply was an HTML"):
        assert read + parsed.trailing_bytes == len(raw)  # every byte accounted for


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(
        st.lists(
            st.tuples(st.integers(0, 255), st.integers(0, 2**32 - 1)),
            min_size=1,
            max_size=99,
        ),
        min_size=1,
        max_size=8,
    )
)
def test_synthesised_responses_read_back_exactly(
    rows: list[list[tuple[int, int]]],
) -> None:
    raw = b"".join(response(tracks=r) for r in rows)
    parsed = parse_dbar(raw)
    if raw.lstrip()[:1] == b"<":  # a track count of 60 after blanks: a page's shape
        return
    assert parsed.complete
    assert [[(t.confidence, t.crc) for t in r.tracks] for r in parsed.responses] == rows


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(st.binary(max_size=2048), st.integers(-5, 120))
def test_read_reply_never_raises(raw: bytes, count: int) -> None:
    found = read_reply(raw, DISC, count)
    assert isinstance(found, DbarLookup)
    assert found.state in (LookupState.FOUND, LookupState.FAILED)


# --- the adapter ---------------------------------------------------------------------


def test_a_lookup_reads_the_reference_disc() -> None:
    asked: list[str] = []

    def fetch(url: str) -> bytes:
        asked.append(url)
        return reference_dbar()

    found = AccurateRipHttpImpl(fetcher=fetch).lookup(DISC, TRACKS)
    assert found.state is LookupState.FOUND and found.complete
    assert len(found.responses) == 13 and asked == [dbar_url(DISC, TRACKS)]
    assert found.url == asked[0]


def test_a_404_is_not_in_the_database() -> None:
    def fetch(url: str) -> bytes:
        raise _http_error(404)

    found = AccurateRipHttpImpl(fetcher=fetch).lookup(DISC, TRACKS)
    assert found.state is LookupState.NOT_IN_DATABASE
    assert "HTTP 404" in found.reason


def test_an_html_page_is_a_failure_not_an_answer() -> None:
    diagnostics.clear()
    page = b"<html><body>404 Not Found</body></html>"
    found = AccurateRipHttpImpl(fetcher=lambda _u: page).lookup(DISC, TRACKS)
    assert found.state is LookupState.FAILED
    assert "web page" in found.reason
    assert "accuraterip.query_failed" in diagnostics.default_log().codes()


def test_a_reply_about_another_disc_is_refused() -> None:
    other = AccurateRipDiscId(DISC.id1, DISC.id2 + 1, DISC.cddb)
    raw = reference_dbar() + response(disc=other)
    found = AccurateRipHttpImpl(fetcher=lambda _u: raw).lookup(DISC, TRACKS)
    assert (
        found.state is LookupState.FAILED and "response 14 names disc" in found.reason
    )
    count = AccurateRipHttpImpl(fetcher=lambda _u: reference_dbar()).lookup(DISC, 13)
    assert count.state is LookupState.FAILED and "14 tracks" in count.reason


def test_transient_failures_are_retried_and_a_refusal_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The suite's guard zeroes the backoffs; put the real ones back to see them.
    monkeypatch.setattr(accuraterip_db, "RETRY_BACKOFFS_S", (0.0, 1.5, 3.0))
    calls: list[str] = []

    def flaky(url: str) -> bytes:
        calls.append(url)
        if len(calls) < 3:
            raise _http_error(503) if len(calls) == 1 else TimeoutError("slow")
        return reference_dbar()

    slept: list[float] = []
    found = AccurateRipHttpImpl(fetcher=flaky, sleep=slept.append).lookup(DISC, TRACKS)
    assert found.state is LookupState.FOUND and len(calls) == 3
    assert slept == [1.5, 3.0]  # waited between tries, never before the first

    refusals: list[str] = []

    def forbidden(url: str) -> bytes:
        refusals.append(url)
        raise _http_error(403)

    refused = AccurateRipHttpImpl(fetcher=forbidden).lookup(DISC, TRACKS)
    assert refused.state is LookupState.FAILED and "HTTP 403" in refused.reason
    assert len(refusals) == 1


def test_an_oversized_reply_is_refused() -> None:
    raw = b"\x01" * (accuraterip_db.MAX_REPLY_BYTES + 1)
    found = AccurateRipHttpImpl(fetcher=lambda _u: raw).lookup(DISC, TRACKS)
    assert found.state is LookupState.FAILED and "exceeded" in found.reason


def test_the_real_fetcher_names_itself_and_bounds_the_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    class _Reply:
        def read(self, n: int) -> bytes:
            seen["read"] = n
            return b"ok"

        def __enter__(self) -> _Reply:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def _urlopen(request: Any, timeout: float) -> _Reply:
        seen["ua"] = request.get_header("User-agent")
        seen["timeout"] = timeout
        return _Reply()

    # The suite's guard (tests/conftest.py) replaced `_default_fetcher` through this
    # same `monkeypatch`; undo it to reach the real one, with `urlopen` faked.
    assert accuraterip_db._default_fetcher.__name__ == "_offline"
    monkeypatch.undo()
    assert accuraterip_db._default_fetcher.__name__ == "_default_fetcher"
    monkeypatch.setattr(accuraterip_db.urllib.request, "urlopen", _urlopen)
    assert accuraterip_db._default_fetcher(dbar_url(DISC, TRACKS)) == b"ok"
    assert seen["ua"].startswith("platterpus/")
    assert seen["timeout"] == accuraterip_db.HTTP_TIMEOUT_S
    assert seen["read"] == accuraterip_db.MAX_REPLY_BYTES + 1


def test_the_suites_guard_keeps_a_default_client_off_the_network(
    accuraterip_requests: list[str],
) -> None:
    """The stand-in for the real fetcher: it records the URL and fails at once."""
    found = AccurateRipHttpImpl().lookup(DISC, TRACKS)
    assert found.state is LookupState.FAILED
    assert "must not reach the internet" in found.reason
    assert accuraterip_requests == [dbar_url(DISC, TRACKS)] * len(
        accuraterip_db.RETRY_BACKOFFS_S
    )


# --- the answer, tri-state ---------------------------------------------------------------


def _found() -> DbarLookup:
    return AccurateRipHttpImpl(fetcher=lambda _u: reference_dbar()).lookup(DISC, TRACKS)


def test_track_5s_repaired_audio_is_matched_and_the_read_is_not() -> None:
    found = _found()
    assert answer_for(found, 5, V1_AFTER).answer == AR_MATCHED
    assert answer_for(found, 5, V1_AFTER).confidence == 129
    assert answer_for(found, 5, V2_AFTER).confidence == 200
    before = answer_for(found, 5, V2_BEFORE)
    assert before.answer == AR_NOT_IN_DATABASE and "13 responses" in before.reason
    # The right CRC on the wrong track is not a match: entries are per track.
    assert answer_for(found, 4, V2_AFTER).answer == AR_NOT_IN_DATABASE


def test_a_cut_short_reply_cannot_say_not_in_the_database() -> None:
    cut = AccurateRipHttpImpl(fetcher=lambda _u: reference_dbar()[:-5]).lookup(
        DISC, TRACKS
    )
    assert cut.state is LookupState.FOUND and not cut.complete
    assert answer_for(cut, 5, V2_AFTER).answer == AR_MATCHED  # response 1 was read
    missing = answer_for(cut, 5, V2_BEFORE)
    assert missing.answer == AR_NOT_DETERMINED and "cut short" in missing.reason


def test_without_an_answer_the_answer_is_not_determined() -> None:
    assert answer_for(None, 5, V2_AFTER) == answer_for(None, 5, V2_AFTER)
    none = answer_for(None, 5, V2_AFTER)
    assert none.answer == AR_NOT_DETERMINED and none.reason == NO_LOOKUP
    failed = answer_for(DbarLookup(LookupState.FAILED, reason="offline"), 5, V2_AFTER)
    assert failed.answer == AR_NOT_DETERMINED and failed.reason == "offline"
    gone = DbarLookup(LookupState.NOT_IN_DATABASE, reason="no entry (HTTP 404)")
    assert answer_for(gone, 5, V2_AFTER).answer == AR_NOT_IN_DATABASE
    assert answer_for(_found(), 5, None).answer == AR_NOT_DETERMINED
    assert answer_for(_found(), 5, True).answer == AR_NOT_DETERMINED  # not a CRC
    assert summarize(None).state == "not_made"
    assert summarize(_found()).responses == 13
