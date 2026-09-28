"""Tests for platterpus.naming — the file-naming presets + preview renderer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import naming
from platterpus.adapters.cyanrip_backend import SANITISE_MODE


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


def test_the_preview_fills_in_the_DISC_codes() -> None:
    """Decision 3A: `%N`/`%M` render as the disc's place in its set."""
    sample = naming.SampleTrack(
        album_artist="A",
        track_artist="A",
        album="B",
        title="T",
        track=1,
        track_total=9,
        date="2001",
        disc=2,
        disc_total=3,
    )
    assert naming.render_preview("CD %N of %M/%t", sample) == "CD 2 of 3/01.flac"
    # A single disc is 1 of 1 by default, as the backend sends it.
    assert naming.render_preview("%N-%M", naming.SAMPLE_EASY) == "1-1.flac"


def test_the_preview_writes_a_BRACE_the_way_the_file_gets_it() -> None:
    """The backend turns a typed `{`/`}` into parentheses, because `{...}` is
    cyanrip's substitution syntax. The preview showed the brace the real file
    never gets."""
    assert naming.render_preview("a{b}/%{c", naming.SAMPLE_EASY) == "a(b)/%(c.flac"


@settings(max_examples=150, deadline=None)
@given(
    st.integers(min_value=1, max_value=99).flatmap(
        lambda total: st.tuples(
            st.integers(min_value=1, max_value=total), st.just(total)
        )
    ),
    # Letters that are not codes, so only the codes Platterpus fills in itself
    # (and literal braces) are in play; cyanrip fills in the rest at rip time.
    st.text(alphabet="xz {}%NM-/", max_size=16),
)
def test_the_preview_and_the_rip_AGREE_on_disc_codes_and_braces(
    position: tuple[int, int], template: str
) -> None:
    """One question, two surfaces: what does this template write? For the codes
    Platterpus fills in itself (`%N`, `%M`) and for literal braces, the preview
    and the scheme handed to cyanrip must give the same text."""
    from platterpus.adapters.cyanrip_backend import scheme_from_template

    disc, total = position
    sample = naming.SampleTrack(
        album_artist="A",
        track_artist="A",
        album="B",
        title="T",
        track=1,
        track_total=9,
        date="2001",
        disc=disc,
        disc_total=total,
    )
    preview = naming.render_preview(template, sample)
    if template.endswith("%") and not template.endswith("%%"):
        return  # a trailing bare % is kept by both, handled elsewhere
    scheme = scheme_from_template(template, disc=str(disc), discs=str(total))
    assert preview == scheme + ".flac"


# --- The value table against the contract it says it was read from -----------
#
# `naming._VALUE_SANITISE` documents itself as READ OUT OF the fork's generated
# provider contract, section P7b — "derived, not observed". Nothing compared the
# two (TASKS `fuzz:naming._VALUE_SANITISE`), so that sentence described how the
# table was once written rather than checking that it still agrees. These tests
# parse P7b out of the newest filed contract and hold ours to it.
#
# Parsed, never hand-copied: P7 itself says "a hand-copied second copy of the
# table inside a generated document is the failure this generator exists to
# prevent", and a hand-copied copy inside a TEST would be the same failure one
# level down — a list checked against itself is consistent, not verified.


@dataclass(frozen=True)
class P7bRow:
    """One row of P7b, as the contract states it (markdown escapes removed)."""

    index: int
    #: The character cyanrip replaces, e.g. ``"<"``.
    character: str
    #: What the ``simple`` mode writes for it (an ASCII stand-in).
    simple: str
    #: What the ``unicode`` mode writes for it (a look-alike glyph).
    unicode: str


_P7B_HEADING: Final[str] = "### P7b - The substitution table"

#: The column header the row regex below is written against. Checked verbatim
#: first, so a contract that adds, drops or reorders a column fails LOUDLY
#: instead of having its cells silently read under the wrong names.
_P7B_HEADER: Final[str] = (
    "| # | character | codepoint | `simple` writes | `unicode` writes "
    "| codepoint | availability macro |"
)

#: One fenced single-character cell. A markdown table spells a literal ``|``
#: inside a cell as ``\|``, so that is the one two-character form allowed.
_P7B_GLYPH: Final[str] = r"`(?:\\\||[^`|])`"

