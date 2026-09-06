"""Executable gates for the `CLAUDE.md` rules that had none.

**Why this file exists.** An audit (2026-08-28) walked every Critical rule and
Code convention in `CLAUDE.md` and asked one question of each: *what would fail
if somebody broke this tomorrow?* For a number of them — including headline
Critical rules — the answer was "nothing". They were prose, and prose binds
whoever last read it. `CLAUDE.md` says this about itself, twice: *"a comment
where a check belongs is not a fix"*, and *"a rule about a gate stated in a file
the gate does not read is a rule with no subject."*

So this module is the missing subject for six of them:

===  =============================================================  ============
#    Rule                                                           Sweep
===  =============================================================  ============
1    Critical #10 — `from __future__ import annotations` everywhere  §1
2    Critical #10 — `Signal(object)` payload named in the class body §2
3    Critical #5  — no bypass of the MusicBrainz query path          §3
4    Critical #1  — flagged deps go through an adapter               §4
5    Convention   — snake_case / PascalCase / SCREAMING_SNAKE_CASE   §5
6    Convention   — ~300-line module heuristic (a RATCHET, not a cap) §6
===  =============================================================  ============

**How every sweep here is built**, because this repo has paid for each of these:

* **The population comes off disk, never from a list.** A hand-maintained
  inventory of "the places this could go wrong" decays invisibly
  (`docs/testing.md` §5.af). Every sweep below walks `src/platterpus` with
  `rglob` and parses with `ast`.
* **Every sweep asserts a floor on that population.** *"Can this check be
  satisfied by finding nothing?"* is the most-cited question in `CLAUDE.md`, and
  a sweep whose glob silently returns nothing passes having examined nothing.
  Each sweep asserts it saw a plausible minimum before it believes its own
  verdict.
* **Every sweep has a non-triviality twin** that proves the detector can FIRE
  against constructed text, and — where the detector could over-fire — that it
  stays quiet on the legitimate shape. Only the pair is a check. A detector
  proven only by "it passes on the real tree" is indistinguishable from one that
  returns the empty set.
* **`ast`, never `grep`.** Three of these rules are about text that *looks like*
  code: `logging.getLogger("musicbrainzngs")` is not an import, and the three
  prose paragraphs in `main_window*.py` that discuss ``Signal(object)`` are not
  declarations. A regex sweep reports all four and is then disbelieved.

**The allowlists below are DEBT LEDGERS, not exemptions.** Three of these
sweeps fail against the tree as it stands. Those failures are findings, and the
entries record them so the ratchet can bite on the *next* one — every entry says
what is actually wrong and what the fix is. They may shrink; a test below
enforces that they may not grow. Read them as a to-do list, not as a set of
blessed cases: `CLAUDE.md`'s own warning is that *"a loosened assertion with a
confident comment is worse than no assertion"*, so none of these comments claims
the subject is fine.

**Deliberately NOT parametrized.** `tests/test_dynamic_sweeps_declare_a_floor.py`
polices `@pytest.mark.parametrize` over a computed population, because an empty
population generates zero cases and pytest reports success. Every sweep here is a
plain test that loops internally and asserts a floor, which sidesteps that
failure mode entirely rather than registering an exemption from it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SRC_ROOT: Final[Path] = REPO_ROOT / "src" / "platterpus"
CLAUDE_MD: Final[Path] = REPO_ROOT / "CLAUDE.md"

#: Floor on the module population every sweep here walks. 156 modules today; a
#: bar well under that catches a broken glob (a moved package, a renamed source
#: root) without tripping on ordinary consolidation. Without it, a `rglob` that
#: matched nothing would make every assertion below vacuously true — which is the
#: single defect `CLAUDE.md` names most often.
_MIN_SOURCE_MODULES: Final[int] = 120


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers. Everything below derives its subject through these, so there
# is one definition of "the source tree" and it cannot drift between sweeps.
# ─────────────────────────────────────────────────────────────────────────────


def _source_modules() -> list[Path]:
    """Every Python module under `src/platterpus`, sorted for stable messages."""
    return sorted(SRC_ROOT.rglob("*.py"))


def _rel(path: Path) -> str:
    """A module's path relative to the package root — what the messages print."""
    return path.relative_to(SRC_ROOT).as_posix()


def _parsed(path: Path) -> tuple[ast.Module, list[str]]:
    """A module's AST plus its raw lines.

    The lines come back alongside the tree because two of the rules here are
    about **comments**, which the AST discards. Re-reading the file per sweep
    would be the alternative; handing both back from one read keeps the two views
    of a module guaranteed to be of the same bytes.
    """
    text = path.read_text(encoding="utf-8")
    return ast.parse(text), text.splitlines()


# ─────────────────────────────────────────────────────────────────────────────
# §1 — Critical rule #10: `from __future__ import annotations` in every module.
#
# Why it matters beyond style: without it, every annotation is evaluated at
# import time, so a forward reference or a heavy typing-only import becomes a
# runtime cost and a runtime failure rather than a checker's problem. The rule is
# stated absolutely in `CLAUDE.md` — "in every module" — so this sweep is
# absolute too, and the modules that do not comply are ledgered rather than
# quietly excused.
# ─────────────────────────────────────────────────────────────────────────────


#: DEBT LEDGER — modules that lack the import today. NOT a list of blessed
#: exemptions: the rule says "every module", and each entry below is a real
#: violation of it. The ledger exists so the sweep can bite on the *next* module
#: to drop the import while the existing nine are fixed separately. It may only
#: shrink (enforced below).
_MODULES_MISSING_FUTURE_ANNOTATIONS: Final[dict[str, str]] = {
    # EMPTY, and it stays empty. When this sweep was first written it held
    # nine entries — six package `__init__.py` files, the two entry points and
    # the generated offsets table. All nine were fixed the same day rather than
    # recorded, because a ledger of fifteen exemptions is fifteen places this
    # file is blind, and the fixes were one line each. The generated one was
    # fixed in `scripts/update_drive_offsets.py`'s TEMPLATE, not in its output:
    # editing the output would be undone by the next regeneration with no
    # failure in between.
}


def _declares_future_annotations(tree: ast.Module) -> bool:
    """True if this module has `from __future__ import annotations`.

    AST rather than a substring search, so the sentence *"every module needs
    `from __future__ import annotations`"* sitting in a docstring — which is
    exactly the text this file's own docstring contains — is not mistaken for the
    import itself.
    """
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def _modules_without_future_annotations() -> list[str]:
    """Every module lacking the import, as package-relative paths."""
    return [
        _rel(path)
        for path in _source_modules()
        if not _declares_future_annotations(_parsed(path)[0])
    ]


def test_every_module_declares_future_annotations() -> None:
    """Critical rule #10, first clause. New modules must comply immediately."""
    modules = _source_modules()
    assert len(modules) >= _MIN_SOURCE_MODULES, (
        f"only {len(modules)} modules found under {SRC_ROOT} (floor "
        f"{_MIN_SOURCE_MODULES}) — the glob is broken, so this sweep's verdict "
        "means nothing. Fix the population before reading the result."
    )
    offenders = sorted(
        set(_modules_without_future_annotations())
        - set(_MODULES_MISSING_FUTURE_ANNOTATIONS)
    )
    assert not offenders, (
        "CLAUDE.md Critical rule #10 requires `from __future__ import "
        "annotations` in EVERY module; these do not have it:\n  "
        + "\n  ".join(offenders)
        + "\nAdd the import as the first statement after the module docstring. "
        "Do NOT add the module to _MODULES_MISSING_FUTURE_ANNOTATIONS — that "
        "ledger only shrinks."
    )


