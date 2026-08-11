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

    def test_an_album_path_with_spaces_parses_without_quoting(self) -> None:
        """A real album folder has spaces, and the verb must take it unquoted.

        Declared as ``max_args=1`` this verb rejected every genuine path with an
        arity complaint — while its handler was already calling ``step.joined()``,
        so the advertised arity contradicted the implementation. Nobody caught it
        writing the verb because every test used a tmp_path with no spaces; it
        surfaced the first time a script named a real album.

        The regression is pinned on the PARSER, not on the handler, because the
        failure happened at parse time: the step never reached the handler at all.
        """
        from platterpus.uiscript.script import parse

        step = parse("rig-check ~/Music/The Police/Every Breath You Take (pass 1)")[0]
        assert step.error == "", step.error
        assert step.joined() == "~/Music/The Police/Every Breath You Take (pass 1)"

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


class TestShippedScripts:
    """Every script we SHIP must parse. This is the deliverable's own gate.

    A test file that fails to load is the worst possible thing to hand another
    project: they run it, see nothing happen, and the round costs a lap. The
    round-8 joint script is sent to the cyanrip fork, so it is held here rather
    than trusted — and this check is what found `rig-check`'s arity bug, which
    reading the file would not have.
    """

    SCRIPTS = sorted(
        (Path(__file__).resolve().parent.parent / "docs/rig-scripts").glob("*.txt")
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
        assert not refused, f"{script.name} carries refused argv:\n" + "\n".join(
            refused
        )