_P7B_ROW: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*(?P<index>\d{1,3})\s*"
    rf"\|\s*(?P<char>{_P7B_GLYPH})\s*"
    r"\|\s*`U\+(?P<cp>[0-9A-F]{4,6})`\s*"
    rf"\|\s*(?P<simple>{_P7B_GLYPH})\s*"
    rf"\|\s*(?P<unicode>{_P7B_GLYPH})\s*"
    r"\|\s*`U\+(?P<ucp>[0-9A-F]{4,6})`\s*"
    r"\|\s*`HAS_[A-Z_]{1,40}`\s*\|\s*$"
)

#: Floor on the parse. Every contract since P7 first shipped (round 13 lap 1)
#: has published ten rows — nine characters, `"` twice — measured across all
#: fifteen filed contracts that carry a P7b, up to round 28 lap 3. Fewer means
#: the parser stopped matching, not that cyanrip substitutes less.
_MIN_P7B_ROWS: Final[int] = 10

#: Floor on the COMPARISON: how many characters must actually be checked
#: against our table. Measured 8 (every P7b character but `"`). Without it an
#: empty parse and an empty table would agree with each other perfectly.
_MIN_COMPARED: Final[int] = 8


def _unfence(cell: str) -> str:
    """``"`\\|`"`` -> ``"|"``, ``"`<`"`` -> ``"<"``."""
    return cell[1:-1].replace("\\|", "|")


def _newest_provider_contract() -> Path:
    """The newest filed inbound provider contract, by (round, lap).

    Read through the ONE ordering the suite already has (and tests) rather than
    a new copy of it: a second round parser here would be the fifth, and the
    earlier four broke on the 2026-08-04 file renaming.
    """
    import test_ripper_error_surfacing as surfacing  # noqa: PLC0415

    contracts = surfacing._newest_provider_contracts()
    assert contracts, (
        "no inbound provider-contract artifact is committed, so there is nothing "
        "to derive the substitution table from — this check would otherwise pass "
        "by finding nothing"
    )
    return contracts[0][1]


def p7b_rows(text: str) -> list[P7bRow]:
    """Every row of P7b in one contract's text, in source order.

    Refuses rather than guesses: a missing section, a changed header, or a table
    line the row pattern cannot read all FAIL, because each would otherwise shrink
    the population silently and read as agreement. Public (no underscore) because
    `test_main_window_helpers_match_rule.py` fuzzes the overwrite guard over the
    same table, and one parser is the point.
    """
    assert _P7B_HEADING in text, (
        "the contract has no P7b section — our value table has nothing to be "
        "derived from any more, and that is a seam change to read, not skip"
    )
    section = text[text.index(_P7B_HEADING) + len(_P7B_HEADING) :]
    # P7b ends where the next heading of any level begins (P7c follows it).
    end = re.search(r"^#{2,3} ", section, re.MULTILINE)
    if end is not None:
        section = section[: end.start()]
    lines = section.splitlines()
    assert _P7B_HEADER in lines, (
        "P7b's column header changed; re-read which column is which before "
        f"trusting this parse. Expected:\n  {_P7B_HEADER}"
    )
    rows: list[P7bRow] = []
    for line in lines[lines.index(_P7B_HEADER) + 1 :]:
        if not line.startswith("|"):
            break  # the table ended; the prose after it is not ours to read
        if re.fullmatch(r"\|(?:\s*-{3,}\s*\|)+", line):
            continue  # the |---|---| separator
        match = _P7B_ROW.match(line)
        assert match is not None, f"a P7b row this parser cannot read: {line!r}"
        row = P7bRow(
            index=int(match.group("index")),
            character=_unfence(match.group("char")),
            simple=_unfence(match.group("simple")),
            unicode=_unfence(match.group("unicode")),
        )
        # TWO READINGS OF ONE ROW, which is what makes the unescaping above
        # checkable: the codepoint columns state the same characters in a form
        # markdown cannot mangle. A `\|` mis-read fails here, not later.
        assert ord(row.character) == int(match.group("cp"), 16), line
        assert ord(row.unicode) == int(match.group("ucp"), 16), line
        rows.append(row)
    return rows


