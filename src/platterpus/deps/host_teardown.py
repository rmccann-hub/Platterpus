"""The uninstall engine: scan, plan, remove, re-scan. Shared by the dialog and the CLI.

The owner's requirement (2026-11-18, TASKS R190): an uninstall removes
**everything** Platterpus created, so a reinstall is truly fresh, with choices
to keep some things. What "everything" is lives in one list,
``deps/install_footprint.footprint``; this module finds which of it is present,
removes what the plan says, and then **looks again**, so the report names what
is still on disk rather than repeating what was asked.

The shape, in order:

1. :meth:`HostTeardown.scan` — one :class:`Observation` per footprint item.
   A probe that cannot answer says so (``unchecked``) and the item is left in
   place: an absence we could not verify is never reported as "not present".
2. ``uninstall_plan.build_plan`` — what goes, what stays and why.
3. :meth:`HostTeardown.remove` — each item **independently**: one failure (a
   busy container) never stops the rest, because a half-removed system is the
   worst outcome (real-user report 2026-06-26, "uninstall didn't do all"). The
   logs go last and are KEPT when anything failed, so the failure can be read.
   Every precondition that could have changed since the scan (does another
   container use the image now?) is checked again where the removal happens.
4. The menu cache is rebuilt, on every path, including failure and cancel:
   KDE serves its menu from a cache, and a stale one kept a launcher pointing
   at a deleted AppImage (real-user report 2026-09-21).
5. The re-scan; ``uninstall_plan.leftovers`` names anything still present.

Commands run through ``deps/uninstall_runner.UninstallRunner``: bounded, logged
in full, and killable, so the dialog's Cancel really stops a running command.
Never touched: the user's music (unless they tick the rips box, and then only
the folder their settings name), and Distrobox/podman themselves (unless the
install note says Platterpus installed them and they tick that box).
"""

from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Final

from platterpus.deps import system_packages_marker
from platterpus.deps.flatpak_footprint import FlatpakFootprint
from platterpus.deps.host_setup import _last_meaningful_line, _os_release_ids
from platterpus.deps.install_footprint import FootprintItem, Kind, footprint
from platterpus.deps.step_engine import StepResult, StepStatus
from platterpus.deps.uninstall_plan import (
    Choices,
    Observation,
    Plan,
    UninstallReport,
    build_plan,
    leftovers,
)
from platterpus.deps.uninstall_runner import REMOVE_TIMEOUT_S, TeardownRunner
from platterpus.deps.user_locations import Locations

log = logging.getLogger(__name__)

_ANSI: Final[re.Pattern[str]] = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_OS_RELEASE: Final[Path] = Path("/etc/os-release")
#: How much of an export to read when deciding whether Distrobox wrote it.
_EXPORT_HEAD_BYTES: Final[int] = 8192


def _default_remove_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def _default_remove_tree(path: Path) -> None:
    shutil.rmtree(path)


def _default_refresh_menu() -> None:
    """Rebuild the menu caches, fire-and-forget (``appimage_integration``'s refresh).

    Never raises: a cache that does not rebuild is a stale menu entry, not a
    reason to fail an uninstall that succeeded.
    """
    from platterpus import appimage_integration

    try:
        appimage_integration._default_refresh()
    except Exception:  # noqa: BLE001 — a menu refresh must never fail a removal
        log.warning("could not refresh the menu caches after uninstall", exc_info=True)


def container_names(listing: str) -> list[str]:
    """The NAME column of ``distrobox list``, exactly. Never raises.

    ``uninstall.sh`` used ``grep -q ripping``, which matched ``ripping-old`` and
    any line containing the word. Here the header names the column and each
    row's cell in it is compared whole.
    """
    rows = [
        [cell.strip() for cell in _ANSI.sub("", line).split("|")]
        for line in listing.splitlines()
        if "|" in line
    ]
    if not rows:
        return []
    header = [cell.upper() for cell in rows[0]]
    column = header.index("NAME") if "NAME" in header else 1
    return [row[column] for row in rows[1:] if len(row) > column and row[column]]


def package_remove_argv(
    tool: str, os_release: Path = _OS_RELEASE, elevate: str = "pkexec"
) -> list[str]:
    """The package-manager argv that removes ``tool``; ``[]`` on an unknown system.

    The mirror of ``host_setup.install_argv``, one family per line, so a package
    installed by one is removed by the matching other.
    """
    ids = _os_release_ids(os_release)
    if any(d in ids for d in ("fedora", "rhel", "centos")):
        return [elevate, "dnf", "remove", "-y", tool]
    if any(d in ids for d in ("debian", "ubuntu")):
        return [elevate, "apt-get", "remove", "-y", tool]
    if "arch" in ids:
        return [elevate, "pacman", "-R", "--noconfirm", tool]
    if "suse" in ids:
        return [elevate, "zypper", "--non-interactive", "remove", tool]
    return []


