"""Security guard: Platterpus must never run a subprocess through a shell.

The user's bar (2026-07-02): "we don't need exploits on our software from
inputs." The single biggest injection surface for a tool that shells out to
cyanrip/flac/metaflac/ffmpeg with user- and MusicBrainz-supplied strings would be
``subprocess(..., shell=True)`` — then a crafted album title or path could inject
a command. We structurally forbid it: every subprocess call passes an **argv
list** with ``shell=False`` (the default), so arguments are never re-parsed by a
shell no matter what characters they contain.

This is a static guard over the whole source tree — enforced in CI, so it can't
regress. It's the automated backstop behind the "validate every input" rule: even
if a validation gap ever let a weird string through, there's no shell for it to
escape into."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
# Scan the shipped package AND the developer/CLI entry points that also shell
# out — the injection surface isn't only in src/. `scripts/` holds standalone
# CLIs (preflight, ctdb_verify, …) and `build/` the packaging helpers, both of
# which invoke external tools. (This is how #8's blocking-behind-indirection and
# the "no-shell guard was src/-only" gap were closed — audit #16.)
_BUILD_LIB = _ROOT / "build" / "lib"  # generated copy of src/ — skip it
_SCAN_ROOTS = (_ROOT / "src" / "platterpus", _ROOT / "scripts", _ROOT / "build")


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            # Skip the setuptools-generated duplicate under build/lib/ (double
            # scanning src/) and any bytecode cache dir.
            if _BUILD_LIB in path.parents or "__pycache__" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def _looks_like_shell(path: Path) -> bool:
    """True for a `.sh`, or an EXTENSIONLESS file with a shell shebang.

    The extensionless half is not hypothetical tidiness. `.githooks/pre-commit`
    is a bash script with no extension, `CLAUDE.md` calls it *"the canonical
    guard"* for Critical Rule #8 — and a `rglob("*.sh")` never saw it. So the one
    test checking shell hygiene silently excluded the most consequential shell
    script in the repository, and an audit later found it failing **open** (a
    `|| true` that absorbed its producer's failure as well as grep's no-match).
    A scan that cannot see a file cannot report anything about it.
    """
    if path.suffix == ".sh":
        return True
    if path.suffix:
        return False
    try:
        first_line = path.open("rb").readline(200).decode("utf-8", "replace")
    except OSError:
        return False
    return first_line.startswith("#!") and "sh" in first_line


#: Received handshake artifacts. **Excluded from the shell-hygiene sweeps, and the
#: scope of the exclusion is the reason it is allowed.**
#:
#: A file under `docs/handshake/inbound/` is a RECORD of what the other project
#: sent, byte-identical on purpose — the envelope format carries a SHA-256 per
#: part precisely so a receiver can prove it did not alter one. Editing such a
#: file to add `set -e` would falsify the record, and it would falsify it in the
#: one direction that matters: a peer's artifact is evidence about *them*.
#:
#: This is a narrowing of a sweep, so it is written down rather than done quietly
#: (`CLAUDE.md` — scoping a sweep is fine; scoping it silently while the rule
#: claims everything is the defect). Two things keep it honest: it covers exactly
#: one directory, and `test_the_inbound_exclusion_covers_only_received_records`
#: below asserts nothing of OURS can hide behind it.
#:
#: If a received script's hygiene is worth changing, the route is a handshake lap
#: asking them to change it — not an edit here.
_INBOUND_RECORDS: str = "docs/handshake/inbound"


def _is_received_record(path: Path) -> bool:
    """Whether `path` is an artifact another project sent us, not code we ship."""
    return _INBOUND_RECORDS in path.relative_to(_ROOT).as_posix()


def _shell_scripts() -> list[Path]:
    """Every shipped shell script, minus generated/vendored trees we don't own.

    "Shipped" excludes received handshake artifacts — see `_INBOUND_RECORDS`.
    """
    skip = {".git", "venv", ".venv", "node_modules", "__pycache__"}
    scripts: list[Path] = []
    for path in _ROOT.rglob("*"):
        if not path.is_file():
            continue
        if _BUILD_LIB in path.parents or skip.intersection(path.parts):
            continue
        if _is_received_record(path):
            continue
        if _looks_like_shell(path):
            scripts.append(path)
    return sorted(scripts)


def test_the_inbound_exclusion_covers_only_received_records() -> None:
    """The exclusion must not be a hole anything of ours can fall through.

    A path-substring skip is exactly the shape that quietly grows to cover code
    it was never meant to. Asserted two ways: nothing outside the inbound
    directory is excluded, and the sweep still sees every script we actually ship.
    """
    excluded = [
        p
        for p in _ROOT.rglob("*")
        if p.is_file() and _looks_like_shell(p) and _is_received_record(p)
    ]
    for path in excluded:
        rel = path.relative_to(_ROOT).as_posix()
        assert rel.startswith(_INBOUND_RECORDS + "/"), (
            f"{rel} is being excluded from the shell-hygiene sweep but is not a "
            "received handshake record"
        )
    ours = {p.relative_to(_ROOT).as_posix() for p in _shell_scripts()}
    assert not any(o.startswith(_INBOUND_RECORDS) for o in ours)
    # Floor, so this cannot pass by the sweep having gone blind.
    assert len(ours) >= _MIN_SHELL_SCRIPTS, sorted(ours)


#: Floor for the shell scan. 13 today (12 `*.sh` + `.githooks/pre-commit`). The
#: previous floor was `assert scripts` — a floor of one, which a glob matching a
#: single stray file would satisfy.
_MIN_SHELL_SCRIPTS: int = 10

#: Scripts that legitimately do NOT set `pipefail`, each with the technical reason.
#: A ratchet: it may shrink, never grow. Both entries are the same real hazard —
#: `producer | head -1` makes the producer see SIGPIPE when `head` exits early, so
#: under `pipefail` + `set -e` the script would abort on a working command. That is
#: a reason to omit pipefail, not an oversight, and it is written down so the next
#: reader does not "fix" it and break a launcher.
_NO_PIPEFAIL_ALLOWED: dict[str, str] = {
    "build/python-appimage/entrypoint.sh": (
        'line 13 is `ls "$APPDIR"/opt/python*/bin/python* | head -1`; under '
        "pipefail the early-exiting `head` makes `ls` fail and `set -e` would "
        "abort the AppImage launcher on a healthy install"
    ),
    "docs/rig-scripts/platterpuscollect.sh": (
        "line 60 is `... | sort -rn | head -1 | cut ...`, the same early-exit "
        "SIGPIPE shape; the script runs on an operator's machine where aborting "
        "mid-collection loses the bundle it exists to produce"
    ),
}


# Floor for the source scans. Without one, every "assert no offenders" test below
# passes by finding nothing — a wrong scan root, a rename of src/platterpus, or a
# broken glob would turn the whole guard green while checking zero files. (CLAUDE.md
# "How to stop shipping the next one": *can this check be satisfied by finding
# nothing? Then give it a floor.*) The tree holds well over a hundred modules; 60 is
# a deliberately loose floor that still fails instantly on an empty/wrong scan.
_MIN_PYTHON_FILES: int = 60
# Likewise for the call-site scan: the tool inventory in
# docs/dependency-contracts.md alone names ~10 external tools, and the audit of
# 2026-07-31 counted 18 subprocess call sites. A scan that finds none is broken.
_MIN_SUBPROCESS_CALLS: int = 12

# Every API that takes a command as a SHELL STRING (or re-execs through one).
# os.system/os.popen were already covered; the exec/spawn family was not, and
# `os.spawnl(os.P_NOWAIT, "/bin/sh", ...)` is the same hole with a different name.
_FORBIDDEN_OS_CALLS: frozenset[str] = frozenset(
    {"system", "popen"}
    | {f"exec{suffix}" for suffix in ("l", "le", "lp", "lpe", "v", "ve", "vp", "vpe")}
    | {f"spawn{suffix}" for suffix in ("l", "le", "lp", "lpe", "v", "ve", "vp", "vpe")}
)

_SUBPROCESS_CALLS: frozenset[str] = frozenset(
    {"run", "Popen", "call", "check_call", "check_output"}
)


def _parsed_sources() -> list[tuple[Path, ast.Module]]:
    """Every scanned file with its AST, with a floor so an empty scan can't pass."""
    files = _python_files()
    assert len(files) >= _MIN_PYTHON_FILES, (
        f"only {len(files)} Python file(s) scanned (expected >= "
        f"{_MIN_PYTHON_FILES}) — the scan roots {_SCAN_ROOTS} are wrong, so "
        "every guard in this file would pass by examining nothing"
    )
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in files
    ]


