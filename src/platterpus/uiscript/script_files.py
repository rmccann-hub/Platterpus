"""Script files a person brings: their scripts folder, and the check every file passes.

**The owner's design** (TASKS R188, 2026-11-17): the Run tests screen lists the
pre-built tests (``uiscript/prebuilt.py``) and then *a scripts folder of the
owner's (`~/.config/platterpus/scripts/`, scanned at start)*, each marked as
theirs; its third tab runs *a custom script file (any extension, checked by
content: plain UTF-8, a size cap, every line valid before Run enables)*.

:func:`user_scripts` is the scan and :func:`check_script_file` is that one check,
used for a file from the folder and a file chosen by hand alike, so the two
cannot disagree about what may run. Run stays disabled until it passes, and the
screen shows its problems, each with its line number.

Pure and Qt-free. Reading is bounded twice over: a file's size is checked
before it is read, and at most :data:`MAX_USER_SCRIPTS` files are listed. Each
function returns a problem rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.paths import CONFIG_DIR
from platterpus.uiscript.run_block import expand_run_blocks
from platterpus.uiscript.script import parse

#: The owner's scripts folder, scanned when the Run tests screen opens.
USER_SCRIPTS_DIR: Final[Path] = CONFIG_DIR / "scripts"

#: The largest script file the screen will accept, in bytes. The Full run is
#: about 107 KB; four times that is room to grow, and a file larger still is not
#: a script somebody wrote.
MAX_SCRIPT_BYTES: Final[int] = 512 * 1024

#: The most files listed from the owner's folder: a folder of thousands is a
#: mistake, and listing them all would make the screen slow to open.
MAX_USER_SCRIPTS: Final[int] = 200


@dataclass(frozen=True)
class ScriptFileCheck:
    """Whether a script file may be run, and if not, why."""

    path: Path
    text: str = ""
    #: Every reason it may not run; empty when it may.
    problems: tuple[str, ...] = ()
    steps: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems


def check_script_file(path: Path) -> ScriptFileCheck:
    """Read ``path`` and say whether it may run. Never raises.

    By content, not by name (the owner, 2026-11-17: *any extension, checked by
    content*): plain UTF-8, at most :data:`MAX_SCRIPT_BYTES`, and every line a
    valid step once ``run-block`` lines are expanded. At most the first five
    bad lines are named, with their line numbers.
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        return ScriptFileCheck(path, problems=(f"cannot read {path}: {exc}",))
    if size > MAX_SCRIPT_BYTES:
        return ScriptFileCheck(
            path,
            problems=(
                f"{path.name} is {size:,} bytes; a script may be at most "
                f"{MAX_SCRIPT_BYTES:,}",
            ),
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return ScriptFileCheck(path, problems=(f"cannot read {path}: {exc}",))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ScriptFileCheck(
            path,
            problems=(
                f"{path.name} is not plain UTF-8 text (byte {exc.start} cannot be "
                "read), so it is not a script",
            ),
        )
    if "\x00" in text:
        return ScriptFileCheck(
            path, problems=(f"{path.name} holds a NUL byte, so it is not text",)
        )
    steps = expand_run_blocks(parse(text)).steps
    bad = [step for step in steps if not step.ok]
    if not steps:
        return ScriptFileCheck(path, text, (f"{path.name} has no steps to run",))
    problems = tuple(
        f"line {step.line_no}: {step.error or 'not a step'}" for step in bad[:5]
    )
    if len(bad) > 5:
        problems += (f"and {len(bad) - 5} more line(s) like these",)
    return ScriptFileCheck(path, text, problems, len(steps))


def user_scripts(folder: Path = USER_SCRIPTS_DIR) -> tuple[Path, ...]:
    """The owner's script files, by name; empty when the folder is absent.

    Every regular file, whatever its extension: each is checked by content when
    it is chosen. Hidden files are left out (an editor's swap file is not a
    script), and at most :data:`MAX_USER_SCRIPTS` are listed.
    """
    try:
        entries = sorted(folder.iterdir(), key=lambda p: p.name.casefold())
    except OSError:
        return ()
    found: list[Path] = []
    for entry in entries:
        if entry.name.startswith("."):
            continue
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        found.append(entry)
        if len(found) >= MAX_USER_SCRIPTS:
            break
    return tuple(found)
