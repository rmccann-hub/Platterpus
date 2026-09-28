"""B1's re-run, the half that touches the world: a scratch checkout, and running in it.

`rerun.py` decides, without running anything, whether a `run:` may be repeated.
This module does the repeating, and only when a person passed `--rerun`:

* **A detached scratch worktree of the author's clone at the commit**
  (`Scratch.tree`), made with `git worktree add --detach` and removed with
  `git worktree remove --force` (`Scratch.close`), never by deleting a directory
  tree. The clone's own record of its worktrees is what has to be put back, and
  `remove` does both. One that will not go is reported for a person to remove.
  The clone's hooks are switched off for the checkout, since a hook is code the
  lap did not ask to run.
* **Running the command there** (`Scratch.run`): no shell, stdin closed, stdout
  and stderr into one file so they interleave as written, bounded by a timeout
  after which the whole process group is killed and the reap is bounded too
  (`CLAUDE.md` rule #9: never wait on a child without a bound). An interrupt
  during the wait (Ctrl-C) kills the group the same way before it goes on up,
  since the child's own session never sees the terminal's SIGINT. Output past
  `MAX_OUTPUT_BYTES` is not compared, and the run is reported rather than
  matched against a part of what it printed.
* **The marker** (`marker_reason`), read from the object store at the commit, so
  a tool that does not declare it costs no checkout.

**This executes the author's committed code**, the other side's when checking
their lap. That is why nothing here runs without `--rerun`.
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .rerun import MARKER_LINES, MARKER_RE, Plan

#: How long one re-run may take, and how long a killed one gets to be reaped.
RERUN_TIMEOUT_S: Final[float] = 120.0
REAP_TIMEOUT_S: Final[float] = 5.0
#: How long `git worktree add` and `remove` may take on a large tree.
WORKTREE_TIMEOUT_S: Final[float] = 300.0
#: How long one of our own git queries (ls-tree, cat-file, for-each-ref) may take.
GIT_TIMEOUT_S: Final[float] = 30.0
#: Output past this many bytes is not compared.
MAX_OUTPUT_BYTES: Final[int] = 32 * 1024 * 1024

#: The environment a re-run gets on top of ours: no pager, no prompt, no lock a
#: read-only query would take, and no `__pycache__` written into the checkout.
RERUN_ENV: Final[dict[str, str]] = {
    "GIT_PAGER": "cat",
    "PAGER": "cat",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
}


@dataclass(frozen=True)
class Ran:
    """A re-run that finished. `exit_code` is the child's own, never invented."""

    argv: tuple[str, ...]
    exit_code: int
    output: str


