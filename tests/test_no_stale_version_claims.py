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
* **§4 — the front page's FACTS, not merely its version number**: the pin it
  says is installed, and whether it asserts a handshake round is open. Added
  2026-08-27 after the README was found stale with every existing gate green.
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


def test_every_compare_link_POINTS_AT_THE_VERSION_IT_LABELS() -> None:
    """A link that exists is not a link that goes anywhere.

    **The check above asks whether a compare link is PRESENT and never where it
    goes** — *"can this check be satisfied by the wrong thing?"* — and on
    2026-09-06 it was. Restamping the docs with a blanket replace of `v0.6.39`
    turned `[0.6.40]: …/compare/v0.6.39...v0.6.40` into
    `…/compare/v0.6.40...v0.6.40`: a link from a version to itself, which GitHub
    renders as an **empty diff**, under a heading listing that release's changes.
    Every existing gate passed. Proved by the revert probe rather than assumed —
    reintroducing the bad link left the whole file green.

    The sweep also found one **pre-existing** row: `[0.2.0]` pointed at
    `v0.1.0...v0.2.1`, the line above it copied, so that entry had always linked to
    the next version's diff.

    **What this does NOT check, said plainly:** whether the tags exist. They do not
    below `v0.6.4` — the project's first 39 tags start there — so every early link
    is dead regardless of its labelling, and pretending otherwise would be a second
    false claim. This is an internal-consistency check: the label and the target
    name the same version, and no link compares a version with itself.
    """
    text = _CHANGELOG.read_text(encoding="utf-8")
    rows = re.findall(r"^\[([^\]]+)\]:\s*(\S+)\s*$", text, re.MULTILINE)
    # FLOOR. A regex that stopped matching would make this pass by sweeping an
    # empty set, which is the shape this whole file is written against.
    assert len(rows) >= 100, (
        f"only {len(rows)} link row(s) parsed from CHANGELOG.md; the format changed "
        "or the pattern broke, and those are different findings"
    )

    problems: list[str] = []
    compared = 0
    for label, url in rows:
        match = re.search(r"/compare/v?(?P<lo>.+?)\.\.\.v?(?P<hi>.+)$", url)
        if match is None:
            continue  # a /releases/tag/… row: nothing to compare
        compared += 1
        lo, hi = match.group("lo"), match.group("hi")
        if lo == hi:
            problems.append(f"[{label}] compares {lo} with itself — an empty diff")
        elif label == "Unreleased":
            if hi != "HEAD":
                problems.append(f"[Unreleased] must end at HEAD, ends at {hi}")
        elif hi != label:
            problems.append(f"[{label}] is labelled {label} but ends at {hi}")

    assert compared >= 100, (
        f"only {compared} compare link(s) examined; the URL shape changed"
    )
    assert not problems, "malformed compare links:\n  " + "\n  ".join(problems)


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

