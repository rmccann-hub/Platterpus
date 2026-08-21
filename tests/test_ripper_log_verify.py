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
from platterpus.deps import fork_source

#: A build a published flag table lists as accepting `--verify-log`.
#:
#: Required for `failed` since round 7 lap 12 (J4): the fork pointed out that our
#: first classifier told "rejected flag" apart from "rejected log" by matching THEIR
#: error text, which is genopt's wording and one upstream sync from changing. The
#: discriminator is now the build. See `tests/test_verify_log_support.py` for the
#: derivation and for the unknown-build branch; this file keeps the shape of the
#: original states, now with the evidence the verdict requires.
KNOWN_BUILD = fork_source.FORK_TEST_BUILD_TAG

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
        build_tag=KNOWN_BUILD,
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

    **The wording is now a belt, not the discriminator** (lap 12, J4). Two paths reach
    `not_determined` and both are asserted here: an unknown build (no tag), where the
    text is irrelevant; and a *listed* build that nevertheless says it rejects the
    flag, which means our table entry is wrong and the safe reading is still "not
    determined". Neither may reach `failed`.
    """
    unknown = rlv.verify_rip_log(
        _REAL_LOG, runner=_runner(ToolRun(exit_code=1, output=output))
    )
    assert unknown.verdict == rlv.NOT_DETERMINED, output
    assert not unknown.is_verified
    assert "cannot establish" in unknown.detail

    listed = rlv.verify_rip_log(
        _REAL_LOG,
        build_tag=KNOWN_BUILD,
        runner=_runner(ToolRun(exit_code=1, output=output)),
    )
    assert listed.verdict == rlv.NOT_DETERMINED, output
    assert "re-check" in listed.detail, (
        "a listed build that rejects the flag must say the published-table entry "
        "needs re-checking, not blame the log"
    )


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


# --- Absent is not mismatched ------------------------------------------------
#
# Added 2026-08-20 from a real rig artifact. A cancelled rip's log stops before
# cyanrip writes its `Log FUN512:` footer, and the verifier reported *"it does
# not match its own FUN512 checksum, so it is not a faithful record of this rip
# and must not be treated as archival evidence"* — at ERROR, and into the
# report's `issues[]`. Nothing had been altered. That is the project's recurring
# "every word accurate, the message wrong" defect, and the two cases mean
# opposite things: one says the file was tampered with, the other says the
# ripper was killed mid-write.


def _unsigned_log(tmp_path: Path) -> Path:
    """A truncated cyanrip log, shaped like the 2026-08-20 cancelled rig rip."""
    path = tmp_path / "cancelled.log"
    path.write_text(
        "cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)\n"
        "Disc tracks:    14\n"
        "\nTracks:\n",
        encoding="utf-8",
    )
    return path


def test_a_log_with_no_checksum_line_is_not_called_a_mismatch(tmp_path: Path) -> None:
    """The regression test: still FAILED, but never "does not match"."""
    result = rlv.verify_rip_log(
        _unsigned_log(tmp_path),
        build_tag=KNOWN_BUILD,
        runner=_runner(
            ToolRun(exit_code=1, output='No FUN512 checksum found in "x.log"!')
        ),
    )
    # Still not archival evidence — the verdict is unchanged and must stay so.
    assert result.verdict == rlv.FAILED
    assert not result.is_verified
    assert "NO 'Log FUN512:' checksum line" in result.detail, result.detail
    assert "does not match" not in result.detail, (
        "an absent checksum was reported as a mismatch — that accuses an "
        "untampered file of having been altered"
    )
    # The distinguishing fact is stated, not left for the reader to infer.
    assert "killed before it writes" in result.detail, result.detail


def test_a_signed_log_that_fails_is_still_reported_as_altered() -> None:
    """The other branch, against a REAL signed log from the corpus.

    Without this the fix could have softened every rejection into "no checksum",
    which would hide the one case that actually matters.
    """
    result = rlv.verify_rip_log(
        _REAL_LOG,
        build_tag=KNOWN_BUILD,
        runner=_runner(ToolRun(exit_code=1, output="Log checksum mismatch!")),
    )
    assert result.verdict == rlv.FAILED
    assert "does NOT match" in result.detail, result.detail
    assert "altered after the ripper signed it" in result.detail, result.detail


def test_the_discriminator_is_our_own_read_not_the_rippers_wording(
    tmp_path: Path,
) -> None:
    """Keyed on the artifact, per the fork's lap-12 J4 ask.

    cyanrip's "No FUN512 checksum found" text is genopt's and one upstream sync
    from changing, so it must not be load-bearing. Proven by giving the runner
    output that says nothing of the kind and checking the verdict text still
    follows the FILE.
    """
    unsigned = rlv.verify_rip_log(
        _unsigned_log(tmp_path),
        build_tag=KNOWN_BUILD,
        runner=_runner(ToolRun(exit_code=1, output="something else entirely")),
    )
    assert "NO 'Log FUN512:' checksum line" in unsigned.detail, unsigned.detail

    signed = rlv.verify_rip_log(
        _REAL_LOG,
        build_tag=KNOWN_BUILD,
        runner=_runner(ToolRun(exit_code=1, output="something else entirely")),
    )
    assert "does NOT match" in signed.detail, signed.detail


def test_an_unreadable_log_is_not_determined_not_an_accusation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**An unreadable log is a THIRD state, and it used to be reported as the worst.**

    This test replaces one that asserted the opposite, and the replaced one is
    worth recording because it would have protected the defect indefinitely. It
    read: *"Fail-closed: if we cannot read the file we do not volunteer the
    excuse"*, and pinned `_has_checksum_line(unreadable) is True`.

    The premise was a false dichotomy. It framed the choice as *gentle* ("no
    checksum line — the rip was probably cancelled") versus *strong* ("the
    checksum does not match") and picked strong, reasoning that we had not earned
    the gentle one. Both are claims **about the artifact**, and we had read
    nothing about the artifact — so the available third option was to make no
    claim at all. Returning True routed an unopenable file to *"the file was
    altered after the ripper signed it and must not be treated as archival
    evidence"*: an accusation of tampering, from a position of total ignorance,
    written into the report's `issues[]` and logged at ERROR.

    Fail-closed means refusing to certify, which `not_determined` does. It does
    not mean picking the most alarming available explanation — and this project
    already has the rule (`not_determined` is never reported as the negative);
    it was applied to the flag-rejection branch twenty lines up and not to this
    one. Same shape as `docs/testing.md` §5.o: a principle honoured in one
    branch of a function and not its sibling.

    **How narrow this actually is, stated rather than implied.** `verify_rip_log`
    already refuses a path that is not a file, so the reachable case is a log
    that exists at the `is_file()` check and raises `OSError` at the read. That
    is not exotic: a removable or network volume unmounted mid-rip (an external
    USB drive is a normal place to keep a library), an `EIO` off failing storage,
    or the folder being moved between the two calls. It is, however, not
    reproducible as root by permissions, so the raise is injected — which is a
    faithful stand-in, because `OSError` from that one call is precisely the real
    condition.
    """
    signed_but_unreadable = tmp_path / "vanishes.log"
    signed_but_unreadable.write_text("Log FUN512: abc\n", encoding="utf-8")

    real_read_text = Path.read_text

    def read_text_fails(self: Path, *args: object, **kwargs: object) -> str:
        if self == signed_but_unreadable:
            raise OSError(5, "Input/output error")
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]  # passthrough for every other path

    monkeypatch.setattr(Path, "read_text", read_text_fails)
    result = rlv.verify_rip_log(
        signed_but_unreadable,
        build_tag=KNOWN_BUILD,
        runner=_runner(ToolRun(exit_code=1, output="something else entirely")),
    )
    monkeypatch.undo()
    assert result.verdict == rlv.NOT_DETERMINED, (
        f"an unreadable log produced a verdict of {result.verdict!r}. The only "
        f"honest answer is not_determined — we did not read the file."
    )
    assert "could not be read" in result.detail, result.detail
    # The two claims that must NOT appear. Asserted by their text because it is
    # the text a user reads in the report and screenshots into a bug report.
    assert "altered" not in result.detail, (
        f"an unreadable log was reported as ALTERED, which is a claim about the "
        f"artifact made without reading it: {result.detail}"
    )
    assert "NO 'Log FUN512:'" not in result.detail, (
        f"an unreadable log was reported as having no checksum line, which is "
        f"also a claim we did not establish: {result.detail}"
    )
    # Non-triviality: prove the alarming wording is still reachable, so this test
    # cannot be satisfied by a build that never says "altered" about anything.
    real_mismatch = rlv.verify_rip_log(
        _REAL_LOG,
        build_tag=KNOWN_BUILD,
        runner=_runner(ToolRun(exit_code=1, output="something else entirely")),
    )
    assert "altered" in real_mismatch.detail, (
        "the ALTERED wording is now unreachable, so the assertions above prove "
        "nothing — a genuine checksum mismatch must still say so plainly"
    )


def test_the_footer_check_no_longer_owns_the_unreadable_case(tmp_path: Path) -> None:
    """The split that made the fix possible, pinned so it is not merged back.

    `_has_checksum_line_in` takes TEXT. It cannot re-acquire an I/O failure mode,
    which is the whole point: the old single function returned a bool for
    "is there a footer" and had to answer that question for a file it could not
    open. Deciding what an unreadable file means is the caller's job.
    """
    assert rlv._has_checksum_line_in("Log FUN512: abc\n") is True
    assert rlv._has_checksum_line_in("no footer here\n") is False
    assert rlv._read_log_text(tmp_path / "nope.log") is None, (
        "a missing file must read as None — the signal that there is nothing to "
        "form a verdict from"
    )
    written = tmp_path / "yes.log"
    written.write_text("Log FUN512: abc\n", encoding="utf-8")
    assert rlv._read_log_text(written) == "Log FUN512: abc\n"
