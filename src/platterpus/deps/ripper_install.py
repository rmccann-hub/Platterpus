"""Install one fork build of cyanrip: the ONE function behind ``--install-ripper``
and the ``install-ripper`` script verb.

**Why this module exists.** ``platterpus --install-ripper <commit>`` (KDD-34) was
written inline in ``app.main``: resolve a target, print what it is, drive the
setup wizard's step engine (:class:`~platterpus.deps.host_setup.HostSetup`), and
report against "is the ripper usable". The acceptance run then needed the same
thing from a script — the owner's timed rip compares two fork builds, so the run
has to switch the installed ripper between them (the fork's round 36 lap 1 S15).
``CLAUDE.md`` is explicit that a verb and a CLI flag doing one job are **two thin
callers of one function, never two implementations**. So the work moved here,
and both callers delegate:

* the CLI (``app.main``) prints what this returns;
* the script verb (``uiscript/install_verbs.py``) runs it on a daemon thread and
  writes it into the transcript.

**The step engine is not copied.** :func:`run_install` constructs the same
``HostSetup`` the wizard and the CLI always have; Critical rule #6 puts every
dependency install in that one subsystem, and Critical rule #3's routing (the
host-exported ``~/.local/bin/cyanrip`` entering the ``ripping`` container) is
what that engine builds and re-exports. Nothing here spawns a process itself.

**Nothing here prints and nothing here touches Qt.** It returns text and data,
so the CLI can print it and a worker thread can carry it to the GUI thread. That
is also why the progress callback is the caller's: on the CLI it prints, in the
verb it appends to a list the tick reads.

**Cancellation is honoured between steps, by design.** The engine polls
``cancelled()`` before each step. A step in flight — a ``dnf install``, a
``meson``/``ninja`` build, a ``sudo install`` of the binary — runs to its end
(bounded by the engine's per-command timeout), because killing a half-done
package install or a half-copied binary leaves the host worse off than waiting.
That is the same documented boundary as ``HostSetupWorker``'s allowlisted
flag-only cancel (``tests/test_qthread_ownership.py``), stated here so the script
verb does not promise more than the engine keeps.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from platterpus.deps.step_engine import (
    CommandRunner,
    StepResult,
    StepStatus,
    console_argv,
    one_line_argv,
)

if TYPE_CHECKING:  # pragma: no cover — types only
    from pathlib import Path

    from platterpus.deps.fork_source import ForkTarget

log = logging.getLogger(__name__)

#: The mark each step status gets on its progress line. One table, so the CLI's
#: terminal rows and the script verb's transcript rows cannot spell a status two
#: ways. Moved here verbatim from ``app.main``.
_MARK: Final[dict[StepStatus, str]] = {
    StepStatus.DONE: "  ok  ",
    StepStatus.RAN: " done ",
    StepStatus.FAILED: " FAIL ",
    StepStatus.WOULD_RUN: " plan ",
    StepStatus.CANCELLED: "  --  ",
    StepStatus.RUNNING: "  ..  ",
}

#: How much of one command's output a :class:`RecordedCommand` keeps: a head and a
#: tail, with the gap counted. A ``dnf install`` can print thousands of lines;
#: the log file keeps the engine's own bounded copy as well.
_RECORD_HEAD_LINES: Final[int] = 20
_RECORD_TAIL_LINES: Final[int] = 40


def step_line(result: StepResult) -> str:
    """One progress row: ``[ done ] Build cyanrip fork — <detail>``."""
    line = f"[{_MARK[result.status]}] {result.title}"
    if result.detail:
        line += f" — {result.detail}"
    return line


def _head_and_tail(text: str) -> str:
    """``text`` bounded to a head and a tail, the elision counted and marked.

    Head AND tail, never head alone: a tool's fatal message is the last thing it
    prints, so a head-only cap drops the one line that explains the failure while
    still looking complete (``CLAUDE.md``, diagnostic completeness).
    """
    lines = text.rstrip("\n").splitlines()
    if len(lines) <= _RECORD_HEAD_LINES + _RECORD_TAIL_LINES:
        return "\n".join(lines)
    elided = len(lines) - _RECORD_HEAD_LINES - _RECORD_TAIL_LINES
    return "\n".join(
        [
            *lines[:_RECORD_HEAD_LINES],
            f"  … [{elided} line(s) omitted; the log file has the engine's copy] …",
            *lines[-_RECORD_TAIL_LINES:],
        ]
    )


@dataclass(frozen=True)
class RecordedCommand:
    """One command the engine ran: the exact argv, its exit code, its output.

    The trio ``CLAUDE.md``'s diagnostic-completeness rule asks for, kept per
    command so a script's transcript can show which command failed without the
    reader opening the log. ``argv`` is the exact list the runner was handed,
    rendered on one line by the engine's own :func:`one_line_argv` (lossless:
    newlines in an ``sh -c`` script become ``\\n``).
    """

    argv: str
    #: The short form for a transcript row, from :func:`console_argv`.
    argv_short: str
    #: The child's exit code as the runner reported it (127 not found, 124 timed
    #: out, by the engine's own convention).
    exit_code: int
    #: The combined output, bounded head + tail with any elision counted.
    output: str


@dataclass
class RecordingRunner:
    """A :class:`CommandRunner` that DELEGATES every call and remembers each one.

    **A wrapper, not a second runner.** Every operation goes to ``inner`` (in
    production the engine's own ``SubprocessRunner``, which logs the argv and the
    output exactly as it always has); this only keeps a copy of what came back so
    the script verb can put it in the transcript. Thread-safe enough for its one
    use: the install runs on one helper thread, and the GUI thread reads
    :attr:`commands` only after that thread has published ``done``.
    """

    inner: CommandRunner
    commands: list[RecordedCommand] = field(default_factory=list)

    def which(self, name: str) -> bool:
        return self.inner.which(name)

    def exists(self, path: Path) -> bool:
        return self.inner.exists(path)

    def run(self, argv: list[str]) -> tuple[int, str]:
        code, output = self.inner.run(argv)
        self.commands.append(
            RecordedCommand(
                argv=one_line_argv(argv),
                argv_short=console_argv(argv),
                exit_code=code,
                output=_head_and_tail(output),
            )
        )
        return code, output


@dataclass(frozen=True)
class InstallOutcome:
    """What one install did. Built by :func:`run_install`; never raised past.

    ``ready`` is the engine's own verdict (``HostSetup.is_ready``: the ripper is
    reachable on the host), not "every step passed" — cd-paranoia is optional and
    deliberately last (KDD-29), so its failure must not read as "the ripper is not
    installed". That rule was ``app.main``'s and moves here with the code.
    """

    target: ForkTarget
    results: tuple[StepResult, ...]
    ready: bool
    #: Titles of the steps that FAILED, in order.
    failed: tuple[str, ...]
    #: True when ``cancelled()`` stopped the engine before a step.
    cancelled: bool
    #: Set when the engine itself raised (it should not); the install then did not
    #: complete and ``ready`` is False.
    crash: str = ""

    @property
    def exit_code(self) -> int:
        """The CLI's exit status: 0 when the ripper is usable, 1 otherwise."""
        return 0 if self.ready else 1


