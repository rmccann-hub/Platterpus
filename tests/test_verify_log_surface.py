"""`scripts/verify_log_surface.py` — clause 3, graded by the reader it is about.

**Why the script exists, in one paragraph**, because a test file is where the
next reader looks. Round 16's close condition clause 3 is *"no line you parse has
moved except the ones §D names"*, and "you" is Platterpus. The cyanrip fork's
`round16-accept.py` grades all three clauses and its exit code is the observable
both sides' S-18 pre-commits hang on — correctly for clauses 1 and 2, which are
facts about their ripper. Clause 3 is not: it is a claim about **our** parser, and
their checker grades it by proxy (the `-j` schema, two instants, the banner, and
the presence of exactly two log lines — against the sixty our generated contract
says we parse). A `GO` resting on a 2-of-60 sample of one third of the condition
is not one either project would want written down, so this script closes the gap
from the side that owns it.

**What these tests hold.** The script's whole value is that it cannot pass by
finding nothing, so most of this file is floors:

* an empty directory is `UNPROBED`, not a pass — the fork's own rule, from their
  checker's first draft;
* a real corpus log passes **and** is asserted to have actually classified lines,
  so a build where every pattern silently stopped matching cannot read as clean;
* an unknown line is found, reported with its file and line number, and exits
  non-zero;
* our own artifacts are excluded **however they are spelled** — the corpus writes
  `_EACcompatible.log` and the evidence bundle writes `(EAC-compatible).log`, and
  the script's first run against the corpus reported 43 lines of our own EAC
  export as evidence that cyanrip's format had moved.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO / "scripts" / "verify_log_surface.py"
#: A real cyanrip log, committed. Read the artifact rather than inventing one:
#: a hand-written fixture would be graded against the patterns it was written
#: from, which is the closed loop this whole seam exists to avoid.
_CORPUS = (
    _REPO
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.log"
)


def _load():
    spec = importlib.util.spec_from_file_location("verify_log_surface", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_log_surface"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def vls():
    return _load()


def test_the_corpus_log_exists_so_this_file_is_not_vacuous() -> None:
    """Floor for the floors."""
    assert _SCRIPT.is_file(), f"missing {_SCRIPT}"
    assert _CORPUS.is_file(), f"missing corpus log {_CORPUS}"


def test_an_empty_directory_is_UNPROBED_and_not_a_pass(tmp_path: Path, vls) -> None:
    """*A clause whose evidence is absent is not a clause that passed.*

    The fork's own rule, adopted verbatim — it was a defect in the first draft of
    their checker and their tests found it. Exit 2, distinct from the exit 1 that
    means "we looked and found something".
    """
    assert vls.main([str(tmp_path)]) == 2


def test_a_log_below_the_line_floor_is_UNPROBED(tmp_path: Path, vls) -> None:
    """A three-line file is not a population to declare a clean sweep from."""
    (tmp_path / "tiny.log").write_text("Disc tracks:    14\n", encoding="utf-8")
    assert vls.main([str(tmp_path)]) == 2
    # ...and the floor is what did it: raise nothing, lower the floor, it passes.
    assert vls.main([str(tmp_path), "--min-lines", "1"]) == 0


def test_a_real_log_passes_AND_actually_classified_something(vls) -> None:
    """**The non-triviality assertion, and it is the important one here.**

    A sweep reports "0 unaccounted" just as happily when every pattern has
    stopped matching as when every line is recognised. So passing is not enough:
    the run must show it *placed* lines, and placed the great majority of them.
    """
    report = vls.sweep([_CORPUS])
    assert not report.unrecognised, report.unrecognised[:5]
    assert report.lines_examined > 500, report.lines_examined
    assert report.lines_parsed > 500, (
        f"only {report.lines_parsed} line(s) matched a parser pattern — a sweep "
        f"that recognises nothing reports a clean result identically"
    )
    # The recognised share is overwhelming; a collapse in the tables would show
    # up here long before it showed up as an unaccounted line.
    placed = report.lines_parsed + report.lines_ignored + report.lines_ours
    assert placed / (report.lines_examined - report.lines_structural) > 0.95


def test_an_unknown_line_is_found_named_and_fails(tmp_path: Path, vls) -> None:
    """The detector detects. File and line number, so it is actionable."""
    text = _CORPUS.read_text(encoding="utf-8", errors="replace")
    spiked = tmp_path / "spiked.log"
    spiked.write_text(text + "\nQuantum flux capacitance: 88.0 GW\n", encoding="utf-8")

    report = vls.sweep([spiked])

    assert len(report.unrecognised) == 1, report.unrecognised
    name, number, line = report.unrecognised[0]
    assert name == str(spiked)
    assert "Quantum flux capacitance" in line
    assert number > 500, "the line number should point at the spike, not line 0"
    assert vls.main([str(spiked)]) == 1


def test_our_own_artifacts_are_excluded_however_they_are_spelled(
    tmp_path: Path, vls
) -> None:
    """**The regression test for this script's own first run.**

    The corpus spells our companion `..._EACcompatible.log`; the evidence bundle
    spells it `... (EAC-compatible).log`. The first version matched the literal
    `"EAC-compatible"`, missed the corpus spelling, and reported 43 lines of our
    own EAC export as evidence that cyanrip's log format had moved. Grading a file
    we wrote against our own parser is the closed loop the fork taught us to
    distrust; doing it and calling the result *their* format change is worse.

    Separator- and case-insensitive, the same move `uiscript/find_script.py`
    makes — legislate the name **and** stop depending on it.
    """
    for spelling in (
        "album_EACcompatible.log",
        "album (EAC-compatible).log",
        "ALBUM (eac compatible).log",
        "album.platterpus-addendum.log",
    ):
        assert vls._is_ours(Path(spelling)), spelling
    for theirs in (
        "album.log",
        "cancel me 20260910t005434 platterpus-fork-gddc1e8c.log",
    ):
        assert not vls._is_ours(Path(theirs)), theirs

    (tmp_path / "album_EACcompatible.log").write_text("Nonsense line\n" * 80)
    (tmp_path / "real.log").write_text(
        _CORPUS.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
    )
    assert vls.main([str(tmp_path)]) == 0, "our own export leaked into the sweep"


def test_the_tables_come_from_the_parser_not_from_the_published_page(vls) -> None:
    """One source of truth, and it is the code.

    The published contract is *generated* from these tables; reading the markdown
    instead would add a copy that goes stale between regenerations — in a script
    whose entire purpose is to be the thing that cannot disagree with the parser.
    """
    from platterpus.parsers import cyanrip_log as parser

    recognised, ignored = vls._tables()
    expected = (
        len(parser._ALL_LINE_RULES)
        + len(parser._SECTION_LINE_PATTERNS)
        + len(parser._INDENTED_LINE_PATTERNS)
    )
    assert len(recognised) == expected, (
        "the sweep's pattern set has drifted from the parser's enumeration tables"
    )
    assert len(ignored) == len(parser._IGNORED_DISC_LINES)
    assert expected > 40, f"only {expected} patterns — the tables look truncated"


def test_an_unreadable_log_is_reported_not_silently_skipped(
    tmp_path: Path, vls, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sweep that quietly drops a file reports a smaller population as complete.

    `CLAUDE.md`: a silent truncation reads as completeness. So an `OSError` on a
    log becomes a finding naming the file, never a shorter list.
    """
    bad = tmp_path / "unreadable.log"
    bad.write_text("x\n")

    def boom(self, **kwargs):  # noqa: ANN001, ANN003
        raise OSError("EIO")

    monkeypatch.setattr(Path, "read_text", boom)
    report = vls.sweep([bad])

    assert report.logs_examined == []
    assert len(report.unrecognised) == 1
    assert "could not read" in report.unrecognised[0][2]
