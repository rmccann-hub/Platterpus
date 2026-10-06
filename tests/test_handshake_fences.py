"""What the handshake gate counts as a fenced code block, which is what it ignores.

`handshake-protocol.md` §2 rule 2: *"Strip fenced code blocks before matching. A
declaration is a statement the file makes, not one it quotes."* The protocol does
not say what a fence is, so the gate reads it as CommonMark does, the way the
Markdown renderers that show a lap to its reader draw it (TASKS C6, 2026-10-06).

Until then ``_strip_fences`` used a regex that needed a closing fence at column 0
of exactly the opening's length. So a field inside an UNTERMINATED fence, an
INDENTED one (one to three spaces), or one closed by a longer run was read as a
declaration, and protocol 7's row C46 counted ``HANDSHAKE-NEXT-LAP`` through it.
``_unfenced_body`` (the R6 pre-commit search) had a second rule of its own; both
now ask ``_fenced_lines``.

The cases below are CommonMark's rules for fenced blocks (§4.5), one each; the
property tests hold the never-raises contract every parser of the peer's text
carries, and the invariants a stripper must keep.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "handshake.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("handshake_fences", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_HS: ModuleType = _load()


@pytest.fixture
def hs() -> ModuleType:
    return _HS


#: A declared verdict, then an illustration of a different one: the shape every
#: case below wraps in a different fence. If the illustration is read, the verdict
#: becomes AMBIGUOUS; if the fence is honoured, it stays HOLD.
_DECLARED = "HANDSHAKE-VERDICT: HOLD\n\nAn example of a close:\n\n"
_QUOTED = "HANDSHAKE-VERDICT: GO\nHANDSHAKE-TESTED: platterpus 0.6.65 on the rig\n"


def _reads_only_the_declaration(hs: ModuleType, text: str) -> bool:
    fields = hs.wire_fields(text)
    return (
        fields.get("HANDSHAKE-VERDICT") == "HOLD" and "HANDSHAKE-TESTED" not in fields
    )


#: (label, a fence around the illustrated close). The label is the test id.
_FENCED: list[tuple[str, str]] = [
    ("terminated, column 0", "```\n" + _QUOTED + "```\n"),
    ("tildes, with an info string", "~~~text\n" + _QUOTED + "~~~\n"),
    ("UNTERMINATED: runs to the end of the file", "```\n" + _QUOTED),
    ("UNTERMINATED after a closer of the other character", "```\n~~~\n" + _QUOTED),
    ("opening indented one space", " ```\n" + _QUOTED + "```\n"),
    ("opening indented three spaces", "   ```\n" + _QUOTED + "   ```\n"),
    ("closed by a LONGER run", "```\n" + _QUOTED + "`````\n"),
    ("a shorter run inside does not close", "````\n```\n" + _QUOTED + "````\n"),
    ("the other character inside does not close", "~~~\n```\n" + _QUOTED + "~~~\n"),
    ("a fence line with an info string does not close", "```\n```md\n" + _QUOTED),
    ("CRLF line endings", "```\r\n" + _QUOTED.replace("\n", "\r\n") + "```\r\n"),
]


def test_every_fence_rule_has_a_fenced_case() -> None:
    """The floor for the sweep below, whose cases are built strings.

    One case per rule the fence reader follows (CommonMark's): both fence
    characters, an unterminated fence, an indented opening, a longer closer, the
    three lines that do NOT close, and CRLF. Eleven when written (2026-10-06).
    """
    labels = [label for label, _text in _FENCED]
    assert len(labels) == len(set(labels)) >= 11
    for rule in (
        "tildes",
        "UNTERMINATED",
        "indented",
        "LONGER",
        "does not close",
        "CRLF",
    ):
        assert any(rule in label for label in labels), rule


@pytest.mark.parametrize(
    ("label", "fenced"), _FENCED, ids=[label for label, _text in _FENCED]
)
def test_a_field_inside_any_fence_is_quoted_not_declared(
    hs: ModuleType, label: str, fenced: str
) -> None:
    """Each fence shape hides the illustrated close; the declared HOLD stands."""
    assert _reads_only_the_declaration(hs, _DECLARED + fenced), label
    assert hs.wire_verdict(_DECLARED + fenced) == "HOLD", label


#: (label, a line CommonMark does not call a fence). The label is the test id.
_NOT_FENCES: list[tuple[str, str]] = [
    ("indented four spaces is indented code, not a fence", "    ```\n"),
    ("a tab counts as four columns", "\t```\n"),
    ("two backticks are not a fence", "``\n"),
    ("a backtick fence's info string may not hold a backtick", "``` a`b\n"),
    ("a block quote's fence is the quote's, not the file's", "> ```\n"),
]


@pytest.mark.parametrize(
    ("label", "not_a_fence"), _NOT_FENCES, ids=[label for label, _text in _NOT_FENCES]
)
def test_a_line_that_is_not_a_fence_quotes_nothing(
    hs: ModuleType, label: str, not_a_fence: str
) -> None:
    """The other side: a line CommonMark does not call a fence hides no field.

    A gate that stripped these would read a real declaration as absent, which
    fails closed, but it would also be a different rule from the renderer's.
    """
    text = not_a_fence + "HANDSHAKE-VERDICT: HOLD\n"
    assert hs.wire_verdict(text) == "HOLD", label


def test_a_closing_fence_may_be_indented_and_what_follows_is_declared(
    hs: ModuleType,
) -> None:
    """A closer indented up to three spaces closes, and the file speaks again.

    So does a closer LONGER than the opening run. The fenced-case table above
    cannot show that one: a closer that failed to close would leave the block
    running to the end of the file, and the illustration would be hidden either
    way. Only a declaration AFTER the closer tells the two apart.
    """
    for closer in ("   ```", "````", "`````"):
        text = "```\n" + _QUOTED + closer + "\nHANDSHAKE-VERDICT: HOLD\n"
        assert _reads_only_the_declaration(hs, text), closer
    # A closer of the other character, however long, does not close.
    text = "```\n" + _QUOTED + "~~~~~\nHANDSHAKE-VERDICT: HOLD\n"
    assert hs.wire_verdict(text) is None


def test_c46_does_not_count_a_next_lap_quoted_in_an_unterminated_fence(
    hs: ModuleType,
) -> None:
    """Row C46 counted through the fence stripper, in both directions.

    An illustrated ``HANDSHAKE-NEXT-LAP`` in an unterminated fence made a correct
    file read as declaring it twice; one in an indented fence made a file that
    never declares it read as conforming.
    """
    header = "HANDSHAKE-PROTOCOL: 7\n"
    declared = "HANDSHAKE-NEXT-LAP: 11 (yours): their reading\n"
    quoted = "HANDSHAKE-NEXT-LAP: 12 (ours): an example\n"
    assert hs.next_lap_problems(header + declared + "\n```\n" + quoted) == []
    problems = hs.next_lap_problems(header + "\n  ```\n" + quoted + "  ```\n")
    assert len(problems) == 1 and "absent" in problems[0], problems


def test_the_r6_body_search_and_the_fields_share_one_rule(hs: ModuleType) -> None:
    """`_unfenced_body` and `_strip_fences` agree on which lines are quoted.

    The body search toggled on any fence-like line, so a ```` ``` ```` line inside
    a ``~~~`` block flipped it out of the block and the rest read as stated.
    """
    text = "~~~\n```\nOur next lap is `GO` unless X.\n~~~\nStated.\n"
    assert hs._unfenced_body(text) == "Stated."
    kept = [line for line in hs._strip_fences(text).split("\n") if line]
    assert kept == ["Stated."]


# --- Properties -----------------------------------------------------------------

#: Lines built from the parts a fence is made of, so generated documents open,
#: close and nest fences far more often than free text would.
_LINE = st.one_of(
    st.builds(
        lambda indent, run, info: indent + run + info,
        st.sampled_from(["", " ", "  ", "   ", "    ", "\t", "> "]),
        st.sampled_from(["```", "````", "~~~", "~~~~~", "``", "`" * 40]),
        st.sampled_from(["", "  ", "text", " a`b", "\r", "\t"]),
    ),
    st.sampled_from(["HANDSHAKE-VERDICT: GO", "HANDSHAKE-NEXT-LAP: 3 (ours):", ""]),
    st.text(max_size=20),
)
_DOCUMENTS = st.lists(_LINE, max_size=12).map("\n".join)


@settings(max_examples=400)
@given(_DOCUMENTS)
def test_the_fence_readers_never_raise_and_keep_the_line_count(text: str) -> None:
    """Never raises, on any text: it reads what the peer sends (CLAUDE.md, parsers).

    And the invariants a stripper owes its callers: the line count is unchanged,
    each line is kept verbatim or blanked, stripping twice changes nothing, and
    the body search drops exactly the lines the field stripper blanks.
    """
    stripped = _HS._strip_fences(text)
    before, after = text.split("\n"), stripped.split("\n")
    assert len(after) == len(before)
    assert all(new in (old, "") for old, new in zip(before, after, strict=True))
    assert _HS._strip_fences(stripped) == stripped
    _HS.wire_fields(text)
    _HS.next_lap_problems(text)
    body = _HS._unfenced_body(text)
    lines = text.splitlines()
    mask = _HS._fenced_lines(lines)
    assert body == "\n".join(
        line for line, fenced in zip(lines, mask, strict=True) if not fenced
    )


@settings(max_examples=200)
@given(st.text(max_size=200))
def test_the_fence_readers_never_raise_on_free_text(text: str) -> None:
    """Free text of any characters, including every line terminator Python knows."""
    _HS._strip_fences(text)
    _HS._unfenced_body(text)
    _HS._fenced_lines(text.split("\n"))
    _HS.wire_fields(text)
