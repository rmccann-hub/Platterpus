"""DriveSetupWorker — runs drive calibration off the GUI thread.

Offset detection (cyanrip's `offset find`) spins the disc and can take a
minute or more, so it must not run on the GUI thread. This worker drives the
backend's calibration commands and reports a single result object; the GUI
then persists the detected offset as Platterpus's `--offset` override (the
backend does not write any config file itself).

Signals:
  status(str)        — human-readable phase ("Analyzing drive cache…")
  finished(object)   — a DriveSetupResult (always emitted, even on partial
                       failure, so the dialog can show what worked)

Usage mirrors RipWorker: construct on the GUI thread, move to a QThread,
connect QThread.started → run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.adapters.rip_backend import RipBackend, RipError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DriveSetupResult:
    """Outcome of a drive-calibration run.

    Each step is independent: a failed `offset find` (e.g. the disc isn't
    in AccurateRip) still leaves the cache verdict intact, so we report
    both halves rather than aborting on the first error. `offset` /
    `can_defeat_cache` are None when their step didn't yield a value;
    the matching `*_error` carries a user-facing reason instead.
    """

    offset: int | None = None
    can_defeat_cache: bool | None = None
    offset_error: str | None = None
    analyze_error: str | None = None
    #: False when this run did not measure the cache (an offset-only run, TASKS
    #: R150), so the window says nothing about it rather than "not determined".
    cache_attempted: bool = True
    #: How the found offset was agreed, e.g. "14 of this disc's tracks agreed".
    offset_detail: str = ""

    @property
    def ok(self) -> bool:
        """True when every step that actually RAN produced a value (and one did).

        A step the backend *can't* do is not a failure. cyanrip has no offset
        finder, so a cache-only run leaves ``offset`` and ``offset_error`` both
        None ("not attempted") and should succeed on the cache verdict alone.

        REGRESSION (real hardware, 2026-07-26): this was ``offset is not None``,
        so **every** cyanrip run reported "Finished with issues." — including a
        perfect cache measurement — because a cyanrip offset is always None. The
        dialog (and the screen-reader announcement) called a success a failure.
        """
        offset_failed = self.offset is None and self.offset_error is not None
        cache_failed = (
            self.cache_attempted
            and self.can_defeat_cache is None
            and self.analyze_error is not None
        )
        got_something = self.offset is not None or self.can_defeat_cache is not None
        return got_something and not offset_failed and not cache_failed


class DriveSetupWorker(QObject):
    """QObject worker that calibrates one drive via the backend's commands."""

    status = Signal(str)
    finished = Signal(object)  # DriveSetupResult

    def __init__(
        self,
        backend: RipBackend,
        device: str,
        parent: QObject | None = None,
        *,
        cache: bool = True,
        offset: bool | None = None,
    ) -> None:
        """``cache`` and ``offset`` say which measurements this run makes (TASKS
        R150): the window asks for the cache check, the offset search, or both.
        ``offset=None`` keeps the old rule, the search whenever the backend has
        one."""
        super().__init__(parent)
        self._backend: RipBackend = backend
        self._device: str = device
        self._want_cache: bool = cache
        self._want_offset: bool | None = offset
        # Set from the GUI thread when the user closes the dialog. Plain
        # bool assignment is atomic under the GIL.
        self._cancelled: bool = False

    @Slot()
    def cancel(self) -> None:
        """Request cancellation and kill the running detection subprocess.

        Thread-safe and non-blocking: called from the GUI thread. Killing the
        subprocess unblocks `run()` (which is waiting on it) so the QThread can
        finish and be torn down cleanly — without this the dialog's QThread is
        destroyed mid-run and Qt aborts the whole app, and the orphaned reader keeps
        the optical drive spinning.

        The flag alone is **not** cancellation: `run()` only reads it *between* its
        two steps, and a step is a `cd-paranoia -A` that can run for ten minutes. So
        the kill is the part that matters, and for a long time it did not happen —
        `RipBackend.cancel_setup` is a concrete no-op on the ABC and no backend
        overrode it, making this method a flag-setter wearing a killer's docstring
        (audit, 2026-07-29). `CyanripBackend.cancel_setup` now implements it.
        """
        self._cancelled = True
        try:
            self._backend.cancel_setup()
        except Exception:  # noqa: BLE001 — cancel must never raise
            log.exception("cancel_setup() raised; ignored")

    @Slot()
    def run(self) -> None:
        """Run cache analysis + offset find in turn, then report the result."""
        if self._cancelled:
            self.finished.emit(DriveSetupResult())
            return

        # Cache analysis first — it confirms a disc is actually present before
        # the offset search. Skipped when the window asked for the search alone.
        can_defeat: bool | None = None
        analyze_error: str | None = None
        if self._want_cache:
            can_defeat, analyze_error = self._analyze_cache()

        offset: int | None = None
        offset_error: str | None = None
        # Only run the offset finder when the window asked for it and the backend
        # has one (cyanrip's `-f` from 2026-11-25, TASKS R150). When it does not
        # run we leave offset/offset_error both None
        # ("not attempted"), and the dialog omits the offset line entirely.
        want_offset = (
            self._backend.supports_offset_detection()
            if self._want_offset is None
            else self._want_offset and self._backend.supports_offset_detection()
        )
        offset_detail = ""
        if want_offset:
            self.status.emit(
                "Detecting read offset… this can take a minute (needs a CD "
                "that's in the AccurateRip database)."
            )
            if self._cancelled:
                # Don't kick off the long offset search if we're already closing.
                self.finished.emit(
                    DriveSetupResult(
                        can_defeat_cache=can_defeat,
                        analyze_error=analyze_error,
                        cache_attempted=self._want_cache,
                    )
                )
                return
            try:
                offset = self._backend.find_offset(self._device)
                offset_detail = self._backend.offset_search_detail()
            except RipError as exc:
                log.warning("offset find failed: %s", exc)
                offset_error = str(exc)
            except NotImplementedError:
                offset_error = "This backend can't auto-detect the read offset."

        self.finished.emit(
            DriveSetupResult(
                offset=offset,
                can_defeat_cache=can_defeat,
                offset_error=offset_error,
                analyze_error=analyze_error,
                cache_attempted=self._want_cache,
                offset_detail=offset_detail,
            )
        )

    def _analyze_cache(self) -> tuple[bool | None, str | None]:
        """The cache check: its verdict, and why there is none when there is not."""
        self.status.emit("Analyzing drive cache…")
        try:
            can_defeat = self._backend.analyze_drive(self._device)
        except RipError as exc:
            log.warning("drive analyze failed: %s", exc)
            return None, str(exc)
        except NotImplementedError:
            return None, "This backend can't analyze the drive cache."
        if can_defeat is not None:
            return can_defeat, None
        # It ran but couldn't decide. Ask the backend WHY, so the dialog can name
        # the actual problem (tool missing / timed out / unrecognised report)
        # rather than one blank "could not be determined" the user can't act on.
        why = self._backend.cache_analysis_detail() or None
        if why:
            log.info("cache analysis inconclusive: %s", why)
        return None, why
