"""Compare two rip reports of the same disc — "you've ripped this before".

Why this exists (a real-hardware finding, 2026-07-09): Platterpus is stateless
per rip, so it can't tell you a *re-rip* came out different from the last one.
A maintainer re-ripped The Police — *Every Breath You Take: The Classics* twice;
12 of 14 tracks were byte-for-byte identical across both rips, but tracks 3 and
5 differed — and track 3 had been a confidence-200 AccurateRip match the first
time and was only an offset-variant match the second. That regression was
invisible to the tool and only surfaced by diffing two ``.platterpus.json``
reports by hand. This module is that diff, made first-class.

Design (mirrors the parser/verdict discipline):

* **Pure and never-raises.** :func:`compare_reports` takes two already-loaded
  report dicts (as written by :mod:`platterpus.rip_report`) and returns a
  :class:`RipComparison`; it degrades to a best-effort result on partial/odd
  input rather than blowing up a post-rip path. The filesystem helpers
  (:func:`load_report`, :func:`find_prior_report`) are the only I/O and are
  equally defensive.
* **One definition of "verified".** Track trust is read from the report's own
  ``accuraterip_verified`` flag and ``accuraterip.offset_450`` block — the same
  values the banner and the JSON already agree on (see
  docs/ux-design-principles.md #1) — so a comparison can never contradict the
  rip it compares.
* **Honest about "same disc".** It keys on the TOC-derived MusicBrainz Disc ID
  first (stable across re-rips), then the CDDB ID, then the MusicBrainz release
  id; when none is available it still compares positionally but says so.

The best-of-both assembler (:func:`best_of_plan` / :func:`assemble_best_of`)
builds on the same per-track "which side is the better master" call.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from platterpus.build_info import self_invocation
from platterpus.paths import LOG_PATH

log = logging.getLogger(__name__)


# Cap on how many report files a library scan will load, so discovery can't
# stall on a pathologically huge library. One report per album, and loading a
# small JSON is cheap, so this comfortably covers a large collection; if it's
# ever hit we log it (never silently truncate — docs/testing.md).
_MAX_SCAN_REPORTS: int = 5000


# --- Per-track AR status ranking --------------------------------------------
#
# Higher = more trustworthy as an archival master. Used to decide, when two
# rips of a track differ, which read to prefer. "verified" is an exact
# AccurateRip match; "offset_variant" matched only the +450 offset pressing
# (partially accurate); "not_in_db" is a real CRC nobody else has confirmed;
# "absent" means the track wasn't in that report at all.
STATUS_VERIFIED: str = "verified"
STATUS_OFFSET_VARIANT: str = "offset_variant"
STATUS_NOT_IN_DB: str = "not_in_db"
STATUS_ABSENT: str = "absent"

_STATUS_RANK: dict[str, int] = {
    STATUS_VERIFIED: 3,
    STATUS_OFFSET_VARIANT: 2,
    STATUS_NOT_IN_DB: 1,
    STATUS_ABSENT: 0,
}

# Which report a differing track's better master lives in.
SIDE_A: str = "a"
SIDE_B: str = "b"
SIDE_EQUAL: str = "equal"  # both reads are byte-identical (either is fine)
SIDE_UNKNOWN: str = "unknown"  # differ, but no basis to prefer one


@dataclass(frozen=True)
class TrackComparison:
    """One track's diff across the two rips."""

    number: int
    title: str
    crc_a: str | None
    crc_b: str | None
    status_a: str
    status_b: str
    confidence_a: int | None
    confidence_b: int | None
    # True only when both reads are present AND byte-identical (same Copy CRC).
    identical: bool
    # Which side is the better archival master for THIS track, and why.
    better: str
    reason: str


@dataclass(frozen=True)
class RipComparison:
    """The full two-rip comparison."""

    label_a: str
    label_b: str
    disc_key_a: str | None
    disc_key_b: str | None
    # True/False when both disc keys are known; None when at least one is
    # missing (compared positionally, see `notes`).
    same_disc: bool | None
    tracks: tuple[TrackComparison, ...]
    identical_count: int
    differing_count: int
    total: int
    a_better_tracks: tuple[int, ...]
    b_better_tracks: tuple[int, ...]
    # "ok" (all compared tracks identical), "warn" (some differ), "neutral"
    # (nothing to compare / different discs).
    headline_level: str
    summary: str
    notes: tuple[str, ...] = ()


# --- Reading report fields (defensive; never raises) ------------------------


def _ar_match_confidence(ar: object) -> int | None:
    """Return a positive AccurateRip confidence (>= 1) from an AR sub-dict, else
    None. Mirrors ``accuraterip_is_match``'s confidence>=1 rule on the SERIALIZED
    report shape (``{"confidence": N, ...}``)."""
    if not isinstance(ar, dict):
        return None
    conf = ar.get("confidence")
    if isinstance(conf, int) and conf >= 1:
        return conf
    return None


def _track_status(track: dict) -> tuple[str, int | None]:
    """Classify one report track: ``(status, confidence)``.

    Reads the report's own ``accuraterip_verified`` flag first (the shared
    definition of "verified"), then the offset-variant block, then falls back to
    "not in database". Pure; tolerates missing keys."""
    accuraterip = track.get("accuraterip") if isinstance(track, dict) else None
    accuraterip = accuraterip if isinstance(accuraterip, dict) else {}
    if track.get("accuraterip_verified"):
        # Confidence = the best of v1/v2 that actually matched.
        conf = None
        for key in ("v1", "v2"):
            c = _ar_match_confidence(accuraterip.get(key))
            if c is not None and (conf is None or c > conf):
                conf = c
        return STATUS_VERIFIED, conf
    offset_conf = _ar_match_confidence(accuraterip.get("offset_450"))
    if offset_conf is not None:
        return STATUS_OFFSET_VARIANT, offset_conf
    return STATUS_NOT_IN_DB, None


def _track_crc(track: dict) -> str | None:
    crc = track.get("copy_crc") if isinstance(track, dict) else None
    if isinstance(crc, str) and crc.strip():
        return crc.strip().upper()
    return None


def _track_title(track: dict, number: int) -> str:
    """A short human label for a track (filename stem, else "Track NN")."""
    filename = track.get("filename") if isinstance(track, dict) else None
    if isinstance(filename, str) and filename.strip():
        stem = Path(filename).stem
        if stem:
            return stem
    return f"Track {number:02d}"


