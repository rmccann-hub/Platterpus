"""`expect-pregaps-agree` (TASKS R10): do the rips of one disc agree on its pregaps?

On the 2026-10-13 Full run the secure re-read left track 4's 158-frame pregap out
of its `Gaps:` list while the whole-disc rip of the same disc listed it, and track
9 read 94 frames in some rips and 95 in others. The fork found it (their round 32
lap 9 S4); nothing of ours compared two rips of one disc, so nothing could have.

**The real-log test is the one that matters**: it reads the logs as filed in
`docs/handshake/artifactsround32/` (from their fixtures since HR-2 moved that folder
to the evidence branch) and requires EXACTLY tracks 4 and 9, with the
secure re-read as the one log reading track 4 as none. A grader that found
nothing, or found everything, fails it. The synthetic cases pin the floor
(fewer than two logs of one disc is never "agree") and the edges of the grammar.

**What the stand-ins do that the product does not** (`CLAUDE.md`): the handler
tests use the uiscript tests' stand-in window, whose only relevant attribute is
`_config.output_dir`, the same one the product's `cyanrip` verb reads. The rips
folder is a real `tmp_path` holding copies of real logs, so the scan, the
modification-time scope and the parse are the product's own.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any

import pytest
from evidence_paths import FIXTURE_ROOT as EVIDENCE_ROOT
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.config import Config
from platterpus.uiscript import pregap_grading as grading
from platterpus.uiscript import pregap_verbs
from platterpus.uiscript.report import Outcome

_REPO = Path(__file__).resolve().parent.parent
#: The run folder moved to the evidence branch (HR-2); its logs and the two
#: securing passes' logs are read from their byte-for-byte fixtures.
_ROUND32 = EVIDENCE_ROOT / "docs/handshake/artifactsround32"
#: The run filed 11 album logs and 2 securing-pass logs (13). Several tests size
#: themselves from `_round32_logs()`, so an empty glob would let them agree with
#: nothing; the floor makes a missing folder fail instead.
_ROUND32_FLOOR = 13
_ACCEPTANCE = _REPO / "src/platterpus/rig_scripts/fullacceptance.txt"

#: The secure re-read's log: the one rip of the run that read track 4 as none.
_SECURE_REREAD = "round32fullsecurereread"


def _round32_logs() -> list[Path]:
    """Every cyanrip log the 2026-10-13 run filed: the album logs (not our
    EAC-layout exports) and the two securing passes' own logs."""
    logs = [
        path
        for path in sorted(_ROUND32.glob("round32full*.log"))
        if not path.name.endswith("eac.log")
    ]
    logs += sorted(_ROUND32.glob("round32full*securingpass.txt"))
    assert len(logs) >= _ROUND32_FLOOR, (
        f"only {len(logs)} round-32 logs under {_ROUND32}"
    )
    return logs


def _gap_log(disc_id: str, gaps: list[str], *, banner: bool = True) -> str:
    """A minimal cyanrip log: the banner, a Disc ID and a `Gaps:` block."""
    head = (
        "cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)\n" if banner else ""
    )
    disc = f"DiscID:         {disc_id}\n" if disc_id else ""
    block = "".join(f"    {line}\n" for line in gaps)
    return f"{head}{disc}CDDB ID:        E20DFE0E\nGaps:\n{block}\nTracks:\n"


_DISC = "pNtImOkdBm9RMBIalzx0w9cfsYY-"
_GAPS = [
    "160 frame pregap in track 2, merging into track 1",
    "158 frame pregap in track 4, merging into track 3",
]


# --- The filed run: exactly tracks 4 and 9 ------------------------------------


