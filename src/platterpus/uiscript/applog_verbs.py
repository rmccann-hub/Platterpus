"""Two verbs that read this launch's own log, for checks only a drive can settle.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the
other ``*_verbs`` modules, so the runner file does not grow.

**Why.** Several open TASKS rows are settled only by what the app logged during
a drive run, and the closing Full run is the next drive run (TASKS *"Fold the
hardware-only checks into the closing run"*, 2026-10-05). A row a person must
close by reading a multi-megabyte log is a row nobody closes, so the run reads
the log itself and puts the answer in its transcript:

* ``app-log <text>`` — every line this launch logged that contains the text,
  as INFO. Section A uses it for *"Cold-container start"*: the first container
  command runs alone (``container_gate.FIRST_ENTRY``), and a probe that waited
  for it logs a line saying so.
* ``sigterm-world`` — after a ``cancel-rip``, which world the rig is in: does a
  cancel's SIGTERM reach the ripper inside the container, or only the host
  wrapper? (TASKS *"If a podman ever forwards the wrapper's SIGTERM"*.) Read
  from the post-cancel rescue's outcome in the log and the cancelled rip's log
  footer: see :func:`sigterm_world`.

Both GATHER (``INFO``) and never fail a run: they measure what a rig does, which
is not a verdict about the program. **Tri-state**, as everywhere here: a log that
did not keep the line, or a rescue that logged no outcome, is *not determined*,
never the answer either way. They read the in-memory session log
(``log_buffer``), which holds every line since launch, head and tail, and every
answer says how much of the launch it could see. A list copy and a substring scan
over at most 50,000 strings: milliseconds, on the GUI thread like ``snapshot``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

#: How many matching lines ``app-log`` copies into the transcript: the first and
#: the last halves, with what was left out counted between them.
APP_LOG_LINES_SHOWN: Final[int] = 12

#: The line ``RipMixin._on_rip_cancel`` logs when Cancel is pressed. Only lines
#: after the LAST one belong to the cancel ``sigterm-world`` is asked about.
CANCEL_MARK: Final[str] = "rip cancel requested by the user"

#: The rescue's own line (``RipMixin._auto_force_stop``), then the outcome
#: ``drive_control.term_unsignalled_holders`` logs from its thread.
RESCUE_MARK: Final[str] = "post-cancel rescue: device-scoped SIGTERM"
_FUSER_TERM: Final[re.Pattern[str]] = re.compile(r"fuser -k TERM \S+ rc=(?P<rc>\S+)")

#: The rescue outcomes :func:`rescue_outcome` names.
SIGNALLED: Final[str] = "signalled"
NOTHING_HELD: Final[str] = "nothing held it"
REFUSED: Final[str] = "refused"
NOT_LOGGED: Final[str] = "fired, outcome not logged"
NO_RESCUE: Final[str] = "no rescue"


def matching_lines(lines: list[str], needle: str) -> list[str]:
    """The lines containing ``needle`` (case-insensitive), head and tail kept.

    Bounded at :data:`APP_LOG_LINES_SHOWN`, with the elision counted in place:
    a silent cut would read as the whole answer.
    """
    folded = needle.casefold()
    hits = [line for line in lines if folded in line.casefold()]
    if len(hits) <= APP_LOG_LINES_SHOWN:
        return hits
    half = APP_LOG_LINES_SHOWN // 2
    return [*hits[:half], f"… [{len(hits) - 2 * half} more line(s)] …", *hits[-half:]]


def lines_after_last(lines: list[str], mark: str) -> list[str] | None:
    """The lines after the last one containing ``mark``; ``None`` if none does."""
    for index in range(len(lines) - 1, -1, -1):
        if mark in lines[index]:
            return lines[index + 1 :]
    return None


def rescue_outcome(after_cancel: list[str]) -> str:
    """What the post-cancel rescue did, read from the lines after the cancel.

    ``signalled`` when it SIGTERMed a holder (``fuser`` exit 0, or a ``SIGTERM
    sent to pid`` line); ``refused`` when the holder was the process the cancel
    itself had signalled (a native ripper, not the container path);
    ``nothing held it`` when the drive was already free; otherwise
    :data:`NOT_LOGGED` or :data:`NO_RESCUE`, both of which decide nothing.
    """
    if not any(RESCUE_MARK in line for line in after_cancel):
        return NO_RESCUE
    codes = [m.group("rc") for line in after_cancel if (m := _FUSER_TERM.search(line))]
    if "0" in codes or any("SIGTERM sent to pid" in line for line in after_cancel):
        return SIGNALLED
    if any("not signalling pid" in line for line in after_cancel):
        return REFUSED
    if "1" in codes or any(
        "so no process was signalled" in line for line in after_cancel
    ):
        return NOTHING_HELD
    return NOT_LOGGED


def sigterm_world(rescue: str, footer: bool | None) -> str:
    """Which SIGTERM world the rig is in, from the rescue and the log's footer.

    Behind the Distrobox wrapper, Cancel SIGTERMs the wrapper's process group.
    If podman does NOT forward it, the ripper hears nothing until the rescue's
    device-scoped SIGTERM 5 s later: the rescue finds it holding the drive, and
    the log is signed after that, its first signal. If podman DOES forward it,
    the ripper heard the cancel already: on a short read it has let go before the
    rescue fires; on a read longer than 5 s the rescue's SIGTERM is its second,
    and cyanrip ``_exit``s without its footer (``cyanrip@174a134:
    src/cyanrip_main.c`` ``on_quit_signal``; ``drive_control``'s docstring).
    """
    if footer is None:
        return (
            "NOT DETERMINED: the cancelled rip's log could not be read from disk, "
            "so whether it was signed is unknown"
        )
    if rescue == SIGNALLED and footer:
        return (
            "ONE SIGNAL (podman does not forward the wrapper's SIGTERM): the ripper "
            "still held the drive when the rescue fired 5 s after Cancel, and signed "
            "its log after the rescue's SIGTERM, so that was its first"
        )
    if rescue == SIGNALLED:
        return (
            "SECOND SIGNAL, the hazard: the ripper held the drive when the rescue "
            "fired and its log has no footer, which is what a forwarded SIGTERM "
            "followed by the rescue's looks like"
        )
    if rescue == NOTHING_HELD:
        return (
            "FORWARDED, probably: the ripper had let go of the drive before the "
            "rescue fired 5 s after Cancel, so something stopped it sooner: podman "
            "forwarding the cancel's SIGTERM, or the rip ending on its own. The read "
            "was short enough that the rescue was no second signal"
        )
    if rescue == REFUSED:
        return (
            "NOT THE CONTAINER PATH: the process holding the drive was the one the "
            "cancel signalled itself (a native cyanrip), so the rescue left it alone"
        )
    return (
        f"NOT DETERMINED: the rescue's outcome is not in this launch's log ({rescue})"
    )


class AppLogVerbsMixin:
    """The ``app-log`` and ``sigterm-world`` handlers. Type-only declarations of
    the runner surface they use."""

    if TYPE_CHECKING:
        _window: QWidget

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

    def _session_log(self) -> tuple[list[str] | None, str]:
        """This launch's log lines, and a sentence on how much of it was kept."""
        from platterpus import log_buffer

        buffer = log_buffer.get_session_buffer()
        if buffer is None:
            return None, "no in-memory log is installed, so this launch's log is unread"
        snap = buffer.snapshot_excluding([])
        kept = f"{snap.received} line(s) logged since launch"
        if snap.dropped:
            kept += (
                f"; {snap.dropped} dropped between {snap.dropped_between}, so an "
                "absence from that span is not evidence"
            )
        return snap.lines, kept + ", every other line kept"

    def _do_app_log(self, step: Step) -> None:
        """``app-log <text>``: what this launch logged about it. INFO."""
        needle = step.joined().strip()
        lines, kept = self._session_log()
        if lines is None:
            self._record(step, Outcome.INFO, f"not determined: {kept}")
            return
        hits = matching_lines(lines, needle)
        if not hits:
            self._record(
                step,
                Outcome.INFO,
                f"no line of this launch's log contains {needle!r} ({kept})",
            )
            return
        self._record(
            step,
            Outcome.INFO,
            f"lines containing {needle!r} ({kept}):\n" + "\n".join(hits),
        )

    def _do_sigterm_world(self, step: Step) -> None:
        """``sigterm-world``: which world the last cancel showed. INFO."""
        lines, kept = self._session_log()
        if lines is None:
            self._record(step, Outcome.INFO, f"NOT DETERMINED: {kept}")
            return
        after = lines_after_last(lines, CANCEL_MARK)
        if after is None:
            self._record(
                step,
                Outcome.INFO,
                f"NOT DETERMINED: no cancel is in this launch's log ({kept}); put "
                "this after a `cancel-rip` and the wait for its log",
            )
            return
        rescue = rescue_outcome(after)
        evidence = matching_lines(after, RESCUE_MARK) + [
            line
            for line in after
            if _FUSER_TERM.search(line)
            or "SIGTERM sent to pid" in line
            or "not signalling pid" in line
            or "so no process was signalled" in line
        ]
        world = sigterm_world(rescue, self._cancelled_log_signed())
        self._record(
            step,
            Outcome.INFO,
            f"{world}. Rescue: {rescue}.\n" + "\n".join(evidence[:APP_LOG_LINES_SHOWN]),
        )

    def _cancelled_log_signed(self) -> bool | None:
        """Whether the last rip's log on disk carries its completion footer.

        ``None`` when it cannot be read, or when no rip has finished since the
        section's ``rip`` (the same freshness rule the log verbs keep). Read
        without recording anything: this verb gathers, and a FAIL from the
        shared reader would grade what it only measures.
        """
        from platterpus.parsers.rip_log import RipLog

        window = self._window
        parsed = getattr(window, "_last_rip_log", None)
        if parsed is getattr(self, "_rip_log_when_requested", None):
            return None
        log_file = getattr(window, "_last_rip_log_file", None)
        reparse = getattr(window, "parse_rip_log_from_disk", None)
        if not isinstance(parsed, RipLog) or log_file is None or reparse is None:
            return None
        try:
            fresh = reparse(log_file)
        except (OSError, ValueError):
            return None
        if not isinstance(fresh, RipLog):
            return None
        return fresh.rip_completed is not None
