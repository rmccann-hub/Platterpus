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

import logging
from pathlib import Path

from platterpus import diagnostics, naming
from platterpus.parsers.rip_log import track_accuraterip_verified

log = logging.getLogger(__name__)

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


# A substituted character is replaced one-for-one, so a real rendering and our
# prediction differ only at substitution points. `unicode` modes write look-alike
# glyphs (all non-ASCII); `simple` modes write `_` (P7b), and `'` for `"`, which is
# left out: we pin `unicode`, which never writes it, so it could only add a spurious
# second candidate, and two withdraw Replace from the prompt. Narrow, so a near-title
# never matches.
_SUBSTITUTION_TARGETS_ASCII: frozenset[str] = frozenset({"_", "-", " "})


def _is_sanitised_rendering_of(predicted: str, actual: str) -> bool:
    """True if ``actual`` could be cyanrip's rendering of ``predicted``.

    Equal strings qualify. Otherwise every differing position must be one where
    a substitution could plausibly have happened: our character is one a
    portable sanitiser replaces (:data:`naming.SUBSTITUTION_SOURCES`) *and*
    theirs looks like a stand-in rather than a different word.

    Deliberately asymmetric — the constraint is on OUR character, not just
    theirs. A rule that only asked "are both sides odd characters" would match
    "Café" against "Cafè", two genuinely different titles.
    """
    if predicted == actual:
        return True
    if len(predicted) != len(actual):
        return False  # substitution is one-for-one; a length change is a different name
    # strict=True is free here — the length check above already guarantees it —
    # and it keeps the guarantee stated where a future edit would break it.
    for ours, theirs in zip(predicted, actual, strict=True):
        if ours == theirs:
            continue
        if ours not in naming.SUBSTITUTION_SOURCES:
            return False
        if theirs.isascii() and theirs not in _SUBSTITUTION_TARGETS_ASCII:
            return False
    return True


def _sanitised_siblings(parent: Path, name: str) -> tuple[Path, ...]:
    """Every folder in ``parent`` that could be a sanitised rendering of ``name``.

    Sorted by name, so the order is the same on every run. Empty when nothing
    matches or on any OS error. Folders only: the caller names these in a prompt
    as places the rip could land, and a file cannot be one.

    **Two matches are an answer, not a refusal** (maintainer ruling, 2026-09-27).
    This used to return nothing on a tie ("refuse rather than guess"), so the guard
    probed a folder that did not exist, found no audio and asked nothing: the
    2026-08-23 silent overwrite by a second route. For a `"` the tie is real, not
    contrived: cyanrip writes `“` or `”` by a parity flag no table can predict
    (P7d), so `a“b` and `a”b` are both this album's and either may be overwritten.
    """
    try:
        return tuple(
            sorted(
                (
                    child
                    for child in parent.iterdir()
                    if _is_sanitised_rendering_of(name, child.name) and child.is_dir()
                ),
                key=lambda child: child.name,
            )
        )
    except OSError:
        return ()