def test_the_filed_round_32_logs_differ_at_exactly_tracks_4_and_9() -> None:
    logs = _round32_logs()
    # Floor on the fixture itself: the filing has eleven album logs and two
    # securing-pass logs. Fewer means the glob stopped matching, and a comparison
    # of almost nothing would pass for the wrong reason.
    assert len(logs) >= 12, f"only {len(logs)} round-32 logs found"
    readings = [grading.read_gap_list(p.read_text("utf-8"), p.stem) for p in logs]
    assert all(r.pregaps is not None and r.disc_id == _DISC for r in readings), [
        (r.label, r.problem) for r in readings if r.pregaps is None
    ]

    result = grading.compare(readings)

    assert result.state == grading.DIFFER, result.detail
    assert result.differing_tracks == (4, 9), result.detail
    assert result.compared == len(logs)
    by_track = {d.track: dict(d.readings) for d in result.differences}
    # Track 4: 158 frames everywhere but the secure re-read, which read none.
    assert by_track[4][0] == (_SECURE_REREAD,), by_track[4]
    assert set(by_track[4]) == {158, 0}
    assert _SECURE_REREAD not in by_track[4][158]
    # Track 9: the whole-disc rip read 95, the secure re-read 94.
    assert set(by_track[9]) == {95, 94}
    assert "round32fullwholedisc" in by_track[9][95]
    assert _SECURE_REREAD in by_track[9][94]
    # The detail names both tracks, marked, and says it is gathered.
    assert result.detail.startswith("⚠"), result.detail
    assert "track 4 " in result.detail and "track 9 " in result.detail
    assert "subchannel-pregap-varies" in result.detail


def test_without_the_secure_reread_track_4_agrees_and_only_9_differs() -> None:
    """The relation the finding rests on: the secure re-read alone omits track 4."""
    readings = [
        grading.read_gap_list(p.read_text("utf-8"), p.stem)
        for p in _round32_logs()
        if p.stem != _SECURE_REREAD
    ]
    result = grading.compare(readings)
    assert result.state == grading.DIFFER
    assert result.differing_tracks == (9,), result.detail


# --- The floor ---------------------------------------------------------------


def test_no_logs_is_not_determined_never_agree() -> None:
    result = grading.compare([])
    assert result.state == grading.NOT_DETERMINED
    assert result.compared == 0
    assert "not a pass" in result.detail


def test_one_log_of_a_disc_is_not_determined() -> None:
    one = grading.read_gap_list(_gap_log(_DISC, _GAPS), "only")
    result = grading.compare([one])
    assert result.state == grading.NOT_DETERMINED, result.detail
    assert "'only'" in result.detail and "nothing to compare" in result.detail


def test_two_logs_of_two_different_discs_compare_nothing() -> None:
    first = grading.read_gap_list(_gap_log(_DISC, _GAPS), "a")
    second = grading.read_gap_list(_gap_log("AnotherDisc000000000000000-", []), "b")
    assert grading.compare([first, second]).state == grading.NOT_DETERMINED


def test_an_unreadable_list_does_not_count_toward_the_floor() -> None:
    good = grading.read_gap_list(_gap_log(_DISC, _GAPS), "good")
    odd = grading.read_gap_list(_gap_log(_DISC, ["a gap somewhere"]), "odd")
    result = grading.compare([good, odd])
    assert odd.pregaps is None and "does not read" in odd.problem
    assert result.state == grading.NOT_DETERMINED
    assert "'odd'" in result.detail, "a set-aside log is named, never dropped"


# --- Agreement and the grammar's edges ----------------------------------------


def test_identical_lists_agree() -> None:
    readings = [grading.read_gap_list(_gap_log(_DISC, _GAPS), n) for n in "abc"]
    result = grading.compare(readings)
    assert result.state == grading.AGREE, result.detail
    assert result.compared == 3
    assert result.differences == ()
    assert result.detail.startswith("✓")


def test_a_zero_frame_line_and_a_missing_line_both_mean_no_pregap() -> None:
    explicit = grading.read_gap_list(
        _gap_log(_DISC, ["0 frame pregap in track 1, unmerged", *_GAPS]), "explicit"
    )
    silent = grading.read_gap_list(_gap_log(_DISC, _GAPS), "silent")
    assert grading.compare([explicit, silent]).state == grading.AGREE


def test_the_merge_clause_is_a_setting_and_is_not_compared() -> None:
    merged = grading.read_gap_list(_gap_log(_DISC, _GAPS), "merged")
    unmerged = grading.read_gap_list(
        _gap_log(_DISC, [g.split(",")[0] + ", unmerged" for g in _GAPS]), "unmerged"
    )
    assert grading.compare([merged, unmerged]).state == grading.AGREE


