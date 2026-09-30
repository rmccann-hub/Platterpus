"""The rig verbs: `expect-newest-pair`, `expect-found-offset`, `cache-probe`.

Round 30's D3 (a run tests only the newest pair) and the fork's round 30 lap 3
S24 (cyanrip's own offset finder against the drive's known offset, and
`cd-paranoia -A` beside cyanrip's cache probe), plus S24's third step, the tags
of one ripped FLAC as text in the run folder.

The graders are pure and tested directly; the verbs are driven through a real
`ScriptRunner` with the network reads and the cache probe replaced, because the
properties that matter there are the runner's: nothing blocks the GUI thread,
a wait that ends without its answer kills the child, and a gather-only step
records INFO whatever happens.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_uiscript_rip_verbs import _DrivePicker, _step_outcome, _window

from platterpus import __version__
from platterpus.adapters import cache_probe
from platterpus.deps import fork_source, ripper_manifest
from platterpus.deps.ripper_manifest import RipperManifest, RipperRelease
from platterpus.uiscript import probe_verbs
from platterpus.uiscript.probe_grading import (
    FoundOffset,
    grade_found_offset,
    grade_newest_pair,
    newest_fork_release,
    parse_found_offset,
)
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.update_check import ReleaseInfo

pytest.importorskip("PySide6.QtWidgets")

# Every verb test builds a QWidget stand-in, which aborts the process without a
# QApplication. Declared for the whole file, so a test run alone (as
# `scripts/revert_probe.py` runs them) is as safe as one run after the others.
pytestmark = pytest.mark.usefixtures("qapp")

_REVIEWED: str = fork_source.PIN_UNDER_REVIEW


def _row(channel: str, commit: str, seq: int) -> RipperRelease:
    return RipperRelease(
        channel=channel,
        version=f"0.9.3+platterpus.{seq}",
        commit=commit,
        release_seq=seq,
        handshake_round=30,
        round_closed=False,
        install_url="https://github.com/rmccann-hub/cyanrip",
    )


def _manifest(*rows: RipperRelease) -> RipperManifest:
    return RipperManifest(
        schema=2,
        project="cyanrip",
        default_channel="stable",
        channels={row.channel: row for row in rows},
    )


def _ours(version: str = __version__) -> ReleaseInfo:
    return ReleaseInfo(version=version, url="https://example.invalid/release")


# --- grade_newest_pair: D3 ----------------------------------------------------


def test_the_newest_pair_passes() -> None:
    grade = grade_newest_pair(
        _manifest(_row("stable", _REVIEWED, 29)),
        _ours(),
        under_review=_REVIEWED,
        app_version=__version__,
    )
    assert grade.passed, grade.detail
    assert "the newest pair" in grade.detail


def test_an_abbreviation_of_the_same_commit_is_the_same_build() -> None:
    """The manifest may carry a longer sha than our seven-character constant."""
    grade = grade_newest_pair(
        _manifest(_row("stable", _REVIEWED + "d9e0f1", 29)),
        _ours(),
        under_review=_REVIEWED,
        app_version=__version__,
    )
    assert grade.passed, grade.detail


def test_a_newer_fork_release_makes_the_pair_stale() -> None:
    grade = grade_newest_pair(
        _manifest(_row("stable", "abcdef1", 30)),
        _ours(),
        under_review=_REVIEWED,
        app_version=__version__,
    )
    assert not grade.passed
    assert "a stale pair" in grade.detail and "abcdef1" in grade.detail


def test_a_newer_build_on_beta_makes_the_pair_stale_even_when_stable_is_ours() -> None:
    """O3: a new build goes to beta until its run passes, so newest is across both."""
    manifest = _manifest(_row("stable", _REVIEWED, 29), _row("beta", "abcdef1", 30))
    assert newest_fork_release(manifest) == manifest.channels["beta"]
    grade = grade_newest_pair(
        manifest, _ours(), under_review=_REVIEWED, app_version=__version__
    )
    assert not grade.passed and "beta" in grade.detail


def test_the_build_under_review_on_beta_passes_while_stable_names_the_one_before() -> (
    None
):
    manifest = _manifest(_row("stable", "0000abc", 28), _row("beta", _REVIEWED, 29))
    grade = grade_newest_pair(
        manifest, _ours(), under_review=_REVIEWED, app_version=__version__
    )
    assert grade.passed, grade.detail


def test_a_newer_app_release_makes_the_pair_stale() -> None:
    grade = grade_newest_pair(
        _manifest(_row("stable", _REVIEWED, 29)),
        _ours("99.0.0"),
        under_review=_REVIEWED,
        app_version=__version__,
    )
    assert not grade.passed
    assert "our newest release is 99.0.0" in grade.detail


@pytest.mark.parametrize("which", ["manifest", "ours"])
def test_a_half_that_cannot_be_read_fails_and_says_not_determined(which: str) -> None:
    """Refusing on "not determined" costs a night only when the network is down."""
    grade = grade_newest_pair(
        None if which == "manifest" else _manifest(_row("stable", _REVIEWED, 29)),
        None if which == "ours" else _ours(),
        under_review=_REVIEWED,
        app_version=__version__,
    )
    assert not grade.passed
    assert "not determined" in grade.detail


def test_an_empty_commit_is_never_the_build_under_review() -> None:
    grade = grade_newest_pair(
        _manifest(_row("stable", _REVIEWED, 29)),
        _ours(),
        under_review="",
        app_version=__version__,
    )
    assert not grade.passed


# --- parse_found_offset / grade_found_offset: cyanrip -f ----------------------

#: The lines `search_for_drive_offset` prints, in the order it prints them
#: (`cyanrip@174a134:src/cyanrip_main.c:594-692`).
_CONFIRMED_RUN: str = (
    "Searching for drive offset, enabling AccuRip and disabling MusicBrainz and "
    "Cover art fetching...\n"
    "Loading data for track 1...\n"
    "Data loaded, searching for offsets...\n"
    "Offset of +667 found in track 1, trying to confirm with another track\n"
    "Loading data for track 2...\n"
    "Data loaded, searching for offsets...\n"
    "Offset of +667 confirmed (confidence: 2) in track 2\n"
    "Drive offset of +667 found (confidence: 2)!\n"
)


def test_a_finished_search_reads_its_summary_line() -> None:
    found = parse_found_offset(_CONFIRMED_RUN)
    assert found == FoundOffset(667, 2, True, "")
    grade = grade_found_offset(found, 667)
    assert grade.passed, grade.detail
    assert "+667" in grade.detail and "confidence 2" in grade.detail


def test_the_summary_wins_over_a_replaced_candidate() -> None:
    text = (
        "Offset of +6 found in track 1, trying to confirm with another track\n"
        "New offset of -30 found at track 2, scrapping old offset of +6, trying "
        "to confirm with another track\n"
        "Drive offset of -30 found (confidence: 1)!\n"
    )
    found = parse_found_offset(text)
    assert (found.offset, found.confidence, found.summarised) == (-30, 1, True)
    grade = grade_found_offset(found, 667)
    assert not grade.passed
    assert "-30" in grade.detail and "+667" in grade.detail
    assert "found once and never confirmed" in grade.detail


def test_a_retry_at_a_wider_radius_is_working_not_giving_up() -> None:
    """`Was not able to find drive offset …` is followed by a retry (line 685)."""
    text = (
        "Nothing found for track 1\n"
        "Was not able to find drive offset with a radius of 6 frames, trying "
        "again with a larger radius...\n"
        "Offset of +667 found in track 1\n"
        "Drive offset of +667 found (confidence: 1)!\n"
    )
    found = parse_found_offset(text)
    assert found == FoundOffset(667, 1, True, "")
    assert grade_found_offset(found, 667).passed


def test_a_search_with_no_summary_did_not_finish_whatever_its_candidate() -> None:
    """Grading the working as the answer is the wrong-thing pass this refuses."""
    text = "Offset of +667 found in track 1, trying to confirm with another track\n"
    found = parse_found_offset(text)
    assert found == FoundOffset(667, 0, False, "")
    grade = grade_found_offset(found, 667)
    assert not grade.passed
    assert "did not finish" in grade.detail and "+667" in grade.detail


def test_a_stopped_search_fails_even_with_a_matching_summary() -> None:
    """cyanrip prints a summary after a stop when it had a candidate (line 634)."""
    text = (
        "Offset of +667 found in track 1, trying to confirm with another track\n"
        "Stopping, offset finding incomplete!\n"
        "Drive offset of +667 found (confidence: 1)!\n"
    )
    found = parse_found_offset(text)
    assert found.summarised and found.gave_up == "Stopping, offset finding incomplete!"
    grade = grade_found_offset(found, 667)
    assert not grade.passed and "stopped" in grade.detail


@pytest.mark.parametrize(
    "ending",
    [
        "No track had AccuRip entry, cannot find offset!",
        "No track was long enough, unable to find drive offset!",
    ],
)
def test_a_search_that_gave_up_fails_with_cyanrips_own_sentence(ending: str) -> None:
    found = parse_found_offset(f"Loading data for track 1...\n{ending}\n")
    assert found == FoundOffset(None, 0, False, ending)
    grade = grade_found_offset(found, 667)
    assert not grade.passed and ending in grade.detail


def test_a_progress_line_ending_in_a_carriage_return_does_not_hide_the_summary() -> (
    None
):
    found = parse_found_offset(
        "reading 12/12\rDrive offset of +667 found (confidence: 3)!"
    )
    assert found == FoundOffset(667, 3, True, "")


def test_no_drive_offset_set_is_not_a_pass() -> None:
    grade = grade_found_offset(FoundOffset(667, 2, True, ""), None)
    assert not grade.passed and "set-drive-offset" in grade.detail


@settings(max_examples=300, deadline=None)
@given(st.text())
def test_parse_found_offset_never_raises(text: str) -> None:
    """A parser of external output returns an answer for ANY input."""
    found = parse_found_offset(text)
    assert isinstance(found, FoundOffset)
    grade_found_offset(found, 667)


@settings(max_examples=200, deadline=None)
@given(
    st.lists(
        st.sampled_from(
            [
                "Offset of +667 found in track 1",
                "Offset of -12 confirmed (confidence: 4) in track 3",
                "New offset of +6 found at track 2, scrapping old offset of +667",
                "Drive offset of +667 found (confidence: 2)!",
                "Stopping, offset finding incomplete!",
                "No track had AccuRip entry, cannot find offset!",
                "Drive offset of +99999999 found (confidence: 99999)!",
                "\x00\r ",
            ]
        ),
        max_size=12,
    )
)
def test_parse_found_offset_never_raises_on_its_own_lines_in_any_order(
    lines: list[str],
) -> None:
    assert isinstance(parse_found_offset("\n".join(lines)), FoundOffset)


def test_parse_found_offset_takes_anything_that_is_not_text() -> None:
    assert parse_found_offset(None) == FoundOffset(None, 0, False, "")  # type: ignore[arg-type]  # the never-raises contract covers a caller's wrong type


# --- The verbs, through a real runner -----------------------------------------


@pytest.fixture
def _run_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where `_ensure_artifact_dir` puts this test's run folder."""
    monkeypatch.setattr(
        "platterpus.paths.LOG_PATH", tmp_path / "share" / "log.txt", raising=False
    )
    return tmp_path / "share" / "uiscript"


