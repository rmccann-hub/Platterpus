"""Tests for the release-signature verifier (update_signing.py).

No minisign binary is needed: we construct spec-accurate minisign public keys
and .minisig signatures with `cryptography` itself (we control both sides), then
assert the verifier accepts a good signature and REJECTS every tampering — a
wrong key, a flipped byte, a mismatched key id, a corrupt/absent signature — and
never raises on junk. Both minisign algorithms are covered: legacy `Ed` (over
the raw file) and prehashed `ED` (over BLAKE2b-512, minisign's -H mode).
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from platterpus import update_signing
from platterpus.update_signing import (
    signing_configured,
    verify_minisign,
    verify_minisign_file,
)

_DATA = b"pretend this is a 240 MB AppImage" * 100
_KEY_ID = b"\x01\x02\x03\x04\x05\x06\x07\x08"


def _public_key_b64(private: Ed25519PrivateKey, key_id: bytes = _KEY_ID) -> str:
    """The base64 payload of a minisign public key: b"Ed" + key_id(8) + pub(32)."""
    from cryptography.hazmat.primitives import serialization

    pub_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(b"Ed" + key_id + pub_raw).decode("ascii")


def _minisig(
    private: Ed25519PrivateKey,
    data: bytes,
    *,
    prehashed: bool = False,
    key_id: bytes = _KEY_ID,
) -> str:
    """A spec-accurate .minisig for `data` signed by `private`."""
    if prehashed:
        alg = b"ED"
        message = hashlib.blake2b(data, digest_size=64).digest()
    else:
        alg = b"Ed"
        message = data
    signature = private.sign(message)
    sig_payload = base64.b64encode(alg + key_id + signature).decode("ascii")
    # A real .minisig also carries a trusted-comment + global-signature pair; we
    # include a plausible-looking global line so the parser must pick the right
    # (74-byte) line, not just the first base64 it sees.
    global_line = base64.b64encode(b"\x00" * 64).decode("ascii")
    return (
        "untrusted comment: signature from minisign secret key\n"
        f"{sig_payload}\n"
        "trusted comment: timestamp:1 file:platterpus-x86_64.AppImage\n"
        f"{global_line}\n"
    )


# --- signing_configured ------------------------------------------------------


def test_signing_not_configured_by_default() -> None:
    # Shipped dormant: the baked-in key is empty until the maintainer sets it.
    assert update_signing.PUBLIC_KEY_B64 == ""
    assert signing_configured() is False


def test_signing_configured_true_when_key_present(monkeypatch) -> None:
    monkeypatch.setattr(update_signing, "PUBLIC_KEY_B64", "abc123")
    assert signing_configured() is True


# --- the happy paths ---------------------------------------------------------


def test_valid_legacy_signature_verifies() -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    assert verify_minisign(_DATA, _minisig(key, _DATA), pub) is True


def test_valid_prehashed_signature_verifies() -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    sig = _minisig(key, _DATA, prehashed=True)
    assert verify_minisign(_DATA, sig, pub) is True


def test_file_variant_verifies_both_algorithms(tmp_path: Path) -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    appimage = tmp_path / "app.AppImage"
    appimage.write_bytes(_DATA)
    assert verify_minisign_file(appimage, _minisig(key, _DATA), pub) is True
    assert (
        verify_minisign_file(appimage, _minisig(key, _DATA, prehashed=True), pub)
        is True
    )


# --- the tampering paths (all must REJECT, none may raise) -------------------


def test_flipped_file_byte_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    sig = _minisig(key, _DATA)
    tampered = bytearray(_DATA)
    tampered[0] ^= 0x01
    assert verify_minisign(bytes(tampered), sig, pub) is False


def test_signature_from_a_different_key_is_rejected() -> None:
    signer = Ed25519PrivateKey.generate()
    attacker_view_pub = _public_key_b64(Ed25519PrivateKey.generate())
    # Same key_id so it passes the id check but fails the crypto — the real gate.
    sig = _minisig(signer, _DATA)
    assert verify_minisign(_DATA, sig, attacker_view_pub) is False


def test_mismatched_key_id_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key, key_id=_KEY_ID)
    sig = _minisig(key, _DATA, key_id=b"\x09\x09\x09\x09\x09\x09\x09\x09")
    assert verify_minisign(_DATA, sig, pub) is False


def test_prehashed_signature_verified_against_raw_message_fails() -> None:
    # Guards the alg branch: an ED signature must be checked against the BLAKE2b
    # digest, never the raw bytes (and vice-versa).
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    # Sign the prehash but claim legacy alg → the verifier hashes-or-not by the
    # tag in the sig, so this specific corruption is caught as a bad signature.
    prehash = hashlib.blake2b(_DATA, digest_size=64).digest()
    signature = key.sign(prehash)
    sig_payload = base64.b64encode(b"Ed" + _KEY_ID + signature).decode("ascii")
    forged = f"untrusted comment: x\n{sig_payload}\ntrusted comment: y\n{base64.b64encode(b'0' * 64).decode()}\n"
    assert verify_minisign(_DATA, forged, pub) is False


# --- malformed / junk input (never raises) -----------------------------------


def test_empty_signature_text_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    assert verify_minisign(_DATA, "", _public_key_b64(key)) is False


def test_garbage_signature_text_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    junk = "untrusted comment: x\nnot valid base64!!!\ntrusted comment: y\n@@@\n"
    assert verify_minisign(_DATA, junk, _public_key_b64(key)) is False


def test_malformed_public_key_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    for bad_pub in ("", "not-base64!!!", base64.b64encode(b"short").decode()):
        assert verify_minisign(_DATA, _minisig(key, _DATA), bad_pub) is False


def test_wrong_length_signature_payload_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    short = base64.b64encode(b"Ed" + _KEY_ID + b"\x00" * 10).decode("ascii")
    sig = f"untrusted comment: x\n{short}\ntrusted comment: y\n"
    assert verify_minisign(_DATA, sig, pub) is False


def test_unknown_algorithm_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    # 74-byte payload (right length) but an algorithm tag we don't accept.
    payload = base64.b64encode(b"Zz" + _KEY_ID + b"\x00" * 64).decode("ascii")
    sig = f"untrusted comment: x\n{payload}\ntrusted comment: y\n"
    assert verify_minisign(_DATA, sig, pub) is False


def test_verify_file_on_missing_path_is_rejected(tmp_path: Path) -> None:
    key = Ed25519PrivateKey.generate()
    pub = _public_key_b64(key)
    missing = tmp_path / "nope.AppImage"
    assert verify_minisign_file(missing, _minisig(key, _DATA), pub) is False
