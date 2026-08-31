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
import os
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


def test_no_tests_collected_is_no_evidence_not_a_detection(target: Path) -> None:
    """Exit code 5 is the dangerous one, and it used to read as success.

    pytest returns 5 for NO_TESTS_COLLECTED — what a mistyped node id gives you.
    It is non-zero, so a `code != 0` check calls it a detection and certifies a
    test as guarding a line it never ran against. That is a false POSITIVE, which
    is worse than the false negative below: it ends the investigation.
    """
    outcome = probe.apply_and_probe(
        _revert(target), run_tests=lambda _t: (5, "no tests ran")
    )
    assert outcome.ok is False
    assert "NO EVIDENCE" in outcome.detail, outcome.detail
    assert "NO TESTS" in outcome.detail.upper(), (
        f"the message must name the actual cause: {outcome.detail!r}"
    )


def test_an_error_name_echoed_in_output_is_not_mistaken_for_a_collection_error(
    target: Path,
) -> None:
    """A genuine failure must stay a detection even when the output says "SyntaxError".

    pytest echoes the failing test's SOURCE into its report. A test that itself
    contains `except SyntaxError:` therefore puts that word in the output of a
    perfectly good detection — and the first version of this tool substring-matched
    for it and reported NO EVIDENCE. Found by running the tool on exactly such a
    test. A substring match where a subject was needed, in the tool built to catch
    that.
    """
    echoed = (
        "F   [100%]\n"
        "=== FAILURES ===\n"
        "    def test_thing():\n"
        "        try:\n"
        "            ast.parse(text)\n"
        "        except SyntaxError:\n"
        "            continue\n"
        "E   AssertionError: the real failure\n"
    )
    outcome = probe.apply_and_probe(_revert(target), run_tests=lambda _t: (1, echoed))
    assert outcome.ok is True, (
        "a real failure was discarded as 'no evidence' because the word "
        f"SyntaxError appeared in echoed source: {outcome.detail!r}"
    )


def test_an_unrecognised_exit_code_is_no_evidence(target: Path) -> None:
    """Tri-state again: a code neither pytest nor this tool defines is not a verdict."""
    outcome = probe.apply_and_probe(
        _revert(target), run_tests=lambda _t: (137, "killed")
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


# ==========================================================================
# A FIFTH WAY TO GET A FALSE VERDICT: stale bytecode
# ==========================================================================
#
# CPython's default `.pyc` invalidation compares the source's SIZE and its mtime
# TRUNCATED TO WHOLE SECONDS. The probe writes a file, runs pytest, and writes it
# back — routinely inside one second — and a revert is frequently the same length
# as the line it replaces. `MAX_RIP_WAIT_S: float = 6 * 60 * 60` and its `3 * 60
# * 60` revert are **35 characters each**, so both halves of the check saw no
# change and the stale bytecode was reused.
#
# Measured 2026-08-29: after the probe restored the 6-hour source,
# `from platterpus.uiscript import runner; runner.MAX_RIP_WAIT_S` still returned
# `10800`. The suite then went red on a value that was not in any file, with
# nothing in `git diff` to explain it.
#
# Both directions are wrong and the quiet one is worse: a revert that never
# reaches the interpreter makes a LIVE test look VACUOUS.


def test_a_same_size_revert_is_invisible_to_cpython_cache_invalidation(
    tmp_path: Path,
) -> None:
    """The mechanism itself, reproduced — not the purge call, the FAILURE.

    Asserting that `_purge_bytecode` is invoked would pass against a purge that
    deleted the wrong tree. This pins the property that made the purge necessary:
    two same-length sources written inside one second are indistinguishable to the
    cache check, so nothing but deleting the cache is reliable.
    """
    import py_compile

    module = tmp_path / "subject.py"
    original = "VALUE: int = 6 * 60 * 60\n"
    reverted = "VALUE: int = 3 * 60 * 60\n"
    assert len(original) == len(reverted), (
        "this test's premise is that the two sources are the SAME LENGTH; if they "
        "differ, CPython's size check would notice and the bug would not exist"
    )

    module.write_text(original, encoding="utf-8")
    cached = Path(py_compile.compile(str(module), doraise=True))
    assert cached.is_file()

    # The revert, written with the SAME mtime — which is what an apply/restore
    # inside one second amounts to.
    stat = module.stat()
    module.write_text(reverted, encoding="utf-8")
    os.utime(module, (stat.st_atime, stat.st_mtime))

    header = cached.read_bytes()[:16]
    recompiled = Path(py_compile.compile(str(module), doraise=True))
    assert recompiled.read_bytes()[:16] == header, (
        "the cache header changed, so this platform DOES distinguish the two "
        "writes and the premise no longer holds — re-check whether the purge is "
        "still needed rather than deleting this test"
    )


def test_the_probe_purges_bytecode_around_every_run(tmp_path: Path) -> None:
    """Both sides: before running the child, and after restoring the original.

    The `finally` half is the one that bit. Bytecode written while the revert was
    in place outlives the restore, so the operator's NEXT command imports the
    reverted module — a defect with nothing in `git diff` to explain it.
    """
    source = (REPO_ROOT / "scripts" / "revert_probe.py").read_text(encoding="utf-8")
    assert "def _purge_bytecode()" in source, "the purge helper is gone"
    # Called from the runner (before the child) and from the restore path.
    assert source.count("_purge_bytecode()") >= 3, (
        "the purge must run BEFORE the child and AFTER the restore; only one "
        f"call site is present: {source.count('_purge_bytecode()')}"
    )
    assert 'env["PYTHONDONTWRITEBYTECODE"] = "1"' in source, (
        "the child may still write a .pyc that a later run inherits"
    )
    restore_block = source[source.index("    finally:\n        path.write_text(") :]
    assert "_purge_bytecode()" in restore_block[:900], (
        "the restore path does not purge, so the REVERTED bytecode outlives the "
        "probe — which is the half that actually caused the incident"
    )
