"""Cover Art Archive adapter — backend-independent album cover fetching.

Why this exists (2026-06-13, user goal: "good music, good cover image,
good everything"): in the old whipper backend, cover art came from the
ripper itself. With the cyanrip backend the GUI feeds the tags itself and
deliberately skips cyanrip's own MusicBrainz lookup (Critical Rule #5 /
KDD-18 metadata model) — but that lookup was where cyanrip's cover art
would have come from, so cyanrip rips had no art. Same story for the
unknown-album path (no release ID → nothing to fetch art for).

The fix at the right altitude: the GUI fetches the front cover *itself*
from the Cover Art Archive (https://coverartarchive.org) using the
release MBID the user already picked in the release list, then embeds it
into the ripped FLACs via the existing metaflac adapter and/or saves it
as `cover.jpg` next to the tracks. Works identically for both backends.

Design rules:
- **Best-effort, never fatal.** A rip without art is still a perfect rip;
  every failure path here returns None / a human-readable outcome string,
  never an exception to the caller.
- **Stdlib only.** The CAA API is one stable GET endpoint; no client
  library needed (and so nothing new for DEPENDENCIES.md).
- **Injectable fetcher** so tests never touch the network — the same
  hard-learned rule as the update downloader.
"""

from __future__ import annotations

import http.client
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from platterpus.adapters.metaflac import MetaflacAdapter, MetaflacError

log = logging.getLogger(__name__)


@dataclass
class CoverArtResult:
    """Structured outcome of the front-cover fetch/embed (for the rip report).

    Mirrors :class:`~platterpus.adapters.flac_verify.FlacVerifyResult` /
    ``TranscodeResult`` so the report has a real object to serialize instead of
    only a prose line — the biggest previously-unstructured field, and the one
    that answers the "good cover image?" half of the north star. ``found`` is
    True/False once art was attempted; ``reason`` is a short machine code
    (``"ok"``/``"404"``/``"network"``/``"oversize"``/``"not-image"``/
    ``"empty"``/``"write-failed"``/``"no-release"``). ``message`` is the human
    one-liner the log view shows. Best-effort throughout: no field is required.
    """

    mode: str = ""
    found: bool | None = None
    reason: str | None = None
    embedded_count: int = 0
    saved_as: str = ""
    release_id: str = ""
    bytes: int = 0
    format: str = ""
    error: str = ""
    message: str = ""


# `/front` redirects to the original full-resolution "front" image the
# community uploaded for this release — same image Picard shows. (The
# `/front-500` variants are downscaled thumbnails; we want the good one.)
COVER_URL_TEMPLATE: str = "https://coverartarchive.org/release/{mbid}/front"

# The typed-image manifest (JSON): lists every image for a release with its
# `types` (Front / Back / Booklet / …) and full-size `image` URL. Used to grab
# the back cover and booklet scans, which have no single-shot shortcut like
# `/front` for booklets.
MANIFEST_URL_TEMPLATE: str = "https://coverartarchive.org/release/{mbid}"

# The Cover Art Archive asks clients to identify themselves, same
# convention as MusicBrainz proper.
USER_AGENT: str = "platterpus (https://github.com/rmccann-hub/Platterpus)"

_TIMEOUT_S: float = 30.0
# Covers are typically well under 5 MiB; cap the read so a misbehaving
# server can't balloon memory. Anything larger is treated as "no art".
_MAX_BYTES: int = 30 * 1024 * 1024

# A fetcher takes a URL and returns the response body. Swapped out in
# tests; the default uses urllib with the timeout + UA above.
Fetcher = Callable[[str], bytes]


