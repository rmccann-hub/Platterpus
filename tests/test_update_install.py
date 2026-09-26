"""Tests for the in-app update installer (update_install.py).

Driven through a fake opener — no network. The contract under test: the
published .sha256 gates the install (a corrupt download never replaces
anything), the swap is atomic via a .part file, and every failure path
cleans up after itself.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from platterpus import update_attestation, update_install
from platterpus.update_install import (
    UpdateInstallError,
    asset_url,
    download_and_install,
)

_PAYLOAD = b"new appimage bytes" * 1000

_FIXTURES = Path(__file__).parent / "fixtures"
#: A real release's attestation (v0.6.60), served for every `.sigstore.json`.
_BUNDLE = (_FIXTURES / "attestation_v0660.sigstore.json").read_bytes()


class _StatementVerifier:
    """Stands in for sigstore's ``Verifier``: returns a statement naming ``payload``.

    **What it does not do that the real one does:** check the signature, the
    certificate chain, the transparency log or the signer's identity. Those run
    for real in ``tests/test_update_attestation.py`` against a genuine release,
    and :func:`test_the_real_verifier_refuses_a_download_its_bundle_does_not_name`
    below runs them inside the updater. What it keeps real is everything after
    the signature: the statement's type, predicate and subject digest.
    """

    def __init__(self, payload: bytes) -> None:
        self._digest = hashlib.sha256(payload).hexdigest()

    def verify_dsse(self, bundle: object, policy: object) -> tuple[str, bytes]:
        statement = {
            "_type": update_attestation.STATEMENT_TYPE,
            "predicateType": update_attestation.PREDICATE_TYPE,
            "subject": [
                {
                    "name": "platterpus-x86_64.AppImage",
                    "digest": {"sha256": self._digest},
                }
            ],
        }
        return update_attestation.PAYLOAD_TYPE, json.dumps(statement).encode()


def _trust(payload: bytes = _PAYLOAD) -> update_attestation.TrustRefresh:
    verifier = _StatementVerifier(payload)
    return update_attestation.TrustRefresh(load=lambda offline: verifier).start()  # type: ignore[arg-type,return-value]  # the stand-in has only verify_dsse


def _with_attestation(open_url: Any) -> Any:
    """Serve the real bundle for the attestation asset; everything else as given."""

    def wrapped(url: str) -> Any:
        if url.endswith(update_attestation.ATTESTATION_SUFFIX):
            return _FakeResponse(_BUNDLE)
        return open_url(url)

    return wrapped


def _install(version: str, *, opener: Any, trust: Any = None, **kwargs: Any) -> Path:
    """``download_and_install`` with the attestation gate answered by the stand-in.

    Every test of the OTHER gates goes through here, so each still reaches the
    step it is about. The attestation gate's own tests call the real function.
    """
    return download_and_install(
        version,
        opener=_with_attestation(opener),
        trust=trust if trust is not None else _trust(),
        **kwargs,
    )


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
    result = _install(
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
    _install("0.2.3", dest_dir=tmp_path, status=phases.append, opener=_opener())

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
        _install("0.2.3", dest_dir=tmp_path, opener=bad)

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
        _install("0.2.3", dest_dir=tmp_path, opener=open_url)
    assert reads and reads[0] == ui._MAX_SHA256_BYTES


def test_malformed_published_checksum_aborts_before_download(
    tmp_path: Path,
) -> None:
    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(b"not-a-checksum\n")
        raise AssertionError("the big download must not start")

    with pytest.raises(UpdateInstallError, match="malformed"):
        _install("0.2.3", dest_dir=tmp_path, opener=open_url)


def test_cancel_mid_download_cleans_up(tmp_path: Path) -> None:
    with pytest.raises(UpdateInstallError, match="cancelled"):
        _install("0.2.3", dest_dir=tmp_path, cancelled=lambda: True, opener=_opener())
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
        _install("0.2.3", dest_dir=tmp_path, opener=open_url)
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
        _install("0.2.3", dest_dir=tmp_path, opener=open_url)
    assert not (tmp_path / ".platterpus-update.part").exists()


def test_network_failure_raises_presentable_error(tmp_path: Path) -> None:
    def open_url(url: str):
        raise OSError("connection reset")

    with pytest.raises(UpdateInstallError, match="checksum"):
        _install("0.2.3", dest_dir=tmp_path, opener=open_url)


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
        _install("0.2.3", dest_dir=tmp_path, opener=open_url)

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

    result = _install(
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
        _install("0.2.3", dest_dir=tmp_path, opener=_signing_opener(_PAYLOAD, None))
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
        _install(
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

    _install("0.2.3", dest_dir=tmp_path, opener=recording_opener)
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
        _install("0.2.3", dest_dir=tmp_path, opener=_opener())

    assert not (tmp_path / ".platterpus-update.part").exists()
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_unknown_size_reports_indeterminate_progress(tmp_path: Path) -> None:
    def open_url(url: str):
        if url.endswith(".sha256"):
            digest = hashlib.sha256(_PAYLOAD).hexdigest()
            return _FakeResponse(f"{digest}  x\n".encode())
        return _FakeResponse(_PAYLOAD, content_length=False)

    seen: list[float] = []
    _install("0.2.3", dest_dir=tmp_path, progress=seen.append, opener=open_url)
    assert seen and all(p == -1.0 for p in seen)  # busy indicator, no bogus %


# --- The transport must stay on TLS -----------------------------------------
#
# Added by security audit, 2026-08-20. `asset_url` hardcodes an https:// URL, so
# an attacker cannot choose the first hop — but nothing checked the hops after
# it, and `urllib`'s default redirect handler ALLOWS https -> http (its
# `redirect_request` permits http, https and ftp). One plaintext `Location:` and
# the payload, its checksum and the executable about to be installed all cross
# the network in the clear.
#
# Why this is worth a guard rather than a shrug: the signature gate is dormant
# (`PUBLIC_KEY_B64` ships empty), so SHA-256 is the only check AND the checksum
# comes down the same channel as the bytes. An attacker who can rewrite the
# transport rewrites both, and the install succeeds. TLS is the whole control.
#
# GitHub does not downgrade. That is exactly the kind of "our dependency happens
# not to do the dangerous thing" assumption that cost this project the
# QKeySequence shortcuts, and the rule from that is: anything we ask a
# dependency for, we check the answer to.


def test_a_plain_http_url_is_refused_before_any_request() -> None:
    """The near end. No connection is opened at all."""
    with pytest.raises(update_install.UpdateInstallError) as exc:
        update_install._default_open("http://example.invalid/payload")
    assert "HTTPS" in str(exc.value), exc.value


def test_a_schemeless_url_is_refused() -> None:
    """`urlsplit` gives an empty scheme here — it must not read as 'fine'."""
    with pytest.raises(update_install.UpdateInstallError):
        update_install._default_open("example.invalid/payload")


def test_a_redirect_off_https_is_refused() -> None:
    """The far end, and the one a hardcoded start URL cannot protect."""
    handler = update_install._HttpsOnlyRedirects()
    with pytest.raises(urllib.error.HTTPError) as exc:
        handler.redirect_request(
            urllib.request.Request("https://github.invalid/a"),
            None,
            302,
            "Found",
            {},
            "http://evil.invalid/payload",
        )
    assert "HTTPS" in str(exc.value), exc.value


def test_a_redirect_to_a_non_web_scheme_is_refused() -> None:
    """`file://` and `ftp://` are schemes urllib would otherwise accept.

    A `file://` redirect would turn "update" into "copy a local path over the
    installed binary", which is a different bug with the same blast radius.
    """
    handler = update_install._HttpsOnlyRedirects()
    for target in ("file:///etc/passwd", "ftp://evil.invalid/payload"):
        with pytest.raises(urllib.error.HTTPError):
            handler.redirect_request(
                urllib.request.Request("https://github.invalid/a"),
                None,
                302,
                "Found",
                {},
                target,
            )


def test_an_https_to_https_redirect_is_still_allowed() -> None:
    """**The floor.** Without this the guard could be "refuse everything".

    GitHub release downloads DO redirect (to objects.githubusercontent.com), so a
    handler that blocked all redirects would break every real update while
    passing all three tests above.
    """
    handler = update_install._HttpsOnlyRedirects()
    result = handler.redirect_request(
        urllib.request.Request("https://github.invalid/a"),
        None,
        302,
        "Found",
        {},
        "https://objects.githubusercontent.invalid/b",
    )
    assert result is not None, (
        "a legitimate https->https redirect was refused — this would break every "
        "real GitHub asset download"
    )


def test_the_final_url_is_checked_not_only_the_requested_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The belt, exercised: a response claiming a non-HTTPS origin is refused.

    The redirect handler should make this unreachable. It is asserted anyway
    because the two checks are different mechanisms, and `geturl()` is the only
    thing that can testify to where the bytes actually came from — a
    same-mechanism belt would share the buckle's failure.
    """
    closed: list[bool] = []

    class _Response:
        url = "http://downgraded.invalid/payload"

        def geturl(self) -> str:
            return self.url

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(
        update_install._OPENER, "open", lambda *a, **k: _Response(), raising=True
    )
    with pytest.raises(update_install.UpdateInstallError) as exc:
        update_install._default_open("https://github.invalid/ok")
    assert "HTTPS" in str(exc.value)
    assert closed, "the response was not closed on refusal — a leaked socket"


