"""Tests for the in-app update installer (update_install.py).

Driven through a fake opener — no network. The contract under test: the
published .sha256 gates the install (a corrupt download never replaces
anything), the swap is atomic via a .part file, and every failure path
cleans up after itself.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from platterpus.update_install import (
    UpdateInstallError,
    asset_url,
    download_and_install,
)

_PAYLOAD = b"new appimage bytes" * 1000


class _FakeResponse:
    """Stands in for urllib's response: read(n) streaming + context manager."""

    def __init__(self, body: bytes, content_length: bool = True) -> None:
        self._body = body
        self._pos = 0
        self.headers = {"Content-Length": str(len(body))} if content_length else {}

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            n = len(self._body)
        chunk = self._body[self._pos : self._pos + n]
        self._pos += n
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _opener(payload: bytes = _PAYLOAD, sha: str | None = None):
    """An opener serving the AppImage and its .sha256 (correct by default)."""
    digest = sha if sha is not None else hashlib.sha256(payload).hexdigest()

    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(f"{digest}  platterpus-x86_64.AppImage\n".encode())
        return _FakeResponse(payload)

    return open_url


def test_asset_url_points_at_the_release_tag() -> None:
    url = asset_url("0.2.3")
    assert "/releases/download/v0.2.3/platterpus-x86_64.AppImage" in url


def test_success_installs_atomically_and_is_executable(tmp_path: Path) -> None:
    seen: list[float] = []
    result = download_and_install(
        "0.2.3", dest_dir=tmp_path, progress=seen.append, opener=_opener()
    )

    assert result == tmp_path / "platterpus-x86_64.AppImage"
    assert result.read_bytes() == _PAYLOAD
    assert result.stat().st_mode & 0o111  # executable
    assert not (tmp_path / ".platterpus-update.part").exists()  # no leftovers
    assert seen and seen[-1] == pytest.approx(100.0)  # progress reached 100%


def test_status_reports_each_phase(tmp_path: Path) -> None:
    """The UI relies on phase labels so the quick post-download steps don't
    look like a freeze (real-user report 2026-06-13). Verify + install must
    each announce themselves, in order, after downloading."""
    phases: list[str] = []
    download_and_install(
        "0.2.3", dest_dir=tmp_path, status=phases.append, opener=_opener()
    )

    joined = " | ".join(phases)
    assert "Downloading" in joined
    assert "Verifying" in joined
    assert "Installing" in joined
    # Order: download before verify before install.
    download_i = next(i for i, p in enumerate(phases) if "Downloading" in p)
    verify_i = next(i for i, p in enumerate(phases) if "Verifying" in p)
    install_i = next(i for i, p in enumerate(phases) if "Installing" in p)
    assert download_i < verify_i < install_i


def test_checksum_mismatch_never_installs(tmp_path: Path) -> None:
    """The integrity gate: a corrupted/tampered download is discarded and
    the existing install is untouched."""
    existing = tmp_path / "platterpus-x86_64.AppImage"
    existing.write_bytes(b"the old version")
    bad = _opener(sha="0" * 64)  # plausible-looking but wrong checksum

    with pytest.raises(UpdateInstallError, match="checksum"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=bad)

    assert existing.read_bytes() == b"the old version"  # untouched
    assert not (tmp_path / ".platterpus-update.part").exists()  # cleaned up


def test_sha256_sidecar_read_is_bounded(tmp_path: Path) -> None:
    """BUG-3: the .sha256 read is capped (_MAX_SHA256_BYTES), so a hostile mirror
    can't stream a multi-GB body into memory before the length check. We assert
    the read was called WITH the cap, not the unbounded read() it used to be."""
    import platterpus.update_install as ui

    reads: list[int] = []

    class _Recording(_FakeResponse):
        def read(self, n: int = -1) -> bytes:
            reads.append(n)
            return super().read(n)

    def open_url(url: str):
        if url.endswith(".sha256"):
            # A valid-length digest so we get past the len==64 gate; it won't
            # match the payload, but the (bounded) sidecar read happens first.
            return _Recording(f"{'a' * 64}  x\n".encode())
        return _FakeResponse(_PAYLOAD)

    with pytest.raises(UpdateInstallError):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)
    assert reads and reads[0] == ui._MAX_SHA256_BYTES


