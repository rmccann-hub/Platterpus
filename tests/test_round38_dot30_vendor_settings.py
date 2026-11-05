"""`.30`'s vendor settings query, read and checked (the fork's ``5cc1c6b3``).

With ``--read-vendor-settings`` the fork sends one read-only vendor query, only to a
drive whose INQUIRY vendor its table names, and keeps the answer in the ``-j``
record's ``drive_declared.vendor_settings`` (the owner's word of 2026-11-05, *"Yes
do this"*, TASKS R137). **Every form here is taken from their tree at
``5cc1c6b3``, not from a lap's prose:**

* the six ``vendor_settings`` objects are the strings their unit test expects
  (``cyanrip@5cc1c6b3:tests/diagrecord.c:419-512``), rebuilt from the same bytes,
  since only a Pioneer drive answers and none has run it yet;
* the decode and the vendor match are checked against every case their own unit
  test pins (``cyanrip@5cc1c6b3:tests/drivecaps.c:361-472``);
* an image's record is their golden reference at ``5cc1c6b3``, byte for byte
  (``tests/fixtures/cyanrip_fork_diagnostics13_golden_5cc1c6b3.json``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import record_drive_declared as declared
from platterpus import record_vendor_settings as vendor
from platterpus.isrc_provenance import parse_isrcs
from platterpus.rip_report import build_report

_FIXTURES: Final[Path] = Path(__file__).parent / "fixtures"
_GOLDEN: Final[Path] = _FIXTURES / "cyanrip_fork_diagnostics13_golden_5cc1c6b3.json"

#: `tests/diagrecord.c:453-455`: a 36-byte INQUIRY naming PIONEER BDR-209D.
_INQ: Final[bytes] = bytes([0x05, 0x80, 0x00, 0x32, 31, 0, 0, 0]) + (
    b"PIONEER BD-RW   BDR-209D" + bytes(4)
)
_SOURCE: Final[str] = (
    "pioneer-optical@d2cbbf2:src/settings/f4.rs:92-94 "
    "(READ BUFFER, mode 02h, buffer F4h, 256 bytes)"
)


def _f4(*, b4: int = 1, b5: int = 8, b9: int = 1) -> bytes:
    """`tests/diagrecord.c:470-474`: a valid block, PureRead Master by default."""
    block = bytearray(256)
    block[0] = 1
    block[11:15] = b"\xff" * 4
    block[4], block[5], block[9] = b4, b5, b9
    return bytes(block)


def _answered(block: bytes, pureread: dict[str, Any] | None) -> dict[str, Any]:
    """`expect_vendor`'s answered string (`tests/diagrecord.c:434-440`)."""
    return {
        "requested": True, "query": "pioneer-f4", "source": _SOURCE,
        "cdb": "3C02F400000000010000", "answered": True, "length": 256,
        "truncated": False, "bytes": block.hex().upper(), "pureread": pureread,
    }  # fmt: skip


_NONE: Final[dict[str, Any]] = {
    "requested": True, "query": None, "source": None, "cdb": None, "answered": None,
    "length": None, "truncated": None, "bytes": None, "pureread": None,
}  # fmt: skip
_REFUSED: Final[dict[str, Any]] = {
    **_answered(b"", None), "answered": False, "length": None, "truncated": None,
    "bytes": None,
}  # fmt: skip


def _pr(support: str, mode: str | None, valid: bool = True) -> dict[str, Any]:
    return {"block_valid": valid, "support": support, "mode": mode}


def _read(value: object, inquiry: bytes = _INQ) -> vendor.VendorSettingsBlock:
    record = {
        "inquiry": {"answered": True, "length": len(inquiry), "truncated": False,
                    "bytes": inquiry.hex().upper()},
        "vendor_settings": value,
    }  # fmt: skip
    found = declared.parse_drive_declared({"drive_declared": record})
    assert found.state == declared.READ and found.vendor_settings is not None
    return found.vendor_settings


