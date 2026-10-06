"""The cyanrip log parser's greedy value captures read exactly what the lazy ones read.

Why this file exists (TASKS.md, *Found while integrating*, item 4, 2026-10-05).
Twenty-one "Label:   value" patterns in ``parsers/cyanrip_log.py`` captured their
value lazily in front of trailing whitespace, ``(?P<v>\\S.*?)\\s*$`` or
``(?P<v>.+?)\\s*$``. That shape re-scans the run of blanks after every character
the lazy capture adds, so it is quadratic in the length of a blank run inside the
value: ``_READ_STALLS`` took 344 ms on one line with 8,000 spaces in it, and
``inbound_text.MAX_LINE_CHARS`` admits 65,536. The saved log is parsed on the GUI
thread (``parse_rip_log_from_disk``), so that is a frozen window.

They were rewritten greedily (the note above ``cyanrip_log._DRIVE`` gives the two
shapes). **A rewrite whose only purpose is speed may change the speed and nothing
else**, and these patterns are a published surface (``docs/cyanrip-consumer-
contract.md``): the fork reads which lines we parse and what we take from them. So
this file keeps every OLD form as the reference and holds each rewrite to it: the
same lines matched, at the same span, with the same groups, by ``match``,
``search`` and ``fullmatch`` alike.

The timing side is ``tests/test_regex_bounded_time.py``, whose sweep times every
pattern behind its own label (the lead-in inputs added for exactly these); the
pins at the bottom of this file name each pattern, so a revert names itself.
"""

from __future__ import annotations

import re
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.parsers import cyanrip_log

#: (attribute in `cyanrip_log`, its OLD lazy form, a label line its value follows).
#: The old forms are kept here and nowhere else, as the reference the rewrite must
#: agree with. The label is a concrete example of the text before the value; the
#: property test also generates labels from the old form's own lead (the part
#: before the last ``\s+(?P<``), so a label this table spells wrongly cannot narrow
#: the proof to lines that never match.
_REWRITES: list[tuple[str, str, str]] = [
    # `\S.*?` became `\S(?:.*\S)?`: the eight TASKS named.
    ("_GAPS_VALUE", r"^\s+(?P<value>\S.*?)\s*$", ""),
    ("_READ_STALLS", r"^Read stalls:\s+(?P<value>\S.*?)\s*$", "Read stalls:"),
    (
        "_TRACK_ACCURIP_STATUS",
        r"^\s+Accurip:\s+(?P<status>\S.*?)\s*$",
        "    Accurip:",
    ),
    ("_ENCODER_ERRORS", r"^Encoder errors:\s+(?P<value>\S.*?)\s*$", "Encoder errors:"),
    ("_INTERRUPTED_AT", r"^Interrupted at:\s+(?P<where>\S.*?)\s*$", "Interrupted at:"),
    ("_TRACKS_TO_RIP", r"^Tracks to rip:\s+(?P<value>\S.*?)\s*$", "Tracks to rip:"),
    ("_TRACK_PARANOIA_SCOPE", r"^\s+Scope:\s+(?P<text>\S.*?)\s*$", "    Scope:"),
    (
        "_TRACK_SECURE_VERDICT",
        r"^\s+Secure re-?read(?:s)?:\s+(?P<text>\S.*?)\s*$",
        "    Secure re-reads:",
    ),
    # The two bounded ones: `\S.{0,N}?` became `\S(?:.{0,N-1}\S)?`.
    ("_INVOKED_AS", r"^Invoked as:\s+(?P<argv>\S.{0,4000}?)\s*$", "Invoked as:"),
    (
        "_PREGAP_SOURCE",
        r"^\s{1,8}Pregap source:\s+(?P<source>\S.{0,63}?)\s*$",
        "    Pregap source:",
    ),
    # `.+?` became `\S(?:.*\S)?|[^\S\n]`: the same shape, found in the same file by
    # the sweep's lead-in inputs once they existed.
    ("_DRIVE", r"^(?:Drive used|Device model):\s+(?P<drive>.+?)\s*$", "Device model:"),
    (
        "_OVERREAD_MODE",
        r"^(?:Over|Under)read mode:\s+(?P<mode>.+?)\s*$",
        "Underread mode:",
    ),
    ("_ALBUM", r"^Album:\s+(?P<value>.+?)\s*$", "Album:"),
    ("_ALBUM_ARTIST", r"^Album artist:\s+(?P<value>.+?)\s*$", "Album artist:"),
    ("_C2", r"^C2 errors:\s+(?P<text>.+?)\s*$", "C2 errors:"),
    ("_PARANOIA_LEVEL", r"^Paranoia level:\s+(?P<text>.+?)\s*$", "Paranoia level:"),
    ("_OUTPUTS", r"^Outputs:\s+(?P<value>.+?)\s*$", "Outputs:"),
    ("_SPEED_CAP", r"^Speed:\s+(?P<text>.+?)\s*$", "Speed:"),
    ("_PREEMPHASIS", r"^\s+Preemphasis:\s+(?P<text>.+?)\s*$", "    Preemphasis:"),
    (
        "_FINISHED_AT",
        r"^Ripping finished at\s+(?P<when>.+?)\s*$",
        "Ripping finished at",
    ),
    (
        "_REPLAYGAIN",
        r"^\s+(?P<key>REPLAYGAIN_[A-Z_]+|R128_TRACK_GAIN):\s+(?P<val>.+?)\s*$",
        "    REPLAYGAIN_TRACK_GAIN:",
    ),
]

