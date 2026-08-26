"""Guard the docs' ``*Last updated for Platterpus vX.Y.Z.*`` footers.

Why this exists
---------------
Every Markdown doc carries a visible "last updated for version X" footer so a
reader on GitHub can gauge its currency at a glance (the convention lives in
``docs/README.md`` → *Doc version stamps*; ``scripts/file_versions.py`` is the
git-derived counterpart for source files). The convention used to be trusted,
not enforced — and it drifted: every doc revised during the v0.5.0 cycle
shipped still stamped v0.4.24, because stamps were bumped to the version
current *at commit time*, which is always one release behind the release the
change actually ships in. The maintainer spotted it on the public README
(2026-07-21).

These tests make that impossible to repeat:

1. every tracked Markdown doc (minus the paste-body exemptions) carries
   exactly one footer;
2. no footer claims a version newer than the canonical ``__version__``
   (catches typos and copy-paste from the wrong branch);
3. any doc whose *content* changed since the latest release tag must be
   stamped with the *current* ``__version__`` — so the release-prep version
   bump forces the cycle's edited docs to be restamped before the release can
   go green. A stamp-only bump (footer-stripped content unchanged) doesn't
   count, so the requirement never cascades across untouched docs.

Test 3 needs git history and tags; on a checkout without them (e.g. a shallow
clone) it skips rather than guessing.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from platterpus import __version__

# Repo root, resolved from this file so the tests work from any CWD.
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# The footer line, exactly as the convention writes it. Anchored to a whole
# line so prose that merely *mentions* the convention (with a vX.Y.Z
# placeholder, or inside a bullet) can never match.
_FOOTER_RE: re.Pattern[str] = re.compile(
    # A PEP 440 pre-release suffix (`0.6.4b1`, `1.0rc2`) is part of the version.
    # The pattern was digits-and-dots only, so the day the project shipped its first
    # beta EVERY doc read as having zero footers — a check that could not see a
    # legal version of its own project. Bounded, per the project rule.
    r"^\*Last updated for Platterpus v(\d{1,4}(?:\.\d{1,4})+(?:(?:a|b|rc)\d{1,3})?)\.\*$",
    re.MULTILINE,
)

# The only Markdown files allowed to omit the footer: the ready-to-paste
# upstream issue/PR bodies, where a Platterpus footer would pollute the paste
# (see docs/README.md → "Doc version stamps").
_EXEMPT_DIR: str = "scripts/cyanrip/"
_EXEMPT_BASENAME_PREFIXES: tuple[str, ...] = ("issue-", "pr-")

# GENERATED docs. Their content is a pure function of the code, so a version
# stamp would make every unrelated release produce a spurious diff and train
# readers to ignore the diffs that matter — and the generator would have to
# re-render on release, which is exactly the coupling generating it avoided.
# Their staleness is enforced by regeneration instead (a strictly stronger
# check than a stamp: it compares content, not a claim about content).
#
# Not a free-form allow-list — an entry here must be a file some test
# regenerates and diffs, which `test_generated_docs_are_actually_generated`
# below verifies by finding the generator.
_EXEMPT_GENERATED: dict[str, str] = {
    "docs/cyanrip-consumer-contract.md": "scripts/emit_dependency_contract.py",
}


# Handshake round files (`docs/handshake/{outbound,inbound,verified}/`). These
# are **correspondence**, not documentation: a byte-faithful record of what was
# sent to and received from the cyanrip fork. Adding our version footer to an
# inbound file would edit the other project's words, and adding one to an
# outbound file would make the committed copy differ from what they received.
# A record that is not the record is worthless. Their currency is the round
# number, and `scripts/handshake.py --status` is what reports it.
_EXEMPT_CORRESPONDENCE: str = "docs/handshake/"

# The SHARED files. Exempt for a stronger reason than the round files: each is
# **the same document in both repositories and neither project owns it**, so
# stamping one with *our* version would fork the very files whose entire purpose
# is not being forked. Their currency is a spec version declared inside them and
# implemented by code — `HANDSHAKE-PROTOCOL` / `handshake.PROTOCOL_VERSION` for
# the protocol, `SEAM-RULES-VERSION` for the seam rules — a real version marker,
# just not ours to set unilaterally.
#
# **This constant named ONE file until round 7 lap 33, while the comment above it
# stated the general principle.** The cyanrip fork found the gap (their lap 32
# §H1) and the evidence was clean: the two shared files carrying our footer were
# exactly the two that drifted, and `handshake-protocol.md` — the one with no
# footer — matched byte-for-byte on the first try. Every Platterpus beta broke the
# other two by construction, because a per-project release stamp inside a
# byte-identical document is itself the drift the document exists to prevent. Same
# lesson as `docs/testing.md` §5.o: a rule enforced at the place it was learned is
# not enforced.
#
# **And it happened again with the fourth file, in the same commit that added it.**
# `docs/OWNERSHIP.md` (round 14 lap 17, `OWNERSHIP-VERSION: 1`) was wired into the
# *other* list of shared files — `test_handshake_tooling._SHARED_FILE_PATHS`, the
# one that compares hashes — and not into this one, so the stamp gate demanded a
# footer for a file that must not carry ours. Two lists answering "which files are
# shared" with no tie between them is the "do two surfaces answer this question?"
# shape; `test_the_two_shared_file_lists_agree` below is now that tie.
_EXEMPT_SHARED_FILES: frozenset[str] = frozenset(
    {
        "docs/handshake-protocol.md",
        "docs/seam-rules.md",
        "docs/seam-commands.md",
        "docs/OWNERSHIP.md",
    }
)


def test_the_two_shared_file_lists_agree() -> None:
    """One question, two lists, no tie — until this test.

    `_EXEMPT_SHARED_FILES` here decides *"do not stamp it"*; `_SHARED_FILE_PATHS`
    in `test_handshake_tooling.py` decides *"compare its hash with the fork's"*.
    Both are answering "which files are shared and owned by neither project", and
    a file in one but not the other is always a defect: shared-but-stamped forks
    the document, shared-but-unhashed means a unilateral edit passes the lap.

    Adding the fourth shared file put it in one list only, which is what this
    test now makes impossible. Compared as sets, in both directions — a one-way
    subset check would pass with the second list empty.
    """
    from test_handshake_tooling import _SHARED_FILE_PATHS  # noqa: PLC0415

    hashed = set(_SHARED_FILE_PATHS.values())
    assert hashed, "the hash-comparison list is empty — nothing would be checked"
    assert hashed == set(_EXEMPT_SHARED_FILES), (
        "the two shared-file lists disagree. Hashed but stampable: "
        f"{sorted(hashed - _EXEMPT_SHARED_FILES)}; stamp-exempt but never hashed: "
        f"{sorted(set(_EXEMPT_SHARED_FILES) - hashed)}. A shared file must be in "
        "both: our footer forks it, and an unhashed one can be edited unilaterally."
    )


def _is_exempt(rel_path: str) -> bool:
    """True for docs that deliberately carry no footer."""
    if rel_path in _EXEMPT_SHARED_FILES:
        return True
    if rel_path in _EXEMPT_GENERATED:
        return True
    if rel_path.startswith(_EXEMPT_CORRESPONDENCE):
        return True
    if not rel_path.startswith(_EXEMPT_DIR):
        return False
    basename = rel_path.rsplit("/", 1)[-1]
    return basename.startswith(_EXEMPT_BASENAME_PREFIXES)


def test_generated_docs_are_actually_generated() -> None:
    """A stamp exemption must be paid for by a generator, not just claimed.

    Without this, `_EXEMPT_GENERATED` is a way to silence the stamp check on any
    doc by asserting it is generated. Each entry must name a generator script
    that exists and that carries the doc's path, so the exemption is only
    available to files something really does regenerate.
    """
    for doc, generator in _EXEMPT_GENERATED.items():
        doc_path = _REPO_ROOT / doc
        gen_path = _REPO_ROOT / generator
        assert doc_path.exists(), f"{doc} is exempt but does not exist"
        assert gen_path.exists(), (
            f"{doc} claims generator {generator}, which is missing"
        )
        assert doc.rsplit("/", 1)[-1] in gen_path.read_text(encoding="utf-8"), (
            f"{generator} does not mention {doc} — it is not its generator"
        )
        assert "GENERATED" in doc_path.read_text(encoding="utf-8")[:2000], (
            f"{doc} carries no generated-file banner for a human reader"
        )


def _git(*args: str) -> str | None:
    """Run git in the repo root; None on any failure (missing git, no repo)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _tracked_markdown() -> list[str]:
    """Every git-tracked .md path (repo-relative); skips if git is unusable."""
    out = _git("ls-files", "*.md")
    if out is None:
        pytest.skip("git not available — cannot enumerate tracked docs")
    return [line for line in out.splitlines() if line]