#: Distinct machines and distros a 0.9.1 claim ALSO needs (maintainer ruling,
#: 2026-09-13): *"me passing full tests, even if different, on the same version of
#: linux and hardware should not allow a 0.9.1"*.
#:
#: **The rule genuinely changed here — this was not a restatement.** Until today
#: §5B put every diversity clause on 1.0.0 and 0.9.1 was a pure count, so two
#: green sheets from one rig satisfied *"feature-complete and internally proven"*.
#: Two passes on one machine and one distro measure the same configuration twice:
#: they are evidence against luck, which is what the count was for, and no
#: evidence at all against *"green because of something true only of this rig"*.
#:
#: Deliberately BELOW the 1.0.0 floors (2 people / 3 machines / 3 distros) so the
#: two bars stay distinct. Collapsing them would delete the intermediate
#: milestone, which is the failure mode of tightening a gate by copying the next
#: one up.
MIN_MACHINES_FOR_0_9_1: int = 2
MIN_DISTROS_FOR_0_9_1: int = 2


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
    shortfalls: list[str] = []
    if len(passes) < MIN_FULL_GREEN_FOR_0_9_1:
        shortfalls.append(
            f"{len(passes)} complete pass(es), need {MIN_FULL_GREEN_FOR_0_9_1}"
        )
    # DIVERSITY IS COUNTED OVER THE FULL-GREEN ROWS, not over the whole ledger.
    #
    # The 1.0.0 gate below counts across every row including `partial` ones, and
    # that is right for it: a partial run on someone else's machine is still
    # evidence that someone else's machine was tried. It is NOT right here. This
    # bar is about the passes themselves, so a second machine that only ever
    # produced a partial must not satisfy it — that would let a green sheet from
    # one rig borrow coverage from a failure on another.
    machines = {r["machine"].lower() for r in passes}
    distros = {r["distro"].lower() for r in passes}
    if len(machines) < MIN_MACHINES_FOR_0_9_1:
        shortfalls.append(
            f"{len(machines)} machine(s) among the passes, "
            f"need {MIN_MACHINES_FOR_0_9_1}"
        )
    if len(distros) < MIN_DISTROS_FOR_0_9_1:
        shortfalls.append(
            f"{len(distros)} distro(s) among the passes, need {MIN_DISTROS_FOR_0_9_1}"
        )
    assert not shortfalls, (
        f"v{__version__} claims 0.9.1+ ('feature-complete and internally proven') "
        "on " + "; ".join(shortfalls) + ". Two passes on ONE machine and ONE "
        "distro measure the same configuration twice — evidence against luck, "
        "and none against 'green because of something true only of this rig' "
        "(maintainer ruling, 2026-09-13). Record real runs in docs/testing.md "
        "§5B, or drop the version back."
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
    # THE REAL LEDGER MUST NOT ALREADY SATISFY 0.9.1 EITHER. Without this the
    # diversity clause added on 2026-09-13 could be silently vacuous: the gate
    # skips below 0.9.1, so nothing would notice if it were satisfiable today.
    real_passes = [r for r in _read_ledger() if r["result"] == "full-green"]
    assert (
        len(real_passes) < MIN_FULL_GREEN_FOR_0_9_1
        or len({r["machine"].lower() for r in real_passes}) < MIN_MACHINES_FOR_0_9_1
        or len({r["distro"].lower() for r in real_passes}) < MIN_DISTROS_FOR_0_9_1
    ), (
        "the ledger ALREADY satisfies the 0.9.1 bar, so that gate can no longer "
        "fail and is not testing anything. Either the bar needs raising or the "
        "version needs bumping — but it must not sit satisfied and skipped."
    )
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


# =============================================================================
# §4 — the front page's FACTS, not just its version number
# (§3 is the field-evidence ledger, above. This was numbered §3 when it landed
#  in 4d85884 — a collision in the same file, found by the doc audit an hour
#  later. Section numbers in a 700-line file are exactly the kind of fact that
#  is easier to duplicate than to notice.)
# =============================================================================
# **Why this section exists, and why it belongs in THIS file rather than a new
# one.** On 2026-08-27 the maintainer read the README and found it out of date.
# Every existing gate was green:
#
#   * the doc-stamp gate passed, because the stamp really was v0.6.30 — the file
#     HAD been edited (restamped) in the release commit. A stamp records *when a
#     doc was edited*, so an accurate stamp beside stale prose is exactly what it
#     is designed to report.
#   * §1 above passed, because it compares MINORS: `_current_minor()` returns
#     (0, 6) and `_claimed_minor("0.6.27")` also returns (0, 6), so
#     `(0,6) < (0,6)` is False. That is defensible as designed — the bug §1 was
#     built for was v0.5.x surviving the whole v0.6 line — but it is structurally
#     blind to patch-level drift.
#
# Meanwhile the status banner said three things that were false: the version, the
# handshake round state ("round 14 is open" — it had closed), and which cyanrip
# build gets installed (`ddf7ac3`, three pins behind `d9c058c`). Two of those
# three are DERIVABLE FROM CODE with no judgement at all, which makes them
# checkable rather than merely reviewable.
#
# So this is the same move made in `fork_source` on the same day, extended to the
# front page: **one predicate, N callers.** The README does not get to hold its
# own opinion about whether a round is open, any more than three code paths did.
#
# Scope is deliberate, and stated rather than implied: only *present-tense claims
# about the current state* in the user-facing docs. A CONDITIONAL ("no release
# while a round is open") is a rule and is correct; historical prose ("round 8
# approved `ddf7ac3`") is a record and is correct. Both are common in this repo
# and a check that fired on them would be switched off within a week.

#: Pins that were once ours and are not now. Derived where it can be —
#: `FORK_PIN` and `FORK_TEST_PIN` are read from the module — with the retired
#: ones listed because there is nowhere else they survive. A pin joins this list
#: when it is superseded; it never leaves.
_RETIRED_PINS: tuple[str, ...] = (
    "ddf7ac3",  # 0.9.4-rc1+platterpus.5, round 7/8 era
    "2f950c8",  # round 6
    "c4d1a00",  # the fork's stable during round 11
    "9003e6f",  # the v0.6.4b1 test pin
    "c455683",  # round 11's pin
    "104f6d4",  # withdrawn
)

#: A present-tense claim that a particular ripper build is what gets installed.
#: Anchored on the verbs the README actually uses, so it cannot fire on prose
#: describing what a past round approved.
#:
#: **The window excludes only the newline, NOT the full stop.** The first version
#: used `[^.\n]{0,120}`, which stops at the first `.` — and a cyanrip version is
#: `0.9.4-rc2+platterpus.10`, so the capture died at "installs cyanrip `0" and the
#: pin was never in the window. The non-triviality test below caught it against
#: the real shipped text, which is the only reason it is not still there.
#:
#: **THE WINDOW HAS NOW BEEN TOO NARROW THREE TIMES, EACH TIME DIFFERENTLY.**
#: `[^.\n]` died at the version string's first full stop. `[^\n]` died at the
#: README's hard wrap, because the claim and its sha sit on different lines — and
#: `scripts/revert_probe.py` reported that one VACUOUS rather than letting it
#: pass as a guard. Both were found by a tool, not by reading the regex. The
#: window now crosses a single newline and stops at a blank line, because a
#: paragraph break means a different subject.
#:
#: **"should report" is the same class of claim and so is in the same pattern.**
#: README line 283 told a user `cyanrip --version` *"should report something
#: like"* a banner three pins old. It reads as an example, but a user who runs
#: the command today sees a different string and has no way to know which of
#: them is wrong — so it is a present-tense claim about the current build, and
#: it is derivable from `FORK_EXPECTED_BANNER` like the rest.
_INSTALL_CLAIM = re.compile(
    r"(?:This build (?:still )?installs|installs cyanrip|the pin is|pinned to"
    r"|should report(?: something like)?)\s+"
    # Crosses a SINGLE newline but never a blank line: the README hard-wraps at
    # ~80 columns, so a claim and its sha routinely sit on different lines, while
    # a paragraph break means a different subject.
    r"(?:[^\n]|\n(?!\n)){0,140}",
    re.IGNORECASE,
)


def _pin_token_pattern() -> re.Pattern[str]:
    """A short sha in either form this project actually writes it.

    TWO forms, and missing the second made the guard vacuous on the very line it
    was widened for. `(`ddf7ac3`)` is the bare-sha form used in the status
    banner; `platterpus-fork-gddf7ac3` is the BUILD TAG form used wherever a
    cyanrip banner is quoted — and the sha there is preceded by the branch name,
    not by a backtick.

    The branch prefix is read from `fork_source.FORK_BRANCH` rather than typed, so
    a fork rename cannot silently switch this check off.
    """
    from platterpus.deps.fork_source import FORK_BRANCH

    return re.compile(
        rf"(?:{re.escape(FORK_BRANCH)}-g|[`(]{{1,2}})(?P<sha>[0-9a-f]{{7}})"
    )


#: Built once; the branch name is a module constant, not a runtime value.
_PIN_TOKEN = _pin_token_pattern()


def _claimed_install_pin(claim: str) -> str | None:
    """The FIRST sha-looking token in an install claim — its subject.

    Taking the first rather than any is what keeps this precise in both
    directions. *"installs `d9c058c`, replacing `ddf7ac3` which round 8
    approved"* is a correct sentence, and a check that flagged any retired sha
    anywhere in the window would refuse it — which is how a gate earns an
    allowlist and then stops meaning anything.
    """
    match = _PIN_TOKEN.search(claim)
    return match.group("sha") if match else None


#: A DECLARATIVE assertion that a round is open right now. The lookbehinds keep
#: conditionals out: "while a round is open" and "during an open round" state
#: when something holds and are correct.
_OPEN_ROUND_CLAIM = re.compile(
    r"(?<!\bwhile )(?<!\bduring an )(?<!\bif )"
    r"(?:round \d{1,3} is open"
    r"|round \d{1,3} is still open"
    r"|a round is (?:currently )?open"
    r"|round \d{1,3} remains open)",
    re.IGNORECASE,
)


def _user_facing_text() -> dict[str, str]:
    return {
        doc: (_REPO_ROOT / doc).read_text(encoding="utf-8") for doc in USER_FACING_DOCS
    }


def test_the_status_banner_names_the_EXACT_current_version() -> None:
    """§1 compares minors, so v0.6.27 survived a bump to v0.6.30. This does not.

    Patch-level drift matters on this particular line specifically because the
    status banner carries the pin and the round state beside the number, and both
    of those move with patch releases. A banner three patches behind is a banner
    whose other two claims are unlikely to be right either — which is exactly
    what was found.
    """
    for doc, text in _user_facing_text().items():
        for match in re.finditer(
            r"\*\*Status:\s*v(?P<ver>\d{1,3}(?:\.\d{1,3}){0,2})", text, re.IGNORECASE
        ):
            claimed = match.group("ver")
            assert claimed == __version__, (
                f"{doc}: the status banner says v{claimed} but __version__ is "
                f"{__version__}. §1 above cannot see this — it compares minors "
                f"only — and the banner also states the ripper pin and the round "
                f"state, which drift with it."
            )


def test_no_user_facing_doc_claims_a_RETIRED_ripper_pin_is_installed() -> None:
    """The README said *"This build still installs cyanrip … (`ddf7ac3`)"* three
    pins after that stopped being true.

    Checked against `fork_source.FORK_PIN` rather than a typed value, so it
    cannot drift when the pin next moves. A mention of a retired pin in
    HISTORICAL prose is fine and is not matched — only a present-tense install
    claim is.
    """
    from platterpus.deps import fork_source

    offenders: list[str] = []
    examined = 0
    for doc, text in _user_facing_text().items():
        for match in _INSTALL_CLAIM.finditer(text):
            examined += 1
            claim = match.group(0)
            subject = _claimed_install_pin(claim)
            if subject is None:
                continue  # a claim naming no sha says nothing checkable
            if subject in _RETIRED_PINS or not fork_source.same_commit(
                subject, fork_source.FORK_PIN
            ):
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(
                    f"{doc}:{line} says the installed build is `{subject}`; the "
                    f"production pin is {fork_source.FORK_PIN}"
                    + (" (a RETIRED pin)" if subject in _RETIRED_PINS else "")
                    + f": {claim[:110]!r}"
                )
    assert examined >= 1, (
        "no install claim found in the user-facing docs at all — either the "
        "wording changed (update _INSTALL_CLAIM) or the claim was removed. A "
        "pattern that cannot match cannot fail."
    )
    assert not offenders, "\n  ".join(offenders)


def test_the_install_claim_names_the_CURRENT_pin() -> None:
    """The converse, and the half that a retired-pin blocklist cannot cover.

    A blocklist only catches pins we thought to list. This asserts the positive:
    somewhere in the user-facing docs, the pin actually being installed is named,
    and it is `FORK_PIN`. Both halves are needed — the blocklist catches a stale
    claim, this catches a claim that names some pin nobody has ever heard of.
    """
    from platterpus.deps import fork_source

    corpus = "\n".join(_user_facing_text().values())
    assert fork_source.FORK_PIN in corpus, (
        f"no user-facing doc names the current production pin "
        f"{fork_source.FORK_PIN}. The front page tells a user which ripper build "
        f"they get; if it names none, or names only retired ones, that is the "
        f"same defect as naming the wrong one."
    )


def test_the_dependency_table_names_the_CURRENT_ripper_pin() -> None:
    """`DEPENDENCIES.md`'s cyanrip row is the second place a reader learns which
    ripper build ships, and it went stale TWICE for the same reason.

    The 2026-09-13 review found it naming the COPR as the package source three
    KDDs after the fork became the backend; the 2026-09-22 audit found it naming
    `fe4d2c4` / `+platterpus.12` / round 18 two pin-bearing rounds later. Both
    times a careful review read the row against memory. This reads it against
    `fork_source`, which is where the fact actually lives.
    """
    from platterpus.deps import fork_source

    text = (_REPO_ROOT / "DEPENDENCIES.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| cyanrip (")]
    assert len(rows) == 1, (
        f"expected exactly one cyanrip row in DEPENDENCIES.md, found {len(rows)} — "
        "the row was renamed or duplicated; update this selector"
    )
    row = rows[0]
    for fact, label in (
        (fork_source.FORK_PIN, "FORK_PIN"),
        (fork_source.FORK_EXPECTED_VERSION, "FORK_EXPECTED_VERSION"),
    ):
        assert fact in row, (
            f"DEPENDENCIES.md's cyanrip row does not name {label} ({fact}); it "
            "describes a ripper build that is not the one the app installs"
        )


