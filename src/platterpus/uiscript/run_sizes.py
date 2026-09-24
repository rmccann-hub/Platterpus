"""Run sizes: Quick, Standard and Full, cut from ONE acceptance script.

**Why sizes exist.** The full acceptance run takes 4 to 6 hours and rips the disc
twice, which is the right price for evidence and the wrong one for "does it still
work after an update?". The maintainer asked for three levels (2026-09-24). Each
level answers one question:

* **Quick** (about 15 minutes): identity, settings, validation, dialogs, identify
  the disc, one short rip with its transcode and seam check, the preset and
  template round-trips, and the restore. *Does it still work?*
* **Standard** (about an hour): Quick plus the whole-disc rip on the defaults with
  every post-rip check, the overwrite prompt, a cancel and the recovery rip, and
  the two short ripper probes. *Is a normal rip right?*
* **Full** (4 to 6 hours): everything. **The only size that counts as evidence**
  toward a version gate or a handshake close.

**Why "size" and not "tier".** ``tier`` is already a word in this language, shared
with the cyanrip fork (round 18): it groups steps for dependency pruning. A second
meaning for it would be the collision round 18 was about.

**Nested by construction.** A section declares the SMALLEST size it belongs to, so
it runs in that size and every larger one. Quick is inside Standard and Standard
inside Full, and no script can make it otherwise, because there is nothing to
write that would express a section in Quick but not in Standard. Free per-section
checkboxes were considered and refused: each combination would be a new test
nobody had run before, and a pass on it would be evidence of nothing.

**A step left out by the size is DECLINED, not prevented** — ``SKIPPED`` in round
18's vocabulary, because the operator chose the smaller run. It is recorded, never
silently dropped, so a Quick transcript still shows every section it did not run.

Pure; no Qt.
"""

from __future__ import annotations

from typing import Final

QUICK: Final[str] = "quick"
STANDARD: Final[str] = "standard"
FULL: Final[str] = "full"

#: Smallest first. A size includes every section declared at its position or
#: before it.
ORDER: Final[tuple[str, ...]] = (QUICK, STANDARD, FULL)

#: What a run is when nobody chose: every step runs, as before sizes existed. A
#: hand-driven console run and ``--run-script`` both get this.
DEFAULT: Final[str] = FULL

#: The one size whose result may be counted toward a version gate or a handshake
#: close (`docs/testing.md` §5B).
EVIDENCE: Final[str] = FULL

#: The chooser's wording, in ORDER. The time is the measured order of magnitude,
#: not a promise; Full's is the figure the script's own header gives.
CHOICES: Final[tuple[tuple[str, str], ...]] = (
    (QUICK, "Quick — about 15 minutes: does it still work?"),
    (STANDARD, "Standard — about an hour: is a normal rip right?"),
    (FULL, "Full — 4 to 6 hours: the only run that counts as evidence"),
)


def parse_size(text: str) -> str | None:
    """The size named by ``text`` (case-insensitive), or ``None`` if it names none."""
    value = text.strip().lower()
    return value if value in ORDER else None


def includes(chosen: str, declared: str | None) -> bool:
    """Does a ``chosen`` run include a step declared for size ``declared``?

    ``None`` (a step before any ``run-size`` line) is in every size: the parts of a
    script that set it up must run whichever size was picked. An unknown value on
    either side is treated as FULL, the conservative reading: an unknown ``chosen``
    runs everything, and an unknown ``declared`` runs only in a full run.
    """
    if declared is None:
        return True
    chosen_rank = ORDER.index(chosen) if chosen in ORDER else len(ORDER) - 1
    declared_rank = ORDER.index(declared) if declared in ORDER else len(ORDER) - 1
    return declared_rank <= chosen_rank


def counts_as_evidence(chosen: str) -> bool:
    """Only a Full run may be counted toward a version gate or a handshake close."""
    return chosen == EVIDENCE