def _subprocess_calls() -> list[tuple[Path, ast.Call, str]]:
    """Every `subprocess.<run|Popen|...>` call site, with a floor."""
    found: list[tuple[Path, ast.Call, str]] = []
    for path, tree in _parsed_sources():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                not isinstance(func, ast.Attribute)
                or func.attr not in _SUBPROCESS_CALLS
            ):
                continue
            base = func.value
            if isinstance(base, ast.Name) and base.id == "subprocess":
                found.append((path, node, func.attr))
    assert len(found) >= _MIN_SUBPROCESS_CALLS, (
        f"only {len(found)} subprocess call site(s) found (expected >= "
        f"{_MIN_SUBPROCESS_CALLS}) — the detector is not seeing the real call "
        "sites, so 'no offenders' means nothing"
    )
    return found


def test_no_shell_true_anywhere_in_source() -> None:
    """No call in the source may pass shell=True (argv-list calls only)."""
    offenders: list[str] = []
    for path, tree in _parsed_sources():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg == "shell":
                    # Flag anything that isn't an explicit `shell=False`.
                    is_false = (
                        isinstance(kw.value, ast.Constant) and kw.value.value is False
                    )
                    if not is_false:
                        offenders.append(f"{path}:{node.lineno}")
    assert not offenders, f"shell= (not False) found — injection risk: {offenders}"


