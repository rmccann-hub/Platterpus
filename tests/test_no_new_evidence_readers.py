"""No tool, check or product code opens a run-evidence path (HR-2 §2).

**Why.** HR-2 moves run evidence off the default branch onto `evidence`. Anything
that opens one of those files from the working tree then fails, or worse, passes
on nothing because its input is missing. So every reader is pointed at a fixture
under `tests/fixtures/evidence/` first (through `tests/evidence_paths.py`, which
names the original path), and from the move on this sweep refuses a new one.

**Tests are checked where it counts, at run time** (`tests/evidence_guard.py`,
wired as an autouse fixture in `conftest.py`): a test names an evidence file by
its original path on purpose, as provenance, and reads the fixture, so the name
alone cannot tell a reader from a label. What a test actually opens can. This
sweep covers what that cannot: tools, CI, product code.

**What counts as opening an evidence path.** A string constant in Python code
under `src/`, `scripts/` or `build/`, or a line of a workflow or shell script,
that names a moving folder or file, or that is the fragment a path to one
is built from (`"artifactsround"` before an f-string's number). The moving set is
the enumerated list in `scripts/evidence_manifest.py` plus every folder the
manifest names once it exists. Not counted:

* docstrings and prose: a constant with whitespace in it is a sentence that
  mentions a path, not a path (a lap citation in a `why` field, for instance);
* the argument of `evidence(...)` / `evidence_dir(...)`, which reads the fixture;
* the files that define the moving set and the fixture layout.

**What it cannot see, said rather than implied.** A reader that names no
evidence path at all: a walk of the whole tree (`docs.rglob("*.log")` in
`test_drive_control`) reaches evidence without naming it. Such a reader is found
the way HR-2 §2 says every reader is found, by running the suite in a scratch
clone with the moving files absent; this sweep is the cheap guard on the common
case, not a replacement for that run.

**Labels, named with their reason.** `_LABELS` holds the strings that name an
evidence path without opening it, each with why; a listed file that no longer
names one fails, so the list cannot outlive its entries. The 38 readers measured
when this sweep landed were converted in HR-2 landing step 2 (2026-10-14).
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evidence_manifest  # needs the path line above
from laplang.evidence import parse_manifest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

#: The files that define what moves and where its fixtures live. They name
#: evidence paths in order to say what they are; none of them opens one.
_DEFINERS: Final[frozenset[str]] = frozenset(
    {
        "scripts/evidence_manifest.py",
        "scripts/evidence_fixtures.py",
        "tests/evidence_paths.py",
        "tests/test_no_new_evidence_readers.py",
    }
)

#: Calls whose string argument is the ORIGINAL path of a fixture, not a read of it.
_FIXTURE_CALLS: Final[frozenset[str]] = frozenset({"evidence", "evidence_dir"})

#: Files that name an evidence path as a LABEL, never opening it, with the reason.
_LABELS: Final[dict[str, str]] = {
    "src/platterpus/uiscript/run_estimate.py": (
        "MEASURED_FROM names where the run the table was measured from was "
        "filed; tests/test_uiscript_run_estimate.py re-derives the table from "
        "its fixture at that path"
    ),
}

#: The fragment a run-folder path is built from: the end of an f-string's
#: constant part (`"artifactsround"` before `{n}`), or a glob over the folders
#: (`"artifactsround*/*report.json"`).
_FRAGMENT: Final[re.Pattern[str]] = re.compile(r"artifacts-?round-?(?:$|[*?\[{])")


def moving_names() -> list[str]:
    """What moves, as the names a reader would write: each folder, plus every
    folder the manifest names once it exists."""
    names = set(evidence_manifest.MOVING_FOLDERS)
    manifest = REPO_ROOT / "docs" / "evidence-manifest.tsv"
    if manifest.is_file():
        rows, _ = parse_manifest(manifest.read_text(encoding="utf-8"))
        names |= {path.rsplit("/", 1)[0] for path in rows}
    return sorted(names)


def _needles() -> list[str]:
    """What to look for: a run folder by its distinctive name (a reader may join
    the path in parts), any other folder by its whole path. `outbound/artifacts`
    moves too (HR-2.1 a), and a needle of `artifacts` would match half the tree."""
    needles: set[str] = set()
    for name in moving_names():
        tail = name.rsplit("/", 1)[-1]
        needles.add(tail if "round" in tail else name + "/")
    return sorted(needles)


def names_evidence(text: str, needles: list[str]) -> bool:
    if any(ch.isspace() for ch in text):
        return False
    # A file that stays on the default branch is not evidence, wherever it sits
    # (HR-2 §5a, HR-2.1 a): the lap checker reads lsl-amendments-1.md by path.
    if any(text.endswith(stay) for stay in evidence_manifest.STAYS):
        return False
    return bool(_FRAGMENT.search(text)) or any(n in text for n in needles)


def _docstring_ids(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
            ):
                found.add(id(body[0].value))
    return found


def _fixture_arg_ids(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name in _FIXTURE_CALLS:
            for arg in ast.walk(node):
                found.add(id(arg))
    return found


def python_hits(path: Path, needles: list[str]) -> Iterator[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    skip = _docstring_ids(tree) | _fixture_arg_ids(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in skip
            and names_evidence(node.value, needles)
        ):
            yield node.lineno, node.value


def text_hits(path: Path, needles: list[str]) -> Iterator[tuple[int, str]]:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for token in line.split():
            if names_evidence(token.strip("\"'`;(),"), needles):
                yield number, token


def scanned() -> list[Path]:
    files: list[Path] = []
    for top in ("src", "scripts", "build"):
        files += [
            p
            for p in (REPO_ROOT / top).rglob("*.py")
            if "fixtures" not in p.relative_to(REPO_ROOT).parts
        ]
        files += list((REPO_ROOT / top).rglob("*.sh"))
    files += list((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    return sorted(set(files))


def readers() -> dict[str, list[tuple[int, str]]]:
    needles = _needles()
    found: dict[str, list[tuple[int, str]]] = {}
    for path in scanned():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in _DEFINERS:
            continue
        hits = list(
            python_hits(path, needles)
            if path.suffix == ".py"
            else text_hits(path, needles)
        )
        if hits:
            found[rel] = hits
    return found


def test_the_sweep_scans_the_tree_and_knows_what_moves() -> None:
    """Floors: a sweep over no files, or with nothing to look for, passes on nothing."""
    assert len(scanned()) >= 250  # 291 on 2026-10-14: src, scripts, build, workflows
    assert len(moving_names()) >= 11
    for name in moving_names():
        assert (REPO_ROOT / name).exists() or (
            REPO_ROOT / "docs" / "evidence-manifest.tsv"
        ).is_file(), name


def test_no_tool_or_product_code_names_an_evidence_path_but_its_labels() -> None:
    found = readers()
    new = {f: hits for f, hits in found.items() if f not in set(_LABELS)}
    assert not new, (
        "These name run evidence, which HR-2 moves off the default branch. A tool "
        "reads it through laplang.evidence.Fetcher; a label goes in _LABELS with "
        "its reason:\n"
        + "\n".join(f"  {f}:{n}  {s!r}" for f, hits in new.items() for n, s in hits)
    )


def test_every_listed_label_still_names_an_evidence_path() -> None:
    stale = set(_LABELS) - set(readers())
    assert not stale, f"no longer name evidence, remove from _LABELS: {stale}"


def test_the_detector_tells_a_path_from_a_sentence_and_a_fixture_call(
    tmp_path: Path,
) -> None:
    """Non-triviality: each kind of reference is classified as the docstring says."""
    needles = _needles()
    sample = tmp_path / "sample.py"
    sample.write_text(
        '"""Reads docs/handshake/artifactsround32/a.log."""\n'
        "from pathlib import Path\n"
        'A = Path("docs/handshake/artifactsround32/a.log")\n'
        'B = Path("docs") / "handshake" / "artifactsround30"\n'
        'C = f"docs/handshake/artifactsround{32}/x"\n'
        'D = "see docs/handshake/artifactsround32/a.log for the run"\n'
        'E = evidence("docs/handshake/artifactsround32/a.log")\n'
        'F = "docs/handshake/artifactsround99/made-up.log"\n'
        'G = sorted(ROOT.glob("docs/handshake/artifactsround*/*report.json"))\n',
        encoding="utf-8",
    )
    lines = sorted(n for n, _ in python_hits(sample, needles))
    assert lines == [3, 4, 5, 9], lines
    wf = tmp_path / "w.yml"
    wf.write_text(
        "# docs/handshake/artifactsround32 in a comment\n"
        "  run: cat docs/handshake/artifactsround32/a.log\n",
        encoding="utf-8",
    )
    assert [n for n, _ in text_hits(wf, needles)] == [2]


def test_the_run_time_guard_sees_an_open_of_an_original_and_nothing_else() -> None:
    """Non-triviality of `tests/evidence_guard.py`: an open of a moving file is
    recorded; its fixture, a run folder's README and an unrelated file are not."""
    import evidence_guard

    moving = (
        REPO_ROOT
        / "docs/handshake/outbound/artifacts/round-15-lap-13-run-transcript.txt"
    )
    folder = REPO_ROOT / evidence_manifest.MOVING_FOLDERS[0]
    assert evidence_guard.evidence_path(moving) == str(moving)
    assert evidence_guard.evidence_path(folder / "x.log") == str(folder / "x.log")
    assert evidence_guard.evidence_path(folder / "README.md") is None
    spec = REPO_ROOT / sorted(evidence_manifest.STAYS)[0]
    assert evidence_guard.evidence_path(spec) is None  # HR-2.1 a: it stays
    fixture = (
        REPO_ROOT
        / "tests"
        / "fixtures"
        / "evidence"
        / "docs/handshake/outbound/artifacts/round-15-lap-13-run-transcript.txt"
    )
    assert evidence_guard.evidence_path(fixture) is None
    assert evidence_guard.evidence_path(REPO_ROOT / "CHANGELOG.md") is None
    evidence_guard.install()
    evidence_guard.seen.clear()
    if moving.is_file():  # before the move: a real open is seen
        moving.read_bytes()
        assert evidence_guard.seen == [str(moving)]
    evidence_guard.seen.clear()  # this test opened it on purpose


