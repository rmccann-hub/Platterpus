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
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

pytest.importorskip("PySide6.QtWidgets")


def _hermetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bring `app.main()` up without touching the user's config, tools or drive.

    Same stubs as `test_app_smoke.py`, which is the file that established this
    pattern; kept in step with it deliberately rather than invented afresh.
    """
    from platterpus import config as config_module

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
            QMessageBox,
            name,
            staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
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
    real_open = MainWindow.open_script_console

    def capturing_open(self: MainWindow, **kwargs: object) -> object:
        console = real_open(self, **kwargs)  # type: ignore[arg-type]
        opened.append(console)
        return console

    monkeypatch.setattr(MainWindow, "open_script_console", capturing_open)

    def _finished() -> bool:
        """The run has ended — or was never started, which is also an answer."""
        if not opened:
            return False
        runner = opened[0].runner  # type: ignore[attr-defined]
        return runner is not None and not runner.running

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
        return 0

    monkeypatch.setattr(QApplication, "exec", fake_exec)
    app_module.main(argv)
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
        missing = tmp_path / "not-here" / "round08joint.txt"
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
