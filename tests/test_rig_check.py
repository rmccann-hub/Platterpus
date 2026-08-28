"""The cyanrip seam check — the one implementation, and both ways in.

The check itself is `platterpus.rig_check`. It is reachable two ways on purpose:
``--rig-check`` (which the *fork's* script calls, so both projects append to one
``MANIFEST.txt``) and the ``rig-check`` script verb (which is where *this*
project's tests are written). These tests hold the pair together — a capability
reachable from only one of them is a capability half the callers cannot use.

The distinction the statuses carry is the thing most worth pinning: **SKIP means
did not run**. A check that ran and found nothing is ``OK``. Collapsing those two
is how a summary comes to read as complete when half of it never executed, which
is the failure `CLAUDE.md` names as a silent truncation reading as completeness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus import rig_check

#: The committed golden reference: a real fork log from a real disc, not a
#: hand-written approximation of one. `CLAUDE.md` — *when a committed artifact
#: can settle a question, the test should read the artifact*; anything else pins
#: this test to my belief about the log's shape, and a stand-in that is tidier
#: than the real thing is exactly what makes the product's gap invisible.
GOLDEN_LOG = (
    Path(__file__).resolve().parent.parent
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)

#: The disc it was ripped from. Hard-coded so the assertion has a floor: a
#: parser that silently degraded to one track would still satisfy "> 0".
GOLDEN_TRACK_COUNT = 14


class TestManifest:
    def test_add_appends_and_never_truncates(self, tmp_path: Path) -> None:
        """The fork's script writes into this same file; a truncating open would
        silently delete the other project's evidence."""
        manifest = rig_check.Manifest(tmp_path, sink=lambda _line: None)
        manifest.add(rig_check.Result(rig_check.OK, "one", "first"))
        # A second Manifest over the same directory stands in for their script
        # opening the file after ours has already written to it.
        other = rig_check.Manifest(tmp_path, sink=lambda _line: None)
        other.add(rig_check.Result(rig_check.INFO, "two", "second"))
        body = (tmp_path / "MANIFEST.txt").read_text(encoding="utf-8")
        assert "one" in body, "the first writer's row was destroyed by the second"
        assert "two" in body

    def test_only_fail_sets_failed(self, tmp_path: Path) -> None:
        """Exit non-zero on FAIL *only* — the fork's contract. An INFO row is a
        measurement this script cannot judge, and a SKIP is work not done;
        neither is a failing verdict, and treating them as one would make every
        run of an unconfigured session look broken."""
        manifest = rig_check.Manifest(tmp_path, sink=lambda _line: None)
        for status in (rig_check.OK, rig_check.INFO, rig_check.SKIP):
            manifest.add(rig_check.Result(status, "n", "d"))
        assert not manifest.failed
        manifest.add(rig_check.Result(rig_check.FAIL, "n", "d"))
        assert manifest.failed


class TestReferenceArgv:
    """The argv the check probes with must be the argv a rip really sends."""

    def test_composes_through_the_real_builder(self) -> None:
        argv = rig_check._compose_reference_argv(
            "cyanrip", "/nonexistent.cue", "platterpus-fork-gddf7ac3"
        )
        # -N is the chokepoint's whole point; without it cyanrip runs its own
        # MusicBrainz lookup and can block on a prompt with no terminal attached.
        assert "-N" in argv
        # The flags whose presence the check reads back out of the -j record.
        for flag in ("-Z", "-l", "-s"):
            assert flag in argv, f"{flag} absent, so the check cannot look for it"
        # argv[0] is stripped: the caller puts the binary back with -j in front.
        assert not argv[0].endswith("cyanrip")

    def test_consumer_flag_tracks_the_build_tag(self) -> None:
        """`--consumer` is capability-gated on the build, so composing with an
        empty tag drops it. If this check composed with a blank tag it would be
        measuring a command line no rip ever sends — the exact class of mistake
        the seam check exists to catch, made by the seam check."""
        known = rig_check._compose_reference_argv(
            "cyanrip", "/nonexistent.cue", "platterpus-fork-gddf7ac3"
        )
        unknown = rig_check._compose_reference_argv("cyanrip", "/nonexistent.cue", "")
        assert "--consumer" in known
        assert "--consumer" not in unknown


def _stub_ripper(tmp_path: Path) -> Path:
    """A fake `cyanrip` that writes a real diagnostics record of its own argv.

    A stub *binary* rather than a patched `subprocess.run`, so the assertion
    covers the actual spawn — the flag, the argument order, and the JSON read
    back off disk. Patching the call would leave exactly the layer this test
    exists to check untested.
    """
    import sys

    # argv[2] is the record path, because the probe composes
    # `[binary, DIAGNOSTICS_FLAG, record, *rip_argv]`. The record is written from
    # `sys.argv` so it reports what ARRIVED rather than a reconstruction — which
    # is precisely the property the real probe relies on cyanrip having, and the
    # reason the check can distinguish a transport problem from a composition one.
    source = f"""#!{sys.executable}
import json
import sys

with open(sys.argv[2], "w") as handle:
    json.dump({{"invocation": " ".join(sys.argv)}}, handle)
"""
    stub = tmp_path / "cyanrip-stub"
    stub.write_text(source, encoding="utf-8")
    stub.chmod(0o755)
    return stub


