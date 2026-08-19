"""One file to send: the post-rip evidence bundle.

**Why this module exists.** Every rip already leaves a complete paper trail —
the app log, cyanrip's own log, the EAC-compatible export, the `.cue`, the
`.platterpus.json` report, the addendum — and until now the person reporting a
problem had to *find* those files, decide which mattered, select them, compress
them and upload the result. The maintainer's words (2026-08-19): *"why make me
bundle it into one compressed file? … this should be on a successful rip, a
partial, a canceled, a failed, etc. so i only need to upload 1 file here."*

That is the same rule `CLAUDE.md` already states about handing back instruction
files: **every manual step in a reporting procedure is a thing the software was
supposed to do.** `rig_session.sh` had already learned it and ends by building
one archive; an ordinary rip had not.

Four properties, each of which is a rule this project has paid for:

1. **It runs on EVERY outcome, not just the good one.** Success, partial,
   cancelled and failed all produce a bundle. The failed and cancelled rips are
   the ones somebody actually needs to send, and they are exactly the paths a
   "write the report when we finish nicely" design skips.

2. **No audio, ever, by allowlist.** Critical rule #8 forbids copyrighted media
   leaving the machine in something we generate. The filter here is an
   **allowlist of extensions**, not a denylist of audio ones, because a denylist
   is wrong the first time a format nobody listed appears — it fails *open*, and
   the failure is silent. Anything not on the list is excluded and **counted in
   the manifest**, so an exclusion is visible rather than invisible.

3. **Every omission is named.** A file that was missing, unreadable, too big or
   the wrong type gets a manifest row saying so. *A silent truncation reads as
   completeness* (`CLAUDE.md`) — a bundle that quietly contains eight of eleven
   artifacts looks exactly like a complete one, and the reader draws conclusions
   from the absence.

4. **It never raises.** A bundle is a convenience wrapped around a rip that has
   already finished; a bug in it must not surface as a crash after a successful
   rip. Failures come back in :attr:`BundleResult.error` for the caller to log
   and show.

This module is deliberately **Qt-free and side-effect-light** so it is testable
without a GUI: the caller passes in whatever text it wants embedded (the
diagnostics blob, for instance) rather than this module reaching into the UI for
it. Threading is the caller's job too — see
``main_window_rip._write_evidence_bundle_async``, which runs it on a daemon
thread because gzipping a 4 MB log is not a GUI-thread operation.
"""

from __future__ import annotations

import hashlib
import io
import logging
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

#: Extensions that may enter a bundle. **Allowlist, not denylist** — see the
#: module docstring. Everything here is text or structured text; none of it can
#: carry audio. `.txt` covers the app log and its rotations, `.log` the ripper's
#: own and the EAC export, `.json` the report and the argv probe, `.cue` the cue
#: sheet, `.md5`/`.sha256` the checksum sidecars, `.toml` the config.
ALLOWED_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".txt", ".log", ".json", ".cue", ".md5", ".sha256", ".toml", ".md"}
)

#: Extra types admitted from **directories the caller names explicitly**, and
#: from nowhere else. Today that means the test-script run folder, whose PNGs are
#: screenshots *this program took of its own window*.
#:
#: **Why this is not simply added to the list above.** An album folder routinely
#: contains `cover.jpg` / `folder.png` — record-label artwork, which is exactly
#: the copyrighted media Critical rule #8 is about. Widening the global allowlist
#: to carry our own screenshots would sweep that in as a side effect, silently,
#: on every rip. So the widening is scoped to the directories a caller opts in,
#: and the album folder is never one of them.
EXTRA_DIR_SUFFIXES: Final[frozenset[str]] = ALLOWED_SUFFIXES | frozenset({".png"})

#: A rotated log is `log.txt.1`, `log.txt.2`… — a numeric suffix, so the check
#: above sees `.1` and would refuse it. Names matching this are admitted on the
#: strength of their *stem* instead.
_ROTATION_STEMS: Final[tuple[str, ...]] = ("log.txt",)

