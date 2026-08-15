"""The transport envelope must be *exactly* the laps it claims to carry.

A bundle is a promise of completeness — "these are our three laps, verbatim" —
and this project has a standing rule about those: a document that promises
completeness needs a sweep, not a comment, because it decays **invisibly**. Nobody
re-reads an envelope to check whether a lap changed under it, and a stale envelope
is worse than no envelope: it looks complete, and the receiver has no way to tell.

So the guard is mechanical in three directions:

1. **The committed bundle is byte-identical to what the generator produces**, so
   editing a lap without repacking fails here rather than at the fork's end.
2. **Splitting it reproduces the source files byte-for-byte**, proved by reading
   both — not by trusting the writer, and not by comparing the writer to itself.
3. **Its name cannot match the `round-*.md` glob** either gate uses, because the
   bundle contains three `HANDSHAKE-…` headers in its body and would otherwise be
   parseable as a lap. That is the exact hazard the fork flagged for their own
   state document, and a filename is the kind of thing a later tidy-up "improves".
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from scripts import emit_handshake_bundle as bundle

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def test_the_committed_bundle_is_exactly_what_the_generator_produces() -> None:
    """The staleness gate. Fails the moment a lap is edited without repacking."""
    assert bundle.BUNDLE_PATH.exists(), "the bundle is not committed"
    assert bundle.BUNDLE_PATH.read_text(encoding="utf-8") == bundle.render(
        bundle.read_parts()
    ), (
        "the bundle is stale — a lap changed since it was packed. Regenerate: "
        "python scripts/emit_handshake_bundle.py"
    )


def test_splitting_the_bundle_reproduces_every_source_file_byte_for_byte() -> None:
    """The round trip, read off disk at both ends.

    Deliberately compares the split output against the **source files**, not
    against the parts the packer held in memory: two implementations agreeing is
    not either one being correct when they share an ancestor, and here the packer
    and the manifest hash *do* share one.
    """
    parts = bundle.split_bundle(bundle.BUNDLE_PATH.read_text(encoding="utf-8"))

    # Non-triviality floor: an empty split would satisfy every assertion below.
    assert len(parts) == len(bundle.BUNDLE_PARTS) >= 3, parts.keys()

    for source in bundle.BUNDLE_PARTS:
        assert source.name in parts, f"{source.name} is missing from the bundle"
        assert parts[source.name] == source.read_bytes(), (
            f"{source.name} does not survive the round trip byte-for-byte"
        )


def test_every_manifest_hash_matches_the_bytes_it_labels() -> None:
    """A hash beside content nobody checks is decoration."""
    text = bundle.BUNDLE_PATH.read_text(encoding="utf-8")
    matches = list(bundle.PART_RE.finditer(text))
    assert len(matches) >= 3, "the delimiters did not parse"
    for match in matches:
        data = (match["body"] + "\n").encode("utf-8")
        assert hashlib.sha256(data).hexdigest() == match["sha"], match["name"]


def test_the_bundle_name_cannot_be_read_as_a_lap_by_either_gate() -> None:
    """`round-*.md` must never match it — on any filesystem, either case.

    Both projects' gates glob that pattern, and the bundle body carries three wire
    headers. A name that matched would most likely resolve as lap 2 (the first
    header in the file) and could displace the round's real latest lap — which is
    how a `GO` once closed a round whose latest lap said `HOLD`.
    """
    name = bundle.BUNDLE_PATH.name
    directory = bundle.BUNDLE_PATH.parent

    assert bundle.BUNDLE_PATH not in set(directory.glob("round-*.md"))
    # Case-insensitive filesystems too: the glob is checked against a lowered
    # name, so an upper-case rename cannot sneak past on macOS or Windows.
    assert not name.lower().startswith("round-")
    # CLAUDE.md -> "Artifact filenames that cross machines": lowercase a-z0-9.
    assert name.removesuffix(".md").isalnum() and name.removesuffix(".md").islower()


def test_the_bundle_declares_no_verdict_of_its_own() -> None:
    """It is an envelope. A wire header at column 0 in its own preamble would
    make it a lap, and a lap that quoted three others would be the falsified
    merged round file both projects have agreed not to produce."""
    text = bundle.BUNDLE_PATH.read_text(encoding="utf-8")
    preamble = text.split(bundle.BEGIN_FMT.split(" BEGIN ")[0], 1)[0]
    offenders = [
        line
        for line in preamble.splitlines()
        if line.startswith("HANDSHAKE-") and not line.startswith("HANDSHAKE-…")
    ]
    assert not offenders, offenders


@pytest.mark.parametrize("part", bundle.BUNDLE_PARTS, ids=lambda p: p.name)
def test_each_packed_lap_still_carries_its_own_wire_header(part: Path) -> None:
    """Packing must not disturb what makes a lap a lap.

    Checked per part rather than over the whole bundle so a failure names the
    file, and asserted on the *split* output rather than the source, since the
    question is whether the envelope preserved it.
    """
    restored = bundle.split_bundle(bundle.BUNDLE_PATH.read_text(encoding="utf-8"))[
        part.name
    ].decode("utf-8")
    assert restored.startswith("HANDSHAKE-PROTOCOL:"), (
        f"{part.name} lost its column-0 wire header in the envelope"
    )
    for field in ("HANDSHAKE-ROUND", "HANDSHAKE-LAP", "HANDSHAKE-VERDICT"):
        assert f"\n{field}:" in f"\n{restored}", f"{part.name} lost {field}"