def _version_tuple(version: str) -> tuple[int, ...]:
    """'0.5.0' → (0, 5, 0) so versions compare numerically, not textually.

    **PEP 440 pre-release suffixes are stripped**, so `0.6.4b1` → `(0, 6, 4)`.
    Without that this raised `ValueError: invalid literal for int() ... '4b1'` the
    moment the project shipped its first beta — a comparator that assumed every
    version it would ever see was a plain `X.Y.Z`, in a project whose release
    workflow has always had a pre-release branch.

    A beta sorts **equal to** its base release here rather than below it, and that
    is deliberate for what this comparator is used for: the question is *"is this
    stamp from the future?"*, and `0.6.4b1` is not a claim about a version after
    `0.6.4`. Ordering betas against each other is not a thing any caller asks.
    """
    parts: list[int] = []
    for part in version.split("."):
        digits = ""
        for ch in part:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def test_every_markdown_doc_carries_exactly_one_footer() -> None:
    """Each tracked doc ends with one (and only one) version-stamp footer."""
    offenders: list[str] = []
    for rel_path in _tracked_markdown():
        if _is_exempt(rel_path):
            continue
        stamps = _FOOTER_RE.findall((_REPO_ROOT / rel_path).read_text())
        if len(stamps) != 1:
            offenders.append(f"{rel_path} (found {len(stamps)} footers)")
    assert not offenders, (
        "Docs must carry exactly one '*Last updated for Platterpus vX.Y.Z.*' "
        "footer (docs/README.md → 'Doc version stamps'): " + ", ".join(offenders)
    )