# Disc-identity fields in preference order, strongest first. The first TWO are
# TOC-derived (per physical disc, stable across re-rips); the release id is
# weaker (two pressings can share a release, and a release can be merged/split
# in MusicBrainz) but is all a pre-v9 report carries.
_DISC_KEY_PRIORITY: tuple[str, ...] = (
    "musicbrainz_disc_id",
    "cddb_id",
    "musicbrainz_release_id",
)


def _disc_fields(report: dict) -> dict[str, str]:
    """All disc-identity fields present in a report: ``{field: value}``.

    ``musicbrainz_disc_id`` / ``cddb_id`` come from the ``rip`` block (v9+),
    ``musicbrainz_release_id`` from the ``disc`` block (all versions). Pure;
    tolerates any shape."""
    out: dict[str, str] = {}
    if not isinstance(report, dict):
        return out
    rip = report.get("rip")
    if isinstance(rip, dict):
        for key in ("musicbrainz_disc_id", "cddb_id"):
            value = rip.get(key)
            if isinstance(value, str) and value.strip():
                out[key] = value.strip()
    disc = report.get("disc")
    if isinstance(disc, dict):
        value = disc.get("musicbrainz_release_id")
        if isinstance(value, str) and value.strip():
            out["musicbrainz_release_id"] = value.strip()
    return out


def disc_key(report: dict) -> str | None:
    """The strongest available single "same physical disc" key, for display.

    Returns the value of the highest-priority field present (see
    ``_DISC_KEY_PRIORITY``), or None when none is present (an unknown-disc rip
    with no IDs). For *deciding whether two reports are the same disc*, use
    :func:`same_disc` — it compares the strongest field the two reports SHARE,
    which ``disc_key`` alone can't (a v8 report keys on the release id while a v9
    report keys on the disc id, so a naive key-equality check would wrongly call
    the first re-rip after an upgrade "different discs"). Pure."""
    fields = _disc_fields(report)
    for key in _DISC_KEY_PRIORITY:
        if key in fields:
            return fields[key]
    return None


def same_disc(report_a: dict, report_b: dict) -> bool | None:
    """Whether two reports are the same physical disc. Pure; never raises.

    Decides by the **strongest identity field the two reports both carry**: if
    both have a MusicBrainz Disc ID, that's decisive (differing → different
    discs, even for two discs of one box set that share a release); else the
    CDDB ID; else the release id (weaker, but it's all pre-v9 reports have).
    Returns None when the two share no comparable field (can't confirm). This is
    what makes a v8-prior vs v9-current re-rip compare correctly — they still
    share the release id even though their strongest keys differ in *type*."""
    fields_a = _disc_fields(report_a)
    fields_b = _disc_fields(report_b)
    for key in _DISC_KEY_PRIORITY:
        if key in fields_a and key in fields_b:
            return fields_a[key] == fields_b[key]
    return None


def report_label(report: dict, *, fallback: str = "") -> str:
    """A short human label for a report: "vX.Y.Z · <rip date>", best-effort."""
    if not isinstance(report, dict):
        return fallback
    bits: list[str] = []
    gen = report.get("generator")
    if isinstance(gen, dict) and isinstance(gen.get("version"), str):
        bits.append(f"v{gen['version']}")
    # Prefer the rip's own creation date, else the report's generated_at.
    rip = report.get("rip")
    when = None
    if isinstance(rip, dict) and isinstance(rip.get("creation_date"), str):
        when = rip["creation_date"]
    elif isinstance(report.get("generated_at"), str):
        when = report["generated_at"]
    if when:
        bits.append(when)
    return " · ".join(bits) if bits else fallback


# --- Is this report a usable baseline? (`outcome.status`) --------------------
#
# Every report carries the PROCESS result of the rip that wrote it in
# ``outcome.status`` (built by ``rip_report.build_outcome``): "success",
# "cancelled", "failed" — or "in_progress".
#
# That last one is NOT a rip result. The rip worker re-writes the report after
# every completed track purely for durability
# (``rip_worker._write_incremental_report``) and stamps it "in_progress"; the GUI
# overwrites it with the real status when the rip actually ends. So an
# "in_progress" report still sitting on disk means the rip that wrote it never
# ended in this program's hands — the window was closed mid-rip, the machine lost
# power, the process was killed — and the snapshot then stays in that album folder
# forever. Reading one back as "your previous rip of this disc" produced the bug
# this classification exists to fix: a later clean re-rip was diffed against the
# abandoned three-track snapshot and warned about "track(s) 4…14 the previous rip
# didn't have" on a rip that was in fact perfect.
OUTCOME_SUCCESS: str = "success"
OUTCOME_CANCELLED: str = "cancelled"
OUTCOME_FAILED: str = "failed"
OUTCOME_IN_PROGRESS: str = "in_progress"

# Three completeness classes, because each one wants a different policy.
#
# COMPLETE — the rip ran to the end. The ideal baseline; compared as-is.
# PARTIAL  — a rip that really ran and really stopped short (cancelled/failed).
#            Its tracks are genuine reads with genuine CRCs, so it is still a
#            valid baseline *for the tracks it got* — it just carries no evidence
#            about the ones it never reached. Used, ranked below a COMPLETE prior,
#            and always labelled: never silently discarded (this is exactly the
#            case the whole feature exists for — a re-rip after a cancel).
# ABANDONED — an unfinalised mid-rip snapshot. Not a rip record at all, so it is
#            not auto-selected as a baseline (see `find_prior_report`).
COMPLETENESS_COMPLETE: str = "complete"
COMPLETENESS_PARTIAL: str = "partial"
COMPLETENESS_ABANDONED: str = "abandoned"


def outcome_status(report: Mapping[str, object]) -> str:
    """The report's ``outcome.status``, stripped + case-folded; ``""`` when absent.

    ``""`` is a REAL, supported answer, not an error: the ``outcome`` block was
    added in schema v7, so every older ``.platterpus.json`` still in a
    long-standing library has no ``outcome`` at all — and this module's whole job
    is reading files written by older versions. See
    :func:`_completeness_from_status` for what absence is taken to mean.

    Takes a ``Mapping`` (not ``dict``) so a ``report_types.RipReport`` TypedDict
    can be passed straight in; note the deliberate absence of the ``x or {}``
    idiom, which silently breaks ``.get()`` on a TypedDict. Pure; never raises.
    """
    if not isinstance(report, dict):
        return ""
    outcome = report.get("outcome")
    if not isinstance(outcome, dict):
        return ""
    status = outcome.get("status")
    return status.strip().casefold() if isinstance(status, str) else ""


