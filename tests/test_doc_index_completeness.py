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


#: Any `docs/…​.md` path written anywhere in a document — as a markdown link
#: target, inside backticks, or in bare prose. Subdirectory paths
#: (`docs/archive/foo.md`) are included, because a reader follows those too.
#: Bounded quantifiers per the project rule; no `)` or backtick can be part of a
#: path segment, so the pattern stops cleanly at either delimiter.
_DOCS_PATH_ANYWHERE = re.compile(
    r"docs/(?P<rel>[A-Za-z0-9._-]{1,80}(?:/[A-Za-z0-9._-]{1,80}){0,3}\.md)"
)


def _docs_paths_named_in(text: str) -> list[str]:
    """Every ``docs/…`` path the text names, in order, duplicates kept.

    Kept as a list rather than a set so the floor below counts *references*
    examined, not distinct filenames — the question this gate asks is "does
    every pointer land", and ten pointers at one file is ten chances to be
    wrong about that file.
    """
    return [m.group("rel") for m in _DOCS_PATH_ANYWHERE.finditer(text)]


def test_every_docs_path_named_in_claude_md_resolves() -> None:
    """A doc `CLAUDE.md` merely *mentions* must still exist.

    **The gap this closes, and why neither existing gate could see it.**
    `CLAUDE.md` names documents two ways: as markdown links
    (`[docs/testing.md](docs/testing.md)`) and, more often, in **plain
    backticks** — the CI/release section named the AppImage-testing doc that way,
    and a whole prose list of "everything else under `docs/`" sits beside the
    companion list.

    * `tests/test_doc_links.py` only sees `[text](target)` — a backticked path is
      not a link, so it is invisible there.
    * `test_claude_mds_companion_list_agrees_with_the_index` above *does* read
      every `docs/…md` string in `CLAUDE.md`, and then filters the set with
      ``if (_DOCS / n).exists()``. That filter is the hole: it is there so
      archive/handshake examples don't have to be indexed, but it means a
      document that has been **deleted or moved** silently drops out of the set
      instead of failing. Deleting a doc `CLAUDE.md` mentions therefore left a
      stale reference that *no* test could see.

    So this asserts the plainest possible thing about the one file every session
    is guaranteed to read: **every path it names is a path that is there.** It
    caught the four docs consolidated away on 2026-08-06 (the merge left
    `CLAUDE.md` still pointing at the former `appimage-testing.md`).

    Written as a bare label, not with a `docs/` prefix, per the convention
    `CLAUDE.md` states for naming a retired file — the prefixed form reads as a
    live pointer, and the wider sweep below now fails on one. This docstring was
    the first thing that sweep caught, which is the convention earning its keep.
    """
    claude = _CLAUDE_MD.read_text(encoding="utf-8")
    named = _docs_paths_named_in(claude)

    dangling = sorted({rel for rel in named if not (_DOCS / rel).is_file()})
    assert not dangling, (
        "CLAUDE.md names these docs/ paths but the files do not exist — a "
        "session reading the one always-loaded file is sent to nothing. Merge "
        "or delete a doc and its CLAUDE.md references go with it: "
        + ", ".join(dangling)
    )
    # FLOOR. Without it this passes on a CLAUDE.md whose reference style
    # changed under the regex — a gate satisfied by finding nothing.
    assert len(named) >= 10, (
        f"only {len(named)} docs/ paths found in CLAUDE.md — the reference "
        "style has changed and this gate is passing by finding nothing"
    )


def test_the_docs_path_sweep_catches_a_vanished_file() -> None:
    """Proven against constructed text, not by reasoning about the regex.

    A detector that cannot fail is decoration. This pins the three shapes the
    sweep above must handle — a markdown link, a backticked path, and a
    subdirectory path — and pins the one it must *not* fire on: a bare
    directory mention (`docs/archive/`) is not a document reference.
    """
    sample = (
        "See [the guide](docs/testing.md) and `docs/gone.md` for detail.\n"
        "The graduation map lives in docs/archive/README.md; dated files are\n"
        "under docs/archive/ generally.\n"
    )
    found = _docs_paths_named_in(sample)
    assert found == ["testing.md", "gone.md", "archive/README.md"], found

    # And the real predicate separates present from absent, on real files.
    assert (_DOCS / "testing.md").is_file()
    assert not (_DOCS / "gone.md").is_file()


#: Surfaces where a `docs/…md` path reads as a **live pointer** — something a
#: contributor will follow *now*. Derived by walking these roots rather than listed
#: file by file, so a module added next month is covered the day it lands.
_LIVE_POINTER_ROOTS: tuple[str, ...] = (
    "src",
    "tests",
    "scripts",
    "build",
    ".github/workflows",
)