def test_the_rig_sheet_header_names_the_CURRENT_pair() -> None:
    """`docs/rig-session.md` promises, in its own first paragraph, to be
    *"rewritten in place when the pairing moves"* and to name that pair in its
    header. On 2026-09-22 the header named `v0.6.30` + `d9c058c` — twenty-three
    patch versions and nine rounds stale — under a v0.6.52 footer, because a
    stamp records when a page was edited, not whether its header was.

    The pair is the app version and the production pin. Both are read from code.
    """
    from platterpus.deps import fork_source

    text = (_REPO_ROOT / "docs" / "rig-session.md").read_text(encoding="utf-8")
    fence = re.search(r"^```\n(?P<body>.*?)^```", text, re.S | re.M)
    assert fence, "docs/rig-session.md has no fenced header block to read the pair from"
    header = fence.group("body")
    assert f"v{__version__}" in header, (
        f"docs/rig-session.md's header does not name Platterpus v{__version__}. "
        "The app moved and the sheet did not: rewrite it in place for the new pair "
        "(archive the old one under docs/archive/ with a graduation-map row)."
    )
    assert fork_source.FORK_PIN in header, (
        f"docs/rig-session.md's header does not name the production pin "
        f"{fork_source.FORK_PIN}; a run against it would produce evidence about a "
        "different build."
    )
    # **AND THE BUILD UNDER REVIEW, while a round is reviewing one** (2026-09-23).
    # The two asserts above are the production pair, and during round 26 that is
    # the WRONG subject for the next run: its close condition is the real test on
    # `.15`, so a sheet naming only `3e01bb3` passed here while telling the operator
    # to test `.14`. The sheet exists to name what the next run is FOR.
    if fork_source.a_round_is_reviewing_a_build():
        assert fork_source.PIN_UNDER_REVIEW in header, (
            f"a round is reviewing {fork_source.PIN_UNDER_REVIEW} and "
            "docs/rig-session.md's header does not name it; the next run is the "
            "test of that build, and a sheet naming only the production pin sends "
            "the operator to evidence about a different one."
        )


