"""The acceptance run's estimate, read from the live window, and its verb (D6).

The model is :mod:`platterpus.uiscript.run_estimate`, pure. This module reads
what it needs from the window (the settings in force, the track table's lengths,
the drive's measured reading speed) and gives it two callers: the runner, which
logs and shows the estimate when a run starts, and the ``run-estimate`` verb,
which records it again from where it stands. The full script puts that verb right
after section E, because a run usually starts before the disc is identified, and
until then no track has a length.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the other
``*_verbs`` modules. Nothing here blocks: it reads attributes and walks the
script's steps once.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from platterpus.config import Config
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.run_estimate import describe, estimate_run

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)


def track_lengths_from(tracks: Iterable[object]) -> dict[int, float]:
    """``{track number: seconds}`` from the track table's rows, where known.

    The lengths are MusicBrainz's (``length_ms``), the ones the rip's own up-front
    estimate uses (``RipWorker._make_estimate``); a placeholder row has none.
    """
    lengths: dict[int, float] = {}
    for track in tracks:
        number = getattr(track, "number", None)
        ms = getattr(track, "length_ms", None)
        if isinstance(number, int) and isinstance(ms, int) and ms > 0:
            lengths[number] = ms / 1000
    return lengths


def estimate_for_window(
    window: object,
    steps: Sequence[Step],
    *,
    run_size: str,
    tick_s: float,
    wait_cap_s: float,
    start_index: int = 0,
) -> str:
    """:func:`describe` for a run against ``window``'s disc and drive. Never raises."""
    try:
        config = getattr(window, "_config", None)
        table = getattr(window, "_track_table", None)
        rate_for = getattr(window, "_read_rate_for_current_drive", None)
        est = estimate_run(
            steps,
            run_size=run_size,
            config=config if isinstance(config, Config) else Config(),
            track_lengths=track_lengths_from(table.tracks()) if table else {},
            rate=rate_for() if callable(rate_for) else None,
            tick_s=tick_s,
            wait_cap_s=wait_cap_s,
            start_index=start_index,
        )
        return describe(est)
    except Exception as exc:  # noqa: BLE001 — an estimate must never stop a run
        log.exception("the acceptance run's estimate failed")
        return f"Run estimate: none, because estimating it failed ({exc!r})."


class EstimateVerbsMixin:
    """The ``run-estimate`` handler. Type-only declarations of the runner surface."""

    if TYPE_CHECKING:
        _window: QWidget
        _steps: list[Step]
        _index: int
        _run_size: str

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

    def _do_run_estimate(self, step: Step) -> None:
        """``run-estimate``: how long the rest of this run should take. INFO.

        From the step after this one to the end, at the run's chosen size. It
        gathers and never fails: a missing figure is a fact about what is known
        yet, said in the sentence, not a defect of the run.
        """
        from platterpus.uiscript.runner import MAX_WAIT_S, TICK_MS

        text = estimate_for_window(
            self._window,
            self._steps,
            run_size=self._run_size,
            tick_s=TICK_MS / 1000,
            wait_cap_s=MAX_WAIT_S,
            start_index=self._index,
        )
        log.info("ui script L%d: %s", step.line_no, text)
        self._record(step, Outcome.INFO, f"for the rest of this run: {text}")
