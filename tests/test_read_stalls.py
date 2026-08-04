"""The stall-watchdog line: their four published shapes, and the tri-state under it.

## Provenance of the expectations, stated because it decides how much they prove

The fork published four exact strings in round 7 lap 14 (D1), **derived from the code
that prints them** and each pinned on their side with a whole-string `strcmp`. Their
own caveat, which we are keeping rather than dropping:

> *"these are derived from the code that will print them, exercised through the real
> formatter. They are **not observed output** — no build has yet printed a populated
> one anywhere."*

So this file pins our structuring against **unobserved wording**, and the design
follows from that: the verbatim text is the authoritative record and
`read_stalls_count` is a best-effort layer on top. An unrecognised shape must yield
`None` beside intact text, never `0` — degrading to `0` would report *"no stalls
measured"* about a log that might be saying the opposite, which is the tri-state rule
broken in the direction that loses a real warning.

We asked for the shapes rather than inventing them because a guessed regex is what
put `merged` in our gap matcher for two rounds. The singular in `1 read exceeded` —
not `1 reads` — is exactly the detail a guess gets wrong.
"""

from __future__ import annotations

import pytest

from platterpus.parsers.cyanrip_log import parse_cyanrip_log, read_stall_count

#: The fork's four published shapes, verbatim from round 7 lap 14 §D1, with the count
#: each must yield. Copied character-for-character; if a value here is edited to make a
#: test pass, the test has stopped measuring anything.
PUBLISHED_SHAPES: dict[str, int | None] = {
    "unknown (stall reporting disabled with -k 0)": None,
    "none (no read exceeded 10s)": 0,
    "2 reads exceeded 10s; longest 187s (track 4, LSN 45231)": 2,
    "1 read exceeded 30s; longest 42s (track 1, LSN 0)": 1,
}


@pytest.mark.parametrize(("value", "expected"), PUBLISHED_SHAPES.items())
def test_each_published_shape_yields_its_count(
    value: str, expected: int | None
) -> None:
    assert read_stall_count(value) == expected, value


def test_all_four_shapes_are_covered_and_distinguish_three_states() -> None:
    """Floor. Four strings that all mapped to one answer would prove nothing.

    The three states must actually be reachable from their published set, or the
    tri-state is decoration.
    """
    assert len(PUBLISHED_SHAPES) == 4
    answers = set(PUBLISHED_SHAPES.values())
    assert None in answers, "no shape exercises the unknown state"
    assert 0 in answers, "no shape exercises the measured-none state"
    assert any(isinstance(a, int) and a > 0 for a in answers), (
        "no shape exercises a populated count — the state that raises an issue"
    )


def test_the_singular_form_is_not_a_typo_we_normalised_away() -> None:
    """`1 read exceeded`, not `1 reads`. A guessed `reads` would have missed it.

    Asserted on its own because it is the single detail in their published set that a
    hand-written regex is most likely to get wrong, and the reason we asked for the
    strings instead of writing them.
    """
    singular = "1 read exceeded 30s; longest 42s (track 1, LSN 0)"
    assert singular in PUBLISHED_SHAPES
    assert read_stall_count(singular) == 1
    assert "1 reads" not in singular


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "some future wording nobody has written yet",
        "reads exceeded 10s",  # a count-shaped line with no count
        "NONE (no read exceeded 10s)",  # case they have not published
        "0 reads exceeded 10s",  # a shape they did not publish; parsed, not assumed
        "\x00",
        "9" * 5000 + " reads exceeded 10s",
    ],
)
def test_an_unrecognised_shape_is_none_never_zero(value: str) -> None:
    """The direction that matters, and it is the safe one.

    `0` is a claim: *the ripper measured and found none*. Reaching it from a shape we
    do not understand would invent that measurement. `None` says we could not tell,
    which is true.
    """
    result = read_stall_count(value)
    if value.strip().startswith("0 reads"):
        # A published-shaped line with a real zero IS a measurement, so 0 is correct.
        assert result == 0
        return
    assert result != 0 or result is None
    assert result is None or result > 0


def test_it_never_raises_on_a_pathological_digit_run() -> None:
    """CPython refuses a digit run over 4300 chars; the parser must not.

    `read_stall_count` reads a dependency's prose, so the never-raises rule applies and
    the guard is `int_or_none` rather than `int`.
    """
    assert read_stall_count("5" * 9000 + " reads exceeded 10s") is None


def test_the_verbatim_text_survives_an_unrecognised_shape() -> None:
    """The layering, asserted end to end through a real parse.

    A shape we cannot structure must still reach the report *as the ripper's own
    sentence*. Losing the text in exchange for a null count would be the worst of both:
    no number and no evidence.
    """
    log = (
        "cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-gdeadbee)\n"
        "Disc tracks:    1\n"
        "Ripping errors: 0\n"
        "Read stalls:    a wording from some future build\n"
        "Rip completed:  yes (1 of 1 tracks)\n"
    )
    parsed = parse_cyanrip_log(log)
    assert parsed.read_stalls == "a wording from some future build"
    assert parsed.read_stalls_count is None


def test_a_populated_count_raises_exactly_one_issue_and_quotes_the_ripper() -> None:
    """The whole point of structuring it: a stalling drive must be visible.

    A rip whose read took 187 seconds is worth telling the user about even when every
    checksum came out right — that is how a disc goes from readable to unreadable. And
    the entry quotes the ripper's own sentence rather than paraphrasing a number out of
    it.
    """
    from platterpus.rip_report import _issues

    detail = "2 reads exceeded 10s; longest 187s (track 4, LSN 45231)"
    issues = _issues(
        outcome=None,
        verdict_level="ok",
        ctdb=None,
        flac_integrity=None,
        derived=None,
        transcode=None,
        cover_art=None,
        read_speed=None,
        rip={"read_stalls": detail, "read_stalls_count": 2},
    )
    stalls = [i for i in issues if i["code"] == "ripper_read_stalls"]
    assert len(stalls) == 1, [i["code"] for i in issues]
    assert stalls[0]["severity"] == "warning"
    assert detail in stalls[0]["message"], "the finding paraphrases instead of quoting"


@pytest.mark.parametrize(
    ("count", "text"),
    [
        (0, "none (no read exceeded 10s)"),
        (None, "unknown (stall reporting disabled with -k 0)"),
        (None, None),
    ],
)
def test_a_clean_or_unmeasured_rip_raises_nothing(
    count: int | None, text: str | None
) -> None:
    """The false-positive half, and the half that decides whether the entry survives.

    `0` is a clean measurement; `None` is no measurement. An entry for either would
    appear on every stock rip and train a reader to skip the code.
    """
    from platterpus.rip_report import _issues

    issues = _issues(
        outcome=None,
        verdict_level="ok",
        ctdb=None,
        flac_integrity=None,
        derived=None,
        transcode=None,
        cover_art=None,
        read_speed=None,
        rip={"read_stalls": text, "read_stalls_count": count},
    )
    assert "ripper_read_stalls" not in {i["code"] for i in issues}
