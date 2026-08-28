"""Tests for :mod:`platterpus.test_session` — the in-app acceptance session.

**What these are really checking.** The module replaces three bash scripts whose
one job was to put a single, audio-free archive somewhere the operator can find
it. Each test below pins a decision that was made in that bash and would be
silently easy to lose in a rewrite:

* the path decisions are **pure**, so they can be asserted at all;
* the archive lands in `~/Downloads` **only when one exists** — the bash refuses
  to invent that folder, because a file in a directory the operator has no habit
  of opening is the original problem with an extra step in front of it;
* a source that was **not there** is still named, because an absence nobody can
  see reads as a complete bundle;
* **no audio can get in**, and the archive says so itself.

Every archive assertion carries a floor. A check that can be satisfied by finding
nothing is decoration: "no `.flac` in the archive" passes perfectly against an
archive with nothing in it at all.
"""

from __future__ import annotations

import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from platterpus import test_session
from platterpus.evidence_bundle import bundle_filename
from platterpus.test_session import (
    SESSION_DIR_PREFIX,
    SOURCES_RECORD_NAME,
    STAMP_FORMAT,
    SessionLayout,
    builtin_acceptance_script,
    builtin_acceptance_script_path,
    downloads_dir,
    finish_session,
    plan_session,
    prepare_session,
    session_sources,
    session_stamp,
)

#: One fixed stamp for every test. Fixed, because a stamp read from the clock
#: makes every path below unassertable — which is the reason the module takes it
#: as a parameter rather than generating it.
STAMP = "20260828T010203Z"


def _members(archive: Path) -> list[str]:
    with tarfile.open(archive, "r:gz") as tar:
        return tar.getnames()


def _member_text(archive: Path, name: str) -> str:
    with tarfile.open(archive, "r:gz") as tar:
        handle = tar.extractfile(name)
        assert handle is not None, f"{name} is in the archive but not readable"
        return handle.read().decode("utf-8")


# ---------------------------------------------------------------------------
# The packaged acceptance script
# ---------------------------------------------------------------------------


def test_builtin_script_path_is_absolute_and_inside_the_package() -> None:
    """The path is decided without touching the disk, so it always answers.

    An error message that cannot name the file it looked for is not a diagnosis.
    """
    path = builtin_acceptance_script_path()
    assert path.is_absolute()
    assert path.name == "fullacceptance.txt"
    assert path.parent.name == "rig_scripts"
    # Inside the installed package, not beside the checkout: that is what makes
    # it reachable identically from a source tree, a pipx install and the
    # AppImage.
    import platterpus

    assert Path(platterpus.__file__).resolve().parent in path.parents


def test_builtin_script_reports_presence_rather_than_raising() -> None:
    """Present or absent, it answers with a sentence — it never raises.

    Written as the *relation* between the two functions rather than as an
    assertion about today's tree, so it keeps testing something once the script
    file is added: the pure path function says where it would be, and this one
    says whether it is really there, and the two must agree.
    """
    expected = builtin_acceptance_script_path()
    found, explanation = builtin_acceptance_script()
    assert explanation, "an explanation is always written, in both directions"
    assert str(expected) in explanation, "the message must name the path it used"
    if expected.is_file():
        assert found == expected
    else:
        assert found is None


def test_a_missing_packaged_script_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The error branch, exercised on purpose.

    The relation test above only runs whichever branch today's tree happens to
    take, and the packaged script is present — so the branch that *matters* (a
    build that shipped without it) would otherwise never execute and could not be
    said to work. A build with the `package-data` entry missing is exactly the
    failure this reporting exists for.
    """
    monkeypatch.setattr(test_session, "BUILTIN_SCRIPT_DIR_NAME", "no_such_directory")

    found, explanation = builtin_acceptance_script()

    assert found is None
    assert "no_such_directory" in explanation, "the message must name where it looked"
    assert "fullacceptance.txt" in explanation


# ---------------------------------------------------------------------------
# plan_session is pure
# ---------------------------------------------------------------------------


def test_plan_session_is_pure(tmp_path: Path) -> None:
    """Same arguments, equal result — and nothing appears on disk.

    Purity is not a style preference here: it is what lets the `~/Downloads`
    decision below be asserted without a filesystem, and what stops a "decide
    where it goes" function from quietly creating the place it decided on.
    """
    first = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    second = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    assert first == second

    # Floor: the call really did produce paths under `tmp_path`, so "nothing was
    # created" is a statement about a call that did something.
    assert first.root.parent == tmp_path
    assert first.transcript.parent == first.root
    assert first.artifacts.parent == first.root

    # And the disk is untouched.
    assert list(tmp_path.iterdir()) == []


def test_plan_session_names_the_folder_in_the_cross_machine_alphabet(
    tmp_path: Path,
) -> None:
    """Lowercase ASCII alphanumerics only — a rig run was lost to this once.

    Asserted as a relation against `evidence_bundle.bundle_filename` rather than
    against a hand-written expected string, because those two spellings must not
    be able to drift apart: the archive's name and the folder's name descend from
    one stamp and a "send me this file" instruction has to name a file that
    exists.
    """
    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    slug = layout.root.name[len(SESSION_DIR_PREFIX) :]
    assert slug == STAMP.lower().replace(":", "")
    assert slug.isalnum() and slug.islower()
    assert layout.bundle.name == bundle_filename(STAMP)
    assert slug in layout.bundle.name


def test_session_stamp_formats_the_moment_it_is_given() -> None:
    """The clock is the caller's business; this only formats."""
    moment = datetime(2026, 8, 28, 1, 2, 3, tzinfo=UTC)
    assert session_stamp(moment) == STAMP
    assert moment.strftime(STAMP_FORMAT) == STAMP


