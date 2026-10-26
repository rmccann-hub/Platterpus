"""The artifact verbs, end to end through the real runner.

Each test builds an album folder the way a rip leaves one — the committed round-29
report (through its fixture), the ripper's log it embeds, and one header-only FLAC per ripped track
(synthetic, no audio, never committed: Critical rule #8) — and a window whose
track table is the REAL `TrackTable`, so `expect-tags` compares against the
same widget a user edits and `track-title` goes through the same edit path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from evidence_paths import evidence_dir
from test_flac_metadata import build_flac, picture_payload
from test_uiscript_rip_verbs import _step_outcome, _window

from platterpus.adapters.musicbrainz_client import TrackSummary
from platterpus.config import Config
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_audit import MIN_PLAUSIBLE_TRACK_BYTES
from platterpus.uiscript import artifact_verbs
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner

pytest.importorskip("PySide6.QtWidgets")

#: Through its fixtures (HR-2 moved the folder off `main`): slim extracts without
#: `debug.lines`, which no verb here reads.
_ROUND29 = evidence_dir("docs/handshake/artifactsround29")
_ALBUM = "full acceptance: angle<bracket"
_ARTIST = "Platterpus Acceptance"
_TITLES = {1: "Roxanne", 2: "Can’t Stand Losing You"}


@pytest.fixture(autouse=True)
def _short_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """The product waits 600 s for a record to settle; a test cannot."""
    monkeypatch.setattr(artifact_verbs, "ARTIFACT_WAIT_S", 0.5)


def _load(name: str) -> dict[str, Any]:
    loaded = json.loads((_ROUND29 / f"round29full{name}report.json").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _handed(table: Any) -> Any:
    """The tags a rip is handed at Start, built from the table as the window
    builds them (`RipMixin._rip_metadata_for`: album fields and each row)."""
    from platterpus.adapters.rip_backend import RipMetadata, TrackTag

    album = table.album_metadata()
    return RipMetadata(
        album_artist=album.artist,
        album_title=album.title,
        year=album.year,
        tracks=tuple(
            TrackTag(number=t.number, title=t.title, artist=t.artist_credit)
            for t in table.tracks()
        ),
    )


def _start_snapshot(win: Any) -> None:
    """Freeze the table onto the rip's record, as `_start_rip_worker` does."""
    win._post_rip_records[1].metadata = _handed(win._track_table)


def _rip(
    tmp_path: Path,
    report: dict[str, Any],
    *,
    titles: dict[int, str] | None = None,
    pictures: dict[int, int] | None = None,
    write_report: bool = True,
    cover_art: str = "embed",
) -> Any:
    """An album folder as a finished rip leaves it, and a window pointed at it."""
    from platterpus.ui.track_table import TrackTable

    folder = tmp_path / "album"
    folder.mkdir(parents=True)
    log_text = report["artifacts"]["rip_log"]["text"]
    log_file = folder / "rip.log"
    log_file.write_text(log_text, encoding="utf-8")
    if write_report:
        (folder / "rip.platterpus.json").write_text(json.dumps(report), "utf-8")
    written = titles if titles is not None else _TITLES
    for track in report.get("tracks") or []:
        number = track["number"]
        path = build_flac(
            folder / Path(track["filename"]).name,
            [
                f"ALBUM={_ALBUM}",
                f"ALBUMARTIST={_ARTIST}",
                f"TITLE={written.get(number, '')}",
                f"ARTIST={_ARTIST}",
                f"TRACKNUMBER={number}",
            ],
            [picture_payload()] * (pictures or {}).get(number, 1),
        )
        # Past the audit's size floor, as a real track is; the reader stops at
        # the last metadata block, so these bytes stand where audio frames would.
        with path.open("ab") as handle:
            handle.write(b"\0" * MIN_PLAUSIBLE_TRACK_BYTES)
    table = TrackTable()
    table._model.set_tracks(
        [TrackSummary(n, t, artist_credit=_ARTIST) for n, t in sorted(_TITLES.items())]
    )
    table._album_title_edit.setText(_ALBUM)
    table._album_artist_edit.setText(_ARTIST)
    win = _window(
        last_rip_log=parse_cyanrip_log(log_text),
        last_rip_log_file=log_file,
        track_table=table,
        config=Config(cover_art=cover_art),
    )
    from platterpus.ui.post_rip_record import PostRipRecord

    # The rip's own record, as the window keeps it: the folder its log went to
    # and the tags it was handed at Start. The graders read this, not the table.
    win._post_rip_records = {1: PostRipRecord(generation=1, log_file=log_file)}
    _start_snapshot(win)
    return win


