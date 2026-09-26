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
    # 356 lines on 2026-09-14, crossing the ~300 heuristic with round 18's rename.
    # **Kept as one module deliberately.** The heuristic asks whether a file is
    # doing more than one job, and this one is not: it is the script run report —
    # the outcome vocabulary, one step's record, the run's record, and the one
    # rendering of them. Splitting the vocabulary from the record it annotates would
    # put the CONCEPT mapping in one file and the enum it maps in another, which is
    # precisely the two-places-one-fact shape this round was called to fix.
    # Most of the growth is comment: the swapped tokens carry their concept and the
    # reason inline, because a reader who meets `SKIPPED` in a transcript has no
    # other way to learn it changed meaning.
    # 356 -> 363 on 2026-09-14 (+7): the tier/label fields on StepRecord, with the
    # note saying they arrive before their users on purpose.
    # 363 -> 428 on 2026-09-14 (+65): tier 4. `VERDICTS` (which outcomes are a
    # claim about the subject rather than a statement about the run),
    # `StepRecord.structural`, `RunReport.sweep_only`, and the render branch that
    # stops a sweep-only run saying "all checks passed". **Still one job**, and the
    # same argument as above with more force: `sweep_only` is a question about the
    # record, asked of the outcome vocabulary, answered for the renderer. Those
    # three already live here and a split would make the sweep rule a fact held in
    # two files that must agree. Roughly two thirds of the +65 is comment, because
    # every one of these encodes a decision the fork and we made jointly and a
    # reader needs the reason, not the mechanics.
    # **428 -> 464** (2026-09-24): `run_size` and `counts_as_evidence` in the report, the not-evidence banner, and `ok` forgiving ONLY size-declined steps.
    "uiscript/report.py": 464,
    # **308 -> 314** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "adapters/accuraterip_offsets.py": 314,
    "adapters/accuraterip_offsets_data.py": 388,
    "adapters/cache_probe.py": 372,
    # **566 -> 567** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "adapters/cover_art.py": 567,
    "adapters/ctdb_client.py": 332,
    # --- The 2026-09-09 log-verification race: eight files, one defect ------
    #
    # A cancelled rip's log was read 6.1 s before the ripper finished writing
    # it, and three archival surfaces published the absence as a finding:
    # `ripper_log_verification: "failed"` in the report, `health_status: null`
    # beside it, and an EAC-compatible log reading "Conclusive status report :
    # absent" over a rip whose end-of-rip summary is six lines long. The log on
    # disk was complete and correctly signed throughout. The process we signal
    # is the host-side Distrobox wrapper; the process that writes the log lives
    # in the container and outlives it.
    #
    # The bumps below are all that one fix. Each entry says what its file took
    # on and why that file rather than another; the new code that is genuinely
    # its own concern went into a NEW focused module, `ripper_log_settle.py`,
    # rather than into any of them.
    # +37 (2026-09-05): the `-j` diagnostics flag and the paragraph explaining
    # why it is the ONLY artifact for an argv-refused run, why it was added
    # after the acceptance run rather than before, and the two places its
    # existence was verified. A flag added silently is how `-V` happened.
    # 1439 -> 1501 (2026-09-06): assert_output_paths_stay_put, the argv
    # chokepoint's third guard. It lives in this file rather than beside it so
    # every route to the ripper inherits it -- the same reason the numeric and
    # metadata guards are called from there -- and most of the growth is the
    # docstring recording that no input route can currently reach it, which is
    # what stops a future reader deleting it as dead.
    # **1544 -> 1567 on 2026-09-07**, for making a SKIPPED `-t` range check
    # visible. The guard is conditional on the disc's track total and two UI
    # callers can pass None, so an unknown count skipped it silently — on the one
    # path where an out-of-range `-t` costs the whole rip. The addition is a log
    # line plus the paragraph saying why it is a log line and not a refusal, and
    # it belongs beside the guard it describes: a warning about a check, in a
    # different file from the check, is the split that makes the next reader
    # believe the check is unconditional.
    # **1567 -> 1577 on 2026-09-10** (log-verification race, above): the
    # `writer_finished` keyword forwarded to the classifier, plus the
    # paragraph saying why this class must FORWARD the caller's declaration
    # rather than re-derive it: a second opinion about one fact is the shape
    # `CLAUDE.md` names as guaranteed to drift, and here both opinions
    # produce a `LogVerification`, so the drift would be invisible.
    # 2026-09-25: errors="replace" on the text-mode pipe (a byte that was not UTF-8 raised and ended the read); tests/test_inbound_text.py sweeps it.
    # **1578 -> 1594** (2026-09-25, D14: control characters in the tag-only fields are replaced, and the report says so): the chokepoint applies `tag_hygiene` and logs each replacement.
    # **1594 -> 1638** (2026-09-25, TASKS `conv.argv-range`): `_tracks_on_disc` range-checks `-l` against the disc, which cyanrip enforces by refusing the whole rip. It belongs beside `_disc_position` and the `-t` check in `_metadata_args`, which are the same kind of guard.
    # **1638 -> 1640** (2026-09-25, the property-test batches): an unknown `%{…}` token's brace becomes a paren, so it cannot reach cyanrip as an unterminated `{` (TASKS `fuzz:adapters.cyanrip_backend.scheme_from_template`).
    # **1640 -> 1670** (2026-09-25, D18: `%N`/`%M` work everywhere): the disc position is checked once and fills in `%N`/`%M` as well as `-c`, so a folder name cannot disagree with the tags; `_disc_args` folded into `_disc_position`, keeping its reasoning.
    "adapters/cyanrip_backend.py": 1670,
    "adapters/musicbrainz_client.py": 524,
    # **585 -> 594 on 2026-09-10** (log-verification race, above): the same
    # keyword on the ABC, where it belongs: any ripper that writes its
    # signature last has the window, so this is a property of the SEAM and
    # not of cyanrip.
    "adapters/rip_backend.py": 594,
    # **414 -> 467 on 2026-09-10** (log-verification race, above): the
    # branch that turns an absent footer into `not_determined` when the
    # writer has not been seen to finish. Most of the growth is the comment
    # recording the measurement — verdict stamped at 22:02:08.902, footer
    # written at 22:02:15 — because the branch above it is the 2026-08-20
    # fix for the same field and a reader needs to see the two are different
    # questions, not a duplicate.
    # **467 -> 473** (2026-09-25, the property-test batches): exit 127 from the wrapper is a missing ripper, not an altered log (`binary_missing`, as `flac_verify`).
    "adapters/ripper_log_verify.py": 473,
    "adapters/transcode.py": 305,
    # **1349 -> 1356 on 2026-09-12** (+7): `--rig-session`'s default output
    # directory moved out of `$HOME` and under the one deletable parent, and the
    # growth is the paragraph saying why plus the import of the shared helper.
    # It DELEGATES to `test_session.rig_parent` rather than building the path
    # again -- two call sites each spelling "where our stuff goes" is exactly how
    # $HOME came to hold two different kinds of litter.
    # **1356 -> 1373 (2026-09-22)** (+17): the desktop-entry association. Two
    # lines of code -- `setApplicationName(APP_NAME)` in place of a literal, and
    # the static `QGuiApplication.setDesktopFileName` -- and the rest is the
    # MEASUREMENT, which is the load-bearing part: `setDesktopFileName` is the
    # API that reads like the fix and changes neither half of WM_CLASS on
    # xcb/6.11.2, so a reader who trusts its name deletes the line that is
    # actually holding the pairing up.
    # **1373 -> 1374** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # **1374 -> 1380 (2026-09-24)**: the startup call that removes INVOCATION_ID
    # before anything spawns, so a container we start is not owned by this
    # window's unit (`container_scope.py`). It has to be here: it must run first.
    "app.py": 1380,
    # **326 -> 349 (2026-09-22)** (+23): `StartupWMClass` in the generated
    # entry, and the comment recording the measured WM_CLASS it has to match
    # (`"__main__.py", "platterpus"`) plus why the value is APP_NAME and not the
    # app-id the file is named for. A guessed string here fails silently -- the
    # pin simply stays dark -- so the derivation is worth more than the line.
    "appimage_integration.py": 349,
    # **753 -> 784 on 2026-09-18**: the paired `integration_declined_version` field and the note recording why the path-only key reproduced the bug it replaced.
    # **784 -> 806 (2026-09-23)**: `APP_STATE_FIELDS`, the one list of fields the app
    # writes for itself, which Settings carries over and the acceptance restore
    # leaves alone. Named here because two surfaces must agree on it.
    # **806 -> 847 (2026-09-24)**: offset-variant re-reads became the default.
    # `DEFAULT_RERIP_OFFSET_VARIANT`, the one default three places read, with the
    # evidence that turned it (a one-frame match passed wrong audio twice), and the
    # v8->v9 step that flips a saved False once. Migrations live here by design.
    # **847 -> 848** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # **848 -> 849** (2026-09-25, D18: `%N`/`%M` work everywhere): the template comment no longer says multi-disc folders are impossible.
    "config.py": 849,
    "cue_validate.py": 1257,
    "cyanrip_cli.py": 327,
    "deps/checks.py": 437,
    # 1678 -> 1691 (2026-09-06): the round-15 close. `FORK_PIN` rolled to
    # `978f9b0` and the roll is documented where the constant is, because the
    # post-close step is the one this file has already watched go stale.
    # 1691 -> 1705 (2026-09-06, same day): FORK_EXPECTED_VERSION is a LITERAL
    # beside a DERIVED build tag, so the round-15 roll moved one and not the
    # other and the banner named a build that never existed. The growth is the
    # note saying so where the literal is, because the next person to roll a
    # pin reads this file and not the changelog.
    # 1705 -> 1790 at round 16. All comment, no code: the reviewed pin moved and
    # three constants around it now carry the DERIVATION that licenses them —
    # the recomputed source anchor, why the version legitimately did not move
    # with the pin, and why no release sequence was invented for a build the
    # fork has not published. Those are exactly the paragraphs a future reader
    # needs and cannot reconstruct, and splitting the file would separate a
    # constant from the reason it holds. Raised deliberately, which is what
    # this ratchet asks for; the module is still one responsibility.
    #
    # **1783 -> 1835 on 2026-09-07**, for `rig_installs_the_test_pin()` and the
    # two `why` strings it now decides. Round 16 is the first round to name a
    # test pin DISTINCT from the pin under review, and `UNDER_REVIEW_TARGET.why`
    # still read *"what an acceptance run must be on"* — so `--install-ripper
    # list` printed two candidates and called the wrong one mandatory, at 2am, to
    # an operator deciding what to put on the drive.
    #
    # The growth is one derived predicate plus its docstring, and it belongs
    # HERE for the reason the paragraph above gives: it compares `FORK_TEST_PIN`
    # against `PIN_UNDER_REVIEW`, and a comparison of two constants in a
    # different file from the constants is the split this ratchet's own note
    # warns against. Moving it would separate the answer from the two facts it
    # is derived from.
    #
    # **1835 -> 1872 in the same session**, for `_known_pairing_for()`: the SWEEP
    # of the rule the production branch of `target_for_commit` had already
    # learned. That branch knew the approved pin's version and said "not known"
    # for the reviewed and test pins — one of three. The lookup replaces three
    # would-be special cases with one loop over the targets it already holds, so
    # this is the shape that stops the file growing again when a fourth known pin
    # appears.
    # **1872 -> 1890 on 2026-09-08**, for `pin_the_rig_should_install()`.
    # One derived answer to "which build must an acceptance run have installed",
    # extracted at the moment a THIRD caller was about to restate it — two of the
    # three surfaces answering that question had already disagreed inside a week.
    # It compares the two pins, so it belongs beside them for the reason the note
    # above gives.
    # **1890 -> 1900 on 2026-09-12, when round 17 opened** (+10): `PIN_UNDER_REVIEW`
    # moved `a9aedf0` -> `fe4d2c4` and the paired version with it, and both carry the
    # note saying WHY the candidate is deliberately not the bump — their lap 1 §2:
    # `6a9a080` moved the version, `a2523c4` regenerated the artifacts, `fe4d2c4` is
    # the first commit at which they agree, and `6a9a080` is red on its own suite.
    # A bare SHA swap with no record of that distinction is how a release gets cut at
    # the bump, which their §2 says has already cost them one.
    # **1900 -> 1909 the same day** (+9): the round-17 candidate joins
    # `BUILD_TAGS_ACCEPTING_CONSUMER_FLAG`, with the evidence rather than the bare
    # tag. `test_handshake_pin_under_review` requires any capability claimed for the
    # build under review to be listed in the newest FILED provider contract, so the
    # comment cites where `--consumer` and `--verify-log` were read and notes that
    # their lap 1 §3 says the same independently. A bare SHA in a capability set is
    # the unbacked claim that test exists to refuse.
    # **1909 -> 1964 the same day, when round 17 CLOSED and the pin ROLLED** (+55).
    # The roll is the first in three rounds: rounds 15, 16 and 17 all closed GO/GO,
    # and only this one could move `FORK_PIN`, because the fork had never published
    # round 16's `a9aedf0` and a pin cannot roll to a build nobody can install.
    # Four constants moved and each carries its derivation rather than a bare value:
    # `FORK_PIN` -> `fe4d2c4`; `FORK_RELEASE_SEQ_BY_PIN` gains `fe4d2c4: 22`, read
    # out of their `release-manifest.json` rather than their lap;
    # `PIN_UNDER_REVIEW_IS_PUBLISHED` False -> True, with the note that its honest
    # value changed between two commits of ours with nothing in our tree changing;
    # and `FORK_EXPECTED_VERSION` -> `.12`, which the sibling pairing guard caught
    # in the same run as the roll rather than a release later.
    #
    # The growth is comment, and it belongs here for the reason the block above
    # gives: the justification is the load-bearing part of each of these constants,
    # and a roll with no record of why is how a pin moves to a build with nothing
    # behind it.
    # **1964 -> 2006 on 2026-09-15**: `pin_under_review_label()` and
    # `pin_under_review_reason()`, the two short accessors section A needed so it
    # could stop composing its own copy of a sentence this module already owns.
    # Almost all of the growth is the docstrings recording what it printed on the
    # acceptance run — "the build under review (… there is no build under review)"
    # — because the next caller tempted to inline that literal needs the reason,
    # not the rule. They belong beside the pins they read, which is this file.
    # **2006 -> 2029 on 2026-09-16**, for round 21's test pin: `ddc1e8c` ->
    # `3952c03`, plus its retirement row. **Every one of the 23 lines is the
    # REASON, not the values** — the three constants themselves are three lines.
    # What the note has to carry is that this test pin INVERTS the round-16 one
    # directly above it: that one was worth recording because it was byte-identical
    # to the reviewed pin, and this one is worth recording because it is NOT, by
    # 211 insertions across five source files carrying both of round 21's breaking
    # changes. A reader who takes the adjacent reasoning forward gets the opposite
    # of the truth, and this is the one file where "the test pin is the same
    # program" would be believed. The derivation is in the note so nobody has to
    # re-run it, which is the same argument as the accessors' docstrings below.
    # **2029 -> 2060 on 2026-09-17**, for `TEST_PIN_IS_SAME_PROGRAM_AS_REVIEWED`.
    # The constant is one line; the other 30 are why it exists, and they have to
    # be here because this is the file a reader consults when a pin moves. It
    # records that round 16's "accept either pin" widening rested on
    # `git diff a9aedf0..ddc1e8c -- src/` being EMPTY, that round 21 is the first
    # round where that is false, and that the 2026-09-17 session went 247 of 247
    # green on the wrong build because two checks had been widened on the unstated
    # assumption. A bare `False` would be re-derived wrongly the first time
    # somebody assumed test pins are always cosmetic.
    # **2060 -> 2124 on 2026-09-18 (+64)**: round 22 opened on a NEW pin, the
    # first in five rounds to do so, and every added line is the reasoning a pin
    # move has to carry. Three facts a future reader needs where they will look
    # for them: that PIN_UNDER_REVIEW moved while FORK_PIN deliberately did NOT
    # (switching the installed pin mid-round is the one ask the deviation policy
    # still requires); that the release-sequence row is required the moment the
    # pin moves, or the offer tells an operator on a numbered release they are on
    # a hand-installed commit; and that the consumer accept-set entry is the LIVE
    # half of our own round-21 §H2 finding, backed by their published flag table
    # rather than assumed. The queued refactor of this file still stands and a
    # round opening is still not the commit for it.
    # **And the first number written here was 2078, measured before the last of
    # those edits had landed** -- the file's own *is the population I measured
    # closed?* rule, arriving in the commit that raises its ratchet. The gate
    # refused it, which is what a ratchet is for.
    # **2124 -> 2133 (round 22 close, 2026-09-21).** The post-close pin roll:
    # `FORK_PIN` to `2cce60d`, `FORK_EXPECTED_VERSION` to `0.9.4-rc2+platterpus.13`,
    # and `PRODUCTION_TARGET.why` rewritten to describe round 22's evidence rather
    # than round 17's. Every line is prose recording WHY the constant holds what it
    # holds -- which is the same reason this file is oversized and the same reason
    # the queued refactor keeps not happening in a round-close commit: the roll is
    # when the file is being read. Re-measured AFTER the last edit landed, which is
    # the correction the entry above records having got wrong once.
    # **2133 -> 2163 (round 24 open, 2026-09-23).** Two parts, one of them a fix.
    # The round-open move: `PIN_UNDER_REVIEW` to `3e01bb3`, its version pairing,
    # and the `release_seq` 24 row read off their live manifest. And a DEFECT the
    # move surfaced: `rig_installs_the_test_pin()` compared the two pins and never
    # asked which round nominated the test pin, so opening a round with
    # `HANDSHAKE-TEST-PIN: none` pointed the rig at round 21's retired `3952c03`.
    # The fix needs a stated `PIN_UNDER_REVIEW_ROUND` (8 lines with its reason) and
    # a round clause in the predicate (6). Measured after `ruff format`.
    # **Then 2174**, in the same change: two more round-open obligations the gate
    # suite named once the pin had moved — `TEST_PIN_IS_SAME_PROGRAM_AS_REVIEWED`
    # re-derived against `3e01bb3` (now False, with the diff that decided it), and
    # `g3e01bb3` added to the `--consumer` accept-set with the contract row that
    # backs it. Re-measured after the last edit.
    # **2174 -> 2195 (round 24 close on our gate, 2026-09-23).** The roll itself:
    # `FORK_PIN` to `3e01bb3`, `FORK_EXPECTED_VERSION` to `+platterpus.14`, and
    # `PRODUCTION_TARGET.why` rewritten for round 24's evidence. Most of the +21 is
    # the FORK_PIN comment recording that the constant rolled on OUR gate's close,
    # one lap EARLIER than our own lap 2 promised, and why — the two gates close on
    # different laps under v5. Left out, the next reader sees a pin that moved
    # against a sent lap's word with no account of it. Measured after `ruff format`.
    # **2195 -> 2198 (round 25 open, 2026-09-23)**: `PIN_UNDER_REVIEW_ROUND` 24 -> 25,
    # with the three lines saying why a round that reviews TEXT still names the pin.
    # **2198 -> 2226 (round 26 open, 2026-09-23)**: `PIN_UNDER_REVIEW` moves to
    # `df91ae7` (`+platterpus.15`) with the nine lines saying why moving it IS the
    # real-test mechanism and why `FORK_PIN` does not move with it; its release
    # sequence, its build tag in the `--consumer` accept-set with the contract that
    # licenses it, the re-derived same-program flag, and the round-26 pairing line.
    # **2226 -> 2239 (2026-09-23)**: the menu stops offering a test pin the open
    # round did not nominate, with why it is the same predicate the rig uses.
    # **2239 -> 2328 (2026-09-24)**: `accepted_rig_builds`, `expected_rig_build_text`,
    # `current_test_pin` and `retired_test_pins` — the one place that answers "which
    # builds may the rig be on?", beside the predicate they derive from. Section A,
    # the evidence manifest, the dependency report and the ripper check each derived
    # it themselves from the raw test-pin constant, and on 2026-09-24 section A
    # refused the build round 26 reviews (docs/testing.md §5.bq). Four copies became
    # one function here, so this file grew and those shrank.
    # **2328 -> 2340 (2026-09-24, round 26 close)**: the roll of `FORK_PIN` and
    # `FORK_EXPECTED_VERSION` to `df91ae7`, each with the history the constant's own
    # comment keeps, as every roll since round 7 has.
    # **2340 -> 2362 (2026-09-24, round 27 open)**: `PIN_UNDER_REVIEW` moves to
    # `221a1df` (`+platterpus.16`) with why, its release sequence, its build tag in
    # the `--consumer` accept-set with the contract that licenses it, the re-derived
    # same-program flag, and the round-27 pairing line.
    # **2362 -> 2382 (2026-09-25)**: `is_the_build_under_review`, the one predicate
    # the update offer and the setup wizard now both ask, so neither can replace the
    # build a round is reviewing (0.6.59 did, before the first Full run).
    "deps/fork_source.py": 2382,
    # One job, stated as a question: *which link in the ripper chain fails to
    # exit?* The four parts — spawn one invocation under a deadline, orchestrate
    # the four invocations, decide the narrowest verdict they support, render the
    # record — are the steps of that single answer, and splitting the decision
    # table away from the observations it reads would put a claim and its
    # evidence in different files. Roughly 40% of the lines are the comments
    # explaining why each bound and each tri-state is there, which the cohesion
    # heuristic is explicitly not meant to punish.
    "deps/ripper_wrapper_probe.py": 510,
    # **663 -> 688 (2026-09-25)**: the default wizard keeps the build under review, records that it did, and says so in its 'already present' line.
    "deps/host_setup.py": 688,
    # **343 -> 392 (2026-09-21).** The menu-cache rebuild the uninstaller never
    # did, and the comment saying why it is unconditional on the failure path and
    # absent on a dry run. Installing refreshed the caches and uninstalling did
    # not, so the launcher kept an entry pointing at a deleted AppImage — a
    # real-user screenshot. Most of the growth is that explanation, which is the
    # part that stops somebody "simplifying" it back to a step or to always-on.
    # **392 -> 393** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "deps/host_teardown.py": 393,
    "deps/ripper_manifest.py": 608,
    # **777 -> 782 (2026-09-24)**: asks `current_test_pin()` / `retired_test_pins()`
    # instead of the raw constant, and says why in four lines (§5.bq).
    # **782 -> 800 (2026-09-25)**: the up-to-date offer keeps the build under review instead of offering the approved pin over it.
    "deps/ripper_offer.py": 800,
    # +4 on 2026-09-04: one KNOWN_CODES entry (`ripper.secure_rerip_verdict`)
    # and the three comment lines saying why it is not a fatal. The registry is
    # this module's point — a code declared anywhere else would defeat it.
    # **685 -> 691** (2026-09-25, the property-test batches): `bounded_output` clamps its bounds and always keeps the tail.
    "diagnostics.py": 691,
    # **411 -> 423 on 2026-09-10** (log-verification race, above):
    # `FORCE_STOP_COUNTDOWN_S` moved here from the UI module that arms the
    # timer, because the rip worker's log wait must outlast it. Two
    # expressions of one number is exactly how the wait and the countdown
    # could stop agreeing; this file is the one whose docstring already
    # explains why the countdown exists at all.
    # **423 -> 411** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    "drive_control.py": 411,
    # **488 -> 447** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    "drive_profiles.py": 447,
    # Raised 1450 -> 1490 on 2026-09-04, deliberately. The addition is the
    # tri-state `_status_line` honesty fix: an EAC-format log must not print
    # "Copy OK" under a track whose own re-reads disagreed. The renderer is the
    # only place that can know both facts at once, so moving it out would put
    # the verdict in one file and the evidence it is drawn from in another --
    # the same reason the decision table above stays with its observations.
    # 1490 -> 1535 (2026-09-06): the UTC-offset marker. Most of the growth is
    # the docstring saying why the fix is ADDITIVE — a naive timestamp must
    # render byte-identically because real EAC carries no zone, so the next
    # person to "tidy" this into an unconditional suffix breaks parity.
    # **1535 -> 1576 on 2026-09-10** (log-verification race, above): the
    # ripper's own completion record — `Rip completed:` and `Interrupted
    # at:` — which this document held in its parsed input and dropped, while
    # printing "this log carries no end-of-rip summary" over a six-line
    # summary. Rendering rows belongs with the renderer; the growth is the
    # two rows and the tri-state that keeps a footerless log silent here.
    # **1576 -> 1574 on 2026-09-25**: the one-frame AccurateRip wording moved to
    # `one_frame_match`, agreed in round 27; the narrowing assert it needs is two
    # of the lines kept.
    # **1574 -> 1579 on 2026-09-25**: `46a522e` (that one-frame wording, HELD until the
    # fork's round-27 lap 4) is reverted on the session branch so a merge cannot carry it
    # onto `main`; this is the renderer's own wording code coming back. Reverting the
    # revert returns it to 1574.
    # **1579 -> 1640** (2026-09-25, D16, KDD-38: metadata may not forge a log signature): `_defuse_signature_lines` and `render_eac_style_log_and_defused`, which returns the rewritten lines for the report; the old entry point is a thin wrapper, so no caller changed.
    # **1640 -> 1635 on 2026-09-26**: the fork released round 27 lap 4 with these words
    # (the summary accepted, the per-track line in the amended form `46a522e`
    # already carried), so the revert is reverted and the wording code leaves again.
    "eac_log_export.py": 1635,
    # 885 -> 905. The gzip container is now opened explicitly so its header
    # timestamp can be zeroed, and the comment above it is the reason the next
    # reader needs: a one-second reproduction window looks like a flaky test,
    # and without the note someone reverts the fix to quiet a rerun. Raised
    # deliberately; the module is still one responsibility.
    # **906 -> 923 on 2026-09-10**: the manifest's `build` row. A version
    # names a release and a commit names the tree that ran; this file
    # printed only the first, so the cyanrip fork's round-16 lap 9 filed our
    # pin as unknown — while the commit sat in the bundle's own application
    # log the whole time. The row belongs in the function that writes the
    # manifest, and the growth is mostly the paragraph recording that it is
    # read from `build_fingerprint()`, the same source the banner uses, so
    # the two cannot disagree.
    # **923 -> 967 on 2026-09-13** (+44), for the middle-elision fix and the
    # reasoning behind it. The growth is almost entirely the docstring of
    # `_member_component`, and it belongs there rather than in a doc because the
    # function is four lines of string slicing whose *cut direction* is the whole
    # point: `cleaned[:64]` looks obviously correct and silently removed the build
    # tag from every album folder over 64 characters, then manufactured a
    # collision between two rips that differed only in a trailing suffix.
    #
    # A reader who trims the comment will re-introduce the tail-cut, because the
    # tail-cut is the version that looks tidier. That is what this ratchet's own
    # note means by growth that genuinely belongs.
    # **967 -> 1023 on 2026-09-17**: `_expected_ripper_build()` and the manifest
    # line it feeds. The bundle recorded what RAN and never what the session was
    # FOR, so 277 files could describe a run on the wrong ripper without a word of
    # alarm — and the approval field said "approved", which was true of our record
    # and exactly wrong as an answer to the question a reader was asking. The
    # helper belongs here because the manifest is this module's product; splitting
    # it out would put the sentence and the reason for the sentence in two files.
    # **1023 -> 1020 (2026-09-24): it SHRANK.** The expected-build line asks
    # `accepted_rig_builds` instead of re-deriving it.
    "evidence_bundle.py": 1020,
    # +22 on 2026-09-04: the measurement behind the relabelled pair line. The
    # line is one f-string; the rest is the docstring recording that the
    # 2026-09-03 diagnostics header named the approved build for a session that
    # ran a different one. The evidence belongs beside the renderer it explains.
    # 513 -> 526 (2026-09-06): `APPROVED_BY_ROUND` 14 -> 15 and
    # `APPROVED_FOR_PLATTERPUS_VERSION` 0.6.28 -> 0.6.37, each with the record
    # it was read from. These two constants went stale for two releases once
    # and stamped the wrong round into every archival log; the provenance is
    # the point, not decoration.
    # **526 -> 547 on 2026-09-12** (+21), when round 17 closed: `APPROVED_BY_ROUND`
    # 15 -> 17 and `APPROVED_FOR_PLATTERPUS_VERSION` -> 0.6.46. Both carry the two
    # things a later reader needs and cannot reconstruct: why 16 is SKIPPED (it
    # approved a pin the fork never published, so crediting it would name a pairing
    # nobody could install), and why the app version stays 0.6.46 while the release
    # carrying it is 0.6.47 (the round approved that pair; 0.6.47 is our own
    # between-rounds change, which this constant's docstring already says is ours to
    # make). A bare 15 -> 17 would read as an off-by-one.
    # **547 -> 563 on 2026-09-13** (+16), when round 18 closed: `APPROVED_BY_ROUND`
    # 17 -> 18 and `APPROVED_FOR_PLATTERPUS_VERSION` 0.6.46 -> 0.6.47. Raised
    # deliberately, and the growth is the same kind as every entry above it: this
    # file is where a round close is *justified*, not merely recorded, and round 18
    # is the first close that moved these constants **without moving the pin** — a
    # reader meeting `18` beside a pin round 17 approved needs the reason on the
    # spot. It also retires the awkwardness the 526 -> 547 note had to explain:
    # 0.6.46 and 0.6.47 are no longer different answers.
    #
    # **If this keeps growing, the fix is a data table, not a smaller comment.** The
    # module is ~40% provenance chain by now; splitting the history into a
    # structure (round, pin, app version, why) would make it iterable and testable.
    # Not done today because a refactor of the approval constants during a round
    # close is the wrong time to move them.
    # 563 -> 571 on 2026-09-14 (+8): the round 18 -> 19 provenance note. **This is
    # the third consecutive round to add ~8 lines of prose here and the note above
    # has now been true three times, so it is promoted from an observation to a
    # queued task** (TASKS.md): the provenance chain is a structure — (round, pin,
    # app version, why) — being stored as consecutive comment blocks, and it grows
    # by one block per round close regardless of whether anything else changes.
    # Still not refactored during a round close, for the reason already stated; the
    # difference is that "not today" now has a row rather than a comment.
    # **571 -> 584 on 2026-09-16 (+13)**: round 20 closed, so both approval
    # constants moved to the pair it reviewed — and the thirteen lines are the
    # reason, not the values. One lap earlier we argued this field should track
    # the shipped version and the fork refused it correctly; the note records
    # that the reasoning did not change, the RECORD did. Without it the next
    # reader sees a constant chasing __version__ and "helpfully" automates it.
    # **584 -> 610 on 2026-09-18 (+26)**: round 21 closed, so both constants moved
    # again — and once more every one of the lines is reasoning, not values. Two
    # facts needed recording where a future reader will look for them. Round 21 is
    # the first approval of `fe4d2c4` backed by hardware on the round's OWN subject
    # (rounds 18-20 re-approved it on evidence that predated them), and the first
    # attempt at that hardware was **void** — 247 of 247 green on the release pin
    # while the condition was about the test pin, with the guard for exactly that
    # passing because round 16 had widened it when the two pins were the same
    # program. A constant naming *which bilateral GO the pin rests on* is the right
    # place to record that the GO nearly rested on a session about a different
    # binary. The queued refactor still stands and this is still not the commit for
    # it: a round close is when the file is being read, not when it should move.
    # **610 -> 619 (round 22 close, 2026-09-21).** `APPROVED_BY_ROUND` 21 -> 22 and
    # `APPROVED_FOR_PLATTERPUS_VERSION` 0.6.50 -> 0.6.51, with the paragraph saying
    # where each came from: the app version is read from the PEER's closing lap,
    # and round 22 is the first approval in four rounds to move the pin rather than
    # re-approve it. Same judgement as the entry above -- a round close is when this
    # file is read, not when it should be split.
    # +13 (round 24, 2026-09-23): the approval record moves to round 24 / 0.6.53,
    # and says why the peer lap of record is their lap 1 — under v5 our gate closes
    # on OUR lap, so there is no later peer lap for the app version to be read from.
    # **651 -> 661 (round 25 closed, 2026-09-23)**: `APPROVED_BY_ROUND` 24 -> 25 with
    # why a round that reviewed TEXT re-approves the same pin, and the app version
    # read off their closing lap as the rule requires.
    # **661 -> 674 (2026-09-24)**: the retired-pin sentence can now say "no test pin
    # is in use now" and name the build under review, instead of naming round 21's
    # pin as the current one (§5.bq).
    # **674 -> 683 (2026-09-24, round 26 close)**: the approval record moved to round
    # 26 for 0.6.55, with the provenance the record's own rule requires beside it.
    "handshake_approval.py": 683,  # was 638: +19 for round 23's approval, and WHY the pin stands still while the round and app version move
    # **561 -> 582 (2026-09-21).** The User Guide section for the consolidated
    # Setup & Updates window. The guide is prose by definition, and a menu item
    # a user cannot find described in the app is the defect
    # `test_help_documents_the_menu.py` exists to catch — so this growth is the
    # other half of a gate, not incidental.
    # **582 -> 586 (2026-09-22)** (+4): the read-offset bullet became two, because
    # the guide described `read_offset` and `override_read_offset` as one control
    # called "Read offset override" — a name neither of them carries on screen —
    # and the number is inert without the tick-box, which the one-bullet version
    # had no room to say. Found by the new guide-vs-screen sweep, not by reading.
    # **586 -> 587 (2026-09-23)**: a menu path that named no real item now names the
    # real one, wrapped onto a second line.
    # **587 -> 589 (2026-09-24)**: everything an acceptance run makes in ONE
    # session folder (maintainer: *"stop polluting my home folder, keep this all
    # contained to 1 folder"*). The guide says where that folder is.
    # **589 -> 591** (2026-09-24): Accurip 450 is ONE frame, not a pressing. The glossary and the Settings bullet say what matched and name no cause.
    # **591 -> 605** (2026-09-24): the User Guide's acceptance section describes the three run sizes and the baseline, and corrects its old ripper advice.
    # **605 -> 630** (2026-09-24, #37 one home per setting): the User Guide says where each moved setting now lives (Set up drive…, Setup & Updates, the console) and what OK/Apply/Cancel/Restore Defaults do.
    # **630 -> 628** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    "help_content.py": 628,
    # 315 -> 359 (2026-09-06): path_escape_reasons, the ONE decision the
    # Settings validator and the argv chokepoint now share. Placed here because
    # settings_validation already imports naming and the question is about a
    # naming template; a third module for one pure function would be the new
    # file rule #7 refuses.
    # **359 -> 376** (2026-09-25, D18: `%N`/`%M` work everywhere): the preview fills in `%N`/`%M` and writes a typed brace as the parenthesis the file gets.
    "naming.py": 376,
    # +29 on 2026-09-04: `is_secure_rerip_verdict` and its reasoning. It is
    # DELIBERATELY here rather than at the worker that calls it — the point of
    # the fix is that the module owning read stability owns the classification,
    # so a consumer cannot form a second opinion about the same sentence.
    # 2759 -> 2819 (2026-09-06): the dispatch fix. `looks_like_cyanrip_log`
    # read exactly the first non-blank line and sent a valid cyanrip log with
    # one line of preamble to the legacy-format parser — zero tracks from
    # fourteen. The growth is the bounded scan, the legacy-format discriminator
    # it needs, the
    # named group the completeness sweep requires, and why each exists. The
    # module is long because it is a line-by-line contract with another
    # project; splitting it is tracked separately and is not this change.
    # **2819 -> 2831 on 2026-09-16 (+12)**: the round-20 rename, accepting BOTH
    # `Frame retries:` and `Retry limit:` permanently, plus the comment saying
    # why both and why in advance — the rename is invisible to the parse and not
    # to the completeness sweep, so the new label has to be here before their
    # build ships. The eleven lines of reasoning are the load-bearing part: a
    # later reader tidying this to a single label breaks every acceptance log
    # already filed under `docs/`.
    # **2831 -> 2937 (2026-09-21).** The both-wordings parser: `_TRACK_START`
    # accepts the fork's §0.3 rename alongside the wording every log written so
    # far carries, and the new `Encoder errors:` footer is parsed rather than
    # ignored. Nearly all of it is the reasoning — why the delimiter is
    # structural (the rename alone takes a real 14-track log to 0 tracks under a
    # report still claiming 14), why taking half of a split claim is worse than
    # taking neither, and why `not applicable` is not a failure. That reasoning is
    # the seam contract in prose, and it is what stops the next reader
    # "simplifying" the old wording away once .14 ships.
    # **2937 -> 2973 (2026-09-24, round 26 lap 4)**: `finished_track` and
    # `partial_summary_denominator` are made public HERE so the rip worker and the
    # report stop keeping their own copies — the copies are what drifted.
    # **2973 -> 2975** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # +1 on 2026-09-26: the `Accurip 450` comment names both cyanrip wordings, `.16`'s and `.17`'s (round 27 lap 4), so it stays true of both.
    "parsers/cyanrip_log.py": 2976,
    # +29 (2026-09-05): `secure_rerip_tracks_scoped`, the ONE predicate that
    # `rig_check` and the acceptance script's `expect-secure-rerip` both read.
    # It belongs beside the dataclass it interrogates; a third module for one
    # pure function would be the new-file-as-last-resort rule broken to satisfy
    # a line count.
    # **883 -> 884** (2026-09-24): Accurip 450 is ONE frame, not a pressing. The `accuraterip_offset` comment corrected.
    # **884 -> 889** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # +1 on 2026-09-26: the `Accurip 450` comment names both cyanrip wordings, `.16`'s and `.17`'s (round 27 lap 4), so it stays true of both.
    "parsers/rip_log.py": 890,  # +52: uniform_reread_baseline + the measured comment explaining why a fixed 3-pass floor cannot discriminate under -Z N (all 14 tracks flagged on a clean disc, 2026-09-22),
    # **903 -> 904 (2026-09-23)**: the read-offset hint names the real wizard path.
    # **904 -> 887** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    # **887 -> 928 (2026-09-24)**: the `Container owner` check, which names the
    # app or terminal the container belongs to. The lookup is in
    # `container_scope.py`; only the CheckResult mapping lives here, beside the
    # other checks, because a check that lived elsewhere would need to import
    # this module back.
    "preflight.py": 928,
    # **367 -> 370** (2026-09-24): Accurip 450 is ONE frame, not a pressing. Two docstrings stated the old mechanism as fact.
    "read_speed_ladder.py": 370,
    # **667 -> 673 on 2026-09-15**: `ArtifactEntry.missing`, so "the file is not
    # there" stops being something a reader has to infer from errno text.
    # **673 -> 690** (2026-09-24): `AlbumLoudnessCoverage`, report schema v26, what the album loudness rows were measured over.
    # **690 -> 712** (2026-09-24, #36): `ComponentInventory`, the one inventory type, and v27's `dependencies_measured_at`.
    # **712 -> 723** (2026-09-25, D14: control characters in the tag-only fields are replaced, and the report says so): `TagFixEntry` and `DiscBlock.tag_control_characters_replaced`.
    # **723 -> 727** (2026-09-25, D16, KDD-38: metadata may not forge a log signature): `DiscBlock.eac_log_signature_lines_defused`.
    "report_types.py": 727,
    # +23 on 2026-09-04: two SKIPs promoted to FAIL, with the reasoning that
    # separates them from the SKIP one branch up. "Nothing was given to look
    # at" and "a folder was given and holds no log" are different facts, and
    # the comment is what stops the next reader collapsing them again — §G is
    # ARCHIVAL and this exit code is its whole grade.
    # +3 (2026-09-05): now DELEGATES the "was the re-read exercised?" count
    # instead of computing it inline, so the manifest row and the graded verb
    # cannot answer one question with two keys.
    # **899 -> 940 (2026-09-24, the 0.6.55 acceptance bundle)**: a FAILED rip's empty parse
    # names the failure (`_rip_failure`) instead of calling it unexplained; it reads
    # the same report as `_rip_was_cancelled`, so it belongs beside it.
    # **940 -> 976** (2026-09-24): the paranoia row reads `READ` (the fork's 3.02x, not our 2.87x) and grades the bound per counter, which a sum could hide.
    # 976 -> 979 on 2026-09-25: errors="replace" on two probe pipes, and the argv
    # builder reached through composition.build_cyanrip_backend, not built here.
    "rig_check.py": 979,
    # **493 -> 496** (2026-09-24): Accurip 450 is ONE frame, not a pressing. The label is kept (a real sidecar holds it); the comment says so.
    "rip_addendum.py": 496,
    # **1216 -> 1287** (2026-09-25): `_grade_a_reported_completion`, round 21 §C. The
    # completion check graded OK off the boolean; it now reads the ripper's own
    # counts and error tally. It is a check of this registry, so it lives here.
    # **1287 -> 1301** (2026-09-26, the maintainer's quick run): the completion check compares the ripper's count with the tracks ASKED for (`completeness.tracks_expected`), not the disc total, so a deliberate partial rip is not graded as contradicting itself.
    "rip_audit.py": 1301,
    # **1404 -> 1405** (2026-09-24): Accurip 450 is ONE frame, not a pressing. `_describe_status` says 'a match on one frame only'.
    "rip_compare.py": 1405,
    "rip_files.py": 422,
    # **2302 -> 2402 on 2026-09-15**: `SUPERSEDED_GATE`, `OPTIONAL_ARTIFACTS`, and
    # the gate-vs-result check in `_issues`. It is the block that decides whether
    # this report tells the truth about what was verified, and the 2026-09-15 run
    # is why: five of eight rips said `"ran"` over a null result. The added lines
    # are mostly the account of how the existing guard could not fire — which is
    # the part a future reader has to have before they "simplify" it back.
    # +14: the two verification-issue codes promoted to named constants so the
    # acceptance verb can grade on them instead of copying the vocabulary,
    # **2416 -> 2430 (2026-09-24)**: schema v25, `settings.every_setting`. The key
    # sits in the settings builder it extends and the history paragraph sits above
    # `REPORT_SCHEMA_VERSION` with every other version's — the file's own rule is
    # that a schema change is explained where the number lives. The derivation is
    # in `user_settings.py`, so this is one call, not a list.
    # **2430 -> 2462 (2026-09-24, the 0.6.55 acceptance bundle)**: `RIP_DID_NOT_FINISH_GATE` and
    # `UNFINISHED_RIP_STATUSES` — a gate on a rip that never finished no longer
    # says "ran"; the vocabulary lives beside `SUPERSEDED_GATE`, its sibling.
    # **2462 -> 2479 (2026-09-24, round 26 lap 4)**: the offset-variant sentence uses the
    # parser's denominator rule, and a rip that never finished is not called read-unstable.
    # **2479 -> 2490** (2026-09-24): schema v26 `album_loudness_covers` plus its history note.
    # **2490 -> 2494** (2026-09-24, #36): schema v27's history note.
    # **2494 -> 2495** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # **2495 -> 2515** (2026-09-25, D14: control characters in the tag-only fields are replaced, and the report says so): schema v28 and the `tag_control_characters_replaced` issue.
    # **2515 -> 2528** (2026-09-25, D16, KDD-38: metadata may not forge a log signature): schema v29 and the `eac_log_signature_line_defused` issue.
    # **2528 -> 2546** (2026-09-26, the maintainer's quick run): a missing EAC-layout log is healthy when the rip's own settings turned it off (`_setting_was_on`).
    "rip_report.py": 2546,
    # +68 on 2026-09-04: round 15 split their P5 into P5 (121) and P5a (7,
    # "strings this document does NOT classify"). The addition is the two
    # decision lists — RETAINED_BEYOND_P5 gained five rows and P5A_NOT_RETAINED
    # is new — and almost all of it is the REASON each row went where it did.
    # P5a is explicitly not a safety claim ("two of the rows really are
    # failures" and they do not say which two), so a row without its reasoning
    # beside it is a row the next reader will move on a guess. This module is
    # the provenance record for that seam; splitting the reasons out of it
    # would leave the claim here and the evidence elsewhere.
    # 1051 -> 1090 at round 16. GENERATED DATA, and now genuinely generated:
    # `scripts/emit_ripper_inventory.py` rebuilds the MESSAGES block and the
    # test fixture from the fork's published contract in one parse. The file
    # has said "do not hand-edit, regenerate" since it was written and there was
    # no tool to regenerate it with, which is how it sat at round 6's row count
    # for five rounds. The growth is three more published rows plus the reasons
    # for the rows we retain past P5 — a line count is not a cohesion signal for
    # a table.
    "ripper_message_inventory.py": 1081,
    # 879 -> 886 (2026-09-06): delegating its absolute/traversal decision to
    # naming.path_escape_reasons while keeping its own user-facing wording.
    # **886 -> 896 on 2026-09-18**: the new field validated on its own
    # rather than folded in with its sibling — a path and a version are two
    # shapes, and one check loose enough for both checks neither properly.
    # **896 -> 922** (2026-09-24, #37 one home per setting): `field_error`, the ONE single-setting predicate the `set` verb and every save-as-you-change control share; it moved here from the runner so neither can restate it.
    # **922 -> 933** (2026-09-25, D14: control characters in the tag-only fields are replaced, and the report says so): `is_control_char`, the one definition both rules share.
    # **933 -> 947** (2026-09-25): `is_control_char` widened to C1 and U+2028/2029, with the reason; the one definition belongs beside the validators that use it.
    # **947 -> 1004** (2026-09-25, the property-test batches): three rules no longer crash (and so pass) on an unhashable choice, an unknown `~user`, or an over-long component; and `%%` no longer hides a segment from the reserved-name and trailing-dot checks.
    # **1004 -> 1024** (2026-09-25, D17, KDD-38): a crashing rule becomes a visible warning on its field instead of a silent pass, and the docstring says why it is not an error.
    "settings_validation.py": 1024,
    # 2026-09-25: errors="replace" on the text-mode pipe (a byte that was not UTF-8 raised and ended the read); tests/test_inbound_text.py sweeps it.
    "sleep_inhibit.py": 600,
    # **794 -> 824 on 2026-09-12** (+30): `RIG_PARENT_NAME` and `rig_parent()`,
    # the single deletable directory every rig artifact of ours now lives under,
    # on the maintainer's "stop polluting my home directory" instruction. The
    # constant is four lines; the rest is why -- that the timestamping was never
    # the problem, that the name deliberately mirrors the fork's `~/cyanrip-rig`
    # because one operator holds both rigs, and that `~/Music` is a library rather
    # than a workspace. Not extracted: a two-line helper in its own module would
    # be splitting to hit a number, and this module already owns every other
    # answer to "where does a session put things".
    # **824 -> 833 the same day** (+9): the bundle's no-Downloads fallback moved
    # from `$HOME` into the same one directory. It used to drop a tarball loose in
    # the home folder once per run on any machine without a Downloads folder --
    # the other half of the same instruction, found by sweeping for every
    # HOME-derived write rather than fixing the two loudest.
    # **833 -> 851 (2026-09-24)**: everything an acceptance run makes in ONE
    # session folder (maintainer: *"stop polluting my home folder, keep this all
    # contained to 1 folder"*). The layout gains `evidence`, `run_dir` and `rips`, and
    # the stager refuses a rip folder by name — the rule that keeps album artwork out.
    # **851 -> 861 (2026-09-24, the 0.6.55 acceptance bundle)**: `SessionLayout.rip_bundles`,
    # so each rip's own bundle lands in the one session folder too.
    "test_session.py": 861,
    "ui/dialogs/pending_installs.py": 419,
    # **new at 448** (2026-09-24, #37 one home per setting): still one window's layout. It gained the two update
    # channels (they live above the checks they steer), a Drive section holding
    # the read offset's status, Set up drive… and Diagnose drive access…, and
    # `set_locked`, the rip lock that reaches a window already open. Every action
    # still delegates to the window; nothing here decides anything.
    "ui/dialogs/setup_center.py": 448,
    # **454 -> 479 on 2026-09-12** (+25): `_transcript_save_default()`. The "Save
    # the transcript" dialog proposed `~/platterpus-transcript.txt`, i.e. a file
    # in the home directory. A save dialog only PROPOSES, which is why this was
    # the mildest of the three offenders and why it was still fixed: "we only
    # suggested it" is how a default becomes the thing everybody has. It asks the
    # same `downloads_dir`/`rig_parent` pair the evidence bundle asks, so the two
    # cannot disagree about where a deliverable belongs.
    # **479 -> 494 (2026-09-24)**: everything an acceptance run makes in ONE
    # session folder (maintainer: *"stop polluting my home folder, keep this all
    # contained to 1 folder"*). The one-shot hand-off of that folder to the next
    # run, and why it is one-shot.
    # **494 -> 509** (2026-09-24): `size_next_run`, the one-shot run-size hand-off beside `contain_next_run_in`.
    # **509 -> 548** (2026-09-24, #37 one home per setting): the console hosts its three test-script settings (in `script_settings_box.py`, split out so the console stays about running) and never replaces a typed batch when the startup script changes.
    # **548 -> 565** (2026-09-24, #37, caught by `tests/test_ui_conformance.py`): the intro and script settings scroll in a `FitScrollArea` so Run and the transcript keep their room on a Steam Deck at 150% text, where the new settings group squeezed three buttons to 12 px.
    # **565 -> 570 (2026-09-24)**: `refresh_settings`, the pass-through the window
    # calls so the console's own script options follow a script's `set`.
    "ui/dialogs/script_console.py": 570,
    # **319 -> 320** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "ui/disc_info_panel.py": 320,
    # **500 -> 577** (2026-09-24, #37 one home per setting): the read offset's ONE home now holds its Apply tick-box and the legacy ripper-config offset line, both moved from Settings, with the tooltip the offset's control had there.
    # **577 -> 583** (2026-09-24, #37, caught by `tests/test_ui_conformance.py`): the legacy ripper-config offset line shows only when a legacy offset exists; its "none set" was noise to most users and the line that clipped the intro on a short screen.
    # **583 -> 561** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    "ui/drive_setup_dialog.py": 561,
    # **341 -> 342** (2026-09-25, Critical rule #9: Qt has no "detach"): the teardown comment now says the dialog ABANDONS a running thread and keeps its reference, which reflowed one line.
    "ui/host_setup_dialog.py": 342,
    # **1558 -> 1572 on 2026-09-08**: the `Help → Install a cyanrip build…`
    # action, plus the paragraph saying why a SECOND ripper entry exists — the
    # update check reads the fork's release manifest and cannot offer a build the
    # fork never published, which is the abort that ended three overnight runs.
    # Menu wiring lives with the menu; the dialog is its own module.
    # **1572 -> 1579 on 2026-09-15**: initialising the START-time settings snapshot
    # and the post-rip pending/superseded ledger beside `_rip_generation`, which is
    # the field they exist to correct. Seven lines, and splitting them from their
    # sibling would be the drift.
    # **1579 -> 1578 on 2026-09-15**: one line, the `_last_derived_verify_result`
    # initialiser, struck with the eight sibling fields the album now owns.
    # Recorded because the ratchet's own non-triviality twin refuses HEADROOM:
    # a count left above the file's real length is room to grow unnoticed.
    # **1578 -> 1562 (2026-09-21): it SHRANK.** Six menu items became one, so the
    # ratchet comes down with it — a recorded count above the real length is
    # silent room to grow, which the sibling test refuses for exactly that reason.
    # **1562 -> 1566 (2026-09-23)**: the dependency-check comment corrected (it
    # named a Settings button as the only door), and Settings' OK applies edits.
    # **1566 -> 1601 (2026-09-24)**: the page scroll area. The window's own
    # central widget, so it belongs in the constructor that builds the widget
    # tree — and it must be built top-down there, every child created in its
    # final parent, because the other order segfaults under PySide6's garbage
    # collector (the comment saying so is most of the growth). Plus three lines
    # of Alt-key notes on the menu items whose letters moved, beside those items.
    # This number was exceeded by commit 641a884 and pushed without a green
    # suite; the check that would have caught it had been stopped.
    # **1601 -> 1609 (2026-09-24, the 0.6.55 acceptance bundle)**: the release picker and
    # Settings dialog are freed after use (four and two were left alive, hidden).
    # **1609 -> 1611** (2026-09-24): the acceptance menu item gets a no-argument slot, so `triggered`'s bool never lands in `size`.
    # **1611 -> 1616** (2026-09-24, #36): the per-instance dependency-check listener list, and About gets its recheck hook.
    # **1616 -> 1599** (2026-09-24, #37 one home per setting): down: Settings' opener moved to `main_window_settings.py`, and Diagnose drive access… left the Tools menu.
    # 1599 -> 1600 on 2026-09-25: a drive change forgets the release detail with the release id.
    # **1600 -> 1675** (2026-09-25, TASKS `stateful:answered-implies-answerable`, `stateful:table-immutable-during-rip`, `stateful:no-modal-during-rip`): a failed release FETCH now un-answers the disc in its own handler, a redundant lookup failing no longer overwrites the chosen release, and `_rip_holds_the_track_table` keeps every MusicBrainz answer off the table and out of a modal while a rip runs. These are the MusicBrainz slots, which live here.
    "ui/main_window.py": 1675,
    # **589 -> 686 (2026-09-21).** The floor check and its bounded deferral: a
    # dependency report that arrives inside another dialog's nested event loop
    # must wait rather than stack, and must not be dropped while it waits. Most
    # of the growth is the comment explaining the launch-time race, which is the
    # part a reader needs and the part a reviewer would otherwise have to
    # reconstruct from two other files.
    # **693 -> 722** (2026-09-24, #36): `_recheck_dependencies_for` and telling its listeners when the check lands.
    # **722 -> 723** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "ui/main_window_deps.py": 723,  # 692 -> 693 (2026-09-23): two dead menu paths corrected;  # +6: the write-through that puts a finished dependency probe where the Diagnostics dialog can read it,
    # **555 -> 561** (2026-09-24, #37 one home per setting): the wizard's Apply tick-box is wired, and a saved offset refreshes an open Setup & Updates.
    # **561 -> 543** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    # 543 -> 549 on 2026-09-25: an insert resets the old disc's identity before scanning (a probe glitch skipped the removal).
    "ui/main_window_drive.py": 549,
    # **508 -> 512** (2026-09-24): Accurip 450 is ONE frame, not a pressing. The status note's docstring said the audio was 'almost certainly correct'.
    # **512 -> 515** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # **515 -> 521** (2026-09-25, the property-test batches): `safe_path_segment` refuses `.`/`..` after the byte cap, and survives a lone surrogate.
    # +1 on 2026-09-26: the `Accurip 450` comment names both cyanrip wordings, `.16`'s and `.17`'s (round 27 lap 4), so it stays true of both.
    "ui/main_window_helpers.py": 522,
    # **1212 -> 1283 on 2026-09-08.** A precondition abort packed a
    # multi-hundred-megabyte archive and put up a folder prompt for a run that
    # touched no drive. The growth is the guard, the dialog that states the fix
    # instead of offering a folder, and the paragraphs recording why the
    # predicate errs toward BUILDING the archive — suppressing one that had
    # evidence costs an overnight disc pass. It belongs beside the bundle launch
    # it gates; the decision and the launch in separate files is how a guard
    # stops being read as part of the path it guards.
    # **1283 -> 1297 on 2026-09-18**: the suppression check keyed on the pair, with the measurement that in-place updates land on the byte-identical path.
    # **1297 -> 1423 (2026-09-21).** Two additions: `run_setup_wizard`, the one
    # chokepoint through which every `HostSetupDialog` now opens (the fix for two
    # concurrent installs into one container), and `open_setup_center`, which
    # opens the window that replaced six menu items. The queued split of this
    # file still stands and this is still not the commit for it: both additions
    # are about the dialogs this mixin already owns.
    # **1423 -> 1493 (2026-09-23)**: the user's settings are snapshotted when an
    # acceptance session is armed and restored on every exit, excluding the app's
    # own state. It lives here because every exit path it hooks is here.
    # **1493 -> 1509 (2026-09-24)**: the acceptance bundle's `SETTINGS.json`. It
    # is captured in the finish handler because that is the one point where both
    # snapshots exist — the user's, taken when the run was armed, and the run's,
    # which the restore overwrites a line later. The logic is in the pure
    # `user_settings.py`; what is here is the capture and the hand-off, and the
    # restore got shorter by delegating to the same module.
    # **1509 -> 1526 (2026-09-24)**: everything an acceptance run makes in ONE
    # session folder (maintainer: *"stop polluting my home folder, keep this all
    # contained to 1 folder"*). Pointing the rips at the session folder
    # for the run, handing the runner its folder, and reading the album roots
    # before the restore.
    # **1526 -> 1589** (2026-09-24): the run-size chooser, asked before anything starts, and its plumbing into the session.
    # **1589 -> 1602** (2026-09-24, #36): the bundle's `COMPONENTS.json` and the run size in its facts.
    # **1602 -> 1607** (2026-09-24, #37 one home per setting): Setup & Updates and the console are handed the window's single-setting writer and Diagnose drive access….
    # **1607 -> 1624** (2026-09-26, the maintainer's quick run): the end-of-run headline asks `RunReport.ok`, so a quick run's size-declined sections do not read as a stopped run.
    "ui/main_window_provision.py": 1624,
    # **4225 -> 4267 on 2026-09-10** (log-verification race, above):
    # `parse_rip_log_from_disk` extracted from the finish handler so the
    # acceptance script's log graders can read the artifact through the SAME
    # parse rather than a second one, plus the `abandon_log_wait()` release
    # in the shutdown path. The extraction is net-neutral in code and pays
    # for itself in the docstring; a copy of that parse in the ui-script
    # layer would have been the drift this file exists to prevent.
    # **4267 -> 4458 on 2026-09-15**: the post-rip supersede work — `emit_if_current`
    # (gating the emit rather than the work), `_seal_superseded_post_rip_work`, and
    # the settings/gates snapshot helpers. This is the THIRD raise of this file in a
    # month and the row in `TASKS.md` for splitting the post-rip chain out of the
    # window stands; it is not done here because a hardware re-run is waiting on
    # this fix, and a structural move under a release is how a correct fix ships
    # broken. The code is the smallest form of the fix, not a resting place.
    # **4458 -> 4480 on 2026-09-15 (same day, second raise, FOURTH this month)**:
    # twenty-two lines, and all of them are the comment on why the report flush
    # is unconditional — the 655 ms measured against the 750 ms debounce, and the
    # reasoning that a check which has just FINISHED is the one at risk, not one
    # still in flight. That comment is the whole defence against the early return
    # being put back by someone who reads the guard as an optimisation; a shorter
    # note would lose the number, which is the part that convinces.
    #
    # **The ratchet is doing its job and the answer is not another raise.** The
    # `TASKS.md` row for extracting the post-rip chain stands, and this run is
    # more evidence for it: both defects found on 2026-09-15 live in the seam
    # between "the current rip" and "the album that just finished", which is
    # exactly what a `PostRipChain` owning its own `(rip_dir, rip_log, settings,
    # report handle)` would make impossible to get wrong.
    #
    # **4480 -> 4678 on 2026-09-15 (+198), and the honest reading is that the
    # refactor above did NOT relieve this file.** The paragraph directly above
    # predicted the fix — *"a `PostRipChain` owning its own `(rip_dir, rip_log,
    # settings, report handle)`"* — and `ui/post_rip_record.py` is that object:
    # 24 per-album facts left the window for a 184-line module that owns them.
    # What stayed, and what grew, is the *routing*: opening a record at Start,
    # filling it at finish, looking one up by generation, writing a report from
    # one rather than from `self`, and the guard that refuses a late write into a
    # folder a newer rip has claimed. So the STATE moved and the PLUMBING did
    # not, which is half the job — and saying so here matters more than the
    # number, because a raise recorded as a win is how the next reader concludes
    # the extraction is done. It is not: the `TASKS.md` row stands, and what it
    # now asks for is narrower and more tractable than before — move the post-rip
    # CHAIN (the five-step daemon and the six launchers) out beside the record it
    # already populates.
    # **4678 -> 4696 (2026-09-21).** The bundle stamp no longer predicts the flush
    # it is about to perform; the outcome is appended from the `else:` branch so a
    # failed flush can never be reported as a successful one. Found by the fork in
    # our own evidence bundle — the stamp read twelve seconds before the
    # `generated_at` of the report it bundles.
    # **4696 -> 4710 (2026-09-24, the 0.6.55 acceptance bundle)**: the gates read the rip's
    # own outcome, and a rip's own bundle goes to the session folder while one runs.
    # **4710 -> 4717** (2026-09-24, #36): the rip report records when its dependency versions were measured.
    # **4717 -> 4715** (2026-09-24, the sweep that retired the old ripper's name): down: the old ripper's config reader, kill pattern or reference line was removed.
    # 4715 -> 4730 on 2026-09-25: _release_detail_for, the one check both the rip start and the report use.
    # **4730 -> 4739** (2026-09-25, D14: control characters in the tag-only fields are replaced, and the report says so): the finish record carries the fixes.
    # **4739 -> 4751** (2026-09-25, D16, KDD-38: metadata may not forge a log signature): the finish path records the rewritten lines after writing the log, so recording them can never cost the log.
    "ui/main_window_rip.py": 4751,
    # **392 -> 414 on 2026-09-15**: four declarations — the settings snapshot, the
    # gate inputs, and the two post-rip ledgers — with the measurement that made
    # them necessary. This file is the single source of truth for the shared
    # surface, so an undeclared attribute reachable only through `getattr` is the
    # hole it exists to close.
    # **414 -> 407 on 2026-09-15**: nine post-rip RESULT declarations struck. They
    # moved to `ui/post_rip_record.py`, where they are the album's rather than the
    # window's. The only ratchet entry this session that went DOWN.
    # **407 -> 427 (2026-09-21).** Seam declarations only — the cross-mixin
    # methods the consolidated window calls on `self`, plus the two blocker
    # predicates. This file growing is the type seam doing its job: an undeclared
    # cross-mixin call is a mypy error, which is how the wiring gets checked.
    # **427 -> 428** (2026-09-24, #36): the listener list's declaration.
    # **428 -> 441** (2026-09-24, #37 one home per setting): the seam declares SettingsMixin's methods and the open Setup & Updates window it refreshes.
    # **441 -> 446 (2026-09-24)**: `_script_console` declared beside
    # `_setup_center`, because SettingsMixin now re-renders the console too.
    "ui/main_window_shared.py": 446,
    # **953 -> 989 on 2026-09-08**: `_on_pick_ripper_build`, a thin caller that
    # opens the picker and hands the commit to `_begin_ripper_install` — the
    # install path already here. It belongs in this file precisely BECAUSE it is
    # thin: putting a one-`exec`-and-delegate method in its own module would
    # separate it from the install it delegates to, which is the split that makes
    # a second install route look reasonable later.
    # **989 -> 1019 (2026-09-21).** `_modal_floor_blocker` split out of
    # `_interruption_blocker`, which now delegates to it. Two questions were
    # sharing one answer — *"may I interrupt this person?"* and *"may I stack on
    # what is already on screen?"* — and the wide one would have dropped the
    # resolution of a missing required dependency because the window was not yet
    # visible.
    "ui/main_window_update.py": 1019,
    # **1658 -> 1659** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "ui/rip_progress.py": 1659,
    # **1303 -> 1304 on 2026-09-18**: one line: the new field preserved alongside its sibling, since Settings not modelling a field is exactly how it would get silently reset.
    # **1304 -> 1319 (2026-09-21).** Corrected the secure-re-read label and
    # tooltip, which called an AGREEMENT COUNT a ceiling, and the Picard checkbox,
    # which read as automatic when the only path to Picard is a dialog the user
    # opens. The growth is the comment recording where the wrong gloss came from
    # (our own dependency contract) so the next reader does not "correct" it back.
    # **1319 -> 1361 (2026-09-22).** Fourteen tooltips rewritten to the
    # maintainer's stated standard: a true/false setting names BOTH outcomes
    # ("on: X. off: Y."), a value setting names what the values mean and what
    # each produces. The old tooltips described the CONTROL ("verify the FLAC
    # files after ripping") rather than the CONSEQUENCE, so the answer to "what
    # happens if I leave this off?" was nowhere on screen. Growth is text, not
    # branching. Measured after `ruff format`, per this table's own correction.
    # **1361 -> 1372 (2026-09-22)** (+11): a tooltip for the Naming scheme
    # dropdown, which had none. It is the only control here that rewrites two
    # other fields, so it was the worst one to leave unexplained — and every
    # tooltip test in this repo started from the set of tooltips, which cannot
    # report an absence. The sweep now starts from the set of controls.
    # **1372 -> 1406 (2026-09-23)**: `apply_user_edits` — OK writes only what the
    # user changed, so a value saved while the dialog was open is not reverted.
    # Net of removing the two duplicate-door buttons.
    # **1406 -> 1382 (2026-09-24): it SHRANK.** `apply_user_edits` moved to
    # `user_settings.py`, the pure module the acceptance run and the rip report
    # now share, which paid for the theme-aware colour lines that had taken the
    # file to 1412.
    # **1382 -> 1381** (2026-09-24): shrank by one; recorded at its real length.
    # **1381 -> 1335** (2026-09-24, #37 one home per setting): down: seven controls moved to their homes, net of OK/Apply/Cancel/Restore Defaults.
    # **1335 -> 1336** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # **1336 -> 1337** (2026-09-25, D18: `%N`/`%M` work everywhere): the template tooltip lists `%N` and `%M`.
    "ui/settings_dialog.py": 1337,
    # **802 -> 832** (2026-09-25, TASKS `stateful:table-immutable-during-rip`): the belt, a locked table refuses a rewrite from code as well as an edit from the user, plus a corrected docstring.
    "ui/track_table.py": 832,
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
    # 3429 -> 3452. `expect-ripper-under-review` now accepts the agreed TEST
    # PIN as well as the reviewed one, and most of the growth is the comment
    # saying why: matching only PIN_UNDER_REVIEW would have failed the round-16
    # session at its first assertion, on the build both projects told the
    # operator to install. This module is still the split candidate TASKS.md
    # tracks; raised deliberately rather than split under a hardware deadline.
    # **3452 -> 3486 on 2026-09-08.** The `expect-ripper-under-review` failure
    # message now derives WHICH build to name and WHICH route can install it,
    # instead of hardcoding the reviewed pin and the in-app check. A real rig run
    # aborted at section A and was handed `--install-ripper a9aedf0` when the
    # round's agreed build is `ddc1e8c`, plus a route that cannot offer an
    # unpublished build at all. The growth is two derived branches and the
    # paragraphs recording why each exists — and it belongs in the verb, because
    # the message IS the verb's output and a failure message assembled elsewhere
    # is the split that let this one drift from the script's own header.
    # **3486 -> 3482 the same day: it SHRANK.** Replacing the inline
    # `FORK_TEST_PIN if … else PIN_UNDER_REVIEW` with a call to
    # `fork_source.pin_the_rig_should_install()` cost four lines, and the
    # ratchet's non-triviality twin refused the stale 3486 as unearned headroom
    # — correctly: a recorded count above the real one is that many lines the
    # ratchet would not notice. A ratchet may shrink, and this is what that
    # looks like.
    # **3482 -> 3557 on 2026-09-10** (log-verification race, above):
    # `_rip_log_from_disk`, which the three log-grading verbs now delegate
    # to. It ABSORBS the staleness and existence guards that were duplicated
    # across all three, so the verbs shrank; the growth is the one shared
    # reader plus the record of why grading the window's snapshot failed §I
    # of the 2026-09-09 run on a log that was correct the whole time.
    # **3557 -> 3580 on 2026-09-11** (the SECOND defect in the same verb, which
    # the entry above made reachable): `_do_expect_log_well_formed`'s track-block
    # floor is now graded against the completion footer instead of
    # unconditionally, because §I cancels during track 1 and a correct record
    # therefore carries zero completed blocks — it failed one on hardware. The
    # branch itself is five lines; the rest is the docstring's *Floors* paragraph,
    # which had to change because it asserted the old floor in prose and a
    # docstring that contradicts its own code is the defect this repo keeps
    # naming. Deliberately NOT extracted: a five-line predicate in its own module
    # would be splitting to hit a number, which the cohesion heuristic explicitly
    # is not. The long-form reasoning lives in the test, not here.
    # 3580 -> 3585 on 2026-09-14 (+5): round 18's token rename. Two call sites
    # swapped meaning (SKIPPED <-> BLOCKED) and each gained the comment saying WHICH
    # concept it now records. The lines are the explanation, not new behaviour — a
    # bare swap would have been a five-character diff that reads as a typo and
    # inverts a state's meaning in every transcript after it.
    # 3585 -> 3676 on 2026-09-14 (+91): round 18's tier scaffolding — two verb
    # handlers, the per-step prune decision, and the state they need. **The pure
    # half went to its own module** (`uiscript/tiers.py`, 97 lines): tier parsing
    # and the prune ledger are decisions, testable without a GUI, and leaving them
    # here would have added the same lines with none of that. What stays is the
    # part that genuinely belongs to the runner — dispatch, and the state a run
    # carries. Most of the +91 is the reasoning for why a pruned step is BLOCKED
    # and never SKIPPED, which is the one thing a later reader must not get wrong.
    # 3676 -> 3731 on 2026-09-14 (+55): tier 4's coercion at `_record`, the
    # `_STRUCTURAL_VERBS` constant both the prune exemption and the coercion read,
    # and `tier` clearing an inherited `needs`. **Deliberately here rather than in
    # `tiers.py`**: the coercion has to sit at the runner's single outcome
    # chokepoint or it is N verb handlers to forget, and `tiers.py` is pure by
    # design. Most of the +55 is the reason the sweep cannot prune and the reason
    # a new block inherits nothing — the edge the fork's §5.2 calls the only one
    # worth arguing about, which our own leftover state could have produced.
    # **3731 -> 3898 on 2026-09-15**: `_do_expect_derived_output` and the shared
    # `_rip_album_dir` reader. The verb is what makes acceptance sections K1 and K2
    # able to fail at all — both are graded ARCHIVAL and on 2026-09-15 both passed
    # over a folder containing none of the output they exist to prove. A handler
    # lives beside its siblings because `_execute` dispatches by name; moving one
    # out would be a second dispatch surface.
    # **3898 -> 3929 on 2026-09-17**: `expect-ripper-under-review` stops accepting
    # the reviewed pin when it is a different program from the round's test pin.
    # The branch is four lines; the rest is the measurement that forced it — a
    # 247-of-247 green acceptance session on a build that could not answer either
    # of the round's breaking changes, with this verb among the steps that passed.
    # The next reader to find "accept either" tempting needs the number, not the
    # rule.
    # **4045 -> 4011 (2026-09-24): it SHRANK.** Section A's accepted set is asked of
    # `fork_source.accepted_rig_builds`; the derivation and its history moved there.
    # **4011 -> 4029 (2026-09-24)**: everything an acceptance run makes in ONE
    # session folder (maintainer: *"stop polluting my home folder, keep this all
    # contained to 1 folder"*). `contain_in`: the run writes into the session
    # folder and builds no second bundle.
    # **4029 -> 4121 (2026-09-24, the 0.6.55 acceptance bundle)**: `expect-verification`
    # fails at once over a rip that did not finish (it waited 600 s), and
    # `screenshot` photographs only on-screen windows, main window first (the
    # headline picture was a hidden dialog at every step).
    # **4121 -> 4125**: the headline screenshot is chosen by the runner's own window
    # (identity), after the full suite showed a class-name match picking a leftover.
    # **4125 -> 4314** (2026-09-24): `run-size` (the dispatch check and its handler), `keep`, `set-drive-offset`, `expect-drive-offset` and the `(offset)` placeholder. Verb handlers live beside the other verb handlers; the pure halves are in `run_sizes.py` and `script.py`.
    # **4314 -> 4297** (2026-09-24, #37 one home per setting): down: the setting validator moved to `settings_validation.field_error`.
    # **4297 -> 4305 (2026-09-24)**: `set` calls the window's one
    # `_refresh_setting_views` after a change, so open windows follow it.
    # 4305 -> 4309 on 2026-09-25: a cyanrip step's recorded output is screened
    # (inbound_text, Critical rule #12), and why the expect-verbs copy stays raw.
    # 4309 -> 4398 on 2026-09-25: probe-ripper-wrapper moved onto a helper thread (_WrapperProbeJob); it ran on the GUI thread.
    "uiscript/runner.py": 4398,  # +116: _do_expect_verification, the assertion section F never had,
    # **318 -> 339** (2026-09-24): `(offset)` and the one preflight view of it, shared by the runner and the committed-script sweeps.
    # **339 -> 345** (2026-09-25): the passthrough sanitiser refuses every line break, via the shared definition.
    # **345 -> 348** (2026-09-25, the property-test batches): `raw_tail` is cut from the source text, so a quoted verb cannot corrupt it.
    "uiscript/script.py": 348,
    # +38 on 2026-09-04: the `expect-rip-complete` entry. This module IS the
    # closed vocabulary and its own docstring calls it the security boundary,
    # so a verb declared anywhere else would defeat the file. The comment is
    # most of the addition and stays with the entry it justifies.
    # +81 (2026-09-05): the three verb registrations for the handlers above.
    # Each carries its "why this verb exists" comment, which is the file's
    # established shape and the reason it is long.
    # **671 -> 713 on 2026-09-15**: the `expect-derived-output` entry. This table is
    # the security boundary — the parser refuses anything not in it — so a verb
    # cannot live anywhere else, and the growth is the comment explaining why
    # `expect-rip-complete` could not state this claim (cyanrip is always invoked
    # `-o flac`, so its log is identical whether our transcode ran or not).
    # **759 -> 801** (2026-09-24): four verbs, `run-size`, `keep`, `set-drive-offset` and `expect-drive-offset`. The table is the vocabulary's security boundary, so a verb is an entry here by design.
    "uiscript/verbs.py": 801,  # +46: the expect-verification declaration; verb help lives beside the verb so the console reference cannot drift from it,
    # 316 lines on arrival (2026-09-25). **One job, kept as one module**: decide
    # whether a release's attestation proves the download was built by our
    # release workflow. It is the only module that imports `sigstore` (Critical
    # rule #1), so the trust-root refresh lives beside the check that consumes it —
    # splitting them would make two sigstore-importing modules for one adapter. The
    # length is mostly the docstrings saying what the check does NOT prove.
    "update_attestation.py": 316,
    # **304 -> 358** (2026-09-25): step 3a, the build-attestation gate — fetch the
    # bundle capped, refuse when missing, oversized, refused or not checked, each
    # with its own message — plus starting the trust-root refresh before the
    # download. It belongs here: it is a step of this pipeline, between the checksum
    # and the swap, and must run on its `.part` file before `replace`.
    "update_install.py": 358,
    # **521 -> 530** (2026-09-24): Accurip 450 is ONE frame, not a pressing. The banner and the CTDB reconciliation say what matched.
    # **530 -> 531** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    "verdict.py": 531,
    # +24 on 2026-09-04: the secure-re-read branch that defers to the parser,
    # plus the comment recording the bundle measurement that produced it. The
    # line-classification loop is one cohesive read of the ripper's output.
    # **3309 -> 3413 on 2026-09-10** (log-verification race, above):
    # `_await_ripper_log` and `abandon_log_wait`. The wait belongs to the
    # worker because the worker is the only thing that knows whether its
    # read loop reached EOF — the fact the whole fix turns on — and it must
    # run off the GUI thread. The pure bounded wait itself is its own module
    # (`ripper_log_settle.py`); what is here is the budget, the announcement
    # and the interrupt.
    # **3413 -> 3463 (2026-09-24, the 0.6.55 acceptance bundle)**: a ripper killed by a signal
    # Platterpus did not send is explained (`ripper_exit`); the worker is the only
    # place that knows whether it sent one, so `_we_stopped_ripper` lives here.
    # **3463 -> 3462 (2026-09-24, round 26 lap 4)**: finished tracks are read through the parser, so its own copy of the pattern is gone.
    # **3462 -> 3464** (2026-09-24, the sweep that retired the old ripper's name): comments now name the old ripper by its role rather than its name, which reflowed a few lines.
    # 3464 -> 3490 on 2026-09-25: every pipe line is screened once (`_screen`), for
    # the log pane and the record, and the capture ends with what screening changed.
    # The screen itself lives in inbound_text; this is the wiring and its reasons.
    "workers/rip_worker.py": 3490,
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


