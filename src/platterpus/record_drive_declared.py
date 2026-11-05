# SPDX-License-Identifier: GPL-3.0-only
"""What the drive declares, from the fork's ``cyanrip-diagnostics/13`` record.

**Why this exists.** Whether a drive caches audio, returns C2 pointers or streams
accurately is something EAC asks it and we have only guessed at. The fork's
``.30`` asks the drive six read-only questions before a rip and keeps every
answer whole in the ``-j`` record as ``drive_declared`` (their round 38 lap 8
S17); our round 38 lap 9 S10 promised a release of ours carries it into the
report before one names ``.30``. ``--doctor`` reading it is TASKS R137, later.

**The shape, from their source** (``cyanrip@40dc64d7:src/diagnostics.c:345-410``,
written at ``:1010-1014``; pinned by their ``tests/diagrecord.c:404-493``)::

    "drive_declared": null            (a disc image, or no disc opened)
    "drive_declared": {
      "inquiry":       {REPLY},
      "configuration": {REPLY},       (GET CONFIGURATION, every feature)
      "cd_read_feature": {"found": bool, "bytes": hex|null, "current": bool|null,
                          "dap": bool|null, "c2_flags": bool|null,
                          "cd_text": bool|null},
      "mode_sense_all_pages": [{"page_control": "current"|"changeable"|
                                "default"|"saved", REPLY...}, ...],  (four)
      "vendor_settings": {...}        (from 5cc1c6b3: record_vendor_settings)
    }

where a REPLY is ``"answered": bool, "length": int|null, "truncated": bool|null,
"bytes": hex|null``, the last three null when it did not answer
(``diag_reply``, ``:349-363``). ``length`` is the whole length the reply's own
header declares, ``bytes`` the bytes kept, upper-case hex, at most 8,192
(``CRIP_REPLY_MAX``, ``cyanrip@40dc64d7:src/drive_caps.h:99``), and
``truncated`` is ``length`` > bytes kept. The CD Read feature (001Eh) is read out
of the GET CONFIGURATION reply: ``current`` is its byte 2 bit 0, and byte 4's
``dap`` 0x80, ``c2_flags`` 0x02 and ``cd_text`` 0x01 (``:386-400``). **Its bits
are null whenever its bytes are**, which includes ``found: true`` with fewer
than 5 bytes (``:389``, ``f.found && f.nb_bytes >= 5``), so ``found`` alone never
means the bits were read.

**Derived, not taken:** ``truncated`` checked against ``length`` and the bytes
kept (``agrees``), the four feature bits against the feature's own bytes
(``bits_agree_with_bytes``), each None with nothing to compare. **Declarations,
not measurements** (their comment at ``:365-372``). Tri-state throughout: absent
key ``not_present``, ``null`` ``not_stated``, a wrong type ``unrecognised``, never
a negative. Pure, never raises; read by :func:`platterpus.isrc_provenance.parse_isrcs`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, TypedDict

from platterpus import inbound_text
from platterpus.record_vendor_settings import VendorSettingsBlock, parse_vendor_settings
from platterpus.ripper_ending import DESCRIBES, STATE_NOT_READ, STATE_READ

if TYPE_CHECKING:  # the reader imports this module, so only its type is needed
    from platterpus.isrc_provenance import IsrcReading

#: The record's key, spelled once.
DRIVE_DECLARED_KEY: Final[str] = "drive_declared"

#: The four page controls, in the order the source writes them (``:375-376``).
PAGE_CONTROLS: Final[tuple[str, ...]] = ("current", "changeable", "default", "saved")
#: More than the source writes is kept up to this, the rest counted.
MAX_PAGE_CONTROLS: Final[int] = 8

#: ``CRIP_REPLY_MAX`` bytes as hex. A longer string is not a reply cyanrip kept,
#: and is refused (``bytes`` None, the reply ``unrecognised``) rather than cut,
#: because a cut reply would be a different declaration.
MAX_REPLY_HEX: Final[int] = 2 * 8192
_HEX: Final[re.Pattern[str]] = re.compile(r"(?:[0-9A-Fa-f]{2})*")
_MAX_LABEL_CHARS: Final[int] = 32

READ: Final[str] = "read"
NOT_PRESENT: Final[str] = "not_present"
NOT_STATED: Final[str] = "not_stated"
UNRECOGNISED: Final[str] = "unrecognised"
STATES: Final[frozenset[str]] = frozenset({READ, NOT_PRESENT, NOT_STATED, UNRECOGNISED})

#: Said in the report beside the replies, as the fork says it of them.
NOTE: Final[str] = (
    "What the drive declares when asked, not a measurement of what it does; "
    "nothing was written to the drive."
)


class ReplyBlock(TypedDict):
    """One SCSI reply as the record keeps it (schema 44)."""

    #: ``read`` or ``unrecognised`` (a field of the wrong type).
    state: str
    answered: bool | None
    length: int | None
    truncated: bool | None
    #: Upper-case hex, the bytes kept, from the first.
    bytes: str | None
    #: Whether ``truncated`` agrees with ``length`` and the bytes kept.
    agrees: bool | None


class CdReadFeatureBlock(TypedDict):
    """The CD Read feature (001Eh), read out of GET CONFIGURATION (schema 44)."""

    state: str
    found: bool | None
    bytes: str | None
    current: bool | None
    dap: bool | None
    c2_flags: bool | None
    cd_text: bool | None
    #: The four bits derived again from ``bytes`` and compared; None when absent.
    bits_agree_with_bytes: bool | None


class ModeSenseBlock(TypedDict):
    """One MODE SENSE (10) reply, all pages, under one page control."""

    page_control: str
    reply: ReplyBlock


class DriveDeclaredBlock(TypedDict):
    """``disc.drive_declared`` (schema 44), from the album pass's ``-j`` record."""

    describes: str
    #: The record's reading state (``ripper_ending.STATE_*``).
    state: str
    detail: str | None
    #: The key's own state: ``read`` / ``not_present`` / ``not_stated`` /
    #: ``unrecognised``. ``not_stated`` is a disc image or no drive opened; null
    #: when the record itself was not read, which ``state`` says why.
    declared_state: str | None
    note: str
    inquiry: ReplyBlock | None
    configuration: ReplyBlock | None
    cd_read_feature: CdReadFeatureBlock | None
    mode_sense_all_pages: list[ModeSenseBlock] | None
    mode_sense_not_kept: int
    #: The vendor's settings query (``record_vendor_settings``); null unless read.
    vendor_settings: VendorSettingsBlock | None


