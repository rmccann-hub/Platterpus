"""The fixture maker for run evidence (HR-2 §2), and its check.

Every evidence file a test reads becomes a fixture before the move, made one way
(``scripts/evidence_fixtures.py``) so each carries proof of its source: a copy
hashes to it, an extract's sidecar names its hash. These drive the maker on a
throwaway tree, because the real evidence is what the move takes away.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evidence_fixtures.py"


@pytest.fixture
def ef(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The maker, pointed at a scratch repository under ``tmp_path``."""
    spec = importlib.util.spec_from_file_location("evidence_fixtures_script", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["evidence_fixtures_script"] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "FIXTURE_ROOT", tmp_path / "tests/fixtures/evidence")
    monkeypatch.setattr(module, "MANIFEST", tmp_path / "docs/evidence-manifest.tsv")
    return module


def _put(root: Path, rel: str, data: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


LOG = "docs/handshake/artifactsround99/round99full.log"
REPORT = "docs/handshake/artifactsround99/round99fullreport.json"
APPLOG = "docs/handshake/artifactsround99/round99fullplatterpusapplog1.txt"


def test_a_copy_is_byte_for_byte_and_checks(ef: ModuleType, tmp_path: Path) -> None:
    _put(tmp_path, LOG, b"Tracks:\x00 bytes kept as they are\n")
    made = ef.make_copy(LOG)
    assert made.read_bytes() == (tmp_path / LOG).read_bytes()
    assert ef.check() == []


def test_a_slim_report_empties_debug_lines_and_counts_them(
    ef: ModuleType, tmp_path: Path
) -> None:
    report = {"rip": {"x": 1}, "debug": {"lines": ["a", "b", "c"], "scope": "s"}}
    _put(tmp_path, REPORT, json.dumps(report).encode())
    made = ef.make_slim_report(REPORT)
    slim = json.loads(made.read_text(encoding="utf-8"))
    assert slim["rip"] == {"x": 1}
    assert slim["debug"]["lines"] == []
    assert slim["debug"]["lines_removed_by_extract"] == 3
    sidecar = json.loads(ef.sidecar_path(REPORT).read_text(encoding="utf-8"))
    assert sidecar["removed_count"] == 3
    assert sidecar["source_path"] == REPORT
    assert ef.check() == []


def test_a_slim_applog_drops_progress_lines_and_says_how_many(
    ef: ModuleType, tmp_path: Path
) -> None:
    lines = [
        "banner\n",
        "2026 DEBUG x: cyanrip │ Ripping track 3, progress - 40.59%\n",
        "2026 INFO x: kept\n",
        "2026 DEBUG x: cyanrip │ Ripping track 3, progress - 41%\n",
    ]
    _put(tmp_path, APPLOG, "".join(lines).encode())
    text = ef.make_slim_applog(APPLOG).read_text(encoding="utf-8")
    assert "progress -" not in text
    assert text.startswith("banner\n2026 INFO x: kept\n")
    assert "[evidence extract: 2 cyanrip progress line(s) removed" in text


def test_check_refuses_a_copy_that_differs_from_its_source(
    ef: ModuleType, tmp_path: Path
) -> None:
    _put(tmp_path, LOG, b"original\n")
    ef.make_copy(LOG).write_bytes(b"edited\n")
    problems = ef.check()
    assert len(problems) == 1 and "byte for byte" in problems[0]


def test_check_refuses_an_extract_whose_source_changed(
    ef: ModuleType, tmp_path: Path
) -> None:
    _put(tmp_path, REPORT, b'{"debug": {"lines": ["a"]}}')
    ef.make_slim_report(REPORT)
    _put(tmp_path, REPORT, b'{"debug": {"lines": ["b"]}}')
    problems = ef.check()
    assert len(problems) == 1 and "extract names source sha256" in problems[0]


def test_after_the_move_the_source_is_read_from_the_manifest(
    ef: ModuleType, tmp_path: Path
) -> None:
    data = b"moved away\n"
    _put(tmp_path, LOG, data)
    ef.make_copy(LOG)
    (tmp_path / LOG).unlink()
    assert any("neither in the working tree" in p for p in ef.check())
    manifest = tmp_path / "docs/evidence-manifest.tsv"
    manifest.write_text(
        "path\tbytes\tsha256\tevidence_commit\tlast_default_commit\n"
        f"{LOG}\t{len(data)}\t{ef.sha256_of(data)}\t{'a' * 40}\t{'b' * 40}\n",
        encoding="utf-8",
    )
    assert ef.check() == []


def test_check_exits_non_zero_when_there_is_nothing_to_check(ef: ModuleType) -> None:
    """A check that examined no fixture has proved nothing (the floor)."""
    assert ef.main(["check"]) == 1


def test_a_path_outside_the_repository_is_refused(ef: ModuleType) -> None:
    with pytest.raises(SystemExit):
        ef.fixture_path("../etc/passwd")
    with pytest.raises(SystemExit):
        ef.fixture_path("/etc/passwd")