# ---------------------------------------------------------------------------
# NO COMMIT MAY CARRY AN UNRESOLVED CONFLICT MARKER.
#
# Shipped to `main` on 2026-09-21 in PR #235: two `<<<<<<< HEAD` blocks sat in
# `CHANGELOG.md`, through nine green CI jobs and a squash merge. `lint` never saw
# them because ruff does not read Markdown; the `changelog` gate checks that
# `[Unreleased]` is empty and the tag's section exists, which both were.
#
# **The cause was a truncated command, not a hard problem.** The merge was run as
# `git merge origin/main 2>&1 | tail -6` — and the output of that command IS the
# list of files needing resolution. Two conflicts appeared in the visible tail
# and were fixed; `CHANGELOG.md` was above the cut. The verification that
# followed grepped the two known files rather than the tree, so it confirmed
# exactly the subset already known. `CLAUDE.md`'s *"a silent truncation reads as
# completeness"*, arriving through a pipe rather than through the product.
#
# A marker is unambiguous, costs nothing to detect, and no judgement is involved
# — which is precisely the kind of thing a person should never be the check for.
# ---------------------------------------------------------------------------

#: Text extensions worth scanning. Binary and vendored trees are skipped; the
#: point is the files a human edits and a merge can conflict in.
_CONFLICT_SCAN_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".cfg", ".sh", ".tsv"}
)

