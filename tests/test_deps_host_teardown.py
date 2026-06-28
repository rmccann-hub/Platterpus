"""Tests for the in-app Uninstaller engine (deps/host_teardown.py).

Driven through a fake CommandRunner + injected removers and tmp dirs, so no
real file or container is ever touched. Verifies the user's contract: remove
everything the app installed; never touch Distrobox/podman or music.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.deps.host_teardown import HostTeardown
from platterpus.deps.step_engine import StepStatus


class _FakeRunner:
    def __init__(self) -> None:
        self.present: set[str] = set()
        self.calls: list[list[str]] = []
        self.results: dict[tuple[str, ...], tuple[int, str]] = {}
        self.default: tuple[int, str] = (0, "")

    def which(self, name: str) -> bool:
        return name in self.present

    def exists(self, path: Path) -> bool:
        return Path(path).exists()  # real tmp files in these tests

    def run(self, argv: list[str]) -> tuple[int, str]:
        self.calls.append(argv)
        return self.results.get(tuple(argv), self.default)


def _teardown(tmp_path: Path, runner: _FakeRunner, **kwargs) -> HostTeardown:
    """A HostTeardown rooted entirely in tmp_path."""
    defaults = dict(
        runner=runner,
        gui_config_dir=tmp_path / "config" / "platterpus",
        gui_data_dir=tmp_path / "share" / "platterpus",
        whipper_config_dir=tmp_path / "config" / "whipper",
        bin_dir=tmp_path / "bin",
        desktop_dir=tmp_path / "applications",
        icon_dir=tmp_path / "icons",
        desktop_folder=tmp_path / "Desktop",
        apps_dir=tmp_path / "Applications",
    )
    defaults.update(kwargs)
    return HostTeardown(**defaults)


def _populate_everything(tmp_path: Path) -> None:
    """Create every artifact the engine targets."""
    files = [
        tmp_path / "applications" / "io.github.rmccann_hub.Platterpus.desktop",
        tmp_path / "applications" / "platterpus-uninstall.desktop",
        tmp_path / "Desktop" / "io.github.rmccann_hub.Platterpus.desktop",
        tmp_path / "icons" / "io.github.rmccann_hub.Platterpus.png",
        tmp_path / "Applications" / "platterpus-uninstall.sh",
        tmp_path / "bin" / "platterpus",
        tmp_path / "bin" / "whipper",
        tmp_path / "bin" / "metaflac",
        tmp_path / "bin" / "cyanrip",
        tmp_path / "config" / "whipper" / "whipper.conf",
        tmp_path / "config" / "platterpus" / "config.toml",
        tmp_path / "share" / "platterpus" / "log.txt",
    ]
    for f in files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x", encoding="utf-8")


def _ids(results: list) -> dict[str, str]:
    return {r.step_id: r.status.value for r in results}


# --- Easy: full install → everything removed -------------------------------


def test_full_uninstall_removes_everything(tmp_path: Path) -> None:
    _populate_everything(tmp_path)
    runner = _FakeRunner()
    runner.present = {"distrobox"}
    runner.results[("distrobox", "list")] = (0, "ID | ripping | Up\n")

    td = _teardown(tmp_path, runner)
    results = td.run()

    assert all(r.ok for r in results)
    # Every file artifact is gone…
    assert not (
        tmp_path / "applications" / "io.github.rmccann_hub.Platterpus.desktop"
    ).exists()
    assert not (tmp_path / "bin" / "whipper").exists()
    assert not (tmp_path / "bin" / "cyanrip").exists()
    assert not (tmp_path / "config" / "whipper").exists()
    assert not (tmp_path / "config" / "platterpus").exists()
    assert not (tmp_path / "share" / "platterpus").exists()
    # …and the container was removed by force.
    assert ["distrobox", "rm", "--force", "ripping"] in runner.calls


def test_app_data_is_the_last_step(tmp_path: Path) -> None:
    """Settings + logs go last so a failed earlier step leaves the log
    available for debugging."""
    td = _teardown(tmp_path, _FakeRunner())
    assert td.STEP_IDS[-1] == "app_data"


# --- Idempotent: clean system → all DONE ------------------------------------


def test_clean_system_is_all_done(tmp_path: Path) -> None:
    runner = _FakeRunner()  # no distrobox → container counts as absent
    results = _teardown(tmp_path, runner).run()
    assert all(r.status is StepStatus.DONE for r in results)
    assert _teardown(tmp_path, runner).is_complete() is True
    # Nothing was executed — the only runner use would be `distrobox list`.
    assert all(c[:2] != ["distrobox", "rm"] for c in runner.calls)


# --- Options: the checkboxes control the plan --------------------------------


def test_optional_steps_can_be_kept(tmp_path: Path) -> None:
    _populate_everything(tmp_path)
    runner = _FakeRunner()
    runner.present = {"distrobox"}
    runner.results[("distrobox", "list")] = (0, "ripping\n")

    td = _teardown(
        tmp_path, runner, remove_container=False, remove_whipper_config=False
    )
    assert "container" not in td.STEP_IDS
    assert "whipper_config" not in td.STEP_IDS
    td.run()

    # Kept: the container and whipper.conf. Removed: the rest.
    assert all(c[:2] != ["distrobox", "rm"] for c in runner.calls)
    assert (tmp_path / "config" / "whipper" / "whipper.conf").exists()
    assert not (tmp_path / "bin" / "whipper").exists()


def test_appimage_step_only_when_running_as_appimage(tmp_path: Path) -> None:
    runner = _FakeRunner()
    assert "appimage" not in _teardown(tmp_path, runner).STEP_IDS

    appimage = tmp_path / "platterpus-x86_64.AppImage"
    appimage.write_text("ELF", encoding="utf-8")
    td = _teardown(tmp_path, runner, appimage=appimage)
    assert "appimage" in td.STEP_IDS
    td.run()
    assert not appimage.exists()


# --- The keep-contract: distrobox/podman are never targets -------------------


def test_never_removes_distrobox_or_podman(tmp_path: Path) -> None:
    _populate_everything(tmp_path)
    runner = _FakeRunner()
    runner.present = {"distrobox", "podman"}
    runner.results[("distrobox", "list")] = (0, "ripping\n")

    _teardown(tmp_path, runner).run()

    # The ONLY mutating command ever issued is the container removal.
    mutating = [c for c in runner.calls if c != ["distrobox", "list"]]
    assert mutating == [["distrobox", "rm", "--force", "ripping"]]


# --- Failure: best-effort (continue past it) + report ------------------------


def test_container_failure_does_not_skip_other_removals(tmp_path: Path) -> None:
    """A failed step (e.g. a busy container) must NOT cancel the rest —
    teardown steps are independent, so everything else is still removed; only
    the GUI's own settings/logs are kept so the failure can be debugged. This
    was the 'uninstall didn't do all' bug (one failure skipped everything after
    it)."""
    _populate_everything(tmp_path)
    runner = _FakeRunner()
    runner.present = {"distrobox"}
    runner.results[("distrobox", "list")] = (0, "ripping\n")
    runner.results[("distrobox", "rm", "--force", "ripping")] = (
        1,
        "Error: container is in use",
    )

    results = _teardown(tmp_path, runner).run()

    status = _ids(results)
    assert status["container"] == "failed"
    # The step AFTER the failure still ran (the fix) — whipper.conf is gone.
    assert status["whipper_config"] == "ran"
    assert not (tmp_path / "config" / "whipper").exists()
    # Settings/logs are deliberately KEPT (not cancelled) so the log survives.
    assert status["app_data"] == "done"
    assert (tmp_path / "share" / "platterpus" / "log.txt").exists()
    # Best-effort: nothing was CANCELLED — every step was attempted.
    assert StepStatus.CANCELLED not in {r.status for r in results}
    failed = next(r for r in results if r.status is StepStatus.FAILED)
    assert "in use" in failed.detail


def test_unremovable_file_reports_failure(tmp_path: Path) -> None:
    _populate_everything(tmp_path)

    def explode(path: Path) -> None:
        raise OSError("permission denied")

    td = _teardown(tmp_path, _FakeRunner(), remove_file=explode)
    results = td.run()
    failed = next(r for r in results if r.status is StepStatus.FAILED)
    assert "permission denied" in failed.detail


# --- Dry run -----------------------------------------------------------------


def test_dry_run_removes_nothing_and_reports_targets(tmp_path: Path) -> None:
    _populate_everything(tmp_path)
    runner = _FakeRunner()
    runner.present = {"distrobox"}
    runner.results[("distrobox", "list")] = (0, "ripping\n")

    results = _teardown(tmp_path, runner).run(dry_run=True)

    assert all(r.status is StepStatus.WOULD_RUN for r in results)
    assert (tmp_path / "bin" / "whipper").exists()  # nothing touched
    assert all(c[:2] != ["distrobox", "rm"] for c in runner.calls)
    shortcuts = next(r for r in results if r.step_id == "shortcuts")
    assert "io.github.rmccann_hub.Platterpus.desktop" in shortcuts.detail


# --- Cancel ------------------------------------------------------------------


def test_cancel_before_first_step(tmp_path: Path) -> None:
    _populate_everything(tmp_path)
    results = _teardown(tmp_path, _FakeRunner()).run(cancelled=lambda: True)
    assert all(r.status is StepStatus.CANCELLED for r in results)
    assert (tmp_path / "bin" / "whipper").exists()


def test_canonical_applications_copy_removed_without_appimage_env(
    tmp_path: Path,
) -> None:
    """Integration moves the AppImage to ~/Applications; the uninstaller must
    find and remove that copy even when not launched from it ($APPIMAGE
    unset — e.g. a source run, or launched from a second stray copy)."""
    canonical = tmp_path / "Applications" / "platterpus-x86_64.AppImage"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"ELF")
    runner = _FakeRunner()

    td = _teardown(tmp_path, runner)  # note: appimage=None
    assert "appimage" in td.STEP_IDS
    td.run()

    assert not canonical.exists()


# --- Tree-removal edge cases, progress, and container-probe failure ----------


def test_app_data_tree_failure_is_reported_and_skips_absent_tree(
    tmp_path: Path,
) -> None:
    # Only the GUI config tree exists (the data/log tree is already gone). The
    # app_data step removes the present tree and skips the absent one; if the
    # removal raises, the step fails with a presentable message.
    (tmp_path / "config" / "platterpus").mkdir(parents=True)
    (tmp_path / "config" / "platterpus" / "config.toml").write_text("x")

    def explode(path: Path) -> None:
        raise OSError("directory not empty")

    results = _teardown(tmp_path, _FakeRunner(), remove_tree=explode).run()

    app_data = next(r for r in results if r.step_id == "app_data")
    assert app_data.status is StepStatus.FAILED
    assert "could not remove" in app_data.detail


def test_run_reports_running_progress_per_step(tmp_path: Path) -> None:
    _populate_everything(tmp_path)
    runner = _FakeRunner()
    runner.present = {"distrobox"}
    runner.results[("distrobox", "list")] = (0, "ripping\n")

    seen: list[tuple[str, StepStatus]] = []
    _teardown(tmp_path, runner).run(
        progress=lambda r: seen.append((r.step_id, r.status))
    )

    # Each actioned step emits a transient RUNNING before its terminal result.
    assert ("shortcuts", StepStatus.RUNNING) in seen


def test_container_probe_treats_list_failure_as_absent(tmp_path: Path) -> None:
    # `distrobox list` failing (non-zero) must not crash or wrongly try to
    # remove a container — it's treated as "no such container" (already done).
    runner = _FakeRunner()
    runner.present = {"distrobox"}
    runner.results[("distrobox", "list")] = (1, "cannot connect to podman")

    results = _teardown(tmp_path, runner).run()

    container = next(r for r in results if r.step_id == "container")
    assert container.status is StepStatus.DONE
    assert all(c[:2] != ["distrobox", "rm"] for c in runner.calls)
