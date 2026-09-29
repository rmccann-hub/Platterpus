"""`-Z N` can only converge when `-r` allows N+1 reads — asserted, not assumed.

cyanrip's secure re-read (`-Z N`, `--repeat-rips`) reads a track until the latest
read's checksum equals N of the EARLIER reads, and stops after `-r` whole-track
reads (`cyanrip@faec4a8:src/cyanrip_main.c:997-1012`). So `-Z N` needs N+1
identical reads, `-r` <= N can never converge, and `-r` == N+1 tolerates no read
that disagrees.

The 2026-09-28 Full run found all three consequences in our own surfaces: the
acceptance script ran every secure re-read at `-r 3 -Z 2` (zero tolerance), the
rig check's own reference argv was `-r 3 -Z 3` (impossible), and the Settings
label counted the reads that must agree one short.

This file holds the one predicate every caller shares
(:func:`platterpus.cyanrip_cli.secure_reread_problem`) against two witnesses that
are NOT that predicate: a line-by-line transliteration of cyanrip's loop, and the
read counts the ripper itself printed in committed hardware logs.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from itertools import chain, repeat
from pathlib import Path

import pytest

from platterpus.cyanrip_cli import (
    DEFAULT_MAX_RETRIES,
    highest_convergeable_repeat_rips,
    retries_flag_value,
    secure_reread_problem,
    whole_track_reads_allowed,
)
from platterpus.read_speed_ladder import (
    MAX_SECURE_REREP,
    recovery_secure_rerip_ceiling,
)

REPO = Path(__file__).resolve().parent.parent


def _cyanrip_secure_reread(
    reads: Iterator[int], *, repeat_rips: int, max_retries: int
) -> tuple[bool, int]:
    """cyanrip's whole-track re-read loop, transliterated. ``(converged, reads)``.

    Line for line from `cyanrip@faec4a8:src/cyanrip_main.c:999-1038`:
    ``matches`` counts the EARLIER reads with this read's checksum, then
    ``total_repeats++``, then the convergence test, THEN the limit test, and only
    a read that neither converged nor hit the limit joins ``last_checksums``.
    Deliberately a transliteration rather than a formula: a formula here would be
    a second copy of the predicate under test, and two copies agreeing proves
    nothing about either.
    """
    last_checksums: list[int] = []
    total_repeats = 0
    while True:
        checksum = next(reads)
        matches = sum(1 for earlier in last_checksums if earlier == checksum)
        total_repeats += 1
        if matches >= repeat_rips:
            return True, total_repeats
        if total_repeats >= max_retries:
            return False, total_repeats
        last_checksums.append(checksum)


def test_the_predicate_agrees_with_cyanrips_loop_on_a_perfect_disc() -> None:
    """Every (-r, -Z) pair in range, judged both ways, on reads that all agree.

    A perfect disc is the case that matters: if even identical reads cannot
    converge, the pair is impossible rather than merely demanding.
    """
    checked = 0
    for max_retries in range(0, 16):
        for repeat_rips in range(1, 12):
            converged, _ = _cyanrip_secure_reread(
                repeat(0xABCD1234), repeat_rips=repeat_rips, max_retries=max_retries
            )
            problem = secure_reread_problem(
                repeat_rips=repeat_rips, retries=max_retries
            )
            assert converged == (problem == ""), (max_retries, repeat_rips, problem)
            checked += 1
    # Floor, and the non-triviality clause: both verdicts must actually occur,
    # or agreement could be two functions that both always say "fine".
    assert checked == 16 * 11
    assert secure_reread_problem(repeat_rips=3, retries=3)
    assert not secure_reread_problem(repeat_rips=2, retries=3)


def test_no_r_on_the_argv_means_cyanrips_own_default() -> None:
    """Our builder sends no `-r` for a setting of 0; cyanrip then uses 10.

    `GEN_OPT_ONE(..., retries, "r", 1, 1, 10, ...)` at
    `cyanrip@faec4a8:src/cyanrip_main.c:1593`. A check that read "no -r" as
    "no limit" would pass `-Z 10`, which cannot converge.
    """
    assert DEFAULT_MAX_RETRIES == 10
    assert whole_track_reads_allowed(None) == 10
    assert secure_reread_problem(repeat_rips=9, retries=None) == ""
    problem = secure_reread_problem(repeat_rips=10, retries=None)
    assert "default of 10" in problem
    converged, _ = _cyanrip_secure_reread(
        repeat(1), repeat_rips=10, max_retries=DEFAULT_MAX_RETRIES
    )
    assert converged is False


def test_r_equal_to_n_plus_one_tolerates_no_read_that_disagrees() -> None:
    """Why the acceptance run's `-r 3 -Z 2` was not a fair test of a real disc.

    One disagreeing read, anywhere, and `-Z 2` cannot converge in three reads;
    with the shipped `-r 5` it still can. Each read beyond N+1 is room for one.
    """
    bad_first = chain([0xBAD], repeat(0x600D))
    assert _cyanrip_secure_reread(bad_first, repeat_rips=2, max_retries=3) == (
        False,
        3,
    )
    bad_first = chain([0xBAD], repeat(0x600D))
    assert _cyanrip_secure_reread(bad_first, repeat_rips=2, max_retries=5) == (
        True,
        4,
    )
    # And the converging read need not match the FIRST read at all, which is why
    # the Settings wording says "N+1 identical reads" rather than "N re-reads
    # that match the first".
    two_bad = chain([0xBAD, 0xBAD2], repeat(0x600D))
    assert _cyanrip_secure_reread(two_bad, repeat_rips=2, max_retries=5) == (
        True,
        5,
    )


def test_every_committed_hardware_log_counts_reads_the_way_the_predicate_does() -> None:
    """The ripper's own words, from real rips of a real disc.

    Each committed secure re-read log names its `-r` and `-Z` in `Invoked as:`
    and prints, per track, `converged after N reads` or `did NOT converge after N
    reads (repeat limit hit)`. On a pair where `-r` == Z+1, every converged track
    must say exactly Z+1 and every other one exactly `-r`. Read from the
    artifact, so this pins the ripper's behaviour and not our belief about it.
    """
    logs = sorted(REPO.glob("docs/handshake/artifactsround*/*securereread.log"))
    assert len(logs) >= 2, f"floor: only {len(logs)} secure re-read log(s) found"
    verdicts_checked = 0
    for log in logs:
        text = log.read_text(encoding="utf-8")
        invoked = re.search(r"^Invoked as:.*$", text, re.MULTILINE)
        assert invoked is not None, f"{log.name} has no 'Invoked as:' line"
        r_match = re.search(r"\s-r\s+(?P<r>\d+)\b", invoked.group(0))
        z_match = re.search(r"\s-Z\s+(?P<z>\d+)\b", invoked.group(0))
        assert r_match is not None and z_match is not None, log.name
        r, z = int(r_match.group("r")), int(z_match.group("z"))
        assert secure_reread_problem(repeat_rips=z, retries=r) == ""
        converged = [
            int(n) for n in re.findall(r"Secure re-read:\s+converged after (\d+)", text)
        ]
        failed = [
            int(n)
            for n in re.findall(r"Secure re-read:\s+did NOT converge after (\d+)", text)
        ]
        assert converged, f"{log.name}: no converged track to measure"
        # The minimum is Z+1 on every pair; at -r == Z+1 it is also the maximum.
        assert all(n >= z + 1 for n in converged), (log.name, converged)
        if r == z + 1:
            assert set(converged) == {z + 1}, (log.name, converged)
        assert all(n == r for n in failed), (log.name, failed)
        verdicts_checked += len(converged) + len(failed)
    assert verdicts_checked >= 20, f"only {verdicts_checked} verdicts read"


# --- the recovery re-read's ceiling (read_speed_ladder) ----------------------


def test_the_users_own_z_is_never_lowered_by_the_recovery_ceiling() -> None:
    """Their number is theirs. Refusing an impossible one is the validator's job
    and the chokepoint's; quietly asking for fewer reads would weaken it."""
    for max_retries in (0, 1, 2, 5, 100):
        for chosen in (1, 2, 7, 10):
            assert (
                recovery_secure_rerip_ceiling(
                    secure_rerip_matches=chosen, max_retries=max_retries
                )
                == chosen
            )