#: Per-file cap before head/tail elision kicks in. Generous, because gzip does
#: most of the work; the cap exists to stop one pathological file (a runaway
#: debug log) making the bundle unsendable.
MAX_FILE_BYTES: Final[int] = 16 * 1024 * 1024

#: How much of an over-cap file to keep from each end. **Both ends**, because a
#: tool's fatal message is the last thing it prints and a head-only cap drops
#: precisely the line that explains the failure (`CLAUDE.md`).
_KEEP_HEAD_BYTES: Final[int] = 6 * 1024 * 1024
_KEEP_TAIL_BYTES: Final[int] = 6 * 1024 * 1024


@dataclass(frozen=True)
class BundleEntry:
    """One file the bundle considered, and what became of it."""

    name: str
    source: str
    included: bool
    reason: str
    bytes_written: int = 0


@dataclass
class BundleResult:
    """What :func:`build_bundle` produced. Never an exception — always this."""

    path: Path | None = None
    entries: list[BundleEntry] = field(default_factory=list)
    error: str = ""

    @property
    def included(self) -> list[BundleEntry]:
        return [e for e in self.entries if e.included]

    @property
    def skipped(self) -> list[BundleEntry]:
        return [e for e in self.entries if not e.included]

    @property
    def ok(self) -> bool:
        return self.path is not None and not self.error


def bundle_filename(stamp: str) -> str:
    """The archive's name, in the cross-machine artifact spelling.

    Lowercase ASCII letters and digits only — no hyphens, no underscores, no
    case (`CLAUDE.md` → *Artifact filenames that cross machines*). A rig run was
    lost to exactly this: the same artifact was `round08joint.txt` on one disk
    and `round-08-joint.txt` in the instructions written for it, and a path is an
    exact-match string. This file is going to be named in a chat message and
    typed into a file dialog, so it gets the same treatment.

    `stamp` is supplied by the caller rather than read from the clock here, so a
    test can pin the name.
    """
    cleaned = "".join(ch for ch in stamp.lower() if ch.isalnum())
    return f"platterpusbundle{cleaned}.tar.gz"


def _is_allowed(
    path: Path, permitted: frozenset[str] = ALLOWED_SUFFIXES
) -> tuple[bool, str]:
    """May this file enter the bundle? Returns (verdict, reason-if-not).

    `permitted` defaults to the strict text-only set. The caller widens it ONLY
    for directories it named explicitly (see `EXTRA_DIR_SUFFIXES`); the album
    folder is always judged by the default, because that is where record-label
    artwork lives.
    """
    if path.suffix.lower() in permitted:
        return True, ""
    # `log.txt.3` — a rotation. Its suffix is `.3`; judge it by the stem.
    for stem in _ROTATION_STEMS:
        if path.name.startswith(stem + ".") and path.name[len(stem) + 1 :].isdigit():
            return True, ""
    return False, (
        f"excluded: {path.suffix or '(no extension)'!r} is not one of the types "
        "this part of the bundle may contain (audio and everything else is "
        "refused by allowlist — Critical rule #8)"
    )


def _read_bounded(path: Path) -> tuple[bytes, str]:
    """Read a file, keeping head AND tail if it is over the cap.

    The elision is marked inline with the byte count it dropped, so a reader can
    tell a bounded file from a complete one. A cap that hides itself turns a
    partial artifact into a confident one.
    """
    size = path.stat().st_size
    if size <= MAX_FILE_BYTES:
        return path.read_bytes(), ""
    with path.open("rb") as handle:
        head = handle.read(_KEEP_HEAD_BYTES)
        handle.seek(size - _KEEP_TAIL_BYTES)
        tail = handle.read(_KEEP_TAIL_BYTES)
    dropped = size - len(head) - len(tail)
    marker = (
        f"\n\n===== platterpus: {dropped} byte(s) elided from the middle of a "
        f"{size}-byte file; the first {len(head)} and last {len(tail)} bytes are "
        "kept =====\n\n"
    ).encode()
    note = f"bounded: {dropped} byte(s) elided from the middle (file was {size})"
    return head + marker + tail, note


