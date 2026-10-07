"""The one reading of the fork's ``Handshake:`` note (round 31, E7).

The fork proposes that a build's released arm be decided by its build flag and a
clean tree alone, so a release cut while a round is open would say
``... OPEN ... -- released build``. Both our readers took the word *open* as
*unreleased* until 2026-10-07; these pin the shared reading they now delegate to,
on every shape the fork has emitted and on the one E7 adds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus import handshake_approval, handshake_note, rip_audit

#: Every note shape on record, with the release state it must read as.
_SHAPES: list[tuple[str, str]] = [
    # Before round 10 a released build printed no suffix.
    ("round 7 lap 39 closed, verdict GO", "released"),
    ("round 7 lap 33 OPEN, verdict HOLD", "unreleased"),
    ("round 7 lap 33 OPEN, verdict HOLD -- NOT a released build", "unreleased"),
    ("round 30 lap 11 OPEN, verdict OPEN -- NOT a released build", "unreleased"),
    ("round 30 lap 17 closed, verdict GO -- released build", "released"),
    (
        "round 30 lap 17 closed, verdict GO -- released build "
        "(declared at build time, not verified by cyanrip)",
        "released",
    ),
    # E7: a release cut while a round is open. The round is information.
    ("round 31 lap 3 OPEN, verdict OPEN -- released build", "released"),
    # A closed round's tree built without the flag, or dirty.
    ("round 30 lap 17 closed, verdict GO -- NOT a released build", "unreleased"),
    ("", "not_determined"),
    ("something the fork has never written", "not_determined"),
]


@pytest.mark.parametrize(("note", "expected"), _SHAPES)
def test_every_note_shape_reads_as_its_release_state(note: str, expected: str) -> None:
    assert handshake_note.release_state(note) == expected


def test_a_release_cut_while_a_round_is_open_is_not_warned_as_unreleased() -> None:
    """Regression (round 31 lap 1 S16): under E7 this is a released build."""
    note = "round 31 lap 3 OPEN, verdict OPEN -- released build"
    report = {
        "rip": {"ripper_handshake_note": note, "ripper_handshake_approval": "approved"}
    }
    album = rip_audit.AlbumAudit(folder=Path("album"))
    rip_audit._audit_handshake_note(report, album)
    warned = [f.text for f in album.findings if f.level == rip_audit.LEVEL_WARN]
    assert not warned, warned
    assert handshake_approval.cross_check_note("approved", note) == ""


def test_an_unreleased_build_is_still_warned_and_still_disagrees() -> None:
    """The other arm, so the change cannot pass by warning about nothing."""
    note = "round 30 lap 11 OPEN, verdict OPEN -- NOT a released build"
    report = {
        "rip": {"ripper_handshake_note": note, "ripper_handshake_approval": "approved"}
    }
    album = rip_audit.AlbumAudit(folder=Path("album"))
    rip_audit._audit_handshake_note(report, album)
    warned = [f.text for f in album.findings if f.level == rip_audit.LEVEL_WARN]
    assert any(m.startswith(rip_audit.OPEN_ROUND_WARNING) for m in warned), warned
    assert any(m.startswith("DISAGREEMENT") for m in warned), warned
    assert handshake_approval.cross_check_note("approved", note) != ""
