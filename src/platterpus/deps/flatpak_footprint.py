"""Picard's part of the uninstall: the app, its runtime, and the flathub user remote.

Picard is installed at user level from its ``.flatpakref`` (``deps/registry.py``),
which also adds the ``flathub`` remote at user level and pulls a runtime. A
plain ``flatpak uninstall`` of Picard leaves the runtime (hundreds of
megabytes), the remote, and Picard's own folder under ``~/.var/app``. Each of
those is removed here, and each **only when nothing else uses it**: the runtime
when no other user-level app runs on it, the remote when nothing installed still
comes from it. The check is made again just before each removal, because the
answer can change between the preview and the click.

Parsers of ``flatpak`` output never raise; they read tab-separated columns we
asked for by name (``--columns=``), so a column cannot move under us.
"""

from __future__ import annotations

from dataclasses import dataclass

from platterpus.deps.install_footprint import PICARD_APP_ID, FootprintItem, Kind
from platterpus.deps.uninstall_plan import Observation
from platterpus.deps.uninstall_runner import REMOVE_TIMEOUT_S, TeardownRunner

_FLATPAK: str = "flatpak"


def _rows(output: str) -> list[list[str]]:
    """Tab-separated rows of a ``--columns=`` listing, stripped. Never raises."""
    return [
        [cell.strip() for cell in line.split("\t")]
        for line in output.splitlines()
        if line.strip()
    ]


def _last_line(output: str) -> str:
    """The last non-blank line: where a tool puts the sentence explaining a failure."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _ref_id(ref: str) -> str:
    """``org.kde.Platform/x86_64/6.8`` → ``org.kde.Platform``; tolerant of a prefix."""
    bare = ref.removeprefix("runtime/").removeprefix("app/")
    return bare.split("/", 1)[0]


@dataclass
class FlatpakFootprint:
    """Probes and removes Picard's Flatpak items through an injected runner."""

    runner: TeardownRunner
    #: Picard's runtime, remembered from the first scan: once Picard is gone it
    #: can no longer be asked which runtime it used, and a re-scan that could not
    #: name the runtime would read as "runtime gone" when it is still there.
    runtime_ref: str = ""

    def _list(self, *args: str) -> tuple[bool, list[list[str]], str]:
        rc, out = self.runner.run([_FLATPAK, *args])
        if rc != 0:
            return False, [], _last_line(out) or f"exit {rc}"
        return True, _rows(out), ""

    def observe(self, item: FootprintItem) -> Observation:
        """What is present for one of Picard's Flatpak items."""
        if not self.runner.which(_FLATPAK):
            return Observation(item)
        if item.kind is Kind.FLATPAK_APP:
            ok, rows, why = self._list(
                "list", "--user", "--app", "--columns=application"
            )
            if not ok:
                return Observation(item, unchecked=f"flatpak list failed: {why}")
            found = any(row and row[0] == item.name for row in rows)
            return Observation(item, present=(item.name,) if found else ())
        if item.kind is Kind.FLATPAK_RUNTIME:
            return self._observe_runtime(item)
        return self._observe_remote(item, leaving=(PICARD_APP_ID,))

    def _observe_runtime(self, item: FootprintItem) -> Observation:
        rc, out = self.runner.run(
            [_FLATPAK, "info", "--user", "--show-runtime", item.name]
        )
        if rc == 0 and out.strip():
            self.runtime_ref = out.strip().splitlines()[0].strip()
        if not self.runtime_ref:
            return Observation(item)
        ok, rows, why = self._list("list", "--user", "--runtime", "--columns=ref")
        if not ok:
            return Observation(item, unchecked=f"flatpak list failed: {why}")
        if not any(row and row[0] == self.runtime_ref for row in rows):
            return Observation(item)  # Picard's runtime is not a user-level one
        users = self.runtime_users(exclude=item.name)
        held = f"also used by {', '.join(users)}" if users else ""
        return Observation(item, present=(self.runtime_ref,), held=held)

    def runtime_users(self, exclude: str) -> list[str]:
        """User-level apps, other than ``exclude``, that run on Picard's runtime."""
        ok, rows, _ = self._list(
            "list", "--user", "--app", "--columns=application,runtime"
        )
        if not ok:
            return ["(could not list installed apps)"]
        return [
            row[0]
            for row in rows
            if len(row) > 1 and row[1] == self.runtime_ref and row[0] != exclude
        ]

    def remote_users(self, remote: str, leaving: tuple[str, ...]) -> list[str]:
        """Installed refs still from ``remote``, ignoring the ids in ``leaving``.

        A ref counts as leaving when its id is one of ``leaving`` or extends one
        (``org.musicbrainz.Picard.Locale`` goes with Picard).
        """
        ok, rows, _ = self._list("list", "--user", "--columns=ref,origin")
        if not ok:
            return ["(could not list installed refs)"]
        users: list[str] = []
        for row in rows:
            if len(row) < 2 or row[1] != remote:
                continue
            ref_id = _ref_id(row[0])
            if any(ref_id == gone or ref_id.startswith(f"{gone}.") for gone in leaving):
                continue
            users.append(row[0])
        return users

    def _observe_remote(
        self, item: FootprintItem, leaving: tuple[str, ...]
    ) -> Observation:
        ok, rows, why = self._list("remotes", "--user", "--columns=name")
        if not ok:
            return Observation(item, unchecked=f"flatpak remotes failed: {why}")
        if not any(row and row[0] == item.name for row in rows):
            return Observation(item)
        gone = tuple(name for name in (*leaving, _ref_id(self.runtime_ref)) if name)
        users = self.remote_users(item.name, gone)
        held = f"still the source of {', '.join(users)}" if users else ""
        return Observation(item, present=(item.name,), held=held)

    def remove(self, item: FootprintItem, present: tuple[str, ...]) -> tuple[bool, str]:
        """Remove one item, re-checking what holds it first. (ok, what happened)."""
        if item.kind is Kind.FLATPAK_APP:
            argv = [_FLATPAK, "uninstall", "--user", "-y", "--delete-data", item.name]
        elif item.kind is Kind.FLATPAK_RUNTIME:
            users = self.runtime_users(exclude=item.name)
            if users:
                return True, f"kept: now also used by {', '.join(users)}"
            argv = [_FLATPAK, "uninstall", "--user", "-y", *present]
        else:
            users = self.remote_users(item.name, ())
            if users:
                return True, f"kept: still the source of {', '.join(users)}"
            argv = [_FLATPAK, "remote-delete", "--user", item.name]
        rc, out = self.runner.run(argv, timeout=REMOVE_TIMEOUT_S)
        if rc != 0:
            return False, _last_line(out) or f"exit {rc}"
        return True, f"removed {', '.join(present)}"
