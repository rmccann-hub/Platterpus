"""Tests for `scripts/revert_probe.py` — the tool that proves a test isn't vacuous.

**Why this file is not optional.** The probe exists to answer *"would this test
fail if I reverted the fix?"*, and its entire value is in the paths where it
**refuses**: a non-unique anchor, a write that did not land, a collection error,
a test that passes anyway. A verification tool whose refusals are untested is
exactly the thing it was built to catch — a check that cannot fail.

So every test here drives the tool to a NOT-OK verdict on purpose, and the one
that matters most is
`test_the_runner_sees_the_reverted_content`: it proves the edit is in place
*while the tests run*, which is failure mode #2 from the tool's own docstring (a
patch script that asserted after it edited, so the write never happened).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


def _load_probe():  # noqa: ANN202 — a module object; annotating it adds nothing
    """Import `scripts/revert_probe.py` by path.

    By path rather than by package import because `scripts/` is deliberately not
    an importable package — `tests/test_harness_fidelity.py` enforces that no test
    imports a repo-root directory by name.
    """
    path = REPO_ROOT / "scripts" / "revert_probe.py"
    spec = importlib.util.spec_from_file_location("_revert_probe_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


probe = _load_probe()


@pytest.fixture
def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A file inside a fake repo root, so the tool's containment check passes."""
    monkeypatch.setattr(probe, "REPO_ROOT", tmp_path)
    path = tmp_path / "subject.py"
    path.write_text("alpha\nUNIQUE_MARKER\nomega\n", encoding="utf-8")
    return path


def _revert(target: Path, **overrides: object) -> object:
    fields: dict[str, object] = {
        "label": "probe",
        "file": target,
        "anchor": "UNIQUE_MARKER\n",
        "replacement": "",
        "tests": ("tests/whatever.py::test_x",),
        "expect": "detected",
    }
    fields.update(overrides)
    return probe.Revert(**fields)  # type: ignore[arg-type]  # kwargs built above


def test_a_detected_revert_is_reported_ok(target: Path) -> None:
    """The happy path: the test failed, so it guards the line."""
    outcome = probe.apply_and_probe(
        _revert(target),
        run_tests=lambda _tests: (1, "FAILED tests/whatever.py::test_x"),
    )
    assert outcome.ok is True
    assert "detected" in outcome.detail


def test_a_test_that_passes_with_the_fix_reverted_is_reported_vacuous(
    target: Path,
) -> None:
    """The finding the whole tool exists to surface — and it must not be silent."""
    outcome = probe.apply_and_probe(
        _revert(target), run_tests=lambda _tests: (0, "1 passed")
    )
    assert outcome.ok is False
    assert "VACUOUS" in outcome.detail, outcome.detail


def test_a_missing_anchor_is_refused_and_the_file_is_untouched(target: Path) -> None:
    """Zero matches means the edit cannot land — a formatter may have reflowed it.

    Reporting this as a *refusal* rather than a pass is the point: a revert that
    never applied produces a passing test indistinguishable from a vacuous one.
    """
    before = target.read_text(encoding="utf-8")
    ran: list[object] = []
    outcome = probe.apply_and_probe(
        _revert(target, anchor="NOT_IN_THE_FILE\n"),
        run_tests=lambda tests: (ran.append(tests), (1, ""))[1],
    )
    assert outcome.ok is False
    assert "REFUSED" in outcome.detail and "0 times" in outcome.detail, outcome.detail
    assert not ran, "the tests were run despite the refusal"
    assert target.read_text(encoding="utf-8") == before, "the file was modified anyway"


def test_an_ambiguous_anchor_is_refused(target: Path) -> None:
    """Two matches means we would not know which site we changed."""
    target.write_text("DUPE\nmiddle\nDUPE\n", encoding="utf-8")
    outcome = probe.apply_and_probe(
        _revert(target, anchor="DUPE\n"), run_tests=lambda _t: (1, "")
    )
    assert outcome.ok is False
    assert "2 times" in outcome.detail, outcome.detail


