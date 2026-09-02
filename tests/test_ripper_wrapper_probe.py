"""The wrapper-exit probe: the fork's three §2 commands, absorbed into the app.

**What this file is really guarding.** Round 15's one close condition needs a
hardware pass, and two consecutive rig mornings produced zero rips because a
probe of `~/.local/bin/cyanrip --version` never returned. The fork's lap 1 §2
asked us to run three shell commands. `CLAUDE.md` says a procedure handed back in
prose is work handed back, so the app runs them instead — which means the
*decision table* those commands feed is now code, and code needs the branch that
matters (a hang) exercised without anything actually hanging.

Hence `_conclude` is pure and separately tested: every verdict is driven from
fabricated outcomes. A test that could only observe the happy path would be a
detector for the case that was never broken.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from platterpus.deps import ripper_wrapper_probe as rwp
from platterpus.deps.ripper_wrapper_probe import ProbeOutcome, Verdict


def _outcome(
    label: str,
    verdict: Verdict,
    *,
    exit_code: int | None = 0,
    elapsed: float = 0.04,
    reason: str | None = None,
) -> ProbeOutcome:
    return ProbeOutcome(
        label=label,
        argv=("/bin/true",),
        verdict=verdict,
        exit_code=exit_code,
        elapsed_s=elapsed,
        output="",
        skipped_reason=reason,
    )


class TestTheDecisionTable:
    """`_conclude` — pure, so every branch is reachable in a unit test."""

    def test_a_hanging_wrapper_alone_absolves_both_programs(self) -> None:
        """The fork's own sentence: *if the third hangs, no part of either
        program is involved.* That has to be the FIRST branch — a container entry
        that never returns makes every later probe meaningless, and reporting it
        as "the export hangs" would send the reader after the wrong component."""
        report = rwp._conclude(
            (
                _outcome("host export, stdin open", Verdict.HANGS, exit_code=None),
                _outcome("wrapper alone", Verdict.HANGS, exit_code=None),
            )
        )
        assert report.verdict is Verdict.HANGS
        assert report.decided_by == "wrapper alone"
        assert "container entry" in report.summary
        # And it must NOT blame the wrapper: nothing exited, so there is no
        # contrast to draw and the honest answer names neither program.
        assert report.blames_the_wrapper is False

    def test_stdin_open_hangs_and_stdin_closed_returns_names_the_one_char_fix(
        self,
    ) -> None:
        """The outcome the fork predicted, and the one that unblocks CC-1."""
        report = rwp._conclude(
            (
                _outcome("host export, stdin open", Verdict.HANGS, exit_code=None),
                _outcome("host export, stdin closed", Verdict.EXITS),
                _outcome("wrapper alone", Verdict.EXITS),
                _outcome("in-container binary", Verdict.EXITS),
            )
        )
        assert report.verdict is Verdict.HANGS
        assert "stdin" in report.summary
        assert report.blames_the_wrapper is True

    def test_both_stdin_shapes_hang_says_closing_stdin_is_not_the_fix(self) -> None:
        """Stated explicitly, because the tempting summary here is the previous
        one — and telling an operator to redirect stdin when that does not help
        is worse than saying nothing."""
        report = rwp._conclude(
            (
                _outcome("host export, stdin open", Verdict.HANGS, exit_code=None),
                _outcome("host export, stdin closed", Verdict.HANGS, exit_code=None),
                _outcome("wrapper alone", Verdict.EXITS),
                _outcome("in-container binary", Verdict.EXITS),
            )
        )
        assert report.verdict is Verdict.HANGS
        assert "not the fix" in report.summary

    def test_a_wrapper_that_exits_does_not_reproduce_the_hang(self) -> None:
        report = rwp._conclude(
            (
                _outcome("host export, stdin open", Verdict.EXITS, elapsed=0.12),
                _outcome("host export, stdin closed", Verdict.EXITS),
                _outcome("wrapper alone", Verdict.EXITS),
                _outcome("in-container binary", Verdict.EXITS),
            )
        )
        assert report.verdict is Verdict.EXITS
        assert "does not reproduce" in report.summary
        assert report.blames_the_wrapper is False

    def test_an_absent_export_is_NOT_DETERMINED_and_never_a_pass(self) -> None:
        """Tri-state, and this is the half a two-state version would get wrong.

        A wrapper we could not test is not a working wrapper. The reason is
        carried into the summary so the reader is not left guessing which of the
        four probes declined."""
        report = rwp._conclude(
            (
                _outcome(
                    "host export, stdin open",
                    Verdict.NOT_DETERMINED,
                    exit_code=None,
                    reason="/home/u/.local/bin/cyanrip does not exist",
                ),
            )
        )
        assert report.verdict is Verdict.NOT_DETERMINED
        assert report.verdict is not Verdict.EXITS
        assert "does not exist" in report.summary
        assert report.decided_by is None

    def test_blaming_the_wrapper_needs_evidence_on_BOTH_sides(self) -> None:
        """A hang with nothing to contrast it against is not attribution.

        `blames_the_wrapper` is the claim that would go into a handshake lap, so
        it requires a wrapper probe that hung AND a direct probe that exited. A
        hang while the binary was never successfully run is equally consistent
        with a broken container, and saying otherwise is exactly the *"never
        state a mechanism in the other side's code"* failure pointed inward.
        """
        only_hangs = rwp._conclude(
            (_outcome("host export, stdin open", Verdict.HANGS, exit_code=None),)
        )
        assert only_hangs.blames_the_wrapper is False

        with_contrast = rwp._conclude(
            (
                _outcome("host export, stdin open", Verdict.HANGS, exit_code=None),
                _outcome("in-container binary", Verdict.EXITS),
            )
        )
        assert with_contrast.blames_the_wrapper is True


class TestRunOne:
    """The real spawner, against real processes — cheap ones."""

    def test_a_process_that_exits_is_recorded_with_its_code_and_argv(self) -> None:
        outcome = rwp.run_one(
            "probe",
            [sys.executable, "-c", "print('hi'); raise SystemExit(3)"],
            timeout_s=30,
        )
        assert outcome.verdict is Verdict.EXITS
        assert outcome.exit_code == 3
        assert "hi" in outcome.output
        # argv read off `Popen.args`, so it is what the OS received.
        assert outcome.argv[0] == sys.executable
        assert outcome.unreapable is False

    def test_a_process_that_never_exits_is_HANGS_and_gets_killed(self) -> None:
        """The behaviour that matters, driven with a real sleeper.

        A short timeout on purpose: this asserts the *mechanism* (deadline fires,
        group is killed, verdict is HANGS), not a duration.
        """
        outcome = rwp.run_one(
            "sleeper",
            [sys.executable, "-c", "import time; time.sleep(120)"],
            timeout_s=1.5,
        )
        assert outcome.verdict is Verdict.HANGS
        assert outcome.elapsed_s < 30, outcome.elapsed_s

    def test_stderr_is_merged_so_a_diagnosis_cannot_be_dropped(self) -> None:
        """`CLAUDE.md`: capture everything the dependency told us. A tool's fatal
        message usually goes to stderr, so a probe that kept only stdout would
        record the failure and discard the reason for it."""
        outcome = rwp.run_one(
            "noisy",
            [sys.executable, "-c", "import sys; sys.stderr.write('BOOM\\n')"],
            timeout_s=30,
        )
        assert "BOOM" in outcome.output

    def test_a_missing_binary_never_raises(self) -> None:
        """A diagnostic that throws turns a hang into a crash about the detector."""
        outcome = rwp.run_one("absent", ["/nonexistent/xyzzy"], timeout_s=5)
        assert outcome.verdict is Verdict.NOT_DETERMINED
        assert outcome.exit_code is None
        assert outcome.skipped_reason is not None

    def test_it_runs_in_its_own_session_so_a_group_kill_cannot_reach_us(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """**The one that would have killed the test runner.**

        `run_one` escalates with `os.killpg`. Without `start_new_session=True`
        the child shares OUR process group, so that signal reaches pytest — and
        `CLAUDE.md` records this exact mistake. Asserted on the kwarg passed to
        `Popen`, because the consequence is unobservable until the day it fires.
        """
        seen: dict[str, object] = {}
        real = subprocess.Popen

        def spy(*args: object, **kwargs: object) -> object:
            seen.update(kwargs)
            return real(*args, **kwargs)  # type: ignore[arg-type]  # pass-through spy

        monkeypatch.setattr(subprocess, "Popen", spy)
        rwp.run_one("x", [sys.executable, "-c", "pass"], timeout_s=30)
        assert seen.get("start_new_session") is True, seen


class TestProbeOrchestration:
    def test_the_observed_failure_is_probed_FIRST_and_with_stdin_attached(
        self, tmp_path: Path
    ) -> None:
        """Two properties in one, and both are load-bearing.

        **Order:** the hanging invocation runs first, because a broken container
        would otherwise mask it. **stdin:** the first probe must leave stdin
        inherited — closing it is the fork's *candidate fix*, so a probe that
        closed it would be testing the fix and would report "exits" every time,
        which is the *"can this check be satisfied by the wrong thing?"* failure.
        """
        export = tmp_path / "cyanrip"
        export.write_text("#!/bin/sh\nexit 0\n")
        export.chmod(0o755)
        calls: list[tuple[str, bool]] = []

        def fake(
            label: str, argv: list[str], *, timeout_s: float, stdin_devnull: bool = True
        ) -> ProbeOutcome:
            calls.append((label, stdin_devnull))
            return _outcome(label, Verdict.EXITS)

        rwp.probe(export_path=export, runner=fake)
        assert calls[0][0] == "host export, stdin open"
        assert calls[0][1] is False, "the first probe must NOT close stdin"
        assert [c[0] for c in calls] == [
            "host export, stdin open",
            "host export, stdin closed",
            "wrapper alone",
            "in-container binary",
        ]

    def test_an_absent_export_still_probes_the_container(self, tmp_path: Path) -> None:
        """Because "not installed" and "installed but hanging" need different
        answers, and the container probes distinguish them."""
        labels: list[str] = []

        def fake(
            label: str, argv: list[str], *, timeout_s: float, stdin_devnull: bool = True
        ) -> ProbeOutcome:
            labels.append(label)
            return _outcome(label, Verdict.EXITS)

        report = rwp.probe(export_path=tmp_path / "absent", runner=fake)
        assert "wrapper alone" in labels
        assert any(o.skipped_reason for o in report.outcomes)


class TestRendering:
    def test_a_null_exit_code_is_never_printed_as_zero(self) -> None:
        """**Tri-state survives rendering, or it was never tri-state.**

        `CLAUDE.md`: an exit code of `null` for a child never reaped is a real
        answer and must never be written as `0`. The value being right in the
        dataclass and wrong on the page is the same bug from the reader's side.
        """
        text = rwp.render(
            rwp._conclude(
                (
                    ProbeOutcome(
                        label="host export, stdin open",
                        argv=("/x/cyanrip", "--version"),
                        verdict=Verdict.HANGS,
                        exit_code=None,
                        elapsed_s=20.0,
                        output="banner\n",
                        unreapable=True,
                    ),
                    _outcome("in-container binary", Verdict.EXITS),
                )
            )
        )
        assert "null (never reaped)" in text
        assert "exit: 0" not in text.split("in-container")[0]
        assert "UNREAPABLE" in text
        assert "/x/cyanrip" in text, "the exact argv must survive into the report"

    def test_every_probe_appears_not_just_the_failing_one(self) -> None:
        """A report that lists only failures cannot distinguish a clean run from
        a run that never happened."""
        text = rwp.render(
            rwp._conclude(
                (
                    _outcome("host export, stdin open", Verdict.EXITS),
                    _outcome("host export, stdin closed", Verdict.EXITS),
                    _outcome("wrapper alone", Verdict.EXITS),
                    _outcome("in-container binary", Verdict.EXITS),
                )
            )
        )
        for label in (
            "host export, stdin open",
            "host export, stdin closed",
            "wrapper alone",
            "in-container binary",
        ):
            assert label in text, label

    def test_elision_is_counted_and_marked_never_silent(self) -> None:
        """`CLAUDE.md`: a silent truncation reads as completeness — and the tail
        is the half that carries a tool's fatal message, so both ends are kept."""
        text = rwp._bounded("HEAD" + ("x" * 50_000) + "TAIL")
        assert text.startswith("HEAD")
        assert text.endswith("TAIL")
        assert "characters elided" in text


