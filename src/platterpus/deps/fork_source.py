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

from platterpus.cyanrip_cli import VERSION_BANNER_SNIPPET

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

#: The handshake-verified commit (round 6, GO, ``docs/handshake/verified/
#: round-6.md``; the fork calls it release **r2**). Short form
#: because that is what ``git rev-parse --short HEAD`` bakes into the banner, and
#: matching the two by eye is part of verifying an install.
#:
#: **A commit, never a tag, and that is not a style preference.** The fork ships
#: annotated release tags, but its environment's git proxy refuses tag pushes
#: (HTTP 403), so ``git ls-remote --tags origin`` returns nothing — no release tag
#: has ever reached the remote. A wizard that cloned a tag would fail on a ref
#: that does not exist. They told us rather than letting our pin-agreement test
#: discover it, which is the handshake working.
#:
#: **Not** ``ad65a24``, which round 6 asked for and round 6b withdrew hours later:
#: at that commit, ripping a BIN/CUE, NRG or cdrdao *disc image* at any paranoia
#: level above 0 returned one correct sector followed by silence — 99.7% of
#: samples zeroed, reported as ``Ripping errors: 0``. The defect is inherited from
#: upstream (``c431d58`` set paranoia's cachemodel, which doubles as its ``c_block``
#: read-chunk size, to 1 sector for image drivers), so every earlier fork build and
#: stock upstream carry it equally. **Real drives were never affected** — the
#: override applies only to the three image drivers — so no disc ripped on the rig
#: is in question. The fix — cachemodel 16 — landed at ``22de22f``.
#:
#: **``2f950c8`` (r2) is also superseded**: round 7 §0 retracted r2's read-liveness
#: heartbeat, which never fired because it was emitted from libcdio-paranoia's
#: status callback — silent in exactly the case it existed for, since a drive
#: grinding on a bad sector blocks inside a single SCSI command and paranoia never
#: calls back. r3 moves it to its own thread. We never consumed that heartbeat (our
#: own stall detection is independent and demonstrably fired on the same stalls), so
#: this is a correctness improvement for them rather than a fix we needed.
#:
#: **The pin decides the banner, which is the release identity.** ``vcs_tag`` bakes
#: in ``git rev-parse --short HEAD``, and no tag from this fork has ever reached the
#: remote (the git proxy refuses tag pushes; they re-probed it in round 7). So the
#: commit SHA is the only resolvable release identifier, and the pin is an
#: *identification* choice as much as a code one.
FORK_PIN: Final[str] = "2f950c8"

#: What the built binary must print. cyanrip's banner is
#: ``cyanrip <version> (<PROJECT_FORK_ID>-g<short sha>)`` (fork
#: ``src/cyanrip_log.c``), and ``meson``'s ``vcs_tag`` fills the sha from
#: ``git rev-parse --short HEAD`` in the source tree — so a correct build of
#: :data:`FORK_PIN` prints exactly this. Verified as the *last* command of the
#: build step: an install that does not identify as the fork is a failed step,
#: not a quiet downgrade.
FORK_EXPECTED_BUILD_TAG: Final[str] = f"{FORK_BRANCH}-g{FORK_PIN}"

#: The full version string the pinned build prints, banner parenthetical excluded.
#:
#: **Recorded because the fork's version no longer tracks upstream's, and because
#: our test doubles were about to lie about it.** Through r1 and r2 the fork carried
#: upstream's string byte for byte (``0.9.4-rc1``) — which we called exactly right,
#: since it means a version number can never answer *"is this the fork?"*; only
#: ``PROJECT_FORK_ID`` can. That property still holds. What it also meant is that r1
#: and r2 were indistinguishable by version, so r3 appends SemVer **build metadata**:
#: ``+platterpus.N``. Upstream will never mint one, so it cannot collide — unlike
#: their withdrawn first attempt (``0.9.4-rc3``), which minted an identifier inside
#: upstream's namespace and was pulled before release for that reason.
#:
#: **Never match on the bare upstream number.** ``0.9.4-rc1`` is answered by stock
#: upstream too. Match ``platterpus-fork`` (the build tag) or the ``+platterpus.``
#: substring; never infer the fork release number from the RC number.
#:
#: This constant exists so the *fakes* cannot drift from the product: several tests
#: simulate the installed fork's ``--version`` output, and every one of them derived
#: the version from a hardcoded ``0.9.4-rc1`` literal. Those tests would have gone on
#: passing against r3 while asserting a string the real binary no longer prints — a
#: harness staler than the product, which is the failure mode CLAUDE.md's "what does
#: my stand-in do that the real thing does not" question exists to catch.
FORK_EXPECTED_VERSION: Final[str] = "0.9.4-rc1"

#: The exact first line the pinned build prints, assembled from the two above.
FORK_EXPECTED_BANNER: Final[str] = (
    f"cyanrip {FORK_EXPECTED_VERSION} ({FORK_EXPECTED_BUILD_TAG})"
)

# --- The NEXT pin, recorded but deliberately not wired in -------------------
#
# Round 7 lap 2 asks for `345241b` (fork release r3, version
# `0.9.4-rc1+platterpus.3`) — superseding lap 1's `d5d12ec`, which superseded
# round 6's `ad65a24`. Three SHAs for one unreleased version, and the version
# string is right to be unchanged: `+platterpus.N` increments when a *release*
# happens, not when a commit lands, and this open round is what stops the release.
# Both new commits came out of our own lap-1 file (their release gate, and the
# `Duration:` sign correction), which is the handshake working.
# **The pin has NOT moved to it, on purpose.** Two independent reasons, either
# sufficient:
#
#   * CLAUDE.md's deviation policy forbids switching the container to a new
#     cyanrip pin while a handshake round is open, and round 7 is open.
#   * Their own round-7 §15 asks us to hold: *"We are not releasing r3 while this
#     round is open, and we ask you to hold too. We expect this to take more than
#     one lap."* r3 carries a retraction, a corrected measurement affecting stored
#     records, and a version scheme changed twice.
#
# Recorded here rather than only in the round file so the values are in the code's
# reach when the round closes, and so `test_fork_source` keeps asserting the LIVE
# pin against the newest *closed* round — the check that caught an attempt to move
# it early.
# NOTE on their branch tip vs the pin: `345241b` is the last commit that touches
# `src/`, so it is what the version banner resolves to and what a build must use.
# Their branch tip adds only `tools/release-gate.py` + its test — `meson test`
# reports 20/20 at the pin and 21/21 at the tip, and the executable is identical.
NEXT_PIN_UNDER_REVIEW: Final[str] = "345241b"
NEXT_VERSION_UNDER_REVIEW: Final[str] = "0.9.4-rc1+platterpus.3"

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
_VERIFY_SCRIPT: Final[str] = (
    "set -eu\n"
    # Which flag prints the version depends on the build: `-V` on 0.9.3.x, `-v`
    # from 0.9.4-rc1 on. Verifying a fork build with `-V` alone made a perfect
    # install report FAILED. The snippet is generated from the same
    # VERSION_FLAGS tuple the Python probes use, so the shell and the Python
    # cannot disagree about which flags exist or in what order to try them.
    + VERSION_BANNER_SNIPPET
    + "\n"
    "printf '%s\\n' \"$banner\"\n"
    'case "$banner" in\n'
    '  *"$2"*) exit 0 ;;\n'
    "esac\n"
    'echo "installed cyanrip does not identify as the pinned fork build ($2)" >&2\n'
    "exit 1\n"
)


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
