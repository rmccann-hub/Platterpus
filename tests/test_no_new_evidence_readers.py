"""No test, tool or check opens a run-evidence path (HR-2 §2).

**Why.** HR-2 moves run evidence off the default branch onto `evidence`. Anything
that opens one of those files from the working tree then fails, or worse, passes
on nothing because its input is missing. So every reader is pointed at a fixture
under `tests/fixtures/evidence/` first (through `tests/evidence_paths.py`, which
names the original path), and from the move on this sweep refuses a new one.

**What counts as opening an evidence path.** A string constant in Python code
under `src/`, `scripts/`, `tests/` or `build/`, or a line of a workflow or shell
script, that names a moving folder or file, or that is the fragment a path to one
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

**The allowlist only shrinks.** `_READERS_BEFORE_THE_MOVE` holds the readers
measured when this sweep landed; HR-2 landing step 2 converts them and empties
it. A listed file that no longer reads evidence fails too, so the list cannot
outlive its entries.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evidence_manifest  # noqa: E402 - needs the path line above
from laplang.evidence import parse_manifest  # noqa: E402

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

#: Measured when this sweep landed (HR-2 landing step 1, 2026-10-14). Step 2
#: converts each reader and removes it from here; the list never grows.
_READERS_BEFORE_THE_MOVE: Final[frozenset[str]] = frozenset(
    {
        "src/platterpus/uiscript/run_estimate.py",
        "tests/test_album_loudness.py",
        "tests/test_cache_probe.py",
        "tests/test_ctdb_partial_rip.py",
        "tests/test_cue_validate.py",
        "tests/test_disc_identity.py",
        "tests/test_drive_media.py",
        "tests/test_eac_log_export.py",
        "tests/test_early_failure_log_report.py",
        "tests/test_export_redaction.py",
        "tests/test_ladder_trigger.py",
        "tests/test_one_frame_match.py",
        "tests/test_outcome_vocabulary.py",
        "tests/test_parity.py",
        "tests/test_parsers_cyanrip_log.py",
        "tests/test_partial_summary_after_autofix.py",
        "tests/test_read_speed_ladder.py",
        "tests/test_record_fate.py",
        "tests/test_rig_check.py",
        "tests/test_rip_addendum.py",
        "tests/test_rip_audit.py",
        "tests/test_rip_estimate.py",
        "tests/test_rip_report.py",
        "tests/test_rip_worker.py",
        "tests/test_ripper_standing.py",
        "tests/test_secure_reread_can_converge.py",
        "tests/test_securing_pass.py",
        "tests/test_track5_autofix_vs_eac.py",
        "tests/test_ui_main_window.py",
        "tests/test_uiscript_applog_verbs.py",
        "tests/test_uiscript_artifact_grading.py",
        "tests/test_uiscript_artifact_verbs.py",
        "tests/test_uiscript_permutation_verbs.py",
        "tests/test_uiscript_pregap_verbs.py",
        "tests/test_uiscript_rip_verbs.py",
        "tests/test_uiscript_run_estimate.py",
        "tests/test_unknown_disc_acceptance.py",
        "tests/test_verdict.py",
    }
)

#: The fragment a run-folder path is built from: the end of an f-string's
#: constant part (`"artifactsround"` before `{n}`), or a glob over the folders
#: (`"artifactsround*/*report.json"`).
_FRAGMENT: Final[re.Pattern[str]] = re.compile(r"artifacts-?round-?(?:$|[*?\[{])")


def moving_names() -> list[str]:
    """What moves, as the names a reader would write: each folder and file."""
    names = set(evidence_manifest.MOVING_FOLDERS) | set(evidence_manifest.MOVING_FILES)
    manifest = REPO_ROOT / "docs" / "evidence-manifest.tsv"
    if manifest.is_file():
        rows, _ = parse_manifest(manifest.read_text(encoding="utf-8"))
        names |= {path.rsplit("/", 1)[0] for path in rows}
    return sorted(names)


def _needles() -> list[str]:
    """The distinctive tail of each name: a reader may join the path in parts."""
    return sorted({name.rsplit("/", 1)[-1] for name in moving_names()})


def names_evidence(text: str, needles: list[str]) -> bool:
    if any(ch.isspace() for ch in text):
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
    for top in ("src", "scripts", "tests", "build"):
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
    assert len(scanned()) >= 500
    assert len(moving_names()) >= 16
    for name in moving_names():
        assert (REPO_ROOT / name).exists() or (
            REPO_ROOT / "docs" / "evidence-manifest.tsv"
        ).is_file(), name


def test_no_code_opens_an_evidence_path_outside_the_allowlist() -> None:
    found = readers()
    new = {f: hits for f, hits in found.items() if f not in _READERS_BEFORE_THE_MOVE}
    assert not new, (
        "These open run evidence, which HR-2 moves off the default branch. Make a "
        "fixture with scripts/evidence_fixtures.py and read it through "
        "tests/evidence_paths.py:\n"
        + "\n".join(f"  {f}:{n}  {s!r}" for f, hits in new.items() for n, s in hits)
    )


def test_the_allowlist_holds_only_readers_that_still_read() -> None:
    stale = _READERS_BEFORE_THE_MOVE - set(readers())
    assert not stale, f"no longer read evidence, remove from the allowlist: {stale}"


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
