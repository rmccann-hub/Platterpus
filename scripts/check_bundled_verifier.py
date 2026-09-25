#!/usr/bin/env python3
"""Prove a built AppImage's own Python can verify a release attestation.

**Why this exists.** The updater imports ``sigstore`` lazily, only while an update
installs, so an AppImage built without a working copy starts, passes
``--version``, and looks healthy. Then it refuses every update it is ever
offered, because the attestation check cannot run, and its users are stranded on
it with no in-app way off. Nothing else in the build would notice. So the
AppImage workflows extract the bundle and run this with the **bundled**
interpreter.

What it checks: that ``platterpus.update_attestation`` and ``sigstore`` import
from inside the bundle (``--bundle-root``), not from the runner; and that they
verify the committed v0.6.60 attestation offline against the committed trust
root. That is the whole chain an update depends on, minus the network.

Usage, from the repository root::

    <squashfs-root>/opt/python3.11/bin/python3.11 scripts/check_bundled_verifier.py \\
        --bundle-root <squashfs-root>

Exits 0 when the bundled verifier accepts the genuine bundle, 1 otherwise.
Deliberately does not add ``src/`` to ``sys.path``: the point is to test the copy
that ships.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
BUNDLE = FIXTURES / "attestation_v0660.sigstore.json"
TRUSTED_ROOT = FIXTURES / "sigstore_trusted_root_20260925.json"
#: The v0.6.60 AppImage's SHA-256, from that release's `.sha256` asset.
DIGEST = "dbd7aacd5ab705449a2d99d217d1e6a3bc57bc8725702d6777efd1315bcdd526"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--bundle-root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        import sigstore
        from sigstore.models import TrustedRoot
        from sigstore.verify import Verifier

        from platterpus import update_attestation
    except ImportError as exc:
        print(
            f"::error::the bundled Python cannot import the attestation verifier "
            f"({exc}). An app built like this would refuse every update."
        )
        return 1
    where = {
        "platterpus.update_attestation": Path(update_attestation.__file__).resolve(),
        "sigstore": Path(sigstore.__file__).resolve(),
    }
    for name, path in where.items():
        print(f"{name}: {path}")
        if (
            args.bundle_root is not None
            and args.bundle_root.resolve() not in path.parents
        ):
            print(f"::error::{name} was imported from outside the bundle")
            return 1
    verifier = Verifier(trusted_root=TrustedRoot.from_file(str(TRUSTED_ROOT)))
    result, _ = update_attestation.select_verified(
        BUNDLE.read_text(encoding="utf-8"), DIGEST, "0.6.60", verifier
    )
    if not result.verified:
        print(
            f"::error::the bundled verifier refused a genuine release: {result.reason}"
        )
        return 1
    print(
        f"bundled verifier accepts the genuine v0.6.60 attestation (sigstore {sigstore.__version__})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
