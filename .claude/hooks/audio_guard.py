#!/usr/bin/env python3
"""Agent-side audio guard: a Claude Code ``PreToolUse`` hook for the Bash tool.

**What it protects.** CLAUDE.md Critical rule #8: no copyrighted media in this
public repository, ever. The real gate is ``.githooks/pre-commit``, which git runs
on every commit. This hook is the agent's EARLY WARNING. It stops a Bash call
*before* it runs, so a session never even attempts the commit, and it tells the
agent what to do instead.

**How Claude Code calls it.** Before every Bash call, the harness runs this script
with a JSON object on stdin. The object carries ``tool_input.command``, the shell
text about to run, and ``cwd``. Exit 2 BLOCKS the call, and stderr is shown to the
agent as the reason. Exit 0 allows it.

**What it decides, in order:**

1. If it cannot read the command it is judging, it blocks. It cannot vouch for
   text it never saw.
2. A command that only REMOVES things from the index or the tree (``git restore``,
   ``git reset``, ``git rm``, ``git rm --cached``) is always allowed. That is the
   way out this hook's own message points to, so it must never be blocked.
3. A command that would itself STAGE an audio file (``git add x.flac``,
   ``git add .`` in a folder holding one, ``git mv a b.flac``,
   ``git commit x.flac``) is blocked.
4. A command that COMMITS or PUSHES is blocked while audio is staged.
5. **It fails closed.** Inside a git repository where it cannot read the staged
   list, it blocks a commit or push and says why. Everything else is allowed,
   because an ordinary command cannot put audio into history.

**Why it replaced a one-line command (2026-10-12).** The line in
``.claude/settings.json`` was::

    git diff --cached ... 2>/dev/null | grep -qiE '<audio>' && {block} || exit 0

It had three defects. It failed OPEN: a failing ``git diff`` printed nothing,
grep matched nothing, and the call was allowed. It never read the command, so
while audio was staged it blocked EVERY Bash call, including the
``git restore --staged`` its own message told the agent to run. And it looked
only at what was staged BEFORE the call, so ``git add x.flac && git commit`` in
one call got straight past it. ``tests/test_audio_guard_hook.py`` pins each one.

It reads shell text, not a shell's mind. Known limits, each failing toward
the real gate rather than toward a silent pass: it does not resolve shell
variables or command substitutions, or follow paths that ``xargs`` or a script
supplies. It does not check ``git checkout <tree> -- <path>``,
``git apply --cached`` or ``git update-index --add``, which can also stage a
file. The git pre-commit hook still checks every one of those at commit time.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# The same extensions, spelled the same way, as `.githooks/pre-commit` and
# ci.yml's media-guard. `tests/test_media_guard_hook.py` compares all three, so
# a format added to one and forgotten in another turns the suite red.
AUDIO: Final[re.Pattern[str]] = re.compile(
    r"\.(flac|wav|pcm|raw|mp3|m4a|aac|ogg|oga|opus|wv|ape|wma|aiff|aif|alac|dsf|dff)$",
    re.IGNORECASE,
)
AUDIO_PATTERN: Final[str] = AUDIO.pattern

# Exit codes Claude Code gives meaning to: 2 blocks the call, 0 allows it.
BLOCK: Final[int] = 2
ALLOW: Final[int] = 0

# How long any one git probe may take. The hook as a whole has 10 s in
# settings.json; a probe that hangs past this is treated as a failed probe.
GIT_TIMEOUT_S: Final[float] = 4.0

# Git subcommands that only take things OUT of the index or the tree, or put the
# tree back. Always allowed: they are how you recover from staging audio.
REMOVING: Final[frozenset[str]] = frozenset({"restore", "reset", "rm"})

# Subcommands that write history or publish it. Blocked while audio is staged.
# `push` publishes no staged content, but the rule asked for push too, and a push
# made while audio is staged is a session about to commit it.
COMMITTING: Final[frozenset[str]] = frozenset(
    {"commit", "commit-tree", "merge", "cherry-pick", "revert", "am", "rebase", "push"}
)

# Git's own options that take a separate value (`git -C dir commit`).
_GIT_VALUE_OPTS: Final[frozenset[str]] = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--super-prefix",
        "--config-env",
    }
)

# `git commit` options that take a separate value. What is left after them is a
# pathspec, and a commit with a pathspec stages those paths itself.
_COMMIT_VALUE_OPTS: Final[frozenset[str]] = frozenset(
    {
        "-m",
        "--message",
        "-F",
        "--file",
        "-C",
        "--reuse-message",
        "-c",
        "--reedit-message",
        "--fixup",
        "--squash",
        "--author",
        "--date",
        "-t",
        "--template",
        "--cleanup",
        "--trailer",
        "--pathspec-from-file",
    }
)

# `git add` flags that change WHICH files would be staged. These are passed on to
# the dry run, so it lists exactly what the real call would add. Interactive
# flags (-p, -i, -e) are dropped: the dry run then lists every candidate, which
# is more than the real call stages, never less.
_ADD_SCOPE_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "-f",
        "--force",
        "-A",
        "--all",
        "--no-all",
        "-u",
        "--update",
        "--ignore-removal",
        "--no-ignore-removal",
        "-N",
        "--intent-to-add",
        "--sparse",
    }
)

# Words that run the next word as the command: `env git commit`, `sudo git ...`.
_PREFIX_COMMANDS: Final[frozenset[str]] = frozenset(
    {"env", "command", "builtin", "exec", "nohup", "time", "sudo", "nice", "stdbuf"}
)

# Shells whose `-c '<text>'` we read as a command of its own.
_SHELLS: Final[frozenset[str]] = frozenset({"bash", "sh", "zsh", "dash"})

# A heredoc operator, but not the here-string `<<<`. The quote around the
# delimiter is matched but not paired (no backreference), which keeps this a
# pattern the regex sweep can time; a mismatched quote is not valid shell anyway.
_HEREDOC: Final[re.Pattern[str]] = re.compile(
    r"(?<!<)<<(-?)(?!<)[ \t]*['\"]?([A-Za-z_][A-Za-z0-9_]*)"
)


# Used only when the command will not parse as shell: does it name git at all,
# and does it name a git command that stages?
_GIT_WORD: Final[re.Pattern[str]] = re.compile(r"\bgit\b")
_GIT_STAGING: Final[re.Pattern[str]] = re.compile(
    r"\bgit[ \t]+(?:add|stage|mv|commit)\b"
)

# Tokens that end one simple command and begin the next.
_SEPARATORS: Final[frozenset[str]] = frozenset(
    {";", "&", "&&", "|", "||", "|&", "(", ")", "\n", ";;"}
)


@dataclass
class GitCall:
    """One `git` invocation found in the command, with the folder it acts on."""

    subcommand: str
    args: list[str]
    cwd: Path


@dataclass
class Findings:
    """What the command does, as far as reading its text can tell."""

    git_calls: list[GitCall] = field(default_factory=list)
    # Set when the text would not parse as shell, so no call could be read.
    unparsed: bool = False


@dataclass
class StageVerdict:
    """Whether one command stages audio: yes (with the names), no, or unknown."""

    audio: list[str] = field(default_factory=list)
    unknown_reason: str | None = None


# ----------------------------------------------------------------- parsing ---


def strip_heredoc_bodies(text: str) -> str:
    """Drop the body lines of every heredoc, keeping the line that ends it.

    A commit message in a heredoc is free text. Read as shell, a line in it
    such as "git push origin" would look like a command, and one apostrophe
    would stop the tokenizer cold. The body is data, not commands, so it is
    removed before tokenizing. The closing delimiter line is kept so a heredoc
    inside a quoted ``"$(cat <<'EOF' ... EOF)"`` still balances its quotes.
    """
    out: list[str] = []
    pending: list[tuple[str, bool]] = []  # (delimiter, tabs-stripped `<<-`)
    for line in text.split("\n"):
        if pending:
            delim, dash = pending[0]
            candidate = line.lstrip("\t") if dash else line
            if candidate.strip() == delim:
                pending.pop(0)
                out.append(line)
            continue
        out.append(line)
        for m in _HEREDOC.finditer(line):
            pending.append((m.group(2), m.group(1) == "-"))
    return "\n".join(out)


def tokenize(text: str) -> list[str]:
    """Split shell text into words and separators. Raises ValueError if unbalanced."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    return list(lexer)


