"""Pick the medium of a MusicBrainz release that matches the disc in the drive.

A MusicBrainz *release* can hold several *media* — disc 1, disc 2, a bonus DVD.
Only one of them is in the drive. Until this module existed, every code path
took ``medium-list[0]``, and the comment beside it read:

    # The brief targets audio CDs; the first medium is the one we want
    # in nearly all cases. Multi-disc handling is P1.

"In nearly all cases" is doing the load-bearing work there, and it was wrong on
the rig (2026-08-02). Disc 1 of a four-disc set has 16 tracks; the medium we
took listed 18; Platterpus handed cyanrip ``-t 17=`` and ``-t 18=``; cyanrip
answered ``Invalid track number 17, list has 16 tracks!`` and exited in two
seconds with nothing ripped.

The argv chokepoint now refuses an out-of-range ``-t``, so that exact failure
cannot recur — **but the chokepoint was never the real fix.** Suppressing two
bad arguments leaves the other sixteen: a disc-2 rip tagged with disc-1's track
titles, which produces a *complete, successful-looking* album of wrong metadata.
That is worse than a rip that fails loudly, and it is what this module prevents.

**How the right medium is identified**, best evidence first:

1. **The disc ID.** MusicBrainz stores, per medium, the disc IDs known to match
   it. Our disc ID came from the physical TOC, so a match here is *the* answer
   and nothing else is consulted.
2. **A unique track-count match.** If exactly one medium has as many tracks as
   the disc, that is it. Two media with the same count is not a match — it is an
   ambiguity, and this returns "could not tell" rather than picking.
3. **A sole medium.** A one-medium release has no ambiguity to resolve.

If none of those apply the answer is **not determined**. The caller still gets
``medium-list[0]`` so a rip is possible, but flagged ``confident=False`` with a
reason, so the UI and the report can say the metadata may belong to a different
disc instead of asserting it silently. Same tri-state discipline as the ripper
identity and the pre-gap state: "we could not tell" is a real answer and must
never be dressed up as a determination.

Pure: dicts in, dataclass out, no I/O and no Qt. It parses an unmaintained
dependency's JSON (Critical rule #1), so it **never raises** — hostile input
yields a "not determined" answer, not an exception.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Literal

#: How the medium was chosen. Ordered strongest-first; the string lands in the
#: report so a support reader can see *why* a medium was believed.
SelectionBasis = Literal[
    "disc-id",
    "track-count",
    "sole-medium",
    "undetermined-first",
    "none",
]

#: Bases that constitute real evidence about which disc is in the drive.
CONFIDENT_BASES: Final[frozenset[str]] = frozenset(
    {"disc-id", "track-count", "sole-medium"}
)


@dataclass(frozen=True)
class MediumChoice:
    """Which medium we are treating as the disc in the drive, and on what basis."""

    #: Index into the release's ``medium-list``. ``-1`` when there are no media.
    index: int
    #: The chosen medium dict. Empty when there are none.
    medium: dict[str, Any] = field(default_factory=dict)
    basis: SelectionBasis = "none"
    #: One sentence for a tooltip, a log line, or the JSON report.
    detail: str = ""
    #: How many media the release has, so a caller can say "disc 2 of 4".
    total_media: int = 0

    @property
    def confident(self) -> bool:
        """True only when something actually identified this disc.

        ``undetermined-first`` is a *fallback so a rip can proceed*, not a
        determination. Treating it as one is how disc 2 gets disc 1's titles.
        """
        return self.basis in CONFIDENT_BASES

    @property
    def position(self) -> int:
        """The medium's 1-based disc number, falling back to index order."""
        raw = self.medium.get("position") if isinstance(self.medium, dict) else None
        try:
            value = int(str(raw))
        except (TypeError, ValueError):
            return max(self.index + 1, 1)
        return value if value > 0 else max(self.index + 1, 1)