def test_expect_newest_pair_reads_both_releases_off_the_gui_thread(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    gui = threading.get_ident()
    readers: list[int] = []
    channels: list[str] = []

    def manifest() -> RipperManifest:
        readers.append(threading.get_ident())
        return _manifest(_row("beta", _REVIEWED, 29))

    def ours(channel: str = "stable", **_: Any) -> ReleaseInfo:
        readers.append(threading.get_ident())
        channels.append(channel)
        return _ours()

    monkeypatch.setattr(ripper_manifest, "fetch_manifest", manifest)
    monkeypatch.setattr("platterpus.update_check.latest_release", ours)
    step = _step_outcome(
        ScriptRunner(_window()), qapp, process_until, "expect-newest-pair"
    )
    assert step.outcome is Outcome.PASS, step.detail
    assert readers and gui not in readers, "a release read ran on the GUI thread"
    # Every `v0.*` tag of ours is a pre-release: stable would show none of them.
    assert channels == ["beta"]


def test_expect_newest_pair_fails_on_a_stale_pair(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ripper_manifest,
        "fetch_manifest",
        lambda: _manifest(_row("stable", _REVIEWED, 29), _row("beta", "abcdef1", 30)),
    )
    monkeypatch.setattr("platterpus.update_check.latest_release", lambda **_: _ours())
    step = _step_outcome(
        ScriptRunner(_window()), qapp, process_until, "expect-newest-pair"
    )
    assert step.outcome is Outcome.FAIL
    assert "a stale pair" in step.detail


def test_expect_newest_pair_fails_when_a_read_raises(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken() -> RipperManifest:
        raise OSError("network is unreachable")

    monkeypatch.setattr(ripper_manifest, "fetch_manifest", broken)
    step = _step_outcome(
        ScriptRunner(_window()), qapp, process_until, "expect-newest-pair"
    )
    assert step.outcome is Outcome.FAIL
    assert "not determined" in step.detail and "unreachable" in step.detail


def test_expect_newest_pair_times_out_as_not_determined(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    def slow() -> RipperManifest:
        release.wait(10)
        return _manifest(_row("stable", _REVIEWED, 29))

    monkeypatch.setattr(probe_verbs, "PAIR_WAIT_S", 0.2)
    monkeypatch.setattr(ripper_manifest, "fetch_manifest", slow)
    try:
        step = _step_outcome(
            ScriptRunner(_window()), qapp, process_until, "expect-newest-pair"
        )
    finally:
        release.set()
    assert step.outcome is Outcome.FAIL
    assert "did not answer" in step.detail and "not determined" in step.detail


def _found_offset(output: str, *, argv: list[str], offset: int | None) -> Any:
    runner = ScriptRunner(_window())
    runner._last_cyanrip_argv = argv
    runner._last_cyanrip_output = output
    runner._drive_offset = offset
    runner._execute(parse("expect-found-offset")[0])
    return runner._report.steps[-1]


def test_expect_found_offset_grades_the_previous_find_offset_run() -> None:
    step = _found_offset(_CONFIRMED_RUN, argv=["cyanrip", "-N", "-f"], offset=667)
    assert step.outcome is Outcome.PASS, step.detail


def test_expect_found_offset_fails_on_a_different_offset() -> None:
    step = _found_offset(_CONFIRMED_RUN, argv=["cyanrip", "-N", "-f"], offset=6)
    assert step.outcome is Outcome.FAIL and "+6" in step.detail


def test_expect_found_offset_refuses_a_previous_step_that_was_not_minus_f() -> None:
    """An assertion satisfied by the wrong command is the defect this refuses."""
    step = _found_offset(_CONFIRMED_RUN, argv=["cyanrip", "-N", "-x", "-I"], offset=667)
    assert step.outcome is Outcome.ERROR and "cyanrip -f" in step.detail


class _Probe:
    """A `cd-paranoia -A` stand-in: answers at once, or blocks until killed."""

    def __init__(self, result: cache_probe.CacheProbeResult | None) -> None:
        self.result = result
        self.killed = threading.Event()
        self.devices: list[str] = []
        self.threads: list[int] = []

    def probe(self, device: str, **_: Any) -> cache_probe.CacheProbeResult:
        self.devices.append(device)
        self.threads.append(threading.get_ident())
        if self.result is not None:
            return self.result
        self.killed.wait(10)
        return cache_probe.CacheProbeResult(
            error="stopped by Platterpus before it finished"
        )

    def cancel(self) -> None:
        self.killed.set()


def _install(monkeypatch: pytest.MonkeyPatch, probe: _Probe) -> None:
    monkeypatch.setattr(cache_probe, "probe_cache_defeat", probe.probe)
    monkeypatch.setattr(cache_probe, "cancel_active_probe", probe.cancel)


def test_cache_probe_records_info_and_saves_the_output(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch, _run_folder: Path
) -> None:
    probe = _Probe(
        cache_probe.CacheProbeResult(
            defeat=True,
            cache_sectors=140,
            analyzed=True,
            raw_output="Cache size: 140 sectors\x1b[0m\nDrive tests OK\n",
            exit_code=0,
        )
    )
    _install(monkeypatch, probe)
    step = _step_outcome(
        ScriptRunner(_window(drive_picker=_DrivePicker("/dev/sr1"))),
        qapp,
        process_until,
        "cache-probe",
    )
    assert step.outcome is Outcome.INFO, step.detail
    assert "140 sectors, defeated, exit 0" in step.detail
    assert probe.devices == ["/dev/sr1"]
    assert threading.get_ident() not in probe.threads
    saved = list(_run_folder.rglob("cacheprobe*.txt"))
    assert len(saved) == 1, saved
    text = saved[0].read_text("utf-8")
    # Screened: the escape is shown, not silently dropped or passed through.
    assert "Cache size: 140 sectors\\x1b[0m" in text and "\x1b" not in text


def test_cache_probe_is_info_when_cd_paranoia_is_missing(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch, _run_folder: Path
) -> None:
    _install(
        monkeypatch,
        _Probe(cache_probe.CacheProbeResult(error="cd-paranoia not installed")),
    )
    step = _step_outcome(ScriptRunner(_window()), qapp, process_until, "cache-probe")
    assert step.outcome is Outcome.INFO
    assert "not determined" in step.detail and "isn't installed" in step.detail


def test_cache_probe_out_of_time_kills_the_child_and_stays_info(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch, _run_folder: Path
) -> None:
    probe = _Probe(None)
    _install(monkeypatch, probe)
    monkeypatch.setattr(probe_verbs, "CACHE_PROBE_WAIT_S", 0.2)
    step = _step_outcome(ScriptRunner(_window()), qapp, process_until, "cache-probe")
    assert step.outcome is Outcome.INFO, step.detail
    assert "was killed" in step.detail
    assert probe.killed.is_set(), "the wait ended and cd-paranoia was left running"


def test_stopping_the_run_mid_probe_kills_the_child(
    qapp: Any, process_until: Any, monkeypatch: pytest.MonkeyPatch, _run_folder: Path
) -> None:
    """CLAUDE.md rule 9: abandoning the helper is safe only once its child is dead."""
    probe = _Probe(None)
    _install(monkeypatch, probe)
    runner = ScriptRunner(_window())
    emitted: list[Any] = []
    runner.finished.connect(emitted.append)
    runner.start(parse("cache-probe\nlog after"), source="cache-probe\nlog after")
    assert process_until(lambda: runner._deadline_step is not None)
    runner.stop()
    assert probe.killed.is_set(), "a stopped run left cd-paranoia reading the drive"
    assert runner._deadline_cancel is None
    rows = {s.source: s.outcome for s in emitted[0].steps}
    assert rows["cache-probe"] is Outcome.BLOCKED


def test_cache_probe_refuses_while_a_rip_reads_the_disc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _Probe(cache_probe.CacheProbeResult())
    _install(monkeypatch, probe)
    runner = ScriptRunner(_window(rip_worker=object()))
    runner._execute(parse("cache-probe")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.FAIL and "two readers" in step.detail
    assert probe.devices == [], "the probe ran beside a rip"


def test_cache_probe_with_no_drive_selected_is_an_error() -> None:
    runner = ScriptRunner(_window(drive_picker=_DrivePicker("")))
    runner._execute(parse("cache-probe")[0])
    assert runner._report.steps[-1].outcome is Outcome.ERROR


def test_a_new_arming_forgets_the_previous_verbs_cancel() -> None:
    """One verb's kill must never be run against the next verb's wait."""
    runner = ScriptRunner(_window())
    runner._deadline_cancel = lambda: None
    runner._arm_deadline(parse("wait 1")[0], 1.0)
    assert runner._deadline_cancel is None


def test_a_cancel_that_raises_does_not_escape(caplog: pytest.LogCaptureFixture) -> None:
    runner = ScriptRunner(_window())

    def broken() -> None:
        raise RuntimeError("kill failed")

    runner._deadline_cancel = broken
    runner._cancel_deadline_work()
    assert runner._deadline_cancel is None
    assert "stopping a waiting step's work failed" in caplog.text
