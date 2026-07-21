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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

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


# --- The comparison ---------------------------------------------------------


def _decide_better(
    crc_a: str | None,
    crc_b: str | None,
    status_a: str,
    status_b: str,
    conf_a: int | None,
    conf_b: int | None,
) -> tuple[str, str]:
    """Decide which side is the better master for one track: ``(side, reason)``.

    Rules, in order:
    * A track missing from one side → the present side wins.
    * Byte-identical reads → ``equal`` (either is fine).
    * Otherwise prefer the stronger AR status (verified > offset-variant >
      not-in-DB); on a tie prefer the higher confidence; on a further tie the
      reads genuinely differ with no basis to choose → ``unknown``.
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
            notes=("the comparison hit an unexpected error — see the log",),
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
            crc_a, crc_b, status_a, status_b, conf_a, conf_b
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
    elif differing == 0 and not only_a and not only_b:
        headline_level = "ok"
        summary = (
            f"All {identical} track(s) are byte-for-byte identical to the previous rip."
        )
    else:
        # Something changed: differing content, and/or the track SET differs (a
        # dropped or added track). Both are worth surfacing, not hiding behind a
        # green "identical" verdict.
        headline_level = "warn"
        summary = _change_summary(
            identical, differing, a_better, b_better, only_a, only_b
        )

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
    skips the current report, and returns the most recent one that
    :func:`same_disc` confirms is the same disc — or None if there's no match.
    Matching via :func:`same_disc` (not raw key equality) is what lets a v9
    re-rip find its v8 predecessor: they share the release id even though their
    strongest keys differ in type. "Most recent" is by the report's
    ``generated_at`` (falling back to file mtime). I/O, but bounded
    (``_MAX_SCAN_REPORTS``) and fully defensive: any unreadable file is skipped
    and the whole thing returns None rather than raising, so it's safe to call
    from a best-effort post-rip path (off the GUI thread — a large library is
    many small reads).
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

    best: tuple[float, Path] | None = None  # (recency epoch, path)
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
                sort_key = _recency_key(other, candidate)
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
