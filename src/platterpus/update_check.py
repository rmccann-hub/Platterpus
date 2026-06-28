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
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from platterpus.deps.version import parse_version

log = logging.getLogger(__name__)

_REPO_SLUG: str = "rmccann-hub/Platterpus"
RELEASES_API_URL: str = f"https://api.github.com/repos/{_REPO_SLUG}/releases?per_page=5"
RELEASES_PAGE_URL: str = f"https://github.com/{_REPO_SLUG}/releases"
_TIMEOUT_S: float = 6.0


@dataclass(frozen=True)
class ReleaseInfo:
    """The newest published release, as the GUI needs it."""

    version: str  # "0.2.0" — tag with the leading "v" stripped
    url: str  # the release's web page


def _default_fetch(url: str) -> str:
    """GET `url` and return the body text (raises on any failure)."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
        return response.read().decode("utf-8")


def latest_release(fetch: Callable[[str], str] | None = None) -> ReleaseInfo | None:
    """The newest release on GitHub, or None if it can't be determined.

    "Newest" = the first entry of the releases list (the API returns them
    newest-first and includes pre-releases). Returns None on any network,
    JSON, or shape problem — callers show "couldn't check" instead of an
    error dialog.
    """
    try:
        body = (fetch or _default_fetch)(RELEASES_API_URL)
        releases = json.loads(body)
        first = releases[0]
        tag = str(first["tag_name"])
        url = str(first.get("html_url") or RELEASES_PAGE_URL)
    except Exception:  # noqa: BLE001 — any failure means "unknown", never a crash
        log.warning("update check failed", exc_info=True)
        return None
    version = tag[1:] if tag.startswith("v") else tag
    if parse_version(version) is None:
        log.warning("update check: unparseable tag %r", tag)
        return None
    return ReleaseInfo(version=version, url=url)


def is_newer(candidate: str, current: str) -> bool:
    """True if version string `candidate` is strictly newer than `current`.

    Unparseable versions are never "newer" — we'd rather miss an update
    than nag forever on garbage input.
    """
    cand = parse_version(candidate)
    curr = parse_version(current)
    if cand is None or curr is None:
        return False
    # Pad to equal length so (0, 2) compares cleanly against (0, 2, 0).
    width = max(len(cand), len(curr))
    return tuple(cand) + (0,) * (width - len(cand)) > tuple(curr) + (0,) * (
        width - len(curr)
    )
