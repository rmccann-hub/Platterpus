"""The pre-built tests: each one an ordered list of blocks, or one packaged script.

**The owner's design** (TASKS R188, 2026-11-17): one **Run tests…** screen,
where a person chooses a pre-built test, a hand-picked combination of blocks, or
a script file. This module is the first of those three: the list of pre-built
tests, each defined once, here, as data.

* **Full, Standard and Quick acceptance** are the same nineteen blocks, joined in
  the Full run's order, and run at three sizes (``uiscript/run_sizes.py``): the
  sizes were always cut from one file, and they still are.
* **The Quick check** is the Quick check's eight blocks.
* **Repeat rips ×5** is the three setup blocks, then
  ``run-block repeatrip ×5 as repeat`` and the comparisons that must hold across
  the five runs, each declared here in advance with its severity, as the owner
  asked (2026-11-17: *a block, a count and the comparison that must hold*). The
  Full run's own five repeat rips stay one fixed block, so Full's steps do not
  change (the owner, 2026-11-23).
* **The drive setup check** is the drive setup block with what it needs.
* **Every other packaged script** the owner may be told to run (the over-read
  probe among them, which R188 began with) is listed by its file, whole, until it
  is cut into blocks. Three leave the list, named in :data:`LEFT_OFF_THE_LIST`
  with why; their files stay, because docs and tests use them.

**Evidence is unchanged.** A run counts as evidence only when it is a Full-size
run of the Full test (or an unnamed hand run, which is what it was before), read
by :func:`platterpus.uiscript.run_sizes.counts_as_evidence`.

The owner's own scripts, and the check any chosen file passes, are
``uiscript/script_files.py``.

Pure and Qt-free. The only disk access is reading a small packaged file.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.uiscript import blocks, run_sizes
from platterpus.uiscript.find_script import packaged_scripts_dir

#: Packaged scripts that are NOT offered, each with why (TASKS R188). Their files
#: stay: documents and tests read them.
LEFT_OFF_THE_LIST: Final[dict[str, str]] = {
    "round08joint.txt": "a joint script of round 8, kept as the record of it",
    "police-rerip.txt": "one album's re-rip of 2026-08, the language's worked example",
    "track3abba.txt": "a one-off measurement of track 3, kept with its results",
}


@dataclass(frozen=True)
class Repeat:
    """A block run N times under one label, and what must hold across the runs.

    Each rule is an ``expect-repeats`` rule (``same-crc``, ``verified``,
    ``at-least K of N``). Its severity is declared here, before any run: every
    rule below is a FAIL when it does not hold, because each one is what the
    owner asked a repeat to prove.
    """

    block: str
    count: int
    label: str
    rules: tuple[str, ...]

    def script(self) -> str:
        """The lines that run it: one ``run-block`` and one check per rule."""
        lines = [f"run-block {self.block} ×{self.count} as {self.label}"]
        lines += [f"expect-repeats {self.label} {rule}" for rule in self.rules]
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class PrebuiltTest:
    """One pre-built test: its name, what a person reads, and what it runs."""

    name: str
    title: str
    #: One line saying what it is for and how long it takes.
    about: str
    size: str = run_sizes.FULL
    #: The blocks it runs, in order; empty for a whole packaged script.
    blocks: tuple[str, ...] = ()
    #: Repeats run after the blocks.
    repeats: tuple[Repeat, ...] = ()
    #: A packaged script run whole, for a test not yet cut into blocks.
    script_file: str = ""
    #: Roughly how long it takes, said before it starts.
    duration: str = ""

    def run_titles(self) -> tuple[str, ...]:
        """What it runs, in order, by TITLE (never a block's internal name)."""
        if self.script_file:
            return (self.title,)
        titles = [blocks.title_of(name) for name in self.blocks]
        for repeat in self.repeats:
            titles.append(f"{blocks.title_of(repeat.block)} ×{repeat.count}")
        return tuple(titles)

    def block_names(self) -> tuple[str, ...]:
        """Every block it runs, for the report: blocks, then repeated ones."""
        return self.blocks + tuple(repeat.block for repeat in self.repeats)

    def text(self) -> tuple[str, str]:
        """``(script text, problem)``: what this test runs. Never raises."""
        if self.script_file:
            path = packaged_scripts_dir() / self.script_file
            try:
                return path.read_text(encoding="utf-8"), ""
            except (OSError, UnicodeDecodeError) as exc:
                return "", f"{self.title}: {path} could not be read: {exc}"
        joined, problem = blocks.joined_text(self.blocks)
        if problem:
            return "", problem
        return joined + "".join(repeat.script() for repeat in self.repeats), ""

    def packaged_path(self) -> Path | None:
        """The packaged file this test IS byte for byte, if it is one."""
        if self.script_file:
            return packaged_scripts_dir() / self.script_file
        for name, order in blocks.GENERATED_FILES.items():
            if self.blocks == order and not self.repeats:
                return packaged_scripts_dir() / name
        return None


#: The Full acceptance test's name: the one test whose Full-size run is evidence.
FULL_TEST: Final[str] = run_sizes.FULL_TEST_NAME

_REPEAT_FIVE: Final[Repeat] = Repeat("repeatrip", 5, "repeat", ("verified", "same-crc"))

#: Every pre-built test, in the order the screen lists them.
PREBUILT: Final[tuple[PrebuiltTest, ...]] = (
    PrebuiltTest(
        FULL_TEST,
        "Full acceptance",
        "Every section, in order: the one run that counts as evidence.",
        run_sizes.FULL,
        blocks.FULL_ORDER,
        duration="4 to 6 hours",
    ),
    PrebuiltTest(
        "standard",
        "Standard acceptance",
        "The Full run's sections that say whether a normal rip is right.",
        run_sizes.STANDARD,
        blocks.FULL_ORDER,
        duration="about an hour",
    ),
    PrebuiltTest(
        "quick",
        "Quick acceptance",
        "The Full run's quickest sections: does it still work?",
        run_sizes.QUICK,
        blocks.FULL_ORDER,
        duration="about 15 minutes",
    ),
    PrebuiltTest(
        "quickcheck",
        "Quick check",
        "One track, graded like the Full run's rips, before you start one.",
        run_sizes.FULL,
        blocks.QUICK_ORDER,
        duration="about 5 minutes",
    ),
    PrebuiltTest(
        "repeatrips",
        "Repeat rips ×5",
        "Five default whole-disc rips: every track verified in every run, and "
        "each track's CRC the same in all five.",
        run_sizes.FULL,
        blocks.SETUP_ORDER,
        (_REPEAT_FIVE,),
        duration="about 5 hours",
    ),
    PrebuiltTest(
        "drivesetup",
        "Drive setup check",
        "Once per drive: its read offset, cyanrip's own offset finder, its cache.",
        run_sizes.FULL,
        blocks.combination(("drivesetup",)),
        duration="about 10 minutes",
    ),
    PrebuiltTest(
        "overreadprobe",
        "Over-read probe",
        "One bounded -O read of the last track, then of track 1.",
        script_file="overreadprobe.txt",
        duration="about 10 minutes",
    ),
    PrebuiltTest(
        "isrcdisc",
        "Disc ISRC",
        "For a disc whose sub-channel carries ISRCs: two tracks, with and "
        "without --prefer-disc-isrc.",
        script_file="isrcdisc.txt",
        duration="about 20 minutes",
    ),
    PrebuiltTest(
        "drivemode",
        "Drive mode",
        "Do tracks 3 and 5 read the same way every time? Twelve rips.",
        script_file="drivemode.txt",
        duration="35 to 50 minutes",
    ),
    PrebuiltTest(
        "drivespeed",
        "Drive speed",
        "Does track 3 read right when Platterpus chooses the speed? 17 rips.",
        script_file="drivespeed.txt",
        duration="40 to 60 minutes",
    ),
    PrebuiltTest(
        "securereread",
        "Secure re-read",
        "The whole-disc secure re-read on its own: one disc, one rip.",
        script_file="securereread.txt",
        duration="2 to 2.5 hours",
    ),
    PrebuiltTest(
        "rigcancelandoverread",
        "Cancel and over-read",
        "The cancel path, the completed re-rip after it, and the PlainText fix.",
        script_file="rigcancelandoverread.txt",
        duration="about an hour",
    ),
    PrebuiltTest(
        "unknowndisc",
        "Unknown-disc acceptance",
        "With a disc MusicBrainz does not know: the unknown-album path.",
        script_file="unknowndiscacceptance.txt",
        duration="about 30 minutes",
    ),
    PrebuiltTest(
        "walkthrough",
        "Walkthrough pictures",
        "Shoots the getting-started guide's pictures. Not acceptance evidence.",
        script_file="walkthrough.txt",
        duration="one whole-disc rip and two minutes",
    ),
)

#: Name → pre-built test.
PREBUILT_BY_NAME: Final[dict[str, PrebuiltTest]] = {t.name: t for t in PREBUILT}

#: The two sentences the screen shows for evidence, with their marks (WCAG:
#: status is never colour alone).
EVIDENCE_YES: Final[str] = "✓ Counts as evidence toward a version or a handshake close."
EVIDENCE_NO: Final[str] = "ⓘ Not evidence: only the whole Full acceptance run is."


def evidence_sentence(size: str, test_name: str) -> str:
    """What the screen says about evidence for this test at this size."""
    if run_sizes.counts_as_evidence(size, test_name):
        return EVIDENCE_YES
    return EVIDENCE_NO


def combination_test(chosen: Sequence[str]) -> PrebuiltTest:
    """A hand-picked combination as a test: setup once, then the ticked blocks."""
    names = blocks.combination(chosen)
    return PrebuiltTest(
        "combination",
        "Combination",
        "Your choice of built-in tests, in their fixed order.",
        run_sizes.FULL,
        names,
    )
