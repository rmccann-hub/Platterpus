"""Tests for :mod:`platterpus.inbound_text`, and the decoding policy it relies on.

**Why this exists.** Critical rule #12's inbound half said control characters and
NULs in the ripper's output are flagged and over-long lines bounded. The
2026-09-25 TASKS audit found no code doing it. Checking it found a second, worse
hole: every text-mode pipe that set no ``errors`` policy raised
``UnicodeDecodeError`` on the first byte that was not UTF-8, and a rip's read loop
then stopped reading the ripper altogether, with the line before the byte lost
as well. Eight of the fourteen text-mode reads had no policy, the rip itself among them. The sweep at the bottom keeps a
new one from arriving.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus import inbound_text
from platterpus.inbound_text import MAX_LINE_CHARS, Tally, screen_line, screen_text

_SRC = Path(inbound_text.__file__).resolve().parent


# --- the screen -------------------------------------------------------------


def test_clean_text_is_kept_verbatim() -> None:
    line = "Track 1 title: Café — «naïve» 日本語\tand a tab"
    screened = screen_line(line)
    assert screened.text == line
    assert not screened.flagged


def test_control_characters_become_visible_escapes_and_are_counted() -> None:
    screened = screen_line("before\x00after\x1b[2J\x7f\x85end\u2028")
    assert screened.text == "before\\x00after\\x1b[2J\\x7f\\x85end\\u2028"
    assert screened.control_chars == 5
    assert screened.flagged


def test_a_byte_that_was_not_utf8_is_counted_not_hidden() -> None:
    screened = screen_line("bad \ufffd byte")
    assert screened.text == "bad \ufffd byte"
    assert screened.undecodable == 1 and screened.flagged


def test_an_over_long_line_keeps_its_head_and_tail_and_says_what_went() -> None:
    """The tail matters: a tool's last words are where its error is."""
    line = "HEAD" + "x" * (MAX_LINE_CHARS * 3) + "the fatal message"
    screened = screen_line(line)
    assert screened.text.startswith("HEAD")
    assert screened.text.endswith("the fatal message")
    assert screened.elided_chars == len(line) - MAX_LINE_CHARS
    assert f"{screened.elided_chars} characters of this line elided" in screened.text
    assert len(screened.text) < MAX_LINE_CHARS + 100


def test_a_line_at_the_bound_is_not_touched() -> None:
    line = "y" * MAX_LINE_CHARS
    assert screen_line(line).text == line


def test_screen_text_keeps_line_structure_and_sums_counts() -> None:
    screened = screen_text("one\x00\ntwo\nthree\x1b")
    assert screened.text == "one\\x00\ntwo\nthree\\x1b"
    assert screened.control_chars == 2


def test_the_tally_says_nothing_about_clean_output_and_everything_about_the_rest() -> (
    None
):
    tally = Tally()
    tally.add(screen_line("clean"))
    assert tally.note() == ""
    tally.add(screen_line("a\x00b"))
    tally.add(screen_line("\ufffd"))
    tally.add(screen_line("z" * (MAX_LINE_CHARS + 10)))
    note = tally.note()
    assert note.startswith("[platterpus] 3 line(s) of this output were screened")
    assert "1 control character(s)" in note
    assert "1 byte(s) that were not UTF-8" in note
    assert "10 character(s) elided" in note


@given(st.text())
def test_screen_line_never_raises_and_leaves_nothing_invisible(line: str) -> None:
    screened = screen_line(line)
    assert not inbound_text._FLAGGED.search(screened.text)  # noqa: SLF001
    assert len(screened.text) <= 4 * MAX_LINE_CHARS + 200


@given(st.text(alphabet=st.characters(blacklist_categories=("Cc", "Zl", "Zp", "Cs"))))
def test_screen_line_changes_nothing_that_needs_no_change(line: str) -> None:
    """Everything else verbatim: the rule's other half, and the easier one to break."""
    screened = screen_line(line)
    assert screened.text == line
    assert screened.control_chars == 0


# --- the decoding policy ----------------------------------------------------


def test_a_text_pipe_with_replace_survives_a_byte_that_is_not_utf8() -> None:
    """The mechanism the sweep below protects, run for real."""
    child = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(b'before\\nbad \\xe9 byte\\nafter\\n')",
    ]
    proc = subprocess.Popen(
        child, stdout=subprocess.PIPE, text=True, errors="replace", bufsize=1
    )
    assert proc.stdout is not None
    lines = [line.rstrip("\n") for line in proc.stdout]
    proc.wait()
    assert lines == ["before", "bad \ufffd byte", "after"]
    assert screen_line(lines[1]).undecodable == 1


#: The subprocess functions that take ``encoding=``; passing it opens text mode too.
_SUBPROCESS_CALLS: frozenset[str] = frozenset(
    {"Popen", "run", "check_output", "check_call", "call"}
)


def _text_mode_calls(source: str) -> tuple[int, list[int]]:
    """``(text-mode calls found, lines of those with no errors policy)``.

    Text mode is ``text=True``, ``universal_newlines=True``, or ``encoding=`` on a
    subprocess call: each decodes the child's bytes, and each raises on a byte
    that does not decode unless ``errors=`` says otherwise.
    """
    found = 0
    missing: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        keywords = {k.arg: k for k in node.keywords if k.arg}
        flag = keywords.get("text") or keywords.get("universal_newlines")
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        text_mode = (
            flag is not None
            and isinstance(flag.value, ast.Constant)
            and flag.value.value is True
        ) or (name in _SUBPROCESS_CALLS and "encoding" in keywords)
        if not text_mode:
            continue
        found += 1
        if "errors" not in keywords:
            missing.append(node.lineno)
    return found, missing


def test_every_text_mode_subprocess_read_says_what_to_do_with_a_bad_byte() -> None:
    """Without ``errors=``, one byte that is not UTF-8 raises and ends the read."""
    missing: list[str] = []
    found = 0
    for path in sorted(_SRC.rglob("*.py")):
        count, lines = _text_mode_calls(path.read_text(encoding="utf-8"))
        found += count
        missing += [f"{path.relative_to(_SRC)}:{line}" for line in lines]
    # Floor: 14 text-mode calls on 2026-09-25, eight of them with no policy.
    assert found >= 12, f"only {found} text-mode call(s) found; the sweep is blind"
    assert not missing, (
        'these text-mode reads set no errors policy; add errors="replace" so a '
        "byte that is not UTF-8 becomes U+FFFD instead of ending the read:\n  "
        + "\n  ".join(missing)
    )


def test_the_policy_sweep_fires_on_the_shape_it_refuses() -> None:
    bad = "import subprocess\nsubprocess.run(['x'], capture_output=True, text=True)\n"
    good = bad.replace("text=True", 'text=True, errors="replace"')
    assert _text_mode_calls(bad) == (1, [2])
    assert _text_mode_calls(good) == (1, [])
    by_encoding = "import subprocess\nsubprocess.run(['x'], encoding='utf-8')\n"
    assert _text_mode_calls(by_encoding) == (1, [2])