def split_simple_commands(tokens: list[str]) -> list[list[str]]:
    """Group tokens into simple commands, dropping redirections and their targets."""
    commands: list[list[str]] = []
    current: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _SEPARATORS:
            if current:
                commands.append(current)
            current = []
            i += 1
            continue
        if tok and set(tok) <= set("<>&"):
            # A redirection (`>`, `>>`, `2>&1`'s `>&`, `<`). Drop it and its
            # target, and a file-descriptor number written just before it.
            if current and current[-1].isdigit():
                current.pop()
            i += 2
            continue
        current.append(tok)
        i += 1
    if current:
        commands.append(current)
    return commands


def _is_assignment(word: str) -> bool:
    """True for `NAME=value`, a shell assignment rather than the program to run.

    String operations, not a regex: `[A-Za-z_][A-Za-z0-9_]*=` searched over a
    long word with no `=` is quadratic, which the regex sweep measured.
    """
    name, sep, _value = word.partition("=")
    return bool(sep) and name.isidentifier() and name.isascii()


def find_git_calls(text: str, cwd: Path, depth: int = 0) -> Findings:
    """Read every `git` invocation out of shell text, following `cd` and `sh -c`."""
    findings = Findings()
    try:
        tokens = tokenize(strip_heredoc_bodies(text))
    except ValueError:
        findings.unparsed = True
        return findings
    here = cwd
    for words in split_simple_commands(tokens):
        # Leading `VAR=value` assignments and prefix commands do not change what
        # runs: `GIT_DIR=x env git commit` is still a commit.
        while words and (
            _is_assignment(words[0]) or os.path.basename(words[0]) in _PREFIX_COMMANDS
        ):
            words = words[1:]
            while words and words[0].startswith("-"):
                words = words[1:]  # the prefix command's own flags (`sudo -E`)
        if not words:
            continue
        program = os.path.basename(words[0])
        if program == "cd" and len(words) >= 2 and words[1] != "-":
            # Follow a literal `cd`, so `cd sub && git commit` reads sub's index.
            target = Path(os.path.expanduser(words[1]))
            here = target if target.is_absolute() else (here / target)
            continue
        if program in _SHELLS and "-c" in words and depth < 3:
            inner_at = words.index("-c") + 1
            if inner_at < len(words):
                inner = find_git_calls(words[inner_at], here, depth + 1)
                findings.git_calls.extend(inner.git_calls)
                findings.unparsed = findings.unparsed or inner.unparsed
            continue
        if program != "git":
            continue
        call = _parse_git_words(words[1:], here)
        if call is not None:
            findings.git_calls.append(call)
    return findings


