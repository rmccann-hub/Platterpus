"""The warnings an acceptance run expects, and the one binary each is expected on.

**Kept out of the graders on purpose.** A grader answers *did this artifact
hold?*; this answers a narrower question the graders consult: *is this the one
state in which a warning the product rightly gives is the run working as
designed?* The product keeps warning users (``rip_audit``); only the acceptance
grader may treat the warning as expected, and only here is that decided, so a
second grader cannot grow its own copy of the rule.

Pure, Qt-free and never raises, like the graders that call it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Final

#: The round number a fork handshake note names: ``round 30 lap 11 OPEN, …``.
_NOTE_ROUND: Final[re.Pattern[str]] = re.compile(
    r"\bround (?P<round>\d{1,4})\b", re.IGNORECASE
)

#: The characters of a git commit as a build tag spells it. A ``-dirty`` build
#: carries a hyphen after the commit, so it is never the build under review.
_HEX: Final[frozenset[str]] = frozenset("0123456789abcdef")


def expected_open_round_warning(report: Mapping[str, Any] | None) -> str:
    """Why the handshake check's open-round warning is expected here, or ``""``.

    **The one warning the acceptance run expects, and only on one binary.** The
    product's audit warns whenever cyanrip says it was built from an open round,
    and it should: a user ripping with an unreleased build must be told. But a
    closing run tests exactly such a build, because a fork build goes to beta
    inside the open round first (round 30's O3), and the fork's release plan
    requires every rip of it to say so. Graded as a failure, that warning failed
    every closing run seven times by construction (2026-10-06), and seven failures
    everyone reads past are where a real one would hide. The maintainer chose
    this narrowing on 2026-10-06; the run that showed it stays ``partial``.

    **All four must hold, each read from the report, or the answer is ``""``:**

    * the build tag is a clean fork tag (no ``-dirty``) whose commit is the build
      under review, asked of :func:`fork_source.is_the_build_under_review`, the
      one predicate the offer and the wizard also use;
    * our own verdict on the binary is ``unapproved``;
    * the binary's note names the round reviewing that build
      (:data:`fork_source.PIN_UNDER_REVIEW_ROUND`);
    * the note says it is open and not closed.

    A label alone is never enough: the note's words are checked together with
    the binary they describe. Any other build, round or verdict leaves the
    warning a failure, and the check's DISAGREEMENT warning is never excused.
    Never raises; a malformed report is ``""``.
    """
    from platterpus.deps import fork_source

    if not isinstance(report, Mapping):
        return ""
    rip = report.get("rip")
    if not isinstance(rip, Mapping):
        return ""
    tag = str(rip.get("ripper_build") or "").strip()
    note = str(rip.get("ripper_handshake_note") or "").strip()
    verdict = str(rip.get("ripper_handshake_approval") or "").strip()
    # String operations, not a regex: a pattern over the whole tag was quadratic
    # in a long run of tag characters (tests/test_regex_bounded_time.py).
    prefix = f"{fork_source.FORK_BRANCH}-g"
    commit = tag[len(prefix) :] if tag.startswith(prefix) else ""
    if not 7 <= len(commit) <= 40 or not set(commit) <= _HEX:
        return ""
    if not fork_source.is_the_build_under_review(commit) or verdict != "unapproved":
        return ""
    named = _NOTE_ROUND.search(note)
    lowered = note.casefold()
    if (
        named is None
        or int(named.group("round")) != fork_source.PIN_UNDER_REVIEW_ROUND
        or "open" not in lowered
        or "closed" in lowered
    ):
        return ""
    return (
        f"expected on the build under review ({tag}, round "
        f"{fork_source.PIN_UNDER_REVIEW_ROUND}), which must say it is unreleased; "
        f"our verdict agrees: {verdict}"
    )
