"""The workflow and shell linters in CI check what they claim to check.

Added 2026-10-27 with the `workflow-lint` and `shellcheck` jobs (the review of
that day, items 2.5 and 3.6, on the owner's word). Three things can quietly go
wrong with a linter job, and each has a test here:

1. **A script falls outside the list.** The shellcheck job lists scripts with a
   pathspec (`*.sh`, the pre-commit hook, minus the handshake records). A new
   shell script without the `.sh` suffix would never be checked, and the job
   would stay green about a file it never read. So the test finds every tracked
   file with a shell shebang and requires the job's own pathspec to list it.
2. **The pins float.** Critical rule #11: a CI tool is pinned to its minor, and
   the workflow reads the pin from pyproject rather than naming a version.
3. **The job stops running the tool.** A job that installs zizmor and never
   runs it, or runs it online, is decoration.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO: Path = Path(__file__).resolve().parent.parent
CI_YML: Path = REPO / ".github" / "workflows" / "ci.yml"

#: The handshake folder's rig scripts are sent records, kept byte for byte as
#: the peer received them, so the job leaves them out on purpose.
_EXCLUDED_PREFIX: str = "docs/handshake/"

#: A shebang that runs a POSIX shell or bash, directly or through `env`.
_SHELL_SHEBANG: re.Pattern[str] = re.compile(r"^#!\s*\S*/(?:env\s+)?(?:ba|da)?sh\b")

#: 14 scripts on 2026-10-27. A floor, so an empty or broken listing can't pass.
_MIN_SCRIPTS: int = 10


def _ci_text() -> str:
    return CI_YML.read_text(encoding="utf-8")


def _job_pathspec() -> list[str]:
    """The pathspec the shellcheck job passes to `git ls-files`, read from ci.yml.

    Read from the workflow itself, so the test checks the list the job really
    builds, not a copy of it.
    """
    match = re.search(
        r"git ls-files -z -- (?P<spec>.+)\)\s*$", _ci_text(), re.MULTILINE
    )
    assert match, "the shellcheck job no longer lists scripts with `git ls-files -z --`"
    return [part.strip("'\"") for part in match.group("spec").split()]


def _git(*args: str) -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    return subprocess.run(
        [git, *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def test_the_shellcheck_job_lists_every_shell_script() -> None:
    """Every tracked file with a shell shebang is in the job's list.

    `*.sh` files are listed whatever their first line says, so the check runs
    the other way: a file that IS a shell script must be listed.
    """
    listed = set(
        filter(None, _git("ls-files", "-z", "--", *_job_pathspec()).split("\0"))
    )
    assert len(listed) >= _MIN_SCRIPTS, (
        f"the job's pathspec lists only {sorted(listed)}"
    )

    examined = 0
    missing: list[str] = []
    for name in filter(None, _git("ls-files", "-z").split("\0")):
        if name.startswith(_EXCLUDED_PREFIX):
            continue
        path = REPO / name
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            first = handle.readline(200)
        examined += 1
        try:
            line = first.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if _SHELL_SHEBANG.match(line) and name not in listed:
            missing.append(name)
    assert examined > 100, f"examined only {examined} tracked files"
    assert not missing, (
        "these shell scripts are outside the shellcheck job's pathspec, so CI "
        f"never checks them; name them with .sh or add them to the pathspec: {missing}"
    )


def test_the_shell_shebang_pattern_recognises_real_shebangs() -> None:
    """The detector above matches the forms in use, and not a Python shebang."""
    for line in ("#!/bin/sh\n", "#!/usr/bin/env bash\n", "#!/bin/bash -e\n"):
        assert _SHELL_SHEBANG.match(line), line
    for line in ("#!/usr/bin/env python3\n", "# not a shebang\n"):
        assert not _SHELL_SHEBANG.match(line), line


def test_the_handshake_records_are_the_only_exclusion() -> None:
    """The pathspec leaves out the handshake folder and nothing else."""
    excludes = [p for p in _job_pathspec() if p.startswith(":(exclude)")]
    assert excludes == [":(exclude)docs/handshake/**"], excludes


def test_the_ci_lint_pins_are_minor_pins_read_from_pyproject() -> None:
    """Critical rule #11: each tool has a floor and a ceiling one minor up,
    and ci.yml names no version of any of them."""
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    extra = pyproject["project"]["optional-dependencies"]["ci-lint"]
    names = {re.split(r"[<>=!~ ;]", spec, maxsplit=1)[0] for spec in extra}
    assert names == {"actionlint-py", "zizmor", "shellcheck-py"}, names
    for spec in extra:
        assert re.search(r">=[\d.]+,\s*<[\d.]+", spec), f"{spec!r} is not a minor pin"

    ci = _ci_text()
    for name in names:
        assert not re.search(rf"{re.escape(name)}\s*(==|>=|~=|<)", ci), (
            f"ci.yml names a version of {name}; read it from pyproject instead"
        )


def test_the_jobs_run_their_tools() -> None:
    """Installing a linter is not running it, and zizmor must stay offline."""
    ci = _ci_text()
    for job in ("workflow-lint:", "shellcheck:"):
        assert f"\n  {job}\n" in ci, f"ci.yml has no `{job}` job"
    assert re.search(r"run: actionlint\b", ci), "workflow-lint does not run actionlint"
    assert re.search(r"run: zizmor --offline\b", ci), (
        "workflow-lint does not run zizmor offline"
    )
    assert re.search(r'^\s+shellcheck "\$\{scripts\[@\]\}"$', ci, re.MULTILINE), (
        "the shellcheck job does not run shellcheck on the listed scripts"
    )
