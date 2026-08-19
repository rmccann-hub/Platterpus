"""Catch a doc that *claims* a version it is no longer on.

The doc-stamp convention (`test_doc_version_stamps.py`) tracks **when a doc was
last edited**. It does not track whether the doc's *prose* makes a claim about
the current version — and those are different things. A doc nobody has touched
since v0.5.0 legitimately keeps a v0.5.0 stamp; that is the convention working.
But a doc that *says* "Status: v0.5.x — public pre-release" is making an
assertion about the present, and that assertion expires whether or not anyone
edits the file.

That is exactly how it slipped: the README still announced v0.5.x through the
whole v0.6.0 cycle, past a release, and the stamp gate had nothing to say
because the stamp was accurate. The maintainer caught it by reading the front
page — and noted it *"has happened many times"*, which is the real finding: a
convention that keeps failing is not a convention, it is a wish.

So this file is the gate in **both** directions:

* **§1 — no doc may claim a version older than the current one** (the bug
  above), and
* **§2 — bumping `__version__` forces the release-facing docs to follow.** The
  CHANGELOG must have a section and a compare link for the new version; the
  README's status banner and SECURITY.md's supported-versions line must name
  its minor. Miss any of them and the release goes red, before it ships rather
  than after someone reads the front page.

**Scope, deliberately narrow.** Only *user-facing* docs, and only patterns that
read as a claim about the current release — "Status: vX.Y", "latest released
`vX.Y.x` is supported". Historical prose ("this was the v0.5.8 crash", "New in
v0.5.0") is legitimate and common, so it is not matched: a check that fired on
every mention of an old version would be turned off within a week.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus import __version__

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: Docs a user or a would-be reporter reads to learn what the project *is* now.
#: Not CHANGELOG/session-log/PLANNING — those are records of the past, where an
#: old version number is the whole point.
USER_FACING_DOCS: tuple[str, ...] = ("README.md", "SECURITY.md")

#: Patterns that assert something about the CURRENT release. Each captures the
#: version it claims. Bounded quantifiers per the project rule.
_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "status banner",
        re.compile(r"\*\*Status:\s*v(?P<ver>\d{1,3}(?:\.\d{1,3}){0,2})", re.IGNORECASE),
    ),
    (
        "supported-versions statement",
        re.compile(
            r"latest released\s*`?v(?P<ver>\d{1,3}(?:\.\d{1,3}){0,2})", re.IGNORECASE
        ),
    ),
)


def _current_minor() -> tuple[int, int]:
    parts = __version__.split(".")
    return int(parts[0]), int(parts[1])


def _claimed_minor(text: str) -> tuple[int, int] | None:
    """(major, minor) from a claim like `0.5.x` / `0.6` / `0.6.1`."""
    bits = [b for b in text.split(".") if b.isdigit()]
    if len(bits) < 2:
        return None
    return int(bits[0]), int(bits[1])


@pytest.mark.parametrize("doc", USER_FACING_DOCS)
def test_no_user_facing_doc_claims_an_old_version(doc: str) -> None:
    """A "Status: vX.Y" that has fallen behind `__version__` is a lie on the
    front page, and the stamp gate cannot see it."""
    path = _REPO_ROOT / doc
    assert path.exists(), f"{doc} is missing"
    text = path.read_text(encoding="utf-8")
    current = _current_minor()

    stale: list[str] = []
    for label, pattern in _CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            claimed = _claimed_minor(match.group("ver"))
            if claimed is not None and claimed < current:
                stale.append(
                    f"{doc}: {label} claims v{match.group('ver')} but "
                    f"__version__ is {__version__}"
                )
    assert not stale, "; ".join(stale)


def test_the_patterns_actually_match_something() -> None:
    """A floor, and the one this check most needs.

    "No stale claims found" is satisfied perfectly by patterns that match
    nothing at all — which is what a reworded README would silently produce. So
    require that each pattern still finds its claim *somewhere* in the docs it
    polices.
    """
    corpus = "\n".join(
        (_REPO_ROOT / doc).read_text(encoding="utf-8") for doc in USER_FACING_DOCS
    )
    for label, pattern in _CLAIM_PATTERNS:
        assert pattern.search(corpus), (
            f"the '{label}' pattern matches nothing in {USER_FACING_DOCS} — "
            "either the wording changed (update the pattern) or the claim was "
            "removed (drop it). A pattern that cannot match cannot fail."
        )


def test_it_would_catch_the_bug_that_prompted_it() -> None:
    """Revert-proof, without editing the repo: feed the checker the exact text
    the README carried through the whole v0.6.0 cycle and confirm it fires."""
    was = "> **Status: v0.5.x — public pre-release.** Implemented end-to-end..."
    current = _current_minor()
    hits = [
        _claimed_minor(m.group("ver"))
        for _, pattern in _CLAIM_PATTERNS
        for m in pattern.finditer(was)
    ]
    assert hits, "the status-banner pattern no longer matches the historical text"
    assert any(h is not None and h < current for h in hits)


def test_the_readme_documents_every_cli_flag() -> None:
    """Every terminal flag the app accepts should be findable by a user reading
    the README, or it may as well not exist.

    Derived from `app.py`'s source rather than a hand-kept list, so adding a
    flag forces a README edit in the same change. Read from the source rather
    than by importing the parser because it is built inside `main()`, and
    refactoring an entry point to suit a test is the wrong trade — the harness
    should adapt to the product.
    """
    source = (_REPO_ROOT / "src" / "platterpus" / "app.py").read_text(encoding="utf-8")
    readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")

    flags = set(re.findall(r'add_argument\(\s*"(--[a-z][a-z0-9-]{1,30})"', source))
    assert len(flags) >= 5, f"only found {len(flags)} flags; the grep has drifted"

    # `--version` and `--uninstall` are documented by behaviour elsewhere in the
    # README; every diagnostic flag must appear verbatim.
    missing = sorted(f for f in flags if f not in readme)
    assert not missing, (
        f"CLI flags the README never mentions: {missing}. A flag a user cannot "
        "discover is a flag that does not exist for them."
    )


# --- §2: bumping the version forces the docs to follow -----------------------
#
# The recurring failure this file exists for. Each check below fails the moment
# `__version__` moves without its doc, so the version bump and the docs land in
# one change or not at all.

_CHANGELOG = _REPO_ROOT / "CHANGELOG.md"


def test_the_changelog_has_a_section_for_the_current_version() -> None:
    """A released version with no changelog section is a release nobody can
    read. `[Unreleased]` alone does not count — that is the *next* one."""
    text = _CHANGELOG.read_text(encoding="utf-8")
    heading = re.compile(rf"^##\s*\[{re.escape(__version__)}\]", re.MULTILINE)
    assert heading.search(text), (
        f"CHANGELOG.md has no '## [{__version__}]' section. Move the "
        "[Unreleased] entries under a dated heading before releasing."
    )


def test_the_changelog_has_a_compare_link_for_the_current_version() -> None:
    """The heading without the link renders as literal brackets on GitHub."""
    text = _CHANGELOG.read_text(encoding="utf-8")
    assert re.search(rf"^\[{re.escape(__version__)}\]:\s*http", text, re.MULTILINE), (
        f"CHANGELOG.md has no '[{__version__}]: https://…' compare link"
    )


def test_the_unreleased_compare_link_points_at_the_current_version() -> None:
    """`compare/v0.6.0...HEAD` after releasing 0.6.1 shows the wrong diff —
    a stale link that looks entirely plausible."""
    text = _CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        r"^\[Unreleased\]:\s*\S*compare/v(?P<ver>\S+?)\.\.\.HEAD", text, re.MULTILINE
    )
    assert match, "CHANGELOG.md has no [Unreleased] compare link"
    assert match.group("ver") == __version__, (
        f"[Unreleased] compares against v{match.group('ver')} but the current "
        f"version is {__version__}"
    )


@pytest.mark.parametrize("doc", USER_FACING_DOCS)
def test_each_release_facing_doc_names_the_current_minor(doc: str) -> None:
    """The positive form of §1: not merely "nothing stale", but "the current
    minor is actually stated". A README whose status banner was deleted would
    satisfy the negative check and tell the reader nothing.
    """
    text = (_REPO_ROOT / doc).read_text(encoding="utf-8")
    major, minor = _current_minor()
    assert re.search(rf"v{major}\.{minor}\b", text), (
        f"{doc} never mentions the current minor (v{major}.{minor}). Its "
        "version claim was removed or has fallen behind."
    )


def test_the_release_facing_docs_are_stamped_current() -> None:
    """These specific docs must carry the current stamp at release time,
    whether or not their body changed — they are the ones a user reads to learn
    what the project is *now*, so an old stamp on them reads as neglect even
    when it is technically accurate."""
    footer = re.compile(r"^\*Last updated for Platterpus v(\S+?)\.\*$", re.MULTILINE)
    stale = []
    for doc in USER_FACING_DOCS:
        found = footer.findall((_REPO_ROOT / doc).read_text(encoding="utf-8"))
        if not found:
            stale.append(f"{doc} (no footer)")
        elif found[0] != __version__:
            stale.append(f"{doc} (stamped v{found[0]})")
    assert not stale, (
        f"release-facing docs not stamped v{__version__}: {', '.join(stale)}"
    )


# --- §3 A version number must be backed by field evidence --------------------
#
# Maintainer ruling, 2026-08-19: the gate to 1.0.0 was implicitly "the suite is
# green", and that is a claim about this repository on a CI runner rather than
# about the software in somebody's hands. The thresholds and the reasoning live in
# `docs/testing.md` §5B; this is the half that runs.

_LEDGER_START = "<!-- FIELD-EVIDENCE-TABLE:"
_LEDGER_END = "<!-- END-FIELD-EVIDENCE-TABLE -->"

#: Distinct people / machines / distros a 1.0.0 claim needs. A floor, not a
#: target — raise it freely; it may not be lowered without the maintainer, since
#: lowering it is how a coverage bar becomes a formality.
MIN_PEOPLE_FOR_1_0: int = 2
MIN_MACHINES_FOR_1_0: int = 3
MIN_DISTROS_FOR_1_0: int = 3

#: Complete hardware passes a 0.9.1 claim needs. Two, because one is a data point
#: and two is the first evidence it was not luck.
MIN_FULL_GREEN_FOR_0_9_1: int = 2


def _version_tuple(text: str) -> tuple[int, int, int]:
    """(major, minor, patch) from a version string, ignoring any suffix."""
    parts = re.split(r"[^0-9]+", text.strip())
    nums = [int(p) for p in parts if p][:3]
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def _read_ledger() -> list[dict[str, str]]:
    """Parse the field-evidence table out of `docs/testing.md`. Never guesses.

    A row is only counted when it has the full column set, so a malformed line
    is dropped rather than silently contributing a blank machine or a blank
    verdict — which is how a coverage count gets inflated by a typo.
    """
    doc = (_REPO_ROOT / "docs" / "testing.md").read_text(encoding="utf-8")
    assert _LEDGER_START in doc and _LEDGER_END in doc, (
        "the field-evidence table is missing from docs/testing.md — the version "
        "gate has no input, and a gate with no input passes by finding nothing"
    )
    block = doc.split(_LEDGER_START, 1)[1].split(_LEDGER_END, 1)[0]
    rows: list[dict[str, str]] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        if cells[0] in {"date", "---"} or set(cells[0]) <= {"-"}:
            continue  # header or separator
        rows.append(
            dict(
                zip(
                    ("date", "version", "person", "machine", "distro", "result"),
                    cells,
                    strict=True,
                )
            )
        )
    return rows


def test_the_field_evidence_ledger_parses_and_is_not_empty() -> None:
    """The floor for the two gates below, and the reason they cannot be vacuous.

    Both gates count rows. A gate that counts rows in a table nobody can parse
    counts zero and — depending on which way the comparison runs — either fires
    constantly or never fires at all. So the parse is asserted separately, with a
    non-emptiness floor, before anything is concluded from the numbers.
    """
    rows = _read_ledger()
    assert rows, (
        "the field-evidence ledger parsed to ZERO rows. Either the table in "
        "docs/testing.md §5B is empty or its column layout changed and this "
        "parser no longer matches it."
    )
    assert all(r["result"] in {"full-green", "partial"} for r in rows), (
        "a ledger row carries a verdict outside {full-green, partial}: "
        f"{sorted({r['result'] for r in rows})}. An unrecognised verdict is not a "
        "pass, and spelling it freely is how one becomes one."
    )


def test_a_0_9_x_claim_needs_two_complete_hardware_passes() -> None:
    """0.9.1+ asserts "internally proven", which means EVERY test green, twice.

    "All at once" is the whole rule. A run of `pass=55 fail=5` whose five failures
    are each separately explained is not a pass — explaining a failure is how you
    fix it, not how you count it. Measured reason: the 2026-08-19 run's five
    failures all descended from ONE defect nobody knew existed, and a looser rule
    would have waved every one of them through as understood.
    """
    if _version_tuple(__version__) < (0, 9, 1):
        pytest.skip(f"v{__version__} makes no 0.9.x claim yet")
    passes = [r for r in _read_ledger() if r["result"] == "full-green"]
    assert len(passes) >= MIN_FULL_GREEN_FOR_0_9_1, (
        f"v{__version__} claims 0.9.1+ ('feature-complete and internally proven') "
        f"on {len(passes)} complete hardware pass(es); {MIN_FULL_GREEN_FOR_0_9_1} "
        "are required. Record them in docs/testing.md §5B, or drop the version "
        "back. See §5B for why two rather than one."
    )


def test_a_1_0_claim_needs_evidence_from_beyond_the_maintainers_rig() -> None:
    """1.0.0 asserts "ready for people who are not us", and that is a COVERAGE bar.

    It is the one threshold that more diligence here cannot clear: the maintainer's
    rig is one configuration out of every configuration a user might have. Written
    down rather than left to release-time judgement precisely because the
    temptation at 0.9.9 will be to reason that things seem fine.
    """
    if _version_tuple(__version__) < (1, 0, 0):
        pytest.skip(f"v{__version__} makes no 1.0 claim yet")
    rows = _read_ledger()
    people = {r["person"].lower() for r in rows}
    machines = {r["machine"].lower() for r in rows}
    distros = {r["distro"].lower() for r in rows}
    shortfalls = []
    if len(people) < MIN_PEOPLE_FOR_1_0:
        shortfalls.append(f"{len(people)} person/people (need {MIN_PEOPLE_FOR_1_0})")
    if len(machines) < MIN_MACHINES_FOR_1_0:
        shortfalls.append(f"{len(machines)} machine(s) (need {MIN_MACHINES_FOR_1_0})")
    if len(distros) < MIN_DISTROS_FOR_1_0:
        shortfalls.append(f"{len(distros)} distro(s) (need {MIN_DISTROS_FOR_1_0})")
    assert not shortfalls, (
        f"v{__version__} claims 1.0.0 — 'ready for people who are not us' — on "
        + ", ".join(shortfalls)
        + ". That is a coverage bar, not a quality bar: it moves only with other "
        "people's hardware. Record real runs in docs/testing.md §5B."
    )


def test_the_version_gates_can_actually_fail() -> None:
    """Non-triviality floor: both gates above SKIP at the current version.

    A skipped test is indistinguishable from a passing one in a summary, so the
    thresholds are exercised directly against a ledger that cannot satisfy them.
    Without this, a parser that returned `[]` forever would leave both gates
    green the day the version is bumped — the "satisfied by finding nothing"
    shape §5B was written to avoid.
    """
    empty: list[dict[str, str]] = []
    assert len([r for r in empty if r["result"] == "full-green"]) < (
        MIN_FULL_GREEN_FOR_0_9_1
    ), "an empty ledger must not satisfy the 0.9.1 bar"
    assert len({r["machine"] for r in empty}) < MIN_MACHINES_FOR_1_0, (
        "an empty ledger must not satisfy the 1.0.0 coverage bar"
    )
    # And the real ledger must not *already* satisfy 1.0 — if it did, the gate
    # would be decorative today and nobody would notice until it mattered.
    rows = _read_ledger()
    assert len({r["machine"].lower() for r in rows}) < MIN_MACHINES_FOR_1_0, (
        "the ledger already meets the 1.0 machine bar; either that is real (in "
        "which case raise the floor or delete this assertion deliberately) or a "
        "row is fabricated"
    )