def _completeness_from_status(status: str) -> str:
    """Map an ``outcome.status`` string to one of the ``COMPLETENESS_*`` classes.

    The two judgement calls, both deliberate:

    * **No status at all → COMPLETE.** A pre-v7 report has no ``outcome`` block,
      and the only thing that ever wrote a full report in those versions was the
      GUI's *rip-finished* handler — an unfinished rip left no report to find. So
      absence means "written at the end of a rip", and treating it as unusable
      instead would throw away every genuine prior in an older library (and break
      the v8-prior/v9-current re-rip case this module is built around).
    * **An unrecognised status → PARTIAL, not COMPLETE.** If a future version adds
      another way for a rip to stop early, the conservative reading keeps its
      tracks usable while refusing to treat them as evidence about the whole disc.
      Guessing "complete" for an unknown status would quietly re-open this bug.
    """
    if status == OUTCOME_IN_PROGRESS:
        return COMPLETENESS_ABANDONED
    if status in ("", OUTCOME_SUCCESS):
        return COMPLETENESS_COMPLETE
    return COMPLETENESS_PARTIAL


def report_completeness(report: Mapping[str, object]) -> str:
    """Classify a report as a comparison baseline: complete / partial / abandoned.

    The single public entry point for that question, so the scan
    (:func:`find_prior_report`) and the diff (:func:`compare_reports`) can never
    disagree about whether a report is a finished rip. Pure; never raises."""
    return _completeness_from_status(outcome_status(report))


def _stopped_phrase(status: str) -> str:
    """Human clause naming *how* a rip stopped short, for a caveat sentence."""
    if status == OUTCOME_CANCELLED:
        return "was cancelled before it finished"
    if status == OUTCOME_FAILED:
        return "failed before it finished"
    if status == OUTCOME_IN_PROGRESS:
        return "never finished — its report is an unfinalised mid-rip snapshot"
    # An unrecognised status: quote it rather than inventing a story about it.
    return f"did not report success (its outcome says {status!r})"


# --- The comparison ---------------------------------------------------------


def _track_converged(track: object) -> bool | None:
    """Whether this track's secure re-read CONVERGED — tri-state, read defensively.

    `None` means "never re-read", which is a different fact from `False` ("re-read
    and never agreed with itself"). Collapsing them would let an unattempted read
    look like a failed one and vice versa, and the tiebreak above depends on the
    distinction. Accepts a mapping or an object because the comparison is fed both
    parsed logs and JSON reports.
    """
    if track is None:
        return None
    if isinstance(track, dict):
        value = track.get("secure_rerip_converged")
    else:
        value = getattr(track, "secure_rerip_converged", None)
    return value if isinstance(value, bool) else None


def _decide_better(
    crc_a: str | None,
    crc_b: str | None,
    status_a: str,
    status_b: str,
    conf_a: int | None,
    conf_b: int | None,
    converged_a: bool | None = None,
    converged_b: bool | None = None,
) -> tuple[str, str]:
    """Decide which side is the better master for one track: ``(side, reason)``.

    Rules, in order:
    * A track missing from one side → the present side wins.
    * Byte-identical reads → ``equal`` (either is fine).
    * Otherwise prefer the stronger AR status (verified > offset-variant >
      not-in-DB); on a tie prefer the higher confidence; **on a further tie prefer
      the read that CONVERGED** across secure re-reads; only then → ``unknown``.

    **WHY CONVERGENCE IS A TIEBREAK, AND WHY IT WAS MISSING.** Found on real
    hardware, 2026-08-05. Two rips of the same disc both read track 5 as
    offset-variant at confidence 200 — identical status, identical confidence — so
    this function returned ``unknown``: *"can't tell which read is correct."* But
    the two reads were **not** equally supported. One had converged across three
    secure re-reads; the other was a single read with ``Secure re-read: not
    attempted``. And EAC, independently, twice, produced the converged one
    (`E0036697`) and never the other (`6902BCF0`).

    So "no basis to choose" was false: **a read corroborated by repetition on this
    drive and this disc is better evidence than one nobody checked.** AccurateRip
    confidence cannot express that — it counts how many *strangers* submitted a
    matching CRC, which is the same number for both reads here and says nothing
    about which of *our* two reads is sound.

    Ranked BELOW confidence deliberately: confidence is corroboration by many
    independent rippers, convergence is corroboration by one drive repeating
    itself. Convergence only breaks ties the earlier rules leave open, so it can
    never overturn an AccurateRip verdict — it only replaces a shrug.
    """
    if crc_a is None and crc_b is None:
        return SIDE_UNKNOWN, "neither rip recorded this track"
    if crc_a is None:
        return SIDE_B, "only the second rip has this track"
    if crc_b is None:
        return SIDE_A, "only the first rip has this track"
    if crc_a == crc_b:
        return SIDE_EQUAL, "both rips are byte-for-byte identical"

    rank_a = _STATUS_RANK.get(status_a, 0)
    rank_b = _STATUS_RANK.get(status_b, 0)
    if rank_a != rank_b:
        side = SIDE_A if rank_a > rank_b else SIDE_B
        winner, loser = (
            (status_a, status_b) if rank_a > rank_b else (status_b, status_a)
        )
        return side, f"reads differ; {_describe_status(winner)} beats " + (
            _describe_status(loser)
        )
    # Same status, differing reads: use confidence as a tiebreak where we have it.
    ca = conf_a if isinstance(conf_a, int) else -1
    cb = conf_b if isinstance(conf_b, int) else -1
    if ca != cb:
        side = SIDE_A if ca > cb else SIDE_B
        return side, f"reads differ; both {_describe_status(status_a)}, but " + (
            f"confidence {max(ca, cb)} beats {min(ca, cb)}"
        )
    # CONVERGENCE. Same status, same confidence, differing bytes — but if exactly
    # one read was corroborated by repeating it, that one is the better master.
    # `is True` / `is not True` on purpose: the flag is TRI-STATE, and "not
    # attempted" (None) must not be read as "failed to converge" (False). Only an
    # affirmative convergence on exactly one side breaks the tie.
    if (converged_a is True) != (converged_b is True):
        side = SIDE_A if converged_a is True else SIDE_B
        return side, (
            f"reads differ; both {_describe_status(status_a)} with equal confidence, "
            "but one read converged across secure re-reads and the other was never "
            "re-read — the corroborated read is the better master"
        )
    # No basis to choose. Only mention "equal confidence" when both sides
    # actually HAVE a confidence — a not-in-DB track has none, so saying "equal
    # confidence" there would be meaningless.
    detail = (
        " with equal confidence" if (conf_a is not None and conf_b is not None) else ""
    )
    return (
        SIDE_UNKNOWN,
        f"reads differ; both {_describe_status(status_a)}{detail} — can't tell "
        "which read is correct (re-rip to break the tie)",
    )


