"""Tests for platterpus.disc_probe_retry — the bounded automatic retry of a
failed disc read (the rig report of 2026-09-28: "sometimes I have to open the
drive and close it again and restart the app"). Pure: no window, no drive."""

from __future__ import annotations

from dataclasses import replace

from hypothesis import example, given, settings
from hypothesis import strategies as st

from platterpus import disc_probe_retry as dpr
from platterpus.disc_probe_retry import (
    AUTO_RETRY_LIMIT,
    BLOCKED_BY_BUDGET,
    BLOCKED_BY_FAILURE_KIND,
    BLOCKED_BY_FREEING,
    BLOCKED_BY_NEWER_REQUEST,
    BLOCKED_BY_NO_DISC,
    BLOCKED_BY_OTHER_DRIVE,
    BLOCKED_BY_RIP,
    BLOCKED_BY_SCAN,
    FREE_WAIT_CHECKS,
    GIVE_UP,
    READ_NOW,
    RETRY_LATER,
    STAND_DOWN,
    DiscReadRetries,
    RetryConditions,
    retry_blocker,
)
from platterpus.drive_media import DISC, EMPTY, NOT_READY, OPEN, UNAVAILABLE

_READY = RetryConditions(
    rip_running=False,
    scan_running=False,
    newest_request=True,
    same_drive=True,
    drive_being_freed=False,
    media_status=DISC,
)

_COLD = "cyanrip timed out after 120s"
_CONTAINER = (
    'cyanrip failed (exit 125). It said: Error: unable to start container "2abb88"'
)


def _friendly(message: str) -> str:
    """Stand-in for `friendly_disc_scan_error`'s passthrough of an unknown error."""
    return f"error text for: {message}"


def test_a_first_failure_is_retried_later_and_says_so() -> None:
    retries = DiscReadRetries()
    retries.new_request()
    decision = retries.after_failure("/dev/sr0", _CONTAINER, "x", _READY)
    assert decision.action == RETRY_LATER
    assert decision.error_text == ""
    # The panel says what the app is doing AND keeps the ripper's own words.
    assert "trying again automatically" in decision.retrying_text
    assert "retry 1 of 2" in decision.retrying_text
    assert _CONTAINER in decision.retrying_text
    assert retries.pending is not None and retries.pending.device == "/dev/sr0"


def test_the_retries_are_bounded_and_the_last_message_says_what_to_do() -> None:
    retries = DiscReadRetries()
    retries.new_request()
    actions = []
    for _ in range(AUTO_RETRY_LIMIT + 1):
        decision = retries.after_failure("/dev/sr0", _CONTAINER, "boom", _READY)
        actions.append(decision.action)
        if decision.action == RETRY_LATER:
            assert retries.when_due(_READY, _friendly).action == READ_NOW
    assert actions == [RETRY_LATER] * AUTO_RETRY_LIMIT + [GIVE_UP]
    assert BLOCKED_BY_BUDGET in decision.log_line
    assert "Rescan disc" in decision.error_text
    assert f"Read {AUTO_RETRY_LIMIT + 1} times" in decision.error_text


def test_a_new_request_gets_a_fresh_budget_and_drops_a_pending_retry() -> None:
    retries = DiscReadRetries()
    retries.new_request()
    for _ in range(AUTO_RETRY_LIMIT):
        retries.after_failure("/dev/sr0", _COLD, "x", _READY)
        retries.when_due(_READY, _friendly)
    retries.after_failure("/dev/sr0", _COLD, "x", _READY)  # budget spent: gives up
    retries.new_request()  # a Rescan
    assert retries.retries_used == 0 and retries.pending is None
    assert retries.after_failure("/dev/sr0", _COLD, "x", _READY).action == RETRY_LATER


def test_a_missing_ripper_is_not_retried_and_no_rescan_is_advised() -> None:
    retries = DiscReadRetries()
    retries.new_request()
    message = "cyanrip binary not found at /home/u/.local/bin/cyanrip"
    decision = retries.after_failure("/dev/sr0", message, message, _READY)
    assert decision.action == GIVE_UP
    assert BLOCKED_BY_FAILURE_KIND in decision.log_line
    assert "Rescan" not in decision.error_text
    assert retries.pending is None


def test_an_empty_or_open_tray_is_not_retried_and_the_user_is_told_to_insert() -> None:
    for tray in (EMPTY, OPEN):
        retries = DiscReadRetries()
        retries.new_request()
        conditions = replace(_READY, media_status=tray)
        decision = retries.after_failure("/dev/sr0", _CONTAINER, "x", conditions)
        assert decision.action == GIVE_UP, tray
        assert "Insert one and it is read automatically" in decision.error_text


def test_a_drive_that_cannot_say_or_is_spinning_up_is_retried() -> None:
    # "unavailable" is no information, and "not ready" is a disc becoming ready:
    # both are exactly when a second read helps.
    for status in (UNAVAILABLE, NOT_READY):
        retries = DiscReadRetries()
        retries.new_request()
        conditions = replace(_READY, media_status=status)
        assert (
            retries.after_failure("/dev/sr0", _COLD, "x", conditions).action
            == RETRY_LATER
        )


def test_a_due_retry_waits_for_the_drive_to_be_freed_and_the_wait_is_bounded() -> None:
    retries = DiscReadRetries()
    retries.new_request()
    freeing = replace(_READY, drive_being_freed=True)
    # Scheduling is not refused by the free: this failure started it.
    assert retries.after_failure("/dev/sr0", _COLD, "x", freeing).action == RETRY_LATER
    waits = 0
    while True:
        decision = retries.when_due(freeing, _friendly)
        if decision.action != RETRY_LATER:
            break
        waits += 1
        assert waits <= FREE_WAIT_CHECKS, "the wait for the free is unbounded"
    assert waits == FREE_WAIT_CHECKS
    assert decision.action == GIVE_UP
    assert BLOCKED_BY_FREEING in decision.error_text


