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
#:
#: **EMPTY as of 2026-08-21, and that is the outcome the mechanism was for.** It
#: held eight entries for a few hours. The fork answered our round-12 lap 4 §C1
#: from *their* trees — `tools/upstream-delta.py` diffs every `cyanrip_log()`
#: format string in `platterpus-fork` against their verbatim mirror of upstream at
#: 0.9.4-rc2 — which answers *"does upstream's source print this"* rather than our
#: *"is it absent from the six stock logs we hold"*. Six were confirmed theirs and
#: are now declared; two were not ours to declare at all:
#:
#: * ``release_id`` — **upstream's line.** They print it; the fork only *reworded*
#:   it (at their `38e84cb`), so the wording is theirs and the line is upstream's —
#:   the exact inverse of ``rip_completed``. Our instinct that this was the likely
#:   false positive was right, and it is why the map existed instead of a guess.
#: * ``swap_addendum_crc`` — **ours.** It parses text Platterpus writes. See
#:   `_OUR_OWN_OUTPUT_RULES` in the generator.
#:
#: Kept as an empty map rather than deleted: the two tests below are the mechanism,
#: and the mechanism is what turned "we do not know" into an answer instead of into
#: a silent declaration. A future uncertainty gets a row here and a question in a
#: lap, not a guess in the published contract.
_UNRESOLVED_FORK_ATTRIBUTION: dict[str, str] = {}

