# SPDX-License-Identifier: GPL-3.0-only
"""The pre-rip plan: what the app says it is about to do, before it does it.

**What these tests are protecting.** The plan exists because `-Z` is on by
default (2) *and* runs in dynamic mode by default, so a rip that looks
"secure" from Settings reads pass 1 with no `-Z` at all. That is correct
behaviour and a surprising one, and it was only discoverable from the finished
artifact. A plan line that said "-Z: on" and stopped there would reproduce the
original problem in a new place — so the tests below assert the *mode* is named,
not merely the flag.

**The trap these tests are written around:** every assertion here could be
satisfied by a plan that prints a constant. So each one either compares two
different configurations and requires them to *differ*, or names a specific
number the caller passed in. A test that passes against `return ["ok"]` is
decoration.
"""

from __future__ import annotations

from platterpus.rip_plan import (
    MODE_DYNAMIC,
    MODE_OFF,
    MODE_UNIFORM,
    PLAN_PREFIX,
    describe_rip_plan,
    secure_rerip_mode,
)


def _plan(**kwargs: object) -> str:
    """One blob of plan text for the given settings, for substring assertions."""
    base: dict[str, object] = {
        "secure_rerip_matches": 2,
        "secure_rerip_dynamic": True,
    }
    base.update(kwargs)
    return "\n".join(describe_rip_plan(**base))  # type: ignore[arg-type]  # kwargs are typed at each call site


class TestSecureReripMode:
    """The mode function the plan, the worker and the report all agree through."""

    def test_zero_matches_is_off_whatever_dynamic_says(self) -> None:
        # `dynamic` is meaningless without a -Z level to use, and the worker
        # gates on exactly this. Both spellings must land on "off" or the plan
        # would announce a dynamic re-read that can never happen.
        assert secure_rerip_mode(0, True) == MODE_OFF
        assert secure_rerip_mode(0, False) == MODE_OFF

    def test_a_negative_is_off_not_a_crash(self) -> None:
        # The argv builder *refuses* a negative (it is a caller bug, not "auto"),
        # but the plan runs BEFORE that refusal and must still render.
        assert secure_rerip_mode(-1, False) == MODE_OFF

    def test_the_two_on_modes_are_distinguished_by_the_dynamic_flag(self) -> None:
        assert secure_rerip_mode(2, True) == MODE_DYNAMIC
        assert secure_rerip_mode(2, False) == MODE_UNIFORM


class TestTheSecureRereadLine:
    """The line the whole module exists for."""

    def test_dynamic_mode_says_pass_one_carries_no_Z(self) -> None:
        text = _plan(secure_rerip_matches=2, secure_rerip_dynamic=True)
        # Not "-Z is on": the point is that the FIRST pass does not carry it.
        assert "DYNAMIC" in text
        assert "NO -Z" in text
        # And it must name the level, so the reader can check it against the
        # `Invoked as:` line of the targeted re-rip afterwards.
        assert "-Z 2" in text

    def test_uniform_mode_says_every_track(self) -> None:
        text = _plan(secure_rerip_matches=2, secure_rerip_dynamic=False)
        assert "UNIFORM" in text
        assert "every track" in text
        # The dynamic-mode warning must NOT appear — it would be false here.
        assert "NO -Z" not in text

    def test_off_says_read_once(self) -> None:
        text = _plan(secure_rerip_matches=0, secure_rerip_dynamic=True)
        assert "OFF" in text
        assert "read ONCE" in text

    def test_dynamic_mode_names_the_setting_that_changes_it(self) -> None:
        # A plan that describes a surprising default without saying which
        # switch flips it makes the reader hunt. The Settings checkbox is
        # named verbatim so it can be found by searching the dialog.
        text = _plan(secure_rerip_matches=2, secure_rerip_dynamic=True)
        assert "Verify every track with a second read" in text

    def test_the_three_modes_produce_three_different_texts(self) -> None:
        # The non-triviality floor: a constant-returning implementation passes
        # every substring test above in isolation but cannot pass this one.
        off = _plan(secure_rerip_matches=0, secure_rerip_dynamic=False)
        dynamic = _plan(secure_rerip_matches=2, secure_rerip_dynamic=True)
        uniform = _plan(secure_rerip_matches=2, secure_rerip_dynamic=False)
        assert len({off, dynamic, uniform}) == 3


