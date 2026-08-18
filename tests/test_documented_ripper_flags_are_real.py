"""No live document may call ``-x`` "overread". It is a different flag, and a hazard.

**The failure this exists for, and it is a hardware hazard rather than a typo.**
``docs/dependency-contracts.md`` — the document ``CLAUDE.md`` names as *"the single
reference for allowable args/syntax/output per dependency"* — carries a block-quoted
⚠ warning, dated 2026-08-07, separating three flags that have all been called ``-x``:

============================  ==================================  ==================
flag                          what it does                        who has it
============================  ==================================  ==================
``-x`` / ``--cache-probe``    measure the drive's readback cache  the **fork**
``-O``                        overread into lead-in/lead-out      upstream + fork
``-x`` / ``--force-overread`` overread                            **whipper only**
============================  ==================================  ==================

Its own words: *"Getting these two confused is a hardware hazard rather than a
documentation nit… anyone who reads 'the previously-documented `-x`' and reaches for
the overread toggle on that drive loses the session."* ``-O`` is **confirmed to hang
the Pioneer BDR-209D for ~23 minutes** (real-hardware finding, 2026-07-22): 13 of 14
tracks ripped perfectly, then the last track's lead-out froze the bar near 100 %.

On 2026-08-18 that correction had still not reached the surfaces people act on:
``README.md``'s status paragraph, ``docs/rig-scripts/README.md`` — **one screen above
that same file's copy of the table** — and ``rigcancelandoverread.txt``, a *runnable*
script whose section C turned overread on for that exact drive, under the claim that
it "has never run on a real drive". Running it would have re-triggered a known hang
while proving nothing.

**Why no existing gate caught it.** ``test_dependency_contract_emitted.py`` checks the
*generated* consumer contract against the parser tables; ``test_argv_surface_agreement
.py`` checks our argv against the fork's published flag table. Neither reads
hand-written prose, so the wrong flag could sit in the README indefinitely and the
only cost was a lost hardware session.

**Why this is narrow on purpose.** The first version of this file also swept for *any*
short flag a doc attributed to cyanrip and compared it against the argv builder. It
produced three false positives immediately — ``cd-paranoia -A``, FLAC's ``-8 -V -j``,
and a shell ``rm -f`` — all on lines that merely *mention* cyanrip, because prose does
not say whose flag it is talking about. Making that pass would have meant an
allowlist of other tools' flags, which is an exemption list that grows until the check
means nothing. A check that must be defanged to stay green is worse than no check, so
what remains is the assertion that encodes the actual hazard and can be made exactly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
BACKEND: Final[Path] = (
    REPO_ROOT / "src" / "platterpus" / "adapters" / "cyanrip_backend.py"
)

#: Live surfaces — the ones a person acts on. Dated record (CHANGELOG, session log,
#: archive, handshake correspondence) is excluded deliberately: those state what was
#: true on a date, and a historical mention of a since-corrected flag is the record
#: working, not drift.
LIVE_DOCS: Final[tuple[str, ...]] = (
    "README.md",
    "TASKS.md",
    "docs/rig-scripts/README.md",
    "docs/rig-scripts/rigcancelandoverread.txt",
)

#: ``-x`` as a standalone flag, not part of a longer token.
_DASH_X: Final[re.Pattern[str]] = re.compile(r"(?<![\w-])-x(?![\w-])")

#: A line that says the pairing *in order to forbid it* is the fix, not the defect —
#: the hazard table, the correction notices, and the whipper-origin explanation all
#: have to write both words in one sentence to do their job.
_IS_A_CORRECTION: Final[re.Pattern[str]] = re.compile(
    r"whipper|corrected|conflat|previously|never cyanrip|cache probe|do not confuse",
    re.IGNORECASE,
)


def _flags_the_backend_emits() -> set[str]:
    """Every ``-X`` literal the cyanrip argv builder can append, read from source.

    Derived rather than listed, so a flag added to the builder is covered the day it
    lands. Read from the source text rather than by calling the builder because a
    flag is only emitted when its setting is on — one call proves nothing about the
    flags it *can* send.
    """
    found = set(re.findall(r'"(-[A-Za-z])"', BACKEND.read_text(encoding="utf-8")))
    return {flag.lstrip("-") for flag in found}


def test_overread_is_still_dash_o_in_the_argv_builder() -> None:
    """The anchor. Everything below is about ``-O`` being overread and ``-x`` not.

    Also a floor: if the source scan stops matching, this fails rather than quietly
    checking nothing.
    """
    emitted = _flags_the_backend_emits()
    assert len(emitted) >= 4, (
        f"only {sorted(emitted)} found in {BACKEND.name} — the argv builder's flag "
        f"literals have changed shape, so this file is checking nothing"
    )
    assert "O" in emitted, (
        "-O (overread) is no longer emitted by cyanrip_backend. If overread was "
        "renamed, every document naming it needs the same change and this test's "
        "premise needs rewriting."
    )
    assert "x" not in emitted, (
        "cyanrip_backend now emits -x. That is the fork's CACHE PROBE, which our "
        "argv has never contained — if this is deliberate, the hazard table in "
        "docs/dependency-contracts.md is out of date and must be updated first."
    )


@pytest.mark.parametrize("rel", LIVE_DOCS)
def test_no_live_doc_calls_dash_x_overread(rel: str) -> None:
    """``-x`` described as overread is the sentence that costs a hardware session."""
    path = REPO_ROOT / rel
    if not path.is_file():
        pytest.skip(f"{rel} is not present")

    offenders = [
        f"{rel}:{n}: {line.strip()[:120]}"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _DASH_X.search(line)
        and "overread" in line.lower()
        and not _IS_A_CORRECTION.search(line)
    ]
    assert not offenders, (
        "these lines call `-x` overread. `-x` is the fork's CACHE PROBE; overread is "
        "`-O`, and `-O` hangs the BDR-209D for ~23 minutes:\n  "
        + "\n  ".join(offenders)
    )


def test_the_check_can_actually_fail() -> None:
    """Non-triviality, against constructed text — the detector must be able to fire.

    Every parametrised case above passes on a clean tree, which is also what a
    regex that matches nothing does. This pins both directions: the defect sentence
    is caught, and the three shapes that legitimately write both words are not.
    """
    defect = "1. `-x` (force overread) has NEVER run on a real drive."
    assert _DASH_X.search(defect) and "overread" in defect.lower()
    assert not _IS_A_CORRECTION.search(defect), "the defect sentence must not be exempt"

    for allowed in (
        "| `-x` / `--force-overread` | overread | **whipper only** — never cyanrip |",
        "## ⚠ `-x` is the cache probe. `-O` is overread. Do not confuse them.",
        "This said `-x` force-overread until 2026-08-18, conflating two flags.",
    ):
        assert _IS_A_CORRECTION.search(allowed), (
            f"a line whose purpose is to forbid the pairing is being flagged: {allowed}"
        )
