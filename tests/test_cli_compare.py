"""Tests for the --compare / --assemble-best-of terminal glue (cli_compare.py)."""

from __future__ import annotations

import json
from pathlib import Path

from platterpus import cli_compare


def _report(disc_id: str, tracks: list[dict]) -> dict:
    return {
        "schema_version": 9,
        "generator": {"name": "platterpus", "version": "0.4.24"},
        "generated_at": "2026-07-08T00:00:00",
        "rip": {"musicbrainz_disc_id": disc_id, "creation_date": "2026-07-08"},
        "disc": {"musicbrainz_release_id": "REL"},
        "tracks": tracks,
    }


def _t(
    number: int,
    crc: str,
    *,
    verified: bool = True,
    offset: int | None = None,
    filename: str | None = None,
) -> dict:
    return {
        "number": number,
        "filename": filename or f"{number:02d}.flac",
        "copy_crc": crc,
        "accuraterip_verified": verified,
        "accuraterip": {
            "v1": {"confidence": 200} if verified else None,
            "v2": None,
            "offset_450": {"confidence": offset} if offset is not None else None,
        },
    }


def _write(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report), encoding="utf-8")


def test_compare_identical_exits_zero(tmp_path: Path, capsys) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write(a, _report("D", [_t(1, "AA"), _t(2, "BB")]))
    _write(b, _report("D", [_t(1, "AA"), _t(2, "BB")]))
    code = cli_compare.run_compare(a, b)
    assert code == 0
    assert "identical" in capsys.readouterr().out.lower()


def test_compare_differences_exit_one(tmp_path: Path, capsys) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write(a, _report("D", [_t(1, "AA", verified=True)]))
    _write(b, _report("D", [_t(1, "BB", verified=False, offset=200)]))
    code = cli_compare.run_compare(a, b)
    assert code == 1
    out = capsys.readouterr().out
    assert "Best-of plan" in out  # plan preview shown when there are differences


def test_compare_missing_file_exits_two(tmp_path: Path, capsys) -> None:
    a = tmp_path / "a.json"
    _write(a, _report("D", [_t(1, "AA")]))
    code = cli_compare.run_compare(a, tmp_path / "nope.json")
    assert code == 2
    assert "error" in capsys.readouterr().out.lower()


def test_assemble_best_of_copies(tmp_path: Path, capsys) -> None:
    dir_a = tmp_path / "A"
    dir_b = tmp_path / "B"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "01.flac").write_text("a1", encoding="utf-8")
    (dir_b / "01.flac").write_text("b1", encoding="utf-8")
    a = dir_a / "r.json"
    b = dir_b / "r.json"
    _write(a, _report("D", [_t(1, "AA", verified=True, filename="01.flac")]))
    _write(
        b, _report("D", [_t(1, "BB", verified=False, offset=200, filename="01.flac")])
    )
    dest = tmp_path / "best"
    code = cli_compare.run_assemble_best_of(dest, a, b)
    assert code == 0
    # track 1: A is the exact match → dest holds A's bytes.
    assert (dest / "01.flac").read_text() == "a1"


def test_assemble_refuses_different_discs(tmp_path: Path, capsys) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write(a, _report("DISC_A", [_t(1, "AA")]))
    _write(b, _report("DISC_B", [_t(1, "AA")]))
    code = cli_compare.run_assemble_best_of(tmp_path / "best", a, b)
    assert code == 2
    assert "different disc" in capsys.readouterr().out.lower()


def test_assemble_missing_report_exits_two(tmp_path: Path) -> None:
    code = cli_compare.run_assemble_best_of(
        tmp_path / "best", tmp_path / "x.json", tmp_path / "y.json"
    )
    assert code == 2


def test_compare_different_discs_skips_best_of_plan(tmp_path: Path, capsys) -> None:
    # For different discs, the per-track "better master" plan + assemble hint must
    # NOT be offered (assemble refuses across discs, so it would mislead).
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write(a, _report("DISC_A", [_t(1, "AA", verified=True)]))
    _write(b, _report("DISC_B", [_t(1, "BB", verified=False, offset=200)]))
    cli_compare.run_compare(a, b)
    out = capsys.readouterr().out
    assert "DIFFERENT discs" in out
    assert "Best-of plan" not in out
    assert "--assemble-best-of" not in out


def test_assemble_reports_copy_failure_exit_one(tmp_path: Path, capsys) -> None:
    # A source FLAC is missing → the copy fails; the run reports it and exits 1.
    dir_a = tmp_path / "A"
    dir_b = tmp_path / "B"
    dir_a.mkdir()
    dir_b.mkdir()
    # No 01.flac written in either folder — the copy has nothing to copy.
    a = dir_a / "r.json"
    b = dir_b / "r.json"
    _write(a, _report("D", [_t(1, "AA", verified=True, filename="01.flac")]))
    _write(
        b, _report("D", [_t(1, "BB", verified=False, offset=200, filename="01.flac")])
    )
    code = cli_compare.run_assemble_best_of(tmp_path / "best", a, b)
    assert code == 1
    assert "could not be copied" in capsys.readouterr().out.lower()
