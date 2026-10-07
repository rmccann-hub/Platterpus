"""What the installed ripper build *means*, in words a user can act on.

**Why this module exists.** Help → About listed the ripper as ``cyanrip: 0.9.4 ✓``,
and the update offer said *"release 28 — you have release 27 (e0471f4)"*. The
maintainer asked for the wording to be fixed *"so that the cyanrip fork version,
release, pin, etc. actually means something"* (2026-09-28). Every number was
accurate and none was explained: the accurate-and-useless shape this project
keeps finding in its own dialogs.

**What it decides: nothing.** Every verdict is *delegated*, so this module cannot
describe a build differently from the rip that build produces: approval is
:func:`platterpus.handshake_approval.approve_ripper` (the check every rip
records), fork / upstream / unknown is
:func:`platterpus.ripper_identity.identify_from_banner`, and the pins come from
:mod:`platterpus.deps.fork_source`. It puts those answers into sentences and
explains the vocabulary once (:data:`HOW_TO_READ`).

**Tri-state, as everywhere.** A build we cannot identify is never described as
upstream, and its approval line repeats the rip-time verdict rather than a guess.
Every status line starts with a text marker (``✓`` / ``ⓘ`` / ``⚠``), never colour
alone (WCAG 1.4.1). Pure: no I/O and no Qt. Nothing here raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from platterpus import handshake_approval
from platterpus.deps import fork_source
from platterpus.ripper_identity import fork_commit_from_banner, identify_from_banner

#: The vocabulary, explained once. Its examples are only examples: it is shown
#: beside whichever build is installed, so it describes no build of its own.
HOW_TO_READ: Final[str] = (
    "How to read a ripper version: in a version such as 0.9.4-rc2+platterpus.17, "
    "the part before the + (0.9.4-rc2) is the upstream cyanrip version the "
    "Platterpus fork is built on, and +platterpus.17 is the fork's own version on "
    "top of it. The commit, seven characters such as e0471f4, names the exact "
    "source a build came from, and approval belongs to the commit, not to the "
    "version number. The fork release number counts the builds the fork has "
    "published, so Platterpus can tell which of two builds is newer; it is a "
    "different number from the +platterpus version. A handshake round is the two "
    "projects testing one ripper build with one Platterpus version on a real drive, "
    "and a build is approved when both of them sign it off."
)

#: The same vocabulary in one sentence, for a dialog that already says a lot.
SHORT_HOW_TO_READ: Final[str] = (
    "(The +platterpus number is the fork's version, the commit names the exact "
    "source and is what gets approved, and the fork release number only orders the "
    "fork's published builds.)"
)

#: Where a user goes to change the installed ripper. The same menu path the rest of
#: the app names (``deps/build_notes.py``), so the instruction is identical wherever
#: it appears.
_SETUP_PATH: Final[str] = "Tools → Setup & Updates…"


def name_build(
    version: str | None, commit: str | None, release_seq: int | None = None
) -> str:
    """``cyanrip 0.9.4-rc2+platterpus.18 (commit 51cc789, fork release 28)``.

    One spelling of *a build* for every sentence that names one. Each part is
    optional and **omitted rather than invented**: with no version this names the
    commit alone (``the build from commit abc1234``) instead of borrowing a version
    from somewhere else. A version from one build beside another build's commit is
    the exact defect ``tests/test_ripper_manifest.py`` guards against.
    """
    ver = (version or "").strip()
    sha = (commit or "").strip()
    parts: list[str] = []
    if sha and ver:
        parts.append(f"commit {sha}")
    if release_seq is not None:
        parts.append(f"fork release {release_seq}")
    tail = f" ({', '.join(parts)})" if parts else ""
    if ver:
        return f"cyanrip {ver}{tail}"
    if sha:
        return f"the build from commit {sha}{tail}"
    return f"an unidentified cyanrip build{tail}"


def known_version_for_commit(commit: str | None) -> str | None:
    """The version this Platterpus *knows* a commit prints, or ``None``.

    Only the builds our record names: the approved pin, the build under review and
    the current test pin. For anything else the answer is ``None``. We do not know
    what it prints, and guessing would put one build's version beside another's
    commit.
    """
    sha = (commit or "").strip()
    if not sha:
        return None
    if fork_source.same_commit(sha, fork_source.FORK_PIN):
        return fork_source.FORK_EXPECTED_VERSION
    if fork_source.same_commit(sha, fork_source.PIN_UNDER_REVIEW):
        return fork_source.UNDER_REVIEW_TARGET.version
    test_pin = fork_source.current_test_pin()
    if test_pin and fork_source.same_commit(sha, test_pin):
        return fork_source.FORK_TEST_VERSION
    return None


def name_known_build(commit: str | None) -> str:
    """:func:`name_build` for a commit, with the version and release our record has."""
    sha = (commit or "").strip()
    return name_build(
        known_version_for_commit(sha),
        sha,
        fork_source.release_seq_for_commit(sha) if sha else None,
    )


def name_installed_build(
    commit: str | None, release_seq: int | None, manifest: object = None
) -> str:
    """The installed build, named with only the facts that belong to it.

    Its version comes from our record, or from a row of the fork's manifest that
    names this exact commit. Otherwise it is left out: a version read off a
    different row would name another build's version beside this commit.
    """
    from platterpus.deps.ripper_manifest import CHANNELS  # noqa: PLC0415

    version = known_version_for_commit(commit)
    if version is None and manifest is not None and commit:
        for channel in CHANNELS:
            row = getattr(manifest, "channel", lambda _c: None)(channel)
            if row is not None and fork_source.same_commit(row.commit, commit):
                version = row.version
                break
    return name_build(version, commit, release_seq)


def approved_build_sentence() -> str:
    """The build this Platterpus installs, and who approved it."""
    return (
        f"{name_known_build(fork_source.FORK_PIN)}. This version of Platterpus "
        f"installs it, and handshake round {handshake_approval.APPROVED_BY_ROUND} "
        f"approved it, tested with Platterpus "
        f"{handshake_approval.APPROVED_FOR_PLATTERPUS_VERSION}."
    )


def under_review_sentence() -> str:
    """The build a round is testing, or ``""`` when no round is testing one."""
    if not fork_source.a_round_is_reviewing_a_build():
        return ""
    return (
        f"{name_known_build(fork_source.PIN_UNDER_REVIEW)}. Handshake round "
        f"{fork_source.PIN_UNDER_REVIEW_ROUND} is testing it, and the acceptance test "
        "needs it, so this Platterpus accepts it too."
    )


@dataclass(frozen=True)
class RipperStanding:
    """The installed ripper, described for a person.

    * ``installed``: what is on this machine, e.g. *cyanrip 0.9.4-rc2+platterpus.17
      (commit e0471f4, fork release 27), the Platterpus fork*.
    * ``status``: approved, under test, not approved, or not determined, with what
      that means for the rips. Starts with a text marker.
    * ``verdict``: the rip-time verdict this status was written from
      (``approved`` / ``unapproved`` / ``not_determined``), so a test can check that
      the two are one fact.
    """

    installed: str
    status: str
    verdict: str


def _installed_sentence(banner: str) -> str:
    """What the banner says is installed, in words. Never names a build it cannot see."""
    identity = identify_from_banner(banner)
    commit = fork_commit_from_banner(banner)
    version = identity.version.removeprefix("cyanrip").strip()
    release = fork_source.release_seq_for_commit(commit) if commit else None
    name = name_build(version or None, commit, release)
    if identity.kind == "fork":
        return f"{name}, the Platterpus fork of cyanrip."
    if identity.kind == "stock":
        return f"{name}, an unmodified upstream cyanrip, not the Platterpus fork."
    tag = f' (build tag "{identity.build_tag}")' if identity.build_tag else ""
    return f"{name}{tag}; which build this is could not be determined."


def describe_installed_ripper(banner: str | None) -> RipperStanding:
    """What the installed ripper is, and what that means for your rips.

    ``banner`` is the ripper's own version line as the dependency check captured
    it, or ``None`` when no check has run yet. Never raises.
    """
    text = (banner or "").strip()
    approval = handshake_approval.approve_ripper(text or None)
    if not text:
        return RipperStanding(
            installed="Not checked yet.",
            status=(
                "ⓘ Not determined: the dependency check has not reported the "
                "ripper's version yet, so whether it is the approved build is not "
                "known. The check runs at launch."
            ),
            verdict=approval.verdict,
        )

    installed = _installed_sentence(text)
    if approval.verdict == handshake_approval.APPROVED:
        status = (
            "✓ Approved: both projects tested this exact build together and signed "
            f"it off (handshake round {handshake_approval.APPROVED_BY_ROUND}, with "
            f"Platterpus {handshake_approval.APPROVED_FOR_PLATTERPUS_VERSION}). "
            "Every rip records its ripper as approved."
        )
        return RipperStanding(installed, status, approval.verdict)

    if approval.verdict == handshake_approval.NOT_DETERMINED:
        return RipperStanding(
            installed,
            (
                "ⓘ Not determined: the ripper's version line carries no build tag, "
                "so whether it is the approved build cannot be checked, and every rip "
                "records it as not determined too. That is not evidence that "
                "anything is wrong."
            ),
            approval.verdict,
        )

    # UNAPPROVED: say WHY this build is here, because "not approved" alone reads as
    # "broken" to someone running exactly the build a test session asked for.
    commit = fork_commit_from_banner(text) or ""
    consequence = (
        "Until a handshake round approves it, every rip records its ripper as "
        "unapproved in its rip report. The audio is unaffected: a rip whose own "
        "checks pass is still bit-perfect."
    )
    if commit and fork_source.is_the_build_under_review(commit):
        status = (
            f"ⓘ Being tested, not approved yet: handshake round "
            f"{fork_source.PIN_UNDER_REVIEW_ROUND} is testing this build now, and "
            f"the acceptance test needs it. {consequence} Keep it until the round "
            "closes."
        )
    else:
        test_pin = fork_source.current_test_pin()
        if commit and test_pin and fork_source.same_commit(commit, test_pin):
            status = (
                f"ⓘ Test build, not a release: both projects chose it for round "
                f"{fork_source.FORK_TEST_PIN_ROUND}'s hardware test. {consequence}"
            )
        else:
            status = (
                "⚠ Not approved: no handshake round has approved this build for "
                f"this Platterpus. {consequence} {_SETUP_PATH} can install the "
                f"approved build, {name_known_build(fork_source.FORK_PIN)}."
            )
    return RipperStanding(installed, status, approval.verdict)


def about_lines(banner: str | None) -> list[tuple[str, str]]:
    """The About dialog's ripper section as ``(label, sentence)`` rows. Pure.

    Plain text: the caller renders it, and escapes it, because the installed
    sentence carries text the ripper printed about itself. :data:`HOW_TO_READ` is
    not included; the caller places it after the rows.
    """
    standing = describe_installed_ripper(banner)
    rows = [
        ("Installed", standing.installed),
        ("Status", standing.status),
        ("Default build", approved_build_sentence()),
    ]
    if extra := under_review_sentence():
        rows.append(("Build under test", extra))
    return rows


__all__ = [
    "HOW_TO_READ",
    "SHORT_HOW_TO_READ",
    "RipperStanding",
    "about_lines",
    "approved_build_sentence",
    "describe_installed_ripper",
    "known_version_for_commit",
    "name_build",
    "name_installed_build",
    "name_known_build",
    "under_review_sentence",
]