#: Ripper build tags a user-facing doc may name although they are not current,
#: each with the reason it is historical rather than a claim. Empty today, and a
#: ratchet: an entry is an admission that a page names a build nobody runs.
_HISTORICAL_BUILD_TAGS: dict[str, str] = {}


def test_every_ripper_build_tag_in_a_user_facing_doc_is_the_CURRENT_one() -> None:
    """The gap the two pin tests above leave open, measured on 2026-09-22.

    `test_no_user_facing_doc_claims_a_RETIRED_ripper_pin_is_installed` matches
    `_INSTALL_CLAIM` — a present-tense *install* sentence. `test_the_install_
    claim_names_the_CURRENT_pin` asks only that the right pin appear SOMEWHERE in
    the corpus. Between them, a wrong pin in any other present-tense sentence
    passes both: the README carried *"Platterpus pins a fork — currently
    `fe4d2c4`, `cyanrip 0.9.4-rc2+platterpus.12`, approved by handshake round
    18"* inside a ⚠ READ THIS BEFORE YOU RUN box, five rounds after that stopped
    being true, while `2cce60d` appeared correctly forty lines away and satisfied
    the positive half.

    The same page also carried a `--version` example printing the stale banner,
    under a comment explaining that this had happened before and that the line
    *"must match the banner named earlier on this page"*. It had gone from four
    pins stale to two pins stale in the same line. **A comment where a check
    belongs is not a fix**, which is this repo's own rule arriving in the
    document a stranger reads first.

    So this sweeps the BANNER FORMS — `platterpus-fork-g<sha>` and
    `+platterpus.<n>` — which are statements of identity rather than references,
    and requires each to be the build the code actually pins. Both expected
    values are derived (`fork_source.FORK_PIN`, `FORK_EXPECTED_VERSION`), so they
    cannot drift when the pin next moves.
    """
    from platterpus.deps import fork_source

    expected_tag = fork_source.FORK_EXPECTED_VERSION.split("+", 1)[1]
    # **The build a round is REVIEWING is current too**, and only while one is.
    # Round 26 reviews `+platterpus.15` on a drive, and the front page has to say
    # which build the real test installs — a page forbidden from naming it would
    # send the operator to the production pin, which is evidence about a different
    # build. Derived from the same two constants the ripper offer and the
    # acceptance run read, so it closes again by itself when the round ends and
    # `PIN_UNDER_REVIEW` settles back onto `FORK_PIN`.
    current_shas = [fork_source.FORK_PIN]
    current_tags = {expected_tag}
    if fork_source.a_round_is_reviewing_a_build():
        current_shas.append(fork_source.PIN_UNDER_REVIEW)
        current_tags.add(fork_source.UNDER_REVIEW_TARGET.version.split("+", 1)[1])
    offenders: list[str] = []
    examined = 0
    for doc, text in _user_facing_text().items():
        for match in re.finditer(
            r"platterpus-fork-g(?P<sha>[0-9a-f]{6,40})|\+(?P<tag>platterpus\.\d+)",
            text,
        ):
            examined += 1
            found = match.group("sha") or match.group("tag")
            if found in _HISTORICAL_BUILD_TAGS:
                continue
            ok = (
                any(fork_source.same_commit(found, sha) for sha in current_shas)
                if match.group("sha")
                else found in current_tags
            )
            if not ok:
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(
                    f"{doc}:{line} names build `{found}`; the code pins "
                    f"{fork_source.FORK_PIN} / +{expected_tag}"
                    + (
                        f" and reviews {fork_source.PIN_UNDER_REVIEW}"
                        if len(current_shas) > 1
                        else ""
                    )
                )

    # NON-TRIVIALITY: a regex that stopped matching would otherwise pass here
    # while the page said anything at all.
    assert examined >= 3, (
        f"only {examined} ripper build tag(s) found in the user-facing docs. The "
        "front page states which ripper build a user gets, in more than one "
        "place; if this pattern has stopped matching, the sweep is checking "
        "nothing."
    )

    # THE CONVERSE: an exemption may not outlive the tag it excuses.
    stale = sorted(
        tag
        for tag in _HISTORICAL_BUILD_TAGS
        if tag not in "\n".join(_user_facing_text().values())
    )
    assert not stale, f"{stale} are excused but no longer appear anywhere"

    assert not offenders, "\n  ".join(offenders)


