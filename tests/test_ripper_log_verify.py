"""`cyanrip --verify-log`: the ripper's verdict on its own log.

**What makes this different from every other check in the codebase**, and the whole
reason it exists: the file, the checksum and the checking code are all the
dependency's. Our own `log_integrity` row verified a log *we* wrote against a
footer *we* computed, and reported it fine on a rip that shipped a cyanrip log
cyanrip itself would reject — because we had appended the auto-fix addendum past
its `Log FUN512:` line (round 7 lap 10, H1/J3). A closed loop agrees with itself.

Four states, and the two negatives are not interchangeable:

* `verified` — an affirmative pass.
* `failed` — the ripper checked and rejected the log. The only state that raises an
  `issues[]` entry, because it is the only one that says something is wrong.
* `not_determined` — we could not ask. A missing binary, a build that does not know
  the flag, a timeout, no log. Never rendered as the negative.
* the block being absent — the verification never ran at all.

The flag-rejection branch is the `-V` lesson pointing the other way: a rejected
flag and a failed operation both exit non-zero, and reading the first as the second
is how "the tool is not installed" got reported for a perfectly working binary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus.adapters import ripper_log_verify as rlv
from platterpus.adapters.tool_run import ToolRun

_REPO = Path(__file__).resolve().parent.parent
#: A real cyanrip log, so the argv we build names a file that exists and the
#: `is_file()` guard is exercised against the genuine article.
_REAL_LOG = (
    _REPO
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)


def _runner(run: ToolRun) -> rlv.ToolRunner:
    """A stand-in that returns exactly what the real runner returns.

    Deliberately not richer: *"what does my stand-in do that the real thing does
    not?"* The one thing it adds is recording the argv it was handed, which the
    tests below assert on.
    """

    def _call(argv: list[str]) -> ToolRun:
        return ToolRun(
            exit_code=run.exit_code,
            output=run.output,
            argv=tuple(argv),
            error=run.error,
            started=run.started,
        )

    return _call


def test_the_real_log_exists_so_these_tests_are_not_vacuous() -> None:
    """Floor. Every case below routes through the `is_file()` guard first."""
    assert _REAL_LOG.is_file(), f"missing corpus log {_REAL_LOG}"


def test_exit_zero_is_verified() -> None:
    result = rlv.verify_rip_log(_REAL_LOG, runner=_runner(ToolRun(exit_code=0)))
    assert result.verdict == rlv.VERIFIED
    assert result.is_verified
    assert result.exit_code == 0
    assert "FUN512" in result.detail


def test_the_argv_uses_the_long_flag_and_names_the_log() -> None:
    """Long spelling on purpose — a short letter is what upstream renamed."""
    result = rlv.verify_rip_log(
        _REAL_LOG, "/home/u/.local/bin/cyanrip", runner=_runner(ToolRun(exit_code=0))
    )
    assert list(result.argv) == [
        "/home/u/.local/bin/cyanrip",
        "--verify-log",
        str(_REAL_LOG),
    ]


def test_a_nonzero_exit_with_real_output_is_failed() -> None:
    result = rlv.verify_rip_log(
        _REAL_LOG,
        runner=_runner(
            ToolRun(exit_code=1, output="Log checksum mismatch! File was modified.")
        ),
    )
    assert result.verdict == rlv.FAILED
    assert not result.is_verified
    # The evidence, so the accusation is checkable rather than taken on trust.
    assert result.exit_code == 1
    assert "modified" in result.output
    assert result.argv


@pytest.mark.parametrize(
    "output",
    [
        "Unable to parse command line argument: --verify-log",
        "cyanrip: unrecognized option '--verify-log'",
        "cyanrip: unrecognised option '--verify-log'",
        "invalid option -- 'verify-log'",
        # Case must not matter: a build could capitalise differently.
        "UNABLE TO PARSE COMMAND LINE ARGUMENT: --verify-log",
    ],
)
def test_a_rejected_flag_is_not_determined_never_failed(output: str) -> None:
    """A build that does not know the flag cannot be reporting a bad log.

    This is the branch that keeps us from accusing an intact archival log of being
    corrupt on any cyanrip old enough to lack `--verify-log`. Getting it backwards
    is the exact shape of the `-V` blocker: a rejected flag exits non-zero, and
    reading that as the operation's verdict was wrong then too.
    """
    result = rlv.verify_rip_log(
        _REAL_LOG, runner=_runner(ToolRun(exit_code=1, output=output))
    )
    assert result.verdict == rlv.NOT_DETERMINED, output
    assert not result.is_verified
    assert "does not accept" in result.detail


def test_a_missing_binary_blames_the_pass_not_the_log() -> None:
    """`started=False` is the third state, and this is why it exists.

    Collapsing "no ripper installed" into "the log failed" is how a missing `flac`
    came to be reported as a corrupt FLAC.
    """
    result = rlv.verify_rip_log(
        _REAL_LOG,
        runner=_runner(
            ToolRun(
                exit_code=None,
                started=False,
                error="cyanrip: No such file or directory",
            )
        ),
    )
    assert result.verdict == rlv.NOT_DETERMINED
    assert "could not be run" in result.detail
    # It quotes the tool's own words rather than a generic sentence.
    assert "No such file" in result.detail


def test_an_unreaped_child_is_not_determined_and_keeps_a_null_exit_code() -> None:
    """`None` is a real answer and must never be written as 0."""
    result = rlv.verify_rip_log(
        _REAL_LOG,
        runner=_runner(ToolRun(exit_code=None, output="", error="", started=True)),
    )
    assert result.verdict == rlv.NOT_DETERMINED
    assert result.exit_code is None
    assert "exit status" in result.detail


def test_a_missing_log_is_not_determined_and_never_runs_the_tool(
    tmp_path: Path,
) -> None:
    """No log is not a failed verification, and it must not spawn a process."""
    calls: list[list[str]] = []

    def _recording(argv: list[str]) -> ToolRun:
        calls.append(argv)
        return ToolRun(exit_code=0)

    result = rlv.verify_rip_log(tmp_path / "gone.log", runner=_recording)
    assert result.verdict == rlv.NOT_DETERMINED
    assert not calls, "the tool was run for a log that does not exist"


def test_a_directory_is_not_mistaken_for_a_log(tmp_path: Path) -> None:
    """`is_file`, not `exists` — a folder named `x.log` is not a log."""
    (tmp_path / "x.log").mkdir()
    result = rlv.verify_rip_log(
        tmp_path / "x.log", runner=_runner(ToolRun(exit_code=0))
    )
    assert result.verdict == rlv.NOT_DETERMINED


def test_every_verdict_carries_a_sentence() -> None:
    """A verdict with no explanation is the "accurate and useless" failure."""
    for run in (
        ToolRun(exit_code=0),
        ToolRun(exit_code=1, output="mismatch"),
        ToolRun(exit_code=1, output="Unable to parse command line argument: -Y"),
        ToolRun(exit_code=None, started=False, error="missing"),
        ToolRun(exit_code=None),
    ):
        result = rlv.verify_rip_log(_REAL_LOG, runner=_runner(run))
        assert result.detail.strip(), run
        assert result.verdict in {rlv.VERIFIED, rlv.FAILED, rlv.NOT_DETERMINED}


def test_not_determined_never_satisfies_is_verified() -> None:
    """The standing rule, asserted rather than assumed."""
    for verdict in (rlv.NOT_DETERMINED, rlv.FAILED, "", "something else"):
        assert not rlv.LogVerification(verdict=verdict, detail="x").is_verified


# --- the ABC's default: honest, not a silent pass -----------------------------


def test_the_backend_default_is_not_determined_and_says_why() -> None:
    """CLAUDE.md rule 9 names an unoverridden ABC no-op as a shipped false promise.

    So the default must state that the *backend* cannot answer, and must not return
    anything a caller could read as success.
    """
    from platterpus.adapters.rip_backend import RipBackend

    class _Bare(RipBackend):  # only the abstracts, none of the optional hooks
        def list_drives(self) -> list:  # type: ignore[type-arg]  # ABC signature
            return []

        def disc_info(self, drive: str) -> object:  # type: ignore[override]  # stub
            return object()

        def rip(self, *a: object, **kw: object) -> object:  # type: ignore[override]  # stub
            return object()

        def version(self) -> str:
            return "stub 0"

    result = _Bare().verify_log(_REAL_LOG)
    assert result.verdict == rlv.NOT_DETERMINED
    assert not result.is_verified
    assert "does not implement" in result.detail
    assert "gap in the backend" in result.detail


def test_the_cyanrip_backend_actually_overrides_it() -> None:
    """The companion to the test above: an honest default is only acceptable if the
    real backend does not take it.

    Grep-for-a-call-site, applied to an override — the shape that shipped a
    `cancel()` calling an ABC's concrete no-op nobody had overridden.
    """
    from platterpus.adapters import cyanrip_backend
    from platterpus.adapters.rip_backend import RipBackend

    assert cyanrip_backend.CyanripImpl.verify_log is not RipBackend.verify_log, (
        "the cyanrip backend inherits the no-op default, so no rip ever verifies a log"
    )
