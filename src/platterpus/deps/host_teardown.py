"""Host-stack teardown — the in-app Uninstaller's engine (reverse of setup).

The user's requirement (2026-06-08): remove everything *this app* put on the
machine — menu/desktop shortcuts, host-exported binaries, the `ripping`
container (with cyanrip inside it), optionally the legacy `whipper.conf` and the
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

Steps are **independent and best-effort**: a failed step (e.g. a busy container)
does NOT stop the rest — the engine removes everything else it can and reports
what failed, so one failure never leaves a half-removed system. (Setup is the
opposite — it stops on failure because its later steps depend on earlier ones.)
The GUI's own config/logs go LAST and are *kept* if any earlier step failed, so
the log survives to debug with; a fully clean run removes them too.

Not handled here (script-only concerns): the dev `.venv/` and the cloned
repo — `uninstall.sh` covers those; a packaged app doesn't know a repo root.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from platterpus import appimage_integration
from platterpus.deps.host_setup import (
    DEFAULT_CONTAINER,
    _last_meaningful_line,
)
from platterpus.deps.step_engine import (
    CommandRunner,
    StepResult,
    StepStatus,
)
from platterpus.paths import (
    APP_NAME,
    CONFIG_DIR,
    CYANRIP_BINARY_DEFAULT,
    FLAC_BINARY_DEFAULT,
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
        # Main app entry/icon are named by the freedesktop app-id; the
        # uninstall helper + script + bin use the plain APP_NAME slug.
        app_id = appimage_integration.DESKTOP_ID  # io.github.rmccann_hub.Platterpus
        slug = APP_NAME  # "platterpus"
        return [
            self.desktop_dir / f"{app_id}.desktop",
            self.desktop_dir / f"{slug}-uninstall.desktop",
            self.desktop_folder / f"{app_id}.desktop",
            self.icon_dir / f"{app_id}.png",
            self.apps_dir / f"{slug}-uninstall.sh",
            self.bin_dir / slug,
        ]

    def _export_files(self) -> list[Path]:
        """The host-exported wrappers distrobox-export wrote.

        Must mirror the setup export step exactly (host_setup exports cyanrip,
        metaflac AND flac): a missing entry here leaves a wrapper behind after
        uninstall. `flac` was omitted, so `~/.local/bin/flac` was orphaned (#34).
        `whipper` stays for the legacy path (a pre-KDD-18 install may still have
        it exported)."""
        return [
            self.bin_dir / WHIPPER_BINARY_DEFAULT.name,
            self.bin_dir / "metaflac",
            self.bin_dir / CYANRIP_BINARY_DEFAULT.name,
            self.bin_dir / FLAC_BINARY_DEFAULT.name,
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
            "exports": "cyanrip/metaflac (+ any legacy whipper) in ~/.local/bin",
            "container": f"'{DEFAULT_CONTAINER}' container (ripping tools inside it)",
            "whipper_config": "legacy whipper.conf (drive calibration)",
            "appimage": "The AppImage file itself",
            "app_data": "Platterpus settings + logs",
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

        stop = False  # set ONLY by an explicit cancel — never by a failure
        any_failed = False  # a removal failed → keep the log to debug with
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
            # The GUI's own settings + logs (app_data) go LAST. If any earlier
            # removal FAILED, keep them — the log survives to debug the failure,
            # and the user can re-run uninstall (idempotent) once it's resolved.
            # A fully clean run still removes them.
            if step_id == "app_data" and any_failed:
                record(
                    StepResult(
                        step_id,
                        title,
                        StepStatus.DONE,
                        "kept settings + logs so the failure(s) above can be "
                        "debugged — re-run uninstall to remove them once fixed",
                    )
                )
                continue
            if progress is not None:
                progress(StepResult(step_id, title, StepStatus.RUNNING, "removing…"))
            ok, detail = self._do_step(step_id)
            if ok:
                record(StepResult(step_id, title, StepStatus.RAN, detail))
            else:
                # Teardown steps are INDEPENDENT — removing the AppImage doesn't
                # depend on removing the container. So a failed step must NOT
                # stop the rest (unlike setup, where later steps depend on
                # earlier ones): keep removing everything else we can, and report
                # what failed. Stopping here is exactly what left a half-removed
                # system — real-user report 2026-06-26: "uninstall didn't do all".
                record(StepResult(step_id, title, StepStatus.FAILED, detail))
                any_failed = True
        return results
