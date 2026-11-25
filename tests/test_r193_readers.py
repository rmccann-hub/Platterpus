"""What `.36` will print, read before it prints it (TASKS R193).

Our round 42 lap 2 S19 promised the fork, answering its lap 1, readers for every
line `.36` changes: the complete ``Ripping errors:`` list (S12), ``frame reads with
errors`` beside ``frame reads failed`` (S14), ``Encoder errors:`` counting a failed
partial track (S15), the album rows' ``unknown (no audio track finished)`` (S23),
the progress line's ``rest of rip read once`` clause (S25), and ``Drive speed:``
(S29); each for the form the fork gives and the form it prints today, each with a
never-raises property test, shipped in our release after the one that names
`.35`. The fork prints none of them until that release is out.

The new lines are injected into a real `.35`-era log, so the rest of the log is
what a drive printed, and each is checked to be claimed by a rule: the sweep in
`tests/test_parsers_cyanrip_log.py` fails on any column-0 line no rule claims.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_parsers_cyanrip_log import _classify_top_level

from platterpus import ripping_error_parts
from platterpus.parsers import cyanrip_log

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference_r36l7.log"
)

#: The fork's own examples, verbatim from its round 42 lap 1.
_DRIVE_SPEED_RANGE = (
    "Drive speed:    5.7x to 14.0x declared by drive (GET PERFORMANCE), not measured"
)
_DRIVE_SPEED_NONE = "Drive speed:    not declared (GET PERFORMANCE not answered)"
_ALBUM_UNKNOWN = (
    "Album integrated loudness (R128): unknown (no audio track finished)",
    "Album loudness range (R128):      unknown (no audio track finished)",
    "Album sample peak level:          unknown (no audio track finished)",
    "Album true peak level:            unknown (no audio track finished)",
)


def _log_with(replace: dict[str, str], insert_after: dict[str, str]) -> str:
    """The fixture with whole lines replaced, and lines added after others."""
    out: list[str] = []
    for line in _FIXTURE.read_text(encoding="utf-8").splitlines():
        for prefix, new in replace.items():
            if line.startswith(prefix):
                line = new
        out.append(line)
        for prefix, new in insert_after.items():
            if line.startswith(prefix):
                out.append(new)
    return "\n".join(out) + "\n"


def test_the_fixture_is_the_shape_this_file_edits() -> None:
    """Floor: each line edited below is in the fixture, so no edit is a no-op."""
    text = _FIXTURE.read_text(encoding="utf-8")
    for prefix in ("Speed:", "Ripping errors:", "Encoder errors:", "Album integrated"):
        assert any(line.startswith(prefix) for line in text.splitlines()), prefix


# --- S12 and S14: every part of `Ripping errors:` ---------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "Ripping errors: 2614 (28 frame reads failed, 2586 paranoia skips)",
            {"frame_reads_failed": 28, "paranoia_skips": 2586, "encoders_failed": 0},
        ),
        ("Ripping errors: 1 (1 encoder failed)", {"encoders_failed": 1}),
        (
            "Ripping errors: 2614 (28 frame reads with errors, 2586 paranoia skips)",
            {"frame_reads_failed": 28, "paranoia_skips": 2586},
        ),
        (
            "Ripping errors: 15 (1 disc ID not computed, 2 arguments refused, "
            "3 allocations failed, 1 cover art load failed, 2 cover art writes failed, "
            "1 decoder setup failed, 4 encoder setups failed, 1 encoder failed)",
            {
                "disc_ids_not_computed": 1,
                "arguments_refused": 2,
                "allocations_failed": 3,
                "cover_art_loads_failed": 1,
                "cover_art_writes_failed": 2,
                "decoder_setups_failed": 1,
                "encoder_setups_failed": 4,
                "encoders_failed": 1,
                "paranoia_skips": 0,
            },
        ),
    ],
)
def test_every_named_part_is_read_and_none_is_unknown(
    line: str, expected: dict[str, int]
) -> None:
    match = cyanrip_log._RIP_ERRORS.match(line)
    assert match is not None
    parts = ripping_error_parts.from_match(match)
    assert parts.form == ripping_error_parts.FORM_NAMED
    assert parts.unknown == ()
    for name, value in expected.items():
        assert getattr(parts, name) == value, name


def test_a_part_we_still_do_not_know_keeps_every_absent_part_undetermined() -> None:
    match = cyanrip_log._RIP_ERRORS.match("Ripping errors: 3 (3 gremlins found)")
    assert match is not None
    parts = ripping_error_parts.from_match(match)
    assert parts.unknown_total == 1
    assert parts.encoders_failed is None and parts.paranoia_skips is None


# --- The lines in a whole log -------------------------------------------------------


def test_a_36_log_reads_and_every_new_line_is_claimed() -> None:
    text = _log_with(
        replace={
            "Ripping errors:": "Ripping errors: 1 (1 encoder failed)",
            "Encoder errors:": (
                "Encoder errors: 1 track failed (1), read not completed; "
                "no whole track was encoded"
            ),
            "Album integrated loudness": _ALBUM_UNKNOWN[0],
            "Album loudness range": _ALBUM_UNKNOWN[1],
            "Album sample peak level": _ALBUM_UNKNOWN[2],
            "Album true peak level": _ALBUM_UNKNOWN[3],
        },
        insert_after={"Speed:": _DRIVE_SPEED_RANGE},
    )
    log = cyanrip_log.parse_cyanrip_log(text)

    assert log.ripping_info.drive_speed_low_x == 5.7
    assert log.ripping_info.drive_speed_high_x == 14.0
    assert "declared by drive" in log.ripping_info.drive_speed_declared
    assert log.album_loudness_unknown == "no audio track finished"
    # The fixture still carries libavfilter's own block, which `.36` drops with
    # these rows (S23), so its fallback values may be present; what must never be
    # stored is the word where a number goes.
    for value in log.album_loudness.values():
        float(value)
    assert log.ripping_error_parts is not None
    assert log.ripping_error_parts.encoders_failed == 1
    for line in (_DRIVE_SPEED_RANGE, *_ALBUM_UNKNOWN):
        assert _classify_top_level(line) is not None, line


def test_today_s_lines_still_read_as_before() -> None:
    log = cyanrip_log.parse_cyanrip_log(_FIXTURE.read_text(encoding="utf-8"))
    assert log.album_loudness.get("integrated_lufs") == "-7.4"
    assert log.album_loudness_unknown == ""
    assert log.ripping_info.drive_speed_declared == ""
    assert log.ripping_info.drive_speed_low_x is None


def test_not_declared_reads_as_no_numbers_never_zero() -> None:
    disc = cyanrip_log._Disc()
    match = cyanrip_log._DRIVE_SPEED.match(_DRIVE_SPEED_NONE)
    assert match is not None
    cyanrip_log._take_drive_speed(disc, match)
    assert disc.drive_speed_declared.startswith("not declared")
    assert disc.drive_speed_low_x is None and disc.drive_speed_high_x is None


# --- Never raises -------------------------------------------------------------------


@given(st.text(max_size=300))
def test_the_drive_speed_reader_never_raises(tail: str) -> None:
    match = cyanrip_log._DRIVE_SPEED.match("Drive speed:    " + tail)
    if match is not None:
        cyanrip_log._take_drive_speed(cyanrip_log._Disc(), match)


@given(st.text(max_size=200))
def test_the_album_rows_never_raise(tail: str) -> None:
    for pattern, take in (
        (cyanrip_log._ALBUM_INTEGRATED_LOUDNESS, "integrated_lufs"),
        (cyanrip_log._ALBUM_LOUDNESS_RANGE, "lra_lu"),
        (cyanrip_log._ALBUM_SAMPLE_PEAK_LEVEL, "sample_peak_dbfs"),
        (cyanrip_log._ALBUM_TRUE_PEAK_LEVEL, "true_peak_dbfs"),
    ):
        head = pattern.pattern.split(r"\s+")[0].lstrip("^").replace("\\", "")
        match = pattern.match(f"{head} unknown ({tail})")
        if match is not None:
            cyanrip_log._record_album_row(cyanrip_log._Disc(), take, match)


@given(st.text(max_size=400))
def test_the_ripping_error_parts_never_raise(parts: str) -> None:
    match = cyanrip_log._RIP_ERRORS.match(f"Ripping errors: 3 ({parts})")
    if match is not None:
        ripping_error_parts.from_match(match)


def test_the_progress_line_reads_both_clauses() -> None:
    """S25's `rest of rip read once` is the same value as `ETA`, under a new name."""
    pytest.importorskip("PySide6")
    from platterpus.workers import rip_worker

    new = "Ripping and encoding track 3, progress - 42.00%, rest of rip read once - 3m, errors - 2"
    old = "Ripping track 5, progress - 42.37%, ETA - 3m, errors - 0"
    for line, clause in ((new, "rest of rip read once"), (old, "ETA")):
        match = rip_worker._CYANRIP_TRACK_PROGRESS.search(line)
        assert match is not None
        assert match.group("eta") == "3m"
        assert match.group("eta_clause") == clause
        # The log pane strips the clause and keeps the running error count.
        stripped = rip_worker._CYANRIP_ETA_CLAUSE.sub("", line)
        assert "3m" not in stripped and "errors - " in stripped


def test_the_ladder_counts_only_the_drive_s_parts() -> None:
    """A cover-art write or an encoder is not the drive's fault: counted as one, the
    read-speed ladder would re-rip a disc slower for nothing (TASKS R193). The
    encoder failure is named twice, in the parts and on `Encoder errors:`, and is
    taken out once."""
    text = _log_with(
        replace={
            "Ripping errors:": (
                "Ripping errors: 6 (4 frame reads with errors, "
                "1 cover art write failed, 1 encoder failed)"
            ),
            "Encoder errors:": (
                "Encoder errors: 1 track failed (1), read not completed; "
                "no whole track was encoded"
            ),
        },
        insert_after={},
    )
    log = cyanrip_log.parse_cyanrip_log(text)
    assert log.ripping_errors == 6
    assert log.drive_read_errors == 4