# --- The build-attestation gate (fail-closed, always on) ---------------------
#
# Added 2026-09-25 (PLANNING.md KDD-37, D9). The SHA-256 above is fetched from
# the same release as the download, so it proves the bytes are intact and not
# who published them. This gate asks the release's Sigstore attestation, and a
# missing, unreadable or non-matching one blocks the install.


def _plain_opener(payload: bytes = _PAYLOAD, attestation: Any = _BUNDLE):
    """Serves the AppImage, its .sha256 and (unless None) the attestation."""
    digest = hashlib.sha256(payload).hexdigest()

    def open_url(url: str):
        if url.endswith(".sha256"):
            return _FakeResponse(f"{digest}  platterpus-x86_64.AppImage\n".encode())
        if url.endswith(update_attestation.ATTESTATION_SUFFIX):
            if attestation is None:
                raise OSError("HTTP Error 404: Not Found")
            return _FakeResponse(attestation)
        return _FakeResponse(payload)

    return open_url


def test_a_release_with_no_attestation_is_refused_and_nothing_changes(
    tmp_path: Path,
) -> None:
    """Accepting a missing file would let anyone defeat the check by deleting it."""
    existing = tmp_path / "platterpus-x86_64.AppImage"
    existing.write_bytes(b"the old version")
    with pytest.raises(
        UpdateInstallError, match="build attestation, which is required"
    ):
        download_and_install(
            "0.2.3",
            dest_dir=tmp_path,
            opener=_plain_opener(attestation=None),
            trust=_trust(),
        )
    assert existing.read_bytes() == b"the old version"
    assert not (tmp_path / ".platterpus-update.part").exists()


