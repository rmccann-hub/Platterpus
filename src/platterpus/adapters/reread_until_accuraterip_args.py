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
lets the ripper itself refuse that agreement. We send it on the **securing pass
only**: that pass re-reads exactly the tracks AccurateRip did not verify, so it is
where an agreement on the wrong audio is the question; the album pass is left as
it was. Its readers are :mod:`platterpus.reread_ar_overrule`.

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
#: The confidence the securing pass sends (the module docstring says why 2).
SECURING_PASS_ACCURATERIP_CONFIDENCE: Final[int] = 2


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
