"""The Run tests screen (TASKS R188): what it lists, says and enables.

The session it starts is `tests/test_ui_acceptance_session.py`'s subject; this
file holds the screen to the owner's design: three tabs, the box under the
choice naming blocks by TITLE (the first build showed internal names, which the
owner's screenshots caught), the evidence sentence with its mark, Run enabled
only for a test that can run, and the C2 probe pointed to in one line.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel

from platterpus.config import Config
from platterpus.ui.dialogs.run_tests_dialog import (
    C2_NOTE,
    COMMIT_HEIGHT_PX,
    INTRO,
    TAB_COMBINATION,
    TAB_FILE,
    RunTestsDialog,
)
from platterpus.uiscript import blocks, prebuilt
from platterpus.uiscript.chosen_test import ChosenTest


def _screen(
    scripts: Path, started: list[ChosenTest] | None = None, *, accept: bool = True
) -> RunTestsDialog:
    def start(choice: ChosenTest) -> bool:
        if started is not None:
            started.append(choice)
        return accept

    return RunTestsDialog(
        None, config=Config(), start=start, edit=lambda _c: None, scripts_dir=scripts
    )


def _labels(screen: RunTestsDialog) -> list[str]:
    return [label.text() for label in screen.findChildren(QLabel)]


def test_the_screen_opens_on_full_and_says_it_is_evidence(
    qapp: QApplication, tmp_path: Path
) -> None:
    screen = _screen(tmp_path)
    assert INTRO in _labels(screen)
    assert screen.current_choice().name == "full"
    text = screen.summary_text()
    assert text.startswith("Runs, in order: Full run: header and settings baseline")
    assert prebuilt.EVIDENCE_YES in text
    assert screen._run_button.isEnabled()
    assert screen._run_button.minimumHeight() >= COMMIT_HEIGHT_PX


def test_every_name_in_the_box_is_a_title_never_an_internal_name(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The defect the owner's screenshots showed: `needripper, drivesetup`."""
    screen = _screen(tmp_path)
    screen._tabs.setCurrentIndex(TAB_COMBINATION)
    for name in ("drivesetup", "wholedisc", "pregaps"):
        screen._block_checks[name].setChecked(True)
    line = screen.summary_text().splitlines()[0]
    assert line == (
        "Runs, in order: Setup: the ripper answers, Setup: the drive's read offset, "
        "Setup: the disc identified, Drive setup check, Whole-disc rip and its "
        "checks, Pregap agreement."
    )
    words = set(line.replace(",", " ").replace(".", " ").split())
    # The run-together names (needripper, drivesetup, wholedisc…), which no title
    # contains; a name that is also an English word ("disc") may be in a title.
    english = {"disc", "identity", "overwrite", "permutations", "pregaps", "defaults"}
    names = set(blocks.BY_NAME) - english
    assert not words & names, words & names
    assert prebuilt.EVIDENCE_NO in screen.summary_text()


def test_the_combination_tab_names_what_each_block_needs_and_the_c2_probe(
    qapp: QApplication, tmp_path: Path
) -> None:
    screen = _screen(tmp_path)
    assert len(screen._block_checks) == len(blocks.combinable_blocks()) >= 19
    whole = screen._block_checks["wholedisc"].text()
    assert whole == "Whole-disc rip and its checks (needs ripper, offset, disc)"
    assert C2_NOTE in _labels(screen)
    assert "docs/rig-scripts/drivetest.sh" in C2_NOTE
    screen._tabs.setCurrentIndex(TAB_COMBINATION)
    assert not screen._run_button.isEnabled(), "nothing ticked, yet Run is on"
    assert "Tick at least one test." in screen.summary_text()


def test_the_owner_s_scripts_follow_the_prebuilt_ones_marked_as_theirs(
    qapp: QApplication, tmp_path: Path
) -> None:
    (tmp_path / "mine.txt").write_text("log mine\n", encoding="utf-8")
    (tmp_path / "broken.txt").write_text("not-a-verb\n", encoding="utf-8")
    screen = _screen(tmp_path)
    items = [
        screen._prebuilt_list.item(i).text()
        for i in range(screen._prebuilt_list.count())
    ]
    assert items[: len(prebuilt.PREBUILT)] == [
        f"{t.title} — {t.duration}" for t in prebuilt.PREBUILT
    ]
    assert items[len(prebuilt.PREBUILT) :] == ["broken.txt (yours)", "mine.txt (yours)"]
    assert not any(name in " ".join(items) for name in prebuilt.LEFT_OFF_THE_LIST)
    assert screen.select_prebuilt(str(tmp_path / "mine.txt"))
    assert screen._run_button.isEnabled()
    assert "mine.txt (yours)" in screen.summary_text()
    assert screen.select_prebuilt(str(tmp_path / "broken.txt"))
    assert not screen._run_button.isEnabled()
    assert "line 1" in screen.summary_text()


def test_a_script_file_is_checked_before_run_is_enabled(
    qapp: QApplication, tmp_path: Path
) -> None:
    screen = _screen(tmp_path)
    screen._tabs.setCurrentIndex(TAB_FILE)
    assert not screen._run_button.isEnabled()
    bad = tmp_path / "binary.bin"
    bad.write_bytes(b"\xff\xfe\x00")
    screen.choose_file(bad)
    assert not screen._run_button.isEnabled()
    assert screen._file_status.text().startswith("⚠")
    good = tmp_path / "check.anyname"
    good.write_text("log ok\nrun-block repeatrip ×2 as r\n", encoding="utf-8")
    screen.choose_file(good)
    assert screen._run_button.isEnabled()
    assert screen._file_status.text().startswith("✓")
    assert prebuilt.EVIDENCE_NO in screen.summary_text()


def test_run_hands_the_choice_to_the_session_and_closes_only_if_it_started(
    qapp: QApplication, tmp_path: Path
) -> None:
    started: list[ChosenTest] = []
    refused = _screen(tmp_path, started, accept=False)
    assert refused.select_prebuilt("quickcheck")
    assert refused._on_run() is False
    assert [c.name for c in started] == ["quickcheck"]
    started.clear()
    screen = _screen(tmp_path, started)
    assert screen.select_prebuilt("drivesetup")
    assert screen._on_run() is True
    [choice] = started
    assert choice.path is None and "drive setup" in choice.text
    assert choice.blocks == ("needripper", "needdisc", "drivesetup")
