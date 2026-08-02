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