#: Root-level and `docs/` files that are live maps rather than dated record.
_LIVE_POINTER_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "PLANNING.md",
    "TASKS.md",
    "DEPENDENCIES.md",
    "SECURITY.md",
)

#: **Deliberately excluded, and the reason matters more than the list.** These are
#: *dated record*, not maps: they state what was true on a date. Repointing a link
#: inside them to a file that did not exist yet would falsify the record, which is a
#: worse outcome than a historical pointer that no longer resolves. `CHANGELOG.md`
#: and `docs/session-log.md` are ours; `docs/handshake/` is correspondence exchanged
#: with another project, and we do not edit documents we received. `docs/archive/`
#: holds retired investigations whose whole purpose is to preserve what they said.
_DATED_RECORD: tuple[str, ...] = (
    "CHANGELOG.md",
    "docs/session-log.md",
    "docs/archive",
    "docs/handshake",
)

#: Synthetic paths that exist to NOT exist — fixture strings in tests that prove the
#: dangling-pointer detectors above can actually fail. A ratchet with a written reason
#: per entry: it may shrink, never grow. Adding a real dead link here instead of
#: fixing it defeats the sweep.
_DELIBERATELY_ABSENT: dict[str, str] = {
    "gone.md": "test_the_docs_path_sweep_catches_a_vanished_file's absent case",
    "archive/foo.md": "same test's subdirectory case",
    "handshake/nope.md": "test_round_digest.py's missing-file case",
    "handshake/verified/round-N.md": "test_fork_source.py's filename TEMPLATE, "
    "with a literal N — never a real path",
    "definitely-not-here.md": "the absent half of "
    "test_the_live_pointer_sweep_catches_a_dead_link_in_code, which proves this "
    "sweep can fail at all",
}


def _live_pointer_files() -> list[Path]:
    """Every file whose `docs/…md` mentions are pointers a reader would follow."""
    seen: list[Path] = []
    for root in _LIVE_POINTER_ROOTS:
        for path in sorted((_REPO_ROOT / root).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".yml", ".yaml", ".sh"}:
                seen.append(path)
    for name in _LIVE_POINTER_FILES:
        candidate = _REPO_ROOT / name
        if candidate.is_file():
            seen.append(candidate)
    for path in sorted(_DOCS.rglob("*.md")):
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if not any(rel == d or rel.startswith(d + "/") for d in _DATED_RECORD):
            seen.append(path)
    return seen


def test_every_docs_pointer_in_a_live_surface_resolves() -> None:
    """The same rule as the CLAUDE.md gate above, applied to the whole tree.

    **Why this exists as a separate, wider sweep.** `CLAUDE.md` rule #7 says
    retiring a file means retiring *every inbound link to it in the same commit* —
    and the only thing enforcing that read `CLAUDE.md` alone. So the rule was held at
    the place it was learned (a consolidation had left `CLAUDE.md` pointing at
    `appimage-testing.md`) and nowhere else, which is this session's recurring shape
    for the sixth time.

    Sweeping the rest of the tree on 2026-08-18 found six live pointers into files
    deleted weeks earlier, in code as well as docs:

    * `.github/workflows/appimage.yml` → the retired AppImage-testing doc
    * `adapters/transcode.py` and `config.py` → the archived multi-format design
    * `update_install.py` and `update_signing.py` → the retired signing ritual,
      which is the *worst* of the six: it is the fail-closed arming procedure, so a
      maintainer who follows that pointer under release pressure lands on nothing
    * `tests/test_argv_surface_agreement.py` → a handshake artifact path that never
      existed in that spelling

    Dated record is excluded on purpose — see `_DATED_RECORD`. A changelog entry is a
    statement about a date, and "fixing" its links would make it lie.
    """
    files = _live_pointer_files()
    dangling: list[str] = []
    examined = 0
    for path in files:
        rel_file = path.relative_to(_REPO_ROOT).as_posix()
        for rel in _docs_paths_named_in(path.read_text(encoding="utf-8")):
            examined += 1
            if rel in _DELIBERATELY_ABSENT or (_DOCS / rel).is_file():
                continue
            dangling.append(f"{rel_file} → docs/{rel}")

    assert not dangling, (
        "these live surfaces point at docs/ files that do not exist. Retiring a "
        "doc means retiring every inbound link in the same commit (CLAUDE.md rule "
        "#7) — repoint each at the section that absorbed it, or at the archived "
        "path:\n  " + "\n  ".join(sorted(dangling))
    )
    # FLOORS. Two, because either one alone can be satisfied by finding nothing:
    # a glob that stops matching yields no files, and a regex that stops matching
    # yields no pointers from plenty of files.
    assert len(files) >= 100, (
        f"only {len(files)} live-pointer files found — the roots have moved and "
        f"this sweep is passing over almost nothing"
    )
    assert examined >= 40, (
        f"only {examined} docs/ pointers examined across {len(files)} files — the "
        f"reference style has changed and this gate is passing by finding nothing"
    )


