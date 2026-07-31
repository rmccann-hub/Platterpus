"""Fitness test: every surface must tell the same story about one rip.

Platterpus reports a rip through several independent renderings of a single
parsed ``RipLog`` — the **EAC-compatible log** (the durable text artifact), the
**JSON report** (the machine record), the **verdict banner** (the trust
headline), the **results table** (the per-track grid on screen), and the
**status line**. They are written in different modules by different code, and
nothing structural stops one from drifting.

**The roster is the point.** This file's own docstring used to name four
surfaces while the imports covered three — and the two it left out are exactly
where the next two defects were found (audit, 2026-07-31). A surface that is not
imported here is not guarded here, so the import list below IS the roster, and
anything missing from it is called out in a TODO rather than left implied.

Four shipped defects in a single week were all exactly that drift:

* the EAC log called offset-variant tracks "not present in AccurateRip" while
  cyanrip's log and our own verdict banner said they matched (v0.5.8);
* an interrupted rip rendered as a clean, complete one because the renderer was
  never told the outcome (v0.5.8);
* a re-read track's Test & Copy proof reached the report but not the log, and a
  track whose re-reads *disagreed* was flagged on screen but not in the log
  (v0.5.9);
* a swapped-in re-rip's CRC was right in cyanrip's addendum and wrong in both
  our log and our report (v0.5.10).

Individually those are four bugs. Together they are one: **a fact reaches some
surfaces and not others.** Unit tests didn't catch them because each surface
was correct *by its own lights* — the disagreement only exists between them.

So this file asserts the agreements, not the outputs. It is a fitness function
in the shape of ``test_gui_thread_discipline.py``: cheap, Qt-free, and aimed at
a class of bug rather than a single behaviour. Scenarios are modelled on the
real Police-disc runs, because that disc produced every one of the defects
above.

When you add a surface, add it here. When you add a fact a surface can report,
add the agreement it owes the others.

**What this file cannot catch, by construction.** It compares surfaces against
each other, so it is blind to a fact that is wrong *before* any of them render
it — every surface then agrees, and agrees wrongly. That is precisely the
v0.5.10 CRC defect: the parsed ``RipLog`` itself carried the discarded read's
CRC, so log, report, and table were perfectly consistent about the wrong bytes.
Guarding the *input* is a different job, done where the input is built —
``test_auto_fix_convergence.py`` for the post-rip enrichers, the parser tests
for what comes out of cyanrip. Both halves are needed; neither substitutes for
the other.

Each assertion here was mutation-checked against the defect it exists for:
deleting the offset-variant branch, the read-stability line, the incomplete-rip
banner, or the Test/Copy pair each turns exactly one test red, and rendering a
CRC the report doesn't have turns three red.
"""

from __future__ import annotations

import re
from dataclasses import replace

from platterpus.eac_log_export import _accuraterip_line, render_eac_style_log
from platterpus.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    RippingInfo,
    TrackResult,
    track_accuraterip_verified,
)
from platterpus.rip_report import build_report

# The on-screen results table. Importing a `ui.` module here is safe and
# deliberate: `_ar_cell` is a pure text function and `rip_progress` imports
# cleanly with no ``QApplication`` (verified — nothing at import time touches a
# widget), so the whole file stays Qt-free and cheap. Private names are used on
# purpose: `_ar_cell` and `_accuraterip_line` are the two *per-track* renderers,
# which is the level at which they can be compared at all. That they really are
# what the user sees is pinned separately, in
# ``test_the_per_track_log_line_is_what_the_rendered_log_actually_carries``.
from platterpus.ui.rip_progress import _ar_cell
from platterpus.verdict import (
    AR_STATE_ABSENT,
    AR_STATE_NO_DATA,
    AR_STATE_NO_MATCH,
    AR_STATE_NOT_CHECKED,
    AR_STATE_OFFSET_VARIANT,
    AR_STATE_VERIFIED,
    AR_STATES,
    accuraterip_counts,
    accuraterip_verdict,
)

# TODO(roster): `platterpus.ui.main_window_helpers.fidelity_summary` — the status
# line — is the fifth surface and is NOT guarded here yet. It is being fixed
# concurrently by the worker who owns `ui/main_window_rip.py`,
# `ui/main_window_helpers.py` and `verdict.py`; adding it here at the same time
# would collide with them. Add it (and its AccurateRip state agreement) once that
# change has landed.

