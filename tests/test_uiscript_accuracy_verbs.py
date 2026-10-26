"""The paired rips of track 3 (section P6; the owner's word of 2026-10-26).

Two verbs, `record-accuracy` and `compare-accuracy`, and the section of
`fullacceptance.txt` written in them with P5's `install-ripper` and
`skip-if-same-build`.

* **The reader** takes each track's AccurateRip state from the verdict
  (`verdict.track_accuraterip_state`), never a rule of its own, so the tests feed
  it cyanrip log text through the real parser. The track blocks below copy the
  wording of the 2026-10-21 Full run's P5 logs: track 3 verified on `.25`
  (`3C8BDDD2 … confidence 128`) and matched on frame 450 only on `.26`.
* **The comparison** is a measurement: per build and per track, right in N of M
  rips with the distinct CRC32s, or a refusal naming why ("not determined").
* **The verbs** are driven through a real `ScriptRunner`.

**What the stand-ins do that the real things do not** (`CLAUDE.md`): the logs
carry only the lines the reader and the parser's track block need, not a whole
rip's header; the window is the shared fake from `test_uiscript_rip_verbs`, whose
"log on disk" is a parsed `RipLog` handed back rather than a file read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from test_uiscript_rip_verbs import _window

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.uiscript.accuracy_grading import (
    STATE_WORDS,
    AccuracyRecord,
    TrackAccuracy,
    accuracy_from_log,
    compare_accuracy,
    label_problem,
)
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse
from platterpus.verdict import AR_STATES, track_accuraterip_state

pytest.importorskip("PySide6.QtWidgets")
pytestmark = pytest.mark.usefixtures("qapp")

RIG_SCRIPTS = Path(__file__).resolve().parents[1] / "src" / "platterpus" / "rig_scripts"

OLD = "platterpus-fork-g5f1d036"
NEW = "platterpus-fork-gca0f097"
FOUND = "disc found in database (max confidence: 200)"
VERIFIED = (
    "3C8BDDD2 (accurately ripped, confidence 128)",
    "96DF8C22 (accurately ripped, confidence 200)",
    "00000000",
)
FRAME_450 = (
    "72B5CF75 (not found, either a new pressing, or bad rip)",
    "CD09EBA8 (not found, either a new pressing, or bad rip)",
    "BF62B1DA (matches Accurip DB, confidence 200, one frame only; whole-track "
    "checksums not found)",
)
MISMATCH = (
    "72B5CF75 (not found, either a new pressing, or bad rip)",
    "CD09EBA8 (not found, either a new pressing, or bad rip)",
    "BF62B1DA (not found, either a new pressing, or bad rip)",
)


def _log_text(
    build: str,
    results: tuple[str, str, str],
    *,
    lookup: str = FOUND,
    crc: str = "59D352DD",
    number: int = 3,
) -> str:
    """One track's block, worded as the 2026-10-21 P5 logs word it."""
    v1, v2, a450 = results
    return (
        f"cyanrip 0.9.4-rc3+platterpus.25 ({build})\n"
        f"Tracks to rip:  {number}\n"
        "AccurateRip:    found\n\n"
        "Tracks:\n"
        f"Track {number} read successfully!\n"
        "Summary:\n\n"
        "  Properties:\n"
        "    Extraction speed:  0.96x\n"
        "    Elapsed:            302.72 s\n\n"
        f"  EAC CRC32:     {crc}\n"
        f"  Accurip:       {lookup}\n"
        f"    Accurip v1:  {v1}\n"
        f"    Accurip v2:  {v2}\n"
        f"    Accurip 450: {a450}\n"
    )


def _parsed(build: str, results: tuple[str, str, str], **kw: Any) -> RipLog:
    return parse_cyanrip_log(_log_text(build, results, **kw))


def _rec(label: str, build: str, *tracks: tuple[int, str, str]) -> AccuracyRecord:
    """A record of ``(number, state, crc32)`` tracks."""
    return AccuracyRecord(
        label=label,
        build=build,
        tracks=tuple(TrackAccuracy(number=n, state=s, crc32=c) for n, s, c in tracks),
    )


# --- the reader, through the real parser -------------------------------------


