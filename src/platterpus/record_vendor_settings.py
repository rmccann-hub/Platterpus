# SPDX-License-Identifier: GPL-3.0-only
"""The drive's own settings, asked with its vendor's read-only query (``.30``).

**Why this exists.** Whether the reference drive was in PureRead Standard,
Master or Perfect has only been known from what Pioneer's Windows utility showed
the owner. The fork's ``.30`` at ``5cc1c6b3`` can ask the drive itself: with
``--read-vendor-settings`` (long-only, default off, and refused without
``--diagnostics``, ``cyanrip@5cc1c6b3:src/cyanrip_main.c:3216-3217`` and
``:3431-3436``) it sends one read-only vendor query from a table, **only to a
drive whose INQUIRY vendor a row names** (``:373-386``), and keeps the answer in
the record's ``drive_declared.vendor_settings``. The owner's word of 2026-11-05,
*"Yes do this"*, is TASKS R137.

**The shape, from their source** (``cyanrip@5cc1c6b3:src/diagnostics.c:371-411``;
pinned by their ``tests/diagrecord.c:419-512``)::

    "vendor_settings": {"requested": bool,
      "query": str|null, "source": str|null, "cdb": hex|null,
      "answered", "length", "truncated", "bytes",          (a REPLY, inline)
      "pureread": null | {"block_valid": bool,
                          "support": "supported"|"unsupported"|"not determined",
                          "mode": str|null}}

``query`` null means no row named the drive, so nothing was sent and every
field after ``requested`` is null (``:385-389``). ``pureread`` is set only for
the ``pioneer-f4`` row's answered reply (``:400-403``); ``mode`` only where
``support`` is ``supported``, then ``"not determined"`` for a mode no one has
named (``:408-411``).

**Derived, not taken.** Two of the record's claims are checked against bytes
in the same record: the row against the INQUIRY's own vendor bytes, ported from
``crip_vendor_query_for`` (``cyanrip@5cc1c6b3:src/drive_caps.c:197-212``), as
``query_agrees_with_inquiry``, which is the owner's condition; and PureRead
against the reply's bytes, ported from ``crip_pioneer_f4_decode`` (``:214-242``),
as ``pureread.agrees_with_bytes``. Each None when there is nothing to compare.
Tri-state as the record is: ``not determined`` is never read as unsupported.
Pure, Qt-free, never raises; called by
:func:`platterpus.record_drive_declared.parse_drive_declared`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Final, TypedDict

from platterpus import inbound_text

if TYPE_CHECKING:  # that module calls this one, so only its type is needed here
    from platterpus.record_drive_declared import ReplyBlock

#: The key inside ``drive_declared``, spelled once.
VENDOR_SETTINGS_KEY: Final[str] = "vendor_settings"

READ: Final[str] = "read"
NOT_PRESENT: Final[str] = "not_present"
NOT_STATED: Final[str] = "not_stated"
UNRECOGNISED: Final[str] = "unrecognised"
STATES: Final[frozenset[str]] = frozenset({READ, NOT_PRESENT, NOT_STATED, UNRECOGNISED})

#: The fork's table, row id to (INQUIRY vendor, CDB as hex)
#: (``cyanrip@5cc1c6b3:src/drive_caps.c:186-195``). A row we do not know is
#: never called a disagreement: their table may have grown.
PIONEER_F4: Final[str] = "pioneer-f4"
VENDOR_ROWS: Final[Mapping[str, tuple[str, str]]] = {
    PIONEER_F4: ("PIONEER", "3C02F400000000010000"),
}
#: Pioneer's settings block is 256 bytes (the row's ``alloc``, ``:193``).
F4_BLOCK_BYTES: Final[int] = 256

SUPPORTED: Final[str] = "supported"
UNSUPPORTED: Final[str] = "unsupported"
NOT_DETERMINED: Final[str] = "not determined"  # the record's own spelling
SUPPORT_WORDS: Final[frozenset[str]] = frozenset(
    {SUPPORTED, UNSUPPORTED, NOT_DETERMINED}
)
#: ``CripPureRead.mode`` (``cyanrip@5cc1c6b3:src/drive_caps.h:177``), and the
#: record's word for none of them (``diagnostics.c:410``).
MODES: Final[frozenset[str]] = frozenset(
    {"standard", "master", "perfect", NOT_DETERMINED}
)

_MAX_TEXT: Final[int] = 512
_MAX_CDB_HEX: Final[int] = 32
_HEX: Final[re.Pattern[str]] = re.compile(r"(?:[0-9A-Fa-f]{2})*")
_REPLY_KEYS: Final[tuple[str, ...]] = ("answered", "length", "truncated", "bytes")


class PureReadBlock(TypedDict):
    """``pureread`` as the record states it, and as we derive it from the bytes."""

    #: ``read`` or ``unrecognised`` (a field of the wrong type or an unknown word).
    state: str
    block_valid: bool | None
    support: str | None
    mode: str | None
    #: The same three, re-derived from the reply's bytes; None without bytes.
    derived_block_valid: bool | None
    derived_support: str | None
    derived_mode: str | None
    #: Whether the record's three equal the derived three; None without bytes.
    agrees_with_bytes: bool | None


class VendorSettingsBlock(TypedDict):
    """``disc.drive_declared.vendor_settings`` (schema 44, an addition)."""

    #: ``read`` / ``not_present`` (a record from before ``5cc1c6b3``) /
    #: ``not_stated`` (null) / ``unrecognised`` (a wrong type, or the record
    #: contradicting its own shape).
    state: str
    requested: bool | None
    query: str | None
    source: str | None
    cdb: str | None
    #: The vendor query's reply; None when no query was sent.
    reply: ReplyBlock | None
    pureread: PureReadBlock | None
    #: Whether ``query`` is the row the INQUIRY's vendor bytes name; None when
    #: not determinable (no INQUIRY bytes, or a row we do not know).
    query_agrees_with_inquiry: bool | None


def _bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return inbound_text.screen_line(value[:_MAX_TEXT]).text


def decode_pioneer_f4(raw: bytes) -> tuple[bool, str, str | None]:
    """``(block_valid, support, mode)`` from Pioneer's settings block. Never raises.

    A line-for-line port of ``crip_pioneer_f4_decode``
    (``cyanrip@5cc1c6b3:src/drive_caps.c:214-242``), so the record's
    ``pureread`` can be checked against its own bytes; ``mode`` is spelled as
    ``diagnostics.c:408-411`` writes it, ``"not determined"`` for a supported
    PureRead at an unnamed level and None where it is not supported.
    """
    if len(raw) < F4_BLOCK_BYTES:
        return False, NOT_DETERMINED, None
    block = raw[:F4_BLOCK_BYTES]
    all_ff = all(byte == 0xFF for byte in block)
    sentinel = block[0] == 0xFF and block[1] == 0xFF
    feature = (
        (block[0] <= 1 or block[0] == 0xFF)
        and (block[1] <= 1 or block[1] == 0xFF)
        and block[11:15] == b"\xff\xff\xff\xff"
    )
    if (not sentinel and not feature) or all_ff:
        return False, NOT_DETERMINED, None
    support = {1: SUPPORTED, 0: UNSUPPORTED}.get(block[9], NOT_DETERMINED)
    if support != SUPPORTED:
        return True, support, None
    if block[4] == 0:
        return True, support, "standard"
    named = {8: "master", 254: "perfect"}.get(block[5]) if block[4] == 1 else None
    return True, support, named or NOT_DETERMINED


def row_for_inquiry(inquiry: bytes) -> str | None:
    """The table row INQUIRY's vendor bytes name, or None. Never raises.

    Ported from ``crip_vendor_query_for`` (``cyanrip@5cc1c6b3:src/drive_caps.c:
    197-212``): bytes 8 to 15, trailing spaces and NULs dropped, matched exactly;
    a reply too short to hold them matches nothing.
    """
    if len(inquiry) < 16:
        return None
    vendor = inquiry[8:16].rstrip(b" \x00")
    for row, (name, _cdb) in VENDOR_ROWS.items():
        if vendor == name.encode("ascii"):
            return row
    return None


def _pureread(value: object, data: str | None) -> PureReadBlock | None:
    if not isinstance(value, Mapping):
        return None
    valid = _bool(value.get("block_valid"))
    support = _text(value.get("support"))
    mode = _text(value.get("mode"))
    well_formed = (
        valid is not None
        and support in SUPPORT_WORDS
        and (mode in MODES if support == SUPPORTED else value.get("mode") is None)
    )
    derived: tuple[bool, str, str | None] | None = None
    if data is not None:
        derived = decode_pioneer_f4(bytes.fromhex(data))
    agrees = None if derived is None else derived == (valid, support, mode)
    return {
        "state": READ if well_formed and agrees is not False else UNRECOGNISED,
        "block_valid": valid,
        "support": support,
        "mode": mode,
        "derived_block_valid": derived[0] if derived else None,
        "derived_support": derived[1] if derived else None,
        "derived_mode": derived[2] if derived else None,
        "agrees_with_bytes": agrees,
    }


def _inquiry_row(
    requested: bool | None, inquiry: ReplyBlock | None
) -> tuple[bool, str | None]:
    """``(determinable, row)``: the row the source would have chosen."""
    if requested is False:
        return True, None  # not asked for: no row is chosen (cyanrip_main.c:378)
    if requested is None or inquiry is None or inquiry["answered"] is None:
        return False, None
    if inquiry["answered"] is False:
        return True, None  # an unanswered INQUIRY names nothing (:378)
    if inquiry["bytes"] is None:
        return False, None
    return True, row_for_inquiry(bytes.fromhex(inquiry["bytes"]))


def parse_vendor_settings(
    declared: Mapping[str, object],
    *,
    inquiry: ReplyBlock | None,
    reply: ReplyBlock | None,
) -> VendorSettingsBlock:
    """``drive_declared.vendor_settings``, read and checked. Pure; never raises.

    ``inquiry`` is the record's INQUIRY reply and ``reply`` the vendor object
    read as a REPLY, both by :mod:`platterpus.record_drive_declared`'s one reply
    reader, so a vendor reply is judged exactly as every other reply is.
    """
    block: VendorSettingsBlock = {
        "state": NOT_PRESENT,
        "requested": None,
        "query": None,
        "source": None,
        "cdb": None,
        "reply": None,
        "pureread": None,
        "query_agrees_with_inquiry": None,
    }
    try:
        if VENDOR_SETTINGS_KEY not in declared:
            return block
        value = declared.get(VENDOR_SETTINGS_KEY)
        if not isinstance(value, Mapping):
            block["state"] = NOT_STATED if value is None else UNRECOGNISED
            return block
        requested = _bool(value.get("requested"))
        query = _text(value.get("query"))
        raw_cdb = value.get("cdb")
        cdb = (
            raw_cdb.upper()
            if isinstance(raw_cdb, str)
            and len(raw_cdb) <= _MAX_CDB_HEX
            and _HEX.fullmatch(raw_cdb)
            else None
        )
        kept = reply if query is not None else None
        data = kept["bytes"] if kept is not None and kept["state"] == READ else None
        answered = query == PIONEER_F4 and kept is not None and kept["answered"] is True
        pureread = _pureread(value.get("pureread"), data if answered else None)
        if query is not None:
            row = VENDOR_ROWS.get(query)
            shape = (
                requested is True
                and kept is not None
                and kept["state"] == READ
                and (row is None or cdb == row[1])
                and (pureread is not None) == answered
                and (pureread is None or pureread["state"] == READ)
            )
        else:
            nulls = ("source", "cdb", *_REPLY_KEYS, "pureread")
            shape = requested is not None and all(value.get(k) is None for k in nulls)
        known, expected = _inquiry_row(requested, inquiry)
        agrees: bool | None = None
        if known and (query is None or query in VENDOR_ROWS):
            agrees = expected == query
        return {
            "state": READ if shape else UNRECOGNISED,
            "requested": requested,
            "query": query,
            "source": _text(value.get("source")),
            "cdb": cdb,
            "reply": kept,
            "pureread": pureread,
            "query_agrees_with_inquiry": agrees,
        }
    except (AttributeError, TypeError, ValueError):
        block["state"] = UNRECOGNISED
        return block