@pytest.mark.parametrize(
    ("max_retries", "expected"),
    [
        (0, MAX_SECURE_REREP),  # no -r: cyanrip's 10 allows the whole bound
        (1, 0),  # one read: nothing to compare, no -Z at all
        (2, 1),
        (3, 2),  # the acceptance script's old value: -Z 3 would be doomed
        (4, MAX_SECURE_REREP),
        (5, MAX_SECURE_REREP),  # the shipped default
    ],
)
def test_the_fallback_z_is_capped_at_what_r_lets_converge(
    max_retries: int, expected: int
) -> None:
    ceiling = recovery_secure_rerip_ceiling(
        secure_rerip_matches=0, max_retries=max_retries
    )
    assert ceiling == expected
    assert (
        secure_reread_problem(
            repeat_rips=ceiling, retries=retries_flag_value(max_retries)
        )
        == ""
    )


def test_highest_convergeable_repeat_rips_is_the_boundary_itself() -> None:
    """The ceiling converges and one more does not, for every -r in range."""
    for retries in (None, *range(0, 101)):
        top = highest_convergeable_repeat_rips(retries)
        assert secure_reread_problem(repeat_rips=top, retries=retries) == ""
        assert secure_reread_problem(repeat_rips=top + 1, retries=retries) != ""


