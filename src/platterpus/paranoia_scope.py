"""Was the secure re-read exercised, counting the securing pass? Pure, never raises.

**Why this module exists.** ``rig-check``'s ``parser/paranoia`` row answered "was
the secure re-read genuinely exercised?" from the album's own log alone. In
dynamic mode the album pass reads each track once and the re-read happens in a
second ripper run, the *securing pass*, whose log is kept beside the album's as
``<album>.platterpus-securing-pass.txt`` (:data:`rip_addendum.SECURING_PASS_LOG_SUFFIX`).
On the 2026-11-03 Full run the whole-disc rip's securing pass re-read track 5
with ``-Z 2 -l 5`` ("converged after 3 reads", its log's ``Scope:`` line present)
and the row still said *"secure re-read genuinely exercised: no"*: true of the
log it read, false of the rip. A diagnosis we hold and do not show is the same
bug from the reader's side, so the row now reads both logs.

**One predicate, two passes.** Each pass is read with
:func:`~platterpus.parsers.rip_log.secure_rerip_tracks_scoped`, the same count
the acceptance script's ``expect-secure-rerip`` grades, so the row and the verb
cannot come to answer one question with two keys.

**What is graded, per pass.** ``sum(per-track) <= disc total`` for every counter,
the fork's published invariant (the disc block sums every pass, a track's block
is the last pass). Each ripper run has its own disc block, so each pass is
bounded against its own; adding the securing pass's per-track figures to the
album's disc block would compare two runs' numbers and could fail a correct rip.
The re-read multiple is an observation, never the property (``rig_check``'s
history of that mistake is in the docstring this was moved from).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from platterpus.parsers.rip_log import RipLog, secure_rerip_tracks_scoped

#: The paranoia counter that counts re-reads: the one summed and quoted with a
#: multiple. ``VERIFY``, ``FIXUP_ATOM`` and ``OVERLAP`` do not scale with the
#: passes (round-26 ``-Z 2``: ``VERIFY`` 2.15x while ``READ`` 3.02x), so they are
#: bound-checked one by one and never summed in.
REREAD_WITNESS: Final[str] = "READ"


@dataclass(frozen=True)
class PassScope:
    """One ripper run's paranoia counters and ``Scope:`` lines, as parsed."""

    per_track_by: dict[str, int]
    disc_by: dict[str, int]
    #: Track blocks carrying cyanrip's ``Scope:`` line (a re-read pass ran).
    scoped: int
    tracks: tuple[int, ...]

    @property
    def per_track(self) -> int:
        return self.per_track_by.get(REREAD_WITNESS, 0)

    @property
    def disc(self) -> int:
        return self.disc_by.get(REREAD_WITNESS, 0)

    @property
    def has_counters(self) -> bool:
        return bool(self.per_track_by or self.disc_by)

    def broken(self) -> list[str]:
        """Every counter whose per-track sum exceeds this run's disc total."""
        keys = sorted(set(self.per_track_by) | set(self.disc_by))
        return [
            f"{key} {self.per_track_by.get(key, 0)} > {self.disc_by.get(key, 0)}"
            for key in keys
            if self.per_track_by.get(key, 0) > self.disc_by.get(key, 0)
        ]


def read_pass(parsed: object) -> PassScope:
    """Read one parsed log's counters off the object. Never raises."""
    tracks = getattr(parsed, "tracks", ()) or ()
    per_track_by: dict[str, int] = {}
    for track in tracks:
        for key, value in (getattr(track, "paranoia_counts", None) or {}).items():
            per_track_by[key] = per_track_by.get(key, 0) + value
    disc_by: dict[str, int] = dict(getattr(parsed, "paranoia_counts", None) or {})
    scoped = secure_rerip_tracks_scoped(parsed) if isinstance(parsed, RipLog) else 0
    numbers = tuple(
        n for n in (getattr(t, "number", None) for t in tracks) if isinstance(n, int)
    )
    return PassScope(per_track_by, disc_by, scoped, numbers)


def _multiple_note(scope: PassScope) -> str:
    """The disc total as a multiple of the per-track sum: an observation."""
    if not scope.per_track or scope.disc == scope.per_track:
        return ""
    if scope.disc % scope.per_track == 0:
        multiple = f"{scope.disc // scope.per_track}"
    else:
        multiple = f"{scope.disc / scope.per_track:.2f}"
    return f" (disc total is {multiple}x the sum on this rip)"


def describe(
    album: PassScope, securing: PassScope | None = None, securing_name: str = ""
) -> tuple[bool | None, str]:
    """``(failed, detail)`` for the ``parser/paranoia`` row.

    ``failed`` is ``None`` when neither log carries a counter at all (the row is
    then untested, not passed), ``True`` when a pass breaks its own bound, and
    ``False`` otherwise. ``securing`` is the securing pass's log, or ``None``
    when the rip kept none (most rips: no track needed a second read).
    """
    if not album.has_counters and not (securing and securing.has_counters):
        return None, (
            "this log carries no paranoia counters at all — not a finding on "
            "its own (a clean read of a clean disc reports none), but it means "
            "the per-track/disc relationship is untested by this rip"
        )
    exercised = album.scoped or (securing.scoped if securing else 0)
    detail = (
        f"{REREAD_WITNESS} (the re-read witness): per-track counters sum to "
        f"{album.per_track}; the disc block totals {album.disc}. Scope: line "
        f"present on {album.scoped} of {len(album.tracks)} track(s)"
    )
    if securing is not None:
        numbers = ", ".join(str(n) for n in securing.tracks) or "none"
        detail += (
            f"; the securing pass ({securing_name}, track(s) {numbers}), its own "
            f"ripper run: per-track {securing.per_track}, its disc block "
            f"{securing.disc}, Scope: line on {securing.scoped} of "
            f"{len(securing.tracks)} track(s)"
        )
    detail += f" — secure re-read genuinely exercised: {'YES' if exercised else 'no'}"
    others = sorted((set(album.per_track_by) | set(album.disc_by)) - {REREAD_WITNESS})
    if others:
        detail += (
            f". Also bound-checked, not summed in: {', '.join(others)} (they do "
            f"not scale with the passes)"
        )
    broken = album.broken() + [
        f"securing pass {item}" for item in (securing.broken() if securing else [])
    ]
    if broken:
        return True, (
            f"{detail}. The per-track sum EXCEEDS the disc total for "
            f"{'; '.join(broken)}, which the provider contract says is "
            f"impossible: the disc block sums every pass and the per-track "
            f"figures are one pass each, so the sum can only ever be less than "
            f"or equal to it."
        )
    return False, f"{detail}{_multiple_note(album)}"


def counts_block(raw: object) -> dict[str, int] | None:
    """A pass's disc paranoia counters for the report, or None when none were read.

    Only ``str -> int`` entries survive (a ``bool`` is not a count); an empty
    dict stays empty, because "the log was read and printed no counter" and
    "no log was read" are different facts. Never raises.
    """
    if not isinstance(raw, dict):
        return None
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }
