# SPDX-License-Identifier: GPL-3.0-only
"""Which audio files did **this rip** write? — the one shared answer.

Every post-rip check needs the same list: the CTDB verify (builds the disc TOC
from it), the FLAC integrity verify (decodes each one), the derived-file verify
(pairs each master with its MP3/WavPack/WAV sibling), the SHA256 manifest in the
JSON report, and the standalone ``--ctdb-calibrate`` diagnostic. Each of them
used to answer it for itself with ``rip_dir.glob("*.flac")``.

**"The files in the album folder" is not "the files this rip wrote."** They
differ the moment a folder holds anything else, and one ordinary sequence puts
it there: cancel a rip (leaving partial files, one of them a truncated FLAC),
fix a track title, re-rip and choose *Replace* — the new titles produce new
filenames, so the new files land *beside* the old ones instead of over them.
The glob then returns 2N files and every consumer silently reports on a mixture
of two rips:

* CTDB builds its TOC from 2N tracks, which can never match the disc → a
  spurious "not in database" on a perfect rip.
* FLAC verify decodes the truncated leftover → a ⚠ FAILED line and a downgraded
  verdict for audio that is actually fine.
* Derived-verify's expected count doubles → a complete transcode reads as
  incomplete.
* The checksum manifest fingerprints files this rip never produced, so the
  report's own integrity record describes something else.

The rip does know what it wrote: the ripper's ``.log`` (which lands *in* the
album folder — the album folder is literally defined as that log's parent)
names one file per track. Parsing it back is the authoritative answer, and it is
the same parsed :class:`~platterpus.parsers.rip_log.RipLog` the report and the
verdict are built from, so no surface can disagree with another.

This module is that single subsystem (CLAUDE.md Critical rule #6 — "one
subsystem, not scattered checks"; same reasoning as :mod:`platterpus.verdict`,
which exists because three surfaces computed "verified" three ways). It is
pure, Qt-free and never raises: a caller on a worker thread gets a list back or
an empty one, never an exception.

**It degrades, it does not refuse.** If the folder has no usable log — an older
rip, a log truncated by a crash, a folder a user points the CLI at by hand —
verifying the glob is far better than verifying nothing, so the glob is still
returned. But that is a *reduced-confidence* answer, so it is always recorded:
``RipFileSet.source`` says which answer you got, and the fallback is logged at
WARNING so a bug report carries it (never a silent downgrade).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from platterpus.parity import decode_log_bytes
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.parsers.rip_log import parse_rip_log

log = logging.getLogger(__name__)

# Audio extensions a rip can produce: the FLAC master (always) plus every format
# the transcode adapter derives from it. Lower-cased; compared case-insensitively.
AUDIO_SUFFIXES: frozenset[str] = frozenset({".flac", ".mp3", ".wav", ".wv", ".m4a"})

# The archival master's extension. FLAC is always written first and kept, so the
# master list is the spine every other list hangs off (CLAUDE.md rule #4).
MASTER_SUFFIX: str = ".flac"

# Where a file list came from. Callers surface/log this rather than guessing,
# because "verified 12 files the rip declared" and "verified whatever was lying
# in the folder" are different claims and must never read the same.
SOURCE_RIP_LOG: str = "rip-log"
SOURCE_GLOB: str = "glob"

# A rip log is tens of kilobytes. Anything wildly bigger is not a log we wrote
# (a stray dump, a concatenated monster), and slurping it on a worker thread
# would stall the post-rip checks — skip it rather than read it.
_MAX_LOG_BYTES: int = 8 * 1024 * 1024


@dataclass(frozen=True)
class RipFileSet:
    """The audio files one rip produced, plus how confident we are in the list.

    ``files`` is the answer. The other three fields exist so the *reason* for a
    surprising answer is visible in the app log instead of being reverse-
    engineered from a wrong verdict later:

    * ``source`` — :data:`SOURCE_RIP_LOG` (authoritative: the rip named these) or
      :data:`SOURCE_GLOB` (best-effort: we had to trust the folder).
    * ``excluded`` — audio in the folder that this rip did **not** write. A
      non-empty tuple is the contamination this module exists to keep out.
    * ``missing`` — filenames the log declared that are not on disk. Real
      anomalies (a file deleted or moved between rip and verify), worth logging.
    """

    files: tuple[Path, ...]
    source: str
    excluded: tuple[Path, ...] = ()
    missing: tuple[str, ...] = ()

    @property
    def authoritative(self) -> bool:
        """True when the list came from the rip's own record, not from a glob."""
        return self.source == SOURCE_RIP_LOG


