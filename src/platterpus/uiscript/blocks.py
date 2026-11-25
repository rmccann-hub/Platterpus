"""The catalogue of test blocks: each one's name, title, and what it needs.

**Why blocks exist** (TASKS R188, the owner's design of 2026-11-17). The Full
acceptance run and the Quick check used to be two long files, and every other
test that wanted "a whole-disc rip" or "identify the disc" copied lines out of
them. The owner's rule: *each test exists once*. So both files are cut, at their
section headers, into blocks under ``rig_scripts/blocks/``, and every pre-built
test (``uiscript/prebuilt.py``) is an ordered list of block names. The two big
files are now **generated** from their blocks by ``scripts/emit_rig_scripts.py``
and are byte-identical to what they were, which ``tests/test_prebuilt_tests.py``
proves against hashes of the files as they stood at ``origin/main``.

**What a block declares.** Its name (the file stem, and what ``run-block``
takes), its title (what a person reads on the Run tests screen: never the
internal name, which the owner's review of the first build caught), and what it
needs set up first. A need is one of three SETUP blocks, ``needripper``,
``needoffset`` and ``needdisc``, which a combination gets once each, before the
first block that needs it, and names in its list.

**Where the files live.** Inside the package, next to the scripts they were cut
from, so an AppImage has them (``pyproject.toml``'s package-data line for
``rig_scripts/blocks/*.txt``). Reading one is a small local file read; nothing
here blocks for long, and nothing touches Qt.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.uiscript.find_script import packaged_scripts_dir

#: The folder name under ``rig_scripts/``.
BLOCKS_DIR_NAME: Final[str] = "blocks"

#: The three setup blocks, in the order a combination runs them.
NEED_RIPPER: Final[str] = "needripper"
NEED_OFFSET: Final[str] = "needoffset"
NEED_DISC: Final[str] = "needdisc"
SETUP_ORDER: Final[tuple[str, ...]] = (NEED_RIPPER, NEED_OFFSET, NEED_DISC)

#: What each need reads as after "needs": one word each, so the longest tick-box
#: still fits a Steam Deck at 150% text; the Combination tab explains the words.
NEED_WORDS: Final[dict[str, str]] = {
    NEED_RIPPER: "ripper",
    NEED_OFFSET: "offset",
    NEED_DISC: "disc",
}

#: Kinds of block. Only COMBINABLE ones are offered on the Combination tab.
KIND_FULL: Final[str] = "full"
KIND_QUICK: Final[str] = "quick"
KIND_SETUP: Final[str] = "setup"
KIND_DRIVE: Final[str] = "drive"
KIND_REPEAT: Final[str] = "repeat"

#: The placeholder a repeatable block carries, replaced with each run's label.
LABEL_PLACEHOLDER: Final[str] = "(label)"


@dataclass(frozen=True)
class Block:
    """One test block: a file under ``rig_scripts/blocks/``, and what it needs."""

    name: str
    title: str
    kind: str
    #: Setup blocks this one needs, from :data:`SETUP_ORDER`.
    needs: tuple[str, ...] = ()
    #: Offered on the Combination tab.
    combinable: bool = False

    def needs_text(self) -> str:
        """``"(needs the ripper, a disc identified)"``, or ``""`` for none."""
        if not self.needs:
            return ""
        return "(needs " + ", ".join(NEED_WORDS[n] for n in self.needs) + ")"


_ALL: Final[tuple[str, ...]] = SETUP_ORDER
_RO: Final[tuple[str, ...]] = (NEED_RIPPER, NEED_OFFSET)
_RD: Final[tuple[str, ...]] = (NEED_RIPPER, NEED_DISC)
_OFFSET: Final[tuple[str, ...]] = (NEED_OFFSET,)

#: Every block, in the fixed order a combination runs them: setup, the drive
#: check, then the Full run's sections in the Full run's own order.
BLOCKS: Final[tuple[Block, ...]] = (
    Block(NEED_RIPPER, "Setup: the ripper answers", KIND_SETUP),
    Block(NEED_OFFSET, "Setup: the drive's read offset", KIND_SETUP),
    Block(NEED_DISC, "Setup: the disc identified", KIND_SETUP),
    Block("drivesetup", "Drive setup check", KIND_DRIVE, _RD, combinable=True),
    # --- The Full acceptance run, cut at its section headers --------------
    Block("fullstart", "Full run: header and settings baseline", KIND_FULL),
    Block("identity", "Identity: which ripper build", KIND_FULL, combinable=True),
    Block("settingsdialogs", "Settings and dialogs", KIND_FULL, combinable=True),
    Block("disc", "Disc identification", KIND_FULL, _OFFSET, combinable=True),
    Block("wholedisc", "Whole-disc rip and its checks", KIND_FULL, _ALL, True),
    Block("overwrite", "Overwrite prompt", KIND_FULL, _ALL, combinable=True),
    Block("cancelrecovery", "Cancel and recovery", KIND_FULL, _ALL, True),
    Block("permutations", "Setting permutations", KIND_FULL, _ALL, True),
    Block("outputformats", "Output formats", KIND_FULL, _ALL, combinable=True),
    Block("presetsnaming", "Goal presets and naming", KIND_FULL, combinable=True),
    Block("secureread", "Secure re-read", KIND_FULL, _ALL, combinable=True),
    Block("offsetfinder", "Offset finder (cyanrip -f)", KIND_FULL, _ALL, True),
    Block("cacheprobe", "Cache probe", KIND_FULL, _RD, combinable=True),
    Block("nooffsetrefusal", "No-offset refusal", KIND_FULL, _RD, combinable=True),
    Block("deemphasis", "De-emphasis pair", KIND_FULL, _RO, combinable=True),
    Block("buildcomparison", "Build comparison", KIND_FULL, _ALL, True),
    Block("repeatrips", "Five repeat rips", KIND_FULL, _ALL, combinable=True),
    Block("pregaps", "Pregap agreement", KIND_FULL, combinable=True),
    Block(
        "installation",
        "The installation and the app's health",
        KIND_FULL,
        combinable=True,
    ),
    Block("defaults", "Leave on defaults", KIND_FULL, _OFFSET, combinable=True),
    # --- The Quick check, cut the same way ---------------------------------
    Block("quickstart", "Quick check: header", KIND_QUICK),
    Block("quickidentity", "Quick check: the ripper", KIND_QUICK),
    Block("quickoffset", "Quick check: the read offset", KIND_QUICK),
    Block("quicksettings", "Quick check: the settings", KIND_QUICK),
    Block("quickdisc", "Quick check: the disc", KIND_QUICK),
    Block("quickrip", "Quick check: one track", KIND_QUICK),
    Block("quicknotcovered", "Quick check: what it does not cover", KIND_QUICK),
    Block("quickdefaults", "Quick check: back to defaults", KIND_QUICK),
    # --- For `run-block repeatrip ×N as <label>` ---------------------------
    Block("repeatrip", "One repeat rip", KIND_REPEAT, _ALL),
)

#: Name → block.
BY_NAME: Final[dict[str, Block]] = {block.name: block for block in BLOCKS}

#: The Full acceptance run, in order: joined, these ARE ``fullacceptance.txt``.
FULL_ORDER: Final[tuple[str, ...]] = tuple(
    block.name for block in BLOCKS if block.kind == KIND_FULL
)

#: The Quick check, in order: joined, these ARE ``quickcheck.txt``.
QUICK_ORDER: Final[tuple[str, ...]] = tuple(
    block.name for block in BLOCKS if block.kind == KIND_QUICK
)

#: The generated files and the blocks each is joined from.
GENERATED_FILES: Final[dict[str, tuple[str, ...]]] = {
    "fullacceptance.txt": FULL_ORDER,
    "quickcheck.txt": QUICK_ORDER,
}


def blocks_dir() -> Path:
    """Where the block files live. Pure: answers even if the folder is missing."""
    return packaged_scripts_dir() / BLOCKS_DIR_NAME


def block_path(name: str) -> Path:
    """The file of block ``name`` (which need not exist)."""
    return blocks_dir() / f"{name}.txt"


def block_text(name: str) -> tuple[str | None, str]:
    """``(text, problem)``: the block's text, or ``None`` and why not. Never raises."""
    if name not in BY_NAME:
        return None, f"no block called {name!r}"
    path = block_path(name)
    try:
        return path.read_text(encoding="utf-8"), ""
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"block {name!r} could not be read from {path}: {exc}"


