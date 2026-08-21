"""The committed consumer contract must equal what the code says today.

``docs/cyanrip-consumer-contract.md`` is the file the cyanrip fork reads to
learn what Platterpus depends on it emitting. A hand-maintained version of that
would be wrong within a week — and *silently* wrong, since nothing downstream
would notice. So it is generated from the parser's own enumeration tables and
from calling the real argv builder, and this test regenerates it and demands a
byte-identical match.

The failure mode this prevents is specific and has happened in this project's
neighbourhood already: we told the fork the `-Z` `Done;` line was stdout-only,
they implemented against that description faithfully, and every verdict shifted
by one track. A description of our behaviour that is *derived from* our
behaviour cannot make that class of mistake.

Regenerate with ``python scripts/emit_dependency_contract.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "emit_dependency_contract.py"

# The parsed surface is large and stable; these floors exist so a generator that
# silently produced an empty (or near-empty) document could not pass. Set well
# below today's counts so ordinary parser work does not trip them — they catch
# collapse, not change.
_MIN_PARSED_PATTERNS = 30
_MIN_IGNORED_LINES = 5
_MIN_FLAGS = 10


def _load_generator() -> ModuleType:
    """Import the script by path — ``scripts/`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("emit_dependency_contract", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_committed_contract_is_what_the_code_generates() -> None:
    generator = _load_generator()
    committed = generator.OUTPUT_PATH.read_text(encoding="utf-8")
    assert committed == generator.render(), (
        "docs/cyanrip-consumer-contract.md is stale — regenerate it with\n"
        "    python scripts/emit_dependency_contract.py\n"
        "and commit the result alongside the parser/adapter change."
    )


def test_the_generator_is_deterministic() -> None:
    """No timestamp, no version, no set iteration order leaking into the text.

    A generator whose output changes between runs would make the staleness check
    above fail at random, and the first fix anyone reaches for is to delete the
    check.
    """
    generator = _load_generator()
    assert generator.render() == generator.render()


def test_the_contract_actually_contains_a_contract() -> None:
    """Floors, because every assertion here is "the file matches the generator"
    and an empty generator satisfies that perfectly."""
    generator = _load_generator()
    assert len(generator._pattern_rows()) >= _MIN_PARSED_PATTERNS
    assert len(generator._ignored_rows()) >= _MIN_IGNORED_LINES
    assert len(generator._emitted_flags()) >= _MIN_FLAGS


def test_the_two_non_negotiable_flags_are_emitted() -> None:
    """`-N` (Critical rule #5) and `-o` (FLAC master, Critical rule #4) are
    claimed *in prose* in the generated document. Assert the claim against the
    derived list, so the prose cannot outlive the behaviour."""
    generator = _load_generator()
    flags = generator._emitted_flags()
    assert "-N" in flags, "cyanrip must never do its own MusicBrainz lookup"
    assert "-o" in flags, "the rip must always produce the FLAC archival master"


#: Every place in the product that spawns the ripper, with the flag that makes
#: that invocation *distinct* from a rip. The contract's "Flags we pass you"
#: section must cover all of them.
#:
#: A ratchet, and the direction matters: this list may **grow** (a new way to run
#: the ripper is a new row here, and it fails until the generator's population
#: includes it) and an entry may only be removed when the call site goes away.
#: The generator asserts nothing about its own completeness — it collects the rip
#: argv plus whatever probes were remembered — so this is the list that makes
#: "remembered" into "checked".
_INVOCATION_SHAPES: dict[str, tuple[str, str]] = {
    "the rip itself": ("-N", "the argv builder; -N is the chokepoint's guarantee"),
    "the version probe": (
        "--version",
        "deps/ripper_offer and the update worker, to learn which build is installed",
    ),
    "the log verifier": (
        "--verify-log",
        "cyanrip_cli.VERIFY_LOG_FLAG, run over a finished rip's own logfile",
    ),
    "the rig-check argv probe": (
        "-j",
        "rig_check.DIAGNOSTICS_FLAG, to read our command line back out of the "
        "diagnostics record; the shape that was MISSING from the contract until "
        "2026-08-21",
    ),
}


def test_every_way_we_run_the_ripper_appears_in_the_contract() -> None:
    """**The check for the class, not the instance.**

    ``docs/cyanrip-consumer-contract.md`` §3 is headed *"Flags we pass you"* and
    is therefore read as complete. It was not: it listed 18 flags and omitted
    ``-j``, which ``rig_check`` really does pass, because the generator's
    population was the rip argv plus two remembered probes. The generator's own
    comment said *"The rip is not the only thing we run. Every invocation we make
    is part of the argv surface"* — one screen above a population that did not
    include this one. That is the third recorded instance of the same blind spot
    in that function, which is what makes a comment there insufficient.

    `CLAUDE.md`: *does this document promise completeness? Then it needs a sweep,
    not a comment.* This is the sweep. A fifth way to run the ripper fails here
    until the generator knows about it.
    """
    generator = _load_generator()
    flags = set(generator._emitted_flags())
    missing = {
        shape: (flag, why)
        for shape, (flag, why) in _INVOCATION_SHAPES.items()
        if flag not in flags
    }
    assert not missing, (
        "the published contract omits a flag we really send:\n"
        + "\n".join(
            f"  {shape}: {flag} — {why}" for shape, (flag, why) in missing.items()
        )
        + "\nAdd it to `_emitted_flags()` in scripts/emit_dependency_contract.py "
        "by DERIVING it from the call site's own constant, then regenerate. Do "
        "not fix this by deleting the row."
    )


def test_the_invocation_shape_registry_is_not_empty_and_names_real_constants() -> None:
    """The floor, plus the check that the rows point at the real code.

    A registry can be satisfied by finding nothing, and a registry of string
    literals can be satisfied by finding nothing *real*. So: at least the four
    shapes known on 2026-08-21, and the two that are exported as constants are
    compared against those constants rather than to their own spelling.
    """
    from platterpus.cyanrip_cli import VERIFY_LOG_FLAG
    from platterpus.rig_check import DIAGNOSTICS_FLAG

    assert len(_INVOCATION_SHAPES) >= 4, (
        f"only {len(_INVOCATION_SHAPES)} invocation shapes registered; four were "
        f"known on 2026-08-21 and this list may not shrink while their call "
        f"sites exist"
    )
    assert _INVOCATION_SHAPES["the log verifier"][0] == VERIFY_LOG_FLAG
    assert _INVOCATION_SHAPES["the rig-check argv probe"][0] == DIAGNOSTICS_FLAG
    for shape, (flag, why) in _INVOCATION_SHAPES.items():
        assert flag.startswith("-"), f"{shape}: {flag!r} is not a flag"
        assert len(why) >= 40, (
            f"{shape}: the reason is {len(why)} chars. Name the call site — the "
            f"next reader has to be able to find it to check this row."
        )


def test_check_mode_reports_staleness() -> None:
    """The `--check` path is what CI would call; prove it can fail, not just
    that it can pass. A checker that always returns 0 is decoration."""
    generator = _load_generator()
    assert generator.main(["--check"]) == 0

    original = generator.OUTPUT_PATH.read_text(encoding="utf-8")
    try:
        generator.OUTPUT_PATH.write_text(original + "\ndrift\n", encoding="utf-8")
        assert generator.main(["--check"]) == 1
    finally:
        generator.OUTPUT_PATH.write_text(original, encoding="utf-8")
    assert generator.main(["--check"]) == 0


def test_fork_only_rows_are_named_and_still_exist() -> None:
    """The fork-only marking is a hand-kept set, so it can drift out of the
    parser. Every name in it must still be a real rule name."""
    generator = _load_generator()
    known = {name for name, _, _ in generator._pattern_rows()}
    missing = sorted(generator._FORK_ONLY_RULES - known)
    assert not missing, (
        f"_FORK_ONLY_RULES names rules the parser no longer has: {missing} — "
        "either the rule was renamed or it was removed."
    )
    assert len(generator._FORK_ONLY_RULES) >= 5