class TestTheArgvProbeSpawn:
    """The spawn itself, which nothing covered until 2026-08-21.

    `_compose_reference_argv` was tested; the function that *runs* it was not. A
    revert-proof found it: changing the spawned `-j` to `-J` left this whole file
    green. cyanrip would have rejected the flag, the probe would have failed, and
    the first anyone would know is a red row in a hardware session.
    """

    def test_the_probe_spawns_the_diagnostics_flag_from_the_shared_constant(
        self, tmp_path: Path
    ) -> None:
        """The flag reaches the binary, and it is the one the contract publishes.

        Compared against `rig_check.DIAGNOSTICS_FLAG` rather than the literal
        `-j`, because the generated consumer contract derives from that same
        constant — so this asserts the two surfaces cannot disagree about what we
        send, which is the property neither module's own tests can express.
        """
        stub = _stub_ripper(tmp_path)
        out = tmp_path / "out"
        out.mkdir()
        lines: list[str] = []
        manifest = rig_check.Manifest(out, sink=lines.append)
        rig_check.check_argv_reaches_the_binary(
            manifest, str(stub), "platterpus-fork-gddf7ac3"
        )
        record = out / "argv-probe.json"
        assert record.is_file(), (
            f"the stub wrote no record, so the spawn never happened as composed. "
            f"rows: {lines}"
        )
        import json

        invocation = json.loads(record.read_text(encoding="utf-8"))["invocation"]
        assert rig_check.DIAGNOSTICS_FLAG in invocation.split(), (
            f"the probe did not spawn {rig_check.DIAGNOSTICS_FLAG!r}; the binary "
            f"received: {invocation}"
        )
        # Non-triviality: the flag alone proves nothing if the rip argv it is
        # supposed to carry never arrived.
        for flag in ("-N", "-Z", "-l", "-s"):
            assert flag in invocation.split(), (
                f"{flag} did not reach the binary, so this record cannot settle "
                f"anything about argv transport: {invocation}"
            )
        assert not manifest.failed, f"the probe failed against a clean stub: {lines}"

    def test_a_dropped_flag_is_caught_even_when_it_is_not_one_of_the_old_four(
        self, tmp_path: Path
    ) -> None:
        """The check said "every flag we composed arrived intact" while checking
        FOUR of fifteen.

        Unchecked were `-T` — the sanitisation mode whose absence cost a finished
        14-track archival rip on 2026-08-23 — plus `-G`, `-a`, `-t`, `-c`, `-F`,
        `-o`, `-r`, `-d` and `--consumer`. A transport that dropped any of them
        reported OK, in the one check whose purpose is settling an argv question
        for the fork without spending a disc pass.

        `-T` is the subject here deliberately: it is the flag whose absence has
        already cost this project a rip, so a check that cannot see it is not a
        check of the thing that went wrong.
        """
        import sys

        # A stub that silently swallows -T and its value, exactly as a broken
        # transport would. Everything else arrives.
        source = f"""#!{sys.executable}
import json
import sys

argv = []
skip = False
for token in sys.argv:
    if skip:
        skip = False
        continue
    if token == "-T":
        skip = True
        continue
    argv.append(token)
with open(sys.argv[2], "w") as handle:
    json.dump({{"invocation": " ".join(argv)}}, handle)
"""
        stub = tmp_path / "cyanrip-drops-T"
        stub.write_text(source, encoding="utf-8")
        stub.chmod(0o755)
        out = tmp_path / "out"
        out.mkdir()
        lines: list[str] = []
        manifest = rig_check.Manifest(out, sink=lines.append)
        rig_check.check_argv_reaches_the_binary(
            manifest, str(stub), "platterpus-fork-gddf7ac3"
        )
        assert manifest.failed, (
            f"a binary that swallowed -T was graded as receiving every flag "
            f"intact: {lines}"
        )
        assert any("-T" in line for line in lines), (
            f"the failure did not name the flag that went missing: {lines}"
        )

    def test_a_flag_is_matched_as_a_token_not_as_a_substring(
        self, tmp_path: Path
    ) -> None:
        """`-s` used to be satisfied by any path containing `-s`.

        The old test was `flag not in received` against the whole invocation
        STRING, and the invocation embeds an operator-supplied output directory.
        A rig session run into `~/rig-session/` therefore satisfied the `-s`
        check with the real `-s 667` absent — `CLAUDE.md`'s "can it be satisfied
        by the wrong thing?", in a check the fork relies on.

        Reproduced by swallowing `-s` while leaving a path that contains the
        literal `-s` in the invocation.
        """
        import sys

        source = f"""#!{sys.executable}
import json
import sys

argv = []
skip = False
for token in sys.argv:
    if skip:
        skip = False
        continue
    if token == "-s":
        skip = True
        continue
    argv.append(token)
# A path carrying the literal "-s", as a real rig-session output dir does.
argv.append("/home/someone/rig-session/scratch")
with open(sys.argv[2], "w") as handle:
    json.dump({{"invocation": " ".join(argv)}}, handle)
"""
        stub = tmp_path / "cyanrip-drops-s"
        stub.write_text(source, encoding="utf-8")
        stub.chmod(0o755)
        out = tmp_path / "out"
        out.mkdir()
        lines: list[str] = []
        manifest = rig_check.Manifest(out, sink=lines.append)
        rig_check.check_argv_reaches_the_binary(
            manifest, str(stub), "platterpus-fork-gddf7ac3"
        )
        assert manifest.failed, (
            f"a dropped -s was satisfied by the substring in a directory name: {lines}"
        )

    def test_the_composed_argv_is_in_platterpus_template_language(self) -> None:
        """`_compose_reference_argv` promises "the argv a real rip would send".

        The one hand-written input it supplies was in the WRONG LANGUAGE.
        `_build_rip_argv` runs the track template through `scheme_from_template`,
        which translates our `%`-tokens into cyanrip's `{}` ones *and neutralises
        literal braces by turning them into parens*. It was handed
        `"{track} - {title}"` — already cyanrip's syntax — and so composed
        `-F "(track) - (title)"`, a naming scheme no rip has ever sent. Measured
        in the 2026-08-23 rig record before it was fixed.

        "What does my stand-in do that the real thing does not?", in the function
        whose entire value is being indistinguishable from the real thing.
        """
        argv = rig_check._compose_reference_argv(
            "cyanrip", "/nonexistent.cue", "platterpus-fork-gddf7ac3"
        )
        scheme = argv[argv.index("-F") + 1]
        assert scheme == "{track} - {title}", (
            f"-F composed as {scheme!r}. cyanrip's token syntax is braces; parens "
            "mean a Platterpus template was passed through the translator twice"
        )
        # Non-triviality: the flags this check exists to prove reach the binary
        # must actually be in what we compose, or the assertion above is about an
        # argv that proves nothing.
        for flag in ("-T", "-G", "-N", "-Z", "-l", "-s"):
            assert flag in argv, f"{flag} is not in the composed reference argv"

    def test_a_binary_that_writes_no_record_fails_rather_than_passing(
        self, tmp_path: Path
    ) -> None:
        """The other half: prove the check can fail.

        A probe that reports OK when the record is absent would grade every
        future transport defect as clean — and there is no disc involved, so this
        is exactly the kind of check that gets trusted.
        """
        silent = tmp_path / "silent"
        silent.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        silent.chmod(0o755)
        out = tmp_path / "out"
        out.mkdir()
        lines: list[str] = []
        manifest = rig_check.Manifest(out, sink=lines.append)
        rig_check.check_argv_reaches_the_binary(manifest, str(silent), "")
        assert manifest.failed, (
            f"a binary that wrote no diagnostics record was graded as passing: {lines}"
        )


