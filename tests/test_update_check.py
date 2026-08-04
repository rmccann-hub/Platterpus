"""Tests for the update check (update_check.py) — KDD-17b.

The fetcher is injected, so no test touches the network. The contract:
any failure yields None (an update check must never break the app), and
"newer" is decided by parsed version tuples, never string comparison.
"""

from __future__ import annotations

import json

import pytest

import platterpus.update_check as uc
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


def test_latest_release_picks_the_highest_version() -> None:
    """The releases *list* endpoint, not /releases/latest (which hides v0.*).

    Selection is by version, not by list position: the API orders by creation time,
    which diverges from version order the moment a patch on an older line is cut
    after a newer release, and taking position 0 then offers a downgrade.
    """
    info = latest_release(fetch=lambda url: json.dumps(_RELEASES))
    assert info == ReleaseInfo(version="0.3.0", url="https://example.com/v0.3.0")


def test_latest_release_ignores_list_order() -> None:
    """A backport published after a newer release must not be offered as newer."""
    out_of_order = json.dumps(
        [
            # Newest by creation time, older by version — the downgrade trap.
            {"tag_name": "v0.6.4", "html_url": "x/0.6.4"},
            {"tag_name": "v0.7.0", "html_url": "x/0.7.0"},
        ]
    )
    info = latest_release(fetch=lambda url: out_of_order)
    assert info is not None and info.version == "0.7.0"


# --- Channels: stable never offers a pre-release ----------------------------

_MIXED = json.dumps(
    [
        {"tag_name": "v0.6.4b1", "html_url": "x/beta", "prerelease": True},
        {"tag_name": "v0.6.3", "html_url": "x/stable", "prerelease": True},
    ]
)


def test_stable_channel_skips_prereleases() -> None:
    """The default. Being handed a tester build is not the same as an update.

    Note both entries carry GitHub's `prerelease: true` — every `v0.*` tag is
    published that way by policy — so the flag alone cannot separate them and the
    PEP 440 suffix on the version is what decides.
    """
    info = latest_release(fetch=lambda url: _MIXED)
    assert info is not None, (
        "the stable channel found NOTHING — which is what happens if the GitHub "
        "`prerelease` flag is what gates the channel, because every v0.* tag we "
        "publish carries it. This assertion caught exactly that."
    )
    assert info.version == "0.6.3", "a beta reached the stable channel"
    assert info.is_prerelease is False, (
        "0.6.3 is a final version; the GitHub flag on its release says how it was "
        "published, not what it is, and must not turn it into a beta"
    )


def test_beta_channel_offers_the_prerelease() -> None:
    info = latest_release(fetch=lambda url: _MIXED, channel=uc.CHANNEL_BETA)
    assert info is not None
    assert info.version == "0.6.4b1"
    assert info.is_prerelease is True


def test_unknown_channel_falls_back_to_stable() -> None:
    """Failing safe means NARROWING what a user is offered, never widening it."""
    info = latest_release(fetch=lambda url: _MIXED, channel="nightly")
    assert info is not None and info.version == "0.6.3"


def test_stable_channel_with_only_prereleases_is_none() -> None:
    """ "Nothing on your channel" is not an error, and not an offer either."""
    only_betas = json.dumps([{"tag_name": "v0.6.4b1", "html_url": "x"}])
    assert latest_release(fetch=lambda url: only_betas) is None
    beta = latest_release(fetch=lambda url: only_betas, channel=uc.CHANNEL_BETA)
    assert beta is not None and beta.version == "0.6.4b1"


def test_one_unparseable_tag_does_not_hide_the_good_ones() -> None:
    """A single odd tag must not abandon the whole check — it used to.

    `releases[0]` plus a hard `return None` on an unparseable tag meant one
    stray tag at the top of the list reported "couldn't check" while five valid
    releases sat below it.
    """
    mixed = json.dumps(
        [
            {"tag_name": "nightly-build", "html_url": "x/junk"},
            {"tag_name": "v0.6.3", "html_url": "x/good"},
        ]
    )
    info = latest_release(fetch=lambda url: mixed)
    assert info is not None and info.version == "0.6.3"


# --- release_sort_key / is_prerelease_version -------------------------------