# --- scenario builders (modelled on the real hardware runs) ------------------


def _verified(crc: str, confidence: int = 200) -> AccurateRipResult:
    return AccurateRipResult(
        version=2,
        result="accurately ripped",
        confidence=confidence,
        local_crc=crc,
    )


def _offset_variant(crc: str) -> AccurateRipResult:
    """A +450 offset-variant match: in the database, but not an exact match."""
    return AccurateRipResult(
        version=2,
        result="matches Accurip DB, track is partially accurately ripped",
        confidence=200,
        local_crc=crc,
    )


def _clean_disc() -> RipLog:
    """Every track exactly verified — the boring case that must stay boring."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        ripping_info=RippingInfo(drive="PIONEER BDR-209D", read_offset_correction=667),
        tracks=tuple(
            TrackResult(
                number=n,
                filename=f"{n:02d}.flac",
                copy_crc=f"AAAA000{n}",
                status="ripped successfully",
                accuraterip_v2=_verified(f"BBBB000{n}"),
            )
            for n in range(1, 5)
        ),
        accuraterip_summary="4/4 tracks ripped accurately (AccurateRip)",
        health_status="No errors occurred",
    )


def _police_disc() -> RipLog:
    """The real shape: mostly exact, two offset-variant, one never converged.

    Track 3 is the one that has never read the same way twice on real hardware;
    track 5 converged on a re-read and was swapped in.
    """
    tracks = [
        TrackResult(
            number=n,
            filename=f"{n:02d}.flac",
            copy_crc=f"CCCC000{n}",
            status="ripped successfully",
            accuraterip_v2=_verified(f"DDDD000{n}"),
        )
        for n in (1, 2, 4)
    ]
    tracks.append(
        TrackResult(
            number=3,
            filename="03.flac",
            copy_crc="3D8FCF0C",
            status="ripped successfully",
            accuraterip_offset=_offset_variant("BF62B1DA"),
            secure_rerip_converged=False,  # re-read, reads disagreed
        )
    )
    tracks.append(
        TrackResult(
            number=5,
            filename="05.flac",
            copy_crc="E0036697",
            status="ripped successfully",
            accuraterip_offset=_offset_variant("4CCBCF89"),
            secure_rerip_converged=True,  # re-read, reads agreed, swapped in
        )
    )
    return RipLog(
        log_creator="cyanrip 0.9.3",
        ripping_info=RippingInfo(drive="PIONEER BDR-209D", read_offset_correction=667),
        tracks=tuple(sorted(tracks, key=lambda t: t.number)),
        accuraterip_summary="3/5 tracks ripped accurately (AccurateRip)",
        partially_accurate_summary="2/2 tracks ripped partially accurately",
        health_status="No errors occurred",
    )


def _unknown_disc() -> RipLog:
    """A disc nobody has submitted (a CD-R): no AR data at all, and that's fine."""
    return RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=tuple(
            TrackResult(number=n, filename=f"{n:02d}.flac", copy_crc=f"EEEE000{n}")
            for n in range(1, 4)
        ),
        health_status="No errors occurred",
    )


SCENARIOS = {
    "clean": _clean_disc,
    "police": _police_disc,
    "unknown": _unknown_disc,
}


def _surfaces(rip_log: RipLog, **render_kwargs: object) -> tuple[str, dict, str, str]:
    """Render one RipLog through every surface. Returns (log_text, report, msg, level)."""
    text = render_eac_style_log(rip_log, **render_kwargs)  # type: ignore[arg-type]
    report = build_report(rip_log)
    message, level = accuraterip_verdict(rip_log)
    return text, report, message, level


# --- the agreements ----------------------------------------------------------


def test_every_track_crc_is_identical_in_the_log_and_the_report() -> None:
    """A CRC identifies specific bytes; two surfaces naming different ones is a lie.

    This is the v0.5.10 defect in general form: the log rendered the discarded
    read's CRC while the file on disk (and cyanrip's own addendum) had another.
    """
    for name, build in SCENARIOS.items():
        rip_log = build()
        text, report, _, _ = _surfaces(rip_log)
        for track, entry in zip(rip_log.tracks, report["tracks"], strict=True):
            assert entry["copy_crc"] == track.copy_crc, (
                f"{name}: report CRC disagrees with the parsed log for track "
                f"{track.number}"
            )
            assert f"Copy CRC {track.copy_crc}" in text, (
                f"{name}: track {track.number}'s CRC {track.copy_crc} is in the "
                "report but not in the EAC-compatible log"
            )