def test_the_future_annotations_ledger_only_shrinks() -> None:
    """The part with teeth: a ledger that can be widened is a comment.

    Both directions. An entry that has been fixed must leave the list, or the
    ledger starts describing a tree that has moved on — the invisible decay
    `CLAUDE.md` describes under *"does this document promise completeness?"*
    """
    missing = set(_modules_without_future_annotations())
    assert len(_MODULES_MISSING_FUTURE_ANNOTATIONS) <= 9, (
        f"the ledger has grown to {len(_MODULES_MISSING_FUTURE_ANNOTATIONS)}. It "
        "was 9 when written (2026-08-28) and may only get smaller — add the "
        "import to the module instead of widening the exemption."
    )
    fixed = sorted(set(_MODULES_MISSING_FUTURE_ANNOTATIONS) - missing)
    assert not fixed, (
        f"{fixed} now declare the import — delete their ledger entries and lower "
        "the bound above, so the ratchet keeps ratcheting."
    )


def test_the_future_annotations_detector_fires_and_does_not_over_fire() -> None:
    """Non-triviality twin. Proves the detector can say NO as well as yes.

    Case 3 is the one that matters: a module whose *prose* names the import must
    still be reported as missing it. That is the "mentioning is not doing" trap
    this repo has hit twice with vacuous detectors, and it is why this sweep
    parses instead of grepping.
    """
    compliant = ast.parse('"""Doc."""\nfrom __future__ import annotations\nX = 1\n')
    assert _declares_future_annotations(compliant)

    bare = ast.parse('"""Doc."""\nX: int = 1\n')
    assert not _declares_future_annotations(bare), (
        "the detector passed a module with no `__future__` import at all — it "
        "cannot fail, so every green run above is meaningless"
    )

    only_mentioned = ast.parse(
        '"""Every module needs `from __future__ import annotations`."""\nX = 1\n'
    )
    assert not _declares_future_annotations(only_mentioned), (
        "a docstring that NAMES the import satisfied the detector. A substring "
        "search does this; the check must read the import statement."
    )

    other_future = ast.parse("from __future__ import division\n")
    assert not _declares_future_annotations(other_future), (
        "a different `__future__` import satisfied the detector — it is matching "
        "the module, not the feature"
    )


# ─────────────────────────────────────────────────────────────────────────────
# §2 — Critical rule #10: `Signal(object)` payload types named in the class body.
#
# The rule, verbatim: "PySide6 `Signal` payload types named in the class body —
# `Signal(object)  # list[DriveDescriptor]` — because Qt's queued connections
# force `object` and the comment is the only remaining type information."
#
# So the subject is any Signal carrying a bare `object`, and the requirement is
# that a type is NAMED next to it. Two design decisions, both deliberate:
#
#   * A payload named in the contiguous comment block IMMEDIATELY ABOVE the
#     declaration counts, not only a trailing comment. The rule's words are "in
#     the class body"; the trailing form is its example, not its scope. Ten of
#     the eleven leading-comment sites in `main_window.py` name their payload in
#     more detail than a trailing comment could hold ("with a
#     main_window_rip.TaggingResult — how the unknown-album tagging pass went"),
#     and failing them would be a check failing for the wrong reason.
#   * "Names a type" is not "has a comment". A comment-presence check is
#     satisfied by any prose — `CLAUDE.md`'s *"can it be satisfied by the wrong
#     thing?"* — so the comment must contain a token that looks like a type: a
#     CamelCase identifier with an internal case change (`TaggingResult`,
#     `main_window_rip.TaggingResult`), or a subscripted builtin generic
#     (`list[...]`, `dict[...]`). All-caps acronyms are excluded on purpose:
#     these comments are dense with "GUI", "Qt", "CTDB" and "FLAC", and counting
#     those as type names is precisely how this check would rot into decoration.
#
# What this cannot prove: that the named type is the RIGHT one. No static check
# can — Qt has erased it by then. It answers "did somebody write the type down",
# which is the whole of what the rule asks for.
# ─────────────────────────────────────────────────────────────────────────────


#: A CamelCase identifier with an internal lower→upper transition, optionally
#: dotted (`evidence_bundle.BundleResult`), or a subscripted builtin container.
#: Anchored on a word boundary so `sha256` and `GUI` do not match.
_TYPE_NAME: Final[re.Pattern[str]] = re.compile(
    r"\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Z][a-z0-9_]+[A-Z][A-Za-z0-9_]*"
    r"|\b(?:list|dict|tuple|set|frozenset|Sequence|Mapping|Iterable)\["
)

#: DEBT LEDGER — object-payload signals whose neighbouring comment describes the
#: payload without naming a type. NOT blessed: each is a real gap in rule #10.
#: Shrink-only (enforced below).
_SIGNALS_WITHOUT_A_NAMED_PAYLOAD: Final[dict[str, str]] = {
    # EMPTY. Held one entry when written — `checksums_done`, whose comment
    # described the value ("the {relpath: sha256} digest map") without naming a
    # type. Fixed rather than recorded: the payload is `dict[str, str]`.
}