def test_the_readme_may_not_CLAIM_a_full_green_the_ledger_does_not_carry() -> None:
    """The false-claims class, in the document a stranger reads first.

    The README's hardware paragraph announced *"the first full green … the first
    `full-green` row this project's field-evidence ledger has ever carried"* and
    *"`0.7.100` is gated on a full hardware pass, which this is"* — for a run
    whose ledger row had been re-graded `partial` on the maintainer's ruling a
    week before, in the same commit that wrote *"Six rows, six partial, zero
    full-green. No full-green pass has been achieved."*

    Nothing could see it: the doc-stamp gate records WHEN a page was edited, and
    the README was edited for 0.6.52 while its hardware paragraph expired
    independently. §1 of this file compares VERSION strings. Neither reads the
    ledger the claim is about.

    Derived from the same table `_read_ledger` already parses, so the gate lifts
    the moment a run actually earns a full-green row.
    """
    rows = _read_ledger()
    assert rows, "the ledger is empty — the gate below would pass over nothing"
    full_green = [r for r in rows if r["result"] == "full-green"]
    if full_green:
        return  # the claim is available to make; this gate has nothing to say

    # PLANNING.md joined the corpus 2026-09-22: its KDD-35 status line said
    # *"the ledger's first `full-green` row exists"* for nine days after that row
    # was re-graded, and the backticks alone kept it out of the pattern. A status
    # line in the design log is read as current by whoever picks up the next
    # version-bump question, which is exactly the reader this gate protects.
    corpus = {**_user_facing_text(), **_ledger_status_text()}
    offenders: list[str] = []
    for doc, text in corpus.items():
        for match in re.finditer(
            r"(?:the )?first `?full[ -]green`?|`?full[ -]green`? row this project"
            r"|first `?full[ -]green`? row exists",
            text,
            re.I,
        ):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{doc}:{line}: {match.group(0)!r}")
    assert not offenders, (
        "a user-facing doc claims a full-green hardware pass, but the "
        f"field-evidence ledger carries {len(rows)} row(s) and none of them is "
        "`full-green`:\n  " + "\n  ".join(offenders)
    )


#: Documents outside README/SECURITY that state the ledger's CURRENT contents.
#: PLANNING.md's KDD-35 carries a dated status line about the ledger; the gates
#: below read it because a stale one there is read as current by the next person
#: asking whether a version bump is supported.
_LEDGER_STATUS_DOCS: tuple[str, ...] = ("PLANNING.md",)

_NUMBER_WORDS: dict[str, int] = {
    word: n
    for n, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}


def _ledger_status_text() -> dict[str, str]:
    return {
        doc: (_REPO_ROOT / doc).read_text(encoding="utf-8")
        for doc in _LEDGER_STATUS_DOCS
    }


def test_a_doc_that_COUNTS_the_ledger_rows_counts_them_correctly() -> None:
    """The README said *"the field-evidence ledger carries six rows"* in the same
    release that added the seventh — v0.6.53, found by the 2026-09-22 document
    audit. The full-green gate above could not see it: it asks whether a pass is
    CLAIMED, not whether the table is DESCRIBED correctly, and a row count is the
    number a reader uses to judge how much evidence exists.

    Floor: at least one count claim must be found, so a rewording that escapes the
    pattern turns this red instead of leaving it passing over nothing.
    """
    rows = _read_ledger()
    assert rows, "the ledger is empty — the gate below would pass over nothing"
    corpus = {**_user_facing_text(), **_ledger_status_text()}
    claims = 0
    wrong: list[str] = []
    for doc, text in corpus.items():
        for match in re.finditer(
            r"ledger (?:carries|holds|has) \**(?P<n>\d+|[a-z]+)\** rows", text, re.I
        ):
            token = match.group("n").lower()
            claimed = int(token) if token.isdigit() else _NUMBER_WORDS.get(token)
            if claimed is None:
                continue
            claims += 1
            if claimed != len(rows):
                line = text.count("\n", 0, match.start()) + 1
                wrong.append(f"{doc}:{line} says {claimed}, the ledger has {len(rows)}")
    assert claims >= 1, (
        "no ledger row-count claim found in README/SECURITY/PLANNING — if the "
        "sentence was reworded, update the pattern rather than let this pass "
        "over nothing"
    )
    assert not wrong, "a doc miscounts the field-evidence ledger:\n  " + "\n  ".join(
        wrong
    )