def _parse_git_words(words: list[str], cwd: Path) -> GitCall | None:
    """Turn the words after `git` into a subcommand, its arguments and its folder."""
    i = 0
    where = cwd
    while i < len(words) and words[i].startswith("-"):
        opt = words[i]
        if opt in _GIT_VALUE_OPTS and i + 1 < len(words):
            if opt == "-C":
                target = Path(os.path.expanduser(words[i + 1]))
                where = target if target.is_absolute() else (where / target)
            i += 2
            continue
        i += 1  # a flag with no value, or `--opt=value` in one word
    if i >= len(words):
        return None
    subcommand, args = words[i], words[i + 1 :]
    # Resolve a user alias (`git config alias.ci commit`), so `git ci` is a commit.
    if subcommand not in REMOVING | COMMITTING | {"add", "stage", "mv"}:
        expansion = _git(where, "config", "--get", f"alias.{subcommand}")
        if (
            expansion is not None
            and expansion.strip()
            and not expansion.startswith("!")
        ):
            parts = expansion.split()
            subcommand, args = parts[0], parts[1:] + args
    return GitCall(subcommand=subcommand, args=args, cwd=where)


# --------------------------------------------------------------- git probes ---


def _git(cwd: Path, *args: str) -> str | None:
    """Run git and return stdout, or None if it failed, was missing or timed out."""
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _git_failure(cwd: Path, *args: str) -> str:
    """The first line of what a failing git call said, for the refusal message."""
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"{type(exc).__name__}: {exc}"
    said = (done.stderr or done.stdout).strip().splitlines()
    first = said[0] if said else "(no output)"
    return f"exit {done.returncode}: {first}"


def inside_a_repository(cwd: Path) -> bool:
    """True if `cwd` is inside a git work tree, judged two ways.

    Git is asked first. If git itself fails, a `.git` entry in this folder or
    any parent still marks a repository. A broken git must not make a real
    repository look like "not a repository", because that answer allows the
    commit.
    """
    if _git(cwd, "rev-parse", "--is-inside-work-tree") is not None:
        return True
    for folder in (cwd, *cwd.parents):
        if (folder / ".git").exists():
            return True
    return False