def test_a_verified_track_reads_its_confidence_crc_speed_and_build() -> None:
    record = accuracy_from_log("A1", _parsed(OLD, VERIFIED))
    assert record.build == OLD
    (track,) = record.tracks
    assert (track.number, track.state, track.crc32) == (3, "verified", "59D352DD")
    assert track.confidence == "200 of 200", "the higher of v1 and v2 is reported"
    assert track.speed == pytest.approx(0.96)
    assert "track 3: verified (200 of 200), CRC32 59D352DD, 0.96x" in (
        record.describe()
    )


def test_a_frame_450_match_is_not_verified() -> None:
    (track,) = accuracy_from_log("B1", _parsed(NEW, FRAME_450)).tracks
    assert track.state == "offset-variant"
    assert "frame 450 only (200 of 200)" in track.describe()


def test_a_track_that_matched_nothing_is_a_mismatch() -> None:
    (track,) = accuracy_from_log("B1", _parsed(NEW, MISMATCH)).tracks
    assert track.state == "no-match" and track.confidence == ""


def test_a_disabled_lookup_is_no_lookup() -> None:
    """cyanrip prints bare checksums when the lookup is off (the fork's golden
    reference log: `Accurip:       disabled`, `Accurip v1:  BAE96A9D`)."""
    bare = ("BAE96A9D", "C0772401", "00000000")
    (track,) = accuracy_from_log("A1", _parsed(OLD, bare, lookup="disabled")).tracks
    assert track.state == "not-checked"
    assert "no lookup" in track.describe()


def test_every_state_the_verdict_returns_has_its_own_words() -> None:
    assert set(STATE_WORDS) == set(AR_STATES)
    assert len(set(STATE_WORDS.values())) == len(AR_STATES)


@settings(max_examples=60, deadline=None)
@given(st.text(max_size=600))
def test_the_reader_never_raises_on_any_log_text(text: str) -> None:
    """External text reaches it through the parser; neither may raise."""
    record = accuracy_from_log("x", parse_cyanrip_log(text))
    record.describe()
    compare_accuracy(["x", "y"], {"x": record, "y": record})


_RESULTS = st.one_of(
    st.none(),
    st.builds(
        AccurateRipResult,
        version=st.sampled_from([1, 2]),
        confidence=st.one_of(st.none(), st.integers(0, 300)),
        local_crc=st.one_of(st.none(), st.sampled_from(["00000000", "3C8BDDD2", ""])),
    ),
)


@settings(max_examples=200, deadline=None)
@given(
    v1=_RESULTS,
    v2=_RESULTS,
    offset=_RESULTS,
    lookup=st.one_of(
        st.none(), st.sampled_from([FOUND, "disabled", "error", "not found", ""])
    ),
)
def test_the_track_state_agrees_with_the_artifact_graders(
    v1: AccurateRipResult | None,
    v2: AccurateRipResult | None,
    offset: AccurateRipResult | None,
    lookup: str | None,
) -> None:
    """Two surfaces summarise a track's two columns: they must say the same.

    `artifact_grading._track_ar_state` (what `expect-accuraterip` grades) and
    `verdict.track_accuraterip_state` (what P6 counts) rank the same states; the
    relation is the property neither side's own test can state (§5.al).
    """
    from platterpus.uiscript.artifact_grading import _track_ar_state

    track = TrackResult(
        number=3,
        accuraterip_v1=v1,
        accuraterip_v2=v2,
        accuraterip_offset=offset,
        accuraterip_lookup=lookup,
    )
    assert track_accuraterip_state(track) == _track_ar_state(track)


@pytest.mark.parametrize(
    ("label", "ok"),
    [("A1", True), ("b.2-x_y", True), ("", False), ("a b", False), ("x" * 33, False)],
)
def test_labels_are_validated_at_the_boundary(label: str, ok: bool) -> None:
    problem = label_problem(label)
    assert (problem == "") is ok
    assert ok or "an accuracy record" in problem


# --- the comparison -----------------------------------------------------------