#: Directories that are not ours to police.
_CONFLICT_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", "__pycache__", ".venv", "node_modules", ".check-logs", ".pytest_cache"}
)


def test_no_file_carries_an_unresolved_conflict_marker() -> None:
    """A `<<<<<<<` / `>>>>>>>` pair anywhere in the tree fails the build.

    Anchored at column 0 and requiring the trailing space git writes, so prose
    *about* conflict markers — including this test and the comment above it —
    does not trip it. That exemption is the narrow kind: a real marker always
    starts the line and always carries a label after the space.
    """
    root = Path(__file__).resolve().parent.parent
    opener = re.compile(r"^<<<<<<< \S", re.MULTILINE)
    closer = re.compile(r"^>>>>>>> \S", re.MULTILINE)

    offenders: list[str] = []
    examined = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in _CONFLICT_SCAN_SUFFIXES:
            continue
        if any(part in _CONFLICT_SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        examined += 1
        if opener.search(text) or closer.search(text):
            rel = path.relative_to(root)
            first = next(
                (
                    i
                    for i, line in enumerate(text.splitlines(), 1)
                    if line.startswith(("<<<<<<< ", ">>>>>>> "))
                ),
                0,
            )
            offenders.append(f"{rel}:{first}")

    assert examined >= 300, (
        f"only {examined} file(s) scanned — the sweep has stopped finding the "
        "tree and would pass over anything"
    )
    assert not offenders, (
        "unresolved merge-conflict markers are committed in these files:\n  "
        + "\n  ".join(offenders)
    )


# --- Code conventions that were rules with no gate (2026-09-25) -------------
#
# Each of these is a convention CLAUDE.md states and nothing checked. Measured the
# day they were written, so each floor and allowlist below records a real count.


def _src_trees() -> list[tuple[str, ast.Module]]:
    return [
        (str(path.relative_to(SRC_ROOT)), ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(SRC_ROOT.rglob("*.py"))
    ]


def test_every_broad_except_says_why() -> None:
    """`except Exception` is sometimes right (a worker must always finish), and
    the codebase marks each one `# noqa: BLE001 — <reason>`. Eleven of 172 had
    the marker and no reason (2026-09-25), which leaves the next reader unable to
    tell a deliberate catch-all from a lazy one."""
    unexplained: list[str] = []
    handlers = 0
    for rel, tree in _src_trees():
        lines = (SRC_ROOT / rel).read_text(encoding="utf-8").splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler) or node.type is None:
                continue
            types = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            if not any(
                isinstance(t, ast.Name) and t.id in ("Exception", "BaseException")
                for t in types
            ):
                continue
            handlers += 1
            marker = re.search(r"noqa: BLE001(.*)$", lines[node.lineno - 1])
            if marker is None or not re.search(r"[A-Za-z]{3,}", marker.group(1)):
                unexplained.append(f"{rel}:{node.lineno}")
    assert handlers >= 150, f"only {handlers} broad handler(s) found; the scan is blind"
    assert not unexplained, (
        "a broad except must say why it is broad, on its own line "
        "(`# noqa: BLE001 — <reason>`):\n  " + "\n  ".join(unexplained)
    )


#: Modules allowed to `print`, each with the reason. Everything else logs.
#: **A ratchet: it may shrink, never grow.**
_PRINT_ALLOWED: Final[dict[str, str]] = {
    "app.py": "the command-line flags (--version, --doctor, --rig-check…) write to the terminal",
    "cli_compare.py": "the --compare command writes its table to the terminal",
    "rip_audit.py": "the --audit command writes its report to the terminal",
}


def test_print_is_used_only_by_command_line_output() -> None:
    """ "Log with the logging module, not print" (Code conventions). A print in a
    GUI path goes nowhere a bug report can see."""
    printing: dict[str, int] = {}
    for rel, tree in _src_trees():
        count = sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        )
        if count:
            printing[rel] = count
    assert sum(printing.values()) >= 20, printing  # floor: 47 measured
    stray = sorted(set(printing) - set(_PRINT_ALLOWED))
    assert not stray, f"print() outside a command-line module (log instead): {stray}"
    stale = sorted(set(_PRINT_ALLOWED) - set(printing))
    assert not stale, f"allowlisted but no longer printing; remove them: {stale}"