def _run(win: Any, qapp: Any, process_until: Any, source: str) -> Any:
    return _step_outcome(ScriptRunner(win), qapp, process_until, source)


def test_expect_tags_passes_when_every_file_says_what_the_table_says(
    qapp, process_until, tmp_path
) -> None:
    step = _run(_rip(tmp_path, _load("overwrite")), qapp, process_until, "expect-tags")
    assert step.outcome is Outcome.PASS, step.detail


def test_expect_tags_fails_on_a_title_that_lost_its_apostrophe(
    qapp, process_until, tmp_path
) -> None:
    win = _rip(
        tmp_path, _load("overwrite"), titles={1: "Roxanne", 2: "Cant Stand Losing You"}
    )
    step = _run(win, qapp, process_until, "expect-tags")
    assert step.outcome is Outcome.FAIL and "track 2: TITLE" in step.detail


def test_expect_tags_writes_the_first_flacs_tags_as_text_to_the_run_folder(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    """The fork's round 30 lap 3 S24: the bundle carries no audio, so the tags
    travel as text, read by the same reader the grade uses."""
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )
    step = _run(_rip(tmp_path, _load("overwrite")), qapp, process_until, "expect-tags")
    assert step.outcome is Outcome.PASS, step.detail
    saved = list((tmp_path / "share" / "uiscript").rglob("tags*.txt"))
    assert len(saved) == 1, saved
    text = saved[0].read_text("utf-8")
    assert text.startswith("# track 1: ")
    assert "TITLE=Roxanne\n" in text and f"ALBUM={_ALBUM}\n" in text
    assert "# picture: type 3, image/jpeg," in text
    # One track, as S24 asked: the second track's title is not in it.
    assert "Losing You" not in text


def test_expect_tags_writes_the_tags_even_when_the_grade_fails(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    """The text is evidence of what the file holds, most of all when it is wrong."""
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )
    win = _rip(tmp_path, _load("overwrite"), titles={1: "Roxane", 2: _TITLES[2]})
    step = _run(win, qapp, process_until, "expect-tags")
    assert step.outcome is Outcome.FAIL
    (saved,) = (tmp_path / "share" / "uiscript").rglob("tags*.txt")
    assert "TITLE=Roxane\n" in saved.read_text("utf-8")


def test_render_tags_shows_a_newline_in_a_value_as_an_escape(tmp_path) -> None:
    """A value holding a newline must not read as a second tag."""
    from platterpus.uiscript.tag_grading import render_tags

    path = build_flac(tmp_path / "01.flac", ["TITLE=one\nARTIST=forged", "ALBUM=a"], [])
    text = render_tags([(1, path)])
    assert "TITLE=one\\x0aARTIST=forged" in text
    assert "\nARTIST=forged" not in text
    assert "# 1 control character(s) shown as \\xNN escapes" in text


def test_render_tags_says_when_a_file_could_not_be_read(tmp_path) -> None:
    from platterpus.uiscript.tag_grading import render_tags

    bogus = tmp_path / "01.flac"
    bogus.write_bytes(b"not a flac")
    text = render_tags([(1, bogus)])
    assert "# not read completely:" in text


def test_track_title_edits_through_the_real_table_and_expect_tags_reads_it(
    qapp, process_until, tmp_path
) -> None:
    """The escaping permutation: a title carrying `\\ = ' :` must reach the file."""
    title = "E=MC2: Rock 'n' Roll \\ Part 2"
    win = _rip(tmp_path, _load("overwrite"), titles={1: title, 2: _TITLES[2]})
    step = _run(win, qapp, process_until, f"track-title 1 {title}")
    assert step.outcome is Outcome.PASS, step.detail
    assert win._track_table.tracks()[0].title == title
    _start_snapshot(win)  # the script's `rip` comes after `track-title`
    assert _run(win, qapp, process_until, "expect-tags").outcome is Outcome.PASS