class TestTheDoctorRow:
    """The preflight check that surfaces it — `CLAUDE.md`: a diagnosis we
    captured but never showed the user is the same bug from their side."""

    def test_a_hang_is_a_WARN_with_the_full_probe_record_attached(self) -> None:
        """WARN not FAIL, deliberately: the app pipes its I/O and can still rip,
        and a blocker here would stop a rig that works. But the complete record
        must reach the report — that is the *surfacing* half of capture."""
        from platterpus import preflight

        report = rwp._conclude(
            (
                _outcome("host export, stdin open", Verdict.HANGS, exit_code=None),
                _outcome("host export, stdin closed", Verdict.EXITS),
                _outcome("wrapper alone", Verdict.EXITS),
                _outcome("in-container binary", Verdict.EXITS),
            )
        )
        result = preflight.check_ripper_wrapper_exits(run_probe=lambda: report)
        assert result.status is preflight.Status.WARN
        assert "stdin" in result.summary
        assert result.detail and "host export, stdin open" in result.detail
        assert result.hint and "/dev/null" in result.hint

    def test_not_determined_is_SKIP_and_never_OK(self) -> None:
        """The tri-state's whole point, at the surface that a user reads."""
        from platterpus import preflight

        report = rwp._conclude(
            (
                _outcome(
                    "host export, stdin open",
                    Verdict.NOT_DETERMINED,
                    exit_code=None,
                    reason="not installed",
                ),
            )
        )
        result = preflight.check_ripper_wrapper_exits(run_probe=lambda: report)
        assert result.status is preflight.Status.SKIP
        assert result.status is not preflight.Status.OK

    def test_a_probe_that_explodes_does_not_take_the_doctor_with_it(self) -> None:
        from platterpus import preflight

        def boom() -> object:
            raise RuntimeError("no distrobox here")

        result = preflight.check_ripper_wrapper_exits(run_probe=boom)
        assert result.status is preflight.Status.SKIP
        assert result.detail and "no distrobox" in result.detail

    def test_the_check_is_actually_wired_into_the_doctor_run(self) -> None:
        """**The assertion that stops this being an unreachable module.**

        A check nothing calls is a check that cannot fire, and this project has
        shipped a fully-implemented `cancel()` called from nowhere. Asserted on
        the source of `run_all` so it cannot pass against a definition that
        merely exists.
        """
        import inspect

        from platterpus import preflight

        source = inspect.getsource(preflight.run_preflight)
        assert "check_ripper_wrapper_exits()" in source, (
            "check_ripper_wrapper_exits is defined but never emitted by "
            "run_preflight, so --doctor would never run it"
        )