def newest_p7b() -> tuple[Path, list[P7bRow]]:
    """``(contract, rows)`` for the newest filed contract, floored."""
    path = _newest_provider_contract()
    rows = p7b_rows(path.read_text(encoding="utf-8"))
    assert len(rows) >= _MIN_P7B_ROWS, (
        f"{path.name} yielded only {len(rows)} P7b rows (floor {_MIN_P7B_ROWS}); "
        "a table that small means the parser missed it, not that cyanrip changed"
    )
    return path, rows


def test_the_value_table_IS_the_contracts_P7b_for_the_pinned_mode() -> None:
    """`naming._VALUE_SANITISE` must equal P7b's column for `SANITISE_MODE`.

    Derived from the artifact: every character P7b maps to exactly ONE glyph
    under our pinned mode must be in our table with that glyph, and nothing else
    may be. A character P7b maps to MORE than one glyph must be absent — that is
    `"`, whose two rows alternate on a parity flag (P7d) no lookup table can
    express, and `naming.py` documents its absence as deliberate. Equality in
    both directions, so a table that silently grew an entry fails as surely as
    one that lost one.

    P7b has columns for the two modes that are not OS-limited, `simple` and
    `unicode`. An `os_` mode writes whatever the build's OS dictates (P7c), so a
    pin on one fails here with that sentence rather than being compared against
    the wrong column.
    """
    path, rows = newest_p7b()
    assert SANITISE_MODE in {"simple", "unicode"}, (
        f"cyanrip_backend.SANITISE_MODE is {SANITISE_MODE!r}, which P7b has no "
        "column for: an os_ mode's output depends on the build's OS (P7c), so "
        "`naming._VALUE_SANITISE` cannot be checked against P7b alone any more"
    )
    glyphs: dict[str, set[str]] = {}
    for row in rows:
        glyphs.setdefault(row.character, set()).add(getattr(row, SANITISE_MODE))
    expected = {char: next(iter(g)) for char, g in glyphs.items() if len(g) == 1}
    alternating = sorted(char for char, g in glyphs.items() if len(g) > 1)

    assert len(expected) >= _MIN_COMPARED, (
        f"only {len(expected)} single-glyph characters to compare (floor "
        f"{_MIN_COMPARED}) — a comparison that small proves little"
    )
    missing = {c: g for c, g in expected.items() if c not in naming._VALUE_SANITISE}
    wrong = {
        c: (naming._VALUE_SANITISE[c], g)
        for c, g in expected.items()
        if c in naming._VALUE_SANITISE and naming._VALUE_SANITISE[c] != g
    }
    extra = sorted(set(naming._VALUE_SANITISE) - set(expected))
    assert not (missing or wrong or extra), (
        f"`naming._VALUE_SANITISE` disagrees with P7b's `{SANITISE_MODE}` column "
        f"in {path.name}.\n  missing (P7b maps, we do not): {missing}\n"
        f"  wrong glyph (ours, P7b's): {wrong}\n"
        f"  not in P7b as a single-glyph character: {extra}\n"
        f"  (characters P7b maps to more than one glyph: {alternating})\n"
        "The preview and the overwrite guard's first probe both render this "
        "table; a stale entry is how a completed rip was overwritten in 2026-08."
    )


def test_the_overwrite_guard_tolerates_every_character_P7b_substitutes() -> None:
    """`naming.SUBSTITUTION_SOURCES` must cover every character in P7b.

    The guard's match rule allows a predicted name and an on-disk one to differ
    only where OUR character is in this set. So a character cyanrip substitutes
    but the set omits is a position where the guard refuses a real match — the
    too-narrow direction, which is the one that destroyed a rip. Our own glyphs
    must be in it too, because our prediction writes them and cyanrip may not.
    """
    path, rows = newest_p7b()
    characters = {row.character for row in rows}
    assert len(characters) >= _MIN_COMPARED, characters
    uncovered = sorted(characters - naming.SUBSTITUTION_SOURCES)
    assert not uncovered, (
        f"P7b ({path.name}) substitutes {uncovered}, which "
        "`naming.SUBSTITUTION_SOURCES` does not list, so the overwrite guard would "
        "refuse to recognise cyanrip's rendering of a title containing them"
    )
    ours = sorted(set(naming._VALUE_SANITISE.values()) - naming.SUBSTITUTION_SOURCES)
    assert not ours, f"our own look-alike glyphs are not tolerated: {ours}"
