"""Host-stack bootstrap — the GUI-driven equivalent of ``setup-host.sh``.

This is the **bootstrap arm of the dependency self-management subsystem**
(Critical Rule #6 / KDD-17): it owns the multi-step, stateful host stack that
lives *outside* the GUI — Distrobox + a container backend + the ``ripping``
container + cyanrip/flac/metaflac exported to ``~/.local/bin`` — so a
non-technical user never has to open a terminal. The GUI's runtime-tool
*presence* checks (cyanrip/metaflac/Picard) stay in ``registry.py``; this
module sets up the container those tools come from.

Everything runs through an injected :class:`CommandRunner`, so the
orchestration is fully unit-testable and supports a dry-run (commands are
reported, never executed). The real runner (:class:`SubprocessRunner`) shells
out; tests pass a fake. Steps are **idempotent** — each checks current state
first and is skipped when already satisfied — mirroring ``setup-host.sh``.

Note on routing: this is host *setup*, not ripping. Ripping still goes through
the host-exported ``~/.local/bin/cyanrip`` (Critical Rule #3); creating the
container and installing the ripper into it is exactly the bootstrap KDD-17
sanctions doing from the GUI.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from platterpus import diagnostics
from platterpus.cyanrip_cli import VERSION_FLAGS
from platterpus.deps import fork_source
from platterpus.deps.step_engine import (
    CommandRunner,
    StepResult,
    StepStatus,
)
from platterpus.paths import (
    CDPARANOIA_BINARY_DEFAULT,
    CYANRIP_BINARY_DEFAULT,
    FLAC_BINARY_DEFAULT,
)
from platterpus.ripper_identity import identify_from_banner

log = logging.getLogger(__name__)

DEFAULT_CONTAINER: str = "ripping"
DEFAULT_IMAGE: str = "registry.fedoraproject.org/fedora-toolbox:latest"
_OS_RELEASE: Path = Path("/etc/os-release")

# Steps whose "is this already done?" probe ENTERS the container
# (`distrobox enter`). The FIRST enter after creating the container triggers
# distrobox's multi-minute one-time container init (it installs base packages),
# so the probe itself can be slow. We emit a "checking…" ping BEFORE these
# probes so the status line reflects what's happening instead of sitting on the
# previous step's text — which looked like a freeze (real-user report
# 2026-06-26: the wizard appeared stuck at "'ripping' container — working…").
_SLOW_PROBE_STEPS: frozenset[str] = frozenset({"tools", "cyanrip", "cyanrip_fork"})

# --- cyanrip packaging (KDD-18) ---------------------------------------------
# Fedora does NOT package cyanrip (verified 2026-06-09: no result in the
# official repos or RPM Fusion; cyanrip's own README lists Debian/openSUSE/
# Alpine/Void/Nix but not Fedora). The one prebuilt source for our
# fedora-toolbox container is the COPR `barsnick/non-fed` (a Fedora
# contributor's "not-in-Fedora" repo), which has succeeded cyanrip builds
# for Fedora 42/43/44 + rawhide on x86_64, GPG-signed. The fallback, if that
# COPR ever disappears, is a meson source build (all build deps ARE in
# Fedora: ffmpeg-free-devel, libcdio-paranoia-devel, libmusicbrainz5-devel,
# libcurl-devel) — see docs/archive/ecosystem-audit-2026-06.md.
#
# We write the standard COPR repo stanza ourselves instead of running
# `dnf copr enable` because the copr plugin isn't guaranteed to be in the
# container image (dnf4 vs dnf5 ship it differently), while a .repo file
# works everywhere. The content below is exactly what `dnf copr enable`
# would write: $releasever/$basearch keep it valid across Fedora versions,
# and gpgcheck=1 + the COPR-published key keep the packages verified.
CYANRIP_COPR_REPO_PATH: str = "/etc/yum.repos.d/copr-barsnick-non-fed.repo"
CYANRIP_COPR_REPO_CONTENT: str = """\
[copr:copr.fedorainfracloud.org:barsnick:non-fed]
name=Copr repo for non-fed owned by barsnick (provides cyanrip)
baseurl=https://download.copr.fedorainfracloud.org/results/barsnick/non-fed/fedora-$releasever-$basearch/
type=rpm-md
gpgcheck=1
gpgkey=https://download.copr.fedorainfracloud.org/results/barsnick/non-fed/pubkey.gpg
repo_gpgcheck=0
skip_if_unavailable=True
enabled=1
"""

# The step-engine vocabulary (StepStatus / StepResult / CommandRunner /
# SubprocessRunner) lives in deps/step_engine.py, shared with host_teardown.py;
# it is imported above for this module's own use.

# --- Distro detection -------------------------------------------------------


def _os_release_ids(os_release: Path) -> str:
    """Return a lowercase "ID ID_LIKE" string from os-release, or ""."""
    try:
        # errors="replace" — /etc/os-release is not ours; a stray byte must give
        # "unknown distro", not a UnicodeDecodeError past the OSError guard.
        text = os_release.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if value:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return f"{fields.get('ID', '')} {fields.get('ID_LIKE', '')}".lower()


def install_argv(
    tool: str, os_release: Path = _OS_RELEASE, elevate: str = "sudo"
) -> list[str]:
    """The host package-manager argv to install `tool` (distrobox/podman).

    Mirrors setup-host.sh's distro `case`. `elevate` is the privilege-
    escalation command prefixed to the install: the shell script uses
    ``sudo`` (it has a TTY), but the GUI path uses ``pkexec`` so root is
    obtained via a graphical polkit prompt — a GUI subprocess has no
    terminal for ``sudo`` to read a password from. Falls back to the
    upstream Distrobox installer for an unknown distro when installing
    distrobox; for podman on an unknown distro there's no safe universal
    command, so the caller surfaces a manual message (we return []).
    """
    ids = _os_release_ids(os_release)
    if any(d in ids for d in ("fedora", "rhel", "centos")):
        return [elevate, "dnf", "install", "-y", tool]
    if any(d in ids for d in ("debian", "ubuntu")):
        return [elevate, "apt-get", "install", "-y", tool]
    if "arch" in ids:
        return [elevate, "pacman", "-S", "--noconfirm", tool]
    if "suse" in ids:
        return [elevate, "zypper", "--non-interactive", "install", tool]
    # Unknown distro: fall back to the upstream Distrobox installer, elevated
    # via the INJECTED `elevate` — not a hardcoded `sudo`. From the GUI `elevate`
    # is `pkexec` (graphical polkit); hardcoding `sudo` here meant the one path
    # that's supposed to work without a terminal still shelled out to `sudo`,
    # which has no TTY to read a password from and silently fails (#35). (Best-
    # effort / hardware-gated on an actual unknown distro; the known-distro
    # branches above are the tested, common paths.)
    if tool == "distrobox":
        return [
            "sh",
            "-c",
            "curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install "
            f"| {elevate} sh",
        ]
    return []  # podman on an unknown distro → manual


# --- Orchestrator -----------------------------------------------------------


@dataclass
class HostSetup:
    """Plans and runs the host-stack bootstrap (idempotently)."""

    runner: CommandRunner
    container: str = DEFAULT_CONTAINER
    image: str = DEFAULT_IMAGE
    os_release: Path = _OS_RELEASE
    cyanrip_path: Path = CYANRIP_BINARY_DEFAULT
    flac_path: Path = FLAC_BINARY_DEFAULT
    cdparanoia_path: Path = CDPARANOIA_BINARY_DEFAULT
    # Privilege escalation for host-root installs. "pkexec" (the default)
    # shows a graphical polkit prompt — correct for a GUI with no TTY. On
    # Bazzite/Silverblue distrobox+podman are preinstalled, so these steps
    # are skipped and no prompt appears at all.
    elevate: str = "pkexec"
    #: Which fork build to install, overriding the module pin. `None` means "the pinned
    #: one" (`fork_source.WIZARD_TARGET`), which is every caller but
    #: ``--install-ripper <commit>``.
    #:
    #: Threaded as a field rather than read from the module at each use because the two
    #: places that need it — "is the fork already installed?" and "build it" — must agree.
    #: They already diverged once: the readiness check compared against `FORK_PIN` while
    #: the build step built the test pin, so a correct install reported "not done" and was
    #: rebuilt on every run.
    fork_target: fork_source.ForkTarget | None = None
    # Ordered step ids, exposed for the dialog/tests.
    STEP_IDS: tuple[str, ...] = field(default=(), init=False)

    @property
    def _target(self) -> fork_source.ForkTarget:
        """The fork build this instance installs and checks against. One resolution."""
        return self.fork_target or fork_source.WIZARD_TARGET

    def __post_init__(self) -> None:
        # cyanrip is the sole ripping backend (KDD-18); it's installed
        # unconditionally along with flac/metaflac (for tagging, FLAC verify,
        # and the CTDB audio check).
        self.STEP_IDS = (
            "distrobox",
            "backend",
            "container",
            "tools",
            "cyanrip",
            "export",
            # Rebuild cyanrip from the pinned Platterpus fork and re-point the
            # host export at it. AFTER "export" deliberately: `distrobox-export
            # --bin` writes the same ~/.local/bin/cyanrip wrapper whichever
            # in-container path it wraps, so whichever export runs last decides
            # which binary Platterpus actually runs. Running the stock export
            # first and the fork export second means a *failed* fork build
            # leaves a working stock ripper rather than nothing — the fork step
            # is additive, and its failure is reported honestly as "you are on
            # stock cyanrip" (deps/fork_source.py explains why we build at all).
            "cyanrip_fork",
            # OPTIONAL, and deliberately LAST: the cd-paranoia cache probe
            # (KDD-29). It is NOT part of is_ready() (which gates on cyanrip +
            # flac), so even if this step fails to find a package the ripper is
            # still fully set up — the wizard reports success and only this one
            # row shows a ✗. Absent cd-paranoia just leaves the cache verdict
            # unmeasured.
            "cache_tool",
        )

    # --- State probes (each "is this step already done?") ---

    def distrobox_present(self) -> bool:
        return self.runner.which("distrobox")

    def backend_present(self) -> bool:
        return self.runner.which("podman") or self.runner.which("docker")

    def container_exists(self) -> bool:
        if not self.distrobox_present():
            return False
        rc, out = self.runner.run(["distrobox", "list"])
        if rc != 0:
            return False
        # `distrobox list` prints a table; match the name as a whole word.
        return any(self.container in line.split() for line in out.splitlines())

    def flac_in_container(self) -> bool:
        if not self.container_exists():
            return False
        rc, _ = self.runner.run(
            ["distrobox", "enter", self.container, "--", "command", "-v", "flac"]
        )
        return rc == 0

    def cyanrip_in_container(self) -> bool:
        if not self.container_exists():
            return False
        rc, _ = self.runner.run(
            ["distrobox", "enter", self.container, "--", "command", "-v", "cyanrip"]
        )
        return rc == 0

    def cyanrip_exported(self) -> bool:
        return self.runner.exists(self.cyanrip_path)

    def fork_installed(self) -> bool:
        """True when the host-exported cyanrip is the pinned Platterpus fork.

        Asks the binary that Platterpus will actually run — the host export —
        rather than checking whether a source tree or an in-container file
        exists. Those can all be present while ``~/.local/bin/cyanrip`` still
        wraps the COPR build, which is exactly the state a maintainer hit:
        every artefact of a fork install present, and stock cyanrip doing the
        ripping.

        Two conditions, both required: it identifies as the fork **and** it is
        the pinned commit. A fork build from an older pin is not the binary the
        handshake verified, so re-running the wizard must rebuild it rather
        than report the step already done.
        """
        if not self.cyanrip_exported():
            return False
        # Try every flag cyanrip has used to print its version. `-V` works on
        # 0.9.3.x; the fork's generic option parser accepts only `-v`, and
        # rejects `-V` with exit 1 — so probing with `-V` alone would report a
        # correctly-installed fork as "not done" and rebuild it on every run.
        # See `platterpus.cyanrip_cli`.
        out = ""
        for flag in VERSION_FLAGS:
            rc, out = self.runner.run([str(self.cyanrip_path), flag])
            if rc == 0:
                break
        else:
            # Every flag failed. That is not evidence of a stock build — it
            # usually means the container is down. Report "not done"; the step
            # then runs and either fixes it or fails with the real output.
            return False
        identity = identify_from_banner(out)
        # Against the WIZARD's target, not the production pin. This decides whether
        # the fork step is already satisfied, so it has to ask about the build the
        # step would install — comparing to `FORK_PIN` while the step builds the test
        # pin would report a correct install as "not done" and rebuild it every run
        # (the exact `-V` failure shape: an accurate comparison of the wrong pair).
        target_pin = self._target.pin
        return identity.kind == "fork" and target_pin in identity.build_tag.casefold()

    def flac_exported(self) -> bool:
        return self.runner.exists(self.flac_path)

    def cdparanoia_exported(self) -> bool:
        return self.runner.exists(self.cdparanoia_path)

    def _export_done(self) -> bool:
        """The export step is satisfied when every required binary is on host.

        `flac` is checked alongside cyanrip because the tools step installs it
        (it provides flac + metaflac) and `flac --test` needs it on the host to
        verify rips (cyanrip doesn't self-verify) and to decode for the CTDB
        cross-check. It was historically installed-but-not-exported, so checking
        it here makes a wizard re-run repair an existing setup.
        """
        return self.cyanrip_exported() and self.flac_exported()

    def is_ready(self) -> bool:
        """True when the whole stack is in place (ripper reachable on host)."""
        return self._export_done()

    # --- The plan ---

    def _commands_for(self, step_id: str) -> list[list[str]]:
        """The argv list a step runs when it's NOT already done."""
        if step_id == "distrobox":
            return [install_argv("distrobox", self.os_release, self.elevate)]
        if step_id == "backend":
            return [install_argv("podman", self.os_release, self.elevate)]
        if step_id == "container":
            return [
                [
                    "distrobox",
                    "create",
                    "--yes",
                    "--name",
                    self.container,
                    "--image",
                    self.image,
                ]
            ]
        if step_id == "tools":
            return [
                [
                    "distrobox",
                    "enter",
                    self.container,
                    "--",
                    "sudo",
                    "dnf",
                    "install",
                    "-y",
                    "flac",
                ]
            ]
        if step_id == "cyanrip":
            return [
                # Drop the COPR repo file. The stanza is passed as its own
                # argv element ("$1"), NOT spliced into the script string, so
                # nothing in it (e.g. $releasever) is shell-expanded.
                [
                    "distrobox",
                    "enter",
                    self.container,
                    "--",
                    "sudo",
                    "sh",
                    "-c",
                    f'printf %s "$1" > {CYANRIP_COPR_REPO_PATH}',
                    "write-copr-repo",
                    CYANRIP_COPR_REPO_CONTENT,
                ],
                [
                    "distrobox",
                    "enter",
                    self.container,
                    "--",
                    "sudo",
                    "dnf",
                    "install",
                    "-y",
                    "cyanrip",
                ],
            ]
        if step_id == "export":
            # distrobox-export is idempotent (re-exporting overwrites the
            # wrapper), so re-running already-exported binaries is harmless.
            # flac (the decoder) and metaflac (the tag editor) come from the
            # flac package installed in the tools step; both are exported so
            # `flac --test` verification, the CTDB audio check, and post-rip
            # tagging can find them on the host.
            binaries = ["/usr/bin/cyanrip", "/usr/bin/metaflac", "/usr/bin/flac"]
            return [
                [
                    "distrobox",
                    "enter",
                    self.container,
                    "--",
                    "distrobox-export",
                    "--bin",
                    b,
                ]
                for b in binaries
            ]
        if step_id == "cyanrip_fork":
            # The whole plan lives in deps/fork_source.py: install build deps,
            # clone/fetch + detach onto the verified pin, compile, install over
            # the COPR binary, re-export, then VERIFY the installed binary
            # prints the pinned fork's build tag. The verify is a command in the
            # list, so a build that produced something unexpected fails the step
            # instead of quietly leaving a mystery binary on the ripping path.
            return fork_source.fork_build_commands(self.container, self._target)
        if step_id == "cache_tool":
            # Install cd-paranoia into the (Fedora) container and export it. We
            # install by the FILE it provides (`/usr/bin/cd-paranoia`) rather than
            # a package name, so dnf resolves whichever package ships it (libcdio
            # on Fedora) without us hardcoding a name that could differ. Container
            # is always fedora-toolbox, so dnf is correct regardless of host distro.
            return [
                [
                    "distrobox",
                    "enter",
                    self.container,
                    "--",
                    "sudo",
                    "dnf",
                    "install",
                    "-y",
                    "/usr/bin/cd-paranoia",
                ],
                [
                    "distrobox",
                    "enter",
                    self.container,
                    "--",
                    "distrobox-export",
                    "--bin",
                    "/usr/bin/cd-paranoia",
                ],
            ]
        raise ValueError(f"unknown step: {step_id}")  # pragma: no cover

    def _is_done(self, step_id: str) -> bool:
        return {
            "distrobox": self.distrobox_present,
            "backend": self.backend_present,
            "container": self.container_exists,
            "tools": self.flac_in_container,
            "cyanrip": self.cyanrip_in_container,
            "export": self._export_done,
            "cyanrip_fork": self.fork_installed,
            "cache_tool": self.cdparanoia_exported,
        }[step_id]()

    _TITLES: dict[str, str] = field(
        default_factory=lambda: {
            "distrobox": "Distrobox",
            "backend": "Container backend (podman)",
            "container": f"'{DEFAULT_CONTAINER}' container",
            "tools": "flac + metaflac (in container)",
            "cyanrip": "cyanrip ripper (in container)",
            "export": "Export tools to ~/.local/bin",
            "cyanrip_fork": "Platterpus fork of cyanrip (build + export)",
            "cache_tool": "cd-paranoia cache probe (optional)",
        },
        init=False,
    )

    def run(
        self,
        progress: Callable[[StepResult], None] | None = None,
        dry_run: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[StepResult]:
        """Run the bootstrap. Returns one StepResult per step.

        Stops at the first failed step (later steps depend on it) and marks
        the remainder CANCELLED. `cancelled()` is polled between steps so the
        dialog can abort cleanly. `dry_run` reports WOULD_RUN without
        executing anything that's not already done.
        """
        results: list[StepResult] = []

        def notify(r: StepResult) -> None:
            """Push a status update to the UI without recording it as a final
            result (used for the transient RUNNING ping)."""
            if progress is not None:
                progress(r)

        def record(r: StepResult) -> None:
            results.append(r)
            notify(r)

        stop = False
        for step_id in self.STEP_IDS:
            title = self._title_for(step_id)
            if stop:
                record(StepResult(step_id, title, StepStatus.CANCELLED))
                continue
            if cancelled is not None and cancelled():
                record(StepResult(step_id, title, StepStatus.CANCELLED))
                stop = True
                continue
            # Steps whose probe enters the container can be slow (the first
            # `distrobox enter` runs distrobox's container init); ping BEFORE the
            # probe so the UI shows current activity, not a stale prior step.
            if step_id in _SLOW_PROBE_STEPS:
                notify(
                    StepResult(
                        step_id,
                        title,
                        StepStatus.RUNNING,
                        "checking the container — the first start after setup "
                        "can take a minute…",
                    )
                )
            if self._is_done(step_id):
                record(
                    StepResult(
                        step_id, title, StepStatus.DONE, self._done_detail(step_id)
                    )
                )
                continue
            commands = [c for c in self._commands_for(step_id) if c]
            if not commands:
                no_plan = (
                    "no automatic install available for this system — "
                    "install it manually and retry"
                )
                record(StepResult(step_id, title, StepStatus.FAILED, no_plan))
                diagnostics.error(
                    "setup.step_failed",
                    f"setup step “{title}” has no install plan on this system",
                    subsystem="setup",
                    detail=no_plan,
                    where=f"host_setup step {step_id!r}",
                )
                stop = True
                continue
            if dry_run:
                detail = "; ".join(" ".join(c) for c in commands)
                record(StepResult(step_id, title, StepStatus.WOULD_RUN, detail))
                continue
            # Live "currently working" ping BEFORE the (often slow) command, so
            # the UI shows what's happening instead of freezing during a multi-
            # minute image pull or dnf install.
            notify(
                StepResult(
                    step_id, title, StepStatus.RUNNING, self._running_hint(step_id)
                )
            )
            ok, detail = self._run_commands(commands)
            if ok:
                record(
                    StepResult(
                        step_id,
                        title,
                        StepStatus.RAN,
                        self._ran_detail(step_id, detail),
                    )
                )
            else:
                record(StepResult(step_id, title, StepStatus.FAILED, detail))
                # Also record it as a DIAGNOSTIC, so a setup failure is findable
                # from the one place that enumerates problems — and so it shows up
                # in the next rip report, which is where the consequence lands ("my
                # ripper is unapproved" is usually "the fork build failed earlier").
                diagnostics.error(
                    "setup.step_failed",
                    f"setup step “{title}” failed: {detail}",
                    subsystem="setup",
                    detail=detail,
                    where=f"host_setup step {step_id!r}",
                )
                stop = True
        return results

    # --- Row text ----------------------------------------------------------
    # Three small helpers rather than three inline conditionals, because they all
    # answer one question the wizard used to leave unanswered: WHICH BUILD?
    #
    # The fork row rendered exactly `✓ Platterpus fork of cyanrip (build + export)
    # — already present`, naming no commit — while the probe deciding "already
    # present" reads `self._target.pin` two lines above the comparison
    # (`_fork_installed`). Same captured-and-discarded shape as the dependency
    # dialog's truncated version, and the same rule unmet (CLAUDE.md #12: *say
    # which build*, on the surfaces a user reads). The pin is a fact we already
    # have; showing it costs nothing and it is the difference between "the wizard
    # says the fork is there" and "the wizard says commit 9048082 is there".

    def _title_for(self, step_id: str) -> str:
        """The step's title, naming the target commit where a build is chosen."""
        title = self._TITLES[step_id]
        if step_id == "cyanrip_fork":
            return f"{title} — commit {self._target.pin}"
        return title

    def _done_detail(self, step_id: str) -> str:
        """Detail for a step that was already satisfied.

        Worded to match what the probe actually checked: `_fork_installed` asks
        whether the *installed* banner's build tag CONTAINS the target pin, so the
        honest sentence is "the banner names this commit" — not "the banner is
        `<expected build tag>`", which would claim an equality nobody tested.
        """
        if step_id == "cyanrip_fork":
            return (
                f"already present — the installed banner names commit "
                f"{self._target.pin}"
            )
        return "already present"

    def _ran_detail(self, step_id: str, detail: str) -> str:
        """Detail for a step that just ran. Names what was built, not just "installed"."""
        if step_id == "cyanrip_fork" and detail == "installed":
            return f"installed — built from commit {self._target.pin}"
        return detail

    @staticmethod
    def _running_hint(step_id: str) -> str:
        """Reassuring sub-text for a step that's actively running.

        For the download-heavy steps, set an explicit time expectation: a
        real-user gave up ~4 minutes into the in-container `dnf install`
        (2026-06-26), quitting before the final export step — so the rip tool
        ended up installed in the container but not exported to the host. Saying
        "SEVERAL MINUTES" up front (not just "a few") keeps the user waiting.
        """
        if step_id == "container":
            return (
                "downloading the container image — this can take SEVERAL MINUTES "
                "the first time. The window stays usable; please don't close it."
            )
        if step_id in ("tools", "cyanrip"):
            return (
                "installing into the container — downloading packages, this can "
                "take SEVERAL MINUTES the first time. Please wait; don't close it."
            )
        return "working…"

    def _run_commands(self, commands: list[list[str]]) -> tuple[bool, str]:
        """Run each argv in order; stop at the first non-zero exit."""
        for argv in commands:
            rc, out = self.runner.run(argv)
            if rc != 0:
                return False, _last_meaningful_line(out) or f"exit {rc}"
        return True, "installed"


def cyanrip_on_host(cyanrip_path: Path = CYANRIP_BINARY_DEFAULT) -> bool:
    """True if cyanrip is reachable from the host.

    Either host-exported by the wizard (the canonical route, mirroring
    whipper) or installed natively and on PATH. Lives here — not in the UI —
    so dependency-presence logic stays inside the self-management subsystem
    (Critical Rule #6).
    """
    import shutil

    return cyanrip_path.exists() or shutil.which("cyanrip") is not None


def _last_meaningful_line(output: str) -> str:
    for line in reversed(output.strip().splitlines()):
        if line.strip():
            return line.strip()
    return ""
