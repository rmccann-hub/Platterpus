# SPDX-License-Identifier: GPL-3.0-only
"""`HANDSHAKE-SOURCE-ANCHOR` must pin OUR source, and be computed, not typed.

**The defect, found by the cyanrip fork in round 7 and confirmed by recomputing
rather than accepted on their word** (`CLAUDE.md`: a correction is not
pre-verified). Every lap of ours that carried the field declared:

```
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 7dc313815850eb60
HANDSHAKE-SHARED-HASHES: … seam-commands=7dc313815850eb60c1048f150c9279…
```

`7dc313815850eb60` is character-for-character the first 16 hex of the
`seam-commands` hash on the next line. The anchor was a **copy of a shared
file's hash** — a file neither project owns and which says nothing about our
source — so the field pinned nothing, in every lap that declared it, while
looking exactly like a value that did.

The generalisable lesson is the mechanism, not the typo: **a field whose value is
typed by hand next to a similar-looking value will eventually be the other one.**
So the anchor is computed (`scripts/handshake.py::source_anchor`), and the tests
below encode the two things that were wrong: it must be derived from our source,
and it must not be any shared file's hash.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

_REPO = Path(__file__).resolve().parents[1]

#: The shared files — the ones the anchor was accidentally taken from. Neither
#: project owns these; a hash of one is not a statement about our source.
_SHARED = ("handshake-protocol.md", "seam-rules.md", "seam-commands.md")


def _handshake() -> ModuleType:
    script = _REPO / "scripts" / "handshake.py"
    spec = importlib.util.spec_from_file_location("handshake_anchor", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _shared_prefixes() -> set[str]:
    out: set[str] = set()
    for name in _SHARED:
        path = _REPO / "docs" / name
        if path.is_file():
            out.add(hashlib.sha256(path.read_bytes()).hexdigest()[:16])
    return out


def test_the_anchor_is_sixteen_hex_and_stable() -> None:
    anchor = _handshake().source_anchor()
    assert re.fullmatch(r"[0-9a-f]{16}", anchor), anchor
    assert anchor == _handshake().source_anchor(), "the anchor is not deterministic"


def test_the_anchor_is_not_a_shared_files_hash() -> None:
    """The exact bug, as an assertion.

    Not "the anchor is not `7dc313815850eb60`" — that would pass the moment the
    shared file changed, while the underlying mistake (taking the value from the
    wrong hash) stayed available. It compares against the shared hashes as they
    are *now*, so the check keeps meaning what it says.
    """
    shared = _shared_prefixes()
    assert shared, "no shared files found — this check would pass vacuously"
    assert _handshake().source_anchor() not in shared


def test_the_anchor_covers_files_that_exist_and_are_ours() -> None:
    """A floor: an anchor over a list of missing files still hashes to something.

    Without this the field could go back to describing nothing simply by having
    its file list rot, and the value would keep looking healthy.
    """
    handshake = _handshake()
    files = handshake.SOURCE_ANCHOR_FILES
    assert len(files) >= 5, "implausibly few files for the seam's source"
    missing = [rel for rel in files if not (_REPO / rel).is_file()]
    assert not missing, f"the anchor names files that do not exist: {missing}"
    assert all(rel.startswith("src/platterpus/") for rel in files), (
        "the anchor must cover OUR source; the fork's covers theirs"
    )


def test_the_anchor_moves_when_the_source_moves(tmp_path: Path) -> None:
    """Non-triviality: an anchor that never changes is decoration.

    Builds a miniature tree rather than touching the real one, so the assertion
    is about the function rather than about whatever the repo happens to contain.
    """
    handshake = _handshake()
    for rel in handshake.SOURCE_ANCHOR_FILES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original\n", encoding="utf-8")
    before = handshake.source_anchor(tmp_path)
    (tmp_path / handshake.SOURCE_ANCHOR_FILES[0]).write_text("edited\n")
    after = handshake.source_anchor(tmp_path)
    assert before != after, "editing a covered file did not move the anchor"


def test_a_rename_moves_the_anchor_too(tmp_path: Path) -> None:
    """Path is hashed with the content, so two files cannot swap unnoticed."""
    handshake = _handshake()
    files = handshake.SOURCE_ANCHOR_FILES
    for index, rel in enumerate(files):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content {index}\n", encoding="utf-8")
    before = handshake.source_anchor(tmp_path)
    # Swap two files' contents. A content-only hash of a sorted set would not
    # notice; hashing `path\0content\0` does.
    first, second = tmp_path / files[0], tmp_path / files[1]
    first_text, second_text = first.read_text(), second.read_text()
    first.write_text(second_text)
    second.write_text(first_text)
    assert handshake.source_anchor(tmp_path) != before


def test_the_newest_lap_declares_the_computed_anchor() -> None:
    """Read the artifact: the value we sent must be the value we compute.

    Scoped to the **newest** verification file. Older laps carry the wrong value
    and must not be edited — the shared protocol §3 is *never edit a file already
    sent*, and rewriting history to make a test pass would be a worse bug than
    the one being fixed.
    """
    handshake = _handshake()
    verified = sorted(
        (_REPO / "docs" / "handshake" / "verified").glob("round-*.md"),
        key=handshake.sort_key,
    )
    assert verified, "no verification files"
    newest = verified[-1]
    text = newest.read_text(encoding="utf-8")
    match = re.search(r"^HANDSHAKE-SOURCE-ANCHOR:.*?([0-9a-f]{16})", text, re.MULTILINE)
    if match is None:
        return  # the field is optional; absence is not this test's finding
    assert match.group(1) == handshake.source_anchor(), (
        f"{newest.name} declares source anchor {match.group(1)}, but the source "
        f"hashes to {handshake.source_anchor()}"
    )
