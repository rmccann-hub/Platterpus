"""Tests for install.sh — the one-file end-user installer.

We can't run a real install in CI (Distrobox, network, a real AppImage), so we
verify shape, help, syntax, and that --dry-run narrates the three steps without
touching the filesystem. The download's checks are exercised for real, against
a fake release served by a stand-in `curl` (see the second half of this file).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "install.sh"


def _run(
    args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_script_exists_and_executable() -> None:
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK), "install.sh is not executable"


def test_passes_bash_syntax_check() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_help_shows_usage() -> None:
    result = _run(["--help"])
    assert result.returncode == 0
    assert "install.sh" in result.stdout
    assert "--appimage" in result.stdout
    assert "--no-host" in result.stdout


def test_dry_run_narrates_three_steps_without_touching_fs(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["XDG_DATA_HOME"] = str(tmp_path / ".local" / "share")
    result = _run(["--dry-run", "--yes"], env=env)
    assert result.returncode == 0, result.stderr
    # The three phases are announced...
    assert "1/3" in result.stdout and "2/3" in result.stdout and "3/3" in result.stdout
    # ...and everything is a DRY-RUN line, so nothing was created under HOME.
    assert "DRY-RUN" in result.stdout
    assert not (tmp_path / "Applications").exists()


def test_unknown_flag_errors() -> None:
    result = _run(["--bogus"])
    assert result.returncode != 0


# ==========================================================================
# The download is checked before it is installed (configuration audit A16)
# ==========================================================================
#
# install.sh used to `curl` the newest release's AppImage straight into
# ~/Applications and mark it executable, checking nothing, while the in-app
# updater checks every update against the release's .sha256 and its build
# attestation, fail-closed. The maintainer chose (2026-09-28, H1 (a)): check the
# .sha256 always, and the attestation whenever the GitHub CLI is installed.
#
# These run the real script end to end with `--no-host`. Only its edges are
# fake: `curl` serves a fake release from disk, `gh` answers pass or fail, and
# the desktop-integration script is a stub that records what it was given.

#: Every command install.sh and the fakes below run. The sandbox PATH holds only
#: these, so a real `gh` on the machine running the tests (GitHub's hosted
#: runners all have one) can neither stand in for the fake nor hide its absence.
_TOOLS: Final[tuple[str, ...]] = (
    "bash",
    "grep",
    "head",
    "cut",
    "chmod",
    "mkdir",
    "mktemp",
    "rm",
    "mv",
    "sha256sum",
    "sed",
    "cat",
    "dirname",
    "tr",
    "awk",
    "cp",
)

_ASSET: Final[str] = "platterpus-x86_64.AppImage"
_BASE_URL: Final[str] = "https://example.invalid/releases/download/v9.9.9/"
_PAYLOAD: Final[bytes] = b"#!/bin/sh\necho 'not really an AppImage'\n"
_OLD_INSTALL: Final[bytes] = b"the AppImage that was already installed\n"

#: Serves a file from $FAKE_RELEASE for each URL install.sh asks for, and fails
#: the way `curl -f` does on a 404 when that file is absent.
_FAKE_CURL: Final[str] = r"""#!@BASH@
out="" url=""
while [ $# -gt 0 ]; do
    case "$1" in
        -o) shift; out="$1" ;;
        http*) url="$1" ;;
    esac
    shift
done
case "$url" in
    */releases) src="$FAKE_RELEASE/releases.json" ;;
    *.AppImage) src="$FAKE_RELEASE/platterpus-x86_64.AppImage" ;;
    *.AppImage.sha256) src="$FAKE_RELEASE/platterpus-x86_64.AppImage.sha256" ;;
    *.AppImage.sigstore.json) src="$FAKE_RELEASE/platterpus-x86_64.AppImage.sigstore.json" ;;
    *) echo "fake curl: unexpected URL $url" >&2; exit 2 ;;
esac
if [ ! -f "$src" ]; then
    echo "curl: (22) The requested URL returned error: 404" >&2
    exit 22