def test_source_has_no_os_system_or_popen_shell_string() -> None:
    """os.system / os.popen / os.exec* / os.spawn* — never allowed.

    os.system and os.popen take a shell STRING outright. The exec/spawn family
    doesn't *have* to, but `os.execl("/bin/sh", "sh", "-c", cmd)` reintroduces
    exactly the shell we forbid, and nothing in this codebase needs either family
    (subprocess covers every case), so the whole surface is banned rather than
    audited call by call.
    """
    offenders: list[str] = []
    for path, tree in _parsed_sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr in _FORBIDDEN_OS_CALLS
                ):
                    offenders.append(f"{path}:{node.lineno} (os.{node.func.attr})")
    assert not offenders, (
        f"os.system/popen/exec*/spawn* found — injection risk: {offenders}"
    )


def test_every_subprocess_call_passes_a_list_not_a_built_string() -> None:
    """The command must be an argv *list*, never a string built by concatenation.

    `shell=False` (the default) is only half the guarantee. A single **string**
    first argument is still legal for `subprocess.run` — POSIX then execs a file
    whose name is that whole string — so `subprocess.run(f"cyanrip -d {device}")`
    passes the shell=True guard while quietly depending on the string's contents.
    An f-string, a `+`/`%` concatenation, or a `" ".join(...)` in the command slot
    is the shape that precedes an injection bug, so it's forbidden structurally
    rather than left to review.

    Accepted: a list/tuple literal, or a Name/Attribute/Subscript/Starred/Call
    holding one (`argv`, `self._cmd`, `_pkill_arglists()[0]`, `prefix + args`).
    A `+` of two lists is indistinguishable from a `+` of two strings in the AST,
    so a BinOp is allowed only for `+`; `%` and f-strings are always rejected.
    """
    offenders: list[str] = []
    for path, node, attr in _subprocess_calls():
        if not node.args:
            # Keyword-only form, e.g. subprocess.run(args=argv). Rare; check the
            # keyword the same way rather than silently skipping it.
            arg = next((kw.value for kw in node.keywords if kw.arg == "args"), None)
            if arg is None:
                offenders.append(f"{path}:{node.lineno} subprocess.{attr} — no command")
                continue
        else:
            arg = node.args[0]
        bad_shape = (
            isinstance(arg, ast.JoinedStr)  # f-string
            or (isinstance(arg, ast.Constant) and isinstance(arg.value, str))
            or (isinstance(arg, ast.BinOp) and not isinstance(arg.op, ast.Add))
            or (
                # "…".join(parts) / str.format(...) in the command slot
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and arg.func.attr in {"join", "format"}
            )
        )
        if bad_shape:
            offenders.append(
                f"{path}:{node.lineno} subprocess.{attr} — command built as a "
                f"string ({type(arg).__name__})"
            )
    assert not offenders, (
        f"subprocess command must be an argv list, not a built string: {offenders}"
    )


def _set_option_lines(text: str) -> list[str]:
    """Real `set -...` lines — not comments, not prose that mentions one.

    The previous version of the errexit test asked `"set -e" not in text`, which a
    **comment** satisfies. Its docstring meanwhile claimed to be "a regression lock
    on the 'all scripts use set -euo pipefail' property" — a stronger claim than
    the substring it checked, and the gap is exactly this project's *"can it be
    satisfied by the wrong thing?"* shape: a label matched where a subject was
    needed. Anchoring to a statement is the difference between "the file mentions
    errexit" and "the file enables it".
    """
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"^\s*set\s+-", line) and not line.lstrip().startswith("#")
    ]