def test_no_stamp_claims_a_future_version() -> None:
    """A footer newer than __version__ is a typo or a wrong-branch paste."""
    current = _version_tuple(__version__)
    offenders: list[str] = []
    for rel_path in _tracked_markdown():
        if _is_exempt(rel_path):
            continue
        for stamp in _FOOTER_RE.findall((_REPO_ROOT / rel_path).read_text()):
            if _version_tuple(stamp) > current:
                offenders.append(f"{rel_path} claims v{stamp} > v{__version__}")
    assert not offenders, "Doc stamps ahead of __version__: " + ", ".join(offenders)


def _strip_footer(text: str) -> str:
    """`text` with its version-stamp footer line(s) removed, for content diffs.

    A stamp bump alone must NOT count as a content change (otherwise every doc
    would be forced to restamp every release, contradicting the convention's own
    promise that an old stamp means "unchanged since"). Comparing the
    footer-stripped content is how we tell a real edit from a stamp-only bump.
    """
    return "\n".join(line for line in text.splitlines() if not _FOOTER_RE.match(line))


def test_docs_changed_since_last_release_are_stamped_current() -> None:
    """Any doc whose *content* changed since the newest release tag must stamp
    __version__.

    This is the forcing function: mid-cycle, __version__ is the last released
    version, so editing a doc's content requires bumping its stamp to that. The
    moment release-prep bumps __version__, every doc the cycle *actually edited*
    fails this test until restamped — so stamps can't lag the release their
    content ships in. A doc whose only difference from the tag is the stamp line
    itself is ignored (a stamp-only bump isn't a content change), which keeps
    the bump from cascading across untouched docs every release.
    """
    tag = _git("describe", "--tags", "--abbrev=0", "--match", "v*")
    if not tag:
        pytest.skip("no release tag reachable (shallow clone?) — cannot diff")
    # Worktree vs. tag: catches committed *and* not-yet-committed doc edits.
    diff = _git("diff", "--name-only", tag, "--", "*.md")
    if diff is None:
        pytest.skip(f"git diff against {tag} failed — cannot check stamps")
    offenders: list[str] = []
    for rel_path in diff.splitlines():
        path = _REPO_ROOT / rel_path
        if _is_exempt(rel_path) or not path.exists():
            continue  # exempt paste body, or the doc was deleted
        current = path.read_text()
        # A stamp-only change (the footer-stripped content matches the tag) is
        # not a content revision, so it doesn't require a fresh stamp. A file
        # absent at the tag (git show fails → None) is genuinely new content.
        at_tag = _git("show", f"{tag}:{rel_path}")
        if at_tag is not None and _strip_footer(at_tag) == _strip_footer(current):
            continue
        stamps = _FOOTER_RE.findall(current)
        # A missing/duplicated footer is test 1's finding; only judge staleness.
        if len(stamps) == 1 and stamps[0] != __version__:
            offenders.append(f"{rel_path} (stamped v{stamps[0]})")
    assert not offenders, (
        f"These docs' content changed since {tag} but aren't stamped with the "
        f"current __version__ (v{__version__}) — bump each footer in the same "
        "commit as the change (docs/README.md → 'Doc version stamps'): "
        + ", ".join(offenders)
    )