def _describe_status(status: str) -> str:
    return {
        STATUS_VERIFIED: "an exact AccurateRip match",
        STATUS_OFFSET_VARIANT: "an offset-variant match",
        STATUS_NOT_IN_DB: "not in the AccurateRip database",
        STATUS_ABSENT: "absent",
    }.get(status, status)


def compare_reports(
    report_a: dict,
    report_b: dict,
    *,
    label_a: str = "",
    label_b: str = "",
) -> RipComparison:
    """Compare two rip reports track-by-track. Pure; never raises.

    ``report_a``/``report_b`` are report dicts (from
    :func:`platterpus.rip_report.build_report`, or loaded from a
    ``.platterpus.json``). Labels default to a best-effort "vX · date" derived
    from each report. The result is a :class:`RipComparison` whose per-track
    ``better`` says which read to keep and whose ``summary`` is a one-liner ready
    for a banner or a CLI.
    """
    try:
        return _compare(report_a, report_b, label_a, label_b)
    except Exception:  # noqa: BLE001 — a comparison must never crash a caller
        log.exception("rip comparison failed; returning an empty comparison")
        return RipComparison(
            label_a=label_a or "rip A",
            label_b=label_b or "rip B",
            disc_key_a=None,
            disc_key_b=None,
            same_disc=None,
            tracks=(),
            identical_count=0,
            differing_count=0,
            total=0,
            a_better_tracks=(),
            b_better_tracks=(),
            headline_level="neutral",
            summary="Could not compare these two rips.",
            notes=(
                f"the comparison hit an unexpected error — see the log at {LOG_PATH}",
            ),
        )


def _report_tracks_by_number(report: dict) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for track in report.get("tracks") or ():
        if isinstance(track, dict) and isinstance(track.get("number"), int):
            out[track["number"]] = track
    return out


def _compare(
    report_a: dict, report_b: dict, label_a: str, label_b: str
) -> RipComparison:
    label_a = label_a or report_label(report_a, fallback="rip A")
    label_b = label_b or report_label(report_b, fallback="rip B")
    key_a = disc_key(report_a)
    key_b = disc_key(report_b)
    same = same_disc(report_a, report_b)
    notes: list[str] = []
    if same is False:
        notes.append(
            "these reports are for DIFFERENT discs (their disc IDs differ) — "
            "a track-by-track comparison is probably meaningless"
        )
    elif same is None:
        notes.append(
            "could not confirm these are the same disc (no shared disc ID) — "
            "compared positionally by track number"
        )

    # How complete each side is, per its own `outcome.status`. This is what keeps
    # a stopped-short rip from being reported as a REGRESSION: a track the
    # incomplete side never reached is missing *by definition*, so calling it out
    # as "a track the previous rip didn't have" describes the previous rip's
    # cancel, not anything wrong with this one. `compare_reports` is also called
    # straight from the CLI on two paths the user names, which is why the check
    # lives here (in the diff) as well as in the scan — an `--compare` against an
    # abandoned snapshot gets the caveat instead of the false warning.
    outcome_a = outcome_status(report_a)
    outcome_b = outcome_status(report_b)
    a_incomplete = _completeness_from_status(outcome_a) != COMPLETENESS_COMPLETE
    b_incomplete = _completeness_from_status(outcome_b) != COMPLETENESS_COMPLETE

    tracks_a = _report_tracks_by_number(report_a)
    tracks_b = _report_tracks_by_number(report_b)
    numbers = sorted(set(tracks_a) | set(tracks_b))

    rows: list[TrackComparison] = []
    identical = 0
    differing = 0
    a_better: list[int] = []
    b_better: list[int] = []
    only_a: list[int] = []  # tracks present in the previous rip but not this one
    only_b: list[int] = []  # tracks present in this rip but not the previous
    for number in numbers:
        ta = tracks_a.get(number)
        tb = tracks_b.get(number)
        crc_a = _track_crc(ta) if ta is not None else None
        crc_b = _track_crc(tb) if tb is not None else None
        status_a, conf_a = (
            _track_status(ta) if ta is not None else (STATUS_ABSENT, None)
        )
        status_b, conf_b = (
            _track_status(tb) if tb is not None else (STATUS_ABSENT, None)
        )
        is_identical = crc_a is not None and crc_a == crc_b
        better, reason = _decide_better(
            crc_a,
            crc_b,
            status_a,
            status_b,
            conf_a,
            conf_b,
            _track_converged(ta),
            _track_converged(tb),
        )
        title = _track_title(
            ta if ta is not None else (tb if tb is not None else {}), number
        )
        rows.append(
            TrackComparison(
                number=number,
                title=title,
                crc_a=crc_a,
                crc_b=crc_b,
                status_a=status_a,
                status_b=status_b,
                confidence_a=conf_a,
                confidence_b=conf_b,
                identical=is_identical,
                better=better,
                reason=reason,
            )
        )
        # Classify by presence: both sides (identical/differing), or one only.
        if crc_a is not None and crc_b is not None:
            if is_identical:
                identical += 1
            else:
                differing += 1
                if better == SIDE_A:
                    a_better.append(number)
                elif better == SIDE_B:
                    b_better.append(number)
        elif crc_a is not None:
            only_a.append(number)
        elif crc_b is not None:
            only_b.append(number)

    # Tracks present only on the side that never finished are EXPECTED, so they
    # are dropped from the *reported* anomalies (the rows themselves keep the
    # full truth — this only governs the warning). Reported separately from
    # `only_a`/`only_b` rather than by not collecting them, so the caveat below
    # can still say how many tracks the short side covered.
    reported_only_a = [] if b_incomplete else only_a
    reported_only_b = [] if a_incomplete else only_b
    caveat = _incomplete_caveat(
        a_incomplete=a_incomplete,
        b_incomplete=b_incomplete,
        outcome_a=outcome_a,
        outcome_b=outcome_b,
        count_a=len(tracks_a),
        count_b=len(tracks_b),
    )
    if caveat:
        # The GUI banner renders only `summary` (ui/rip_progress.comparison_banner_text),
        # so a caveat that lived only in `notes` would never reach the person who
        # needs it. It goes in both: summary for the banner, notes for the CLI.
        notes.append(caveat)

    total = len(numbers)
    if total == 0:
        headline_level = "neutral"
        summary = "Neither report has any tracks to compare."
    elif identical == 0 and differing == 0:
        # No track is present in BOTH reports (disjoint numbering, or a prior
        # report with an empty/partial track list). Nothing was actually
        # compared — never claim an "identical" re-rip in that case.
        headline_level = "neutral"
        summary = "No tracks in common to compare between the two rips."
    elif differing == 0 and not reported_only_a and not reported_only_b:
        headline_level = "ok"
        if a_incomplete or b_incomplete:
            # True and precise: every track the two rips SHARE matched, but the
            # short side never covered the whole disc, so "identical to the
            # previous rip" full stop would overclaim.
            summary = (
                f"All {identical} track(s) the two rips have in common are "
                "byte-for-byte identical."
            )
        else:
            summary = (
                f"All {identical} track(s) are byte-for-byte identical to the "
                "previous rip."
            )
    else:
        # Something changed: differing content, and/or the track SET differs (a
        # dropped or added track). Both are worth surfacing, not hiding behind a
        # green "identical" verdict.
        headline_level = "warn"
        summary = _change_summary(
            identical, differing, a_better, b_better, reported_only_a, reported_only_b
        )
    if caveat:
        summary = f"{summary} {caveat}"

    return RipComparison(
        label_a=label_a,
        label_b=label_b,
        disc_key_a=key_a,
        disc_key_b=key_b,
        same_disc=same,
        tracks=tuple(rows),
        identical_count=identical,
        differing_count=differing,
        total=total,
        a_better_tracks=tuple(a_better),
        b_better_tracks=tuple(b_better),
        headline_level=headline_level,
        summary=summary,
        notes=tuple(notes),
    )