#: `setattr` on something other than `self`, each a data write onto an instance
#: whose field name is data. **A ratchet: it may shrink, never grow.**
_SETATTR_ALLOWED: Final[dict[str, str]] = {
    "logging_setup.py": "records the handlers on the root logger so a later call finds them",
    "ui/main_window_rip.py": "writes named fields onto the post-rip record",
    "uiscript/runner.py": "a script's `set` installs a validated Config on the window",
    "user_settings.py": "applies named values to a copy of the Config dataclass",
}


def test_no_clever_metaprogramming() -> None:
    """ "No clever metaprogramming" (Code conventions): no exec/eval, no dynamic
    classes, no metaclasses, no module __getattr__, no computed imports, and
    `setattr` only where a named field is written onto a data instance."""
    forbidden: list[str] = []
    setattr_files: set[str] = set()
    for rel, tree in _src_trees():
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in (
                "__getattr__",
                "__dir__",
            ):
                forbidden.append(f"{rel}:{node.lineno} module-level {node.name}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                k.arg == "metaclass" for k in node.keywords
            ):
                forbidden.append(f"{rel}:{node.lineno} metaclass")
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if isinstance(func, ast.Name) and name in ("exec", "eval", "__import__"):
                forbidden.append(f"{rel}:{node.lineno} {name}()")
            if isinstance(func, ast.Name) and name == "type" and len(node.args) == 3:
                forbidden.append(f"{rel}:{node.lineno} type() building a class")
            if (
                name == "import_module"
                and node.args
                and not isinstance(node.args[0], ast.Constant)
            ):
                forbidden.append(f"{rel}:{node.lineno} computed import")
            if isinstance(func, ast.Name) and name == "setattr":
                target = node.args[0] if node.args else None
                if not (isinstance(target, ast.Name) and target.id == "self"):
                    setattr_files.add(rel)
    assert not forbidden, "metaprogramming the conventions forbid:\n  " + "\n  ".join(
        forbidden
    )
    assert setattr_files, (
        "no setattr found at all; the scan is blind"
    )  # 7 sites measured
    grown = sorted(setattr_files - set(_SETATTR_ALLOWED))
    assert not grown, f"setattr on a non-self object in a new module: {grown}"
    stale = sorted(set(_SETATTR_ALLOWED) - setattr_files)
    assert not stale, f"allowlisted setattr modules that no longer use it: {stale}"


