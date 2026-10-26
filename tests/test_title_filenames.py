"""Filenames built from titles: no value can leave the library folder.

Peer review 2.7 (the claude-code-skills session, 2026-10-26). Where the guarantee
lives, because there are three sanitisers and each covers a different route:

* **cyanrip renders the identified-disc path.** We hand it ``-D``/``-F`` naming
  schemes and the tag values, and it substitutes each value with ``/`` -> ``∕``
  and the other path-illegal characters swapped for look-alikes
  (``cyanrip@eca33dc:src/naming.c:132-218``). It maps nothing for ``.`` or
  ``..``, which is why we refuse those ourselves.
* **We refuse what cyanrip would turn into a directory reference** before argv
  exists (``cyanrip_backend._reject_path_reference_values``, through
  ``settings_validation.path_segment_issue``), and the track table refuses the
  same with a specific message before Start (``TrackTable.validate``).
* **The unknown-album path is ours end to end**, built into the template
  literally by ``main_window_helpers.safe_path_segment`` (``/`` -> ``-``, control
  characters dropped, 255-byte cap, ``.``/``..`` refused).

**Found by this file, and fixed:** the album YEAR. ``%y`` is cyanrip's
``{date}`` token, rendered from the ``date=`` tag we send, which is the Year box
above the track table, typed freely. ``%Y`` had been made digits-only
(``_year_token``, 2026-07-28), but ``%y`` sends the value whole, and the year was
checked for neither. A year of ``..`` with a custom template ``%y/%A/%d/%t - %n``
put the album one folder above the output directory. Now the year is refused
when it is a directory reference, at both checks, like the four fields that
always were.

**What this deliberately does not do**, written down rather than scoped away
(TASKS R88): a leading dot (``.hidden``) is a hidden folder INSIDE the library,
not an escape; a Windows-reserved name (``CON``, ``a?b``) is legal on the Linux
target and a template's own literal text already warns about it
(``settings_validation`` portability hazards); and a value longer than 255 UTF-8
bytes reaches cyanrip, which does not shorten it (no ``NAME_MAX`` handling in
``cyanrip@eca33dc:src/naming.c``), so that rip fails at file creation rather than
before Start. Refusing it would force the TAG shorter too; that choice is the
maintainer's.
"""

from __future__ import annotations

from typing import Final

import pytest
from hypothesis import given
from hypothesis import strategies as st
from PySide6.QtWidgets import QApplication

from platterpus.adapters.cyanrip_backend import _metadata_args
from platterpus.adapters.rip_backend import RipError, RipMetadata, TrackTag
from platterpus.naming import PRESETS, SampleTrack, render_preview
from platterpus.settings_validation import path_segment_issue
from platterpus.ui.main_window_helpers import safe_path_segment

#: Values that must each land as ONE path segment, inside the library.
_HOSTILE_BUT_ONE_SEGMENT: Final[tuple[str, ...]] = (
    "../x",
    "../../etc/passwd",
    "/root",
    "a/b/c",
    "..\\..\\x",
    ".hidden",
    "...",
    "CON",
    "a?b*c|d",
)


def _sample(value: str) -> SampleTrack:
    return SampleTrack(
        album_artist=value,
        track_artist=value,
        album=value,
        title=value,
        track=1,
        track_total=9,
        date="2020",
    )


def _segments(path: str) -> list[str]:
    return path.split("/")


# --- the identified-disc route: what we refuse, and what cyanrip maps ---------


@pytest.mark.parametrize("value", _HOSTILE_BUT_ONE_SEGMENT)
def test_a_hostile_title_that_we_PASS_lands_as_one_segment(value: str) -> None:
    """Passed by our check, then rendered the way cyanrip renders it (the preview
    mirrors its table): every preset keeps exactly its own folder depth."""
    assert path_segment_issue("Album title", value) == ""
    for preset in PRESETS:
        for template in (preset.track_template, preset.disc_template):
            rendered = render_preview(template, _sample(value))
            assert len(_segments(rendered)) == len(_segments(template)), (
                template,
                rendered,
            )
            assert not {".", ".."} & set(_segments(rendered)), rendered
            assert not rendered.startswith("/")


@pytest.mark.parametrize("value", [".", "..", " .. ", "\t.\t", "a\nb", "x\x00y"])
def test_what_cyanrip_would_NOT_map_is_refused_before_argv(value: str) -> None:
    for field in ("album_title", "album_artist"):
        meta = RipMetadata(**{field: value})  # type: ignore[arg-type]  # one str field
        with pytest.raises(RipError):
            _metadata_args(meta, "")
    for track in (TrackTag(1, title=value), TrackTag(1, title="T", artist=value)):
        with pytest.raises(RipError):
            _metadata_args(RipMetadata(album_title="A", tracks=(track,)), "")


@given(st.text(max_size=30))
def test_ANY_title_our_check_passes_keeps_the_folder_depth(value: str) -> None:
    """The property behind the table above, over every string."""
    if path_segment_issue("Album title", value) or not value.strip():
        return
    rendered = render_preview("%A/%d/%t - %n", _sample(value))
    segments = _segments(rendered)
    assert len(segments) == 3
    assert not {".", ".."} & set(segments)


# --- the year: found by this review, and fixed --------------------------------


@pytest.mark.parametrize("year", ["..", ".", " .. "])
def test_a_YEAR_that_is_a_directory_reference_is_refused(year: str) -> None:
    """``%y`` is cyanrip's ``{date}``: the year reaches the path verbatim."""
    meta = RipMetadata(album_artist="A", album_title="B", year=year)
    with pytest.raises(RipError, match="Year"):
        _metadata_args(meta, "")


def test_an_ordinary_year_still_passes() -> None:
    """The floor: a check that refused every year would pass the test above."""
    for year in ("1971", "1971-11-08", "", "c. 1971"):
        args = _metadata_args(RipMetadata(album_title="B", year=year), "")
        assert args, year


def test_the_track_table_refuses_a_directory_reference_year(qapp: QApplication) -> None:
    from test_ui_track_table import _detail

    from platterpus.ui.track_table import TrackTable

    widget = TrackTable()
    widget.set_release(_detail())
    widget._album_year_edit.setText("..")
    ok, message = widget.validate()
    assert ok is False and "Year" in message
    assert "outside your output directory" in message
    widget._album_year_edit.setText("1971")
    assert widget.validate() == (True, "")


# --- the unknown-album route: ours end to end ---------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("../x", "..-x"),
        ("/etc/passwd", "-etc-passwd"),
        ("..", ""),
        (".", ""),
        ("a\nb", "ab"),
        (".hidden", ".hidden"),
    ],
)
def test_the_unknown_album_segment(value: str, expected: str) -> None:
    assert safe_path_segment(value) == expected


def test_an_overlong_unknown_album_title_is_capped_on_a_codepoint() -> None:
    capped = safe_path_segment("日" * 200)  # 600 UTF-8 bytes
    assert len(capped.encode("utf-8")) <= 255 and capped == "日" * 85


# --- the residual, pinned (TASKS R88) -----------------------------------------


def test_RESIDUAL_an_overlong_identified_title_is_not_refused_here() -> None:
    """Over 255 bytes, so no filesystem can hold it as one name; it still passes
    our check and reaches cyanrip, which does not shorten it. Pinned so the gap
    stays visible until the maintainer chooses refuse, warn, or shorten."""
    value = "日" * 90  # 270 UTF-8 bytes
    assert path_segment_issue("Album title", value) == ""
    assert _metadata_args(RipMetadata(album_title=value), "")