def test_track_title_is_refused_while_the_table_is_locked(
    qapp, process_until, tmp_path
) -> None:
    win = _rip(tmp_path, _load("overwrite"))
    win._track_table.set_locked(True)
    step = _run(win, qapp, process_until, "track-title 1 anything")
    assert step.outcome is Outcome.FAIL and "locked" in step.detail
    assert win._track_table.tracks()[0].title == "Roxanne"


def test_expect_cover_art_passes_and_fails_on_the_files(
    qapp, process_until, tmp_path
) -> None:
    ok = _run(
        _rip(tmp_path / "a", _load("overwrite")),
        qapp,
        process_until,
        "expect-cover-art",
    )
    assert ok.outcome is Outcome.PASS, ok.detail
    missing = _rip(tmp_path / "b", _load("overwrite"), pictures={1: 1, 2: 0})
    step = _run(missing, qapp, process_until, "expect-cover-art")
    assert step.outcome is Outcome.FAIL and "track(s) 2" in step.detail


def test_expect_cover_art_is_blocked_when_no_cover_was_fetched(
    qapp, process_until, tmp_path
) -> None:
    report = _load("overwrite")
    report["cover_art"].update(found=False, reason="none", embedded_count=0)
    step = _run(
        _rip(tmp_path, report, pictures={1: 0, 2: 0}),
        qapp,
        process_until,
        "expect-cover-art",
    )
    assert step.outcome is Outcome.BLOCKED, step.detail


def test_expect_cover_art_off_means_no_picture_anywhere(
    qapp, process_until, tmp_path
) -> None:
    report = _load("overwrite")
    report["cover_art"].update(mode="", embedded_count=0)
    step = _run(
        _rip(tmp_path, report, cover_art=""), qapp, process_until, "expect-cover-art"
    )
    assert step.outcome is Outcome.FAIL and "embeds nothing" in step.detail


def test_the_record_verbs_pass_a_real_rip(qapp, process_until, tmp_path) -> None:
    win = _rip(tmp_path, _load("overwrite"))
    for source in ("expect-album-audit", "expect-accuraterip", "expect-ctdb partial"):
        step = _run(win, qapp, process_until, source)
        assert step.outcome is Outcome.PASS, (source, step.detail)
    step = _run(win, qapp, process_until, "expect-ctdb whole")
    assert step.outcome is Outcome.FAIL, step.detail


def test_an_unfinished_rip_fails_the_graders_except_the_log_question(
    qapp, process_until, tmp_path
) -> None:
    win = _rip(tmp_path, _load("cancelme"))
    step = _run(win, qapp, process_until, "expect-accuraterip")
    assert step.outcome is Outcome.FAIL and "did not finish" in step.detail
    step = _run(win, qapp, process_until, "expect-album-audit ripper_log_integrity")
    assert step.outcome is Outcome.PASS, step.detail


def test_a_record_that_never_settles_is_not_graded(
    qapp, process_until, tmp_path
) -> None:
    """No report at all: the verb waits, then FAILs rather than grading nothing."""
    win = _rip(tmp_path, _load("overwrite"), write_report=False)
    step = _run(win, qapp, process_until, "expect-ctdb partial")
    assert step.outcome is Outcome.FAIL and "did not settle" in step.detail


# --- Run A on 0.7.112: the window was cleared before section F graded --------


def test_section_f_grades_the_rips_record_after_the_window_was_cleared(
    qapp, process_until, tmp_path
) -> None:
    """App log lines 649-730 of bundle platterpusbundle20261021t113505z: a drive
    flicker cleared the table and the release 41 s after the rip, and section F
    then failed correct files ("the window has no row for it"; "mode 'embed'
    embeds nothing, yet track(s) 1 … 14 carry a picture"). Both verbs now grade
    against the rip's record, so clearing the window changes nothing."""
    win = _rip(tmp_path, _load("overwrite"))
    win._track_table.clear()  # what `_reset_disc_view` did
    win._current_release_id = ""
    tags = _run(win, qapp, process_until, "expect-tags")
    cover = _run(win, qapp, process_until, "expect-cover-art")
    assert tags.outcome is Outcome.PASS, tags.detail
    assert cover.outcome is Outcome.PASS, cover.detail