def test_the_metaprogramming_gate_fires_on_what_it_forbids() -> None:
    sample = ast.parse(
        "exec('x')\nKlass = type('K', (), {})\nclass M(metaclass=Meta): pass\n"
        "import importlib\nimportlib.import_module(name)\n"
    )
    names = [
        n.func.id if isinstance(n.func, ast.Name) else n.func.attr
        for n in ast.walk(sample)
        if isinstance(n, ast.Call)
    ]
    assert {"exec", "type", "import_module"} <= set(names)


def test_output_parsers_do_not_split_tool_output_into_columns() -> None:
    """ "Named-group regexes, not column-index splits" (Code conventions), for the
    packages that read external tools: `parsers/` and `adapters/`.

    Scoped deliberately and said so: a whitespace `.split()[N]` there reads a
    COLUMN of a tool's output, which moves when the tool's layout does. A split at
    a named separator (`.split(":", 1)[1]`, `.rsplit("}", 1)[-1]`) is not column
    indexing and is allowed. None existed on 2026-09-25; this keeps it so.
    """
    columns: list[str] = []
    examined = 0
    for rel, tree in _src_trees():
        if not rel.startswith(("parsers/", "adapters/")):
            continue
        examined += 1
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr in ("split", "rsplit")
            ):
                continue
            call = node.value
            whitespace = not call.args or (
                isinstance(call.args[0], ast.Constant) and call.args[0].value is None
            )
            if whitespace:
                columns.append(f"{rel}:{node.lineno}: {ast.unparse(node)[:60]}")
    assert examined >= 15, f"only {examined} parser/adapter module(s) examined"
    assert not columns, (
        "a whitespace column split of tool output; use a named-group regex:\n  "
        + "\n  ".join(columns)
    )


