"""The install note (deps/system_packages_marker.py): what Platterpus itself installed.

The uninstaller offers to remove Distrobox/podman only when this note names them
(TASKS R190), so a wrong answer either strands a package we installed or, much
worse, removes the user's own tools. Reading never raises and errs towards "we
installed nothing", which keeps their tools.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.deps import system_packages_marker as marker

REPO = Path(__file__).resolve().parents[1]


def test_record_read_and_forget(tmp_path: Path) -> None:
    note = tmp_path / "sub" / marker.MARKER_NAME
    assert marker.read_installed(note) == ()
    assert marker.record_installed("distrobox", note)
    assert marker.record_installed("podman", note)
    assert marker.record_installed("podman", note)  # no repeat
    assert marker.read_installed(note) == ("distrobox", "podman")
    marker.forget_installed(("distrobox",), note)
    assert marker.read_installed(note) == ("podman",)
    marker.forget_installed(("podman",), note)
    assert not note.exists()


def test_anything_but_a_package_name_is_ignored(tmp_path: Path) -> None:
    note = tmp_path / marker.MARKER_NAME
    note.write_text(
        "# comment\npodman\nrm -rf /\n$(evil)\n\nDistrobox\n", encoding="utf-8"
    )
    assert marker.read_installed(note) == ("podman",)
    assert not marker.record_installed("podman; reboot", note)


def test_an_unreadable_note_means_nothing_was_installed(tmp_path: Path) -> None:
    folder = tmp_path / marker.MARKER_NAME
    folder.mkdir()  # a folder where the file should be: reading raises IsADirectoryError
    assert marker.read_installed(folder) == ()


def test_setup_host_sh_writes_the_same_note() -> None:
    script = (REPO / "setup-host.sh").read_text(encoding="utf-8")
    assert marker.MARKER_NAME in script
    assert "note_installed distrobox" in script
    assert "note_installed podman" in script
    assert marker.MARKER_PATH.parent.name == "platterpus"
