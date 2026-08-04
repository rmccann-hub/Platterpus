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
from dataclasses import dataclass, field
from pathlib import Path

from platterpus import diagnostics, rip_files
from platterpus.adapters.metaflac import MetaflacAdapter, MetaflacError

log = logging.getLogger(__name__)


def _tracks_to_embed_in(rip_dir: Path, rip_log: object | None) -> list[Path]:
    """The FLAC masters **this rip** wrote, in track order.

    Why not ``rip_dir.rglob("*.flac")`` (what this used to be): embedding art
    *mutates* the files it finds, and "the FLACs in the folder" is not "the FLACs
    this rip wrote". One ordinary sequence puts a stranger's file there — cancel a
    rip (partial files remain), fix a track title, re-rip and choose *Replace*: the
    new titles produce new filenames, so the new files land *beside* the old ones.
    A raw glob then embedded this album's cover into the leftovers too and told the
    user "embedded in N track(s)" with N inflated by files this rip never made.

    :mod:`platterpus.rip_files` is the one shared answer to "which files are
    mine?" (CLAUDE.md Critical rule #6) — it reads the rip's own log, and falls
    back to a folder scan (loudly, at WARNING) when there is no usable log, so an
    older rip or a folder a user points us at by hand still gets art. ``rip_log``
    is an already-parsed log when the caller has one, so the log isn't re-read.
    """
    return list(rip_files.rip_master_files(rip_dir, rip_log=rip_log).files)


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
    one-liner the log view shows — reason-specific, so "the release has no art"
    and "we could not reach the archive" never read the same (see
    :func:`no_art_message`). ``error`` carries the dependency's own diagnostic for
    that reason (the exception text, the HTTP status) so it is never swallowed.
    Best-effort throughout: no field is required.
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
    # Extra images saved beside the audio (back.jpg / booklet-NN.jpg) — filled by
    # the caller from :func:`save_additional_covers` so the report records the
    # whole cover-art package, not just the front.
    additional_saved: list[str] = field(default_factory=list)


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
        body: bytes = response.read(_MAX_BYTES + 1)
    return body


def _image_name(extension: str, *, save_file: bool) -> str:
    """The on-disk name for the cover image we are about to write.

    ``metaflac --import-picture-from`` reads from a *file*, so the image always
    lands on disk even when the user only asked to embed it. That scratch write
    used to reuse the canonical library name ``cover.<ext>`` and then delete it
    — so the DEFAULT setting (embed, don't save) silently destroyed a
    ``cover.jpg`` the user had put in the album folder themselves, or one a
    previous save-enabled rip had left there. Re-ripping into an existing folder
    ("Replace") is a real path to that (audit finding, 2026-07-28).

    So the canonical name is used only when we actually intend to keep the file;
    otherwise we write a clearly-temporary sibling that is safe to delete. The
    leading dot keeps it out of the way in a file manager if a crash orphans it.
    """
    return f"cover{extension}" if save_file else f".platterpus-cover-tmp{extension}"


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


# The user-facing sentence for each way the fetch can come back empty.
#
# WHY this table exists (2026-07-31): every one of these used to collapse into
# the single line "Cover art: none found for this release", which told an OFFLINE
# user that the *release* has no art. Those are different facts — "nobody ever
# uploaded a cover for this disc" is final, "we could not reach the archive" is
# a temporary failure that says nothing at all about the release — and the
# project's honesty principle forbids reporting one as the other. The wording is
# in a plain dict (not built inline) so the report line, the log line and the
# tests all read the exact same sentence.
_NO_ART_MESSAGES: dict[str, str] = {
    # The archive answered "I have nothing for this release" — the one case where
    # "none found for this release" is the truth.
    "404": "Cover art: none found for this release in the Cover Art Archive "
    "(rip unaffected).",
    # We never got an answer, so we do NOT know whether art exists. Say so.
    "network": "Cover art: could not reach the Cover Art Archive — art was not "
    "fetched, so this release may still have one (rip unaffected).",
    # No release id: the disc was never identified, so there was nothing to ask
    # about. Again not the same as "the release has no art".
    "no-release": "Cover art: the disc was not identified, so there was no "
    "release to look art up for (rip unaffected).",
    # The server answered, but with something unusable. The art may well exist;
    # what failed was this response.
    "empty": "Cover art: the Cover Art Archive returned an empty image — art was "
    "not applied (rip unaffected).",
    "oversize": "Cover art: the image in the Cover Art Archive is too large to "
    "use — art was not applied (rip unaffected).",
    "not-image": "Cover art: the Cover Art Archive's reply was not a JPEG/PNG/GIF "
    "image — art was not applied (rip unaffected).",
}


