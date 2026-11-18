"""Which kind of failure the ripper's exit status names, for the build that ran.

From `.25` (fork release 36) cyanrip exits 64 for a refused argument or flag, 74
when the disc or drive failed, and 128 + N for a run a signal stopped; 1 stays the
generic failure. Earlier builds and stock cyanrip exit 1 for all of it. These pin
`ripper_exit_class`: every class, the builds on each side of the threshold, the
builds we cannot place, and the one claim it must never make: a class the build
cannot emit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.deps.fork_source import release_seq_for_commit
from platterpus.rip_report import build_outcome
from platterpus.ripper_exit import FIRST_RELEASE_WITH_EXIT_CLASSES
from platterpus.ripper_exit_class import (
    DISC_OR_DRIVE_EXIT,
    EXIT_CLASSES,
    build_speaks_exit_classes,
    classify_exit,
    describe_exit_class,
    explain_failed_exit,
)

#: `.25`, release 36: the first build with the classes.
_WITH = "platterpus-fork-g5f1d036"
#: `.24` (release 35) and `.23` (release 33): the last builds without them.
_BEFORE = ("platterpus-fork-g93afa15", "platterpus-fork-g891c79e")
#: Stock cyanrip's banner tag.
_STOCK = "release"
#: A fork commit outside the release list, a tag we do not recognise, no tag.
_UNPLACEABLE = ("platterpus-fork-g0000000", "g1a2b3c4", "")

#: The fork's provider contract for `.25`, whose P4 table is the source of truth.
_CONTRACT = (
    Path(__file__).resolve().parent.parent
    / "docs/handshake/inbound/artifacts/round-35-lap-15-provider-contract-g3e978f9.md"
)


@pytest.mark.parametrize(
    ("code", "tag", "expected"),
    [
        # The classes, on the first build that emits them (clean and dirty).
        (64, _WITH, "refused"),
        (74, _WITH, "disc_or_drive"),
        (74, f"{_WITH}-dirty", "disc_or_drive"),
        (1, _WITH, "failure"),
        (3, _WITH, "failure"),
        # The same numbers on builds that cannot emit a class: no class claimed.
        (64, _BEFORE[0], "unclassified"),
        (74, _BEFORE[0], "unclassified"),
        (74, _BEFORE[1], "unclassified"),
        (1, _BEFORE[0], "unclassified"),
        (74, _STOCK, "unclassified"),
        (1, _STOCK, "unclassified"),
        # A build we cannot place: the build-dependent codes are not determined.
        (74, _UNPLACEABLE[0], "not_determined"),
        (64, _UNPLACEABLE[1], "not_determined"),
        (1, _UNPLACEABLE[2], "not_determined"),
    ],
)
def test_each_code_reads_by_the_build_that_ran(
    code: int, tag: str, expected: str
) -> None:
    assert classify_exit(code, tag) == expected


@pytest.mark.parametrize("tag", [_WITH, *_BEFORE, _STOCK, *_UNPLACEABLE])
def test_the_build_independent_readings_hold_on_every_build(tag: str) -> None:
    """0, a signal and podman's 125 mean the same whatever produced them."""
    assert classify_exit(0, tag) == "ok"
    assert classify_exit(137, tag) == "signal"  # SIGKILL through the wrapper
    assert classify_exit(143, tag) == "signal"  # SIGTERM; `.25`'s own 128 + N too
    assert classify_exit(-9, tag) == "signal"  # Popen's own report of SIGKILL
    assert classify_exit(125, tag) == "container_tool"
    # No exit status at all is never a class.
    assert classify_exit(None, tag) == "not_determined"


def test_the_threshold_is_the_release_of_the_build_that_brought_the_classes() -> None:
    """Derived from the release list, not restated: `.25` is 36, `.24` is below."""
    assert release_seq_for_commit("5f1d036") == FIRST_RELEASE_WITH_EXIT_CLASSES
    seq_24 = release_seq_for_commit("93afa15")
    assert seq_24 is not None and seq_24 < FIRST_RELEASE_WITH_EXIT_CLASSES
    assert build_speaks_exit_classes(_WITH) is True
    assert all(build_speaks_exit_classes(t) is False for t in (*_BEFORE, _STOCK))
    assert all(build_speaks_exit_classes(t) is None for t in _UNPLACEABLE)


def test_the_numbers_are_the_ones_the_providers_contract_states() -> None:
    """Read off the fork's P4 table, so a renumbering there turns this red."""
    text = _CONTRACT.read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| `(\d+)` \| \d+ \| `(CRIP_[A-Z_]+)`", text, re.M))
    assert len(rows) >= 8, f"examined too few P4 rows to compare: {rows}"
    assert rows["64"] == "CRIP_EXIT_USAGE"
    assert rows[str(DISC_OR_DRIVE_EXIT)] == "CRIP_EXIT_IOERR"
    assert rows["1"] == "CRIP_EXIT_FAILURE"
    assert "`128 + quit_signal`" in text and "CRIP_EXIT_SIGNAL_BASE" in text


@given(code=st.one_of(st.none(), st.integers()), tag=st.text(max_size=80))
def test_classify_never_raises_and_answers_in_the_vocabulary(
    code: int | None, tag: str
) -> None:
    assert classify_exit(code, tag) in EXIT_CLASSES