def test_expect_tags_says_so_when_no_record_of_the_rip_is_kept(
    qapp, process_until, tmp_path
) -> None:
    """No record of what the rip was handed: an ERROR naming that, never a
    comparison with whatever the table holds now."""
    win = _rip(tmp_path, _load("overwrite"))
    win._post_rip_records = {}
    step = _run(win, qapp, process_until, "expect-tags")
    assert step.outcome is Outcome.ERROR and "no record of the tags" in step.detail


def test_expect_tags_grades_the_record_not_a_later_edit_of_the_table(
    qapp, process_until, tmp_path
) -> None:
    """The relation: the files are compared with what the rip was handed, so an
    edit made after Start (or a scan that rewrote the table) cannot make correct
    files fail, and a wrong file still fails."""
    win = _rip(tmp_path, _load("overwrite"))
    assert win._track_table.edit_track_title(1, "Changed after the rip") == ""
    step = _run(win, qapp, process_until, "expect-tags")
    assert step.outcome is Outcome.PASS, step.detail
    wrong = _rip(tmp_path / "w", _load("overwrite"), titles={1: "Roxane", 2: "x"})
    assert _run(wrong, qapp, process_until, "expect-tags").outcome is Outcome.FAIL


def test_expect_cover_art_reads_the_release_from_the_report(tmp_path) -> None:
    """The pure half: an unknown disc's report names no release; a report with
    no disc block is not determined, never "expect nothing"."""
    from platterpus.uiscript.tag_grading import grade_cover_art, report_release_id

    report = _load("overwrite")
    assert report_release_id(report) == report["disc"]["musicbrainz_release_id"]
    assert report_release_id({"disc": {"musicbrainz_release_id": None}}) == ""
    assert report_release_id({}) is None
    grade = grade_cover_art([], {}, "embed", None)
    assert grade.blocked and grade.detail.startswith("not determined"), grade


# --- Run C on 0.7.112: the cover step landed after the grade ------------------


def test_a_missing_cover_art_result_is_not_determined_never_zero(tmp_path) -> None:
    """Run C's app log line 17625: "the report says 0 file(s) took the cover; the
    files hold 16", graded 91 s before the cover step recorded its result (line
    17719). An absent block is "not determined", not a count of zero."""
    from platterpus.uiscript.tag_grading import cover_art_pending, grade_cover_art

    report = _load("overwrite")
    del report["cover_art"]
    assert cover_art_pending(report, "embed")
    assert not cover_art_pending(report, "")  # nothing asked for, nothing pending
    grade = grade_cover_art(
        [], report, "embed", report["disc"]["musicbrainz_release_id"]
    )
    assert grade.blocked and grade.detail.startswith("not determined"), grade
    assert "0 file(s)" not in grade.detail


def test_expect_cover_art_waits_for_a_cover_result_that_lands_late(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    """The report settles without the cover step, which is not a gate; the verb
    waits for its result rather than grading the record without it."""
    from PySide6.QtCore import QTimer

    monkeypatch.setattr(artifact_verbs, "ARTIFACT_WAIT_S", 20.0)
    monkeypatch.setattr(artifact_verbs, "COVER_ART_WAIT_S", 10.0)
    full = _load("overwrite")
    early = dict(full)
    del early["cover_art"]
    win = _rip(tmp_path, early)
    (report_file,) = (tmp_path / "album").glob("*.platterpus.json")
    QTimer.singleShot(300, lambda: report_file.write_text(json.dumps(full), "utf-8"))
    step = _run(win, qapp, process_until, "expect-cover-art")
    assert step.outcome is Outcome.PASS, step.detail
    assert step.elapsed_s >= 0.2, "graded before the cover result landed"


def test_expect_cover_art_says_not_determined_when_the_result_never_lands(
    qapp, process_until, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(artifact_verbs, "ARTIFACT_WAIT_S", 20.0)
    monkeypatch.setattr(artifact_verbs, "COVER_ART_WAIT_S", 0.3)
    report = _load("overwrite")
    del report["cover_art"]
    step = _run(_rip(tmp_path, report), qapp, process_until, "expect-cover-art")
    assert step.outcome is Outcome.BLOCKED, step.detail
    assert step.detail.startswith("not determined"), step.detail
