"""Where the Platterpus fork of cyanrip comes from, and how to build it.

Platterpus depends on a *forked* cyanrip. Everything the archival log claims
beyond stock cyanrip's output — per-track pre-gap length and provenance, sample
peak, per-track extraction speed and elapsed time, the ``Rip completed:`` footer,
the ``Invoked as:`` line — comes from that fork, and the whole
``docs/cyanrip-handshake.md`` process exists to keep the two halves in step. So
"which cyanrip is installed" is not a preference; it is the difference between a
log that can reach EAC parity and one that cannot.

Until this module existed the fork was installed **by hand, from a terminal**,
which broke the project's zero-terminal bar (KDD-17) in the one place it matters
most, and — as the maintainer discovered by reading the dependency dialog — left
no in-app path to a fork install at all. The one-time setup wizard installs the
stock COPR package first (fast, GPG-signed, and it drags in every runtime
library the fork also needs), then this step builds the fork over it.

**Why build from source rather than package it.** The fork is a moving pin
tracked by a bidirectional handshake, not a release. Packaging it would add a
second release process and a second thing to keep in step with the handshake;
building the pinned commit means the binary can never be newer or older than the
commit both sides verified.

**Why the stock package stays.** If the source build fails — no network, a
missing devel package, a compiler change — the user is left with a *working*
ripper rather than none. The fork step is additive and its failure is reported
as "you are on stock cyanrip", which is exactly true and exactly recoverable.

Everything here is data and pure argv construction: no subprocess, no Qt. The
step engine in :mod:`platterpus.deps.host_setup` runs what this module returns,
so the plan can be asserted in tests without a container.
"""

from __future__ import annotations

from typing import Final

# --- Provenance: the one place the pin is written ---------------------------
#
# Changing the pin is a handshake event, not an edit: per CLAUDE.md's deviation
# policy, switching the container to a new cyanrip pin while a handshake round
# is open requires asking first. A test asserts this value matches the pin named
# in the newest closed round under `docs/handshake/`, so the code and the record
# cannot drift apart silently.

#: The fork's clone URL. HTTPS rather than SSH: the wizard runs unattended and
#: must not depend on the user having a key agent.
FORK_REPO_URL: Final[str] = "https://github.com/rmccann-hub/cyanrip.git"

#: The branch the fork's work lands on. Cloned by name, then detached onto the
#: pin — the branch alone is a moving target and would silently install
#: unverified work.
FORK_BRANCH: Final[str] = "platterpus-fork"

#: The handshake-verified commit (round 4, GO, ``docs/handshake/verified/
#: round-4.md``). Short form because that is what ``git rev-parse --short HEAD``
#: bakes into the banner, and matching the two by eye is part of verifying an
#: install.
FORK_PIN: Final[str] = "a04a94b"

#: What the built binary must print. cyanrip's banner is
#: ``cyanrip <version> (<PROJECT_FORK_ID>-g<short sha>)`` (fork
#: ``src/cyanrip_log.c``), and ``meson``'s ``vcs_tag`` fills the sha from
#: ``git rev-parse --short HEAD`` in the source tree — so a correct build of
#: :data:`FORK_PIN` prints exactly this. Verified as the *last* command of the
#: build step: an install that does not identify as the fork is a failed step,
#: not a quiet downgrade.
FORK_EXPECTED_BUILD_TAG: Final[str] = f"{FORK_BRANCH}-g{FORK_PIN}"

# --- Where it lives inside the container ------------------------------------

#: Source tree. Under the user's cache dir, which Distrobox shares with the
#: host, so a re-run fetches instead of re-cloning and the uninstaller can find
#: it. ``$HOME`` is expanded by the shell inside the container, not here.
FORK_SOURCE_DIR: Final[str] = "$HOME/.cache/platterpus/cyanrip-fork"

#: Same path with ``$HOME`` resolved on the host — for the uninstaller and for
#: telling the user where the source went. Distrobox mounts the host home at the
#: same path inside the container, so these are the same directory.
FORK_SOURCE_DIR_HOST: Final[str] = ".cache/platterpus/cyanrip-fork"

#: Install target. ``/usr/local/bin`` precedes ``/usr/bin`` on Fedora's default
#: PATH, so the fork wins over the COPR package for anything inside the
#: container too — not only for the host export.
FORK_INSTALL_PATH: Final[str] = "/usr/local/bin/cyanrip"

# --- Build dependencies -----------------------------------------------------
#
# READ OFF THE FORK'S OWN `src/meson.build` AT THE PIN, not remembered: every
# `dependency('x')` line there appears here as `pkgconfig(x)`, plus the build
# tools. Requesting the pkg-config *virtual provide* rather than a package name
# is the same trick the cd-paranoia step uses — dnf resolves whichever package
# ships it, so this keeps working whether the container has Fedora's
# `ffmpeg-free-devel` or RPM Fusion's `ffmpeg-devel`, which conflict with each
# other and cannot both be named.
FORK_BUILD_PACKAGES: Final[tuple[str, ...]] = (
    # Toolchain
    "git",
    "meson",
    "ninja-build",
    "gcc",
    # ffmpeg libs (src/meson.build: libavcodec/libavformat/libswresample/
    # libavfilter/libavutil)
    "pkgconfig(libavcodec)",
    "pkgconfig(libavformat)",
    "pkgconfig(libswresample)",
    "pkgconfig(libavfilter)",
    "pkgconfig(libavutil)",
    # Disc reading + metadata + network
    "pkgconfig(libcdio)",
    "pkgconfig(libcdio_paranoia)",
    "pkgconfig(libmusicbrainz5)",
    "pkgconfig(libcurl)",
)

