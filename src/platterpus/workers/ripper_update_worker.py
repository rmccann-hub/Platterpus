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
from platterpus.deps.ripper_offer import OFFER_NOT_DETERMINED, RipperOffer

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

    def _probe_installed_commit(self) -> str | None:
        """The fork commit of the binary that is **actually installed**.

        Read off the binary here, on the worker's own thread, rather than taken
        from the caller. That is the whole fix: this used to arrive as a
        constructor argument the window filled from a cached
        ``self._observed_ripper_banner`` — an attribute **assigned nowhere in the
        tree**. The read could not raise (``getattr`` with a default), so it
        yielded ``None`` on every call and :func:`evaluate_offer` fell back to the
        build-time constant ``FORK_PIN``. The dialog therefore told an operator
        running ``c4d1a00`` that they had *"release 11 (ddf7ac3)"*, and kept
        saying it after every successful install (2026-08-17).

        **A cached observation needs a producer somebody remembers to write; a
        probe does not.** So there is no cache any more.

        It belongs on this thread because the probe shells out to the
        host-exported ripper, which enters a Distrobox container — seconds on a
        cold container, and the GUI-thread rule forbids that on the main thread.

        Never raises and never blocks the result: every failure yields ``None``,
        which :func:`evaluate_offer` already treats as "fall back to the pin",
        and the constructor argument stays honoured as a test seam.
        """
        if self.installed_commit:
            return self.installed_commit
        try:
            from platterpus.deps.checks import check_cyanrip
            from platterpus.paths import CYANRIP_BINARY_DEFAULT
            from platterpus.ripper_identity import fork_commit_from_banner

            probe = check_cyanrip(CYANRIP_BINARY_DEFAULT)
            if not probe.present:
                return None
            return fork_commit_from_banner(str(probe.raw_output or ""))
        except Exception:  # noqa: BLE001 — a probe must never fail the check
            log.warning("could not read the installed ripper banner", exc_info=True)
            return None

    @Slot()
    def run(self) -> None:
        from platterpus.deps.ripper_manifest import fetch_manifest
        from platterpus.deps.ripper_offer import evaluate_offer

        try:
            manifest = fetch_manifest(fetch=self._fetcher.fetch)
            offer = evaluate_offer(
                manifest, self.channel, installed_commit=self._probe_installed_commit()
            )
        except Exception:  # noqa: BLE001 — a worker must always finish
            log.exception("ripper update check crashed")
            # **The recovery must not call the thing that just failed.**
            #
            # This branch originally rebuilt the verdict by calling `evaluate_offer`
            # again — reasoning that one expression of "not determined" beats two.
            # That reasoning is right in general and wrong here: if `evaluate_offer`
            # is what raised, the recovery raises too, `run()` propagates, and
            # `finished` is never emitted. A worker that never finishes is a thread
            # `stop_thread` cannot join, so closing the window waits out the whole
            # shutdown budget and then abandons it (CLAUDE.md rule 9).
            #
            # So the fallback is assembled here, from constants, with no call that
            # can fail. `tests/test_ripper_update_worker.py` pins it by making
            # `evaluate_offer` raise.
            offer = RipperOffer(
                verdict=OFFER_NOT_DETERMINED,
                channel=self.channel,
                release=None,
                detail=(
                    "Couldn't check for a newer cyanrip build — the check itself "
                    "failed. Your installed ripper is unchanged, and this is not "
                    "evidence that it is out of date. The details are in the log."
                ),
            )
        self.finished.emit(offer)
