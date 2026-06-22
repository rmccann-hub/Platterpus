"""Host-stack teardown — the in-app Uninstaller's engine (reverse of setup).

The user's requirement (2026-06-08): remove everything *this app* put on the
machine — menu/desktop shortcuts, host-exported binaries, the `ripping`
container (with whipper/cyanrip inside it), optionally `whipper.conf` and the
AppImage file itself, and finally the GUI's own config + logs — while
**keeping Distrobox/podman and all music untouched**. Distrobox/podman are
general-purpose tools the user may rely on for other containers, and music is
sacred; neither is ever listed here.

This is the *teardown arm* of the dependency self-management subsystem
(Critical Rule #6), mirroring ``deps/host_setup.py``: idempotent steps (each
checks "anything left to remove?" first), an injectable ``CommandRunner`` for
the one container command, injectable file/tree removers for everything else,
dry-run support, and per-step :class:`StepResult` reporting — so the engine
is fully unit-testable and the GUI shows live progress.

Step order matters: the GUI's own config/logs go LAST, so if an earlier step
fails the log file still exists to debug with.

Not handled here (script-only concerns): the dev `.venv/` and the cloned
repo — `uninstall.sh` covers those; a packaged app doesn't know a repo root.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from whipper_gui import appimage_integration
from whipper_gui.deps.host_setup import (
    DEFAULT_CONTAINER,
    _last_meaningful_line,
)
from whipper_gui.deps.step_engine import (
    CommandRunner,
    StepResult,
    StepStatus,
)
from whipper_gui.paths import (
    CONFIG_DIR,
    CYANRIP_BINARY_DEFAULT,
    LOG_DIR,
    WHIPPER_BINARY_DEFAULT,
    WHIPPER_CONFIG_PATH,
)

log = logging.getLogger(__name__)


def _default_remove_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def _default_remove_tree(path: Path) -> None:
    shutil.rmtree(path)


@dataclass
class HostTeardown:
    """Plans and runs the uninstall (idempotently). See module docstring."""

    runner: CommandRunner
    container: str = DEFAULT_CONTAINER
    # What the optional checkboxes control. All default ON — "remove all our
    # stuff" is the user's stated goal; the dialog lets them keep pieces.
    remove_container: bool = True
    remove_whipper_config: bool = True
    # The running AppImage file ($APPIMAGE), or None when running from
    # source/pipx — then there's no AppImage step at all.
    appimage: Path | None = None

    # Filesystem locations, injectable for tests (defaults = the real ones).
    gui_config_dir: Path = CONFIG_DIR
    gui_data_dir: Path = LOG_DIR
    whipper_config_dir: Path = field(default_factory=lambda: WHIPPER_CONFIG_PATH.parent)
    bin_dir: Path = field(default_factory=lambda: WHIPPER_BINARY_DEFAULT.parent)
    desktop_dir: Path = field(default_factory=lambda: appimage_integration.DESKTOP_DIR)
    icon_dir: Path = field(default_factory=lambda: appimage_integration.ICON_DIR)
    desktop_folder: Path = field(
        default_factory=lambda: appimage_integration.DESKTOP_FOLDER
    )
    apps_dir: Path = field(default_factory=lambda: Path.home() / "Applications")

    # Injectable removers so tests never touch the real filesystem and the
    # engine never needs root (everything we own is user-level).
    remove_file: Callable[[Path], None] = _default_remove_file
    remove_tree: Callable[[Path], None] = _default_remove_tree

    STEP_IDS: tuple[str, ...] = field(default=(), init=False)

    def __post_init__(self) -> None:
        steps = ["shortcuts", "exports"]
        if self.remove_container:
            steps.append("container")
        if self.remove_whipper_config:
            steps.append("whipper_config")
        # The AppImage step covers the running file ($APPIMAGE) AND the
        # settled copy integration moves into ~/Applications — so an
        # uninstall finds the app even when started from a different copy
        # (or from source) after the file was relocated.
        if self.appimage is not None or self.runner.exists(
            self.apps_dir / appimage_integration.CANONICAL_APPIMAGE_NAME
        ):
            steps.append("appimage")
        steps.append("app_data")  # always last — keeps the log alive longest
        self.STEP_IDS = tuple(steps)

    def _appimage_targets(self) -> list[Path]:
        """The AppImage file(s) to remove: the running one and the canonical
        ~/Applications copy (deduplicated — usually the same file)."""
        targets: list[Path] = []
        if self.appimage is not None:
            targets.append(self.appimage)
        canonical = self.apps_dir / appimage_integration.CANONICAL_APPIMAGE_NAME
        if canonical not in targets:
            targets.append(canonical)
        return targets

    # --- What each step targets ---------------------------------------------

    def _shortcut_files(self) -> list[Path]:
        """Menu entries, desktop icons, launcher art, the staged uninstall
        launcher, and the dev CLI symlink — every shortcut-ish artifact any
        install path (AppImage self-integration, install-appimage.sh,
        dev-setup.sh) may have created."""
        name = appimage_integration.DESKTOP_ID  # "whipper-gui"
        return [
            self.desktop_dir / f"{name}.desktop",
            self.desktop_dir / f"{name}-uninstall.desktop",
            self.desktop_folder / f"{name}.desktop",
            self.icon_dir / f"{name}.png",
            self.apps_dir / f"{name}-uninstall.sh",
            self.bin_dir / "whipper-gui",
        ]

    def _export_files(self) -> list[Path]:
        """The host-exported wrappers distrobox-export wrote."""
        return [
            self.bin_dir / WHIPPER_BINARY_DEFAULT.name,
            self.bin_dir / "metaflac",
            self.bin_dir / CYANRIP_BINARY_DEFAULT.name,
        ]

    def _tree_targets(self, step_id: str) -> list[Path]:
        if step_id == "whipper_config":
            return [self.whipper_config_dir]
        if step_id == "app_data":
            return [self.gui_config_dir, self.gui_data_dir]
        raise ValueError(step_id)  # pragma: no cover

    # --- Probes ("is there anything left to remove?") ------------------------

    def _container_exists(self) -> bool:
        if not self.runner.which("distrobox"):
            return False
        rc, out = self.runner.run(["distrobox", "list"])
        if rc != 0:
            return False
        return any(self.container in line.split() for line in out.splitlines())

    def _is_done(self, step_id: str) -> bool:
        if step_id == "shortcuts":
            return not any(self.runner.exists(p) for p in self._shortcut_files())
        if step_id == "exports":
            return not any(self.runner.exists(p) for p in self._export_files())
        if step_id == "container":
            return not self._container_exists()
        if step_id == "appimage":
            return not any(self.runner.exists(p) for p in self._appimage_targets())
        return not any(
            self.runner.exists(p) for p in self._tree_targets(step_id)
        )  # whipper_config / app_data

    def is_complete(self) -> bool:
        """True when nothing this engine targets remains."""
        return all(self._is_done(step) for step in self.STEP_IDS)

    _TITLES: dict[str, str] = field(
        default_factory=lambda: {
            "shortcuts": "Menu + desktop shortcuts",
            "exports": "whipper/metaflac/cyanrip in ~/.local/bin",
            "container": f"'{DEFAULT_CONTAINER}' container (whipper inside it)",
            "whipper_config": "whipper.conf (drive calibration)",
            "appimage": "The AppImage file itself",
            "app_data": "Whipper GUI settings + logs",
        },
        init=False,
    )

    # --- Actions -------------------------------------------------------------

    def _remove_paths(self, files: list[Path], trees: list[Path]) -> tuple[bool, str]:
        """Remove what exists; report what was removed or the first error."""
        removed: list[str] = []
        for path in files:
            if not self.runner.exists(path):
                continue
            try:
                self.remove_file(path)
                removed.append(path.name)
            except OSError as exc:
                return False, f"could not remove {path}: {exc}"
        for path in trees:
            if not self.runner.exists(path):
                continue
            try:
                self.remove_tree(path)
                removed.append(str(path))
            except OSError as exc:
                return False, f"could not remove {path}: {exc}"
        if removed:
            return True, "removed " + ", ".join(removed)
        return True, "nothing to remove"

    def _do_step(self, step_id: str) -> tuple[bool, str]:
        if step_id == "shortcuts":
            return self._remove_paths(self._shortcut_files(), [])
        if step_id == "exports":
            return self._remove_paths(self._export_files(), [])
        if step_id == "container":
            rc, out = self.runner.run(["distrobox", "rm", "--force", self.container])
            if rc != 0:
                return False, _last_meaningful_line(out) or f"exit {rc}"
            return True, f"removed container '{self.container}'"
        if step_id == "appimage":
            return self._remove_paths(self._appimage_targets(), [])
        return self._remove_paths([], self._tree_targets(step_id))

    def _dry_run_detail(self, step_id: str) -> str:
        if step_id == "shortcuts":
            targets = self._shortcut_files()
        elif step_id == "exports":
            targets = self._export_files()
        elif step_id == "container":
            return f"distrobox rm --force {self.container}"
        elif step_id == "appimage":
            targets = list(self._appimage_targets())
        else:
            targets = self._tree_targets(step_id)
        present = [str(p) for p in targets if self.runner.exists(p)]
        return "would remove: " + "; ".join(present)

    # --- Orchestration (same shape as HostSetup.run) --------------------------

    def run(
        self,
        progress: Callable[[StepResult], None] | None = None,
        dry_run: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[StepResult]:
        """Run the uninstall. One StepResult per step; stops on failure."""
        results: list[StepResult] = []

        def record(result: StepResult) -> None:
            results.append(result)
            if progress is not None:
                progress(result)

        stop = False
        for step_id in self.STEP_IDS:
            title = self._TITLES[step_id]
            if stop:
                record(StepResult(step_id, title, StepStatus.CANCELLED))
                continue
            if cancelled is not None and cancelled():
                record(StepResult(step_id, title, StepStatus.CANCELLED))
                stop = True
                continue
            if self._is_done(step_id):
                record(StepResult(step_id, title, StepStatus.DONE, "already removed"))
                continue
            if dry_run:
                record(
                    StepResult(
                        step_id,
                        title,
                        StepStatus.WOULD_RUN,
                        self._dry_run_detail(step_id),
                    )
                )
                continue
            if progress is not None:
                progress(StepResult(step_id, title, StepStatus.RUNNING, "removing…"))
            ok, detail = self._do_step(step_id)
            if ok:
                record(StepResult(step_id, title, StepStatus.RAN, detail))
            else:
                record(StepResult(step_id, title, StepStatus.FAILED, detail))
                stop = True
        return results