def test_shell_scripts_enable_errexit() -> None:
    """Every shipped shell script must ENABLE errexit, in a real `set` statement.

    So a failed step aborts instead of silently continuing — the shell-side
    analogue of the no-shell guard. A structural minimum, not a full shellcheck.
    """
    scripts = _shell_scripts()
    assert len(scripts) >= _MIN_SHELL_SCRIPTS, (
        f"the scan found only {len(scripts)} shell scripts (floor "
        f"{_MIN_SHELL_SCRIPTS}) — the roots or the shebang detection are wrong, "
        "so every finding here is meaningless"
    )
    offenders: list[str] = []
    for path in scripts:
        flags = "".join(
            line.split()[1].lstrip("-")
            for line in _set_option_lines(path.read_text(encoding="utf-8"))
            if len(line.split()) > 1
        )
        if "e" not in flags:
            offenders.append(str(path.relative_to(_ROOT)))
    assert not offenders, (
        "these shell scripts never enable errexit in a real `set -` statement, so "
        f"a failed command continues silently: {offenders}"
    )


def test_shell_scripts_enable_pipefail_or_say_why_not() -> None:
    """`set -e` alone does not catch a failure inside a pipeline.

    This is the half the old test claimed and did not check. It matters here
    concretely: the media guard's `producer | grep ... || true` discarded the
    producer's failure, and the guards that must never fail open are shell.

    The allowlist carries a written technical reason per entry and may shrink,
    never grow — the same ratchet shape as the ripper spawn-site enumeration.
    """
    scripts = _shell_scripts()
    assert len(scripts) >= _MIN_SHELL_SCRIPTS, "scan is broken; see the errexit test"

    missing: list[str] = []
    for path in scripts:
        relative = str(path.relative_to(_ROOT))
        has_pipefail = any(
            "pipefail" in line
            for line in _set_option_lines(path.read_text(encoding="utf-8"))
        )
        if not has_pipefail and relative not in _NO_PIPEFAIL_ALLOWED:
            missing.append(relative)
    assert not missing, (
        "these shell scripts do not set `pipefail`, so a failure in the middle of "
        "a pipeline is invisible. Add it, or add an allowlist entry to "
        "_NO_PIPEFAIL_ALLOWED with the technical reason:\n  " + "\n  ".join(missing)
    )

    # The other direction of the ratchet: an allowlist entry whose script gained
    # pipefail (or vanished) must be removed, or the list quietly describes a repo
    # that has moved on.
    known = {str(p.relative_to(_ROOT)) for p in scripts}
    stale = [
        name
        for name in _NO_PIPEFAIL_ALLOWED
        if name not in known
        or any(
            "pipefail" in line
            for line in _set_option_lines((_ROOT / name).read_text(encoding="utf-8"))
        )
    ]
    assert not stale, (
        "these _NO_PIPEFAIL_ALLOWED entries are stale — the script now sets "
        f"pipefail, or no longer exists. Remove them: {stale}"
    )
    for name, reason in _NO_PIPEFAIL_ALLOWED.items():
        assert len(reason) >= 40, (
            f"{name}'s allowlist reason is too short to be a reason: {reason!r}"
        )


def test_a_commented_set_line_does_not_count_as_enabling_anything() -> None:
    """Pinned directly, because a revert would NOT show this.

    Every script in the tree really does enable errexit, so swapping the anchored
    matcher back for the old `"set -e" in text` substring breaks nothing today —
    the weakness only bites the first time somebody writes about `set -e` in a
    comment without setting it. That is the invisible kind of decay, so the
    property is asserted against constructed input rather than left to a future
    accident to reveal.
    """
    commented = "#!/usr/bin/env bash\n# set -euo pipefail is the repo rule\necho hi\n"
    assert _set_option_lines(commented) == [], (
        "a comment mentioning `set -euo pipefail` was read as enabling it — the "
        "exact label-instead-of-subject failure this matcher replaced"
    )
    real = "#!/usr/bin/env bash\nset -euo pipefail\necho hi\n"
    assert _set_option_lines(real) == ["set -euo pipefail"], (
        "a real `set` statement was not recognised, so the check now passes "
        "nothing and would report every script as an offender"
    )
    indented = "#!/bin/sh\n    set -e\n"
    assert _set_option_lines(indented) == ["set -e"], (
        "an indented `set -e` (inside a function or an if) was missed"
    )


def test_the_canonical_media_guard_hook_is_in_scope() -> None:
    """The extensionless hook must be swept, and this says so out loud.

    `rglob("*.sh")` never matched `.githooks/pre-commit`, so the only shell-hygiene
    test in the repo excluded the script `CLAUDE.md` calls the canonical guard for
    Critical Rule #8 — and it was later found failing open. A scan's blind spot is
    invisible by construction, so the fix needs a test that names the file rather
    than trusting the glob.
    """
    hook = _ROOT / ".githooks" / "pre-commit"
    assert hook.is_file(), "the Rule #8 pre-commit hook is missing entirely"
    assert hook in _shell_scripts(), (
        "the shell scan does not include .githooks/pre-commit, so nothing here "
        "checks the guard that enforces the one rule with legal consequences"
    )
