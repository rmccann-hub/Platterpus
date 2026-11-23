"""Everything Platterpus creates on a computer — ONE list, read by both uninstallers.

**Why one list.** Until 2026-11-18 there were two uninstallers with two lists:
``uninstall.sh`` (for a source checkout) and the in-app dialog
(``deps/host_teardown.py``). Each knew things the other did not, and neither
knew about the fork's build folder, the container image, the rig folders,
Picard's data or an interrupted download — so a "reinstall" after an uninstall
was not fresh (TASKS R190, the owner: "include everything in the uninstaller").
Now the dialog and the command line both read :func:`footprint`, and a test
(``tests/test_install_footprint.py``) holds this list to every place the code
writes outside its own folders, so a new writer without an entry here fails CI.

**Pure.** This module does no I/O; where the user's folders are is
``deps/user_locations.py``'s question. Deciding what
is actually *present* is the scanner's job (``deps/host_teardown.py``), and
deciding what to remove is the plan's (``deps/uninstall_plan.py``).

**Order is removal order.** The container goes before its image, Picard before
its runtime and the runtime before the remote it came from, the command link
before the virtual environment it points into, and the settings and logs go
last so the log survives the longest (and is kept when anything failed).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

from platterpus.deps import fork_source
from platterpus.deps.host_setup import DEFAULT_CONTAINER, DEFAULT_IMAGE
from platterpus.deps.user_locations import Locations
from platterpus.paths import (
    APP_ID,
    APP_NAME,
    CDPARANOIA_BINARY_DEFAULT,
    CYANRIP_BINARY_DEFAULT,
    FLAC_BINARY_DEFAULT,
    LEGACY_RIPPER_CONFIG_DIR,
    LEGACY_RIPPER_WRAPPER_PATH,
)
from platterpus.test_session import RIG_PARENT_NAME

#: Picard's Flatpak application id (``deps/registry.py`` installs it).
PICARD_APP_ID: Final[str] = "org.musicbrainz.Picard"

#: The Flatpak remote Picard's ``.flatpakref`` adds at user level on first install.
FLATHUB_REMOTE: Final[str] = "flathub"

#: The folder name older versions used, before the app was called Platterpus:
#: the previous ripper's name plus ``-gui``. Derived, never spelled, so the old
#: name stays out of live text (``tests/test_no_previous_ripper_in_live_text.py``).
LEGACY_APP_SLUG: Final[str] = f"{LEGACY_RIPPER_CONFIG_DIR.name}-gui"

#: The hidden partial-download files: the in-app updater's
#: (``update_install.py``) and ``install.sh``'s. Both land beside the AppImage.
PARTIAL_DOWNLOADS: Final[tuple[str, ...]] = (
    f".{APP_NAME}-update.part",
    f".{APP_NAME}-install.part",
)

#: Names of the binaries the setup wizard exports into ``~/.local/bin``, plus the
#: leftover wrapper of the ripper older versions drove. Must mirror
#: ``host_setup``'s export step (``tests/test_audit_regressions.py``).
EXPORTED_BINARIES: Final[tuple[str, ...]] = (
    CYANRIP_BINARY_DEFAULT.name,
    "metaflac",
    FLAC_BINARY_DEFAULT.name,
    CDPARANOIA_BINARY_DEFAULT.name,
    LEGACY_RIPPER_WRAPPER_PATH.name,
)


class Kind(Enum):
    """How an item is found and removed."""

    FILE = "file"  # one file (or symlink)
    TREE = "tree"  # one folder and everything in it
    MATCHING_FILES = "matching files"  # files in a folder matching a pattern
    MATCHING_TREES = "matching folders"  # folders in a folder matching a pattern
    EXPORT = "export"  # a ~/.local/bin wrapper, removed only if Distrobox wrote it
    VENV_LINK = "venv link"  # ~/.local/bin/platterpus, only if it points into a .venv
    CONTAINER = "container"  # the Distrobox container, matched by exact name
    IMAGE = "image"  # its image, only when no other container uses it
    FLATPAK_APP = "flatpak app"  # Picard, with its data
    FLATPAK_RUNTIME = (
        "flatpak runtime"  # Picard's runtime, only if nothing else uses it
    )
    FLATPAK_REMOTE = "flatpak remote"  # the flathub user remote, only if unused
    SYSTEM_PACKAGE = "system package"  # distrobox/podman, only if we installed them


class Group(Enum):
    """Which choice in the dialog (or flag on the command line) governs an item."""

    APP = "the app"  # always removed
    SETTINGS = "settings and measured drive data"  # keep box (a)
    LOGS = "logs, test runs and bundles"  # keep box (b)
    PICARD = "MusicBrainz Picard"  # keep box (c)
    RIPS = "your rips"  # opt-in (d)
    SYSTEM_PACKAGES = "system packages"  # opt-in (e)


@dataclass(frozen=True)
class FootprintItem:
    """One thing Platterpus creates, and where it comes from."""

    item_id: str
    title: str
    kind: Kind
    group: Group
    #: A path for the file kinds; the folder searched for the matching kinds.
    path: Path | None = None
    #: The case-insensitive ``fnmatch`` pattern for the matching kinds.
    pattern: str = ""
    #: The name for the container, image, Flatpak and package kinds.
    name: str = ""
    #: Kept when an earlier removal failed, so the log survives to debug with.
    keep_on_failure: bool = False


def footprint(
    loc: Locations,
    *,
    appimage: Path | None = None,
    venv: Path | None = None,
    rips: Path | None = None,
    system_packages: tuple[str, ...] = (),
) -> tuple[FootprintItem, ...]:
    """Everything Platterpus creates, in removal order.

    ``appimage`` is the running AppImage, wherever it is; ``venv`` a source
    checkout's ``.venv``; ``rips`` the (already checked) rips folder; and
    ``system_packages`` the packages the install note says we installed.
    """
    bin_dir = loc.home / ".local" / "bin"
    apps = loc.home / "Applications"
    menu = loc.data_home / "applications"
    icons = loc.data_home / "icons"
    app, settings, logs = Group.APP, Group.SETTINGS, Group.LOGS
    items: list[FootprintItem] = [
        FootprintItem(
            "container",
            f"the '{DEFAULT_CONTAINER}' container (cyanrip and its tools)",
            Kind.CONTAINER,
            app,
            name=DEFAULT_CONTAINER,
        ),
        FootprintItem(
            "image",
            "the container's image (Fedora toolbox)",
            Kind.IMAGE,
            app,
            name=DEFAULT_IMAGE,
        ),
    ]
    items += [
        FootprintItem(
            f"export:{name}",
            f"~/.local/bin/{name}",
            Kind.EXPORT,
            app,
            path=bin_dir / name,
        )
        for name in EXPORTED_BINARIES
    ]
    items.append(
        FootprintItem(
            "cli_link",
            f"~/.local/bin/{APP_NAME}",
            Kind.VENV_LINK,
            app,
            path=bin_dir / APP_NAME,
        )
    )
    shortcut_names = (f"{APP_ID}.desktop", f"{APP_NAME}.desktop")
    menu_names = (
        *shortcut_names,
        f"{APP_NAME}-uninstall.desktop",
        f"{LEGACY_APP_SLUG}.desktop",
    )
    items += [
        FootprintItem(f"menu:{name}", "menu entry", Kind.FILE, app, path=menu / name)
        for name in menu_names
    ]
    desktop_folders = dict.fromkeys([loc.desktop_folder, loc.home / "Desktop"])
    items += [
        FootprintItem(
            f"desktop:{folder.name}/{name}",
            "desktop shortcut",
            Kind.FILE,
            app,
            path=folder / name,
        )
        for folder in desktop_folders
        for name in shortcut_names
    ]
    items += [
        FootprintItem(f"icon:{name}", "menu icon", Kind.FILE, app, path=icons / name)
        for name in (f"{APP_ID}.png", f"{APP_NAME}.png")
    ]
    if appimage is not None:
        items.append(
            FootprintItem(
                "appimage:running",
                "the running AppImage",
                Kind.FILE,
                app,
                path=appimage,
            )
        )
    items += [
        FootprintItem(
            "appimages",
            "AppImages in ~/Applications",
            Kind.MATCHING_FILES,
            app,
            path=apps,
            pattern=f"{APP_NAME}*.appimage",
        ),
        FootprintItem(
            "appimages:old",
            "AppImages of older versions",
            Kind.MATCHING_FILES,
            app,
            path=apps,
            pattern=f"{LEGACY_APP_SLUG}*.appimage",
        ),
    ]
    download_dirs = dict.fromkeys(
        [apps, *([appimage.parent] if appimage is not None else [])]
    )
    items += [
        FootprintItem(
            f"part:{folder}/{name}",
            "an interrupted download",
            Kind.FILE,
            app,
            path=folder / name,
        )
        for folder in download_dirs
        for name in PARTIAL_DOWNLOADS
    ]
    items.append(
        FootprintItem(
            "staged_uninstaller",
            "the staged uninstaller",
            Kind.FILE,
            app,
            path=apps / f"{APP_NAME}-uninstall.sh",
        )
    )
    items += [
        FootprintItem(
            "old:ripper_config",
            "leftover ripper settings (older versions)",
            Kind.TREE,
            app,
            path=loc.config_home / LEGACY_RIPPER_CONFIG_DIR.name,
        ),
        FootprintItem(
            "old:config",
            "settings of older versions",
            Kind.TREE,
            app,
            path=loc.config_home / LEGACY_APP_SLUG,
        ),
        FootprintItem(
            "old:data",
            "logs of older versions",
            Kind.TREE,
            app,
            path=loc.data_home / LEGACY_APP_SLUG,
        ),
        # The fork's source and build folder lives under $HOME/.cache whatever
        # XDG_CACHE_HOME says: fork_source builds it from $HOME inside the shell.
        FootprintItem(
            "cache",
            "the cyanrip source and build cache",
            Kind.TREE,
            app,
            path=loc.home / Path(fork_source.FORK_SOURCE_SUBPATH).parent,
        ),
        FootprintItem(
            "picard",
            "MusicBrainz Picard (Flatpak, with its data)",
            Kind.FLATPAK_APP,
            Group.PICARD,
            name=PICARD_APP_ID,
        ),
        FootprintItem(
            "picard:data",
            "Picard's own settings folder",
            Kind.TREE,
            Group.PICARD,
            path=loc.home / ".var" / "app" / PICARD_APP_ID,
        ),
        FootprintItem(
            "picard:runtime",
            "Picard's Flatpak runtime",
            Kind.FLATPAK_RUNTIME,
            Group.PICARD,
            name=PICARD_APP_ID,
        ),
        FootprintItem(
            "picard:remote",
            "the flathub user remote",
            Kind.FLATPAK_REMOTE,
            Group.PICARD,
            name=FLATHUB_REMOTE,
        ),
        FootprintItem(
            "rig",
            "test-run folders",
            Kind.MATCHING_TREES,
            logs,
            path=loc.home,
            pattern=f"{RIG_PARENT_NAME}*",
        ),
        FootprintItem(
            "rig:old",
            "test-run folders of older versions",
            Kind.MATCHING_TREES,
            logs,
            path=loc.home,
            pattern=f"{APP_NAME}testsession*",
        ),
    ]
    if rips is not None:
        items.append(
            FootprintItem("rips", "your rips", Kind.TREE, Group.RIPS, path=rips)
        )
    items += [
        FootprintItem(
            f"package:{name}",
            f"the {name} system package",
            Kind.SYSTEM_PACKAGE,
            Group.SYSTEM_PACKAGES,
            name=name,
        )
        for name in system_packages
    ]
    if venv is not None:
        items.append(
            FootprintItem(
                "venv", "the source checkout's .venv", Kind.TREE, app, path=venv
            )
        )
    items += [
        FootprintItem(
            "settings",
            "Platterpus settings and drive data",
            Kind.TREE,
            settings,
            path=loc.config_home / APP_NAME,
        ),
        FootprintItem(
            "logs",
            "Platterpus logs and support bundles",
            Kind.TREE,
            logs,
            path=loc.data_home / APP_NAME,
            keep_on_failure=True,
        ),
    ]
    return tuple(items)
