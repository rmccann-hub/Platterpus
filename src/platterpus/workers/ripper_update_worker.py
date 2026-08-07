"""RipperUpdateWorker — asks the cyanrip fork whether a newer build is published.

One short HTTPS GET, which is exactly why it needs a worker: the GUI thread must
never block on the network, and a stalled or absent connection would freeze the
window for the whole timeout. Same minimal shape as
:class:`platterpus.workers.update_worker.UpdateCheckWorker`.

The worker does **not** read the config: the window reads the channel on the GUI
thread and hands it over as a plain string, so nothing touches shared state off-
thread. It also does not install anything — see
:mod:`platterpus.deps.ripper_offer` for why that is deliberate rather than
unfinished.

Signals:
  finished(object) — a :class:`~platterpus.deps.ripper_offer.RipperOffer`, always.
    Never ``None``: "couldn't determine" is a verdict this subsystem carries
    explicitly, and a null would push that distinction onto every caller.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from platterpus.deps.ripper_manifest import CHANNEL_STABLE, CancellableFetcher

log = logging.getLogger(__name__)


class RipperUpdateWorker(QObject):
    """QObject worker: fetch the fork's release manifest, emit an offer."""

    finished = Signal(object)  # RipperOffer

    def __init__(
        self,
        channel: str = CHANNEL_STABLE,
        installed_commit: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        """``channel`` is the user's ripper update channel (``config.ripper_channel``).

        ``installed_commit`` is the fork commit actually installed, when the window
        could read it off the binary's banner. ``None`` means "fall back to the
        commit this build pins", which is what a user who has never run
        ``--install-ripper`` has.
        """
        super().__init__(parent)
        self.channel: str = channel
        self.installed_commit: str | None = installed_commit
        # The interruptible fetch. Held on the instance so `cancel()` — called from
        # the GUI thread by `stop_thread` during `closeEvent` — can close the socket
        # out from under a blocked read. `QThread.quit()` cannot reach a thread
        # sitting in `read()`, and a flag the blocked call never checks is a false
        # promise (CLAUDE.md rule 9), so this is the handle that makes the cancel real.
        self._fetcher: CancellableFetcher = CancellableFetcher()

    @Slot()
    def cancel(self) -> None:
        """Break an in-flight fetch. Safe from any thread, and safe to call twice."""
        self._fetcher.cancel()

    @Slot()
    def run(self) -> None:
        from platterpus.deps.ripper_manifest import fetch_manifest
        from platterpus.deps.ripper_offer import evaluate_offer

        try:
            manifest = fetch_manifest(fetch=self._fetcher.fetch)
            offer = evaluate_offer(
                manifest, self.channel, installed_commit=self.installed_commit
            )
        except Exception:  # noqa: BLE001 — a worker must always finish
            log.exception("ripper update check crashed")
            # Build the "not determined" answer from the same function rather than
            # hand-assembling one here: two ways to express the same verdict is two
            # things to drift, and this path is the one nobody looks at.
            from platterpus.deps.ripper_offer import evaluate_offer as _evaluate

            offer = _evaluate(None, self.channel)
        self.finished.emit(offer)
