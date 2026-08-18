"""Turning "a newer ripper exists" into an honest offer a person can act on.

:mod:`platterpus.deps.ripper_manifest` reads *their* document. This module answers
the question that actually matters here, which needs *our* record too: **should we
tell the user about this build, what happens to their rips if they take it, and can
Platterpus install it for them?**

**The consequence is the whole point.** Installing a fork build our handshake record
has not approved is not a neutral upgrade — :mod:`platterpus.handshake_approval`
compares the installed banner against the pin a closed round verified, so every rip
made afterwards reports ``ripper_handshake_approval: unapproved`` in its report, its
log and its EAC-compatible export. That is the *correct* verdict, not a bug.

**Their ``round_closed`` is their view, not our approval.** The manifest says whether
*the fork* considers a round closed. Our record is the one our rips are checked
against, and the two can legitimately differ for a while — they close their half
first, we verify, then we close ours. :func:`evaluate_offer` compares both and says
which situation you are in rather than collapsing them.

Redesigned 2026-08-18 (maintainer directive)
--------------------------------------------

*"the autoupdate on platterpus should take the next viable candidate without the
user needing to pick … it shouldnt need to be explicity callled out by eitether rop
unless very impartant"*, and *"make sure we can try will pins or non autoupdates,
but that is manually and by script most likely"*.

What this module used to do was end **every** answer with a command line to copy —
``platterpus --install-ripper <sha>`` — which made a SHA the interface. The operator
who reported it had ``c4d1a00`` installed against a ``ddf7ac3`` pin and got told
their build *"is not one of the fork's numbered releases … install a released build
first"*: accurate, and a dead end. The app knew which build it wanted and made a
person retype it.

So the shape is now **notice, and offer to do it** — three changes, each narrow:

1. :attr:`RipperOffer.install_commit` names the build a one-click install would
   build. The UI drives the install; **this module still installs nothing**, which
   ``tests/test_ripper_manifest.py::test_the_offer_never_installs_anything`` asserts
   on the source rather than on behaviour.
2. :attr:`RipperOffer.auto_installable` says whether that install carries a
   consequence a person must read first. It is ``True`` only for a build **our own
   record** approves, so the common case — *get back onto the build this Platterpus
   was verified against* — is one click and costs nothing.
3. :data:`OFFER_MISMATCHED` is a new verdict for "the installed ripper is not the
   build this Platterpus expects". It used to be folded into *not determined*, which
   is the answer that offers nothing — and it was the single most common real state.

**Pins stay manual, and stay a command line.** A specific commit is reached with
``--install-ripper <commit>``, which is what a rig script calls. That is deliberate:
an arbitrary commit has been approved by nobody, so it is exactly the case that
*should* cost a person a deliberate act. :func:`_install_hint` still renders it, for
the offers where it belongs.

**Being behind the fork is the normal state, so the code has to handle it well.** Our
pin sits several fork releases back on purpose — round 11 §5: ``ddf7ac3`` has hardware
behind it and nothing published since has been near a drive, and *"we do not ship a
ripper to users on the strength of a suite"*. So this module's job is not to close a
gap; it is to describe one accurately, and the gap will keep widening between hardware
rounds. That is why :func:`_seq_from_manifest` exists: a hand-maintained map of
release numbers cannot place a build published after the map shipped, and the
consequence of it failing to is a user on the fork's current release being told their
ripper has no story. Placing it from *their* document survives the next release
without an edit here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from platterpus.build_info import self_invocation
from platterpus.deps import fork_source
from platterpus.deps.ripper_manifest import (
    CHANNEL_BETA,
    CHANNEL_STABLE,
    CHANNELS,
    RipperManifest,
    RipperRelease,
)

log = logging.getLogger(__name__)

#: Outcomes. Strings rather than an enum, matching every other verdict in this
#: codebase, so the value reads the same in the log, a report and a bug report.
#:
#: ``NOT_DETERMINED`` is a first-class answer and is **never** rendered as "up to
#: date": we could not reach the manifest, or could not parse it. Saying "you're
#: current" when the honest answer is "I could not tell" is the failure this project
#: keeps naming — a check satisfied by finding nothing.
OFFER_NOT_DETERMINED: Final[str] = "not_determined"
OFFER_UP_TO_DATE: Final[str] = "up_to_date"
OFFER_AVAILABLE: Final[str] = "available"

#: The installed ripper is **not** the build this Platterpus was verified against,
#: and we can say what to do about it.
#:
#: **Split out of ``not_determined`` deliberately.** Both are "we cannot order this
#: build against the release sequence", so the old code returned the same verdict for
#: an unreachable network and for a wrong binary sitting on the ripping path. They
#: need opposite responses: one has nothing to offer, the other has exactly one
#: obvious thing to offer, and merging them meant the obvious thing was never
#: offered. Reported from real use, 2026-08-17.
OFFER_MISMATCHED: Final[str] = "mismatched"


@dataclass(frozen=True)
class RipperOffer:
    """What to tell the user about the ripper build situation.

    Pure data with a rendered sentence, so the dialog does no reasoning and the
    reasoning is testable without Qt.
    """

    #: One of :data:`OFFER_NOT_DETERMINED`, :data:`OFFER_UP_TO_DATE`,
    #: :data:`OFFER_AVAILABLE`, :data:`OFFER_MISMATCHED`.
    verdict: str
    #: The channel that was asked about.
    channel: str
    #: The build on offer *as the fork published it*, when there is one. ``None`` when
    #: the answer did not come from a manifest row — including
    #: :data:`OFFER_MISMATCHED`, whose target is our own pin rather than their row.
    release: RipperRelease | None
    #: One paragraph for the user. Always populated — a verdict with no explanation
    #: is what made the old dependency dialog accurate and useless.
    detail: str
    #: True when taking this build would make every subsequent rip report
    #: ``unapproved``. Carried separately from :attr:`detail` so the UI can refuse to
    #: make it the default action rather than relying on the user reading a
    #: paragraph.
    would_be_unapproved: bool = False
    #: The fork commit a one-click install would build, or ``""`` when there is
    #: nothing to install.
    #:
    #: **Carried so the UI never has to show it.** The whole defect this replaced was
    #: a SHA rendered into a sentence for a person to retype; the value is here for
    #: the install call, not for the paragraph.
    install_commit: str = ""
    #: True when Platterpus may offer that install as a plain "install it now?" with
    #: no consequence to weigh — i.e. **our own** record approves the build.
    #:
    #: ``False`` does not mean "refuse"; it means the offer must state what taking it
    #: costs and must not be the default button. That is the *"unless very
    #: important"* case, and it is the only one a person still has to think about.
    auto_installable: bool = False
    #: Whether this offer may be raised **unprompted** — the automatic launch-time
    #: check — as opposed to only when the user asks from the Help menu.
    #:
    #: **A separate axis from :attr:`auto_installable`, and it has to be.** That flag
    #: answers *"is this install safe"*; this one answers *"is now a reasonable moment
    #: to interrupt somebody about it"*. Conflating them is what let the automatic
    #: check raise an every-launch modal offering a step *backwards* to a user sitting
    #: on a fork release they installed on purpose: the install was perfectly safe and
    #: the interruption was still wrong.
    #:
    #: The UI used to decide this from the verdict alone (``verdict in (AVAILABLE,
    #: MISMATCHED)``), which cannot see the thing that matters — whether we managed to
    #: read the manifest at all, and therefore whether an unplaceable build might be
    #: one of their newer releases. That is knowable only here.
    #:
    #: **Defaults to ``False`` — fail closed.** A verdict added later is silent until
    #: somebody decides it is worth interrupting for, which is the direction a mistake
    #: should go in. The old verdict-list form defaulted the other way by construction:
    #: anything matching the list surfaced, and nothing made you think about it.
    may_surface_unprompted: bool = False

    @property
    def is_actionable(self) -> bool:
        """True only when there is a real, newer *published* build to offer."""
        return self.verdict == OFFER_AVAILABLE and self.release is not None

    @property
    def can_install(self) -> bool:
        """True when Platterpus knows a build it could install from here.

        Distinct from :attr:`is_actionable`, which asks whether the *fork* published
        something newer. A mismatched install has nothing newer to offer and still
        has an obvious thing to do — that gap is what made the old flow a dead end.
        """
        return bool(self.install_commit)

    def build_hint(self) -> tuple[str | None, tuple[str, ...]]:
        """The ``(version, meson_options)`` that describe :attr:`install_commit`.

        ``(None, ())`` unless :attr:`release` is a row for **that same commit**.

        **This exists because the two can be different commits, and the install used
        the row unconditionally.** The rollback offer is exactly that shape: the row
        is the channel head the user is sitting on, while ``install_commit`` is
        :data:`~platterpus.deps.fork_source.FORK_PIN`, the older build we are putting
        back. Handing the head's fields to a build of the pin produced two defects,
        both measured against the live manifest for the very operator this feature was
        written for (``c4d1a00`` installed, pin ``ddf7ac3``):

        * ``-Ddeclare_released=true`` reached a ``meson setup`` of ``ddf7ac3``, whose
          ``meson_options.txt`` does not exist. Meson fails the **whole configure** on
          an unknown ``-D``, ``set -eu`` aborts, and the step reports FAILED — so the
          advertised one-click repair could never succeed for the population it was
          for, and the user saw a meson error that reads as a Platterpus bug.
        * the expectation became ``cyanrip 0.9.4-rc1+platterpus.6
          (platterpus-fork-gddf7ac3)`` — a banner **no build prints**, because
          ``ddf7ac3`` prints ``+platterpus.5``. That pairing went into the log a bug
          report carries, in the one file used to attribute an artifact to a binary.

        Returning ``()`` is the safe answer in both directions and not a compromise:
        no options is exactly what every commit predating ``meson_options.txt`` needs,
        and ``version=None`` yields the honest **tag-only** expectation that
        ``ForkTarget.version_known`` exists to produce. The under-claim is the correct
        direction — the same reasoning as ``_clean_build_options``.

        A method on the offer rather than a check in the dialog on purpose: the UI had
        no way to know the two commits could differ, and the comment there asserted
        they could not. The fact lives where the commit is chosen.
        """
        row = self.release
        if row is None or not self.install_commit:
            return None, ()
        if not fork_source.same_commit(self.install_commit, row.commit):
            log.info(
                "ripper install: the manifest row describes %s but we are installing "
                "%s — building with no version claim and no meson options",
                row.commit,
                self.install_commit,
            )
            return None, ()
        return row.version, tuple(row.meson_options)


def _install_hint(commit: str) -> str:
    """The exact command that installs ``commit``, for the offers that need one.

    Names ``--install-ripper`` rather than describing the steps: it drives the *same*
    step engine the setup wizard does (`CLAUDE.md` Critical rule #12 — "a route to a
    moving pin that does not ship inside a release"), so this stays correct when a
    build dependency changes. A copied shell snippet would be a second description of
    the install and would drift the first time it did.

    **Only rendered where a person genuinely has to act.** Since 2026-08-18 the
    approved cases install themselves on one click, so a command line here means the
    build has a consequence attached — which is exactly when a deliberate,
    typed-out act is the right friction.
    """
    # `self_invocation()`, NOT the literal "platterpus". There is no `platterpus`
    # on PATH for an AppImage user — the project's PRIMARY distribution channel —
    # so this string used to hand them a command that produces
    # `bash: platterpus: command not found`. Reported by the cyanrip fork as the
    # only thing that had actually blocked the operator, and it blocked them
    # TWICE, which is what a broken instruction does: it does not teach.
    return f"{self_invocation()} --install-ripper {commit}"


def _approved_record() -> tuple[int, str]:
    """The round our record says approved the pin, and the app version it named.

    Imported lazily to keep this module free of an import cycle:
    :mod:`platterpus.handshake_approval` imports ``fork_source``, and a top-level
    import here would make the dependency direction ambiguous for a reader.

    Both halves together because `CLAUDE.md` Critical rule #12 says a round approves
    a pin *for a named app version* — quoting the round without the version is half
    the claim, and it is the half that reads as more authoritative than it is.
    """
    from platterpus.handshake_approval import (
        APPROVED_BY_ROUND,
        APPROVED_FOR_PLATTERPUS_VERSION,
    )

    return APPROVED_BY_ROUND, APPROVED_FOR_PLATTERPUS_VERSION


def _approves_commit(commit: str) -> bool:
    """Does our record approve the build at ``commit``? Delegated, never re-derived.

    A one-line pass-through to :func:`platterpus.handshake_approval.approves_commit`,
    imported lazily for the same import-cycle reason as :func:`_approved_record`. It
    exists as a named function here so the delegation is visible at the call site and
    so a future edit has to *replace a call* rather than tweak an expression — the
    thing that went wrong was an expression in this module quietly answering a
    question another module owns.
    """
    from platterpus.handshake_approval import approves_commit

    return approves_commit(commit)


def _expected_build_sentence() -> str:
    """One line naming the build this Platterpus was verified against, and by whom."""
    our_round, our_version = _approved_record()
    return (
        f"{fork_source.FORK_EXPECTED_VERSION} ({fork_source.FORK_PIN}) — the build "
        f"handshake round {our_round} approved, for Platterpus {our_version}"
    )


def _mismatch_offer(
    channel: str, installed: str | None, *, manifest_seen: bool = True
) -> RipperOffer:
    """The installed ripper is not the one this build expects. Offer to fix it.

    ``installed`` is the fork commit we read off the binary, or ``None`` when we could
    not identify a Platterpus-fork build at all — which covers a missing ripper, a
    failed probe, and **stock upstream cyanrip**, three states with one correct
    response and no way to tell apart from a commit alone.

    ``auto_installable`` is ``True`` here without qualification, and that is the one
    claim in this module that costs nothing to make: the build being offered is
    :data:`~platterpus.deps.fork_source.FORK_PIN`, so taking it moves a rip's verdict
    *to* ``approved``. There is no consequence to weigh, so there is nothing for the
    user to read before clicking.

    ``manifest_seen`` is a different question and controls
    :attr:`RipperOffer.may_surface_unprompted` rather than the install. **When we could
    not read the manifest we cannot tell an unrecognised build from one of the fork's
    newer releases** — and those want opposite treatment: a stray build should be
    offered the pin, a *newer release* the user installed on purpose must not be nagged
    every launch to undo it. With a named commit and no manifest the honest position is
    "offer it if asked, never raise it unprompted". With no commit at all
    (``installed is None``) the offer stands unprompted regardless: no ripper on the
    ripping path cannot be a deliberate newer release, and that case is exactly the
    one worth interrupting for.
    """
    if installed:
        installed_line = f"Installed:  cyanrip build {installed}"
        lead = (
            "The cyanrip build installed on this machine is not the one this "
            "Platterpus was verified against."
        )
    else:
        installed_line = (
            "Installed:  not identified — the ripper may be missing, or it may be "
            "stock upstream cyanrip rather than the Platterpus fork"
        )
        lead = (
            "Platterpus couldn't identify a Platterpus-fork cyanrip build on this "
            "machine."
        )
    unsure = (
        ""
        if manifest_seen or not installed
        else (
            "\n\nThe fork's release manifest was unreachable, so Platterpus could not "
            "check whether that build is one of their newer published releases. If you "
            "installed it deliberately, nothing here needs doing."
        )
    )
    return RipperOffer(
        verdict=OFFER_MISMATCHED,
        channel=channel,
        release=None,
        install_commit=fork_source.FORK_PIN,
        auto_installable=True,
        # A NAMED build we could not place, with no manifest to place it against, is
        # not raised unprompted — see the docstring. `installed is None` still is.
        may_surface_unprompted=manifest_seen or not installed,
        # NOT `would_be_unapproved`: this offer's target IS the approved pin, so
        # taking it is what makes rips report `approved`. The flag describes the
        # build on offer, never the one already installed.
        would_be_unapproved=False,
        detail=(
            f"{lead}\n\n"
            f"{installed_line}\n"
            f"Expected:   {_expected_build_sentence()}\n\n"
            "Until they match, every rip reports its ripper as 'unapproved' in the "
            "report, the log and the EAC-compatible export. The audio is unaffected "
            "and still bit-perfect if its own checks pass — what changes is whether "
            "the record can say the ripper was jointly verified.\n\n"
            "Platterpus can install the expected build for you. It takes a few "
            f"minutes and needs no commit typed in.{unsure}"
        ),
    )


def _test_pin_offer(channel: str, installed: str, *, retired: bool) -> RipperOffer:
    """A build nominated for a hardware session, named as such rather than "wrong".

    A test pin is *supposed* to be installed during a session, so telling an operator
    mid-run that their ripper is wrong — or worse, quietly reinstalling over it — is
    the wrong advice at the worst moment. :attr:`auto_installable` is therefore
    ``False``: the route back to the pin is offered, and it is never the default.

    A **retired** pin is a different fact and gets said out loud: evidence gathered
    with it is not what any round is waiting for.
    """
    our_round, _ = _approved_record()
    if retired:
        story = (
            f"cyanrip build {installed} is a handshake **test pin from an earlier "
            f"round**, and it has since been retired. Evidence gathered with a "
            "retired pin is not what a round is waiting for."
        )
    else:
        story = (
            f"cyanrip build {installed} is the round-{fork_source.FORK_TEST_PIN_ROUND}"
            " **test pin** — nominated by both projects to gather hardware evidence. "
            "Seeing it here during a test session is expected."
        )
    return RipperOffer(
        verdict=OFFER_NOT_DETERMINED,
        channel=channel,
        release=None,
        install_commit=fork_source.FORK_PIN,
        # Deliberately NOT auto-installable — see the docstring. A session build is
        # the one thing an automatic update must never clobber.
        auto_installable=False,
        detail=(
            f"{story}\n\n"
            "A test pin is not a numbered release, so it cannot be ordered against "
            "the release sequence and whether anything newer exists is not "
            "determined. Rips made with it report their ripper as 'unapproved', "
            f"which is the correct answer: no round has approved it.\n\n"
            f"When the session is over, the build to return to is "
            f"{_expected_build_sentence()} — Platterpus can install it for you, or "
            f"you can name any commit yourself:\n    "
            f"{_install_hint(fork_source.FORK_PIN)}\n\n"
            f"(Round {our_round} is the newest our record has closed.)"
        ),
    )


def _seq_from_manifest(installed: str, manifest: RipperManifest | None) -> int | None:
    """Where ``installed`` sits in the release sequence **according to their document**.

    The second of two sources, and it exists because neither one alone can place the
    builds people actually run.

    * :data:`~platterpus.deps.fork_source.FORK_RELEASE_SEQ_BY_PIN` is *our* record.
      It is the only source that can place a build the fork has since moved past —
      including our own pin ``ddf7ac3`` (release 11), which is the head of no channel
      any more and therefore appears nowhere in the current manifest.
    * The manifest is *their* statement, and the only source that can place a release
      published **after this Platterpus was built**.

    **The second source is the fix for a defect the first one keeps producing.** The
    map is hand-maintained, which makes it a mirror of a document we already download,
    and a stale mirror answers ``None`` — which routes a user sitting on the fork's
    newest published stable to :func:`_mismatch_offer`: *"the build installed on this
    machine is not the one this Platterpus was verified against."* True, and it drops
    the fact that actually explains their situation, that they are on the fork's
    current release. That is the message the maintainer received on 2026-08-17 while
    running ``c4d1a00``.

    Adding ``c4d1a00`` to the map fixed **that build**. This fixes the **class**: the
    next release is equally absent from a map that shipped before it existed, so
    without this the identical wrong message returns on release 17 — and our pin is
    deliberately several releases behind (round 11 §5: ``ddf7ac3`` is rig-tested,
    nothing since has been near a drive), so being behind is the *normal* state here,
    not an anomaly to be tidied away. `CLAUDE.md`: where the underlying source is
    reachable, derive from it rather than maintaining a list by hand.

    Our record is asked **first**, and not because it is more trustworthy — the two
    agree wherever they overlap, which ``tests/test_ripper_manifest.py`` checks
    against the fork's own published document. It is so the answer for the build we
    care most about does not depend on the network being reachable.

    ``None`` stays a real answer: a build neither source can place cannot be ordered
    against anything, and the caller must report "not determined" rather than guess a
    direction.
    """
    if manifest is None:
        return None
    # Iterate OUR channel tuple rather than the dict, so the order two channels are
    # consulted in is fixed by this codebase instead of by JSON key order in a
    # document we did not write. Both channels usually name the same commit, so the
    # order rarely matters — "rarely matters" is precisely when a non-deterministic
    # answer goes unnoticed.
    for name in CHANNELS:
        row = manifest.channel(name)
        if row is not None and fork_source.same_commit(installed, row.commit):
            log.info(
                "ripper update: build %s is release %d per the fork's manifest "
                "(%s channel) — not in our own record",
                installed,
                row.release_seq,
                name,
            )
            return row.release_seq
    return None


def evaluate_offer(
    manifest: RipperManifest | None,
    channel: str = CHANNEL_STABLE,
    *,
    installed_commit: str | None = None,
) -> RipperOffer:
    """Decide what to say about ``channel``, given the manifest and our own record.

    ``installed_commit`` is the fork commit currently installed, read off the binary's
    banner by
    :meth:`platterpus.workers.ripper_update_worker.RipperUpdateWorker._probe_installed_commit`.

    **``None`` means "we could not identify a fork build" — it does NOT mean "the
    pinned one".** It used to: the parameter did not exist when this was written, so
    falling back to :data:`~platterpus.deps.fork_source.FORK_PIN` was the only option
    and was usually right. Once the binary is actually probed that fallback becomes a
    claim we never checked, and it fails in the worst direction — a machine running
    **stock upstream cyanrip** produces no fork commit, so the fallback reported it as
    ``0.9.4-rc1+platterpus.5 (ddf7ac3)``, *"your cyanrip build is current"*. Every
    word of that sentence was assembled from a constant. (Found 2026-08-18 while
    building the one-click install; same family as the ``_observed_ripper_banner``
    defect a day earlier — a value nothing produced, read through a default that
    could not raise.)

    Never raises: every input is already validated, and the failure modes are all
    "we do not know", which is a verdict rather than an exception.
    """
    if channel not in CHANNELS:
        # Same fail-safe direction as the app's own update check: an unrecognised
        # channel must never *widen* what a user is offered.
        log.warning(
            "ripper update: unknown channel %r — treating as %r",
            channel,
            CHANNEL_STABLE,
        )
        channel = CHANNEL_STABLE

    installed = (installed_commit or "").strip()

    # --- Classify what is installed FIRST, before consulting the network --------
    #
    # Order matters and it is not arbitrary. A wrong binary on the ripping path is
    # both the more urgent fact and the one we can act on with no network at all, so
    # answering it before the manifest means the offer still works offline. The old
    # order asked the manifest first and therefore had nothing to say when it was
    # unreachable — even though the useful answer needed only two local constants.
    if not installed:
        return _mismatch_offer(channel, None)

    installed_seq = fork_source.release_seq_for_commit(installed)
    if installed_seq is None:
        # Not a release OUR record lists. Handle the session builds first: being the
        # pin two projects nominated for a hardware round is the more relevant fact
        # about a binary than where it sits in a sequence, and it is the one case
        # where reinstalling over it would wreck work in progress.
        if fork_source.same_commit(installed, fork_source.FORK_TEST_PIN):
            return _test_pin_offer(channel, installed, retired=False)
        if any(
            fork_source.same_commit(installed, retired)
            for retired in fork_source.SUPERSEDED_TEST_PINS
        ):
            return _test_pin_offer(channel, installed, retired=True)
        # Then ask THEIR document, which knows about releases published after this
        # Platterpus was built — see :func:`_seq_from_manifest` for why a
        # hand-maintained map cannot be the only source here.
        installed_seq = _seq_from_manifest(installed, manifest)
    if installed_seq is None:
        # Neither source can place it: a build with no story. Offline with an
        # unrecognised binary lands here too, which is the right answer — the useful
        # advice needs no network — but it is NOT raised unprompted in that case,
        # because without the manifest we cannot rule out that it is one of the fork's
        # newer releases and nagging somebody to undo a deliberate choice is the one
        # thing the automatic check must not do.
        return _mismatch_offer(channel, installed, manifest_seen=manifest is not None)

    if manifest is None:
        return RipperOffer(
            verdict=OFFER_NOT_DETERMINED,
            channel=channel,
            release=None,
            detail=(
                "Couldn't check for a newer cyanrip build — the fork's release "
                "manifest was unreachable or unreadable. Your installed ripper is "
                "unchanged, and this is not evidence that it is out of date."
            ),
        )

    row = manifest.channel(channel)
    if row is None:
        return RipperOffer(
            verdict=OFFER_NOT_DETERMINED,
            channel=channel,
            release=None,
            detail=(
                f"The fork's manifest carried no usable {channel} entry. Your "
                "installed ripper is unchanged."
            ),
        )

    newer = manifest.newer_than(channel, installed_seq)
    if newer is None:
        return _up_to_date_offer(channel, row, installed, installed_seq)

    # There is something newer. Everything below is about stating the cost honestly.
    our_round, our_version = _approved_record()
    # **Keyed on the COMMIT, through the same predicate the rip-time check uses.**
    #
    # This was `newer.round_closed and newer.handshake_round <= our_round` — the
    # manifest's own ROUND LABEL — until 2026-08-18, and that is a different question
    # in this project. `APPROVED_BY_ROUND` names the newest closed round that approved
    # *the pin we install*; rounds 9, 10 and 11 each closed here against a commit that
    # is not `FORK_PIN`, because reviewing a pin and installing it are separate acts
    # (round 11 §5). So any head the fork labelled with a round we have closed was
    # reported as *"one our record approves"*, offered as a one-click install with
    # nothing to weigh — and then stamped `unapproved` into every subsequent report,
    # log and EAC export. Four real cases reproduced it, including `422d12a`, the build
    # the fork WITHDREW for failing its own tests.
    #
    # `approves_commit` is `handshake_approval`'s own predicate, so the sentence this
    # function prints and the verdict a rip records are one computation. A second
    # implementation of "is this approved" is a second thing free to disagree, and the
    # one that reaches an archival record is the one that matters.
    approved_here = _approves_commit(newer.commit)
    unclosed = (
        ""
        if newer.round_closed
        else (
            f"\n\nThe fork also reports round {newer.handshake_round} as still OPEN, "
            "so this build has not completed verification on their side either."
        )
    )
    beta_note = (
        "\n\nThis is the beta channel: the fork publishes these for testing, and a "
        "beta ripper is expected to change again."
        if channel == CHANNEL_BETA
        else ""
    )
    headline = (
        f"A newer cyanrip build is published on the {channel} channel: "
        f"{newer.version} ({newer.commit}), release {newer.release_seq} — you have "
        f"release {installed_seq} ({installed})."
    )
    if approved_here:
        # IT COSTS NOTHING — because this build IS the one our record approved, so
        # taking it is what makes a rip report `approved`. The claim is about the
        # commit, and the sentence says so; it deliberately no longer cites the
        # round as the *reason*, because a round number was never the thing that
        # decides this.
        consequence = (
            f"\n\nThis is the build our record approves for Platterpus {our_version} "
            f"(handshake round {our_round}), so taking it is what makes your rips "
            "report their ripper as verified. Platterpus can install it for you — it "
            "takes a few minutes and needs no commit typed in."
        )
    else:
        consequence = (
            "\n\n⚠ Taking this build changes what your rips can claim. Platterpus "
            f"checks every rip against the ripper that handshake round {our_round} "
            f"approved, so until a round in *this* repository verifies {newer.commit}"
            ", every rip you make will report its ripper as 'unapproved' in the "
            "report, the log and the EAC-compatible export. The audio is unaffected "
            "and still bit-perfect if its own checks pass — what changes is whether "
            "the record can say the ripper was jointly verified."
            f"\n\nPlatterpus will not install this one for you. If you want it "
            f"anyway — during a joint test session, say — install it deliberately:"
            f"\n    {_install_hint(newer.commit)}"
        )
    # One assembly, one order, every part appended exactly once. `unclosed` is
    # empty whenever `approved_here` is true (a closed round is half of what
    # `approved_here` means), so the two can share this line without a branch.
    return RipperOffer(
        verdict=OFFER_AVAILABLE,
        channel=channel,
        release=newer,
        would_be_unapproved=not approved_here,
        install_commit=newer.commit,
        auto_installable=approved_here,
        # A genuine forward step, and we read the manifest to establish it. This is
        # the one case the automatic check exists for.
        may_surface_unprompted=True,
        detail=f"{headline}{consequence}{unclosed}{beta_note}",
    )


def _up_to_date_offer(
    channel: str,
    row: RipperRelease,
    installed: str,
    installed_seq: int,
) -> RipperOffer:
    """Nothing newer is published. Say so — and say whether it is the *approved* one.

    **"Newest published" and "the one your rips are checked against" are different
    questions, and this used to answer only the first.** A user who took a newer
    build during a session sits at the head of the channel *and* fails
    :func:`platterpus.handshake_approval.approve_ripper` on every rip, so the old
    text said "your cyanrip build is current" to someone whose every report said
    ``unapproved``. Both facts, or the reassuring one is a trap.
    """
    # Name the channel in the "current" answer, for the same reason the app's own
    # update check does: on stable, a user is genuinely current *for that channel*
    # while a newer beta exists, and a bare "you have the newest" would be the
    # accurate-but-misleading kind of true.
    channel_note = (
        " You're on the beta channel, so pre-release ripper builds are included."
        if channel == CHANNEL_BETA
        else " You're on the stable channel — pre-release ripper builds are not offered."
    )
    if fork_source.same_commit(installed, row.commit):
        current = (
            f"Your cyanrip build is the newest published: {row.version} ({installed}), "
            f"release {installed_seq} on the {channel} channel.{channel_note}"
        )
    else:
        # AHEAD OF THIS CHANNEL, which is not the same statement and must not borrow
        # the other one's sentence. `row` is the channel head; `installed` is a
        # different build that nothing newer supersedes — a beta while Settings say
        # stable, or a commit installed by hand. Pairing `row.version` with
        # `installed` here would print the head's version number against somebody
        # else's commit and call it "on the stable channel": every field true, the
        # sentence false. Exactly the shape `CLAUDE.md` keeps naming, and it only
        # became reachable once we started resolving a sequence the manifest states
        # rather than only ones our own map lists.
        current = (
            f"Nothing newer than your cyanrip build is published on the {channel} "
            f"channel — you have release {installed_seq} ({installed}), and {channel} "
            f"is at release {row.release_seq} ({row.commit}).{channel_note}"
        )
    if fork_source.same_commit(installed, fork_source.FORK_PIN):
        return RipperOffer(
            verdict=OFFER_UP_TO_DATE,
            channel=channel,
            release=row,
            detail=current,
        )
    # Newest published, but not what our record approved. Offer the way back.
    return RipperOffer(
        verdict=OFFER_UP_TO_DATE,
        channel=channel,
        release=row,
        install_commit=fork_source.FORK_PIN,
        auto_installable=True,
        detail=(
            f"{current}\n\n"
            "⚠ It is not, however, the build this Platterpus was verified against "
            f"({_expected_build_sentence()}), so every rip reports its ripper as "
            "'unapproved'. That is the correct verdict, not a fault — but if you did "
            "not mean to be ahead of the handshake, Platterpus can put the approved "
            "build back for you."
        ),
    )
