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


def _expected_build_sentence() -> str:
    """One line naming the build this Platterpus was verified against, and by whom."""
    our_round, our_version = _approved_record()
    return (
        f"{fork_source.FORK_EXPECTED_VERSION} ({fork_source.FORK_PIN}) — the build "
        f"handshake round {our_round} approved, for Platterpus {our_version}"
    )


def _mismatch_offer(channel: str, installed: str | None) -> RipperOffer:
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
    return RipperOffer(
        verdict=OFFER_MISMATCHED,
        channel=channel,
        release=None,
        install_commit=fork_source.FORK_PIN,
        auto_installable=True,
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
            "minutes and needs no commit typed in."
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
        # Not a numbered release. Three sub-cases, and they are genuinely different
        # to the person reading the message: the current test pin (expected), a
        # retired one (stale evidence), or a build we have no story for (the
        # `c4d1a00` case that prompted this redesign).
        if fork_source.same_commit(installed, fork_source.FORK_TEST_PIN):
            return _test_pin_offer(channel, installed, retired=False)
        if any(
            fork_source.same_commit(installed, retired)
            for retired in fork_source.SUPERSEDED_TEST_PINS
        ):
            return _test_pin_offer(channel, installed, retired=True)
        return _mismatch_offer(channel, installed)

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
    approved_here = newer.round_closed and newer.handshake_round <= our_round
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
        # THE COMMON CASE, AND IT COSTS NOTHING. Their round is closed and our record
        # has closed it too, so both halves of the bilateral gate are in. No SHA, no
        # command line, no paragraph of consequence — there is none to state.
        consequence = (
            f"\n\nHandshake round {newer.handshake_round} is closed on both sides, so "
            f"this build is one our record approves for Platterpus {our_version}. "
            "Platterpus can install it for you — it takes a few minutes and needs no "
            "commit typed in."
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
    current = (
        f"Your cyanrip build is the newest published: {row.version} ({installed}), "
        f"release {installed_seq} on the {channel} channel.{channel_note}"
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
