"""Verbs for what a person does with the window's own controls (review C9).

The review of the 2026-11-03 Full run listed features a user reaches on one
drive that no acceptance step exercised. Most are reachable with verbs that
already existed (``open settings``, ``ok``, ``answer-dialog click=replace``,
``cancel-rip``); three things a script could not yet *assert* are here:

* ``expect-config-saved [seconds]`` — the settings file on disk holds exactly
  the running app's settings, read back without side effects. With ``seconds``
  the file must also have been written within that many seconds, so a
  ``set`` (which saves) a few seconds before ``open settings`` / ``ok`` leaves
  the Settings dialog's OK as the only thing that can have written it.
* ``expect-no-rip`` — no rip is running. After answering the overwrite prompt's
  Cancel, the answer that started nothing must have started nothing.
* ``wait-for-status <seconds> <text>`` — wait until the status line under the
  Overall bar contains ``text``, so a step can act at a phase of a rip (the
  securing pass's ``to secure it``) rather than at a guessed time.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the other
``*_verbs`` modules. Nothing here blocks: the settings file is a small local
file read once, and the wait arms the runner's own deadline.
"""

from __future__ import annotations

import logging
import time
import tomllib
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, Final

from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: The longest `wait-for-status` may wait: a whole-disc securing pass can take an
#: hour, and an unbounded wait is a run that never ends.
MAX_STATUS_WAIT_S: Final[float] = 3 * 3600.0

#: The longest window `expect-config-saved` accepts for "written just now".
MAX_SAVED_WITHIN_S: Final[float] = 600.0


def config_differences(running: dict[str, Any], on_disk: dict[str, Any]) -> list[str]:
    """Each field whose value on disk is not the running one, as a sentence. Pure.

    Only the running app's fields are compared: a key on disk this version does
    not know is a newer version's, kept on purpose (``config._forward_compat_extra``).
    """
    out: list[str] = []
    for field, value in running.items():
        if field not in on_disk:
            out.append(f"{field}: missing from the file (running {value!r})")
        elif on_disk[field] != value:
            out.append(f"{field}: the file holds {on_disk[field]!r}, running {value!r}")
    return out


def status_text(window: object) -> str | None:
    """The rip status line under the Overall bar, or ``None`` with no such line.

    The same surface ``expect-status`` and the desktop notification read
    (``RipProgress.current_status``), so the three cannot disagree.
    """
    progress = getattr(window, "_rip_progress", None)
    reader = getattr(progress, "current_status", None)
    if not callable(reader):
        return None
    return str(reader() or "")


class ControlVerbsMixin:
    """The C9 handlers. Type-only declarations of the runner surface they use."""

    if TYPE_CHECKING:
        _window: QWidget
        _deadline_outcome: Outcome
        _deadline_detail: str
        _deadline_timeout_detail: str

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

    def _do_expect_config_saved(self, step: Step) -> None:
        """``expect-config-saved [seconds]``: the file on disk is the running config."""
        # The path `config.save` writes, which `config` takes from `paths`.
        from platterpus import paths

        within: float | None = None
        if step.args:
            try:
                within = float(step.args[0])
            except ValueError:
                self._record(step, Outcome.ERROR, f"{step.args[0]!r} is not a number")
                return
            if not 0 < within <= MAX_SAVED_WITHIN_S:
                self._record(
                    step,
                    Outcome.ERROR,
                    f"{within:g} s is outside 0 to {MAX_SAVED_WITHIN_S:.0f} s",
                )
                return
        running = getattr(self._window, "_config", None)
        if running is None or not is_dataclass(running) or isinstance(running, type):
            self._record(step, Outcome.ERROR, "the window has no settings to compare")
            return
        path = paths.CONFIG_PATH
        # Read with tomllib, NOT `config.load()`: load() writes a defaults file
        # when there is none and backs up one it cannot parse, so reading through
        # it could repair the very thing this step is checking.
        try:
            age = time.time() - path.stat().st_mtime
            with path.open("rb") as handle:
                on_disk = tomllib.load(handle)
        except FileNotFoundError:
            self._record(step, Outcome.FAIL, f"there is no settings file at {path}")
            return
        except (OSError, tomllib.TOMLDecodeError) as exc:
            self._record(
                step, Outcome.FAIL, f"the settings file {path} cannot be read: {exc}"
            )
            return
        differences = config_differences(asdict(running), on_disk)
        written = f"written {age:.1f} s ago"
        if differences:
            self._record(
                step,
                Outcome.FAIL,
                f"the settings file {path} ({written}) is not what the app is "
                "running:\n  " + "\n  ".join(differences),
            )
            return
        if within is not None and not 0 <= age <= within:
            self._record(
                step,
                Outcome.FAIL,
                f"the settings file {path} holds the running settings but was "
                f"{written}, not within the last {within:g} s, so the step before "
                "this one did not save it",
            )
            return
        self._record(
            step,
            Outcome.PASS,
            f"the settings file {path} holds every running setting ({written})",
        )

    def _do_expect_no_rip(self, step: Step) -> None:
        """``expect-no-rip``: the window holds no rip worker."""
        worker = getattr(self._window, "_rip_worker", None)
        if worker is None:
            self._record(step, Outcome.PASS, "no rip is running")
            return
        self._record(
            step,
            Outcome.FAIL,
            "a rip is running: the answer before this step was meant to start nothing",
        )

    def _do_wait_for_status(self, step: Step) -> None:
        """``wait-for-status <seconds> <text>``: until the status line contains it."""
        try:
            seconds = float(step.args[0])
        except ValueError:
            self._record(step, Outcome.ERROR, f"{step.args[0]!r} is not a number")
            return
        if not 0 < seconds <= MAX_STATUS_WAIT_S:
            self._record(
                step,
                Outcome.ERROR,
                f"{seconds:g} s is outside 0 to {MAX_STATUS_WAIT_S:.0f} s",
            )
            return
        wanted = " ".join(step.args[1:]).strip()
        if status_text(self._window) is None:
            self._record(
                step, Outcome.ERROR, "no rip-progress status line on the window to read"
            )
            return
        # A rip running when the step starts is one it watches from the start.
        seen_running: list[bool] = [
            getattr(self._window, "_rip_worker", None) is not None
        ]

        def reached() -> bool:
            actual = status_text(self._window) or ""
            running = getattr(self._window, "_rip_worker", None) is not None
            seen_running[0] = seen_running[0] or running
            if wanted.casefold() in actual.casefold():
                self._deadline_detail = f"the status line reads {actual!r}"
                return True
            self._deadline_timeout_detail = (
                f"waited {seconds:g} s and the status line never contained "
                f"{wanted!r}; it reads {actual!r}"
            )
            if seen_running[0] and not running:
                # The rip this step watched has ended without the status ever
                # reading it: waiting on would only run the clock out on a
                # question already answered.
                self._deadline_outcome = Outcome.FAIL
                self._deadline_detail = (
                    f"the rip ended and the status line never contained "
                    f"{wanted!r}; it reads {actual!r}"
                )
                return True
            return False

        self._arm_deadline(step, seconds, reached)
        # Set after arming, which resets it; each poll replaces it with the line
        # as it last read, so a timeout says what the status did say.
        self._deadline_timeout_detail = (
            f"waited {seconds:g} s and the status line never contained {wanted!r}"
        )
