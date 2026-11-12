# SPDX-License-Identifier: GPL-3.0-only
""" "Burn" means writing a disc, and nothing else, on both sides of the seam.

**Why this exists (the owner, 2026-11-11).** Round 39's five back-to-back rips
of the reference disc were called a "test burn" in both projects' laps, scripts
and docs, borrowed from *burn-in test*. The owner, who plans no disc writing:
*"you guys keep saying burn rips, what do you mean? a rip is a read from the
drive, a burn is write to a cd to the drive. i do not plan to do burns right
now."* and *"both sides shouldnt use burn unless they mean it as i said"*. In a
program whose whole job is reading discs, a word that means writing one, used
for a read, is a wrong statement about what the drive did. The rule is in
`CLAUDE.md` (*Working with the maintainer*); this is the check behind it.

**What it reads.** Every tracked text file, except the RECORDS, which keep what
was written when it was written: sent and received laps and their artifacts
(`docs/handshake/` but its README and our status block), `docs/archive/`,
`CHANGELOG.md`'s released sections, `docs/session-log.md`, the evidence
manifest, and test fixtures that copy a lap. A line passes when it is about
writing a disc (a CD-R someone burned, a "burner" program, the desktop entry's
`DiscBurning` category) or is one of the quotes listed below, each with why it
is quoted rather than reworded.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final

_REPO: Final[Path] = Path(__file__).resolve().parents[1]
_THIS: Final[str] = "tests/test_burn_means_writing_a_disc.py"

#: Any form of the word.
_BURN: Final[re.Pattern[str]] = re.compile(r"burn", re.IGNORECASE)

#: A line that uses the word for writing a disc, which is the one meaning allowed.
_WRITING: Final[re.Pattern[str]] = re.compile(
    r"CD-R|CD-RW|burner|DiscBurning|re-burn|burnable|burned disc|burned CD"
    r"|disc is a burn|burned rather than pressed|burned from|burned yourself"
    r"|self-burned|home-burned|cdrinfo"
    # A line that states this rule names the word to retire it.
    r"|means writing a disc",
    re.IGNORECASE,
)

#: Quotes kept as written: ``{path: (text on the line, why it is kept)}``.
_QUOTES: Final[dict[str, tuple[str, str]]] = {
    "TASKS.md": (
        "first burn proof",
        "the owner's own words of 2026-07-30, quoted",
    ),
    "docs/hardware-test-checklist.md": (
        "first-burn proof",
        "the same words of the owner's, quoted",
    ),
    "scripts/evidence_names.py": (
        "burn",
        "0.7.122's album-folder name, which the bundle filed at ac0a5133 carries "
        "and the filing tool must still read",
    ),
    "tests/test_evidence_file.py": (
        "burn",
        "the test of that old folder name and its filed names (burnripN)",
    ),
}


def _is_record(path: str) -> bool:
    """A file that keeps what was written when it was written."""
    if path.startswith("docs/handshake/"):
        return path not in (
            "docs/handshake/README.md",
            "docs/handshake/outbound/platterpusstatus.md",
        )
    return path.startswith(("docs/archive/", "tests/fixtures/")) or path in (
        "docs/session-log.md",
        "docs/evidence-manifest.tsv",
        _THIS,
    )


def _unreleased(text: str) -> str:
    """CHANGELOG's ``[Unreleased]`` section: released sections are records."""
    start = text.index("## [Unreleased]")
    end = text.index("\n## [", start + 1)
    return text[start:end]


def _offending_lines() -> tuple[list[str], int, int]:
    """``(lines that misuse the word, files examined, writing-sense lines seen)``."""
    listed = subprocess.run(
        ["git", "ls-files"], cwd=_REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    bad: list[str] = []
    examined = writing = 0
    for path in listed:
        if _is_record(path):
            continue
        try:
            text = (_REPO / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # a binary or unreadable file holds no prose
        examined += 1
        if path == "CHANGELOG.md":
            text = _unreleased(text)
        quote = _QUOTES.get(path)
        for number, line in enumerate(text.splitlines(), start=1):
            if not _BURN.search(line):
                continue
            if _WRITING.search(line):
                writing += 1
                continue
            if quote is not None and quote[0] in line:
                continue
            bad.append(f"{path}:{number}: {line.strip()[:160]}")
    return bad, examined, writing


def test_burn_is_only_used_for_writing_a_disc() -> None:
    bad, examined, writing = _offending_lines()
    # Floors: a sweep that read nothing, or found no genuine use of the word to
    # let through, proves nothing about the lines it did not see.
    assert examined >= 500, f"only {examined} tracked text files read"
    assert writing >= 8, f"only {writing} disc-writing uses seen: the filter is off"
    assert not bad, (
        '"burn" means writing a disc (the owner, 2026-11-11); reword these, or '
        "quote them in _QUOTES with the reason:\n" + "\n".join(bad)
    )


def test_every_quote_is_still_on_its_line() -> None:
    """A stale quote entry would excuse the next misuse in that file."""
    for path, (text, why) in _QUOTES.items():
        assert len(why) >= 20, f"{path}: the reason is not a reason"
        content = (_REPO / path).read_text(encoding="utf-8")
        assert text in content, f"{path}: the quoted {text!r} is gone; drop the entry"
