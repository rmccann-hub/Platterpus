# SPDX-License-Identifier: GPL-3.0-only
"""`scripts/lap_turn.py`: who released the last lap, and who holds the next.

The owner's first question for both repos (2026-11-12). The decision is pure
and tested here on every form ``HANDSHAKE-NEXT-LAP`` takes; one test reads this
repository's own laps, so the parser is held to real files and not only to
the shapes written below.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lap_turn import Lap, decide, laps_at, parse_lap, render, turn_line  # noqa: E402

US = "platterpus"
THEM = "cyanrip-fork"


def _lap(r: int, n: int, author: str, next_lap: str, released: bool = True) -> Lap:
    return Lap(r, n, author, released, next_lap, "test")


def test_our_released_lap_naming_yours_puts_the_turn_with_the_fork() -> None:
    turn = decide(
        [
            _lap(39, 3, THEM, "4 (yours): your reading of this lap"),
            _lap(39, 4, US, "5 (yours): your reading of this lap and of 0.7.123"),
        ]
    )
    assert turn.last is not None and (turn.last.round, turn.last.lap) == (39, 4)
    assert turn.next_holder == THEM and turn.next_number == 5


def test_their_released_lap_naming_yours_puts_the_turn_with_us() -> None:
    turn = decide([_lap(39, 1, THEM, "2 (yours): your reading of .31")])
    assert turn.next_holder == US and turn.next_number == 2


def test_ours_names_the_author_itself() -> None:
    turn = decide([_lap(38, 15, US, "16 (ours): held for the owner")])
    assert turn.next_holder == US


def test_a_held_lap_does_not_move_the_turn_but_is_listed() -> None:
    """The other side cannot read a held lap, so the turn stays where the last
    RELEASED lap put it, and the held one is named so it is not forgotten."""
    turn = decide(
        [
            _lap(39, 3, THEM, "4 (yours): …"),
            _lap(39, 4, US, "5 (yours): …", released=False),
        ]
    )
    assert turn.last is not None and turn.last.lap == 3
    assert turn.next_holder == US
    assert [(x.round, x.lap) for x in turn.held] == [(39, 4)]


def test_an_old_lap_with_no_release_header_is_history_not_held() -> None:
    turn = decide(
        [_lap(7, 4, THEM, "", released=False), _lap(39, 4, US, "5 (yours): …")]
    )
    assert turn.held == ()


def test_a_released_copy_outranks_a_held_copy_of_the_same_lap() -> None:
    """Our lap on main is released; a stale held copy elsewhere must not hide it."""
    turn = decide(
        [
            _lap(39, 4, US, "5 (yours): …", released=False),
            _lap(39, 4, US, "5 (yours): …", released=True),
        ]
    )
    assert turn.last is not None and turn.last.released
    assert turn.held == ()


def test_a_closing_lap_is_quoted_not_guessed() -> None:
    turn = decide([_lap(38, 18, THEM, "none — round 38 closes on this lap")])
    assert turn.next_holder is None
    assert "round 38 closes" in turn.next_text
    assert "read it" in render(turn, "As of a fetch just now.")


def test_no_released_lap_says_so() -> None:
    turn = decide([_lap(1, 1, US, "2 (yours)", released=False)])
    assert turn.last is None
    assert "No released lap" in render(turn, "")


def test_only_a_lap_file_from_a_known_side_is_a_lap() -> None:
    text = "HANDSHAKE-FROM: platterpus\nHANDSHAKE-READY-TO-READ: yes — released\n"
    assert parse_lap("round-39-lap-04.md", text, "x") is not None
    assert parse_lap("README.md", text, "x") is None
    assert parse_lap("round-39-lap-04.md", "HANDSHAKE-FROM: someone\n", "x") is None
    held = parse_lap(
        "round-39-lap-04.md",
        "HANDSHAKE-FROM: platterpus\nHANDSHAKE-READY-TO-READ: no\n",
        "x",
    )
    assert held is not None and not held.released


def test_this_repositorys_own_laps_give_an_answer() -> None:
    """Read at HEAD, as the script reads origin/main: real files, both folders.

    Floors, so the test cannot pass by finding nothing: dozens of laps, and the
    newest released one must name its next lap in a form the decision reads or
    quotes."""
    laps = laps_at(
        REPO_ROOT,
        "HEAD",
        ("docs/handshake/outbound", "docs/handshake/inbound"),
        "Platterpus",
    )
    assert len(laps) >= 50, f"only {len(laps)} laps read"
    assert {lap.author for lap in laps} == {US, THEM}
    turn = decide(laps)
    assert turn.last is not None and turn.last.released
    assert turn.next_holder in (US, THEM) or turn.next_text


# --- the HANDOFF block's first line (the owner, 2026-11-13) --------------------


def test_our_turn_names_the_lap_the_repo_and_the_lap_expected_back() -> None:
    turn = decide([_lap(39, 5, THEM, "6 (yours): the EAC re-rip read")])
    assert turn_line(turn) == (
        "MY TURN TO SEND: round 39 lap 6 goes to rmccann-hub/cyanrip "
        "platterpus-fork, expecting round 39 lap 7 back."
    )


def test_after_we_send_it_is_our_turn_to_wait() -> None:
    turn = decide(
        [
            _lap(39, 5, THEM, "6 (yours): …"),
            _lap(39, 6, US, "7 (yours): your GO"),
        ]
    )
    assert turn_line(turn) == (
        "MY TURN TO WAIT: round 39 lap 6 went to rmccann-hub/cyanrip "
        "platterpus-fork, expecting round 39 lap 7 back."
    )


def test_a_lap_of_ours_written_and_held_is_still_ours_to_send() -> None:
    """The fork cannot read a held lap, so holding it is not waiting."""
    turn = decide(
        [
            _lap(39, 5, THEM, "6 (yours): …"),
            _lap(39, 6, US, "7 (yours): …", released=False),
        ]
    )
    assert turn_line(turn).startswith("MY TURN TO SEND: round 39 lap 6 is written")


def test_from_the_forks_side_the_same_record_reads_the_other_way() -> None:
    turn = decide([_lap(39, 5, THEM, "6 (yours): …")])
    assert turn_line(turn, me=THEM) == (
        "MY TURN TO WAIT: round 39 lap 5 went to rmccann-hub/Platterpus main, "
        "expecting round 39 lap 6 back."
    )


def test_a_closing_lap_names_no_turn_rather_than_guessing_one() -> None:
    turn = decide([_lap(38, 18, THEM, "none — round 38 closes on this lap")])
    assert turn_line(turn).startswith("NEITHER SIDE'S TURN IS NAMED")


def test_render_puts_the_turn_first() -> None:
    turn = decide([_lap(39, 5, THEM, "6 (yours): …")])
    assert (
        render(turn, "As of a fetch just now.")
        .splitlines()[0]
        .startswith("MY TURN TO SEND")
    )
