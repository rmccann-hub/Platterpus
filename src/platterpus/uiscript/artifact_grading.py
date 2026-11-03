"""Pure graders behind the acceptance script's artifact verbs: the rip's RECORD.

**Why these exist.** Every rip leaves a report that already answers most of what
a reader asks: its own self-audit (named checks, among them whether cyanrip's
``-Y`` accepts its own log), the AccurateRip and CTDB verdicts. Until 2026-09-30
**no acceptance step read any of it**, so a Full run could go green over a rip
whose cue had lost every title or whose CTDB lookup failed. The graders that
open the FLAC files are in :mod:`platterpus.uiscript.tag_grading`, and those
that read a verdict the report computed (CTDB's, the gates', the read offset's)
in :mod:`platterpus.uiscript.record_grading`.

**Every grader delegates**: to :mod:`platterpus.rip_audit`'s registry,
:func:`platterpus.verdict.accuraterip_state` and
:data:`platterpus.rip_report.UNFINISHED_RIP_STATUSES`. A second copy would be a
second key for one question (``CLAUDE.md``). Pure and Qt-free, tested against
the committed round-29 reports; nothing here raises on a malformed artifact.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from platterpus.uiscript import expected_warnings

#: Where a rip's report stands, as the artifact verbs need to know it.
SETTLE_ABSENT: Final[str] = "absent"  # no readable report in the folder yet
SETTLE_PENDING: Final[str] = "pending"  # written, but its checks are still landing
SETTLE_SETTLED: Final[str] = "settled"  # finished; every check left a result
SETTLE_UNFINISHED: Final[str] = "unfinished"  # the rip failed or was cancelled

#: The `outcome.status` of a rip that finished. The report writer's own values
#: (`main_window_rip`: "success", "cancelled", "failed"); anything else — an
#: in-progress write — is not yet an outcome.
_FINISHED_STATUS: Final[str] = "success"


@dataclass(frozen=True)
class Grade:
    """One grader's answer: did it hold, and the sentence that says why.

    ``blocked`` is the third answer, for a question the run could not ask
    because a prerequisite it does not own is missing — e.g. MusicBrainz's
    release has no front cover, so there is no embedding to check. It is
    recorded as BLOCKED by the runner, never as a pass: a check satisfied by
    finding nothing is decoration.
    """

    passed: bool
    detail: str
    blocked: bool = False


def report_path(folder: Path) -> Path | None:
    """The folder's ``*.platterpus.json`` that parses as a JSON object, if any."""
    try:
        candidates = sorted(folder.glob("*.platterpus.json"))
    except OSError:
        return None
    for path in candidates:
        if read_report(path) is not None:
            return path
    return None