def _default_fetcher(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
        # Read one byte past the cap so the caller can tell "at the cap"
        # from "over the cap".
        return response.read(_MAX_BYTES + 1)


def image_extension(data: bytes) -> str:
    """Return ".jpg"/".png"/".gif" from the image's magic bytes, or "".

    CAA stores JPEG/PNG/GIF (plus PDF for booklets, which `/front` never
    serves). Sniffing the bytes beats trusting a Content-Type header and
    doubles as a sanity check that we got an image at all — an HTML error
    page or truncated body returns "" and is discarded upstream.
    Never raises, for any input.
    """
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return ""


def _fetch_front_cover_detailed(
    release_id: str, fetcher: Fetcher | None = None
) -> tuple[bytes | None, str]:
    """Fetch the front cover, returning ``(data_or_None, reason)``.

    Same behaviour as :func:`fetch_front_cover` but also reports WHY it came back
    empty, so the report can distinguish a genuine "not in the archive" (``404``)
    from a network problem, an oversized body, or a non-image response. ``reason``
    is ``"ok"`` on success. Never raises.
    """
    mbid = (release_id or "").strip()
    if not mbid:
        return None, "no-release"
    # URL-encode the id before interpolating it into the request path. It comes
    # from a MusicBrainz response, so a value containing "/", "?" or "#" (a
    # non-UUID or a tampered response) could otherwise rewrite which resource we
    # fetch; quoting with safe="" turns those into %2F/%3F/%23 so the id can only
    # ever address a (possibly non-existent → 404) release, never escape the path.
    url = COVER_URL_TEMPLATE.format(mbid=urllib.parse.quote(mbid, safe=""))
    fetch = fetcher or _default_fetcher
    try:
        data = fetch(url)
    except urllib.error.HTTPError as exc:
        # A 404 (release simply has no cover) is the common, expected case —
        # distinguish it from any other HTTP status so the report can say which.
        reason = "404" if exc.code == 404 else "network"
        log.info("cover art fetch for %s returned HTTP %s", mbid, exc.code)
        return None, reason
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # urllib.error.URLError is an OSError subclass; timeouts are too.
        # ValueError covers a malformed URL from a weird MBID.
        log.info("cover art fetch failed for %s: %s", mbid, exc)
        return None, "network"
    if not data:
        log.info("cover art for %s was empty — ignoring", mbid)
        return None, "empty"
    if len(data) > _MAX_BYTES:
        log.info("cover art for %s oversized — ignoring", mbid)
        return None, "oversize"
    if not image_extension(data):
        log.info("cover art response for %s is not a known image — ignoring", mbid)
        return None, "not-image"
    return data, "ok"


def fetch_front_cover(release_id: str, fetcher: Fetcher | None = None) -> bytes | None:
    """Return the front-cover image bytes for `release_id`, or None.

    None means "no art" for ANY reason — release not in the archive
    (HTTP 404 is common and normal), network down, oversized or
    unrecognizable response. Callers treat art as a bonus, never a
    requirement, so there is no error to propagate. (See
    :func:`_fetch_front_cover_detailed` for the reason-aware variant the report
    uses.)
    """
    data, _reason = _fetch_front_cover_detailed(release_id, fetcher=fetcher)
    return data


def save_additional_covers(
    rip_dir: Path,
    release_id: str,
    fetcher: Fetcher | None = None,
) -> list[str]:
    """Save the release's BACK cover and BOOKLET scans into ``rip_dir``.

    Reads the Cover Art Archive typed-image manifest for ``release_id`` and
    downloads any Back/Booklet images, saving them as ``back.<ext>`` and
    ``booklet-NN.<ext>`` beside the audio (they can't be embedded in FLAC, so
    they live as files — the front cover is handled by :func:`apply_cover_art`).
    Returns the filenames written (empty when the release has none, or on any
    failure). Best-effort and **never raises** — extra art is a bonus.
    """
    mbid = (release_id or "").strip()
    if not mbid:
        return []
    fetch = fetcher or _default_fetcher
    url = MANIFEST_URL_TEMPLATE.format(mbid=urllib.parse.quote(mbid, safe=""))
    try:
        raw = fetch(url)
        manifest = json.loads(raw)
        images = manifest.get("images", []) if isinstance(manifest, dict) else []
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as e:
        log.info("cover-art manifest fetch failed for %s: %s", mbid, e)
        return []

    saved: list[str] = []
    have_back = False
    booklet_n = 0
    for img in images:
        if not isinstance(img, dict):
            continue
        types = [str(t).lower() for t in (img.get("types") or [])]
        image_url = str(img.get("image") or "")
        if not image_url:
            continue
        if "back" in types and not have_back:
            stem = "back"
        elif "booklet" in types:
            booklet_n += 1
            stem = f"booklet-{booklet_n:02d}"
        else:
            continue
        try:
            data = fetch(image_url)
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError):
            log.info("cover image fetch failed (%s) for %s", stem, mbid)
            continue
        ext = image_extension(data or b"")
        if not data or len(data) > _MAX_BYTES or not ext:
            continue
        target = rip_dir / f"{stem}{ext}"
        try:
            target.write_bytes(data)
        except OSError as exc:
            log.warning("could not write %s: %s", target, exc)
            continue
        saved.append(target.name)
        if stem == "back":
            have_back = True
    if saved:
        log.info("saved %d extra cover image(s) for %s: %s", len(saved), mbid, saved)
    return saved


