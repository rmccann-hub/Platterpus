# SPDX-License-Identifier: GPL-3.0-only
"""The `Ripping errors:` line with every part named (TASKS R174).

The fork's round 41 lap 1 S16 proposes, for a build after `.33`::

    Ripping errors: 57 (28 frame reads failed, 28 paranoia skips, 1 track not finished)

the leading count unchanged, then each non-zero part in the order `frame reads
failed`, `sectors failing EDC`, `paranoia skips`, `tracks not finished`, `disc
lookups failed`, replacing `(including N paranoia skips)`, which they stop
printing only after a release of ours reads both. These tests hold that we read
BOTH wordings through the real parser (`parse_cyanrip_log`), that the skip field
the read-speed ladder subtracts is fed from either, and that a part we do not
know is kept and counted rather than dropped (CLAUDE.md, diagnostic
completeness). The older wording's own tests stay in `test_parsers_cyanrip_log.py`.
"""

from __future__ import annotations

import logging

import pytest

from platterpus import ripping_error_parts as parts_mod
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog
from platterpus.ripping_error_parts import (
    FORM_COUNT_ONLY,
    FORM_INCLUDING,
    FORM_NAMED,
    FORM_UNRECOGNISED,
    MAX_UNKNOWN_KEPT,
    PART_FIELDS,
    RippingErrorParts,
)

#: The lap's own example, word for word (round 41 lap 1 S16).
_LAP_EXAMPLE: str = (
    "Ripping errors: 57 (28 frame reads failed, 28 paranoia skips, "
    "1 track not finished)"
)


def _parse(line: str) -> RipLog:
    """The real parser over a log whose footer is ``line``."""
    return parse_cyanrip_log(f"cyanrip 0.9.4\n{line}\n")


def _parts(line: str) -> RippingErrorParts:
    """The parts the real parser read from ``line``; the line must be read."""
    parsed = _parse(line)
    assert parsed.ripping_error_parts is not None, line
    return parsed.ripping_error_parts


def _values(parts: RippingErrorParts) -> dict[str, int | None]:
    return {name: getattr(parts, name) for name in PART_FIELDS}


def test_the_laps_example_reads_every_part_and_the_total() -> None:
    parsed = _parse(_LAP_EXAMPLE)
    assert parsed.ripping_errors == 57
    parts = parsed.ripping_error_parts
    assert parts is not None and parts.form == FORM_NAMED
    # Parts not printed are zero: only non-zero parts are printed, and every
    # printed part was recognised.
    assert _values(parts) == {
        "frame_reads_failed": 28,
        "sectors_failing_edc": 0,
        "paranoia_skips": 28,
        "tracks_not_finished": 1,
        "disc_lookups_failed": 0,
    }
    assert parts.unknown == () and parts.unknown_total == 0
    # Today's skip field is fed from the new wording, and the ladder's
    # subtraction is unchanged: N minus the skips minus failed encodes.
    assert parsed.ripping_errors_paranoia_skips == 28
    assert parsed.drive_read_errors == 29
    # The user-facing sentence still counts N, as it does for `.20`'s wording.
    assert parsed.health_status == "57 ripping errors"


@pytest.mark.parametrize(
    ("plural", "singular", "field"),
    [
        ("frame reads failed", "frame read failed", "frame_reads_failed"),
        ("sectors failing EDC", "sector failing EDC", "sectors_failing_edc"),
        ("paranoia skips", "paranoia skip", "paranoia_skips"),
        ("tracks not finished", "track not finished", "tracks_not_finished"),
        ("disc lookups failed", "disc lookup failed", "disc_lookups_failed"),
    ],
)
@pytest.mark.parametrize("count", [1, 2, 4096])
def test_every_part_is_read_alone_in_both_numbers(
    plural: str, singular: str, field: str, count: int
) -> None:
    """Each of the five, alone, plural and singular whatever the number.

    The lap spells one singular (`1 track not finished`), so every label is read
    in both numbers, beside any count.
    """
    for printed in (plural, singular):
        parts = _parts(f"Ripping errors: {count} ({count} {printed})")
        expected = dict.fromkeys(PART_FIELDS, 0)
        expected[field] = count
        assert _values(parts) == expected, printed
        assert parts.unknown_total == 0


def test_all_five_in_the_promised_order() -> None:
    line = (
        "Ripping errors: 15 (1 frame read failed, 2 sectors failing EDC, "
        "3 paranoia skips, 4 tracks not finished, 5 disc lookups failed)"
    )
    parts = _parts(line)
    assert _values(parts) == {
        "frame_reads_failed": 1,
        "sectors_failing_edc": 2,
        "paranoia_skips": 3,
        "tracks_not_finished": 4,
        "disc_lookups_failed": 5,
    }