class TestTheOtherFlags:
    def test_the_ladder_says_pass_one_sends_no_S(self) -> None:
        text = _plan(read_speed_mode="auto_ladder", read_speed=0)
        assert "NO \n-S" in text or "NO -S" in text

    def test_a_fixed_speed_names_the_number_it_was_given(self) -> None:
        assert "fixed at 8x" in _plan(read_speed_mode="fixed", read_speed=8)

    def test_an_offset_override_is_signed_and_an_absent_one_says_so(self) -> None:
        # `+667` and `667` are different claims to a reader comparing against a
        # log; the sign is the part that matters on a read offset.
        assert "+667 samples" in _plan(read_offset_override=667)
        assert "-30 samples" in _plan(read_offset_override=-30)
        assert "not overridden" in _plan(read_offset_override=None)

    def test_zero_is_a_real_offset_not_an_absent_one(self) -> None:
        # `0` is falsy and is a legitimate read offset. A plan that tested
        # truthiness would render it as "not overridden" — the same class of bug
        # as the `0`/`None` confusions this project has shipped before.
        assert "+0 samples" in _plan(read_offset_override=0)
        assert "not overridden" not in _plan(read_offset_override=0)

    def test_a_track_subset_says_the_rest_is_not_read(self) -> None:
        text = _plan(only_tracks=(3, 5), disc_track_total=14)
        assert "only 3, 5" in text
        assert "NOT read" in text

    def test_a_whole_disc_rip_names_the_toc_count_when_known(self) -> None:
        assert "whole disc (14 on the TOC)" in _plan(disc_track_total=14)
        # …and does not invent one when it is not.
        assert "whole disc" in _plan(disc_track_total=None)
        assert "on the TOC" not in _plan(disc_track_total=None)

    def test_overread_differs_between_on_and_off(self) -> None:
        assert _plan(force_overread=True) != _plan(force_overread=False)


class TestTheFlagsWeNeverSend:
    """Stated positively: 'absent from the plan' and 'we never send it' look the
    same to a reader, and the fork has asked for a `-j` record for laps."""

    def test_minus_N_is_named_as_always_on(self) -> None:
        assert "-N" in _plan()
        assert "ALWAYS disabled" in _plan()

    def test_minus_j_and_minus_x_are_named_as_never_sent(self) -> None:
        text = _plan()
        assert "-j" in text and "-x" in text
        assert "NEVER sent" in text


class TestShape:
    def test_every_line_carries_the_prefix(self) -> None:
        # The live-log widget interleaves these with the ripper's own output;
        # an unprefixed line would read as something cyanrip said.
        lines = describe_rip_plan(secure_rerip_matches=2, secure_rerip_dynamic=True)
        assert lines, "the plan must never be empty"
        assert all(line.startswith(PLAN_PREFIX) for line in lines)

    def test_it_is_pure_enough_to_call_twice(self) -> None:
        first = describe_rip_plan(secure_rerip_matches=2, secure_rerip_dynamic=False)
        second = describe_rip_plan(secure_rerip_matches=2, secure_rerip_dynamic=False)
        assert first == second

    def test_it_renders_something_for_every_mode_without_raising(self) -> None:
        # A floor: at least this many lines, so a future edit that drops half the
        # plan fails rather than quietly shrinking it.
        for matches, dynamic in ((0, False), (2, True), (2, False), (10, False)):
            lines = describe_rip_plan(
                secure_rerip_matches=matches, secure_rerip_dynamic=dynamic
            )
            assert len(lines) >= 9, (matches, dynamic, lines)
