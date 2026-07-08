"""Pure helper functions for the main window.

These are deliberately free functions, not methods: they take plain
inputs and return plain outputs with no dependence on the window's
widgets or Qt state, which makes them trivially unit-testable and keeps
``main_window.py`` focused on wiring. Extracted from ``main_window`` as
part of the 2026-06-13 modularization (the window had grown into a
1700-line god-object); ``main_window`` re-exports these names so existing
imports keep working.

Future contributors: any new "transform a string / summarize a parsed
object" logic for the main window belongs here, not as a method on
``MainWindow``. If a helper starts needing widget state, that's a sign it
should be a method instead.
"""

from __future__ import annotations

from pathlib import Path

from platterpus import naming
from platterpus.parsers.rip_log import track_accuraterip_verified

# Audio extensions that mark a folder as already holding a rip (mirrors the
# Critical-Rule-#8 media list + .githooks/pre-commit). Used to detect an
# occupied album folder so an unknown-disc rip never silently overwrites a
# previous disc's archival master.
_AUDIO_EXTS: frozenset[str] = frozenset(
    {
        ".flac", ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus",
        ".wv", ".ape", ".wma", ".aiff", ".aif", ".alac", ".dsf", ".dff",
    }
)  # fmt: skip

# A single path component may be at most NAME_MAX bytes on every mainstream
# Linux filesystem (ext4/btrfs/xfs) — 255 *bytes*, not characters. A long CJK or
# accented title is multi-byte in UTF-8 (≈3 bytes/CJK char), so ~85 characters
# already blows the limit and directory creation would fail. We cap here.
_NAME_MAX_BYTES: int = 255


def _dir_has_audio(directory: Path) -> bool:
    """True if ``directory`` already contains at least one audio file.

    Best-effort and never raises — a missing/unreadable directory reads as
    "no audio" so the caller proceeds normally.
    """
    try:
        return any(
            p.is_file() and p.suffix.lower() in _AUDIO_EXTS for p in directory.iterdir()
        )
    except OSError:
        return False


def unique_album_title(
    output_root: Path, artist: str, title: str, *, max_tries: int = 999
) -> str:
    """Return an album title whose folder isn't already holding a rip.

    An unknown-disc rip names its folder literally from what the user typed
    (``output_root/artist/title``). Two *different* unknown discs both left at the
    defaults ("Unknown Artist" / "Unknown Album") would otherwise land in the SAME
    folder and the second rip would silently overwrite the first — destroying an
    archival master (the never-touch-the-user's-music line). This returns:

    * ``title`` unchanged when the target folder is absent or has no audio, or
    * the first free ``"title (2)"``, ``"title (3)"``… whose folder holds no audio.

    Pure + filesystem-only (no Qt); never raises — on any error it returns the
    original title so the rip proceeds exactly as before. (Known/identified discs
    are deliberately NOT auto-suffixed: re-ripping the same album to the same
    folder is usually intentional, so that case is left for a future confirm.)
    """
    try:
        if not _dir_has_audio(output_root / artist / title):
            return title
        for n in range(2, max_tries + 1):
            candidate = f"{title} ({n})"
            if not _dir_has_audio(output_root / artist / candidate):
                return candidate
        return title
    except OSError:
        return title


def known_album_folder(
    output_root: Path, disc_template: str, artist: str, title: str, year: str
) -> Path:
    """The folder a KNOWN (identified) disc's rip will write into.

    Unlike an unknown disc — whose folder we build literally — a known disc's
    folder is produced by cyanrip rendering the *disc template* from the fetched
    tags. We reproduce that here (via :func:`naming.render_preview`, which mirrors
    cyanrip's token substitution + path sanitisation) and take the rendered
    file's parent directory, so the caller can check whether that folder already
    holds a rip *before* starting.

    Best-effort: exact for ordinary titles; a title with characters cyanrip maps
    differently than the preview may yield a slightly different folder, in which
    case the overwrite check simply won't fire — it can only ever *miss* a
    collision, never invent one (fail-safe toward not blocking the user).
    """
    sample = naming.SampleTrack(
        album_artist=artist,
        track_artist=artist,
        album=title,
        title="",  # the track title never affects the album folder
        track=1,
        track_total=1,
        date=year or "",
    )
    # render_preview appends ".flac"; the album folder is that file's parent.
    rendered = naming.render_preview(disc_template, sample)
    return output_root / Path(rendered).parent


def suffix_album_folder_template(template: str, n: int) -> str:
    """Append ``" (n)"`` to the album-folder segment of a naming template.

    The album folder is the directory immediately containing the track files —
    the second-to-last ``/``-separated segment (the last segment is the base
    filename). We suffix *that* segment only, so the tag tokens (``%d`` etc.)
    stay intact and the FLAC's album tag is unchanged — only the on-disk folder
    gets a ``(2)``. E.g. ``"%A/%d/%t - %n"`` → ``"%A/%d (2)/%t - %n"``.

    A single-segment template (no folder to suffix) is returned unchanged.
    """
    parts = template.split("/")
    if len(parts) < 2:
        return template
    folder_idx = len(parts) - 2
    parts[folder_idx] = f"{parts[folder_idx]} ({n})"
    return "/".join(parts)


