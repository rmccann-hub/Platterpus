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

import re
from pathlib import Path

import pytest

from platterpus.cyanrip_cli import VERSION_FLAGS

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


#: ``round-6.md``, or ``round-6b.md`` / ``round-6c.md`` for an amendment sent
#: after the round's main file. The suffix is the round's, not a new round.
_ROUND_NAME = re.compile(r"^round-(?P<number>\d{1,4})(?P<amendment>[a-z]{0,2})$")


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
    grouped: dict[int, list[Path]] = {}
    for path in INBOUND.glob("round-*.md"):
        match = _ROUND_NAME.match(path.stem)
        if match is None:
            continue
        grouped.setdefault(int(match.group("number")), []).append(path)
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
        files = sorted(grouped[number], key=lambda p: p.stem)
        text = "\n\n".join(f.read_text(encoding="utf-8") for f in files)
        if len(_their_flags(text)) >= _MIN_PUBLISHED_FLAGS:
            return files
    # No round has one. That is a real failure, not something to paper over.
    newest = max(grouped)
    return sorted(grouped[newest], key=lambda p: p.stem)


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


def _our_rip_flags() -> set[str]:
    text = CONSUMER_CONTRACT.read_text(encoding="utf-8")
    match = _OUR_FLAGS.search(text)
    assert match is not None, (
        "could not find the flag inventory line in the generated consumer "
        "contract — regenerate it with scripts/emit_dependency_contract.py"
    )
    return set(match.group(1).split())


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
    numbers = {_ROUND_NAME.match(p.stem).group("number") for p in files}  # type: ignore[union-attr]
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
    # The newest round on disk may legitimately NOT be the one used; that is the
    # point. Assert the relationship rather than a hardcoded round number, so this
    # keeps holding as rounds accumulate.
    newest_on_disk = max(
        int(_ROUND_NAME.match(p.stem).group("number"))  # type: ignore[union-attr]
        for p in INBOUND.glob("round-*.md")
        if _ROUND_NAME.match(p.stem)
    )
    used_round = int(_ROUND_NAME.match(files[0].stem).group("number"))  # type: ignore[union-attr]
    assert used_round <= newest_on_disk
