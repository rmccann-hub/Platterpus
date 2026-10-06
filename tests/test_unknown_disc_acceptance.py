"""The second acceptance script, for a disc MusicBrainz does not know (C4 (b)).

TASKS *"Permutations the acceptance test still does not run"*, (b), ruled
2026-10-05 (``PLANNING.md`` KDD-41): the full run stops at section E on such a
disc, so the unknown-album path has a script of its own,
``rig_scripts/unknowndiscacceptance.txt``, and two verbs
(``uiscript/unknown_disc_verbs.py``).

**The record grader is tested against a committed rip report** (round 30's
derived-MP3 rip, two tracks), because the report is the product's own record;
where an unknown-album report is needed it is that report with exactly the
``disc`` fields an unknown rip writes changed, so every other field is still a
real rip's. **What the stand-in window does that the product does not**: it
holds a release id, rows and an unknown-mode flag as plain values; the real
fields are named by ``tests/test_uiscript_rip_verbs.py``'s floor test.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from test_uiscript_rip_verbs import _run_one, _window

from platterpus import test_session
from platterpus.uiscript import find_script
from platterpus.uiscript.report import Outcome
from platterpus.uiscript.unknown_disc_verbs import (
    grade_unidentified,
    grade_unknown_record,
)

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "src" / "platterpus" / "rig_scripts"
_UNKNOWN = _SCRIPTS / test_session.UNKNOWN_DISC_SCRIPT_NAME
_FULL = _SCRIPTS / test_session.ACCEPTANCE_SCRIPT_NAME
_REPORT = (
    _REPO / "docs/handshake/artifactsround30/round30oct05fullderivedmp3report.json"
)
_MBID = "e0b2b3c4-1111-2222-3333-444455556666"


def _known_report() -> dict[str, Any]:
    loaded = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _as_unknown(report: dict[str, Any]) -> dict[str, Any]:
    """The committed report as an unknown-album rip writes its `disc` block."""
    edited = copy.deepcopy(report)
    edited["disc"]["unknown"] = True
    edited["disc"]["musicbrainz_release_id"] = None
    return edited


# --- The pure graders ---------------------------------------------------------


def _ready(**changes: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "release_id": "",
        "well_formed": False,
        "rows": 2,
        "unknown_mode": True,
        "picker_open": False,
        "picard_pending": False,
    }
    args.update(changes)
    return args


def test_an_unknown_disc_ready_to_rip_as_unknown_passes() -> None:
    grade = grade_unidentified(**_ready())
    assert grade.passed, grade.detail
    assert "2 placeholder row(s)" in grade.detail


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"picker_open": True}, "release picker is open"),
        ({"release_id": _MBID, "well_formed": True}, "was identified"),
        ({"release_id": "not-an-mbid"}, "malformed release id"),
        ({"rows": 0}, "no track rows"),
        ({"unknown_mode": False}, "confirmation was not accepted"),
        ({"unknown_mode": None}, "confirmation was not accepted"),
        ({"picard_pending": True}, "external application"),
    ],
)
def test_each_way_of_not_being_ready_names_its_own_reason(
    changes: dict[str, Any], says: str
) -> None:
    grade = grade_unidentified(**_ready(**changes))
    assert not grade.passed and says in grade.detail, (changes, grade.detail)


def test_a_committed_known_rip_does_not_read_as_an_unknown_one() -> None:
    """The control, on a real report: round 30's MP3 rip was identified."""
    report = _known_report()
    assert report["disc"]["unknown"] is False, "the fixture changed under the test"
    grade = grade_unknown_record(report)
    assert not grade.passed and "unknown: False" in grade.detail, grade.detail


def test_the_same_rip_recorded_as_unknown_passes() -> None:
    grade = grade_unknown_record(_as_unknown(_known_report()))
    assert grade.passed, grade.detail


def test_an_unknown_record_that_still_names_a_release_disagrees_with_itself() -> None:
    report = _as_unknown(_known_report())
    report["disc"]["musicbrainz_release_id"] = _MBID
    grade = grade_unknown_record(report)
    assert not grade.passed and "disagrees" in grade.detail


def test_a_failed_placeholder_tagging_pass_fails_the_record() -> None:
    report = _as_unknown(_known_report())
    report["issues"] = [
        *report.get("issues", []),
        {"code": "tagging_failed", "detail": "metaflac refused 02 - Track 02.flac"},
    ]
    grade = grade_unknown_record(report)
    assert not grade.passed and "metaflac refused" in grade.detail


def test_a_report_with_no_disc_block_records_no_path() -> None:
    report = _known_report()
    del report["disc"]
    assert not grade_unknown_record(report).passed


# --- The handler, on the stand-in window --------------------------------------


class _UnknownControls:
    def __init__(self, unknown: bool) -> None:
        self._unknown = unknown

    def is_unknown_mode(self) -> bool:
        return self._unknown

    def set_config(self, _config: object) -> None:
        return None


