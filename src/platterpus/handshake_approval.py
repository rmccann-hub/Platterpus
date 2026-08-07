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
#:
#: **Derived from the record, and now gated against it.** Read off the
#: ``HANDSHAKE-APP-VERSION`` of the newest **closed** round's verification file that
#: names :data:`~platterpus.deps.fork_source.FORK_PIN` — today
#: ``docs/handshake/verified/round-07-lap-41.md``, which declares ``platterpus
#: 0.6.5`` against pin ``ddf7ac3``.
APPROVED_FOR_PLATTERPUS_VERSION: Final[str] = "0.6.5"

#: The handshake round whose **bilateral** GO approved the current pin.
#:
#: **This pair went stale for two releases and nothing caught it** (found
#: 2026-08-07). When round 7 closed, ``FORK_PIN`` moved to the round-7 release and a
#: test derived from the handshake record confirmed it — but these two constants sat
#: beside it untouched since v0.6.4b4, so v0.6.4 and v0.6.5 both stamped *"handshake
#: round 6 approved, for Platterpus 0.6.3"* into every rip report and every EAC-
#: compatible log, about a pin round **7** approved. Round 6 approved ``2f950c8``, a
#: different commit entirely.
#:
#: The reason it survived is the one `CLAUDE.md` names: **a list checked against
#: itself is consistent, not verified.** Both tests that touched these values
#: asserted ``str(APPROVED_BY_ROUND) in approval.detail`` — that the constant we
#: printed is the constant we hold. That is true for every possible value, including
#: a wrong one. Nothing compared either constant to the *record*, even though the
#: constant one line away in ``fork_source`` had exactly such a check and it was that
#: check which moved the pin correctly.
#:
#: ``tests/test_fork_source.py::test_the_approval_round_and_app_version_match_the_record``
#: now derives both from ``docs/handshake/`` the same way the pin is derived, so the
#: three values move together or the suite fails.
APPROVED_BY_ROUND: Final[int] = 7

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


def _why_this_build_is_here(tag: str) -> str:
    """A sentence naming *why* a recognised-but-unapproved build is installed.

    The verdict stays ``unapproved`` — a build under review or nominated for testing
    has been approved by nobody, and softening that would be the whole point of the
    check thrown away. What this adds is the *reason*, because "NOT the build this
    Platterpus was verified against" is the shape of message the old dependency
    dialog used to produce: every word true, and the user left thinking something
    broke. During a hardware session the test pin is *supposed* to be installed, and
    a report that cannot say so is the same failure as one that cannot say anything.

    Returns ``""`` for a build we have no story for — silence beats a guess.
    """
    lowered = tag.casefold()
    test_pin = fork_source.FORK_TEST_PIN
    if test_pin and test_pin.casefold() in lowered:
        return (
            f" That build is the round-{fork_source.FORK_TEST_PIN_ROUND} **test pin**"
            f" ({test_pin}, cyanrip {fork_source.FORK_TEST_VERSION}) — nominated by"
            " both projects to gather the hardware evidence the round needs to"
            " close. Seeing it here during a test session is expected; a test pin"
            " is not a release and no round has approved it."
        )
    for retired in fork_source.SUPERSEDED_TEST_PINS:
        if retired.casefold() in lowered:
            return (
                f" That build was a round-{fork_source.FORK_TEST_PIN_ROUND} test pin that"
                f" has since been RETIRED; the current one is {test_pin}"
                f" (cyanrip {fork_source.FORK_TEST_VERSION}). Evidence gathered with"
                " a retired pin is not what the round is waiting for."
            )
    under_review = fork_source.NEXT_PIN_UNDER_REVIEW
    if under_review and under_review.casefold() in lowered:
        return (
            f" That build is the pin an OPEN handshake round proposes"
            f" ({under_review}); it has not been approved by either project yet."
        )
    return ""


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
    extra = _why_this_build_is_here(tag)
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
    """The same check, taken off a **parsed** rip log.

    Accepts ``object`` and reads the attributes defensively because this is called
    from the report builder, which must never raise on a partially-parsed log.

    **Reads ``ripper_build`` FIRST, and that is the whole point of this function.**
    It used to read only ``log_creator`` — and the parser *splits the banner*: given
    ``cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)`` it stores
    ``log_creator`` **without** the parenthetical and puts the tag in
    ``ripper_build``. So :func:`approve_ripper` was handed a string with no ``(``,
    concluded "no build tag", and returned ``not_determined``.

    That was not merely a wrong *reason* — it was a **wrong verdict**. The same log,
    given its full first line, returns ``unapproved`` and names the test pin. Every
    real fork rip therefore reported *"which build produced this rip is not
    determined"* about a build it had already extracted and could name. The
    maintainer's own instruction predicted the right value — *"expect
    ripper_handshake_approval: unapproved on every rip"* — and we shipped the other
    one.

    Found by the cyanrip fork reading our JSON (round 7 lap 10, H2). Two lessons,
    both already written down here and both re-earned:

    * **The fixture was more capable than the product.** The test added the same day
      built its fixture with ``log_creator=FORK_EXPECTED_BANNER`` — the *whole*
      banner, which the parser never produces — so it exercised a string shape the
      product cannot hand this function. *"What does my stand-in do that the real
      thing does not?"*
    * **A tri-state's two negatives are not interchangeable.** ``not_determined``
      and ``unapproved`` are different claims about different evidence, and
      collapsing them the safe-looking direction still misreports.
    """
    build = str(getattr(rip_log, "ripper_build", "") or "").strip()
    banner = str(getattr(rip_log, "log_creator", "") or "").strip()
    if build:
        # Reassemble the banner the ripper actually printed. `approve_ripper` is the
        # single classifier — the log, the report, the UI and `--doctor` all reach it
        # — so this normalises the input rather than adding a second code path that
        # could disagree with it.
        return approve_ripper(f"{banner} ({build})" if banner else f"({build})")
    return approve_ripper(banner)


