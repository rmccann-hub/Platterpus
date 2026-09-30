"""The script console, and the two ways it produced a transcript of the wrong run.

Both were found on the rig on 2026-08-13, in the same launch, by an operator who
had every reason to believe they were reading their own script's results.

**Defect 1 — `--run-script` silently ran something else.** `load_file` returned
`None`, so `app.py` called `run_now()` regardless of whether the named file had
loaded. A path that could not be read left the editor holding
:data:`~platterpus.ui.dialogs.script_console.STARTER_SCRIPT`, and *that* ran. The
resulting transcript was correct about everything it said — right app version,
right timestamp, real steps — and was about a nine-line sample the operator had
never seen. `_load_path` had appended *"could not read …"* to the transcript
pane; `_on_run` clears that pane as its first act, so the one sentence explaining
what happened was erased roughly 120 ms later by the very call that followed it.

**Defect 2 — the console counted itself as an application dialog.** It is a
`QDialog`, and it is open by definition while a script runs, so `_active_dialog`
always found it. `expect-dialog none` could therefore never pass — *including in
the starter script*, the sample a first-time reader is told to press Run on to
prove the feature works. It had always reported `FAIL`. Worse and unshipped: a
`cancel` with no application dialog open would have found the console and
rejected it, closing the window that hosts the runner's own timer, mid-run.

**Why these are tested through `main()` and not through the console alone.**
Defect 1 did not live in either component. `load_file` reported the failure
correctly and `_on_run` cleared the pane correctly; the bug was in the sentence
of `app.py` that joined them. A test of either side in isolation passes on the
broken code.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from conftest import stop_window_threads
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

pytest.importorskip("PySide6.QtWidgets")


def _hermetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bring `app.main()` up without touching the user's config, tools or drive.

    Same stubs as `test_app_smoke.py`, which is the file that established this
    pattern; kept in step with it deliberately rather than invented afresh.
    """
    from platterpus import config as config_module
    from platterpus.ui import message_boxes

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.setattr(
        "platterpus.logging_setup.configure_logging", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "platterpus.deps.checks._run_version_command", lambda argv: (False, "", None)
    )
    monkeypatch.setattr(
        "platterpus.adapters.cyanrip_backend.CyanripImpl.list_drives",
        lambda self: [],
    )
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    for name in ("warning", "information", "question", "critical"):
        monkeypatch.setattr(
            message_boxes,
            name,
            lambda *a, **k: QMessageBox.StandardButton.No,
        )
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)


