"""Tests for :mod:`platterpus.update_attestation`, against a REAL release.

**Why against a real one.** A check of our verifier against a bundle our own test
made would pass if the verifier and the fixture shared a mistake. So the anchor
here is the attestation GitHub actually holds for the v0.6.60 AppImage, verified
offline with Sigstore's real trust root (``tests/fixtures/README.md`` says where
both came from). If this passes, a genuine release verifies; every other test
then shows one specific thing that must not.

**Why it matters.** Until 2026-09-25 the updater checked only a SHA-256 fetched
from the same release as the download, which proves nothing about who published
it. This is the check that replaced that gap (``PLANNING.md`` KDD-37, D9).
"""

from __future__ import annotations

import base64
import json
import re
import threading
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sigstore.models import TrustedRoot
from sigstore.verify import Verifier

from platterpus import update_attestation
from platterpus.update_attestation import (
    AttestationResult,
    TrustRefresh,
    select_verified,
    verify_update,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_BUNDLE = (_FIXTURES / "attestation_v0660.sigstore.json").read_text(encoding="utf-8")
#: The v0.6.60 AppImage's SHA-256, from that release's own `.sha256` asset.
_DIGEST = "dbd7aacd5ab705449a2d99d217d1e6a3bc57bc8725702d6777efd1315bcdd526"
#: The commit tag v0.6.60 points at (GitHub's tag list, 2026-09-25).
_COMMIT = "88c09dd5057e9295dc03a1b26ca8827f576544cf"


@pytest.fixture(scope="module")
def verifier() -> Verifier:
    """Sigstore's production verifier, built offline from the committed root."""
    root = TrustedRoot.from_file(str(_FIXTURES / "sigstore_trusted_root_20260925.json"))
    return Verifier(trusted_root=root)


# --- the anchor: a genuine release verifies ----------------------------------


def test_a_genuine_release_verifies_and_names_its_commit(verifier: Verifier) -> None:
    result, document = select_verified(_BUNDLE, _DIGEST, "0.6.60", verifier)
    assert result.verified, result.reason
    assert result.source_commit == _COMMIT
    assert result.workflow_ref == "refs/heads/main"
    assert document is not None and json.loads(document)["dsseEnvelope"]


def test_the_digest_comparison_ignores_case(verifier: Verifier) -> None:
    result, _ = select_verified(_BUNDLE, _DIGEST.upper(), "0.6.60", verifier)
    assert result.verified


def test_json_lines_with_a_bad_line_first_still_finds_the_good_bundle(
    verifier: Verifier,
) -> None:
    """The release action can write JSON Lines; any line that verifies is enough."""
    text = '{"not": "a bundle"}\n' + _BUNDLE
    result, document = select_verified(text, _DIGEST, "0.6.60", verifier)
    assert result.verified and document == _BUNDLE.strip()


# --- what must not verify ----------------------------------------------------


def test_a_different_file_is_refused(verifier: Verifier) -> None:
    """The case that matters most: a swapped AppImage with a genuine bundle."""
    result, document = select_verified(_BUNDLE, "0" * 64, "0.6.60", verifier)
    assert result.verdict == "refused" and document is None
    assert "different file" in result.reason


def _tampered_payload(edit: Any) -> str:
    bundle = json.loads(_BUNDLE)
    statement = json.loads(base64.b64decode(bundle["dsseEnvelope"]["payload"]))
    edit(statement)
    bundle["dsseEnvelope"]["payload"] = base64.b64encode(
        json.dumps(statement).encode()
    ).decode()
    return json.dumps(bundle)


def test_an_edited_statement_fails_the_signature(verifier: Verifier) -> None:
    """Rewriting the subject to name another file breaks the signature over it."""

    def swap(statement: dict[str, Any]) -> None:
        statement["subject"][0]["digest"]["sha256"] = "1" * 64

    result, _ = select_verified(_tampered_payload(swap), "1" * 64, "0.6.60", verifier)
    assert result.verdict == "refused"
    assert "did not check out" in result.reason


def test_a_signer_outside_the_allowed_identity_is_refused(
    verifier: Verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same genuine bundle, checked as if it had to come from another repo."""
    monkeypatch.setattr(update_attestation, "REPOSITORY", "someone-else/Platterpus")
    result, _ = select_verified(_BUNDLE, _DIGEST, "0.6.60", verifier)
    assert result.verdict == "refused"
    assert "signer" in result.reason


def test_another_workflow_in_this_repo_is_refused(
    verifier: Verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(update_attestation, "WORKFLOW_PATH", ".github/workflows/ci.yml")
    result, _ = select_verified(_BUNDLE, _DIGEST, "0.6.60", verifier)
    assert result.verdict == "refused"


def test_the_identity_allows_main_and_the_releases_own_tag_only() -> None:
    """Read the policy's children rather than trusting its docstring."""
    policy = update_attestation.identity_policy("0.6.61")
    signer = f"https://github.com/{update_attestation.REPOSITORY}/.github/workflows/release.yml@"
    any_of = policy._children[2]  # noqa: SLF001 — the AnyOf of allowed signers
    allowed = {child._value for child in any_of._children}  # noqa: SLF001
    assert allowed == {signer + "refs/heads/main", signer + "refs/tags/v0.6.61"}


@pytest.mark.parametrize(
    "text",
    ["", "   \n", "not json at all", '{"mediaType": "nonsense"}', "[1, 2, 3]"],
)
def test_garbage_is_refused_never_raised(verifier: Verifier, text: str) -> None:
    result, document = select_verified(text, _DIGEST, "0.6.60", verifier)
    assert not result.verified and document is None


@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.text(max_size=400))
def test_select_verified_never_raises(verifier: Verifier, text: str) -> None:
    result, _ = select_verified(text, _DIGEST, "0.6.60", verifier)
    assert isinstance(result, AttestationResult) and not result.verified


def test_an_unexpected_exception_becomes_not_checked_not_a_crash() -> None:
    class _Exploding:
        def verify_dsse(self, bundle: object, policy: object) -> tuple[str, bytes]:
            raise RuntimeError("boom")

    result, _ = select_verified(_BUNDLE, _DIGEST, "0.6.60", _Exploding())  # type: ignore[arg-type]  # a stand-in with only verify_dsse
    assert result.verdict == "not_checked" and "boom" in result.reason


@pytest.mark.parametrize(
    ("statement", "reason"),
    [
        ([], "not a JSON object"),
        ({"_type": "x"}, "statement type"),
        (
            {"_type": update_attestation.STATEMENT_TYPE, "predicateType": "y"},
            "not build provenance",
        ),
        (
            {
                "_type": update_attestation.STATEMENT_TYPE,
                "predicateType": update_attestation.PREDICATE_TYPE,
                "subject": "not a list",
            },
            "different file",
        ),
    ],
)
def test_a_signed_statement_of_the_wrong_shape_is_refused(
    statement: object, reason: str
) -> None:
    result = update_attestation._check_statement(  # noqa: SLF001
        json.dumps(statement).encode(), _DIGEST
    )
    assert result.verdict == "refused" and reason in result.reason


# --- the trust root refresh ---------------------------------------------------


def test_the_refreshed_root_is_used_when_it_arrives(verifier: Verifier) -> None:
    trust = TrustRefresh(load=lambda offline: verifier).start()
    got, how = trust.verifier(wait_s=5)
    assert got is verifier and "refreshed" in how


def test_a_failed_refresh_falls_back_to_the_cached_root(verifier: Verifier) -> None:
    calls: list[bool] = []

    def load(offline: bool) -> Verifier:
        calls.append(offline)
        if not offline:
            raise OSError("no network")
        return verifier

    got, how = TrustRefresh(load=load).start().verifier(wait_s=5)
    assert got is verifier and calls == [False, True]
    assert "cached trust root used" in how and "no network" in how


def test_a_stalled_refresh_is_waited_for_a_bounded_time_only(
    verifier: Verifier,
) -> None:
    """A refresh on a stalled network takes 120 s to fail (measured). Never wait that long."""
    release = threading.Event()

    def load(offline: bool) -> Verifier:
        if not offline:
            release.wait(10)
        return verifier

    trust = TrustRefresh(load=load).start()
    got, how = trust.verifier(wait_s=0.3)
    release.set()
    assert got is verifier and "within 0 s" in how


def test_cancelling_stops_the_wait(verifier: Verifier) -> None:
    release = threading.Event()

    def load(offline: bool) -> Verifier:
        if not offline:
            release.wait(10)
        return verifier

    got, how = (
        TrustRefresh(load=load).start().verifier(wait_s=60, cancelled=lambda: True)
    )
    release.set()
    assert got is verifier and "cached" in how


def test_no_trust_root_at_all_is_not_checked() -> None:
    def load(offline: bool) -> Verifier:
        raise OSError("disk gone")

    result = verify_update(_BUNDLE, _DIGEST, "0.6.60", TrustRefresh(load=load).start())
    assert result.verdict == "not_checked" and "no trust root" in result.reason


def test_verify_update_end_to_end_on_the_real_release(verifier: Verifier) -> None:
    trust = TrustRefresh(load=lambda offline: verifier).start()
    assert verify_update(_BUNDLE, _DIGEST, "0.6.60", trust).verified


# --- the release workflow publishes what the updater checks ------------------
#
# Two halves of one contract: `release.yml` produces the attestation asset and
# the updater consumes it. Each half is tested against the other here, so a
# rename, a reorder or a dropped upload fails in CI instead of on a user's
# machine as an update that can never install.

_REPO = Path(__file__).resolve().parent.parent
_RELEASE_YML = _REPO / ".github" / "workflows" / "release.yml"


def _workflow() -> str:
    return _RELEASE_YML.read_text(encoding="utf-8")


def _step(name_prefix: str) -> str:
    """The text of the release job's step whose name starts with ``name_prefix``.

    Read as text, like the other workflow tests: PyYAML is not a dependency. A
    step runs from its ``      - `` line to the next one at the same indent.
    """
    text = _workflow()
    start = text.index(f"      - name: {name_prefix}")
    following = text.find("\n      - ", start + 1)
    return text[start : following if following != -1 else len(text)]


def _asset_name() -> str:
    from platterpus.appimage_integration import CANONICAL_APPIMAGE_NAME

    return CANONICAL_APPIMAGE_NAME + update_attestation.ATTESTATION_SUFFIX


def test_the_workflow_the_updater_trusts_is_the_one_that_attests() -> None:
    """The identity policy names a workflow path; that file must do the attesting."""
    assert _REPO / update_attestation.WORKFLOW_PATH == _RELEASE_YML
    assert "uses: actions/attest-build-provenance@" in _step("Attest AppImage")


def test_the_attestation_is_made_and_checked_before_the_release_is_published() -> None:
    """A release visible before its attestation is an update that cannot install."""
    text = _workflow()
    attest = text.index("      - name: Attest AppImage build provenance")
    check = text.index("      - name: Check the attestation")
    publish = text.index("      - name: Publish to GitHub Release")
    assert attest < check < publish


def test_the_check_step_writes_the_asset_the_updater_fetches() -> None:
    step = _step("Check the attestation")
    assert "scripts/release_attestation.py" in step
    assert f"--out {_asset_name()}" in step
    assert "steps.attest.outputs.bundle-path" in step
    assert "id: attest" in _step("Attest AppImage")
    # The sigstore pin is read from pyproject, never restated in the workflow.
    assert "sigstore>=" not in step and "sigstore~=" not in step


def test_both_publish_branches_upload_the_attestation() -> None:
    """The release is created OR re-uploaded; both must carry the asset."""
    step = _step("Publish to GitHub Release")
    assert step.count("gh release upload") == 1 and step.count("gh release create") == 1
    upload, create = step.split("gh release create", 1)
    assert _asset_name() in upload.split("gh release upload", 1)[1]
    assert _asset_name() in create


def test_the_release_job_may_mint_an_identity_and_write_attestations() -> None:
    block = _workflow().split("\npermissions:\n", 1)[1].split("\n\n", 1)[0]
    assert re.search(r"^  id-token: write\b", block, re.MULTILINE)
    assert re.search(r"^  attestations: write\b", block, re.MULTILINE)


def _load_release_script() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "release_attestation", _REPO / "scripts" / "release_attestation.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_release_script_stages_the_bundle_that_verifies(
    tmp_path: Path, verifier: Verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JSON Lines in, the one verifying line out: exactly what the updater reads."""
    script = _load_release_script()
    monkeypatch.setattr(script, "_sha256", lambda path: _DIGEST)
    monkeypatch.setattr(
        update_attestation,
        "TrustRefresh",
        lambda: TrustRefresh(load=lambda o: verifier),
    )
    bundle = tmp_path / "attestation.json"
    bundle.write_text('{"stale": "line"}\n' + _BUNDLE, encoding="utf-8")
    out = tmp_path / _asset_name()
    code = script.main(
        [
            "--bundle",
            str(bundle),
            "--artifact",
            str(bundle),
            "--version",
            "0.6.60",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert out.read_text(encoding="utf-8").strip() == _BUNDLE.strip()
    result, _ = select_verified(
        out.read_text(encoding="utf-8"), _DIGEST, "0.6.60", verifier
    )
    assert result.verified


def test_the_release_script_refuses_and_writes_nothing_for_the_wrong_file(
    tmp_path: Path, verifier: Verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_release_script()
    monkeypatch.setattr(script, "_sha256", lambda path: "0" * 64)
    monkeypatch.setattr(
        update_attestation,
        "TrustRefresh",
        lambda: TrustRefresh(load=lambda o: verifier),
    )
    bundle = tmp_path / "attestation.json"
    bundle.write_text(_BUNDLE, encoding="utf-8")
    out = tmp_path / _asset_name()
    code = script.main(
        [
            "--bundle",
            str(bundle),
            "--artifact",
            str(bundle),
            "--version",
            "0.6.60",
            "--out",
            str(out),
        ]
    )
    assert code == 1 and not out.exists()