def apply_local_cover_art(
    rip_dir: Path,
    image_path: Path,
    embed: bool,
    save_file: bool,
    metaflac: MetaflacAdapter,
) -> CoverArtResult:
    """Embed/save a user-supplied local image as the cover for ``rip_dir``.

    The "load cover art from a file" path: instead of fetching from the archive,
    use ``image_path`` (an image the user picked) as the front cover — embed it
    into the FLACs and/or save it as ``cover.<ext>``. Mirrors
    :func:`apply_cover_art` so the rip report gets the same structured outcome;
    ``mode`` is recorded as ``"local"`` so the report shows the art came from a
    file. Never raises — a bad/unreadable file degrades to a populated result.
    """
    result = CoverArtResult(mode="local")
    try:
        data = image_path.read_bytes()
    except OSError as exc:
        log.warning("could not read chosen cover image %s: %s", image_path, exc)
        result.found = False
        result.reason = "read-failed"
        result.error = str(exc)
        result.message = "Cover art: the chosen image could not be read."
        return result
    extension = image_extension(data)
    if not extension:
        result.found = False
        result.reason = "not-image"
        result.message = "Cover art: the chosen file is not a JPEG/PNG/GIF image."
        return result

    result.found = True
    result.reason = "ok"
    result.bytes = len(data)
    result.format = extension.lstrip(".")
    target = rip_dir / f"cover{extension}"
    try:
        target.write_bytes(data)
    except OSError as exc:
        log.warning("could not write cover image %s: %s", target, exc)
        result.reason = "write-failed"
        result.error = str(exc)
        result.message = "Cover art: found, but could not be saved (rip unaffected)."
        return result

    embedded = 0
    if embed:
        for flac_path in sorted(rip_dir.rglob("*.flac")):
            try:
                metaflac.embed_picture(flac_path, target)
                embedded += 1
            except MetaflacError as exc:
                log.warning("cover embed failed for %s: %s", flac_path, exc)
    result.embedded_count = embedded
    if not save_file:
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            log.warning("could not remove temporary cover %s: %s", target, exc)
    else:
        result.saved_as = target.name

    parts: list[str] = []
    if embed:
        parts.append(
            f"embedded in {embedded} track(s)"
            if embedded
            else "chosen, but embedding failed (see the app log)"
        )
    if save_file:
        parts.append(f"saved as {target.name}")
    result.message = (
        "Cover art (from file): " + " and ".join(parts) + "."
        if parts
        else "Cover art: set from file."
    )
    return result


def plan_actions(
    mode: str,
    ripper_fetches_art: bool,
    release_id: str,
) -> tuple[bool, bool]:
    """Decide what the GUI should do about cover art: (embed, save_file).

    `mode` is the Config.cover_art value — vocabulary inherited from the
    old whipper backend, reused backend-independently: "" (off), "embed",
    "file", "complete" (both). `ripper_fetches_art` is True when the ripper
    handles art itself (the historical whipper-with-a-release-ID path, via
    `--cover-art`) — then the GUI stays out of the way. No release ID means
    the disc was never identified, so there is nothing to look up.
    """
    if ripper_fetches_art or not (release_id or "").strip():
        return (False, False)
    embed = mode in ("embed", "complete")
    save_file = mode in ("file", "complete")
    return (embed, save_file)


def apply_cover_art(
    rip_dir: Path,
    release_id: str,
    embed: bool,
    save_file: bool,
    metaflac: MetaflacAdapter,
    fetcher: Fetcher | None = None,
    mode: str = "",
) -> CoverArtResult:
    """Fetch the front cover and embed/save it in `rip_dir`'s FLACs.

    Returns a :class:`CoverArtResult` — a structured outcome the rip report
    serializes, whose ``message`` is the one-line human summary for the log view
    (this runs after the rip, so the status line already shows the fidelity
    verdict — this goes to the log instead). ``mode`` is the Config.cover_art
    value, recorded so the report knows art was *requested*. Never raises:
    per-file embed failures are logged and counted, everything else degrades to
    a populated result.
    """
    result = CoverArtResult(mode=mode, release_id=(release_id or "").strip())
    data, reason = _fetch_front_cover_detailed(release_id, fetcher=fetcher)
    if data is None:
        result.found = False
        result.reason = reason
        result.message = "Cover art: none found for this release (rip unaffected)."
        return result

    result.found = True
    result.reason = "ok"
    result.bytes = len(data)
    # metaflac imports from a file, so the image always lands on disk
    # first; when only embedding was requested it's removed afterwards.
    extension = image_extension(data) or ".jpg"
    result.format = extension.lstrip(".")
    image_path = rip_dir / f"cover{extension}"
    try:
        image_path.write_bytes(data)
    except OSError as exc:
        log.warning("could not write cover image %s: %s", image_path, exc)
        result.reason = "write-failed"
        result.error = str(exc)
        result.message = "Cover art: found, but could not be saved (rip unaffected)."
        return result

    embedded = 0
    flac_files = sorted(rip_dir.rglob("*.flac"))
    if embed:
        for flac_path in flac_files:
            try:
                metaflac.embed_picture(flac_path, image_path)
                embedded += 1
            except MetaflacError as exc:
                log.warning("cover embed failed for %s: %s", flac_path, exc)
    result.embedded_count = embedded

    if not save_file:
        try:
            image_path.unlink(missing_ok=True)
        except OSError as exc:  # purely cosmetic leftover; log and move on
            log.warning("could not remove temporary cover %s: %s", image_path, exc)
    else:
        result.saved_as = image_path.name

    # Build the outcome line from what actually happened.
    parts: list[str] = []
    if embed:
        if embedded:
            parts.append(f"embedded in {embedded} track(s)")
        else:
            parts.append("found, but embedding failed (see the app log)")
    if save_file:
        parts.append(f"saved as {image_path.name}")
    result.message = (
        "Cover art: " + " and ".join(parts) + "." if parts else "Cover art: fetched."
    )
    return result