def test_expect_unidentified_reads_the_window(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import platterpus.uiscript.runner as runner_mod

    monkeypatch.setattr(runner_mod, "_release_picker", lambda: None)
    win = _window(rip_controls=_UnknownControls(unknown=True))
    win._current_release_id = ""
    win._pending_picard_launch = False
    record, _runner = _run_one(win, "expect-unidentified")
    assert record.outcome is Outcome.PASS, record.detail

    win._current_release_id = _MBID
    record, _runner = _run_one(win, "expect-unidentified")
    assert record.outcome is Outcome.FAIL and "was identified" in record.detail

    win._current_release_id = ""
    win._pending_picard_launch = True
    record, _runner = _run_one(win, "expect-unidentified")
    assert record.outcome is Outcome.FAIL and "external application" in record.detail


def test_expect_unidentified_names_an_open_picker(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import platterpus.uiscript.runner as runner_mod

    monkeypatch.setattr(runner_mod, "_release_picker", lambda: object())
    win = _window(rip_controls=_UnknownControls(unknown=False))
    win._current_release_id = ""
    record, _runner = _run_one(win, "expect-unidentified")
    assert record.outcome is Outcome.FAIL and "picker is open" in record.detail


# --- The script, and where it is registered -----------------------------------


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _preamble_decisions(path: Path) -> list[str]:
    """The baseline: every `set`/`keep` line before section A."""
    lines = _lines(path)
    end = next(i for i, raw in enumerate(lines) if raw.startswith("log --- A. "))
    return [
        raw.strip() for raw in lines[:end] if raw.strip().startswith(("set ", "keep "))
    ]


def test_the_baseline_is_the_full_runs_line_for_line() -> None:
    """Two runs starting from two baselines would be two different tests of one app."""
    full = _preamble_decisions(_FULL)
    assert len(full) >= 30, "floor: the full baseline was not read"
    assert _preamble_decisions(_UNKNOWN) == full


def test_the_header_says_which_disc_it_needs() -> None:
    header = "\n".join(_lines(_UNKNOWN)[:20])
    assert "WHICH DISC IT NEEDS" in header
    assert "does NOT know" in header and "TWO audio tracks" in header


def test_the_name_is_letters_and_digits_only() -> None:
    """`CLAUDE.md` → artifact filenames: an operator types it."""
    stem = Path(test_session.UNKNOWN_DISC_SCRIPT_NAME).stem
    assert re.fullmatch(r"[A-Za-z0-9]+", stem), stem


def test_the_session_and_run_script_both_reach_the_packaged_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path, why = test_session.builtin_acceptance_script(
        test_session.UNKNOWN_DISC_SCRIPT_NAME
    )
    assert path == _UNKNOWN and path.is_file(), why
    assert test_session.UNKNOWN_DISC_SCRIPT_NAME in test_session.ACCEPTANCE_SCRIPT_NAMES
    # `--run-script unknowndiscacceptance`, from a folder holding nothing.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    found, explanation = find_script.resolve_script_path("unknowndiscacceptance")
    assert found is not None and found.resolve() == _UNKNOWN.resolve(), explanation
    assert "packaged" in explanation


def test_the_disc_is_confirmed_unknown_before_anything_rips() -> None:
    lines = [raw.strip() for raw in _lines(_UNKNOWN)]
    answer = lines.index("answer-dialog ok 180 Rip as unknown album")
    check = lines.index("expect-unidentified")
    abort = next(
        i
        for i, ln in enumerate(lines)
        if i > check and ln.startswith("abort-if-failed")
    )
    first_rip = lines.index("rip")
    assert answer < check < abort < first_rip
    assert "expect-unknown-record" in lines[first_rip:]


def _declared() -> dict[str, str]:
    doc = (_REPO / "docs" / "testing.md").read_text(encoding="utf-8")
    start = "<!-- UNKNOWN-DISC-SEVERITY-TABLE"
    end = "<!-- END-UNKNOWN-DISC-SEVERITY-TABLE -->"
    assert start in doc and end in doc, "the table's markers are gone"
    block = doc.split(start, 1)[1].split(end, 1)[0]
    out: dict[str, str] = {}
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] in {"ARCHIVAL", "UX"}:
            out[cells[0]] = cells[1]
    return out


def test_every_section_is_classified_in_advance() -> None:
    """The full run's rule, held here too: a severity is declared before the run."""
    sections = [
        m.group(1)
        for raw in _lines(_UNKNOWN)
        if (m := re.match(r"log --- ([A-Z][0-9]?)\. ", raw))
    ]
    assert len(sections) >= 4, f"floor: only {sections} parsed"
    declared = _declared()
    assert sorted(declared) == sorted(sections), (declared, sections)
