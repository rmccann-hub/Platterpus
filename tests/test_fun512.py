"""Tests for platterpus.fun512 — cyanrip's log signature, checked without cyanrip (R16).

Pinned to the signed cyanrip logs in the tree (the fork's golden references and a
cancelled rip), so the port is checked against signatures cyanrip itself wrote.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import fun512

_FIXTURES = Path(__file__).parent / "fixtures"
_SIGNED = (
    "cyanrip_fork_golden_reference.log",
    "cyanrip_fork_golden_reference_r6b.log",
    "cyanrip_cancelled_at_track_one.log",
)


@pytest.mark.parametrize("name", _SIGNED)
def test_every_signed_log_in_the_tree_verifies(name: str) -> None:
    assert fun512.verify((_FIXTURES / name).read_bytes()) == fun512.VALID


@pytest.mark.parametrize("name", _SIGNED)
def test_one_flipped_bit_above_the_signature_fails(name: str) -> None:
    data = bytearray((_FIXTURES / name).read_bytes())
    data[len(data) // 3] ^= 0x01
    assert fun512.verify(bytes(data)) == fun512.MISMATCH


def test_text_after_the_signature_is_refused_and_line_endings_are_not() -> None:
    data = (_FIXTURES / _SIGNED[0]).read_bytes().rstrip(b"\r\n")
    assert fun512.verify(data) == fun512.VALID
    assert fun512.verify(data + b"\r\n\n") == fun512.VALID
    assert fun512.verify(data + b"\nappended") == fun512.TRAILING_DATA


def test_an_unsigned_text_says_so() -> None:
    assert fun512.verify(b"just a log\n") == fun512.NO_SIGNATURE


@given(st.binary(max_size=400))
def test_verify_never_raises(data: bytes) -> None:
    assert fun512.verify(data) in {
        fun512.VALID,
        fun512.NO_SIGNATURE,
        fun512.TRAILING_DATA,
        fun512.MISMATCH,
    }
    assert fun512.verify(data + fun512.MARK + data[:20]) is not None


#: Every signed log in the tree was signed at index 0 (measured 2026-10-16), so
#: those tests cannot see the index. This pins the port's output at a non-zero
#: index for a fixed digest. The values are the port's own, so they pin the
#: index's effect (``0x81 + index``, `cyanrip@5c564042:src/fun512.c`), not an
#: independent witness of it; index 0's value is the one cyanrip's logs check.
_PIN_TEXT = b"Platterpus fun512 index pin\n"
_PIN_AT_0 = "t9dXAiRtGABeIZdeSiNgY.j0GmHKTXdzX3AFKjoP2zJC1eOW2TiZhPQ7ZJqP.7VIu_MN1cY6RglAsTKSkZ4XcA"
_PIN_AT_7 = "t95eCy1kEQlXKJ5XQyppauH9E2jDRH56VnkMIzMG0jtL3Oqf0DGQjf0ybZOG8rxBsvoE3M8zTwBJuDubmJceeQ"


def test_the_index_changes_the_signature_and_any_of_the_sixteen_verifies() -> None:
    import hashlib

    digest = hashlib.sha512(_PIN_TEXT).digest()
    assert fun512.fun512(digest, 0) == _PIN_AT_0
    assert fun512.fun512(digest, 7) == _PIN_AT_7
    assert (
        fun512.verify(_PIN_TEXT + fun512.MARK + _PIN_AT_7.encode() + b"\n")
        == fun512.VALID
    )
