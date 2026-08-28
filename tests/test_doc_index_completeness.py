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
    # **A shared file's internal paths are the fork's layout, and we may not edit
    # them.** `docs/OWNERSHIP.md` is byte-identical in both repositories and owned
    # by neither, so its hash is compared on every lap; repointing this mention at
    # our own spelling would break the byte-identity the file exists to have. The
    # document it names is real and we hold it — at `docs/handshake-protocol.md`,
    # flat, where the fork keeps it at `docs/handshake/PROTOCOL.md`. Raised with
    # them in round 14 lap 18: a shared file naming a path that resolves in only
    # one of the two repositories is a small defect in the shared file, and the
    # fix is theirs and ours jointly, not a unilateral edit here.
    "handshake/PROTOCOL.md": "the cyanrip fork's path for the shared protocol "
    "document, named inside the byte-identical docs/OWNERSHIP.md; ours is at "
    "docs/handshake-protocol.md and the shared file must not be edited to say so",
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


#: Documents that are REGENERATED from code, so a `file.md:NN` citation into them
#: is a pointer at a line number that moves on the next parser change — silently,
#: because prose is not diffed against the file it cites.
#:
#: **Derived, not listed** — read off each `scripts/emit_*.py`'s own
#: ``OUTPUT_PATH``, so a third generated page joins this rule the day it is
#: written. A typed list here would be the same hand-maintained field that rotted
#: in the consumer contract's own `_FORK_ONLY_RULES`, in a test written *about*
#: stale cross-references.
#:
#: Not taken from `test_doc_version_stamps._EXEMPT_GENERATED`, which looks like the
#: registry for this and is not: that map answers *"which docs are exempt from a
#: version stamp"* and carries one of the two generated pages, because the other
#: embeds `__version__` and therefore does get restamped. Two different questions.
#: An ``OUTPUT_PATH`` declaration in a generator, e.g.
#: ``OUTPUT_PATH: Path = _REPO_ROOT / "docs" / "script-language.md"``.
_GENERATOR_OUTPUT = re.compile(
    r'^OUTPUT_PATH\b[^\n]*?"(?P<name>[A-Za-z0-9._-]+\.md)"\s*$', re.MULTILINE
)


def _generated_doc_basenames() -> frozenset[str]:
    """Every ``docs/*.md`` written by a generator script, by basename.

    Read out of each generator's **source** rather than by importing it. Importing
    was the first version and it is the wrong tool twice over: these scripts pull in
    the whole application (one of them imports PySide6 transitively) at collection
    time, and one of them — `emit_envelope.py` — cannot be exec'd from a bare spec
    at all, because `@dataclass` looks its own module up in `sys.modules` and a
    hand-built spec is not registered there. A regex over the declaration is a
    derivation with none of that surface.
    """
    found: set[str] = set()
    for script in sorted((_REPO_ROOT / "scripts").glob("emit_*.py")):
        for match in _GENERATOR_OUTPUT.finditer(
            script.read_text(encoding="utf-8", errors="replace")
        ):
            found.add(match.group("name"))

    # FLOOR. A regex derivation can stop matching without anything looking wrong —
    # a generator renaming its constant, or the formatter moving the closing quote
    # off the end of the line, and this returns an empty set. Every caller then
    # examines nothing and passes, which is the failure this whole module is about.
    #
    # Two is the measured count on 2026-08-21: `emit_dependency_contract.py` ->
    # cyanrip-consumer-contract.md and `emit_script_language.py` ->
    # script-language.md.
    #
    # KNOWN AND DELIBERATE EXCLUSION: `emit_envelope.py` declares `OUT`, not
    # `OUTPUT_PATH`, and writes into `docs/handshake/outbound/` rather than
    # `docs/`. It is out of scope for an index of top-level `docs/*.md` either
    # way, so the narrower pattern costs nothing here — stated so the next reader
    # does not have to re-derive that it is an omission on purpose. The
    # import-based version this replaced also missed it, for the same reason.
    assert len(found) >= 2, (
        f"only found {sorted(found)} generated docs. Either a generator renamed "
        f"its OUTPUT_PATH declaration or the pattern stopped matching it — and an "
        f"empty set here makes every caller pass having examined nothing."
    )
    return frozenset(found)


_GENERATED_DOCS: frozenset[str] = _generated_doc_basenames()

#: The citation shape this refuses: ``somepage.md:99``, ``:56,57,59`` or ``:103-105``.
_LINE_CITATION = re.compile(r"(?P<doc>[a-z0-9-]+\.md):(?P<lines>\d[\d,\s-]*)")


