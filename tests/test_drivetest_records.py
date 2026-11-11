"""`drivetest.sh` puts every rip's ripper record in its upload (round 39 lap 1 S10).

The fork's lap 1 S10 is BLOCKING: *"Put each rip's `--diagnostics` record in the
bundle, in the test burn and from now on."* The app's own acceptance bundle has
carried the records since 0.6.65 (``test_session.session_diagnostics_records``;
the 2026-11-10 Full run's bundle listed 26 under ``ripperdiagnostics/``,
``cyanrip@60b545ed:docs/rig-2026-11-10-5cc1c6b/MANIFEST.txt:156-181``). The drive
test's upload did not: cyanrip writes each record in the rips folder's ROOT, and
``pack()`` moves album folders only, so no record of the 2026-11-09 runs reached
an upload (their S9).

These run the real script, as the owner does, in a throwaway home folder: a fake
AppImage, a config naming the rips folder, records old and new, and a FLAC that
must never get in. The drive is never touched (``records`` reads none).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "docs/rig-scripts/drivetest.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("tar") is None,
    reason="needs bash and tar",
)


def _home(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    app = home / "Applications" / "platterpus-x86_64.AppImage"
    app.parent.mkdir(parents=True)
    app.write_text("#!/bin/sh\necho platterpus 0.7.122\n", encoding="utf-8")
    app.chmod(0o755)
    rips = home / "rips"
    rips.mkdir()
    config = home / ".config" / "platterpus" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(f'output_dir = "{rips}"\n', encoding="utf-8")
    return home, rips


def _at(path: Path, text: str, epoch: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (epoch, epoch))
    return path


#: 2026-11-10T12:00:00Z, after the default start of 2026-11-09.
_NOV_10 = 1794312000
#: 2026-11-01T00:00:00Z, before it.
_NOV_01 = 1793491200


def _run(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(home),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        # Skip the systemd-inhibit re-exec: there is no session bus here.
        "DRIVETEST_AWAKE": "1",
    }
    return subprocess.run(  # noqa: S603 — our own script, a fixed argv
        ["bash", str(_SCRIPT), *args],  # noqa: S607 — bash from PATH, as the owner runs it
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_records_packs_every_record_since_the_date_and_no_audio(tmp_path: Path) -> None:
    home, rips = _home(tmp_path)
    new = _at(rips / "cyanrip-diagnostics-20261110T120000Z.json", "{}", _NOV_10)
    beside = _at(
        rips / "album" / "cyanrip-diagnostics-20261110T130000Z-securingpass.json",
        '{"block_crcs": []}',
        _NOV_10,
    )
    old = _at(rips / "cyanrip-diagnostics-20261101T000000Z.json", "{}", _NOV_01)
    _at(rips / "album" / "01.flac", "not audio, but named as audio", _NOV_10)

    done = _run(home, "records")
    assert done.returncode == 0, done.stdout + done.stderr

    upload = home / "platterpus-rig" / "drivetest38" / "platterpusdrivetest38records.tar.gz"
    assert upload.is_file(), done.stdout
    with tarfile.open(upload) as archive:
        names = archive.getnames()
        summary = archive.extractfile(
            "platterpusdrivetest38records/records/RECORDS.txt"
        )
        assert summary is not None
        said = summary.read().decode()
    records = sorted(Path(n).name for n in names if "/records/cyanrip-" in n)
    assert records == sorted([new.name, beside.name])
    assert old.name not in records  # before the start date: not this test's
    assert not [n for n in names if n.lower().endswith(".flac")]
    assert "ripper records: 2 of 2 found" in said


def test_every_upload_carries_the_records_since_its_test_began(tmp_path: Path) -> None:
    """The ordinary uploads too (the test burn's probe, a stopped run), not only
    `records`: one function, `copy_records`, called from `make_upload`."""
    text = _SCRIPT.read_text(encoding="utf-8")
    body = text.split("make_upload() {", 1)[1].split("\n}\n", 1)[0]
    assert 'copy_records "$since" "$stage/records"' in body
    assert "records)  records ;;" in text
