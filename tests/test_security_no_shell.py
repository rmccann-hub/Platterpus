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

_SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"


def _python_files() -> list[Path]:
    return sorted(_SRC.rglob("*.py"))


def test_no_shell_true_anywhere_in_source() -> None:
    """No call in the source may pass shell=True (argv-list calls only)."""
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    """os.system / os.popen take a shell STRING — never allowed."""
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr in {"system", "popen"}
                ):
                    offenders.append(f"{path}:{node.lineno} (os.{node.func.attr})")
    assert not offenders, f"os.system/os.popen found — injection risk: {offenders}"
