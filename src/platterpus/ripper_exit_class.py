"""Which KIND of failure the ripper's exit status names, for the build that ran.

**Why this exists.** From ``.25`` (fork release 36, build tag
``platterpus-fork-g5f1d036``) cyanrip sorts its own failures into exit classes,
which our round 35 lap 8 S9 asked for and the fork's provider contract derives
from source (``docs/handshake/inbound/artifacts/round-35-lap-15-provider-
contract-g3e978f9.md`` §P4):

* ``64`` ``CRIP_EXIT_USAGE`` — an argument refused, or a flag this build lacks;
* ``74`` ``CRIP_EXIT_IOERR`` — the disc or drive failed: no device, unopenable,
  TOC unreadable, medium changed;
* ``128 + N`` — a run stopped by signal N, after its log and footer were written;
* ``1`` — every other failure, which **carries no class**; ``0`` — success.

Before this module the report recorded the number and the status line ignored
it, so a ``74`` read exactly like a ``1``: the user was not told the one thing
the ripper had gone out of its way to say, that the disc or the drive was the
problem. That is the *capture without surfacing* shape ``CLAUDE.md`` names.

**Tri-state, and never a class the build cannot emit.** Builds before release 36,
and stock cyanrip, exit ``1`` for a refusal and for a drive failure alike. On
those builds a ``64`` or a ``74`` is NOT cyanrip's class (it never prints one), so
it is reported as ``unclassified``, never as ``refused`` or ``disc_or_drive``. A
build we cannot place in the release sequence gives ``not_determined`` for any
code whose meaning depends on the build. Which builds speak the classes is asked
of :func:`platterpus.ripper_exit.refusal_exit_code` — the one place that already
answers "which convention does this build use" — so the release threshold and
the tag parsing live in exactly one function.

Pure; never raises.
"""

from __future__ import annotations

from typing import Final, Literal

from platterpus.ripper_exit import (
    CONTAINER_TOOL_ERROR,
    REFUSED_EXIT_BEFORE_CLASSES,
    REFUSED_EXIT_WITH_CLASSES,
    describe_unrequested_exit,
    refusal_exit_code,
    signal_of,
)

#: The class names written to the report's ``outcome.ripper_exit_class``. A JSON
#: consumer reads these strings, so they are wire format: add, never rename.
ExitClass = Literal[
    # Exit 0, on every build.
    "ok",
    # 64 on a build from release 36: cyanrip refused an argument or a flag.
    "refused",
    # 74 on a build from release 36: cyanrip says the disc or the drive failed.
    "disc_or_drive",
    # 128 + N, or a negative status from Popen: a signal ended it (any build).
    "signal",
    # 125: podman's error of its own, so the ripper never got to run (any build).
    "container_tool",
    # Any other non-zero exit on a build that speaks the classes: a failure the
    # ripper names no class for. Its own message says which one.
    "failure",
    # A non-zero exit on a build that predates the classes (an earlier fork
    # release, or stock cyanrip): it cannot tell a refusal from a drive failure
    # from anything else, so no class is claimed.
    "unclassified",
    # No exit status (never reaped), or a code whose meaning depends on a build
    # we cannot place.
    "not_determined",
]

#: cyanrip's ``CRIP_EXIT_IOERR`` (EX_IOERR), the disc-or-drive class from ``.25``.
DISC_OR_DRIVE_EXIT: Final[int] = 74

#: Every value of :data:`ExitClass`, for tests and for any reader that enumerates.
EXIT_CLASSES: Final[tuple[ExitClass, ...]] = (
    "ok",
    "refused",
    "disc_or_drive",
    "signal",
    "container_tool",
    "failure",
    "unclassified",
    "not_determined",
)


def build_speaks_exit_classes(build_tag: str) -> bool | None:
    """Whether ``build_tag``'s build emits the exit classes: tri-state.

    ``True`` for a fork release from 36, ``False`` for an earlier fork release or
    stock cyanrip, ``None`` for a build we cannot place. Read off
    :func:`~platterpus.ripper_exit.refusal_exit_code`: a build whose refusal is
    ``64`` is a build that speaks the classes, by the contract's definition of
    the classes. Delegating rather than restating keeps the threshold in one place.
    """
    code = refusal_exit_code(build_tag)
    if code is None:
        return None
    if code == REFUSED_EXIT_WITH_CLASSES:
        return True
    if code == REFUSED_EXIT_BEFORE_CLASSES:
        return False
    # A value refusal_exit_code does not document today. Unknown, not a guess.
    return None  # pragma: no cover — refusal_exit_code returns only 64, 1 or None


