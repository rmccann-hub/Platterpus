"""The in-app script language: parser, vocabulary, and transcript.

**What this feature is for.** The maintainer tests on hardware CI cannot reach,
and the cases that matter most are the ones where *nothing visible happens* — on
2026-08-06 he sat in front of a modal release picker for thirty seconds and
reported "nothing happened that i can see", with no artifact able to say whether
the dialog had been on screen. So: a pasteable batch that drives the real GUI
unattended and hands back a transcript.

**Why the parser gets this much attention.** A script is external input, typed by
a human or copied out of a chat window. `CLAUDE.md`'s rule is literal — validate
every input, visibly — and the specific failure to avoid is a parser that raises
on line 12 of a 60-line batch and destroys the other 59 results. For an
unattended run that is the whole session.
"""

from __future__ import annotations

import pytest

from platterpus.uiscript import report as report_mod
from platterpus.uiscript import script as script_mod
from platterpus.uiscript import verbs as verbs_mod
from platterpus.uiscript.report import Outcome, RunReport, StepRecord

# --- The vocabulary is a closed set --------------------------------------


def test_the_vocabulary_is_not_empty_and_every_entry_is_coherent() -> None:
    assert len(verbs_mod.VERBS) >= 15  # floor
    for name, verb in verbs_mod.VERBS.items():
        assert name == name.lower(), f"{name} is not lower-case"
        assert verb.name == name
        assert verb.help.startswith(name), f"{name}'s help must start with the verb"
        assert verb.min_args >= 0
        if verb.max_args is not None:
            assert verb.max_args >= verb.min_args


def test_exactly_the_intended_verbs_are_unsafe() -> None:
    """The escape hatch is two verbs, and a third appearing is a review event.

    This is the security boundary; it must not widen because somebody needed
    something quickly. If a new unsafe verb is genuinely wanted, this list is the
    deliberate edit that admits it.
    """
    unsafe = {name for name, verb in verbs_mod.VERBS.items() if verb.unsafe}
    assert unsafe == {"eval", "call"}


def test_no_destructive_verb_exists() -> None:
    """Named, not merely absent.

    An unattended batch must not be able to eject a disc, delete a rip, run the
    uninstaller or install a dependency — the failure mode of an unattended
    destructive action is unbounded. Asserting the *words* are absent is crude
    and it is exactly the check that fails loudly if someone adds one.
    """
    forbidden = {
        "eject",
        "delete",
        "remove",
        "uninstall",
        "install",
        "reset",
        "wipe",
        "format",
        "quit",
        "exit",
    }
    assert not (forbidden & set(verbs_mod.VERBS)), "a destructive verb was added"


def test_the_reference_is_rendered_from_the_table_not_hand_written() -> None:
    text = verbs_mod.verb_reference()
    for name in verbs_mod.VERBS:
        assert name in text, f"{name} missing from the reference"
    assert "unsafe opt-in" in text  # the hatch is disclosed, not hidden
    for target in verbs_mod.OPENABLE:
        assert target in text


# --- Parsing --------------------------------------------------------------


def test_a_clean_script_parses_to_the_steps_you_typed() -> None:
    steps = script_mod.parse("# a comment\n\nlog hello there\nopen settings\ncancel\n")
    assert [s.verb for s in steps] == ["log", "open", "cancel"]
    assert all(s.ok for s in steps)
    # Blank and comment-only lines produce NO step: a transcript reading
    # "line 2: blank, OK" helps nobody.
    assert [s.line_no for s in steps] == [3, 4, 5]


def test_quoted_values_survive_spaces_em_dashes_and_brackets() -> None:
    """The real labels, which is the whole reason quoting exists here."""
    steps = script_mod.parse(
        'expect "Output format" "FLAC — Lossless Archival Master [Recommended]"'
    )
    assert len(steps) == 1
    assert steps[0].args == (
        "Output format",
        "FLAC — Lossless Archival Master [Recommended]",
    )


def test_a_hash_inside_a_quoted_value_is_not_a_comment() -> None:
    """Album titles contain '#', and this language exists to set album titles.

    A naive `line.split("#")` would silently truncate the value — silently, which
    is the worst kind: the rip would land in a folder named differently from what
    the script said, and the transcript would agree with itself.
    """
    steps = script_mod.parse('album "Greatest Hits #2 [run #3]"  # trailing comment')
    assert len(steps) == 1
    assert steps[0].args == ("Greatest Hits #2 [run #3]",)