def test_none_signalled_is_an_empty_list_not_an_unknown_one() -> None:
    stock = grading.read_gap_list(_gap_log(_DISC, ["None signalled"]), "stock")
    assert stock.pregaps == {}


def test_a_log_with_no_gaps_block_is_not_determined() -> None:
    text = "cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)\n"
    reading = grading.read_gap_list(text + f"DiscID:         {_DISC}\n", "nogaps")
    assert reading.pregaps is None
    assert "no Gaps: block" in reading.problem


def test_a_log_without_a_disc_id_is_set_aside() -> None:
    reading = grading.read_gap_list(_gap_log("", _GAPS), "anonymous")
    assert reading.disc_id == ""
    assert "no Disc ID" in reading.problem


def test_a_file_cyanrip_did_not_write_is_not_read_as_a_log() -> None:
    reading = grading.read_gap_list(_gap_log(_DISC, _GAPS, banner=False), "eac")
    assert reading.pregaps is None
    assert "not a log cyanrip wrote" in reading.problem


def test_one_differing_frame_is_a_difference() -> None:
    """Track 9's 94 against 95: the smallest disagreement still counts."""
    first = grading.read_gap_list(_gap_log(_DISC, _GAPS), "a")
    second = grading.read_gap_list(
        _gap_log(_DISC, [_GAPS[0], _GAPS[1].replace("158", "157")]), "b"
    )
    result = grading.compare([first, second])
    assert result.state == grading.DIFFER
    assert result.differing_tracks == (4,)


@settings(max_examples=150, deadline=None)
@given(st.text(max_size=300))
def test_parse_gap_lines_never_raises(text: str) -> None:
    pregaps, problem = grading.parse_gap_lines(text)
    assert pregaps is not None or problem


@settings(max_examples=150, deadline=None)
@given(st.text(max_size=400))
def test_read_gap_list_never_raises(text: str) -> None:
    grading.read_gap_list(text, "fuzz")


def test_an_absurdly_long_number_never_raises() -> None:
    reading = grading.read_gap_list(
        _gap_log(_DISC, ["9" * 5000 + " frame pregap in track 4"]), "long"
    )
    assert reading.pregaps is None


# --- The scan: which files count ----------------------------------------------


def _rips_folder(root: Path) -> None:
    """The filed run laid out as a rips folder: each log in its own album folder."""
    for log in _round32_logs():
        if log.name.endswith("securingpass.txt"):
            album = log.stem.removesuffix("securingpass")
            folder = root / album
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(log, folder / f"{album}.platterpus-securing-pass.txt")
        else:
            folder = root / log.stem
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(log, folder / log.name)
    eac = _ROUND32 / "round32fullwholedisceac.log"
    shutil.copyfile(eac, root / "round32fullwholedisc" / "export (EAC-compatible).log")


def test_the_scan_reads_this_runs_logs_and_the_securing_passes(tmp_path: Path) -> None:
    _rips_folder(tmp_path)
    scan = pregap_verbs.scan_run_logs(tmp_path, since=0.0)
    labels = {r.label for r in scan.readings}
    assert len(scan.readings) == len(_round32_logs())
    assert "round32fullsecurereread (securing pass)" in labels
    assert scan.not_cyanrip == 1, "the EAC-layout export is counted, not compared"
    outcome, detail, state = pregap_verbs.answer(scan)
    assert (outcome, state) == (Outcome.INFO, grading.DIFFER)
    assert "1 other .log file" in detail


def test_the_scan_leaves_out_logs_from_before_the_run(tmp_path: Path) -> None:
    _rips_folder(tmp_path)
    old = tmp_path / "round32fullsecurereread" / "round32fullsecurereread.log"
    os.utime(old, (1_000_000.0, 1_000_000.0))
    scan = pregap_verbs.scan_run_logs(tmp_path, since=2_000_000.0)
    assert "round32fullsecurereread" not in {r.label for r in scan.readings}
    # With the secure re-read's album log out of scope, track 4 agrees.
    assert grading.compare(scan.readings).differing_tracks == (9,)


