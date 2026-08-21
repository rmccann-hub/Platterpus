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


#: Rules that match a committed FORK log and no committed STOCK log, yet are not
#: declared fork-only. Each needs a reason, and the map may **shrink, never grow**.
#:
#: **Why an unresolved list rather than just declaring them.** The derivation below
#: is real evidence but it has one known weakness: only 6 stock logs are committed,
#: so *"never appears in a stock log"* can be a fact about our sample rather than
#: about upstream. Declaring a line fork-only when upstream also prints it would
#: put the fork on the hook for something that is not theirs — an error in the
#: opposite direction and just as wrong. The answer lives in their tree, so it is
#: a question for them, not a guess for us.
_UNRESOLVED_FORK_ATTRIBUTION: dict[str, str] = {
    "consumer": (
        "the `Consumer:` line exists because of the fork's --consumer flag, so it "
        "is almost certainly fork-only; not declared until they confirm, because "
        "the flag's own P1 row is the evidence and we have not read it for this"
    ),
    "handshake_note": (
        "the `Handshake:` line is the fork's own release-gate note; near-certainly "
        "fork-only, same reason as `consumer` for not asserting it unilaterally"
    ),
    "invoked_as": (
        "`Invoked as:` was added during the round-4 argv discussion; we believe "
        "fork-only but have not read the upstream source to confirm upstream "
        "never prints it"
    ),
    "read_stalls": (
        "`Read stalls:` was our own round-5 ask, so fork-only is the expectation; "
        "unconfirmed against upstream, which may have adopted it since"
    ),
    "secure_rerip_converged": (
        "the secure re-rip convergence line is a fork feature we asked for; not "
        "yet confirmed absent from upstream, which has its own -Z handling"
    ),
    "swap_addendum_crc": (
        "the swapped-byte-order addendum CRC; believed fork-only, unconfirmed"
    ),
    "release_id": (
        "genuinely uncertain, and the most likely false positive here: a "
        "MusicBrainz release id line is the sort of thing upstream would also "
        "print, and our stock sample is 6 logs"
    ),
    "rip_completed": (
        "genuinely uncertain. Round 12 §D1 reworded this line, which shows the "
        "fork owns its current WORDING, but not that upstream prints no such "
        "line at all — a different claim"
    ),
}


def _rules_matching_only_fork_logs(generator: ModuleType) -> set[str]:
    """Rule names that match a committed fork log and no committed stock log.

    Derived from the artifacts rather than from anyone's belief about them — the
    `CLAUDE.md` rule about reading the file that can settle the question. Fork vs
    stock is decided by the real `ripper_identity` classifier on each log's own
    banner, not by its filename.
    """
    import re

    from platterpus import ripper_identity

    fork_text: list[str] = []
    stock_text: list[str] = []
    for path in sorted(_REPO_ROOT.glob("output_reference/**/*.log")) + sorted(
        _REPO_ROOT.glob("docs/handshake/inbound/artifacts/*.log")
    ):
        body = path.read_text(encoding="utf-8", errors="replace")
        identity = ripper_identity.identify_from_banner(body)
        (fork_text if getattr(identity, "is_fork", False) else stock_text).append(body)

    # A floor on the CORPUS, because "matched no stock log" is meaningless when
    # there are no stock logs — the check would then declare everything fork-only.
    assert len(fork_text) >= 5, f"only {len(fork_text)} fork logs committed"
    assert len(stock_text) >= 3, f"only {len(stock_text)} stock logs committed"

    only_fork: set[str] = set()
    for name, pattern, _ in generator._pattern_rows():
        compiled = re.compile(pattern, re.MULTILINE)
        if any(compiled.search(body) for body in fork_text) and not any(
            compiled.search(body) for body in stock_text
        ):
            only_fork.add(name)
    return only_fork


def test_a_fork_only_rule_is_declared_or_explicitly_unresolved() -> None:
    """**The converse of the test above, and the direction that actually failed.**

    That test checks names in `_FORK_ONLY_RULES` still exist. It cannot see a
    fork-only rule *missing* from the set — and that omission understates the
    fork's obligation, which is the dangerous direction: they can reword a line
    believing nothing consumes it.

    Measured 2026-08-21: the four `album_*` rules were added, this set was not,
    and the contract we publish said *"9 exist only in the fork"* when it was 13
    — for exactly the four rows we had just made ourselves depend on **in
    preference to** the FFmpeg block their own P3 disclaims. Everything else on
    that page is derived; this set is typed, which is why it was the field that
    rotted.
    """
    generator = _load_generator()
    candidates = _rules_matching_only_fork_logs(generator)
    assert len(candidates) >= 10, (
        f"the derivation found only {len(candidates)} fork-only candidates, so it "
        f"has stopped recognising the logs and a pass proves nothing"
    )
    undeclared = candidates - set(generator._FORK_ONLY_RULES)
    surprises = sorted(undeclared - set(_UNRESOLVED_FORK_ATTRIBUTION))
    assert not surprises, (
        "these rules match a committed FORK log and no committed STOCK log, but "
        f"are neither declared fork-only nor recorded as unresolved: {surprises}.\n"
        "Add them to `_FORK_ONLY_RULES` in scripts/emit_dependency_contract.py and "
        "regenerate, or record why the attribution is uncertain in "
        "`_UNRESOLVED_FORK_ATTRIBUTION` above. Do not delete this assertion: the "
        "published contract is what tells the fork which lines it is on the hook "
        "for, and an omission there is silent on both sides."
    )


def test_the_unresolved_attribution_list_only_shrinks() -> None:
    """A ratchet, and its reasons have to be real.

    An unresolved list is a legitimate answer to *"we do not know"* and an
    illegitimate place to park work. So: it may not grow past what was measured
    on 2026-08-21, every entry needs a reason long enough to be one, and an entry
    that has since been resolved must be **removed** rather than left to imply
    doubt that no longer exists.
    """
    generator = _load_generator()
    assert len(_UNRESOLVED_FORK_ATTRIBUTION) <= 8, (
        f"{len(_UNRESOLVED_FORK_ATTRIBUTION)} unresolved attributions; 8 were "
        f"measured on 2026-08-21 and this list may only shrink. A new fork-only "
        f"rule of ours is DECLARED, not parked here."
    )
    for name, reason in _UNRESOLVED_FORK_ATTRIBUTION.items():
        assert len(reason) >= 60, f"{name}: the reason is {len(reason)} chars"
        assert name not in generator._FORK_ONLY_RULES, (
            f"{name} is both declared fork-only and listed as unresolved — the "
            f"question has been answered, so delete the unresolved entry"
        )
