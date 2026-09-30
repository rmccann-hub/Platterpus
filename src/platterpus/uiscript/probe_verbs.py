"""The acceptance script's rig verbs: questions a run asks of its surroundings.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like
:mod:`platterpus.uiscript.artifact_verbs`, so each handler is reachable as
``runner._do_<verb>`` while the runner file does not grow.

* ``expect-newest-pair`` — round 30's D3: the run tests only the newest pair.
* ``expect-found-offset`` — grades the previous ``cyanrip -f``'s offset against
  the drive's (the fork's round 30 lap 3 S24).
* ``cache-probe`` — ``cd-paranoia -A`` beside cyanrip's own cache probe, so each
  run measures the drive's cache both ways (the same S24).

**Nothing here blocks the GUI thread.** The two reads that can take seconds or
minutes, the network fetches and ``cd-paranoia -A``, run on a daemon thread
that touches nothing Qt; the runner's deadline machinery polls a predicate on
each tick and records the answer once it is there. A stopped run abandons the
thread, which is safe because it holds no Qt object and every read it makes is
bounded by its adapter's own timeout.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from platterpus import inbound_text
from platterpus.uiscript import probe_grading
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: How long the two fetches of ``expect-newest-pair`` may take together. Each
#: adapter has its own timeout well inside this; the deadline is the backstop.
PAIR_WAIT_S: Final[float] = 120.0

#: ``cd-paranoia -A`` reads the disc at several points. Its adapter stops it at
#: 600 s; this deadline sits just beyond that so the adapter's answer, not the
#: runner's, is the one recorded.
CACHE_PROBE_WAIT_S: Final[float] = 630.0


@dataclass
class _Job:
    """One helper thread's result. ``done`` is set LAST, after every field."""

    done: threading.Event = field(default_factory=threading.Event)
    value: object = None
    error: str = ""


def _start(work: Callable[[], object], name: str) -> _Job:
    """Run ``work`` on a daemon thread; a failure is kept as text, never raised."""
    job = _Job()

    def run() -> None:
        try:
            job.value = work()
        except Exception as exc:  # noqa: BLE001 — a helper thread must not die silently
            log.exception("ui script helper %s failed", name)
            job.error = repr(exc)
        finally:
            job.done.set()

    threading.Thread(target=run, name=f"uiscript-{name}", daemon=True).start()
    return job