def test_a_collection_error_is_no_evidence_rather_than_a_detection(
    target: Path,
) -> None:
    """A syntax error exits non-zero, which naively reads as "the test caught it".

    Distinguishing these is not pedantry: the cyanrip fork lost a session to a
    `sed` that produced non-compiling source while output was suppressed, so a
    stale binary ran the test and passed. Opposite direction, same root — the exit
    code alone does not say whether the test *ran*.
    """
    outcome = probe.apply_and_probe(
        _revert(target),
        run_tests=lambda _t: (2, "ImportError while loading conftest '/x/conftest.py'"),
    )
    assert outcome.ok is False
    assert "NO EVIDENCE" in outcome.detail, outcome.detail


def test_an_unaffected_expectation_fails_when_the_test_does_depend_on_the_line(
    target: Path,
) -> None:
    """`expect: unaffected` asserts an anchor is NARROW; it must be able to fail."""
    outcome = probe.apply_and_probe(
        _revert(target, expect="unaffected"),
        run_tests=lambda _t: (1, "FAILED something"),
    )
    assert outcome.ok is False
    assert "UNEXPECTED" in outcome.detail, outcome.detail


def test_the_runner_sees_the_reverted_content(target: Path) -> None:
    """The edit must be in place WHILE the tests run, not applied around them.

    Failure mode #2 from the tool's docstring: a patch script that asserted after
    it edited, so the write never happened. A tool that restored before running —
    or never wrote at all — would pass every other test in this file.
    """
    seen: list[str] = []

    def runner(_tests: tuple[str, ...]) -> tuple[int, str]:
        seen.append(target.read_text(encoding="utf-8"))
        return 1, "FAILED"

    outcome = probe.apply_and_probe(_revert(target), run_tests=runner)
    assert outcome.ok is True
    assert seen, "the runner was never called"
    assert "UNIQUE_MARKER" not in seen[0], (
        "the tests ran against the ORIGINAL content — the revert was not in effect, "
        "so a resulting failure would prove nothing"
    )


def test_the_file_is_restored_after_every_outcome(target: Path) -> None:
    """Restoration is not conditional on the verdict.

    Checked for a detected revert, a vacuous one and an error, because a `finally`
    that only covers the happy path leaves the operator's tree edited.
    """
    before = target.read_text(encoding="utf-8")
    for code, output in ((1, "FAILED"), (0, "1 passed"), (2, "INTERNALERROR")):
        probe.apply_and_probe(
            _revert(target), run_tests=lambda _t, c=code, o=output: (c, o)
        )
        assert target.read_text(encoding="utf-8") == before, (
            f"the file was not restored after a run that exited {code}"
        )


def test_an_empty_spec_is_refused_rather_than_reported_as_success(
    tmp_path: Path,
) -> None:
    """A spec with nothing in it would exit 0 having probed nothing.

    That is this project's canonical *"can this check be satisfied by finding
    nothing?"* shape, and the tool whose job is catching vacuous checks is the
    last place it should be allowed.
    """
    spec = tmp_path / "spec.json"
    spec.write_text('{"reverts": []}', encoding="utf-8")
    with pytest.raises(probe.ProbeError, match="non-empty"):
        probe._parse_spec(spec)


def test_a_spec_naming_a_file_outside_the_repo_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tool writes to the file it is given, so containment is a safety check."""
    monkeypatch.setattr(probe, "REPO_ROOT", tmp_path / "repo")
    (tmp_path / "repo").mkdir()
    spec = tmp_path / "spec.json"
    spec.write_text(
        '{"reverts": [{"file": "../escape.py", "anchor": "x", "tests": ["t::t"]}]}',
        encoding="utf-8",
    )
    with pytest.raises(probe.ProbeError):
        probe._parse_spec(spec)