def no_art_message(reason: str | None) -> str:
    """The user-facing one-liner for a fetch that produced no art.

    Pure and total: an unknown/None ``reason`` still gets an honest sentence that
    *names the reason code* rather than inventing a fact about the release, so a
    reason added later can never silently regress into "none found". Never raises
    — this is on the best-effort cover-art path, which must never break a rip.
    """
    known = _NO_ART_MESSAGES.get(reason or "")
    if known:
        return known
    code = reason or "unknown"
    return f"Cover art: not applied — {code} (rip unaffected)."


def _fetch_front_cover_detailed(
    release_id: str, fetcher: Fetcher | None = None
) -> tuple[bytes | None, str, str]:
    """Fetch the front cover, returning ``(data_or_None, reason, detail)``.

    Same behaviour as :func:`fetch_front_cover` but also reports WHY it came back
    empty, so the report can distinguish a genuine "not in the archive" (``404``)
    from a network problem, an oversized body, or a non-image response. ``reason``
    is ``"ok"`` on success. ``detail`` is the raw diagnostic we got from the
    dependency (the exception text, the HTTP status, the body size) — kept so it
    can land in the log AND in the report's ``error`` field instead of being
    swallowed; it is ``""`` when there is nothing extra to say. Never raises.
    """
    mbid = (release_id or "").strip()
    if not mbid:
        return None, "no-release", "no release id was chosen for this disc"
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
        # Any OTHER status means the archive did not tell us about the release at
        # all, so it is classed with the network failures, not with "no art".
        reason = "404" if exc.code == 404 else "network"
        log.info("cover art fetch for %s returned HTTP %s", mbid, exc.code)
        return None, reason, f"HTTP {exc.code}"
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # urllib.error.URLError is an OSError subclass; timeouts are too.
        # ValueError covers a malformed URL from a weird MBID.
        log.info("cover art fetch failed for %s: %s", mbid, exc)
        return None, "network", f"{type(exc).__name__}: {exc}"
    if not data:
        log.info("cover art for %s was empty — ignoring", mbid)
        return None, "empty", "the response body was empty"
    if len(data) > _MAX_BYTES:
        log.info("cover art for %s oversized — ignoring", mbid)
        return None, "oversize", f"{len(data)} bytes exceeds the {_MAX_BYTES}-byte cap"
    if not image_extension(data):
        log.info("cover art response for %s is not a known image — ignoring", mbid)
        return None, "not-image", "the response is not a JPEG/PNG/GIF"
    return data, "ok", ""


