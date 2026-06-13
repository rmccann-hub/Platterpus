"""Cover Art Archive adapter — backend-independent album cover fetching.

Why this exists (2026-06-13, user goal: "good music, good cover image,
good everything"): cover art used to be whipper-only. With the cyanrip
backend the GUI feeds the tags itself and deliberately skips cyanrip's
own MusicBrainz lookup (Critical Rule #5 / KDD-18 metadata model) — but
that lookup was where cyanrip's cover art came from, so cyanrip rips had
no art. Same story for whipper's `--unknown` heal path (no release ID on
the whipper side → nothing to fetch art for).

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
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from whipper_gui.adapters.metaflac import MetaflacAdapter, MetaflacError

log = logging.getLogger(__name__)

# `/front` redirects to the original full-resolution "front" image the
# community uploaded for this release — same image Picard shows. (The
# `/front-500` variants are downscaled thumbnails; we want the good one.)
COVER_URL_TEMPLATE: str = "https://coverartarchive.org/release/{mbid}/front"

# The Cover Art Archive asks clients to identify themselves, same
# convention as MusicBrainz proper.
USER_AGENT: str = (
    "whipper-gui (https://github.com/rmccann-hub/Whipper-GUI-Frontend---CD-Rip)"
)

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


def fetch_front_cover(release_id: str, fetcher: Fetcher | None = None) -> bytes | None:
    """Return the front-cover image bytes for `release_id`, or None.

    None means "no art" for ANY reason — release not in the archive
    (HTTP 404 is common and normal), network down, oversized or
    unrecognizable response. Callers treat art as a bonus, never a
    requirement, so there is no error to propagate.
    """
    mbid = (release_id or "").strip()
    if not mbid:
        return None
    url = COVER_URL_TEMPLATE.format(mbid=mbid)
    fetch = fetcher or _default_fetcher
    try:
        data = fetch(url)
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # urllib.error.URLError/HTTPError are OSError subclasses; timeouts
        # are too. ValueError covers a malformed URL from a weird MBID.
        log.info("cover art fetch failed for %s: %s", mbid, exc)
        return None
    if not data or len(data) > _MAX_BYTES:
        log.info("cover art for %s empty or oversized — ignoring", mbid)
        return None
    if not image_extension(data):
        log.info("cover art response for %s is not a known image — ignoring", mbid)
        return None
    return data


def plan_actions(
    mode: str,
    ripper_fetches_art: bool,
    release_id: str,
) -> tuple[bool, bool]:
    """Decide what the GUI should do about cover art: (embed, save_file).

    `mode` is the Config.cover_art value — whipper's vocabulary, reused
    backend-independently: "" (off), "embed", "file", "complete" (both).
    `ripper_fetches_art` is True when the ripper handles art itself
    (whipper with a release ID, via `--cover-art`) — then the GUI stays
    out of the way. No release ID means the disc was never identified,
    so there is nothing to look up.
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
) -> str:
    """Fetch the front cover and embed/save it in `rip_dir`'s FLACs.

    Returns a one-line human-readable outcome for the rip log view (this
    runs after the rip finished, so the status line already shows the
    fidelity verdict — the outcome goes to the log instead). Never raises:
    per-file embed failures are logged and counted, everything else
    degrades to an explanatory message.
    """
    data = fetch_front_cover(release_id, fetcher=fetcher)
    if data is None:
        return "Cover art: none found for this release (rip unaffected)."

    # metaflac imports from a file, so the image always lands on disk
    # first; when only embedding was requested it's removed afterwards.
    extension = image_extension(data) or ".jpg"
    image_path = rip_dir / f"cover{extension}"
    try:
        image_path.write_bytes(data)
    except OSError as exc:
        log.warning("could not write cover image %s: %s", image_path, exc)
        return "Cover art: found, but could not be saved (rip unaffected)."

    embedded = 0
    flac_files = sorted(rip_dir.rglob("*.flac"))
    if embed:
        for flac_path in flac_files:
            try:
                metaflac.embed_picture(flac_path, image_path)
                embedded += 1
            except MetaflacError as exc:
                log.warning("cover embed failed for %s: %s", flac_path, exc)

    if not save_file:
        try:
            image_path.unlink(missing_ok=True)
        except OSError as exc:  # purely cosmetic leftover; log and move on
            log.warning("could not remove temporary cover %s: %s", image_path, exc)

    # Build the outcome line from what actually happened.
    parts: list[str] = []
    if embed:
        if embedded:
            parts.append(f"embedded in {embedded} track(s)")
        else:
            parts.append("found, but embedding failed (see the app log)")
    if save_file:
        parts.append(f"saved as {image_path.name}")
    return "Cover art: " + " and ".join(parts) + "."
