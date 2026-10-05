"""External programs the app runs or offers, the desktop interface, bundled data."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from bommap.model import _P, ROOT_REF, Entry, GeneratorError
from bommap.plan import (
    _dnf_installs,
    _exports,
    _installer_programs,
    _registry_name,
    setup_plan,
)
from bommap.reading import (
    _code_strings,
    _join,
    _require,
    _src_files,
    _text,
    _vers,
    tool_lookups,
)


@dataclass(frozen=True)
class _ToolNote:
    """What a tool is for. The tool's NAME is never taken from here alone."""

    purpose: str
    scope: str = "optional"
    runs_in: str = "host"
    #: (file, literal, as_word?) — proof the code still uses it, for tools no
    #: derivation source finds on its own.
    witnesses: tuple[tuple[str, str, bool], ...] = ()


#: One note per external program. A program the code is found to use without a
#: note here stops the run; a note whose program the code no longer uses stops
#: it too. Registry tools (cyanrip, flac, …) are described by the registry and
#: are not repeated here.
_TOOL_NOTES: Final[dict[str, _ToolNote]] = {
    "distrobox": _ToolNote(
        "Creates and enters the ripping container: setup, the fork build, the "
        "scoped force-stop exception, and teardown.",
        scope="required",
    ),
    "distrobox-enter": _ToolNote(
        "What the exported ~/.local/bin wrappers run; the wrapper probe times it "
        "to diagnose a wrapper that hangs.",
        scope="required",
        witnesses=(
            ("src/platterpus/deps/ripper_wrapper_probe.py", "distrobox-enter", False),
        ),
    ),
    "distrobox-export": _ToolNote(
        "Exports cyanrip, flac, metaflac and cd-paranoia from the container to "
        "~/.local/bin.",
        scope="required",
        runs_in="ripping container",
    ),
    "podman": _ToolNote(
        "Distrobox's container engine; the wizard installs it when no engine is "
        "present. Docker is accepted instead when it is already there.",
        scope="required",
    ),
    "docker": _ToolNote(
        "Accepted in place of podman as Distrobox's engine when present.",
    ),
    "sudo": _ToolNote(
        "Root inside the container for dnf and the fork install.",
        scope="required",
        runs_in="ripping container",
    ),
    "dnf": _ToolNote(
        "Installs flac, cyanrip, cd-paranoia and the fork's build inputs inside "
        "the container; also the host installer on Fedora-family systems.",
        scope="required",
        runs_in="ripping container; host on Fedora-family systems",
    ),
    "sh": _ToolNote(
        "Runs the fork's build, install and verify scripts in the container, and "
        "the upstream Distrobox installer on an unrecognised distro.",
        scope="required",
        runs_in="ripping container; host for the Distrobox installer",
    ),
    "pkexec": _ToolNote(
        "Graphical privilege prompt for installing Distrobox or podman on the host "
        "(a GUI has no terminal for sudo).",
    ),
    "apt-get": _ToolNote("Host installer for Distrobox / podman on Debian and Ubuntu."),
    "pacman": _ToolNote("Host installer for Distrobox / podman on Arch."),
    "zypper": _ToolNote("Host installer for Distrobox / podman on openSUSE."),
    "curl": _ToolNote(
        "Fetches the upstream Distrobox installer on an unrecognised distro.",
    ),
    "flatpak": _ToolNote(
        "Installs MusicBrainz Picard from Flathub and launches it for an unknown disc.",
        witnesses=(("src/platterpus/ui/unknown_album.py", "flatpak", False),),
    ),
    "systemd-inhibit": _ToolNote(
        "Holds idle sleep, suspend and the lid switch off during a long unattended run.",
    ),
    "fuser": _ToolNote(
        "Device-scoped force-stop of whatever holds the drive on cancel (host copy only).",
    ),
    "pkill": _ToolNote(
        "Name-matched force-stop of the reader on cancel (host first, then the "
        "container — Critical rule #3's scoped exception).",
    ),
    "pgrep": _ToolNote(
        "Lists the reader processes the host sees: the exit check, and the "
        "acceptance bundle's record of whether a ripper was still running as it "
        "was packed (host copy only; never signals anything).",
    ),
    "eject": _ToolNote("Opens the drive tray after a force-stop."),
    "gio": _ToolNote(
        "Marks the desktop shortcut trusted after AppImage integration.",
        witnesses=(("src/platterpus/appimage_integration.py", "gio", False),),
    ),
    "update-desktop-database": _ToolNote(
        "Refreshes the menu after AppImage integration (fire-and-forget).",
        witnesses=(
            (
                "src/platterpus/appimage_integration.py",
                "update-desktop-database",
                False,
            ),
        ),
    ),
    "kbuildsycoca6": _ToolNote(
        "Refreshes KDE Plasma 6's menu cache after AppImage integration (fire-and-forget).",
        witnesses=(("src/platterpus/appimage_integration.py", "kbuildsycoca6", False),),
    ),
    "kbuildsycoca5": _ToolNote(
        "The same refresh for KDE Plasma 5 (fire-and-forget).",
        witnesses=(("src/platterpus/appimage_integration.py", "kbuildsycoca5", False),),
    ),
    "bash": _ToolNote(
        "Runs the packaged rig_session.sh for --rig-session. That script uses "
        "ordinary shell utilities, which are not listed one by one.",
        witnesses=(("src/platterpus/app.py", "bash", False),),
    ),
}


