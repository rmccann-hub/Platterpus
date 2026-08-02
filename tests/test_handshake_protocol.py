"""The release handshake is bidirectional, and something has to say so.

Platterpus and cyanrip share a parsed seam: our reader is shaped by their
writer. Neither side can verify a change to it alone, and **both sides have
been wrong about the other** — an indentation ask of ours shifted every `-Z`
verdict by one track, and their FIXPLAN's "a fork cannot fix this" was true of
signal handlers but not of `setvbuf`.

So the rule is two files per round, in both directions, with the release gated
on both. That rule lives in `docs/cyanrip-handshake.md`.

**Why this file exists at all:** `docs/testing.md` §5.m, written the same day,
says a prose rule becomes real only when something executes it. A handshake
protocol documented and then forgotten would be that lesson failing on its
first opportunity. These tests are cheap and they keep the doc, its links and
its two direction-specs from quietly rotting apart.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parents[1]
_DOC = _ROOT / "docs" / "cyanrip-handshake.md"
_CLAUDE = _ROOT / "CLAUDE.md"
_DOCS_INDEX = _ROOT / "docs" / "README.md"


def test_the_protocol_document_exists() -> None:
    assert _DOC.is_file(), (
        "docs/cyanrip-handshake.md is the single home for the release handshake"
    )


def test_it_specifies_BOTH_directions() -> None:
    """One-directional is the failure mode. A report is a claim; a handshake is
    a claim plus an independent check, and the check is what has found the
    truth every time so far."""
    text = _DOC.read_text(encoding="utf-8")
    assert "What Platterpus sends" in text
    assert "What cyanrip sends" in text
    # The return leg — the one most likely to be skipped, because it feels like
    # a formality once the other side has "already answered".
    assert "verification file" in text.lower()
    assert "second handshake" in text.lower()


def test_it_states_that_the_release_is_gated_on_both() -> None:
    text = _DOC.read_text(encoding="utf-8").lower()
    assert "neither project ships until" in text
    assert "both" in text


def test_the_cyanrip_return_spec_enumerates_every_section() -> None:
    """The return file's shape is pinned so a round cannot come back missing
    the awkward parts — the revert-proof statement and "what did you find wrong
    in OUR output" are the two that would otherwise evaporate."""
    text = _DOC.read_text(encoding="utf-8")
    for marker in (
        "commit SHA",
        "measured",
        "read from source",
        "unverified",
        "log output text",
        "No changes",
        "golden reference log",
        "Revert-proof statement",
        "found wrong in Platterpus's output",
    ):
        assert marker in text, f"the cyanrip return spec lost: {marker!r}"


def test_it_says_when_a_handshake_is_required() -> None:
    """A protocol with no scope gets applied to nothing. The table has to name
    the parsed seam and the release itself."""
    text = _DOC.read_text(encoding="utf-8")
    assert "when a handshake is required" in text.lower()
    assert "container to a new fork pin" in text


def test_claude_md_points_at_it_rather_than_restating_it() -> None:
    """Single-home rule: the always-loaded file links, it does not duplicate.
    Two copies of a protocol is how the two get to disagree."""
    claude = _CLAUDE.read_text(encoding="utf-8")
    assert "cyanrip-handshake.md" in claude, (
        "CLAUDE.md must link the handshake protocol, or nobody reads it"
    )


def test_the_docs_index_lists_it() -> None:
    """docs/README.md is the canonical annotated index; an unlisted doc is a
    doc nobody finds."""
    assert "cyanrip-handshake.md" in _DOCS_INDEX.read_text(encoding="utf-8")


def test_the_shared_rigour_bar_is_stated_for_both_sides() -> None:
    """The bar is not ours to hold alone — a fork that skips revert-proving
    hands us fixes we cannot trust."""
    text = _DOC.read_text(encoding="utf-8")
    assert "Both sides hold to these" in text
    assert "Revert-prove every fix" in text
