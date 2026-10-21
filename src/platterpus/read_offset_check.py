"""Is the read offset this rip applied the one AccurateRip lists for its drive?

**Why this exists** (TASKS P2 #6; the owner's known-fixes list of 2026-10-21,
item 11: *"The log doesn't say the read offset is right, only which one was
applied."*). A wrong read offset shifts every sample of every track and still
reads cleanly. The app *picks* the offset from AccurateRip's drive-offset list
(KDD-31), but the report only wrote down the number applied, never whether it
was the list's; the real logcheckers deduct for that row (``docs/eac-parity.md``
Part D, −5).

**Two pieces of evidence, side by side.** *The database:* the drive as the
rip's own log names it (cyanrip's banner, not the drive picker's idea of it),
looked up by the rule the app applies offsets with
(``OffsetDatabase.lookup_entry``; ``lookup`` delegates to it): ``matches``,
``differs``, ``drive_not_listed`` or ``not_determined``. *The disc* (KDD-31): a
track that matched the AccurateRip consensus was read at an offset right for
this unit, so ``accuraterip_reconfirms`` is ``confirmed`` (one or more tracks
matched), ``not_confirmed`` (tracks, none matched, which proves nothing either
way) or ``not_determined`` (no tracks).

**Tri-state, and the third state is not a pass.** ``not_determined`` means we
could not check (no drive named, no list available to this writer, no offset
stated); it is never written as ``matches`` and never as ``differs``. A
``differs`` raises a ``warning`` issue; ``drive_not_listed`` an ``info`` one;
``not_determined`` none, because an entry that fires on every report where
nothing could be checked trains a reader to skip it.

Pure, Qt-free and never raises: the banner is external text (Critical rule
#12), so it is bounded before it is used or quoted.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Final, Protocol, TypedDict

from platterpus.parsers.rip_log import track_accuraterip_verified

log = logging.getLogger(__name__)

#: The four answers about the database. Strings, not an enum, because they are
#: written into the JSON report and read back from reports of any age.
OFFSET_MATCHES: Final[str] = "matches"
OFFSET_DIFFERS: Final[str] = "differs"
OFFSET_DRIVE_NOT_LISTED: Final[str] = "drive_not_listed"
OFFSET_NOT_DETERMINED: Final[str] = "not_determined"

#: The three answers about the disc (KDD-31).
AR_CONFIRMED: Final[str] = "confirmed"
AR_NOT_CONFIRMED: Final[str] = "not_confirmed"
AR_NOT_DETERMINED: Final[str] = "not_determined"

#: The issue codes (``rip_report.issues``).
ISSUE_DIFFERS: Final[str] = "read_offset_differs_from_accuraterip"
ISSUE_NOT_LISTED: Final[str] = "read_offset_drive_not_listed"

#: Longest banner we will look up. A real one is under 60 characters (the
#: BDR-209D's is 42); anything past this is not a drive name, and it must not
#: be quoted whole into a report sentence.
_MAX_BANNER_CHARS: Final[int] = 200

#: The interface word libcdio-paranoia can put before ``CD-ROM`` at the end of
#: its ``Device model:`` string (``PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM``).
_INTERFACE_WORDS: Final[frozenset[str]] = frozenset(
    {"SCSI", "ATAPI", "IDE", "USB", "SATA"}
)


class OffsetLookup(Protocol):
    """What this check needs from the AccurateRip list.

    A Protocol, so this pure module never imports the adapter;
    ``adapters.accuraterip_offsets.OffsetDatabase`` satisfies it.
    """

    @property
    def size(self) -> int: ...

    def lookup_entry(self, vendor: str, model: str) -> tuple[str, int] | None: ...


class ReadOffsetCheckBlock(TypedDict):
    """The report's ``rip.read_offset_check`` (schema v39, an addition)."""

    #: ``matches`` / ``differs`` / ``drive_not_listed`` / ``not_determined``.
    state: str
    #: The offset the ripper's log says it applied (``Offset: +667 samples``).
    applied: int | None
    #: The AccurateRip list's offset for the drive, and the row it came from.
    listed: int | None
    listed_entry: str | None
    #: The drive as the log names it, bounded.
    drive_as_logged: str | None
    #: One sentence saying all of the above.
    detail: str
    #: ``confirmed`` / ``not_confirmed`` / ``not_determined`` (KDD-31).
    accuraterip_reconfirms: str
    accuraterip_tracks_matched: int | None
    accuraterip_tracks_read: int | None
    accuraterip_detail: str