#: Each of `test_vendor_settings`'s records (`tests/diagrecord.c:451-512`), and
#: `test_drive_declared`'s requested-false line (`:562-565`).
_SHAPES: Final[dict[str, dict[str, Any]]] = {
    "no row for the drive": _NONE,
    "PureRead Master": _answered(_f4(), _pr("supported", "master")),
    "an unknown level": _answered(_f4(b5=7), _pr("supported", "not determined")),
    "unsupported": _answered(_f4(b9=0), _pr("unsupported", None)),
    "a zero-filled block": _answered(bytes(256), _pr("not determined", None, False)),
    "refused": _REFUSED,
}


@pytest.mark.parametrize(
    "what",
    [
        "no row for the drive", "PureRead Master", "an unknown level", "unsupported",
        "a zero-filled block", "refused",
    ],
)  # fmt: skip
def test_every_shape_diagrecord_expects_is_read_and_agrees(what: str) -> None:
    value = _SHAPES[what]
    # Their "no row" record (`:458-466`) is built beside the 36-byte PIONEER
    # INQUIRY, a pair the source cannot produce (`cyanrip_main.c:380-381` would
    # match the row), so here it sits beside an INQUIRY naming no vendor.
    found = _read(value, _INQ[:8] if value["query"] is None else _INQ)
    assert found["state"] == vendor.READ, what
    assert found["requested"] is True and found["query"] == value["query"]
    assert found["query_agrees_with_inquiry"] is True
    pureread = found["pureread"]
    if value["pureread"] is None:
        assert pureread is None
    else:
        assert pureread is not None and pureread["state"] == vendor.READ
        assert pureread["agrees_with_bytes"] is True
        assert (pureread["support"], pureread["mode"]) == (
            value["pureread"]["support"], value["pureread"]["mode"],
        )  # fmt: skip
    if value["query"] is None:
        assert found["reply"] is None and found["cdb"] is None
    else:
        assert found["reply"] is not None and found["cdb"] == "3C02F400000000010000"


def test_not_requested_is_every_field_null_and_agrees() -> None:
    found = _read({**_NONE, "requested": False})
    assert (found["state"], found["requested"]) == (vendor.READ, False)
    assert found["query_agrees_with_inquiry"] is True  # asked for nothing, sent nothing


def test_pureread_contradicting_its_own_bytes_says_so() -> None:
    found = _read(_answered(_f4(b9=0), _pr("supported", "master")))
    pureread = found["pureread"]
    assert pureread is not None and pureread["agrees_with_bytes"] is False
    assert (pureread["derived_support"], pureread["derived_mode"]) == (
        "unsupported",
        None,
    )
    assert pureread["state"] == found["state"] == vendor.UNRECOGNISED


def test_a_query_sent_to_another_vendors_drive_is_a_disagreement() -> None:
    plextor = _INQ[:8] + b"PLEXTOR " + _INQ[16:]
    assert (
        _read(_answered(_f4(), _pr("supported", "master")), plextor)[
            "query_agrees_with_inquiry"
        ]
        is False
    )
    # And the converse: a PIONEER drive, asked for, with no query recorded.
    assert _read(_NONE)["query_agrees_with_inquiry"] is False


def test_pureread_where_the_source_writes_none_is_unrecognised() -> None:
    assert _read({**_REFUSED, "pureread": _pr("supported", "master")})["state"] == (
        vendor.UNRECOGNISED
    )
    missing = _read(_answered(_f4(), None))
    assert missing["state"] == vendor.UNRECOGNISED and missing["pureread"] is None
    # A mode beside a support other than `supported` is not a shape they write.
    odd = _read(_answered(_f4(b9=0), _pr("unsupported", "master")))
    assert odd["pureread"] is not None and odd["pureread"]["state"] == "unrecognised"


def test_a_record_before_5cc1c6b3_says_not_present_never_no() -> None:
    found = declared.parse_drive_declared({"drive_declared": {"inquiry": None}})
    assert found.vendor_settings is not None
    assert found.vendor_settings["state"] == vendor.NOT_PRESENT
    assert found.vendor_settings["query_agrees_with_inquiry"] is None
    assert _read(None)["state"] == vendor.NOT_STATED
    assert _read("x")["state"] == vendor.UNRECOGNISED


