"""Tests for scripts/evidence_file.py — filing a run, counted by the tool (R16).

HR-2 point 9: home folders, the hostname and the owner's name are replaced
"through its filing tool, counting each replacement", and signed logs are
verified first and kept as written. These build a small bundle in the shape a
Full run's export has and file it.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evidence_file  # noqa: E402

_SIGNED = Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference.log"


def _bundle(root: Path) -> Path:
    raw = root / "bundle"
    album = raw / "album" / "full acceptance (2026)"
    album.mkdir(parents=True)
    (album / "Album.log").write_bytes(_SIGNED.read_bytes())
    (raw / "DIAGNOSTICS.txt").write_text(
        "Linux rigbox 6.11.4-bazzite #1 SMP\nconfig in /var/home/someone/.config\n"
        "ripped by Ada Lovelace on rigbox\n",
        encoding="utf-8",
    )
    (raw / "session" / "run").mkdir(parents=True)
    (raw / "session" / "run" / "transcript.txt").write_text("ok\n", encoding="utf-8")
    (raw / "session" / "run" / "shot.png").write_bytes(b"\x89PNG")
    return raw


def _rows(out: Path) -> dict[str, dict[str, str]]:
    with (out.parent / f"{out.name}-FILING.tsv").open(encoding="utf-8") as fh:
        return {r["file"]: r for r in csv.DictReader(fh, delimiter="\t") if r["file"]}


def test_filing_replaces_and_counts_homes_hosts_and_names(tmp_path: Path) -> None:
    names = tmp_path / "names"
    names.write_text("Ada Lovelace\n", encoding="utf-8")
    out = tmp_path / "staged"

    code = evidence_file.main(
        [
            "stage",
            str(_bundle(tmp_path)),
            str(out),
            "--prefix",
            "round99full",
            "--names",
            str(names),
        ]
    )
    rows = _rows(out)

    assert code == 0
    diag = (out / "round99fulldiagnostics.txt").read_text(encoding="utf-8")
    assert (
        diag
        == "Linux host 6.11.4-bazzite #1 SMP\nconfig in ~/.config\nripped by the owner on host\n"
    )
    assert rows["round99fulldiagnostics.txt"]["homes"] == "1"
    assert rows["round99fulldiagnostics.txt"]["hosts"] == "2"
    assert rows["round99fulldiagnostics.txt"]["names"] == "1"
    assert (
        rows["round99fulldiagnostics.txt"]["sha256 before"]
        != rows["round99fulldiagnostics.txt"]["sha256 after"]
    )


def test_a_signed_log_is_verified_first_and_kept_byte_for_byte(tmp_path: Path) -> None:
    out = tmp_path / "staged"
    evidence_file.main(["stage", str(_bundle(tmp_path)), str(out), "--prefix", "r"])

    assert (out / "rwholedisc.log").read_bytes() == _SIGNED.read_bytes()
    assert _rows(out)["rwholedisc.log"]["verification"].startswith(
        "cyanrip FUN512 valid"
    )


def test_a_tampered_signed_log_fails_the_filing(tmp_path: Path) -> None:
    raw = _bundle(tmp_path)
    log = next((raw / "album").rglob("*.log"))
    data = bytearray(log.read_bytes())
    data[100] ^= 1
    log.write_bytes(bytes(data))

    assert (
        evidence_file.main(["stage", str(raw), str(tmp_path / "s"), "--prefix", "r"])
        == 1
    )


def test_without_a_name_list_the_record_says_names_were_not_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence_file.main(
        [
            "stage",
            str(_bundle(tmp_path)),
            str(tmp_path / "s"),
            "--prefix",
            "r",
            "--names",
            str(tmp_path / "absent"),
        ]
    )
    assert "names not checked" in capsys.readouterr().out


def test_a_member_with_no_filed_name_is_refused_not_guessed(tmp_path: Path) -> None:
    raw = _bundle(tmp_path)
    (raw / "surprise.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="no filed name"):
        evidence_file.main(["stage", str(raw), str(tmp_path / "s"), "--prefix", "r"])


def test_commit_builds_an_evidence_commit_and_its_rows(tmp_path: Path) -> None:
    out = tmp_path / "staged"
    evidence_file.main(["stage", str(_bundle(tmp_path)), str(out), "--prefix", "r"])
    clone = tmp_path / "clone"
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    env = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(
        ["git", *env, "-C", str(clone), "commit", "-q", "--allow-empty", "-m", "base"],
        check=True,
    )
    parent = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    sha = evidence_file.commit(
        clone, out, "docs/handshake/artifactsround99", parent, "2026-10-16T00:00:00Z"
    )

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(clone), *args], capture_output=True, text=True, check=True
        ).stdout

    assert (
        git("log", "-1", "--format=%an <%ae> %P", sha).strip()
        == f"evidence <evidence@invalid> {parent}"
    )
    filed = git("ls-tree", "-r", "--name-only", sha).split()
    assert sorted(filed) == sorted(
        f"docs/handshake/artifactsround99/{p.name}" for p in out.iterdir()
    )
    rows = (
        (tmp_path / "staged-manifest-rows.tsv").read_text(encoding="utf-8").splitlines()
    )
    assert len(rows) == len(filed) and all(r.split("\t")[3] == sha for r in rows)
