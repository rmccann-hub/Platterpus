"""Which read offset a rip applies, and how to say what it is.

A bit-perfect rip needs the drive's read offset. cyanrip (the sole backend)
reads no config file of its own — the GUI passes the offset as `-s N` at rip
time. **The offset belongs to a DRIVE, not to the program** (the owner's rule of
2026-11-12: *"test the drive once, up front, save it per drive"*), so the value
a rip applies is the one saved in the SELECTED drive's profile
(:mod:`platterpus.drive_profiles`, persisted by
:mod:`platterpus.drive_profile_store`), and :func:`offset_for_drive` below is
the one function that decides it. Every caller — the Start gate, the argv, the
displays, ``--doctor``, the script verbs — delegates to it rather than restating
the rule.

Why this changed (2026-11-12). Until then the offset was ONE global value,
``Config.read_offset`` with the ``Config.override_read_offset`` switch, and the
per-drive profile only recorded provenance. A second drive that was not on the
AccurateRip list therefore ripped at the FIRST drive's offset with no prompt:
every sample shifted, silently — the EAC-2007 wrong-offset bug the profile
ledger was built to prevent, reached by the other door.

What the two global config fields mean now:

* ``override_read_offset`` stays the user's **master switch** — the drive
  wizard's "Apply this read offset to every rip" tick-box. Off means no ``-s``
  reaches cyanrip on any drive (and a Start then treats the drive as not set up,
  exactly as before).
* ``read_offset`` is **no longer read to decide a rip's offset**. It keeps the
  value most recently saved for a drive, so an older Platterpus reading the same
  config after a downgrade still finds a sane number, and it is read ONCE, by
  :func:`plan_global_offset_move`, to hand an existing user's offset to the drive
  it was set up on.

**No other file is consulted.** Until 2026-09-24 this module also read a
leftover per-drive offset from the config file of the ripper Platterpus used
before cyanrip (KDD-18). cyanrip never read that file, and the maintainer asked
for it gone (2026-09-24). The uninstaller still removes the file if it is there
(`deps/host_teardown.py`), because cleaning up is not reading.

No I/O: the one function that changes anything, :func:`move_global_offset`,
changes a store in memory and leaves saving it to its caller.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from platterpus.drive_profiles import (
    DriveProfile,
    OffsetRecord,
    OffsetSource,
    confidence_for,
    describe_source,
)
from platterpus.settings_validation import OFFSET_MAX, OFFSET_MIN

if TYPE_CHECKING:
    from platterpus.drive_profile_store import DriveProfileStore

log = logging.getLogger(__name__)

# --- Why a drive has (or has no) offset for the next rip --------------------
#
# Named, so a caller that refuses a rip can say WHICH condition refused it
# rather than a generic "not configured" (CLAUDE.md: a named function that
# returns which one refused).

#: The selected drive has a saved offset and the master switch is on.
REASON_APPLIED: Final[str] = "applied"
#: The master switch ("Apply this read offset to every rip") is off.
REASON_SWITCHED_OFF: Final[str] = "switched_off"
#: No drive is selected, so there is no drive to ask.
REASON_NO_DRIVE: Final[str] = "no_drive"
#: The selected drive has no offset saved in its profile.
REASON_NOT_SET_FOR_DRIVE: Final[str] = "not_set_for_drive"
#: The saved value is outside the range Settings accepts — a hand-edited or
#: corrupt ``drive_profiles.json``. Never handed to cyanrip.
REASON_OUT_OF_RANGE: Final[str] = "out_of_range"


@dataclass(frozen=True)
class DriveOffset:
    """What the next rip on one drive does with the read offset.

    ``value`` is the number handed to cyanrip as ``-s``, or None when no offset
    will be passed (``reason`` says why). ``record`` is the drive's saved record,
    kept even when it is not applied, so a display can name its provenance.
    """

    value: int | None
    reason: str
    record: OffsetRecord | None = None


def offset_for_drive(
    record: OffsetRecord | None,
    *,
    apply_offsets: bool,
    drive_selected: bool = True,
) -> DriveOffset:
    """THE answer to "which read offset does the next rip on this drive use?"

    ``record`` is the selected drive's saved offset (its profile's ``offset``),
    ``apply_offsets`` the master switch (``Config.override_read_offset``), and
    ``drive_selected`` whether a drive is selected at all. Pure; never raises.

    A drive with no record gets None — **never another drive's value**. The
    range check is here, at the chokepoint, because the profile file is an input
    like any other: its loader accepts any whole number, and an absurd one must
    not reach ``cyanrip -s``.
    """
    if not drive_selected:
        return DriveOffset(None, REASON_NO_DRIVE)
    if record is None:
        return DriveOffset(None, REASON_NOT_SET_FOR_DRIVE)
    if not OFFSET_MIN <= record.value <= OFFSET_MAX:
        return DriveOffset(None, REASON_OUT_OF_RANGE, record)
    if not apply_offsets:
        return DriveOffset(None, REASON_SWITCHED_OFF, record)
    return DriveOffset(record.value, REASON_APPLIED, record)


def is_offset_configured(decision: DriveOffset) -> bool:
    """True only if an offset will ACTUALLY reach the ripper for this drive.

    A thin view of :func:`offset_for_drive`, kept as its own name because the
    Start gate and the first-run offer ask exactly this yes/no question. Treating
    anything else as "configured" (a leftover offset in another program's config
    once; another drive's offset until 2026-11-12) made the rip skip both the
    AccurateRip-list auto-apply and the setup wizard, and rip at the wrong
    offset.
    """
    return decision.value is not None


def describe_applied_offset(decision: DriveOffset) -> str:
    """What the next rip on the selected drive does with the offset, in one line.

    Shared by Settings (which shows it read-only) and Setup & Updates (beside
    *Set up drive…*), so the two can never word the same fact differently. The
    offset has ONE home, the drive-setup wizard, and these are views of it.

    "Not applied" is not "zero": with no offset no ``-s`` reaches cyanrip at
    all, which for most drives is not bit-perfect, so the sentence says that
    rather than showing a bare ``+0``.
    """
    if decision.value is not None:
        source = describe_source(decision.record.source) if decision.record else ""
        tail = f" ({source})" if source else ""
        return f"{decision.value:+d} samples, applied to every rip on this drive{tail}"
    if decision.reason == REASON_NO_DRIVE:
        return "no drive selected: each drive keeps its own read offset"
    if decision.reason == REASON_NOT_SET_FOR_DRIVE:
        return (
            "not set for this drive yet: the next rip looks it up in the "
            "AccurateRip drive list, or asks you to set the drive up"
        )
    if decision.reason == REASON_OUT_OF_RANGE and decision.record is not None:
        return (
            f"the saved {decision.record.value:+d} is out of range and is not "
            "used: set the drive up again"
        )
    return "not applied: no read offset is passed to the ripper"


# --- The one-time move from the global offset to per-drive profiles ----------

#: Nothing to move: the global switch was off, so no offset was reaching a rip.
MOVE_NOTHING: Final[str] = "nothing"
#: No drive is selected yet; ask again once one is.
MOVE_WAIT: Final[str] = "wait"
#: A saved profile already holds the global value: it was set up on that drive.
MOVE_ALREADY_HELD: Final[str] = "already_held"
#: The selected drive inherits the global value.
MOVE_INHERIT: Final[str] = "inherit"


def plan_global_offset_move(
    *,
    override_read_offset: bool,
    read_offset: int,
    selected_fingerprint: str | None,
    profiles: Sequence[DriveProfile],
) -> str:
    """Which drive the single global offset of older versions belongs to.

    Run ONCE, the first time this version sees a selected drive (the store
    records that it ran). Returns one of the ``MOVE_*`` constants; pure, never
    raises. The rule, and why — so no existing user is suddenly blocked or
    silently changed:

    * **The switch was off** → nothing reached a rip, nothing to move.
    * **The value is out of range** → nothing to move (config loading already
      reset it and told the user; handing it on would put it back).
    * **No drive is selected** → wait; there is no drive to give it to.
    * **A saved profile already records that value** → it was set up on that
      drive (every wizard save, AccurateRip-list apply and accepted correction
      recorded the drive it was made for), so the drive already holds it as its
      own, and no other drive inherits it. A second drive with nothing saved is
      then asked to be set up, which is the fix, not a regression: it was
      ripping at the first drive's offset.
    * **Otherwise the SELECTED drive inherits it.** No profile holds the value,
      so it was set by a path that recorded no drive (a script's
      ``set read_offset``, or a save made before profiles existed), and the
      selected drive is the one that has been ripping at it. Any different
      record that drive had is replaced, because every rip it made used the
      global value, not that record.
    """
    if not override_read_offset:
        return MOVE_NOTHING
    if not OFFSET_MIN <= read_offset <= OFFSET_MAX:
        return MOVE_NOTHING
    if not selected_fingerprint:
        return MOVE_WAIT
    for profile in profiles:
        if profile.offset is not None and profile.offset.value == read_offset:
            return MOVE_ALREADY_HELD
    return MOVE_INHERIT


def move_global_offset(
    store: DriveProfileStore,
    fingerprint: str,
    *,
    override_read_offset: bool,
    read_offset: int,
    now_iso: str,
) -> str:
    """Carry out :func:`plan_global_offset_move` on ``store``, in memory.

    ``fingerprint`` is the selected drive's. Returns the plan. On anything but
    :data:`MOVE_WAIT` the store is marked moved (``global_offset_moved``), and on
    :data:`MOVE_INHERIT` the selected drive's record becomes the global value
    with :attr:`OffsetSource.GLOBAL_CONFIG` provenance. The caller saves the
    store, so the record and its "done" mark land in one write. Never raises.
    """
    plan = plan_global_offset_move(
        override_read_offset=override_read_offset,
        read_offset=read_offset,
        selected_fingerprint=fingerprint,
        profiles=store.all(),
    )
    if plan == MOVE_WAIT:
        return plan
    if plan == MOVE_INHERIT:
        existing = store.get(fingerprint)
        if existing is not None and existing.offset is not None:
            log.warning(
                "read offset: the selected drive's recorded %+d (%s) is replaced "
                "by %+d, the offset every rip on it used",
                existing.offset.value,
                existing.offset.source.value,
                read_offset,
            )
        base = existing or DriveProfile(fingerprint=fingerprint, vendor="", model="")
        store.upsert(
            replace(
                base,
                offset=OffsetRecord(
                    value=read_offset,
                    source=OffsetSource.GLOBAL_CONFIG,
                    confidence=confidence_for(OffsetSource.GLOBAL_CONFIG),
                    detected_at=now_iso,
                ),
            )
        )
    log.info(
        "read offset: moved to per-drive profiles (%s; global value %+d, applied "
        "%s, selected drive %s)",
        plan,
        read_offset,
        override_read_offset,
        fingerprint,
    )
    store.global_offset_moved = True
    return plan