def _run_main_with(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, argv: list[str]
) -> dict[str, object]:
    """Drive the real `app.main(argv)` and report what the console ended up with.

    Returns the console's editor text and transcript text, plus whether a runner
    was ever constructed — the three facts that separate "ran my script", "ran
    the wrong script" and "ran nothing", which the failure being guarded here
    made indistinguishable.
    """
    from platterpus import app as app_module
    from platterpus.ui.main_window import MainWindow

    _hermetic(monkeypatch, tmp_path)
    seen: dict[str, object] = {}
    # Capture the console `main()` itself opened, rather than fishing one out of
    # `topLevelWidgets()`. The `qapp` fixture is session-scoped and `close()`
    # does not destroy, so a console left by an earlier test in this file is
    # still a top-level widget — and picking it up gave a `runner is None` that
    # looked exactly like "the script did not run". Wrapping the real method
    # cannot pick the wrong object.
    opened: list[object] = []
    # The window that opened it, kept so the fake `exec()` below can end the way
    # the real one does: by the window closing.
    windows: list[MainWindow] = []
    real_open = MainWindow.open_script_console

    def capturing_open(self: MainWindow, **kwargs: object) -> object:
        console = real_open(self, **kwargs)  # type: ignore[arg-type]
        opened.append(console)
        windows.append(self)
        return console

    monkeypatch.setattr(MainWindow, "open_script_console", capturing_open)

    def _finished() -> bool:
        """The run has ended — or was never started, which is also an answer.

        "Never started" is `runner is None`. `open_script_console(autorun=True)`
        starts the runner synchronously, so a console that is open with no runner
        was refused, and there is nothing to wait for. This used to return False
        for it, so both refusal tests waited out the full 10 s deadline and passed
        on what they read afterwards (2026-09-26).
        """
        if not opened:
            return False
        runner = opened[0].runner  # type: ignore[attr-defined]
        return runner is None or not runner.running

    def fake_exec(self: QApplication) -> int:
        # Real wall-clock waiting, not a tight `processEvents()` loop. The runner
        # advances one step per `TICK_MS` (120 ms) QTimer firing, and a timer
        # cannot fire in a loop that spins in microseconds — the first version of
        # this pumped 400 times and read a transcript containing only the parse
        # line, which looks identical to a script that ran and did nothing.
        deadline = time.monotonic() + 10.0
        while not _finished() and time.monotonic() < deadline:
            self.processEvents()
            time.sleep(0.01)
        self.processEvents()
        seen["console_found"] = bool(opened)
        if opened:
            console = opened[0]
            seen["editor"] = console.script_text()  # type: ignore[attr-defined]
            seen["transcript"] = console.transcript_text()  # type: ignore[attr-defined]
            seen["ran"] = console.runner is not None  # type: ignore[attr-defined]
            console.close()  # type: ignore[attr-defined]
            console.deleteLater()  # type: ignore[attr-defined]
        # The real `exec()` returns only after the last window has closed, so the
        # window's own `closeEvent` has stopped its workers by then. This stand-in
        # used to return with the window still open, which the product never does,
        # and left the window's startup threads running into whichever test ran
        # next (four tests here, found 2026-09-27 with `-W error::UserWarning`).
        # Close it through the real `closeEvent`, then join what that may have
        # abandoned, with the one helper every window fixture uses.
        for window in windows:
            window.close()
            stop_window_threads(window)
            window.deleteLater()
        return 0

    monkeypatch.setattr(QApplication, "exec", fake_exec)
    app_module.main(argv)
    # The subject of the close above, asserted rather than trusted: `main()`
    # showed this window, and the real `exec()` never returns while it is open.
    # (No window captured means the console never opened, which every caller
    # asserts against with its own message.)
    assert not any(w.isVisible() for w in windows), (
        "the fake exec() returned with the window still open, which the real one "
        "never does; its startup threads then outlive this test"
    )
    return seen


