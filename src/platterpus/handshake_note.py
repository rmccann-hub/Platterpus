"""What the fork's compiled-in ``Handshake:`` note says about its own build.

The cyanrip fork writes one line into every log, for example::

    Handshake:      round 30 lap 17 closed, verdict GO -- released build

Two separate facts share that line:

* **Was the build released?** That is the arm after ``--``: ``released build`` or
  ``NOT a released build``. Since round 10 the fork decides it at build time.
* **Which round was the tree in?** That is the ``OPEN`` / ``closed`` word before it.

Until 2026-10-07 our audit (``rip_audit``) and our approval cross-check
(``handshake_approval.cross_check_note``) each read the word *open* as *not
released*. That was true while the fork printed ``NOT a released build`` for every
build cut inside an open round. Their round 31 lap 1 proposes (E7) that the arm be
decided by the build flag and a clean tree alone, with the round kept in the line as
information. Under that, a released build cut while a round is open would say
``... OPEN ... -- released build``, and both our readers would have warned that it
was unreleased. So the arm decides now, and the round word decides only for a note
old enough to have no arm (before round 10, a released build printed no suffix).

**One reading, two callers.** Both readers delegate here, because two copies of this
judgement is how they would come to disagree (``docs/testing.md`` §5.al).

Pure; never raises.
"""

from __future__ import annotations

from typing import Final, Literal

#: Whether the build says it was released. ``not_determined`` is a third state, never
#: a negative: an empty or unfamiliar note is not evidence that a build is unreleased.
ReleaseState = Literal["released", "unreleased", "not_determined"]

#: Which round state the note names, as information.
RoundState = Literal["open", "closed", "not_determined"]

#: The two arms. The unreleased one CONTAINS the released one, so it is tested first.
_UNRELEASED_ARM: Final[str] = "not a released build"
_RELEASED_ARM: Final[str] = "released build"


def round_state(note: str | None) -> RoundState:
    """``open`` or ``closed`` when the note names exactly one of them."""
    lowered = (note or "").casefold()
    says_open = "open" in lowered
    says_closed = "closed" in lowered
    if says_open and not says_closed:
        return "open"
    if says_closed and not says_open:
        return "closed"
    return "not_determined"


def release_state(note: str | None) -> ReleaseState:
    """The build's own claim about whether it was released.

    The arm decides when the note has one. A note without an arm predates round 10:
    then an open round, or a ``HOLD`` verdict, reads as unreleased and a closed round
    as released, which is how both callers read every note before 2026-10-07.
    """
    lowered = (note or "").casefold().strip()
    if not lowered:
        return "not_determined"
    if _UNRELEASED_ARM in lowered:
        return "unreleased"
    if _RELEASED_ARM in lowered:
        return "released"
    state = round_state(lowered)
    if state == "open" or "hold" in lowered:
        return "unreleased"
    if state == "closed":
        return "released"
    return "not_determined"