def staged_audio(cwd: Path) -> tuple[list[str] | None, str]:
    """The staged audio files in `cwd`'s repository, or None if unreadable.

    Returns ``(names, why)``. ``names`` is None when the staged list could not
    be read, and ``why`` then says what git said. "Could not read" is never
    reported as "nothing staged".
    """
    listing = _git(cwd, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    if listing is None:
        return None, _git_failure(
            cwd, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"
        )
    return [name for name in listing.split("\0") if name and AUDIO.search(name)], ""


def what_add_would_stage(
    call: GitCall, pathspecs: list[str], flags: list[str]
) -> StageVerdict:
    """Ask git, with a dry run, exactly which files this add would stage."""
    if any(
        s == "-" or s.startswith("--pathspec-from-file=-") for s in flags + pathspecs
    ):
        return StageVerdict(unknown_reason="paths come from stdin")
    listing = _git(call.cwd, "add", "--dry-run", *flags, "--", *pathspecs)
    if listing is None:
        why = _git_failure(call.cwd, "add", "--dry-run", *flags, "--", *pathspecs)
        return StageVerdict(unknown_reason=f"`git add --dry-run` failed ({why})")
    names = [
        line[len("add '") : -1]
        for line in listing.splitlines()
        if line.startswith("add '") and line.endswith("'")
    ]
    return StageVerdict(audio=[n for n in names if AUDIO.search(n)])


def stages_audio(call: GitCall) -> StageVerdict:
    """Whether this one git call would put an audio file into the index."""
    if call.subcommand in ("add", "stage"):
        if "-n" in call.args or "--dry-run" in call.args:
            return StageVerdict()  # a dry run stages nothing
        flags: list[str] = []
        pathspecs: list[str] = []
        after_dashdash = False
        for arg in call.args:
            if after_dashdash or not arg.startswith("-"):
                pathspecs.append(arg)
            elif arg == "--":
                after_dashdash = True
            elif arg in _ADD_SCOPE_FLAGS or arg.startswith("--pathspec-from-file"):
                flags.append(arg)
        literal = [p for p in pathspecs if AUDIO.search(p)]
        if literal:
            return StageVerdict(audio=literal)
        from_file = any(f.startswith("--pathspec-from-file") for f in flags)
        if (
            not pathspecs
            and not from_file
            and not any(f in flags for f in ("-A", "--all", "-u", "--update"))
        ):
            return StageVerdict()  # `git add` with nothing to add
        return what_add_would_stage(call, pathspecs, flags)
    if call.subcommand == "mv":
        names = [a for a in call.args if not a.startswith("-")]
        if names and AUDIO.search(names[-1]):
            return StageVerdict(audio=[names[-1]])
        return StageVerdict()
    if call.subcommand == "commit":
        pathspecs = _commit_pathspecs(call.args)
        literal = [p for p in pathspecs if AUDIO.search(p)]
        if literal:
            return StageVerdict(audio=literal)
        if pathspecs:
            return what_add_would_stage(call, pathspecs, [])
    return StageVerdict()


def _commit_pathspecs(args: list[str]) -> list[str]:
    """The paths a `git commit` names, which it stages and commits itself."""
    out: list[str] = []
    skip = False
    after_dashdash = False
    for arg in args:
        if skip:
            skip = False
            continue
        if after_dashdash:
            out.append(arg)
        elif arg == "--":
            after_dashdash = True
        elif arg in _COMMIT_VALUE_OPTS:
            skip = True
        elif not arg.startswith("-"):
            out.append(arg)
    return out


# ------------------------------------------------------------------ judging ---


def judge(command: str, cwd: Path) -> tuple[int, str]:
    """Decide one Bash call. Returns (exit code, message for stderr)."""
    findings = find_git_calls(command, cwd)

    if findings.unparsed:
        # The text is not valid shell as written (an unclosed quote, say). Bash
        # will most likely refuse it too. If it mentions git, judge it by the
        # staged list alone, and by any audio name beside a staging word.
        if not _GIT_WORD.search(command):
            return ALLOW, ""
        audio_words = [
            word
            for word in (w.strip("'\";&|()<>") for w in command.split())
            if AUDIO.search(word)
        ]
        if audio_words and _GIT_STAGING.search(command):
            return BLOCK, _msg_stages(audio_words)
        return _check_commit_and_push(
            cwd, why_checked="it mentions git and would not parse"
        )

    calls = findings.git_calls
    if not calls:
        return ALLOW, ""
    if all(c.subcommand in REMOVING for c in calls):
        return ALLOW, ""  # always allowed: the way out of a staged audio file

    unknown: list[str] = []
    for call in calls:
        verdict = stages_audio(call)
        if verdict.audio:
            return BLOCK, _msg_stages(verdict.audio)
        if verdict.unknown_reason:
            unknown.append(f"git {call.subcommand}: {verdict.unknown_reason}")

    committing = [c for c in calls if c.subcommand in COMMITTING]
    if not committing:
        return ALLOW, ""
    if unknown:
        # The same command stages files we could not enumerate, then commits.
        return BLOCK, (
            "Blocked (CLAUDE.md Critical rule #8): this command stages files the "
            "audio guard could not list, then commits or pushes in the same call:\n"
            + "\n".join(f"    {u}" for u in unknown)
            + "\nRun the staging step on its own first, so its result can be checked."
        )
    for folder in {c.cwd for c in committing}:
        code, message = _check_commit_and_push(
            folder, why_checked="it commits or pushes"
        )
        if code == BLOCK:
            return code, message
    return ALLOW, ""


def _check_commit_and_push(cwd: Path, why_checked: str) -> tuple[int, str]:
    """Block if audio is staged in `cwd`'s repository, or if that cannot be read."""
    if not cwd.exists():
        # A folder this same command creates (`mkdir x && cd x && git init ...`).
        # Its index is empty now; what the command stages there was judged above.
        return ALLOW, ""
    if not inside_a_repository(cwd):
        return ALLOW, ""
    names, why = staged_audio(cwd)
    if names is None:
        return BLOCK, (
            "Blocked (CLAUDE.md Critical rule #8): the audio guard could not read "
            f"the staged files in {cwd} ({why}), and {why_checked}. It will not "
            "vouch for a commit it could not inspect. Fix the repository state "
            "(run `git status` to see what git reports), then retry. Commands that "
            "do not commit or push are not blocked."
        )
    if names:
        return BLOCK, (
            "Blocked (CLAUDE.md Critical rule #8): audio is staged, and "
            f"{why_checked}:\n"
            + "\n".join(f"    {n}" for n in names)
            + "\nUnstage it first, on its own: git restore --staged -- <file> "
            "(always allowed). Test with real audio outside the repo."
        )
    return ALLOW, ""


def _msg_stages(names: list[str]) -> str:
    return (
        "Blocked (CLAUDE.md Critical rule #8): this command would stage audio or "
        "other copyrighted media:\n"
        + "\n".join(f"    {n}" for n in names)
        + "\nKeep real audio outside the repo (the session scratchpad or /tmp); "
        "commit only the text proof (logs and per-track CRCs)."
    )


def main() -> int:
    """Read the hook input from stdin, judge the command, print why if blocked."""
    try:
        event = json.loads(sys.stdin.read())
        tool_input = event["tool_input"]
        command = tool_input["command"]
        if not isinstance(command, str):
            raise TypeError("tool_input.command is not a string")
    except (ValueError, KeyError, TypeError) as exc:
        print(
            "Blocked: the audio guard (CLAUDE.md Critical rule #8) could not read "
            f"the command it was asked to judge ({type(exc).__name__}: {exc}). It "
            "will not allow a command it could not see.",
            file=sys.stderr,
        )
        return BLOCK
    raw_cwd = event.get("cwd") if isinstance(event, dict) else None
    cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd else Path.cwd()
    try:
        code, message = judge(command, cwd)
    except Exception as exc:  # noqa: BLE001 -- the guard's own bug must not decide silently
        # A defect in this script. Failing closed on EVERY call would take away
        # the agent's shell, so fail closed where it matters: refuse anything that
        # names a commit or a push, allow the rest, and say what broke either way.
        broke = f"the audio guard crashed ({type(exc).__name__}: {exc})"
        words = set(command.split())
        if "git" in words and words & COMMITTING:
            print(
                f"Blocked: {broke}, and this command commits or pushes.",
                file=sys.stderr,
            )
            return BLOCK
        print(
            f"Warning: {broke}; allowing a command that does not commit or push.",
            file=sys.stderr,
        )
        return ALLOW
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
