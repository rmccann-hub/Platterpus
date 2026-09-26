#!/usr/bin/env python3
"""Choose and check the attestation a release publishes beside its AppImage.

**Run by ``release.yml``**, after ``actions/attest-build-provenance`` has written
its bundle and before the release becomes visible. It picks the bundle that
verifies against the built AppImage, using the updater's own check
(``platterpus.update_attestation.select_verified``), and writes it to the asset
the updater fetches. So what a release publishes is, by construction, what the
installed app will accept, and a release whose attestation the updater would
refuse fails here, before anybody is offered it.

Why this matters: the updater refuses an update without a passing attestation
(fail-closed, 2026-09-25). A release published with a missing or wrong one
would be an update nobody could install, so the release workflow is the place
to find out.

Usage::

    python scripts/release_attestation.py --bundle PATH --artifact FILE \\
        --version X.Y.Z --out FILE

``--bundle`` is the action's ``bundle-path`` output: JSON Lines, one bundle per
line. Exits 0 and writes ``--out`` when a bundle verifies; exits 1 otherwise,
printing why each one failed.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from platterpus import update_attestation  # noqa: E402 — after the path setup


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--version", required=True, help="the release, without v")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    text = args.bundle.read_text(encoding="utf-8")
    digest = _sha256(args.artifact)
    trust = update_attestation.TrustRefresh().start()
    verifier, how = trust.verifier()
    print(f"trust root: {how}")
    if verifier is None:
        print("::error::no Sigstore trust root could be loaded, so nothing was checked")
        return 1
    result, document = update_attestation.select_verified(
        text, digest, args.version, verifier
    )
    if document is None:
        print(
            f"::error::no attestation bundle verifies against {args.artifact.name} "
            f"(sha256 {digest}) for v{args.version}: {result.reason}. The in-app "
            "updater would refuse this release, so it is not published."
        )
        return 1
    args.out.write_text(document + "\n", encoding="utf-8")
    print(
        f"attestation verified for {args.artifact.name} (sha256 {digest}): built "
        f"from commit {result.source_commit} via {result.workflow_ref}; "
        f"wrote {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