def fetch_front_cover(release_id: str, fetcher: Fetcher | None = None) -> bytes | None:
    """Return the front-cover image bytes for `release_id`, or None.

    None means "no art" for ANY reason — release not in the archive
    (HTTP 404 is common and normal), network down, oversized or
    unrecognizable response. Callers treat art as a bonus, never a
    requirement, so there is no error to propagate. (See
    :func:`_fetch_front_cover_detailed` for the reason-aware variant the report
    uses.)
    """
    data, _reason, _detail = _fetch_front_cover_detailed(release_id, fetcher=fetcher)
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
    rip_log: object | None = None,
) -> CoverArtResult:
    """Embed/save a user-supplied local image as the cover for ``rip_dir``.

    The "load cover art from a file" path: instead of fetching from the archive,
    use ``image_path`` (an image the user picked) as the front cover — embed it
    into the FLACs and/or save it as ``cover.<ext>``. Mirrors
    :func:`apply_cover_art` so the rip report gets the same structured outcome;
    ``mode`` is recorded as ``"local"`` so the report shows the art came from a
    file. Never raises — a bad/unreadable file degrades to a populated result.

    ``rip_log`` is this rip's already-parsed log when the caller has one; it scopes
    the embed to the files THIS rip wrote (see :func:`_tracks_to_embed_in`).
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
    target = rip_dir / _image_name(extension, save_file=save_file)
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
        # Scoped to this rip's own masters, never a raw folder glob — see
        # _tracks_to_embed_in for the leftover-file hazard that motivates it.
        for flac_path in _tracks_to_embed_in(rip_dir, rip_log):
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
    rip_log: object | None = None,
) -> CoverArtResult:
    """Fetch the front cover and embed/save it in `rip_dir`'s FLACs.

    Returns a :class:`CoverArtResult` — a structured outcome the rip report
    serializes, whose ``message`` is the one-line human summary for the log view
    (this runs after the rip, so the status line already shows the fidelity
    verdict — this goes to the log instead). ``mode`` is the Config.cover_art
    value, recorded so the report knows art was *requested*. ``rip_log`` is this
    rip's already-parsed log when the caller has one; it scopes the embed to the
    files THIS rip wrote (see :func:`_tracks_to_embed_in`). Never raises:
    per-file embed failures are logged and counted, everything else degrades to
    a populated result.
    """
    result = CoverArtResult(mode=mode, release_id=(release_id or "").strip())
    data, reason, detail = _fetch_front_cover_detailed(release_id, fetcher=fetcher)
    if data is None:
        result.found = False
        result.reason = reason
        # Keep the dependency's own diagnostic (exception text / HTTP status) on
        # the result so the rip report carries it too — never swallowed.
        result.error = detail
        # Reason-specific wording: an offline user must NOT be told the release
        # has no art (see _NO_ART_MESSAGES).
        result.message = no_art_message(reason)
        # ...and the same fact goes to the log file, with the machine-readable
        # reason code, so a bug report explains itself without the user having to
        # remember what the GUI said.
        log.warning(
            "cover art not applied for release %r: reason=%s (%s)",
            result.release_id,
            reason,
            detail or "no further detail",
        )
        # Enumerate it too. "good cover image" is a third of the north star, and a
        # missing cover reached the report only as a `cover_art.reason` string that
        # nothing listed as a problem — so a rip with no art looked, in the one list
        # a triager opens, exactly like a rip with art.
        #
        # `info` when the release genuinely has no art (nothing went wrong), and
        # `warning` when we could not find out — the distinction the reason code
        # already carries and no severity reflected.
        diagnostics.record(
            diagnostics.INFO if reason == "no-art" else diagnostics.WARNING,
            "coverart.fetch_failed",
            f"cover art was not applied (reason: {reason}) — {result.message}",
            tool="Cover Art Archive (HTTP)",
            detail=f"release {result.release_id or '(unknown)'}: "
            + (detail or "no further detail"),
            where="adapters.cover_art.fetch_and_apply",
        )
        return result

    result.found = True
    result.reason = "ok"
    result.bytes = len(data)
    # metaflac imports from a file, so the image always lands on disk
    # first; when only embedding was requested it's removed afterwards.
    extension = image_extension(data) or ".jpg"
    result.format = extension.lstrip(".")
    image_path = rip_dir / _image_name(extension, save_file=save_file)
    try:
        image_path.write_bytes(data)
    except OSError as exc:
        log.warning("could not write cover image %s: %s", image_path, exc)
        result.reason = "write-failed"
        result.error = str(exc)
        result.message = "Cover art: found, but could not be saved (rip unaffected)."
        return result

    embedded = 0
    # Scoped to this rip's own masters, never a raw folder glob — see
    # _tracks_to_embed_in for the leftover-file hazard that motivates it.
    flac_files = _tracks_to_embed_in(rip_dir, rip_log)
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
