"""The getting-started walkthrough's parts, held to each other (KDD-42).

Five things describe the same guide: the shot list (``getting_started.SHOTS``), the
guide's text, the walkthrough script that shoots the pictures, the README section
generated from the text, and the viewer that shows it. Each test here checks one
pair of them, because a picture renamed in one place and not another is the
failure this whole arrangement exists to prevent. Every sweep carries a floor, so
none of them can pass by finding nothing.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QTextBrowser

from platterpus import getting_started
from platterpus.uiscript import script as script_mod

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
UI_DIR: Path = REPO_ROOT / "src" / "platterpus" / "ui"
WALKTHROUGH: Path = (
    REPO_ROOT
    / "src"
    / "platterpus"
    / "rig_scripts"
    / getting_started.WALKTHROUGH_SCRIPT
)

#: Qt's own standard-button labels, which appear in no source file of ours.
_QT_STANDARD_LABELS: frozenset[str] = frozenset({"Yes", "No", "OK", "Cancel", "Close"})


def _guide() -> str:
    return getting_started.guide_markdown()


# --- The shot list -----------------------------------------------------------------


def test_the_shot_list_has_its_floors() -> None:
    """Emptying the list must not be a way to make every test below pass."""
    assert len(getting_started.SHOTS) >= getting_started.MIN_SHOTS
    assert len(getting_started.shots_of("loop")) >= getting_started.MIN_LOOPS
    assert getting_started.shots_of("still"), "no picture the script takes"
    assert getting_started.shots_of("desktop"), "no picture taken by hand"


def test_every_shot_is_well_formed() -> None:
    stems = [s.stem for s in getting_started.SHOTS]
    assert len(stems) == len(set(stems)), "a stem is used twice"
    for shot in getting_started.SHOTS:
        # ASCII letters, digits and hyphens, numbered by step: a folder listing reads
        # in the guide's order, and the name survives a chat client and a file manager.
        assert re.fullmatch(r"\d{2}-[a-z0-9-]+", shot.stem), shot.stem
        assert int(shot.stem[:2]) == shot.step, shot.stem
        assert 1 <= shot.step <= getting_started.STEP_COUNT, shot.stem
        # Alt text says what the picture shows: a sentence, not a file name.
        assert len(shot.alt) >= 40 and shot.alt.endswith("."), shot.stem
        assert shot.stem not in shot.alt
    steps = [s.step for s in getting_started.SHOTS]
    assert steps == sorted(steps), "the shot list is out of the guide's order"


def test_a_loop_is_a_gif_and_everything_else_a_png() -> None:
    for shot in getting_started.SHOTS:
        expected = ".gif" if shot.kind == "loop" else ".png"
        assert shot.file_name == shot.stem + expected


def test_shot_lookup() -> None:
    first = getting_started.SHOTS[0]
    assert getting_started.shot(first.stem) is first
    assert getting_started.shot("no-such-shot") is None


# --- The guide's text --------------------------------------------------------------


def test_the_guide_ships_and_has_every_step_in_order() -> None:
    text = _guide()
    assert text != getting_started.FALLBACK_MARKDOWN, "the packaged guide is missing"
    assert getting_started.step_numbers(text) == list(
        range(1, getting_started.STEP_COUNT + 1)
    )


def test_a_missing_guide_says_so_instead_of_opening_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(getting_started, "GUIDE_FILE", tmp_path / "absent.md")
    text = getting_started.guide_markdown()
    assert text == getting_started.FALLBACK_MARKDOWN
    assert "missing" in text and "User Guide" in text


def test_every_picture_the_guide_shows_is_planned_described_and_present() -> None:
    """Before the shoot the text shows no picture; after it, every planned one."""
    refs = getting_started.image_references(_guide())
    planned = {
        f"{getting_started.IMAGES_SUBDIR}/{s.file_name}": s
        for s in getting_started.SHOTS
    }
    for ref in refs:
        assert ref.target in planned, f"line {ref.line}: {ref.target} is not planned"
        assert ref.alt, f"line {ref.line}: {ref.target} has no alt text"
        assert (getting_started.GUIDE_DIR / ref.target).is_file(), ref.target
    if getting_started.SHOOT_STATUS == "pending":
        assert not refs, "the guide shows pictures while the shoot is still pending"
        return
    assert {r.target for r in refs} == set(planned), "a planned picture is not shown"
    budget = getting_started.IMAGE_BUDGET_BYTES
    assert budget is not None, "a shot guide needs its size budget (KDD-42 W7)"
    total = sum(
        (getting_started.IMAGES_DIR / s.file_name).stat().st_size
        for s in getting_started.SHOTS
    )
    assert total <= budget, f"the pictures take {total} bytes; the budget is {budget}"


def test_image_references_are_read_with_their_lines() -> None:
    text = "intro\n\n![The window](images/03-set-up-drive.png)\n![](images/x.gif)\n"
    refs = getting_started.image_references(text)
    assert [(r.alt, r.target, r.line) for r in refs] == [
        ("The window", "images/03-set-up-drive.png", 3),
        ("", "images/x.gif", 4),
    ]


def _ui_labels() -> str:
    """Every string in the UI code, with Qt's mnemonic ampersands taken out."""
    texts = [p.read_text(encoding="utf-8") for p in UI_DIR.rglob("*.py")]
    assert len(texts) >= 40, f"only {len(texts)} UI files read"
    joined = "\n".join(texts)
    return joined.replace("&&", "\x00").replace("&", "").replace("\x00", "&")