_IDS: list[str] = [name for name, _old, _label in _REWRITES]

#: Every whitespace character the patterns treat specially, other than the
#: newline: `\s` accepts all of them and `.` accepts all of them, which is
#: exactly the overlap the old lazy capture backtracked over. The non-ASCII ones
#: are there because a `str` pattern's `\s` is Unicode.
_BLANKS: str = " \t\r\x0b\x0c\x1c\x85\xa0 　"

#: Value characters: ordinary text, the label's own colon, a non-ASCII letter,
#: every blank above, and the newline, which `.` refuses and `\s` accepts. The
#: newline is in on purpose: the parser is fed single lines, but a rewrite that
#: agrees only on single lines would be a narrower claim than "same pattern".
_VALUE_CHARS: str = "ax:-|0é" + _BLANKS + "\n"


def _match_shape(match: re.Match[str] | None) -> tuple[object, ...] | None:
    """Everything a caller can read off a match: the span and every group."""
    return None if match is None else (match.span(), match.groupdict())


def _every_reading(pattern: re.Pattern[str], line: str) -> list[object]:
    """What `match`, `search` and `fullmatch` each make of ``line``."""
    return [
        _match_shape(pattern.match(line)),
        _match_shape(pattern.search(line)),
        _match_shape(pattern.fullmatch(line)),
    ]


def _lead_of(old: str) -> str:
    """The old form's text before its value: after `^`, up to the last `\\s+(?P<`."""
    return old[1 : old.rindex(r"\s+(?P<")]


def _lines(old: str, label: str) -> st.SearchStrategy[str]:
    """Lines built from the parts the pattern branches on.

    A label (the table's, one generated from the old form's own lead, or junk), a
    gap of blanks, a value with a blank run INSIDE it, a blank run AFTER it, more
    blanks, and an ending. The runs reach 200 characters, long enough that a
    lazy capture backtracks over them for real and short enough that the old,
    quadratic forms stay affordable as the reference. Free text alone almost
    never forms a label, a gap and a value, so it could not carry the proof.
    """
    lead = st.one_of(
        st.just(label),
        st.from_regex(_lead_of(old), fullmatch=True),
        st.text(alphabet=_VALUE_CHARS, max_size=6),
    )
    blanks = st.text(alphabet=_BLANKS + "\n", max_size=4)
    value = st.text(alphabet=_VALUE_CHARS, max_size=8)
    run = st.sampled_from([0, 1, 2, 7, 64, 200]).map(lambda n: " " * n)
    ending = st.sampled_from(["", "\n", "\nx", " \n", "\n\n", "x"])
    return st.builds(
        lambda lead_, gap, head, inside, tail, after, more, end: (
            lead_ + gap + head + inside + tail + after + more + end
        ),
        lead,
        blanks,
        value,
        run,
        value,
        run,
        blanks,
        ending,
    )


@pytest.mark.parametrize(("name", "old", "label"), _REWRITES, ids=_IDS)
def test_each_rewrite_reads_what_its_old_form_read(
    name: str, old: str, label: str
) -> None:
    """Same lines matched, same span, same groups: on every generated line.

    One Hypothesis run per pattern, so a failure names the pattern and shrinks to
    the shortest line the two forms read differently.
    """
    new = getattr(cyanrip_log, name)
    reference = re.compile(old)
    assert new.pattern != old, f"{name} still has its old form; nothing to prove"

    @settings(max_examples=150, deadline=None)
    @given(_lines(old, label))
    def agrees(line: str) -> None:
        assert _every_reading(new, line) == _every_reading(reference, line)

    agrees()


