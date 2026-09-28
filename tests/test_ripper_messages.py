"""Property tests for `ripper_messages.format_to_pattern`.

`format_to_pattern` turns each format string in the fork's published fatal-
message inventory into a regex, and the union of those regexes decides which
lines of cyanrip's live output are shown to the user as the reason a rip failed.
Its input is external: the formats come from the provider contract, not from us.
It had no property test (TASKS `fuzz:ripper_messages.format_to_pattern`).

Two properties, both over the conversion specifiers the function claims to
support (every flag, width, precision, length modifier and conversion letter in
`ripper_messages._CONVERSION`):

* **never raises**: any text at all returns ``None`` or a pattern that compiles,
  and a pattern never matches a line shorter than the literal-text floor. That
  floor is the function's whole defence against matching every line;
* **round trip**: what C's ``printf`` prints for a generated format, with
  generated arguments, is matched by the pattern built from that format.

**The round trip is checked against Python's own printf machinery, not against
``_CONVERSION``.** The existing inventory test renders formats with a copy of
the product's regex (`test_ripper_error_surfacing._sample`), so the two agree
by construction; two implementations sharing an ancestor share its bugs.

**It found a real defect.** Three published formats carry an interior newline,
spelled as the C source spells it (backslash, then ``n``). The pattern escaped
it as literal text, and no build prints that, so none of the three ever matched
its own first line. Fixed in `format_to_pattern`; pinned below on the three real
formats as well as on generated ones.

**Scope, stated rather than silent.** Generated lines never begin with
whitespace: the matcher deliberately ignores an indented line
(`test_ripper_error_surfacing._BENIGN_LINES` holds
``"  Error reading sector 5"``), and no published format begins with any.
`test_no_published_format_is_outside_the_round_trips_scope` fails if one
appears, and also if a published format uses a C escape other than ``\\n``,
which `format_to_pattern` would still match as literal text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.ripper_message_inventory import ALL_FORMATS
from platterpus.ripper_messages import (
    _CONVERSION_LIMIT,
    _MIN_LITERAL_CHARS,
    build_matcher,
    format_to_pattern,
)

_SETTINGS = settings(max_examples=200, deadline=None)

#: Every conversion letter and length modifier `_CONVERSION` accepts.
_CONVERSION_LETTERS: Final[str] = "diuoxXeEfgGaAcspn"
_LENGTH_MODIFIERS: Final[tuple[str, ...]] = (
    "",
    "hh",
    "h",
    "ll",
    "l",
    "j",
    "z",
    "t",
    "L",
)

#: The C escape for a line break, as the published inventory spells it.
_C_NEWLINE: Final[str] = "\\n"


@dataclass(frozen=True)
class Piece:
    """One piece of a format: its text in the format, and what printf prints."""

    spec: str
    printed: str
    #: "text" (literal characters), "percent" (``%%``) or "conversion".
    kind: str


def _no_line_break(text: str) -> bool:
    return "\n" not in text


#: Any character except a lone surrogate, which no decoded line can hold.
_ANY_CHAR = st.characters(exclude_categories=("Cs",))


@st.composite
def _conversion(draw: st.DrawFn) -> Piece:
    """A C conversion with every optional part drawn, and its printed value.

    Printed by Python's ``%`` operator where it implements the letter, which is
    every one except ``a``/``A`` (hex float: ``float.hex``), ``p`` (a pointer:
    ``0x…``) and ``n`` (prints nothing). Python ignores length modifiers, so
    they are dropped before formatting. Widths and precisions stay under 100 so
    the printed value fits the pattern's documented per-conversion bound.
    """
    flags = "".join(draw(st.lists(st.sampled_from("-+ #0"), max_size=3, unique=True)))
    width = draw(st.sampled_from(["", "*"]) | st.integers(1, 40).map(str))
    precision = draw(
        st.sampled_from(["", ".", ".*"]) | st.integers(0, 40).map(lambda n: f".{n}")
    )
    length = draw(st.sampled_from(_LENGTH_MODIFIERS))
    letter = draw(st.sampled_from(_CONVERSION_LETTERS))
    spec = f"%{flags}{width}{precision}{length}{letter}"

    star_args: list[int] = []
    if width == "*":
        star_args.append(draw(st.integers(0, 40)))
    if precision == ".*":
        star_args.append(draw(st.integers(0, 40)))
    python_spec = f"%{flags}{width}{precision}"
    printed: str
    if letter in "diu":
        value = draw(st.integers(-(10**12), 10**12))
        printed = (python_spec + "d") % (*star_args, value)
    elif letter in "oxX":
        printed = (python_spec + letter) % (*star_args, draw(st.integers(0, 2**64 - 1)))
    elif letter in "eEfgG":
        number = draw(st.floats(min_value=-1e9, max_value=1e9) | st.just(float("nan")))
        printed = (python_spec + letter) % (*star_args, number)
    elif letter in "aA":
        hexed = float.hex(draw(st.floats(min_value=-1e9, max_value=1e9)))
        printed = hexed.upper() if letter == "A" else hexed
    elif letter == "c":
        char = draw(_ANY_CHAR.filter(_no_line_break))
        printed = (python_spec + "c") % (*star_args, char)
    elif letter == "s":
        value_text = draw(st.text(_ANY_CHAR, max_size=60).filter(_no_line_break))
        printed = (python_spec + "s") % (*star_args, value_text)
    elif letter == "p":
        printed = hex(draw(st.integers(0, 2**48)))
    else:  # "n" stores a count and prints nothing
        printed = ""
    return Piece(spec=spec, printed=printed, kind="conversion")


#: Literal text: no ``%`` (that would start a conversion) and no backslash or
#: newline (the line break is inserted deliberately, between lines).
_TEXT = st.text(
    st.characters(exclude_categories=("Cs",), exclude_characters="%\\\n"),
    min_size=1,
    max_size=20,
).map(lambda text: Piece(spec=text, printed=text, kind="text"))

_PERCENT = st.just(Piece(spec="%%", printed="%", kind="percent"))

#: Six letters or more, so a line can carry a fingerprint the floor accepts.
_ANCHOR = st.text("AbcdefGhij:!'", min_size=6, max_size=16).map(
    lambda text: Piece(spec=text, printed=text, kind="text")
)


@st.composite
def _line(draw: st.DrawFn) -> list[Piece]:
    """One printed line's pieces, with no whitespace at either edge.

    An edge literal is stripped here because `format_to_pattern` strips the
    line, and the printed line keeps whatever the format had: an indented line
    is outside the round trip's scope (see the module docstring).
    """
    pieces = draw(
        st.lists(
            st.one_of(_TEXT, _conversion(), _PERCENT, _ANCHOR), min_size=0, max_size=8
        )
    )
    for index, strip in ((0, str.lstrip), (-1, str.rstrip)):
        if pieces and pieces[index].kind == "text":
            text = strip(pieces[index].spec)
            pieces[index] = Piece(spec=text, printed=text, kind="text")
    return [p for p in pieces if p.spec]


def _literal_chars(pieces: list[Piece]) -> int:
    """How much literal text a line carries, by the documented rule.

    Each run of literal text between two conversions counts its length once
    stripped, and each ``%%`` counts one. Computed from how the line was BUILT,
    so it does not borrow the product's regex to decide what a conversion is.
    """
    total = 0
    run = ""
    for piece in pieces:
        if piece.kind == "text":
            run += piece.spec
            continue
        total += len(run.strip())
        run = ""
        if piece.kind == "percent":
            total += 1
    return total + len(run.strip())


#: Formats that are MOSTLY conversions: real conversion specs with a little
#: literal text between them, so a format carrying fewer literal characters than
#: the floor is common rather than a once-in-a-run accident. These are the
#: formats the floor exists to refuse; random text almost never produces one,
#: which is what made the first version of the test below unable to fail.
_SPARSE_FORMAT = st.lists(
    st.one_of(
        _conversion().map(lambda piece: piece.spec),
        st.sampled_from(["a", "x!", " ", "%%", "\\n"]),
    ),
    max_size=6,
).map("".join)


@given(
    fmt=st.one_of(
        st.text(max_size=80),
        st.text("%-+ #0123456789.*hlLjztdiuoxXeEfgGaAcspn\\ab\n"),
        _SPARSE_FORMAT,
    ),
    short=st.text("ax! %", max_size=_MIN_LITERAL_CHARS - 1),
)
@_SETTINGS
def test_format_to_pattern_never_raises_and_never_matches_a_short_line(
    fmt: str, short: str
) -> None:
    """Any input: ``None``, or a pattern that compiles and needs real text.

    A pattern that could match a line shorter than the literal floor would be
    matching on conversions alone, which is the "matches every line" failure the
    floor exists to refuse. The second alphabet is dense in the characters a
    conversion is made of, so near-miss specs are common; the third is built
    from real specs with a few literal characters between them.
    """
    pattern = format_to_pattern(fmt)
    if pattern is None:
        return
    compiled = re.compile(pattern)
    assert compiled.fullmatch("") is None, (fmt, pattern)
    assert compiled.fullmatch(short) is None, (fmt, pattern, short)


@given(lines=st.lists(_line(), min_size=1, max_size=3))
@_SETTINGS
def test_what_printf_prints_is_matched_by_the_pattern_built_from_its_format(
    lines: list[list[Piece]],
) -> None:
    """The round trip, one printed line at a time.

    The format joins its lines with the C escape ``\\n``, as the published
    inventory spells them. The pattern must match the first non-blank line
    printf prints, both on its own and inside the matcher the rip worker builds,
    and must be ``None`` exactly when that line carries too little literal text.
    """
    fmt = _C_NEWLINE.join("".join(p.spec for p in line) for line in lines)
    printed_lines = ["".join(p.printed for p in line) for line in lines]
    pattern = format_to_pattern(fmt)

    first = next((i for i, line in enumerate(lines) if line), None)
    if first is None:
        assert pattern is None, (fmt, pattern)
        return
    expected_none = _literal_chars(lines[first]) < _MIN_LITERAL_CHARS
    assert (pattern is None) == expected_none, (fmt, pattern)
    if pattern is None:
        return
    for piece in lines[first]:
        assert len(piece.printed) <= _CONVERSION_LIMIT, (
            f"the generator printed {len(piece.printed)} characters for "
            f"{piece.spec!r}, past the documented bound; fix the generator"
        )
    line = printed_lines[first]
    assert re.fullmatch(pattern, line), (fmt, pattern, line)
    matcher, unmatchable = build_matcher([fmt])
    assert unmatchable == []
    assert matcher.match(line), (fmt, line)


#: The three published formats carrying an interior line break, as measured at
#: round 28 lap 3, with what cyanrip prints for each (two lines).
_PUBLISHED_MULTILINE: Final[tuple[tuple[str, str], ...]] = (
    (
        "Unable to get AccuRIP DB data: %s\\n!",
        "Unable to get AccuRIP DB data: Connection timed out\n!",
    ),
    (
        'Unable to get cover art "%s": %s\\n!',
        'Unable to get cover art "front": Connection timed out\n!',
    ),
    (
        'Couldn\'t open path "%s" for writing: %s!\\nInvalid folder name? Try -D <folder>.',
        'Couldn\'t open path "/m/a.cue" for writing: Permission denied!\n'
        "Invalid folder name? Try -D <folder>.",
    ),
)


def test_a_published_format_with_a_line_break_matches_its_own_first_line() -> None:
    """The defect, on the real formats: each pattern must match what it prints.

    Checked format by format, with nothing else in the matcher, because the live
    matcher hid this: a sibling format and the prefix fallback caught each first
    line, so "is the line surfaced?" was always yes while the inventory entry
    meant to carry it matched nothing.
    """
    published = [fmt for fmt in ALL_FORMATS if _C_NEWLINE in fmt]
    assert sorted(published) == sorted(fmt for fmt, _ in _PUBLISHED_MULTILINE), (
        "the published formats with an interior line break changed; re-measure "
        f"this table: {published}"
    )
    for fmt, printed in _PUBLISHED_MULTILINE:
        pattern = format_to_pattern(fmt)
        assert pattern is not None, fmt
        first_line = printed.split("\n")[0]
        assert re.fullmatch(pattern, first_line), (fmt, pattern, first_line)
        matcher, _unmatchable = build_matcher([fmt])
        assert matcher.match(first_line), fmt


def test_no_published_format_is_outside_the_round_trips_scope() -> None:
    """What pins the round trip's input: the published formats' own shapes.

    The generated formats never begin a line with whitespace and use no C escape
    but ``\\n``. If a published format ever does either, the round trip no longer
    describes it: an indented first line is ignored by design, and any other
    escape (``\\t``, ``\\\\``) would be matched as literal text.
    """
    assert len(ALL_FORMATS) >= 125, f"the inventory collapsed to {len(ALL_FORMATS)}"
    indented = [f for f in ALL_FORMATS if f != f.lstrip()]
    assert not indented, f"published formats that begin with whitespace: {indented}"
    other_escapes = sorted(
        {m.group(0) for f in ALL_FORMATS for m in re.finditer(r"\\.", f)} - {_C_NEWLINE}
    )
    assert not other_escapes, (
        f"published formats use C escapes format_to_pattern does not interpret: "
        f"{other_escapes}"
    )