def _object_payload_signals() -> list[tuple[str, str, str]]:
    """Every `x = Signal(..., object, ...)` in src, with the comment beside it.

    Returns `(key, signal_name, comment_text)` where `key` is
    ``<module>:<signal>`` and `comment_text` is the trailing comment plus the
    contiguous comment block immediately above the declaration.
    """
    found: list[tuple[str, str, str]] = []
    for path in _source_modules():
        tree, lines = _parsed(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            callee = call.func
            callee_name = (
                callee.id
                if isinstance(callee, ast.Name)
                else getattr(callee, "attr", "")
            )
            if callee_name != "Signal":
                continue
            # Only a BARE `object` argument loses its type. `Signal(str)` and
            # `Signal(bool, str)` are self-describing and out of scope.
            if not any(
                isinstance(arg, ast.Name) and arg.id == "object" for arg in call.args
            ):
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            found.append(
                (
                    f"{_rel(path)}:{target.id}",
                    target.id,
                    _comment_context(lines, node.lineno),
                )
            )
    return found


def _comment_context(lines: list[str], lineno: int) -> str:
    """The trailing comment on `lineno` plus the comment block directly above it.

    Both halves, joined, because the codebase uses both forms and the rule asks
    only that the type be named *in the class body*. The block above stops at the
    first non-comment line, so a comment attached to a different declaration
    three lines up is never borrowed.
    """
    parts: list[str] = []
    index = lineno - 2
    while index >= 0 and lines[index].strip().startswith("#"):
        parts.append(lines[index].strip().lstrip("#").strip())
        index -= 1
    parts.reverse()
    declaration = lines[lineno - 1]
    hash_at = declaration.find("#")
    if hash_at != -1:
        parts.append(declaration[hash_at + 1 :].strip())
    return " ".join(parts)


def test_every_object_payload_signal_names_its_payload_type() -> None:
    """Critical rule #10, the `Signal(object)` clause."""
    signals = _object_payload_signals()
    # 29 object-payload signals today across 11 modules. The floor guards the
    # AST shape: PySide6 could be imported as `QtCore.Signal`, a refactor could
    # move the declarations, and either would silently empty this sweep.
    assert len(signals) >= 20, (
        f"only {len(signals)} object-payload Signals found (floor 20) — the AST "
        "matcher has stopped recognising the declaration shape, so a green run "
        "here proves nothing. Check `_object_payload_signals` before trusting it."
    )
    offenders = sorted(
        key
        for key, _name, comment in signals
        if not _TYPE_NAME.search(comment)
        and key not in _SIGNALS_WITHOUT_A_NAMED_PAYLOAD
    )
    assert not offenders, (
        "CLAUDE.md Critical rule #10: a `Signal(object)` must name its payload "
        "type in the class body, because Qt's queued connections erase it and "
        "the comment is the only type information left. These name none:\n  "
        + "\n  ".join(offenders)
        + "\nAdd a trailing comment naming the type — `Signal(object)  # "
        "list[DriveDescriptor]` — or name it in the comment block directly "
        "above. Do NOT add an entry to _SIGNALS_WITHOUT_A_NAMED_PAYLOAD."
    )


def test_the_signal_payload_ledger_only_shrinks() -> None:
    """Two-way ratchet: it may not grow, and it may not go stale."""
    signals = _object_payload_signals()
    assert len(_SIGNALS_WITHOUT_A_NAMED_PAYLOAD) <= 1, (
        f"the ledger has grown to {len(_SIGNALS_WITHOUT_A_NAMED_PAYLOAD)}. It was "
        "1 when written (2026-08-28) and may only shrink."
    )
    unnamed = {key for key, _name, comment in signals if not _TYPE_NAME.search(comment)}
    resolved = sorted(set(_SIGNALS_WITHOUT_A_NAMED_PAYLOAD) - unnamed)
    assert not resolved, (
        f"{resolved} now name a payload type (or no longer exist) — delete the "
        "ledger entry and lower the bound above."
    )


def test_the_payload_detector_fires_and_does_not_over_fire() -> None:
    """Non-triviality twin, both directions.

    The over-fire half is the important one here. Widening "names a type" to
    "has a comment" would let `checksums_done`'s prose pass, and widening the
    pattern to any capitalised word would let "GUI thread" pass — this asserts
    neither happens, so the ledger entry above stays a real finding rather than
    an artefact of a sloppy regex.
    """
    # FIRES: a bare declaration with no comment at all.
    assert not _TYPE_NAME.search(_comment_context(["finished = Signal(object)"], 1))
    # FIRES: prose that describes the payload without naming a type — the
    # `checksums_done` shape, reproduced so the ledger entry is falsifiable.
    prose = [
        "# Emitted from a daemon thread; queued to the GUI thread with the",
        "# {relpath: sha256} digest map once every audio file has been hashed.",
        "checksums_done = Signal(object)",
    ]
    assert not _TYPE_NAME.search(_comment_context(prose, 3)), (
        "prose naming no type satisfied the detector — 'GUI' or 'sha256' is "
        "being read as a type name, which makes this whole sweep decoration"
    )
    # DOES NOT over-fire: the rule's own example, trailing form.
    trailing = ["finished = Signal(object)  # list[DriveDescriptor]"]
    assert _TYPE_NAME.search(_comment_context(trailing, 1))
    # DOES NOT over-fire: the leading-block form the codebase actually uses,
    # including the dotted `module.TypeName` spelling.
    leading = [
        "# Emitted from the post-rip thread; queued to the GUI thread with a",
        "# main_window_rip.TaggingResult saying how the tagging pass went.",
        "tagging_done = Signal(object)",
    ]
    assert _TYPE_NAME.search(_comment_context(leading, 3))
    # DOES NOT borrow a comment belonging to a different declaration: a blank
    # line between the block and the signal breaks the association.
    detached = [
        "# BundleResult, for the signal below this blank line.",
        "",
        "finished = Signal(object)",
    ]
    assert not _TYPE_NAME.search(_comment_context(detached, 3)), (
        "the comment context walked past a non-comment line and borrowed a "
        "comment attached to something else"
    )


# ─────────────────────────────────────────────────────────────────────────────
# §3 — Critical rule #5: no bypass of the MusicBrainz query path.
#
# "Always query MusicBrainz via the `MusicBrainzClient` adapter (currently backed
# by `python-musicbrainzngs`)." The enforceable half of that is the import: if
# only the adapter can import the library, only the adapter can query it.
#
# The allowed importer is DERIVED, not guessed — it is whichever module under
# `adapters/` does the importing. The check is then "no importer outside
# `adapters/`", plus a floor asserting an importer exists at all (an import
# restriction on a library nobody imports is a check that cannot fail).
# ─────────────────────────────────────────────────────────────────────────────


def _modules_importing(top_level: str) -> list[str]:
    """Every module that imports `top_level`, as package-relative paths.

    AST, so that `logging.getLogger("musicbrainzngs")` in `logging_setup.py` —
    which configures the library's log level and touches nothing else — is not
    counted. A grep reports it, and a reviewer who checks one false positive
    stops checking the rest.
    """
    importers: list[str] = []
    for path in _source_modules():
        tree, _lines = _parsed(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name.split(".")[0] == top_level for alias in node.names
            ):
                importers.append(_rel(path))
                break
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and (node.module or "").split(".")[0] == top_level
            ):
                importers.append(_rel(path))
                break
    return importers


def test_musicbrainzngs_is_imported_only_by_its_adapter() -> None:
    """Critical rule #5 / #1: one seam to MusicBrainz, and it is the adapter."""
    modules = _source_modules()
    assert len(modules) >= _MIN_SOURCE_MODULES, (
        f"only {len(modules)} modules examined (floor {_MIN_SOURCE_MODULES}) — "
        "the population is broken, so 'nobody bypasses the adapter' is not a "
        "finding"
    )
    importers = _modules_importing("musicbrainzngs")
    assert importers, (
        "NOTHING in src imports `musicbrainzngs`. Either the adapter has been "
        "re-backed (in which case retarget this sweep at whatever library now "
        "backs MusicBrainzClient) or the import detector is broken — but as "
        "written this check can no longer fail, and Critical rule #5 is "
        "unguarded again."
    )
    outside = sorted(name for name in importers if not name.startswith("adapters/"))
    assert not outside, (
        "CLAUDE.md Critical rule #5 — always query MusicBrainz through the "
        "MusicBrainzClient adapter — and Critical rule #1, which makes the "
        "adapter mandatory for this unmaintained library. These import it "
        f"directly:\n  {chr(10).join(outside)}\n"
        f"Route the call through `{importers[0]}` instead."
    )
    assert len(importers) == 1, (
        f"{len(importers)} adapter modules import musicbrainzngs: {importers}. "
        "Critical rule #1 asks for ONE thin adapter so a replacement is a "
        "single-file job; two seams to the same library are two things to "
        "rewrite and two places that can disagree about its error shapes."
    )


def test_the_import_detector_fires_and_ignores_a_mere_mention() -> None:
    """Non-triviality twin for the import sweep.

    The second half is the one with history: `logging_setup.py` names
    `musicbrainzngs` as a *logger name* string and would be a false positive for
    any text search, so this pins that the detector reads imports.
    """
    assert _modules_importing("musicbrainzngs"), "the detector finds no importer"
    assert not _modules_importing("no_such_library_anywhere"), (
        "the detector claims a library that does not exist is imported — it is "
        "matching something other than an import"
    )
    # The mention-is-not-an-import case, asserted against the real module rather
    # than a constructed one, so it stays true of the file that actually does it.
    assert "logging_setup.py" not in _modules_importing("musicbrainzngs"), (
        "logging_setup.py was counted as an importer. It only passes the string "
        '"musicbrainzngs" to logging.getLogger — if that now reads as an import, '
        "this sweep is a text search wearing an AST costume"
    )