def test_the_readme_section_counts_match_the_severity_table() -> None:
    """The README printed *"17 sections are archival, 3 are UX"* — which is wrong
    twice: the table says 4 UX, and 17 + 3 does not reach the 21 sections the same
    paragraph implies.

    Both numbers move when a section is added or re-graded (K3 and K4 both moved
    in September), and nothing compared the prose to the table.
    """
    severity = (_REPO_ROOT / "docs" / "testing.md").read_text(encoding="utf-8")
    block = severity.split("<!-- ACCEPTANCE-SEVERITY-TABLE:", 1)[1].split(
        "<!-- END-ACCEPTANCE-SEVERITY-TABLE -->", 1
    )[0]
    rows = re.findall(r"^\|\s*([A-Z0-9]+)\s*\|\s*(ARCHIVAL|UX)\s*\|", block, re.M)
    assert len(rows) >= 15, f"only {len(rows)} severity rows parsed"
    archival = sum(1 for _, sev in rows if sev == "ARCHIVAL")
    ux = sum(1 for _, sev in rows if sev == "UX")

    for doc, text in _user_facing_text().items():
        for match in re.finditer(
            r"(?P<a>\d+)\s+are archival and\s+(?P<u>\d+)\s+are UX"
            r"|(?P<a2>\d+)\s+sections are archival,\s*(?P<u2>\d+)\s+are UX",
            text,
        ):
            claimed_a = int(match.group("a") or match.group("a2"))
            claimed_u = int(match.group("u") or match.group("u2"))
            line = text.count("\n", 0, match.start()) + 1
            assert (claimed_a, claimed_u) == (archival, ux), (
                f"{doc}:{line} says {claimed_a} archival / {claimed_u} UX; the "
                f"severity table in docs/testing.md has {archival} / {ux}"
            )


def test_the_readme_names_the_ROUND_and_APP_VERSION_the_approval_record_holds() -> None:
    """The §5.bn class, fourth instance — found hours after §5.bn was written.

    Round 23 closed `GO`/`GO` and moved `APPROVED_BY_ROUND` 22 -> 23 and
    `APPROVED_FOR_PLATTERPUS_VERSION` "0.6.51" -> "0.6.52". The README went on
    saying *"rounds 1 through 22 are all closed"*, *"Platterpus `0.6.51`"* and
    *"approved by handshake round 22"* — three live claims about the approval
    record, in the document a stranger reads first, and **every gate in this file
    passed**. The sweeps added with §5.bn cover the ledger, the severity counts
    and the build tag; none of them reads the round or the app version.

    A gate whose subject is "a claim that decays" has to enumerate the claims, and
    each one that is missed is invisible in exactly the same way. Derived from
    `handshake_approval`, which is itself derived from the closed-round record by
    `test_fork_source.py::test_the_approval_round_and_app_version_match_the_record`
    — so this is two links in one chain rather than a second opinion.
    """
    from platterpus import handshake_approval as ha

    checked = 0
    for doc, text in _user_facing_text().items():
        for match in re.finditer(
            r"rounds?\s+\*\*1 through (?P<through>\d+)\*\*"
            r"|approved by handshake round (?P<by>\d+)",
            text,
        ):
            checked += 1
            claimed = int(match.group("through") or match.group("by"))
            line = text.count("\n", 0, match.start()) + 1
            assert claimed == ha.APPROVED_BY_ROUND, (
                f"{doc}:{line} names handshake round {claimed}; the approval "
                f"record holds {ha.APPROVED_BY_ROUND}. The round number is a live "
                f"claim about what approved the pin a user is about to install."
            )
        for match in re.finditer(
            r"approved pair is.{0,200}?Platterpus \*\*`(?P<ver>\d+\.\d+\.\d+)`\*\*",
            text,
        ):
            checked += 1
            claimed = match.group("ver")
            line = text.count("\n", 0, match.start()) + 1
            assert claimed == ha.APPROVED_FOR_PLATTERPUS_VERSION, (
                f"{doc}:{line} says the approved pair names Platterpus {claimed}; "
                f"the record holds {ha.APPROVED_FOR_PLATTERPUS_VERSION}"
            )

    # NON-TRIVIALITY: a reworded banner would otherwise silently stop being checked.
    assert checked >= 3, (
        f"only {checked} round/app-version claim(s) matched in the user-facing "
        "docs. The status banner and the install box both carry one; if this "
        "pattern has stopped matching, the sweep is checking nothing."
    )


def test_no_user_facing_doc_ASSERTS_an_open_round_when_none_is_open() -> None:
    """The README said *"round 14 is open"* after round 14 closed GO/GO.

    **Delegated, not restated.** The answer comes from
    `fork_source.a_round_is_reviewing_a_build()` — the single predicate three code
    surfaces were unified onto the same day — so the front page cannot hold a
    different opinion from the app. That is the whole point: this was three
    implementations, then four once the README was counted.

    A conditional ("no release while a round is open") is a RULE and is correct;
    the lookbehinds keep it out.
    """
    from platterpus.deps import fork_source

    if fork_source.a_round_is_reviewing_a_build():
        pytest.skip(
            f"a round IS open (PIN_UNDER_REVIEW={fork_source.PIN_UNDER_REVIEW} != "
            f"FORK_PIN={fork_source.FORK_PIN}), so an open-round claim is correct "
            "here. The converse — a doc claiming CLOSED while a round is open — is "
            "covered by the pin checks above, which would name the reviewed build."
        )

    offenders: list[str] = []
    for doc, text in _user_facing_text().items():
        for match in _OPEN_ROUND_CLAIM.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{doc}:{line}: {match.group(0)!r}")
    assert not offenders, (
        "these assert a handshake round is OPEN, but no round is: "
        f"PIN_UNDER_REVIEW == FORK_PIN == {fork_source.FORK_PIN}, and "
        "`handshake.py --status` reports every round CLOSED.\n  "
        + "\n  ".join(offenders)
        + "\nA CONDITIONAL phrasing ('while a round is open') is a rule, is "
        "correct, and is not matched."
    )


