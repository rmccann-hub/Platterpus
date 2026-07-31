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


def _shell_scripts() -> list[Path]:
    """Every shipped *.sh, minus generated/vendored trees we don't own."""
    skip = {".git", "venv", ".venv", "node_modules", "__pycache__"}
    scripts: list[Path] = []
    for path in _ROOT.rglob("*.sh"):
        if _BUILD_LIB in path.parents or skip.intersection(path.parts):
            continue
        scripts.append(path)
    return sorted(scripts)


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


def test_shell_scripts_enable_errexit() -> None:
    """Every shipped shell script must enable errexit (``set -e`` / ``-euo
    pipefail``) so a failed step aborts instead of silently continuing — the
    shell-side analogue of the no-shell guard. A structural minimum enforced in
    CI (not a full shellcheck), and a regression lock on the "all scripts use
    set -euo pipefail" property (audit §B verified-clean)."""
    scripts = _shell_scripts()
    assert scripts, "no shell scripts found — scan roots are wrong"
    offenders = [
        str(path)
        for path in scripts
        if "set -e" not in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"shell scripts missing `set -e` (errexit): {offenders}"