# ─────────────────────────────────────────────────────────────────────────────
# §4 — Critical rule #1: external / unmaintained deps go through an adapter.
#
# The rule names its own subjects: "Currently flagged: `python-musicbrainzngs`
# and `appimage-builder` (if ever reached for) are unmaintained; `cyanrip` is the
# external ripper (actively maintained, but still an external CLI)."
#
# So this sweep READS THE RULE rather than restating it. If the flagged list
# changes in `CLAUDE.md`, the new name arrives here unclassified and this fails
# until somebody says which kind it is — which is the only way a gate over a
# prose rule can stay in step with the prose.
#
# Each flagged name is one of two kinds, and the kind decides the check:
#
#   * `python-import` — reachable by `import`. The adapter rule is enforceable
#     statically: every importer must live under `adapters/`.
#   * `external-cli` — reachable only by spawning a process. An import check
#     CANNOT enforce the adapter rule for these, and pretending otherwise would
#     be a check that passes for the wrong reason. What is enforced here is the
#     weaker, still-real claim that it has not quietly BECOME an import (that
#     would be a new seam with no adapter); the subprocess route is gated
#     elsewhere and each entry names where.
# ─────────────────────────────────────────────────────────────────────────────


#: How each flagged dependency is reachable from our code, and — for the ones an
#: import check cannot cover — which gate does cover them. A two-way ratchet: a
#: name added to Critical rule #1 fails until it is classified here, and an entry
#: for a name the rule no longer flags fails too, so this cannot describe a rule
#: that has moved on.
_FLAGGED_DEPENDENCY_KIND: Final[dict[str, str]] = {
    # Imported by `adapters/musicbrainz_client.py`. §3 above is the detailed
    # gate; it is repeated here through the generic mechanism so that the
    # coverage claim is derived from the rule rather than asserted by me.
    "python-musicbrainzngs": "python-import",
    # Rule #2: "Do not use `appimage-builder` without stopping and asking
    # first." It is a build tool, invoked as a command, never imported — the
    # check below is that it has not become an import. That is deliberately
    # narrow: nothing static can prove `build/build_appimage.sh` did not shell
    # out to it, and a check claiming otherwise would be worse than none.
    "appimage-builder": "external-cli",
    # The ripper. Reached by spawning `~/.local/bin/cyanrip` through
    # `adapters/cyanrip_backend.py`; there is no Python package to import. Its
    # real route is swept by `tests/test_ripper_spawn_sites_are_enumerated.py`,
    # which enumerates every module that can start a child process and requires
    # the rip routes to delegate to the `-N` chokepoint. Not duplicated here —
    # two implementations of one check are two things that can disagree.
    "cyanrip": "external-cli",
}

_VALID_KINDS: Final[frozenset[str]] = frozenset({"python-import", "external-cli"})


def _flagged_dependencies() -> list[str]:
    """The dependency names Critical rule #1 flags, read out of `CLAUDE.md`.

    Scoped to the "Currently flagged: … Every call into these" sentence so the
    backticked `RipBackend` and `adapters/rip_backend.py` later in the same rule
    are not mistaken for dependencies.
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")
    match = re.search(r"Currently flagged:(.*?)Every call into these", text, re.S)
    if match is None:
        return []
    return re.findall(r"`([^`]+)`", match.group(1))


def _import_name(flagged: str) -> str:
    """The module name a flagged distribution would be imported under.

    `python-musicbrainzngs` → `musicbrainzngs`, `appimage-builder` →
    `appimage_builder`: the distro `python-` prefix is not part of the import
    path, and PyPI's hyphens become underscores. Derived rather than tabled, so
    a newly flagged name needs no mapping entry.
    """
    stem = flagged.removeprefix("python-")
    return stem.replace("-", "_")


def test_the_flagged_dependency_list_is_read_from_the_rule() -> None:
    """Floor on §4's population — it comes from prose, which can be reworded."""
    flagged = _flagged_dependencies()
    assert len(flagged) >= 3, (
        f"Critical rule #1's 'Currently flagged:' sentence yielded {flagged!r} "
        "(expected at least 3 names). Either the rule was reworded or the "
        "extraction broke — until this is fixed, every §4 assertion below is "
        "about an empty list and cannot fail."
    )


def test_every_flagged_dependency_is_classified() -> None:
    """Two-way ratchet between `CLAUDE.md`'s rule #1 and this file.

    The point is that a NEW flagged dependency cannot be added to the rule and
    then quietly go ungated: it lands here unclassified and fails.
    """
    flagged = set(_flagged_dependencies())
    unclassified = sorted(flagged - set(_FLAGGED_DEPENDENCY_KIND))
    assert not unclassified, (
        f"Critical rule #1 flags {unclassified}, which this sweep does not know "
        "how to check. Classify each in _FLAGGED_DEPENDENCY_KIND as "
        "'python-import' (an import check applies) or 'external-cli' (say which "
        "gate covers its real route)."
    )
    stale = sorted(set(_FLAGGED_DEPENDENCY_KIND) - flagged)
    assert not stale, (
        f"{stale} are classified here but no longer flagged by Critical rule #1. "
        "Remove the entries — a classification of a rule that has moved on is a "
        "map that is wrong by omission."
    )
    bad_kinds = sorted(
        f"{name}={kind}"
        for name, kind in _FLAGGED_DEPENDENCY_KIND.items()
        if kind not in _VALID_KINDS
    )
    assert not bad_kinds, f"unknown kind(s): {bad_kinds}; valid: {sorted(_VALID_KINDS)}"


def test_no_flagged_dependency_is_imported_outside_an_adapter() -> None:
    """Critical rule #1: "Adapter modules are mandatory, not optional."

    For a `python-import` dependency this is the whole rule, statically. For an
    `external-cli` one it is the narrower claim that it has not become an import
    behind the adapter layer's back — stated plainly so nobody reads this test's
    green as proof the subprocess route is guarded. It is not; the entry in
    `_FLAGGED_DEPENDENCY_KIND` names the gate that is.
    """
    modules = _source_modules()
    assert len(modules) >= _MIN_SOURCE_MODULES, (
        f"only {len(modules)} modules examined (floor {_MIN_SOURCE_MODULES}) — "
        "the sweep looked at nothing, so it found nothing"
    )
    problems: list[str] = []
    for flagged, kind in sorted(_FLAGGED_DEPENDENCY_KIND.items()):
        importers = _modules_importing(_import_name(flagged))
        outside = [name for name in importers if not name.startswith("adapters/")]
        if kind == "python-import":
            if not importers:
                problems.append(
                    f"{flagged}: classified 'python-import' but NOTHING imports "
                    f"`{_import_name(flagged)}`. Either it is really an "
                    "external-cli, or the check is now unfalsifiable."
                )
            problems += [
                f"{flagged}: imported by {name}, which is not an adapter"
                for name in outside
            ]
        else:
            problems += [
                f"{flagged}: classified 'external-cli' but {name} now IMPORTS "
                f"`{_import_name(flagged)}`. That is a new seam with no adapter "
                "— add one under `adapters/` and reclassify."
                for name in importers
            ]
    assert not problems, (
        "CLAUDE.md Critical rule #1 — every call into a flagged external or "
        "unmaintained dependency goes through a thin adapter module:\n  "
        + "\n  ".join(problems)
    )


def test_the_flagged_dependency_checks_can_fail() -> None:
    """Non-triviality twin for §4.

    Two ways this sweep could be decoration: the rule-extraction could return an
    empty list, or `_import_name` could produce a module name nothing could ever
    match. Both are asserted against directly.
    """
    assert _import_name("python-musicbrainzngs") == "musicbrainzngs"
    assert _import_name("appimage-builder") == "appimage_builder"
    assert _import_name("cyanrip") == "cyanrip"
    # The `python-import` branch is reachable and does real work today: exactly
    # one flagged name resolves to a library that is genuinely imported.
    live = [
        name
        for name, kind in _FLAGGED_DEPENDENCY_KIND.items()
        if kind == "python-import" and _modules_importing(_import_name(name))
    ]
    assert live, (
        "no flagged dependency is actually imported anywhere, so the "
        "adapter-boundary assertion is empty-vs-empty and cannot fail"
    )