# --- The build script -------------------------------------------------------
#
# One `sh -c` because `cd`/`git`/`meson`/`ninja` must share a working tree, and
# the step engine runs one argv per command with no shell state between them.
#
# Every value it needs arrives as a POSITIONAL ARGUMENT ("$1"…), never spliced
# into this string — the same discipline the COPR repo stanza uses, so nothing
# in a URL, a branch name or a path can be re-interpreted by the shell.
#
# `set -eu` so a failed clone cannot fall through to "build whatever is already
# in that directory" — which would install a stale binary while reporting
# success, the exact class of silent-wrong-answer this project keeps hunting.
_BUILD_SCRIPT: Final[str] = """\
set -eu
src="$1"
url="$2"
branch="$3"
pin="$4"
mkdir -p "$(dirname "$src")"
if [ -d "$src/.git" ]; then
  git -C "$src" remote set-url origin "$url"
  git -C "$src" fetch --force origin "$branch"
else
  git clone --branch "$branch" "$url" "$src"
fi
# Detach onto the verified commit. `--force` discards a half-finished previous
# attempt; the tree is a build cache we own, never the user's work.
git -C "$src" checkout --force --detach "$pin"
# `--wipe` reconfigures an existing build dir (and fails if there isn't one),
# so branch on it rather than deleting anything.
if [ -d "$src/build" ]; then
  meson setup --wipe "$src/build" "$src"
else
  meson setup "$src/build" "$src"
fi
ninja -C "$src/build"
"""

#: Verifies the freshly installed binary is the fork *and* the pinned build,
#: by reading its own banner. Runs as the last command of the step, so a build
#: that produced something unexpected fails the step loudly instead of leaving
#: a mystery binary on the ripping path.
_VERIFY_SCRIPT: Final[str] = """\
set -eu
banner="$("$1" -V 2>&1 | head -n 1)"
printf '%s\\n' "$banner"
case "$banner" in
  *"$2"*) exit 0 ;;
esac
echo "installed cyanrip does not identify as the pinned fork build ($2)" >&2
exit 1
"""


def _enter(container: str, *argv: str) -> list[str]:
    """``distrobox enter <container> -- <argv>``.

    Critical rule #3: the GUI never talks to podman directly, and the ripper is
    only ever reached through the host export. Container *setup* is the one
    place we drive Distrobox, and it goes through this single helper so every
    command in the plan has the same shape.
    """
    return ["distrobox", "enter", container, "--", *argv]


def build_deps_command(container: str) -> list[str]:
    """Install the toolchain and headers the fork's meson build requires."""
    return _enter(container, "sudo", "dnf", "install", "-y", *FORK_BUILD_PACKAGES)


def build_command(container: str) -> list[str]:
    """Clone-or-fetch, detach onto the pin, configure and compile.

    The four values the script needs are appended as positional arguments.
    ``sh -c SCRIPT NAME ARG1 …`` assigns ``NAME`` to ``$0``, so the first real
    argument must be a throwaway label — ``"build-cyanrip-fork"`` here, which
    also makes the command self-describing in the log.
    """
    return _enter(
        container,
        "sh",
        "-c",
        _BUILD_SCRIPT,
        "build-cyanrip-fork",
        FORK_SOURCE_DIR,
        FORK_REPO_URL,
        FORK_BRANCH,
        FORK_PIN,
    )


def install_command(container: str) -> list[str]:
    """Copy the built binary over the COPR one, on the container's PATH."""
    return _enter(
        container,
        "sudo",
        "install",
        "-Dm0755",
        f"{FORK_SOURCE_DIR}/build/src/cyanrip",
        FORK_INSTALL_PATH,
    )


def export_command(container: str) -> list[str]:
    """Re-point the host export at the fork.

    ``distrobox-export --bin`` writes ``~/.local/bin/cyanrip`` regardless of
    which in-container path it wraps, so exporting the fork *after* the generic
    export step is what makes the fork the binary Platterpus actually runs.
    """
    return _enter(container, "distrobox-export", "--bin", FORK_INSTALL_PATH)


def verify_command(container: str) -> list[str]:
    """Assert the installed binary prints the pinned fork's build tag."""
    return _enter(
        container,
        "sh",
        "-c",
        _VERIFY_SCRIPT,
        "verify-cyanrip-fork",
        FORK_INSTALL_PATH,
        FORK_EXPECTED_BUILD_TAG,
    )


def fork_build_commands(container: str) -> list[list[str]]:
    """The whole step, in order: deps → build → install → export → verify.

    Verify is deliberately last rather than first: the point is to check what we
    just installed, and a check that runs before the install can only ever
    confirm the previous state.
    """
    return [
        build_deps_command(container),
        build_command(container),
        install_command(container),
        export_command(container),
        verify_command(container),
    ]