def free_album_folder_templates(
    output_root: Path,
    disc_template: str,
    track_template: str,
    artist: str,
    title: str,
    year: str,
    *,
    max_tries: int = 999,
) -> tuple[str, str]:
    """Suffixed (disc_template, track_template) whose album folder is free.

    Used for the "rip to a new folder" choice when a known-disc rip would land
    on a folder that already holds audio: finds the smallest ``(2)``, ``(3)``…
    whose rendered folder has no audio and returns both templates suffixed the
    same way (so the track files and the disc log/cue land together). Falls back
    to the originals if none is free within ``max_tries`` (never raises).
    """
    try:
        for n in range(2, max_tries + 1):
            candidate_disc = suffix_album_folder_template(disc_template, n)
            folder = known_album_folder(
                output_root, candidate_disc, artist, title, year
            )
            if not _dir_has_audio(folder):
                return (
                    candidate_disc,
                    suffix_album_folder_template(track_template, n),
                )
    except OSError:
        pass
    return (disc_template, track_template)


def safe_path_segment(value: str) -> str:
    """Make a user string safe to drop literally into a rip-naming template.

    Used per path component for the unknown-album path (built from what the user
    typed), so it must be robust across locales and to odd/corrupt tag values:

    * strips whitespace, turns ``/`` into ``-`` (it'd create stray subdirs), and
      drops ``%`` (the ripper treats it as a format code);
    * strips NUL and C0 control characters (never valid in a path — a corrupt or
      adversarial tag could carry them);
    * refuses ``.``/``..`` (the filesystem's current/parent-dir names) by
      returning ``""`` — so a disc literally titled ``..`` can't create a no-op
      or traversing directory;
    * caps the result at 255 UTF-8 **bytes** (the filesystem NAME_MAX), truncating
      on a codepoint boundary so a very long international title still yields a
      creatable folder rather than an mkdir failure.

    Returns ``""`` for blank/degenerate input so callers fall back to an
    "Unknown …" placeholder.
    """
    cleaned = (value or "").strip().replace("/", "-").replace("%", "")
    # Drop NUL + C0 controls (< space) and DEL; re-strip in case that exposed
    # edge whitespace.
    cleaned = "".join(ch for ch in cleaned if ch >= " " and ch != "\x7f").strip()
    # "." and ".." are filesystem-special — never let a title become one.
    if cleaned in (".", ".."):
        return ""
    # Cap at NAME_MAX bytes on a codepoint boundary (errors="ignore" drops a
    # partial trailing multi-byte char left by the byte-slice).
    encoded = cleaned.encode("utf-8")
    if len(encoded) > _NAME_MAX_BYTES:
        cleaned = encoded[:_NAME_MAX_BYTES].decode("utf-8", "ignore").strip()
    return cleaned


def friendly_disc_scan_error(error_text: str) -> str:
    """Turn known disc-scan failures into plain language with a next step.

    The headline case (real-user report, 2026-06-10): whipper has cdrdao
    read the disc's table of contents into a temp file; when the drive
    isn't ready yet (disc still spinning up, or scanned the instant it was
    inserted) cdrdao produces nothing and whipper trips over the missing
    file — "FileNotFoundError: ... .cdrdao.read-toc.whipper.task". A retry
    almost always succeeds, so point at the Rescan disc button instead of
    showing a raw traceback line.

    Future contributors: add new ``if <signature>: return <plain message>``
    branches here as real-user reports surface other recoverable scan
    failures. Always fall through to the raw text for anything unrecognized
    — never hide information the user might need to report a bug.
    """
    if "read-toc" in error_text and (
        "FileNotFoundError" in error_text or "No such file" in error_text
    ):
        return (
            "The drive couldn't read the disc's table of contents — this "
            "usually means the disc wasn't ready yet (still spinning up). "
            "Click “Rescan disc” to try again."
        )
    # Cold-container start (real-user report, 2026-06-27): the FIRST whipper
    # call of a session has to start the Distrobox container, which can take
    # longer than the timeout. The timeouts were raised to budget for it, but
    # if one is still hit a retry runs against the now-warm container and
    # almost always succeeds — so point at Rescan rather than the raw text.
    if "timed out" in error_text:
        return (
            "Reading the disc took too long — the first scan after opening "
            "the app has to start the ripping container, which can be slow. "
            "Click “Rescan disc” to try again (it’s much faster the second time)."
        )
    return error_text


