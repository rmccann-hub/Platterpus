"""The overnight acceptance run, as a thing the *program* does.

**Why this module exists.** Running an acceptance session today means the
maintainer downloads three bash files and types three commands. Their words:
*"this was supposed to be a no cli program, not give me commands to use"* and
*"i should just be able to run this with an specific script file i can use with
the settings window, and run it, not a ton of scripts and shit in bash, make it
all verify and do it itself"*.

That is the rule `CLAUDE.md` already states about handing back instruction
files: **every manual step in a procedure is a thing the software was supposed
to do.** Three shell scripts — `docs/rig-scripts/platterpusovernight.sh`,
`docs/rig-scripts/platterpusmorning.sh` and the harness in `rig_session.sh` —
between them make a session folder, run the acceptance script, collect the
artifacts, and pack **one** `.tar.gz` into `~/Downloads`. This module is the
Qt-free core of the same job, so the app can do it from a button.

**What this module is NOT.** It is not a second bundler. Deciding what may enter
an archive, refusing audio by allowlist, naming every omission and never raising
are all already solved in :mod:`platterpus.evidence_bundle`, and `CLAUDE.md` is
explicit that a second implementation is a second thing to drift. Everything
here delegates: this module decides *which paths* a session involves and *where
the one file lands*, and hands the rest over.

**The shape of the module, and why it is split this way.**

* :func:`plan_session` is **pure**. It decides every path and touches no disk,
  which is what makes the interesting decisions — the `~/Downloads` fallback
  above all — assertable in a unit test with no filesystem at all. This project's
  rule is that decision logic lives in a pure, testable function rather than
  scattered through the code that acts on it.
* The clock is **never read inside** the pure function. A function that reads the
  clock cannot be asserted against, so the timestamp arrives as a parameter and
  :func:`session_stamp` (which formats a moment the *caller* supplies) is the
  only thing that knows the format.
* The one question that genuinely needs the disk — *does `~/Downloads` exist?* —
  is its own named function, :func:`downloads_dir`, so the impure part is one
  line and the decision that uses its answer stays pure.
* :func:`finish_session` **never raises**. Packaging is a convenience wrapped
  around a test run that has already finished; a bug here must not surface as a
  crash on top of a completed overnight session. Failures come back in
  :attr:`~platterpus.evidence_bundle.BundleResult.error`.

No Qt import anywhere, deliberately: this has to be unit-testable headless, and
the GUI's job is only to call it from a worker thread (`CLAUDE.md`'s
never-block-the-GUI-thread rule — staging files and gzipping a multi-megabyte log
is not a main-thread operation).
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from platterpus import __version__
from platterpus.evidence_bundle import BundleResult, build_bundle, bundle_filename

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# The acceptance script that ships inside the package
# --------------------------------------------------------------------------

#: Directory *inside the package* holding scripts we ship. It lives here rather
#: than in `docs/` or `scripts/` for the same reason `rig_session.sh` does: a
#: hardware session must not need a source clone at the right commit. One file,
#: reachable identically from a checkout, a `pipx` install and the AppImage.
BUILTIN_SCRIPT_DIR_NAME: Final[str] = "rig_scripts"

#: The full overnight acceptance run. Named as a constant rather than typed at
#: each call site so the name has exactly one home.
ACCEPTANCE_SCRIPT_NAME: Final[str] = "fullacceptance.txt"


def builtin_acceptance_script_path() -> Path:
    """Where the packaged acceptance script *would* live. PURE — no disk access.

    Answers even when the file is missing, which is the point: an error message
    that cannot name the path it looked for is not a diagnosis. Use
    :func:`builtin_acceptance_script` when you need to know whether it is really
    there.
    """
    package_root = Path(__file__).resolve().parent
    return package_root / BUILTIN_SCRIPT_DIR_NAME / ACCEPTANCE_SCRIPT_NAME


def builtin_acceptance_script() -> tuple[Path | None, str]:
    """The packaged acceptance script, or ``None`` plus why not. Never raises.

    Returns ``(path, explanation)``. ``explanation`` is always populated and
    always written for a person — this is the same shape
    :func:`platterpus.uiscript.find_script.resolve_script_path` already returns,
    kept identical on purpose so the two ways of naming a script report their
    failures the same way rather than in two dialects.

    A missing file is reported, not raised: the packaging step that ships this
    file can fail (it needs a `[tool.setuptools.package-data]` entry), and the
    right response is a sentence on screen naming the path, not a traceback on
    top of whatever the user was doing.
    """
    path = builtin_acceptance_script_path()
    try:
        if path.is_file():
            return path, f"using the acceptance script shipped in the app: {path}"
    except OSError as exc:  # pragma: no cover — an unreadable package dir
        log.warning("could not check for the packaged acceptance script: %r", exc)
        return None, f"could not check {path}: {exc}"
    log.error("the packaged acceptance script is missing: %s", path)
    return None, (
        f"the acceptance script that ships inside Platterpus is not there: {path}. "
        "This build did not include it — the app cannot run the overnight session "
        "until it does. You can still point the app at a script file yourself."
    )


# --------------------------------------------------------------------------
# Timestamps
# --------------------------------------------------------------------------

#: UTC, sortable, no punctuation a shell or a file manager will argue with. The
#: same shape the bash used (`date -u +%Y%m%dT%H%M%SZ`), kept so a session folder
#: made by the old script and one made by the app sort together in a listing.
STAMP_FORMAT: Final[str] = "%Y%m%dT%H%M%SZ"


def session_stamp(moment: datetime) -> str:
    """Format a moment the CALLER supplies. Pure — it never reads the clock.

    Every path in this module descends from this string, so if it were read from
    the clock in here, not one of those paths could be asserted against. The
    caller writes ``session_stamp(datetime.now(timezone.utc))``; a test writes
    ``session_stamp(datetime(2026, 8, 28, tzinfo=timezone.utc))``.
    """
    return moment.strftime(STAMP_FORMAT)


def _stamp_slug(stamp: str) -> str:
    """A stamp reduced to the cross-machine filename alphabet.

    `CLAUDE.md` → *Artifact filenames that cross machines*: lowercase ASCII
    letters and digits only, because a rig run was once lost to the same artifact
    being `round08joint.txt` on one disk and `round-08-joint.txt` in the
    instructions written for it. A path is an exact-match string.

    This is the same reduction :func:`~platterpus.evidence_bundle.bundle_filename`
    applies. It is repeated here rather than imported because that function
    returns a whole *filename*, not a slug — and the two are pinned to each other
    by a test (the bundle's name must contain this slug), so they cannot drift
    apart quietly.
    """
    return "".join(ch for ch in stamp.lower() if ch.isascii() and ch.isalnum())


# --------------------------------------------------------------------------
# Deciding the paths
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionLayout:
    """Every path one acceptance session uses. Decided once, passed around.

    Frozen because these are a *decision*, not a working area: a function that
    could quietly repoint `bundle` halfway through a session is a function that
    can put the deliverable somewhere nobody looks.
    """

    #: The stamp every path below descends from. Carried so callers (and the
    #: bundler) never have to re-derive it and get a different answer.
    stamp: str
    #: The session folder. Staging happens here; it stays in `$HOME`.
    root: Path
    #: Where the script run's transcript is written.
    transcript: Path
    #: Collected copies of individual files live here.
    artifacts: Path
    #: **The one file the user sends.** Full path, name included.
    bundle: Path


#: Session-folder prefix. Lowercase and separator-free for the same reason the
#: archive's name is (see :func:`_stamp_slug`) — the "send this" message names
#: this directory when the archive itself could not be written, so an operator
#: may well type it.
SESSION_DIR_PREFIX: Final[str] = "platterpustestsession"


def downloads_dir(home: Path) -> Path | None:
    """``home/Downloads`` **if it really exists**, otherwise ``None``.

    The only disk-touching decision in the whole path story, pulled out into its
    own function so :func:`plan_session` can stay pure and still be given the
    real answer.

    **It never creates the directory**, and that is deliberate rather than lazy —
    the bash it replaces says so at length. `~/Downloads` is chosen because it is
    the folder a browser's upload dialog opens in, so the deliverable is already
    in front of the operator. Inventing that folder on a machine that does not
    have one puts the file somewhere the operator has *no habit of looking*,
    which is the original problem with an extra step in front of it.
    """
    try:
        candidate = home / "Downloads"
        return candidate if candidate.is_dir() else None
    except OSError as exc:  # pragma: no cover — an unreadable $HOME
        log.warning("could not check for %s/Downloads: %r", home, exc)
        return None


def plan_session(
    *, home: Path, stamp: str, downloads: Path | None = None
) -> SessionLayout:
    """Decide every path for one session. **PURE** — touches no disk at all.

    No ``mkdir``, no ``exists()``, nothing whose answer depends on the machine.
    Call it twice with the same arguments and you get equal results, which is
    what lets the interesting decision below be tested without a filesystem.

    ``downloads`` is the **already-resolved** answer to "is there a Downloads
    folder?" — pass :func:`downloads_dir(home) <downloads_dir>`, or ``None``.

    ``None`` means *there is no Downloads folder*, so the archive lands in
    ``$HOME``. It does **not** mean "work it out for me": if this function
    decided that itself it would have to touch the disk, and the fallback — the
    one behaviour most likely to put the deliverable where the operator cannot
    find it — would stop being assertable.
    """
    slug = _stamp_slug(stamp)
    root = home / f"{SESSION_DIR_PREFIX}{slug}"
    # The archive's *name* comes from the bundler, so this module and the module
    # that writes the file cannot disagree about what the deliverable is called.
    # Two surfaces answering one question with two spellings is how a "send me
    # this file" instruction stops naming a file that exists.
    destination = downloads if downloads is not None else home
    return SessionLayout(
        stamp=stamp,
        root=root,
        transcript=root / "transcript.txt",
        artifacts=root / "artifacts",
        bundle=destination / bundle_filename(stamp),
    )


def prepare_session(layout: SessionLayout) -> None:
    """Create the session directories. Idempotent — safe to call twice.

    **Raises** ``OSError`` if the folders cannot be made, and that is the right
    behaviour here rather than the never-raises rule that governs
    :func:`finish_session`: nothing has run yet, so a session that cannot create
    its own workspace must stop before the disc spins rather than discover it
    six hours later.

    Note what it does *not* create: the archive's destination directory. That is
    `~/Downloads` only when :func:`downloads_dir` found a real one, so there is
    no path on which this module conjures a Downloads folder into existence.
    """
    layout.root.mkdir(parents=True, exist_ok=True)
    layout.artifacts.mkdir(parents=True, exist_ok=True)
    log.info("acceptance session workspace ready: %s", layout.root)


# --------------------------------------------------------------------------
# Deciding what to collect
# --------------------------------------------------------------------------


#: Where a staged app-log ROTATION goes inside the session folder. Chosen so it
#: sorts AFTER `transcript.txt` — see the note in `_stage`. A `z` prefix is blunt
#: and that is the point: the ordering is load-bearing, so it should be obvious
#: to anyone renaming it.
_ROTATION_STAGE_DIR: Final[str] = "zz-applog-rotations"


def _is_log_rotation(path: Path) -> bool:
    """Is this a rotated app log (`log.txt.3`) rather than the current one?

    Keyed on the same shape `_log_rotations` produces, so "what is a rotation"
    has one definition here rather than two that can disagree.
    """
    return bool(re.fullmatch(r".+\.txt\.\d+", path.name))


def _log_rotations(log_path: Path) -> list[Path]:
    """`log.txt.1`, `log.txt.2`… beside ``log_path``, oldest-numbered first.

    Globbing reads the disk, which is fine here — :func:`session_sources` is not
    the pure one. What it must never do is *filter by existence*, and it does
    not: a rotation that is not on disk has no name to report, whereas the files
    we can name are reported whether they exist or not.

    The rotation shape mirrors ``evidence_bundle``'s (a numeric suffix on the
    log's own name). That module stays the authority on what may enter an
    archive; this only decides what is worth *looking* at.
    """
    try:
        found = [
            p
            for p in log_path.parent.glob(f"{log_path.name}.*")
            if p.is_file() and p.name[len(log_path.name) + 1 :].isdigit()
        ]
    except OSError as exc:
        log.warning("could not list log rotations beside %s: %r", log_path, exc)
        return []
    return sorted(found, key=lambda p: (len(p.name), p.name))


def session_sources(
    layout: SessionLayout,
    *,
    log_path: Path,
    extra: Sequence[Path] = (),
) -> list[Path]:
    """Everything worth collecting, in order, deduplicated, absences included.

    **A path that does not exist is still returned.** That is the whole point of
    the list: :func:`finish_session` writes a record naming every entry and what
    became of it, so *"the app log was not there"* is a line somebody can read
    rather than a gap they cannot see. `CLAUDE.md`: a silent truncation reads as
    completeness, and a bundle quietly missing an artifact looks exactly like a
    complete one.

    ``extra`` is where the caller adds anything else — the config file, a rip
    folder, a `--rig-session` output directory. Those are not hardcoded here so
    this module never reaches into the real machine's `~/.config` behind a
    caller's back; the app wires in :data:`platterpus.paths.CONFIG_PATH` at the
    call site, and a test wires in a temporary directory.

    Deduplication is by the expanded path as written, **not** by
    ``Path.resolve()``. Resolving touches the disk, and — the reason that matters
    — an absent path resolves differently from a present one, so a resolving
    dedupe would behave differently for exactly the entries this function exists
    to keep.
    """
    candidates: list[Path] = [
        layout.transcript,
        layout.artifacts,
        log_path,
        *_log_rotations(log_path),
        *extra,
    ]
    seen: set[Path] = set()
    ordered: list[Path] = []
    for raw in candidates:
        path = raw.expanduser()
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


# --------------------------------------------------------------------------
# Packing the one file
# --------------------------------------------------------------------------

#: Handed to ``build_bundle(log_dir=...)``, which requires the argument.
#:
#: This module deliberately collects **only what `sources` names** — one list in,
#: one archive out — so the bundler's own "sweep the app log directory" route
#: must contribute nothing, or the log would arrive twice under two names and
#: every byte count in the manifest would be wrong. `os.devnull` is never a
#: directory, so this reads as a stated no-op rather than as an argument somebody
#: forgot to fill in.
_NO_LOG_SWEEP: Final[Path] = Path(os.devnull)

#: Archive member holding the record below. Written by us and allowed to
#: overwrite a caller's key of the same name: it is the omission record, and a
#: caller must not be able to blank it by accident.
SOURCES_RECORD_NAME: Final[str] = "SOURCES.txt"


def _member_slug(name: str) -> str:
    """A directory name made safe to use as an archive path component.

    Album titles reach this — they are user data and routinely contain spaces,
    colons and angle brackets. Those are legal inside a tar, but they are also
    what makes a member name unquotable in the shell command somebody will
    eventually run over it, so they are flattened.
    """
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in name)
    return cleaned.strip("._-") or "unnamed"


def _link_or_copy(source: Path, destination: Path) -> None:
    """Put ``source``'s content at ``destination``, cheaply where possible.

    A hard link first: staging a session's files should not double a
    multi-megabyte log on a machine that has just finished ripping. Falls back to
    a copy when a link is impossible (a different filesystem, a directory that
    already holds the name, a filesystem with no link support).

    Nothing here ever *writes* to a staged file, so sharing an inode with the
    user's real log is safe — it is read, archived, and left alone.
    """
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _is_within(path: Path, root: Path) -> bool:
    """Is ``path`` inside ``root``? Pure string comparison, no disk access."""
    return path == root or root in path.parents


@dataclass
class _Staged:
    """What :func:`_stage` worked out: the archive routes plus the honest record."""

    extra_dirs: dict[str, Path]
    lines: list[str]
    present: int
    absent: int
    failed: int


def _stage(layout: SessionLayout, sources: Sequence[Path]) -> _Staged:
    """Route every named source, and write down what became of each one.

    Three routes, chosen by what the path *is*:

    * **A directory** goes into the archive as its own ``extra_dirs`` entry — no
      copying at all. The bundler walks it, applies its allowlist and reports
      what it refused, which is strictly better than us copying a tree first and
      hoping.

      **DO NOT NAME AN ALBUM FOLDER AS A SOURCE.** ``extra_dirs`` is the route
      that widens the allowlist to admit `.png`, because it exists for folders
      holding screenshots *this program took of its own window*. An album folder
      routinely contains `cover.png` / `folder.png`, which is record-label
      artwork — the copyrighted media Critical rule #8 is about — and it would be
      admitted here. ``evidence_bundle`` keeps that distinction load-bearing by
      never judging an album folder under the widened set, and this module can
      only preserve it by never handing one over. Audio is refused either way;
      artwork is not, and this is the one place that difference bites. A rip
      folder's *text* belongs in a session bundle as individual named files, or
      through ``build_bundle(album_dir=…)``, which uses the strict set.
    * **A file** is linked (or copied) into its own subfolder of
      ``layout.artifacts``, because ``build_bundle`` has no route for a lone
      file. The subfolder — not a renamed file — is what keeps two sources both
      called `log.txt` from becoming one, and it is deliberate rather than tidy:
      **renaming would change the suffix the bundler judges the file by.** The
      first version appended a counter, produced `log.txt-1`, and that name is
      neither an allowed extension nor a recognised rotation, so the second file
      was silently refused from the archive. A collision fix that drops the file
      is worse than the collision. The folder is named for the source's own
      parent directory so a member can be traced back to where it came from.
    * **Anything inside the session folder** is skipped, because the session
      folder is already an ``extra_dirs`` entry — staging it into itself would
      both duplicate it and, for `artifacts`, recurse.

    Absences and staging failures are counted and named. Never raises: a source
    that cannot be staged is a line in the record, not the end of the session.
    """
    extra_dirs: dict[str, Path] = {"session": layout.root}
    lines: list[str] = []
    present = absent = failed = 0

    for index, source in enumerate(sources):
        try:
            is_dir = source.is_dir()
            is_file = source.is_file()
        except OSError as exc:
            failed += 1
            lines.append(f"  {source}\n      UNREADABLE: {exc}")
            continue

        if not is_dir and not is_file:
            # NAMED, not dropped. "the EAC log was never written" and "the EAC log
            # was written and we failed to collect it" are different findings, and
            # without this line they look identical.
            absent += 1
            lines.append(f"  {source}\n      ABSENT — it was not there to collect")
            continue

        if _is_within(source, layout.root):
            present += 1
            relative = source.relative_to(layout.root)
            lines.append(
                f"  {source}\n      in the session folder — archived as "
                f"session/{relative.as_posix()}"
            )
            continue

        if is_dir:
            present += 1
            prefix = f"extra{index:02d}{_member_slug(source.name)}"
            extra_dirs[prefix] = source
            lines.append(f"  {source}\n      directory — archived under {prefix}/")
            continue

        # A file. Its own subfolder, so two `log.txt`s from two directories do
        # not become one — and so the FILENAME is never altered, because the
        # bundler decides what may enter by reading that name (see the docstring).
        #
        # **A ROTATION IS STAGED SOMEWHERE THAT SORTS LAST, and that is the
        # budget again.** `build_bundle` walks an `extra_dirs` tree with
        # `sorted(rglob("*"))` and charges `MAX_TOTAL_BYTES` in that order, so a
        # relative path decides what survives a full archive. Under the old
        # single `artifacts/` root the order was `artifacts/02share/log.txt.1` …
        # then `transcript.txt` — every rotation ahead of the one file that
        # records whether the run passed.
        #
        # This is the SAME defect `_collect` was fixed for on 2026-08-29, at a
        # second site, found by an audit refuting the first fix's scope. Fixing
        # it where it was learned and not across the codebase is `docs/testing.md`
        # §5.o, and this is that lesson landing on the very change that cited it.
        #
        # `_ROTATION_STAGE_DIR` sorts after `transcript.txt` lexicographically,
        # which is the whole mechanism — no new cap, no reserved share.
        parent = (
            layout.root / _ROTATION_STAGE_DIR
            if _is_log_rotation(source)
            else layout.artifacts
        )
        folder = parent / f"{index:02d}{_member_slug(source.parent.name)}"
        destination = folder / source.name
        try:
            folder.mkdir(parents=True, exist_ok=True)
            _link_or_copy(source, destination)
        except OSError as exc:
            failed += 1
            lines.append(f"  {source}\n      COULD NOT COLLECT: {exc}")
            continue
        present += 1
        lines.append(
            f"  {source}\n      archived as session/"
            f"{destination.relative_to(layout.root).as_posix()}"
        )

    return _Staged(extra_dirs, lines, present, absent, failed)


def _render_sources_record(layout: SessionLayout, staged: _Staged) -> str:
    """The per-source record, written into the archive as `SOURCES.txt`.

    ``evidence_bundle``'s own manifest reports what it saw; it cannot report a
    file it was never handed. This is the other half: every path this session
    *asked for*, and what became of it. The two together are what make an absence
    visible instead of invisible.
    """
    total = staged.present + staged.absent + staged.failed
    return "\n".join(
        [
            "PLATTERPUS ACCEPTANCE SESSION — SOURCES",
            "=======================================",
            "",
            f"session stamp      {layout.stamp}",
            f"session folder     {layout.root}",
            f"deliverable        {layout.bundle}",
            "",
            "Every path this session asked for is listed below, INCLUDING the ones",
            "that were not there. An absence somebody can read is a finding; an",
            "absence nobody can see reads as a complete bundle.",
            "",
            f"asked for {total}: {staged.present} collected, "
            f"{staged.absent} absent, {staged.failed} failed",
            "",
        ]
        + (staged.lines or ["  (nothing was named — this is itself a finding)"])
        + [
            "",
            "No audio can be in this archive: everything above passed the",
            "allowlist in evidence_bundle (see MANIFEST.txt, which names every",
            "file it refused and why).",
            "",
        ]
    )


def _album_scan_facts(album_dirs: Sequence[Path]) -> dict[str, str]:
    """How many album folders went in — and how many were dropped getting here.

    ``build_bundle``'s manifest names every folder it *received*, which is a
    complete account of its own input and no account at all of what was cut
    before it. :func:`session_album_dirs` caps its result, so the bundle could
    honestly name 40 folders while a 41st finished rip existed on disk and was
    never mentioned anywhere. This is the line that closes that.

    **Tri-state, never a comforting zero.** A caller who passes a plain list has
    not told us whether anything was dropped, and writing ``0`` there would be an
    invented fact of exactly the kind this project refuses to write for an
    unreaped exit code. It says *not determined* instead.
    """
    facts = {"album folders": str(len(album_dirs))}
    if isinstance(album_dirs, AlbumScan):
        facts["album folders examined"] = str(album_dirs.examined)
        facts["album folders dropped"] = str(album_dirs.dropped)
    else:
        facts["album folders dropped"] = (
            "not determined — the caller passed a plain sequence, which carries "
            "no record of the scan that produced it"
        )
    return facts


def finish_session(
    layout: SessionLayout,
    *,
    sources: Sequence[Path],
    embedded_text: Mapping[str, str] | None = None,
    app_version: str = __version__,
    outcome: str = "acceptance test session",
    facts: Mapping[str, str] | None = None,
    album_dirs: Sequence[Path] = (),
) -> BundleResult:
    """Pack the session into **one file**. Never raises.

    Delegates the archive itself to
    :func:`~platterpus.evidence_bundle.build_bundle` — the allowlist that refuses
    audio, the head-and-tail bounding, the manifest that names every exclusion
    and the "never raises" guarantee all live there and are not repeated here.
    What this adds is the session's own record of *what it asked for*, including
    the paths that were not there (see :func:`_render_sources_record`).

    ``embedded_text`` is written into the archive verbatim as ``name ->
    contents`` — for text that lives in memory rather than in a file, such as the
    run's diagnostics blob. Keeping it a parameter is what lets this module stay
    Qt-free.

    **One thing a caller must not do:** name an album folder in ``sources``. See
    :func:`_stage` — a directory source is admitted under the *widened* allowlist
    that exists for this program's own screenshots, and an album folder's `.png`
    is record-label artwork. Audio cannot get in either way; artwork can.

    ``album_dirs`` is the safe route for exactly that, and it is why the parameter
    exists separately: it goes to ``build_bundle``'s own album channel, which is
    held to the STRICT allowlist however many folders are passed. An acceptance
    session rips several discs, and without this its bundle carried the app log
    and the transcript but **none of the per-album text artifacts** the shell
    collector it replaces had always gathered — the rip logs, cue sheets, reports
    and checksums that are the actual evidence a session exists to produce.

    A failure comes back as :attr:`BundleResult.error`. An overnight session that
    has just finished six hours of ripping must not lose its evidence to a bug in
    the packaging step, and a crash at that moment would be indistinguishable
    from the run itself failing.
    """
    result = BundleResult()
    try:
        staged = _stage(layout, sources)
        text: dict[str, str] = dict(embedded_text or {})
        text[SOURCES_RECORD_NAME] = _render_sources_record(layout, staged)
        result = build_bundle(
            dest_dir=layout.bundle.parent,
            stamp=layout.stamp,
            app_version=app_version,
            outcome=outcome,
            facts={
                **dict(facts or {}),
                "session folder": str(layout.root),
                "sources collected": str(staged.present),
                "sources absent": str(staged.absent),
                "sources failed": str(staged.failed),
                **_album_scan_facts(album_dirs),
            },
            album_dirs=list(album_dirs),
            log_dir=_NO_LOG_SWEEP,
            extra_dirs=staged.extra_dirs,
            extra_text=text,
        )
    except Exception as exc:  # noqa: BLE001 — must never crash a finished session
        log.exception("could not pack the acceptance session")
        result.error = f"{type(exc).__name__}: {exc}"
    if result.ok and result.path is not None:
        log.info("SEND THIS ONE FILE: %s", result.path)
    else:
        log.error(
            "could not pack the session (the folder is still complete at %s): %s",
            layout.root,
            result.error,
        )
    return result


#: What marks a directory as a rip's album folder. Every finished rip writes
#: one beside its log, so its presence is the app's own evidence that a rip
#: landed there — rather than a guess from the folder's name, which comes from
#: MusicBrainz metadata and is not ours to predict (the 2026-08-23 defect where
#: a predicted folder name missed by one glyph and a finished rip was
#: overwritten).
RIP_REPORT_GLOB: Final[str] = "*.platterpus.json"


class AlbumScan(list[Path]):
    """The album folders a scan kept, carrying what it had to leave behind.

    **Why a `list` subclass and not a dataclass.** The count has to arrive at the
    bundle, and the route it must travel is an existing one:
    ``session_album_dirs(...)`` → ``finish_session(album_dirs=...)`` →
    ``build_bundle``. A dataclass would make every caller unpack it, and a
    caller that forgets is a caller that silently reports nothing — which is the
    defect being fixed, moved one function along. Being a `list[Path]` means the
    value flows exactly as it did, compares equal to the plain list a test
    writes, and the counts ride along for whoever asks.

    It is deliberately not clever: no ``__getattr__``, no properties, no
    behaviour changed. Two integers on a list.

    :attr:`examined` is how many distinct album folders the scan actually found;
    :attr:`dropped` is how many of them the cap discarded. ``examined ==
    len(self) + dropped`` always, which is what makes the pair checkable rather
    than merely reported.
    """

    #: Distinct album folders found before the cap was applied.
    examined: int
    #: How many of those the cap discarded — the number that used to vanish.
    dropped: int

    def __init__(self, folders: Iterable[Path], *, examined: int, dropped: int) -> None:
        super().__init__(folders)
        self.examined = examined
        self.dropped = dropped


def session_album_dirs(
    search_roots: Sequence[Path], *, since: float, limit: int = 40
) -> AlbumScan:
    """Album folders that received a rip DURING this session. Never raises.

    **Why discovered and not remembered.** The obvious alternative is for the
    session to record each folder as its rips finish. That fails exactly when it
    matters: a run that crashes, is cancelled, or ends in a way the bookkeeping
    did not anticipate still leaves finished rips on disk, and those are the ones
    somebody needs to send. Reading the disk answers "what is actually there",
    which is a different and more reliable question than "what do we think we
    did" (`CLAUDE.md`: *why am I predicting this at all when I could read it?*).

    ``since`` is a POSIX timestamp taken when the session started, passed in
    rather than read from a clock here so a test can pin it. A folder is included
    when its report file was modified at or after that moment — so a library full
    of previous rips does not end up in the archive, and a rip from this session
    does even if its folder existed before.

    ``limit`` bounds a pathological case rather than a normal one: a
    misconfigured output directory pointing at a whole music library would
    otherwise put hundreds of folders through the bundler. Ordering newest-first
    decides **which** folders survive that cap, so what is kept is the most
    recent work rather than an arbitrary slice.

    **Ordering is not visibility, and this docstring used to claim it was.** It
    argued that newest-first plus a manifest naming every folder received meant
    the archive "never implies it covers more than it does" — true of the folders
    that arrived, and silent about the ones that never did. A folder past the cap
    left no count, no manifest line and no log entry: a 41st finished rip could
    sit on disk while a complete-looking bundle carried 40 and said nothing at
    all about the one it dropped. So the loss is returned (:class:`AlbumScan`),
    written into
    the bundle's facts (:func:`_album_scan_facts`) and logged here. A cap that
    cannot be seen is a silent truncation, and this module's whole subject is
    that a silent truncation reads as completeness.
    """
    found: dict[Path, float] = {}
    for root in search_roots:
        try:
            if not root.is_dir():
                continue
            for report in root.rglob(RIP_REPORT_GLOB):
                try:
                    modified = report.stat().st_mtime
                except OSError:
                    continue
                if modified < since:
                    continue
                folder = report.parent
                found[folder] = max(found.get(folder, 0.0), modified)
        except OSError as exc:
            # A search root we cannot read is a fact about this machine, not a
            # reason to lose the roots we can.
            log.warning("could not scan %s for rip folders: %r", root, exc)
    newest_first = sorted(found.items(), key=lambda item: item[1], reverse=True)
    kept = [folder for folder, _ in newest_first[:limit]]
    dropped = len(found) - len(kept)
    if dropped:
        # To the log as well as to the return value, because the app log is
        # itself inside the bundle: a reader who wonders why a rip they remember
        # is not in the archive can find the sentence that says so.
        log.warning(
            "the album-folder scan found %d rip folder(s) and the cap of %d kept "
            "the newest %d — %d were dropped and are NOT in the bundle",
            len(found),
            limit,
            len(kept),
            dropped,
        )
    return AlbumScan(kept, examined=len(found), dropped=dropped)
