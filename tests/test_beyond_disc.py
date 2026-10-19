"""TASKS R26: the fork's per-track `Beyond disc:` line, read into the report.

`.24` (`cyanrip@93afa15`) reads a frame outside the disc once under `-O` and writes
a frame the drive refuses as silence, saying so per track after `Appended:`:
`Beyond disc: N of M frames refused (written as silence)`
(`cyanrip@93afa15:src/cyanrip_log.c:481`; round 35 lap 1 S11; the P2 row in
`docs/handshake/inbound/artifacts/round-35-lap-01-provider-contract-g16b9469.md`).

No committed log carries the line: our Full run keeps `-O` off, and the fork's
golden reference is ripped without it. So every case here is the real `.24` golden
reference with the line inserted where S11 says it goes (the Properties block,
after the LSNs and `Appended:`), and the contract case builds the line from the
contract's own format string rather than from our pattern.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report

_FIXTURES = Path(__file__).parent / "fixtures"
_R35_LOG = _FIXTURES / "cyanrip_fork_golden_reference_r35.log"
_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs/handshake/inbound/artifacts/round-35-lap-01-provider-contract-g16b9469.md"
)
# Track 1's last Properties row in the golden reference; the line goes after it.
_ANCHOR = "    End LSN:     374\n"


def _with_line(line: str) -> str:
    """The `.24` golden reference with `line` added to track 1's Properties block."""
    text = _R35_LOG.read_text(encoding="utf-8")
    assert text.count(_ANCHOR) == 1  # floor: the insertion lands, and once
    return text.replace(_ANCHOR, _ANCHOR + line, 1)


def _pair(text: str, index: int = 0) -> tuple[int | None, int | None]:
    track = parse_cyanrip_log(text).tracks[index]
    return (track.beyond_disc_frames_refused, track.beyond_disc_frames)


# --- the line -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        # The image case S12 gives at +667: both frames past the lead-out refused.
        ("    Beyond disc: 2 of 2 frames refused (written as silence)\n", (2, 2)),
        # The drive read every frame outside the disc: a measured 0, not "absent".
        ("    Beyond disc: 0 of 2 frames refused (written as silence)\n", (0, 2)),
        # Some refused, some read.
        ("    Beyond disc: 1 of 2 frames refused (written as silence)\n", (1, 2)),
        # A wide overread offset reaches many frames.
        ("    Beyond disc: 12 of 40 frames refused (written as silence)\n", (12, 40)),
        # A singular the format string does not print today, read anyway.
        ("    Beyond disc: 1 of 1 frame refused (written as silence)\n", (1, 1)),
        # A reworded parenthetical still yields the counts it restates.
        ("    Beyond disc: 2 of 2 frames refused (zero-filled)\n", (2, 2)),
    ],
)
def test_each_shape_is_read_as_a_pair(line: str, expected: tuple[int, int]) -> None:
    assert _pair(_with_line(line)) == expected


def test_the_contracts_own_row_filled_in_is_read() -> None:
    """Built from the `.24` contract's P2 format string, indented as the
    Properties block is, so the test does not merely agree with our pattern."""
    rows = re.findall(
        r"^\| `[^`]+` \| `(Beyond disc:[^`]*)` \|$",
        _CONTRACT.read_text(encoding="utf-8"),
        re.M,
    )
    assert rows == ["Beyond disc: %i of %i frames refused (written as silence)"]
    assert _pair(_with_line("    " + rows[0] % (2, 2) + "\n")) == (2, 2)


def test_the_line_belongs_to_the_track_it_is_printed_in() -> None:
    tracks = parse_cyanrip_log(
        _with_line("    Beyond disc: 2 of 2 frames refused (written as silence)\n")
    ).tracks
    assert len(tracks) == 3  # floor: the other tracks were parsed, so None is a read
    assert [(t.beyond_disc_frames_refused, t.beyond_disc_frames) for t in tracks] == [
        (2, 2),
        (None, None),
        (None, None),
    ]


def test_a_log_without_the_line_states_nothing_not_zero() -> None:
    """`-O` off, or a build before `.24`: not stated, which is not "0 refused"."""
    tracks = parse_cyanrip_log(_R35_LOG.read_text(encoding="utf-8")).tracks
    assert len(tracks) == 3  # floor
    for track in tracks:
        assert (track.beyond_disc_frames_refused, track.beyond_disc_frames) == (
            None,
            None,
        )


def test_more_refused_than_read_is_left_unstated_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    line = "    Beyond disc: 3 of 2 frames refused (written as silence)\n"
    with caplog.at_level("WARNING", logger="platterpus.parsers.cyanrip_log"):
        assert _pair(_with_line(line)) == (None, None)
    assert any("Beyond disc" in r.getMessage() for r in caplog.records)


@given(st.text(max_size=200))
def test_the_line_parser_never_raises(tail: str) -> None:
    parse_cyanrip_log(_with_line(f"    Beyond disc: {tail}\n"))


@given(st.integers(0, 10**9 - 1), st.integers(0, 10**9 - 1))
def test_any_pair_the_ripper_can_print_is_read_or_refused_never_misread(
    refused: int, tried: int
) -> None:
    line = (
        f"    Beyond disc: {refused} of {tried} frames refused (written as silence)\n"
    )
    expected = (refused, tried) if refused <= tried else (None, None)
    assert _pair(_with_line(line)) == expected


# --- the report -----------------------------------------------------------------


def _report(line: str) -> dict:
    return build_report(parse_cyanrip_log(_with_line(line)))


def test_the_report_carries_the_pair_per_track_and_raises_an_info_issue() -> None:
    report = _report("    Beyond disc: 2 of 2 frames refused (written as silence)\n")
    rows = report["tracks"]

    assert len(rows) == 3  # floor
    assert (rows[0]["beyond_disc_frames_refused"], rows[0]["beyond_disc_frames"]) == (
        2,
        2,
    )
    assert (rows[1]["beyond_disc_frames_refused"], rows[1]["beyond_disc_frames"]) == (
        None,
        None,
    )
    found = [i for i in report["issues"] if i["code"] == "beyond_disc_frames_refused"]
    assert len(found) == 1
    assert found[0]["severity"] == "info"
    assert "track 1" in found[0]["message"]
    assert "2 of the 2 frames" in found[0]["message"]


def test_a_measured_zero_is_kept_in_the_report_and_raises_nothing() -> None:
    report = _report("    Beyond disc: 0 of 2 frames refused (written as silence)\n")
    row = report["tracks"][0]

    # 0, not None: the `or None` idiom the string keys use would erase it.
    assert (row["beyond_disc_frames_refused"], row["beyond_disc_frames"]) == (0, 2)
    assert "beyond_disc_frames_refused" not in {i["code"] for i in report["issues"]}


def test_a_log_without_the_line_reports_null_and_raises_nothing() -> None:
    report = build_report(parse_cyanrip_log(_R35_LOG.read_text(encoding="utf-8")))

    assert len(report["tracks"]) == 3  # floor
    for row in report["tracks"]:
        assert row["beyond_disc_frames_refused"] is None
        assert row["beyond_disc_frames"] is None
    assert "beyond_disc_frames_refused" not in {i["code"] for i in report["issues"]}
