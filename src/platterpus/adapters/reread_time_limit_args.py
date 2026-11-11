# SPDX-License-Identifier: GPL-3.0-only
"""The words of cyanrip's ``--reread-time-limit``, its range, and its build gate.

**What the option does** (the fork's ``.28``, their round 36 lap 10 S11, accepted
by our lap 11 S6): after each whole-track ``-Z`` read of a track that has not
converged, once its reads have taken SECONDS or more, no further read starts. A
read in progress is never stopped, so the first read always runs.

**Where we send it** (round 39, TASKS R49): on the securing pass only, whose
``-Z`` reads it bounds by time as well as by ``-r``. The seconds are
``securing_time_limit.securing_pass_time_limit``'s, derived from the album
pass's log rather than from the disc being ripped now, so CLAUDE.md's argv rule
applies: the RANGE is checked here, at the chokepoint, not only stated.

**Its range is the option's own**: a whole number from 1 to INT32_MAX, read from
the fork's option table at every listed build (``GEN_OPT_ONE(..., int32_t,
reread_time_limit, "", 1, 1, 0, 1, INT32_MAX`` at
``cyanrip@3f288fb:src/cyanrip_main.c:2990``, ``cyanrip@8d2ca72:…:3035`` and
``cyanrip@5cc1c6b:…:3214``). And cyanrip refuses it without ``-Z`` (exit 64,
``cyanrip@5cc1c6b:src/cyanrip_main.c:3414-3417``), so we refuse that pair before
it reaches them, as the ``-Z``/``-r`` pair is refused.

**A caller error raises; it is never dropped.** A silent drop would read, in our
own record, as a limit that was set. A build that does not list the option
(``fork_source.accepts_reread_time_limit``) gets nothing, and its count alone
bounds the pass: cyanrip refuses an option it does not know, and every
availability probe reads a refused run as a missing ripper.

**Composes with ``.31``'s proposed ``--reread-until-accuraterip CONF``** (their
round 38 lap 16 S13; not sent until a release carries it): that option keeps a
``-Z`` track reading past agreement on a checksum AccurateRip does not match, and
this one is what still ends such a track's reads, by time, where ``-r`` would end
them by count.

Pure apart from the import of the gate; never raises except the refusal.
"""

from __future__ import annotations

from typing import Final

from platterpus.adapters.rip_backend import RipError

#: cyanrip's long-only option, as P1 of `.28`'s provider contract spells it
#: (`round-37-lap-04-provider-contract-gef413b1.md:62`).
REREAD_TIME_LIMIT_FLAG: Final[str] = "--reread-time-limit"
#: The option's range, from its own table (the module docstring cites each build).
REREAD_TIME_LIMIT_MIN_SECONDS: Final[int] = 1
REREAD_TIME_LIMIT_MAX_SECONDS: Final[int] = 2**31 - 1


def reread_time_limit_args_for_build(build_tag: str, seconds: int) -> list[str]:
    """``["--reread-time-limit", "<seconds>"]`` for a build that lists it, else ``[]``.

    The gate alone, as for ``--prefer-accuraterip-match``; ``seconds`` must
    already have passed :func:`reread_time_limit_args`'s range check.
    """
    from platterpus.deps import fork_source

    if not fork_source.accepts_reread_time_limit(build_tag):
        return []
    return [REREAD_TIME_LIMIT_FLAG, str(seconds)]


def reread_time_limit_args(
    build_tag: str, seconds: int | None, secure_rerip_matches: int
) -> list[str]:
    """The argv words for ``seconds``, after the range and ``-Z`` checks.

    ``None`` asks for no limit and gives ``[]``. Anything else must be a whole
    number in the option's range, on a pass with ``-Z``, or :class:`RipError` is
    raised whatever the build; then the build gate decides whether it is sent.
    """
    if seconds is None:
        return []
    if (
        isinstance(seconds, bool)
        or not isinstance(seconds, int)
        or not REREAD_TIME_LIMIT_MIN_SECONDS <= seconds <= REREAD_TIME_LIMIT_MAX_SECONDS
    ):
        raise RipError(
            f"refusing reread_time_limit_s={seconds!r}: cyanrip takes a whole "
            f"number of seconds from {REREAD_TIME_LIMIT_MIN_SECONDS} to "
            f"{REREAD_TIME_LIMIT_MAX_SECONDS}"
        )
    if secure_rerip_matches <= 0:
        raise RipError(
            "refusing --reread-time-limit without -Z: it limits -Z's re-reads, "
            "and cyanrip refuses it alone (exit 64)"
        )
    return reread_time_limit_args_for_build(build_tag, seconds)