def test_the_appimage_is_built_by_python_appimage_only() -> None:
    """Critical rule #2: `python-appimage` is the builder, and `appimage-builder`
    needs the maintainer's sign-off. Nothing asserted which tool the build ran."""
    script = (REPO_ROOT / "build" / "build_appimage.sh").read_text(encoding="utf-8")
    code = [ln for ln in script.splitlines() if not ln.lstrip().startswith("#")]
    assert any("python_appimage build app" in ln for ln in code), (
        "build_appimage.sh no longer invokes python-appimage"
    )
    for workflow in ("release.yml", "appimage.yml"):
        text = (REPO_ROOT / ".github" / "workflows" / workflow).read_text(
            encoding="utf-8"
        )
        assert "bash build/build_appimage.sh" in text, (
            f"{workflow} does not use the recipe"
        )
    users = [
        str(path.relative_to(REPO_ROOT))
        for folder in ("build", ".github", "scripts")
        for path in (REPO_ROOT / folder).rglob("*")
        if path.is_file()
        and path.suffix in {".sh", ".yml", ".yaml", ".py", ".txt", ".toml"}
        and re.search(
            r"appimage[-_]builder", path.read_text(encoding="utf-8", errors="replace")
        )
    ]
    assert not users, f"appimage-builder is used without sign-off: {users}"