def test_retries_flag_value_is_what_the_builder_actually_sends() -> None:
    """The prediction and the command line must be one mapping, measured.

    The validator and the worker both predict the builder's `-r` through
    `retries_flag_value`; this proves the builder agrees, value by value, so a
    change to one cannot leave the other judging a command line nobody runs.
    """
    from platterpus.composition import build_cyanrip_backend

    backend = build_cyanrip_backend("cyanrip")
    for max_retries in range(0, 101):
        argv = backend._build_rip_argv(  # noqa: SLF001 — the real builder, on purpose
            "/dev/sr0",
            unknown=True,
            cover_art="",
            max_retries=max_retries,
            read_offset_override=None,
        )
        sent = int(argv[argv.index("-r") + 1]) if "-r" in argv else None
        assert sent == retries_flag_value(max_retries), max_retries
    # Non-triviality: both shapes occurred.
    assert retries_flag_value(0) is None and retries_flag_value(5) == 5


# --- what the surfaces SAY the numbers mean ----------------------------------


def _settings_source_calls(method: str) -> list[str]:
    """String-literal first arguments of ``<obj>.<method>(...)`` in settings_dialog."""
    import ast

    source = (REPO / "src" / "platterpus" / "ui" / "settings_dialog.py").read_text(
        encoding="utf-8"
    )
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            found.append(node.args[0].value)
    return found


def _retry_tooltips() -> dict[str, str]:
    """The Max retries and secure re-read tooltips, read from the source."""
    import ast

    source = (REPO / "src" / "platterpus" / "ui" / "settings_dialog.py").read_text(
        encoding="utf-8"
    )
    wanted = {"_max_retries_spin": "", "_secure_rerip_spin": ""}
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setToolTip"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr in wanted
            and node.args
        ):
            wanted[node.func.value.attr] = ast.literal_eval(node.args[0])
    assert all(wanted.values()), f"a retry tooltip was not found: {wanted}"
    return wanted


def test_the_validators_retry_labels_are_the_rows_the_dialog_renders() -> None:
    """One label, spelled in two places, held to one string.

    The secure re-read row was renamed on 2026-09-21 and the validator went on
    naming "Max reads to confirm a shaky track" — a control that no longer
    existed — for a week, under a comment claiming every place had been fixed.
    """
    import dataclasses

    from platterpus import settings_validation as sv
    from platterpus.config import Config

    rows = _settings_source_calls("addRow")
    assert len(rows) >= 20, "floor: the row-label extractor found almost nothing"
    assert f"{sv.MAX_RETRIES_LABEL}:" in rows
    assert f"{sv.SECURE_REREP_LABEL}:" in rows
    # And the message the validator actually shows uses it, which is the point.
    issues = sv.validate_config(dataclasses.replace(Config(), secure_rerip_matches=11))
    messages = [i.message for i in issues if i.field == "secure_rerip_matches"]
    assert messages and messages[0].startswith(sv.SECURE_REREP_LABEL), messages