#: A claim that the *approved pair* was proven on hardware. The round approves a
#: PAIR — a ripper pin AND a named Platterpus version — so a run on any other app
#: version is evidence about the RIPPER, not about the pair.
#:
#: Deliberately narrow. "the pair" / "the approved pair" / "the round-N pair" next
#: to a verification verb is the claim; a run reported as evidence about the pin
#: ("fe4d2c4 passed on hardware") is correct and is not matched.
_APPROVED_PAIR_PROVEN_CLAIM = re.compile(
    r"(?:the\s+)?(?:approved\s+pair|round[-\s]?\d+\s+pair|pair\s+round[-\s]?\d+\s+approved)"
    r"[^.\n]{0,80}?"
    r"\b(?:verified|proven|validated|confirmed|passed|green)\b"
    r"[^.\n]{0,40}?\b(?:on\s+)?(?:hardware|a\s+drive|the\s+rig|real\s+disc)",
    re.IGNORECASE,
)


#: Where a hardware result actually gets WRITTEN UP — which is not where
#: `USER_FACING_DOCS` points. That set is README + SECURITY, the two pages a user
#: reads; a run is written up in the session log, the task list and the handshake
#: record long before it reaches either. Guarding only the front page would have
#: been a sweep whose name promised the write-up and whose population excluded it.
_RUN_WRITEUP_DOCS: tuple[str, ...] = (
    "README.md",
    "TASKS.md",
    "CHANGELOG.md",
    "docs/session-log.md",
    "docs/cyanrip-handshake.md",
    "docs/testing.md",
)


#: A fenced code block, stripped before matching.
_FENCED_BLOCK = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
#: A double-quoted span. Quoting a claim is not making it.
#: Allows ONE line break inside the span: prose wraps, so a quoted sentence in a
#: CHANGELOG bullet routinely straddles two lines. Caught the second time this
#: gate ran — on its own changelog entry, which quotes the forbidden sentence in
#: order to say it would be false. Bounded to one newline so an unbalanced quote
#: cannot swallow a following paragraph.
_QUOTED_SPAN = re.compile(
    r"[\"\u201c\u201d][^\"\u201c\u201d\n]{0,200}"
    r"(?:\n[^\"\u201c\u201d\n]{0,200})?[\"\u201c\u201d]"
)


def _assertions_only(text: str) -> str:
    """Blank out what a document QUOTES, keeping what it STATES.

    The same rule `handshake.py` applies to the wire header, and for the same
    reason it was needed there: **a document warning against a claim is the most
    likely place that claim appears verbatim.** This gate proved it immediately —
    the `TASKS.md` row written to record the constraint quoted the forbidden
    sentence to say *do not write this*, and the first run flagged it.

    Blanked, not deleted, so reported line numbers stay true to the file.

    The evasion this permits — writing the false claim inside quotes — is the
    shape the gate is content to miss: a quoted sentence reads as a citation, and
    what it exists to stop is a *write-up asserting* the pair was proven.
    """

    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return _QUOTED_SPAN.sub(blank, _FENCED_BLOCK.sub(blank, text))


def _run_writeup_text() -> dict[str, str]:
    """Read the write-up docs, skipping any that have been retired.

    Tolerant of absence on purpose: this list names documents by path, and a gate
    that dies when one is renamed gets deleted rather than fixed. The floor below
    is what stops tolerance becoming vacuity.
    """
    found = {
        doc: (_REPO_ROOT / doc).read_text(encoding="utf-8")
        for doc in _RUN_WRITEUP_DOCS
        if (_REPO_ROOT / doc).is_file()
    }
    # A POPULATION FLOOR, because every other clause here can be satisfied by
    # finding nothing. If the paths rot, this fails loudly instead of passing.
    assert len(found) >= 4, (
        f"only {len(found)} of {len(_RUN_WRITEUP_DOCS)} write-up docs resolve "
        f"({sorted(found)}) — the sweep has lost its population and would pass "
        "by not looking. Fix the paths rather than lowering this floor."
    )
    return found


def test_no_doc_claims_the_APPROVED_PAIR_was_proven_while_the_app_has_moved_past_it() -> (
    None
):
    """A hardware run on an app version the round never approved is evidence
    about the RIPPER, not about the pair — and the write-up is where that slips.

    **The fork asked for this in the record before any artifact exists**, which is
    the right time: once a green run is in hand, "the round-17 pair verified on
    hardware" is the sentence that writes itself, and it would be false. Round 17
    approved (`fe4d2c4`, Platterpus **0.6.46**); the run is on **0.6.47**, because
    the pin roll that makes their published build report `approved` is itself
    0.6.47. So the pair under test is not the pair the round approved.

    **This is a NEW STATE the pin roll created**, which is the question `CLAUDE.md`
    asks of every fix: `APPROVED_FOR_PLATTERPUS_VERSION` and `__version__` had
    always been allowed to diverge in principle, and until now nothing depended on
    anyone noticing. The moment a hardware run is interpreted, it does.

    Skips when the two agree, because then the claim is simply true and a gate
    that fires on a correct sentence teaches people to route around it.
    """
    from platterpus import __version__
    from platterpus.handshake_approval import APPROVED_FOR_PLATTERPUS_VERSION

    if APPROVED_FOR_PLATTERPUS_VERSION == __version__:
        pytest.skip(
            f"the running app ({__version__}) IS the version the current pin was "
            "approved for, so a claim about 'the approved pair' is accurate here."
        )

    offenders: list[str] = []
    for doc, text in _run_writeup_text().items():
        for match in _APPROVED_PAIR_PROVEN_CLAIM.finditer(_assertions_only(text)):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{doc}:{line}: {match.group(0)!r}")
    assert not offenders, (
        "these claim the handshake-APPROVED PAIR was proven on hardware, but the "
        f"app has moved past it: the round approved Platterpus "
        f"{APPROVED_FOR_PLATTERPUS_VERSION} and this build is {__version__}.\n  "
        + "\n  ".join(offenders)
        + "\nA run on this build is evidence about the RIPPER PIN. Say that "
        "instead — naming the pin is accurate and is not matched."
    )