def _incomplete_caveat(
    *,
    a_incomplete: bool,
    b_incomplete: bool,
    outcome_a: str,
    outcome_b: str,
    count_a: int,
    count_b: int,
) -> str:
    """The sentence that labels a comparison against a rip that stopped short.

    A partial prior is genuinely useful — its tracks are real reads with real
    CRCs — so it is compared rather than discarded. But comparing against it and
    *saying nothing* would be the mirror image of the bug: the user would see a
    green "identical" headline for a disc only a third of which was ever
    compared. This is the caveat that keeps the result honest, and it is deliberately
    stated in track counts (the number the user can check) rather than adjectives.
    Returns "" when both sides finished. Pure; never raises."""
    parts: list[str] = []
    if a_incomplete:
        parts.append(
            f"Note: the previous rip {_stopped_phrase(outcome_a)}, so it covers "
            f"{count_a} track(s) against this rip's {count_b} — the rest are absent "
            "from it by definition, not lost by this rip."
        )
    if b_incomplete:
        parts.append(
            f"Note: this rip {_stopped_phrase(outcome_b)}, so it covers {count_b} "
            f"track(s) against the previous rip's {count_a}."
        )
    return " ".join(parts)


def _change_summary(
    identical: int,
    differing: int,
    a_better: list[int],
    b_better: list[int],
    only_a: list[int],
    only_b: list[int],
) -> str:
    """One-line summary when something changed — differing content and/or a
    changed track set (a dropped or added track). Names the better side for
    differing tracks and calls out any track present in only one rip."""
    parts: list[str] = []
    if identical:
        parts.append(f"{identical} track(s) identical")
    if differing:
        parts.append(f"{differing} differ from the previous rip")
    if only_a:
        listed = ", ".join(str(n) for n in only_a)
        parts.append(f"track(s) {listed} are in the previous rip but not this one")
    if only_b:
        listed = ", ".join(str(n) for n in only_b)
        parts.append(f"this rip has track(s) {listed} the previous rip didn't")
    if a_better:
        listed = ", ".join(str(n) for n in a_better)
        parts.append(f"the previous rip is the better master for track(s) {listed}")
    if b_better:
        listed = ", ".join(str(n) for n in b_better)
        parts.append(f"this rip is the better master for track(s) {listed}")
    return "; ".join(parts) + "."


# --- Filesystem helpers (I/O; still never raise) ----------------------------


