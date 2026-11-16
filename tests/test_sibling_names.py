"""The name-length check leaves room for every file we name from cyanrip's (TASKS R88).

The gap this closes, measured 2026-11-16: the before-Start check let a name of
up to 255 bytes through, and Platterpus then writes files BESIDE that name with
longer endings (``<track>.flac.platterpus-refix.tmp``, ``<album> (EAC-compatible).log``
and more), which fail with ``ENAMETOOLONG``. A track name of 235 to 255 bytes
broke the securing pass's swap; a log name of 231 to 255 broke the sidecars.

These tests create REAL files in ``tmp_path``: a name exactly at the check's
limit must let every sibling be created; one byte more must be refused by the
check (and is shown to break a sibling, which is why the check refuses it).
"""

from __future__ import annotations

import ast
import errno
import os
from pathlib import Path
from typing import Final

import pytest

from platterpus import naming, rip_addendum, rip_report, sibling_names
from platterpus.adapters import transcode
from platterpus.adapters.cyanrip_name_lengths import overlong_names
from platterpus.adapters.rip_backend import RipMetadata, TrackTag
from platterpus.ctdb import repair_commit
from platterpus.verified_read_chase import chase_log_path_for

_SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"
_TEMPLATE: Final[str] = "%A/%d/%t - %n"
#: "07 - " before the title on track 7 of a 12-track disc.
_PREFIX: Final[str] = "07 - "


def _name_max(folder: Path) -> int:
    """The filesystem's own per-name limit where the test writes."""
    try:
        return os.pathconf(folder, "PC_NAME_MAX")
    except (OSError, ValueError):
        return -1


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    # The boundary means something only where the filesystem's limit is the one
    # the check assumes. Every Linux filesystem a library lives on says 255.
    if _name_max(tmp_path) != naming.NAME_MAX_BYTES:
        pytest.skip(f"tmp_path's NAME_MAX is {_name_max(tmp_path)}, not 255")
    return tmp_path


def _create(folder: Path, name: str) -> None:
    (folder / name).write_bytes(b"")


def _track_names(title: str) -> tuple[str, ...]:
    """Every file a rip makes from track 7's name: the FLAC, its siblings, and
    each derived format with its own siblings."""
    flac = f"{_PREFIX}{title}.flac"
    names = [flac, *sibling_names.master_siblings(flac)]
    for fmt in sorted(transcode.SUPPORTED_FORMATS):
        ext = transcode.extension_for(fmt)
        assert ext is not None
        derived = f"{_PREFIX}{title}.{ext}"
        names += [derived, *sibling_names.derived_siblings(derived)]
    return tuple(names)


def _track_check(title: str) -> bool:
    """Whether the check refuses track 7 with this title (FLAC + every format)."""
    meta = RipMetadata(
        album_artist="A", album_title="B", tracks=(TrackTag(7, title=title),)
    )
    refused = bool(overlong_names(_TEMPLATE, meta, disc_track_total=12))
    for fmt in transcode.SUPPORTED_FORMATS:
        ext = transcode.extension_for(fmt) or ""
        refused |= bool(
            overlong_names(_TEMPLATE, meta, disc_track_total=12, derived_extension=ext)
        )
    return refused


def _longest_title_that_passes() -> str:
    """Found by asking the check, not by arithmetic: the boundary is the check's."""
    title = ""
    while not _track_check(title + "a"):
        title += "a"
        assert len(title) < 400, "the check never refused a track name"
    return title


def test_a_track_name_the_check_passes_can_have_every_sibling(folder: Path) -> None:
    title = _longest_title_that_passes()
    names = _track_names(title)
    for name in names:
        _create(folder, name)
    # Non-trivial: the passing name is close enough to 255 that the margin matters.
    longest = max(len(n.encode()) for n in names)
    assert longest == naming.NAME_MAX_BYTES, longest
    assert len(os.listdir(folder)) == len(names) >= 10


def test_one_byte_more_is_refused_and_would_break_a_sibling(folder: Path) -> None:
    title = _longest_title_that_passes() + "a"
    assert _track_check(title)
    flac = f"{_PREFIX}{title}.flac"
    _create(folder, flac)  # cyanrip itself could still write it
    with pytest.raises(OSError) as raised:
        _create(folder, sibling_names.refix_temp_name(flac))
    assert raised.value.errno == errno.ENAMETOOLONG