#: Every test marked `tree_walk` (HR-2 §2: a whole-tree sweep that may open run
#: evidence in passing and depends on none of it). A ratchet: a new entry is a
#: decision to make in review, so it cannot become the quiet way round the guard.
_TREE_WALKS: Final[frozenset[str]] = frozenset(
    {
        "test_cited_commits_are_reachable.py::test_every_lap_that_names_its_commit_by_subject_resolves_through_head",
        "test_cited_commits_are_reachable.py::test_the_paraphrased_subjects_are_still_paraphrases",
        "test_critical_rules_are_enforced.py::test_no_file_carries_an_unresolved_conflict_marker",
        "test_doc_index_completeness.py::test_no_doc_reuses_a_section_id",
        "test_doc_index_completeness.py::test_no_prose_cites_a_generated_document_by_line_number",
        "test_doc_links.py::test_every_relative_doc_link_resolves",
        "test_doc_version_stamps.py::test_every_documented_kdd_range_ends_at_the_last_real_kdd",
        "test_regex_bounded_time.py::test_the_wire_field_rewrite_agrees_on_the_lines_laps_carry",
    }
)


def test_the_tree_walk_marker_is_on_exactly_the_reviewed_sweeps() -> None:
    marked: set[str] = set()
    for path in sorted((REPO_ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for deco in node.decorator_list:
                if ast.unparse(deco) == "pytest.mark.tree_walk":
                    marked.add(f"{path.name}::{node.name}")
    assert marked == set(_TREE_WALKS), (
        f"added: {sorted(marked - _TREE_WALKS)}; gone: {sorted(_TREE_WALKS - marked)}"
    )
