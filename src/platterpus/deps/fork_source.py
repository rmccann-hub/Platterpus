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
#: **Moved to the round-7 release on 2026-08-07, when round 7 closed** (both
#: verdicts GO, laps 38/40). It names the *released* commit `422d12a`, not the
#: approved pin `104f6d4`, and that distinction is deliberate and recorded in our
#: lap 40 §A rather than left in a constant:
#:
#: * `104f6d4` is what the round approved, and `HANDSHAKE-PIN` still says so on
#:   both sides.
#: * `422d12a` is the release built from that code — `git diff 104f6d4 422d12a --
#:   src/` is empty on their side, and we verified the consequence rather than the
#:   claim: all twelve `EAC CRC32`/`Accurip` lines of their regenerated golden
#:   reference are byte-identical to the `104f6d4` one we hold.
#:
#: **Why not simply install the approved pin.** cyanrip bakes its handshake state
#: in at build time. `104f6d4` was built while round 7 was open, so every log it
#: writes says `round 7 lap 33 OPEN, verdict HOLD -- NOT a released build` — we
#: have one, from the J1 rip. That was true when it compiled and is false now.
#: Shipping a stable Platterpus whose every archival record carries that sentence
#: is the worse of the two errors.
FORK_PIN: Final[str] = "422d12a"

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
#: Round 7's release drops the `-beta.N` suffix: `0.9.4-rc1+platterpus.5`.
FORK_EXPECTED_VERSION: Final[str] = "0.9.4-rc1+platterpus.5"

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
#: Moved a third time in lap 21 — `9003e6f` → `c5fb909`, `beta.1` → `beta.2`. The fork's
#: own words: *"INSTALL `c5fb909`, NOT `9003e6f`"*. Six commits, one of them a fix to a
#: log value we parse (track 1's pre-gap counted the 2-second lead-in twice).
#: Moved a fifth time in lap 25's second revision — `f5e11ba` → `9048082`,
#: `beta.4` → `beta.5`. The fork's own words: *"`beta.4` (`f5e11ba`) is superseded and
#: should not be installed."* One change, and it is the cue fix for a defect our rip found.
#:
#: **Pin the ARTIFACTS commit, not the version bump.** `c10cc94` is where `meson.build`
#: says `beta.5`; `9048082` is where the regenerated `PROVIDER-CONTRACT.md` lands, and it
#: is the same ripping code (`git diff c10cc94..9048082 -- src/ meson.build` is empty).
#: Their contract generator reads the *built binary* and refuses on a dirty tree, so a
#: contract can never be regenerated in the commit that bumps the version — six of their
#: seven bumps shipped a contract describing the previous release.
#: Moved a sixth time in round 7 lap 32/33 — `9048082` → `4a35604`, `beta.5` → `beta.7`.
#: **`beta.6` (`dc21958`) never reached this constant**, so no user could install it
#: through the app; it was declared as a test pin in lap 30 and withdrawn in lap 32
#: before the pin moved. That is the `HANDSHAKE-TEST-PIN` mechanism working: naming a
#: build to test cost nobody an install.
#:
#: **Why beta.6 was withdrawn, and why beta.7 is not optional.** Our lap 31 reported
#: that cyanrip's `-t` parse does `strtol()` then `end += 1` without checking a `=` is
#: there, reading one past the NUL. The fork ran it: `append_missing_keys()` then
#: `strlen`s and parses what it read, and argv is contiguous with the environment
#: block — so an environment variable landed **in a FLAC tag, in the log and in the
#: cue, at exit 0 with nothing printed** (their lap 32 §B). Generalising the report
#: into a malformed-shape probe axis found four more crashes (`-c /`, `-c //`, `-p =`,
#: `-p ==`, all NULL-deref in `strtol`). Fixed in `3923dee` and `58f5151`.
#:
#: Platterpus can never emit a bare `-t N` — the builder only adds `-t` when a tag
#: exists, and `assert_meta_args_are_parseable` refuses the shape at the chokepoint —
#: so this is not a defence of the app. It is about the **artifact**: a rip made on a
#: build with a known path from adjacent memory into the archival record is evidence
#: we would then have to argue about, and the rip exists to settle things.
#: **Moved to `104f6d4` / `beta.8`. The pin moved three times in one hour** —
#: `4a35604` → `92ceeed` → `104f6d4` — and the first two arrived OUT OF BAND, reported
#: by the maintainer rather than by a lap. `104f6d4` is their lap-33 commit ("gate the
#: golden reference's version, and pin beta.8"); `92ceeed` is its ancestor. Recorded
#: rather than smoothed over: our lap 34 declares it and asks them to confirm.
#: The maintainer reported it directly (2026-08-06); no lap declares it. Our lap 33 and
#: their lap 32 both name `4a35604` / `beta.7`, so the record and the rig disagree until
#: a lap 34 closes the gap. Recorded here rather than smoothed over.
#:
#: **Why taking it is safe, verified rather than assumed.** beta.8 changes no ripping
#: code at all:
#:
#:     git diff 4a35604..104f6d4 -- 'src/*.c' 'src/*.h'   # empty
#:
#: and their own `HANDSHAKE-SOURCE-ANCHOR` is unchanged at `8290677bea1a834d` across
#: both builds — which is independent confirmation, because that anchor is *defined* as
#: a hash over exactly those files. The diff is `.gitattributes`, a `Changelog.md`
#: entry, `src/archive-version.txt`, meson version detection for tarball builds, their
#: test harness, and a one-line version string in `PROVIDER-CONTRACT.md`. Nothing we
#: parse can have moved.
#:
#: **Why we must pin it anyway even though the code is identical.** Every rip verifies
#: its own ripper against the approved build (`handshake_approval.py`, report schema
#: v15). A beta.8 banner against a `4a35604` expectation would report an unapproved
#: binary on a rip that is behaviourally the declared one — a false alarm on the very
#: artifact the round is waiting for.
FORK_TEST_PIN: Final[str] = "104f6d4"
FORK_TEST_VERSION: Final[str] = "0.9.4-rc1+platterpus.5-beta.8"
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
#:
#: **`9003e6f` joined the list in lap 21**, and it is the one a rig is most likely to
#: still have built: it was the pin for thirteen laps and it is what the 2026-08-04 rig
#: session actually ran, so every artifact we hold from real hardware came from it.
SUPERSEDED_TEST_PINS: Final[tuple[str, ...]] = (
    "f750890",
    "d9c7124",
    "9003e6f",
    # Retired in lap 25. `c5fb909` is the build the 2026-08-04 rig session actually ran,
    # so it stays listed for the same reason `9003e6f` does: a rig that has not rebuilt
    # still gets `--consumer`. Its successor `e61e75a` is **observably identical** to it —
    # the fork measured log body (275 lines), cue, decoded PCM and the `-j` record side by
    # side (their lap 24 §C2) — so the rig evidence transfers; the one code change is a
    # `dev_path` leak on argument-validation refusals, which made their sanitizers
    # unusable and touches no line we parse.
    "c5fb909",
    # Retired in lap 26, one lap after it arrived — MAINTAINER DIRECTIVE, 2026-08-05:
    # *"take the newest beta and release based on that, i want to test cutting edge. with
    # our logs we should see failure, and that in itself is a test"* — for both projects.
    #
    # This reverses what our own lap 26 §M recommended (promote `e61e75a`, the
    # conservative build). The maintainer's reasoning is better than ours was: their §A2
    # denominator change **cannot be verified anywhere but the rig**, so a session spent
    # on the conservative build leaves the one unverifiable change unverified, and the
    # next session has to happen anyway. Our own A2 consumer fix ships in the same
    # release, so both halves of that change land together rather than a build arriving
    # ahead of the code that can describe it.
    "e61e75a",
    # Retired in lap 25's SECOND revision, 2026-08-05. `f5e11ba` is the build two rig
    # sessions actually ran (b7 and b8), so it stays listed for the usual reason — a rig
    # that has not rebuilt still gets `--consumer`.
    #
    # It is retired for a defect OUR OWN RIP FOUND, which is the first time that has been
    # the reason: on tracks 3, 6, 11 and 12 the log says `Pregap length: 0 frames` and the
    # cue writes an `INDEX 00` anyway, one frame past the end of the previous `FILE`.
    # Present in all three cue sheets on record, so it is as old as their sub-channel
    # pre-gap search rather than a `beta.4` regression.
    "f5e11ba",
    # Retired in lap 33 when the pin moved to `4a35604` (beta.7). `9048082` is the
    # build the 2026-08-05 rig session ran and the one the rig still has built, so it
    # stays listed for the usual reason: a rig that has not rebuilt still receives
    # `--consumer`, and a silent `Consumer: not identified` in a rig log is the
    # half-recorded pair that flag exists to prevent.
    "9048082",
    # `dc21958` (beta.6) never became FORK_TEST_PIN and so was never installable
    # through the app — see the note on FORK_TEST_PIN. Listed anyway because it WAS
    # named to the maintainer as a test pin in lap 30, so a hand-built copy could
    # exist on the rig, and `--consumer` costs nothing to keep working on it. Being
    # listed here is explicitly not an endorsement: it is withdrawn.
    "dc21958",
    # Retired when the pin moved to `92ceeed` (beta.8). `4a35604` is the build BOTH
    # SIDES DECLARED in writing (their lap 32, our lap 33) and it is behaviourally
    # identical to beta.8 — the `src/*.c` + `src/*.h` diff between them is empty and
    # their source anchor did not move. A rig that built beta.7 is running the same
    # ripping code and must keep receiving `--consumer`.
    "4a35604",
    # The commit that GENERATED their beta.7 golden reference. Never a test pin: their
    # lap 32 as first sent named it as one by mistake and they corrected the file in
    # place. Listed because a rig could have built it from that first copy.
    "400155b",
    # Retired within the hour by `104f6d4`. Same ripping code — the `src/*.c` +
    # `src/*.h` diff from `4a35604` all the way to `104f6d4` is empty — so a rig that
    # built it is running the declared code and must keep receiving `--consumer`.
    "92ceeed",
)

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
#:
#: **:data:`FORK_EXPECTED_BUILD_TAG` joined this set when round 7 closed, and
#: leaving it out would have been a silent regression.** The sentence above was
#: written when ``FORK_PIN`` was the r2 build, which predates the flag — so the
#: rule *"the pinned build must never be sent it"* was correct then and became
#: false the moment the pin moved to the round-7 release, which accepts it (its
#: own golden reference is invoked with ``-u platterpus/0.6.4b12``). Nothing would
#: have crashed; every rip on the new pin would simply have stopped recording who
#: drove it, which is the provenance line the whole seam exists to carry.
#:
#: The former production pin ``2f950c8`` is deliberately **absent**: it is r2, it
#: does not accept the flag, and a rig still running it must not be sent one.
BUILD_TAGS_ACCEPTING_CONSUMER_FLAG: Final[frozenset[str]] = frozenset(
    {
        FORK_EXPECTED_BUILD_TAG,  # the round-7 release, the current pin
        f"{FORK_BRANCH}-g{NEXT_PIN_UNDER_REVIEW}",  # r4
        FORK_TEST_BUILD_TAG,  # the round-7 test pin, still on the rig
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
        """The exact first line a correct build prints.

        Only meaningful when :attr:`version` is a real version. For an
        operator-supplied commit it is not — read :attr:`expectation` instead, which
        says so rather than composing a sentence around a placeholder.
        """
        return f"cyanrip {self.version} ({self.build_tag})"

    @property
    def version_known(self) -> bool:
        """False for an operator-supplied commit, whose `meson.build` we cannot read."""
        return not self.version.startswith("(")

    @property
    def expectation(self) -> str:
        """What a correct build must print, stated as strictly as we can and no more.

        For a pinned build that is the whole banner. For a commit handed to
        ``--install-ripper`` it is the build tag alone, because the version string of an
        arbitrary commit is genuinely unknown to us and printing a guess next to the
        word "expects" would invite a comparison against a number we never measured.
        The verify step keys on the tag in both cases, so nothing is weakened.
        """
        if self.version_known:
            return self.banner
        return (
            f"a banner ending ({self.build_tag}) — the version string is not "
            "predictable for a commit we do not pin"
        )


#: The pin a **closed** round approved. Moves only when a round closes.
PRODUCTION_TARGET: Final[ForkTarget] = ForkTarget(
    pin=FORK_PIN,
    version=FORK_EXPECTED_VERSION,
    why=(
        "the round-7 release, built from the code round 7 approved at 104f6d4 "
        f"(Platterpus {FORK_EXPECTED_VERSION}) — see docs/handshake/verified/"
        "round-07-lap-40.md §A for why the released commit and not the pin"
    ),
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
#: **Flipped back to PRODUCTION_TARGET on 2026-08-07**, which is the one line the
#: note above says it would be. Round 7 closed with GO on both sides, so the test
#: pin has done its job and the wizard builds the release again.
WIZARD_TARGET: Final[ForkTarget] = PRODUCTION_TARGET


def target_for_commit(pin: str) -> ForkTarget:
    """A build target for an ARBITRARY fork commit, for ``--install-ripper <commit>``.

    **Why this exists, and it closes a gap in a rule we had already written.**
    `CLAUDE.md` Critical rule #12 says *"a moving pin needs a route to it that does not
    ship inside a release"*, and names ``platterpus --install-ripper`` as that route.
    It was only half true: the flag existed, but it built :data:`WIZARD_TARGET`, whose
    pin is a module constant — so reaching a new pin still required cutting a release,
    which is the granularity the rule says is wrong. The fork's pin has now moved
    **five times inside one round**, twice in a single day.

    So the pin becomes an argument. What we can still check, we check: a correct build
    of ``pin`` must print ``platterpus-fork-g<pin>``, and :attr:`ForkTarget.build_tag`
    is derived, so the verify step is as strict as for a pinned build.

    What we CANNOT check is the version string — an arbitrary commit's
    ``meson.build`` is unknown to us, and inventing one would put a number we never
    measured into a banner comparison. :attr:`version` therefore says exactly that,
    and the resulting :attr:`banner` is not usable as an equality test. That is the
    honest shape: the tag is verified, the version is declared unknown, and nothing
    pretends otherwise.
    """
    return ForkTarget(
        pin=pin,
        version="(version not known for an operator-supplied commit)",
        why=(
            f"commit {pin}, supplied on the command line — NOT a pinned build, and no "
            "round has approved it. Every rip with this installed reports "
            "ripper_handshake_approval: unapproved, which is the correct answer"
        ),
    )


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
