"""Every release file is uploaded while the release is still a draft.

**Why this exists (2026-10-12).** The owner turned on release immutability: once a
GitHub release is published, its tag cannot move and no file can be added to it or
replaced. `release.yml`'s publish step already created each new release as a DRAFT
with every file attached and published it afterwards, which holds under the new
rule. Its other branch did not. When the release already existed, it ran
`gh release upload --clobber` and then published, so a re-run against a release
that was already published would now fail inside the upload with an error that
does not say why.

That branch now finishes a leftover draft and refuses a published release with a
sentence that names the cause. These tests run the step's OWN script, extracted
from `release.yml`, against a fake `gh` that records every call it receives.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
RELEASE_YML: Final[Path] = REPO_ROOT / ".github" / "workflows" / "release.yml"
STEP_NAME: Final[str] = "Publish to GitHub Release"
ASSETS: Final[tuple[str, ...]] = (
    "platterpus-x86_64.AppImage",
    "platterpus-x86_64.AppImage.sha256",
    "platterpus-x86_64.AppImage.sigstore.json",
    "platterpus-x86_64.AppImage.zsync",
    "install.sh",
    "install-appimage.sh",
)


def _step_script() -> str:
    """The step's `run: |` block, dedented, read from `release.yml`."""
    lines = RELEASE_YML.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, ln in enumerate(lines) if ln.strip() == f"- name: {STEP_NAME}"
    )
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body: list[str] = []
    indent: int | None = None
    for line in lines[run_at + 1 :]:
        if line.strip() == "":
            body.append("")
            continue
        here = len(line) - len(line.lstrip(" "))
        if indent is None:
            indent = here
        if here < indent:
            break
        body.append(line[indent:])
    script = "\n".join(body)
    assert "gh release create" in script and "--draft" in script, script[:300]
    return script


def _fake_gh(bin_dir: Path, *, exists: bool, draft: bool) -> Path:
    """A `gh` that logs its argv and answers `release view` as told."""
    log = bin_dir / "gh.log"
    script = f"""#!/bin/bash
echo "$*" >> "{log}"
if [ "$1 $2" = "release view" ]; then
  {"" if exists else "exit 1"}
  case "$*" in
    *isDraft*) echo "{"true" if draft else "false"}" ;;
  esac
  exit 0
fi
exit 0
"""
    gh = bin_dir / "gh"
    gh.write_text(script, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return log


def _run(tmp_path: Path, *, exists: bool, draft: bool) -> tuple[int, str, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = _fake_gh(bin_dir, exists=exists, draft=draft)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "TAG": "v0.7.999",
        "GITHUB_SHA": "0" * 40,
        "GH_TOKEN": "unused",
    }
    done = subprocess.run(
        ["bash", "-e", "-c", _step_script()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return done.returncode, done.stdout + done.stderr, calls


def test_a_new_release_is_created_as_a_draft_with_every_file(tmp_path: Path) -> None:
    code, out, calls = _run(tmp_path, exists=False, draft=False)
    assert code == 0, out
    create = next(c for c in calls if c.startswith("release create"))
    assert "--draft" in create
    for asset in ASSETS:
        assert asset in create, f"{asset} is not uploaded while the release is a draft"
    # Published only after the create that carried every file.
    assert calls.index(create) < calls.index("release edit v0.7.999 --draft=false")
    assert not any(c.startswith("release upload") for c in calls)


def test_a_leftover_draft_is_finished(tmp_path: Path) -> None:
    code, out, calls = _run(tmp_path, exists=True, draft=True)
    assert code == 0, out
    upload = next(c for c in calls if c.startswith("release upload"))
    for asset in ASSETS:
        assert asset in upload
    assert calls.index(upload) < calls.index("release edit v0.7.999 --draft=false")


def test_a_published_release_is_refused_before_any_upload(tmp_path: Path) -> None:
    code, out, calls = _run(tmp_path, exists=True, draft=False)
    assert code == 1, out
    assert "immutable" in out
    assert not any(c.startswith("release upload") for c in calls), calls
    assert not any(c.startswith("release edit") for c in calls), calls


@pytest.mark.parametrize("asset", ASSETS)
def test_every_asset_is_named_in_both_branches(asset: str) -> None:
    """The create and the re-upload carry the same files, so a draft left by a
    failed run is finished with everything a fresh run would have attached."""
    script = _step_script()
    create = script[script.index("gh release create") :]
    upload = script[
        script.index("gh release upload") : script.index("gh release create")
    ]
    assert asset in create and asset in upload
