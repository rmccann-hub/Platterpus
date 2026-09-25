"""Check that an update was built by this repository's release workflow.

**Why this exists.** The in-app updater checked one thing: the download's SHA-256,
fetched from the same GitHub release as the download. That proves the file arrived
intact. It does not prove who published it, because anyone able to replace the
AppImage on a release can replace its ``.sha256`` too. Update signing would have
closed that, and the maintainer decided never to arm it (``PLANNING.md`` KDD-37,
D9). Asked the follow-up, the maintainer said yes to this instead (2026-09-25).

**What it proves.** Every release's AppImage carries a build-provenance
attestation, made by ``actions/attest-build-provenance`` in ``release.yml``. It is a
statement, signed through Sigstore with a certificate GitHub issues to one workflow
run, saying *"this file, with this SHA-256, was built by this workflow from this
commit"*. The signature is recorded in Sigstore's public transparency log. So an
update that passes here was built by ``.github/workflows/release.yml`` in
``rmccann-hub/Platterpus``, run from ``main`` or from the release's own tag, and
that build is traceable to a public commit. A file somebody uploaded by hand, or
built anywhere else, cannot pass.

**What it does not prove, said plainly.** Anyone who can push to ``main`` can run
the release workflow, and ``main`` is not protected (a maintainer ruling). The
check does not stop a genuine older build being served under a newer version
either; the source commit is logged so such a mix-up is visible afterwards.

**Adapter.** This is the only module that imports ``sigstore`` (Critical rule #1),
and it imports it lazily: the library takes about 0.7 s to import and is needed
only while an update installs. Nothing here raises. Every answer is an
:class:`AttestationResult`, and the updater refuses anything but ``verified``.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from sigstore.verify import Verifier
    from sigstore.verify.policy import VerificationPolicy

log = logging.getLogger(__name__)

#: The release asset holding the attestation, next to the AppImage and its
#: ``.sha256``. ``release.yml`` uploads it before the release becomes visible.
ATTESTATION_SUFFIX: Final[str] = ".sigstore.json"

#: Cap on the attestation read. The v0.6.60 bundle is 10,887 bytes (measured
#: 2026-09-25); 256 KiB leaves room for a JSON Lines file of several bundles and
#: still stops a hostile server streaming an endless body into memory.
MAX_BUNDLE_BYTES: Final[int] = 256 * 1024

#: At most this many candidate bundles are tried from one file.
_MAX_CANDIDATES: Final[int] = 16

REPOSITORY: Final[str] = "rmccann-hub/Platterpus"
WORKFLOW_PATH: Final[str] = ".github/workflows/release.yml"
OIDC_ISSUER: Final[str] = "https://token.actions.githubusercontent.com"
PAYLOAD_TYPE: Final[str] = "application/vnd.in-toto+json"
STATEMENT_TYPE: Final[str] = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE: Final[str] = "https://slsa.dev/provenance/v1"

#: How long to wait for Sigstore's trust root to refresh once the download has
#: finished. The refresh starts before the download, so it has normally long
#: finished. A stalled network makes it hang for 120 s before failing (measured
#: 2026-09-25), which is why the wait is bounded and the cached root is the
#: fallback.
TRUST_REFRESH_WAIT_S: Final[float] = 20.0

Verdict = Literal["verified", "refused", "not_checked"]


@dataclass(frozen=True)
class AttestationResult:
    """What the check found. Only ``verified`` lets an update install.

    ``refused`` means the attestation was read and failed a check. ``not_checked``
    means no check could be made (no verifier, no trust root). Both block the
    install; they are kept apart because they call for different fixes.
    """

    verdict: Verdict
    reason: str
    source_commit: str | None = None
    workflow_ref: str | None = None

    @property
    def verified(self) -> bool:
        return self.verdict == "verified"


def _refused(reason: str) -> AttestationResult:
    return AttestationResult("refused", reason)


def identity_policy(version: str) -> VerificationPolicy:
    """The certificate a genuine release carries, for release ``version``.

    Issued by GitHub Actions, for a run in this repository, of ``release.yml``,
    from ``main`` (a dispatched release, the usual route) or from the tag
    ``v<version>`` (a tag push). Any other workflow, fork or ref is refused.
    """
    from sigstore.verify import policy

    repo_uri = f"https://github.com/{REPOSITORY}"
    signer = f"{repo_uri}/{WORKFLOW_PATH}@"
    return policy.AllOf(
        [
            policy.OIDCIssuerV2(OIDC_ISSUER),
            policy.OIDCSourceRepositoryURI(repo_uri),
            policy.AnyOf(
                [
                    policy.OIDCBuildSignerURI(signer + "refs/heads/main"),
                    policy.OIDCBuildSignerURI(signer + f"refs/tags/v{version}"),
                ]
            ),
        ]
    )


def _candidates(text: str) -> list[str]:
    """The bundle documents in ``text``: one JSON document, or JSON Lines."""
    stripped = text.strip()
    if not stripped:
        return []
    try:
        json.loads(stripped)
    except ValueError:
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        return lines[:_MAX_CANDIDATES]
    return [stripped]


def _check_statement(payload: bytes, sha256_hex: str) -> AttestationResult:
    """Check the signed statement names our file and is build provenance."""
    try:
        statement = json.loads(payload)
    except ValueError:
        return _refused("its signed statement is not JSON")
    if not isinstance(statement, dict):
        return _refused("its signed statement is not a JSON object")
    if statement.get("_type") != STATEMENT_TYPE:
        return _refused(f"its statement type is {statement.get('_type')!r}")
    if statement.get("predicateType") != PREDICATE_TYPE:
        return _refused(
            f"it is not build provenance ({statement.get('predicateType')!r})"
        )
    subjects = statement.get("subject")
    digests = [
        str(subject.get("digest", {}).get("sha256", "")).lower()
        for subject in (subjects if isinstance(subjects, list) else [])
        if isinstance(subject, dict) and isinstance(subject.get("digest"), dict)
    ]
    if sha256_hex.lower() not in digests:
        return _refused("it names a different file: its SHA-256 does not match")
    commit, ref = _provenance_source(statement.get("predicate"))
    return AttestationResult("verified", "", source_commit=commit, workflow_ref=ref)


def _provenance_source(predicate: object) -> tuple[str | None, str | None]:
    """The commit and workflow ref the provenance names, for the log. Best effort."""
    if not isinstance(predicate, dict):
        return None, None
    definition = predicate.get("buildDefinition")
    if not isinstance(definition, dict):
        return None, None
    commit: str | None = None
    dependencies = definition.get("resolvedDependencies")
    if isinstance(dependencies, list) and dependencies:
        first = dependencies[0]
        if isinstance(first, dict) and isinstance(first.get("digest"), dict):
            value = first["digest"].get("gitCommit")
            commit = value if isinstance(value, str) else None
    ref: str | None = None
    parameters = definition.get("externalParameters")
    if isinstance(parameters, dict) and isinstance(parameters.get("workflow"), dict):
        value = parameters["workflow"].get("ref")
        ref = value if isinstance(value, str) else None
    return commit, ref


def _verify_one(
    document: str, sha256_hex: str, version: str, verifier: Verifier
) -> AttestationResult:
    from sigstore.errors import Error as SigstoreError
    from sigstore.models import Bundle

    try:
        bundle = Bundle.from_json(document)
    except SigstoreError as exc:
        return _refused(f"it is not a readable Sigstore bundle ({exc})")
    try:
        payload_type, payload = verifier.verify_dsse(bundle, identity_policy(version))
    except SigstoreError as exc:
        return _refused(f"its signature or signer did not check out ({exc})")
    if payload_type != PAYLOAD_TYPE:
        return _refused(f"it carries {payload_type!r}, not an in-toto statement")
    return _check_statement(payload, sha256_hex)


def select_verified(
    text: str, sha256_hex: str, version: str, verifier: Verifier
) -> tuple[AttestationResult, str | None]:
    """Try each bundle in ``text``; return the result and the document that passed.

    The release workflow uses this to choose which bundle to publish, and the
    updater uses it to check one, so what is published is by construction what
    the updater accepts. Never raises.
    """
    documents = _candidates(text)
    if not documents:
        return _refused("the attestation file is empty"), None
    last = _refused("no bundle in the file checked out")
    for document in documents:
        try:
            result = _verify_one(document, sha256_hex, version, verifier)
        except Exception as exc:  # noqa: BLE001 — last line before an executable
            # A third-party verifier raising a type we did not list must become
            # a refusal, never a crashed update worker. Logged with the trace.
            log.exception("attestation check raised unexpectedly")
            return AttestationResult(
                "not_checked", f"the check itself failed: {exc}"
            ), None
        if result.verified:
            return result, document
        last = result
    return last, None


def production_verifier(offline: bool) -> Verifier:
    """Sigstore's public-good verifier. ``offline`` uses the cached trust root.

    Online, it refreshes the trust root over TUF, which is how a key rotation at
    Sigstore reaches us without a Platterpus release. Offline, it uses the last
    refreshed copy, or the one inside the installed ``sigstore`` package.
    """
    from sigstore.verify import Verifier

    return Verifier.production(offline=offline)


class TrustRefresh:
    """Refresh Sigstore's trust root on a daemon thread, started early.

    Started before the AppImage download, so the network round trip overlaps
    the download instead of following it. :meth:`verifier` waits a bounded time
    for it, then falls back to the cached root, and says which one it used.
    The thread is a daemon and is never joined without a deadline, so a stalled
    refresh can neither hang the update worker nor keep the app from exiting.
    """

    def __init__(self, load: Callable[[bool], Verifier] | None = None) -> None:
        self._load: Callable[[bool], Verifier] = load or production_verifier
        self._done: threading.Event = threading.Event()
        self._refreshed: Verifier | None = None
        self._error: str = ""

    def start(self) -> TrustRefresh:
        threading.Thread(
            target=self._run, name="sigstore-trust-refresh", daemon=True
        ).start()
        return self

    def _run(self) -> None:
        try:
            self._refreshed = self._load(False)
        except Exception as exc:  # noqa: BLE001 — reported; the cached root is used
            self._error = f"{type(exc).__name__}: {exc}"
        finally:
            self._done.set()

    def verifier(
        self,
        wait_s: float = TRUST_REFRESH_WAIT_S,
        cancelled: Callable[[], bool] | None = None,
    ) -> tuple[Verifier | None, str]:
        """``(verifier, how)``. ``verifier`` is None only if no root could load."""
        deadline = time.monotonic() + wait_s
        while not self._done.wait(0.25):
            if time.monotonic() >= deadline or (cancelled is not None and cancelled()):
                break
        if self._refreshed is not None:
            return self._refreshed, "trust root refreshed from Sigstore"
        why = self._error or f"no answer from Sigstore within {wait_s:.0f} s"
        try:
            return self._load(True), f"cached trust root used ({why})"
        except Exception as exc:  # noqa: BLE001 — becomes a not_checked result
            return None, f"no trust root could be loaded ({why}; cached: {exc})"


def verify_update(
    text: str,
    sha256_hex: str,
    version: str,
    trust: TrustRefresh,
    cancelled: Callable[[], bool] | None = None,
) -> AttestationResult:
    """The updater's check: does ``text`` attest this file as a genuine release?"""
    verifier, how = trust.verifier(cancelled=cancelled)
    if verifier is None:
        log.warning("attestation not checked: %s", how)
        return AttestationResult("not_checked", how)
    result, _document = select_verified(text, sha256_hex, version, verifier)
    log.info(
        "update attestation for v%s: %s%s (%s; commit %s, ref %s)",
        version,
        result.verdict,
        f" — {result.reason}" if result.reason else "",
        how,
        result.source_commit or "unknown",
        result.workflow_ref or "unknown",
    )
    return result
