"""A refusal's exit code is the build's own (the 2026-10-20 Full run, section P2).

`.25` exits 64 for `Offset is unset!` (`CRIP_EXIT_USAGE`, the class our round 35
lap 8 S9 asked for), and the acceptance script expected 1. The ripper was right
and the script was stale; the run failed one step in an ARCHIVAL section over it.
These hold the lookup and the script verb that now ask the build.
"""

from __future__ import annotations

import pytest

from platterpus.deps import fork_source
from platterpus.ripper_exit import (
    REFUSED_EXIT_BEFORE_CLASSES,
    REFUSED_EXIT_WITH_CLASSES,
    refusal_exit_code,
)
from platterpus.uiscript import script as script_mod
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner


@pytest.mark.parametrize(
    ("tag", "code"),
    [
        ("platterpus-fork-g5f1d036", 64),  # .25, the first with the classes
        ("platterpus-fork-g5f1d036-dirty", 64),
        ("platterpus-fork-g93afa15", 1),  # .24
        ("platterpus-fork-g891c79e", 1),  # .23, FORK_PIN today
        ("release", 1),  # stock cyanrip 0.9.3
        ("platterpus-fork-g0000000", None),  # a fork commit we cannot place
        ("g1a2b3c4", None),  # a banner we do not recognise
        ("", None),  # no banner read
    ],
)
def test_each_build_has_its_own_refusal_code(tag: str, code: int | None) -> None:
    assert refusal_exit_code(tag) == code


def test_the_codes_are_the_ones_the_contract_states() -> None:
    assert (REFUSED_EXIT_WITH_CLASSES, REFUSED_EXIT_BEFORE_CLASSES) == (64, 1)
    # Non-triviality: the build under review really is placed as .25 or later.
    assert fork_source.release_seq_for_commit(fork_source.PIN_UNDER_REVIEW) == 36


def _runner(tag: str, exit_code: int | None) -> tuple[ScriptRunner, list]:
    runner = ScriptRunner.__new__(ScriptRunner)
    runner._last_cyanrip_argv = ["~/.local/bin/cyanrip", "-N", "-l", "1"]
    runner._last_cyanrip_output = "Offset is unset!"
    runner._last_cyanrip_exit = exit_code
    runner._ripper_build_tag = tag
    recorded: list[tuple[Outcome, str]] = []
    runner._record = lambda step, outcome, detail="": recorded.append((outcome, detail))  # type: ignore[method-assign]
    return runner, recorded


def _expect_refused(tag: str, exit_code: int | None) -> tuple[Outcome, str]:
    runner, recorded = _runner(tag, exit_code)
    runner._do_expect_exit(script_mod.parse("expect-exit refused")[0])
    return recorded[0]


def test_the_2026_10_20_run_passes_with_refused() -> None:
    """The exact case: `.25` exited 64."""
    assert _expect_refused("platterpus-fork-g5f1d036", 64)[0] is Outcome.PASS


def test_refused_still_fails_a_build_that_did_not_refuse() -> None:
    assert _expect_refused("platterpus-fork-g5f1d036", 0)[0] is Outcome.FAIL
    assert _expect_refused("platterpus-fork-g5f1d036", 1)[0] is Outcome.FAIL
    assert _expect_refused("platterpus-fork-g891c79e", 64)[0] is Outcome.FAIL


def test_refused_on_an_unplaceable_build_is_not_determined_never_a_pass() -> None:
    outcome, detail = _expect_refused("g1a2b3c4", 64)
    assert outcome is Outcome.ERROR
    assert "not determined" in detail


def test_the_full_acceptance_script_asks_the_build() -> None:
    from importlib.resources import files

    text = (files("platterpus") / "rig_scripts" / "fullacceptance.txt").read_text(
        encoding="utf-8"
    )
    block = text[text.index("log --- P2. C1") :]
    block = block[: block.index("snapshot afterc1")]
    assert "expect-exit refused" in block
    assert "expect-exit 1" not in block