# --- The KDD range, mechanically ---------------------------------------------
#
# `README.md` and `docs/README.md` each describe `PLANNING.md` as holding
# "KDD-01 through KDD-NN". That NN has now drifted THREE times (v23-vs-v25 is
# called out in CLAUDE.md itself; docs/session-log.md records an earlier
# 19→21 catch; the 2026-07-28 audit found it stuck at 25 against an actual 32).
# Prose conventions have failed at this repeatedly, so it is a test now.

_KDD_HEADING: re.Pattern[str] = re.compile(r"^### KDD-(\d+)", re.MULTILINE)
# Matches "KDD-01 through KDD-25" and "KDD-01 … KDD-25" alike.
_KDD_RANGE: re.Pattern[str] = re.compile(r"KDD-0*1\s*(?:through|…|-|–|to)\s*KDD-(\d+)")


def test_every_documented_kdd_range_ends_at_the_last_real_kdd() -> None:
    planning = (_REPO_ROOT / "PLANNING.md").read_text(encoding="utf-8")
    numbers = [int(n) for n in _KDD_HEADING.findall(planning)]
    assert numbers, "PLANNING.md has no `### KDD-NN` headings — did the format change?"
    highest = max(numbers)

    stale: list[str] = []
    for path in sorted(_REPO_ROOT.rglob("*.md")):
        # The session log and the archive are dated HISTORY: an entry recording
        # "the range was KDD-01 … KDD-19 at the time" is correct, not drift.
        # Only living docs — the ones a contributor is told to trust — are held
        # to the current range.
        if ".git" in path.parts or path.name == "session-log.md":
            continue
        if "archive" in path.parts:
            continue
        for claimed in _KDD_RANGE.findall(path.read_text(encoding="utf-8")):
            if int(claimed) != highest:
                stale.append(
                    f"{path.relative_to(_REPO_ROOT)} says the range ends at "
                    f"KDD-{claimed}; PLANNING.md's last is KDD-{highest}"
                )
    assert not stale, "Stale KDD ranges:\n  " + "\n  ".join(stale)


def test_the_kdd_numbers_are_a_gapless_unique_sequence() -> None:
    """A duplicate or a skipped number would make every cross-reference
    ambiguous — the decision log is cited by number from six other docs."""
    planning = (_REPO_ROOT / "PLANNING.md").read_text(encoding="utf-8")
    numbers = [int(n) for n in _KDD_HEADING.findall(planning)]
    assert numbers == sorted(numbers), "KDD headings are out of order"
    assert len(set(numbers)) == len(numbers), "a KDD number is used twice"
    assert numbers == list(range(1, max(numbers) + 1)), "a KDD number is missing"
