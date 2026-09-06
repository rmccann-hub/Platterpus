"""One lock for "something is deliberately writing WRONG CODE into `src/`".

**Why this is shared rather than one per tool.** Two scripts in this repository
mutate tracked source in place and put it back: `mutation_sweep.py` applies a
mutant and `revert_probe.py` applies a revert. For the duration of one edit the
working tree is *incorrect*, and anything reading it in that window — another of
these tools, a test run, a coverage pass, an editor's language server — sees the
incorrect version.

Two separate locks would let a sweep and a probe run at once, each holding its
own, each corrupting what the other reads. A mutual-exclusion primitive that does
not exclude the other party is decoration. So: **one lock, both callers**, which
is this project's *one predicate, N callers* rule applied to a resource instead of
a question.

**Measured, by doing it** (2026-09-05): a mutation sweep was backgrounded while
`scripts/check.py` ran the suite, and two `test_audit_regressions.py` cases failed
against a `verdict.py` that was byte-identical to `HEAD` by the time anyone
looked. `git status` was clean and `git diff` was empty. The hazard was written in
the sweep's own comments an hour before that happened, which is the whole argument
for a lock over a warning: a rule you must remember while typing a command loses
to convenience every time.

**It fails CLOSED.** A stale lock from a killed run stops everything and names the
file to delete. That is the right direction to be wrong in for a tool whose
failure mode is a silently corrupted source tree — the shape that hides from
`git diff`, which is the hardest kind to find.

This does **not** protect against a human running `pytest` in another terminal.
Nothing here can. It bounds the collisions this repository's own tooling can
cause, which are the ones that have actually happened.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

#: Deliberately at the repo root and deliberately `.gitignore`d: it is per-checkout
#: state, and committing it would hand every clone a permanent refusal.
LOCK_PATH: Final[Path] = REPO_ROOT / ".mutation-sweep.lock"


@contextmanager
def exclusive_tree(holder: str) -> Iterator[None]:
    """Hold the working tree for one in-place-mutation run, or refuse.

    ``holder`` names the tool, so the refusal can say *what* is already running
    rather than only *that* something is. "A sweep is running" and "a revert probe
    is running" send a reader to different places.

    `O_CREAT | O_EXCL` so the check and the claim are a single operation. A
    read-then-write would let two callers both observe "no lock" and both proceed,
    which is the race this exists to prevent rather than to add.
    """
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        try:
            held_by = LOCK_PATH.read_text(encoding="utf-8").strip() or "(unknown)"
        except OSError:  # pragma: no cover — the lock vanished between calls
            held_by = "(unreadable)"
        raise SystemExit(
            f"REFUSING TO RUN {holder}: the working tree is already held by "
            f"{held_by}.\n"
            "These tools write wrong code into src/ and take it out again, so two "
            "at once — or one alongside a test run — corrupts what the other "
            "reads, invisibly to `git diff`.\n"
            f"If nothing is running, delete {LOCK_PATH} and try again."
        ) from None
    try:
        os.write(fd, f"{holder} pid={os.getpid()}\n".encode())
        os.close(fd)
        yield
    finally:
        LOCK_PATH.unlink(missing_ok=True)
