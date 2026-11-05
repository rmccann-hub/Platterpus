"""The automatic CTDB repair after a rip: when to start it, and what the user is told.

The owner's word of 2026-11-05 (``PLANNING.md`` KDD-47, amended): *"Should
ripping to a good file need a button? Either we are confident it will happen or
not, if not we need to fix that or then leave for the user but let them know."*
So there is no button. After the CTDB check of a finished rip, when it finds the
rip differs from CTDB's strongest entry and the Settings switch is on (the
default), this mixin starts :class:`~platterpus.workers.ctdb_repair_worker.
CtdbRepairWorker` and, when it lands, records it and says what happened.

**The pipeline, in order** (the decision of 2026-11-05, TASKS R133):

1. The rip finishes; tagging, cover art and the derived-format transcode run on
   the post-rip daemon; the CTDB check, the FLAC integrity check, the derived
   verify and the checksums run after it (``main_window_rip``).
2. The CTDB check lands (``RipMixin._on_ctdb_verified``). The verdict is shown
   and written into the EAC-layout log at once, as the record of the read
   (KDD-24). When a repair is wanted, the result is NOT recorded yet: the report's
   ``ctdb`` gate stays pending, so neither the library move nor an acceptance
   step settles on an album whose files are about to change.
3. The worker waits for the other readers, repairs (every proof, or nothing is
   replaced), and verifies the repaired files again.
4. It lands here: the read's verdict is recorded with ``repair`` and
   ``after_repair`` beside it, and the user is told. After a REPAIRED outcome the
   derived copies are made again from the repaired FLAC (the same transcode,
   whole album, so an MP3's album ReplayGain stays an album figure), and the
   derived verify, the checksums and the FLAC integrity check run again on what
   is now on disk. Their earlier results are cleared first: they describe files
   that no longer exist.

**Why re-derive rather than move the transcode after the repair.** Moving it
would delay every rip's MP3 by a whole CTDB lookup and decode to serve the rare
rip that needs a repair; re-deriving costs that only the rips that were repaired.

**What holds the library move.** ``_ctdb_repair_busy``: set by the CTDB check's
own daemon BEFORE it emits, whenever a repair may start, so the settlement poll
can never see "every check finished" in the gap between that daemon ending and
this slot running; cleared once the repair has landed and its re-runs are
launched (or when the slot decides not to start one).
"""

from __future__ import annotations

import dataclasses
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QThread

from platterpus import diagnostics, rip_files
from platterpus.adapters.transcode import TranscodeResult, transcode_files
from platterpus.ctdb.repair_run import differs_from_strongest
from platterpus.ctdb.repair_types import RepairStatus, failed, refused
from platterpus.ctdb.repair_wording import (
    ANOTHER_REPAIR,
    CLOSED_UNFINISHED,
    IN_PROGRESS,
    NEWER_RIP,
    OFF_IN_SETTINGS,
    repair_text,
)
from platterpus.ui.failure_text import LOG_POINTER
from platterpus.ui.main_window_shared import MainWindowShared
from platterpus.workers import start_worker_thread
from platterpus.workers.ctdb_repair_worker import CtdbRepairOutcome, CtdbRepairWorker

if TYPE_CHECKING:
    from platterpus.ctdb.verify import CtdbVerifyResult

log = logging.getLogger(__name__)

#: How many albums' repair contexts are kept. A repair starts within seconds of
#: its CTDB check, so a handful is plenty.
_CONTEXTS_KEPT: Final[int] = 4

#: The diagnostic code and severity for each outcome (``diagnostics.KNOWN_CODES``).
_DIAGNOSTIC: Final[dict[RepairStatus, tuple[str, str]]] = {
    RepairStatus.REPAIRED: ("ctdb_repair.repaired", diagnostics.INFO),
    RepairStatus.REFUSED: ("ctdb_repair.refused", diagnostics.WARNING),
    RepairStatus.FAILED: ("ctdb_repair.failed", diagnostics.ERROR),
}