def test_the_label_counts_extra_reads_and_the_tooltips_state_the_arithmetic() -> None:
    """The number on the spin box is N, and cyanrip needs N+1 identical reads.

    "Reads that must agree to trust a track: 2" was one short — the rig logs say
    "converged after 3 reads" at `-Z 2`. Asserted from the shipped defaults and
    cyanrip's own `-r` default, so a changed default makes the prose fail rather
    than quietly go stale.
    """
    from platterpus import settings_validation as sv
    from platterpus.config import Config

    shipped = Config()
    assert sv.SECURE_REREP_LABEL.lower().startswith("extra")
    tooltips = _retry_tooltips()
    secure = tooltips["_secure_rerip_spin"]
    assert "plus one" in secure
    assert (
        f"at {shipped.secure_rerip_matches} (default), "
        f"{shipped.secure_rerip_matches + 1} identical reads"
    ) in secure
    retries = tooltips["_max_retries_spin"]
    # `-r` is ALSO the whole-track ceiling, and 0 is cyanrip's 10, not "none".
    assert "whole track" in retries
    assert f"{shipped.max_retries} (default)" in retries
    assert f"find {shipped.secure_rerip_matches + 1} identical reads" in retries
    assert f"default of {DEFAULT_MAX_RETRIES}" in retries
    assert "no retries" not in retries


def test_the_rip_plan_names_the_read_count_the_ripper_prints() -> None:
    """Against the artifact: the plan's "N identical reads" is the log's count.

    Each committed secure re-read log names its `-Z` and says how many reads a
    converged track took; the fewest is Z+1, whatever `-r` was. The plan for the
    same `-Z` must name that number.
    """
    from platterpus.rip_plan import describe_rip_plan

    logs = sorted(REPO.glob("docs/handshake/artifactsround*/*securereread.log"))
    assert logs, "floor: no committed secure re-read log to compare against"
    for log in logs:
        text = log.read_text(encoding="utf-8")
        z_match = re.search(r"^Invoked as:.*?\s-Z\s+(?P<z>\d+)\b", text, re.MULTILINE)
        assert z_match is not None, log.name
        z = int(z_match.group("z"))
        printed = min(
            int(n) for n in re.findall(r"Secure re-read:\s+converged after (\d+)", text)
        )
        for dynamic in (True, False):
            # THE -Z LINE, not the whole plan: the -r line below it also says
            # "N identical reads", and a first version of this test was
            # satisfied by that line with the -Z line's count reverted
            # (revert_probe: VACUOUS). Only the pair of line and number checks.
            lines = describe_rip_plan(
                secure_rerip_matches=z, secure_rerip_dynamic=dynamic
            )
            z_lines = [line for line in lines if "Secure re-read (-Z):" in line]
            assert len(z_lines) == 1, lines
            assert f"{printed} identical reads" in z_lines[0], (log.name, z_lines)


@pytest.mark.parametrize(
    ("max_retries", "matches", "expected"),
    [
        (5, 2, "room for 2 read(s) that disagree."),
        (3, 2, "room for 0 read(s) that disagree."),  # the Full run's old pair
        (0, 2, "up to 10 times"),  # no -r sent: cyanrip's own default
        (2, 2, "NEVER succeed"),
    ],
)
def test_the_rip_plan_says_how_much_room_the_retry_ceiling_leaves(
    max_retries: int, matches: int, expected: str
) -> None:
    from platterpus.rip_plan import describe_rip_plan

    plan = "\n".join(
        describe_rip_plan(
            secure_rerip_matches=matches,
            secure_rerip_dynamic=True,
            max_retries=max_retries,
        )
    )
    assert expected in plan, plan
    assert "whole-track reads a secure re-read may take" in plan


def test_the_rip_plan_says_nothing_about_room_when_the_re_read_is_off() -> None:
    from platterpus.rip_plan import describe_rip_plan

    plan = "\n".join(
        describe_rip_plan(secure_rerip_matches=0, secure_rerip_dynamic=True)
    )
    assert "room for" not in plan
    assert "Retry ceiling (-r): 5" in plan


def test_the_ladders_reason_names_the_identical_passes_z_needs() -> None:
    """The status line said "re-reading until 2 passes agree (-Z 2)"."""
    from platterpus.read_speed_ladder import FLOOR_SPEED, next_step

    step = next_step(current_speed=FLOOR_SPEED, current_secure_rerip=0)
    assert step is not None and step.secure_rerip_matches == 2
    assert "until 3 passes are identical (-Z 2)" in step.reason
    locked = next_step(current_speed=0, current_secure_rerip=2, speed_locked=True)
    assert locked is not None and locked.secure_rerip_matches == 3
    assert "until 4 passes are identical (-Z 3)" in locked.reason


# --- the input boundary (settings_validation) and what reaches the argv ------