# ---------------------------------------------------------------------------
# The ~/Downloads fallback — both branches
# ---------------------------------------------------------------------------


def test_bundle_lands_in_downloads_when_one_exists(tmp_path: Path) -> None:
    """A browser's upload dialog opens in `~/Downloads`, so the file goes there."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    resolved = downloads_dir(tmp_path)
    assert resolved == downloads

    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=resolved)
    assert layout.bundle.parent == downloads
    assert layout.bundle == downloads / bundle_filename(STAMP)
    # The staging folder always stays in $HOME; only the ONE file moves.
    assert layout.root.parent == tmp_path


def test_bundle_falls_back_to_home_and_downloads_is_never_invented(
    tmp_path: Path,
) -> None:
    """No `~/Downloads` → the archive goes to `$HOME`, and none is created.

    Creating the folder would put the deliverable somewhere the operator has no
    habit of looking, which is the same problem the fallback exists to avoid.
    """
    assert downloads_dir(tmp_path) is None
    assert not (tmp_path / "Downloads").exists(), "asking must not create it"

    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=downloads_dir(tmp_path))
    assert layout.bundle.parent == tmp_path
    assert layout.bundle == tmp_path / bundle_filename(STAMP)
    assert not (tmp_path / "Downloads").exists(), "planning must not create it either"


def test_a_downloads_file_rather_than_a_directory_is_not_downloads(
    tmp_path: Path,
) -> None:
    """A *file* called `Downloads` is not a folder to put anything in."""
    (tmp_path / "Downloads").write_text("not a directory", encoding="utf-8")
    assert downloads_dir(tmp_path) is None


# ---------------------------------------------------------------------------
# prepare_session
# ---------------------------------------------------------------------------


def test_prepare_session_is_idempotent(tmp_path: Path) -> None:
    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    prepare_session(layout)
    prepare_session(layout)  # again: must not raise
    assert layout.root.is_dir()
    assert layout.artifacts.is_dir()
    assert not (tmp_path / "Downloads").exists()


# ---------------------------------------------------------------------------
# session_sources
# ---------------------------------------------------------------------------


def test_session_sources_keeps_a_path_that_does_not_exist(tmp_path: Path) -> None:
    """An absent artifact must still be NAMED, so the record can report it.

    Filtering by existence here is what makes "the EAC log was never written" and
    "we failed to collect the EAC log" look identical in the finished bundle.
    """
    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    missing = tmp_path / "nowhere" / "eaclog.log"
    assert not missing.exists()

    sources = session_sources(
        layout, log_path=tmp_path / "logs" / "log.txt", extra=[missing]
    )

    assert missing in sources
    # The app log is named too, though nothing has created it.
    assert tmp_path / "logs" / "log.txt" in sources
    # Floor: the list is not simply "everything we were handed and nothing else".
    assert layout.transcript in sources
    assert layout.artifacts in sources
    assert len(sources) >= 4


def test_session_sources_deduplicates_and_keeps_order(tmp_path: Path) -> None:
    """A path named twice is collected once — and the first position wins."""
    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    log_path = tmp_path / "logs" / "log.txt"
    duplicate = tmp_path / "extra.txt"

    sources = session_sources(
        layout,
        log_path=log_path,
        # `layout.artifacts` and `log_path` are already in the list; `duplicate`
        # is named twice by the caller.
        extra=[duplicate, layout.artifacts, duplicate, log_path],
    )

    assert len(sources) == len(set(sources)), "the list contains a duplicate"
    assert sources.count(duplicate) == 1
    assert sources.count(layout.artifacts) == 1
    assert sources.count(log_path) == 1
    # Order: the layout's own paths come first, then the log, then extras.
    assert sources.index(layout.transcript) < sources.index(log_path)
    assert sources.index(log_path) < sources.index(duplicate)


def test_session_sources_finds_log_rotations(tmp_path: Path) -> None:
    """`log.txt.1` and friends are collected; `log.txt.old` is not a rotation."""
    layout = plan_session(home=tmp_path, stamp=STAMP, downloads=None)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_path = log_dir / "log.txt"
    log_path.write_text("current", encoding="utf-8")
    (log_dir / "log.txt.1").write_text("older", encoding="utf-8")
    (log_dir / "log.txt.2").write_text("oldest", encoding="utf-8")
    (log_dir / "log.txt.old").write_text("not a rotation", encoding="utf-8")

    sources = session_sources(layout, log_path=log_path)

    assert log_dir / "log.txt.1" in sources
    assert log_dir / "log.txt.2" in sources
    assert log_dir / "log.txt.old" not in sources


# ---------------------------------------------------------------------------
# finish_session — the archive
# ---------------------------------------------------------------------------


def _prepared(
    tmp_path: Path, *, downloads: Path | None = None
) -> tuple[Path, SessionLayout]:
    """A home with a prepared session in it. Returns (home, layout)."""
    home = tmp_path / "home"
    home.mkdir()
    layout = plan_session(home=home, stamp=STAMP, downloads=downloads)
    prepare_session(layout)
    return home, layout


def test_round_trip_produces_one_archive_with_the_text_artifacts(
    tmp_path: Path,
) -> None:
    """prepare → write → finish: one non-empty file holding what was named."""
    home, layout = _prepared(tmp_path)
    layout.transcript.write_text("step 1: pass\nstep 2: pass\n", encoding="utf-8")
    (layout.artifacts / "report.json").write_text('{"steps": 2}', encoding="utf-8")

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_path = log_dir / "log.txt"
    log_path.write_text("the app log\n", encoding="utf-8")
    (log_dir / "log.txt.1").write_text("the rotated app log\n", encoding="utf-8")

    sources = session_sources(layout, log_path=log_path)
    result = finish_session(
        layout,
        sources=sources,
        embedded_text={"diagnostics.txt": "captured in memory, not from a file"},
    )

    assert result.ok, result.error
    assert result.path is not None
    # The bundler and the planner must agree about the deliverable's name; a
    # "send me this file" instruction that names a path nobody wrote is the
    # failure this relation prevents.
    assert result.path == layout.bundle
    assert layout.bundle.parent == home
    assert layout.bundle.stat().st_size > 0

    members = _members(layout.bundle)
    # THE FLOOR. "no audio present" and "the archive is empty" are the same
    # assertion without one.
    assert len(members) >= 3, members
    assert "MANIFEST.txt" in members
    assert SOURCES_RECORD_NAME in members
    assert "diagnostics.txt" in members
    assert "session/transcript.txt" in members
    assert "session/artifacts/report.json" in members

    # Staged from outside the session folder, including the rotation. Each lands
    # in its own subfolder and KEEPS ITS FILENAME — the bundler judges what may
    # enter by that name, so a rotation renamed on the way in would be refused.
    staged = [n for n in members if n.startswith("session/artifacts/0")]
    assert sorted(n.rsplit("/", 1)[1] for n in staged) == ["log.txt", "log.txt.1"], (
        staged
    )
    log_member = next(n for n in staged if n.endswith("/log.txt"))
    assert "the app log" in _member_text(layout.bundle, log_member)
    assert "step 1: pass" in _member_text(layout.bundle, "session/transcript.txt")


def test_no_audio_can_enter_the_archive_and_the_manifest_says_so(
    tmp_path: Path,
) -> None:
    """Critical rule #8, proved rather than asserted.

    The audio here is a handful of zero bytes generated inside `tmp_path` — never
    a real track, and never anywhere inside the repository.
    """
    _, layout = _prepared(tmp_path)

    album = tmp_path / "Some Album"
    album.mkdir()
    (album / "riplog.log").write_text("track 1 CRC ABCD1234\n", encoding="utf-8")
    (album / "album.cue").write_text('FILE "x" WAVE\n', encoding="utf-8")
    (album / "track01.flac").write_bytes(b"\0" * 8)
    (album / "track02.wav").write_bytes(b"\0" * 8)
    (album / "cover.jpg").write_bytes(b"\0" * 8)

    result = finish_session(layout, sources=[album], embedded_text={})
    assert result.ok, result.error
    assert result.path is not None

    members = _members(result.path)
    # FLOOR FIRST: the text from that same directory really did get in, so the
    # absence of the audio below is about the filter and not about an empty walk.
    assert any(name.endswith("riplog.log") for name in members), members
    assert any(name.endswith("album.cue") for name in members), members

    assert not any(name.endswith(".flac") for name in members), members
    assert not any(name.endswith(".wav") for name in members), members
    # Record-label artwork is refused too: the widened image rule exists only for
    # screenshots this program takes of its own window.
    assert not any(name.endswith(".jpg") for name in members), members

    # AND THE EXCLUSION IS NAMED. A file quietly dropped leaves an archive that
    # reads as complete; the manifest is what makes the omission visible.
    manifest = _member_text(result.path, "MANIFEST.txt")
    assert "track01.flac" in manifest
    assert "track02.wav" in manifest
    assert "cover.jpg" in manifest
    assert "NOT INCLUDED" in manifest
    assert "excluded" in manifest
    assert "NO AUDIO IS PRESENT" in manifest


def test_a_directory_source_is_admitted_under_the_widened_image_rule(
    tmp_path: Path,
) -> None:
    """Pins the one hazard in this module, so it is known rather than latent.

    A directory source travels through ``evidence_bundle``'s ``extra_dirs``
    route, which widens the allowlist to admit `.png` — it exists for folders of
    screenshots this program took of its own window. That is correct for a
    session folder and **wrong for an album folder**, whose `cover.png` is
    record-label artwork.

    Audio is refused on both routes, so Critical rule #8's core is safe either
    way. This test exists so the *difference* is visible in the suite: if the
    routing ever changes, the change shows up here rather than in a bundle.
    """
    _, layout = _prepared(tmp_path)
    screenshots = tmp_path / "scriptrun"
    screenshots.mkdir()
    (screenshots / "step01.png").write_bytes(b"\0" * 8)
    (screenshots / "run.log").write_text("ran\n", encoding="utf-8")
    (screenshots / "track.flac").write_bytes(b"\0" * 8)

    result = finish_session(layout, sources=[screenshots], embedded_text={})
    assert result.ok, result.error
    assert result.path is not None

    members = _members(result.path)
    assert any(name.endswith("run.log") for name in members), members
    assert any(name.endswith("step01.png") for name in members), members
    # Audio never, on any route.
    assert not any(name.endswith(".flac") for name in members), members


def test_an_absent_source_is_named_in_the_record(tmp_path: Path) -> None:
    """The bundler cannot report a file it was never handed. This half can."""
    _, layout = _prepared(tmp_path)
    layout.transcript.write_text("ran\n", encoding="utf-8")
    missing = tmp_path / "nowhere" / "eaclog.log"

    result = finish_session(
        layout,
        sources=[layout.transcript, missing],
        embedded_text={},
    )
    assert result.ok, result.error
    assert result.path is not None

    record = _member_text(result.path, SOURCES_RECORD_NAME)
    assert "eaclog.log" in record
    assert "ABSENT" in record
    # Floor + the counts, so "1 absent" cannot be read off an empty record.
    assert "1 collected" in record
    assert "1 absent" in record


def test_two_sources_with_the_same_filename_both_survive(tmp_path: Path) -> None:
    """Staging must not let one `log.txt` overwrite another — or refuse it.

    This test found a real defect on its first run: the collision was originally
    broken by renaming the second file to `log.txt-1`, which is neither an
    allowed extension nor a recognised rotation, so the bundler dropped it. The
    archive still looked fine. Both halves are asserted below — two members, and
    both *bodies* — because "two files went in" and "two distinct files went in"
    are different claims.
    """
    _, layout = _prepared(tmp_path)
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    (first / "log.txt").write_text("FIRST\n", encoding="utf-8")
    (second / "log.txt").write_text("SECOND\n", encoding="utf-8")

    result = finish_session(
        layout,
        sources=[first / "log.txt", second / "log.txt"],
        embedded_text={},
    )
    assert result.ok, result.error
    assert result.path is not None

    staged = [n for n in _members(result.path) if n.startswith("session/artifacts/")]
    assert len(staged) == 2, staged
    bodies = sorted(_member_text(result.path, name).strip() for name in staged)
    assert bodies == ["FIRST", "SECOND"]


def test_finish_session_returns_an_error_instead_of_raising(tmp_path: Path) -> None:
    """An unwritable destination is a value, never an exception.

    A session that has just spent the night ripping must not lose its evidence to
    a crash in the step that packages it — and a traceback at that moment is
    indistinguishable, to the operator, from the run itself having failed.
    """
    home = tmp_path / "home"
    home.mkdir()
    # A *file* where the archive's directory should be: `mkdir` cannot succeed,
    # and this works the same as root, which a chmod-based test would not.
    blocked = tmp_path / "blocked"
    blocked.write_text("i am a file, not a folder", encoding="utf-8")

    layout = plan_session(home=home, stamp=STAMP, downloads=blocked)
    prepare_session(layout)
    layout.transcript.write_text("ran\n", encoding="utf-8")

    result = finish_session(
        layout, sources=[layout.transcript], embedded_text={}
    )  # must not raise

    assert not result.ok
    assert result.error, "a failure must say what went wrong"
    assert result.path is None
    # The session folder is still there, which is what the failure message tells
    # the operator to fall back to.
    assert layout.root.is_dir()
    assert layout.transcript.is_file()
