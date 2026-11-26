"""The acceptance script's graders for the rig, not for a rip.

Two questions a run asks of its surroundings rather than of what a rip left:

* **Is this the newest pair?** Round 30's D3, agreed with the cyanrip fork and
  ruled by our operator (option A): a run tests only the newest pair, so section
  A refuses to go on unless the build this app reviews is the fork's newest
  release by their published manifest and this app is our newest release.
  (``expect-ripper-under-review``, just before it, already checks the installed
  ripper is that build.) A run on anything else is not evidence, and a night
  spent on it is a night wasted.
* **What offset does cyanrip itself find?** The fork's round 30 lap 3 S24: this
  rig's drive has ground truth, +667, and nothing had ever run ``cyanrip -f``,
  cyanrip's own offset finder, against it.

Pure and Qt-free, like :mod:`platterpus.uiscript.artifact_grading`, whose
:class:`~platterpus.uiscript.artifact_grading.Grade` they return. The network
reads happen in the verbs (off the GUI thread); these functions only judge what
the reads returned. Nothing here raises.
"""

from __future__ import annotations

from typing import Final

from platterpus.deps.fork_source import same_commit
from platterpus.deps.ripper_manifest import RipperManifest, RipperRelease

# Re-exported by name (`X as X`): section O's verb and its tests read the reader
# from here, where it lived until 2026-11-25.
from platterpus.parsers.cyanrip_offset_search import (
    STOPPED,
)
from platterpus.parsers.cyanrip_offset_search import (
    FoundOffset as FoundOffset,
)
from platterpus.parsers.cyanrip_offset_search import (
    parse_found_offset as parse_found_offset,
)
from platterpus.uiscript.artifact_grading import Grade
from platterpus.update_check import ReleaseInfo, is_newer


def newest_fork_release(manifest: RipperManifest | None) -> RipperRelease | None:
    """The fork's newest published build: the channel row with the highest
    ``release_seq``, which is the manifest's own ordering key.

    Newest across BOTH channels, and deliberately so: under our operator's O3
    (2026-09-30) a new build goes to beta until its run passes, so the build a
    run should test is on beta while stable still names the one before it.
    """
    if manifest is None or not manifest.channels:
        return None
    return max(manifest.channels.values(), key=lambda row: row.release_seq)


def grade_newest_pair(
    manifest: RipperManifest | None,
    ours: ReleaseInfo | None,
    *,
    under_review: str,
    app_version: str,
) -> Grade:
    """D3: pass only when both halves of the pair are the newest.

    **A half that cannot be established fails, it does not pass.** Refusing on
    "not determined" costs a night only when the network is down, and the same
    night's run needs the network for MusicBrainz and AccurateRip anyway; passing
    on it would let a stale pair spend a night producing a run that is not
    evidence (our round 30 lap 4 S33).
    """
    newest = newest_fork_release(manifest)
    if newest is None:
        return Grade(
            False,
            "the fork's release manifest could not be read, so whether "
            f"{under_review} is their newest release is not determined; a run "
            "on a pair not shown newest is not evidence (D3)",
        )
    if ours is None:
        return Grade(
            False,
            "our own releases could not be read, so whether this app "
            f"({app_version}) is our newest release is not determined; a run on "
            "a pair not shown newest is not evidence (D3)",
        )
    stale: list[str] = []
    # The predicate every other surface asks, not a copy of it (CLAUDE.md: one
    # predicate, N callers).
    if not same_commit(newest.commit, under_review):
        stale.append(
            f"the fork's newest release is {newest.version} at {newest.commit} "
            f"(release {newest.release_seq}, {newest.channel}), and this app "
            f"reviews {under_review}"
        )
    if is_newer(ours.version, app_version):
        stale.append(
            f"our newest release is {ours.version}, and this app is {app_version}"
        )
    if stale:
        return Grade(False, "a stale pair: " + "; ".join(stale) + " (D3)")
    return Grade(
        True,
        f"the newest pair: {newest.version} at {newest.commit} "
        f"(release {newest.release_seq}, {newest.channel}) with Platterpus "
        f"{app_version}",
    )


# --- cyanrip -f ----------------------------------------------------------------

# The reader moved to `parsers/cyanrip_offset_search.py` (2026-11-25, TASKS R150),
# where Set up drive's offset search reads the same output through the same
# function; this module grades a script step with it.
_STOPPED: Final[str] = STOPPED


def grade_found_offset(found: FoundOffset, expected: int | None) -> Grade:
    """Pass when cyanrip's finished search found the offset this drive is set to.

    **Only a finished search passes.** A search stopped part-way, or one that
    never printed its summary, has not answered, whatever its last candidate
    was; reporting that as agreement would grade the working, not the answer.
    """
    if expected is None:
        return Grade(
            False,
            "no set-drive-offset has run, so there is no offset to compare "
            "cyanrip's against",
        )
    if not found.summarised:
        if found.offset is None:
            said = f": {found.gave_up!r}" if found.gave_up else ""
            return Grade(False, f"cyanrip -f found no offset{said}")
        return Grade(
            False,
            "cyanrip -f did not finish its search (no `Drive offset of … found` "
            f"line); its last candidate was {found.offset:+d}",
        )
    agreed = f"confidence {found.confidence}" + (
        ", found once and never confirmed" if found.confidence == 1 else ""
    )
    if found.gave_up == _STOPPED:
        return Grade(
            False,
            f"cyanrip -f was stopped before its search finished ({_STOPPED!r}); "
            f"it had {found.offset:+d}, {agreed}",
        )
    if found.offset != expected:
        return Grade(
            False,
            f"cyanrip -f found {found.offset:+d} ({agreed}); this drive is set "
            f"to {expected:+d}",
        )
    return Grade(True, f"cyanrip -f found {found.offset:+d} ({agreed}), as set")