def test_every_label_the_guide_names_is_one_the_app_shows() -> None:
    """The guide puts app labels in bold, so a renamed button fails here, not in a
    reader's hands. Menu paths are checked a part at a time."""
    labels = _ui_labels()
    bold = re.findall(r"\*\*(.+?)\*\*", _guide())
    assert len(bold) >= 20, f"only {len(bold)} labels found in the guide"
    missing = [
        text
        for text in bold
        for part in text.split(" → ")
        if part not in _QT_STANDARD_LABELS and f'"{part}' not in labels
    ]
    assert not missing, f"labels the app does not show: {missing}"


# --- The README section --------------------------------------------------------------


def _emitter() -> ModuleType:
    path = REPO_ROOT / "scripts" / "emit_getting_started.py"
    spec = importlib.util.spec_from_file_location("emit_getting_started", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_readme_section_is_the_guide() -> None:
    """KDD-42 W6: one source, two renderings. A stale README fails CI."""
    emitter = _emitter()
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert emitter.rendered_readme(readme) == readme, (
        "README.md's Getting started section is stale: run "
        "python3 scripts/emit_getting_started.py"
    )
    # Not vacuous: the section really carries the guide's steps.
    assert readme.count("\n### ") >= getting_started.STEP_COUNT


def test_the_emitter_refuses_a_readme_without_exactly_one_pair_of_markers() -> None:
    emitter = _emitter()
    assert emitter.rendered_readme("no markers here") is None
    twice = f"{emitter.BEGIN}\n{emitter.END}\n{emitter.BEGIN}\n{emitter.END}"
    assert emitter.rendered_readme(twice) is None
    assert emitter.rendered_readme(f"{emitter.END}\n{emitter.BEGIN}") is None


def test_the_readme_rendering_moves_headings_down_and_paths_out() -> None:
    text = (
        "# Getting started\n\nIntro.\n\n## 1. One\n\n![A](images/01-a.png)\n\n"
        "*Last updated for Platterpus v0.7.100.*\n"
    )
    out = getting_started.readme_markdown(text)
    # The README has its own footer; two would fail the one-footer rule.
    assert "Last updated for" not in out
    assert not out.startswith("# ")
    assert "### 1. One" in out and "\n## " not in out
    assert "](src/platterpus/guide/images/01-a.png)" in out


# --- The walkthrough script ------------------------------------------------------------


def _script_steps() -> list[script_mod.Step]:
    steps = script_mod.parse(WALKTHROUGH.read_text(encoding="utf-8"))
    errors = [f"{s.line_no}: {s.error}" for s in steps if s.error]
    assert not errors, f"the walkthrough script does not parse: {errors}"
    return steps


def test_the_script_shoots_exactly_the_planned_pictures() -> None:
    """Every still is a `screenshot`, every loop a `record`, under its stem, and the
    script takes nothing the shot list does not plan."""
    steps = _script_steps()
    shots = [s.args[0] for s in steps if s.verb == "screenshot"]
    loops = [s.args[0] for s in steps if s.verb == "record"]
    assert len(shots) + len(loops) >= getting_started.MIN_SHOTS - 2
    assert sorted(shots) == sorted(s.stem for s in getting_started.shots_of("still"))
    assert sorted(loops) == sorted(s.stem for s in getting_started.shots_of("loop"))


def test_every_callout_is_drawn_by_a_later_screenshot() -> None:
    """A callout with no screenshot after it marks nothing, silently."""
    pending = 0
    callouts = 0
    for step in _script_steps():
        if step.verb == "callout":
            pending += 1
            callouts += 1
        elif step.verb == "screenshot":
            pending = 0
    assert callouts >= 8, f"only {callouts} callouts"
    assert pending == 0, "the script ends with callouts no screenshot draws"


def test_the_script_names_itself_as_not_evidence() -> None:
    head = WALKTHROUGH.read_text(encoding="utf-8")[:2000]
    assert "NOT ACCEPTANCE EVIDENCE" in head


# --- KDD-42 W5: no label artwork in a capture ---------------------------------------------


#: The modules allowed to put a picture into a widget, and what each shows. A new
#: one here is a decision: if it could show a disc's cover, the walkthrough needs a
#: placeholder before its next shoot (KDD-42 W5).
_PICTURE_SHOWERS: dict[str, str] = {
    "help_dialogs.py": "the Platterpus logo in About",
    "getting_started_dialog.py": "the guide's own pictures",
}
_PICTURE_CALL: re.Pattern[str] = re.compile(r"\b(QPixmap|QImage|QMovie)\(|setPixmap\(")


def test_no_window_renders_cover_art_into_a_capture() -> None:
    """The walkthrough photographs the app, and a disc's cover art is the label's
    copyright. Today no window shows one, so captures need no placeholder. This
    fails the day a window starts showing a picture, so that decision is made
    before the next shoot rather than discovered in a published GIF."""
    files = sorted(UI_DIR.rglob("*.py"))
    assert len(files) >= 40
    showing = {
        p.name for p in files if _PICTURE_CALL.search(p.read_text(encoding="utf-8"))
    }
    assert "help_dialogs.py" in showing, "the sweep no longer finds the known logo"
    unexpected = showing - set(_PICTURE_SHOWERS)
    assert not unexpected, (
        f"{sorted(unexpected)} now put a picture in a window: if it can be a disc's "
        "cover, give the walkthrough a placeholder (KDD-42 W5) and list it here"
    )


# --- The viewer --------------------------------------------------------------------------


def _gif_frame(data: bytes) -> bytes:
    """One 1x1 frame: a 10 cs delay, then LZW data for one pixel."""
    return (
        bytes.fromhex("21F904000A000000")
        + bytes.fromhex("2C0000000001000100" + "00")
        + bytes([2])
        + bytes([len(data)])
        + data
        + b"\x00"
    )


def _write_gif(path: Path) -> None:
    """A two-frame, looping 1x1 GIF, made here: no image file is committed."""
    path.write_bytes(
        b"GIF89a"
        + bytes.fromhex("0100010080" + "0000")
        + bytes.fromhex("000000FFFFFF")
        + bytes.fromhex("21FF0B")
        + b"NETSCAPE2.0"
        + bytes.fromhex("03010000" + "00")
        + _gif_frame(bytes.fromhex("4401"))
        + _gif_frame(bytes.fromhex("4C01"))
        + b"\x3b"
    )


def _guide_with_a_loop(tmp_path: Path) -> tuple[str, Path]:
    images = tmp_path / getting_started.IMAGES_SUBDIR
    images.mkdir()
    _write_gif(images / "05-loop.gif")
    return "# Guide\n\n## 1. Step\n\n![A short loop.](images/05-loop.gif)\n", tmp_path


def test_the_viewer_shows_the_packaged_guide(qapp: QApplication) -> None:
    from platterpus.ui.getting_started_dialog import TITLE, GettingStartedDialog

    dialog = GettingStartedDialog()
    try:
        assert dialog.windowTitle() == TITLE
        assert not dialog.isModal(), "the guide is read while working"
        view = dialog.findChild(QTextBrowser)
        assert view is not None and view.accessibleName()
        assert "Set up your drive" in view.toPlainText()
        # The pending guide has no loop, so there is nothing to pause.
        assert dialog.movies() == {}
        assert not [
            b for b in dialog.findChildren(QPushButton) if "animations" in b.text()
        ]
    finally:
        dialog.deleteLater()


def test_a_loop_plays_and_the_reader_can_pause_it(
    qapp: QApplication, tmp_path: Path
) -> None:
    """WCAG 2.2.2: something that moves for more than five seconds can be stopped."""
    from platterpus.ui.getting_started_dialog import (
        PAUSE_LABEL,
        PLAY_LABEL,
        GettingStartedDialog,
    )

    text, base = _guide_with_a_loop(tmp_path)
    dialog = GettingStartedDialog(markdown=text, base_dir=base)
    try:
        movies = dialog.movies()
        assert list(movies) == ["images/05-loop.gif"]
        movie = movies["images/05-loop.gif"]
        assert movie.state() == movie.MovieState.Running
        pause = next(
            b for b in dialog.findChildren(QPushButton) if b.text() == PAUSE_LABEL
        )
        pause.click()
        assert movie.state() == movie.MovieState.Paused
        assert pause.text() == PLAY_LABEL
        # Closing pauses; reopening does not undo the reader's own pause.
        dialog.show()
        dialog.hide()
        dialog.show()
        assert movie.state() == movie.MovieState.Paused
        pause.click()
        assert movie.state() == movie.MovieState.Running
        dialog.hide()
        assert movie.state() == movie.MovieState.Paused
        dialog.show()
        assert movie.state() == movie.MovieState.Running
    finally:
        dialog.hide()
        dialog.deleteLater()


def test_a_frame_is_put_back_into_the_page(qapp: QApplication, tmp_path: Path) -> None:
    """The browser draws a GIF's first frame and stops; the movie must repaint it."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QTextDocument

    from platterpus.ui.getting_started_dialog import GettingStartedDialog

    text, base = _guide_with_a_loop(tmp_path)
    dialog = GettingStartedDialog(markdown=text, base_dir=base)
    try:
        view = dialog.findChild(QTextBrowser)
        assert view is not None
        url = QUrl("images/05-loop.gif")
        movie = dialog.movies()["images/05-loop.gif"]
        movie.jumpToNextFrame()
        resource = view.document().resource(
            QTextDocument.ResourceType.ImageResource, url
        )
        assert resource is not None and not resource.isNull()
    finally:
        dialog.deleteLater()


def test_a_missing_loop_is_logged_and_shows_its_alt_text(
    qapp: QApplication, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from platterpus.ui.getting_started_dialog import GettingStartedDialog

    text = "# G\n\n![Gone.](images/missing.gif)\n"
    with caplog.at_level("WARNING"):
        dialog = GettingStartedDialog(markdown=text, base_dir=tmp_path)
    try:
        assert dialog.movies() == {}
        assert "missing.gif" in caplog.text
    finally:
        dialog.deleteLater()