def drive_name_candidates(banner: object) -> tuple[str, ...]:
    """The names to try in the list for a drive banner, most specific first.

    cyanrip prints the drive two ways (``cyanrip@eca33dc:src/cyanrip_log.c:927,930``):

    * ``Drive used:     PIONEER  BD-RW   BDR-209D (revision 1.51)`` — the fork's
      line, vendor and model then the firmware revision in brackets;
    * ``Device model:   PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM`` — libcdio-
      paranoia's string: vendor, model, revision, then an interface and
      ``CD-ROM``.

    The revision and the interface are not part of AccurateRip's name, so they
    are dropped. The revision token is dropped only when it is recognisably one
    (an interface suffix was there, or the last token is four characters or
    fewer with a digit in it), so a model's own last word is never thrown away
    on a guess. Never raises; ``()`` for no usable name.
    """
    if not isinstance(banner, str):
        return ()
    text = banner.strip()
    if not text or len(text) > _MAX_BANNER_CHARS:
        return ()
    if text.lower().startswith("error retrieving"):
        return ()  # cyanrip's own "could not read the drive's identity"
    # The fork's form: everything before "(revision …)" is the name.
    head, bracket, _rest = text.partition("(revision")
    if bracket and text.endswith(")"):
        name = " ".join(head.split())
        return (name,) if name else ()
    tokens = text.split()
    candidates = [" ".join(tokens)]
    had_suffix = False
    if len(tokens) >= 2 and tokens[-1].upper() == "CD-ROM":
        tokens = tokens[:-1]
        if tokens and tokens[-1].upper() in _INTERFACE_WORDS:
            tokens = tokens[:-1]
        had_suffix = True
        candidates.append(" ".join(tokens))
    last = tokens[-1] if tokens else ""
    looks_like_revision = len(last) <= 4 and any(c.isdigit() for c in last)
    # Vendor + model + revision is at least three tokens.
    if len(tokens) >= 3 and (had_suffix or looks_like_revision):
        candidates.append(" ".join(tokens[:-1]))
    # Order kept, duplicates and empties dropped.
    seen: list[str] = []
    for name in candidates:
        if name and name not in seen:
            seen.append(name)
    return tuple(seen)


def _reconfirmation(
    tracks: Iterable[object] | None,
) -> tuple[str, int | None, int | None, str]:
    """KDD-31: do this rip's AccurateRip matches re-confirm the offset?"""
    track_list = list(tracks or ())
    read = len(track_list)
    if not read:
        why = "no tracks in the log, so AccurateRip cannot re-confirm the offset"
        return AR_NOT_DETERMINED, None, None, why
    matched = sum(1 for t in track_list if track_accuraterip_verified(t))
    if matched:
        why = f"AccurateRip matched {matched} of {read} tracks at this offset, "
        return AR_CONFIRMED, matched, read, why + "which confirms it on this drive"
    why = (
        f"no track of {read} matched AccurateRip, so this rip neither confirms "
        "nor refutes the offset (a disc not in the database, a CD-R and a wrong "
        "offset all look like this)"
    )
    return AR_NOT_CONFIRMED, 0, read, why


