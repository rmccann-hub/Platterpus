"""Tests for the re-rip comparison + best-of assembler (rip_compare.py).

The comparison is the first-class version of a by-hand finding (2026-07-09): a
re-rip of The Police disc was byte-identical on 12/14 tracks but track 3 had
silently regressed from an exact AccurateRip match to an offset-variant one.
These tests pin that behaviour and the never-raises contract. Cases follow
docs/testing.md's taxonomy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from platterpus.rip_compare import (
    SIDE_A,
    SIDE_B,
    SIDE_EQUAL,
    SIDE_UNKNOWN,
    assemble_best_of,
    best_of_plan,
    compare_reports,
    disc_key,
    find_prior_report,
    load_report,
    render_best_of_plan,
    render_comparison,
)

# --- Report builders --------------------------------------------------------


def _track(
    number: int,
    crc: str,
    *,
    verified: bool = True,
    v_conf: int | None = 200,
    offset_conf: int | None = None,
    filename: str | None = None,
) -> dict:
    """Build one serialized-report track dict."""
    accuraterip = {
        "v1": {"confidence": v_conf} if verified else None,
        "v2": None,
        "offset_450": {"confidence": offset_conf} if offset_conf is not None else None,
    }
    return {
        "number": number,
        "filename": filename or f"{number:02d} - Track {number}.flac",
        "copy_crc": crc,
        "accuraterip_verified": verified,
        "accuraterip": accuraterip,
    }


def _report(
    *,
    tracks: list[dict],
    disc_id: str | None = "MBDISC1",
    cddb_id: str | None = "CDDB1",
    release_id: str | None = "REL1",
    version: str = "0.4.24",
    generated_at: str = "2026-07-08T00:00:00",
) -> dict:
    rip: dict = {"creation_date": generated_at}
    if disc_id is not None:
        rip["musicbrainz_disc_id"] = disc_id
    if cddb_id is not None:
        rip["cddb_id"] = cddb_id
    return {
        "schema_version": 9,
        "generator": {"name": "platterpus", "version": version},
        "generated_at": generated_at,
        "rip": rip,
        "disc": {"musicbrainz_release_id": release_id},
        "tracks": tracks,
    }


# --- disc_key precedence ----------------------------------------------------


def test_disc_key_prefers_mb_disc_id_then_cddb_then_release() -> None:
    assert disc_key(_report(tracks=[])) == "MBDISC1"
    assert disc_key(_report(tracks=[], disc_id=None)) == "CDDB1"
    assert disc_key(_report(tracks=[], disc_id=None, cddb_id=None)) == "REL1"
    assert (
        disc_key(_report(tracks=[], disc_id=None, cddb_id=None, release_id=None))
        is None
    )


def test_disc_key_tolerates_garbage() -> None:
    assert disc_key("not a dict") is None  # type: ignore[arg-type]
    assert disc_key({}) is None
    assert disc_key({"rip": {"musicbrainz_disc_id": "  "}}) is None  # blank ignored


# --- compare_reports: the core behaviours -----------------------------------


def test_identical_rips_report_ok() -> None:
    tracks = [_track(1, "AAAA1111"), _track(2, "BBBB2222")]
    comp = compare_reports(_report(tracks=tracks), _report(tracks=tracks))
    assert comp.same_disc is True
    assert comp.differing_count == 0
    assert comp.identical_count == 2
    assert comp.headline_level == "ok"
    assert all(t.better == SIDE_EQUAL for t in comp.tracks)


def test_regressed_track_prefers_the_exact_match_side() -> None:
    # The Police track-3 case: A is an exact match, B only offset-variant.
    a = _report(
        tracks=[_track(1, "SAME"), _track(3, "AAAA", verified=True, v_conf=200)]
    )
    b = _report(
        tracks=[
            _track(1, "SAME"),
            _track(3, "BBBB", verified=False, offset_conf=200),
        ]
    )
    comp = compare_reports(a, b)
    assert comp.differing_count == 1
    assert comp.identical_count == 1
    assert comp.a_better_tracks == (3,)
    assert comp.b_better_tracks == ()
    row = next(t for t in comp.tracks if t.number == 3)
    assert row.better == SIDE_A
    assert "exact" in row.reason.lower()
    assert comp.headline_level == "warn"


def test_both_offset_variant_equal_confidence_is_unknown() -> None:
    # The Police track-5 case: both reads are offset-variant, same confidence →
    # no basis to choose.
    a = _report(tracks=[_track(5, "AAAA", verified=False, offset_conf=200)])
    b = _report(tracks=[_track(5, "BBBB", verified=False, offset_conf=200)])
    comp = compare_reports(a, b)
    row = comp.tracks[0]
    assert row.better == SIDE_UNKNOWN
    # An ambiguous differing track is NOT credited to either side.
    assert comp.a_better_tracks == () and comp.b_better_tracks == ()
    assert comp.differing_count == 1


def test_confidence_breaks_a_tie_when_status_matches() -> None:
    a = _report(tracks=[_track(1, "AAAA", verified=True, v_conf=5)])
    b = _report(tracks=[_track(1, "BBBB", verified=True, v_conf=200)])
    comp = compare_reports(a, b)
    assert comp.tracks[0].better == SIDE_B
    assert comp.b_better_tracks == (1,)


def test_track_present_in_only_one_rip() -> None:
    a = _report(tracks=[_track(1, "AAAA"), _track(2, "BBBB")])
    b = _report(tracks=[_track(1, "AAAA")])  # missing track 2
    comp = compare_reports(a, b)
    row2 = next(t for t in comp.tracks if t.number == 2)
    assert row2.better == SIDE_A
    assert row2.crc_b is None
    # A track present on only one side isn't an identical/differing count.
    assert comp.identical_count == 1
    assert comp.differing_count == 0


def test_different_disc_is_flagged() -> None:
    a = _report(tracks=[_track(1, "AAAA")], disc_id="DISC_A")
    b = _report(tracks=[_track(1, "AAAA")], disc_id="DISC_B")
    comp = compare_reports(a, b)
    assert comp.same_disc is False
    assert any("different disc" in n.lower() for n in comp.notes)


def test_missing_disc_key_compares_positionally_with_note() -> None:
    a = _report(tracks=[_track(1, "AAAA")], disc_id=None, cddb_id=None, release_id=None)
    b = _report(tracks=[_track(1, "AAAA")], disc_id=None, cddb_id=None, release_id=None)
    comp = compare_reports(a, b)
    assert comp.same_disc is None
    assert any("same disc" in n.lower() for n in comp.notes)


def test_empty_reports_are_neutral_not_crashing() -> None:
    comp = compare_reports({}, {})
    assert comp.total == 0
    assert comp.headline_level == "neutral"


def test_compare_never_raises_on_garbage() -> None:
    comp = compare_reports("nonsense", None)  # type: ignore[arg-type]
    assert comp.headline_level == "neutral"
    assert comp.total == 0


def test_v8_report_without_disc_id_falls_back_to_release_id() -> None:
    # A pre-v9 report has no rip.musicbrainz_disc_id; the release id still keys.
    a = _report(tracks=[_track(1, "AAAA")], disc_id=None, cddb_id=None)
    b = _report(tracks=[_track(1, "AAAA")], disc_id=None, cddb_id=None)
    comp = compare_reports(a, b)
    assert comp.same_disc is True
    assert comp.disc_key_a == "REL1"


# --- load_report / find_prior_report (filesystem) ---------------------------


def test_load_report_handles_bad_inputs(tmp_path: Path) -> None:
    assert load_report(tmp_path / "nope.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_report(bad) is None
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")  # valid JSON, not a dict
    assert load_report(arr) is None
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_report(tracks=[_track(1, "AA")])), encoding="utf-8")
    assert isinstance(load_report(good), dict)


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report), encoding="utf-8")


def test_find_prior_report_returns_most_recent_same_disc(tmp_path: Path) -> None:
    root = tmp_path / "Music"
    current = root / "Album (2)" / "x.platterpus.json"
    older = root / "Album" / "x.platterpus.json"
    other = root / "Other" / "x.platterpus.json"
    _write_report(
        current,
        _report(tracks=[_track(1, "NEW")], generated_at="2026-07-08T00:00:00"),
    )
    _write_report(
        older,
        _report(tracks=[_track(1, "OLD")], generated_at="2026-07-01T00:00:00"),
    )
    _write_report(
        other,
        _report(tracks=[_track(1, "ZZZ")], disc_id="DIFFERENT"),
    )
    found = find_prior_report(current, root)
    assert found == older


def test_find_prior_report_picks_newest_of_several_priors(tmp_path: Path) -> None:
    # Several prior rips of the same disc; the one with the newest generated_at
    # must win. Regression for the recency-key bug where the sort compared ISO
    # strings against "mtime:…" strings, so ordering was by first character
    # ("m" > "2") rather than by actual time.
    root = tmp_path / "Music"
    current = root / "cur" / "x.platterpus.json"
    _write_report(
        current, _report(tracks=[_track(1, "NEW")], generated_at="2026-07-09T00:00:00")
    )
    _write_report(
        root / "old1" / "x.platterpus.json",
        _report(tracks=[_track(1, "O1")], generated_at="2026-07-01T00:00:00"),
    )
    newest = root / "old2" / "x.platterpus.json"
    _write_report(
        newest,
        _report(tracks=[_track(1, "O2")], generated_at="2026-07-05T00:00:00"),
    )
    _write_report(
        root / "old3" / "x.platterpus.json",
        _report(tracks=[_track(1, "O3")], generated_at="2026-06-15T00:00:00"),
    )
    assert find_prior_report(current, root) == newest


def test_find_prior_report_none_when_no_match(tmp_path: Path) -> None:
    root = tmp_path / "Music"
    current = root / "A" / "x.platterpus.json"
    _write_report(current, _report(tracks=[_track(1, "AAAA")], disc_id="ONLY"))
    assert find_prior_report(current, root) is None


def test_find_prior_report_none_without_disc_key(tmp_path: Path) -> None:
    root = tmp_path / "Music"
    current = root / "A" / "x.platterpus.json"
    sibling = root / "B" / "x.platterpus.json"
    no_key = _report(
        tracks=[_track(1, "AAAA")], disc_id=None, cddb_id=None, release_id=None
    )
    _write_report(current, no_key)
    _write_report(sibling, no_key)
    # No disc identity to match on → don't guess across the library.
    assert find_prior_report(current, root) is None


# --- best_of_plan + assemble_best_of ----------------------------------------


def test_best_of_plan_picks_the_better_side() -> None:
    a = _report(
        tracks=[
            _track(1, "SAME", filename="01.flac"),
            _track(3, "AEX", verified=True, filename="03.flac"),
        ]
    )
    b = _report(
        tracks=[
            _track(1, "SAME", filename="01.flac"),
            _track(3, "BOFF", verified=False, offset_conf=200, filename="03.flac"),
        ]
    )
    comp = compare_reports(a, b)
    plan = best_of_plan(comp, a, b)
    by_num = {e.number: e for e in plan.entries}
    assert by_num[1].side == SIDE_A  # identical → A
    assert by_num[3].side == SIDE_A  # exact beats offset
    assert plan.from_a == 2 and plan.from_b == 0


def test_best_of_plan_flags_ambiguous_tracks() -> None:
    a = _report(tracks=[_track(5, "AAAA", verified=False, offset_conf=200)])
    b = _report(tracks=[_track(5, "BBBB", verified=False, offset_conf=200)])
    comp = compare_reports(a, b)
    plan = best_of_plan(comp, a, b)
    assert plan.ambiguous_tracks == (5,)


def test_assemble_best_of_copies_chosen_files(tmp_path: Path) -> None:
    folder_a = tmp_path / "a"
    folder_b = tmp_path / "b"
    folder_a.mkdir()
    folder_b.mkdir()
    # Synthetic, non-audio stand-ins named like the report's FLACs (never real
    # audio — Critical rule #8; these live only in tmp_path).
    (folder_a / "01.flac").write_text("A-track1", encoding="utf-8")
    (folder_a / "03.flac").write_text("A-track3", encoding="utf-8")
    (folder_b / "01.flac").write_text("B-track1", encoding="utf-8")
    (folder_b / "03.flac").write_text("B-track3", encoding="utf-8")
    a = _report(
        tracks=[
            _track(1, "SAME", filename="01.flac"),
            _track(3, "AEX", verified=True, filename="03.flac"),
        ]
    )
    b = _report(
        tracks=[
            _track(1, "SAME", filename="01.flac"),
            _track(3, "BOFF", verified=False, offset_conf=200, filename="03.flac"),
        ]
    )
    comp = compare_reports(a, b)
    plan = best_of_plan(comp, a, b)
    dest = tmp_path / "best"
    result = assemble_best_of(plan, folder_a, folder_b, dest)
    assert result.error is None
    assert result.copied == 2
    assert set(result.copied_tracks) == {1, 3}
    # Both chosen from A → dest holds A's bytes.
    assert (dest / "03.flac").read_text() == "A-track3"
    # Sources untouched (non-destructive).
    assert (folder_a / "03.flac").read_text() == "A-track3"
    assert (folder_b / "03.flac").read_text() == "B-track3"


def test_assemble_best_of_records_missing_source(tmp_path: Path) -> None:
    folder_a = tmp_path / "a"
    folder_b = tmp_path / "b"
    folder_a.mkdir()
    folder_b.mkdir()
    (folder_a / "01.flac").write_text("A1", encoding="utf-8")
    # track 1 present, track 2's file is missing from A on purpose
    a = _report(
        tracks=[_track(1, "S", filename="01.flac"), _track(2, "S2", filename="02.flac")]
    )
    b = _report(
        tracks=[_track(1, "S", filename="01.flac"), _track(2, "S2", filename="02.flac")]
    )
    comp = compare_reports(a, b)
    plan = best_of_plan(comp, a, b)
    dest = tmp_path / "best"
    result = assemble_best_of(plan, folder_a, folder_b, dest)
    # track 1 copied; track 2 failed (no source file on the chosen side dir).
    assert result.copied == 1
    assert any("track 2" in f for f in result.failures)


def test_assemble_best_of_fatal_when_dest_unmakeable(tmp_path: Path) -> None:
    a = _report(tracks=[_track(1, "S", filename="01.flac")])
    comp = compare_reports(a, a)
    plan = best_of_plan(comp, a, a)
    # A file where the dest dir should go → mkdir fails → fatal error, no raise.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    result = assemble_best_of(plan, tmp_path, tmp_path, blocker)
    assert result.error is not None
    assert result.copied == 0


# --- Rendering (smoke) ------------------------------------------------------


def test_render_comparison_and_plan_are_readable() -> None:
    a = _report(tracks=[_track(1, "AAAA"), _track(2, "BBBB", verified=True, v_conf=5)])
    b = _report(tracks=[_track(1, "AAAA"), _track(2, "CCCC", verified=True, v_conf=9)])
    comp = compare_reports(a, b)
    text = render_comparison(comp)
    assert "Comparing:" in text
    assert "Better" in text
    plan_text = render_best_of_plan(best_of_plan(comp, a, b))
    assert "Best-of plan:" in plan_text


@pytest.mark.parametrize("junk", ["", "x", "{}", "[]"])
def test_load_report_various_junk(tmp_path: Path, junk: str) -> None:
    p = tmp_path / "j.json"
    p.write_text(junk, encoding="utf-8")
    # Never raises; returns dict only for a JSON object.
    assert load_report(p) in (None, {}) or isinstance(load_report(p), dict)


# --- Review-driven edge cases (2026-07-09 adversarial review) ----------------


def test_dropped_track_is_flagged_not_hidden_as_ok() -> None:
    # A={1,2,3}, B={1,2}: track 3 vanished from the re-rip. Must NOT read as a
    # green "all identical" — the missing track has to surface.
    a = _report(tracks=[_track(1, "AA"), _track(2, "BB"), _track(3, "CC")])
    b = _report(tracks=[_track(1, "AA"), _track(2, "BB")])
    comp = compare_reports(a, b)
    assert comp.headline_level == "warn"
    assert "3" in comp.summary
    assert "not this one" in comp.summary


def test_added_track_is_flagged() -> None:
    a = _report(tracks=[_track(1, "AA")])
    b = _report(tracks=[_track(1, "AA"), _track(2, "BB")])
    comp = compare_reports(a, b)
    assert comp.headline_level == "warn"
    assert "this rip has track(s) 2" in comp.summary


def test_zero_overlap_same_disc_is_neutral_not_ok() -> None:
    # Same disc id, disjoint track numbers → nothing actually compared.
    a = _report(tracks=[_track(1, "AA")])
    b = _report(tracks=[_track(2, "BB")])
    comp = compare_reports(a, b)
    assert comp.headline_level == "neutral"
    assert "no tracks in common" in comp.summary.lower()


def test_v8_prior_vs_v9_current_is_same_disc_via_release_id() -> None:
    # The first re-rip after upgrading to v9: prior report has only the release
    # id, current has disc_id + release_id. They must still match on the release.
    v8 = _report(tracks=[_track(1, "AA")], disc_id=None, cddb_id=None)
    v9 = _report(tracks=[_track(1, "AA")])  # has disc_id + cddb + release
    comp = compare_reports(v8, v9)
    assert comp.same_disc is True


def test_boxset_discs_sharing_release_are_different_via_disc_id() -> None:
    # Two discs of one box set share a release id but have different disc IDs —
    # the disc ID must win (different discs), not the shared release.
    d1 = _report(tracks=[_track(1, "AA")], disc_id="DISC1")
    d2 = _report(tracks=[_track(1, "BB")], disc_id="DISC2")
    comp = compare_reports(d1, d2)
    assert comp.same_disc is False


def test_same_disc_helper_priority() -> None:
    from platterpus.rip_compare import same_disc

    # Both have disc_id → decisive even if release differs.
    a = _report(tracks=[], disc_id="D", release_id="R1")
    b = _report(tracks=[], disc_id="D", release_id="R2")
    assert same_disc(a, b) is True
    # No shared comparable field → None.
    only_disc = _report(tracks=[], disc_id="D", cddb_id=None, release_id=None)
    only_rel = _report(tracks=[], disc_id=None, cddb_id=None, release_id="R")
    assert same_disc(only_disc, only_rel) is None


def test_offset_variant_confidence_tiebreak_prefers_higher() -> None:
    # The realistic tie: both offset-variant, DIFFERENT confidence → higher wins.
    a = _report(tracks=[_track(1, "AA", verified=False, offset_conf=120)])
    b = _report(tracks=[_track(1, "BB", verified=False, offset_conf=200)])
    comp = compare_reports(a, b)
    assert comp.tracks[0].better == SIDE_B
    assert comp.b_better_tracks == (1,)


def test_not_in_db_tie_reason_omits_confidence() -> None:
    a = _report(tracks=[_track(1, "AA", verified=False)])  # not in DB
    b = _report(tracks=[_track(1, "BB", verified=False)])  # not in DB, differs
    comp = compare_reports(a, b)
    row = comp.tracks[0]
    assert row.better == SIDE_UNKNOWN
    assert "confidence" not in row.reason  # no meaningless "equal confidence"


def test_find_prior_report_matches_v8_prior_from_v9_current(tmp_path: Path) -> None:
    # Regression for the feature's most likely first use: a v9 re-rip must find
    # its v8 predecessor (shared release id, different strongest-key type).
    root = tmp_path / "Music"
    current = root / "Album (2)" / "x.platterpus.json"
    prior = root / "Album" / "x.platterpus.json"
    _write_report(current, _report(tracks=[_track(1, "NEW")]))  # v9: disc_id+rel
    _write_report(
        prior,
        _report(tracks=[_track(1, "OLD")], disc_id=None, cddb_id=None),  # v8: rel only
    )
    assert find_prior_report(current, root) == prior


def test_best_of_fallback_to_worse_side_is_flagged(tmp_path: Path) -> None:
    # Track 1 differs; A is the exact match but has NO filename recorded, B is
    # offset-variant with a filename. The plan must fall back to B AND flag it
    # (we'd be copying the worse read as "best-of").
    a = _report(tracks=[_track(1, "AA", verified=True, filename=None)])
    # _track always sets a filename; strip it to simulate a missing name.
    a["tracks"][0]["filename"] = None
    b = _report(
        tracks=[_track(1, "BB", verified=False, offset_conf=200, filename="01.flac")]
    )
    comp = compare_reports(a, b)
    plan = best_of_plan(comp, a, b)
    entry = plan.entries[0]
    assert entry.side == SIDE_B  # fell back to the only side with a file
    assert 1 in plan.ambiguous_tracks  # ...and flagged it


def test_best_of_plan_never_raises_on_garbage() -> None:
    # best_of_plan must not raise even if handed non-dict reports.
    comp = compare_reports({}, {})
    plan = best_of_plan(comp, None, None)  # type: ignore[arg-type]
    assert plan.entries == ()