def test_an_attestation_for_a_different_file_is_refused(tmp_path: Path) -> None:
    """The stand-in attests other bytes: the downloaded digest is what is checked."""
    with pytest.raises(UpdateInstallError, match="did not check out"):
        download_and_install(
            "0.2.3",
            dest_dir=tmp_path,
            opener=_plain_opener(),
            trust=_trust(b"some other build"),
        )
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()
    assert not (tmp_path / ".platterpus-update.part").exists()


def test_the_real_verifier_refuses_a_download_its_bundle_does_not_name(
    tmp_path: Path,
) -> None:
    """The whole real chain inside the updater: signature, signer, then subject.

    A genuine v0.6.60 bundle served beside bytes that are not that AppImage. It
    passes every Sigstore check and fails only on the file, which is the swap
    this gate exists to stop.
    """
    from sigstore.models import TrustedRoot
    from sigstore.verify import Verifier

    root = TrustedRoot.from_file(str(_FIXTURES / "sigstore_trusted_root_20260925.json"))
    real = Verifier(trusted_root=root)
    trust = update_attestation.TrustRefresh(load=lambda offline: real).start()
    with pytest.raises(UpdateInstallError, match="different file"):
        download_and_install(
            "0.6.60", dest_dir=tmp_path, opener=_plain_opener(), trust=trust
        )
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_no_trust_root_means_not_checked_and_not_installed(tmp_path: Path) -> None:
    def load(offline: bool) -> Any:
        raise OSError("no cached root")

    with pytest.raises(UpdateInstallError, match="couldn't check"):
        download_and_install(
            "0.2.3",
            dest_dir=tmp_path,
            opener=_plain_opener(),
            trust=update_attestation.TrustRefresh(load=load).start(),
        )
    assert not (tmp_path / "platterpus-x86_64.AppImage").exists()