def load_report(path: Path) -> dict | None:
    """Load a ``.platterpus.json`` report. Returns None on any error.

    Never raises — a missing/torn/foreign JSON just yields None (the callers
    treat "no comparable report" as a normal, silent outcome)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        data = json.loads(text)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def find_prior_report(
    current_report_path: Path,
    search_root: Path,
    *,
    current_report: dict | None = None,
    extra_roots: Sequence[Path] = (),
) -> Path | None:
    """Find a prior report for the SAME disc as ``current_report_path``.

    Scans ``search_root`` — plus any ``extra_roots`` (e.g. the library folder
    the auto-move feature relocates finished rips into; duplicates and roots
    nested in one another are deduped so nothing is scanned twice) — for
    ``*.platterpus.json`` files (one per album),
    skips the current report, and returns the best one that
    :func:`same_disc` confirms is the same disc — or None if there's no match.
    Matching via :func:`same_disc` (not raw key equality) is what lets a v9
    re-rip find its v8 predecessor: they share the release id even though their
    strongest keys differ in type.

    **"Best" is completeness first, then recency** (recency is the report's
    ``generated_at``, falling back to file mtime). Two consequences, both
    deliberate — see the ``COMPLETENESS_*`` block for the full reasoning:

    * An **abandoned** (``in_progress``) report is never selected. It is a
      durability snapshot of a rip that never ended, not a rip record, and being
      re-written after every track it carries a very *recent* timestamp — so
      under a recency-only rule it would out-rank and hide the user's real prior
      rip. It is logged when skipped rather than dropped in silence, and remains
      reachable deliberately via ``platterpus --compare <old> <new>``, which
      takes explicit paths and labels the result.
    * A **partial** (cancelled/failed) prior loses to any complete prior of the
      same disc regardless of dates, because the interesting question is "how does
      this compare to the last time I ripped the whole disc". With no complete
      prior it is used, and :func:`compare_reports` labels it.

    I/O, but bounded (``_MAX_SCAN_REPORTS``) and fully defensive: any unreadable
    file is skipped and the whole thing returns None rather than raising, so it's
    safe to call from a best-effort post-rip path (off the GUI thread — a large
    library is many small reads).
    """
    try:
        current_path = Path(current_report_path).resolve()
    except OSError:
        current_path = Path(current_report_path)
    if current_report is None:
        current_report = load_report(current_path)
    if current_report is None:
        return None
    if not _disc_fields(current_report):
        # No disc identity to match on — don't guess across the library.
        return None

    # Dedup the scan roots (resolved), and drop a root nested inside another —
    # rglob on the outer root already covers it, and scanning twice would both
    # waste the report budget and double-count candidates.
    roots: list[Path] = []
    for raw_root in (search_root, *extra_roots):
        try:
            resolved_root = Path(raw_root).resolve()
        except OSError:
            resolved_root = Path(raw_root)
        if any(
            resolved_root == kept or _is_under(resolved_root, kept) for kept in roots
        ):
            continue
        roots = [kept for kept in roots if not _is_under(kept, resolved_root)]
        roots.append(resolved_root)

    # ((completeness rank, recency epoch), path). A TUPLE key, so the ordinary
    # ">" comparison below sorts on completeness first and only falls back to
    # recency inside one class — a complete prior can never be shadowed by a
    # newer stopped-short one.
    best: tuple[tuple[int, float], Path] | None = None
    scanned = 0  # one budget across ALL roots — the cap is about total I/O
    for root in roots:
        try:
            candidates = root.rglob("*.platterpus.json")
        except OSError:
            continue
        # The rglob generator does its I/O lazily, so a traversal error (a dying
        # disk, a stale NFS mount) can surface on ANY iteration step, not just
        # the rglob() call above. Wrap the whole loop so such an error just ends
        # this root's scan with whatever was found so far, never propagating out
        # of this best-effort helper ("returns None rather than raising").
        try:
            for candidate in candidates:
                if scanned >= _MAX_SCAN_REPORTS:
                    log.warning(
                        "prior-rip scan stopped at %d reports under %s; a match "
                        "beyond that was not considered",
                        _MAX_SCAN_REPORTS,
                        root,
                    )
                    break
                try:
                    same_file = candidate.resolve() == current_path
                except OSError:
                    same_file = candidate == current_path
                if same_file:
                    continue
                scanned += 1
                other = load_report(candidate)
                if other is None or same_disc(current_report, other) is not True:
                    continue
                completeness = report_completeness(other)
                if completeness == COMPLETENESS_ABANDONED:
                    # An "in_progress" report: a rip that never ended (see the
                    # COMPLETENESS_* block). Not a baseline — and logged, not
                    # dropped in silence, because "why did my re-rip not get a
                    # comparison banner?" has to be answerable from the log file.
                    log.info(
                        "prior-rip scan ignoring %s: its outcome is still "
                        "'in_progress', so it is an abandoned mid-rip snapshot "
                        "rather than a finished rip. Compare against it "
                        "deliberately with: %s --compare <that file> "
                        "<this rip's report>",
                        self_invocation(),
                        candidate,
                    )
                    continue
                # 1 = complete, 0 = partial: a cancelled/failed prior is real data
                # and stays in the running, but any complete rip of the same disc
                # outranks it however old it is.
                rank = 1 if completeness == COMPLETENESS_COMPLETE else 0
                sort_key = (rank, _recency_key(other, candidate))
                if best is None or sort_key > best[0]:
                    best = (sort_key, candidate)
        except OSError:
            log.warning("prior-rip scan hit an I/O error under %s", root)
        if scanned >= _MAX_SCAN_REPORTS:
            break
    return best[1] if best is not None else None


def _is_under(path: Path, ancestor: Path) -> bool:
    """True when ``path`` sits strictly inside ``ancestor``. Pure; never raises."""
    try:
        return path != ancestor and path.is_relative_to(ancestor)
    except (OSError, ValueError):
        return False


def _recency_key(report: dict, path: Path) -> float:
    """A numeric recency key (epoch seconds) for a report, higher = newer.

    Uses the report's ``generated_at`` (parsed to an epoch), falling back to the
    file mtime, then ``0.0``. Returning a single numeric scale is deliberate: an
    earlier version returned an ISO *string* for one branch and a ``"mtime:…"``
    string for the other, which sorted wrongly (``"m" > "2"``, so any report
    lacking ``generated_at`` always beat one that had it). Pure; never raises."""
    from datetime import datetime

    gen = report.get("generated_at")
    if isinstance(gen, str) and gen:
        try:
            return datetime.fromisoformat(gen).timestamp()
        except (ValueError, OverflowError, OSError):
            pass
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


# --- Human rendering (CLI) --------------------------------------------------


def render_comparison(comparison: RipComparison) -> str:
    """Render a :class:`RipComparison` as a readable multi-line report (CLI)."""
    lines: list[str] = []
    lines.append(f"Comparing:  A = {comparison.label_a}")
    lines.append(f"            B = {comparison.label_b}")
    if comparison.same_disc is True:
        lines.append(f"Same disc:  yes ({comparison.disc_key_a})")
    elif comparison.same_disc is False:
        lines.append(
            f"Same disc:  NO — A={comparison.disc_key_a} B={comparison.disc_key_b}"
        )
    else:
        lines.append("Same disc:  unconfirmed (no disc ID)")
    lines.append("")
    header = f"{'#':>3}  {'Track':<32}  {'A':<20}  {'B':<20}  Better"
    lines.append(header)
    lines.append("-" * len(header))
    for t in comparison.tracks:
        lines.append(
            f"{t.number:>3}  {_clip(t.title, 32):<32}  "
            f"{_cell(t.crc_a, t.status_a, t.confidence_a):<20}  "
            f"{_cell(t.crc_b, t.status_b, t.confidence_b):<20}  "
            f"{_better_label(t)}"
        )
    lines.append("")
    lines.append(comparison.summary)
    for note in comparison.notes:
        # Skip a note the summary already states verbatim. The "this rip didn't
        # finish" caveat deliberately lives in BOTH — the GUI banner renders only
        # the summary, so it has to be there, while `notes` is the structured
        # place a caveat belongs — and printing it twice here would just look like
        # a bug.
        if note in comparison.summary:
            continue
        lines.append(f"note: {note}")
    return "\n".join(lines)


def _cell(crc: str | None, status: str, confidence: int | None) -> str:
    if crc is None:
        return "—"
    tag = {
        STATUS_VERIFIED: f"✓{confidence}" if confidence is not None else "✓",
        STATUS_OFFSET_VARIANT: f"~{confidence}" if confidence is not None else "~",
        STATUS_NOT_IN_DB: "·",
    }.get(status, "")
    return f"{crc} {tag}".strip()


def _better_label(t: TrackComparison) -> str:
    if t.better == SIDE_EQUAL:
        return "= identical"
    if t.better == SIDE_A:
        return "◀ A"
    if t.better == SIDE_B:
        return "B ▶"
    return "? differ"


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


# --- Best-of-both per-track assembler ---------------------------------------
#
# When a re-rip beats the previous rip on some tracks and loses on others,
# neither folder is the ideal master — the best copy is track-by-track. This
# assembles that: for each track, pick the better side and COPY its file into a
# fresh destination folder. It is strictly NON-DESTRUCTIVE — it never deletes or
# overwrites either source; the user keeps both original rips untouched.


@dataclass(frozen=True)
class BestOfEntry:
    """One track's choice in a best-of plan."""

    number: int
    title: str
    side: str  # SIDE_A / SIDE_B (a real, copyable source) — never equal/unknown
    reason: str
    filename_a: str | None
    filename_b: str | None

    @property
    def source_filename(self) -> str | None:
        """The filename to copy from, on the chosen side."""
        return self.filename_a if self.side == SIDE_A else self.filename_b


