"""A server's answer is external input: malformed, oversized, wrong-typed or hostile.

Peer review 2.8 (the claude-code-skills session, 2026-10-26). For each server the
app talks to, the property is the same: whatever comes back, the adapter returns
its documented result or raises its one documented error, never anything else;
what it returns is the type it declares; and what it takes from the answer is
bounded and screened before anything acts on it. Where each adapter stood before
this file, and what already held it:

* **MusicBrainz** (`adapters/musicbrainz_client.py`, through `musicbrainzngs`):
  example tests only (`tests/test_musicbrainz_client.py`, sparse and odd
  metadata, 404, web-service errors). No property. **Found here:** a payload of
  the wrong shape (a list where an object belongs, a number where a title
  belongs) raised `AttributeError` / `TypeError` out of the adapter, and a title
  that was not a string was handed on as one.
* **AccurateRip**: we never ask it. cyanrip does, and its answer reaches us only
  as cyanrip's log, whose parser has its never-raises properties
  (`tests/test_parsers_property.py`, `tests/test_parsers_structure_fuzz.py`,
  `tests/test_never_raises_contract.py`).
* **CTDB** (`adapters/ctdb_client.py`): size cap and bad XML were held by
  examples (`tests/test_ctdb_client.py`); parity URLs are host-checked
  (`adapters/ctdb_parity.parity_url`). No property; added here, with the
  entity-expansion bomb.
* **Cover Art Archive** (`adapters/cover_art.py`): `image_extension` had a
  property (`tests/test_cover_art.py`), the front-cover fetch examples. **Found
  here:** the typed-image manifest that `save_additional_covers` reads raised out
  of a function documented never to raise (an `images` that is not a list, a
  deeply nested document), fetched any URL the manifest named (`file://` and any
  host included), and had no bound on how many images it fetched.
* **The update check** (`update_check.py`): garbage and oversize held by
  examples (`tests/test_update_check.py`). **Found here:** a tag with
  surrounding whitespace survived into the version we show and build a download
  URL from, and the release page URL was taken from the answer unchecked and
  opened in the browser.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final
from unittest import mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.adapters import cover_art, ctdb_client, musicbrainz_client
from platterpus.adapters.ctdb_client import CtdbLookupError, parse_lookup_response
from platterpus.adapters.musicbrainz_client import (
    MusicBrainzNgsImpl,
    MusicBrainzQueryError,
    ReleaseDetail,
    ReleaseSummary,
    TrackSummary,
)
from platterpus.update_check import (
    RELEASES_PAGE_URL,
    available_releases,
    latest_release,
)

#: Keys the adapters look for, so generated payloads reach past the first `.get`.
_KEYS: Final[list[str]] = [
    "release",
    "disc",
    "release-list",
    "id",
    "title",
    "artist-credit",
    "artist",
    "name",
    "date",
    "country",
    "disambiguation",
    "medium-list",
    "track-list",
    "track-count",
    "recording",
    "position",
    "number",
    "length",
    "format",
    "disc-list",
    "label-info-list",
    "label",
    "catalog-number",
    "barcode",
    "tag-list",
    "count",
    "isrc-list",
    "images",
    "types",
    "image",
    "tag_name",
    "html_url",
    "prerelease",
]

_SCALAR = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(10**6), max_value=10**6)
    | st.floats(allow_nan=False)
    | st.text(max_size=12)
    | st.sampled_from(["1", "2", "CD", "back", "booklet", "v0.7.113", "Front"])
)

_JSON: st.SearchStrategy[Any] = st.recursive(
    _SCALAR,
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(
            st.sampled_from(_KEYS) | st.text(max_size=4), inner, max_size=6
        )
    ),
    max_leaves=25,
)

_FAST = settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)


# --- MusicBrainz ---------------------------------------------------------------


def _assert_summary_is_typed(summary: ReleaseSummary) -> None:
    for name in (
        "mbid",
        "title",
        "artist_credit",
        "date",
        "country",
        "label",
        "catalog_number",
        "barcode",
        "medium_format",
        "disambiguation",
        "genre",
    ):
        value = getattr(summary, name)
        assert isinstance(value, str), (name, value)
        assert len(value) <= musicbrainz_client.MAX_TEXT_CHARS + 1, name


def _assert_track_is_typed(track: TrackSummary) -> None:
    assert isinstance(track.number, int)
    for name in ("title", "artist_credit", "isrc"):
        value = getattr(track, name)
        assert isinstance(value, str), (name, value)


@_FAST
@given(payload=_JSON)
def test_a_disc_id_answer_of_ANY_shape_is_a_list_or_the_documented_error(
    payload: object,
) -> None:
    client = MusicBrainzNgsImpl("platterpus-test", "0", "test@example.invalid")
    with mock.patch.object(
        musicbrainz_client.musicbrainzngs,
        "get_releases_by_discid",
        return_value=payload,
    ):
        try:
            result = client.releases_by_disc_id("disc")
        except MusicBrainzQueryError:
            return
    assert isinstance(result, list)
    for summary in result:
        _assert_summary_is_typed(summary)


@_FAST
@given(payload=_JSON)
def test_a_release_answer_of_ANY_shape_is_a_release_or_the_documented_error(
    payload: object,
) -> None:
    client = MusicBrainzNgsImpl("platterpus-test", "0", "test@example.invalid")
    with mock.patch.object(
        musicbrainz_client.musicbrainzngs, "get_release_by_id", return_value=payload
    ):
        try:
            detail = client.release_by_mbid("mbid", disc_track_count=3)
        except MusicBrainzQueryError:
            return
    assert isinstance(detail, ReleaseDetail)
    _assert_summary_is_typed(detail.summary)
    for track in detail.tracks:
        _assert_track_is_typed(track)


def test_a_release_answer_with_WRONG_TYPES_is_coerced_not_passed_on() -> None:
    """The case the property found, pinned: a number for a title is no title."""
    payload = {
        "release": {
            "id": 7,
            "title": 12345,
            "date": ["1971"],
            "medium-list": [
                {
                    "position": "1",
                    "track-list": [
                        {"position": "1", "recording": {"title": 99, "id": "r"}}
                    ],
                }
            ],
        }
    }
    client = MusicBrainzNgsImpl("platterpus-test", "0", "test@example.invalid")
    with mock.patch.object(
        musicbrainz_client.musicbrainzngs, "get_release_by_id", return_value=payload
    ):
        detail = client.release_by_mbid("mbid")
    assert detail.summary.title == "" and detail.summary.mbid == ""
    assert detail.summary.date == ""
    assert [t.title for t in detail.tracks] == [""]


def test_an_ordinary_release_answer_is_read_unchanged() -> None:
    """The floor: a coercion that blanked everything would pass the tests above."""
    payload = {
        "release": {
            "id": "abc",
            "title": "Abbey Road",
            "artist-credit": [{"artist": {"name": "The Beatles"}}],
            "date": "1969-09-26",
            "medium-list": [
                {
                    "position": "1",
                    "format": "CD",
                    "track-list": [
                        {
                            "position": "1",
                            "recording": {
                                "title": "Come Together",
                                "isrc-list": ["GBAYE0601690"],
                            },
                        }
                    ],
                }
            ],
        }
    }
    client = MusicBrainzNgsImpl("platterpus-test", "0", "test@example.invalid")
    with mock.patch.object(
        musicbrainz_client.musicbrainzngs, "get_release_by_id", return_value=payload
    ):
        detail = client.release_by_mbid("abc")
    assert (detail.summary.mbid, detail.summary.title) == ("abc", "Abbey Road")
    assert detail.summary.artist_credit == "The Beatles"
    assert detail.tracks[0].title == "Come Together"
    assert detail.tracks[0].isrc == "GBAYE0601690"


def test_an_absurdly_long_title_is_bounded_and_the_cut_is_marked() -> None:
    long_title = "A" * (musicbrainz_client.MAX_TEXT_CHARS * 3)
    payload = {"release": {"id": "x", "title": long_title}}
    client = MusicBrainzNgsImpl("platterpus-test", "0", "test@example.invalid")
    with mock.patch.object(
        musicbrainz_client.musicbrainzngs, "get_release_by_id", return_value=payload
    ):
        title = client.release_by_mbid("x").summary.title
    assert len(title) == musicbrainz_client.MAX_TEXT_CHARS + 1
    assert title.endswith("…")


# --- CTDB ----------------------------------------------------------------------


@_FAST
@given(raw=st.binary(max_size=300))
def test_ANY_ctdb_body_parses_or_raises_the_documented_error(raw: bytes) -> None:
    try:
        result = parse_lookup_response(raw)
    except CtdbLookupError:
        return
    assert isinstance(result.entries, tuple)


_ATTR = st.sampled_from(
    ["crc32", "crc", "confidence", "npar", "hasparity", "trackcrcs", "id", "stride"]
)


@_FAST
@given(
    attrs=st.lists(
        st.dictionaries(
            _ATTR,
            # Text XML can carry at all: no control characters, no surrogates. An
            # unparseable body is the other test's subject.
            st.text(
                alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
                max_size=20,
            ),
            max_size=6,
        ),
        max_size=5,
    )
)
def test_ANY_ctdb_entry_attributes_parse_without_raising(
    attrs: list[dict[str, str]],
) -> None:
    from xml.sax.saxutils import quoteattr

    entries = "".join(
        "<entry " + " ".join(f"{k}={quoteattr(v)}" for k, v in a.items()) + "/>"
        for a in attrs
    )
    body = f'<ctdb xmlns="http://db.cuetools.net/ns/mmd-1.0#">{entries}</ctdb>'
    result = parse_lookup_response(body.encode("utf-8"))
    assert len(result.entries) == len(attrs)
    for entry in result.entries:
        assert entry.parity_url == "" or "cuetools.net" in entry.parity_url


def test_an_entity_expansion_bomb_is_refused_not_expanded() -> None:
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        + b"".join(
            f'<!ENTITY lol{i} "{("&lol" + (str(i - 1) if i > 1 else "") + ";") * 10}">'.encode()
            for i in range(1, 10)
        )
        + b"]><ctdb>&lol9;</ctdb>"
    )
    with pytest.raises(CtdbLookupError):
        parse_lookup_response(bomb)


def test_the_ctdb_lookup_turns_a_hostile_body_into_its_documented_error() -> None:
    client = ctdb_client.CtdbHttpImpl(fetcher=lambda _url: b"\x00not xml")
    from platterpus.ctdb.toc import DiscToc

    toc = DiscToc(track_offsets=(150,), leadout=20000)
    with pytest.raises(CtdbLookupError):
        client.lookup(toc)


# --- Cover Art Archive ---------------------------------------------------------


@_FAST
@given(body=st.binary(max_size=64))
def test_ANY_front_cover_body_is_an_image_or_none(body: bytes) -> None:
    data = cover_art.fetch_front_cover("mbid", fetcher=lambda _url: body)
    assert data is None or (cover_art.image_extension(data) and data == body)


@_FAST
@given(manifest=_JSON)
def test_ANY_manifest_never_raises_and_only_writes_images(
    manifest: object, tmp_path_factory: pytest.TempPathFactory
) -> None:
    rip_dir = tmp_path_factory.mktemp("rip")
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 16
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        if (
            url.startswith(cover_art.MANIFEST_URL_TEMPLATE.split("{")[0])
            and url.count("/") == 4
        ):
            return json.dumps(manifest).encode()
        fetched.append(url)
        return png

    saved = cover_art.save_additional_covers(rip_dir, "mbid", fetcher=fetch)
    assert all(isinstance(name, str) for name in saved)
    assert all(cover_art.image_url_is_ours(url) for url in fetched), fetched
    assert len(fetched) <= cover_art.MAX_EXTRA_IMAGES


@pytest.mark.parametrize(
    "manifest",
    [
        b'{"images": 5}',
        b'{"images": [{"types": 7, "image": "https://archive.org/x.png"}]}',
        b"[" * 100_000 + b"]" * 100_000,
        b"\xff\xfe not json",
    ],
)
def test_a_MALFORMED_manifest_is_no_images_not_a_crash(
    manifest: bytes, tmp_path: Path
) -> None:
    assert cover_art.save_additional_covers(
        tmp_path, "mbid", fetcher=lambda _url: manifest
    ) in ([], ["back.png"])


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://archive.org/x.jpg",
        "http://localhost:631/x.jpg",
        "https://evil.example/x.jpg",
        "https://archive.org.evil.example/x.jpg",
        "javascript:alert(1)",
    ],
)
def test_a_manifest_cannot_send_us_to_another_host_or_scheme(
    url: str, tmp_path: Path
) -> None:
    manifest = json.dumps({"images": [{"types": ["Back"], "image": url}]}).encode()
    fetched: list[str] = []

    def fetch(target: str) -> bytes:
        if target.endswith("/release/mbid"):
            return manifest
        fetched.append(target)
        return b"\x89PNG\r\n\x1a\n0000"

    assert cover_art.save_additional_covers(tmp_path, "mbid", fetcher=fetch) == []
    assert fetched == []


@pytest.mark.parametrize(
    "url",
    [
        "http://coverartarchive.org/release/x/1.jpg",
        "https://coverartarchive.org/release/x/1.jpg",
        "https://ia800.us.archive.org/0/items/x/1.jpg",
        "https://archive.org/download/x/1.jpg",
    ],
)
def test_the_archives_own_image_urls_are_still_fetched(
    url: str, tmp_path: Path
) -> None:
    """The floor: a check that refused every URL would pass the test above."""
    manifest = json.dumps({"images": [{"types": ["Back"], "image": url}]}).encode()

    def fetch(target: str) -> bytes:
        return manifest if target.endswith("/release/mbid") else b"\x89PNG\r\n\x1a\n00"

    assert cover_art.save_additional_covers(tmp_path, "mbid", fetcher=fetch) == [
        "back.png"
    ]


def test_a_manifest_naming_thousands_of_pages_fetches_a_bounded_number(
    tmp_path: Path,
) -> None:
    pages = [
        {"types": ["Booklet"], "image": f"https://archive.org/x/{n}.png"}
        for n in range(1000)
    ]
    manifest = json.dumps({"images": pages}).encode()
    fetched: list[str] = []

    def fetch(target: str) -> bytes:
        if target.endswith("/release/mbid"):
            return manifest
        fetched.append(target)
        return b"\x89PNG\r\n\x1a\n00"

    saved = cover_art.save_additional_covers(tmp_path, "mbid", fetcher=fetch)
    assert len(fetched) == cover_art.MAX_EXTRA_IMAGES == len(saved)


# --- The update check ------------------------------------------------------------


@_FAST
@given(payload=_JSON)
def test_ANY_releases_answer_gives_canonical_versions_and_our_own_pages(
    payload: object,
) -> None:
    body = json.dumps(payload)
    for releases in (
        available_releases(fetch=lambda _url: body, channel="beta"),
        [r for r in [latest_release(fetch=lambda _url: body, channel="beta")] if r],
    ):
        for release in releases:
            assert release.version == release.version.strip()
            assert not release.version.lower().startswith("v")
            assert release.url.startswith(RELEASES_PAGE_URL), release.url


@pytest.mark.parametrize(
    ("tag", "url", "expected_version", "expected_url"),
    [
        ("v9.9.9\n", "https://evil.example/", "9.9.9", RELEASES_PAGE_URL),
        (" v9.9.9 ", "javascript:alert(1)", "9.9.9", RELEASES_PAGE_URL),
        ("v9.9.9", "file:///etc/passwd", "9.9.9", RELEASES_PAGE_URL),
        (
            "v9.9.9",
            "https://github.com/rmccann-hub/Platterpus/releases/tag/v9.9.9",
            "9.9.9",
            "https://github.com/rmccann-hub/Platterpus/releases/tag/v9.9.9",
        ),
    ],
)
def test_a_hostile_tag_or_page_url_is_normalised_or_replaced(
    tag: str, url: str, expected_version: str, expected_url: str
) -> None:
    body = json.dumps([{"tag_name": tag, "html_url": url}])
    release = latest_release(fetch=lambda _url: body, channel="beta")
    assert release is not None
    assert (release.version, release.url) == (expected_version, expected_url)


def test_a_partly_recognisable_tag_is_still_skipped() -> None:
    """``vv1.2.3`` is not a tag we publish; it must not become version ``v1.2.3``."""
    body = json.dumps([{"tag_name": "vv1.2.3"}, {"tag_name": "v1.2.2"}])
    release = latest_release(fetch=lambda _url: body, channel="beta")
    assert release is not None and release.version == "1.2.2"
