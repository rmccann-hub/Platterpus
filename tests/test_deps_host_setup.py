"""Tests for the host-stack bootstrap (deps/host_setup.py).

Driven entirely through a fake CommandRunner, so no Distrobox/podman/sudo is
touched — the orchestration, idempotency, distro detection, dry-run, cancel,
and failure-stop behaviour are all verified offline. (The real command
execution is the hardware-gated part, validated on a target machine.)
"""

from __future__ import annotations

from pathlib import Path

from whipper_gui.deps.host_setup import (
    HostSetup,
    StepStatus,
    install_argv,
)


class _FakeRunner:
    def __init__(self) -> None:
        self.present: set[str] = set()
        self.paths: set[Path] = set()
        self.calls: list[list[str]] = []
        self.results: dict[tuple[str, ...], tuple[int, str]] = {}
        self.default: tuple[int, str] = (0, "")

    def which(self, name: str) -> bool:
        return name in self.present

    def exists(self, path: Path) -> bool:
        return path in self.paths

    def run(self, argv: list[str]) -> tuple[int, str]:
        self.calls.append(argv)
        return self.results.get(tuple(argv), self.default)


def _fedora(tmp_path: Path) -> Path:
    p = tmp_path / "os-release"
    p.write_text('ID=fedora\nID_LIKE="rhel fedora"\n', encoding="utf-8")
    return p


def _setup(tmp_path: Path, runner: _FakeRunner) -> HostSetup:
    return HostSetup(
        runner=runner,
        os_release=_fedora(tmp_path),
        whipper_path=tmp_path / "whipper",
    )


def _ids(results: list) -> list[tuple[str, str]]:
    return [(r.step_id, r.status.value) for r in results]


# --- Easy: nothing present → all five steps run --------------------------


def test_fresh_system_runs_all_steps(tmp_path: Path) -> None:
    runner = _FakeRunner()  # nothing present
    results = _setup(tmp_path, runner).run()

    assert [r.step_id for r in results] == [
        "distrobox",
        "backend",
        "container",
        "tools",
        "export",
    ]
    assert all(r.status is StepStatus.RAN for r in results)
    # The actual install/create/export commands were issued.
    flat = [" ".join(c) for c in runner.calls]
    assert any("dnf install -y distrobox" in c for c in flat)
    assert any("dnf install -y podman" in c for c in flat)
    assert any("distrobox create --yes --name ripping" in c for c in flat)
    assert any("sudo dnf install -y whipper flac python3-setuptools" in c for c in flat)
    assert any("distrobox-export --bin /usr/bin/whipper" in c for c in flat)


def test_host_root_installs_use_pkexec_not_sudo(tmp_path: Path) -> None:
    """A GUI has no TTY for sudo to prompt on, so host package installs must
    use pkexec (graphical polkit). In-container installs stay sudo (distrobox
    grants passwordless sudo)."""
    runner = _FakeRunner()  # nothing present
    _setup(tmp_path, runner).run()
    flat = [" ".join(c) for c in runner.calls]
    assert any(c.startswith("pkexec dnf install -y distrobox") for c in flat)
    assert any(c.startswith("pkexec dnf install -y podman") for c in flat)
    # The in-container tool install is still plain sudo (no host TTY needed).
    assert any("-- sudo dnf install -y whipper" in c for c in flat)
    assert not any(c.startswith("sudo ") for c in flat)


# --- Idempotent: everything present → nothing runs -----------------------


def test_fully_set_up_system_is_all_done(tmp_path: Path) -> None:
    runner = _FakeRunner()
    runner.present = {"distrobox", "podman"}
    runner.paths = {tmp_path / "whipper"}
    runner.results[("distrobox", "list")] = (0, "ID | ripping | Created\n")
    runner.results[
        ("distrobox", "enter", "ripping", "--", "command", "-v", "whipper")
    ] = (0, "/usr/bin/whipper")

    results = _setup(tmp_path, runner).run()

    assert all(r.status is StepStatus.DONE for r in results)
    # No mutating commands — only the read-only probes (list / command -v).
    flat = [" ".join(c) for c in runner.calls]
    assert not any("install" in c or "create" in c or "export" in c for c in flat)


# --- Hard: partial state — only the missing step runs --------------------