def title_of(name: str) -> str:
    """A block's title for a person; the name itself only if it is unknown."""
    block = BY_NAME.get(name)
    return block.title if block is not None else name


def combinable_blocks() -> tuple[Block, ...]:
    """The blocks a person can tick on the Combination tab, in run order."""
    return tuple(block for block in BLOCKS if block.combinable)


def combination(chosen: Iterable[str]) -> tuple[str, ...]:
    """The blocks a combination runs: setup once each, then ``chosen`` in order.

    The order is the catalogue's, never the order the boxes were ticked: a
    block's place in the Full run is where its preconditions hold (the pregap
    check after every rip). Unknown and non-combinable names are dropped; the
    caller only ever passes ticked boxes, which are combinable by construction.
    """
    wanted = {name for name in chosen if name in BY_NAME and BY_NAME[name].combinable}
    needs = {need for name in wanted for need in BY_NAME[name].needs}
    return tuple(
        block.name
        for block in BLOCKS
        if block.name in wanted or (block.kind == KIND_SETUP and block.name in needs)
    )


def joined_text(names: Iterable[str]) -> tuple[str, str]:
    """``(text, problem)``: the named blocks' texts joined, in order.

    A block meant to be repeated has its :data:`LABEL_PLACEHOLDER` replaced with
    its own name, so it runs once under that label. ``problem`` is the first
    block that could not be read; the text is then ``""``.
    """
    parts: list[str] = []
    for name in names:
        text, problem = block_text(name)
        if text is None:
            return "", problem
        if BY_NAME[name].kind == KIND_REPEAT:
            text = text.replace(LABEL_PLACEHOLDER, name)
        parts.append(text)
    return "".join(parts), ""