def test_the_report_carries_it_and_an_image_carries_none() -> None:
    data: dict[str, Any] = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert data["cyanrip"]["version"] == "0.9.4-rc3+platterpus.30"
    image = declared.report_block(parse_isrcs(json.dumps(data)))
    assert image["declared_state"] == "not_stated" and image["vendor_settings"] is None
    data["drive_declared"] = {
        "inquiry": {"answered": True, "length": 36, "truncated": False,
                    "bytes": _INQ.hex().upper()},
        "vendor_settings": _answered(_f4(), _pr("supported", "master")),
    }  # fmt: skip
    block = declared.report_block(parse_isrcs(json.dumps(data)))
    report = build_report(None, disc={"drive_declared": block})
    carried = json.loads(json.dumps(report))["disc"]["drive_declared"][
        "vendor_settings"
    ]
    assert carried["pureread"]["mode"] == "master"
    assert carried["pureread"]["agrees_with_bytes"] is True
    assert carried["query_agrees_with_inquiry"] is True


# --- the two ports, against every case their unit test pins -------------------

#: `tests/drivecaps.c:411-426`: (b0, b1, tail FFh, b4, b5, b9, length,
#: block_valid, support, mode), each over a 5Ah-filled buffer.
_F4_CASES: Final[list[tuple[int, int, bool, int, int, int, int, bool, str, str | None]]] = [
    (1, 0, True, 1, 8, 1, 256, True, "supported", "master"),
    (1, 0, True, 0, 0, 1, 256, True, "supported", "standard"),
    (1, 0, True, 0, 77, 1, 256, True, "supported", "standard"),
    (1, 0, True, 1, 254, 1, 256, True, "supported", "perfect"),
    (1, 0, True, 1, 7, 1, 256, True, "supported", "not determined"),
    (1, 0, True, 255, 0, 1, 256, True, "supported", "not determined"),
    (1, 0, True, 2, 8, 1, 256, True, "supported", "not determined"),
    (1, 0, True, 1, 8, 0, 256, True, "unsupported", None),
    (1, 0, True, 1, 8, 2, 256, True, "not determined", None),
    (1, 0, True, 1, 8, 255, 256, True, "not determined", None),
    (255, 255, False, 1, 8, 1, 256, True, "supported", "master"),
    (0, 1, True, 1, 8, 1, 256, True, "supported", "master"),
    (1, 0, False, 1, 8, 1, 256, False, "not determined", None),
    (2, 0, True, 1, 8, 1, 256, False, "not determined", None),
    (1, 3, True, 1, 8, 1, 256, False, "not determined", None),
    (1, 0, True, 1, 8, 1, 255, False, "not determined", None),
]  # fmt: skip


@pytest.mark.parametrize("case", _F4_CASES)
def test_the_f4_decode_matches_every_case_drivecaps_pins(
    case: tuple[int, int, bool, int, int, int, int, bool, str, str | None],
) -> None:
    b0, b1, tail, b4, b5, b9, length, valid, support, mode = case
    block = bytearray([0x5A] * 256)
    block[0], block[1], block[4], block[5], block[9] = b0, b1, b4, b5, b9
    if tail:
        block[11:15] = b"\xff" * 4
    assert vendor.decode_pioneer_f4(bytes(block[:length])) == (valid, support, mode)


def test_the_f4_decode_refuses_what_holds_no_state() -> None:
    assert vendor.decode_pioneer_f4(bytes(256))[0] is False  # zero-filled
    assert vendor.decode_pioneer_f4(b"\xff" * 256) == (False, "not determined", None)
    for k in range(
        11, 15
    ):  # `tests/drivecaps.c:447-459`: any one of bytes 11 to 14 not FFh
        block = bytearray([0x5A] * 256)
        block[0], block[1], block[4], block[5], block[9] = 1, 0, 1, 8, 1
        block[11:15] = b"\xff" * 4
        block[k] = 0x5A
        assert vendor.decode_pioneer_f4(bytes(block))[0] is False, k