def test_no_crc_appears_in_the_log_that_no_track_actually_has() -> None:
    """The inverse direction: the log may not invent or retain a stale CRC."""
    for name, build in SCENARIOS.items():
        rip_log = build()
        text, _, _, _ = _surfaces(rip_log)
        known = {t.copy_crc for t in rip_log.tracks}
        rendered = set(re.findall(r"(?:Copy|Test) CRC ([0-9A-F]{8})", text))
        assert rendered <= known, (
            f"{name}: the log shows CRC(s) {rendered - known} that belong to no "
            "track — a stale or invented value"
        )


def test_verified_track_counts_agree_across_all_three_surfaces() -> None:
    """ "How many tracks are proven?" must have exactly one answer."""
    for name, build in SCENARIOS.items():
        rip_log = build()
        text, report, message, _ = _surfaces(rip_log)
        expected = sum(1 for t in rip_log.tracks if track_accuraterip_verified(t))

        in_report = sum(1 for t in report["tracks"] if t["accuraterip_verified"])
        in_log = text.count("Accurately ripped (confidence")
        assert in_report == expected, f"{name}: report verified-count disagrees"
        assert in_log == expected, f"{name}: EAC log verified-count disagrees"

        # The verdict headline quotes the count in prose; when it does, it must be
        # the same number. (An all-verified or nothing-verified disc words it
        # without a count, which is fine — there is nothing to disagree with.)
        quoted = re.search(r"(\d+) of (\d+) tracks", message)
        if quoted:
            assert int(quoted.group(1)) == expected, (
                f"{name}: the verdict banner claims {quoted.group(1)} verified "
                f"tracks but {expected} are"
            )


def test_an_offset_variant_track_is_never_called_absent_or_exact() -> None:
    """The v0.5.8 defect: three surfaces disagreeing about the same two tracks.

    An offset-variant match is *in* the database (so "not present" is false) but
    is not an exact match (so counting it as verified over-claims). Every surface
    has to land in that middle.
    """
    rip_log = _police_disc()
    text, report, message, level = _surfaces(rip_log)
    variants = [t for t in rip_log.tracks if t.accuraterip_offset is not None]
    assert variants, "scenario must contain offset-variant tracks"

    assert "not present in AccurateRip" not in text
    # Per-track lines only: the status report now also carries an
    # offset-variant count line, which is a summary, not a track.
    per_track = [x for x in text.splitlines() if x.startswith("     Matched an offset")]
    assert len(per_track) == len(variants)
    for track in variants:
        entry = next(t for t in report["tracks"] if t["number"] == track.number)
        assert entry["accuraterip_verified"] is False, (
            f"track {track.number} matched only an offset-variant pressing; the "
            "report must not call it verified"
        )
    assert level == "warn", "a partially-accurate disc is not a clean pass"
    _, _, partial = accuraterip_counts(rip_log)
    assert partial == len(variants)


def test_a_track_whose_rereads_disagreed_is_flagged_everywhere() -> None:
    """The v0.5.9 defect: the app warned on screen, the durable log did not."""
    rip_log = _police_disc()
    text, report, _, _ = _surfaces(rip_log)
    unstable = [t for t in rip_log.tracks if t.secure_rerip_converged is False]
    assert unstable, "scenario must contain a non-converged track"

    for track in unstable:
        entry = next(t for t in report["tracks"] if t["number"] == track.number)
        assert entry["secure_rerip_converged"] is False, (
            f"track {track.number}'s measured non-convergence is missing from the "
            "machine record"
        )
        assert f"track(s) {track.number}" in text, (
            f"track {track.number} did not read reproducibly, but the "
            "EAC-compatible log's summary never says so"
        )
    assert "not confirmed reproducible" in text


def test_a_converged_track_earns_the_test_and_copy_pair_in_the_log() -> None:
    """Convergence is EAC's Test & Copy proof; having it and not saying it is a loss."""
    rip_log = _police_disc()
    text, report, _, _ = _surfaces(rip_log)
    converged = [t for t in rip_log.tracks if t.secure_rerip_converged is True]
    assert converged, "scenario must contain a converged track"

    for track in converged:
        assert f"Test CRC {track.copy_crc}" in text
        entry = next(t for t in report["tracks"] if t["number"] == track.number)
        assert entry["secure_rerip_converged"] is True


