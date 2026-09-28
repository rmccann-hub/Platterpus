"""B1's re-run, the pure half: which `run:` commands may be repeated, and matching.

Written from the shared proposal's §"What B1 re-runs"
(`cyanrip@889a375:docs/handshake/PROPOSAL-lap-statement-language.md:219-252`),
not from the fork's checker, so that two checkers agreeing is evidence. The list
there is the whole list, "because a checker that guessed which commands are safe
to repeat would be a guess wearing a derivation's clothes":

1. **The commit** is the statement's `at:`, else the lap's
   `HANDSHAKE-FROM-COMMIT`, checked out detached in a scratch worktree of the
   author's clone and removed afterwards (`scratch.Scratch`).
2. **The command is a simple one** (`plan_command`): it splits into words with
   no shell and has none of the characters in `FORBIDDEN`; no argument is an
   absolute path, climbs out with `..`, or asks git to write a file.
3. **Its program is one of three kinds**: `git` with a read-only query as its
   first word; `sha256sum` or `wc`; or a file of the author's tree at that
   commit, run directly or as `python3 PATH`, whose own first 40 lines declare
   the re-run marker (`MARKER_RE`; checked by `scratch.marker_reason`), its
   author's word that its output depends only on the commit.
4. **Its result quotes what it printed** (`quoted_parts`, `appears`): each
   double-quoted string after `=>` must be in the output, stdout and stderr
   together, and an ellipsis inside one splits it into parts that must appear in
   that order. A result that quotes nothing is prose, and is not compared.

Anything else is reported, never refused, and never guessed.

**The spaces around an ellipsis are the elision's, not the output's.**
`"Ok 91 … Fail 0"` is the parts `Ok 91` and `Fail 0`: the writer set the mark off
with spaces, as prose does, and the output may have had anything there, a comma
or a newline. Reading the spaces as quoted text would refuse an honest lap for
its typography, and dropping them cannot make a false claim match, because every
character of each part is still required. Spaces at the outer ends of a
quotation are kept: `" 3 data.txt"` quotes the space.

**Where this reads more narrowly than the list, and why.** Item 3 lets any
read-only git query through by its first word, but the proposal's B1 row says
the checker re-runs a command "whose command can depend on nothing but that
commit". Three kinds of git argument break that, so a query carrying one is
reported unchecked instead of re-run (`_git_moves`): one that names a ref other
than `HEAD` (a ref moves, so a re-run would compare against wherever it points
today and could refuse an honest lap), one that reads the clock (relative
dates), and one that prints where the checkout is (a scratch path is not the
author's). This only ever turns a re-run into an `UNCHECKED run:`, the direction
the proposal gives for "anything else"; it can never make a lap be refused.

**How a command splits.** The proposal forbids every shell character that
changes what runs (pipes, redirections, expansions, globs, escapes) and does not
forbid quotes, so a quoted argument is taken apart the way a shell would take it
apart, by `shlex`, without any shell running. A word a shell would read as a
comment (one starting `#`) is reported, because the shell would have dropped it.

Nothing here reads a file or runs a program. It never raises on a lap's content:
a command that cannot be planned comes back as a reason.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Final

#: Characters that make a command need a shell, a glob or an elision to mean
#: what it says: the proposal's list in its order, then the backtick, a newline
#: and the ellipsis it names in words.
FORBIDDEN: Final[str] = "|;&<>$()*?[]{}\\`\n…"

#: The read-only git queries B1 re-runs, by the word after `git`.
GIT_QUERIES: Final[frozenset[str]] = frozenset(
    {
        "log",
        "show",
        "diff",
        "rev-parse",
        "merge-base",
        "ls-tree",
        "cat-file",
        "rev-list",
    }
)
#: Programs B1 re-runs as they are, on files of the checkout.
PLAIN_PROGRAMS: Final[frozenset[str]] = frozenset({"sha256sum", "wc"})

#: How many of a tool's first lines are searched for the marker.
MARKER_LINES: Final[int] = 40
#: A line that DECLARES the marker: after leading space and comment or string
#: punctuation, the line starts with it. A line that merely mentions it in prose,
#: or quotes it in backticks (as this package's own docstrings do), does not, so
#: a checker's documentation cannot mark the checker re-runnable by accident.
MARKER_RE: Final[re.Pattern[str]] = re.compile(
    r"^[\s#/*;%\"'-]*LSL-RERUN: commit-only(?:\s|$)"
)

#: git options that make a query read the clone's refs, which move.
_REF_OPTIONS: Final[frozenset[str]] = frozenset(
    {"--all", "--branches", "--tags", "--remotes", "--reflog", "--walk-reflogs", "-g"}
)
_REF_OPTION_PREFIXES: Final[tuple[str, ...]] = (
    "--glob=",
    "--branches=",
    "--tags=",
    "--remotes=",
    "--exclude=",
)
#: git options whose answer can depend on the clock rather than the commit.
_CLOCK_OPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^--(?:since|until|after|before|max-age|min-age)(?:=|$)"
    r"|^--relative-date$|^--date=(?:relative|human|auto:human)$"
)
#: Pretty-format placeholders for relative dates (`%ar`, `%cr`, `%ah`, `%ch`).
_CLOCK_PLACEHOLDER_RE: Final[re.Pattern[str]] = re.compile(r"%[ac][rh]")
#: `git rev-parse` options that print where the checkout is.
_LOCATION_OPTIONS: Final[frozenset[str]] = frozenset(
    {
        "--show-toplevel",
        "--git-dir",
        "--absolute-git-dir",
        "--git-common-dir",
        "--show-superproject-working-tree",
        "--git-path",
        "--resolve-git-dir",
    }
)
#: Refs git keeps outside `refs/`, each of which moves.
PSEUDO_REFS: Final[frozenset[str]] = frozenset(
    {
        "FETCH_HEAD",
        "ORIG_HEAD",
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "REBASE_HEAD",
        "BISECT_HEAD",
        "AUTO_MERGE",
    }
)


@dataclass(frozen=True)
class RunClaim:
    """One `run: CMD => RESULT`, split. `result` is None when there is no `=>`."""

    command: str
    result: str | None


@dataclass(frozen=True)
class Plan:
    """A command B1 may re-run.

    `words` is the command as the lap wrote it, split. `tree_file` is the path of
    the author's file it runs, which must declare the marker at the commit, or
    None for `git`, `sha256sum` and `wc`.
    """

    words: tuple[str, ...]
    tree_file: str | None


def split_run(value: str) -> RunClaim:
    """`run: CMD => RESULT` into its command and result, at the first ` => `.

    The first, because `>` cannot be in a command B1 re-runs, so a command that
    held a ` => ` of its own is not re-run whichever one is taken.
    """
    body = value[len("run: ") :] if value.startswith("run: ") else value
    command, sep, result = body.partition(" => ")
    return RunClaim(command.strip(), result.strip() if sep else None)


def quoted_parts(result: str) -> list[list[str]]:
    """Each double-quoted string in `result`, split at the ellipsis into its parts.

    Whitespace next to an ellipsis belongs to the elision (module docstring), so
    `"a … b"` is the parts `a` and `b`. Empty parts are dropped (`"a…"` is the
    one part `a`), and a quoted string with no part left (`""`, `"…"`) compares
    nothing and is dropped too, so an empty quotation cannot be what makes a
    result "matched".
    """
    found: list[list[str]] = []
    for quoted in re.findall(r'"([^"]*)"', result):
        pieces = quoted.split("…")
        parts: list[str] = []
        for i, piece in enumerate(pieces):
            if i > 0:
                piece = piece.lstrip()
            if i < len(pieces) - 1:
                piece = piece.rstrip()
            if piece:
                parts.append(piece)
        if parts:
            found.append(parts)
    return found


def appears(parts: list[str], output: str) -> bool:
    """True when every part is in `output`, each after the one before it."""
    at = 0
    for part in parts:
        found = output.find(part, at)
        if found < 0:
            return False
        at = found + len(part)
    return True


def plan_command(command: str, refs: frozenset[str]) -> Plan | str:
    """The command to re-run, or the reason B1 does not re-run it.

    `refs` names every ref of the author's clone (`scratch.ref_names`), for the
    narrowing in `_git_moves`. Pure: it reads no file and runs nothing.
    """
    shell = sorted({ch for ch in command if ch in FORBIDDEN})
    if shell:
        shown = ", ".join(repr(ch) for ch in shell)
        return f"it needs a shell, a glob or an elision to mean what it says ({shown})"
    try:
        words = shlex.split(command, posix=True)
    except ValueError as exc:
        return f"it does not split into words without a shell ({exc})"
    if not words:
        return "it names no command"
    for word in words:
        reason = _word_reason(word)
        if reason is not None:
            return reason
    program = words[0]
    if program == "git":
        if len(words) < 2 or words[1] not in GIT_QUERIES:
            return (
                "a git command is re-run only with a read-only query as its first "
                f"word ({', '.join(sorted(GIT_QUERIES))})"
            )
        moves = _git_moves(words[2:], refs)
        return Plan(tuple(words), None) if moves is None else moves
    if program in PLAIN_PROGRAMS:
        return Plan(tuple(words), None)
    if program == "python3":
        if len(words) < 2 or words[1].startswith("-"):
            return "python3 is re-run only as 'python3 PATH', PATH a file of the author's tree"
        target = words[1]
    elif "/" in program:
        target = program
    else:
        return (
            f"{program!r} is not git, sha256sum, wc, or a file of the author's tree "
            "run directly or as python3 PATH"
        )
    path = PurePosixPath(target).as_posix()
    if path in ("", "."):
        return f"{target!r} is not a file path"
    return Plan(tuple(words), path)


def _word_reason(word: str) -> str | None:
    """Why one word stops a command being simple, or None."""
    if word.startswith("#"):
        return f"a shell would read {word!r} as the start of a comment"
    values = [word, *word.split("=")[1:]]
    if any(value.startswith(("/", "~")) for value in values):
        return f"{word!r} is an absolute path, and a re-run runs inside the checkout"
    if ".." in re.split(r"[/=:]", word):
        return f"{word!r} climbs out with '..'"
    if word == "--output" or word.startswith("--output="):
        return "it asks git to write a file (--output)"
    return None


def _git_moves(args: list[str], refs: frozenset[str]) -> str | None:
    """Why a read-only git query can still depend on more than its commit, or None.

    See the module docstring: this narrows item 3, and only toward "unchecked".
    """
    for arg in args:
        if arg == "--":
            return None  # the rest are paths
        if arg.startswith("-"):
            if _CLOCK_OPTION_RE.match(arg) or (
                arg.startswith(("--format", "--pretty"))
                and _CLOCK_PLACEHOLDER_RE.search(arg)
            ):
                return (
                    f"{arg!r} reads the clock, so its answer is not the commit's alone"
                )
            if arg in _REF_OPTIONS or arg.startswith(_REF_OPTION_PREFIXES):
                return f"{arg!r} reads the clone's refs, which move"
            if arg in _LOCATION_OPTIONS:
                return (
                    f"{arg!r} prints where the checkout is, not what the commit holds"
                )
            continue
        named = names_ref(arg, refs)
        if named is not None:
            return (
                f"{arg!r} names the ref {named!r}, which can move; only a SHA or "
                "HEAD names what the command ran at"
            )
    return None


def names_ref(arg: str, refs: frozenset[str]) -> str | None:
    """The ref a revision argument names (`main`, `origin/x~2`, `v1..v2`), or None."""
    if "@{" in arg:
        return arg
    revision = arg.split(":", 1)[0].lstrip("^")
    for side in re.split(r"\.\.\.?", revision):
        base = re.split(r"[~^@]", side, maxsplit=1)[0]
        if base and (base in refs or base in PSEUDO_REFS):
            return base
    return None
