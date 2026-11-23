"""The command-line uninstaller — what ``uninstall.sh`` runs.

``uninstall.sh`` used to be its own 380-line list of things to delete, which
drifted from the in-app dialog's list in both directions (TASKS R190). It is now
a thin launcher for this module, and this module reads the same footprint, the
same plan and the same engine as the dialog: one list, two front doors.

Defaults match the dialog: everything Platterpus created is removed; ``--keep-*``
keeps a group; rips and the system packages Platterpus installed go only when
asked (``--remove-rips``, ``--remove-system-packages``). ``--dry-run`` prints the
plan and changes nothing. ``--full`` is accepted for old scripts: removing
everything is the default now.

Runs without Qt, and imports nothing outside the standard library but
Platterpus itself, so the launcher can run it from a checkout with any Python
3.12 or newer.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from platterpus import appimage_integration  # imported before the .venv can go
from platterpus.deps.host_teardown import HostTeardown
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.deps.uninstall_plan import Choices, build_plan, preview_lines, summary
from platterpus.deps.uninstall_runner import UninstallRunner
from platterpus.deps.user_locations import Locations, rips_setting, safe_rips_folder
from platterpus.paths import CONFIG_PATH

log = logging.getLogger(__name__)

_GLYPH: dict[StepStatus, str] = {
    StepStatus.RAN: "✓",
    StepStatus.DONE: "ⓘ",
    StepStatus.FAILED: "⚠",
    StepStatus.CANCELLED: "•",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uninstall.sh",
        description=(
            "Uninstall Platterpus: remove everything it created on this computer, "
            "so a reinstall starts fresh. Your rips are kept unless you ask."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be removed; change nothing",
    )
    parser.add_argument("--yes", action="store_true", help="do not ask before removing")
    parser.add_argument(
        "--full",
        action="store_true",
        help="accepted for old scripts; removing everything is the default now",
    )
    parser.add_argument(
        "--keep-settings",
        action="store_true",
        help="keep settings and measured drive data",
    )
    parser.add_argument(
        "--keep-logs",
        action="store_true",
        help="keep logs, test runs and support bundles",
    )
    parser.add_argument(
        "--keep-picard", action="store_true", help="keep MusicBrainz Picard"
    )
    parser.add_argument(
        "--remove-rips",
        action="store_true",
        help="ALSO delete your rips, from the folder your settings name",
    )
    parser.add_argument(
        "--remove-system-packages",
        action="store_true",
        help="ALSO remove Distrobox/podman, only if Platterpus installed them",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="the source checkout this runs from (set by uninstall.sh)",
    )
    return parser


def _confirm(question: str, answer: str = "y") -> bool:
    """Ask on the terminal; anything but ``answer`` (case-insensitive) is no."""
    try:
        reply = input(f"{question} ")
    except EOFError:
        return False
    return reply.strip().lower() == answer.lower()


def _print_step(result: StepResult) -> None:
    if result.status is StepStatus.RUNNING:
        return
    line = f"  {_GLYPH.get(result.status, '•')} {result.title}"
    print(f"{line} — {result.detail}" if result.detail else line)


def main(argv: list[str] | None = None) -> int:
    """Run the uninstall. 0 when complete (or a dry run), 1 when anything is left."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    loc = Locations.from_environment()
    rips, refusal = safe_rips_folder(rips_setting(CONFIG_PATH), loc.home)
    repo = args.repo_root.resolve() if args.repo_root is not None else None
    venv = repo / ".venv" if repo is not None and (repo / ".venv").is_dir() else None
    runner = UninstallRunner()
    engine = HostTeardown(
        runner=runner,
        locations=loc,
        appimage=appimage_integration.appimage_path(),
        venv=venv,
        rips=rips,
        elevate="sudo",
    )
    choices = Choices(
        keep_settings=args.keep_settings,
        keep_logs=args.keep_logs,
        keep_picard=args.keep_picard,
        remove_rips=args.remove_rips and rips is not None,
        remove_system_packages=args.remove_system_packages,
    )
    print("Platterpus uninstall")
    if args.dry_run:
        print("  Mode: DRY RUN (nothing will be touched)")
    if args.remove_rips and rips is None:
        print(f"  ⚠ --remove-rips refused: {refusal}. Your rips are kept.")
    print("  Checking what is on this computer…")
    plan = build_plan(engine.scan(), choices)
    print()
    for line in preview_lines(plan):
        print(line)
    print()
    if args.dry_run or plan.nothing_to_do:
        _print_not_touched(repo, rips, choices)
        return 0
    if not args.yes and not _confirm("Remove everything under “Will remove”? [y/N]"):
        print("Nothing was removed.")
        return 0
    if choices.remove_rips and not args.yes:
        print(f"⚠ This DELETES your rips in {rips}. Make sure you have a backup.")
        if not _confirm("Type DELETE to confirm:", "DELETE"):
            print("Nothing was removed.")
            return 0
    print("Removing:")
    try:
        report = engine.run(choices, progress=_print_step)
    except KeyboardInterrupt:
        runner.cancel()
        print("Interrupted. Run the uninstaller again to finish.")
        return 1
    for line in report.leftovers:
        print(f"  ⚠ still present: {line}")
    print()
    print(summary(report))
    _print_not_touched(repo, rips, choices)
    return 0 if report.complete else 1


def _print_not_touched(repo: Path | None, rips: Path | None, choices: Choices) -> None:
    print("Not touched:")
    if repo is not None and (repo / "pyproject.toml").is_file():
        print(f"  - the clone at {repo}")
        print(f'    To remove it: cd .. && rm -rf "{repo.name}"')
    if not choices.remove_rips:
        where = rips if rips is not None else "your rips folder"
        print(f"  - your rips in {where} (--remove-rips deletes them)")
    if not choices.remove_system_packages:
        print("  - Distrobox and podman themselves")


if __name__ == "__main__":
    sys.exit(main())
