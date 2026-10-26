"""The ripper build script refuses a wrong HEAD and a dirty tree, before building.

The claude-code-skills review of 2026-10-26 (item 2.1) found the build script
echoed HEAD, *warned* on ``git status --porcelain`` and built anyway, and that the
pin it checked out was a seven-character prefix. These tests EXECUTE the shipped
script (``fork_source._BUILD_SCRIPT``) with real git against a throwaway fork
repository, so what they hold is the script's behaviour rather than its text.

**What the stand-ins do that the real thing does not.** ``meson`` and ``ninja``
are fakes on ``PATH``: ``meson`` makes the build directory, ``ninja`` writes a
``build/src/cyanrip`` that prints a banner the test chooses and records that it
ran. Nothing is compiled. ``git`` is the real one. The container, ``distrobox``
and ``sudo install`` are absent because the build script never calls them; the
later steps are separate scripts (``tests/test_fork_source.py`` holds that order).
"""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from platterpus.deps import fork_source

#: Where the script puts the clone, relative to ``$HOME`` — the real subpath.
SUBPATH: str = fork_source.FORK_SOURCE_SUBPATH
BRANCH: str = fork_source.FORK_BRANCH

_GIT_ENV: dict[str, str] = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    # Keep the user's own git config (hooks, signing) out of the fixture.
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env={**os.environ, **_GIT_ENV},
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return done.stdout.strip()


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@dataclass(frozen=True)
class Rig:
    """A throwaway fork repository, a HOME, and fake meson/ninja on PATH."""

    origin: Path
    home: Path
    bin_dir: Path
    ninja_log: Path
    first: str  # full sha of the commit we pin
    second: str  # full sha of a later commit on the same branch

    @property
    def clone(self) -> Path:
        return self.home / SUBPATH

    def tag_for(self, sha: str) -> str:
        return f"{BRANCH}-g{sha[:7]}"

    def run(
        self, *, pin: str, full: str, tag: str, banner: str
    ) -> subprocess.CompletedProcess[str]:
        """Run the shipped build script exactly as ``build_command`` lays it out."""
        env = {
            **os.environ,
            **_GIT_ENV,
            "HOME": str(self.home),
            "PATH": f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_BANNER": banner,
            "NINJA_LOG": str(self.ninja_log),
        }
        return subprocess.run(
            [
                "sh",
                "-c",
                fork_source._BUILD_SCRIPT,
                "build-cyanrip-fork",
                SUBPATH,
                str(self.origin),
                BRANCH,
                pin,
                tag,
                "",
                full,
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def ninja_runs(self) -> int:
        if not self.ninja_log.exists():
            return 0
        return len(self.ninja_log.read_text().splitlines())


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", BRANCH)
    # `build` is ignored at every pin we build (checked at the fork for ddf7ac3,
    # 5f1d036 and upstream master), so a reused build dir is not dirt.
    (origin / ".gitignore").write_text("build\n")
    (origin / "src").mkdir()
    (origin / "src" / "main.c").write_text("int main(void) { return 0; }\n")
    _git(origin, "add", ".")
    _git(origin, "commit", "-q", "-m", "first")
    first = _git(origin, "rev-parse", "HEAD")
    (origin / "src" / "main.c").write_text("int main(void) { return 1; }\n")
    _git(origin, "commit", "-q", "-am", "second")
    second = _git(origin, "rev-parse", "HEAD")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # meson setup [--wipe] [opts] <src>/build <src>: make the build directory.
    _write_exe(
        bin_dir / "meson",
        '#!/bin/sh\nfor a in "$@"; do case "$a" in */build) mkdir -p "$a";; esac; '
        "done\n",
    )
    # ninja -C <src>/build: write a "binary" printing $FAKE_BANNER, and log the run.
    _write_exe(
        bin_dir / "ninja",
        "#!/bin/sh\n"
        'mkdir -p "$2/src"\n'
        'printf \'#!/bin/sh\\nprintf "%%s\\\\n" "%s"\\n\' "$FAKE_BANNER" '
        '> "$2/src/cyanrip"\n'
        'chmod +x "$2/src/cyanrip"\n'
        'echo ran >> "$NINJA_LOG"\n',
    )
    home = tmp_path / "home"
    home.mkdir()
    return Rig(
        origin=origin,
        home=home,
        bin_dir=bin_dir,
        ninja_log=tmp_path / "ninja.log",
        first=first,
        second=second,
    )


def _good(rig: Rig) -> subprocess.CompletedProcess[str]:
    tag = rig.tag_for(rig.first)
    return rig.run(
        pin=rig.first[:7],
        full=rig.first,
        tag=tag,
        banner=f"cyanrip 0.9.4-test ({tag})",
    )


def test_a_clean_tree_at_the_recorded_commit_builds(rig: Rig) -> None:
    """The positive control: without it, every refusal below could be the script
    failing for some reason of the fixture's and still read as a pass."""
    done = _good(rig)
    assert done.returncode == 0, done.stderr
    assert f"HEAD is exactly the recorded commit {rig.first}" in done.stdout
    assert "tree is clean" in done.stdout
    assert "safe to install" in done.stdout
    assert rig.ninja_runs() == 1


def test_a_dirty_tree_exits_non_zero_before_building(rig: Rig) -> None:
    assert _good(rig).returncode == 0
    # A stray untracked file in the cached clone: not ignored, so it is dirt, and
    # a header beside the sources can change what compiles.
    (rig.clone / "src" / "stray.h").write_text("#define X 1\n")
    done = _good(rig)
    assert done.returncode != 0, "a dirty tree was built"
    assert "DIRTY" in done.stderr and "stray.h" in done.stderr, done.stderr
    assert "UNCHANGED" in done.stderr, done.stderr
    assert rig.ninja_runs() == 1, "ninja ran on the dirty tree"


def test_a_head_that_is_not_the_recorded_commit_exits_non_zero(rig: Rig) -> None:
    """HEAD moved after the checkout: a post-checkout hook in the cached clone, the
    kind of thing a tampered or half-broken cache can hold. The checkout itself
    succeeded, so only the comparison with the full commit can catch it."""
    assert _good(rig).returncode == 0
    hook = rig.clone / ".git" / "hooks" / "post-checkout"
    _write_exe(
        hook,
        "#!/bin/sh\n"
        '[ -n "${IN_HOOK-}" ] && exit 0\n'
        f"IN_HOOK=1 git checkout -q --detach {rig.second}\n",
    )
    done = _good(rig)
    assert done.returncode != 0, "a wrong HEAD was built"
    assert f"HEAD is {rig.second}" in done.stderr, done.stderr
    assert rig.first in done.stderr, done.stderr
    assert rig.ninja_runs() == 1, "ninja ran on the wrong commit"


def test_a_short_pin_shadowed_by_a_ref_exits_non_zero(rig: Rig) -> None:
    """With no full commit recorded, git resolves a short name as a REF first, so
    a tag spelled like the pin wins. The prefix check catches it."""
    _git(rig.origin, "tag", rig.first[:7], rig.second)
    tag = rig.tag_for(rig.first)
    done = rig.run(
        pin=rig.first[:7],
        full="",
        tag=tag,
        banner=f"cyanrip 0.9.4-test ({tag})",
    )
    assert done.returncode != 0, "a short pin resolved to another commit was built"
    assert "does not begin with" in done.stderr, done.stderr
    assert rig.ninja_runs() == 0


def test_a_short_pin_with_no_full_commit_says_it_checked_only_the_prefix(
    rig: Rig,
) -> None:
    tag = rig.tag_for(rig.first)
    done = rig.run(
        pin=rig.first[:7], full="", tag=tag, banner=f"cyanrip 0.9.4-test ({tag})"
    )
    assert done.returncode == 0, done.stderr
    assert "only the prefix is checked" in done.stdout


def test_a_binary_whose_own_tag_says_dirty_is_refused(rig: Rig) -> None:
    """Item 2.2's install half: the guard matched ``*"$5"*``, so a binary
    printing ``(<tag>-dirty)`` was called "safe to install"."""
    tag = rig.tag_for(rig.first)
    done = rig.run(
        pin=rig.first[:7],
        full=rig.first,
        tag=tag,
        banner=f"cyanrip 0.9.4-test ({tag}-dirty)",
    )
    assert done.returncode != 0, "a -dirty binary was accepted for install"
    assert "DIRTY build of the right commit" in done.stderr, done.stderr


# --- The recorded full commits ------------------------------------------------


@pytest.mark.parametrize(
    ("short", "full"),
    [
        (fork_source.FORK_PIN, fork_source.FORK_PIN_FULL),
        (fork_source.PIN_UNDER_REVIEW, fork_source.PIN_UNDER_REVIEW_FULL),
        (fork_source.FORK_TEST_PIN, fork_source.FORK_TEST_PIN_FULL),
    ],
    ids=["FORK_PIN", "PIN_UNDER_REVIEW", "FORK_TEST_PIN"],
)
def test_each_full_commit_begins_with_its_short_pin(short: str, full: str) -> None:
    """The short pin is the build tag; the full one is what HEAD must be. Moving a
    short pin without its full commit fails here, rather than leaving the build
    script checking the old commit or only a prefix."""
    assert len(full) == 40 and set(full) <= set("0123456789abcdef"), full
    assert full.startswith(short.lower()), f"{full} does not begin with {short}"
    assert fork_source.full_commit_for(short) == full


def test_every_named_target_carries_its_full_commit() -> None:
    for target in (
        fork_source.PRODUCTION_TARGET,
        fork_source.UNDER_REVIEW_TARGET,
        fork_source.TEST_TARGET,
        fork_source.WIZARD_TARGET,
    ):
        assert len(target.full_commit) == 40, target.pin
        assert target.full_commit.startswith(target.pin.lower())
    # And it reaches the container as $7.
    argv = fork_source.build_command("ripping", fork_source.PRODUCTION_TARGET)
    assert argv[-1] == fork_source.FORK_PIN_FULL


@pytest.mark.parametrize(
    ("pin", "expected"),
    [
        ("", ""),
        ("5f1d03", ""),  # too short to name anything
        ("not-hex", ""),
        ("0badc0de", ""),  # hex, unrecorded: no full commit, the prefix path
        ("A" * 40, "a" * 40),  # a full sha is its own answer, lower-cased
    ],
)
def test_full_commit_for_answers_only_what_it_recorded(pin: str, expected: str) -> None:
    assert fork_source.full_commit_for(pin) == expected