def declared_names(rip_log: object) -> tuple[str, ...]:
    """Basenames of the files a parsed rip log says the rip wrote, in track order.

    Read via ``getattr`` (like :mod:`platterpus.verdict`) so any log-shaped
    object works and a shape change degrades to "no names" instead of raising.

    Two deliberate reductions of the log's own text:

    * **Track order, not lexical order.** The CTDB TOC must be in disc order;
      sorting filenames only *happens* to agree while the naming template
      zero-pads ("02" before "10"). Ordering by the log's track number is
      correct regardless of what the user sets the template to.
    * **Basename only.** The log records a path relative to the configured
      output *root* (``Artist/Album/01 - Track.flac``), while callers hold the
      album folder. Keeping only the last path segment both maps the name into
      that folder and makes the value safe: log text is external input, so a name
      containing ``..`` or an absolute path must not be able to point outside the
      folder we were asked about (CLAUDE.md "validate every input"). The split is
      done on the string rather than via ``Path`` so a Windows-style separator is
      stripped too — POSIX ``Path`` would keep ``a\\b.flac`` as one filename.
    """
    tracks: object = getattr(rip_log, "tracks", ()) or ()
    # A string is iterable but is not a track list; iterating it would silently
    # yield characters. Reject both so a malformed object gives "no names".
    if isinstance(tracks, str | bytes) or not isinstance(tracks, Iterable):
        return ()
    numbered: list[tuple[int, str]] = []
    for track in tracks:
        raw = getattr(track, "filename", "") or ""
        if not isinstance(raw, str):
            continue
        # A NUL can't appear in a real filename and makes Path operations throw
        # on some platforms; drop the entry rather than risk it.
        if not raw.strip() or "\x00" in raw:
            continue
        # Accept both separators: a whipper log written on another platform (or a
        # hand-edited one) can carry backslashes, which POSIX Path treats as part
        # of the name and would leave a directory component embedded in it.
        name = raw.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].strip()
        if not name or name in {".", ".."}:
            continue
        number = getattr(track, "number", 0)
        numbered.append((number if isinstance(number, int) else 0, name))
    numbered.sort(key=lambda pair: pair[0])
    # De-duplicate while keeping order: two log blocks naming one file (an
    # auto-fix re-rip addendum, a re-parsed partial) must not double it up.
    seen: set[str] = set()
    ordered: list[str] = []
    for _number, name in numbered:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return tuple(ordered)


def _log_candidates(rip_dir: Path) -> list[Path]:
    """Rip logs sitting directly in ``rip_dir``, newest first. Never raises.

    Newest-first matters because the folder can legitimately hold more than one
    ``.log``: the ripper's own, the optional ``… (EAC-compatible).log`` companion
    (written *after* it), and possibly a previous rip's. The newest one that
    actually parses into filenames is this rip's record — see
    :func:`_names_from_disk`, which walks this list until one answers.

    Non-recursive: the album folder is the log's parent by construction, so a
    log in a subfolder belongs to some other album (a bonus disc, a nested
    library) and must not describe this one.
    """
    scored: list[tuple[float, Path]] = []
    try:
        candidates = list(rip_dir.glob("*.log"))
    except OSError as exc:
        # A missing or unreadable folder is a legitimate outcome here (the caller
        # then falls back), not an error worth raising into a verify worker.
        log.warning("could not list rip logs in %s: %s", rip_dir, exc)
        return []
    for path in candidates:
        # One guarded stat per candidate: a log can vanish between the glob and
        # the stat (a concurrent cleanup), and the size check needs it anyway.
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > _MAX_LOG_BYTES:
            log.warning("skipping oversized rip log %s (%d bytes)", path, stat.st_size)
            continue
        scored.append((stat.st_mtime, path))
    # Sort by mtime descending, with the path as a tie-break so two logs written
    # in the same coarse mtime tick still give a stable, reproducible order.
    scored.sort(key=lambda pair: (-pair[0], str(pair[1])))
    return [path for _mtime, path in scored]


