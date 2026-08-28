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

#: Paths whose *job* is to state what was true on a date. A historical mention of a
#: since-corrected flag is the record working, not drift, so these are skipped —
#: named as prefixes, and this is the only list in this file a human maintains.
DATED_RECORD: Final[tuple[str, ...]] = (
    "CHANGELOG.md",
    "docs/session-log.md",
    "docs/archive/",
    "docs/handshake/",
)


def _live_docs() -> list[str]:
    """Every live prose surface in the repo, **derived from disk**.

    **Why derived and not listed.** The first version of this gate hardcoded four
    paths — the three surfaces the 2026-08-18 correction had touched, plus the rig
    script. `PLANNING.md` was not among them, and it carried the sentence *"re-opening
    any of them is a fresh cyanrip task (e.g. `-x` overread)"* the whole time: the gate
    written to stop that exact sentence could not see the copy of it that already
    existed. A hand-maintained list of "the places this could go wrong" is a claim
    about a set nobody re-derives, and it decays invisibly — the same failure
    `CLAUDE.md` records for three completeness-promising maps in one sweep
    (`docs/testing.md` §5.af).

    So: sweep the tree, subtract the dated record, and let a new document be covered
    the day it is written rather than the day somebody remembers to add it here.
    """
    found: list[str] = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith((".git/", ".venv/", "node_modules/")):
            continue
        if any(rel == skip or rel.startswith(skip) for skip in DATED_RECORD):
            continue
        found.append(rel)
    return found


LIVE_DOCS: Final[tuple[str, ...]] = tuple(_live_docs())

#: ``-x`` as a standalone flag, not part of a longer token.
_DASH_X: Final[re.Pattern[str]] = re.compile(r"(?<![\w-])-x(?![\w-])")

#: What makes a line that pairs ``-x`` with "overread" a CORRECTION rather than the
#: defect: it names the right answer. The hazard table, the correction notices and the
#: whipper-origin explanation all have to write both words together to do their job —
#: and every one of them also says which flag overread actually is, or which tool the
#: ``-x`` spelling belongs to. A line that says the wrong thing never does.
#:
#: **This replaced a keyword list, and the swap is the point** (`CLAUDE.md`: *where a
#: check matches on a label, make it also require the subject*). The old version
#: exempted any line containing "previously", "conflat", "corrected"… — words that
#: describe the *shape* of a correction rather than its *content*, so it could be
#: satisfied by a sentence that apologised for the confusion and then repeated it.
#: Requiring the correct flag cannot be.
_NAMES_THE_RIGHT_ANSWER: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w-])-O(?![\w-])|cache[- ]probe|whipper", re.IGNORECASE
)


def _paragraph_around(lines: list[str], index: int) -> str:
    """The block of contiguous non-blank lines containing `lines[index]`.

    **Why a paragraph and not an N-line window.** Prose wraps: a blockquote in
    `docs/rig-scripts/README.md` names the defect on its first line and `-O` on its
    third, and a ±1 window would flag the first half of a sentence that is doing
    exactly its job. Picking a bigger N would fix that case and be arbitrary — the
    next correction that wraps to four lines fails again, and nobody would know why
    the number was three.

    A paragraph is the unit a correction is actually written in, so it is the unit the
    exemption is judged over. It is also *narrow* in the direction that matters: a
    defect sentence sitting in its own paragraph is never forgiven by a correct
    statement elsewhere on the page, which an ever-growing N eventually would.
    """
    start = index
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = index
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return "\n".join(lines[start : end + 1])


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

    lines = path.read_text(encoding="utf-8").splitlines()
    offenders: list[str] = []
    for index, line in enumerate(lines):
        if not (_DASH_X.search(line) and "overread" in line.lower()):
            continue
        if _NAMES_THE_RIGHT_ANSWER.search(_paragraph_around(lines, index)):
            continue
        offenders.append(f"{rel}:{index + 1}: {line.strip()[:120]}")
    assert not offenders, (
        "these lines pair `-x` with overread and never name the right answer. `-x` is "
        "the fork's CACHE PROBE; overread is `-O`, and `-O` hangs the BDR-209D for "
        "~23 minutes. If the line is a correction, say which flag overread IS (or "
        "which tool the `-x` spelling belongs to) in the same paragraph:\n  "
        + "\n  ".join(offenders)
    )