def test_only_export_runs_when_container_ready_but_not_exported(
    tmp_path: Path,
) -> None:
    runner = _FakeRunner()
    runner.present = {"distrobox", "podman"}
    # whipper NOT exported (paths empty).
    runner.results[("distrobox", "list")] = (0, "ripping\n")
    runner.results[
        ("distrobox", "enter", "ripping", "--", "command", "-v", "whipper")
    ] = (0, "/usr/bin/whipper")

    results = _setup(tmp_path, runner).run()

    status = dict(_ids(results))
    assert status["distrobox"] == "done"
    assert status["backend"] == "done"
    assert status["container"] == "done"
    assert status["tools"] == "done"
    assert status["export"] == "ran"
    flat = [" ".join(c) for c in runner.calls]
    assert any("distrobox-export --bin /usr/bin/whipper" in c for c in flat)
    assert any("distrobox-export --bin /usr/bin/metaflac" in c for c in flat)


# --- Edge / failure: a step fails → pipeline stops -----------------------


def test_failure_stops_pipeline(tmp_path: Path) -> None:
    runner = _FakeRunner()  # nothing present
    create = (
        "distrobox",
        "create",
        "--yes",
        "--name",
        "ripping",
        "--image",
        "registry.fedoraproject.org/fedora-toolbox:latest",
    )
    runner.results[create] = (1, "Error: cannot pull image")

    results = _setup(tmp_path, runner).run()
    status = dict(_ids(results))
    assert status["distrobox"] == "ran"
    assert status["backend"] == "ran"
    assert status["container"] == "failed"
    # Steps after the failure don't run.
    assert status["tools"] == "cancelled"
    assert status["export"] == "cancelled"
    # The failure detail surfaces the error line.
    failed = next(r for r in results if r.status is StepStatus.FAILED)
    assert "cannot pull image" in failed.detail


# --- Unexpected: unknown distro can't auto-install the backend -----------


def test_unknown_distro_backend_is_manual_failure(tmp_path: Path) -> None:
    osr = tmp_path / "os-release"
    osr.write_text("ID=tinycore\n", encoding="utf-8")
    runner = _FakeRunner()
    # distrobox has an upstream installer fallback, so it "runs"; podman
    # has no universal command → that step fails with a manual message.
    setup = HostSetup(runner=runner, os_release=osr, whipper_path=tmp_path / "whipper")
    results = setup.run()
    status = dict(_ids(results))
    assert status["distrobox"] == "ran"  # upstream installer fallback
    assert status["backend"] == "failed"
    backend = next(r for r in results if r.step_id == "backend")
    assert "manually" in backend.detail.lower()


# --- Dry run: nothing executes -------------------------------------------


def test_dry_run_reports_without_executing(tmp_path: Path) -> None:
    runner = _FakeRunner()  # nothing present
    results = _setup(tmp_path, runner).run(dry_run=True)

    assert all(r.status is StepStatus.WOULD_RUN for r in results)
    # No commands were actually run (the probes short-circuit when distrobox
    # isn't present, so the runner is never invoked).
    assert runner.calls == []
    # The detail shows what *would* run.
    distrobox = next(r for r in results if r.step_id == "distrobox")
    assert "dnf install -y distrobox" in distrobox.detail


# --- Cancellation --------------------------------------------------------


def test_cancel_before_first_step(tmp_path: Path) -> None:
    runner = _FakeRunner()
    results = _setup(tmp_path, runner).run(cancelled=lambda: True)
    assert all(r.status is StepStatus.CANCELLED for r in results)
    assert runner.calls == []


# --- is_ready + StepResult.ok --------------------------------------------


def test_is_ready_reflects_exported_whipper(tmp_path: Path) -> None:
    runner = _FakeRunner()
    setup = _setup(tmp_path, runner)
    assert setup.is_ready() is False
    runner.paths = {tmp_path / "whipper"}
    assert setup.is_ready() is True


# --- install_argv distro matrix ------------------------------------------


def test_install_argv_picks_package_manager(tmp_path: Path) -> None:
    def osr(content: str) -> Path:
        p = tmp_path / f"os-{abs(hash(content))}"
        p.write_text(content, encoding="utf-8")
        return p

    assert install_argv("distrobox", osr("ID=fedora\n"))[:3] == [
        "sudo",
        "dnf",
        "install",
    ]
    assert install_argv("podman", osr('ID=ubuntu\nID_LIKE="debian"\n'))[:2] == [
        "sudo",
        "apt-get",
    ]
    assert install_argv("distrobox", osr("ID=arch\n"))[:2] == ["sudo", "pacman"]
    assert install_argv("podman", osr("ID=opensuse-leap\nID_LIKE=suse\n"))[:2] == [
        "sudo",
        "zypper",
    ]
    # Unknown distro: distrobox falls back to the upstream installer; podman
    # has no universal command.
    unknown = osr("ID=plan9\n")
    assert install_argv("distrobox", unknown)[0] == "sh"
    assert install_argv("podman", unknown) == []