def test_a_part_out_of_the_promised_order_is_still_read_as_itself() -> None:
    """We key on the label, never the position."""
    parts = _parts("Ripping errors: 6 (5 disc lookups failed, 1 frame read failed)")
    assert parts.frame_reads_failed == 1
    assert parts.disc_lookups_failed == 5
    assert parts.paranoia_skips == 0


def test_a_part_we_do_not_know_is_kept_counted_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Never dropped: kept verbatim, counted, and named in a warning.

    And with an unknown part on the line, an absent known part is not stated
    rather than 0, because the unknown one may be a known part renamed; the
    ladder then states no drive count rather than one it cannot have.
    """
    with caplog.at_level(logging.WARNING, logger="platterpus.parsers.cyanrip_log"):
        parsed = _parse(
            "Ripping errors: 9 (2 frame reads failed, 7 sectors with bad Q)"
        )
    parts = parsed.ripping_error_parts
    assert parts is not None and parts.form == FORM_NAMED
    assert parts.frame_reads_failed == 2
    assert parts.unknown == (parts_mod.UnknownPart("7 sectors with bad Q", 7),)
    assert parts.unknown_total == 1
    assert parts.paranoia_skips is None and parts.sectors_failing_edc is None
    assert parsed.ripping_errors_paranoia_skips is None
    assert parsed.drive_read_errors is None
    assert "7 sectors with bad Q" in caplog.text
    assert "1 part(s) we do not recognise" in caplog.text


def test_a_known_label_printed_twice_keeps_the_second_as_unknown() -> None:
    parts = _parts("Ripping errors: 5 (2 paranoia skips, 3 paranoia skips)")
    assert parts.paranoia_skips == 2
    assert parts.unknown == (parts_mod.UnknownPart("3 paranoia skips", 3),)


def test_unknown_parts_past_the_bound_are_counted_not_kept() -> None:
    extra = 5
    pieces = ", ".join(f"{n} oddities" for n in range(MAX_UNKNOWN_KEPT + extra))
    parts = _parts(f"Ripping errors: 99 ({pieces})")
    assert len(parts.unknown) == MAX_UNKNOWN_KEPT
    assert parts.unknown_elided == extra
    assert parts.unknown_total == MAX_UNKNOWN_KEPT + extra
    assert parts_mod.unknown_summary(parts).endswith(f"and {extra} more not kept")


def test_a_part_with_no_number_is_kept_with_no_count_invented() -> None:
    parts = _parts("Ripping errors: 3 (3 frame reads failed, and more)")
    assert parts.frame_reads_failed == 3
    assert parts.unknown == (parts_mod.UnknownPart("and more", None),)


def test_an_implausible_part_is_not_determined() -> None:
    parts = _parts("Ripping errors: 3 (99999999999999999999 paranoia skips)")
    assert parts.paranoia_skips is None


@pytest.mark.parametrize(
    ("line", "form", "skips", "drive"),
    [
        # The older wordings read exactly as before (their own tests are in
        # `test_parsers_cyanrip_log.py`): every part but the skips not stated.
        ("Ripping errors: 0", FORM_COUNT_ONLY, 0, 0),
        ("Ripping errors: 3", FORM_COUNT_ONLY, 0, 3),
        (
            "Ripping errors: 2589 (including 2586 paranoia skips)",
            FORM_INCLUDING,
            2586,
            3,
        ),
        ("Ripping errors: 1 (including 1 paranoia skip)", FORM_INCLUDING, 1, 0),
        ("Ripping errors: 7 (including 7 skips)", FORM_UNRECOGNISED, None, None),
    ],
)
def test_the_older_wordings_still_read_as_before(
    line: str, form: str, skips: int | None, drive: int | None
) -> None:
    parsed = _parse(line)
    parts = parsed.ripping_error_parts
    assert parts is not None and parts.form == form
    assert parsed.ripping_errors_paranoia_skips == skips
    assert parsed.drive_read_errors == drive
    others = [name for name in PART_FIELDS if name != "paranoia_skips"]
    assert all(getattr(parts, name) is None for name in others)


def test_an_unrecognised_suffix_is_kept_verbatim() -> None:
    parts = _parts("Ripping errors: 7 (including 7 skips)")
    assert parts.unknown == (parts_mod.UnknownPart("(including 7 skips)", None),)


def test_no_line_states_no_parts() -> None:
    parsed = parse_cyanrip_log("cyanrip 0.9.4\nTrack 1 read successfully!\n")
    assert parsed.ripping_error_parts is None
