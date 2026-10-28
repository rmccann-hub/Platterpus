"""The `Preemphasis:` row is read by string operations exactly as the regex read it.

On 2026-10-28 tests/test_regex_bounded_time.py failed a CI leg on the parser's
`_PREEMPHASIS` value regex. Timed locally it was linear, and the owner judged the
CI reading noise at about 0.05 ms, then had the regex replaced with string
operations (`cyanrip_preemphasis.preemphasis_text`) so it could not flake that way again,
**keeping today's results exactly**. This file keeps the old regex as the
reference and holds the function to it:

- on generated lines built from the parts the regex branches on (indent, label,
  gap, value, trailing blanks), with every blank a `str` regex's `\\s` accepts;
- on written-out lines, including the two the owner named: a line of only spaces
  after the label gives a single space, and a line the regex refused gives None;
- in the parser itself, on the real row and on a line of only spaces.

The equivalence is over single lines, which is all the parser feeds it: it reads
`text.splitlines()`, so no line it sees holds a newline.
"""

from __future__ import annotations

import re
import time
from typing import Final

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_preemphasis import preemphasis_text

#: The regex the function replaced, as it stood on main at 0b4dc300.
_OLD: Final[re.Pattern[str]] = re.compile(
    r"^\s+Preemphasis:\s+(?P<text>\S(?:.*\S)?|[^\S\n])\s*$"
)

#: Blanks `\s` and `str.isspace` accept, ASCII and not, but never the newline:
#: the parser splits on it, so no line it reads holds one.
_BLANKS: Final[str] = " \t\r\x0b\x0c\x1c\x85\xa0 　"

#: Value characters: text, the label's colon, a non-ASCII letter, and blanks.
_VALUE_CHARS: Final[str] = "anoe:-()é" + _BLANKS


def _old(line: str) -> str | None:
    match = _OLD.match(line)
    return None if match is None else match.group("text")


@st.composite
def _lines(draw: st.DrawFn) -> str:
    """Lines made of the parts the old regex branches on, each part optional."""
    indent = draw(st.text(alphabet=_BLANKS, max_size=20))
    label = draw(
        st.sampled_from(
            ["Preemphasis:", "Preemphasis", "preemphasis:", "Preemphasis::", "x"]
        )
    )
    gap = draw(st.text(alphabet=_BLANKS, max_size=6))
    value = draw(st.text(alphabet=_VALUE_CHARS, max_size=30))
    tail = draw(st.text(alphabet=_BLANKS, max_size=6))
    return indent + label + gap + value + tail


@settings(max_examples=3000, deadline=None)
@given(_lines())
def test_the_function_reads_every_generated_line_as_the_regex_did(line: str) -> None:
    assert preemphasis_text(line) == _old(line), repr(line)


@settings(max_examples=1000, deadline=None)
@given(st.text(alphabet=_VALUE_CHARS + "Pr", max_size=40))
def test_the_function_reads_free_text_as_the_regex_did(line: str) -> None:
    assert preemphasis_text(line) == _old(line), repr(line)


#: (line, what the old regex read): written out, so a reader sees each case.
_EXAMPLES: Final[list[tuple[str, str | None]]] = [
    ("  Preemphasis:   none detected", "none detected"),
    (
        "  Preemphasis:   present (subcode) (deemphasis applied)",
        "present (subcode) (deemphasis applied)",
    ),
    ("  Preemphasis:   none detected   ", "none detected"),
    ("\tPreemphasis:\tnone", "none"),
    # Only spaces after the label: the single-space value, as before.
    ("  Preemphasis:   ", " "),
    ("  Preemphasis:  ", " "),
    # Only blanks, ending in a tab: the regex took the last one.
    ("  Preemphasis:  \t", "\t"),
    # One blank after the label and nothing else: the regex refused it.
    ("  Preemphasis: ", None),
    ("  Preemphasis:", None),
    ("  Preemphasis:none", None),
    ("Preemphasis:   none detected", None),
    ("  preemphasis:   none", None),
    ("  Preemphasis    none", None),
    ("", None),
    (" " * 3000 + "Preemphasis:" + " " * 3000, " "),
    (" " * 3000 + "Preemphasis: a" + " " * 3000 + "b", "a" + " " * 3000 + "b"),
]


def test_the_written_out_lines_read_as_the_regex_did() -> None:
    for line, expected in _EXAMPLES:
        assert _old(line) == expected, f"the reference moved on {line[:40]!r}"
        assert preemphasis_text(line) == expected, f"{line[:40]!r}"


def test_the_parser_reads_the_row_through_the_function() -> None:
    """The parser's own result, so a call site still on a regex would show."""
    base = "Track 1 ripped and encoded successfully!\n  Preemphasis:   {value}\n"
    detected = cyanrip_log.parse_cyanrip_log(base.format(value="present (subcode)"))
    clean = cyanrip_log.parse_cyanrip_log(base.format(value="none detected"))
    assert [t.pre_emphasis for t in detected.tracks] == [True]
    assert [t.pre_emphasis for t in clean.tracks] == [False]


def test_the_row_is_still_recognised_for_the_contract() -> None:
    """The consumer contract and the real-log classifier still list the row."""
    table = dict(cyanrip_log._INDENTED_LINE_PATTERNS)
    assert table["track_preemphasis"].match("  Preemphasis:   none detected")
    assert not table["track_preemphasis"].match("Preemphasis:   none detected")


def test_the_function_is_fast_on_a_long_blank_run() -> None:
    """The line the timing sweeps use, at 20,000 blanks: string operations are
    linear, so this takes microseconds; 50 ms leaves room for any runner."""
    line = "    Preemphasis: a" + " " * 20_000 + "b"
    start = time.thread_time()
    preemphasis_text(line)
    elapsed = time.thread_time() - start
    assert elapsed < 0.050, f"took {elapsed * 1000:.1f} ms"