def _abba() -> dict[str, AccuracyRecord]:
    """The 2026-10-21 shape: `.25` right every time, `.26` on frame 450 only."""
    out: dict[str, AccuracyRecord] = {}
    for label in ("A1", "A2", "A3", "A4"):
        out[label] = _rec(label, OLD, (3, "verified", "59D352DD"))
    for label, crc in (
        ("B1", "D7314554"),
        ("B2", "D7314554"),
        ("B3", "0A0B0C0D"),
        ("B4", "59D352DD"),
    ):
        state = "verified" if crc == "59D352DD" else "offset-variant"
        out[label] = _rec(label, NEW, (3, state, crc))
    return out


def test_the_tally_counts_right_in_n_of_m_per_build_with_the_crcs() -> None:
    labels = ["A1", "B1", "B2", "A2", "A3", "B3", "B4", "A4"]
    result = compare_accuracy(labels, _abba())
    assert result.determined, result.refusal
    lines = result.detail.splitlines()
    assert lines[0] == (
        f"track 3, {OLD}: right in 4 of 4 rip(s) (A1, A2, A3, A4); verified 4"
    )
    assert lines[1] == "  1 distinct CRC32: 59D352DD x4 (verified 4)"
    assert lines[2] == (
        f"track 3, {NEW}: right in 1 of 4 rip(s) (B1, B2, B3, B4); "
        "frame 450 only 3, verified 1"
    )
    assert lines[3] == (
        "  3 distinct CRC32: 0A0B0C0D x1 (frame 450 only 1); 59D352DD x1 "
        "(verified 1); D7314554 x2 (frame 450 only 2)"
    )
    assert lines[4] == "track 3: CRC32 read under more than one build: 59D352DD"


def test_a_log_naming_no_build_is_not_determined() -> None:
    records = {**_abba(), "A1": _rec("A1", "", (3, "verified", "X"))}
    result = compare_accuracy(["A1", "B1"], records)
    assert not result.determined and "names no build" in result.refusal


def test_different_track_sets_are_not_determined() -> None:
    records = {**_abba(), "B1": _rec("B1", NEW, (2, "verified", "X"))}
    result = compare_accuracy(["A1", "B1"], records)
    assert not result.determined and "track sets differ" in result.refusal


def test_one_build_only_is_not_determined() -> None:
    result = compare_accuracy(["A1", "A2"], _abba())
    assert not result.determined and "needs two" in result.refusal


def test_a_rip_accuraterip_said_nothing_about_is_not_determined_but_tallied() -> None:
    records = {**_abba(), "B2": _rec("B2", NEW, (3, "not-checked", "D7314554"))}
    result = compare_accuracy(["A1", "B1", "B2", "A2"], records)
    assert not result.determined
    assert "B2 track 3 (no lookup)" in result.refusal
    assert "right in 0 of 2 rip(s) (B1, B2)" in result.detail, (
        "the tallies must survive a refusal; the transcript keeps the data"
    )


@pytest.mark.parametrize(
    ("labels", "why"),
    [
        (["A1"], "two labels or more"),
        (["A1", "A1"], "named more than once"),
        (["A1", "Z9"], "no accuracy has been recorded as Z9"),
    ],
)
def test_bad_label_lists_are_not_determined(labels: list[str], why: str) -> None:
    result = compare_accuracy(labels, _abba())
    assert not result.determined and why in result.refusal


# --- the verbs, through a real runner ----------------------------------------


