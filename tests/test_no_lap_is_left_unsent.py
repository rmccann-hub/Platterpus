"""A lap that is written but never handed over is invisible to every other gate.

**The measurement this exists for.** Round 15 laps 4, 5 and 6 were written on
2026-09-02, -03 and -04 and **none of them was ever sent**, while the cyanrip
fork's lap 3 — a `GO`, asking nothing further — sat unanswered for two days.
Every gate in this repository was green throughout, because they all grade *files
in a directory* and a send is an event outside the tree.

`scripts/emit_envelope.py` made it worse than invisible. Its `PARTS` still pointed
at **round 14 lap 16**, and the envelope was regenerated four separate times in
one day — incidentally, because it also carries `fullacceptance.txt` — each run
reporting success while packing a round the fork closed weeks ago.

**This gate is the backstop, not the rule.** The rule is `CLAUDE.md`'s *ask before
writing a lap*, because only the maintainer can observe a send. A test can see a
lap accumulating unsent; it cannot ask a question.

**Scope: the CURRENT round only.** Closed rounds are history and their transport
is settled by the fact that the round closed — both sides declared a verdict, so
the laps crossed. Checking them would mean re-litigating settled correspondence
against a record (`SENT_LAPS`) that is deliberately incomplete.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
OUTBOUND: Final[Path] = REPO_ROOT / "docs" / "handshake" / "outbound"
EMITTER: Final[Path] = REPO_ROOT / "scripts" / "emit_envelope.py"

#: Laps of the current round that left WITHOUT the envelope, with the evidence.
#:
#: Deliberately NOT `SENT_LAPS`: that map pins the sha256 of the exact bytes handed
#: over, and pinning a value now would assert a byte-identity nobody measured at
#: the time. "We know it arrived" and "we know which bytes arrived" are different
#: claims and this file only makes the first.
#:
#: A ratchet: entries need a written reason naming what establishes the send, and
#: the list may shrink but should not grow casually — every addition is a lap that
#: went out unpacked, which is the shape the envelope exists to prevent.
SENT_OUTSIDE_THE_ENVELOPE: Final[dict[str, str]] = {
    "round-15-lap-02.md": (
        "The fork's lap 3 answers it directly — it quotes our lap 2's subject "
        "and declares GO on the pin lap 2 proposed — so it demonstrably arrived. "
        "Held at docs/handshake/inbound/round-15-lap-03.md."
    ),
}


def _current_round() -> int:
    """`CURRENT_ROUND`, read from the source text rather than by importing it.

    Importing `handshake.py` standalone fails on its dataclasses (the module is
    not registered in `sys.modules`, so `InitVar` resolution has nothing to look
    up), and the fixture that does it properly lives in another test file. Reading
    the literal is also the more honest thing here: this file is about what a
    reader of the source would conclude, and a `CURRENT_ROUND` computed at import
    time would itself be the finding.
    """
    text = (REPO_ROOT / "scripts" / "handshake.py").read_text(encoding="utf-8")
    match = re.search(r"^CURRENT_ROUND:\s*Final\[int\]\s*=\s*(\d+)", text, re.M)
    assert match, "CURRENT_ROUND is no longer a literal in scripts/handshake.py"
    return int(match.group(1))


def _packed_lap_names() -> set[str]:
    """Lap filenames named in the emitter's `PARTS`, read as source.

    Read as TEXT rather than by importing and inspecting the tuple: the point is
    what a reader of the file would see is being sent, and a `PARTS` assembled at
    import time from something dynamic is itself a finding.
    """
    text = EMITTER.read_text(encoding="utf-8")
    block = re.search(r"^PARTS: tuple\[Path, \.\.\.\] = \((.*?)^\)", text, re.S | re.M)
    assert block, "PARTS is no longer a literal tuple in emit_envelope.py"
    return set(re.findall(r'"(round-\d+-lap-\d+\.md)"', block.group(1)))


def test_no_lap_of_the_current_round_is_left_unsent() -> None:
    """Every outbound lap of the open round is packed, or recorded as gone.

    The floor is the lap count: a sweep whose population empties — the verb
    renamed, the directory moved, `PARTS` made dynamic — would otherwise pass by
    not looking, which is the failure mode this whole file is about.
    """
    number = _current_round()
    laps = sorted(OUTBOUND.glob(f"round-{number:02d}-lap-*.md"))
    assert len(laps) >= 2, (
        f"only {len(laps)} outbound lap(s) found for round {number} — the sweep "
        "has lost its population and is passing by not looking"
    )

    packed = _packed_lap_names()
    unsent = [
        lap.name
        for lap in laps
        if lap.name not in packed and lap.name not in SENT_OUTSIDE_THE_ENVELOPE
    ]

    # THE NEWEST LAP MAY BE PENDING. Exactly one, and only the highest-numbered.
    #
    # A lap written in this commit and about to be handed over is not
    # "accumulating" — and many laps legitimately travel BARE rather than in the
    # envelope (`emit_envelope.py`: *"a lap that only answers a lap would produce
    # a one-part envelope — pointless"*), so requiring every lap to be packed
    # would push us into building envelopes the convention says not to build.
    #
    # The defect this file exists for still fails: when lap 5 was written, lap 4
    # was already unaccounted, so two would be pending and only one is allowed.
    # Three stacked up in the real case. One is a hand-over in progress; two is
    # the failure.
    if unsent and unsent[-1] == laps[-1].name:
        unsent = unsent[:-1]

    assert not unsent, (
        f"these round-{number} laps are written but neither packed in the "
        f"envelope nor recorded as having left:\n  " + "\n  ".join(unsent) + "\n"
        "A lap nobody is carrying is a lap the peer is not reading, and the "
        "newest one is already excused as a hand-over in progress — so this is a "
        "lap that has been passed over. Either add it to `PARTS` in "
        "scripts/emit_envelope.py and regenerate, or — if it went out bare — "
        "record it in SENT_OUTSIDE_THE_ENVELOPE with the evidence."
    )


def test_the_envelope_leads_with_a_lap_of_the_CURRENT_round() -> None:
    """`PARTS[0]` names the envelope, so a stale lead names a stale envelope.

    This is the defect itself rather than its consequence: `PARTS[0]` sat on
    `round-14-lap-16.md` while round 15 ran, and four regenerations reported
    success. The generator cannot know a round has moved on; this can.
    """
    number = _current_round()
    text = EMITTER.read_text(encoding="utf-8")
    block = re.search(r"^PARTS: tuple\[Path, \.\.\.\] = \((.*?)^\)", text, re.S | re.M)
    assert block, "PARTS is no longer a literal tuple in emit_envelope.py"
    first = re.search(r'"(round-\d+-lap-\d+\.md)"', block.group(1))
    assert first, "PARTS[0] does not name a lap file"
    lead = first.group(1)
    assert lead.startswith(f"round-{number:02d}-"), (
        f"the envelope leads with {lead!r} while the open round is {number}. "
        "PARTS[0] is the OPERATIVE lap and names the file the operator sends, so "
        "this ships a round the peer has already closed — regenerating it will "
        "keep reporting success while it does."
    )
