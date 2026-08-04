# SPDX-License-Identifier: GPL-3.0-only
"""One place that answers *"did anything go wrong, and what?"*.

**Why this module exists (maintainer directive, 2026-08-04).** *"I want full error
and reporting to the output log file (JSON) as possible for future debugging. Be
thorough and verbose; make finding errors easy."*

Before this, the answer to *"did anything go wrong in this rip?"* was: read the
whole report and infer it. Diagnostics were scattered across a dozen blocks —
`outcome.failure_hint`, `log_parse.note`, `ctdb.error`, per-track `issues`,
`verification.*` — each shaped differently, each optional, and several of them
carrying `None` for both *"fine"* and *"never measured"*. Nothing enumerated them.
A reader had to already know where to look, which is the opposite of what a
debugging artifact is for.

This is that enumeration. Every subsystem records its problems here; the report
carries them as one ordered list plus a count, so the first question a support
thread asks has a single answer.

## The four rules this module encodes

1. **Recording a diagnostic ALSO logs it.** Not "and remember to log too" — the
   recorder does it, so the log file and the JSON cannot disagree about what
   happened. Two independent descriptions of one event is the drift this project
   keeps paying for; there is one call site and it feeds both.

2. **Never raises.** A recorder that throws while recording an error destroys the
   evidence for the failure it was called about, and turns a diagnosable problem
   into a crash. Every public entry point here is defensive to the point of
   paranoia, including against un-stringifiable objects.

3. **Bounded, with the truncation *stated*.** A pathological rip could record
   thousands of items. The list is capped, and when it is, the block says so and
   counts what was dropped — because a silent truncation reads as completeness
   (CLAUDE.md, diagnostic completeness).

4. **Tri-state everywhere it matters.** `exit_code=None` means *the child was
   never reaped* and is a real answer, distinct from `0`. Same discipline as
   `rip_report`: absence of evidence never renders as a negative.

## What a `code` is for

`Diagnostic.code` is a stable, machine-greppable key — `ripper.nonzero_exit`,
`transcode.ffmpeg_failed`, `ctdb.http_error`. The **message** is for a person and
may be reworded freely; the **code** is a contract, so a future bug report can say
"seven `ripper.stall_detected` in one rip" without anyone parsing prose. Codes are
namespaced `subsystem.what` and listed in :data:`KNOWN_CODES` so a typo is
catchable rather than silently minting a new category.
"""

from __future__ import annotations

import logging
import threading
import traceback
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from platterpus.paths import LOG_PATH

log = logging.getLogger(__name__)

# --- Severity ---------------------------------------------------------------
#
# Strings rather than an enum so they cross the JSON boundary unchanged and read
# the same in the log, the report and a bug report — the same reasoning as
# `handshake_approval`'s verdicts.

#: Something the user experienced as a failure, or that invalidates a claim.
ERROR: Final[str] = "error"
#: Something degraded, was skipped, or could not be measured. The rip may be fine.
WARNING: Final[str] = "warning"
#: Notable but not a problem — kept because "why did it choose that?" is a real
#: debugging question and the answer is usually an info-level decision.
INFO: Final[str] = "info"

SEVERITIES: Final[tuple[str, ...]] = (ERROR, WARNING, INFO)

#: Rank for sorting/severity comparison. Lower is worse, so `min` is "the worst".
_SEVERITY_RANK: Final[dict[str, int]] = {ERROR: 0, WARNING: 1, INFO: 2}

