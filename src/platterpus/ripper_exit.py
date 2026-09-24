"""What the ripper's exit status says about WHO ended the rip.

**Why this exists.** The 2026-09-24 acceptance run lost its first whole-disc rip
95 seconds in. The facts were all captured: the ripper printed ``Trying to quit``,
exited **137**, and 130 ms later the next call through the Distrobox wrapper
failed with podman's own ``unable to start container … /etc/passwd: no such file
or directory`` — the container had been stopped underneath the rip. Nobody had
pressed Cancel and Platterpus had sent no signal. The status line the user read
was *"Rip failed — no diagnosis was captured"*.

That sentence was false, and it is the shape `CLAUDE.md` names under
*diagnostic completeness*: **capture without surfacing is the same bug from the
user's side.** Every fact needed to say what happened was on the worker, and
none of it reached a sentence, because the only thing that fed the status line
was a matched line of the ripper's *output* — and a process that is killed does
not get to print why.

**What an exit status can tell us, and where each reading comes from:**

* **The ripper's own codes are 0-5.** The fork's provider contract derives its
  exit inventory from source and resolves exactly ``0``-``5`` with no unresolved
  paths (``docs/handshake/inbound/artifacts/round-26-lap-01-provider-contract-
  g37f946b.md`` §P4). So a larger number did not come from cyanrip deciding to
  stop.
* **128 + N is a death by signal N**, in the shell convention the Distrobox
  wrapper's transport (``podman exec``) reports a killed child with; ``137`` is
  SIGKILL, ``143`` SIGTERM. A **negative** status is the same fact reported by
  ``Popen`` for the process it spawned itself (``-9`` for SIGKILL).
* **125 is podman's code for an error of its own** — the container tool failed
  before or around the command, rather than the command failing. That is the code
  the post-rip probe above returned.

**A signal comes from software.** A scratched disc, a failing drive or a bad read
offset make the ripper *report* an error and exit 1; none of them sends a signal.
So when the ripper dies by a signal Platterpus did not send, the one thing this
module can say with certainty is that the disc and the drive are not the cause —
and that the rip is safe to run again. Which piece of software sent it is NOT
knowable from the exit status, so the sentence names the likely candidates and
never asserts one.

Pure; never raises. The worker decides whether *we* sent a signal (it is the only
place that knows) and passes the answer in.
"""

from __future__ import annotations

import signal
from typing import Final

#: The shell's convention for "killed by signal N": exit status 128 + N.
_SIGNAL_EXIT_BASE: Final[int] = 128

#: Linux numbers its signals 1..64 (the real-time range tops out at 64). A status
#: past 128 + 64 is not a signal death under any convention, so it is not read as
#: one.
_HIGHEST_SIGNAL: Final[int] = 64

#: podman's exit status for "the error is podman's own" (podman-exec(1), *Exit
#: Status*: 125 is an error with podman itself, 126 a command that cannot be
#: invoked, 127 a command that cannot be found). Only 125 is named here: it is the one measured on the rig,
#: and it is the one that means the container itself was the problem.
CONTAINER_TOOL_ERROR: Final[int] = 125

#: The line cyanrip's signal handler writes when it is asked to stop. Named so the
#: worker and this module mean the same text; its origin and the single-`write(2)`
#: shape are measured in ``docs/testing.md`` §5.ay.
QUIT_NOTICE: Final[str] = "Trying to quit"


def signal_of(exit_code: int | None) -> int | None:
    """The signal that ended the process, or ``None`` if it exited by itself.

    ``None`` in is ``None`` out: an unreaped child has no exit status at all, and
    that is a different fact from "it was not signalled".
    """
    if exit_code is None:
        return None
    if exit_code < 0:
        number = -exit_code
    elif exit_code > _SIGNAL_EXIT_BASE:
        number = exit_code - _SIGNAL_EXIT_BASE
    else:
        return None
    return number if 1 <= number <= _HIGHEST_SIGNAL else None


def signal_label(number: int) -> str:
    """``"SIGKILL"`` for 9, and a plain ``"signal 70"`` for a number we cannot name."""
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"signal {number}"


def describe_unrequested_exit(
    exit_code: int | None,
    *,
    we_stopped_it: bool,
    said_quit_notice: bool = False,
) -> str:
    """One sentence a user can act on, or ``""`` when the exit needs no special words.

    ``we_stopped_it`` is True when this rip was cancelled or Platterpus itself sent
    the stop signal — then a signal death is the expected ending, and saying it came
    "from outside" would be false. ``said_quit_notice`` is whether the ripper's own
    output carried :data:`QUIT_NOTICE`, which is evidence it was ASKED to stop
    before it was killed; it is reported as that, not as a cause.

    Returns ``""`` for a clean exit, for the ripper's own failure codes (its output
    carries the diagnosis for those, and other code surfaces it), and for anything
    this module cannot read with confidence.
    """
    if exit_code is None or exit_code == 0 or we_stopped_it:
        return ""
    number = signal_of(exit_code)
    if number is not None:
        asked = (
            f" It had printed '{QUIT_NOTICE}' first, so it was asked to stop "
            f"before it was killed."
            if said_quit_notice
            else ""
        )
        return (
            f"The rip was stopped from outside Platterpus: the ripper ended on "
            f"{signal_label(number)} (exit {exit_code}), and Platterpus had not "
            f"asked it to stop.{asked} A signal comes from software, so the disc "
            f"and the drive are not the cause. Something on this computer ended "
            f"it — most often the Distrobox container the ripper runs in being "
            f"stopped or restarted (a system update, another app, or a manual "
            f"'distrobox stop'), or the system running out of memory. Start the "
            f"rip again."
        )
    if exit_code == CONTAINER_TOOL_ERROR:
        return (
            f"The rip could not run: the container tool (podman) reported an "
            f"error of its own (exit {exit_code}), so the ripper inside the "
            f"Distrobox container never got to work. The disc and the drive are "
            f"not the cause. Its own message is in the rip log view; if it says "
            f"the container could not be started, start the rip again — if it "
            f"keeps happening, Tools → Setup & Updates checks the container."
        )
    return ""
