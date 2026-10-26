"""`.27`'s `not written whole:` footer lines: parsed, reported, and shown.

The fork's round 36 lap 7 S6 says the lines are built (`d33902d`): when
`Encoder errors:` names a failed track, each file a failed encoder left prints on
a line of its own directly below it, `    not written whole: <path>`, by the path
the track's `File(s):` names (`cyanrip@709337a:src/cyanrip_log.c:327-345`).

**Where the lines come from.** No committed log carries them: the fork's capped
rip (their S8) is not committed. So the log here is the `.27` golden reference
(`cyanrip@ed540ff:docs/golden-reference.log`, our fixture) with its `Encoder
errors:` line replaced by the failure arm and the lines below it, each built from
the fork's own P2 format strings
(`cyanrip@302dba8:PROVIDER-CONTRACT.md:286` and the `Encoder errors:` row above
it), filled with the paths the reference's own `File(s):` lines name.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus import written_whole
from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report
from platterpus.ui.main_window_helpers import fidelity_summary

_R36L7_LOG = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36l7.log"
)

#: The fork's P2 rows, copied, so the filled lines check our reader against their
#: text (`cyanrip_log.c:322` and `:342`; indentation is the source's).
_P2_FAILED = "Encoder errors: %i track%s failed (%s%s); %i track%s encoded"
_P2_NOT_WHOLE = "    not written whole: %s"

_CLEAN_FOOTER = "Encoder errors: none; 3 tracks encoded\n"


def _golden() -> str:
    return _R36L7_LOG.read_text(encoding="utf-8")


def _failed(*paths: str, failed: str = "2, 3", count: int = 2) -> str:
    """The reference with tracks' encoders failed and ``paths`` named below."""
    text = _golden()
    assert text.count(_CLEAN_FOOTER) == 1  # floor: the anchor lands, once
    footer = _P2_FAILED % (count, "s" if count != 1 else "", failed, "", 1, "")
    lines = "".join((_P2_NOT_WHOLE % path) + "\n" for path in paths)
    return text.replace(_CLEAN_FOOTER, footer + "\n" + lines, 1)


def _issues(report: dict[str, object], code: str) -> list[str]:
    issues = report["issues"]
    assert isinstance(issues, list)
    return [str(i["message"]) for i in issues if i.get("code") == code]


# --- parse --------------------------------------------------------------------------


def test_the_reference_names_its_tracks_files_as_the_lines_will() -> None:
    """The paths below are the ones the reference's own `File(s):` lines name."""
    log = parse_cyanrip_log(_golden())
    assert [t.filename for t in log.tracks] == ["o/1.flac", "o/2.flac", "o/3.flac"]
    assert (log.not_written_whole, log.not_written_whole_total) == ((), 0)


def test_the_lines_below_a_failure_arm_are_read_in_order() -> None:
    log = parse_cyanrip_log(_failed("o/2.flac", "o/3.flac"))

    assert len(log.tracks) == 3  # floor: the whole log was read
    assert log.encoder_failed_tracks == 2
    assert log.not_written_whole == ("o/2.flac", "o/3.flac")
    assert log.not_written_whole_total == 2


def test_the_rule_claims_the_line_and_is_listed() -> None:
    rule = next(r for r in cyanrip_log._ALL_LINE_RULES if r.name == "not_written_whole")
    assert rule.pattern.match(_P2_NOT_WHOLE % "o/2.flac")


def test_a_line_that_is_not_below_encoder_errors_is_not_taken() -> None:
    """Position is the discriminator: in a track block it describes nothing."""
    text = _golden().replace(
        "  File(s):\n    o/1.flac\n",
        "  File(s):\n    o/1.flac\n    not written whole: o/1.flac\n",
        1,
    )
    assert "not written whole: o/1.flac" in text  # floor: the line landed
    log = parse_cyanrip_log(text)
    assert log.not_written_whole == ()


def test_the_list_is_bounded_head_and_tail_and_the_rest_counted() -> None:
    paths = [f"o/{n}.flac" for n in range(1, 251)]
    log = parse_cyanrip_log(_failed(*paths))

    kept = log.not_written_whole
    assert log.not_written_whole_total == 250
    assert len(kept) == written_whole.KEEP_HEAD + written_whole.KEEP_TAIL
    assert kept[0] == "o/1.flac" and kept[-1] == "o/250.flac"
    assert written_whole.not_kept(log) == 50


def test_an_absurd_path_is_bounded_with_its_cut_counted() -> None:
    log = parse_cyanrip_log(_failed("o/" + "x" * 9000 + ".flac"))
    [path] = log.not_written_whole
    assert len(path) < 4200
    assert "characters cut" in path and path.endswith("x.flac")


# --- report and status line ---------------------------------------------------------


def test_the_report_names_each_file_and_raises_a_warning_per_file() -> None:
    log = parse_cyanrip_log(_failed("o/2.flac", "o/3.flac"))
    report = build_report(log)

    assert report["rip"]["not_written_whole"] == ["o/2.flac", "o/3.flac"]
    assert report["rip"]["not_written_whole_not_kept"] == 0
    warnings = [
        i
        for i in report["issues"]
        if i["code"] == written_whole.ISSUE_NOT_WRITTEN_WHOLE
    ]
    assert [i["severity"] for i in warnings] == ["warning", "warning"]
    assert warnings[0]["message"].startswith("track 2: ")
    assert "o/2.flac" in warnings[0]["message"]
    assert "o/3.flac" in warnings[1]["message"]


def test_a_log_without_the_lines_says_nothing_rather_than_all_whole() -> None:
    report = build_report(parse_cyanrip_log(_golden()))
    assert report["rip"]["not_written_whole"] is None
    assert _issues(report, written_whole.ISSUE_NOT_WRITTEN_WHOLE) == []


def test_files_past_the_bound_are_said_in_one_more_warning() -> None:
    report = build_report(
        parse_cyanrip_log(_failed(*[f"o/{n}.flac" for n in range(1, 251)]))
    )
    messages = _issues(report, written_whole.ISSUE_NOT_WRITTEN_WHOLE)
    assert len(messages) == 201
    assert "50 more files" in messages[-1]
    assert report["rip"]["not_written_whole_not_kept"] == 50


def test_a_control_character_in_a_path_is_shown_not_obeyed() -> None:
    report = build_report(parse_cyanrip_log(_failed("o/2\x1b[31m.flac")))
    assert report["rip"]["not_written_whole"] == ["o/2\\x1b[31m.flac"]
    [message] = _issues(report, written_whole.ISSUE_NOT_WRITTEN_WHOLE)
    assert "\x1b" not in message and "\\x1b" in message


def test_the_status_line_names_the_damaged_files() -> None:
    log = parse_cyanrip_log(_failed("o/2.flac", "o/3.flac"))
    status = fidelity_summary(log, expected_track_total=3)
    assert "cyanrip says 2 files were not written whole: o/2.flac, o/3.flac." in status
    clean = fidelity_summary(parse_cyanrip_log(_golden()), expected_track_total=3)
    assert "not written whole" not in clean


@given(st.text(max_size=300))
def test_the_line_never_raises(path: str) -> None:
    flat = path.replace("\n", " ").replace("\r", " ")
    log = parse_cyanrip_log(_failed(flat))
    build_report(log)
    fidelity_summary(log, expected_track_total=3)
