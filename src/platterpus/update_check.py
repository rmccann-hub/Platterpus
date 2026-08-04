"""Update check — "is a newer release published?" (KDD-17b).

The *delivery* of updates is the standard AppImage mechanism: the build
embeds zsync update-information (see ``build/build_appimage.sh``), so any
AppImageUpdate-compatible tool can fetch the delta and verify it. This
module only answers the cheap question — *is there anything newer?* — by
asking the GitHub releases API, so the Help menu can say "you're up to
date" or point at the new release. Per KDD-17 we deliberately do NOT
download update payloads ourselves (that would hand-roll AppImageUpdate,
adding code + supply-chain surface for nothing).

Uses the releases *list* endpoint, not ``/releases/latest`` — the latter
excludes pre-releases, and every ``v0.*`` release is one (the same lesson
install.sh learned). Network access is behind an injectable fetcher and
every failure path returns None: an update check must never break the app.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

log = logging.getLogger(__name__)

#: Update channels. ``stable`` never offers a pre-release; ``beta`` offers whichever
#: is newest, pre-release or not. Strings rather than an enum so the value round-trips
#: through the TOML config unchanged and reads the same in a bug report.
CHANNEL_STABLE: Final[str] = "stable"
CHANNEL_BETA: Final[str] = "beta"
CHANNELS: Final[tuple[str, ...]] = (CHANNEL_STABLE, CHANNEL_BETA)

_REPO_SLUG: str = "rmccann-hub/Platterpus"
RELEASES_API_URL: str = f"https://api.github.com/repos/{_REPO_SLUG}/releases?per_page=5"
RELEASES_PAGE_URL: str = f"https://github.com/{_REPO_SLUG}/releases"
_TIMEOUT_S: float = 6.0
# The releases-list JSON is a few KB in practice. Cap the read so a misbehaving
# or hostile endpoint can't stream an unbounded body into memory on the worker
# thread — same defensive bound the cover-art / CTDB / updater fetchers all use.
# This is over-HTTPS to api.github.com, so it's belt-and-braces, not the front
# line — but an unbounded read has no upside, and the cap keeps the fetchers
# consistent (nothing reads a network body without a ceiling).
_MAX_BODY_BYTES: int = 4 * 1024 * 1024


# Our OWN release tags, which are PEP 440 — `0.6.4`, `0.6.4b1`, `0.6.5rc2`. This is
# deliberately NOT `deps.version.parse_version`: that one reads a *dependency tool's*
# `--version` output, where a trailing `b1` is noise to be ignored, and it returns
# (0, 6, 4) for both `0.6.4` and `0.6.4b1`. Correct there; catastrophic here, because
# it makes a beta and its own final release compare EQUAL — so a tester on `0.6.4b1`
# is never offered `0.6.4`, and `0.6.4b2` is never offered either. The beta channel
# would have shipped as a one-way door.
#
# Bounded quantifiers for the same reason `deps.version` bounds its own: this parses
# a tag string from a network response.
_RELEASE_VERSION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*v?(?P<major>\d{1,6})\.(?P<minor>\d{1,6})(?:\.(?P<patch>\d{1,6}))?"
    r"(?:(?P<stage>a|b|rc)(?P<pre>\d{1,6}))?\s*$",
    re.IGNORECASE,
)

# Ordering of the pre-release stages, with a *final* release ranking above all of
# them. `_FINAL_RANK` must stay the largest value here — that single fact is what
# makes `0.6.4 > 0.6.4rc1`.
_STAGE_RANK: Final[dict[str, int]] = {"a": 0, "b": 1, "rc": 2}
_FINAL_RANK: Final[int] = 3


def release_sort_key(version: str) -> tuple[int, int, int, int, int] | None:
    """A totally-ordered key for one of *our* release versions, or ``None``.

    ``(major, minor, patch, stage_rank, pre_number)``. A final release gets
    ``stage_rank`` :data:`_FINAL_RANK` and ``pre_number`` 0, so:

        0.6.3  <  0.6.4b1  <  0.6.4b2  <  0.6.4rc1  <  0.6.4  <  0.6.5

    Returns ``None`` for anything that is not a version we could have published —
    including a *partly* recognisable string. An unparseable version is never
    "newer" (see :func:`is_newer`), so ``None`` fails safe: we would rather miss an
    update than nag forever, or worse, offer a downgrade.
    """
    match = _RELEASE_VERSION_RE.match(version or "")
    if match is None:
        return None
    stage = (match.group("stage") or "").lower()
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch") or 0),
        _STAGE_RANK.get(stage, _FINAL_RANK),
        int(match.group("pre") or 0),
    )


def is_prerelease_version(version: str) -> bool:
    """True when ``version`` carries a PEP 440 pre-release suffix (``b1``, ``rc2``).

    **Read off the version string, and deliberately NOT off the API's ``prerelease``
    flag.** This project marks *every* ``v0.*`` tag as a GitHub pre-release — see
    `release.yml` — so for the entire 0.x line that flag is a constant and carries
    no information at all. Gating the stable channel on it would have left stable
    users with **nothing on their channel**, ever: `0.6.3` and `0.6.4b1` are both
    flagged, and both would have been skipped. The first version of this module did
    exactly that, and `test_stable_channel_skips_prereleases` caught it by using a
    fixture where both entries carry the flag — which is not a contrived case, it is
    every release we have ever cut.

    The flag describes how a release was *published*; this describes what the
    artifact *is*. The user's warning is about the artifact.
    """
    key = release_sort_key(version)
    return key is not None and key[3] != _FINAL_RANK


@dataclass(frozen=True)
class ReleaseInfo:
    """The newest published release, as the GUI needs it."""

    version: str  # "0.2.0" — tag with the leading "v" stripped
    url: str  # the release's web page
    #: Whether this is a pre-release — GitHub's flag OR a PEP 440 suffix on the
    #: version. Carried so the offer can WARN rather than silently hand a tester
    #: build to someone who only wanted an update.
    is_prerelease: bool = False


def _default_fetch(url: str) -> str:
    """GET `url` and return the body text (raises on any failure).

    Reads at most ``_MAX_BODY_BYTES`` (one byte past, to distinguish "at the cap"
    from "over it") so an oversized response can't exhaust memory; an over-cap
    body raises, which ``latest_release`` turns into "couldn't check" like any
    other failure.
    """
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
        data: bytes = response.read(_MAX_BODY_BYTES + 1)
    if len(data) > _MAX_BODY_BYTES:
        raise ValueError(
            f"update check response exceeded {_MAX_BODY_BYTES} bytes — refusing it"
        )
    return data.decode("utf-8")


def latest_release(
    fetch: Callable[[str], str] | None = None,
    channel: str = CHANNEL_STABLE,
) -> ReleaseInfo | None:
    """The newest release on the given channel, or None if it can't be determined.

    ``channel`` is :data:`CHANNEL_STABLE` (skip every pre-release) or
    :data:`CHANNEL_BETA` (consider all of them). Anything else is treated as
    ``stable`` and logged — an unrecognised channel must not silently widen what a
    user is offered.

    **Newest by version, not by position.** This used to take ``releases[0]``,
    trusting the API's newest-first ordering, which is by *creation time*. Those
    orders diverge the moment a patch on an older line is cut after a newer release
    — `0.6.5` published, then `0.6.4.1` backported — and taking position 0 then
    offers a downgrade. Sorting by :func:`release_sort_key` makes the answer depend
    on the versions rather than on publication history.

    Returns None on any network, JSON, or shape problem — callers show "couldn't
    check" instead of an error dialog.
    """
    if channel not in CHANNELS:
        log.warning(
            "update check: unknown channel %r — treating as %r", channel, CHANNEL_STABLE
        )
        channel = CHANNEL_STABLE
    try:
        body = (fetch or _default_fetch)(RELEASES_API_URL)
        releases = json.loads(body)
    except Exception:  # noqa: BLE001 — any failure means "unknown", never a crash
        log.warning("update check failed", exc_info=True)
        return None

    candidates: list[tuple[tuple[int, int, int, int, int], ReleaseInfo]] = []
    try:
        for entry in releases:
            tag = str(entry["tag_name"])
            version = tag[1:] if tag.startswith("v") else tag
            key = release_sort_key(version)
            if key is None:
                # Not a shape we publish. Skip the entry rather than abandoning the
                # whole check: one odd tag in the list must not hide five good ones.
                log.warning("update check: skipping unparseable tag %r", tag)
                continue
            # The VERSION decides, not the API's `prerelease` flag — see
            # `is_prerelease_version` for why that flag is uninformative here.
            pre = is_prerelease_version(version)
            if pre and channel != CHANNEL_BETA:
                continue
            url = str(entry.get("html_url") or RELEASES_PAGE_URL)
            candidates.append(
                (key, ReleaseInfo(version=version, url=url, is_prerelease=pre))
            )
    except Exception:  # noqa: BLE001 — a malformed entry is "unknown", never a crash
        log.warning("update check: malformed releases payload", exc_info=True)
        return None

    if not candidates:
        log.info("update check: no releases on the %r channel", channel)
        return None
    return max(candidates, key=lambda pair: pair[0])[1]


def is_newer(candidate: str, current: str) -> bool:
    """True if version string `candidate` is strictly newer than `current`.

    Pre-release aware: ``0.6.4b1`` is newer than ``0.6.3`` and OLDER than ``0.6.4``.
    Unparseable versions are never "newer" — we'd rather miss an update than nag
    forever on garbage input, or offer a downgrade.
    """
    cand = release_sort_key(candidate)
    curr = release_sort_key(current)
    if cand is None or curr is None:
        return False
    return cand > curr