#: Modules that run a container tool as a PROGRAM, each with its reason
#: (Critical rule #3: the GUI rips through the host-exported ripper, never by
#: entering the container itself). **A ratchet: it may shrink, never grow.**
_CONTAINER_TOOL_ALLOWED: Final[dict[str, str]] = {
    "drive_control.py": "rule #3's one scoped exception: force-stopping a runaway reader on cancel",
    "deps/fork_source.py": "builds the pinned fork inside the container and exports it (the setup wizard and --install-ripper)",
    "deps/host_setup.py": "creates the `ripping` container during setup",
    "deps/host_teardown.py": "removes what setup created, on uninstall",
    "deps/ripper_wrapper_probe.py": "times `distrobox-enter -- true` to diagnose a wrapper that hangs",
}

#: A string constant that IS a container tool (optionally a path to one), as it
#: would appear as argv[0]. Prose that merely mentions Distrobox does not match.
_CONTAINER_TOOL: Final[re.Pattern[str]] = re.compile(
    r"^(?:\S*/)?(?:distrobox(?:-enter|-export|-create|-rm|-stop)?|podman|docker|toolbox)$"
)

#: The modules on the RIP path. Named so that allowlisting one of them is a
#: separate, visible failure rather than an edit to the dict above.
_RIP_PATH: Final[frozenset[str]] = frozenset(
    {
        "adapters/cyanrip_backend.py",
        "composition.py",
        "rig_check.py",
        "uiscript/runner.py",
        "workers/rip_worker.py",
    }
)


def test_only_setup_and_the_scoped_exception_enter_the_container() -> None:
    """Critical rule #3, which no test enforced (TASKS `rule-3.routing`)."""
    running: set[str] = set()
    for rel, tree in _src_trees():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _CONTAINER_TOOL.match(node.value.strip())
            ):
                running.add(rel)
    assert len(running) >= 4, f"only {sorted(running)} found; the scan is blind"
    assert not (set(_CONTAINER_TOOL_ALLOWED) & _RIP_PATH), (
        "a rip-path module was allowlisted to enter the container"
    )
    stray = sorted(running - set(_CONTAINER_TOOL_ALLOWED))
    assert not stray, (
        "these modules run a container tool directly; the rip path goes through "
        f"the host-exported ~/.local/bin/cyanrip (Critical rule #3): {stray}"
    )
    stale = sorted(set(_CONTAINER_TOOL_ALLOWED) - running)
    assert not stale, f"allowlisted but no longer running one; remove them: {stale}"