fi
if [ -n "$out" ]; then cp "$src" "$out"; else cat "$src"; fi
"""

#: Answers install.sh's help probe as $FAKE_GH_HELP says, then records the
#: arguments of a real `verify` call and passes or fails as $FAKE_GH_EXIT says,
#: printing the sentence the real gh printed for a file its bundle does not
#: cover. The three help shapes:
#:   current: the flags list has the --signer-workflow line gh 2.101.0 prints;
#:   old:     no such flag line, but the prose names the flag in backticks, as
#:            the real help's prose does, so a match on prose would be caught;
#:   missing: no `attestation` command at all, exiting 1 as gh does.
_FAKE_GH: Final[str] = r"""#!@BASH@
case " $* " in
    *" --help "*)
        case "$FAKE_GH_HELP" in
            current)
                echo 'FLAGS'
                echo '  -b, --bundle string            Path to bundle on disk'
                echo '      --signer-workflow string   Enforce that the workflow that signed the attestation matches'
                exit 0 ;;
            old)
                echo 'In this situation, use either the `--signer-workflow` or'
                echo 'FLAGS'
                echo '  -b, --bundle string            Path to bundle on disk'
                echo '      --cert-identity string     Enforce that the certificate matches'
                exit 0 ;;
            *)
                echo 'unknown command "attestation" for "gh"' >&2
                exit 1 ;;
        esac ;;
esac
printf '%s\n' "$@" > "$FAKE_RELEASE/gh-args.txt"
if [ "$FAKE_GH_EXIT" != 0 ]; then
    echo 'Error: verifying with issuer "sigstore.dev"' >&2
