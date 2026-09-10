"""The log-grading verbs read the ARTIFACT, not the window's memory of it.

## The defect

On the 2026-09-09 hardware run, §I — an ARCHIVAL section whose entire subject is
whether cancelling a rip destroys its record — the one failure in 238 steps was
``expect-log-well-formed`` reporting the record destroyed. It had not been. The
cyanrip log on disk carried ``Rip completed:  no (interrupted by SIGTERM, 0 of 14
tracks)``, ``Interrupted at: track 1, mid-read`` and a valid ``Log FUN512:``.

The verb graded ``window._last_rip_log`` — the `RipLog` the window parsed when the
rip "finished", which was 6.1 seconds before the ripper stopped writing. Two
documents, one of them stale, and every surface agreed with the stale one because
every surface read the same stale source.

``CLAUDE.md`` had the rule already: *am I answering from the artifact, or from my
memory of the artifact?* — with the corollary that **when a committed artifact can
settle a question, the test should read the artifact.** The acceptance script is
where this project's tests are written, so it binds there too.

## What is pinned here rather than in `test_uiscript_rip_verbs.py`

That file's stand-in window returns the snapshot from its re-parse, i.e. it models
a disk that agrees — the ordinary case, and the right stand-in for testing grading
logic. Two things it therefore cannot see, and they are the only two that matter:
a stale snapshot over a good log, and a log that cannot be re-read. Both are here,
against real files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from platterpus.config import Config
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.runner import ScriptRunner
from platterpus.uiscript.script import parse

_CORPUS = (
    Path(__file__).resolve().parent.parent
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)


def _parse(text: str) -> Any:
    """Parse cyanrip log text the way the window does.

    **Pinned difference from the product**, per the stand-in rule: the window also
    folds in the measured cache-defeat verdict and the auto-fix supersede. Neither
    touches the completion footer, the signature or the track blocks — the only
    fields these verbs grade — and both need live window state that has nothing to
    do with what is on disk. Reproducing the *reading* is the point; reproducing
    the enrichment would make this a copy of `MainWindow`.
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    return parse_cyanrip_log(text)


def _truncated_before_the_footer(text: str) -> str:
    """The log as it looked mid-write — everything up to the summary block.

    Cut at the ripper's own end-of-rip block rather than at a byte offset, so this
    reproduces the real shape: the tracks are all there, and the last six lines
    (tally, error count, completion verdict, footer) are not.
    """
    marker = "Tracks ripped accurately:"
    assert marker in text, "the corpus log has no end-of-rip tally to cut before"
    return text.split(marker)[0]


def _window(*, on_disk: Path | None, snapshot: Any) -> Any:
    """A stand-in window whose re-parse REALLY reads the file it is given.

    Callers must have requested the session-wide ``qapp`` fixture: a `QWidget`
    with no `QApplication` aborts the interpreter rather than raising, which is
    a crash the suite cannot report.
    """
    from PySide6.QtWidgets import QWidget

    win = QWidget()
    win._config = Config()
    win._last_rip_log = snapshot
    win._last_rip_log_file = on_disk

    def parse_rip_log_from_disk(path: Path) -> Any:
        return _parse(Path(path).read_text(encoding="utf-8", errors="replace"))

    win.parse_rip_log_from_disk = parse_rip_log_from_disk
    return win


def _run(window: Any, line: str) -> tuple[list[Any], ScriptRunner]:
    runner = ScriptRunner(window)
    steps = parse(line)
    assert len(steps) == 1
    runner._report.steps.clear()
    runner._execute(steps[0])
    return list(runner._report.steps), runner


def test_the_corpus_log_is_well_formed_so_these_tests_are_not_vacuous() -> None:
    """Floor. If the reference log did not pass, a PASS below would prove nothing."""
    assert _CORPUS.is_file(), f"missing corpus log {_CORPUS}"
    parsed = _parse(_CORPUS.read_text(errors="replace"))
    assert parsed.rip_completed is True
    assert parsed.log_checksum.strip()
    assert parsed.tracks


def test_the_truncated_snapshot_really_is_missing_what_the_verb_grades() -> None:
    """The other half of the floor.

    A "stale snapshot" that still carried a footer would make the test below pass
    for the wrong reason — the *can it be satisfied by the wrong thing* question,
    asked of my own fixture.
    """
    stale = _parse(_truncated_before_the_footer(_CORPUS.read_text(errors="replace")))
    assert stale.rip_completed is None, "the fixture still has a completion footer"
    assert not stale.log_checksum.strip(), "the fixture still has a signature"
    assert stale.tracks, "the fixture lost the track blocks too — cut too early"


def test_a_stale_snapshot_over_a_good_log_PASSES(tmp_path: Path, qapp: Any) -> None:
    """**The regression test for the 2026-09-09 failure.**

    Disk: the complete, signed log. Window: the parse taken before the ripper
    finished writing. The verb's proposition is about the record, and the record
    is the file — so this passes, and it failed before the fix.
    """
    text = _CORPUS.read_text(errors="replace")
    on_disk = tmp_path / "album.log"
    on_disk.write_text(text, encoding="utf-8")
    win = _window(on_disk=on_disk, snapshot=_parse(_truncated_before_the_footer(text)))

    steps, _ = _run(win, "expect-log-well-formed")

    graded = steps[-1]
    assert graded.outcome is Outcome.PASS, graded.detail
    assert "signature present" in graded.detail, graded.detail


