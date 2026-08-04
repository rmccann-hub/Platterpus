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

from dataclasses import dataclass
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
# Round 7 lap 4 asks for `5bc654d` (fork release **r4**, version
# `0.9.4-rc1+platterpus.4`), superseding lap 2's `345241b` (r3), which superseded
# lap 1's `d5d12ec`, which superseded round 6's `ad65a24`. **Four SHAs in one open
# round**, and the fork-release number moved `.3` → `.4` because r4 adds `-dirty`
# to the build tag (our A9), the paranoia semantics in their generated contract
# (A8), and their own release gate. The base stays `0.9.4-rc1` deliberately: the
# maintainer asked for `0.9.5-rc1` and the fork declined with reasons we accept —
# it would mint a number inside upstream's namespace (exactly why `0.9.4-rc3` was
# withdrawn, which we endorsed) and assert a base that does not exist. Our
# `parse_version` returning `(0, 9, 4)` for this tree is *correct*.
#
# (Superseded note, kept for the record: lap 2 asked for `345241b` (fork release r3, version
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
NEXT_PIN_UNDER_REVIEW: Final[str] = "5bc654d"

#: The fork's **test pin** — a build designated to gather the hardware evidence a
#: close requires, which is *not* a release and never moves :data:`FORK_PIN`.
#:
#: Their round-7 lap-6 §1 named the deadlock this resolves: a round cannot close
#: without `HANDSHAKE-TESTED`; that evidence needs the reviewed build on the rig;
#: installing it is forbidden while the round is open. Every step is a rule both
#: projects hold and together they are unsatisfiable. A test pin breaks it without
#: weakening the release gate.
#: Moved twice inside round 7, and **each move retired a build we were told not to
#: install** — `f750890` (lap 6) was withdrawn in lap 7 because its `-x` cache probe
#: ran *before* the stall watchdog started, so a hang on the least-tested read path
#: in the program was silent; `d9c7124` (lap 7) was superseded hours later by the
#: beta. The pin is a variable rather than a sentence in a doc precisely because it
#: moves faster than a release cycle.
FORK_TEST_PIN: Final[str] = "9003e6f"
FORK_TEST_VERSION: Final[str] = "0.9.4-rc1+platterpus.5-beta.1"
#: Which round nominated it. Stated rather than derived from the approved round + 1:
#: a test pin belongs to *a* round, and arithmetic on the approved round is only
#: accidentally right — it breaks the first time two rounds pass without a close.
FORK_TEST_PIN_ROUND: Final[int] = 7
FORK_TEST_BUILD_TAG: Final[str] = f"{FORK_BRANCH}-g{FORK_TEST_PIN}"

#: Test pins this round has already retired. Listed **only** so a rig that built one
#: before the pin moved still receives ``--consumer`` (they all carry the flag — it
#: landed in r4, before any of them). Not an endorsement: the current test pin is
#: :data:`FORK_TEST_PIN` and the fork's lap 8 says plainly *"do not install
#: `f750890`"*. The cost of omitting them would be a silent `Consumer: not
#: identified` in a rig log, which is exactly the half-recorded pair this flag
#: exists to prevent.
SUPERSEDED_TEST_PINS: Final[tuple[str, ...]] = ("f750890", "d9c7124")

#: Build tags known to accept ``--consumer``. **Sending it to a build without it
#: is a release blocker, not a cosmetic miss**: cyanrip exits non-zero on an
#: unrecognised option, and every availability probe here reads a non-zero exit as
#: *"the tool is not installed"* — the exact `-V` failure from round 5, in the
#: opposite direction. The flag arrived in the fork's r4, so the pinned r2 build
#: (:data:`FORK_PIN`) must never be sent it.
#:
#: A set rather than a version comparison on purpose: the fork's version string is
#: deliberately upstream's plus build metadata, so it cannot be ordered, and
#: `0.9.4-rc1` is answered by stock upstream too.
BUILD_TAGS_ACCEPTING_CONSUMER_FLAG: Final[frozenset[str]] = frozenset(
    {
        f"{FORK_BRANCH}-g{NEXT_PIN_UNDER_REVIEW}",  # r4
        FORK_TEST_BUILD_TAG,  # the round-7 test pin (currently the beta)
        *(f"{FORK_BRANCH}-g{pin}" for pin in SUPERSEDED_TEST_PINS),
    }
)