def resolve_sanitised_paths(output_root: Path, relative: Path) -> tuple[Path, ...]:
    """Map a *predicted* rip path onto every folder on disk it could be.

    **Why this exists.** cyanrip renders the naming template itself and swaps
    path-problematic characters in tag values for stand-ins. We predict that
    rendering (:mod:`platterpus.naming`) so the overwrite guard can look before
    a rip starts — and on 2026-08-23 the prediction missed by one character
    (`<` → `‹`, a mapping no table on our side knew about). The guard therefore
    probed a folder that did not exist, found no audio, asked nothing, and a
    completed 14-track archival rip was overwritten by a 2-track one.

    The old code documented that risk and called it fail-safe: *"it can only
    ever miss a collision, never invent one (fail-safe toward not blocking the
    user)"*. **That reasoning is inverted.** Missing the collision IS the
    destructive outcome; inventing one costs a dialog. "Fail-safe" had been
    defined as "never interrupt", for a guard whose whole job is to interrupt
    before the user's music is destroyed.

    So we stop needing the table to be right. Walk the predicted path segment by
    segment; take the literal child when it exists, otherwise EVERY on-disk
    sibling that could be a sanitised rendering of it, otherwise the literal
    name (nothing is there — which is the correct answer for a first rip).

    **Several siblings branch the walk; they do not end it.** Each is followed on
    to the next segment, so a tie at the artist folder still finds the album
    folder under each artist. The result is therefore never empty: one path in
    the ordinary case, and more than one exactly when the disk holds several
    folders the rip could land in — which the overwrite prompt must name, since
    none of them can be told apart from here. It is bounded by what is on disk:
    every extra path is an existing folder, or the literal under one.

    Pure filesystem reads, no Qt: an unreadable folder degrades to the literal
    prediction, i.e. exactly the old behaviour.
    """
    branches: list[Path] = [output_root]
    for segment in relative.parts:
        extended: list[Path] = []
        for current in branches:
            literal = current / segment
            if literal.exists():
                extended.append(literal)
                continue
            extended.extend(_sanitised_siblings(current, segment) or (literal,))
        branches = extended
    # Each branch has its own parent, so no path repeats; dict.fromkeys keeps the
    # walk's order while making that a guarantee rather than an argument.
    return tuple(dict.fromkeys(branches))


def known_album_folders(
    output_root: Path, disc_template: str, artist: str, title: str, year: str
) -> tuple[Path, ...]:
    """Every folder a KNOWN (identified) disc's rip could write into.

    Unlike an unknown disc — whose folder we build literally — a known disc's
    folder is produced by cyanrip rendering the *disc template* from the fetched
    tags. We reproduce that here (via :func:`naming.render_preview`, which mirrors
    cyanrip's token substitution + path sanitisation) and take the rendered
    file's parent directory, so the caller can check whether that folder already
    holds a rip *before* starting.

    The rendered prediction is then resolved against what is actually on disk
    (:func:`resolve_sanitised_paths`), so a character cyanrip maps differently
    from our table still finds the real folder. Before that it did not: the
    prediction missed by one glyph, the overwrite prompt never fired, and a
    14-track archival rip was overwritten without a word (2026-08-23). The
    docstring here used to argue that a miss was the safe direction; it is the
    destructive one.

    **Plural since 2026-09-27**, because the disk can hold more than one folder
    this album could be (`a“b` and `a”b` for a title `a"b`). It returned one path
    then, and on such a tie it returned the literal prediction, a folder that did
    not exist, so the prompt stood down. A caller must look at every path here.

    Never empty. When nothing on disk matches, the literal prediction comes back
    alone, which is the right answer for an album that has not been ripped yet.
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
    return resolve_sanitised_paths(output_root, Path(rendered).parent)


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

    A suffix is free only when EVERY folder it could resolve to is free: with
    `a“b (2)` empty and `a”b (2)` full, cyanrip may pick either, so (2) is taken.
    """
    try:
        for n in range(2, max_tries + 1):
            candidate_disc = suffix_album_folder_template(disc_template, n)
            folders = known_album_folders(
                output_root, candidate_disc, artist, title, year
            )
            if not any(_dir_has_audio(folder) for folder in folders):
                return (
                    candidate_disc,
                    suffix_album_folder_template(track_template, n),
                )
    except OSError as exc:
        # NEVER SILENT. This was a bare `pass`, and the consequence is not cosmetic:
        # falling back to the ORIGINAL templates means the rip lands in the folder
        # the user chose "rip to a new folder" specifically to avoid, and could
        # overwrite audio already there. Failing quietly turned a permissions
        # problem into an apparent product decision.
        log.warning(
            "could not find a free album folder under %s (%s) — falling back to the "
            "ORIGINAL templates, so this rip may land in a folder that already "
            "holds audio",
            output_root,
            exc,
        )
        diagnostics.warning(
            "library.move_failed",
            "could not probe for a free album folder, so this rip uses the original "
            "folder name — it may write into a folder that already contains audio",
            detail=f"{output_root}: {exc}",
            where="ui.main_window_helpers.free_album_folder_templates",
        )
    return (disc_template, track_template)