def _collect(
    album_dir: Path | None,
    log_dir: Path,
    extra_dirs: Mapping[str, Path] | None = None,
) -> list[tuple[str, Path, frozenset[str]]]:
    """Decide what to look for. Returns (archive name, source, allowed suffixes).

    The app log comes first because it is the artifact that exists for *every*
    outcome — including the ones where the rip produced no album folder at all,
    which are precisely the failures worth sending.

    The third element travels with each candidate rather than being decided at
    the point of the check, so a file's permission is fixed by *where it came
    from*. That is what stops the widened image rule leaking onto the album
    folder: there is no code path where an album file is judged by anything but
    the strict set.
    """
    found: list[tuple[str, Path, frozenset[str]]] = []
    if log_dir.is_dir():
        for entry in sorted(log_dir.iterdir()):
            if entry.is_file():
                found.append((f"applog/{entry.name}", entry, ALLOWED_SUFFIXES))
    if album_dir is not None and album_dir.is_dir():
        for entry in sorted(album_dir.rglob("*")):
            if entry.is_file():
                relative = entry.relative_to(album_dir)
                found.append((f"album/{relative.as_posix()}", entry, ALLOWED_SUFFIXES))
    for prefix, directory in sorted((extra_dirs or {}).items()):
        if not directory.is_dir():
            continue
        for entry in sorted(directory.rglob("*")):
            if entry.is_file():
                relative = entry.relative_to(directory)
                found.append(
                    (f"{prefix}/{relative.as_posix()}", entry, EXTRA_DIR_SUFFIXES)
                )
    return found


def _render_manifest(
    *,
    stamp: str,
    app_version: str,
    outcome: str,
    facts: Mapping[str, str],
    album_dir: Path | None,
    entries: Sequence[BundleEntry],
) -> str:
    """The human-readable index, and the honest one.

    It lists what went in **and what did not, with the reason**. The skipped
    section is the point: a bundle missing the EAC log because the export failed
    and a bundle missing it because the rip never got that far are different
    findings, and without this they look identical.

    `outcome` is a label. `facts` are the raw fields the label was derived from,
    written out beside it, because a label can be wrong and the fields it came
    from are what a reader can re-derive from.
    """
    lines: list[str] = [
        "PLATTERPUS EVIDENCE BUNDLE",
        "==========================",
        "",
        f"created            {stamp}",
        f"platterpus         {app_version}",
        f"rip outcome        {outcome}",
        f"album folder       {album_dir if album_dir is not None else '(none)'}",
        "",
        "Raw facts this outcome was derived from (a label can be wrong; these",
        "are what it was computed from):",
    ]
    lines.extend(f"  {key:<22} {value}" for key, value in sorted(facts.items()))
    included = [e for e in entries if e.included]
    skipped = [e for e in entries if not e.included]
    lines += [
        "",
        f"INCLUDED ({len(included)} file(s))",
        "-" * 40,
    ]
    if included:
        for entry in included:
            note = f"   [{entry.reason}]" if entry.reason else ""
            lines.append(f"  {entry.name:<52} {entry.bytes_written:>10} B{note}")
    else:
        lines.append("  (nothing — this is itself a finding, not an empty result)")
    lines += [
        "",
        f"NOT INCLUDED ({len(skipped)} file(s))",
        "-" * 40,
        "  Listed so an absence is visible. A bundle quietly missing an artifact",
        "  looks exactly like a complete one.",
    ]
    if skipped:
        for entry in skipped:
            lines.append(f"  {entry.name:<52} {entry.reason}")
    else:
        lines.append("  (nothing was excluded)")
    # **Derived, not typed out.** The first version listed the extensions as prose
    # and was wrong within the hour: it named the strict set while the archive also
    # carried this program's own screenshots under the widened one, so the manifest
    # denied the presence of files it had just listed above. A document that
    # describes a rule in its own words is a second copy of that rule, and the copy
    # is the one that goes stale (`CLAUDE.md`: a comment where a check belongs is
    # not a fix).
    strict = " ".join(sorted(ALLOWED_SUFFIXES))
    widened = " ".join(sorted(EXTRA_DIR_SUFFIXES - ALLOWED_SUFFIXES))
    lines += [
        "",
        "NO AUDIO IS PRESENT — no file of any audio type can enter this archive.",
        f"Everything here passed an allowlist: {strict}",
        f"Plus, from this program's own run folder ONLY: {widened}",
        "(those are screenshots Platterpus took of its own window. An album folder",
        "is never judged by that wider rule, because its images are record-label",
        "artwork.) The per-track CRCs in the logs prove bit-perfection without the",
        "audio.",
        "",
    ]
    return "\n".join(lines)


