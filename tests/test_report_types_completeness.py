"""``report_types.py`` must actually describe what ``rip_report`` writes.

**Why this exists.** `report_types.py`'s own docstring says it is the *"single
source of truth for the structure `rip_report` WRITES and `rip_compare` READS"*.
It was missing **13 of 28** keys of the `rip` block — eight of them shipped in
schema v13/v14, months before this test. Nothing noticed, because a `TypedDict`
that under-describes a dict literal is not a type error: the emit site is not
annotated as the `TypedDict`, so mypy has nothing to compare.

That makes it the third expired completeness promise found in one sweep
(`docs/testing.md` §5.af), and the first one in *code* rather than in docs. Same
fix: derive the expected set from the thing being described, and turn the promise
into a gate. `CLAUDE.md` rule 10 is the standing version — *no untyped dict as a
pseudo-struct* — and a struct that describes half the dict is the same defect with
better manners.

**Read out of the AST, not by importing and calling.** Building a real report needs
a parsed rip log, a config and a folder; the question here is purely structural, so
the keys come from the source. That also means a key added inside an `if` branch is
still seen, which a runtime call over one fixture would miss.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _REPO_ROOT / "src" / "platterpus" / "rip_report.py"
_TYPES = _REPO_ROOT / "src" / "platterpus" / "report_types.py"

#: Block name → a key that uniquely identifies its dict literal in `rip_report`.
#: Anchored on a key rather than a line number so inserting a field cannot make
#: the test read the wrong literal and pass for the wrong reason.
_BLOCKS: dict[str, str] = {
    "RipBlock": "extraction_engine",
    "OutcomeBlock": "failure_hint",
    "TimingBlock": "elapsed_human",
}


def _emitted_keys(anchor: str) -> list[str]:
    """The string keys of the dict literal in ``rip_report`` containing ``anchor``.

    The *last* match wins: `build_report` assembles the block once, and an earlier
    partial literal mentioning the same key would otherwise shadow it.
    """
    tree = ast.parse(_REPORT.read_text(encoding="utf-8"))
    found: list[str] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [
            k.value
            for k in node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        ]
        if anchor in keys:
            found = keys
    assert found is not None, (
        f"no dict literal in rip_report.py contains {anchor!r} — the anchor has "
        "moved, and this test is now measuring nothing"
    )
    return found


def _declared_keys(class_name: str) -> list[str]:
    """The annotated field names of a ``TypedDict`` in ``report_types``."""
    tree = ast.parse(_TYPES.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ]
    raise AssertionError(f"report_types.py has no class {class_name}")


def test_every_emitted_key_is_declared() -> None:
    """The finding this file was written for, swept over all three blocks."""
    problems: list[str] = []
    total_checked = 0
    for class_name, anchor in _BLOCKS.items():
        emitted = _emitted_keys(anchor)
        declared = set(_declared_keys(class_name))
        total_checked += len(emitted)
        missing = [k for k in emitted if k not in declared]
        if missing:
            problems.append(f"{class_name} does not declare: {', '.join(missing)}")
    assert not problems, (
        "report_types.py calls itself the single source of truth for what "
        "rip_report writes, and it is incomplete — " + "; ".join(problems)
    )
    # Floor: this must not pass by finding nothing. 30 is comfortably below the
    # real count across three blocks and far above "the AST walk broke".
    assert total_checked >= 30, (
        f"only {total_checked} emitted keys found across {len(_BLOCKS)} blocks — "
        "has an anchor moved, or the literal been refactored?"
    )


def test_no_declared_key_is_unemitted() -> None:
    """The converse: a field described and never written is a promise to a consumer.

    `rip_compare` reads these types. A key declared here and absent from every
    report makes a downstream `.get()` look safe when it can only ever be `None`.
    """
    problems: list[str] = []
    for class_name, anchor in _BLOCKS.items():
        emitted = set(_emitted_keys(anchor))
        declared = _declared_keys(class_name)
        # `NotRequired` fields are conditional by construction — `TimingBlock`'s
        # `disc_seconds` is only written when a disc duration is known — so they
        # are legitimately absent from the unconditional literal.
        source = _TYPES.read_text(encoding="utf-8")
        extra = [
            k
            for k in declared
            if k not in emitted and f"{k}: NotRequired" not in source
        ]
        if extra:
            problems.append(f"{class_name} declares but nothing writes: {extra}")
    assert not problems, "; ".join(problems)


def test_the_handshake_approval_fields_are_in_the_rip_block() -> None:
    """The new fields specifically, named so a rename cannot silently drop them.

    These are the maintainer's *"verify at the time of rip as well so we can
    confirm"*, and a report that stopped carrying them would still validate as a
    report — which is exactly why they get their own assertion rather than relying
    on the sweep above.
    """
    emitted = set(_emitted_keys("extraction_engine"))
    declared = set(_declared_keys("RipBlock"))
    required = {
        "ripper_handshake_approval",
        "ripper_handshake_approval_detail",
        "ripper_handshake_approved_build",
        "ripper_handshake_approved_for_platterpus",
        "ripper_handshake_approved_by_round",
    }
    assert required <= emitted, f"not written: {sorted(required - emitted)}"
    assert required <= declared, f"not declared: {sorted(required - declared)}"