def _host_tool_entries() -> list[Entry]:
    from platterpus.adapters.transcode import __file__ as transcode_file
    from platterpus.deps.registry import SPECS
    from platterpus.sleep_inhibit import INHIBIT_BINARY

    # --- Collect every program the code is found to use, with where ---
    found: dict[str, set[str]] = {}

    def note(program: str, rel: str) -> None:
        found.setdefault(program, set()).add(rel)

    for program, files in tool_lookups().items():
        for rel in files:
            note(program, rel)
    for step, argv in setup_plan():
        # The fork's build step is planned by fork_source.fork_build_commands;
        # every other step by host_setup itself.
        planner = (
            "src/platterpus/deps/fork_source.py"
            if step == "cyanrip_fork"
            else "src/platterpus/deps/host_setup.py"
        )
        note(argv[0], planner)
        if "--" in argv:
            note(argv[argv.index("--") + 1], planner)
    for program in _installer_programs():
        note(program, "src/platterpus/deps/host_setup.py")
    picard = next(spec for spec in SPECS if spec.dep_id == "picard")
    if picard.install_command:
        note(picard.install_command[0], "src/platterpus/deps/registry.py")
        # Picard has no binary name: it is a Flatpak, reached by its app ID,
        # which is the stem of the .flatpakref it installs from.
        app_id = Path(picard.install_command[-1]).stem
        for rel in _src_files():
            if any(app_id in s for s in _code_strings(rel)):
                note(_registry_name("picard"), rel)
    note(INHIBIT_BINARY, "src/platterpus/sleep_inhibit.py")
    for program, info in _TOOL_NOTES.items():
        for rel, literal, as_word in info.witnesses:
            note(
                program,
                _require(rel, literal, as_word=as_word, why=f"tool {program}"),
            )

    registry_names = {_registry_name(spec.dep_id) for spec in SPECS}
    registry_names.add("cyanrip")  # the ripper category carries it
    unmapped = sorted(set(found) - set(_TOOL_NOTES) - registry_names)
    if unmapped:
        raise GeneratorError(
            f"the code uses {unmapped} and scripts/emit_bom.py has no note for "
            "them; add a _TOOL_NOTES entry saying what each is for"
        )
    stale = sorted(set(_TOOL_NOTES) - set(found))
    if stale:
        raise GeneratorError(
            f"_TOOL_NOTES describes {stale}, which the code no longer uses; "
            "remove them or add the witness that shows where they are used"
        )

    entries: list[Entry] = []
    exports = _exports()
    installs = _dnf_installs()
    encoders = _ffmpeg_encoders(Path(transcode_file))
    for spec in SPECS:
        if spec.dep_id in {"cyanrip", "musicbrainzngs"}:
            continue  # the ripper and python-runtime categories carry these
        name = _registry_name(spec.dep_id)
        minimum = ".".join(str(n) for n in spec.min_version)
        any_version = all(n == 0 for n in spec.min_version)
        props: list[tuple[str, str]] = [
            (_P + "registry-id", spec.dep_id),
            (_P + "checked-minimum", "any version" if any_version else minimum),
            (_P + "resolution-tier", spec.tier.value),
        ]
        if spec.from_setup_wizard:
            route = [
                f"exported to ~/.local/bin by the setup wizard from {_join(exports.get(name, ()))}"
            ]
            for step, pkgs in installs.items():
                for pkg in pkgs:
                    if (
                        pkg == name
                        or Path(pkg).name == name
                        or (name == "metaflac" and pkg == "flac")
                    ):
                        route.insert(
                            0, f"dnf install {pkg} in the container (step {step})"
                        )
            props.append((_P + "install-route", "; ".join(route)))
            props.append(
                (_P + "runs-in", "ripping container (through the host export)")
            )
        elif spec.install_command:
            props.append((_P + "install-route", " ".join(spec.install_command)))
            props.append((_P + "runs-in", "host"))
        else:
            props.append((_P + "install-route", "the user's own package manager"))
            props.append((_P + "runs-in", "host"))
        if name == "ffmpeg":
            props.append((_P + "encoders-used", _join(encoders)))
        spec_files = {"src/platterpus/deps/registry.py", *found.get(name, ())}
        entries.append(
            Entry(
                ref=f"tool:{spec.dep_id}",
                category="host-tool",
                name=name,
                version_range="" if any_version else _vers("generic", f">={minimum}"),
                is_external=True,
                scope="optional" if spec.optional else "required",
                description=spec.description,
                used_in=tuple(sorted(spec_files)),
                enforced_in=(
                    "src/platterpus/deps/registry.py (min_version, probed at launch)",
                ),
                properties=tuple(props),
                required_by=(ROOT_REF,),
            )
        )
    # Who needs each program, when it is not simply "Platterpus": the
    # container-side tools belong to the container, Distrobox's engines to
    # Distrobox, and Flatpak to Picard as well as to the app that installs it.
    needed_by: dict[str, tuple[str, ...]] = {
        "sudo": ("container:ripping",),
        "distrobox-export": ("container:ripping",),
        "podman": ("tool-host:distrobox",),
        "docker": ("tool-host:distrobox",),
        "flatpak": (ROOT_REF, "tool:picard"),
    }
    for program in sorted(_TOOL_NOTES):
        info = _TOOL_NOTES[program]
        required_by = needed_by.get(program, (ROOT_REF,))
        entries.append(
            Entry(
                ref=f"tool-host:{program}",
                category="host-tool",
                name=program,
                is_external=True,
                scope=info.scope,
                description=info.purpose,
                used_in=tuple(sorted(found[program])),
                properties=(
                    (_P + "runs-in", info.runs_in),
                    (_P + "version-basis", "not checked; whatever the system provides"),
                ),
                required_by=required_by,
            )
        )
    return entries