@pytest.mark.parametrize(
    ("name", "length", "row"),
    [  # `tests/drivecaps.c:366-374`
        (b"PIONEER ", 36, "pioneer-f4"), (b"PIONEER\0", 36, "pioneer-f4"),
        (b"PIONEER ", 16, "pioneer-f4"), (b"PIONEER ", 15, None),
        (b"PIONEERX", 36, None), (b"PIONEE  ", 36, None), (b"pioneer ", 36, None),
        (b"PLEXTOR ", 36, None), (b"        ", 36, None),
    ],
)  # fmt: skip
def test_the_vendor_match_matches_every_case_drivecaps_pins(
    name: bytes, length: int, row: str | None
) -> None:
    inquiry = bytes([0x05, 0x80, 0x00, 0x32, 31, 0, 0, 0]) + name + b"BD-RW   BDR-209D"
    assert vendor.row_for_inquiry(inquiry[:length]) == row


# --- never raises ----------------------------------------------------------------

_JSON: Final[Any] = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=12),
    lambda children: (
        st.lists(children, max_size=5)
        | st.dictionaries(st.text(max_size=12), children, max_size=5)
    ),
    max_leaves=25,
)
_KEYS: Final[list[str]] = [*_NONE]


@settings(max_examples=300, deadline=None)
@given(
    st.dictionaries(st.sampled_from(_KEYS), _JSON, max_size=9),
    st.binary(max_size=40),
)
def test_the_vendor_reader_never_raises(value: dict[str, Any], inquiry: bytes) -> None:
    found = _read(value, inquiry)
    assert found["state"] in vendor.STATES
    assert found["query_agrees_with_inquiry"] in (True, False, None)


@given(st.binary(max_size=300))
def test_the_f4_decode_never_raises(raw: bytes) -> None:
    valid, support, mode = vendor.decode_pioneer_f4(raw)
    assert support in vendor.SUPPORT_WORDS and (mode is None or mode in vendor.MODES)
    assert valid or (support, mode) == ("not determined", None)


# --- who sends the flag: the two round-38 rig scripts, once each; never an app rip ---

_RIG: Final[Path] = Path(__file__).resolve().parents[1] / "src/platterpus/rig_scripts"
_FLAG: Final[str] = "--read-vendor-settings"


@pytest.mark.parametrize("name", ["drivemode.txt", "drivespeed.txt"])
def test_the_first_rip_of_each_drive_script_asks_the_drive_once(name: str) -> None:
    from platterpus.uiscript.script import (
        args_as_preflight_sees_them,
        parse,
        sanitise_cyanrip_args,
    )

    steps = [s for s in parse((_RIG / name).read_text(encoding="utf-8"))]
    rips = [s for s in steps if s.verb == "cyanrip" and "-D" in s.args]
    assert len(rips) >= 12  # floor: the scripts' twelve and seventeen rips
    asking = [s for s in rips if _FLAG in s.args]
    assert asking == [rips[0]], f"{name}: the flag belongs on the first rip only"
    # The fork refuses it without a record (`cyanrip_main.c:3431-3436`).
    assert "(diagnostics)" in rips[0].args
    assert (
        sanitise_cyanrip_args(args_as_preflight_sees_them(list(rips[0].args))) is None
    )


def test_no_app_rip_sends_the_flag() -> None:
    """The app's opt-in setting is later (TASKS R137); until then no app rip asks."""
    # A string literal is what an argv is built from; prose names it in backticks.
    literal = re.compile(r"[\"']" + re.escape(_FLAG) + r"[\"']")
    src = Path(__file__).resolve().parents[1] / "src/platterpus"
    scanned = sorted(src.rglob("*.py"))
    assert len(scanned) > 100  # floor: the package, not an empty glob
    senders = [
        p.relative_to(src).as_posix()
        for p in scanned
        if literal.search(p.read_text(encoding="utf-8"))
    ]
    assert senders == [], senders
    contract = Path(__file__).resolve().parents[1] / "docs/cyanrip-consumer-contract.md"
    assert _FLAG not in contract.read_text(encoding="utf-8")
