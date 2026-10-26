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
(``settings_validation`` portability hazards).

**Name length, closed by the owner's interim (2026-10-26).** A value that made a
folder or file name longer than 255 UTF-8 bytes reached cyanrip, which does not
shorten it (no ``NAME_MAX`` handling in ``cyanrip@eca33dc:src/naming.c``), so the
rip read the track and then failed to create its file. It is now refused before
Start, by the track table and at the argv chokepoint, through one function
(``adapters.cyanrip_name_lengths``), naming the track, the byte count and what to
shorten. That forces the TAG shorter too; the fork shortening only the file name
is the long-term fix, to be asked for in a lap (TASKS R88).
"""

from __future__ import annotations

from typing import Final

import pytest
from hypothesis import given
from hypothesis import strategies as st
from PySide6.QtWidgets import QApplication

from platterpus import naming
from platterpus.adapters import transcode
from platterpus.adapters.cyanrip_backend import (
    CyanripImpl,
    _metadata_args,
    _path_schemes,
)
from platterpus.adapters.cyanrip_name_lengths import (
    OverlongName,
    RipNaming,
    describe,
    overlong_names,
)
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


# --- name length: refused before Start (TASKS R88, the owner's interim) -------

#: The default preset's track template, the shape most rips use.
_TEMPLATE: Final[str] = "%A/%d/%t - %n"

#: On a 12-track disc, track 7's file name is "07 - " + title + ".flac": 10
#: bytes around the title, so a 245-byte title is exactly 255.
_AROUND_THE_TITLE: Final[int] = len(b"07 - ") + len(b".flac")


def _one_track(
    title: str, *, album: str = "Album", artist: str = "Artist"
) -> RipMetadata:
    return RipMetadata(
        album_artist=artist,
        album_title=album,
        tracks=(TrackTag(1, title="Short"), TrackTag(7, title=title)),
    )


def _names(
    meta: RipMetadata,
    *,
    only_tracks: tuple[int, ...] = (),
    derived_extension: str = "",
) -> tuple[OverlongName, ...]:
    return overlong_names(
        _TEMPLATE,
        meta,
        disc_track_total=12,
        only_tracks=only_tracks,
        derived_extension=derived_extension,
    )


def _argv(meta: RipMetadata) -> list[str]:
    return CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="",
        max_retries=5,
        read_offset_override=None,
        track_template=_TEMPLATE,
        metadata=meta,
        disc_track_total=12,
    )


def test_an_overlong_identified_title_IS_refused_before_start() -> None:
    """Was ``test_RESIDUAL_an_overlong_identified_title_is_not_refused_here``.

    90 CJK characters are 270 UTF-8 bytes, so no Linux filesystem can hold the
    file name, and cyanrip found that out only after reading the whole track. The
    path checks still pass it (it is a legal name in every other respect); the
    name-length check refuses it at the argv chokepoint, with a message naming the
    track, the byte count and what to shorten."""
    value = "日" * 90
    assert path_segment_issue("Track 7’s title", value) == ""
    assert _metadata_args(_one_track(value), "")  # the tags alone are fine
    with pytest.raises(RipError) as raised:
        _argv(_one_track(value))
    assert str(raised.value) == (
        "Track 7’s file name would be 280 bytes; the limit is 255 — shorten its title."
    )


def test_an_ordinary_rip_still_builds() -> None:
    """The floor: a check that refused every rip would pass the test above."""
    argv = _argv(_one_track("Black Dog"))
    assert "-F" in argv and "-D" in argv


@pytest.mark.parametrize(("title_bytes", "refused"), [(245, False), (246, True)])
def test_the_limit_is_255_bytes_exactly(title_bytes: int, refused: bool) -> None:
    found = _names(_one_track("a" * title_bytes))
    assert bool(found) is refused
    assert title_bytes + _AROUND_THE_TITLE == (256 if refused else 255)
    if refused:
        assert [(item.track, item.byte_count) for item in found] == [(7, 256)]


@pytest.mark.parametrize(
    ("disc_track_total", "refused"), [(9, False), (12, False), (100, True)]
)
def test_the_track_number_is_padded_as_cyanrip_pads_it(
    disc_track_total: int, refused: bool
) -> None:
    """``{track}`` is "7" on a 9-track disc, "07" on 12, "007" on 100
    (``cyanrip@eca33dc:src/naming.c:239-250``): 254, 255 and 256 bytes here."""
    found = overlong_names(
        _TEMPLATE, _one_track("a" * 245), disc_track_total=disc_track_total
    )
    assert bool(found) is refused


@pytest.mark.parametrize(
    ("title", "on_disk", "refused"),
    [
        ("日" * 81 + "ab", 255, False),  # 243 + 2 bytes: exactly at the limit
        ("日" * 82, 256, True),  # one 3-byte character over
        ("a" * 243 + ":", 256, True),  # 244 bytes typed; cyanrip writes `∶`
        ("a" * 243 + '"', 256, True),  # a quote becomes a 3-byte quote glyph
    ],
)
def test_characters_are_counted_in_bytes_as_cyanrip_writes_them(
    title: str, on_disk: int, refused: bool
) -> None:
    found = _names(_one_track(title))
    assert bool(found) is refused
    rendered = naming.render_scheme(
        "{track} - {title}", {"track": "07", "title": title}
    )
    assert naming.name_bytes_on_disk(rendered + ".flac") == on_disk


@pytest.mark.parametrize(("title_bytes", "refused"), [(244, False), (245, True)])
def test_a_literal_colon_in_the_template_costs_three_bytes(
    title_bytes: int, refused: bool
) -> None:
    """cyanrip sanitises a template's literal text as it does a value
    (``cyanrip@eca33dc:src/naming.c:266-272``), so the ``:`` typed in
    ``%t: %n`` lands as ``∶``. The renderer keeps literal text as typed, so the
    byte count is what has to add the two bytes: "07∶ " is 6 bytes, not 4."""
    found = overlong_names(
        "%A/%d/%t: %n", _one_track("a" * title_bytes), disc_track_total=12
    )
    assert bool(found) is refused
    assert naming.name_bytes_on_disk("07: ") == 6


def test_an_overlong_album_folder_is_refused_naming_the_album_title() -> None:
    found = _names(_one_track("Fine", album="b" * 256))
    folder = [item for item in found if item.kind == "folder"]
    assert len(folder) == 1 and folder[0].byte_count == 256
    assert folder[0].message() == (
        "The album folder’s name would be 256 bytes; the limit is 255 — "
        "shorten the album title."
    )


def test_an_overlong_album_artist_folder_names_the_album_artist() -> None:
    (found,) = _names(_one_track("Fine", artist="c" * 300))
    assert found.kind == "folder" and found.fields == ("the album artist",)


def test_an_album_title_that_fits_as_a_folder_can_overflow_as_the_log() -> None:
    """cyanrip writes ``<album>.log`` and ``<album>.cue`` into the album folder
    (``cyanrip@eca33dc:src/cyanrip_main.c:2355-2356``), so 252 bytes fit as the
    folder and are 256 as the log."""
    found = _names(_one_track("Fine", album="d" * 252))
    assert [(item.kind, item.byte_count) for item in found] == [("log", 256)]
    assert found[0].message() == (
        "The rip log’s file name would be 256 bytes; the limit is 255 — "
        "shorten the album title."
    )


def test_every_overlong_name_is_counted_in_the_message() -> None:
    meta = RipMetadata(
        album_artist="A",
        album_title="B",
        tracks=tuple(TrackTag(n, title="日" * 90) for n in (1, 2, 3)),
    )
    found = _names(meta)
    assert [item.track for item in found] == [1, 2, 3]
    assert describe(found).endswith(
        "2 more names are too long as well; each is listed in the log."
    )


def test_only_the_tracks_being_ripped_are_checked() -> None:
    """An unticked track is never created, so its long title cannot fail a rip."""
    meta = _one_track("日" * 90)
    assert _names(meta, only_tracks=(1,)) == ()
    assert [item.track for item in _names(meta, only_tracks=(7,))] == [7]


def test_a_derived_extension_is_measured_and_none_is_longer_than_flac() -> None:
    """The argv chokepoint measures ``.flac`` only, because it does not know the
    derived format; that is sound only while no derived extension is longer."""
    for fmt in transcode.SUPPORTED_FORMATS:
        ext = transcode.extension_for(fmt)
        assert ext is not None and len(ext) <= len("flac"), fmt
    at_limit = _one_track("a" * 245)
    assert _names(at_limit) == ()
    assert _names(at_limit, derived_extension="mp3") == ()
    (longer,) = _names(at_limit, derived_extension="flacx")
    assert longer.byte_count == 256 and longer.name.endswith(".flacx")


def test_an_unknown_disc_keeps_its_own_capped_folder() -> None:
    """The unknown-disc path is ours: ``_as_unknown_params`` builds the folder
    from ``safe_path_segment``, already capped at 255 bytes, so however long the
    typed title, its folder and track names are never refused."""
    segment = safe_path_segment("日" * 200)  # 600 bytes typed
    assert len(segment.encode("utf-8")) == 255
    template = f"{segment}/{segment}/%t - Track %t"
    assert overlong_names(template, RipMetadata(), disc_track_total=12) == ()


def test_the_track_table_refuses_an_overlong_title_before_start(
    qapp: QApplication,
) -> None:
    from test_ui_track_table import _detail

    from platterpus.ui.track_table import TrackTable

    widget = TrackTable()
    widget.set_release(_detail())
    meta = RipMetadata(
        album_artist="Pink Floyd",
        album_title="Dark Side",
        tracks=(TrackTag(1, title="Speak to Me"), TrackTag(2, title="日" * 90)),
    )
    ok, message = widget.validate(RipNaming(_TEMPLATE, meta, disc_track_total=12))
    assert ok is False
    assert message == (
        "Track 2’s file name would be 280 bytes; the limit is 255 — shorten its title."
    )
    fine = RipMetadata(album_title="Dark Side", tracks=(TrackTag(2, title="Breathe"),))
    assert widget.validate(RipNaming(_TEMPLATE, fine, disc_track_total=12)) == (
        True,
        "",
    )


#: Text with every kind of character the byte count treats differently: ASCII,
#: a substituted character, a quote, a separator, 2-, 3- and 4-byte UTF-8, a
#: control character and a lone surrogate.
_TEXT: Final[st.SearchStrategy[str]] = st.text(
    alphabet=st.sampled_from(list('aZ 9:/"\\<.éß日😀\x00\ud800')), max_size=150
)


@given(title=_TEXT, album=_TEXT, artist=_TEXT, year=_TEXT, template=st.text())
def test_the_check_never_raises(
    title: str, album: str, artist: str, year: str, template: str
) -> None:
    meta = RipMetadata(
        album_artist=artist,
        album_title=album,
        year=year,
        tracks=(TrackTag(1, title=title, artist=artist),),
    )
    found = overlong_names(template, meta)
    assert all(item.byte_count > naming.NAME_MAX_BYTES for item in found)
    assert isinstance(describe(found), str)


@given(title=_TEXT)
def test_the_check_agrees_with_the_renderer(title: str) -> None:
    """Track 7's verdict is exactly: does the renderer's name, measured as cyanrip
    writes it, exceed 255 bytes. Rendered here from the scheme the argv sends."""
    meta = _one_track(title)
    _folder, file_scheme = _path_schemes(_TEMPLATE, meta, (1, 1))
    assert file_scheme is not None
    tags = {"track": "07", "album": "Album", "album_artist": "Artist"}
    tags["artist"] = "Artist"
    if title:
        tags["title"] = title
    expected = naming.name_bytes_on_disk(
        naming.render_scheme(file_scheme, tags) + ".flac"
    )
    flagged = [item for item in _names(meta) if item.track == 7]
    assert bool(flagged) is (expected > naming.NAME_MAX_BYTES)
    if flagged:
        assert flagged[0].byte_count == expected
