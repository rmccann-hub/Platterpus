"""The setup wizard's real plan, read by calling it: the commands it would run,
the packages it installs inside the container, the binaries it exports, and
the host installers `install_argv` chooses per distro family.
"""

from __future__ import annotations

import tempfile
from functools import cache
from pathlib import Path
from typing import Final

from bommap.model import GeneratorError


class _PlanRunner:
    """A runner that runs nothing: ``HostSetup`` needs one to be constructed.

    Only ``_commands_for`` is called below, which builds argvs and never runs
    them, so nothing here can touch the machine this generator runs on.
    """

    def which(self, name: str) -> bool:
        return False

    def exists(self, path: Path) -> bool:
        return False

    def run(self, argv: list[str]) -> tuple[int, str]:
        raise GeneratorError("the setup plan tried to run a command")


@cache
def setup_plan() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """(step, argv) for every command the setup wizard's plan would run.

    Called on the REAL ``HostSetup``, with an ``os-release`` path that does not
    exist so the distro-dependent steps take their unknown-distro branch — the
    same answer on every machine, which is what a deterministic file needs.
    """
    from platterpus.deps.host_setup import HostSetup

    setup = HostSetup(runner=_PlanRunner(), os_release=Path("/nonexistent/os-release"))
    out: list[tuple[str, tuple[str, ...]]] = []
    for step in setup.STEP_IDS:
        for argv in setup._commands_for(step):
            if argv:
                out.append((step, tuple(argv)))
    return tuple(out)


def _dnf_installs() -> dict[str, tuple[str, ...]]:
    """Setup step → the packages it ``dnf install``s inside the container."""
    out: dict[str, list[str]] = {}
    for step, argv in setup_plan():
        if "dnf" in argv and "install" in argv:
            start = argv.index("install") + 1
            out.setdefault(step, []).extend(
                a for a in argv[start:] if not a.startswith("-")
            )
    return {step: tuple(pkgs) for step, pkgs in out.items()}


def _exports() -> dict[str, tuple[str, ...]]:
    """Binary basename → the in-container paths the wizard exports to ~/.local/bin."""
    out: dict[str, list[str]] = {}
    for _step, argv in setup_plan():
        if "distrobox-export" in argv and "--bin" in argv:
            path = argv[argv.index("--bin") + 1]
            out.setdefault(Path(path).name, []).append(path)
    return {name: tuple(paths) for name, paths in sorted(out.items())}


#: Distro families whose installer argv is read from ``install_argv``. The
#: COMMANDS come from the code; only the families are named here, as the
#: os-release IDs the function branches on.
_DISTRO_FAMILIES: Final[tuple[str, ...]] = (
    "fedora",
    "debian",
    "arch",
    "opensuse-tumbleweed suse",
)


def _installer_programs() -> set[str]:
    """Every program ``install_argv`` would run, across the distro families.

    Called with the GUI's real elevation command (``HostSetup.elevate``'s
    default) and a throwaway ``os-release`` per family, plus one that does not
    exist (the unknown-distro branch). Three shapes come back:

    * ``[elevate, manager, …, tool]`` — the elevation command, the package
      manager, and the tool being installed;
    * ``["sh", "-c", "curl … | elevate sh"]`` — every command in the pipeline;
    * ``[]`` — no safe command (podman on an unknown distro).
    """
    from platterpus.deps.host_setup import HostSetup, install_argv

    elevate = HostSetup.__dataclass_fields__["elevate"].default
    assert isinstance(elevate, str)
    found: set[str] = set()
    with tempfile.TemporaryDirectory() as tmp:
        absent = Path(tmp) / "absent"
        for family in (*_DISTRO_FAMILIES, ""):
            release = Path(tmp) / "os-release"
            ident, _, like = family.partition(" ")
            release.write_text(f"ID={ident}\nID_LIKE={like}\n", encoding="utf-8")
            for tool in ("distrobox", "podman"):
                argv = install_argv(tool, release if family else absent, elevate)
                if not argv:
                    continue
                if argv[0] == elevate:
                    found.update({elevate, argv[1], tool})
                elif argv[0] == "sh" and len(argv) > 2:
                    found.add("sh")
                    for segment in argv[2].split("|"):
                        words = segment.split()
                        found.update(words[:2] if words[:1] == [elevate] else words[:1])
                else:
                    raise GeneratorError(
                        f"install_argv returned an unknown shape: {argv[:2]}"
                    )
    return found


def _fork_refs() -> tuple[str, ...]:
    """The refs of every fork build in the map: each is built the same way."""
    from platterpus.deps import fork_source as fs

    refs = ["ripper:cyanrip-fork"]
    if fs.UNDER_REVIEW_TARGET.pin != fs.PRODUCTION_TARGET.pin:
        refs.append("ripper:cyanrip-fork-under-review")
    return tuple(refs)


def _manifest_url() -> str:
    from platterpus.deps.ripper_manifest import MANIFEST_URL

    return MANIFEST_URL


def _container_name() -> str:
    from platterpus.deps.host_setup import DEFAULT_CONTAINER

    return DEFAULT_CONTAINER


def _registry_name(dep_id: str) -> str:
    """The program name for a registry entry (``cdparanoia`` runs ``cd-paranoia``)."""
    if dep_id == "cdparanoia":
        from platterpus.paths import CDPARANOIA_BINARY_DEFAULT

        return CDPARANOIA_BINARY_DEFAULT.name
    if dep_id == "picard":
        return "MusicBrainz Picard"
    return dep_id