def _parse_log_file(path: Path) -> object | None:
    """Parse one rip log into a ``RipLog``, or None if it can't be read.

    Sniffs the format rather than trusting the configured backend (a folder can
    hold logs from either ripper), exactly like the finish handler does. The
    parsers themselves never raise, so only the read can fail.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        log.warning("could not read rip log %s: %s", path, exc)
        return None
    # decode_log_bytes handles a BOM / UTF-16 log without ever raising, so a
    # stray byte can't turn "which files are mine?" into an exception.
    text = decode_log_bytes(raw)
    if looks_like_cyanrip_log(text):
        return parse_cyanrip_log(text)
    return parse_rip_log(text)


def _names_from_disk(rip_dir: Path) -> tuple[str, ...]:
    """Filenames declared by the newest log in ``rip_dir`` that names any.

    Walking the candidates (instead of taking the newest outright) is what makes
    the optional EAC-layout companion log harmless: it is newer than the
    ripper's log but neither parser recognises its filename lines, so it yields
    nothing and we move on to the real log rather than falling back to the glob.
    """
    for candidate in _log_candidates(rip_dir):
        parsed = _parse_log_file(candidate)
        if parsed is None:
            continue
        names = declared_names(parsed)
        if names:
            log.debug("rip file list taken from %s (%d files)", candidate, len(names))
            return names
    return ()


def _glob_audio(rip_dir: Path, *, recursive: bool, suffix: str | None) -> list[Path]:
    """Audio files in ``rip_dir`` by extension, sorted. Never raises.

    ``suffix`` of None means "any audio extension". ``recursive`` is per-caller
    because the fallback must reproduce what that caller did before this module
    existed — the verifiers looked at direct children only, the checksum
    manifest walked the tree — and a fallback that quietly changes scope would
    be a second bug hiding inside the fix for the first.
    """
    try:
        walk = rip_dir.rglob("*") if recursive else rip_dir.glob("*")
        found: list[Path] = []
        for path in walk:
            lowered = path.suffix.lower()
            if suffix is not None:
                if lowered != suffix:
                    continue
            elif lowered not in AUDIO_SUFFIXES:
                continue
            # is_file() last: it is the expensive check, and a directory named
            # "x.flac" is rare enough that filtering by extension first is cheaper.
            if path.is_file():
                found.append(path)
        return sorted(found)
    except OSError as exc:
        # A missing/unreadable directory yields no files rather than raising —
        # every caller here is a best-effort post-rip check, never a gate.
        log.warning("could not scan %s for audio files: %s", rip_dir, exc)
        return []


def _resolve_declared(
    rip_dir: Path, names: Sequence[str]
) -> tuple[list[Path], list[str]]:
    """Split declared basenames into ``(files that exist, names that don't)``."""
    present: list[Path] = []
    absent: list[str] = []
    for name in names:
        path = rip_dir / name
        try:
            exists = path.is_file()
        except OSError:
            exists = False
        if exists:
            present.append(path)
        else:
            absent.append(name)
    return present, absent


def rip_master_files(rip_dir: Path, *, rip_log: object | None = None) -> RipFileSet:
    """The FLAC masters **this rip** wrote, in track order.

    ``rip_log`` is an already-parsed log when the caller has one (the finish
    handler parses it anyway, so passing it avoids a second read); when it is
    None — every worker today, which is handed only a folder — the log is read
    back out of the album folder.

    Falls back to a non-recursive ``*.flac`` glob (the pre-fix behaviour) when no
    log names any file that is actually on disk, and logs that it did so.
    """
    names = declared_names(rip_log) if rip_log is not None else ()
    if not names:
        names = _names_from_disk(rip_dir)
    # Keep only masters. A log that names something else entirely (a differently
    # configured ripper writing another format) tells us nothing about the FLACs,
    # so treat it as no answer and fall through to the glob.
    masters = tuple(n for n in names if n.lower().endswith(MASTER_SUFFIX))
    everything = _glob_audio(rip_dir, recursive=False, suffix=MASTER_SUFFIX)

    if masters:
        present, absent = _resolve_declared(rip_dir, masters)
        if present:
            mine = set(present)
            excluded = tuple(p for p in everything if p not in mine)
            _log_scope(rip_dir, len(present), excluded, tuple(absent))
            return RipFileSet(
                files=tuple(present),
                source=SOURCE_RIP_LOG,
                excluded=excluded,
                missing=tuple(absent),
            )
        # The log named files and none of them are here: the folder has moved on
        # (a library move, a manual tidy-up). Its list can't scope anything, so
        # fall back — loudly, because verifying a folder we can't tie to the rip
        # is exactly the reduced-confidence case that must never look normal.
        log.warning(
            "rip log for %s names %d file(s), none of which are on disk — falling "
            "back to a folder scan, so stale files (if any) cannot be excluded",
            rip_dir,
            len(masters),
        )
    else:
        log.warning(
            "no rip log in %s names the files it wrote — falling back to a folder "
            "scan of %d FLAC(s), so leftovers from an earlier rip cannot be "
            "excluded from verification",
            rip_dir,
            len(everything),
        )
    return RipFileSet(files=tuple(everything), source=SOURCE_GLOB)


def rip_audio_files(rip_dir: Path, *, rip_log: object | None = None) -> RipFileSet:
    """Every audio file this rip produced: its FLAC masters and their derived siblings.

    Used by the SHA256 manifest, which must fingerprint the whole of what one rip
    left behind (masters *and* any MP3/WavPack/WAV derived from them) and nothing
    else. Derived files are found by name — the transcode writes ``01 - X.mp3``
    beside ``01 - X.flac`` — so a leftover with a different stem is excluded with
    its master.

    Falls back to the previous behaviour (every audio file anywhere under the
    folder, recursively) when the master list isn't authoritative.
    """
    masters = rip_master_files(rip_dir, rip_log=rip_log)
    if not masters.authoritative:
        # No trustworthy master list → don't pretend: hash everything, exactly as
        # before. rip_master_files has already logged the downgrade. RECURSIVE,
        # because that is what the manifest did before this module existed —
        # narrowing the fallback would silently shrink what the report attests to,
        # which is a second bug wearing the first one's fix as a disguise.
        return RipFileSet(
            files=tuple(_glob_audio(rip_dir, recursive=True, suffix=None)),
            source=SOURCE_GLOB,
        )

    mine: list[Path] = []
    for master in masters.files:
        mine.append(master)
        for suffix in sorted(AUDIO_SUFFIXES - {MASTER_SUFFIX}):
            sibling = master.with_suffix(suffix)
            try:
                exists = sibling.is_file()
            except OSError:
                exists = False
            if exists:
                mine.append(sibling)
    ours = set(mine)
    excluded = tuple(
        p for p in _glob_audio(rip_dir, recursive=True, suffix=None) if p not in ours
    )
    return RipFileSet(
        files=tuple(sorted(mine)),
        source=SOURCE_RIP_LOG,
        excluded=excluded,
        missing=masters.missing,
    )


def _log_scope(
    rip_dir: Path,
    kept: int,
    excluded: tuple[Path, ...],
    missing: tuple[str, ...],
) -> None:
    """Record what the rip's own list included and left out.

    Deliberately noisy about exclusions: a folder holding another rip's audio is
    unusual, and when a user asks why a verify covered 12 files and not 24, this
    line is the answer sitting in their log file.
    """
    if excluded:
        log.warning(
            "%s holds %d audio file(s) this rip did not write — excluding them "
            "from verification: %s",
            rip_dir,
            len(excluded),
            ", ".join(p.name for p in excluded[:10])
            + (", …" if len(excluded) > 10 else ""),
        )
    if missing:
        log.warning(
            "%s: this rip's log names %d file(s) that are not on disk: %s",
            rip_dir,
            len(missing),
            ", ".join(missing[:10]) + (", …" if len(missing) > 10 else ""),
        )
    log.info("verifying %d file(s) this rip wrote in %s", kept, rip_dir)
