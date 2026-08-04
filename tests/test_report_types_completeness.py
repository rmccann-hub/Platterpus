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
import json
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


# --- The sweep (2026-08-04) -------------------------------------------------
#
# The three anchored blocks above were the finding; three anchors are not the
# codebase. A hand-listed `_BLOCKS` is a completeness promise of exactly the kind
# CLAUDE.md says decays invisibly — it is only ever wrong by *omission*, and nobody
# reviews a dict for what is not in it. Measured when this sweep was added:
# `RipReport` was missing `completeness` and `artifacts` (four schema versions
# late), `TrackBlock` was missing all four pre-gap provenance keys, `DiscBlock` was
# missing the three `medium_*` keys — including `medium_undetermined`, the only
# field that says a rip's titles may belong to another disc — and `TimingBlock` was
# missing `realtime_multiplier_basis`, which changes what the ratio is measured
# against. None of it was a type error, for the reason this module's docstring gives.
#
# So: derive the expected set from a REAL report, built at runtime, and require a
# declared field for every key in every nested block. That cannot be wrong by
# omission, because the report is the thing being described.


def _real_log() -> object:
    """A parsed rip log with the fields every block needs, so nothing is null."""
    from platterpus.parsers.rip_log import (
        AccurateRipResult,
        RipLog,
        RippingInfo,
        TrackResult,
    )

    return RipLog(
        log_creator="cyanrip 0.9.4-rc1 (platterpus-fork-g0000000)",
        ripping_info=RippingInfo(drive="PIONEER BD-RW BDR-209D"),
        tracks=(
            TrackResult(
                number=1,
                copy_crc="AA",
                accuraterip_v2=AccurateRipResult(
                    version=2, result="accurately ripped", confidence=200
                ),
            ),
        ),
    )


def _real_report_kwargs() -> dict:
    """The keyword arguments that populate every optional block."""
    from platterpus.rip_report import build_timing

    return {
        "timing": build_timing(100, disc_seconds=50),
        "disc": {
            "unknown": False,
            "musicbrainz_release_id": "mbid",
            "catalog_number": "CAT",
            "barcode": "BAR",
            "label": "LBL",
            "medium_basis": "track count",
            "medium_detail": "disc 1 of 2",
            "medium_undetermined": False,
        },
        "disc_track_total": 1,
    }


def _real_report() -> dict:
    """A report with every block populated, built through the real builder.

    Runtime rather than AST here, deliberately: the question is *"does the type
    describe what a consumer will actually receive"*, and only a built report
    answers that — an AST walk cannot see a key added by `_enrich_timing` after the
    literal is constructed, which is exactly how `realtime_multiplier_basis` hid.

    **For top-level keys this is still not enough** — the *writer* adds one more. See
    :func:`test_the_report_declares_every_section_the_WRITER_writes`.
    """
    from platterpus.rip_report import build_report

    return build_report(_real_log(), **_real_report_kwargs())


#: Report key → the `TypedDict` that must describe it. Derived from `RipReport`'s own
#: annotations below, so this is a *rendering* of the type rather than a second list
#: that can disagree with it.
def _nested_block_types() -> dict[str, str]:
    """``report key → TypedDict name`` for every dict-valued section of `RipReport`.

    Read off `RipReport`'s annotations, so adding a block to the report *and* the
    type automatically brings it under this sweep — and adding it to the report
    alone fails :func:`test_the_report_declares_every_section_it_writes` first.
    """
    tree = ast.parse(_TYPES.read_text(encoding="utf-8"))
    known = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == "RipReport"):
            continue
        for stmt in node.body:
            if not (
                isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ):
                continue
            # `X`, `X | None` — take the first name-ish token that is a known class.
            names = [
                n.id
                for n in ast.walk(stmt.annotation)
                if isinstance(n, ast.Name) and n.id in known
            ]
            if names:
                out[stmt.target.id] = names[0]
    return out


def test_the_report_declares_every_section_the_WRITER_writes(tmp_path: Path) -> None:
    """The sweep must read a **written file**, not the builder's return value.

    Found by a real rig artifact (2026-08-04): the uploaded `.platterpus.json` had
    **32** top-level keys where `build_report` produces 31. The extra one was
    `self_check`, which `write_report` adds *after* `_build` (one of its checks stats
    the audio files, and `_build` is pure by contract). It was undeclared, and the
    sweep written the same day could not see it — because it inspected the builder,
    which is my stand-in, not the artifact a consumer actually opens.

    *"What does my stand-in do that the real thing does not?"* — it stops one function
    early. So this reads the file back off disk.
    """
    from platterpus.rip_report import write_report

    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    written = write_report(_real_log(), album / "rip.log", **_real_report_kwargs())
    assert written is not None and written.exists(), "no report was written"
    report = json.loads(written.read_text(encoding="utf-8"))
    # FLOOR: the writer-added block must actually be present, or this test has
    # quietly become the builder test it was written to replace.
    assert "self_check" in report, (
        "the written report carries no `self_check` — the writer's post-build step "
        "did not run, so this sweep is measuring the builder again"
    )
    declared = set(_declared_keys("RipReport"))
    emitted = set(report)
    assert len(emitted) >= 25, f"only {len(emitted)} top-level keys — builder broken?"
    assert not emitted - declared, (
        "RipReport does not declare section(s) the report writes: "
        f"{sorted(emitted - declared)}"
    )
    assert not declared - emitted, (
        "RipReport declares section(s) no report writes (a promise to a consumer "
        f"that can only ever be None): {sorted(declared - emitted)}"
    )


def test_every_nested_block_type_describes_every_key_it_receives() -> None:
    """The sweep. Each dict-valued section, checked against its declared type."""
    report = _real_report()
    mapping = _nested_block_types()
    source = _TYPES.read_text(encoding="utf-8")

    problems: list[str] = []
    checked_blocks = 0
    checked_keys = 0
    for key, class_name in sorted(mapping.items()):
        value = report.get(key)
        # `tracks` / `issues` are lists of blocks; check the first element.
        if isinstance(value, list):
            value = value[0] if value and isinstance(value[0], dict) else None
        if not isinstance(value, dict) or not value:
            continue  # nothing populated in this fixture — not this test's business
        declared = set(_declared_keys(class_name))
        checked_blocks += 1
        checked_keys += len(value)
        missing = sorted(k for k in value if k not in declared)
        if missing:
            problems.append(
                f"{class_name} (report[{key!r}]) does not declare: {missing}"
            )
        extra = sorted(
            k for k in declared if k not in value and f"{k}: NotRequired" not in source
        )
        if extra:
            problems.append(f"{class_name} declares but report[{key!r}] lacks: {extra}")

    # FLOORS. Both halves: enough blocks to be a sweep, and enough keys that the
    # blocks are not empty stubs. A sweep that examines nothing passes trivially.
    assert checked_blocks >= 8, (
        f"only {checked_blocks} nested block(s) examined — the fixture is not "
        "populating the report, so a pass here proves nothing"
    )
    assert checked_keys >= 60, f"only {checked_keys} nested keys examined"
    assert not problems, "report_types.py is out of step with the report — " + (
        "; ".join(problems)
    )