def test_the_deliberately_absent_list_is_still_deliberately_absent() -> None:
    """Every exemption must still be *needed*, or the ratchet only ever loosens.

    An allowlist entry whose file has since been created is no longer an exemption;
    it is a stale hole that would let a genuinely dead pointer of the same name
    through. So each entry is checked to be absent — the exact opposite of the
    assertion it exempts.
    """
    assert _DELIBERATELY_ABSENT, "the allowlist is empty — delete it rather than ship"
    for rel, reason in _DELIBERATELY_ABSENT.items():
        assert not (_DOCS / rel).is_file(), (
            f"`docs/{rel}` now exists, so its exemption ({reason}) is stale. Remove "
            f"the entry: the sweep can check it for real now."
        )


def test_the_live_pointer_sweep_catches_a_dead_link_in_code() -> None:
    """Revert-proof, against constructed text rather than by reading the regex.

    The failure mode being excluded is a sweep that walks 100+ files, matches
    nothing in any of them, and reports success. This proves the predicate the sweep
    is built from separates present from absent on real paths.
    """
    sample = "# See docs/testing.md for the rules, and docs/definitely-not-here.md\n"
    found = _docs_paths_named_in(sample)
    assert found == ["testing.md", "definitely-not-here.md"], found
    assert (_DOCS / found[0]).is_file()
    assert not (_DOCS / found[1]).is_file()


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


# --- Section ids must be unique, because they are cited from other files ---------


#: A cited section id: ``5.ag``, ``§5.ah``, ``3.12a``, ``6.1``. Both spellings of the
#: prefix, because the collision that prompted this check spanned them — one heading
#: wrote ``### §5.ag`` and the other ``### 5.ag``, which is exactly why a reader's eye
#: slid past it.
_SECTION_ID = re.compile(r"^#{2,4}\s+§?(\d+\.[0-9a-z]+)\b", re.MULTILINE)


def test_no_doc_reuses_a_section_id() -> None:
    """A cited id that resolves to two places is a broken cross-reference.

    Found 2026-08-18 by reading, not by a check: ``docs/testing.md`` carried **two**
    ``5.ag`` sections and **two** ``5.ah`` sections, added five days apart. Three files
    cite ``§5.ah`` and two cite ``§5.ag``, so every one of those references was
    ambiguous — and the ambiguity is invisible from either end. The citing file looks
    correct, each section looks correct, and only counting reveals it.

    This is the same class as the promise-of-completeness sweeps above (§5.af): a
    numbered section is a *promise that the number identifies it*, and that promise
    decays silently as sections are appended. Deriving the ids and counting them is the
    check the parenthetical-comment version of this rule could not be.

    Scoped to headings that carry an ``N.xx`` id, which is the convention that is cited;
    plain prose headings are unaffected.
    """
    offenders: list[str] = []
    examined = 0
    for path in sorted(_DOCS.rglob("*.md")) + [_CLAUDE_MD]:
        ids = _SECTION_ID.findall(path.read_text(encoding="utf-8"))
        if not ids:
            continue
        examined += 1
        seen: dict[str, int] = {}
        for ident in ids:
            seen[ident] = seen.get(ident, 0) + 1
        for ident, count in sorted(seen.items()):
            if count > 1:
                offenders.append(
                    f"{path.relative_to(_REPO_ROOT)}: §{ident} appears {count} times"
                )

    # Floor: if no document was found to carry numbered sections, this check examined
    # nothing and would pass for a repo whose docs had all been deleted.
    assert examined >= 2, (
        f"only {examined} document(s) were found carrying `N.xx` section ids — the "
        "pattern has gone stale and this check is passing by finding nothing"
    )
    assert not offenders, (
        "duplicate section ids — every cross-reference to these is ambiguous:\n  "
        + "\n  ".join(offenders)
    )


def test_the_duplicate_id_check_would_catch_the_shipped_collision() -> None:
    """Non-triviality, measured against the exact text that shipped.

    Two headings from `docs/testing.md` as they stood on 2026-08-18, one with the ``§``
    and one without — the spelling difference is why the collision survived a reader's
    eye, so the detector has to be blind to it.
    """
    shipped = (
        "### §5.ag — A conformance table is run, not read\n"
        "body\n"
        "### 5.ag — An implemented capability is not a capability either\n"
    )
    ids = _SECTION_ID.findall(shipped)
    assert ids.count("5.ag") == 2, (
        f"the detector does not see the shipped collision; it found {ids}"
    )