class TestARunScriptThatCannotLoadRunsNothing:
    def test_a_missing_file_does_not_fall_through_to_the_starter_script(
        self, qapp, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The failure exactly as it happened, with the outcome inverted.

        `ran is False` is the assertion that matters. Checking only that the
        transcript mentions the path would pass on code that ran the sample and
        *also* mentioned it.
        """
        # A name NO packaged script has. It used to be `round08joint.txt`, which
        # the package now ships — and the packaged directory is the resolver's
        # last fallback, so that name would (correctly, and saying so) run the
        # shipped copy. The subject here is a name that matches nothing at all.
        from platterpus.uiscript.find_script import packaged_scripts_dir

        missing = tmp_path / "not-here" / "nosuchrigscript08.txt"
        assert not (packaged_scripts_dir() / missing.name).exists(), (
            "the premise: this name must not be one the package ships"
        )
        seen = _run_main_with(monkeypatch, tmp_path, ["--run-script", str(missing)])

        assert seen["console_found"], "the console did not open at all"
        assert seen["ran"] is False, (
            "a script ran even though --run-script's file could not be read — "
            "this is the rig failure: the transcript would be of the starter "
            "sample, stamped with the right app version, and read like a result"
        )
        transcript = str(seen["transcript"])
        assert "REFUSED TO RUN" in transcript
        assert str(missing) in transcript, "the refusal does not name the path"
        # "Not found" is only useful beside where it looked. A bare "no such
        # file" sends the operator to re-check the one path they already typed.
        assert "Searched:" in transcript

    def test_the_editor_is_left_untouched_and_that_is_said_out_loud(
        self, qapp, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Not running is only half of it. The editor still holds the previous
        script, and a reader who presses Run without noticing gets the same wrong
        transcript by hand — so the refusal says so."""
        from platterpus.ui.dialogs.script_console import STARTER_SCRIPT

        seen = _run_main_with(
            monkeypatch, tmp_path, ["--run-script", str(tmp_path / "nope.txt")]
        )
        assert str(seen["editor"]).strip() == STARTER_SCRIPT.strip()
        assert "running it would have produced" in str(seen["transcript"])

    def test_a_readable_file_still_loads_and_still_runs(
        self, qapp, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The non-triviality floor for the two tests above.

        A `--run-script` that refused *everything* would satisfy them perfectly.
        This one proves the happy path is intact, and identifies the script by a
        string only the loaded file contains.
        """
        script = tmp_path / "mine.txt"
        script.write_text("log a line only my script has\n", encoding="utf-8")

        seen = _run_main_with(monkeypatch, tmp_path, ["--run-script", str(script)])

        assert seen["ran"] is True, "a readable script did not run"
        transcript = str(seen["transcript"])
        assert "a line only my script has" in transcript
        assert "REFUSED TO RUN" not in transcript


class TestTheConsoleIsTheHarnessNotTheApplication:
    def test_the_harness_check_matches_the_real_class(self, qapp) -> None:
        """`_is_the_harness` compares a class *name* — this pins that string.

        The name comparison exists because `runner` is imported by the console,
        so importing it back would be circular. That makes the check a string
        literal, and a string literal that nothing checks is one rename away
        from silently matching nothing.
        """
        from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
        from platterpus.uiscript.runner import _is_the_harness

        console = ScriptConsoleDialog(qapp.activeWindow() or _bare_window())
        try:
            assert _is_the_harness(console)
        finally:
            console.close()
            console.deleteLater()

    def test_the_check_does_not_match_an_ordinary_dialog(self, qapp) -> None:
        """The converse, so the exclusion cannot be widened into "ignore every
        dialog" — which would make `expect-dialog` unable to see anything."""
        from platterpus.uiscript.runner import _is_the_harness

        ordinary = QDialog()
        try:
            assert not _is_the_harness(ordinary)
        finally:
            ordinary.deleteLater()

    def test_active_dialog_looks_past_the_console(self, qapp) -> None:
        from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
        from platterpus.uiscript.runner import _active_dialog

        window = _bare_window()
        console = ScriptConsoleDialog(window)
        console.show()
        qapp.processEvents()
        try:
            assert _active_dialog() is None, (
                "the console counted itself; `expect-dialog none` can never pass "
                "and a stray `cancel` would close the window running the script"
            )
            other = QDialog(window)
            other.setWindowTitle("Settings")
            other.show()
            qapp.processEvents()
            try:
                found = _active_dialog()
                assert found is other, f"expected the Settings dialog, got {found}"
            finally:
                other.close()
                other.deleteLater()
        finally:
            console.close()
            console.deleteLater()
            window.close()
            window.deleteLater()

    def test_a_hidden_dialog_is_not_waiting_for_an_answer(
        self, qapp, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Qt's focus can keep naming a dialog after it is hidden.

        Measured 2026-09-26 in the parallel suite: a closed Setup & Updates left by
        an earlier test was still `QApplication.activeWindow()`, so `rip` refused
        to start behind a dialog nobody could see. The stand-in reproduces that
        state directly, because which test leaves it depends on how the tests
        were shared out between workers.
        """
        from platterpus.uiscript import runner

        hidden = QDialog()
        hidden.setWindowTitle("Setup & Updates")
        assert not hidden.isVisible(), "the premise: nothing is on screen"

        class _StaleFocus:
            modal: QDialog | None = None

            @staticmethod
            def activeModalWidget() -> QDialog | None:
                return _StaleFocus.modal

            @staticmethod
            def activeWindow() -> QDialog:
                return hidden

            @staticmethod
            def topLevelWidgets() -> list[QDialog]:
                return [hidden]

        monkeypatch.setattr(runner, "QApplication", _StaleFocus)
        try:
            assert runner._active_dialog() is None, "stale active window counted"
            _StaleFocus.modal = hidden
            assert runner._active_dialog() is None, "stale modal widget counted"
        finally:
            hidden.deleteLater()


def _bare_window():
    """A plain top-level to parent dialogs to, so nothing is orphaned."""
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    widget.setWindowTitle("stand-in main window")
    return widget


class TestSeparatorStyleCannotCostARun:
    """The headline fix: `round-08-joint.txt` and `round08joint.txt` are one name.

    This artifact crosses two repositories, a chat client and a file manager, and
    has been renamed by at least one of them. A convention binds only whoever
    last read it; a normalised comparison binds the code.
    """

    def test_the_key_ignores_case_and_every_separator(self) -> None:
        from platterpus.uiscript.find_script import normalise

        forms = [
            "round08joint.txt",
            "round-08-joint.txt",
            "Round_08_Joint.TXT",
            "round 08 joint.txt",
            "round.08.joint.txt",
        ]
        keys = {normalise(f) for f in forms}
        assert len(keys) == 1, f"these should all be one name, got {keys}"

    def test_the_key_does_not_collapse_different_names(self) -> None:
        """The non-triviality floor. A `normalise` that returned "" would make
        the test above pass perfectly and every file match every other."""
        from platterpus.uiscript.find_script import normalise

        assert normalise("round08joint.txt") != normalise("round09joint.txt")
        assert normalise("round08joint.txt") != normalise("round08lap07.md")
        assert normalise("a.txt"), "normalise() returned empty for a real name"

    def test_a_hyphenated_request_finds_the_separatorless_file(
        self, tmp_path: Path
    ) -> None:
        """Exactly the rig failure, in the direction it happened."""
        from platterpus.uiscript.find_script import resolve_script_path

        real = tmp_path / "round08joint.txt"
        real.write_text("log hi\n", encoding="utf-8")

        found, why = resolve_script_path(str(tmp_path / "round-08-joint.txt"))
        assert found == real, why
        assert "matched" in why, "the explanation does not say it was a near-name"

    def test_it_works_in_the_other_direction_too(self, tmp_path: Path) -> None:
        """Symmetry matters: the fork writes one form and we write the other, and
        neither of us should have to be the one who changes."""
        from platterpus.uiscript.find_script import resolve_script_path

        real = tmp_path / "round-08-joint.txt"
        real.write_text("log hi\n", encoding="utf-8")
        found, _ = resolve_script_path(str(tmp_path / "round08joint.txt"))
        assert found == real

    def test_an_exact_hit_is_never_second_guessed(self, tmp_path: Path) -> None:
        from platterpus.uiscript.find_script import resolve_script_path

        exact = tmp_path / "round08joint.txt"
        exact.write_text("log hi\n", encoding="utf-8")
        found, why = resolve_script_path(str(exact))
        assert found == exact
        assert "matched" not in why, "an exact path should not be reported as fuzzy"

    def test_two_candidates_are_a_refusal_not_a_coin_toss(self, tmp_path: Path) -> None:
        """Silently picking one is how you get a confident transcript of the
        wrong file — the defect this module exists to end, not to relocate."""
        from platterpus.uiscript.find_script import resolve_script_path

        (tmp_path / "round08joint.txt").write_text("log a\n", encoding="utf-8")
        (tmp_path / "round-08-joint.txt").write_text("log b\n", encoding="utf-8")

        found, why = resolve_script_path(str(tmp_path / "round_08_joint.txt"))
        assert found is None, "it guessed between two files"
        assert "more than one" in why
        assert "round08joint.txt" in why and "round-08-joint.txt" in why

    def test_a_miss_names_every_directory_it_searched(self, tmp_path: Path) -> None:
        from platterpus.uiscript.find_script import resolve_script_path

        found, why = resolve_script_path(str(tmp_path / "nothing-like-this.txt"))
        assert found is None
        assert "Searched:" in why
        assert str(tmp_path) in why, "it does not say it looked where I pointed"

    def test_an_unreadable_directory_is_not_an_error(self, tmp_path: Path) -> None:
        """The operator asked about a file, not a directory. A permission problem
        on a fallback dir must not turn a clean 'not found' into a crash."""
        from platterpus.uiscript.find_script import resolve_script_path

        found, why = resolve_script_path(str(tmp_path / "no-such-dir" / "x.txt"))
        assert found is None
        assert "Searched:" in why

    def test_the_resolver_is_the_one_run_script_uses(
        self, qapp, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Revert-proof for the wiring. A resolver nothing calls is the shape
        `CLAUDE.md` records shipping three times; this drives the real
        `main(["--run-script", ...])` with a deliberately mis-separated name and
        requires the run to happen anyway.
        """
        script = tmp_path / "round08joint.txt"
        script.write_text("log resolved by normalising the name\n", encoding="utf-8")

        seen = _run_main_with(
            monkeypatch,
            tmp_path,
            ["--run-script", str(tmp_path / "round-08-joint.txt")],
        )

        assert seen["ran"] is True, "the mis-separated name was not resolved"
        assert "resolved by normalising the name" in str(seen["transcript"])


def _nowhere_else(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An empty HOME and an empty working directory, so only the package has it.

    Returns the fake HOME. `~/Downloads` and `~/Desktop` are expanded from
    ``$HOME`` at call time, so pointing it at an empty folder is what makes "the
    packaged copy was the only one" true rather than true-on-this-machine.
    """
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(work)
    return home


class TestThePackagedCopyIsTheLastFallbackNeverTheFirst:
    """`--run-script fullacceptance` with nothing downloaded (TASKS, 2026-08-27).

    The scripts ship inside the package so an AppImage user has them; the
    resolver reaches them only after every place an operator might have put a
    newer one. Silently preferring the packaged copy would be the "ran a
    different script without saying so" defect this module was written to end,
    so every answer says which copy it is.
    """

    def test_a_bare_name_reaches_the_script_the_menu_runs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The relation between the two routes, not a fact about either.

        Tools → Run acceptance test… opens `builtin_acceptance_script_path()`;
        `--run-script fullacceptance` must open the SAME file, or the two
        routes to one test can run two different scripts.
        """
        from platterpus.test_session import builtin_acceptance_script_path
        from platterpus.uiscript.find_script import resolve_script_path

        _nowhere_else(monkeypatch, tmp_path)
        menu = builtin_acceptance_script_path()
        assert menu.is_file(), f"the premise: this build ships {menu}"

        found, why = resolve_script_path("fullacceptance")

        assert found is not None, why
        assert found.resolve() == menu.resolve(), why
        assert "packaged inside this Platterpus build" in why, why
        # It says where it looked first, so "used the packaged copy" arrives
        # with its reason rather than as a bare assertion.
        assert "nothing matching was found first in" in why, why

    def test_a_downloaded_copy_wins_and_the_answer_says_they_differ(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An operator who fetched a newer script must still get THAT one."""
        from platterpus.uiscript.find_script import resolve_script_path

        home = _nowhere_else(monkeypatch, tmp_path)
        mine = home / "Downloads" / "fullacceptance.txt"
        mine.write_text("log my newer copy\n", encoding="utf-8")

        found, why = resolve_script_path("fullacceptance")

        assert found == mine, why
        assert "your copy" in why, why
        assert "packaged inside this Platterpus build" not in why, (
            f"the operator's own file was described as the packaged one:\n{why}"
        )
        # Theirs wins, and they are told a shipped copy exists and differs —
        # a stale download quietly beating a newer build is the one outcome of
        # this ordering nobody would otherwise see.
        assert "DIFFERENT" in why, why
        assert "rig_scripts" in why, "the packaged copy it shadowed is not named"

    def test_an_identical_download_is_called_identical(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The non-triviality twin: a comparison that always said DIFFERENT
        would pass the test above perfectly."""
        from platterpus.test_session import builtin_acceptance_script_path
        from platterpus.uiscript.find_script import resolve_script_path

        home = _nowhere_else(monkeypatch, tmp_path)
        mine = home / "Downloads" / "fullacceptance.txt"
        mine.write_bytes(builtin_acceptance_script_path().read_bytes())

        found, why = resolve_script_path("fullacceptance")

        assert found == mine, why
        assert "identical" in why and "DIFFERENT" not in why, why

    def test_two_downloads_are_a_refusal_not_a_fall_through(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Ambiguity stops the search; it never falls through to the package.

        A bare name matches every script suffix, so `x.txt` and `x.pscript`
        side by side are two candidates. Resolving that by running the packaged
        copy instead would be a guess dressed as a fallback.
        """
        from platterpus.uiscript.find_script import resolve_script_path

        home = _nowhere_else(monkeypatch, tmp_path)
        (home / "Downloads" / "fullacceptance.txt").write_text("log a\n", "utf-8")
        (home / "Downloads" / "fullacceptance.pscript").write_text("log b\n", "utf-8")

        found, why = resolve_script_path("fullacceptance")

        assert found is None, f"it guessed:\n{why}"
        assert "more than one" in why, why

    def test_a_miss_names_the_packaged_directory_last(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from platterpus.uiscript.find_script import (
            packaged_scripts_dir,
            resolve_script_path,
        )

        _nowhere_else(monkeypatch, tmp_path)
        found, why = resolve_script_path("nothing-like-this")

        assert found is None
        searched = [
            line.strip()
            for line in why.split("Searched:\n", 1)[1].splitlines()
            if line.startswith("  ") and not line.startswith("  (")
        ]
        assert len(searched) >= 4, f"too few directories listed: {searched}"
        assert searched[-1] == str(packaged_scripts_dir()), (
            f"the packaged directory is not the LAST place searched: {searched}"
        )
        # The working directory is searched, and listed, ONCE. The bare name's
        # own parent `.` and the fallback `.` used to be two entries (review R11),
        # spelled differently, so the comparison is by the directory they name.
        named = [str(Path(entry).resolve()) for entry in searched]
        assert len(named) == len(set(named)), searched

    @pytest.mark.parametrize(
        ("typed", "said"),
        [
            # Nothing but a suffix was added: say that, and only that.
            ("fullacceptance", "— added .txt)"),
            # A suffix AND a separator/case difference: say both.
            (
                "Full-Acceptance",
                "— added .txt, and the same name once separators and case are ignored)",
            ),
            # Typed with its suffix: only separators and case differed.
            (
                "full_acceptance.txt",
                "— same name once separators and case are ignored)",
            ),
        ],
        ids=["suffix-only", "suffix-and-separators", "separators-only"],
    )
    def test_the_answer_says_what_actually_differed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, typed: str, said: str
    ) -> None:
        """Review R11: `--run-script fullacceptance` reported a separators-and-case
        match when the only difference was the `.txt` it appended — the module
        whose job is saying which file ran and why, saying something that did not
        happen."""
        from platterpus.test_session import builtin_acceptance_script_path
        from platterpus.uiscript.find_script import resolve_script_path

        _nowhere_else(monkeypatch, tmp_path)
        found, why = resolve_script_path(typed)

        assert found is not None and found.resolve() == (
            builtin_acceptance_script_path().resolve()
        ), why
        assert f"you typed {typed!r}; matched 'fullacceptance.txt' {said}" in why, why
        earlier = why.split("nothing matching was found first in: ", 1)[1]
        places = earlier.split(")", 1)[0].split(", ")
        named = [str(Path(place).resolve()) for place in places]
        assert len(named) == len(set(named)), f"a directory listed twice: {places}"

    def test_an_explicit_path_to_either_copy_is_labelled(self, tmp_path: Path) -> None:
        """ "Print which copy was resolved, always" — including an exact path."""
        from platterpus.test_session import builtin_acceptance_script_path
        from platterpus.uiscript.find_script import (
            is_packaged_copy,
            resolve_script_path,
        )

        shipped = builtin_acceptance_script_path()
        _, why = resolve_script_path(str(shipped))
        assert "packaged inside this Platterpus build" in why, why
        assert is_packaged_copy(shipped)

        mine = tmp_path / "fullacceptance.txt"
        mine.write_text("log mine\n", encoding="utf-8")
        _, why = resolve_script_path(str(mine))
        assert "your copy" in why, why
        assert not is_packaged_copy(mine), "a same-named file elsewhere is not packaged"

    def test_run_script_by_bare_name_runs_the_packaged_copy(
        self,
        qapp,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Through the real `main()`: the fallback is wired, and it is said.

        The packaged directory is pointed at a stand-in holding a one-line
        script, because the real `fullacceptance.txt` would start rips. What
        this proves is the wiring — `--run-script <bare name>` reaches the
        package and the log names it the packaged copy — which the resolver's
        own tests cannot, since a fallback nothing calls passes all of them.
        """
        from platterpus.uiscript import find_script

        shipped = tmp_path / "shipped"
        shipped.mkdir()
        (shipped / "demoscript.txt").write_text(
            "log only the packaged demo says this\n", encoding="utf-8"
        )
        monkeypatch.setattr(find_script, "packaged_scripts_dir", lambda: shipped)
        _nowhere_else(monkeypatch, tmp_path)

        with caplog.at_level("INFO", logger="platterpus.app"):
            seen = _run_main_with(
                monkeypatch, tmp_path, ["--run-script", "demo-script"]
            )

        assert seen["ran"] is True, "the packaged fallback was not reached"
        assert "only the packaged demo says this" in str(seen["transcript"])
        said = [
            r.getMessage() for r in caplog.records if "--run-script" in r.getMessage()
        ]
        assert any("packaged inside this Platterpus build" in m for m in said), (
            f"the run started without saying it used the packaged copy: {said}"
        )


def test_the_console_contains_only_the_next_run(qapp, tmp_path: Path) -> None:
    """The acceptance session's folder reaches exactly ONE run, then clears.

    One-shot on purpose: a run the operator starts by hand afterwards must not be
    written into a finished session's folder, or skip its own bundle.
    """
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

    window = _bare_window()
    console = ScriptConsoleDialog(window)
    try:
        folder = tmp_path / "evidence" / "run"
        console.contain_next_run_in(folder)
        console._editor.setPlainText("log contained\n")
        assert console.run_now()
        first = console._runner
        assert first is not None and first._contained_dir == folder
        assert console._contain_next_run_in is None, "the folder was not one-shot"
        first.stop("test")
        qapp.processEvents()
        console._editor.setPlainText("log by hand\n")
        assert console.run_now()
        second = console._runner
        assert second is not None and second is not first
        assert second._contained_dir is None, "a later run was redirected too"
        second.stop("test")
        qapp.processEvents()
    finally:
        console.close()
        console.deleteLater()
        window.close()
        window.deleteLater()


def test_esc_does_not_end_or_hide_a_run_in_flight(qapp) -> None:
    """Round 29's Full run (the fork's round 30 S25): a stray Esc hid the console
    through `reject()`, which skips `closeEvent`, and the run went on unseen. Esc
    is now refused while a run is in flight; the Stop and close buttons still work."""
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

    window = _bare_window()
    console = ScriptConsoleDialog(window)
    try:
        console._editor.setPlainText("wait 30\n")
        assert console.run_now()
        runner = console._runner
        assert runner is not None and runner.running, "the floor: a run is in flight"
        console.show()
        console.reject()
        qapp.processEvents()
        assert runner.running, "Esc ended the run"
        assert console.isVisible(), "Esc hid the console while its run went on"
    finally:
        console.close()
        console.deleteLater()
        window.close()
        window.deleteLater()


def test_esc_still_closes_an_idle_console(qapp) -> None:
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

    window = _bare_window()
    console = ScriptConsoleDialog(window)
    try:
        console.show()
        console.reject()
        qapp.processEvents()
        assert not console.isVisible()
    finally:
        console.deleteLater()
        window.close()
        window.deleteLater()


def test_the_run_names_WHO_closed_the_console(qapp) -> None:
    """The window's teardown closes the console, and the transcript said "the
    console was closed" either way, so the fork attributed a window close to the
    operator. Each cause now has its own reason."""
    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog

    reasons: dict[str, str] = {}
    for label, closer in (
        ("window", lambda c: c.close_for("the main window was closed")),
        ("console", lambda c: c.close()),
    ):
        window = _bare_window()
        console = ScriptConsoleDialog(window)
        try:
            console._editor.setPlainText("wait 30\n")
            assert console.run_now()
            runner = console._runner
            assert runner is not None and runner.running, "the floor"
            closer(console)
            qapp.processEvents()
            assert not runner.running
            reasons[label] = runner._report.ended_reason
        finally:
            console.deleteLater()
            window.close()
            window.deleteLater()
    assert reasons == {
        "window": "the main window was closed",
        "console": "the console was closed",
    }, reasons
