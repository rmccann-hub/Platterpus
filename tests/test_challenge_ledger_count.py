"""The challenge ledger's headline count is DERIVED from its rows, not asserted.

**Why this exists.** ``docs/cyanrip-handshake.md`` §9 is the ledger the maintainer
asked for on 2026-08-26, in these words:

    *"if they tend to be more correct than wrong, you should find out why and adopt
    the logic if possible, but let them try it out until you have measurable results
    either way."*

*Measurable* — so the table carries one row per resolved challenge and a headline
sentence stating the tally.

**The headline was wrong, and it had been wrong before anyone noticed.** It read
*"fork right 8, us right 6, of 14"*; the fourteen rows tally fork 9 / us 5. When
two rows were added on 2026-09-13 the new figure was produced by **adding to the
old sentence** rather than re-counting the rows, so the error propagated and grew.
Two lines below it, a sub-count over rows 10–16 was correct — because that one was
derived.

That is ``CLAUDE.md``'s *am I answering from the artifact, or from my memory of the
artifact?*, landing on the one table whose entire purpose is to not be answered
from memory. A corrected number would decay at the next row. A derived one cannot.

**Deliberately strict about the "who was right" vocabulary.** A row whose verdict
is neither ``THEM`` nor ``US`` is a parse failure here rather than a silently
dropped row — a tally over a population that quietly shrinks is the shape this repo
refuses everywhere else.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LEDGER = _REPO_ROOT / "docs" / "cyanrip-handshake.md"

#: A ledger row: ``| 12 | **r16 lap 9 §2** | … | **THEM** | … |``
_ROW = re.compile(r"^\| (\d+) \| \*\*r.*$", re.MULTILINE)

#: The headline sentence the rows have to agree with.
_HEADLINE = re.compile(
    r"fork right (?P<fork>\d+), us right (?P<us>\d+), of\s+(?P<total>\d+)\s*\n?resolved"
)

#: The sub-count over the rows made under the challenge mandate (2026-08-26).
_SUBCOUNT = re.compile(
    r"Rows (?P<lo>\d+)[–-](?P<hi>\d+)\s*\n?\s*are the \w+ made under it: "
    r"fork right (?P<fork>\d+), us right (?P<us>\d+)"
)

#: First row made under the challenge mandate. Rows 1-9 predate it.
_MANDATE_FIRST_ROW = 10


def _rows() -> list[tuple[int, str]]:
    """``(row number, verdict)`` for every ledger row, verdict normalised."""
    text = _LEDGER.read_text(encoding="utf-8")
    out: list[tuple[int, str]] = []
    for match in _ROW.finditer(text):
        cells = [c.strip() for c in match.group(0).split("|")]
        # | '' | num | round·lap | challenge | who was right | settled by | mechanism |
        assert len(cells) >= 6, f"row {match.group(1)} has {len(cells)} cells"
        plain = re.sub(r"[*_`]", "", cells[4]).strip().upper()
        if plain.startswith("THEM"):
            verdict = "THEM"
        elif plain.startswith("US"):
            verdict = "US"
        else:
            verdict = f"UNPARSED:{cells[4][:40]}"
        out.append((int(match.group(1)), verdict))
    # FLOOR. Every assertion below is over this list, and all of them pass happily
    # against an empty one — which is exactly the *can this check be satisfied by
    # finding nothing?* failure, asked of a counter.
    assert len(out) >= 14, (
        f"only {len(out)} ledger row(s) parsed from {_LEDGER.name}; there were 16 on "
        "2026-09-13. Either rows were removed or the row pattern stopped matching, "
        "and a tally over a shrunken population is confidently wrong rather than "
        "merely stale."
    )
    return out


def test_every_ledger_row_states_a_verdict_this_counter_understands() -> None:
    """A row nobody can tally is a row silently excluded from the tally."""
    unparsed = [(n, v) for n, v in _rows() if v.startswith("UNPARSED")]
    assert not unparsed, (
        f"ledger row(s) {unparsed} have a 'who was right' cell this counter cannot "
        "read. Write THEM or US (bold is fine). A row that does not parse is "
        "dropped from the count without anything saying so — which is how the "
        "headline drifted in the first place."
    )


def test_row_numbers_are_contiguous_from_one() -> None:
    """A gap or a duplicate makes 'of N' mean two different things."""
    numbers = [n for n, _ in _rows()]
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"ledger row numbers are {numbers} — they must run 1..N with no gaps or "
        "repeats, or the headline's 'of N' is not the number of rows."
    )


def test_the_headline_count_matches_the_rows_it_summarises() -> None:
    """The check the headline never had. It was wrong by one in each direction."""
    rows = _rows()
    fork = sum(1 for _, v in rows if v == "THEM")
    us = sum(1 for _, v in rows if v == "US")

    text = _LEDGER.read_text(encoding="utf-8")
    match = _HEADLINE.search(text)
    assert match is not None, (
        "no 'fork right N, us right M, of T resolved' headline found in §9. It is "
        "what makes the ledger readable at a glance; if the wording changed, update "
        "this pattern rather than deleting the check."
    )

    stated = (int(match["fork"]), int(match["us"]), int(match["total"]))
    actual = (fork, us, len(rows))
    assert stated == actual, (
        f"the ledger headline says fork {stated[0]} / us {stated[1]} of {stated[2]}, "
        f"but the rows tally fork {actual[0]} / us {actual[1]} of {actual[2]}. "
        "**Re-derive the number; do not adjust the old one.** The previous error "
        "came from adding to the sentence instead of counting the rows, which is "
        "why adding two rows moved it further from the truth rather than nearer."
    )


def test_the_mandate_subcount_matches_its_rows_too() -> None:
    """The half that was already right, pinned so it stays right.

    It was correct while the headline was wrong, for exactly one reason: it was
    derived from the rows. That is the property worth keeping, not the number.
    """
    text = _LEDGER.read_text(encoding="utf-8")
    match = _SUBCOUNT.search(text)
    assert match is not None, (
        "no 'Rows X–Y are the N made under it: fork right A, us right B' sentence "
        "found. It is the only count that speaks to the maintainer's actual "
        "question, since rows before the mandate are a different population."
    )

    lo, hi = int(match["lo"]), int(match["hi"])
    assert lo == _MANDATE_FIRST_ROW, (
        f"the sub-count starts at row {lo}; the challenge mandate was issued "
        f"2026-08-26 and row {_MANDATE_FIRST_ROW} is the first made under it. A "
        "sub-count over the wrong window answers a different question in the same "
        "words."
    )

    rows = _rows()
    assert hi == len(rows), (
        f"the sub-count ends at row {hi} but the ledger now has {len(rows)} rows. "
        "It must run to the newest row, or it is quietly reporting a stale window."
    )

    window = [v for n, v in rows if lo <= n <= hi]
    fork = sum(1 for v in window if v == "THEM")
    us = sum(1 for v in window if v == "US")
    assert (fork, us) == (int(match["fork"]), int(match["us"])), (
        f"the mandate sub-count says fork {match['fork']} / us {match['us']} over "
        f"rows {lo}–{hi}, but those rows tally fork {fork} / us {us}."
    )


def test_the_counter_can_actually_fail() -> None:
    """Non-vacuity, proved by mutation rather than by a forbidden string.

    Every assertion above is a comparison against a number parsed out of prose, and
    all of them would hold if the parse silently returned nothing. This flips one
    row's verdict in memory and requires the tally to move — the same discipline as
    ``scripts/revert_probe.py``: a check never observed to fail is indistinguishable
    from one that cannot.
    """
    rows = _rows()
    baseline = sum(1 for _, v in rows if v == "THEM")
    flipped = [(n, "US" if v == "THEM" else v) for n, v in rows]
    mutated = sum(1 for _, v in flipped if v == "THEM")
    assert mutated < baseline, (
        "flipping every THEM verdict did not lower the THEM tally, so the tally is "
        "not reading the verdict column at all"
    )