def test_a_single_read_track_claims_no_second_read_anywhere() -> None:
    """The mirror rule: never render proof of a read that didn't happen."""
    rip_log = _clean_disc()
    text, report, _, _ = _surfaces(rip_log)
    assert "Test CRC" not in text
    assert "Read stability" not in text
    assert all(t["secure_rerip_converged"] is None for t in report["tracks"])


def test_an_interrupted_rip_is_declared_in_the_durable_log() -> None:
    """The v0.5.8 HIGH defect: a cancelled rip that read as a clean complete one."""
    rip_log = _clean_disc()  # 4 tracks written…
    text = render_eac_style_log(
        rip_log,
        outcome_status="cancelled",
        disc_track_total=14,  # …of a 14-track disc
    )
    assert "INCOMPLETE RIP (cancelled)" in text
    assert "4" in text and "14" in text
    # And the notice sits ABOVE the checksum, so it cannot be stripped silently.
    assert text.index("INCOMPLETE RIP") < text.index("Platterpus log checksum")


def test_a_complete_rip_carries_no_incomplete_banner() -> None:
    """The same fact in the other direction — no crying wolf on a good rip."""
    text, _, _, _ = _surfaces(_clean_disc(), outcome_status="success")
    assert "INCOMPLETE RIP" not in text


def test_a_disc_absent_from_accuraterip_over_claims_nowhere() -> None:
    """No AR data is not a failure and not a pass — every surface must stay neutral."""
    rip_log = _unknown_disc()
    text, report, _, level = _surfaces(rip_log)
    assert level == "neutral"
    assert "Accurately ripped (confidence" not in text
    assert "offset-variant" not in text
    assert all(t["accuraterip_verified"] is False for t in report["tracks"])


# --- The four AccurateRip states, and the two surfaces that must agree -------
#
# AccurateRip can put a track in exactly FOUR states. Both renderers below have
# to place a given track in the same one; which words they use for it is their
# own business (a narrow table column cannot spell out what a log line can).
#
# The states are defined here from the *data*, independently of either
# implementation, so this table is a specification rather than a restatement of
# one renderer's if-chain:
#
#   VERIFIED   — an exact v1/v2 checksum match (confidence >= 1).
#   OFFSET     — no exact match, but the +450-frame offset-variant pressing
#                matched: in the database, partially accurate.
#   NO_MATCH   — the disc IS in the database (cyanrip printed a per-track
#                "Accurip" line, checksum included, which it only does for a
#                disc it found) but no stored copy matches our read. "Not in the
#                database" is a FALSE statement about such a track.
#   ABSENT     — nothing was submitted for this disc, so there was nothing to
#                compare against. This is the only state "not in DB" describes.
#
# The bug this section exists for (2026-07-31): the EAC-compatible log grew a
# fourth state on 2026-07-28 ("Cannot be verified as accurate") precisely because
# calling a NO_MATCH track absent is a false claim — and the on-screen table was
# never told, so the durable artifact and the screen made contradictory claims
# about the same parsed track, with the screen making the false one.

_STATE_VERIFIED = "VERIFIED"
_STATE_OFFSET = "OFFSET"
_STATE_NO_MATCH = "NO_MATCH"
_STATE_ABSENT = "ABSENT"
_STATE_NOT_CHECKED = "NOT_CHECKED"

# Which verdict state each surface-label stands for. This mapping is the floor:
# its keys are asserted EQUAL to `verdict.AR_STATES`, so adding a state to the
# classifier fails this file until the state has a label AND a case below.
#
# The old floor hardcoded four state names, which is a floor equal to its own
# list — it could not notice a fifth state at all, and one was added (`not-checked`)
# while it stayed green. Same shape as the never-raises roster whose floor equalled
# its own length (audit, 2026-07-31).
_LABEL_FOR_AR_STATE: dict[str, str] = {
    AR_STATE_VERIFIED: _STATE_VERIFIED,
    AR_STATE_OFFSET_VARIANT: _STATE_OFFSET,
    AR_STATE_NO_MATCH: _STATE_NO_MATCH,
    AR_STATE_ABSENT: _STATE_ABSENT,
    AR_STATE_NOT_CHECKED: _STATE_NOT_CHECKED,
    # `no-data` is reachable only when a track carries no AR result object at all,
    # which both surfaces render identically to `absent` by construction — there is
    # no wording for the two to disagree about. Deliberately unlabelled, and this
    # comment is the justification the exclusion needs.
    AR_STATE_NO_DATA: "",
}

