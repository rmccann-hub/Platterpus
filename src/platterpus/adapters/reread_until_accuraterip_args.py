# SPDX-License-Identifier: GPL-3.0-only
"""The words of cyanrip's ``--reread-until-accuraterip``, its range, and its build gate.

**What the option does** (the fork's ``.31``, built as their round 39 lap 1 S4
says, from their round 38 lap 16 S13, which our lap 17 S8 accepted): under ``-Z``,
an agreement on a read AccurateRip does not match, on a track AccurateRip holds at
confidence CONF or more, does not end the track. Reading goes on until a read
AccurateRip matches at CONF or more, which is kept, or a limit (``-r``, or
``--reread-time-limit``), where ``--prefer-accuraterip-match``'s keep rule applies.

**Why we send it, and where** (round 39's gate G1): track 3 of the reference disc
converged on ``3D8FCF0C`` on the owner's drive, reads agreeing with each other on
audio AccurateRip does not hold, so ``-Z`` alone shipped the wrong read. The rule
lets the ripper itself refuse that agreement. We send it on **every pass that
reads with ``-Z``** (:func:`confidence_for_pass`), and on no other:

* the securing pass, which re-reads the tracks AccurateRip did not verify (sent
  there first, commit f7615bf6);
* the album pass when it reads with ``-Z`` itself: Archival Exact's uniform
  secure re-read, the rig sheet's section N, "uniform secure re-read, WHOLE DISC",
  and a read-speed ladder pass that escalated ``-Z``. The fork's round 39 lap 3
  S15 asked why that step sent ``-Z 2`` alone: on 2026-11-11 it kept
  ``3D8FCF0C`` by agreement (reads 1 and 4) before our chase replaced it. An
  agreement AccurateRip rejects is the same question on any ``-Z`` pass, so the
  answer cannot depend on which pass asked it;
* never a pass without ``-Z``: the verified-read chase's single reads, a plain
  album pass. cyanrip refuses the option there (below), and there is no
  agreement for it to test.

Its readers are :mod:`platterpus.reread_ar_overrule`.

**``--reread-time-limit`` does NOT follow it onto the album pass**, and that is
the same reasoning that put it on the securing pass (commit d11d6edf). That
limit is rule 2 of the chase budget, the larger of 5 x a track's length and 2 x
its album-pass read time, sent only when every track's budget can be computed,
so that it is never below any track's own. Before the album pass there is no
album-pass read time, so a value from the length alone can sit below a slow
track's budget, and a limit sent wrongly can only stop reads early. This option
is the other way round: it can only make a ``-Z`` track read on, and ``-r`` still
bounds that by count, as it bounds every track whose reads never agree.

**CONF is 2**, as our round 38 lap 17 S8 told the fork (*"sent as
``--reread-until-accuraterip 2``"*): an entry at confidence 1 is one other
submission, which can be another drive's identical misread; two independent
submissions are the least that makes "AccurateRip holds this track" a claim about
the disc. It is a constant, not a setting: the value is ours, never derived from
the disc being ripped, so CLAUDE.md's argv rule still checks its range here.

**Its range is the option's own**: a whole number from 1 to INT32_MAX
(``GEN_OPT_ONE(..., int32_t, reread_until_accuraterip, "", 1, 1, 0, 1, INT32_MAX``
at ``cyanrip@e531a33:src/cyanrip_main.c:3345``). And cyanrip refuses it without
``-Z`` (exit 64, ``cyanrip@e531a33:src/cyanrip_main.c:3553-3556``), so we refuse
that pair before it reaches them, as ``--reread-time-limit``'s is refused.

**A caller error raises; it is never dropped**, for the reason
:mod:`platterpus.adapters.reread_time_limit_args` gives. A build that does not
list the option (``fork_source.accepts_reread_until_accuraterip``) gets nothing:
cyanrip refuses an option it does not know, and every availability probe reads a
refused run as a missing ripper.

Pure apart from the import of the gate; never raises except the refusal.
"""

from __future__ import annotations

from typing import Final

from platterpus.adapters.rip_backend import RipError

#: cyanrip's long-only option, as P1 of `.31`'s provider contract spells it
#: (`round-39-lap-01-provider-contract-g6eacb8b.md:63`).
REREAD_UNTIL_ACCURATERIP_FLAG: Final[str] = "--reread-until-accuraterip"
#: The option's range, from its own table (the module docstring cites it).
REREAD_UNTIL_ACCURATERIP_MIN: Final[int] = 1
REREAD_UNTIL_ACCURATERIP_MAX: Final[int] = 2**31 - 1
#: The confidence every ``-Z`` pass sends (the module docstring says why 2).
REREAD_ACCURATERIP_CONFIDENCE: Final[int] = 2


def confidence_for_pass(secure_rerip_matches: int) -> int | None:
    """What a pass with this ``-Z`` asks for: CONF when it reads with ``-Z``, else None.

    The ONE decision of which passes carry the option, so the worker's single
    spawn site (``RipWorker._rip_once``) cannot ask for it on one ``-Z`` pass and
    forget it on another, which is how section N's whole-disc ``-Z`` pass sent
    ``-Z 2`` alone (the fork's round 39 lap 3 S15). ``None`` without ``-Z``,
    because :func:`reread_until_accuraterip_args` refuses the option there, as
    cyanrip does. The build gate is still the backend's. Never raises.
    """
    if isinstance(secure_rerip_matches, int) and secure_rerip_matches > 0:
        return REREAD_ACCURATERIP_CONFIDENCE
    return None


def reread_until_accuraterip_args(
    build_tag: str, confidence: int | None, secure_rerip_matches: int
) -> list[str]:
    """The argv words for ``confidence``, after the range and ``-Z`` checks.

    ``None`` asks for nothing and gives ``[]``. Anything else must be a whole
    number in the option's range, on a pass with ``-Z``, or :class:`RipError` is
    raised whatever the build; then the build gate decides whether it is sent.
    """
    if confidence is None:
        return []
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, int)
        or not REREAD_UNTIL_ACCURATERIP_MIN
        <= confidence
        <= REREAD_UNTIL_ACCURATERIP_MAX
    ):
        raise RipError(
            f"refusing reread_until_accuraterip={confidence!r}: cyanrip takes a "
            f"whole AccurateRip confidence from {REREAD_UNTIL_ACCURATERIP_MIN} to "
            f"{REREAD_UNTIL_ACCURATERIP_MAX}"
        )
    if secure_rerip_matches <= 0:
        raise RipError(
            "refusing --reread-until-accuraterip without -Z: it tests -Z's "
            "agreement, and cyanrip refuses it alone (exit 64)"
        )
    from platterpus.deps import fork_source

    if not fork_source.accepts_reread_until_accuraterip(build_tag):
        return []
    return [REREAD_UNTIL_ACCURATERIP_FLAG, str(confidence)]
