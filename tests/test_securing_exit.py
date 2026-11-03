"""The securing pass's two exit statuses, each named (TASKS R64).

Disc 1 of the 2026-10-21 Full run was stopped during its securing pass. Its
report (`round36full1021bwholediscreport.json`, evidence `08de9851`) held
`outcome.securing_pass_exit_code: 1`; the pass's own `--diagnostics` record in
the same bundle (`round36full1021bjrecord20261022t001928zsecuringpass.json`)
held `exit_code: 143`. One is the wrapper's, the other cyanrip's, and neither
field said which. The record here is synthetic, with the real record's
`schema`, `exit_code` and `rip.interrupted*` fields.
"""

from __future__ import annotations

import json
from pathlib import Path

from platterpus import record_fate
from platterpus.rip_report import build_outcome
from platterpus.ripper_ending import RipperEnding
from platterpus.securing_exit import READER_IS, WRAPPER_IS, exits_block

#: The fields of disc 1's securing-pass record that this reads.
_DISC1_RECORD = {
    "schema": "cyanrip-diagnostics/10",
    "exit_code": 143,
    "rip": {"interrupted": True, "interrupted_by": "SIGTERM"},
}


def _keep(tmp_path: Path, record: object) -> record_fate.RecordFate:
    temp = tmp_path / "platterpus-refix-x"
    temp.mkdir()
    told = temp / "cyanrip-diagnostics-20261022T001928Z.json"
    told.write_text(json.dumps(record), encoding="utf-8")
    rips = tmp_path / "rips"
    rips.mkdir()
    return record_fate.keep_securing_record(told, rips, started=True, cancelled=True)


def test_disc_1s_two_codes_are_both_recorded_each_named(tmp_path: Path) -> None:
    fate = _keep(tmp_path, _DISC1_RECORD)
    assert fate.state == record_fate.STATE_KEPT, fate
    outcome = build_outcome(
        status="cancelled",
        securing_pass_started=True,
        securing_pass_exit_code=1,
        securing_pass_record=fate,
    )
    block = outcome["securing_pass_exit_codes"]
    assert block is not None
    assert (block["wrapper"], block["reader"]) == (1, 143)
    assert block["wrapper_is"] == WRAPPER_IS and block["reader_is"] == READER_IS
    assert "~/.local/bin/cyanrip" in block["wrapper_is"]
    assert block["agree"] is False and block["reader_record_state"] == "read"
    assert "exited 1;" in block["sentence"] and "143 (SIGTERM)" in block["sentence"]
    # The old field is unchanged: still the wrapper's, as it always was.
    assert outcome["securing_pass_exit_code"] == 1


def test_no_securing_pass_has_no_pair() -> None:
    assert build_outcome(status="success")["securing_pass_exit_codes"] is None
    assert exits_block(started=False, wrapper_code=0, ending=None) is None


def test_a_missing_or_unread_record_is_not_determined_never_zero(
    tmp_path: Path,
) -> None:
    """Tri-state: no record read is `reader` null and `agree` null, never 0 or
    a guess that the two agree."""
    missing = record_fate.keep_securing_record(
        tmp_path / "gone.json", tmp_path, started=True, cancelled=True
    )
    block = build_outcome(
        status="cancelled",
        securing_pass_started=True,
        securing_pass_exit_code=1,
        securing_pass_record=missing,
    )["securing_pass_exit_codes"]
    assert block is not None
    assert block["reader"] is None and block["agree"] is None
    assert block["reader_record_state"] == "not_read"
    assert "record says it exited not known" in block["sentence"]
    unrecognised = exits_block(
        started=True, wrapper_code=None, ending=RipperEnding("unrecognised")
    )
    assert unrecognised is not None
    assert unrecognised["reader"] is None and unrecognised["wrapper"] is None


def test_two_codes_that_agree_say_so() -> None:
    block = exits_block(
        started=True, wrapper_code=0, ending=RipperEnding("read", exit_code=0)
    )
    assert block is not None and block["agree"] is True
    assert "differ" not in block["sentence"]


def test_a_bool_is_not_an_exit_status() -> None:
    block = exits_block(
        started=True, wrapper_code=True, ending=RipperEnding("read", exit_code=1)
    )
    assert block is not None and block["wrapper"] is None and block["agree"] is None