class TestRunRigCheck:
    def test_missing_album_dir_is_skip_not_ok(self, tmp_path: Path) -> None:
        """Without an album folder the log checks must say **SKIP**, not OK.

        This is the assertion the whole status vocabulary exists for. If a
        not-run check rendered as OK, a session where the rip was never found
        would produce a manifest indistinguishable from one where every check
        passed.
        """
        lines: list[str] = []
        rig_check.run_rig_check(tmp_path / "out", sink=lines.append)
        rows = [ln for ln in lines if ln.startswith(("OK", "FAIL", "SKIP", "INFO"))]
        log_rows = [r for r in rows if "handshake/note" in r or "parser/log" in r]
        assert len(log_rows) == 2, f"expected both log checks to report; got {log_rows}"
        for row in log_rows:
            assert row.startswith("SKIP"), f"a check that did not run reported: {row}"

    def test_parses_a_real_shaped_log_and_reads_the_handshake_note(
        self, tmp_path: Path
    ) -> None:
        assert GOLDEN_LOG.is_file(), f"the golden reference moved: {GOLDEN_LOG}"
        album = tmp_path / "album"
        album.mkdir()
        (album / GOLDEN_LOG.name).write_text(
            GOLDEN_LOG.read_text(encoding="utf-8"), encoding="utf-8"
        )
        # An EAC-compatible log sits beside the real one in every rip folder and
        # is a DIFFERENT format; parsing it as a cyanrip log would find nothing.
        # The check must pick the ripper log, not whichever sorts last.
        (album / "Album_EACcompatible.log").write_text("not a cyanrip log\n")
        lines: list[str] = []
        rig_check.run_rig_check(tmp_path / "out", album_dir=album, sink=lines.append)
        joined = "\n".join(lines)
        assert f"parsed {GOLDEN_TRACK_COUNT} track(s)" in joined, joined
        # The handshake note is read from the same log. This artifact carries the
        # OPEN shape ("round 7 lap 7 OPEN, verdict HOLD"), which is a fact about
        # the committed file rather than a guess — read it back to prove the row
        # describes the log in front of it and not a remembered one.
        assert "handshake/note" in joined
        assert "Handshake:" in GOLDEN_LOG.read_text(encoding="utf-8")
        assert "OPEN" in joined, "the open-round note was not recognised"

    @pytest.mark.parametrize(
        ("note", "expected"),
        [
            ("Handshake:      round 7 lap 39 closed, verdict GO", "closed"),
            ("Handshake:      round 8 lap 1 OPEN -- NOT a released build", "OPEN"),
            ("Handshake:      round 9 lap 2 verdict PENDING", "unrecognised"),
        ],
    )
    def test_both_handshake_note_shapes_are_read(
        self, tmp_path: Path, note: str, expected: str
    ) -> None:
        """The fork's §4b asks that **both** shapes be read, not just whichever
        one happens to be in the only log to hand. Only one committed artifact
        exists and it carries the OPEN shape, so the closed shape — and a shape
        that is neither — are covered here. A note the check cannot classify must
        say *unrecognised* rather than defaulting to either verdict: an open
        round silently reported as closed would clear a release gate.
        """
        album = tmp_path / "album"
        album.mkdir()
        (album / "Album.log").write_text(f"cyanrip\n{note}\n", encoding="utf-8")
        manifest = rig_check.Manifest(tmp_path / "out", sink=lambda _line: None)
        rig_check.check_handshake_note_transition(manifest, album)
        rows = [r for r in manifest.results if r.name == "handshake/note"]
        assert len(rows) == 1
        assert rows[0].detail.startswith(expected), rows[0].detail

    def test_a_log_that_parses_to_zero_tracks_fails(self, tmp_path: Path) -> None:
        """A floor, so the check cannot be satisfied by finding nothing. A parse
        that yields zero tracks is not a parse that found nothing wrong."""
        album = tmp_path / "album"
        album.mkdir()
        (album / "Album.log").write_text("nothing resembling a rip\n", encoding="utf-8")
        lines: list[str] = []
        rig_check.run_rig_check(tmp_path / "out", album_dir=album, sink=lines.append)
        assert any(ln.startswith("FAIL") and "ZERO tracks" in ln for ln in lines), (
            "\n".join(lines)
        )

    def test_never_raises_without_a_ripper_installed(self, tmp_path: Path) -> None:
        """The binary is absent in CI. Every probe must degrade to a FAIL row
        rather than an exception — a check that crashes reports nothing at all,
        which is strictly worse than a check that reports a failure."""
        code = rig_check.run_rig_check(tmp_path / "out", sink=lambda _line: None)
        assert code in (0, 1)
        assert (tmp_path / "out" / "MANIFEST.txt").is_file()


