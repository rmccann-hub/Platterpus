"""An attribute the product READS but nothing ever WRITES.

**Two shipped instances, found the same day, with identical semantics and
different syntax — which is why this is a sweep and not two fixes.**

1. ``ui/main_window_update.py`` read ``self._observed_ripper_banner`` through
   ``getattr(..., "")``. The attribute was assigned **nowhere** in ``src/`` — only
   in a test, which is exactly what made it look wired. Because the read could not
   raise, ``_installed_ripper_commit()`` returned ``None`` on every call and the
   ripper update check silently compared the fork's manifest against the
   build-time constant ``FORK_PIN`` instead of the installed binary. It told an
   operator running ``c4d1a00`` they had *"release 11 (ddf7ac3)"* — and kept
   saying it immediately after every successful install.

2. ``uiscript/runner.py`` listed ``"_cache_defeat_value"`` among the disc-panel
   fields a ``snapshot`` records. The panel's attribute is ``_cache_value``. So
   **every scripted rig transcript silently omitted the cache-defeat verdict**
   while the GUI displayed it correctly — a hole in the very artifact we upload as
   handshake evidence.

**Why the syntax difference matters.** A grep for ``getattr(self, "`` finds the
first and misses the second entirely: instance 2's name is an element of a tuple
the code loops over, not an argument at a call site. A detector shaped like the
first bug would have reported the tree clean. So this collects **every
private-attribute-shaped string literal** in the product and asks the same
question of each.

**The failure mode this class shares** is that nothing raises. ``getattr`` with a
default, and a loop that skips what it cannot find, both degrade to silence — so
the feature is simply absent and every surface around it looks healthy. That is
worse than a crash, which is why it needs a mechanical sweep rather than review.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
SRC: Path = REPO_ROOT / "src" / "platterpus"

#: A private attribute name as this codebase spells them: leading underscore,
#: lowercase, no dunders (``__init__`` and friends are Python's, not ours).
_PRIVATE_ATTR = re.compile(r"^_[a-z][a-z0-9_]*$")

#: Names that are read but deliberately never assigned by us, each with a reason.
#: **A ratchet: it may shrink, never grow.** An entry here is a promise that the
#: name belongs to something outside our control.
_ALLOWED_UNASSIGNED: dict[str, str] = {
    "_do_": (
        "a PREFIX, not a name: uiscript/runner.py builds handler names as "
        'f"_do_{verb}". The handlers it resolves to are real defs and are in the '
        "denominator; only the fragment is not."
    ),
}


def _source_files() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


def _assigned_names(files: list[Path]) -> set[str]:
    """Every private name the product actually WRITES, by any route.

    Deliberately generous — this is the *denominator*, and a name missed here
    becomes a false positive that wastes a maintainer's afternoon. Covers plain
    assignment, annotated declaration (``_x: T`` with no value, which is how the
    window declares its thread slots), ``setattr`` with a literal name, and
    ``for``/``with`` bindings.
    """
    assigned: set[str] = set()
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # A METHOD is an attribute too. Omitting these was the first version's
            # bug and it reported nine healthy names dead — the uiscript runner
            # dispatches to handlers by string (`_on_start`, `_on_rip_cancel`),
            # which is the same dynamic-reference pattern this sweep polices, only
            # correct. A detector whose denominator is too small is not stricter,
            # it is wrong, and it burns the maintainer's trust on the first run.
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                assigned.add(node.name)
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign | ast.AugAssign):
                targets = [node.target]
            elif isinstance(node, ast.For):
                targets = [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Attribute):
                        assigned.add(sub.attr)
                    elif isinstance(sub, ast.Name):
                        assigned.add(sub.id)
            # An attribute name HELD IN A CONSTANT is a declaration, not a guess:
            # `_CONFIGURED_ATTR: str = "_platterpus_configured"`, then
            # `setattr(root, _CONFIGURED_ATTR, True)`. The setattr carries a
            # variable, so the literal-argument branch below cannot see it — and
            # without this the sweep called four correct sentinels dead. They are
            # markers stamped on FOREIGN objects (the root logger, a QWidget),
            # which is the one case where nothing in our tree can ever "assign"
            # them in the ordinary sense.
            value = getattr(node, "value", None)
            if (
                isinstance(node, ast.Assign | ast.AnnAssign)
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and _PRIVATE_ATTR.match(value.value)
            ):
                assigned.add(value.value)
            # `setattr(obj, "_x", value)` — how the window assigns thread slots
            # in a loop. A sweep that missed this would report real code dead.
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                assigned.add(node.args[1].value)
    return assigned


def _mapping_keys(tree: ast.AST) -> set[int]:
    """``id()`` of every string constant used as a MAPPING KEY: ``d["_x"]`` or
    ``d.get("_x")``.

    Those name a key in somebody else's data, not an attribute of ours, so they
    cannot be the bug this sweep hunts. Taught 2026-09-25, when the in-toto
    statement's ``_type`` key (``update_attestation.py``) tripped the sweep: the
    key is fixed by the in-toto spec, and the allowlist is a ratchet that may not
    grow, so the right move was to teach the sweep the difference rather than
    exempt the subject. **Narrow on purpose:** only a subscript index and the
    first argument of a ``.get(...)`` call. A ``getattr`` argument and a tuple
    element — the two shapes that shipped — are still collected, and the self-test
    below proves it.
    """
    keys: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            keys.add(id(node.slice))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            keys.add(id(node.args[0]))
    return keys


def _private_literals(tree: ast.AST) -> dict[str, int]:
    """``{name: line}`` for every private-attribute-shaped string in ``tree``
    that is not a mapping key."""
    keys = _mapping_keys(tree)
    found: dict[str, int] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _PRIVATE_ATTR.match(node.value)
            and id(node) not in keys
        ):
            found.setdefault(node.value, node.lineno)
    return found


def _read_names(files: list[Path]) -> dict[str, tuple[Path, int]]:
    """Every private-attribute-shaped name the product mentions as a STRING.

    A string is how both real defects were spelled: one as a ``getattr``
    argument, one as a tuple element. Attribute access written as real syntax
    (``self._x``) cannot have this bug — it raises.
    """
    reads: dict[str, tuple[Path, int]] = {}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for name, line in _private_literals(tree).items():
            reads.setdefault(name, (path, line))
    return reads


def test_no_private_attribute_is_read_but_never_written() -> None:
    """The sweep. Both shipped defects are of exactly this shape."""
    files = _source_files()
    assert len(files) >= 100, (
        f"only {len(files)} source files found — the glob is wrong and this sweep "
        "has gone vacuous."
    )

    assigned = _assigned_names(files)
    assert len(assigned) >= 500, (
        f"only {len(assigned)} assigned names found — the denominator collapsed, "
        "which would report the whole codebase dead."
    )

    reads = _read_names(files)
    assert len(reads) >= 5, (
        f"only {len(reads)} private-attribute string literals found ({sorted(reads)})"
        " — the collector is not seeing the population it is meant to police."
    )

    orphans = {
        name: where
        for name, where in reads.items()
        if name not in assigned and name not in _ALLOWED_UNASSIGNED
    }
    assert not orphans, (
        "these names are referenced as attribute strings but assigned NOWHERE in "
        "src/ — the read degrades to silence and the feature is simply absent:\n  "
        + "\n  ".join(
            f"{name!r} at {path.relative_to(REPO_ROOT)}:{line}"
            for name, (path, line) in sorted(orphans.items())
        )
    )


def test_the_sweep_catches_both_defects_it_was_written_for() -> None:
    """Non-triviality, measured rather than argued.

    A detector verified only against a fixed tree cannot be told apart from one
    that matches nothing. So both real defects are reconstructed here and the
    sweep must find each — including the tuple-element spelling, which a
    ``getattr``-shaped detector misses entirely.
    """
    assigned = {"_cache_value", "_rip_thread"}

    # Defect 1's shape: a getattr argument.
    tree1 = ast.parse(
        'banner = str(getattr(self, "_observed_ripper_banner", "") or "")'
    )
    # Defect 2's shape: a tuple element in a loop. Same semantics, different syntax.
    tree2 = ast.parse('FIELDS = (("_cache_defeat_value", "cache defeat"),)')

    for label, tree, wanted in (
        ("getattr argument", tree1, "_observed_ripper_banner"),
        ("tuple element", tree2, "_cache_defeat_value"),
    ):
        # The collector the sweep itself uses, not a copy of it.
        found = _private_literals(tree)
        assert wanted in found, f"the collector misses the {label} spelling"
        assert wanted not in assigned, f"{label}: fixture is wrong, not the sweep"


def test_a_mapping_key_is_not_an_attribute_read() -> None:
    """The one exclusion, and its limit: a key in data is skipped; the same name
    as a getattr argument in the same file is still caught."""
    tree = ast.parse(
        'a = statement.get("_type")\n'
        'b = statement["_type"]\n'
        'c = getattr(obj, "_type", None)\n'
    )
    found = _private_literals(tree)
    assert found == {"_type": 3}, found
    assert _private_literals(ast.parse('x = d.get("_only_a_key")')) == {}


def test_every_allowlist_entry_is_still_needed() -> None:
    """An exemption that no longer applies must be deleted, not left to rot.

    Same converse check the handshake `--check` allowlist carries: an entry that
    silently excuses nothing while implying it excuses something is worse than no
    entry at all.
    """
    files = _source_files()
    reads = _read_names(files)
    stale = sorted(name for name in _ALLOWED_UNASSIGNED if name not in reads)
    assert not stale, (
        f"these allowlist entries name attributes nothing reads any more: {stale}. "
        "Delete them — the ratchet may shrink, and should."
    )
