"""The mutation harness has to be trustworthy before its score means anything.

**A measuring instrument nobody measured is the failure this whole subsystem
comes from.** `mutmut` reported success for seven runs while checking nothing,
and the replacement must not be able to do the same — so the properties asserted
here are the ones whose absence would let a sweep lie:

* it can be satisfied by finding nothing → refused by a floor;
* it must never leave a mutated source on disk;
* a mutant it reports as applied must actually have changed the file;
* a suite that catches nothing must score 0, and one that catches everything 100.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import mutation_sweep as ms  # noqa: E402


def test_it_finds_the_mutable_sites_it_claims_to(tmp_path: Path) -> None:
    """Comparisons, booleans and small constants — and nothing else."""
    module = tmp_path / "m.py"
    module.write_text(
        "def f(a, b):\n"
        "    if a < b and b == 2:\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8",
    )
    kinds = sorted({m.kind for m in ms._mutants_for(module)})
    assert kinds == ["bool", "cmp", "const"], kinds


def test_a_string_constant_is_NOT_mutated(tmp_path: Path) -> None:
    """Deliberate. Mutating log wording finds text no test should pin, and every
    test would then 'kill' it for the wrong reason — a mutant that is trivial to
    kill inflates the score while measuring nothing."""
    module = tmp_path / "m.py"
    module.write_text('def f():\n    return "hello"\n', encoding="utf-8")
    assert ms._mutants_for(module) == []


def test_the_edit_is_TEXTUAL_and_touches_only_its_own_line(tmp_path: Path) -> None:
    """`ast.unparse` would reformat the whole module, so a failing test could be
    reacting to the reformatting rather than to the mutation — a mutant that is
    not the mutation."""
    module = tmp_path / "m.py"
    source = "def f(a, b):\n    # a comment that must survive\n    return a < b\n"
    module.write_text(source, encoding="utf-8")
    mutant = next(m for m in ms._mutants_for(module) if m.kind == "cmp")
    out = ms._apply(source, mutant)
    assert out is not None
    assert "# a comment that must survive" in out
    assert out.splitlines()[2].strip() == "return a <= b"


def test_a_word_operator_is_not_matched_inside_an_identifier(tmp_path: Path) -> None:
    """`is` inside `exists` would corrupt the source into something that is not
    the mutation, and whose failure would be attributed to the mutation."""
    module = tmp_path / "m.py"
    source = "def f(exists, other):\n    return exists is other\n"
    module.write_text(source, encoding="utf-8")
    mutant = next(m for m in ms._mutants_for(module) if m.before == "Is")
    out = ms._apply(source, mutant)
    assert out is not None
    assert "exists is not other" in out
    assert "ex is nots" not in out


def _sweep(tmp_path: Path, body: str, test_body: str, **kw: object) -> dict:
    module = tmp_path / "subject.py"
    module.write_text(body, encoding="utf-8")
    test = tmp_path / "test_subject.py"
    test.write_text(test_body, encoding="utf-8")
    return ms.sweep(
        [module],
        [str(test)],
        limit=kw.get("limit", 20),  # type: ignore[arg-type]
        seed=0,
        timeout=120,
    )


def test_a_suite_that_catches_NOTHING_scores_zero(tmp_path: Path) -> None:
    """The score must be able to be bad. A harness that cannot report a failing
    suite is decoration."""
    report = _sweep(
        tmp_path,
        "def f(a, b):\n    return a < b\n",
        "def test_nothing():\n    assert True\n",
    )
    assert report["checked"] >= 1
    assert report["killed"] == 0
    assert report["score"] == 0.0


def test_a_suite_that_catches_EVERYTHING_scores_one(tmp_path: Path) -> None:
    """And it must be able to report a good suite, or the number is not a scale."""
    report = _sweep(
        tmp_path,
        "def f(a, b):\n    return a < b\n",
        "import sys\n"
        "sys.path.insert(0, __file__.rsplit('/', 1)[0])\n"
        "from subject import f\n"
        "def test_boundary():\n"
        "    assert f(1, 1) is False\n"
        "    assert f(0, 1) is True\n",
    )
    assert report["checked"] >= 1
    assert report["survived"] == 0
    assert report["score"] == 1.0


def test_the_source_is_ALWAYS_restored(tmp_path: Path) -> None:
    """Non-negotiable: a mutated source left on disk poisons every later run and
    could be committed."""
    module = tmp_path / "subject.py"
    source = "def f(a, b):\n    return a < b\n"
    module.write_text(source, encoding="utf-8")
    before = hashlib.sha256(source.encode()).hexdigest()
    test = tmp_path / "test_subject.py"
    test.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    ms.sweep([module], [str(test)], limit=20, seed=0, timeout=120)

    after = hashlib.sha256(module.read_bytes()).hexdigest()
    assert after == before, "the harness left the subject mutated on disk"


def test_the_floor_refuses_a_sweep_that_CHECKED_NOTHING(tmp_path: Path) -> None:
    """**The mutmut failure mode, refused by construction.**

    A sweep with no mutants to run must exit non-zero and say NO RESULT, not exit
    0 and read as clean. This is *"can this check be satisfied by finding
    nothing?"* asked of the checker itself.
    """
    module = tmp_path / "subject.py"
    module.write_text(
        'def f():\n    return "no mutable sites here"\n', encoding="utf-8"
    )
    test = tmp_path / "test_subject.py"
    test.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    rc = ms.main(
        [
            "--target",
            str(module.relative_to(REPO_ROOT))
            if module.is_relative_to(REPO_ROOT)
            else str(module),
            "--tests",
            str(test),
            "--min-checked",
            "1",
        ]
    )
    assert rc != 0, "a sweep that checked nothing must not report success"


def test_the_cli_runs_end_to_end_without_touching_project_source(
    tmp_path: Path,
) -> None:
    """End-to-end through the CLI — on a COPY, never on `src/`.

    **The first version pointed at `src/platterpus/ctdb/crc.py`, and that was a
    hazard I introduced rather than found.** The sweep mutates its target in
    place, so a test inside the suite that mutates real project source puts a
    corrupted CRC implementation on disk for the duration of its subprocess.
    Anything reading the tree in that window — another gate, a coverage pass, a
    developer's editor, a second pytest — sees it. The restore is reliable; the
    *window* is the defect, and "reliable enough that nothing has noticed" is not
    a property to depend on for the module that computes archival checksums.

    What this test is actually for is the CLI contract the workflow depends on:
    the argument names, the `checked=` and `score=` lines it reports, and the
    exit code. None of that needs the subject to be ours.
    """
    module = tmp_path / "subject.py"
    module.write_text(
        "def classify(a, b):\n"
        "    if a < b and b > 0:\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8",
    )
    test = tmp_path / "test_subject.py"
    test.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "from subject import classify\n"
        "def test_it():\n"
        "    assert classify(1, 2) is True\n"
        "    assert classify(2, 1) is False\n",
        encoding="utf-8",
    )

    before = hashlib.sha256(module.read_bytes()).hexdigest()
    proc = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "mutation_sweep.py"),
            "--target",
            str(module),
            "--tests",
            str(test),
            "--limit",
            "6",
            "--min-checked",
            "1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert "checked=" in proc.stdout, proc.stdout + proc.stderr
    assert "score=" in proc.stdout, proc.stdout + proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert hashlib.sha256(module.read_bytes()).hexdigest() == before, (
        "the CLI left its target mutated"
    )


@pytest.mark.parametrize("missing", ["src/platterpus/does_not_exist.py"])
def test_a_missing_target_is_an_ERROR_not_an_empty_pass(missing: str) -> None:
    """A typo'd path must not produce a clean sweep over zero modules."""
    assert ms.main(["--target", missing, "--tests", "tests/test_verdict.py"]) == 2