# --- Codes ------------------------------------------------------------------
#
# The stable machine keys. Grouped by subsystem, and deliberately explicit rather
# than free-form: a typo in a free-form code silently creates a new category that
# no aggregation will ever find, which is the "can this check be satisfied by
# finding nothing" trap applied to telemetry.
#
# ADDING ONE IS FINE — add it here and it is legal. The point is that adding one
# is a *decision* rather than an accident.
KNOWN_CODES: Final[frozenset[str]] = frozenset(
    {
        # The ripper (cyanrip). The seam that matters most.
        "ripper.nonzero_exit",
        "ripper.unreapable_child",
        "ripper.fatal_message",
        "ripper.stall_detected",
        "ripper.no_banner",
        "ripper.unapproved_build",
        "ripper.argv_mismatch",
        "ripper.logfile_missing",
        "ripper.logfile_truncated",
        "ripper.parse_degraded",
        "ripper.cancelled",
        # Post-rip verification and derived outputs.
        "flac.verify_failed",
        "flac.recompress_failed",
        "transcode.failed",
        "checksum.mismatch",
        # Network-backed lookups. All optional; all must fail visibly.
        "musicbrainz.lookup_failed",
        "coverart.fetch_failed",
        "accuraterip.query_failed",
        "ctdb.query_failed",
        "ctdb.crc_mismatch",
        # Environment / dependency subsystem.
        "deps.missing",
        "deps.version_unreadable",
        "deps.command_failed",
        "setup.step_failed",
        # Our own plumbing. An internal error is still the user's problem.
        "config.invalid_value",
        "report.build_degraded",
        "internal.unexpected_exception",
        "library.move_failed",
        "drive.control_failed",
    }
)

# --- Bounds -----------------------------------------------------------------
#
# A cap, because one pathological rip must not produce an unopenable JSON. Head
# and tail rather than head alone: the last diagnostics are the ones nearest the
# failure, and a head-only cap drops exactly those.
_MAX_ITEMS: Final[int] = 400
_HEAD_ITEMS: Final[int] = 150
_TAIL_ITEMS: Final[int] = 250
#: Per-item detail cap. Generous — a meson failure or a Python traceback is worth
#: keeping whole — but not unbounded, because `detail` can be a tool's entire
#: stdout.
_MAX_DETAIL_CHARS: Final[int] = 20_000


def _safe_str(value: object, limit: int | None = None) -> str:
    """``str(value)`` that cannot raise, optionally length-capped.

    A ``__str__`` that throws is rare and real (a partially-constructed object, a
    C extension mid-teardown). Rule 2 of this module: recording an error must never
    become a second error.
    """
    try:
        text = str(value)
    except Exception:  # noqa: BLE001 — the whole point is that nothing escapes
        try:
            text = f"<unstringifiable {type(value).__name__}>"
        except Exception:  # noqa: BLE001 — even type() can fail on a broken proxy
            text = "<unstringifiable object>"
    if limit is not None and len(text) > limit:
        dropped = len(text) - limit
        # State the truncation inline. An elided detail that does not say it was
        # elided is indistinguishable from a tool that stopped talking.
        text = text[:limit] + f"\n… [{dropped} more character(s) omitted]"
    return text


#: Default line bounds for :func:`bounded_output`. The tail is the larger half on
#: purpose — see the docstring.
OUTPUT_HEAD_LINES: Final[int] = 40
OUTPUT_TAIL_LINES: Final[int] = 60


def bounded_output(
    output: object,
    *,
    head: int = OUTPUT_HEAD_LINES,
    tail: int = OUTPUT_TAIL_LINES,
) -> str:
    """A tool's output capped to a head and a tail, with the gap counted and marked.

    **This lives here, once.** The head-and-tail rule was written three times in
    this codebase (the step engine, the rip worker's stdout capture, and the
    transcode adapter's log tail), each with different limits and one of them
    head-only. Three implementations of one rule is three chances to drop the line
    that explains a failure.

    **Head AND tail, never head alone.** A tool's fatal message is the *last* thing
    it prints, so a head-only cap drops exactly the line a reader needs — while
    still looking like a complete capture. The tail is the larger half for the same
    reason.

    **The marker is load-bearing.** An unmarked jump reads as a command that fell
    silent, which is a different and more alarming fact than "we elided some
    lines". A silent truncation reads as completeness.

    Never raises: takes ``object`` and stringifies defensively, because this runs
    on whatever a dependency handed us.
    """
    text = _safe_str(output) if not isinstance(output, str) else output
    lines = text.rstrip("\n").splitlines()
    if len(lines) <= head + tail:
        return "\n".join(lines)
    elided = len(lines) - head - tail
    return "\n".join(
        [
            *lines[:head],
            f"  … [{elided} line(s) omitted] …",
            *lines[-tail:],
        ]
    )