def test_the_approved_pair_pattern_catches_the_sentence_it_exists_to_stop() -> None:
    """Non-triviality. A prose gate that matches nothing is decoration, and this
    one is guarding a sentence nobody has written yet — so the only evidence it
    works is feeding it the sentence deliberately.
    """
    caught = "the round-17 pair verified on hardware with zero failures"
    assert _APPROVED_PAIR_PROVEN_CLAIM.search(caught), (
        "the pattern no longer catches the exact claim it was written for"
    )
    # And the sentence we DO want written must pass, or the gate pushes authors
    # toward vagueness instead of precision.
    allowed = "fe4d2c4 passed on hardware; this is evidence about the pin, not the pair"
    assert not _APPROVED_PAIR_PROVEN_CLAIM.search(allowed), (
        "the pattern fires on a correctly-scoped claim about the PIN, which would "
        "make the honest sentence unwritable"
    )

    # QUOTED IS NOT ASSERTED, and both directions are pinned. The first run of
    # this gate failed on the TASKS.md row written to record the rule, because
    # that row quotes the sentence in order to forbid it.
    quoting = 'do not write "the round-17 pair verified on hardware" — it is false'
    assert not _APPROVED_PAIR_PROVEN_CLAIM.search(_assertions_only(quoting)), (
        "a document that QUOTES the claim in order to warn against it is flagged, "
        "which makes the warning unwritable"
    )
    # A QUOTE THAT WRAPS IS STILL A QUOTE. Prose reflows, so the quoted sentence
    # lands across two lines as often as not — which is how this gate failed on
    # its own changelog entry the second time it ran.
    wrapped = 'never write "the round-17 pair verified on\nhardware" — it is false'
    assert not _APPROVED_PAIR_PROVEN_CLAIM.search(_assertions_only(wrapped)), (
        "a quoted warning broken across two lines is flagged, so the rule cannot "
        "be written down in wrapped prose"
    )
    assert _APPROVED_PAIR_PROVEN_CLAIM.search(_assertions_only(caught)), (
        "stripping quotes has swallowed the bare assertion too — the gate would "
        "now pass by not looking"
    )


def test_the_three_new_patterns_catch_the_text_that_actually_shipped() -> None:
    """Non-triviality, against the README's real line 9 as of 2026-08-27.

    All three claims were in ONE sentence, which is why one reviewer's glance
    missed all three. Fed verbatim so a reworded pattern cannot go quiet.
    """
    shipped = (
        "> **Status: v0.6.27 — out of beta.** The ripper pairing is **jointly "
        "verified**: handshake rounds 8 through 13 are all closed with `GO` from "
        "both projects, and round 14 is open with a single close condition — one "
        "hardware acceptance pass on the released pair. This build still installs "
        "cyanrip `0.9.4-rc1+platterpus.5` (`ddf7ac3`), the build round 8 approved "
        "and rig-tested on real hardware."
    )

    vers = [
        m.group("ver")
        for m in re.finditer(
            r"\*\*Status:\s*v(?P<ver>\d{1,3}(?:\.\d{1,3}){0,2})", shipped
        )
    ]
    assert vers == ["0.6.27"], vers
    assert vers[0] != __version__, "pick a different sample; 0.6.27 is now current"

    installs = [m.group(0) for m in _INSTALL_CLAIM.finditer(shipped)]
    assert installs, "the install-claim pattern misses the shipped text entirely"
    subjects = [_claimed_install_pin(c) for c in installs]
    assert "ddf7ac3" in subjects, (
        f"the SUBJECT of the shipped install claim was not extracted; got "
        f"{subjects} from {installs}. (The first version of the window was "
        f"`[^.\\n]` and died at the first dot of the version string.)"
    )

    # THE HARD-WRAPPED SHAPE, verbatim from README line 282-283. The window was
    # `[^\n]` when this was added and the revert probe reported the guard VACUOUS,
    # because the sha is on the line after the verb.
    wrapped = (
        "`cyanrip --version` should report something like\n"
        "`cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`. The parenthetical is"
    )
    wrapped_hits = [m.group(0) for m in _INSTALL_CLAIM.finditer(wrapped)]
    assert wrapped_hits, "the pattern misses a claim that wraps across a line"
    assert _claimed_install_pin(wrapped_hits[0]) == "ddf7ac3", (
        f"the wrapped claim's subject was not extracted: {wrapped_hits}"
    )

    # And it must NOT reach across a PARAGRAPH break into a different subject.
    across = (
        "the pin is `d9c058c` today.\n"
        "\n"
        "Historically round 8 approved `ddf7ac3`, which shipped in v0.6.4."
    )
    across_hits = [m.group(0) for m in _INSTALL_CLAIM.finditer(across)]
    assert across_hits and _claimed_install_pin(across_hits[0]) == "d9c058c", (
        f"the window crossed a blank line and picked up a different subject: "
        f"{across_hits}"
    )

    # Precision in the other direction: a sentence that names the CURRENT pin and
    # mentions a retired one historically must resolve to the current one.
    both = "This build installs cyanrip `d9c058c`, replacing `ddf7ac3` (round 8)."
    assert _claimed_install_pin(next(iter(_INSTALL_CLAIM.finditer(both))).group(0)) == (
        "d9c058c"
    ), "subject extraction takes the wrong sha when both are present"

    assert _OPEN_ROUND_CLAIM.search(shipped), "the open-round pattern misses it"

    # And the conditionals that must NOT fire — without these the check would
    # demand rewrites of correct rules, which is how a gate gets switched off.
    for correct in (
        "no release, no pin switch while a round is open",
        "the pin is expected to differ during an open round",
        "if a round is open, the release waits",
        "round 8 approved `ddf7ac3` and it shipped in v0.6.4",
    ):
        assert not _OPEN_ROUND_CLAIM.search(correct), (
            f"the open-round pattern FALSELY flags a correct phrasing: {correct!r}"
        )
