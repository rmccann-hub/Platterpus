"""What the ripper's exit status says about who ended the rip.

`ripper_exit` turns an exit status into the sentence a user reads when the ripper
died without printing why. These pin the readings it rests on and the one it must
never make: blaming "something outside" for a stop Platterpus itself caused, or
for a failure the ripper reported in its own words.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from platterpus import ripper_exit


def test_signal_readings_match_both_conventions() -> None:
    """128+N through the wrapper, -N from Popen, and nothing else is a signal."""
    assert ripper_exit.signal_of(137) == 9
    assert ripper_exit.signal_of(143) == 15
    assert ripper_exit.signal_of(-9) == 9
    for not_a_signal in (0, 1, 3, 5, 125, 126, 127, 128, 193, 255, -65):
        assert ripper_exit.signal_of(not_a_signal) is None, not_a_signal
    assert ripper_exit.signal_of(None) is None


def test_the_ripper_own_codes_are_never_read_as_signals() -> None:
    """cyanrip's exit inventory is 0-5 (round 26 lap 1 provider contract §P4).

    None of them may be explained as a death by signal, or a refused argument
    would reach the user as "something on this computer stopped it".
    """
    for own in range(6):
        assert ripper_exit.describe_unrequested_exit(own, we_stopped_it=False) == ""


def test_the_2026_09_24_death_is_described() -> None:
    """The measured case: exit 137, not our signal, 'Trying to quit' printed."""
    text = ripper_exit.describe_unrequested_exit(
        137, we_stopped_it=False, said_quit_notice=True
    )
    assert "stopped from outside Platterpus" in text
    assert "SIGKILL" in text and "exit 137" in text
    assert "Trying to quit" in text
    assert "not the cause" in text and "Start the rip again" in text


def test_a_stop_we_caused_says_nothing() -> None:
    """The false-accusation direction: our own signal is never 'from outside'."""
    for code in (137, 143, -9, -15, 125):
        assert ripper_exit.describe_unrequested_exit(code, we_stopped_it=True) == ""


def test_the_container_tool_error_is_named_as_the_containers() -> None:
    """125 is podman's own error — the code the rig's post-rip probe returned."""
    text = ripper_exit.describe_unrequested_exit(125, we_stopped_it=False)
    assert "podman" in text and "exit 125" in text
    assert "Setup & Updates" in text


def test_a_signal_number_python_cannot_name_still_reads() -> None:
    assert ripper_exit.signal_label(9) == "SIGKILL"
    assert ripper_exit.signal_label(70) == "signal 70"


@given(st.integers(min_value=-(2**31), max_value=2**31), st.booleans(), st.booleans())
def test_never_raises(code: int, we_stopped: bool, notice: bool) -> None:
    """Pure and total: any status in, a string out."""
    result = ripper_exit.describe_unrequested_exit(
        code, we_stopped_it=we_stopped, said_quit_notice=notice
    )
    assert isinstance(result, str)
