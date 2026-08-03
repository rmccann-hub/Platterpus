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

#: The consumer contract's flag inventory line — a sorted space-separated list.
_OUR_FLAGS = re.compile(r"^(-[A-Za-z](?: -[A-Za-z])+)$", re.M)


def _newest_inbound() -> Path:
    rounds = sorted(
        INBOUND.glob("round-*.md"),
        key=lambda p: int(re.search(r"round-(\d+)", p.name).group(1)),  # type: ignore[union-attr]
    )
    assert rounds, "no inbound handshake rounds — nothing to check the argv against"
    return rounds[-1]


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
    their = _their_flags(_newest_inbound().read_text(encoding="utf-8"))
    ours = _our_rip_flags()

    # Floors. Either side coming back empty would make this pass vacuously, which
    # is exactly how the `-V` gap survived a round of "verification".
    assert len(their) >= 30, f"only parsed {len(their)} flags from P1 — regex is wrong"
    assert len(ours) >= 10, f"only parsed {len(ours)} flags from our contract"

    unknown = sorted(ours - their)
    assert not unknown, (
        f"we send flag(s) the ripper's own contract does not list: {unknown}. "
        f"Either the contract is stale or the flag is gone — and a flag that is "
        f"gone makes cyanrip exit 1 without ripping. Checked against "
        f"{_newest_inbound().name}."
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
    their = _their_flags(_newest_inbound().read_text(encoding="utf-8"))
    assert len(their) >= 30, f"only parsed {len(their)} flags from P1 — regex is wrong"

    listed = [f for f in VERSION_FLAGS if f in their]
    assert listed, (
        f"none of our version flags {list(VERSION_FLAGS)} appear in "
        f"{_newest_inbound().name}'s flag table. Every version probe would exit "
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
    their = _their_flags(_newest_inbound().read_text(encoding="utf-8"))
    assert flag in their, f"{flag} is not in {_newest_inbound().name}'s flag table"