def _ffmpeg_encoders(path: Path) -> list[str]:
    """Every codec the transcode adapter names after ``-c:a``, read from its AST."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    codecs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [
                e.value if isinstance(e, ast.Constant) else None for e in node.elts
            ]
            for index, value in enumerate(values[:-1]):
                following = values[index + 1]
                if value == "-c:a" and isinstance(following, str):
                    codecs.add(following)
    if not codecs:
        raise GeneratorError("found no -c:a codec in adapters/transcode.py")
    return sorted(codecs)


def _desktop_entries() -> list[Entry]:
    from platterpus.screen_inhibit import SCREENSAVER_PATH, SCREENSAVER_SERVICE

    return [
        Entry(
            ref=f"desktop:{SCREENSAVER_SERVICE}",
            category="desktop",
            name=SCREENSAVER_SERVICE,
            cdx_type="platform",
            is_external=True,
            scope="optional",
            description=(
                "The freedesktop screensaver D-Bus interface, used to keep the "
                "screen from blanking during a run that takes screenshots."
            ),
            used_in=("src/platterpus/screen_inhibit.py",),
            properties=((_P + "dbus-object-path", SCREENSAVER_PATH),),
            required_by=(ROOT_REF,),
        )
    ]


def _data_entries() -> list[Entry]:
    header = _text("src/platterpus/adapters/accuraterip_offsets_data.py")
    source = re.search(r"^Source:\s*(?P<url>\S+)", header, re.MULTILINE)
    generated = re.search(
        r"^Generated:\s*(?P<date>\S+)\s*\|\s*drives:\s*(?P<n>\d+)", header, re.MULTILINE
    )
    script = re.search(
        r'^SOURCE_URL = "(?P<url>[^"]+)"',
        _text("scripts/update_drive_offsets.py"),
        re.MULTILINE,
    )
    if source is None or generated is None or script is None:
        raise GeneratorError(
            "the AccurateRip drive-offset snapshot header changed shape"
        )
    return [
        Entry(
            ref="data:accuraterip-drive-offsets",
            category="data",
            name="AccurateRip drive offsets",
            cdx_type="data",
            version=generated.group("date"),
            description=(
                "A snapshot of AccurateRip's drive read-offset table, shipped in "
                "the package so offset lookup works offline."
            ),
            used_in=("src/platterpus/adapters/accuraterip_offsets.py",),
            enforced_in=("scripts/update_drive_offsets.py (regenerates it)",),
            external_refs=(
                (
                    "distribution",
                    script.group("url"),
                    "the source the snapshot was taken from",
                ),
            ),
            properties=(
                (_P + "drives", generated.group("n")),
                (
                    _P + "stored-in",
                    "src/platterpus/adapters/accuraterip_offsets_data.py",
                ),
            ),
            required_by=(ROOT_REF,),
        )
    ]