def test_an_unknown_verb_is_reported_against_its_own_line_and_the_rest_still_parses() -> (
    None
):
    """The property that makes an unattended batch worth running."""
    steps = script_mod.parse("log one\nbogus thing\nlog two\n")
    assert len(steps) == 3
    assert steps[0].ok and steps[2].ok
    assert not steps[1].ok
    assert "bogus" in steps[1].error
    assert steps[1].line_no == 2


def test_an_arity_mistake_is_reported_not_raised() -> None:
    steps = script_mod.parse("wait\n")
    assert not steps[0].ok
    assert "at least 1" in steps[0].error


def test_an_unterminated_quote_is_attributed_to_its_line() -> None:
    steps = script_mod.parse('log fine\nalbum "never closed\nlog also fine\n')
    assert steps[0].ok
    assert not steps[1].ok and "unterminated quote" in steps[1].error
    assert steps[2].ok, "one bad line must not poison the rest of the batch"


def test_absurd_input_is_bounded_and_says_so() -> None:
    long_line = "log " + "x" * (script_mod.MAX_LINE_CHARS + 10)
    steps = script_mod.parse(long_line)
    assert not steps[0].ok and "limit" in steps[0].error

    many = "\n".join(["log x"] * (script_mod.MAX_LINES + 50))
    steps = script_mod.parse(many)
    assert len(steps) == script_mod.MAX_LINES + 1
    # Never a silent truncation — the marker is the last step and says so.
    assert "not parsed" in steps[-1].error


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n\n\n",
        "#",
        '"',
        '""',
        "   ",
        "log",
        "\\",
        "set = =",
        "\x00",
        "eval " + "(" * 200,
    ],
)
def test_the_parser_never_raises_on_any_input(text: str) -> None:
    """It is fed pasted text; a traceback here loses the whole run."""
    script_mod.parse(text)


def test_unsafe_use_is_detectable_before_the_run_starts() -> None:
    """Refuse the batch up front, not at line 40 of 60.

    An unattended run that dies two-thirds of the way through is worse than one
    that never started, because the partial transcript looks like a result.
    """
    assert not script_mod.uses_unsafe(script_mod.parse("log hi\nopen settings"))
    assert script_mod.uses_unsafe(script_mod.parse("log hi\neval window.width()"))


# --- The transcript -------------------------------------------------------


def _report(*outcomes: Outcome) -> RunReport:
    return RunReport(
        started_at="2026-08-06T01:00:00Z",
        app_version="0.6.4b12",
        steps=[
            StepRecord(i + 1, f"step {i + 1}", outcome)
            for i, outcome in enumerate(outcomes)
        ],
    )


def test_counts_include_every_category_even_at_zero() -> None:
    """ "0 failures" is a measurement; an absent key reads as "not checked"."""
    tally = _report(Outcome.PASS).counts()
    assert set(tally) == {o.value for o in Outcome}
    assert tally["pass"] == 1 and tally["fail"] == 0


def test_a_run_is_only_ok_when_everything_passed() -> None:
    assert _report(Outcome.PASS, Outcome.PASS).ok
    assert not _report(Outcome.PASS, Outcome.FAIL).ok
    assert not _report(Outcome.PASS, Outcome.ERROR).ok
    assert not _report(Outcome.PASS, Outcome.BLOCKED).ok


def test_a_run_that_ended_early_is_never_ok_however_its_steps_went() -> None:
    """A transcript that stops without a verdict reads like one that passed."""
    rep = _report(Outcome.PASS, Outcome.PASS)
    rep.ended_reason = "aborted at line 2"
    assert not rep.ok
    assert "ENDED EARLY" in report_mod.render(rep)


def test_an_unsafe_run_says_so_at_the_top_of_its_own_transcript() -> None:
    """Evidence produced with arbitrary code in play is not the same evidence.

    At the top, because a reader must not have to scroll to find it out.
    """
    rep = _report(Outcome.PASS)
    rep.used_unsafe = True
    rendered = report_mod.render(rep)
    assert "UNSAFE" in rendered
    header_end = rendered.index("[")  # first step line
    assert "UNSAFE" in rendered[:header_end], "the warning is below the first step"


def test_the_transcript_shows_failures_with_their_detail() -> None:
    rep = _report(Outcome.PASS)
    rep.steps.append(
        StepRecord(2, 'expect "Goal" "X"', Outcome.FAIL, detail="found 'Y' instead")
    )
    rendered = report_mod.render(rep)
    assert "FAIL" in rendered
    assert "found 'Y' instead" in rendered
    assert "see failures above" in rendered


