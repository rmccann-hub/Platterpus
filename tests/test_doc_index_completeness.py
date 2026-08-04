"""``docs/README.md`` must actually index every document it claims to index.

**Why this exists.** `CLAUDE.md` calls `docs/README.md` *"the canonical annotated
index"* and keeps a one-line-each summary beside it, with a parenthetical saying
*"so this list can't drift from it again; it did once, KDD-range v23 vs v25"*.
That parenthetical is the entire enforcement — a comment. The list drifted again
immediately: `docs/cyanrip-consumer-contract.md` was added, listed in `CLAUDE.md`,
and **never indexed in `docs/README.md`**, which is the file the prose calls
canonical. `docs/handshake/` — 24 files of binding correspondence — was reachable
from neither.

`tests/test_doc_links.py` names this exact failure in its own docstring — *"the
milder form where the text went stale rather than the target vanishing"* — and
then gates only the target-vanishing half. This file gates the other half.

**What is checked here that `test_doc_links.py` cannot see.** That gate asks
whether a link *resolves*; this one asks whether a document is *annotated*. A doc
mentioned once in passing prose has a resolving link and is not indexed — which is
precisely how a reader loses it. So the unit here is a **table row with a
description of substance**, not a mention.

Subdirectories are deliberately out of scope: `docs/archive/` and
`docs/handshake/` each carry their own README, and the handshake round files are
correspondence, not documentation — indexing 30 of them in the top-level map would
bury the 20 documents a contributor actually needs. That exemption is only
honest if the top-level map *routes a reader to them*, which is asserted below.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DOCS = _REPO_ROOT / "docs"
_DOCS_INDEX = _DOCS / "README.md"
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"

#: The index is its own entry point, so it does not index itself.
_NOT_INDEXED_BY_DESIGN: frozenset[str] = frozenset({"README.md"})

#: Characters of description a row needs before it counts as an *annotation*
#: rather than a bare listing. `docs/README.md`'s own rows run to paragraphs; a
#: row reading "| [`foo.md`](foo.md) | TODO |" tells a reader nothing about
#: whether to open it, which is the only question an index answers.
_MIN_ANNOTATION_CHARS = 40


def _top_level_docs() -> list[Path]:
    """Every markdown document directly under ``docs/``, sorted."""
    return sorted(p for p in _DOCS.glob("*.md") if p.is_file())


def _index_text() -> str:
    return _DOCS_INDEX.read_text(encoding="utf-8")


def _table_rows(text: str) -> list[list[str]]:
    """Every markdown table row in ``text``, as its list of cells.

    Header and separator rows are dropped — a separator (`|---|---|`) would
    otherwise read as a row whose cells are dashes.
    """
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def _annotation_for(rows: list[list[str]], name: str) -> str | None:
    """The description cell of the index row that links ``name``, if any.

    Matched on the row's **first** cell, because that is the column the index
    uses for the document's identity. A document merely *mentioned* in another
    row's prose (`see cyanrip-handshake.md`) is a cross-reference, not an entry.
    """
    target = re.compile(rf"\]\(\s*{re.escape(name)}\s*\)")
    for cells in rows:
        if len(cells) >= 2 and target.search(cells[0]):
            return " ".join(cells[1:])
    return None


def test_every_top_level_doc_has_an_annotated_index_row() -> None:
    """The finding this file was written for.

    `cyanrip-consumer-contract.md` was in `CLAUDE.md`'s companion list and absent
    from the index that list calls canonical.
    """
    rows = _table_rows(_index_text())
    docs = [p for p in _top_level_docs() if p.name not in _NOT_INDEXED_BY_DESIGN]

    unindexed: list[str] = []
    thin: list[str] = []
    for path in docs:
        annotation = _annotation_for(rows, path.name)
        if annotation is None:
            unindexed.append(path.name)
        elif len(annotation) < _MIN_ANNOTATION_CHARS:
            thin.append(f"{path.name} ({len(annotation)} chars)")

    assert not unindexed, (
        "docs/README.md is the canonical annotated index (CLAUDE.md says so), and "
        "these documents have no row in it: " + ", ".join(unindexed)
    )
    assert not thin, (
        "these index rows exist but say too little to be an annotation — an index "
        "answers 'should I open this': " + ", ".join(thin)
    )
    # Floor: this must not pass by finding nothing to check.
    assert len(docs) >= 15, f"only {len(docs)} top-level docs found — glob broken?"
    assert len(rows) >= 20, f"the index has only {len(rows)} table rows"


def test_no_index_row_links_a_document_that_is_gone() -> None:
    """The converse, scoped to *rows* so history stays legal.

    A consolidation retires filenames, and the index rightly keeps saying
    "(Absorbed the former `best-practices.md`.)" — that is a useful historical
    note in a row's prose, not a stale entry. What must not survive is a **row
    whose identity cell points at a file that no longer exists**, which is how a
    merged-away document keeps looking like a live one.
    """
    rows = _table_rows(_index_text())
    dangling: list[str] = []
    checked = 0
    for cells in rows:
        if not cells:
            continue
        for match in re.finditer(r"\]\(\s*(?P<target>[^)#\s]+\.md)\s*\)", cells[0]):
            target = match.group("target")
            checked += 1
            if not (_DOCS / target).resolve().is_file():
                dangling.append(target)
    assert not dangling, (
        "docs/README.md has index rows for documents that no longer exist: "
        + ", ".join(sorted(set(dangling)))
    )
    assert checked >= 20, f"only {checked} row targets examined — pattern broken?"


def test_claude_mds_companion_list_agrees_with_the_index() -> None:
    """The two lists must not disagree about what exists.

    `CLAUDE.md` is the file guaranteed to be read every session and it
    daisy-chains to the index; a document in one list and not the other means a
    session picks up a different map depending on which file it happened to read.
    """
    claude = _CLAUDE_MD.read_text(encoding="utf-8")
    rows = _table_rows(_index_text())
    named_in_claude = {
        m.group("name") for m in re.finditer(r"docs/(?P<name>[\w.-]+\.md)", claude)
    }
    # Round files and archive documents are cited by CLAUDE.md as examples, not
    # as companions; they are indexed by their own subdirectory READMEs.
    named_in_claude = {
        n
        for n in named_in_claude
        if (_DOCS / n).exists() and n not in _NOT_INDEXED_BY_DESIGN
    }
    missing = sorted(n for n in named_in_claude if _annotation_for(rows, n) is None)
    assert not missing, (
        "CLAUDE.md names these companion documents but docs/README.md — which "
        "CLAUDE.md calls the canonical index — has no row for them: "
        + ", ".join(missing)
    )
    # Floor + non-triviality: CLAUDE.md's companion list is substantial, and a
    # regex that silently stopped matching would make this vacuous.
    assert len(named_in_claude) >= 10, (
        f"only {len(named_in_claude)} docs/ companions found in CLAUDE.md — has "
        "the reference style changed?"
    )


def test_the_index_routes_to_the_subdirectory_indexes() -> None:
    """Subdirectories are out of scope here *because* they self-index.

    That is only a valid exemption if the top-level map actually routes a reader
    to them — otherwise "indexed elsewhere" means "not indexed". `docs/handshake/`
    failed this: 24 files of binding release correspondence, its own README, and
    no route from the canonical map.
    """
    text = _index_text()
    for sub in ("archive", "handshake"):
        readme = _DOCS / sub / "README.md"
        assert readme.is_file(), (
            f"docs/{sub}/ has no README, so the exemption this test's docstring "
            "grants it is no longer true"
        )
        count = len(list((_DOCS / sub).rglob("*.md")))
        assert re.search(rf"\]\(\s*{sub}/", text), (
            f"docs/README.md never links docs/{sub}/, so the {count} documents "
            "under it are unreachable from the canonical index"
        )
        assert count >= 2, f"docs/{sub}/ holds only {count} files — still a dir?"
