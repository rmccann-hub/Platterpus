"""Where this user's folders are, and which rips folder is safe to delete.

Split out of ``deps/install_footprint.py`` so the list of what Platterpus
creates stays one readable list. Everything here is pure except two small
reads the caller asks for: ``user-dirs.dirs`` (the localized Desktop folder)
and ``config.toml``'s ``output_dir`` (the rips folder).
"""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus.paths import APP_NAME, DEFAULT_OUTPUT_DIR


@dataclass(frozen=True)
class Locations:
    """Where this user's folders are. Built once from the environment."""

    home: Path
    config_home: Path
    data_home: Path
    desktop_folder: Path

    @classmethod
    def from_environment(
        cls, env: Mapping[str, str] | None = None, home: Path | None = None
    ) -> Locations:
        """The real locations, honouring ``XDG_*`` and a localized Desktop folder."""
        env = os.environ if env is None else env
        home = Path.home() if home is None else home
        config_home = Path(env.get("XDG_CONFIG_HOME") or home / ".config")
        data_home = Path(env.get("XDG_DATA_HOME") or home / ".local" / "share")
        try:
            user_dirs = (config_home / "user-dirs.dirs").read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            user_dirs = ""
        desktop = desktop_folder_from_user_dirs(user_dirs, home)
        return cls(home, config_home, data_home, desktop)


_DESKTOP_LINE: Final[re.Pattern[str]] = re.compile(
    r'^\s*XDG_DESKTOP_DIR\s*=\s*"(?P<value>[^"]*)"\s*$', re.MULTILINE
)


def desktop_folder_from_user_dirs(text: str, home: Path) -> Path:
    """The Desktop folder named in ``user-dirs.dirs``, or ``home/Desktop``.

    The same file ``xdg-user-dir DESKTOP`` reads, parsed here so no program has
    to be run: a German desktop's ``"$HOME/Schreibtisch"`` is where the
    shortcut was put, and plain ``~/Desktop`` would miss it. A value that is
    not under ``$HOME`` or ``/`` is ignored, as ``xdg-user-dir`` ignores it.
    """
    match = _DESKTOP_LINE.search(text)
    if match is not None:
        value = match.group("value")
        if value.startswith("$HOME/") and len(value) > len("$HOME/"):
            return home / value[len("$HOME/") :]
        if value.startswith("/") and value != "/":
            return Path(value)
    return home / "Desktop"


def rips_setting(config_path: Path) -> str:
    """The rips folder the settings name (``output_dir``), as written.

    Read with ``tomllib`` alone, so the command-line uninstaller needs nothing
    else. A missing or unreadable file means the default folder, which is where
    rips go when nothing was ever set.
    """
    try:
        with config_path.open("rb") as handle:
            value = tomllib.load(handle).get("output_dir")
    except (OSError, tomllib.TOMLDecodeError):
        value = None
    return value if isinstance(value, str) else str(DEFAULT_OUTPUT_DIR)


def safe_rips_folder(raw: str, home: Path) -> tuple[Path | None, str]:
    """The rips folder to delete, or ``None`` and the reason it is refused.

    ``uninstall.sh --remove-rips`` used to delete ``~/Music/rips`` whatever the
    settings named. Now the folder comes from the settings, and anything whose
    deletion would take more than rips with it is refused: an empty or relative
    path, ``/``, the home folder, any folder that contains the home folder,
    and a hidden folder in it (``~/.config``, ``~/.local``…), where settings
    and programs live and rips never do.
    """
    text = raw.strip()
    if not text:
        return None, "the settings name no rips folder"
    path = Path(text).expanduser()
    if not path.is_absolute():
        return None, f"the rips folder {text!r} is not an absolute path"
    resolved = Path(os.path.normpath(path))
    if resolved == Path(resolved.anchor):
        return None, "the rips folder is the root of the filesystem"
    home_resolved = Path(os.path.normpath(home))
    if resolved == home_resolved or home_resolved.is_relative_to(resolved):
        return None, f"the rips folder {resolved} is, or contains, your home folder"
    if resolved.is_relative_to(home_resolved):
        first = resolved.relative_to(home_resolved).parts[0]
        if first.startswith("."):
            return (
                None,
                f"the rips folder {resolved} is inside the hidden folder ~/{first}",
            )
    return resolved, ""


def dev_checkout_venv(prefix: Path) -> Path | None:
    """The ``.venv`` this process runs from, when it is a source checkout's.

    ``prefix`` is ``sys.prefix``. Only a ``.venv`` beside a ``pyproject.toml``
    and ``src/platterpus`` counts, so a pipx or system install never does.
    """
    if prefix.name != ".venv":
        return None
    root = prefix.parent
    if (root / "pyproject.toml").is_file() and (root / "src" / APP_NAME).is_dir():
        return prefix
    return None
