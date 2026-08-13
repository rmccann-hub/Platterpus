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


# --- ~ in a path -------------------------------------------------------------
#
# Found by validating the cyanrip fork's returned round-8 joint script: their C6
# test passes `--verify-log ~/Music/…` with a path that contains both a home
# reference and spaces. Nothing downstream expanded the `~`, so cyanrip would
# have been handed a file name starting with a literal tilde, failed to open it,
# and exited 1 — which is exactly what the test asserts. It would have gone green
# while proving nothing about foreign-log refusal.


def test_a_tilde_path_reaches_the_ripper_expanded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", "/home/rig")
    steps = script_mod.parse("cyanrip -N --verify-log ~/Music/rip.log")
    assert steps[0].args == ("-N", "--verify-log", "/home/rig/Music/rip.log")


def test_quoting_a_path_does_not_cost_you_the_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The case that actually occurs, and the reason this diverges from a shell.

    Every real album folder under ``~/Music`` has spaces in it, so the operator
    must quote — and in bash quoting is precisely what makes ``~`` literal. Both
    spellings would fail silently, in opposite ways.
    """
    monkeypatch.setenv("HOME", "/home/rig")
    steps = script_mod.parse('rig-check "~/Music/The Police/Every Breath - Archive"')
    assert steps[0].args == ("/home/rig/Music/The Police/Every Breath - Archive",)


def test_free_text_verbs_keep_their_tilde(monkeypatch: pytest.MonkeyPatch) -> None:
    """The floor on the blast radius. `expect-cyanrip` carries a MATCH PATTERN,
    and rewriting one would turn an assertion into a different assertion that
    still reports itself as passing."""
    monkeypatch.setenv("HOME", "/home/rig")
    steps = script_mod.parse("log ~/note\nexpect-cyanrip ~/pattern")
    assert steps[0].args == ("~/note",)
    assert steps[1].args == ("~/pattern",)


def test_a_tilde_inside_a_value_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only a leading `~/` (or a lone `~`) is a home reference. A tag value like
    `album=~untitled~` is text, and expanding inside it would corrupt a tag."""
    monkeypatch.setenv("HOME", "/home/rig")
    steps = script_mod.parse("cyanrip -N -a album=~untitled~")
    assert steps[0].args == ("-N", "-a", "album=~untitled~")


def test_expansion_is_declared_per_verb_and_the_declaration_is_reachable() -> None:
    """Revert-proof for the wiring rather than the function: `expand_home` could
    be perfect and unused. Assert both that the flag is set where it is needed and
    that it is NOT set on the free-text verbs, so a later blanket `takes_paths`
    would fail here rather than silently widening the rewrite."""
    assert verbs_mod.VERBS["cyanrip"].takes_paths
    assert verbs_mod.VERBS["rig-check"].takes_paths
    assert verbs_mod.VERBS["set"].takes_paths
    assert not verbs_mod.VERBS["log"].takes_paths
    assert not verbs_mod.VERBS["expect-cyanrip"].takes_paths
    assert not verbs_mod.VERBS["album"].takes_paths