def resolve_cli_target(spec: str) -> tuple[ForkTarget | None, str]:
    """``--install-ripper [COMMIT]`` → ``(target, preamble)``.

    The three spellings the flag accepts, resolved ONCE so every line after it —
    the banner, the build, the verify — reads the same target:

    * ``latest`` / ``latest-beta``: a channel's head, from the fork's manifest
      (``deps/ripper_latest.py``). The preamble is the resolver's sentence; a
      ``None`` target means the manifest could not answer, and that is a refusal,
      never the approved build instead.
    * a commit: :func:`~platterpus.deps.fork_source.target_for_commit`.
    * empty: the wizard's target, the build a closed round approved.

    ``list`` is not handled here: it is a query that installs nothing, and stays
    with the CLI that prints the menu.
    """
    from platterpus.deps.fork_source import WIZARD_TARGET, target_for_commit
    from platterpus.deps.ripper_latest import resolve_keyword

    latest = resolve_keyword(spec)
    if latest is not None:
        return latest.target, latest.detail
    if spec:
        return target_for_commit(spec), ""
    return WIZARD_TARGET, ""


def install_preamble(target: ForkTarget) -> str:
    """What is about to be installed, and — when it is not approved — why that is
    expected. Printed BEFORE minutes of dnf and meson, not in a rip report later.

    Moved verbatim from ``app.main``; its two decisions keep their reasons:

    * **Compare the PIN, not the whole ForkTarget.** ``target_for_commit`` builds a
      target whose ``version`` and ``why`` differ by construction, so ``!=`` was
      true even for the approved pin by name, and the note then contradicted what
      ``--rig-check`` reported minutes later (measured on the rig, 2026-08-14).
    * **The reason is derived, not asserted.** One predicate in ``fork_source``
      decides whether a round is reviewing a build; this used to say "the round is
      open" unconditionally, which is false between rounds.
    """
    from platterpus import __version__
    from platterpus.build_info import build_fingerprint
    from platterpus.deps import fork_source
    from platterpus.deps.fork_source import PRODUCTION_TARGET, same_commit

    text = (
        f"Platterpus {__version__} (build {build_fingerprint()}) — installing "
        f"the ripping stack\n"
        f"cyanrip build: {target.pin} — {target.why}\n"
        f"expects banner: {target.expectation}\n"
    )
    if same_commit(target.pin, PRODUCTION_TARGET.pin):
        return text
    if fork_source.a_round_is_reviewing_a_build():
        because = (
            f"a round is open and is reviewing "
            f"{fork_source.PIN_UNDER_REVIEW}; nothing has approved this "
            f"build yet"
        )
    else:
        because = (
            f"no round is open, so {PRODUCTION_TARGET.pin} is the newest "
            f"build our record approves; this one is ahead of it and "
            f"unreviewed"
        )
    return text + (
        f"\nNOTE: this is not the handshake-approved build "
        f"({PRODUCTION_TARGET.pin}). Every rip will report\n"
        f"      'ripper handshake approval: unapproved' — that is correct, "
        f"not a fault:\n"
        f"      {because}.\n"
    )


