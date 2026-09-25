"""Tests for platterpus.naming — the file-naming presets + preview renderer."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import naming


def test_default_preset_is_clean_artist_album_track_title() -> None:
    # The recommended default must be the clean layout, not the old cluttered
    # one that repeated album/artist and trailed the date.
    assert naming.DEFAULT_PRESET is naming.PRESETS[0]
    assert naming.DEFAULT_PRESET.track_template == "%A/%d/%t - %n"


def test_preset_for_templates_matches_and_rejects() -> None:
    p = naming.DEFAULT_PRESET
    assert naming.preset_for_templates(p.track_template, p.disc_template) is p
    # A hand-edited template matches no preset → Custom (None).
    assert naming.preset_for_templates("%A/%n", "%A/%d/%d") is None


def test_render_preview_clean_template() -> None:
    out = naming.render_preview("%A/%d/%t - %n", naming.SAMPLE_EASY)
    assert out == "Led Zeppelin/Led Zeppelin IV/01 - Black Dog.flac"


def test_render_preview_zero_pads_track_to_disc_width() -> None:
    # 15-track disc → 2-digit width; track 3 → "03".
    out = naming.render_preview("%t", naming.SAMPLE_STRESS)
    assert out == "03.flac"


def test_render_preview_sanitises_colon_in_value_not_separator() -> None:
    # A ":" inside the album value becomes cyanrip's "∶"; the template's own
    # "/" stays a real path separator.
    out = naming.render_preview("%A/%d", naming.SAMPLE_STRESS)
    assert "Riding with the King∶ Deluxe Edition" in out
    assert ":" not in out
    # Two real separators (one from the template, plus the .flac has none).
    assert out.count("/") == 1


def test_render_preview_year_token_is_full_date_today() -> None:
    # %y resolves to the full date (cyanrip's {date}), not a bare year.
    out = naming.render_preview("%d (%y)", naming.SAMPLE_EASY)
    assert "(1971-11-08)" in out


def test_render_preview_capital_year_token_is_year_only() -> None:
    # %Y (Platterpus-only) is the 4-digit year, distinct from %y's full date.
    out = naming.render_preview("%d (%Y)", naming.SAMPLE_EASY)
    assert "(1971)" in out
    assert "1971-11-08" not in out
    # And it works when the release date is already year-only.
    out2 = naming.render_preview(
        "%Y", naming.SampleTrack("A", "A", "D", "T", 1, 1, "1980")
    )
    assert out2 == "1980.flac"


def test_year_presets_use_year_only_token() -> None:
    # The two year-in-folder presets switched from %y to %Y in v4, so a folder
    # reads "Album (1971)", never the full date.
    for key in ("artist_album_year_track_title", "artist_year_album_track_title"):
        preset = next(p for p in naming.PRESETS if p.key == key)
        assert "%Y" in preset.track_template
        assert "%y" not in preset.track_template
        out = naming.render_preview(preset.track_template, naming.SAMPLE_EASY)
        assert "1971-11-08" not in out
        assert "1971" in out


def test_render_preview_compilation_uses_track_artist() -> None:
    out = naming.render_preview("%t - %a - %n", naming.SAMPLE_STRESS)
    assert "Eric Clapton feat. B.B. King" in out


@pytest.mark.parametrize(
    "template",
    ["", "%", "%%", "%z", "%A/%z/%", "no codes at all", "%t%n%d%a%A%y"],
)
def test_render_preview_never_raises(template: str) -> None:
    # It backs a live preview as the user types — it must never raise, on any
    # input, and always end in .flac.
    out = naming.render_preview(template, naming.SAMPLE_EASY)
    assert out.endswith(".flac")


# The 7 examples above pin the known-interesting shapes; this fuzzes the whole
# input space. render_preview backs a LIVE preview updated on every keystroke,
# so its docstring promises it NEVER raises — a crash here would take the
# Settings dialog down mid-type. Hypothesis throws arbitrary text (lone/trailing
# "%", stray tokens, control chars, odd Unicode) and shrinks any crash to a
# minimal reproducer. text() draws the full unicode range by default, so a "%"
# followed by any codepoint — including an astral/surrogate one — is exercised.
@given(template=st.text(max_size=200))
@settings(max_examples=300, deadline=None)
def test_render_preview_never_raises_property(template: str) -> None:
    out = naming.render_preview(template, naming.SAMPLE_STRESS)
    assert isinstance(out, str)
    assert out.endswith(".flac")


def test_render_preview_literal_percent() -> None:
    assert naming.render_preview("100%%", naming.SAMPLE_EASY) == "100%.flac"


def test_render_preview_unknown_token_passes_through() -> None:
    # An unknown %z stays visible (so a typo is obvious), rather than vanishing.
    assert naming.render_preview("%z", naming.SAMPLE_EASY) == "%z.flac"


def test_every_preset_renders_for_both_samples() -> None:
    for preset in naming.PRESETS:
        for sample in (naming.SAMPLE_EASY, naming.SAMPLE_STRESS):
            out = naming.render_preview(preset.track_template, sample)
            assert out.endswith(".flac")
            assert "%" not in out  # every token in a shipped preset resolves


def test_custom_label_is_not_a_preset_key() -> None:
    # The Custom sentinel must never collide with a real preset (else selecting
    # it would overwrite the user's hand-tuned templates).
    assert all(p.label != naming.CUSTOM_LABEL for p in naming.PRESETS)


# --- The value sanitiser, fuzzed on the VALUE --------------------------------
#
# `test_render_preview_never_raises_property` above fuzzes the TEMPLATE and holds
# the sample fixed, so `_sanitise_value` only ever saw the eight or so characters
# SAMPLE_STRESS happens to contain. These fuzz the value itself, and assert what
# the sanitiser is FOR rather than that it returns:
#
#  * it is a character-for-character map — a path-illegal character becomes its
#    look-alike, every other character is untouched, and nothing is dropped or
#    added (the overwrite guard lines a predicted name up against the one on
#    disk position by position, so a length change would misalign the match);
#  * no table key survives it, so a "/" inside a tag value can never become a
#    folder separator in the preview;
#  * it is idempotent — a look-alike is never itself rewritten.

#: A value dense in the characters the table exists for, so a draw reaches the
#: substitution branch constantly rather than once in a few hundred.
_TAG_VALUE = st.one_of(
    st.text(max_size=40),
    st.text(alphabet="".join(naming._VALUE_SANITISE) + "ab ‹∶", max_size=40),
)


@given(value=_TAG_VALUE)
@settings(max_examples=300, deadline=None)
def test_sanitise_value_is_a_character_for_character_map(value: str) -> None:
    out = naming._sanitise_value(value)
    assert len(out) == len(value)
    for before, after in zip(value, out, strict=True):
        assert after == naming._VALUE_SANITISE.get(before, before), (before, after)
    assert not set(out) & set(naming._VALUE_SANITISE), out
    assert naming._sanitise_value(out) == out


def test_the_value_sanitiser_property_reaches_every_table_row() -> None:
    """Floor: the whole table in one value, so no row can be skipped unseen."""
    every_key = "".join(naming._VALUE_SANITISE)
    assert len(every_key) >= 8, "the table shrank — re-derive it from P7b"
    out = naming._sanitise_value(every_key)
    assert out == "".join(naming._VALUE_SANITISE.values())


@st.composite
def _sample_track(draw: st.DrawFn) -> naming.SampleTrack:
    """A sample whose every value is drawn — non-empty, as the real samples are."""
    text = _TAG_VALUE.filter(bool)
    total = draw(st.integers(min_value=1, max_value=999))
    return naming.SampleTrack(
        album_artist=draw(text),
        track_artist=draw(text),
        album=draw(text),
        title=draw(text),
        track=draw(st.integers(min_value=1, max_value=total)),
        track_total=total,
        date=draw(text),
    )


@given(
    sample=_sample_track(),
    tokens=st.lists(st.sampled_from(["%A", "%a", "%d", "%n", "%y", "%t"]), min_size=1),
)
@settings(max_examples=200, deadline=None)
def test_a_tag_value_never_adds_or_removes_a_folder_level(
    sample: naming.SampleTrack, tokens: list[str]
) -> None:
    """The template's own "/" are the only separators in the preview.

    A value carrying "/" (an album called "AC/DC Live") must render as ONE
    segment, or the preview shows a folder the rip will not create.
    """
    template = "/".join(tokens)
    out = naming.render_preview(template, sample)
    assert out.count("/") == template.count("/"), (template, out)
    # And each segment is exactly that token's sanitised value, in order.
    assert out.removesuffix(".flac").split("/") == [
        sample.value_for(token[1]) for token in tokens
    ]
