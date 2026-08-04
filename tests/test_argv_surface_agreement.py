"""Every flag we send must be a flag the ripper's published contract lists.

**This is the check that would have caught the ``-V`` blocker without reading a
line of cyanrip's source, and it did not exist.** The fork's ask J10, in their
words: *"you found it by reading genopt.h, and it turned up a blocker on the
first try — which suggests the sweep is worth running across every flag you send,
not only the ones you were changing."*

They are right, and the evidence is worse than that. Round 4's P1 table — a file
committed in this repo, which I said I had verified — lists ``-v`` / ``--version``
and contains **no ``-V`` row at all**. The information that our version probe was
about to break was in the artifact the whole time. I diffed their P2 log lines
against our parser and never diffed their P1 flags against our argv. A
verification that checks one half of a two-half contract is not a verification of
the contract.

So: mechanical, every commit, over the *whole* argv surface.

* **Their half** is P1, derived on their side from the binary's own ``--help``, so
  it cannot drift from what the build accepts.
* **Our half** is the generated consumer contract, derived from a real call to the
  argv builder plus the version-flag tuple, so it cannot drift from what we send.

Two independently generated descriptions of one seam. Where they disagree, the
disagreement is the bug report — the same reasoning both sides adopted for the
log-line half.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

from platterpus.cyanrip_cli import VERSION_FLAGS


def _handshake() -> ModuleType:
    """Load `scripts/handshake.py`, which owns the handshake filename convention.

    Loaded rather than re-implemented: the round/lap parser is the *definition* of the
    naming scheme, and a second copy here is a second description of one fact — the
    drift this repository has spent a whole round finding instances of. `scripts/` is
    not a package, hence the spec loader, which is the same shim
    `tests/test_handshake_tooling.py` uses.
    """
    script = Path(__file__).resolve().parents[1] / "scripts" / "handshake.py"
    spec = importlib.util.spec_from_file_location("handshake_naming", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parents[1]
INBOUND = REPO_ROOT / "docs" / "handshake" / "inbound"
CONSUMER_CONTRACT = REPO_ROOT / "docs" / "cyanrip-consumer-contract.md"

#: A P1 row: ``| `-d` | `--device` | Set device path … |``. The long column is
#: optional because older rounds published short flags only.
_P1_ROW = re.compile(
    r"^\|\s*`(?P<short>-[A-Za-z])`\s*\|(?:\s*`(?P<long>--[a-z-]+)`\s*\|)?", re.M
)

#: Below this many flags, a document is not publishing a flag table — it is
#: mentioning flags in prose. Their real tables carry 37-39 rows.
_MIN_PUBLISHED_FLAGS = 30

#: The consumer contract's flag inventory line — a sorted space-separated list.
#: The generated contract's flag-inventory line. Short **and long** options: the
#: emitter matched only `-X` until `--consumer` was added, so both the document and
#: this reader silently agreed to ignore a flag we really send. A reader as narrow
#: as the writer cannot detect the writer's narrowness.
_FLAG_TOKEN = r"--?[A-Za-z][\w-]*"
_OUR_FLAGS = re.compile(rf"^({_FLAG_TOKEN}(?: {_FLAG_TOKEN})+)$", re.M)


#: The handshake module, for its round parser and its ordering. **Imported, never
#: re-declared** — and importing the wrong function out of it is what broke this file.
#:
#: It used to bind `_ROUND_NAME`, the module's **grandfathered** `round-6` / `round-6b`
#: regex. That was correct until the 2026-08-04 migration renamed round 7 to
#: `round-07-lap-NN.md`, which `_ROUND_NAME` does not match at all — so **every one of
#: round 7's ten inbound laps became invisible to this test**, and it silently fell back
#: to diffing our argv against **round 6's** flag table. Measured, not inferred: the
#: label read `round-6.md + round-6b.md + round-6c.md` while the fork was on lap 21.
#:
#: That is the fourth place in this repo to grow its own round parser and the fourth to
#: break on the same migration. `round_number` accepts both name forms and `sort_key` is
#: the one ordering; nothing here re-spells either.
_HS = _handshake()

#: The oldest round whose flag table we are willing to check against. **A ratchet: it
#: may rise, never fall.**
#:
#: Falling back to an older table is legitimate — "the contract is unchanged" is a
#: complete answer and round 7 gave it — but *silently* falling back is not, because a
#: stale table is precisely how the ``-V`` blocker survived a round of verification.
_TABLE_ROUND_FLOOR: int = 6

#: How many rounds behind the newest inbound round the table we read may be. **Also a
#: ratchet, and it is currently 1 because that is the measured truth, not the goal.**
#:
#: Measured 2026-08-04: **none of round 7's twenty-one laps embeds a P1 flag table.**
#: Every one names ``PROVIDER-CONTRACT.md @ <commit>`` in *the fork's* repository, which
#: is not present here — so the newest flag table in this repo is **round 6b's**, and
#: the fork's own lap 21 §C3 reports their flag count moving 40 → 41 (``-j``), a change
#: this check structurally cannot see.
#:
#: Recorded as a number rather than left implicit because *a silent truncation reads as
#: completeness*: without this, the check reports agreement about a surface it is
#: reading from before the round opened. Asked for in lap 22 §C.
_MAX_TABLE_LAG: int = 1


def _group_by_round() -> dict[int, list[Path]]:
    """Inbound files grouped by round. **The one grouping, so a test can check it.**

    Extracted from :func:`_newest_round_files` because the regression test for the
    2026-08-04 naming migration first grew its *own* copy of this loop — and so passed
    with the broken version restored, since it was measuring itself rather than the
    thing that decides which table gets read. Identify the subject the way production
    identifies it.
    """
    grouped: dict[int, list[Path]] = {}
    for path in INBOUND.glob("round-*.md"):
        number = _HS.round_number(path)
        if number is None:
            continue
        grouped.setdefault(number, []).append(path)
    return grouped


def _newest_inbound_round() -> int:
    """The highest round number present in `inbound/`, by the shared round parser.

    Deliberately NOT read through :func:`_group_by_round` — this is the independent
    witness the grouping is checked against, and one function answering both questions
    is a check that can only agree with itself.
    """
    numbers = [
        n for p in INBOUND.glob("round-*.md") if (n := _HS.round_number(p)) is not None
    ]
    assert numbers, "no inbound handshake rounds on disk"
    return max(numbers)


def _newest_round_files() -> list[Path]:
    """Every inbound file belonging to the newest round, oldest first.

    **A round can arrive in several files, and the flag table need not be in all
    of them.** Round 6 came as a return file with the full P1 table, then two
    amendments: one withdrawing the pin, one a short pin-update note that mentions
    `-k` in prose without restating the table. Reading only the newest *file* saw
    the note and concluded the contract listed almost no flags — every rip flag we
    send failed at once, which reads like a catastrophic seam break rather than
    what it was.

    So the round is read as a set, exactly as `handshake.py --check` reads it.
    """
    grouped = _group_by_round()
    assert grouped, "no inbound handshake rounds — nothing to check the argv against"

    # Walk BACK to the newest round that actually publishes a flag table.
    #
    # "The contract is unchanged" is a legitimate and complete answer — round 7
    # gave it, in prose (§9: everything else unchanged from round 6b), and omitted
    # the provider contract entirely. Keying strictly on the newest round then
    # parsed a file with no P1 table, found almost no flags, and failed every rip
    # flag at once: a total-seam-break signature for a round that had simply not
    # restated something that had not moved.
    #
    # Falling back is not a weakening. The table we check against is still the
    # newest one that exists, and `_newest_inbound_label()` names it, so a reader
    # of a failure knows which round's contract was used. What we must never do is
    # silently check against *nothing*, which is what the floor below prevents.
    for number in sorted(grouped, reverse=True):
        files = sorted(grouped[number], key=_HS.sort_key)
        text = "\n\n".join(f.read_text(encoding="utf-8") for f in files)
        if len(_their_flags(text)) >= _MIN_PUBLISHED_FLAGS:
            return files
    # No round has one. That is a real failure, not something to paper over.
    newest = max(grouped)
    return sorted(grouped[newest], key=_HS.sort_key)


def _newest_inbound_text() -> str:
    return "\n\n".join(p.read_text(encoding="utf-8") for p in _newest_round_files())


def _newest_inbound_label() -> str:
    return " + ".join(p.name for p in _newest_round_files())


def _their_flags(text: str) -> set[str]:
    """Every flag spelling the provider contract publishes, short and long."""
    flags: set[str] = set()
    for m in _P1_ROW.finditer(text):
        flags.add(m.group("short"))
        if m.group("long"):
            flags.add(m.group("long"))
    return flags


#: Flags whose absence from the published table is EXPECTED, not a finding.
#:
#: ``VERSION_FLAGS`` is a *fallback tuple*, tried in order until one exits 0, and
#: the whole point of having more than one entry is that no single flag works on
#: every build: upstream moved version reporting from ``-V`` to ``-v`` after 0.9.3,
#: and the fork re-added ``-V``. So "every flag we send must be in their table" is
#: the wrong assertion for these — the right one is
#: :func:`test_at_least_one_version_flag_is_in_their_table` below, which is what
#: actually protects the probe.
#:
#: Nothing else goes in here. `--verify-log` is deliberately NOT exempt: it is a
#: single flag with no fallback, so if their table stops listing it we want to hear
#: about it before a rip does.
_PROBE_FALLBACK_FLAGS: frozenset[str] = frozenset(VERSION_FLAGS)


def _our_flags() -> set[str]:
    """Every flag the generated contract says we send — rips AND probes.

    The contract enumerates the whole argv surface on purpose: *"a dependency's own
    flags are a validated surface, not trivia"*, and a probe invocation is as much a
    thing we send as a rip is.
    """
    text = CONSUMER_CONTRACT.read_text(encoding="utf-8")
    match = _OUR_FLAGS.search(text)
    assert match is not None, (
        "could not find the flag inventory line in the generated consumer "
        "contract — regenerate it with scripts/emit_dependency_contract.py"
    )
    return set(match.group(1).split())


def _our_rip_flags() -> set[str]:
    """The subset that must appear in their table, one for one.

    Excludes only the version-probe fallback tuple, for the reason on
    :data:`_PROBE_FALLBACK_FLAGS`. Kept as a *derived* set rather than a second
    hand-written list so a new flag is covered by default — the safe direction, and
    the opposite of the hand-maintained allowlist that hid 16 of the fork's fatal
    strings in round 5.
    """
    return _our_flags() - _PROBE_FALLBACK_FLAGS


def test_every_rip_flag_we_send_is_in_the_providers_published_contract() -> None:
    """The rip argv, mechanically diffed against P1."""
    their = _their_flags(_newest_inbound_text())
    ours = _our_rip_flags()

    # Floors. Either side coming back empty would make this pass vacuously, which
    # is exactly how the `-V` gap survived a round of "verification".
    assert len(their) >= _MIN_PUBLISHED_FLAGS, (
        f"only parsed {len(their)} flags from P1 — regex is wrong"
    )
    assert len(ours) >= 10, f"only parsed {len(ours)} flags from our contract"

    unknown = sorted(ours - their)
    assert not unknown, (
        f"we send flag(s) the ripper's own contract does not list: {unknown}. "
        f"Either the contract is stale or the flag is gone — and a flag that is "
        f"gone makes cyanrip exit 1 without ripping. Checked against "
        f"{_newest_inbound_label()}."
    )


def test_every_version_flag_we_probe_with_is_in_the_published_contract() -> None:
    """THE ONE THAT MATTERED, generalised.

    A version probe is not part of the rip argv, so the rip-flag sweep above
    would not have caught ``-V``. It gets its own assertion because the failure
    mode is uniquely bad: a rejected version flag exits non-zero, which every
    probe in this codebase is built to read as *"the tool is not installed"* — so
    the app reports a working ripper missing.

    At least ONE spelling must be listed. Not all of them: the tuple deliberately
    spans builds, and an older build's spelling is expected to be absent from a
    newer contract. What is not acceptable is *none* of them being listed, which
    would mean we cannot ask this binary its version at all.
    """
    their = _their_flags(_newest_inbound_text())
    assert len(their) >= _MIN_PUBLISHED_FLAGS, (
        f"only parsed {len(their)} flags from P1 — regex is wrong"
    )

    listed = [f for f in VERSION_FLAGS if f in their]
    assert listed, (
        f"none of our version flags {list(VERSION_FLAGS)} appear in "
        f"{_newest_inbound_label()}'s flag table. Every version probe would exit "
        f"non-zero and the app would report cyanrip missing. Flags the contract "
        f"does list: {sorted(their)}"
    )


def test_the_probe_exemption_is_only_the_version_fallback_tuple() -> None:
    """An exemption list that grows is the rule being retired one flag at a time.

    `VERSION_FLAGS` is exempt from the one-for-one check for a real reason (it is a
    fallback tuple; no single entry works on every build). Nothing else has that
    property, and in particular `--verify-log` must NOT drift in here: it is a
    single flag with no fallback, so their table dropping it is a finding we want
    before a rip discovers it.

    This is the counter to the round-5 lesson from the other side — a hand-maintained
    allowlist in their generator hid 16 fatal strings, and the list was consistent
    with itself the whole time.
    """
    from platterpus.cyanrip_cli import VERIFY_LOG_FLAG

    assert _PROBE_FALLBACK_FLAGS == frozenset(VERSION_FLAGS)
    assert VERIFY_LOG_FLAG not in _PROBE_FALLBACK_FLAGS
    assert VERIFY_LOG_FLAG in _our_rip_flags(), (
        "--verify-log is not in the checked set, so their table could drop it "
        "silently and every rip's log verification would report 'not determined'"
    )
    # And the exemption actually removes something, or it is decoration.
    assert _our_flags() - _our_rip_flags(), "the exemption excludes nothing"


def test_the_contract_enumerates_probes_not_only_the_rip() -> None:
    """The generated contract must describe the WHOLE argv surface.

    A renamed flag is indistinguishable from an absent tool — that is how upstream's
    `-V` removal turned a working fork build into "cyanrip is not installed" — so a
    contract that documented only the rip left our two most failure-prone
    invocations undescribed. Both probes are now derived from the same constants the
    code uses, not restated.
    """
    from platterpus.cyanrip_cli import VERIFY_LOG_FLAG

    ours = _our_flags()
    assert VERIFY_LOG_FLAG in ours, (
        "the contract does not mention --verify-log, which we run after every rip"
    )
    assert ours & frozenset(VERSION_FLAGS), (
        "the contract does not mention any version flag, which we run at launch"
    )
    # Rip flags are still there — this is an addition, not a replacement.
    for rip_flag in ("-d", "-N", "-o"):
        assert rip_flag in ours, rip_flag


def test_the_sweep_can_actually_fail() -> None:
    """A detector that cannot fail is decoration.

    Proven against a constructed contract rather than by reasoning: this is the
    exact shape of the round-4 P1 that lacked ``-V``, and the helper must not
    report it as containing one.
    """
    p1_without_V = (
        "| `-h` | `--help` | Print this text |\n"
        "| `-v` | `--version` | Print the version number |\n"
        "| `-d` | `--device` | Set device path |\n"
    )
    parsed = _their_flags(p1_without_V)
    assert parsed == {"-h", "--help", "-v", "--version", "-d", "--device"}
    assert "-V" not in parsed, "the parser is case-insensitive — it would miss this"


@pytest.mark.parametrize("flag", sorted(_our_rip_flags()))
def test_each_rip_flag_individually(flag: str) -> None:
    """Same assertion, one test per flag, so a failure names the flag in its own
    test id rather than burying it in a list."""
    their = _their_flags(_newest_inbound_text())
    assert flag in their, f"{flag} is not in {_newest_inbound_label()}'s flag table"


def test_a_round_is_read_as_a_set_of_files_not_only_its_newest() -> None:
    """The regression test for reading one file when a round arrived as three.

    Round 6 came as `round-6.md` (with the full P1 table), `round-6b.md` (the pin
    withdrawal) and `round-6c.md` (a short pin note mentioning `-k` in prose).
    Keying on the newest *file* parsed the note, found almost no flags, and failed
    every rip flag at once — a total-seam-break signature for what was actually a
    file-selection bug. The floor below is what makes that impossible to repeat.
    """
    files = _newest_round_files()
    assert files, "no round files found"
    # Every file in the set belongs to the same round.
    numbers = {_HS.round_number(p) for p in files}
    assert len(numbers) == 1, f"files from different rounds grouped together: {files}"
    # And the union clears the flag floor even when the newest file alone does not,
    # which is the whole point. Asserted as a comparison so it cannot pass by the
    # amendment happening to contain a table.
    union = _their_flags(_newest_inbound_text())
    newest_alone = _their_flags(files[-1].read_text(encoding="utf-8"))
    assert len(union) >= _MIN_PUBLISHED_FLAGS, (
        f"the round's union lists only {len(union)} flags"
    )
    assert len(union) >= len(newest_alone), (
        "reading the whole round found fewer flags than its newest file — the "
        "union is losing information"
    )


def test_a_round_that_says_the_contract_is_unchanged_does_not_break_the_check() -> None:
    """Round 7's regression.

    "The contract is unchanged" is a complete answer, and round 7 gave it in prose
    while omitting the provider contract entirely. Keying strictly on the newest
    round then parsed a file with no flag table and failed *every* rip flag at
    once — which reads as a catastrophic seam break rather than as a round that
    did not restate something that had not moved.

    Asserted two ways so this cannot pass vacuously: the table actually used must
    clear the published-table floor, and the label must name a round that has one.
    """
    files = _newest_round_files()
    assert files, "no round files found"
    used = _their_flags(_newest_inbound_text())
    assert len(used) >= _MIN_PUBLISHED_FLAGS, (
        f"fell back to a document with only {len(used)} flags — the fallback found "
        "no published table at all"
    )
    # And it is honest about which round it read, so a failure is diagnosable.
    label = _newest_inbound_label()
    assert "round-" in label
    # **The assertion here used to be `used_round <= newest_on_disk`, which CANNOT
    # FAIL** — the used round is drawn from the on-disk set, so it is ≤ the maximum by
    # construction. *"Can this check be satisfied by finding nothing?"* It could be
    # satisfied by anything at all. Worse, both sides of it were computed with
    # `_ROUND_NAME`, the grandfathered regex, so `newest_on_disk` read **6** while
    # round 7 was on lap 21 — the test written to catch the fallback going stale had
    # inherited the same blind spot as the code it was checking, which is the
    # shared-ancestor failure this project has now hit from a fourth direction.
    #
    # Replaced with a RATCHET: the table actually used may not come from a round older
    # than `_TABLE_ROUND_FLOOR`, and the gap to the newest inbound round is asserted
    # against a recorded number so it can shrink but never silently grow.
    used_round = _HS.round_number(files[0])
    assert used_round is not None
    assert used_round >= _TABLE_ROUND_FLOOR, (
        f"the flag table is being read from round {used_round}, older than the "
        f"recorded floor {_TABLE_ROUND_FLOOR} — the input half of the seam has gone "
        f"backwards. Label: {label}"
    )
    assert _newest_inbound_round() - used_round <= _MAX_TABLE_LAG, (
        f"the newest inbound round is {_newest_inbound_round()} but the flag table "
        f"read is round {used_round}'s — a lag of "
        f"{_newest_inbound_round() - used_round}, past the recorded "
        f"{_MAX_TABLE_LAG}. Ask the fork to publish the P1 table (or commit "
        f"PROVIDER-CONTRACT.md here) for the current round: an argv check against a "
        f"stale table is how the -V blocker survived a round of 'verification'."
    )


def test_the_round_grouping_can_see_the_NEWEST_inbound_round() -> None:
    """**REGRESSION for the naming migration, and the bug was in this file.**

    `_newest_round_files` grouped with `handshake._ROUND_NAME` — the *grandfathered*
    `round-6` / `round-6b` regex, which does not match `round-07-lap-16.md` at all. So
    from 2026-08-04 every one of round 7's inbound laps was **invisible** to the argv
    check, and it fell back to round 6's table without saying so.

    It happened to reach the same table the fixed code reaches, because none of round
    7's laps publishes a P1 table — so nothing failed, and nothing could have. That is
    the point: *a difference that changes no observable behaviour today is invisible to
    every test either side can write.*

    Asserted as "the grouping sees the newest round", not "the newest round is used" —
    falling back to an older table is legitimate (a round may say the contract is
    unchanged); being unable to *see* the newest round is not.
    """
    newest = _newest_inbound_round()
    grouped = set(_group_by_round())
    assert newest in grouped, (
        f"round {newest} is on disk but the grouping cannot see it — the round parser "
        f"here does not understand the current filename convention. Sees: "
        f"{sorted(grouped)}"
    )
    # A floor, or this passes on a directory holding one grandfathered file.
    canonical = [p for p in INBOUND.glob("round-*.md") if _HS.name_round_and_lap(p)]
    assert len(canonical) >= 5, (
        f"only {len(canonical)} canonically-named inbound files — with too few, the "
        "grandfathered regex would have worked and this test proves nothing"
    )