#: Build tags whose published flag table lists ``-Y`` / ``--verify-log``.
#:
#: **Why this exists rather than a match on the ripper's error text** (their round-7
#: lap 12, J4): our first version of the log-verification classifier decided
#: "rejected flag" versus "rejected log" by matching cyanrip's *wording* —
#: ``Unable to parse command line argument: …``. The fork told us that string is
#: **genopt's, not theirs, and one upstream sync from changing**, and asked us to key
#: on the exit code plus the flag's presence in their published table instead. They
#: are right, and the mistake is one we have made from the other side: a matcher
#: built on a dependency's prose is a hand-maintained list of shapes, which is the
#: round-5 lesson exactly.
#:
#: Every tag here is a fork build named by a round whose P1 table contains the flag;
#: `tests/test_verify_log_support.py` derives that set from the committed inbound
#: tables and asserts agreement, so this cannot drift from the documents.
BUILD_TAGS_ACCEPTING_VERIFY_LOG: Final[frozenset[str]] = frozenset(
    {
        FORK_EXPECTED_BUILD_TAG,  # the round-6 approved pin
        f"{FORK_BRANCH}-g{NEXT_PIN_UNDER_REVIEW}",
        FORK_TEST_BUILD_TAG,
        *(f"{FORK_BRANCH}-g{pin}" for pin in SUPERSEDED_TEST_PINS),
    }
)


def accepts_verify_log(build_tag: str) -> bool | None:
    """Whether a build accepts ``--verify-log``. **Tri-state.**

    ``True`` a published flag table lists it for this build. ``None`` we do not
    know — and that is deliberately NOT ``False``: no document in this repository
    says any cyanrip *lacks* the flag, so claiming absence would be inventing
    evidence. Stock upstream lands here, including builds that very likely do
    support it (every stock 0.9.3 log in `output_reference/` carries a
    ``Log FUN512:`` footer, which is evidence about the footer and not about the
    flag — see `docs/cyanrip-handshake.md`; lap 13 asks the fork for the earliest
    build with ``-Y`` so this can return ``True`` for the stock line too).

    ``False`` is reserved for a build we affirmatively know rejects it, and nothing
    populates that today.

    Tolerant of a ``-dirty`` suffix, like :func:`accepts_consumer_flag`: a dirty
    build of a listed commit still has the flag.
    """
    tag = (build_tag or "").strip().casefold()
    if not tag:
        return None
    if tag.endswith("-dirty"):
        tag = tag[: -len("-dirty")]
    if tag in {t.casefold() for t in BUILD_TAGS_ACCEPTING_VERIFY_LOG}:
        return True
    return None


def accepts_consumer_flag(build_tag: str) -> bool:
    """Whether a build identified by ``build_tag`` will accept ``--consumer``.

    Tolerant of a ``-dirty`` suffix: a dirty build of a listed commit still has
    the flag. Deliberately **False for anything unrecognised** — an unknown build
    is not evidence the flag is safe, and the failure mode of guessing wrong is a
    ripper that reports itself missing.
    """
    tag = (build_tag or "").strip().casefold()
    if tag.endswith("-dirty"):
        tag = tag[: -len("-dirty")]
    return tag in {t.casefold() for t in BUILD_TAGS_ACCEPTING_CONSUMER_FLAG}


NEXT_VERSION_UNDER_REVIEW: Final[str] = "0.9.4-rc1+platterpus.4"

# --- Which build the wizard actually installs -------------------------------


@dataclass(frozen=True)
class ForkTarget:
    """A commit the wizard can build, with the banner a correct build must print.

    **Why this exists rather than one more constant.** The build step and the verify
    step each named a *separate* module constant — ``FORK_PIN`` and
    ``FORK_EXPECTED_BUILD_TAG`` — which happened to agree only because one is
    derived from the other. The moment a second installable build existed (a test
    pin, nominated mid-round), "build X, then assert it printed Y" became two
    independent edits, and getting one of them wrong installs a binary while
    reporting the other. Bundling the pin with the tag it must print makes the pair
    un-drift-able: there is one object, and the build and the check read the same
    field off it.
    """

    #: Short commit SHA to detach onto.
    pin: str
    #: The version string, banner parenthetical excluded.
    version: str
    #: Human-readable reason this target exists, for the log and the wizard UI.
    why: str

    @property
    def build_tag(self) -> str:
        """The banner parenthetical a correct build of :attr:`pin` prints."""
        return f"{FORK_BRANCH}-g{self.pin}"

    @property
    def banner(self) -> str:
        """The exact first line a correct build prints."""
        return f"cyanrip {self.version} ({self.build_tag})"