def _coerce_argv(argv: object) -> tuple[str, ...]:
    """Best-effort argv coercion that accepts whatever a caller actually has.

    Takes ``object`` on purpose: call sites hand this a list, a tuple, a
    `Popen.args` (which may be a bare string), or occasionally something odd. A
    non-iterable is KEPT as a single element rather than discarded — losing the
    command line to a type quibble would defeat the point.
    """
    if not argv:
        return ()
    # `str` first: a string IS iterable, and iterating one would explode a command
    # line into single characters — a silently useless argv is worse than none.
    if isinstance(argv, str):
        return (_safe_str(argv, 4000),)
    # A real narrowing rather than a `type: ignore`. CLAUDE.md rule 10: do not
    # weaken a type to make the checker pass.
    if isinstance(argv, Iterable):
        try:
            return tuple(_safe_str(a, 4000) for a in argv)
        except Exception:  # noqa: BLE001 — a generator that raises mid-iteration
            return (_safe_str(argv, 4000),)
    return (_safe_str(argv, 4000),)


@dataclass(frozen=True)
class Diagnostic:
    """One thing that went wrong, or nearly did, with everything needed to act.

    Frozen because a diagnostic is a record of a moment; mutating one after the
    fact would make the log and the report disagree, which is exactly what this
    module exists to prevent.
    """

    severity: str
    #: Stable machine key — see :data:`KNOWN_CODES`.
    code: str
    #: Which part of the program is speaking. Free-form but conventionally the
    #: `code`'s namespace.
    subsystem: str
    #: One sentence, written for a person.
    message: str
    #: Everything else: a tool's captured output, a traceback, a parsed value that
    #: looked wrong. Empty when there genuinely is no more to say.
    detail: str = ""
    #: The external tool involved, if any. `None` for our own faults — which is
    #: itself useful: it separates "the ripper failed" from "we failed".
    tool: str | None = None
    #: The exact argv as spawned, if any. The single most useful thing for
    #: reproducing a failure by hand.
    argv: tuple[str, ...] = ()
    #: Tri-state. `None` means the child was never reaped — a real outcome, never
    #: to be written as 0.
    exit_code: int | None = None
    #: ISO-8601 UTC. Set by the recorder, not the caller, so ordering is reliable.
    at: str = ""
    #: Where in the program this came from, for a maintainer reading the JSON.
    where: str = ""
    #: The track this concerns, when it is track-scoped. `None` = disc-level.
    track: int | None = None

    def to_json(self) -> dict[str, Any]:
        """The JSON form. Keys are stable; this is a consumed contract."""
        return {
            "severity": self.severity,
            "code": self.code,
            "subsystem": self.subsystem,
            "message": self.message,
            "detail": self.detail or None,
            "tool": self.tool,
            # A list, not a joined string: a reader that wants to re-run this
            # must not have to re-split a quoted command line.
            "argv": list(self.argv) or None,
            "exit_code": self.exit_code,
            "at": self.at or None,
            "where": self.where or None,
            "track": self.track,
        }

    @property
    def is_error(self) -> bool:
        return self.severity == ERROR