def _log_check(album: str) -> bool:
    meta = RipMetadata(album_artist="A", album_title=album, tracks=(TrackTag(1),))
    return any(
        item.kind == "log"
        for item in overlong_names("%A/%t - %n", meta, disc_track_total=1)
    )


def test_a_log_name_the_check_passes_can_have_every_sidecar(folder: Path) -> None:
    album = ""
    while not _log_check(album + "d"):
        album += "d"
        assert len(album) < 400, "the check never refused a log name"
    log_name = f"{album}.log"
    names = (log_name, f"{album}.cue", *sibling_names.log_siblings(log_name))
    for name in names:
        _create(folder, name)
    assert max(len(n.encode()) for n in names) == naming.NAME_MAX_BYTES
    # One byte more: refused, and its longest sidecar could not be created.
    longer = f"{album}d.log"
    assert _log_check(album + "d")
    _create(folder, longer)
    with pytest.raises(OSError) as raised:
        _create(folder, sibling_names.securing_pass_log_name(longer))
    assert raised.value.errno == errno.ENAMETOOLONG


def test_the_writers_build_their_names_through_this_module() -> None:
    """The relation, not either side: each writer's name for a sibling is the one
    the check measured. A writer that spelled its own ending would pass the sweep
    below only if it reused the constant, and this pins that it does."""
    log = Path("/m/Album.log")
    flac = Path("/m/07 - T.flac")
    log_names = set(sibling_names.log_siblings(log.name))
    assert rip_addendum.addendum_path_for(log).name in log_names
    assert rip_addendum.securing_pass_log_path_for(log).name in log_names
    assert chase_log_path_for(log).name in log_names
    assert rip_report.report_path_for(log).name in log_names
    master = set(sibling_names.master_siblings(flac.name))
    assert repair_commit.candidate_path(flac).name in master
    assert repair_commit.backup_path(flac).name in master


#: Every ending this module defines: the population the sweep below looks for.
_ENDINGS: Final[frozenset[str]] = frozenset(
    value
    for key, value in vars(sibling_names).items()
    if key.endswith(("_SUFFIX", "_PREFIX"))
    and isinstance(value, str)
    and len(value) > 1
)


def test_no_module_spells_an_ending_of_its_own() -> None:
    """A copy of an ending elsewhere is a name the check does not know about.

    Looks for a string literal (or an f-string's literal part) EQUAL to an
    ending, so prose that mentions one is not flagged. ``.tmp`` and the one-dot
    prefix are too common to sweep for and are left out (``len(value) > 1`` and
    the ``.tmp`` check below); their writers are pinned by the test above."""
    endings = _ENDINGS - {sibling_names.ATOMIC_TEMP_SUFFIX}
    assert len(endings) >= 10, sorted(endings)
    examined = 0
    stray: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        if path.name == "sibling_names.py":
            continue
        examined += 1
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in endings:
                stray.append(f"{path.relative_to(_SRC)}:{node.lineno} {node.value!r}")
    assert examined >= 300, examined
    assert not stray, stray


def test_every_name_helper_is_measured_by_the_check() -> None:
    """Every ``*_name`` helper a writer can call builds a name that is in one of
    the lists the margins are derived from, so no writer can create a sibling
    the check left no room for. (The JSON report is the probe for
    ``atomic_temp_name``: it is the one file written atomically beside a log.)"""
    measured = (
        set(sibling_names.master_siblings("x.flac"))
        | set(sibling_names.derived_siblings("x.mp3"))
        | set(sibling_names.log_siblings("x.log"))
    )
    helpers = {
        key: value
        for key, value in vars(sibling_names).items()
        if key.endswith("_name") and callable(value)
    }
    assert len(helpers) >= 10, sorted(helpers)
    probes = ("x.flac", "x.mp3", "x.log", sibling_names.report_name("x.log"))
    unmeasured = [
        key
        for key, helper in helpers.items()
        if not any(helper(probe) in measured for probe in probes)
    ]
    assert not unmeasured, unmeasured
