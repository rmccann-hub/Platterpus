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

from platterpus.uiscript import blocks, prebuilt, run_sizes, script_files
from platterpus.uiscript.find_script import packaged_scripts_dir
from platterpus.uiscript.run_block import expand_run_blocks
from platterpus.uiscript.script import parse

_REPO: Final[Path] = Path(__file__).resolve().parents[1]

#: SHA-256 of each file at origin/main 93a45b62, the day it was cut (2026-11-23),
#: and its step count there. Re-pinned 2026-11-25 for the full run's new section
#: S, the installation and the app's own health (the owner's word that day; 675
#: steps to 682, the seven of `installation.txt`).
PINNED: Final[dict[str, tuple[str, int]]] = {
    "fullacceptance.txt": (
        "44e56cea55270d36f8f6067ebef7f7c930fc109e6ad69fb31a6fcbe57d18c0ee",
        682,
    ),
    "quickcheck.txt": (
        "8869d1b3a6003948d995b832e50e3159b24d2db33c52690eb45e94b72069c65b",
        78,
    ),
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_the_full_run_has_its_twenty_blocks_in_order() -> None:
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
        "installation",
        "defaults",
    )
    assert len(blocks.QUICK_ORDER) == 8
    # The floor under the hash sweep below: both generated files are pinned.
    assert (
        set(PINNED)
        == set(blocks.GENERATED_FILES)
        == {
            "fullacceptance.txt",
            "quickcheck.txt",
        }
    )


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


# --- The pre-built tests ------------------------------------------------------


def test_the_prebuilt_list_has_its_tests_in_order() -> None:
    names = [test.name for test in prebuilt.PREBUILT]
    assert names[:6] == [
        "full",
        "standard",
        "quick",
        "quickcheck",
        "repeatrips",
        "drivesetup",
    ]
    assert len(names) == len(set(names)) >= 14


@pytest.mark.parametrize(
    ("name", "file", "steps"),
    [("full", "fullacceptance.txt", 682), ("quickcheck", "quickcheck.txt", 78)],
)
def test_full_and_quick_expand_to_their_files_byte_for_byte(
    name: str, file: str, steps: int
) -> None:
    """The owner's proof, through the pre-built definitions themselves."""
    test = prebuilt.PREBUILT_BY_NAME[name]
    text, problem = test.text()
    assert not problem, problem
    assert _sha(text) == PINNED[file][0]
    expanded = expand_run_blocks(parse(text)).steps
    assert len(expanded) == steps
    assert test.packaged_path() == packaged_scripts_dir() / file


def test_the_three_acceptance_sizes_are_one_list_of_blocks() -> None:
    sizes = {}
    for name in ("full", "standard", "quick"):
        test = prebuilt.PREBUILT_BY_NAME[name]
        assert test.blocks == blocks.FULL_ORDER
        sizes[name] = test.size
    assert sizes == {
        "full": run_sizes.FULL,
        "standard": run_sizes.STANDARD,
        "quick": run_sizes.QUICK,
    }


def test_full_s_five_repeat_rips_stay_one_fixed_block() -> None:
    """The owner, 2026-11-23: not a counted entry, so Full's steps do not change."""
    full = prebuilt.PREBUILT_BY_NAME["full"]
    assert "repeatrips" in full.blocks and not full.repeats


def test_repeat_rips_five_runs_the_block_five_times_and_compares_them() -> None:
    test = prebuilt.PREBUILT_BY_NAME["repeatrips"]
    text, problem = test.text()
    assert not problem, problem
    expansion = expand_run_blocks(parse(text))
    assert expansion.runs == {"repeat": 5}
    checks = [s.joined() for s in expansion.steps if s.verb == "expect-repeats"]
    assert checks == ["repeat verified", "repeat same-crc"]
    assert test.run_titles()[-1] == "One repeat rip ×5"


@pytest.mark.parametrize("test", prebuilt.PREBUILT, ids=lambda t: t.name)
def test_every_prebuilt_test_reads_and_every_line_is_valid(
    test: prebuilt.PrebuiltTest,
) -> None:
    text, problem = test.text()
    assert not problem, problem
    steps = expand_run_blocks(parse(text)).steps
    assert steps
    assert [s.error for s in steps if not s.ok] == []
    for title in test.run_titles():
        assert title not in blocks.BY_NAME, f"{test.name} shows the name {title!r}"