def read_report(path: Path) -> dict[str, Any] | None:
    """A report as a dict, or ``None`` while it is absent, partial or not JSON."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # a half-written report is "not yet", not a failure
    return loaded if isinstance(loaded, dict) else None


def settle_state(report: Mapping[str, Any] | None) -> str:
    """Where this report stands: one of the ``SETTLE_*`` constants.

    **One predicate, shared** by `expect-verification` and every artifact verb,
    so they cannot disagree about when a rip's record is final. It is the
    report's own backstop read back: a gate that claims ``"ran"`` over an empty
    block is filed by `rip_report` as a dropped-verification issue, and while any
    such issue stands the record is not final. Narrowed rather than trusted — the
    report is written by another process and may be mid-write.
    """
    from platterpus.rip_report import (
        UNFINISHED_RIP_STATUSES,
        VERIFICATION_DROPPED_CODES,
    )

    if report is None:
        return SETTLE_ABSENT
    outcome = report.get("outcome")
    status = outcome.get("status") if isinstance(outcome, dict) else None
    if status in UNFINISHED_RIP_STATUSES:
        return SETTLE_UNFINISHED
    if status != _FINISHED_STATUS:
        return SETTLE_PENDING
    verification = report.get("verification")
    gates = verification.get("gates") if isinstance(verification, dict) else None
    if not isinstance(gates, dict):
        return SETTLE_PENDING
    issues = report.get("issues")
    codes = {
        issue.get("code")
        for issue in (issues if isinstance(issues, list) else [])
        if isinstance(issue, dict)
    }
    return SETTLE_PENDING if codes & VERIFICATION_DROPPED_CODES else SETTLE_SETTLED


def derived_verification_refusal(report: Mapping[str, Any] | None) -> str | None:
    """Why a settled report's derived-file verification did not run, or None.

    **One predicate, shared** by `expect-derived-output` and `expect-verification`
    (run C, 2026-10-22). The MP3, WavPack and WAV verifies gave up waiting for
    their transcodes and recorded ``"not run — no mp3 files found to verify"``,
    and both verbs passed: one counted the files that appeared a minute later,
    the other needed only *some* gate to have run. A section that asks for a
    derived format has not verified it when its verification did not run.

    None when the gate says the check ran, was never asked for (``flac-only``),
    or is absent (an older report, or not a derived rip). Never raises.
    """
    from platterpus.verification_gates import (
        CUT_SHORT_GATE,
        GATE_RAN_FAILED,
        NOT_RUN_PREFIX,
    )

    verification = report.get("verification") if report is not None else None
    gates = verification.get("gates") if isinstance(verification, dict) else None
    state = gates.get("derived") if isinstance(gates, dict) else None
    if not isinstance(state, str):
        return None
    if state.startswith(NOT_RUN_PREFIX) or state == CUT_SHORT_GATE:
        return (
            f"the derived-file verification did not run: its gate reads {state!r}. "
            "The derived files were asked for, so their verification is owed, and "
            "an absent result is not a passed one."
        )
    if state == GATE_RAN_FAILED:  # C1, 2026-11-03: it ran and a file failed it
        return (
            "the derived-file verification ran and FAILED: a derived file did not "
            "decode, or is not bit-identical to its FLAC master (the report's "
            "verification.derived names which)."
        )
    return None


# --- expect-album-audit -------------------------------------------------------

#: The handshake check's name in :data:`platterpus.rip_audit.CHECKS`.
_HANDSHAKE_CHECK: Final[str] = "handshake_note"


def grade_album_audit(
    path: Path,
    only: Sequence[str] = (),
    report: Mapping[str, Any] | None = None,
) -> Grade:
    """Grade the report's own self-audit, re-run now against the files on disk.

    Passes when every check asked about (all of them when ``only`` is empty)
    **ran**, raised **no warning**, and said **at least one thing was ok** — the
    last because a check that could only reach "not determined" (no EAC log was
    written, no audio file was found) has not verified anything. Notes beside an
    ``ok`` are allowed: the handshake check notes an open round on every rip, and
    that is the record being accurate.

    **One warning is expected rather than failed**: the handshake check's
    open-round warning on the build under review, when ``report`` shows it is
    that build (:func:`~platterpus.uiscript.expected_warnings.expected_open_round_warning`). It then counts as the
    check's verified answer, since the binary's statement and our verdict were
    compared and agree, and the passing sentence names it.

    Measured first: every check reached ``ok`` on each finished round-29 rip
    (``docs/handshake/artifactsround29/*report.json``), a floor already met.
    """
    from platterpus import rip_audit

    names = [check.name for check in rip_audit.CHECKS]
    unknown = [name for name in only if name not in names]
    if unknown:
        return Grade(
            False,
            f"no audit check is called {', '.join(unknown)} — the checks are "
            f"{', '.join(names)}",
        )
    wanted = list(only) or names
    album = rip_audit.audit_album(path)
    if not album.by_check:
        texts = "; ".join(f.text for f in album.findings) or "no finding at all"
        return Grade(False, f"the audit could not run on {path.name}: {texts}")
    expected = expected_warnings.expected_open_round_warning(report)
    excused: list[str] = []
    problems: list[str] = []
    for name in wanted:
        if name in album.skipped_checks or name not in album.by_check:
            problems.append(f"{name} did not run")
            continue
        findings = album.by_check[name]
        warned = [f.text for f in findings if f.level == rip_audit.LEVEL_WARN]
        verified = any(f.level == rip_audit.LEVEL_OK for f in findings)
        if name == _HANDSHAKE_CHECK and expected:
            open_round = [
                w for w in warned if w.startswith(rip_audit.OPEN_ROUND_WARNING)
            ]
            if open_round:
                warned = [w for w in warned if w not in open_round]
                excused.append(f"{name}'s open-round warning {expected}")
                verified = True
        if warned:
            problems.append(f"{name} warned: {' / '.join(warned)}")
        elif not verified:
            said = " / ".join(f.text for f in findings)
            problems.append(f"{name} verified nothing ({said})")
    if problems:
        return Grade(False, "; ".join(problems))
    if excused:
        return Grade(
            True,
            f"all {len(wanted)} audit check(s) ran and reached ok, and the only "
            f"warning was {'; '.join(excused)} ({', '.join(wanted)})",
        )
    return Grade(
        True,
        f"all {len(wanted)} audit check(s) ran, none warned, each reached ok "
        f"({', '.join(wanted)})",
    )


# --- expect-accuraterip -------------------------------------------------------

#: The states in which AccurateRip was ASKED and answered. `absent` counts: the
#: database was consulted and does not hold the disc, which is a determined
#: answer about the disc, not a fault in the rip. `not-checked` and `no-data`
#: are the plumbing failing — no lookup, or a lookup that left no result.
_AR_DETERMINED: Final[frozenset[str]] = frozenset(
    {"verified", "offset-variant", "no-match", "absent"}
)
#: Which of two columns (v1, v2) a track is summarised by: the best one.
_AR_RANK: Final[tuple[str, ...]] = (
    "verified",
    "offset-variant",
    "no-match",
    "absent",
    "no-data",
    "not-checked",
)


def _track_ar_state(track: object) -> str:
    from platterpus.verdict import accuraterip_state

    offset = getattr(track, "accuraterip_offset", None)
    lookup = getattr(track, "accuraterip_lookup", None)
    states = [
        accuraterip_state(getattr(track, column, None), offset, lookup)
        for column in ("accuraterip_v1", "accuraterip_v2")
    ]
    return min(states, key=lambda s: _AR_RANK.index(s) if s in _AR_RANK else 99)


def grade_accuraterip(rip_log: object, report: Mapping[str, Any]) -> Grade:
    """Every ripped audio track has an AccurateRip answer, and the report agrees.

    **Passes on any disc**, because the script runs on "any ordinary audio CD":
    a disc AccurateRip does not hold, or a track that matched only one frame, is
    a determined answer. What fails is AccurateRip never having been asked (or
    having said nothing) for a track, and **the report disagreeing with the log
    on disk** about which tracks verified — the report is what a reader keeps,
    and it is rendered from a parse of the log that can be stale (the 2026-09-09
    defect `_rip_log_from_disk` exists for).
    """
    from platterpus.data_tracks import is_data_track
    from platterpus.parsers.rip_log import track_accuraterip_verified

    # The shared predicate the verdict asks, so the grade and the banner leave out
    # the same tracks (TASKS R13 replaced a restated substring check here).
    tracks = [t for t in (getattr(rip_log, "tracks", ()) or ()) if not is_data_track(t)]
    if not tracks:
        return Grade(
            False,
            "the log on disk carries no audio track, so there is nothing to grade",
        )
    states = {int(getattr(t, "number", 0)): _track_ar_state(t) for t in tracks}
    undetermined = sorted(n for n, s in states.items() if s not in _AR_DETERMINED)
    reported = {
        entry.get("number"): entry.get("accuraterip_verified")
        for entry in (report.get("tracks") or [])
        if isinstance(entry, dict)
    }
    disagree = sorted(
        int(getattr(t, "number", 0))
        for t in tracks
        if reported.get(getattr(t, "number", None)) is not track_accuraterip_verified(t)
    )
    tally: dict[str, list[int]] = {}
    for number, state in sorted(states.items()):
        tally.setdefault(state, []).append(number)
    # The transcript's words, not the verdict's keys: `offset-variant` names a
    # cause our screens stopped naming on 2026-09-24 (plan of record, Appendix I
    # §2, defect 5). One map, shared with `record-accuracy`'s transcript.
    from platterpus.uiscript.accuracy_grading import STATE_WORDS

    summary = "; ".join(
        f"{STATE_WORDS.get(state, state)}: {', '.join(str(n) for n in numbers)}"
        for state, numbers in tally.items()
    )
    problems: list[str] = []
    if undetermined:
        problems.append(
            f"AccurateRip gave no answer for track(s) "
            f"{', '.join(str(n) for n in undetermined)} (not looked up, or no result)"
        )
    if disagree:
        problems.append(
            f"the report and the log on disk disagree about whether track(s) "
            f"{', '.join(str(n) for n in disagree)} verified"
        )
    if problems:
        return Grade(False, "; ".join(problems) + f" [{summary}]")
    return Grade(
        True, f"{len(tracks)} track(s), each with an AccurateRip answer [{summary}]"
    )
