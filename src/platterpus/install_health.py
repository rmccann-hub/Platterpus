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

from platterpus import cache_check_plan
from platterpus.drive_profiles import DriveProfile

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


@dataclass(frozen=True)
class DriveSetupFacts:
    """What drive setup saved for the selected drive, and whether it still holds.

    Built by `drive_setup_facts` from the drive's saved profile, so the acceptance
    run (`check_drive_facts`) and Setup & Updates (`drive_setup_line`) read one
    answer from one key rather than two answers from two (TASKS R248).
    """

    label: str
    #: The firmware revision the drive reports now ("" when it reports none).
    firmware_now: str
    #: `cache_check_plan.verdict_state`: MEASURED, NOT_MEASURED or FIRMWARE_CHANGED.
    cache_state: str
    #: The firmware the cache verdict was measured under ("" when unrecorded).
    cache_measured_under: str
    offset_saved: bool
    #: When the read offset was saved, ISO-8601 UTC ("" when unrecorded).
    offset_saved_at: str


def drive_setup_facts(drive: object, profile: DriveProfile | None) -> DriveSetupFacts:
    """The facts for ``drive`` (a DriveDescriptor) from its saved ``profile``.

    The profile is looked up by the drive's fingerprint (vendor, model, and the
    serial or WWN where the drive exposes one), so a profile found here is this
    drive's, not another of the same model's where the drive tells them apart.
    Never raises.
    """
    firmware = str(getattr(drive, "release", "") or "")
    label = (
        " ".join(
            part
            for part in (getattr(drive, "vendor", ""), getattr(drive, "model", ""))
            if part
        )
        or "the selected drive"
    )
    offset = profile.offset if profile is not None else None
    return DriveSetupFacts(
        label=label,
        firmware_now=firmware.strip(),
        cache_state=cache_check_plan.verdict_state(profile, firmware),
        cache_measured_under=(
            profile.cache_defeat_release.strip() if profile is not None else ""
        ),
        offset_saved=offset is not None,
        offset_saved_at=offset.detected_at if offset is not None else "",
    )


def check_drive_facts(facts: DriveSetupFacts | None) -> list[Finding]:
    """The selected drive's saved read offset and cache verdict.

    ``None`` means no drive is selected.
    """
    if facts is None:
        return [Finding(False, "no drive is selected, so its saved facts are unread")]
    label = facts.label
    found = [
        Finding(True, f"{label} has a saved read offset")
        if facts.offset_saved
        else Finding(False, f"{label} has no saved read offset")
    ]
    if facts.cache_state == cache_check_plan.MEASURED:
        found.append(Finding(True, f"{label} has a cache verdict for its firmware"))
    elif facts.cache_state == cache_check_plan.FIRMWARE_CHANGED:
        found.append(
            Finding(
                False,
                f"{label}'s firmware changed since its cache verdict was measured "
                f"(then {facts.cache_measured_under}, now {facts.firmware_now}); "
                "drive setup measures it again",
            )
        )
    else:
        found.append(
            Finding(
                False,
                f"{label} has no cache verdict for its current firmware "
                f"({facts.cache_state}); drive setup measures it",
            )
        )
    return found


def drive_setup_line(facts: DriveSetupFacts | None) -> str:
    """Setup & Updates' line: is there anything for drive setup to do?

    **Why (the owner, 2026-11-25, after reinstalling):** *"let users know if the
    hardware is the same as the last setup not need to run (and check if it
    is)"*. Drive facts are measured once and saved per drive and firmware (the
    owner's rule of 2026-11-12), so on the same drive and firmware there is
    nothing to redo; the line says so, checked against the drive connected now.
    The button stays for anyone who wants to run it anyway. Marked ✓, ⚠ or ⓘ,
    never colour alone.
    """
    if facts is None:
        return "ⓘ Drive setup: no drive is selected, so there is nothing to check."
    found = check_drive_facts(facts)
    failed = [f.text for f in found if f.ok is False]
    if not failed:
        firmware = f", firmware {facts.firmware_now}" if facts.firmware_now else ""
        when = facts.offset_saved_at[:10]
        on = f" on {when}" if when else ""
        return (
            f"✓ Drive setup was done for {facts.label}{firmware}{on}. This is the "
            "same drive and firmware, so there is nothing to redo."
        )
    if facts.cache_state == cache_check_plan.FIRMWARE_CHANGED:
        return (
            f"⚠ {facts.label}'s firmware changed since drive setup (then "
            f"{facts.cache_measured_under}, now {facts.firmware_now}), so run drive "
            "setup again: what it measured may no longer hold."
        )
    if not facts.offset_saved and facts.cache_state == cache_check_plan.NOT_MEASURED:
        return (
            f"⚠ Drive setup has not been run for {facts.label}. Run it once; what "
            "it measures is saved for this drive."
        )
    missing = "read offset" if not facts.offset_saved else "cache verdict"
    return (
        f"⚠ Drive setup is not finished for {facts.label}: it has no saved "
        f"{missing}. Run drive setup to measure it."
    )


def host_setup_line(report: object | None, tools: list[Finding]) -> str:
    """Setup & Updates' line: is there anything for setup to do?

    ``report`` is the last dependency check (`deps.manager.DependencyReport`, or
    ``None`` when none ran this session); ``tools`` is `check_tools`, which reads
    files only. Setup's work is done when the tools it exports are in place and
    the last complete check found nothing required missing; otherwise the line
    says which, and ``None`` is "not checked yet", never "done" (TASKS R248).
    """
    absent = [f.text.split()[0] for f in tools if f.ok is False]
    if absent:
        return (
            f"⚠ Setup is not finished: {', '.join(absent)} not in place. Run setup "
            "to install them."
        )
    if report is None:
        return (
            "ⓘ The tools setup exports are in place; the ripping container has not "
            "been checked yet in this session (Check dependencies does it)."
        )
    missing = [
        m
        for m in (getattr(report, "missing", []) or [])
        if not getattr(getattr(m, "spec", None), "optional", False)
    ]
    if missing or getattr(report, "unchecked", None):
        return (
            "⚠ The last dependency check did not find everything setup installs "
            "(see Dependencies above). Run setup to repair it."
        )
    return (
        "✓ Setup is done: the tools it installs are in place and the last check "
        "found every required one, so there is nothing to redo. Run it again only "
        "to repair an installation."
    )


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
