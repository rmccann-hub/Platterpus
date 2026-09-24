"""Tests for :mod:`platterpus.container_scope`.

**Why this exists.** On 2026-09-23 a rip was killed because the Distrobox
container it ran in belonged to an earlier, already-closed Platterpus window's
systemd unit, and died with that unit. podman leaves the container's monitor in
the caller's unit while ``INVOCATION_ID`` is set, and every KDE-launched app has
it set. The fix removes the variable at startup; ``--doctor`` names the owner.
Reproduced on the rig on 2026-09-24 with a stand-in app (case A: the container
died with the app's unit; case B, the fix: it survived). These tests hold the
two halves: the variable is gone before anything can spawn, and the owner
lookup reads ``/proc`` correctly and never raises.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import container_scope
from platterpus.container_scope import (
    ContainerOwner,
    Ownership,
    app_from_unit,
    classify,
    container_owner,
    release_launcher_unit_hold,
    unit_from_cgroup,
)

_PLATTERPUS_UNIT = (
    "app-io.github.rmccann_hub.Platterpus@38d9de2a1b8f4519a672aeb63feb3cf7.service"
)
_OWN_SCOPE = "libpod-conmon-2abb8858c807d9d4dd36ee927645c67a0cc982a4d18d378f33dccbd2874db979.scope"


# --- The release ------------------------------------------------------------


def test_release_removes_the_variable_and_nothing_else() -> None:
    env = {"INVOCATION_ID": "abc", "HOME": "/home/x", "PATH": "/usr/bin"}
    assert release_launcher_unit_hold(env) is True
    assert env == {"HOME": "/home/x", "PATH": "/usr/bin"}
    assert release_launcher_unit_hold(env) is False, "a second call finds nothing"


def test_a_child_spawned_after_the_release_does_not_inherit_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The property that matters is the CHILD's environment, so spawn one."""
    monkeypatch.setenv("INVOCATION_ID", "0123456789abcdef")
    release_launcher_unit_hold(os.environ)
    seen = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ.get('INVOCATION_ID'))"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert seen == "None"