# ─────────────────────────────────────────────────────────────────────────────
# §5 — Code convention: "snake_case for functions, variables, modules;
# PascalCase for classes; SCREAMING_SNAKE_CASE for module-level constants."
#
# SCOPE, stated rather than implied — `CLAUDE.md`: *"Scoping a sweep is fine.
# Scoping it silently while the rule claims everything is the defect."*
#
#   IN  — module filenames, class names, function/method names, and module-level
#         CONSTANTS.
#   OUT — local variables, parameters, comprehension targets, and module-level
#         type aliases. Type aliases are PascalCase by Python convention
#         (`Runner = Callable[...]`), so a "module-level names must be
#         SCREAMING_SNAKE" sweep reports ~12 correct declarations as violations;
#         a list of excuses that long enforces nothing. Locals are left out
#         because ruff's `N` ruleset is the right tool and is not enabled here
#         (`[tool.ruff] select = E,F,W,I,B,UP`) — which is also why the
#         `noqa: N802` markers in this codebase are documentation rather than
#         enforcement, and why five real Qt overrides never acquired one.
#
# The exemption signal is the codebase's own: a `noqa: N802` comment on the `def`
# line, used for Qt/stdlib API overrides where the name is not ours to choose. It is
# read from the source, not reinvented as a list of method names here.
# ─────────────────────────────────────────────────────────────────────────────


_SNAKE: Final[re.Pattern[str]] = re.compile(r"_{0,2}[a-z][a-z0-9_]*_{0,2}")
_PASCAL: Final[re.Pattern[str]] = re.compile(r"_?[A-Z][A-Za-z0-9]*")
_SCREAMING: Final[re.Pattern[str]] = re.compile(r"_{0,2}[A-Z][A-Z0-9_]*")

#: Method names that override a framework base class whose API is not ours, and
#: which are missing the repo's own `noqa: N802` marker.
#:
#: DEBT LEDGER, not an exemption list. Every entry IS a legitimate override —
#: the fix is one comment on the `def` line, after which the generic exemption
#: covers it and the entry is deleted. They are listed here rather than pattern-
#: matched (`*Event`, `rowCount`, …) on purpose: a pattern would also exempt a
#: method of ours that happened to be spelled that way, and the marker is the
#: signal the codebase already chose. Shrink-only (enforced below).
_NON_SNAKE_FUNCTIONS_MISSING_THE_MARKER: Final[dict[str, str]] = {
    # EMPTY. Held five entries when written — `doRollover` and four
    # `QAbstractTableModel` overrides, all legitimate, none marked. They are
    # marked now, and the deeper finding was fixed with them: ruff's naming
    # rules were NOT enabled, so all sixteen N802 suppression markers in `src`
    # suppressed a rule that never ran. `pyproject.toml` now selects
    # N801/N802/N804/N805 for `src` (0 findings) and exempts `tests` (113), so
    # this sweep is the belt and the linter is the braces.
}

#: Methods that mutate a container in place. A module-level name on the receiving
#: end of one of these is module STATE, not a constant, so snake_case is correct
#: for it and the SCREAMING_SNAKE rule does not apply.
_MUTATING_METHODS: Final[frozenset[str]] = frozenset(
    {
        "append",
        "extend",
        "insert",
        "remove",
        "pop",
        "clear",
        "sort",
        "reverse",
        "add",
        "discard",
        "update",
        "setdefault",
        "popitem",
    }
)


def _is_literal(value: ast.expr) -> bool:
    """True if `value` is a literal constant — the shape a constant has.

    Deliberately narrow. `log = logging.getLogger(__name__)` is a Call and
    `Runner = Callable[[str], int]` is a Subscript; neither is a constant, and
    including them is how this check would start reporting correct code.
    """
    if isinstance(value, ast.Constant):
        return True
    if isinstance(value, ast.Tuple | ast.List | ast.Set):
        return all(_is_literal(element) for element in value.elts)
    if isinstance(value, ast.Dict):
        return all(key is not None and _is_literal(key) for key in value.keys) and all(
            _is_literal(item) for item in value.values
        )
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
        return _is_literal(value.operand)
    return False


def _rebound_or_mutated(tree: ast.Module) -> set[str]:
    """Module-level names that are written to after their first binding.

    A name that is `global`-declared, augmented, index-assigned or mutated
    in place is module *state*, whatever it was initialised to — `False` and `[]`
    are literals, and `_fatal_dialog_open`/`_abandoned_threads` are variables.
    Without this the convention sweep reports three correct snake_case variables
    as mis-named constants, which is the "satisfied by the wrong thing" failure.
    """
    written: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            written.update(node.names)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            written.add(node.target.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript | ast.Attribute) and isinstance(
                    target.value, ast.Name
                ):
                    written.add(target.value.id)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _MUTATING_METHODS
            and isinstance(node.func.value, ast.Name)
        ):
            written.add(node.func.value.id)
    return written


def _module_level_constants(tree: ast.Module) -> list[tuple[str, int]]:
    """`(name, lineno)` for every module-level literal constant in `tree`."""
    state = _rebound_or_mutated(tree)
    bindings: dict[str, int] = {}
    constants: list[tuple[str, int]] = []
    for statement in tree.body:
        pairs: list[tuple[ast.Name, ast.expr]] = []
        if isinstance(statement, ast.Assign):
            pairs = [
                (target, statement.value)
                for target in statement.targets
                if isinstance(target, ast.Name)
            ]
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.value is not None
        ):
            pairs = [(statement.target, statement.value)]
        for target, value in pairs:
            bindings[target.id] = bindings.get(target.id, 0) + 1
            if target.id.startswith("__") and target.id.endswith("__"):
                continue  # dunders are the language's names, not ours
            if target.id in state or bindings[target.id] > 1:
                continue  # written more than once → a variable
            if _is_literal(value):
                constants.append((target.id, target.lineno))
    return constants


