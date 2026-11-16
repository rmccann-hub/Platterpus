"""`CLAUDE.md` stays small: a ratchet on its size that may shrink, never grow.

**Why this exists (`TASKS.md` R32).** `CLAUDE.md` is loaded into every session,
so every byte in it is paid for on every task. The operator's review of
2026-10-19 (item 3) set a standard of 300 lines and 32 KiB; by 2026-11-16 the
file had grown to 676 lines and 99,225 bytes, because each new rule arrived
with its incident history inline and nothing measured the total. On the owner's
word of 2026-11-16 (*"7. a"*) it was trimmed to each rule's operative sentence
and a pointer, and everything else MOVED, word for word, to the homes the
pointers name (Critical rule #7: moved, never summarised away).

**What it holds.** The file may not grow past the size measured after that
trim. It is a two-way ratchet, like the repository's other recorded counts:
growing past the cap fails, and shrinking well below it fails too, asking for
the cap to be lowered in the same change, so there is never slack to grow
back into. A new rule that needs room makes room: move something's history
out first.

**What it does not hold.** The 300-line / 32 KiB standard itself is not yet
met in bytes (the trim reached the line count, not the byte count, without
dropping an operative rule); `_STANDARD_*` records it so the gap is stated
rather than forgotten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

_CLAUDE_MD: Final[Path] = Path(__file__).resolve().parents[1] / "CLAUDE.md"

#: The caps, measured with `wc -lc CLAUDE.md` after the R32 trim (2026-11-16).
#: Lower them when the file shrinks; never raise them.
_MAX_LINES: Final[int] = 311
_MAX_BYTES: Final[int] = 42126

#: How far below a cap the file may sit before the cap must be lowered.
_LINE_SLACK: Final[int] = 10
_BYTE_SLACK: Final[int] = 1024

#: The standard the operator's review set (R32): the target, not yet the cap.
_STANDARD_LINES: Final[int] = 300
_STANDARD_BYTES: Final[int] = 32 * 1024

#: Headings a truncated or emptied file would lose. A size check alone passes
#: on an empty file, so this is the floor that makes it a check of CLAUDE.md.
_REQUIRED_HEADINGS: Final[tuple[str, ...]] = (
    "## Code conventions",
    "## Critical rules",
    "## How to stop shipping the next one",
    "## Deviation policy",
    "## Reporting to the operator",
    "## Companion documents",
    "## Project operations",
)


def _size() -> tuple[int, int]:
    """`(lines, bytes)` of CLAUDE.md, counted the way `wc -lc` counts them."""
    data = _CLAUDE_MD.read_bytes()
    return data.count(b"\n"), len(data)


def test_claude_md_is_still_the_rules_file() -> None:
    """Floor: the ratchet below must be measuring the real file, not a stub."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    missing = [h for h in _REQUIRED_HEADINGS if h not in text]
    assert not missing, f"CLAUDE.md lost these sections: {missing}"
    lines, _ = _size()
    assert lines >= 150, f"CLAUDE.md is only {lines} lines; was it truncated?"


def test_claude_md_does_not_grow() -> None:
    lines, size = _size()
    assert lines <= _MAX_LINES and size <= _MAX_BYTES, (
        f"CLAUDE.md is {lines} lines and {size} bytes; the cap is {_MAX_LINES} "
        f"lines and {_MAX_BYTES} bytes (TASKS R32). It is loaded into every "
        "session: keep a rule's operative sentence here and move its history to "
        "the home its pointer names (Critical rule #7), rather than raise the cap."
    )


def test_the_cap_follows_the_file_down() -> None:
    """The ratchet's other half: a cap far above the file is room to regrow."""
    lines, size = _size()
    assert lines > _MAX_LINES - _LINE_SLACK and size > _MAX_BYTES - _BYTE_SLACK, (
        f"CLAUDE.md shrank to {lines} lines and {size} bytes; lower _MAX_LINES "
        f"and _MAX_BYTES in {Path(__file__).name} to those numbers in the same "
        "change, so the space it gave up cannot be taken back unnoticed."
    )


def test_the_caps_never_pass_the_r32_measurement() -> None:
    """Editing the constants upward is the one way round the ratchet; refuse it."""
    assert _MAX_LINES <= 311 and _MAX_BYTES <= 42126, (
        "the CLAUDE.md caps were raised above the R32 measurement of 2026-11-16 "
        "(311 lines, 42,126 bytes); they may only go down"
    )
    assert _STANDARD_LINES == 300 and _STANDARD_BYTES == 32 * 1024
