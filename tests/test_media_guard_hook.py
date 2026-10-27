"""Behavioural tests for `.githooks/pre-commit` — the Critical Rule #8 guard.

**Why this file exists.** `CLAUDE.md` calls this hook *"the canonical guard"* for
the one rule in the project with legal consequences: never commit audio or other
copyrighted media to a public repository. It had **no test of any kind**. It was
also invisible to `tests/test_security_no_shell.py::test_shell_scripts_enable_errexit`,
whose scan globs `*.sh` and so never sees an extensionless hook.

And it failed **open**. The original spelling was

    offenders=$(git diff --cached --name-only --diff-filter=ACMR | grep -iE "$pattern" || true)

where `|| true` is needed for grep's no-match exit — the normal case — but sits
outside the pipeline and therefore also absorbs a failure of `git diff` itself.
`set -o pipefail` cannot help, because it is the pipeline's own status being
discarded. A fatal `git diff` yielded an empty `offenders`, and the hook exited 0.
The identical idiom was in `ci.yml`'s media-guard, so the two guards meant to be
*independent* witnesses shared one failure mode — which is the entire point of
having a backstop.

`test_the_hook_refuses_when_it_cannot_list_the_staged_files` is the regression
test for that, and it is the reason this file runs a real `git` shim rather than
asserting on the script's text: the defect was in behaviour under a failing
producer, and no amount of reading the source would have shown it passing.

**And it passed a non-ASCII name** (external review of 2026-10-27, item 1.1).
Without `-z`, git quotes a name holding a byte outside printable ASCII
(`core.quotePath`): `Björk.flac` is listed as `"Bj\\303\\266rk.flac"`, closing
quote included, so the hook's end-anchored `\\.flac$` never matched and the
commit went through.
`test_a_staged_audio_file_with_an_unusual_name_blocks_the_commit` is the
regression test; the hook now lists names with `-z` and reads them back
NUL-separated.

The list of extensions lives in ONE file, `.githooks/audio-extensions.txt`,
which the hook and CI's media-guard read.
`test_every_audio_list_equals_the_shared_file` holds the two guards that keep
their own copy to it.

No real audio is created anywhere here (Rule #8 applies to the tests too). The
fixtures are ordinary text files with audio *extensions*, written under
`tmp_path` and never added to this repository.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
HOOK: Final[Path] = REPO_ROOT / ".githooks" / "pre-commit"
#: The shared definition of "audio" that every guard is held to.
EXTENSIONS_FILE: Final[Path] = REPO_ROOT / ".githooks" / "audio-extensions.txt"

_GIT: Final[str | None] = shutil.which("git")

pytestmark = pytest.mark.skipif(
    _GIT is None or not HOOK.is_file(),
    reason="needs git on PATH and the committed .githooks/pre-commit",
)


def _git(repo: Path, *args: str) -> None:
    """Run git in `repo`, raising with its output if it fails."""
    assert _GIT is not None
    subprocess.run(
        [_GIT, *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway git repo with the real hook available to run against it."""
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    return work


def _run_hook(
    repo: Path, extra_path: Path | None = None, hook: Path = HOOK
) -> subprocess.CompletedProcess[str]:
    """Invoke the hook exactly as git would: as a program, with cwd in the repo.

    `hook` defaults to the committed hook. The extension-list tests pass a copy
    placed beside a doctored list, because the hook finds its list next to itself.
    """
    env = None
    if extra_path is not None:
        import os

        env = dict(os.environ)
        env["PATH"] = f"{extra_path}:{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", str(hook)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_a_staged_audio_file_blocks_the_commit(repo: Path) -> None:
    """The thing the hook is for. Text content, audio extension — no media created."""
    (repo / "track01.flac").write_text("not audio, just a name\n", encoding="utf-8")
    _git(repo, "add", "-f", "track01.flac")

    result = _run_hook(repo)

    assert result.returncode == 1, (
        f"the hook allowed a staged .flac. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "track01.flac" in result.stderr, (
        "the refusal did not name the offending file, so the operator cannot act "
        f"on it: {result.stderr!r}"
    )


def test_the_extension_match_is_case_insensitive(repo: Path) -> None:
    """`.FLAC` off a Windows-ish tool must not slip past a lowercase pattern."""
    (repo / "TRACK.FLAC").write_text("not audio\n", encoding="utf-8")
    _git(repo, "add", "-f", "TRACK.FLAC")
    assert _run_hook(repo).returncode == 1