def test_no_prose_cites_a_generated_document_by_line_number() -> None:
    """**Measured drift, not a style preference.**

    `docs/cyanrip-known-issues.md` carried three citations into
    `docs/cyanrip-consumer-contract.md` by line number, and on 2026-08-21 **all
    three were already wrong** — checked against the file as committed at
    `faa2a39`, before that day's change touched it:

    * `:99` was cited for the AccurateRip result capture group; it was
      `track_pregap_source`.
    * `:56,57,59,64,65,66` were cited as six specific label rules; `:56` was
      `read_offset`.
    * `:103-105` were cited as the three speed/elapsed regexes; they were
      `track_accurip_offset`, `track_appended_silence`, `track_peak_kind_header`.

    Nothing could have caught it. The contract is regenerated from the parser's
    enumeration tables on every change, so **each of those numbers is a pointer
    into a file that renumbers itself**, and a citation is only ever wrong by
    silence — the prose keeps reading plausibly. This is the *"a comment where a
    check belongs is not a fix"* shape applied to a cross-reference.

    A rule NAME is the stable key and it is what the cited page is organised by, so
    the fix is to cite the row rather than its offset. This gate makes the fix
    stick.

    **How to record a citation you are RETIRING**, since a changelog entry about
    this very fix has to mention the three numbers and immediately tripped the gate
    on its own text: write them as prose — *"line 99 of that page"*, *"lines
    103-105"* — not in the ``page.md:NN`` form. Exactly the rule `CLAUDE.md` already
    states for a retired document, where a dead file is named as *a label, not a
    path*, because the path form reads as a live pointer. No allow-list, and
    deliberately none: an exemption for `CHANGELOG.md` would exempt the one file a
    stale citation is most likely to be copied onward from.
    """
    offenders: list[str] = []
    examined = 0
    for path in sorted(_REPO_ROOT.rglob("*.md")):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        examined += 1
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            for match in _LINE_CITATION.finditer(line):
                if match.group("doc") in _GENERATED_DOCS:
                    offenders.append(
                        f"{path.relative_to(_REPO_ROOT)}:{line_no} cites "
                        f"{match.group('doc')}:{match.group('lines').strip()}"
                    )
    assert examined >= 30, (
        f"only {examined} Markdown files walked — the sweep has stopped finding the "
        f"docs and would pass for an empty repository"
    )
    assert len(_GENERATED_DOCS) >= 2, (
        f"only {sorted(_GENERATED_DOCS)} derived as generated pages; two were "
        f"known on 2026-08-21 (the consumer contract and the script language). "
        f"With an empty population this check cannot fail at all."
    )
    assert "cyanrip-consumer-contract.md" in _GENERATED_DOCS, (
        "the page the three measured offenders cited is not in the derived "
        "population — the derivation has stopped reading the generators"
    )
    assert not offenders, (
        "these cite a GENERATED document by line number, and that document "
        "renumbers itself every time the code it is derived from changes:\n  "
        + "\n  ".join(offenders)
        + "\nCite the row instead — a rule name, a flag, a section — because that is "
        "the key the page is organised by and the only part of it that is stable. "
        "Measured 2026-08-21: three such citations existed and all three were "
        "already pointing at the wrong rows."
    )


def test_the_line_citation_detector_sees_all_three_shapes_that_shipped() -> None:
    """Non-triviality, against the exact text that was in the repo.

    A single-number citation, a comma list and a range — the three spellings the
    three real offenders used. A detector that only caught `:99` would have reported
    one problem where there were three, which is the failure mode `CLAUDE.md` calls
    worse than failing.
    """
    shipped = [
        "our own capture group takes the whole field "
        "(`docs/cyanrip-consumer-contract.md:99`, `\\((?P<result>[^)]*)\\)`)",
        "declares all six as parsed (`docs/cyanrip-consumer-contract.md:56,57,59,64,65,66`)",
        "Corroborated by `docs/cyanrip-consumer-contract.md:103-105`, where all three",
    ]
    found = [
        match.group("lines").strip()
        for line in shipped
        for match in _LINE_CITATION.finditer(line)
        if match.group("doc") in _GENERATED_DOCS
    ]
    assert found == ["99", "56,57,59,64,65,66", "103-105"], found


# -----------------------------------------------------------------------------
# Citations INTO the handshake record must resolve
# -----------------------------------------------------------------------------
# The test above forbids line citations into a *generated* page, because such a
# page renumbers itself. The handshake round files are the opposite class: once
# filed they are immutable correspondence — the record of what each side actually
# sent — so a line citation into one is both legitimate and, unusually, checkable.
#
# WHY THIS EXISTS. `docs/cyanrip-handshake.md` §9 (the challenge ledger) is
# nothing but such citations, and writing it produced the failure on the first
# attempt: two rows cited `inbound/round-10-lap-04.md` and
# `inbound/round-11-lap-02.md` because those are the paths the FORK used when
# quoting them. Both are OURS — they sit in `verified/` in this tree. The role
# flips across the seam (our outbound is their inbound), so a path copied out of
# a peer's lap points at nothing here, and points at nothing *silently*: the
# prose still reads correctly. A third row was off by one line.
#
# A ledger whose citations do not resolve is the invisible-decay shape the whole
# of this file is about — a map is only ever wrong by omission, and nobody reviews
# a table for the pointer that no longer lands.

_HANDSHAKE_DIR = _REPO_ROOT / "docs" / "handshake"