#: Rules the log-corpus derivation flags as fork-only that **are not**, each with
#: what settled it. This is the bucket that keeps the derivation honest: it has a
#: measured false-positive rate, and pretending otherwise is how a guess gets
#: published as a contract claim.
#:
#: "Matches a fork log, matches no stock log" is evidence, not proof — our stock
#: sample is six logs, and one of these two shows the method reading *our own
#: output* back and calling it the fork's. Both were settled from a source, not
#: from a bigger sample.
_NOT_FORK_DESPITE_THE_LOGS: dict[str, str] = {
    "release_id": (
        "UPSTREAM'S LINE, per the fork on 2026-08-21 from their verbatim mirror of "
        "upstream: upstream prints `Release ID unavailable, cannot search Cover Art "
        "DB!`, `Release ID %s not found in release list for DiscID %s!` and `Found "
        "MusicBrainz release: %s - %s`. The fork only REWORDED the first (their "
        "38e84cb), so the wording is theirs and the line is upstream's — the exact "
        "inverse of `rip_completed`, where they own both. We may therefore depend on "
        "the line existing and NOT on its exact text.\n"
        "CAVEAT, RECORDED BECAUSE A CORRECTION IS NOT PRE-VERIFIED (CLAUDE.md): none "
        "of those three strings is the line THIS rule matches. Our pattern is "
        "`^Release ID:\\s+(?P<value>\\S+)` — the banner header row, which their own "
        "P2 inventory puts at `cyanrip_log.c:716` as `Release ID:     %s` and which "
        "their answer does not mention. Their conclusion is plausible (an echo of a "
        "release id is exactly what upstream would print) and NOT declaring it "
        "fork-only errs safe either way, since the error we are avoiding is putting "
        "them on the hook for a line that is not theirs. Confirming the banner row "
        "specifically is round 13's. Note our own stock-log absence (0 of 11) is no "
        "evidence here at all: the row only appears when a release id is known, "
        "which needs the `-a musicbrainz_albumid=` that only Platterpus sends."
    ),
    "swap_addendum_crc": (
        "OURS. It parses the `[Platterpus auto-fix addendum]` block that "
        "`rip_addendum.render_addendum` writes. `addendum` appears zero times in the "
        "fork's src/ and zero times in upstream's. Our own corroboration is the "
        "stronger one: the single committed 'fork log' this rule matches has the "
        "match INSIDE our own addendum block, so the derivation was reading our "
        "output back and attributing it to them. Published in its own section of the "
        "contract rather than in the table of lines we depend on THEM for."
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
    settled = set(_UNRESOLVED_FORK_ATTRIBUTION) | set(_NOT_FORK_DESPITE_THE_LOGS)
    surprises = sorted(undeclared - settled)
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

    **The cap is now 0, and moving it down was the point of the ratchet.** It was
    8 while eight attributions were open; all eight were answered the same day, so
    a cap of 8 would silently permit re-growing to eight parked questions and the
    ratchet would have measured nothing. Raising it again is allowed — a genuinely
    uncertain new rule belongs here rather than being declared on a guess — but it
    is then a visible edit with a number attached, which is the whole mechanism.
    """
    generator = _load_generator()
    assert len(_UNRESOLVED_FORK_ATTRIBUTION) <= 0, (
        f"{len(_UNRESOLVED_FORK_ATTRIBUTION)} unresolved attributions; all eight "
        f"open on 2026-08-21 were answered that day and the cap moved to 0. A new "
        f"fork-only rule of ours is DECLARED, not parked here — and a genuinely "
        f"uncertain one raises this number in the same commit, with the reason."
    )
    for name, reason in _UNRESOLVED_FORK_ATTRIBUTION.items():
        assert len(reason) >= 60, f"{name}: the reason is {len(reason)} chars"
        assert name not in generator._FORK_ONLY_RULES, (
            f"{name} is both declared fork-only and listed as unresolved — the "
            f"question has been answered, so delete the unresolved entry"
        )


def test_the_derivations_known_false_positives_are_named_and_reasoned() -> None:
    """The bucket that stops a heuristic being published as a contract claim.

    "Matches a fork log, matches no stock log" is evidence with a measured false
    positive rate — two of ten on 2026-08-21 — and both were settled from a
    *source* rather than from a larger sample. Requiring a written reason per entry
    is what keeps this from becoming a place to park anything inconvenient, and
    asserting they are NOT declared fork-only is what stops the two buckets
    contradicting each other in the published document.
    """
    generator = _load_generator()
    assert len(_NOT_FORK_DESPITE_THE_LOGS) >= 2, (
        "the two measured false positives are the argument for this bucket "
        "existing; removing them removes the record that the derivation can be "
        "wrong"
    )
    for name, why in _NOT_FORK_DESPITE_THE_LOGS.items():
        assert len(why) >= 120, f"{name}: the reason is {len(why)} chars"
        assert name not in generator._FORK_ONLY_RULES, (
            f"{name} is both declared fork-only and recorded as not-fork — the "
            f"published contract would claim the fork owns a line we have "
            f"evidence they do not"
        )
    # The one that is ours must be published as ours, not merely withheld.
    assert "swap_addendum_crc" in generator._OUR_OWN_OUTPUT_RULES, (
        "swap_addendum_crc is recorded as parsing our own output but is not in "
        "_OUR_OWN_OUTPUT_RULES, so the contract still lists it among the lines we "
        "ask the fork to hold stable"
    )


def test_the_not_fork_bucket_names_real_rules_the_derivation_really_flags() -> None:
    """Both halves, or the bucket becomes a place to silence the derivation.

    A name that is not a real rule is a typo that silently exempts nothing; a name
    the derivation does **not** flag is an exemption for a question nobody asked,
    which is how an escape hatch turns into a habit. So each entry must be a live
    rule *and* still be a candidate — when it stops being one, delete the row.
    """
    generator = _load_generator()
    known = {name for name, _, _ in generator._pattern_rows()}
    unknown = sorted(set(_NOT_FORK_DESPITE_THE_LOGS) - known)
    assert not unknown, f"_NOT_FORK_DESPITE_THE_LOGS names non-existent rules: {unknown}"
    candidates = _rules_matching_only_fork_logs(generator)
    idle = sorted(set(_NOT_FORK_DESPITE_THE_LOGS) - candidates)
    assert not idle, (
        f"these rows exempt rules the derivation no longer flags: {idle} — the "
        f"exemption is doing nothing and should be deleted, so the next reader is "
        f"not told the derivation has false positives it no longer has"
    )


def test_our_own_output_rules_are_derived_from_our_own_emitter() -> None:
    """**The check that makes `_OUR_OWN_OUTPUT_RULES` a measurement, not a belief.**

    The claim *"this rule parses text we write, not text cyanrip writes"* is the
    whole basis for moving a row out of the contract's §1, and the fork found the
    original mis-filing by reading their own tree. Ours has to be checkable here:
    render a real addendum with the real emitter and require every declared name to
    match a line of it. A rule that matches nothing we emit is not ours, and a
    typo in the set is caught by the same assertion.

    **`track_secure_verdict` must NOT be in the set**, and that is asserted rather
    than assumed: the addendum deliberately mirrors cyanrip's own `Secure re-read:`
    label so the supersede is honoured on a re-parse, and the fork really does emit
    that line (their P2, `cyanrip_log.c:441/444/449`). "Matches our text" is a
    necessary condition for membership, never a sufficient one.
    """
    from platterpus.rip_addendum import SupersededTrack, render_addendum

    generator = _load_generator()
    rendered = render_addendum(
        "accuraterip",
        [
            SupersededTrack(
                number=5,
                filename="05 - Example.flac",
                crc="E0036697",
                previous_crc="6902BCF0",
                accuraterip_v1="ABCD1234 — matched — confidence 7",
                accuraterip_v2="DEADBEEF — matched — confidence 9",
                accuraterip_offset="12345678 — matched — confidence 3",
                secure_reread="converged after 5 reads",
            )
        ],
    )
    assert rendered.strip(), "render_addendum produced nothing to check against"
    patterns = {name: pattern for name, pattern, _ in generator._pattern_rows()}
    assert generator._OUR_OWN_OUTPUT_RULES, (
        "the set is empty, so this test passes by finding nothing; the addendum "
        "block is still parsed and still needs to be published as ours"
    )
    for name in sorted(generator._OUR_OWN_OUTPUT_RULES):
        assert name in patterns, f"{name} is not a rule the parser has"
        compiled = __import__("re").compile(patterns[name])
        matched = [line for line in rendered.splitlines() if compiled.match(line)]
        assert matched, (
            f"`{name}` is declared as parsing Platterpus's own output, but it "
            f"matches no line that rip_addendum.render_addendum actually writes. "
            f"Either the emitter's text moved or the declaration is wrong — and a "
            f"wrong one publishes a cyanrip line as ours, which is the same "
            f"mis-attribution in the other direction."
        )
    assert "track_secure_verdict" not in generator._OUR_OWN_OUTPUT_RULES, (
        "the addendum mirrors cyanrip's `Secure re-read:` label on purpose; that "
        "line IS theirs (their P2) and belongs in §1"
    )


def test_a_line_we_write_ourselves_is_not_published_as_one_they_must_hold() -> None:
    """The published-document half of the fix, asserted on the text we ship.

    §1's own preamble says *"changing the text, indentation, or field order of any
    of these changes what Platterpus records about a rip"*, and the page tells the
    fork that a change to a §1 line *"is a breaking change to us and requires a
    handshake round"*. Applying that to `[Platterpus auto-fix addendum]` — text
    `rip_addendum.render_addendum` writes — asked another project to keep a line
    stable that it does not emit and cannot break.

    Checked against the rendered document rather than the sets, because the sets
    are the input and the document is what the fork actually reads.
    """
    generator = _load_generator()
    text = generator.render()
    section_1 = text.split("## 1a.")[0]
    ours_section = text.split("## 1a.")[1].split("## 2.")[0]
    assert "## 1a." in text, "the 'lines we write' section is missing entirely"
    for name in sorted(generator._OUR_OWN_OUTPUT_RULES):
        assert f"`{name}`" not in section_1, (
            f"`{name}` parses our own text and is still listed in §1, the table of "
            f"lines we ask the fork to hold stable"
        )
        assert f"`{name}`" in ours_section, (
            f"`{name}` was removed from §1 but is not published in §1a either — it "
            f"has been made invisible rather than correctly attributed, and the "
            f"fork will meet it in a rig log with nothing to explain it"
        )
    # The section has to say whose it is and where it comes from, or it is a list
    # of names with no claim attached.
    assert "rip_addendum" in ours_section, (
        "§1a does not name the module that writes these lines, so a reader cannot "
        "check the attribution"
    )