def classify_exit(exit_code: int | None, build_tag: str) -> ExitClass:
    """The class of ``exit_code`` for the build named by ``build_tag``.

    Build-independent readings come first, because they hold whatever produced
    the status: ``0`` is success on every cyanrip, a signal death is the shell /
    ``Popen`` convention :func:`~platterpus.ripper_exit.signal_of` reads, and
    ``125`` is podman's own error (``ripper_exit.CONTAINER_TOOL_ERROR``). Only
    then is the build asked, because only ``64``, ``74`` and ``1`` change meaning
    with it.
    """
    if exit_code is None:
        # An unreaped child has no exit status at all, which is a different fact
        # from any class. The report already carries `ripper_exit_code: null`.
        return "not_determined"
    if exit_code == 0:
        return "ok"
    if signal_of(exit_code) is not None:
        return "signal"
    if exit_code == CONTAINER_TOOL_ERROR:
        return "container_tool"
    speaks = build_speaks_exit_classes(build_tag)
    if speaks is None:
        return "not_determined"
    if not speaks:
        # The build cannot emit a class, so none is claimed, even for a 64 or a 74
        # that happens to share a class's number.
        return "unclassified"
    if exit_code == REFUSED_EXIT_WITH_CLASSES:
        return "refused"
    if exit_code == DISC_OR_DRIVE_EXIT:
        return "disc_or_drive"
    return "failure"


def describe_exit_class(exit_class: ExitClass, exit_code: int | None) -> str:
    """One sentence for the two classes that change what a user should do, or ``""``.

    Only ``refused`` and ``disc_or_drive`` get words here. ``signal`` and
    ``container_tool`` already have theirs in
    :func:`~platterpus.ripper_exit.describe_unrequested_exit`, which stays the
    authority for them. ``failure`` gets none because the class says nothing the
    ripper's own message does not say better; and ``unclassified`` /
    ``not_determined`` get none because there is nothing true to add.

    The sentence never REPLACES cyanrip's own message: the caller appends it after
    whatever cyanrip printed (the tool's words lead, the advice follows), and the
    sentence points at the rip log view for the case where nothing was matched.
    """
    if exit_class == "disc_or_drive":
        return (
            f"The disc or the drive failed: cyanrip exited {exit_code}, its code "
            f"for a disc or drive failure (no drive at that device, a drive it "
            f"could not open, a table of contents it could not read, or a disc "
            f"that changed mid-rip). Its own message says which; it is in the rip "
            f"log view. Check that the disc is in the drive and the drive is "
            f"connected, then start the rip again."
        )
    if exit_class == "refused":
        return (
            f"cyanrip refused an argument or a flag Platterpus sent it (exit "
            f"{exit_code}, its code for a refused argument), so the disc and the "
            f"drive are not the cause. Its own message names the argument; it is "
            f"in the rip log view. If it names a flag this ripper build lacks, "
            f"Tools → Setup & Updates can update the ripper."
        )
    return ""


def explain_failed_exit(
    exit_code: int | None,
    build_tag: str,
    *,
    we_stopped_it: bool,
    said_quit_notice: bool = False,
) -> str:
    """The sentence the rip worker appends to a failed pass's hint, or ``""``.

    The one entry point the worker calls, so the status line and the report's
    ``failure_hint`` are composed in one place. The signal and container-tool
    wording of :func:`~platterpus.ripper_exit.describe_unrequested_exit` is kept
    and asked first (it knows whether Platterpus stopped the ripper itself, which
    the class cannot); the class sentence answers only when it has nothing to say.
    """
    unrequested = describe_unrequested_exit(
        exit_code, we_stopped_it=we_stopped_it, said_quit_notice=said_quit_notice
    )
    if unrequested:
        return unrequested
    if we_stopped_it:
        # A rip we cancelled or signalled is described by the cancel, not by the
        # exit status it ended on.
        return ""
    return describe_exit_class(classify_exit(exit_code, build_tag), exit_code)