def test_an_ordinary_text_commit_is_allowed(repo: Path) -> None:
    """The floor: a guard that blocks everything would pass the tests above.

    Without this, `exit 1` unconditionally would satisfy every other assertion in
    this file — the mirror image of a check satisfied by finding nothing.
    """
    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo)

    assert result.returncode == 0, (
        f"the hook blocked an ordinary text commit. stderr={result.stderr!r}"
    )


def test_a_log_and_a_crc_file_are_allowed(repo: Path) -> None:
    """The durable proof this project DOES commit must not be blocked.

    Rule #8's own instruction is to commit the text artifacts — the ripper log and
    per-track CRCs — and never the audio. A guard that rejected those would push
    people to `--no-verify`, which disables it entirely.
    """
    (repo / "album.log").write_text("Track 1 | CRC32 A1B2C3D4\n", encoding="utf-8")
    (repo / "crcs.txt").write_text("01 A1B2C3D4\n", encoding="utf-8")
    _git(repo, "add", "album.log", "crcs.txt")
    assert _run_hook(repo).returncode == 0


def test_the_hook_refuses_when_it_cannot_list_the_staged_files(repo: Path) -> None:
    """THE regression test: a failing producer must refuse, not pass.

    With the original `... | grep ... || true`, a fatal `git diff` produced an
    empty offender list and the hook exited **0** — so a commit could proceed
    entirely unchecked. This drives that exact state with a `git` shim that fails
    only for `diff`, leaving every other git call real.

    Asserting on the exit code AND on a diagnostic reaching stderr, because a
    silent refusal would be nearly as bad: the operator needs to know the guard
    declined rather than passed.
    """
    assert _GIT is not None
    shim_dir = repo.parent / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "# Fail only for `git diff`, so the hook's producer breaks while\n"
        "# everything else behaves normally.\n"
        'if [ "${1:-}" = "diff" ]; then\n'
        '  echo "fatal: bad object deadbeef" >&2\n'
        "  exit 128\n"
        "fi\n"
        f'exec {_GIT} "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)

    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo, extra_path=shim_dir)

    assert result.returncode != 0, (
        "the hook exited 0 while `git diff` was failing, so it vouched for a "
        "commit it never inspected — fail-OPEN on Critical Rule #8. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert (
        "could not list" in result.stderr.lower() or "blocked" in result.stderr.lower()
    ), (
        "the hook refused but said nothing useful, so the operator cannot tell a "
        f"refusal from a crash: {result.stderr!r}"
    )


def test_the_shim_itself_is_not_what_causes_the_refusal(repo: Path) -> None:
    """Non-triviality for the test above: the shim must be transparent otherwise.

    If the shim broke *every* git call, the previous test would pass for the wrong
    reason — it would prove only that a wrecked PATH breaks the hook, not that a
    failing producer is now refused. So the same shim, with `diff` allowed
    through, must let an ordinary commit pass.
    """
    assert _GIT is not None
    shim_dir = repo.parent / "shim_ok"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text(f'#!/usr/bin/env bash\nexec {_GIT} "$@"\n', encoding="utf-8")
    shim.chmod(0o755)

    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo, extra_path=shim_dir)
    assert result.returncode == 0, (
        "a pass-through git shim broke the hook, so the refusal test above proves "
        f"nothing about a failing producer. stderr={result.stderr!r}"
    )


# --- Names git would quote (external review 2026-10-27, item 1.1) -----------