def test_record_then_compare_through_the_runner(tmp_path: Path) -> None:
    runner = ScriptRunner(_window(last_rip_log=None))
    for label, build, results in (
        ("A1", OLD, VERIFIED),
        ("B1", NEW, FRAME_450),
    ):
        runner._window = _window(
            last_rip_log=_parsed(build, results), last_rip_log_file=tmp_path / "x.log"
        )
        runner._execute(parse(f"record-accuracy {label}")[0])
        step = runner._report.steps[-1]
        assert step.outcome is Outcome.INFO, step.detail
        assert f"accuracy {label}: build {build}" in step.detail
    runner._execute(parse("compare-accuracy A1 B1")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.INFO, step.detail
    assert f"track 3, {OLD}: right in 1 of 1 rip(s) (A1)" in step.detail
    assert f"track 3, {NEW}: right in 0 of 1 rip(s) (B1)" in step.detail


def test_record_accuracy_of_a_log_naming_no_build_is_an_error(tmp_path: Path) -> None:
    text = _log_text(OLD, VERIFIED).replace(f" ({OLD})", "", 1)
    runner = ScriptRunner(
        _window(
            last_rip_log=parse_cyanrip_log(text), last_rip_log_file=tmp_path / "x.log"
        )
    )
    runner._execute(parse("record-accuracy A1")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.ERROR and "not determined" in step.detail


def test_record_accuracy_with_no_rip_records_the_readers_failure() -> None:
    runner = ScriptRunner(_window(last_rip_log=None))
    runner._execute(parse("record-accuracy A1")[0])
    assert runner._report.steps[-1].outcome is Outcome.FAIL
    assert "A1" not in runner._accuracies


def test_a_bad_label_is_refused_before_anything_is_read() -> None:
    runner = ScriptRunner(_window(last_rip_log=None))
    runner._execute(parse("record-accuracy a/b")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.ERROR and "an accuracy record" in step.detail


def test_compare_accuracy_refuses_as_an_error_when_a_record_is_missing() -> None:
    runner = ScriptRunner(_window())
    runner._execute(parse("compare-accuracy A1 B1")[0])
    step = runner._report.steps[-1]
    assert step.outcome is Outcome.ERROR and "not determined" in step.detail


def test_a_new_run_forgets_the_last_runs_records() -> None:
    runner = ScriptRunner(_window())
    runner._accuracies = {"A1": _rec("A1", OLD, (3, "verified", "X"))}
    runner.start(parse("log hi"), source="log hi")
    runner.stop()
    assert runner._accuracies == {}


# --- the committed section ------------------------------------------------------


def _p6_lines() -> list[str]:
    text = (RIG_SCRIPTS / "fullacceptance.txt").read_text(encoding="utf-8")
    body = text.split("log --- P6.", 1)[1].split("log --- ", 1)[0]
    return [
        ln.strip()
        for ln in body.splitlines()[1:]
        if ln.strip() and not ln.strip().startswith("#")
    ]


def test_the_committed_section_rips_track_3_in_abba_order() -> None:
    lines = _p6_lines()
    assert lines[0] == "run-size full", "paired rips are a Full-run section"
    assert lines[1] == "skip-if-same-build (fork-pin) (under-review)"
    assert "select-tracks 3" in lines
    # The build each rip reads on is the last `install-ripper` before its `rip`.
    side = {"(fork-pin)": "A", "(under-review)": "B"}
    current = ""
    order: list[str] = []
    labels: list[str] = []
    for line in lines:
        if line.startswith("install-ripper "):
            current = side.get(line.split()[1], "")
        elif line == "rip":
            order.append(current)
        elif line.startswith("record-accuracy "):
            labels.append(line.split()[1])
    assert "".join(order) == "ABBAABBA", (
        "ABBA over four pairs, so drift favours neither"
    )
    assert [label[0] for label in labels] == list("ABBAABBA"), (
        "each record's label must name the build it was ripped on"
    )
    assert len(set(labels)) == 8
    assert f"compare-accuracy {' '.join(labels)}" in lines
    assert lines[-9] == "install-ripper (pin)", "it ends on the build section A accepts"
    for setting in (
        "secure_rerip_dynamic off",
        "secure_rerip_matches 0",
        "second_read_without_accuraterip off",
        "read_speed_mode fixed",
    ):
        assert f"set {setting}" in lines
    for restored in (
        "secure_rerip_dynamic on",
        "secure_rerip_matches 2",
        "second_read_without_accuraterip on",
        "read_speed_mode auto_ladder",
    ):
        assert f"set {restored}" in lines and f"expect {restored}" in lines
    # Every rip waits, and its checks finish before the next install.
    for index, line in enumerate(lines):
        if line == "rip":
            assert lines[index + 1 : index + 5] == [
                "wait-for-rip 1800",
                "expect-rip-complete",
                "expect-verification",
                lines[index + 4],
            ]
            assert lines[index + 4].startswith("record-accuracy ")


def test_every_step_of_the_section_is_a_known_built_verb() -> None:
    from platterpus.uiscript.verbs import VERBS

    steps = parse("\n".join(_p6_lines()))
    assert len(steps) >= 60
    for step in steps:
        assert step.ok, (step.source, step.error)
        assert VERBS[step.verb].implemented
        assert hasattr(ScriptRunner, f"_do_{step.verb.replace('-', '_')}"), step.verb