@dataclass(frozen=True)
class DriveDeclared:
    """The record's ``drive_declared``, read. Blocks are None unless ``read``."""

    state: str = NOT_PRESENT
    inquiry: ReplyBlock | None = None
    configuration: ReplyBlock | None = None
    cd_read_feature: CdReadFeatureBlock | None = None
    mode_sense: tuple[ModeSenseBlock, ...] = ()
    mode_sense_not_kept: int = 0
    vendor_settings: VendorSettingsBlock | None = None


def _bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _hex(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > MAX_REPLY_HEX:
        return None
    return value.upper() if _HEX.fullmatch(value) else None


def _reply(value: object) -> ReplyBlock | None:
    """One REPLY object, or None when the key is not an object. Never raises."""
    if not isinstance(value, Mapping):
        return None
    answered = _bool(value.get("answered"))
    raw = value.get("length")
    length = raw if type(raw) is int and raw >= 0 else None  # a bool is not a length
    truncated = _bool(value.get("truncated"))
    data = _hex(value.get("bytes"))
    whole = length is not None and truncated is not None and data is not None
    if answered is True:
        well_formed = whole
    elif answered is False:
        nulls = ("length", "truncated", "bytes")
        well_formed = all(value.get(key) is None for key in nulls)
    else:
        well_formed = False
    agrees: bool | None = None
    if answered is True and length is not None and data is not None:
        agrees = truncated == (length > len(data) // 2) if whole else None
    return {
        "state": READ if well_formed else UNRECOGNISED,
        "answered": answered,
        "length": length,
        "truncated": truncated,
        "bytes": data,
        "agrees": agrees,
    }


def _feature(value: object) -> CdReadFeatureBlock | None:
    """The ``cd_read_feature`` object, its bits checked against its bytes."""
    if not isinstance(value, Mapping):
        return None
    found = _bool(value.get("found"))
    data = _hex(value.get("bytes"))
    bits = {
        key: _bool(value.get(key)) for key in ("current", "dap", "c2_flags", "cd_text")
    }
    agree: bool | None = None
    if data is not None and len(data) >= 10:
        raw = bytes.fromhex(data)
        derived = {
            "current": bool(raw[2] & 0x01),
            "dap": bool(raw[4] & 0x80),
            "c2_flags": bool(raw[4] & 0x02),
            "cd_text": bool(raw[4] & 0x01),
        }
        agree = derived == bits
    stated_null = data is None and all(bit is None for bit in bits.values())
    well_formed = found is not None and (agree is True or stated_null)
    return {
        "state": READ if well_formed else UNRECOGNISED,
        "found": found,
        "bytes": data,
        "current": bits["current"],
        "dap": bits["dap"],
        "c2_flags": bits["c2_flags"],
        "cd_text": bits["cd_text"],
        "bits_agree_with_bytes": agree,
    }


def _mode_sense(value: object) -> tuple[tuple[ModeSenseBlock, ...], int]:
    if not isinstance(value, list):
        return (), 0
    kept: list[ModeSenseBlock] = []
    for item in value[:MAX_PAGE_CONTROLS]:
        reply = _reply(item)
        if reply is None:
            continue
        label = item.get("page_control") if isinstance(item, Mapping) else None
        control = (
            inbound_text.screen_line(label[:_MAX_LABEL_CHARS]).text
            if isinstance(label, str)
            else ""
        )
        if control not in PAGE_CONTROLS:
            reply = {**reply, "state": UNRECOGNISED}
        kept.append({"page_control": control, "reply": reply})
    return tuple(kept), max(0, len(value) - MAX_PAGE_CONTROLS)


def parse_drive_declared(data: Mapping[str, object]) -> DriveDeclared:
    """The record's top-level ``drive_declared``. Pure; never raises."""
    try:
        if DRIVE_DECLARED_KEY not in data:
            return DriveDeclared()
        value = data.get(DRIVE_DECLARED_KEY)
        if value is None:
            return DriveDeclared(state=NOT_STATED)
        if not isinstance(value, Mapping):
            return DriveDeclared(state=UNRECOGNISED)
        pages, not_kept = _mode_sense(value.get("mode_sense_all_pages"))
        inquiry = _reply(value.get("inquiry"))
        vendor = _reply(value.get("vendor_settings"))  # its REPLY is inline
        return DriveDeclared(
            state=READ,
            inquiry=inquiry,
            configuration=_reply(value.get("configuration")),
            cd_read_feature=_feature(value.get("cd_read_feature")),
            mode_sense=pages,
            mode_sense_not_kept=not_kept,
            vendor_settings=parse_vendor_settings(value, inquiry=inquiry, reply=vendor),
        )
    except (AttributeError, TypeError, ValueError):
        return DriveDeclared(state=UNRECOGNISED)


def report_block(reading: IsrcReading | None) -> DriveDeclaredBlock:
    """The report's ``disc.drive_declared`` (schema 44). Pure; never raises.

    ``reading`` is the album pass's record as
    :mod:`platterpus.isrc_provenance` read it; ``None`` is no reading at all.
    """
    state = reading.state if reading is not None else STATE_NOT_READ
    detail = reading.detail if reading is not None else ""
    declared = reading.drive_declared if reading is not None else DriveDeclared()
    listed = declared.state == READ
    return {
        "describes": DESCRIBES,
        "state": state,
        "detail": detail or None,
        # Null, never `not_present`, for a record not read: absence of the key
        # is a claim about a record we have.
        "declared_state": declared.state if state == STATE_READ else None,
        "note": NOTE,
        "inquiry": declared.inquiry,
        "configuration": declared.configuration,
        "cd_read_feature": declared.cd_read_feature,
        "mode_sense_all_pages": list(declared.mode_sense) if listed else None,
        "mode_sense_not_kept": declared.mode_sense_not_kept,
        "vendor_settings": declared.vendor_settings,
    }