# Row-level precedence: what the *row* claims is its strongest statement. A row
# can hold two different per-column states (v1 exact, v2 missed, say), and the
# log writes ONE line per track, so comparing them needs this reduction. Ordered
# most- to least-informative, matching the order the log line itself tries.
_STATE_PRECEDENCE: tuple[str, ...] = (
    _STATE_VERIFIED,
    _STATE_OFFSET,
    _STATE_NO_MATCH,
    # Below NO_MATCH: if either column managed a real comparison, that is the
    # row's strongest claim. NOT_CHECKED means no column had anything to compare.
    _STATE_NOT_CHECKED,
    _STATE_ABSENT,
)


def _state_from_log_line(line: str) -> str:
    """Classify the EAC-compatible log's per-track AccurateRip line."""
    if line.startswith("Accurately ripped"):
        return _STATE_VERIFIED
    if line.startswith("Matched an offset-variant pressing"):
        return _STATE_OFFSET
    if line.startswith("Cannot be verified as accurate"):
        return _STATE_NO_MATCH
    if line.startswith("Not checked against the AccurateRip database"):
        return _STATE_NOT_CHECKED
    if line.startswith("Track not present in AccurateRip database"):
        return _STATE_ABSENT
    # Deliberately loud: new wording must be classified on purpose, not silently
    # bucketed into whichever state happens to match first.
    raise AssertionError(f"unclassifiable EAC log line: {line!r}")


def _state_from_table_cell(cell: str) -> str | None:
    """Classify one results-table AR cell. ``None`` = this column said nothing."""
    if cell.startswith("OK ("):
        return _STATE_VERIFIED
    if cell.startswith("offset-variant match"):
        return _STATE_OFFSET
    if cell == "not checked":
        return _STATE_NOT_CHECKED
    if cell == "in DB, no match":
        return _STATE_NO_MATCH
    if cell == "not in DB":
        return _STATE_ABSENT
    if cell == "—":
        # An empty column claims nothing at all. At row level that is the same
        # thing the log's "not present" says: no evidence either way.
        return None
    raise AssertionError(f"unclassifiable results-table AR cell: {cell!r}")


def _state_from_table_row(track: TrackResult) -> str:
    """Classify what the on-screen results ROW says about a track.

    The table renders v1 and v2 as separate columns; the log writes one line. So
    take the row's strongest claim — that is what a reader takes away from it.
    """
    offset = track.accuraterip_offset
    # The lookup status must be handed to the table exactly as the real row does
    # it — a helper that omits it asks the table a different question from the one
    # the log answers, and the whole point of this file is that they agree.
    lookup = track.accuraterip_lookup
    cells = (
        _ar_cell(track.accuraterip_v1, offset_result=offset, lookup=lookup),
        _ar_cell(track.accuraterip_v2, offset_result=offset, lookup=lookup),
    )
    states = {s for s in (_state_from_table_cell(c) for c in cells) if s is not None}
    for state in _STATE_PRECEDENCE:
        if state in states:
            return state
    return _STATE_ABSENT  # nothing but "—": the row makes no claim


def _ar(
    version: int,
    result: str,
    confidence: int | None,
    *,
    local_crc: str | None = "BF62B1DA",
) -> AccurateRipResult:
    """One AR result. ``local_crc`` present = we computed a checksum and compared.

    cyanrip's real per-track lines always carry that checksum
    ("Accurip v2:  9ABCDEF0 (not found, either a new pressing, or bad rip)"), and
    it only prints them for a disc it found in the database — which is what makes
    the checksum the evidence that a comparison happened. Pass ``local_crc=None``
    for a result that carries no comparison.
    """
    return AccurateRipResult(
        version=version, result=result, confidence=confidence, local_crc=local_crc
    )


# cyanrip's real wording for "compared, matched nothing" — the exact string the
# results table used to render as "not in DB".
_CYANRIP_NO_MATCH = "not found, either a new pressing, or bad rip"