def ambiguous_overwrite_text(
    candidates: tuple[Path, ...], occupied: frozenset[Path]
) -> str:
    """The overwrite prompt's wording when more than one folder could be the target.

    Names EVERY candidate, each marked with whether it already holds a rip, so the
    user sees there is more than one and which of them this rip could overwrite.
    The names come from MusicBrainz tags, so the box showing this must be
    PlainText (Critical rule #12); nothing here is markup.
    """
    lines = [
        f"This album could be ripped into any of these {len(candidates)} folders. "
        "Their names differ only where cyanrip swaps a character for a look-alike, "
        "so Platterpus cannot tell which one it will write into:",
        "",
    ]
    lines += [
        f"• {folder} — {'⚠ already holds a rip' if folder in occupied else 'no rip'}"
        for folder in candidates
    ]
    lines += [
        "",
        "Ripping into a folder that holds a rip overwrites its files."
        if occupied
        else "Neither holds a rip yet, but this rip would land in one of them "
        "with no way to choose which.",
    ]
    return "\n".join(lines)


def safe_path_segment(value: str) -> str:
    """Make a user string safe to drop literally into a rip-naming template.

    Used per path component for the unknown-album path (built from what the user
    typed), so it must be robust across locales and to odd/corrupt tag values:

    * strips whitespace, turns ``/`` into ``-`` (it'd create stray subdirs), and
      drops ``%`` (the ripper treats it as a format code);
    * strips NUL, C0 control characters and lone surrogates (never valid in a
      path — a corrupt or adversarial tag could carry them);
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
    # Drop NUL + C0 controls (< space), DEL and lone surrogates (no UTF-8 name can
    # hold one; the encode below raised on it); re-strip for exposed whitespace.
    cleaned = "".join(
        ch
        for ch in cleaned
        if ch >= " " and ch != "\x7f" and not "\ud800" <= ch <= "\udfff"
    ).strip()
    # Cap at NAME_MAX bytes on a codepoint boundary (errors="ignore" drops a
    # partial trailing multi-byte char left by the byte-slice).
    encoded = cleaned.encode("utf-8")
    if len(encoded) > _NAME_MAX_BYTES:
        cleaned = encoded[:_NAME_MAX_BYTES].decode("utf-8", "ignore").strip()
    # "." and ".." are filesystem-special — never let a title become one. AFTER
    # the cap, because the cap strips what it cuts to: ".." + 253 spaces + "x"
    # used to come back as "..".
    if cleaned in (".", ".."):
        return ""
    return cleaned


def friendly_disc_scan_error(error_text: str) -> str:
    """Turn known disc-scan failures into plain language with a next step.

    The headline case (real-user report, 2026-06-10, on the ripper older
    versions used): it had cdrdao read the disc's table of contents into a
    temp file; when the drive isn't ready yet (disc still spinning up, or
    scanned the instant it was inserted) cdrdao produces nothing and the
    ripper tripped over the missing file — a ``FileNotFoundError`` naming
    its ``….cdrdao.read-toc.….task`` temp file. A retry almost always
    succeeds, so point at the Rescan disc button instead of showing a raw
    traceback line.

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
    # Cold-container start (real-user report, 2026-06-27): the FIRST ripper
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