def test_malformed_published_checksum_aborts_before_download(
    tmp_path: Path,
) -> None:
    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(b"not-a-checksum\n")
        raise AssertionError("the big download must not start")

    with pytest.raises(UpdateInstallError, match="malformed"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)


def test_cancel_mid_download_cleans_up(tmp_path: Path) -> None:
    with pytest.raises(UpdateInstallError, match="cancelled"):
        download_and_install(
            "0.2.3", dest_dir=tmp_path, cancelled=lambda: True, opener=_opener()
        )
    assert not (tmp_path / ".platterpus-update.part").exists()
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_download_rejects_oversized_content_length(tmp_path: Path) -> None:
    """Regression: a Content-Length larger than the max expected AppImage size
    is refused up front — a hostile/misbehaving server can't stream an endless
    body onto the disk before the post-download checksum gate can reject it."""
    payload = b"x" * 100
    digest = hashlib.sha256(payload).hexdigest()

    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(f"{digest}  x\n".encode())
        resp = _FakeResponse(payload)
        resp.headers["Content-Length"] = str(2 * 1024**3)  # 2 GiB, over the cap
        return resp

    with pytest.raises(UpdateInstallError, match="larger than expected"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)
    assert not (tmp_path / ".platterpus-update.part").exists()


def test_download_aborts_when_stream_exceeds_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: even with no (or a lying) Content-Length, the running byte
    count is bounded so a server can't stream forever and fill the disk."""
    import platterpus.update_install as ui

    monkeypatch.setattr(ui, "_MAX_DOWNLOAD_BYTES", 50)
    payload = b"x" * 500  # exceeds the (patched) 50-byte cap
    digest = hashlib.sha256(payload).hexdigest()

    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(f"{digest}  x\n".encode())
        return _FakeResponse(payload, content_length=False)  # no header to trust

    with pytest.raises(UpdateInstallError, match="maximum expected size"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)
    assert not (tmp_path / ".platterpus-update.part").exists()


def test_network_failure_raises_presentable_error(tmp_path: Path) -> None:
    def open_url(url: str):
        raise OSError("connection reset")

    with pytest.raises(UpdateInstallError, match="checksum"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)


def test_download_stream_failure_cleans_up_and_raises(tmp_path: Path) -> None:
    # The checksum fetch succeeds, but the AppImage stream dies mid-read. The
    # generic failure path must wrap it as a presentable error and delete the
    # partial file — never leaving a half-download or touching the install.
    class _ExplodingResponse(_FakeResponse):
        def read(self, n: int = -1) -> bytes:
            raise OSError("stream reset")

    def open_url(url: str):
        if url.endswith(".sha256"):
            digest = hashlib.sha256(_PAYLOAD).hexdigest()
            return _FakeResponse(f"{digest}  x\n".encode())
        return _ExplodingResponse(_PAYLOAD)

    with pytest.raises(UpdateInstallError, match="download failed"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)

    assert not (tmp_path / ".platterpus-update.part").exists()
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


# --- Signature authenticity gate (fail-closed) -------------------------------
# These arm the gate by monkeypatching a real test key into
# update_signing.PUBLIC_KEY_B64, then serve a matching (or missing/bad) .minisig
# through the fake opener. The contract: with a key configured, ONLY a
# correctly-signed release installs; a missing or invalid signature is refused
# and cleaned up. With no key configured, the .minisig is never even fetched.


def _test_key_and_sig(payload: bytes = _PAYLOAD):
    """A fresh Ed25519 key + its minisign pubkey b64 + a valid .minisig for
    `payload` (prehashed ED, the mode we recommend for the large AppImage)."""
    import base64
    import hashlib as _hashlib

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    key_id = b"\x11\x22\x33\x44\x55\x66\x77\x88"
    pub_raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(b"Ed" + key_id + pub_raw).decode("ascii")
    signature = key.sign(_hashlib.blake2b(payload, digest_size=64).digest())
    sig_payload = base64.b64encode(b"ED" + key_id + signature).decode("ascii")
    global_line = base64.b64encode(b"\x00" * 64).decode("ascii")
    minisig = (
        f"untrusted comment: minisign\n{sig_payload}\n"
        f"trusted comment: file:platterpus-x86_64.AppImage\n{global_line}\n"
    )
    return pub_b64, minisig


