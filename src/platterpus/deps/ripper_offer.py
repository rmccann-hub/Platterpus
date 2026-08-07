"""Turning "a newer ripper exists" into an honest offer a person can act on.

:mod:`platterpus.deps.ripper_manifest` reads *their* document. This module answers
the question that actually matters here, which needs *our* record too: **should we
tell the user about this build, and what happens to their rips if they take it?**

**The consequence is the whole point.** Installing a fork build our handshake record
has not approved is not a neutral upgrade — :mod:`platterpus.handshake_approval`
compares the installed banner against the pin a closed round verified, so every rip
made afterwards reports ``ripper_handshake_approval: unapproved`` in its report, its
log and its EAC-compatible export. That is the *correct* verdict, not a bug, and it
is exactly why this must never be automatic: a silent updater would quietly convert
a library of jointly-verified archival records into unverified ones. `CLAUDE.md`'s
deviation policy says the same thing from the other direction — switching the
container to a new cyanrip pin is a handshake event, not a preference.

So the shape is **notice, and offer**: we look, we say what we found, we state what
taking it costs, and a person decides. Nothing in this module installs anything.

**Their ``round_closed`` is their view, not our approval.** The manifest says whether
*the fork* considers a round closed. Our record is the one our rips are checked
against, and the two can legitimately differ for a while — they close their half
first, we verify, then we close ours. :func:`evaluate_offer` compares both and says
which of the three situations you are in rather than collapsing them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

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
#: date": we could not reach the manifest, could not parse it, or cannot place our
#: own installed build in the release sequence. Saying "you're current" when the
#: honest answer is "I could not tell" is the failure this project keeps naming — a
#: check satisfied by finding nothing.
OFFER_NOT_DETERMINED: Final[str] = "not_determined"
OFFER_UP_TO_DATE: Final[str] = "up_to_date"
OFFER_AVAILABLE: Final[str] = "available"


@dataclass(frozen=True)
class RipperOffer:
    """What to tell the user about the ripper build situation.

    Pure data with a rendered sentence, so the dialog does no reasoning and the
    reasoning is testable without Qt.
    """

    #: One of :data:`OFFER_NOT_DETERMINED`, :data:`OFFER_UP_TO_DATE`,
    #: :data:`OFFER_AVAILABLE`.
    verdict: str
    #: The channel that was asked about.
    channel: str
    #: The build on offer, when there is one. ``None`` for the other two verdicts.
    release: RipperRelease | None
    #: One paragraph for the user. Always populated — a verdict with no explanation
    #: is what made the old dependency dialog accurate and useless.
    detail: str
    #: True when taking this build would make every subsequent rip report
    #: ``unapproved``. Carried separately from :attr:`detail` so the UI can refuse to
    #: make it the default action rather than relying on the user reading a
    #: paragraph.
    would_be_unapproved: bool = False

    @property
    def is_actionable(self) -> bool:
        """True only when there is a real, newer build to offer."""
        return self.verdict == OFFER_AVAILABLE and self.release is not None


def _install_hint(release: RipperRelease) -> str:
    """The exact command that installs ``release``, for the offer text.

    Names ``--install-ripper`` rather than describing the steps: it drives the *same*
    step engine the setup wizard does (`CLAUDE.md` Critical rule #12 — "a route to a
    moving pin that does not ship inside a release"), so this stays correct when a
    build dependency changes. A copied shell snippet would be a second description of
    the install and would drift the first time it did.
    """
    return f"platterpus --install-ripper {release.commit}"


def evaluate_offer(
    manifest: RipperManifest | None,
    channel: str = CHANNEL_STABLE,
    *,
    installed_commit: str | None = None,
) -> RipperOffer:
    """Decide what to say about ``channel``, given the manifest and our own record.

    ``installed_commit`` is the fork commit currently installed, when it can be read
    off the binary's banner; ``None`` falls back to the commit this build *pins*,
    which is what a user who has never run ``--install-ripper`` will have. Either way
    the commit must be one whose release number we know
    (:func:`platterpus.deps.fork_source.release_seq_for_commit`) — a build outside the
    numbered release sequence, such as a mid-round test pin, cannot be ordered
    against releases and yields ``not_determined``.

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

    reference = installed_commit or fork_source.FORK_PIN
    installed_seq = fork_source.release_seq_for_commit(reference)
    if installed_seq is None:
        # A real and expected case during a hardware session: a test pin is not a
        # numbered release, so it has no place in the sequence. Say that plainly
        # rather than offering an "upgrade" that might be a sideways move.
        return RipperOffer(
            verdict=OFFER_NOT_DETERMINED,
            channel=channel,
            release=None,
            detail=(
                f"The installed cyanrip build ({reference}) is not one of the fork's "
                "numbered releases — a mid-round test pin, or a commit installed by "
                "hand. It cannot be ordered against the release sequence, so whether "
                "anything newer exists is not determined. Install a released build "
                "first if you want update checks to work."
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
        # Name the channel in the "current" answer, for the same reason the app's own
        # update check does: on stable, a user is genuinely current *for that
        # channel* while a newer beta exists, and a bare "you have the newest" would
        # be the accurate-but-misleading kind of true.
        channel_note = (
            " You're on the beta channel, so pre-release ripper builds are included."
            if channel == CHANNEL_BETA
            else (
                " You're on the stable channel — pre-release ripper builds are not "
                "offered."
            )
        )
        return RipperOffer(
            verdict=OFFER_UP_TO_DATE,
            channel=channel,
            release=row,
            detail=(
                f"Your cyanrip build is current: {row.version} ({reference}), release "
                f"{installed_seq} on the {channel} channel.{channel_note}"
            ),
        )

    # There is something newer. Everything below is about stating the cost honestly.
    our_round = _our_approved_round()
    approved_here = newer.round_closed and newer.handshake_round <= our_round
    consequence = (
        ""
        if approved_here
        else (
            "\n\n⚠ Taking this build changes what your rips can claim. Platterpus "
            f"checks every rip against the ripper that handshake round {our_round} "
            "approved, so until a round in *this* repository verifies "
            f"{newer.commit}, every rip you make will report its ripper as "
            "'unapproved' in the report, the log and the EAC-compatible export. The "
            "audio is unaffected and still bit-perfect if its own checks pass — what "
            "changes is whether the record can say the ripper was jointly verified."
        )
    )
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
    return RipperOffer(
        verdict=OFFER_AVAILABLE,
        channel=channel,
        release=newer,
        would_be_unapproved=not approved_here,
        detail=(
            f"A newer cyanrip build is published on the {channel} channel: "
            f"{newer.version} ({newer.commit}), release {newer.release_seq} — you "
            f"have release {installed_seq} ({reference}).{consequence}{unclosed}"
            f"{beta_note}\n\nTo install it:\n    {_install_hint(newer)}"
        ),
    )


def _our_approved_round() -> int:
    """The round *our* record says approved the pinned ripper.

    Imported lazily to keep this module free of an import cycle:
    :mod:`platterpus.handshake_approval` imports ``fork_source``, and a top-level
    import here would make the dependency direction ambiguous for a reader.
    """
    from platterpus.handshake_approval import APPROVED_BY_ROUND

    return APPROVED_BY_ROUND