def _as_int(value: object) -> int | None:
    """Coerce MB's loosely-typed numbers. ``None`` for anything unusable.

    Bounded: MusicBrainz is the untrusted boundary, and CPython refuses to
    ``int()`` a digit run longer than 4300 characters.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and 0 < len(value) <= 9 and value.strip().isdigit():
        return int(value)
    return None


def _medium_disc_ids(medium: dict[str, Any]) -> set[str]:
    """Every disc ID MusicBrainz associates with this medium.

    Requires the ``discids`` include on the release fetch; without it the
    ``disc-list`` is absent and this returns an empty set, which correctly
    degrades to the track-count rule rather than mis-matching.
    """
    ids: set[str] = set()
    discs = medium.get("disc-list")
    if not isinstance(discs, list):
        return ids
    for disc in discs:
        if isinstance(disc, dict):
            disc_id = disc.get("id")
            if isinstance(disc_id, str) and disc_id:
                ids.add(disc_id)
    return ids


def _medium_track_count(medium: dict[str, Any]) -> int | None:
    """The medium's track count, from the declared field or the actual list.

    MB usually sends ``track-count``, but not always; falling back to the
    length of ``track-list`` is what makes the track-count rule usable on a
    sparse response instead of silently unavailable.
    """
    declared = _as_int(medium.get("track-count"))
    if declared is not None:
        return declared
    tracks = medium.get("track-list")
    return len(tracks) if isinstance(tracks, list) else None


def select_medium(
    media: object,
    *,
    disc_id: str = "",
    disc_track_count: int | None = None,
) -> MediumChoice:
    """Choose the medium matching the disc in the drive. Never raises.

    ``media`` is the release's ``medium-list`` exactly as MusicBrainz sent it —
    validated here rather than trusted, because it crosses the boundary of an
    unmaintained dependency. ``disc_id`` is our TOC-derived MusicBrainz disc ID
    and ``disc_track_count`` the number of tracks the drive reports.
    """
    if not isinstance(media, list) or not media:
        return MediumChoice(
            index=-1,
            basis="none",
            detail="The release lists no media, so no track list could be read.",
            total_media=0,
        )

    # Ignore entries that are not dicts rather than letting one bad element
    # abort the selection: MB has sent surprises before, and a partial answer
    # beats no answer as long as it is honest about which it is.
    indexed = [(i, m) for i, m in enumerate(media) if isinstance(m, dict)]
    total = len(media)
    if not indexed:
        return MediumChoice(
            index=-1,
            basis="none",
            detail="The release's media list held no readable entries.",
            total_media=total,
        )

    # 1. Disc ID — authoritative. Our disc ID is computed from the physical TOC,
    #    so a medium claiming it IS the disc in the drive.
    if disc_id:
        for index, medium in indexed:
            if disc_id in _medium_disc_ids(medium):
                return MediumChoice(
                    index=index,
                    medium=medium,
                    basis="disc-id",
                    detail=(
                        f"Matched by MusicBrainz disc ID: this disc is medium "
                        f"{index + 1} of {total}."
                    ),
                    total_media=total,
                )

    # 2. A sole medium cannot be the wrong one. Checked before track count so a
    #    single-disc release whose count MB has wrong still resolves.
    if len(indexed) == 1:
        index, medium = indexed[0]
        return MediumChoice(
            index=index,
            medium=medium,
            basis="sole-medium",
            detail="The release has one medium, so there is nothing to choose between.",
            total_media=total,
        )

    # 3. A UNIQUE track-count match. Two media with the same count is an
    #    ambiguity, not a match — picking either would be a coin flip presented
    #    as a fact.
    if disc_track_count is not None and disc_track_count > 0:
        matches = [
            (i, m) for i, m in indexed if _medium_track_count(m) == disc_track_count
        ]
        if len(matches) == 1:
            index, medium = matches[0]
            return MediumChoice(
                index=index,
                medium=medium,
                basis="track-count",
                detail=(
                    f"Matched by track count ({disc_track_count}): this disc is "
                    f"medium {index + 1} of {total}, the only one with that many "
                    f"tracks."
                ),
                total_media=total,
            )

    # Nothing identified it. Fall back to the first medium so a rip is still
    # possible, and say plainly that the metadata may belong to another disc.
    index, medium = indexed[0]
    counts = ", ".join(str(_medium_track_count(m) or "?") for _, m in indexed)
    if disc_track_count:
        why = (
            f"the drive reports {disc_track_count} tracks and the release's media "
            f"have {counts}"
        )
    else:
        why = (
            f"the release's media have {counts} tracks and the disc's count is unknown"
        )
    return MediumChoice(
        index=index,
        medium=medium,
        basis="undetermined-first",
        detail=(
            f"Could not determine which of this release's {total} discs is in the "
            f"drive — {why}. Showing medium {index + 1}; its track titles may "
            f"belong to a different disc of the set."
        ),
        total_media=total,
    )
