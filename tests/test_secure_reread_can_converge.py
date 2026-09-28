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
