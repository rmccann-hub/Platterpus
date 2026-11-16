"""`.33`'s ``cyanrip-diagnostics/14`` record, read through our readers (round 41).

The fork's round 41 lap 1 says the record moves to ``/14`` and adds one key,
``drive_declared.read_performance`` (their S4, ``cyanrip@13bec0a:src/diagnostics.c:415-444``),
and that our readers take any schema starting ``cyanrip-diagnostics/``, so a ``/14``
record reads as a ``/13`` one did and the new key is one none of them reads (their
S5, citing ``src/platterpus/ripper_ending.py:53`` and ``:104``). **Checked here, not
taken:** the record is their golden reference as published with ``.33``, byte for
byte (``tests/fixtures/cyanrip_fork_diagnostics14_golden.json``, from
``cyanrip@57cbf654:docs/golden-reference.diagnostics.json``), and the two
``read_performance`` forms a drive gives are the strings their own unit test expects
(``cyanrip@13bec0a:tests/diagrecord.c:580-605``), since no drive has answered GET
PERFORMANCE yet (their S8).

Both readers that recognise a record by its schema are held: ``ripper_ending`` (the
ending) and ``isrc_provenance`` (the tracks and ``drive_declared``, read through
``record_drive_declared``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import pytest

from platterpus import record_drive_declared as declared
from platterpus.isrc_provenance import parse_isrcs
from platterpus.ripper_ending import RECORD_SCHEMA_PREFIX, STATE_READ, parse_ending

_GOLDEN_14: Final[Path] = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_diagnostics14_golden.json"
)

#: `tests/diagrecord.c:591-595`: one whole descriptor of two declared.
_ANSWERED: Final[dict[str, Any]] = {
    "answered": True, "length": 40, "truncated": True,
    "bytes": "00000024000000000000000000000583" "00052B0F00000C3C00000000",
    "descriptors": [
        {"start_lba": 0, "start_kb_per_s": 1411, "end_lba": 338703,
         "end_kb_per_s": 3132},
    ],
}  # fmt: skip
#: `tests/diagrecord.c:602-603`: refused.
_REFUSED: Final[dict[str, Any]] = {
    "answered": False, "length": None, "truncated": None, "bytes": None,
    "descriptors": None,
}  # fmt: skip

#: A drive's `drive_declared` as `/13` gave it, the fields our reader reads.
_INQUIRY: Final[dict[str, Any]] = {
    "answered": True, "length": 8, "truncated": False, "bytes": "0580003200000000",
}  # fmt: skip


def _golden() -> dict[str, Any]:
    data = json.loads(_GOLDEN_14.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_the_published_record_is_14_and_reads_as_13_did() -> None:
    data = _golden()
    # Non-triviality: this is the `/14` record `.33` writes, not an older one.
    assert data["schema"] == "cyanrip-diagnostics/14"
    assert data["cyanrip"]["version"] == "0.9.4-rc3+platterpus.33"
    assert data["schema"].startswith(RECORD_SCHEMA_PREFIX)
    text = _GOLDEN_14.read_text(encoding="utf-8")

    ending = parse_ending(text)
    assert ending.state == STATE_READ
    assert (ending.exit_code, ending.interrupted) == (0, False)

    reading = parse_isrcs(text)
    assert reading.state == STATE_READ
    assert [t.number for t in reading.tracks] == [1, 2, 3]
    # An image is no drive: `drive_declared` is null, so GET PERFORMANCE was not
    # asked and `read_performance` has nowhere to be (their S4).
    assert data["drive_declared"] is None
    assert reading.drive_declared.state == declared.NOT_STATED


@pytest.mark.parametrize("performance", [None, _ANSWERED, _REFUSED])
def test_read_performance_changes_nothing_our_reader_reads(
    performance: dict[str, Any] | None,
) -> None:
    """The new key beside a `/13` drive's fields: read as before, never refused."""
    without = {"drive_declared": {"inquiry": _INQUIRY}}
    with_key = {
        "drive_declared": {"inquiry": _INQUIRY, "read_performance": performance}
    }
    before = declared.parse_drive_declared(without)
    after = declared.parse_drive_declared(with_key)
    assert before.state == declared.READ
    assert after == before


def test_a_14_record_with_a_drive_reads_through_the_whole_reader() -> None:
    """The golden record with a drive's `drive_declared` in it, as a rip on the
    BDR-209D will write it: `/14` and `read_performance` both present."""
    data = _golden()
    data["drive_declared"] = {"inquiry": _INQUIRY, "read_performance": _ANSWERED}
    text = json.dumps(data)
    assert parse_ending(text).state == STATE_READ
    reading = parse_isrcs(text)
    assert reading.state == STATE_READ
    assert reading.drive_declared.state == declared.READ
    assert reading.drive_declared.inquiry is not None
