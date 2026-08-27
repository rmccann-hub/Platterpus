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


# =============================================================================
# §3 — the front page's FACTS, not just its version number
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