def fidelity_summary(
    rip_log: object, *, expected_track_total: int | None = None
) -> str:
    """One-line rip-quality verdict for the status label.

    ``expected_track_total`` is how many tracks the rip was ASKED to produce
    (:func:`platterpus.verdict.expected_track_total` — the disc's count, or the
    user's Rip? selection when they chose a subset). Keyword-only and defaulted so
    every existing caller and test keeps working; supplying it is what stops this
    line disagreeing with the trust banner beside it about how complete the rip is.

    A legacy-format log records a Test CRC and a Copy CRC per track (the
    ripper that wrote it read each track twice); a match means the two
    independent reads were bit-identical (a secure, archival-quality rip).
    A cyanrip log is worded around what cyanrip checks instead (below).
    This surfaces that confidence directly so the user doesn't have to open
    the log to confirm fidelity — addressing the
    "I can't confirm fidelity" feedback. AccurateRip is reported only when
    it actually matched, since it's "not in database" for any disc nobody
    has submitted (e.g. CD-Rs).

    Takes ``object`` and reads fields via ``getattr`` defensively because it
    must accept both the cyanrip and legacy-format ``RipLog`` shapes (and never
    raise on a partially-parsed log). Future contributors adding a third
    backend: give its log a ``log_creator`` prefix and branch on it here,
    wording the verdict around what that ripper actually verifies — don't
    claim a Test/Copy match a ripper didn't perform.
    """
    tracks = getattr(rip_log, "tracks", ()) or ()
    # `expected_track_total` is the number of tracks this rip was ASKED for; the
    # log only contains the ones it got to. Using the log's own count made a
    # cancelled 2-of-14 rip announce "all 2 tracks ripped cleanly" — the same
    # wrong-denominator bug the trust banner had, on the surface that also feeds
    # the desktop notification. The banner was given this fact and this function
    # was not, six lines apart, which is how a fix reaches three surfaces out of
    # four (audit finding, 2026-07-30).
    total = expected_track_total if expected_track_total else len(tracks)
    if not tracks:
        return "Done."
    # cyanrip's verification model differs from the legacy format's: one EAC
    # CRC per track plus a paranoia error count, not a test+copy dual read.
    # Word the verdict to match what was actually checked.
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
                # Name the TAB, not "the log". This means the rip's own log, which is
                # on screen right now behind a button — naming the place beats naming
                # a file the user would have to go find.
                f"see the Rip log tab for the rest."
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
            f"see the Rip log tab for the rest."
        )
    clause = _accuraterip_clause(rip_log)
    if clause is None:  # no per-track AR data → legacy summary-string fallback
        ar = (getattr(rip_log, "accuraterip_summary", "") or "").lower()
        clause = (
            " AccurateRip confirmed." if "exact match" in ar or "found" in ar else ""
        )
    return summary + clause + _partial_accurate_clause(rip_log)


def _partial_accurate_clause(rip_log: object) -> str:
    """A short note when on some tracks only one frame matched AccurateRip.

    cyanrip reports these as "partially accurately ripped" up to +platterpus.16,
    and as "one frame only" from .17. This docstring used to
    say the audio was "almost certainly correct (it matches AccurateRip at the
    common pressing offset)", and on 2026-09-24 one such track held wrong audio:
    one frame matching verifies one frame (see :mod:`platterpus.one_frame_match`).
    So the note says what matched and that the rest is unverified, which is also
    why "12/14 verified" is not "14/14". Empty when there were none (the common
    case). Never raises.

    Uses the shared :func:`~platterpus.verdict.track_accuraterip_partial`, which
    requires an actual *match* at the variant offset. Counting the mere presence
    of the "Accurip 450:" line (as this did) reported a partial for a track whose
    variant lookup said "not found" (audit finding, 2026-07-28).
    """
    from platterpus.verdict import track_accuraterip_partial

    count = 0
    for track in getattr(rip_log, "tracks", ()) or ():
        if track_accuraterip_partial(track):
            count += 1
    if count == 0:
        return ""
    noun = "track" if count == 1 else "tracks"
    return (
        f" On {count} {noun}, only one frame matched AccurateRip (the rest unverified)."
    )


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