def test_the_serialised_shape_carries_everything_the_text_does() -> None:
    """It is embedded in the rip JSON, where nothing else explains the run."""
    rep = _report(Outcome.PASS, Outcome.FAIL)
    rep.ended_reason = "stopped by the user"
    rep.used_unsafe = True
    rep.artifact_dir = "/tmp/run-1"
    data = rep.as_dict()
    assert data["ended_reason"] == "stopped by the user"
    assert data["used_unsafe_verbs"] is True
    assert data["artifact_dir"] == "/tmp/run-1"
    assert data["ok"] is False
    assert data["counts"]["fail"] == 1
    assert len(data["steps"]) == 2
    assert data["steps"][0]["outcome"] == "pass"


# --- The names the runner will resolve at RUN time ------------------------


def test_every_openable_dialog_names_a_real_method(qapp) -> None:
    """A typo here fails in front of an unattended batch, which is the worst moment.

    Not hypothetical: five of these seven were guessed wrong on the first attempt
    — `open_settings_dialog`, `open_about_dialog`, `open_diagnostics_dialog`,
    `open_user_guide`, `open_drive_setup_dialog`, not one of which exists. They
    were caught by running this check, not by reading the code.
    """
    from platterpus.ui.main_window import MainWindow

    assert len(verbs_mod.OPENABLE) >= 5  # floor
    missing = [
        f"{target} -> {method}"
        for target, method in verbs_mod.OPENABLE.items()
        if not hasattr(MainWindow, method)
    ]
    assert not missing, f"OPENABLE names methods MainWindow does not have: {missing}"


# --- The straight passthrough is filtered ---------------------------------
#
# The maintainer's question, which found a bug: "does all pass through platterpus
# to cyanrip (filtered), or do any do a straight pass to cyanrip bypassing
# platterpus? ... if there is a straight pass through there should likely be a
# sanitation check for the values."
#
# The answer was the second. The app's own rip argv goes through
# `assert_metadata_lookup_disabled` at cyanrip_backend.py:279 -- ONE chokepoint --
# and the `cyanrip` script verb bypassed it entirely as first written.


def test_a_scripted_rip_without_dash_N_is_refused() -> None:
    """The failure this prevents is a hang, not a wrong result.

    Without `-N`, cyanrip runs its own MusicBrainz lookup, which can block on an
    interactive prompt with no terminal attached. An unattended batch would hang
    forever — the exact thing this feature exists to prevent.
    """
    refusal = script_mod.sanitise_cyanrip_args(["-d", "/dev/sr0", "-o", "flac"])
    assert refusal is not None
    assert "-N" in refusal


def test_the_guard_is_delegated_not_restated() -> None:
    """The refusal text comes from the real chokepoint, not a copy of its rule.

    A second implementation of a safety check is a second thing to drift; if the
    chokepoint's wording or logic changes, this follows automatically.
    """
    from platterpus.adapters.cyanrip_backend import (
        RipError,
        assert_metadata_lookup_disabled,
    )

    try:
        assert_metadata_lookup_disabled(["cyanrip", "-o", "flac"])
        raise AssertionError("the chokepoint should have refused this")
    except RipError as exc:
        canonical = str(exc)
    assert script_mod.sanitise_cyanrip_args(["-o", "flac"]) == canonical


def test_only_print_and_exit_flags_are_exempt_from_the_N_requirement() -> None:
    """`--version` and `--help` print and exit; demanding `-N` of them would be
    a rule applied past its own reason.

    This test previously also asserted that ``-x`` was exempt, and its passing is
    what made the wrong exemption look verified for a whole release. It was
    measuring my belief about the flag rather than the fork's contract: their
    published provider contract lists ``-x`` and ``-j`` under **Ripping options**
    (rows 40 and 42 of the round-7 lap-39 artifact), not under the metadata
    options where the non-ripping ``-I``/``-J`` live. A list checked against
    itself is consistent, not verified.
    """
    for probe in (["--version"], ["-v"], ["--help"], ["-h"]):
        assert script_mod.sanitise_cyanrip_args(probe) is None, probe


def test_a_rip_modifier_is_not_a_probe_even_though_it_probes() -> None:
    """``-x`` measures the drive cache *before ripping*; ``-j`` records a rip.

    Bare, they are rips with cyanrip's own MusicBrainz lookup ENABLED, which can
    block on an interactive prompt with no terminal attached — the exact
    unattended hang this sanitiser exists to prevent. The fork's own probe
    invocation carries ``-N``, and so does every ``-x`` call site in this repo.
    """
    for rip_modifier in (["-x"], ["--cache-probe"], ["-j", "/tmp/diag.json"]):
        refusal = script_mod.sanitise_cyanrip_args(rip_modifier)
        assert refusal is not None, f"{rip_modifier} was waved through as a probe"
        assert "-N" in refusal
    # With -N they are fine — the flag is not banned, the missing guard was.
    assert (
        script_mod.sanitise_cyanrip_args(["-x", "-D", "/tmp/s", "-o", "flac", "-N"])
        is None
    )
    assert (
        script_mod.sanitise_cyanrip_args(
            ["-d", "/dev/sr0", "-I", "-N", "-A", "-U", "-x"]
        )
        is None
    )