def _signing_opener(payload: bytes, minisig: str | None):
    """Opener serving the AppImage + .sha256 + (optionally) a .minisig."""
    digest = hashlib.sha256(payload).hexdigest()

    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(f"{digest}  platterpus-x86_64.AppImage\n".encode())
        if url.endswith(".minisig"):
            if minisig is None:
                raise OSError("404 no signature published")
            return _FakeResponse(minisig.encode())
        return _FakeResponse(payload)

    return open_url


def test_valid_signature_installs_when_signing_armed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from platterpus import update_signing

    pub_b64, minisig = _test_key_and_sig()
    monkeypatch.setattr(update_signing, "PUBLIC_KEY_B64", pub_b64)

    result = download_and_install(
        "0.2.3", dest_dir=tmp_path, opener=_signing_opener(_PAYLOAD, minisig)
    )
    assert result.read_bytes() == _PAYLOAD  # installed
    assert not (tmp_path / ".platterpus-update.part").exists()


def test_missing_signature_is_refused_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from platterpus import update_signing

    pub_b64, _ = _test_key_and_sig()
    monkeypatch.setattr(update_signing, "PUBLIC_KEY_B64", pub_b64)

    # No .minisig published — fail-closed: refuse, don't fall through to install.
    with pytest.raises(UpdateInstallError, match="no verifiable signature"):
        download_and_install(
            "0.2.3", dest_dir=tmp_path, opener=_signing_opener(_PAYLOAD, None)
        )
    assert not (tmp_path / ".platterpus-update.part").exists()
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_invalid_signature_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from platterpus import update_signing

    # A signature made for DIFFERENT bytes than what we serve → verify fails.
    pub_b64, minisig_for_other = _test_key_and_sig(payload=b"different bytes")
    monkeypatch.setattr(update_signing, "PUBLIC_KEY_B64", pub_b64)

    with pytest.raises(UpdateInstallError, match="failed signature verification"):
        download_and_install(
            "0.2.3",
            dest_dir=tmp_path,
            opener=_signing_opener(_PAYLOAD, minisig_for_other),
        )
    assert not (tmp_path / ".platterpus-update.part").exists()
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_signature_not_fetched_when_signing_not_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from platterpus import update_signing

    # Default: no key → SHA-256-only behaviour, and the .minisig is never sought.
    monkeypatch.setattr(update_signing, "PUBLIC_KEY_B64", "")
    fetched: list[str] = []

    inner = _signing_opener(_PAYLOAD, None)

    def recording_opener(url: str):
        fetched.append(url)
        return inner(url)

    download_and_install("0.2.3", dest_dir=tmp_path, opener=recording_opener)
    assert not any(u.endswith(".minisig") for u in fetched)


def test_install_swap_failure_cleans_up_and_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A verified download that can't be swapped into place (e.g. permissions)
    # must surface a presentable error and remove the .part, leaving no mess.
    def boom(self: Path, target: Path) -> None:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(Path, "replace", boom)

    with pytest.raises(UpdateInstallError, match="couldn't install"):
        download_and_install("0.2.3", dest_dir=tmp_path, opener=_opener())

    assert not (tmp_path / ".platterpus-update.part").exists()
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_unknown_size_reports_indeterminate_progress(tmp_path: Path) -> None:
    def open_url(url: str):
        if url.endswith(".sha256"):
            digest = hashlib.sha256(_PAYLOAD).hexdigest()
            return _FakeResponse(f"{digest}  x\n".encode())
        return _FakeResponse(_PAYLOAD, content_length=False)

    seen: list[float] = []
    download_and_install(
        "0.2.3", dest_dir=tmp_path, progress=seen.append, opener=open_url
    )
    assert seen and all(p == -1.0 for p in seen)  # busy indicator, no bogus %
