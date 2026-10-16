# SPDX-License-Identifier: GPL-3.0-only
"""Verify a cyanrip log's ``Log FUN512:`` signature without cyanrip (TASKS R16).

**Why this exists.** HR-2 point 9 says self-verifying logs are verified BEFORE
anything is replaced in them, and the result recorded with both hashes. cyanrip
does that with ``--verify-log`` (``-Y``), which needs the binary in its
container. Filing a run in a session that has no cyanrip used a port written in
the scratchpad for the purpose; this is that port, committed and pinned to signed
logs in the tree.

**What it computes**, from ``cyanrip@5c564042:src/fun512.c``: the SHA-512 of
every byte before the ``Log FUN512:`` line; that digest XORed with ``0x81 + i``
and then each byte XORed with every other; base64 without padding, with ``/``
as ``_`` and ``+`` as ``.``. The signature is valid when it equals that string
for some ``i`` in 0 to 15. Only line endings may follow the signature.

Pure, Qt-free, and never raises: every input gets a verdict.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Final

MARK: Final[bytes] = b"Log FUN512: "

VALID: Final[str] = "valid"
NO_SIGNATURE: Final[str] = "no_signature"
TRAILING_DATA: Final[str] = "trailing_data"
MISMATCH: Final[str] = "mismatch"

#: How many index values cyanrip may have signed with.
INDICES: Final[int] = 16


def fun512(digest: bytes, index: int) -> str:
    """The signature string for a SHA-512 ``digest`` at ``index``."""
    mixed = bytearray(digest)
    for j in range(len(mixed)):
        mixed[j] ^= (0x81 + index) & 0xFF
    for j in range(len(mixed)):
        for k in range(len(mixed)):
            if j != k:
                mixed[j] ^= mixed[k]
    text = base64.b64encode(bytes(mixed)).decode("ascii").rstrip("=")
    return text.replace("/", "_").replace("+", ".")


def verify(data: bytes) -> str:
    """One of :data:`VALID`, :data:`NO_SIGNATURE`, :data:`TRAILING_DATA`,
    :data:`MISMATCH`. Never raises."""
    at = data.rfind(MARK)
    if at < 0:
        return NO_SIGNATURE
    rest = data[at + len(MARK) :]
    end = next((i for i, b in enumerate(rest) if b in (10, 13)), len(rest))
    if rest[end:].strip(b"\r\n"):
        return TRAILING_DATA
    claimed = rest[:end].decode("ascii", errors="replace")
    digest = hashlib.sha512(data[:at]).digest()
    if any(fun512(digest, i) == claimed for i in range(INDICES)):
        return VALID
    return MISMATCH