def test_one_probe_flag_does_not_exempt_a_whole_rip_command_line() -> None:
    """The exemption is a property of the ENTIRE argv, not of any one argument.

    Written as ``any(...)`` it meant a single ``-v`` anywhere waved through
    everything after it, so ``cyanrip -v -d /dev/sr0 -o flac`` — a full rip of
    the inserted disc with metadata lookup on — was classified as a probe.
    """
    refusal = script_mod.sanitise_cyanrip_args(["-v", "-d", "/dev/sr0", "-o", "flac"])
    assert refusal is not None, "a probe flag smuggled a whole rip past the guard"
    assert "-N" in refusal


def test_an_empty_argv_is_not_a_probe() -> None:
    """``all()`` over an empty sequence is True, which would have made a bare
    ``cyanrip`` with no arguments the most exempt invocation of all."""
    assert script_mod.sanitise_cyanrip_args([]) is not None


def test_a_newline_in_an_argument_is_refused_as_log_forgery() -> None:
    """Not shell injection — we never use a shell. Log forgery.

    cyanrip writes its argv into an archival log, and a newline could fabricate a
    second line in a document whose entire purpose is being trustworthy evidence.
    """
    refusal = script_mod.sanitise_cyanrip_args(
        ["-N", "-a", "album=x\nInvoked as: lies"]
    )
    assert refusal is not None
    assert "newline" in refusal


def test_a_malformed_consumer_tag_is_refused_by_the_same_delegation() -> None:
    refusal = script_mod.sanitise_cyanrip_args(["-N", "--consumer", "bad tag"])
    assert refusal is not None
    assert "whitespace" in refusal


def test_absurd_argv_is_bounded() -> None:
    assert script_mod.sanitise_cyanrip_args(["-N"] + ["-x"] * 100) is not None
    assert script_mod.sanitise_cyanrip_args(["-N", "x" * 5000]) is not None


def test_a_well_formed_rip_argv_is_allowed() -> None:
    """The floor: a sanitiser that refused everything would pass every test above."""
    assert (
        script_mod.sanitise_cyanrip_args(["-N", "-d", "/dev/sr0", "-o", "flac"]) is None
    )


def test_the_verb_table_and_the_runner_agree_about_what_works() -> None:
    """The sweep that would have caught the gap the moment it opened.

    The table advertises 25 verbs; the runner implemented 12, and the other 13
    parsed, arity-checked, passed the unsafe gate and then failed at RUN time.
    That is `docs/testing.md` §5.p — *a documented capability is not a
    capability* — and for an unattended batch it means dying mid-run against a
    reference that promised the command would work.

    Asserted in BOTH directions: a verb flagged implemented must have a handler,
    and a handler must not exist for a verb flagged otherwise. One direction
    alone would let the flag rot into permanent pessimism once the verbs land.
    """
    from platterpus.uiscript.runner import ScriptRunner

    def has_handler(name: str) -> bool:
        return hasattr(ScriptRunner, f"_do_{name.replace('-', '_')}")

    wrong = [
        f"{name}: table says implemented={verb.implemented}, "
        f"handler {'exists' if has_handler(name) else 'missing'}"
        for name, verb in verbs_mod.VERBS.items()
        if verb.implemented != has_handler(name)
    ]
    assert not wrong, "the verb table and the runner disagree:\n  " + "\n  ".join(wrong)


def test_the_reference_marks_unimplemented_verbs_in_capitals() -> None:
    """A user reads this while choosing what to put in an unattended batch."""
    text = verbs_mod.verb_reference()
    unimplemented = [n for n, v in verbs_mod.VERBS.items() if not v.implemented]
    if not unimplemented:  # the happy future; the assertion below still holds
        return
    assert "NOT YET IMPLEMENTED" in text
    for name in unimplemented:
        # `name + " "`, not `name` — otherwise `expect` matches the
        # `expect-cyanrip` line, which IS implemented, and the assertion passes
        # against the wrong row. Exactly the substring collision the surface
        # audit flagged for the label resolver, walked into here in the test
        # written to guard against sloppiness.
        line = next(ln for ln in text.splitlines() if ln.strip().startswith(name + " "))
        assert "NOT YET IMPLEMENTED" in line, f"{name} is advertised as working"
