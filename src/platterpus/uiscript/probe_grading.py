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

import re
from dataclasses import dataclass
from typing import Final

from platterpus.deps.fork_source import same_commit
from platterpus.deps.ripper_manifest import RipperManifest, RipperRelease
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

#: cyanrip's offset finder's own lines, read in its source
#: (`cyanrip@174a134:src/cyanrip_main.c:594-692`, ``search_for_drive_offset``).
#: Named groups, never columns, so a reworded tail does not move the number read.
#:
#: **The summary is the answer.** The per-track lines (found, confirmed, a new
#: candidate replacing the old) are its working; the search ends by printing
#: ``Drive offset of ±N found (confidence: C)!`` once it has one (line 689), and
#: ``C`` is its own count of the tracks that agreed, so 1 means found once and
#: never confirmed. A run with working and no summary did not finish.
_SUMMARY: Final[re.Pattern[str]] = re.compile(
    r"^Drive offset of (?P<offset>[+-]\d{1,6}) found \(confidence: "
    r"(?P<confidence>\d{1,4})\)!",
    re.M,
)
_CANDIDATE: Final[re.Pattern[str]] = re.compile(
    r"^(?:New offset|Offset) of (?P<offset>[+-]\d{1,6}) (?:found|confirmed)", re.M
)
#: The three ways it ends without an answer (lines 634, 679, 681). NOT
#: ``Was not able to find drive offset with a radius of N frames``: that one is
#: followed by a retry at twice the radius (line 685), so it is working too.
#: ``Stopping, offset finding incomplete!`` is a stop signal cutting the search
#: short, and cyanrip still prints a summary after it if it had a candidate, so
#: a summary beside it is an incomplete search, never a finished one.
_GAVE_UP: Final[re.Pattern[str]] = re.compile(
    r"^(?P<why>No track had AccuRip entry, cannot find offset!"
    r"|No track was long enough, unable to find drive offset!"
    r"|Stopping, offset finding incomplete!)",
    re.M,
)
_STOPPED: Final[str] = "Stopping, offset finding incomplete!"


@dataclass(frozen=True)
class FoundOffset:
    """What ``cyanrip -f`` printed about the drive's offset.

    ``offset`` and ``confidence`` are the summary line's when there is one
    (``summarised``); otherwise ``offset`` is the last candidate the working
    named, or ``None``, and ``confidence`` is 0. ``gave_up`` is cyanrip's own
    sentence when it printed one of the three ending lines.
    """

    offset: int | None
    confidence: int
    summarised: bool
    gave_up: str


def parse_found_offset(output: str) -> FoundOffset:
    """Read ``cyanrip -f``'s output. **Never raises**: any input gives an answer."""
    try:
        # A carriage return starts a line as far as a terminal is concerned, and
        # a progress line ending in one must not hide the line written after it.
        text = output.replace("\r", "\n") if isinstance(output, str) else ""
        endings = [m.group("why") for m in _GAVE_UP.finditer(text)]
        why = endings[-1] if endings else ""
        summaries = list(_SUMMARY.finditer(text))
        if summaries:
            last = summaries[-1]
            return FoundOffset(
                int(last.group("offset")), int(last.group("confidence")), True, why
            )
        candidates = list(_CANDIDATE.finditer(text))
        offset = int(candidates[-1].group("offset")) if candidates else None
        return FoundOffset(offset, 0, False, why)
    except (ValueError, TypeError, AttributeError):
        return FoundOffset(None, 0, False, "")


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