class Scratch:
    """Detached scratch worktrees of one clone, one per commit, removed by `close`."""

    def __init__(self, clone: Path) -> None:
        self.clone: Path = clone
        self.parent: Path | None = None
        self._trees: dict[str, Path | str] = {}
        self._runs: int = 0

    def tree(self, sha: str) -> Path | str:
        """The checkout of `sha`, made once, or why there is none."""
        if sha not in self._trees:
            self._trees[sha] = self._add(sha)
        return self._trees[sha]

    def _add(self, sha: str) -> Path | str:
        if self.parent is None:
            try:
                self.parent = Path(tempfile.mkdtemp(prefix="lsl-rerun-"))
            except OSError as exc:
                return f"no scratch directory could be made ({exc})"
        path = self.parent / sha
        added = _git(
            self.clone,
            "-c",
            "core.hooksPath=/dev/null",
            "worktree",
            "add",
            "--detach",
            str(path),
            sha,
            timeout=WORKTREE_TIMEOUT_S,
        )
        if added is None:
            return f"git did not answer when asked to check out {sha}"
        if added.returncode != 0:
            said = added.stderr.strip().splitlines()
            return f"no worktree of {sha} could be checked out ({said[-1] if said else f'exit {added.returncode}'})"
        head = _git(path, "rev-parse", "HEAD")
        if head is None or not head.stdout.strip().startswith(sha):
            return f"the worktree made for {sha} is not at {sha}"
        return path

    def run(self, plan: Plan, cwd: Path) -> Ran | str:
        """Run `plan` in `cwd`, or say why it did not run to the end."""
        if self.parent is None:
            return "no scratch directory was made"
        self._runs += 1
        out_path = self.parent / f"output-{self._runs}"
        # A file run directly is run from the checkout, whatever `PATH` holds,
        # with the name the lap gave it as its argv[0].
        executable = None
        if plan.tree_file is not None and plan.words[0] != "python3":
            executable = str(cwd / plan.tree_file)
        try:
            with out_path.open("wb") as sink:
                try:
                    child = subprocess.Popen(
                        list(plan.words),
                        executable=executable,
                        cwd=cwd,
                        stdin=subprocess.DEVNULL,
                        stdout=sink,
                        stderr=subprocess.STDOUT,
                        env={**os.environ, **RERUN_ENV},
                        start_new_session=True,
                    )
                except OSError as exc:
                    return f"it could not be started ({exc})"
                try:
                    code = child.wait(timeout=RERUN_TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    return _kill(child)
                except BaseException:
                    # Ctrl-C (KeyboardInterrupt) or SystemExit during the wait.
                    # The child leads its own session, so the terminal's SIGINT
                    # never reached it, and Popen.wait gives up on it without
                    # killing it. Left alive it would run on, unbounded, in a
                    # checkout `close` is about to remove (review finding R14).
                    # So the group is killed and the reap bounded, as on a
                    # timeout, before the interrupt goes on up.
                    _kill(child)
                    raise
                # Anything the command left running in its group would go on
                # writing into a checkout about to be removed.
                _kill_group(child.pid)
            size = out_path.stat().st_size
            if size > MAX_OUTPUT_BYTES:
                return f"it printed {size} bytes, more than the {MAX_OUTPUT_BYTES} compared"
            output = out_path.read_bytes().decode("utf-8", errors="replace")
        except OSError as exc:
            return f"its output could not be read ({exc})"
        finally:
            try:
                out_path.unlink()
            except OSError:
                pass
        return Ran(plan.words, code, output)

    def close(self) -> list[str]:
        """Remove every worktree made; return the paths that could not be removed."""
        left: list[str] = []
        for tree in self._trees.values():
            if not isinstance(tree, Path):
                continue
            removed = _git(
                self.clone,
                "worktree",
                "remove",
                "--force",
                str(tree),
                timeout=WORKTREE_TIMEOUT_S,
            )
            if removed is None or removed.returncode != 0:
                left.append(str(tree))
        if self.parent is not None:
            try:
                self.parent.rmdir()
            except OSError:
                left.append(str(self.parent))
        self._trees.clear()
        self.parent = None
        return left


def ref_names(clone: Path) -> frozenset[str]:
    """Every name that resolves to a ref of `clone`, in each spelling git accepts.

    Empty when git cannot be asked. That only loosens `rerun._git_moves`, and a
    query it then lets through must still match what the lap quotes.
    """
    listed = _git(clone, "for-each-ref", "--format=%(refname)")
    if listed is None or listed.returncode != 0:
        return frozenset()
    names: set[str] = set()
    for full in listed.stdout.split():
        names.add(full)
        for prefix in ("refs/heads/", "refs/tags/", "refs/remotes/", "refs/"):
            if full.startswith(prefix):
                names.add(full[len(prefix) :])
        if full.startswith("refs/remotes/") and full.endswith("/HEAD"):
            names.add(full[len("refs/remotes/") : -len("/HEAD")])
    return frozenset(names)


def marker_reason(clone: Path, sha: str, path: str) -> str | None:
    """None when `path` at `sha` declares the marker; otherwise why it does not.

    A symbolic link is not followed: the file that declares the marker must be
    the file that runs.
    """
    listed = _git(clone, "ls-tree", sha, "--", path)
    if listed is None:
        return f"git did not answer about {path} at {sha}"
    fields = listed.stdout.split(None, 3)
    if listed.returncode != 0 or len(fields) < 4:
        return f"{path} is not a file of the author's tree at {sha}"
    mode, kind, blob = fields[0], fields[1], fields[2]
    if kind != "blob" or mode not in ("100644", "100755"):
        return f"{path} at {sha} is not a plain file (mode {mode}, {kind})"
    shown = _git(clone, "cat-file", "blob", blob)
    if shown is None or shown.returncode != 0:
        return f"git could not read {path} at {sha}"
    head = shown.stdout.splitlines()[:MARKER_LINES]
    if any(MARKER_RE.match(line) for line in head):
        return None
    return (
        f"{path} at {sha} does not declare the re-run marker in its first "
        f"{MARKER_LINES} lines, so its author has not said its output depends "
        "only on the commit"
    )


def _kill_group(pid: int) -> None:
    """SIGKILL the process group `pid` leads; nothing to do if it is gone."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _kill(child: subprocess.Popen[bytes]) -> str:
    """Kill a re-run that ran too long, with its whole process group."""
    _kill_group(child.pid)
    try:
        child.wait(timeout=REAP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return (
            f"it ran past {RERUN_TIMEOUT_S:.0f} s, was killed, and could not be "
            "reaped, so its exit code is unknown"
        )
    return f"it ran past {RERUN_TIMEOUT_S:.0f} s and was killed"


def _git(
    root: Path, *args: str, timeout: float = GIT_TIMEOUT_S
) -> subprocess.CompletedProcess[str] | None:
    """Run git in `root`. None means git could not be asked."""
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