def test_prerelease_ordering_is_total_and_correct() -> None:
    """A beta sorts BELOW its own final release and above the previous one.

    This is the property `deps.version.parse_version` cannot express — it reads
    `0.6.4b1` and `0.6.4` as the same (0, 6, 4). Correct for a dependency's
    `--version` output, and a one-way door here: a tester on `0.6.4b1` would never
    be offered `0.6.4`, or `0.6.4b2`.
    """
    ascending = [
        "0.6.3",
        "0.6.4a1",
        "0.6.4a2",
        "0.6.4b1",
        "0.6.4b2",
        "0.6.4rc1",
        "0.6.4",
        "0.6.5",
        "0.7.0",
        "1.0.0",
    ]
    keys = [uc.release_sort_key(v) for v in ascending]
    assert all(k is not None for k in keys)
    assert keys == sorted(keys), f"not monotonically increasing: {keys}"
    # And the pairwise claim the ordering exists for.
    assert is_newer("0.6.4b1", "0.6.3")
    assert is_newer("0.6.4", "0.6.4b1")
    assert is_newer("0.6.4b2", "0.6.4b1")
    assert not is_newer("0.6.4b1", "0.6.4")


@pytest.mark.parametrize(
    "version,expected",
    [
        ("0.6.4", False),
        ("0.6.4b1", True),
        ("0.6.4a3", True),
        ("0.6.4rc1", True),
        ("v0.6.4b1", True),  # tolerates the leading v
        ("0.6.4B1", True),  # and case
        ("nonsense", False),  # unparseable is not a pre-release claim
        ("", False),
    ],
)
def test_is_prerelease_version(version: str, expected: bool) -> None:
    assert uc.is_prerelease_version(version) is expected


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "nightly",
        "0",
        "0.",
        ".6.4",
        "0.6.4.5.6",  # more components than we publish
        "0.6.4beta1",  # not a PEP 440 spelling
        "0.6.4-b1",
        "1" * 40,
        "0.6.4b",  # stage with no number
        "9" * 8 + ".1",  # component past the bound
    ],
)
def test_release_sort_key_refuses_what_we_never_published(bad: str) -> None:
    """None fails safe: an unparseable version is never "newer" (is_newer)."""
    assert uc.release_sort_key(bad) is None
    assert not is_newer(bad, "0.6.3")
    assert not is_newer("0.6.3", bad)


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


# --- _default_fetch: the real network path's read cap (fault-injection) ------
#
# latest_release injects a fetcher in every other test, so _default_fetch (the
# only code that touches urllib) is otherwise unexercised. These monkeypatch
# urllib's urlopen with a fake response — the repo's convention (see
# test_cover_art) rather than a real socket — to prove the read is bounded.


class _FakeResponse:
    """A urlopen()-shaped context manager whose read(n) honours the byte limit,
    so we can prove _default_fetch stops at the cap instead of slurping it all."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, amount: int | None = None) -> bytes:
        if amount is None or amount < 0:
            return self._body
        return self._body[:amount]


def _patch_urlopen(monkeypatch, body: bytes) -> None:
    monkeypatch.setattr(
        uc.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(body),
    )


def test_default_fetch_reads_a_normal_body(monkeypatch) -> None:
    _patch_urlopen(monkeypatch, json.dumps(_RELEASES).encode("utf-8"))
    body = uc._default_fetch(RELEASES_API_URL)
    assert json.loads(body)[0]["tag_name"] == "v0.3.0"


def test_default_fetch_rejects_an_oversized_body(monkeypatch) -> None:
    # A hostile/misbehaving endpoint streaming a huge body must NOT be read
    # unbounded into memory on the worker thread — the read is capped and an
    # over-cap body raises (which latest_release turns into "couldn't check").
    _patch_urlopen(monkeypatch, b"x" * (uc._MAX_BODY_BYTES + 64))
    with pytest.raises(ValueError, match="exceeded"):
        uc._default_fetch(RELEASES_API_URL)


def test_oversized_body_surfaces_as_no_update(monkeypatch) -> None:
    # End-to-end: the cap breach is just another failure — the app says
    # "couldn't check", never crashes or hangs.
    _patch_urlopen(monkeypatch, b"x" * (uc._MAX_BODY_BYTES + 64))
    assert latest_release() is None


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