# One case per state, each a TrackResult built from what a real cyanrip log
# produces. Modelled on the Police "Classics" disc, which produced states 1-2 on
# real hardware, and on cyanrip's own documented output for 3-4.
AR_STATE_CASES: tuple[tuple[str, str, TrackResult], ...] = (
    (
        "exact match with confidence",
        _STATE_VERIFIED,
        TrackResult(
            number=1,
            filename="01.flac",
            copy_crc="AAAA0001",
            status="ripped successfully",
            accuraterip_v2=_ar(2, "accurately ripped, confidence 200", 200),
        ),
    ),
    (
        "offset-variant pressing only",
        _STATE_OFFSET,
        TrackResult(
            number=2,
            filename="02.flac",
            copy_crc="AAAA0002",
            status="ripped successfully",
            accuraterip_v1=_ar(1, _CYANRIP_NO_MATCH, None),
            accuraterip_v2=_ar(2, _CYANRIP_NO_MATCH, None),
            accuraterip_offset=_ar(
                450, "matches Accurip DB, track is partially accurately ripped", 200
            ),
        ),
    ),
    (
        "in the database, no stored copy matches our read",
        _STATE_NO_MATCH,
        TrackResult(
            number=3,
            filename="03.flac",
            copy_crc="AAAA0003",
            status="ripped successfully",
            accuraterip_v1=_ar(1, _CYANRIP_NO_MATCH, None),
            accuraterip_v2=_ar(2, _CYANRIP_NO_MATCH, None),
        ),
    ),
    (
        "no lookup was made at all — the database has said nothing",
        _STATE_NOT_CHECKED,
        TrackResult(
            number=6,
            filename="06.flac",
            copy_crc="AAAA0006",
            status="ripped successfully",
            # cyanrip prints the per-track CRC rows even when AccurateRip is off,
            # which is exactly why this case exists: the CRCs alone used to be read
            # as proof a comparison happened, so a never-queried disc rendered as
            # "in DB, no match" — a claim about a database nobody consulted.
            accuraterip_lookup="disabled",
            accuraterip_v1=_ar(1, _CYANRIP_NO_MATCH, None),
            accuraterip_v2=_ar(2, _CYANRIP_NO_MATCH, None),
        ),
    ),
    (
        "in the database, and even the offset variant missed",
        _STATE_NO_MATCH,
        TrackResult(
            number=4,
            filename="04.flac",
            copy_crc="AAAA0004",
            status="ripped successfully",
            accuraterip_offset=_ar(450, _CYANRIP_NO_MATCH, None),
        ),
    ),
    (
        "genuinely absent: nobody has submitted this disc",
        _STATE_ABSENT,
        TrackResult(
            number=5,
            filename="05.flac",
            copy_crc="AAAA0005",
            status="ripped successfully",
        ),
    ),
)


def test_the_state_case_table_covers_every_accuraterip_state() -> None:
    """A floor, so the agreement test below cannot pass by examining nothing.

    Four states exist; a table that quietly lost one would still be green while
    guarding three quarters of the surface (the "can this check be satisfied by
    finding nothing?" rule in CLAUDE.md).
    """
    # Derived, not hardcoded: a state added to the classifier has to appear here.
    assert set(_LABEL_FOR_AR_STATE) == set(AR_STATES), (
        "verdict.AR_STATES and this file's label map have diverged — a new "
        f"classifier state needs a label and a case: "
        f"{set(AR_STATES) ^ set(_LABEL_FOR_AR_STATE)}"
    )
    wanted = {label for label in _LABEL_FOR_AR_STATE.values() if label}
    covered = {expected for _, expected, _ in AR_STATE_CASES}
    assert covered == wanted, (
        f"the case table no longer covers every AccurateRip state: missing "
        f"{wanted - covered}, unexpected {covered - wanted}"
    )
    assert len(AR_STATE_CASES) >= len(wanted)


def test_the_log_and_the_results_table_agree_on_the_accuraterip_state() -> None:
    """The agreement itself: one track, one state, two surfaces.

    Neither surface has to use the other's words — the log has room for a
    sentence, the table has room for two — but they may not place the same track
    in different states. This is the assertion that was missing when the log
    learned about the "in the database, no match" state and the table did not.
    """
    for name, expected, track in AR_STATE_CASES:
        log_state = _state_from_log_line(_accuraterip_line(track))
        table_state = _state_from_table_row(track)
        assert log_state == table_state, (
            f"{name}: the durable log puts this track in {log_state} but the "
            f"on-screen results table puts it in {table_state} — the same parsed "
            "track, two contradictory claims"
        )
        # And both must be in the state the DATA says, so an agreed-upon wrong
        # answer can't pass either.
        assert log_state == expected, (
            f"{name}: expected {expected}, both surfaces say {log_state}"
        )