def test_the_cap_is_counted_in_the_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _rips_folder(tmp_path)
    monkeypatch.setattr(pregap_verbs, "MAX_LOGS", 3)
    scan = pregap_verbs.scan_run_logs(tmp_path, since=0.0)
    assert len(scan.readings) == 3
    assert scan.dropped_by_cap == len(_round32_logs()) - 3
    _outcome, detail, _state = pregap_verbs.answer(scan)
    assert "were NOT compared" in detail


def test_an_empty_rips_folder_is_blocked(tmp_path: Path) -> None:
    outcome, detail, state = pregap_verbs.answer(
        pregap_verbs.scan_run_logs(tmp_path, since=0.0)
    )
    assert (outcome, state) == (Outcome.BLOCKED, grading.NOT_DETERMINED)
    assert "not a pass" in detail


@pytest.mark.parametrize("value", ["", "yesterday", "2026-10-13T11:29:19"])
def test_a_start_time_that_cannot_scope_the_scan_is_none(value: str) -> None:
    assert pregap_verbs.run_start_epoch(value) is None


def test_the_runs_own_start_time_is_read() -> None:
    assert pregap_verbs.run_start_epoch("1970-01-01T00:00:10+00:00") == 10.0


# --- The verb, through the runner ---------------------------------------------


def _run_verb(tmp_path: Path, qapp: Any, process_until: Any, output_dir: str) -> Any:
    from test_uiscript_rip_verbs import _step_outcome, _window

    from platterpus.uiscript.runner import ScriptRunner

    win = _window(config=Config(output_dir=output_dir))
    return _step_outcome(ScriptRunner(win), qapp, process_until, "expect-pregaps-agree")


def _dated_after_the_run_starts(root: Path) -> None:
    """Date every file a minute ahead, as a real run's rips are dated after it starts.

    **The difference this pins** (`CLAUDE.md`, *what does my stand-in do that the
    real thing does not?*): a real run writes its rips after its first step, and
    the verb counts only files modified since then. A test that copies the logs
    and then starts the run writes them first, and the run's start time is cut to
    the second, so whenever a second boundary fell between the copy and the
    start the verb correctly found nothing (measured: 2 runs in 12 failed that
    way before this helper). The scope itself is pinned by
    `test_the_scan_leaves_out_logs_from_before_the_run`.
    """
    ahead = time.time() + 60.0
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (ahead, ahead))


def test_the_verb_names_the_differing_tracks_as_info(
    tmp_path: Path, qapp: Any, process_until: Any, caplog: pytest.LogCaptureFixture
) -> None:
    _rips_folder(tmp_path)
    _dated_after_the_run_starts(tmp_path)
    step = _run_verb(tmp_path, qapp, process_until, str(tmp_path))
    assert step.outcome is Outcome.INFO, step.detail
    assert "track(s) 4, 9" in step.detail
    assert any("pregap lists DIFFER" in r.getMessage() for r in caplog.records), (
        "the disagreement goes to the app log too, so the bundle carries it"
    )


def test_the_verb_is_blocked_on_an_empty_rips_folder(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    step = _run_verb(tmp_path, qapp, process_until, str(tmp_path))
    assert step.outcome is Outcome.BLOCKED, step.detail


def test_the_verb_refuses_a_relative_rips_folder(
    tmp_path: Path, qapp: Any, process_until: Any
) -> None:
    step = _run_verb(tmp_path, qapp, process_until, "rips")
    assert step.outcome is Outcome.ERROR
    assert "not an absolute path" in step.detail


def test_the_acceptance_script_runs_it_in_its_own_section() -> None:
    """P4 exists, after every rip, before Q, at a size where two rips exist."""
    text = _ACCEPTANCE.read_text(encoding="utf-8")
    header = "log --- P4. "
    assert text.count(header) == 1
    body = text.split(header, 1)[1].split("\nlog --- ", 1)[0]
    lines = [ln.strip() for ln in body.splitlines()[1:] if ln.strip()]
    assert lines[:2] == ["run-size standard", "expect-pregaps-agree"], lines
    assert text.index(header) > text.rindex("log --- P3. ")
    assert text.index(header) < text.index("log --- Q. ")
