"""The walkthrough's verbs, ``callout`` and ``record`` (``PLANNING.md`` KDD-42, W3).

The getting-started guide is shot by a script: ``callout`` marks the button a
step presses on the next ``screenshot``, and ``record`` takes the frame bursts the
guide's GIFs are made from. The drawing is tested on rendered images; the verbs
are driven through the real runner against a real, shown window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_uiscript_rip_verbs import _window

from platterpus.uiscript.callout import (
    BADGE_DIAMETER_PX,
    CALLOUT_COLOUR,
    CalloutMark,
    draw_callouts,
    label_matches,
    normalise_label,
)
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse

# --- labels: matched as the user reads them -------------------------------------


def test_a_label_is_read_as_the_user_sees_it() -> None:
    assert normalise_label("&Rip") == "Rip"
    assert normalise_label("Save && quit") == "Save & quit"
    assert normalise_label("  Set up\n drive…  ") == "Set up drive…"


def test_a_callout_matches_exactly_or_by_a_stated_prefix() -> None:
    assert label_matches("&Rip", "Rip")
    assert not label_matches("Rip again", "Rip")
    assert label_matches("✓ Bit-perfect: all 14 tracks", "✓ Bit-perfect*")
    # A bare `*` names nothing, so it cannot mark every widget at once.
    assert not label_matches("anything", "*")
    assert not label_matches("", "")


# --- drawing: on the picture, readable, on the widget ---------------------------


def _white(width: int, height: int) -> Any:
    from PySide6.QtGui import QColor, QImage

    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#FFFFFF"))
    return image


def _is_amber(image: Any, x: int, y: int) -> bool:
    from PySide6.QtGui import QColor

    pixel = QColor(image.pixel(x, y))
    want = QColor(CALLOUT_COLOUR)
    return all(
        abs(a - b) <= 40
        for a, b in (
            (pixel.red(), want.red()),
            (pixel.green(), want.green()),
            (pixel.blue(), want.blue()),
        )
    )


def test_a_mark_outlines_the_widget_and_leaves_it_readable(qapp: Any) -> None:
    image = _white(300, 160)
    out = draw_callouts(image, [CalloutMark(1, 100, 60, 80, 30)])
    # The outline sits PADDING_PX outside the widget: on the bottom edge, mid-way.
    assert _is_amber(out, 140, 60 + 30 + 4)
    # The widget itself is not painted over: its centre is still white.
    from PySide6.QtGui import QColor

    assert QColor(out.pixel(140, 75)) == QColor("#FFFFFF")
    # The badge sits on the outline's top-left corner.
    assert _is_amber(out, 96 + 6, 56 + 6) or _is_amber(out, 96 - 6, 56 - 6)
    # The input picture is not changed.
    assert QColor(image.pixel(140, 94)) == QColor("#FFFFFF")


def test_a_mark_lands_on_its_widget_on_a_2x_screen(qapp: Any) -> None:
    out = draw_callouts(_white(600, 320), [CalloutMark(1, 100, 60, 80, 30)], 2.0)
    assert _is_amber(out, 280, (60 + 30 + 4) * 2)
    from PySide6.QtGui import QColor

    assert QColor(out.pixel(280, 150)) == QColor("#FFFFFF")


def test_a_badge_at_the_window_edge_stays_on_the_picture(qapp: Any) -> None:
    out = draw_callouts(_white(200, 100), [CalloutMark(7, 0, 0, 40, 20)])
    half = int(BADGE_DIAMETER_PX / 2)
    # Clamped inside: the badge's centre is a full radius in from both edges.
    # Sampled left of centre, in the amber fill, clear of the white digit.
    assert _is_amber(out, half + 1 - 7, half + 1)
    # And the badge did not run off the picture: its far edge is inside it.
    assert half * 2 + 2 <= out.width()


def test_no_marks_change_no_pixels(qapp: Any) -> None:
    image = _white(50, 40)
    assert draw_callouts(image, []) == image.convertToFormat(image.format())


# --- the verbs, through the runner ----------------------------------------------


def _shown_window(qapp: Any, process_until: Any, labels: list[str]) -> Any:
    from PySide6.QtWidgets import QPushButton, QVBoxLayout

    main = _window()
    main.setWindowTitle("walkthrough")
    layout = QVBoxLayout(main)
    for label in labels:
        layout.addWidget(QPushButton(label, main))
    main.resize(320, 60 + 40 * len(labels))
    main.show()
    assert process_until(lambda: main.windowHandle() is not None)
    assert process_until(lambda: main.windowHandle().isExposed())
    return main


def _run(runner: Any, process_until: Any, source: str) -> list[Any]:
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    runner.start(parse(source), source=source)
    assert process_until(lambda: bool(emitted), timeout=30.0), "the run never finished"
    return list(emitted[0].steps)


def _close(*widgets: Any) -> None:
    for widget in widgets:
        widget.close()
        widget.deleteLater()


def test_a_callout_is_drawn_on_the_next_screenshot_and_only_that_one(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    from PySide6.QtGui import QImage

    main = _shown_window(qapp, process_until, ["&Rip", "Cancel"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        callout, first, second = _run(
            runner, process_until, "callout 1 Rip\nscreenshot marked\nscreenshot plain"
        )
        assert callout.outcome is Outcome.PASS, callout.detail
        assert "QPushButton 'Rip'" in callout.detail
        assert first.outcome is Outcome.PASS, first.detail
        assert "callout 1 ('Rip') drawn" in first.detail
        assert "callout" not in second.detail  # cleared: drawn on one picture only
        rip = next(
            b for b in main.findChildren(type(main.children()[1])) if "Rip" in b.text()
        )
        corner = rip.mapTo(main, rip.rect().bottomLeft())
        marked = QImage(str(next(tmp_path.rglob("marked.png"))))
        plain = QImage(str(next(tmp_path.rglob("plain.png"))))
        ratio = marked.width() / main.width()
        x = int((corner.x() + rip.width() // 2) * ratio)
        y = int((corner.y() + 4) * ratio)
        assert _is_amber(marked, x, y), "the outline is under the Rip button"
        assert not _is_amber(plain, x, y), "the next picture carries no mark"
    finally:
        _close(main)


def test_a_callout_on_a_label_nobody_shows_fails_and_names_what_is_there(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    main = _shown_window(qapp, process_until, ["&Rip", "Cancel"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, "callout 1 Start")
        assert step.outcome is Outcome.FAIL
        assert "no visible widget reads 'Start'" in step.detail
        assert "'Rip'" in step.detail and "'Cancel'" in step.detail
    finally:
        _close(main)


def test_a_callout_that_matches_two_widgets_fails(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    main = _shown_window(qapp, process_until, ["OK", "OK"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, "callout 1 OK")
        assert step.outcome is Outcome.FAIL
        assert "2 visible widgets read 'OK'" in step.detail
    finally:
        _close(main)


@pytest.mark.parametrize(
    ("line", "said"),
    [
        ("callout 0 Rip", "run 1 to 99"),
        ("callout 100 Rip", "run 1 to 99"),
        ("callout one Rip", "is not a number"),
    ],
)
def test_a_callout_number_out_of_range_is_an_error(
    qapp: Any, process_until: Any, tmp_path: Path, line: str, said: str
) -> None:
    main = _shown_window(qapp, process_until, ["&Rip"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, line)
        assert step.outcome is Outcome.ERROR
        assert said in step.detail
    finally:
        _close(main)


def test_a_callout_whose_window_is_gone_fails_the_screenshot(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    """A picture missing the mark its step was given does not show what the
    walkthrough says it shows, so the screenshot fails and names the mark."""
    from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout

    main = _shown_window(qapp, process_until, ["Cancel"])
    dialog = QDialog()
    dialog.setWindowTitle("a dialog")
    QVBoxLayout(dialog).addWidget(QPushButton("Choose", dialog))
    dialog.show()
    assert process_until(lambda: dialog.windowHandle() is not None)
    assert process_until(lambda: dialog.windowHandle().isExposed())
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        callout_steps = _run(runner, process_until, "callout 2 Choose")
        assert callout_steps[0].outcome is Outcome.PASS, callout_steps[0].detail
        dialog.hide()
        runner2_steps = _run(runner, process_until, "screenshot after")
        assert runner2_steps[-1].outcome is Outcome.FAIL, runner2_steps[-1].detail
        assert "callout 2 ('Choose') NOT DRAWN" in runner2_steps[-1].detail
    finally:
        _close(main, dialog)


def test_a_screenshot_without_callouts_is_unchanged(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    main = _shown_window(qapp, process_until, ["&Rip"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, "screenshot plain")
        assert step.outcome is Outcome.PASS, step.detail
        assert "callout" not in step.detail
    finally:
        _close(main)


def test_a_burst_writes_every_frame_and_a_manifest(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    main = _shown_window(qapp, process_until, ["&Rip"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, "record burst 1 5")
        assert step.outcome is Outcome.PASS, step.detail
        assert "5 of 5 frame(s) taken, 0 lost" in step.detail
        frames = sorted(p.name for p in tmp_path.rglob("burst-0*.png"))
        assert frames == [f"burst-{i:04d}.png" for i in range(1, 6)]
        manifest = next(tmp_path.rglob("burst-frames.txt")).read_text("utf-8")
        assert "5 of 5" in manifest
    finally:
        _close(main)


def test_a_lost_frame_is_counted_and_fails_the_burst(
    qapp: Any, process_until: Any, tmp_path: Path
) -> None:
    """A dropped frame is counted, never skipped silently."""
    main = _shown_window(qapp, process_until, ["&Rip"])
    real_grab = main.grab
    calls = {"n": 0}

    class _Unwritable:
        def __init__(self, pixmap: Any) -> None:
            self._pixmap = pixmap

        def width(self) -> int:
            return int(self._pixmap.width())

        def height(self) -> int:
            return int(self._pixmap.height())

        def save(self, *_args: Any) -> bool:
            return False

    def flaky_grab(*args: Any) -> Any:
        calls["n"] += 1
        pixmap = real_grab(*args)
        return _Unwritable(pixmap) if calls["n"] == 2 else pixmap

    main.grab = flaky_grab  # type: ignore[method-assign]  # one frame lost on purpose
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, "record lossy 1 4")
        assert step.outcome is Outcome.FAIL, step.detail
        assert "3 of 4 frame(s) taken, 1 lost" in step.detail
        assert "frame 2: not written" in step.detail
    finally:
        _close(main)


@pytest.mark.parametrize(
    "line", ["record x 30 5", "record x 0.1 5", "record x 1 20", "record x a b"]
)
def test_a_burst_out_of_bounds_is_an_error(
    qapp: Any, process_until: Any, tmp_path: Path, line: str
) -> None:
    main = _shown_window(qapp, process_until, ["&Rip"])
    try:
        runner = ScriptRunner(main)
        runner.contain_in(tmp_path)
        (step,) = _run(runner, process_until, line)
        assert step.outcome is Outcome.ERROR, step.detail
        assert not list(tmp_path.rglob("x-0*.png"))
    finally:
        _close(main)
