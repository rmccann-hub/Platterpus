"""What an uninstall will remove, what it keeps and why, and what it left behind.

Pure: it reads what the scanner found (:class:`Observation`, one per item of
``deps/install_footprint.footprint``) and the user's choices, and returns text
and decisions. Both uninstallers (the dialog and ``uninstall.sh``) render the
same preview from :func:`preview_lines`, so the two cannot describe one
uninstall in two ways.

**The report says what happened, not what was asked** (TASKS R190). After
removing, the engine scans again; :func:`leftovers` compares the two scans and
names everything still present that the plan meant to remove.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from platterpus.deps.install_footprint import FootprintItem, Group
from platterpus.deps.step_engine import StepResult, StepStatus


@dataclass(frozen=True)
class Observation:
    """What one scan found for one footprint item."""

    item: FootprintItem
    #: The concrete things found: paths, or a container, image, app or package name.
    present: tuple[str, ...] = ()
    #: Why the item could not be checked; empty when it could.
    unchecked: str = ""
    #: Why a present item must stay anyway (another container uses the image,
    #: an export Distrobox did not write); empty when nothing holds it.
    held: str = ""

    @property
    def removable(self) -> bool:
        """Present, checked, and nothing outside Platterpus depends on it."""
        return bool(self.present) and not self.unchecked and not self.held


@dataclass(frozen=True)
class Choices:
    """The user's choices. The defaults remove everything except rips and packages."""

    keep_settings: bool = False
    keep_logs: bool = False
    keep_picard: bool = False
    remove_rips: bool = False
    remove_system_packages: bool = False

    def keeps(self, group: Group) -> bool:
        """Whether these choices keep everything in ``group``."""
        if group is Group.SETTINGS:
            return self.keep_settings
        if group is Group.LOGS:
            return self.keep_logs
        if group is Group.PICARD:
            return self.keep_picard
        if group is Group.RIPS:
            return not self.remove_rips
        if group is Group.SYSTEM_PACKAGES:
            return not self.remove_system_packages
        return False


@dataclass(frozen=True)
class Plan:
    """The scan, split into what goes and what stays (with the reason)."""

    remove: tuple[Observation, ...] = ()
    kept: tuple[tuple[Observation, str], ...] = ()
    unchecked: tuple[Observation, ...] = ()
    absent: tuple[Observation, ...] = field(default=())

    @property
    def nothing_to_do(self) -> bool:
        return not self.remove


def build_plan(observations: tuple[Observation, ...], choices: Choices) -> Plan:
    """Decide, item by item, what this uninstall removes."""
    remove: list[Observation] = []
    kept: list[tuple[Observation, str]] = []
    unchecked: list[Observation] = []
    absent: list[Observation] = []
    for obs in observations:
        if obs.unchecked:
            unchecked.append(obs)
        elif not obs.present:
            absent.append(obs)
        elif choices.keeps(obs.item.group):
            kept.append((obs, f"you chose to keep {obs.item.group.value}"))
        elif obs.held:
            kept.append((obs, obs.held))
        else:
            remove.append(obs)
    return Plan(tuple(remove), tuple(kept), tuple(unchecked), tuple(absent))


def _things(obs: Observation) -> str:
    return ", ".join(obs.present)


def preview_lines(plan: Plan) -> list[str]:
    """The plan as lines a person reads before saying yes. Nothing is left out."""
    lines: list[str] = []
    if plan.remove:
        lines.append("Will remove:")
        lines += [f"  - {o.item.title}: {_things(o)}" for o in plan.remove]
    else:
        lines.append("Nothing of Platterpus's is left to remove.")
    if plan.kept:
        lines.append("Will keep:")
        lines += [f"  - {o.item.title}: {_things(o)} ({why})" for o, why in plan.kept]
    if plan.unchecked:
        lines.append("Could not check (left in place):")
        lines += [f"  ? {o.item.title}: {o.unchecked}" for o in plan.unchecked]
    return lines


def leftovers(plan: Plan, rescan: tuple[Observation, ...]) -> list[str]:
    """Everything the plan meant to remove that the re-scan still finds.

    Matched by item and by each concrete thing, so a folder of AppImages that
    lost two of three reports the one that stayed. An item the re-scan could
    not check is reported as unknown, not as gone.
    """
    after = {o.item.item_id: o for o in rescan}
    found: list[str] = []
    for obs in plan.remove:
        again = after.get(obs.item.item_id)
        if again is None:
            continue
        if again.held:
            continue  # kept on purpose at removal time; the results say why
        if again.unchecked:
            found.append(f"{obs.item.title}: could not check ({again.unchecked})")
            continue
        still = [thing for thing in obs.present if thing in again.present]
        if still:
            found.append(f"{obs.item.title}: {', '.join(still)}")
    return found


@dataclass(frozen=True)
class UninstallReport:
    """What one uninstall did: the plan, each removal's result, and what is left."""

    plan: Plan
    results: tuple[StepResult, ...]
    leftovers: tuple[str, ...]
    cancelled: bool = False

    @property
    def failed(self) -> tuple[StepResult, ...]:
        return tuple(r for r in self.results if r.status is StepStatus.FAILED)

    @property
    def complete(self) -> bool:
        """Everything planned is gone: nothing failed, nothing left, not cancelled."""
        return not self.failed and not self.leftovers and not self.cancelled


def summary(report: UninstallReport) -> str:
    """One sentence on how the uninstall ended, from the re-scan, not the request.

    The dialog's status line and the command line's last line, so the two
    routes cannot tell one outcome two ways. Status is never colour alone: each
    sentence starts with its glyph.
    """
    if report.complete:
        return (
            "✓ Uninstalled, and a check afterwards found nothing of Platterpus's "
            "left behind."
        )
    parts: list[str] = []
    if report.failed:
        parts.append(
            "⚠ Could not remove: " + ", ".join(r.title for r in report.failed) + "."
        )
    if report.leftovers:
        parts.append(f"⚠ {len(report.leftovers)} item(s) are still on this computer.")
    if report.cancelled:
        parts.append("ⓘ Cancelled before everything was removed.")
    if not parts:
        parts.append("⚠ The uninstall did not complete.")
    return " ".join(parts)