def test_the_paragraph_scope_forgives_a_wrapped_correction_and_nothing_further() -> (
    None
):
    """Both directions of the paragraph rule, because only the pair is a check.

    Forgiving too much is the failure mode that matters here: an exemption that
    reached across a blank line would let a page with one correct sentence at the
    top license every wrong one below it.
    """
    wrapped = [
        "> **⚠ Corrected. This said `-x` (force overread) has never run",
        "> on a real drive, which conflated two flags.** Overread is **`-O`**,",
        "> and it hung the BDR-209D for ~23 minutes.",
    ]
    assert _NAMES_THE_RIGHT_ANSWER.search(_paragraph_around(wrapped, 0)), (
        "a correction whose subject wraps to the next line is being flagged"
    )

    separated = [
        "Overread is `-O` and it hangs the BDR-209D.",
        "",
        "Enable `-x` force-overread and rip one track.",
    ]
    assert not _NAMES_THE_RIGHT_ANSWER.search(_paragraph_around(separated, 2)), (
        "a correct sentence in a DIFFERENT paragraph is exempting a defect — the "
        "exemption must not reach across a blank line"
    )


def test_the_sweep_actually_finds_the_documents() -> None:
    """A floor for the derivation. A sweep that returns nothing passes every case
    above while checking nothing — the "satisfied by finding nothing" shape.

    The named files are asserted individually because they are the surfaces that
    were actually wrong: three were in the old hardcoded list, and `PLANNING.md`
    is the one it missed.
    """
    docs = set(LIVE_DOCS)
    assert len(docs) >= 20, (
        f"the sweep found only {len(docs)} live docs: {sorted(docs)}"
    )
    for required in (
        "README.md",
        "TASKS.md",
        "PLANNING.md",
        "CLAUDE.md",
        "docs/dependency-contracts.md",
        "docs/rig-scripts/README.md",
        # The rig scripts moved INTO the package on 2026-08-28 so the running
        # program can open them. The sweep above is a whole-tree rglob, so it
        # followed them without being told; this named assertion is the half
        # that had to be moved by hand, and it is named precisely because it is
        # one of the surfaces that was actually wrong.
        "src/platterpus/rig_scripts/rigcancelandoverread.txt",
    ):
        assert required in docs, f"{required} fell out of the live-doc sweep"
    # ...and the dated record really is excluded, or the exclusion is decoration.
    assert "CHANGELOG.md" not in docs
    assert not [d for d in docs if d.startswith("docs/handshake/")]


def test_the_check_can_actually_fail() -> None:
    """Non-triviality, against constructed text — the detector must be able to fire.

    Every parametrised case above passes on a clean tree, which is also what a
    regex that matches nothing does. This pins both directions: the defect sentence
    is caught, and the three shapes that legitimately write both words are not.
    """
    defect = "1. `-x` (force overread) has NEVER run on a real drive."
    assert _DASH_X.search(defect) and "overread" in defect.lower()
    assert not _NAMES_THE_RIGHT_ANSWER.search(defect), (
        "the defect sentence must not be exempt"
    )

    # The shape the OLD keyword exemption let through, and the reason it was
    # replaced: it apologises for the confusion and then repeats it, naming no
    # correct flag anywhere. A check satisfiable by the wrong thing is worse than
    # one that fails, because a failure gets investigated and a pass gets cited.
    apologetic_defect = "Previously conflated, but corrected: `-x` is force-overread."
    assert not _NAMES_THE_RIGHT_ANSWER.search(apologetic_defect), (
        "a sentence that says 'corrected' and then states the wrong flag is being "
        "exempted — that is the keyword-matching failure this predicate replaced"
    )

    for allowed in (
        "| `-x` / `--force-overread` | overread | **whipper only** — never cyanrip |",
        "## ⚠ `-x` is the cache probe. `-O` is overread. Do not confuse them.",
        "# NOTE: -x here is the cache-probe. It is NOT overread. Overread is -O,",
    ):
        assert _NAMES_THE_RIGHT_ANSWER.search(allowed), (
            f"a line whose purpose is to forbid the pairing is being flagged: {allowed}"
        )