class ProbeVerbsMixin:
    """The ``expect-newest-pair``, ``expect-found-offset`` and ``cache-probe``
    handlers. Type-only declarations of the runner surface they use."""

    if TYPE_CHECKING:
        _window: QWidget
        _drive_offset: int | None
        _last_cyanrip_argv: list[str]
        _last_cyanrip_output: str
        _deadline_outcome: Outcome
        _deadline_detail: str
        _deadline_timeout_detail: str
        _deadline_cancel: Callable[[], None] | None

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

    def _do_expect_newest_pair(self, step: Step) -> None:
        """D3: refuse the run unless both halves of the pair are the newest."""
        from platterpus import __version__, update_check
        from platterpus.deps import fork_source, ripper_manifest

        def fetch() -> object:
            # Ours from the beta channel, because every `v0.*` tag of ours is a
            # pre-release: the stable channel would show none of them.
            return (
                ripper_manifest.fetch_manifest(),
                update_check.latest_release(channel=update_check.CHANNEL_BETA),
            )

        job = _start(fetch, "newest-pair")

        def answered() -> bool:
            if not job.done.is_set():
                return False
            if job.error or not isinstance(job.value, tuple):
                self._deadline_outcome = Outcome.FAIL
                self._deadline_detail = (
                    f"the release reads failed ({job.error or 'no answer'}), so "
                    "whether this is the newest pair is not determined (D3)"
                )
                return True
            manifest, ours = job.value
            grade = probe_grading.grade_newest_pair(
                manifest,
                ours,
                under_review=fork_source.PIN_UNDER_REVIEW,
                app_version=__version__,
            )
            self._deadline_outcome = Outcome.PASS if grade.passed else Outcome.FAIL
            self._deadline_detail = grade.detail
            return True

        self._arm_deadline(step, PAIR_WAIT_S, answered)
        self._deadline_timeout_detail = (
            f"the release reads did not answer within {PAIR_WAIT_S:.0f}s, so whether "
            "this is the newest pair is not determined (D3)"
        )

    def _do_expect_found_offset(self, step: Step) -> None:
        """The previous ``cyanrip -f`` found the offset this drive is set to."""
        if "-f" not in self._last_cyanrip_argv:
            self._record(
                step,
                Outcome.ERROR,
                "the previous cyanrip step was not `cyanrip -f`, so there is no "
                "offset search to grade",
            )
            return
        found = probe_grading.parse_found_offset(self._last_cyanrip_output)
        grade = probe_grading.grade_found_offset(found, self._drive_offset)
        self._record(step, Outcome.PASS if grade.passed else Outcome.FAIL, grade.detail)

    def _do_cache_probe(self, step: Step) -> None:
        """``cd-paranoia -A`` on the selected drive: gathered, never asserted.

        INFO whatever it says, running out of time included. It is here so a run
        measures the cache both ways, beside cyanrip's own probe in section P,
        and the fork's cache fix is to be measured against it (their round 30
        lap 3 S25). Its whole output goes to the run folder, because a figure
        without the text it was read from cannot be checked.

        **Refused while a rip reads the disc**, for the reason the ``cyanrip``
        verb refuses: two readers on one drive, and the rip is the one harmed.
        **A wait that ends without the answer kills the child** (the runner's
        ``_deadline_cancel``), so a stopped run does not leave cd-paranoia
        seeking for up to ten more minutes.
        """
        from platterpus.adapters import cache_probe

        if getattr(self._window, "_rip_worker", None) is not None:
            self._record(
                step,
                Outcome.FAIL,
                "refusing to probe the cache while a rip is READING THE DISC: two "
                "readers on one drive. Put a `wait-for-rip` before this step.",
            )
            return
        picker = getattr(self._window, "_drive_picker", None)
        device = picker.current_device() if picker is not None else None
        if not device:
            self._record(step, Outcome.ERROR, "no drive is selected to probe")
            return
        job = _start(lambda: cache_probe.probe_cache_defeat(device), "cache-probe")
        started = time.monotonic()

        def answered() -> bool:
            if not job.done.is_set():
                if time.monotonic() - started < CACHE_PROBE_WAIT_S:
                    return False
                # Out of time. INFO, not the runner's FAIL: this step gathers,
                # and a probe that could not finish is a measurement not taken.
                cache_probe.cancel_active_probe()
                self._deadline_outcome = Outcome.INFO
                self._deadline_detail = (
                    f"cd-paranoia -A did not answer within {CACHE_PROBE_WAIT_S:.0f}s "
                    "and was killed; not determined, which is not a pass"
                )
                return True
            result = job.value
            self._deadline_outcome = Outcome.INFO
            if job.error or not isinstance(result, cache_probe.CacheProbeResult):
                self._deadline_detail = (
                    f"cd-paranoia -A could not run ({job.error or 'no answer'}); "
                    "not determined, which is not a pass"
                )
                return True
            detail = _describe_cache(result, cache_probe.describe(result))
            directory = self._ensure_artifact_dir()
            if directory is not None:
                name = f"cacheprobe{step.line_no:04d}.txt"
                # Screened, as all dependency output we store is: a control
                # character becomes a visible escape rather than vanishing.
                text = inbound_text.screen_text(result.raw_output).text
                try:
                    (directory / name).write_text(text, encoding="utf-8")
                except OSError as exc:
                    log.error("cannot write %s: %r", name, exc)
                    detail += f"; its output could not be saved ({exc!r})"
                else:
                    detail += f"; output in {name}"
            self._deadline_detail = detail
            return True

        # The runner's own deadline is the backstop behind `answered`'s, and
        # should never be the one that fires.
        self._arm_deadline(step, CACHE_PROBE_WAIT_S + 30.0, answered)
        self._deadline_cancel = cache_probe.cancel_active_probe
        self._deadline_timeout_detail = (
            f"cd-paranoia -A did not answer within {CACHE_PROBE_WAIT_S + 30.0:.0f}s; "
            "not determined, which is not a pass"
        )


def _describe_cache(result: object, why_unknown: str) -> str:
    """One transcript line for a cache probe, figures first."""
    sectors = getattr(result, "cache_sectors", None)
    defeat = getattr(result, "defeat", None)
    exit_code = getattr(result, "exit_code", None)
    size = f"{sectors} sectors" if sectors is not None else "no size reported"
    verdict = {True: "defeated", False: "NOT defeated", None: "not determined"}[defeat]
    line = f"cd-paranoia -A: cache {size}, {verdict}, exit {exit_code}"
    return f"{line} ({why_unknown})" if why_unknown else line
