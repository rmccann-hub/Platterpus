"""Tests for the uninstall engine (deps/host_teardown.py): scan, plan, remove, re-scan.

Driven through a fake runner and a fake home under ``tmp_path``, so no real file,
container or Flatpak is ever touched. The contract (TASKS R190): everything
Platterpus created goes by default; the choices keep groups; the image goes only
when no other container uses it; one failure never stops the rest; the logs are
kept when anything failed; and the report names what is STILL present after a
re-scan, not what was asked.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from platterpus.deps import system_packages_marker
from platterpus.deps.host_setup import DEFAULT_IMAGE
from platterpus.deps.host_teardown import (
    HostTeardown,
    container_names,
    package_remove_argv,
)
from platterpus.deps.install_footprint import PICARD_APP_ID, Group
from platterpus.deps.step_engine import StepStatus
from platterpus.deps.uninstall_plan import Choices, build_plan
from platterpus.deps.user_locations import Locations

Answer = tuple[int, str] | Callable[[list[str]], tuple[int, str]]


class _FakeRunner:
    """Programs on PATH, and canned answers keyed by argv (or by its first words)."""

    def __init__(self, present: set[str] | None = None) -> None:
        self.present: set[str] = present or set()
        self.calls: list[list[str]] = []
        self.answers: dict[tuple[str, ...], Answer] = {}

    def which(self, name: str) -> bool:
        return name in self.present

    def run(self, argv: list[str], timeout: float = 60.0) -> tuple[int, str]:
        self.calls.append(argv)
        for length in range(len(argv), 0, -1):
            answer = self.answers.get(tuple(argv[:length]))
            if answer is not None:
                return answer(argv) if callable(answer) else answer
        return 0, ""


def _locations(tmp_path: Path) -> Locations:
    home = tmp_path / "home"
    return Locations(
        home=home,
        config_home=home / ".config",
        data_home=home / ".local" / "share",
        desktop_folder=home / "Desktop",
    )


def _engine(tmp_path: Path, runner: _FakeRunner, **kwargs: object) -> HostTeardown:
    loc = _locations(tmp_path)
    defaults: dict[str, object] = {
        "runner": runner,
        "locations": loc,
        "install_note": loc.data_home
        / "platterpus"
        / system_packages_marker.MARKER_NAME,
        "refresh_menu": lambda: None,
    }
    defaults.update(kwargs)
    return HostTeardown(**defaults)  # type: ignore[arg-type]  # test kwargs


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _populate(tmp_path: Path) -> Path:
    """A home holding one of nearly everything Platterpus creates."""
    home = _locations(tmp_path).home
    _touch(home / ".local/bin/cyanrip", "#!/bin/sh\n# distrobox_binary\n")
    _touch(home / ".local/bin/flac", "#!/bin/sh\nexec /usr/bin/distrobox-enter\n")
    _touch(home / ".local/share/applications/io.github.rmccann_hub.Platterpus.desktop")
    _touch(home / ".local/share/applications/platterpus-uninstall.desktop")
    _touch(home / ".local/share/icons/io.github.rmccann_hub.Platterpus.png")
    _touch(home / "Desktop/io.github.rmccann_hub.Platterpus.desktop")
    _touch(home / "Applications/platterpus-x86_64.AppImage")
    _touch(home / "Applications/platterpus-0.7.100.AppImage")
    _touch(home / "Applications/.platterpus-update.part")
    _touch(home / "Applications/platterpus-uninstall.sh")
    _touch(home / ".cache/platterpus/cyanrip-fork/meson.build")
    _touch(home / "platterpus-rig/rigsession1/log.txt")
    _touch(home / ".config/platterpus/config.toml")
    _touch(home / ".local/share/platterpus/log.txt")
    return home


def _with_container(runner: _FakeRunner, *, image_users: str = "ripping\n") -> None:
    runner.present |= {"distrobox", "podman"}
    runner.answers[("distrobox", "list")] = (
        0,
        "ID           | NAME     | STATUS | IMAGE\n"
        f"abc123       | ripping  | Up     | {DEFAULT_IMAGE}\n",
    )
    runner.answers[("podman", "image", "inspect")] = (0, "[{}]")
    runner.answers[("podman", "ps")] = (0, image_users)


# --- The default removes everything -------------------------------------------


def test_default_uninstall_removes_everything_and_the_rescan_finds_nothing(
    tmp_path: Path,
) -> None:
    home = _populate(tmp_path)
    runner = _FakeRunner()
    _with_container(runner)

    # After `distrobox rm`, the listing no longer names the container, and the
    # image is gone after `podman rmi`: the re-scan must see the world change.
    def removed(argv: list[str]) -> tuple[int, str]:
        runner.answers[("distrobox", "list")] = (0, "ID | NAME | STATUS\n")
        runner.answers[("podman", "ps")] = (0, "")
        return 0, ""

    def image_gone(argv: list[str]) -> tuple[int, str]:
        runner.answers[("podman", "image", "inspect")] = (125, "Error: image not known")
        return 0, ""

    runner.answers[("distrobox", "rm")] = removed
    runner.answers[("podman", "rmi")] = image_gone

    report = _engine(tmp_path, runner).run(Choices())

    assert report.complete, (report.failed, report.leftovers)
    assert ["distrobox", "rm", "--force", "ripping"] in runner.calls
    assert ["podman", "rmi", DEFAULT_IMAGE] in runner.calls
    left = sorted(
        str(p.relative_to(home)) for p in (tmp_path / "home").rglob("*") if p.is_file()
    )
    assert left == [], left


def test_choices_keep_settings_logs_and_picard(tmp_path: Path) -> None:
    home = _populate(tmp_path)
    runner = _FakeRunner({"flatpak"})
    runner.answers[("flatpak", "list", "--user", "--app", "--columns=application")] = (
        0,
        f"{PICARD_APP_ID}\n",
    )
    report = _engine(tmp_path, runner).run(
        Choices(keep_settings=True, keep_logs=True, keep_picard=True)
    )

    assert (home / ".config/platterpus/config.toml").exists()
    assert (home / ".local/share/platterpus/log.txt").exists()
    assert (home / "platterpus-rig/rigsession1/log.txt").exists()  # a test run: (b)
    assert not any(c[:2] == ["flatpak", "uninstall"] for c in runner.calls)
    kept = {obs.item.group for obs, _why in report.plan.kept}
    assert {Group.SETTINGS, Group.LOGS, Group.PICARD} <= kept
    assert not (home / ".cache/platterpus").exists()


# --- Exact container name, and the image only when nobody else uses it ---------


def test_container_name_is_matched_exactly() -> None:
    listing = (
        "ID | NAME | STATUS | IMAGE\n"
        "1 | ripping-old | Up | x\n"
        "2 | my-ripping | Up | x\n"
        "3 | \x1b[32mripping\x1b[0m | Up | x\n"
    )
    assert container_names(listing) == ["ripping-old", "my-ripping", "ripping"]
    assert "ripping" not in container_names("ID | NAME\n1 | ripping-old\n")


def test_a_container_merely_containing_the_word_is_not_ours(tmp_path: Path) -> None:
    runner = _FakeRunner({"distrobox"})
    runner.answers[("distrobox", "list")] = (
        0,
        "ID | NAME | STATUS\n1 | ripping2 | Up\n",
    )
    obs = {o.item.item_id: o for o in _engine(tmp_path, runner).scan()}
    assert obs["container"].present == ()


def test_image_is_kept_when_another_container_uses_it(tmp_path: Path) -> None:
    runner = _FakeRunner()
    _with_container(runner, image_users="ripping\nmy-dev-box\n")
    engine = _engine(tmp_path, runner)

    plan = build_plan(engine.scan(), Choices())
    kept = {obs.item.item_id: why for obs, why in plan.kept}
    assert "my-dev-box" in kept["image"]

    engine.run(Choices())
    assert not any(c[:2] == ["podman", "rmi"] for c in runner.calls)


def test_image_users_are_checked_again_where_the_removal_happens(
    tmp_path: Path,
) -> None:
    """A container created after the scan holds the image: re-checked, not assumed."""
    runner = _FakeRunner()
    _with_container(runner)
    engine = _engine(tmp_path, runner)
    plan = build_plan(engine.scan(), Choices())
    runner.answers[("podman", "ps")] = (0, "made-since\n")

    results, _ = engine.remove(plan)

    image = next(r for r in results if r.step_id == "image")
    assert image.status is StepStatus.RAN and "made-since" in image.detail
    assert not any(c[:2] == ["podman", "rmi"] for c in runner.calls)


def test_a_listing_that_fails_is_unchecked_not_absent(tmp_path: Path) -> None:
    runner = _FakeRunner({"distrobox", "flatpak"})
    runner.answers[("distrobox", "list")] = (1, "Error: cannot connect to podman")
    runner.answers[("flatpak",)] = (1, "error: simulated")
    obs = {o.item.item_id: o for o in _engine(tmp_path, runner).scan()}
    assert "cannot connect to podman" in obs["container"].unchecked
    assert "simulated" in obs["picard"].unchecked
    plan = build_plan(tuple(obs.values()), Choices())
    assert {o.item.item_id for o in plan.unchecked} >= {"container", "picard"}
    assert "container" not in {o.item.item_id for o in plan.remove}


# --- Only what is ours ----------------------------------------------------------


def test_a_bin_file_distrobox_did_not_write_is_left_alone(tmp_path: Path) -> None:
    home = _locations(tmp_path).home
    mine = _touch(home / ".local/bin/flac", "#!/bin/sh\necho the user's own flac\n")
    report = _engine(tmp_path, _FakeRunner()).run(Choices())
    assert mine.exists()
    assert any(o.item.item_id == "export:flac" for o, _ in report.plan.kept)


def test_the_cli_link_goes_only_when_it_points_into_a_venv(tmp_path: Path) -> None:
    home = _locations(tmp_path).home
    (home / ".local/bin").mkdir(parents=True)
    link = home / ".local/bin/platterpus"
    link.symlink_to(tmp_path / "pipx/venvs/platterpus/bin/platterpus")
    _engine(tmp_path, _FakeRunner()).run(Choices())
    assert link.is_symlink(), "a pipx link is not dev-setup.sh's"

    link.unlink()
    link.symlink_to(tmp_path / "repo/.venv/bin/platterpus")
    _engine(tmp_path, _FakeRunner()).run(Choices())
    assert not link.is_symlink()


def test_rips_go_only_when_asked_and_only_the_given_folder(tmp_path: Path) -> None:
    rips = _touch(tmp_path / "library" / "Album" / "01.txt").parent.parent
    engine = _engine(tmp_path, _FakeRunner(), rips=rips)
    engine.run(Choices())
    assert rips.exists(), "rips removed without being asked"
    engine.run(Choices(remove_rips=True))
    assert not rips.exists()


# --- Independence, the logs, and the re-scan -------------------------------------


def test_one_failure_does_not_stop_the_rest_and_the_logs_are_kept(
    tmp_path: Path,
) -> None:
    home = _populate(tmp_path)
    runner = _FakeRunner()
    _with_container(runner)
    runner.answers[("distrobox", "rm")] = (1, "Error: container is in use")

    report = _engine(tmp_path, runner).run(Choices())

    assert [r.step_id for r in report.failed] == ["container"]
    assert "container is in use" in report.failed[0].detail
    assert not (home / ".config/platterpus").exists(), "later steps still ran"
    assert (home / ".local/share/platterpus/log.txt").exists(), "log kept to debug"
    logs = next(r for r in report.results if r.step_id == "logs")
    assert logs.status is StepStatus.DONE and "kept" in logs.detail
    assert not report.complete


def test_the_rescan_reports_what_is_still_present(tmp_path: Path) -> None:
    """A remover that 'succeeds' but leaves the file is caught by looking again."""
    home = _populate(tmp_path)
    stubborn = home / ".local/share/icons/io.github.rmccann_hub.Platterpus.png"
    real_unlink: Callable[[Path], None] = lambda p: p.unlink()  # noqa: E731

    def remover(path: Path) -> None:
        if path != stubborn:
            real_unlink(path)

    report = _engine(tmp_path, _FakeRunner(), remove_file=remover).run(Choices())

    assert stubborn.exists()
    assert any(str(stubborn) in line for line in report.leftovers), report.leftovers
    assert not report.complete


def test_cancel_stops_before_the_next_item_and_says_so(tmp_path: Path) -> None:
    _populate(tmp_path)
    seen: list[str] = []
    report = _engine(tmp_path, _FakeRunner()).run(
        Choices(), progress=lambda r: seen.append(r.step_id), cancelled=lambda: True
    )
    assert report.cancelled and not report.complete
    assert all(r.status is StepStatus.CANCELLED for r in report.results)


def test_the_menu_cache_is_refreshed_even_after_a_failure(tmp_path: Path) -> None:
    refreshed: list[bool] = []
    runner = _FakeRunner()
    _with_container(runner)
    runner.answers[("distrobox", "rm")] = (1, "busy")
    _engine(tmp_path, runner, refresh_menu=lambda: refreshed.append(True)).run(
        Choices()
    )
    assert refreshed == [True]


# --- Picard, its runtime and the flathub remote ---------------------------------


class _Flatpak:
    """A stateful stand-in for user-level Flatpak: uninstalling really removes.

    A static fake kept listing Picard after `flatpak uninstall`, which the real
    tool does not do, so the remote looked used forever.
    """

    RUNTIME = "org.kde.Platform/x86_64/6.8"

    def __init__(
        self, runner: _FakeRunner, other_app: str = "", other_ref: str = ""
    ) -> None:
        # ref -> (application id or "" for a runtime, the runtime it uses, origin)
        self.refs: dict[str, tuple[str, str, str]] = {
            f"{PICARD_APP_ID}/x86_64/stable": (PICARD_APP_ID, self.RUNTIME, "flathub"),
            self.RUNTIME: ("", "", "flathub"),
            "org.kde.Platform.Locale/x86_64/6.8": ("", "", "flathub"),
        }
        if other_app:
            self.refs[f"{other_app}/x86_64/stable"] = (
                other_app,
                self.RUNTIME,
                "flathub",
            )
        if other_ref and other_ref not in self.refs:
            self.refs[other_ref] = ("", "", "flathub")
        self.remotes: set[str] = {"flathub"}
        runner.present.add("flatpak")
        runner.answers[("flatpak",)] = self.answer

    def answer(self, argv: list[str]) -> tuple[int, str]:
        args = argv[1:]
        apps = [(a, rt) for a, rt, _ in self.refs.values() if a]
        if args[:2] == ["list", "--user"] and "--columns=application" in args:
            return 0, "".join(f"{a}\n" for a, _ in apps)
        if args[:2] == ["list", "--user"] and "--columns=application,runtime" in args:
            return 0, "".join(f"{a}\t{rt}\n" for a, rt in apps)
        if args[:3] == ["list", "--user", "--runtime"]:
            return 0, "".join(f"{r}\n" for r, (a, _, _) in self.refs.items() if not a)
        if args[:2] == ["list", "--user"] and "--columns=ref,origin" in args:
            return 0, "".join(f"{r}\t{o}\n" for r, (_, _, o) in self.refs.items())
        if args[:1] == ["info"]:
            found = [rt for a, rt in apps if a == args[-1]]
            return (0, f"{found[0]}\n") if found else (1, "error: not installed")
        if args[:1] == ["remotes"]:
            return 0, "".join(f"{r}\n" for r in sorted(self.remotes))
        if args[:1] == ["remote-delete"]:
            self.remotes.discard(args[-1])
            return 0, ""
        if args[:1] == ["uninstall"]:
            target = args[-1]
            for ref, (app, _, _) in list(self.refs.items()):
                rid = ref.split("/", 1)[0]
                base = target.split("/", 1)[0]
                if app == target or ref == target or rid.startswith(f"{base}."):
                    del self.refs[ref]
            return 0, ""
        return 1, f"unexpected flatpak call {argv}"


def _picard_runner(
    other_app_on_runtime: str = "", other_flathub_ref: str = ""
) -> _FakeRunner:
    runner = _FakeRunner()
    _Flatpak(runner, other_app_on_runtime, other_flathub_ref)
    return runner


def test_picard_its_runtime_and_the_remote_go_when_nothing_else_uses_them(
    tmp_path: Path,
) -> None:
    runner = _picard_runner()
    report = _engine(tmp_path, runner).run(Choices())
    assert report.complete, (report.failed, report.leftovers)
    assert ["flatpak", "uninstall", "--user", "-y", "--delete-data", PICARD_APP_ID] in (
        runner.calls
    )
    assert ["flatpak", "uninstall", "--user", "-y", "org.kde.Platform/x86_64/6.8"] in (
        runner.calls
    )
    assert ["flatpak", "remote-delete", "--user", "flathub"] in runner.calls


def test_a_shared_runtime_and_a_used_remote_are_kept(tmp_path: Path) -> None:
    runner = _picard_runner("org.kde.kate", "org.kde.kate/x86_64/stable")
    plan = build_plan(_engine(tmp_path, runner).scan(), Choices())
    kept = {obs.item.item_id: why for obs, why in plan.kept}
    assert "org.kde.kate" in kept["picard:runtime"]
    assert "org.kde.kate" in kept["picard:remote"]


# --- System packages: only the ones the note names, only when asked ---------------


def test_system_packages_need_the_note_and_the_box(tmp_path: Path) -> None:
    loc = _locations(tmp_path)
    note = loc.data_home / "platterpus" / system_packages_marker.MARKER_NAME
    os_release = _touch(tmp_path / "os-release", 'ID="fedora"\n')
    runner = _FakeRunner({"distrobox", "podman"})
    runner.answers[("distrobox", "list")] = (0, "ID | NAME\n")
    runner.answers[("podman", "image")] = (125, "image not known")

    engine = _engine(tmp_path, runner, os_release=os_release, install_note=note)
    assert not any(o.item.group is Group.SYSTEM_PACKAGES for o in engine.scan())

    system_packages_marker.record_installed("podman", note)
    engine.run(Choices(keep_logs=True))
    assert not any("remove" in c for c in runner.calls), "removed without the box"

    engine.run(Choices(keep_logs=True, remove_system_packages=True))
    assert ["pkexec", "dnf", "remove", "-y", "podman"] in runner.calls
    assert system_packages_marker.read_installed(note) == ()


@pytest.mark.parametrize(
    ("os_id", "expected"),
    [
        ("fedora", ["sudo", "dnf", "remove", "-y", "podman"]),
        ("ubuntu", ["sudo", "apt-get", "remove", "-y", "podman"]),
        ("arch", ["sudo", "pacman", "-R", "--noconfirm", "podman"]),
        (
            "opensuse-tumbleweed",
            ["sudo", "zypper", "--non-interactive", "remove", "podman"],
        ),
        ("plan9", []),
    ],
)
def test_package_remove_argv_mirrors_install(
    tmp_path: Path, os_id: str, expected: list[str]
) -> None:
    os_release = _touch(tmp_path / "os-release", f"ID={os_id}\n")
    assert package_remove_argv("podman", os_release, "sudo") == expected
