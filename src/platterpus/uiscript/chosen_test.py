"""What a person chose on the Run tests screen, and the sentences that describe it.

TASKS R188. The screen offers three ways to choose (a pre-built test, a
combination of blocks, a script file); each becomes one :class:`ChosenTest`,
the one value the session is started from, so the three cannot drift into three
ways of starting a run. The box under the choice (*what will run, its time
estimate, and whether it counts as evidence*) is :func:`summary`, here and pure,
so a test can read the exact sentence the owner will.

**Titles, never internal names.** The first build showed "needripper,
drivesetup" in its "Runs, in order" line, and the owner's screenshots caught it.
Every name shown here goes through :func:`platterpus.uiscript.blocks.title_of`.

Pure and Qt-free; nothing here raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.uiscript import run_sizes
from platterpus.uiscript.prebuilt import (
    PrebuiltTest,
    combination_test,
    evidence_sentence,
)
from platterpus.uiscript.script_files import ScriptFileCheck

#: The name a script file's run carries in its report: never "" (which a hand
#: run in the console has) and never "full", so a file is never evidence.
FILE_TEST_PREFIX: Final[str] = "file:"

#: How a size reads on the screen.
SIZE_WORDS: Final[dict[str, str]] = {
    run_sizes.QUICK: "Quick",
    run_sizes.STANDARD: "Standard",
    run_sizes.FULL: "Full",
}


@dataclass(frozen=True)
class ChosenTest:
    """One test, ready to run: what it is, what it runs, and why it cannot."""

    #: The name the report records (``uiscript/prebuilt.py``, or ``file:<name>``).
    name: str
    title: str
    size: str
    #: The script text it runs, ``run-block`` lines unexpanded.
    text: str
    #: The file it IS, when it is one; the session then loads that file.
    path: Path | None
    blocks: tuple[str, ...] = ()
    #: What it runs, in order, by title.
    titles: tuple[str, ...] = ()
    duration: str = ""
    #: Why it cannot run; ``""`` when it can.
    problem: str = ""

    @property
    def runnable(self) -> bool:
        return not self.problem and bool(self.text.strip())


def from_prebuilt(test: PrebuiltTest) -> ChosenTest:
    """A pre-built test as a choice (a combination is one, too)."""
    text, problem = test.text()
    return ChosenTest(
        test.name,
        test.title,
        test.size,
        text,
        test.packaged_path(),
        test.block_names(),
        test.run_titles(),
        test.duration,
        problem,
    )


def from_combination(ticked: list[str]) -> ChosenTest:
    """The ticked blocks as a choice; not runnable when nothing is ticked."""
    choice = from_prebuilt(combination_test(ticked))
    if not ticked:
        return ChosenTest(
            choice.name,
            choice.title,
            choice.size,
            "",
            None,
            problem="Tick at least one test.",
        )
    return choice


def from_file(check: ScriptFileCheck, *, yours: bool = False) -> ChosenTest:
    """A checked script file as a choice; its problems are why it cannot run."""
    label = f"{check.path.name} (yours)" if yours else check.path.name
    return ChosenTest(
        FILE_TEST_PREFIX + check.path.name,
        label,
        run_sizes.FULL,
        check.text,
        check.path,
        titles=(f"the script {label}, {check.steps} step(s)",),
        problem="\n".join(check.problems),
    )


def summary(choice: ChosenTest, estimate: str = "") -> str:
    """The box under the choice: what runs, how long, and whether it is evidence."""
    if choice.problem:
        return f"⚠ {choice.title} cannot run:\n{choice.problem}"
    lines = [f"Runs, in order: {', '.join(choice.titles)}."]
    size = SIZE_WORDS.get(choice.size, choice.size)
    time = f"Size: {size}."
    if choice.duration:
        time += f" Takes {choice.duration}."
    lines.append(time)
    if estimate:
        lines.append(estimate)
    lines.append(evidence_sentence(choice.size, choice.name))
    return "\n".join(lines)