def test_the_divergence_between_disk_and_snapshot_is_REPORTED(
    tmp_path: Path, qapp: Any
) -> None:
    """Passing quietly would hide the real problem it just worked around.

    If the file says something the window's copy does not, the JSON report and the
    EAC-compatible log — both rendered from that copy — describe a different
    document. That is the actual 2026-09-09 damage, and it was invisible precisely
    because every surface agreed with the one stale source. `Outcome.INFO`: stated
    for every caller, graded by none.
    """
    text = _CORPUS.read_text(errors="replace")
    on_disk = tmp_path / "album.log"
    on_disk.write_text(text, encoding="utf-8")
    win = _window(on_disk=on_disk, snapshot=_parse(_truncated_before_the_footer(text)))

    steps, _ = _run(win, "expect-log-well-formed")

    notes = [s for s in steps if s.outcome is Outcome.INFO]
    assert len(notes) == 1, [s.detail for s in steps]
    detail = notes[0].detail
    assert "DISAGREE" in detail
    assert "disk: present" in detail and "window: absent" in detail, detail
    assert "EAC-compatible log" in detail, detail


def test_no_divergence_note_when_the_two_agree(tmp_path: Path, qapp: Any) -> None:
    """The converse, so the note cannot become background noise on every run."""
    text = _CORPUS.read_text(errors="replace")
    on_disk = tmp_path / "album.log"
    on_disk.write_text(text, encoding="utf-8")
    win = _window(on_disk=on_disk, snapshot=_parse(text))

    steps, _ = _run(win, "expect-log-well-formed")

    assert [s.outcome for s in steps] == [Outcome.PASS], [s.detail for s in steps]


def test_a_log_that_cannot_be_re_read_FAILS_and_names_the_file(
    tmp_path: Path, qapp: Any
) -> None:
    """No silent fallback to the snapshot.

    A fallback would restore the exact reading this replaces, and it would do so
    on the runs where the two disagree — the only runs where any of it matters.
    """
    text = _CORPUS.read_text(errors="replace")
    missing = tmp_path / "gone.log"
    win = _window(on_disk=missing, snapshot=_parse(text))

    steps, _ = _run(win, "expect-log-well-formed")

    graded = steps[-1]
    assert graded.outcome is Outcome.FAIL, graded.detail
    assert "gone.log" in graded.detail, graded.detail
    assert "could not be re-read" in graded.detail, graded.detail


def test_a_snapshot_with_no_recorded_path_FAILS_rather_than_grading_the_copy(
    tmp_path: Path, qapp: Any
) -> None:
    """The window holds a log but not where it came from — a state, not a pass."""
    win = _window(on_disk=None, snapshot=_parse(_CORPUS.read_text(errors="replace")))

    steps, _ = _run(win, "expect-log-well-formed")

    graded = steps[-1]
    assert graded.outcome is Outcome.FAIL, graded.detail
    assert "stale-snapshot" in graded.detail, graded.detail


def test_every_log_grading_verb_goes_through_the_from_disk_reader() -> None:
    """**The sweep, not the one place it was learned.**

    Three verbs grade the ripper's log and all three read the snapshot. Fixing the
    one that failed on the rig would have left the other two carrying the same
    defect, waiting for a run where the timing bit them instead — which is
    `CLAUDE.md` §5.o exactly. Enforced by source inspection so a FOURTH verb
    cannot be written against `_last_rip_log` either.
    """
    import inspect

    from platterpus.uiscript import runner as runner_mod

    graders = (
        "_do_expect_log_well_formed",
        "_do_expect_rip_complete",
        "_do_expect_secure_rerip",
    )
    for name in graders:
        source = inspect.getsource(getattr(ScriptRunner, name))
        assert "_rip_log_from_disk(step)" in source, (
            f"{name} does not read the log from disk — it grades the window's "
            "snapshot, which is the 2026-09-09 defect"
        )
        assert "_last_rip_log" not in source, (
            f"{name} still reaches for the window's parsed snapshot directly"
        )
    # FLOOR: the list above must be the whole population, or this test passes by
    # examining a shrinking subset of the verbs it claims to cover.
    #: The one verb allowed to touch `_last_rip_log` directly, with its reason.
    #: A ratchet: it may shrink, never grow. `_do_rip` does not GRADE the log — it
    #: snapshots which log was current when a section asked for a rip, so the
    #: graders can refuse to report a previous section's rip as this one's. That
    #: freshness key is a fact about the window's state and is meant to be, and a
    #: from-disk read cannot serve it: the file has not changed yet.
    ALLOWED = {"_do_rip": "captures the pre-rip freshness key, does not grade"}
    reached = {
        name
        for name, obj in vars(ScriptRunner).items()
        if name.startswith("_do_")
        and callable(obj)
        and "_last_rip_log" in inspect.getsource(obj)
    }
    assert reached <= set(ALLOWED), (
        f"these verbs read the window's parsed rip log directly and have no "
        f"recorded reason to: {sorted(reached - set(ALLOWED))}"
    )
    # And the allowlist is not allowed to rot into a list of names nobody checks:
    # every entry must still be a real verb that still does the thing.
    for name in ALLOWED:
        assert hasattr(ScriptRunner, name), f"{name} is allowlisted but gone"
        assert "_last_rip_log" in inspect.getsource(getattr(ScriptRunner, name)), (
            f"{name} no longer reads _last_rip_log — remove it from ALLOWED "
            "rather than leaving an entry that grants nothing"
        )
    assert inspect.getsource(runner_mod.ScriptRunner._rip_log_from_disk)
