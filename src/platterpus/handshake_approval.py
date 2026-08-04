"""What the cyanrip handshake has *affirmatively* approved, and how a rip checks it.

**Why this module exists (maintainer directive, 2026-08-04).** *"Both of you should
not make a new release until you are both happy with the handshake files, and proper
testing is needed… This needs to be an affirmative handshake and include what
versions you both are and what to use, and verify at the time of rip as well so we
can confirm."*

Three obligations follow, and each was previously enforced somewhere other than
where it mattered:

1. **Affirmative, and bilateral.** A round closes only when **both** sides declare
   ``GO``. Silence is not consent and neither is one side's GO — the gate used to
   read our verdict alone, which meant their `HOLD` could not block our release.
   Enforced in ``scripts/handshake.py``; the *approved pair* it produces is
   recorded here.
2. **Both versions named, not just theirs.** A record saying *"pin `2f950c8`"* does
   not say which Platterpus that pin was approved *for*. Two artifacts from the
   same ripper and different app versions are not interchangeable evidence, and
   the pair is what a support question is actually about.
3. **Checked at rip time, not only in CI.** A release gate runs once, on a machine
   that never rips a disc. The user's rig is where an unapproved binary would
   actually be used, and until now nothing there compared the installed build
   against what the handshake approved: `ripper_identity` answers *"fork, stock, or
   undetermined"*, which is a different question from *"the build we verified"*.

**Tri-state, never a bare negative** (Code conventions: *say which build produced
an artifact*). An unrecognised or absent build tag reports ``not_determined``. A
build tag we do not recognise is not evidence of an unapproved build — it is
absence of evidence, and the two must not render the same way.

This module is **pure**: no subprocess, no I/O, no Qt. It takes a banner string
and returns a verdict, so the rip path, the report, the EAC-style log and the
preflight can all reach the same answer without three implementations of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from platterpus import __version__
from platterpus.deps import fork_source

#: The Platterpus version the currently-pinned ripper was approved **for**.
#:
#: Not ``__version__``: this names the release that carried the verification, and
#: it stays put while the app version moves on. When they differ, a rip is running
#: an approved *ripper* under an app the round never saw — worth saying, not worth
#: refusing, because our own changes are ours to make between rounds.
APPROVED_FOR_PLATTERPUS_VERSION: Final[str] = "0.6.3"

#: The handshake round whose **bilateral** GO approved the current pin.
APPROVED_BY_ROUND: Final[int] = 6

#: Verdict values. Strings rather than an enum so they cross the JSON boundary
#: unchanged and read the same in the log, the report and a bug report.
APPROVED: Final[str] = "approved"
UNAPPROVED: Final[str] = "unapproved"
NOT_DETERMINED: Final[str] = "not_determined"


@dataclass(frozen=True)
class RipperApproval:
    """Whether the ripper that produced a rip is the one the handshake approved."""

    verdict: str
    #: One sentence, written for the user rather than for a log parser. Always
    #: populated — a verdict with no explanation is what made the old dependency
    #: dialog accurate and useless.
    detail: str
    #: What the binary said it was, as far as we could read it. Empty when absent.
    observed_banner: str
    #: What the handshake approved, so the two sit side by side in any report.
    approved_banner: str = fork_source.FORK_EXPECTED_BANNER
    #: The Platterpus version the pair was verified as.
    approved_for_platterpus: str = APPROVED_FOR_PLATTERPUS_VERSION
    #: The round whose bilateral GO settled it.
    approved_by_round: int = APPROVED_BY_ROUND

    @property
    def is_approved(self) -> bool:
        """True only for an affirmative match. ``not_determined`` is **not** a pass."""
        return self.verdict == APPROVED


def _build_tag_of(banner: str) -> str:
    """The parenthetical build tag in a cyanrip banner, or ``""``.

    Deliberately tolerant of the whole banner being absent or malformed: this runs
    over a dependency's output, and the parse-never-raises rule applies.
    """
    if "(" not in banner or ")" not in banner:
        return ""
    inner = banner[banner.index("(") + 1 : banner.rindex(")")].strip()
    return inner


def approve_ripper(banner: str | None) -> RipperApproval:
    """Compare an observed cyanrip banner against the handshake-approved build.

    ``banner`` is the ripper's first log line or ``--version`` output — whatever we
    actually saw. ``None`` or empty means we never got one, which is
    ``not_determined`` and not a failure of the binary.

    Never raises.
    """
    text = (banner or "").strip()
    if not text:
        return RipperApproval(
            verdict=NOT_DETERMINED,
            detail=(
                "the ripper did not report a version banner, so whether it is the "
                "build this Platterpus was verified against could not be checked"
            ),
            observed_banner="",
        )

    tag = _build_tag_of(text)
    if not tag:
        return RipperApproval(
            verdict=NOT_DETERMINED,
            detail=(
                f"the ripper reported {text!r} with no build tag, so which build "
                "produced this rip is not determined — an absent tag is not "
                "evidence of an unapproved build"
            ),
            observed_banner=text,
        )

    if tag.casefold() == fork_source.FORK_EXPECTED_BUILD_TAG.casefold():
        return RipperApproval(
            verdict=APPROVED,
            detail=(
                f"ripper build {tag} is the one handshake round "
                f"{APPROVED_BY_ROUND} approved, verified by both projects, for "
                f"Platterpus {APPROVED_FOR_PLATTERPUS_VERSION}"
            ),
            observed_banner=text,
        )

    # A *recognisable* build that is not the approved one. This is the real
    # negative, and it is the case worth a loud line: the user is ripping with a
    # ripper no closed round has verified, which makes the archival claims on this
    # rip weaker than the ones on a verified rip — a fact only they can weigh.
    under_review = fork_source.NEXT_PIN_UNDER_REVIEW
    extra = ""
    if under_review and under_review.casefold() in tag.casefold():
        extra = (
            f" That build is the pin an OPEN handshake round proposes "
            f"({under_review}); it has not been approved by either project yet."
        )
    return RipperApproval(
        verdict=UNAPPROVED,
        detail=(
            f"ripper build {tag} is NOT the build this Platterpus was verified "
            f"against ({fork_source.FORK_EXPECTED_BUILD_TAG}, approved by handshake "
            f"round {APPROVED_BY_ROUND}). The rip is still bit-perfect if its own "
            f"checks passed — but it was not produced by a jointly-verified "
            f"ripper.{extra}"
        ),
        observed_banner=text,
    )


def approve_rip_log(rip_log: object) -> RipperApproval:
    """The same check, taken off a parsed rip log's ``log_creator`` banner.

    Accepts ``object`` and reads the attribute defensively because this is called
    from the report builder, which must never raise on a partially-parsed log.
    """
    banner = getattr(rip_log, "log_creator", "") or ""
    return approve_ripper(str(banner))


def version_pair_line() -> str:
    """One line naming **both** versions and what they were approved as.

    The maintainer's ask, rendered once so the log, the report and `--doctor`
    cannot phrase it three ways: *"include what versions you both are and what to
    use."*
    """
    return (
        f"Platterpus {__version__} + cyanrip {fork_source.FORK_EXPECTED_BANNER} "
        f"— pair verified by handshake round {APPROVED_BY_ROUND} "
        f"(approved for Platterpus {APPROVED_FOR_PLATTERPUS_VERSION})"
    )


def observed_version_pair_line(banner: str | None) -> str:
    """The same line, but reporting what this rip *actually* ran.

    Used where the artifact must say what happened rather than what should have:
    an archival log that names the approved pair while a different binary produced
    it is the stale-build-tag failure with the roles swapped.
    """
    approval = approve_ripper(banner)
    observed = approval.observed_banner or "(no banner)"
    return (
        f"Platterpus {__version__} + cyanrip {observed} — "
        f"handshake approval: {approval.verdict}"
    )


__all__ = [
    "APPROVED",
    "APPROVED_BY_ROUND",
    "APPROVED_FOR_PLATTERPUS_VERSION",
    "NOT_DETERMINED",
    "UNAPPROVED",
    "RipperApproval",
    "approve_rip_log",
    "approve_ripper",
    "observed_version_pair_line",
    "version_pair_line",
]
