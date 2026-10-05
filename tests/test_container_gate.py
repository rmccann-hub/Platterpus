"""The first container command of a session runs alone (`container_gate`).

The 2026-10-04 rig run: the dependency probe and the startup disc scan entered
the stopped container in the same second, and both hung (60 s and 84 s); the
same scan on the running container returned in 13.5 s.
"""

from __future__ import annotations

import os
import stat
import threading
import time
from pathlib import Path

import pytest

from platterpus import container_gate, killable
from platterpus.container_gate import FirstEntryGate


def _export_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the exports directory at a temp folder, as `HOME` would."""
    home = tmp_path / "home"
    exports = home / ".local" / "bin"
    exports.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    assert container_gate.exported_tools_dir() == str(exports), "floor: HOME moved"
    return exports


def test_a_host_tool_never_waits(tmp_path: Path, monkeypatch) -> None:
    _export_dir(monkeypatch, tmp_path)
    gate = FirstEntryGate()
    assert gate.claim("/usr/bin/fuser") is False
    assert gate.claim("") is False
    assert not gate.is_open(), "a host tool opened the container gate"


def test_the_second_container_command_waits_for_the_first(
    tmp_path: Path, monkeypatch
) -> None:
    exports = _export_dir(monkeypatch, tmp_path)
    gate = FirstEntryGate(wait_s=10)
    shim = str(exports / "cyanrip")
    assert gate.claim(shim) is True, "the first command is not the first entry"

    outcome: list[bool] = []
    second = threading.Thread(target=lambda: outcome.append(gate.claim(shim)))
    second.start()
    time.sleep(0.6)
    assert second.is_alive(), "the second entry did not wait for the first"
    gate.release()
    second.join(timeout=5)
    assert outcome == [False], "after the first finished, the second is not first"
    assert gate.is_open()
    started = time.monotonic()
    assert gate.claim(shim) is False
    assert time.monotonic() - started < 0.1, "an open gate still made a caller wait"


def test_the_wait_ends_on_the_callers_cancel_and_at_its_bound(
    tmp_path: Path, monkeypatch
) -> None:
    exports = _export_dir(monkeypatch, tmp_path)
    shim = str(exports / "cyanrip")

    gate = FirstEntryGate(wait_s=30)
    assert gate.claim(shim) is True
    started = time.monotonic()
    assert gate.claim(shim, should_stop=lambda: True) is False
    assert time.monotonic() - started < 2, "a cancelled caller sat out the wait"

    bounded = FirstEntryGate(wait_s=0.5)
    assert bounded.claim(shim) is True
    # On a thread with a join timeout, so a gate that ignores its bound fails
    # this test instead of hanging the suite.
    result: list[tuple[bool, float]] = []

    def second() -> None:
        began = time.monotonic()
        result.append((bounded.claim(shim), time.monotonic() - began))

    waiter = threading.Thread(target=second, daemon=True)
    waiter.start()
    waiter.join(timeout=5)
    assert not waiter.is_alive(), "the wait ignored its bound"
    claimed, waited = result[0]
    assert claimed is False
    assert 0.4 <= waited < 3, f"the bound was not honoured: {waited:.2f}s"


def test_two_cold_probes_through_the_killable_runner_run_one_after_the_other(
    tmp_path: Path, monkeypatch
) -> None:
    """The real chokepoint, with a stand-in export that records when it ran."""
    exports = _export_dir(monkeypatch, tmp_path)
    record = tmp_path / "order.txt"
    shim = exports / "cyanrip"
    shim.write_text(
        "#!/bin/sh\n"
        f'echo "start $1" >> "{record}"\n'
        "sleep 0.4\n"
        f'echo "end $1" >> "{record}"\n'
    )
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(killable, "FIRST_ENTRY", FirstEntryGate(wait_s=10))

    def probe(tag: str) -> None:
        killable.KillableCommand(f"probe {tag}").run([str(shim), tag], timeout=10)

    first = threading.Thread(target=probe, args=("a",))
    first.start()
    time.sleep(0.1)
    second = threading.Thread(target=probe, args=("b",))
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    lines = record.read_text().split()
    order = [" ".join(lines[i : i + 2]) for i in range(0, len(lines), 2)]
    assert order == ["start a", "end a", "start b", "end b"], order
    assert killable.FIRST_ENTRY.is_open()


@pytest.mark.skipif(os.name != "posix", reason="shell stand-in")
def test_once_open_container_commands_overlap_as_before(
    tmp_path: Path, monkeypatch
) -> None:
    exports = _export_dir(monkeypatch, tmp_path)
    record = tmp_path / "order.txt"
    shim = exports / "cyanrip"
    shim.write_text(
        "#!/bin/sh\n"
        f'echo "start $1" >> "{record}"\n'
        "sleep 0.4\n"
        f'echo "end $1" >> "{record}"\n'
    )
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    opened = FirstEntryGate()
    assert opened.claim(str(shim)) is True
    opened.release()
    monkeypatch.setattr(killable, "FIRST_ENTRY", opened)

    threads = [
        threading.Thread(
            target=lambda t=tag: killable.KillableCommand(t).run(
                [str(shim), t], timeout=10
            )
        )
        for tag in ("a", "b")
    ]
    for t in threads:
        t.start()
        time.sleep(0.05)
    for t in threads:
        t.join(timeout=10)
    lines = record.read_text().split()
    assert lines[:4] == ["start", "a", "start", "b"], lines
