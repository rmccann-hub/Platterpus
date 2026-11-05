# SPDX-License-Identifier: GPL-3.0-only
"""The automatic CTDB repair after a rip, on a worker with a real ``cancel()`` (R133).

The owner's word of 2026-11-05 (``PLANNING.md`` KDD-47, amended: *no button*):
after a rip whose CTDB check finds it differs from the strongest entry, the app
repairs it **on its own, if and only if every proof passes**, checks it again,
and says what it did; when it cannot, it says why. This is the worker that does
the work; ``ui/main_window_ctdb_repair.py`` decides when to start it and tells
the user.

**Why a ``QThread`` worker and not a daemon like the CTDB verify.** The other
post-rip checks only READ the album and run on daemon threads that die with the
process (``docs/architecture.md`` §3.2). The repair WRITES the archival master,
so it must be stoppable on demand: closing the window cancels it, and the cancel
has to reach the ``flac`` child it is blocked in. Every child process the repair
runs (the ``metaflac`` length probes, the ``flac`` decodes and encode, the
``metaflac`` metadata copy, and the fresh verify's decodes afterwards) goes
through ONE :class:`~platterpus.killable.KillableJob`, so ``cancel()`` SIGKILLs
the one in flight and refuses every later one. A kill is safe by construction:
every child that writes, writes only a hidden candidate file, which the core
deletes on any failure (``ctdb/repair.py``); the original is replaced only by
the commit, a link and a rename with no child process.

What it does, in order (:meth:`CtdbRepairWorker.run`):

1. **Waits for the album's other readers** (the FLAC integrity check, the
   derived-file verify, the checksums), so their results describe the files
   they read and the window can run them again on the repaired files without
   two runs of one check overlapping. Bounded, and cancel-aware.
2. **Repairs** through ``ctdb/repair_run.repair_verified_rip`` (the one caller
   of the core), fed AccurateRip's per-track answer from the rip's own log, and
   refusing outright when that answer cannot be lined up with the files.
3. **Verifies again** after a REPAIRED outcome: a fresh lookup and decode of the
   repaired files (``ctdb_worker.verify_rip_dir``), kept as ``after_repair``
   BESIDE the read's verdict, never in its place (KDD-24).

Never raises; always emits :attr:`CtdbRepairWorker.done` then ``finished``. The
outcome is also kept on the worker (:attr:`CtdbRepairWorker.outcome`), so a
window closing can record what happened after the signal can no longer be
delivered.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PySide6.QtCore import QObject, Signal, Slot

from platterpus import rip_files
from platterpus.adapters.ctdb_client import CTDBClient
from platterpus.adapters.flac_rewrite import FlacRewriter, killable_runner
from platterpus.ctdb import decode
from platterpus.ctdb.repair import PcmDecoder
from platterpus.ctdb.repair_run import accuraterip_answers, repair_verified_rip
from platterpus.ctdb.repair_types import RepairRecord, RepairStatus, failed, refused
from platterpus.ctdb.repair_wording import CANCELLED
from platterpus.ctdb.toc import SamplesProbe
from platterpus.ctdb.verify import CtdbVerifyResult
from platterpus.killable import KillableJob
from platterpus.workers.ctdb_worker import verify_rip_dir

log = logging.getLogger(__name__)

#: How long the repair waits for the album's other readers before giving up.
#: Far above any real check (a WavPack verify of a long album decodes it twice);
#: the bound only stops a wedged reader holding the repair forever.
READERS_SETTLE_S: Final[float] = 900.0
#: How often a wait re-checks for a cancel. Short, so closing the window is prompt.
_POLL_S: Final[float] = 0.2

#: ``(flac_paths, result, accuraterip, probe, decoder, rewriter) -> result``.
RepairCall = Callable[
    [
        Sequence[Path],
        CtdbVerifyResult,
        Mapping[int, bool | None],
        SamplesProbe,
        PcmDecoder,
        FlacRewriter,
    ],
    CtdbVerifyResult,
]
#: ``(rip_dir, decoder, probe) -> result or None``: the fresh verify afterwards.
ReverifyCall = Callable[[Path, PcmDecoder, SamplesProbe], CtdbVerifyResult | None]


@dataclass(frozen=True)
class CtdbRepairOutcome:
    """What the worker did. ``result`` is the READ's verdict with ``repair`` set.

    ``result.after_repair`` holds the fresh verify when a repair changed a file.
    ``cancelled`` is True when :meth:`CtdbRepairWorker.cancel` was called before
    the work ended, whatever the record says (a cancel that landed after the
    commit leaves a REPAIRED record, which is the truth about the files).
    """

    result: CtdbVerifyResult
    cancelled: bool = False


def _default_repair(
    paths: Sequence[Path],
    result: CtdbVerifyResult,
    accuraterip: Mapping[int, bool | None],
    probe: SamplesProbe,
    decoder: PcmDecoder,
    rewriter: FlacRewriter,
) -> CtdbVerifyResult:
    return repair_verified_rip(
        paths,
        result,
        accuraterip_verified=accuraterip,
        samples_probe=probe,
        decoder=decoder,
        rewriter=rewriter,
    )


class CtdbRepairWorker(QObject):
    """Repair one album toward CTDB's strongest entry, then verify it again."""

    done = Signal(object)  # CtdbRepairOutcome
    finished = Signal()

    def __init__(
        self,
        result: CtdbVerifyResult,
        rip_dir: Path,
        *,
        client: CTDBClient,
        rip_log: object | None = None,
        disc_tracks_hint: int | None = None,
        wait_for: Sequence[threading.Thread] = (),
        repair: RepairCall | None = None,
        reverify: ReverifyCall | None = None,
        settle_s: float = READERS_SETTLE_S,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._result: CtdbVerifyResult = result
        self._rip_dir: Path = Path(rip_dir)
        self._client: CTDBClient = client
        self._rip_log: object | None = rip_log
        self._disc_tracks_hint: int | None = disc_tracks_hint
        self._wait_for: tuple[threading.Thread, ...] = tuple(wait_for)
        self._repair: RepairCall = repair or _default_repair
        self._reverify: ReverifyCall = reverify or self._default_reverify
        self._settle_s: float = settle_s
        # ONE job for every child process this repair runs: its cancel kills the
        # one in flight and refuses the rest (`killable.KillableJob`).
        self._job: KillableJob = KillableJob("CTDB repair")
        self._outcome: CtdbRepairOutcome | None = None
        self._outcome_lock: threading.Lock = threading.Lock()

    # --- the killable seams --------------------------------------------------

    def _decoder(self, path: Path) -> bytes:
        return decode.decode_flac_to_pcm(path, runner=decode.killable_runner(self._job))

    def _probe(self, path: Path) -> int:
        return decode.total_samples(
            path, runner=decode.killable_probe_runner(self._job)
        )

    def _default_reverify(
        self, rip_dir: Path, decoder: PcmDecoder, probe: SamplesProbe
    ) -> CtdbVerifyResult | None:
        return verify_rip_dir(
            self._client,
            rip_dir,
            rip_log=self._rip_log,
            disc_tracks_hint=self._disc_tracks_hint,
            decoder=decoder,
            samples_probe=probe,
        )

    # --- the public surface --------------------------------------------------

    def cancel(self) -> None:
        """SIGKILL the child in flight and refuse every later one. Non-blocking.

        The repair blocks inside ``flac`` and ``metaflac`` children, which
        ``QThread.quit()`` cannot reach, so the kill is what makes this real
        (``CLAUDE.md`` rule 9). The waits in step 1 poll the same job's flag every
        :data:`_POLL_S`. What it cannot interrupt: the fresh verify's CTDB
        lookup, an HTTP GET bounded by the client's own timeout.
        """
        self._job.cancel()

    @property
    def outcome(self) -> CtdbRepairOutcome | None:
        """What the worker did, once it has finished; None until then."""
        with self._outcome_lock:
            return self._outcome

    @Slot()
    def run(self) -> None:
        """Do the work; always emit ``done`` and then ``finished``. Never raises."""
        try:
            outcome = self._run()
        except Exception as exc:  # noqa: BLE001 — a worker must always finish
            log.exception("the CTDB repair crashed")
            outcome = CtdbRepairOutcome(
                dataclasses.replace(
                    self._result,
                    repair=failed(f"the repair crashed ({type(exc).__name__}: {exc})"),
                ),
                cancelled=self._job.cancelled,
            )
        with self._outcome_lock:
            self._outcome = outcome
        self.done.emit(outcome)
        self.finished.emit()

    # --- the work ------------------------------------------------------------

    def _with_repair(self, record: RepairRecord) -> CtdbRepairOutcome:
        return CtdbRepairOutcome(
            dataclasses.replace(self._result, repair=record),
            cancelled=self._job.cancelled,
        )

    def _readers_settled(self) -> str | None:
        """Wait for the album's other readers; why not, or None once they are done."""
        started = time.monotonic()
        for thread in self._wait_for:
            while thread.is_alive():
                if self._job.cancelled:
                    return CANCELLED
                if time.monotonic() - started > self._settle_s:
                    return (
                        "the album's other checks were still reading its files after "
                        f"{self._settle_s:.0f} s, so the repair did not start"
                    )
                thread.join(_POLL_S)
        return None

    def _run(self) -> CtdbRepairOutcome:
        waited = self._readers_settled()
        if waited is not None:
            maker = failed if waited == CANCELLED else refused
            return self._with_repair(maker(waited))
        flac_paths = list(
            rip_files.rip_master_files(self._rip_dir, rip_log=self._rip_log).files
        )
        answers = accuraterip_answers(self._rip_log, len(flac_paths))
        if answers is None:
            return self._with_repair(
                refused(
                    "the rip's log could not be matched track for track with its "
                    "files, so AccurateRip's answer for each track is not known, and "
                    "a repair is never made without it"
                )
            )
        repaired = self._repair(
            flac_paths,
            self._result,
            answers,
            self._probe,
            self._decoder,
            FlacRewriter(runner=killable_runner(self._job)),
        )
        record = repaired.repair
        is_repaired = record is not None and record.status is RepairStatus.REPAIRED
        if self._job.cancelled and not is_repaired:
            # The core said why it stopped (a decode killed mid-way reads as a
            # failed decode); the user is told the cause, which is the cancel.
            return CtdbRepairOutcome(
                dataclasses.replace(repaired, repair=failed(CANCELLED)),
                cancelled=True,
            )
        if not is_repaired or self._job.cancelled:
            return CtdbRepairOutcome(repaired, cancelled=self._job.cancelled)
        log.info("CTDB repair committed; verifying the repaired files against CTDB")
        after = self._reverify(self._rip_dir, self._decoder, self._probe)
        return CtdbRepairOutcome(
            dataclasses.replace(repaired, after_repair=after),
            cancelled=self._job.cancelled,
        )
