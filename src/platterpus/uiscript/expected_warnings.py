"""The warnings an acceptance run expects, and the one state each is expected in.

Two, each narrowed until a label alone cannot satisfy it: the build under review
saying it is unreleased (:func:`expected_open_round_warning`, 2026-10-06), and a
ripping-error tally the record places entirely on reads the album replaced with
one AccurateRip verified (:func:`expected_ripping_error_warning`, TASKS R59 (a),
the owner's word of 2026-11-16).

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
from dataclasses import dataclass
from typing import Any, Final

#: The round number a fork handshake note names: ``round 30 lap 11 OPEN, …``.
_NOTE_ROUND: Final[re.Pattern[str]] = re.compile(
    r"\bround (?P<round>\d{1,4})\b", re.IGNORECASE
)

#: The characters of a git commit as a build tag spells it. A ``-dirty`` build
#: carries a hyphen after the commit, so it is never the build under review.
_HEX: Final[frozenset[str]] = frozenset("0123456789abcdef")

#: The last report schema whose replaced track carries the SUPERSEDED read's
#: paranoia counters. 0.7.111 and 0.7.112 wrote schema 39 (``rip_report.py``'s
#: v40 note); TASKS R61's fix, which takes a replaced track's counters from the
#: read its file holds, shipped in 0.7.113, the first release writing 40
#: (``v0.7.113:src/platterpus/rip_report.py`` reads ``REPORT_SCHEMA_VERSION: int
#: = 40`` and carries ``_merge_shipped_track``). Read from the artifact, not
#: remembered: run C's track 16 shows chase read 5's CRC beside the first read's
#: ``SKIP: 1`` (``tests/test_auto_fix_convergence.py::_run_c_track_16``).
_LAST_SCHEMA_WITH_SUPERSEDED_COUNTERS: Final[int] = 39


@dataclass(frozen=True)
class ExpectedWarning:
    """One warning the grader may expect: its exact words, and why it is expected.

    ``text`` is the whole warning, so the grader excuses only a finding that says
    exactly this, never one that merely begins the same way.
    """

    text: str
    reason: str


def expected_open_round_warning(report: Mapping[str, Any] | None) -> str:
    """Why the handshake check's open-round warning is expected here, or ``""``.

    **The one warning the acceptance run expects, and only on one binary.** The
    product's audit warns whenever cyanrip says it was not declared released,
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


def _int(value: object) -> int | None:
    """``value`` as an int, or None. A bool is not a number here."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def expected_ripping_error_warning(
    report: Mapping[str, Any] | None,
) -> ExpectedWarning | None:
    """The completion check's ripping-error warning this report earns, if expected.

    **Why it may be expected** (TASKS R59 (a); the owner's word of 2026-11-16,
    "4. a"). cyanrip's ``Ripping errors:`` tally counts the album pass. When every
    error it counted was in the first read of a track the album then REPLACED with
    a read AccurateRip verified, the files hold none of those reads, and the tally
    is history about a read nobody keeps. The product's audit still says so
    (``rip_audit``); this decides only that the acceptance grader may read that
    warning as the run working, not failing. On run C (2026-10-22) disc 3's track
    16 had two paranoia skips in its first read, chase read 5 replaced it at v1
    confidence 11 and v2 24, and ``expect-album-audit`` failed on the tally alone.

    **Every condition is read from the report, or the answer is None:**

    * the placement closes (:func:`platterpus.replaced_read_errors.errors_in_replaced_reads`,
      the one placement the audit, ``health_status``, the window and the
      EAC-layout log all use, so this cannot place an error a fifth way): every
      counted error has a track, and each such track's first read was replaced on
      AccurateRip's word by a read whose row says AccurateRip verified it;
    * NONE of the counted errors is in a read the album keeps (``kept_tracks``
      empty, ``in_replaced == counted > 0``). A ripping error on a kept read is a
      real finding about the files, and stays a failure (run C's whole-disc rip:
      one skip in track 16, whose first read no read replaced);
    * the replacing reads' own counters show no ``READERR`` and no ``SKIP``. The
      one exception is a report of schema 39 or older, whose replaced track
      carries the superseded read's counters (R61), so they say nothing about the
      read kept, and AccurateRip's match is the evidence that remains; the
      returned reason says so rather than calling the read clean;
    * no track carries an AccurateRip contradiction (the audit then rewords the
      health it prints, and this narrowing does not reach that case);
    * the warning names the tally the placement placed, word for word.

    The grader still requires this warning to be the completion check's ONLY
    finding, so a count that disagrees or is missing still fails. Never raises;
    a malformed report is None.
    """
    from platterpus import rip_audit
    from platterpus.replaced_read_errors import errors_in_replaced_reads

    if not isinstance(report, Mapping):
        return None
    try:
        health = report.get("health_status")
        # The sentence the placement reads as the tally (schema 42 moved the
        # ripper's own words to `ripper_health_status`); the warning must name it.
        tally = report.get(
            "ripper_health_status"
            if "ripper_health_status" in report
            else "health_status"
        )
        if not isinstance(health, str) or not health or health != tally:
            return None
        rows = report.get("tracks")
        if not isinstance(rows, list) or any(
            isinstance(row, Mapping) and row.get("accuraterip_contradiction")
            for row in rows
        ):
            return None
        placed = errors_in_replaced_reads(report)
        if placed is None or placed.kept_tracks or not placed.tracks:
            return None
        if placed.in_kept_reads != 0 or placed.in_replaced != placed.counted:
            return None
        schema = _int(report.get("schema_version"))
        if schema is None:
            return None
        superseded = schema <= _LAST_SCHEMA_WITH_SUPERSEDED_COUNTERS
        if placed.kept_read_errors != 0 and not superseded:
            return None  # the read kept printed an error, or printed no counters
    except (AttributeError, TypeError, ValueError):
        return None
    tracks = ", ".join(str(n) for n in placed.tracks)
    reason = (
        f"expected: the ripper's {placed.counted} ripping error(s) were all in the "
        f"first read of track(s) {tracks}, replaced by a read AccurateRip verified"
    )
    if placed.kept_read_errors == 0:
        reason += ", whose own counters show no read error and no skip"
    else:
        reason += (
            f"; this report (schema {schema}) carries the superseded first read's "
            "counters on those tracks (TASKS R61), so the read kept is vouched for "
            "by AccurateRip alone"
        )
    return ExpectedWarning(rip_audit.ripping_errors_warning(health), reason)
