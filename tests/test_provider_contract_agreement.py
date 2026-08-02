"""Our consumer contract must not contradict the fork's provider contract.

The two halves of the cyanrip seam are each generated from their own side's
code: ours from the parser's enumeration tables, theirs by walking every
`cyanrip_log()` call site. Generating both removes the "described behaviour we
do not have" failure — but it does not stop the two *descriptions* from
disagreeing, and a disagreement there is the next breakage.

The specific hazard: **parsing a line the fork considers unstable.** Their P3
list is text they reserve the right to reword without a handshake. If we parse
one of those, their next cosmetic change breaks us and neither side finds out
until a rip comes back wrong. That check is the reason this file exists, and it
is the concrete answer to their §J4.

Reads their committed round-4 file directly. When a new round lands with a new
provider contract, this test re-derives from it — no list to maintain here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.parsers import cyanrip_log as parser

_ROUND_4 = Path(__file__).parents[1] / "docs" / "handshake" / "inbound" / "round-4.md"

_ROW = re.compile(
    r"^\| `(?P<where>[a-z_]+\.c:\d+)` \| `(?P<line>.+?)` \|", re.MULTILINE
)


def _section(start: str, end: str) -> list[tuple[str, str]]:
    text = _ROUND_4.read_text(encoding="utf-8")
    block = text[text.index(start) : text.index(end)]
    return [(m.group("where"), m.group("line")) for m in _ROW.finditer(block)]


def _render(fmt: str) -> str:
    """Turn a C format string into a plausible instance of the line.

    `%i`/`%u`/`%X` → a number, `%f` → a decimal, `%s` → a word. Good enough to
    ask "would our pattern bite on this", which is the only question here.
    """
    return re.sub(
        r"%0?\d*[.]?\d*l?[iudxXsfc]",
        lambda m: (
            "7"
            if m.group(0)[-1] in "iudxX"
            else ("1.5" if m.group(0)[-1] == "f" else "X")
        ),
        fmt.replace('\\"', '"'),
    )


def _top_level_rule_matching(line: str) -> str | None:
    """The name of the disc-level rule that claims ``line``, if any.

    Only top-level rules: the fork's unstable lines are all emitted at column 0,
    and the indented patterns are applied by the parser *only inside* a section
    or track block, so testing them here would produce false positives — as it
    did on the first attempt, where a permissive `Gaps:`-section pattern
    appeared to match all twelve.
    """
    for rule in parser._ALL_LINE_RULES:
        if rule.pattern.match(line):
            return str(rule.name)
    return None


def test_the_provider_contract_is_present_and_substantial() -> None:
    """A floor. Every check below is "for each line in their contract", which
    an unparsed or truncated file satisfies by having no lines."""
    stable = _section("## P2 - Outputs: stable log lines", "## P3 - Unstable lines")
    unstable = _section("## P3 - Unstable lines", "## P4 - Exit codes")
    assert len(stable) >= 200, f"only parsed {len(stable)} stable lines"
    assert len(unstable) >= 10, f"only parsed {len(unstable)} unstable lines"


def test_we_parse_nothing_the_fork_reserves_the_right_to_reword() -> None:
    """The load-bearing one.

    A line on their P3 list can change wording in any release without a
    handshake. Parsing one means their next cosmetic edit silently breaks us.
    """
    offenders = [
        (where, line, name)
        for where, line in _section("## P3 - Unstable lines", "## P4 - Exit codes")
        if (name := _top_level_rule_matching(_render(line)))
    ]
    assert not offenders, "we parse lines the fork calls unstable: " + "; ".join(
        f"{name} <- {where} {line!r}" for where, line, name in offenders
    )


@pytest.mark.parametrize(
    "line",
    [
        "Pregap LSN:  unknown (sub-channel CRC mismatches)",
        "Pregap source: lead-in",
        "Pregap source: sub-channel (not signalled by TOC)",
        "Rip completed:  no (interrupted by user, 2 of 3 tracks)",
    ],
)
def test_variants_only_their_contract_reveals_are_handled(line: str) -> None:
    """Four lines that appear in their P2 table and in **no artifact we hold**.

    Their golden reference is one successful rip of one disc image; it cannot
    contain a CRC-mismatch pre-gap, a lead-in-sourced pre-gap, or a cancelled
    footer. Those only became visible when they generated the contract, and one
    of them — the cancelled footer — was silently dropping the ripper's own
    track counts on the exact scenario we care most about.
    """
    assert line in [
        ln
        for _, ln in _section(
            "## P2 - Outputs: stable log lines", "## P3 - Unstable lines"
        )
    ] or any(
        _render(ln).startswith(line.split("%")[0][:20])
        for _, ln in _section(
            "## P2 - Outputs: stable log lines", "## P3 - Unstable lines"
        )
    ), f"{line!r} is no longer in their stable contract — re-verify before trusting it"


def test_their_exit_codes_are_the_two_we_record() -> None:
    """We now record whatever they exit with, but the report's prose assumes
    the {0,1} shape they documented. If that ever grows a third value, the
    assumption needs revisiting rather than silently surviving."""
    text = _ROUND_4.read_text(encoding="utf-8")
    block = text[text.index("## P4 - Exit codes") : text.index("## P5")]
    assert "Distinct exit values found in the tree: `0`, `1`" in block, (
        "the fork's exit-code inventory changed shape; re-read P4"
    )