#: The pin a **closed** round approved. Moves only when a round closes.
PRODUCTION_TARGET: Final[ForkTarget] = ForkTarget(
    pin=FORK_PIN,
    version=FORK_EXPECTED_VERSION,
    why=f"the build handshake round 6 approved for Platterpus {FORK_EXPECTED_VERSION}",
)

#: The build nominated to gather the hardware evidence an OPEN round needs.
TEST_TARGET: Final[ForkTarget] = ForkTarget(
    pin=FORK_TEST_PIN,
    version=FORK_TEST_VERSION,
    why=(
        f"the round-{FORK_TEST_PIN_ROUND} test pin, nominated by both projects for "
        "the joint hardware session — NOT a release, and no round has approved it"
    ),
)

#: **What the setup wizard and ``--install-ripper`` build by default.**
#:
#: Pointed at :data:`TEST_TARGET` for the v0.6.4b1 beta on the maintainer's explicit
#: instruction — *"Point the test pin / wizard build target at 9003e6f"* — because
#: the beta exists for one purpose: to put both projects on the same build for the
#: joint hardware session. Round 7 is OPEN, so a rip with this installed reports
#: ``ripper_handshake_approval: unapproved``, and **that is the correct answer**, not
#: a defect: a test pin has been approved by nobody. The wizard says so at install
#: time rather than letting the rip report be the first place it surfaces.
#:
#: **Flipping back is this one line.** When round 7 closes, move :data:`FORK_PIN` to
#: the approved pin and point this at :data:`PRODUCTION_TARGET`. Deliberately a
#: separate knob from ``FORK_PIN``: the deviation policy forbids moving the pin while
#: a round is open, and conflating "what we install for a test" with "what a closed
#: round approved" is how a test build becomes the production record by accident.
WIZARD_TARGET: Final[ForkTarget] = TEST_TARGET

# --- Where it lives inside the container ------------------------------------

#: Source tree, **relative to the container user's ``$HOME``** — deliberately with
#: no ``$HOME`` in it.
#:
#: **This constant used to be the literal string ``"$HOME/.cache/platterpus/
#: cyanrip-fork"``, with a comment claiming "``$HOME`` is expanded by the shell
#: inside the container, not here". That comment was false, and it cost a release
#: cycle to find out** (real-user log, 2026-08-04, v0.6.4b2).
#:
#: The value was passed as a positional argument into ``sh -c SCRIPT``, where the
#: script did ``src="$1"``. **Parameter expansion does not recurse:** ``$HOME``
#: inside a *variable's value* is never re-expanded, so ``src`` stayed the literal
#: 8 characters ``$HOME/…`` and every path built from it was a RELATIVE path
#: beginning with a directory literally named ``$HOME``. The user's log said so in
#: plain text and nobody had ever read it::
#:
#:     Source dir: /home/rmccann/$HOME/.cache/platterpus/cyanrip-fork
#:     ninja: Entering directory `$HOME/.cache/platterpus/cyanrip-fork/build'
#:
#: **Why it went unnoticed for so long:** the clone, the configure, the compile and
#: the install *all* used the same wrong string, so they agreed with each other and
#: the build genuinely succeeded — right commit, right version, 31/31 targets. The
#: only casualty was meson's ``vcs_tag``, which could not resolve a git revision
#: from that path and fell back to upstream cyanrip's literal ``release``. So the
#: binary self-identified as ``platterpus-fork-grelease``: a build tag naming no
#: commit, which our verify step correctly refused. Consistently wrong is the
#: hardest kind of wrong to see.
#:
#: The script now expands ``$HOME`` **at the point of use** (``src="$HOME/$1"``),
#: which is what the old comment believed was happening.
FORK_SOURCE_SUBPATH: Final[str] = ".cache/platterpus/cyanrip-fork"

