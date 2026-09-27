"""Property tests for the overwrite guard's match rule, over the whole of P7b.

`ui.main_window_helpers._is_sanitised_rendering_of(predicted, actual)` decides
whether a folder on disk is cyanrip's rendering of the name we predicted. It is
the rule that stops a finished archival rip being overwritten in silence (the
2026-08-23 incident: a 14-track rip replaced by a 2-track one because the
prediction missed by one glyph). Until now it was exercised on exactly one
character and one glyph pair (TASKS `fuzz:ui.main_window_helpers.
_is_sanitised_rendering_of`).

The table here is not ours. It is parsed out of the newest filed provider
contract's P7b by the one parser in `test_naming.py`, so these properties hold
the rule to what cyanrip is documented to write, not to what we believe it
writes.

**Scoped to the column our pin writes, and the scope is stated, not silent.**
`adapters.cyanrip_backend.SANITISE_MODE` is `unicode`, and
`test_naming.test_the_value_table_IS_the_contracts_P7b_for_the_pinned_mode`
fails if it ever moves to a mode P7b has no column for. P7b's other column,
`simple`, writes `_` for eight characters (which the rule accepts) and `'` for
`"` (which it does not, measured 2026-09-27). Accepting `'` is not free: under
the pinned mode cyanrip never writes it, so it could only add candidates, and
two candidates make `_sanitised_sibling` stand down. So it stays out, and the
comment beside `_SUBSTITUTION_TARGETS_ASCII` now says so.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Final

from hypothesis import given, settings
from hypothesis import strategies as st
from test_naming import newest_p7b

from platterpus import naming
from platterpus.adapters.cyanrip_backend import SANITISE_MODE
from platterpus.ui.main_window_helpers import _is_sanitised_rendering_of

#: Ordinary title characters no sanitiser touches: letters, digits, spaces,
#: punctuation cyanrip passes through, accented and CJK text. Mixed into every
#: drawn title so the substitutions sit inside realistic context.
_ORDINARY: Final[str] = "aZ09 -_.,'!&()éèüñß日本"

#: Floor on the deterministic sweep: every (character, glyph) pair P7b gives for
#: the pinned mode. Measured 10 on round 28 lap 3 — eight characters with one
#: glyph each, and `"` with two.
_MIN_PAIRS: Final[int] = 10

_SETTINGS = settings(max_examples=200, deadline=None)


@functools.cache
def _pinned_table() -> tuple[str, dict[str, tuple[str, ...]]]:
    """``(contract name, {character: glyphs})`` for `SANITISE_MODE`'s column.

    Cached because Hypothesis calls the tests below hundreds of times, and the
    contract does not change between examples.
    """
    path, rows = newest_p7b()
    assert SANITISE_MODE in {"simple", "unicode"}, SANITISE_MODE
    glyphs: dict[str, set[str]] = {}
    for row in rows:
        glyphs.setdefault(row.character, set()).add(getattr(row, SANITISE_MODE))
    return Path(path).name, {c: tuple(sorted(g)) for c, g in glyphs.items()}


def _is_plain(char: str) -> bool:
    """True for a character neither cyanrip nor the rule treats as substitutable.

    Not in P7b (cyanrip leaves it alone) and not in `SUBSTITUTION_SOURCES` (the
    rule does not tolerate a difference at it). The rule is deliberately
    generous at our own look-alike glyphs, which are in that set because our
    prediction writes them where cyanrip may not; a title that literally
    contains `‹` therefore may match a folder with another glyph there, which
    costs a dialog, and is excluded from the refusal property on purpose.
    """
    _name, table = _pinned_table()
    return char not in table and char not in naming.SUBSTITUTION_SOURCES


def _title_characters() -> st.SearchStrategy[str]:
    """One title character: usually from the pools that matter, sometimes any."""
    _name, table = _pinned_table()
    glyphs = {g for gs in table.values() for g in gs}
    pool = sorted(set(_ORDINARY) | set(table) | glyphs | naming.SUBSTITUTION_SOURCES)
    return st.one_of(
        st.sampled_from(pool),
        # Anything else Unicode can put in a title, bar lone surrogates, which
        # cannot occur in a decoded filename.
        st.characters(exclude_categories=("Cs",)),
    )


def _render(raw: str, data: st.DataObject) -> str:
    """cyanrip's rendering of a tag value under the pinned mode, per P7b.

    Every P7b character becomes one of the glyphs P7b lists for it, and every
    other character is passed through (P7b: "anything not in the character
    column is passed through unchanged"). Where P7b lists two glyphs — the quote,
    chosen by a parity flag P7d says no table can predict — each occurrence
    draws either one, so every combination the parity can produce is reachable.
    """
    _name, table = _pinned_table()
    return "".join(
        data.draw(st.sampled_from(table[c])) if c in table else c for c in raw
    )


@given(data=st.data())
@_SETTINGS
def test_any_rendering_P7b_allows_is_recognised(data: st.DataObject) -> None:
    """A folder cyanrip could have written for this title is recognised.

    `predicted` is built the way production builds it, by `naming`'s own value
    sanitiser; `actual` by P7b. Recognising every such pair is the property the
    2026-08-23 overwrite broke: the guard looked for a folder that was not there.
    """
    raw = "".join(data.draw(st.lists(_title_characters(), max_size=40)))
    predicted = naming._sanitise_value(raw)
    actual = _render(raw, data)
    assert _is_sanitised_rendering_of(predicted, actual), (raw, predicted, actual)


@given(data=st.data())
@_SETTINGS
def test_a_difference_where_nothing_is_substituted_is_refused(
    data: st.DataObject,
) -> None:
    """Change one character no sanitiser touches, and it is another album.

    The same rendering as above, with one PLAIN position altered to anything
    else — a letter, an accented letter, a look-alike glyph, a stand-in. The rule
    must refuse it: a folder that differs where no substitution could have
    happened is a different title (the "Café" / "Cafè" case), and matching it
    would warn about, or protect, the wrong album. One plain character is always
    present, so no example can pass by having nothing to alter.
    """
    chars = data.draw(st.lists(_title_characters(), max_size=40))
    plain_pool = sorted(c for c in _ORDINARY if _is_plain(c))
    chars.insert(
        data.draw(st.integers(min_value=0, max_value=len(chars))),
        data.draw(st.sampled_from(plain_pool)),
    )
    raw = "".join(chars)
    predicted = naming._sanitise_value(raw)
    rendered = list(_render(raw, data))
    position = data.draw(
        st.sampled_from([i for i, c in enumerate(raw) if _is_plain(c)])
    )
    rendered[position] = data.draw(
        _title_characters().filter(lambda c: c != raw[position])
    )
    actual = "".join(rendered)
    assert not _is_sanitised_rendering_of(predicted, actual), (
        raw,
        predicted,
        actual,
    )


def test_every_P7b_substitution_is_recognised_and_an_ordinary_letter_is_not() -> None:
    """The whole table, deterministically — the floor under the two above.

    Hypothesis draws; it does not promise to draw every row. This walks every
    (character, glyph) pair P7b gives for the pinned mode, so no row can go
    unchecked by chance, and at each one also asserts the refusal half: an
    ordinary letter in the substituted position is not a stand-in.
    """
    name, table = _pinned_table()
    pairs = [(char, glyph) for char, glyphs in table.items() for glyph in glyphs]
    assert len(pairs) >= _MIN_PAIRS, (
        f"only {len(pairs)} (character, glyph) pairs from {name} (floor "
        f"{_MIN_PAIRS}); the sweep would prove little"
    )
    for char, glyph in pairs:
        predicted = naming._sanitise_value(f"Songs {char}About{char} Nothing")
        actual = f"Songs {glyph}About{glyph} Nothing"
        assert _is_sanitised_rendering_of(predicted, actual), (char, glyph)
        assert not _is_sanitised_rendering_of(predicted, "Songs xAboutx Nothing"), (
            f"an ordinary letter was accepted as cyanrip's stand-in for {char!r}"
        )