@dataclass(frozen=True)
class BestOfPlan:
    """A per-track plan for assembling a best-of-both master folder."""

    entries: tuple[BestOfEntry, ...]
    # Tracks where the two rips differ with no basis to choose (SIDE_UNKNOWN).
    # These default to side A in the plan but are flagged so the caller can warn.
    ambiguous_tracks: tuple[int, ...]
    from_a: int  # how many tracks the plan takes from A
    from_b: int  # how many from B


@dataclass(frozen=True)
class BestOfResult:
    """Outcome of executing a best-of plan (copying files)."""

    dest: Path
    copied: int
    copied_tracks: tuple[int, ...] = ()
    failures: tuple[str, ...] = ()
    error: str | None = None


def _report_filenames_by_number(report: dict) -> dict[int, str]:
    out: dict[int, str] = {}
    if not isinstance(report, dict):
        return out
    for track in report.get("tracks") or ():
        if not isinstance(track, dict) or not isinstance(track.get("number"), int):
            continue
        name = track.get("filename")
        if isinstance(name, str) and name.strip():
            # Reports store a path (possibly with subdirs); the FLAC lives beside
            # the report, so keep just the basename for the copy source.
            out[track["number"]] = Path(name).name
    return out


def best_of_plan(
    comparison: RipComparison,
    report_a: dict,
    report_b: dict,
) -> BestOfPlan:
    """Build a per-track best-of plan from a comparison + the two reports.

    Each track is assigned to whichever side is the better master; an identical
    track takes side A (arbitrary — the files are equal); a genuinely ambiguous
    track (``SIDE_UNKNOWN``) defaults to A but is recorded in
    ``ambiguous_tracks`` so the caller can flag it. Pure; never raises. The
    reports supply each track's source filename per side.
    """
    names_a = _report_filenames_by_number(report_a)
    names_b = _report_filenames_by_number(report_b)
    entries: list[BestOfEntry] = []
    ambiguous: list[int] = []
    from_a = 0
    from_b = 0
    for t in comparison.tracks:
        # The side that is actually the better master (equal/unknown → prefer A).
        if t.better == SIDE_B:
            side = SIDE_B
        elif t.better in (SIDE_A, SIDE_EQUAL):
            side = SIDE_A
        else:  # SIDE_UNKNOWN
            ambiguous.append(t.number)
            side = SIDE_A if names_a.get(t.number) else SIDE_B
        # If the better side lacks a recorded file, fall back to the other side —
        # but flag it: we're then copying the WORSE read, which the user should
        # know about (a missing filename is rare, but silently shipping the
        # inferior copy as "best-of" would be a lie).
        if side == SIDE_A and not names_a.get(t.number) and names_b.get(t.number):
            side = SIDE_B
            if t.number not in ambiguous:
                ambiguous.append(t.number)
        elif side == SIDE_B and not names_b.get(t.number) and names_a.get(t.number):
            side = SIDE_A
            if t.number not in ambiguous:
                ambiguous.append(t.number)
        if side == SIDE_A:
            from_a += 1
        else:
            from_b += 1
        entries.append(
            BestOfEntry(
                number=t.number,
                title=t.title,
                side=side,
                reason=t.reason,
                filename_a=names_a.get(t.number),
                filename_b=names_b.get(t.number),
            )
        )
    return BestOfPlan(
        entries=tuple(entries),
        ambiguous_tracks=tuple(ambiguous),
        from_a=from_a,
        from_b=from_b,
    )


def assemble_best_of(
    plan: BestOfPlan,
    folder_a: Path,
    folder_b: Path,
    dest: Path,
    *,
    copy_fn: Callable[[Path, Path], object] | None = None,
) -> BestOfResult:
    """Copy the best per-track file into ``dest``. NON-DESTRUCTIVE; never raises.

    For each planned track, copies the chosen side's file from ``folder_a`` /
    ``folder_b`` into ``dest`` (created if needed). Sources are never modified or
    deleted. ``copy_fn`` defaults to ``shutil.copy2`` (preserves mtime); tests
    inject a stub. A per-file failure is collected in ``failures`` and the rest
    proceed; a fatal error (e.g. dest can't be created) is returned in ``error``.
    """
    import shutil

    copier = copy_fn or shutil.copy2
    dest = Path(dest)
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return BestOfResult(
            dest=dest, copied=0, error=f"could not create destination: {exc}"
        )

    copied = 0
    copied_tracks: list[int] = []
    failures: list[str] = []
    for entry in plan.entries:
        source_name = entry.source_filename
        if not source_name:
            failures.append(f"track {entry.number}: no source file on the chosen side")
            continue
        source_dir = folder_a if entry.side == SIDE_A else folder_b
        source = Path(source_dir) / source_name
        target = dest / source_name
        try:
            copier(source, target)
            copied += 1
            copied_tracks.append(entry.number)
        except OSError as exc:
            failures.append(f"track {entry.number}: {exc}")
    return BestOfResult(
        dest=dest,
        copied=copied,
        copied_tracks=tuple(copied_tracks),
        failures=tuple(failures),
        error=None,
    )