def test_expand_home_never_raises_without_a_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rig script runs from a service context often enough that an unset $HOME
    is real. Returning the token unchanged fails visibly at the tool; raising here
    would take the whole batch down at parse time."""
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    assert script_mod.parse("cyanrip -N --verify-log ~/x.log")[0].error == ""


# --- --verify-log: the app does it, so a script must be able to --------------


def test_verify_log_alone_is_allowed_because_our_own_adapter_does_exactly_this() -> (
    None
):
    """`ripper_log_verify` has built `[cyanrip, --verify-log, <path>]` with no
    `-N` since v0.6.x, and correctly — there is no metadata lookup to disable on
    a path that only checksums a text file. Refusing it from a script meant the
    test surface could not exercise what the product does."""
    assert script_mod.sanitise_cyanrip_args(["--verify-log", "/tmp/rip.log"]) is None
    assert script_mod.sanitise_cyanrip_args(["-Y", "/tmp/rip.log"]) is None


def test_the_production_adapter_really_does_omit_dash_N() -> None:
    """The floor under the test above. If the adapter started passing `-N`, the
    justification for this exemption would be gone and nothing else would say so
    — the argument would keep citing an adapter that no longer behaves that way.
    Read the source rather than trusting the claim (`CLAUDE.md`: answer from the
    artifact, and name which one)."""
    import inspect

    from platterpus.adapters import ripper_log_verify

    src = inspect.getsource(ripper_log_verify)
    assert "[binary, VERIFY_LOG_FLAG, str(path)]" in src, (
        "the verify-log argv has changed shape; re-derive the exemption "
        "in verbs.FILE_ONLY_FLAGS instead of leaving its reason stale"
    )


@pytest.mark.parametrize(
    "args",
    [
        ["--verify-log", "/tmp/rip.log", "-d", "/dev/sr0"],
        ["-d", "/dev/sr0", "--verify-log", "/tmp/rip.log"],
        ["--verify-log", "/tmp/rip.log", "-o", "flac"],
        ["--verify-log"],
        ["--verify-log", "-d"],
    ],
)
def test_the_exemption_covers_the_shape_not_the_flag(args: list[str]) -> None:
    """The companion question: can this be satisfied by the WRONG thing?

    An exemption keyed on "the argv mentions --verify-log" would wave through a
    full rip that happens to carry it — the same `any`-instead-of-`all` mistake
    that made `cyanrip -v -d /dev/sr0 -o flac` read as a probe. The shape is
    checked: exactly the flag, exactly one non-flag operand, nothing else.
    """
    assert script_mod.sanitise_cyanrip_args(args) is not None


def test_a_rip_is_still_refused_after_the_exemption_was_added() -> None:
    """Would this have failed before the change? No — which is the point. It
    exists so a later widening of FILE_ONLY_FLAGS cannot quietly reopen the hole
    the whole sanitiser was written to close."""
    refusal = script_mod.sanitise_cyanrip_args(["-d", "/dev/sr0", "-o", "flac"])
    assert refusal is not None and "-N" in refusal


# --- preflight: say it before the disc pass, not forty minutes in ------------


def _preflight_for(text: str) -> list[str]:
    from platterpus.uiscript.runner import _preflight

    return _preflight(script_mod.parse(text))


def test_preflight_names_every_step_that_will_be_refused() -> None:
    """The whole point: the operator learns before step 1, not on the drive."""
    problems = _preflight_for(
        "log start\n"
        "cyanrip --version\n"
        "cyanrip -d /dev/sr0 -o flac\n"
        "cyanrip -N -d /dev/sr0 -t 1\n"
    )
    assert len(problems) == 2, problems
    assert any("L3" in p and "-N" in p for p in problems)
    assert any("L4" in p and "=" in p for p in problems)


def test_preflight_is_silent_on_a_clean_script() -> None:
    """The floor, from the other side. A preflight that reported something for
    every script would be noise, and noise at the top of a transcript is scrolled
    past — which is the same as not being there."""
    assert _preflight_for("cyanrip --version\ncyanrip -N -d /dev/sr0 -x") == []


def test_preflight_reruns_the_real_sanitiser_rather_than_describing_it() -> None:
    """A second description of what is refused would drift from the guard the
    first time either changed, and the copy the operator reads is the one that
    would be wrong. Asserted structurally because the alternative — a comment
    claiming they agree — is the shape this project keeps paying for."""
    import inspect

    from platterpus.uiscript.runner import _preflight

    src = inspect.getsource(_preflight)
    assert "sanitise_cyanrip_args(" in src


def test_preflight_does_not_filter_the_run() -> None:
    """It moves the *notice* earlier, nothing else. Dropping the refused steps
    would lose their per-step failure rows, and a transcript that never mentions
    a step is indistinguishable from a script that never contained it."""
    steps = script_mod.parse("cyanrip -d /dev/sr0 -o flac\nlog after\n")
    from platterpus.uiscript.runner import _preflight

    assert len(_preflight(steps)) == 1
    assert len(steps) == 2, "preflight must not consume steps"


def test_the_transcript_puts_the_preflight_above_the_steps() -> None:
    """Below the step list it would be read after the thing it was meant to
    prevent."""
    report = RunReport(
        started_at="2026-08-12T00:00:00+00:00",
        app_version="test",
        preflight=["L3: cyanrip -d /dev/sr0 — refused: no -N"],
    )
    report.steps.append(StepRecord(3, "cyanrip -d /dev/sr0", Outcome.FAIL, "refused"))
    text = report_mod.render(report)
    assert "will be refused" in text
    assert text.index("L3: cyanrip -d /dev/sr0 — refused: no -N") < text.index(
        "[ FAIL "
    )


def test_the_preflight_survives_into_the_json() -> None:
    """The transcript is pasted; the JSON is what a machine reads. A finding in
    only one of them is a finding half the consumers cannot see."""
    report = RunReport(started_at="t", app_version="v", preflight=["L1: nope"])
    assert report.as_dict()["preflight"] == ["L1: nope"]


# --- the three defects the 2026-08-12 rig run found --------------------------


def test_wait_for_rip_fails_when_no_rip_is_running() -> None:
    """A wait that succeeds by finding nothing is the shape the script's own
    header forbids.

    On the rig, `rip` had just failed — the Start button was disabled because
    the disc never identified — and `wait-for-rip 7200` then reported **ok
    immediately**, in SECTION D, in a transcript whose entire purpose was
    proving the rip happened.
    """
    from platterpus.uiscript.report import Outcome
    from platterpus.uiscript.runner import ScriptRunner

    class _NoRip:
        _rip_worker = None

    runner = ScriptRunner.__new__(ScriptRunner)
    runner._window = _NoRip()
    recorded: list[tuple[Outcome, str]] = []
    runner._record = lambda step, outcome, detail="": recorded.append((outcome, detail))  # type: ignore[method-assign]
    runner._arm_deadline = lambda *a, **k: recorded.append((Outcome.PASS, "ARMED"))  # type: ignore[method-assign]

    runner._do_wait_for_rip(script_mod.parse("wait-for-rip 7200")[0])
    assert recorded and recorded[0][0] is Outcome.FAIL, recorded
    assert "nothing to wait for" in recorded[0][1]
    assert not any(d == "ARMED" for _o, d in recorded), "it armed a deadline anyway"


def test_a_refused_cyanrip_step_invalidates_the_last_result() -> None:
    """The stale-subject bug, found by the fork reading their own transcript.

    Four times in one rig run, `expect-cyanrip` / `expect-exit` graded the
    *previous* invocation because the step between them was refused and never
    ran. L316's *"expected exit 1, got 0"* was testing C5's `-f` probe, not the
    C6 line it followed. **Had `-f` exited 1, that assertion would have passed
    for a command that never ran.**
    """
    import inspect

    from platterpus.uiscript.runner import ScriptRunner

    src = inspect.getsource(ScriptRunner._do_cyanrip)
    refusal_branch = src.split("if refusal is not None:", 1)[1].split("return", 1)[0]
    for field in ("_last_cyanrip_argv", "_last_cyanrip_output", "_last_cyanrip_exit"):
        assert field in refusal_branch, (
            f"a refused step leaves {field} pointing at an unrelated command"
        )


def test_expect_exit_reports_no_subject_rather_than_a_stale_one() -> None:
    """The other half: clearing the state is only useful if the assertions then
    say so. Asserted through the real handler, not by reading it."""
    from platterpus.uiscript.report import Outcome
    from platterpus.uiscript.runner import ScriptRunner

    runner = ScriptRunner.__new__(ScriptRunner)
    runner._last_cyanrip_argv = []
    runner._last_cyanrip_output = ""
    runner._last_cyanrip_exit = None
    recorded: list[tuple[Outcome, str]] = []
    runner._record = lambda step, outcome, detail="": recorded.append((outcome, detail))  # type: ignore[method-assign]

    runner._do_expect_exit(script_mod.parse("expect-exit 1")[0])
    assert recorded[0][0] is Outcome.ERROR
    assert "no cyanrip command has run" in recorded[0][1]


def test_expect_cyanrip_can_match_a_string_containing_quotes() -> None:
    """cyanrip prints `Missing "=" in track metadata "1"`. Until the raw tail
    existed there was no spelling of that assertion the language could carry —
    the quotes were consumed as grouping characters before the comparison, so
    the fork's C3 had to settle for a weakened substring and reported it as a
    gap in the language rather than in their test. It was."""
    step = script_mod.parse('expect-cyanrip Missing "=" in track metadata')[0]
    assert step.raw_tail == 'Missing "=" in track metadata'
    # The lossy form is what it used to match on, and it could never have hit.
    assert step.joined() == "Missing = in track metadata"
    assert step.joined() not in 'Missing "=" in track metadata'


def test_the_raw_tail_strips_the_verb_and_the_comment_and_nothing_else() -> None:
    """A floor on the new field: it must not smuggle the verb back in, and it
    must still respect the comment rule that a `#` inside quotes is data."""
    assert script_mod.parse("log  hello   there  ")[0].raw_tail == "hello   there"
    assert script_mod.parse("log hi # trailing")[0].raw_tail == "hi"
    assert (
        script_mod.parse('album "Greatest Hits #2"')[0].raw_tail == '"Greatest Hits #2"'
    )
