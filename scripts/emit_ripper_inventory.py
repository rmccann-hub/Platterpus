#!/usr/bin/env python3
"""Regenerate the ripper message inventory from the fork's published contract.

**Why this exists, and why it did not before.** `ripper_message_inventory.py` has
said *"Do not hand-edit. Regenerate when a handshake round ships a new inventory"*
since it was written, and **there was no tool to regenerate it with**. So every
round it was edited by hand, and the module docstring records what that cost: the
file sat at round 6's 115 rows for five rounds while seven newer contracts were
committed to this repository — including one whose covering lap said in prose that
ten rows had been added.

That is the shape this project names most often: an instruction where a mechanism
belongs. Round 16 made it concrete again. The fork's generator had been deleting
interior newlines from format strings, so three published rows were single lines
no build prints; correcting them by hand fixed the *strings* and left every
`file:line` in the module pointing at round 15's source, because their line
numbers move with every commit. Two expressions of one contract, disagreeing.

**What it generates, and what it deliberately does not.**

* `MESSAGES` — the P5 table, verbatim from the contract. Derived, so it cannot
  drift.
* `tests/fixtures/cyanrip_fatal_messages.tsv` — the same rows plus P5a, which the
  tests read as the independent copy. Generated from the same parse, in one run,
  so the two cannot disagree about what the contract said.

It does **not** touch `RETAINED_BEYOND_P5`, `SURFACING_EXCLUDED` or
`P5A_NOT_RETAINED`. Those carry hand-written reasons for keeping or dropping a
row, and a reason is not derivable from the document that caused it. Regenerating
them would delete exactly the part a person has to think about.

**Usage**

    python3 scripts/emit_ripper_inventory.py           # write
    python3 scripts/emit_ripper_inventory.py --check   # exit 1 if stale

The contract it reads is the newest one filed under
`docs/handshake/inbound/artifacts/`, chosen by round then lap — the same rule the
surfacing tests use, and for the same reason: filesystem order is not lap order.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
ARTIFACTS: Final[Path] = REPO_ROOT / "docs" / "handshake" / "inbound" / "artifacts"
INVENTORY: Final[Path] = (
    REPO_ROOT / "src" / "platterpus" / "ripper_message_inventory.py"
)
FIXTURE: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "cyanrip_fatal_messages.tsv"

#: A filed provider contract: `round-NN-lap-LL-provider-contract-<tag>.md`.
_CONTRACT_NAME: Final[re.Pattern[str]] = re.compile(
    r"^round-(?P<round>\d+)-lap-(?P<lap>\d+)-provider-contract-(?P<tag>[^.]+)\.md$"
)

#: One row of P5 or P5a. The message is fenced in backticks and may itself contain
#: backslash escapes; everything between the first and last backtick of that cell
#: is the payload, so a message containing a backtick would need care — none does,
#: and `--check` would fail loudly rather than silently mis-parse if one appeared.
_ROW: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*`(?P<site>[^`]+)`\s*\|\s*`(?P<text>.*)`\s*\|"
    r"\s*(?P<evidence>[^|]+?)\s*\|\s*(?P<logfile>[^|]+?)\s*\|\s*$"
)

#: **The "Reaches logfile?" column is TRI-STATE and the first version of this
#: parser only accepted two of the three.** `yes`, `no`, and
#: `**not directly** - see legend` — the last for calls that reach the logfile
#: only indirectly. Requiring `yes|no` silently dropped three rows, and the
#: failure looked like a shrinking contract rather than a narrow regex: the
#: generator reported 117 where the table has 120, which is the *"can this check
#: be satisfied by finding nothing?"* question arriving as an off-by-three.
#:
#: It maps to `False`, matching what the hand-maintained file recorded for these
#: same rows, and the safe direction: we do not claim a message is in the logfile.
#: The contract's own wording survives in `evidence` and in the fixture, so the
#: distinction is not lost, only not expressed by this boolean.
_LOGFILE_TRUE: Final[str] = "yes"

_P5_HEADING: Final[str] = "## P5 - Fatal and error message inventory"
_P5A_HEADING: Final[str] = "## P5a - Strings this document does NOT classify"


@dataclass(frozen=True)
class Row:
    """One published row, exactly as the contract states it."""

    site: str
    text: str
    evidence: str
    reaches_logfile: bool


def newest_contract() -> Path:
    """The filed contract with the highest (round, lap).

    By LAP and not by filesystem order: a round can publish more than one, and
    `sorted()` over names put lap 8 after lap 10 the last time this was left to
    the filesystem.
    """
    best: tuple[tuple[int, int], Path] | None = None
    for path in ARTIFACTS.glob("round-*-provider-contract-*.md"):
        match = _CONTRACT_NAME.match(path.name)
        if not match:
            continue
        key = (int(match.group("round")), int(match.group("lap")))
        if best is None or key > best[0]:
            best = (key, path)
    if best is None:
        raise SystemExit(f"no provider contract filed under {ARTIFACTS}")
    return best[1]


def _section(lines: list[str], heading: str, stop: str | None) -> list[str]:
    """The lines between ``heading`` and ``stop`` (or the next `## `)."""
    try:
        start = lines.index(heading)
    except ValueError:
        raise SystemExit(f"contract has no section {heading!r}") from None
    out: list[str] = []
    for line in lines[start + 1 :]:
        if stop is not None and line == stop:
            break
        if stop is None and line.startswith("## "):
            break
        out.append(line)
    return out


def parse(contract: Path) -> tuple[list[Row], list[Row]]:
    """``(P5, P5a)`` rows, in document order.

    A floor on both: a table that parses to nothing is a parser that has stopped
    matching, not a contract that has emptied, and the difference has to be
    loud. This is the *"can this check be satisfied by finding nothing?"*
    question asked of the generator rather than of the tests it feeds.
    """
    lines = contract.read_text(encoding="utf-8").splitlines()

    def rows_in(section: list[str]) -> list[Row]:
        found: list[Row] = []
        for line in section:
            match = _ROW.match(line)
            if not match:
                continue
            found.append(
                Row(
                    site=match.group("site"),
                    text=_unescape_cell(match.group("text")),
                    evidence=match.group("evidence").strip(),
                    reaches_logfile=match.group("logfile") == _LOGFILE_TRUE,
                )
            )
        return found

    p5 = rows_in(_section(lines, _P5_HEADING, _P5A_HEADING))
    p5a = rows_in(_section(lines, _P5A_HEADING, None))

    if len(p5) < 100:
        raise SystemExit(
            f"P5 parsed to {len(p5)} rows, which is far below any published "
            "inventory — the row pattern has stopped matching"
        )
    if not p5a:
        raise SystemExit("P5a parsed to nothing; the section split may have moved")
    return p5, p5a


def _unescape_cell(text: str) -> str:
    r"""Undo the escaping the contract applies to a markdown table cell.

    Their generator escapes `"` and `|` so a cell cannot break the table, and the
    payload is the C source literal underneath. **`\n` is NOT unescaped**: in the C
    source it is two characters, and the whole point of their round-16 fix was to
    stop deleting it — turning it into a real newline here would undo that from the
    other side.

    This must agree exactly with how the surfacing tests read the same document
    (`tests/test_ripper_error_surfacing.py`, the `.replace` pair). Two readers of
    one table that unescape differently is the same "two expressions of one
    contract" defect this generator exists to end, one level down.
    """
    return text.replace(chr(92) + chr(34), chr(34)).replace(chr(92) + "|", "|")


def _py_literal(text: str) -> str:
    """A Python string literal for ``text``, preserving backslashes verbatim.

    The contract publishes the C *source* literal, so a `\\n` in it is the two
    characters and must stay two characters. `repr()` gets this right and a
    hand-rolled quoter does not, which is the whole reason this is a function
    with a comment rather than an f-string.
    """
    return repr(text)


def render_messages(p5: list[Row]) -> str:
    """The `MESSAGES` tuple body."""
    out: list[str] = []
    for row in p5:
        out.append("    RipperMessage(")
        out.append(f"        site={_py_literal(row.site)},")
        out.append(f"        text={_py_literal(row.text)},")
        out.append(f"        evidence={_py_literal(row.evidence)},")
        out.append(f"        reaches_logfile={row.reaches_logfile},")
        out.append("    ),")
    return "\n".join(out)


def render_fixture(contract: Path, p5: list[Row], p5a: list[Row]) -> str:
    """The TSV the tests read as the independent copy of the same contract."""
    match = _CONTRACT_NAME.match(contract.name)
    assert match is not None  # newest_contract() only returns matching names
    head = [
        f"# cyanrip fork fatal/error message inventory — {len(p5)} in P5 + "
        f"{len(p5a)} in P5a, handshake round {int(match.group('round'))}.",
        "#",
        "# GENERATED by scripts/emit_ripper_inventory.py from",
        f"#   {contract.relative_to(REPO_ROOT)}",
        "# Do not hand-edit: regenerate. The generator and the in-code inventory",
        "# are produced in one run from one parse, so the two copies the tests",
        "# compare cannot disagree about what the contract said — only about",
        "# whether we have kept up with it, which is the question worth asking.",
        "#",
    ]
    body = [f"{row.site}\t{row.text}" for row in p5]
    tail = [
        "# --- P5a: strings the contract does NOT classify as failures ---------",
        *(f"{row.site}\t{row.text}" for row in p5a),
    ]
    return "\n".join([*head, *body, *tail]) + "\n"


def rewrite_inventory(p5: list[Row]) -> str:
    """The module with its `MESSAGES` block replaced and nothing else touched."""
    text = INVENTORY.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(?P<head>^MESSAGES: Final\[tuple\[RipperMessage, \.\.\.\]\] = \(\n)"
        r"(?P<body>.*?)"
        r"(?P<tail>^\)\n)",
        re.S | re.M,
    )
    match = pattern.search(text)
    if match is None:
        raise SystemExit("could not find the MESSAGES tuple to replace")
    return (
        text[: match.start()]
        + match.group("head")
        + render_messages(p5)
        + "\n"
        + match.group("tail")
        + text[match.end() :]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if either artifact is stale, writing nothing",
    )
    args = parser.parse_args()

    contract = newest_contract()
    p5, p5a = parse(contract)
    new_module = rewrite_inventory(p5)
    new_fixture = render_fixture(contract, p5, p5a)

    stale: list[str] = []
    if INVENTORY.read_text(encoding="utf-8") != new_module:
        stale.append(str(INVENTORY.relative_to(REPO_ROOT)))
    if FIXTURE.read_text(encoding="utf-8") != new_fixture:
        stale.append(str(FIXTURE.relative_to(REPO_ROOT)))

    if args.check:
        if stale:
            print(
                f"stale against {contract.name}: " + ", ".join(stale),
                file=sys.stderr,
            )
            return 1
        print(f"up to date against {contract.name} ({len(p5)} P5, {len(p5a)} P5a)")
        return 0

    INVENTORY.write_text(new_module, encoding="utf-8")
    FIXTURE.write_text(new_fixture, encoding="utf-8")
    print(
        f"wrote {INVENTORY.relative_to(REPO_ROOT)} and "
        f"{FIXTURE.relative_to(REPO_ROOT)} from {contract.name} "
        f"({len(p5)} P5, {len(p5a)} P5a)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
