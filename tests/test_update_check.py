"""Tests for the update check (update_check.py) — KDD-17b.

The fetcher is injected, so no test touches the network. The contract:
any failure yields None (an update check must never break the app), and
"newer" is decided by parsed version tuples, never string comparison.
"""

from __future__ import annotations

import json

from platterpus.update_check import (
    RELEASES_API_URL,
    ReleaseInfo,
    is_newer,
    latest_release,
)

_RELEASES = [
    {"tag_name": "v0.3.0", "html_url": "https://example.com/v0.3.0"},
    {"tag_name": "v0.2.0", "html_url": "https://example.com/v0.2.0"},
]


# --- latest_release ---------------------------------------------------------


def test_latest_release_takes_first_entry() -> None:
    """The releases list is newest-first and includes pre-releases — exactly
    why we use it instead of /releases/latest (which hides v0.*)."""
    info = latest_release(fetch=lambda url: json.dumps(_RELEASES))
    assert info == ReleaseInfo(version="0.3.0", url="https://example.com/v0.3.0")


def test_latest_release_queries_the_list_endpoint() -> None:
    seen: list[str] = []

    def fetch(url: str) -> str:
        seen.append(url)
        return json.dumps(_RELEASES)

    latest_release(fetch=fetch)
    assert seen == [RELEASES_API_URL]
    assert "/releases/latest" not in seen[0]


def test_latest_release_none_on_network_error() -> None:
    def boom(url: str) -> str:
        raise OSError("no route to host")

    assert latest_release(fetch=boom) is None


def test_latest_release_none_on_garbage() -> None:
    assert latest_release(fetch=lambda url: "not json") is None
    assert latest_release(fetch=lambda url: "[]") is None  # no releases yet
    assert latest_release(fetch=lambda url: '[{"no_tag": true}]') is None


def test_latest_release_unparseable_tag_is_none() -> None:
    # A tag that isn't a version must not be treated as one.
    bad = json.dumps([{"tag_name": "nightly-build", "html_url": "x"}])
    assert latest_release(fetch=lambda url: bad) is None


# --- is_newer ----------------------------------------------------------------


def test_is_newer_basic_ordering() -> None:
    assert is_newer("0.3.0", "0.2.0") is True
    assert is_newer("0.2.0", "0.2.0") is False
    assert is_newer("0.1.9", "0.2.0") is False
    # Mixed lengths pad cleanly: 0.2 == 0.2.0, 0.2.1 > 0.2.
    assert is_newer("0.2", "0.2.0") is False
    assert is_newer("0.2.1", "0.2") is True
    # The double-digit trap — tuple compare, not string compare.
    assert is_newer("0.10.0", "0.9.0") is True


def test_is_newer_unparseable_is_never_newer() -> None:
    assert is_newer("garbage", "0.2.0") is False
    assert is_newer("0.3.0", "garbage") is False