def test_the_validator_refuses_exactly_the_pairs_the_argv_chokepoint_would() -> None:
    """Over the whole Settings range, the two boundaries give one verdict.

    A pair the validator lets through must build; a pair it refuses must be one
    the chokepoint would refuse too. Otherwise Settings would either save a rip
    that fails at the drive, or refuse one that would have worked.
    """
    import dataclasses

    from platterpus import settings_validation as sv
    from platterpus.config import Config

    refused = 0
    for max_retries in range(sv.MAX_RETRIES_MIN, sv.MAX_RETRIES_MAX + 1):
        for matches in range(sv.SECURE_REREP_MIN, sv.SECURE_REREP_MAX + 1):
            config = dataclasses.replace(
                Config(), max_retries=max_retries, secure_rerip_matches=matches
            )
            validator_refuses = any(
                i.is_error() and i.field == "secure_rerip_matches"
                for i in sv.validate_config(config)
            )
            argv_refuses = bool(
                secure_reread_problem(
                    repeat_rips=matches, retries=retries_flag_value(max_retries)
                )
            )
            assert validator_refuses == argv_refuses, (max_retries, matches)
            refused += validator_refuses
    assert refused > 0, "non-triviality: the sweep never met a refused pair"


def test_no_setting_the_validator_accepts_can_send_a_z_that_cannot_converge() -> None:
    """The population, closed: every -Z a rip can send, for every saved pair.

    A rip sends the user's own -Z when they set one, and otherwise only the
    worker's recovery bound (the ladder's escalations and the instability
    auto-fix both ask `recovery_secure_rerip_ceiling`; the ladder never climbs
    past it). So for each pair Settings would save, the highest -Z of either
    kind must converge under the -r that pair sends.
    """
    import dataclasses

    from platterpus import settings_validation as sv
    from platterpus.config import Config

    checked = 0
    for max_retries in range(sv.MAX_RETRIES_MIN, sv.MAX_RETRIES_MAX + 1):
        for matches in range(sv.SECURE_REREP_MIN, sv.SECURE_REREP_MAX + 1):
            config = dataclasses.replace(
                Config(), max_retries=max_retries, secure_rerip_matches=matches
            )
            if sv.errors_only(sv.validate_config(config)):
                continue
            highest = recovery_secure_rerip_ceiling(
                secure_rerip_matches=matches, max_retries=max_retries
            )
            retries = retries_flag_value(max_retries)
            assert secure_reread_problem(repeat_rips=highest, retries=retries) == ""
            checked += 1
    assert checked > 900, f"only {checked} accepted pairs checked"


#: Names the secure re-read row has had, newest last. A surface that tells a
#: person to change a setting must name the row they will find.
_RETIRED_SECURE_REREAD_LABELS: tuple[str, ...] = (
    "Max reads to confirm a shaky track",  # until 2026-09-21
    "Reads that must agree to trust a track",  # 2026-09-21 to 2026-09-28, one short
)


def test_no_instruction_a_user_follows_names_a_retired_row_label() -> None:
    """The instruction surfaces, not the history.

    Found 2026-09-28 by grep, after the label and tooltip were fixed: the README
    still said *re-read until "Max reads to confirm a shaky track" reads agree*,
    the test plan told the rig to set **Max reads to confirm a shaky track → 2**,
    and the CTDB repair runbook pointed at the same missing row. Deliberately
    scoped to what a person follows — the README, the two runbooks, the User
    Guide and the dialog's own on-screen strings — because comments and the
    parity doc NAME the old labels on purpose, as the record of the rename.
    """
    from platterpus import settings_validation as sv
    from platterpus.help_content import USER_GUIDE

    surfaces: dict[str, str] = {
        "README.md": (REPO / "README.md").read_text(encoding="utf-8"),
        "docs/test-plan.md": (REPO / "docs/test-plan.md").read_text(encoding="utf-8"),
        "docs/manual-ctdb-repair.md": (REPO / "docs/manual-ctdb-repair.md").read_text(
            encoding="utf-8"
        ),
        "help_content.USER_GUIDE": USER_GUIDE,
        "settings_dialog labels": "\n".join(_settings_source_calls("addRow")),
        "settings_dialog tooltips": "\n".join(_settings_source_calls("setToolTip")),
    }
    stale = [
        f"{where}: {label!r}"
        for where, text in surfaces.items()
        for label in _RETIRED_SECURE_REREAD_LABELS
        if label.lower() in text.lower()
    ]
    assert not stale, "these surfaces still name a retired row: " + "; ".join(stale)
    # Non-triviality: the sweep read real text, and the CURRENT label is where a
    # reader would look for it. An emptied surface would pass the check above.
    for where in ("README.md", "help_content.USER_GUIDE", "settings_dialog labels"):
        assert sv.SECURE_REREP_LABEL.lower() in surfaces[where].lower(), where


