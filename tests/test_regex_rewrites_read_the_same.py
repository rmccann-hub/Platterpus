"""Patterns rewritten for speed read exactly what their old forms read.

The lead-in shapes added to ``tests/test_regex_bounded_time.py`` on 2026-10-06
found six patterns outside ``parsers/cyanrip_log.py`` that slowed down with the
square of a run of blanks or zeros (the twenty-one inside it have their own file,
``tests/test_cyanrip_log_reads_values_greedily.py``):

* ``cue_validate._RE_REM``, ``_RE_TITLE``, ``_RE_PERFORMER``: ``\\s+`` then
  ``.*\\S``, which re-scanned the rest of the line once per blank when no value
  followed;
* ``parsers/rip_log._FIELD``: a lazy ``.*?`` before ``\\s*$``;
* ``workers/rip_worker._CYANRIP_ETA_VALUE``: two ``\\s*`` side by side once the
  minutes were absent;
* ``scripts/handshake._SOURCE_NAMED_LAP``: ``0*\\d+``, two repeats over the same
  zeros.

**A rewrite whose only purpose is speed may change the speed and nothing else.**
So each old form is kept here as the reference, and each rewrite must give the
same answer on every generated input: the same match, at the same span, with the
same groups, by ``match``, ``search`` and ``fullmatch``, and the same list of
matches by ``finditer`` (``_SOURCE_NAMED_LAP`` is searched for, not anchored).
The new forms are read from the source with ``ast``, as the timing sweep reads
them, so a script's import-time path setup is not needed.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_regex_bounded_time import _pattern_assigned_to

#: Blanks the patterns treat specially: `\s` accepts all of them, and `.` all but
#: the newline. The non-ASCII ones are there because a `str` pattern's `\s` is
#: Unicode.
_BLANKS: str = " \t\r\x0b\x0c\x85\xa0　"

#: A blank run: absent, short, or long enough that the old forms backtracked
#: over it for real, and short enough that they stay affordable as the reference.
_RUN = st.sampled_from([0, 1, 2, 7, 64, 200]).map(lambda n: " " * n)


def _blanks(max_size: int = 3) -> st.SearchStrategy[str]:
    return st.text(alphabet=_BLANKS + "\n", max_size=max_size)


def _text(alphabet: str, max_size: int = 6) -> st.SearchStrategy[str]:
    return st.text(alphabet=alphabet + _BLANKS + "\n", max_size=max_size)


def _joined(*parts: st.SearchStrategy[str]) -> st.SearchStrategy[str]:
    """The parts, generated independently and concatenated in order."""
    return st.tuples(*parts).map("".join)


def _cue_lines(keyword: str) -> st.SearchStrategy[str]:
    """A cue line: indent, the keyword (or a near miss), blanks, a value, blanks.

    For `REM` a key comes first, up to past its 64-character bound.
    """
    word = st.sampled_from([keyword, keyword.lower(), keyword[:-1], ""])
    key = (
        st.text(alphabet="A_0z", min_size=0, max_size=66)
        if keyword == "REM"
        else st.just("")
    )
    gap = _blanks()
    return _joined(
        _blanks(),
        word,
        gap,
        key,
        gap,
        _text('ax"0é'),
        _RUN,
        _text('ax"0é'),
        _RUN,
        st.sampled_from(["", "\n", "x", " \n"]),
    )


def _field_lines() -> st.SearchStrategy[str]:
    """A legacy-log field: indent, a key (blanks and hyphens allowed), a colon, a value."""
    return _joined(
        _blanks(),
        st.text(alphabet="aZ0_- \t", max_size=6),
        st.sampled_from([":", "", "::"]),
        _blanks(),
        _text("ax:0é"),
        _RUN,
        _text("ax:0é"),
        _RUN,
        st.sampled_from(["", "\n", "x", " \n"]),
    )


def _eta_values() -> st.SearchStrategy[str]:
    """cyanrip ETA values (`1h 5m`, `3m`, `42s`) and near misses, token by token."""
    token = st.one_of(
        st.text(alphabet="0123456789٣", min_size=1, max_size=9),
        st.sampled_from(["h", "m", "s", "x", "hm"]),
        st.text(alphabet=_BLANKS + "\n", min_size=1, max_size=3),
        _RUN,
    )
    return st.lists(token, max_size=8).map("".join)


def _lap_references() -> st.SearchStrategy[str]:
    """`HANDSHAKE-PEER-VERDICT-SOURCE`-shaped text: names of laps, and near misses."""
    token = st.one_of(
        st.sampled_from(["round-", "-lap-", "lap-", "round", "-", ".md", " ", "x"]),
        st.text(alphabet="0", min_size=1, max_size=200),
        st.text(alphabet="0123456789٣", min_size=1, max_size=4),
    )
    return st.lists(token, max_size=10).map("".join)


#: (module, name, old form, how its lines are generated).
_REWRITES: list[tuple[str, str, str, st.SearchStrategy[str]]] = [
    (
        "src/platterpus/cue_validate.py",
        "_RE_REM",
        r"^\s*REM\s+(?P<key>[A-Za-z0-9_]{1,64})\s+(?P<value>.*\S)\s*$",
        _cue_lines("REM"),
    ),
    (
        "src/platterpus/cue_validate.py",
        "_RE_TITLE",
        r"^\s*TITLE\s+(?P<value>.*\S)\s*$",
        _cue_lines("TITLE"),
    ),
    (
        "src/platterpus/cue_validate.py",
        "_RE_PERFORMER",
        r"^\s*PERFORMER\s+(?P<value>.*\S)\s*$",
        _cue_lines("PERFORMER"),
    ),
    (
        "src/platterpus/parsers/rip_log.py",
        "_FIELD",
        r"^(?P<indent>\s+)(?P<key>[\w][\w\s\-]*?):\s*(?P<value>.*?)\s*$",
        _field_lines(),
    ),
    (
        "src/platterpus/workers/rip_worker.py",
        "_CYANRIP_ETA_VALUE",
        r"^(?:(?P<h>\d{1,4})\s*h)?\s*(?:(?P<m>\d{1,4})\s*m)?\s*(?:(?P<s>\d{1,7})\s*s)?$",
        _eta_values(),
    ),
    (
        "scripts/handshake.py",
        "_SOURCE_NAMED_LAP",
        r"round-0*\d+-lap-0*(\d+)",
        _lap_references(),
    ),
]

_IDS: list[str] = [
    f"{rel.rsplit('/', 1)[-1]}:{name}" for rel, name, _o, _s in _REWRITES
]


def test_the_population_is_the_six_patterns_rewritten() -> None:
    """The floor for both sweeps below, which parametrize over `_REWRITES`.

    `_REWRITES` holds Hypothesis strategies, so it is built rather than written
    out, and an emptied list would turn both sweeps into one skip each. Each
    pattern the lead-in sweep found and that was fixed is named here (2026-10-06);
    a seventh fix adds its name, and none can leave without this saying which.
    """
    assert sorted(_IDS) == sorted(
        [
            "cue_validate.py:_RE_REM",
            "cue_validate.py:_RE_TITLE",
            "cue_validate.py:_RE_PERFORMER",
            "rip_log.py:_FIELD",
            "rip_worker.py:_CYANRIP_ETA_VALUE",
            "handshake.py:_SOURCE_NAMED_LAP",
        ]
    )


def _shape(match: re.Match[str] | None) -> tuple[object, ...] | None:
    """Everything a caller can read off a match: the span and every group."""
    return None if match is None else (match.span(), match.groups(), match.groupdict())


def _readings(pattern: re.Pattern[str], text: str) -> list[object]:
    """What `match`, `search`, `fullmatch` and `finditer` each make of ``text``."""
    return [
        _shape(pattern.match(text)),
        _shape(pattern.search(text)),
        _shape(pattern.fullmatch(text)),
        [_shape(found) for found in pattern.finditer(text)],
    ]


@pytest.mark.parametrize(("rel", "name", "old", "lines"), _REWRITES, ids=_IDS)
def test_each_rewrite_reads_what_its_old_form_read(
    rel: str, name: str, old: str, lines: st.SearchStrategy[str]
) -> None:
    """Same readings, on every generated input, or the rewrite is not a fix."""
    new = _pattern_assigned_to(rel, name)
    reference = re.compile(old)
    assert new.pattern != old, f"{name} still has its old form; nothing to prove"

    @settings(max_examples=200, deadline=None)
    @given(lines)
    def agrees(text: str) -> None:
        assert _readings(new, text) == _readings(reference, text)

    agrees()


#: Hand-written inputs per rewrite, including the ones the property is meant to
#: reach: real values, an empty value, all blanks, a long run inside and after.
_EXAMPLES: dict[str, list[str]] = {
    "_RE_REM": [
        'REM GENRE "Rock"',
        "  REM DATE 1999  ",
        "REM COMMENT a" + " " * 3000 + "b",
        "REM COMMENT " + " " * 3000,
        "REM " + "K" * 64 + " v",
        "REM " + "K" * 65 + " v",
        "REM KEY",
        "rem KEY v",
    ],
    "_RE_TITLE": [
        'TITLE "Album"',
        '    TITLE "Track one"   ',
        "TITLE a" + " " * 3000 + "b",
        "TITLE" + " " * 3000,
        "TITLE x",
        "TITLE x\n",
        "TITLE x\ny",
        "TITLE",
    ],
    "_RE_PERFORMER": [
        'PERFORMER "Artist"',
        '  PERFORMER "A / B"  ',
        "PERFORMER a" + " " * 3000 + "b",
        "PERFORMER" + " " * 3000,
        "PERFORMER x",
        "PERFORMER \n x",
        "PERFORMERx y",
    ],
    "_FIELD": [
        "    Pre-emphasis: ",
        "    Peak level: 98.4 %",
        "  Test CRC: 0A1B2C3D",
        "  Key: a" + " " * 3000 + "b",
        "  Key:" + " " * 3000,
        "  Two words here:   value  ",
        "  a:b:c",
        "  Key: x\ny",
        "no indent: value",
    ],
    "_CYANRIP_ETA_VALUE": [
        "1h 5m",
        "3m",
        "42s",
        "1h5m3s",
        "",
        "   ",
        "0h" + " " * 3000 + "x",
        "1h" + " " * 50 + "5m" + " " * 50,
        "12345m",
        "5 m 3 s",
    ],
    "_SOURCE_NAMED_LAP": [
        "round-30-lap-09.md",
        "a peer source: round-030-lap-0009.md",
        "round-0-lap-000",
        "round-1-lap-2 and round-3-lap-4",
        "round-" + "0" * 3000 + "x",
        "round--lap-1",
        "lap 9",
    ],
}


@pytest.mark.parametrize(("rel", "name", "old", "lines"), _REWRITES, ids=_IDS)
def test_each_rewrite_agrees_on_the_inputs_written_out(
    rel: str, name: str, old: str, lines: st.SearchStrategy[str]
) -> None:
    """The equivalence on hand-written inputs, with a floor on matches compared."""
    new = _pattern_assigned_to(rel, name)
    reference = re.compile(old)
    examples = _EXAMPLES[name]
    differing = [
        text[:40]
        for text in examples
        if _readings(new, text) != _readings(reference, text)
    ]
    assert not differing, f"{name} reads these differently: {differing!r}"
    matched = sum(reference.search(text) is not None for text in examples)
    assert matched >= 3, f"only {matched} of these inputs matched {name}'s old form"