def test_an_oversized_attestation_is_refused_and_the_read_is_bounded(
    tmp_path: Path,
) -> None:
    reads: list[int] = []

    class _Recording(_FakeResponse):
        def read(self, n: int = -1) -> bytes:
            reads.append(n)
            return super().read(n)

    inner = _plain_opener()

    def open_url(url: str):
        if url.endswith(update_attestation.ATTESTATION_SUFFIX):
            return _Recording(b" " * (update_attestation.MAX_BUNDLE_BYTES + 10))
        return inner(url)

    with pytest.raises(UpdateInstallError, match="larger than any real one"):
        download_and_install(
            "0.2.3", dest_dir=tmp_path, opener=open_url, trust=_trust()
        )
    assert reads == [update_attestation.MAX_BUNDLE_BYTES + 1]


def test_a_checksum_failure_stops_before_the_attestation_is_fetched(
    tmp_path: Path,
) -> None:
    fetched: list[str] = []
    inner = _plain_opener()

    def open_url(url: str):
        fetched.append(url)
        if url.endswith(".sha256"):
            return _FakeResponse(f"{'0' * 64}  x\n".encode())
        return inner(url)

    with pytest.raises(UpdateInstallError, match="checksum"):
        download_and_install(
            "0.2.3", dest_dir=tmp_path, opener=open_url, trust=_trust()
        )
    assert not any(u.endswith(update_attestation.ATTESTATION_SUFFIX) for u in fetched)


def test_the_attestation_is_fetched_from_the_release_being_installed(
    tmp_path: Path,
) -> None:
    fetched: list[str] = []
    inner = _plain_opener()

    def open_url(url: str):
        fetched.append(url)
        return inner(url)

    download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url, trust=_trust())
    assert asset_url("0.2.3") + ".sigstore.json" in fetched


def test_the_attestation_phase_is_announced_as_a_post_download_step(
    tmp_path: Path,
) -> None:
    """Its label must not start with "Checking"/"Downloading": the progress
    dialog reads those as the download itself and would show a stuck bar."""
    from platterpus.ui.main_window_update import _is_download_phase

    phases: list[str] = []
    download_and_install(
        "0.2.3",
        dest_dir=tmp_path,
        status=phases.append,
        opener=_plain_opener(),
        trust=_trust(),
    )
    label = next(p for p in phases if "attestation" in p)
    assert not _is_download_phase(label)
    assert phases.index(label) < next(
        i for i, p in enumerate(phases) if p.startswith("Installing")
    )


def test_without_a_trust_argument_the_real_refresh_starts_before_the_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production passes no ``trust``. The refresh must start before the big
    download, so its network round trip overlaps it instead of following it."""
    events: list[str] = []
    stand_in = _trust()

    class _Recording:
        def start(self) -> Any:
            events.append("refresh started")
            return stand_in

    monkeypatch.setattr(update_attestation, "TrustRefresh", _Recording)
    inner = _plain_opener()

    def open_url(url: str):
        if url == asset_url("0.2.3"):
            events.append("download started")
        return inner(url)

    download_and_install("0.2.3", dest_dir=tmp_path, opener=open_url)
    assert events == ["refresh started", "download started"]