def check_read_offset(
    *,
    drive_banner: object,
    applied: object,
    lookup: OffsetLookup | None,
    tracks: Iterable[object] | None,
) -> ReadOffsetCheckBlock:
    """Compare the applied read offset with the AccurateRip list. Never raises.

    ``drive_banner`` is the parsed log's drive field, ``applied`` its
    ``Offset:`` value (what the ripper says it applied, not what we asked for),
    ``lookup`` the AccurateRip list (None when this writer was given none) and
    ``tracks`` the parsed log's tracks, for the KDD-31 half.
    """
    # `bool` is an `int` in Python; a True here is not an offset of 1.
    ok = isinstance(applied, int) and not isinstance(applied, bool)
    offset = applied if ok and isinstance(applied, int) else None
    drive = drive_banner.strip() if isinstance(drive_banner, str) else ""
    try:
        reconfirm = _reconfirmation(tracks)
        state, detail, entry = _judge(drive, offset, lookup)
    except Exception:  # noqa: BLE001 — a report field must never break a report
        log.exception("read-offset check failed; recorded as not determined")
        reconfirm = (AR_NOT_DETERMINED, None, None, "not checked")
        state, entry = OFFSET_NOT_DETERMINED, None
        detail = "the read offset could not be checked (an internal error)"
    ar_state, matched, read, ar_detail = reconfirm
    return {
        "state": state,
        "applied": offset,
        "listed": entry[1] if entry is not None else None,
        "listed_entry": entry[0] if entry is not None else None,
        "drive_as_logged": drive[:_MAX_BANNER_CHARS] or None,
        "detail": detail,
        "accuraterip_reconfirms": ar_state,
        "accuraterip_tracks_matched": matched,
        "accuraterip_tracks_read": read,
        "accuraterip_detail": ar_detail,
    }


def _judge(
    drive: str, offset: int | None, lookup: OffsetLookup | None
) -> tuple[str, str, tuple[str, int] | None]:
    """``(state, detail, list entry)``: the decision, apart from its record."""
    shown = f"{offset:+d}" if offset is not None else "the offset applied (not stated)"
    unchecked = f"{shown}, not checked against the AccurateRip drive database: "
    candidates = drive_name_candidates(drive)
    if not candidates:
        too_long = len(drive) > _MAX_BANNER_CHARS
        reason = (
            "the log's drive name is too long to be one"
            if too_long
            else "the log names no drive it could be looked up by"
        )
        return OFFSET_NOT_DETERMINED, unchecked + reason, None
    if lookup is None or lookup.size <= 0:
        reason = "the drive database was not available to this report"
        return OFFSET_NOT_DETERMINED, unchecked + reason, None
    # Most specific name first; the first row found is the answer.
    entry = next(
        (e for e in (lookup.lookup_entry("", n) for n in candidates) if e), None
    )
    if entry is None:
        return (
            OFFSET_DRIVE_NOT_LISTED,
            f"{shown}; the drive in the log ({candidates[-1]}) is not in the "
            "AccurateRip drive database, so the offset could not be checked "
            "against it",
            None,
        )
    name, listed = entry
    if offset is None:
        return (
            OFFSET_NOT_DETERMINED,
            "the log does not state the offset applied; the AccurateRip drive "
            f"database gives {listed:+d} for {name}",
            entry,
        )
    if offset == listed:
        detail = f"{offset:+d}, matches the AccurateRip drive database for {name}"
        return OFFSET_MATCHES, detail, entry
    detail = (
        f"{offset:+d} applied, but the AccurateRip drive database gives "
        f"{listed:+d} for {name}"
    )
    return OFFSET_DIFFERS, detail, entry


def issue_for(block: object) -> tuple[str, str, str] | None:
    """``(severity, code, message)`` for the report's ``issues``, or None.

    Reads the serialized block, so the list and the block cannot disagree.
    """
    if not isinstance(block, dict):
        return None
    state = block.get("state")
    said = f"read offset {block.get('detail') or ''}."
    ar = str(block.get("accuraterip_detail") or "")
    ar = f" {ar[:1].upper()}{ar[1:]}." if ar else ""
    if state == OFFSET_DIFFERS:
        harm = " A wrong read offset shifts every sample of every track."
        return "warning", ISSUE_DIFFERS, said + harm + ar
    if state == OFFSET_DRIVE_NOT_LISTED:
        return "info", ISSUE_NOT_LISTED, said + ar
    return None


def results_line(block: object) -> str:
    """The line the results pane shows, with its marker (status is never colour).

    ``✓`` a match, ``⚠`` a difference, ``ⓘ`` not listed or not determined.
    """
    if not isinstance(block, dict):
        return "ⓘ Read offset: not checked against the AccurateRip drive database."
    state = block.get("state")
    marker = {OFFSET_MATCHES: "✓", OFFSET_DIFFERS: "⚠"}.get(str(state), "ⓘ")
    line = f"{marker} Read offset {block.get('detail') or 'not checked'}."
    if block.get("accuraterip_reconfirms") != AR_NOT_DETERMINED:
        line += f" {block.get('accuraterip_detail')}."
    return line