def test_a_sweep_leaves_NO_STALE_BYTECODE_behind(tmp_path: Path) -> None:
    """No `.pyc` for the target survives a sweep.

    **What was OBSERVED, and it is not the same as what is asserted here.** After
    a sweep over `src/platterpus/ctdb/crc.py` on 2026-09-05, six CTDB tests
    failed with that file byte-identical to `git show HEAD:` — sha256 compared,
    not eyeballed. `git status` said clean, `git diff` was empty, the archival CRC
    was wrong, and deleting `__pycache__` fixed it. That corruption is measured.

    **The MECHANISM is inferred, and the reproduction FAILED.** The explanation —
    CPython validates cached bytecode by (mtime, size), so a restore of identical
    size within the same second leaves a mutant's `.pyc` looking valid — is
    plausible and fits every observation. It could not be made deterministic here:
    with all three defences removed, an end-to-end probe still loaded correct
    behaviour, because this filesystem's mtime resolution invalidates the cache on
    its own.

    Saying so rather than shipping the confident version, because *"did I
    reproduce the symptom, or only explain it?"* is the first question `CLAUDE.md`
    asks, and the workflow this harness replaced was left red for a week behind a
    diagnosis that was plausible, specific and wrong.

    **So this asserts the OBSERVABLE the fix removes**, which does discriminate:
    with a naive restore the sweep leaves `sub.cpython-311.pyc` behind, and with
    the fix it leaves none. A stale `.pyc` is the necessary condition for the
    corruption whatever triggers it, so removing it closes the class even where
    the trigger is not pinned.
    """
    pkg = tmp_path / "sweeppkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    module = pkg / "sub.py"
    source = "def f(a, b):\n    return a < b\n"
    module.write_text(source, encoding="utf-8")

    test = tmp_path / "test_sub.py"
    test.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "from sweeppkg.sub import f\n"
        "def test_it():\n"
        "    assert f(1, 2) is True\n",
        encoding="utf-8",
    )

    # Prime a cache the way an ordinary import would, so the sweep is not being
    # asked about a module that has never been compiled — the easy case.
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, {str(tmp_path)!r}); import sweeppkg.sub",
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    assert list((pkg / "__pycache__").glob("sub.*.pyc")), (
        "the cache was never primed, so this test cannot observe it being cleared"
    )

    ms.sweep([module], [str(test)], limit=10, seed=0, timeout=120)

    left = sorted(x.name for x in (pkg / "__pycache__").glob("sub.*.pyc"))
    assert left == [], f"the sweep left compiled bytecode behind: {left}"
    assert module.read_text(encoding="utf-8") == source

    # And the module still behaves correctly when imported fresh — the end-to-end
    # property, kept even though it passes with the fix reverted. It is the thing
    # anyone actually cares about, and a test that only checks the mechanism goes
    # green the day the mechanism stops mattering.
    probe = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, {str(tmp_path)!r});"
            "from sweeppkg.sub import f; print('MUTANT' if f(1, 1) else 'CLEAN')",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert "CLEAN" in probe.stdout, probe.stdout + probe.stderr