#: The same path as the uninstaller and the "where did the source go" message use
#: it: relative to the host home. Distrobox mounts the host home at the same path
#: inside the container, so these are one directory.
FORK_SOURCE_DIR_HOST: Final[str] = FORK_SOURCE_SUBPATH

#: Human-readable form for logs and UI **only** — never passed to a shell. Written
#: with a tilde rather than ``$HOME`` precisely so it cannot be mistaken for
#: something a shell will expand.
FORK_SOURCE_DIR_DISPLAY: Final[str] = f"~/{FORK_SOURCE_SUBPATH}"


def assert_shell_safe_subpath(subpath: str) -> str:
    """Return ``subpath`` unchanged, or raise if it could not survive a shell.

    **The argv-chokepoint guard for the `$HOME` bug** (CLAUDE.md: *validate every
    output to a dependency, enforced by code at the argv chokepoint — not merely
    stated*). A path handed to the container must be a plain relative path: no
    shell variable, no leading slash, no traversal, no metacharacter.

    ``$`` is the one that actually bit us, and it bit *silently* — the build
    succeeded into a directory named ``$HOME`` and only the build tag came out
    wrong. A path containing ``$`` is never what anyone meant, so it is an error
    rather than something to expand on the caller's behalf.

    Raises :class:`ValueError` with the offending character named, because a guard
    that fails without saying why is the class of message this whole cycle was
    about.
    """
    if not subpath or subpath.strip() != subpath:
        raise ValueError(f"fork source subpath is empty or padded: {subpath!r}")
    if subpath.startswith("/"):
        raise ValueError(
            f"fork source subpath must be relative to $HOME, got absolute: {subpath!r}"
        )
    if ".." in subpath.split("/"):
        raise ValueError(f"fork source subpath escapes its parent: {subpath!r}")
    # `$` first and by name: it is the failure this function exists for.
    if "$" in subpath:
        raise ValueError(
            f"fork source subpath contains '$' ({subpath!r}) — a shell variable in a "
            "path is never expanded when it arrives as an argument, which is the "
            "v0.6.4b2 `$HOME` defect. Pass a plain relative path."
        )
    forbidden = set("`\"'\\;|&<>()*?[]{}!\n\r\t")
    bad = sorted(forbidden.intersection(subpath))
    if bad:
        raise ValueError(
            f"fork source subpath contains shell metacharacter(s) {bad}: {subpath!r}"
        )
    return subpath


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
# $1 is a path RELATIVE TO $HOME, and $HOME is expanded HERE — at the point of
# use, inside the container's own shell. Passing a pre-baked "$HOME/..." string
# does NOT work: parameter expansion does not recurse, so it stayed literal and
# every path became a relative one under a directory named '$HOME'. See
# FORK_SOURCE_SUBPATH for the full post-mortem.
src="$HOME/$1"
url="$2"
branch="$3"
pin="$4"