#: Tokens in the fork's compiled-in ``Handshake:`` line that mean *"this binary was
#: built from a tree whose round had not closed"*. Matched case-insensitively as
#: substrings, because the line is prose the fork writes for a human and its exact
#: shape is not something either side has frozen — J1 of round 7 lap 10 proposes
#: giving it a machine-readable form, and until that lands this is a best-effort
#: read of a *self-description*, never the basis of a negative on its own.
_NOTE_NOT_RELEASED: Final[tuple[str, ...]] = (
    "not a released build",
    "open",
    "hold",
)


def cross_check_note(verdict: str, note: str | None) -> str:
    """Compare our verdict on the banner against the binary's own statement.

    Two **independent** witnesses to the same fact. ``verdict`` comes from
    :func:`approve_ripper` reading the build tag against our record; ``note`` is the
    ``Handshake:`` line the fork's build system compiled into the binary. Neither is
    derived from the other, which is the only reason comparing them is worth
    anything — and it is why a build from an open-round tree says so *permanently*,
    in a way no banner can.

    Returns ``""`` when they agree or when there is nothing to compare, and a
    sentence naming the disagreement otherwise.

    **Why this function exists at all.** Our own round-7 lap-10 file told the fork
    that *"when the two disagree, the disagreement is the finding"* — and nothing in
    the code compared them. That is the capture-without-surfacing shape one layer up:
    we parsed the note (schema v17), stored it, published a claim about what we would
    do with it, and did nothing. The same defect the ``ripper_handshake_approval``
    block itself had until lap 10, when it turned out to be read by nothing.

    Pure; never raises.
    """
    text = (note or "").strip()
    if not text:
        return ""
    lowered = text.casefold()
    says_unreleased = any(token in lowered for token in _NOTE_NOT_RELEASED)

    if verdict == APPROVED and says_unreleased:
        # The dangerous direction. We approved a build that states, in its own
        # compiled-in text, that it came from a tree whose round had not closed.
        # Either our approved pin is wrong or their build tag is stale — CLAUDE.md
        # rule 12: a build tag names a commit, not what was built.
        return (
            "the ripper's own build-time note says it is NOT a released build "
            f"({text!r}) while our build-tag check reports it as the approved build. "
            "Two independent witnesses disagree, so one of them is wrong: either the "
            "approved pin is not what we think it is, or the binary carries a build "
            "tag for a different tree"
        )
    if verdict == NOT_DETERMINED:
        # Not a disagreement — the note is the ONLY witness here, and saying so is
        # the point: a reader must know the provenance rests on a self-description
        # we cannot corroborate.
        return (
            "the ripper's build tag could not be classified, so the only statement "
            f"about this build's provenance is its own: {text!r}"
        )
    return ""


#: The tool name, as cyanrip's own banner already spells it. A banner *starts* with
#: this word, so any renderer that prefixes "cyanrip " to one prints it twice.
_RIPPER_NAME: Final[str] = "cyanrip"


def _named_banner(banner: str) -> str:
    """A banner with the tool name exactly once. **Both renderers go through here.**

    Both of them said ``f"… + cyanrip {banner}"`` while every banner they are handed —
    :data:`fork_source.FORK_EXPECTED_BANNER`, and whatever the ripper actually reported
    — already begins ``cyanrip ``. So the maintainer-requested pair line rendered
    *"Platterpus 0.6.4b3 + cyanrip cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)"*, in the
    Copy-diagnostics bundle, which is the one place its whole job is to be quotable.

    Kept as a shared helper rather than fixed twice: the defect was **two** renderers
    making the same assumption, and fixing each in place leaves the assumption in two
    places to be made again by a third.

    A banner that does *not* name the tool still gets the prefix, because a bare version
    or build tag is exactly the case where the reader needs to be told which tool it is.
    """
    text = banner.strip()
    if text.casefold().startswith(f"{_RIPPER_NAME} "):
        return text
    return f"{_RIPPER_NAME} {text}" if text else f"{_RIPPER_NAME} (no banner)"


def version_pair_line() -> str:
    """One line naming **both** versions and what they were approved as.

    The maintainer's ask, rendered once so the log, the report and `--doctor`
    cannot phrase it three ways: *"include what versions you both are and what to
    use."*
    """
    return (
        f"Platterpus {__version__} + {_named_banner(fork_source.FORK_EXPECTED_BANNER)} "
        f"— pair verified by handshake round {APPROVED_BY_ROUND} "
        f"(approved for Platterpus {APPROVED_FOR_PLATTERPUS_VERSION})"
    )


def observed_version_pair_line(banner: str | None) -> str:
    """The same line, but reporting what this rip *actually* ran.

    Used where the artifact must say what happened rather than what should have:
    an archival log that names the approved pair while a different binary produced
    it is the stale-build-tag failure with the roles swapped.

    **Called from nowhere in `src/` as of v0.6.4b4** — the structured report carries the
    same facts as `ripper_version` / `ripper_build` / `ripper_handshake_approval`, so
    nothing is missing from a diagnosis; what is missing is this rendering, and the
    docstring above asserted a use it does not have. Recorded here rather than deleted
    or given a call site invented during a release: a renderer with no caller is the
    shape `RipHandle.cancel` had, and the honest state is worth writing down until it
    has the one it should have (`TASKS.md`, round-7 block).
    """
    approval = approve_ripper(banner)
    observed = approval.observed_banner or ""
    return (
        f"Platterpus {__version__} + {_named_banner(observed)} — "
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
    "cross_check_note",
    "observed_version_pair_line",
    "version_pair_line",
]