@dataclass(frozen=True)
class CtdbRepairContext:
    """What a repair needs from the rip it follows, frozen at the rip's finish.

    Read on the GUI thread when the rip finishes, because by the time the CTDB
    check lands the window may describe another disc and Settings may have
    changed: the derived format re-made after a repair must be the one this rip
    made, not the one chosen since.
    """

    rip_dir: Path
    rip_log: object | None
    disc_tracks_hint: int | None
    transcode_fmt: str
    mp3_vbr_quality: int
    flac_verify: bool


class CtdbRepairMixin(MainWindowShared):
    """The window's half of the automatic CTDB repair (TASKS R133).

    Its slots (``_ctdb_repair_worker``, ``_ctdb_repair_thread``, ``_ctdb_repair_busy``
    and the rest) are declared on ``MainWindowShared``, where the QThread sweeps read
    them, and set by :meth:`_init_ctdb_repair_state`.
    """

    def _init_ctdb_repair_state(self) -> None:
        """Set the repair's slots; called once from ``MainWindow.__init__``."""
        self._ctdb_repair_worker = None
        self._ctdb_repair_thread = None
        self._ctdb_repair_busy = False
        self._ctdb_repair_generation = None
        self._ctdb_repair_pending = None
        self._ctdb_repair_contexts = {}

    # --- frozen at the rip's finish -------------------------------------------

    def _note_ctdb_repair_context(self, context: CtdbRepairContext) -> None:
        """Keep what a repair of THIS rip would need, under its generation."""
        self._ctdb_repair_contexts[self._rip_generation] = context
        for stale in sorted(self._ctdb_repair_contexts)[:-_CONTEXTS_KEPT]:
            del self._ctdb_repair_contexts[stale]

    def _ctdb_repair_enabled(self, generation: int) -> bool:
        """The switch as this rip ran under it: frozen at Start on its record."""
        record = self._post_rip_record(generation)
        frozen = (record.settings if record is not None else {}).get(
            "ctdb_repair_after_rip"
        )
        if isinstance(frozen, bool):
            return frozen
        return bool(getattr(self._config, "ctdb_repair_after_rip", False))

    def _arm_ctdb_repair(self, generation: int, result: object) -> None:
        """Called on the CTDB check's DAEMON, before it emits: hold the move.

        Only sets a flag (an attribute write, atomic under CPython): the decision
        proper is made on the GUI thread in :meth:`_route_ctdb_result`, which
        clears the flag again when it starts nothing. Arming too often costs one
        poll; arming too late would let the album be filed while its files change.
        """
        if differs_from_strongest(result) and self._ctdb_repair_enabled(generation):
            self._ctdb_repair_busy = True

    # --- the decision, on the GUI thread --------------------------------------

    def _ctdb_repair_blocker(self, generation: int) -> str | None:
        """Why a wanted repair cannot start now, or None when it can.

        A named function returning WHICH condition refused (``CLAUDE.md``: check
        the preconditions where the thing happens, and say which one said no).
        """
        if not self._ctdb_repair_enabled(generation):
            return OFF_IN_SETTINGS
        if generation != self._rip_generation:
            return NEWER_RIP
        if self._ctdb_repair_running():
            return ANOTHER_REPAIR
        return None

    def _ctdb_repair_running(self) -> bool:
        """Whether a repair worker's thread is still alive."""
        thread = self._ctdb_repair_thread
        if thread is None:
            return False
        try:
            return bool(thread.isRunning())
        except RuntimeError:  # the C++ object is already gone
            return False

    def _route_ctdb_result(self, generation: int, result: object) -> object | None:
        """Start a repair for this CTDB result, or say why not. On the GUI thread.

        Returns the result the caller must record now, or None when a repair has
        started and will record the result itself when it lands. A rip that does
        not differ from the strongest entry passes straight through unchanged.
        """
        from platterpus.ctdb.verify import CtdbVerifyResult

        if not isinstance(result, CtdbVerifyResult) or not differs_from_strongest(
            result
        ):
            self._release_ctdb_repair_hold(generation)
            return result
        if generation not in self._ctdb_repair_contexts:
            # Only a CTDB check the finish handler started can be repaired: it is
            # what records the album folder and the formats. Nothing else starts
            # one in the app, so this is a check run by other means (a test); it
            # is logged rather than called a refusal the user would have to read.
            log.warning(
                "CTDB result for rip %d differs from the strongest entry, but no "
                "rip context was recorded for it; no repair attempted",
                generation,
            )
            self._release_ctdb_repair_hold(generation)
            return result
        blocker = self._ctdb_repair_blocker(generation)
        if blocker is not None:
            self._release_ctdb_repair_hold(generation)
            declined = dataclasses.replace(result, repair=refused(blocker))
            self._tell_ctdb_repair(generation, declined)
            return declined
        self._start_ctdb_repair(generation, result)
        return None

    def _release_ctdb_repair_hold(self, generation: int) -> None:
        """Clear the move's hold, unless a repair of another album holds it."""
        if not self._ctdb_repair_running() and self._ctdb_repair_pending is None:
            self._ctdb_repair_busy = False

    def _start_ctdb_repair(self, generation: int, result: CtdbVerifyResult) -> None:
        """Start the worker for this album; the CTDB gate stays pending meanwhile."""
        context = self._ctdb_repair_contexts[generation]
        record = self._post_rip_record(generation)
        if record is not None:
            # Pending again (the CTDB daemon's own `finally` took it out): the
            # report must not settle on a CTDB block the repair is about to finish.
            record.pending.add("ctdb")
        self._ctdb_repair_busy = True
        self._ctdb_repair_generation = generation
        self._ctdb_repair_pending = result
        # The album's other readers, read HERE on the GUI thread: the worker waits
        # for them so their results describe what they read, and so re-running
        # them afterwards never overlaps a run still in flight.
        readers = [
            thread
            for attr in (
                "_post_rip_thread",
                "_flac_verify_thread",
                "_derived_verify_thread",
                "_checksums_thread",
            )
            if isinstance(thread := getattr(self, attr, None), threading.Thread)
        ]
        worker = CtdbRepairWorker(
            result,
            context.rip_dir,
            client=self._ctdb_client,
            rip_log=context.rip_log,
            disc_tracks_hint=context.disc_tracks_hint,
            wait_for=readers,
        )
        thread = QThread(self)
        self._ctdb_repair_worker = worker
        self._ctdb_repair_thread = thread
        worker.done.connect(self._on_ctdb_repair_done)
        thread.finished.connect(self._on_ctdb_repair_thread_finished)
        log.info("starting the CTDB repair for %s", context.rip_dir)
        self._rip_progress.set_ctdb_repair(IN_PROGRESS, "neutral")
        self._rip_progress.append_log_line(IN_PROGRESS)
        start_worker_thread(worker, thread, worker.run)

    def _on_ctdb_repair_thread_finished(self) -> None:
        """The worker's thread has stopped: drop the slots (Qt deletes it later)."""
        self._ctdb_repair_worker = None
        self._ctdb_repair_thread = None

    # --- the outcome ------------------------------------------------------------

    def _on_ctdb_repair_done(self, outcome: object) -> None:
        """The worker finished (queued to the GUI thread): record, tell, re-run."""
        if isinstance(outcome, CtdbRepairOutcome):
            self._land_ctdb_repair(outcome, closing=False)

    def _land_ctdb_repair(self, outcome: CtdbRepairOutcome, *, closing: bool) -> None:
        """Record the outcome against its album and say what happened.

        Shared by the worker's signal and the window closing, so the two cannot
        record a repair two ways. ``closing`` skips what a closing window must not
        start: the UI and the re-runs.
        """
        generation = self._ctdb_repair_generation
        self._ctdb_repair_pending = None
        self._ctdb_repair_generation = None
        if generation is None:
            self._ctdb_repair_busy = False
            return
        result = outcome.result
        record = self._post_rip_record(generation)
        if record is not None:
            record.pending.discard("ctdb")
        self._diagnose_ctdb_repair(result)
        self._record_post_rip_result(generation, "ctdb", result)
        if not closing:
            self._tell_ctdb_repair(generation, result)
            repaired = (
                result.repair is not None
                and result.repair.status is RepairStatus.REPAIRED
            )
            if repaired:
                self._rerun_after_ctdb_repair(generation)
        self._ctdb_repair_busy = False

    def _diagnose_ctdb_repair(self, result: CtdbVerifyResult) -> None:
        """Put the outcome in the diagnostics (the log and the report's block)."""
        record = result.repair
        if record is None:
            return
        code, severity = _DIAGNOSTIC[record.status]
        tracks = ", ".join(str(row.track) for row in record.tracks) or "none"
        diagnostics.record(
            severity,
            code,
            f"CTDB repair {record.status.value}: "
            + (
                record.reason
                or f"track(s) {tracks} rewritten toward entry "
                f"{record.entry_id} ({record.confidence:,} submissions)"
            ),
            where="ui.main_window_ctdb_repair",
        )

    def _tell_ctdb_repair(self, generation: int, result: CtdbVerifyResult) -> None:
        """Show the outcome on the results pane and in the log view, if on screen."""
        said = repair_text(result, log_pointer=LOG_POINTER)
        if said is None or generation != self._rip_generation:
            return
        level, text = said
        self._rip_progress.set_ctdb_repair(text, level)
        self._rip_progress.append_log_line(text)

    def _rerun_after_ctdb_repair(self, generation: int) -> None:
        """Re-make the derived copies and re-check what is on disk now.

        Only for the album on screen: every launcher below registers against the
        current rip (``_launch_post_rip_daemon``), so for an album the window has
        moved on from the copies are left, and that is said in the log.
        """
        context = self._ctdb_repair_contexts.get(generation)
        record = self._post_rip_record(generation)
        if context is None or record is None:
            return
        if generation != self._rip_generation:
            log.warning(
                "CTDB repair landed after a newer rip started: the derived copies and "
                "checksums of %s were not made again from the repaired FLAC",
                context.rip_dir,
            )
            return
        # These describe files the repair replaced. Cleared, not kept: a stale claim
        # about a file that no longer exists is not a result.
        record.checksums = None
        record.audio_md5 = None
        record.flac_verify = None
        rederive: threading.Thread | None = None
        if context.transcode_fmt:
            record.transcode = None
            record.derived_verify = None
            rederive = self._start_rederive(context)
            self._start_derived_verify(
                context.rip_dir, context.transcode_fmt, wait_for=rederive
            )
        self._start_checksums(context.rip_dir, wait_for=rederive)
        if context.flac_verify:
            self._start_flac_verify(context.rip_dir, wait_for=None)

    def _start_rederive(self, context: CtdbRepairContext) -> threading.Thread:
        """Transcode the whole album again from the repaired FLACs, on a daemon.

        The same function and the same settings as the first transcode
        (``adapters/transcode.transcode_files``), so the copies are made the same
        way; its result replaces the first one in the report.
        """
        fmt = context.transcode_fmt
        self._rip_progress.append_log_line(
            f"ⓘ Making the {fmt.upper()} copies again from the repaired FLAC…"
        )

        def compute(_still_current: Callable[[], bool]) -> object:
            paths = list(
                rip_files.rip_master_files(
                    context.rip_dir, rip_log=context.rip_log
                ).files
            )
            try:
                return transcode_files(
                    paths, fmt=fmt, mp3_vbr_quality=context.mp3_vbr_quality
                )
            except Exception:  # noqa: BLE001 — must never crash the GUI
                log.exception("re-deriving after the CTDB repair failed unexpectedly")
                return TranscodeResult(error="failed unexpectedly")

        return self._launch_post_rip_daemon(
            compute=compute,
            signal=self.transcode_done,
            thread_attr="_post_rip_thread",
        )

    # --- closing ----------------------------------------------------------------

    def _land_ctdb_repair_on_close(self) -> None:
        """Record a repair the window is closing on, after its thread was stopped.

        Called from ``closeEvent`` after ``stop_thread`` cancelled the worker and
        waited, and before the final report flush. The worker's own outcome when
        it finished in time (its signal can no longer be delivered); otherwise the
        read's verdict with a record saying the app closed first. Either way the
        read's verdict reaches the report rather than being left as a pending gate.
        """
        pending = self._ctdb_repair_pending
        if pending is None:
            self._ctdb_repair_busy = False
            return
        worker = self._ctdb_repair_worker
        outcome = worker.outcome if worker is not None else None
        if outcome is None:
            outcome = CtdbRepairOutcome(
                dataclasses.replace(pending, repair=failed(CLOSED_UNFINISHED)),
                cancelled=True,
            )
        self._land_ctdb_repair(outcome, closing=True)
