"""Is the installation whole? Pure checks the acceptance run reports on.

**Why this exists (the owner, 2026-11-25).** After an uninstall and a reinstall,
the menu entry and the Desktop icon pointed at a file that had moved, a disc read
was left failed after setup, and the uninstaller logged a traceback on close. The
Full acceptance run graded every rip and none of that: *"it should include
everything, not just how the rip runs. now the priority might not be same, but it
should be reported."* So these checks are graded by the run's own verb,
``expect-installed`` (`uiscript/health_verbs.py`), in a section whose severity is
declared in advance (`docs/testing.md` → *Acceptance severity*, section S).

**What each check answers.** One `Finding` per fact: ``ok=True`` held,
``ok=False`` failed, ``ok=None`` reported without a verdict (not applicable, or a
count for the reader). Every function here reads files only, never starts a
process and never touches Qt, so the verb can run it on the GUI thread, and each
never raises: a file it cannot read is a finding, not an exception.
"""

from __future__ import annotations

import os
import shlex
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: The tools setup exports to ``~/.local/bin``: a rip cannot run without these.
REQUIRED_TOOLS: Final[tuple[str, ...]] = ("cyanrip", "flac", "metaflac")
#: Exported too, but a rip runs without it (the cache check is optional).
OPTIONAL_TOOLS: Final[tuple[str, ...]] = ("cd-paranoia",)

#: How a Python traceback starts in the log: the one shape no deliberate test
#: step produces, so finding it is always a finding.
TRACEBACK_MARK: Final[str] = "Traceback (most recent call last)"


@dataclass(frozen=True)
class Finding:
    """One fact about the installation: held (True), failed (False), or reported."""

    ok: bool | None
    text: str


def exec_target(desktop_text: str) -> Path | None:
    """The program a ``.desktop`` file's ``Exec=`` line launches, or ``None``.

    The first word of the value, unquoted the way the freedesktop spec quotes it
    (which `shlex` reads: double quotes, backslash escapes). ``None`` when there
    is no ``Exec=`` line or its value cannot be split.
    """
    for line in desktop_text.splitlines():
        if not line.startswith("Exec="):
            continue
        try:
            words = shlex.split(line[len("Exec=") :])
        except ValueError:
            return None
        return Path(words[0]) if words else None
    return None


def _entry_findings(label: str, entry: Path, expected: Path | None) -> list[Finding]:
    """Whether one ``.desktop`` file exists and launches a file that is there."""
    try:
        text = entry.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return [Finding(False, f"the {label} is missing: {entry}")]
    except OSError as exc:
        return [Finding(False, f"the {label} {entry} cannot be read: {exc}")]
    target = exec_target(text)
    if target is None:
        return [Finding(False, f"the {label} {entry} has no program to launch")]
    if not target.is_file():
        return [
            Finding(
                False,
                f"the {label} launches {target}, which is not there, so it opens "
                "nothing",
            )
        ]
    if not os.access(target, os.X_OK):
        return [
            Finding(False, f"the {label} launches {target}, which is not executable")
        ]
    if expected is not None and target.resolve() != expected.resolve():
        return [
            Finding(
                False,
                f"the {label} launches {target}, not the installed app at {expected}",
            )
        ]
    return [Finding(True, f"the {label} launches {target}")]


def check_shortcuts(
    installed: Path | None,
    *,
    desktop_dir: Path,
    desktop_folder: Path | None,
    desktop_id: str,
    uninstall_name: str,
) -> list[Finding]:
    """The menu entry, the uninstaller's entry and the Desktop icon.

    ``installed`` is where the AppImage lives now (`None` when the app is not
    running as an AppImage: a source or pipx install has no shortcuts of ours, and
    that is reported, not failed). The Desktop icon is checked only where a
    Desktop folder exists, as `appimage_integration.integrate` writes it only
    there.
    """
    if installed is None:
        return [
            Finding(
                None, "not running as the AppImage, so there are no shortcuts of ours"
            )
        ]
    found = _entry_findings(
        "menu entry", desktop_dir / f"{desktop_id}.desktop", installed
    )
    found += _entry_findings(
        "uninstaller's menu entry", desktop_dir / f"{uninstall_name}.desktop", installed
    )
    if desktop_folder is not None and desktop_folder.is_dir():
        found += _entry_findings(
            "Desktop icon", desktop_folder / f"{desktop_id}.desktop", installed
        )
    else:
        found.append(Finding(None, "no Desktop folder, so no Desktop icon is expected"))
    return found


def check_tools(
    bin_dir: Path,
    required: Sequence[str] = REQUIRED_TOOLS,
    optional: Sequence[str] = OPTIONAL_TOOLS,
) -> list[Finding]:
    """Each exported tool exists in ``bin_dir`` and is executable.

    Presence only: whether the ripper is the approved build is section A's
    question, and asking it again here would be a second answer to one question.
    """
    found: list[Finding] = []
    for name, needed in [(n, True) for n in required] + [(n, False) for n in optional]:
        path = bin_dir / name
        if path.is_file() and os.access(path, os.X_OK):
            found.append(Finding(True, f"{name} is exported at {path}"))
        elif needed:
            found.append(Finding(False, f"{name} is not an executable file at {path}"))
        else:
            found.append(Finding(None, f"{name} (optional) is not exported at {path}"))
    return found


def check_drive_facts(
    drive_label: str, cache_state: str | None, measured: str, offset_saved: bool
) -> list[Finding]:
    """The selected drive's saved read offset and cache verdict.

    ``cache_state`` is `cache_check_plan.verdict_state` for this drive, compared
    with ``measured`` (that module's MEASURED), so this module needs no import of
    it. ``None`` means no drive is selected.
    """
    if cache_state is None:
        return [Finding(False, "no drive is selected, so its saved facts are unread")]
    found = [
        Finding(True, f"{drive_label} has a saved read offset")
        if offset_saved
        else Finding(False, f"{drive_label} has no saved read offset")
    ]
    if cache_state == measured:
        found.append(
            Finding(True, f"{drive_label} has a cache verdict for its firmware")
        )
    else:
        found.append(
            Finding(
                False,
                f"{drive_label} has no cache verdict for its current firmware "
                f"({cache_state}); drive setup measures it",
            )
        )
    return found


def find_tracebacks(lines: Iterable[str], limit: int = 5) -> list[str]:
    """The log lines that carry a Python traceback, up to ``limit``.

    Each hit is shortened to its first 300 characters: enough to name the logger
    and the message, which is what a reader needs to find it in the full log.
    """
    hits: list[str] = []
    for line in lines:
        if TRACEBACK_MARK in line:
            hits.append(line.strip().replace("\n", " | ")[:300])
            if len(hits) >= limit:
                break
    return hits


def count_tracebacks(lines: Iterable[str]) -> int:
    """How many log lines carry a traceback (all of them, not only the first few)."""
    return sum(1 for line in lines if TRACEBACK_MARK in line)