fi
exit "$FAKE_GH_EXIT"
"""

_STUB_INTEGRATE: Final[str] = """#!@BASH@
printf '%s\\n' "$@" > "$HOME/integrated-with.txt"
"""


def _write_script(path: Path, text: str, bash: str) -> None:
    path.write_text(text.replace("@BASH@", bash), encoding="utf-8")
    path.chmod(0o755)


def _install(
    tmp_path: Path,
    *,
    checksum: str | None = "match",
    bundle: bool = True,
    gh_exit: int | None = 0,
    gh_help: str = "current",
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run install.sh --no-host against a fake release; return the run and HOME.

    `checksum` is "match", "mismatch", "malformed", or None for a release with
    no .sha256. `gh_exit` None means gh is not installed at all. `gh_help` is
    the fake gh's answer to the help probe: "current", "old" or "missing".
    """
    bash = shutil.which("bash")
    assert bash is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in _TOOLS:
        found = shutil.which(tool)
        assert found is not None, f"{tool} is not installed"
        (bin_dir / tool).symlink_to(found)
    _write_script(bin_dir / "curl", _FAKE_CURL, bash)
    if gh_exit is not None:
        _write_script(bin_dir / "gh", _FAKE_GH, bash)

    release = tmp_path / "release"
    release.mkdir()
    (release / _ASSET).write_bytes(_PAYLOAD)
    # The sidecars are listed FIRST, so picking the AppImage is the grep's doing.
    listing = [
        {
            "tag_name": "v9.9.9",
            "assets": [
                {"browser_download_url": _BASE_URL + _ASSET + ".sha256"},
                {"browser_download_url": _BASE_URL + _ASSET + ".sigstore.json"},
                {"browser_download_url": _BASE_URL + _ASSET},
            ],
        }
    ]
    (release / "releases.json").write_text(
        json.dumps(listing, indent=2), encoding="utf-8"
    )
    digest = hashlib.sha256(_PAYLOAD).hexdigest()
    sidecar = {
        "match": f"{digest}  {_ASSET}\n",
        "mismatch": f"{'0' * 64}  {_ASSET}\n",
        "malformed": "not a checksum\n",
    }
    if checksum is not None:
        (release / f"{_ASSET}.sha256").write_text(sidecar[checksum], encoding="utf-8")
    if bundle:
        (release / f"{_ASSET}.sigstore.json").write_text("{}\n", encoding="utf-8")

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    shutil.copy2(SCRIPT, checkout / "install.sh")
    _write_script(checkout / "install-appimage.sh", _STUB_INTEGRATE, bash)

    home = tmp_path / "home"
    (home / "Applications").mkdir(parents=True)
    (home / "Applications" / _ASSET).write_bytes(_OLD_INSTALL)
    scratch = tmp_path / "tmp"
    scratch.mkdir()
    env = {
        "PATH": str(bin_dir),
        "HOME": str(home),
        "TMPDIR": str(scratch),
        "FAKE_RELEASE": str(release),
        "FAKE_GH_EXIT": str(gh_exit or 0),
        "FAKE_GH_HELP": gh_help,
        "LC_ALL": "C",
    }
    result = subprocess.run(
        [bash, str(checkout / "install.sh"), "--no-host", "--yes"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=60,
    )
    # Whatever happened, the script cleaned up after itself.
    assert list(scratch.iterdir()) == [], "install.sh left its temp dir behind"
    assert not (home / "Applications" / ".platterpus-install.part").exists()
    return result, home


def test_a_download_that_passes_both_checks_is_installed(tmp_path: Path) -> None:
    result, home = _install(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    installed = home / "Applications" / _ASSET
    assert installed.read_bytes() == _PAYLOAD
    assert os.access(installed, os.X_OK)
    assert "checksum matches" in result.stdout
    assert "build attestation verified" in result.stdout
    # The attestation was checked against THIS repository's release workflow,
    # using the bundle the release publishes, so gh needs no login.
    args = (tmp_path / "release" / "gh-args.txt").read_text(encoding="utf-8")
    assert args.splitlines()[:2] == ["attestation", "verify"]
    for expected in (
        "--repo\nrmccann-hub/Platterpus\n",
        "--signer-workflow\nrmccann-hub/Platterpus/.github/workflows/release.yml\n",
        "--bundle\n",
    ):
        assert expected in args, args
    integrated = (home / "integrated-with.txt").read_text(encoding="utf-8").strip()
    assert integrated == str(installed)


def test_without_gh_the_checksum_still_decides_and_the_skip_is_said(
    tmp_path: Path,
) -> None:
    result, home = _install(tmp_path, gh_exit=None)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / "Applications" / _ASSET).read_bytes() == _PAYLOAD
    assert "checksum matches" in result.stdout
    assert "was not checked" in result.stdout
    assert not (tmp_path / "release" / "gh-args.txt").exists()


# Literal tuples with `ids=`, not `pytest.param(...)`: a call inside the values reads
# as a computed population to tests/test_dynamic_sweeps_declare_a_floor.py.
@pytest.mark.parametrize(
    ("checksum", "bundle", "gh_exit", "reason"),
    [
        ("mismatch", True, 0, "does not match"),
        ("mismatch", True, None, "does not match"),
        ("malformed", True, 0, "malformed"),
        (None, True, 0, "couldn't fetch the release's checksum"),
        ("match", True, 1, 'verifying with issuer "sigstore.dev"'),
        ("match", False, 0, "couldn't fetch the release's build"),
    ],
    ids=[
        "checksum-mismatch",
        "checksum-mismatch-no-gh",
        "malformed-checksum",
        "no-checksum-published",
        "attestation-fails",
        "no-attestation-published",
    ],
)
def test_a_download_that_fails_a_check_is_refused_and_changes_nothing(
    tmp_path: Path,
    checksum: str | None,
    bundle: bool,
    gh_exit: int | None,
    reason: str,
) -> None:
    result, home = _install(tmp_path, checksum=checksum, bundle=bundle, gh_exit=gh_exit)

    assert result.returncode != 0, f"accepted:\n{result.stdout}"
    assert "Refusing to install" in result.stderr, result.stderr
    # The refusal names its reason, and for gh that is gh's own sentence.
    assert reason in result.stderr, result.stderr
    # The AppImage that was already there is untouched, and nothing was
    # integrated: a refused file never replaces a working install.
    assert (home / "Applications" / _ASSET).read_bytes() == _OLD_INSTALL
    assert not (home / "integrated-with.txt").exists()
    assert "no published release yet" not in result.stderr


# N5, decided by the maintainer on 2026-09-29: verify the attestation only when
# `gh attestation verify --help` lists --signer-workflow (gh 2.51.0 or later).
# A gh without it used to fail the verify call, and the installer then refused a
# download that was fine.
@pytest.mark.parametrize(
    "gh_help",
    ["old", "missing"],
    ids=["gh-without-signer-workflow", "gh-without-attestation-command"],
)
def test_a_gh_too_old_to_check_attestations_gets_the_checksum_only_path(
    tmp_path: Path, gh_help: str
) -> None:
    result, home = _install(tmp_path, gh_help=gh_help)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / "Applications" / _ASSET).read_bytes() == _PAYLOAD
    assert "checksum matches" in result.stdout
    assert "too old to check the attestation" in result.stdout
    # Only the help probe ran: gh was never asked to verify anything.
    assert not (tmp_path / "release" / "gh-args.txt").exists()


def test_with_a_gh_too_old_the_checksum_still_refuses_a_mismatch(
    tmp_path: Path,
) -> None:
    result, home = _install(tmp_path, checksum="mismatch", gh_help="old")

    assert result.returncode != 0, f"accepted:\n{result.stdout}"
    assert "does not match" in result.stderr, result.stderr
    assert (home / "Applications" / _ASSET).read_bytes() == _OLD_INSTALL
    assert not (home / "integrated-with.txt").exists()