@dataclass
class DiagnosticLog:
    """A bounded, thread-safe collection of :class:`Diagnostic`.

    **Thread-safe because rips are not single-threaded.** The rip worker, the
    transcode worker, the CTDB worker and the GUI thread can all record; a plain
    list would drop items under contention and the drop would be invisible.
    """

    _items: list[Diagnostic] = field(default_factory=list)
    _dropped: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # --- Recording ----------------------------------------------------------

    def record(
        self,
        severity: str,
        code: str,
        message: str,
        *,
        subsystem: str = "",
        detail: object = "",
        tool: str | None = None,
        argv: object = (),
        exit_code: int | None = None,
        where: str = "",
        track: int | None = None,
    ) -> Diagnostic | None:
        """Record one diagnostic, log it, and return it.

        Returns ``None`` only if recording itself failed — which is logged and
        never raised. Callers may ignore the return value; it exists for tests and
        for the rare caller that wants to render the same sentence it recorded.

        ``detail`` and ``argv`` take ``object`` deliberately: callers hand this
        whatever a dependency gave them, and coercing defensively here is better
        than every call site remembering to.
        """
        try:
            item = self._build(
                severity=severity,
                code=code,
                message=message,
                subsystem=subsystem,
                detail=detail,
                tool=tool,
                argv=argv,
                exit_code=exit_code,
                where=where,
                track=track,
            )
        except Exception:  # noqa: BLE001 — rule 2: never raise from here
            log.exception("diagnostics: failed to build a diagnostic for %r", code)
            return None

        # LOG IT HERE, not at the call site. One call feeds both sinks, so the log
        # file and the report cannot describe the same event differently.
        try:
            self._emit_to_log(item)
        except Exception:  # noqa: BLE001 — a logging failure must not lose the item
            pass

        try:
            with self._lock:
                if len(self._items) >= _MAX_ITEMS:
                    self._dropped += 1
                    # Keep the head (what happened first, often the root cause) and
                    # slide the tail (what happened last, nearest the failure).
                    del self._items[_HEAD_ITEMS]
                self._items.append(item)
        except Exception:  # noqa: BLE001 — rule 2
            log.exception("diagnostics: failed to store %r", code)
            return None
        return item

    def _build(
        self,
        *,
        severity: str,
        code: str,
        message: str,
        subsystem: str,
        detail: object,
        tool: str | None,
        argv: object,
        exit_code: int | None,
        where: str,
        track: int | None,
    ) -> Diagnostic:
        """Coerce and validate. Split out so `record` stays readable."""
        sev = severity if severity in SEVERITIES else ERROR
        if sev != severity:
            # An unrecognised severity becomes ERROR, not INFO: guessing downward
            # would hide a problem, and this is the wrong place to be optimistic.
            log.warning(
                "diagnostics: unknown severity %r for %r — recording as error",
                severity,
                code,
            )
        code_text = _safe_str(code, 200).strip() or "internal.unexpected_exception"
        if code_text not in KNOWN_CODES:
            # NOT an error, and not silent. An unlisted code still gets recorded —
            # losing a real diagnostic to a taxonomy quibble would be absurd — but
            # the mismatch is logged so the list stays honest.
            log.warning(
                "diagnostics: %r is not in KNOWN_CODES; recording it anyway "
                "(add it to platterpus.diagnostics.KNOWN_CODES)",
                code_text,
            )
        argv_tuple: tuple[str, ...] = _coerce_argv(argv)
        return Diagnostic(
            severity=sev,
            code=code_text,
            subsystem=_safe_str(subsystem, 100).strip() or code_text.split(".")[0],
            message=_safe_str(message, 2000).strip() or f"({code_text}, no message)",
            detail=_safe_str(detail, _MAX_DETAIL_CHARS) if detail else "",
            tool=_safe_str(tool, 100) if tool else None,
            argv=argv_tuple,
            exit_code=exit_code,
            at=datetime.now(UTC).isoformat(timespec="seconds"),
            where=_safe_str(where, 300),
            track=track,
        )

    @staticmethod
    def _emit_to_log(item: Diagnostic) -> None:
        """Mirror a diagnostic into the log file at a level matching its severity.

        The prefix is a fixed, greppable token. *"Make finding errors easy"* is a
        literal instruction: a user can run
        ``grep 'platterpus-diagnostic' ~/.local/share/platterpus/log.txt``
        and see every problem the program noticed, in order, without knowing any
        of the subsystem names.
        """
        level = {ERROR: logging.ERROR, WARNING: logging.WARNING}.get(
            item.severity, logging.INFO
        )
        parts = [f"platterpus-diagnostic [{item.severity}] {item.code}: {item.message}"]
        if item.tool:
            parts.append(f"  tool: {item.tool}")
        if item.exit_code is not None:
            parts.append(f"  exit code: {item.exit_code}")
        elif item.argv:
            # Say it explicitly — "no exit code" and "exit code 0" are different
            # facts and the log must not let them look the same.
            #
            # Gated on `argv`, NOT on `tool`: a tool with no argv was never a child
            # process (an HTTP lookup like CTDB or MusicBrainz names a `tool` but
            # spawns nothing), and telling the reader its child "was never reaped"
            # would be a confident, wrong explanation. Caught by reading this
            # module's own first output — the same accurate-but-misleading shape
            # this whole subsystem exists to eliminate.
            parts.append("  exit code: none (no child was reaped)")
        if item.argv:
            parts.append(f"  argv: {' '.join(item.argv)}")
        if item.track is not None:
            parts.append(f"  track: {item.track}")
        if item.where:
            parts.append(f"  where: {item.where}")
        if item.detail:
            parts.append(f"  detail:\n{item.detail}")
        log.log(level, "\n".join(parts))

    # --- Convenience --------------------------------------------------------

    def error(self, code: str, message: str, **kw: Any) -> Diagnostic | None:
        return self.record(ERROR, code, message, **kw)

    def warning(self, code: str, message: str, **kw: Any) -> Diagnostic | None:
        return self.record(WARNING, code, message, **kw)

    def info(self, code: str, message: str, **kw: Any) -> Diagnostic | None:
        return self.record(INFO, code, message, **kw)

    def exception(
        self, code: str, message: str, exc: BaseException, **kw: Any
    ) -> Diagnostic | None:
        """Record an unexpected exception **with its traceback** in ``detail``.

        The traceback is the point. A caught-and-summarised exception loses the
        line that raised it, which is the only part that locates the bug.
        """
        try:
            tb = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ).rstrip()
        except Exception:  # noqa: BLE001 — rule 2
            tb = f"{type(exc).__name__}: {_safe_str(exc)}"
        existing = _safe_str(kw.pop("detail", ""))
        detail = f"{existing}\n{tb}".strip() if existing else tb
        return self.record(ERROR, code, message, detail=detail, **kw)

    # --- Reading ------------------------------------------------------------

    def items(self) -> tuple[Diagnostic, ...]:
        with self._lock:
            return tuple(self._items)

    def count(self, severity: str | None = None) -> int:
        with self._lock:
            if severity is None:
                return len(self._items)
            return sum(1 for i in self._items if i.severity == severity)

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._dropped

    def worst_severity(self) -> str | None:
        """The most severe severity present, or ``None`` when nothing was recorded."""
        recorded = self.items()
        if not recorded:
            return None
        return min(recorded, key=lambda i: _SEVERITY_RANK.get(i.severity, 99)).severity

    def codes(self) -> tuple[str, ...]:
        """Every distinct code, in first-seen order.

        The at-a-glance summary: a reader can tell *what kinds* of thing went wrong
        before reading a single message.
        """
        seen: dict[str, None] = {}
        for item in self.items():
            seen.setdefault(item.code, None)
        return tuple(seen)

    def clear(self) -> None:
        """Reset. Used between rips, and by tests."""
        with self._lock:
            self._items.clear()
            self._dropped = 0

    # --- Report block -------------------------------------------------------

    def to_report_block(self) -> dict[str, Any]:
        """The `diagnostics` block for the rip report JSON.

        Deliberately answers the question *before* the detail: `error_count` and
        `codes` are readable at a glance, and `items` is there when someone needs
        the whole story. A reader who only ever looks at `error_count` still learns
        the thing that matters.
        """
        recorded = self.items()
        dropped = self.dropped
        return {
            "error_count": sum(1 for i in recorded if i.severity == ERROR),
            "warning_count": sum(1 for i in recorded if i.severity == WARNING),
            "info_count": sum(1 for i in recorded if i.severity == INFO),
            "worst_severity": self.worst_severity(),
            "codes": list(self.codes()),
            # SAY WHAT PERIOD THIS COVERS. The collector is process-wide, so a
            # setup failure from earlier in the same session appears in a later
            # rip's report. That is deliberate and useful — "the fork build failed
            # an hour ago" explains an unapproved ripper — but a reader who assumes
            # the block is rip-scoped would misattribute it. Absent a stated scope,
            # they would have no way to know.
            "scope": "process session (not only this rip)",
            # Stated, not implied. A capped list that does not say it was capped
            # reads as the complete set.
            "truncated": dropped > 0,
            "dropped_count": dropped,
            # The REAL path, resolved through `paths.LOG_PATH`, not the `~/.local/
            # share/...` literal it used to name. That literal is wrong under a
            # custom `XDG_DATA_HOME`, a Flatpak sandbox, or any other relocation —
            # and a hint that points at a file the user does not have is worse than
            # no hint, because they conclude the log does not exist.
            "log_grep_hint": f"grep 'platterpus-diagnostic' {LOG_PATH}",
            "items": [i.to_json() for i in recorded],
        }