def fidelity_summary(rip_log: object) -> str:
    """One-line rip-quality verdict for the status label.

    whipper rips each track twice and records a Test CRC and Copy CRC; a
    match means the two independent reads were bit-identical (a secure,
    archival-quality rip). This surfaces that confidence directly so the
    user doesn't have to open the log to confirm fidelity — addressing the
    "I can't confirm fidelity" feedback. AccurateRip is reported only when
    it actually matched, since it's "not in database" for any disc nobody
    has submitted (e.g. CD-Rs).

    Takes ``object`` and reads fields via ``getattr`` defensively because it
    must accept both the whipper and cyanrip ``RipLog`` shapes (and never
    raise on a partially-parsed log). Future contributors adding a third
    backend: give its log a ``log_creator`` prefix and branch on it here,
    wording the verdict around what that ripper actually verifies — don't
    claim a Test/Copy match a ripper didn't perform.
    """
    tracks = getattr(rip_log, "tracks", ()) or ()
    total = len(tracks)
    if total == 0:
        return "Done."
    # cyanrip's verification model differs from whipper's: one EAC CRC per
    # track plus a paranoia error count, not a test+copy dual read. Word
    # the verdict to match what was actually checked.
    if str(getattr(rip_log, "log_creator", "")).startswith("cyanrip"):
        clean = sum(
            1 for t in tracks if getattr(t, "status", "") == "ripped successfully"
        )
        no_errors = getattr(rip_log, "health_status", "") == "No errors occurred"
        if clean == total and no_errors:
            summary = f"Done — all {total} tracks ripped cleanly, no read errors."
        else:
            summary = (
                f"Done — {clean}/{total} tracks ripped cleanly; "
                f"check the log for the rest."
            )
        clause = _accuraterip_clause(rip_log)
        if clause is None:  # no per-track AR data → legacy summary-string fallback
            ar = getattr(rip_log, "accuraterip_summary", "") or ""
            clause = f" AccurateRip: {ar}." if ar and not ar.startswith("0/") else ""
        return summary + clause + _partial_accurate_clause(rip_log)
    verified = sum(
        1
        for t in tracks
        if getattr(t, "test_crc", "")
        and getattr(t, "test_crc", "") == getattr(t, "copy_crc", "")
    )
    if verified == total:
        summary = f"Done — all {total} tracks read consistently, Test/Copy CRCs match."
    else:
        summary = (
            f"Done — {verified}/{total} tracks CRC-verified; "
            f"check the log for the rest."
        )
    clause = _accuraterip_clause(rip_log)
    if clause is None:  # no per-track AR data → legacy summary-string fallback
        ar = (getattr(rip_log, "accuraterip_summary", "") or "").lower()
        clause = (
            " AccurateRip confirmed." if "exact match" in ar or "found" in ar else ""
        )
    return summary + clause + _partial_accurate_clause(rip_log)


def _partial_accurate_clause(rip_log: object) -> str:
    """A short note when some tracks matched ONLY the +450-frame offset variant.

    cyanrip reports these "partially accurately ripped": the audio is almost
    certainly correct (it matches AccurateRip at the common pressing offset),
    but it's honestly distinct from a plain exact match — so the user
    understands why, say, "12/14 verified" isn't "14/14" without it reading as a
    bad rip. Empty when there were none (the common case). Never raises.
    """
    count = 0
    for track in getattr(rip_log, "tracks", ()) or ():
        if getattr(track, "accuraterip_offset", None) is not None:
            count += 1
    if count == 0:
        return ""
    noun = "track" if count == 1 else "tracks"
    return f" {count} {noun} partially accurate (offset-variant match)."


def _accuraterip_clause(rip_log: object) -> str | None:
    """The ' AccurateRip: …' suffix for the status line, from per-track data.

    Counts verified tracks with the SAME rule the results-pane verdict banner
    uses (:func:`track_accuraterip_verified`, confidence ≥ 1), so the status
    line and the banner can never disagree about how many tracks AccurateRip
    confirmed. Returns:

    * ``None`` — no per-track AccurateRip data was parsed; the caller should
      fall back to the legacy ``accuraterip_summary`` string heuristic.
    * ``""`` — AR data exists but nothing matched (we never append a
      non-confirmation).
    * ``" AccurateRip: …"`` — the verified count, worded like the banner.
    """
    tracks = getattr(rip_log, "tracks", ()) or ()
    has_ar = any(
        getattr(t, "accuraterip_v1", None) is not None
        or getattr(t, "accuraterip_v2", None) is not None
        for t in tracks
    )
    if not has_ar:
        return None
    total = len(tracks)
    verified = sum(1 for t in tracks if track_accuraterip_verified(t))
    if verified == 0:
        return ""
    if verified == total:
        return f" AccurateRip: all {total} verified."
    return f" AccurateRip: {verified}/{total} verified."