def test_no_surface_calls_a_compared_track_absent_from_the_database() -> None:
    """The specific false claim, named. Regression for the 2026-07-31 finding.

    A track cyanrip compared against the database (it printed a checksum for it)
    is *in* that database. Saying "not in DB" — or the log's "not present" — about
    it is factually false, whichever surface says it.
    """
    compared = [
        (name, track)
        for name, expected, track in AR_STATE_CASES
        if expected == _STATE_NO_MATCH
    ]
    assert compared, "no compared-but-unmatched case left to check"
    for name, track in compared:
        line = _accuraterip_line(track)
        offset = track.accuraterip_offset
        cells = [
            _ar_cell(track.accuraterip_v1, offset_result=offset),
            _ar_cell(track.accuraterip_v2, offset_result=offset),
        ]
        assert "not present" not in line, f"{name}: the durable log claims absence"
        for cell in cells:
            assert cell != "not in DB", (
                f"{name}: the results table says {cell!r} about a track the "
                "database demonstrably has — the exact false claim the log's "
                "fourth state was added to remove"
            )


def test_the_per_track_log_line_is_what_the_rendered_log_actually_carries() -> None:
    """Pin the stand-in: `_accuraterip_line` is not a private detour.

    The agreement above compares two *private* per-track renderers, which is only
    meaningful if the log's line really reaches the durable artifact. Render the
    whole log for each case and find the line in it — otherwise this file could
    happily verify a function the user never sees.
    """
    for name, _, track in AR_STATE_CASES:
        rip_log = RipLog(
            log_creator="cyanrip 0.9.3",
            ripping_info=RippingInfo(drive="PIONEER BDR-209D"),
            tracks=(track,),
            health_status="No errors occurred",
        )
        text = render_eac_style_log(rip_log)
        assert _accuraterip_line(track) in text, (
            f"{name}: the per-track AccurateRip line never reaches the rendered "
            "EAC-compatible log"
        )


def test_every_scenario_track_lands_in_the_same_state_on_both_surfaces() -> None:
    """The same agreement over the whole-disc scenarios, not just the case table.

    Cheap breadth: the scenarios above are the real hardware runs, so any state
    they contain that the case table forgot is still covered here.
    """
    examined = 0
    for name, build in SCENARIOS.items():
        rip_log = build()
        for track in rip_log.tracks:
            log_state = _state_from_log_line(_accuraterip_line(track))
            table_state = _state_from_table_row(track)
            assert log_state == table_state, (
                f"{name}: track {track.number} is {log_state} in the durable log "
                f"and {table_state} in the results table"
            )
            examined += 1
    assert examined >= 12, f"only {examined} tracks examined across the scenarios"


def test_a_zero_checksum_is_never_a_match_on_any_surface() -> None:
    """cyanrip's own words: "a checksum of 0 is meaningless".

    It prints that caveat on an `Accurip 450:` row whose local CRC is all zeros —
    and still reports a confidence. Keying on the confidence alone turned that into
    a positive offset-variant match at confidence 200, so a track nothing was
    meaningfully compared for announced a partially-accurate match on the results
    table AND in the archival log.

    Keyed on the zero CRC rather than on cyanrip's wording, so a backend that omits
    the caveat is covered too.
    """
    track = TrackResult(
        number=9,
        filename="09.flac",
        copy_crc="AAAA0009",
        status="ripped successfully",
        accuraterip_lookup="disc found in database (max confidence: 200)",
        accuraterip_v1=_ar(1, _CYANRIP_NO_MATCH, None),
        accuraterip_v2=_ar(2, _CYANRIP_NO_MATCH, None),
        accuraterip_offset=_ar(
            450,
            "match found, confidence 200, but a checksum of 0 is meaningless",
            200,
            local_crc="00000000",
        ),
    )
    assert _state_from_table_row(track) != _STATE_OFFSET, (
        "an all-zero checksum was rendered as a partially-accurate match"
    )
    line = _accuraterip_line(track)
    assert "offset-variant" not in line, (
        f"the archival log claimed an offset-variant match from a zero CRC: {line!r}"
    )
    # And a REAL offset match on the same shape must still be recognised, so the
    # guard cannot pass by refusing everything.
    real = replace(
        track,
        accuraterip_offset=_ar(
            450,
            "matches Accurip DB, track is partially accurately ripped",
            200,
            local_crc="BF62B1DA",
        ),
    )
    assert _state_from_table_row(real) == _STATE_OFFSET