def test_a_due_retry_reads_once_the_drive_is_free() -> None:
    retries = DiscReadRetries()
    retries.new_request()
    retries.after_failure("/dev/sr0", _COLD, "x", _READY)
    freeing = replace(_READY, drive_being_freed=True)
    assert retries.when_due(freeing, _friendly).action == RETRY_LATER
    decision = retries.when_due(_READY, _friendly)
    assert decision.action == READ_NOW and decision.device == "/dev/sr0"
    assert retries.pending is None


def test_a_due_retry_stands_down_when_a_newer_read_owns_the_panel() -> None:
    for condition in (
        {"newest_request": False},
        {"scan_running": True},
        {"same_drive": False},
    ):
        retries = DiscReadRetries()
        retries.new_request()
        retries.after_failure("/dev/sr0", _COLD, "x", _READY)
        decision = retries.when_due(replace(_READY, **condition), _friendly)
        assert decision.action == STAND_DOWN, condition
        # A newer read owns the panel: nothing may be written to it.
        assert decision.error_text == "" and decision.retrying_text == "", condition


def test_a_due_retry_gives_up_visibly_when_a_rip_or_an_empty_tray_stops_it() -> None:
    for condition, reason in (
        ({"rip_running": True}, BLOCKED_BY_RIP),
        ({"media_status": OPEN}, BLOCKED_BY_NO_DISC),
    ):
        retries = DiscReadRetries()
        retries.new_request()
        retries.after_failure("/dev/sr0", _COLD, "x", _READY)
        decision = retries.when_due(replace(_READY, **condition), _friendly)
        assert decision.action == GIVE_UP, condition
        # The panel said "trying again…" and must not go on saying it.
        assert decision.error_text.startswith(_friendly(_COLD)), decision.error_text
        assert reason in decision.log_line


def test_a_timer_with_nothing_pending_does_nothing() -> None:
    retries = DiscReadRetries()
    assert retries.when_due(_READY, _friendly).action == STAND_DOWN


def test_the_blocker_names_the_first_condition_that_refused() -> None:
    cases = [
        ({"rip_running": True}, BLOCKED_BY_RIP),
        ({"scan_running": True}, BLOCKED_BY_SCAN),
        ({"newest_request": False}, BLOCKED_BY_NEWER_REQUEST),
        ({"same_drive": False}, BLOCKED_BY_OTHER_DRIVE),
        ({"drive_being_freed": True}, BLOCKED_BY_FREEING),
        ({"media_status": EMPTY}, BLOCKED_BY_NO_DISC),
        ({}, ""),
    ]
    for change, expected in cases:
        assert retry_blocker(replace(_READY, **change)) == expected, change
    # A rip outranks everything: it holds the drive.
    everything = replace(
        _READY,
        rip_running=True,
        scan_running=True,
        newest_request=False,
        same_drive=False,
        drive_being_freed=True,
        media_status=EMPTY,
    )
    assert retry_blocker(everything) == BLOCKED_BY_RIP


_ANY_CONDITIONS = st.builds(
    RetryConditions,
    rip_running=st.booleans(),
    scan_running=st.booleans(),
    newest_request=st.booleans(),
    same_drive=st.booleans(),
    drive_being_freed=st.booleans(),
    media_status=st.sampled_from([DISC, EMPTY, OPEN, NOT_READY, UNAVAILABLE]),
)
# Weighted towards "ready": uniformly random conditions refuse most of the time,
# and a first version drawn that way passed with the budget check deleted (the
# revert probe said so), because it almost never reached a third retry.
_CONDITIONS = st.one_of(st.just(_READY), st.just(_READY), _ANY_CONDITIONS)
_FAIL = (True, _READY, _COLD)
_DUE = (False, _READY, "")


@settings(max_examples=200)
@example(steps=[_FAIL, _DUE, _FAIL, _DUE, _FAIL, _DUE, _FAIL, _DUE])
@given(
    st.lists(st.tuples(st.booleans(), _CONDITIONS, st.text(max_size=40)), max_size=60)
)
def test_one_request_never_reads_more_than_the_limit_allows(
    steps: list[tuple[bool, RetryConditions, str]],
) -> None:
    """However failures and timer firings interleave, one request gets at most
    AUTO_RETRY_LIMIT automatic re-reads — the bound is the point of the design,
    and a retry loop is the failure a bounded retry exists to rule out."""
    retries = DiscReadRetries()
    retries.new_request()
    reads = 0
    for is_failure, conditions, message in steps:
        if is_failure:
            retries.after_failure("/dev/sr0", message, _friendly(message), conditions)
        else:
            decision = retries.when_due(conditions, _friendly)
            reads += decision.action == READ_NOW
    assert reads <= AUTO_RETRY_LIMIT
    assert retries.retries_used <= AUTO_RETRY_LIMIT


def test_the_limit_is_reachable() -> None:
    """Non-triviality for the property above: the bound is met, not just obeyed."""
    retries = DiscReadRetries()
    retries.new_request()
    reads = 0
    for _ in range(10):
        retries.after_failure("/dev/sr0", _COLD, "x", _READY)
        reads += retries.when_due(_READY, _friendly).action == READ_NOW
    assert reads == AUTO_RETRY_LIMIT
    assert dpr.AUTO_RETRY_LIMIT >= 1