@dataclass
class HostTeardown:
    """Scans for, and removes, everything in the footprint. See the module docstring."""

    runner: TeardownRunner
    locations: Locations
    #: The running AppImage ($APPIMAGE), wherever it is; ``None`` from source.
    appimage: Path | None = None
    #: A source checkout's ``.venv``, removed too; ``None`` otherwise.
    venv: Path | None = None
    #: The rips folder, already checked by ``user_locations.safe_rips_folder``.
    rips: Path | None = None
    install_note: Path = system_packages_marker.MARKER_PATH
    os_release: Path = _OS_RELEASE
    #: ``pkexec`` from the GUI (a polkit prompt); ``sudo`` from a terminal.
    elevate: str = "pkexec"
    container_engines: tuple[str, ...] = ("podman", "docker")
    remove_file: Callable[[Path], None] = _default_remove_file
    remove_tree: Callable[[Path], None] = _default_remove_tree
    refresh_menu: Callable[[], None] = _default_refresh_menu
    flatpak: FlatpakFootprint = field(init=False)

    def __post_init__(self) -> None:
        self.flatpak = FlatpakFootprint(self.runner)

    def items(self) -> tuple[FootprintItem, ...]:
        """The footprint for this computer and these choices of input."""
        return footprint(
            self.locations,
            appimage=self.appimage,
            venv=self.venv,
            rips=self.rips,
            system_packages=system_packages_marker.read_installed(self.install_note),
        )

    # --- Scan ----------------------------------------------------------------

    def scan(self) -> tuple[Observation, ...]:
        """One observation per footprint item, in removal order."""
        return tuple(self._observe(item) for item in self.items())

    def _observe(self, item: FootprintItem) -> Observation:
        kind = item.kind
        if kind in (Kind.FILE, Kind.TREE, Kind.EXPORT, Kind.VENV_LINK):
            return self._observe_path(item)
        if kind in (Kind.MATCHING_FILES, Kind.MATCHING_TREES):
            return Observation(item, present=self._matches(item))
        if kind is Kind.CONTAINER:
            return self._observe_container(item)
        if kind is Kind.IMAGE:
            return self._observe_image(item)
        if kind is Kind.SYSTEM_PACKAGE:
            found = self.runner.which(item.name)
            return Observation(item, present=(item.name,) if found else ())
        return self.flatpak.observe(item)

    def _observe_path(self, item: FootprintItem) -> Observation:
        path = item.path
        if path is None or not (path.exists() or path.is_symlink()):
            return Observation(item)
        if item.kind is Kind.TREE and not path.is_dir():
            return Observation(item, held=f"{path} is not a folder")
        present = (str(path),)
        if item.kind is Kind.EXPORT and not _written_by_distrobox(path):
            return Observation(item, present, held="not a Distrobox export")
        if item.kind is Kind.VENV_LINK and not _links_into_a_venv(path):
            return Observation(item, present, held="not a link into a .venv")
        return Observation(item, present)

    def _matches(self, item: FootprintItem) -> tuple[str, ...]:
        folder = item.path
        if folder is None or not folder.is_dir():
            return ()
        want_dirs = item.kind is Kind.MATCHING_TREES
        pattern = item.pattern.lower()
        found: list[str] = []
        try:
            entries = sorted(folder.iterdir())
        except OSError as exc:
            log.warning("uninstall: could not list %s: %s", folder, exc)
            return ()
        for entry in entries:
            if not fnmatchcase(entry.name.lower(), pattern):
                continue
            is_dir = entry.is_dir() and not entry.is_symlink()
            if is_dir == want_dirs:
                found.append(str(entry))
        return tuple(found)

    def _observe_container(self, item: FootprintItem) -> Observation:
        if not self.runner.which("distrobox"):
            return Observation(item)
        rc, out = self.runner.run(["distrobox", "list"])
        if rc != 0:
            why = _last_meaningful_line(out) or f"exit {rc}"
            return Observation(item, unchecked=f"distrobox list failed: {why}")
        found = item.name in container_names(out)
        return Observation(item, present=(item.name,) if found else ())

    def _engine(self) -> str:
        return next((e for e in self.container_engines if self.runner.which(e)), "")

    def _image_users(self, engine: str, image: str) -> list[str] | None:
        """Containers built from ``image``; ``None`` when the engine could not say."""
        rc, out = self.runner.run(
            [
                engine,
                "ps",
                "-a",
                "--filter",
                f"ancestor={image}",
                "--format",
                "{{.Names}}",
            ]
        )
        if rc != 0:
            return None
        return [line.strip() for line in out.splitlines() if line.strip()]

    def _observe_image(self, item: FootprintItem) -> Observation:
        engine = self._engine()
        if not engine:
            return Observation(item)
        rc, out = self.runner.run([engine, "image", "inspect", item.name])
        if rc != 0:
            said = out.lower()
            if "no such image" in said or "image not known" in said:
                return Observation(item)
            why = _last_meaningful_line(out) or f"exit {rc}"
            return Observation(item, unchecked=f"{engine} image inspect failed: {why}")
        users = self._image_users(engine, item.name)
        ours = {i.name for i in self.items() if i.kind is Kind.CONTAINER}
        if users is None:
            held = "could not tell whether another container uses it"
        else:
            others = [name for name in users if name not in ours]
            held = f"used by other container(s): {', '.join(others)}" if others else ""
        return Observation(item, present=(item.name,), held=held)

    # --- Remove --------------------------------------------------------------

    def run(
        self,
        choices: Choices,
        progress: Callable[[StepResult], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> UninstallReport:
        """Scan, plan, remove, refresh the menu, and scan again."""
        plan = build_plan(self.scan(), choices)
        results, was_cancelled = self.remove(plan, progress, cancelled)
        # Unconditional, including after a failure or a cancel: the shortcut
        # files go early, so by the time anything else fails the cache is stale.
        self.refresh_menu()
        left = leftovers(plan, self.scan())
        for line in left:
            log.error("uninstall: still present after removal: %s", line)
        return UninstallReport(plan, tuple(results), tuple(left), was_cancelled)

    def remove(
        self,
        plan: Plan,
        progress: Callable[[StepResult], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> tuple[list[StepResult], bool]:
        """Remove each planned item independently. Returns (results, cancelled)."""
        results: list[StepResult] = []
        stopped = False
        for obs in plan.remove:
            item = obs.item
            if stopped or (cancelled is not None and cancelled()):
                stopped = True
                results.append(
                    StepResult(item.item_id, item.title, StepStatus.CANCELLED)
                )
                continue
            if item.keep_on_failure and any(
                r.status is StepStatus.FAILED for r in results
            ):
                detail = (
                    "kept so the failures above can be read; uninstall again once fixed"
                )
                results.append(
                    StepResult(item.item_id, item.title, StepStatus.DONE, detail)
                )
                continue
            if progress is not None:
                progress(
                    StepResult(
                        item.item_id, item.title, StepStatus.RUNNING, "removing…"
                    )
                )
            ok, detail = self._remove_one(obs)
            status = StepStatus.RAN if ok else StepStatus.FAILED
            result = StepResult(item.item_id, item.title, status, detail)
            if not ok:
                log.error("uninstall: %s failed: %s", item.item_id, detail)
            results.append(result)
            if progress is not None:
                progress(result)
        return results, stopped

    def _remove_one(self, obs: Observation) -> tuple[bool, str]:
        item = obs.item
        kind = item.kind
        if kind in (Kind.TREE, Kind.MATCHING_TREES):
            return self._remove_paths(obs.present, self.remove_tree)
        if kind in (Kind.FILE, Kind.MATCHING_FILES, Kind.EXPORT, Kind.VENV_LINK):
            return self._remove_paths(obs.present, self.remove_file)
        if kind is Kind.CONTAINER:
            return self._command(["distrobox", "rm", "--force", item.name], item.name)
        if kind is Kind.IMAGE:
            engine = self._engine()
            users = self._image_users(engine, item.name) if engine else None
            if users is None:
                return True, "kept: could not tell whether another container uses it"
            if users:
                return True, f"kept: used by other container(s): {', '.join(users)}"
            return self._command([engine, "rmi", item.name], item.name)
        if kind is Kind.SYSTEM_PACKAGE:
            argv = package_remove_argv(item.name, self.os_release, self.elevate)
            if not argv:
                return False, (
                    f"no automatic removal on this system; remove {item.name} with "
                    "your package manager"
                )
            ok, detail = self._command(argv, item.name)
            if ok:
                system_packages_marker.forget_installed((item.name,), self.install_note)
            return ok, detail
        return self.flatpak.remove(item, obs.present)

    def _command(self, argv: list[str], what: str) -> tuple[bool, str]:
        rc, out = self.runner.run(argv, timeout=REMOVE_TIMEOUT_S)
        if rc != 0:
            return False, _last_meaningful_line(out) or f"exit {rc}"
        return True, f"removed {what}"

    @staticmethod
    def _remove_paths(
        present: tuple[str, ...], remover: Callable[[Path], None]
    ) -> tuple[bool, str]:
        """Remove each path; carry on past a failure and report every one."""
        removed: list[str] = []
        failures: list[str] = []
        for text in present:
            path = Path(text)
            if not (path.exists() or path.is_symlink()):
                removed.append(f"{text} (already gone)")
                continue
            try:
                remover(path)
                removed.append(text)
            except OSError as exc:
                failures.append(f"could not remove {text}: {exc}")
        if failures:
            return False, "; ".join(failures)
        return True, "removed " + ", ".join(removed)


def _written_by_distrobox(path: Path) -> bool:
    """Whether a ``~/.local/bin`` file is a Distrobox export (it names distrobox)."""
    try:
        with path.open("rb") as handle:
            head = handle.read(_EXPORT_HEAD_BYTES)
    except OSError:
        return False
    return b"distrobox" in head


def _links_into_a_venv(path: Path) -> bool:
    """Whether ``path`` is a symlink into a ``.venv`` (dev-setup.sh's CLI link)."""
    if not path.is_symlink():
        return False
    try:
        target = path.readlink()
    except OSError:
        return False
    return ".venv" in target.parts