@given(code=st.integers(), tag=st.sampled_from([*_BEFORE, _STOCK, *_UNPLACEABLE]))
def test_no_build_without_the_classes_is_ever_given_one(code: int, tag: str) -> None:
    """The claim this module must never make, over every exit code."""
    assert classify_exit(code, tag) not in {"refused", "disc_or_drive", "failure"}


def test_only_the_two_actionable_classes_get_a_sentence() -> None:
    drive = describe_exit_class("disc_or_drive", 74)
    assert "The disc or the drive failed" in drive and "exited 74" in drive
    assert "rip log view" in drive, "it must point at cyanrip's own message"
    refused = describe_exit_class("refused", 64)
    assert "refused an argument or a flag" in refused and "exit 64" in refused
    assert "disc and the drive are not the cause" in refused
    for other in EXIT_CLASSES:
        if other not in {"disc_or_drive", "refused"}:
            assert describe_exit_class(other, 1) == "", other


def test_the_signal_and_podman_wording_is_kept_and_asked_first() -> None:
    """`describe_unrequested_exit` stays the authority for 128 + N and 125."""
    killed = explain_failed_exit(137, _WITH, we_stopped_it=False)
    assert "stopped from outside Platterpus" in killed
    podman = explain_failed_exit(125, _WITH, we_stopped_it=False)
    assert "container tool (podman)" in podman
    # A rip we stopped is described by the stop, whatever its code.
    assert explain_failed_exit(74, _WITH, we_stopped_it=True) == ""
    assert explain_failed_exit(137, _WITH, we_stopped_it=True) == ""
    assert "disc or the drive" in explain_failed_exit(74, _WITH, we_stopped_it=False)
    assert explain_failed_exit(74, _BEFORE[0], we_stopped_it=False) == ""


@pytest.mark.parametrize(
    ("code", "tag", "cls", "recorded_tag"),
    [
        (74, _WITH, "disc_or_drive", _WITH),
        (64, f"  {_WITH}  ", "refused", _WITH),
        (74, _BEFORE[0], "unclassified", _BEFORE[0]),
        (74, None, "not_determined", None),
        (None, _WITH, "not_determined", _WITH),
    ],
)
def test_the_report_records_the_class_beside_the_code(
    code: int | None, tag: str | None, cls: str, recorded_tag: str | None
) -> None:
    """`outcome` carries the class and the tag it was read against (schema v39)."""
    outcome = build_outcome(
        status="failed", ripper_exit_code=code, ripper_build_tag=tag
    )
    assert outcome["ripper_exit_code"] == code
    assert outcome["ripper_exit_class"] == cls
    assert outcome["ripper_exit_build_tag"] == recorded_tag


def test_a_stand_in_workers_non_string_tag_is_no_tag() -> None:
    """The window passes `getattr(worker, ...)`; a mock's attribute is not a tag."""
    outcome = build_outcome(
        status="failed",
        ripper_exit_code=74,
        ripper_build_tag=object(),  # type: ignore[arg-type]  # a mock's attribute
    )
    assert outcome["ripper_exit_class"] == "not_determined"
    assert outcome["ripper_exit_build_tag"] is None


# --- `.34`'s TOC refusal, exit 74 (round 41, 2026-11-16) ---------------------------

#: `.34`'s build tag, the build under review from the fork's round 41 lap 3 (S9).
_DOT34 = "platterpus-fork-gfb28088"

#: `.34`'s new fatal line as a run prints it, its `%i`s filled: the format is P5 row
#: `cyanrip_main.c:679` of `round-41-lap-03-provider-contract-g3069c11.md`, logged at
#: `cyanrip@fb28088:src/cyanrip_main.c:679` before anything is read; the init that
#: fails on it returns `CRIP_EXIT_IOERR` at `:4029-4030` (their lap 3 S13).
_INVALID_TOC = "Invalid TOC: track 2 starts at LSN 0, not after track 1 at LSN 150!"


def test_dot34s_invalid_toc_refusal_is_the_disc_class_with_its_own_sentence() -> None:
    """Their lap 3 S13: an unordered TOC ends the run with exit 74 and a new fatal
    line. Our class reading of a 74 depends on placing the build by its release
    number, so `.34` reads `disc_or_drive` only because its row (release 46) is
    recorded; without it, `not_determined`. And the user reads cyanrip's own
    sentence first: the line is in the regenerated inventory and is matched as a
    ripper diagnostic, and the class sentence follows it, never replaces it."""
    from platterpus.parsers.cyanrip_log import is_ripper_error_line
    from platterpus.ripper_message_inventory import MESSAGES

    assert release_seq_for_commit("fb28088") == 46
    assert build_speaks_exit_classes(_DOT34) is True
    assert classify_exit(DISC_OR_DRIVE_EXIT, _DOT34) == "disc_or_drive"
    assert "disc or the drive" in explain_failed_exit(
        DISC_OR_DRIVE_EXIT, _DOT34, we_stopped_it=False
    )

    formats = {m.text: m.site for m in MESSAGES}
    assert (
        formats.get(
            "Invalid TOC: track %i starts at LSN %i, not after track %i at LSN %i!"
        )
        == "cyanrip_main.c:679"
    )
    assert is_ripper_error_line(_INVALID_TOC)
    # Non-triviality: the matcher is not matching everything.
    assert not is_ripper_error_line("Track 2 starts at LSN 150")
