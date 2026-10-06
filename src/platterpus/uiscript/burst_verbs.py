"""The walkthrough's ``record`` verb: a short burst of frames (``PLANNING.md`` KDD-42, W3).

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the
other ``*_verbs`` modules. ``record <name> <seconds> <fps>`` takes a burst of
main-window frames, ``<name>-0001.png`` onward, with a manifest; the burst
becomes one of the getting-started guide's GIFs (assembled with ffmpeg, KDD-42
W4). The marks on the guide's stills are the other verb, ``callout``
(:mod:`platterpus.uiscript.walkthrough_verbs`).

**Nothing here blocks the GUI thread.** A frame is one ``QWidget.grab()``, a few
milliseconds, taken on a ``QTimer`` tick, and the wait is the runner's deadline
machinery, so the window keeps painting what the burst is recording.

**A dropped frame is counted, never skipped silently**: the manifest says how
many frames were asked for, taken and lost, and a burst that lost any FAILs.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QTimer

from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: Bounds on a burst, so one script line cannot fill a disk: at most 20 s, at
#: most 15 frames a second, and so at most 300 frames.
RECORD_MAX_SECONDS: Final[float] = 20.0
RECORD_MIN_SECONDS: Final[float] = 0.5
RECORD_MAX_FPS: Final[int] = 15
#: How long past the burst's own length the runner waits before calling it lost.
RECORD_GRACE_S: Final[float] = 15.0


@dataclass
class _Burst:
    """One ``record`` in flight. Kept on the runner so the timer is not collected."""

    name: str
    directory: Path
    frames: int
    interval_ms: int
    timer: QTimer
    taken: int = 0
    failed: int = 0
    size: tuple[int, int] = (0, 0)
    failures: list[str] = field(default_factory=list)


class BurstVerbsMixin:
    """The ``record`` handler. Type-only declarations of the runner surface it
    uses; the attributes and methods themselves are the runner's."""

    if TYPE_CHECKING:
        _window: QWidget
        _deadline_outcome: Outcome
        _deadline_detail: str
        _deadline_timeout_detail: str
        _deadline_cancel: Callable[[], None] | None
        _burst: _Burst

        def _record(
            self,
            step: Step,
            outcome: Outcome,
            detail: str = "",
            *,
            elapsed: float = 0.0,
            artifact: str = "",
            declined_by_size: bool = False,
        ) -> None: ...

        def _arm_deadline(
            self,
            step: Step,
            seconds: float,
            predicate: Callable[[], bool] | None = None,
        ) -> None: ...

        def _ensure_artifact_dir(self) -> Path | None: ...

    def _do_record(self, step: Step) -> None:
        """A burst of main-window frames: ``<name>-0001.png`` …, and a manifest."""
        from platterpus.uiscript.runner import _is_on_screen, _safe_name

        try:
            seconds = float(step.args[1])
            fps = int(step.args[2])
        except ValueError:
            self._record(
                step,
                Outcome.ERROR,
                f"{step.args[1]!r} {step.args[2]!r}: seconds and fps must be numbers",
            )
            return
        if not RECORD_MIN_SECONDS <= seconds <= RECORD_MAX_SECONDS or not (
            1 <= fps <= RECORD_MAX_FPS
        ):
            self._record(
                step,
                Outcome.ERROR,
                f"a burst runs {RECORD_MIN_SECONDS:g} to {RECORD_MAX_SECONDS:g} s at "
                f"1 to {RECORD_MAX_FPS} fps; got {seconds:g} s at {fps} fps",
            )
            return
        directory = self._ensure_artifact_dir()
        if directory is None:
            self._record(step, Outcome.ERROR, "could not create the run folder")
            return
        name = _safe_name(step.args[0])
        on_screen = _is_on_screen(self._window)
        burst = _Burst(
            name=name,
            directory=directory,
            frames=max(1, round(seconds * fps)),
            interval_ms=max(1, round(1000 / fps)),
            timer=QTimer(),
        )
        self._burst = burst

        def take_frame() -> None:
            index = burst.taken + burst.failed + 1
            if index > burst.frames:
                burst.timer.stop()
                return
            path = burst.directory / f"{burst.name}-{index:04d}.png"
            try:
                pixmap = self._window.grab()
                burst.size = (pixmap.width(), pixmap.height())
                ok = pixmap.save(str(path), "PNG")
            except Exception as exc:  # noqa: BLE001 — a lost frame is counted
                ok = False
                burst.failures.append(f"frame {index}: {exc!r}")
            if ok:
                burst.taken += 1
            else:
                burst.failed += 1
                if len(burst.failures) < burst.failed:
                    burst.failures.append(f"frame {index}: not written")

        def finished() -> bool:
            if burst.taken + burst.failed < burst.frames:
                return False
            burst.timer.stop()
            manifest = _burst_manifest(burst, on_screen)
            (burst.directory / f"{burst.name}-frames.txt").write_text(
                manifest + "\n", encoding="utf-8"
            )
            self._deadline_outcome = (
                Outcome.FAIL
                if burst.failed
                else (Outcome.PASS if on_screen else Outcome.INFO)
            )
            self._deadline_detail = manifest
            return True

        burst.timer.setInterval(burst.interval_ms)
        burst.timer.timeout.connect(take_frame)
        started = time.monotonic()
        take_frame()
        burst.timer.start()
        self._arm_deadline(step, seconds + RECORD_GRACE_S, finished)
        self._deadline_cancel = burst.timer.stop
        self._deadline_timeout_detail = (
            f"the burst {name!r} took {burst.taken} of {burst.frames} frame(s) in "
            f"{time.monotonic() - started:.1f}s and ran out of time; the frames it "
            "took are in the run folder"
        )


def _burst_manifest(burst: _Burst, on_screen: bool) -> str:
    """The burst's one-paragraph record: asked, taken, lost, and how."""
    width, height = burst.size
    lines = [
        f"burst {burst.name!r}: {burst.taken} of {burst.frames} frame(s) taken, "
        f"{burst.failed} lost, one every {burst.interval_ms} ms, {width}x{height}"
        + (
            ""
            if on_screen
            else " — RENDERED while the display was not showing the window: what "
            "the app drew, not proof it was on screen"
        )
    ]
    lines.extend(f"  {failure}" for failure in burst.failures)
    return "\n".join(lines)