@pytest.mark.parametrize(
    "name",
    [
        # The reviewer's case: a byte outside ASCII, quoted under core.quotePath.
        "Björk.flac",
        # A tab is quoted whatever core.quotePath says.
        "tab\there.wav",
        # A double quote is escaped inside the quoting too.
        'say "hi".mp3',
    ],
)
def test_a_staged_audio_file_with_an_unusual_name_blocks_the_commit(
    repo: Path, name: str
) -> None:
    r"""THE regression test for item 1.1: a name git quotes must still be caught.

    The old hook read `git diff --name-only` without `-z`, so `Björk.flac` came
    back as `"Bj\303\266rk.flac"`, and an end-anchored `\.flac$` saw the closing
    quote instead of the extension. The hook said nothing and exited 0.
    """
    assert _GIT is not None
    # Pin the input. Quoting is git's default, but a contributor's global config
    # could turn it off, and then this test would pass against the old hook too.
    _git(repo, "config", "core.quotePath", "true")
    (repo / name).write_text("not audio, just a name\n", encoding="utf-8")
    _git(repo, "add", "-f", "--", name)

    # Non-triviality: prove the fixture reproduces the condition the bug needed,
    # that the plain listing really does quote this name. A name git happened
    # not to quote would pass here for the wrong reason.
    plain = subprocess.run(
        [_GIT, "diff", "--cached", "--name-only"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert plain.startswith('"') and plain.endswith('"'), (
        f"git did not quote {name!r} (it listed {plain!r}), so this case cannot "
        "tell the fixed hook from the old one"
    )

    result = _run_hook(repo)

    assert result.returncode == 1, (
        f"the hook allowed a staged audio file named {name!r}, which git quotes. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert name in result.stderr, (
        "the refusal did not name the file as it is on disk, so the operator "
        f"cannot find it: {result.stderr!r}"
    )


def test_a_non_ascii_text_file_is_allowed(repo: Path) -> None:
    """The floor for the test above: a quoted name that is NOT audio passes.

    Without it, a hook that refused every quoted name would satisfy the
    regression test while blocking an ordinary commit of `Björk notes.md`.
    """
    _git(repo, "config", "core.quotePath", "true")
    (repo / "Björk notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "Björk notes.md")

    result = _run_hook(repo)

    assert result.returncode == 0, (
        f"the hook blocked a non-ASCII text file. stderr={result.stderr!r}"
    )


# --- The shared extension list ----------------------------------------------


def _shared_extensions() -> list[str]:
    """The shared list, read the way the hook reads it, with its format checked.

    The format is part of the contract. CI's media-guard reads the same file, and
    its copy was created independently, so the bytes must be exactly one
    lowercase word per line, a final newline, and nothing else.
    """
    raw = EXTENSIONS_FILE.read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n"), (
        "audio-extensions.txt must end with exactly one newline"
    )
    entries = raw.decode("ascii").split("\n")[:-1]
    bad = [e for e in entries if not re.fullmatch(r"[a-z0-9]+", e)]
    assert not bad, f"malformed lines in audio-extensions.txt: {bad!r}"
    assert len(entries) == len(set(entries)), "duplicate lines in audio-extensions.txt"
    # Floor: 18 extensions on 2026-10-27. The list may grow; a shorter one means
    # a format was dropped, which should be a decision made here on purpose.
    assert len(entries) >= 18, f"audio-extensions.txt shrank to {entries!r}"
    return entries


def test_every_listed_extension_blocks_the_commit(repo: Path) -> None:
    """The hook really USES the shared file: each extension in it is refused.

    Behavioural rather than textual, so it holds whatever the hook's source looks
    like. One commit stages one file per extension, in upper case to keep the
    case-insensitive match honest, and every one must be named in the refusal.
    """
    names = [f"track.{ext.upper()}" for ext in _shared_extensions()]
    for name in names:
        (repo / name).write_text("not audio\n", encoding="utf-8")
    _git(repo, "add", "-f", "--", *names)

    result = _run_hook(repo)

    assert result.returncode == 1, result.stderr
    missed = [n for n in names if n not in result.stderr]
    assert not missed, f"the hook did not refuse {missed}: {result.stderr!r}"


def _hook_beside(tmp_path: Path, list_text: str | None) -> Path:
    """A copy of the real hook with `list_text` as its extension list (None: none)."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    copy = hooks / "pre-commit"
    shutil.copyfile(HOOK, copy)
    copy.chmod(0o755)
    if list_text is not None:
        (hooks / EXTENSIONS_FILE.name).write_text(list_text, encoding="utf-8")
    return copy


@pytest.mark.parametrize(
    ("label", "list_text"),
    [
        ("missing", None),
        ("empty", ""),
        ("malformed", "flac\n.wav\n"),
        ("pattern-syntax", "flac\n.*\n"),
        ("blank-line", "flac\n\nwav\n"),
    ],
)
def test_the_hook_refuses_without_a_usable_extension_list(
    repo: Path, tmp_path: Path, label: str, list_text: str | None
) -> None:
    """No list, no pass: a guard with nothing to match against passes everything.

    An ordinary text commit is staged, so the list is the only reason to refuse.
    """
    hook = _hook_beside(tmp_path, list_text)
    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")

    result = _run_hook(repo, hook=hook)

    assert result.returncode != 0, (
        f"the hook passed a commit with a {label} extension list, so it vouched "
        f"for a commit it had no way to check. stderr={result.stderr!r}"
    )
    assert "audio-extension list" in result.stderr, result.stderr


def test_a_copied_hook_with_the_real_list_behaves_normally(
    repo: Path, tmp_path: Path
) -> None:
    """Non-triviality for the test above: copying the hook is not what refuses.

    The same copy, given the real list, must pass a text commit and block audio.
    """
    hook = _hook_beside(tmp_path, EXTENSIONS_FILE.read_text(encoding="utf-8"))
    (repo / "notes.md").write_text("# text\n", encoding="utf-8")
    _git(repo, "add", "notes.md")
    assert _run_hook(repo, hook=hook).returncode == 0

    (repo / "a.flac").write_text("not audio\n", encoding="utf-8")
    _git(repo, "add", "-f", "a.flac")
    assert _run_hook(repo, hook=hook).returncode == 1


def _alternation(text: str, label: str) -> list[str]:
    r"""The extensions inside the first `\.(a|b|…)$` regular expression in `text`."""
    match = re.search(r"\\\.\(((?:[a-z0-9]+\|)+[a-z0-9]+)\)\$", text)
    assert match, f"no audio-extension pattern found in {label}; this test is broken"
    return match.group(1).split("|")


def test_every_audio_list_equals_the_shared_file() -> None:
    """One definition of "audio", and every copy of it compared, not trusted.

    `.githooks/audio-extensions.txt` is the shared list. The hook reads it (the
    behavioural test above proves that), and so does CI's media-guard. Two guards
    cannot read a repository file, so they keep their own copy:

    * `.claude/hooks/audio_guard.py`, the agent-side guard, as a compiled regular
      expression;
    * `docs/rig-scripts/platterpuscollect.sh`, which an operator downloads and runs
      on its own machine, as a `find` expression.

    Each copy is held to the file here, in the file's order, so a format added in
    one place and forgotten in another turns the suite red. Two lists maintained
    separately is how `release.yml`'s two tag-shape lists diverged for the whole
    v0.x line.
    """
    shared = _shared_extensions()

    hook_text = HOOK.read_text(encoding="utf-8")
    assert EXTENSIONS_FILE.name in hook_text, (
        "the pre-commit hook no longer names the shared list"
    )
    assert not re.search(r"\\\.\((?:[a-z0-9]+\|)+", hook_text), (
        "the pre-commit hook carries its own extension pattern again, which can "
        "drift from the shared file; read the file instead"
    )

    agent = _alternation(
        (REPO_ROOT / ".claude" / "hooks" / "audio_guard.py").read_text(
            encoding="utf-8"
        ),
        "audio_guard.py",
    )
    assert agent == shared, (
        "audio_guard.py's AUDIO pattern differs from audio-extensions.txt.\n"
        f"  shared:     {shared}\n  agent hook: {agent}"
    )

    # CI's media-guard is the server-side witness. It either reads the shared
    # file, or the pattern it still spells inline must equal the file.
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    if EXTENSIONS_FILE.name not in ci_text:
        ci = _alternation(ci_text, "ci.yml")
        assert ci == shared, (
            "ci.yml's media-guard pattern differs from audio-extensions.txt.\n"
            f"  shared: {shared}\n  ci:     {ci}"
        )

    # The rig collector spells its list as one shell assignment, which its `find`
    # expression is built from. Read the assignment, not a mention of it.
    collector_text = (
        REPO_ROOT / "docs" / "rig-scripts" / "platterpuscollect.sh"
    ).read_text(encoding="utf-8")
    assignment = re.search(r'^AUDIO_EXTS="([a-z0-9 ]+)"$', collector_text, re.MULTILINE)
    assert assignment, "no AUDIO_EXTS assignment in platterpuscollect.sh"
    collector = assignment.group(1).split()
    assert collector == shared, (
        "platterpuscollect.sh's AUDIO_EXTS differs from audio-extensions.txt.\n"
        f"  shared:    {shared}\n  collector: {collector}"
    )
    # And its `find` really is built from that list, so the assignment above is
    # not a decoration beside a hand-written expression.
    assert '-iname "*.$ext"' in collector_text and "for ext in $AUDIO_EXTS" in (
        collector_text
    ), "platterpuscollect.sh's audio find no longer uses AUDIO_EXTS"
    assert not re.search(r"-iname '\*\.(?:flac|wav|mp3)'", collector_text), (
        "platterpuscollect.sh has a hand-written audio -iname again"
    )
