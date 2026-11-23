"""TASKS R188: the blocks rebuild Full and Quick exactly, and each test exists once.

**The proof the owner asked for before anything changes**: *"before anything
changes, a test proves the new Full and Quick lists expand to exactly today's
`fullacceptance.txt` and `quickcheck.txt` steps."* So the two files are pinned
here by their SHA-256 as they stood at ``origin/main`` when they were cut
(``93a45b62``), and the blocks, joined in the catalogue's order, must give those
bytes and those step counts (675 and 78). A later edit to a block changes the
hash and fails here first: that is the point, and the fix is to re-pin in the
same change with the reason.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Final

import pytest

from platterpus.uiscript import blocks
from platterpus.uiscript.find_script import packaged_scripts_dir
from platterpus.uiscript.script import parse

_REPO: Final[Path] = Path(__file__).resolve().parents[1]

#: SHA-256 of each file at origin/main 93a45b62, the day it was cut (2026-11-23),
#: and its step count there.
PINNED: Final[dict[str, tuple[str, int]]] = {
    "fullacceptance.txt": (
        "dc1196a79431928fabc97b0590c1c1caaf1acf5b177659bee7e51336fe5f4139",
        675,
    ),
    "quickcheck.txt": (
        "8869d1b3a6003948d995b832e50e3159b24d2db33c52690eb45e94b72069c65b",
        78,
    ),
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_the_full_run_has_its_nineteen_blocks_in_order() -> None:
    assert blocks.FULL_ORDER == (
        "fullstart",
        "identity",
        "settingsdialogs",
        "disc",
        "wholedisc",
        "overwrite",
        "cancelrecovery",
        "permutations",
        "outputformats",
        "presetsnaming",
        "secureread",
        "offsetfinder",
        "cacheprobe",
        "nooffsetrefusal",
        "deemphasis",
        "buildcomparison",
        "repeatrips",
        "pregaps",
        "defaults",
    )
    assert len(blocks.QUICK_ORDER) == 8
    # The floor under the hash sweep below: both generated files are pinned.
    assert set(PINNED) == set(blocks.GENERATED_FILES) == {
        "fullacceptance.txt",
        "quickcheck.txt",
    }


@pytest.mark.parametrize("name", sorted(PINNED))
def test_the_blocks_join_to_the_file_as_it_was_byte_for_byte(name: str) -> None:
    sha, count = PINNED[name]
    joined, problem = blocks.joined_text(blocks.GENERATED_FILES[name])
    assert not problem, problem
    assert _sha(joined) == sha, f"{name}: the blocks no longer join to the pinned file"
    assert len(parse(joined)) == count
    on_disk = (packaged_scripts_dir() / name).read_text(encoding="utf-8")
    assert on_disk == joined, (
        f"{name} is stale: run python3 scripts/emit_rig_scripts.py"
    )


def test_every_block_in_the_catalogue_has_a_file_and_every_file_a_block() -> None:
    files = {path.stem for path in blocks.blocks_dir().glob("*.txt")}
    assert len(files) >= 32, f"only {len(files)} block files: the glob found too little"
    assert files == set(blocks.BY_NAME), sorted(files ^ set(blocks.BY_NAME))


@pytest.mark.parametrize("block", blocks.BLOCKS, ids=lambda b: b.name)
def test_every_block_parses_with_no_bad_line(block: blocks.Block) -> None:
    text, problem = blocks.block_text(block.name)
    assert text is not None, problem
    if block.kind == blocks.KIND_REPEAT:
        assert blocks.LABEL_PLACEHOLDER in text
        text = text.replace(blocks.LABEL_PLACEHOLDER, "repeat1")
    steps = parse(text)
    assert steps, f"{block.name} has no steps"
    assert [s.error for s in steps if not s.ok] == []


def test_a_title_is_never_the_internal_name() -> None:
    """The owner's screenshots showed `needripper, drivesetup`: a defect."""
    for block in blocks.BLOCKS:
        assert block.title != block.name
        assert " " in block.title, f"{block.name}: {block.title!r} reads as a name"


def test_a_combination_gets_each_setup_once_in_the_fixed_order() -> None:
    chosen = blocks.combination(["pregaps", "wholedisc", "drivesetup", "secureread"])
    assert chosen == (
        "needripper",
        "needoffset",
        "needdisc",
        "drivesetup",
        "wholedisc",
        "secureread",
        "pregaps",
    )
    assert blocks.combination(["presetsnaming"]) == ("presetsnaming",)
    # Not combinable: the Full run's header, a setup block on its own, a quick block.
    assert blocks.combination(["fullstart", "needdisc", "quickrip"]) == ()


def test_the_generator_check_passes_and_catches_a_hand_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = importlib.util.spec_from_file_location(
        "emit_rig_scripts", _REPO / "scripts" / "emit_rig_scripts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["emit_rig_scripts"] = module
    spec.loader.exec_module(module)
    assert module.main(["--check"]) == 0
    # A hand-edited copy is stale: point the generator at a copy and edit it.
    copy = tmp_path / "rig_scripts"
    copy.mkdir()
    for name in blocks.GENERATED_FILES:
        (copy / name).write_text(
            (packaged_scripts_dir() / name).read_text(encoding="utf-8") + "# hand\n",
            encoding="utf-8",
        )
    # Only the generator's OUTPUT folder moves; the blocks are still read from
    # the package, which `blocks.blocks_dir` resolves on its own.
    monkeypatch.setattr(module, "packaged_scripts_dir", lambda: copy)
    assert module.main(["--check"]) == 1
    assert module.main([]) == 0
    assert module.main(["--check"]) == 0