class TestScriptVerb:
    """The verb is the *script language's* way in, and it must actually work."""

    def test_the_verb_is_in_the_vocabulary_and_implemented(self) -> None:
        from platterpus.uiscript.verbs import VERBS

        verb = VERBS["rig-check"]
        assert verb.implemented, "an advertised verb with no handler dies mid-run"
        # 0 args: the album folder is optional, because SKIP is an honest answer.
        assert verb.min_args == 0
        # Rest-of-line, not one token. See the arity test below for why.
        assert verb.max_args is None

    def test_an_album_path_with_spaces_parses_without_quoting(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real album folder has spaces, and the verb must take it unquoted.

        Declared as ``max_args=1`` this verb rejected every genuine path with an
        arity complaint — while its handler was already calling ``step.joined()``,
        so the advertised arity contradicted the implementation. Nobody caught it
        writing the verb because every test used a tmp_path with no spaces; it
        surfaced the first time a script named a real album.

        The regression is pinned on the PARSER, not on the handler, because the
        failure happened at parse time: the step never reached the handler at all.

        The ``~`` is now expanded at parse time as well (see
        ``test_uiscript.py`` — a literal tilde reached the ripper and produced a
        *plausible* failure). Both facts are asserted here because they are the
        two halves of "the path a person actually types arrives usable": the
        spaces survive the tokeniser, and the home reference resolves.
        """
        from platterpus.uiscript.script import parse

        monkeypatch.setenv("HOME", "/home/rig")
        step = parse("rig-check ~/Music/The Police/Every Breath You Take (pass 1)")[0]
        assert step.error == "", step.error
        assert (
            step.joined() == "/home/rig/Music/The Police/Every Breath You Take (pass 1)"
        )

    def test_the_runner_has_a_handler_for_it(self) -> None:
        """`tests/test_uiscript.py` sweeps this too; asserted here as well so a
        failure names the verb rather than the sweep."""
        from platterpus.uiscript.runner import ScriptRunner

        assert hasattr(ScriptRunner, "_do_rig_check")
        assert hasattr(ScriptRunner, "_service_rig_check")

    def test_the_verb_does_not_run_the_check_on_the_gui_thread(self) -> None:
        """`run_rig_check` spawns subprocesses, so it must be called from the
        helper thread, never from the handler's own frame. Asserted by reading
        the handler's source for the thread hand-off, because the alternative —
        a comment saying it is safe — is the shape `CLAUDE.md` has an explicit
        rule against (*a comment where a check belongs is not a fix*)."""
        import inspect

        from platterpus.uiscript.runner import ScriptRunner

        src = inspect.getsource(ScriptRunner._do_rig_check)
        assert "threading.Thread" in src
        assert "daemon=True" in src
        # The call must be INSIDE the closure, so it cannot be reached before the
        # thread starts. `_work` is defined after the guard clauses and before the
        # thread start; the call site must sit between them.
        body = src.split("def _work()", 1)
        assert len(body) == 2, "the thread closure is gone; this test is now vacuous"
        assert "run_rig_check(" not in body[0], "the check runs before the thread does"
        assert "run_rig_check(" in body[1]


class TestCliFlag:
    """The fork's script calls this; its argument handling is their interface."""

    def test_a_named_but_missing_album_folder_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Refuse, do not degrade to SKIP. A folder that was *named* and is
        missing is a mistake; SKIP would report it as an omission, and the
        operator would read a clean-looking manifest for a session that checked
        nothing."""
        from platterpus.app import main

        code = main(
            [
                "--rig-check",
                str(tmp_path / "out"),
                "--rig-check-album",
                str(tmp_path / "does-not-exist"),
            ]
        )
        assert code == 2
        assert "error:" in capsys.readouterr().out

    def test_the_flags_exist_with_the_names_the_fork_was_given(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Their script hard-codes these three. Renaming one silently breaks a
        caller in another repository, which no test in that repository can see.

        Asserted against ``--help`` rather than the parser object, so it also
        proves the flags are *documented* — an interface another project is told
        to call and cannot discover is only half published."""
        from platterpus.app import main

        with pytest.raises(SystemExit) as exit_info:
            main(["--help"])
        assert exit_info.value.code == 0
        helptext = capsys.readouterr().out
        for flag in ("--rig-check", "--rig-check-album", "--rig-check-device"):
            assert flag in helptext, f"{flag} is the fork's interface; it moved"


#: Scripts we ship that legitimately carry `cyanrip` lines our own sanitiser
#: refuses, with the exact count. **Only for a section another project owns.**
#:
#: `round08joint.txt` is one file with two authors: sections A/B/D are ours,
#: section C is the cyanrip fork's and is committed **verbatim** — the file's own
#: header promises we will not edit it. Their three refused lines are:
#:
#: * `-t 1` — refused because it is the malformed shape whose memory disclosure
#:   their C3 exists to test. The refusal IS our half of that seam passing; it
#:   cannot also be their half, which needs the argv to reach the binary and
#:   belongs in their own argv gate.
#: **Was 3; is 1 as of the fork's returned lap-7 copy.** They added `-N` to the
#: two lines that needed it, and we quoted the `--verify-log` path (the one edit
#: we made inside their section, announced by a `log` line beside it). The
#: number goes DOWN as the seam converges, which is the whole reason it is a
#: count rather than a flag.
#:
#: A count, not a boolean, and asserted for equality below — see that test.
KNOWN_FOREIGN_REFUSALS: dict[str, int] = {"round08joint.txt": 1}


class TestShippedScripts:
    """Every script we SHIP must parse. This is the deliverable's own gate.

    A test file that fails to load is the worst possible thing to hand another
    project: they run it, see nothing happen, and the round costs a lap. The
    round-8 joint script is sent to the cyanrip fork, so it is held here rather
    than trusted — and this check is what found `rig-check`'s arity bug, which
    reading the file would not have.
    """

    SCRIPTS = sorted(
        (Path(__file__).resolve().parent.parent / "src/platterpus/rig_scripts").glob(
            "*.txt"
        )
    )

    def test_there_are_scripts_to_check(self) -> None:
        """The floor. Without it, a glob that matched nothing would pass silently
        and this whole class would be decoration."""
        assert len(self.SCRIPTS) >= 2, f"only found {self.SCRIPTS}"

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_every_shipped_script_parses_with_no_errors(self, script: Path) -> None:
        from platterpus.uiscript.script import parse

        steps = parse(script.read_text(encoding="utf-8"))
        broken = [
            f"line {s.line_no}: {s.source!r} -> {s.error}" for s in steps if s.error
        ]
        assert not broken, f"{script.name} does not load:\n" + "\n".join(broken)
        # A second floor: a file of pure comments parses cleanly and tests nothing.
        assert len(steps) >= 5, f"{script.name} parsed to {len(steps)} steps"

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_every_shipped_cyanrip_line_survives_the_sanitiser(
        self, script: Path
    ) -> None:
        """A shipped script must not contain a cyanrip line the runner refuses.

        Checked against the REAL `sanitise_cyanrip_args`, not a restatement of its
        rules — a second copy of a safety check is a second thing to drift, and
        this is the check that would catch a rip invocation missing `-N` (which
        would hang an unattended batch on an interactive prompt forever).
        """
        from platterpus.uiscript.script import parse, sanitise_cyanrip_args

        refused = [
            f"line {s.line_no}: {' '.join(s.args)!r} -> {reason}"
            for s in parse(script.read_text(encoding="utf-8"))
            if s.verb == "cyanrip"
            and (reason := sanitise_cyanrip_args(list(s.args))) is not None
        ]
        allowed = KNOWN_FOREIGN_REFUSALS.get(script.name, 0)
        assert len(refused) <= allowed, (
            f"{script.name} carries {len(refused)} refused argv, "
            f"{allowed} accounted for:\n" + "\n".join(refused)
        )

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_every_shipped_answer_dialog_action_is_one_the_runner_accepts(
        self, script: Path
    ) -> None:
        """The parser cannot catch this, and the run that does costs a disc.

        `answer-dialog` validates its first argument at *execution* time, so
        `answer-dialog maybe 60 …` parses perfectly and dies an hour into a
        hardware session with the drive held. Arity is all the parser knows.

        Checked against the REAL `answer_dialog_action_error`, imported rather
        than restated — a second copy of the accepted vocabulary is a second
        thing to drift, and it would drift in the direction of being more
        permissive than the runner, which is the direction that lets a broken
        script ship. Same reasoning as the `cyanrip` sanitiser above.
        """
        from platterpus.uiscript.runner import answer_dialog_action_error
        from platterpus.uiscript.script import parse

        steps = [
            s
            for s in parse(script.read_text(encoding="utf-8"))
            if s.verb == "answer-dialog" and s.args
        ]
        bad = [
            f"line {s.line_no}: {s.source!r} -> {reason}"
            for s in steps
            if (reason := answer_dialog_action_error(s.args[0])) is not None
        ]
        assert not bad, f"{script.name} would fail at run time:\n" + "\n".join(bad)

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_the_foreign_refusal_allowance_is_never_larger_than_reality(
        self, script: Path
    ) -> None:
        """The companion floor, and the reason the allowance is a **count**.

        An allowance is a hole. Left as "this file may contain refusals" it would
        absorb a genuine `-N`-less rip line added later — the exact invocation
        that hangs an unattended batch on an interactive prompt forever, which is
        the whole reason the sanitiser exists. Pinned to the *exact* number so a
        new refusal fails even though the file is already allowed to carry some,
        and so the number must shrink as the fork fixes its lines rather than
        quietly outliving them.
        """
        from platterpus.uiscript.script import parse, sanitise_cyanrip_args

        refused = sum(
            1
            for s in parse(script.read_text(encoding="utf-8"))
            if s.verb == "cyanrip" and sanitise_cyanrip_args(list(s.args)) is not None
        )
        allowed = KNOWN_FOREIGN_REFUSALS.get(script.name, 0)
        assert allowed == refused, (
            f"{script.name}: the allowance is {allowed} but {refused} lines are "
            "refused. If the fork fixed a line, lower the number; the allowance "
            "is a record of a known state, not a budget to spend."
        )


def test_at_least_one_shipped_script_answers_a_dialog() -> None:
    """The floor for the check above, which is otherwise satisfied by nothing.

    A sweep over `answer-dialog` steps passes trivially when no script contains
    one, and it would keep passing after the verb was renamed out from under it.
    This is the "can this check be satisfied by finding nothing?" question
    answered with a number.
    """
    from platterpus.uiscript.script import parse

    found = [
        (script.name, step.args[0])
        for script in TestShippedScripts.SCRIPTS
        for step in parse(script.read_text(encoding="utf-8"))
        if step.verb == "answer-dialog" and step.args
    ]
    assert found, (
        "no shipped script contains an `answer-dialog` step, so the check above "
        "examined nothing. Either a script lost its dialog answer or the verb "
        "was renamed — do not delete this floor, find out which."
    )


class TestAlbumDiscovery:
    """No album folder given → find the one the operator just ripped.

    The rig script used to say *"Replace the path with the folder the rip
    actually wrote"*. A hand-edit in a written procedure is a thing the software
    was supposed to do (maintainer directive, 2026-08-11), and this is that
    thing: the operator has just ripped a disc, and which folder it landed in is
    a question the program can answer.
    """

    def test_an_explicit_path_always_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Discovery is a default, not a policy. A rig session may deliberately
        point at an older rip, and a check that overrode that would silently
        examine a different artifact from the one it was asked about."""
        from platterpus import rip_compare

        called: list[str] = []
        monkeypatch.setattr(
            rip_compare, "newest_report", lambda _roots: called.append("looked") or None
        )
        album = tmp_path / "album"
        album.mkdir()
        (album / "rip.log").write_text("cyanrip\n", encoding="utf-8")
        rig_check.run_rig_check(tmp_path / "out", album_dir=album, sink=lambda _l: None)
        assert not called, "discovery ran even though a path was given"

    def test_discovery_is_announced_not_silent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A check that silently chose its own subject would let a reader
        attribute one rip's log to another. The manifest must name the folder."""
        from platterpus import rip_compare

        album = tmp_path / "Some Artist" / "Some Album"
        album.mkdir(parents=True)
        report = album / "rip.platterpus.json"
        report.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(rip_compare, "default_report_roots", lambda *a, **k: [])
        monkeypatch.setattr(rip_compare, "newest_report", lambda _roots: report)
        lines: list[str] = []
        rig_check.run_rig_check(tmp_path / "out", sink=lines.append)
        joined = "\n".join(lines)
        assert "album/discovery" in joined, joined
        assert str(album) in joined, joined

    def test_finding_nothing_is_reported_and_the_checks_still_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """*"No album folder"* and *"I picked one for you"* are different facts,
        and SKIP still means did not run. Silence on the first would make an
        unconfigured machine look like one where discovery worked."""
        from platterpus import rip_compare

        monkeypatch.setattr(rip_compare, "default_report_roots", lambda *a, **k: [])
        monkeypatch.setattr(rip_compare, "newest_report", lambda _roots: None)
        lines: list[str] = []
        rig_check.run_rig_check(tmp_path / "out", sink=lines.append)
        joined = "\n".join(lines)
        assert "album/discovery" in joined
        log_rows = [ln for ln in lines if "handshake/note" in ln or "parser/log" in ln]
        assert len(log_rows) == 2 and all(r.startswith("SKIP") for r in log_rows), (
            log_rows
        )

    def test_a_raising_discovery_does_not_end_the_session(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A rig session is expensive and unattended. It must not die because a
        configured output folder has gone missing."""
        from platterpus import rip_compare

        def boom(*_a: object, **_k: object) -> list[Path]:
            raise OSError("output folder vanished")

        monkeypatch.setattr(rip_compare, "default_report_roots", boom)
        lines: list[str] = []
        rc = rig_check.run_rig_check(tmp_path / "out", sink=lines.append)
        assert rc in (0, 1)
        assert any("could not look" in ln for ln in lines), lines


# --- A cancelled rip is not a parser failure --------------------------------
#
# Added 2026-08-20. The zero-track floor is correct and stays; what it lacked was
# any check on its SUBJECT. A cancel that lands 91s into track 1 of a
# paranoia-max rip leaves cyanrip's log ending at its `Tracks:` header with
# nothing under it, and `rig-check` called that "parsed to ZERO tracks", i.e. a
# parser failure. It was one of only two failures in a 60-step rig run, and it
# was noise — which is expensive, because a FAIL that turns out to be nothing
# teaches the reader to discount the next one.


def _album_with_empty_log(root: Path, *, cancelled: bool) -> Path:
    """A rip folder whose cyanrip log parses to zero tracks."""
    import json

    album = root / "album"
    album.mkdir(parents=True, exist_ok=True)
    # The real shape: header, then `Tracks:` and nothing after it. Taken from the
    # 2026-08-20 rig artifact rather than invented.
    (album / "rip.log").write_text(
        "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)\n"
        "Disc tracks:    14\n"
        "Tracks to rip:  1, 2, 3\n"
        "\nTracks:\n",
        encoding="utf-8",
    )
    report: dict[str, object] = {"outcome": {"status": "completed"}, "issues": []}
    if cancelled:
        report = {
            "outcome": {"status": "cancelled"},
            "issues": [
                {
                    "code": "rip_cancelled",
                    "message": "the rip was cancelled before it finished",
                }
            ],
        }
    (album / "rip.platterpus.json").write_text(json.dumps(report), encoding="utf-8")
    return album


def test_zero_track_parse_of_a_cancelled_rip_is_skip_not_fail(tmp_path: Path) -> None:
    """The regression test. Revert the fix and this FAILs, which is the bug."""
    album = _album_with_empty_log(tmp_path, cancelled=True)
    manifest = rig_check.Manifest(tmp_path / "m", sink=lambda _line: None)
    rig_check.check_parsers_against_the_log(manifest, album)

    parser = [r for r in manifest.results if r.name == "parser/log"]
    assert len(parser) == 1, parser
    assert parser[0].status == rig_check.SKIP, parser[0].detail
    assert "CANCELLED" in parser[0].detail, (
        "the skip must say WHY it skipped — a bare SKIP is indistinguishable "
        "from a check that quietly stopped working"
    )
    assert not manifest.failed, "a cancelled rip must not fail the rig check"


def test_zero_track_parse_without_cancellation_evidence_still_fails(
    tmp_path: Path,
) -> None:
    """**The floor the fix must not remove.**

    This is the half that matters: the excuse requires POSITIVE evidence of
    cancellation. Without it an empty parse is a real parser regression and must
    still fail — otherwise the fix would have turned a noisy check into one that
    can be satisfied by finding nothing, which is the defect class this project
    keeps paying for.
    """
    album = _album_with_empty_log(tmp_path, cancelled=False)
    manifest = rig_check.Manifest(tmp_path / "m", sink=lambda _line: None)
    rig_check.check_parsers_against_the_log(manifest, album)

    parser = [r for r in manifest.results if r.name == "parser/log"]
    assert len(parser) == 1, parser
    assert parser[0].status == rig_check.FAIL, parser[0].detail
    assert "does not say it was cancelled" in parser[0].detail, parser[0].detail
    assert manifest.failed


def test_cancellation_evidence_survives_a_missing_or_broken_report(
    tmp_path: Path,
) -> None:
    """No report, or an unreadable one, must read as "no excuse" — fail-closed."""
    album = tmp_path / "nojson"
    album.mkdir()
    assert rig_check._rip_was_cancelled(album) is False
    (album / "rip.platterpus.json").write_text("{not json", encoding="utf-8")
    assert rig_check._rip_was_cancelled(album) is False
    (album / "rip.platterpus.json").write_text("[]", encoding="utf-8")
    assert rig_check._rip_was_cancelled(album) is False


def test_either_witness_alone_establishes_cancellation(tmp_path: Path) -> None:
    """Two independent markers, either sufficient — redundancy against drift."""
    import json

    only_status = tmp_path / "a"
    only_status.mkdir()
    (only_status / "r.platterpus.json").write_text(
        json.dumps({"outcome": {"status": "cancelled"}}), encoding="utf-8"
    )
    assert rig_check._rip_was_cancelled(only_status) is True

    only_issue = tmp_path / "b"
    only_issue.mkdir()
    (only_issue / "r.platterpus.json").write_text(
        json.dumps({"issues": [{"code": "rip_cancelled"}]}), encoding="utf-8"
    )
    assert rig_check._rip_was_cancelled(only_issue) is True


# --- Round 14 CC-2: the two rows that carry T1 and T4 evidence ---------------
#
# Both read the fork's OWN committed artifacts rather than a fixture written from
# a belief about them (`CLAUDE.md`: *when a committed artifact can settle a
# question, the test should read the artifact* — anything else pins your belief
# about it). The golden reference is the only `-Z` log either project holds where
# tracks genuinely re-read, which is the one condition under which T1's claim is
# falsifiable at all.

_ARTIFACTS = (
    Path(__file__).resolve().parents[1] / "docs" / "handshake" / "inbound" / "artifacts"
)
_GOLDEN = _ARTIFACTS / "round-14-lap-01-golden-reference-g76a1017.log"
_INTERRUPTED = _ARTIFACTS / "round-14-lap-01-sample-interrupted-g76a1017.log"


def _rows(album: Path, name: str) -> list[object]:
    manifest = rig_check.Manifest(album.parent / "m", sink=lambda _line: None)
    rig_check.check_parsers_against_the_log(manifest, album)
    return [r for r in manifest.results if r.name == name]


def _album_from(tmp_path: Path, artifact: Path) -> Path:
    album = tmp_path / "album"
    album.mkdir()
    (album / "rip.log").write_text(
        artifact.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return album


def test_paranoia_scope_row_reports_the_ratio_and_that_rereads_happened(
    tmp_path: Path,
) -> None:
    """T1's evidence must reach the manifest, with the ratio and a yes/no.

    The numbers are the fork's, measured: per-track counters sum to 30 against a
    disc block of 90, so the ratio is exactly the re-read count (3). Asserted as
    the RELATION rather than as three magic numbers, plus a non-triviality floor —
    two empty tallies also compare equal, and a row saying `0` against `0` would
    satisfy a laxer assertion while proving the check ran on nothing.
    """
    assert _GOLDEN.is_file(), _GOLDEN
    rows = _rows(_album_from(tmp_path, _GOLDEN), "parser/paranoia")
    assert len(rows) == 1, rows
    detail = rows[0].detail  # type: ignore[attr-defined]
    assert "sum to 30" in detail and "totals 90" in detail, detail
    assert "Scope: line present on 3 of 3" in detail, detail
    assert "genuinely exercised: YES" in detail, detail
    assert rows[0].status == rig_check.INFO, rows[0].status  # type: ignore[attr-defined]
    # The multiple may be MENTIONED and must not be the property. Asserted as
    # wording rather than as a number, because the fork's spec asks specifically
    # whether we encode `disc == passes x sum` — true on their fixture by
    # construction, false on media, and a row that named it "ratio" invited
    # exactly that reading.
    assert "ratio" not in detail.lower(), detail
    assert "3x the sum on this rip" in detail, detail


def test_a_per_track_sum_above_the_disc_total_is_a_failure(tmp_path: Path) -> None:
    """The one graded half: `sum(per-track) <= disc` cannot be violated by media.

    The disc block sums every pass and the per-track figures are one pass each, so
    the sum is bounded by the total whatever the drive does. A violation is a
    provider-contract break. Built by editing the fork's own reference downward
    rather than hand-writing a log, so the subject is a real document minus one
    number — `CLAUDE.md`'s *what does my stand-in do that the real thing does not?*
    """
    text = _GOLDEN.read_text(encoding="utf-8")
    # The disc-level block is the one at column 0; drop its total below the
    # per-track sum of 30 while leaving every per-track block untouched.
    head, sep, tail = text.rpartition("READ:")
    assert sep, "the reference no longer has a disc-level READ: row to lower"
    lowered = head + sep + tail.replace(tail.split("\n")[0], "          1", 1)
    album = tmp_path / "album"
    album.mkdir()
    (album / "rip.log").write_text(lowered, encoding="utf-8")
    rows = _rows(album, "parser/paranoia")
    assert len(rows) == 1, rows
    assert rows[0].status == rig_check.FAIL, rows[0].detail  # type: ignore[attr-defined]
    assert "EXCEEDS the disc total" in rows[0].detail  # type: ignore[attr-defined]


def test_the_interruption_row_survives_a_rip_that_parsed_to_zero_tracks(
    tmp_path: Path,
) -> None:
    """**The placement test, and it is the one that would have caught the bug.**

    A rip stopped mid-track is exactly the rip whose log carries `Interrupted at:`
    AND exactly the rip that parses to zero tracks — so a row emitted after the
    zero-track early return is unreachable for every log it describes. The first
    version of this check was written there. The fork's own interrupted sample is
    the subject because it is a real one.
    """
    assert _INTERRUPTED.is_file(), _INTERRUPTED
    album = _album_from(tmp_path, _INTERRUPTED)
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    assert not parse_cyanrip_log(_INTERRUPTED.read_text(encoding="utf-8")).tracks, (
        "this artifact must parse to ZERO tracks or it is not testing the "
        "early-return path this test exists for"
    )
    rows = _rows(album, "parser/interrupted")
    assert len(rows) == 1, rows
    assert "track 1, mid-read" in rows[0].detail, rows[0].detail  # type: ignore[attr-defined]


def test_a_completed_rip_reports_the_absence_rather_than_going_quiet(
    tmp_path: Path,
) -> None:
    """Tri-state: no `Interrupted at:` is an answer, not a missing row.

    Without this the check could be satisfied by finding nothing — a manifest with
    no `parser/interrupted` row reads identically whether the rip finished cleanly
    or the check silently stopped working.
    """
    rows = _rows(_album_from(tmp_path, _GOLDEN), "parser/interrupted")
    assert len(rows) == 1, rows
    assert "no 'Interrupted at:' line" in rows[0].detail, rows[0].detail  # type: ignore[attr-defined]


def test_the_cache_probe_row_says_where_the_evidence_is_when_there_is_none(
    tmp_path: Path,
) -> None:
    """**Regression for a claim we made to the fork that was false.**

    Round 14 lap 2 §F3 told them the `Cache probe:` line *"reaches us because
    rig-check surfaces it verbatim into the manifest"*. It does not and cannot:
    `-x` is not in the rip argv builder at all, so no Platterpus rip ever probes,
    and `rig-check`'s own one invocation targets a device that cannot open. They
    read the script, saw no `rig-check` after the probe section, and refused to
    guess at a mechanism in our code — which is how a wrong claim of ours got
    caught by someone who could not check it.

    An absence that does not say where to look is the defect: a reader of this
    manifest would conclude the evidence was missing rather than filed elsewhere.
    """
    rows = _rows(_album_from(tmp_path, _GOLDEN), "parser/cache-probe")
    assert len(rows) == 1, rows
    detail = rows[0].detail  # type: ignore[attr-defined]
    assert "never will be one" in detail, detail
    assert "SCRIPT REPORT" in detail, detail
    assert "-x -I" in detail, detail


def test_no_rip_argv_platterpus_builds_ever_carries_the_cache_probe_flag() -> None:
    """The claim above, asserted against the builder rather than believed.

    `-x` proceeds into a full rip unless paired with `-I`; the fork declined to
    change that and it once cost this rig an hour. So the reason no rip probes is
    that the flag is absent from the builder, and that is what is checked here —
    a docstring saying so is not a check.
    """
    from platterpus.adapters import cyanrip_backend

    source = Path(cyanrip_backend.__file__).read_text(encoding="utf-8")
    assert '"-x"' not in source and "'-x'" not in source, (
        "the cyanrip argv builder now mentions -x. If a rip can probe the cache, "
        "the manifest row in rig_check saying it never can is now a lie, and -x "
        "without -I proceeds into a full rip."
    )