def _handshake_citations() -> list[tuple[Path, int, str, int]]:
    """Every ``round-*.md:NN`` citation in prose, as (citing file, line, target, N).

    Population derived from the filesystem, never listed: the sweep walks every
    Markdown file in the repository and keys on the round-file naming shape.
    """
    pattern = re.compile(
        r"(?P<dir>inbound/|outbound/|verified/)?"
        r"(?P<doc>round-?\d+[a-z]?(?:-lap-?\d+)?\.md):(?P<line>\d+)"
    )
    found: list[tuple[Path, int, str, int]] = []
    for path in sorted(_REPO_ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        # Skip the round files themselves: a lap quoting a lap uses the OTHER
        # side's layout by design, and rewriting a received artifact to suit our
        # directory names would falsify the record.
        if _HANDSHAKE_DIR in path.parents:
            continue
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            for match in pattern.finditer(line):
                target = (match.group("dir") or "") + match.group("doc")
                found.append((path, line_no, target, int(match.group("line"))))
    return found


def test_every_handshake_citation_in_prose_resolves_in_THIS_tree() -> None:
    """A pointer into the correspondence must land, and land here.

    Two ways it fails, both measured while writing the challenge ledger:

    * **the wrong directory** — a path copied out of a peer's lap, where the
      inbound/outbound roles are reversed. Reads perfectly, resolves nowhere.
    * **the wrong line** — off by one, because the section header was read from a
      `grep` of a different pattern than the one that produced the number.

    **Scope, stated rather than implied.** Only *resolution* is asserted, not
    content: a test that also pinned the text at each line would fail on a reflow
    and teach nothing. And an unqualified basename is accepted if it resolves in
    **any** of the three role directories — `cyanrip-known-issues.md` cites laps
    by bare basename throughout, which is unambiguous to a reader, and demanding
    a prefix there would be a doc rewrite for no gain. So the claim being checked
    is exactly *"this pointer lands somewhere in the record"* — which is the claim
    that decays — and not *"it lands in the file the writer meant"*.
    """
    citations = _handshake_citations()

    # FLOOR. This whole test passes for an empty repository otherwise, and the
    # ledger it was written for is the population.
    assert len(citations) >= 8, (
        f"only {len(citations)} handshake line-citations found in prose. The "
        f"challenge ledger in docs/cyanrip-handshake.md §9 carries at least eight; "
        f"a sweep that has stopped finding them cannot fail"
    )

    broken: list[str] = []
    for citing, citing_line, target, target_line in citations:
        where = f"{citing.relative_to(_REPO_ROOT)}:{citing_line}"
        if "/" in target:
            candidates = [_HANDSHAKE_DIR / target]
        else:
            # An unqualified basename is ambiguous across the three role
            # directories; accept it if it resolves in any one of them, and say
            # so, because forcing the prefix everywhere would be noise.
            candidates = [
                _HANDSHAKE_DIR / role / target
                for role in ("inbound", "outbound", "verified")
            ]
        resolved = [c for c in candidates if c.is_file()]
        if not resolved:
            tried = ", ".join(str(c.relative_to(_REPO_ROOT)) for c in candidates)
            broken.append(
                f"{where} cites {target}:{target_line} — no such file ({tried})"
            )
            continue
        # ANY, not ALL. An unqualified basename names one of three role
        # directories and the citation is satisfied by whichever one holds it;
        # requiring every namesake to be long enough would report a working
        # pointer as broken, which is the wrong-reason pass in reverse.
        lengths = {
            c: len(c.read_text(encoding="utf-8", errors="replace").splitlines())
            for c in resolved
        }
        if not any(target_line <= n for n in lengths.values()):
            detail = ", ".join(
                f"{c.relative_to(_REPO_ROOT)} has {n} lines"
                for c in resolved
                for n in [lengths[c]]
            )
            broken.append(
                f"{where} cites {target}:{target_line} — out of range everywhere "
                f"({detail})"
            )

    assert not broken, (
        "these citations into the handshake record do not resolve in this tree:\n  "
        + "\n  ".join(broken)
        + "\n\nThe commonest cause is a path copied out of a peer's lap: the "
        "inbound/outbound roles are REVERSED across the seam, so their "
        "`inbound/round-N.md` is our `verified/round-N.md`. Re-resolve it against "
        "this repository's layout rather than trusting the quoted path."
    )


def test_the_handshake_citation_sweep_catches_the_role_flip_that_shipped() -> None:
    """Non-triviality, against the exact two paths that were wrong.

    `inbound/round-10-lap-04.md` and `inbound/round-11-lap-02.md` are the real
    first-draft citations. Both are ours and live in `verified/`. A sweep that
    accepted a bare basename anywhere would have passed on both — which is why
    the check honours an explicit directory prefix instead of searching past it.
    """
    for wrong in ("inbound/round-10-lap-04.md", "inbound/round-11-lap-02.md"):
        assert not (_HANDSHAKE_DIR / wrong).is_file(), (
            f"{wrong} now exists, so it is no longer evidence of the role flip; "
            "pick a different pair or drop this test"
        )
        right = wrong.replace("inbound/", "verified/")
        assert (_HANDSHAKE_DIR / right).is_file(), (
            f"{right} is missing — the file this citation should have named is "
            "gone, and the ledger row citing it is now unverifiable"
        )
