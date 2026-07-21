"""Verify a release's minisign signature — the update *authenticity* gate.

Why this exists
---------------
The in-app updater (``update_install.py``) already verifies the download's
**SHA-256** against the release's published ``.sha256``. That proves *integrity*
(the bytes match what was published) but not *authenticity* (that a legitimate
party published them): a compromised release channel able to swap **both** the
AppImage and its ``.sha256`` would sail through. An Ed25519 signature made with
a key the maintainer holds **offline** — never in CI, so it can't be forged even
by a CI compromise — closes that gap. The maintainer signs each release with
``minisign``; this module verifies the ``.minisig`` against the public key baked
in below, and the updater refuses to install anything that fails (fail-closed).

Dormant until armed
-------------------
``PUBLIC_KEY_B64`` is empty until the maintainer bakes in their key. While it's
empty, :func:`signing_configured` is ``False`` and the updater keeps its
SHA-256-only behaviour — so shipping this code changes nothing until the key is
set. Baking in a key **arms** the fail-closed check, so the release that first
sets the key MUST also be the first to carry a ``.minisig`` asset (see
``docs/release-signing.md``).

Verify-only
-----------
No secret key ever touches this code. We use the well-maintained ``cryptography``
library for the Ed25519 primitive (the maintainer's chosen mechanism) and stdlib
``hashlib`` for the BLAKE2b prehash minisign uses on large files. Every function
here is pure and **never raises** — any malformed key/signature or verification
failure returns ``False``, which the caller treats as "reject" (fail-closed).

minisign format (the bytes we parse)
------------------------------------
A ``.minisig`` file is::

    untrusted comment: <arbitrary>
    <base64: sig_algorithm(2) + key_id(8) + signature(64)>
    trusted comment: <arbitrary>
    <base64: global_signature(64)>

``sig_algorithm`` is ``b"Ed"`` (signature over the raw file) or ``b"ED"``
(signature over ``BLAKE2b-512(file)`` — minisign's ``-H`` prehash mode, which we
recommend for the ~240 MB AppImage). We verify the **file signature** — the part
that authenticates the artifact. We deliberately do *not* verify the trailing
"global signature" over the trusted comment: it exists only to bind that comment,
and we never read the trusted comment, so it's not part of our threat model.
Keeping the parse to the single security-relevant line also avoids depending on
byte-exact trusted-comment concatenation we couldn't cross-check without the
minisign binary.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

log = logging.getLogger(__name__)

# ── The maintainer's minisign PUBLIC key ────────────────────────────────────
# Paste the base64 payload from the SECOND line of the `minisign.pub` produced
# by `minisign -G` (the line after "untrusted comment: …"). Leaving it EMPTY
# keeps release-signing OFF (SHA-256-only updates, unchanged). Setting it ARMS
# the fail-closed signature gate — see docs/release-signing.md before you do.
PUBLIC_KEY_B64: str = ""

# minisign signature-algorithm tags (first 2 bytes of the decoded signature).
_SIGALG_LEGACY: bytes = b"Ed"  # Ed25519 over the raw file
_SIGALG_PREHASHED: bytes = b"ED"  # Ed25519 over BLAKE2b-512(file) (minisign -H)

# A minisign public-key payload is exactly alg(2) + key_id(8) + pubkey(32).
_PUBKEY_LEN: int = 42
# A minisign file-signature payload is exactly alg(2) + key_id(8) + sig(64).
_SIG_LEN: int = 74
_BLAKE2B_DIGEST_SIZE: int = 64  # minisign prehashes with BLAKE2b-512
# Chunk size for hashing a large file off disk without loading it all in memory.
_HASH_CHUNK_BYTES: int = 1024 * 1024


def signing_configured() -> bool:
    """True once a maintainer public key is baked in (arms the fail-closed gate).

    While False, the updater must keep its SHA-256-only behaviour — the feature
    ships dormant so setting the key is the single, deliberate act that turns it
    on.
    """
    return bool(PUBLIC_KEY_B64.strip())


def _decode_public_key(public_key_b64: str) -> tuple[bytes, Ed25519PublicKey] | None:
    """Parse a minisign public-key base64 → (key_id, Ed25519 key). None if bad."""
    try:
        raw = base64.b64decode(public_key_b64.strip(), validate=True)
    except (binascii.Error, ValueError):
        return None
    # minisign public keys always carry the legacy "Ed" algo tag (the pubkey is
    # the same 32 bytes whether the maintainer later signs pure or prehashed).
    if len(raw) != _PUBKEY_LEN or raw[:2] != _SIGALG_LEGACY:
        return None
    key_id = raw[2:10]
    try:
        key = Ed25519PublicKey.from_public_bytes(raw[10:_PUBKEY_LEN])
    except ValueError:
        return None
    return key_id, key


def _parse_signature(signature_text: str) -> tuple[bytes, bytes, bytes] | None:
    """Parse a .minisig's file-signature line → (alg, key_id, signature).

    Robust to comment-line wording: the file signature is simply the first
    base64 line that decodes to exactly ``_SIG_LEN`` bytes whose algorithm tag
    starts with ``b"E"`` (the trailing global-signature line is 64 bytes, so
    there's no ambiguity). Returns None if no such line is present.
    """
    for line in signature_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        try:
            raw = base64.b64decode(candidate, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(raw) == _SIG_LEN and raw[:1] == b"E":
            return raw[:2], raw[2:10], raw[10:_SIG_LEN]
    return None


def _prepare(
    signature_text: str, public_key_b64: str
) -> tuple[bytes, bytes, Ed25519PublicKey] | None:
    """Shared parse + key-id match → (alg, signature, key). None on any problem."""
    decoded_key = _decode_public_key(public_key_b64)
    if decoded_key is None:
        log.warning("release-signing: the configured public key is malformed")
        return None
    key_id, key = decoded_key

    parsed_sig = _parse_signature(signature_text)
    if parsed_sig is None:
        log.warning("release-signing: the signature file is malformed")
        return None
    alg, sig_key_id, signature = parsed_sig

    if sig_key_id != key_id:
        # Not a security boundary (verifying with the wrong key already fails),
        # but it gives a precise "signed by a different key" diagnosis.
        log.warning("release-signing: signature key id does not match our key")
        return None
    if alg not in (_SIGALG_LEGACY, _SIGALG_PREHASHED):
        log.warning("release-signing: unknown signature algorithm %r", alg)
        return None
    return alg, signature, key


def _verify(
    alg: bytes, signature: bytes, key: Ed25519PublicKey, message: bytes
) -> bool:
    """Ed25519-verify ``signature`` over ``message`` (already prehashed if ED)."""
    try:
        key.verify(signature, message)
    except InvalidSignature:
        log.warning("release-signing: signature verification FAILED")
        return False
    return True


def verify_minisign(data: bytes, signature_text: str, public_key_b64: str) -> bool:
    """True iff ``data`` is authentically signed by ``public_key_b64``'s key.

    Pure and never raises — malformed input or a bad signature returns False.
    Loads ``data`` fully in memory; for the on-disk AppImage prefer
    :func:`verify_minisign_file`, which streams the prehash.
    """
    prepared = _prepare(signature_text, public_key_b64)
    if prepared is None:
        return False
    alg, signature, key = prepared
    message = (
        hashlib.blake2b(data, digest_size=_BLAKE2B_DIGEST_SIZE).digest()
        if alg == _SIGALG_PREHASHED
        else data
    )
    return _verify(alg, signature, key, message)


def verify_minisign_file(path: Path, signature_text: str, public_key_b64: str) -> bool:
    """Like :func:`verify_minisign` but reads ``path`` from disk efficiently.

    For a prehashed (``ED``) signature — the recommended mode for the large
    AppImage — the BLAKE2b digest is computed by streaming the file in chunks,
    so memory stays bounded. A legacy (``Ed``) signature needs the whole file as
    the Ed25519 message, so it's read fully (the download-size cap already
    bounds it). Never raises: an unreadable file returns False.
    """
    prepared = _prepare(signature_text, public_key_b64)
    if prepared is None:
        return False
    alg, signature, key = prepared
    try:
        if alg == _SIGALG_PREHASHED:
            hasher = hashlib.blake2b(digest_size=_BLAKE2B_DIGEST_SIZE)
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
                    hasher.update(chunk)
            message = hasher.digest()
        else:
            message = Path(path).read_bytes()
    except OSError as exc:
        log.warning("release-signing: could not read %s to verify: %s", path, exc)
        return False
    return _verify(alg, signature, key, message)