#: The process-wide collector. A module global because diagnostics arrive from
#: workers that have no reference to the report builder — threading one through
#: every layer would mean the layers that most need to report (a deep parser, a
#: dependency probe) are the ones least able to.
_DEFAULT: Final[DiagnosticLog] = DiagnosticLog()


def default_log() -> DiagnosticLog:
    """The process-wide collector."""
    return _DEFAULT


def record(severity: str, code: str, message: str, **kw: Any) -> Diagnostic | None:
    """Record on the process-wide collector. The usual entry point."""
    return _DEFAULT.record(severity, code, message, **kw)


def error(code: str, message: str, **kw: Any) -> Diagnostic | None:
    return _DEFAULT.error(code, message, **kw)


def warning(code: str, message: str, **kw: Any) -> Diagnostic | None:
    return _DEFAULT.warning(code, message, **kw)


def info(code: str, message: str, **kw: Any) -> Diagnostic | None:
    return _DEFAULT.info(code, message, **kw)


def exception(
    code: str, message: str, exc: BaseException, **kw: Any
) -> Diagnostic | None:
    return _DEFAULT.exception(code, message, exc, **kw)


def record_command_failure(
    code: str,
    tool: str,
    argv: object,
    exit_code: int | None,
    output: object,
    *,
    message: str = "",
    where: str = "",
    severity: str = ERROR,
) -> Diagnostic | None:
    """The shape almost every external-tool failure wants.

    One call records the four things CLAUDE.md's diagnostic-completeness rule
    demands for a dependency: **exit code** (tri-state), **exact argv**, **complete
    output**, and a sentence a person can read. Having a single helper is the point
    — a per-call-site hand-rolled version is how the four drift to three.
    """
    tool_name = _safe_str(tool, 100)
    if not message:
        code_part = (
            f"exit {exit_code}"
            if exit_code is not None
            else "no exit status (unreaped)"
        )
        message = f"{tool_name} failed ({code_part})"
    return _DEFAULT.record(
        severity,
        code,
        message,
        tool=tool_name,
        argv=argv,
        exit_code=exit_code,
        detail=output,
        where=where,
    )


def to_report_block() -> dict[str, Any]:
    """The process-wide collector's report block."""
    return _DEFAULT.to_report_block()


def clear() -> None:
    """Reset the process-wide collector (between rips, and in tests)."""
    _DEFAULT.clear()


__all__ = [
    "ERROR",
    "INFO",
    "KNOWN_CODES",
    "SEVERITIES",
    "WARNING",
    "Diagnostic",
    "DiagnosticLog",
    "clear",
    "default_log",
    "error",
    "exception",
    "info",
    "record",
    "record_command_failure",
    "to_report_block",
    "warning",
]