def test_every_packaged_script_is_offered_generated_or_left_off_with_a_reason() -> None:
    offered = {t.script_file for t in prebuilt.PREBUILT if t.script_file}
    generated = set(blocks.GENERATED_FILES)
    left = set(prebuilt.LEFT_OFF_THE_LIST)
    assert left == {"round08joint.txt", "police-rerip.txt", "track3abba.txt"}
    on_disk = {p.name for p in packaged_scripts_dir().glob("*.txt")}
    assert len(on_disk) >= 10
    assert on_disk == offered | generated | left, sorted(
        on_disk ^ (offered | generated | left)
    )
    assert not (offered & left) and not (offered & generated)
    assert "overreadprobe.txt" in offered, "R188 began with the over-read probe"


def test_only_the_full_test_at_full_size_is_evidence() -> None:
    """Evidence status is unchanged: the Full run, or an unnamed hand run."""
    for test in prebuilt.PREBUILT:
        expected = test.name == "full"
        assert prebuilt.evidence_sentence(test.size, test.name) == (
            prebuilt.EVIDENCE_YES if expected else prebuilt.EVIDENCE_NO
        ), test.name
    assert run_sizes.counts_as_evidence(run_sizes.FULL)  # a hand run, as before
    assert not run_sizes.counts_as_evidence(run_sizes.FULL, "combination")
    assert prebuilt.EVIDENCE_YES.startswith("✓")
    assert prebuilt.EVIDENCE_NO.startswith("ⓘ")


def test_a_combination_names_its_setup_and_its_blocks_by_title() -> None:
    test = prebuilt.combination_test(["wholedisc", "pregaps"])
    assert test.run_titles() == (
        "Setup: the ripper answers",
        "Setup: the drive's read offset",
        "Setup: the disc identified",
        "Whole-disc rip and its checks",
        "Pregap agreement",
    )
    assert not run_sizes.counts_as_evidence(test.size, test.name)


# --- The owner's scripts, checked by content ------------------------------------


def test_a_valid_file_passes_whatever_its_extension(tmp_path: Path) -> None:
    path = tmp_path / "mine.script"
    path.write_text("log hello\nrun-block repeatrip ×2 as r\n", encoding="utf-8")
    check = script_files.check_script_file(path)
    assert check.ok, check.problems
    assert check.steps > 2


@pytest.mark.parametrize(
    ("content", "said"),
    [
        (b"\xff\xfe not utf-8", "not plain UTF-8"),
        (b"log ok\nnot-a-verb here\n", "line 2"),
        (b"# only a comment\n", "no steps"),
        (b"log a\x00b\n", "NUL"),
        (b"run-block nosuch x2 as r\n", "line 1"),
    ],
)
def test_a_file_that_may_not_run_says_why(
    tmp_path: Path, content: bytes, said: str
) -> None:
    path = tmp_path / "bad"
    path.write_bytes(content)
    check = script_files.check_script_file(path)
    assert not check.ok
    assert said in " ".join(check.problems), check.problems


def test_a_file_over_the_cap_is_refused_before_it_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(script_files, "MAX_SCRIPT_BYTES", 10)
    path = tmp_path / "big.txt"
    path.write_text("log this is longer than ten bytes\n", encoding="utf-8")
    check = script_files.check_script_file(path)
    assert not check.ok and "at most" in check.problems[0]
    missing = script_files.check_script_file(tmp_path / "absent.txt")
    assert not missing.ok


def test_the_scripts_folder_lists_files_by_name_and_skips_the_rest(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.txt").write_text("log b\n", encoding="utf-8")
    (tmp_path / "A run").write_text("log a\n", encoding="utf-8")
    (tmp_path / ".swap").write_text("x", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    assert [p.name for p in script_files.user_scripts(tmp_path)] == ["A run", "b.txt"]
    assert script_files.user_scripts(tmp_path / "absent") == ()