# --- Say where we are before doing anything ---------------------------------
# These four lines are the ones that would have ended the v0.6.4b2 hunt in
# seconds. The failure was entirely visible in a path and nobody printed it.
echo "platterpus: HOME=$HOME"
echo "platterpus: cwd=$(pwd)"
echo "platterpus: source tree=$src"
echo "platterpus: requested pin=$pin branch=$branch"
case "$src" in
  /*) : ;;
  *) echo "platterpus: FATAL source tree is not an absolute path: $src" >&2
     exit 1 ;;
esac
case "$src" in
  *'$'*) echo "platterpus: FATAL source tree contains an unexpanded variable:" \\
              "$src — this is the v0.6.4b2 defect" >&2
         exit 1 ;;
esac

mkdir -p "$(dirname "$src")"
if [ -d "$src/.git" ]; then
  echo "platterpus: reusing existing clone, fetching $branch"
  git -C "$src" remote set-url origin "$url"
  git -C "$src" fetch --force origin "$branch"
else
  echo "platterpus: no clone at $src — cloning $branch"
  git clone --branch "$branch" "$url" "$src"
fi
# Detach onto the verified commit. `--force` discards a half-finished previous
# attempt; the tree is a build cache we own, never the user's work.
git -C "$src" checkout --force --detach "$pin"

# --- Prove the tree is what we asked for, before building it ----------------
# A build tag names a commit; it does not name what was built (CLAUDE.md rule
# 12). So state the commit we actually landed on, and whether the tree is dirty
# — a dirty tree bakes a tag for a different tree, silently.
echo "platterpus: HEAD=$(git -C "$src" rev-parse HEAD)"
echo "platterpus: HEAD short=$(git -C "$src" rev-parse --short HEAD)"
echo "platterpus: describe=$(git -C "$src" describe --always --dirty 2>&1 || true)"
dirt="$(git -C "$src" status --porcelain 2>/dev/null || true)"
if [ -n "$dirt" ]; then
  echo "platterpus: WARNING the source tree is DIRTY — the build tag will not" \\
       "describe what is built:" >&2
  printf '%s\\n' "$dirt" >&2
else
  echo "platterpus: tree is clean"
fi
# meson's vcs_tag resolves the build tag by running git in the source root. If
# THAT cannot work, the tag silently becomes upstream's `release` fallback — the
# v0.6.4b2 symptom — so probe it here, where a failure is attributable.
if git -C "$src" rev-parse --short HEAD >/dev/null 2>&1; then
  echo "platterpus: git is usable in the source root (vcs_tag should resolve)"
else
  echo "platterpus: WARNING git is NOT usable in the source root — meson's" \\
       "vcs_tag will fall back and the build tag will name no commit" >&2
fi

# `--wipe` reconfigures an existing build dir (and fails if there isn't one),
# so branch on it rather than deleting anything.
if [ -d "$src/build" ]; then
  echo "platterpus: reconfiguring existing build dir"
  meson setup --wipe "$src/build" "$src"
else
  echo "platterpus: configuring a fresh build dir"
  meson setup "$src/build" "$src"
fi
ninja -C "$src/build"

# --- Read the banner off the thing we just built ----------------------------
# The build step's own self-check. Previously the first time anyone learned the
# banner was wrong was three commands later, in the verify step, which reported
# only what it EXPECTED. Reading it here attributes a wrong tag to the build
# that produced it.
built="$src/build/src/cyanrip"
if [ -x "$built" ]; then
  echo "platterpus: built binary=$built"
  for _f in -V --version; do
    if _out="$("$built" "$_f" 2>/dev/null)"; then
      echo "platterpus: built banner=$(printf '%s\\n' "$_out" | head -n 1)"
      break
    fi
  done
else
  echo "platterpus: FATAL ninja reported success but $built is not executable" >&2
  exit 1
fi
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
    '  *"$2"*) echo "platterpus: installed binary identifies as $2" ; exit 0 ;;\n'
    "esac\n"
    # NAME WHAT WE GOT, NOT ONLY WHAT WE WANTED.
    #
    # This said only "does not identify as the pinned fork build ($2)". The
    # observed banner was printed one line ABOVE on stdout — and
    # `HostSetup._run_commands` keeps only the LAST line for the UI, so the one
    # fact that mattered was discarded at exactly the moment it mattered. The real
    # answer was `platterpus-fork-grelease`: not a wrong commit, a tag naming NO
    # commit, which points at meson's vcs_tag rather than at the checkout. Two
    # sessions were spent guessing at what one string would have settled.
    #
    # `grelease` gets its own sentence, because it has a specific cause and a
    # user should not have to know that to act on it.
    # ORDER MATTERS: `HostSetup._run_commands` shows the UI only the LAST
    # meaningful line, so the line carrying BOTH banners has to be last. The
    # `grelease` explanation goes first — it is context, and the log keeps every
    # line regardless now.
    'case "$banner" in\n'
    "  *-grelease*|*-gunknown*)\n"
    '    echo "note: that build tag names no commit at all (meson vcs_tag fell'
    " back to its literal default), so the binary cannot prove which source it"
    ' was built from" >&2 ;;\n'
    "esac\n"
    'echo "installed cyanrip reports \\"$banner\\" but this Platterpus expects'
    ' build tag \\"$2\\"" >&2\n'
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


def build_command(container: str, target: ForkTarget | None = None) -> list[str]:
    """Clone-or-fetch, detach onto the pin, configure and compile.

    The four values the script needs are appended as positional arguments.
    ``sh -c SCRIPT NAME ARG1 …`` assigns ``NAME`` to ``$0``, so the first real
    argument must be a throwaway label — ``"build-cyanrip-fork"`` here, which
    also makes the command self-describing in the log.

    ``target`` defaults to :data:`WIZARD_TARGET` — resolved at *call* time, not
    bound as a default argument value, so a caller that overrides it in a test
    cannot be silently answered with the module's own choice. (The fork hit exactly
    this in their gate: a ``directory=HANDSHAKE_DIR`` default bound at definition
    time made a test point at a throwaway record and measure the real one.)
    """
    chosen = target if target is not None else WIZARD_TARGET
    return _enter(
        container,
        "sh",
        "-c",
        _BUILD_SCRIPT,
        "build-cyanrip-fork",
        assert_shell_safe_subpath(FORK_SOURCE_SUBPATH),
        FORK_REPO_URL,
        FORK_BRANCH,
        chosen.pin,
    )


#: Copies the built binary into place, through a shell so ``$HOME`` resolves the
#: SAME WAY the build script resolves it.
#:
#: **This has to go through ``sh -c`` now, and that is the point.** It used to be a
#: bare ``sudo install`` with the path spliced in Python — and it "worked" only
#: because the spliced string was the same wrong literal the build used, so both
#: agreed on a directory named ``$HOME``. Fixing the build alone would have left
#: this one copying from a path that no longer exists. Two expressions of one path
#: is the drift; one expansion rule, applied in both places, is the fix.
_INSTALL_SCRIPT: Final[str] = """\
set -eu
src="$HOME/$1"
built="$src/build/src/cyanrip"
if [ ! -x "$built" ]; then
  echo "platterpus: FATAL nothing to install — $built is missing or not executable" >&2
  echo "platterpus: (the build step is what creates it; did it run?)" >&2
  exit 1
fi
echo "platterpus: installing $built -> $2"
sudo install -Dm0755 "$built" "$2"
echo "platterpus: installed $(ls -l "$2")"
"""


def install_command(container: str) -> list[str]:
    """Copy the built binary over the COPR one, on the container's PATH."""
    return _enter(
        container,
        "sh",
        "-c",
        _INSTALL_SCRIPT,
        "install-cyanrip-fork",
        assert_shell_safe_subpath(FORK_SOURCE_SUBPATH),
        FORK_INSTALL_PATH,
    )


def export_command(container: str) -> list[str]:
    """Re-point the host export at the fork.

    ``distrobox-export --bin`` writes ``~/.local/bin/cyanrip`` regardless of
    which in-container path it wraps, so exporting the fork *after* the generic
    export step is what makes the fork the binary Platterpus actually runs.
    """
    return _enter(container, "distrobox-export", "--bin", FORK_INSTALL_PATH)


def verify_command(container: str, target: ForkTarget | None = None) -> list[str]:
    """Assert the installed binary prints the built target's build tag.

    Reads the tag off the **same** :class:`ForkTarget` the build used. Previously
    this named ``FORK_EXPECTED_BUILD_TAG`` while the build named ``FORK_PIN``; with
    one installable build those always agreed, and with two they would not have —
    the verify would have demanded the production tag from a test-pin build and
    failed a correct install.
    """
    chosen = target if target is not None else WIZARD_TARGET
    return _enter(
        container,
        "sh",
        "-c",
        _VERIFY_SCRIPT,
        "verify-cyanrip-fork",
        FORK_INSTALL_PATH,
        chosen.build_tag,
    )


def fork_build_commands(
    container: str, target: ForkTarget | None = None
) -> list[list[str]]:
    """The whole step, in order: deps → build → install → export → verify.

    Verify is deliberately last rather than first: the point is to check what we
    just installed, and a check that runs before the install can only ever
    confirm the previous state.

    One ``target`` is resolved here and passed to *both* the build and the verify,
    so the two cannot be given different builds by a caller that overrides only one.
    """
    chosen = target if target is not None else WIZARD_TARGET
    return [
        build_deps_command(container),
        build_command(container, chosen),
        install_command(container),
        export_command(container),
        verify_command(container, chosen),
    ]