def render_best_of_plan(plan: BestOfPlan) -> str:
    """Render a best-of plan as readable lines (CLI preview)."""
    lines: list[str] = [
        f"Best-of plan: {plan.from_a} track(s) from A, {plan.from_b} from B."
    ]
    for entry in plan.entries:
        side = "A" if entry.side == SIDE_A else "B"
        name = entry.source_filename or "(missing)"
        lines.append(f"  {entry.number:>3}  [{side}] {name}  — {entry.reason}")
    if plan.ambiguous_tracks:
        listed = ", ".join(str(n) for n in plan.ambiguous_tracks)
        lines.append(
            f"note: track(s) {listed} differ with no basis to choose — defaulted "
            "to A; re-rip to break the tie"
        )
    return "\n".join(lines)


def default_report_roots(config: object | None = None) -> list[Path]:
    """Where rips land on this machine, best-effort, in priority order.

    The user's configured output folder, then their library folder (the
    auto-move destination), then ``~/Music`` as the last resort. Only existing
    directories are returned, deduped, order preserved.

    **Why this is a function and not three lines at each call site.** The same
    list was being reconstructed in shell inside ``rig_session.sh`` — twice —
    and a third copy was about to be written for the compare path. Three
    descriptions of "where the rips are" will eventually disagree, and the one
    that disagrees silently searches the wrong place and reports *no rip found*,
    which is indistinguishable from *no rip happened*. Pure apart from the
    directory-existence checks; never raises.
    """
    if config is None:
        try:
            from platterpus import config as config_module

            config = config_module.load()
        except Exception:  # noqa: BLE001 — a bad config must not break discovery
            log.warning("could not load config for report discovery", exc_info=True)
            config = None

    roots: list[Path] = []
    for raw in (
        getattr(config, "output_dir", "") or "",
        getattr(config, "library_dir", "") or "",
        str(Path.home() / "Music"),
    ):
        if not raw:
            continue
        try:
            candidate = Path(raw).expanduser()
            if not candidate.is_dir():
                continue
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved not in roots:
            roots.append(resolved)
    return roots


def newest_report(roots: Sequence[Path]) -> Path | None:
    """The most recently modified ``*.platterpus.json`` under ``roots``.

    Newest by **file mtime**, deliberately, and different from the "best prior"
    rule in :func:`find_prior_report`: this answers *"which rip did the operator
    just make"*, where recency is the whole question and completeness is not —
    a cancelled rip they just ran is still the rip they want looked at.

    Bounded by the same ``_MAX_SCAN_REPORTS`` budget and just as defensive: any
    unreadable tree is skipped and the whole thing returns None rather than
    raising.
    """
    best: tuple[float, Path] | None = None
    scanned = 0
    for root in roots:
        try:
            candidates = root.rglob("*.platterpus.json")
        except OSError:
            continue
        try:
            for candidate in candidates:
                if scanned >= _MAX_SCAN_REPORTS:
                    log.warning(
                        "newest-rip scan stopped at %d reports; a newer one "
                        "beyond that was not considered",
                        _MAX_SCAN_REPORTS,
                    )
                    break
                scanned += 1
                try:
                    stamp = candidate.stat().st_mtime
                except OSError:
                    continue
                if best is None or stamp > best[0]:
                    best = (stamp, candidate)
        except OSError:
            continue
    return best[1] if best else None


def _pair_label(report_path: Path) -> str:
    """A label that distinguishes two rips of the SAME disc.

    The album folder plus the filename. Filename alone is useless here: two
    passes of one disc produce identical basenames, so a message built from
    ``.name`` reads "Album.json -> Album.json" and names neither rip. The folder
    is the distinguishing part, which is why a rig script gives each pass its own
    album title.
    """
    parent = report_path.parent.name
    return f"{parent}/{report_path.name}" if parent else report_path.name


@dataclass(frozen=True)
class DiscoveredPair:
    """The outcome of looking for two rips of one disc to compare.

    ``previous``/``later`` are both set only when a comparable pair was found.
    ``reason`` always explains the outcome, including the successful one —
    because *"nothing to compare"* has at least four distinct causes and a
    caller that cannot tell them apart will report the wrong one:

    * no reports at all (no rip has happened, or they land elsewhere);
    * exactly one report (a single rip — not yet a double);
    * reports exist but none is the same disc (different albums);
    * the same album twice but identity could not be **confirmed**, which is
      tri-state and is NOT the same as *different discs*.
    """

    previous: Path | None
    later: Path | None
    reason: str

    @property
    def found(self) -> bool:
        return self.previous is not None and self.later is not None


def discover_pair_to_compare(roots: Sequence[Path] | None = None) -> DiscoveredPair:
    """Find the newest rip and its best prior rip *of the same disc*.

    This is what makes a double test rip one argument-less command: rip the disc
    twice, then ask for a comparison without naming either folder. A path the
    operator has to type is a path they can mistype, and comparing the *wrong*
    pair still prints a confident-looking table.

    Delegates the hard half to :func:`find_prior_report`, which already ranks by
    completeness before recency and refuses to select an abandoned in-progress
    snapshot. Nothing about "same disc" is re-decided here.
    """
    search_roots = list(roots) if roots is not None else default_report_roots()
    if not search_roots:
        return DiscoveredPair(None, None, "no rip folders exist to search")

    later = newest_report(search_roots)
    if later is None:
        return DiscoveredPair(
            None,
            None,
            "no .platterpus.json found under "
            + ", ".join(str(r) for r in search_roots)
            + " — either no rip has happened, or rips land somewhere else",
        )

    report = load_report(later)
    if report is None:
        return DiscoveredPair(
            None, None, f"the newest report could not be read: {later}"
        )
    if not _disc_fields(report):
        # Refusing to guess. An unknown-disc rip has no identity to match on, and
        # picking "the other newest thing" would compare two different albums.
        return DiscoveredPair(
            None,
            None,
            f"the newest rip ({later.name}) carries no disc identity, so a prior "
            "rip of the same disc cannot be identified",
        )

    previous = find_prior_report(
        later,
        search_roots[0],
        current_report=report,
        extra_roots=tuple(search_roots[1:]),
    )
    if previous is None:
        return DiscoveredPair(
            None,
            None,
            f"found the newest rip ({later.name}) but no earlier rip of the same "
            "disc — a second pass has not been made, or it is not under the "
            "searched folders",
        )
    # The FOLDER, not the filename. Two passes of one disc always produce the
    # same basename -- the album title names the file -- so "Album.platterpus.json
    # -> Album.platterpus.json" tells the operator nothing about which rip is
    # which. The distinct thing is the directory, which is exactly why a rig
    # script gives each pass its own album title.
    return DiscoveredPair(
        previous, later, f"{_pair_label(previous)} -> {_pair_label(later)}"
    )