def build_bundle(
    *,
    dest_dir: Path,
    stamp: str,
    app_version: str,
    outcome: str,
    facts: Mapping[str, str] | None = None,
    album_dir: Path | None = None,
    log_dir: Path,
    extra_dirs: Mapping[str, Path] | None = None,
    extra_text: Mapping[str, str] | None = None,
) -> BundleResult:
    """Write one `.tar.gz` of every text artifact worth sending. Never raises.

    `extra_text` is written into the archive verbatim as `name -> contents`; the
    GUI uses it for the diagnostics blob, which lives in memory rather than in a
    file. Keeping it a parameter is what lets this module stay Qt-free.

    `extra_dirs` maps an archive prefix to a directory whose contents are
    admitted under the *widened* `EXTRA_DIR_SUFFIXES` — used for the test-script
    run folder, whose PNGs are screenshots this program took of its own window.
    The album folder is never passed here; see `EXTRA_DIR_SUFFIXES` for why that
    distinction is load-bearing rather than tidy.
    """
    result = BundleResult()
    facts = dict(facts or {})
    extra_text = dict(extra_text or {})
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive_path = dest_dir / bundle_filename(stamp)

        # Gather and classify FIRST, so the manifest can describe the finished
        # set. Writing the manifest last would mean describing a tar we are in
        # the middle of building, and the description would be the thing that
        # could be wrong.
        payload: list[tuple[str, bytes]] = []
        entries: list[BundleEntry] = []
        for name, source, permitted in _collect(album_dir, log_dir, extra_dirs):
            allowed, why = _is_allowed(source, permitted)
            if not allowed:
                entries.append(BundleEntry(name, str(source), False, why))
                continue
            try:
                data, note = _read_bounded(source)
            except OSError as exc:
                entries.append(
                    BundleEntry(name, str(source), False, f"unreadable: {exc}")
                )
                continue
            payload.append((name, data))
            entries.append(BundleEntry(name, str(source), True, note, len(data)))

        for name, text in sorted(extra_text.items()):
            blob = text.encode("utf-8", errors="replace")
            payload.append((name, blob))
            entries.append(BundleEntry(name, "(generated in-app)", True, "", len(blob)))

        manifest = _render_manifest(
            stamp=stamp,
            app_version=app_version,
            outcome=outcome,
            facts=facts,
            album_dir=album_dir,
            entries=entries,
        )
        payload.insert(0, ("MANIFEST.txt", manifest.encode("utf-8")))

        with tarfile.open(archive_path, "w:gz") as tar:
            for name, data in payload:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                # A fixed mtime and uid/gid: the archive is evidence, and two
                # bundles of the same inputs should differ only where the inputs
                # differ. It also keeps a username off an artifact that gets
                # posted publicly.
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                tar.addfile(info, io.BytesIO(data))

        result.path = archive_path
        result.entries = entries
        log.info(
            "evidence bundle written: %s (%d file(s) in, %d excluded, %d bytes)",
            archive_path,
            len(result.included),
            len(result.skipped),
            archive_path.stat().st_size,
        )
    except Exception as exc:  # noqa: BLE001 — a convenience must never crash a rip
        log.exception("could not write the evidence bundle")
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def sha256_of(path: Path) -> str:
    """Hex digest of a file, or "" if it cannot be read. Never raises."""
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        log.warning("could not hash %s", path, exc_info=True)
        return ""
