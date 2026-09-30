"""The artifact verbs, end to end through the real runner.

Each test builds an album folder the way a rip leaves one — the committed round-29
report, the ripper's log it embeds, and one header-only FLAC per ripped track
(synthetic, no audio, never committed: Critical rule #8) — and a window whose
track table is the REAL `TrackTable`, so `expect-tags` compares against the
same widget a user edits and `track-title` goes through the same edit path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
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

_ROUND29 = Path(__file__).resolve().parent.parent / "docs/handshake/artifactsround29"
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
    win._current_release_id = (
        report["cover_art"]["release_id"] if report.get("cover_art") else ""
    )
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


def test_track_title_edits_through_the_real_table_and_expect_tags_reads_it(
    qapp, process_until, tmp_path
) -> None:
    """The escaping permutation: a title carrying `\\ = ' :` must reach the file."""
    title = "E=MC2: Rock 'n' Roll \\ Part 2"
    win = _rip(tmp_path, _load("overwrite"), titles={1: title, 2: _TITLES[2]})
    step = _run(win, qapp, process_until, f"track-title 1 {title}")
    assert step.outcome is Outcome.PASS, step.detail
    assert win._track_table.tracks()[0].title == title
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