def test_module_and_class_names_follow_the_convention() -> None:
    """snake_case modules, PascalCase classes."""
    modules = _source_modules()
    assert len(modules) >= _MIN_SOURCE_MODULES, (
        f"only {len(modules)} modules examined (floor {_MIN_SOURCE_MODULES})"
    )
    bad_modules: list[str] = []
    bad_classes: list[str] = []
    classes_seen = 0
    for path in modules:
        if not _SNAKE.fullmatch(path.stem):
            bad_modules.append(_rel(path))
        tree, _lines = _parsed(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes_seen += 1
                if not _PASCAL.fullmatch(node.name):
                    bad_classes.append(f"{_rel(path)}:{node.lineno} {node.name}")
    assert classes_seen >= 100, (
        f"only {classes_seen} classes found (floor 100) — the AST walk is not "
        "reaching class definitions, so 'all class names are PascalCase' is not "
        "a finding"
    )
    assert not bad_modules, (
        "CLAUDE.md naming convention: module filenames are snake_case. "
        f"Rename:\n  {chr(10).join(bad_modules)}"
    )
    assert not bad_classes, (
        "CLAUDE.md naming convention: class names are PascalCase. "
        f"Rename:\n  {chr(10).join(bad_classes)}"
    )


def test_function_names_are_snake_case_or_marked_as_framework_overrides() -> None:
    """snake_case functions, with `noqa: N802` as the codebase's own exemption.

    A name we did not choose — `closeEvent`, `rowCount` — is not a convention
    violation, but it has to SAY so, or the sweep cannot tell it apart from a
    camelCase method somebody wrote by hand.
    """
    functions_seen = 0
    offenders: list[str] = []
    for path in _source_modules():
        tree, lines = _parsed(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            functions_seen += 1
            if _SNAKE.fullmatch(node.name):
                continue
            # The marker sits on the `def` line, which is `node.lineno` even when
            # the signature wraps over several lines.
            if "N802" in lines[node.lineno - 1]:
                continue
            key = f"{_rel(path)}:{node.name}"
            if key not in _NON_SNAKE_FUNCTIONS_MISSING_THE_MARKER:
                offenders.append(f"{key} (line {node.lineno})")
    assert functions_seen >= 800, (
        f"only {functions_seen} functions examined (floor 800) — the walk is not "
        "reaching function definitions and this sweep proves nothing"
    )
    assert not offenders, (
        "CLAUDE.md naming convention: functions and methods are snake_case. "
        f"These are not:\n  {chr(10).join(offenders)}\n"
        "If the name is a framework override we do not control, mark the `def` "
        "line with a `noqa: N802 — Qt override` comment, as the rest of the "
        "codebase does. Do "
        "NOT add an entry to _NON_SNAKE_FUNCTIONS_MISSING_THE_MARKER."
    )


def test_the_unmarked_override_ledger_only_shrinks() -> None:
    """Two-way ratchet on §5's ledger."""
    assert len(_NON_SNAKE_FUNCTIONS_MISSING_THE_MARKER) <= 5, (
        f"the ledger has grown to {len(_NON_SNAKE_FUNCTIONS_MISSING_THE_MARKER)}. "
        "It was 5 when written (2026-08-28); the fix is one `noqa: N802` comment "
        "comment per entry, so it may only shrink."
    )
    still_unmarked: set[str] = set()
    for path in _source_modules():
        tree, lines = _parsed(path)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                and not _SNAKE.fullmatch(node.name)
                and "N802" not in lines[node.lineno - 1]
            ):
                still_unmarked.add(f"{_rel(path)}:{node.name}")
    resolved = sorted(set(_NON_SNAKE_FUNCTIONS_MISSING_THE_MARKER) - still_unmarked)
    assert not resolved, (
        f"{resolved} are now marked (or gone) — delete the ledger entries and "
        "lower the bound above."
    )


def test_module_level_constants_are_screaming_snake_case() -> None:
    """SCREAMING_SNAKE_CASE for constants; module state stays snake_case."""
    constants_seen = 0
    offenders: list[str] = []
    for path in _source_modules():
        tree, _lines = _parsed(path)
        for name, lineno in _module_level_constants(tree):
            constants_seen += 1
            if not _SCREAMING.fullmatch(name):
                offenders.append(f"{_rel(path)}:{lineno} {name}")
    assert constants_seen >= 200, (
        f"only {constants_seen} module-level constants found (floor 200) — the "
        "detector has stopped recognising them, so a clean result here is not a "
        "clean codebase"
    )
    assert not offenders, (
        "CLAUDE.md naming convention: module-level CONSTANTS are "
        f"SCREAMING_SNAKE_CASE. These are not:\n  {chr(10).join(offenders)}\n"
        "If the name is really mutable module state rather than a constant, it "
        "will be excluded automatically once it is written to — check whether "
        "you meant `Final`."
    )


def test_the_naming_detectors_fire_and_do_not_over_fire() -> None:
    """Non-triviality twin for §5, one assertion per detector, both directions."""
    assert _SNAKE.fullmatch("_do_rip") and _SNAKE.fullmatch("__init__")
    assert not _SNAKE.fullmatch("closeEvent"), (
        "the snake_case matcher accepts camelCase"
    )
    assert _PASCAL.fullmatch("MainWindow") and not _PASCAL.fullmatch("main_window")
    assert _SCREAMING.fullmatch("_MIN_TRACKS") and not _SCREAMING.fullmatch("MinTracks")

    # The constant detector must EXCLUDE the three real shapes of module state,
    # or it reports correct code — the failure that would get this sweep deleted.
    logger_only = ast.parse("import logging\nlog = logging.getLogger(__name__)\n")
    assert not _module_level_constants(logger_only), (
        "a module-level logger was classified as a constant"
    )
    type_alias = ast.parse(
        "from collections.abc import Callable\nRunner = Callable[[str], int]\n"
    )
    assert not _module_level_constants(type_alias), (
        "a type alias was classified as a constant; type aliases are PascalCase "
        "by convention and reporting them would fill this sweep with excuses"
    )
    global_flag = ast.parse(
        "_open = False\n\n\ndef show() -> None:\n    global _open\n    _open = True\n"
    )
    assert not _module_level_constants(global_flag), (
        "a `global`-rebound flag was classified as a constant"
    )
    mutated_list = ast.parse(
        "_threads = []\n\n\ndef keep(t: object) -> None:\n    _threads.append(t)\n"
    )
    assert not _module_level_constants(mutated_list), (
        "a list mutated in place was classified as a constant"
    )
    # …and it must still FIND a real one, mis-named.
    real = ast.parse("MAX_TRACKS: int = 99\nbad_name: int = 1\n")
    assert {name for name, _line in _module_level_constants(real)} == {
        "MAX_TRACKS",
        "bad_name",
    }, "the constant detector no longer finds plain literal constants"


# ─────────────────────────────────────────────────────────────────────────────
# §6 — Code convention: "Split when a file exceeds ~300 lines… The line count is
# a *heuristic for cohesion*, not a hard cap."
#
# A hard failure would therefore be WRONG: the rule explicitly refuses to be a
# cap, and 66 modules are over the line today, several of them legitimately
# (`accuraterip_offsets_data.py` is a generated blob; `parsers/cyanrip_log.py` is
# one cohesive parser). Failing them all would produce a test everyone disables,
# which is worse than no test.
#
# So it is a RATCHET, the shape this repo already uses for
# `test_qthread_ownership.py::_WORKERS_WITHOUT_CANCEL`: the current set is
# recorded with its counts, and the sweep fails only when an oversize file GROWS
# or a NEW file joins. Growth is the direction the heuristic is actually about —
# a 4,140-line module is not going to be fixed by this test, but it must not
# become 4,300.
#
# Counts were measured on 2026-08-28 against the working tree. Refresh them in a
# deliberate commit if a file legitimately grows; the point is that it takes a
# decision, not silence.
# ─────────────────────────────────────────────────────────────────────────────


#: The line-count threshold from the convention. `> 300`, since the rule says
#: "exceeds ~300 lines".
_MODULE_LINE_THRESHOLD: Final[int] = 300

#: RATCHET — every module already over the threshold, with the count it had when
#: this was written. A file may shrink or leave; it may not grow, and no new file
#: may join.
_OVERSIZE_MODULES: Final[dict[str, int]] = {
    "adapters/accuraterip_offsets.py": 308,
    "adapters/accuraterip_offsets_data.py": 388,
    "adapters/cache_probe.py": 372,
    "adapters/cover_art.py": 566,
    "adapters/ctdb_client.py": 332,
    "adapters/cyanrip_backend.py": 1402,
    "adapters/musicbrainz_client.py": 524,
    "adapters/rip_backend.py": 585,
    "adapters/ripper_log_verify.py": 414,
    "adapters/transcode.py": 305,
    "app.py": 1349,
    "appimage_integration.py": 326,
    "config.py": 753,
    "cue_validate.py": 1257,
    "cyanrip_cli.py": 327,
    "deps/checks.py": 437,
    "deps/fork_source.py": 1678,
    # One job, stated as a question: *which link in the ripper chain fails to
    # exit?* The four parts — spawn one invocation under a deadline, orchestrate
    # the four invocations, decide the narrowest verdict they support, render the
    # record — are the steps of that single answer, and splitting the decision
    # table away from the observations it reads would put a claim and its
    # evidence in different files. Roughly 40% of the lines are the comments
    # explaining why each bound and each tri-state is there, which the cohesion
    # heuristic is explicitly not meant to punish.
    "deps/ripper_wrapper_probe.py": 510,
    "deps/host_setup.py": 663,
    "deps/host_teardown.py": 343,
    "deps/ripper_manifest.py": 608,
    "deps/ripper_offer.py": 777,
    # +4 on 2026-09-04: one KNOWN_CODES entry (`ripper.secure_rerip_verdict`)
    # and the three comment lines saying why it is not a fatal. The registry is
    # this module's point — a code declared anywhere else would defeat it.
    "diagnostics.py": 685,
    "drive_control.py": 383,
    "drive_profiles.py": 488,
    # Raised 1450 -> 1490 on 2026-09-04, deliberately. The addition is the
    # tri-state `_status_line` honesty fix: an EAC-format log must not print
    # "Copy OK" under a track whose own re-reads disagreed. The renderer is the
    # only place that can know both facts at once, so moving it out would put
    # the verdict in one file and the evidence it is drawn from in another --
    # the same reason the decision table above stays with its observations.
    "eac_log_export.py": 1490,
    "evidence_bundle.py": 885,
    # +22 on 2026-09-04: the measurement behind the relabelled pair line. The
    # line is one f-string; the rest is the docstring recording that the
    # 2026-09-03 diagnostics header named the approved build for a session that
    # ran a different one. The evidence belongs beside the renderer it explains.
    "handshake_approval.py": 513,
    "help_content.py": 561,
    "naming.py": 315,
    # +29 on 2026-09-04: `is_secure_rerip_verdict` and its reasoning. It is
    # DELIBERATELY here rather than at the worker that calls it — the point of
    # the fix is that the module owning read stability owns the classification,
    # so a consumer cannot form a second opinion about the same sentence.
    "parsers/cyanrip_log.py": 2759,
    # +29 (2026-09-05): `secure_rerip_tracks_scoped`, the ONE predicate that
    # `rig_check` and the acceptance script's `expect-secure-rerip` both read.
    # It belongs beside the dataclass it interrogates; a third module for one
    # pure function would be the new-file-as-last-resort rule broken to satisfy
    # a line count.
    "parsers/rip_log.py": 831,
    "preflight.py": 905,
    "read_speed_ladder.py": 367,
    "report_types.py": 667,
    # +23 on 2026-09-04: two SKIPs promoted to FAIL, with the reasoning that
    # separates them from the SKIP one branch up. "Nothing was given to look
    # at" and "a folder was given and holds no log" are different facts, and
    # the comment is what stops the next reader collapsing them again — §G is
    # ARCHIVAL and this exit code is its whole grade.
    # +3 (2026-09-05): now DELEGATES the "was the re-read exercised?" count
    # instead of computing it inline, so the manifest row and the graded verb
    # cannot answer one question with two keys.
    "rig_check.py": 799,
    "rip_addendum.py": 493,
    "rip_audit.py": 1216,
    "rip_compare.py": 1404,
    "rip_files.py": 422,
    "rip_report.py": 2302,
    # +68 on 2026-09-04: round 15 split their P5 into P5 (121) and P5a (7,
    # "strings this document does NOT classify"). The addition is the two
    # decision lists — RETAINED_BEYOND_P5 gained five rows and P5A_NOT_RETAINED
    # is new — and almost all of it is the REASON each row went where it did.
    # P5a is explicitly not a safety claim ("two of the rows really are
    # failures" and they do not say which two), so a row without its reasoning
    # beside it is a row the next reader will move on a guess. This module is
    # the provenance record for that seam; splitting the reasons out of it
    # would leave the claim here and the evidence elsewhere.
    "ripper_message_inventory.py": 1051,
    "settings_validation.py": 879,
    "sleep_inhibit.py": 599,
    "test_session.py": 794,
    "ui/dialogs/pending_installs.py": 419,
    "ui/dialogs/script_console.py": 454,
    "ui/disc_info_panel.py": 319,
    "ui/drive_setup_dialog.py": 500,
    "ui/host_setup_dialog.py": 341,
    "ui/main_window.py": 1558,
    "ui/main_window_deps.py": 589,
    "ui/main_window_drive.py": 555,
    "ui/main_window_helpers.py": 508,
    "ui/main_window_provision.py": 1212,
    "ui/main_window_rip.py": 4140,
    "ui/main_window_shared.py": 392,
    "ui/main_window_update.py": 953,
    "ui/rip_progress.py": 1658,
    "ui/settings_dialog.py": 1303,
    "ui/track_table.py": 802,
    # +184 on 2026-09-04: `_do_expect_rip_complete`, plus the freshness marker
    # in `_do_rip` and the sentinel beside `MAX_RIP_WAIT_S`. Mostly comment, and
    # the comment is the load-bearing part twice over: the verb replaces
    # `expect-status Done`, a claim about the DISC wearing a claim about the run,
    # and its first two versions each carried a defect a reader would otherwise
    # reintroduce (the completion footer counts against the disc, not the
    # selection; and the freshness marker has to be taken ahead of `rip`'s
    # refusal paths, not on its success path). The handler stays beside the one
    # it replaces because a reader comparing the two needs them in one file, and
    # the marker has to live in `_do_rip` because that is the step it is about.
    # +43 on top of the earlier raise: `abort-if-failed` scoped to its own
    # section, plus the section marker in `_do_log`. The comment carries the
    # refutation as well as the fix — an adversarial reviewer showed the
    # scenario first given for this was wrong, so the next reader needs to
    # know the change rests on the harness not contradicting the release bar,
    # not on a measured failure.
    # +309 (2026-09-05): three handlers for the three ARCHIVAL claims that had
    # NO assertion — `expect-log-well-formed` (§I), `expect-secure-rerip` (§N),
    # `expect-identified` (§E) — plus a floor on `snapshot`, whose 22 sites
    # could not fail. Raised rather than split BECAUSE the split is real work
    # and this landed hours before an eight-hour unattended hardware run:
    # refactoring the script engine on the same night as the run it drives is
    # the risk this project keeps paying for. The split is TASKS.md work and
    # this number is the debt marker, recorded deliberately and not silently.
    "uiscript/runner.py": 3429,
    "uiscript/script.py": 318,
    # +38 on 2026-09-04: the `expect-rip-complete` entry. This module IS the
    # closed vocabulary and its own docstring calls it the security boundary,
    # so a verb declared anywhere else would defeat the file. The comment is
    # most of the addition and stays with the entry it justifies.
    # +81 (2026-09-05): the three verb registrations for the handlers above.
    # Each carries its "why this verb exists" comment, which is the file's
    # established shape and the reason it is long.
    "uiscript/verbs.py": 652,
    "update_install.py": 304,
    "verdict.py": 521,
    # +24 on 2026-09-04: the secure-re-read branch that defers to the parser,
    # plus the comment recording the bundle measurement that produced it. The
    # line-classification loop is one cohesive read of the ripper's output.
    "workers/rip_worker.py": 3309,
}


def _module_line_counts() -> dict[str, int]:
    """Every module's line count, package-relative."""
    return {
        _rel(path): len(path.read_text(encoding="utf-8").splitlines())
        for path in _source_modules()
    }


def test_no_new_module_crosses_the_size_threshold() -> None:
    """A file crossing ~300 lines is a prompt to ask whether it does one job."""
    counts = _module_line_counts()
    assert len(counts) >= _MIN_SOURCE_MODULES, (
        f"only {len(counts)} modules measured (floor {_MIN_SOURCE_MODULES}) — the "
        "population is broken and this ratchet is measuring nothing"
    )
    newly_over = sorted(
        f"{name} ({count} lines)"
        for name, count in counts.items()
        if count > _MODULE_LINE_THRESHOLD and name not in _OVERSIZE_MODULES
    )
    assert not newly_over, (
        "CLAUDE.md: 'Split when a file exceeds ~300 lines. One responsibility "
        "per module.' These have just crossed it:\n  "
        + "\n  ".join(newly_over)
        + "\nThe count is a heuristic for cohesion, not a cap — so the question "
        "is whether the module is doing more than one job, and the answer may "
        "legitimately be no. If it is genuinely cohesive, add it to "
        "_OVERSIZE_MODULES with its count in a commit that says why."
    )


def test_no_oversize_module_grows() -> None:
    """The direction the heuristic is actually about.

    A 4,140-line module will not be fixed by a test. It can be stopped from
    becoming 4,300 — which is the difference between a known debt and a
    spreading one.
    """
    counts = _module_line_counts()
    assert len(counts) >= _MIN_SOURCE_MODULES, (
        f"only {len(counts)} modules measured (floor {_MIN_SOURCE_MODULES})"
    )
    grown = sorted(
        f"{name}: {counts[name]} lines, was {recorded} (+{counts[name] - recorded})"
        for name, recorded in _OVERSIZE_MODULES.items()
        if name in counts and counts[name] > recorded
    )
    assert not grown, (
        "these modules are already past the ~300-line cohesion heuristic and "
        "have grown:\n  "
        + "\n  ".join(grown)
        + "\nMove the new code into a focused module. If the growth genuinely "
        "belongs here, raise the recorded number in a commit that says why — "
        "deliberately, not silently."
    )


def test_the_oversize_ratchet_is_not_stale() -> None:
    """The other direction: the record cannot outlive its subject.

    A stale entry makes the ratchet describe a tree that has moved on, and — the
    part that bites — an entry for a deleted file silently leaves the population
    of the growth check instead of failing it. That is the exact mechanism
    `CLAUDE.md` records for the doc-index check that filtered its own candidates
    to files that still exist.
    """
    counts = _module_line_counts()
    assert _OVERSIZE_MODULES, "the ratchet is empty, so it cannot fail"
    gone = sorted(name for name in _OVERSIZE_MODULES if name not in counts)
    assert not gone, (
        f"these ratchet entries name modules that no longer exist: {gone}. "
        "Remove them — an entry with no subject is a check that quietly stopped."
    )
    shrunk = sorted(
        f"{name}: now {counts[name]}, recorded {recorded}"
        for name, recorded in _OVERSIZE_MODULES.items()
        if name in counts and counts[name] <= _MODULE_LINE_THRESHOLD
    )
    assert not shrunk, (
        "these modules are no longer oversize — delete their ratchet entries so "
        f"they cannot silently grow back:\n  {chr(10).join(shrunk)}"
    )


def test_the_size_ratchet_can_fail() -> None:
    """Non-triviality twin for §6.

    The two ways this could be decoration: the threshold could be so high that
    nothing reaches it, or the recorded counts could be padded so far above
    reality that no realistic growth trips them. Both are asserted against —
    the recorded numbers must be the REAL ones, not headroom.
    """
    counts = _module_line_counts()
    over = {n: c for n, c in counts.items() if c > _MODULE_LINE_THRESHOLD}
    assert over, (
        "no module exceeds the threshold, so `test_no_oversize_module_grows` "
        "has an empty population — either the threshold or the measurement is "
        "wrong"
    )
    padded = sorted(
        f"{name}: recorded {recorded}, actually {counts[name]}"
        for name, recorded in _OVERSIZE_MODULES.items()
        if name in counts and recorded > counts[name]
    )
    assert not padded, (
        "these recorded counts are ABOVE the file's real length, so the module "
        "has that much room to grow before the ratchet notices. Record the real "
        f"count:\n  {chr(10).join(padded)}"
    )


# ==========================================================================
# §7 — `QDesktopServices.openUrl`'s bool is never thrown away
# ==========================================================================
#
# **Found by the lesson-to-gate audit, 2026-08-28, and it was live in a shipped
# build.** `openUrl` returns False when nothing on the system claims the URL —
# no browser handler, no association, a portal that declined — and that bool is
# the only warning there is. Throw it away and the button becomes a coin flip:
# it works on one machine and does nothing at all on another, with no error, no
# log line and nothing to report.
#
# `ui/external_open.py` exists to fix exactly that, and its own docstring cites
# §5.o — *enforce a rule across the codebase, not at the place it was learned*.
# It was applied at three call sites. A **fourth** was then written without it,
# in `ui/main_window_update.py`: *"Open the download page?"* → **Yes** called
# `QDesktopServices.openUrl` directly and discarded the result, so the one
# button offering a user their update silently did nothing on a desktop with no
# browser handler.
#
# That is §5.o landing on the module written to answer §5.o, which is the whole
# argument for this sweep over another careful fix: the rule was known, written
# down, and cited — and still only bound the sites somebody remembered.


def _discarded_open_url_calls() -> list[str]:
    """Every `QDesktopServices.openUrl(...)` whose return value is dropped.

    A call is "discarded" when it is a bare expression statement — `ast.Expr` —
    rather than something whose value is used: assigned, returned, tested in an
    `if`, or passed on. That is the precise shape of the defect, and it is why
    this is an AST walk and not a grep: `if QDesktopServices.openUrl(u):` and
    `ok = QDesktopServices.openUrl(u)` are both correct and a text search cannot
    tell them from the broken form.
    """
    offenders: list[str] = []
    for path in _source_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "openUrl":
                offenders.append(f"{_rel(path)}:{node.lineno}")
    return offenders


def _open_url_mentions() -> int:
    """How many modules reference `openUrl` at all — the sweep's floor."""
    return sum(
        1 for path in _source_modules() if "openUrl" in path.read_text(encoding="utf-8")
    )


def test_no_module_throws_away_open_urls_return_value() -> None:
    """The regression test for the update dialog's dead button."""
    mentions = _open_url_mentions()
    # Floor: if `openUrl` vanished from the tree entirely (renamed, wrapped,
    # moved to a helper this walk does not follow) the sweep would pass by
    # matching nothing, which is the shape the rest of this file refuses.
    assert mentions >= 1, (
        "no module mentions `openUrl` any more — this sweep is measuring "
        "nothing. If the call genuinely moved, repoint it; do not delete it."
    )
    offenders = _discarded_open_url_calls()
    assert not offenders, (
        "these call sites discard `QDesktopServices.openUrl`'s return value, "
        "which is the ONLY signal that nothing on the system claims the URL — "
        "the button then does nothing, silently, with no log line:\n  "
        + "\n  ".join(offenders)
        + "\n\nUse `platterpus.ui.external_open.open_path_externally` (a local "
        "path) or `open_web_url` (a web address). Both check the bool and show "
        "the user something they can copy."
    )


def test_the_open_url_detector_fires_and_does_not_over_fire() -> None:
    """Both directions, against constructed source.

    The over-fire half is the one that keeps this check alive: flagging a
    correctly-checked call would make it a false-failure machine, and those get
    deleted rather than obeyed.
    """
    broken = ast.parse("QDesktopServices.openUrl(QUrl(u))\n")
    assert any(
        isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Attribute)
        and n.value.func.attr == "openUrl"
        for n in ast.walk(broken)
    ), "the detector would not catch the exact line that shipped"

    for correct in (
        "if QDesktopServices.openUrl(QUrl(u)):\n    pass\n",
        "ok = QDesktopServices.openUrl(QUrl(u))\n",
        "return QDesktopServices.openUrl(QUrl(u))\n",
    ):
        tree = (
            ast.parse(correct)
            if "return" not in correct
            else ast.parse("def f():\n    " + correct)
        )
        assert not any(
            isinstance(n, ast.Expr)
            and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute)
            and n.value.func.attr == "openUrl"
            for n in ast.walk(tree)
        ), f"a correctly-checked call is being flagged: {correct!r}"
