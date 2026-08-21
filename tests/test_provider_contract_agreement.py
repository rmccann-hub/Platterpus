"""Our consumer contract must not contradict the fork's provider contract.

The two halves of the cyanrip seam are each generated from their own side's
code: ours from the parser's enumeration tables, theirs by walking every
`cyanrip_log()` call site. Generating both removes the "described behaviour we
do not have" failure — but it does not stop the two *descriptions* from
disagreeing, and a disagreement there is the next breakage.

The specific hazard: **parsing a line the fork considers unstable.** Their P3
list is text they reserve the right to reword without a handshake. If we parse
one of those, their next cosmetic change breaks us and neither side finds out
until a rip comes back wrong. That check is the reason this file exists, and it
is the concrete answer to their §J4.

## This file used to lie about its own currency, for nine rounds

The docstring above this line said *"Reads their committed round-4 file
directly. When a new round lands with a new provider contract, this test
re-derives from it — no list to maintain here."* It did not re-derive from
anything: `_ROUND_4` was a hard-coded path to `inbound/round-4.md`, and it was
still the subject when round 12 closed. So the *input* half of the seam was
being diffed against round 11/12's flag table by
`tests/test_argv_surface_agreement.py` while the *output* half was diffed
against a document from eight rounds earlier — and the file said otherwise in
its own first paragraph, which is why nobody looked.

Two things it cost, both real:

* **Their P3 grew rows we could not see.** Round 4's P3 was 12 rows, all
  ``*.c``. Round 12's is 25, ten of them ``genopt.h`` — and the row regex here
  matched ``[a-z_]+\\.c:`` only, so even pointed at the new file it would have
  read 15 of 25 and reported a full pass.
* **Their P4 stopped saying the sentence this file asserts on.** See
  :func:`test_the_verify_log_exit_codes_are_the_ones_we_classify`.

**The resolution is imported, not re-derived** —
`test_argv_surface_agreement.newest_provider_contract`. That module already owns
the handshake round/lap parsing (itself delegating to `scripts/handshake.py`),
and this repository has now broken *four* independently-grown round parsers on
one naming migration. One resolver also means the two halves of the seam cannot
be checked against contracts from different rounds again, which is the failure
above.

## Section headings move; section NUMBERS do not

Round 4's was ``## P3 - Unstable lines: reworded without a handshake``; round
12's is ``## P3 - Unstable wording, and stdout-only routing``. The old code
matched on the literal prose, which worked only because `str.index` happens to
accept a prefix. Sections are resolved by their ``P<n>`` label instead — that is
the part of the heading the contract's own generator keys on, and the only part
either side has ever treated as stable.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_argv_surface_agreement import (
    _MAX_TABLE_LAG,
    _file_round,
    _newest_inbound_round,
    newest_provider_contract,
)

from platterpus.adapters import ripper_log_verify
from platterpus.cyanrip_cli import VERIFY_LOG_EXIT_NO_VERDICT
from platterpus.deps import fork_source
from platterpus.parsers import cyanrip_log as parser

#: The contract this whole file is about. Resolved once, by the shared parser.
CONTRACT: Path = newest_provider_contract()

#: A ``| `file:line` | `text` |`` row in one of their inventories.
#:
#: ``\.[ch]`` rather than ``\.c``: round 12's P3 puts ten ``genopt.h`` rows beside the
#: ``*.c`` ones, and a reader narrower than the document silently drops them — the
#: "silent truncation reads as completeness" shape, arriving in the reader rather than
#: the writer. Measured on round 12 lap 3: 15 rows parsed of 25 present.
_ROW = re.compile(
    r"^\| `(?P<where>[A-Za-z0-9_.]+\.[ch]:\d+)` \| `(?P<line>.+?)` \|", re.MULTILINE
)

#: A contract section heading, by its ``P<n>`` label. **The label, never the prose** —
#: see the module docstring on why the prose is not a stable key.
_HEADING = re.compile(r"^## +(?P<label>P\d+)\b", re.MULTILINE)


def _sections() -> dict[str, str]:
    """Every ``P<n>`` section of the contract, label -> body (heading included).

    Built once from the heading positions rather than by two `str.index` calls per
    lookup, so a section that is *absent* raises a `KeyError` naming it instead of
    silently returning a slice that runs to the wrong place.
    """
    text = CONTRACT.read_text(encoding="utf-8")
    marks = list(_HEADING.finditer(text))
    bounds = [m.start() for m in marks] + [len(text)]
    return {
        m.group("label"): text[bounds[i] : bounds[i + 1]] for i, m in enumerate(marks)
    }


def _rows(label: str) -> list[tuple[str, str]]:
    """The ``(file:line, text)`` rows of one section."""
    return [
        (m.group("where"), m.group("line")) for m in _ROW.finditer(_sections()[label])
    ]


def _render(fmt: str) -> str:
    """Turn a C format string into a plausible instance of the line.

    `%i`/`%u`/`%X` → a number, `%f` → a decimal, `%s` → a word. Good enough to
    ask "would our pattern bite on this", which is the only question here.

    **Length modifiers are handled** (``%lld``, ``%hi``, ``%llu``, ``%zu``). They were
    not, and the omission ran the wrong way: an unrendered ``%llds`` leaves a literal
    ``%`` in the string, which can stop a pattern matching a line the *real* log would
    match — a false pass in the one check this file exists for. Round 12's P3 has four
    ``%llds`` rows and round 12's ``genopt.h`` block three more.
    """
    return re.sub(
        r"%0?\d*[.]?\d*(?:hh|h|ll|l|z|j|t)?(?P<conv>[iudxXsfc])",
        lambda m: (
            "7"
            if m.group("conv") in "iudxX"
            else ("1.5" if m.group("conv") == "f" else "X")
        ),
        fmt.replace('\\"', '"'),
    )


def _top_level_rule_matching(line: str) -> str | None:
    """The name of the disc-level rule that claims ``line``, if any.

    Only top-level rules: the fork's unstable lines are all emitted at column 0,
    and the indented patterns are applied by the parser *only inside* a section
    or track block, so testing them here would produce false positives — as it
    did on the first attempt, where a permissive `Gaps:`-section pattern
    appeared to match all twelve.
    """
    for rule in parser._ALL_LINE_RULES:
        if rule.pattern.match(line):
            return str(rule.name)
    return None


def test_the_renderer_handles_length_modifiers() -> None:
    """An unrendered specifier is a **false pass** in the load-bearing check.

    `_render` turns a C format string into something our patterns can be tried
    against. It handled `%i`/`%s`/`%f` and *silently* left `%llds`, `%hi` and `%llu`
    alone — so the string kept a literal `%`, which can stop a pattern matching a
    line the real log *would* match. Round 12's P3 carries four `%llds` rows
    (`stall_watchdog.c`) and three `%ll*`/`%h*` rows in its `genopt.h` block, so the
    gap was live, not hypothetical.

    Pinned as exact equality rather than "contains no %": the fix has to produce a
    plausible *instance*, and the plain forms must keep working — extending a
    renderer is how you break the four cases it already handled.
    """
    assert (
        _render("Still waiting: %s has not returned after %llds")
        == "Still waiting: X has not returned after 7s"
    )
    assert _render("(default: %hi)") == "(default: 7)"
    assert _render("(default: %llu)") == "(default: 7)"
    assert _render("Track %i - the read for LSN %i returned after %llds") == (
        "Track 7 - the read for LSN 7 returned after 7s"
    )
    # The forms that already worked.
    assert _render("%s folder: [%s] extension: %s%s") == "X folder: [X] extension: XX"
    assert _render("Album integrated loudness (R128): %.1f LUFS") == (
        "Album integrated loudness (R128): 1.5 LUFS"
    )
    assert _render('Log \\"%s\\" checksum valid.') == 'Log "X" checksum valid.'


def test_the_contract_we_read_is_the_current_rounds_own() -> None:
    """**The regression test for reading round 4 while round 12 was closing.**

    Held to the *same recorded lag* as the flag table (`_MAX_TABLE_LAG`), imported
    rather than re-declared: two numbers for one question is how the argv check and
    the round-own-table check once disagreed about the same situation.
    """
    round_of_contract = _file_round(CONTRACT)
    assert round_of_contract is not None, (
        f"{CONTRACT.name} does not resolve to a round — the artifact naming "
        "convention changed and the resolver did not"
    )
    newest = _newest_inbound_round()
    assert newest - round_of_contract <= _MAX_TABLE_LAG, (
        f"the provider contract read here is round {round_of_contract}'s but the "
        f"newest inbound round is {newest} — a lag of "
        f"{newest - round_of_contract}, past the recorded {_MAX_TABLE_LAG}. This is "
        f"the state this file spent nine rounds in. Contract: {CONTRACT.name}"
    )


def test_the_provider_contract_is_present_and_substantial() -> None:
    """A floor. Every check below is "for each line in their contract", which
    an unparsed or truncated file satisfies by having no lines."""
    stable = _rows("P2")
    unstable = _rows("P3")
    assert len(stable) >= 200, f"only parsed {len(stable)} stable lines"
    assert len(unstable) >= 10, f"only parsed {len(unstable)} unstable lines"


def test_every_unstable_row_in_the_document_is_read() -> None:
    """The reader must not be narrower than the document.

    Their P3 is not all ``*.c``: round 12 lists ten ``genopt.h`` rows, and the row
    regex used to accept ``.c`` only — so it read 15 of 25 and reported a clean
    sweep. Counted against the section's own table rows rather than against a number
    written here, because a hard-coded expected count is the thing that goes stale.
    """
    # Every data row of the P3 table: a `|`-delimited line whose first cell is a
    # backticked token. Deliberately NOT the same regex `_ROW` uses — a reader
    # checked against itself is consistent, not verified (the round-5 lesson).
    table_rows = [
        line for line in _sections()["P3"].splitlines() if line.startswith("| `")
    ]
    parsed = _rows("P3")
    assert len(table_rows) >= 10, f"only {len(table_rows)} rows in P3 at all"
    unread = [
        line
        for line in table_rows
        if not any(f"| `{where}` |" in line for where, _ in parsed)
    ]
    assert not unread, (
        f"P3 has {len(table_rows)} rows and this file reads {len(parsed)} of them. "
        f"Unread: {unread}"
    )


def test_we_parse_nothing_the_fork_reserves_the_right_to_reword() -> None:
    """The load-bearing one.

    A line on their P3 list can change wording in any release without a
    handshake. Parsing one means their next cosmetic edit silently breaks us.
    """
    offenders = [
        (where, line, name)
        for where, line in _rows("P3")
        if (name := _top_level_rule_matching(_render(line)))
    ]
    assert not offenders, "we parse lines the fork calls unstable: " + "; ".join(
        f"{name} <- {where} {line!r}" for where, line, name in offenders
    )


#: The first parenthesised list in P3's closing paragraph — the FFmpeg `ebur128` line
#: names it disclaims **in prose rather than in a row**.
#:
#: Keyed on the parenthetical (structure) rather than on the sentence around it
#: (prose), and scoped to it so the *"Prefer the `Sample peak level:` … lines in P2"*
#: half of the same paragraph — which is an instruction, not a disclaimer — does not
#: get swept in as something we must not parse.
_PROSE_PARENTHETICAL = re.compile(r"\(((?:[^()]|\([^()]*\))*)\)")
_BACKTICKED = re.compile(r"`([^`]+)`")


def test_the_prose_half_of_P3_is_disclaimed_too() -> None:
    """P3 states part of its content as a PARAGRAPH, not a row.

    Round 12's P3 ends with *"Also unstable, and **not ours**: the loudness block
    FFmpeg's `ebur128` filter prints (`Integrated loudness`, `Loudness range`,
    `Sample peak:`, `True peak:`, ...)"*. A row-only reader cannot see any of it, so
    the load-bearing check above was silently scoped to the table.

    It turns out **not** to change the verdict, and the reason is worth pinning
    rather than asserting: every pattern in `parsers/cyanrip_log.py` that reads the
    ebur128 block is an *indented* rule (`_LOUDNESS_I`, `_LOUDNESS_LRA`,
    `_LOUDNESS_PEAK`), which `_top_level_rule_matching` excludes by design, and the
    column-0 rows we do claim are the fork's own `Album integrated loudness (R128):`
    family from P2 — the ones their prose tells us to prefer (see the long comment
    at `parsers/cyanrip_log.py` "The album loudness/peak facts, from the rows cyanrip
    OWNS"). That is a live property of the parser, not a fact about the document, so
    it gets a check: somebody adding a top-level rule for FFmpeg's wording would
    otherwise land it green.
    """
    prose = _sections()["P3"].split("Also unstable", 1)
    assert len(prose) == 2, (
        "P3 no longer carries the 'Also unstable, and not ours' paragraph — if the "
        "prose disclaimer moved, this check needs re-pointing at wherever it went"
    )
    parenthetical = _PROSE_PARENTHETICAL.search(prose[1])
    assert parenthetical is not None, (
        "P3's prose disclaimer no longer names its lines in a parenthesised list"
    )
    named = sorted(set(_BACKTICKED.findall(parenthetical.group(1))))
    # FLOOR: a check that can be satisfied by finding nothing is decoration.
    assert len(named) >= 3, f"only {len(named)} disclaimed names parsed: {named}"
    offenders = [(n, name) for n in named if (name := _top_level_rule_matching(n))]
    assert not offenders, (
        "we claim FFmpeg's wording at column 0, which P3 disclaims in prose: "
        + "; ".join(f"{rule} <- {line!r}" for line, rule in offenders)
    )


@pytest.mark.parametrize(
    "line",
    [
        "Pregap LSN:  unknown (sub-channel CRC mismatches)",
        "Pregap source: lead-in",
        "Pregap source: sub-channel (not signalled by TOC)",
        "Rip completed:  no (interrupted by user, 2 of 3 tracks)",
    ],
)
def test_variants_only_their_contract_reveals_are_handled(line: str) -> None:
    """Four lines that appear in their P2 table and in **no artifact we hold**.

    Their golden reference is one successful rip of one disc image; it cannot
    contain a CRC-mismatch pre-gap, a lead-in-sourced pre-gap, or a cancelled
    footer. Those only became visible when they generated the contract, and one
    of them — the cancelled footer — was silently dropping the ripper's own
    track counts on the exact scenario we care most about.
    """
    stable = [ln for _, ln in _rows("P2")]
    assert line in stable or any(
        _render(ln).startswith(line.split("%")[0][:20]) for ln in stable
    ), f"{line!r} is no longer in their stable contract — re-verify before trusting it"


def _p4_codes() -> dict[int, str]:
    """P4's exit-code table: code -> the meaning the source states, if any.

    Derived from the table rather than from the summary sentence beneath it. The
    sentence is what this file used to assert on — *"Distinct exit values found in
    the tree: `0`, `1`"* — and the fork **removed it in round 12**, at column 0,
    knowing we parsed it. A claim keyed on one sentence of somebody else's generated
    document is a claim that expires without notice.
    """
    row = re.compile(r"^\| `(?P<code>\d+)` \|(?P<rest>.*)$", re.MULTILINE)
    return {
        int(m.group("code")): m.group("rest").strip()
        for m in row.finditer(_sections()["P4"])
    }


def test_the_exit_code_inventory_is_read_as_a_table() -> None:
    """A floor for the two checks below, and the shape-change regression.

    Round 4's P4 had two rows and a summary sentence; round 12's has six rows, a
    per-code meaning, and no such sentence. Both parse here — what is asserted is
    that a table was found at all, because "no rows" would satisfy every
    for-each-code check below.
    """
    codes = _p4_codes()
    assert len(codes) >= 2, f"only parsed {len(codes)} exit-code rows from P4"
    assert 0 in codes and 1 in codes, (
        f"P4 no longer documents both 0 and 1: {sorted(codes)} — every probe and "
        "every rip in this codebase splits on exactly that pair"
    )


def test_the_verify_log_exit_codes_are_the_ones_we_classify() -> None:
    """**The assertion that went false, re-pointed at what it was protecting.**

    It used to read ``assert "Distinct exit values found in the tree: `0`, `1`" in
    block``, with a docstring saying the report's prose *"assumes the {0,1} shape"*.
    The fork removed that sentence in round 12 and derived 0–5 instead, so the check
    correctly fails against the current contract. What the assumption actually was,
    checked against the code:

    * The **rip** and every **version/info probe** split on ``0`` vs non-zero vs
      ``None`` and read no class out of the number. P4 still says ``1`` carries no
      class, so nothing there assumed a two-value inventory — it assumed *zero
      versus not*, which is unchanged.
    * ``--verify-log`` is the one surface that now discriminates, and
      `adapters/ripper_log_verify.py` is the one consumer that turns a non-zero
      code into a claim about an archival artifact. That is where a third value
      matters, and it is what this test guards.

    So: every code P4 names as *no verdict was reached* must be a code that adapter
    refuses to turn into a verdict. One list, in `cyanrip_cli`, read by both.
    """
    codes = _p4_codes()
    assert len(codes) >= 2, "P4 table not parsed"
    # Codes whose stated meaning is "we could not look", derived from the row text.
    no_verdict = {
        code
        for code, meaning in codes.items()
        if "no verdict was reached" in meaning.casefold()
        or "io_error" in meaning.casefold()
    }
    assert no_verdict, (
        "P4 no longer names any exit code as 'no verdict was reached'. If the fork "
        "withdrew CRIP_LOG_EXIT_IO_ERROR, cyanrip_cli.VERIFY_LOG_EXIT_NO_VERDICT and "
        "the branch in adapters/ripper_log_verify.py that reads it must go with it."
    )
    assert no_verdict == set(VERIFY_LOG_EXIT_NO_VERDICT), (
        f"P4 names {sorted(no_verdict)} as 'no verdict reached' but "
        f"cyanrip_cli.VERIFY_LOG_EXIT_NO_VERDICT holds "
        f"{sorted(VERIFY_LOG_EXIT_NO_VERDICT)}. A code that means 'unreadable' must "
        "never reach the branch that says the log was altered."
    )


@pytest.mark.parametrize("code", sorted(VERIFY_LOG_EXIT_NO_VERDICT))
def test_a_no_verdict_exit_code_never_becomes_an_accusation(
    code: int, tmp_path: Path
) -> None:
    """**The regression test for the fix, and the fixture is the worst case.**

    The log written here is *readable by us* and *carries a `Log FUN512:` footer* —
    which is precisely the input that routed exit 5 to the bottom of
    :func:`~platterpus.adapters.ripper_log_verify.verify_rip_log` and produced *"the
    file was altered after the ripper signed it and must not be treated as archival
    evidence"*. A fixture with no footer, or an unreadable one, would land on an
    earlier branch and prove nothing (*"what does my stand-in do that the real thing
    does not?"*).

    The build tag is the **approved pin**, imported rather than typed, because the
    accusation branch is only reachable once `accepts_verify_log` returns True — a
    test using an unknown tag would pass against the unfixed code.

    Asserted on the wording as well as the verdict: `not_determined` with a sentence
    that still says "altered" is the same defect from the user's side.
    """
    log_file = tmp_path / "cyanrip.log"
    log_file.write_text(
        "cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g237a4ff)\n"
        "Rip completed:  yes\n"
        "Log FUN512:     AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n",
        encoding="utf-8",
    )
    result = ripper_log_verify.verify_rip_log(
        log_file,
        build_tag=fork_source.FORK_EXPECTED_BUILD_TAG,
        runner=lambda argv: _tool_run(argv, code),
    )
    assert result.verdict == ripper_log_verify.NOT_DETERMINED, (
        f"exit {code} means 'no verdict was reached' in their P4, and this adapter "
        f"returned {result.verdict!r}: {result.detail}"
    )
    lowered = result.detail.casefold()
    for accusation in ("altered", "modified", "rejected"):
        assert accusation not in lowered, (
            f"the detail for exit {code} says {accusation!r} — the ripper told us it "
            f"reached no verdict, so nothing here may describe the file: {result.detail}"
        )
    # And the evidence is still carried, or a `not_determined` is undiagnosable.
    assert result.exit_code == code
    assert result.argv and str(log_file) in result.argv


def test_the_no_verdict_branch_is_reached_before_the_capability_gate() -> None:
    """It must not wait on a build tag joining the capability table.

    `BUILD_TAGS_ACCEPTING_VERIFY_LOG` deliberately does **not** list the round-12
    pin, and adding it is not this change's business — so if the no-verdict branch
    sat *after* that gate, the fix would be unreachable for exactly the builds that
    emit these codes, and its regression test above would be the only thing that ever
    ran it. Asserted with a tag no table knows.
    """
    result = ripper_log_verify.verify_rip_log(
        __file__,
        build_tag="platterpus-fork-gdeadbee",
        runner=lambda argv: _tool_run(argv, max(VERIFY_LOG_EXIT_NO_VERDICT)),
    )
    assert result.verdict == ripper_log_verify.NOT_DETERMINED
    assert "no verdict" in result.detail.casefold(), (
        "an unknown build fell through to the capability-gate message instead of the "
        f"ripper's own reason: {result.detail}"
    )


def _tool_run(argv: list[str], code: int) -> object:
    """A minimal :class:`ToolRun` for the exit code under test.

    Built with the real dataclass constructor. `ToolRun` has no
    ``from_process`` — and the stand-in must be *less* capable than the real
    thing, so this passes only what a genuine run would carry: the exit code,
    empty output, and the argv as spawned.
    """
    from platterpus.adapters.tool_run import ToolRun

    return ToolRun(exit_code=code, output="", argv=tuple(argv))


#: Rules declared fork-only that their published inventory does **not** carry as a
#: literal format string, with why. May shrink, never grow without a written cause.
#:
#: One entry, and it is a real property of their generator rather than an excuse:
#: `track_peak_kind_header` reads the `True peak:` / `Sample peak:` sub-headers,
#: which cyanrip emits through the generic sub-header call site their P2 lists as
#: `cyanrip_log.c:58` → `%s%s:`. The label is a runtime argument, so no literal
#: exists to match and their P2a *Composed lines* section does not reconstruct this
#: one. That is a small gap in THEIR contract, not a defect in our declaration —
#: raised as round 13's, since a `%s%s:` row tells a consumer nothing.
_FORK_ONLY_WITHOUT_A_PUBLISHED_LITERAL: dict[str, str] = {
    "track_peak_kind_header": (
        "the peak sub-headers are emitted through the generic `cyanrip_log.c:58` "
        "`%s%s:` call site with the label as a runtime argument, so their P2 has no "
        "literal to match and P2a does not reconstruct it; verified against the "
        "committed logs instead, where both spellings appear"
    ),
}


def _p2_rows() -> list[tuple[str, str]]:
    """Every ``(file:line, format string)`` row of their stable-lines inventory.

    P2 *and* P2a: a rule can legitimately be backed by a composed line, and reading
    P2 alone would report a false gap — the same "narrower than the document"
    truncation this file's `_ROW` comment records one instance of.
    """
    rows = list(_rows("P2"))
    sections = _sections()
    if "P2a" in sections:
        rows += [
            (m.group("where"), m.group("line")) for m in _ROW.finditer(sections["P2a"])
        ]
    return rows


def test_every_fork_only_declaration_is_backed_by_their_own_inventory() -> None:
    """**The in-house half of "which of these lines are yours?".**

    Round 12 lap 4 §C1 asked the fork to attribute eight rules; their standing
    status of 2026-08-21 confirmed six as theirs, derived by diffing every
    `cyanrip_log()` format string in their tree against their verbatim mirror of
    upstream. That is better evidence than anything we can produce — and
    `CLAUDE.md` is explicit that a *correction* is not pre-verified, and that
    verifying somebody's **description** of their behaviour is a different claim
    from verifying the behaviour.

    We cannot check the upstream-absence half from this repository. We can check
    the half that is committed here: every line we declare fork-only must appear
    as a row in the newest provider contract's stable-lines inventory, with an
    emitting `file:line`. So a rule we put the fork on the hook for is one they
    have published, not one we believe they print.

    Measured 2026-08-21 against `round-12-lap-03-provider-contract-g8a1a3ee.md`:
    17 of 18 declarations backed, the one exception reasoned above. That included
    all six of the newly-confirmed rules — `consumer` `cyanrip_log.c:625`,
    `handshake_note` `:616`, `invoked_as` `:595`, `read_stalls` `:211`,
    `rip_completed` `:808`, `secure_rerip_converged` `cyanrip_main.c:954`.

    Both indented and column-0 candidates are tried, because a per-track row is
    printed indented and their inventory records the format string without its
    indentation — testing only the bare form would report every indented rule as
    an unbacked declaration.
    """
    import importlib.util

    from platterpus.parsers import cyanrip_log as parser_module

    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "emit_dependency_contract.py"
    )
    spec = importlib.util.spec_from_file_location("emit_dependency_contract", script)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)

    rows = _p2_rows()
    assert len(rows) >= 150, (
        f"only {len(rows)} rows read from their P2/P2a inventory (295 on "
        f"2026-08-21) — the row reader has stopped matching their table and every "
        f"declaration below would report as unbacked for the wrong reason"
    )

    patterns = {name: pattern for name, pattern, _ in generator._pattern_rows()}
    declared = sorted(generator._FORK_ONLY_RULES)
    assert len(declared) >= 18, (
        f"only {len(declared)} fork-only declarations; 18 existed on 2026-08-21"
    )

    unbacked: list[str] = []
    for name in declared:
        compiled = re.compile(patterns[name])
        if not any(
            compiled.match(candidate)
            for _where, fmt in rows
            for candidate in (_render(fmt), "  " + _render(fmt), "    " + _render(fmt))
        ):
            unbacked.append(name)

    surprises = sorted(set(unbacked) - set(_FORK_ONLY_WITHOUT_A_PUBLISHED_LITERAL))
    assert not surprises, (
        f"these rules are published as the fork's obligation but appear in no row "
        f"of their own stable-lines inventory ({CONTRACT.name}): {surprises}.\n"
        "Either the declaration is wrong — in which case we are asking another "
        "project to hold a line it does not emit, the `swap_addendum_crc` mistake "
        "again — or their contract has a gap, which is a round's question. Record "
        "which in `_FORK_ONLY_WITHOUT_A_PUBLISHED_LITERAL` with the cause; do not "
        "delete the assertion."
    )
    # And the exception list may not outlive its cause.
    stale = sorted(set(_FORK_ONLY_WITHOUT_A_PUBLISHED_LITERAL) - set(unbacked))
    assert not stale, (
        f"these exceptions are no longer needed — their contract now publishes a "
        f"literal for them: {stale}. Delete the rows."
    )
    # The parser is imported so a renamed rule fails here rather than silently
    # dropping out of `declared` (the set is checked against the parser elsewhere,
    # but this test's population comes from it and a floor on a shrunken set is not
    # the same guarantee).
    assert set(declared) <= {rule.name for rule in parser_module._ALL_LINE_RULES} | {
        name for name, _ in parser_module._SECTION_LINE_PATTERNS
    } | {name for name, _ in parser_module._INDENTED_LINE_PATTERNS}