def run_install(
    target: ForkTarget,
    *,
    progress: Callable[[StepResult], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    runner: CommandRunner | None = None,
) -> InstallOutcome:
    """Drive the setup wizard's step engine to install ``target``. Never raises.

    Every step is idempotent, so on a machine that is already set up this is a
    no-op through seven steps and a rebuild of the fork on the eighth when the
    installed build is a different commit (``HostSetup.fork_installed`` compares
    the host export's banner with ``target.pin``). The whole pipeline runs rather
    than one step reached into: a pipeline entered at the middle is a second
    pipeline.

    ``runner`` defaults to the engine's real ``SubprocessRunner``; the script verb
    passes a :class:`RecordingRunner` around it so the transcript can carry each
    command's argv, exit code and output. ``HostSetup`` is imported here, at call
    time, so a test's stand-in for it is the one this uses.
    """
    from platterpus.deps.host_setup import HostSetup
    from platterpus.deps.step_engine import SubprocessRunner

    setup = HostSetup(runner=runner or SubprocessRunner(), fork_target=target)
    was_cancelled = False

    def _cancelled() -> bool:
        nonlocal was_cancelled
        if cancelled is not None and cancelled():
            was_cancelled = True
        return was_cancelled

    try:
        results = tuple(setup.run(progress=progress, cancelled=_cancelled))
        ready = setup.is_ready()
    except Exception as exc:  # noqa: BLE001 — an install must report, never raise into a worker or the CLI
        log.exception("ripper install crashed")
        return InstallOutcome(
            target=target,
            results=(),
            ready=False,
            failed=(),
            cancelled=was_cancelled,
            crash=repr(exc),
        )
    failed = tuple(r.title for r in results if r.status is StepStatus.FAILED)
    return InstallOutcome(
        target=target,
        results=results,
        ready=ready and not was_cancelled,
        failed=failed,
        cancelled=was_cancelled,
    )


def outcome_text(outcome: InstallOutcome) -> str:
    """The closing sentence(s) of an install, as the CLI has always printed them.

    Report against the ripper being usable, not against every step passing (see
    :class:`InstallOutcome`). On a failure, say where the command output went:
    every argv and its combined output reached the log through the engine's
    ``SubprocessRunner``, so the failure is diagnosable without re-running.
    """
    if outcome.ready:
        text = "Ripping stack is ready. Launch Platterpus and insert a disc."
        if outcome.failed:
            text += f"\nOptional step(s) did not complete: {', '.join(outcome.failed)}"
        return text
    from platterpus.paths import LOG_PATH

    if outcome.crash:
        why = f"the installer itself failed ({outcome.crash})"
    elif outcome.cancelled:
        why = "it was cancelled before a step started"
    else:
        why = f"Failed step(s): {', '.join(outcome.failed) or 'unknown'}"
    return (
        f"Setup did not complete. {why}\n"
        f"The full command output is in the log: {LOG_PATH}"
    )


# --- What a SCRIPT may install ------------------------------------------------

#: The words ``install-ripper`` accepts in place of a commit, each naming a build
#: by its ROLE in the handshake record rather than by a sha. A committed script
#: that named a sha would freeze it on the day the script shipped, which is the
#: defect ``expect-ripper-under-review`` was rewritten to remove.
SCRIPT_INSTALL_KEYWORDS: Final[dict[str, str]] = {
    "(fork-pin)": "the build a closed round approved (FORK_PIN)",
    "(under-review)": "the build the handshake record is reviewing (PIN_UNDER_REVIEW)",
    "(pin)": "the build an acceptance run must be on (what section A accepts)",
}

#: A literal commit as a script may type it: 7 to 40 hex digits. Seven, not git's
#: four, because the fork's build tags carry seven and a shorter prefix can match
#: more than one known commit.
_COMMIT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-fA-F]{7,40}$")


