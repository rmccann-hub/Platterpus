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


def _chase_wrapper(signed: bytes, attempts: int = 2) -> bytes:
    """The verified-read chase's record, as `verified_read_chase.py` writes it."""
    out = b""
    for n in range(1, attempts + 1):
        out += (
            f"=== Platterpus verified-read chase: track 16, attempt {n} ===\n"
            "argv: /var/home/someone/.local/bin/cyanrip -d /dev/sr0 -l 16\n"
            "exit status: 0\n"
        ).encode()
        out += signed + b"\n"
    return out


def test_a_chase_wrapper_keeps_each_log_and_redacts_around_them(
    tmp_path: Path,
) -> None:
    """The 2026-10-22 11:45 UTC run: the chase's record named the rig's home
    folder on each argv line, and its five embedded logs, read as ONE signed log,
    failed the check and were kept unredacted. Each embedded log now verifies on
    its own and stays byte for byte; the lines between them are redacted."""
    raw = _bundle(tmp_path)
    folder = next((raw / "album").iterdir())
    (folder / "Album.platterpus-verified-read.txt").write_bytes(
        _chase_wrapper(_SIGNED.read_bytes())
    )
    out = tmp_path / "staged"

    code = evidence_file.main(["stage", str(raw), str(out), "--prefix", "r"])

    filed = (out / "rwholediscverifiedread.txt").read_bytes()
    row = _rows(out)["rwholediscverifiedread.txt"]
    assert code == 0
    assert b"/var/home/someone" not in filed
    assert filed.count(_SIGNED.read_bytes()) == 2, "an embedded log was altered"
    assert row["verification"] == (
        "verified-read wrapper: 2 embedded cyanrip log(s), 2 FUN512 valid"
    )
    assert row["homes"] == "2"


def test_a_tampered_log_inside_a_chase_wrapper_fails_the_filing(
    tmp_path: Path,
) -> None:
    raw = _bundle(tmp_path)
    folder = next((raw / "album").iterdir())
    data = bytearray(_SIGNED.read_bytes())
    data[100] ^= 1
    (folder / "Album.platterpus-verified-read.txt").write_bytes(
        _chase_wrapper(bytes(data), attempts=1)
    )

    assert (
        evidence_file.main(["stage", str(raw), str(tmp_path / "s"), "--prefix", "r"])
        == 1
    )


@pytest.mark.parametrize(
    ("rel", "name"),
    [
        # Section P5's timed rips, one album folder each (0.7.112).
        (
            "album/timing A1 20261022t215702 platterpus-fork-g5f1d036/x CD4.log",
            "timinga1.log",
        ),
        (
            "album/timing B2 20261022t215702 platterpus-fork-gca0f097/x CD4.platterpus.json",
            "timingb2report.json",
        ),
        ("session/run/installripper1628.txt", "installripper1628.txt"),
        # A rip that never finished leaves its files loose under album/.
        (
            "album/full acceptance x 20261021t214510 CD1 (EAC-compatible).log",
            "wholedisceac.log",
        ),
        ("album/full acceptance x 20261021t214510 CD1.log", "wholedisc.log"),
    ],
)
def test_the_round_36_bundles_members_have_filed_names(rel: str, name: str) -> None:
    """Every member of the four 2026-10-21/22 bundles needed a name before any
    could be filed: the timed rips' folders, the install records, and the loose
    files of the run that stopped after 21,600 s."""
    from evidence_names import staged_name

    assert staged_name(rel) == name
