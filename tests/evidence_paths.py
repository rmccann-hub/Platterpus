"""Where a test finds a file that was filed as run evidence (HR-2).

Run evidence (the ``docs/handshake/artifacts*`` folders) moves off ``main`` onto
the ``evidence`` branch in round 33 (HR-2). A test that reads one of those files
reads its fixture instead, made by ``scripts/evidence_fixtures.py``: a byte-for-byte
copy, or a slim extract with a sidecar naming its source's SHA-256.

A test names the ORIGINAL repository path, so the provenance stays in the test:

    from evidence_paths import evidence

    log = evidence("docs/handshake/artifactsround32/round32fullwholedisc.log")

``evidence()`` refuses a path with no fixture rather than returning one that
does not exist, because a test that globs a missing folder and finds nothing
passes on nothing (HR-2 §2: a defect, fixed on sight).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

FIXTURE_ROOT: Final[Path] = Path(__file__).resolve().parent / "fixtures" / "evidence"


def evidence(original: str) -> Path:
    """The fixture standing for the evidence file at ``original``."""
    path = FIXTURE_ROOT / original
    if not path.is_file():
        raise FileNotFoundError(
            f"no evidence fixture for {original}; make one with "
            "scripts/evidence_fixtures.py (copy, slim-report or slim-applog)"
        )
    return path


def evidence_dir(original_folder: str) -> Path:
    """The fixture folder standing for an evidence folder, which must hold files."""
    path = FIXTURE_ROOT / original_folder
    if not path.is_dir() or not any(path.iterdir()):
        raise FileNotFoundError(f"no evidence fixtures under {original_folder}")
    return path