def known_script_commits() -> dict[str, str]:
    """``{commit: why it is known}`` — every build a script may install.

    The fork's numbered releases our record holds (``FORK_RELEASE_SEQ_BY_PIN``,
    each read off their ``release-manifest.json``), plus the approved pin and the
    build under review, which a round may name before the fork has numbered it.
    Anything else is refused: an unattended batch that could build any sha would
    install whatever a typo named, and the step engine would happily do it.
    """
    from platterpus.deps import fork_source

    known = {
        commit: f"the fork's release_seq {seq}"
        for commit, seq in fork_source.FORK_RELEASE_SEQ_BY_PIN.items()
    }
    known[fork_source.FORK_PIN] = "the approved pin (FORK_PIN)"
    known[fork_source.PIN_UNDER_REVIEW] = known.get(
        fork_source.PIN_UNDER_REVIEW, "the build under review (PIN_UNDER_REVIEW)"
    )
    return known


def resolve_script_commit(spec: str) -> tuple[str, str]:
    """A script's ``install-ripper`` argument → ``(commit, "")`` or ``("", why)``.

    Pure and never raises. A keyword resolves through ``fork_source``'s one
    predicate for each role, so it moves when the record moves. A literal commit
    must be hex, 7 to 40 characters, and one :func:`known_script_commits` names;
    it resolves to that known spelling, so the build tag the verify step expects
    is the seven-character one the binary prints.
    """
    from platterpus.deps import fork_source

    word = (spec or "").strip()
    keyword = word.lower()
    if keyword == "(fork-pin)":
        return fork_source.FORK_PIN, ""
    if keyword == "(under-review)":
        return fork_source.PIN_UNDER_REVIEW, ""
    if keyword == "(pin)":
        return fork_source.pin_the_rig_should_install(), ""
    if not _COMMIT_RE.match(word):
        return "", (
            f"{word!r} is neither a commit (7 to 40 hex digits) nor one of "
            f"{', '.join(SCRIPT_INSTALL_KEYWORDS)}"
        )
    matches = [c for c in known_script_commits() if fork_source.same_commit(word, c)]
    if len(matches) != 1:
        return "", (
            f"{word} is not a build this Platterpus knows "
            + (f"uniquely (it matches {matches})" if matches else "")
            + ": a script may install only the fork's numbered releases our "
            "record holds, the approved pin and the build under review — "
            f"{', '.join(sorted(known_script_commits()))}"
        )
    return matches[0], ""