def _example_lines(label: str) -> list[str]:
    """The shapes the property test is meant to reach, written out by hand.

    A floor on matches below makes sure these are not all misses: two forms that
    both refuse every line agree perfectly and prove nothing.
    """
    head = label + " "
    return [
        head + "max",
        head + "ok   ",
        head + "a" + " " * 3000 + "b",
        head + "a" + " " * 3000,
        head + "a" + " " * 3000 + "b" + " " * 3000,
        head + "two  words   here",
        head + "x",
        head + "x\n",
        head + "x\ny",
        head + " ",
        head + "  ",
        head + "\t",
        head + " \n",
        head + "　value　",
        label + ":" + "x",
        label,
        "",
    ]


@pytest.mark.parametrize(("name", "old", "label"), _REWRITES, ids=_IDS)
def test_each_rewrite_agrees_on_the_shapes_written_out(
    name: str, old: str, label: str
) -> None:
    """The equivalence on hand-written lines, with long blank runs, and a floor."""
    new = getattr(cyanrip_log, name)
    reference = re.compile(old)
    lines = _example_lines(label)
    differing = [
        line[:40]
        for line in lines
        if _every_reading(new, line) != _every_reading(reference, line)
    ]
    assert not differing, f"{name} reads these lines differently: {differing!r}"
    matched = sum(reference.match(line) is not None for line in lines)
    assert matched >= 6, f"only {matched} of these lines matched {name}'s old form"


@pytest.mark.parametrize(
    ("name", "old", "bound"),
    [
        ("_INVOKED_AS", r"^Invoked as:\s+(?P<argv>\S.{0,4000}?)\s*$", 4001),
        (
            "_PREGAP_SOURCE",
            r"^\s{1,8}Pregap source:\s+(?P<source>\S.{0,63}?)\s*$",
            64,
        ),
    ],
)
def test_a_bounded_value_keeps_its_bound(name: str, old: str, bound: int) -> None:
    """At, under and over the cap, the rewrite and the old form agree.

    The cap is where a bounded rewrite would go wrong if it were off by one: the
    old `\\S.{0,N}?` admits a value of N+1 characters, and the rewrite spells that
    as `\\S`, up to N-1 more, then `\\S`. A value one longer than the cap matches
    neither, which is the bound doing its job.
    """
    new = getattr(cyanrip_log, name)
    reference = re.compile(old)
    label = "Invoked as: " if name == "_INVOKED_AS" else "  Pregap source: "
    results: list[bool] = []
    for length in (bound - 2, bound - 1, bound, bound + 1, bound + 2):
        # Blanks inside the value count toward the cap in both forms; checked at
        # the cap and one past it, because the old form is slow on long runs.
        for inner in ("a", " ") if length in (bound, bound + 1) else ("a",):
            value = "a" + inner * (length - 2) + "b" if length >= 2 else "a"
            for after in ("", "   "):
                line = label + value + after
                assert _every_reading(new, line) == _every_reading(reference, line), (
                    name,
                    length,
                    repr(inner),
                    repr(after),
                )
                results.append(reference.match(line) is not None)
    # Non-triviality: the sweep crossed the cap, so both outcomes were compared.
    assert any(results) and not all(results), results


#: The line that drives an OLD form into its quadratic region: a label, a value
#: with 20,000 spaces inside it, and a non-blank last character. The old forms
#: took about two seconds on it; the greedy ones take microseconds.
_PIN_RUN: int = 20_000


@pytest.mark.parametrize(
    ("name", "label"),
    [(name, label) for name, _old, label in _REWRITES if name != "_PREGAP_SOURCE"],
    ids=[name for name in _IDS if name != "_PREGAP_SOURCE"],
)
def test_each_rewrite_is_fast_on_a_long_blank_run(name: str, label: str) -> None:
    """Each pattern, by name, on the line that shows the lazy form quadratic.

    `_PREGAP_SOURCE` is not pinned: its old form was bounded at 64 characters, so
    it cost at most 64 passes over the run, which is linear, and a pin that cannot
    fail on a revert would be decoration. It is rewritten for consistency, and the
    equivalence tests above cover it.

    50 ms is far from both: thousands of times the greedy form's cost, and a
    fortieth of the old one's.
    """
    pattern = getattr(cyanrip_log, name)
    line = label + " a" + " " * _PIN_RUN + "b"
    start = time.thread_time()
    pattern.match(line)
    elapsed = time.thread_time() - start
    assert elapsed < 0.050, (
        f"cyanrip_log.{name} took {elapsed * 1000:.1f} ms on a {len(line)}-character "
        "line: a lazy capture before trailing whitespace has come back"
    )