def test_main_releases_it_before_anything_can_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--doctor`` is the first path out of startup that spawns the wrapper.

    Its first step, ``default_context``, builds the backend, and the checks
    after it run the wrapper. Record the variable at both: if the release were
    moved below the dispatch, or dropped, this sees the launcher's value.
    """
    from types import SimpleNamespace

    from platterpus import app, preflight

    monkeypatch.setenv("INVOCATION_ID", "0123456789abcdef")
    observed: list[str | None] = []

    def fake_context(*_args: object, **_kwargs: object) -> SimpleNamespace:
        observed.append(os.environ.get("INVOCATION_ID"))
        return SimpleNamespace(backend_name="cyanrip")

    def fake_run(*_args: object, **_kwargs: object) -> list[object]:
        observed.append(os.environ.get("INVOCATION_ID"))
        return []

    monkeypatch.setattr(preflight, "default_context", fake_context)
    monkeypatch.setattr(preflight, "run_preflight", fake_run)
    app.main(["--doctor"])
    assert len(observed) == 2, "the doctor path never ran, so this examined nothing"
    assert observed == [None, None]


# --- The owner lookup ------------------------------------------------------


def _proc(tmp_path: Path, processes: dict[int, tuple[str, list[str], str]]) -> Path:
    """A fake ``/proc``: pid -> (comm, argv, cgroup text)."""
    root = tmp_path / "proc"
    root.mkdir()
    (root / "self").mkdir()  # a non-numeric entry, as the real one has
    for pid, (comm, argv, cgroup) in processes.items():
        d = root / str(pid)
        d.mkdir()
        (d / "comm").write_text(comm + "\n", encoding="utf-8")
        (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
        (d / "cgroup").write_text(cgroup, encoding="utf-8")
    return root


def _conmon(name: str, *, exec_session: bool = False) -> list[str]:
    argv = ["/usr/bin/conmon", "--api-version", "1", "-c", "2abb", "-n", name]
    return argv + (["-e", "--exec-attach"] if exec_session else [])


def _cg(unit: str) -> str:
    return f"0::/user.slice/user-1000.slice/user@1000.service/app.slice/{unit}\n"


def test_a_monitor_inside_a_platterpus_window_is_reported_as_that_app(
    tmp_path: Path,
) -> None:
    """The 2026-09-24 reading on the rig, as the check report printed it."""
    proc = _proc(
        tmp_path, {4242: ("conmon", _conmon("ripping"), _cg(_PLATTERPUS_UNIT))}
    )
    owner = container_owner(proc=proc)
    assert owner == ContainerOwner(
        Ownership.APP,
        unit=_PLATTERPUS_UNIT,
        app="io.github.rmccann_hub.Platterpus",
        pid=4242,
    )


def test_a_monitor_in_its_own_scope_is_reported_as_safe(tmp_path: Path) -> None:
    """Case B on the rig: what the fix produces."""
    cgroup = (
        f"0::/user.slice/user-1000.slice/user@1000.service/user.slice/{_OWN_SCOPE}\n"
    )
    proc = _proc(tmp_path, {77: ("conmon", _conmon("ripping"), cgroup)})
    assert container_owner(proc=proc).ownership is Ownership.OWN_SCOPE


def test_exec_session_monitors_and_other_containers_are_ignored(tmp_path: Path) -> None:
    proc = _proc(
        tmp_path,
        {
            10: (
                "conmon",
                _conmon("ripping", exec_session=True),
                _cg("app-x@1.service"),
            ),
            11: ("conmon", _conmon("other"), _cg("app-y@2.service")),
            12: ("bash", ["bash", "-n", "ripping"], _cg("app-z@3.service")),
        },
    )
    assert container_owner(proc=proc) == ContainerOwner(Ownership.NOT_RUNNING)


def test_a_konsole_tab_is_named_by_its_app(tmp_path: Path) -> None:
    proc = _proc(
        tmp_path,
        {5: ("conmon", _conmon("ripping"), _cg("app-org.kde.konsole-22592.scope"))},
    )
    owner = container_owner(proc=proc)
    assert (owner.ownership, owner.app) == (Ownership.APP, "org.kde.konsole")


def test_an_unreadable_proc_is_unknown_not_a_crash(tmp_path: Path) -> None:
    assert container_owner(proc=tmp_path / "absent").ownership is Ownership.UNKNOWN


@pytest.mark.parametrize(
    ("unit", "app"),
    [
        (_PLATTERPUS_UNIT, "io.github.rmccann_hub.Platterpus"),
        ("app-org.kde.konsole-22592.scope", "org.kde.konsole"),
        (
            "app-com.onepassword.OnePassword@autostart.service",
            "com.onepassword.OnePassword",
        ),
        (_OWN_SCOPE, ""),
        ("session-2.scope", ""),
    ],
)
def test_app_names_come_from_the_unit_name(unit: str, app: str) -> None:
    assert app_from_unit(unit) == app


def test_classification_covers_every_kind() -> None:
    assert classify(_OWN_SCOPE) is Ownership.OWN_SCOPE
    assert classify(_PLATTERPUS_UNIT) is Ownership.APP
    assert classify("session-2.scope") is Ownership.OTHER
    assert classify("") is Ownership.UNKNOWN


def test_unit_from_cgroup_reads_the_v2_line_only() -> None:
    text = "12:pids:/user.slice\n0::/user.slice/user@1000.service/app.slice/x.service\n"
    assert unit_from_cgroup(text) == "x.service"
    assert unit_from_cgroup("garbage") == ""


@given(st.text())
def test_unit_from_cgroup_never_raises(text: str) -> None:
    assert isinstance(unit_from_cgroup(text), str)


@given(st.text())
def test_app_from_unit_never_raises(unit: str) -> None:
    assert isinstance(app_from_unit(unit), str)


# --- The --doctor line ------------------------------------------------------


def test_doctor_warns_when_an_app_owns_the_container_and_names_it() -> None:
    from platterpus.preflight import Status, check_container_owner

    result = check_container_owner(
        ContainerOwner(
            Ownership.APP,
            unit=_PLATTERPUS_UNIT,
            app="io.github.rmccann_hub.Platterpus",
            pid=4242,
        )
    )
    assert result.status is Status.WARN
    assert "io.github.rmccann_hub.Platterpus" in result.summary
    assert "distrobox stop" in result.hint


@pytest.mark.parametrize(
    ("ownership", "status"),
    [
        (Ownership.OWN_SCOPE, "ok"),
        (Ownership.NOT_RUNNING, "ok"),
        (Ownership.UNKNOWN, "warn"),
        (Ownership.OTHER, "warn"),
    ],
)
def test_doctor_status_for_every_ownership(ownership: Ownership, status: str) -> None:
    from platterpus.preflight import check_container_owner

    assert (
        check_container_owner(ContainerOwner(ownership, unit="u")).status.value
        == status
    )


def test_the_doctor_runs_the_owner_check() -> None:
    """Not merely defined: `run_preflight` must emit it, or --doctor never shows it."""
    import inspect

    from platterpus import preflight

    assert "check_container_owner()" in inspect.getsource(preflight.run_preflight)


def test_the_module_never_starts_or_stops_the_container() -> None:
    """Critical rule #3: this module reads /proc and edits our env, nothing else.

    Read from the syntax tree, not the text, because the module's comments name
    podman and distrobox to explain what it avoids.
    """
    import ast

    tree = ast.parse(Path(container_scope.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names
            if isinstance(node, ast.Import)
            else [ast.alias(node.module or "")]
        )
    }
    assert not imported & {"subprocess", "shutil", "signal"}, imported
    calls = {
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else getattr(node.func, "id", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert not calls & {
        "system",
        "popen",
        "kill",
        "killpg",
        "execv",
        "execvp",
        "spawnv",
    }, calls