# --- the argv chokepoint (adapters/cyanrip_backend.py) -----------------------


@pytest.mark.parametrize(
    ("argv_tail", "names"),
    [
        # The rig check's own reference argv until 2026-09-28.
        (["-r", "3", "-Z", "3"], ("-Z 3", "-r 3")),
        (["-r", "2", "-Z", "2"], ("-Z 2", "-r 2")),
        (["-r", "1", "-Z", "1"], ("-Z 1", "-r 1")),
        (["-r", "0", "-Z", "1"], ("-Z 1", "-r 0")),
        # No -r: cyanrip's own 10, and -Z 10 needs 11 reads.
        (["-Z", "10"], ("-Z 10", "default of 10")),
        # A repeated -r: cyanrip applies the LAST (genopt.h:582), so a harmless
        # first one must not hide an impossible second one.
        (["-r", "5", "-Z", "2", "-r", "2"], ("-Z 2", "-r 2")),
    ],
)
def test_the_chokepoint_refuses_a_z_that_r_can_never_satisfy(
    argv_tail: list[str], names: tuple[str, ...]
) -> None:
    """Through the one function every route to the ripper passes, not the helper.

    Each value here is inside its own range, which is exactly why the range check
    let the pair through: the defect is the combination.
    """
    from platterpus.adapters.cyanrip_backend import assert_metadata_lookup_disabled
    from platterpus.adapters.rip_backend import RipError

    with pytest.raises(RipError) as excinfo:
        assert_metadata_lookup_disabled(["cyanrip", "-N", *argv_tail])
    message = str(excinfo.value)
    for name in names:
        assert name in message, f"the refusal does not name {name!r}: {message}"


def test_the_chokepoint_accepts_every_pair_that_can_converge() -> None:
    """The floor: a guard that refused every -Z would pass the test above."""
    from platterpus.adapters.cyanrip_backend import assert_metadata_lookup_disabled

    accepted = 0
    for argv_tail in (
        ["-r", "3", "-Z", "2"],  # the Full run's pair: zero tolerance, but possible
        ["-r", "5", "-Z", "2"],  # the shipped defaults
        ["-r", "2", "-Z", "1"],
        ["-Z", "9"],  # no -r: cyanrip's 10 allows ten reads
        ["-r", "1"],  # no -Z at all: nothing to converge
        ["-r", "2", "-Z", "5", "-Z", "1"],  # the LAST -Z is the one applied
    ):
        assert_metadata_lookup_disabled(["cyanrip", "-N", *argv_tail])
        accepted += 1
    assert accepted == 6


def test_the_builder_refuses_exactly_the_settings_pairs_the_predicate_does() -> None:
    """The relation, over the whole Settings range: settings -> argv -> verdict.

    `_build_rip_argv` ends at the chokepoint, so a pair the predicate calls
    impossible must raise there, and every other pair must build. Checked for
    every (Max retries, secure re-read) the validator's ranges allow, so no pair
    can reach cyanrip that the predicate would have refused.
    """
    from platterpus import settings_validation as sv
    from platterpus.adapters.rip_backend import RipError
    from platterpus.composition import build_cyanrip_backend

    backend = build_cyanrip_backend("cyanrip")
    refused = built = 0
    for max_retries in range(sv.MAX_RETRIES_MIN, sv.MAX_RETRIES_MAX + 1):
        for matches in range(sv.SECURE_REREP_MIN, sv.SECURE_REREP_MAX + 1):
            impossible = bool(
                secure_reread_problem(
                    repeat_rips=matches, retries=retries_flag_value(max_retries)
                )
            )
            try:
                backend._build_rip_argv(  # noqa: SLF001 — the real builder, on purpose
                    "/dev/sr0",
                    unknown=True,
                    cover_art="",
                    max_retries=max_retries,
                    read_offset_override=None,
                    secure_rerip_matches=matches,
                )
            except RipError:
                assert impossible, (max_retries, matches)
                refused += 1
            else:
                assert not impossible, (max_retries, matches)
                built += 1
    # Non-triviality: both outcomes occurred, and the refusals are the small
    # corner (-r 0..10 against -Z up to 10), not the whole table.
    assert refused > 0 and built > refused
